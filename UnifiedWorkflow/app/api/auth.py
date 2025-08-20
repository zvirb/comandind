"""Authentication utilities for handling users, passwords, and tokens."""

import logging
from datetime import datetime, timedelta, timezone
import secrets # Import secrets module for CSRF token generation
import hmac
import hashlib
import time
from typing import Any, Optional

from fastapi import Response
import jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
 
from shared.database.models import User
from shared.utils.config import get_settings
from shared.services.jwt_consistency_service import jwt_consistency_service

logger = logging.getLogger(__name__)

# --- Configuration ---
settings = get_settings()
# SECURITY FIX: Ensure consistent SECRET_KEY across all auth modules
SECRET_KEY = str(settings.JWT_SECRET_KEY.get_secret_value())
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Standard session duration
REFRESH_TOKEN_EXPIRE_DAYS = 7
CSRF_TOKEN_LENGTH = 32 # Length of the CSRF token in bytes
ACTIVITY_TIMEOUT_MINUTES = 60  # Match token expiration for consistency

# Create hasher with Argon2 (modern, secure algorithm)
from pwdlib.hashers.argon2 import Argon2Hasher

pwd_hasher = PasswordHash([Argon2Hasher()])

# --- Password Hashing ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    return pwd_hasher.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_hasher.hash(password)

# --- CSRF Token Generation ---
def generate_csrf_token() -> str:
    """Generates a CSRF token compatible with EnhancedCSRFMiddleware.
    
    Format: timestamp:nonce:signature (matching middleware expectation)
    This ensures consistency with the validation middleware.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get CSRF secret from settings (matching middleware initialization logic)
    csrf_secret = getattr(settings, 'CSRF_SECRET_KEY', None) or getattr(settings, 'JWT_SECRET_KEY', 'default-csrf-secret-change-in-production')
    if hasattr(csrf_secret, 'get_secret_value'):
        csrf_secret = csrf_secret.get_secret_value()
    secret_key = csrf_secret.encode() if isinstance(csrf_secret, str) else csrf_secret
    
    # Generate token components
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(32)
    
    # Create HMAC signature (matching middleware format)
    message = f"{timestamp}:{nonce}".encode()
    signature = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
    
    # Format: timestamp:nonce:signature
    csrf_token = f"{timestamp}:{nonce}:{signature}"
    
    logger.debug(f"Generated CSRF token with format: {csrf_token[:50]}...")
    return csrf_token

# --- User Authentication and Retrieval ---
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieves a user from the database by email."""
    return db.query(User).filter(User.email == email, User.is_active == True).first()

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticates a user against the database."""
    import logging
    logger = logging.getLogger(__name__)
    
    user = get_user_by_email(db, email)
    if not user:
        logger.warning(f"User not found: {email}")
        return None
    
    logger.info(f"User found: {email}, verifying password...")
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Password verification failed for user: {email}")
        return None
    
    logger.info(f"Authentication successful for user: {email}")
    return user

async def get_user_by_email_async(db: AsyncSession, email: str) -> Optional[User]:
    """Retrieves a user from the database by email (async)."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
    
    result = await db.execute(select(User).filter(User.email == email, User.is_active == True))
    return result.scalars().first()

