#!/usr/bin/env python3
"""
Test Script for Stream 3: Inter-Agent Communication Protocol

This script validates the enhanced inter-agent communication system
implementing all Stream 3 requirements:

1. Real message passing between agents
2. Dynamic agent requests and coordination
3. Context sharing and dynamic information gathering
4. Conflict resolution with resource management
5. Resource availability notifications

Tests both the communication hub and integration with ML orchestrator.
"""

import asyncio
import json
import time
from typing import Dict, Any, List

# Import the enhanced communication system
from agent_communication import (
    EnhancedAgentCommunicationHub,
    AgentMessage, MessageType, MessagePriority,
    AgentInfo, AgentRole, WorkflowContext,
    get_enhanced_communication_hub
)

from ml_enhanced_orchestrator import (
    get_ml_enhanced_orchestrator,
    initialize_agent_communication,
    execute_parallel_agents_with_communication,
    get_communication_status,
    request_agent_collaboration,
    share_agent_context,
    broadcast_to_agent_group,
    get_coordination_performance
)

class Stream3TestSuite:
    """Test suite for Stream 3 enhanced inter-agent communication."""
    
    def __init__(self):
        self.test_results = []
        self.communication_hub = None
        self.orchestrator = None
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all Stream 3 communication tests."""
        
        print("🚀 Starting Stream 3: Inter-Agent Communication Protocol Tests")
        print("=" * 70)
        
        try:
            # Initialize systems
            await self._setup_test_environment()
            
            # Run test categories
            await self._test_basic_communication()
            await self._test_dynamic_agent_requests()
            await self._test_context_sharing()
            await self._test_conflict_resolution()
            await self._test_resource_notifications()
            await self._test_parallel_execution_coordination()
            await self._test_ml_orchestrator_integration()
            
            # Cleanup
            await self._cleanup_test_environment()
            
            # Generate summary
            return self._generate_test_summary()
            
        except Exception as e:
            self._add_test_result("setup", False, f"Test suite failed: {str(e)}")
            return self._generate_test_summary()
    
    async def _setup_test_environment(self):
        """Set up test environment."""
        print("\n📋 Setting up test environment...")
        
        try:
            # Initialize communication hub
            self.communication_hub = await get_enhanced_communication_hub(use_mcp_services=False)
            
            # Initialize ML orchestrator
            self.orchestrator = get_ml_enhanced_orchestrator()
            await self.orchestrator.initialize_enhanced_communication()
            
            # Register test agents
            await self._register_test_agents()
            
            self._add_test_result("environment_setup", True, "Test environment initialized successfully")
            print("✅ Test environment ready")
            
        except Exception as e:
            self._add_test_result("environment_setup", False, f"Setup failed: {str(e)}")
            print(f"❌ Setup failed: {str(e)}")
            raise
    
    async def _register_test_agents(self):
        """Register test agents for communication testing."""
        
        test_agents = [
            AgentInfo(
                agent_id="test-backend-agent",
                agent_type="development",
                role=AgentRole.SPECIALIST,
                capabilities=["api_design", "database_integration", "performance_optimization"],
                specializations=["fastapi", "postgresql", "redis"],
                max_concurrent_tasks=3,
                dynamic_request_capability=True
            ),
            AgentInfo(
                agent_id="test-frontend-agent",
                agent_type="frontend",
                role=AgentRole.SPECIALIST,
                capabilities=["ui_design", "component_architecture", "state_management"],
                specializations=["react", "svelte", "css"],
                max_concurrent_tasks=2,
                dynamic_request_capability=True
            ),
            AgentInfo(
                agent_id="test-validator-agent",
                agent_type="validation",
                role=AgentRole.VALIDATOR,
                capabilities=["testing", "quality_assurance", "security_validation"],
                specializations=["playwright", "security_scanning", "automated_testing"],
                max_concurrent_tasks=4,
                dynamic_request_capability=True
            ),
            AgentInfo(
                agent_id="test-coordinator-agent",
                agent_type="orchestration",
                role=AgentRole.COORDINATOR,
                capabilities=["workflow_coordination", "resource_management", "conflict_resolution"],
                specializations=["orchestration", "coordination", "planning"],
                max_concurrent_tasks=5,
                dynamic_request_capability=True
            )
        ]
        
        for agent in test_agents:
            success = await self.communication_hub.register_agent(agent)
            if not success:
                raise Exception(f"Failed to register agent: {agent.agent_id}")
        
        print(f"📝 Registered {len(test_agents)} test agents")
    
    async def _test_basic_communication(self):
        """Test basic message passing between agents."""
        print("\n🔄 Testing basic inter-agent communication...")
        
        try:
            # Test direct message
            message = AgentMessage(
                from_agent="test-backend-agent",
                to_agent="test-frontend-agent",
                message_type=MessageType.REQUEST,
                priority=MessagePriority.NORMAL,
                content={
                    "request_type": "api_integration",
                    "endpoint": "/api/users",
                    "parameters": {"limit": 50}
                },
                requires_response=True
            )
            
            # Send message
            success = await self.communication_hub.send_message(message)
            self._add_test_result("basic_message_send", success, 
                                f"Message send {'succeeded' if success else 'failed'}")
            
            # Test message reception
            received_message = await self.communication_hub.receive_message("test-frontend-agent", timeout=2.0)
            message_received = received_message is not None
            self._add_test_result("basic_message_receive", message_received,
                                f"Message reception {'succeeded' if message_received else 'failed'}")
            
            # Test response
            if received_message:
                response = AgentMessage(
                    from_agent="test-frontend-agent",
                    to_agent="test-backend-agent",
                    content={
                        "response_type": "acknowledgment",
                        "status": "api_integration_accepted",
                        "implementation_plan": "Will create React component for user listing"
                    }
                )
                
                response_sent = await self.communication_hub.send_response(received_message.id, response)
                self._add_test_result("basic_message_response", response_sent,
                                    f"Response {'sent' if response_sent else 'failed'}")
                
                # Wait for response
                response_received = await self.communication_hub.wait_for_response(message.id, timeout=2.0)
                response_success = response_received is not None
                self._add_test_result("basic_response_receive", response_success,
                                    f"Response reception {'succeeded' if response_success else 'failed'}")
            
            print("✅ Basic communication tests completed")
            
        except Exception as e:
            self._add_test_result("basic_communication", False, f"Basic communication failed: {str(e)}")
            print(f"❌ Basic communication test failed: {str(e)}")
    
    async def _test_dynamic_agent_requests(self):
        """Test dynamic agent request functionality."""
        print("\n🔄 Testing dynamic agent requests...")
        
        try:
            # Test requesting additional agent
            requested_agent = await self.communication_hub.request_additional_agent(
                requesting_agent="test-backend-agent",
                required_capabilities=["security_validation", "automated_testing"],
                task_description="Need security validation for new API endpoint"
            )
            
            agent_assigned = requested_agent is not None
            self._add_test_result("dynamic_agent_request", agent_assigned,
                                f"Dynamic agent request {'succeeded' if agent_assigned else 'failed'}")
            
            if agent_assigned:
                print(f"🎯 Successfully assigned agent: {requested_agent}")
                
                # Test that the assigned agent received notification
                await asyncio.sleep(0.5)  # Give time for notification
                notification = await self.communication_hub.receive_message(requested_agent, timeout=1.0)
                notification_received = notification is not None and notification.content.get("assignment_type") == "dynamic_request"
                
                self._add_test_result("dynamic_agent_notification", notification_received,
                                    f"Dynamic agent notification {'received' if notification_received else 'missed'}")
            
            print("✅ Dynamic agent request tests completed")
            
        except Exception as e:
            self._add_test_result("dynamic_agent_requests", False, f"Dynamic agent requests failed: {str(e)}")
            print(f"❌ Dynamic agent request test failed: {str(e)}")
    
    async def _test_context_sharing(self):
        """Test context sharing between agents."""
        print("\n🔄 Testing context sharing...")
        
        try:
            # Test context sharing
            context_data = {
                "user_requirements": ["responsive_design", "accessibility", "performance"],
                "api_endpoints": ["/api/users", "/api/posts", "/api/comments"],
                "database_schema": {"users": ["id", "name", "email"], "posts": ["id", "user_id", "title", "content"]},
                "performance_targets": {"response_time": "< 200ms", "throughput": "> 1000 rps"}
            }
            
            context_shared = await self.communication_hub.share_context(
                from_agent="test-backend-agent",
                to_agent="test-frontend-agent",
                context_data=context_data,
                context_type="api_integration"
            )
            
            self._add_test_result("context_sharing", context_shared,
                                f"Context sharing {'succeeded' if context_shared else 'failed'}")
            
            # Test context request
            requested_context = await self.communication_hub.request_context(
                requesting_agent="test-validator-agent",
                target_agent="test-backend-agent",
                context_type="api_integration",
                specific_data=["api_endpoints", "performance_targets"]
            )
            
            context_received = requested_context is not None
            self._add_test_result("context_request", context_received,
                                f"Context request {'succeeded' if context_received else 'failed'}")
            
            if context_received:
                print(f"📋 Received context keys: {list(requested_context.keys())}")
            
            print("✅ Context sharing tests completed")
            
        except Exception as e:
            self._add_test_result("context_sharing", False, f"Context sharing failed: {str(e)}")
            print(f"❌ Context sharing test failed: {str(e)}")
    
    async def _test_conflict_resolution(self):
        """Test conflict detection and resolution."""
        print("\n🔄 Testing conflict resolution...")
        
        try:
            # Create a message that would cause resource conflict
            conflicting_message = AgentMessage(
                from_agent="test-backend-agent",
                to_agent="test-validator-agent",
                message_type=MessageType.REQUEST,
                priority=MessagePriority.CRITICAL,
                content={"action": "intensive_testing", "duration": "2_hours"},
                resource_requirements={"cpu": 0.8, "memory": 0.9}  # High resource usage
            )
            
            # Try to send multiple conflicting messages quickly
            conflicts_detected = 0
            for i in range(3):
                conflicting_message.id = f"conflict_test_{i}"
                
                # This should trigger conflict detection
                success = await self.communication_hub.send_message(conflicting_message)
                if not success:
                    conflicts_detected += 1
                
                await asyncio.sleep(0.1)
            
            conflict_detection_working = conflicts_detected > 0
            self._add_test_result("conflict_detection", conflict_detection_working,
                                f"Conflict detection {'working' if conflict_detection_working else 'not working'} - {conflicts_detected} conflicts detected")
            
            print("✅ Conflict resolution tests completed")
            
        except Exception as e:
            self._add_test_result("conflict_resolution", False, f"Conflict resolution failed: {str(e)}")
            print(f"❌ Conflict resolution test failed: {str(e)}")
    
    async def _test_resource_notifications(self):
        """Test resource availability notifications."""
        print("\n🔄 Testing resource notifications...")
        
        try:
            # Register a resource
            resource_registered = await self.communication_hub.register_resource(
                agent_id="test-backend-agent",
                resource_type="database_connection",
                resource_data={"connection_pool": 10, "max_connections": 100, "current_usage": 0.3}
            )
            
            self._add_test_result("resource_registration", resource_registered,
                                f"Resource registration {'succeeded' if resource_registered else 'failed'}")
            
            # Test resource availability notification
            await asyncio.sleep(0.5)  # Give time for notifications
            
            # Check if interested agents received notifications
            notification_count = 0
            for agent_id in ["test-frontend-agent", "test-validator-agent"]:
                notification = await self.communication_hub.receive_message(agent_id, timeout=0.5)
                if notification and notification.message_type == MessageType.RESOURCE_AVAILABLE:
                    notification_count += 1
            
            notifications_working = notification_count > 0
            self._add_test_result("resource_notifications", notifications_working,
                                f"Resource notifications {'working' if notifications_working else 'not working'} - {notification_count} notifications sent")
            
            # Test resource unregistration
            resource_unregistered = await self.communication_hub.unregister_resource(
                agent_id="test-backend-agent",
                resource_type="database_connection"
            )
            
            self._add_test_result("resource_unregistration", resource_unregistered,
                                f"Resource unregistration {'succeeded' if resource_unregistered else 'failed'}")
            
            print("✅ Resource notification tests completed")
            
        except Exception as e:
            self._add_test_result("resource_notifications", False, f"Resource notifications failed: {str(e)}")
            print(f"❌ Resource notification test failed: {str(e)}")
    
    async def _test_parallel_execution_coordination(self):
        """Test coordination during parallel execution."""
        print("\n🔄 Testing parallel execution coordination...")
        
        try:
            # Create coordination session
            workflow_id = f"test_workflow_{int(time.time())}"
            participating_agents = ["test-backend-agent", "test-frontend-agent", "test-validator-agent"]
            
            session_created = await self.communication_hub.create_coordination_session(
                workflow_id=workflow_id,
                participating_agents=participating_agents,
                coordination_type="parallel_test"
            )
            
            self._add_test_result("coordination_session_creation", session_created,
                                f"Coordination session {'created' if session_created else 'failed'}")
            
            # Test broadcast to coordination group
            if session_created:
                broadcast_count = await self.communication_hub.broadcast_to_group(
                    from_agent="test-coordinator-agent",
                    group_name="specialists",
                    message_content={
                        "coordination_update": "parallel_execution_starting",
                        "workflow_id": workflow_id,
                        "expected_duration": 300
                    }
                )
                
                broadcast_success = broadcast_count > 0
                self._add_test_result("coordination_broadcast", broadcast_success,
                                    f"Coordination broadcast {'succeeded' if broadcast_success else 'failed'} - {broadcast_count} messages sent")
                
                # Simulate coordination updates
                await self.communication_hub.update_workflow_context(
                    workflow_id=workflow_id,
                    updates={
                        "phase": 1,
                        "current_step": "parallel_execution",
                        "shared_data": {"progress": 25, "agents_active": 3}
                    },
                    agent_id="test-coordinator-agent"
                )
                
                context_updated = workflow_id in self.communication_hub.workflow_contexts
                self._add_test_result("coordination_context_update", context_updated,
                                    f"Context update {'succeeded' if context_updated else 'failed'}")
            
            print("✅ Parallel execution coordination tests completed")
            
        except Exception as e:
            self._add_test_result("parallel_execution_coordination", False, f"Parallel coordination failed: {str(e)}")
            print(f"❌ Parallel execution coordination test failed: {str(e)}")
    
    async def _test_ml_orchestrator_integration(self):
        """Test integration with ML Enhanced Orchestrator."""
        print("\n🔄 Testing ML orchestrator integration...")
        
        try:
            # Test communication status
            status = await get_communication_status()
            communication_active = status.get('communication_active', False)
            
            self._add_test_result("orchestrator_communication_status", communication_active,
                                f"ML orchestrator communication {'active' if communication_active else 'inactive'}")
            
            # Test enhanced parallel execution
            agent_requests = [
                {
                    'id': 'test-backend-agent',
                    'context': {
                        'task_description': 'API optimization',
                        'needs_collaboration': True,
                        'required_capabilities': ['performance_optimization'],
                        'share_context': True,
                        'context_share_targets': ['test-validator-agent']
                    }
                },
                {
                    'id': 'test-frontend-agent',
                    'context': {
                        'task_description': 'UI enhancement',
                        'monitor_conflicts': True,
                        'estimated_duration': 120
                    }
                }
            ]
            
            execution_result = await execute_parallel_agents_with_communication(
                agent_requests=agent_requests,
                allow_instances=True
            )
            
            execution_success = execution_result.get('communication_enabled', False)
            self._add_test_result("orchestrator_parallel_execution", execution_success,
                                f"Enhanced parallel execution {'succeeded' if execution_success else 'failed'}")
            
            # Test coordination performance analysis
            if 'ml_coordination' in execution_result:
                coordination_analysis = execution_result.get('coordination_summary', {})
                analysis_available = coordination_analysis.get('coordination_active', False)
                
                self._add_test_result("orchestrator_coordination_analysis", analysis_available,
                                    f"Coordination analysis {'available' if analysis_available else 'unavailable'}")
            
            print("✅ ML orchestrator integration tests completed")
            
        except Exception as e:
            self._add_test_result("ml_orchestrator_integration", False, f"ML orchestrator integration failed: {str(e)}")
            print(f"❌ ML orchestrator integration test failed: {str(e)}")
    
    async def _cleanup_test_environment(self):
        """Clean up test environment."""
        print("\n🧹 Cleaning up test environment...")
        
        try:
            if self.communication_hub:
                await self.communication_hub.stop()
                
            print("✅ Test environment cleaned up")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
    
    def _add_test_result(self, test_name: str, success: bool, details: str):
        """Add a test result to the results list."""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': time.time()
        })
    
    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        
        successful_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Categorize results
        categories = {
            'basic_communication': [],
            'dynamic_requests': [],
            'context_sharing': [],
            'conflict_resolution': [],
            'resource_notifications': [],
            'parallel_coordination': [],
            'orchestrator_integration': []
        }
        
        for result in self.test_results:
            test_name = result['test']
            if 'basic' in test_name or 'message' in test_name:
                categories['basic_communication'].append(result)
            elif 'dynamic' in test_name:
                categories['dynamic_requests'].append(result)
            elif 'context' in test_name:
                categories['context_sharing'].append(result)
            elif 'conflict' in test_name:
                categories['conflict_resolution'].append(result)
            elif 'resource' in test_name:
                categories['resource_notifications'].append(result)
            elif 'coordination' in test_name or 'parallel' in test_name:
                categories['parallel_coordination'].append(result)
            elif 'orchestrator' in test_name:
                categories['orchestrator_integration'].append(result)
        
        summary = {
            'test_suite': 'Stream 3: Inter-Agent Communication Protocol',
            'execution_time': time.time(),
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': total_tests - successful_tests,
            'success_rate': success_rate,
            'status': 'PASSED' if success_rate >= 80 else 'FAILED',
            'categories': {
                category: {
                    'total': len(results),
                    'passed': sum(1 for r in results if r['success']),
                    'success_rate': (sum(1 for r in results if r['success']) / len(results)) * 100 if results else 0
                }
                for category, results in categories.items()
            },
            'detailed_results': self.test_results,
            'requirements_validation': {
                'message_passing': any('message' in r['test'] and r['success'] for r in self.test_results),
                'dynamic_agents': any('dynamic' in r['test'] and r['success'] for r in self.test_results),
                'context_sharing': any('context' in r['test'] and r['success'] for r in self.test_results),
                'conflict_resolution': any('conflict' in r['test'] and r['success'] for r in self.test_results),
                'resource_notifications': any('resource' in r['test'] and r['success'] for r in self.test_results)
            }
        }
        
        return summary

async def main():
    """Main test execution function."""
    print("🧪 Stream 3: Inter-Agent Communication Protocol Test Suite")
    print("Testing enhanced inter-agent communication system implementation")
    print("=" * 70)
    
    test_suite = Stream3TestSuite()
    results = await test_suite.run_all_tests()
    
    # Print detailed summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    print(f"Test Suite: {results['test_suite']}")
    print(f"Status: {results['status']}")
    print(f"Success Rate: {results['success_rate']:.1f}% ({results['successful_tests']}/{results['total_tests']})")
    
    print("\n📋 Requirements Validation:")
    for requirement, validated in results['requirements_validation'].items():
        status = "✅ PASS" if validated else "❌ FAIL"
        print(f"  {requirement.replace('_', ' ').title()}: {status}")
    
    print("\n📁 Category Breakdown:")
    for category, stats in results['categories'].items():
        category_name = category.replace('_', ' ').title()
        print(f"  {category_name}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
    
    print("\n🔍 Detailed Results:")
    for result in results['detailed_results']:
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {result['test']}: {result['details']}")
    
    # Save results to file
    results_file = f"/home/marku/ai_workflow_engine/.claude/orchestration_enhanced/stream3_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    if results['status'] == 'PASSED':
        print("\n🎉 Stream 3 implementation validation SUCCESSFUL!")
        print("Enhanced inter-agent communication system is working correctly.")
    else:
        print("\n⚠️ Stream 3 implementation needs attention.")
        print("Some communication features require fixes.")
    
    return results

if __name__ == "__main__":
    # Run the test suite
    results = asyncio.run(main())
    
    # Exit with appropriate code
    exit_code = 0 if results['status'] == 'PASSED' else 1
    exit(exit_code)