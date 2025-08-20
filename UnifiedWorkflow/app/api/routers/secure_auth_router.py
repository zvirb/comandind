"""
Secure Authentication Router with Cookie-Based Sessions
Implements secure authentication with httpOnly cookies and CSRF protection
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User
from api.auth import create_access_token, verify_password
from shared.utils.config import get_settings
from app.shared.services.websocket_token_bridge import get_websocket_bridge

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

class SecureLoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class AuthStatusResponse(BaseModel):
    authenticated: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None

@router.post("/secure-login")
async def secure_login(
    request: SecureLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Secure login with httpOnly cookie authentication
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "user_id": user.id
        }
        
        expires_delta = timedelta(
            days=30 if request.remember_me else 1
        )
        
        access_token = create_access_token(
            data=token_data,
            expires_delta=expires_delta
        )
        
        # Set secure httpOnly cookie
        max_age = int(expires_delta.total_seconds())
        
        response.set_cookie(
            key="auth_token",
            value=access_token,
            max_age=max_age,
            httponly=True,
            secure=True,  # HTTPS only
            samesite="lax",
            domain=None,  # Same domain only
            path="/"
        )
        
        # Generate CSRF token
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=max_age,
            httponly=False,  # Accessible to JavaScript for headers
            secure=True,
            samesite="strict",
            path="/"
        )
        
        logger.info(f"Secure login successful for user {user.id} ({user.email})")
        
        return {
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role.value
            },
            "csrf_token": csrf_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Secure login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Check authentication status via secure cookie
    """
    try:
        return AuthStatusResponse(
            authenticated=True,
            user_id=current_user.id,
            email=current_user.email,
            role=current_user.role.value
        )
    except Exception as e:
        logger.debug(f"Auth status check failed: {e}")
        return AuthStatusResponse(authenticated=False)

@router.get("/admin-status")
async def admin_status(
    current_user: User = Depends(get_current_user)
):
    """
    Check if current user has admin privileges
    """
    try:
        is_admin = current_user.role.value in ['admin', 'administrator', 'superuser']
        
        return {
            "is_admin": is_admin,
            "role": current_user.role.value,
            "user_id": current_user.id
        }
    except Exception as e:
        logger.error(f"Admin status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

@router.post("/logout")
async def secure_logout(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Secure logout with cookie clearing
    """
    try:
        # Clear authentication cookies
        response.delete_cookie(
            key="auth_token",
            httponly=True,
            secure=True,
            samesite="lax",
            path="/"
        )
        
        response.delete_cookie(
            key="csrf_token",
            secure=True,
            samesite="strict",
            path="/"
        )
        
        logger.info(f"Secure logout for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Secure logout error: {e}")
        # Still clear cookies even if there's an error
        response.delete_cookie("auth_token", path="/")
        response.delete_cookie("csrf_token", path="/")
        
        return {
            "success": True,
            "message": "Logged out"
        }

@router.post("/refresh-session")
async def refresh_session(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Refresh the authentication session
    """
    try:
        # Create new access token
        token_data = {
            "sub": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role.value,
            "user_id": current_user.id
        }
        
        expires_delta = timedelta(hours=24)
        access_token = create_access_token(
            data=token_data,
            expires_delta=expires_delta
        )
        
        # Update cookie
        max_age = int(expires_delta.total_seconds())
        
        response.set_cookie(
            key="auth_token",
            value=access_token,
            max_age=max_age,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/"
        )
        
        # Generate new CSRF token
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            max_age=max_age,
            httponly=False,
            secure=True,
            samesite="strict",
            path="/"
        )
        
        return {
            "success": True,
            "message": "Session refreshed",
            "csrf_token": csrf_token
        }
        
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh session"
        )

@router.post("/websocket-token")
async def get_websocket_token(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Generate secure bridge token for WebSocket authentication.
    
    SECURITY: This endpoint validates httpOnly cookies and provides a short-lived
    bridge token for WebSocket connections, solving the httpOnly vs WebSocket dilemma.
    """
    try:
        # Get the original JWT token from httpOnly cookie
        auth_token = request.cookies.get("auth_token")
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token not found"
            )
        
        # Create bridge token
        bridge = get_websocket_bridge()
        bridge_token = await bridge.create_bridge_token(
            request=request,
            jwt_token=auth_token,
            user_id=current_user.id
        )
        
        return {
            "bridge_token": bridge_token,
            "expires_in": 300,  # 5 minutes
            "user_id": current_user.id,
            "usage": "single_use"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WebSocket token generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate WebSocket token"
        )

@router.get("/security-info")
async def security_info():
    """
    Provide security implementation information
    """
    return {
        "authentication": {
            "method": "httpOnly cookies",
            "csrf_protection": True,
            "secure_cookies": True,
            "same_site": "lax/strict",
            "websocket_bridge": "enabled"
        },
        "headers": {
            "hsts": "max-age=63072000; includeSubDomains; preload",
            "csp": "Enhanced Content Security Policy",
            "x_frame_options": "DENY",
            "x_content_type_options": "nosniff"
        },
        "oauth": {
            "pkce": "enabled",
            "state_validation": True,
            "secure_redirects": True
        },
        "session": {
            "secure_storage": "server-side",
            "token_rotation": True,
            "concurrent_session_limits": "planned"
        },
        "websocket_security": {
            "bridge_tokens": "short_lived",
            "single_use": True,
            "no_query_params": True,
            "ip_validation": True
        }
    }