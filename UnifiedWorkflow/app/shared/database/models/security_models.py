"""Security-related database models for audit trails and access controls."""

import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Boolean, String, DateTime, Integer, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, Enum as SQLAlchemyEnum

from shared.utils.database_setup import Base


class AuditOperation(str, enum.Enum):
    """Enumeration for audit operations."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SELECT = "SELECT"
    TRUNCATE = "TRUNCATE"


class ViolationSeverity(str, enum.Enum):
    """Enumeration for security violation severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AccessLevel(str, enum.Enum):
    """Enumeration for access levels."""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    ADMIN = "ADMIN"


class RetentionPolicyType(str, enum.Enum):
    """Enumeration for data retention policy types."""
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    ANONYMIZE = "ANONYMIZE"


class SecurityTier(str, enum.Enum):
    """Enumeration for security tier levels."""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    ENTERPRISE = "enterprise"


class SecurityRequirementType(str, enum.Enum):
    """Enumeration for security requirement types."""
    TWO_FACTOR_AUTH = "two_factor_auth"
    CLIENT_CERTIFICATE = "client_certificate"
    DEVICE_TRUST = "device_trust"
    HARDWARE_KEY = "hardware_key"
    THREAT_DETECTION = "threat_detection"
    COMPLIANCE_REPORTING = "compliance_reporting"


class SecurityRequirementStatus(str, enum.Enum):
    """Enumeration for security requirement completion status."""
    NOT_CONFIGURED = "not_configured"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditLog(Base):
    """Comprehensive audit logging for all database operations."""
    __tablename__ = "audit_log"
    __table_args__ = {'schema': 'audit'}
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[AuditOperation] = mapped_column(
        SQLAlchemyEnum(AuditOperation, values_callable=lambda x: [e.value for e in x]), 
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    row_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Data changes tracking
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    changed_fields: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Security context
    security_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )


class SecurityViolation(Base):
    """Security violations and unauthorized access attempts."""
    __tablename__ = "security_violations"
    __table_args__ = {'schema': 'audit'}
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[ViolationSeverity] = mapped_column(
        SQLAlchemyEnum(ViolationSeverity, values_callable=lambda x: [e.value for e in x]), 
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    table_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attempted_operation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Violation details
    violation_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Resolution tracking
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )


class DataAccessLog(Base):
    """Cross-service data access logging for privacy compliance."""
    __tablename__ = "data_access_log"
    __table_args__ = {'schema': 'audit'}
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    access_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Privacy tracking
    sensitive_data_accessed: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True
    )
    access_pattern: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Request context
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class DataRetentionPolicy(Base):
    """Data retention and privacy policies for GDPR compliance."""
    __tablename__ = "data_retention_policies"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retention_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_type: Mapped[RetentionPolicyType] = mapped_column(
        SQLAlchemyEnum(RetentionPolicyType, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Policy status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )


class QdrantAccessControl(Base):
    """Access control for Qdrant vector database operations."""
    __tablename__ = "qdrant_access_control"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    access_level: Mapped[AccessLevel] = mapped_column(
        SQLAlchemyEnum(AccessLevel, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Access control status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class EncryptedField(Base):
    """Encrypted field storage for sensitive data."""
    __tablename__ = "encrypted_fields"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    row_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Encrypted data
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    encryption_algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default='AES-256-GCM')
    
    # Metadata
    data_classification: Mapped[str] = mapped_column(String(20), nullable=False, default='SENSITIVE')
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")


class SecurityMetric(Base):
    """Security metrics and monitoring data."""
    __tablename__ = "security_metrics"
    __table_args__ = {'schema': 'audit'}
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(nullable=False)
    
    # Context
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    time_window: Mapped[str] = mapped_column(String(20), nullable=False, default='1h')
    
    # Metadata
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    threshold_violated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )


class PrivacyRequest(Base):
    """GDPR and privacy requests tracking."""
    __tablename__ = "privacy_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: 'DATA_EXPORT', 'DATA_DELETION', 'DATA_RECTIFICATION', 'DATA_PORTABILITY'
    
    # Request details
    request_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requested_scope: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='PENDING')
    # Statuses: 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', 'CANCELLED'
    
    # Compliance tracking
    legal_basis: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retention_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timeline
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Processing details
    processor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_export_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class CrossServiceAuth(Base):
    """Cross-service authentication tokens and permissions."""
    __tablename__ = "cross_service_auth"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Authentication details
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scope: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    
    # Token lifecycle
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        index=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


class SecurityActionType(str, enum.Enum):
    """Enumeration for security action types."""
    IP_BLOCK = "ip_block"
    USER_SUSPEND = "user_suspend"
    RATE_LIMIT = "rate_limit"
    ACCOUNT_LOCKOUT = "account_lockout"
    SERVICE_ISOLATION = "service_isolation"
    ALERT_ESCALATION = "alert_escalation"
    THREAT_QUARANTINE = "threat_quarantine"


