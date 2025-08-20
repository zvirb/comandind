"""Two-Factor Authentication Setup and Management Router.

This router provides comprehensive 2FA management endpoints including:
- TOTP setup with QR code generation
- WebAuthn/FIDO2 passkey registration
- SMS and Email 2FA configuration
- Backup codes generation and management
- Method management and preferences
- Administrative override capabilities
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_async_session
from shared.services.enhanced_2fa_service import enhanced_2fa_service
from shared.services.security_audit_service import security_audit_service
from shared.database.models import User, UserRole
from shared.schemas.two_factor_schemas import (
    # Status and info schemas
    TwoFactorStatusResponse,
    
    # TOTP schemas
    TOTPSetupRequest, TOTPSetupResponse,
    TOTPVerificationRequest, TOTPVerificationResponse,
    
    # WebAuthn schemas
    PasskeySetupRequest, PasskeySetupResponse,
    PasskeyRegistrationRequest, PasskeyRegistrationResponse,
    PasskeyListResponse,
    
    # SMS and Email schemas
    SMSSetupRequest, SMSSetupResponse, SMSVerificationRequest,
    EmailSetupRequest, EmailSetupResponse, EmailVerificationRequest,
    
    # Challenge and verification schemas
    TwoFactorChallengeRequest, TwoFactorChallengeResponse,
    TwoFactorVerificationRequest, TwoFactorVerificationResponse,
    
    # Management schemas
    BackupCodesGenerationResponse,
    MethodDisableRequest, MethodDisableResponse,
    TrustedDeviceRequest, TrustedDeviceResponse, DeviceListResponse,
    TwoFactorSettingsRequest, TwoFactorSettingsResponse,
    
    # Admin schemas
    AdminTwoFactorStatusResponse, AdminOverrideRequest, AdminOverrideResponse,
    ComplianceReportRequest, ComplianceReportResponse,
    
    # Error schemas
    TwoFactorErrorResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/2fa", tags=["Two-Factor Authentication"])


# Import dependencies from enhanced_auth_router
from .enhanced_auth_router import get_current_user, require_2fa_verification


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get user's current 2FA status and configuration."""
    try:
        status_data = await enhanced_2fa_service.get_user_2fa_status(user.id, session)
        return TwoFactorStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"Error getting 2FA status for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get 2FA status"
        )


# TOTP Setup and Management
@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    request: TOTPSetupRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Setup TOTP (Time-based One-Time Password) authentication."""
    try:
        setup_data = await enhanced_2fa_service.setup_totp(
            user_id=user.id,
            user_email=user.email,
            session=session
        )
        
        return TOTPSetupResponse(
            qr_code=setup_data["qr_code"],
            secret=setup_data["secret"],
            backup_codes=setup_data["backup_codes"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting up TOTP for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup TOTP"
        )


@router.post("/totp/verify", response_model=TOTPVerificationResponse)
async def verify_totp_setup(
    request: TOTPVerificationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Verify TOTP code and enable TOTP authentication."""
    try:
        is_verified = await enhanced_2fa_service.verify_and_enable_totp(
            user_id=user.id,
            totp_code=request.code,
            session=session
        )
        
        return TOTPVerificationResponse(
            verified=is_verified,
            enabled=is_verified,
            message="TOTP authentication enabled successfully" if is_verified else "Invalid TOTP code"
        )
        
    except Exception as e:
        logger.error(f"Error verifying TOTP for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify TOTP"
        )


