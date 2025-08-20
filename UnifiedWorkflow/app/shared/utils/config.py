"""Handles application configuration management using Pydantic's BaseSettings.

Loads settings from environment variables and Docker secrets.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, ValidationError, computed_field, EmailStr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# --- Configuration Loading Strategy ---
# Pydantic settings are loaded from multiple sources with the following priority:
# 1. Environment variables.
# 2. The .env file (if it exists).
# 3. The Docker secrets directory (if it exists).
# 4. Default values in the Settings model.
# This setup allows for flexible configuration in both local dev and containerized environments.

# Use Docker secrets directory if running in container, otherwise local secrets
SECRETS_DIR = '/run/secrets' if os.path.exists('/run/secrets') else '/home/marku/ai_workflow_engine/secrets'
# Load .env file only if it exists, which is typical for local development.
ENV_FILE = ".env" if os.path.exists(".env") else None

def read_secret_file(secret_name: str) -> Optional[str]:
    """
    Reads a Docker secret from the secrets directory.
    Returns None if the secret file doesn't exist or can't be read.
    """
    secret_path = os.path.join(SECRETS_DIR, secret_name)
    try:
        if os.path.exists(secret_path):
            with open(secret_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    logger.debug(f"Successfully read secret: {secret_name}")
                    return content
    except Exception as e:
        logger.warning(f"Failed to read secret {secret_name}: {e}")
    return None

if ENV_FILE:
    logger.info("Found .env file, loading settings.")
class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    It loads from a .env file for local development, but prioritizes
    environment variables in a containerized environment.
    """
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

    # Database Configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: Optional[SecretStr] = None
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USER: Optional[str] = None
    REDIS_PASSWORD: Optional[SecretStr] = None
    REDIS_URL: Optional[str] = None

    # Security & API Keys (loaded from Docker secrets)
    API_KEY: Optional[SecretStr] = None
    SERPAPI_KEY: Optional[SecretStr] = None
    TAVILY_API_KEY: Optional[SecretStr] = None
    JWT_SECRET_KEY: Optional[SecretStr] = None
    CSRF_SECRET_KEY: Optional[SecretStr] = None
    ADMIN_EMAIL: Optional[EmailStr] = None
    ADMIN_PASSWORD: Optional[SecretStr] = None

    # Home Assistant Configuration
    HOME_ASSISTANT_URL: str = "http://localhost:8123"
    HOME_ASSISTANT_TOKEN: Optional[SecretStr] = None

    # Qdrant Configuration
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: Optional[SecretStr] = None
    QDRANT_USE_TLS: bool = False  # Disable TLS for internal Docker network connections
    QDRANT_CERT_PATH: Optional[str] = "/etc/certs/worker/rootCA.pem"  # Path to CA certificate

    # Ollama Configuration
    # Use Optional here to allow the validator to set a default.
    # This also captures the inconsistent OLLAMA_HOST env var.
    OLLAMA_API_BASE_URL: Optional[str] = None
    OLLAMA_HOST: Optional[str] = None
    # Use aliases to gracefully handle alternative env var names that might be used
    # (e.g., OLLAMA_LLM_MODEL). This makes configuration more robust for users.
    OLLAMA_GENERATION_MODEL_NAME: str = Field(
        default="llama3.2:3b", alias="OLLAMA_LLM_MODEL")
    OLLAMA_EMBEDDING_MODEL_NAME: str = Field(
        default="nomic-embed-text", alias="OLLAMA_EMBEDDING_MODEL")
    EMBEDDING_DIM: int = 768

    # Search Configuration
    DEFAULT_CONTEXT_SEARCH_LIMIT: int = 5
    DEFAULT_DOCUMENT_SEARCH_LIMIT: int = 10
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[SecretStr] = None

    @model_validator(mode='after')
    def consolidate_ollama_url(self) -> 'Settings':
        """
        Consolidates Ollama URL from inconsistent environment variables.
        The project sometimes uses OLLAMA_HOST and sometimes OLLAMA_API_BASE_URL.
        This validator prioritizes OLLAMA_API_BASE_URL, falls back to OLLAMA_HOST,
        and finally sets a default if neither is present. This ensures that
        `settings.OLLAMA_API_BASE_URL` is always the single source of truth.
        """
        if self.OLLAMA_API_BASE_URL:
            logger.debug(f"Using OLLAMA_API_BASE_URL: {self.OLLAMA_API_BASE_URL}")
        elif self.OLLAMA_HOST:
            logger.warning(f"OLLAMA_API_BASE_URL not set, falling back to OLLAMA_HOST: {self.OLLAMA_HOST}")
            self.OLLAMA_API_BASE_URL = self.OLLAMA_HOST
        else:
            logger.debug("No Ollama URL configured, using default http://ollama:11434")
            self.OLLAMA_API_BASE_URL = "http://ollama:11434"
        return self

    @model_validator(mode='after')
    def load_google_oauth_from_secrets(self) -> 'Settings':
        """
        Loads Google OAuth credentials from Docker secrets only.
        This ensures production-ready secure credential management.
        """
        # Load Google OAuth credentials from Docker secrets only
        # Try both .txt extension (local) and without extension (Docker)
        if not self.GOOGLE_CLIENT_ID:
            secret_client_id = (read_secret_file('google_client_id.txt') or 
                               read_secret_file('google_client_id'))
            if secret_client_id:
                self.GOOGLE_CLIENT_ID = secret_client_id
                logger.debug("Loaded Google Client ID from Docker secret")

        if not self.GOOGLE_CLIENT_SECRET:
            secret_client_secret = (read_secret_file('google_client_secret.txt') or 
                                   read_secret_file('google_client_secret'))
            if secret_client_secret:
                self.GOOGLE_CLIENT_SECRET = SecretStr(secret_client_secret)
                logger.debug("Loaded Google Client Secret from Docker secret")

        return self

    @model_validator(mode='after')
    def load_secrets_from_docker(self) -> 'Settings':
        """
        Loads sensitive configuration from Docker secrets if not already set.
        This is the primary method for loading secrets in production.
        """
        # Load database password - Always prioritize Docker secret over environment
        postgres_password = (read_secret_file('postgres_password.txt') or 
                           read_secret_file('POSTGRES_PASSWORD'))
        if postgres_password:
            self.POSTGRES_PASSWORD = SecretStr(postgres_password)
            logger.debug("Loaded PostgreSQL password from Docker secret (overriding environment)")
        elif not self.POSTGRES_PASSWORD:
            logger.warning("No PostgreSQL password found in Docker secrets or environment")
        
        # Load JWT secret key
        if not self.JWT_SECRET_KEY:
            jwt_secret = (read_secret_file('jwt_secret_key.txt') or 
                         read_secret_file('JWT_SECRET_KEY'))
            if jwt_secret:
                self.JWT_SECRET_KEY = SecretStr(jwt_secret)
                logger.debug("Loaded JWT secret key from Docker secret")
        
        # Load CSRF secret key
        if not self.CSRF_SECRET_KEY:
            csrf_secret = (read_secret_file('csrf_secret_key.txt') or 
                          read_secret_file('CSRF_SECRET_KEY'))
            if csrf_secret:
                self.CSRF_SECRET_KEY = SecretStr(csrf_secret)
                logger.debug("Loaded CSRF secret key from Docker secret")
        
        # Load API key
        if not self.API_KEY:
            api_key = (read_secret_file('api_key.txt') or 
                      read_secret_file('API_KEY'))
            if api_key:
                self.API_KEY = SecretStr(api_key)
                logger.debug("Loaded API key from Docker secret")
        
        # Load Qdrant API key
        if not self.QDRANT_API_KEY:
            qdrant_api_key = (read_secret_file('qdrant_api_key.txt') or 
                             read_secret_file('QDRANT_API_KEY'))
            if qdrant_api_key:
                self.QDRANT_API_KEY = SecretStr(qdrant_api_key)
                logger.debug("Loaded Qdrant API key from Docker secret")
        
        # Load Redis password
        if not self.REDIS_PASSWORD:
            redis_password = (read_secret_file('redis_password.txt') or 
                             read_secret_file('REDIS_PASSWORD'))
            if redis_password:
                self.REDIS_PASSWORD = SecretStr(redis_password)
                logger.debug("Loaded Redis password from Docker secret")
        
        # Load admin credentials
        if not self.ADMIN_EMAIL:
            admin_email = read_secret_file('admin_email.txt')
            if admin_email:
                self.ADMIN_EMAIL = admin_email
                logger.debug("Loaded admin email from Docker secret")
        
        if not self.ADMIN_PASSWORD:
            admin_password = read_secret_file('admin_password.txt')
            if admin_password:
                self.ADMIN_PASSWORD = SecretStr(admin_password)
                logger.debug("Loaded admin password from Docker secret")
        
        return self

    @computed_field
    @property
    def database_url(self) -> str:
        """Computes the database connection URL from the settings."""
        # Use explicit DATABASE_URL if set, otherwise compute from components
        logger.info(f"Config DATABASE_URL value: {self.DATABASE_URL}")
        logger.info(f"Config POSTGRES_HOST: {self.POSTGRES_HOST}")
        
        if self.DATABASE_URL:
            logger.info("Using explicit DATABASE_URL from environment")
            return self.DATABASE_URL
        
        # Ensure password is available
        if not self.POSTGRES_PASSWORD:
            raise ValueError("POSTGRES_PASSWORD is required but not set (check Docker secrets)")
        
        computed_url = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode=disable"
        )
        logger.info(f"Computing database URL from components: {computed_url}")
        return computed_url

    @computed_field
    @property
    def redis_url(self) -> str:
        """Computes the Redis connection URL with authentication."""
        # Use explicit REDIS_URL if set, otherwise compute from components
        if self.REDIS_URL:
            logger.debug("Using explicit REDIS_URL from environment")
            return self.REDIS_URL
        
        # Build URL from components with authentication
        base_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        
        # Add authentication if available
        if self.REDIS_USER and self.REDIS_PASSWORD:
            password = self.REDIS_PASSWORD.get_secret_value()
            auth_url = f"redis://{self.REDIS_USER}:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            logger.debug(f"Using Redis URL with user authentication: {self.REDIS_USER}@{self.REDIS_HOST}:{self.REDIS_PORT}")
            return auth_url
        elif self.REDIS_PASSWORD:
            password = self.REDIS_PASSWORD.get_secret_value()
            auth_url = f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            logger.debug(f"Using Redis URL with password authentication: {self.REDIS_HOST}:{self.REDIS_PORT}")
            return auth_url
        else:
            logger.debug(f"Using Redis URL without authentication: {base_url}")
            return base_url

    @computed_field
    @property
    def qdrant_url(self) -> str:
        """Computes the Qdrant connection URL from host and port."""
        # Always use HTTPS since Qdrant container has TLS enabled
        # SSL verification is disabled in client connections via verify=False
        protocol = "https"
        return f"{protocol}://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached, singleton instance of the Settings object. This function
    is decorated with @lru_cache to ensure that the Settings object is created
    only once.

    Pydantic's BaseSettings loads configuration from environment variables,
    a .env file, or Docker secrets. Static analysis tools like Pylance may
    raise a false-positive error ("Arguments missing for parameters...") because
    they cannot see that the required settings are provided at runtime.
    We suppress this specific Pylance error as it's a known limitation and
    add robust error handling for missing settings at startup.
    """
    try:
        # The pyright ignore comment is for Pylance/Pyright.
        return Settings()  # pyright: ignore [reportCallIssue]
    except ValidationError as e:
        logger.critical("!!! Configuration validation failed on startup: %s", e)
        # Re-raise the exception to prevent the application from starting
        # with an invalid configuration.
        raise