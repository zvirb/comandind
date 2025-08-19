#!/usr/bin/env python3
"""
Create a test user for Profile API testing.
"""
import os
import sys
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add app path
sys.path.append('/home/marku/ai_workflow_engine/app')

from api.auth import get_password_hash, get_user_by_email
from shared.database.models import User, UserRole, UserStatus
from shared.utils.config import get_settings

async def create_test_user():
    """Create a test user for Profile API testing."""
    settings = get_settings()
    
    # Create sync session for user creation
    sync_engine = create_engine(settings.database_url_sync if hasattr(settings, 'database_url_sync') else settings.database_url.replace('postgresql+asyncpg', 'postgresql'))
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    db_session = session_local()
    
    try:
        # Test user credentials
        test_email = "test@example.com"
        test_password = "testpassword123"
        
        print(f"Creating test user: {test_email}")
        
        # Check if user already exists
        existing_user = get_user_by_email(db_session, email=test_email)
        if existing_user:
            print(f"Test user {test_email} already exists.")
            print(f"User ID: {existing_user.id}")
            print(f"Status: {existing_user.status}")
            print(f"Is Active: {existing_user.is_active}")
            return existing_user
        
        # Create test user
        hashed_password = get_password_hash(test_password)
        test_user = User(
            username="test_user",
            email=test_email,
            hashed_password=hashed_password,
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True
        )
        
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        print(f"Successfully created test user: {test_email}")
        print(f"User ID: {test_user.id}")
        print(f"Password: {test_password}")
        
        return test_user
        
    except Exception as e:
        print(f"Error creating test user: {e}")
        db_session.rollback()
        return None
        
    finally:
        db_session.close()

if __name__ == "__main__":
    user = asyncio.run(create_test_user())
    if user:
        print(f"\nTest user details:")
        print(f"Email: {user.email}")
        print(f"ID: {user.id}")
        print(f"Status: {user.status}")
        print(f"Role: {user.role}")
        print(f"Is Active: {user.is_active}")