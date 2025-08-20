#!/usr/bin/env python3
"""
Test script to identify Chat API 422 errors.
This script will:
1. Create a test user with proper JWT token
2. Test various request formats to identify validation issues
3. Reproduce the 422 error pattern
"""

import json
import requests
import jwt
from datetime import datetime, timedelta
import uuid
import sys
import os

# Add the app directory to sys.path so we can import our modules
sys.path.append('/home/marku/ai_workflow_engine/app')

def create_test_jwt_token():
    """Create a valid JWT token for testing"""
    from api.auth import SECRET_KEY, ALGORITHM
    
    # Use a real user from the database - user ID 24, test@example.com
    payload = {
        "sub": "test@example.com",  # Legacy format
        "id": 24,
        "email": "test@example.com", 
        "role": "user",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def test_chat_endpoint(token, request_data, endpoint=""):
    """Test the chat endpoint with given request data"""
    url = f"http://localhost:8000/api/v1/chat{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n=== Testing {url} ===")
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=request_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 422:
            print("🚨 FOUND 422 ERROR!")
            try:
                error_detail = response.json()
                print(f"Error Detail: {json.dumps(error_detail, indent=2)}")
            except:
                print("Could not parse error response as JSON")
        
        return response
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def main():
    """Main test runner"""
    print("🧪 Starting Chat API 422 Error Investigation")
    
    # Test different request formats that might cause 422 errors
    test_cases = [
        # Case 1: Basic message (should work)
        {
            "name": "Basic message",
            "data": {"message": "Hello test"},
            "endpoint": "/"
        },
        
        # Case 2: Missing message field (should cause 400, not 422)
        {
            "name": "Missing message",
            "data": {},
            "endpoint": "/"
        },
        
        # Case 3: Invalid mode (should trigger 422 if validation is strict)
        {
            "name": "Invalid mode",
            "data": {
                "message": "Hello test",
                "mode": "invalid-mode"
            },
            "endpoint": "/"
        },
        
        # Case 4: Invalid session_id type (should trigger 422)
        {
            "name": "Invalid session_id type",
            "data": {
                "message": "Hello test",
                "session_id": 12345  # should be string
            },
            "endpoint": "/"
        },
        
        # Case 5: Invalid message_history format (should trigger 422)
        {
            "name": "Invalid message_history format",
            "data": {
                "message": "Hello test",
                "message_history": "invalid"  # should be list
            },
            "endpoint": "/"
        },
        
        # Case 6: Invalid current_graph_state format (should trigger 422)
        {
            "name": "Invalid current_graph_state format",
            "data": {
                "message": "Hello test",
                "current_graph_state": "invalid"  # should be dict
            },
            "endpoint": "/"
        },
        
        # Case 7: Very long message (should trigger 422 if max_length validation)
        {
            "name": "Very long message",
            "data": {
                "message": "x" * 10001  # Exceeds max_length=10000
            },
            "endpoint": "/"
        },
        
        # Case 8: Empty message (should trigger 422 if min_length validation)
        {
            "name": "Empty message",
            "data": {
                "message": ""
            },
            "endpoint": "/"
        },
        
        # Case 9: Test structured endpoint directly
        {
            "name": "Structured endpoint - valid",
            "data": {
                "message": "Hello test",
                "session_id": str(uuid.uuid4()),
                "mode": "smart-router"
            },
            "endpoint": "/structured"
        },
        
        # Case 10: Test structured endpoint with invalid data
        {
            "name": "Structured endpoint - invalid",
            "data": {
                "message": "Hello test",
                "mode": "invalid-mode",
                "current_graph_state": "not-a-dict"
            },
            "endpoint": "/structured"
        }
    ]
    
    # We can't create a real test user without database access
    # But we can create a valid JWT token for testing
    try:
        token = create_test_jwt_token()
        print(f"✅ Created test JWT token")
    except Exception as e:
        print(f"❌ Failed to create JWT token: {e}")
        return
    
    # Run all test cases
    error_422_found = False
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        response = test_chat_endpoint(
            token, 
            test_case['data'], 
            test_case.get('endpoint', '/')
        )
        
        if response and response.status_code == 422:
            error_422_found = True
    
    if error_422_found:
        print("\n🎯 Found 422 validation errors! Check the output above for details.")
    else:
        print("\n✅ No 422 errors found in test cases.")
    
    print("\n🏁 Chat API investigation complete!")

if __name__ == "__main__":
    main()