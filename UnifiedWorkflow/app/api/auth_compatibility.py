"""
Authentication compatibility layer to handle transition between auth systems.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.auth_middleware_service import auth_middleware_service
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.database.models import User
from api.auth import SECRET_KEY, ALGORITHM
import jwt

logger = logging.getLogger(__name__)


async def get_user_from_legacy_token(request: Request, db: AsyncSession) -> Optional[User]:
    """
    Fallback function to handle legacy JWT tokens during transition period.
    """
    try:
        # Extract token from request
        token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif "access_token" in request.cookies:
            token = request.cookies["access_token"]
        
        if not token:
            return None
        
        # Try to decode with legacy method
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Handle both old and new token formats
        user_id = payload.get("id")
        user_email = None
        
        if not user_id:
            # Try 'sub' field - could be user_id (int/str) or email (str)
            sub_field = payload.get("sub")
            if isinstance(sub_field, str):
                # First try to parse as user_id (enhanced format)
                try:
                    user_id = int(sub_field)
                except ValueError:
                    # 'sub' is email string (legacy format) - get user by email
                    user_email = sub_field
                    logger.info(f"Legacy token format detected with sub='{user_email}'")
            elif isinstance(sub_field, int):
                user_id = sub_field
        
        # If we have neither user_id nor user_email, token is invalid
        if not user_id and not user_email:
            return None
        
        # Check activity timeout for newer tokens
        from api.auth import is_token_activity_expired
        if is_token_activity_expired(payload):
            logger.info(f"Token activity expired for user {user_id or user_email}")
            return None
        
        # Get user from database
        from sqlalchemy import select
        if user_id:
            # Get by user_id (enhanced/converted format)
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        else:
            # Get by email (legacy format)
            result = await db.execute(select(User).where(User.email == user_email))
            user = result.scalar_one_or_none()
        
        if user and user.is_active:
            logger.info(f"Successfully authenticated user {user.id} ({user.email}) with legacy token")
            return user
        
        return None
        
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.debug(f"Legacy token validation failed: {str(e)}")
        return None


async def enhanced_get_current_user(request: Request, db: AsyncSession) -> User:
    """
    Enhanced authentication function that tries both enhanced and legacy systems.
    Prioritizes legacy token validation since that's what the login creates.
    """
    # First try legacy/simple token validation (what the login creates)
    user = await get_user_from_legacy_token(request, db)
    if user:
        logger.info(f"Successfully authenticated user {user.id} with simple JWT token")
        return user
    
    try:
        # Fallback to enhanced authentication system
        auth_context = await auth_middleware_service.authenticate_request(
            request=request,
            session=db,
            required_scopes=["read"]
        )
        
        if (auth_context.user_id and 
            auth_context.auth_state.value == "authenticated"):
            
            # Get user from database
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == auth_context.user_id))
            user = result.scalar_one_or_none()
            
            if user and user.is_active:
                logger.info(f"Enhanced authentication successful for user {user.id}")
                return user
        
    except Exception as e:
        logger.debug(f"Enhanced authentication failed: {str(e)}")
    
    # If both methods fail, raise authentication error
    logger.warning("Both simple and enhanced authentication failed")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def initialize_auth_services():
    """
    Initialize authentication services at startup.
    """
    try:
        await auth_middleware_service.initialize()
        logger.info("Authentication services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize authentication services: {str(e)}")
        # Don't fail startup, just log the error