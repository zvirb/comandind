"""
Configuration for Infrastructure Recovery Service
Predictive monitoring and automated recovery settings
"""
import os
from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class InfrastructureRecoveryConfig(BaseSettings):
    """Configuration for infrastructure recovery and predictive monitoring"""
    
    # Service Configuration
    SERVICE_NAME: str = "infrastructure-recovery-service"
    PORT: int = Field(default=8010, env="RECOVERY_SERVICE_PORT")
    HOST: str = Field(default="0.0.0.0", env="RECOVERY_SERVICE_HOST")
    
    # Redis Configuration Components
    REDIS_HOST: str = Field(default="redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=4, env="REDIS_DB")
    REDIS_USER: str = Field(default="lwe-app", env="REDIS_USER")
    REDIS_PASSWORD: str = Field(default="", env="REDIS_PASSWORD")
    
    # Database and Monitoring
    DATABASE_URL: str = Field(default="postgresql://app_user:password@postgres:5432/ai_workflow_db", env="DATABASE_URL")
    
    # Monitoring URLs
    PROMETHEUS_URL: str = Field(default="http://prometheus:9090", env="PROMETHEUS_URL")
    ALERTMANAGER_URL: str = Field(default="http://alertmanager:9093", env="ALERTMANAGER_URL")
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components"""
        if self.REDIS_PASSWORD:
            return f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Predictive Monitoring Configuration
    HEALTH_SCORE_THRESHOLD: float = Field(default=0.7, description="Minimum health score before intervention")
    PREDICTION_WINDOW_MINUTES: int = Field(default=15, description="Time window for failure prediction")
    ML_MODEL_UPDATE_INTERVAL: int = Field(default=3600, description="Model update interval in seconds")
    FEATURE_COLLECTION_INTERVAL: int = Field(default=30, description="Feature collection interval in seconds")
    
    # Recovery Configuration
    MAX_RECOVERY_ATTEMPTS: int = Field(default=3, description="Maximum recovery attempts per incident")
    RECOVERY_TIMEOUT_SECONDS: int = Field(default=300, description="Timeout for recovery operations")
    COOLDOWN_PERIOD_SECONDS: int = Field(default=600, description="Cooldown between recovery attempts")
    
    # Auto-scaling Configuration
    SCALE_UP_THRESHOLD: float = Field(default=0.8, description="Resource utilization threshold for scaling up")
    SCALE_DOWN_THRESHOLD: float = Field(default=0.3, description="Resource utilization threshold for scaling down")
    AUTO_SCALING_ENABLED: bool = Field(default=True, env="AUTO_SCALING_ENABLED")
    
    # Service Dependencies
    MONITORED_SERVICES: List[str] = Field(default=[
        "postgres", "redis", "qdrant", "ollama", "api", "webui", 
        "worker", "coordination-service", "hybrid-memory-service",
        "learning-service", "perception-service", "reasoning-service"
    ])
    
    # Critical Service Dependencies
    CRITICAL_SERVICE_DEPENDENCIES: Dict[str, List[str]] = Field(default={
        "api": ["postgres", "redis", "qdrant", "ollama"],
        "worker": ["postgres", "redis", "ollama", "qdrant"],
        "webui": ["api"],
        "coordination-service": ["postgres", "redis", "qdrant"],
        "hybrid-memory-service": ["postgres", "qdrant", "ollama"],
        "learning-service": ["postgres", "redis", "qdrant", "ollama"],
        "perception-service": ["ollama"],
        "reasoning-service": ["postgres", "redis", "ollama"]
    })
    
    # Health Check Endpoints
    SERVICE_HEALTH_ENDPOINTS: Dict[str, str] = Field(default={
        "api": "http://api:8000/health",
        "webui": "http://webui:3001/health",
        "coordination-service": "http://coordination-service:8001/health",
        "hybrid-memory-service": "http://hybrid-memory-service:8002/health",
        "learning-service": "http://learning-service:8003/health",
        "perception-service": "http://perception-service:8004/health",
        "reasoning-service": "http://reasoning-service:8005/health",
        "postgres": "pg_isready check",
        "redis": "redis ping check",
        "qdrant": "https://qdrant:6333/healthz",
        "ollama": "http://ollama:11434/"
    })
    
    # Recovery Actions Configuration
    RECOVERY_ACTIONS: Dict[str, List[str]] = Field(default={
        "restart_container": ["docker", "restart"],
        "scale_service": ["docker-compose", "scale"],
        "clear_cache": ["redis-cli", "flushdb"],
        "rebuild_index": ["qdrant", "recreate_collection"],
        "restart_ollama": ["docker", "restart", "ollama"],
        "database_maintenance": ["psql", "vacuum", "analyze"]
    })
    
    # Rollback Configuration
    ROLLBACK_ENABLED: bool = Field(default=True, env="ROLLBACK_ENABLED")
    ROLLBACK_SNAPSHOT_INTERVAL: int = Field(default=1800, description="Snapshot interval for rollback")
    MAX_ROLLBACK_SNAPSHOTS: int = Field(default=10, description="Maximum rollback snapshots to keep")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Global configuration instance with proper initialization
infrastructure_recovery_config = InfrastructureRecoveryConfig()

# Ensure configuration is refreshed if needed
def refresh_config():
    """Refresh the global configuration instance"""
    global infrastructure_recovery_config
    infrastructure_recovery_config = InfrastructureRecoveryConfig()