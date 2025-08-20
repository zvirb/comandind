#!/usr/bin/env python3
"""
Internal API test to bypass external network issues.
This tests the chat API from inside the container.
"""

import sys
sys.path.append('/project/app')

import asyncio
import json
from fastapi.testclient import TestClient
from api.main import app
from api.auth import create_access_token
from shared.database.models import User, UserRole

def create_test_token():
    """Create test token for user ID 24"""
    token_data = {
        "sub": "test@example.com",
        "id": 24,
        "email": "test@example.com",
        "role": "user"
    }
    return create_access_token(data=token_data)

def test_chat_validation():
    """Test chat endpoint validation with various invalid inputs"""
    
    client = TestClient(app)
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🧪 Testing Chat API validation with internal TestClient")
    print(f"✅ Created test token: {token[:30]}...")
    
    test_cases = [
        {
            "name": "Valid basic request",
            "data": {"message": "Hello test"},
            "expect_422": False
        },
        {
            "name": "Invalid mode enum",
            "data": {"message": "Hello", "mode": "invalid-mode"},
            "expect_422": True
        },
        {
            "name": "Invalid session_id type",
            "data": {"message": "Hello", "session_id": 12345},
            "expect_422": True
        },
        {
            "name": "Invalid message_history type",
            "data": {"message": "Hello", "message_history": "not-a-list"},
            "expect_422": True
        },
        {
            "name": "Invalid current_graph_state type",
            "data": {"message": "Hello", "current_graph_state": "not-a-dict"},
            "expect_422": True
        },
        {
            "name": "Empty message (min_length validation)",
            "data": {"message": ""},
            "expect_422": True
        },
        {
            "name": "Very long message (max_length validation)",
            "data": {"message": "x" * 10001},
            "expect_422": True
        },
        {
            "name": "Invalid user_preferences type",
            "data": {"message": "Hello", "user_preferences": "not-a-dict"},
            "expect_422": True
        }
    ]
    
    found_422_errors = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Expected 422: {test_case['expect_422']}")
        print(f"{'='*60}")
        
        try:
            response = client.post(
                "/api/v1/chat/",
                headers=headers,
                json=test_case['data']
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 422:
                print("🚨 FOUND 422 ERROR!")
                try:
                    error_detail = response.json()
                    print(f"Error Detail: {json.dumps(error_detail, indent=2)}")
                    found_422_errors.append({
                        "test": test_case['name'],
                        "error": error_detail
                    })
                except:
                    print("Could not parse 422 error response")
                    found_422_errors.append({
                        "test": test_case['name'],
                        "error": response.text
                    })
            else:
                print(f"Response: {response.text[:200]}...")
                
                if test_case['expect_422'] and response.status_code != 422:
                    print(f"⚠️  Expected 422 but got {response.status_code}")
                elif not test_case['expect_422'] and response.status_code == 422:
                    print(f"⚠️  Unexpected 422 error!")
                    found_422_errors.append({
                        "test": test_case['name'],
                        "error": response.text
                    })
                    
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    if found_422_errors:
        print(f"🎯 Found {len(found_422_errors)} validation errors:")
        for error in found_422_errors:
            print(f"  - {error['test']}")
            
        print("\n📋 Detailed error analysis:")
        for error in found_422_errors:
            print(f"\n🔍 {error['test']}:")
            if isinstance(error['error'], dict):
                print(json.dumps(error['error'], indent=2))
            else:
                print(error['error'])
    else:
        print("✅ No 422 validation errors found")
    
    return found_422_errors

if __name__ == "__main__":
    validation_errors = test_chat_validation()
    print(f"\n🏁 API validation test complete! Found {len(validation_errors)} issues.")