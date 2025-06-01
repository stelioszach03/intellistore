"""
Configuration management for IntelliStore API
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host", alias="HOST")
    port: int = Field(default=8000, description="Server port", alias="PORT")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Security
    secret_key: str = Field(description="Secret key for JWT signing", alias="JWT_SECRET")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    
    # CORS
    allowed_origins_str: str = Field(
        default="http://localhost:51090,http://localhost:3000",
        description="Allowed CORS origins (comma-separated)",
        alias="ALLOWED_ORIGINS"
    )
    
    # Vault configuration (optional for development)
    vault_addr: Optional[str] = Field(default=None, description="HashiCorp Vault address", alias="VAULT_ADDR")
    vault_token: Optional[str] = Field(default=None, description="Vault authentication token", alias="VAULT_TOKEN")
    vault_mount_point: str = Field(default="intellistore", description="Vault mount point")
    
    # Raft metadata service
    raft_leader_addr: str = Field(default="localhost:8001", description="Raft leader address", alias="RAFT_LEADER_ADDR")
    raft_timeout: int = Field(default=10, description="Raft request timeout in seconds")
    
    # Storage nodes
    storage_nodes_str: str = Field(default="localhost:8001", description="Storage node addresses (comma-separated)", alias="STORAGE_NODES")
    
    # Kafka configuration (optional for development)
    kafka_brokers_str: Optional[str] = Field(default=None, description="Kafka broker addresses (comma-separated)", alias="KAFKA_BROKERS")
    kafka_access_logs_topic: str = Field(default="access-logs", description="Access logs topic")
    kafka_tiering_topic: str = Field(default="tiering-requests", description="Tiering requests topic")
    
    # Database (if needed for caching)
    database_url: Optional[str] = Field(default=None, description="Database URL for caching", alias="DATABASE_URL")
    
    # Redis (for caching and sessions)
    redis_url: Optional[str] = Field(default=None, description="Redis URL", alias="REDIS_URL")
    
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
        default="http://localhost:8002",
        description="ML inference service URL"
    )
    hot_threshold: float = Field(default=0.8, description="Hot tier prediction threshold")
    
    # WebSocket configuration
    websocket_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")
    
    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string"""
        return [item.strip() for item in self.allowed_origins_str.split(',') if item.strip()]
    
    @property
    def storage_nodes(self) -> List[str]:
        """Parse storage nodes from comma-separated string"""
        return [item.strip() for item in self.storage_nodes_str.split(',') if item.strip()]
    
    @property
    def kafka_brokers(self) -> Optional[List[str]]:
        """Parse kafka brokers from comma-separated string"""
        if self.kafka_brokers_str is None:
            return None
        return [item.strip() for item in self.kafka_brokers_str.split(',') if item.strip()]
    
    model_config = {
        "env_file": [".env", ".env.development"],
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "env_parse_none_str": "None"
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
    allowed_origins_str: str = Field(default="", description="Allowed CORS origins (comma-separated)", alias="ALLOWED_ORIGINS")  # Must be explicitly set


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