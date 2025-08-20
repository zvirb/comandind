"""
Authentication Middleware

Provides JWT token validation middleware for protected endpoints
to prevent authentication cascade failures and 401/403 loops.
"""

import logging
import time
from typing import Optional, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import jwt
from jwt import InvalidTokenError as JWTError

from api.auth import ALGORITHM, SECRET_KEY
from shared.schemas import TokenData
from shared.database.models import UserRole

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication middleware that validates tokens for protected endpoints.
    
    This middleware handles token validation before FastAPI dependency injection,
    preventing authentication cascade failures and infinite loops.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Endpoints that require authentication
        self.protected_paths: Set[str] = {
            "/api/v1/chat",
            "/api/v1/conversation", 
            "/api/v1/tasks",
            "/api/v1/documents",
            "/api/v1/user",
            "/api/v1/dashboard",
            "/api/v1/settings",
            "/api/v1/admin",
            "/api/v1/profile",
            "/api/v1/calendar",
            "/api/v1/drive",
            "/api/v1/categories",
            "/api/v1/mission-suggestions",
            "/api/v1/user-history",
            "/api/v1/smart-router",
            "/api/v1/hybrid-intelligence",
            "/api/v1/system-prompts",
            "/api/v1/focus-nudge",
            "/api/v1/2fa",
            "/api/v1/protocol",
            "/native"
        }
        
        # Endpoints that are always exempt from authentication
        self.exempt_paths: Set[str] = {
            "/health",
            "/api/v1/health",
            "/api/health",
            "/",
            "/api/v1/auth",
            "/api/auth",
            "/api/v1/oauth",
            "/oauth",
            "/public",
            "/api/v1/public",
            "/ws",  # WebSocket endpoints handle their own auth
        }
    
    def _is_protected_endpoint(self, path: str) -> bool:
        """Check if the endpoint requires authentication."""
        # First check if explicitly exempt
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return False
            
        # Check if it's a protected path
        return any(path.startswith(protected) for protected in self.protected_paths)
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers or cookies."""
        # Try Authorization header first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Fallback to cookie
        return request.cookies.get("access_token")
    
    def _validate_token(self, token: str) -> Optional[TokenData]:
        """Validate JWT token and return token data."""
        try:
            # Decode JWT with error handling
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                options={
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": False,  # Skip audience verification for compatibility
                },
                leeway=60  # Allow 60 seconds clock skew
            )
            
            # Extract user information from token payload
            email: Optional[str] = None
            user_id: Optional[int] = None
            role: Optional[str] = None
            
            # Enhanced format (sub=user_id, email=email, role=role)
            if "email" in payload and "sub" in payload:
                try:
                    user_id = int(payload.get("sub"))
                    email = payload.get("email")
                    role = payload.get("role")
                except (ValueError, TypeError):
                    # Sub might be email (legacy format)
                    pass
            
            # Legacy format fallback (sub=email, id=user_id, role=role)
            if not user_id or not email:
                sub_value = payload.get("sub")
                if sub_value and "@" in str(sub_value):  # Looks like an email
                    email = sub_value
                    user_id = payload.get("id")
                    role = payload.get("role")
                elif sub_value:
                    # Try parsing sub as user_id one more time
                    try:
                        user_id = int(sub_value)
                        email = payload.get("email") or payload.get("sub")
                        role = payload.get("role")
                    except (ValueError, TypeError):
                        pass
            
            # Final validation
            if not email or not role or not user_id:
                logger.error(
                    f"Incomplete token data: email={email}, user_id={user_id}, role={role}. "
                    f"Payload keys: {list(payload.keys())}"
                )
                return None
            
            # Create TokenData with validated information
            try:
                return TokenData(id=user_id, email=email, role=UserRole(role))
            except ValueError:
                logger.error(f"Invalid role value '{role}' in token")
                return None
                
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.debug("Invalid token format")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None
    
    def _create_auth_error_response(self, request_id: str, message: str = "Authentication required") -> JSONResponse:
        """Create a standardized authentication error response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication failed",
                "message": message,
                "request_id": request_id
            },
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Request-ID": request_id
            }
        )
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Process request and validate authentication for protected endpoints."""
        
        request_id = getattr(request.state, 'request_id', f"auth_{int(time.time())}")
        path = request.url.path
        
        # Skip authentication for non-protected endpoints
        if not self._is_protected_endpoint(path):
            return await call_next(request)
        
        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            logger.debug(f"No token found for protected endpoint: {path}")
            return self._create_auth_error_response(request_id, "No authentication token provided")
        
        # Validate token
        token_data = self._validate_token(token)
        if not token_data:
            logger.debug(f"Invalid token for protected endpoint: {path}")
            return self._create_auth_error_response(request_id, "Invalid authentication token")
        
        # Store validated token data in request state for dependency injection
        request.state.authenticated_user_id = token_data.id
        request.state.authenticated_user_email = token_data.email
        request.state.authenticated_user_role = token_data.role
        request.state.token_validated = True
        
        logger.debug(f"Authentication successful for user {token_data.id} on {path}")
        
        # Continue to next middleware/endpoint
        return await call_next(request)


class AuthenticationTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent authentication hanging by applying timeouts
    specifically to authentication-related operations.
    """
    
    def __init__(self, app, auth_timeout: float = 10.0):
        super().__init__(app)
        self.auth_timeout = auth_timeout
    
    def _is_auth_operation(self, path: str) -> bool:
        """Check if this is an authentication operation that needs timeout protection."""
        auth_patterns = [
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh", 
            "/api/v1/auth/token",
            "/api/v1/oauth/",
            "/api/auth/jwt/login",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/token"
        ]
        return any(pattern in path for pattern in auth_patterns)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Apply timeout protection to authentication operations."""
        
        if not self._is_auth_operation(request.url.path):
            return await call_next(request)
        
        try:
            # Apply timeout to authentication operations
            import asyncio
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.auth_timeout
            )
            return response
            
        except asyncio.TimeoutError:
            request_id = getattr(request.state, 'request_id', f"timeout_{int(time.time())}")
            
            logger.error(
                f"Authentication timeout: {request.method} {request.url.path} after {self.auth_timeout}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "timeout_seconds": self.auth_timeout
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                content={
                    "error": "Authentication timeout",
                    "message": f"Authentication operation timed out after {self.auth_timeout} seconds",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )