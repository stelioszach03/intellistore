# IntelliStore Makefile

.PHONY: help dev build test clean deploy

# Default target
help:
	@echo "IntelliStore Development Commands"
	@echo "================================="
	@echo "dev          - Start local development environment"
	@echo "build        - Build all Docker images"
	@echo "test         - Run all tests"
	@echo "test-unit    - Run unit tests only"
	@echo "test-integration - Run integration tests"
	@echo "test-e2e     - Run end-to-end tests"
	@echo "lint         - Run linters on all code"
	@echo "clean        - Clean up development environment"
	@echo "deploy-dev   - Deploy to development cluster"
	@echo "deploy-prod  - Deploy to production cluster"
	@echo "security-scan - Run security scans"

# Development environment
dev:
	@echo "Starting IntelliStore development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Services starting up..."
	@echo "Frontend: http://localhost:53641"
	@echo "API: http://localhost:8000"
	@echo "Grafana: http://localhost:3001"
	@echo "Vault: http://localhost:8200"

# Build all images
build:
	@echo "Building all Docker images..."
	docker build -t intellistore/core:latest ./intellistore-core
	docker build -t intellistore/api:latest ./intellistore-api
	docker build -t intellistore/ml:latest ./intellistore-ml
	docker build -t intellistore/tier-controller:latest ./intellistore-tier-controller
	docker build -t intellistore/frontend:latest ./intellistore-frontend

# Run tests
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	cd intellistore-core && go test ./...
	cd intellistore-api && python -m pytest tests/unit/
	cd intellistore-ml && python -m pytest tests/
	cd intellistore-tier-controller && go test ./...
	cd intellistore-frontend && npm test -- --watchAll=false

test-integration:
	@echo "Running integration tests..."
	cd intellistore-core && go test -tags=integration ./tests/integration/
	cd intellistore-api && python -m pytest tests/integration/

test-e2e:
	@echo "Running end-to-end tests..."
	./scripts/e2e-test.sh

# Linting
lint:
	@echo "Running linters..."
	cd intellistore-core && golangci-lint run
	cd intellistore-api && flake8 . && black --check .
	cd intellistore-ml && flake8 . && black --check .
	cd intellistore-tier-controller && golangci-lint run
	cd intellistore-frontend && npm run lint

# Security scanning
security-scan:
	@echo "Running security scans..."
	cd secguard-intellistore && ./scan.sh

# Clean up
clean:
	@echo "Cleaning up development environment..."
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

# Deployment
deploy-dev:
	@echo "Deploying to development cluster..."
	helm upgrade --install intellistore-dev ./intellistore-helm \
		--namespace intellistore-dev \
		--create-namespace \
		-f intellistore-helm-values/values.dev.yaml

deploy-prod:
	@echo "Deploying to production cluster..."
	helm upgrade --install intellistore ./intellistore-helm \
		--namespace intellistore \
		--create-namespace \
		-f intellistore-helm-values/values.production.yaml

# Setup development dependencies
setup:
	@echo "Setting up development environment..."
	# Install Go dependencies
	cd intellistore-core && go mod download
	cd intellistore-tier-controller && go mod download
	# Install Python dependencies
	cd intellistore-api && pip install -r requirements.txt -r requirements-dev.txt
	cd intellistore-ml && pip install -r requirements.txt
	# Install Node.js dependencies
	cd intellistore-frontend && npm install
	# Install tools
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	pip install black flake8 pytest

# Generate documentation
docs:
	@echo "Generating documentation..."
	cd intellistore-api && python -m pydoc-markdown
	cd intellistore-frontend && npm run build-storybook

# Database migrations (if needed)
migrate:
	@echo "Running database migrations..."
	# Add migration commands here if using a database

# Backup
backup:
	@echo "Creating backup..."
	kubectl exec -n intellistore deployment/vault -- vault operator raft snapshot save /tmp/vault-backup.snap
	kubectl cp intellistore/vault-0:/tmp/vault-backup.snap ./backups/vault-$(date +%Y%m%d-%H%M%S).snap