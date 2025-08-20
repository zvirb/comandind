"""Pydantic schemas for Two-Factor Authentication API endpoints.

This module defines all the request/response schemas for the comprehensive 2FA system,
including TOTP, WebAuthn, SMS, Email, and administrative management schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
import re


# Base schemas
class TwoFactorMethodEnum(str):
    """Enumeration of supported 2FA methods."""
    TOTP = "totp"
    PASSKEY = "passkey"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"


class TwoFactorStatusResponse(BaseModel):
    """User's current 2FA status."""
    is_enabled: bool = Field(..., description="Whether 2FA is currently enabled")
    is_required: bool = Field(..., description="Whether 2FA is required for this user")
    grace_period_end: Optional[datetime] = Field(None, description="When grace period ends (if applicable)")
    
    methods_enabled: Dict[str, bool] = Field(
        ..., 
        description="Which 2FA methods are enabled",
        example={
            "totp": True,
            "passkey": False,
            "backup_codes": True
        }
    )
    
    passkey_count: int = Field(0, description="Number of registered passkeys")
    default_method: Optional[str] = Field(None, description="User's preferred 2FA method")
    recovery_email: Optional[str] = Field(None, description="Recovery email address")
    recovery_phone: Optional[str] = Field(None, description="Recovery phone number")


# TOTP schemas
class TOTPSetupRequest(BaseModel):
    """Request to setup TOTP authentication."""
    pass  # No additional data needed for initial setup


class TOTPSetupResponse(BaseModel):
    """Response from TOTP setup containing QR code and backup codes."""
    qr_code: str = Field(..., description="Base64 encoded QR code image")
    secret: str = Field(..., description="TOTP secret for manual entry")
    backup_codes: List[str] = Field(..., description="One-time backup codes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "secret": "JBSWY3DPEHPK3PXP",
                "backup_codes": ["a1b2c3d4", "e5f6g7h8", "i9j0k1l2"]
            }
        }


class TOTPVerificationRequest(BaseModel):
    """Request to verify TOTP code and enable TOTP."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('TOTP code must be numeric')
        return v


class TOTPVerificationResponse(BaseModel):
    """Response from TOTP verification."""
    verified: bool = Field(..., description="Whether verification was successful")
    enabled: bool = Field(..., description="Whether TOTP is now enabled")
    message: str = Field(..., description="Human-readable status message")


# WebAuthn/Passkey schemas
class PasskeySetupRequest(BaseModel):
    """Request to start passkey registration."""
    credential_name: str = Field(..., min_length=1, max_length=100, description="User-friendly name for the passkey")


class PasskeySetupResponse(BaseModel):
    """Response containing WebAuthn registration options."""
    registration_options: Dict[str, Any] = Field(..., description="WebAuthn registration options")
    session_token: str = Field(..., description="Session token for completing registration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "registration_options": {
                    "challenge": "base64url-encoded-challenge",
                    "rp": {"id": "example.com", "name": "AI Workflow Engine"},
                    "user": {"id": "base64url-encoded-user-id", "name": "user@example.com"}
                },
                "session_token": "session-token-here"
            }
        }


class PasskeyRegistrationRequest(BaseModel):
    """Request to complete passkey registration."""
    session_token: str = Field(..., description="Session token from setup response")
    credential_name: str = Field(..., min_length=1, max_length=100, description="User-friendly name for the passkey")
    credential_data: Dict[str, Any] = Field(..., description="WebAuthn credential data from browser")


class PasskeyRegistrationResponse(BaseModel):
    """Response from passkey registration completion."""
    registered: bool = Field(..., description="Whether registration was successful")
    credential_id: Optional[str] = Field(None, description="ID of the registered credential")
    message: str = Field(..., description="Human-readable status message")


class PasskeyListResponse(BaseModel):
    """List of user's registered passkeys."""
    passkeys: List[Dict[str, Any]] = Field(..., description="List of registered passkeys")
    
    class Config:
        json_schema_extra = {
            "example": {
                "passkeys": [
                    {
                        "id": "credential-id-1",
                        "name": "MacBook Touch ID",
                        "registered_at": "2023-01-01T00:00:00Z",
                        "last_used_at": "2023-01-02T12:00:00Z",
                        "authenticator_type": "platform"
                    }
                ]
            }
        }


