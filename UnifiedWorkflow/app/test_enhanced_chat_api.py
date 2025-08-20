#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced Chat API 422 error fixes.
Tests various edge cases and problematic request patterns.
"""

import requests
import json
import time
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def get_auth_token() -> str:
    """Get authentication token for testing."""
    try:
        login_data = {
            "email": "markuszvirbulis@gmail.com",
            "password": "jWmlTz564SGc-Ud.pqIlKWTw"
        }
        response = requests.post(f"{BASE_URL}/auth/jwt/login", json=login_data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Failed to get auth token: {e}")
        raise

def test_chat_endpoint(endpoint: str, payload: Dict[str, Any], token: str, test_name: str) -> Dict[str, Any]:
    """Test a chat endpoint with given payload."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Testing {test_name}: {endpoint}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(f"{API_BASE}{endpoint}", json=payload, headers=headers)
        
        result = {
            "test_name": test_name,
            "endpoint": endpoint,
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response_data": None,
            "error": None,
            "headers": dict(response.headers)
        }
        
        try:
            result["response_data"] = response.json()
        except:
            result["response_data"] = response.text
        
        if not result["success"]:
            result["error"] = result["response_data"]
        
        logger.info(f"✅ {test_name}: Status {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"❌ {test_name} failed: {result['error']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ {test_name} exception: {e}")
        return {
            "test_name": test_name,
            "endpoint": endpoint,
            "status_code": 500,
            "success": False,
            "error": str(e),
            "response_data": None,
            "headers": {}
        }

def run_comprehensive_tests():
    """Run comprehensive test suite for chat API enhancements."""
    
    logger.info("🚀 Starting comprehensive Chat API 422 error fix tests")
    
    # Get authentication token
    try:
        token = get_auth_token()
        logger.info("✅ Authentication token obtained")
    except Exception as e:
        logger.error(f"❌ Failed to get token: {e}")
        return
    
    # Test cases covering various problematic scenarios
    test_cases = [
        {
            "name": "Basic valid request",
            "endpoint": "/chat/",
            "payload": {"message": "Hello, test message"}
        },
        {
            "name": "Invalid mode normalization",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test invalid mode",
                "mode": "SMART_ROUTER"  # Should normalize to smart-router
            }
        },
        {
            "name": "Mode variations normalization", 
            "endpoint": "/chat/",
            "payload": {
                "message": "Test mode variations",
                "mode": "expert_group"  # Should normalize to expert-group
            }
        },
        {
            "name": "Non-string session_id",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test numeric session ID",
                "session_id": 12345
            }
        },
        {
            "name": "JSON string current_graph_state",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test JSON string state",
                "current_graph_state": "{\"test\": \"value\", \"nested\": {\"key\": \"data\"}}"
            }
        },
        {
            "name": "JSON string message_history",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test JSON string history",
                "message_history": "[{\"role\": \"user\", \"content\": \"previous message\"}]"
            }
        },
        {
            "name": "Invalid JSON string handling",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test invalid JSON",
                "current_graph_state": "invalid-json-{"
            }
        },
        {
            "name": "Mixed type coercion",
            "endpoint": "/chat/",
            "payload": {
                "message": "Mixed types test",
                "mode": "socraticinterview",  # Should normalize
                "session_id": 99999,
                "current_graph_state": "{}",
                "message_history": "[]",
                "user_preferences": "{\"model\": \"llama3.2:3b\"}"
            }
        },
        {
            "name": "Alternative query field",
            "endpoint": "/chat/",
            "payload": {
                "query": "Using query field instead of message",
                "mode": "direct"
            }
        },
        {
            "name": "Null values handling",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test null values",
                "session_id": None,
                "mode": None,
                "current_graph_state": None,
                "message_history": None,
                "user_preferences": None
            }
        },
        {
            "name": "Extra fields tolerance",
            "endpoint": "/chat/",
            "payload": {
                "message": "Test extra fields",
                "extra_field_1": "should be ignored",
                "extra_field_2": {"nested": "object"},
                "mode": "smart-router"
            }
        },
        {
            "name": "Structured endpoint valid",
            "endpoint": "/chat/structured",
            "payload": {
                "message": "Test structured endpoint",
                "mode": "smart-router"
            }
        },
        {
            "name": "Structured endpoint invalid mode",
            "endpoint": "/chat/structured", 
            "payload": {
                "message": "Test structured with invalid mode",
                "mode": "invalid-mode"
            }
        },
        {
            "name": "Enhanced endpoint test",
            "endpoint": "/chat/enhanced",
            "payload": {
                "message": "Test enhanced endpoint",
                "mode": "smart-router"
            }
        },
        {
            "name": "Very long message (within limit)",
            "endpoint": "/chat/",
            "payload": {
                "message": "A" * 5000,  # 5000 chars, within 10000 limit
                "mode": "smart-router"
            }
        }
    ]
    
    # Run all tests
    results = []
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        result = test_chat_endpoint(
            test_case["endpoint"],
            test_case["payload"], 
            token,
            test_case["name"]
        )
        results.append(result)
        
        if result["success"]:
            passed += 1
        else:
            failed += 1
        
        # Small delay between tests
        time.sleep(0.1)
    
    # Print summary
    logger.info(f"\n🎯 TEST SUMMARY:")
    logger.info(f"✅ Passed: {passed}/{len(test_cases)}")
    logger.info(f"❌ Failed: {failed}/{len(test_cases)}")
    
    if failed > 0:
        logger.info(f"\n❌ FAILED TESTS:")
        for result in results:
            if not result["success"]:
                logger.info(f"  - {result['test_name']}: Status {result['status_code']}")
                if result["error"]:
                    logger.info(f"    Error: {result['error']}")
    
    # Validation headers check
    logger.info(f"\n🔍 VALIDATION HEADERS CHECK:")
    for result in results:
        if result["success"] and result["headers"]:
            validation_headers = {
                k: v for k, v in result["headers"].items() 
                if "validation" in k.lower() or "contract" in k.lower()
            }
            if validation_headers:
                logger.info(f"  {result['test_name']}: {validation_headers}")
    
    return results

if __name__ == "__main__":
    results = run_comprehensive_tests()
    
    # Save results to file
    with open("/tmp/chat_api_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📊 Results saved to /tmp/chat_api_test_results.json")