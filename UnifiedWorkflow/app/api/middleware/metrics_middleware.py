"""
FastAPI middleware for automatic Prometheus metrics collection.

This middleware automatically instruments all HTTP requests with comprehensive
metrics including request/response times, status codes, payload sizes, and
custom business metrics.
"""

import time
import logging
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio

# Import metrics with error handling
try:
    from shared.monitoring.prometheus_metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    metrics = None
import json
import re
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that automatically collects Prometheus metrics for all requests.
    
    Features:
    - Request/response time measurement
    - HTTP status code tracking
    - Request/response size measurement
    - Endpoint normalization (removes dynamic path parameters)
    - User type detection from JWT tokens
    - Rate limiting detection
    - Business metric extraction
    """
    
    def __init__(
        self,
        app: ASGIApp,
        skip_paths: Optional[list] = None,
        normalize_paths: bool = True,
        track_user_metrics: bool = True,
        track_business_metrics: bool = True
    ):
        super().__init__(app)
        
        # Paths to skip from metrics collection (e.g., health checks)
        self.skip_paths = skip_paths or ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
        
        # Configuration options
        self.normalize_paths = normalize_paths
        self.track_user_metrics = track_user_metrics
        self.track_business_metrics = track_business_metrics
        
        # Regex patterns for path normalization
        self.path_patterns = [
            (re.compile(r'/api/v\d+/users/[^/]+'), '/api/v{version}/users/{user_id}'),
            (re.compile(r'/api/v\d+/tasks/[^/]+'), '/api/v{version}/tasks/{task_id}'),
            (re.compile(r'/api/v\d+/workflows/[^/]+'), '/api/v{version}/workflows/{workflow_id}'),
            (re.compile(r'/api/v\d+/models/[^/]+'), '/api/v{version}/models/{model_id}'),
            (re.compile(r'/\d+'), '/{id}'),  # Generic ID replacement
            (re.compile(r'/[a-fA-F0-9-]{36}'), '/{uuid}'),  # UUID replacement
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        
        # Skip metrics collection for certain paths
        if self._should_skip_path(request.url.path):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        request_size = await self._get_request_size(request)
        
        # Increment active requests counter if metrics are available
        if METRICS_AVAILABLE and metrics:
            metrics.active_requests.inc()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate timing
            process_time = time.time() - start_time
            response_size = self._get_response_size(response)
            
            # Extract request information
            method = request.method
            endpoint = self._normalize_endpoint(request.url.path)
            status_code = response.status_code
            
            # Record basic HTTP metrics if available
            if METRICS_AVAILABLE and metrics:
                metrics.record_request_metrics(
                    method=method,
                    endpoint=endpoint,
                    status=status_code,
                    duration=process_time,
                    request_size=request_size,
                    response_size=response_size
                )
            
            # Track user-specific metrics
            if self.track_user_metrics:
                await self._track_user_metrics(request, response)
            
            # Track business metrics
            if self.track_business_metrics:
                await self._track_business_metrics(request, response)
            
            # Add timing header for observability
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculate timing for failed requests
            process_time = time.time() - start_time
            
            # Extract request information
            method = request.method
            endpoint = self._normalize_endpoint(request.url.path)
            
            # Record metrics for failed requests if available
            if METRICS_AVAILABLE and metrics:
                metrics.record_request_metrics(
                    method=method,
                    endpoint=endpoint,
                    status=500,
                    duration=process_time,
                    request_size=request_size
                )
            
            logger.error(f"Request failed: {method} {endpoint} - {str(e)}")
            raise
            
        finally:
            # Always decrement active requests counter if available
            if METRICS_AVAILABLE and metrics:
                metrics.active_requests.dec()
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if path should be skipped from metrics collection."""
        return any(skip_path in path for skip_path in self.skip_paths)
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path to reduce cardinality."""
        if not self.normalize_paths:
            return path
        
        normalized_path = path
        
        # Apply normalization patterns
        for pattern, replacement in self.path_patterns:
            normalized_path = pattern.sub(replacement, normalized_path)
        
        return normalized_path
    
    async def _get_request_size(self, request: Request) -> int:
        """Get request body size in bytes."""
        try:
            if hasattr(request, '_body'):
                return len(request._body)
            
            # For streaming requests, we can't easily get the size
            content_length = request.headers.get('content-length')
            if content_length:
                return int(content_length)
                
            return 0
        except Exception:
            return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Get response body size in bytes."""
        try:
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
                
            # Estimate size if content-length is not available
            if hasattr(response, 'body'):
                if isinstance(response.body, bytes):
                    return len(response.body)
                elif isinstance(response.body, str):
                    return len(response.body.encode('utf-8'))
            
            return 0
        except Exception:
            return 0
    
    async def _track_user_metrics(self, request: Request, response: Response):
        """Track user-specific metrics."""
        try:
            # Extract user information from JWT token or session
            user_info = await self._get_user_info(request)
            if user_info:
                user_type = user_info.get('type', 'authenticated')
                endpoint = self._normalize_endpoint(request.url.path)
                
                # Record user request
                from shared.monitoring.prometheus_metrics import record_user_request
                record_user_request(user_type, endpoint)
                
                # Check for rate limiting
                if response.status_code == 429:
                    user_id = user_info.get('id', 'unknown')
                    from shared.monitoring.prometheus_metrics import record_rate_limit_hit
                    record_rate_limit_hit(user_id, endpoint)
        
        except Exception as e:
            logger.warning(f"Failed to track user metrics: {str(e)}")
    
    async def _track_business_metrics(self, request: Request, response: Response):
        """Track business-specific metrics."""
        try:
            path = request.url.path
            method = request.method
            
            # Track authentication events
            if '/auth/' in path:
                await self._track_auth_metrics(request, response)
            
            # Track AI task metrics
            if '/ai/' in path or '/tasks/' in path:
                await self._track_ai_metrics(request, response)
            
            # Track data processing metrics
            if '/data/' in path or method in ['POST', 'PUT', 'PATCH']:
                await self._track_data_metrics(request, response)
            
            # Track user registration
            if path.endswith('/register') and method == 'POST' and response.status_code == 201:
                from shared.monitoring.prometheus_metrics import record_user_registration
                record_user_registration(source='web')
        
        except Exception as e:
            logger.warning(f"Failed to track business metrics: {str(e)}")
    
    async def _track_auth_metrics(self, request: Request, response: Response):
        """Track authentication-specific metrics."""
        try:
            path = request.url.path
            method = request.method
            status_code = response.status_code
            
            if '/login' in path and method == 'POST':
                if status_code == 200:
                    if METRICS_AVAILABLE and metrics:
                        metrics.record_auth_attempt('password', 'success')
                else:
                    # Try to get failure reason from response
                    reason = 'unknown'
                    if status_code == 401:
                        reason = 'invalid_credentials'
                    elif status_code == 423:
                        reason = 'account_locked'
                    elif status_code == 429:
                        reason = 'rate_limited'
                    
                    user_agent = request.headers.get('user-agent', 'unknown')[:50]
                    client_ip = self._get_client_ip(request)
                    ip_range = self._get_ip_range(client_ip)
                    
                    if METRICS_AVAILABLE and metrics:
                        metrics.record_auth_attempt(
                            'password', 'failure',
                            reason=reason,
                            user_agent=user_agent,
                            ip_range=ip_range
                        )
            
            elif '/oauth' in path:
                oauth_provider = self._extract_oauth_provider(path)
                status = 'success' if status_code == 200 else 'failure'
                if METRICS_AVAILABLE and metrics:
                    metrics.record_auth_attempt(f'oauth_{oauth_provider}', status)
            
            elif '/2fa' in path or '/mfa' in path:
                status = 'success' if status_code == 200 else 'failure'
                if METRICS_AVAILABLE and metrics:
                    metrics.record_auth_attempt('mfa', status)
        
        except Exception as e:
            logger.warning(f"Failed to track auth metrics: {str(e)}")
    
    async def _track_ai_metrics(self, request: Request, response: Response):
        """Track AI task-specific metrics."""
        try:
            # This would be expanded based on your AI task endpoints
            if response.status_code in [200, 201, 202]:
                # Extract task info from request/response if available
                task_type = self._extract_task_type(request.url.path)
                model = request.headers.get('X-Model-Name', 'default')
                
                # Record successful task initiation
                if METRICS_AVAILABLE and metrics:
                    metrics.ai_tasks_total.labels(
                        task_type=task_type,
                        model=model,
                        status='initiated'
                    ).inc()
        
        except Exception as e:
            logger.warning(f"Failed to track AI metrics: {str(e)}")
    
    async def _track_data_metrics(self, request: Request, response: Response):
        """Track data processing metrics."""
        try:
            # Track data operations
            if request.method in ['POST', 'PUT', 'PATCH']:
                operation_type = self._extract_operation_type(request.url.path, request.method)
                data_type = self._extract_data_type(request)
                
                if response.status_code in [200, 201]:
                    if METRICS_AVAILABLE and metrics:
                        metrics.data_validation_attempts_total.labels(
                            data_type=data_type,
                            validation_type='input'
                        ).inc()
                else:
                    if METRICS_AVAILABLE and metrics:
                        metrics.data_validation_failures_total.labels(
                            data_type=data_type,
                            validation_type='input',
                            error_type='validation_error'
                        ).inc()
        
        except Exception as e:
            logger.warning(f"Failed to track data metrics: {str(e)}")
    
    async def _get_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user information from request."""
        try:
            # Try to get user from FastAPI dependency injection
            if hasattr(request.state, 'user'):
                return {
                    'id': getattr(request.state.user, 'id', 'unknown'),
                    'type': getattr(request.state.user, 'type', 'authenticated')
                }
            
            # Try to extract from Authorization header
            auth_header = request.headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # This would require JWT parsing logic
                return {'id': 'jwt_user', 'type': 'authenticated'}
            
            return None
        
        except Exception:
            return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers first
        forwarded = request.headers.get('x-forwarded-for')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _get_ip_range(self, ip: str) -> str:
        """Get IP range classification for metrics."""
        if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
            return 'private'
        elif ip.startswith('127.'):
            return 'localhost'
        else:
            return 'public'
    
    def _extract_oauth_provider(self, path: str) -> str:
        """Extract OAuth provider from path."""
        if 'google' in path.lower():
            return 'google'
        elif 'github' in path.lower():
            return 'github'
        elif 'microsoft' in path.lower():
            return 'microsoft'
        else:
            return 'unknown'
    
    def _extract_task_type(self, path: str) -> str:
        """Extract task type from path."""
        if '/generate' in path:
            return 'generation'
        elif '/analyze' in path:
            return 'analysis'
        elif '/process' in path:
            return 'processing'
        else:
            return 'unknown'
    
    def _extract_operation_type(self, path: str, method: str) -> str:
        """Extract operation type from path and method."""
        if method == 'POST':
            return 'create'
        elif method == 'PUT':
            return 'update'
        elif method == 'PATCH':
            return 'partial_update'
        else:
            return method.lower()
    
    def _extract_data_type(self, request: Request) -> str:
        """Extract data type from request."""
        content_type = request.headers.get('content-type', '').lower()
        
        if 'json' in content_type:
            return 'json'
        elif 'form' in content_type:
            return 'form'
        elif 'multipart' in content_type:
            return 'multipart'
        else:
            return 'unknown'