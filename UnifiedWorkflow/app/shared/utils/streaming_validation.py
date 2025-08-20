"""
Validation script for testing streaming endpoints and ensuring SSE compliance.
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .streaming_utils import (
    format_sse_data, format_sse_error, format_sse_info, 
    format_sse_content, format_sse_final, SSEValidator
)

logger = logging.getLogger(__name__)


class StreamingResponseValidator:
    """Validator for streaming response integrity."""
    
    def __init__(self):
        self.validator = SSEValidator()
        self.validation_errors = []
        self.warnings = []
    
    def validate_streaming_response(self, sse_responses: List[str]) -> Dict[str, Any]:
        """
        Validate a list of SSE responses for format compliance and content integrity.
        
        Args:
            sse_responses: List of SSE formatted response strings
            
        Returns:
            Dictionary containing validation results
        """
        results = {
            "total_responses": len(sse_responses),
            "valid_responses": 0,
            "invalid_responses": 0,
            "errors": [],
            "warnings": [],
            "event_types": {},
            "response_sizes": [],
            "validation_passed": True
        }
        
        for i, response in enumerate(sse_responses):
            response_result = self._validate_single_response(response, i)
            
            if response_result["valid"]:
                results["valid_responses"] += 1
                
                # Track event types
                event_type = response_result.get("event_type")
                if event_type:
                    results["event_types"][event_type] = results["event_types"].get(event_type, 0) + 1
                
                # Track response size
                results["response_sizes"].append(len(response))
            else:
                results["invalid_responses"] += 1
                results["validation_passed"] = False
                results["errors"].extend(response_result["errors"])
            
            results["warnings"].extend(response_result["warnings"])
        
        # Calculate statistics
        if results["response_sizes"]:
            results["avg_response_size"] = sum(results["response_sizes"]) / len(results["response_sizes"])
            results["max_response_size"] = max(results["response_sizes"])
            results["min_response_size"] = min(results["response_sizes"])
        
        return results
    
    def _validate_single_response(self, response: str, index: int) -> Dict[str, Any]:
        """Validate a single SSE response."""
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "event_type": None
        }
        
        # Check SSE format
        if not self.validator.validate_sse_format(response):
            result["valid"] = False
            result["errors"].append(f"Response {index}: Invalid SSE format")
            return result
        
        # Extract and parse JSON
        try:
            json_part = response[6:-2]  # Remove "data: " and "\n\n"
            event_data = json.loads(json_part)
            result["event_type"] = event_data.get("type")
            
            # Validate event structure
            if not self.validator.validate_event_structure(event_data):
                result["valid"] = False
                result["errors"].append(f"Response {index}: Invalid event structure")
            
            # Check for required fields based on event type
            validation_result = self._validate_event_content(event_data, index)
            result["errors"].extend(validation_result["errors"])
            result["warnings"].extend(validation_result["warnings"])
            
            if validation_result["errors"]:
                result["valid"] = False
                
        except json.JSONDecodeError as e:
            result["valid"] = False
            result["errors"].append(f"Response {index}: JSON decode error: {e}")
        
        return result
    
    def _validate_event_content(self, event_data: dict, index: int) -> Dict[str, List[str]]:
        """Validate event content based on event type."""
        errors = []
        warnings = []
        
        event_type = event_data.get("type")
        
        # Content validation based on event type
        if event_type in ["content", "info", "expert_response"]:
            content = event_data.get("content")
            if not content:
                warnings.append(f"Response {index}: Empty content for {event_type} event")
            elif not isinstance(content, str):
                errors.append(f"Response {index}: Content should be string for {event_type} event")
        
        # Metadata validation
        if event_type == "final":
            if "session_id" not in event_data:
                errors.append(f"Response {index}: Missing session_id in final event")
            if "mode" not in event_data:
                errors.append(f"Response {index}: Missing mode in final event")
        
        # Expert response validation
        if event_type == "expert_response":
            if "expert" not in event_data and "expert" not in event_data.get("metadata", {}):
                warnings.append(f"Response {index}: Missing expert field in expert_response")
            if "expert_id" not in event_data and "expert_id" not in event_data.get("metadata", {}):
                warnings.append(f"Response {index}: Missing expert_id field in expert_response")
        
        # Timestamp validation
        if "timestamp" in event_data:
            try:
                datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))
            except ValueError:
                warnings.append(f"Response {index}: Invalid timestamp format")
        
        return {"errors": errors, "warnings": warnings}


def test_streaming_utilities():
    """Test the streaming utility functions."""
    test_results = {
        "format_sse_data": [],
        "format_sse_error": [],
        "format_sse_content": [],
        "format_sse_final": []
    }
    
    # Test format_sse_data
    try:
        sse_data = format_sse_data("test", "Hello world", extra_field="test")
        validator = SSEValidator()
        if validator.validate_sse_format(sse_data):
            test_results["format_sse_data"].append("PASS: Basic formatting")
        else:
            test_results["format_sse_data"].append("FAIL: Basic formatting")
    except Exception as e:
        test_results["format_sse_data"].append(f"FAIL: Exception - {e}")
    
    # Test format_sse_error
    try:
        sse_error = format_sse_error("Test error message")
        validator = SSEValidator()
        if validator.validate_sse_format(sse_error):
            test_results["format_sse_error"].append("PASS: Error formatting")
        else:
            test_results["format_sse_error"].append("FAIL: Error formatting")
    except Exception as e:
        test_results["format_sse_error"].append(f"FAIL: Exception - {e}")
    
    # Test format_sse_content
    try:
        sse_content = format_sse_content("Sample content with special chars: \n\t\"quotes\"")
        validator = SSEValidator()
        if validator.validate_sse_format(sse_content):
            test_results["format_sse_content"].append("PASS: Content formatting")
        else:
            test_results["format_sse_content"].append("FAIL: Content formatting")
    except Exception as e:
        test_results["format_sse_content"].append(f"FAIL: Exception - {e}")
    
    # Test format_sse_final
    try:
        sse_final = format_sse_final("test-session", "expert_group", tokens={"total": 100})
        validator = SSEValidator()
        if validator.validate_sse_format(sse_final):
            test_results["format_sse_final"].append("PASS: Final formatting")
        else:
            test_results["format_sse_final"].append("FAIL: Final formatting")
    except Exception as e:
        test_results["format_sse_final"].append(f"FAIL: Exception - {e}")
    
    return test_results


def run_streaming_validation_tests():
    """Run all streaming validation tests."""
    logger.info("Starting streaming validation tests...")
    
    # Test utility functions
    utility_results = test_streaming_utilities()
    logger.info(f"Utility test results: {utility_results}")
    
    # Test validator with sample responses
    validator = StreamingResponseValidator()
    
    sample_responses = [
        format_sse_data("info", "Starting process..."),
        format_sse_content("This is streaming content"),
        format_sse_data("expert_response", "Expert analysis here", expert="Technical Expert", expert_id="tech"),
        format_sse_final("session-123", "expert_group", total_experts=3),
        format_sse_error("Sample error message", "test_error")
    ]
    
    validation_results = validator.validate_streaming_response(sample_responses)
    logger.info(f"Validation results: {validation_results}")
    
    # Check if all tests passed
    all_passed = (
        validation_results["validation_passed"] and
        all("PASS" in result for results in utility_results.values() for result in results)
    )
    
    logger.info(f"All streaming validation tests passed: {all_passed}")
    
    return {
        "utility_tests": utility_results,
        "validation_results": validation_results,
        "all_passed": all_passed
    }


if __name__ == "__main__":
    # Run tests if script is executed directly
    import sys
    logging.basicConfig(level=logging.INFO)
    
    results = run_streaming_validation_tests()
    
    if results["all_passed"]:
        print("✅ All streaming validation tests passed!")
        sys.exit(0)
    else:
        print("❌ Some streaming validation tests failed!")
        print(f"Results: {results}")
        sys.exit(1)