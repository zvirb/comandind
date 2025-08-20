#!/usr/bin/env python3
"""
Cognitive Processing Workflow Tests
==================================

Isolated testing of cognitive processing workflows for the learning service
to validate pattern recognition, knowledge graph operations, and learning
capabilities before service integration.
"""

import asyncio
import json
import time
import requests
import uuid
from typing import Dict, Any, List
from datetime import datetime

# Test Configuration
LEARNING_SERVICE_URL = "http://localhost:8005"
TEST_SESSION_ID = f"test_session_{int(time.time())}"

class CognitiveWorkflowTester:
    """Test suite for cognitive processing workflows."""
    
    def __init__(self):
        self.base_url = LEARNING_SERVICE_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", data: Dict[Any, Any] = None):
        """Log test results."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    {details}")
        if not success and data:
            print(f"    Error data: {json.dumps(data, indent=2)}")
    
    def test_service_health(self) -> bool:
        """Test learning service health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test(
                        "Service Health Check", 
                        True, 
                        f"Service operational with {data.get('uptime_seconds', 0):.1f}s uptime",
                        data
                    )
                    return True
                else:
                    self.log_test("Service Health Check", False, f"Service status: {data.get('status')}", data)
                    return False
            else:
                self.log_test("Service Health Check", False, f"HTTP {response.status_code}", {"status_code": response.status_code})
                return False
        except Exception as e:
            self.log_test("Service Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    def test_learning_from_success_outcome(self) -> bool:
        """Test learning from a successful cognitive outcome."""
        try:
            # Simulate a successful reasoning service outcome
            outcome_data = {
                "outcome_type": "success",
                "service_name": "reasoning-service",
                "context": {
                    "task_type": "hypothesis_testing",
                    "complexity": "medium",
                    "evidence_count": 5,
                    "reasoning_chain_length": 3
                },
                "input_data": {
                    "hypothesis": "Service coordination improves with structured workflows",
                    "evidence": [
                        "95% success rate with structured workflows",
                        "70% success rate without structure",
                        "User satisfaction increased by 40%"
                    ]
                },
                "output_data": {
                    "conclusion": "hypothesis_confirmed",
                    "confidence": 0.89,
                    "reasoning_chain": [
                        "Evidence analysis shows consistent improvement",
                        "Statistical significance confirmed",
                        "Pattern matches historical successful cases"
                    ]
                },
                "performance_metrics": {
                    "execution_time": 2.34,
                    "accuracy": 0.89,
                    "evidence_quality": 0.85
                },
                "session_id": TEST_SESSION_ID
            }
            
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=outcome_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("patterns_learned", 0) > 0:
                    self.log_test(
                        "Learning from Success Outcome",
                        True,
                        f"Learned {data.get('patterns_learned')} patterns with {data.get('confidence_score'):.2f} confidence",
                        data
                    )
                    return True
                else:
                    self.log_test("Learning from Success Outcome", False, "No patterns learned", data)
                    return False
            else:
                self.log_test(
                    "Learning from Success Outcome", 
                    False, 
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test("Learning from Success Outcome", False, f"Exception: {str(e)}")
            return False
    
    def test_learning_from_failure_outcome(self) -> bool:
        """Test learning from a failed cognitive outcome."""
        try:
            # Simulate a failed coordination service outcome
            outcome_data = {
                "outcome_type": "failure",
                "service_name": "coordination-service",
                "context": {
                    "task_type": "multi_agent_coordination",
                    "complexity": "high",
                    "agent_count": 7,
                    "workflow_depth": 4
                },
                "input_data": {
                    "workflow_request": "Complex data analysis with multiple validation steps",
                    "agents_requested": ["analyst", "validator", "synthesizer"],
                    "timeout_seconds": 300
                },
                "error_data": {
                    "error_type": "timeout_error",
                    "failed_step": "agent_coordination",
                    "partial_results": {
                        "completed_agents": 2,
                        "failed_agents": 1,
                        "timeout_agents": 4
                    }
                },
                "performance_metrics": {
                    "execution_time": 305.7,
                    "completion_rate": 0.29,
                    "resource_utilization": 0.85
                },
                "session_id": TEST_SESSION_ID
            }
            
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=outcome_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    insights = data.get("learning_insights", [])
                    failure_insights = [insight for insight in insights if "timeout" in insight.lower() or "coordination" in insight.lower()]
                    
                    self.log_test(
                        "Learning from Failure Outcome",
                        True,
                        f"Extracted {len(failure_insights)} failure-related insights",
                        data
                    )
                    return True
                else:
                    self.log_test("Learning from Failure Outcome", False, "Failed to process failure outcome", data)
                    return False
            else:
                self.log_test(
                    "Learning from Failure Outcome", 
                    False, 
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test("Learning from Failure Outcome", False, f"Exception: {str(e)}")
            return False
    
    def test_pattern_recognition_workflow(self) -> bool:
        """Test pattern recognition in cognitive workflows."""
        try:
            # Simulate a pattern recognition task
            outcome_data = {
                "outcome_type": "success",
                "service_name": "learning-service",
                "context": {
                    "task_type": "pattern_recognition",
                    "pattern_type": "behavioral",
                    "data_complexity": "medium",
                    "historical_context": True
                },
                "input_data": {
                    "behavioral_sequence": [
                        "user_request",
                        "agent_selection", 
                        "task_decomposition",
                        "parallel_execution",
                        "result_synthesis",
                        "quality_validation",
                        "user_response"
                    ],
                    "success_indicators": [
                        "execution_time < 30s",
                        "user_satisfaction > 0.8",
                        "accuracy > 0.9"
                    ]
                },
                "output_data": {
                    "pattern_identified": "optimal_workflow_sequence",
                    "pattern_confidence": 0.92,
                    "replication_potential": 0.88,
                    "optimization_suggestions": [
                        "Reduce agent selection time",
                        "Optimize parallel execution batching"
                    ]
                },
                "performance_metrics": {
                    "pattern_detection_time": 1.45,
                    "confidence_score": 0.92,
                    "similarity_to_known_patterns": 0.76
                },
                "session_id": TEST_SESSION_ID
            }
            
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=outcome_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("confidence_score", 0) > 0.8:
                    self.log_test(
                        "Pattern Recognition Workflow",
                        True,
                        f"High-confidence pattern recognition ({data.get('confidence_score'):.2f})",
                        data
                    )
                    return True
                else:
                    self.log_test("Pattern Recognition Workflow", False, "Low confidence pattern recognition", data)
                    return False
            else:
                self.log_test(
                    "Pattern Recognition Workflow", 
                    False, 
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test("Pattern Recognition Workflow", False, f"Exception: {str(e)}")
            return False
    
    def test_meta_learning_workflow(self) -> bool:
        """Test meta-learning capabilities."""
        try:
            # Simulate meta-learning from multiple service interactions
            outcome_data = {
                "outcome_type": "success",
                "service_name": "meta-learning-engine",
                "context": {
                    "task_type": "meta_learning",
                    "learning_domain": "cross_service_optimization",
                    "service_interactions": 15,
                    "time_window_hours": 2
                },
                "input_data": {
                    "service_performance_data": {
                        "reasoning-service": {"avg_time": 2.1, "success_rate": 0.89, "confidence": 0.85},
                        "coordination-service": {"avg_time": 4.5, "success_rate": 0.76, "confidence": 0.82},
                        "learning-service": {"avg_time": 1.8, "success_rate": 0.93, "confidence": 0.91}
                    },
                    "interaction_patterns": [
                        {"sequence": ["reasoning", "coordination"], "success_rate": 0.87},
                        {"sequence": ["coordination", "learning"], "success_rate": 0.91},
                        {"sequence": ["reasoning", "learning"], "success_rate": 0.94}
                    ]
                },
                "output_data": {
                    "meta_pattern": "reasoning_learning_direct_path",
                    "optimization_insight": "Bypass coordination for simple reasoning-learning workflows",
                    "predicted_improvement": 0.15,
                    "confidence": 0.88
                },
                "performance_metrics": {
                    "meta_learning_time": 3.2,
                    "pattern_synthesis_accuracy": 0.91,
                    "cross_validation_score": 0.85
                },
                "session_id": TEST_SESSION_ID
            }
            
            response = self.session.post(
                f"{self.base_url}/learn/outcome",
                json=outcome_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                insights = data.get("learning_insights", [])
                meta_insights = [insight for insight in insights if "optimization" in insight.lower() or "pattern" in insight.lower()]
                
                if data.get("status") == "success" and len(meta_insights) > 0:
                    self.log_test(
                        "Meta-Learning Workflow",
                        True,
                        f"Generated {len(meta_insights)} meta-learning insights",
                        data
                    )
                    return True
                else:
                    self.log_test("Meta-Learning Workflow", False, "Failed to generate meta-learning insights", data)
                    return False
            else:
                self.log_test(
                    "Meta-Learning Workflow", 
                    False, 
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_test("Meta-Learning Workflow", False, f"Exception: {str(e)}")
            return False
    
    def test_continuous_learning_adaptation(self) -> bool:
        """Test continuous learning and adaptation capabilities."""
        try:
            # Simulate a sequence of related learning events to test adaptation
            learning_sequence = [
                {
                    "outcome_type": "success",
                    "service_name": "adaptive-learning-test", 
                    "context": {"iteration": 1, "task_complexity": "low"},
                    "performance_metrics": {"accuracy": 0.75, "execution_time": 3.2}
                },
                {
                    "outcome_type": "success",
                    "service_name": "adaptive-learning-test",
                    "context": {"iteration": 2, "task_complexity": "medium"},
                    "performance_metrics": {"accuracy": 0.82, "execution_time": 2.8}
                },
                {
                    "outcome_type": "success", 
                    "service_name": "adaptive-learning-test",
                    "context": {"iteration": 3, "task_complexity": "high"},
                    "performance_metrics": {"accuracy": 0.89, "execution_time": 2.3}
                }
            ]
            
            responses = []
            for i, outcome_data in enumerate(learning_sequence):
                outcome_data["session_id"] = f"{TEST_SESSION_ID}_adaptation_{i}"
                response = self.session.post(
                    f"{self.base_url}/learn/outcome",
                    json=outcome_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    responses.append(response.json())
                else:
                    self.log_test(
                        "Continuous Learning Adaptation",
                        False,
                        f"Failed at iteration {i+1}: HTTP {response.status_code}"
                    )
                    return False
            
            # Analyze improvement trend
            confidence_scores = [r.get("confidence_score", 0) for r in responses]
            patterns_learned = sum(r.get("patterns_learned", 0) for r in responses)
            
            # Check if there's learning improvement
            improvement_detected = len(confidence_scores) >= 2 and confidence_scores[-1] > confidence_scores[0]
            
            if improvement_detected and patterns_learned > 0:
                self.log_test(
                    "Continuous Learning Adaptation",
                    True,
                    f"Detected learning improvement: {confidence_scores[0]:.2f} → {confidence_scores[-1]:.2f}, {patterns_learned} total patterns",
                    {"confidence_trend": confidence_scores, "total_patterns": patterns_learned}
                )
                return True
            else:
                self.log_test(
                    "Continuous Learning Adaptation",
                    False,
                    f"No improvement detected: {confidence_scores}",
                    {"confidence_trend": confidence_scores, "total_patterns": patterns_learned}
                )
                return False
                
        except Exception as e:
            self.log_test("Continuous Learning Adaptation", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all cognitive workflow tests."""
        print(f"\n{'='*60}")
        print("COGNITIVE PROCESSING WORKFLOW TESTS")
        print(f"Session ID: {TEST_SESSION_ID}")
        print(f"Learning Service: {self.base_url}")
        print(f"{'='*60}\n")
        
        # Test sequence
        tests = [
            ("Service Health", self.test_service_health),
            ("Learning from Success", self.test_learning_from_success_outcome),
            ("Learning from Failure", self.test_learning_from_failure_outcome),
            ("Pattern Recognition", self.test_pattern_recognition_workflow),
            ("Meta-Learning", self.test_meta_learning_workflow),
            ("Continuous Learning", self.test_continuous_learning_adaptation)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                print()  # Add spacing between tests
            except Exception as e:
                self.log_test(test_name, False, f"Test execution failed: {str(e)}")
                print()
        
        # Summary
        success_rate = (passed / total) * 100
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        print(f"Session ID: {TEST_SESSION_ID}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        # Return comprehensive results
        return {
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "success_rate": success_rate,
                "session_id": TEST_SESSION_ID
            },
            "detailed_results": self.test_results,
            "status": "success" if success_rate >= 80 else "partial_success" if success_rate >= 60 else "failure"
        }

if __name__ == "__main__":
    tester = CognitiveWorkflowTester()
    results = tester.run_all_tests()
    
    # Save detailed results
    with open(f"/tmp/cognitive_workflow_test_results_{int(time.time())}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Exit with appropriate code
    exit(0 if results["summary"]["success_rate"] >= 80 else 1)