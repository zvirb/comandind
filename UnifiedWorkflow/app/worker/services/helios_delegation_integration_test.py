"""
Helios Delegation Integration Test

This script tests the integration between Smart Router delegation and 
Helios expert team coordination to ensure the system works end-to-end.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeliosDelegationIntegrationTest:
    """Test suite for Helios delegation integration."""
    
    def __init__(self):
        self.test_cases = [
            {
                "name": "Simple Task (Should Not Delegate)",
                "request": "What time is it?",
                "expected_delegation": False,
                "expected_complexity": "low"
            },
            {
                "name": "Multi-Domain Analysis (Should Delegate)",
                "request": "I need a comprehensive business and technical analysis of implementing AI in our company, including strategic planning and risk assessment.",
                "expected_delegation": True,
                "expected_complexity": "high"
            },
            {
                "name": "Strategic Planning (Should Delegate)",
                "request": "Help me create a 5-year roadmap for digital transformation with expert recommendations from multiple perspectives.",
                "expected_delegation": True,
                "expected_complexity": "high"
            },
            {
                "name": "Creative Project (May Delegate)",
                "request": "I need creative ideas for a marketing campaign that combines technical innovation with business strategy.",
                "expected_delegation": True,
                "expected_complexity": "medium"
            },
            {
                "name": "Tool Capability (Should Not Delegate)",
                "request": "Schedule a meeting for tomorrow at 2 PM with John about project updates.",
                "expected_delegation": False,
                "expected_complexity": "low"
            }
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("🚀 Starting Helios Delegation Integration Tests")
        
        results = {
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": [],
            "overall_status": "unknown"
        }
        
        for i, test_case in enumerate(self.test_cases):
            logger.info(f"🧪 Running Test {i+1}/{len(self.test_cases)}: {test_case['name']}")
            
            try:
                test_result = await self._run_single_test(test_case)
                results["test_results"].append(test_result)
                
                if test_result["passed"]:
                    results["passed"] += 1
                    logger.info(f"✅ Test {i+1} PASSED")
                else:
                    results["failed"] += 1
                    logger.warning(f"❌ Test {i+1} FAILED: {test_result.get('reason', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"💥 Test {i+1} ERROR: {str(e)}")
                results["failed"] += 1
                results["test_results"].append({
                    "test_name": test_case["name"],
                    "passed": False,
                    "reason": f"Test execution error: {str(e)}",
                    "error": True
                })
        
        # Determine overall status
        if results["failed"] == 0:
            results["overall_status"] = "ALL_PASSED"
        elif results["passed"] > results["failed"]:
            results["overall_status"] = "MOSTLY_PASSED"
        else:
            results["overall_status"] = "MOSTLY_FAILED"
        
        logger.info(f"🎯 Integration Tests Complete: {results['passed']}/{results['total_tests']} passed")
        return results
    
    async def _run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case."""
        
        # Test delegation decision analysis
        delegation_result = await self._test_delegation_analysis(test_case)
        
        # Test tool registration
        tool_registration_result = await self._test_tool_registration()
        
        # Test service availability
        service_availability_result = await self._test_service_availability()
        
        # Combine results
        all_checks_passed = (
            delegation_result["passed"] and
            tool_registration_result["passed"] and
            service_availability_result["passed"]
        )
        
        return {
            "test_name": test_case["name"],
            "request": test_case["request"],
            "passed": all_checks_passed,
            "delegation_analysis": delegation_result,
            "tool_registration": tool_registration_result,
            "service_availability": service_availability_result,
            "reason": "All checks passed" if all_checks_passed else "One or more checks failed"
        }
    
    async def _test_delegation_analysis(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test the delegation decision analysis."""
        try:
            from worker.services.smart_router_delegation_enhancement import DelegationAwareSmartRouter
            
            router = DelegationAwareSmartRouter()
            
            # Analyze delegation potential
            delegation_decision = await router._analyze_delegation_potential(
                test_case["request"], 
                user_id=1
            )
            
            # Check if delegation decision matches expectations
            expected_delegation = test_case["expected_delegation"]
            actual_delegation = delegation_decision.should_delegate
            
            passed = (expected_delegation == actual_delegation)
            
            return {
                "passed": passed,
                "expected_delegation": expected_delegation,
                "actual_delegation": actual_delegation,
                "confidence": delegation_decision.confidence,
                "complexity_score": delegation_decision.complexity_score,
                "triggers": [trigger.value for trigger in delegation_decision.triggers],
                "reasoning": delegation_decision.reasoning
            }
            
        except Exception as e:
            logger.error(f"Delegation analysis test error: {e}")
            return {
                "passed": False,
                "error": str(e),
                "message": "Failed to analyze delegation potential"
            }
    
    async def _test_tool_registration(self) -> Dict[str, Any]:
        """Test that the Helios delegation tool is properly registered."""
        try:
            from worker.tool_registry import AVAILABLE_TOOLS
            from worker.tool_handlers import TOOL_HANDLER_MAP
            
            # Check tool registry
            helios_tool = None
            for tool in AVAILABLE_TOOLS:
                if tool["id"] == "delegate_to_helios_team":
                    helios_tool = tool
                    break
            
            tool_in_registry = helios_tool is not None
            
            # Check tool handler mapping
            handler_exists = "delegate_to_helios_team" in TOOL_HANDLER_MAP
            
            # Check handler function
            handler_callable = False
            if handler_exists:
                handler_func = TOOL_HANDLER_MAP["delegate_to_helios_team"]
                handler_callable = callable(handler_func)
            
            passed = tool_in_registry and handler_exists and handler_callable
            
            return {
                "passed": passed,
                "tool_in_registry": tool_in_registry,
                "handler_exists": handler_exists,
                "handler_callable": handler_callable,
                "tool_description": helios_tool["description"] if helios_tool else None
            }
            
        except Exception as e:
            logger.error(f"Tool registration test error: {e}")
            return {
                "passed": False,
                "error": str(e),
                "message": "Failed to verify tool registration"
            }
    
    async def _test_service_availability(self) -> Dict[str, Any]:
        """Test that required services are available."""
        try:
            # Test Helios delegation service import
            delegation_service_available = False
            try:
                from shared.services.helios_delegation_service import HeliosDelegationService
                delegation_service_available = True
            except ImportError as e:
                logger.warning(f"Helios delegation service not available: {e}")
            
            # Test Helios control unit import
            control_unit_available = False
            try:
                from worker.services.helios_control_unit import HeliosControlUnit
                control_unit_available = True
            except ImportError as e:
                logger.warning(f"Helios control unit not available: {e}")
            
            # Test enhanced router import
            enhanced_router_available = False
            try:
                from worker.services.smart_router_delegation_enhancement import DelegationAwareSmartRouter
                enhanced_router_available = True
            except ImportError as e:
                logger.warning(f"Enhanced delegation router not available: {e}")
            
            passed = delegation_service_available and control_unit_available and enhanced_router_available
            
            return {
                "passed": passed,
                "delegation_service_available": delegation_service_available,
                "control_unit_available": control_unit_available,
                "enhanced_router_available": enhanced_router_available
            }
            
        except Exception as e:
            logger.error(f"Service availability test error: {e}")
            return {
                "passed": False,
                "error": str(e),
                "message": "Failed to verify service availability"
            }
    
    async def test_end_to_end_delegation(self, user_request: str) -> Dict[str, Any]:
        """Test end-to-end delegation workflow."""
        logger.info(f"🔄 Testing end-to-end delegation for: {user_request}")
        
        try:
            from worker.services.smart_router_delegation_enhancement import DelegationAwareSmartRouter
            
            router = DelegationAwareSmartRouter()
            
            # Collect streaming updates
            updates = []
            
            async def test_callback(update):
                updates.append(update)
                logger.info(f"📡 Update: {update.get('type', 'unknown')} - {update.get('message', '')}")
            
            # Process request
            result = await router.process_user_request(
                user_input=user_request,
                user_id=1,
                session_id="test_session",
                stream_callback=test_callback,
                context={}
            )
            
            return {
                "success": True,
                "result": result,
                "updates": updates,
                "processing_method": result.get("processing_method", "unknown"),
                "delegation_occurred": result.get("expert_team_analysis", False)
            }
            
        except Exception as e:
            logger.error(f"End-to-end test error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "End-to-end delegation test failed"
            }


async def main():
    """Run the integration tests."""
    test_suite = HeliosDelegationIntegrationTest()
    
    # Run standard test suite
    results = await test_suite.run_all_tests()
    
    print("\n" + "="*60)
    print("🎯 HELIOS DELEGATION INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Overall Status: {results['overall_status']}")
    print("="*60)
    
    # Print detailed results
    for i, test_result in enumerate(results["test_results"]):
        status = "✅ PASS" if test_result["passed"] else "❌ FAIL"
        print(f"{i+1}. {test_result['test_name']}: {status}")
        if not test_result["passed"]:
            print(f"   Reason: {test_result.get('reason', 'Unknown')}")
    
    print("\n" + "="*60)
    
    # Run end-to-end test
    print("🔄 Running End-to-End Delegation Test...")
    e2e_result = await test_suite.test_end_to_end_delegation(
        "I need a comprehensive strategic analysis of implementing blockchain technology in our financial services company, considering technical, business, regulatory, and risk perspectives."
    )
    
    if e2e_result["success"]:
        print("✅ End-to-End Test: SUCCESS")
        print(f"Processing Method: {e2e_result['processing_method']}")
        print(f"Delegation Occurred: {e2e_result['delegation_occurred']}")
        print(f"Updates Received: {len(e2e_result['updates'])}")
    else:
        print("❌ End-to-End Test: FAILED")
        print(f"Error: {e2e_result.get('error', 'Unknown error')}")
    
    print("="*60)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())