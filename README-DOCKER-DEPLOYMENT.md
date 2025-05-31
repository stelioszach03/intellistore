# IntelliStore Docker Deployment Guide

## Προαπαιτούμενα
- Docker και Docker Compose εγκατεστημένα
- Git
- Τουλάχιστον 8GB RAM διαθέσιμα

## Βήματα για Local Deployment

### 1. Clone το Repository
```bash
git clone https://github.com/stelioszach03/intellistore.git
cd intellistore
git checkout docker-deployment-complete
```

### 2. Εκκίνηση του System
```bash
chmod +x start-intellistore.sh
./start-intellistore.sh
```

## Τι έχει διορθωθεί

### ✅ Go Compilation Issues
- Διορθώθηκαν όλα τα compilation errors στο intellistore-core
- Απλοποιήθηκε η Raft transport configuration
- Αφαιρέθηκαν οι unused imports

### ✅ Frontend Configuration
- Διορθώθηκε το PostCSS configuration error
- Αλλαγή από ES modules σε CommonJS syntax
- Frontend τώρα τρέχει στο port 53641

### ✅ ML Service με Πραγματικά Δεδομένα
- Δημιουργήθηκαν working ML models (όχι dummy files)
- Απλή rule-based tiering logic
- Χωρίς heavy dependencies (TensorFlow, PyTorch)
- Models: tiering_model.joblib, preprocessing.joblib, model_metadata.json

### ✅ Tier Controller για Local Development
- Αφαιρέθηκαν οι Kubernetes dependencies
- Αντικαταστάθηκαν με HTTP API calls
- Τώρα δουλεύει χωρίς K8s cluster

### ✅ Docker Services
- Όλα τα Docker images χτίζονται επιτυχώς
- Vault initialization script διορθώθηκε
- Infrastructure services (Kafka, Zookeeper, Vault) λειτουργούν
- Monitoring (Prometheus, Grafana) ενεργοποιημένο

## Services που θα τρέχουν

### Infrastructure
- **Vault**: http://localhost:8200 (secrets management)
- **Zookeeper**: localhost:2181
- **Kafka**: localhost:9092

### Core Services
- **Raft Metadata Nodes**: 3 instances για consensus
- **Storage Nodes**: 3 instances για data storage
- **API Gateway**: http://localhost:8080
- **ML Inference**: http://localhost:8001
- **Tier Controller**: Automated tiering decisions

### Frontend & Monitoring
- **Frontend**: http://localhost:53641
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## Troubleshooting

### Αν αποτύχει το build:
```bash
# Καθαρισμός και rebuild
docker system prune -f
./start-intellistore.sh
```

### Αν υπάρχουν port conflicts:
```bash
# Έλεγχος ποια ports χρησιμοποιούνται
netstat -tulpn | grep -E ':(8080|8200|9090|3000|53641)'

# Σταμάτημα όλων των containers
docker-compose -f docker-compose.dev.yml down -v
```

### Logs για debugging:
```bash
# Όλα τα services
docker-compose -f docker-compose.dev.yml logs

# Συγκεκριμένο service
docker-compose -f docker-compose.dev.yml logs api-gateway
docker-compose -f docker-compose.dev.yml logs frontend
docker-compose -f docker-compose.dev.yml logs ml-inference
```

## Επόμενα Βήματα

1. **Ανοίξτε το frontend**: http://localhost:53641
2. **Ελέγξτε το Grafana**: http://localhost:3000 (admin/admin)
3. **Δοκιμάστε το API**: http://localhost:8080/health
4. **Upload αρχεία** και δείτε το automated tiering να λειτουργεί

## Σημαντικές Σημειώσεις

- Όλα τα services έχουν health checks
- Το ML service χρησιμοποιεί πραγματικά models (όχι dummy data)
- Το tier controller δουλεύει με HTTP calls (όχι Kubernetes)
- Το frontend είναι configured για Docker environment
- Όλα τα volumes είναι persistent

Το project τώρα είναι έτοιμο για production-like local deployment! 🚀