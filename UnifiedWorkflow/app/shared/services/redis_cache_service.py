"""
Redis Caching Service for High-Performance Data Access

This service provides optimized caching for user preferences, session data,
and frequently accessed database content to improve application performance.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import asyncio
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
import pickle
import hashlib

from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    avg_response_time_ms: float = 0.0

class RedisCache:
    """High-performance Redis caching service with metrics and health monitoring."""
    
    def __init__(self):
        self.config = get_settings()
        self.pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.metrics = CacheMetrics()
        self.health_check_interval = 30  # seconds
        self._last_health_check = datetime.now()
        self._is_healthy = False
        
        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.session_ttl = 1800  # 30 minutes  
        self.user_preferences_ttl = 7200  # 2 hours
        self.dashboard_ttl = 300  # 5 minutes
        self.auth_ttl = 900  # 15 minutes
        
    async def initialize(self) -> bool:
        """Initialize Redis connection pool and client."""
        try:
            # Use the computed Redis URL from settings (includes authentication)
            redis_url = self.config.redis_url
            logger.debug(f"Using Redis URL from settings: {redis_url}")
            
            # Create connection pool for optimal performance
            self.pool = ConnectionPool.from_url(
                redis_url,
                max_connections=50,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis_client.ping()
            self._is_healthy = True
            self._last_health_check = datetime.now()
            
            logger.info("Redis cache service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self._is_healthy = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Redis connection."""
        try:
            if not self.redis_client:
                return False
                
            # Check if enough time has passed since last health check
            if (datetime.now() - self._last_health_check).seconds < self.health_check_interval:
                return self._is_healthy
            
            # Perform actual health check
            await self.redis_client.ping()
            self._is_healthy = True
            self._last_health_check = datetime.now()
            
            return True
            
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_healthy = False
            return False
    
    def _generate_cache_key(self, prefix: str, identifier: Union[str, int], suffix: str = "") -> str:
        """Generate consistent cache keys."""
        key_parts = [prefix, str(identifier)]
        if suffix:
            key_parts.append(suffix)
        
        base_key = ":".join(key_parts)
        
        # Hash long keys to prevent Redis key length issues
        if len(base_key) > 200:
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
        
        return base_key
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with metrics tracking."""
        start_time = datetime.now()
        
        try:
            if not await self.health_check():
                self.metrics.errors += 1
                return default
            
            result = await self.redis_client.get(key)
            
            if result is not None:
                self.metrics.hits += 1
                try:
                    # Try JSON first, fall back to pickle
                    return json.loads(result)
                except json.JSONDecodeError:
                    return pickle.loads(result)
            else:
                self.metrics.misses += 1
                return default
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.metrics.errors += 1
            return default
        finally:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_avg_response_time(response_time)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL and metrics tracking."""
        try:
            if not await self.health_check():
                self.metrics.errors += 1
                return False
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Serialize value
            try:
                serialized_value = json.dumps(value)
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                serialized_value = pickle.dumps(value)
            
            result = await self.redis_client.set(key, serialized_value, ex=ttl)
            
            if result:
                self.metrics.sets += 1
                return True
            else:
                self.metrics.errors += 1
                return False
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if not await self.health_check():
                self.metrics.errors += 1
                return False
            
            result = await self.redis_client.delete(key)
            
            if result:
                self.metrics.deletes += 1
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            if not await self.health_check():
                return 0
            
            # Use SCAN to find keys matching pattern
            keys_to_delete = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys_to_delete.append(key)
            
            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)
                self.metrics.deletes += deleted_count
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            self.metrics.errors += 1
            return 0
    
    def _update_avg_response_time(self, response_time_ms: float):
        """Update average response time metric."""
        total_operations = self.metrics.hits + self.metrics.misses + self.metrics.sets
        if total_operations > 0:
            self.metrics.avg_response_time_ms = (
                (self.metrics.avg_response_time_ms * (total_operations - 1) + response_time_ms) / 
                total_operations
            )
    
    # === USER PREFERENCES CACHING ===
    
    async def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences from cache."""
        key = self._generate_cache_key("user_prefs", user_id)
        return await self.get(key)
    
    async def set_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Cache user preferences."""
        key = self._generate_cache_key("user_prefs", user_id)
        return await self.set(key, preferences, ttl=self.user_preferences_ttl)
    
    async def invalidate_user_preferences(self, user_id: int) -> bool:
        """Invalidate user preferences cache."""
        key = self._generate_cache_key("user_prefs", user_id)
        return await self.delete(key)
    
    # === SESSION DATA CACHING ===
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from cache."""
        key = self._generate_cache_key("session", session_id)
        return await self.get(key)
    
    async def set_session_data(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Cache session data."""
        key = self._generate_cache_key("session", session_id) 
        return await self.set(key, session_data, ttl=self.session_ttl)
    
    async def invalidate_session_data(self, session_id: str) -> bool:
        """Invalidate session data cache."""
        key = self._generate_cache_key("session", session_id)
        return await self.delete(key)
    
    async def invalidate_user_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        pattern = f"session:*user:{user_id}*"
        return await self.delete_pattern(pattern)
    
    # === DASHBOARD DATA CACHING ===
    
    async def get_dashboard_data(self, user_id: int, dashboard_type: str) -> Optional[Dict[str, Any]]:
        """Get dashboard data from cache."""
        key = self._generate_cache_key("dashboard", user_id, dashboard_type)
        return await self.get(key)
    
    async def set_dashboard_data(self, user_id: int, dashboard_type: str, data: Dict[str, Any]) -> bool:
        """Cache dashboard data."""
        key = self._generate_cache_key("dashboard", user_id, dashboard_type)
        return await self.set(key, data, ttl=self.dashboard_ttl)
    
    async def invalidate_dashboard_data(self, user_id: int, dashboard_type: str = None) -> int:
        """Invalidate dashboard data cache."""
        if dashboard_type:
            key = self._generate_cache_key("dashboard", user_id, dashboard_type)
            return 1 if await self.delete(key) else 0
        else:
            pattern = f"dashboard:{user_id}:*"
            return await self.delete_pattern(pattern)
    
    # === AUTHENTICATION CACHING ===
    
    async def get_user_auth_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user authentication data from cache."""
        key = self._generate_cache_key("user_auth", user_id)
        return await self.get(key)
    
    async def set_user_auth_data(self, user_id: int, auth_data: Dict[str, Any]) -> bool:
        """Cache user authentication data."""
        key = self._generate_cache_key("user_auth", user_id)
        return await self.set(key, auth_data, ttl=self.auth_ttl)
    
    async def invalidate_user_auth_data(self, user_id: int) -> bool:
        """Invalidate user authentication data cache."""
        key = self._generate_cache_key("user_auth", user_id)
        return await self.delete(key)
    
    # === TOKEN VALIDATION CACHING ===
    
    async def get_token_validation(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get token validation result from cache."""
        key = self._generate_cache_key("token_validation", token_hash)
        return await self.get(key)
    
    async def set_token_validation(self, token_hash: str, validation_result: Dict[str, Any], ttl: int = None) -> bool:
        """Cache token validation result."""
        key = self._generate_cache_key("token_validation", token_hash)
        # Use shorter TTL for token validation (5 minutes by default)
        cache_ttl = ttl or 300
        return await self.set(key, validation_result, ttl=cache_ttl)
    
    async def invalidate_token_validation(self, token_hash: str) -> bool:
        """Invalidate token validation cache."""
        key = self._generate_cache_key("token_validation", token_hash)
        return await self.delete(key)
    
    async def get_session_validation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session validation result from cache."""
        key = self._generate_cache_key("session_validation", session_id)
        return await self.get(key)
    
    async def set_session_validation(self, session_id: str, validation_result: Dict[str, Any]) -> bool:
        """Cache session validation result."""
        key = self._generate_cache_key("session_validation", session_id)
        # Use shorter TTL for session validation (2 minutes)
        return await self.set(key, validation_result, ttl=120)
    
    async def invalidate_session_validation(self, session_id: str) -> bool:
        """Invalidate session validation cache."""
        key = self._generate_cache_key("session_validation", session_id)
        return await self.delete(key)
    
    # === DEVICE MANAGEMENT CACHING ===
    
    async def get_device_data(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device data from cache."""
        key = self._generate_cache_key("device", device_id)
        return await self.get(key)
    
    async def set_device_data(self, device_id: str, device_data: Dict[str, Any]) -> bool:
        """Cache device data."""
        key = self._generate_cache_key("device", device_id)
        return await self.set(key, device_data, ttl=self.auth_ttl)
    
    async def invalidate_device_data(self, device_id: str) -> bool:
        """Invalidate device data cache."""
        key = self._generate_cache_key("device", device_id)
        return await self.delete(key)
    
    async def invalidate_user_devices(self, user_id: int) -> int:
        """Invalidate all cached devices for a user."""
        pattern = f"device:*user:{user_id}*"
        return await self.delete_pattern(pattern)
    
    # === METRICS AND MONITORING ===
    
    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        total_operations = self.metrics.hits + self.metrics.misses
        hit_rate = (self.metrics.hits / total_operations * 100) if total_operations > 0 else 0
        
        # Get Redis info
        redis_info = {}
        try:
            if self.redis_client and await self.health_check():
                info = await self.redis_client.info()
                redis_info = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
                }
        except Exception as e:
            logger.warning(f"Failed to get Redis info: {e}")
        
        return {
            "cache_metrics": asdict(self.metrics),
            "hit_rate_percent": round(hit_rate, 2),
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat(),
            "redis_info": redis_info
        }
    
    async def reset_metrics(self):
        """Reset cache metrics."""
        self.metrics = CacheMetrics()
    
    async def close(self):
        """Close Redis connection."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.pool:
                await self.pool.disconnect()
            logger.info("Redis cache service closed")
        except Exception as e:
            logger.error(f"Error closing Redis cache: {e}")

# Global cache instance
redis_cache = RedisCache()

async def get_redis_cache() -> RedisCache:
    """Get the global Redis cache instance."""
    if not redis_cache._is_healthy:
        await redis_cache.initialize()
    return redis_cache