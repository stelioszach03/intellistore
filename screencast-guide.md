# IntelliStore Local Development Screencast Guide

This guide provides step-by-step instructions for setting up and running IntelliStore locally for demonstration purposes.

## Prerequisites

Before starting, ensure you have the following installed:
- Docker and Docker Compose
- Go 1.21+
- Python 3.11+
- Node.js 18+
- kubectl
- Helm 3.x
- k3d (for local Kubernetes)

## Quick Start (5 minutes)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/intellistore.git
cd intellistore

# Start local development environment
make dev
```

This single command will:
- Start all services with Docker Compose
- Initialize Vault with encryption keys
- Create sample data for demonstration
- Launch the frontend at http://localhost:3000

### 2. Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Vault UI**: http://localhost:8200

### 3. Demo Login

Use these credentials to log in:
- **Username**: demo
- **Password**: demo123

## Detailed Setup (15 minutes)

If you want to understand each component, follow these detailed steps:

### Step 1: Start Infrastructure Services

```bash
# Start Kafka, Zookeeper, and Vault
docker-compose up -d kafka zookeeper vault

# Wait for services to be ready
sleep 30

# Initialize Vault
./intellistore-vault-config/scripts/bootstrap-vault.sh
```

### Step 2: Build and Start Core Services

```bash
# Build the core service
cd intellistore-core
docker build -t intellistore-core .

# Start Raft metadata cluster (3 nodes)
docker-compose up -d raft-metadata-0 raft-metadata-1 raft-metadata-2

# Start storage nodes (6 nodes: 3 SSD, 3 HDD)
docker-compose up -d storage-node-ssd-0 storage-node-ssd-1 storage-node-ssd-2
docker-compose up -d storage-node-hdd-0 storage-node-hdd-1 storage-node-hdd-2
```

### Step 3: Start API and ML Services

```bash
# Build and start API service
cd ../intellistore-api
docker build -t intellistore-api .
docker-compose up -d api

# Build and start ML inference service
cd ../intellistore-ml
docker build -t intellistore-ml .
docker-compose up -d ml-inference

# Start tier controller
cd ../intellistore-tier-controller
docker build -t intellistore-tier-controller .
docker-compose up -d tier-controller
```

### Step 4: Start Frontend

```bash
# Build and start frontend
cd ../intellistore-frontend
npm install
npm run build
docker build -t intellistore-frontend .
docker-compose up -d frontend
```

### Step 5: Initialize Sample Data

```bash
# Create a demo user and bucket
cd ../intellistore-core
go run cmd/client/main.go --api-url http://localhost:8000 \
  login --username demo --password demo123

go run cmd/client/main.go --api-url http://localhost:8000 \
  create-bucket --name demo-bucket

# Upload some sample files
echo "This is a hot file that will be accessed frequently" > hot-file.txt
echo "This is a cold file that will be accessed rarely" > cold-file.txt

go run cmd/client/main.go --api-url http://localhost:8000 \
  upload --bucket demo-bucket --key hot-file.txt --file hot-file.txt

go run cmd/client/main.go --api-url http://localhost:8000 \
  upload --bucket demo-bucket --key cold-file.txt --file cold-file.txt
```

## Demo Scenarios

### Scenario 1: Basic File Operations

1. **Login** to the frontend at http://localhost:3000
2. **Navigate** to the Buckets page
3. **Click** on "demo-bucket" to view objects
4. **Upload** a new file using the drag-and-drop interface
5. **Watch** the progress bars for each shard (9 total: 6 data + 3 parity)
6. **Download** the file to verify integrity

### Scenario 2: ML-Driven Tiering

1. **Access** multiple files repeatedly to generate access patterns
2. **Navigate** to the Metrics Dashboard
3. **Observe** the ML predictions in the "ML Tiering" panel
4. **Watch** objects automatically migrate from cold to hot tier
5. **Check** the storage utilization charts

### Scenario 3: Monitoring and Observability

1. **Open** Grafana at http://localhost:3001
2. **Login** with admin/admin123
3. **Navigate** to the IntelliStore dashboard
4. **Observe** real-time metrics:
   - Cluster health and Raft consensus
   - Storage utilization per tier
   - API request rates and latencies
   - ML prediction accuracy

### Scenario 4: Fault Tolerance

1. **Stop** one storage node: `docker-compose stop storage-node-ssd-0`
2. **Try** downloading a file - it should still work (erasure coding)
3. **Check** the alerts in Grafana
4. **Restart** the node: `docker-compose start storage-node-ssd-0`
5. **Watch** the cluster recover

### Scenario 5: CLI Operations

```bash
# List all buckets
go run cmd/client/main.go --api-url http://localhost:8000 list-buckets

# List objects in a bucket
go run cmd/client/main.go --api-url http://localhost:8000 \
  list-objects --bucket demo-bucket

# Download a file
go run cmd/client/main.go --api-url http://localhost:8000 \
  download --bucket demo-bucket --key hot-file.txt --output downloaded.txt

# Force tier migration
go run cmd/client/main.go --api-url http://localhost:8000 \
  migrate-tier --bucket demo-bucket --key cold-file.txt --tier hot
```

## Kubernetes Demo (Advanced)

For a full Kubernetes demonstration:

### Step 1: Create Local Cluster

```bash
# Create k3d cluster
k3d cluster create intellistore-demo --port "8080:80@loadbalancer"

# Install Helm dependencies
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### Step 2: Deploy IntelliStore

```bash
# Deploy Kafka
helm install kafka bitnami/kafka

# Deploy Vault
helm install vault ./intellistore-vault-config/helm

# Deploy IntelliStore
helm install intellistore ./intellistore-helm
```

### Step 3: Access Services

```bash
# Port forward to access services
kubectl port-forward svc/intellistore-frontend 3000:3000 &
kubectl port-forward svc/intellistore-api 8000:8000 &
kubectl port-forward svc/grafana 3001:3000 &
```

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker logs with `docker-compose logs <service>`
2. **Vault sealed**: Run the bootstrap script again
3. **Frontend not loading**: Check if API is accessible at http://localhost:8000/health
4. **ML predictions not working**: Ensure Kafka is running and topics are created

### Useful Commands

```bash
# Check all service status
docker-compose ps

# View logs for a specific service
docker-compose logs -f api

# Restart a service
docker-compose restart <service-name>

# Clean up everything
make clean
docker-compose down -v
```

## Performance Testing

To demonstrate performance and scalability:

```bash
# Install hey (HTTP load testing tool)
go install github.com/rakyll/hey@latest

# Test API performance
hey -n 1000 -c 10 http://localhost:8000/health

# Test upload performance
for i in {1..10}; do
  echo "Test file $i" > test$i.txt
  go run cmd/client/main.go --api-url http://localhost:8000 \
    upload --bucket demo-bucket --key test$i.txt --file test$i.txt &
done
wait
```

## Demo Script

Here's a 10-minute demo script:

1. **[0-1 min]** Start with `make dev` and show services starting
2. **[1-3 min]** Login to frontend, show dashboard and navigation
3. **[3-5 min]** Upload files, show shard progress, demonstrate erasure coding
4. **[5-7 min]** Show ML tiering in action, metrics dashboard
5. **[7-8 min]** Demonstrate fault tolerance by stopping a node
6. **[8-9 min]** Show CLI operations and Vault integration
7. **[9-10 min]** Show monitoring, alerts, and observability

## Cleanup

```bash
# Stop all services
make clean

# Remove all data
docker-compose down -v
docker system prune -f
```

This will remove all containers, volumes, and networks created during the demo.