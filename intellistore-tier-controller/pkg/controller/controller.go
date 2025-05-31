package controller

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/Shopify/sarama"
	"github.com/intellistore/tier-controller/pkg/k8s"
	"github.com/intellistore/tier-controller/pkg/metrics"
	"github.com/sirupsen/logrus"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

// TieringRequest represents a request to migrate an object between tiers
type TieringRequest struct {
	Timestamp        float64 `json:"timestamp"`
	BucketName       string  `json:"bucket_name"`
	ObjectKey        string  `json:"object_key"`
	CurrentTier      string  `json:"current_tier"`
	RecommendedTier  string  `json:"recommended_tier"`
	Confidence       float64 `json:"confidence"`
	ProbabilityHot   float64 `json:"probability_hot"`
	ModelVersion     string  `json:"model_version"`
}

// Config holds the configuration for the tier controller
type Config struct {
	KafkaBrokers     []string
	KafkaGroupID     string
	KafkaTopic       string
	APIServiceURL    string
	Kubeconfig       string
	Namespace        string
	Concurrency      int
	MigrationTimeout time.Duration
	MetricsRegistry  *metrics.Registry
	Logger           *logrus.Entry
}

// Controller manages tier migrations based on ML predictions
type Controller struct {
	config          *Config
	kafkaConsumer   sarama.ConsumerGroup
	k8sClient       kubernetes.Interface
	migrationQueue  chan *TieringRequest
	workers         sync.WaitGroup
	ctx             context.Context
	cancel          context.CancelFunc
	metrics         *metrics.Registry
	logger          *logrus.Entry
}

// New creates a new tier controller
func New(config *Config) (*Controller, error) {
	// Initialize Kafka consumer
	kafkaConfig := sarama.NewConfig()
	kafkaConfig.Consumer.Group.Rebalance.Strategy = sarama.BalanceStrategyRoundRobin
	kafkaConfig.Consumer.Offsets.Initial = sarama.OffsetNewest
	kafkaConfig.Consumer.Group.Session.Timeout = 10 * time.Second
	kafkaConfig.Consumer.Group.Heartbeat.Interval = 3 * time.Second

	consumer, err := sarama.NewConsumerGroup(config.KafkaBrokers, config.KafkaGroupID, kafkaConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kafka consumer: %w", err)
	}

	// Initialize Kubernetes client
	k8sClient, err := k8s.NewClient(config.Kubeconfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kubernetes client: %w", err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &Controller{
		config:         config,
		kafkaConsumer:  consumer,
		k8sClient:      k8sClient,
		migrationQueue: make(chan *TieringRequest, config.Concurrency*2),
		ctx:            ctx,
		cancel:         cancel,
		metrics:        config.MetricsRegistry,
		logger:         config.Logger,
	}, nil
}

// Start begins processing tier migration requests
func (c *Controller) Start(ctx context.Context) error {
	c.logger.Info("Starting tier controller")

	// Start worker goroutines
	for i := 0; i < c.config.Concurrency; i++ {
		c.workers.Add(1)
		go c.worker(i)
	}

	// Start Kafka consumer
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			default:
				if err := c.kafkaConsumer.Consume(ctx, []string{c.config.KafkaTopic}, c); err != nil {
					c.logger.Errorf("Kafka consumer error: %v", err)
					time.Sleep(5 * time.Second)
				}
			}
		}
	}()

	// Wait for context cancellation
	<-ctx.Done()

	c.logger.Info("Shutting down tier controller")

	// Cancel context and wait for workers
	c.cancel()
	c.workers.Wait()

	// Close Kafka consumer
	if err := c.kafkaConsumer.Close(); err != nil {
		c.logger.Errorf("Failed to close Kafka consumer: %v", err)
	}

	c.logger.Info("Tier controller stopped")
	return nil
}

// Setup implements sarama.ConsumerGroupHandler
func (c *Controller) Setup(sarama.ConsumerGroupSession) error {
	c.logger.Info("Kafka consumer group session started")
	return nil
}

// Cleanup implements sarama.ConsumerGroupHandler
func (c *Controller) Cleanup(sarama.ConsumerGroupSession) error {
	c.logger.Info("Kafka consumer group session ended")
	return nil
}

// ConsumeClaim implements sarama.ConsumerGroupHandler
func (c *Controller) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for {
		select {
		case message := <-claim.Messages():
			if message == nil {
				return nil
			}

			c.metrics.KafkaMessagesReceived.Inc()

			// Parse tiering request
			var request TieringRequest
			if err := json.Unmarshal(message.Value, &request); err != nil {
				c.logger.Errorf("Failed to parse tiering request: %v", err)
				c.metrics.KafkaMessageErrors.Inc()
				session.MarkMessage(message, "")
				continue
			}

			c.logger.WithFields(logrus.Fields{
				"bucket":           request.BucketName,
				"object":           request.ObjectKey,
				"current_tier":     request.CurrentTier,
				"recommended_tier": request.RecommendedTier,
				"confidence":       request.Confidence,
			}).Info("Received tiering request")

			// Queue for processing
			select {
			case c.migrationQueue <- &request:
				c.metrics.MigrationRequestsQueued.Inc()
			default:
				c.logger.Warn("Migration queue full, dropping request")
				c.metrics.MigrationRequestsDropped.Inc()
			}

			session.MarkMessage(message, "")

		case <-c.ctx.Done():
			return nil
		}
	}
}

