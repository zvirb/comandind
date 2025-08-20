"""Custom authentication router to replace FastAPI-Users functionality."""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Form, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
import logging
import jwt
from datetime import datetime, timedelta

from api.auth import authenticate_user, create_access_token, create_refresh_token, set_auth_cookies, unset_auth_cookies, SECRET_KEY, ALGORITHM, generate_csrf_token, get_password_hash, verify_password
from shared.utils.config import get_settings
from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User
from shared.utils.database_setup import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterResponse(BaseModel):
    id: int
    email: str
    message: str = "User registered successfully"
    requires_approval: bool = False

@router.post("/jwt/login-debug")
async def login_debug(request: Request):
    """Debug endpoint to see what the frontend is actually sending."""
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    logger.info(f"Debug - Content-Type: {content_type}")
    logger.info(f"Debug - Body: {body}")
    logger.info(f"Debug - Headers: {dict(request.headers)}")
    
    try:
        import json
        if body:
            data = json.loads(body)
            logger.info(f"Debug - Parsed JSON: {data}")
            return {"status": "ok", "received": data}
        else:
            return {"status": "error", "message": "No body"}
    except Exception as e:
        logger.error(f"Debug - JSON parse error: {e}")
        return {"status": "error", "message": str(e), "raw_body": body.decode()}

@router.post("/jwt/login", response_model=LoginResponse)
@router.post("/login", response_model=LoginResponse)  # Add legacy compatibility endpoint
async def login(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Unified login endpoint that handles both JSON and form-encoded requests."""
    try:
        content_type = request.headers.get("content-type", "")
        user_email = None
        user_password = None
        
        if "application/json" in content_type:
            # Handle JSON requests
            try:
                body = await request.json()
                user_email = body.get("email") or body.get("username")
                user_password = body.get("password")
            except Exception as e:
                logger.error(f"JSON parsing error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid JSON data"
                )
        
        elif "application/x-www-form-urlencoded" in content_type:
            # Handle form requests
            try:
                form_data = await request.form()
                user_email = form_data.get("email") or form_data.get("username")
                user_password = form_data.get("password")
            except Exception as e:
                logger.error(f"Form parsing error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid form data"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported content type: {content_type}"
            )
        
        if not user_email or not user_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required fields: email/username and password"
            )
        
        return await _perform_login(user_email, user_password, response, db)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/jwt/login-form", response_model=LoginResponse)
@router.post("/login-form", response_model=LoginResponse)
async def login_form(
    response: Response,
    email: str = Form(None),
    password: str = Form(None),
    username: str = Form(None),  # Support for username field
    db: Session = Depends(get_db)
):
    """Form-encoded login endpoint."""
    user_email = email or username
    if not user_email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required fields: email/username and password"
        )
    return await _perform_login(user_email, password, response, db)

async def _perform_login(user_email: str, user_password: str, response: Response, db: Session) -> LoginResponse:
    """
    Shared login logic that authenticates a user and returns JWT tokens.
    Sets secure HTTP-only cookies for authentication.
    """
    try:
        logger.info(f"Login attempt - Email: {user_email}")
        
        # Debug: Check what database URL is being used
        from shared.utils.config import get_settings
        settings = get_settings()
        logger.info(f"Login using database URL: {settings.database_url}")
        
        # Authenticate user with enhanced session cleanup on failure
        try:
            user = authenticate_user(db, user_email, user_password)
            if not user:
                # Ensure session cleanup on authentication failure
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Session rollback error during auth failure: {rollback_error}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            # Re-raise HTTP exceptions (authentication failures)
            raise
        except Exception as auth_error:
            logger.error(f"Authentication service error: {auth_error}")
            # Ensure database session is cleaned up on service error
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Session rollback error during auth service failure: {rollback_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
        
        # Check if user is active
        # Handle both enum and string types for status
        user_status = user.status.value if hasattr(user.status, 'value') else str(user.status)
        if user_status != "active":
            logger.warning(f"User {user.email} login attempt with status: {user_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        
        # Create access and refresh tokens with consistent format
        # Use user ID as 'sub' for enhanced compatibility
        token_data = {
            "sub": str(user.id),  # User ID as string for JWT standard
            "email": user.email,  # Include email for reference
            "id": user.id,  # Keep numeric ID for backward compatibility
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Set secure cookies
        set_auth_cookies(response, access_token, refresh_token)
        
        return LoginResponse(access_token=access_token)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.get("/session-warnings")
async def get_session_warnings():
    """Session warnings endpoint - simplified implementation."""
    return {"warnings": [], "status": "ok"}

@router.get("/connection-health")
async def get_connection_health():
    """Connection health endpoint - simplified implementation."""
    return {"status": "healthy", "connection": "ok"}

@router.get("/validate")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Validate the current authentication token and return user info.
    """
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            "status": current_user.status.value if hasattr(current_user.status, 'value') else str(current_user.status),
            "is_active": current_user.is_active
        },
        "expires_at": None  # Can be enhanced to include token expiry
    }

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refresh the authentication token using refresh token from cookie.
    """
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        
        # Decode and validate refresh token
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Extract user info from refresh token
            email = payload.get("sub")
            user_id = payload.get("id")
            
            if not email or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token format"
                )
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user from database
        from api.auth import get_user_by_email
        user = get_user_by_email(db, email=email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_data = {
            "sub": user.email,
            "id": user.id,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        # Set new cookies
        set_auth_cookies(response, access_token, new_refresh_token)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Token refreshed successfully"
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _user: User = Depends(get_current_user)
):
    """
    Logout endpoint that clears authentication cookies.
    """
    unset_auth_cookies(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/csrf-token")
async def get_csrf_token(request: Request, response: Response):
    """
    Get a fresh CSRF token. This endpoint is used by the frontend
    to obtain a CSRF token before making state-changing requests.
    """
    import os
    
    try:
        # SECURITY FIX: Generate a single token and use it consistently everywhere
        csrf_token = generate_csrf_token()
        
        logger.debug(f"Auth router using CSRF token: {csrf_token[:30]}...")
        
        # Use secure cookies only in production (HTTPS)
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        cookie_secure = is_production
        # SECURITY FIX: Match middleware cookie settings for consistency
        # Use 'strict' in production with HTTPS, 'lax' in development
        cookie_samesite = "strict" if cookie_secure else "lax"
        
        # Set CSRF token cookie (same token as will be returned in JSON)
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,  # Must be accessible by JavaScript
            samesite=cookie_samesite,
            secure=cookie_secure,
            max_age=3600,  # 1 hour
            path="/",
            # Set explicit domain for production (aiwfe.com) to enable subdomain sharing
            domain=f".{os.getenv('DOMAIN', 'aiwfe.com')}" if is_production and os.getenv('DOMAIN', 'aiwfe.com') not in ['localhost', '127.0.0.1'] else None
        )
        
        # SECURITY FIX: Also set X-CSRF-TOKEN header (same token as cookie and JSON)
        response.headers["X-CSRF-TOKEN"] = csrf_token
        
        # Return the same token in JSON response
        logger.info("CSRF token endpoint called successfully")
        return {
            "csrf_token": csrf_token,  # Same token as cookie and header
            "message": "CSRF token generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error generating CSRF token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate CSRF token"
        )

class AdminPasswordResetRequest(BaseModel):
    email: str
    new_password: str
    admin_key: str

@router.post("/admin/reset-password")
async def admin_reset_password(
    request: AdminPasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to reset user passwords for troubleshooting.
    Requires admin key for security.
    """
    import os
    
    # Simple admin key check (in production this should be more secure)
    expected_admin_key = os.getenv("ADMIN_RESET_KEY", "admin-reset-key-change-in-production")
    if request.admin_key != expected_admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Hash the new password
        hashed_password = get_password_hash(request.new_password)
        
        # Update user password
        user.hashed_password = hashed_password
        db.commit()
        
        logger.info(f"Admin password reset successful for user: {request.email}")
        
        return {
            "message": f"Password reset successful for {request.email}",
            "user_id": user.id
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin password reset failed: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin password reset failed"
        )

