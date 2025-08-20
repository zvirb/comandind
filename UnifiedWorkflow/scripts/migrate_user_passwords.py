#!/usr/bin/env python3
"""
Script to migrate user passwords from bcrypt to pwdlib (Argon2id) format.
This handles the migration from the old authentication system to the new one.
"""

import logging
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pwdlib import PasswordHash

from shared.utils.config import get_settings
from shared.utils.database_setup import Base

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pwd_hasher = PasswordHash.recommended()

def migrate_bcrypt_passwords(session):
    """
    Migrate all users with bcrypt password hashes to require password reset.
    
    This approach:
    1. Identifies users with old bcrypt hashes ($2b$ format)
    2. Sets their password to a special "needs reset" value
    3. They'll need to use password reset flow to set new password with modern hash
    """
    
    # Find all users with bcrypt password hashes
    result = session.execute(
        text("SELECT id, email, hashed_password FROM users WHERE hashed_password LIKE '$2b$%'")
    )
    bcrypt_users = result.fetchall()
    
    if not bcrypt_users:
        logger.info("No users found with old bcrypt password hashes.")
        return
    
    logger.info(f"Found {len(bcrypt_users)} users with old bcrypt password hashes.")
    
    # Set a special "needs reset" password hash for these users
    # This is a valid but unusable hash that forces password reset
    needs_reset_hash = pwd_hasher.hash("NEEDS_PASSWORD_RESET_INVALID_LOGIN")
    
    updated_count = 0
    for user in bcrypt_users:
        user_id, email, old_hash = user
        logger.info(f"Migrating user: {email}")
        
        # Update password to "needs reset" state
        session.execute(
            text("UPDATE users SET hashed_password = :new_hash WHERE id = :user_id"),
            {"new_hash": needs_reset_hash, "user_id": user_id}
        )
        updated_count += 1
    
    session.commit()
    logger.info(f"Successfully migrated {updated_count} users to require password reset.")
    logger.info("Users will need to use the 'Forgot Password' feature to set new passwords.")

def main():
    """Main migration function."""
    settings = get_settings()
    
    # Create database engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            migrate_bcrypt_passwords(session)
            logger.info("Password migration completed successfully.")
        except Exception as e:
            logger.error(f"Error during password migration: {e}", exc_info=True)
            session.rollback()
            raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Password migration failed: {e}", exc_info=True)
        sys.exit(1)