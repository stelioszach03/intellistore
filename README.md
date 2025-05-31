# IntelliStore

🚀 **AI-Driven Cloud-Native Distributed Object Storage System**

IntelliStore is a modern, intelligent object storage system that combines distributed storage with machine learning for optimal data tiering and management. Built for high performance, scalability, and ease of use.

## ✨ Features

- **🧠 AI-Powered Tiering**: Machine learning algorithms automatically optimize data placement between hot and cold storage tiers
- **🔄 Distributed Architecture**: Fault-tolerant distributed storage with erasure coding
- **⚡ High Performance**: Built with Go and optimized for speed and efficiency
- **🌐 RESTful API**: Complete REST API with FastAPI for all storage operations
- **📊 Real-time Monitoring**: Built-in metrics and monitoring capabilities
- **🔒 Secure**: Authentication, authorization, and encryption support
- **🎯 Easy Deployment**: Simple setup without Docker dependencies

## 🏗️ Architecture

IntelliStore consists of five main components:

1. **Core Storage Engine** (Go) - Distributed storage with Raft consensus
2. **API Gateway** (Python/FastAPI) - RESTful API for client interactions
3. **ML Service** (Python) - Intelligent tiering predictions
4. **Tier Controller** (Go) - Manages data movement between tiers
5. **Frontend Dashboard** (React/TypeScript) - Web-based management interface

## 📋 Prerequisites

Before installing IntelliStore, ensure you have the following installed:

- **Python 3.8+** - [Download Python](https://python.org/downloads/)
- **Node.js 16+** - [Download Node.js](https://nodejs.org/)
- **Go 1.19+** - [Download Go](https://golang.org/dl/)

### Platform Support

✅ **Linux** (Ubuntu, CentOS, RHEL, etc.)  
✅ **macOS** (Intel and Apple Silicon)  
✅ **Windows** (Windows 10/11)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/stelioszach03/intellistore.git
cd intellistore
```

### 2. Run Setup

The setup script will automatically install all dependencies and configure virtual environments:

```bash
# On Linux/macOS
python3 setup.py

# On Windows
python setup.py
```

### 3. Start IntelliStore

```bash
# On Linux/macOS
./start.sh

# On Windows
start.bat
```

That's it! 🎉 IntelliStore will start all components automatically.

## 🌐 Access Points

Once started, you can access:

- **Frontend Dashboard**: http://localhost:51017
- **API Documentation**: http://localhost:8000/docs
- **API Endpoint**: http://localhost:8000
- **ML Service**: http://localhost:8002
- **Core Storage**: http://localhost:8001

## 📖 Detailed Setup

### Manual Setup (Advanced Users)

If you prefer to set up components manually:

#### 1. Setup API Service

```bash
cd intellistore-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Setup ML Service

```bash
cd intellistore-ml
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Setup Core Storage

```bash
cd intellistore-core
go mod download
go build -o bin/ ./cmd/...
```

#### 4. Setup Tier Controller

```bash
cd intellistore-tier-controller
go mod download
go build -o bin/ ./cmd/...
```

#### 5. Setup Frontend

```bash
cd intellistore-frontend
npm install
```

## 🎮 Usage

### Starting Individual Components

You can start components individually for development:

```bash
# Start API Server
cd intellistore-api
./venv/bin/python main.py

# Start ML Service
cd intellistore-ml
./venv/bin/python simple_main.py

# Start Core Storage
cd intellistore-core
./bin/server -mode=storage -id=node1

# Start Frontend
cd intellistore-frontend
npm run dev
```

### Management Commands

```bash
# Check status of all components
./start.sh status

# Stop all components
./start.sh stop

# Restart all components
./start.sh restart

# View logs
./start.sh logs api-server
./start.sh logs ml-service
./start.sh logs frontend
```

### API Usage Examples

#### Upload a File

```bash
curl -X POST "http://localhost:8000/buckets/my-bucket/objects/my-file.txt" \
  -H "Content-Type: text/plain" \
  -d "Hello, IntelliStore!"
```

#### Download a File

```bash
curl "http://localhost:8000/buckets/my-bucket/objects/my-file.txt"
```

#### List Objects

```bash
curl "http://localhost:8000/buckets/my-bucket/objects"
```

#### Get ML Prediction

```bash
curl -X POST "http://localhost:8002/predict/event" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "my-bucket",
    "object_key": "my-file.txt",
    "size": 1024,
    "content_type": "text/plain"
  }'
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Key configuration options:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Security
JWT_SECRET=your-secret-key-here

# CORS Origins
ALLOWED_ORIGINS=http://localhost:51017,http://localhost:3000

# Storage Configuration
DATA_SHARDS=6
PARITY_SHARDS=3
MAX_FILE_SIZE=10737418240

# ML Configuration
ML_INFERENCE_URL=http://localhost:8002
HOT_THRESHOLD=0.8
```

### Component Ports

| Component | Default Port | Description |
|-----------|--------------|-------------|
| Frontend | 51017 | Web dashboard |
| API Server | 8000 | REST API |
| Core Storage | 8001 | Storage engine |
| ML Service | 8002 | ML predictions |
| Tier Controller | 8003 | Data tiering |

## 🔧 Development

### Project Structure

```
intellistore/
├── intellistore-api/          # FastAPI REST API service
├── intellistore-core/         # Go storage engine
├── intellistore-ml/           # Python ML service
├── intellistore-tier-controller/ # Go tier management
├── intellistore-frontend/     # React dashboard
├── setup.py                   # Cross-platform setup script
├── start.sh                   # Unix startup script
├── start.bat                  # Windows startup script
├── .env.example              # Configuration template
└── README.md                 # This file
```

### Adding New Features

1. **API Endpoints**: Add to `intellistore-api/app/api/`
2. **Storage Logic**: Modify `intellistore-core/internal/`
3. **ML Models**: Update `intellistore-ml/src/`
4. **Frontend Components**: Add to `intellistore-frontend/src/`

### Running Tests

```bash
# API Tests
cd intellistore-api
./venv/bin/python -m pytest

# Frontend Tests
cd intellistore-frontend
npm test

# Go Tests
cd intellistore-core
go test ./...
```

## 📊 Monitoring

### Health Checks

- API Health: http://localhost:8000/health
- ML Health: http://localhost:8002/health
- Metrics: http://localhost:8000/metrics

### Logs

Logs are stored in the `logs/` directory:

- `api-server.log` - API service logs
- `ml-service.log` - ML service logs
- `core-server.log` - Storage engine logs
- `frontend.log` - Frontend development logs

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000  # On Linux/macOS
netstat -ano | findstr :8000  # On Windows

# Kill the process
kill -9 <PID>  # On Linux/macOS
taskkill /PID <PID> /F  # On Windows
```

#### Python Virtual Environment Issues

```bash
# Remove and recreate virtual environment
rm -rf intellistore-api/venv
cd intellistore-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Go Build Issues

```bash
# Clean and rebuild
cd intellistore-core
go clean -cache
go mod download
go build -o bin/ ./cmd/...
```

#### Frontend Issues

```bash
# Clear cache and reinstall
cd intellistore-frontend
rm -rf node_modules package-lock.json
npm install
```

### Getting Help

1. Check the logs in the `logs/` directory
2. Verify all prerequisites are installed
3. Ensure no other services are using the required ports
4. Check the GitHub issues page for known problems

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) for the API layer
- Uses [React](https://reactjs.org/) and [Vite](https://vitejs.dev/) for the frontend
- Powered by [Go](https://golang.org/) for high-performance storage
- Machine learning with [scikit-learn](https://scikit-learn.org/)

---

**IntelliStore** - Intelligent storage for the modern world 🌟