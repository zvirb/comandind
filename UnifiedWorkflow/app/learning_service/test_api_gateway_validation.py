#!/usr/bin/env python3
"""
API Gateway Integration Validation Tests
=======================================

Tests to validate learning service endpoints are properly configured
for API gateway routing and authentication integration.
"""

import json
import time
import requests
from typing import Dict, Any, List
from datetime import datetime

# Test Configuration  
LEARNING_SERVICE_URL = "http://localhost:8005"

class APIGatewayValidator:
    """Validator for API gateway integration readiness."""
    
    def __init__(self):
        self.base_url = LEARNING_SERVICE_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", data: Dict[Any, Any] = None):
        """Log test results."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
    
    def test_cors_headers(self) -> bool:
        """Test CORS headers for gateway integration."""
        try:
            # Test preflight OPTIONS request
            response = self.session.options(
                f"{self.base_url}/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization, Content-Type"
                }
            )
            
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
                "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
            }
            
            # Check if CORS is properly configured
            has_cors = any(cors_headers.values())
            
            if has_cors:
                self.log_test(
                    "CORS Headers Configuration",
                    True,
                    f"CORS enabled for cross-origin requests",
                    cors_headers
                )
                return True
            else:
                self.log_test("CORS Headers Configuration", False, "CORS not configured", cors_headers)
                return False
                
        except Exception as e:
            self.log_test("CORS Headers Configuration", False, f"Exception: {str(e)}")
            return False
    
    def test_endpoint_routing_patterns(self) -> bool:
        """Test standard REST API routing patterns."""
        try:
            # Test standard endpoint patterns that gateways expect
            endpoints_to_test = [
                ("/", "GET", "Root endpoint"),
                ("/health", "GET", "Health check"),
                ("/learn/outcome", "POST", "Learning endpoint"),
                ("/docs", "GET", "API documentation"),
                ("/openapi.json", "GET", "OpenAPI specification")
            ]
            
            successful_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, method, description in endpoints_to_test:
                try:
                    if method == "GET":
                        response = self.session.get(f"{self.base_url}{endpoint}")
                    elif method == "POST":
                        # Use minimal valid data for POST test
                        test_data = {
                            "outcome_type": "test",
                            "service_name": "test-service",
                            "context": {}
                        }
                        response = self.session.post(
                            f"{self.base_url}{endpoint}",
                            json=test_data,
                            headers={"Content-Type": "application/json"}
                        )
                    
                    if response.status_code in [200, 201, 202]:
                        successful_endpoints += 1
                        print(f"    ✓ {endpoint} ({method}): HTTP {response.status_code}")
                    else:
                        print(f"    ✗ {endpoint} ({method}): HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"    ✗ {endpoint} ({method}): Error - {str(e)}")
            
            success_rate = (successful_endpoints / total_endpoints) * 100
            
            if success_rate >= 80:
                self.log_test(
                    "Endpoint Routing Patterns",
                    True,
                    f"{successful_endpoints}/{total_endpoints} endpoints accessible ({success_rate:.1f}%)",
                    {"successful_endpoints": successful_endpoints, "total_endpoints": total_endpoints}
                )
                return True
            else:
                self.log_test(
                    "Endpoint Routing Patterns",
                    False,
                    f"Only {successful_endpoints}/{total_endpoints} endpoints accessible ({success_rate:.1f}%)",
                    {"successful_endpoints": successful_endpoints, "total_endpoints": total_endpoints}
                )
                return False
                
        except Exception as e:
            self.log_test("Endpoint Routing Patterns", False, f"Exception: {str(e)}")
            return False
    
    def test_content_type_handling(self) -> bool:
        """Test proper content type handling for API gateway."""
        try:
            # Test JSON content type handling
            test_data = {
                "outcome_type": "success",
                "service_name": "content-type-test",
                "context": {"test": "content_type_validation"}
            }
            
            # Test with proper JSON content type
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            
            json_success = response.status_code == 200
            
            # Test response content type
            response_content_type = response.headers.get("Content-Type", "")
            json_response = "application/json" in response_content_type
            
            if json_success and json_response:
                self.log_test(
                    "Content Type Handling",
                    True,
                    f"Proper JSON handling: {response_content_type}",
                    {"request_success": json_success, "response_content_type": response_content_type}
                )
                return True
            else:
                self.log_test(
                    "Content Type Handling",
                    False,
                    f"Content type issues: request={json_success}, response={json_response}",
                    {"request_success": json_success, "response_content_type": response_content_type}
                )
                return False
                
        except Exception as e:
            self.log_test("Content Type Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_error_response_format(self) -> bool:
        """Test standardized error response format."""
        try:
            # Send invalid request to trigger error response
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json={},  # Invalid empty data
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    
                    # Check for standard error format
                    has_detail = "detail" in error_data
                    has_status = "status" in error_data
                    
                    if has_detail or has_status:
                        self.log_test(
                            "Error Response Format",
                            True,
                            f"Standard error format: HTTP {response.status_code}",
                            error_data
                        )
                        return True
                    else:
                        self.log_test(
                            "Error Response Format",
                            False,
                            f"Non-standard error format",
                            error_data
                        )
                        return False
                        
                except json.JSONDecodeError:
                    self.log_test("Error Response Format", False, "Error response not JSON")
                    return False
            else:
                self.log_test("Error Response Format", False, f"Expected error, got HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Error Response Format", False, f"Exception: {str(e)}")
            return False
    
    def test_openapi_specification(self) -> bool:
        """Test OpenAPI specification availability for gateway integration."""
        try:
            # Test OpenAPI JSON endpoint
            response = self.session.get(f"{self.base_url}/openapi.json")
            
            if response.status_code == 200:
                try:
                    openapi_spec = response.json()
                    
                    # Check for essential OpenAPI fields
                    has_openapi = "openapi" in openapi_spec
                    has_info = "info" in openapi_spec
                    has_paths = "paths" in openapi_spec
                    
                    if has_openapi and has_info and has_paths:
                        self.log_test(
                            "OpenAPI Specification",
                            True,
                            f"Valid OpenAPI spec available: v{openapi_spec.get('openapi', 'unknown')}",
                            {
                                "openapi_version": openapi_spec.get("openapi"),
                                "service_info": openapi_spec.get("info", {}),
                                "paths_count": len(openapi_spec.get("paths", {}))
                            }
                        )
                        return True
                    else:
                        self.log_test(
                            "OpenAPI Specification",
                            False,
                            "Invalid OpenAPI specification",
                            {"has_openapi": has_openapi, "has_info": has_info, "has_paths": has_paths}
                        )
                        return False
                        
                except json.JSONDecodeError:
                    self.log_test("OpenAPI Specification", False, "OpenAPI response not valid JSON")
                    return False
            else:
                self.log_test("OpenAPI Specification", False, f"OpenAPI not available: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("OpenAPI Specification", False, f"Exception: {str(e)}")
            return False
    
    def test_authentication_ready_headers(self) -> bool:
        """Test that service can handle authentication headers from gateway."""
        try:
            # Test with common authentication headers that gateways add
            auth_headers = {
                "Authorization": "Bearer mock-jwt-token",
                "X-User-ID": "test-user-123",
                "X-Request-ID": "test-request-456"
            }
            
            test_data = {
                "outcome_type": "success",
                "service_name": "auth-header-test",
                "context": {"test": "authentication_headers"}
            }
            
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=test_data,
                headers={**auth_headers, "Content-Type": "application/json"}
            )
            
            # Service should handle auth headers gracefully (not reject them)
            if response.status_code == 200:
                self.log_test(
                    "Authentication Header Handling",
                    True,
                    "Service accepts authentication headers from gateway",
                    {"response_status": response.status_code}
                )
                return True
            else:
                self.log_test(
                    "Authentication Header Handling",
                    False,
                    f"Service rejected request with auth headers: HTTP {response.status_code}",
                    {"response_status": response.status_code}
                )
                return False
                
        except Exception as e:
            self.log_test("Authentication Header Handling", False, f"Exception: {str(e)}")
            return False
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all API gateway integration validations."""
        print(f"\n{'='*60}")
        print("API GATEWAY INTEGRATION VALIDATION")
        print(f"Learning Service: {self.base_url}")
        print(f"{'='*60}\n")
        
        # Validation sequence
        validations = [
            ("CORS Configuration", self.test_cors_headers),
            ("Endpoint Routing", self.test_endpoint_routing_patterns),
            ("Content Type Handling", self.test_content_type_handling),
            ("Error Response Format", self.test_error_response_format),
            ("OpenAPI Specification", self.test_openapi_specification),
            ("Authentication Headers", self.test_authentication_ready_headers)
        ]
        
        passed = 0
        total = len(validations)
        
        for validation_name, validation_func in validations:
            try:
                if validation_func():
                    passed += 1
                print()  # Add spacing between validations
            except Exception as e:
                self.log_test(validation_name, False, f"Validation execution failed: {str(e)}")
                print()
        
        # Summary
        success_rate = (passed / total) * 100
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Validations Passed: {passed}/{total} ({success_rate:.1f}%)")
        print(f"Gateway Integration Ready: {'YES' if success_rate >= 80 else 'NEEDS WORK'}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        # Return comprehensive results
        return {
            "summary": {
                "total_validations": total,
                "passed_validations": passed,
                "success_rate": success_rate,
                "gateway_ready": success_rate >= 80
            },
            "detailed_results": self.test_results,
            "status": "ready" if success_rate >= 80 else "needs_work"
        }

if __name__ == "__main__":
    validator = APIGatewayValidator()
    results = validator.run_all_validations()
    
    # Save detailed results
    with open(f"/tmp/api_gateway_validation_results_{int(time.time())}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Exit with appropriate code
    exit(0 if results["summary"]["gateway_ready"] else 1)