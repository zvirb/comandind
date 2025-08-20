#!/usr/bin/env python3
"""Reset password for test user."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.models import User
from shared.utils.database_setup import get_async_session
from api.auth import get_password_hash

async def reset_password():
    """Reset password for test user."""
    
    # Create a known test user or reset existing one
    email = "test@example.com"
    username = "testuser"
    new_password = "TestPassword123!"
    
    async with get_async_session() as session:
        # Check if user exists
        result = await session.execute(
            select(User).where(
                (User.email == email) | (User.username == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update password
            user.hashed_password = get_password_hash(new_password)
            await session.commit()
            print(f"✓ Password reset for user: {user.username} ({user.email})")
        else:
            # Create new test user
            new_user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(new_password),
                is_active=True,
                is_verified=True,
                role="user"
            )
            session.add(new_user)
            await session.commit()
            print(f"✓ Created test user: {username} ({email})")
        
        print(f"Login credentials:")
        print(f"  Email: {email}")
        print(f"  Username: {username}")
        print(f"  Password: {new_password}")

if __name__ == "__main__":
    asyncio.run(reset_password())