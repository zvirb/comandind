"""
Learning Service Middleware
==========================

Middleware components for request/response processing,
logging, metrics collection, and error handling.
"""

import time
import logging
from typing import Callable
from contextlib import contextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} - "
                f"Process time: {process_time:.3f}s"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request failed: {str(e)} - Process time: {process_time:.3f}s")
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting performance metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.total_time = 0.0
        self.error_count = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        self.request_count += 1
        
        try:
            response = await call_next(request)
            
            process_time = time.time() - start_time
            self.total_time += process_time
            
            return response
            
        except Exception as e:
            self.error_count += 1
            process_time = time.time() - start_time
            self.total_time += process_time
            raise
    
    @property
    def average_response_time(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_time / self.request_count
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


def setup_middleware(app: FastAPI):
    """Setup all middleware for the FastAPI app."""
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    logger.info("Middleware setup completed")