#!/usr/bin/env python3
"""
Test the improved chat API with 422 error prevention and monitoring.
"""

import sys
sys.path.append('/project/app')

import json
import requests
import jwt
from datetime import datetime, timedelta
import uuid

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

def test_improved_chat_api():
    """Test the improved chat API with various validation scenarios"""
    
    print("🚀 Testing Improved Chat API with 422 Error Prevention")
    
    try:
        token = create_test_jwt_token()
        print(f"✅ Created test JWT token")
    except Exception as e:
        print(f"❌ Failed to create JWT token: {e}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_cases = [
        {
            "name": "Valid basic request",
            "data": {"message": "Hello, this is a test message"},
            "expect_success": True
        },
        {
            "name": "Invalid mode (should be normalized)",
            "data": {"message": "Hello", "mode": "invalid-mode"},
            "expect_success": True  # Should succeed with normalization
        },
        {
            "name": "Invalid session_id type (should be normalized)",
            "data": {"message": "Hello", "session_id": 12345},
            "expect_success": True  # Should succeed with normalization
        },
        {
            "name": "Invalid message_history type (should be normalized)",
            "data": {"message": "Hello", "message_history": "not-a-list"},
            "expect_success": True  # Should succeed with normalization
        },
        {
            "name": "Invalid current_graph_state type (should be normalized)",
            "data": {"message": "Hello", "current_graph_state": "not-a-dict"},
            "expect_success": True  # Should succeed with normalization
        },
        {
            "name": "Very long message (should be truncated)",
            "data": {"message": "x" * 15000},  # Longer than 10000 limit
            "expect_success": True  # Should succeed with truncation
        },
        {
            "name": "Invalid user_preferences type (should be normalized)",
            "data": {"message": "Hello", "user_preferences": "not-a-dict"},
            "expect_success": True  # Should succeed with normalization
        },
        {
            "name": "Complex mixed invalid types",
            "data": {
                "message": "Hello test",
                "mode": "invalid-mode",
                "session_id": 12345,
                "current_graph_state": "not-a-dict",
                "message_history": "not-a-list",
                "user_preferences": "not-a-dict"
            },
            "expect_success": True  # Should succeed with full normalization
        },
        {
            "name": "Empty message (should fail)",
            "data": {"message": ""},
            "expect_success": False  # Should fail with 400
        },
        {
            "name": "Missing message (should fail)",
            "data": {"session_id": "test"},
            "expect_success": False  # Should fail with 400
        }
    ]
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Expected Success: {test_case['expect_success']}")
        print(f"{'='*60}")
        
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/chat/",
                headers=headers,
                json=test_case['data'],
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            if test_case['expect_success']:
                if response.status_code == 200:
                    print("✅ Test PASSED - Request succeeded as expected")
                    try:
                        resp_data = response.json()
                        print(f"Response: {json.dumps(resp_data, indent=2)}")
                    except:
                        print("Response body could not be parsed as JSON")
                    results["passed"] += 1
                else:
                    print(f"❌ Test FAILED - Expected success but got {response.status_code}")
                    print(f"Response: {response.text}")
                    results["failed"] += 1
                    results["errors"].append({
                        "test": test_case['name'],
                        "expected": "success",
                        "actual": f"status {response.status_code}",
                        "response": response.text
                    })
            else:
                if 400 <= response.status_code < 500:
                    print("✅ Test PASSED - Request failed as expected")
                    results["passed"] += 1
                else:
                    print(f"❌ Test FAILED - Expected 4xx error but got {response.status_code}")
                    print(f"Response: {response.text}")
                    results["failed"] += 1
                    results["errors"].append({
                        "test": test_case['name'],
                        "expected": "4xx error",
                        "actual": f"status {response.status_code}",
                        "response": response.text
                    })
                    
        except Exception as e:
            print(f"❌ Test FAILED with exception: {e}")
            results["failed"] += 1
            results["errors"].append({
                "test": test_case['name'],
                "expected": "success" if test_case['expect_success'] else "4xx error",
                "actual": f"exception: {e}",
                "response": ""
            })
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📊 Success Rate: {results['passed']/(results['passed']+results['failed'])*100:.1f}%")
    
    if results['errors']:
        print(f"\n🔍 Error Details:")
        for error in results['errors']:
            print(f"  - {error['test']}: Expected {error['expected']}, got {error['actual']}")
    
    return results

if __name__ == "__main__":
    test_results = test_improved_chat_api()
    print(f"\n🏁 Improved Chat API test complete!")
    print(f"Success Rate: {test_results['passed']/(test_results['passed']+test_results['failed'])*100:.1f}%")