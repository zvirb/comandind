#!/usr/bin/env python3
"""
Reset passwords for test accounts with secure credentials.
Sets known passwords for admin@aiwfe.com and testuser@aiwfe.com for testing.
"""
import secrets
import string
import sys
import json
from datetime import datetime

# Add app to path for imports
sys.path.append('/app')

def generate_secure_password(length=16):
    """Generate a cryptographically secure password using recommended practices."""
    # Use a mix of uppercase, lowercase, digits, and special characters
    chars = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    
    # Ensure at least one character from each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase), 
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*-_=+")
    ]
    
    # Fill remaining length with random choices
    for _ in range(length - 4):
        password.append(secrets.choice(chars))
    
    # Shuffle the password list to randomize positions
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

def reset_test_passwords():
    """Reset passwords for existing test accounts."""
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import sessionmaker
    from shared.utils.config import get_settings
    from shared.database.models import User, UserRole, UserStatus
    from api.auth import get_password_hash, get_user_by_email
    
    # Generate secure credentials
    admin_password = generate_secure_password(20)  # Extra long for admin
    user_password = generate_secure_password(16)   # Standard length for user
    
    print("=== SECURE PASSWORD RESET FOR TEST ACCOUNTS ===")
    print(f"Password reset performed at {datetime.now().isoformat()}")
    print()
    
    # Store credentials securely for testing
    test_credentials = {
        "admin": {
            "email": "admin@aiwfe.com",
            "password": admin_password,
            "role": "admin"
        },
        "user": {
            "email": "testuser@aiwfe.com", 
            "password": user_password,
            "role": "user"
        }
    }
    
    # Setup database connection
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_local()
    
    updated_accounts = []
    
    try:
        for account_type, creds in test_credentials.items():
            email = creds["email"]
            password = creds["password"]
            
            print(f"Resetting password for {account_type} account: {email}")
            
            # Get existing user
            user = get_user_by_email(db_session, email=email)
            if not user:
                print(f"❌ Account {email} not found. Cannot reset password.")
                continue
            
            # Update password with secure hash
            hashed_password = get_password_hash(password)
            
            # Update user password using SQLAlchemy update
            stmt = update(User).where(User.id == user.id).values(
                hashed_password=hashed_password,
                is_verified=True,  # Ensure account is verified for testing
                is_active=True     # Ensure account is active
            )
            
            db_session.execute(stmt)
            db_session.commit()
            
            # Refresh user to get updated data
            db_session.refresh(user)
            
            updated_accounts.append({
                "user_id": user.id,
                "email": email,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "password": password,  # Store temporarily for validation
                "reset_at": datetime.now().isoformat()
            })
            
            print(f"✅ Successfully reset password for {email}")
            print(f"   User ID: {user.id}")
            print(f"   Role: {user.role.value if hasattr(user.role, 'value') else str(user.role)}")
            print(f"   Active: {getattr(user, 'is_active', False)}")
            print(f"   Verified: {getattr(user, 'is_verified', False)}")
            print()
        
        # Save credentials to file for testing
        credentials_output = {
            "reset_at": datetime.now().isoformat(),
            "accounts": updated_accounts,
            "note": "Secure test account credentials for authentication validation"
        }
        
        try:
            with open("/app/test_account_credentials.json", 'w') as f:
                json.dump(credentials_output, f, indent=2)
            print("📁 Credentials saved to: /app/test_account_credentials.json")
        except Exception as e:
            print(f"⚠️  Could not save credentials file: {e}")
        
        print()
        print("=== PASSWORD RESET SUMMARY ===")
        print(f"Total accounts updated: {len(updated_accounts)}")
        for account in updated_accounts:
            print(f"- {account['email']} (ID: {account['user_id']}, Role: {account['role']})")
        
        print()
        print("🔐 NEW SECURE CREDENTIALS FOR TESTING:")
        print("Admin Account:")
        print(f"  Email: admin@aiwfe.com")
        print(f"  Password: {test_credentials['admin']['password']}")
        print()
        print("User Account:")
        print(f"  Email: testuser@aiwfe.com")
        print(f"  Password: {test_credentials['user']['password']}")
        print()
        print("⚠️  These credentials are for testing only. Store securely!")
        print("🧪 You can now test login functionality with these credentials.")
        
        return updated_accounts
        
    except Exception as e:
        print(f"❌ Error during password reset: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    try:
        updated_accounts = reset_test_passwords()
        print(f"\n🎉 Password reset completed successfully! {len(updated_accounts)} accounts updated.")
    except Exception as e:
        print(f"\n💥 Password reset failed: {e}")
        sys.exit(1)