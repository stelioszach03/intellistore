# IntelliStore Makefile

.PHONY: help setup dev build test clean start stop status

# Default target
help:
	@echo "IntelliStore Development Commands"
	@echo "================================="
	@echo "setup        - Set up development environment"
	@echo "dev          - Start local development environment"
	@echo "build        - Build all components"
	@echo "test         - Run all tests"
	@echo "test-unit    - Run unit tests only"
	@echo "test-integration - Run integration tests"
	@echo "lint         - Run linters on all code"
	@echo "clean        - Clean up development environment"
	@echo "start        - Start all services"
	@echo "stop         - Stop all services"
	@echo "status       - Check service status"

# Setup development environment
setup:
	@echo "Setting up IntelliStore development environment..."
	python3 setup.py

# Development environment
dev: setup start

# Build all components
build:
	@echo "Building all components..."
	@echo "Building Go components..."
	cd intellistore-core && go build -o bin/intellistore-server cmd/server/main.go
	cd intellistore-tier-controller && go build -o bin/simple_tier_controller cmd/simple_main.go
	@echo "Installing Python dependencies..."
	cd intellistore-api && python -m pip install -r requirements.txt
	cd intellistore-ml && python -m pip install -r requirements.txt
	@echo "Installing Node.js dependencies..."
	cd intellistore-frontend && npm install
	@echo "Build complete!"

# Start all services
start:
	@echo "Starting IntelliStore..."
	./start.sh

# Stop all services
stop:
	@echo "Stopping IntelliStore..."
	./start.sh stop

# Check service status
status:
	@echo "Checking IntelliStore status..."
	./start.sh status

# Run tests
test: test-unit

test-unit:
	@echo "Running unit tests..."
	@if [ -d "intellistore-core" ]; then cd intellistore-core && go test ./... || true; fi
	@if [ -d "intellistore-api" ] && [ -f "intellistore-api/venv/bin/activate" ]; then \
		cd intellistore-api && source venv/bin/activate && python -m pytest tests/ || true; \
	fi
	@if [ -d "intellistore-ml" ] && [ -f "intellistore-ml/venv/bin/activate" ]; then \
		cd intellistore-ml && source venv/bin/activate && python -m pytest tests/ || true; \
	fi
	@if [ -d "intellistore-tier-controller" ]; then cd intellistore-tier-controller && go test ./... || true; fi
	@if [ -d "intellistore-frontend" ] && [ -d "intellistore-frontend/node_modules" ]; then \
		cd intellistore-frontend && npm test -- --watchAll=false || true; \
	fi

test-integration:
	@echo "Running integration tests..."
	@echo "Integration tests require all services to be running"
	@echo "Use 'make start' first, then run integration tests manually"

# Linting
lint:
	@echo "Running linters..."
	@if [ -d "intellistore-core" ]; then cd intellistore-core && go fmt ./... && go vet ./...; fi
	@if [ -d "intellistore-api" ] && [ -f "intellistore-api/venv/bin/activate" ]; then \
		cd intellistore-api && source venv/bin/activate && black . && flake8 . || true; \
	fi
	@if [ -d "intellistore-ml" ] && [ -f "intellistore-ml/venv/bin/activate" ]; then \
		cd intellistore-ml && source venv/bin/activate && black . && flake8 . || true; \
	fi
	@if [ -d "intellistore-tier-controller" ]; then cd intellistore-tier-controller && go fmt ./... && go vet ./...; fi
	@if [ -d "intellistore-frontend" ] && [ -d "intellistore-frontend/node_modules" ]; then \
		cd intellistore-frontend && npm run lint || true; \
	fi

# Clean up
clean:
	@echo "Cleaning up development environment..."
	./start.sh stop || true
	@echo "Removing virtual environments..."
	rm -rf intellistore-api/venv intellistore-ml/venv
	@echo "Removing build artifacts..."
	rm -rf intellistore-core/bin intellistore-tier-controller/bin
	rm -rf intellistore-frontend/node_modules intellistore-frontend/dist
	rm -rf logs/ data/
	@echo "Clean complete!"

# Install dependencies only
deps:
	@echo "Installing dependencies..."
	python3 setup.py --deps-only