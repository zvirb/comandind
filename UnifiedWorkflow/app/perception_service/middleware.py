"""Middleware for logging, metrics, and monitoring.

Custom middleware for comprehensive request tracking, performance monitoring,
and error handling in the Perception Service.
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'perception_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'perception_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'perception_active_requests',
    'Number of active HTTP requests'
)

REQUEST_SIZE = Histogram(
    'perception_http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

RESPONSE_SIZE = Histogram(
    'perception_http_response_size_bytes',  
    'HTTP response size in bytes',
    ['method', 'endpoint']
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware for request/response tracking.
    
    Features:
    - Request ID generation
    - Structured logging with context
    - Performance timing
    - Error tracking
    - Request/response size logging
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Start timing
        start_time = time.time()
        
        # Get request size
        content_length = request.headers.get("content-length")
        request_size = int(content_length) if content_length else 0
        
        # Create structured logger with context
        request_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) if request.url.query else None,
            client_ip=client_ip,
            user_agent=user_agent,
            request_size_bytes=request_size
        )
        
        # Add request ID to request state for access in endpoints
        request.state.request_id = request_id
        request.state.logger = request_logger
        
        # Log incoming request
        request_logger.info("Incoming request")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Get response size
            response_size = 0
            if hasattr(response, 'body'):
                response_size = len(response.body)
            
            # Log successful response
            request_logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                response_size_bytes=response_size
            )
            
            # Add performance headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            # Calculate error response time
            process_time = time.time() - start_time
            
            # Log error
            request_logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2),
                exc_info=True
            )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                    "timestamp": time.time()
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": f"{process_time:.3f}"
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies."""
        # Check for forwarded headers (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus metrics middleware for performance monitoring.
    
    Tracks:
    - Request counts by method, endpoint, and status
    - Request duration histograms
    - Active request gauge
    - Request/response sizes
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Extract endpoint pattern
        endpoint = self._get_endpoint_pattern(request)
        method = request.method
        
        # Get request size
        content_length = request.headers.get("content-length")
        request_size = int(content_length) if content_length else 0
        
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Get response size
            response_size = 0
            if hasattr(response, 'body'):
                response_size = len(response.body)
            elif hasattr(response, 'content'):
                response_size = len(response.content)
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            REQUEST_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
            
            RESPONSE_SIZE.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
            
            return response
            
        except Exception as e:
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Re-raise the exception
            raise
            
        finally:
            # Always decrement active requests
            ACTIVE_REQUESTS.dec()
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern for consistent metrics labeling."""
        path = request.url.path
        
        # Map common patterns to avoid high cardinality
        if path == "/":
            return "root"
        elif path == "/health":
            return "health"
        elif path == "/metrics":
            return "metrics"
        elif path == "/docs" or path.startswith("/docs"):
            return "docs"
        elif path == "/openapi.json":
            return "openapi"
        elif path == "/conceptualize":
            return "conceptualize"
        else:
            # For unknown paths, use a generic label to avoid metric explosion
            return "other"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Basic security middleware for production hardening.
    
    Features:
    - Security headers
    - Basic rate limiting tracking
    - Request size limits
    - Content type validation
    """
    
    def __init__(self, app, max_request_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning("Request too large", 
                         content_length=content_length,
                         max_allowed=self.max_request_size)
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
        
        # Validate content type for POST requests
        if request.method == "POST" and request.url.path == "/conceptualize":
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Content-Type must be application/json"}
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    Note: In production, consider using Redis-based rate limiting
    for distributed deployments.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests = {}  # In production, use Redis
        self.window_size = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_id, current_time):
            logger.warning("Rate limit exceeded", client_id=client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record request
        self._record_request(client_id, current_time)
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if available (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        if client_id not in self.client_requests:
            return False
        
        # Count requests in current window
        window_start = current_time - self.window_size
        requests_in_window = [
            req_time for req_time in self.client_requests[client_id]
            if req_time > window_start
        ]
        
        return len(requests_in_window) >= self.requests_per_minute
    
    def _record_request(self, client_id: str, current_time: float) -> None:
        """Record a request for rate limiting."""
        if client_id not in self.client_requests:
            self.client_requests[client_id] = []
        
        self.client_requests[client_id].append(current_time)
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove old entries to prevent memory leaks."""
        cutoff_time = current_time - self.window_size
        
        for client_id in list(self.client_requests.keys()):
            # Filter out old requests
            self.client_requests[client_id] = [
                req_time for req_time in self.client_requests[client_id]
                if req_time > cutoff_time
            ]
            
            # Remove empty entries
            if not self.client_requests[client_id]:
                del self.client_requests[client_id]