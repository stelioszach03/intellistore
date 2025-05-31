#!/bin/bash

# IntelliStore Complete Docker Deployment Script
# This script starts the full IntelliStore system with all services

set -e

echo "🚀 Starting IntelliStore Complete System..."
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose -f docker-compose.dev.yml down --remove-orphans --volumes

# Build all images
echo "🔨 Building all Docker images..."
docker-compose -f docker-compose.dev.yml build --no-cache

# Start infrastructure services first (Vault, Kafka, etc.)
echo "🏗️  Starting infrastructure services..."
docker-compose -f docker-compose.dev.yml up -d vault kafka zookeeper

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure services to be ready..."
sleep 30

# Initialize Vault (skip if already initialized)
echo "🔐 Initializing Vault..."
docker-compose -f docker-compose.dev.yml exec vault sh -c '
    export VAULT_ADDR=http://localhost:8200
    export VAULT_TOKEN=dev-root-token
    
    # Check if Vault is already initialized
    if vault status | grep -q "Initialized.*true"; then
        echo "Vault is already initialized, skipping init..."
        # Try to unseal if needed
        if vault status | grep -q "Sealed.*true"; then
            echo "Vault is sealed, attempting to unseal..."
            # In dev mode, Vault should auto-unseal
        fi
    else
        echo "Initializing Vault..."
        vault operator init -key-shares=1 -key-threshold=1 > /tmp/vault-keys.txt
        vault operator unseal $(grep "Unseal Key 1:" /tmp/vault-keys.txt | awk "{print \$NF}")
        export VAULT_TOKEN=$(grep "Initial Root Token:" /tmp/vault-keys.txt | awk "{print \$NF}")
    fi
    
    # Configure Vault
    vault auth -token=$VAULT_TOKEN || true
    vault secrets enable -path=intellistore kv-v2 || echo "KV engine already enabled"
    vault policy write intellistore-policy /vault/policies/intellistore-policy.hcl || echo "Policy already exists"
'

# Start Raft metadata nodes
echo "🗄️  Starting Raft metadata nodes..."
docker-compose -f docker-compose.dev.yml up -d raft-metadata-0 raft-metadata-1 raft-metadata-2

# Wait for Raft cluster to form
echo "⏳ Waiting for Raft cluster to form..."
sleep 20

# Start storage nodes
echo "💾 Starting storage nodes..."
docker-compose -f docker-compose.dev.yml up -d storage-node-0 storage-node-1 storage-node-2

# Wait for storage nodes to be ready
echo "⏳ Waiting for storage nodes to be ready..."
sleep 15

# Start application services
echo "🚀 Starting application services..."
docker-compose -f docker-compose.dev.yml up -d api ml-inference tier-controller

# Wait for application services
echo "⏳ Waiting for application services to be ready..."
sleep 20

# Start monitoring
echo "📊 Starting monitoring services..."
docker-compose -f docker-compose.dev.yml up -d prometheus grafana

# Start frontend
echo "🌐 Starting frontend..."
docker-compose -f docker-compose.dev.yml up -d frontend

echo ""
echo "✅ IntelliStore is starting up!"
echo "================================================"
echo ""
echo "🌐 Frontend:     http://localhost:53641"
echo "🔧 API:          http://localhost:8000"
echo "🔐 Vault:        http://localhost:8200"
echo "📊 Prometheus:   http://localhost:9090"
echo "📈 Grafana:      http://localhost:3001"
echo "🧠 ML Service:   http://localhost:8001"
echo ""
echo "⏳ Please wait 2-3 minutes for all services to fully initialize..."
echo ""
echo "📋 To check service status:"
echo "   docker-compose -f docker-compose.dev.yml ps"
echo ""
echo "📋 To view logs:"
echo "   docker-compose -f docker-compose.dev.yml logs -f [service-name]"
echo ""
echo "📋 To stop all services:"
echo "   docker-compose -f docker-compose.dev.yml down"
echo ""