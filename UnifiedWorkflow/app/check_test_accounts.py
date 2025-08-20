#!/usr/bin/env python3
"""
Check existing test accounts and provide login credentials.
"""
import sys
import json
from datetime import datetime

# Add app to path for imports
sys.path.append('/app')

def check_test_accounts():
    """Check existing test accounts and provide their details."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from shared.utils.config import get_settings
    from shared.database.models import User, UserRole, UserStatus
    from api.auth import get_user_by_email
    
    print("=== TEST ACCOUNT STATUS CHECK ===")
    print(f"Check performed at {datetime.now().isoformat()}")
    print()
    
    # Setup database connection
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_local()
    
    test_accounts = [
        {"email": "admin@aiwfe.com", "expected_role": "admin"},
        {"email": "testuser@aiwfe.com", "expected_role": "user"}
    ]
    
    existing_accounts = []
    
    try:
        for account_info in test_accounts:
            email = account_info["email"]
            
            print(f"Checking account: {email}")
            
            # Get user from database
            user = get_user_by_email(db_session, email=email)
            if user:
                existing_accounts.append({
                    "user_id": user.id,
                    "email": user.email,
                    "username": getattr(user, 'username', 'N/A'),
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "status": user.status.value if hasattr(user.status, 'value') else str(user.status),
                    "is_active": getattr(user, 'is_active', False),
                    "is_verified": getattr(user, 'is_verified', False),
                    "tfa_enabled": getattr(user, 'tfa_enabled', False),
                    "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
                })
                
                print(f"✅ Found account {email}")
                print(f"   User ID: {user.id}")
                print(f"   Username: {getattr(user, 'username', 'N/A')}")
                print(f"   Role: {user.role.value if hasattr(user.role, 'value') else str(user.role)}")
                print(f"   Status: {user.status.value if hasattr(user.status, 'value') else str(user.status)}")
                print(f"   Active: {getattr(user, 'is_active', False)}")
                print(f"   Verified: {getattr(user, 'is_verified', False)}")
                print(f"   2FA Enabled: {getattr(user, 'tfa_enabled', False)}")
                if hasattr(user, 'created_at') and user.created_at:
                    print(f"   Created: {user.created_at.isoformat()}")
                print()
            else:
                print(f"❌ Account {email} not found")
                print()
        
        print("=== ACCOUNT SUMMARY ===")
        print(f"Total existing accounts: {len(existing_accounts)}")
        
        if existing_accounts:
            print("\nExisting test accounts:")
            for account in existing_accounts:
                print(f"- {account['email']} (ID: {account['user_id']}, Role: {account['role']}, Status: {account['status']})")
            
            print("\n📋 TESTING CREDENTIALS:")
            print("These accounts exist but you'll need the passwords to test login.")
            print("To reset passwords for testing, you can:")
            print("1. Use the admin password reset functionality")
            print("2. Create new test accounts with known passwords")
            print("3. Use the password reset router endpoints")
            
            print("\n🔐 For login testing with existing accounts:")
            for account in existing_accounts:
                print(f"- Email: {account['email']}")
                print(f"  Role: {account['role']}")
                print(f"  Status: {'Ready for login' if account['is_active'] and account['status'] == 'active' else 'Account may need activation'}")
        else:
            print("No test accounts found. You may need to create them.")
        
        return existing_accounts
        
    except Exception as e:
        print(f"❌ Error checking accounts: {e}")
        raise
    finally:
        db_session.close()

if __name__ == "__main__":
    try:
        accounts = check_test_accounts()
        print(f"\n🎉 Check completed successfully! {len(accounts)} accounts found.")
    except Exception as e:
        print(f"\n💥 Check failed: {e}")
        sys.exit(1)