# SMS 2FA schemas
class SMSSetupRequest(BaseModel):
    """Request to setup SMS 2FA."""
    phone_number: str = Field(..., description="Phone number for SMS 2FA")
    country_code: str = Field(..., description="Country code (e.g., +1)")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic phone number validation
        phone_pattern = re.compile(r'^[0-9\-\+\s\(\)]{7,20}$')
        if not phone_pattern.match(v):
            raise ValueError('Invalid phone number format')
        return v


class SMSSetupResponse(BaseModel):
    """Response from SMS setup."""
    setup_complete: bool = Field(..., description="Whether SMS setup is complete")
    phone_number_masked: str = Field(..., description="Masked phone number for confirmation")
    verification_required: bool = Field(True, description="Whether phone verification is required")


class SMSVerificationRequest(BaseModel):
    """Request to verify SMS code."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit SMS code")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('SMS code must be numeric')
        return v


# Email 2FA schemas
class EmailSetupRequest(BaseModel):
    """Request to setup Email 2FA."""
    email_address: EmailStr = Field(..., description="Email address for 2FA")


class EmailSetupResponse(BaseModel):
    """Response from Email setup."""
    setup_complete: bool = Field(..., description="Whether Email setup is complete")
    email_masked: str = Field(..., description="Masked email address for confirmation")
    verification_required: bool = Field(True, description="Whether email verification is required")


class EmailVerificationRequest(BaseModel):
    """Request to verify email code."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit email code")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('Email code must be numeric')
        return v


# Challenge and authentication schemas
class TwoFactorChallengeRequest(BaseModel):
    """Request to start a 2FA challenge."""
    method: str = Field(..., description="2FA method to use")
    
    @validator('method')
    def validate_method(cls, v):
        valid_methods = ["totp", "passkey", "sms", "email"]
        if v not in valid_methods:
            raise ValueError(f'Method must be one of: {", ".join(valid_methods)}')
        return v


class TwoFactorChallengeResponse(BaseModel):
    """Response containing 2FA challenge data."""
    method: str = Field(..., description="2FA method being used")
    session_token: str = Field(..., description="Session token for this challenge")
    challenge_data: Optional[Dict[str, Any]] = Field(None, description="Method-specific challenge data")
    message: str = Field(..., description="Instructions for the user")
    expires_at: datetime = Field(..., description="When this challenge expires")


class TwoFactorVerificationRequest(BaseModel):
    """Request to verify a 2FA challenge."""
    session_token: str = Field(..., description="Session token from challenge response")
    response_data: Dict[str, Any] = Field(..., description="Method-specific response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_token": "challenge-session-token",
                "response_data": {
                    "code": "123456",  # For TOTP/SMS/Email
                    # OR
                    "credential_id": "passkey-credential-id",  # For WebAuthn
                    "authenticator_data": "...",
                    "client_data_json": "...",
                    "signature": "..."
                }
            }
        }


class TwoFactorVerificationResponse(BaseModel):
    """Response from 2FA verification."""
    verified: bool = Field(..., description="Whether verification was successful")
    method_used: str = Field(..., description="2FA method that was used")
    message: str = Field(..., description="Human-readable result message")
    access_token: Optional[str] = Field(None, description="New access token if login flow")


