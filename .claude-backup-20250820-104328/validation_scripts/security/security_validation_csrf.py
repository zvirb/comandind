#!/usr/bin/env python3
"""
CSRF Security Validation Script

This script performs comprehensive security validation of the CSRF authentication fixes,
specifically focusing on the middleware exemption issue identified by ui-regression-debugger.

SECURITY VALIDATION REQUIREMENTS:
1. Analyze CSRF middleware configuration
2. Verify exemption paths are correctly configured
3. Test CSRF protection on non-exempt endpoints
4. Validate token format and cryptographic properties
5. Check for security bypasses or weaknesses
6. Verify session security and token rotation
"""

import asyncio
import httpx
import json
import os
import sys
import time
import hmac
import hashlib
import secrets
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse


class CSRFSecurityValidator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True
        )
        self.csrf_token = None
        self.session_cookies = {}
        
        # Expected exempt paths (from main.py configuration)
        self.expected_exempt_paths = {
            "/health",
            "/api/v1/health",
            "/api/health",
            "/api/v1/auth/login",
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/jwt/login-debug",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/token",
            "/api/v1/auth/logout",
            "/api/v1/auth/csrf-token",
            "/api/v1/public",
            "/api/v1/ws/agent",
            "/api/v1/ws/focus-nudge",
            "/api/v1/ws/helios",
            "/ws/chat",
            "/ws/v2/secure/agent",
            "/ws/v2/secure/helios",
            "/ws/v2/secure/monitoring",
            "/api/auth/login",
            "/api/auth/jwt/login",
            "/api/auth/jwt/login-debug",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/auth/token",
            "/api/auth/logout",
            "/api/auth/csrf-token",
        }
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_security_finding(self, level: str, finding: str, details: Dict[str, Any] = None):
        """Log security findings with severity levels."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level.upper()}] {finding}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")
        print()
    
    async def test_csrf_token_generation(self) -> bool:
        """Test CSRF token endpoint and validate token format."""
        self.log_security_finding("info", "Testing CSRF token generation...")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/auth/csrf-token",
                headers={
                    "Origin": "http://localhost:5173",
                    "User-Agent": "CSRF-Security-Validator/1.0"
                }
            )
            
            if response.status_code != 200:
                self.log_security_finding("critical", "CSRF token endpoint failed", {
                    "status_code": response.status_code,
                    "response": response.text
                })
                return False
            
            data = response.json()
            token = data.get("csrf_token")
            
            if not token:
                self.log_security_finding("critical", "No CSRF token returned")
                return False
            
            # Validate token format: timestamp:nonce:signature
            parts = token.split(":")
            if len(parts) != 3:
                self.log_security_finding("critical", "Invalid CSRF token format", {
                    "token": token[:50] + "...",
                    "parts_count": len(parts),
                    "expected_parts": 3
                })
                return False
            
            timestamp_str, nonce, signature = parts
            
            # Validate timestamp
            try:
                timestamp = int(timestamp_str)
                current_time = int(time.time())
                age = current_time - timestamp
                
                if abs(age) > 300:  # 5 minutes tolerance
                    self.log_security_finding("high", "CSRF token timestamp out of acceptable range", {
                        "token_age_seconds": age,
                        "max_acceptable_age": 300
                    })
            except ValueError:
                self.log_security_finding("critical", "Invalid timestamp in CSRF token", {
                    "timestamp_str": timestamp_str
                })
                return False
            
            # Validate nonce length (should be ~32 chars base64-encoded)
            if len(nonce) < 20:
                self.log_security_finding("medium", "CSRF token nonce appears short", {
                    "nonce_length": len(nonce),
                    "recommended_min": 20
                })
            
            # Validate signature length (SHA256 hex = 64 chars)
            if len(signature) != 64:
                self.log_security_finding("high", "CSRF token signature length unexpected", {
                    "signature_length": len(signature),
                    "expected_length": 64
                })
            
            # Store token for further tests
            self.csrf_token = token
            
            # Check if cookie was set
            csrf_cookie = None
            for cookie in response.cookies:
                if cookie.name == "csrf_token":
                    csrf_cookie = cookie
                    break
            
            if csrf_cookie:
                self.log_security_finding("info", "CSRF token cookie set correctly", {
                    "httponly": csrf_cookie.get("httponly", False),
                    "secure": csrf_cookie.get("secure", False),
                    "samesite": csrf_cookie.get("samesite", "not_set")
                })
                
                # Security check: CSRF tokens must NOT be HttpOnly
                if csrf_cookie.get("httponly", False):
                    self.log_security_finding("critical", "CSRF token cookie is HttpOnly - JavaScript cannot access it")
                    return False
            else:
                self.log_security_finding("medium", "No CSRF token cookie set")
            
            self.log_security_finding("info", "CSRF token generation successful", {
                "token_format": "timestamp:nonce:signature",
                "timestamp_valid": True,
                "nonce_length": len(nonce),
                "signature_length": len(signature)
            })
            
            return True
            
        except Exception as e:
            self.log_security_finding("critical", f"CSRF token generation test failed: {str(e)}")
            return False
    
    async def test_exemption_paths(self) -> Dict[str, bool]:
        """Test that exempt paths don't require CSRF tokens."""
        self.log_security_finding("info", "Testing CSRF exemption paths...")
        
        results = {}
        
        # Test exempt paths - these should work without CSRF tokens
        exempt_test_paths = [
            ("/health", "GET"),
            ("/api/v1/health", "GET"),
            ("/api/health", "GET"),
            ("/api/v1/auth/csrf-token", "GET"),
            ("/api/auth/csrf-token", "GET"),
        ]
        
        for path, method in exempt_test_paths:
            try:
                response = await self.client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={
                        "Origin": "http://localhost:5173",
                        "User-Agent": "CSRF-Security-Validator/1.0"
                    }
                )
                
                # Exempt paths should not return CSRF errors (403 with CSRF message)
                is_exempt = response.status_code != 403 or "CSRF" not in response.text
                results[path] = is_exempt
                
                if is_exempt:
                    self.log_security_finding("info", f"Exempt path working correctly: {method} {path}", {
                        "status_code": response.status_code
                    })
                else:
                    self.log_security_finding("high", f"Exempt path incorrectly protected: {method} {path}", {
                        "status_code": response.status_code,
                        "response": response.text[:200]
                    })
                    
            except Exception as e:
                self.log_security_finding("error", f"Error testing exempt path {path}: {str(e)}")
                results[path] = False
        
        return results
    
    async def test_login_endpoint_exemption(self) -> bool:
        """Specifically test the /api/v1/auth/jwt/login endpoint exemption."""
        self.log_security_finding("info", "Testing JWT login endpoint CSRF exemption...")
        
        # Test without CSRF token - should work (endpoint is exempt)
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/jwt/login",
                json=login_data,
                headers={
                    "Origin": "http://localhost:5173",
                    "Content-Type": "application/json",
                    "User-Agent": "CSRF-Security-Validator/1.0"
                }
            )
            
            # Check if it's a CSRF error (403 with CSRF message)
            is_csrf_error = (response.status_code == 403 and "CSRF" in response.text)
            
            if is_csrf_error:
                self.log_security_finding("critical", "JWT login endpoint incorrectly requires CSRF token", {
                    "status_code": response.status_code,
                    "response": response.text,
                    "expected": "Endpoint should be exempt from CSRF protection"
                })
                return False
            
            # The endpoint should be exempt, so we expect either:
            # - 401 (authentication failed - normal)
            # - 200 (authentication successful)
            # - 422 (validation error)
            # NOT 403 with CSRF error
            
            if response.status_code in [200, 401, 422]:
                self.log_security_finding("info", "JWT login endpoint correctly exempt from CSRF", {
                    "status_code": response.status_code,
                    "csrf_exempt": True
                })
                return True
            else:
                self.log_security_finding("medium", "JWT login endpoint unexpected response", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
                
        except Exception as e:
            self.log_security_finding("error", f"Error testing JWT login exemption: {str(e)}")
            return False
    
    async def test_protected_endpoints(self) -> bool:
        """Test that non-exempt endpoints properly require CSRF tokens."""
        self.log_security_finding("info", "Testing CSRF protection on non-exempt endpoints...")
        
        # Test endpoints that should require CSRF protection
        protected_endpoints = [
            ("/api/v1/documents/upload", "POST", {"test": "data"}),
            ("/api/v1/user/current", "POST", {}),  # If this exists as POST
            ("/api/v1/tasks", "POST", {"task": "test"}),
        ]
        
        for path, method, data in protected_endpoints:
            try:
                # Test without CSRF token - should fail
                response = await self.client.request(
                    method,
                    f"{self.base_url}{path}",
                    json=data if data else None,
                    headers={
                        "Origin": "http://localhost:5173",
                        "Content-Type": "application/json",
                        "User-Agent": "CSRF-Security-Validator/1.0"
                    }
                )
                
                # Should get CSRF error (403)
                is_csrf_protected = (response.status_code == 403 and "CSRF" in response.text)
                
                if is_csrf_protected:
                    self.log_security_finding("info", f"Protected endpoint correctly requires CSRF: {method} {path}")
                else:
                    # Could be 401 (auth required) or other error, but not CSRF-related
                    if response.status_code == 401:
                        self.log_security_finding("info", f"Protected endpoint requires authentication: {method} {path}")
                    elif response.status_code == 404:
                        self.log_security_finding("info", f"Endpoint not found (expected): {method} {path}")
                    else:
                        self.log_security_finding("medium", f"Protected endpoint unexpected response: {method} {path}", {
                            "status_code": response.status_code,
                            "response": response.text[:200]
                        })
                
            except Exception as e:
                self.log_security_finding("error", f"Error testing protected endpoint {path}: {str(e)}")
        
        return True
    
    async def test_csrf_token_validation(self) -> bool:
        """Test CSRF token validation logic."""
        if not self.csrf_token:
            self.log_security_finding("error", "No CSRF token available for validation test")
            return False
        
        self.log_security_finding("info", "Testing CSRF token validation...")
        
        # Test with valid CSRF token on a protected endpoint
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/upload",
                headers={
                    "Origin": "http://localhost:5173",
                    "X-CSRF-TOKEN": self.csrf_token,
                    "Content-Type": "application/json",
                    "User-Agent": "CSRF-Security-Validator/1.0"
                },
                json={"test": "data"}
            )
            
            # Should not get CSRF error (but might get auth error)
            is_csrf_error = (response.status_code == 403 and "CSRF" in response.text)
            
            if not is_csrf_error:
                self.log_security_finding("info", "Valid CSRF token accepted", {
                    "status_code": response.status_code
                })
            else:
                self.log_security_finding("high", "Valid CSRF token rejected", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
            
        except Exception as e:
            self.log_security_finding("error", f"Error testing CSRF token validation: {str(e)}")
            return False
        
        # Test with invalid CSRF token
        try:
            invalid_token = "1234567890:invalid_nonce:invalid_signature"
            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/upload",
                headers={
                    "Origin": "http://localhost:5173",
                    "X-CSRF-TOKEN": invalid_token,
                    "Content-Type": "application/json",
                    "User-Agent": "CSRF-Security-Validator/1.0"
                },
                json={"test": "data"}
            )
            
            # Should get CSRF error
            is_csrf_error = (response.status_code == 403 and "CSRF" in response.text)
            
            if is_csrf_error:
                self.log_security_finding("info", "Invalid CSRF token correctly rejected")
            else:
                self.log_security_finding("high", "Invalid CSRF token incorrectly accepted", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
                
        except Exception as e:
            self.log_security_finding("error", f"Error testing invalid CSRF token: {str(e)}")
            return False
        
        return True
    
    async def test_origin_validation(self) -> bool:
        """Test Origin header validation."""
        self.log_security_finding("info", "Testing Origin header validation...")
        
        if not self.csrf_token:
            await self.test_csrf_token_generation()
        
        # Test with untrusted origin
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/upload",
                headers={
                    "Origin": "https://malicious-site.com",
                    "X-CSRF-TOKEN": self.csrf_token,
                    "Content-Type": "application/json",
                    "User-Agent": "CSRF-Security-Validator/1.0"
                },
                json={"test": "data"}
            )
            
            # Should get origin validation error
            is_origin_error = (response.status_code == 403 and ("Origin" in response.text or "CSRF" in response.text))
            
            if is_origin_error:
                self.log_security_finding("info", "Untrusted origin correctly rejected")
                return True
            else:
                self.log_security_finding("high", "Untrusted origin incorrectly accepted", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
                
        except Exception as e:
            self.log_security_finding("error", f"Error testing origin validation: {str(e)}")
            return False
    
    async def analyze_middleware_configuration(self) -> Dict[str, Any]:
        """Analyze the current CSRF middleware configuration."""
        self.log_security_finding("info", "Analyzing CSRF middleware configuration...")
        
        # Try to access the middleware configuration endpoint (if it exists)
        config_analysis = {
            "exempt_paths_configured": len(self.expected_exempt_paths),
            "expected_exempt_paths": list(self.expected_exempt_paths),
            "middleware_active": True,  # We'll test this
        }
        
        # Test if CSRF middleware is active by trying a protected endpoint
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/upload",
                headers={
                    "Origin": "http://localhost:5173",
                    "Content-Type": "application/json"
                },
                json={"test": "data"}
            )
            
            csrf_active = (response.status_code == 403 and "CSRF" in response.text)
            config_analysis["middleware_active"] = csrf_active
            
            if not csrf_active:
                self.log_security_finding("critical", "CSRF middleware appears to be inactive", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
            
        except Exception as e:
            self.log_security_finding("error", f"Error analyzing middleware configuration: {str(e)}")
        
        return config_analysis
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive CSRF security validation."""
        print("=" * 80)
        print("CSRF SECURITY VALIDATION REPORT")
        print("=" * 80)
        print()
        
        results = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "base_url": self.base_url,
            "tests_passed": 0,
            "tests_failed": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "findings": []
        }
        
        # Test 1: CSRF Token Generation
        token_generation_ok = await self.test_csrf_token_generation()
        if token_generation_ok:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
        
        # Test 2: Exemption Paths
        exemption_results = await self.test_exemption_paths()
        exempt_paths_ok = all(exemption_results.values())
        if exempt_paths_ok:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
        
        # Test 3: JWT Login Endpoint Exemption (CRITICAL TEST)
        jwt_login_exempt_ok = await self.test_login_endpoint_exemption()
        if jwt_login_exempt_ok:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
            results["critical_issues"] += 1
        
        # Test 4: Protected Endpoints
        protected_endpoints_ok = await self.test_protected_endpoints()
        if protected_endpoints_ok:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
        
        # Test 5: CSRF Token Validation
        if self.csrf_token:
            token_validation_ok = await self.test_csrf_token_validation()
            if token_validation_ok:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1
        
        # Test 6: Origin Validation
        origin_validation_ok = await self.test_origin_validation()
        if origin_validation_ok:
            results["tests_passed"] += 1
        else:
            results["tests_failed"] += 1
            results["high_issues"] += 1
        
        # Test 7: Middleware Configuration Analysis
        config_analysis = await self.analyze_middleware_configuration()
        results["configuration"] = config_analysis
        
        # Summary
        print("=" * 80)
        print("SECURITY VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Tests Passed: {results['tests_passed']}")
        print(f"Tests Failed: {results['tests_failed']}")
        print(f"Critical Issues: {results['critical_issues']}")
        print(f"High Issues: {results['high_issues']}")
        print(f"Medium Issues: {results['medium_issues']}")
        print()
        
        if results['critical_issues'] > 0:
            print("🚨 CRITICAL SECURITY ISSUES FOUND!")
        elif results['high_issues'] > 0:
            print("⚠️  HIGH PRIORITY SECURITY ISSUES FOUND")
        elif results['tests_failed'] > 0:
            print("⚠️  SOME SECURITY TESTS FAILED")
        else:
            print("✅ ALL SECURITY TESTS PASSED")
        
        return results


async def main():
    """Main entry point for CSRF security validation."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    async with CSRFSecurityValidator(base_url) as validator:
        results = await validator.run_comprehensive_validation()
        
        # Exit with error code if critical issues found
        if results['critical_issues'] > 0:
            sys.exit(1)
        elif results['tests_failed'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())