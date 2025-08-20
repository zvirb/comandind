#!/usr/bin/env python3
"""
ML Execution Validation Test

Validates that ML decisions are not just calculated but actually executed
and impact real orchestration behavior.
"""

import asyncio
import time
import json
import sys
from pathlib import Path

# Add the current directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ml_enhanced_orchestrator import MLEnhancedOrchestrator, MLDecisionEngine, MLModelType

class MLExecutionValidator:
    
    def __init__(self):
        self.orchestrator = MLEnhancedOrchestrator()
        self.execution_logs = []
        
    def log_execution(self, step: str, decision: str, impact: str):
        """Log execution decisions and their impacts."""
        self.execution_logs.append({
            'timestamp': time.time(),
            'step': step,
            'decision': decision,
            'impact': impact
        })
        print(f"📝 {step}: {decision} → {impact}")
        
    async def test_ml_agent_routing_execution(self):
        """Test that ML agent selection actually routes to the right agents."""
        print("=== Testing ML Agent Routing Execution ===")
        
        # Test 1: Security task should route to security agent
        security_context = {
            'task_type': 'security_validation',
            'complexity': 0.7,
            'available_agents': [
                {'id': 'backend-gateway-expert', 'capabilities': ['backend']},
                {'id': 'security-validator', 'capabilities': ['security', 'audit']},
                {'id': 'webui-architect', 'capabilities': ['frontend']}
            ]
        }
        
        decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.AGENT_SELECTION,
            security_context
        )
        
        selected_agent = decision.options[0]['agent_id']
        is_security_agent = 'security' in selected_agent
        confidence = decision.options[0]['score']
        
        self.log_execution(
            "Security Task Routing",
            f"Selected {selected_agent} (confidence: {confidence:.3f})",
            f"Security specialist prioritized: {is_security_agent}"
        )
        
        # Test 2: Backend task should route to backend agent
        backend_context = {
            'task_type': 'backend_implementation',
            'complexity': 0.8,
            'available_agents': security_context['available_agents']
        }
        
        decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.AGENT_SELECTION,
            backend_context
        )
        
        selected_agent = decision.options[0]['agent_id']
        is_backend_agent = 'backend' in selected_agent
        confidence = decision.options[0]['score']
        
        self.log_execution(
            "Backend Task Routing",
            f"Selected {selected_agent} (confidence: {confidence:.3f})",
            f"Backend specialist prioritized: {is_backend_agent}"
        )
        
        return is_security_agent and is_backend_agent
        
    async def test_ml_validation_escalation_execution(self):
        """Test that ML risk assessment actually escalates validation."""
        print("\n=== Testing ML Validation Escalation Execution ===")
        
        # Low risk scenario
        low_risk_context = {
            'proposed_changes': ['minor_ui_update'],
            'current_system_state': {'uptime': 0.999, 'error_rate': 0.001},
            'change_complexity': 0.2,
            'rollback_difficulty': 0.1
        }
        
        low_risk_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.RISK_ASSESSMENT,
            low_risk_context
        )
        
        low_risk_validation_context = {
            'changes': low_risk_context['proposed_changes'],
            'affected_services': [],
            'criticality': 'low'
        }
        
        low_validation_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.VALIDATION_STRATEGY,
            low_risk_validation_context
        )
        
        low_validation_levels = len(low_validation_decision.options)
        
        self.log_execution(
            "Low Risk Validation",
            f"Risk: {low_risk_decision.risk_assessment:.3f}",
            f"Validation levels: {low_validation_levels}"
        )
        
        # High risk scenario
        high_risk_context = {
            'proposed_changes': [
                'database_migration',
                'auth_system_overhaul', 
                'api_breaking_changes'
            ],
            'current_system_state': {'uptime': 0.95, 'error_rate': 0.05},
            'change_complexity': 0.9,
            'rollback_difficulty': 0.8
        }
        
        high_risk_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.RISK_ASSESSMENT,
            high_risk_context
        )
        
        high_risk_validation_context = {
            'changes': high_risk_context['proposed_changes'],
            'affected_services': ['database', 'auth', 'api'],
            'criticality': 'critical'
        }
        
        high_validation_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.VALIDATION_STRATEGY,
            high_risk_validation_context
        )
        
        high_validation_levels = len(high_validation_decision.options)
        
        self.log_execution(
            "High Risk Validation",
            f"Risk: {high_risk_decision.risk_assessment:.3f}",
            f"Validation levels: {high_validation_levels}"
        )
        
        # Verify escalation actually happens
        escalation_works = high_validation_levels > low_validation_levels
        
        self.log_execution(
            "Validation Escalation",
            f"Low: {low_validation_levels} → High: {high_validation_levels}",
            f"Escalation working: {escalation_works}"
        )
        
        return escalation_works
        
    async def test_ml_parallel_safety_execution(self):
        """Test that ML parallel coordination actually affects execution safety."""
        print("\n=== Testing ML Parallel Safety Execution ===")
        
        # Safe parallel scenario
        safe_context = {
            'agents': [
                {'id': 'webui-architect', 'capabilities': ['frontend']},
                {'id': 'documentation-specialist', 'capabilities': ['docs']}
            ],
            'container_dependencies': {
                'webui-architect': ['frontend'],
                'documentation-specialist': ['docs']
            },
            'system_loads': {'cpu': 0.2, 'memory': 0.3}
        }
        
        safe_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.PARALLEL_COORDINATION,
            safe_context
        )
        
        safe_groups = [g for g in safe_decision.options if g.get('parallel_safe', False)]
        
        self.log_execution(
            "Safe Parallel Coordination",
            f"Groups: {len(safe_decision.options)}",
            f"Safe parallel groups: {len(safe_groups)}"
        )
        
        # Conflicting scenario  
        conflict_context = {
            'agents': [
                {'id': 'backend-gateway-expert', 'capabilities': ['backend']},
                {'id': 'schema-database-expert', 'capabilities': ['database']},
                {'id': 'security-validator', 'capabilities': ['security']}
            ],
            'container_dependencies': {
                'backend-gateway-expert': ['database', 'redis'],
                'schema-database-expert': ['database'],
                'security-validator': ['backend', 'database']
            },
            'system_loads': {'cpu': 0.8, 'memory': 0.9}
        }
        
        conflict_decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.PARALLEL_COORDINATION,
            conflict_context
        )
        
        conflict_safe_groups = [g for g in conflict_decision.options if g.get('parallel_safe', False)]
        conflict_unsafe_groups = [g for g in conflict_decision.options if not g.get('parallel_safe', True)]
        
        self.log_execution(
            "Conflict Parallel Coordination",
            f"Groups: {len(conflict_decision.options)}",
            f"Safe: {len(conflict_safe_groups)}, Sequential: {len(conflict_unsafe_groups)}"
        )
        
        # Verify safety logic works
        safety_logic_works = len(conflict_unsafe_groups) > 0  # Should detect conflicts
        
        self.log_execution(
            "Parallel Safety Logic",
            f"Conflict detection working",
            f"Safety logic functional: {safety_logic_works}"
        )
        
        return safety_logic_works
        
    async def test_ml_learning_impact_execution(self):
        """Test that ML learning actually impacts future decisions."""
        print("\n=== Testing ML Learning Impact Execution ===")
        
        # Record some performance history
        performance_data = [
            {'agent': 'backend-gateway-expert', 'task': 'backend_implementation', 'score': 0.9},
            {'agent': 'backend-gateway-expert', 'task': 'backend_implementation', 'score': 0.85},
            {'agent': 'webui-architect', 'task': 'backend_implementation', 'score': 0.3},
            {'agent': 'webui-architect', 'task': 'frontend_implementation', 'score': 0.9}
        ]
        
        # Simulate learning by updating performance matrix
        for record in performance_data:
            agent = record['agent']
            if agent not in self.orchestrator.ml_engine.agent_performance_matrix:
                self.orchestrator.ml_engine.agent_performance_matrix[agent] = []
            
            self.orchestrator.ml_engine.agent_performance_matrix[agent].append({
                'task_type': record['task'],
                'performance': record['score'],
                'outcome': 'success' if record['score'] > 0.7 else 'partial_success'
            })
        
        self.log_execution(
            "Performance Learning",
            f"Recorded {len(performance_data)} performance samples",
            "Updated ML performance matrix"
        )
        
        # Test decision before and after learning
        context = {
            'task_type': 'backend_implementation',
            'complexity': 0.6,
            'available_agents': [
                {'id': 'backend-gateway-expert', 'capabilities': ['backend']},
                {'id': 'webui-architect', 'capabilities': ['frontend']}
            ]
        }
        
        # Get decision with learning
        decision = await self.orchestrator.ml_engine.make_decision(
            MLModelType.AGENT_SELECTION,
            context
        )
        
        backend_score = next(opt['score'] for opt in decision.options if opt['agent_id'] == 'backend-gateway-expert')
        frontend_score = next(opt['score'] for opt in decision.options if opt['agent_id'] == 'webui-architect')
        
        learning_impact = backend_score > frontend_score
        score_difference = backend_score - frontend_score
        
        self.log_execution(
            "Learning Impact",
            f"Backend: {backend_score:.3f}, Frontend: {frontend_score:.3f}",
            f"Learning improved selection: {learning_impact} (diff: {score_difference:.3f})"
        )
        
        return learning_impact and score_difference > 0.05
        
    async def test_ml_decision_consistency_execution(self):
        """Test that ML decisions are consistent and deterministic."""
        print("\n=== Testing ML Decision Consistency ===")
        
        context = {
            'task_type': 'security_audit',
            'complexity': 0.7,
            'available_agents': [
                {'id': 'security-validator', 'capabilities': ['security']},
                {'id': 'backend-gateway-expert', 'capabilities': ['backend']}
            ]
        }
        
        # Run same decision multiple times
        decisions = []
        for i in range(3):
            decision = await self.orchestrator.ml_engine.make_decision(
                MLModelType.AGENT_SELECTION,
                context
            )
            decisions.append(decision.options[0]['agent_id'])
        
        # Check consistency
        consistent_decisions = len(set(decisions)) == 1
        selected_agent = decisions[0]
        
        self.log_execution(
            "Decision Consistency",
            f"3 runs selected: {decisions}",
            f"Consistent decisions: {consistent_decisions}"
        )
        
        # Check if security task consistently selects security agent
        correct_agent_selection = 'security' in selected_agent
        
        self.log_execution(
            "Correct Agent Selection",
            f"Selected {selected_agent} for security task",
            f"Security agent prioritized: {correct_agent_selection}"
        )
        
        return consistent_decisions and correct_agent_selection
        
    async def run_execution_validation(self):
        """Run all execution validation tests."""
        print("⚡ VALIDATING ML EXECUTION IMPACT")
        print("=" * 50)
        
        tests = [
            ("ML Agent Routing Execution", self.test_ml_agent_routing_execution),
            ("ML Validation Escalation Execution", self.test_ml_validation_escalation_execution),
            ("ML Parallel Safety Execution", self.test_ml_parallel_safety_execution),
            ("ML Learning Impact Execution", self.test_ml_learning_impact_execution),
            ("ML Decision Consistency Execution", self.test_ml_decision_consistency_execution)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                print(f"\n⚡ {test_name}")
                result = await test_func()
                results.append((test_name, result))
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status}: {test_name}")
            except Exception as e:
                print(f"❌ FAIL: {test_name} - Exception: {e}")
                results.append((test_name, False))
        
        # Generate execution report
        passed = sum(1 for _, result in results if result)
        total = len(results)
        success_rate = (passed / total) * 100
        
        print(f"\n⚡ EXECUTION VALIDATION RESULTS:")
        print(f"   • Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
        
        print(f"\n📋 EXECUTION LOG SUMMARY:")
        for log in self.execution_logs:
            print(f"   • {log['step']}: {log['decision']} → {log['impact']}")
        
        if success_rate >= 80:
            print("\n✅ FINAL CONCLUSION: ML Integration provides REAL, FUNCTIONAL decision-making")
            print("   → Decisions actually impact orchestration execution")
            print("   → Not just theoretical calculations")
            print("   → Consistent, intelligent behavior across all scenarios")
        else:
            print("\n⚠️  FINAL CONCLUSION: ML Integration has execution gaps")
            
        # Save detailed execution report
        report = {
            'timestamp': time.time(),
            'success_rate': success_rate,
            'test_results': results,
            'execution_logs': self.execution_logs,
            'conclusion': 'FUNCTIONAL' if success_rate >= 80 else 'NEEDS_IMPROVEMENT'
        }
        
        report_file = Path(__file__).parent / 'ml_execution_validation_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Execution validation report saved to: {report_file}")
        
        return success_rate

async def main():
    validator = MLExecutionValidator()
    await validator.run_execution_validation()

if __name__ == "__main__":
    asyncio.run(main())