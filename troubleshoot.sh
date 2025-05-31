#!/bin/bash

echo "🔍 IntelliStore Troubleshooting Guide"
echo "===================================="

echo ""
echo "1. 🐳 Docker Status:"
docker --version
docker-compose --version

echo ""
echo "2. 📦 Current containers:"
docker ps -a

echo ""
echo "3. 🖼️ Current images:"
docker images | grep intellistore

echo ""
echo "4. 🌐 Network connectivity test:"
echo "Testing Docker registry connectivity..."
docker pull hello-world:latest && echo "✅ Docker registry accessible" || echo "❌ Docker registry not accessible"

echo ""
echo "5. 💾 Disk space:"
df -h

echo ""
echo "6. 🔧 Common fixes:"
echo "   - If build fails with 'failed to resolve source metadata':"
echo "     Run: docker system prune -a"
echo "     Then: docker pull node:18 && docker pull golang:1.21"
echo ""
echo "   - If containers can't communicate:"
echo "     Check docker-compose.dev.yml service names match"
echo ""
echo "   - If ports are in use:"
echo "     Run: docker-compose -f docker-compose.dev.yml down"
echo ""
echo "   - For complete reset:"
echo "     Run: ./restart-intellistore.sh"

echo ""
echo "7. 📋 Service URLs (when running):"
echo "   Frontend: http://localhost:53641"
echo "   API: http://localhost:8000"
echo "   Grafana: http://localhost:3000"
echo "   Prometheus: http://localhost:9090"
echo "   Vault: http://localhost:8200"