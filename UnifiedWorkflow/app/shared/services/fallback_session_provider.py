"""
Fallback Session Provider - Local Session Storage for Redis Failures

Provides local session storage fallback when Redis circuit breaker is active.
Maintains session state during service disruptions with automatic recovery.
Designed for service boundary coordination during infrastructure failures.
"""

import logging
import time
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import threading
from pathlib import Path

from shared.services.jwt_token_adapter import NormalizedTokenData

logger = logging.getLogger(__name__)


@dataclass
class FallbackSession:
    """Local session data structure for fallback storage"""
    user_id: int
    email: str
    role: str
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    session_data: Dict[str, Any]
    token_format: str = "legacy"
    

class FallbackSessionProvider:
    """
    Local session storage provider for Redis circuit breaker failures.
    
    Features:
    - In-memory session storage with disk persistence
    - Automatic session cleanup and expiration
    - Graceful degradation during Redis outages
    - Automatic recovery when Redis returns
    - Thread-safe operations
    - Performance monitoring
    """
    
    def __init__(self, max_sessions: int = 1000, session_ttl: int = 3600):
        self.max_sessions = max_sessions
        self.session_ttl = session_ttl  # seconds
        self.sessions: Dict[str, FallbackSession] = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        self.lock = threading.RLock()
        
        # Persistence settings
        self.persistence_enabled = True
        self.persistence_file = Path(tempfile.gettempdir()) / "aiwfe_fallback_sessions.json"
        
        # Load persisted sessions on startup
        self._load_persisted_sessions()
        
        # Performance tracking
        self.stats = {
            "sessions_created": 0,
            "sessions_retrieved": 0,
            "sessions_expired": 0,
            "fallback_activations": 0,
            "redis_recoveries": 0
        }
    
    async def create_session(self, normalized_token: NormalizedTokenData, 
                           additional_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a fallback session from normalized token data.
        
        Args:
            normalized_token: Normalized JWT token data
            additional_data: Optional additional session data
            
        Returns:
            Session key for retrieval
        """
        session_key = f"fallback_session:{normalized_token.user_id}"
        
        with self.lock:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=self.session_ttl)
            
            session = FallbackSession(
                user_id=normalized_token.user_id,
                email=normalized_token.email,
                role=normalized_token.role.value,
                created_at=now,
                last_accessed=now,
                expires_at=expires_at,
                session_data=additional_data or {},
                token_format=normalized_token.format_type
            )
            
            # Check session limits
            if len(self.sessions) >= self.max_sessions:
                await self._cleanup_expired_sessions()
                
                # If still at limit, remove oldest session
                if len(self.sessions) >= self.max_sessions:
                    oldest_key = min(self.sessions.keys(), 
                                   key=lambda k: self.sessions[k].last_accessed)
                    del self.sessions[oldest_key]
                    logger.warning(f"Removed oldest session {oldest_key} due to limit")
            
            self.sessions[session_key] = session
            self.stats["sessions_created"] += 1
            
            logger.debug(f"Created fallback session {session_key} for user {normalized_token.user_id}")
            
            # Persist to disk
            await self._persist_sessions()
            
            return session_key
    
    async def get_session(self, session_key: str) -> Optional[FallbackSession]:
        """
        Retrieve a fallback session by key.
        
        Args:
            session_key: Session identifier
            
        Returns:
            FallbackSession if found and valid, None otherwise
        """
        with self.lock:
            session = self.sessions.get(session_key)
            
            if not session:
                return None
            
            now = datetime.now(timezone.utc)
            
            # Check expiration
            if session.expires_at < now:
                del self.sessions[session_key]
                self.stats["sessions_expired"] += 1
                logger.debug(f"Expired fallback session {session_key}")
                return None
            
            # Update last accessed time
            session.last_accessed = now
            self.stats["sessions_retrieved"] += 1
            
            # Periodic cleanup
            await self._periodic_cleanup()
            
            return session
    
    async def update_session(self, session_key: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.
        
        Args:
            session_key: Session identifier
            data: Data to update
            
        Returns:
            True if updated successfully, False if session not found
        """
        with self.lock:
            session = self.sessions.get(session_key)
            
            if not session:
                return False
            
            # Check expiration
            now = datetime.now(timezone.utc)
            if session.expires_at < now:
                del self.sessions[session_key]
                return False
            
            # Update data and access time
            session.session_data.update(data)
            session.last_accessed = now
            
            # Persist changes
            await self._persist_sessions()
            
            logger.debug(f"Updated fallback session {session_key}")
            return True
    
    async def delete_session(self, session_key: str) -> bool:
        """
        Delete a fallback session.
        
        Args:
            session_key: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if session_key in self.sessions:
                del self.sessions[session_key]
                logger.debug(f"Deleted fallback session {session_key}")
                
                # Persist changes
                await self._persist_sessions()
                return True
            
            return False
    
    async def get_user_session(self, user_id: int) -> Optional[FallbackSession]:
        """
        Get session by user ID (convenience method).
        
        Args:
            user_id: User identifier
            
        Returns:
            FallbackSession if found, None otherwise
        """
        session_key = f"fallback_session:{user_id}"
        return await self.get_session(session_key)
    
    async def clear_user_sessions(self, user_id: int) -> int:
        """
        Clear all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions cleared
        """
        with self.lock:
            keys_to_remove = [
                key for key, session in self.sessions.items()
                if session.user_id == user_id
            ]
            
            for key in keys_to_remove:
                del self.sessions[key]
            
            if keys_to_remove:
                await self._persist_sessions()
                logger.debug(f"Cleared {len(keys_to_remove)} sessions for user {user_id}")
            
            return len(keys_to_remove)
    
    async def validate_session_for_user(self, user_id: int, email: str) -> bool:
        """
        Validate that a session exists and matches user credentials.
        
        Args:
            user_id: User identifier
            email: User email
            
        Returns:
            True if valid session exists, False otherwise
        """
        session = await self.get_user_session(user_id)
        
        if not session:
            return False
            
        return session.email.lower() == email.lower()
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions from storage"""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, session in self.sessions.items()
            if session.expires_at < now
        ]
        
        for key in expired_keys:
            del self.sessions[key]
            self.stats["sessions_expired"] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired fallback sessions")
            await self._persist_sessions()
    
    async def _periodic_cleanup(self):
        """Perform periodic cleanup if needed"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.last_cleanup = current_time
            await self._cleanup_expired_sessions()
    
    async def _persist_sessions(self):
        """Persist sessions to disk for recovery across restarts"""
        if not self.persistence_enabled:
            return
            
        try:
            # Convert sessions to serializable format
            serializable_sessions = {}
            for key, session in self.sessions.items():
                session_dict = asdict(session)
                # Convert datetime objects to ISO strings
                session_dict["created_at"] = session.created_at.isoformat()
                session_dict["last_accessed"] = session.last_accessed.isoformat()
                session_dict["expires_at"] = session.expires_at.isoformat()
                serializable_sessions[key] = session_dict
            
            # Write to temporary file then move (atomic operation)
            temp_file = self.persistence_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump({
                    "sessions": serializable_sessions,
                    "stats": self.stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
            
            # Atomic move
            temp_file.replace(self.persistence_file)
            
        except Exception as e:
            logger.warning(f"Failed to persist fallback sessions: {e}")
    
    def _load_persisted_sessions(self):
        """Load persisted sessions from disk"""
        if not self.persistence_enabled or not self.persistence_file.exists():
            return
            
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            sessions_data = data.get("sessions", {})
            persisted_stats = data.get("stats", {})
            
            # Load sessions and check expiration
            now = datetime.now(timezone.utc)
            loaded_count = 0
            
            for key, session_dict in sessions_data.items():
                try:
                    # Convert ISO strings back to datetime objects
                    session_dict["created_at"] = datetime.fromisoformat(session_dict["created_at"])
                    session_dict["last_accessed"] = datetime.fromisoformat(session_dict["last_accessed"])
                    session_dict["expires_at"] = datetime.fromisoformat(session_dict["expires_at"])
                    
                    # Skip expired sessions
                    if session_dict["expires_at"] > now:
                        session = FallbackSession(**session_dict)
                        self.sessions[key] = session
                        loaded_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to load session {key}: {e}")
                    continue
            
            # Update stats
            self.stats.update(persisted_stats)
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} persisted fallback sessions")
                
        except Exception as e:
            logger.warning(f"Failed to load persisted sessions: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fallback session provider statistics"""
        with self.lock:
            return {
                **self.stats,
                "active_sessions": len(self.sessions),
                "max_sessions": self.max_sessions,
                "session_ttl": self.session_ttl,
                "persistence_enabled": self.persistence_enabled
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status"""
        with self.lock:
            # Check for expired sessions that need cleanup
            now = datetime.now(timezone.utc)
            expired_count = sum(1 for session in self.sessions.values() 
                              if session.expires_at < now)
            
            return {
                "status": "healthy",
                "active_sessions": len(self.sessions),
                "expired_sessions_pending_cleanup": expired_count,
                "stats": self.get_stats(),
                "storage_location": str(self.persistence_file) if self.persistence_enabled else None
            }


# Global instance for service boundary coordination
fallback_session_provider = FallbackSessionProvider()