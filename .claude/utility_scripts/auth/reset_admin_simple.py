#!/usr/bin/env python3
"""
Simple admin password reset script for Docker execution.
"""
import sys
import os
import logging

# Add app directory to path for imports
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.models import User
from api.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_admin_password(new_password="Admin123!@#"):
    """Reset admin password to a known value."""
    try:
        # Get database URL from environment or use Docker service name
        database_url = os.getenv("DATABASE_URL", "postgresql://aiwfe_user:aiwfe_pass@postgres:5432/aiwfe_db")
        
        # Create database connection
        logger.info(f"Connecting to database...")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Get admin user
        with SessionLocal() as db:
            admin_user = db.query(User).filter(User.email == "admin@aiwfe.com").first()
            
            if not admin_user:
                logger.error("Admin user not found!")
                return False
            
            # Update password
            admin_user.hashed_password = get_password_hash(new_password)
            db.commit()
            
            logger.info(f"✅ Admin password reset successfully!")
            logger.info(f"Email: admin@aiwfe.com")
            logger.info(f"Password: {new_password}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reset admin password")
    parser.add_argument("--password", default="Admin123!@#", help="New password")
    args = parser.parse_args()
    
    success = reset_admin_password(args.password)
    sys.exit(0 if success else 1)