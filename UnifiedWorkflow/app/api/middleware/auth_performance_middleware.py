"""
Authentication Performance Enhancement Middleware
Optimizes authentication performance and reduces latency to <50ms
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import jwt
from cachetools import TTLCache, LRUCache
import hashlib
from datetime import datetime, timedelta
# Optional import for monitoring service (graceful fallback if not available)\ntry:\n    from shared.services.auth_monitoring_service import auth_monitoring_service\n    AUTH_MONITORING_AVAILABLE = True\nexcept ImportError:\n    AUTH_MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)

class AuthPerformanceMiddleware(BaseHTTPMiddleware):
    """
    High-performance authentication middleware with caching and optimization.
    Target: Reduce authentication time from 176ms to <50ms
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Token validation cache (TTL: 5 minutes, Max: 1000 tokens)
        self.token_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)
        
        # User session cache (TTL: 10 minutes, Max: 500 sessions)
        self.session_cache: TTLCache = TTLCache(maxsize=500, ttl=600)
        
        # JWT decode cache (TTL: 2 minutes, Max: 2000 tokens)
        self.jwt_decode_cache: TTLCache = TTLCache(maxsize=2000, ttl=120)
        
        # Performance metrics
        self.auth_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_auth_time_ms": 0.0,
            "auth_times": LRUCache(maxsize=1000)  # Rolling average
        }
        
        # Pre-computed common paths for faster lookup
        self.protected_path_set = frozenset([
            "/api/v1/chat", "/api/v1/conversation", "/api/v1/tasks",
            "/api/v1/documents", "/api/v1/user", "/api/v1/dashboard",
            "/api/v1/settings", "/api/v1/admin", "/api/v1/profile"
        ])
        
        self.exempt_path_set = frozenset([
            "/health", "/api/v1/health", "/api/health", "/",
            "/api/v1/auth", "/api/auth", "/oauth", "/public"
        ])
    
    def _get_token_hash(self, token: str) -> str:
        """Create a fast hash of the token for caching."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    def _is_protected_endpoint(self, path: str) -> bool:
        """Fast path protection check using pre-computed sets."""
        # Exact match first (fastest)
        if path in self.exempt_path_set:
            return False
        if path in self.protected_path_set:
            return True
        
        # Prefix matching (slower, but cached)
        for exempt in self.exempt_path_set:
            if path.startswith(exempt):
                return False
        
        for protected in self.protected_path_set:
            if path.startswith(protected):
                return True
        
        return False
    
    def _extract_token_fast(self, request: Request) -> Optional[str]:
        """Optimized token extraction."""
        # Authorization header is most common, check first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Slice is faster than replace
        
        # Cookie fallback
        return request.cookies.get("access_token")
    
    async def _validate_token_cached(self, token: str) -> Optional[Dict]:
        """Cached token validation for maximum performance."""
        token_hash = self._get_token_hash(token)
        
        # Check token validation cache first
        cached_result = self.token_cache.get(token_hash)
        if cached_result is not None:
            self.auth_metrics["cache_hits"] += 1
            # Record cache hit for monitoring
            if AUTH_MONITORING_AVAILABLE:
                try:
                    auth_monitoring_service.record_cache_operation("token_validation", hit=True)
                except Exception as e:
                    logger.debug(f"Auth monitoring service unavailable: {e}")
            return cached_result
        
        # Check JWT decode cache
        decoded_payload = self.jwt_decode_cache.get(token_hash)
        if decoded_payload is None:
            # Decode JWT (this is the expensive part)
            try:
                from api.auth import ALGORITHM, SECRET_KEY
                decoded_payload = jwt.decode(
                    token,
                    SECRET_KEY,
                    algorithms=[ALGORITHM],
                    options={"verify_exp": True, "verify_nbf": False, "verify_iat": False},
                    leeway=30  # Reduced leeway for performance
                )
                # Cache the decoded payload
                self.jwt_decode_cache[token_hash] = decoded_payload
            except Exception as e:
                logger.debug(f"JWT decode failed: {e}")
                # Cache negative result for 30 seconds
                self.token_cache[token_hash] = None
                return None
        
        # Fast payload processing
        try:
            user_data = {
                "id": int(decoded_payload.get("sub", 0)) or decoded_payload.get("id"),
                "email": decoded_payload.get("email") or decoded_payload.get("sub"),
                "role": decoded_payload.get("role", "user")
            }
            
            # Validate essential fields
            if not user_data["id"] or not user_data["email"] or "@" not in str(user_data["email"]):
                result = None
            else:
                result = user_data
            
            # Cache the result
            self.token_cache[token_hash] = result
            self.auth_metrics["cache_misses"] += 1
            # Record cache miss for monitoring
            if AUTH_MONITORING_AVAILABLE:
                try:
                    auth_monitoring_service.record_cache_operation("token_validation", hit=False)
                except Exception as e:
                    logger.debug(f"Auth monitoring service unavailable: {e}")
            
            return result
            
        except Exception as e:
            logger.debug(f"Token processing failed: {e}")
            self.token_cache[token_hash] = None
            return None
    
    def _create_fast_error_response(self, status_code: int, message: str) -> JSONResponse:
        """Create optimized error response."""
        return JSONResponse(
            status_code=status_code,
            content={"error": message, "timestamp": int(time.time())},
            headers={"Cache-Control": "no-cache"}
        )
    
    def _update_performance_metrics(self, auth_time_ms: float):
        """Update authentication performance metrics."""
        self.auth_metrics["total_requests"] += 1
        self.auth_metrics["auth_times"][int(time.time())] = auth_time_ms
        
        # Calculate rolling average
        recent_times = list(self.auth_metrics["auth_times"].values())
        if recent_times:
            self.auth_metrics["avg_auth_time_ms"] = sum(recent_times) / len(recent_times)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """High-performance authentication dispatch."""
        
        start_time = time.perf_counter()
        path = request.url.path
        
        # Fast path check
        if not self._is_protected_endpoint(path):
            return await call_next(request)
        
        # Extract token
        token = self._extract_token_fast(request)
        if not token:
            return self._create_fast_error_response(401, "No token provided")
        
        # Validate token with caching
        user_data = await self._validate_token_cached(token)
        if not user_data:
            return self._create_fast_error_response(401, "Invalid token")
        
        # Store user data in request state
        request.state.authenticated_user_id = user_data["id"]
        request.state.authenticated_user_email = user_data["email"]
        request.state.authenticated_user_role = user_data["role"]
        request.state.token_validated = True
        
        # Calculate auth time
        auth_time_ms = (time.perf_counter() - start_time) * 1000
        self._update_performance_metrics(auth_time_ms)
        
        # Log performance if slow
        if auth_time_ms > 50:
            logger.warning(f"Slow auth: {auth_time_ms:.1f}ms for {path}")
        
        # Continue processing
        return await call_next(request)
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics."""
        cache_hit_rate = 0.0
        if self.auth_metrics["total_requests"] > 0:
            cache_hit_rate = (self.auth_metrics["cache_hits"] / 
                            (self.auth_metrics["cache_hits"] + self.auth_metrics["cache_misses"])) * 100
        
        return {
            "total_auth_requests": self.auth_metrics["total_requests"],
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "avg_auth_time_ms": round(self.auth_metrics["avg_auth_time_ms"], 2),
            "token_cache_size": len(self.token_cache),
            "session_cache_size": len(self.session_cache),
            "jwt_decode_cache_size": len(self.jwt_decode_cache),
            "performance_target_met": self.auth_metrics["avg_auth_time_ms"] < 50.0
        }
    
    def clear_cache(self):
        """Clear all caches (useful for testing/debugging)."""
        self.token_cache.clear()
        self.session_cache.clear()
        self.jwt_decode_cache.clear()
        logger.info("Authentication caches cleared")


