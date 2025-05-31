package metadata

import (
	"encoding/json"
	"fmt"
	"io"
	"sync"
	"time"

	"github.com/hashicorp/raft"
	"go.uber.org/zap"
)

// ObjectMetadata represents metadata for a stored object
type ObjectMetadata struct {
	BucketName    string            `json:"bucketName"`
	ObjectKey     string            `json:"objectKey"`
	Size          int64             `json:"size"`
	Tier          string            `json:"tier"` // "hot" or "cold"
	CreatedAt     time.Time         `json:"createdAt"`
	LastAccessed  time.Time         `json:"lastAccessed"`
	Shards        []ShardInfo       `json:"shards"`
	EncryptionKey string            `json:"encryptionKey"` // Vault key reference
	Checksum      string            `json:"checksum"`
	ContentType   string            `json:"contentType"`
	Metadata      map[string]string `json:"metadata"`
}

// ShardInfo represents information about a single shard
type ShardInfo struct {
	ShardID   string `json:"shardId"`
	NodeID    string `json:"nodeId"`
	NodeAddr  string `json:"nodeAddr"`
	ShardType string `json:"shardType"` // "data" or "parity"
	Index     int    `json:"index"`
	Size      int64  `json:"size"`
	Checksum  string `json:"checksum"`
}

// BucketMetadata represents metadata for a bucket
type BucketMetadata struct {
	Name        string            `json:"name"`
	CreatedAt   time.Time         `json:"createdAt"`
	Owner       string            `json:"owner"`
	ACL         map[string]string `json:"acl"` // user -> permission
	ObjectCount int64             `json:"objectCount"`
	TotalSize   int64             `json:"totalSize"`
	Metadata    map[string]string `json:"metadata"`
}

// Command represents a command to be applied to the FSM
type Command struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
}

// FSM implements the raft.FSM interface for metadata operations
type FSM struct {
	mu      sync.RWMutex
	dataDir string
	logger  *zap.Logger

	// In-memory state
	objects map[string]*ObjectMetadata // key: bucketName/objectKey
	buckets map[string]*BucketMetadata // key: bucketName
}

// NewFSM creates a new FSM instance
func NewFSM(dataDir string, logger *zap.Logger) *FSM {
	return &FSM{
		dataDir: dataDir,
		logger:  logger,
		objects: make(map[string]*ObjectMetadata),
		buckets: make(map[string]*BucketMetadata),
	}
}

// Apply applies a Raft log entry to the FSM
func (f *FSM) Apply(log *raft.Log) interface{} {
	f.mu.Lock()
	defer f.mu.Unlock()

	var cmd Command
	if err := json.Unmarshal(log.Data, &cmd); err != nil {
		f.logger.Error("Failed to unmarshal command", zap.Error(err))
		return fmt.Errorf("failed to unmarshal command: %w", err)
	}

	switch cmd.Type {
	case "create_bucket":
		return f.applyCreateBucket(cmd.Data)
	case "delete_bucket":
		return f.applyDeleteBucket(cmd.Data)
	case "create_object":
		return f.applyCreateObject(cmd.Data)
	case "update_object":
		return f.applyUpdateObject(cmd.Data)
	case "delete_object":
		return f.applyDeleteObject(cmd.Data)
	case "update_access_time":
		return f.applyUpdateAccessTime(cmd.Data)
	default:
		f.logger.Error("Unknown command type", zap.String("type", cmd.Type))
		return fmt.Errorf("unknown command type: %s", cmd.Type)
	}
}

func (f *FSM) applyCreateBucket(data interface{}) interface{} {
	bucketData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid bucket data")
	}

	bucket := &BucketMetadata{
		Name:        bucketData["name"].(string),
		CreatedAt:   time.Now(),
		Owner:       bucketData["owner"].(string),
		ACL:         make(map[string]string),
		ObjectCount: 0,
		TotalSize:   0,
		Metadata:    make(map[string]string),
	}

	if acl, exists := bucketData["acl"]; exists {
		if aclMap, ok := acl.(map[string]interface{}); ok {
			for k, v := range aclMap {
				bucket.ACL[k] = v.(string)
			}
		}
	}

	f.buckets[bucket.Name] = bucket
	f.logger.Info("Created bucket", zap.String("name", bucket.Name))
	return nil
}