# Backup codes schemas
class BackupCodesGenerationResponse(BaseModel):
    """Response containing new backup codes."""
    backup_codes: List[str] = Field(..., description="New backup codes")
    generated_at: datetime = Field(..., description="When codes were generated")
    message: str = Field(..., description="Instructions for the user")
    
    class Config:
        json_schema_extra = {
            "example": {
                "backup_codes": ["a1b2c3d4", "e5f6g7h8", "i9j0k1l2"],
                "generated_at": "2023-01-01T00:00:00Z",
                "message": "Store these codes securely. Each can only be used once."
            }
        }


# Method management schemas
class MethodDisableRequest(BaseModel):
    """Request to disable a 2FA method."""
    method: str = Field(..., description="2FA method to disable")
    confirmation_code: Optional[str] = Field(None, description="Current 2FA code for confirmation")
    
    @validator('method')
    def validate_method(cls, v):
        valid_methods = ["totp", "passkey", "sms", "email"]
        if v not in valid_methods:
            raise ValueError(f'Method must be one of: {", ".join(valid_methods)}')
        return v


class MethodDisableResponse(BaseModel):
    """Response from disabling a 2FA method."""
    disabled: bool = Field(..., description="Whether method was successfully disabled")
    method: str = Field(..., description="Method that was disabled")
    remaining_methods: List[str] = Field(..., description="Remaining enabled methods")
    message: str = Field(..., description="Human-readable result message")


# Administrative schemas
class AdminTwoFactorStatusResponse(BaseModel):
    """Administrative view of user's 2FA status."""
    user_id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    is_enabled: bool = Field(..., description="Whether 2FA is enabled")
    is_required: bool = Field(..., description="Whether 2FA is required")
    grace_period_end: Optional[datetime] = Field(None, description="Grace period end date")
    methods_enabled: Dict[str, bool] = Field(..., description="Enabled methods")
    last_2fa_use: Optional[datetime] = Field(None, description="Last successful 2FA")
    failed_attempts: int = Field(0, description="Recent failed attempts")


class AdminOverrideRequest(BaseModel):
    """Request for admin to override 2FA requirement."""
    user_id: int = Field(..., description="Target user ID")
    override_type: str = Field(..., description="Type of override")
    reason: str = Field(..., min_length=10, description="Detailed reason for override")
    duration_hours: int = Field(24, ge=1, le=168, description="Override duration (1-168 hours)")
    is_emergency: bool = Field(False, description="Whether this is an emergency override")
    
    @validator('override_type')
    def validate_override_type(cls, v):
        valid_types = ["disable", "bypass", "extend_grace"]
        if v not in valid_types:
            raise ValueError(f'Override type must be one of: {", ".join(valid_types)}')
        return v


class AdminOverrideResponse(BaseModel):
    """Response from admin override request."""
    override_id: str = Field(..., description="Unique override ID")
    granted: bool = Field(..., description="Whether override was granted")
    expires_at: datetime = Field(..., description="When override expires")
    requires_approval: bool = Field(..., description="Whether additional approval is needed")
    message: str = Field(..., description="Human-readable result message")


# Compliance and reporting schemas
class ComplianceReportRequest(BaseModel):
    """Request for 2FA compliance report."""
    report_type: str = Field("summary", description="Type of report")
    period_start: Optional[datetime] = Field(None, description="Report period start")
    period_end: Optional[datetime] = Field(None, description="Report period end")
    include_details: bool = Field(False, description="Include detailed user data")
    
    @validator('report_type')
    def validate_report_type(cls, v):
        valid_types = ["summary", "detailed", "violations", "trends"]
        if v not in valid_types:
            raise ValueError(f'Report type must be one of: {", ".join(valid_types)}')
        return v


