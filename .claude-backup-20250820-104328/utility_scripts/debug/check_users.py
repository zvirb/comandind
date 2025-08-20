#!/usr/bin/env python3
"""
Check existing users in database and create a test user if needed.
"""

import sys
sys.path.append('/project/app')

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from shared.database.models import User, UserRole
from shared.utils.config import get_settings
from api.auth import get_password_hash

def main():
    settings = get_settings()
    
    # Construct database URL
    password = settings.POSTGRES_PASSWORD.get_secret_value() if settings.POSTGRES_PASSWORD else 'password'
    db_url = f'postgresql+psycopg2://{settings.POSTGRES_USER}:{password}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}?sslmode=require'
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Check existing users
        users = session.query(User).all()
        print(f"Found {len(users)} users in database:")
        for user in users:
            print(f"  ID: {user.id}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}")
        
        # If no users, create test user
        if not users:
            print("\nNo users found. Creating test user...")
            test_user = User(
                email="test@example.com",
                hashed_password=get_password_hash("testpass123"),
                role=UserRole.USER,
                is_active=True
            )
            session.add(test_user)
            session.commit()
            print("✅ Test user created: test@example.com / testpass123")
        else:
            print("\nUsers already exist. Using first active user for testing.")

if __name__ == "__main__":
    main()