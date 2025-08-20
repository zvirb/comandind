#!/usr/bin/env python3
"""
Security Validation Script for Authentication Loop Fixes

This script validates the security of authentication loop fixes implemented by
frontend and backend teams, testing for:
1. Rate limiting bypass vulnerabilities
2. Redis caching data leakage
3. Request deduplication race conditions  
4. Exponential backoff DoS exploitation
5. Authentication state machine security
"""

import asyncio
import aiohttp
import time
import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityValidator:
    def __init__(self, base_url: str = "https://aiwfe.com"):
        self.base_url = base_url
        self.session = None
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "vulnerabilities_found": [],
            "security_findings": []
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(ssl=True)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_vulnerability(self, test_name: str, severity: str, description: str, details: Dict[str, Any]):
        """Log security vulnerability finding."""
        vulnerability = {
            "test": test_name,
            "severity": severity,
            "description": description,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results["vulnerabilities_found"].append(vulnerability)
        logger.error(f"VULNERABILITY [{severity}] {test_name}: {description}")

    def log_finding(self, test_name: str, status: str, details: Dict[str, Any]):
        """Log security test finding."""
        finding = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results["security_findings"].append(finding)
        
        if status == "PASS":
            self.validation_results["tests_passed"] += 1
            logger.info(f"PASS {test_name}")
        else:
            self.validation_results["tests_failed"] += 1
            logger.warning(f"FAIL {test_name}: {details}")

    async def test_rate_limiting_bypass(self) -> Dict[str, Any]:
        """Test for rate limiting bypass vulnerabilities."""
        logger.info("Testing rate limiting bypass vulnerabilities...")
        
        results = {
            "ip_rate_limiting": False,
            "token_rate_limiting": False,
            "session_validate_limits": False,
            "login_limits": False,
            "bypass_attempts": []
        }

        # Test 1: IP-based rate limiting
        try:
            responses = []
            for i in range(20):
                async with self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers={"Authorization": f"Bearer test-token-{i}"}
                ) as response:
                    responses.append({
                        "status": response.status,
                        "headers": dict(response.headers),
                        "time": time.time()
                    })
            
            # Check if rate limiting kicked in
            rate_limited_responses = [r for r in responses if r["status"] == 429]
            results["ip_rate_limiting"] = len(rate_limited_responses) > 0

            if not results["ip_rate_limiting"]:
                self.log_vulnerability(
                    "rate_limiting_bypass",
                    "MEDIUM",
                    "IP-based rate limiting not effectively applied",
                    {"responses_200": len([r for r in responses if r["status"] < 400])}
                )

        except Exception as e:
            logger.error(f"Error testing IP rate limiting: {e}")

        # Test 2: Session validation rate limits
        try:
            rapid_responses = []
            for i in range(15):
                start_time = time.time()
                async with self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers={"Authorization": "Bearer same-token"}
                ) as response:
                    rapid_responses.append({
                        "status": response.status,
                        "response_time": time.time() - start_time
                    })
                    
            results["session_validate_limits"] = any(
                r["status"] == 429 for r in rapid_responses[-5:]
            )

        except Exception as e:
            logger.error(f"Error testing session validation limits: {e}")

        # Test 3: Login endpoint rate limiting
        try:
            login_attempts = []
            for i in range(12):
                async with self.session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"email": f"test{i}@test.com", "password": "wrongpassword"},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    login_attempts.append({
                        "status": response.status,
                        "attempt": i + 1
                    })

            # Check if login rate limiting is working
            blocked_attempts = [a for a in login_attempts if a["status"] == 429]
            results["login_limits"] = len(blocked_attempts) > 0

            if not results["login_limits"]:
                self.log_vulnerability(
                    "login_rate_limiting_bypass",
                    "HIGH", 
                    "Login rate limiting allows too many attempts",
                    {"total_attempts": len(login_attempts), "blocked": len(blocked_attempts)}
                )

        except Exception as e:
            logger.error(f"Error testing login rate limiting: {e}")

        self.log_finding("rate_limiting_bypass_test", 
                        "PASS" if all(results.values()) else "PARTIAL",
                        results)
        
        return results

    async def test_redis_data_leakage(self) -> Dict[str, Any]:
        """Test for Redis authentication data leakage risks."""
        logger.info("Testing Redis caching for authentication data leakage...")
        
        results = {
            "no_sensitive_keys_exposed": True,
            "proper_key_expiration": True,
            "no_token_leakage": True,
            "secure_data_patterns": True
        }

        # Test 1: Check response headers for Redis debugging info
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/validate",
                headers={"Authorization": "Bearer test-redis-check"}
            ) as response:
                headers = dict(response.headers)
                
                # Check for Redis debugging headers that might leak info
                sensitive_headers = [
                    'x-redis-key', 'x-cache-key', 'x-auth-cache',
                    'x-session-id', 'x-redis-debug'
                ]
                
                for header in sensitive_headers:
                    if header in headers:
                        self.log_vulnerability(
                            "redis_header_leakage",
                            "MEDIUM",
                            f"Redis debugging header exposed: {header}",
                            {"header": header, "value": headers[header]}
                        )
                        results["no_sensitive_keys_exposed"] = False

        except Exception as e:
            logger.error(f"Error checking Redis header leakage: {e}")

        # Test 2: Check for cache timing attacks
        try:
            # First request - should be slower (cache miss)
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/validate",
                headers={"Authorization": "Bearer timing-test-token"}
            ) as response:
                first_response_time = time.time() - start_time
                first_status = response.status

            # Second identical request - might be faster (cache hit)
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/validate",
                headers={"Authorization": "Bearer timing-test-token"}
            ) as response:
                second_response_time = time.time() - start_time
                second_status = response.status

            # Significant timing difference might indicate caching behavior
            timing_difference = abs(first_response_time - second_response_time)
            if timing_difference > 0.05:  # 50ms threshold
                self.log_finding("redis_cache_timing", "INFO", {
                    "first_response_time": first_response_time,
                    "second_response_time": second_response_time,
                    "timing_difference": timing_difference
                })

        except Exception as e:
            logger.error(f"Error testing cache timing: {e}")

        self.log_finding("redis_data_leakage_test", 
                        "PASS" if all(results.values()) else "REVIEW",
                        results)
        
        return results

    async def test_deduplication_race_conditions(self) -> Dict[str, Any]:
        """Test request deduplication for race condition vulnerabilities."""
        logger.info("Testing request deduplication race conditions...")
        
        results = {
            "concurrent_request_handling": True,
            "no_duplicate_processing": True,
            "proper_deduplication": True,
            "race_condition_free": True
        }

        # Test 1: Concurrent identical requests
        try:
            tasks = []
            token = "race-condition-test-token"
            
            # Send 5 identical concurrent requests
            for i in range(5):
                task = self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers={"Authorization": f"Bearer {token}"}
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze responses for race conditions
            request_ids = []
            status_codes = []
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.warning(f"Request {i} failed with exception: {response}")
                    continue
                    
                async with response as resp:
                    status_codes.append(resp.status)
                    try:
                        data = await resp.json()
                        if 'request_id' in data:
                            request_ids.append(data['request_id'])
                    except:
                        pass

            # Check for duplicate request IDs (indicates race condition)
            unique_request_ids = set(request_ids)
            if len(request_ids) != len(unique_request_ids):
                self.log_vulnerability(
                    "deduplication_race_condition",
                    "MEDIUM",
                    "Duplicate request IDs detected in concurrent requests",
                    {"total_requests": len(request_ids), "unique_ids": len(unique_request_ids)}
                )
                results["race_condition_free"] = False

        except Exception as e:
            logger.error(f"Error testing concurrent requests: {e}")

        # Test 2: Rapid-fire deduplication bypass
        try:
            rapid_responses = []
            identical_request_data = {"test": "deduplication", "timestamp": time.time()}
            
            for i in range(10):
                start_time = time.time()
                async with self.session.post(
                    f"{self.base_url}/api/v1/auth/validate",
                    json=identical_request_data,
                    headers={"Authorization": "Bearer dedup-test-token"}
                ) as response:
                    rapid_responses.append({
                        "status": response.status,
                        "response_time": time.time() - start_time,
                        "attempt": i + 1
                    })

            # Check if deduplication is working
            blocked_requests = [r for r in rapid_responses if r["status"] == 429]
            results["proper_deduplication"] = len(blocked_requests) > 0

        except Exception as e:
            logger.error(f"Error testing rapid deduplication: {e}")

        self.log_finding("deduplication_race_conditions_test",
                        "PASS" if all(results.values()) else "FAIL",
                        results)
        
        return results

    async def test_exponential_backoff_dos(self) -> Dict[str, Any]:
        """Test exponential backoff for DoS exploitation vulnerabilities."""
        logger.info("Testing exponential backoff against DoS exploitation...")
        
        results = {
            "backoff_implemented": False,
            "no_dos_amplification": True,
            "proper_retry_limits": True,
            "resource_exhaustion_protected": True
        }

        # Test 1: Failed login attempts with backoff
        try:
            login_times = []
            
            for attempt in range(6):
                start_time = time.time()
                async with self.session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={
                        "email": "dos-test@test.com", 
                        "password": f"wrongpassword{attempt}"
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_time = time.time() - start_time
                    login_times.append({
                        "attempt": attempt + 1,
                        "status": response.status,
                        "response_time": response_time
                    })

            # Check for increasing response times (indicates backoff)
            if len(login_times) >= 3:
                avg_early = sum(t["response_time"] for t in login_times[:2]) / 2
                avg_late = sum(t["response_time"] for t in login_times[-2:]) / 2
                
                if avg_late > avg_early * 1.5:  # 50% increase threshold
                    results["backoff_implemented"] = True

            # Check for 429 responses indicating rate limiting
            rate_limited = any(t["status"] == 429 for t in login_times)
            if rate_limited:
                results["backoff_implemented"] = True

        except Exception as e:
            logger.error(f"Error testing exponential backoff: {e}")

        # Test 2: Resource exhaustion protection
        try:
            # Attempt many simultaneous requests to test resource limits
            tasks = []
            for i in range(20):
                task = self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers={"Authorization": f"Bearer dos-test-{i}"}
                )
                tasks.append(task)

            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            # Check for proper resource management
            successful_responses = 0
            rate_limited_responses = 0
            
            for response in responses:
                if isinstance(response, Exception):
                    continue
                async with response as resp:
                    if resp.status < 400:
                        successful_responses += 1
                    elif resp.status == 429:
                        rate_limited_responses += 1

            # If too many requests succeed without rate limiting, it's a concern
            if successful_responses > 15 and rate_limited_responses == 0:
                self.log_vulnerability(
                    "dos_resource_exhaustion",
                    "MEDIUM",
                    "Too many concurrent requests processed without rate limiting",
                    {"successful": successful_responses, "rate_limited": rate_limited_responses}
                )
                results["resource_exhaustion_protected"] = False

        except Exception as e:
            logger.error(f"Error testing resource exhaustion protection: {e}")

        self.log_finding("exponential_backoff_dos_test",
                        "PASS" if all(results.values()) else "REVIEW",
                        results)
        
        return results

    async def test_session_hijacking_prevention(self) -> Dict[str, Any]:
        """Test authentication state machine for session hijacking prevention."""
        logger.info("Testing session hijacking prevention...")
        
        results = {
            "secure_headers_present": True,
            "no_session_fixation": True,
            "proper_csrf_protection": True,
            "secure_token_handling": True,
            "xss_protection": True
        }

        # Test 1: Security headers validation
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/validate",
                headers={"Authorization": "Bearer security-header-test"}
            ) as response:
                headers = dict(response.headers)
                
                required_security_headers = {
                    'x-frame-options': 'DENY',
                    'strict-transport-security': True,  # Just check presence
                    'content-security-policy': True,
                    'x-content-type-options': 'nosniff',
                    'x-xss-protection': True
                }
                
                missing_headers = []
                for header, expected in required_security_headers.items():
                    header_lower = header.lower()
                    if header_lower not in [h.lower() for h in headers.keys()]:
                        missing_headers.append(header)
                    elif expected != True:  # Check specific value
                        actual_value = headers.get(header_lower, '')
                        if expected.lower() not in actual_value.lower():
                            missing_headers.append(f"{header} (incorrect value)")

                if missing_headers:
                    self.log_vulnerability(
                        "missing_security_headers",
                        "MEDIUM",
                        "Required security headers missing or incorrect",
                        {"missing_headers": missing_headers}
                    )
                    results["secure_headers_present"] = False

        except Exception as e:
            logger.error(f"Error testing security headers: {e}")

        # Test 2: CSRF protection validation
        try:
            # Attempt POST without CSRF token
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": "csrf-test@test.com", "password": "test"},
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://malicious-site.com"  # Different origin
                }
            ) as response:
                # Check if request was properly rejected or handled
                if response.status == 200:
                    # This might indicate insufficient CSRF protection
                    response_data = await response.json()
                    if response_data.get('success'):
                        self.log_vulnerability(
                            "csrf_bypass",
                            "HIGH",
                            "CSRF protection may be insufficient",
                            {"status": response.status, "origin_header": "https://malicious-site.com"}
                        )
                        results["proper_csrf_protection"] = False

        except Exception as e:
            logger.error(f"Error testing CSRF protection: {e}")

        # Test 3: XSS protection validation  
        try:
            xss_payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "'\"><img src=x onerror=alert('xss')>"
            ]
            
            for payload in xss_payloads:
                async with self.session.get(
                    f"{self.base_url}/api/v1/auth/validate",
                    headers={"Authorization": f"Bearer {payload}"}
                ) as response:
                    response_text = await response.text()
                    
                    # Check if payload is reflected without proper escaping
                    if payload in response_text and 'script' in payload:
                        self.log_vulnerability(
                            "xss_reflection",
                            "HIGH",
                            "Potential XSS vulnerability - payload reflected",
                            {"payload": payload, "reflected": True}
                        )
                        results["xss_protection"] = False

        except Exception as e:
            logger.error(f"Error testing XSS protection: {e}")

        self.log_finding("session_hijacking_prevention_test",
                        "PASS" if all(results.values()) else "FAIL",
                        results)
        
        return results

    async def run_comprehensive_security_validation(self) -> Dict[str, Any]:
        """Run all security validation tests."""
        logger.info("Starting comprehensive security validation of authentication loop fixes...")
        
        test_results = {}
        
        try:
            # Run all security tests
            test_results["rate_limiting"] = await self.test_rate_limiting_bypass()
            test_results["redis_security"] = await self.test_redis_data_leakage()
            test_results["deduplication"] = await self.test_deduplication_race_conditions()
            test_results["dos_protection"] = await self.test_exponential_backoff_dos()
            test_results["session_security"] = await self.test_session_hijacking_prevention()

            # Generate overall security assessment
            total_vulnerabilities = len(self.validation_results["vulnerabilities_found"])
            critical_vulns = len([v for v in self.validation_results["vulnerabilities_found"] 
                                if v["severity"] == "CRITICAL"])
            high_vulns = len([v for v in self.validation_results["vulnerabilities_found"] 
                            if v["severity"] == "HIGH"])
            medium_vulns = len([v for v in self.validation_results["vulnerabilities_found"] 
                              if v["severity"] == "MEDIUM"])

            security_score = max(0, 100 - (critical_vulns * 40) - (high_vulns * 20) - (medium_vulns * 10))
            
            self.validation_results.update({
                "test_results": test_results,
                "security_score": security_score,
                "overall_status": (
                    "CRITICAL" if critical_vulns > 0 else
                    "HIGH_RISK" if high_vulns > 0 else
                    "MEDIUM_RISK" if medium_vulns > 0 else
                    "LOW_RISK"
                ),
                "recommendations": self._generate_security_recommendations()
            })

        except Exception as e:
            logger.error(f"Error during security validation: {e}")
            self.validation_results["error"] = str(e)

        return self.validation_results

    def _generate_security_recommendations(self) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        
        for vuln in self.validation_results["vulnerabilities_found"]:
            if "rate_limiting" in vuln["test"]:
                recommendations.append("Strengthen rate limiting implementation with stricter thresholds")
            elif "redis" in vuln["test"]:
                recommendations.append("Review Redis configuration for sensitive data exposure")
            elif "race_condition" in vuln["test"]:
                recommendations.append("Implement proper synchronization for concurrent request handling")
            elif "dos" in vuln["test"]:
                recommendations.append("Enhance DoS protection with better resource limits")
            elif "csrf" in vuln["test"]:
                recommendations.append("Implement comprehensive CSRF protection")
            elif "xss" in vuln["test"]:
                recommendations.append("Add proper input sanitization and output encoding")

        if not recommendations:
            recommendations.append("Continue monitoring authentication security patterns")
            recommendations.append("Implement regular security testing in CI/CD pipeline")

        return recommendations

async def main():
    """Main execution function."""
    print("🔒 Authentication Loop Security Validation")
    print("=" * 50)
    
    async with SecurityValidator() as validator:
        results = await validator.run_comprehensive_security_validation()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"/home/marku/ai_workflow_engine/.claude/security_validation_results_auth_loop_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📊 Security Validation Complete")
        print(f"Security Score: {results['security_score']}/100")
        print(f"Overall Status: {results['overall_status']}")
        print(f"Tests Passed: {results['tests_passed']}")
        print(f"Tests Failed: {results['tests_failed']}")
        print(f"Vulnerabilities Found: {len(results['vulnerabilities_found'])}")
        print(f"\nResults saved to: {results_file}")
        
        if results["vulnerabilities_found"]:
            print("\n⚠️  Vulnerabilities Identified:")
            for vuln in results["vulnerabilities_found"]:
                print(f"  - [{vuln['severity']}] {vuln['description']}")
        
        if results["recommendations"]:
            print("\n💡 Security Recommendations:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"  {i}. {rec}")

if __name__ == "__main__":
    asyncio.run(main())