class ComplianceReportResponse(BaseModel):
    """2FA compliance report data."""
    report_id: str = Field(..., description="Unique report ID")
    generated_at: datetime = Field(..., description="Report generation time")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    
    # Summary statistics
    total_users: int = Field(..., description="Total number of users")
    users_with_2fa: int = Field(..., description="Users with 2FA enabled")
    compliance_percentage: float = Field(..., description="Overall compliance percentage")
    users_in_grace_period: int = Field(..., description="Users still in grace period")
    users_overdue: int = Field(..., description="Users overdue for 2FA setup")
    
    # Method breakdown
    method_usage: Dict[str, int] = Field(..., description="Usage count by method")
    
    # Security metrics
    failed_attempts: int = Field(..., description="Failed 2FA attempts in period")
    admin_overrides: int = Field(..., description="Admin overrides in period")
    
    # Detailed data (if requested)
    user_details: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed user data")
    recommendations: List[str] = Field(..., description="Compliance recommendations")


# Device and session schemas
class TrustedDeviceRequest(BaseModel):
    """Request to mark device as trusted."""
    device_name: str = Field(..., min_length=1, max_length=100, description="User-friendly device name")
    remember_duration_days: int = Field(30, ge=1, le=90, description="How long to remember (1-90 days)")


class TrustedDeviceResponse(BaseModel):
    """Response from trusted device registration."""
    device_id: str = Field(..., description="Unique device ID")
    trusted: bool = Field(..., description="Whether device is now trusted")
    expires_at: datetime = Field(..., description="When trust expires")
    message: str = Field(..., description="Human-readable result message")


class DeviceListResponse(BaseModel):
    """List of user's registered devices."""
    devices: List[Dict[str, Any]] = Field(..., description="List of registered devices")
    
    class Config:
        json_schema_extra = {
            "example": {
                "devices": [
                    {
                        "id": "device-id-1",
                        "name": "MacBook Pro",
                        "device_type": "desktop",
                        "is_trusted": True,
                        "last_seen_at": "2023-01-02T12:00:00Z",
                        "location": "San Francisco, CA"
                    }
                ]
            }
        }


# Settings and preferences schemas
class TwoFactorSettingsRequest(BaseModel):
    """Request to update 2FA settings."""
    preferred_method: Optional[str] = Field(None, description="Preferred 2FA method")
    fallback_method: Optional[str] = Field(None, description="Fallback 2FA method")
    remember_device_preference: Optional[bool] = Field(None, description="Whether to allow device remembering")
    notify_on_new_device: Optional[bool] = Field(None, description="Notify when new device detected")
    notify_on_failed_attempt: Optional[bool] = Field(None, description="Notify on failed 2FA attempts")
    notification_email: Optional[EmailStr] = Field(None, description="Email for security notifications")
    require_2fa_for_sensitive_actions: Optional[bool] = Field(None, description="Require 2FA for sensitive actions")
    auto_logout_minutes: Optional[int] = Field(None, ge=5, le=480, description="Auto logout time (5-480 minutes)")


class TwoFactorSettingsResponse(BaseModel):
    """User's current 2FA settings."""
    preferred_method: Optional[str] = Field(None, description="Preferred 2FA method")
    fallback_method: Optional[str] = Field(None, description="Fallback 2FA method")
    remember_device_preference: bool = Field(True, description="Whether device remembering is allowed")
    notify_on_new_device: bool = Field(True, description="Notify when new device detected")
    notify_on_failed_attempt: bool = Field(True, description="Notify on failed 2FA attempts")
    notification_email: Optional[str] = Field(None, description="Email for security notifications")
    require_2fa_for_sensitive_actions: bool = Field(False, description="Require 2FA for sensitive actions")
    auto_logout_minutes: Optional[int] = Field(None, description="Auto logout time in minutes")
    setup_completed_at: Optional[datetime] = Field(None, description="When 2FA setup was completed")
    last_method_change: Optional[datetime] = Field(None, description="Last time methods were changed")


# Error response schemas
class TwoFactorErrorResponse(BaseModel):
    """Error response for 2FA operations."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "invalid_code",
                "message": "The provided code is invalid or has expired",
                "details": {"attempts_remaining": 2},
                "retry_after": None
            }
        }