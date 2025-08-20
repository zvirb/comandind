"""
Debug authentication router for testing token transmission and validation.
This router provides endpoints to test authentication flow and token handling.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User
from shared.utils.database_setup import get_async_session
from api.dependencies import get_current_user, get_current_user_payload

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/debug/auth/test-token")
async def test_token_validation(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test endpoint to validate token parsing and user authentication.
    Returns details about the authenticated user and token.
    """
    try:
        # Get raw token information
        auth_header = request.headers.get("authorization", "")
        cookie_token = request.cookies.get("access_token", "")
        
        # Get token payload for debugging
        token_data = get_current_user_payload(request)
        
        return {
            "success": True,
            "message": "Authentication successful",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "role": current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
                "is_active": current_user.is_active
            },
            "token_info": {
                "has_auth_header": bool(auth_header),
                "has_cookie_token": bool(cookie_token),
                "token_data": {
                    "id": token_data.id,
                    "email": token_data.email,
                    "role": token_data.role.value if hasattr(token_data.role, 'value') else str(token_data.role)
                }
            },
            "request_info": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Token test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Token validation test failed: {str(e)}"
        )

@router.get("/debug/auth/test-websocket-token")
async def test_websocket_token_format(
    token: Optional[str] = Query(None, description="WebSocket token to test"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Test endpoint to validate WebSocket token format without establishing WebSocket connection.
    Useful for debugging token transmission issues.
    """
    try:
        if not token:
            return {
                "success": False,
                "error": "No token provided",
                "message": "Provide token as query parameter: ?token=<your_jwt_token>"
            }
        
        import urllib.parse
        import jwt
        
        # Try both approaches to see if there's a difference
        try:
            from api.auth import SECRET_KEY as AUTH_SECRET_KEY, ALGORITHM
            logger.info(f"DEBUG: From api.auth - SECRET_KEY: {AUTH_SECRET_KEY[:10]}...")
        except ImportError as e:
            logger.error(f"Failed to import from api.auth: {e}")
            AUTH_SECRET_KEY = None
            ALGORITHM = "HS256"
        
        try:
            from shared.utils.config import get_settings
            settings = get_settings()
            CONFIG_SECRET_KEY = str(settings.JWT_SECRET_KEY.get_secret_value())
            logger.info(f"DEBUG: From config - SECRET_KEY: {CONFIG_SECRET_KEY[:10]}...")
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            CONFIG_SECRET_KEY = None
        
        # Use the config version as it's more direct
        SECRET_KEY = CONFIG_SECRET_KEY or AUTH_SECRET_KEY
        
        # Clean token (same logic as WebSocket handler)
        decoded_token = urllib.parse.unquote(token)
        cleaned_token = decoded_token.strip('"').replace("Bearer ", "").strip()
        
        logger.info(f"DEBUG: Using SECRET_KEY: {SECRET_KEY[:10]}...")
        logger.info(f"DEBUG: Using ALGORITHM: {ALGORITHM}")
        logger.info(f"DEBUG: Raw token: {token[:50]}...")
        logger.info(f"DEBUG: Cleaned token: {cleaned_token[:50]}...")
        
        # Validate JWT
        logger.debug(f"Decoding token with SECRET_KEY: {SECRET_KEY[:10]}..., ALGORITHM: {ALGORITHM}")
        logger.debug(f"Token length: {len(cleaned_token)}")
        
        payload = jwt.decode(
            cleaned_token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False
            },
            leeway=60
        )
        
        # Extract user info (same logic as WebSocket handler)
        user_email = None
        user_id = None
        
        if "email" in payload and "sub" in payload:
            try:
                sub_value = payload.get("sub")
                if isinstance(sub_value, int) or (isinstance(sub_value, str) and sub_value.isdigit()):
                    user_id = int(sub_value)
                    user_email = payload.get("email")
            except (ValueError, TypeError, AttributeError):
                pass
        
        if not user_email:
            sub_value = payload.get("sub")
            if sub_value and "@" in str(sub_value):
                user_email = sub_value
                user_id = payload.get("id")
        
        # Get user from database
        from shared.utils.database_setup import get_db
        from api.auth import get_user_by_email
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            user = get_user_by_email(db, email=user_email) if user_email else None
        finally:
            db.close()
        
        return {
            "success": True,
            "message": "Token validation successful",
            "token_analysis": {
                "original_length": len(token),
                "cleaned_length": len(cleaned_token),
                "payload_keys": list(payload.keys()),
                "extracted_email": user_email,
                "extracted_user_id": user_id,
                "user_found_in_db": user is not None,
                "user_active": user.is_active if user else None
            },
            "jwt_payload": payload,
            "user_info": {
                "id": user.id if user else None,
                "email": user.email if user else None,
                "is_active": user.is_active if user else None
            } if user else None
        }
        
    except jwt.ExpiredSignatureError:
        return {
            "success": False,
            "error": "Token expired",
            "message": "JWT token has expired"
        }
    except jwt.InvalidTokenError as e:
        return {
            "success": False,
            "error": "Invalid token",
            "message": f"JWT validation failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"WebSocket token test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Validation error",
            "message": f"Token validation failed: {str(e)}"
        }

@router.get("/debug/auth/create-test-user")
async def create_test_user(
    email: str = Query(..., description="Email for test user"),
    password: str = Query("test123", description="Password for test user"),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Create a test user for authentication testing.
    Only works in development mode.
    """
    import os
    from shared.database.models import UserRole, UserStatus
    from sqlalchemy import select
    
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=403,
            detail="Test user creation not allowed in production"
        )
    
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return {
                "success": False,
                "error": "User already exists",
                "message": f"User with email {email} already exists",
                "user_id": existing_user.id
            }
        
        # Create new test user
        from api.auth import get_password_hash
        hashed_password = get_password_hash(password)
        
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return {
            "success": True,
            "message": "Test user created successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "role": new_user.role.value,
                "is_active": new_user.is_active
            },
            "login_info": {
                "email": email,
                "password": password,
                "login_endpoint": "/api/v1/auth/jwt/login-form"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create test user: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create test user: {str(e)}"
        )

@router.post("/debug/auth/login-test")
async def login_test_user(
    email: str = Query(..., description="Email"),
    password: str = Query(..., description="Password")
) -> Dict[str, Any]:
    """
    Test login endpoint that returns detailed token information.
    """
    try:
        from shared.utils.database_setup import get_db
        from api.auth import verify_password, get_user_by_email, create_access_token
        
        # Get user from database
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            user = get_user_by_email(db, email=email)
            
            if not user or not verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail="User account is inactive"
                )
            
            # Create access token
            access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value})
            
            # Decode token to show payload
            import jwt
            from api.auth import SECRET_KEY, ALGORITHM
            
            decoded_payload = jwt.decode(
                access_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False}  # Don't verify expiration for debugging
            )
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role.value,
                    "is_active": user.is_active
                },
                "token_info": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "payload": decoded_payload
                },
                "usage": {
                    "websocket_query": f"?token={access_token}",
                    "websocket_subprotocol": f"Bearer.{access_token}",
                    "authorization_header": f"Bearer {access_token}"
                }
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Login test failed: {str(e)}"
        )