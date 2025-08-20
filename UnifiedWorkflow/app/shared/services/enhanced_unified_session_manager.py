"""
Enhanced Unified Session Manager - Redis with Database Backup
Provides hybrid session storage for maximum reliability and performance.

Features:
- Primary Redis storage for speed
- Database backup for persistence
- Automatic failover between storage mechanisms
- Session replication and synchronization
- Connection pool optimization support
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
from sqlalchemy import select, delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database.models import User
from shared.utils.database_setup import get_async_session_context
from shared.services.redis_cache_service import RedisCache
from shared.services.unified_session_manager import SessionData, SessionStatus, UnifiedSessionManager

logger = logging.getLogger(__name__)

class StorageBackend(Enum):
    """Session storage backend enumeration."""
    REDIS_PRIMARY = "redis_primary"
    DATABASE_BACKUP = "database_backup"
    HYBRID = "hybrid"

@dataclass
class SessionConfig:
    """Enhanced session configuration."""
    redis_ttl: int = 3600  # 1 hour Redis TTL
    database_sync_interval: int = 300  # 5 minutes database sync
    enable_database_backup: bool = True
    enable_session_replication: bool = True
    max_redis_retry_attempts: int = 3
    failover_to_database: bool = True

class EnhancedUnifiedSessionManager(UnifiedSessionManager):
    """Enhanced session manager with Redis + Database hybrid storage."""
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize enhanced session manager."""
        super().__init__()
        self.config = config or SessionConfig()
        self._database_sync_tasks = {}
        self._last_database_sync = {}
        
        # Storage backend health tracking
        self._redis_healthy = True
        self._database_healthy = True
        self._health_check_interval = 60  # 1 minute
        
        logger.info("Enhanced Unified Session Manager initialized with hybrid storage")
    
    async def create_session(self, user_id: int, email: str, role: str, 
                           metadata: Optional[Dict[str, Any]] = None) -> SessionData:
        """Create session with hybrid storage."""
        try:
            # Create session using parent implementation
            session = await super().create_session(user_id, email, role, metadata)
            
            # Persist to database if enabled
            if self.config.enable_database_backup:
                await self._persist_session_to_database(session)
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session with hybrid storage: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session with fallback mechanism."""
        try:
            # Try Redis first (fastest)
            if self._redis_healthy:
                session = await super().get_session(session_id)
                if session:
                    return session
            
            # Fallback to database
            if self.config.failover_to_database and self._database_healthy:
                return await self._get_session_from_database(session_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, **updates) -> bool:
        """Update session in both Redis and database."""
        try:
            # Update in Redis
            redis_success = await super().update_activity(session_id)
            
            # Update in database if sync is due
            if self.config.enable_database_backup:
                await self._schedule_database_sync(session_id)
            
            return redis_success
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session in both storage backends."""
        try:
            # Invalidate in Redis
            redis_success = await super().invalidate_session(session_id)
            
            # Invalidate in database
            db_success = True
            if self.config.enable_database_backup:
                db_success = await self._invalidate_session_in_database(session_id)
            
            return redis_success and db_success
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {e}")
            return False
    
    async def _persist_session_to_database(self, session: SessionData) -> bool:
        """Persist session data to database."""
        try:
            async with get_async_session_context() as db:
                # Use PostgreSQL UPSERT for efficient session storage
                stmt = pg_insert(SessionStore).values(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    email=session.email,
                    role=session.role,
                    status=session.status.value,
                    created_at=session.created_at,
                    last_activity=session.last_activity,
                    expires_at=session.expires_at,
                    metadata=session.metadata,
                    updated_at=datetime.now()
                )
                
                # Handle conflicts with update
                stmt = stmt.on_conflict_do_update(
                    index_elements=['session_id'],
                    set_={
                        'last_activity': stmt.excluded.last_activity,
                        'expires_at': stmt.excluded.expires_at,
                        'metadata': stmt.excluded.metadata,
                        'status': stmt.excluded.status,
                        'updated_at': stmt.excluded.updated_at
                    }
                )
                
                await db.execute(stmt)
                await db.commit()
                
                logger.debug(f"Session {session.session_id} persisted to database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to persist session to database: {e}")
            return False
    
    async def _get_session_from_database(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session from database."""
        try:
            async with get_async_session_context() as db:
                result = await db.execute(
                    select(SessionStore).filter(
                        SessionStore.session_id == session_id,
                        SessionStore.status == SessionStatus.ACTIVE.value,
                        SessionStore.expires_at > datetime.now()
                    )
                )
                
                session_record = result.scalar_one_or_none()
                if not session_record:
                    return None
                
                # Convert database record to SessionData
                session = SessionData(
                    session_id=session_record.session_id,
                    user_id=session_record.user_id,
                    email=session_record.email,
                    role=session_record.role,
                    status=SessionStatus(session_record.status),
                    created_at=session_record.created_at,
                    last_activity=session_record.last_activity,
                    expires_at=session_record.expires_at,
                    metadata=session_record.metadata or {}
                )
                
                # Cache session back to Redis if healthy
                if self._redis_healthy:
                    await self._cache_session_to_redis(session)
                
                logger.debug(f"Session {session_id} retrieved from database")
                return session
                
        except Exception as e:
            logger.error(f"Failed to retrieve session from database: {e}")
            return None
    
    async def _invalidate_session_in_database(self, session_id: str) -> bool:
        """Invalidate session in database."""
        try:
            async with get_async_session_context() as db:
                await db.execute(
                    update(SessionStore)
                    .filter(SessionStore.session_id == session_id)
                    .values(
                        status=SessionStatus.INVALIDATED.value,
                        updated_at=datetime.now()
                    )
                )
                await db.commit()
                
                logger.debug(f"Session {session_id} invalidated in database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to invalidate session in database: {e}")
            return False
    
    async def _cache_session_to_redis(self, session: SessionData) -> bool:
        """Cache session from database back to Redis."""
        try:
            await self.redis_client.setex(
                f"session:{session.session_id}",
                self.config.redis_ttl,
                json.dumps(session.to_dict())
            )
            
            logger.debug(f"Session {session.session_id} cached to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache session to Redis: {e}")
            return False
    
    async def _schedule_database_sync(self, session_id: str) -> None:
        """Schedule database synchronization for session."""
        try:
            current_time = time.time()
            last_sync = self._last_database_sync.get(session_id, 0)
            
            # Check if sync is due
            if current_time - last_sync >= self.config.database_sync_interval:
                # Get session from Redis
                session = await super().get_session(session_id)
                if session:
                    await self._persist_session_to_database(session)
                    self._last_database_sync[session_id] = current_time
                    
        except Exception as e:
            logger.error(f"Failed to schedule database sync for {session_id}: {e}")
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from both storage backends."""
        try:
            # Clean up Redis sessions (parent implementation)
            redis_cleaned = await super().cleanup_expired_sessions()
            
            # Clean up database sessions
            db_cleaned = 0
            if self.config.enable_database_backup:
                db_cleaned = await self._cleanup_database_sessions()
            
            total_cleaned = redis_cleaned + db_cleaned
            logger.info(f"Cleaned up {total_cleaned} expired sessions ({redis_cleaned} Redis, {db_cleaned} database)")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Failed to clean up expired sessions: {e}")
            return 0
    
    async def _cleanup_database_sessions(self) -> int:
        """Clean up expired sessions from database."""
        try:
            async with get_async_session_context() as db:
                # Delete expired sessions
                result = await db.execute(
                    delete(SessionStore).filter(
                        db.or_(
                            SessionStore.expires_at < datetime.now(),
                            SessionStore.status.in_([
                                SessionStatus.EXPIRED.value,
                                SessionStatus.INVALIDATED.value
                            ])
                        )
                    )
                )
                
                await db.commit()
                cleaned_count = result.rowcount
                
                logger.debug(f"Cleaned up {cleaned_count} expired sessions from database")
                return cleaned_count
                
        except Exception as e:
            logger.error(f"Failed to clean up database sessions: {e}")
            return 0
    
    async def get_storage_health(self) -> Dict[str, Any]:
        """Get health status of storage backends."""
        try:
            redis_health = await self._check_redis_health()
            db_health = await self._check_database_health()
            
            return {
                "redis": {
                    "healthy": redis_health,
                    "status": "connected" if redis_health else "disconnected"
                },
                "database": {
                    "healthy": db_health,
                    "status": "connected" if db_health else "disconnected"
                },
                "hybrid_mode": self.config.enable_database_backup,
                "failover_enabled": self.config.failover_to_database
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage health: {e}")
            return {"error": str(e)}
    
    async def _check_redis_health(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.redis_client.ping()
            self._redis_healthy = True
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._redis_healthy = False
            return False
    
    async def _check_database_health(self) -> bool:
        """Check database connection health."""
        try:
            async with get_async_session_context() as db:
                await db.execute(select(1))
                self._database_healthy = True
                return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            self._database_healthy = False
            return False


# Database model for session storage
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from shared.utils.database_setup import Base

class SessionStore(Base):
    """Database table for session backup storage."""
    __tablename__ = "session_store"
    
    session_id = Column(String(255), primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    metadata = Column(JSON)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


# Global session manager instance
_enhanced_session_manager: Optional[EnhancedUnifiedSessionManager] = None

async def get_enhanced_session_manager() -> EnhancedUnifiedSessionManager:
    """Get or create enhanced session manager instance."""
    global _enhanced_session_manager
    
    if _enhanced_session_manager is None:
        config = SessionConfig(
            redis_ttl=3600,  # 1 hour
            database_sync_interval=300,  # 5 minutes
            enable_database_backup=True,
            enable_session_replication=True,
            failover_to_database=True
        )
        _enhanced_session_manager = EnhancedUnifiedSessionManager(config)
        
        # Start background health checks
        asyncio.create_task(_enhanced_session_manager._start_health_monitoring())
    
    return _enhanced_session_manager