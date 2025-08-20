#!/usr/bin/env python3
"""
Direct validation test to identify 422 patterns without running the full app.
"""

import sys
sys.path.append('/project/app')

from pydantic import ValidationError
from shared.schemas.enhanced_chat_schemas import ChatMessageRequest, ChatMode

def test_pydantic_validation():
    """Test ChatMessageRequest validation directly"""
    
    print("🧪 Testing ChatMessageRequest Pydantic validation")
    
    test_cases = [
        {
            "name": "Valid basic request",
            "data": {"message": "Hello test"},
            "should_fail": False
        },
        {
            "name": "Valid with all fields",
            "data": {
                "message": "Hello test",
                "session_id": "test-session",
                "mode": "smart-router",
                "current_graph_state": {},
                "message_history": [],
                "user_preferences": {}
            },
            "should_fail": False
        },
        {
            "name": "Invalid mode enum",
            "data": {"message": "Hello", "mode": "invalid-mode"},
            "should_fail": True
        },
        {
            "name": "Invalid session_id type",
            "data": {"message": "Hello", "session_id": 12345},
            "should_fail": True
        },
        {
            "name": "Invalid message_history type",
            "data": {"message": "Hello", "message_history": "not-a-list"},
            "should_fail": True
        },
        {
            "name": "Invalid current_graph_state type",
            "data": {"message": "Hello", "current_graph_state": "not-a-dict"},
            "should_fail": True
        },
        {
            "name": "Empty message (min_length validation)",
            "data": {"message": ""},
            "should_fail": True
        },
        {
            "name": "Very long message (max_length validation)",
            "data": {"message": "x" * 10001},
            "should_fail": True
        },
        {
            "name": "Invalid user_preferences type",
            "data": {"message": "Hello", "user_preferences": "not-a-dict"},
            "should_fail": True
        },
        {
            "name": "Missing message field",
            "data": {"session_id": "test"},
            "should_fail": True
        },
        {
            "name": "None message",
            "data": {"message": None},
            "should_fail": True
        }
    ]
    
    validation_errors = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"Should fail: {test_case['should_fail']}")
        print(f"{'='*60}")
        
        try:
            request = ChatMessageRequest(**test_case['data'])
            print("✅ Validation passed")
            print(f"   Created: {request}")
            
            if test_case['should_fail']:
                print("⚠️  Expected validation to fail but it passed!")
                
        except ValidationError as e:
            print("🚨 Validation failed (Pydantic ValidationError)")
            print(f"   Error details: {e}")
            
            validation_errors.append({
                "test": test_case['name'],
                "error_type": "ValidationError",
                "error": str(e),
                "error_details": e.errors()
            })
            
            if not test_case['should_fail']:
                print("⚠️  Unexpected validation failure!")
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            validation_errors.append({
                "test": test_case['name'],
                "error_type": type(e).__name__,
                "error": str(e)
            })
    
    print(f"\n{'='*60}")
    print("VALIDATION ERROR ANALYSIS")
    print(f"{'='*60}")
    
    if validation_errors:
        print(f"🎯 Found {len(validation_errors)} Pydantic validation errors:")
        
        for error in validation_errors:
            print(f"\n🔍 {error['test']}:")
            print(f"   Error Type: {error['error_type']}")
            print(f"   Error: {error['error']}")
            
            if 'error_details' in error:
                print("   Detailed validation errors:")
                for detail in error['error_details']:
                    print(f"     - Field: {detail.get('loc', 'unknown')}")
                    print(f"       Type: {detail.get('type', 'unknown')}")
                    print(f"       Message: {detail.get('msg', 'unknown')}")
                    print(f"       Input: {detail.get('input', 'unknown')}")
    else:
        print("✅ No validation errors found (this might indicate the validation is too permissive)")
    
    return validation_errors

def test_chat_mode_validation():
    """Test ChatMode enum validation specifically"""
    print(f"\n{'='*60}")
    print("CHATMODE ENUM VALIDATION")
    print(f"{'='*60}")
    
    valid_modes = ["smart-router", "socratic-interview", "expert-group", "direct"]
    invalid_modes = ["invalid-mode", "test", "random", "", None, 123]
    
    print("Valid modes:")
    for mode in valid_modes:
        try:
            chat_mode = ChatMode(mode)
            print(f"  ✅ {mode} -> {chat_mode}")
        except Exception as e:
            print(f"  ❌ {mode} -> {e}")
    
    print("\nInvalid modes:")
    for mode in invalid_modes:
        try:
            chat_mode = ChatMode(mode)
            print(f"  ⚠️  {mode} -> {chat_mode} (unexpected success)")
        except Exception as e:
            print(f"  ✅ {mode} -> {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("🚀 Starting direct Pydantic validation testing...")
    
    # Test enum validation
    test_chat_mode_validation()
    
    # Test full request validation
    validation_errors = test_pydantic_validation()
    
    print(f"\n🏁 Validation test complete!")
    print(f"   Found {len(validation_errors)} validation issues")
    
    if validation_errors:
        print("\n📋 Summary of validation patterns that cause 422 errors:")
        for error in validation_errors:
            print(f"   - {error['test']}: {error['error_type']}")