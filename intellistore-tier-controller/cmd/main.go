package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/intellistore/tier-controller/pkg/controller"
	"github.com/intellistore/tier-controller/pkg/metrics"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sirupsen/logrus"
)

var (
	kafkaBrokers     = flag.String("kafka-brokers", "kafka:9092", "Kafka broker addresses")
	kafkaGroupID     = flag.String("kafka-group-id", "tier-controller", "Kafka consumer group ID")
	kafkaTopic       = flag.String("kafka-topic", "tiering-requests", "Kafka topic to consume from")
	apiServiceURL    = flag.String("api-service-url", "http://intellistore-api:8000", "IntelliStore API service URL")
	kubeconfig       = flag.String("kubeconfig", "", "Path to kubeconfig file (optional, uses in-cluster config if not provided)")
	namespace        = flag.String("namespace", "intellistore", "Kubernetes namespace for migration jobs")
	metricsPort      = flag.Int("metrics-port", 9090, "Port for Prometheus metrics")
	logLevel         = flag.String("log-level", "info", "Log level (debug, info, warn, error)")
	concurrency      = flag.Int("concurrency", 5, "Number of concurrent migration workers")
	migrationTimeout = flag.Duration("migration-timeout", 30*time.Minute, "Timeout for migration jobs")
)

func main() {
	flag.Parse()

	// Configure logging
	level, err := logrus.ParseLevel(*logLevel)
	if err != nil {
		logrus.Fatalf("Invalid log level: %v", err)
	}
	logrus.SetLevel(level)
	logrus.SetFormatter(&logrus.JSONFormatter{})

	logger := logrus.WithFields(logrus.Fields{
		"component": "tier-controller",
		"version":   "1.0.0",
	})

	logger.Info("Starting IntelliStore Tier Controller")

	// Initialize metrics
	metricsRegistry := metrics.NewRegistry()

	// Create controller configuration
	config := &controller.Config{
		KafkaBrokers:     []string{*kafkaBrokers},
		KafkaGroupID:     *kafkaGroupID,
		KafkaTopic:       *kafkaTopic,
		APIServiceURL:    *apiServiceURL,
		Kubeconfig:       *kubeconfig,
		Namespace:        *namespace,
		Concurrency:      *concurrency,
		MigrationTimeout: *migrationTimeout,
		MetricsRegistry:  metricsRegistry,
		Logger:           logger,
	}

	// Create and initialize controller
	ctrl, err := controller.New(config)
	if err != nil {
		logger.Fatalf("Failed to create controller: %v", err)
	}

	// Start metrics server
	go func() {
		mux := http.NewServeMux()
		mux.Handle("/metrics", promhttp.Handler())
		mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
			fmt.Fprintf(w, "OK")
		})

		server := &http.Server{
			Addr:    fmt.Sprintf(":%d", *metricsPort),
			Handler: mux,
		}

		logger.Infof("Starting metrics server on port %d", *metricsPort)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Errorf("Metrics server failed: %v", err)
		}
	}()

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigChan
		logger.Infof("Received signal %v, shutting down gracefully", sig)
		cancel()
	}()

	// Start controller
	logger.Info("Starting tier controller")
	if err := ctrl.Start(ctx); err != nil {
		logger.Fatalf("Controller failed: %v", err)
	}

	logger.Info("Tier controller stopped")
}