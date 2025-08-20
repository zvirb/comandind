"""Enhanced Authentication Router with Mandatory 2FA Support.

This router handles the complete authentication flow including:
- Username/password authentication
- Mandatory 2FA enforcement with grace periods
- Multi-method 2FA verification (TOTP, WebAuthn, SMS, Email)
- Device management and trusted device handling
- Session management with 2FA verification status
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
import jwt

from api.auth import (
    authenticate_user, authenticate_user_async, create_access_token, create_refresh_token,
    set_auth_cookies, unset_auth_cookies, get_password_hash
)
from shared.database.models import User, UserStatus, UserRole
from shared.database.models.auth_models import RegisteredDevice, DeviceSecurityLevel, DeviceType
from shared.utils.database_setup import get_async_session, get_db
from shared.utils.config import get_settings
from shared.services.enhanced_2fa_service import enhanced_2fa_service
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.schemas.two_factor_schemas import (
    TwoFactorStatusResponse, TwoFactorChallengeRequest, TwoFactorChallengeResponse,
    TwoFactorVerificationRequest, TwoFactorVerificationResponse
)
from api.middleware.evidence_collection_middleware import create_authentication_evidence

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Enhanced Authentication"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


# Request/Response schemas for enhanced auth
from pydantic import BaseModel, EmailStr, Field


class EnhancedLoginRequest(BaseModel):
    """Enhanced login request with device identification."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    device_name: Optional[str] = Field(None, description="User-friendly device name")
    remember_device: bool = Field(False, description="Whether to remember this device")


class EnhancedLoginResponse(BaseModel):
    """Enhanced login response with 2FA status."""
    access_token: Optional[str] = Field(None, description="JWT access token if login complete")
    token_type: str = Field("bearer", description="Token type")
    user_id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    
    # 2FA status
    requires_2fa: bool = Field(..., description="Whether 2FA is required")
    tfa_status: Optional[TwoFactorStatusResponse] = Field(None, description="Current 2FA status")
    grace_period_end: Optional[datetime] = Field(None, description="Grace period end date")
    
    # Device status
    device_id: Optional[str] = Field(None, description="Registered device ID")
    is_trusted_device: bool = Field(False, description="Whether device is trusted")
    
    # Session info
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="Status message for user")


class RegistrationRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    device_name: Optional[str] = Field(None, description="User-friendly device name")


class EnhancedLoginResponse(BaseModel):
    """Enhanced login response with evidence."""
    access_token: str = Field(..., description="JWT access token")
    user_id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    requires_2fa: bool = Field(..., description="Whether 2FA is required")
    tfa_status: TwoFactorStatusResponse = Field(..., description="2FA status details")
    grace_period_end: Optional[datetime] = Field(None, description="2FA setup grace period end")
    device_id: str = Field(..., description="Device ID")
    is_trusted_device: bool = Field(..., description="Whether device is trusted")
    session_id: str = Field(..., description="Session ID")
    message: str = Field(..., description="Login status message")
    evidence: Optional[Dict[str, Any]] = Field(None, description="Authentication evidence")


class RegistrationResponse(BaseModel):
    """User registration response."""
    user_id: int = Field(..., description="New user ID")
    email: str = Field(..., description="User email")
    requires_2fa_setup: bool = Field(..., description="Whether 2FA setup is required")
    grace_period_end: Optional[datetime] = Field(None, description="2FA setup grace period end")
    message: str = Field(..., description="Registration status message")


class DeviceFingerprint(BaseModel):
    """Device fingerprint for device identification."""
    user_agent: str = Field(..., description="Browser user agent")
    screen_resolution: Optional[str] = Field(None, description="Screen resolution")
    timezone: Optional[str] = Field(None, description="User timezone")
    language: Optional[str] = Field(None, description="Browser language")
    platform: Optional[str] = Field(None, description="Operating system")


