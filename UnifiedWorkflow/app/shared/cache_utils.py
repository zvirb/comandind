"""
Advanced Redis Caching Utility with Performance Monitoring and Advanced Patterns

Features:
- Comprehensive caching strategy
- Performance tracking
- Advanced cache warming
- Memory optimization
- Metrics generation
"""

import time
import json
import asyncio
import functools
from typing import Any, Callable, Optional

import redis.asyncio as async_redis
import redis

class CacheManager:
    def __init__(
        self, 
        redis_url: str, 
        namespace: str = "app_cache",
        default_ttl: int = 3600  # 1 hour default
    ):
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.sync_redis = redis.from_url(redis_url)
        self.async_redis = async_redis.from_url(redis_url)
        
        # Metrics tracking
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "cache_size": 0,
            "errors": 0
        }
    
    def _get_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.namespace}:{key}"
    
    def get_metrics(self) -> dict:
        """Retrieve current cache metrics."""
        self.metrics['cache_size'] = len(self.sync_redis.keys(f"{self.namespace}:*"))
        self.metrics['hit_ratio'] = (
            self.metrics['hits'] / self.metrics['total_requests'] 
            if self.metrics['total_requests'] > 0 else 0
        )
        return self.metrics
    
    def cache(
        self, 
        key: Optional[str] = None, 
        ttl: Optional[int] = None,
        serialize: Callable[[Any], str] = json.dumps,
        deserialize: Callable[[str], Any] = json.loads
    ):
        """
        Advanced decorator for caching function results.
        
        :param key: Optional custom cache key generator
        :param ttl: Optional time-to-live for the cache entry
        :param serialize: Function to serialize data to cache
        :param deserialize: Function to deserialize data from cache
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                self.metrics['total_requests'] += 1
                
                # Generate cache key
                cache_key = key or f"{func.__module__}.{func.__name__}"
                cache_key = self._get_key(cache_key)
                
                try:
                    # Check cache first
                    cached_result = await self.async_redis.get(cache_key)
                    
                    if cached_result:
                        self.metrics['hits'] += 1
                        return deserialize(cached_result)
                    
                    # Cache miss - compute and cache result
                    self.metrics['misses'] += 1
                    result = await func(*args, **kwargs)
                    
                    # Store in cache
                    await self.async_redis.setex(
                        cache_key, 
                        ttl or self.default_ttl, 
                        serialize(result)
                    )
                    
                    return result
                
                except Exception as e:
                    self.metrics['errors'] += 1
                    raise
            
            return wrapper
        return decorator

    async def warm_cache(self, key_pattern: str, warming_func: Callable):
        """
        Preemptively warm cache for specific keys.
        
        :param key_pattern: Redis key pattern to match
        :param warming_func: Function to generate cache entries
        """
        keys = self.sync_redis.keys(key_pattern)
        
        async def _warm_key(key):
            start_time = time.time()
            try:
                await warming_func(key)
                duration = time.time() - start_time
                print(f"Warmed cache for {key} in {duration:.2f}s")
            except Exception as e:
                print(f"Cache warming failed for {key}: {e}")
        
        await asyncio.gather(*[_warm_key(key) for key in keys])

# Example Usage in other modules
# from shared.cache_utils import CacheManager
# cache_manager = CacheManager(redis_url='redis://localhost:6379')
#
# @cache_manager.cache(key='user_profile', ttl=3600)
# async def get_user_profile(user_id):
#     # Fetch user profile from database
#     pass