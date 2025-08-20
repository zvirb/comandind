"""
Performance tracking middleware for API response time monitoring.

This middleware tracks request/response times and integrates with
the monitoring endpoints to provide performance insights.
"""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API performance metrics including response times and error rates.
    """
    
    def __init__(self, app, exclude_paths: set = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            "/health",
            "/api/v1/health",
            "/api/health",
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/metrics",
            "/favicon.ico"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track request processing time and performance metrics.
        """
        # Skip tracking for excluded paths to avoid noise
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Add performance headers
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            # Track performance metrics
            try:
                from api.routers.monitoring_endpoints_router import track_request_performance
                track_request_performance(request, process_time)
            except ImportError:
                # Monitoring endpoints not available
                pass
            
            # Log slow requests (> 2 seconds)
            if process_time > 2.0:
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {process_time:.2f}s"
                )
            
            # Log successful request
            logger.debug(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} - {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # Track errors
            process_time = time.time() - start_time
            
            try:
                from api.routers.monitoring_endpoints_router import track_error
                track_error()
            except ImportError:
                pass
            
            # Log error with timing
            logger.error(
                f"Request error: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Time: {process_time:.3f}s",
                exc_info=True
            )
            
            # Re-raise the exception
            raise