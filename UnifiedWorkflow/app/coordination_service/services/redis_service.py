"""Redis Service for coordination and caching.

This module provides Redis integration for the coordination service, handling
workflow state caching, agent coordination, and cognitive event management.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


class RedisService:
    """Redis service for coordination and caching operations."""
    
    def __init__(
        self,
        redis_url: str,
        db: int = 0,
        max_connections: int = 20,
        retry_on_timeout: bool = True,
        socket_keepalive: bool = True,
        socket_keepalive_options: Optional[Dict[str, int]] = None
    ):
        self.redis_url = redis_url
        self.db = db
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        
        self._redis: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
        
        # Performance metrics
        self.metrics = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_operations": 0,
            "avg_response_time": 0.0,
            "connection_errors": 0
        }
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        logger.info("Initializing Redis service", url=self.redis_url, db=self.db)
        
        try:
            # Create connection pool with minimal options to avoid socket issues
            self._connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                db=self.db,
                max_connections=self.max_connections,
                retry_on_timeout=self.retry_on_timeout
            )
            
            # Create Redis client
            self._redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            
            logger.info("Redis service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis service", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self._redis:
                return False
            
            response = await self._redis.ping()
            return response is True
            
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            return False
    
    # Basic Redis Operations
    
    async def set(
        self,
        key: str,
        value: str,
        expiry_seconds: Optional[int] = None
    ) -> bool:
        """Set a key-value pair with optional expiration."""
        start_time = time.time()
        
        try:
            self.metrics["total_operations"] += 1
            
            if expiry_seconds:
                result = await self._redis.setex(key, expiry_seconds, value)
            else:
                result = await self._redis.set(key, value)
            
            self._update_response_time(start_time)
            return result is True
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis set operation failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        start_time = time.time()
        
        try:
            self.metrics["total_operations"] += 1
            
            value = await self._redis.get(key)
            
            if value is not None:
                self.metrics["cache_hits"] += 1
                self._update_response_time(start_time)
                return value.decode('utf-8') if isinstance(value, bytes) else value
            else:
                self.metrics["cache_misses"] += 1
                return None
                
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis get operation failed", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key."""
        start_time = time.time()
        
        try:
            self.metrics["total_operations"] += 1
            
            result = await self._redis.delete(key)
            
            self._update_response_time(start_time)
            return result > 0
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis delete operation failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            self.metrics["total_operations"] += 1
            result = await self._redis.exists(key)
            return result > 0
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis exists operation failed", key=key, error=str(e))
            return False
    
    # JSON Operations
    
    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        expiry_seconds: Optional[int] = None
    ) -> bool:
        """Set JSON value with optional expiration."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expiry_seconds)
            
        except Exception as e:
            logger.error("Redis set_json operation failed", key=key, error=str(e))
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value by key."""
        try:
            value = await self.get(key)
            if value:
                return json.loads(value)
            return None
            
        except Exception as e:
            logger.error("Redis get_json operation failed", key=key, error=str(e))
            return None
    
    # List Operations
    
    async def list_push(self, key: str, *values: str) -> int:
        """Push values to list (left push)."""
        try:
            self.metrics["total_operations"] += 1
            return await self._redis.lpush(key, *values)
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis list_push operation failed", key=key, error=str(e))
            return 0
    
    async def list_pop(self, key: str, timeout: int = 0) -> Optional[str]:
        """Pop value from list (blocking right pop)."""
        try:
            self.metrics["total_operations"] += 1
            
            if timeout > 0:
                result = await self._redis.brpop(key, timeout=timeout)
                return result[1].decode('utf-8') if result else None
            else:
                result = await self._redis.rpop(key)
                return result.decode('utf-8') if result else None
                
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis list_pop operation failed", key=key, error=str(e))
            return None
    
    async def list_length(self, key: str) -> int:
        """Get list length."""
        try:
            self.metrics["total_operations"] += 1
            return await self._redis.llen(key)
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis list_length operation failed", key=key, error=str(e))
            return 0
    
    # Hash Operations
    
    async def hash_set(self, key: str, field: str, value: str) -> bool:
        """Set hash field."""
        try:
            self.metrics["total_operations"] += 1
            result = await self._redis.hset(key, field, value)
            return result >= 0
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis hash_set operation failed", key=key, field=field, error=str(e))
            return False
    
    async def hash_get(self, key: str, field: str) -> Optional[str]:
        """Get hash field value."""
        try:
            self.metrics["total_operations"] += 1
            
            value = await self._redis.hget(key, field)
            
            if value is not None:
                self.metrics["cache_hits"] += 1
                return value.decode('utf-8') if isinstance(value, bytes) else value
            else:
                self.metrics["cache_misses"] += 1
                return None
                
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis hash_get operation failed", key=key, field=field, error=str(e))
            return None
    
    async def hash_get_all(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        try:
            self.metrics["total_operations"] += 1
            
            result = await self._redis.hgetall(key)
            
            if result:
                self.metrics["cache_hits"] += 1
                # Decode bytes to strings
                return {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in result.items()
                }
            else:
                self.metrics["cache_misses"] += 1
                return {}
                
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis hash_get_all operation failed", key=key, error=str(e))
            return {}
    
    # Set Operations
    
    async def set_add(self, key: str, *values: str) -> int:
        """Add values to set."""
        try:
            self.metrics["total_operations"] += 1
            return await self._redis.sadd(key, *values)
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis set_add operation failed", key=key, error=str(e))
            return 0
    
    async def set_remove(self, key: str, *values: str) -> int:
        """Remove values from set."""
        try:
            self.metrics["total_operations"] += 1
            return await self._redis.srem(key, *values)
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis set_remove operation failed", key=key, error=str(e))
            return 0
    
    async def set_members(self, key: str) -> List[str]:
        """Get all set members."""
        try:
            self.metrics["total_operations"] += 1
            
            members = await self._redis.smembers(key)
            return [
                member.decode('utf-8') if isinstance(member, bytes) else member
                for member in members
            ]
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis set_members operation failed", key=key, error=str(e))
            return []
    
    # Pub/Sub Operations for Cognitive Events
    
    async def publish_cognitive_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        channel: str = "cognitive_events"
    ) -> bool:
        """Publish cognitive event to Redis channel."""
        try:
            self.metrics["total_operations"] += 1
            
            event_message = {
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": time.time(),
                "source": "coordination_service"
            }
            
            message = json.dumps(event_message)
            result = await self._redis.publish(channel, message)
            
            logger.debug("Published cognitive event", event_type=event_type, channel=channel, subscribers=result)
            return result >= 0
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Failed to publish cognitive event", event_type=event_type, error=str(e))
            return False
    
    async def subscribe_to_cognitive_events(
        self,
        callback,
        channels: List[str] = None
    ) -> None:
        """Subscribe to cognitive events from Redis channels."""
        channels = channels or ["cognitive_events"]
        
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(*channels)
            
            logger.info("Subscribed to cognitive events", channels=channels)
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        await callback(event_data)
                        
                    except Exception as e:
                        logger.error("Error processing cognitive event", error=str(e))
                        
        except Exception as e:
            logger.error("Cognitive event subscription failed", error=str(e))
            raise
    
    # Utility Operations
    
    async def scan_keys(self, pattern: str) -> List[str]:
        """Scan keys matching pattern."""
        try:
            self.metrics["total_operations"] += 1
            
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                keys.append(key_str)
            
            return keys
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis scan_keys operation failed", pattern=pattern, error=str(e))
            return []
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        try:
            self.metrics["total_operations"] += 1
            result = await self._redis.expire(key, seconds)
            return result is True
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis expire operation failed", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time-to-live for key."""
        try:
            self.metrics["total_operations"] += 1
            return await self._redis.ttl(key)
            
        except Exception as e:
            self.metrics["failed_operations"] += 1
            logger.error("Redis ttl operation failed", key=key, error=str(e))
            return -1
    
    async def flush_db(self) -> bool:
        """Flush current database (use with caution)."""
        try:
            await self._redis.flushdb()
            logger.warning("Redis database flushed")
            return True
            
        except Exception as e:
            logger.error("Redis flush_db operation failed", error=str(e))
            return False
    
    # Performance and Monitoring
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed Redis service status."""
        try:
            info = await self._redis.info()
            
            cache_hit_rate = (
                self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
            )
            
            error_rate = (
                self.metrics["failed_operations"] / self.metrics["total_operations"]
                if self.metrics["total_operations"] > 0 else 0
            )
            
            return {
                "connection_status": "connected" if await self.health_check() else "disconnected",
                "redis_info": {
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                },
                "service_metrics": {
                    **self.metrics,
                    "cache_hit_rate": cache_hit_rate,
                    "error_rate": error_rate
                },
                "configuration": {
                    "database": self.db,
                    "max_connections": self.max_connections,
                    "retry_on_timeout": self.retry_on_timeout,
                    "socket_keepalive": self.socket_keepalive
                }
            }
            
        except Exception as e:
            logger.error("Failed to get Redis detailed status", error=str(e))
            return {
                "connection_status": "error",
                "error": str(e),
                "service_metrics": self.metrics
            }
    
    async def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_operations": 0,
            "avg_response_time": 0.0,
            "connection_errors": 0
        }
        logger.info("Redis service metrics reset")
    
    async def shutdown(self) -> None:
        """Graceful shutdown of Redis service."""
        logger.info("Shutting down Redis service...")
        
        try:
            if self._redis:
                await self._redis.close()
            
            if self._connection_pool:
                await self._connection_pool.disconnect()
            
            logger.info("Redis service shutdown complete")
            
        except Exception as e:
            logger.error("Error during Redis shutdown", error=str(e))
    
    # Private helper methods
    
    def _update_response_time(self, start_time: float) -> None:
        """Update average response time metric."""
        response_time = time.time() - start_time
        
        # Calculate running average
        total_ops = self.metrics["total_operations"]
        current_avg = self.metrics["avg_response_time"]
        
        self.metrics["avg_response_time"] = (
            (current_avg * (total_ops - 1) + response_time) / total_ops
        )