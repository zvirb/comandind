"""
Authentication Monitoring Middleware
Integrates authentication monitoring with existing auth flow for comprehensive tracking.
"""

import logging
import time
import asyncio
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
# # from shared.services.auth_monitoring_service import auth_monitoring_service, AuthenticationEvent

logger = logging.getLogger(__name__)

class AuthMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor authentication events and performance.
    Integrates with existing authentication flow without disrupting it.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Track authentication endpoints for monitoring
        self.auth_endpoints = {
            '/api/v1/auth/login',
            '/api/v1/auth/logout',
            '/api/v1/auth/refresh',
            '/api/auth/login',
            '/api/auth/logout',
            '/api/auth/refresh',
            '/oauth/callback'
        }
        
        # Protected endpoints that require authentication
        self.protected_prefixes = {
            '/api/v1/',
            '/api/dashboard',
            '/api/chat',
            '/api/conversation',
            '/api/user',
            '/api/admin'
        }
    
    def _extract_client_info(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """Extract client IP and user agent from request."""
        try:
            # Get client IP (handle proxy headers)
            client_ip = (
                request.headers.get('x-forwarded-for', '').split(',')[0].strip() or
                request.headers.get('x-real-ip') or
                getattr(request.client, 'host', None)
            )
            
            user_agent = request.headers.get('user-agent', 'unknown')
            
            return client_ip, user_agent
            
        except Exception as e:
            logger.debug(f"Failed to extract client info: {e}")
            return None, None
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an authentication endpoint."""
        return path in self.auth_endpoints
    
    def _is_protected_endpoint(self, path: str) -> bool:
        """Check if path requires authentication."""
        return any(path.startswith(prefix) for prefix in self.protected_prefixes)
    
    def _determine_auth_method(self, request: Request) -> str:
        """Determine authentication method used."""
        if request.headers.get('authorization', '').startswith('Bearer '):
            return 'bearer_token'
        elif request.cookies.get('access_token') or request.cookies.get('auth_token'):
            return 'cookie'
        elif 'websocket' in request.headers.get('upgrade', '').lower():
            return 'websocket'
        else:
            return 'unknown'
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Monitor authentication events and performance."""
        
        start_time = time.perf_counter()
        path = request.url.path
        method = request.method
        
        # Skip monitoring for non-auth related endpoints
        if not (self._is_auth_endpoint(path) or self._is_protected_endpoint(path)):
            return await call_next(request)
        
        client_ip, user_agent = self._extract_client_info(request)
        auth_method = self._determine_auth_method(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Determine if this was an authentication attempt
        is_auth_attempt = (
            self._is_auth_endpoint(path) or 
            (self._is_protected_endpoint(path) and response.status_code in [401, 403])
        )
        
        if is_auth_attempt:
            # Create authentication event
            user_id = None
            user_email = None
            error_message = None
            
            # Extract user info from request state if available
            if hasattr(request.state, 'authenticated_user_id'):
                user_id = request.state.authenticated_user_id
                user_email = request.state.authenticated_user_email
            
            # Determine event type and success
            if response.status_code == 200:
                if path.endswith('/login'):
                    event_type = 'login_success'
                elif path.endswith('/refresh'):
                    event_type = 'token_refresh'
                else:
                    event_type = 'token_validation'
            else:
                if path.endswith('/login'):
                    event_type = 'login_failure'
                else:
                    event_type = 'token_validation'
                
                # Determine error message based on status code
                if response.status_code == 401:
                    error_message = 'unauthorized'
                elif response.status_code == 403:
                    error_message = 'forbidden'
                elif response.status_code >= 500:
                    error_message = 'server_error'
                else:
                    error_message = f'http_{response.status_code}'
            
            # Record authentication event
            auth_event = AuthenticationEvent(
                user_id=user_id,
                user_email=user_email,
                event_type=event_type,
                authentication_method=auth_method,
                client_ip=client_ip,
                user_agent=user_agent,
                timestamp=time.time(),
                response_time_ms=response_time_ms,
                error_message=error_message,
                session_id=getattr(request.state, 'session_id', None)
            )
            
            # Record the event asynchronously to not block response
            asyncio.create_task(self._record_auth_event(auth_event))
        
        # Monitor JWT operations if this involves token handling
        if hasattr(request.state, 'jwt_operation_recorded'):
            jwt_op_data = request.state.jwt_operation_recorded
            asyncio.create_task(self._record_jwt_operation(jwt_op_data))
        
        # Add response time header for debugging
        response.headers['X-Auth-Response-Time'] = f"{response_time_ms:.2f}ms"
        
        return response
    
    async def _record_auth_event(self, event: AuthenticationEvent) -> None:
        """Record authentication event asynchronously."""
        try:
            auth_monitoring_service.record_auth_attempt(event)
            
            # Update performance targets
            auth_monitoring_service.check_performance_targets(event.response_time_ms)
            
            logger.debug(f"Recorded auth event: {event.event_type} in {event.response_time_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Failed to record authentication event: {e}")
    
    async def _record_jwt_operation(self, jwt_data: dict) -> None:
        """Record JWT operation asynchronously."""
        try:
            auth_monitoring_service.record_jwt_operation(
                operation_type=jwt_data.get('operation'),
                result=jwt_data.get('result'),
                validation_time_ms=jwt_data.get('validation_time_ms')
            )
            
        except Exception as e:
            logger.error(f"Failed to record JWT operation: {e}")


class CacheMonitoringMixin:
    """
    Mixin to add cache monitoring to existing authentication middleware.
    """
    
    def record_cache_hit(self, cache_type: str) -> None:
        """Record authentication cache hit."""
        try:
            auth_monitoring_service.record_cache_operation(cache_type, hit=True)
        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}")
    
    def record_cache_miss(self, cache_type: str) -> None:
        """Record authentication cache miss.""" 
        try:
            auth_monitoring_service.record_cache_operation(cache_type, hit=False)
        except Exception as e:
            logger.error(f"Failed to record cache miss: {e}")


class WebSocketAuthMonitoringMixin:
    """
    Mixin to add WebSocket authentication monitoring.
    """
    
    def record_websocket_auth(self, success: bool, response_time_ms: float = 0.0) -> None:
        """Record WebSocket authentication attempt."""
        try:
            auth_monitoring_service.record_websocket_auth(success)
            
            if response_time_ms > 0:
                auth_monitoring_service.check_performance_targets(response_time_ms)
                
        except Exception as e:
            logger.error(f"Failed to record WebSocket auth: {e}")