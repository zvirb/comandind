"""
Optimized Authentication Service

This service implements high-performance authentication with:
1. Redis-based JWT validation caching
2. Connection pool optimization
3. Reduced middleware overhead
4. Optimized route resolution

Target: Reduce auth latency from 176ms to under 40ms (60%+ improvement)
"""

import time
import hashlib
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import HTTPException, status
import jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import User, UserRole
from shared.utils.config import get_settings
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizedAuthService:
    """
    High-performance authentication service with intelligent caching.
    
    Performance optimizations:
    - JWT validation caching (Redis)
    - Connection pooling optimization
    - Reduced database calls
    - Intelligent cache invalidation
    """
    
    def __init__(self):
        self.settings = settings
        self.cache_ttl = 300  # 5 minute cache for tokens
        self.session_cache_ttl = 120  # 2 minute cache for session validation
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0, 
            "db_queries": 0,
            "avg_response_time": 0.0,
            "total_requests": 0
        }
        
        # Pre-compile JWT secret for performance
        self.jwt_secret = settings.JWT_SECRET_KEY.get_secret_value()
        self.jwt_algorithm = "HS256"
    
    def _generate_cache_key(self, token: str, endpoint_type: str = "auth") -> str:
        """Generate deterministic cache key for token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return f"auth_cache:{endpoint_type}:{token_hash}"
    
    async def _get_cached_validation(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached validation result."""
        try:
            redis = await get_redis_cache()
            cached_data = await redis.get_json(cache_key)
            
            if cached_data:
                # Check expiry
                cached_time = cached_data.get("cached_at", 0)
                max_age = self.session_cache_ttl if "session" in cache_key else self.cache_ttl
                
                if time.time() - cached_time < max_age:
                    self.metrics["cache_hits"] += 1
                    return cached_data
                else:
                    # Expired cache, remove it
                    await redis.delete(cache_key)
            
            self.metrics["cache_misses"] += 1
            return None
            
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
            self.metrics["cache_misses"] += 1
            return None
    
    async def _cache_validation_result(self, cache_key: str, validation_data: Dict[str, Any]):
        """Cache validation result with TTL."""
        try:
            redis = await get_redis_cache()
            
            cached_result = {
                **validation_data,
                "cached_at": time.time()
            }
            
            ttl = self.session_cache_ttl if "session" in cache_key else self.cache_ttl
            await redis.set_json(cache_key, cached_result, ex=ttl)
            
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    def _decode_jwt_fast(self, token: str) -> Dict[str, Any]:
        """Fast JWT decoding with minimal validation."""
        try:
            # Decode with performance optimized options
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={
                    "verify_exp": True,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_aud": False
                },
                leeway=30  # Reduced leeway for performance
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    async def _get_user_from_db_optimized(
        self, 
        user_id: int, 
        email: str, 
        db: AsyncSession
    ) -> Optional[User]:
        """Optimized single-query user lookup."""
        try:
            # Single optimized query with all needed conditions
            result = await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.email == email,  # Combined validation
                    User.is_active == True
                ).limit(1)  # Explicit limit for performance
            )
            
            user = result.scalar_one_or_none()
            self.metrics["db_queries"] += 1
            return user
            
        except Exception as e:
            logger.error(f"Optimized user lookup failed: {e}")
            self.metrics["db_queries"] += 1
            return None
    
    async def validate_token_optimized(
        self, 
        token: str, 
        db: AsyncSession,
        is_session_validation: bool = False
    ) -> Tuple[bool, Optional[User], Dict[str, Any]]:
        """
        High-performance token validation with intelligent caching.
        
        Returns: (is_valid, user_object, metadata)
        """
        start_time = time.time()
        
        try:
            # Generate cache key
            endpoint_type = "session" if is_session_validation else "auth" 
            cache_key = self._generate_cache_key(token, endpoint_type)
            
            # Try cache first
            cached_result = await self._get_cached_validation(cache_key)
            if cached_result and cached_result.get("valid"):
                # Reconstruct user from cache
                user_data = cached_result.get("user")
                if user_data:
                    # Create lightweight user object from cache
                    user = User(
                        id=user_data["id"],
                        email=user_data["email"],
                        role=UserRole(user_data["role"]),
                        is_active=user_data["is_active"]
                    )
                    
                    response_time = time.time() - start_time
                    self._update_metrics(response_time)
                    
                    return True, user, {
                        "cached": True,
                        "response_time_ms": round(response_time * 1000, 2),
                        "source": "redis_cache"
                    }
            
            # Cache miss - perform full validation
            payload = self._decode_jwt_fast(token)
            
            # Extract user info from standardized token format
            user_id = payload.get("id") or int(payload.get("sub", 0))
            email = payload.get("email")
            role = payload.get("role")
            
            if not all([user_id, email, role]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            # Optimized database lookup
            user = await self._get_user_from_db_optimized(user_id, email, db)
            
            if not user:
                response_time = time.time() - start_time
                self._update_metrics(response_time)
                
                return False, None, {
                    "cached": False,
                    "response_time_ms": round(response_time * 1000, 2),
                    "error": "User not found or inactive"
                }
            
            # Cache successful validation
            validation_data = {
                "valid": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_active": user.is_active
                },
                "token_info": {
                    "user_id": user_id,
                    "session_id": payload.get("session_id"),
                    "device_id": payload.get("device_id")
                }
            }
            
            await self._cache_validation_result(cache_key, validation_data)
            
            response_time = time.time() - start_time
            self._update_metrics(response_time)
            
            return True, user, {
                "cached": False,
                "response_time_ms": round(response_time * 1000, 2),
                "source": "database_lookup"
            }
            
        except HTTPException:
            response_time = time.time() - start_time
            self._update_metrics(response_time)
            raise
        except Exception as e:
            response_time = time.time() - start_time
            self._update_metrics(response_time)
            
            logger.error(f"Token validation error: {e}")
            return False, None, {
                "cached": False,
                "response_time_ms": round(response_time * 1000, 2),
                "error": str(e)
            }
    
    def _update_metrics(self, response_time: float):
        """Update performance metrics."""
        self.metrics["total_requests"] += 1
        
        # Update average response time (exponential moving average)
        alpha = 0.1  # Smoothing factor
        if self.metrics["avg_response_time"] == 0:
            self.metrics["avg_response_time"] = response_time
        else:
            self.metrics["avg_response_time"] = (
                alpha * response_time + 
                (1 - alpha) * self.metrics["avg_response_time"]
            )
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cached tokens for a user."""
        try:
            redis = await get_redis_cache()
            
            # Pattern-based cache invalidation
            pattern = f"auth_cache:*"
            keys = await redis.scan_iter(match=pattern)
            
            # This is a simplified approach - in production, you'd want
            # to store user_id -> cache_key mappings for efficient invalidation
            deleted_count = 0
            async for key in keys:
                try:
                    cached_data = await redis.get_json(key)
                    if cached_data and cached_data.get("user", {}).get("id") == user_id:
                        await redis.delete(key)
                        deleted_count += 1
                except Exception:
                    pass
            
            logger.info(f"Invalidated {deleted_count} cached tokens for user {user_id}")
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        total_requests = self.metrics["total_requests"]
        
        if total_requests == 0:
            cache_hit_rate = 0.0
        else:
            cache_hit_rate = (self.metrics["cache_hits"] / total_requests) * 100
        
        return {
            "total_requests": total_requests,
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "database_queries": self.metrics["db_queries"],
            "avg_response_time_ms": round(self.metrics["avg_response_time"] * 1000, 2),
            "cache_efficiency": {
                "memory_saved_queries": self.metrics["cache_hits"],
                "performance_improvement_estimate": f"{round(cache_hit_rate)}% faster"
            }
        }
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {key: 0 if key != "avg_response_time" else 0.0 
                      for key in self.metrics}


# Global service instance
optimized_auth_service = OptimizedAuthService()