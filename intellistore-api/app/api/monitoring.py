"""
Monitoring and metrics API endpoints
"""

import time
from typing import Dict, Any, List

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.auth import get_current_user, UserInfo
from app.services.raft_service import RaftService
from app.services.kafka_service import KafkaService
from app.services.vault_service import VaultService

router = APIRouter()
logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: str
    timestamp: float
    services: Dict[str, Any]


class MetricsResponse(BaseModel):
    cluster_health: Dict[str, Any]
    storage_utilization: Dict[str, Any]
    ml_tiering: Dict[str, Any]
    api_metrics: Dict[str, Any]


class AlertResponse(BaseModel):
    alerts: List[Dict[str, Any]]
    total_count: int


def get_raft_service(request: Request) -> RaftService:
    """Get Raft service from app state"""
    return request.app.state.raft_service


def get_kafka_service(request: Request) -> KafkaService:
    """Get Kafka service from app state"""
    return request.app.state.kafka_service


def get_vault_service(request: Request) -> VaultService:
    """Get Vault service from app state"""
    return request.app.state.vault_service


@router.get("/health", response_model=HealthResponse)
async def health_check(
    raft_service: RaftService = Depends(get_raft_service),
    kafka_service: KafkaService = Depends(get_kafka_service),
    vault_service: VaultService = Depends(get_vault_service)
):
    """Comprehensive health check of all services"""
    logger.info("Performing health check")
    
    services = {}
    overall_status = "healthy"
    
    try:
        # Check Raft service
        raft_health = await raft_service.health_check()
        services["raft"] = raft_health
        if raft_health["status"] != "healthy":
            overall_status = "degraded"
        
        # Check Kafka service
        kafka_health = await kafka_service.health_check()
        services["kafka"] = kafka_health
        if kafka_health["status"] != "healthy":
            overall_status = "degraded"
        
        # Check Vault service
        vault_health = await vault_service.health_check()
        services["vault"] = vault_health
        if vault_health["status"] != "healthy":
            overall_status = "degraded"
        
        # Check storage nodes
        storage_nodes = await raft_service.get_storage_nodes()
        storage_health = []
        
        for node in storage_nodes[:3]:  # Check first 3 nodes
            try:
                # This would check individual storage node health
                node_health = {
                    "node": node,
                    "status": "healthy",
                    "last_check": time.time()
                }
                storage_health.append(node_health)
            except Exception as e:
                storage_health.append({
                    "node": node,
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": time.time()
                })
                overall_status = "degraded"
        
        services["storage_nodes"] = {
            "status": "healthy" if all(n["status"] == "healthy" for n in storage_health) else "degraded",
            "nodes": storage_health,
            "total_nodes": len(storage_nodes)
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        overall_status = "unhealthy"
        services["error"] = str(e)
    
    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        services=services
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """Get comprehensive system metrics"""
    logger.info("Fetching system metrics", user=current_user.username)
    
    try:
        # Cluster health metrics
        cluster_status = await raft_service.get_cluster_status()
        storage_nodes = await raft_service.get_storage_nodes()
        
        cluster_health = {
            "raft_state": cluster_status.get("state", "unknown"),
            "leader": cluster_status.get("leader", "unknown"),
            "commit_index": cluster_status.get("commitIndex", 0),
            "applied_index": cluster_status.get("appliedIndex", 0),
            "storage_nodes_count": len(storage_nodes),
            "healthy_nodes": len([n for n in storage_nodes if "healthy" in n])  # Simplified
        }
        
        # Storage utilization metrics
        storage_utilization = {
            "total_capacity": 1000000000000,  # 1TB demo
            "used_capacity": 250000000000,    # 250GB demo
            "ssd_usage": {
                "total": 500000000000,  # 500GB
                "used": 100000000000    # 100GB
            },
            "hdd_usage": {
                "total": 500000000000,  # 500GB
                "used": 150000000000    # 150GB
            },
            "nodes": [
                {
                    "node_id": "storage-0",
                    "tier": "ssd",
                    "capacity": 100000000000,
                    "used": 30000000000,
                    "usage_percent": 30.0
                },
                {
                    "node_id": "storage-1", 
                    "tier": "ssd",
                    "capacity": 100000000000,
                    "used": 40000000000,
                    "usage_percent": 40.0
                },
                {
                    "node_id": "storage-2",
                    "tier": "hdd", 
                    "capacity": 200000000000,
                    "used": 80000000000,
                    "usage_percent": 40.0
                }
            ]
        }
        
        # ML tiering metrics
        ml_tiering = {
            "predictions_last_hour": 150,
            "hot_predictions": 45,
            "cold_predictions": 105,
            "migrations_last_hour": 12,
            "successful_migrations": 11,
            "failed_migrations": 1,
            "model_accuracy": 0.87,
            "average_prediction_confidence": 0.82
        }
        
        # API metrics
        api_metrics = {
            "requests_last_hour": 1250,
            "successful_requests": 1200,
            "failed_requests": 50,
            "average_response_time": 0.145,
            "active_connections": 25,
            "upload_operations": 45,
            "download_operations": 180,
            "delete_operations": 12
        }
        
        return MetricsResponse(
            cluster_health=cluster_health,
            storage_utilization=storage_utilization,
            ml_tiering=ml_tiering,
            api_metrics=api_metrics
        )
        
    except Exception as e:
        logger.error("Failed to fetch metrics", error=str(e))
        raise


@router.get("/alerts", response_model=AlertResponse)
async def get_alerts(
    severity: str = "all",
    limit: int = 100,
    current_user: UserInfo = Depends(get_current_user)
):
    """Get active alerts"""
    logger.info("Fetching alerts", user=current_user.username, severity=severity)
    
    try:
        # In a real implementation, this would query Alertmanager
        # For demo, return sample alerts
        sample_alerts = [
            {
                "id": "alert-001",
                "name": "HighDiskUsage",
                "severity": "warning",
                "status": "firing",
                "description": "Storage node storage-2 disk usage is above 80%",
                "labels": {
                    "node": "storage-2",
                    "tier": "hdd",
                    "usage": "85%"
                },
                "fired_at": time.time() - 3600,  # 1 hour ago
                "annotations": {
                    "summary": "High disk usage detected",
                    "runbook_url": "https://docs.intellistore.com/alerts/high-disk-usage"
                }
            },
            {
                "id": "alert-002", 
                "name": "MLModelAccuracyLow",
                "severity": "warning",
                "status": "firing",
                "description": "ML tiering model accuracy has dropped below 85%",
                "labels": {
                    "model": "tiering-classifier",
                    "accuracy": "0.82"
                },
                "fired_at": time.time() - 1800,  # 30 minutes ago
                "annotations": {
                    "summary": "ML model performance degraded",
                    "runbook_url": "https://docs.intellistore.com/alerts/ml-accuracy"
                }
            },
            {
                "id": "alert-003",
                "name": "RaftLeaderElection", 
                "severity": "critical",
                "status": "resolved",
                "description": "Raft cluster underwent leader election",
                "labels": {
                    "cluster": "metadata",
                    "new_leader": "raft-metadata-1"
                },
                "fired_at": time.time() - 7200,  # 2 hours ago
                "resolved_at": time.time() - 6900,  # 1h 55m ago
                "annotations": {
                    "summary": "Leader election completed successfully",
                    "runbook_url": "https://docs.intellistore.com/alerts/leader-election"
                }
            }
        ]
        
        # Filter by severity
        if severity != "all":
            sample_alerts = [a for a in sample_alerts if a["severity"] == severity]
        
        # Apply limit
        alerts = sample_alerts[:limit]
        
        return AlertResponse(
            alerts=alerts,
            total_count=len(sample_alerts)
        )
        
    except Exception as e:
        logger.error("Failed to fetch alerts", error=str(e))
        raise


@router.get("/cluster/status")
async def get_cluster_status(
    current_user: UserInfo = Depends(get_current_user),
    raft_service: RaftService = Depends(get_raft_service)
):
    """Get detailed cluster status"""
    logger.info("Fetching cluster status", user=current_user.username)
    
    try:
        status = await raft_service.get_cluster_status()
        storage_nodes = await raft_service.get_storage_nodes()
        
        return {
            "raft_cluster": status,
            "storage_nodes": {
                "total": len(storage_nodes),
                "ssd_nodes": len([n for n in storage_nodes if "ssd" in n]),
                "hdd_nodes": len([n for n in storage_nodes if "hdd" in n]),
                "nodes": storage_nodes
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to get cluster status", error=str(e))
        raise


@router.get("/storage/utilization")
async def get_storage_utilization(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get detailed storage utilization"""
    logger.info("Fetching storage utilization", user=current_user.username)
    
    try:
        # In a real implementation, this would query storage nodes for actual usage
        return {
            "total_capacity": 1000000000000,  # 1TB
            "used_capacity": 250000000000,    # 250GB
            "available_capacity": 750000000000, # 750GB
            "usage_percentage": 25.0,
            "tiers": {
                "ssd": {
                    "capacity": 500000000000,
                    "used": 100000000000,
                    "available": 400000000000,
                    "usage_percentage": 20.0
                },
                "hdd": {
                    "capacity": 500000000000,
                    "used": 150000000000,
                    "available": 350000000000,
                    "usage_percentage": 30.0
                }
            },
            "growth_trend": {
                "daily_growth": 5000000000,  # 5GB per day
                "weekly_growth": 35000000000, # 35GB per week
                "projected_full": "2025-12-31"  # When storage will be full
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to get storage utilization", error=str(e))
        raise


@router.get("/ml/tiering/stats")
async def get_ml_tiering_stats(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get ML tiering statistics"""
    logger.info("Fetching ML tiering stats", user=current_user.username)
    
    try:
        # In a real implementation, this would query the ML service
        return {
            "model_info": {
                "name": "tiering-classifier",
                "version": "1.2.0",
                "algorithm": "XGBoost",
                "last_trained": "2025-05-30T10:00:00Z",
                "accuracy": 0.87,
                "precision": 0.85,
                "recall": 0.89,
                "f1_score": 0.87
            },
            "predictions": {
                "total_predictions": 15420,
                "hot_predictions": 4326,
                "cold_predictions": 11094,
                "average_confidence": 0.82,
                "predictions_last_24h": 1250
            },
            "migrations": {
                "total_migrations": 892,
                "successful_migrations": 875,
                "failed_migrations": 17,
                "migrations_last_24h": 45,
                "average_migration_time": 12.5,
                "data_migrated_gb": 2340.5
            },
            "performance": {
                "inference_latency_ms": 15.2,
                "throughput_predictions_per_second": 150,
                "model_size_mb": 12.8,
                "memory_usage_mb": 256
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Failed to get ML tiering stats", error=str(e))
        raise


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """Acknowledge an alert"""
    logger.info("Acknowledging alert", alert_id=alert_id, user=current_user.username)
    
    try:
        # In a real implementation, this would update Alertmanager
        return {
            "alert_id": alert_id,
            "acknowledged_by": current_user.username,
            "acknowledged_at": time.time(),
            "message": "Alert acknowledged successfully"
        }
        
    except Exception as e:
        logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
        raise


@router.post("/alerts/{alert_id}/silence")
async def silence_alert(
    alert_id: str,
    duration_hours: int = 1,
    current_user: UserInfo = Depends(get_current_user)
):
    """Silence an alert for a specified duration"""
    logger.info("Silencing alert", 
               alert_id=alert_id, 
               duration_hours=duration_hours,
               user=current_user.username)
    
    try:
        # In a real implementation, this would create a silence in Alertmanager
        return {
            "alert_id": alert_id,
            "silenced_by": current_user.username,
            "silenced_at": time.time(),
            "silence_until": time.time() + (duration_hours * 3600),
            "duration_hours": duration_hours,
            "message": f"Alert silenced for {duration_hours} hours"
        }
        
    except Exception as e:
        logger.error("Failed to silence alert", alert_id=alert_id, error=str(e))
        raise