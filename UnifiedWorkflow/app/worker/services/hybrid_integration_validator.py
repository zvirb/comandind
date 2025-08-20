"""
Hybrid Integration Validator

Validates the integration and functionality of the enhanced LangGraph services
with hybrid orchestration, consensus protocols, and blackboard communication.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from worker.services.hybrid_expert_group_langgraph_service import (
    hybrid_expert_group_langgraph_service, 
    OrchestrationMode,
    HybridExpertGroupState
)
from worker.services.blackboard_integration_service import (
    blackboard_integration_service,
    EventType,
    Performative
)
from worker.services.consensus_building_service import (
    consensus_building_service,
    ConsensusPhase
)

logger = logging.getLogger(__name__)


class IntegrationTestResult:
    """Container for integration test results."""
    
    def __init__(self):
        self.test_name = ""
        self.status = "pending"  # pending, running, passed, failed
        self.details = {}
        self.execution_time_ms = 0
        self.error_message = None
        self.validation_score = 0.0
        self.started_at = None
        self.completed_at = None


class HybridIntegrationValidator:
    """Comprehensive validator for hybrid orchestration system integration."""
    
    def __init__(self):
        self.test_results = []
        self.validation_session_id = str(uuid.uuid4())
    
    async def run_comprehensive_validation(self, user_id: int = 1) -> Dict[str, Any]:
        """Run comprehensive validation of the hybrid orchestration system."""
        
        logger.info("Starting comprehensive hybrid integration validation")
        
        validation_start = datetime.now(timezone.utc)
        overall_results = {
            "validation_session_id": self.validation_session_id,
            "started_at": validation_start.isoformat(),
            "test_results": [],
            "overall_status": "running",
            "overall_score": 0.0,
            "components_validated": [],
            "issues_identified": [],
            "recommendations": []
        }
        
        # Test suite execution
        test_suite = [
            ("blackboard_integration", self._test_blackboard_integration),
            ("consensus_building", self._test_consensus_building),
            ("hybrid_orchestration", self._test_hybrid_orchestration),
            ("dynamic_leadership", self._test_dynamic_leadership),
            ("market_task_allocation", self._test_market_task_allocation),
            ("argumentation_system", self._test_argumentation_system),
            ("quality_assurance", self._test_quality_assurance),
            ("end_to_end_workflow", self._test_end_to_end_workflow)
        ]
        
        # Execute test suite
        for test_name, test_function in test_suite:
            try:
                logger.info(f"Running test: {test_name}")
                result = await self._execute_test(test_name, test_function, user_id)
                self.test_results.append(result)
                overall_results["test_results"].append(result.__dict__)
                
                if result.status == "passed":
                    overall_results["components_validated"].append(test_name)
                else:
                    overall_results["issues_identified"].append({
                        "component": test_name,
                        "issue": result.error_message or "Test failed",
                        "severity": "high" if test_name in ["end_to_end_workflow", "hybrid_orchestration"] else "medium"
                    })
                    
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                failed_result = IntegrationTestResult()
                failed_result.test_name = test_name
                failed_result.status = "failed"
                failed_result.error_message = f"Test crashed: {str(e)}"
                self.test_results.append(failed_result)
                overall_results["test_results"].append(failed_result.__dict__)
        
        # Calculate overall results
        overall_results.update(self._calculate_overall_results())
        overall_results["completed_at"] = datetime.now(timezone.utc).isoformat()
        overall_results["duration_seconds"] = (
            datetime.now(timezone.utc) - validation_start
        ).total_seconds()
        
        # Generate recommendations
        overall_results["recommendations"] = self._generate_recommendations()
        
        logger.info(f"Validation complete. Overall score: {overall_results['overall_score']:.2f}")
        return overall_results
    
    async def _execute_test(
        self, 
        test_name: str, 
        test_function, 
        user_id: int
    ) -> IntegrationTestResult:
        """Execute a single integration test."""
        
        result = IntegrationTestResult()
        result.test_name = test_name
        result.started_at = datetime.now(timezone.utc)
        result.status = "running"
        
        try:
            start_time = datetime.now()
            
            # Execute test function
            test_details = await test_function(user_id)
            
            end_time = datetime.now()
            result.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result.details = test_details
            result.validation_score = test_details.get("validation_score", 0.0)
            result.status = "passed" if result.validation_score >= 0.7 else "failed"
            
            if result.status == "failed":
                result.error_message = test_details.get("error", "Validation score below threshold")
                
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            result.validation_score = 0.0
            result.details = {"error": str(e)}
            
        finally:
            result.completed_at = datetime.now(timezone.utc)
        
        return result
    
    async def _test_blackboard_integration(self, user_id: int) -> Dict[str, Any]:
        """Test blackboard integration service functionality."""
        
        test_session_id = f"test_blackboard_{uuid.uuid4()}"
        
        try:
            # Test 1: Post and retrieve blackboard events
            event = await blackboard_integration_service.post_blackboard_event(
                user_id=user_id,
                session_id=test_session_id,
                source_agent_id="test_agent",
                agent_role="Test Agent",
                event_type=EventType.AGENT_CONTRIBUTION,
                performative=Performative.INFORM,
                event_payload={"test": "blackboard integration"}
            )
            
            recent_events = await blackboard_integration_service.get_recent_events(
                user_id=user_id,
                session_id=test_session_id,
                limit=10
            )
            
            # Test 2: Agent context storage and retrieval
            context_state = await blackboard_integration_service.store_agent_context(
                agent_id="test_agent",
                agent_type="expert",
                agent_role="Test Agent",
                user_id=user_id,
                session_id=test_session_id,
                context_key="test_context",
                context_value={"integration": "test", "timestamp": datetime.now().isoformat()}
            )
            
            retrieved_contexts = await blackboard_integration_service.get_agent_context(
                agent_id="test_agent",
                session_id=test_session_id
            )
            
            # Test 3: Contribution opportunity detection
            opportunities = await blackboard_integration_service.detect_contribution_opportunities(
                agent_id="technical_expert",
                agent_role="Technical Expert",
                session_id=test_session_id,
                user_id=user_id,
                expertise_areas=["programming", "architecture"]
            )
            
            # Validation
            validation_score = 0.0
            
            if event and event.id:
                validation_score += 0.3
            
            if recent_events and len(recent_events) >= 1:
                validation_score += 0.3
                
            if context_state and context_state.id:
                validation_score += 0.2
                
            if retrieved_contexts:
                validation_score += 0.2
            
            return {
                "validation_score": validation_score,
                "events_posted": 1,
                "events_retrieved": len(recent_events),
                "contexts_stored": 1,
                "contexts_retrieved": len(retrieved_contexts),
                "opportunities_detected": len(opportunities),
                "test_session_id": test_session_id
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e),
                "test_session_id": test_session_id
            }
    
    async def _test_consensus_building(self, user_id: int) -> Dict[str, Any]:
        """Test consensus building service functionality."""
        
        test_session_id = f"test_consensus_{uuid.uuid4()}"
        
        try:
            # Simulate a consensus building process
            participating_agents = [
                {"agent_id": "technical_expert", "agent_role": "Technical Expert"},
                {"agent_id": "business_analyst", "agent_role": "Business Analyst"},
                {"agent_id": "planning_expert", "agent_role": "Planning Expert"}
            ]
            
            consensus_criteria = {
                "convergence_threshold": 0.6,  # Lower threshold for testing
                "max_rounds": 2,
                "require_unanimous": False
            }
            
            # Initiate consensus process
            consensus_id = await consensus_building_service.initiate_consensus_process(
                user_id=user_id,
                session_id=test_session_id,
                topic="Test consensus topic for integration validation",
                participating_agents=participating_agents,
                consensus_criteria=consensus_criteria,
                method="delphi"
            )
            
            # Check if consensus session was created
            if consensus_id in consensus_building_service.active_consensus_sessions:
                session = consensus_building_service.active_consensus_sessions[consensus_id]
                
                validation_score = 0.5  # Base score for successful initiation
                
                # Test proposal collection (simulated)
                if session.get("participating_agents"):
                    validation_score += 0.2
                
                # Test consensus criteria setup
                if session.get("consensus_criteria"):
                    validation_score += 0.2
                
                # Test method assignment
                if session.get("method") == "delphi":
                    validation_score += 0.1
                
                return {
                    "validation_score": validation_score,
                    "consensus_id": consensus_id,
                    "participating_agents_count": len(participating_agents),
                    "consensus_method": session.get("method"),
                    "session_status": session.get("current_phase"),
                    "test_session_id": test_session_id
                }
            else:
                return {
                    "validation_score": 0.0,
                    "error": "Consensus session not found after initiation",
                    "test_session_id": test_session_id
                }
                
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e),
                "test_session_id": test_session_id
            }
    
    async def _test_hybrid_orchestration(self, user_id: int) -> Dict[str, Any]:
        """Test hybrid orchestration mode functionality."""
        
        try:
            # Test with a simplified request
            test_request = "Design a simple web application architecture"
            selected_agents = ["technical_expert", "business_analyst"]
            
            # Test hybrid mode
            result = await hybrid_expert_group_langgraph_service.process_request(
                user_request=test_request,
                selected_agents=selected_agents,
                user_id=str(user_id),
                orchestration_mode=OrchestrationMode.HYBRID,
                consensus_required=False  # Disable for faster testing
            )
            
            validation_score = 0.0
            
            # Check basic result structure
            if result and isinstance(result, dict):
                validation_score += 0.2
            
            # Check for response content
            if result.get("response"):
                validation_score += 0.3
            
            # Check orchestration mode
            if result.get("orchestration_mode") == "hybrid":
                validation_score += 0.2
            
            # Check workflow type
            if result.get("workflow_type") == "hybrid_expert_group":
                validation_score += 0.2
            
            # Check agent involvement
            if result.get("experts_involved"):
                validation_score += 0.1
            
            return {
                "validation_score": validation_score,
                "response_length": len(result.get("response", "")),
                "orchestration_mode": result.get("orchestration_mode"),
                "workflow_type": result.get("workflow_type"),
                "experts_involved": result.get("experts_involved", []),
                "agent_contributions_count": len(result.get("agent_contributions", {})),
                "has_consensus_decisions": bool(result.get("consensus_decisions")),
                "has_allocated_tasks": bool(result.get("allocated_tasks"))
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    async def _test_dynamic_leadership(self, user_id: int) -> Dict[str, Any]:
        """Test dynamic leadership election functionality."""
        
        try:
            # Create a test state to test leadership election
            test_state = {
                "session_id": f"test_leadership_{uuid.uuid4()}",
                "user_id": str(user_id),
                "user_request": "Complex system design requiring leadership coordination",
                "selected_agents": ["project_manager", "technical_expert", "business_analyst"],
                "orchestration_mode": "hybrid",
                "contribution_opportunities": {
                    "project_manager": [{"priority": 0.8, "opportunity_type": "coordinate"}],
                    "technical_expert": [{"priority": 0.9, "opportunity_type": "design"}],
                    "business_analyst": [{"priority": 0.7, "opportunity_type": "analyze"}]
                },
                "chat_model": "llama3.1:8b"
            }
            
            # Test leadership election node
            service = hybrid_expert_group_langgraph_service
            updated_state = await service._elect_dynamic_leader_node(test_state)
            
            validation_score = 0.0
            
            # Check if leader was elected
            if updated_state.get("current_leader"):
                validation_score += 0.4
            
            # Check if leadership history was recorded
            if updated_state.get("leadership_history"):
                validation_score += 0.3
            
            # Check if orchestration mode was set
            if updated_state.get("orchestration_mode"):
                validation_score += 0.2
            
            # Check if discussion context was updated
            if updated_state.get("discussion_context"):
                validation_score += 0.1
            
            return {
                "validation_score": validation_score,
                "elected_leader": updated_state.get("current_leader"),
                "orchestration_mode": updated_state.get("orchestration_mode"),
                "leadership_history_count": len(updated_state.get("leadership_history", [])),
                "discussion_entries": len(updated_state.get("discussion_context", []))
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    async def _test_market_task_allocation(self, user_id: int) -> Dict[str, Any]:
        """Test market-based task allocation functionality."""
        
        try:
            # Create test state with tasks
            test_state = {
                "session_id": f"test_allocation_{uuid.uuid4()}",
                "user_id": str(user_id),
                "selected_agents": ["technical_expert", "business_analyst", "planning_expert"],
                "consensus_decisions": [
                    {
                        "consensus_id": "test_consensus",
                        "result": {
                            "implementation_steps": [
                                "Design system architecture",
                                "Analyze business requirements",
                                "Create implementation plan"
                            ]
                        }
                    }
                ],
                "chat_model": "llama3.1:8b"
            }
            
            # Test task allocation node
            service = hybrid_expert_group_langgraph_service
            updated_state = await service._allocate_tasks_market_based_node(test_state)
            
            validation_score = 0.0
            
            # Check if tasks were created
            allocated_tasks = updated_state.get("allocated_tasks", [])
            if allocated_tasks:
                validation_score += 0.4
            
            # Check if bids were collected
            task_bids = updated_state.get("task_bids", {})
            if task_bids:
                validation_score += 0.3
            
            # Check allocation method
            for task in allocated_tasks:
                if task.get("allocation_method") == "contract_net":
                    validation_score += 0.2
                    break
            
            # Check if agents were assigned
            allocated_agents = set(task.get("allocated_to") for task in allocated_tasks if task.get("allocated_to"))
            if allocated_agents:
                validation_score += 0.1
            
            return {
                "validation_score": validation_score,
                "tasks_allocated": len(allocated_tasks),
                "bids_collected": len(task_bids),
                "agents_with_tasks": len(allocated_agents),
                "allocation_methods": list(set(task.get("allocation_method") for task in allocated_tasks))
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    async def _test_argumentation_system(self, user_id: int) -> Dict[str, Any]:
        """Test argumentation and conflict resolution functionality."""
        
        try:
            # Create test state with potential conflicts
            test_state = {
                "session_id": f"test_argumentation_{uuid.uuid4()}",
                "user_id": str(user_id),
                "agent_contributions": {
                    "technical_expert": [{
                        "content": "We should use microservices architecture for better scalability",
                        "confidence": 0.8
                    }],
                    "business_analyst": [{
                        "content": "A monolithic architecture would be more cost-effective initially",
                        "confidence": 0.7
                    }]
                },
                "consensus_decisions": [],
                "chat_model": "llama3.1:8b"
            }
            
            # Test argumentation node
            service = hybrid_expert_group_langgraph_service
            updated_state = await service._conduct_argumentation_node(test_state)
            
            validation_score = 0.0
            
            # Check if conflicts were detected and processed
            argumentation_history = updated_state.get("argumentation_history", [])
            if isinstance(argumentation_history, list):
                validation_score += 0.4
            
            # Check if phase was updated
            if updated_state.get("current_phase") == "task_allocation":
                validation_score += 0.3
            
            # Check if discussion context was updated
            discussion_context = updated_state.get("discussion_context", [])
            if discussion_context and any("argumentation" in entry.get("phase", "") for entry in discussion_context):
                validation_score += 0.3
            
            return {
                "validation_score": validation_score,
                "argumentation_results": len(argumentation_history),
                "current_phase": updated_state.get("current_phase"),
                "discussion_entries": len(discussion_context)
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    async def _test_quality_assurance(self, user_id: int) -> Dict[str, Any]:
        """Test quality assurance and validation functionality."""
        
        try:
            # Create test state with quality data
            test_state = {
                "session_id": f"test_qa_{uuid.uuid4()}",
                "user_id": str(user_id),
                "agent_contributions": {
                    "technical_expert": [{
                        "content": "Detailed technical analysis with comprehensive recommendations",
                        "confidence": 0.9
                    }],
                    "business_analyst": [{
                        "content": "Business requirements analysis with stakeholder considerations",
                        "confidence": 0.8
                    }]
                },
                "consensus_decisions": [{
                    "convergence_score": 0.85,
                    "result": {"recommendation": "test consensus"}
                }],
                "allocated_tasks": [{
                    "allocated_to": "technical_expert",
                    "bid_score": 4.5,
                    "allocation_method": "contract_net"
                }],
                "chat_model": "llama3.1:8b"
            }
            
            # Test quality validation node
            service = hybrid_expert_group_langgraph_service
            updated_state = await service._validate_and_synthesize_node(test_state)
            
            validation_score = 0.0
            
            # Check validation results
            validation_results = updated_state.get("validation_results", {})
            if validation_results:
                validation_score += 0.3
                
                # Check individual quality metrics
                if validation_results.get("contribution_quality", 0) > 0:
                    validation_score += 0.2
                    
                if validation_results.get("consensus_integrity", 0) > 0:
                    validation_score += 0.2
                    
                if validation_results.get("overall_coherence", 0) > 0:
                    validation_score += 0.2
            
            # Check quality checkpoints
            quality_checkpoints = updated_state.get("quality_checkpoints", [])
            if quality_checkpoints:
                validation_score += 0.1
            
            return {
                "validation_score": validation_score,
                "quality_results": validation_results,
                "checkpoints_created": len(quality_checkpoints),
                "overall_coherence": validation_results.get("overall_coherence", 0.0)
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    async def _test_end_to_end_workflow(self, user_id: int) -> Dict[str, Any]:
        """Test complete end-to-end workflow functionality."""
        
        try:
            # Test with a comprehensive request
            test_request = "Create a project plan for developing a web application with user authentication"
            selected_agents = ["project_manager", "technical_expert", "business_analyst"]
            
            # Run full workflow
            result = await hybrid_expert_group_langgraph_service.process_request(
                user_request=test_request,
                selected_agents=selected_agents,
                user_id=str(user_id),
                orchestration_mode=OrchestrationMode.HYBRID,
                consensus_required=False  # Simplified for testing
            )
            
            validation_score = 0.0
            
            # Comprehensive validation
            required_keys = [
                "response", "discussion_context", "experts_involved",
                "orchestration_mode", "workflow_type"
            ]
            
            for key in required_keys:
                if result.get(key):
                    validation_score += 0.15
            
            # Check workflow completeness
            if len(result.get("discussion_context", [])) >= 3:  # Multiple phases
                validation_score += 0.1
            
            # Check expert involvement
            if len(result.get("experts_involved", [])) >= 2:
                validation_score += 0.1
            
            # Check response quality
            response_length = len(result.get("response", ""))
            if response_length > 200:  # Substantial response
                validation_score += 0.1
            
            return {
                "validation_score": validation_score,
                "response_length": response_length,
                "experts_involved": len(result.get("experts_involved", [])),
                "discussion_phases": len(result.get("discussion_context", [])),
                "workflow_completed": result.get("workflow_type") == "hybrid_expert_group",
                "has_consensus": bool(result.get("consensus_decisions")),
                "has_tasks": bool(result.get("allocated_tasks")),
                "orchestration_mode": result.get("orchestration_mode")
            }
            
        except Exception as e:
            return {
                "validation_score": 0.0,
                "error": str(e)
            }
    
    def _calculate_overall_results(self) -> Dict[str, Any]:
        """Calculate overall validation results."""
        
        if not self.test_results:
            return {
                "overall_status": "failed",
                "overall_score": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
                "total_tests": 0
            }
        
        passed_tests = sum(1 for result in self.test_results if result.status == "passed")
        failed_tests = sum(1 for result in self.test_results if result.status == "failed")
        total_tests = len(self.test_results)
        
        # Calculate weighted overall score
        total_score = sum(result.validation_score for result in self.test_results)
        overall_score = total_score / total_tests if total_tests > 0 else 0.0
        
        # Determine overall status
        if overall_score >= 0.8:
            overall_status = "excellent"
        elif overall_score >= 0.7:
            overall_status = "good"
        elif overall_score >= 0.5:
            overall_status = "acceptable"
        else:
            overall_status = "needs_improvement"
        
        return {
            "overall_status": overall_status,
            "overall_score": overall_score,
            "tests_passed": passed_tests,
            "tests_failed": failed_tests,
            "total_tests": total_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0
        }
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations based on test results."""
        
        recommendations = []
        
        # Analyze failed tests for recommendations
        failed_tests = [result for result in self.test_results if result.status == "failed"]
        
        for failed_test in failed_tests:
            test_name = failed_test.test_name
            
            if test_name == "blackboard_integration":
                recommendations.append({
                    "component": "Blackboard Integration",
                    "priority": "high",
                    "recommendation": "Review database connectivity and event persistence mechanisms",
                    "actions": [
                        "Check database migrations for cognitive state models",
                        "Validate database connection configuration",
                        "Test event posting and retrieval independently"
                    ]
                })
            
            elif test_name == "consensus_building":
                recommendations.append({
                    "component": "Consensus Building",
                    "priority": "high",
                    "recommendation": "Optimize consensus protocols for faster convergence",
                    "actions": [
                        "Review consensus criteria and thresholds",
                        "Implement timeout handling for consensus processes",
                        "Add more robust error handling for consensus failures"
                    ]
                })
            
            elif test_name == "hybrid_orchestration":
                recommendations.append({
                    "component": "Hybrid Orchestration",
                    "priority": "critical",
                    "recommendation": "Core orchestration functionality needs attention",
                    "actions": [
                        "Check LangGraph workflow compilation",
                        "Validate orchestration mode switching logic",
                        "Review agent coordination mechanisms"
                    ]
                })
            
            elif test_name == "end_to_end_workflow":
                recommendations.append({
                    "component": "End-to-End Workflow",
                    "priority": "critical",
                    "recommendation": "Complete workflow integration requires fixes",
                    "actions": [
                        "Review workflow state management",
                        "Check agent selection and coordination",
                        "Validate LangGraph node execution order"
                    ]
                })
        
        # Overall system recommendations
        overall_score = sum(result.validation_score for result in self.test_results) / len(self.test_results)
        
        if overall_score < 0.7:
            recommendations.append({
                "component": "System Overall",
                "priority": "high",
                "recommendation": "System requires optimization before production use",
                "actions": [
                    "Address critical component failures",
                    "Implement comprehensive error handling",
                    "Add performance monitoring and logging",
                    "Consider staged rollout approach"
                ]
            })
        
        return recommendations


# Global validator instance
hybrid_integration_validator = HybridIntegrationValidator()