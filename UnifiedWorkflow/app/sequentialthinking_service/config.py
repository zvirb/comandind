"""
Configuration settings for Sequential Thinking Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Service Configuration
    SERVICE_NAME: str = "sequentialthinking-service"
    PORT: int = 8002
    DEBUG: bool = False
    
    # Redis Configuration for Checkpointing
    REDIS_URL: str = "redis://redis:6379"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 1  # Use separate DB for checkpoints
    REDIS_KEY_PREFIX: str = "st_checkpoint:"
    
    # Memory Service Integration
    MEMORY_SERVICE_URL: str = "http://memory-service:8001"
    
    # Ollama Configuration
    OLLAMA_URL: str = "https://ollama:11435"
    OLLAMA_PRIMARY_MODEL: str = "llama3:8b-instruct-q4_0"
    OLLAMA_BACKUP_MODEL: str = "phi3:mini-instruct"
    OLLAMA_REASONING_TIMEOUT: int = 300  # 5 minutes
    
    # LangGraph Configuration
    MAX_THINKING_STEPS: int = 20
    MAX_RETRY_ATTEMPTS: int = 3
    CHECKPOINT_SAVE_FREQUENCY: int = 1  # Save after every step
    ENABLE_SELF_HEALING: bool = True
    
    # Authentication
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # mTLS Configuration
    MTLS_ENABLED: bool = True
    MTLS_CA_CERT_FILE: Optional[str] = None
    MTLS_CERT_FILE: Optional[str] = None
    MTLS_KEY_FILE: Optional[str] = None
    
    # Performance Settings
    CONCURRENT_REASONING_LIMIT: int = 5
    MEMORY_CACHE_SIZE: int = 1000
    RESPONSE_TIMEOUT: int = 60
    CHECKPOINT_EXPIRATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load secrets from files if specified
        if not self.REDIS_PASSWORD and os.path.exists("/run/secrets/REDIS_PASSWORD"):
            with open("/run/secrets/REDIS_PASSWORD", "r") as f:
                self.REDIS_PASSWORD = f.read().strip()
        
        if not self.JWT_SECRET_KEY and os.path.exists("/run/secrets/JWT_SECRET_KEY"):
            with open("/run/secrets/JWT_SECRET_KEY", "r") as f:
                self.JWT_SECRET_KEY = f.read().strip()


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings