"""Configuration management for the Perception Service.

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
    port: int = Field(default=8001, description="Service port")
    host: str = Field(default="0.0.0.0", description="Service host")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Ollama Configuration
    ollama_url: str = Field(
        default="http://ollama:11434",
        description="Ollama service URL"
    )
    ollama_model: str = Field(
        default="llava",
        description="Ollama model name for image analysis"
    )
    ollama_timeout: int = Field(
        default=120,
        description="Ollama request timeout in seconds"
    )
    ollama_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for Ollama requests"
    )
    
    # Vector Configuration
    vector_dimensions: int = Field(
        default=1536,
        description="Output vector dimensions"
    )
    
    # Performance Configuration
    max_image_size_mb: int = Field(
        default=10,
        description="Maximum image size in MB"
    )
    max_concurrent_requests: int = Field(
        default=10,
        description="Maximum concurrent processing requests"
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
    
    # Default prompt for image conceptualization
    default_prompt: str = Field(
        default="Describe this image in detail, focusing on key visual concepts, objects, actions, and scene elements that would be useful for semantic search and similarity matching.",
        description="Default prompt for image analysis"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is acceptable."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()
    
    @validator('vector_dimensions')
    def validate_vector_dimensions(cls, v):
        """Validate vector dimensions are positive."""
        if v <= 0:
            raise ValueError('Vector dimensions must be positive')
        return v
    
    @validator('max_image_size_mb')
    def validate_max_image_size(cls, v):
        """Validate max image size is reasonable."""
        if v <= 0 or v > 100:
            raise ValueError('Max image size must be between 1 and 100 MB')
        return v
    
    @validator('ollama_timeout')
    def validate_ollama_timeout(cls, v):
        """Validate Ollama timeout is reasonable."""
        if v <= 0 or v > 300:
            raise ValueError('Ollama timeout must be between 1 and 300 seconds')
        return v
    
    class Config:
        env_prefix = "PERCEPTION_"
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
        max_concurrent_requests=20,
        enable_metrics=True
    )


def get_development_settings() -> Settings:
    """Get development-friendly settings."""
    return Settings(
        debug=True,
        log_level="DEBUG",
        cors_origins=["*"],
        max_concurrent_requests=5,
        ollama_timeout=60
    )