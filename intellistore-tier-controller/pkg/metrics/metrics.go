package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Registry holds all metrics for the tier controller
type Registry struct {
	KafkaMessagesReceived      prometheus.Counter
	KafkaMessageErrors         prometheus.Counter
	MigrationRequestsQueued    prometheus.Counter
	MigrationRequestsDropped   prometheus.Counter
	MigrationRequestsProcessed prometheus.Counter
	MigrationRequestsSkipped   prometheus.Counter
	MigrationJobsCreated       prometheus.Counter
	MigrationJobsCreationFailed prometheus.Counter
	MigrationJobsSucceeded     prometheus.Counter
	MigrationJobsFailed        prometheus.Counter
	MigrationJobsTimedOut      prometheus.Counter
	MigrationDuration          prometheus.Histogram
}

// NewRegistry creates a new metrics registry
func NewRegistry() *Registry {
	return &Registry{
		KafkaMessagesReceived: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_kafka_messages_received_total",
			Help: "Total number of Kafka messages received",
		}),
		KafkaMessageErrors: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_kafka_message_errors_total",
			Help: "Total number of Kafka message processing errors",
		}),
		MigrationRequestsQueued: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_requests_queued_total",
			Help: "Total number of migration requests queued",
		}),
		MigrationRequestsDropped: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_requests_dropped_total",
			Help: "Total number of migration requests dropped due to full queue",
		}),
		MigrationRequestsProcessed: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_requests_processed_total",
			Help: "Total number of migration requests processed",
		}),
		MigrationRequestsSkipped: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_requests_skipped_total",
			Help: "Total number of migration requests skipped",
		}),
		MigrationJobsCreated: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_jobs_created_total",
			Help: "Total number of migration jobs created",
		}),
		MigrationJobsCreationFailed: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_jobs_creation_failed_total",
			Help: "Total number of migration job creation failures",
		}),
		MigrationJobsSucceeded: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_jobs_succeeded_total",
			Help: "Total number of successful migration jobs",
		}),
		MigrationJobsFailed: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_jobs_failed_total",
			Help: "Total number of failed migration jobs",
		}),
		MigrationJobsTimedOut: promauto.NewCounter(prometheus.CounterOpts{
			Name: "tier_controller_migration_jobs_timed_out_total",
			Help: "Total number of migration jobs that timed out",
		}),
		MigrationDuration: promauto.NewHistogram(prometheus.HistogramOpts{
			Name:    "tier_controller_migration_duration_seconds",
			Help:    "Duration of migration jobs in seconds",
			Buckets: prometheus.ExponentialBuckets(1, 2, 10), // 1s to ~17min
		}),
	}
}