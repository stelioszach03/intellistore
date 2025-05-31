package metadata

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/hashicorp/raft"
	"go.uber.org/zap"
)

// API provides HTTP endpoints for metadata operations
type API struct {
	raft   *raft.Raft
	fsm    *FSM
	logger *zap.Logger
}

// NewAPI creates a new API instance
func NewAPI(raftNode *raft.Raft, logger *zap.Logger) *API {
	// Extract FSM from raft node (this is a simplified approach)
	// In a real implementation, you'd need a way to access the FSM
	return &API{
		raft:   raftNode,
		logger: logger,
	}
}

// RegisterRoutes registers HTTP routes
func (a *API) RegisterRoutes(router *mux.Router) {
	// Bucket operations
	router.HandleFunc("/buckets", a.handleCreateBucket).Methods("POST")
	router.HandleFunc("/buckets/{bucketName}", a.handleDeleteBucket).Methods("DELETE")
	router.HandleFunc("/buckets/{bucketName}", a.handleGetBucket).Methods("GET")
	router.HandleFunc("/buckets", a.handleListBuckets).Methods("GET")

	// Object operations
	router.HandleFunc("/buckets/{bucketName}/objects", a.handleCreateObject).Methods("POST")
	router.HandleFunc("/buckets/{bucketName}/objects/{objectKey}", a.handleUpdateObject).Methods("PATCH")
	router.HandleFunc("/buckets/{bucketName}/objects/{objectKey}", a.handleDeleteObject).Methods("DELETE")
	router.HandleFunc("/buckets/{bucketName}/objects/{objectKey}", a.handleGetObject).Methods("GET")
	router.HandleFunc("/buckets/{bucketName}/objects", a.handleListObjects).Methods("GET")

	// Cluster operations
	router.HandleFunc("/cluster/status", a.handleClusterStatus).Methods("GET")
	router.HandleFunc("/cluster/leader", a.handleGetLeader).Methods("GET")
}

func (a *API) handleCreateBucket(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Name  string            `json:"name"`
		Owner string            `json:"owner"`
		ACL   map[string]string `json:"acl"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Name == "" {
		http.Error(w, "Bucket name is required", http.StatusBadRequest)
		return
	}

	// Check if we're the leader
	if a.raft.State() != raft.Leader {
		a.redirectToLeader(w, r)
		return
	}

	// Create command
	cmd := Command{
		Type: "create_bucket",
		Data: map[string]interface{}{
			"name":  req.Name,
			"owner": req.Owner,
			"acl":   req.ACL,
		},
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		http.Error(w, "Failed to marshal command", http.StatusInternalServerError)
		return
	}

	// Apply command to Raft
	future := a.raft.Apply(cmdBytes, 10*time.Second)
	if err := future.Error(); err != nil {
		a.logger.Error("Failed to apply create bucket command", zap.Error(err))
		http.Error(w, "Failed to create bucket", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Bucket created successfully",
		"name":    req.Name,
	})
}

func (a *API) handleDeleteBucket(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]

	if a.raft.State() != raft.Leader {
		a.redirectToLeader(w, r)
		return
	}

	cmd := Command{
		Type: "delete_bucket",
		Data: map[string]interface{}{
			"name": bucketName,
		},
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		http.Error(w, "Failed to marshal command", http.StatusInternalServerError)
		return
	}

	future := a.raft.Apply(cmdBytes, 10*time.Second)
	if err := future.Error(); err != nil {
		a.logger.Error("Failed to apply delete bucket command", zap.Error(err))
		http.Error(w, "Failed to delete bucket", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (a *API) handleGetBucket(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]

	// This is a read operation, can be served by any node
	// In a real implementation, you'd access the FSM to get bucket info
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"name":        bucketName,
		"createdAt":   time.Now(),
		"objectCount": 0,
		"totalSize":   0,
	})
}

func (a *API) handleListBuckets(w http.ResponseWriter, r *http.Request) {
	// This is a read operation, can be served by any node
	// In a real implementation, you'd access the FSM to list buckets
	buckets := []map[string]interface{}{
		{
			"name":        "example-bucket",
			"createdAt":   time.Now(),
			"objectCount": 0,
			"totalSize":   0,
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(buckets)
}

func (a *API) handleCreateObject(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]

	var req struct {
		ObjectKey     string      `json:"objectKey"`
		Size          int64       `json:"size"`
		Tier          string      `json:"tier"`
		Shards        []ShardInfo `json:"shards"`
		EncryptionKey string      `json:"encryptionKey"`
		Checksum      string      `json:"checksum"`
		ContentType   string      `json:"contentType"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if a.raft.State() != raft.Leader {
		a.redirectToLeader(w, r)
		return
	}

	cmd := Command{
		Type: "create_object",
		Data: map[string]interface{}{
			"bucketName":    bucketName,
			"objectKey":     req.ObjectKey,
			"size":          req.Size,
			"tier":          req.Tier,
			"shards":        req.Shards,
			"encryptionKey": req.EncryptionKey,
			"checksum":      req.Checksum,
			"contentType":   req.ContentType,
		},
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		http.Error(w, "Failed to marshal command", http.StatusInternalServerError)
		return
	}

	future := a.raft.Apply(cmdBytes, 10*time.Second)
	if err := future.Error(); err != nil {
		a.logger.Error("Failed to apply create object command", zap.Error(err))
		http.Error(w, "Failed to create object", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Object created successfully",
		"bucket":  bucketName,
		"key":     req.ObjectKey,
	})
}