async def authenticate_user_async(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticates a user against the database (async version)."""
    import logging
    logger = logging.getLogger(__name__)
    
    user = await get_user_by_email_async(db, email)
    if not user:
        logger.warning(f"User not found or inactive: {email}")
        return None
    
    logger.info(f"User found: {email}, verifying password...")
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Password verification failed for user: {email}")
        return None
    
    logger.info(f"Authentication successful for user: {email}")
    return user

# --- Token Creation ---
def create_access_token(data: dict[str, Any]) -> str:
    """Creates a new JWT access token using centralized JWT service.
    
    SECURITY FIX: Uses jwt_consistency_service to ensure consistent SECRET_KEY
    across all authentication modules, fixing Bearer token validation issues.
    """
    try:
        return jwt_consistency_service.create_token(data, ACCESS_TOKEN_EXPIRE_MINUTES)
    except Exception as e:
        logger.error(f"Access token creation failed: {e}")
        # Fallback to original method if centralized service fails
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": now,
            "nbf": now,
        })
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

def create_refresh_token(data: dict[str, Any]) -> str:
    """Creates a new JWT refresh token using centralized JWT service."""
    try:
        return jwt_consistency_service.create_token(data, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
    except Exception as e:
        logger.error(f"Refresh token creation failed: {e}")
        # Fallback to original method
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

def refresh_access_token_activity(token_payload: dict) -> str:
    """Refreshes an access token with updated activity timestamp."""
    # Preserve original user data but update activity timestamps
    user_data = {
        "sub": token_payload.get("sub"),
        "role": token_payload.get("role"),
        "id": token_payload.get("id")
    }
    return create_access_token(user_data)

def is_token_activity_expired(token_payload: dict) -> bool:
    """Check if token has exceeded activity timeout.
    
    Returns False for now - activity timeout should be handled by token refresh,
    not by rejecting valid tokens. The JWT expiration (60 minutes) provides
    sufficient security without abrupt session termination.
    """
    # Activity timeout disabled - causes false session expirations
    # The standard JWT expiration provides adequate security
    # Future: Implement token refresh on activity instead of hard timeout
    return False

# --- Cookie Management (including CSRF) ---
def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Sets secure, HTTP-only authentication cookies in the response."""
    import os
    # Use secure cookies only in production (HTTPS), not for localhost development
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    csrf_token = generate_csrf_token()
    
    # Cookie settings optimized for production (aiwfe.com) and development
    cookie_secure = is_production
    # Use 'lax' for better compatibility with OAuth and form submissions
    cookie_samesite = "lax"
    
    # Set explicit domain for production (aiwfe.com) to enable subdomain sharing
    domain_name = os.getenv('DOMAIN', 'aiwfe.com')
    cookie_domain = f".{domain_name}" if is_production and domain_name not in ['localhost', '127.0.0.1'] else None
    
    response.set_cookie(
        key="access_token",
        value=access_token,  # Just the token without "Bearer" prefix
        httponly=True,  # SECURITY FIX: HttpOnly enabled - use WebSocket bridge for WS auth
        samesite=cookie_samesite,
        secure=cookie_secure, # Only secure in production
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/", # Make cookie accessible across entire domain
        domain=cookie_domain  # Explicit domain for production (aiwfe.com)
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure, # Only secure in production
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/", # Make cookie accessible across entire domain
        domain=cookie_domain  # Explicit domain for production (aiwfe.com)
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False, # IMPORTANT: Must be accessible by frontend JS for double-submit
        samesite=cookie_samesite,
        secure=cookie_secure, # Only secure in production
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, # Match refresh token expiry
        path="/", # Make cookie accessible across entire domain
        domain=cookie_domain  # Explicit domain for production (aiwfe.com)
    )

def unset_auth_cookies(response: Response):
    """Clears authentication cookies from the response to log a user out."""
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    # Use same secure setting as when setting cookies
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    logger.info(f"Unsetting auth cookies - is_production: {is_production}")
    
    # Try multiple deletion approaches to handle domain issues
    # Delete without domain (for exact host match)
    response.delete_cookie("access_token", secure=is_production, samesite="strict", path="/")
    response.delete_cookie("refresh_token", secure=is_production, samesite="strict", path="/")
    response.delete_cookie("csrf_token", secure=is_production, samesite="strict", path="/")
    
    # Also try deleting with domain specified (for subdomain match)
    domain = os.getenv("DOMAIN", "aiwfe.com")
    if domain:
        logger.info(f"Also deleting cookies for domain: {domain}")
        response.delete_cookie("access_token", domain=domain, secure=is_production, samesite="strict", path="/")
        response.delete_cookie("refresh_token", domain=domain, secure=is_production, samesite="strict", path="/")
        response.delete_cookie("csrf_token", domain=domain, secure=is_production, samesite="strict", path="/")
    
    logger.info("Auth cookies deletion commands sent")