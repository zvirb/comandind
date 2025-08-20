#!/usr/bin/env python3
"""
Creates an admin user for the AI Workflow Engine.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Import required modules
sys.path.append('/app')
from api.auth import get_password_hash, get_user_by_email
from shared.database.models import User, UserRole, UserStatus
from shared.utils.config import get_settings

def create_admin_user():
    """Create admin user from environment variables."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_local()
    
    try:
        # Get admin credentials from environment
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        print(f"Creating admin user: {admin_email}")
        
        # Check if user already exists
        existing_user = get_user_by_email(db_session, email=admin_email)
        if existing_user:
            print(f"Admin user {admin_email} already exists. Skipping.")
            return
        
        # Create admin user
        hashed_password = get_password_hash(admin_password)
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        
        db_session.add(admin_user)
        db_session.commit()
        print(f"Successfully created admin user: {admin_email}")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    create_admin_user()