func (a *API) handleUpdateObject(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]
	objectKey := vars["objectKey"]

	var req struct {
		Tier         string `json:"tier,omitempty"`
		LastAccessed int64  `json:"lastAccessed,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if a.raft.State() != raft.Leader {
		a.redirectToLeader(w, r)
		return
	}

	data := map[string]interface{}{
		"bucketName": bucketName,
		"objectKey":  objectKey,
	}

	if req.Tier != "" {
		data["tier"] = req.Tier
	}
	if req.LastAccessed != 0 {
		data["lastAccessed"] = req.LastAccessed
	}

	cmd := Command{
		Type: "update_object",
		Data: data,
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		http.Error(w, "Failed to marshal command", http.StatusInternalServerError)
		return
	}

	future := a.raft.Apply(cmdBytes, 10*time.Second)
	if err := future.Error(); err != nil {
		a.logger.Error("Failed to apply update object command", zap.Error(err))
		http.Error(w, "Failed to update object", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (a *API) handleDeleteObject(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]
	objectKey := vars["objectKey"]

	if a.raft.State() != raft.Leader {
		a.redirectToLeader(w, r)
		return
	}

	cmd := Command{
		Type: "delete_object",
		Data: map[string]interface{}{
			"bucketName": bucketName,
			"objectKey":  objectKey,
		},
	}

	cmdBytes, err := json.Marshal(cmd)
	if err != nil {
		http.Error(w, "Failed to marshal command", http.StatusInternalServerError)
		return
	}

	future := a.raft.Apply(cmdBytes, 10*time.Second)
	if err := future.Error(); err != nil {
		a.logger.Error("Failed to apply delete object command", zap.Error(err))
		http.Error(w, "Failed to delete object", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (a *API) handleGetObject(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]
	objectKey := vars["objectKey"]

	// This is a read operation, can be served by any node
	// In a real implementation, you'd access the FSM to get object info
	object := map[string]interface{}{
		"bucketName":   bucketName,
		"objectKey":    objectKey,
		"size":         1024,
		"tier":         "hot",
		"createdAt":    time.Now(),
		"lastAccessed": time.Now(),
		"shards":       []ShardInfo{},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(object)
}

func (a *API) handleListObjects(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	bucketName := vars["bucketName"]

	// This is a read operation, can be served by any node
	// In a real implementation, you'd access the FSM to list objects
	objects := []map[string]interface{}{
		{
			"bucketName":   bucketName,
			"objectKey":    "example-object.txt",
			"size":         1024,
			"tier":         "hot",
			"createdAt":    time.Now(),
			"lastAccessed": time.Now(),
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(objects)
}

func (a *API) handleClusterStatus(w http.ResponseWriter, r *http.Request) {
	status := map[string]interface{}{
		"state":        a.raft.State().String(),
		"leader":       string(a.raft.Leader()),
		"lastIndex":    a.raft.LastIndex(),
		"appliedIndex": a.raft.AppliedIndex(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (a *API) handleGetLeader(w http.ResponseWriter, r *http.Request) {
	leader := map[string]interface{}{
		"leader": string(a.raft.Leader()),
		"state":  a.raft.State().String(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(leader)
}

func (a *API) redirectToLeader(w http.ResponseWriter, r *http.Request) {
	leader := a.raft.Leader()
	if leader == "" {
		http.Error(w, "No leader available", http.StatusServiceUnavailable)
		return
	}

	// In a real implementation, you'd redirect to the leader's HTTP address
	w.Header().Set("Location", fmt.Sprintf("http://%s%s", leader, r.URL.Path))
	w.WriteHeader(http.StatusTemporaryRedirect)
}