"""
Configuration management for IntelliStore API
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Security
    secret_key: str = Field(description="Secret key for JWT signing")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    
    # CORS
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins"
    )
    
    # Vault configuration
    vault_addr: str = Field(description="HashiCorp Vault address")
    vault_token: str = Field(description="Vault authentication token")
    vault_mount_point: str = Field(default="intellistore", description="Vault mount point")
    
    # Raft metadata service
    raft_leader_addr: str = Field(description="Raft leader address")
    raft_timeout: int = Field(default=10, description="Raft request timeout in seconds")
    
    # Storage nodes
    storage_nodes: List[str] = Field(description="List of storage node addresses")
    
    # Kafka configuration
    kafka_brokers: List[str] = Field(description="Kafka broker addresses")
    kafka_access_logs_topic: str = Field(default="access-logs", description="Access logs topic")
    kafka_tiering_topic: str = Field(default="tiering-requests", description="Tiering requests topic")
    
    # Database (if needed for caching)
    database_url: Optional[str] = Field(default=None, description="Database URL for caching")
    
    # Redis (for caching and sessions)
    redis_url: Optional[str] = Field(default=None, description="Redis URL")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # File upload limits
    max_file_size: int = Field(default=10 * 1024 * 1024 * 1024, description="Max file size (10GB)")
    max_chunk_size: int = Field(default=64 * 1024 * 1024, description="Max chunk size (64MB)")
    
    # Erasure coding configuration
    data_shards: int = Field(default=6, description="Number of data shards")
    parity_shards: int = Field(default=3, description="Number of parity shards")
    
    # ML tiering configuration
    ml_inference_url: str = Field(
        default="http://ml-inference:8000",
        description="ML inference service URL"
    )
    hot_threshold: float = Field(default=0.8, description="Hot tier prediction threshold")
    
    # WebSocket configuration
    websocket_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Environment variable mappings
        fields = {
            "secret_key": {"env": "JWT_SECRET"},
            "vault_addr": {"env": "VAULT_ADDR"},
            "vault_token": {"env": "VAULT_TOKEN"},
            "raft_leader_addr": {"env": "RAFT_LEADER_ADDR"},
            "storage_nodes": {"env": "STORAGE_NODES"},
            "kafka_brokers": {"env": "KAFKA_BROKERS"},
            "database_url": {"env": "DATABASE_URL"},
            "redis_url": {"env": "REDIS_URL"},
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Development settings
class DevelopmentSettings(Settings):
    """Development-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    
    # Override with development defaults
    vault_addr: str = "http://vault:8200"
    vault_token: str = "dev-root-token"
    raft_leader_addr: str = "raft-metadata-0:8080"
    storage_nodes: List[str] = [
        "storage-node-0:8080",
        "storage-node-1:8081", 
        "storage-node-2:8082"
    ]
    kafka_brokers: List[str] = ["kafka:9092"]
    secret_key: str = "dev-secret-key-change-in-production"


# Production settings
class ProductionSettings(Settings):
    """Production-specific settings"""
    debug: bool = False
    log_level: str = "INFO"
    
    # Security settings for production
    allowed_origins: List[str] = []  # Must be explicitly set
    
    class Config(Settings.Config):
        # Require all sensitive settings in production
        fields = {
            **Settings.Config.fields,
            "secret_key": {"env": "JWT_SECRET"},  # Required
            "vault_token": {"env": "VAULT_TOKEN"},  # Required
        }


def get_settings_for_environment(env: str = None) -> Settings:
    """Get settings for specific environment"""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    if env.lower() == "production":
        return ProductionSettings()
    elif env.lower() == "development":
        return DevelopmentSettings()
    else:
        return Settings()