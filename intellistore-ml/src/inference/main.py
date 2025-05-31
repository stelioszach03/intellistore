"""
ML Inference Service for IntelliStore Hot/Cold Tiering
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional

import joblib
import numpy as np
import onnxruntime as ort
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, KafkaProducer
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
INFERENCE_REQUESTS = Counter('ml_inference_requests_total', 'Total inference requests')
INFERENCE_LATENCY = Histogram('ml_inference_latency_seconds', 'Inference latency')
HOT_PREDICTIONS = Counter('ml_hot_predictions_total', 'Total hot predictions')
COLD_PREDICTIONS = Counter('ml_cold_predictions_total', 'Total cold predictions')
MODEL_LOAD_TIME = Gauge('ml_model_load_time_seconds', 'Model load time')
KAFKA_MESSAGES_PROCESSED = Counter('ml_kafka_messages_processed_total', 'Kafka messages processed')
KAFKA_PROCESSING_ERRORS = Counter('ml_kafka_processing_errors_total', 'Kafka processing errors')

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


class TieringEvent(BaseModel):
    timestamp: float
    bucket_name: str
    object_key: str
    size: int
    current_tier: str
    user: str
    content_type: str


class MLInferenceService:
    """ML Inference Service for hot/cold tiering predictions"""
    
    def __init__(self):
        self.model = None
        self.onnx_session = None
        self.preprocessing = None
        self.model_metadata = None
        self.feature_columns = None
        self.start_time = time.time()
        self.kafka_consumer = None
        self.kafka_producer = None
        self.running = False
        
    async def initialize(self):
        """Initialize the ML service"""
        try:
            logger.info("Initializing ML inference service")
            
            # Load model and preprocessing
            await self._load_model()
            
            # Initialize Kafka
            await self._initialize_kafka()
            
            logger.info("ML inference service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize ML service", error=str(e))
            raise
    
    async def _load_model(self):
        """Load the trained model and preprocessing objects"""
        try:
            start_time = time.time()
            
            # Load ONNX model (preferred for production)
            try:
                self.onnx_session = ort.InferenceSession("models/tiering_model.onnx")
                logger.info("Loaded ONNX model successfully")
            except Exception as e:
                logger.warning("Failed to load ONNX model, falling back to joblib", error=str(e))
                
                # Fallback to joblib model
                self.model = joblib.load("models/tiering_model.joblib")
                logger.info("Loaded joblib model successfully")
            
            # Load preprocessing objects
            self.preprocessing = joblib.load("models/preprocessing.joblib")
            self.feature_columns = self.preprocessing['feature_columns']
            
            # Load model metadata
            with open("models/model_metadata.json", 'r') as f:
                self.model_metadata = json.load(f)
            
            load_time = time.time() - start_time
            MODEL_LOAD_TIME.set(load_time)
            
            logger.info("Model loaded successfully", 
                       model_version=self.model_metadata.get('model_version', 'unknown'),
                       load_time=load_time,
                       features=len(self.feature_columns))
            
        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise
    
    async def _initialize_kafka(self):
        """Initialize Kafka consumer and producer"""
        try:
            # Kafka configuration
            kafka_brokers = ['kafka:9092']  # Update for your environment
            
            # Create consumer for tiering requests
            self.kafka_consumer = KafkaConsumer(
                'tiering-requests-input',
                bootstrap_servers=kafka_brokers,
                group_id='ml-inference-service',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            # Create producer for tiering decisions
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=kafka_brokers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            
            logger.info("Kafka initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Kafka", error=str(e))
            # Don't raise - service can still work for direct API calls
    
    def _extract_features(self, event_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from event data"""
        try:
            # Current time
            current_time = time.time()
            
            # Extract basic features
            features = {
                'hour_of_day': time.localtime(current_time).tm_hour,
                'day_of_week': time.localtime(current_time).tm_wday,
                'is_weekend': int(time.localtime(current_time).tm_wday >= 5),
                'is_business_hours': int(9 <= time.localtime(current_time).tm_hour <= 17),
                'object_age_days': (current_time - event_data.get('timestamp', current_time)) / (24 * 3600),
                'size': event_data.get('size', 0),
                'is_media': int(event_data.get('content_type', '').startswith(('image/', 'video/', 'audio/'))),
                'user_activity_level': 10,  # Default value - would be calculated from historical data
                'bucket_popularity': 5,     # Default value - would be calculated from historical data
                'access_count_7d': 2,       # Default value - would be calculated from historical data
                'download_count_7d': 1,     # Default value - would be calculated from historical data
                'unique_users_7d': 1,       # Default value - would be calculated from historical data
                'avg_daily_access': 0.3,    # Default value - would be calculated from historical data
                'last_access_hours_ago': 24, # Default value - would be calculated from historical data
                'recent_access_trend': 1.0, # Default value - would be calculated from historical data
            }
            
            # Handle categorical features
            current_tier = event_data.get('current_tier', 'hot')
            size_mb = features['size'] / (1024 * 1024)
            
            if size_mb < 1:
                size_category = 'small'
            elif size_mb < 100:
                size_category = 'medium'
            elif size_mb < 1000:
                size_category = 'large'
            else:
                size_category = 'xlarge'
            
            # Encode categorical features
            label_encoders = self.preprocessing['label_encoders']
            
            if 'size_category' in label_encoders:
                try:
                    features['size_category_encoded'] = label_encoders['size_category'].transform([size_category])[0]
                except ValueError:
                    features['size_category_encoded'] = 0  # Default for unknown categories
            
            if 'current_tier' in label_encoders:
                try:
                    features['current_tier_encoded'] = label_encoders['current_tier'].transform([current_tier])[0]
                except ValueError:
                    features['current_tier_encoded'] = 0  # Default for unknown categories
            
            # Create feature vector in the correct order
            feature_vector = []
            for col in self.feature_columns:
                feature_vector.append(features.get(col, 0))
            
            return np.array(feature_vector, dtype=np.float32).reshape(1, -1)
            
        except Exception as e:
            logger.error("Failed to extract features", error=str(e))
            raise
    
    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Make prediction using the loaded model"""
        try:
            with INFERENCE_LATENCY.time():
                INFERENCE_REQUESTS.inc()
                
                if self.onnx_session:
                    # Use ONNX model
                    input_name = self.onnx_session.get_inputs()[0].name
                    outputs = self.onnx_session.run(None, {input_name: features})
                    probabilities = outputs[1][0]  # Get probabilities
                    prediction = outputs[0][0]     # Get prediction
                else:
                    # Use scikit-learn model
                    probabilities = self.model.predict_proba(features)[0]
                    prediction = self.model.predict(features)[0]
                
                # Extract probabilities
                prob_cold = float(probabilities[0])
                prob_hot = float(probabilities[1])
                
                # Determine prediction
                predicted_tier = "hot" if prediction == 1 else "cold"
                confidence = max(prob_hot, prob_cold)
                
                # Update metrics
                if predicted_tier == "hot":
                    HOT_PREDICTIONS.inc()
                else:
                    COLD_PREDICTIONS.inc()
                
                return {
                    "prediction": predicted_tier,
                    "confidence": confidence,
                    "probability_hot": prob_hot,
                    "probability_cold": prob_cold,
                    "model_version": self.model_metadata.get('model_version', 'unknown')
                }
                
        except Exception as e:
            logger.error("Prediction failed", error=str(e))
            raise
    
    async def process_kafka_message(self, message):
        """Process a message from Kafka"""
        try:
            KAFKA_MESSAGES_PROCESSED.inc()
            
            event_data = message.value
            logger.debug("Processing Kafka message", 
                        bucket=event_data.get('bucket_name'),
                        object=event_data.get('object_key'))
            
            # Extract features
            features = self._extract_features(event_data)
            
            # Make prediction
            result = self.predict(features)
            
            # Check if object should be migrated to hot tier
            hot_threshold = 0.8  # Configurable threshold
            if result['probability_hot'] >= hot_threshold:
                # Publish migration request
                migration_request = {
                    'timestamp': time.time(),
                    'bucket_name': event_data.get('bucket_name'),
                    'object_key': event_data.get('object_key'),
                    'current_tier': event_data.get('current_tier', 'cold'),
                    'recommended_tier': 'hot',
                    'confidence': result['confidence'],
                    'probability_hot': result['probability_hot'],
                    'model_version': result['model_version']
                }
                
                if self.kafka_producer:
                    self.kafka_producer.send('tiering-requests', migration_request)
                    logger.info("Published hot tier migration request",
                               bucket=event_data.get('bucket_name'),
                               object=event_data.get('object_key'),
                               confidence=result['confidence'])
            
        except Exception as e:
            KAFKA_PROCESSING_ERRORS.inc()
            logger.error("Failed to process Kafka message", error=str(e))
    
    async def start_kafka_consumer(self):
        """Start consuming messages from Kafka"""
        if not self.kafka_consumer:
            logger.warning("Kafka consumer not initialized")
            return
        
        self.running = True
        logger.info("Starting Kafka consumer")
        
        try:
            while self.running:
                try:
                    # Poll for messages with timeout
                    message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            await self.process_kafka_message(message)
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error("Error in Kafka consumer loop", error=str(e))
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            logger.error("Kafka consumer failed", error=str(e))
        finally:
            if self.kafka_consumer:
                self.kafka_consumer.close()
            logger.info("Kafka consumer stopped")
    
    def stop_kafka_consumer(self):
        """Stop the Kafka consumer"""
        self.running = False
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "status": "healthy" if (self.model or self.onnx_session) else "unhealthy",
            "model_loaded": bool(self.model or self.onnx_session),
            "model_version": self.model_metadata.get('model_version', 'unknown') if self.model_metadata else 'unknown',
            "uptime_seconds": time.time() - self.start_time
        }


# Global service instance
ml_service = MLInferenceService()

# FastAPI app
app = FastAPI(
    title="IntelliStore ML Inference Service",
    description="Machine Learning service for hot/cold object tiering predictions",
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
    
    # Start Kafka consumer in background
    asyncio.create_task(ml_service.start_kafka_consumer())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    ml_service.stop_kafka_consumer()


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make a prediction for object tiering"""
    try:
        # Convert request to feature array
        feature_vector = []
        for col in ml_service.feature_columns:
            feature_vector.append(request.features.get(col, 0))
        
        features = np.array(feature_vector, dtype=np.float32).reshape(1, -1)
        
        # Make prediction
        result = ml_service.predict(features)
        
        return PredictionResponse(**result)
        
    except Exception as e:
        logger.error("Prediction endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/event")
async def predict_from_event(event: TieringEvent):
    """Make a prediction from a tiering event"""
    try:
        # Extract features from event
        features = ml_service._extract_features(event.dict())
        
        # Make prediction
        result = ml_service.predict(features)
        
        return PredictionResponse(**result)
        
    except Exception as e:
        logger.error("Event prediction failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    health = ml_service.get_health()
    return HealthResponse(**health)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")


@app.get("/model/info")
async def model_info():
    """Get model information"""
    if not ml_service.model_metadata:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "model_metadata": ml_service.model_metadata,
        "feature_columns": ml_service.feature_columns,
        "model_type": "ONNX" if ml_service.onnx_session else "scikit-learn"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)