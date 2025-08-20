"""
JWT Secret Rotation Service

Provides secure JWT secret rotation with graceful key rollover:
- Automatic rotation with configurable intervals
- Multi-key validation for seamless transitions
- Redis-based key storage for distributed systems
- Zero-downtime rotation mechanism
"""

import os
import secrets
import logging
import asyncio
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

import redis.asyncio as redis
from cryptography.fernet import Fernet
import jwt
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

@dataclass
class JWTKey:
    """JWT key with metadata"""
    key_id: str
    secret: str
    created_at: datetime
    expires_at: datetime
    is_primary: bool = False

class JWTRotationService:
    """
    JWT secret rotation service with graceful key rollover.
    
    Features:
    - Automatic key rotation every 24 hours
    - Multi-key validation during transition periods
    - Secure key storage in Redis with encryption
    - Zero-downtime deployment support
    """
    
    def __init__(
        self,
        redis_url: str = None,
        rotation_interval_hours: int = 24,
        key_grace_period_hours: int = 2,
        encryption_key: str = None
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.rotation_interval = timedelta(hours=rotation_interval_hours)
        self.grace_period = timedelta(hours=key_grace_period_hours)
        
        # Use encryption for storing keys in Redis
        self.encryption_key = encryption_key or os.getenv("JWT_KEY_ENCRYPTION_SECRET")
        if not self.encryption_key:
            # Generate a secure encryption key if not provided
            self.encryption_key = Fernet.generate_key().decode()
            logger.warning("Generated new JWT encryption key - store in environment for persistence")
        
        self.fernet = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        # Redis keys
        self.KEYS_HASH = "jwt:rotation:keys"
        self.PRIMARY_KEY = "jwt:rotation:primary"
        self.ROTATION_LOCK = "jwt:rotation:lock"
        
        # In-memory cache for performance
        self._key_cache: Dict[str, JWTKey] = {}
        self._cache_expires_at: Optional[datetime] = None
        self._rotation_task: Optional[asyncio.Task] = None
        
        # Redis connection pool
        self._redis_pool: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection with connection pooling."""
        if self._redis_pool is None:
            self._redis_pool = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True
            )
        return self._redis_pool
    
    def _encrypt_key(self, key_data: str) -> str:
        """Encrypt key data for secure storage."""
        return self.fernet.encrypt(key_data.encode()).decode()
    
    def _decrypt_key(self, encrypted_data: str) -> str:
        """Decrypt key data from storage."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def _generate_key_id(self) -> str:
        """Generate unique key identifier."""
        return f"jwt-key-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(8)}"
    
    def _generate_jwt_secret(self) -> str:
        """Generate cryptographically secure JWT secret."""
        return secrets.token_urlsafe(64)  # 512-bit secret
    
    async def _store_key(self, jwt_key: JWTKey) -> None:
        """Store JWT key in Redis with encryption."""
        redis_client = await self._get_redis()
        
        key_data = {
            "secret": jwt_key.secret,
            "created_at": jwt_key.created_at.isoformat(),
            "expires_at": jwt_key.expires_at.isoformat(),
            "is_primary": jwt_key.is_primary
        }
        
        # Encrypt the entire key data
        encrypted_data = self._encrypt_key(str(key_data))
        
        # Store in Redis hash
        await redis_client.hset(self.KEYS_HASH, jwt_key.key_id, encrypted_data)
        
        if jwt_key.is_primary:
            await redis_client.set(self.PRIMARY_KEY, jwt_key.key_id)
            
        logger.info(f"Stored JWT key {jwt_key.key_id} (primary: {jwt_key.is_primary})")
    
    async def _load_keys(self) -> Dict[str, JWTKey]:
        """Load all JWT keys from Redis."""
        redis_client = await self._get_redis()
        
        # Get all keys
        key_data = await redis_client.hgetall(self.KEYS_HASH)
        if not key_data:
            return {}
        
        keys = {}
        for key_id, encrypted_data in key_data.items():
            try:
                # Decrypt and parse key data
                decrypted_data = self._decrypt_key(encrypted_data)
                parsed_data = eval(decrypted_data)  # Safe since we control the format
                
                jwt_key = JWTKey(
                    key_id=key_id,
                    secret=parsed_data["secret"],
                    created_at=datetime.fromisoformat(parsed_data["created_at"]),
                    expires_at=datetime.fromisoformat(parsed_data["expires_at"]),
                    is_primary=parsed_data["is_primary"]
                )
                keys[key_id] = jwt_key
                
            except Exception as e:
                logger.error(f"Failed to load JWT key {key_id}: {e}")
                continue
        
        return keys
    
    async def _get_primary_key(self) -> Optional[JWTKey]:
        """Get the primary JWT key."""
        redis_client = await self._get_redis()
        primary_key_id = await redis_client.get(self.PRIMARY_KEY)
        
        if not primary_key_id:
            return None
        
        keys = await self._load_keys()
        return keys.get(primary_key_id)
    
    async def _cleanup_expired_keys(self) -> None:
        """Remove expired keys from storage."""
        redis_client = await self._get_redis()
        keys = await self._load_keys()
        now = datetime.now(timezone.utc)
        
        expired_keys = [
            key_id for key_id, key in keys.items()
            if now > key.expires_at
        ]
        
        if expired_keys:
            await redis_client.hdel(self.KEYS_HASH, *expired_keys)
            logger.info(f"Cleaned up {len(expired_keys)} expired JWT keys")
    
    async def _refresh_key_cache(self) -> None:
        """Refresh the in-memory key cache."""
        self._key_cache = await self._load_keys()
        self._cache_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        logger.debug(f"Refreshed JWT key cache with {len(self._key_cache)} keys")
    
    async def _get_cached_keys(self) -> Dict[str, JWTKey]:
        """Get keys from cache, refreshing if needed."""
        now = datetime.now(timezone.utc)
        
        if not self._key_cache or (self._cache_expires_at and now > self._cache_expires_at):
            await self._refresh_key_cache()
        
        return self._key_cache
    
    async def initialize(self) -> None:
        """Initialize the JWT rotation service."""
        try:
            # Test Redis connection
            redis_client = await self._get_redis()
            await redis_client.ping()
            logger.info("JWT rotation service Redis connection established")
            
            # Load existing keys
            await self._refresh_key_cache()
            
            # Create initial key if none exist
            if not self._key_cache:
                await self._generate_new_primary_key()
                logger.info("Generated initial JWT key")
            
            # Start rotation background task
            self._rotation_task = asyncio.create_task(self._rotation_worker())
            logger.info("JWT rotation service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize JWT rotation service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the JWT rotation service."""
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
        
        if self._redis_pool:
            await self._redis_pool.close()
            
        logger.info("JWT rotation service shutdown completed")
    
    async def _generate_new_primary_key(self) -> JWTKey:
        """Generate a new primary JWT key."""
        now = datetime.now(timezone.utc)
        
        # Mark current primary as non-primary
        current_keys = await self._load_keys()
        for key in current_keys.values():
            if key.is_primary:
                key.is_primary = False
                # Extend grace period for seamless transition
                key.expires_at = now + self.grace_period
                await self._store_key(key)
        
        # Generate new primary key
        new_key = JWTKey(
            key_id=self._generate_key_id(),
            secret=self._generate_jwt_secret(),
            created_at=now,
            expires_at=now + self.rotation_interval + self.grace_period,
            is_primary=True
        )
        
        await self._store_key(new_key)
        await self._refresh_key_cache()
        
        logger.info(f"Generated new primary JWT key: {new_key.key_id}")
        return new_key
    
    async def _rotation_worker(self) -> None:
        """Background worker for automatic key rotation."""
        while True:
            try:
                primary_key = await self._get_primary_key()
                
                if primary_key:
                    # Check if rotation is needed
                    time_until_rotation = primary_key.created_at + self.rotation_interval - datetime.now(timezone.utc)
                    
                    if time_until_rotation.total_seconds() <= 0:
                        # Acquire rotation lock to prevent concurrent rotations
                        redis_client = await self._get_redis()
                        
                        async with self._redis_lock(redis_client, self.ROTATION_LOCK, timeout=300):
                            logger.info("Starting automatic JWT key rotation")
                            await self._generate_new_primary_key()
                            await self._cleanup_expired_keys()
                            logger.info("Automatic JWT key rotation completed")
                    else:
                        logger.debug(f"Next JWT rotation in: {time_until_rotation}")
                
                # Sleep for 1 hour before next check
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                logger.info("JWT rotation worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in JWT rotation worker: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    @asynccontextmanager
    async def _redis_lock(self, redis_client: redis.Redis, lock_key: str, timeout: int = 60):
        """Redis-based distributed lock."""
        lock_value = secrets.token_hex(16)
        acquired = False
        
        try:
            # Try to acquire lock
            acquired = await redis_client.set(lock_key, lock_value, ex=timeout, nx=True)
            if not acquired:
                raise RuntimeError(f"Could not acquire lock: {lock_key}")
            
            yield
            
        finally:
            if acquired:
                # Release lock only if we own it
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await redis_client.eval(lua_script, 1, lock_key, lock_value)
    
    async def get_current_secret(self) -> str:
        """Get the current primary JWT secret."""
        primary_key = await self._get_primary_key()
        if not primary_key:
            raise RuntimeError("No primary JWT key available")
        
        return primary_key.secret
    
    async def get_validation_secrets(self) -> List[str]:
        """Get all valid JWT secrets for token validation."""
        keys = await self._get_cached_keys()
        now = datetime.now(timezone.utc)
        
        # Return secrets from non-expired keys, primary first
        valid_keys = [key for key in keys.values() if now <= key.expires_at]
        valid_keys.sort(key=lambda k: (not k.is_primary, k.created_at), reverse=True)
        
        return [key.secret for key in valid_keys]
    
    async def create_token(self, payload: Dict, algorithm: str = "HS256") -> str:
        """Create JWT token with current primary secret."""
        secret = await self.get_current_secret()
        
        # Add key ID to payload for validation tracking
        primary_key = await self._get_primary_key()
        if primary_key:
            payload["kid"] = primary_key.key_id
        
        return jwt.encode(payload, secret, algorithm=algorithm)
    
    async def validate_token(self, token: str, algorithm: str = "HS256") -> Dict:
        """Validate JWT token against all valid secrets."""
        secrets = await self.get_validation_secrets()
        
        if not secrets:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT validation temporarily unavailable"
            )
        
        # Try validation with each secret
        last_exception = None
        
        for secret in secrets:
            try:
                payload = jwt.decode(token, secret, algorithms=[algorithm])
                
                # Log which key was used for validation
                key_id = payload.get("kid", "unknown")
                logger.debug(f"Token validated with key: {key_id}")
                
                return payload
                
            except jwt.InvalidTokenError as e:
                last_exception = e
                continue
        
        # If we get here, no secret validated the token
        logger.warning("JWT validation failed with all available secrets")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    async def force_rotation(self) -> JWTKey:
        """Force immediate key rotation (for emergency situations)."""
        redis_client = await self._get_redis()
        
        async with self._redis_lock(redis_client, self.ROTATION_LOCK, timeout=300):
            logger.warning("Force rotating JWT keys")
            new_key = await self._generate_new_primary_key()
            await self._cleanup_expired_keys()
            logger.warning(f"Force rotation completed - new key: {new_key.key_id}")
            return new_key
    
    async def get_rotation_status(self) -> Dict:
        """Get rotation service status and metrics."""
        primary_key = await self._get_primary_key()
        all_keys = await self._get_cached_keys()
        now = datetime.now(timezone.utc)
        
        if not primary_key:
            return {
                "status": "error",
                "error": "No primary key available",
                "total_keys": len(all_keys)
            }
        
        time_until_rotation = primary_key.created_at + self.rotation_interval - now
        
        return {
            "status": "healthy",
            "primary_key_id": primary_key.key_id,
            "primary_key_age": (now - primary_key.created_at).total_seconds(),
            "next_rotation_in": max(0, time_until_rotation.total_seconds()),
            "total_keys": len(all_keys),
            "valid_keys": len([k for k in all_keys.values() if now <= k.expires_at]),
            "rotation_interval_hours": self.rotation_interval.total_seconds() / 3600,
            "grace_period_hours": self.grace_period.total_seconds() / 3600
        }

# Global instance
_jwt_rotation_service: Optional[JWTRotationService] = None

async def get_jwt_rotation_service() -> JWTRotationService:
    """Get the global JWT rotation service instance."""
    global _jwt_rotation_service
    
    if _jwt_rotation_service is None:
        _jwt_rotation_service = JWTRotationService()
        await _jwt_rotation_service.initialize()
    
    return _jwt_rotation_service

async def shutdown_jwt_rotation_service():
    """Shutdown the global JWT rotation service."""
    global _jwt_rotation_service
    
    if _jwt_rotation_service:
        await _jwt_rotation_service.shutdown()
        _jwt_rotation_service = None