"""
Redis Service for Learning State Management
==========================================

Redis integration for learning state caching, performance tracking,
and fast access to frequently used patterns and metrics.
"""

import asyncio
import json
import logging
import os
import pickle
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis
import numpy as np

from models.patterns import LearningPattern, PatternMetrics
from config import config


logger = logging.getLogger(__name__)


class RedisService:
    """
    Service for Redis-based caching and state management for learning operations.
    
    Provides:
    - Pattern caching for fast access
    - Learning session state management  
    - Performance metrics caching
    - Pattern relationship caching
    - Batch operations for efficiency
    """
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.connected = False
        
        # Cache key prefixes
        self.PATTERN_PREFIX = "learning:pattern:"
        self.METRICS_PREFIX = "learning:metrics:"
        self.SESSION_PREFIX = "learning:session:"
        self.RELATIONSHIP_PREFIX = "learning:relationship:"
        self.PERFORMANCE_PREFIX = "learning:performance:"
        self.EMBEDDING_PREFIX = "learning:embedding:"
        
        # Cache TTL settings (seconds)
        self.PATTERN_TTL = config.pattern_cache_ttl
        self.METRICS_TTL = 3600  # 1 hour
        self.SESSION_TTL = 7200  # 2 hours
        self.PERFORMANCE_TTL = 1800  # 30 minutes
        
        logger.info("Redis Service initialized")
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            # Get Redis connection parameters from environment
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', config.redis_db))
            redis_user = os.getenv('REDIS_USER', 'lwe-app')
            redis_password = os.getenv('REDIS_PASSWORD', '')
            
            # Create Redis client with authentication
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                username=redis_user,
                password=redis_password,
                decode_responses=False,  # We'll handle encoding manually
                socket_timeout=10.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            
            logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}/{redis_db} with user {redis_user}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis Service: {e}")
            self.connected = False
            raise
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.aclose()
            self.connected = False
            logger.info("Redis connection closed")
    
    # Pattern caching methods
    
    async def cache_pattern(self, pattern: LearningPattern) -> bool:
        """Cache a learning pattern."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.PATTERN_PREFIX}{pattern.pattern_id}"
            
            # Serialize pattern
            pattern_data = self._serialize_pattern(pattern)
            
            # Store in Redis with TTL
            await self.redis_client.setex(
                key, 
                self.PATTERN_TTL, 
                pattern_data
            )
            
            # Add to pattern index
            await self._add_to_pattern_index(pattern)
            
            logger.debug(f"Cached pattern {pattern.pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching pattern: {e}")
            return False
    
    async def get_cached_pattern(self, pattern_id: str) -> Optional[LearningPattern]:
        """Retrieve a cached pattern."""
        if not self.connected:
            return None
        
        try:
            key = f"{self.PATTERN_PREFIX}{pattern_id}"
            pattern_data = await self.redis_client.get(key)
            
            if pattern_data:
                pattern = self._deserialize_pattern(pattern_data)
                logger.debug(f"Retrieved cached pattern {pattern_id}")
                return pattern
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached pattern: {e}")
            return None
    
    async def get_cached_patterns(self) -> Dict[str, LearningPattern]:
        """Retrieve all cached patterns."""
        if not self.connected:
            return {}
        
        try:
            patterns = {}
            
            # Get pattern keys
            pattern_keys = await self.redis_client.keys(f"{self.PATTERN_PREFIX}*")
            
            if pattern_keys:
                # Batch get patterns
                pattern_data_list = await self.redis_client.mget(pattern_keys)
                
                for key, pattern_data in zip(pattern_keys, pattern_data_list):
                    if pattern_data:
                        pattern_id = key.decode().replace(self.PATTERN_PREFIX, '')
                        pattern = self._deserialize_pattern(pattern_data)
                        if pattern:
                            patterns[pattern_id] = pattern
            
            logger.info(f"Retrieved {len(patterns)} cached patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving cached patterns: {e}")
            return {}
    
    async def invalidate_pattern_cache(self, pattern_id: str) -> bool:
        """Invalidate a pattern from cache."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.PATTERN_PREFIX}{pattern_id}"
            await self.redis_client.delete(key)
            
            # Remove from pattern index
            await self._remove_from_pattern_index(pattern_id)
            
            logger.debug(f"Invalidated cache for pattern {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating pattern cache: {e}")
            return False
    
    # Metrics caching methods
    
    async def cache_pattern_metrics(
        self, 
        pattern_id: str, 
        metrics: PatternMetrics
    ) -> bool:
        """Cache pattern performance metrics."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.METRICS_PREFIX}{pattern_id}"
            metrics_data = self._serialize_metrics(metrics)
            
            await self.redis_client.setex(
                key,
                self.METRICS_TTL,
                metrics_data
            )
            
            logger.debug(f"Cached metrics for pattern {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching pattern metrics: {e}")
            return False
    
    async def get_cached_metrics(self, pattern_id: str) -> Optional[PatternMetrics]:
        """Retrieve cached pattern metrics."""
        if not self.connected:
            return None
        
        try:
            key = f"{self.METRICS_PREFIX}{pattern_id}"
            metrics_data = await self.redis_client.get(key)
            
            if metrics_data:
                return self._deserialize_metrics(metrics_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached metrics: {e}")
            return None
    
    # Learning session management
    
    async def create_learning_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any]
    ) -> bool:
        """Create a learning session."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            
            session_info = {
                **session_data,
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "patterns_learned": []
            }
            
            await self.redis_client.setex(
                key,
                self.SESSION_TTL,
                json.dumps(session_info)
            )
            
            logger.info(f"Created learning session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating learning session: {e}")
            return False
    
    async def update_learning_session(
        self, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update a learning session."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            
            # Get current session data
            session_data = await self.redis_client.get(key)
            if not session_data:
                return False
            
            session_info = json.loads(session_data)
            
            # Apply updates
            session_info.update(updates)
            session_info["last_updated"] = datetime.utcnow().isoformat()
            
            # Save back to Redis
            await self.redis_client.setex(
                key,
                self.SESSION_TTL,
                json.dumps(session_info)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating learning session: {e}")
            return False
    
    async def get_learning_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a learning session."""
        if not self.connected:
            return None
        
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            session_data = await self.redis_client.get(key)
            
            if session_data:
                return json.loads(session_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving learning session: {e}")
            return None
    
    # Performance tracking
    
    async def track_performance_metric(
        self,
        metric_name: str,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track a performance metric."""
        if not self.connected:
            return False
        
        try:
            timestamp = datetime.utcnow()
            key = f"{self.PERFORMANCE_PREFIX}{metric_name}"
            
            metric_data = {
                "value": value,
                "timestamp": timestamp.isoformat(),
                "context": context or {}
            }
            
            # Add to time series
            await self.redis_client.lpush(
                key,
                json.dumps(metric_data)
            )
            
            # Keep only last 1000 entries
            await self.redis_client.ltrim(key, 0, 999)
            
            # Set TTL
            await self.redis_client.expire(key, self.PERFORMANCE_TTL)
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking performance metric: {e}")
            return False
    
    async def get_performance_metrics(
        self,
        metric_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent performance metrics."""
        if not self.connected:
            return []
        
        try:
            key = f"{self.PERFORMANCE_PREFIX}{metric_name}"
            metric_data_list = await self.redis_client.lrange(key, 0, limit - 1)
            
            metrics = []
            for metric_data in metric_data_list:
                metrics.append(json.loads(metric_data))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving performance metrics: {e}")
            return []
    
    # Pattern relationships caching
    
    async def cache_pattern_relationships(
        self,
        pattern_id: str,
        relationships: Dict[str, List[Any]]
    ) -> bool:
        """Cache pattern relationships."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.RELATIONSHIP_PREFIX}{pattern_id}"
            
            # Serialize relationships
            rel_data = {}
            for rel_type, rel_list in relationships.items():
                rel_data[rel_type] = [
                    rel.dict() if hasattr(rel, 'dict') else rel 
                    for rel in rel_list
                ]
            
            await self.redis_client.setex(
                key,
                self.PATTERN_TTL,
                json.dumps(rel_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching pattern relationships: {e}")
            return False
    
    async def get_cached_relationships(
        self, 
        pattern_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get cached pattern relationships."""
        if not self.connected:
            return {}
        
        try:
            key = f"{self.RELATIONSHIP_PREFIX}{pattern_id}"
            rel_data = await self.redis_client.get(key)
            
            if rel_data:
                return json.loads(rel_data)
            
            return {}
            
        except Exception as e:
            logger.error(f"Error retrieving cached relationships: {e}")
            return {}
    
    # Utility methods
    
    async def cache_embedding(
        self, 
        pattern_id: str, 
        embedding: np.ndarray
    ) -> bool:
        """Cache a pattern embedding."""
        if not self.connected:
            return False
        
        try:
            key = f"{self.EMBEDDING_PREFIX}{pattern_id}"
            
            # Serialize numpy array
            embedding_data = pickle.dumps(embedding)
            
            await self.redis_client.setex(
                key,
                self.PATTERN_TTL,
                embedding_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    async def get_cached_embedding(self, pattern_id: str) -> Optional[np.ndarray]:
        """Get cached pattern embedding."""
        if not self.connected:
            return None
        
        try:
            key = f"{self.EMBEDDING_PREFIX}{pattern_id}"
            embedding_data = await self.redis_client.get(key)
            
            if embedding_data:
                return pickle.loads(embedding_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            return None
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self.connected:
            return {}
        
        try:
            # Get key counts for different prefixes
            stats = {}
            
            prefixes = [
                ("patterns", self.PATTERN_PREFIX),
                ("metrics", self.METRICS_PREFIX),
                ("sessions", self.SESSION_PREFIX),
                ("relationships", self.RELATIONSHIP_PREFIX),
                ("performance", self.PERFORMANCE_PREFIX),
                ("embeddings", self.EMBEDDING_PREFIX)
            ]
            
            for name, prefix in prefixes:
                keys = await self.redis_client.keys(f"{prefix}*")
                stats[f"{name}_count"] = len(keys)
            
            # Get Redis info
            redis_info = await self.redis_client.info()
            stats.update({
                "used_memory": redis_info.get("used_memory", 0),
                "used_memory_human": redis_info.get("used_memory_human", "0B"),
                "connected_clients": redis_info.get("connected_clients", 0),
                "total_commands_processed": redis_info.get("total_commands_processed", 0)
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {}
    
    # Private methods
    
    def _serialize_pattern(self, pattern: LearningPattern) -> bytes:
        """Serialize a pattern for Redis storage."""
        return pickle.dumps(pattern.dict())
    
    def _deserialize_pattern(self, data: bytes) -> Optional[LearningPattern]:
        """Deserialize a pattern from Redis storage."""
        try:
            pattern_dict = pickle.loads(data)
            return LearningPattern(**pattern_dict)
        except Exception as e:
            logger.error(f"Error deserializing pattern: {e}")
            return None
    
    def _serialize_metrics(self, metrics: PatternMetrics) -> bytes:
        """Serialize pattern metrics."""
        return pickle.dumps(metrics.dict())
    
    def _deserialize_metrics(self, data: bytes) -> Optional[PatternMetrics]:
        """Deserialize pattern metrics."""
        try:
            metrics_dict = pickle.loads(data)
            return PatternMetrics(**metrics_dict)
        except Exception as e:
            logger.error(f"Error deserializing metrics: {e}")
            return None
    
    async def _add_to_pattern_index(self, pattern: LearningPattern) -> None:
        """Add pattern to searchable indexes."""
        try:
            # Add to type index
            type_key = f"learning:index:type:{pattern.pattern_type.value}"
            await self.redis_client.sadd(type_key, pattern.pattern_id)
            await self.redis_client.expire(type_key, self.PATTERN_TTL)
            
            # Add to scope index
            scope_key = f"learning:index:scope:{pattern.pattern_scope.value}"
            await self.redis_client.sadd(scope_key, pattern.pattern_id)
            await self.redis_client.expire(scope_key, self.PATTERN_TTL)
            
            # Add to service index
            service_key = f"learning:index:service:{pattern.source_service}"
            await self.redis_client.sadd(service_key, pattern.pattern_id)
            await self.redis_client.expire(service_key, self.PATTERN_TTL)
            
        except Exception as e:
            logger.error(f"Error adding to pattern index: {e}")
    
    async def _remove_from_pattern_index(self, pattern_id: str) -> None:
        """Remove pattern from searchable indexes."""
        try:
            # Get all index keys and remove the pattern ID
            index_keys = await self.redis_client.keys("learning:index:*")
            
            for key in index_keys:
                await self.redis_client.srem(key, pattern_id)
                
        except Exception as e:
            logger.error(f"Error removing from pattern index: {e}")