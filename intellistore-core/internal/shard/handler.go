package shard

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/gorilla/mux"
	"github.com/intellistore/core/pkg/storage"
	"go.uber.org/zap"
)

// Handler handles shard operations
type Handler struct {
	storage *storage.Manager
	logger  *zap.Logger
}

// NewHandler creates a new shard handler
func NewHandler(storage *storage.Manager, logger *zap.Logger) *Handler {
	return &Handler{
		storage: storage,
		logger:  logger,
	}
}

// UploadRequest represents a shard upload request
type UploadRequest struct {
	ShardID     string `json:"shardId"`
	ObjectKey   string `json:"objectKey"`
	BucketName  string `json:"bucketName"`
	ShardType   string `json:"shardType"` // "data" or "parity"
	Index       int    `json:"index"`
	TotalShards int    `json:"totalShards"`
}

// HandleUpload handles shard upload requests
func (h *Handler) HandleUpload(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()

	// Parse multipart form
	if err := r.ParseMultipartForm(32 << 20); err != nil { // 32MB max
		h.logger.Error("Failed to parse multipart form", zap.Error(err))
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	// Get metadata from form
	shardID := r.FormValue("shardId")
	objectKey := r.FormValue("objectKey")
	bucketName := r.FormValue("bucketName")
	shardType := r.FormValue("shardType")
	indexStr := r.FormValue("index")
	totalShardsStr := r.FormValue("totalShards")

	if shardID == "" || objectKey == "" || bucketName == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	index, err := strconv.Atoi(indexStr)
	if err != nil {
		http.Error(w, "Invalid index", http.StatusBadRequest)
		return
	}

	totalShards, err := strconv.Atoi(totalShardsStr)
	if err != nil {
		http.Error(w, "Invalid totalShards", http.StatusBadRequest)
		return
	}

	// Get file from form
	file, header, err := r.FormFile("shard")
	if err != nil {
		h.logger.Error("Failed to get file from form", zap.Error(err))
		http.Error(w, "Failed to get file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	h.logger.Info("Receiving shard upload",
		zap.String("shardId", shardID),
		zap.String("objectKey", objectKey),
		zap.String("bucketName", bucketName),
		zap.String("shardType", shardType),
		zap.Int("index", index),
		zap.Int64("size", header.Size))

	// Create shard directory
	shardDir := filepath.Join(h.storage.GetDataDir(), "shards", bucketName, objectKey)
	if err := os.MkdirAll(shardDir, 0755); err != nil {
		h.logger.Error("Failed to create shard directory", zap.Error(err))
		http.Error(w, "Failed to create directory", http.StatusInternalServerError)
		return
	}

	// Create shard file
	shardPath := filepath.Join(shardDir, fmt.Sprintf("%s.shard", shardID))
	outFile, err := os.Create(shardPath)
	if err != nil {
		h.logger.Error("Failed to create shard file", zap.Error(err))
		http.Error(w, "Failed to create file", http.StatusInternalServerError)
		return
	}
	defer outFile.Close()

	// Copy file data and calculate checksum
	hasher := sha256.New()
	writer := io.MultiWriter(outFile, hasher)

	bytesWritten, err := io.Copy(writer, file)
	if err != nil {
		h.logger.Error("Failed to write shard data", zap.Error(err))
		http.Error(w, "Failed to write file", http.StatusInternalServerError)
		return
	}

	checksum := hex.EncodeToString(hasher.Sum(nil))

	// Create metadata file
	metadata := map[string]interface{}{
		"shardId":     shardID,
		"objectKey":   objectKey,
		"bucketName":  bucketName,
		"shardType":   shardType,
		"index":       index,
		"totalShards": totalShards,
		"size":        bytesWritten,
		"checksum":    checksum,
		"uploadedAt":  time.Now(),
		"tier":        h.storage.GetTier(),
	}

	metadataPath := filepath.Join(shardDir, fmt.Sprintf("%s.meta", shardID))
	metadataFile, err := os.Create(metadataPath)
	if err != nil {
		h.logger.Error("Failed to create metadata file", zap.Error(err))
		http.Error(w, "Failed to create metadata", http.StatusInternalServerError)
		return
	}
	defer metadataFile.Close()

	if err := json.NewEncoder(metadataFile).Encode(metadata); err != nil {
		h.logger.Error("Failed to write metadata", zap.Error(err))
		http.Error(w, "Failed to write metadata", http.StatusInternalServerError)
		return
	}

	// Update storage metrics
	h.storage.UpdateMetrics(bytesWritten, time.Since(startTime))

	h.logger.Info("Shard uploaded successfully",
		zap.String("shardId", shardID),
		zap.Int64("size", bytesWritten),
		zap.String("checksum", checksum),
		zap.Duration("duration", time.Since(startTime)))

	// Return success response
	response := map[string]interface{}{
		"shardId":  shardID,
		"size":     bytesWritten,
		"checksum": checksum,
		"message":  "Shard uploaded successfully",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(response)
}

// HandleDownload handles shard download requests
func (h *Handler) HandleDownload(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()
	vars := mux.Vars(r)
	shardID := vars["shardID"]

	if shardID == "" {
		http.Error(w, "Shard ID is required", http.StatusBadRequest)
		return
	}

	// Get bucket and object from query parameters
	bucketName := r.URL.Query().Get("bucket")
	objectKey := r.URL.Query().Get("object")

	if bucketName == "" || objectKey == "" {
		http.Error(w, "Bucket and object parameters are required", http.StatusBadRequest)
		return
	}

	h.logger.Info("Serving shard download",
		zap.String("shardId", shardID),
		zap.String("bucketName", bucketName),
		zap.String("objectKey", objectKey))

	// Find shard file
	shardDir := filepath.Join(h.storage.GetDataDir(), "shards", bucketName, objectKey)
	shardPath := filepath.Join(shardDir, fmt.Sprintf("%s.shard", shardID))
	metadataPath := filepath.Join(shardDir, fmt.Sprintf("%s.meta", shardID))

	// Check if shard exists
	if _, err := os.Stat(shardPath); os.IsNotExist(err) {
		h.logger.Warn("Shard not found", zap.String("shardId", shardID))
		http.Error(w, "Shard not found", http.StatusNotFound)
		return
	}

	// Read metadata
	var metadata map[string]interface{}
	if metadataFile, err := os.Open(metadataPath); err == nil {
		defer metadataFile.Close()
		json.NewDecoder(metadataFile).Decode(&metadata)
	}

	// Open shard file
	file, err := os.Open(shardPath)
	if err != nil {
		h.logger.Error("Failed to open shard file", zap.Error(err))
		http.Error(w, "Failed to open file", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	// Get file info
	fileInfo, err := file.Stat()
	if err != nil {
		h.logger.Error("Failed to get file info", zap.Error(err))
		http.Error(w, "Failed to get file info", http.StatusInternalServerError)
		return
	}

	// Set headers
	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Length", strconv.FormatInt(fileInfo.Size(), 10))
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s.shard", shardID))

	if metadata != nil {
		if checksum, ok := metadata["checksum"].(string); ok {
			w.Header().Set("X-Shard-Checksum", checksum)
		}
		if shardType, ok := metadata["shardType"].(string); ok {
			w.Header().Set("X-Shard-Type", shardType)
		}
	}

	// Stream file content
	bytesServed, err := io.Copy(w, file)
	if err != nil {
		h.logger.Error("Failed to stream shard", zap.Error(err))
		return
	}

	// Update metrics
	h.storage.UpdateDownloadMetrics(bytesServed, time.Since(startTime))

	h.logger.Info("Shard downloaded successfully",
		zap.String("shardId", shardID),
		zap.Int64("size", bytesServed),
		zap.Duration("duration", time.Since(startTime)))
}

// HandleDelete handles shard deletion requests
func (h *Handler) HandleDelete(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	shardID := vars["shardID"]

	if shardID == "" {
		http.Error(w, "Shard ID is required", http.StatusBadRequest)
		return
	}

	bucketName := r.URL.Query().Get("bucket")
	objectKey := r.URL.Query().Get("object")

	if bucketName == "" || objectKey == "" {
		http.Error(w, "Bucket and object parameters are required", http.StatusBadRequest)
		return
	}

	h.logger.Info("Deleting shard",
		zap.String("shardId", shardID),
		zap.String("bucketName", bucketName),
		zap.String("objectKey", objectKey))

	// Find shard files
	shardDir := filepath.Join(h.storage.GetDataDir(), "shards", bucketName, objectKey)
	shardPath := filepath.Join(shardDir, fmt.Sprintf("%s.shard", shardID))
	metadataPath := filepath.Join(shardDir, fmt.Sprintf("%s.meta", shardID))

	// Delete shard file
	if err := os.Remove(shardPath); err != nil && !os.IsNotExist(err) {
		h.logger.Error("Failed to delete shard file", zap.Error(err))
		http.Error(w, "Failed to delete shard", http.StatusInternalServerError)
		return
	}

	// Delete metadata file
	if err := os.Remove(metadataPath); err != nil && !os.IsNotExist(err) {
		h.logger.Error("Failed to delete metadata file", zap.Error(err))
		// Continue anyway, shard file is already deleted
	}

	// Try to remove directory if empty
	if entries, err := os.ReadDir(shardDir); err == nil && len(entries) == 0 {
		os.Remove(shardDir)
	}

	h.logger.Info("Shard deleted successfully", zap.String("shardId", shardID))

	w.WriteHeader(http.StatusNoContent)
}

// HandleList handles shard listing requests
func (h *Handler) HandleList(w http.ResponseWriter, r *http.Request) {
	bucketName := r.URL.Query().Get("bucket")
	objectKey := r.URL.Query().Get("object")

	var shards []map[string]interface{}

	if bucketName != "" && objectKey != "" {
		// List shards for specific object
		shardDir := filepath.Join(h.storage.GetDataDir(), "shards", bucketName, objectKey)
		if entries, err := os.ReadDir(shardDir); err == nil {
			for _, entry := range entries {
				if filepath.Ext(entry.Name()) == ".meta" {
					metadataPath := filepath.Join(shardDir, entry.Name())
					if metadataFile, err := os.Open(metadataPath); err == nil {
						var metadata map[string]interface{}
						json.NewDecoder(metadataFile).Decode(&metadata)
						shards = append(shards, metadata)
						metadataFile.Close()
					}
				}
			}
		}
	} else {
		// List all shards on this node
		shardsDir := filepath.Join(h.storage.GetDataDir(), "shards")
		filepath.Walk(shardsDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if filepath.Ext(path) == ".meta" {
				if metadataFile, err := os.Open(path); err == nil {
					var metadata map[string]interface{}
					json.NewDecoder(metadataFile).Decode(&metadata)
					shards = append(shards, metadata)
					metadataFile.Close()
				}
			}
			return nil
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"shards": shards,
		"count":  len(shards),
	})
}