#!/usr/bin/env python3
"""
Script to set up a test user for Playwright testing with trusted device.
This allows Playwright to bypass 2FA for automated testing.
"""

import asyncio
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta

# Add the app directory to Python path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.models import User, UserStatus, UserRole
from shared.database.models.auth_models import (
    RegisteredDevice, DeviceSecurityLevel, DeviceType, UserTwoFactorAuth
)
from shared.utils.database_setup import get_async_session, initialize_database
from shared.utils.config import get_settings
from shared.services.security_audit_service import security_audit_service
from api.auth import get_password_hash


# Test user configuration
TEST_USER_EMAIL = "playwright.test@example.com"
TEST_USER_PASSWORD = "PlaywrightTest123!"
PLAYWRIGHT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/120.0.0.0 Safari/537.36"
PLAYWRIGHT_DEVICE_NAME = "Playwright Test Browser"


def generate_playwright_device_fingerprint() -> str:
    """Generate a consistent device fingerprint for Playwright."""
    fingerprint_data = f"{PLAYWRIGHT_USER_AGENT}|1920x1080|UTC|en-US|Linux x86_64"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


async def create_test_user_and_trusted_device():
    """Create test user and set up trusted device for Playwright."""
    
    # Initialize database first
    settings = get_settings()
    initialize_database(settings)
    
    async for session in get_async_session():
        try:
            # Set security context
            await security_audit_service.set_security_context(
                session=session, 
                user_id=None, 
                service_name="playwright_setup"
            )
            
            # Check if test user already exists
            result = await session.execute(
                select(User).where(User.email == TEST_USER_EMAIL)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"✅ Test user {TEST_USER_EMAIL} already exists (ID: {existing_user.id})")
                user = existing_user
            else:
                # Create test user
                hashed_password = get_password_hash(TEST_USER_PASSWORD)
                user = User(
                    email=TEST_USER_EMAIL,
                    hashed_password=hashed_password,
                    full_name="Playwright Test User",
                    role=UserRole.USER,
                    status=UserStatus.ACTIVE,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(user)
                await session.flush()  # Get the user ID
                print(f"✅ Created test user {TEST_USER_EMAIL} (ID: {user.id})")
            
            # Generate consistent device fingerprint for Playwright
            device_fingerprint = generate_playwright_device_fingerprint()
            
            # Check if trusted device already exists
            result = await session.execute(
                select(RegisteredDevice).where(
                    RegisteredDevice.user_id == user.id,
                    RegisteredDevice.device_fingerprint == device_fingerprint
                )
            )
            existing_device = result.scalar_one_or_none()
            
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
                session.add(device)
                print(f"✅ Created trusted device for Playwright: {PLAYWRIGHT_DEVICE_NAME}")
            
            # Set up 2FA settings to allow trusted device bypass
            result = await session.execute(
                select(UserTwoFactorAuth).where(UserTwoFactorAuth.user_id == user.id)
            )
            existing_2fa = result.scalar_one_or_none()
            
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
                session.add(two_factor_auth)
                print(f"✅ Created 2FA settings (disabled) for test user")
            
            await session.commit()
            
            print("\n🎭 Playwright Test User Setup Complete!")
            print(f"   Email: {TEST_USER_EMAIL}")
            print(f"   Password: {TEST_USER_PASSWORD}")
            print(f"   Device Fingerprint: {device_fingerprint}")
            print(f"   User Agent: {PLAYWRIGHT_USER_AGENT}")
            print(f"   Device Name: {PLAYWRIGHT_DEVICE_NAME}")
            print("\n📝 Playwright can now login without 2FA using this trusted device.")
            
            return user.id, device_fingerprint
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error setting up test user: {e}")
            raise
        finally:
            await session.close()


async def verify_setup():
    """Verify the test user and trusted device are set up correctly."""
    
    # Initialize database first
    settings = get_settings()
    initialize_database(settings)
    
    async for session in get_async_session():
        try:
            # Check user exists
            result = await session.execute(
                select(User).where(User.email == TEST_USER_EMAIL)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ Test user not found!")
                return False
            
            # Check trusted device exists
            device_fingerprint = generate_playwright_device_fingerprint()
            result = await session.execute(
                select(RegisteredDevice).where(
                    RegisteredDevice.user_id == user.id,
                    RegisteredDevice.device_fingerprint == device_fingerprint,
                    RegisteredDevice.is_trusted == True,
                    RegisteredDevice.is_active == True
                )
            )
            device = result.scalar_one_or_none()
            
            if not device:
                print("❌ Trusted device not found!")
                return False
            
            print("✅ Playwright test setup verified successfully!")
            print(f"   User ID: {user.id}")
            print(f"   Device ID: {device.id}")
            print(f"   Device is trusted: {device.is_trusted}")
            print(f"   Security level: {device.security_level}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying setup: {e}")
            return False
        finally:
            await session.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up Playwright test user")
    parser.add_argument("--verify", action="store_true", help="Verify existing setup")
    args = parser.parse_args()
    
    if args.verify:
        success = asyncio.run(verify_setup())
        sys.exit(0 if success else 1)
    else:
        asyncio.run(create_test_user_and_trusted_device())