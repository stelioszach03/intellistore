#!/usr/bin/env python3
"""
Simplified IntelliStore API for demonstration
This is a standalone version that doesn't require external services
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
SECRET_KEY = "dev-secret-key-for-demo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mock data
USERS_DB = {
    "admin": {
        "username": "admin",
        "email": "admin@intellistore.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # admin123
        "roles": ["admin", "user"]
    },
    "user": {
        "username": "user",
        "email": "user@intellistore.com", 
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # admin123
        "roles": ["user"]
    }
}

BUCKETS_DB = [
    {
        "name": "documents",
        "created_at": "2024-01-15T10:30:00Z",
        "size": 1024 * 1024 * 150,  # 150MB
        "object_count": 25,
        "tier": "hot",
        "encryption": True
    },
    {
        "name": "images",
        "created_at": "2024-01-10T14:20:00Z", 
        "size": 1024 * 1024 * 1024 * 2,  # 2GB
        "object_count": 150,
        "tier": "warm",
        "encryption": True
    },
    {
        "name": "backups",
        "created_at": "2024-01-01T09:00:00Z",
        "size": 1024 * 1024 * 1024 * 10,  # 10GB
        "object_count": 5,
        "tier": "cold",
        "encryption": True
    }
]

OBJECTS_DB = {
    "documents": [
        {
            "name": "report.pdf",
            "size": 1024 * 1024 * 5,  # 5MB
            "last_modified": "2024-01-20T15:30:00Z",
            "tier": "hot",
            "content_type": "application/pdf"
        },
        {
            "name": "presentation.pptx",
            "size": 1024 * 1024 * 12,  # 12MB
            "last_modified": "2024-01-19T11:45:00Z",
            "tier": "hot",
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
    ],
    "images": [
        {
            "name": "photo1.jpg",
            "size": 1024 * 1024 * 3,  # 3MB
            "last_modified": "2024-01-18T16:20:00Z",
            "tier": "warm",
            "content_type": "image/jpeg"
        },
        {
            "name": "logo.png",
            "size": 1024 * 256,  # 256KB
            "last_modified": "2024-01-17T09:15:00Z",
            "tier": "hot",
            "content_type": "image/png"
        }
    ]
}

METRICS_DATA = {
    "storage": {
        "total_capacity": 1024 * 1024 * 1024 * 100,  # 100GB
        "used_capacity": 1024 * 1024 * 1024 * 12,    # 12GB
        "available_capacity": 1024 * 1024 * 1024 * 88, # 88GB
        "utilization_percentage": 12.0
    },
    "performance": {
        "requests_per_second": 145.2,
        "average_response_time": 0.025,
        "throughput_mbps": 89.5,
        "error_rate": 0.001
    },
    "tiering": {
        "hot_tier_usage": 1024 * 1024 * 1024 * 3,    # 3GB
        "warm_tier_usage": 1024 * 1024 * 1024 * 5,   # 5GB
        "cold_tier_usage": 1024 * 1024 * 1024 * 4,   # 4GB
        "ml_predictions_accuracy": 94.5
    }
}

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserInfo(BaseModel):
    username: str
    email: Optional[str] = None
    roles: List[str] = []

class BucketInfo(BaseModel):
    name: str
    created_at: str
    size: int
    object_count: int
    tier: str
    encryption: bool

class ObjectInfo(BaseModel):
    name: str
    size: int
    last_modified: str
    tier: str
    content_type: str

# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = USERS_DB.get(username)
    if user is None:
        raise credentials_exception
    return user

# Create FastAPI app
app = FastAPI(
    title="IntelliStore API (Demo)",
    description="Simplified IntelliStore API for demonstration",
    version="1.0.0-demo"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:53641", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
async def root():
    return {
        "service": "IntelliStore API (Demo)",
        "version": "1.0.0-demo",
        "description": "AI-Driven Cloud-Native Distributed Object Storage",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0-demo"
    }

@app.post("/auth/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    user = USERS_DB.get(login_request.username)
    if not user or not verify_password(login_request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return UserInfo(
        username=current_user["username"],
        email=current_user["email"],
        roles=current_user["roles"]
    )

@app.get("/buckets", response_model=List[BucketInfo])
async def list_buckets(current_user: dict = Depends(get_current_user)):
    return BUCKETS_DB

@app.get("/buckets/{bucket_name}/objects", response_model=List[ObjectInfo])
async def list_objects(bucket_name: str, current_user: dict = Depends(get_current_user)):
    if bucket_name not in OBJECTS_DB:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return OBJECTS_DB[bucket_name]

@app.get("/monitoring/metrics")
async def get_metrics(current_user: dict = Depends(get_current_user)):
    return METRICS_DATA

@app.get("/monitoring/dashboard")
async def get_dashboard_data(current_user: dict = Depends(get_current_user)):
    return {
        "buckets": len(BUCKETS_DB),
        "total_objects": sum(bucket["object_count"] for bucket in BUCKETS_DB),
        "total_size": sum(bucket["size"] for bucket in BUCKETS_DB),
        "metrics": METRICS_DATA
    }

if __name__ == "__main__":
    print("Starting IntelliStore Demo API...")
    print("Available users:")
    print("  - admin / admin123 (admin role)")
    print("  - user / admin123 (user role)")
    print()
    
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )