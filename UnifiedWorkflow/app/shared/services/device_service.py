"""Device management service for tracking and managing user devices."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from shared.database.models import (
    User, RegisteredDevice, DeviceSecurityLevel, DeviceType, 
    DeviceLoginAttempt, TwoFactorMethod
)
from shared.utils.device_fingerprint import DeviceFingerprinter


class DeviceService:
    """Service for managing user devices and security levels."""
    
    def __init__(self):
        self.remember_device_days = 30  # Default remember period
    
    def register_device(
        self, 
        db: Session, 
        user: User, 
        request: Request,
        device_name: Optional[str] = None,
        client_fingerprint: Optional[Dict[str, Any]] = None,
        remember: bool = False,
        security_level: DeviceSecurityLevel = DeviceSecurityLevel.ALWAYS_LOGIN
    ) -> RegisteredDevice:
        """
        Register a new device for a user.
        
        Args:
            db: Database session
            user: User object
            request: FastAPI request object
            device_name: User-friendly device name
            client_fingerprint: Client-side fingerprint data
            remember: Whether to remember this device
            security_level: Security level for this device
            
        Returns:
            RegisteredDevice object
        """
        # Generate device fingerprint
        device_fingerprint = DeviceFingerprinter.generate_fingerprint(request, client_fingerprint)
        
        # Check if device already exists
        existing_device = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.device_fingerprint == device_fingerprint
        ).first()
        
        if existing_device:
            # Update existing device
            existing_device.last_seen_at = datetime.now(timezone.utc)
            existing_device.last_ip_address = DeviceFingerprinter.get_client_ip(request)
            existing_device.is_active = True
            if remember:
                existing_device.is_remembered = True
                existing_device.remember_expires_at = datetime.now(timezone.utc) + timedelta(days=self.remember_device_days)
            db.commit()
            return existing_device
        
        # Parse user agent
        user_agent = request.headers.get('user-agent', '')
        user_agent_info = DeviceFingerprinter.parse_user_agent(user_agent)
        
        # Generate device name if not provided
        if not device_name:
            device_name = DeviceFingerprinter.generate_device_name(
                user_agent_info, 
                DeviceFingerprinter.get_client_ip(request)
            )
        
        # Determine device type
        device_type = DeviceType(DeviceFingerprinter.determine_device_type(user_agent_info))
        
        # Create new device
        device = RegisteredDevice(
            user_id=user.id,
            device_name=device_name,
            device_fingerprint=device_fingerprint,
            user_agent=user_agent,
            device_type=device_type,
            security_level=security_level,
            is_remembered=remember,
            remember_expires_at=datetime.now(timezone.utc) + timedelta(days=self.remember_device_days) if remember else None,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            last_ip_address=DeviceFingerprinter.get_client_ip(request),
            is_active=True,
            is_trusted=False
        )
        
        db.add(device)
        db.commit()
        
        return device
    
    def get_user_devices(self, db: Session, user: User, active_only: bool = True) -> List[RegisteredDevice]:
        """
        Get all devices for a user.
        
        Args:
            db: Database session
            user: User object
            active_only: Whether to return only active devices
            
        Returns:
            List of RegisteredDevice objects
        """
        query = db.query(RegisteredDevice).filter(RegisteredDevice.user_id == user.id)
        
        if active_only:
            query = query.filter(RegisteredDevice.is_active == True)
        
        return query.order_by(RegisteredDevice.last_seen_at.desc()).all()
    
    def get_device_by_fingerprint(
        self, 
        db: Session, 
        user: User, 
        device_fingerprint: str
    ) -> Optional[RegisteredDevice]:
        """
        Get a device by its fingerprint.
        
        Args:
            db: Database session
            user: User object
            device_fingerprint: Device fingerprint hash
            
        Returns:
            RegisteredDevice object if found, None otherwise
        """
        return db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.device_fingerprint == device_fingerprint,
            RegisteredDevice.is_active == True
        ).first()
    
    def update_device_security_level(
        self, 
        db: Session, 
        user: User, 
        device_id: uuid.UUID, 
        security_level: DeviceSecurityLevel
    ) -> bool:
        """
        Update the security level of a device.
        
        Args:
            db: Database session
            user: User object
            device_id: Device UUID
            security_level: New security level
            
        Returns:
            True if updated successfully, False otherwise
        """
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.is_active == True
        ).first()
        
        if not device:
            return False
        
        device.security_level = security_level
        db.commit()
        return True
    
    def update_device_name(
        self, 
        db: Session, 
        user: User, 
        device_id: uuid.UUID, 
        device_name: str
    ) -> bool:
        """
        Update the name of a device.
        
        Args:
            db: Database session
            user: User object
            device_id: Device UUID
            device_name: New device name
            
        Returns:
            True if updated successfully, False otherwise
        """
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.is_active == True
        ).first()
        
        if not device:
            return False
        
        device.device_name = device_name
        db.commit()
        return True
    
    def trust_device(self, db: Session, user: User, device_id: uuid.UUID) -> bool:
        """
        Mark a device as trusted.
        
        Args:
            db: Database session
            user: User object
            device_id: Device UUID
            
        Returns:
            True if updated successfully, False otherwise
        """
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.is_active == True
        ).first()
        
        if not device:
            return False
        
        device.is_trusted = True
        db.commit()
        return True
    
    def revoke_device(self, db: Session, user: User, device_id: uuid.UUID) -> bool:
        """
        Revoke/deactivate a device.
        
        Args:
            db: Database session
            user: User object
            device_id: Device UUID
            
        Returns:
            True if revoked successfully, False otherwise
        """
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user.id
        ).first()
        
        if not device:
            return False
        
        device.is_active = False
        device.is_remembered = False
        device.remember_expires_at = None
        db.commit()
        return True
    
    def revoke_all_devices(self, db: Session, user: User, except_device_id: Optional[uuid.UUID] = None) -> int:
        """
        Revoke all devices for a user except optionally one device.
        
        Args:
            db: Database session
            user: User object
            except_device_id: Device ID to exclude from revocation
            
        Returns:
            Number of devices revoked
        """
        query = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.is_active == True
        )
        
        if except_device_id:
            query = query.filter(RegisteredDevice.id != except_device_id)
        
        devices = query.all()
        count = len(devices)
        
        for device in devices:
            device.is_active = False
            device.is_remembered = False
            device.remember_expires_at = None
        
        db.commit()
        return count
    
    def is_device_remembered(self, db: Session, user: User, device_fingerprint: str) -> bool:
        """
        Check if a device is remembered and not expired.
        
        Args:
            db: Database session
            user: User object
            device_fingerprint: Device fingerprint hash
            
        Returns:
            True if device is remembered and not expired, False otherwise
        """
        device = self.get_device_by_fingerprint(db, user, device_fingerprint)
        
        if not device or not device.is_remembered:
            return False
        
        if device.remember_expires_at and device.remember_expires_at < datetime.now(timezone.utc):
            # Remember period has expired
            device.is_remembered = False
            device.remember_expires_at = None
            db.commit()
            return False
        
        return True
    
    def log_login_attempt(
        self,
        db: Session,
        email: str,
        request: Request,
        was_successful: bool,
        user: Optional[User] = None,
        device: Optional[RegisteredDevice] = None,
        failure_reason: Optional[str] = None,
        used_2fa: bool = False,
        two_factor_method: Optional[TwoFactorMethod] = None,
        client_fingerprint: Optional[Dict[str, Any]] = None
    ) -> DeviceLoginAttempt:
        """
        Log a login attempt for security monitoring.
        
        Args:
            db: Database session
            email: Email address used for login
            request: FastAPI request object
            was_successful: Whether the login was successful
            user: User object (if login was successful)
            device: Device object (if available)
            failure_reason: Reason for failure (if applicable)
            used_2fa: Whether 2FA was used
            two_factor_method: 2FA method used (if applicable)
            client_fingerprint: Client-side fingerprint data
            
        Returns:
            DeviceLoginAttempt object
        """
        device_fingerprint = DeviceFingerprinter.generate_fingerprint(request, client_fingerprint)
        
        attempt = DeviceLoginAttempt(
            user_id=user.id if user else None,
            device_id=device.id if device else None,
            email=email,
            device_fingerprint=device_fingerprint,
            ip_address=DeviceFingerprinter.get_client_ip(request),
            user_agent=request.headers.get('user-agent', ''),
            was_successful=was_successful,
            failure_reason=failure_reason,
            used_2fa=used_2fa,
            two_factor_method=two_factor_method,
            attempted_at=datetime.now(timezone.utc)
        )
        
        db.add(attempt)
        db.commit()
        
        return attempt
    
    def get_recent_login_attempts(
        self, 
        db: Session, 
        user: User, 
        days: int = 30,
        limit: int = 50
    ) -> List[DeviceLoginAttempt]:
        """
        Get recent login attempts for a user.
        
        Args:
            db: Database session
            user: User object
            days: Number of days to look back
            limit: Maximum number of attempts to return
            
        Returns:
            List of DeviceLoginAttempt objects
        """
        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        return db.query(DeviceLoginAttempt).filter(
            DeviceLoginAttempt.user_id == user.id,
            DeviceLoginAttempt.attempted_at >= since_date
        ).order_by(DeviceLoginAttempt.attempted_at.desc()).limit(limit).all()


# Global service instance
device_service = DeviceService()