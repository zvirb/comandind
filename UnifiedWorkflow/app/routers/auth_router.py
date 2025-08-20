"""Provides API endpoints for user authentication, including login, logout, and registration."""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
import logging
import secrets
from datetime import datetime, timedelta, timezone

from shared.utils.database_setup import get_async_db
from shared.services.auth_middleware_service import auth_middleware_service, AuthenticationState
from shared.services.secure_token_storage_service import secure_token_storage, TokenType, StorageType
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from api.auth import (
    authenticate_user,
    unset_auth_cookies,
    get_password_hash
)
from shared.schemas import Token, User as UserSchema, UserCreate
from api.dependencies import verify_csrf_token
from shared.database.models import User

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/token", response_model=Token)
async def login_for_access_token_form(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticates a user with email and password from form data and returns an access token.
    This endpoint uses enhanced authentication with race condition prevention.
    """
    try:
        # Initialize middleware if needed
        await auth_middleware_service.initialize()
        await security_audit_service.set_security_context(
            session=db,
            user_id=0,  # Will be updated after authentication
            service_name="auth_router"
        )
        
        # Get client information
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        device_fingerprint = request.headers.get("x-device-fingerprint", "")
        session_id = request.headers.get("x-session-id") or str(secrets.token_urlsafe(32))
        
        # Authenticate user (using existing sync method for compatibility)
        # Note: In full async migration, this would be converted to async
        from shared.utils.database_setup import get_db_sync
        with get_db_sync() as sync_db:
            user = authenticate_user(sync_db, email=username, password=password)
        
        if not user:
            # Log failed login attempt
            await security_audit_service.log_security_violation(
                session=db,
                violation_type="LOGIN_FAILED",
                severity="MEDIUM",
                violation_details={
                    "email": username,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "reason": "Invalid credentials"
                },
                ip_address=ip_address,
                user_agent=user_agent,
                blocked=True
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update security context with authenticated user
        await security_audit_service.set_security_context(
            session=db,
            user_id=user.id,
            session_id=session_id,
            service_name="auth_router",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Create enhanced JWT tokens
        access_token_data = await enhanced_jwt_service.create_access_token(
            session=db,
            user_id=user.id,
            scopes=["read", "write"],
            session_id=session_id,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address
        )
        
        # Create refresh token
        refresh_token_data = await enhanced_jwt_service.create_service_token(
            session=db,
            user_id=user.id,
            source_service="auth_router",
            target_service="token_refresh",
            permissions={"refresh": True},
            scope=["token_refresh"],
            expires_hours=24 * 7  # 7 days
        )
        
        access_token = access_token_data["access_token"]
        refresh_token = refresh_token_data["service_token"]
        
        # Store tokens in secure storage
        await secure_token_storage.store_token(
            session=db,
            user_id=user.id,
            token_type=TokenType.ACCESS_TOKEN,
            token_value=access_token,
            session_id=session_id,
            device_fingerprint=device_fingerprint,
            expires_at=datetime.fromisoformat(access_token_data["expires_at"]),
            storage_type=StorageType.SECURE_STORAGE,
            metadata={
                "scopes": access_token_data["scopes"],
                "jti": access_token_data["jti"],
                "login_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        await secure_token_storage.store_token(
            session=db,
            user_id=user.id,
            token_type=TokenType.REFRESH_TOKEN,
            token_value=refresh_token,
            session_id=session_id,
            device_fingerprint=device_fingerprint,
            expires_at=datetime.fromisoformat(refresh_token_data["expires_at"]),
            storage_type=StorageType.SECURE_STORAGE,
            metadata={
                "auth_id": refresh_token_data["auth_id"],
                "permissions": refresh_token_data["permissions"]
            }
        )
        
        # Generate CSRF token
        csrf_token = secrets.token_urlsafe(32)
        await secure_token_storage.store_token(
            session=db,
            user_id=user.id,
            token_type=TokenType.CSRF_TOKEN,
            token_value=csrf_token,
            session_id=session_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            storage_type=StorageType.SECURE_STORAGE
        )
        
        # Set secure authentication cookies
        await _set_enhanced_auth_cookies(response, access_token, refresh_token, csrf_token)
        
        # Log successful login
        await security_audit_service.log_data_access(
            session=db,
            user_id=user.id,
            service_name="auth_router",
            access_type="LOGIN_SUCCESS",
            table_name="user_sessions",
            row_count=1,
            sensitive_data_accessed=True,
            access_pattern={
                "session_id": session_id,
                "device_fingerprint": device_fingerprint,
                "login_method": "password",
                "token_expires_at": access_token_data["expires_at"]
            },
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Return token response
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "expires_in": access_token_data["expires_in"],
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Login failed with unexpected error: {str(e)}")
        
        # Log the error
        await security_audit_service.log_security_violation(
            session=db,
            violation_type="LOGIN_ERROR",
            severity="HIGH",
            violation_details={
                "error": str(e),
                "username": username,
                "ip_address": ip_address
            },
            ip_address=ip_address,
            blocked=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    revoke_all_sessions: bool = Form(default=False),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logs out the current user with enhanced session cleanup.
    Supports revoking all sessions or just the current one.
    """
    try:
        # Get session ID from request
        session_id = request.headers.get("x-session-id")
        
        if not session_id:
            # Try to extract from cookies or generate for cleanup
            session_id = str(secrets.token_urlsafe(32))
        
        # Use enhanced logout with cleanup
        await auth_middleware_service.logout_with_cleanup(
            request=request,
            response=response,
            session=db,
            session_id=session_id,
            revoke_all_sessions=revoke_all_sessions
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Logout failed: {str(e)}")
        
        # Fallback to basic cookie clearing
        unset_auth_cookies(response)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    user_create: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Registers a new user with enhanced security and audit logging.
    """
    try:
        # Get client information
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        
        # Set security context for registration
        await security_audit_service.set_security_context(
            session=db,
            user_id=0,
            service_name="auth_router",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_create.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Log registration attempt for existing user
            await security_audit_service.log_security_violation(
                session=db,
                violation_type="DUPLICATE_REGISTRATION",
                severity="LOW",
                violation_details={
                    "email": user_create.email,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                },
                ip_address=ip_address,
                user_agent=user_agent,
                blocked=True
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered."
            )
        
        # Create new user with enhanced password hashing
        hashed_password = get_password_hash(user_create.password)
        new_user = User(email=user_create.email, hashed_password=hashed_password)
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Update security context with new user ID
        await security_audit_service.set_security_context(
            session=db,
            user_id=new_user.id,
            service_name="auth_router",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Log successful registration
        await security_audit_service.log_data_access(
            session=db,
            user_id=new_user.id,
            service_name="auth_router",
            access_type="USER_REGISTRATION",
            table_name="users",
            row_count=1,
            sensitive_data_accessed=True,
            access_pattern={
                "email": user_create.email,
                "registration_timestamp": datetime.now(timezone.utc).isoformat(),
                "ip_address": ip_address
            },
            ip_address=ip_address
        )
        
        return new_user
        
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        
        # Log database error
        await security_audit_service.log_security_violation(
            session=db,
            violation_type="REGISTRATION_DB_ERROR",
            severity="MEDIUM",
            violation_details={
                "email": user_create.email,
                "error": str(exc),
                "ip_address": ip_address
            },
            ip_address=ip_address,
            blocked=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user due to a database error."
        ) from exc
    except Exception as e:
        await db.rollback()
        logger = logging.getLogger(__name__)
        logger.error(f"Registration failed: {str(e)}")
        
        # Log unexpected error
        await security_audit_service.log_security_violation(
            session=db,
            violation_type="REGISTRATION_ERROR",
            severity="HIGH",
            violation_details={
                "email": user_create.email,
                "error": str(e),
                "ip_address": ip_address
            },
            ip_address=ip_address,
            blocked=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration service error"
        )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Refresh access token using the enhanced authentication middleware.
    """
    try:
        session_id = request.headers.get("x-session-id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session ID required"
            )
        
        # Use middleware to refresh token with queuing
        success = await auth_middleware_service.refresh_token_with_queuing(
            request=request,
            response=response,
            session=db,
            session_id=session_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )
        
        return {"message": "Token refreshed successfully", "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Token refresh failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.post("/extend-session")
async def extend_user_session(
    request: Request,
    extension_minutes: int = Form(default=30),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Extend user session with activity-based renewal.
    """
    try:
        session_id = request.headers.get("x-session-id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session ID required"
            )
        
        # Use middleware to extend session
        success = await auth_middleware_service.extend_session(
            session=db,
            session_id=session_id,
            extension_minutes=extension_minutes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session extension failed"
            )
        
        return {"message": f"Session extended by {extension_minutes} minutes"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Session extension failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session extension service error"
        )


@router.get("/session-warnings")
async def get_session_warnings(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get session warnings (expiry, activity, security warnings).
    """
    try:
        session_id = request.headers.get("x-session-id")
        
        if not session_id:
            return {"warnings": []}
        
        warnings = await auth_middleware_service.get_session_warnings(session_id)
        return {"warnings": warnings}
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get session warnings: {str(e)}")
        return {"warnings": []}


@router.get("/connection-health")
async def get_connection_health(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get connection health information.
    """
    try:
        session_id = request.headers.get("x-session-id")
        
        if not session_id:
            return {"status": "unknown"}
        
        health = await auth_middleware_service.get_connection_health(session_id)
        return health
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get connection health: {str(e)}")
        return {"status": "error", "message": str(e)}


async def _set_enhanced_auth_cookies(
    response: Response, 
    access_token: str, 
    refresh_token: str, 
    csrf_token: str
):
    """Set enhanced secure authentication cookies."""
    import os
    
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Accessible by JavaScript for WebSocket auth
        secure=is_production,
        samesite="lax" if not is_production else "strict",
        max_age=30 * 60,  # 30 minutes
        path="/"
    )
    
    # Set refresh token cookie (more secure)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax" if not is_production else "strict",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/"
    )
    
    # Set CSRF token cookie
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Accessible by JavaScript for CSRF protection
        secure=is_production,
        samesite="lax" if not is_production else "strict",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/"
    )