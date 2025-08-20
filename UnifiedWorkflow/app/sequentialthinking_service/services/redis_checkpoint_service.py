"""
Redis-based checkpointing service for LangGraph state persistence
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint

from ..config import get_settings
from ..models import CheckpointInfo, ReasoningState

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisCheckpointSaver(BaseCheckpointSaver):
    """
    Redis-based checkpoint saver for LangGraph state persistence
    Provides durable, fault-tolerant state management for reasoning sessions
    """
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__()
        self.redis = redis_client
        self.key_prefix = settings.REDIS_KEY_PREFIX
        
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[tuple]:
        """Retrieve checkpoint tuple from Redis"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                return None
                
            key = f"{self.key_prefix}{thread_id}"
            data = await self.redis.get(key)
            
            if not data:
                return None
                
            checkpoint_data = json.loads(data)
            checkpoint = Checkpoint(
                v=checkpoint_data["v"],
                ts=checkpoint_data["ts"], 
                channel_values=checkpoint_data["channel_values"],
                channel_versions=checkpoint_data["channel_versions"],
                versions_seen=checkpoint_data["versions_seen"]
            )
            
            return (checkpoint, checkpoint_data.get("metadata", {}))
            
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")
            return None
    
    async def aput(self, config: Dict[str, Any], checkpoint: Checkpoint, metadata: Dict[str, Any]) -> None:
        """Store checkpoint in Redis"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                raise ValueError("No thread_id in config")
                
            key = f"{self.key_prefix}{thread_id}"
            
            checkpoint_data = {
                "v": checkpoint.v,
                "ts": checkpoint.ts,
                "channel_values": checkpoint.channel_values,
                "channel_versions": checkpoint.channel_versions, 
                "versions_seen": checkpoint.versions_seen,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.redis.set(
                key, 
                json.dumps(checkpoint_data, default=str),
                ex=settings.CHECKPOINT_EXPIRATION_HOURS * 3600
            )
            
            logger.debug(f"Checkpoint saved for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            raise

    async def alist(self, config: Dict[str, Any]) -> List[tuple]:
        """List all checkpoints for a thread"""
        try:
            thread_id = config.get("configurable", {}).get("thread_id")
            if not thread_id:
                return []
                
            # For simplicity, return the latest checkpoint
            # In a production system, you might maintain checkpoint history
            tuple_data = await self.aget_tuple(config)
            return [tuple_data] if tuple_data else []
            
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
            return []


class RedisCheckpointService:
    """
    Service for managing Redis-based checkpoints and recovery
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.checkpoint_saver: Optional[RedisCheckpointSaver] = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize Redis connection and checkpoint saver"""
        try:
            # Create Redis connection
            redis_url = settings.REDIS_URL
            if settings.REDIS_PASSWORD:
                redis_url = redis_url.replace("redis://", f"redis://:{settings.REDIS_PASSWORD}@")
            
            self.redis = redis.from_url(
                redis_url,
                db=settings.REDIS_DB,
                decode_responses=False,  # Keep binary for JSON serialization
                retry_on_timeout=True,
                socket_timeout=30,
                socket_connect_timeout=30
            )
            
            # Test connection
            await self.redis.ping()
            
            # Create checkpoint saver
            self.checkpoint_saver = RedisCheckpointSaver(self.redis)
            
            self._initialized = True
            logger.info("Redis checkpoint service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis checkpoint service: {e}")
            raise
    
    def get_checkpoint_saver(self) -> RedisCheckpointSaver:
        """Get the checkpoint saver instance"""
        if not self._initialized or not self.checkpoint_saver:
            raise RuntimeError("Redis checkpoint service not initialized")
        return self.checkpoint_saver
    
    async def create_checkpoint_info(
        self, 
        session_id: str, 
        step_number: int, 
        state: ReasoningState
    ) -> CheckpointInfo:
        """Create checkpoint information record"""
        if not self._initialized:
            raise RuntimeError("Service not initialized")
            
        redis_key = f"{settings.REDIS_KEY_PREFIX}{session_id}"
        
        # Get checkpoint size from Redis
        size_bytes = None
        try:
            data = await self.redis.get(redis_key)
            if data:
                size_bytes = len(data)
        except Exception as e:
            logger.warning(f"Could not get checkpoint size: {e}")
        
        return CheckpointInfo(
            reasoning_session_id=session_id,
            step_number=step_number,
            state=state,
            redis_key=redis_key,
            size_bytes=size_bytes,
            is_rollback_point=step_number % 5 == 0  # Every 5th step is rollback point
        )
    
    async def get_rollback_checkpoints(self, session_id: str) -> List[CheckpointInfo]:
        """Get available rollback points for a session"""
        if not self._initialized:
            raise RuntimeError("Service not initialized")
            
        # In a full implementation, this would query checkpoint history
        # For now, return current checkpoint if it exists
        redis_key = f"{settings.REDIS_KEY_PREFIX}{session_id}"
        
        try:
            data = await self.redis.get(redis_key)
            if data:
                checkpoint_data = json.loads(data)
                return [CheckpointInfo(
                    reasoning_session_id=session_id,
                    step_number=checkpoint_data.get("metadata", {}).get("step_number", 0),
                    state=ReasoningState.COMPLETED,
                    redis_key=redis_key,
                    size_bytes=len(data),
                    created_at=datetime.fromisoformat(checkpoint_data["created_at"])
                )]
        except Exception as e:
            logger.error(f"Error getting rollback checkpoints: {e}")
            
        return []
    
    async def rollback_to_checkpoint(
        self, 
        session_id: str, 
        checkpoint_info: CheckpointInfo
    ) -> bool:
        """Rollback to a specific checkpoint"""
        if not self._initialized:
            raise RuntimeError("Service not initialized")
            
        try:
            # Verify checkpoint exists
            data = await self.redis.get(checkpoint_info.redis_key)
            if not data:
                logger.error(f"Checkpoint not found: {checkpoint_info.redis_key}")
                return False
                
            # Rollback is handled by LangGraph when loading the checkpoint
            # This method mainly validates the rollback is possible
            logger.info(f"Rollback prepared for session {session_id} to step {checkpoint_info.step_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    async def cleanup_expired_checkpoints(self) -> int:
        """Clean up expired checkpoints"""
        if not self._initialized:
            return 0
            
        try:
            pattern = f"{settings.REDIS_KEY_PREFIX}*"
            keys = await self.redis.keys(pattern)
            
            cleaned = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.CHECKPOINT_EXPIRATION_HOURS)
            
            for key in keys:
                try:
                    data = await self.redis.get(key)
                    if data:
                        checkpoint_data = json.loads(data)
                        created_at = datetime.fromisoformat(checkpoint_data["created_at"])
                        
                        if created_at < cutoff_time:
                            await self.redis.delete(key)
                            cleaned += 1
                            
                except Exception as e:
                    logger.warning(f"Error checking checkpoint {key}: {e}")
                    
            logger.info(f"Cleaned up {cleaned} expired checkpoints")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error during checkpoint cleanup: {e}")
            return 0
    
    async def get_checkpoint_stats(self) -> Dict[str, Any]:
        """Get checkpoint storage statistics"""
        if not self._initialized:
            return {}
            
        try:
            pattern = f"{settings.REDIS_KEY_PREFIX}*"
            keys = await self.redis.keys(pattern)
            
            total_size = 0
            oldest_checkpoint = None
            newest_checkpoint = None
            
            for key in keys:
                try:
                    data = await self.redis.get(key)
                    if data:
                        total_size += len(data)
                        checkpoint_data = json.loads(data)
                        created_at = datetime.fromisoformat(checkpoint_data["created_at"])
                        
                        if oldest_checkpoint is None or created_at < oldest_checkpoint:
                            oldest_checkpoint = created_at
                        if newest_checkpoint is None or created_at > newest_checkpoint:
                            newest_checkpoint = created_at
                            
                except Exception:
                    continue
            
            return {
                "total_checkpoints": len(keys),
                "total_size_bytes": total_size,
                "oldest_checkpoint": oldest_checkpoint.isoformat() if oldest_checkpoint else None,
                "newest_checkpoint": newest_checkpoint.isoformat() if newest_checkpoint else None
            }
            
        except Exception as e:
            logger.error(f"Error getting checkpoint stats: {e}")
            return {}
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis checkpoint service closed")