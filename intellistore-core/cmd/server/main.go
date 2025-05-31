package main

import (
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/raft"
	raftboltdb "github.com/hashicorp/raft-boltdb/v2"
	"github.com/intellistore/core/internal/metadata"
	"github.com/intellistore/core/internal/shard"
	"github.com/intellistore/core/pkg/metrics"
	"github.com/intellistore/core/pkg/storage"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
)

func main() {
	var (
		mode     = flag.String("mode", "raft", "server mode: raft | storage")
		nodeID   = flag.String("id", "", "unique node ID")
		dataDir  = flag.String("data-dir", "/var/lib/intellistore", "storage data directory")
		raftAddr = flag.String("raft-addr", "0.0.0.0:5000", "address for Raft RPC")
		httpAddr = flag.String("http-addr", "0.0.0.0:8080", "address for HTTP API")
		joinAddr = flag.String("join", "", "address of existing cluster member to join")
		tier     = flag.String("tier", "ssd", "storage tier: ssd | hdd")
	)
	flag.Parse()

	// Initialize logger
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Initialize metrics
	metrics.Init()

	// Ensure data directory exists
	if err := os.MkdirAll(*dataDir, 0755); err != nil {
		logger.Fatal("Failed to create data directory", zap.Error(err))
	}

	switch *mode {
	case "raft":
		if err := runRaftNode(*nodeID, *dataDir, *raftAddr, *joinAddr, logger); err != nil {
			logger.Fatal("Failed to run Raft node", zap.Error(err))
		}
	case "storage":
		if err := runStorageNode(*nodeID, *dataDir, *httpAddr, *tier, logger); err != nil {
			logger.Fatal("Failed to run storage node", zap.Error(err))
		}
	default:
		fmt.Println("Invalid mode. Use -mode=raft or -mode=storage")
		os.Exit(1)
	}
}

