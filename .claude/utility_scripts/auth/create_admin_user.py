#!/usr/bin/env python3
"""
Create or update admin user with correct password hash.
Uses the same configuration as the API to ensure compatibility.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
app_root = project_root / "app"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(app_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from shared.database.models import User
from pwdlib import PasswordHash
from shared.utils.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user(email="admin@example.com", password="admin123"):
    """Create or update admin user with correct password hash."""
    
    # Use the same configuration as the API
    settings = get_settings()
    database_url = str(settings.database_url)
    logger.info(f"Using database URL: {database_url}")
    
    # Create password hasher
    pwd_hasher = PasswordHash.recommended()
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == email).first()
        
        if admin_user:
            # Update existing user
            logger.info(f"Admin user exists, updating password...")
            admin_user.hashed_password = pwd_hasher.hash(password)
            admin_user.is_active = True
            admin_user.status = "active"
            db.commit()
            logger.info(f"✅ Admin user password updated successfully!")
        else:
            # Create new admin user - use direct SQL to handle username column
            logger.info(f"Creating new admin user...")
            hashed_password = pwd_hasher.hash(password)
            
            insert_query = text("""
                INSERT INTO users (username, email, hashed_password, is_active, is_verified, 
                                 status, role, tfa_enabled, notifications_enabled)
                VALUES (:username, :email, :hashed_password, :is_active, :is_verified,
                       :status, :role, :tfa_enabled, :notifications_enabled)
                RETURNING id, email
            """)
            
            result = db.execute(insert_query, {
                "username": "admin",  # Simple username for admin
                "email": email,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_verified": True,
                "status": "active",
                "role": "admin",
                "tfa_enabled": False,
                "notifications_enabled": True
            })
            
            new_user_data = result.first()
            db.commit()
            logger.info(f"✅ Admin user created successfully! ID: {new_user_data[0]}")
        
        logger.info(f"Email: {email}")
        logger.info(f"Password: {password}")
        logger.info(f"Status: active")
        logger.info(f"Role: admin")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating/updating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create or update admin user")
    parser.add_argument("--email", default="admin@example.com", help="Admin email")
    parser.add_argument("--password", default="admin123", help="Admin password")
    args = parser.parse_args()
    
    success = create_admin_user(args.email, args.password)
    sys.exit(0 if success else 1)