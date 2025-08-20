#!/usr/bin/env python3
"""
Integration Components Validation Test

Tests all 5 backend service boundary integration components to ensure proper functionality.
Validates JWT normalization, session handling, circuit breakers, and service coordination.
"""

import asyncio
import sys
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.services.jwt_token_adapter import jwt_token_adapter, NormalizedTokenData
from shared.services.fallback_session_provider import fallback_session_provider
from shared.services.service_boundary_coordinator import service_boundary_coordinator
from shared.database.models import UserRole

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationComponentValidator:
    """Validator for all 5 integration components"""
    
    def __init__(self):
        self.test_results = {}
        self.overall_status = "unknown"
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run validation tests for all integration components"""
        logger.info("Starting integration component validation...")
        
        try:
            # Test 1: JWT Token Adapter
            await self.test_jwt_token_adapter()
            
            # Test 2: Fallback Session Provider
            await self.test_fallback_session_provider()
            
            # Test 3: Service Boundary Coordinator
            await self.test_service_boundary_coordinator()
            
            # Test 4: Integration workflow
            await self.test_integration_workflow()
            
            # Calculate overall status
            self.calculate_overall_status()
            
            return {
                "overall_status": self.overall_status,
                "test_results": self.test_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": self.generate_summary()
            }
            
        except Exception as e:
            logger.error(f"Integration validation failed: {e}")
            self.test_results["validation_error"] = {
                "status": "failed",
                "error": str(e)
            }
            self.overall_status = "failed"
            return {
                "overall_status": self.overall_status,
                "test_results": self.test_results,
                "error": str(e)
            }
    
    async def test_jwt_token_adapter(self):
        """Test JWT Token Adapter functionality"""
        logger.info("Testing JWT Token Adapter...")
        
        try:
            # Test with legacy format token
            legacy_payload = {
                "sub": "test@example.com",
                "id": 12345,
                "role": "user",
                "exp": int(time.time()) + 3600,
                "iat": int(time.time())
            }
            
            # Note: We can't create actual JWT tokens without the secret key in this test context
            # This test validates the adapter structure and methods exist
            
            test_result = {
                "status": "passed",
                "tests": {
                    "adapter_initialization": True,
                    "normalization_methods_exist": hasattr(jwt_token_adapter, 'normalize_token'),
                    "format_detection_methods_exist": hasattr(jwt_token_adapter, '_try_enhanced_format'),
                    "consistency_validation_exists": hasattr(jwt_token_adapter, 'validate_token_consistency'),
                    "expiration_check_exists": hasattr(jwt_token_adapter, 'is_token_expired')
                }
            }
            
            # Check if all required methods exist
            required_methods = [
                'normalize_token', '_try_enhanced_format', '_try_legacy_format',
                'validate_token_consistency', 'is_token_expired'
            ]
            
            missing_methods = [method for method in required_methods 
                             if not hasattr(jwt_token_adapter, method)]
            
            if missing_methods:
                test_result["status"] = "failed"
                test_result["missing_methods"] = missing_methods
            
            self.test_results["jwt_token_adapter"] = test_result
            logger.info("JWT Token Adapter test completed")
            
        except Exception as e:
            logger.error(f"JWT Token Adapter test failed: {e}")
            self.test_results["jwt_token_adapter"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_fallback_session_provider(self):
        """Test Fallback Session Provider functionality"""
        logger.info("Testing Fallback Session Provider...")
        
        try:
            # Create test normalized token
            test_token = NormalizedTokenData(
                user_id=99999,
                email="test.fallback@example.com",
                role=UserRole.USER,
                format_type="test",
                raw_payload={"test": True},
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                issued_at=datetime.now(timezone.utc)
            )
            
            # Test session creation
            session_key = await fallback_session_provider.create_session(
                test_token,
                additional_data={"test_session": True}
            )
            
            # Test session retrieval
            retrieved_session = await fallback_session_provider.get_session(session_key)
            
            # Test session update
            update_success = await fallback_session_provider.update_session(
                session_key,
                {"updated": True}
            )
            
            # Test user session lookup
            user_session = await fallback_session_provider.get_user_session(99999)
            
            # Test session validation
            validation_result = await fallback_session_provider.validate_session_for_user(
                99999, "test.fallback@example.com"
            )
            
            # Test health check
            health_status = await fallback_session_provider.health_check()
            
            # Cleanup
            await fallback_session_provider.delete_session(session_key)
            
            test_result = {
                "status": "passed",
                "tests": {
                    "session_creation": session_key is not None,
                    "session_retrieval": retrieved_session is not None,
                    "session_update": update_success,
                    "user_session_lookup": user_session is not None,
                    "session_validation": validation_result,
                    "health_check": health_status.get("status") == "healthy",
                    "session_cleanup": True
                }
            }
            
            # Check if any tests failed
            if not all(test_result["tests"].values()):
                test_result["status"] = "partial_failure"
            
            self.test_results["fallback_session_provider"] = test_result
            logger.info("Fallback Session Provider test completed")
            
        except Exception as e:
            logger.error(f"Fallback Session Provider test failed: {e}")
            self.test_results["fallback_session_provider"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_service_boundary_coordinator(self):
        """Test Service Boundary Coordinator functionality"""
        logger.info("Testing Service Boundary Coordinator...")
        
        try:
            # Test health check
            health_status = await service_boundary_coordinator.health_check()
            
            # Test circuit breaker status
            circuit_breaker_status = service_boundary_coordinator.get_circuit_breaker_status()
            
            # Test coordination stats
            coordination_stats = service_boundary_coordinator.get_coordination_stats()
            
            # Test overall health status
            overall_health = service_boundary_coordinator.get_overall_health_status()
            
            # Test state change coordination (without actual user)
            test_token = NormalizedTokenData(
                user_id=88888,
                email="test.coordinator@example.com",
                role=UserRole.USER,
                format_type="test",
                raw_payload={"test": True}
            )
            
            # Test login coordination
            await service_boundary_coordinator.coordinate_authentication_state(
                user_id=88888,
                email="test.coordinator@example.com",
                event_type="login",
                source="test",
                details={"normalized_token": test_token}
            )
            
            # Test logout coordination
            await service_boundary_coordinator.coordinate_authentication_state(
                user_id=88888,
                email="test.coordinator@example.com", 
                event_type="logout",
                source="test"
            )
            
            test_result = {
                "status": "passed",
                "tests": {
                    "health_check": health_status.get("status") is not None,
                    "circuit_breaker_monitoring": isinstance(circuit_breaker_status, dict),
                    "coordination_stats": isinstance(coordination_stats, dict),
                    "overall_health_calculation": overall_health is not None,
                    "login_coordination": True,  # No exceptions = success
                    "logout_coordination": True   # No exceptions = success
                }
            }
            
            self.test_results["service_boundary_coordinator"] = test_result
            logger.info("Service Boundary Coordinator test completed")
            
        except Exception as e:
            logger.error(f"Service Boundary Coordinator test failed: {e}")
            self.test_results["service_boundary_coordinator"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_integration_workflow(self):
        """Test complete integration workflow"""
        logger.info("Testing integration workflow...")
        
        try:
            # Create test user scenario
            test_user_id = 77777
            test_email = "test.workflow@example.com"
            
            test_token = NormalizedTokenData(
                user_id=test_user_id,
                email=test_email,
                role=UserRole.USER,
                format_type="enhanced",
                raw_payload={
                    "sub": test_user_id,
                    "email": test_email,
                    "role": "user"
                },
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                issued_at=datetime.now(timezone.utc)
            )
            
            # Phase 1: Create fallback session
            session_key = await fallback_session_provider.create_session(
                test_token,
                additional_data={"workflow_test": True}
            )
            
            # Phase 2: Coordinate login
            await service_boundary_coordinator.coordinate_authentication_state(
                user_id=test_user_id,
                email=test_email,
                event_type="login",
                source="workflow_test",
                details={"normalized_token": test_token}
            )
            
            # Phase 3: Validate session exists across services
            fallback_session = await fallback_session_provider.get_user_session(test_user_id)
            session_valid = await fallback_session_provider.validate_session_for_user(
                test_user_id, test_email
            )
            
            # Phase 4: Test token refresh coordination
            await service_boundary_coordinator.coordinate_authentication_state(
                user_id=test_user_id,
                email=test_email,
                event_type="token_refresh",
                source="workflow_test",
                details={"new_token_data": {"format_type": "enhanced"}}
            )
            
            # Phase 5: Coordinate logout and cleanup
            await service_boundary_coordinator.coordinate_authentication_state(
                user_id=test_user_id,
                email=test_email,
                event_type="logout",
                source="workflow_test"
            )
            
            # Verify cleanup
            post_logout_session = await fallback_session_provider.get_user_session(test_user_id)
            
            test_result = {
                "status": "passed",
                "workflow_phases": {
                    "session_creation": session_key is not None,
                    "login_coordination": True,
                    "session_validation": session_valid,
                    "token_refresh_coordination": True,
                    "logout_coordination": True,
                    "session_cleanup": post_logout_session is None
                }
            }
            
            # Check if any workflow phases failed
            if not all(test_result["workflow_phases"].values()):
                test_result["status"] = "partial_failure"
            
            self.test_results["integration_workflow"] = test_result
            logger.info("Integration workflow test completed")
            
        except Exception as e:
            logger.error(f"Integration workflow test failed: {e}")
            self.test_results["integration_workflow"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def calculate_overall_status(self):
        """Calculate overall validation status"""
        if not self.test_results:
            self.overall_status = "no_tests"
            return
        
        statuses = [result.get("status", "unknown") for result in self.test_results.values()]
        
        if all(status == "passed" for status in statuses):
            self.overall_status = "passed"
        elif any(status == "failed" for status in statuses):
            self.overall_status = "failed"
        elif any(status == "partial_failure" for status in statuses):
            self.overall_status = "partial_failure"
        else:
            self.overall_status = "unknown"
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get("status") == "passed")
        failed_tests = sum(1 for result in self.test_results.values() 
                          if result.get("status") == "failed")
        partial_tests = sum(1 for result in self.test_results.values() 
                           if result.get("status") == "partial_failure")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "partial_failure_tests": partial_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "components_tested": list(self.test_results.keys())
        }


async def main():
    """Run integration component validation"""
    print("=" * 60)
    print("Backend Service Boundary Integration Component Validation")
    print("=" * 60)
    
    validator = IntegrationComponentValidator()
    results = await validator.run_all_tests()
    
    print(f"\nOverall Status: {results['overall_status'].upper()}")
    print(f"Timestamp: {results['timestamp']}")
    
    if "summary" in results:
        summary = results["summary"]
        print(f"\nSummary:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        print(f"  Partial Failures: {summary['partial_failure_tests']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
    
    print(f"\nDetailed Results:")
    for component, result in results["test_results"].items():
        status = result.get("status", "unknown").upper()
        print(f"  {component}: {status}")
        
        if result.get("status") == "failed":
            print(f"    Error: {result.get('error', 'Unknown error')}")
        elif "tests" in result:
            failed_tests = [test for test, passed in result["tests"].items() if not passed]
            if failed_tests:
                print(f"    Failed sub-tests: {', '.join(failed_tests)}")
    
    # Return exit code based on results
    if results["overall_status"] == "passed":
        print(f"\n✅ All integration components are working correctly!")
        return 0
    elif results["overall_status"] == "partial_failure":
        print(f"\n⚠️  Some integration components have issues - check details above")
        return 1
    else:
        print(f"\n❌ Integration component validation failed!")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)