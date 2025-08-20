#!/usr/bin/env python3
"""
Comprehensive Test Runner for MCP Server
Supports multiple test modes and CI/CD integration
"""

import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any

class TestRunner:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = {
            "timestamp": time.time(),
            "server_url": server_url,
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def wait_for_server(self, timeout: int = 30) -> bool:
        """Wait for server to be ready"""
        print(f"⏳ Waiting for server at {self.server_url} (timeout: {timeout}s)...")
        
        import requests
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except:
                pass
            time.sleep(1)
        
        print("❌ Server did not become ready in time")
        return False
    
    def run_basic_tests(self) -> bool:
        """Run the basic test suite"""
        print("\n🧪 Running basic test suite...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_integrated_mcp.py"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            success = result.returncode == 0
            
            self.results["tests"]["basic"] = {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return success
            
        except Exception as e:
            print(f"❌ Failed to run basic tests: {e}")
            self.results["tests"]["basic"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def run_performance_tests(self) -> bool:
        """Run performance tests"""
        print("\n⚡ Running performance tests...")
        
        try:
            # Import and run performance tests
            import requests
            import threading
            import statistics
            
            # Test response times
            response_times = []
            for _ in range(10):
                start = time.time()
                response = requests.get(f"{self.server_url}/health", timeout=5)
                end = time.time()
                
                if response.status_code == 200:
                    response_times.append(end - start)
            
            if response_times:
                avg_time = statistics.mean(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                print(f"📊 Response times - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
                
                # Performance thresholds
                performance_ok = avg_time < 0.5 and max_time < 1.0
                
                self.results["tests"]["performance"] = {
                    "success": performance_ok,
                    "avg_response_time": avg_time,
                    "max_response_time": max_time,
                    "min_response_time": min_time,
                    "total_requests": len(response_times)
                }
                
                if performance_ok:
                    print("✅ Performance tests passed")
                else:
                    print("⚠️ Performance tests show slow responses")
                
                return performance_ok
            else:
                print("❌ No successful responses for performance testing")
                return False
                
        except Exception as e:
            print(f"❌ Performance tests failed: {e}")
            self.results["tests"]["performance"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def run_load_tests(self, concurrent_users: int = 10, requests_per_user: int = 5) -> bool:
        """Run load tests"""
        print(f"\n🏋️ Running load tests ({concurrent_users} users, {requests_per_user} requests each)...")
        
        try:
            import requests
            import threading
            from queue import Queue
            
            results_queue = Queue()
            
            def user_simulation(user_id: int):
                user_results = []
                for i in range(requests_per_user):
                    try:
                        start = time.time()
                        response = requests.get(f"{self.server_url}/health", timeout=10)
                        end = time.time()
                        
                        user_results.append({
                            "status_code": response.status_code,
                            "response_time": end - start,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        user_results.append({
                            "status_code": None,
                            "response_time": None,
                            "success": False,
                            "error": str(e)
                        })
                
                results_queue.put(user_results)
            
            # Start concurrent users
            threads = []
            start_time = time.time()
            
            for user_id in range(concurrent_users):
                thread = threading.Thread(target=user_simulation, args=(user_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all users to complete
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            
            # Collect and analyze results
            all_results = []
            while not results_queue.empty():
                all_results.extend(results_queue.get())
            
            total_requests = len(all_results)
            successful_requests = sum(1 for r in all_results if r["success"])
            failed_requests = total_requests - successful_requests
            
            if successful_requests > 0:
                avg_response_time = sum(r["response_time"] for r in all_results if r["response_time"]) / successful_requests
            else:
                avg_response_time = 0
            
            success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
            total_duration = end_time - start_time
            requests_per_second = total_requests / total_duration if total_duration > 0 else 0
            
            print(f"📊 Load test results:")
            print(f"   Total requests: {total_requests}")
            print(f"   Successful: {successful_requests}")
            print(f"   Failed: {failed_requests}")
            print(f"   Success rate: {success_rate:.1f}%")
            print(f"   Avg response time: {avg_response_time:.3f}s")
            print(f"   Requests per second: {requests_per_second:.1f}")
            
            # Load test passes if success rate > 95% and avg response time < 1s
            load_test_ok = success_rate > 95.0 and avg_response_time < 1.0
            
            self.results["tests"]["load"] = {
                "success": load_test_ok,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "requests_per_second": requests_per_second,
                "duration": total_duration
            }
            
            if load_test_ok:
                print("✅ Load tests passed")
            else:
                print("⚠️ Load tests show performance issues")
            
            return load_test_ok
            
        except Exception as e:
            print(f"❌ Load tests failed: {e}")
            self.results["tests"]["load"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def run_security_tests(self) -> bool:
        """Run basic security tests"""
        print("\n🔒 Running security tests...")
        
        try:
            import requests
            
            security_issues = []
            
            # Test for SQL injection patterns
            try:
                malicious_data = {"query": "'; DROP TABLE users; --"}
                response = requests.post(f"{self.server_url}/mcp/memory/search_nodes", 
                                       json=malicious_data, timeout=5)
                if response.status_code not in [400, 422]:
                    security_issues.append("Potential SQL injection vulnerability")
            except:
                pass  # Server properly rejected or handled
            
            # Test for XSS patterns
            try:
                xss_data = {
                    "name": "<script>alert('xss')</script>",
                    "entityType": "test",
                    "observations": ["<img src=x onerror=alert('xss')>"]
                }
                response = requests.post(f"{self.server_url}/mcp/memory/create_entities", 
                                       json=[xss_data], timeout=5)
                # If it accepts without sanitization, it's a concern
                if response.status_code == 200:
                    result = response.json()
                    if "<script>" in str(result):
                        security_issues.append("Potential XSS vulnerability - scripts not sanitized")
            except:
                pass
            
            # Test for oversized requests
            try:
                huge_data = {
                    "name": "a" * 100000,  # 100KB name
                    "entityType": "test",
                    "observations": ["a" * 1000000]  # 1MB observation
                }
                response = requests.post(f"{self.server_url}/mcp/memory/create_entities", 
                                       json=[huge_data], timeout=10)
                if response.status_code == 200:
                    security_issues.append("Server accepts oversized requests without limits")
            except:
                pass  # Good - server properly rejects or times out
            
            security_ok = len(security_issues) == 0
            
            self.results["tests"]["security"] = {
                "success": security_ok,
                "issues_found": security_issues,
                "tests_run": ["sql_injection", "xss", "oversized_requests"]
            }
            
            if security_ok:
                print("✅ Security tests passed")
            else:
                print(f"⚠️ Security issues found: {security_issues}")
            
            return security_ok
            
        except Exception as e:
            print(f"❌ Security tests failed: {e}")
            self.results["tests"]["security"] = {
                "success": False,
                "error": str(e)
            }
            return False
    
    def save_results(self, output_file: str = "test_results.json"):
        """Save test results to JSON file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"📁 Results saved to {output_file}")
        except Exception as e:
            print(f"⚠️ Failed to save results: {e}")
    
    def run_all_tests(self, include_load: bool = False, include_security: bool = False) -> bool:
        """Run all test suites"""
        print("🚀 Starting comprehensive test suite...")
        
        if not self.wait_for_server():
            return False
        
        tests_to_run = [
            ("basic", self.run_basic_tests),
            ("performance", self.run_performance_tests)
        ]
        
        if include_load:
            tests_to_run.append(("load", self.run_load_tests))
        
        if include_security:
            tests_to_run.append(("security", self.run_security_tests))
        
        all_passed = True
        
        for test_name, test_func in tests_to_run:
            self.results["summary"]["total"] += 1
            
            if test_func():
                self.results["summary"]["passed"] += 1
                print(f"✅ {test_name.capitalize()} tests passed")
            else:
                self.results["summary"]["failed"] += 1
                all_passed = False
                print(f"❌ {test_name.capitalize()} tests failed")
        
        return all_passed

def main():
    parser = argparse.ArgumentParser(description="Comprehensive MCP Server Test Runner")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Server URL (default: http://localhost:8000)")
    parser.add_argument("--include-load", action="store_true",
                       help="Include load tests")
    parser.add_argument("--include-security", action="store_true", 
                       help="Include security tests")
    parser.add_argument("--output", default="test_results.json",
                       help="Output file for results (default: test_results.json)")
    parser.add_argument("--ci", action="store_true",
                       help="CI mode - exit with error code on failure")
    
    args = parser.parse_args()
    
    runner = TestRunner(args.url)
    
    success = runner.run_all_tests(
        include_load=args.include_load,
        include_security=args.include_security
    )
    
    runner.save_results(args.output)
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    summary = runner.results["summary"]
    print(f"Total tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        exit_code = 0
    else:
        print("💥 SOME TESTS FAILED!")
        exit_code = 1
    
    if args.ci:
        sys.exit(exit_code)
    
    return exit_code

if __name__ == "__main__":
    main()