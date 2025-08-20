"""
Unified Session Manager Service - Centralized session management authority.
Resolves session fragmentation by providing single source of truth for all session operations.
"""

import logging
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import User
from shared.utils.database_setup import get_async_session_context
from shared.services.redis_cache_service import RedisCache

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired" 
    INVALIDATED = "invalidated"
    PENDING_REFRESH = "pending_refresh"

@dataclass
class SessionData:
    """Unified session data structure."""
    session_id: str
    user_id: int
    email: str
    role: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary loaded from Redis."""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        data['status'] = SessionStatus(data['status'])
        return cls(**data)

class UnifiedSessionManager:
    """
    Centralized session management service providing single authority for all session operations.
    
    Features:
    - Redis-backed session storage (eliminates memory leaks)
    - Unified authentication state across REST/WebSocket
    - Connection pool health monitoring
    - Automatic session cleanup and expiration
    - Circuit breaker pattern for connection failures
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.cache_service: Optional[RedisCache] = None
        self._circuit_breaker = {
            'failures': 0,
            'last_failure': None,
            'open': False
        }
        self._session_ttl = 86400  # 24 hours default
        self._activity_extension = 3600  # 1 hour activity extension
        
    async def initialize(self):
        """Initialize the session manager with Redis connection and timeout protection."""
        try:
            # Initialize Redis cache service with timeout
            self.cache_service = RedisCache()
            
            # Use asyncio timeout to prevent hanging on Redis connection
            initialization_timeout = 10  # 10 seconds timeout
            await asyncio.wait_for(
                self.cache_service.initialize(),
                timeout=initialization_timeout
            )
            
            # Get Redis client for session operations
            self.redis_client = self.cache_service.redis_client
            
            # Test Redis connectivity with timeout
            await asyncio.wait_for(
                self.redis_client.ping(),
                timeout=5  # 5 seconds timeout for ping
            )
            
            logger.info("UnifiedSessionManager initialized successfully with Redis backend")
            
            # Reset circuit breaker on successful connection
            self._circuit_breaker['failures'] = 0
            self._circuit_breaker['open'] = False
            
        except asyncio.TimeoutError:
            logger.error("UnifiedSessionManager initialization timed out - Redis may be unresponsive")
            self._circuit_breaker['failures'] += 1
            self._circuit_breaker['last_failure'] = time.time()
            
            # Open circuit breaker on timeout
            if self._circuit_breaker['failures'] >= 3:
                self._circuit_breaker['open'] = True
                logger.error("Session manager circuit breaker opened due to Redis timeout failures")
            
            raise RuntimeError("Session manager initialization timed out")
            
        except Exception as e:
            logger.error(f"Failed to initialize UnifiedSessionManager: {e}")
            self._circuit_breaker['failures'] += 1
            self._circuit_breaker['last_failure'] = time.time()
            
            # Open circuit breaker if too many failures
            if self._circuit_breaker['failures'] >= 3:
                self._circuit_breaker['open'] = True
                logger.error("Session manager circuit breaker opened due to Redis failures")
            
            raise RuntimeError(f"Session manager initialization failed: {e}")
    
    async def create_session(
        self, 
        user_id: int, 
        email: str, 
        role: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create a new unified session."""
        if self._circuit_breaker['open']:
            if time.time() - self._circuit_breaker['last_failure'] < 300:  # 5 min cooldown
                raise RuntimeError("Session manager circuit breaker is open")
            else:
                # Try to reset circuit breaker
                self._circuit_breaker['open'] = False
                self._circuit_breaker['failures'] = 0
        
        if not session_id:
            import uuid
            session_id = f"sess_{uuid.uuid4().hex}"
        
        now = datetime.now()
        expires_at = now + timedelta(seconds=self._session_ttl)
        
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            email=email,
            role=role,
            status=SessionStatus.ACTIVE,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        try:
            # Store session in Redis with TTL
            await self.redis_client.setex(
                f"session:{session_id}",
                self._session_ttl,
                json.dumps(session_data.to_dict())
            )
            
            # Store user session mapping
            await self.redis_client.sadd(f"user_sessions:{user_id}", session_id)
            await self.redis_client.expire(f"user_sessions:{user_id}", self._session_ttl)
            
            logger.info(f"Created unified session {session_id} for user {user_id}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            self._circuit_breaker['failures'] += 1
            if self._circuit_breaker['failures'] >= 3:
                self._circuit_breaker['open'] = True
            raise
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data by ID with graceful error handling."""
        if self._circuit_breaker['open']:
            logger.debug("Session manager circuit breaker is open, returning None")
            return None
        
        if not self.redis_client:
            logger.debug("Redis client not available, returning None")
            return None
        
        try:
            session_data = await self.redis_client.get(f"session:{session_id}")
            if not session_data:
                return None
            
            data = json.loads(session_data)
            session = SessionData.from_dict(data)
            
            # Check if session is expired
            if session.expires_at < datetime.now():
                # Try to invalidate but don't fail if it doesn't work
                try:
                    await self.invalidate_session(session_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup expired session {session_id}: {cleanup_error}")
                return None
            
            return session
            
        except Exception as e:
            logger.warning(f"Failed to get session {session_id}, Redis may be unavailable: {e}")
            # Increment failure count but don't open circuit breaker immediately
            self._circuit_breaker['failures'] += 1
            return None
    
    async def validate_session(self, session_id: str) -> tuple[bool, Optional[SessionData]]:
        """Validate session and return status with data."""
        session = await self.get_session(session_id)
        
        if not session:
            return False, None
        
        # Check session status
        if session.status != SessionStatus.ACTIVE:
            return False, session
        
        # Check expiration
        if session.expires_at < datetime.now():
            await self.invalidate_session(session_id)
            return False, None
        
        # Update last activity
        await self.update_activity(session_id)
        
        return True, session
    
    async def update_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            # Update last activity
            session.last_activity = datetime.now()
            
            # Extend expiration if needed
            time_until_expiry = (session.expires_at - datetime.now()).total_seconds()
            if time_until_expiry < self._activity_extension:
                session.expires_at = datetime.now() + timedelta(seconds=self._activity_extension)
            
            # Save updated session
            await self.redis_client.setex(
                f"session:{session_id}",
                self._session_ttl,
                json.dumps(session.to_dict())
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update activity for session {session_id}: {e}")
            return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session."""
        try:
            session = await self.get_session(session_id)
            if session:
                # Remove from user session set
                await self.redis_client.srem(f"user_sessions:{session.user_id}", session_id)
            
            # Delete session data
            await self.redis_client.delete(f"session:{session_id}")
            
            logger.info(f"Invalidated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False
    
    async def invalidate_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        try:
            session_ids = await self.redis_client.smembers(f"user_sessions:{user_id}")
            invalidated_count = 0
            
            for session_id in session_ids:
                if isinstance(session_id, bytes):
                    session_id = session_id.decode('utf-8')
                
                if await self.invalidate_session(session_id):
                    invalidated_count += 1
            
            # Clean up user session set
            await self.redis_client.delete(f"user_sessions:{user_id}")
            
            logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate user sessions for {user_id}: {e}")
            return 0
    
    async def get_user_sessions(self, user_id: int) -> List[SessionData]:
        """Get all active sessions for a user."""
        try:
            session_ids = await self.redis_client.smembers(f"user_sessions:{user_id}")
            sessions = []
            
            for session_id in session_ids:
                if isinstance(session_id, bytes):
                    session_id = session_id.decode('utf-8')
                
                session = await self.get_session(session_id)
                if session and session.status == SessionStatus.ACTIVE:
                    sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions across the system."""
        try:
            # Scan for all session keys
            session_keys = []
            async for key in self.redis_client.scan_iter(match="session:*"):
                session_keys.append(key)
            
            cleaned_count = 0
            now = datetime.now()
            
            for key in session_keys:
                try:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        data = json.loads(session_data)
                        expires_at = datetime.fromisoformat(data['expires_at'])
                        
                        if expires_at < now:
                            session_id = key.decode('utf-8').split(':', 1)[1]
                            await self.invalidate_session(session_id)
                            cleaned_count += 1
                
                except Exception as session_error:
                    logger.warning(f"Error processing session key {key}: {session_error}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session management statistics."""
        try:
            # Count total active sessions
            session_keys = []
            async for key in self.redis_client.scan_iter(match="session:*"):
                session_keys.append(key)
            
            total_sessions = len(session_keys)
            active_sessions = 0
            expired_sessions = 0
            now = datetime.now()
            
            for key in session_keys:
                try:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        data = json.loads(session_data)
                        expires_at = datetime.fromisoformat(data['expires_at'])
                        status = SessionStatus(data['status'])
                        
                        if expires_at >= now and status == SessionStatus.ACTIVE:
                            active_sessions += 1
                        else:
                            expired_sessions += 1
                
                except Exception:
                    expired_sessions += 1  # Count unparseable sessions as expired
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": expired_sessions,
                "circuit_breaker_open": self._circuit_breaker['open'],
                "circuit_breaker_failures": self._circuit_breaker['failures'],
                "redis_connected": self.redis_client is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {
                "error": str(e),
                "circuit_breaker_open": self._circuit_breaker['open']
            }
    
    async def close(self):
        """Close session manager and cleanup resources."""
        if self.cache_service:
            await self.cache_service.close()
        logger.info("UnifiedSessionManager closed")

# Global session manager instance
_session_manager: Optional[UnifiedSessionManager] = None

async def get_session_manager() -> UnifiedSessionManager:
    """Get the global session manager instance with graceful failure handling."""
    global _session_manager
    
    if _session_manager is None:
        _session_manager = UnifiedSessionManager()
        try:
            await _session_manager.initialize()
        except Exception as e:
            logger.warning(f"Session manager initialization failed, will operate in fallback mode: {e}")
            # Don't re-raise - let the session manager operate in degraded mode
    
    return _session_manager

async def cleanup_session_manager():
    """Cleanup the global session manager."""
    global _session_manager
    
    if _session_manager:
        await _session_manager.close()
        _session_manager = None