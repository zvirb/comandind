"""
Request protection middleware for server-side safeguards against request flooding.

This module implements:
- Task-specific rate limiting
- Request deduplication
- Circuit breaker patterns for failing requests
"""

import time
import hashlib
import logging
import json
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class TaskRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting middleware specifically for task endpoints.
    Implements stricter limits for task operations to prevent frontend flooding.
    """
    
    def __init__(
        self, 
        app,
        task_calls: int = 10,          # Tasks requests per minute per user
        task_period: int = 60,         # Time window for tasks
        subtask_calls: int = 5,        # Subtask generation per 10 minutes
        subtask_period: int = 600,     # 10 minute window for subtasks
        general_calls: int = 200,      # General API calls
        general_period: int = 60       # General time window
    ):
        super().__init__(app)
        self.task_calls = task_calls
        self.task_period = task_period
        self.subtask_calls = subtask_calls
        self.subtask_period = subtask_period
        self.general_calls = general_calls
        self.general_period = general_period
        
        # Storage for rate limiting data per user
        self.user_task_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_subtask_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_general_requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from authenticated request or fall back to IP."""
        # Try to get user from authentication
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.id}"
        
        # Try to get from JWT token (simplified extraction)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                # In a real implementation, you'd decode the JWT properly
                # For now, we'll use the token as identifier
                token_hash = hashlib.md5(auth_header.encode()).hexdigest()
                return f"token_{token_hash}"
            except Exception:
                pass
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip_{client_ip}"
    
    def _cleanup_old_requests(self, requests: deque, period: int) -> None:
        """Remove requests older than the specified period."""
        cutoff_time = time.time() - period
        while requests and requests[0] < cutoff_time:
            requests.popleft()
    
    def _is_task_endpoint(self, path: str) -> bool:
        """Check if the request is for a task-related endpoint."""
        return path.startswith("/api/v1/tasks")
    
    def _is_subtask_generation(self, path: str, method: str) -> bool:
        """Check if the request is for subtask generation (most resource-intensive)."""
        return (
            path.endswith("/subtasks/generate") and 
            method == "POST" and
            "/api/v1/tasks/" in path
        )
    
    def _check_rate_limits(self, user_id: str, path: str, method: str) -> Tuple[bool, str, Dict[str, int]]:
        """
        Check all applicable rate limits for the request.
        Returns (is_limited, reason, retry_headers).
        """
        current_time = time.time()
        
        # Check subtask generation rate limit (most restrictive)
        if self._is_subtask_generation(path, method):
            subtask_requests = self.user_subtask_requests[user_id]
            self._cleanup_old_requests(subtask_requests, self.subtask_period)
            
            if len(subtask_requests) >= self.subtask_calls:
                remaining_time = self.subtask_period - (current_time - subtask_requests[0])
                return True, f"Subtask generation rate limit exceeded: {self.subtask_calls} per {self.subtask_period//60} minutes", {
                    "X-RateLimit-Limit-Subtasks": str(self.subtask_calls),
                    "X-RateLimit-Remaining-Subtasks": "0",
                    "X-RateLimit-Reset-Subtasks": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            # Record the request
            subtask_requests.append(current_time)
        
        # Check task endpoint rate limit
        elif self._is_task_endpoint(path):
            task_requests = self.user_task_requests[user_id]
            self._cleanup_old_requests(task_requests, self.task_period)
            
            if len(task_requests) >= self.task_calls:
                remaining_time = self.task_period - (current_time - task_requests[0])
                return True, f"Task endpoint rate limit exceeded: {self.task_calls} per minute", {
                    "X-RateLimit-Limit-Tasks": str(self.task_calls),
                    "X-RateLimit-Remaining-Tasks": "0", 
                    "X-RateLimit-Reset-Tasks": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            # Record the request
            task_requests.append(current_time)
        
        # Check general rate limit
        general_requests = self.user_general_requests[user_id]
        self._cleanup_old_requests(general_requests, self.general_period)
        
        if len(general_requests) >= self.general_calls:
            remaining_time = self.general_period - (current_time - general_requests[0])
            return True, f"General rate limit exceeded: {self.general_calls} per minute", {
                "X-RateLimit-Limit": str(self.general_calls),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(current_time + remaining_time)),
                "Retry-After": str(int(remaining_time))
            }
        
        # Record the request
        general_requests.append(current_time)
        
        # Calculate remaining limits for headers
        task_remaining = max(0, self.task_calls - len(self.user_task_requests[user_id])) if self._is_task_endpoint(path) else self.task_calls
        subtask_remaining = max(0, self.subtask_calls - len(self.user_subtask_requests[user_id])) if self._is_subtask_generation(path, method) else self.subtask_calls
        general_remaining = max(0, self.general_calls - len(general_requests))
        
        headers = {
            "X-RateLimit-Limit": str(self.general_calls),
            "X-RateLimit-Remaining": str(general_remaining),
            "X-RateLimit-Reset": str(int(current_time + self.general_period))
        }
        
        if self._is_task_endpoint(path):
            headers.update({
                "X-RateLimit-Limit-Tasks": str(self.task_calls),
                "X-RateLimit-Remaining-Tasks": str(task_remaining),
                "X-RateLimit-Reset-Tasks": str(int(current_time + self.task_period))
            })
        
        if self._is_subtask_generation(path, method):
            headers.update({
                "X-RateLimit-Limit-Subtasks": str(self.subtask_calls),
                "X-RateLimit-Remaining-Subtasks": str(subtask_remaining),
                "X-RateLimit-Reset-Subtasks": str(int(current_time + self.subtask_period))
            })
        
        return False, "", headers
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Skip rate limiting for health checks, auth endpoints, and WebSocket connections
        exempt_paths = [
            "/health", "/api/v1/health", "/api/v1/auth", "/api/auth", 
            "/ws/", "/api/v1/ws/", "/api/ws/"
        ]
        
        # Also skip WebSocket upgrade requests
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        is_websocket_upgrade = "upgrade" in connection_header and upgrade_header == "websocket"
        
        if any(request.url.path.startswith(path) for path in exempt_paths) or is_websocket_upgrade:
            return await call_next(request)
        
        user_id = self._get_user_id(request)
        is_limited, reason, headers = self._check_rate_limits(
            user_id, request.url.path, request.method
        )
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for user {user_id}: {reason} on {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": reason,
                    "user_id": user_id,
                    "path": request.url.path,
                    "timestamp": datetime.now().isoformat()
                },
                headers=headers
            )
        
        # Process the request and add rate limit headers to response
        response = await call_next(request)
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """
    Request deduplication middleware to prevent identical concurrent requests.
    Particularly important for task operations to prevent double-processing.
    """
    
    def __init__(
        self, 
        app,
        deduplication_window: int = 5,     # Window in seconds to check for duplicates
        max_concurrent_requests: int = 3   # Max concurrent identical requests per user
    ):
        super().__init__(app)
        self.deduplication_window = deduplication_window
        self.max_concurrent_requests = max_concurrent_requests
        
        # Storage for active requests
        self.active_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.request_responses: Dict[str, Any] = {}  # Cache responses briefly
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request (same logic as rate limiting)."""
        # Try to get user from authentication
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.id}"
        
        # Try to get from JWT token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token_hash = hashlib.md5(auth_header.encode()).hexdigest()
                return f"token_{token_hash}"
            except Exception:
                pass
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip_{client_ip}"
    
    async def _get_request_signature(self, request: Request) -> str:
        """Generate a signature for request deduplication."""
        # Include user, method, path, and body content for POST/PUT requests
        user_id = self._get_user_id(request)
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        
        # For requests with bodies, include body hash
        body_hash = ""
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # Store the body for later use without breaking ASGI
                body_bytes = await request.body()
                if body_bytes:
                    body_hash = hashlib.md5(body_bytes).hexdigest()
                    # Store body in request state for downstream use
                    request._body = body_bytes
            except Exception as e:
                logger.warning(f"Failed to read request body for deduplication: {e}")
        
        # Create signature
        signature_data = f"{user_id}:{method}:{path}:{query}:{body_hash}"
        return hashlib.sha256(signature_data.encode()).hexdigest()
    
    def _cleanup_old_requests(self, requests: deque) -> None:
        """Remove old request timestamps outside the deduplication window."""
        cutoff_time = time.time() - self.deduplication_window
        while requests and requests[0] < cutoff_time:
            requests.popleft()
    
    def _should_deduplicate(self, path: str, method: str) -> bool:
        """Check if this endpoint should be deduplicated."""
        # Focus on task operations and potentially expensive endpoints
        task_patterns = [
            "/api/v1/tasks",
            "/api/v1/smart-router",
            "/api/v1/chat",
            "/api/v1/documents"
        ]
        
        # Only deduplicate POST, PUT, PATCH requests (not GET requests)
        return method in ["POST", "PUT", "PATCH"] and any(path.startswith(pattern) for pattern in task_patterns)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Skip deduplication for endpoints that don't need it or WebSocket requests
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        is_websocket_upgrade = "upgrade" in connection_header and upgrade_header == "websocket"
        
        if not self._should_deduplicate(request.url.path, request.method) or is_websocket_upgrade:
            return await call_next(request)
        
        # Get request signature
        request_signature = await self._get_request_signature(request)
        current_time = time.time()
        
        # Check for concurrent identical requests
        active_requests = self.active_requests[request_signature]
        self._cleanup_old_requests(active_requests)
        
        if len(active_requests) >= self.max_concurrent_requests:
            logger.warning(f"Duplicate request blocked: {request.method} {request.url.path} (signature: {request_signature[:16]}...)")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "Duplicate request detected",
                    "message": f"Too many identical requests in progress. Please wait before retrying.",
                    "request_signature": request_signature[:16],
                    "retry_after": self.deduplication_window
                },
                headers={"Retry-After": str(self.deduplication_window)}
            )
        
        # Check if we have a cached response for this exact request
        cached_response = self.request_responses.get(request_signature)
        if cached_response and (current_time - cached_response['timestamp']) < self.deduplication_window:
            logger.info(f"Returning cached response for duplicate request: {request_signature[:16]}...")
            return JSONResponse(
                content=cached_response['content'],
                status_code=cached_response['status_code'],
                headers=cached_response.get('headers', {})
            )
        
        # Record this request as active
        active_requests.append(current_time)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Cache successful responses for a short time
            if response.status_code < 400:
                if hasattr(response, 'body') and response.body:
                    try:
                        # For JSON responses, cache the content
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            self.request_responses[request_signature] = {
                                'content': json.loads(response.body.decode('utf-8')),
                                'status_code': response.status_code,
                                'headers': dict(response.headers),
                                'timestamp': current_time
                            }
                    except Exception as e:
                        logger.debug(f"Failed to cache response: {e}")
            
            return response
        
        finally:
            # Remove this request from active list
            try:
                active_requests.remove(current_time)
            except ValueError:
                pass  # Request might have been cleaned up already


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Circuit breaker middleware to prevent cascade failures.
    Opens circuit when error rates exceed thresholds.
    """
    
    def __init__(
        self,
        app,
        failure_threshold: int = 5,           # Number of failures to open circuit
        success_threshold: int = 2,           # Number of successes to close circuit
        timeout: int = 60,                    # Timeout in seconds before trying again
        error_rate_threshold: float = 0.5,    # Error rate threshold (50%)
        window_size: int = 20                 # Window size for error rate calculation
    ):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.error_rate_threshold = error_rate_threshold
        self.window_size = window_size
        
        # Circuit breaker state per endpoint
        self.circuit_states: Dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_time: Dict[str, float] = defaultdict(float)
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.window_size))
    
    def _get_endpoint_key(self, request: Request) -> str:
        """Generate a key for circuit breaker state based on endpoint."""
        # Group similar endpoints together
        path = request.url.path
        method = request.method
        
        # Normalize task endpoints
        if "/api/v1/tasks/" in path:
            if path.endswith("/subtasks/generate"):
                return f"{method}:/api/v1/tasks/*/subtasks/generate"
            elif "/subtasks/" in path:
                return f"{method}:/api/v1/tasks/*/subtasks/*"
            elif path.count("/") == 4:  # /api/v1/tasks/{id}
                return f"{method}:/api/v1/tasks/*"
        
        # Normalize smart router endpoints
        if path.startswith("/api/v1/smart-router"):
            return f"{method}:/api/v1/smart-router/*"
        
        # For other endpoints, use exact path
        return f"{method}:{path}"
    
    def _record_request(self, endpoint_key: str, is_success: bool) -> None:
        """Record request outcome for circuit breaker logic."""
        current_time = time.time()
        
        # Add to history
        self.request_history[endpoint_key].append({
            'timestamp': current_time,
            'success': is_success
        })
        
        if is_success:
            self.success_counts[endpoint_key] += 1
            # Reset failure count on success in HALF_OPEN state
            if self.circuit_states[endpoint_key] == CircuitState.HALF_OPEN:
                if self.success_counts[endpoint_key] >= self.success_threshold:
                    self.circuit_states[endpoint_key] = CircuitState.CLOSED
                    self.failure_counts[endpoint_key] = 0
                    self.success_counts[endpoint_key] = 0
                    logger.info(f"Circuit breaker CLOSED for {endpoint_key}")
        else:
            self.failure_counts[endpoint_key] += 1
            self.last_failure_time[endpoint_key] = current_time
            
            # Check if we should open the circuit
            if self.circuit_states[endpoint_key] == CircuitState.CLOSED:
                # Check failure count threshold
                if self.failure_counts[endpoint_key] >= self.failure_threshold:
                    self.circuit_states[endpoint_key] = CircuitState.OPEN
                    logger.warning(f"Circuit breaker OPENED for {endpoint_key} (failure count: {self.failure_counts[endpoint_key]})")
                
                # Check error rate threshold
                elif len(self.request_history[endpoint_key]) >= 5:  # Minimum sample size
                    error_count = sum(1 for req in self.request_history[endpoint_key] if not req['success'])
                    error_rate = error_count / len(self.request_history[endpoint_key])
                    
                    if error_rate >= self.error_rate_threshold:
                        self.circuit_states[endpoint_key] = CircuitState.OPEN
                        logger.warning(f"Circuit breaker OPENED for {endpoint_key} (error rate: {error_rate:.2%})")
    
    def _should_allow_request(self, endpoint_key: str) -> Tuple[bool, str]:
        """Check if request should be allowed based on circuit state."""
        current_state = self.circuit_states[endpoint_key]
        current_time = time.time()
        
        if current_state == CircuitState.CLOSED:
            return True, ""
        
        elif current_state == CircuitState.OPEN:
            # Check if timeout has passed
            if current_time - self.last_failure_time[endpoint_key] >= self.timeout:
                self.circuit_states[endpoint_key] = CircuitState.HALF_OPEN
                self.success_counts[endpoint_key] = 0
                logger.info(f"Circuit breaker HALF_OPEN for {endpoint_key}")
                return True, ""
            else:
                remaining_time = self.timeout - (current_time - self.last_failure_time[endpoint_key])
                return False, f"Circuit breaker OPEN. Try again in {remaining_time:.0f} seconds."
        
        elif current_state == CircuitState.HALF_OPEN:
            # Allow limited requests to test if service recovered
            return True, ""
        
        return True, ""
    
    def _is_request_failure(self, response: StarletteResponse) -> bool:
        """Determine if response indicates a failure."""
        # Consider 5xx errors and timeouts as failures
        # 4xx errors are client errors, not service failures
        return response.status_code >= 500
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Skip circuit breaker for health checks, auth, and WebSocket connections
        exempt_paths = [
            "/health", "/api/v1/health", "/api/v1/auth", "/api/auth",
            "/ws/", "/api/v1/ws/", "/api/ws/"
        ]
        
        # Also skip WebSocket upgrade requests
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        is_websocket_upgrade = "upgrade" in connection_header and upgrade_header == "websocket"
        
        if any(request.url.path.startswith(path) for path in exempt_paths) or is_websocket_upgrade:
            return await call_next(request)
        
        endpoint_key = self._get_endpoint_key(request)
        
        # Check if request should be allowed
        should_allow, reason = self._should_allow_request(endpoint_key)
        
        if not should_allow:
            logger.warning(f"Circuit breaker blocked request to {endpoint_key}: {reason}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Service temporarily unavailable",
                    "message": reason,
                    "endpoint": endpoint_key,
                    "circuit_state": self.circuit_states[endpoint_key].value
                },
                headers={"Retry-After": str(self.timeout)}
            )
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Record success/failure
            is_failure = self._is_request_failure(response)
            self._record_request(endpoint_key, not is_failure)
            
            return response
        
        except Exception as e:
            # Record failure for unhandled exceptions
            logger.error(f"Unhandled exception in {endpoint_key}: {e}")
            self._record_request(endpoint_key, False)
            
            # Return a proper error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred"
                }
            )