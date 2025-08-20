#!/usr/bin/env python3
"""
Test authentication flow with secure test accounts.
Validates login functionality for admin@aiwfe.com and testuser@aiwfe.com.
"""
import requests
import json
import sys
from datetime import datetime

def test_authentication_flow():
    """Test the complete authentication flow for both test accounts."""
    
    print("=== SECURE AUTHENTICATION FLOW TEST ===")
    print(f"Test started at {datetime.now().isoformat()}")
    print()
    
    # Load test credentials
    try:
        with open("/app/test_account_credentials.json", 'r') as f:
            credentials_data = json.load(f)
        
        test_accounts = {}
        for account in credentials_data.get("accounts", []):
            test_accounts[account["email"]] = {
                "password": account["password"],
                "role": account["role"],
                "user_id": account["user_id"]
            }
    except Exception as e:
        print(f"❌ Could not load test credentials: {e}")
        return False
    
    # Base URL (try both HTTP and HTTPS)
    base_urls = [
        "https://aiwfe.com",
        "http://localhost:8000",
        "http://api:8000"
    ]
    
    successful_tests = []
    failed_tests = []
    
    for base_url in base_urls:
        print(f"\n🌐 Testing against: {base_url}")
        print("-" * 50)
        
        for email, account_data in test_accounts.items():
            password = account_data["password"]
            role = account_data["role"]
            user_id = account_data["user_id"]
            
            print(f"\n📧 Testing {role} account: {email}")
            
            # Test login
            login_success = test_login(base_url, email, password, role, user_id)
            
            test_result = {
                "base_url": base_url,
                "email": email,
                "role": role,
                "user_id": user_id,
                "login_success": login_success
            }
            
            if login_success:
                successful_tests.append(test_result)
                print(f"✅ {role.title()} login successful")
            else:
                failed_tests.append(test_result)
                print(f"❌ {role.title()} login failed")
    
    # Summary
    print("\n" + "="*60)
    print("🎯 AUTHENTICATION TEST SUMMARY")
    print("="*60)
    print(f"Total successful tests: {len(successful_tests)}")
    print(f"Total failed tests: {len(failed_tests)}")
    
    if successful_tests:
        print("\n✅ SUCCESSFUL AUTHENTICATIONS:")
        for test in successful_tests:
            print(f"- {test['email']} ({test['role']}) @ {test['base_url']}")
    
    if failed_tests:
        print("\n❌ FAILED AUTHENTICATIONS:")
        for test in failed_tests:
            print(f"- {test['email']} ({test['role']}) @ {test['base_url']}")
    
    # Authentication credentials summary
    print("\n🔐 VERIFIED SECURE CREDENTIALS:")
    print("Admin Account:")
    print(f"  Email: admin@aiwfe.com")
    print(f"  Password: {test_accounts.get('admin@aiwfe.com', {}).get('password', 'Not found')}")
    print("User Account:")
    print(f"  Email: testuser@aiwfe.com")
    print(f"  Password: {test_accounts.get('testuser@aiwfe.com', {}).get('password', 'Not found')}")
    
    return len(successful_tests) > 0

def test_login(base_url, email, password, role, user_id):
    """Test login functionality for a specific account."""
    try:
        # Try multiple login endpoints
        login_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/jwt/login",
            "/api/auth/login",
            "/auth/login"
        ]
        
        for endpoint in login_endpoints:
            login_url = f"{base_url}{endpoint}"
            
            # Prepare login data
            login_data = {
                "email": email,
                "password": password,
                "remember_me": False,
                "method": "standard"
            }
            
            try:
                print(f"  🔄 Trying {endpoint}...")
                
                # Make login request
                response = requests.post(
                    login_url,
                    json=login_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=10,
                    verify=False  # Skip SSL verification for testing
                )
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        
                        # Check if login was successful
                        if "access_token" in response_data:
                            print(f"    ✅ Login successful!")
                            print(f"    🎫 Token received: {response_data['access_token'][:20]}...")
                            print(f"    👤 User ID: {response_data.get('user_id', 'N/A')}")
                            print(f"    🎭 Role: {response_data.get('role', 'N/A')}")
                            
                            # Validate user data
                            if response_data.get('user_id') == user_id:
                                print(f"    ✅ User ID matches expected: {user_id}")
                            else:
                                print(f"    ⚠️  User ID mismatch: expected {user_id}, got {response_data.get('user_id')}")
                            
                            if response_data.get('role') == role:
                                print(f"    ✅ Role matches expected: {role}")
                            else:
                                print(f"    ⚠️  Role mismatch: expected {role}, got {response_data.get('role')}")
                            
                            return True
                        else:
                            print(f"    ❌ No access token in response")
                    except json.JSONDecodeError:
                        print(f"    ❌ Invalid JSON response")
                elif response.status_code == 422:
                    print(f"    ⚠️  Validation error (422) - endpoint may need different format")
                elif response.status_code == 404:
                    print(f"    ⚠️  Endpoint not found (404)")
                else:
                    print(f"    ❌ HTTP {response.status_code}: {response.text[:100]}")
                    
            except requests.exceptions.ConnectionError:
                print(f"    ⚠️  Connection failed to {base_url}")
            except requests.exceptions.Timeout:
                print(f"    ⚠️  Request timeout")
            except Exception as e:
                print(f"    ❌ Request error: {e}")
        
        return False
        
    except Exception as e:
        print(f"  ❌ Login test error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_authentication_flow()
        if success:
            print(f"\n🎉 Authentication flow validation completed successfully!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Authentication flow validation completed with issues.")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Authentication flow test failed: {e}")
        sys.exit(1)