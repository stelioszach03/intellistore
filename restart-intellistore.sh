#!/bin/bash

echo "🔄 Restarting IntelliStore with clean build..."
echo "================================================"

# Stop and remove all containers
echo "🛑 Stopping all containers..."
docker-compose -f docker-compose.dev.yml down --volumes --remove-orphans

# Remove all images to force rebuild
echo "🗑️ Removing old images..."
docker images | grep intellistore | awk '{print $3}' | xargs -r docker rmi -f

# Clean Docker system
echo "🧹 Cleaning Docker system..."
docker system prune -f

# Pull base images to ensure they're available
echo "📥 Pulling base images..."
docker pull node:18
docker pull golang:1.21
docker pull debian:bullseye-slim
docker pull python:3.11-slim

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.dev.yml up --build

echo "✅ IntelliStore restart complete!"