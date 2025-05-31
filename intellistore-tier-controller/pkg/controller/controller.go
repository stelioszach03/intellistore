package controller

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"
	"net/http"
	"bytes"

	"github.com/Shopify/sarama"
	"github.com/intellistore/tier-controller/pkg/metrics"
	"github.com/sirupsen/logrus"
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
	httpClient      *http.Client
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

	// Initialize HTTP client for API calls
	httpClient := &http.Client{
		Timeout: 30 * time.Second,
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &Controller{
		config:         config,
		kafkaConsumer:  consumer,
		httpClient:     httpClient,
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

	// Create migration request payload
	migrationPayload := map[string]interface{}{
		"bucket_name":       request.BucketName,
		"object_key":        request.ObjectKey,
		"current_tier":      request.CurrentTier,
		"recommended_tier":  request.RecommendedTier,
		"confidence":        request.Confidence,
		"model_version":     request.ModelVersion,
	}

	payloadBytes, err := json.Marshal(migrationPayload)
	if err != nil {
		requestLogger.Errorf("Failed to marshal migration payload: %v", err)
		c.metrics.MigrationJobsCreationFailed.Inc()
		return
	}

	// Submit migration request to API
	apiURL := fmt.Sprintf("%s/api/v1/migrate", c.config.APIServiceURL)
	resp, err := c.httpClient.Post(apiURL, "application/json", bytes.NewBuffer(payloadBytes))
	if err != nil {
		requestLogger.Errorf("Failed to submit migration request: %v", err)
		c.metrics.MigrationJobsCreationFailed.Inc()
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		requestLogger.Errorf("Migration request failed with status: %d", resp.StatusCode)
		c.metrics.MigrationJobsCreationFailed.Inc()
		return
	}

	requestLogger.WithField("job_name", jobName).Info("Submitted migration request")
	c.metrics.MigrationJobsCreated.Inc()

	// Record completion time
	duration := time.Since(startTime)
	c.metrics.MigrationJobDuration.Observe(duration.Seconds())
	requestLogger.WithField("duration", duration).Info("Migration request completed")
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