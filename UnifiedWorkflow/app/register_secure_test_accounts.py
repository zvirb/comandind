#!/usr/bin/env python3
"""
Register secure test accounts with cryptographically strong passwords.
Creates admin@aiwfe.com (admin) and testuser@aiwfe.com (user) accounts.
"""
import secrets
import string
import sys
import os
import json
from datetime import datetime

# Add app to path for imports
sys.path.append('/home/marku/ai_workflow_engine/app')

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

def register_test_accounts():
    """Register secure test accounts using the unified auth API."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from shared.utils.config import get_settings
    from shared.database.models import User, UserRole, UserStatus
    from api.auth import get_password_hash, get_user_by_email
    
    # Generate secure credentials
    admin_password = generate_secure_password(20)  # Extra long for admin
    user_password = generate_secure_password(16)   # Standard length for user
    
    print("=== SECURE TEST ACCOUNT REGISTRATION ===")
    print(f"Generated secure credentials at {datetime.now().isoformat()}")
    print()
    
    # Store credentials securely for testing
    credentials = {
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
    
    registered_accounts = []
    
    try:
        for account_type, creds in credentials.items():
            email = creds["email"]
            password = creds["password"]
            role = UserRole.ADMIN if creds["role"] == "admin" else UserRole.USER
            
            print(f"Registering {account_type} account: {email}")
            
            # Check if user already exists
            existing_user = get_user_by_email(db_session, email=email)
            if existing_user:
                print(f"⚠️  Account {email} already exists. Skipping registration.")
                print(f"   Existing user ID: {existing_user.id}, Role: {existing_user.role}")
                continue
            
            # Create secure user account
            hashed_password = get_password_hash(password)
            
            # Generate username from email prefix
            username = email.split('@')[0] + "_" + secrets.token_hex(4)
            
            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role,
                status=UserStatus.ACTIVE,
                is_active=True,
                is_verified=True,  # Pre-verify test accounts
                tfa_enabled=False,
                notifications_enabled=True
            )
            
            db_session.add(new_user)
            db_session.commit()
            db_session.refresh(new_user)
            
            registered_accounts.append({
                "user_id": new_user.id,
                "email": email,
                "role": role.value,
                "password": password  # Store temporarily for validation
            })
            
            print(f"✅ Successfully registered {email}")
            print(f"   User ID: {new_user.id}")
            print(f"   Role: {role.value}")
            print(f"   Username: {username}")
            print()
        
        # Save credentials to secure file for testing
        credentials_file = "/home/marku/ai_workflow_engine/app/test_account_credentials.json"
        with open(credentials_file, 'w') as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "accounts": registered_accounts,
                "note": "Secure test accounts for authentication validation"
            }, f, indent=2)
        
        print(f"📁 Credentials saved to: {credentials_file}")
        print()
        print("=== REGISTRATION SUMMARY ===")
        print(f"Total accounts registered: {len(registered_accounts)}")
        for account in registered_accounts:
            print(f"- {account['email']} (ID: {account['user_id']}, Role: {account['role']})")
        
        print()
        print("🔐 SECURE CREDENTIALS FOR TESTING:")
        print("Admin Account:")
        print(f"  Email: admin@aiwfe.com")
        print(f"  Password: {credentials['admin']['password']}")
        print()
        print("User Account:")
        print(f"  Email: testuser@aiwfe.com")
        print(f"  Password: {credentials['user']['password']}")
        print()
        print("⚠️  These credentials are for testing only. Store securely!")
        
        return registered_accounts
        
    except Exception as e:
        print(f"❌ Error during registration: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    try:
        registered_accounts = register_test_accounts()
        print(f"\n🎉 Registration completed successfully! {len(registered_accounts)} accounts created.")
    except Exception as e:
        print(f"\n💥 Registration failed: {e}")
        sys.exit(1)