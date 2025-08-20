"""Middleware components for the Reasoning Service.

Provides structured logging, metrics collection, and request processing
middleware for production-ready cognitive service deployment.
"""

import time
import uuid
from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    'reasoning_requests_total', 
    'Total reasoning service requests', 
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'reasoning_request_duration_seconds', 
    'Reasoning service request duration'
)
COGNITIVE_OPERATIONS = Counter(
    'reasoning_cognitive_operations_total',
    'Total cognitive operations performed',
    ['operation_type', 'status']
)
REASONING_ACCURACY = Histogram(
    'reasoning_accuracy_score',
    'Reasoning accuracy scores',
    ['reasoning_type']
)
EVIDENCE_VALIDATION_SCORE = Histogram(
    'reasoning_evidence_validation_score', 
    'Evidence validation scores'
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging middleware for request tracking."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        url = str(request.url)
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request start
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=method,
            path=path,
            client_host=client_host,
            user_agent=user_agent
        )
        
        # Add request ID to state for downstream use
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful completion
            self.logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors too
            processing_time = time.time() - start_time
            
            # Log error
            self.logger.error(
                "Request failed",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2),
                exc_info=True
            )
            
            # Re-raise exception
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Prometheus metrics collection middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Normalize endpoint for metrics (remove IDs, etc.)
        normalized_endpoint = self._normalize_endpoint(path)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            processing_time = time.time() - start_time
            status_category = self._get_status_category(response.status_code)
            
            REQUEST_COUNT.labels(
                method=method, 
                endpoint=normalized_endpoint, 
                status=status_category
            ).inc()
            
            REQUEST_DURATION.observe(processing_time)
            
            # Record cognitive operation metrics if applicable
            if self._is_cognitive_endpoint(path):
                operation_type = self._extract_operation_type(path)
                COGNITIVE_OPERATIONS.labels(
                    operation_type=operation_type,
                    status="success"
                ).inc()
            
            return response
            
        except Exception as e:
            # Record error metrics
            processing_time = time.time() - start_time
            
            REQUEST_COUNT.labels(
                method=method, 
                endpoint=normalized_endpoint, 
                status="error"
            ).inc()
            
            REQUEST_DURATION.observe(processing_time)
            
            # Record cognitive operation errors
            if self._is_cognitive_endpoint(path):
                operation_type = self._extract_operation_type(path)
                COGNITIVE_OPERATIONS.labels(
                    operation_type=operation_type,
                    status="error"
                ).inc()
            
            # Re-raise exception
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for consistent metrics."""
        # Remove query parameters
        path = path.split("?")[0]
        
        # Normalize common patterns
        if path.startswith("/validate/"):
            return "/validate/*"
        elif path.startswith("/decide/"):
            return "/decide/*"
        elif path.startswith("/test/"):
            return "/test/*"
        elif path.startswith("/reasoning/"):
            return "/reasoning/*"
        else:
            return path
    
    def _get_status_category(self, status_code: int) -> str:
        """Categorize HTTP status codes for metrics."""
        if 200 <= status_code < 300:
            return "success"
        elif 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "other"
    
    def _is_cognitive_endpoint(self, path: str) -> bool:
        """Check if endpoint is a cognitive operation."""
        cognitive_paths = [
            "/validate/evidence",
            "/decide/multi-criteria", 
            "/test/hypothesis",
            "/reasoning/chain"
        ]
        return any(path.startswith(cp) for cp in cognitive_paths)
    
    def _extract_operation_type(self, path: str) -> str:
        """Extract operation type from path."""
        if "/validate/" in path:
            return "evidence_validation"
        elif "/decide/" in path:
            return "decision_analysis"
        elif "/test/" in path:
            return "hypothesis_testing"
        elif "/reasoning/" in path:
            return "reasoning_chain"
        else:
            return "unknown"


class CognitiveMetricsMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for cognitive operation metrics."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Record cognitive-specific metrics based on response
        try:
            if response.status_code == 200 and hasattr(response, '_content'):
                await self._record_cognitive_metrics(request, response)
        except Exception as e:
            logger.warning("Failed to record cognitive metrics", error=str(e))
        
        return response
    
    async def _record_cognitive_metrics(self, request: Request, response: Response):
        """Record cognitive operation specific metrics."""
        path = request.url.path
        
        # This would ideally parse response JSON, but that's complex in middleware
        # Instead, we'll rely on the endpoints to record their own metrics
        # This middleware serves as a placeholder for future enhancements
        
        pass


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security headers and validation middleware."""
    
    def __init__(self, app, enable_cors: bool = True):
        super().__init__(app)
        self.enable_cors = enable_cors
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Security validation
        if not self._validate_request_security(request):
            return Response(
                content="Request validation failed",
                status_code=400,
                headers={"X-Error": "Security validation failed"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _validate_request_security(self, request: Request) -> bool:
        """Validate request for security concerns."""
        # Check for obviously malicious patterns
        path = request.url.path.lower()
        
        # Block common attack patterns
        malicious_patterns = [
            "../", "..\\", "script>", "<script", "javascript:",
            "eval(", "exec(", "system(", "shell_exec"
        ]
        
        for pattern in malicious_patterns:
            if pattern in path or pattern in str(request.query_params):
                logger.warning("Blocked malicious request pattern", 
                             pattern=pattern, path=path)
                return False
        
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10_000_000:  # 10MB limit
            logger.warning("Blocked oversized request", 
                         content_length=content_length)
            return False
        
        return True
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response."""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_timestamps: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client identifier
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Clean old timestamps
        self._clean_old_timestamps(client_id, current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_id, current_time):
            logger.warning("Rate limit exceeded", client_id=client_id)
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Record request timestamp
        if client_id not in self.request_timestamps:
            self.request_timestamps[client_id] = []
        self.request_timestamps[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(self.request_timestamps.get(client_id, [])))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use IP address as identifier (in production, might use API keys)
        return request.client.host if request.client else "unknown"
    
    def _clean_old_timestamps(self, client_id: str, current_time: float):
        """Remove timestamps older than 1 minute."""
        if client_id in self.request_timestamps:
            minute_ago = current_time - 60
            self.request_timestamps[client_id] = [
                ts for ts in self.request_timestamps[client_id] 
                if ts > minute_ago
            ]
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """Check if client has exceeded rate limit."""
        if client_id not in self.request_timestamps:
            return False
        
        return len(self.request_timestamps[client_id]) >= self.requests_per_minute


def get_request_id(request: Request) -> str:
    """Extract request ID from request state."""
    return getattr(request.state, "request_id", "unknown")