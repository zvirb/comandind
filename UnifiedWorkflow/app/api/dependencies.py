"""FastAPI dependencies for authentication and authorization."""

from typing import List, Optional, Annotated
from dataclasses import dataclass
import time

from fastapi import Depends, HTTPException, Request, status, Query, WebSocket, WebSocketException
import jwt
from jwt import InvalidTokenError as JWTError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
 
from shared.schemas import TokenData
from api.auth import ALGORITHM, SECRET_KEY, is_token_activity_expired, get_user_by_email
from shared.database.models import User, UserRole, UserStatus
from shared.utils.database_setup import get_db, get_async_session
from shared.utils.config import get_settings
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.auth_middleware_service import auth_middleware_service
from shared.services.security_audit_service import security_audit_service
from shared.services.jwt_consistency_service import jwt_consistency_service

settings = get_settings()

credentials_exception = HTTPException(
   status_code=status.HTTP_401_UNAUTHORIZED,
   detail="Could not validate credentials",
   headers={"WWW-Authenticate": "Bearer"},
)

def get_current_user_payload(request: Request) -> TokenData:
    """
    Unified token payload parser supporting both legacy and enhanced JWT formats.
    This function provides backward compatibility while supporting new token structures.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    token = None
    
    # Extract token from request (Authorization header or cookie)
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            scheme, _, param = auth_header.partition(' ')
            if scheme and scheme.lower() == 'bearer' and param:
                token = param
        except Exception as e:
            logger.debug(f"Failed to parse authorization header: {e}")
    
    # Fallback to cookie if no valid header token
    if not token:
        # Check for both cookie types (legacy and secure)
        cookie_token = request.cookies.get("access_token") or request.cookies.get("auth_token")
        if cookie_token:
            token = cookie_token
    
    if not token:
        logger.error("No valid authentication token found")
        raise credentials_exception

    try:
        # SECURITY FIX: Use centralized JWT service for consistent SECRET_KEY usage
        payload = jwt_consistency_service.decode_token(
            token,
            options={
                "verify_exp": True,
                "verify_nbf": False,  # Don't verify not-before claim (might not be set)
                "verify_iat": False,  # Don't verify issued-at time (might not be set)
                "verify_aud": False,  # Don't verify audience (not being set in tokens)
            }
        )
        
        # Unified token format handling
        email: Optional[str] = None
        user_id: Optional[int] = None
        role: Optional[str] = None
        
        # Enhanced format (sub=user_id, email=email, role=role)
        if "email" in payload and "sub" in payload:
            try:
                user_id = int(payload.get("sub"))
                email = payload.get("email")
                role = payload.get("role")
                logger.debug(f"Parsed enhanced token format for user {user_id}")
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
                logger.debug(f"Parsed legacy token format for user {user_id}")
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
            raise credentials_exception
        
        # Create TokenData with validated information
        try:
            token_data = TokenData(id=user_id, email=email, role=UserRole(role))
            logger.debug(f"Successfully validated token for user {user_id} ({email})")
            return token_data
        except ValueError as e:
            logger.error(f"Invalid role value '{role}' in token: {e}")
            raise credentials_exception from e
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise credentials_exception
    except jwt.InvalidSignatureError:
        logger.error("JWT signature verification failed - possible SECRET_KEY mismatch between token creation and validation")
        # This is likely a Bearer token created with a different SECRET_KEY
        raise credentials_exception
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise credentials_exception from e
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise credentials_exception from e


async def get_current_user(request: Request, db: AsyncSession = Depends(get_async_session)) -> User:
    """
    Optimized authentication dependency using the enhanced authentication service.
    
    Performance optimizations:
    - Fast-path JWT validation with Redis caching
    - Reduced database queries through intelligent caching
    - Connection pool optimization
    - Target: <100ms total authentication time (90% improvement)
    
    Falls back to legacy authentication for complex edge cases.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    
    try:
        # First, check if user is already validated by middleware
        if hasattr(request.state, 'authenticated_user_id') and request.state.authenticated_user_id:
            # Fast path - user already validated by performance middleware
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(
                    User.id == request.state.authenticated_user_id,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            if user:
                response_time = (time.time() - start_time) * 1000
                logger.debug(f"Middleware-cached authentication: {response_time:.2f}ms for user {user.id}")
                return user
        
        # Try optimized authentication service first
        try:
            from api.services.optimized_auth_service import optimized_auth_service
            
            # Extract token from request
            token = None
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
            else:
                token = request.cookies.get("access_token")
            
            if token:
                is_valid, user, metadata = await optimized_auth_service.validate_token_optimized(
                    token, db, is_session_validation=False
                )
                
                if is_valid and user:
                    response_time = (time.time() - start_time) * 1000
                    logger.debug(f"Optimized auth successful: {response_time:.2f}ms for user {user.id} (cached: {metadata.get('cached', False)})")
                    return user
                    
        except Exception as opt_error:
            logger.debug(f"Optimized authentication failed, using fallback: {opt_error}")
        
        # Fallback to fast authentication optimization system
        try:
            from auth_performance_optimizations import get_current_user_fast
            user = await get_current_user_fast(request, db)
            response_time = (time.time() - start_time) * 1000
            logger.debug(f"Fast auth optimization successful: {response_time:.2f}ms for user {user.id}")
            return user
            
        except Exception as fast_error:
            logger.debug(f"Fast authentication failed, using legacy: {fast_error}")
        
        # Legacy authentication (original implementation) for edge cases
        logger.info("Using legacy authentication (consider optimizing this case)")
        
        # Parse and validate token first (no database calls)
        try:
            token_data = get_current_user_payload(request)
        except HTTPException:
            logger.debug("Token validation failed")
            raise
        
        # Single database lookup using injected async session
        try:
            # Single optimized query to get user
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(
                    User.id == token_data.id,
                    User.is_active == True  # Pre-filter inactive users
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {token_data.id} not found or inactive")
                raise credentials_exception
            
            # Validate email matches token for security
            if user.email != token_data.email:
                logger.error(f"Email mismatch: token={token_data.email}, db={user.email}")
                raise credentials_exception
                
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"Legacy authentication used: {response_time:.2f}ms for user {user.id} - consider optimization")
            return user
            
        except HTTPException:
            # Re-raise authentication failures
            raise
        except Exception as e:
            logger.warning(f"Async database lookup failed, attempting sync fallback: {e}")
            
            # Fallback to sync session for database connectivity issues
            try:
                db_gen = get_db()
                db_sync = next(db_gen)
                
                try:
                    # Single sync query with same optimizations
                    user = get_user_by_email(db_sync, email=token_data.email)
                    
                    if not user or not user.is_active:
                        logger.error(f"User {token_data.email} not found or inactive (sync)")
                        raise credentials_exception
                    
                    # Validate user ID matches token
                    if user.id != token_data.id:
                        logger.error(f"User ID mismatch: token={token_data.id}, db={user.id}")
                        raise credentials_exception
                    
                    response_time = (time.time() - start_time) * 1000
                    logger.warning(f"Sync fallback authentication: {response_time:.2f}ms for user {user.id}")
                    return user
                    
                finally:
                    db_sync.close()
                    
            except HTTPException:
                raise
            except Exception as sync_error:
                logger.error(f"Authentication failed completely: {sync_error}")
                raise credentials_exception from sync_error
                
    except HTTPException:
        response_time = (time.time() - start_time) * 1000
        logger.debug(f"Authentication failed: {response_time:.2f}ms")
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Authentication error: {response_time:.2f}ms - {e}")
        raise credentials_exception from e


class RoleChecker:
    """Dependency that checks if the current user has one of the allowed roles."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )


async def verify_csrf_token(request: Request):
    """
    Dependency to verify the CSRF token using the double-submit cookie pattern.
    This should be applied to all state-changing (POST, PUT, PATCH, DELETE) endpoints.
    """
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-TOKEN") # Standard header name

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch or missing. Request forbidden.",
        )
    # If tokens match, proceed. No return value needed.

async def get_current_user_ws(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
):
    """
    Simplified and robust WebSocket authentication dependency.
    Handles token extraction from multiple sources with clear error reporting.
    """
    import logging
    import urllib.parse
    logger = logging.getLogger(__name__)
    
    logger.info("WebSocket authentication starting")
    
    # Extract token from multiple possible sources
    if token is None:
        # Method 1: WebSocket subprotocol (browser-compatible)
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if protocols:
            logger.debug(f"WebSocket protocols: {protocols}")
            for protocol in protocols.split(","):
                protocol = protocol.strip()
                if protocol.startswith("Bearer."):
                    token = protocol[7:]  # Remove "Bearer." prefix
                    logger.info("Token extracted from WebSocket subprotocol")
                    break
        
        # Method 2: Authorization header (fallback)
        if token is None:
            auth_header = websocket.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                logger.info("Token extracted from Authorization header")
    
    if token is None:
        logger.error("No authentication token found in query, subprotocol, or header")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")

    # Clean and validate token
    try:
        # URL decode and clean token
        decoded_token = urllib.parse.unquote(token)
        cleaned_token = decoded_token.strip('"').replace("Bearer ", "").strip()
        
        if not cleaned_token:
            logger.error("Empty token after cleaning")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token format")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token format")
            
        logger.debug(f"Token cleaned successfully (length: {len(cleaned_token)})")
        
        # Decode JWT with simplified options
        from api.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(
            cleaned_token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_nbf": False,  # Don't verify not-before (may not be set)
                "verify_iat": False,  # Don't verify issued-at (may not be set)
                "verify_aud": False   # Don't verify audience (not being used)
            },
            leeway=60  # Allow 60 seconds clock skew
        )
        
        # Extract user information with unified approach
        user_email = None
        user_id = None
        
        # Try enhanced format first (sub=user_id, email=email)
        if "email" in payload and "sub" in payload:
            try:
                sub_value = payload.get("sub")
                if isinstance(sub_value, int) or sub_value.isdigit():
                    user_id = int(sub_value)
                    user_email = payload.get("email")
                    logger.debug(f"Enhanced token format: user_id={user_id}, email={user_email}")
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Fallback to legacy format (sub=email, id=user_id)
        if not user_email:
            sub_value = payload.get("sub")
            if sub_value and "@" in str(sub_value):
                user_email = sub_value
                user_id = payload.get("id")
                logger.debug(f"Legacy token format: email={user_email}, user_id={user_id}")
        
        if not user_email:
            logger.error(f"No email found in token payload. Available keys: {list(payload.keys())}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
        
        # Database lookup with proper connection handling
        from shared.utils.database_setup import get_db
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            user = get_user_by_email(db, email=user_email)
            
            if not user:
                logger.error(f"User not found: {user_email}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            
            if not user.is_active:
                logger.error(f"User is inactive: {user_email}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User inactive")
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User inactive")
            
            # Validate user ID if available in token
            if user_id and user.id != user_id:
                logger.error(f"User ID mismatch: token={user_id}, db={user.id}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token validation failed")
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token validation failed")
            
            logger.info(f"WebSocket authentication successful for user {user.id} ({user.email})")
            return user
            
        finally:
            db.close()
            
    except jwt.ExpiredSignatureError:
        logger.error("JWT token expired")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
    except WebSocketException:
        raise  # Re-raise WebSocket exceptions
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Authentication error")
        raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR, reason="Authentication error")

@dataclass
class AuthenticationMetrics:
    """Authentication performance metrics tracking"""
    response_time_ms: float
    cache_hit: bool
    auth_method: str
    timestamp: str
