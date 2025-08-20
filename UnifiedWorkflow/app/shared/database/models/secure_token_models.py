"""Database models for secure token storage and session management."""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Boolean, Column, String, DateTime, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey

from shared.utils.database_setup import Base


class SecureTokenStorage(Base):
    """Secure storage for encrypted tokens with metadata."""
    __tablename__ = "secure_token_storage"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token identification
    token_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(50), nullable=False)  # access_token, refresh_token, etc.
    
    # Encrypted token data
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Session and device tracking
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Token lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Token status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metadata and audit
    token_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="secure_tokens")


class AuthenticationSession(Base):
    """Enhanced authentication session tracking."""
    __tablename__ = "authentication_sessions"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session identification
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Device and client information
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Session state
    auth_state: Mapped[str] = mapped_column(String(50), default="authenticated")  # authenticated, refreshing, extending, expired
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Session extensions
    extension_count: Mapped[int] = mapped_column(Integer, default=0)
    last_extended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Security tracking
    login_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # password, 2fa, etc.
    security_level: Mapped[str] = mapped_column(String(50), default="standard")
    
    # Session termination
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # logout, expiry, forced, etc.
    
    # Metadata
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="auth_sessions")
    session_warnings: Mapped[list["SessionWarning"]] = relationship("SessionWarning", back_populates="session")


class SessionWarning(Base):
    """Session warnings for expiry, activity, security alerts."""
    __tablename__ = "session_warnings"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Warning identification
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("authentication_sessions.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Warning details
    warning_type: Mapped[str] = mapped_column(String(50), nullable=False)  # expiry_warning, activity_warning, security_warning
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, critical
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Warning state
    action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    suggested_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Warning lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Warning metadata
    warning_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    session: Mapped["AuthenticationSession"] = relationship("AuthenticationSession", back_populates="session_warnings")
    user: Mapped["User"] = relationship("User")


class ConnectionHealthMetric(Base):
    """Connection health metrics tracking."""
    __tablename__ = "connection_health_metrics"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric identification
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("authentication_sessions.id"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    
    # Health metrics
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Request metrics
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance metrics
    average_response_time: Mapped[Optional[float]] = mapped_column(String(10), nullable=True)  # milliseconds
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    
    # Health status
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy, degraded, unhealthy, unknown
    
    # Additional metrics
    queue_size: Mapped[int] = mapped_column(Integer, default=0)
    processing_time: Mapped[Optional[float]] = mapped_column(String(10), nullable=True)
    
    # Detailed metrics
    metrics_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    session: Mapped[Optional["AuthenticationSession"]] = relationship("AuthenticationSession")
    user: Mapped[Optional["User"]] = relationship("User")


class AuthQueueOperation(Base):
    """Authentication queue operations tracking."""
    __tablename__ = "auth_queue_operations"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Operation identification
    operation_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Operation details
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # token_validation, token_refresh, etc.
    priority: Mapped[int] = mapped_column(Integer, default=1)
    
    # Operation state
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, in_progress, completed, failed, cancelled
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Operation lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Operation results
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Operation metadata
    operation_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    operation_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")


# Update the User model to include relationships to the new models
# This would be added to the existing User model in _models.py
"""
# Add these relationships to the User model:

secure_tokens: Mapped[list["SecureTokenStorage"]] = relationship(
    "SecureTokenStorage", back_populates="user", cascade="all, delete-orphan"
)

auth_sessions: Mapped[list["AuthenticationSession"]] = relationship(
    "AuthenticationSession", back_populates="user", cascade="all, delete-orphan"
)
"""