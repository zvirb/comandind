#!/usr/bin/env python3
"""
Test Script for Parallel Execution Engine

Validates the parallel execution capabilities implemented in the MCP Integration Layer.
Tests multiple Task tool calls, resource coordination, error isolation, and progress tracking.
"""

import asyncio
import json
import time
import logging
from typing import List, Dict, Any

# Import the enhanced MCP integration layer
from mcp_integration_layer import (
    MCPIntegrationLayer,
    ParallelTaskManager,
    AgentTask,
    AgentResult,
    WorkflowPhase,
    create_task_call,
    batch_task_calls,
    execute_task_batches
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParallelExecutionTest:
    """Test suite for parallel execution engine."""
    
    def __init__(self):
        self.integration_layer = None
        self.test_results: List[Dict[str, Any]] = []
    
    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up parallel execution test environment")
        
        # Initialize integration layer with moderate concurrency
        self.integration_layer = MCPIntegrationLayer(
            workflow_id="test_parallel_execution",
            max_concurrent_tasks=8
        )
        
        # Register test agents
        await self._register_test_agents()
        
        logger.info("Test environment setup complete")
    
    async def _register_test_agents(self):
        """Register test agents for parallel execution testing."""
        test_agents = [
            {
                "agent_id": "backend_specialist_1",
                "agent_type": "backend-gateway-expert",
                "capabilities": ["api_design", "database_optimization", "container_management"],
                "specializations": ["python", "fastapi", "postgresql"]
            },
            {
                "agent_id": "frontend_specialist_1", 
                "agent_type": "webui-architect",
                "capabilities": ["component_design", "styling", "user_experience"],
                "specializations": ["react", "css", "javascript"]
            },
            {
                "agent_id": "documentation_specialist_1",
                "agent_type": "documentation-specialist", 
                "capabilities": ["api_docs", "user_guides", "architecture_docs"],
                "specializations": ["markdown", "technical_writing", "diagrams"]
            },
            {
                "agent_id": "security_specialist_1",
                "agent_type": "security-validator",
                "capabilities": ["penetration_testing", "vulnerability_assessment", "compliance"],
                "specializations": ["owasp", "encryption", "authentication"]
            },
            {
                "agent_id": "test_specialist_1",
                "agent_type": "test-automation-engineer",
                "capabilities": ["automated_testing", "performance_testing", "ci_cd"],
                "specializations": ["pytest", "selenium", "load_testing"]
            }
        ]
        
        for agent in test_agents:
            success = await self.integration_layer.register_agent(
                agent["agent_id"],
                agent["agent_type"], 
                agent["capabilities"],
                agent["specializations"]
            )
            
            if success:
                logger.info(f"Registered test agent: {agent['agent_id']}")
            else:
                logger.error(f"Failed to register test agent: {agent['agent_id']}")
    
    async def test_basic_parallel_execution(self) -> Dict[str, Any]:
        """Test basic parallel execution of multiple tasks."""
        logger.info("=== Testing Basic Parallel Execution ===")
        
        start_time = time.time()
        
        # Create multiple task calls
        task_calls = [
            create_task_call(
                agent_id="backend_specialist_1",
                task_type="api_implementation",
                description="Implement REST API endpoints",
                context_data={"endpoints": ["users", "projects", "tasks"]}
            ),
            create_task_call(
                agent_id="frontend_specialist_1", 
                task_type="component_development",
                description="Develop React components",
                context_data={"components": ["UserList", "ProjectCard", "TaskBoard"]}
            ),
            create_task_call(
                agent_id="documentation_specialist_1",
                task_type="api_documentation", 
                description="Create API documentation",
                context_data={"apis": ["REST", "GraphQL", "WebSocket"]}
            )
        ]
        
        # Execute tasks in parallel
        results = await self.integration_layer.execute_multiple_task_calls(task_calls)
        
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_tasks = sum(1 for r in results if r.success)
        
        test_result = {
            "test_name": "basic_parallel_execution",
            "execution_time_seconds": execution_time,
            "total_tasks": len(results),
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / len(results) if results else 0,
            "parallel_efficiency": len(results) / execution_time if execution_time > 0 else 0,
            "status": "PASSED" if successful_tasks == len(results) else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Basic parallel execution test: {test_result['status']}")
        logger.info(f"Tasks: {successful_tasks}/{len(results)}, Time: {execution_time:.2f}s")
        
        return test_result
    
    async def test_resource_coordination(self) -> Dict[str, Any]:
        """Test resource coordination and conflict prevention."""
        logger.info("=== Testing Resource Coordination ===")
        
        start_time = time.time()
        
        # Create tasks that might conflict on resources
        task_calls = [
            create_task_call(
                agent_id="backend_specialist_1",
                task_type="database_migration",
                description="Perform database migration",
                context_data={"resource_type": "database"}
            ),
            create_task_call(
                agent_id="backend_specialist_1",  # Same agent, different task
                task_type="api_optimization", 
                description="Optimize API performance",
                context_data={"resource_type": "backend_services"}
            ),
            create_task_call(
                agent_id="security_specialist_1",
                task_type="security_audit",
                description="Perform security audit", 
                context_data={"resource_type": "backend_services"}
            )
        ]
        
        # Execute with coordination
        results = await self.integration_layer.execute_multiple_task_calls(task_calls)
        
        execution_time = time.time() - start_time
        
        # Check resource locks during execution
        status = self.integration_layer.get_parallel_execution_status()
        
        successful_tasks = sum(1 for r in results if r.success)
        
        test_result = {
            "test_name": "resource_coordination",
            "execution_time_seconds": execution_time,
            "total_tasks": len(results),
            "successful_tasks": successful_tasks,
            "resource_conflicts_detected": len(status.get("resource_locks", {})),
            "status": "PASSED" if successful_tasks == len(results) else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Resource coordination test: {test_result['status']}")
        logger.info(f"Resource conflicts handled: {test_result['resource_conflicts_detected']}")
        
        return test_result
    
    async def test_error_isolation(self) -> Dict[str, Any]:
        """Test error isolation between parallel tasks."""
        logger.info("=== Testing Error Isolation ===")
        
        start_time = time.time()
        
        # Create mix of normal and error-prone tasks
        task_calls = [
            create_task_call(
                agent_id="frontend_specialist_1",
                task_type="normal_task",
                description="Normal frontend task",
                context_data={"should_succeed": True}
            ),
            create_task_call(
                agent_id="test_specialist_1",
                task_type="error_prone_task", 
                description="Task that might fail",
                context_data={"simulate_error": True}
            ),
            create_task_call(
                agent_id="documentation_specialist_1",
                task_type="normal_task",
                description="Normal documentation task", 
                context_data={"should_succeed": True}
            )
        ]
        
        results = await self.integration_layer.execute_multiple_task_calls(task_calls)
        
        execution_time = time.time() - start_time
        
        # Analyze error isolation
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = sum(1 for r in results if not r.success)
        
        # Check if successful tasks were affected by failures
        isolation_effective = successful_tasks > 0 and failed_tasks > 0
        
        test_result = {
            "test_name": "error_isolation",
            "execution_time_seconds": execution_time,
            "total_tasks": len(results),
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "isolation_effective": isolation_effective,
            "status": "PASSED" if isolation_effective or failed_tasks == 0 else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Error isolation test: {test_result['status']}")
        logger.info(f"Success/Fail ratio: {successful_tasks}/{failed_tasks}")
        
        return test_result
    
    async def test_progress_tracking(self) -> Dict[str, Any]:
        """Test progress tracking for parallel tasks."""
        logger.info("=== Testing Progress Tracking ===")
        
        start_time = time.time()
        progress_updates = []
        
        # Custom progress callback for testing
        async def track_progress(instance_id: str, progress: float):
            progress_updates.append({
                "instance_id": instance_id,
                "progress": progress,
                "timestamp": time.time()
            })
        
        # Add progress callback
        self.integration_layer.parallel_task_manager.add_progress_callback(track_progress)
        
        # Create long-running tasks
        task_calls = [
            create_task_call(
                agent_id="backend_specialist_1",
                task_type="long_task",
                description="Long-running backend task",
                context_data={"duration": "long"}
            ),
            create_task_call(
                agent_id="frontend_specialist_1", 
                task_type="long_task",
                description="Long-running frontend task",
                context_data={"duration": "long"}
            )
        ]
        
        results = await self.integration_layer.execute_multiple_task_calls(task_calls)
        
        execution_time = time.time() - start_time
        
        # Analyze progress tracking
        unique_instances = len(set(update["instance_id"] for update in progress_updates))
        total_updates = len(progress_updates)
        
        test_result = {
            "test_name": "progress_tracking",
            "execution_time_seconds": execution_time,
            "total_tasks": len(results),
            "progress_updates_received": total_updates,
            "unique_instances_tracked": unique_instances,
            "average_updates_per_task": total_updates / len(results) if results else 0,
            "status": "PASSED" if total_updates > 0 and unique_instances == len(results) else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Progress tracking test: {test_result['status']}")
        logger.info(f"Progress updates: {total_updates}, Instances: {unique_instances}")
        
        return test_result
    
    async def test_batch_execution(self) -> Dict[str, Any]:
        """Test batch execution with controlled parallelism."""
        logger.info("=== Testing Batch Execution ===")
        
        start_time = time.time()
        
        # Create a large number of tasks
        task_calls = []
        for i in range(12):  # Create 12 tasks
            task_calls.append(
                create_task_call(
                    agent_id=f"test_agent_{i % 5}",  # Rotate through agents
                    task_type="batch_task",
                    description=f"Batch task {i+1}",
                    context_data={"task_number": i+1, "batch_test": True}
                )
            )
        
        # Batch tasks into groups of 4
        batches = batch_task_calls(task_calls, batch_size=4)
        
        # Execute batches
        all_results = await execute_task_batches(self.integration_layer, batches)
        
        execution_time = time.time() - start_time
        
        successful_tasks = sum(1 for r in all_results if r.success)
        
        test_result = {
            "test_name": "batch_execution",
            "execution_time_seconds": execution_time,
            "total_tasks": len(all_results),
            "successful_tasks": successful_tasks,
            "num_batches": len(batches),
            "average_batch_size": len(task_calls) / len(batches),
            "status": "PASSED" if successful_tasks == len(all_results) else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Batch execution test: {test_result['status']}")
        logger.info(f"Batches: {len(batches)}, Tasks: {successful_tasks}/{len(all_results)}")
        
        return test_result
    
    async def test_concurrent_task_limits(self) -> Dict[str, Any]:
        """Test concurrent task limits and queuing."""
        logger.info("=== Testing Concurrent Task Limits ===")
        
        start_time = time.time()
        
        # Create more tasks than the concurrent limit (8)
        task_calls = []
        for i in range(15):  # 15 tasks > 8 concurrent limit
            task_calls.append(
                create_task_call(
                    agent_id=f"load_test_agent_{i}",
                    task_type="concurrent_test",
                    description=f"Concurrent test task {i+1}",
                    context_data={"task_id": i+1}
                )
            )
        
        # Execute all tasks
        results = await self.integration_layer.execute_multiple_task_calls(task_calls)
        
        execution_time = time.time() - start_time
        
        successful_tasks = sum(1 for r in results if r.success)
        
        # Get metrics
        metrics = self.integration_layer.get_task_execution_metrics()
        
        test_result = {
            "test_name": "concurrent_task_limits",
            "execution_time_seconds": execution_time,
            "total_tasks": len(results),
            "successful_tasks": successful_tasks,
            "concurrent_limit": 8,
            "tasks_submitted": 15,
            "average_execution_time_ms": metrics.get("average_execution_time_ms", 0),
            "status": "PASSED" if successful_tasks == len(results) else "FAILED"
        }
        
        self.test_results.append(test_result)
        
        logger.info(f"Concurrent limits test: {test_result['status']}")
        logger.info(f"Handled {len(results)} tasks with limit of 8 concurrent")
        
        return test_result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all parallel execution tests."""
        logger.info("Starting parallel execution test suite")
        
        await self.setup()
        
        # Run all tests
        test_methods = [
            self.test_basic_parallel_execution,
            self.test_resource_coordination,
            self.test_error_isolation,
            self.test_progress_tracking,
            self.test_batch_execution,
            self.test_concurrent_task_limits
        ]
        
        suite_start_time = time.time()
        
        for test_method in test_methods:
            try:
                await test_method()
                await asyncio.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed with error: {e}")
                self.test_results.append({
                    "test_name": test_method.__name__,
                    "status": "ERROR",
                    "error_message": str(e)
                })
        
        suite_execution_time = time.time() - suite_start_time
        
        # Compile overall results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("status") == "PASSED")
        failed_tests = sum(1 for r in self.test_results if r.get("status") == "FAILED")
        error_tests = sum(1 for r in self.test_results if r.get("status") == "ERROR")
        
        summary = {
            "test_suite": "parallel_execution_engine",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "suite_execution_time_seconds": suite_execution_time,
            "overall_status": "PASSED" if failed_tests == 0 and error_tests == 0 else "FAILED",
            "detailed_results": self.test_results
        }
        
        logger.info("=== TEST SUITE SUMMARY ===")
        logger.info(f"Overall Status: {summary['overall_status']}")
        logger.info(f"Tests: {passed_tests} passed, {failed_tests} failed, {error_tests} errors")
        logger.info(f"Success Rate: {summary['success_rate']:.1%}")
        logger.info(f"Execution Time: {suite_execution_time:.2f} seconds")
        
        return summary

async def main():
    """Main test execution function."""
    test_suite = ParallelExecutionTest()
    
    try:
        summary = await test_suite.run_all_tests()
        
        # Save results to file
        results_file = "/home/marku/ai_workflow_engine/.claude/orchestration_enhanced/parallel_execution_test_results.json"
        with open(results_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Test results saved to: {results_file}")
        
        # Return appropriate exit code
        return 0 if summary["overall_status"] == "PASSED" else 1
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)