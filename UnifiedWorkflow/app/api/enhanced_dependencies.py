"""Enhanced FastAPI dependencies with mTLS and Enhanced JWT Authentication."""

import logging
from typing import List, Optional, Annotated, Callable
import os

from fastapi import Depends, HTTPException, Request, status, Query, WebSocket, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError as JWTError
from sqlalchemy.orm import Session
import redis.asyncio as redis

from shared.schemas import TokenData
from shared.database.models import User, UserRole, UserStatus
from shared.utils.database_setup import get_db
from shared.utils.config import get_settings
from shared.services.enhanced_jwt_service import (
    EnhancedJWTService, EnhancedTokenData, TokenAudience, TokenType, ServiceScope,
    require_scopes, require_audience
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Global enhanced JWT service instance
_enhanced_jwt_service: Optional[EnhancedJWTService] = None

# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)

# =============================================================================
# Enhanced JWT Service Initialization
# =============================================================================

async def get_enhanced_jwt_service() -> EnhancedJWTService:
    """Get or create the enhanced JWT service instance."""
    global _enhanced_jwt_service
    
    if _enhanced_jwt_service is None:
        # Initialize Redis connection for JWT service
        redis_client = None
        try:
            redis_client = redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            await redis_client.ping()
            logger.info("Enhanced JWT service connected to Redis")
        except Exception as e:
            logger.warning(f"Enhanced JWT service failed to connect to Redis: {e}")
            redis_client = None
        
        _enhanced_jwt_service = EnhancedJWTService(redis_client)
        logger.info("Enhanced JWT service initialized")
    
    return _enhanced_jwt_service

# =============================================================================
# mTLS Client Certificate Validation
# =============================================================================

def validate_client_certificate(request: Request) -> Optional[dict]:
    """Validate mTLS client certificate if present."""
    # Check if mTLS is enabled
    if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
        return None
    
    # Extract client certificate information from headers set by reverse proxy
    cert_subject = request.headers.get("X-Client-Certificate-Subject")
    cert_fingerprint = request.headers.get("X-Client-Certificate-Fingerprint")
    cert_verified = request.headers.get("X-Client-Certificate-Verified")
    
    if not cert_subject or cert_verified != "success":
        logger.warning("Invalid or missing client certificate")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid client certificate required"
        )
    
    return {
        "subject": cert_subject,
        "fingerprint": cert_fingerprint,
        "verified": True
    }

# =============================================================================
# Enhanced Token Validation
# =============================================================================

