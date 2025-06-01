# IntelliStore API

FastAPI-based REST API for the IntelliStore distributed storage system.

## Configuration

The API server requires configuration through environment variables. There are several ways to provide configuration:

### 1. Development (Recommended)
For development, the API will automatically use `.env.development` which contains safe defaults:
```bash
# No additional setup needed - just run the server
./venv/bin/python main.py
```

### 2. Custom Environment File
Create a `.env` file (which will be ignored by git):
```bash
cp .env.example .env
# Edit .env with your specific values
```

### 3. Environment Variables
Set environment variables directly:
```bash
export JWT_SECRET="your-secret-key"
export PORT=8092
./venv/bin/python main.py
```

## Required Configuration

The following environment variables are **required**:

- `JWT_SECRET`: Secret key for JWT token signing (must be set for security)

## Optional Configuration

- `PORT`: Server port (default: 8092)
- `HOST`: Server host (default: 0.0.0.0)
- `DEBUG`: Enable debug mode (default: false)
- `ENVIRONMENT`: Environment name (development/production)
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)
- `RAFT_LEADER_ADDR`: Raft cluster leader address
- `STORAGE_NODES`: Storage node addresses (comma-separated)
- `ML_INFERENCE_URL`: ML service URL for tiering decisions

## Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The API will be available at:
- API: http://localhost:8092
- API Documentation: http://localhost:8092/docs
- OpenAPI Schema: http://localhost:8092/openapi.json

## Troubleshooting

### JWT_SECRET Missing Error
If you see the error:
```
ValidationError: 1 validation error for Settings
JWT_SECRET
  Field required
```

This means the JWT_SECRET environment variable is not set. Either:
1. Use the provided `.env.development` file (automatic)
2. Create a `.env` file with `JWT_SECRET=your-secret-key`
3. Set the environment variable: `export JWT_SECRET="your-secret-key"`