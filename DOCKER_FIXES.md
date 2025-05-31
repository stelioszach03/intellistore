# 🔧 IntelliStore Docker Fixes Applied

## ✅ Issues Fixed

### 1. Docker Image Connectivity Issues
- **Problem**: `node:18-alpine` and `golang:1.21-alpine` images couldn't be pulled
- **Solution**: Changed to stable base images:
  - `node:18-alpine` → `node:18`
  - `golang:1.21-alpine` → `golang:1.21`
  - `alpine:latest` → `debian:bullseye-slim`

### 2. Package Manager Compatibility
- **Problem**: Alpine-specific commands in Debian-based images
- **Solution**: Updated package manager commands:
  - `apk add` → `apt-get install`
  - `addgroup/adduser` → `groupadd/useradd`

### 3. Service Networking
- **Problem**: Services couldn't communicate (tier-controller ↔ Kafka, frontend ↔ API)
- **Solution**: Fixed service names and networking configuration:
  - Kafka advertised listeners: `localhost:9092` → `kafka:9092`
  - Frontend proxy targets: `intellistore-api` → `api`
  - Added proper service dependencies

### 4. Environment Variables
- **Problem**: Hardcoded connection strings
- **Solution**: Added environment variable support:
  - `KAFKA_BROKERS` for tier-controller
  - `API_SERVICE_URL` for tier-controller
  - Proper comma-separated parsing

## 🚀 How to Run

### Quick Start
```bash
# Navigate to project directory
cd intellistore

# Start all services
docker-compose -f docker-compose.dev.yml up --build
```

### Clean Restart (if issues persist)
```bash
# Use the restart script
bash restart-intellistore.sh
```

### Troubleshooting
```bash
# Run diagnostics
bash troubleshoot.sh
```

## 🌐 Service URLs

When running successfully, access:
- **Frontend**: http://localhost:53641
- **API**: http://localhost:8000
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Vault**: http://localhost:8200

## 📋 Service Status Check

```bash
# Check all containers
docker ps

# Check logs for specific service
docker-compose -f docker-compose.dev.yml logs [service-name]

# Example: Check API logs
docker-compose -f docker-compose.dev.yml logs api
```

## 🔍 Common Issues & Solutions

### Build Failures
```bash
# Clean Docker system
docker system prune -a

# Pull base images manually
docker pull node:18
docker pull golang:1.21
docker pull python:3.11-slim
docker pull debian:bullseye-slim
```

### Port Conflicts
```bash
# Stop all services
docker-compose -f docker-compose.dev.yml down

# Check what's using ports
netstat -tulpn | grep :53641
netstat -tulpn | grep :8000
```

### Network Issues
```bash
# Recreate networks
docker-compose -f docker-compose.dev.yml down
docker network prune
docker-compose -f docker-compose.dev.yml up --build
```

## 📝 Changes Made

### Files Modified:
1. `intellistore-frontend/Dockerfile.dev` - Changed base image
2. `intellistore-tier-controller/Dockerfile` - Updated to Debian-based build
3. `docker-compose.dev.yml` - Fixed service networking
4. `intellistore-tier-controller/cmd/main.go` - Added env var support
5. `intellistore-api/` - Added migration endpoints
6. `intellistore-frontend/vite.config.ts` - Fixed proxy configuration

### Git Status:
- Branch: `docker-deployment-complete`
- Latest commit: `7d7d6e1f`
- All fixes pushed to GitHub

## 🎯 Expected Behavior

After applying these fixes:
1. ✅ All Docker images build successfully
2. ✅ Services can communicate with each other
3. ✅ Frontend can reach API endpoints
4. ✅ Tier-controller can connect to Kafka
5. ✅ No more "connection refused" errors
6. ✅ Application runs end-to-end

## 🆘 If Problems Persist

1. Check Docker daemon is running
2. Ensure sufficient disk space (>2GB free)
3. Verify no other services using the same ports
4. Try the complete restart script
5. Check firewall/antivirus isn't blocking Docker

---

**Note**: These fixes address the core networking and build issues. The application should now start successfully with `docker-compose -f docker-compose.dev.yml up --build`.