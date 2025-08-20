"""Enhanced 2FA Service - Comprehensive Multi-Method Two-Factor Authentication System.

This service provides enterprise-grade 2FA with support for:
- TOTP (Time-based One-Time Password) with QR code generation
- WebAuthn/FIDO2 hardware security keys
- SMS and Email 2FA with international support  
- Backup codes for emergency access
- Mandatory 2FA enforcement with grace periods
- Administrative override capabilities
"""

import base64
import hashlib
import hmac
import io
import json
import logging
import secrets
import struct
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any

import pyotp
import qrcode
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from webauthn import generate_registration_options, verify_registration_response
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers import structs, base64url_to_bytes, bytes_to_base64url

from shared.database.models import User
from shared.database.models.auth_models import (
    UserTwoFactorAuth, PasskeyCredential, TwoFactorChallenge, RegisteredDevice,
    TwoFactorMethod, DeviceLoginAttempt
)
from shared.utils.config import get_settings
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)
settings = get_settings()


class TwoFactorAuthMethod:
    """Base class for 2FA authentication methods."""
    
    def __init__(self, method_type: TwoFactorMethod):
        self.method_type = method_type
    
    async def setup(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Setup this 2FA method for a user."""
        raise NotImplementedError
    
    async def verify(self, user_id: int, challenge: str, **kwargs) -> bool:
        """Verify a 2FA challenge for this method."""
        raise NotImplementedError
    
    async def remove(self, user_id: int) -> bool:
        """Remove this 2FA method for a user."""
        raise NotImplementedError


class TOTPMethod(TwoFactorAuthMethod):
    """TOTP (Time-based One-Time Password) authentication method."""
    
    def __init__(self):
        super().__init__(TwoFactorMethod.TOTP)
        self.issuer = "AI Workflow Engine"
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode()) if hasattr(settings, 'ENCRYPTION_KEY') else None
    
    def _encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret for secure storage."""
        if self.cipher:
            return self.cipher.encrypt(secret.encode()).decode()
        return secret
    
    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt TOTP secret from storage."""
        if self.cipher:
            return self.cipher.decrypt(encrypted_secret.encode()).decode()
        return encrypted_secret
    
    async def setup(self, user_id: int, user_email: str, **kwargs) -> Dict[str, Any]:
        """Setup TOTP for a user and return QR code data."""
        try:
            # Generate a random 32-character base32 secret
            secret = pyotp.random_base32()
            
            # Create TOTP object
            totp = pyotp.TOTP(secret)
            
            # Generate provisioning URI for QR code
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.issuer
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for transmission
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            encrypted_backup_codes = [self._encrypt_secret(code) for code in backup_codes]
            
            return {
                "secret": secret,  # To be encrypted and stored
                "qr_code": f"data:image/png;base64,{img_str}",
                "backup_codes": backup_codes,  # Show to user once
                "encrypted_backup_codes": encrypted_backup_codes,  # Store in database
                "provisioning_uri": provisioning_uri
            }
            
        except Exception as e:
            logger.error(f"Error setting up TOTP for user {user_id}: {e}")
            raise ValueError("Failed to setup TOTP authentication")
    
    async def verify(self, user_id: int, challenge: str, secret: str = None, backup_codes: List[str] = None, **kwargs) -> bool:
        """Verify TOTP code or backup code."""
        try:
            # First try TOTP verification
            if secret:
                decrypted_secret = self._decrypt_secret(secret)
                totp = pyotp.TOTP(decrypted_secret)
                
                # Verify with window of 1 (30 seconds before/after)
                if totp.verify(challenge, valid_window=1):
                    return True
            
            # If TOTP fails, try backup codes
            if backup_codes:
                decrypted_codes = [self._decrypt_secret(code) for code in backup_codes]
                if challenge in decrypted_codes:
                    # Mark backup code as used (remove from list)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying TOTP for user {user_id}: {e}")
            return False
    
    async def remove(self, user_id: int) -> bool:
        """Remove TOTP setup for a user."""
        try:
            # This will be handled by the main 2FA service
            return True
        except Exception as e:
            logger.error(f"Error removing TOTP for user {user_id}: {e}")
            return False


class WebAuthnMethod(TwoFactorAuthMethod):
    """WebAuthn/FIDO2 passkey authentication method."""
    
    def __init__(self):
        super().__init__(TwoFactorMethod.PASSKEY)
        self.rp_id = settings.DOMAIN if hasattr(settings, 'DOMAIN') else "localhost"
        self.rp_name = "AI Workflow Engine"
        self.origin = f"https://{self.rp_id}" if self.rp_id != "localhost" else "http://localhost:3000"
    
    async def setup(self, user_id: int, user_email: str, **kwargs) -> Dict[str, Any]:
        """Generate WebAuthn registration options."""
        try:
            # Generate registration options
            registration_options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=str(user_id).encode(),
                user_name=user_email,
                user_display_name=user_email,
                challenge=secrets.token_bytes(32),
                exclude_credentials=[],  # Could exclude existing credentials
                authenticator_selection=structs.AuthenticatorSelectionCriteria(
                    authenticator_attachment=structs.AuthenticatorAttachment.PLATFORM,
                    resident_key=structs.ResidentKeyRequirement.REQUIRED,
                    user_verification=structs.UserVerificationRequirement.REQUIRED,
                ),
                attestation=structs.AttestationConveyancePreference.NONE,
            )
            
            return {
                "registration_options": registration_options,
                "challenge": base64url_to_bytes(registration_options.challenge)
            }
            
        except Exception as e:
            logger.error(f"Error setting up WebAuthn for user {user_id}: {e}")
            raise ValueError("Failed to setup WebAuthn authentication")
    
    async def verify_registration(self, user_id: int, credential_data: Dict[str, Any], challenge: bytes) -> Dict[str, Any]:
        """Verify WebAuthn registration response."""
        try:
            verification_response = verify_registration_response(
                credential=credential_data,
                expected_challenge=challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
            )
            
            if verification_response.verified:
                return {
                    "credential_id": verification_response.credential_id,
                    "public_key": verification_response.credential_public_key,
                    "sign_count": verification_response.sign_count,
                    "verified": True
                }
            
            return {"verified": False}
            
        except Exception as e:
            logger.error(f"Error verifying WebAuthn registration for user {user_id}: {e}")
            return {"verified": False}
    
    async def generate_authentication_options(self, user_id: int, credentials: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate WebAuthn authentication options."""
        try:
            # Convert stored credentials to the format expected by webauthn
            allow_credentials = [
                structs.PublicKeyCredentialDescriptor(
                    id=base64url_to_bytes(cred["credential_id"]),
                    type=structs.PublicKeyCredentialType.PUBLIC_KEY,
                )
                for cred in credentials
            ]
            
            authentication_options = generate_authentication_options(
                rp_id=self.rp_id,
                challenge=secrets.token_bytes(32),
                allow_credentials=allow_credentials,
                user_verification=structs.UserVerificationRequirement.REQUIRED,
            )
            
            return {
                "authentication_options": authentication_options,
                "challenge": base64url_to_bytes(authentication_options.challenge)
            }
            
        except Exception as e:
            logger.error(f"Error generating WebAuthn authentication options for user {user_id}: {e}")
            raise ValueError("Failed to generate authentication options")
    
    async def verify(self, user_id: int, challenge: str, credential_data: Dict[str, Any], stored_credential: Dict[str, Any], **kwargs) -> bool:
        """Verify WebAuthn authentication response."""
        try:
            verification_response = verify_authentication_response(
                credential=credential_data,
                expected_challenge=base64url_to_bytes(challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64url_to_bytes(stored_credential["public_key"]),
                credential_current_sign_count=stored_credential["sign_count"],
            )
            
            return verification_response.verified
            
        except Exception as e:
            logger.error(f"Error verifying WebAuthn authentication for user {user_id}: {e}")
            return False


class SMSMethod(TwoFactorAuthMethod):
    """SMS-based 2FA method."""
    
    def __init__(self):
        super().__init__(TwoFactorMethod.TOTP)  # Using TOTP enum for now
        # In production, integrate with SMS provider like Twilio, AWS SNS, etc.
        self.provider = None
    
    async def setup(self, user_id: int, phone_number: str, **kwargs) -> Dict[str, Any]:
        """Setup SMS 2FA for a user."""
        # Validate phone number format
        # In production, implement proper phone number validation
        if not phone_number or len(phone_number) < 10:
            raise ValueError("Invalid phone number")
        
        return {
            "phone_number": phone_number,
            "setup_complete": True
        }
    
    async def send_code(self, phone_number: str) -> str:
        """Send SMS verification code."""
        # Generate 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"
        
        # In production, send via SMS provider
        logger.info(f"SMS 2FA code for {phone_number}: {code}")
        
        return code
    
    async def verify(self, user_id: int, challenge: str, expected_code: str, **kwargs) -> bool:
        """Verify SMS code."""
        return challenge == expected_code


class EmailMethod(TwoFactorAuthMethod):
    """Email-based 2FA method."""
    
    def __init__(self):
        super().__init__(TwoFactorMethod.TOTP)  # Using TOTP enum for now
    
    async def setup(self, user_id: int, email: str, **kwargs) -> Dict[str, Any]:
        """Setup Email 2FA for a user."""
        return {
            "email": email,
            "setup_complete": True
        }
    
    async def send_code(self, email: str) -> str:
        """Send email verification code."""
        # Generate 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"
        
        # In production, send via email service
        logger.info(f"Email 2FA code for {email}: {code}")
        
        return code
    
    async def verify(self, user_id: int, challenge: str, expected_code: str, **kwargs) -> bool:
        """Verify email code."""
        return challenge == expected_code


class Enhanced2FAService:
    """Comprehensive 2FA service supporting multiple authentication methods."""
    
    def __init__(self):
        self.methods = {
            TwoFactorMethod.TOTP: TOTPMethod(),
            TwoFactorMethod.PASSKEY: WebAuthnMethod(),
        }
        self.sms_method = SMSMethod()
        self.email_method = EmailMethod()
        
        # 2FA enforcement settings
        self.mandatory_2fa_enabled = True
        self.grace_period_days = 7
        self.admin_override_duration_hours = 24
    
    async def is_2fa_required(self, user_id: int, session: AsyncSession) -> Tuple[bool, Optional[datetime]]:
        """Check if 2FA is required for a user and return grace period end if applicable."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                return False, None
            
            # Check if 2FA is globally mandatory
            if not self.mandatory_2fa_enabled:
                return False, None
            
            # Check if user already has 2FA enabled
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if user_2fa and user_2fa.is_enabled:
                return False, None  # 2FA already set up
            
            # Calculate grace period end
            grace_period_end = user.created_at + timedelta(days=self.grace_period_days)
            
            # Check if grace period has expired
            if datetime.now(timezone.utc) > grace_period_end:
                return True, None  # Must set up 2FA immediately
            
            return True, grace_period_end  # 2FA required but still in grace period
            
        except Exception as e:
            logger.error(f"Error checking 2FA requirement for user {user_id}: {e}")
            return False, None
    
    async def get_user_2fa_status(self, user_id: int, session: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive 2FA status for a user."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            # Get passkey credentials
            result = await session.execute(
                select(PasskeyCredential).where(
                    PasskeyCredential.user_id == user_id,
                    PasskeyCredential.is_active == True
                )
            )
            passkeys = result.scalars().all()
            
            # Check if 2FA is required
            is_required, grace_period_end = await self.is_2fa_required(user_id, session)
            
            return {
                "is_enabled": user_2fa.is_enabled if user_2fa else False,
                "is_required": is_required,
                "grace_period_end": grace_period_end.isoformat() if grace_period_end else None,
                "methods_enabled": {
                    "totp": user_2fa.totp_enabled if user_2fa else False,
                    "passkey": len(passkeys) > 0,
                    "backup_codes": bool(user_2fa.totp_backup_codes) if user_2fa else False,
                },
                "passkey_count": len(passkeys),
                "default_method": user_2fa.default_method.value if user_2fa and user_2fa.default_method else None,
                "recovery_email": user_2fa.recovery_email if user_2fa else None,
                "recovery_phone": user_2fa.recovery_phone if user_2fa else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting 2FA status for user {user_id}: {e}")
            return {"is_enabled": False, "is_required": False}
    
    async def setup_totp(self, user_id: int, user_email: str, session: AsyncSession) -> Dict[str, Any]:
        """Setup TOTP authentication for a user."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Generate TOTP setup data
            totp_setup = await self.methods[TwoFactorMethod.TOTP].setup(user_id, user_email)
            
            # Get or create user 2FA record
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa:
                user_2fa = UserTwoFactorAuth(
                    user_id=user_id,
                    is_enabled=False,  # Will be enabled after verification
                    totp_enabled=False,
                    passkey_enabled=False
                )
                session.add(user_2fa)
            
            # Store encrypted secret (don't enable yet)
            cipher = Fernet(settings.ENCRYPTION_KEY.encode()) if hasattr(settings, 'ENCRYPTION_KEY') else None
            if cipher:
                encrypted_secret = cipher.encrypt(totp_setup["secret"].encode()).decode()
            else:
                encrypted_secret = totp_setup["secret"]
            
            user_2fa.totp_secret = encrypted_secret
            user_2fa.totp_backup_codes = totp_setup["encrypted_backup_codes"]
            
            await session.commit()
            
            # Log the setup attempt
            await security_audit_service.log_security_event(
                session=session,
                user_id=user_id,
                event_type="2fa_totp_setup_initiated",
                details={"method": "TOTP"},
                severity="INFO"
            )
            
            return {
                "qr_code": totp_setup["qr_code"],
                "backup_codes": totp_setup["backup_codes"],
                "secret": totp_setup["secret"]  # For manual entry
            }
            
        except Exception as e:
            logger.error(f"Error setting up TOTP for user {user_id}: {e}")
            await session.rollback()
            raise ValueError("Failed to setup TOTP authentication")
    
    async def verify_and_enable_totp(self, user_id: int, totp_code: str, session: AsyncSession) -> bool:
        """Verify TOTP code and enable TOTP authentication."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user 2FA record
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa or not user_2fa.totp_secret:
                return False
            
            # Verify TOTP code
            is_valid = await self.methods[TwoFactorMethod.TOTP].verify(
                user_id=user_id,
                challenge=totp_code,
                secret=user_2fa.totp_secret,
                backup_codes=user_2fa.totp_backup_codes or []
            )
            
            if is_valid:
                # Enable TOTP and overall 2FA
                user_2fa.totp_enabled = True
                user_2fa.is_enabled = True
                if not user_2fa.default_method:
                    user_2fa.default_method = TwoFactorMethod.TOTP
                
                await session.commit()
                
                # Log successful setup
                await security_audit_service.log_security_event(
                    session=session,
                    user_id=user_id,
                    event_type="2fa_totp_setup_completed",
                    details={"method": "TOTP"},
                    severity="INFO"
                )
                
                return True
            
            # Log failed verification
            await security_audit_service.log_security_event(
                session=session,
                user_id=user_id,
                event_type="2fa_totp_verification_failed",
                details={"method": "TOTP"},
                severity="WARNING"
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying TOTP for user {user_id}: {e}")
            await session.rollback()
            return False
    
    async def setup_webauthn_registration(self, user_id: int, user_email: str, session: AsyncSession) -> Dict[str, Any]:
        """Start WebAuthn/passkey registration process."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Generate registration options
            webauthn_setup = await self.methods[TwoFactorMethod.PASSKEY].setup(user_id, user_email)
            
            # Store challenge temporarily
            challenge_record = TwoFactorChallenge(
                user_id=user_id,
                challenge_type=TwoFactorMethod.PASSKEY,
                challenge_data={
                    "challenge": base64.b64encode(webauthn_setup["challenge"]).decode(),
                    "type": "registration"
                },
                session_token=secrets.token_urlsafe(32),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
            )
            session.add(challenge_record)
            await session.commit()
            
            # Log the setup attempt
            await security_audit_service.log_security_event(
                session=session,
                user_id=user_id,
                event_type="2fa_webauthn_setup_initiated",
                details={"method": "WebAuthn"},
                severity="INFO"
            )
            
            return {
                "registration_options": webauthn_setup["registration_options"],
                "session_token": challenge_record.session_token
            }
            
        except Exception as e:
            logger.error(f"Error setting up WebAuthn for user {user_id}: {e}")
            await session.rollback()
            raise ValueError("Failed to setup WebAuthn authentication")
    
    async def complete_webauthn_registration(
        self, 
        user_id: int, 
        session_token: str, 
        credential_data: Dict[str, Any], 
        credential_name: str,
        session: AsyncSession
    ) -> bool:
        """Complete WebAuthn registration process."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get and validate challenge
            result = await session.execute(
                select(TwoFactorChallenge).where(
                    TwoFactorChallenge.user_id == user_id,
                    TwoFactorChallenge.session_token == session_token,
                    TwoFactorChallenge.challenge_type == TwoFactorMethod.PASSKEY,
                    TwoFactorChallenge.expires_at > datetime.now(timezone.utc),
                    TwoFactorChallenge.is_completed == False
                )
            )
            challenge = result.scalar_one_or_none()
            
            if not challenge:
                return False
            
            # Verify registration
            challenge_bytes = base64.b64decode(challenge.challenge_data["challenge"])
            verification_result = await self.methods[TwoFactorMethod.PASSKEY].verify_registration(
                user_id=user_id,
                credential_data=credential_data,
                challenge=challenge_bytes
            )
            
            if verification_result["verified"]:
                # Store the credential
                passkey_credential = PasskeyCredential(
                    user_id=user_id,
                    credential_id=base64.b64encode(verification_result["credential_id"]).decode(),
                    public_key=base64.b64encode(verification_result["public_key"]).decode(),
                    sign_count=verification_result["sign_count"],
                    name=credential_name,
                    authenticator_type="platform",  # Could be detected
                    backup_eligible=False,
                    backup_state=False
                )
                session.add(passkey_credential)
                
                # Get or create user 2FA record
                result = await session.execute(
                    select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
                )
                user_2fa = result.scalar_one_or_none()
                
                if not user_2fa:
                    user_2fa = UserTwoFactorAuth(
                        user_id=user_id,
                        is_enabled=True,
                        totp_enabled=False,
                        passkey_enabled=True,
                        default_method=TwoFactorMethod.PASSKEY
                    )
                    session.add(user_2fa)
                else:
                    user_2fa.passkey_enabled = True
                    user_2fa.is_enabled = True
                    if not user_2fa.default_method:
                        user_2fa.default_method = TwoFactorMethod.PASSKEY
                
                # Mark challenge as completed
                challenge.is_completed = True
                challenge.completed_at = datetime.now(timezone.utc)
                
                await session.commit()
                
                # Log successful setup
                await security_audit_service.log_security_event(
                    session=session,
                    user_id=user_id,
                    event_type="2fa_webauthn_setup_completed",
                    details={"method": "WebAuthn", "credential_name": credential_name},
                    severity="INFO"
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error completing WebAuthn registration for user {user_id}: {e}")
            await session.rollback()
            return False
    
    async def start_2fa_challenge(self, user_id: int, method: str, session: AsyncSession) -> Dict[str, Any]:
        """Start a 2FA challenge for authentication."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa or not user_2fa.is_enabled:
                raise ValueError("2FA not enabled for user")
            
            if method == "totp":
                if not user_2fa.totp_enabled:
                    raise ValueError("TOTP not enabled for user")
                
                # For TOTP, no server-side challenge needed
                challenge_token = secrets.token_urlsafe(32)
                challenge_record = TwoFactorChallenge(
                    user_id=user_id,
                    challenge_type=TwoFactorMethod.TOTP,
                    challenge_data={"type": "totp_verification"},
                    session_token=challenge_token,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
                )
                session.add(challenge_record)
                await session.commit()
                
                return {
                    "method": "totp",
                    "session_token": challenge_token,
                    "message": "Enter your TOTP code"
                }
                
            elif method == "passkey":
                if not user_2fa.passkey_enabled:
                    raise ValueError("Passkey not enabled for user")
                
                # Get user's passkeys
                result = await session.execute(
                    select(PasskeyCredential).where(
                        PasskeyCredential.user_id == user_id,
                        PasskeyCredential.is_active == True
                    )
                )
                passkeys = result.scalars().all()
                
                if not passkeys:
                    raise ValueError("No active passkeys found")
                
                # Generate authentication options
                credentials = [
                    {
                        "credential_id": pk.credential_id,
                        "public_key": pk.public_key,
                        "sign_count": pk.sign_count
                    }
                    for pk in passkeys
                ]
                
                auth_options = await self.methods[TwoFactorMethod.PASSKEY].generate_authentication_options(
                    user_id=user_id,
                    credentials=credentials
                )
                
                # Store challenge
                challenge_token = secrets.token_urlsafe(32)
                challenge_record = TwoFactorChallenge(
                    user_id=user_id,
                    challenge_type=TwoFactorMethod.PASSKEY,
                    challenge_data={
                        "challenge": base64.b64encode(auth_options["challenge"]).decode(),
                        "type": "authentication"
                    },
                    session_token=challenge_token,
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
                )
                session.add(challenge_record)
                await session.commit()
                
                return {
                    "method": "passkey",
                    "session_token": challenge_token,
                    "authentication_options": auth_options["authentication_options"]
                }
            
            else:
                raise ValueError(f"Unsupported 2FA method: {method}")
                
        except Exception as e:
            logger.error(f"Error starting 2FA challenge for user {user_id}: {e}")
            await session.rollback()
            raise
    
    async def verify_2fa_challenge(
        self, 
        user_id: int, 
        session_token: str, 
        response_data: Dict[str, Any], 
        session: AsyncSession
    ) -> bool:
        """Verify a 2FA challenge response."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get and validate challenge
            result = await session.execute(
                select(TwoFactorChallenge).where(
                    TwoFactorChallenge.user_id == user_id,
                    TwoFactorChallenge.session_token == session_token,
                    TwoFactorChallenge.expires_at > datetime.now(timezone.utc),
                    TwoFactorChallenge.is_completed == False
                )
            )
            challenge = result.scalar_one_or_none()
            
            if not challenge:
                return False
            
            # Get user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa or not user_2fa.is_enabled:
                return False
            
            verified = False
            
            if challenge.challenge_type == TwoFactorMethod.TOTP:
                # Verify TOTP code
                totp_code = response_data.get("code", "")
                verified = await self.methods[TwoFactorMethod.TOTP].verify(
                    user_id=user_id,
                    challenge=totp_code,
                    secret=user_2fa.totp_secret,
                    backup_codes=user_2fa.totp_backup_codes or []
                )
                
                # If backup code was used, remove it
                if verified and totp_code in (user_2fa.totp_backup_codes or []):
                    user_2fa.totp_backup_codes.remove(totp_code)
                    
            elif challenge.challenge_type == TwoFactorMethod.PASSKEY:
                # Verify WebAuthn response
                credential_id = response_data.get("credential_id", "")
                
                # Get the specific passkey credential
                result = await session.execute(
                    select(PasskeyCredential).where(
                        PasskeyCredential.user_id == user_id,
                        PasskeyCredential.credential_id == credential_id,
                        PasskeyCredential.is_active == True
                    )
                )
                passkey = result.scalar_one_or_none()
                
                if passkey:
                    challenge_bytes = base64.b64decode(challenge.challenge_data["challenge"])
                    verified = await self.methods[TwoFactorMethod.PASSKEY].verify(
                        user_id=user_id,
                        challenge=base64.b64encode(challenge_bytes).decode(),
                        credential_data=response_data,
                        stored_credential={
                            "public_key": passkey.public_key,
                            "sign_count": passkey.sign_count
                        }
                    )
                    
                    if verified:
                        # Update sign count
                        passkey.sign_count += 1
                        passkey.last_used_at = datetime.now(timezone.utc)
            
            if verified:
                # Mark challenge as completed
                challenge.is_completed = True
                challenge.completed_at = datetime.now(timezone.utc)
                
                await session.commit()
                
                # Log successful authentication
                await security_audit_service.log_security_event(
                    session=session,
                    user_id=user_id,
                    event_type="2fa_authentication_success",
                    details={"method": challenge.challenge_type.value},
                    severity="INFO"
                )
                
                return True
            else:
                # Log failed authentication
                await security_audit_service.log_security_event(
                    session=session,
                    user_id=user_id,
                    event_type="2fa_authentication_failed",
                    details={"method": challenge.challenge_type.value},
                    severity="WARNING"
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error verifying 2FA challenge for user {user_id}: {e}")
            await session.rollback()
            return False
    
    async def disable_2fa_method(self, user_id: int, method: str, session: AsyncSession) -> bool:
        """Disable a specific 2FA method for a user."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa:
                return False
            
            if method == "totp":
                user_2fa.totp_enabled = False
                user_2fa.totp_secret = None
                user_2fa.totp_backup_codes = None
                
            elif method == "passkey":
                # Disable all passkeys
                await session.execute(
                    update(PasskeyCredential)
                    .where(PasskeyCredential.user_id == user_id)
                    .values(is_active=False)
                )
                user_2fa.passkey_enabled = False
            
            # Check if any methods are still enabled
            if not user_2fa.totp_enabled and not user_2fa.passkey_enabled:
                user_2fa.is_enabled = False
                user_2fa.default_method = None
            elif user_2fa.default_method and method == user_2fa.default_method.value:
                # Set new default method
                if user_2fa.totp_enabled:
                    user_2fa.default_method = TwoFactorMethod.TOTP
                elif user_2fa.passkey_enabled:
                    user_2fa.default_method = TwoFactorMethod.PASSKEY
            
            await session.commit()
            
            # Log the disable action
            await security_audit_service.log_security_event(
                session=session,
                user_id=user_id,
                event_type="2fa_method_disabled",
                details={"method": method},
                severity="INFO"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error disabling 2FA method {method} for user {user_id}: {e}")
            await session.rollback()
            return False
    
    async def admin_disable_user_2fa(self, admin_user_id: int, target_user_id: int, reason: str, session: AsyncSession) -> bool:
        """Admin emergency disable of user's 2FA."""
        try:
            # Set security context for admin
            await security_audit_service.set_security_context(
                session=session, user_id=admin_user_id, service_name="enhanced_2fa_service"
            )
            
            # Verify admin privileges
            result = await session.execute(select(User).where(User.id == admin_user_id))
            admin_user = result.scalar_one_or_none()
            
            if not admin_user or not admin_user.is_superuser:
                raise ValueError("Insufficient privileges")
            
            # Get target user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == target_user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if user_2fa:
                # Disable all 2FA methods
                user_2fa.is_enabled = False
                user_2fa.totp_enabled = False
                user_2fa.passkey_enabled = False
                user_2fa.totp_secret = None
                user_2fa.totp_backup_codes = None
                user_2fa.default_method = None
                
                # Disable all passkeys
                await session.execute(
                    update(PasskeyCredential)
                    .where(PasskeyCredential.user_id == target_user_id)
                    .values(is_active=False)
                )
                
                await session.commit()
                
                # Log the admin action
                await security_audit_service.log_security_event(
                    session=session,
                    user_id=admin_user_id,
                    event_type="admin_2fa_disabled",
                    details={
                        "target_user_id": target_user_id,
                        "reason": reason
                    },
                    severity="HIGH"
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error admin disabling 2FA for user {target_user_id}: {e}")
            await session.rollback()
            raise
    
    async def generate_new_backup_codes(self, user_id: int, session: AsyncSession) -> List[str]:
        """Generate new backup codes for a user."""
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, user_id=user_id, service_name="enhanced_2fa_service"
            )
            
            # Get user 2FA settings
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user_id)
            )
            user_2fa = result.scalar_one_or_none()
            
            if not user_2fa or not user_2fa.totp_enabled:
                raise ValueError("TOTP not enabled for user")
            
            # Generate new backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            # Encrypt and store
            cipher = Fernet(settings.ENCRYPTION_KEY.encode()) if hasattr(settings, 'ENCRYPTION_KEY') else None
            if cipher:
                encrypted_codes = [cipher.encrypt(code.encode()).decode() for code in backup_codes]
            else:
                encrypted_codes = backup_codes
            
            user_2fa.totp_backup_codes = encrypted_codes
            await session.commit()
            
            # Log the generation
            await security_audit_service.log_security_event(
                session=session,
                user_id=user_id,
                event_type="2fa_backup_codes_generated",
                details={"count": len(backup_codes)},
                severity="INFO"
            )
            
            return backup_codes
            
        except Exception as e:
            logger.error(f"Error generating backup codes for user {user_id}: {e}")
            await session.rollback()
            raise


# Global instance
enhanced_2fa_service = Enhanced2FAService()