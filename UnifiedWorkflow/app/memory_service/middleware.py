"""Middleware for logging, metrics, and request processing."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram

logger = structlog.get_logger(__name__)

# Metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True
            )
            
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for Prometheus metrics collection."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            
            # Extract endpoint pattern (remove query params and path params)
            endpoint = self._extract_endpoint(request)
            
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record failed request metrics
            duration = time.time() - start_time
            endpoint = self._extract_endpoint(request)
            
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
            raise
    
    def _extract_endpoint(self, request: Request) -> str:
        """Extract endpoint pattern from request."""
        path = request.url.path
        
        # Map specific paths to generic patterns
        if path.startswith("/memory/"):
            if "/add" in path:
                return "/memory/add"
            elif "/search" in path:
                return "/memory/search"
            else:
                return "/memory/*"
        elif path == "/health":
            return "/health"
        elif path == "/metrics":
            return "/metrics"
        elif path in ["/docs", "/redoc", "/openapi.json"]:
            return "/docs"
        else:
            return path