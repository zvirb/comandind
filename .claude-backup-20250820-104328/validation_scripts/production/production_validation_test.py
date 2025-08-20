#!/usr/bin/env python3
"""
Production Validation Test Suite
Tests the database connection pool fixes and server recovery
"""
import requests
import asyncio
import time
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

class ProductionValidationTester:
    def __init__(self):
        self.base_url = "https://aiwfe.com"
        self.results = []
    
    def test_api_health(self) -> Dict[str, Any]:
        """Test basic API health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            result = {
                "test": "API Health",
                "status": "PASS" if response.status_code == 200 else "FAIL",
                "response_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            result = {
                "test": "API Health",
                "status": "FAIL",
                "error": str(e)
            }
        self.results.append(result)
        return result
    
    def test_concurrent_health_checks(self, num_requests: int = 10) -> Dict[str, Any]:
        """Test concurrent requests to verify no connection pool exhaustion"""
        start_time = time.time()
        
        def make_request(request_id):
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=10)
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": str(e)
                }
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            responses = [f.result() for f in futures]
        
        end_time = time.time()
        successful = sum(1 for r in responses if r.get("success", False))
        
        result = {
            "test": f"Concurrent Health Checks ({num_requests} requests)",
            "status": "PASS" if successful == num_requests else "FAIL",
            "successful_requests": successful,
            "total_requests": num_requests,
            "success_rate": f"{(successful/num_requests)*100:.1f}%",
            "total_time": f"{end_time - start_time:.2f}s",
            "avg_response_time": f"{sum(r.get('response_time', 0) for r in responses if 'response_time' in r)/len([r for r in responses if 'response_time' in r]):.3f}s" if any('response_time' in r for r in responses) else "N/A"
        }
        
        self.results.append(result)
        return result
    
    def test_authentication_endpoints(self) -> Dict[str, Any]:
        """Test authentication-protected endpoints return proper auth errors (not server errors)"""
        endpoints = [
            "/api/v1/tasks",
            "/api/v1/categories"
        ]
        
        test_results = []
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                data = response.json()
                
                # Check if we get proper auth error (not server error)
                is_auth_error = (
                    response.status_code == 401 and 
                    data.get("success") == False and
                    "authentication" in data.get("error", {}).get("category", "").lower()
                )
                
                test_results.append({
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "is_proper_auth_error": is_auth_error,
                    "response_data": data
                })
                
            except Exception as e:
                test_results.append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "is_proper_auth_error": False
                })
        
        all_auth_proper = all(r.get("is_proper_auth_error", False) for r in test_results)
        
        result = {
            "test": "Authentication Endpoints",
            "status": "PASS" if all_auth_proper else "FAIL",
            "endpoints_tested": len(endpoints),
            "proper_auth_responses": sum(1 for r in test_results if r.get("is_proper_auth_error", False)),
            "details": test_results
        }
        
        self.results.append(result)
        return result
    
    def test_csrf_protection(self) -> Dict[str, Any]:
        """Test CSRF protection is working"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/google/login",
                json={},
                timeout=10
            )
            
            # Should get CSRF error, not server error
            is_csrf_protected = (
                response.status_code in [400, 403] and
                "csrf" in response.text.lower()
            )
            
            result = {
                "test": "CSRF Protection",
                "status": "PASS" if is_csrf_protected else "FAIL",
                "status_code": response.status_code,
                "csrf_protected": is_csrf_protected,
                "response": response.text[:200]
            }
            
        except Exception as e:
            result = {
                "test": "CSRF Protection",
                "status": "FAIL",
                "error": str(e)
            }
        
        self.results.append(result)
        return result
    
    def test_frontend_loading(self) -> Dict[str, Any]:
        """Test frontend loads without server error messages"""
        try:
            response = requests.get(self.base_url, timeout=15)
            content = response.text.lower()
            
            # Check for server error indicators that were reported before
            server_error_indicators = [
                "failed to fetch tasks: server error occurred",
                "using default categories",
                "server error occurred",
                "connection pool exhausted"
            ]
            
            errors_found = [error for error in server_error_indicators if error in content]
            
            result = {
                "test": "Frontend Loading",
                "status": "PASS" if not errors_found and response.status_code == 200 else "FAIL",
                "status_code": response.status_code,
                "page_size": len(response.text),
                "server_errors_found": errors_found,
                "contains_login_form": "login" in content and "password" in content
            }
            
        except Exception as e:
            result = {
                "test": "Frontend Loading",
                "status": "FAIL",
                "error": str(e)
            }
        
        self.results.append(result)
        return result
    
    def test_redis_connectivity(self) -> Dict[str, Any]:
        """Test Redis connectivity through health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            data = response.json()
            
            redis_ok = data.get("redis_connection") == "ok"
            
            result = {
                "test": "Redis Connectivity",
                "status": "PASS" if redis_ok else "FAIL",
                "redis_status": data.get("redis_connection"),
                "full_response": data
            }
            
        except Exception as e:
            result = {
                "test": "Redis Connectivity", 
                "status": "FAIL",
                "error": str(e)
            }
        
        self.results.append(result)
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("🚀 Starting Production Validation Tests...")
        print("=" * 50)
        
        tests = [
            self.test_api_health,
            self.test_redis_connectivity,
            self.test_frontend_loading,
            self.test_authentication_endpoints,
            self.test_csrf_protection,
            lambda: self.test_concurrent_health_checks(10)
        ]
        
        for test in tests:
            result = test()
            status_emoji = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_emoji} {result['test']}: {result['status']}")
        
        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "PASS")
        
        print("\n" + "=" * 50)
        print(f"📊 VALIDATION SUMMARY: {passed_tests}/{total_tests} PASSED")
        print("=" * 50)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
            "overall_status": "PASS" if passed_tests == total_tests else "PARTIAL",
            "detailed_results": self.results
        }

if __name__ == "__main__":
    tester = ProductionValidationTester()
    summary = tester.run_all_tests()
    
    # Save results
    with open("/home/marku/ai_workflow_engine/production_validation_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Results saved to: production_validation_results.json")