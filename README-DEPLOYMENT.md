# IntelliStore Complete Docker Deployment Guide

## 🚀 Quick Start

This is the complete IntelliStore system with all services running in Docker containers. The system includes:

- **Frontend**: React application with professional UI
- **API**: FastAPI backend with authentication and data management
- **Core**: Go-based distributed storage with Raft consensus
- **ML Service**: Machine learning inference service
- **Tier Controller**: Kubernetes-based storage tier management
- **Infrastructure**: Vault, Kafka, Redis, PostgreSQL, Prometheus, Grafana

## 📋 Prerequisites

1. **Docker** (version 20.10 or higher)
2. **Docker Compose** (version 2.0 or higher)
3. **At least 8GB RAM** (recommended 16GB)
4. **At least 10GB free disk space**

## 🏃‍♂️ Running the System

### Option 1: Automated Script (Recommended)

```bash
# Make the script executable
chmod +x start-intellistore.sh

# Run the complete system
./start-intellistore.sh
```

### Option 2: Manual Steps

```bash
# 1. Clean up any existing containers
docker-compose -f docker-compose.dev.yml down --remove-orphans --volumes

# 2. Build all images
docker-compose -f docker-compose.dev.yml build

# 3. Start infrastructure services
docker-compose -f docker-compose.dev.yml up -d vault kafka zookeeper redis postgres

# 4. Wait 30 seconds for infrastructure to initialize
sleep 30

# 5. Start Raft metadata cluster
docker-compose -f docker-compose.dev.yml up -d raft-metadata-0 raft-metadata-1 raft-metadata-2

# 6. Wait 20 seconds for Raft cluster to form
sleep 20

# 7. Start storage nodes
docker-compose -f docker-compose.dev.yml up -d storage-node-0 storage-node-1 storage-node-2

# 8. Start application services
docker-compose -f docker-compose.dev.yml up -d api ml-inference tier-controller

# 9. Start monitoring
docker-compose -f docker-compose.dev.yml up -d prometheus grafana

# 10. Start frontend
docker-compose -f docker-compose.dev.yml up -d frontend
```

## 🌐 Access Points

Once all services are running, you can access:

- **Frontend Application**: http://localhost:53641
- **API Documentation**: http://localhost:8000/docs
- **Vault UI**: http://localhost:8200
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **ML Service**: http://localhost:8001

## 📊 Service Status

Check if all services are running:

```bash
docker-compose -f docker-compose.dev.yml ps
```

Expected services:
- ✅ frontend (port 53641)
- ✅ api (port 8000)
- ✅ ml-inference (port 8001)
- ✅ tier-controller (port 8002)
- ✅ raft-metadata-0, raft-metadata-1, raft-metadata-2
- ✅ storage-node-0, storage-node-1, storage-node-2
- ✅ vault (port 8200)
- ✅ kafka (port 9092)
- ✅ zookeeper (port 2181)
- ✅ redis (port 6379)
- ✅ postgres (port 5432)
- ✅ prometheus (port 9090)
- ✅ grafana (port 3001)

## 🔍 Troubleshooting

### View Service Logs

```bash
# View all logs
docker-compose -f docker-compose.dev.yml logs -f

# View specific service logs
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f api
docker-compose -f docker-compose.dev.yml logs -f vault
```

### Common Issues

1. **Port conflicts**: Make sure ports 53641, 8000, 8001, 8002, 8200, 9090, 3001 are available
2. **Memory issues**: Ensure you have at least 8GB RAM available
3. **Docker daemon**: Make sure Docker is running and you have permissions

### Restart Services

```bash
# Restart specific service
docker-compose -f docker-compose.dev.yml restart frontend

# Restart all services
docker-compose -f docker-compose.dev.yml restart
```

### Clean Restart

```bash
# Stop all services and remove volumes
docker-compose -f docker-compose.dev.yml down --volumes

# Remove all images (optional)
docker-compose -f docker-compose.dev.yml down --rmi all

# Start fresh
./start-intellistore.sh
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │       API       │    │   ML Service   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Python)     │
│   Port 53641    │    │   Port 8000     │    │   Port 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Tier Controller │    │   Raft Cluster │    │ Storage Nodes   │
│ (Kubernetes)    │◄──►│   (Metadata)    │◄──►│ (Distributed)   │
│   Port 8002     │    │   3 Nodes       │    │   3 Nodes       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Vault       │    │     Kafka       │    │   Monitoring    │
│  (Secrets)      │    │  (Messaging)    │    │ Prometheus +    │
│   Port 8200     │    │   Port 9092     │    │   Grafana       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔐 Security Notes

- Vault is initialized with development settings
- Default credentials are used for demo purposes
- In production, use proper secret management
- All services run in isolated Docker networks

## 📈 Performance Monitoring

- **Prometheus**: Collects metrics from all services
- **Grafana**: Visualizes system performance
- **Health checks**: All services have built-in health endpoints

## 🛑 Stopping the System

```bash
# Stop all services
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.dev.yml down --volumes
```

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose -f docker-compose.dev.yml logs -f`
2. Verify all services are running: `docker-compose -f docker-compose.dev.yml ps`
3. Ensure you have enough system resources (RAM, disk space)
4. Try a clean restart with `--volumes` flag

---

**Note**: This is a complete production-like deployment with real services, not simplified mocks. All components are fully functional and interconnected.