# WebAuthn/Passkey Setup and Management
@router.post("/passkey/setup", response_model=PasskeySetupResponse)
async def setup_passkey(
    request: PasskeySetupRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Start WebAuthn/passkey registration process."""
    try:
        setup_data = await enhanced_2fa_service.setup_webauthn_registration(
            user_id=user.id,
            user_email=user.email,
            session=session
        )
        
        return PasskeySetupResponse(
            registration_options=setup_data["registration_options"],
            session_token=setup_data["session_token"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting up passkey for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup passkey"
        )


@router.post("/passkey/register", response_model=PasskeyRegistrationResponse)
async def register_passkey(
    request: PasskeyRegistrationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Complete WebAuthn/passkey registration."""
    try:
        is_registered = await enhanced_2fa_service.complete_webauthn_registration(
            user_id=user.id,
            session_token=request.session_token,
            credential_data=request.credential_data,
            credential_name=request.credential_name,
            session=session
        )
        
        return PasskeyRegistrationResponse(
            registered=is_registered,
            credential_id=request.credential_data.get("id") if is_registered else None,
            message="Passkey registered successfully" if is_registered else "Passkey registration failed"
        )
        
    except Exception as e:
        logger.error(f"Error registering passkey for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register passkey"
        )


@router.get("/passkeys", response_model=PasskeyListResponse)
async def list_passkeys(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's registered passkeys."""
    try:
        from sqlalchemy import select
        from shared.database.models.auth_models import PasskeyCredential
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="two_factor_setup_router"
        )
        
        # Get user's passkeys
        result = await session.execute(
            select(PasskeyCredential).where(
                PasskeyCredential.user_id == user.id,
                PasskeyCredential.is_active == True
            )
        )
        passkeys = result.scalars().all()
        
        passkey_list = [
            {
                "id": pk.credential_id,
                "name": pk.name,
                "registered_at": pk.registered_at.isoformat(),
                "last_used_at": pk.last_used_at.isoformat() if pk.last_used_at else None,
                "authenticator_type": pk.authenticator_type
            }
            for pk in passkeys
        ]
        
        return PasskeyListResponse(passkeys=passkey_list)
        
    except Exception as e:
        logger.error(f"Error listing passkeys for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list passkeys"
        )


# SMS 2FA Setup (placeholder for future implementation)
@router.post("/sms/setup", response_model=SMSSetupResponse)
async def setup_sms_2fa(
    request: SMSSetupRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Setup SMS-based 2FA (placeholder implementation)."""
    try:
        # This is a placeholder - in production, integrate with SMS provider
        return SMSSetupResponse(
            setup_complete=True,
            phone_number_masked=f"***-***-{request.phone_number[-4:]}",
            verification_required=True
        )
        
    except Exception as e:
        logger.error(f"Error setting up SMS 2FA for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup SMS 2FA"
        )


# Email 2FA Setup (placeholder for future implementation)
@router.post("/email/setup", response_model=EmailSetupResponse)
async def setup_email_2fa(
    request: EmailSetupRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Setup Email-based 2FA (placeholder implementation)."""
    try:
        # This is a placeholder - in production, integrate with email provider
        email_parts = request.email_address.split("@")
        masked_email = f"{email_parts[0][:2]}***@{email_parts[1]}"
        
        return EmailSetupResponse(
            setup_complete=True,
            email_masked=masked_email,
            verification_required=True
        )
        
    except Exception as e:
        logger.error(f"Error setting up Email 2FA for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup Email 2FA"
        )


# Backup Codes Management
@router.post("/backup-codes/generate", response_model=BackupCodesGenerationResponse)
async def generate_backup_codes(
    user: User = Depends(require_2fa_verification),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate new backup codes for emergency access."""
    try:
        backup_codes = await enhanced_2fa_service.generate_new_backup_codes(
            user_id=user.id,
            session=session
        )
        
        return BackupCodesGenerationResponse(
            backup_codes=backup_codes,
            generated_at=datetime.now(timezone.utc),
            message="Store these codes securely. Each can only be used once."
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating backup codes for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate backup codes"
        )


# Method Management
@router.post("/method/disable", response_model=MethodDisableResponse)
async def disable_2fa_method(
    request: MethodDisableRequest,
    user: User = Depends(require_2fa_verification),
    session: AsyncSession = Depends(get_async_session)
):
    """Disable a specific 2FA method."""
    try:
        is_disabled = await enhanced_2fa_service.disable_2fa_method(
            user_id=user.id,
            method=request.method,
            session=session
        )
        
        if is_disabled:
            # Get remaining methods
            status_data = await enhanced_2fa_service.get_user_2fa_status(user.id, session)
            remaining_methods = [
                method for method, enabled in status_data["methods_enabled"].items() 
                if enabled
            ]
            
            return MethodDisableResponse(
                disabled=True,
                method=request.method,
                remaining_methods=remaining_methods,
                message=f"{request.method.upper()} authentication disabled successfully"
            )
        else:
            return MethodDisableResponse(
                disabled=False,
                method=request.method,
                remaining_methods=[],
                message="Failed to disable method"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error disabling 2FA method for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA method"
        )


# Device Management
@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's registered devices."""
    try:
        from sqlalchemy import select
        from shared.database.models.auth_models import RegisteredDevice
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="two_factor_setup_router"
        )
        
        # Get user's devices
        result = await session.execute(
            select(RegisteredDevice).where(
                RegisteredDevice.user_id == user.id,
                RegisteredDevice.is_active == True
            )
        )
        devices = result.scalars().all()
        
        device_list = [
            {
                "id": str(device.id),
                "name": device.device_name,
                "device_type": device.device_type.value,
                "is_trusted": device.is_trusted,
                "last_seen_at": device.last_seen_at.isoformat(),
                "location": device.location_info.get("city", "Unknown") if device.location_info else "Unknown"
            }
            for device in devices
        ]
        
        return DeviceListResponse(devices=device_list)
        
    except Exception as e:
        logger.error(f"Error listing devices for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list devices"
        )


@router.post("/device/trust", response_model=TrustedDeviceResponse)
async def trust_device(
    request: TrustedDeviceRequest,
    http_request: Request,
    user: User = Depends(require_2fa_verification),
    session: AsyncSession = Depends(get_async_session)
):
    """Mark current device as trusted."""
    try:
        from sqlalchemy import select, update
        from shared.database.models.auth_models import RegisteredDevice
        from datetime import timedelta
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="two_factor_setup_router"
        )
        
        # Get current device (simplified - would need proper device identification)
        user_agent = http_request.headers.get("user-agent", "")
        result = await session.execute(
            select(RegisteredDevice).where(
                RegisteredDevice.user_id == user.id,
                RegisteredDevice.user_agent == user_agent
            ).limit(1)
        )
        device = result.scalar_one_or_none()
        
        if device:
            device.is_trusted = True
            device.device_name = request.device_name
            device.remember_expires_at = datetime.now(timezone.utc) + timedelta(days=request.remember_duration_days)
            
            await session.commit()
            
            return TrustedDeviceResponse(
                device_id=str(device.id),
                trusted=True,
                expires_at=device.remember_expires_at,
                message="Device marked as trusted"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
    except Exception as e:
        logger.error(f"Error trusting device for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trust device"
        )


# Settings and Preferences
@router.get("/settings", response_model=TwoFactorSettingsResponse)
async def get_2fa_settings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get user's 2FA settings and preferences."""
    try:
        from sqlalchemy import select
        from shared.database.models.enhanced_2fa_models import UserTwoFactorSettings
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="two_factor_setup_router"
        )
        
        # Get user settings
        result = await session.execute(
            select(UserTwoFactorSettings).where(UserTwoFactorSettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            return TwoFactorSettingsResponse(
                preferred_method=settings.preferred_method,
                fallback_method=settings.fallback_method,
                remember_device_preference=settings.remember_device_preference,
                notify_on_new_device=settings.notify_on_new_device,
                notify_on_failed_attempt=settings.notify_on_failed_attempt,
                notification_email=settings.notification_email,
                require_2fa_for_sensitive_actions=settings.require_2fa_for_sensitive_actions,
                auto_logout_minutes=settings.auto_logout_minutes,
                setup_completed_at=settings.setup_completed_at,
                last_method_change=settings.last_method_change
            )
        else:
            # Return default settings
            return TwoFactorSettingsResponse(
                preferred_method=None,
                fallback_method=None,
                remember_device_preference=True,
                notify_on_new_device=True,
                notify_on_failed_attempt=True,
                notification_email=None,
                require_2fa_for_sensitive_actions=False,
                auto_logout_minutes=None,
                setup_completed_at=None,
                last_method_change=None
            )
        
    except Exception as e:
        logger.error(f"Error getting 2FA settings for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get 2FA settings"
        )


@router.post("/settings", response_model=TwoFactorSettingsResponse)
async def update_2fa_settings(
    request: TwoFactorSettingsRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update user's 2FA settings and preferences."""
    try:
        from sqlalchemy import select
        from shared.database.models.enhanced_2fa_models import UserTwoFactorSettings
        
        # Set security context
        await security_audit_service.set_security_context(
            session=session, user_id=user.id, service_name="two_factor_setup_router"
        )
        
        # Get or create user settings
        result = await session.execute(
            select(UserTwoFactorSettings).where(UserTwoFactorSettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = UserTwoFactorSettings(user_id=user.id)
            session.add(settings)
        
        # Update settings
        update_data = request.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.last_method_change = datetime.now(timezone.utc)
        
        await session.commit()
        
        # Return updated settings
        return TwoFactorSettingsResponse(
            preferred_method=settings.preferred_method,
            fallback_method=settings.fallback_method,
            remember_device_preference=settings.remember_device_preference,
            notify_on_new_device=settings.notify_on_new_device,
            notify_on_failed_attempt=settings.notify_on_failed_attempt,
            notification_email=settings.notification_email,
            require_2fa_for_sensitive_actions=settings.require_2fa_for_sensitive_actions,
            auto_logout_minutes=settings.auto_logout_minutes,
            setup_completed_at=settings.setup_completed_at,
            last_method_change=settings.last_method_change
        )
        
    except Exception as e:
        logger.error(f"Error updating 2FA settings for user {user.id}: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update 2FA settings"
        )


# Administrative Endpoints
@router.get("/admin/users/{user_id}", response_model=AdminTwoFactorStatusResponse)
async def admin_get_user_2fa_status(
    user_id: int,
    admin_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get 2FA status for any user (admin only)."""
    try:
        # Check admin privileges
        if not admin_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # Get target user
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get 2FA status
        status_data = await enhanced_2fa_service.get_user_2fa_status(user_id, session)
        is_required, grace_period_end = await enhanced_2fa_service.is_2fa_required(user_id, session)
        
        return AdminTwoFactorStatusResponse(
            user_id=user_id,
            email=target_user.email,
            is_enabled=status_data["is_enabled"],
            is_required=is_required,
            grace_period_end=grace_period_end,
            methods_enabled=status_data["methods_enabled"],
            last_2fa_use=None,  # Would need to track this
            failed_attempts=0   # Would need to track this
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin 2FA status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user 2FA status"
        )


@router.post("/admin/override", response_model=AdminOverrideResponse)
async def admin_override_2fa(
    request: AdminOverrideRequest,
    admin_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create administrative override for 2FA requirement."""
    try:
        # Check admin privileges
        if not admin_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        if request.override_type == "disable":
            # Disable 2FA for user
            success = await enhanced_2fa_service.admin_disable_user_2fa(
                admin_user_id=admin_user.id,
                target_user_id=request.user_id,
                reason=request.reason,
                session=session
            )
            
            if success:
                override_id = f"admin_disable_{request.user_id}_{datetime.now().timestamp()}"
                return AdminOverrideResponse(
                    override_id=override_id,
                    granted=True,
                    expires_at=datetime.now(timezone.utc),
                    requires_approval=False,
                    message="2FA disabled by administrator"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to disable 2FA"
                )
        else:
            # Other override types would be implemented here
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Override type '{request.override_type}' not yet implemented"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating admin override: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin override"
        )


@router.get("/admin/compliance-report", response_model=ComplianceReportResponse)
async def get_compliance_report(
    request: ComplianceReportRequest = Depends(),
    admin_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate 2FA compliance report (admin only)."""
    try:
        # Check admin privileges
        if not admin_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # This would generate a comprehensive compliance report
        # For now, return a placeholder
        from sqlalchemy import select, func
        
        # Get total user count
        result = await session.execute(select(func.count(User.id)).where(User.is_active == True))
        total_users = result.scalar() or 0
        
        # Get users with 2FA enabled
        from shared.database.models.auth_models import UserTwoFactorAuth
        result = await session.execute(
            select(func.count(UserTwoFactorAuth.user_id)).where(UserTwoFactorAuth.is_enabled == True)
        )
        users_with_2fa = result.scalar() or 0
        
        compliance_percentage = (users_with_2fa / total_users * 100) if total_users > 0 else 0
        
        return ComplianceReportResponse(
            report_id=f"compliance_{datetime.now().timestamp()}",
            generated_at=datetime.now(timezone.utc),
            period_start=request.period_start or datetime.now(timezone.utc) - timedelta(days=30),
            period_end=request.period_end or datetime.now(timezone.utc),
            total_users=total_users,
            users_with_2fa=users_with_2fa,
            compliance_percentage=compliance_percentage,
            users_in_grace_period=0,  # Would calculate this
            users_overdue=0,          # Would calculate this
            method_usage={"totp": users_with_2fa, "passkey": 0, "sms": 0, "email": 0},
            failed_attempts=0,
            admin_overrides=0,
            user_details=None,
            recommendations=[
                "Encourage users to set up multiple 2FA methods",
                "Consider mandatory 2FA for all users",
                "Provide 2FA setup assistance for users"
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )