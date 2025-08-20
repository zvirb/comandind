"""
Cached Authentication Middleware

This middleware enhances authentication performance by caching token validation
results in Redis to reduce database load and prevent repeated JWT decoding.
"""

import time
import logging
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from fastapi.responses import JSONResponse

from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)


class CachedAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware with Redis caching for improved performance.
    
    This middleware:
    1. Checks Redis cache for token validation results before database lookup
    2. Caches successful authentication results to reduce database load
    3. Implements intelligent cache invalidation
    4. Provides fallback to standard authentication if cache fails
    """
    
    def __init__(
        self,
        app,
        cache_ttl: int = 300,              # 5 minute cache TTL for auth results
        session_cache_ttl: int = 120,      # 2 minute cache TTL for session validation
        enable_metrics: bool = True        # Track cache hit/miss metrics
    ):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.session_cache_ttl = session_cache_ttl
        self.enable_metrics = enable_metrics
        
        # Metrics tracking
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_errors": 0,
            "auth_calls": 0,
            "session_calls": 0
        }
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers."""
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None
    
    def _generate_token_hash(self, token: str) -> str:
        """Generate a hash of the token for cache key."""
        return hashlib.sha256(token.encode()).hexdigest()[:32]
    
    def _is_session_validation_endpoint(self, path: str) -> bool:
        """Check if this is a session validation endpoint."""
        return (
            path.endswith("/validate") or 
            path.endswith("/session/validate") or
            "/session/validate" in path
        )
    
    def _should_cache_auth(self, path: str, method: str) -> bool:
        """Determine if this authentication should be cached."""
        # Skip caching for sensitive operations
        skip_patterns = [
            "/login", "/register", "/logout", "/refresh"
        ]
        
        # Don't cache POST operations that modify state
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return False
        
        # Don't cache if path contains sensitive operations
        if any(pattern in path.lower() for pattern in skip_patterns):
            return False
        
        return True
    
    def _exempt_from_auth(self, path: str) -> bool:
        """Check if endpoint is exempt from authentication."""
        exempt_patterns = [
            "/health", "/api/v1/health", "/api/health",
            "/metrics", "/docs", "/openapi.json",
            "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/auth/refresh", "/api/v1/auth/csrf-token",
            "/api/v1/public", "/public",
            "/ws/", "/api/ws/", "/api/v1/ws/"
        ]
        
        return any(path.startswith(pattern) for pattern in exempt_patterns)
    
    async def _get_cached_auth_result(self, token_hash: str, is_session_validation: bool = False) -> Optional[Dict[str, Any]]:
        """Get cached authentication result."""
        try:
            redis_cache = await get_redis_cache()
            
            if is_session_validation:
                result = await redis_cache.get_session_validation(token_hash)
            else:
                result = await redis_cache.get_token_validation(token_hash)
            
            if result:
                # Check if cached result is still valid
                cached_time = result.get("cached_at")
                if cached_time:
                    cache_age = time.time() - cached_time
                    max_age = self.session_cache_ttl if is_session_validation else self.cache_ttl
                    
                    if cache_age > max_age:
                        # Cache expired, remove it
                        if is_session_validation:
                            await redis_cache.invalidate_session_validation(token_hash)
                        else:
                            await redis_cache.invalidate_token_validation(token_hash)
                        return None
                
                if self.enable_metrics:
                    self.metrics["cache_hits"] += 1
                
                return result
            
            if self.enable_metrics:
                self.metrics["cache_misses"] += 1
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached auth result: {e}")
            if self.enable_metrics:
                self.metrics["cache_errors"] += 1
            return None
    
    async def _cache_auth_result(self, token_hash: str, auth_result: Dict[str, Any], is_session_validation: bool = False):
        """Cache authentication result."""
        try:
            redis_cache = await get_redis_cache()
            
            # Add timestamp to cached result
            cached_result = {
                **auth_result,
                "cached_at": time.time()
            }
            
            if is_session_validation:
                await redis_cache.set_session_validation(token_hash, cached_result)
            else:
                ttl = self.cache_ttl
                await redis_cache.set_token_validation(token_hash, cached_result, ttl=ttl)
            
        except Exception as e:
            logger.warning(f"Error caching auth result: {e}")
            if self.enable_metrics:
                self.metrics["cache_errors"] += 1
    
    async def _validate_token_with_cache(self, request: Request, token: str) -> Optional[Dict[str, Any]]:
        """Validate token using cache-first approach."""
        token_hash = self._generate_token_hash(token)
        is_session_validation = self._is_session_validation_endpoint(request.url.path)
        
        # Try cache first
        if self._should_cache_auth(request.url.path, request.method):
            cached_result = await self._get_cached_auth_result(token_hash, is_session_validation)
            if cached_result:
                # Restore user to request state from cache
                user_data = cached_result.get("user")
                if user_data:
                    # Create a mock user object for request state
                    class MockUser:
                        def __init__(self, data):
                            for key, value in data.items():
                                setattr(self, key, value)
                    
                    request.state.user = MockUser(user_data)
                    request.state.cached_auth = True
                
                return cached_result
        
        # Cache miss - perform actual authentication
        try:
            # Import authentication dependencies directly to avoid circular imports
            from api.dependencies import get_current_user_payload
            from shared.utils.database_setup import get_async_session_context
            
            # Create mock request for token validation
            class MockRequest:
                def __init__(self, token):
                    self.headers = {"authorization": f"Bearer {token}"}
                    self.cookies = {}
            
            # Validate token using existing auth system
            mock_request = MockRequest(token)
            token_data = get_current_user_payload(mock_request)
            
            # Get user from database
            from shared.utils.database_setup import get_async_session_context
            async with get_async_session_context() as db:
                from sqlalchemy import select
                from shared.database.models import User
                result = await db.execute(
                    select(User).where(
                        User.id == token_data.id,
                        User.is_active == True
                    )
                )
                user = result.scalar_one_or_none()
            if not user:
                return None
            
            # Create auth result
            auth_result = {
                "valid": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_active": user.is_active
                },
                "token_hash": token_hash,
                "validated_at": time.time()
            }
            
            # Cache the result
            if self._should_cache_auth(request.url.path, request.method):
                await self._cache_auth_result(token_hash, auth_result, is_session_validation)
            
            # Set user in request state
            request.state.user = user
            request.state.cached_auth = False
            
            return auth_result
            
        except Exception as e:
            logger.debug(f"Token validation failed: {e}")
            return None
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Track metrics
        if self.enable_metrics:
            if self._is_session_validation_endpoint(request.url.path):
                self.metrics["session_calls"] += 1
            else:
                self.metrics["auth_calls"] += 1
        
        # Skip authentication for exempt endpoints
        if self._exempt_from_auth(request.url.path):
            return await call_next(request)
        
        # Skip WebSocket upgrades
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        if "upgrade" in connection_header and upgrade_header == "websocket":
            return await call_next(request)
        
        # Extract token
        token = self._extract_token(request)
        if not token:
            # No token provided, let the request continue to be handled by endpoint
            return await call_next(request)
        
        # Validate token with caching
        auth_result = await self._validate_token_with_cache(request, token)
        
        if not auth_result or not auth_result.get("valid"):
            # Invalid token
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add cache info to response headers for debugging
        response = await call_next(request)
        
        if hasattr(request.state, 'cached_auth'):
            response.headers["X-Auth-Cache"] = "hit" if request.state.cached_auth else "miss"
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authentication caching metrics."""
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        hit_rate = (self.metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = {key: 0 for key in self.metrics}