"""
IntelliStore API Service

FastAPI-based REST API for IntelliStore distributed object storage system.
Provides endpoints for bucket and object operations, authentication, and monitoring.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.api.auth import router as auth_router
from app.api.buckets import router as buckets_router
from app.api.objects import router as objects_router
from app.api.monitoring import router as monitoring_router
from app.api.websocket import router as websocket_router, periodic_status_updates
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.services.kafka_service import KafkaService
from app.services.vault_service import VaultService
from app.services.raft_service import RaftService

# Prometheus metrics (clear registry to prevent duplicates)
from prometheus_client import REGISTRY, CollectorRegistry
import prometheus_client

# Create a new registry to avoid conflicts
CUSTOM_REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    'intellistore_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code'],
    registry=CUSTOM_REGISTRY
)

REQUEST_DURATION = Histogram(
    'intellistore_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    registry=CUSTOM_REGISTRY
)

# Global services
kafka_service: KafkaService = None
vault_service: VaultService = None
raft_service: RaftService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_service, vault_service, raft_service
    
    settings = get_settings()
    logger = structlog.get_logger()
    
    # Initialize services
    logger.info("Initializing services...")
    
    try:
        # Initialize Vault service (optional)
        if settings.vault_addr and settings.vault_token:
            try:
                vault_service = VaultService(
                    vault_url=settings.vault_addr,
                    vault_token=settings.vault_token
                )
                await vault_service.initialize()
                logger.info("Vault service initialized")
            except Exception as e:
                logger.warning("Failed to initialize Vault service", error=str(e))
                vault_service = None
        else:
            logger.info("Vault service disabled (no configuration)")
            vault_service = None
        
        # Initialize Raft service (optional)
        try:
            raft_service = RaftService(
                leader_addr=settings.raft_leader_addr,
                storage_nodes=settings.storage_nodes
            )
            await raft_service.initialize()
            logger.info("Raft service initialized")
        except Exception as e:
            logger.warning("Failed to initialize Raft service", error=str(e))
            raft_service = None
        
        # Initialize Kafka service (optional)
        if settings.kafka_brokers:
            try:
                kafka_service = KafkaService(
                    bootstrap_servers=settings.kafka_brokers,
                    access_logs_topic=settings.kafka_access_logs_topic
                )
                await kafka_service.initialize()
                logger.info("Kafka service initialized")
            except Exception as e:
                logger.warning("Failed to initialize Kafka service", error=str(e))
                kafka_service = None
        else:
            logger.info("Kafka service disabled (no configuration)")
            kafka_service = None
        
        # Store services in app state
        app.state.kafka_service = kafka_service
        app.state.vault_service = vault_service
        app.state.raft_service = raft_service
        
        # Start background tasks
        try:
            asyncio.create_task(periodic_status_updates())
            logger.info("Background tasks started")
        except Exception as e:
            logger.warning("Failed to start background tasks", error=str(e))
        
        logger.info("Service initialization complete")
        
        yield
        
    except Exception as e:
        logger.error("Critical error during service initialization", error=str(e))
        # Don't raise - allow API to start even if some services fail
        yield
    finally:
        # Cleanup
        logger.info("Shutting down services...")
        if kafka_service:
            await kafka_service.close()
        if vault_service:
            await vault_service.close()
        if raft_service:
            await raft_service.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Setup logging
    setup_logging()
    logger = structlog.get_logger()
    
    settings = get_settings()
    
    app = FastAPI(
        title="IntelliStore API",
        description="AI-Driven Cloud-Native Distributed Object Storage API",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add request logging and metrics middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint info
        method = request.method
        path = request.url.path
        status_code = response.status_code
        
        # Update metrics
        REQUEST_COUNT.labels(
            method=method,
            endpoint=path,
            status_code=status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=path
        ).observe(duration)
        
        # Log request
        logger.info(
            "API request",
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            user_agent=request.headers.get("user-agent"),
            remote_addr=request.client.host if request.client else None
        )
        
        return response
    
    # Include routers
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(buckets_router, prefix="/buckets", tags=["Buckets"])
    app.include_router(objects_router, prefix="/buckets", tags=["Objects"])
    app.include_router(objects_router, prefix="/api/v1", tags=["Migration"])  # For migration endpoint
    app.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
    app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    
    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            generate_latest(CUSTOM_REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "IntelliStore API",
            "version": "1.0.0",
            "description": "AI-Driven Cloud-Native Distributed Object Storage",
            "docs": "/docs" if settings.debug else "Documentation disabled in production"
        }
    
    logger.info("FastAPI application created successfully")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
        access_log=True,
        server_header=False,
        date_header=False
    )