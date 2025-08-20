#!/usr/bin/env python3
"""
Direct validation test with advanced false positive prevention using 
machine learning-assisted validation.
"""

import sys
import time
import logging
from typing import Dict, Any, List

sys.path.append('/project/app')

from pydantic import ValidationError
from shared.schemas.enhanced_chat_schemas import ChatMessageRequest, ChatMode
from advanced_validation_framework import (
    AdvancedValidationFramework, 
    ValidationStrategy, 
    ValidationRiskLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PydanticValidationTest:
    """Advanced Pydantic validation test with ML-assisted false positive prevention."""
    
    def __init__(self):
        self.validation_framework = AdvancedValidationFramework({
            'environment': 'testing',
            'version': '1.0.0'
        })
    
    async def validate_chat_request(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate chat request with advanced validation techniques.
        
        Args:
            test_case: Test case configuration
        
        Returns:
            Validation evidence with ML insights
        """
        async def validation_func():
            try:
                request = ChatMessageRequest(**test_case['data'])
                return {
                    'success': not test_case['should_fail'],
                    'request': request,
                    'layer': 'pydantic_validation'
                }
            except ValidationError as e:
                return {
                    'success': test_case['should_fail'],
                    'error': str(e),
                    'error_details': e.errors(),
                    'layer': 'pydantic_validation'
                }
        
        return await self.validation_framework.validate_with_ml_detection(
            test_name=test_case['name'],
            validation_func=validation_func,
            strategy=ValidationStrategy.STRICT,
            expected_risk_level=ValidationRiskLevel.MEDIUM
        )
    
    async def run_chat_request_validation_tests(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run advanced validation tests with ML false positive detection.
        
        Args:
            test_cases: List of test cases to validate
        
        Returns:
            List of validation evidences
        """
        validation_results = []
        
        for test_case in test_cases:
            logger.info(f"Running test: {test_case['name']}")
            start_time = time.time()
            
            evidence = await self.validate_chat_request(test_case)
            
            # Add execution time to evidence
            evidence.contextual_factors['execution_time_ms'] = int((time.time() - start_time) * 1000)
            
            validation_results.append(evidence)
            
            # Display detailed test result
            self._display_test_result(test_case, evidence)
        
        return validation_results
    
    def _display_test_result(self, test_case: Dict[str, Any], evidence: Any):
        """
        Display detailed test result with ML insights.
        
        Args:
            test_case: Original test case
            evidence: Validation evidence
        """
        print(f"\n{'='*80}")
        print(f"Test: {test_case['name']}")
        print(f"Expected Failure: {test_case['should_fail']}")
        print(f"Actual Success: {evidence.success}")
        print(f"Anomaly Probability: {evidence.anomaly_probability:.2f}")
        print(f"Risk Score: {evidence.risk_score:.2f}")
        print(f"Execution Time: {evidence.contextual_factors.get('execution_time_ms', 0)} ms")
        
        if not evidence.success:
            print("Error Details:")
            if 'error' in evidence.evidence_data:
                print(evidence.evidence_data['error'])
            if 'error_details' in evidence.evidence_data:
                for detail in evidence.evidence_data['error_details']:
                    print(f"  - Field: {detail.get('loc', 'unknown')}")
                    print(f"    Type: {detail.get('type', 'unknown')}")
                    print(f"    Message: {detail.get('msg', 'unknown')}")
                    print(f"    Input: {detail.get('input', 'unknown')}")
    
    def test_chat_mode_validation(self):
        """Test ChatMode enum validation with ML false positive detection."""
        valid_modes = ["smart-router", "socratic-interview", "expert-group", "direct"]
        invalid_modes = ["invalid-mode", "test", "random", "", None, 123]
        
        print("\nCHAT MODE ENUM VALIDATION")
        print("="*60)
        
        # Test valid modes
        for mode in valid_modes:
            try:
                chat_mode = ChatMode(mode)
                print(f"✅ {mode} -> {chat_mode}")
            except Exception as e:
                print(f"❌ {mode} -> Unexpected failure: {e}")
        
        # Test invalid modes
        for mode in invalid_modes:
            try:
                chat_mode = ChatMode(mode)
                print(f"⚠️  {mode} -> Unexpected validation success!")
            except Exception as e:
                print(f"✅ {mode} -> {type(e).__name__}: {e}")

async def main():
    """Main execution function for advanced validation testing."""
    print("🚀 Starting advanced Pydantic validation testing...")
    
    # Test case configurations
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
    
    # Initialize validation test
    validation_test = PydanticValidationTest()
    
    # Run chat mode enum validation
    validation_test.test_chat_mode_validation()
    
    # Run advanced validation tests
    validation_results = await validation_test.run_chat_request_validation_tests(test_cases)
    
    # Generate and display validation report
    validation_report = validation_test.validation_framework.generate_validation_report()
    
    print("\nVALIDATION REPORT")
    print("="*60)
    print(f"Total Tests: {validation_report['total_tests']}")
    print(f"Failed Tests: {validation_report['failed_tests']}")
    print(f"Anomalous Tests: {validation_report['anomalous_tests']}")
    print(f"Failure Rate: {validation_report['failure_rate']:.2%}")
    print(f"Anomaly Rate: {validation_report['anomaly_rate']:.2%}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())