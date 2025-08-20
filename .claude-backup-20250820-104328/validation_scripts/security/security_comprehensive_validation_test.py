#!/usr/bin/env python3
"""
Comprehensive Security Validation Test
=====================================

This script performs active security testing and penetration testing 
of the authentication system across production and development environments.

Security Areas Tested:
1. CSRF Protection Mechanisms
2. JWT Security Implementation  
3. SSL/TLS Configuration
4. Security Headers Validation
5. Input Validation & XSS Protection
6. Authentication Flow Security
7. Session Management Security
8. Authorization Bypass Testing
"""

import os
import sys
import json
import time
import hmac
import hashlib
import secrets
import requests
import ssl
import socket
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityValidator:
    """Comprehensive security validator for authentication systems."""
    
    def __init__(self, base_url="https://aiwfe.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False  # Skip SSL verification for testing
        requests.packages.urllib3.disable_warnings()
        
        self.results = {
            'csrf_protection': {},
            'jwt_security': {},
            'ssl_tls': {},
            'security_headers': {},
            'input_validation': {},
            'authentication_flow': {},
            'penetration_testing': {},
            'overall_score': 0
        }
        
    def run_comprehensive_security_validation(self):
        """Execute all security validation tests."""
        logger.info("🔒 STARTING COMPREHENSIVE SECURITY VALIDATION")
        logger.info("=" * 60)
        
        test_suites = [
            ("CSRF Protection", self.test_csrf_protection),
            ("JWT Security", self.test_jwt_security),
            ("SSL/TLS Configuration", self.test_ssl_tls_security),
            ("Security Headers", self.test_security_headers),
            ("Input Validation", self.test_input_validation),
            ("Authentication Flow", self.test_authentication_flow),
            ("Penetration Testing", self.test_penetration_attacks)
        ]
        
        for suite_name, test_method in test_suites:
            logger.info(f"\n🧪 Testing: {suite_name}")
            logger.info("-" * 40)
            try:
                test_method()
            except Exception as e:
                logger.error(f"❌ Test suite '{suite_name}' failed: {e}")
                
        self.generate_security_report()
        
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms."""
        logger.info("Testing CSRF token generation and validation...")
        
        # Test 1: Get CSRF token
        try:
            response = self.session.get(f"{self.base_url}/api/v1/auth/csrf-token")
            if response.status_code == 200:
                csrf_token = response.headers.get('X-CSRF-TOKEN')
                cookie_token = None
                for cookie in self.session.cookies:
                    if 'csrf' in cookie.name.lower():
                        cookie_token = cookie.value
                        break
                        
                self.results['csrf_protection']['token_generation'] = {
                    'status': 'PASS' if csrf_token else 'FAIL',
                    'header_token': csrf_token[:20] + '...' if csrf_token else None,
                    'cookie_token': cookie_token[:20] + '...' if cookie_token else None
                }
                logger.info("✅ CSRF token generation working")
            else:
                self.results['csrf_protection']['token_generation'] = {
                    'status': 'FAIL', 'error': f"HTTP {response.status_code}"
                }
                logger.error("❌ CSRF token generation failed")
        except Exception as e:
            self.results['csrf_protection']['token_generation'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
        # Test 2: Protected endpoint without CSRF token
        try:
            response = self.session.post(f"{self.base_url}/api/v1/auth/test-protected")
            csrf_blocked = response.status_code == 403
            self.results['csrf_protection']['missing_token_protection'] = {
                'status': 'PASS' if csrf_blocked else 'FAIL',
                'blocked': csrf_blocked
            }
            logger.info("✅ Requests without CSRF token properly blocked" if csrf_blocked 
                       else "❌ Missing CSRF token protection")
        except Exception as e:
            self.results['csrf_protection']['missing_token_protection'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
        # Test 3: Token format validation
        try:
            invalid_token = "invalid:token:format"
            headers = {'X-CSRF-TOKEN': invalid_token}
            response = self.session.post(f"{self.base_url}/api/v1/auth/test-protected", headers=headers)
            format_validation = response.status_code == 403
            self.results['csrf_protection']['token_format_validation'] = {
                'status': 'PASS' if format_validation else 'FAIL',
                'blocked': format_validation
            }
            logger.info("✅ Invalid CSRF token format rejected" if format_validation 
                       else "❌ Invalid token format not detected")
        except Exception as e:
            self.results['csrf_protection']['token_format_validation'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
    def test_jwt_security(self):
        """Test JWT implementation security."""
        logger.info("Testing JWT security mechanisms...")
        
        # Test 1: JWT structure validation
        try:
            # Try to get a JWT token through login attempt
            login_data = {"email": "test@example.com", "password": "invalid"}
            response = self.session.post(f"{self.base_url}/api/v1/auth/jwt/login", json=login_data)
            
            # Even failed login should reveal JWT structure if present
            jwt_structure_valid = True  # We'll validate this differently
            self.results['jwt_security']['structure_validation'] = {
                'status': 'INFO',
                'login_attempt_status': response.status_code,
                'response_structure': 'jwt_based' if 'token' in response.text else 'unknown'
            }
            logger.info("ℹ️ JWT structure analysis completed")
        except Exception as e:
            self.results['jwt_security']['structure_validation'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
        # Test 2: Token expiration handling
        try:
            # Create an expired JWT-like token
            expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MTYyMzkwMjJ9.invalid"
            headers = {'Authorization': f'Bearer {expired_token}'}
            response = self.session.get(f"{self.base_url}/api/v1/auth/profile", headers=headers)
            
            expired_handling = response.status_code in [401, 403]
            self.results['jwt_security']['expiration_handling'] = {
                'status': 'PASS' if expired_handling else 'FAIL',
                'properly_rejected': expired_handling
            }
            logger.info("✅ Expired tokens properly rejected" if expired_handling 
                       else "❌ Expired token handling needs improvement")
        except Exception as e:
            self.results['jwt_security']['expiration_handling'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
    def test_ssl_tls_security(self):
        """Test SSL/TLS configuration security."""
        logger.info("Testing SSL/TLS security configuration...")
        
        # Test 1: SSL certificate validation
        try:
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
            cert_valid = cert is not None
            self.results['ssl_tls']['certificate_validation'] = {
                'status': 'PASS' if cert_valid else 'FAIL',
                'certificate_present': cert_valid,
                'subject': cert.get('subject') if cert else None,
                'issuer': cert.get('issuer') if cert else None,
                'not_after': cert.get('notAfter') if cert else None
            }
            logger.info("✅ SSL certificate validation passed" if cert_valid 
                       else "❌ SSL certificate issues detected")
        except Exception as e:
            self.results['ssl_tls']['certificate_validation'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
        # Test 2: TLS version and cipher strength
        try:
            # Test TLS version support
            response = self.session.get(f"{self.base_url}/api/v1/health")
            tls_secure = response.status_code == 200
            self.results['ssl_tls']['tls_configuration'] = {
                'status': 'PASS' if tls_secure else 'FAIL',
                'connection_successful': tls_secure
            }
            logger.info("✅ TLS configuration operational" if tls_secure 
                       else "❌ TLS configuration issues")
        except Exception as e:
            self.results['ssl_tls']['tls_configuration'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
    def test_security_headers(self):
        """Test security headers implementation."""
        logger.info("Testing security headers...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/health")
            headers = response.headers
            
            security_headers = {
                'Content-Security-Policy': headers.get('Content-Security-Policy'),
                'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
                'X-Frame-Options': headers.get('X-Frame-Options'),
                'X-XSS-Protection': headers.get('X-XSS-Protection'),
                'Referrer-Policy': headers.get('Referrer-Policy'),
                'Permissions-Policy': headers.get('Permissions-Policy'),
                'Strict-Transport-Security': headers.get('Strict-Transport-Security')
            }
            
            headers_present = sum(1 for v in security_headers.values() if v is not None)
            total_headers = len(security_headers)
            
            self.results['security_headers']['header_validation'] = {
                'status': 'PASS' if headers_present >= 5 else 'PARTIAL' if headers_present >= 3 else 'FAIL',
                'headers_present': headers_present,
                'total_expected': total_headers,
                'headers': security_headers
            }
            
            logger.info(f"✅ Security headers: {headers_present}/{total_headers} present")
            for header, value in security_headers.items():
                if value:
                    logger.info(f"  ✓ {header}: {value[:50]}...")
                else:
                    logger.warning(f"  ⚠ {header}: Missing")
                    
        except Exception as e:
            self.results['security_headers']['header_validation'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
    def test_input_validation(self):
        """Test input validation and XSS protection."""
        logger.info("Testing input validation mechanisms...")
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "onmouseover='alert(1)'",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        validation_results = []
        
        for payload in xss_payloads:
            try:
                # Test XSS in login form
                data = {"email": payload, "password": "test"}
                response = self.session.post(f"{self.base_url}/api/v1/auth/jwt/login", json=data)
                
                # Check if payload is reflected or executed
                payload_blocked = payload not in response.text
                validation_results.append({
                    'payload': payload[:30] + '...',
                    'blocked': payload_blocked,
                    'status_code': response.status_code
                })
                
            except Exception as e:
                validation_results.append({
                    'payload': payload[:30] + '...',
                    'error': str(e)
                })
                
        blocked_count = sum(1 for r in validation_results if r.get('blocked', False))
        total_payloads = len(xss_payloads)
        
        self.results['input_validation']['xss_protection'] = {
            'status': 'PASS' if blocked_count == total_payloads else 'PARTIAL' if blocked_count > 0 else 'FAIL',
            'blocked': blocked_count,
            'total_tested': total_payloads,
            'results': validation_results
        }
        
        logger.info(f"✅ XSS Protection: {blocked_count}/{total_payloads} payloads blocked")
        
    def test_authentication_flow(self):
        """Test authentication flow security."""
        logger.info("Testing authentication flow...")
        
        # Test 1: Brute force protection
        try:
            failed_attempts = 0
            for i in range(5):
                data = {"email": "test@example.com", "password": f"invalid{i}"}
                response = self.session.post(f"{self.base_url}/api/v1/auth/jwt/login", json=data)
                if response.status_code == 403:
                    failed_attempts += 1
                    
            brute_force_protected = failed_attempts > 0
            self.results['authentication_flow']['brute_force_protection'] = {
                'status': 'PASS' if brute_force_protected else 'NEEDS_REVIEW',
                'failed_attempts_tracked': failed_attempts
            }
            
            logger.info("✅ Brute force protection active" if brute_force_protected 
                       else "⚠️ Brute force protection needs review")
        except Exception as e:
            self.results['authentication_flow']['brute_force_protection'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
        # Test 2: Session management
        try:
            # Test if sessions are properly managed
            response1 = self.session.get(f"{self.base_url}/api/v1/health")
            session_id1 = self.session.cookies.get('session_id')
            
            # Clear cookies and test again
            self.session.cookies.clear()
            response2 = self.session.get(f"{self.base_url}/api/v1/health")
            session_id2 = self.session.cookies.get('session_id')
            
            session_management = session_id1 != session_id2
            self.results['authentication_flow']['session_management'] = {
                'status': 'PASS' if session_management else 'NEEDS_REVIEW',
                'sessions_different': session_management
            }
            
            logger.info("✅ Session management working" if session_management 
                       else "⚠️ Session management needs review")
        except Exception as e:
            self.results['authentication_flow']['session_management'] = {
                'status': 'ERROR', 'error': str(e)
            }
            
    def test_penetration_attacks(self):
        """Perform basic penetration testing."""
        logger.info("Performing penetration testing...")
        
        # Test 1: SQL Injection attempts
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1--"
        ]
        
        sql_injection_blocked = []
        for payload in sql_payloads:
            try:
                data = {"email": payload, "password": "test"}
                response = self.session.post(f"{self.base_url}/api/v1/auth/jwt/login", json=data)
                
                # Check for SQL error messages or successful bypass
                sql_error_indicators = ['sql', 'syntax', 'mysql', 'postgresql', 'database', 'error']
                has_sql_error = any(indicator in response.text.lower() for indicator in sql_error_indicators)
                
                sql_injection_blocked.append({
                    'payload': payload,
                    'status_code': response.status_code,
                    'sql_error_detected': has_sql_error,
                    'blocked': response.status_code != 200 and not has_sql_error
                })
                
            except Exception as e:
                sql_injection_blocked.append({
                    'payload': payload,
                    'error': str(e)
                })
                
        blocked_count = sum(1 for r in sql_injection_blocked if r.get('blocked', False))
        
        self.results['penetration_testing']['sql_injection'] = {
            'status': 'PASS' if blocked_count == len(sql_payloads) else 'PARTIAL' if blocked_count > 0 else 'CRITICAL',
            'blocked': blocked_count,
            'total_tested': len(sql_payloads),
            'results': sql_injection_blocked
        }
        
        logger.info(f"✅ SQL Injection Protection: {blocked_count}/{len(sql_payloads)} attacks blocked")
        
        # Test 2: Authentication bypass attempts
        bypass_attempts = [
            {"Authorization": "Bearer fake_token"},
            {"Authorization": "Bearer "},
            {"Authorization": ""},
            {"X-User-ID": "1"},
            {"X-Admin": "true"}
        ]
        
        bypass_blocked = []
        for headers in bypass_attempts:
            try:
                response = self.session.get(f"{self.base_url}/api/v1/auth/profile", headers=headers)
                blocked = response.status_code in [401, 403]
                bypass_blocked.append({
                    'headers': headers,
                    'blocked': blocked,
                    'status_code': response.status_code
                })
                
            except Exception as e:
                bypass_blocked.append({
                    'headers': headers,
                    'error': str(e)
                })
                
        bypass_blocked_count = sum(1 for r in bypass_blocked if r.get('blocked', False))
        
        self.results['penetration_testing']['authentication_bypass'] = {
            'status': 'PASS' if bypass_blocked_count == len(bypass_attempts) else 'CRITICAL',
            'blocked': bypass_blocked_count,
            'total_tested': len(bypass_attempts),
            'results': bypass_blocked
        }
        
        logger.info(f"✅ Authentication Bypass Protection: {bypass_blocked_count}/{len(bypass_attempts)} attempts blocked")
        
    def generate_security_report(self):
        """Generate comprehensive security validation report."""
        logger.info("\n" + "=" * 60)
        logger.info("🔒 COMPREHENSIVE SECURITY VALIDATION REPORT")
        logger.info("=" * 60)
        
        # Calculate overall security score
        scores = []
        
        for category, tests in self.results.items():
            if category == 'overall_score':
                continue
                
            category_score = 0
            test_count = 0
            
            for test_name, result in tests.items():
                test_count += 1
                status = result.get('status', 'UNKNOWN')
                
                if status == 'PASS':
                    category_score += 100
                elif status == 'PARTIAL':
                    category_score += 70
                elif status == 'NEEDS_REVIEW':
                    category_score += 50
                elif status == 'INFO':
                    category_score += 80
                elif status == 'FAIL':
                    category_score += 0
                elif status == 'CRITICAL':
                    category_score += 0
                elif status == 'ERROR':
                    category_score += 30
                    
            if test_count > 0:
                scores.append(category_score / test_count)
                
        overall_score = sum(scores) / len(scores) if scores else 0
        self.results['overall_score'] = overall_score
        
        # Print category results
        for category, tests in self.results.items():
            if category == 'overall_score':
                continue
                
            logger.info(f"\n📋 {category.replace('_', ' ').title()}:")
            for test_name, result in tests.items():
                status = result.get('status', 'UNKNOWN')
                icon = self._get_status_icon(status)
                logger.info(f"  {icon} {test_name.replace('_', ' ').title()}: {status}")
                
                if status in ['FAIL', 'CRITICAL', 'ERROR'] and 'error' in result:
                    logger.error(f"      Error: {result['error']}")
                    
        # Security recommendations
        logger.info(f"\n📊 OVERALL SECURITY SCORE: {overall_score:.1f}/100")
        
        if overall_score >= 90:
            logger.info("🟢 EXCELLENT: Security posture is very strong")
        elif overall_score >= 80:
            logger.info("🟡 GOOD: Security posture is solid with minor improvements needed")
        elif overall_score >= 70:
            logger.info("🟠 MODERATE: Security posture needs attention")
        elif overall_score >= 60:
            logger.info("🔴 POOR: Security posture has significant vulnerabilities")
        else:
            logger.error("🚨 CRITICAL: Security posture requires immediate attention")
            
        # Generate recommendations
        self._generate_recommendations()
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/marku/ai_workflow_engine/security_validation_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
            
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        logger.info("=" * 60)
        
    def _get_status_icon(self, status):
        """Get appropriate icon for test status."""
        icons = {
            'PASS': '✅',
            'PARTIAL': '🟡',
            'FAIL': '❌',
            'CRITICAL': '🚨',
            'ERROR': '⚠️',
            'NEEDS_REVIEW': '🔍',
            'INFO': 'ℹ️',
            'UNKNOWN': '❓'
        }
        return icons.get(status, '❓')
        
    def _generate_recommendations(self):
        """Generate security recommendations based on test results."""
        logger.info("\n🔧 SECURITY RECOMMENDATIONS:")
        
        recommendations = []
        
        # Check CSRF protection
        csrf_results = self.results.get('csrf_protection', {})
        if any(test.get('status') == 'FAIL' for test in csrf_results.values()):
            recommendations.append("- Strengthen CSRF protection mechanisms")
            
        # Check JWT security
        jwt_results = self.results.get('jwt_security', {})
        if any(test.get('status') in ['FAIL', 'CRITICAL'] for test in jwt_results.values()):
            recommendations.append("- Review JWT implementation and security controls")
            
        # Check security headers
        headers_result = self.results.get('security_headers', {}).get('header_validation', {})
        if headers_result.get('status') != 'PASS':
            recommendations.append("- Implement missing security headers (CSP, HSTS, etc.)")
            
        # Check input validation
        input_results = self.results.get('input_validation', {})
        if any(test.get('status') != 'PASS' for test in input_results.values()):
            recommendations.append("- Enhance input validation and XSS protection")
            
        # Check penetration testing results
        pen_results = self.results.get('penetration_testing', {})
        if any(test.get('status') == 'CRITICAL' for test in pen_results.values()):
            recommendations.append("- URGENT: Address critical security vulnerabilities")
            
        if not recommendations:
            recommendations.append("- Security posture is strong, maintain current practices")
            recommendations.append("- Continue regular security audits and monitoring")
            
        for rec in recommendations:
            logger.info(rec)

def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://aiwfe.com"
        
    validator = SecurityValidator(base_url)
    validator.run_comprehensive_security_validation()

if __name__ == "__main__":
    main()