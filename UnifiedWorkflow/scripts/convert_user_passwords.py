#!/usr/bin/env python3
"""
Script to convert user passwords directly from bcrypt to pwdlib format.
This preserves existing passwords so users can continue logging in.
"""

import logging
import sys
import getpass
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pwdlib import PasswordHash

from shared.utils.config import get_settings
from shared.utils.database_setup import Base

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pwd_hasher = PasswordHash.recommended()

def convert_user_passwords_directly(session):
    """
    Convert user passwords directly by asking admin for their passwords.
    This allows users to keep their existing passwords in the new format.
    """
    
    # Find all users with "needs reset" hashes (our previous migration)
    result = session.execute(
        text("SELECT id, email, hashed_password FROM users WHERE hashed_password LIKE '%NEEDS_PASSWORD_RESET%'")
    )
    reset_users = result.fetchall()
    
    if not reset_users:
        logger.info("No users found that need password conversion.")
        return
    
    logger.info(f"Found {len(reset_users)} users that need password conversion:")
    for user in reset_users:
        logger.info(f"  - {user[1]}")  # email
    
    print("\nTo convert these users' passwords, you'll need to provide their actual passwords.")
    print("They can then log in normally with their existing passwords using the new hash format.")
    print()
    
    converted_count = 0
    for user in reset_users:
        user_id, email, old_hash = user
        
        print(f"\nUser: {email}")
        while True:
            try:
                password = getpass.getpass(f"Enter password for {email} (or 'skip' to skip this user): ")
                if password.lower() == 'skip':
                    logger.info(f"Skipping user: {email}")
                    break
                
                if not password:
                    print("Password cannot be empty. Try again or type 'skip'.")
                    continue
                
                # Hash the password with new format
                new_hash = pwd_hasher.hash(password)
                
                # Update password in database
                session.execute(
                    text("UPDATE users SET hashed_password = :new_hash WHERE id = :user_id"),
                    {"new_hash": new_hash, "user_id": user_id}
                )
                
                logger.info(f"Converted password for user: {email}")
                converted_count += 1
                break
                
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                return
            except Exception as e:
                logger.error(f"Error processing {email}: {e}")
                break
    
    if converted_count > 0:
        session.commit()
        logger.info(f"Successfully converted passwords for {converted_count} users.")
        logger.info("Users can now log in with their existing passwords.")
    else:
        logger.info("No passwords were converted.")

def main():
    """Main conversion function."""
    settings = get_settings()
    
    # Create database engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        try:
            convert_user_passwords_directly(session)
            logger.info("Password conversion completed.")
        except Exception as e:
            logger.error(f"Error during password conversion: {e}", exc_info=True)
            session.rollback()
            raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Password conversion failed: {e}", exc_info=True)
        sys.exit(1)