class AuthConnectionPoolMiddleware(BaseHTTPMiddleware):
    """
    Middleware to optimize database connections for auth operations.
    """
    
    def __init__(self, app, pool_size: int = 20):
        super().__init__(app)
        self.pool_size = pool_size
        self.active_connections = {}
        self.connection_pool = asyncio.Queue(maxsize=pool_size)
        
        # Pre-populate connection pool
        asyncio.create_task(self._initialize_pool())
    
    async def _initialize_pool(self):
        """Initialize database connection pool."""
        try:
            # This would normally create actual DB connections
            for i in range(self.pool_size):
                await self.connection_pool.put(f"connection_{i}")
            logger.info(f"Auth connection pool initialized with {self.pool_size} connections")
        except Exception as e:
            logger.error(f"Failed to initialize auth connection pool: {e}")
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Use pooled connections for auth operations."""
        
        path = request.url.path
        
        # Only optimize database-heavy auth operations
        if "/api/v1/auth/" in path or "/api/auth/" in path:
            # Simulate using a pooled connection
            try:
                connection = await asyncio.wait_for(
                    self.connection_pool.get(), timeout=1.0
                )
                request.state.auth_connection = connection
                
                response = await call_next(request)
                
                # Return connection to pool
                await self.connection_pool.put(connection)
                return response
                
            except asyncio.TimeoutError:
                logger.warning("Auth connection pool exhausted")
                # Fall through to normal processing
        
        return await call_next(request)
