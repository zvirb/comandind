"""
Unified Error Response Handler

This module provides standardized error handling and response formatting
for all API endpoints to ensure consistent error responses across the application.
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Standard error categories for consistent classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL_SERVER = "internal_server"
    BUSINESS_LOGIC = "business_logic"
    SECURITY = "security"


class ErrorSeverity(str, Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Additional context for error tracking and debugging."""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


class StandardErrorResponse(BaseModel):
    """Standardized error response format."""
    success: bool = Field(False, description="Always false for error responses")
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class DetailedError(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    category: ErrorCategory = Field(..., description="Error category")
    severity: ErrorSeverity = Field(ErrorSeverity.MEDIUM, description="Error severity")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    suggestions: Optional[List[str]] = Field(None, description="Suggested solutions")
    documentation_url: Optional[str] = Field(None, description="Link to relevant documentation")


class UnifiedErrorHandler:
    """Unified error handler for consistent error responses across the application."""
    
    def __init__(self):
        self.logger = logger
        self._error_mappings = self._initialize_error_mappings()
    
    def _initialize_error_mappings(self) -> Dict[int, Dict[str, Any]]:
        """Initialize standard HTTP status code to error details mappings."""
        return {
            400: {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "suggestions": ["Check request format and required fields", "Validate input data"]
            },
            401: {
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "suggestions": ["Check authentication credentials", "Ensure valid access token"]
            },
            403: {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.MEDIUM,
                "suggestions": ["Verify user permissions", "Contact administrator if needed"]
            },
            404: {
                "category": ErrorCategory.NOT_FOUND,
                "severity": ErrorSeverity.LOW,
                "suggestions": ["Check resource ID or path", "Ensure resource exists"]
            },
            409: {
                "category": ErrorCategory.CONFLICT,
                "severity": ErrorSeverity.MEDIUM,
                "suggestions": ["Check for existing resources", "Resolve data conflicts"]
            },
            429: {
                "category": ErrorCategory.RATE_LIMIT,
                "severity": ErrorSeverity.MEDIUM,
                "suggestions": ["Reduce request frequency", "Implement exponential backoff"]
            },
            500: {
                "category": ErrorCategory.INTERNAL_SERVER,
                "severity": ErrorSeverity.HIGH,
                "suggestions": ["Try again later", "Contact support if issue persists"]
            },
            502: {
                "category": ErrorCategory.EXTERNAL_SERVICE,
                "severity": ErrorSeverity.HIGH,
                "suggestions": ["External service is unavailable", "Try again later"]
            },
            503: {
                "category": ErrorCategory.EXTERNAL_SERVICE,
                "severity": ErrorSeverity.HIGH,
                "suggestions": ["Service is temporarily unavailable", "Try again later"]
            }
        }
    
    def create_error_response(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> StandardErrorResponse:
        """Create standardized error response."""
        
        # Generate error code if not provided
        if not error_code:
            error_code = f"ERR_{status_code}_{uuid.uuid4().hex[:8].upper()}"
        
        # Get standard mappings for this status code
        standard_mapping = self._error_mappings.get(status_code, {
            "category": ErrorCategory.INTERNAL_SERVER,
            "severity": ErrorSeverity.MEDIUM,
            "suggestions": ["An unexpected error occurred"]
        })
        
        # Create detailed error
        detailed_error = DetailedError(
            code=error_code,
            message=message,
            category=standard_mapping["category"],
            severity=standard_mapping["severity"],
            details=details,
            suggestions=standard_mapping.get("suggestions")
        )
        
        # Create response
        response = StandardErrorResponse(
            error=detailed_error.dict(),
            request_id=context.request_id if context else None
        )
        
        # Log error with context
        self._log_error(status_code, detailed_error, context)
        
        return response
    
    def create_http_exception(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create HTTPException with standardized error response."""
        
        error_response = self.create_error_response(
            status_code=status_code,
            message=message,
            error_code=error_code,
            details=details,
            context=context
        )
        
        return HTTPException(
            status_code=status_code,
            detail=error_response.dict()
        )
    
    def create_json_response(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> JSONResponse:
        """Create JSONResponse with standardized error response."""
        
        error_response = self.create_error_response(
            status_code=status_code,
            message=message,
            error_code=error_code,
            details=details,
            context=context
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.dict()
        )
    
    def _log_error(
        self,
        status_code: int,
        error: DetailedError,
        context: Optional[ErrorContext] = None
    ) -> None:
        """Log error with appropriate level based on severity."""
        
        log_data = {
            "status_code": status_code,
            "error_code": error.code,
            "error_message": error.message,  # Renamed to avoid logging conflict
            "category": error.category,
            "severity": error.severity
        }
        
        if context:
            log_data.update(asdict(context))
        
        if error.details:
            log_data["details"] = error.details
        
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error occurred", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error occurred", extra=log_data)
        else:
            self.logger.info("Low severity error occurred", extra=log_data)
    
    # === Convenience Methods for Common Errors ===
    
    def authentication_error(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create authentication error (401)."""
        return self.create_http_exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code="AUTH_REQUIRED",
            details=details,
            context=context
        )
    
    def authorization_error(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create authorization error (403)."""
        return self.create_http_exception(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details,
            context=context
        )
    
    def validation_error(
        self,
        message: str = "Validation failed",
        field_errors: Optional[Dict[str, str]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create validation error (400)."""
        details = {"field_errors": field_errors} if field_errors else None
        return self.create_http_exception(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code="VALIDATION_FAILED",
            details=details,
            context=context
        )
    
    def not_found_error(
        self,
        resource: str = "Resource",
        resource_id: Optional[Union[str, int]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create not found error (404)."""
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        details = {"resource": resource}
        if resource_id:
            details["resource_id"] = str(resource_id)
        
        return self.create_http_exception(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=details,
            context=context
        )
    
    def conflict_error(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create conflict error (409)."""
        return self.create_http_exception(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            error_code="RESOURCE_CONFLICT",
            details=details,
            context=context
        )
    
    def rate_limit_error(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create rate limit error (429)."""
        details = {"retry_after_seconds": retry_after} if retry_after else None
        return self.create_http_exception(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
            context=context
        )
    
    def internal_server_error(
        self,
        message: str = "Internal server error",
        error_id: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create internal server error (500)."""
        details = {"error_id": error_id} if error_id else None
        return self.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
            context=context
        )
    
    def service_unavailable_error(
        self,
        service: str = "Service",
        message: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ) -> HTTPException:
        """Create service unavailable error (503)."""
        if not message:
            message = f"{service} is temporarily unavailable"
        
        return self.create_http_exception(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service},
            context=context
        )


def create_error_context(
    request: Request,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None
) -> ErrorContext:
    """Create error context from FastAPI request."""
    return ErrorContext(
        user_id=user_id,
        session_id=session_id,
        request_id=request.headers.get("X-Request-ID"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        endpoint=str(request.url.path),
        method=request.method
    )


def handle_exception(
    error_handler: UnifiedErrorHandler,
    exception: Exception,
    context: Optional[ErrorContext] = None
) -> HTTPException:
    """Handle unexpected exceptions with consistent error response."""
    
    # Generate unique error ID for tracking
    error_id = f"ERR_{uuid.uuid4().hex[:12].upper()}"
    
    # Log the full exception with stack trace
    logger.exception(f"Unhandled exception [{error_id}]: {str(exception)}", extra={
        "error_id": error_id,
        "exception_type": type(exception).__name__,
        "context": asdict(context) if context else None
    })
    
    # Return generic internal server error to client
    return error_handler.internal_server_error(
        message="An unexpected error occurred",
        error_id=error_id,
        context=context
    )


# Global error handler instance
error_handler = UnifiedErrorHandler()


# Convenience functions for direct use
def authentication_error(message: str = "Authentication required", **kwargs) -> HTTPException:
    return error_handler.authentication_error(message, **kwargs)


def authorization_error(message: str = "Insufficient permissions", **kwargs) -> HTTPException:
    return error_handler.authorization_error(message, **kwargs)


def validation_error(message: str = "Validation failed", **kwargs) -> HTTPException:
    return error_handler.validation_error(message, **kwargs)


def not_found_error(resource: str = "Resource", **kwargs) -> HTTPException:
    return error_handler.not_found_error(resource, **kwargs)


def conflict_error(message: str = "Resource conflict", **kwargs) -> HTTPException:
    return error_handler.conflict_error(message, **kwargs)


def rate_limit_error(message: str = "Rate limit exceeded", **kwargs) -> HTTPException:
    return error_handler.rate_limit_error(message, **kwargs)


def internal_server_error(message: str = "Internal server error", **kwargs) -> HTTPException:
    return error_handler.internal_server_error(message, **kwargs)


def service_unavailable_error(service: str = "Service", **kwargs) -> HTTPException:
    return error_handler.service_unavailable_error(service, **kwargs)