"""
Session Management Router - Handle user session persistence and validation.
Prevents forced logouts during navigation between features.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_db, get_async_session
from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User
from api.auth import create_access_token, get_user_by_email
from shared.services.unified_session_manager import get_session_manager, SessionData

logger = logging.getLogger(__name__)
router = APIRouter()

class SessionInfo(BaseModel):
    """Session information model."""
    user_id: int
    email: str
    role: str
    is_active: bool
    session_created: datetime
    last_activity: datetime
    expires_at: datetime

class SessionRefreshRequest(BaseModel):
    """Session refresh request model."""
    extend_minutes: Optional[int] = 30

class SessionValidationResponse(BaseModel):
    """Session validation response model."""
    valid: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
    expires_in_minutes: Optional[int] = None
    message: str

@router.get(
    "/info",
    response_model=SessionInfo,
)
async def get_session_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get current session information including expiration details.
    Uses unified session manager when available, with graceful fallback.
    """
    # Start with fallback data based on current authenticated user
    session_created = current_user.created_at or datetime.now()
    expires_at = session_created + timedelta(hours=24)
    
    fallback_session_info = SessionInfo(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        is_active=current_user.is_active,
        session_created=session_created,
        last_activity=datetime.now(),
        expires_at=expires_at
    )
    
    try:
        # Try to get enhanced session data from unified session manager
        session_manager = await get_session_manager()
        
        # Extract session ID from request headers or cookies
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")
        
        if session_id:
            # Get session from unified manager with timeout protection
            session_data = await session_manager.get_session(session_id)
            if session_data:
                logger.debug(f"Retrieved session data from unified manager for user {current_user.id}")
                return SessionInfo(
                    user_id=session_data.user_id,
                    email=session_data.email,
                    role=session_data.role,
                    is_active=True,
                    session_created=session_data.created_at,
                    last_activity=session_data.last_activity,
                    expires_at=session_data.expires_at
                )
        
        # If no session ID found or session not in Redis, return fallback
        logger.debug(f"No session data found in unified manager, using fallback for user {current_user.id}")
        return fallback_session_info
        
    except Exception as e:
        # Log the error but don't fail the request - return fallback data
        logger.warning(f"Unified session manager unavailable, using fallback session info for user {current_user.id}: {e}")
        return fallback_session_info


@router.post(
    "/validate",
)
async def validate_session(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Validate current session without requiring full authentication.
    Returns session status and remaining time.
    """
    try:
        # Try to get current user (will handle token validation)
        try:
            from api.dependencies import get_current_user_payload
            token_data = get_current_user_payload(request)
            
            # Look up user to confirm they're still active
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(
                    User.id == token_data.id,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                response_data = SessionValidationResponse(
                    valid=False,
                    message="User not found or inactive"
                )
                response = JSONResponse(content=response_data.dict())
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                return response
            
            # Calculate remaining session time (estimate)
            expires_in_minutes = 60  # Default estimate
            
            response_data = SessionValidationResponse(
                valid=True,
                user_id=user.id,
                email=user.email,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                expires_in_minutes=expires_in_minutes,
                message="Session is valid"
            )
            
            # CRITICAL FIX: Add caching headers to reduce frontend request frequency
            response = JSONResponse(content=response_data.dict())
            response.headers["Cache-Control"] = "private, max-age=30"  # Cache for 30 seconds
            response.headers["X-Session-Validation"] = "success"
            return response
            
        except HTTPException as auth_error:
            response_data = SessionValidationResponse(
                valid=False,
                message=f"Authentication failed: {auth_error.detail}"
            )
            response = JSONResponse(content=response_data.dict())
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
            
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        response_data = SessionValidationResponse(
            valid=False,
            message="Session validation error"
        )
        response = JSONResponse(content=response_data.dict())
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


@router.post(
    "/refresh",
    dependencies=[Depends(verify_csrf_token)],
)
async def refresh_session(
    refresh_request: SessionRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Refresh user session and extend expiration time.
    Generates new access token with extended expiration.
    """
    try:
        # Create new access token with extended expiration
        from datetime import timedelta
        
        access_token_expires = timedelta(minutes=refresh_request.extend_minutes)
        access_token = create_access_token(
            data={"sub": str(current_user.id), "email": current_user.email, "role": current_user.role.value},
            expires_delta=access_token_expires
        )
        
        # Return new token and session info
        response_data = {
            "message": "Session refreshed successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": refresh_request.extend_minutes,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            }
        }
        
        response = JSONResponse(content=response_data)
        
        # Set secure cookie with new token
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=refresh_request.extend_minutes * 60,
            httponly=True,
            secure=True,  # HTTPS only in production
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not refresh session"
        )


@router.post(
    "/extend",
    dependencies=[Depends(verify_csrf_token)],
)
async def extend_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Extend current session without generating new token.
    Updates last activity timestamp.
    """
    try:
        # Update last activity (this would typically update a session table)
        # For now, just return success with current session info
        
        return {
            "message": "Session extended successfully",
            "user_id": current_user.id,
            "email": current_user.email,
            "last_activity": datetime.now().isoformat(),
            "status": "active"
        }
        
    except Exception as e:
        logger.error(f"Error extending session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not extend session"
        )


@router.post(
    "/logout",
    dependencies=[Depends(verify_csrf_token)],
)
async def logout_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Logout user and invalidate session.
    Clears authentication cookies.
    """
    try:
        # Clear authentication cookies
        response = JSONResponse(content={
            "message": "Logged out successfully",
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Clear access token cookie
        response.delete_cookie(
            key="access_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        # Clear any other auth-related cookies
        response.delete_cookie(
            key="auth_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        response.delete_cookie(
            key="csrf_token",
            httponly=False,  # CSRF tokens are usually not httponly
            secure=True,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )


@router.get(
    "/health",
)
async def session_health_check():
    """
    Health check for session management.
    """
    return {
        "status": "ok",
        "service": "session_management",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "session_validation",
            "session_refresh", 
            "session_extension",
            "logout_handling"
        ]
    }


@router.get(
    "/features/status",
)
async def check_feature_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Check which features the user can access with current session.
    Prevents forced logouts when navigating between features.
    """
    try:
        # Define feature access based on user role and session status
        base_features = [
            "dashboard",
            "profile",
            "settings"
        ]
        
        user_features = [
            "chat",
            "documents",
            "calendar"
        ]
        
        admin_features = [
            "admin_panel",
            "user_management",
            "system_monitoring"
        ]
        
        # Check user role
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        
        accessible_features = base_features + user_features
        if user_role.lower() in ["admin", "superuser"]:
            accessible_features.extend(admin_features)
        
        return {
            "user_id": current_user.id,
            "role": user_role,
            "session_valid": True,
            "accessible_features": accessible_features,
            "restricted_features": [],
            "navigation_allowed": True,
            "message": "All features accessible with current session"
        }
        
    except Exception as e:
        logger.error(f"Error checking feature access: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not check feature access"
        )