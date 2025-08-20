#!/usr/bin/env python3
"""
Reset admin password to a known value.
This script safely resets the admin password for emergency access.
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.models import User
from api.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_admin_password(new_password="admin123"):
    """Reset admin password to a known value."""
    
    # Database connection
    database_url = "postgresql://app_user:$(cat secrets/postgres_password.txt)@localhost:5432/ai_workflow_db"
    
    # Read the actual password from secrets
    with open("secrets/postgres_password.txt", "r") as f:
        postgres_password = f.read().strip()
    
    database_url = f"postgresql://app_user:{postgres_password}@localhost:5432/ai_workflow_db"
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Find admin user
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        
        if not admin_user:
            logger.error("Admin user not found!")
            return False
        
        # Update password
        admin_user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        logger.info(f"✅ Admin password reset successfully!")
        logger.info(f"Email: admin@example.com")
        logger.info(f"New Password: {new_password}")
        
        # Also update the secrets file for consistency
        with open("secrets/admin_password.txt", "w") as f:
            f.write(new_password)
        
        return True
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reset admin password")
    parser.add_argument("--password", default="admin123", help="New password (default: admin123)")
    args = parser.parse_args()
    
    success = reset_admin_password(args.password)
    sys.exit(0 if success else 1)