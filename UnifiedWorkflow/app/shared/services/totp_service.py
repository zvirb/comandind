"""Time-based One-Time Password (TOTP) service for 2FA using Google Authenticator."""

import base64
import io
import secrets
from typing import Optional, Dict, Any, Tuple
import pyotp
import qrcode
from sqlalchemy.orm import Session
from shared.database.models import User, UserTwoFactorAuth, TwoFactorMethod
from shared.utils.device_fingerprint import DeviceFingerprinter


class TOTPService:
    """Service for managing TOTP-based 2FA (Google Authenticator)."""
    
    def __init__(self):
        self.issuer_name = "AI Workflow Engine"
    
    def generate_secret(self) -> str:
        """Generate a new base32-encoded TOTP secret."""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """
        Generate a QR code for TOTP setup.
        
        Args:
            user_email: User's email address
            secret: Base32-encoded TOTP secret
            
        Returns:
            Base64-encoded PNG image of the QR code
        """
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: Base32-encoded TOTP secret
            token: 6-digit TOTP token to verify
            window: Number of time steps to allow for clock drift
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception:
            return False
    
    def generate_backup_codes(self, count: int = 8) -> list[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            # Format as XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes
    
    def setup_totp_for_user(self, db: Session, user: User) -> Dict[str, Any]:
        """
        Set up TOTP for a user.
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            Dict containing secret, QR code, and backup codes
        """
        # Generate new secret
        secret = self.generate_secret()
        
        # Generate QR code
        qr_code = self.generate_qr_code(user.email, secret)
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        
        # Get or create 2FA settings for user
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if not two_factor_auth:
            two_factor_auth = UserTwoFactorAuth(
                user_id=user.id,
                is_enabled=False,  # Will be enabled after verification
                default_method=TwoFactorMethod.TOTP
            )
            db.add(two_factor_auth)
        
        # Store the secret and backup codes (temporarily until verified)
        two_factor_auth.totp_secret = secret
        two_factor_auth.totp_backup_codes = backup_codes
        two_factor_auth.totp_enabled = False  # Will be enabled after verification
        
        db.commit()
        
        return {
            "secret": secret,
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "manual_entry_key": secret,
            "issuer": self.issuer_name
        }
    
    def verify_and_enable_totp(self, db: Session, user: User, token: str) -> bool:
        """
        Verify a TOTP token and enable TOTP for the user if valid.
        
        Args:
            db: Database session
            user: User object
            token: 6-digit TOTP token to verify
            
        Returns:
            True if token is valid and TOTP is enabled, False otherwise
        """
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if not two_factor_auth or not two_factor_auth.totp_secret:
            return False
        
        # Verify the token
        if self.verify_token(two_factor_auth.totp_secret, token):
            # Enable TOTP
            two_factor_auth.totp_enabled = True
            two_factor_auth.is_enabled = True
            two_factor_auth.default_method = TwoFactorMethod.TOTP
            db.commit()
            return True
        
        return False
    
    def authenticate_with_totp(self, db: Session, user: User, token: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate a user with TOTP token or backup code.
        
        Args:
            db: Database session
            user: User object
            token: TOTP token or backup code
            
        Returns:
            Tuple of (success, method_used)
        """
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if not two_factor_auth or not two_factor_auth.totp_enabled:
            return False, None
        
        # Try TOTP first
        if two_factor_auth.totp_secret and self.verify_token(two_factor_auth.totp_secret, token):
            return True, "totp"
        
        # Try backup codes
        if two_factor_auth.totp_backup_codes and token.upper() in two_factor_auth.totp_backup_codes:
            # Remove used backup code
            backup_codes = two_factor_auth.totp_backup_codes.copy()
            backup_codes.remove(token.upper())
            two_factor_auth.totp_backup_codes = backup_codes
            db.commit()
            return True, "backup_code"
        
        return False, None
    
    def disable_totp(self, db: Session, user: User) -> bool:
        """
        Disable TOTP for a user.
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            True if TOTP was disabled, False otherwise
        """
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if not two_factor_auth:
            return False
        
        # Disable TOTP
        two_factor_auth.totp_enabled = False
        two_factor_auth.totp_secret = None
        two_factor_auth.totp_backup_codes = None
        
        # Check if any other 2FA methods are enabled
        if not two_factor_auth.passkey_enabled:
            two_factor_auth.is_enabled = False
            two_factor_auth.default_method = None
        
        db.commit()
        return True
    
    def regenerate_backup_codes(self, db: Session, user: User) -> Optional[list[str]]:
        """
        Regenerate backup codes for a user.
        
        Args:
            db: Database session
            user: User object
            
        Returns:
            New backup codes if successful, None otherwise
        """
        two_factor_auth = db.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if not two_factor_auth or not two_factor_auth.totp_enabled:
            return None
        
        # Generate new backup codes
        backup_codes = self.generate_backup_codes()
        two_factor_auth.totp_backup_codes = backup_codes
        db.commit()
        
        return backup_codes


# Global service instance
totp_service = TOTPService()