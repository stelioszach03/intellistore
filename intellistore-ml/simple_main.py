#!/usr/bin/env python3
"""
Simplified ML Inference Service for IntelliStore
Works without external dependencies like Kafka
"""

import json
import time
import os
from typing import Dict, Any, Optional
import logging

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class PredictionRequest(BaseModel):
    features: Dict[str, float] = Field(..., description="Feature values for prediction")

class PredictionResponse(BaseModel):
    prediction: str = Field(..., description="Predicted tier: 'hot' or 'cold'")
    confidence: float = Field(..., description="Prediction confidence (0-1)")
    probability_hot: float = Field(..., description="Probability of being hot")
    probability_cold: float = Field(..., description="Probability of being cold")
    model_version: str = Field(..., description="Model version used")

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float

class SimpleTieringEvent(BaseModel):
    timestamp: Optional[float] = None
    bucket_name: str
    object_key: str
    size: int
    current_tier: Optional[str] = "cold"
    user: Optional[str] = "unknown"
    content_type: Optional[str] = "application/octet-stream"

class SimpleMLService:
    """Simplified ML service with rule-based predictions"""
    
    def __init__(self):
        self.start_time = time.time()
        self.model_version = "1.0.0-simple"
        self.initialized = False
        
    async def initialize(self):
        """Initialize the service"""
        logger.info("Initializing simplified ML service")
        self.initialized = True
        logger.info("ML service initialized successfully")
    
    def predict_from_features(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Make prediction from feature dictionary"""
        try:
            # Simple rule-based prediction
            # In a real implementation, this would use a trained model
            
            # Extract key features
            size = features.get('size', 0)
            hour_of_day = features.get('hour_of_day', 12)
            is_business_hours = features.get('is_business_hours', 1)
            is_media = features.get('is_media', 0)
            object_age_days = features.get('object_age_days', 1)
            
            # Simple scoring algorithm
            score = 0.5  # Base score
            
            # Size factor (smaller files more likely to be hot)
            if size < 1024 * 1024:  # < 1MB
                score += 0.2
            elif size < 10 * 1024 * 1024:  # < 10MB
                score += 0.1
            elif size > 100 * 1024 * 1024:  # > 100MB
                score -= 0.1
            
            # Time factor (business hours more likely to be hot)
            if is_business_hours:
                score += 0.15
            
            # Media files often accessed repeatedly
            if is_media:
                score += 0.1
            
            # Age factor (newer files more likely to be hot)
            if object_age_days < 1:
                score += 0.2
            elif object_age_days < 7:
                score += 0.1
            elif object_age_days > 30:
                score -= 0.2
            
            # Ensure score is between 0 and 1
            score = max(0.0, min(1.0, score))
            
            # Determine prediction
            predicted_tier = "hot" if score > 0.6 else "cold"
            confidence = abs(score - 0.5) * 2  # Convert to confidence
            
            return {
                "prediction": predicted_tier,
                "confidence": confidence,
                "probability_hot": score,
                "probability_cold": 1.0 - score,
                "model_version": self.model_version
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
    def extract_features_from_event(self, event: SimpleTieringEvent) -> Dict[str, float]:
        """Extract features from a tiering event"""
        current_time = time.time()
        if event.timestamp is None:
            event.timestamp = current_time
        
        # Extract basic features
        features = {
            'hour_of_day': float(time.localtime(current_time).tm_hour),
            'day_of_week': float(time.localtime(current_time).tm_wday),
            'is_weekend': float(time.localtime(current_time).tm_wday >= 5),
            'is_business_hours': float(9 <= time.localtime(current_time).tm_hour <= 17),
            'object_age_days': (current_time - event.timestamp) / (24 * 3600),
            'size': float(event.size),
            'is_media': float(event.content_type.startswith(('image/', 'video/', 'audio/'))),
            'user_activity_level': 5.0,  # Default value
            'bucket_popularity': 3.0,     # Default value
            'access_count_7d': 2.0,       # Default value
            'download_count_7d': 1.0,     # Default value
            'unique_users_7d': 1.0,       # Default value
            'avg_daily_access': 0.3,      # Default value
            'last_access_hours_ago': 24.0, # Default value
            'recent_access_trend': 1.0,   # Default value
        }
        
        return features
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "status": "healthy" if self.initialized else "initializing",
            "model_loaded": self.initialized,
            "model_version": self.model_version,
            "uptime_seconds": time.time() - self.start_time
        }

# Global service instance
ml_service = SimpleMLService()

# FastAPI app
app = FastAPI(
    title="IntelliStore ML Inference Service",
    description="Simplified ML service for hot/cold object tiering predictions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the service on startup"""
    await ml_service.initialize()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    health_data = ml_service.get_health()
    return HealthResponse(**health_data)

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make a prediction from features"""
    if not ml_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = ml_service.predict_from_features(request.features)
    return PredictionResponse(**result)

@app.post("/predict/event", response_model=PredictionResponse)
async def predict_from_event(event: SimpleTieringEvent):
    """Make a prediction from a tiering event"""
    if not ml_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Extract features from event
    features = ml_service.extract_features_from_event(event)
    
    # Make prediction
    result = ml_service.predict_from_features(features)
    return PredictionResponse(**result)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "IntelliStore ML Inference Service",
        "version": "1.0.0",
        "description": "Simplified ML service for object tiering predictions",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "predict_event": "/predict/event",
            "docs": "/docs"
        }
    }

@app.get("/metrics")
async def metrics():
    """Simple metrics endpoint"""
    return {
        "service": "ml-inference",
        "uptime_seconds": time.time() - ml_service.start_time,
        "status": "healthy" if ml_service.initialized else "initializing",
        "model_version": ml_service.model_version
    }

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "simple_main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )