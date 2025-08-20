"""Redis service for cognitive state management and caching.

Provides async Redis operations for reasoning state persistence,
caching, and event coordination in the cognitive architecture.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Union
import redis.asyncio as redis
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class RedisService:
    """Async Redis service for cognitive state management."""
    
    def __init__(
        self,
        url: str,
        timeout: int = 5,
        max_connections: int = 20,
        retry_on_timeout: bool = True
    ):
        self.url = url
        self.timeout = timeout
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection pool and client."""
        try:
            # Create async Redis client directly from URL
            # Note: password is already included in the URL
            self._client = redis.from_url(
                self.url,
                max_connections=self.max_connections,
                socket_connect_timeout=self.timeout,
                socket_timeout=self.timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=True,
                encoding="utf-8"
            )
            
            # Test connection
            await self._client.ping()
            logger.info("Redis service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis service", error=str(e))
            raise
    
    def _get_client(self) -> redis.Redis:
        """Get Redis client, raising error if not initialized."""
        if self._client is None:
            raise RuntimeError("Redis service not initialized. Call initialize() first.")
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def health_check(self) -> bool:
        """Check Redis connectivity and responsiveness."""
        try:
            client = self._get_client()
            start_time = time.time()
            
            # Ping and simple operation
            await client.ping()
            await client.set("health_check", str(time.time()), ex=10)
            
            latency = time.time() - start_time
            logger.info("Redis health check passed", latency_ms=round(latency * 1000, 2))
            return True
            
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    # Cognitive State Management
    
    async def store_reasoning_state(
        self,
        reasoning_id: str,
        state: Dict[str, Any],
        expire_seconds: int = 3600
    ) -> bool:
        """Store reasoning chain state for later retrieval."""
        try:
            client = self._get_client()
            key = f"reasoning:state:{reasoning_id}"
            
            # Store with expiration
            await client.setex(
                key,
                expire_seconds,
                json.dumps(state, default=str)
            )
            
            logger.debug("Reasoning state stored", reasoning_id=reasoning_id)
            return True
            
        except Exception as e:
            logger.error("Failed to store reasoning state", 
                        reasoning_id=reasoning_id, error=str(e))
            return False
    
    async def get_reasoning_state(self, reasoning_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve reasoning chain state."""
        try:
            client = self._get_client()
            key = f"reasoning:state:{reasoning_id}"
            
            state_data = await client.get(key)
            if state_data:
                return json.loads(state_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get reasoning state", 
                        reasoning_id=reasoning_id, error=str(e))
            return None
    
    async def update_reasoning_state(
        self,
        reasoning_id: str,
        updates: Dict[str, Any],
        expire_seconds: int = 3600
    ) -> bool:
        """Update existing reasoning state with new information."""
        try:
            # Get current state
            current_state = await self.get_reasoning_state(reasoning_id)
            if current_state is None:
                current_state = {}
            
            # Merge updates
            current_state.update(updates)
            
            # Store updated state
            return await self.store_reasoning_state(reasoning_id, current_state, expire_seconds)
            
        except Exception as e:
            logger.error("Failed to update reasoning state", 
                        reasoning_id=reasoning_id, error=str(e))
            return False
    
    # Caching for Performance
    
    async def cache_evidence_validation(
        self,
        evidence_hash: str,
        validation_result: Dict[str, Any],
        expire_seconds: int = 1800  # 30 minutes
    ) -> bool:
        """Cache evidence validation results to avoid reprocessing."""
        try:
            client = self._get_client()
            key = f"cache:evidence:{evidence_hash}"
            
            cache_data = {
                "validation_result": validation_result,
                "timestamp": time.time(),
                "expires_at": time.time() + expire_seconds
            }
            
            await client.setex(
                key,
                expire_seconds,
                json.dumps(cache_data, default=str)
            )
            
            logger.debug("Evidence validation cached", evidence_hash=evidence_hash)
            return True
            
        except Exception as e:
            logger.error("Failed to cache evidence validation", 
                        evidence_hash=evidence_hash, error=str(e))
            return False
    
    async def get_cached_evidence_validation(
        self,
        evidence_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached evidence validation result."""
        try:
            client = self._get_client()
            key = f"cache:evidence:{evidence_hash}"
            
            cache_data = await client.get(key)
            if cache_data:
                cached = json.loads(cache_data)
                # Check if still valid
                if cached.get("expires_at", 0) > time.time():
                    logger.debug("Evidence validation cache hit", evidence_hash=evidence_hash)
                    return cached["validation_result"]
                else:
                    # Expired, delete key
                    await client.delete(key)
                    logger.debug("Evidence validation cache expired", evidence_hash=evidence_hash)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached evidence validation", 
                        evidence_hash=evidence_hash, error=str(e))
            return None
    
    # Cognitive Event Coordination
    
    async def publish_cognitive_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        channel: str = "cognitive_events"
    ) -> bool:
        """Publish cognitive event for coordination service."""
        try:
            client = self._get_client()
            
            event_message = {
                "event_type": event_type,
                "timestamp": time.time(),
                "service": "reasoning_service",
                "data": event_data
            }
            
            await client.publish(channel, json.dumps(event_message, default=str))
            logger.info("Cognitive event published", 
                       event_type=event_type, channel=channel)
            return True
            
        except Exception as e:
            logger.error("Failed to publish cognitive event", 
                        event_type=event_type, error=str(e))
            return False
    
    async def subscribe_to_cognitive_events(
        self,
        channels: List[str],
        callback_func
    ):
        """Subscribe to cognitive events for coordination."""
        try:
            client = self._get_client()
            pubsub = client.pubsub()
            
            # Subscribe to channels
            for channel in channels:
                await pubsub.subscribe(channel)
                logger.info("Subscribed to cognitive channel", channel=channel)
            
            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        await callback_func(message["channel"], event_data)
                    except Exception as e:
                        logger.error("Error processing cognitive event", 
                                   channel=message["channel"], error=str(e))
            
        except Exception as e:
            logger.error("Failed to subscribe to cognitive events", error=str(e))
            raise
    
    # Performance and Analytics
    
    async def record_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
        expire_seconds: int = 86400  # 24 hours
    ) -> bool:
        """Record performance metrics for monitoring."""
        try:
            client = self._get_client()
            timestamp = int(time.time())
            
            # Create metric key with timestamp
            key = f"metrics:{metric_name}:{timestamp}"
            
            metric_data = {
                "name": metric_name,
                "value": value,
                "timestamp": timestamp,
                "tags": tags or {}
            }
            
            await client.setex(
                key,
                expire_seconds,
                json.dumps(metric_data)
            )
            
            # Also update running statistics
            stats_key = f"stats:{metric_name}"
            pipe = client.pipeline()
            pipe.hincrby(stats_key, "count", 1)
            pipe.hincrbyfloat(stats_key, "sum", float(value))
            pipe.hset(stats_key, "last_value", value)
            pipe.hset(stats_key, "last_updated", timestamp)
            pipe.expire(stats_key, expire_seconds)
            await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error("Failed to record performance metric", 
                        metric_name=metric_name, error=str(e))
            return False
    
    async def get_performance_stats(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a metric."""
        try:
            client = self._get_client()
            stats_key = f"stats:{metric_name}"
            
            stats = await client.hgetall(stats_key)
            if stats:
                count = int(stats.get("count", 0))
                total_sum = float(stats.get("sum", 0))
                
                return {
                    "metric_name": metric_name,
                    "count": count,
                    "sum": total_sum,
                    "average": total_sum / count if count > 0 else 0,
                    "last_value": float(stats.get("last_value", 0)),
                    "last_updated": int(stats.get("last_updated", 0))
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get performance stats", 
                        metric_name=metric_name, error=str(e))
            return None
    
    # Utility Methods
    
    async def set_with_expiry(
        self,
        key: str,
        value: Any,
        expire_seconds: int
    ) -> bool:
        """Set key with expiration."""
        try:
            client = self._get_client()
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            await client.setex(key, expire_seconds, str(value))
            return True
            
        except Exception as e:
            logger.error("Failed to set key with expiry", key=key, error=str(e))
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get and parse JSON value."""
        try:
            client = self._get_client()
            value = await client.get(key)
            
            if value:
                return json.loads(value)
            return None
            
        except Exception as e:
            logger.error("Failed to get JSON value", key=key, error=str(e))
            return None
    
    async def delete(self, *keys: str) -> int:
        """Delete keys and return count of deleted keys."""
        try:
            client = self._get_client()
            return await client.delete(*keys)
            
        except Exception as e:
            logger.error("Failed to delete keys", keys=keys, error=str(e))
            return 0
    
    async def close(self):
        """Close Redis connection pool."""
        try:
            if self._client:
                await self._client.close()
            if self._pool:
                await self._pool.disconnect()
                
            logger.info("Redis service closed")
            
        except Exception as e:
            logger.error("Error closing Redis service", error=str(e))