class SecurityActionStatus(str, enum.Enum):
    """Enumeration for security action status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"


class SecurityAction(Base):
    """Automated security actions and responses."""
    __tablename__ = "security_actions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Action details
    action_type: Mapped[SecurityActionType] = mapped_column(
        SQLAlchemyEnum(SecurityActionType), 
        nullable=False, 
        index=True
    )
    target: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Severity and status
    severity: Mapped[ViolationSeverity] = mapped_column(
        SQLAlchemyEnum(ViolationSeverity), 
        nullable=False, 
        index=True
    )
    status: Mapped[SecurityActionStatus] = mapped_column(
        SQLAlchemyEnum(SecurityActionStatus), 
        nullable=False, 
        default=SecurityActionStatus.ACTIVE,
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    expiration: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Creation context
    auto_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), 
        nullable=True,
        index=True
    )
    created_by_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Action execution details
    execution_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_user_id])


class UserSecurityTier(Base):
    """User security tier configuration and status."""
    __tablename__ = "user_security_tiers"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, unique=True)
    
    # Security tier information
    current_tier: Mapped[SecurityTier] = mapped_column(
        SQLAlchemyEnum(SecurityTier), 
        nullable=False, 
        default=SecurityTier.STANDARD,
        index=True
    )
    requested_tier: Mapped[Optional[SecurityTier]] = mapped_column(
        SQLAlchemyEnum(SecurityTier), 
        nullable=True
    )
    
    # Tier upgrade tracking
    upgrade_in_progress: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    upgrade_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    upgrade_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Security configuration
    security_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    tier_features: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Administrative settings
    minimum_required_tier: Mapped[Optional[SecurityTier]] = mapped_column(
        SQLAlchemyEnum(SecurityTier), 
        nullable=True
    )
    admin_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compliance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="security_tier")


class SecurityRequirement(Base):
    """Security requirements for each tier and their completion status."""
    __tablename__ = "security_requirements"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Requirement information
    requirement_type: Mapped[SecurityRequirementType] = mapped_column(
        SQLAlchemyEnum(SecurityRequirementType), 
        nullable=False,
        index=True
    )
    required_for_tier: Mapped[SecurityTier] = mapped_column(
        SQLAlchemyEnum(SecurityTier), 
        nullable=False,
        index=True
    )
    
    # Status tracking
    status: Mapped[SecurityRequirementStatus] = mapped_column(
        SQLAlchemyEnum(SecurityRequirementStatus), 
        nullable=False, 
        default=SecurityRequirementStatus.NOT_CONFIGURED,
        index=True
    )
    
    # Configuration details
    configuration_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    validation_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Progress tracking
    setup_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Expiration and renewal
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class SecurityTierPolicy(Base):
    """Administrative policies for security tier requirements."""
    __tablename__ = "security_tier_policies"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Policy information
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tier requirements
    minimum_tier: Mapped[SecurityTier] = mapped_column(
        SQLAlchemyEnum(SecurityTier), 
        nullable=False,
        index=True
    )
    allowed_tiers: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    
    # Policy rules
    policy_rules: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enforcement_level: Mapped[str] = mapped_column(String(20), nullable=False, default="ADVISORY")
    # Levels: ADVISORY, MANDATORY, STRICT
    
    # Target scope
    applies_to_roles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    applies_to_users: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    exclude_users: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Grace period and compliance
    grace_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    compliance_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    # Administrative context
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_user_id])


class CertificateRequest(Base):
    """Client certificate requests and provisioning status."""
    __tablename__ = "certificate_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Request details
    request_type: Mapped[str] = mapped_column(String(20), nullable=False, default="CLIENT_CERT")
    # Types: CLIENT_CERT, SERVER_CERT, CA_CERT
    
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    # Platforms: windows, macos, linux, android, ios
    
    device_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Certificate details
    certificate_cn: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_san: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    key_size: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    # Statuses: PENDING, PROCESSING, READY, DOWNLOADED, EXPIRED, REVOKED
    
    # Certificate lifecycle
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Download information
    download_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    download_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_downloads: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    
    # File paths (for cleanup)
    certificate_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bundle_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class SecurityTierUpgradeLog(Base):
    """Log of security tier upgrade attempts and completions."""
    __tablename__ = "security_tier_upgrade_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Upgrade details
    from_tier: Mapped[SecurityTier] = mapped_column(SQLAlchemyEnum(SecurityTier), nullable=False)
    to_tier: Mapped[SecurityTier] = mapped_column(SQLAlchemyEnum(SecurityTier), nullable=False)
    
    # Status and progress
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="STARTED", index=True)
    # Statuses: STARTED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    
    progress_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Requirements tracking
    requirements_completed: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    requirements_failed: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Upgrade context
    upgrade_method: Mapped[str] = mapped_column(String(20), nullable=False, default="USER_INITIATED")
    # Methods: USER_INITIATED, ADMIN_REQUIRED, POLICY_ENFORCED, AUTO_UPGRADE
    
    upgrade_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Error handling
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")