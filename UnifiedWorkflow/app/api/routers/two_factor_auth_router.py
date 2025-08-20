"""Two-Factor Authentication router for managing 2FA settings and devices."""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import (
    User, UserTwoFactorAuth, RegisteredDevice, DeviceSecurityLevel, 
    TwoFactorMethod, DeviceType
)
from shared.services.totp_service import totp_service
from shared.services.device_service import device_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class TOTPSetupResponse(BaseModel):
    qr_code: str
    secret: str
    backup_codes: List[str]
    manual_entry_key: str
    issuer: str

class TOTPVerifyRequest(BaseModel):
    token: str

class DeviceResponse(BaseModel):
    id: str
    device_name: str
    device_type: str
    security_level: str
    is_remembered: bool
    is_trusted: bool
    first_seen_at: datetime
    last_seen_at: datetime
    last_ip_address: Optional[str]

class UpdateDeviceRequest(BaseModel):
    device_name: Optional[str] = None
    security_level: Optional[DeviceSecurityLevel] = None

class TwoFactorStatusResponse(BaseModel):
    is_enabled: bool
    default_method: Optional[str]
    totp_enabled: bool
    passkey_enabled: bool
    backup_codes_remaining: int

# TOTP/Google Authenticator endpoints
@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set up TOTP (Google Authenticator) for the current user."""
    try:
        setup_data = totp_service.setup_totp_for_user(db, current_user)
        return TOTPSetupResponse(**setup_data)
    except Exception as e:
        logger.error(f"Error setting up TOTP for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up TOTP"
        )

@router.post("/totp/verify")
async def verify_totp_setup(
    request: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify TOTP token and enable TOTP for the user."""
    try:
        success = totp_service.verify_and_enable_totp(db, current_user, request.token)
        if success:
            return {"message": "TOTP enabled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP token"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying TOTP for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify TOTP"
        )

@router.delete("/totp")
async def disable_totp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable TOTP for the current user."""
    try:
        success = totp_service.disable_totp(db, current_user)
        if success:
            return {"message": "TOTP disabled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TOTP not found or already disabled"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling TOTP for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable TOTP"
        )

@router.post("/totp/backup-codes")
async def regenerate_backup_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate backup codes for TOTP."""
    try:
        backup_codes = totp_service.regenerate_backup_codes(db, current_user)
        if backup_codes:
            return {"backup_codes": backup_codes}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TOTP not enabled"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating backup codes for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )

# 2FA status endpoints
@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current 2FA status for the user."""
    try:
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == current_user.id
        ).first()
        
        if not two_factor_auth:
            return TwoFactorStatusResponse(
                is_enabled=False,
                default_method=None,
                totp_enabled=False,
                passkey_enabled=False,
                backup_codes_remaining=0
            )
        
        # Count remaining backup codes
        backup_codes_remaining = 0
        if two_factor_auth.totp_backup_codes:
            backup_codes_remaining = len(two_factor_auth.totp_backup_codes)
        
        return TwoFactorStatusResponse(
            is_enabled=two_factor_auth.is_enabled,
            default_method=two_factor_auth.default_method.value if two_factor_auth.default_method else None,
            totp_enabled=two_factor_auth.totp_enabled,
            passkey_enabled=two_factor_auth.passkey_enabled,
            backup_codes_remaining=backup_codes_remaining
        )
        
    except Exception as e:
        logger.error(f"Error getting 2FA status for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get 2FA status"
        )

# Device management endpoints
@router.get("/devices", response_model=List[DeviceResponse])
async def get_user_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """Get all devices for the current user."""
    try:
        devices = device_service.get_user_devices(db, current_user, active_only)
        
        return [
            DeviceResponse(
                id=str(device.id),
                device_name=device.device_name,
                device_type=device.device_type.value,
                security_level=device.security_level.value,
                is_remembered=device.is_remembered,
                is_trusted=device.is_trusted,
                first_seen_at=device.first_seen_at,
                last_seen_at=device.last_seen_at,
                last_ip_address=device.last_ip_address
            )
            for device in devices
        ]
        
    except Exception as e:
        logger.error(f"Error getting devices for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get devices"
        )

@router.put("/devices/{device_id}")
async def update_device(
    device_id: str,
    request: UpdateDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update device settings."""
    try:
        device_uuid = uuid.UUID(device_id)
        updated = False
        
        if request.device_name:
            success = device_service.update_device_name(db, current_user, device_uuid, request.device_name)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found"
                )
            updated = True
        
        if request.security_level:
            success = device_service.update_device_security_level(db, current_user, device_uuid, request.security_level)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found"
                )
            updated = True
        
        if updated:
            return {"message": "Device updated successfully"}
        else:
            return {"message": "No changes made"}
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device {device_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device"
        )

@router.post("/devices/{device_id}/trust")
async def trust_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a device as trusted."""
    try:
        device_uuid = uuid.UUID(device_id)
        success = device_service.trust_device(db, current_user, device_uuid)
        
        if success:
            return {"message": "Device marked as trusted"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error trusting device {device_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trust device"
        )

@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke/deactivate a device."""
    try:
        device_uuid = uuid.UUID(device_id)
        success = device_service.revoke_device(db, current_user, device_uuid)
        
        if success:
            return {"message": "Device revoked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking device {device_id} for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke device"
        )

@router.post("/devices/revoke-all")
async def revoke_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    except_current: bool = True
):
    """Revoke all devices for the user."""
    try:
        # If except_current is True, we need to identify the current device
        # For now, we'll revoke all devices since we don't have current device info
        # In a real implementation, you'd pass the current device fingerprint
        
        count = device_service.revoke_all_devices(db, current_user)
        
        return {
            "message": f"Successfully revoked {count} device(s)",
            "revoked_count": count
        }
        
    except Exception as e:
        logger.error(f"Error revoking all devices for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke devices"
        )

@router.post("/devices/register")
async def register_current_device(
    request_obj: Request,
    device_name: Optional[str] = None,
    remember: bool = False,
    security_level: DeviceSecurityLevel = DeviceSecurityLevel.ALWAYS_LOGIN,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register the current device."""
    try:
        device = device_service.register_device(
            db, 
            current_user, 
            request_obj,
            device_name=device_name,
            remember=remember,
            security_level=security_level
        )
        
        return {
            "message": "Device registered successfully",
            "device_id": str(device.id),
            "device_name": device.device_name
        }
        
    except Exception as e:
        logger.error(f"Error registering device for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device"
        )