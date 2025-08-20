"""Middleware components for the Coordination Service."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with structured logging."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log incoming request
        logger.info(
            "HTTP request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log completed request
            logger.info(
                "HTTP request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                response_size=response.headers.get("content-length", "unknown")
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            # Calculate processing time for error case
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "HTTP request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Re-raise exception
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting performance metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.total_request_time = 0.0
        self.error_count = 0
        self.endpoint_metrics = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with metrics collection."""
        start_time = time.time()
        endpoint = f"{request.method} {request.url.path}"
        
        # Increment request count
        self.request_count += 1
        
        # Initialize endpoint metrics if needed
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "error_count": 0,
                "avg_time": 0.0
            }
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Update metrics
            self.total_request_time += process_time
            self.endpoint_metrics[endpoint]["count"] += 1
            self.endpoint_metrics[endpoint]["total_time"] += process_time
            self.endpoint_metrics[endpoint]["avg_time"] = (
                self.endpoint_metrics[endpoint]["total_time"] / 
                self.endpoint_metrics[endpoint]["count"]
            )
            
            # Track errors
            if response.status_code >= 400:
                self.error_count += 1
                self.endpoint_metrics[endpoint]["error_count"] += 1
            
            return response
            
        except Exception as e:
            # Calculate processing time for error case
            process_time = time.time() - start_time
            
            # Update error metrics
            self.error_count += 1
            self.total_request_time += process_time
            self.endpoint_metrics[endpoint]["count"] += 1
            self.endpoint_metrics[endpoint]["total_time"] += process_time
            self.endpoint_metrics[endpoint]["error_count"] += 1
            self.endpoint_metrics[endpoint]["avg_time"] = (
                self.endpoint_metrics[endpoint]["total_time"] / 
                self.endpoint_metrics[endpoint]["count"]
            )
            
            # Re-raise exception
            raise
    
    def get_metrics(self) -> dict:
        """Get current metrics summary."""
        avg_request_time = (
            self.total_request_time / self.request_count 
            if self.request_count > 0 else 0.0
        )
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0.0,
            "avg_request_time_ms": round(avg_request_time * 1000, 2),
            "total_request_time_seconds": round(self.total_request_time, 2),
            "endpoint_metrics": self.endpoint_metrics
        }
    
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.request_count = 0
        self.total_request_time = 0.0
        self.error_count = 0
        self.endpoint_metrics.clear()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for optional authentication."""
    
    def __init__(self, app, auth_secret: str = None, enable_auth: bool = False):
        super().__init__(app)
        self.auth_secret = auth_secret
        self.enable_auth = enable_auth
        self.public_paths = {
            "/health",
            "/status/detailed",
            "/docs",
            "/openapi.json",
            "/redoc"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with optional authentication."""
        # Skip authentication for public paths or if disabled
        if not self.enable_auth or request.url.path in self.public_paths:
            return await call_next(request)
        
        # Check for authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(
                "Authentication failed - missing or invalid auth header",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else None
            )
            return Response(
                content='{"error": "Authentication required"}',
                status_code=401,
                headers={"content-type": "application/json"}
            )
        
        # Validate token
        token = auth_header.split(" ", 1)[1]
        if token != self.auth_secret:
            logger.warning(
                "Authentication failed - invalid token",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else None
            )
            return Response(
                content='{"error": "Invalid authentication token"}',
                status_code=401,
                headers={"content-type": "application/json"}
            )
        
        # Authentication successful
        logger.debug(
            "Authentication successful",
            path=request.url.path,
            method=request.method
        )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, max_requests_per_minute: int = 1000):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.request_timestamps = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_old_timestamps(self):
        """Remove old timestamp entries."""
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute ago
        
        # Clean up old entries
        clients_to_remove = []
        for client_ip, timestamps in self.request_timestamps.items():
            # Filter out old timestamps
            recent_timestamps = [ts for ts in timestamps if ts > cutoff_time]
            
            if recent_timestamps:
                self.request_timestamps[client_ip] = recent_timestamps
            else:
                clients_to_remove.append(client_ip)
        
        # Remove clients with no recent requests
        for client_ip in clients_to_remove:
            del self.request_timestamps[client_ip]
        
        self.last_cleanup = current_time
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Periodic cleanup
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_timestamps()
        
        # Initialize client tracking if needed
        if client_ip not in self.request_timestamps:
            self.request_timestamps[client_ip] = []
        
        # Filter recent requests (last minute)
        cutoff_time = current_time - 60
        recent_requests = [
            ts for ts in self.request_timestamps[client_ip] 
            if ts > cutoff_time
        ]
        
        # Check rate limit
        if len(recent_requests) >= self.max_requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
                requests_in_last_minute=len(recent_requests),
                max_allowed=self.max_requests_per_minute
            )
            
            return Response(
                content='{"error": "Rate limit exceeded", "retry_after": 60}',
                status_code=429,
                headers={
                    "content-type": "application/json",
                    "retry-after": "60"
                }
            )
        
        # Add current request timestamp
        recent_requests.append(current_time)
        self.request_timestamps[client_ip] = recent_requests
        
        return await call_next(request)