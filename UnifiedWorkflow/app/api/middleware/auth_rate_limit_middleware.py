"""
Enhanced Authentication Rate Limiting Middleware

This middleware provides specialized rate limiting for authentication endpoints
with different limits for session validation vs general API calls to prevent
frontend infinite loops and reduce server load.
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Specialized rate limiting middleware for authentication endpoints.
    Provides different rate limits for session validation vs other auth operations
    to prevent infinite loops and reduce database load.
    """
    
    def __init__(
        self, 
        app,
        # Session validation - very permissive to prevent frontend infinite loops
        session_validate_calls: int = 100,     # 100 session validations per minute
        session_validate_period: int = 60,     # 1 minute window
        
        # General auth operations - more restrictive
        auth_calls: int = 30,                  # 30 auth operations per minute
        auth_period: int = 60,                 # 1 minute window
        
        # Login attempts - most restrictive
        login_calls: int = 10,                 # 10 login attempts per 10 minutes
        login_period: int = 600,               # 10 minute window
        
        # Token refresh - moderate restrictions
        token_refresh_calls: int = 20,         # 20 refresh attempts per 5 minutes
        token_refresh_period: int = 300        # 5 minute window
    ):
        super().__init__(app)
        self.session_validate_calls = session_validate_calls
        self.session_validate_period = session_validate_period
        self.auth_calls = auth_calls
        self.auth_period = auth_period
        self.login_calls = login_calls
        self.login_period = login_period
        self.token_refresh_calls = token_refresh_calls
        self.token_refresh_period = token_refresh_period
        
        # Storage for rate limiting data per user
        self.user_session_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_auth_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_login_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_token_refresh_requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from authenticated request or fall back to IP."""
        # Try to get user from authentication state
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.id}"
        
        # Try to extract from JWT token header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token_hash = hashlib.md5(auth_header.encode()).hexdigest()
                return f"token_{token_hash[:16]}"
            except Exception:
                pass
        
        # Fall back to IP address with X-Forwarded-For support
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
    
    def _get_endpoint_type(self, path: str, method: str) -> str:
        """Determine the type of authentication endpoint."""
        # Session validation endpoints - most permissive
        if path.endswith("/validate") or path.endswith("/session/validate"):
            return "session_validate"
        
        # Login endpoints - most restrictive
        if (path.endswith("/login") or path.endswith("/login-form") or 
            "login" in path or path.endswith("/register")):
            return "login"
        
        # Token refresh endpoints
        if (path.endswith("/refresh") or path.endswith("/token") or 
            "refresh" in path):
            return "token_refresh"
        
        # General auth endpoints
        if "/auth/" in path or "/api/v1/auth/" in path or "/api/auth/" in path:
            return "auth"
        
        # Default to general auth for any auth-related endpoint
        return "auth"
    
    def _check_rate_limits(self, user_id: str, path: str, method: str) -> Tuple[bool, str, Dict[str, str]]:
        """
        Check applicable rate limits for the authentication request.
        Returns (is_limited, reason, retry_headers).
        """
        current_time = time.time()
        endpoint_type = self._get_endpoint_type(path, method)
        
        if endpoint_type == "session_validate":
            # Check session validation rate limit (most permissive)
            session_requests = self.user_session_requests[user_id]
            self._cleanup_old_requests(session_requests, self.session_validate_period)
            
            if len(session_requests) >= self.session_validate_calls:
                remaining_time = self.session_validate_period - (current_time - session_requests[0])
                return True, f"Session validation rate limit exceeded: {self.session_validate_calls} per minute", {
                    "X-RateLimit-Limit-Session": str(self.session_validate_calls),
                    "X-RateLimit-Remaining-Session": "0",
                    "X-RateLimit-Reset-Session": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            session_requests.append(current_time)
            
            # Return success headers
            remaining = max(0, self.session_validate_calls - len(session_requests))
            return False, "", {
                "X-RateLimit-Limit-Session": str(self.session_validate_calls),
                "X-RateLimit-Remaining-Session": str(remaining),
                "X-RateLimit-Reset-Session": str(int(current_time + self.session_validate_period))
            }
        
        elif endpoint_type == "login":
            # Check login rate limit (most restrictive)
            login_requests = self.user_login_requests[user_id]
            self._cleanup_old_requests(login_requests, self.login_period)
            
            if len(login_requests) >= self.login_calls:
                remaining_time = self.login_period - (current_time - login_requests[0])
                return True, f"Login rate limit exceeded: {self.login_calls} per {self.login_period//60} minutes", {
                    "X-RateLimit-Limit-Login": str(self.login_calls),
                    "X-RateLimit-Remaining-Login": "0",
                    "X-RateLimit-Reset-Login": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            login_requests.append(current_time)
            
            remaining = max(0, self.login_calls - len(login_requests))
            return False, "", {
                "X-RateLimit-Limit-Login": str(self.login_calls),
                "X-RateLimit-Remaining-Login": str(remaining),
                "X-RateLimit-Reset-Login": str(int(current_time + self.login_period))
            }
        
        elif endpoint_type == "token_refresh":
            # Check token refresh rate limit
            refresh_requests = self.user_token_refresh_requests[user_id]
            self._cleanup_old_requests(refresh_requests, self.token_refresh_period)
            
            if len(refresh_requests) >= self.token_refresh_calls:
                remaining_time = self.token_refresh_period - (current_time - refresh_requests[0])
                return True, f"Token refresh rate limit exceeded: {self.token_refresh_calls} per {self.token_refresh_period//60} minutes", {
                    "X-RateLimit-Limit-Refresh": str(self.token_refresh_calls),
                    "X-RateLimit-Remaining-Refresh": "0",
                    "X-RateLimit-Reset-Refresh": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            refresh_requests.append(current_time)
            
            remaining = max(0, self.token_refresh_calls - len(refresh_requests))
            return False, "", {
                "X-RateLimit-Limit-Refresh": str(self.token_refresh_calls),
                "X-RateLimit-Remaining-Refresh": str(remaining),
                "X-RateLimit-Reset-Refresh": str(int(current_time + self.token_refresh_period))
            }
        
        else:
            # Check general auth rate limit
            auth_requests = self.user_auth_requests[user_id]
            self._cleanup_old_requests(auth_requests, self.auth_period)
            
            if len(auth_requests) >= self.auth_calls:
                remaining_time = self.auth_period - (current_time - auth_requests[0])
                return True, f"Auth rate limit exceeded: {self.auth_calls} per minute", {
                    "X-RateLimit-Limit-Auth": str(self.auth_calls),
                    "X-RateLimit-Remaining-Auth": "0",
                    "X-RateLimit-Reset-Auth": str(int(current_time + remaining_time)),
                    "Retry-After": str(int(remaining_time))
                }
            
            auth_requests.append(current_time)
            
            remaining = max(0, self.auth_calls - len(auth_requests))
            return False, "", {
                "X-RateLimit-Limit-Auth": str(self.auth_calls),
                "X-RateLimit-Remaining-Auth": str(remaining),
                "X-RateLimit-Reset-Auth": str(int(current_time + self.auth_period))
            }
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Only apply to authentication endpoints
        auth_patterns = [
            "/api/v1/auth/", "/api/auth/", "/auth/",
            "/api/v1/session/validate"
        ]
        
        # Skip non-auth endpoints and WebSocket connections
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        is_websocket_upgrade = "upgrade" in connection_header and upgrade_header == "websocket"
        
        is_auth_endpoint = any(request.url.path.startswith(pattern) for pattern in auth_patterns)
        
        if not is_auth_endpoint or is_websocket_upgrade:
            return await call_next(request)
        
        user_id = self._get_user_id(request)
        is_limited, reason, headers = self._check_rate_limits(
            user_id, request.url.path, request.method
        )
        
        if is_limited:
            logger.warning(f"Auth rate limit exceeded for user {user_id}: {reason} on {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Authentication rate limit exceeded",
                    "message": reason,
                    "user_id": user_id,
                    "path": request.url.path,
                    "endpoint_type": self._get_endpoint_type(request.url.path, request.method),
                    "timestamp": datetime.now().isoformat()
                },
                headers=headers
            )
        
        # Process the request and add rate limit headers
        response = await call_next(request)
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response