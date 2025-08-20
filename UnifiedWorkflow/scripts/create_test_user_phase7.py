#!/usr/bin/env python3
"""
Phase 7 Iteration: Create test user for authentication validation
"""

import os
import sys
import asyncio
from datetime import datetime
from pwdlib import PasswordHash

# Add the app directory to Python path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

# Import from the app
from shared.utils.database_setup import get_async_session
from shared.database.models import User
from sqlalchemy import select

async def create_test_user():
    """Create a test user with known credentials for validation"""
    
    # Set up password hashing
    pwd_context = PasswordHash.recommended()
    
    # Test user credentials
    email = "phase7.test@example.com"
    username = "phase7test"
    password = "testpass123"
    full_name = "Phase 7 Test User"
    
    # Hash the password
    hashed_password = pwd_context.hash(password)
    
    print(f"Creating test user:")
    print(f"Email: {email}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Hashed: {hashed_password}")
    
    async for session in get_async_session():
        try:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"User {email} already exists, updating password...")
                existing_user.hashed_password = hashed_password
                existing_user.is_active = True
                await session.commit()
                print(f"Updated user {email}")
            else:
                # Create new user
                new_user = User(
                    email=email,
                    username=username,
                    hashed_password=hashed_password,
                    full_name=full_name,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                print(f"Created new user {email} with ID {new_user.id}")
            
            # Verify the user was created/updated
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"Verification successful:")
                print(f"  ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Username: {user.username}")
                print(f"  Active: {user.is_active}")
                print(f"  Created: {user.created_at}")
                
                # Test password verification
                is_valid = pwd_context.verify(password, user.hashed_password)
                print(f"  Password verification: {is_valid}")
                
                return True
            else:
                print("ERROR: User not found after creation")
                return False
                
        except Exception as e:
            print(f"ERROR: {e}")
            await session.rollback()
            return False

async def test_authentication():
    """Test authentication with the created user"""
    print("\n" + "="*50)
    print("TESTING AUTHENTICATION")
    print("="*50)
    
    import requests
    
    # Test credentials
    email = "phase7.test@example.com"
    password = "testpass123"
    
    # Test login
    login_data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(
            "https://aiwfe.com/api/v1/auth/jwt/login",
            json=login_data,
            timeout=10
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Login response headers: {dict(response.headers)}")
        print(f"Login response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ AUTHENTICATION SUCCESS!")
            return True
        else:
            print("❌ AUTHENTICATION FAILED")
            return False
            
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Phase 7 Iteration: Authentication Fix Test")
    print("="*50)
    
    # Create/update test user
    success = asyncio.run(create_test_user())
    
    if success:
        print("\n✅ User creation/update successful")
        
        # Test authentication
        auth_success = asyncio.run(test_authentication())
        
        if auth_success:
            print("\n🎉 PHASE 7 ITERATION SUCCESS: Authentication working!")
            exit(0)
        else:
            print("\n❌ PHASE 7 ITERATION FAILED: Authentication still broken")
            exit(1)
    else:
        print("\n❌ PHASE 7 ITERATION FAILED: User creation failed")
        exit(1)