func runRaftNode(nodeID, dataDir, raftAddr, joinAddr string, logger *zap.Logger) error {
	logger.Info("Starting Raft metadata node",
		zap.String("nodeID", nodeID),
		zap.String("dataDir", dataDir),
		zap.String("raftAddr", raftAddr))

	// Create Raft configuration
	cfg := raft.DefaultConfig()
	cfg.LocalID = raft.ServerID(nodeID)
	cfg.Logger = hclog.New(&hclog.LoggerOptions{
		Name:   "raft",
		Level:  hclog.Info,
		Output: os.Stderr,
	})

	// Create FSM (Finite State Machine)
	fsm := metadata.NewFSM(dataDir, logger)

	// Create transport
	addr, err := net.ResolveTCPAddr("tcp", raftAddr)
	if err != nil {
		return fmt.Errorf("failed to resolve TCP address: %w", err)
	}

	transport, err := raft.NewTCPTransport(raftAddr, addr, 3, 10*time.Second, os.Stderr)
	if err != nil {
		return fmt.Errorf("failed to create transport: %w", err)
	}

	// Create log store
	logStore, err := raftboltdb.NewBoltStore(filepath.Join(dataDir, "raft-log.db"))
	if err != nil {
		return fmt.Errorf("failed to create log store: %w", err)
	}

	// Create stable store
	stableStore, err := raftboltdb.NewBoltStore(filepath.Join(dataDir, "raft-stable.db"))
	if err != nil {
		return fmt.Errorf("failed to create stable store: %w", err)
	}

	// Create snapshot store
	snapshotStore, err := raft.NewFileSnapshotStore(dataDir, 3, os.Stderr)
	if err != nil {
		return fmt.Errorf("failed to create snapshot store: %w", err)
	}

	// Create Raft instance
	raftNode, err := raft.NewRaft(cfg, fsm, logStore, stableStore, snapshotStore, transport)
	if err != nil {
		return fmt.Errorf("failed to create Raft node: %w", err)
	}

	// Bootstrap cluster if this is the first node
	if joinAddr == "" {
		configuration := raft.Configuration{
			Servers: []raft.Server{
				{
					ID:      cfg.LocalID,
					Address: transport.LocalAddr(),
				},
			},
		}
		raftNode.BootstrapCluster(configuration)
		logger.Info("Bootstrapped new cluster")
	} else {
		// Join existing cluster
		logger.Info("Attempting to join cluster", zap.String("joinAddr", joinAddr))
		// In a real implementation, you'd make an HTTP request to the join address
		// to add this node to the cluster
	}

	// Start HTTP API server for metadata operations
	router := mux.NewRouter()
	api := metadata.NewAPI(raftNode, logger)
	api.RegisterRoutes(router)

	// Add metrics endpoint
	router.Handle("/metrics", promhttp.Handler())

	httpServer := &http.Server{
		Addr:    ":8080",
		Handler: router,
	}

	go func() {
		logger.Info("Starting HTTP API server", zap.String("addr", ":8080"))
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("HTTP server error", zap.Error(err))
		}
	}()

	// Start metrics server
	go func() {
		metricsRouter := mux.NewRouter()
		metricsRouter.Handle("/metrics", promhttp.Handler())
		logger.Info("Starting metrics server", zap.String("addr", ":9100"))
		if err := http.ListenAndServe(":9100", metricsRouter); err != nil {
			logger.Error("Metrics server error", zap.Error(err))
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("Shutting down Raft node")
	future := raftNode.Shutdown()
	if err := future.Error(); err != nil {
		logger.Error("Error shutting down Raft", zap.Error(err))
	}

	return nil
}

func runStorageNode(nodeID, dataDir, httpAddr, tier string, logger *zap.Logger) error {
	logger.Info("Starting storage node",
		zap.String("nodeID", nodeID),
		zap.String("dataDir", dataDir),
		zap.String("httpAddr", httpAddr),
		zap.String("tier", tier))

	// Create storage manager
	storageManager := storage.NewManager(dataDir, tier, logger)

	// Create shard handler
	shardHandler := shard.NewHandler(storageManager, logger)

	// Setup HTTP routes
	router := mux.NewRouter()

	// Shard operations
	router.HandleFunc("/shard/upload", shardHandler.HandleUpload).Methods("POST")
	router.HandleFunc("/shard/download/{shardID}", shardHandler.HandleDownload).Methods("GET")
	router.HandleFunc("/shard/delete/{shardID}", shardHandler.HandleDelete).Methods("DELETE")
	router.HandleFunc("/shard/list", shardHandler.HandleList).Methods("GET")

	// Health check
	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	}).Methods("GET")

	// Node info
	router.HandleFunc("/info", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		// In a real implementation, you'd use json.Marshal
		fmt.Fprintf(w, `{"nodeID":"%s","tier":"%s","dataDir":"%s","timestamp":%d}`,
			nodeID, tier, dataDir, time.Now().Unix())
	}).Methods("GET")

	// Add metrics endpoint
	router.Handle("/metrics", promhttp.Handler())

	// Start HTTP server
	server := &http.Server{
		Addr:    httpAddr,
		Handler: router,
	}

	go func() {
		logger.Info("Starting storage HTTP server", zap.String("addr", httpAddr))
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("HTTP server error", zap.Error(err))
		}
	}()

	// Start metrics server on separate port
	go func() {
		metricsRouter := mux.NewRouter()
		metricsRouter.Handle("/metrics", promhttp.Handler())
		logger.Info("Starting metrics server", zap.String("addr", ":9100"))
		if err := http.ListenAndServe(":9100", metricsRouter); err != nil {
			logger.Error("Metrics server error", zap.Error(err))
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("Shutting down storage node")
	return server.Close()
}



func parseStorageNodes(nodesList string) []string {
	if nodesList == "" {
		return nil
	}
	return strings.Split(nodesList, ",")
}