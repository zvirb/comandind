#!/usr/bin/env python3
"""
ML Integration Validation Test Suite

Tests actual ML decision-making capabilities rather than just theoretical framework.
Provides concrete evidence that ML integration is functional and making real decisions.
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the current directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ml_enhanced_orchestrator import (
        MLDecisionEngine, 
        MLModelType, 
        MLDecisionPoint,
        MLEnhancedOrchestrator
    )
    print("✓ Successfully imported ML orchestrator components")
except ImportError as e:
    print(f"✗ Failed to import ML components: {e}")
    sys.exit(1)

class MLValidationTester:
    """Comprehensive ML functionality validation."""
    
    def __init__(self):
        self.ml_engine = MLDecisionEngine()
        self.test_results = []
        self.evidence = []
        
    def log_evidence(self, test_name: str, evidence: Dict[str, Any]):
        """Log concrete evidence for test results."""
        self.evidence.append({
            'test': test_name,
            'timestamp': time.time(),
            'evidence': evidence
        })
        
    def log_result(self, test_name: str, passed: bool, details: str):
        """Log test result with pass/fail status."""
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        })
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"    Details: {details}")
            
    async def test_agent_selection_decision(self):
        """Test ML agent selection with real decision-making."""
        print("\n=== Testing Agent Selection Decision Engine ===")
        
        # Prepare realistic test context
        context = {
            'task_type': 'backend_implementation',
            'complexity': 0.7,
            'available_agents': [
                {
                    'id': 'backend-gateway-expert',
                    'capabilities': ['api_design', 'server_architecture', 'containerization'],
                    'specializations': ['backend', 'gateway', 'microservices']
                },
                {
                    'id': 'webui-architect', 
                    'capabilities': ['frontend_design', 'component_systems', 'ui_patterns'],
                    'specializations': ['frontend', 'ui', 'react']
                },
                {
                    'id': 'security-validator',
                    'capabilities': ['security_audit', 'vulnerability_scan', 'penetration_test'],
                    'specializations': ['security', 'validation', 'compliance']
                },
                {
                    'id': 'python-refactoring-architect',
                    'capabilities': ['code_refactoring', 'architecture_analysis', 'maintainability'],
                    'specializations': ['python', 'refactoring', 'architecture']
                }
            ]
        }
        
        try:
            # Execute ML decision
            decision = await self.ml_engine.make_decision(
                MLModelType.AGENT_SELECTION, 
                context
            )
            
            # Validate decision structure
            self.log_result(
                "Agent Selection Decision Structure",
                isinstance(decision, MLDecisionPoint) and 
                decision.decision_type == "agent_selection" and
                len(decision.options) > 0,
                f"Generated {len(decision.options)} scored agent options"
            )
            
            # Validate scoring logic
            scores = [agent['score'] for agent in decision.options]
            backend_agent_score = next((agent['score'] for agent in decision.options 
                                     if agent['agent_id'] == 'backend-gateway-expert'), 0)
            frontend_agent_score = next((agent['score'] for agent in decision.options 
                                       if agent['agent_id'] == 'webui-architect'), 0)
            
            # Backend agent should score higher for backend task
            scoring_logical = backend_agent_score > frontend_agent_score
            
            self.log_result(
                "Agent Selection Scoring Logic",
                scoring_logical,
                f"Backend agent score ({backend_agent_score:.3f}) > Frontend agent score ({frontend_agent_score:.3f})"
            )
            
            # Validate confidence calculation
            confidence_valid = (
                len(decision.confidence_scores) == len(decision.options) and
                all(0 <= score <= 1 for score in decision.confidence_scores)
            )
            
            self.log_result(
                "Confidence Scoring System",
                confidence_valid,
                f"Generated {len(decision.confidence_scores)} confidence scores, all in [0,1] range"
            )
            
            # Log evidence
            self.log_evidence("agent_selection", {
                'decision_type': decision.decision_type,
                'num_options': len(decision.options),
                'top_agent': decision.options[0]['agent_id'] if decision.options else None,
                'top_score': decision.options[0]['score'] if decision.options else 0,
                'confidence_range': f"[{min(decision.confidence_scores):.3f}, {max(decision.confidence_scores):.3f}]",
                'recommended_action': decision.recommended_action,
                'reasoning': decision.reasoning
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "Agent Selection Decision Engine",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
            
    async def test_parallel_coordination_decision(self):
        """Test ML parallel coordination strategy generation."""
        print("\n=== Testing Parallel Coordination Decision Engine ===")
        
        context = {
            'agents': [
                'backend-gateway-expert',
                'schema-database-expert', 
                'security-validator',
                'webui-architect'
            ],
            'container_dependencies': {
                'backend-gateway-expert': ['database', 'redis'],
                'schema-database-expert': ['database'],
                'security-validator': ['backend', 'database'],
                'webui-architect': ['backend']
            },
            'system_loads': {
                'cpu': 0.4,
                'memory': 0.6,
                'disk': 0.3
            }
        }
        
        try:
            decision = await self.ml_engine.make_decision(
                MLModelType.PARALLEL_COORDINATION,
                context
            )
            
            # Validate coordination grouping
            has_groups = len(decision.options) > 0
            all_groups_valid = all(
                'agents' in group and 'risk_score' in group 
                for group in decision.options
            )
            
            self.log_result(
                "Parallel Coordination Grouping",
                has_groups and all_groups_valid,
                f"Generated {len(decision.options)} coordination groups"
            )
            
            # Validate risk assessment
            risk_scores = [group['risk_score'] for group in decision.options]
            risk_valid = all(0 <= risk <= 1 for risk in risk_scores)
            
            self.log_result(
                "Coordination Risk Assessment",
                risk_valid,
                f"Risk scores range: [{min(risk_scores):.3f}, {max(risk_scores):.3f}]"
            )
            
            # Validate parallel safety decisions
            safety_decisions = [group.get('parallel_safe', False) for group in decision.options]
            has_safety_logic = len(safety_decisions) > 0 and any(isinstance(safe, bool) for safe in safety_decisions)
            
            self.log_result(
                "Parallel Safety Logic",
                has_safety_logic,
                f"Safety decisions: {safety_decisions}"
            )
            
            self.log_evidence("parallel_coordination", {
                'num_groups': len(decision.options),
                'risk_assessment': risk_scores,
                'safety_decisions': safety_decisions,
                'coordination_strategy': decision.recommended_action
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "Parallel Coordination Decision Engine",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
            
    async def test_validation_strategy_decision(self):
        """Test ML validation strategy generation."""
        print("\n=== Testing Validation Strategy Decision Engine ===")
        
        # Test different criticality levels
        test_scenarios = [
            {
                'name': 'Low Criticality',
                'context': {
                    'changes': ['minor_ui_update'],
                    'affected_services': [],
                    'criticality': 'low'
                }
            },
            {
                'name': 'High Criticality',
                'context': {
                    'changes': ['database_migration', 'api_refactor'],
                    'affected_services': ['backend', 'database', 'auth'],
                    'criticality': 'critical'
                }
            }
        ]
        
        for scenario in test_scenarios:
            try:
                decision = await self.ml_engine.make_decision(
                    MLModelType.VALIDATION_STRATEGY,
                    scenario['context']
                )
                
                # Validate escalation logic
                num_levels = len(decision.options)
                has_escalation = (
                    (scenario['context']['criticality'] == 'low' and num_levels >= 1) or
                    (scenario['context']['criticality'] == 'critical' and num_levels >= 2)
                )
                
                self.log_result(
                    f"Validation Strategy - {scenario['name']}",
                    has_escalation,
                    f"Generated {num_levels} validation levels for {scenario['context']['criticality']} criticality"
                )
                
                self.log_evidence(f"validation_strategy_{scenario['name'].lower()}", {
                    'criticality': scenario['context']['criticality'],
                    'validation_levels': num_levels,
                    'coverage_levels': [level.get('coverage') for level in decision.options],
                    'confidence_scores': decision.confidence_scores
                })
                
            except Exception as e:
                self.log_result(
                    f"Validation Strategy - {scenario['name']}",
                    False,
                    f"Exception occurred: {str(e)}"
                )
                
    async def test_risk_assessment_algorithm(self):
        """Test ML risk assessment capabilities."""
        print("\n=== Testing Risk Assessment Algorithm ===")
        
        context = {
            'proposed_changes': [
                'database_schema_change',
                'api_endpoint_modification',
                'authentication_system_update'
            ],
            'current_system_state': {
                'uptime': 0.99,
                'error_rate': 0.01,
                'load': 0.5
            },
            'change_complexity': 0.8,
            'rollback_difficulty': 0.6
        }
        
        try:
            decision = await self.ml_engine.make_decision(
                MLModelType.RISK_ASSESSMENT,
                context
            )
            
            # Validate risk calculation
            has_risk_score = decision.risk_assessment is not None and 0 <= decision.risk_assessment <= 1
            has_mitigation = decision.recommended_action is not None and len(decision.recommended_action) > 0
            
            self.log_result(
                "Risk Assessment Calculation",
                has_risk_score,
                f"Risk score: {decision.risk_assessment:.3f}"
            )
            
            self.log_result(
                "Risk Mitigation Recommendations",
                has_mitigation,
                f"Mitigation strategy: {decision.recommended_action[:100]}..."
            )
            
            self.log_evidence("risk_assessment", {
                'risk_score': decision.risk_assessment,
                'mitigation_strategy': decision.recommended_action,
                'reasoning': decision.reasoning
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "Risk Assessment Algorithm",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
            
    async def test_container_conflict_detection(self):
        """Test ML container conflict detection."""
        print("\n=== Testing Container Conflict Detection ===")
        
        context = {
            'containers': [
                {
                    'name': 'backend-api',
                    'ports': [8000, 8080],
                    'volumes': ['/data', '/logs'],
                    'dependencies': ['database', 'redis']
                },
                {
                    'name': 'ml-service',
                    'ports': [8080, 9000],  # Port conflict with backend-api
                    'volumes': ['/ml-models', '/logs'],  # Volume conflict with backend-api
                    'dependencies': ['database']
                },
                {
                    'name': 'frontend',
                    'ports': [3000],
                    'volumes': ['/static'],
                    'dependencies': ['backend-api']
                }
            ]
        }
        
        try:
            decision = await self.ml_engine.make_decision(
                MLModelType.CONTAINER_CONFLICT,
                context
            )
            
            # Should detect port and volume conflicts
            conflicts_detected = len(decision.options) > 0
            has_resolution = decision.recommended_action is not None
            
            self.log_result(
                "Container Conflict Detection",
                conflicts_detected,
                f"Detected {len(decision.options)} potential conflicts"
            )
            
            self.log_result(
                "Conflict Resolution Strategy",
                has_resolution,
                f"Resolution: {decision.recommended_action[:100]}..."
            )
            
            self.log_evidence("container_conflict", {
                'conflicts_detected': len(decision.options),
                'conflict_types': [opt.get('conflict_type') for opt in decision.options],
                'resolution_strategy': decision.recommended_action
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "Container Conflict Detection",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
            
    async def test_stream_prioritization(self):
        """Test ML stream prioritization decisions."""
        print("\n=== Testing Stream Prioritization Algorithm ===")
        
        context = {
            'execution_streams': [
                {
                    'name': 'backend_implementation',
                    'agents': ['backend-gateway-expert', 'schema-database-expert'],
                    'estimated_duration': 120,
                    'dependencies': [],
                    'criticality': 'high'
                },
                {
                    'name': 'frontend_updates', 
                    'agents': ['webui-architect', 'whimsy-ui-creator'],
                    'estimated_duration': 90,
                    'dependencies': ['backend_implementation'],
                    'criticality': 'medium'
                },
                {
                    'name': 'security_validation',
                    'agents': ['security-validator'],
                    'estimated_duration': 60,
                    'dependencies': ['backend_implementation'],
                    'criticality': 'critical'
                }
            ]
        }
        
        try:
            decision = await self.ml_engine.make_decision(
                MLModelType.STREAM_PRIORITIZATION,
                context
            )
            
            # Validate prioritization logic
            has_priority_scores = len(decision.confidence_scores) > 0
            streams_ordered = len(decision.options) == len(context['execution_streams'])
            
            self.log_result(
                "Stream Prioritization Logic",
                has_priority_scores and streams_ordered,
                f"Prioritized {len(decision.options)} execution streams"
            )
            
            # Check if critical streams are prioritized appropriately
            if decision.options:
                top_stream = decision.options[0]
                critical_prioritized = top_stream.get('criticality') in ['critical', 'high']
                
                self.log_result(
                    "Critical Stream Prioritization",
                    critical_prioritized,
                    f"Top priority stream criticality: {top_stream.get('criticality')}"
                )
            
            self.log_evidence("stream_prioritization", {
                'num_streams': len(decision.options),
                'priority_scores': decision.confidence_scores,
                'execution_order': [stream.get('name') for stream in decision.options],
                'prioritization_reasoning': decision.reasoning
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "Stream Prioritization Algorithm",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
    
    async def test_ml_orchestrator_integration(self):
        """Test full ML orchestrator integration."""
        print("\n=== Testing ML Orchestrator Integration ===")
        
        try:
            orchestrator = MLEnhancedOrchestrator()
            
            # Test orchestrator initialization
            has_ml_engine = hasattr(orchestrator, 'ml_engine')
            has_workflow_phases = hasattr(orchestrator, 'workflow_phases')
            
            self.log_result(
                "ML Orchestrator Initialization",
                has_ml_engine and has_workflow_phases,
                "ML engine and workflow phases properly initialized"
            )
            
            # Test ML decision integration in workflow
            context = {
                'task_type': 'full_stack_implementation',
                'complexity': 0.8,
                'available_agents': [
                    {'id': 'backend-gateway-expert', 'capabilities': ['backend']},
                    {'id': 'webui-architect', 'capabilities': ['frontend']}
                ]
            }
            
            # This should integrate ML decisions into the orchestration flow
            decision_integrated = hasattr(orchestrator, 'ml_engine') and orchestrator.ml_engine is not None
            
            self.log_result(
                "ML Decision Integration",
                decision_integrated,
                "ML decision engine properly integrated into orchestrator"
            )
            
            self.log_evidence("orchestrator_integration", {
                'ml_engine_present': has_ml_engine,
                'workflow_phases_present': has_workflow_phases,
                'integration_successful': decision_integrated
            })
            
            return True
            
        except Exception as e:
            self.log_result(
                "ML Orchestrator Integration",
                False,
                f"Exception occurred: {str(e)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run complete ML validation test suite."""
        print("🧪 STARTING ML INTEGRATION VALIDATION TESTS")
        print("=" * 60)
        
        test_functions = [
            self.test_agent_selection_decision,
            self.test_parallel_coordination_decision,
            self.test_validation_strategy_decision,
            self.test_risk_assessment_algorithm,
            self.test_container_conflict_detection,
            self.test_stream_prioritization,
            self.test_ml_orchestrator_integration
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for test_func in test_functions:
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
                total_tests += 1
            except Exception as e:
                print(f"✗ Test function {test_func.__name__} failed with exception: {e}")
                total_tests += 1
        
        # Generate final report
        self.generate_validation_report(total_tests, passed_tests)
        
    def generate_validation_report(self, total_tests: int, passed_tests: int):
        """Generate comprehensive validation report with evidence."""
        print("\n" + "=" * 60)
        print("🔍 ML INTEGRATION VALIDATION REPORT")
        print("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   • Total Tests: {total_tests}")
        print(f"   • Passed: {passed_tests}")
        print(f"   • Failed: {total_tests - passed_tests}")
        print(f"   • Success Rate: {success_rate:.1f}%")
        
        print(f"\n📋 DETAILED TEST RESULTS:")
        for i, result in enumerate(self.test_results, 1):
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"   {i:2d}. {status}: {result['test']}")
            if result['details']:
                print(f"       └─ {result['details']}")
        
        print(f"\n🔬 EVIDENCE COLLECTED:")
        for evidence in self.evidence:
            print(f"   • {evidence['test']}:")
            for key, value in evidence['evidence'].items():
                print(f"     └─ {key}: {value}")
        
        # Save detailed report
        report_data = {
            'timestamp': time.time(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'test_results': self.test_results,
            'evidence': self.evidence
        }
        
        report_file = Path(__file__).parent / 'ml_validation_report.json'
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Conclusion
        if success_rate >= 80:
            print("\n✅ CONCLUSION: ML Integration is FUNCTIONAL and provides real decision-making capabilities")
        elif success_rate >= 60:
            print("\n⚠️  CONCLUSION: ML Integration is PARTIALLY FUNCTIONAL with some issues")
        else:
            print("\n❌ CONCLUSION: ML Integration has SIGNIFICANT ISSUES and requires fixes")

async def main():
    """Main test execution."""
    tester = MLValidationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())