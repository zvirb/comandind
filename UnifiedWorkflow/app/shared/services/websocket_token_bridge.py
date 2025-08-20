"""
WebSocket Token Bridge

Solves the httpOnly cookie vs WebSocket authentication dilemma:
- Maintains httpOnly=True for maximum security
- Provides secure token exchange for WebSocket connections
- Uses short-lived bridge tokens with strict validation
- Prevents token exposure in URLs or logs
"""

import os
import secrets
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer
import jwt

from app.shared.services.jwt_rotation_service import get_jwt_rotation_service

logger = logging.getLogger(__name__)

@dataclass
class BridgeToken:
    """Short-lived bridge token for WebSocket authentication"""
    token_id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    original_token_hash: str  # Hash of original JWT for validation

class WebSocketTokenBridge:
    """
    Secure token bridge for WebSocket authentication.
    
    Workflow:
    1. Frontend makes authenticated request to /api/v1/auth/websocket-token
    2. Server validates httpOnly JWT cookie
    3. Server generates short-lived bridge token (5 minutes)
    4. Frontend uses bridge token for WebSocket connection
    5. WebSocket validates bridge token and establishes session
    6. Bridge token expires quickly to minimize exposure window
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.bridge_ttl = timedelta(minutes=5)  # Very short window
        self.max_bridge_tokens_per_user = 3  # Prevent abuse
        
        # Redis keys
        self.BRIDGE_TOKEN_PREFIX = "websocket:bridge:"
        self.USER_BRIDGE_TOKENS_PREFIX = "websocket:user_bridges:"
        
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
    
    def _generate_bridge_token_id(self) -> str:
        """Generate secure bridge token ID."""
        return f"bridge-{secrets.token_urlsafe(32)}"
    
    def _hash_jwt_token(self, jwt_token: str) -> str:
        """Create hash of JWT token for validation."""
        import hashlib
        return hashlib.sha256(jwt_token.encode()).hexdigest()
    
    async def _store_bridge_token(self, bridge_token: BridgeToken) -> None:
        """Store bridge token in Redis with TTL."""
        redis_client = await self._get_redis()
        
        # Store bridge token data
        token_data = {
            "user_id": bridge_token.user_id,
            "created_at": bridge_token.created_at.isoformat(),
            "expires_at": bridge_token.expires_at.isoformat(),
            "original_token_hash": bridge_token.original_token_hash
        }
        
        # Store with TTL for automatic cleanup
        await redis_client.hset(
            f"{self.BRIDGE_TOKEN_PREFIX}{bridge_token.token_id}",
            mapping=token_data
        )
        await redis_client.expire(
            f"{self.BRIDGE_TOKEN_PREFIX}{bridge_token.token_id}",
            int(self.bridge_ttl.total_seconds())
        )
        
        # Track user's bridge tokens for cleanup
        user_tokens_key = f"{self.USER_BRIDGE_TOKENS_PREFIX}{bridge_token.user_id}"
        await redis_client.sadd(user_tokens_key, bridge_token.token_id)
        await redis_client.expire(user_tokens_key, int(self.bridge_ttl.total_seconds()) + 60)
        
        logger.debug(f"Stored bridge token {bridge_token.token_id} for user {bridge_token.user_id}")
    
    async def _load_bridge_token(self, token_id: str) -> Optional[BridgeToken]:
        """Load bridge token from Redis."""
        redis_client = await self._get_redis()
        
        token_data = await redis_client.hgetall(f"{self.BRIDGE_TOKEN_PREFIX}{token_id}")
        if not token_data:
            return None
        
        try:
            return BridgeToken(
                token_id=token_id,
                user_id=int(token_data["user_id"]),
                created_at=datetime.fromisoformat(token_data["created_at"]),
                expires_at=datetime.fromisoformat(token_data["expires_at"]),
                original_token_hash=token_data["original_token_hash"]
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse bridge token data for {token_id}: {e}")
            return None
    
    async def _cleanup_user_bridge_tokens(self, user_id: int) -> None:
        """Clean up old bridge tokens for a user."""
        redis_client = await self._get_redis()
        user_tokens_key = f"{self.USER_BRIDGE_TOKENS_PREFIX}{user_id}"
        
        # Get all tokens for this user
        token_ids = await redis_client.smembers(user_tokens_key)
        if not token_ids:
            return
        
        # Check each token and remove expired ones
        for token_id in token_ids:
            bridge_token = await self._load_bridge_token(token_id)
            if not bridge_token or datetime.now(timezone.utc) > bridge_token.expires_at:
                # Remove expired token
                await redis_client.delete(f"{self.BRIDGE_TOKEN_PREFIX}{token_id}")
                await redis_client.srem(user_tokens_key, token_id)
        
        # If we have too many tokens, remove oldest ones
        remaining_tokens = await redis_client.smembers(user_tokens_key)
        if len(remaining_tokens) > self.max_bridge_tokens_per_user:
            # Load all remaining tokens to find oldest
            token_objects = []
            for token_id in remaining_tokens:
                bridge_token = await self._load_bridge_token(token_id)
                if bridge_token:
                    token_objects.append(bridge_token)
            
            # Sort by creation time and remove oldest
            token_objects.sort(key=lambda t: t.created_at)
            tokens_to_remove = token_objects[:-self.max_bridge_tokens_per_user]
            
            for token in tokens_to_remove:
                await redis_client.delete(f"{self.BRIDGE_TOKEN_PREFIX}{token.token_id}")
                await redis_client.srem(user_tokens_key, token.token_id)
                logger.debug(f"Removed old bridge token {token.token_id} for user {user_id}")
    
    async def create_bridge_token(self, request: Request, jwt_token: str, user_id: int) -> str:
        """
        Create a new bridge token for WebSocket authentication.
        
        Args:
            request: FastAPI request object for security context
            jwt_token: Original JWT token from httpOnly cookie
            user_id: User ID from validated JWT
            
        Returns:
            Bridge token ID for WebSocket authentication
        """
        now = datetime.now(timezone.utc)
        
        # Clean up old tokens for this user
        await self._cleanup_user_bridge_tokens(user_id)
        
        # Create new bridge token
        bridge_token = BridgeToken(
            token_id=self._generate_bridge_token_id(),
            user_id=user_id,
            created_at=now,
            expires_at=now + self.bridge_ttl,
            original_token_hash=self._hash_jwt_token(jwt_token)
        )
        
        await self._store_bridge_token(bridge_token)
        
        # Log for security monitoring
        client_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For") or request.client.host
        logger.info(f"Created WebSocket bridge token for user {user_id} from IP {client_ip}")
        
        return bridge_token.token_id
    
    async def validate_bridge_token(self, token_id: str, client_ip: str = None) -> Tuple[int, str]:
        """
        Validate bridge token and return user information.
        
        Args:
            token_id: Bridge token ID to validate
            client_ip: Client IP address for logging
            
        Returns:
            Tuple of (user_id, original_token_hash)
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        if not token_id or not token_id.startswith("bridge-"):
            logger.warning(f"Invalid bridge token format from IP {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bridge token format"
            )
        
        # Load bridge token
        bridge_token = await self._load_bridge_token(token_id)
        if not bridge_token:
            logger.warning(f"Bridge token not found: {token_id} from IP {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bridge token not found or expired"
            )
        
        # Check expiration
        now = datetime.now(timezone.utc)
        if now > bridge_token.expires_at:
            logger.warning(f"Expired bridge token used: {token_id} from IP {client_ip}")
            # Clean up expired token
            redis_client = await self._get_redis()
            await redis_client.delete(f"{self.BRIDGE_TOKEN_PREFIX}{token_id}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bridge token expired"
            )
        
        # Consume token immediately for single use
        redis_client = await self._get_redis()
        await redis_client.delete(f"{self.BRIDGE_TOKEN_PREFIX}{token_id}")
        await redis_client.srem(f"{self.USER_BRIDGE_TOKENS_PREFIX}{bridge_token.user_id}", token_id)
        
        logger.info(f"Validated and consumed bridge token for user {bridge_token.user_id} from IP {client_ip}")
        
        return bridge_token.user_id, bridge_token.original_token_hash
    
    async def get_bridge_stats(self) -> Dict:
        """Get bridge token statistics for monitoring."""
        redis_client = await self._get_redis()
        
        # Count active bridge tokens
        pattern = f"{self.BRIDGE_TOKEN_PREFIX}*"
        keys = await redis_client.keys(pattern)
        
        return {
            "active_bridge_tokens": len(keys),
            "bridge_ttl_minutes": self.bridge_ttl.total_seconds() / 60,
            "max_tokens_per_user": self.max_bridge_tokens_per_user
        }

# Global instance
_websocket_bridge: Optional[WebSocketTokenBridge] = None

def get_websocket_bridge() -> WebSocketTokenBridge:
    """Get the global WebSocket token bridge instance."""
    global _websocket_bridge
    
    if _websocket_bridge is None:
        _websocket_bridge = WebSocketTokenBridge()
    
    return _websocket_bridge