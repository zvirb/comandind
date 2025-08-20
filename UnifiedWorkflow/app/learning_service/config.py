"""
Learning Service Configuration
============================

Configuration management for the learning service including
Neo4j, Qdrant, Redis, and learning engine parameters.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LearningConfig(BaseSettings):
    """Learning service configuration with environment variable support."""
    
    # Service Configuration
    port: int = Field(default=8005, env="LEARNING_PORT")
    log_level: str = Field(default="INFO", env="LEARNING_LOG_LEVEL") 
    debug: bool = Field(default=False, env="LEARNING_DEBUG")
    
    # Neo4j Knowledge Graph Configuration
    neo4j_url: str = Field(default="bolt://neo4j:7687", env="LEARNING_NEO4J_URL")
    neo4j_auth: str = Field(env="LEARNING_NEO4J_AUTH", description="Neo4j authentication in format username/password")
    neo4j_database: str = Field(default="neo4j", env="LEARNING_NEO4J_DATABASE")
    
    # Qdrant Vector Database Configuration  
    qdrant_url: str = Field(default="http://qdrant:6333", env="LEARNING_QDRANT_URL")
    qdrant_collection: str = Field(default="learning_patterns", env="LEARNING_QDRANT_COLLECTION")
    qdrant_vector_size: int = Field(default=384, env="LEARNING_QDRANT_VECTOR_SIZE")
    
    # Redis Configuration - Uses shared Redis with authentication
    redis_url: str = Field(
        default=os.getenv("REDIS_URL", "redis://lwe-app:${REDIS_PASSWORD}@redis:6379/2"),
        env="LEARNING_REDIS_URL"
    )
    redis_db: int = Field(default=2, env="LEARNING_REDIS_DB")
    
    # Service Integration URLs
    reasoning_service_url: str = Field(
        default="http://reasoning-service:8003", 
        env="LEARNING_REASONING_SERVICE_URL"
    )
    coordination_service_url: str = Field(
        default="http://coordination-service:8004",
        env="LEARNING_COORDINATION_SERVICE_URL"
    )
    hybrid_memory_url: str = Field(
        default="http://hybrid-memory-service:8002",
        env="LEARNING_HYBRID_MEMORY_URL"
    )
    
    # Learning Engine Configuration
    pattern_recognition_threshold: float = Field(
        default=0.80, env="LEARNING_PATTERN_THRESHOLD"
    )
    application_success_threshold: float = Field(
        default=0.75, env="LEARNING_APPLICATION_THRESHOLD"
    )
    similarity_threshold: float = Field(
        default=0.85, env="LEARNING_SIMILARITY_THRESHOLD"
    )
    confidence_threshold: float = Field(
        default=0.70, env="LEARNING_CONFIDENCE_THRESHOLD"
    )
    
    # Enhanced Performance Configuration
    max_concurrent_requests: int = Field(
        default=25, env="LEARNING_MAX_CONCURRENT"
    )
    learning_batch_size: int = Field(
        default=50, env="LEARNING_BATCH_SIZE"
    )
    pattern_cache_ttl: int = Field(
        default=3600, env="LEARNING_PATTERN_CACHE_TTL"
    )
    knowledge_graph_cache_ttl: int = Field(
        default=1800, env="LEARNING_KG_CACHE_TTL"
    )
    
    # Async Pattern Recognition Optimization
    async_pattern_processing: bool = Field(
        default=True, env="LEARNING_ASYNC_PATTERN_PROCESSING"
    )
    pattern_processing_workers: int = Field(
        default=4, env="LEARNING_PATTERN_PROCESSING_WORKERS"
    )
    knowledge_graph_connection_pool: int = Field(
        default=10, env="LEARNING_KG_CONNECTION_POOL"
    )
    vector_db_batch_size: int = Field(
        default=100, env="LEARNING_VECTOR_DB_BATCH_SIZE"
    )
    
    # Learning Strategy Configuration
    meta_learning_enabled: bool = Field(
        default=True, env="LEARNING_META_LEARNING_ENABLED"
    )
    pattern_generalization_enabled: bool = Field(
        default=True, env="LEARNING_PATTERN_GENERALIZATION_ENABLED"
    )
    anomaly_detection_enabled: bool = Field(
        default=True, env="LEARNING_ANOMALY_DETECTION_ENABLED"
    )
    performance_prediction_enabled: bool = Field(
        default=True, env="LEARNING_PERFORMANCE_PREDICTION_ENABLED"
    )
    
    # Learning Rate and Adaptation
    learning_rate: float = Field(default=0.1, env="LEARNING_RATE")
    adaptation_rate: float = Field(default=0.05, env="LEARNING_ADAPTATION_RATE")
    pattern_decay_rate: float = Field(default=0.01, env="LEARNING_PATTERN_DECAY_RATE")
    
    # Monitoring and Metrics
    monthly_improvement_target: float = Field(
        default=0.10, env="LEARNING_MONTHLY_IMPROVEMENT_TARGET"
    )
    pattern_storage_limit: int = Field(
        default=100000, env="LEARNING_PATTERN_STORAGE_LIMIT"
    )
    
    @field_validator('neo4j_auth')
    @classmethod
    def validate_neo4j_auth(cls, v):
        """Validate Neo4j authentication format."""
        if '/' not in v:
            raise ValueError("Neo4j auth must be in format 'username/password'")
        return v
    
    @field_validator('pattern_recognition_threshold', 'application_success_threshold', 
               'similarity_threshold', 'confidence_threshold')
    @classmethod
    def validate_thresholds(cls, v):
        """Validate threshold values are between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Threshold values must be between 0 and 1")
        return v
    
    @field_validator('learning_rate', 'adaptation_rate', 'pattern_decay_rate')
    @classmethod
    def validate_rates(cls, v):
        """Validate rate values are between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Rate values must be between 0 and 1")
        return v
    
    @property
    def neo4j_username(self) -> str:
        """Extract username from neo4j_auth."""
        return self.neo4j_auth.split('/')[0]
    
    @property  
    def neo4j_password(self) -> str:
        """Extract password from neo4j_auth."""
        return self.neo4j_auth.split('/')[1]
    
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "allow"}


# Global configuration instance
config = LearningConfig()