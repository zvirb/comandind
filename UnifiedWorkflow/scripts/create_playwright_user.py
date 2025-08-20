#!/usr/bin/env python3
"""
Creates a test user for Playwright testing with trusted device.
"""
import hashlib
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import required modules
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
from api.auth import get_password_hash, get_user_by_email
from shared.database.models import User, UserRole, UserStatus
from shared.database.models.auth_models import (
    RegisteredDevice, DeviceSecurityLevel, DeviceType, UserTwoFactorAuth
)
from shared.utils.config import get_settings

# Test user configuration
TEST_USER_EMAIL = "playwright.test@example.com"
TEST_USER_PASSWORD = "PlaywrightTest123!"
PLAYWRIGHT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/120.0.0.0 Safari/537.36"
PLAYWRIGHT_DEVICE_NAME = "Playwright Test Browser"

def generate_playwright_device_fingerprint() -> str:
    """Generate a consistent device fingerprint for Playwright."""
    fingerprint_data = f"{PLAYWRIGHT_USER_AGENT}|1920x1080|UTC|en-US|Linux x86_64"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()

def create_playwright_user():
    """Create test user with trusted device for Playwright."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_local()
    
    try:
        print(f"Creating Playwright test user: {TEST_USER_EMAIL}")
        
        # Check if user already exists
        existing_user = get_user_by_email(db_session, email=TEST_USER_EMAIL)
        if existing_user:
            print(f"✅ Test user {TEST_USER_EMAIL} already exists (ID: {existing_user.id})")
            user = existing_user
        else:
            # Create test user
            hashed_password = get_password_hash(TEST_USER_PASSWORD)
            user = User(
                email=TEST_USER_EMAIL,
                hashed_password=hashed_password,
                role=UserRole.USER,
                status=UserStatus.ACTIVE,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db_session.add(user)
            db_session.flush()  # Get the user ID
            print(f"✅ Created test user {TEST_USER_EMAIL} (ID: {user.id})")
        
        # Generate consistent device fingerprint for Playwright
        device_fingerprint = generate_playwright_device_fingerprint()
        
        # Check if trusted device already exists
        existing_device = db_session.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user.id,
            RegisteredDevice.device_fingerprint == device_fingerprint
        ).first()
        
        if existing_device:
            print(f"✅ Trusted device already exists (ID: {existing_device.id})")
            # Ensure it's still trusted and active
            existing_device.is_trusted = True
            existing_device.is_active = True
            existing_device.security_level = DeviceSecurityLevel.AUTO_LOGIN
            existing_device.is_remembered = True
            existing_device.remember_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        else:
            # Create trusted device for Playwright
            device = RegisteredDevice(
                user_id=user.id,
                device_name=PLAYWRIGHT_DEVICE_NAME,
                device_fingerprint=device_fingerprint,
                user_agent=PLAYWRIGHT_USER_AGENT,
                device_type=DeviceType.DESKTOP,
                security_level=DeviceSecurityLevel.AUTO_LOGIN,  # Auto-login for trusted device
                is_remembered=True,
                remember_expires_at=datetime.now(timezone.utc) + timedelta(days=365),  # Remember for 1 year
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
                last_ip_address="127.0.0.1",
                is_active=True,
                is_trusted=True  # Mark as trusted to bypass 2FA
            )
            db_session.add(device)
            print(f"✅ Created trusted device for Playwright: {PLAYWRIGHT_DEVICE_NAME}")
        
        # Set up 2FA settings to allow trusted device bypass
        existing_2fa = db_session.query(UserTwoFactorAuth).filter(
            UserTwoFactorAuth.user_id == user.id
        ).first()
        
        if existing_2fa:
            print(f"✅ 2FA settings already exist for user")
        else:
            # Create 2FA settings (disabled by default for test user)
            two_factor_auth = UserTwoFactorAuth(
                user_id=user.id,
                is_enabled=False,  # Disabled for test user
                totp_enabled=False,
                passkey_enabled=False
            )
            db_session.add(two_factor_auth)
            print(f"✅ Created 2FA settings (disabled) for test user")
        
        db_session.commit()
        
        print("\n🎭 Playwright Test User Setup Complete!")
        print(f"   Email: {TEST_USER_EMAIL}")
        print(f"   Password: {TEST_USER_PASSWORD}")
        print(f"   Device Fingerprint: {device_fingerprint}")
        print(f"   User Agent: {PLAYWRIGHT_USER_AGENT}")
        print(f"   Device Name: {PLAYWRIGHT_DEVICE_NAME}")
        print("\n📝 Playwright can now login without 2FA using this trusted device.")
        
    except Exception as e:
        print(f"❌ Error creating Playwright user: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    create_playwright_user()