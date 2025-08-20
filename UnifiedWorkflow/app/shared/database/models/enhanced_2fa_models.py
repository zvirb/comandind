"""Enhanced 2FA Database Models - Comprehensive Multi-Method Authentication.

This module extends the existing auth models with additional tables for:
- 2FA enforcement policies and grace periods
- SMS and Email 2FA methods
- 2FA audit trails and compliance tracking
- Administrative override capabilities
- Cross-device 2FA synchronization
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Boolean, String, DateTime, Integer, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint

from shared.utils.database_setup import Base


class TwoFactorPolicyType(str, enum.Enum):
    """Types of 2FA enforcement policies."""
    MANDATORY_ALL = "mandatory_all"           # All users must have 2FA
    MANDATORY_ADMIN = "mandatory_admin"       # Only admins must have 2FA
    OPTIONAL = "optional"                     # 2FA is optional
    ROLE_BASED = "role_based"                # 2FA requirement based on role


class TwoFactorGraceStatus(str, enum.Enum):
    """Grace period status for 2FA enforcement."""
    ACTIVE = "active"                         # Grace period is active
    EXPIRED = "expired"                       # Grace period has expired
    COMPLETED = "completed"                   # User completed 2FA setup
    EXTENDED = "extended"                     # Admin extended grace period


class SMSProvider(str, enum.Enum):
    """SMS service providers."""
    TWILIO = "twilio"
    AWS_SNS = "aws_sns"
    NEXMO = "nexmo"
    CUSTOM = "custom"


class EmailProvider(str, enum.Enum):
    """Email service providers for 2FA."""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    MAILGUN = "mailgun"


class TwoFactorAuditAction(str, enum.Enum):
    """Actions that can be audited for 2FA."""
    SETUP_INITIATED = "setup_initiated"
    SETUP_COMPLETED = "setup_completed"
    SETUP_FAILED = "setup_failed"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"
    METHOD_DISABLED = "method_disabled"
    BACKUP_CODES_GENERATED = "backup_codes_generated"
    BACKUP_CODE_USED = "backup_code_used"
    ADMIN_OVERRIDE = "admin_override"
    GRACE_PERIOD_EXTENDED = "grace_period_extended"


class TwoFactorPolicy(Base):
    """System-wide 2FA enforcement policies."""
    __tablename__ = "two_factor_policies"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Policy configuration
    policy_type: Mapped[TwoFactorPolicyType] = mapped_column(
        SQLAlchemyEnum(TwoFactorPolicyType, values_callable=lambda x: [e.value for e in x]),
        default=TwoFactorPolicyType.MANDATORY_ALL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Grace period settings
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7)
    grace_period_warning_days: Mapped[int] = mapped_column(Integer, default=3)
    max_grace_extensions: Mapped[int] = mapped_column(Integer, default=1)
    
    # Enforcement settings
    allow_admin_override: Mapped[bool] = mapped_column(Boolean, default=True)
    admin_override_duration_hours: Mapped[int] = mapped_column(Integer, default=24)
    require_admin_approval_for_disable: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Method requirements
    minimum_methods_required: Mapped[int] = mapped_column(Integer, default=1)
    allowed_methods: Mapped[List[str]] = mapped_column(JSONB, default=["totp", "passkey", "backup_codes"])
    preferred_method_order: Mapped[List[str]] = mapped_column(JSONB, default=["passkey", "totp", "backup_codes"])
    
    # Compliance settings
    require_backup_method: Mapped[bool] = mapped_column(Boolean, default=True)
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=30)
    remember_device_days: Mapped[int] = mapped_column(Integer, default=30)
    
    # Metadata
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])


class UserTwoFactorGracePeriod(Base):
    """Tracks 2FA grace periods for individual users."""
    __tablename__ = "user_two_factor_grace_periods"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Grace period details
    status: Mapped[TwoFactorGraceStatus] = mapped_column(
        SQLAlchemyEnum(TwoFactorGraceStatus, values_callable=lambda x: [e.value for e in x]),
        default=TwoFactorGraceStatus.ACTIVE
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extension_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Notification tracking
    warning_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    final_warning_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Admin actions
    extended_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    extension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    extended_by_admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[extended_by])


class UserSMSTwoFactor(Base):
    """SMS-based 2FA configuration for users."""
    __tablename__ = "user_sms_two_factor"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Phone configuration
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(String(5), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Provider settings
    provider: Mapped[SMSProvider] = mapped_column(
        SQLAlchemyEnum(SMSProvider, values_callable=lambda x: [e.value for e in x]),
        default=SMSProvider.TWILIO
    )
    provider_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Rate limiting
    daily_sms_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_sms_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    max_daily_sms: Mapped[int] = mapped_column(Integer, default=10)
    
    # Security
    last_code_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class UserEmailTwoFactor(Base):
    """Email-based 2FA configuration for users."""
    __tablename__ = "user_email_two_factor"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Email configuration
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Provider settings
    provider: Mapped[EmailProvider] = mapped_column(
        SQLAlchemyEnum(EmailProvider, values_callable=lambda x: [e.value for e in x]),
        default=EmailProvider.SMTP
    )
    provider_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Rate limiting
    daily_email_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_email_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    max_daily_emails: Mapped[int] = mapped_column(Integer, default=5)
    
    # Security
    last_code_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class TwoFactorAuditLog(Base):
    """Comprehensive audit log for all 2FA activities."""
    __tablename__ = "two_factor_audit_log"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    # Action details
    action: Mapped[TwoFactorAuditAction] = mapped_column(
        SQLAlchemyEnum(TwoFactorAuditAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    method_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Request context
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Result and details
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Admin actions
    performed_by_admin: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    admin_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Risk assessment
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[performed_by_admin])


class TwoFactorVerificationCode(Base):
    """Temporary storage for SMS/Email verification codes."""
    __tablename__ = "two_factor_verification_codes"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Code details
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Hashed code for security
    method_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "sms" or "email"
    destination: Mapped[str] = mapped_column(String(255), nullable=False)  # Phone or email (masked)
    
    # Expiry and usage
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Rate limiting
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class TwoFactorAdminOverride(Base):
    """Tracks administrative overrides for 2FA enforcement."""
    __tablename__ = "two_factor_admin_overrides"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Override details
    override_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "disable", "bypass", "extend_grace"
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Duration
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Approval workflow
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Emergency settings
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    emergency_contact_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin: Mapped["User"] = relationship("User", foreign_keys=[admin_user_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])


class TwoFactorComplianceReport(Base):
    """Compliance reporting for 2FA enforcement."""
    __tablename__ = "two_factor_compliance_reports"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report metadata
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "daily", "weekly", "monthly"
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Compliance metrics
    total_users: Mapped[int] = mapped_column(Integer, nullable=False)
    users_with_2fa: Mapped[int] = mapped_column(Integer, nullable=False)
    users_in_grace_period: Mapped[int] = mapped_column(Integer, nullable=False)
    users_overdue: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Method breakdown
    totp_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passkey_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sms_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Security metrics
    failed_2fa_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    admin_overrides_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    backup_codes_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Detailed data
    compliance_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    recommendations: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    
    # Generation info
    generated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    generator: Mapped[Optional["User"]] = relationship("User")


class UserTwoFactorSettings(Base):
    """Extended user 2FA settings and preferences."""
    __tablename__ = "user_two_factor_settings"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # User preferences
    preferred_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fallback_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remember_device_preference: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notification preferences
    notify_on_new_device: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_failed_attempt: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Security preferences
    require_2fa_for_sensitive_actions: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_logout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allow_backup_codes: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Setup tracking
    setup_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_method_change: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_method_changes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Custom settings
    custom_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")