async def get_enhanced_token_payload(
    request: Request,
    audience: TokenAudience = TokenAudience.API_SERVICE,
    required_scopes: Optional[List[ServiceScope]] = None
) -> EnhancedTokenData:
    """Extract and validate enhanced JWT token from request."""
    jwt_service = await get_enhanced_jwt_service()
    
    # Extract token from Authorization header or cookie
    token = None
    
    # Try Authorization header first
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            scheme, _, param = auth_header.partition(' ')
            if scheme and scheme.lower() == 'bearer' and param:
                token = param
        except Exception as e:
            logger.warning(f"Failed to parse authorization header: {e}")
    
    # Fallback to cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        logger.error("No authentication token found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Validate token with enhanced JWT service
    try:
        token_data = jwt_service.validate_token(
            token=token,
            expected_audience=audience,
            required_scopes=required_scopes
        )
        
        # Log authentication success
        logger.info(f"Enhanced JWT validation successful for user: {token_data.email}")
        
        return token_data
        
    except HTTPException:
        raise  # Re-raise FastAPI HTTP exceptions
    except Exception as e:
        logger.error(f"Enhanced JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

# =============================================================================
# Enhanced User Dependencies
# =============================================================================

async def get_current_user_enhanced(
    request: Request,
    audience: TokenAudience = TokenAudience.API_SERVICE,
    required_scopes: Optional[List[ServiceScope]] = None,
    db: Session = Depends(get_db)
) -> User:
    """Get current user with enhanced JWT and optional mTLS validation."""
    
    # Validate client certificate if mTLS is enabled
    cert_info = validate_client_certificate(request)
    
    # Validate JWT token
    token_data = await get_enhanced_token_payload(
        request=request,
        audience=audience,
        required_scopes=required_scopes
    )
    
    # Look up user in database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        logger.error(f"User not found: {token_data.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check user status
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    # Add certificate info to user object for logging/auditing
    if cert_info:
        user._cert_info = cert_info
    
    return user

# =============================================================================
# Service-Specific Dependencies
# =============================================================================

def require_api_access(scopes: Optional[List[ServiceScope]] = None):
    """Dependency factory for API service access."""
    default_scopes = [ServiceScope.API_READ]
    final_scopes = (scopes or []) + default_scopes
    
    async def dependency(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
        return await get_current_user_enhanced(
            request=request,
            audience=TokenAudience.API_SERVICE,
            required_scopes=final_scopes,
            db=db
        )
    
    return dependency

def require_admin_access():
    """Dependency for admin-only access."""
    async def dependency(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
        user = await get_current_user_enhanced(
            request=request,
            audience=TokenAudience.API_SERVICE,
            required_scopes=[ServiceScope.API_ADMIN],
            db=db
        )
        
        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator privileges required"
            )
        
        return user
    
    return dependency

def require_worker_access():
    """Dependency for worker service access."""
    async def dependency(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
        return await get_current_user_enhanced(
            request=request,
            audience=TokenAudience.WORKER_SERVICE,
            required_scopes=[ServiceScope.WORKER_EXECUTE],
            db=db
        )
    
    return dependency

def require_streaming_access():
    """Dependency for streaming/WebSocket access."""
    async def dependency(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
        return await get_current_user_enhanced(
            request=request,
            audience=TokenAudience.WEB_UI,
            required_scopes=[ServiceScope.API_STREAM],
            db=db
        )
    
    return dependency

# =============================================================================
# WebSocket Enhanced Authentication
# =============================================================================

async def get_current_user_websocket_enhanced(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None
) -> User:
    """Enhanced WebSocket authentication with JWT validation."""
    
    if not token:
        logger.warning("WebSocket authentication failed: No token provided")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    
    # Clean token
    import urllib.parse
    decoded_token = urllib.parse.unquote(token)
    cleaned_token = decoded_token.strip('"').replace("Bearer ", "")
    
    # Get JWT service
    jwt_service = await get_enhanced_jwt_service()
    
    try:
        # Validate WebSocket token
        token_data = jwt_service.validate_token(
            token=cleaned_token,
            expected_audience=TokenAudience.WEB_UI,
            required_scopes=[ServiceScope.API_STREAM]
        )
        
        # Look up user
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.id == token_data.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            if user.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is not active"
                )
            
            logger.info(f"WebSocket enhanced authentication successful for user: {user.email}")
            return user
            
        finally:
            db.close()
            
    except HTTPException as e:
        logger.error(f"WebSocket authentication failed: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

# =============================================================================
# Enhanced CSRF Protection
# =============================================================================

async def verify_enhanced_csrf_token(request: Request):
    """Enhanced CSRF token verification with additional security checks."""
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-TOKEN")
    
    if not csrf_cookie or not csrf_header:
        logger.warning("CSRF validation failed: Missing tokens")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required"
        )
    
    if csrf_cookie != csrf_header:
        logger.warning("CSRF validation failed: Token mismatch")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch"
        )
    
    # Additional security: Check token format and length
    if len(csrf_cookie) < 32:
        logger.warning("CSRF validation failed: Token too short")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token format"
        )
    
    # Log successful CSRF validation
    logger.debug("CSRF token validation successful")

# =============================================================================
# Rate Limiting Dependencies
# =============================================================================

async def check_rate_limit(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 3600
) -> None:
    """Rate limiting dependency using Redis."""
    try:
        jwt_service = await get_enhanced_jwt_service()
        if not jwt_service.redis:
            return  # No rate limiting if Redis unavailable
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        client_id = f"rate_limit:{client_ip}:{hash(user_agent) % 10000}"
        
        # Check current count
        current_count = await jwt_service.redis.get(client_id)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= max_requests:
            logger.warning(f"Rate limit exceeded for client: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Increment counter
        pipe = jwt_service.redis.pipeline()
        pipe.incr(client_id)
        pipe.expire(client_id, window_seconds)
        await pipe.execute()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Don't fail requests due to rate limiting errors

# =============================================================================
# Legacy Compatibility Wrappers
# =============================================================================

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Legacy compatibility wrapper for get_current_user."""
    return await get_current_user_enhanced(
        request=request,
        audience=TokenAudience.API_SERVICE,
        required_scopes=None,
        db=db
    )

async def verify_csrf_token(request: Request):
    """Legacy compatibility wrapper for CSRF verification."""
    await verify_enhanced_csrf_token(request)

# =============================================================================
# Service Token Dependencies
# =============================================================================

async def validate_service_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> EnhancedTokenData:
    """Validate service-to-service authentication tokens."""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    jwt_service = await get_enhanced_jwt_service()
    
    try:
        token_data = jwt_service.validate_token(
            token=credentials.credentials,
            expected_audience=TokenAudience.API_SERVICE,
            required_scopes=None  # Service tokens define their own scopes
        )
        
        if token_data.token_type != TokenType.SERVICE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for service authentication"
            )
        
        logger.info(f"Service token validation successful: {token_data.service_context.get('service_name', 'unknown')}")
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token validation failed"
        )

# =============================================================================
# Security Headers Middleware Dependency
# =============================================================================

def add_security_headers(request: Request, response):
    """Add enhanced security headers to response."""
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    # Basic security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' wss: ws:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "media-src 'self'; "
        "frame-src 'none';"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    
    # HTTPS-only headers for production
    if is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # mTLS indicator header
    if os.getenv("MTLS_ENABLED", "false").lower() == "true":
        response.headers["X-mTLS-Enabled"] = "true"
    
    return response