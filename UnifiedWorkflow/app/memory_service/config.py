"""Configuration management for the Hybrid Memory Service.

Environment-based configuration with validation and sensible defaults.
"""

import os
from typing import List
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Service Configuration
    port: int = Field(default=8002, description="Service port")
    host: str = Field(default="0.0.0.0", description="Service host")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Database Configuration - PostgreSQL (shared AI Workflow DB)
    database_url: str = Field(
        default=os.getenv("DATABASE_URL", "postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db"),
        description="PostgreSQL database URL - uses shared AI Workflow database"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=30,
        description="Database pool max overflow connections"
    )
    
    # Qdrant Configuration
    qdrant_url: str = Field(
        default="http://qdrant:6333",
        description="Qdrant vector database URL"
    )
    qdrant_collection_name: str = Field(
        default="hybrid_memory_vectors",
        description="Qdrant collection name for memory vectors"
    )
    qdrant_vector_size: int = Field(
        default=1536,
        description="Vector dimensions for Qdrant"
    )
    qdrant_timeout: int = Field(
        default=30,
        description="Qdrant request timeout in seconds"
    )
    
    # Ollama Configuration
    ollama_url: str = Field(
        default="http://ollama:11434",
        description="Ollama service URL"
    )
    ollama_model: str = Field(
        default="llama3.2:3b",
        description="Ollama model name for text processing"
    )
    ollama_timeout: int = Field(
        default=120,
        description="Ollama request timeout in seconds"
    )
    ollama_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for Ollama requests"
    )
    
    # Memory Pipeline Configuration
    extraction_prompt: str = Field(
        default="Extract and summarize the key information, concepts, and relationships from this text. Focus on actionable insights, facts, and contextual knowledge that would be valuable for future retrieval.",
        description="Prompt for memory extraction phase"
    )
    reconciliation_prompt: str = Field(
        default="Compare and reconcile this new memory with existing related memories. Identify overlaps, contradictions, and complementary information. Provide a refined summary that integrates the new information coherently.",
        description="Prompt for memory reconciliation phase"
    )
    
    # Performance Configuration
    max_memory_size_chars: int = Field(
        default=10000,
        description="Maximum memory text size in characters"
    )
    max_concurrent_requests: int = Field(
        default=15,
        description="Maximum concurrent processing requests"
    )
    similarity_threshold: float = Field(
        default=0.75,
        description="Similarity threshold for memory reconciliation"
    )
    max_related_memories: int = Field(
        default=5,
        description="Maximum number of related memories to consider for reconciliation"
    )
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Monitoring Configuration
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    
    # Search Configuration
    default_search_limit: int = Field(
        default=10,
        description="Default number of results for memory search"
    )
    max_search_limit: int = Field(
        default=100,
        description="Maximum number of results for memory search"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is acceptable."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    @validator('qdrant_vector_size')
    def validate_vector_size(cls, v):
        """Validate vector dimensions are positive."""
        if v <= 0:
            raise ValueError('Vector dimensions must be positive')
        return v
    
    @validator('max_memory_size_chars')
    def validate_max_memory_size(cls, v):
        """Validate max memory size is reasonable."""
        if v <= 0 or v > 100000:
            raise ValueError('Max memory size must be between 1 and 100000 characters')
        return v
    
    @validator('similarity_threshold')
    def validate_similarity_threshold(cls, v):
        """Validate similarity threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Similarity threshold must be between 0.0 and 1.0')
        return v
    
    @validator('database_pool_size')
    def validate_pool_size(cls, v):
        """Validate database pool size is reasonable."""
        if v <= 0 or v > 100:
            raise ValueError('Database pool size must be between 1 and 100')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Environment-specific configurations
def get_production_settings() -> Settings:
    """Get production-optimized settings."""
    return Settings(
        debug=False,
        log_level="WARNING",
        cors_origins=["https://aiwfe.example.com"],
        max_concurrent_requests=25,
        enable_metrics=True,
        database_pool_size=30,
        database_max_overflow=50
    )


def get_development_settings() -> Settings:
    """Get development-friendly settings."""
    return Settings(
        debug=True,
        log_level="DEBUG",
        cors_origins=["*"],
        max_concurrent_requests=10,
        ollama_timeout=60,
        database_pool_size=10,
        database_max_overflow=15
    )