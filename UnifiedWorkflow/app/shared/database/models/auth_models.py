"""Authentication-related database models for 2FA and device management."""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Boolean, Column, String, DateTime, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, Enum as SQLAlchemyEnum

from shared.utils.database_setup import Base


class DeviceSecurityLevel(str, enum.Enum):
    """Security levels for registered devices."""
    ALWAYS_LOGIN = "always_login"           # User must always log in
    AUTO_LOGIN = "auto_login"               # User is automatically logged in
    ALWAYS_2FA = "always_2fa"               # User must always use 2FA


class TwoFactorMethod(str, enum.Enum):
    """Available 2FA methods."""
    TOTP = "totp"                           # Time-based One-Time Password (Google Authenticator)
    PASSKEY = "passkey"                     # WebAuthn/FIDO2 Passkey
    BACKUP_CODES = "backup_codes"           # One-time backup codes


class DeviceType(str, enum.Enum):
    """Types of devices that can be registered."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    UNKNOWN = "unknown"


class RegisteredDevice(Base):
    """Represents a registered device for a user."""
    __tablename__ = "registered_devices"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Device identification
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)  # User-friendly name
    device_fingerprint: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)  # Browser fingerprint
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        SQLAlchemyEnum(DeviceType, values_callable=lambda x: [e.value for e in x]), 
        default=DeviceType.UNKNOWN
    )
    
    # Security settings
    security_level: Mapped[DeviceSecurityLevel] = mapped_column(
        SQLAlchemyEnum(DeviceSecurityLevel, values_callable=lambda x: [e.value for e in x]), 
        default=DeviceSecurityLevel.ALWAYS_LOGIN
    )
    is_remembered: Mapped[bool] = mapped_column(Boolean, default=False)
    remember_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    location_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # City, country, etc.
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="registered_devices")


class UserTwoFactorAuth(Base):
    """Stores user's 2FA settings and credentials."""
    __tablename__ = "user_two_factor_auth"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Global 2FA settings
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    default_method: Mapped[Optional[TwoFactorMethod]] = mapped_column(
        SQLAlchemyEnum(TwoFactorMethod, values_callable=lambda x: [e.value for e in x]), 
        nullable=True
    )
    
    # TOTP (Google Authenticator) settings
    totp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # Base32 encoded secret
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_backup_codes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Encrypted backup codes
    
    # Passkey settings
    passkey_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Recovery settings
    recovery_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recovery_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="two_factor_auth")


class PasskeyCredential(Base):
    """Stores WebAuthn/FIDO2 passkey credentials."""
    __tablename__ = "passkey_credentials"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # WebAuthn credential data
    credential_id: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)  # Base64 encoded
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # CBOR encoded public key
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Credential metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # User-friendly name for the passkey
    authenticator_type: Mapped[str] = mapped_column(String(50), nullable=True)  # "platform" or "roaming"
    backup_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_state: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Registration info
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Associated device (optional)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("registered_devices.id"), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="passkey_credentials")
    device: Mapped[Optional["RegisteredDevice"]] = relationship("RegisteredDevice")


class TwoFactorChallenge(Base):
    """Temporary storage for 2FA challenges during authentication."""
    __tablename__ = "two_factor_challenges"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Challenge data
    challenge_type: Mapped[TwoFactorMethod] = mapped_column(
        SQLAlchemyEnum(TwoFactorMethod, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    challenge_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)  # Method-specific challenge data
    
    # Session info
    session_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class DeviceLoginAttempt(Base):
    """Logs device login attempts for security monitoring."""
    __tablename__ = "device_login_attempts"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("registered_devices.id"), nullable=True)
    
    # Attempt details
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # Attempted email
    device_fingerprint: Mapped[str] = mapped_column(String(512), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Result
    was_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    used_2fa: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_method: Mapped[Optional[TwoFactorMethod]] = mapped_column(
        SQLAlchemyEnum(TwoFactorMethod, values_callable=lambda x: [e.value for e in x]), 
        nullable=True
    )
    
    # Metadata
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    device: Mapped[Optional["RegisteredDevice"]] = relationship("RegisteredDevice")