// worker processes migration requests
func (c *Controller) worker(id int) {
	defer c.workers.Done()

	logger := c.logger.WithField("worker_id", id)
	logger.Info("Starting migration worker")

	for {
		select {
		case request := <-c.migrationQueue:
			c.processMigrationRequest(logger, request)
		case <-c.ctx.Done():
			logger.Info("Stopping migration worker")
			return
		}
	}
}

// processMigrationRequest handles a single migration request
func (c *Controller) processMigrationRequest(logger *logrus.Entry, request *TieringRequest) {
	startTime := time.Now()
	c.metrics.MigrationRequestsProcessed.Inc()

	requestLogger := logger.WithFields(logrus.Fields{
		"bucket":           request.BucketName,
		"object":           request.ObjectKey,
		"current_tier":     request.CurrentTier,
		"recommended_tier": request.RecommendedTier,
		"confidence":       request.Confidence,
	})

	requestLogger.Info("Processing migration request")

	// Check if migration is needed
	if request.CurrentTier == request.RecommendedTier {
		requestLogger.Info("Object already in recommended tier, skipping migration")
		c.metrics.MigrationRequestsSkipped.Inc()
		return
	}

	// Check confidence threshold
	confidenceThreshold := 0.8 // Configurable
	if request.Confidence < confidenceThreshold {
		requestLogger.Infof("Confidence %.2f below threshold %.2f, skipping migration", 
			request.Confidence, confidenceThreshold)
		c.metrics.MigrationRequestsSkipped.Inc()
		return
	}

	// Create migration job
	jobName := fmt.Sprintf("migrate-%s-%s-%d", 
		request.BucketName, 
		sanitizeObjectKey(request.ObjectKey), 
		time.Now().Unix())

	job, err := k8s.CreateMigrationJob(
		jobName,
		c.config.Namespace,
		request.BucketName,
		request.ObjectKey,
		request.CurrentTier,
		request.RecommendedTier,
		c.config.APIServiceURL,
	)
	if err != nil {
		requestLogger.Errorf("Failed to create migration job: %v", err)
		c.metrics.MigrationJobsCreationFailed.Inc()
		return
	}

	// Submit job to Kubernetes
	createdJob, err := c.k8sClient.BatchV1().Jobs(c.config.Namespace).Create(
		context.TODO(), job, metav1.CreateOptions{})
	if err != nil {
		requestLogger.Errorf("Failed to submit migration job: %v", err)
		c.metrics.MigrationJobsCreationFailed.Inc()
		return
	}

	requestLogger.WithField("job_name", createdJob.Name).Info("Created migration job")
	c.metrics.MigrationJobsCreated.Inc()

	// Monitor job completion (optional - could be done by a separate controller)
	go c.monitorMigrationJob(requestLogger, createdJob.Name, request, startTime)
}

// monitorMigrationJob monitors the completion of a migration job
func (c *Controller) monitorMigrationJob(logger *logrus.Entry, jobName string, request *TieringRequest, startTime time.Time) {
	timeout := time.After(c.config.MigrationTimeout)
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			logger.Errorf("Migration job %s timed out", jobName)
			c.metrics.MigrationJobsTimedOut.Inc()
			c.cleanupJob(jobName)
			return

		case <-ticker.C:
			job, err := c.k8sClient.BatchV1().Jobs(c.config.Namespace).Get(
				context.TODO(), jobName, metav1.GetOptions{})
			if err != nil {
				logger.Errorf("Failed to get job status: %v", err)
				continue
			}

			// Check if job completed
			if job.Status.Succeeded > 0 {
				duration := time.Since(startTime)
				logger.WithField("duration", duration).Info("Migration job completed successfully")
				c.metrics.MigrationJobsSucceeded.Inc()
				c.metrics.MigrationDuration.Observe(duration.Seconds())
				c.cleanupJob(jobName)
				return
			}

			// Check if job failed
			if job.Status.Failed > 0 {
				duration := time.Since(startTime)
				logger.WithField("duration", duration).Error("Migration job failed")
				c.metrics.MigrationJobsFailed.Inc()
				c.cleanupJob(jobName)
				return
			}

		case <-c.ctx.Done():
			return
		}
	}
}

// cleanupJob removes completed migration jobs
func (c *Controller) cleanupJob(jobName string) {
	// Delete job after completion (with some delay to allow log collection)
	go func() {
		time.Sleep(5 * time.Minute)
		
		deletePolicy := metav1.DeletePropagationForeground
		err := c.k8sClient.BatchV1().Jobs(c.config.Namespace).Delete(
			context.TODO(), jobName, metav1.DeleteOptions{
				PropagationPolicy: &deletePolicy,
			})
		if err != nil {
			c.logger.Errorf("Failed to cleanup job %s: %v", jobName, err)
		} else {
			c.logger.Infof("Cleaned up job %s", jobName)
		}
	}()
}

// sanitizeObjectKey removes characters that are not valid in Kubernetes resource names
func sanitizeObjectKey(objectKey string) string {
	// Replace invalid characters with hyphens
	result := ""
	for _, char := range objectKey {
		if (char >= 'a' && char <= 'z') || (char >= '0' && char <= '9') || char == '-' {
			result += string(char)
		} else {
			result += "-"
		}
	}
	
	// Ensure it doesn't start or end with hyphen
	if len(result) > 0 && result[0] == '-' {
		result = "obj" + result
	}
	if len(result) > 0 && result[len(result)-1] == '-' {
		result = result + "end"
	}
	
	// Limit length
	if len(result) > 50 {
		result = result[:50]
	}
	
	return result
}