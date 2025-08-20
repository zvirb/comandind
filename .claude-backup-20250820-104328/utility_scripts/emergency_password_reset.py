#!/usr/bin/env python3
"""
Emergency password reset for admin users.
"""
import sys
import os
import logging
from pwdlib import PasswordHash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_passwords():
    """Reset all admin passwords to a known value."""
    import psycopg2
    
    # Connection parameters from docker environment
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ai_workflow_db',
        'user': 'app_user',
        'password': os.getenv('POSTGRES_PASSWORD', 'OVie0GVt2jSUi9aLrh9swS64KGraIZyHLprAEimLwKc=')
    }
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # Get password hasher
        pwd_hasher = PasswordHash.recommended()
        new_password = "Admin123!@#"
        hashed_password = pwd_hasher.hash(new_password)
        
        # Update both admin accounts
        users_to_update = [
            ('admin@example.com', 'admin'),
            ('admin@aiwfe.com', 'admin_aiwfe')
        ]
        
        for email, username in users_to_update:
            cur.execute(
                "UPDATE users SET hashed_password = %s WHERE email = %s",
                (hashed_password, email)
            )
            logger.info(f"✅ Updated password for {username} ({email})")
        
        # Commit changes
        conn.commit()
        
        logger.info("\n" + "="*50)
        logger.info("PASSWORDS RESET SUCCESSFULLY!")
        logger.info("="*50)
        logger.info("\nYou can now login with:")
        logger.info("  Email: admin@example.com OR admin@aiwfe.com")
        logger.info(f"  Password: {new_password}")
        logger.info("="*50)
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error resetting passwords: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = reset_passwords()
    sys.exit(0 if success else 1)