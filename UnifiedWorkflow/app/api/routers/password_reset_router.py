"""Password reset router for handling forgot password functionality."""

import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

from api.auth import get_password_hash, verify_password
from shared.database.models import User
from shared.utils.database_setup import get_db, Base
from shared.utils.config import get_settings

router = APIRouter()

# Password reset token model
class PasswordResetToken(Base):
    """Stores password reset tokens."""
    __tablename__ = "password_reset_tokens"
    
    token: str = Column(String, primary_key=True, index=True)
    user_id: int = Column(Integer, nullable=False)
    expires_at: datetime = Column(DateTime(timezone=True), nullable=False)
    used: bool = Column(Boolean, default=False)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class MessageResponse(BaseModel):
    message: str

def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)

def send_password_reset_email(email: str, token: str, user_name: Optional[str] = None):
    """Send password reset email to user."""
    settings = get_settings()
    
    # For now, we'll just log the reset link since email configuration may not be set up
    reset_link = f"https://localhost/reset-password?token={token}"
    
    print(f"=== PASSWORD RESET EMAIL ===")
    print(f"To: {email}")
    print(f"Subject: Reset Your AI Workflow Engine Password")
    print(f"Reset Link: {reset_link}")
    print(f"Token: {token}")
    print(f"============================")
    
    # TODO: Implement actual email sending when SMTP is configured
    # This would use settings.SMTP_* configuration values
    
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset process.
    Sends a reset email to the user if the email exists.
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success message to prevent email enumeration
    # But only actually send email if user exists
    if user:
        # Generate reset token
        token = generate_reset_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
        
        # Store reset token in database
        reset_token = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at,
            used=False
        )
        
        # Remove any existing unused tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).delete()
        
        db.add(reset_token)
        db.commit()
        
        # Send reset email
        try:
            send_password_reset_email(user.email, token)
        except Exception as e:
            print(f"Failed to send reset email: {e}")
            # Don't fail the request if email sending fails
    
    return MessageResponse(
        message="If an account with that email exists, you will receive a password reset link shortly."
    )

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset user password using a valid reset token.
    """
    # Find the reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find the user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update user password
    user.hashed_password = get_password_hash(request.new_password)
    
    # Mark token as used
    reset_token.used = True
    
    db.commit()
    
    return MessageResponse(
        message="Password has been reset successfully. You can now log in with your new password."
    )

@router.get("/verify-reset-token/{token}")
async def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify if a reset token is valid (for frontend validation).
    """
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find the user to get email for display
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    
    return {
        "valid": True,
        "email": user.email if user else None,
        "expires_at": reset_token.expires_at.isoformat()
    }