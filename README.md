# IntelliStore: AI-Driven Cloud-Native Distributed Object Storage

IntelliStore is a production-ready, cloud-native distributed object storage system that combines advanced features like Reed-Solomon erasure coding, client-side encryption, AI-driven hot/cold tiering, and a modern React frontend.

## 🚀 Features

- **Distributed Architecture**: Raft-based metadata consensus with multiple storage nodes
- **Data Protection**: Reed-Solomon erasure coding (6 data + 3 parity shards)
- **Security**: Client-side AES-GCM encryption with HashiCorp Vault key management
- **AI-Driven Tiering**: Machine learning models predict access patterns for automatic hot/cold migration
- **Cloud-Native**: Kubernetes-native deployment with Helm charts
- **Observability**: Prometheus metrics, Grafana dashboards, and real-time alerting
- **Modern UI**: React TypeScript frontend with Tailwind CSS and real-time updates

## 📁 Project Structure

```
intellistore/
├── intellistore-core/          # Core storage engine (Go)
├── intellistore-api/           # REST API service (FastAPI/Python)
├── intellistore-ml/            # ML training and inference (Python)
├── intellistore-tier-controller/ # Tiering orchestration (Go)
├── intellistore-frontend/      # React TypeScript UI
├── intellistore-vault-config/  # Vault configuration
├── intellistore-helm/          # Kubernetes Helm charts
├── intellistore-iac/           # Terraform infrastructure
├── secguard-intellistore/      # Security scanning
└── intellistore-helm-values/   # Environment-specific values
```

## 🛠️ Quick Start

### Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (local: kind/k3d, cloud: EKS/GKE/AKS)
- Helm 3.x
- Terraform (for cloud deployment)

### Local Development

```bash
# Clone and setup
git clone <repository-url>
cd intellistore

# Start local development environment
make dev

# Access the UI
open http://localhost:3000
```

### Production Deployment

```bash
# Deploy to Kubernetes
helm upgrade --install intellistore ./intellistore-helm \
  --namespace intellistore \
  --create-namespace \
  -f intellistore-helm-values/values.production.yaml

# Verify deployment
kubectl get pods -n intellistore
```

## 🏗️ Architecture

IntelliStore follows a microservices architecture:

1. **Metadata Service**: Raft consensus cluster storing object metadata
2. **Storage Nodes**: Distributed nodes storing encrypted shards
3. **API Gateway**: FastAPI service handling client requests
4. **ML Pipeline**: Training and inference for access pattern prediction
5. **Tier Controller**: Orchestrates hot/cold data migration
6. **Frontend**: React SPA with real-time monitoring

## 📊 Monitoring

- **Metrics**: Prometheus scrapes all services
- **Dashboards**: Grafana provides cluster health, storage utilization, and ML insights
- **Alerting**: Automated alerts for node failures, capacity issues, and performance degradation

## 🔒 Security

- **Encryption**: All data encrypted client-side with AES-GCM
- **Key Management**: HashiCorp Vault manages encryption keys
- **mTLS**: Service-to-service communication secured with mutual TLS
- **RBAC**: Kubernetes RBAC and Vault policies control access

## 📈 Scalability

- **Horizontal Scaling**: Add storage nodes dynamically
- **Load Balancing**: API requests distributed across replicas
- **Auto-scaling**: Kubernetes HPA scales based on CPU/memory usage
- **Multi-region**: Deploy across availability zones for high availability

## 🧪 Testing

```bash
# Run all tests
make test

# Integration tests
make test-integration

# End-to-end tests
make test-e2e
```

## 📚 Documentation

- [API Documentation](./docs/api.md)
- [Deployment Guide](./docs/deployment.md)
- [Development Setup](./docs/development.md)
- [Architecture Deep Dive](./docs/architecture.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🆘 Support

- [GitHub Issues](https://github.com/your-org/intellistore/issues)
- [Documentation](https://intellistore.docs.example.com)
- [Community Slack](https://intellistore-community.slack.com)