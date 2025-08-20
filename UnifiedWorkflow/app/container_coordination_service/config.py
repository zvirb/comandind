"""Configuration for Container Coordination Service."""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class CoordinationConfig(BaseSettings):
    """Configuration for container coordination service."""
    
    # Service configuration
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8030, description="Port to bind to")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Docker configuration
    docker_socket: str = Field(
        default="unix://var/run/docker.sock",
        description="Docker socket path"
    )
    docker_api_version: str = Field(
        default="auto",
        description="Docker API version"
    )
    
    # Redis configuration for coordination
    redis_host: str = Field(
        default="redis",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port"
    )
    redis_db: int = Field(
        default=10,
        description="Redis database number for container coordination"
    )
    redis_password: str = Field(
        default=os.getenv("REDIS_PASSWORD", ""),
        description="Redis password"
    )
    
    # Container operation settings
    operation_timeout: int = Field(
        default=300,
        description="Maximum time for container operations in seconds"
    )
    lock_timeout: int = Field(
        default=600,
        description="Maximum time for resource locks in seconds"
    )
    conflict_detection_window: int = Field(
        default=30,
        description="Time window for conflict detection in seconds"
    )
    
    # Monitoring settings
    health_check_interval: int = Field(
        default=30,
        description="Health check interval in seconds"
    )
    state_update_interval: int = Field(
        default=5,
        description="Container state update interval in seconds"
    )
    operation_history_retention: int = Field(
        default=86400,
        description="Operation history retention time in seconds (24 hours)"
    )
    
    # Coordination settings
    max_concurrent_operations: int = Field(
        default=10,
        description="Maximum concurrent container operations"
    )
    max_queue_size: int = Field(
        default=100,
        description="Maximum operation queue size"
    )
    priority_levels: int = Field(
        default=5,
        description="Number of priority levels for operations"
    )
    
    # Emergency settings
    emergency_stop_timeout: int = Field(
        default=30,
        description="Emergency stop timeout in seconds"
    )
    force_unlock_timeout: int = Field(
        default=1800,
        description="Force unlock timeout in seconds (30 minutes)"
    )
    
    # Container patterns for coordination
    managed_containers: List[str] = Field(
        default=[
            "ai_workflow_engine-api-*",
            "ai_workflow_engine-worker-*",
            "ai_workflow_engine-webui-*",
            "ai_workflow_engine-postgres-*",
            "ai_workflow_engine-redis-*",
            "ai_workflow_engine-qdrant-*",
            "ai_workflow_engine-ollama-*",
            "ai_workflow_engine-coordination-service-*",
            "ai_workflow_engine-*-service-*"
        ],
        description="Container name patterns to manage"
    )
    
    excluded_containers: List[str] = Field(
        default=[
            "ai_workflow_engine-log-watcher-*",
            "ai_workflow_engine-caddy_reverse_proxy-*"
        ],
        description="Container patterns to exclude from coordination"
    )
    
    # Conflict types and handling
    conflicting_operations: dict = Field(
        default={
            "restart": ["restart", "stop", "kill", "update"],
            "stop": ["restart", "start", "update"],
            "start": ["stop", "kill"],
            "update": ["restart", "stop", "start", "kill"],
            "scale": ["restart", "stop", "update"],
            "backup": ["update", "stop", "kill"]
        },
        description="Operations that conflict with each other"
    )
    
    # Performance settings
    operation_batch_size: int = Field(
        default=5,
        description="Number of operations to process in batch"
    )
    coordination_loop_interval: float = Field(
        default=1.0,
        description="Coordination loop interval in seconds"
    )
    
    class Config:
        env_prefix = "CONTAINER_COORD_"
        case_sensitive = False