func (f *FSM) applyDeleteBucket(data interface{}) interface{} {
	bucketData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid bucket data")
	}

	bucketName := bucketData["name"].(string)
	delete(f.buckets, bucketName)
	
	// Remove all objects in the bucket
	for key := range f.objects {
		if f.objects[key].BucketName == bucketName {
			delete(f.objects, key)
		}
	}

	f.logger.Info("Deleted bucket", zap.String("name", bucketName))
	return nil
}

func (f *FSM) applyCreateObject(data interface{}) interface{} {
	objectData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid object data")
	}

	object := &ObjectMetadata{
		BucketName:   objectData["bucketName"].(string),
		ObjectKey:    objectData["objectKey"].(string),
		Size:         int64(objectData["size"].(float64)),
		Tier:         objectData["tier"].(string),
		CreatedAt:    time.Now(),
		LastAccessed: time.Now(),
		Shards:       make([]ShardInfo, 0),
		Checksum:     objectData["checksum"].(string),
		ContentType:  objectData["contentType"].(string),
		Metadata:     make(map[string]string),
	}

	if encKey, exists := objectData["encryptionKey"]; exists {
		object.EncryptionKey = encKey.(string)
	}

	if shards, exists := objectData["shards"]; exists {
		if shardsSlice, ok := shards.([]interface{}); ok {
			for _, shardData := range shardsSlice {
				if shardMap, ok := shardData.(map[string]interface{}); ok {
					shard := ShardInfo{
						ShardID:   shardMap["shardId"].(string),
						NodeID:    shardMap["nodeId"].(string),
						NodeAddr:  shardMap["nodeAddr"].(string),
						ShardType: shardMap["shardType"].(string),
						Index:     int(shardMap["index"].(float64)),
						Size:      int64(shardMap["size"].(float64)),
						Checksum:  shardMap["checksum"].(string),
					}
					object.Shards = append(object.Shards, shard)
				}
			}
		}
	}

	key := fmt.Sprintf("%s/%s", object.BucketName, object.ObjectKey)
	f.objects[key] = object

	// Update bucket statistics
	if bucket, exists := f.buckets[object.BucketName]; exists {
		bucket.ObjectCount++
		bucket.TotalSize += object.Size
	}

	f.logger.Info("Created object",
		zap.String("bucket", object.BucketName),
		zap.String("key", object.ObjectKey),
		zap.Int64("size", object.Size))
	return nil
}

func (f *FSM) applyUpdateObject(data interface{}) interface{} {
	objectData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid object data")
	}

	bucketName := objectData["bucketName"].(string)
	objectKey := objectData["objectKey"].(string)
	key := fmt.Sprintf("%s/%s", bucketName, objectKey)

	if object, exists := f.objects[key]; exists {
		if tier, exists := objectData["tier"]; exists {
			object.Tier = tier.(string)
		}
		if lastAccessed, exists := objectData["lastAccessed"]; exists {
			if timestamp, ok := lastAccessed.(float64); ok {
				object.LastAccessed = time.Unix(int64(timestamp), 0)
			}
		}
		f.logger.Info("Updated object",
			zap.String("bucket", bucketName),
			zap.String("key", objectKey))
	}

	return nil
}

func (f *FSM) applyDeleteObject(data interface{}) interface{} {
	objectData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid object data")
	}

	bucketName := objectData["bucketName"].(string)
	objectKey := objectData["objectKey"].(string)
	key := fmt.Sprintf("%s/%s", bucketName, objectKey)

	if object, exists := f.objects[key]; exists {
		// Update bucket statistics
		if bucket, exists := f.buckets[bucketName]; exists {
			bucket.ObjectCount--
			bucket.TotalSize -= object.Size
		}

		delete(f.objects, key)
		f.logger.Info("Deleted object",
			zap.String("bucket", bucketName),
			zap.String("key", objectKey))
	}

	return nil
}

