package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"
)

var (
	port     = flag.Int("port", 8094, "Port for HTTP server")
	logLevel = flag.String("log-level", "info", "Log level (debug, info, warn, error)")
)

// TieringRequest represents a request to migrate an object between tiers
type TieringRequest struct {
	Timestamp       float64 `json:"timestamp"`
	BucketName      string  `json:"bucket_name"`
	ObjectKey       string  `json:"object_key"`
	CurrentTier     string  `json:"current_tier"`
	RecommendedTier string  `json:"recommended_tier"`
	Confidence      float64 `json:"confidence"`
	ProbabilityHot  float64 `json:"probability_hot"`
	ModelVersion    string  `json:"model_version"`
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status    string `json:"status"`
	Timestamp int64  `json:"timestamp"`
	Version   string `json:"version"`
}

func main() {
	flag.Parse()

	// Override with environment variables if set
	if envPort := os.Getenv("TIER_CONTROLLER_PORT"); envPort != "" {
		fmt.Sscanf(envPort, "%d", port)
	}

	// Configure logging
	level, err := logrus.ParseLevel(*logLevel)
	if err != nil {
		logrus.Fatalf("Invalid log level: %v", err)
	}
	logrus.SetLevel(level)
	logrus.SetFormatter(&logrus.JSONFormatter{})

	logger := logrus.WithFields(logrus.Fields{
		"component": "tier-controller",
		"version":   "1.0.0-simple",
	})

	logger.Info("Starting IntelliStore Tier Controller (Simple Mode)")

	// Create HTTP server
	mux := http.NewServeMux()

	// Health endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		response := HealthResponse{
			Status:    "healthy",
			Timestamp: time.Now().Unix(),
			Version:   "1.0.0-simple",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	})

	// Tier migration endpoint (simplified - just logs the request)
	mux.HandleFunc("/migrate", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req TieringRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}

		logger.WithFields(logrus.Fields{
			"bucket":           req.BucketName,
			"object":           req.ObjectKey,
			"current_tier":     req.CurrentTier,
			"recommended_tier": req.RecommendedTier,
			"confidence":       req.Confidence,
		}).Info("Received tier migration request")

		// In a real implementation, this would trigger the actual migration
		response := map[string]interface{}{
			"status":  "accepted",
			"message": "Migration request queued",
			"request": req,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	})

	// Status endpoint
	mux.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		status := map[string]interface{}{
			"status":     "running",
			"mode":       "simple",
			"version":    "1.0.0-simple",
			"timestamp":  time.Now().Unix(),
			"kafka":      "disabled",
			"kubernetes": "disabled",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(status)
	})

	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", *port),
		Handler: mux,
	}

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigChan
		logger.Infof("Received signal %v, shutting down gracefully", sig)
		
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer shutdownCancel()
		
		if err := server.Shutdown(shutdownCtx); err != nil {
			logger.Errorf("Server shutdown error: %v", err)
		}
	}()

	logger.Infof("Starting HTTP server on port %d", *port)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Fatalf("Server failed: %v", err)
	}

	logger.Info("Tier controller stopped")
}