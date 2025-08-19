#!/usr/bin/env python3
"""
Authenticated Endpoint Testing Infrastructure

Provides comprehensive testing of API endpoints with proper authentication
to prevent false positives from treating 401 errors as "healthy" status.

This system addresses the specific authentication validation failures identified
in the orchestration audit where HTTP 401 responses were incorrectly marked as healthy.
"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import jwt
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationType(Enum):
    """Types of authentication methods supported."""
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth" 
    API_KEY = "api_key"
    SESSION_COOKIE = "session_cookie"
    NONE = "none"

class EndpointTestResult(Enum):
    """Possible endpoint test results."""
    SUCCESS = "success"
    AUTH_FAILURE = "auth_failure"  # 401, 403
    SERVER_ERROR = "server_error"  # 500+
    CLIENT_ERROR = "client_error"  # 400-499 except auth
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"

@dataclass
class AuthenticationCredential:
    """Authentication credential configuration."""
    auth_type: AuthenticationType
    credential_data: Dict[str, Any]
    description: str
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class EndpointTestDefinition:
    """Definition of an endpoint test."""
    name: str
    url: str
    method: str = "GET"
    auth_required: bool = True
    auth_type: AuthenticationType = AuthenticationType.BEARER_TOKEN
    expected_status_codes: List[int] = None
    timeout: int = 10
    headers: Dict[str, str] = None
    body: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.expected_status_codes is None:
            self.expected_status_codes = [200, 201, 202, 204] if self.auth_required else [200]
        if self.headers is None:
            self.headers = {}
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AuthenticatedEndpointTestResult:
    """Result of an authenticated endpoint test."""
    endpoint_name: str
    url: str
    method: str
    test_result: EndpointTestResult
    status_code: Optional[int]
    response_time_ms: float
    auth_type_used: AuthenticationType
    auth_successful: bool
    response_headers: Dict[str, str]
    response_body_preview: str
    error_message: Optional[str] = None
    timestamp: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AuthenticationTestReport:
    """Comprehensive authentication test report."""
    test_id: str
    timestamp: str
    endpoints_tested: int
    endpoints_passed: int
    endpoints_failed: int
    authentication_types_tested: List[str]
    test_results: List[AuthenticatedEndpointTestResult]
    authentication_issues: List[str]
    critical_findings: List[str]
    recommendations: List[str]
    overall_success: bool
    execution_time_ms: float

class AuthenticatedEndpointTester:
    """
    Comprehensive authenticated endpoint testing system.
    
    Prevents false positives by properly handling authentication and
    correctly categorizing HTTP status codes:
    - 200-299: Success
    - 401, 403: Authentication/Authorization failure (NOT healthy)
    - 400-499: Client error
    - 500+: Server error
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_id = f"auth_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.credentials: Dict[str, AuthenticationCredential] = {}
        self.endpoints: List[EndpointTestDefinition] = []
        
        # Default critical endpoints for AI Workflow Engine
        self.default_endpoints = [
            EndpointTestDefinition(
                name="categories_api",
                url="https://aiwfe.com/api/v1/categories",
                method="GET",
                auth_required=True,
                auth_type=AuthenticationType.BEARER_TOKEN,
                expected_status_codes=[200],
                metadata={"criticality": "high", "user_facing": True}
            ),
            EndpointTestDefinition(
                name="tasks_api",
                url="https://aiwfe.com/api/v1/tasks", 
                method="GET",
                auth_required=True,
                auth_type=AuthenticationType.BEARER_TOKEN,
                expected_status_codes=[200],
                metadata={"criticality": "high", "user_facing": True}
            ),
            EndpointTestDefinition(
                name="calendar_events_api",
                url="https://aiwfe.com/api/v1/calendar/events",
                method="GET", 
                auth_required=True,
                auth_type=AuthenticationType.BEARER_TOKEN,
                expected_status_codes=[200],
                metadata={"criticality": "high", "user_facing": True}
            ),
            EndpointTestDefinition(
                name="calendar_sync_auto",
                url="https://aiwfe.com/api/v1/calendar/sync/auto",
                method="POST",
                auth_required=True,
                auth_type=AuthenticationType.BEARER_TOKEN,
                expected_status_codes=[200, 201],
                metadata={"criticality": "medium", "background_task": True}
            ),
            EndpointTestDefinition(
                name="health_check",
                url="https://aiwfe.com/health",
                method="GET",
                auth_required=False,
                auth_type=AuthenticationType.NONE,
                expected_status_codes=[200],
                metadata={"criticality": "high", "public": True}
            ),
            EndpointTestDefinition(
                name="monitoring_metrics",
                url="https://aiwfe.com/api/v1/monitoring/metrics",
                method="GET", 
                auth_required=False,  # Based on log evidence showing 200 responses
                auth_type=AuthenticationType.NONE,
                expected_status_codes=[200],
                metadata={"criticality": "medium", "monitoring": True}
            )
        ]
        
        self._load_configuration()

    def _load_configuration(self):
        """Load endpoint and credential configuration."""
        # Load endpoints from config or use defaults
        endpoints_config = self.config.get('endpoints', [])
        if endpoints_config:
            for endpoint_config in endpoints_config:
                self.endpoints.append(EndpointTestDefinition(**endpoint_config))
        else:
            self.endpoints = self.default_endpoints.copy()
            logger.info(f"Using {len(self.endpoints)} default endpoints")

        # Load authentication credentials
        credentials_config = self.config.get('credentials', {})
        for cred_name, cred_config in credentials_config.items():
            self.credentials[cred_name] = AuthenticationCredential(**cred_config)

    async def generate_test_authentication_tokens(self) -> Dict[str, AuthenticationCredential]:
        """
        Generate test authentication tokens for validation purposes.
        
        This creates isolated test tokens that don't interfere with production.
        """
        test_credentials = {}
        
        # Generate JWT test token
        try:
            jwt_secret = self.config.get('jwt_secret', 'test_validation_secret_key')
            test_payload = {
                'sub': 'test_user_validation',
                'username': 'validation_test_user',
                'user_id': 99999,  # High ID to avoid conflicts
                'exp': int(time.time()) + 3600,  # 1 hour expiry
                'iat': int(time.time()),
                'validation_token': True
            }
            
            test_jwt_token = jwt.encode(test_payload, jwt_secret, algorithm='HS256')
            
            test_credentials['jwt_bearer'] = AuthenticationCredential(
                auth_type=AuthenticationType.BEARER_TOKEN,
                credential_data={'token': test_jwt_token},
                description="Test JWT Bearer token for validation",
                expires_at=datetime.fromtimestamp(test_payload['exp'], timezone.utc).isoformat(),
                metadata={'generated_for_testing': True, 'user_id': 99999}
            )
            
            logger.info("✅ Generated JWT test token")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate JWT test token: {e}")

        # Generate API Key test credential
        test_api_key = hashlib.sha256(f"test_validation_{self.test_id}".encode()).hexdigest()[:32]
        test_credentials['api_key'] = AuthenticationCredential(
            auth_type=AuthenticationType.API_KEY,
            credential_data={'api_key': test_api_key, 'header_name': 'X-API-Key'},
            description="Test API key for validation",
            metadata={'generated_for_testing': True}
        )

        # Add any configured credentials
        test_credentials.update(self.credentials)
        
        return test_credentials

    async def test_all_endpoints(self) -> AuthenticationTestReport:
        """
        Execute comprehensive authenticated endpoint testing.
        
        Returns detailed report with proper authentication status classification.
        """
        start_time = time.time()
        logger.info(f"🚀 Starting authenticated endpoint testing - ID: {self.test_id}")
        
        test_results = []
        authentication_issues = []
        critical_findings = []
        
        # Generate test authentication credentials
        logger.info("🔐 Generating test authentication credentials...")
        test_credentials = await self.generate_test_authentication_tokens()
        
        if not test_credentials:
            critical_findings.append("No authentication credentials available for testing")
            
        # Test each endpoint
        for endpoint in self.endpoints:
            logger.info(f"🔍 Testing endpoint: {endpoint.name} ({endpoint.method} {endpoint.url})")
            
            endpoint_result = await self._test_single_endpoint(endpoint, test_credentials)
            test_results.append(endpoint_result)
            
            # Analyze result for issues
            if endpoint_result.test_result == EndpointTestResult.AUTH_FAILURE:
                auth_issue = f"Authentication failed for {endpoint.name}: {endpoint_result.error_message}"
                authentication_issues.append(auth_issue)
                
                if endpoint.metadata.get('criticality') == 'high':
                    critical_findings.append(f"Critical endpoint {endpoint.name} failing authentication")
            
            elif endpoint_result.test_result == EndpointTestResult.SERVER_ERROR:
                critical_findings.append(f"Server error on {endpoint.name}: HTTP {endpoint_result.status_code}")

        # Calculate summary statistics
        endpoints_passed = sum(1 for result in test_results if result.test_result == EndpointTestResult.SUCCESS)
        endpoints_failed = len(test_results) - endpoints_passed
        
        auth_types_tested = list(set(result.auth_type_used.value for result in test_results))
        
        execution_time = (time.time() - start_time) * 1000
        overall_success = endpoints_failed == 0 and len(critical_findings) == 0
        
        # Generate recommendations
        recommendations = self._generate_authentication_recommendations(
            test_results, authentication_issues, critical_findings
        )

        logger.info(f"✅ Endpoint testing complete - Success: {overall_success}")
        logger.info(f"📊 Results: {endpoints_passed} passed, {endpoints_failed} failed")

        return AuthenticationTestReport(
            test_id=self.test_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            endpoints_tested=len(test_results),
            endpoints_passed=endpoints_passed,
            endpoints_failed=endpoints_failed,
            authentication_types_tested=auth_types_tested,
            test_results=test_results,
            authentication_issues=authentication_issues,
            critical_findings=critical_findings,
            recommendations=recommendations,
            overall_success=overall_success,
            execution_time_ms=execution_time
        )

    async def _test_single_endpoint(self, endpoint: EndpointTestDefinition, 
                                  credentials: Dict[str, AuthenticationCredential]) -> AuthenticatedEndpointTestResult:
        """Test a single endpoint with authentication."""
        start_time = time.time()
        
        try:
            # Prepare request
            headers = endpoint.headers.copy()
            auth = None
            auth_type_used = endpoint.auth_type
            
            # Apply authentication if required
            if endpoint.auth_required:
                auth_applied = False
                
                # Find appropriate credential
                for cred_name, credential in credentials.items():
                    if credential.auth_type == endpoint.auth_type:
                        if credential.auth_type == AuthenticationType.BEARER_TOKEN:
                            headers['Authorization'] = f"Bearer {credential.credential_data['token']}"
                            auth_applied = True
                            break
                        elif credential.auth_type == AuthenticationType.API_KEY:
                            header_name = credential.credential_data.get('header_name', 'X-API-Key')
                            headers[header_name] = credential.credential_data['api_key']
                            auth_applied = True
                            break
                        elif credential.auth_type == AuthenticationType.BASIC_AUTH:
                            auth = HTTPBasicAuth(
                                credential.credential_data['username'],
                                credential.credential_data['password']
                            )
                            auth_applied = True
                            break
                
                if not auth_applied:
                    logger.warning(f"⚠️  No suitable credential found for {endpoint.name} ({endpoint.auth_type.value})")
            else:
                auth_type_used = AuthenticationType.NONE

            # Make request
            response = requests.request(
                method=endpoint.method,
                url=endpoint.url,
                headers=headers,
                auth=auth,
                json=endpoint.body,
                timeout=endpoint.timeout,
                verify=True
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Analyze response
            test_result, auth_successful, error_message = self._analyze_response(
                response, endpoint.expected_status_codes, endpoint.auth_required
            )
            
            # Get response preview (truncated)
            response_preview = response.text[:500] if response.text else ""
            if len(response.text) > 500:
                response_preview += "... (truncated)"

            return AuthenticatedEndpointTestResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method,
                test_result=test_result,
                status_code=response.status_code,
                response_time_ms=execution_time,
                auth_type_used=auth_type_used,
                auth_successful=auth_successful,
                response_headers=dict(response.headers),
                response_body_preview=response_preview,
                error_message=error_message,
                metadata=endpoint.metadata.copy()
            )

        except requests.exceptions.ConnectTimeout:
            execution_time = (time.time() - start_time) * 1000
            return AuthenticatedEndpointTestResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method,
                test_result=EndpointTestResult.TIMEOUT,
                status_code=None,
                response_time_ms=execution_time,
                auth_type_used=auth_type_used,
                auth_successful=False,
                response_headers={},
                response_body_preview="",
                error_message=f"Request timeout after {endpoint.timeout}s",
                metadata=endpoint.metadata.copy()
            )

        except requests.exceptions.ConnectionError as e:
            execution_time = (time.time() - start_time) * 1000
            return AuthenticatedEndpointTestResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method,
                test_result=EndpointTestResult.CONNECTION_ERROR,
                status_code=None,
                response_time_ms=execution_time,
                auth_type_used=auth_type_used,
                auth_successful=False,
                response_headers={},
                response_body_preview="",
                error_message=f"Connection error: {str(e)}",
                metadata=endpoint.metadata.copy()
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Unexpected error testing {endpoint.name}: {e}")
            logger.error(traceback.format_exc())
            
            return AuthenticatedEndpointTestResult(
                endpoint_name=endpoint.name,
                url=endpoint.url,
                method=endpoint.method,
                test_result=EndpointTestResult.CONNECTION_ERROR,
                status_code=None,
                response_time_ms=execution_time,
                auth_type_used=auth_type_used,
                auth_successful=False,
                response_headers={},
                response_body_preview="",
                error_message=f"Test exception: {str(e)}",
                metadata=endpoint.metadata.copy()
            )

    def _analyze_response(self, response: requests.Response, expected_status_codes: List[int], 
                         auth_required: bool) -> Tuple[EndpointTestResult, bool, Optional[str]]:
        """
        Analyze HTTP response and properly categorize the result.
        
        This is the critical function that prevents false positives by
        correctly handling authentication errors.
        """
        status_code = response.status_code
        
        # Success cases
        if status_code in expected_status_codes:
            return EndpointTestResult.SUCCESS, True, None
        
        # Authentication/Authorization failures - CRITICAL: These are NOT healthy!
        if status_code in [401, 403]:
            auth_successful = False
            if status_code == 401:
                error_message = "Authentication failed: Invalid or missing credentials"
            else:  # 403
                error_message = "Authorization failed: Insufficient permissions"
            return EndpointTestResult.AUTH_FAILURE, auth_successful, error_message
        
        # Server errors
        if status_code >= 500:
            return EndpointTestResult.SERVER_ERROR, auth_required, f"Server error: HTTP {status_code}"
        
        # Other client errors
        if 400 <= status_code < 500:
            return EndpointTestResult.CLIENT_ERROR, auth_required, f"Client error: HTTP {status_code}"
        
        # Unexpected status codes
        return EndpointTestResult.CLIENT_ERROR, False, f"Unexpected status code: {status_code}"

    def _generate_authentication_recommendations(self, test_results: List[AuthenticatedEndpointTestResult],
                                               authentication_issues: List[str],
                                               critical_findings: List[str]) -> List[str]:
        """Generate specific recommendations based on authentication test results."""
        recommendations = []
        
        # Critical findings recommendations
        if critical_findings:
            recommendations.append("CRITICAL: Address server errors and authentication failures immediately")
            
        # Authentication-specific recommendations
        auth_failures = [r for r in test_results if r.test_result == EndpointTestResult.AUTH_FAILURE]
        if auth_failures:
            recommendations.append(
                f"Fix authentication for {len(auth_failures)} failing endpoints - "
                "401/403 errors indicate authentication system problems"
            )
            
            # Check if all auth failures are the same type
            failing_endpoints = [r.endpoint_name for r in auth_failures]
            if len(failing_endpoints) > 1:
                recommendations.append(f"Authentication failing on multiple endpoints: {', '.join(failing_endpoints)}")
            
        # Server error recommendations  
        server_errors = [r for r in test_results if r.test_result == EndpointTestResult.SERVER_ERROR]
        if server_errors:
            recommendations.append(
                f"CRITICAL: Fix {len(server_errors)} endpoints returning server errors (500+)"
            )
            
        # Success case recommendations
        if not auth_failures and not server_errors and not critical_findings:
            recommendations.append(
                "All endpoint authentication tests passed - authentication system functioning correctly"
            )
            
        # Performance recommendations
        slow_endpoints = [r for r in test_results if r.response_time_ms > 2000]  # 2 second threshold
        if slow_endpoints:
            recommendations.append(
                f"Performance: {len(slow_endpoints)} endpoints are slow (>2s response time)"
            )

        return recommendations

    async def save_test_report(self, report: AuthenticationTestReport, 
                             output_path: Optional[Path] = None) -> Path:
        """Save authentication test report to file."""
        if output_path is None:
            output_path = Path(f".claude/logs/auth_test_report_{report.test_id}.json")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dictionaries for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"💾 Authentication test report saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    # Example usage
    config = {
        'jwt_secret': 'test_secret_key_for_development',
        'credentials': {
            'production_test': {
                'auth_type': 'bearer_token',
                'credential_data': {'token': 'test_token_placeholder'},
                'description': 'Production test token'
            }
        },
        'endpoints': [
            # Uses default endpoints if not specified
        ]
    }
    
    tester = AuthenticatedEndpointTester(config)
    
    # Run authentication tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        test_report = loop.run_until_complete(tester.test_all_endpoints())
        
        print("\n" + "="*80)
        print("AUTHENTICATED ENDPOINT TEST REPORT")
        print("="*80)
        print(f"Test ID: {test_report.test_id}")
        print(f"Overall Success: {test_report.overall_success}")
        print(f"Endpoints Tested: {test_report.endpoints_tested}")
        print(f"Endpoints Passed: {test_report.endpoints_passed}")
        print(f"Endpoints Failed: {test_report.endpoints_failed}")
        print(f"Execution Time: {test_report.execution_time_ms:.2f}ms")
        print()
        
        if test_report.critical_findings:
            print("❌ CRITICAL FINDINGS:")
            for finding in test_report.critical_findings:
                print(f"   - {finding}")
            print()
        
        if test_report.authentication_issues:
            print("🔐 AUTHENTICATION ISSUES:")
            for issue in test_report.authentication_issues:
                print(f"   - {issue}")
            print()
        
        if test_report.recommendations:
            print("💡 RECOMMENDATIONS:")
            for rec in test_report.recommendations:
                print(f"   - {rec}")
            print()
        
        # Show detailed results
        print("📋 DETAILED RESULTS:")
        for result in test_report.test_results:
            status_emoji = "✅" if result.test_result == EndpointTestResult.SUCCESS else "❌"
            print(f"   {status_emoji} {result.endpoint_name}: {result.test_result.value} "
                  f"(HTTP {result.status_code}, {result.response_time_ms:.0f}ms)")
        
        # Save report
        loop.run_until_complete(tester.save_test_report(test_report))
        
    finally:
        loop.close()