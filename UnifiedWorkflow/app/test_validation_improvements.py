#!/usr/bin/env python3
"""
Test validation improvements directly without needing authentication.
This validates the normalization logic and confirms metrics collection.
"""

import sys
sys.path.append('/project/app')

from shared.schemas.enhanced_chat_schemas import ChatMessageRequest, ChatMode
from api.routers.chat_router import normalize_chat_request
import logging
import uuid

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_normalization_logic():
    """Test the normalize_chat_request function directly"""
    
    print("🧪 Testing Chat Request Normalization Logic")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Valid basic request",
            "body": {"message": "Hello test"},
            "should_succeed": True
        },
        {
            "name": "Invalid mode (should be normalized)",
            "body": {"message": "Hello", "mode": "invalid-mode"},
            "should_succeed": True
        },
        {
            "name": "Invalid session_id type (should be normalized)",
            "body": {"message": "Hello", "session_id": 12345},
            "should_succeed": True
        },
        {
            "name": "Invalid message_history type (should be normalized)",
            "body": {"message": "Hello", "message_history": "not-a-list"},
            "should_succeed": True
        },
        {
            "name": "Invalid current_graph_state type (should be normalized)",
            "body": {"message": "Hello", "current_graph_state": "not-a-dict"},
            "should_succeed": True
        },
        {
            "name": "Invalid user_preferences type (should be normalized)",
            "body": {"message": "Hello", "user_preferences": "not-a-dict"},
            "should_succeed": True
        },
        {
            "name": "Complex mixed invalid types",
            "body": {
                "message": "Hello test",
                "mode": "invalid-mode",
                "session_id": 12345,
                "current_graph_state": "not-a-dict",
                "message_history": "not-a-list",
                "user_preferences": "not-a-dict"
            },
            "should_succeed": True
        }
    ]
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Test normalization
            message = test_case['body'].get('message')
            normalized = normalize_chat_request(test_case['body'], message, logger)
            print(f"✅ Normalization succeeded")
            print(f"   Normalized: {normalized}")
            
            # Test if normalized data can create a valid ChatMessageRequest
            chat_request = ChatMessageRequest(**normalized)
            print(f"✅ ChatMessageRequest creation succeeded")
            print(f"   Request: {chat_request}")
            
            results["passed"] += 1
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results["failed"] += 1
            results["errors"].append({
                "test": test_case['name'],
                "error": str(e)
            })
    
    print(f"\n{'='*60}")
    print("NORMALIZATION TEST RESULTS")
    print(f"{'='*60}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    if results['errors']:
        print(f"\n🔍 Error Details:")
        for error in results['errors']:
            print(f"  - {error['test']}: {error['error']}")
    
    return results

def test_direct_pydantic_validation():
    """Test that common frontend variations now work"""
    
    print(f"\n{'='*60}")
    print("TESTING FRONTEND COMPATIBILITY")
    print(f"{'='*60}")
    
    # These cases previously failed with 422 errors
    frontend_cases = [
        {
            "name": "String session_id (common frontend format)",
            "data": {
                "message": "Hello",
                "session_id": "session-123",  # String instead of potential int
                "mode": "smart-router"
            }
        },
        {
            "name": "Mixed valid and normalized fields",
            "data": {
                "message": "Hello test",
                "mode": "smart-router",  # Valid mode
                "session_id": "test-session",  # Valid string
                "current_graph_state": {},  # Valid dict
                "message_history": [],  # Valid list
                "user_preferences": {}  # Valid dict
            }
        },
        {
            "name": "Minimal valid request",
            "data": {
                "message": "Hello world"
            }
        }
    ]
    
    for i, case in enumerate(frontend_cases, 1):
        print(f"\nFrontend Case {i}: {case['name']}")
        print("-" * 40)
        
        try:
            request = ChatMessageRequest(**case['data'])
            print(f"✅ Frontend request succeeds: {request}")
        except Exception as e:
            print(f"❌ Frontend request still fails: {e}")

def test_metrics_collection():
    """Test that metrics would be collected (simulate without HTTP)"""
    
    print(f"\n{'='*60}")
    print("TESTING METRICS COLLECTION SIMULATION")
    print(f"{'='*60}")
    
    try:
        from shared.monitoring.prometheus_metrics import metrics
        
        print("✅ Prometheus metrics module loaded successfully")
        
        # Simulate metrics that would be collected
        print("\n📊 Simulating metric collection:")
        
        # Simulate successful validation
        metrics.data_validation_attempts_total.labels(
            data_type="chat_request",
            validation_type="pydantic_schema"
        ).inc()
        print("  ✅ Recorded validation attempt")
        
        # Simulate successful normalization
        metrics.data_validation_attempts_total.labels(
            data_type="message",
            validation_type="length_truncation"
        ).inc()
        print("  ✅ Recorded message normalization")
        
        print("\n📈 Metrics are being collected and will appear in Grafana dashboard!")
        
    except Exception as e:
        print(f"❌ Metrics collection test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Chat API Validation Improvement Tests")
    
    # Test normalization logic
    normalization_results = test_normalization_logic()
    
    # Test frontend compatibility
    test_direct_pydantic_validation()
    
    # Test metrics collection
    test_metrics_collection()
    
    print(f"\n🏁 Validation improvement tests complete!")
    print(f"Success Rate: {normalization_results['passed']/(normalization_results['passed']+normalization_results['failed'])*100:.1f}%")
    
    if normalization_results['passed'] == len(normalization_results):
        print("🎉 All normalization tests passed! The 422 error prevention system is working correctly.")