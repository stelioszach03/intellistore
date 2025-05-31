#!/bin/bash

# IntelliStore Setup Validation Script
# Checks if all components are properly configured

echo "🔍 Validating IntelliStore Setup..."
echo "=================================="

ERRORS=0

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Docker is installed"
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Docker Compose is installed"
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Docker daemon is running"
fi

# Check required files
FILES=(
    "docker-compose.dev.yml"
    "intellistore-api/Dockerfile"
    "intellistore-api/main.py"
    "intellistore-api/requirements.txt"
    "intellistore-core/Dockerfile"
    "intellistore-core/cmd/server/main.go"
    "intellistore-core/go.mod"
    "intellistore-frontend/Dockerfile.dev"
    "intellistore-frontend/package.json"
    "intellistore-frontend/vite.config.ts"
    "intellistore-ml/Dockerfile.inference"
    "intellistore-ml/src/inference/main.py"
    "intellistore-ml/requirements.txt"
    "intellistore-tier-controller/Dockerfile"
    "intellistore-tier-controller/cmd/main.go"
    "intellistore-tier-controller/go.mod"
    "monitoring/prometheus.yml"
    "intellistore-vault-config/policies/intellistore-policy.hcl"
)

echo ""
echo "📁 Checking required files..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (missing)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check port availability
echo ""
echo "🔌 Checking port availability..."
PORTS=(53641 8000 8001 8002 8200 9090 3001 5432 6379 9092 2181)

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is in use"
    else
        echo "✅ Port $port is available"
    fi
done

# Check system resources
echo ""
echo "💾 Checking system resources..."

# Check available memory (in MB)
if command -v free &> /dev/null; then
    MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$MEMORY" -lt 4096 ]; then
        echo "⚠️  Available memory: ${MEMORY}MB (recommended: 8GB+)"
    else
        echo "✅ Available memory: ${MEMORY}MB"
    fi
fi

# Check available disk space
DISK_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$DISK_SPACE" -lt 10 ]; then
    echo "⚠️  Available disk space: ${DISK_SPACE}GB (recommended: 10GB+)"
else
    echo "✅ Available disk space: ${DISK_SPACE}GB"
fi

echo ""
echo "=================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All checks passed! Ready to start IntelliStore."
    echo ""
    echo "🚀 To start the system, run:"
    echo "   ./start-intellistore.sh"
    echo ""
    echo "   OR manually:"
    echo "   docker-compose -f docker-compose.dev.yml up -d"
else
    echo "❌ Found $ERRORS issues. Please fix them before starting."
fi
echo "=================================="