func (f *FSM) applyUpdateAccessTime(data interface{}) interface{} {
	objectData, ok := data.(map[string]interface{})
	if !ok {
		return fmt.Errorf("invalid object data")
	}

	bucketName := objectData["bucketName"].(string)
	objectKey := objectData["objectKey"].(string)
	key := fmt.Sprintf("%s/%s", bucketName, objectKey)

	if object, exists := f.objects[key]; exists {
		object.LastAccessed = time.Now()
	}

	return nil
}

// Snapshot returns a snapshot of the FSM state
func (f *FSM) Snapshot() (raft.FSMSnapshot, error) {
	f.mu.RLock()
	defer f.mu.RUnlock()

	// Create a deep copy of the state
	objects := make(map[string]*ObjectMetadata)
	for k, v := range f.objects {
		objects[k] = v
	}

	buckets := make(map[string]*BucketMetadata)
	for k, v := range f.buckets {
		buckets[k] = v
	}

	return &fsmSnapshot{
		objects: objects,
		buckets: buckets,
	}, nil
}

// Restore restores the FSM state from a snapshot
func (f *FSM) Restore(snapshot io.ReadCloser) error {
	f.mu.Lock()
	defer f.mu.Unlock()

	var state struct {
		Objects map[string]*ObjectMetadata `json:"objects"`
		Buckets map[string]*BucketMetadata `json:"buckets"`
	}

	if err := json.NewDecoder(snapshot).Decode(&state); err != nil {
		return fmt.Errorf("failed to decode snapshot: %w", err)
	}

	f.objects = state.Objects
	f.buckets = state.Buckets

	f.logger.Info("Restored FSM state from snapshot",
		zap.Int("objects", len(f.objects)),
		zap.Int("buckets", len(f.buckets)))

	return nil
}

// GetObject retrieves object metadata
func (f *FSM) GetObject(bucketName, objectKey string) (*ObjectMetadata, bool) {
	f.mu.RLock()
	defer f.mu.RUnlock()

	key := fmt.Sprintf("%s/%s", bucketName, objectKey)
	object, exists := f.objects[key]
	return object, exists
}

// GetBucket retrieves bucket metadata
func (f *FSM) GetBucket(bucketName string) (*BucketMetadata, bool) {
	f.mu.RLock()
	defer f.mu.RUnlock()

	bucket, exists := f.buckets[bucketName]
	return bucket, exists
}

// ListObjects lists all objects in a bucket
func (f *FSM) ListObjects(bucketName string) []*ObjectMetadata {
	f.mu.RLock()
	defer f.mu.RUnlock()

	var objects []*ObjectMetadata
	for _, object := range f.objects {
		if object.BucketName == bucketName {
			objects = append(objects, object)
		}
	}
	return objects
}

// ListBuckets lists all buckets
func (f *FSM) ListBuckets() []*BucketMetadata {
	f.mu.RLock()
	defer f.mu.RUnlock()

	var buckets []*BucketMetadata
	for _, bucket := range f.buckets {
		buckets = append(buckets, bucket)
	}
	return buckets
}

// fsmSnapshot implements raft.FSMSnapshot
type fsmSnapshot struct {
	objects map[string]*ObjectMetadata
	buckets map[string]*BucketMetadata
}

func (s *fsmSnapshot) Persist(sink raft.SnapshotSink) error {
	state := struct {
		Objects map[string]*ObjectMetadata `json:"objects"`
		Buckets map[string]*BucketMetadata `json:"buckets"`
	}{
		Objects: s.objects,
		Buckets: s.buckets,
	}

	if err := json.NewEncoder(sink).Encode(state); err != nil {
		sink.Cancel()
		return fmt.Errorf("failed to encode snapshot: %w", err)
	}

	return sink.Close()
}

func (s *fsmSnapshot) Release() {
	// Nothing to release
}