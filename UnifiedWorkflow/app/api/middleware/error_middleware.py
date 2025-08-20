"""
Error Handling Middleware

Provides global exception handling and consistent error responses
for all API endpoints with request tracking and monitoring.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import asyncio

from shared.utils.error_handler import (
    error_handler, create_error_context, handle_exception,
    StandardErrorResponse, ErrorSeverity
)
from shared.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling across the application."""
    
    def __init__(self, app, enable_request_tracking: bool = True):
        super().__init__(app)
        self.enable_request_tracking = enable_request_tracking
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and handle any exceptions with timeout protection."""
        
        # Generate request ID for tracking
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        
        # Add request ID to response headers
        start_time = datetime.utcnow()
        
        try:
            # Log request start if tracking enabled
            if self.enable_request_tracking:
                self._log_request_start(request, request_id)
            
            # Process request with timeout protection for OAuth/auth endpoints
            if self._is_auth_endpoint(request.url.path):
                # Apply shorter timeout for authentication endpoints to prevent hangs
                response = await asyncio.wait_for(
                    call_next(request), 
                    timeout=30.0  # 30 second timeout for auth endpoints
                )
            else:
                # Standard processing for other endpoints
                response = await call_next(request)
            
            # Log successful request if tracking enabled
            if self.enable_request_tracking:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._log_request_success(request, request_id, response.status_code, duration_ms)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except asyncio.TimeoutError:
            # Handle timeout errors specifically
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.error(
                f"Request timeout: {request.method} {request.url.path} ({duration_ms:.2f}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "timeout": True,
                    "client_host": request.client.host if request.client else None
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "message": "The request took too long to process",
                    "request_id": request_id,
                    "timeout_seconds": 30
                },
                headers={"X-Request-ID": request_id}
            )
            
        except HTTPException as http_ex:
            # Handle HTTPException (already formatted)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._log_http_exception(request, request_id, http_ex, duration_ms)
            
            # Add request ID to error response
            if isinstance(http_ex.detail, dict):
                http_ex.detail["request_id"] = request_id
            
            # Use FastAPI's default HTTP exception handler
            response = await http_exception_handler(request, http_ex)
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            # Handle unexpected exceptions
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return await self._handle_unexpected_exception(
                request, request_id, exc, duration_ms
            )
    
    def _log_request_start(self, request: Request, request_id: str) -> None:
        """Log request start information."""
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type")
            }
        )
    
    def _log_request_success(
        self, 
        request: Request, 
        request_id: str, 
        status_code: int, 
        duration_ms: float
    ) -> None:
        """Log successful request completion."""
        self.logger.info(
            f"Request completed: {request.method} {request.url.path} [{status_code}] ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else None
            }
        )
    
    def _log_http_exception(
        self, 
        request: Request, 
        request_id: str, 
        exception: HTTPException, 
        duration_ms: float
    ) -> None:
        """Log HTTP exception details."""
        log_level = logging.WARNING if exception.status_code < 500 else logging.ERROR
        
        self.logger.log(
            log_level,
            f"HTTP exception: {request.method} {request.url.path} [{exception.status_code}] ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": exception.status_code,
                "duration_ms": duration_ms,
                "exception_detail": str(exception.detail),
                "client_host": request.client.host if request.client else None
            }
        )
    
    async def _handle_unexpected_exception(
        self, 
        request: Request, 
        request_id: str, 
        exception: Exception, 
        duration_ms: float
    ) -> JSONResponse:
        """Handle unexpected exceptions with proper logging and security audit."""
        
        # Create error context
        context = create_error_context(request)
        context.request_id = request_id
        
        # Generate unique error ID
        error_id = f"ERR_{uuid.uuid4().hex[:12].upper()}"
        
        # Log the exception with full details
        self.logger.exception(
            f"Unexpected exception: {request.method} {request.url.path} [{error_id}] ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "error_id": error_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
                "stack_trace": traceback.format_exc()
            }
        )
        
        # Log security violation for potential security issues
        try:
            # This is a background task to avoid blocking the response
            asyncio.create_task(self._log_security_violation(request, exception, error_id))
        except Exception as audit_exc:
            self.logger.error(f"Failed to log security violation: {audit_exc}")
        
        # Create standardized error response
        error_response = error_handler.create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            error_code=error_id,
            details={"error_id": error_id},
            context=context
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict(),
            headers={"X-Request-ID": request_id}
        )
    
    async def _log_security_violation(
        self, 
        request: Request, 
        exception: Exception, 
        error_id: str
    ) -> None:
        """Log potential security violations for unexpected exceptions."""
        try:
            from shared.utils.database_setup import get_async_session
            
            # Get async session using generator pattern correctly
            async_session_gen = get_async_session()
            session = await anext(async_session_gen)
            
            try:
                # Determine if this might be a security-related exception
                is_security_related = any([
                    "authentication" in str(exception).lower(),
                    "authorization" in str(exception).lower(),
                    "permission" in str(exception).lower(),
                    "access" in str(exception).lower(),
                    "token" in str(exception).lower(),
                    "sql" in str(exception).lower(),
                    "injection" in str(exception).lower()
                ])
                
                if is_security_related:
                    await security_audit_service.log_security_violation(
                        session=session,
                        violation_type='UNEXPECTED_EXCEPTION_SECURITY',
                        severity='HIGH',
                        violation_details={
                            'error_id': error_id,
                            'exception_type': type(exception).__name__,
                            'exception_message': str(exception),
                            'endpoint': str(request.url.path),
                            'method': request.method,
                            'user_agent': request.headers.get("User-Agent"),
                            'potential_security_issue': True
                        },
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("User-Agent"),
                        blocked=False
                    )
            finally:
                # Properly close the session
                await session.close()
                
        except Exception as exc:
            self.logger.error(f"Failed to log security violation for error {error_id}: {exc}")
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if the path is an authentication-related endpoint."""
        auth_patterns = [
            "/api/v1/auth/",
            "/api/auth/",
            "/api/v1/oauth/",
            "/oauth/",
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/token"
        ]
        return any(path.startswith(pattern) or pattern in path for pattern in auth_patterns)


