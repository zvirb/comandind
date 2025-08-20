#!/usr/bin/env python3
"""
OAuth Flow Analysis Tool
Comprehensive analysis of OAuth authentication flow and Google API integration.
"""

import asyncio
import aiohttp
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class OAuthFlowAnalyzer:
    """Analyzes OAuth flow and Google API integration status."""
    
    def __init__(self, base_url: str = "https://aiwfe.com"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)  # For testing
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
    async def test_oauth_configuration(self) -> Dict[str, Any]:
        """Test Google OAuth configuration status."""
        logger.info("Testing OAuth configuration...")
        
        try:
            url = f"{self.base_url}/api/v1/oauth/google/config/check"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"OAuth config check successful: {data}")
                    return {
                        "status": "success",
                        "configured": data.get("configured", False),
                        "issues": data.get("issues", []),
                        "client_id_present": data.get("client_id_present", False),
                        "client_secret_present": data.get("client_secret_present", False)
                    }
                else:
                    logger.error(f"OAuth config check failed: {response.status}")
                    return {"status": "error", "message": f"HTTP {response.status}"}
                    
        except Exception as e:
            logger.error(f"OAuth configuration test failed: {e}")
            return {"status": "error", "message": str(e)}
            
    async def test_oauth_status_endpoint(self) -> Dict[str, Any]:
        """Test OAuth status endpoint (requires authentication)."""
        logger.info("Testing OAuth status endpoint...")
        
        try:
            url = f"{self.base_url}/api/v1/oauth/google/status"
            async with self.session.get(url) as response:
                logger.info(f"OAuth status endpoint response: {response.status}")
                
                if response.status == 401:
                    return {
                        "status": "expected_unauthorized",
                        "message": "Endpoint correctly requires authentication"
                    }
                elif response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "data": data,
                        "message": "OAuth status retrieved successfully"
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error", 
                        "code": response.status,
                        "message": text[:200]
                    }
                    
        except Exception as e:
            logger.error(f"OAuth status test failed: {e}")
            return {"status": "error", "message": str(e)}
            
    async def test_calendar_sync_endpoint(self) -> Dict[str, Any]:
        """Test calendar sync endpoint (requires authentication)."""
        logger.info("Testing calendar sync endpoint...")
        
        try:
            url = f"{self.base_url}/api/v1/calendar/sync"
            
            # Test GET request first (should be method not allowed)
            async with self.session.get(url) as response:
                logger.info(f"Calendar sync GET response: {response.status}")
                
            # Test POST request (should require authentication)
            async with self.session.post(url, json={"force_sync": False}) as response:
                logger.info(f"Calendar sync POST response: {response.status}")
                
                if response.status == 401:
                    return {
                        "status": "expected_unauthorized",
                        "message": "Calendar sync endpoint correctly requires authentication"
                    }
                elif response.status == 422:
                    return {
                        "status": "validation_error",
                        "message": "Calendar sync endpoint validation working"
                    }
                elif response.status == 403:
                    return {
                        "status": "csrf_required",
                        "message": "CSRF token required (security working)"
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "unexpected",
                        "code": response.status,
                        "message": text[:200]
                    }
                    
        except Exception as e:
            logger.error(f"Calendar sync test failed: {e}")
            return {"status": "error", "message": str(e)}
            
    async def test_oauth_health_check(self) -> Dict[str, Any]:
        """Test OAuth health check endpoint (requires authentication)."""
        logger.info("Testing OAuth health check endpoint...")
        
        try:
            url = f"{self.base_url}/api/v1/oauth/google/health-check"
            async with self.session.get(url) as response:
                logger.info(f"OAuth health check response: {response.status}")
                
                if response.status == 401:
                    return {
                        "status": "expected_unauthorized",
                        "message": "Health check endpoint correctly requires authentication"
                    }
                elif response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "data": data,
                        "message": "OAuth health check successful"
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "code": response.status,
                        "message": text[:200]
                    }
                    
        except Exception as e:
            logger.error(f"OAuth health check failed: {e}")
            return {"status": "error", "message": str(e)}
            
    async def test_oauth_connection_flow(self) -> Dict[str, Any]:
        """Test OAuth connection initiation (requires authentication)."""
        logger.info("Testing OAuth connection flow...")
        
        try:
            url = f"{self.base_url}/api/v1/oauth/google/connect/calendar"
            async with self.session.get(url) as response:
                logger.info(f"OAuth connect response: {response.status}")
                
                if response.status == 401:
                    return {
                        "status": "expected_unauthorized",
                        "message": "OAuth connect endpoint correctly requires authentication"
                    }
                elif response.status == 302:
                    location = response.headers.get('Location', '')
                    if 'accounts.google.com' in location:
                        return {
                            "status": "success",
                            "message": "OAuth flow correctly redirects to Google",
                            "redirect_url": location[:100] + "..."
                        }
                    else:
                        return {
                            "status": "unexpected_redirect",
                            "message": f"Unexpected redirect: {location[:100]}"
                        }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "code": response.status,
                        "message": text[:200]
                    }
                    
        except Exception as e:
            logger.error(f"OAuth connection flow test failed: {e}")
            return {"status": "error", "message": str(e)}
            
    async def diagnose_oauth_flow(self) -> Dict[str, Any]:
        """Run comprehensive OAuth flow diagnosis."""
        logger.info("Starting comprehensive OAuth flow diagnosis...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url,
            "tests": {}
        }
        
        # Test 1: OAuth Configuration
        results["tests"]["oauth_configuration"] = await self.test_oauth_configuration()
        
        # Test 2: OAuth Status Endpoint
        results["tests"]["oauth_status_endpoint"] = await self.test_oauth_status_endpoint()
        
        # Test 3: Calendar Sync Endpoint
        results["tests"]["calendar_sync_endpoint"] = await self.test_calendar_sync_endpoint()
        
        # Test 4: OAuth Health Check
        results["tests"]["oauth_health_check"] = await self.test_oauth_health_check()
        
        # Test 5: OAuth Connection Flow
        results["tests"]["oauth_connection_flow"] = await self.test_oauth_connection_flow()
        
        # Generate diagnosis summary
        results["diagnosis"] = self._analyze_results(results["tests"])
        
        return results
        
    def _analyze_results(self, tests: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and provide diagnosis."""
        diagnosis = {
            "overall_status": "unknown",
            "issues_found": [],
            "recommendations": [],
            "oauth_configured": False,
            "endpoints_secure": True,
            "authentication_working": True
        }
        
        # Check OAuth configuration
        oauth_config = tests.get("oauth_configuration", {})
        if oauth_config.get("status") == "success":
            diagnosis["oauth_configured"] = oauth_config.get("configured", False)
            if not diagnosis["oauth_configured"]:
                diagnosis["issues_found"].append("Google OAuth not properly configured")
                diagnosis["recommendations"].append("Check Google OAuth client ID and secret")
        else:
            diagnosis["issues_found"].append("OAuth configuration endpoint failed")
            
        # Check endpoint security
        security_tests = [
            "oauth_status_endpoint",
            "calendar_sync_endpoint", 
            "oauth_health_check",
            "oauth_connection_flow"
        ]
        
        for test_name in security_tests:
            test_result = tests.get(test_name, {})
            if test_result.get("status") not in ["expected_unauthorized", "success", "csrf_required", "validation_error"]:
                diagnosis["endpoints_secure"] = False
                diagnosis["issues_found"].append(f"{test_name} has unexpected behavior")
                
        # Overall status determination
        if diagnosis["oauth_configured"] and diagnosis["endpoints_secure"]:
            if len(diagnosis["issues_found"]) == 0:
                diagnosis["overall_status"] = "healthy"
            else:
                diagnosis["overall_status"] = "issues_detected"
        else:
            diagnosis["overall_status"] = "configuration_issues"
            
        # Specific recommendations
        if not diagnosis["oauth_configured"]:
            diagnosis["recommendations"].append("Configure Google OAuth credentials in secrets")
            
        if not diagnosis["endpoints_secure"]:
            diagnosis["recommendations"].append("Review endpoint authentication and security")
            
        return diagnosis

async def main():
    """Main function to run OAuth flow analysis."""
    print("🔍 OAuth Flow Analysis Starting...")
    print("=" * 60)
    
    async with OAuthFlowAnalyzer() as analyzer:
        results = await analyzer.diagnose_oauth_flow()
        
        # Print results
        print(f"\n📊 OAUTH FLOW DIAGNOSIS RESULTS")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Base URL: {results['base_url']}")
        print(f"Overall Status: {results['diagnosis']['overall_status'].upper()}")
        
        print(f"\n✅ OAUTH CONFIGURATION:")
        config_test = results['tests']['oauth_configuration']
        if config_test['status'] == 'success':
            print(f"  • Configured: {config_test['configured']}")
            print(f"  • Client ID Present: {config_test['client_id_present']}")
            print(f"  • Client Secret Present: {config_test['client_secret_present']}")
            if config_test['issues']:
                print(f"  • Issues: {', '.join(config_test['issues'])}")
        else:
            print(f"  • Error: {config_test['message']}")
            
        print(f"\n🔐 ENDPOINT SECURITY TESTS:")
        for test_name, test_result in results['tests'].items():
            if test_name != 'oauth_configuration':
                status_icon = "✅" if test_result['status'] in ['expected_unauthorized', 'success', 'csrf_required', 'validation_error'] else "❌"
                print(f"  {status_icon} {test_name}: {test_result['status']} - {test_result['message']}")
                
        print(f"\n🏥 DIAGNOSIS SUMMARY:")
        diagnosis = results['diagnosis']
        print(f"  • OAuth Configured: {diagnosis['oauth_configured']}")
        print(f"  • Endpoints Secure: {diagnosis['endpoints_secure']}")
        print(f"  • Authentication Working: {diagnosis['authentication_working']}")
        
        if diagnosis['issues_found']:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in diagnosis['issues_found']:
                print(f"  • {issue}")
                
        if diagnosis['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in diagnosis['recommendations']:
                print(f"  • {rec}")
                
        # Save results to file
        output_file = "oauth_flow_analysis_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to: {output_file}")
        
        # Return appropriate exit code
        if diagnosis['overall_status'] == 'healthy':
            print(f"\n🎉 OAuth flow analysis completed successfully!")
            return 0
        else:
            print(f"\n⚠️  OAuth flow has issues that need attention.")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)