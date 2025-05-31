package storage

import (
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"go.uber.org/zap"
)

// Manager manages storage operations and metrics
type Manager struct {
	dataDir string
	tier    string
	logger  *zap.Logger
	mu      sync.RWMutex

	// Metrics
	bytesStored     prometheus.Counter
	bytesServed     prometheus.Counter
	uploadDuration  prometheus.Histogram
	downloadDuration prometheus.Histogram
	diskUsage       prometheus.Gauge
	shardsCount     prometheus.Gauge
}

// NewManager creates a new storage manager
func NewManager(dataDir, tier string, logger *zap.Logger) *Manager {
	m := &Manager{
		dataDir: dataDir,
		tier:    tier,
		logger:  logger,
	}

	m.initMetrics()
	m.updateDiskUsage()

	// Start periodic disk usage updates
	go m.periodicDiskUsageUpdate()

	return m
}

func (m *Manager) initMetrics() {
	m.bytesStored = promauto.NewCounter(prometheus.CounterOpts{
		Name: "intellistore_storage_bytes_stored_total",
		Help: "Total bytes stored on this node",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
	})

	m.bytesServed = promauto.NewCounter(prometheus.CounterOpts{
		Name: "intellistore_storage_bytes_served_total",
		Help: "Total bytes served by this node",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
	})

	m.uploadDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name: "intellistore_storage_upload_duration_seconds",
		Help: "Duration of shard upload operations",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
		Buckets: prometheus.DefBuckets,
	})

	m.downloadDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name: "intellistore_storage_download_duration_seconds",
		Help: "Duration of shard download operations",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
		Buckets: prometheus.DefBuckets,
	})

	m.diskUsage = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_storage_disk_usage_bytes",
		Help: "Current disk usage in bytes",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
	})

	m.shardsCount = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_storage_shards_count",
		Help: "Number of shards stored on this node",
		ConstLabels: prometheus.Labels{
			"node_tier": m.tier,
		},
	})
}

// GetDataDir returns the data directory
func (m *Manager) GetDataDir() string {
	return m.dataDir
}

// GetTier returns the storage tier
func (m *Manager) GetTier() string {
	return m.tier
}

// UpdateMetrics updates storage metrics after an upload
func (m *Manager) UpdateMetrics(bytesStored int64, duration time.Duration) {
	m.bytesStored.Add(float64(bytesStored))
	m.uploadDuration.Observe(duration.Seconds())
	m.shardsCount.Inc()
}

// UpdateDownloadMetrics updates metrics after a download
func (m *Manager) UpdateDownloadMetrics(bytesServed int64, duration time.Duration) {
	m.bytesServed.Add(float64(bytesServed))
	m.downloadDuration.Observe(duration.Seconds())
}

// updateDiskUsage calculates and updates disk usage metrics
func (m *Manager) updateDiskUsage() {
	var totalSize int64

	shardsDir := filepath.Join(m.dataDir, "shards")
	if _, err := os.Stat(shardsDir); os.IsNotExist(err) {
		m.diskUsage.Set(0)
		return
	}

	err := filepath.Walk(shardsDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Continue walking even if there's an error
		}
		if !info.IsDir() && filepath.Ext(path) == ".shard" {
			totalSize += info.Size()
		}
		return nil
	})

	if err != nil {
		m.logger.Error("Failed to calculate disk usage", zap.Error(err))
		return
	}

	m.diskUsage.Set(float64(totalSize))
}

// periodicDiskUsageUpdate updates disk usage metrics periodically
func (m *Manager) periodicDiskUsageUpdate() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		m.updateDiskUsage()
	}
}

// GetStats returns current storage statistics
func (m *Manager) GetStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	// Count shards
	var shardCount int
	shardsDir := filepath.Join(m.dataDir, "shards")
	if _, err := os.Stat(shardsDir); err == nil {
		filepath.Walk(shardsDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if !info.IsDir() && filepath.Ext(path) == ".shard" {
				shardCount++
			}
			return nil
		})
	}

	return map[string]interface{}{
		"dataDir":    m.dataDir,
		"tier":       m.tier,
		"shardCount": shardCount,
		"diskUsage":  m.diskUsage,
	}
}

// Cleanup removes old or orphaned shards
func (m *Manager) Cleanup() error {
	m.logger.Info("Starting storage cleanup")

	shardsDir := filepath.Join(m.dataDir, "shards")
	if _, err := os.Stat(shardsDir); os.IsNotExist(err) {
		return nil
	}

	// In a real implementation, you would:
	// 1. Check with metadata service for valid shards
	// 2. Remove orphaned shards
	// 3. Clean up empty directories
	// 4. Compact storage if needed

	m.logger.Info("Storage cleanup completed")
	return nil
}

// HealthCheck performs a health check on the storage system
func (m *Manager) HealthCheck() error {
	// Check if data directory is accessible
	if _, err := os.Stat(m.dataDir); err != nil {
		return err
	}

	// Check if we can write to the data directory
	testFile := filepath.Join(m.dataDir, ".health_check")
	if err := os.WriteFile(testFile, []byte("test"), 0644); err != nil {
		return err
	}
	os.Remove(testFile)

	return nil
}