class ValidationErrorHandler:
    """Handler for FastAPI validation errors."""
    
    @staticmethod
    async def validation_exception_handler(request: Request, exc) -> JSONResponse:
        """Handle FastAPI validation exceptions with consistent format."""
        
        request_id = getattr(request.state, 'request_id', f"req_{uuid.uuid4().hex[:12]}")
        
        # Extract field errors from FastAPI validation exception
        field_errors = {}
        if hasattr(exc, 'errors'):
            for error in exc.errors():
                field_name = '.'.join(str(loc) for loc in error['loc'][1:])  # Skip 'body' prefix
                field_errors[field_name] = error['msg']
        
        # Create error context
        context = create_error_context(request)
        context.request_id = request_id
        
        # Create standardized validation error response
        error_response = error_handler.create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"field_errors": field_errors},
            context=context
        )
        
        logger.warning(
            f"Validation error: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "field_errors": field_errors,
                "client_host": request.client.host if request.client else None
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.dict(),
            headers={"X-Request-ID": request_id}
        )


def setup_error_handlers(app: FastAPI) -> None:
    """Setup all error handlers for the FastAPI application."""
    
    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware, enable_request_tracking=True)
    
    # Add validation error handler
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(
        RequestValidationError, 
        ValidationErrorHandler.validation_exception_handler
    )
    
    # Add custom HTTPException handler for consistent format
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Custom HTTP exception handler for consistent error format."""
        
        request_id = getattr(request.state, 'request_id', f"req_{uuid.uuid4().hex[:12]}")
        
        # If detail is already in our standard format, use it as-is
        if isinstance(exc.detail, dict) and 'error' in exc.detail:
            content = exc.detail
            if 'request_id' not in content:
                content['request_id'] = request_id
        else:
            # Convert to standard format
            context = create_error_context(request)
            context.request_id = request_id
            
            error_response = error_handler.create_error_response(
                status_code=exc.status_code,
                message=str(exc.detail),
                context=context
            )
            content = error_response.dict()
        
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={"X-Request-ID": request_id}
        )
    
    logger.info("Error handlers configured successfully")


# Performance monitoring decorator
def monitor_performance(endpoint_name: str):
    """Decorator to monitor endpoint performance (FastAPI compatible)."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if duration_ms > 1000:  # Log slow requests (>1s)
                    logger.warning(
                        f"Slow endpoint response: {endpoint_name} ({duration_ms:.2f}ms)",
                        extra={"endpoint": endpoint_name, "duration_ms": duration_ms}
                    )
                
                return result
            except Exception as exc:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.error(
                    f"Endpoint error: {endpoint_name} ({duration_ms:.2f}ms): {str(exc)}",
                    extra={"endpoint": endpoint_name, "duration_ms": duration_ms, "error": str(exc)}
                )
                raise
        return wrapper
    return decorator