def generate_device_fingerprint(request: Request, device_data: Optional[DeviceFingerprint] = None) -> str:
    """Generate a device fingerprint from request data."""
    import hashlib
    
    # Basic fingerprint from request headers
    user_agent = request.headers.get("user-agent", "unknown")
    accept_language = request.headers.get("accept-language", "unknown")
    accept_encoding = request.headers.get("accept-encoding", "unknown")
    
    # Additional data if provided
    if device_data:
        fingerprint_data = f"{user_agent}|{device_data.screen_resolution}|{device_data.timezone}|{device_data.language}|{device_data.platform}"
    else:
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"
    
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def detect_device_type(user_agent: str) -> DeviceType:
    """Detect device type from user agent."""
    user_agent_lower = user_agent.lower()
    
    if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone"]):
        return DeviceType.MOBILE
    elif any(tablet in user_agent_lower for tablet in ["tablet", "ipad"]):
        return DeviceType.TABLET
    elif any(desktop in user_agent_lower for desktop in ["windows", "mac", "linux", "x11"]):
        return DeviceType.DESKTOP
    else:
        return DeviceType.UNKNOWN


async def get_or_create_device(
    session: AsyncSession,
    user_id: int,
    request: Request,
    device_name: Optional[str] = None,
    device_data: Optional[DeviceFingerprint] = None
) -> RegisteredDevice:
    """Get existing device or create new one."""
    
    # Generate device fingerprint
    fingerprint = generate_device_fingerprint(request, device_data)
    
    # Check for existing device
    result = await session.execute(
        select(RegisteredDevice).where(
            RegisteredDevice.user_id == user_id,
            RegisteredDevice.device_fingerprint == fingerprint
        )
    )
    device = result.scalar_one_or_none()
    
    if device:
        # Update last seen
        device.last_seen_at = datetime.now(timezone.utc)
        device.last_ip_address = request.client.host if request.client else None
        return device
    
    # Create new device
    user_agent = request.headers.get("user-agent", "Unknown Device")
    device_type = detect_device_type(user_agent)
    
    device = RegisteredDevice(
        user_id=user_id,
        device_name=device_name or f"{device_type.value.title()} Device",
        device_fingerprint=fingerprint,
        user_agent=user_agent,
        device_type=device_type,
        security_level=DeviceSecurityLevel.ALWAYS_LOGIN,
        last_ip_address=request.client.host if request.client else None,
        is_active=True,
        is_trusted=False
    )
    
    session.add(device)
    await session.flush()  # Get device ID
    
    return device


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Get current authenticated user with 2FA verification status."""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    try:
        # Decode and validate JWT token
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET_KEY.get_secret_value(), 
            algorithms=["HS256"]
        )
        
        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from database
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        
        return user
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/register", response_model=RegistrationResponse)
async def register_user(
    request: RegistrationRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Register a new user with mandatory 2FA onboarding."""
    try:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create new user
        hashed_password = get_password_hash(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        
        session.add(new_user)
        await session.flush()  # Get user ID
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=new_user.id, service_name="enhanced_auth_router"
        )
        
        # Create device record
        device = await get_or_create_device(
            session=session,
            user_id=new_user.id,
            request=http_request,
            device_name=request.device_name
        )
        
        # Check 2FA requirements
        is_required, grace_period_end = await enhanced_2fa_service.is_2fa_required(new_user.id, session)
        
        await session.commit()
        
        # Log registration
        await security_audit_service.log_security_event(
            session=session,
            user_id=new_user.id,
            event_type="user_registration",
            details={
                "email": request.email,
                "device_id": str(device.id),
                "requires_2fa": is_required
            },
            severity="INFO"
        )
        
        return RegistrationResponse(
            user_id=new_user.id,
            email=new_user.email,
            requires_2fa_setup=is_required,
            grace_period_end=grace_period_end,
            message="Registration successful. Please set up two-factor authentication." if is_required else "Registration successful."
        )
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/jwt/login", response_model=EnhancedLoginResponse)
async def enhanced_login(
    request: EnhancedLoginRequest,
    response: Response,
    http_request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """Enhanced login with mandatory 2FA enforcement."""
    session_id = None
    
    try:
        # Create session ID for tracking
        import secrets
        session_id = secrets.token_urlsafe(32)
        
        # Authenticate user credentials using async session
        user = await authenticate_user_async(session, request.email, request.password)
        
        if not user:
            # Log failed login attempt
            await security_audit_service.log_security_event(
                session=session,
                user_id=None,
                event_type="login_failed_invalid_credentials",
                details={
                    "email": request.email,
                    "ip_address": http_request.client.host if http_request.client else None
                },
                severity="WARNING"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check user status
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active"
            )
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="enhanced_auth_router"
        )
        
        # Get or create device record
        device = await get_or_create_device(
            session=session,
            user_id=user.id,
            request=http_request,
            device_name=request.device_name
        )
        
        # Get 2FA status
        tfa_status = await enhanced_2fa_service.get_user_2fa_status(user.id, session)
        is_required, grace_period_end = await enhanced_2fa_service.is_2fa_required(user.id, session)
        
        # Check if device is trusted and can skip 2FA
        is_trusted_device = (
            device.is_trusted and 
            device.remember_expires_at and 
            device.remember_expires_at > datetime.now(timezone.utc)
        )
        
        # Determine if 2FA is needed for this login
        requires_2fa_now = (
            tfa_status["is_enabled"] and 
            not is_trusted_device and
            device.security_level != DeviceSecurityLevel.AUTO_LOGIN
        )
        
        # If 2FA is required but not enabled and grace period expired, force 2FA setup
        if is_required and not tfa_status["is_enabled"] and not grace_period_end:
            await session.commit()
            
            return EnhancedLoginResponse(
                user_id=user.id,
                email=user.email,
                requires_2fa=True,
                tfa_status=TwoFactorStatusResponse(**tfa_status),
                device_id=str(device.id),
                is_trusted_device=is_trusted_device,
                session_id=session_id,
                message="Two-factor authentication setup is required to continue."
            )
        
        # If 2FA verification is needed
        if requires_2fa_now:
            await session.commit()
            
            return EnhancedLoginResponse(
                user_id=user.id,
                email=user.email,
                requires_2fa=True,
                tfa_status=TwoFactorStatusResponse(**tfa_status),
                grace_period_end=grace_period_end,
                device_id=str(device.id),
                is_trusted_device=is_trusted_device,
                session_id=session_id,
                message="Two-factor authentication required."
            )
        
        # Complete login - create tokens using enhanced JWT service
        try:
            # Set security context before creating tokens
            await security_audit_service.set_security_context(
                session=session, user_id=user.id, service_name="enhanced_auth_router"
            )
            
            # Create access token using enhanced JWT service
            token_result = await enhanced_jwt_service.create_access_token(
                session=session,
                user_id=user.id,
                scopes=["read", "write"],
                session_id=session_id,
                device_fingerprint=device.device_fingerprint,
                ip_address=http_request.client.host if http_request.client else None
            )
            
            access_token = token_result["access_token"]
            
            # Create refresh token using enhanced JWT service as a service token
            refresh_token_result = await enhanced_jwt_service.create_service_token(
                session=session,
                user_id=user.id,
                source_service="webui",
                target_service="api",
                permissions={"refresh": True, "user_token": True},
                scope=["refresh_token"],
                expires_hours=24 * 7  # 7 days
            )
            
            refresh_token = refresh_token_result["service_token"]
            
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            # Fallback to legacy token creation if enhanced service fails
            token_data = {
                "sub": str(user.id),  # User ID as string for consistency
                "email": user.email,  # Include email for reference
                "id": user.id,  # Keep numeric ID for backward compatibility
                "role": user.role.value,
                "session_id": session_id,
                "device_id": str(device.id),
                "tfa_verified": not requires_2fa_now
            }
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
        
        # Set auth cookies
        set_auth_cookies(response, access_token, refresh_token)
        
        # Handle device trust
        if request.remember_device and tfa_status["is_enabled"]:
            device.is_trusted = True
            device.remember_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        
        await session.commit()
        
        # Log successful login
        await security_audit_service.log_security_event(
            session=session,
            user_id=user.id,
            event_type="login_success",
            details={
                "device_id": str(device.id),
                "trusted_device": is_trusted_device,
                "tfa_required": requires_2fa_now,
                "session_id": session_id
            },
            severity="INFO"
        )
        
        # Generate authentication evidence
        auth_evidence = create_authentication_evidence(
            user_id=str(user.id),
            method="enhanced_jwt_login",
            success=True,
            additional_details={
                "device_id": str(device.id),
                "trusted_device": is_trusted_device,
                "tfa_verified": not requires_2fa_now,
                "session_id": session_id,
                "device_type": device.device_type.value,
                "security_level": device.security_level.value,
                "auth_flow": "enhanced_login_flow"
            }
        )
        
        return EnhancedLoginResponse(
            access_token=access_token,
            user_id=user.id,
            email=user.email,
            requires_2fa=False,
            tfa_status=TwoFactorStatusResponse(**tfa_status),
            grace_period_end=grace_period_end,
            device_id=str(device.id),
            is_trusted_device=is_trusted_device,
            session_id=session_id,
            message="Login successful.",
            evidence=auth_evidence
        )
        
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/2fa/challenge", response_model=TwoFactorChallengeResponse)
async def start_2fa_challenge(
    request: TwoFactorChallengeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Start a 2FA challenge for the authenticated user."""
    try:
        challenge_data = await enhanced_2fa_service.start_2fa_challenge(
            user_id=user.id,
            method=request.method,
            session=session
        )
        
        return TwoFactorChallengeResponse(
            method=challenge_data["method"],
            session_token=challenge_data["session_token"],
            challenge_data=challenge_data.get("authentication_options"),
            message=challenge_data["message"],
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA challenge error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start 2FA challenge"
        )


@router.post("/2fa/verify", response_model=TwoFactorVerificationResponse)
async def verify_2fa_challenge(
    request: TwoFactorVerificationRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Verify a 2FA challenge and complete authentication."""
    try:
        is_verified = await enhanced_2fa_service.verify_2fa_challenge(
            user_id=user.id,
            session_token=request.session_token,
            response_data=request.response_data,
            session=session
        )
        
        if is_verified:
            # Update session with 2FA verification
            # Create new token with 2FA verified status using enhanced JWT service
            try:
                # Set security context
                await security_audit_service.set_security_context(
                    session=session, user_id=user.id, service_name="enhanced_auth_router"
                )
                
                # Create access token with 2FA verified
                token_result = await enhanced_jwt_service.create_access_token(
                    session=session,
                    user_id=user.id,
                    scopes=["read", "write", "2fa_verified"],
                    session_id=request.session_token,
                    ip_address=None  # Not available in this context
                )
                
                access_token = token_result["access_token"]
                
                # Create refresh token
                refresh_token_result = await enhanced_jwt_service.create_service_token(
                    session=session,
                    user_id=user.id,
                    source_service="webui",
                    target_service="api",
                    permissions={"refresh": True, "user_token": True, "tfa_verified": True},
                    scope=["refresh_token", "2fa_verified"],
                    expires_hours=24 * 7  # 7 days
                )
                
                refresh_token = refresh_token_result["service_token"]
                
            except Exception as e:
                logger.error(f"Enhanced token creation failed, using fallback: {e}")
                # Fallback to legacy token creation
                token_data = {
                    "sub": user.email,
                    "id": user.id,
                    "role": user.role.value,
                    "tfa_verified": True
                }
                access_token = create_access_token(token_data)
                refresh_token = create_refresh_token(token_data)
            
            set_auth_cookies(response, access_token, refresh_token)
            
            return TwoFactorVerificationResponse(
                verified=True,
                method_used=request.response_data.get("method", "unknown"),
                message="Two-factor authentication successful",
                access_token=access_token
            )
        else:
            return TwoFactorVerificationResponse(
                verified=False,
                method_used=request.response_data.get("method", "unknown"),
                message="Two-factor authentication failed"
            )
            
    except Exception as e:
        logger.error(f"2FA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA verification failed"
        )


@router.post("/logout")
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Logout user and clear authentication cookies."""
    try:
        # Clear auth cookies
        unset_auth_cookies(response)
        
        # Log logout
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="enhanced_auth_router"
        )
        
        await security_audit_service.log_security_event(
            session=session,
            user_id=user.id,
            event_type="user_logout",
            details={},
            severity="INFO"
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


async def require_2fa_verification(
    user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Dependency that requires 2FA verification for sensitive operations."""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Decode token to check 2FA verification status
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )
        
        tfa_verified = payload.get("tfa_verified", False)
        
        if not tfa_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Two-factor authentication required for this operation"
            )
        
        return user
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.get("/status")
async def auth_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current authentication and 2FA status."""
    try:
        # Get 2FA status
        tfa_status = await enhanced_2fa_service.get_user_2fa_status(user.id, session)
        is_required, grace_period_end = await enhanced_2fa_service.is_2fa_required(user.id, session)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "is_authenticated": True,
            "tfa_status": tfa_status,
            "tfa_required": is_required,
            "grace_period_end": grace_period_end.isoformat() if grace_period_end else None
        }
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication status"
        )