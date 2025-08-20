"""
Authentication Request Deduplication Middleware

This middleware prevents duplicate authentication requests from causing
database overload and infinite loops by caching identical requests
and returning cached responses.
"""

import time
import hashlib
import logging
import json
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


class AuthDeduplicationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent duplicate authentication requests.
    
    This middleware:
    1. Identifies identical auth requests within a time window
    2. Returns cached responses for duplicate requests
    3. Prevents auth endpoint flooding
    4. Reduces database load from repeated auth calls
    """
    
    def __init__(
        self,
        app,
        deduplication_window: int = 10,        # 10 second window for auth deduplication
        session_validate_window: int = 3,      # 3 second window for session validation
        max_concurrent_requests: int = 2,      # Max identical concurrent requests
        cache_successful_responses: bool = True # Cache successful auth responses
    ):
        super().__init__(app)
        self.deduplication_window = deduplication_window
        self.session_validate_window = session_validate_window
        self.max_concurrent_requests = max_concurrent_requests
        self.cache_successful_responses = cache_successful_responses
        
        # Storage for request tracking and response caching
        self.active_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.cached_responses: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            "deduplicated_requests": 0,
            "cached_responses_served": 0,
            "total_auth_requests": 0
        }
    
    def _get_user_identifier(self, request: Request) -> str:
        """Get user identifier for request deduplication."""
        # Try to get from JWT token first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
            return f"token_{token_hash}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip_{client_ip}"
    
    async def _generate_request_signature(self, request: Request) -> str:
        """Generate unique signature for request deduplication."""
        # Include user, method, path for GET requests
        user_id = self._get_user_identifier(request)
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        # For POST requests, include body hash for more precise deduplication
        body_hash = ""
        if method == "POST":
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_hash = hashlib.md5(body_bytes).hexdigest()
                    # Store body in request state for downstream middleware
                    request._body = body_bytes
            except Exception as e:
                logger.debug(f"Failed to read request body for deduplication: {e}")
        
        # Create signature
        signature_data = f"{user_id}:{method}:{path}:{query}:{body_hash}"
        return hashlib.sha256(signature_data.encode()).hexdigest()[:32]
    
    def _cleanup_old_requests(self, requests: deque, window: int):
        """Remove old request timestamps."""
        cutoff_time = time.time() - window
        while requests and requests[0] < cutoff_time:
            requests.popleft()
    
    def _cleanup_cached_responses(self, window: int):
        """Clean up old cached responses."""
        cutoff_time = time.time() - window
        expired_keys = []
        
        for key, response_data in self.cached_responses.items():
            if response_data["timestamp"] < cutoff_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cached_responses[key]
    
    def _should_deduplicate(self, path: str, method: str) -> bool:
        """Check if this auth request should be deduplicated."""
        # Focus on authentication endpoints
        auth_patterns = [
            "/api/v1/auth/", "/api/auth/", "/auth/",
            "/api/v1/session/validate"
        ]
        
        return any(path.startswith(pattern) for pattern in auth_patterns)
    
    def _get_deduplication_window(self, path: str) -> int:
        """Get deduplication window based on endpoint type."""
        # Session validation gets shorter window (more frequent calls expected)
        if "/session/validate" in path or path.endswith("/validate"):
            return self.session_validate_window
        
        # Other auth endpoints get longer window
        return self.deduplication_window
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Only apply to authentication endpoints
        if not self._should_deduplicate(request.url.path, request.method):
            return await call_next(request)
        
        # Skip WebSocket upgrades
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        if "upgrade" in connection_header and upgrade_header == "websocket":
            return await call_next(request)
        
        self.metrics["total_auth_requests"] += 1
        
        # Generate request signature
        request_signature = await self._generate_request_signature(request)
        current_time = time.time()
        deduplication_window = self._get_deduplication_window(request.url.path)
        
        # Clean up old data
        self._cleanup_old_requests(self.active_requests[request_signature], deduplication_window)
        self._cleanup_cached_responses(deduplication_window * 2)  # Keep responses longer
        
        # Check for cached response first
        cached_response = self.cached_responses.get(request_signature)
        if cached_response and (current_time - cached_response["timestamp"]) < deduplication_window:
            logger.debug(f"Serving cached auth response for {request.url.path}")
            self.metrics["cached_responses_served"] += 1
            
            return JSONResponse(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={
                    **cached_response.get("headers", {}),
                    "X-Auth-Cache": "hit",
                    "X-Deduplication": "cached_response"
                }
            )
        
        # Check for concurrent identical requests
        active_requests = self.active_requests[request_signature]
        
        if len(active_requests) >= self.max_concurrent_requests:
            logger.info(f"Blocking duplicate auth request: {request.method} {request.url.path}")
            self.metrics["deduplicated_requests"] += 1
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Duplicate authentication request",
                    "message": "Identical authentication request already in progress",
                    "retry_after": deduplication_window
                },
                headers={
                    "Retry-After": str(deduplication_window),
                    "X-Deduplication": "blocked_duplicate"
                }
            )
        
        # Record this request as active
        active_requests.append(current_time)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Cache successful auth responses
            if (self.cache_successful_responses and 
                response.status_code < 400 and 
                hasattr(response, 'body')):
                
                try:
                    # For JSON responses, cache the content
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type and response.body:
                        response_content = json.loads(response.body.decode('utf-8'))
                        
                        # Only cache certain successful responses
                        if (response.status_code == 200 and 
                            isinstance(response_content, dict) and
                            ('valid' in response_content or 'success' in response_content)):
                            
                            self.cached_responses[request_signature] = {
                                "content": response_content,
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "timestamp": current_time
                            }
                            
                            logger.debug(f"Cached auth response for {request.url.path}")
                
                except Exception as e:
                    logger.debug(f"Failed to cache auth response: {e}")
            
            # Add deduplication info to response
            response.headers["X-Deduplication"] = "original_request"
            
            return response
        
        finally:
            # Remove this request from active list
            try:
                active_requests.remove(current_time)
            except ValueError:
                pass  # Request might have been cleaned up already
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get deduplication metrics."""
        dedup_rate = 0
        cache_hit_rate = 0
        
        if self.metrics["total_auth_requests"] > 0:
            dedup_rate = (self.metrics["deduplicated_requests"] / 
                         self.metrics["total_auth_requests"] * 100)
            cache_hit_rate = (self.metrics["cached_responses_served"] / 
                            self.metrics["total_auth_requests"] * 100)
        
        return {
            **self.metrics,
            "deduplication_rate_percent": round(dedup_rate, 2),
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "active_signatures": len(self.active_requests),
            "cached_responses": len(self.cached_responses)
        }
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = {key: 0 for key in self.metrics}
    
    def clear_cache(self):
        """Clear all cached responses and active requests."""
        self.cached_responses.clear()
        self.active_requests.clear()