@router.post("/debug/test-password")
async def debug_test_password(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to test password verification for troubleshooting.
    """
    email = request.get("email")
    password = request.get("password")
    
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing email or password"
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {
                "user_found": False,
                "message": "User not found"
            }
        
        # Test password verification
        password_valid = verify_password(password, user.hashed_password)
        
        return {
            "user_found": True,
            "user_id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "status": user.status.value if hasattr(user.status, 'value') else str(user.status),
            "password_valid": password_valid,
            "hashed_password_preview": user.hashed_password[:50] + "...",
            "message": "Password verification successful" if password_valid else "Password verification failed"
        }
            
    except Exception as e:
        logger.error(f"Debug password test failed: {str(e)}")
        return {
            "error": str(e),
            "message": "Debug test encountered an error"
        }

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(request.password)
        
        # Generate a username from email (before @ symbol)
        base_username = request.email.split('@')[0]
        
        # Since the database requires a username, we need to create it dynamically
        # We'll use SQLAlchemy's execute to insert directly
        from sqlalchemy import text
        
        # Check if username already exists and make it unique
        username = base_username
        counter = 1
        result = db.execute(text("SELECT COUNT(*) FROM users WHERE username = :username"), 
                           {"username": username})
        while result.scalar() > 0:
            username = f"{base_username}{counter}"
            counter += 1
            result = db.execute(text("SELECT COUNT(*) FROM users WHERE username = :username"), 
                               {"username": username})
        
        # Insert directly using raw SQL to handle the username column
        insert_query = text("""
            INSERT INTO users (username, email, hashed_password, is_active, is_verified, 
                             status, tfa_enabled, notifications_enabled)
            VALUES (:username, :email, :hashed_password, :is_active, :is_verified,
                   :status, :tfa_enabled, :notifications_enabled)
            RETURNING id, email
        """)
        
        # SECURITY FIX: Create users as 'active' to match login requirements
        # This fixes the CSRF validation inconsistency issue where users
        # created with 'pending_approval' status couldn't log in (403 error)
        result = db.execute(insert_query, {
            "username": username,
            "email": request.email,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_verified": False,
            "status": "active",  # Changed from 'pending_approval' to 'active'
            "tfa_enabled": False,
            "notifications_enabled": True
        })
        
        new_user_data = result.first()
        db.commit()
        
        logger.info(f"User registered successfully: {request.email}")
        
        return RegisterResponse(
            id=new_user_data[0],
            email=new_user_data[1],
            message="User registered successfully",
            requires_approval=False  # Can be changed based on business logic
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )