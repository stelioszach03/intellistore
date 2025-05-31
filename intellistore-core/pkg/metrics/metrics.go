package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Raft metrics
	RaftLeaderChanges = promauto.NewCounter(prometheus.CounterOpts{
		Name: "intellistore_raft_leader_changes_total",
		Help: "Total number of Raft leader changes",
	})

	RaftCommitDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name: "intellistore_raft_commit_duration_seconds",
		Help: "Duration of Raft commit operations",
		Buckets: prometheus.DefBuckets,
	})

	RaftAppliedIndex = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_raft_applied_index",
		Help: "Current Raft applied index",
	})

	RaftCommitIndex = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_raft_commit_index",
		Help: "Current Raft commit index",
	})

	RaftLastIndex = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_raft_last_index",
		Help: "Current Raft last index",
	})

	RaftState = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "intellistore_raft_state",
		Help: "Current Raft state (0=Follower, 1=Candidate, 2=Leader, 3=Shutdown)",
	}, []string{"node_id"})

	// Object storage metrics
	ObjectsTotal = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "intellistore_objects_total",
		Help: "Total number of objects stored",
	}, []string{"bucket", "tier"})

	ObjectSizeBytes = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_object_size_bytes",
		Help: "Size distribution of stored objects",
		Buckets: []float64{1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824}, // 1KB to 1GB
	}, []string{"bucket", "tier"})

	ObjectOperations = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_object_operations_total",
		Help: "Total number of object operations",
	}, []string{"operation", "bucket", "status"})

	ObjectOperationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_object_operation_duration_seconds",
		Help: "Duration of object operations",
		Buckets: prometheus.DefBuckets,
	}, []string{"operation", "bucket"})

	// Shard metrics
	ShardsTotal = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "intellistore_shards_total",
		Help: "Total number of shards stored",
	}, []string{"node_id", "tier", "shard_type"})

	ShardOperations = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_shard_operations_total",
		Help: "Total number of shard operations",
	}, []string{"operation", "node_id", "status"})

	ShardOperationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_shard_operation_duration_seconds",
		Help: "Duration of shard operations",
		Buckets: prometheus.DefBuckets,
	}, []string{"operation", "node_id"})

	ShardSizeBytes = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_shard_size_bytes",
		Help: "Size distribution of shards",
		Buckets: []float64{1024, 10240, 102400, 1048576, 10485760}, // 1KB to 10MB
	}, []string{"node_id", "shard_type"})

	// Erasure coding metrics
	ErasureOperations = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_erasure_operations_total",
		Help: "Total number of erasure coding operations",
	}, []string{"operation", "status"})

	ErasureOperationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_erasure_operation_duration_seconds",
		Help: "Duration of erasure coding operations",
		Buckets: prometheus.DefBuckets,
	}, []string{"operation"})

	ErasureReconstructionSuccess = promauto.NewCounter(prometheus.CounterOpts{
		Name: "intellistore_erasure_reconstruction_success_total",
		Help: "Total number of successful erasure code reconstructions",
	})

	ErasureReconstructionFailure = promauto.NewCounter(prometheus.CounterOpts{
		Name: "intellistore_erasure_reconstruction_failure_total",
		Help: "Total number of failed erasure code reconstructions",
	})

	// ML tiering metrics
	TieringPredictions = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_tiering_predictions_total",
		Help: "Total number of tiering predictions made",
	}, []string{"prediction"})

	TieringMigrations = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_tiering_migrations_total",
		Help: "Total number of tiering migrations",
	}, []string{"from_tier", "to_tier", "status"})

	TieringMigrationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_tiering_migration_duration_seconds",
		Help: "Duration of tiering migrations",
		Buckets: []float64{1, 5, 10, 30, 60, 300, 600}, // 1s to 10m
	}, []string{"from_tier", "to_tier"})

	TieringModelAccuracy = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_tiering_model_accuracy",
		Help: "Current accuracy of the tiering prediction model",
	})

	// API metrics
	APIRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_api_requests_total",
		Help: "Total number of API requests",
	}, []string{"method", "endpoint", "status"})

	APIRequestDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_api_request_duration_seconds",
		Help: "Duration of API requests",
		Buckets: prometheus.DefBuckets,
	}, []string{"method", "endpoint"})

	APIActiveConnections = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "intellistore_api_active_connections",
		Help: "Number of active API connections",
	})

	// Vault metrics
	VaultOperations = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "intellistore_vault_operations_total",
		Help: "Total number of Vault operations",
	}, []string{"operation", "status"})

	VaultOperationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "intellistore_vault_operation_duration_seconds",
		Help: "Duration of Vault operations",
		Buckets: prometheus.DefBuckets,
	}, []string{"operation"})

	// System metrics
	NodeHealth = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "intellistore_node_health",
		Help: "Health status of nodes (1=healthy, 0=unhealthy)",
	}, []string{"node_id", "node_type"})

	ClusterSize = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "intellistore_cluster_size",
		Help: "Number of nodes in the cluster",
	}, []string{"node_type"})
)

// Init initializes the metrics system
func Init() {
	// Register custom collectors if needed
	// This function can be used to set up any additional metrics configuration
}

// RecordRaftState records the current Raft state for a node
func RecordRaftState(nodeID string, state int) {
	RaftState.WithLabelValues(nodeID).Set(float64(state))
}

// RecordObjectOperation records an object operation
func RecordObjectOperation(operation, bucket, status string, duration float64) {
	ObjectOperations.WithLabelValues(operation, bucket, status).Inc()
	ObjectOperationDuration.WithLabelValues(operation, bucket).Observe(duration)
}

// RecordShardOperation records a shard operation
func RecordShardOperation(operation, nodeID, status string, duration float64) {
	ShardOperations.WithLabelValues(operation, nodeID, status).Inc()
	ShardOperationDuration.WithLabelValues(operation, nodeID).Observe(duration)
}

// RecordErasureOperation records an erasure coding operation
func RecordErasureOperation(operation, status string, duration float64) {
	ErasureOperations.WithLabelValues(operation, status).Inc()
	ErasureOperationDuration.WithLabelValues(operation).Observe(duration)
}

// RecordTieringPrediction records a tiering prediction
func RecordTieringPrediction(prediction string) {
	TieringPredictions.WithLabelValues(prediction).Inc()
}

// RecordTieringMigration records a tiering migration
func RecordTieringMigration(fromTier, toTier, status string, duration float64) {
	TieringMigrations.WithLabelValues(fromTier, toTier, status).Inc()
	TieringMigrationDuration.WithLabelValues(fromTier, toTier).Observe(duration)
}

// RecordAPIRequest records an API request
func RecordAPIRequest(method, endpoint, status string, duration float64) {
	APIRequests.WithLabelValues(method, endpoint, status).Inc()
	APIRequestDuration.WithLabelValues(method, endpoint).Observe(duration)
}

// RecordVaultOperation records a Vault operation
func RecordVaultOperation(operation, status string, duration float64) {
	VaultOperations.WithLabelValues(operation, status).Inc()
	VaultOperationDuration.WithLabelValues(operation).Observe(duration)
}

// SetNodeHealth sets the health status of a node
func SetNodeHealth(nodeID, nodeType string, healthy bool) {
	value := 0.0
	if healthy {
		value = 1.0
	}
	NodeHealth.WithLabelValues(nodeID, nodeType).Set(value)
}

// SetClusterSize sets the cluster size for a node type
func SetClusterSize(nodeType string, size int) {
	ClusterSize.WithLabelValues(nodeType).Set(float64(size))
}