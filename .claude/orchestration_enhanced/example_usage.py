#!/usr/bin/env python3
"""Example Usage of ML-Enhanced Orchestrator

Demonstrates how to use the ML-Enhanced Orchestrator with all
dependency fallbacks and graceful degradation features.
"""

import asyncio
import sys
from typing import Dict, Any, List

# Import the ML-Enhanced Orchestrator components
from ml_enhanced_orchestrator import (
    MLDecisionEngine,
    MLEnhancedOrchestrator,
    MLModelType,
    get_ml_enhanced_orchestrator,
    HAS_NUMPY
)

async def example_agent_selection():
    """Example: ML-powered agent selection for a task."""
    print("🤖 ML Agent Selection Example")
    print("-" * 40)
    
    # Create ML decision engine
    engine = MLDecisionEngine()
    
    # Define the task context
    context = {
        'task_type': 'security_validation',
        'complexity': 0.8,
        'available_agents': [
            {
                'id': 'security-validator',
                'capabilities': ['security_validation', 'penetration_testing', 'vulnerability_assessment'],
                'specializations': ['jwt_security', 'authentication_flows', 'security_scanning']
            },
            {
                'id': 'user-experience-auditor', 
                'capabilities': ['browser_automation', 'user_interaction_simulation', 'workflow_validation'],
                'specializations': ['playwright_testing', 'production_validation', 'evidence_collection']
            },
            {
                'id': 'backend-gateway-expert',
                'capabilities': ['api_design', 'containerization', 'fastapi_optimization'],
                'specializations': ['server_architecture', 'docker_configuration', 'worker_systems']
            }
        ]
    }
    
    # Make ML-powered decision
    decision = await engine.make_decision(MLModelType.AGENT_SELECTION, context)
    
    print(f"📋 Task: {context['task_type']}")
    print(f"⚡ Complexity: {context['complexity']}")
    print(f"🎯 Recommended Action: {decision.recommended_action}")
    print(f"📊 Confidence Scores: {[f'{score:.2f}' for score in decision.confidence_scores]}")
    print(f"🔍 Reasoning: {decision.reasoning}")
    print(f"⚠️ Risk Assessment: {decision.risk_assessment:.2f}")

async def example_risk_assessment():
    """Example: ML-powered risk assessment for operations."""
    print("\n🔒 ML Risk Assessment Example")
    print("-" * 40)
    
    engine = MLDecisionEngine()
    
    # High-risk deployment scenario
    high_risk_context = {
        'operation_type': 'database_migration',
        'system_state': {
            'health_metrics': {
                'cpu_usage': 75,  # High CPU usage
                'memory_usage': 85,  # High memory usage
                'error_rate': 0.05  # 5% error rate
            }
        },
        'recent_failures': [
            {'severity': 0.8, 'timestamp': 1234567890},
            {'severity': 0.6, 'timestamp': 1234567900}
        ]
    }
    
    decision = await engine.make_decision(MLModelType.RISK_ASSESSMENT, high_risk_context)
    
    print(f"🔧 Operation: {high_risk_context['operation_type']}")
    print(f"📈 System CPU: {high_risk_context['system_state']['health_metrics']['cpu_usage']}%")
    print(f"💾 System Memory: {high_risk_context['system_state']['health_metrics']['memory_usage']}%")
    print(f"❌ Error Rate: {high_risk_context['system_state']['health_metrics']['error_rate']*100:.1f}%")
    print(f"🎯 Recommendation: {decision.recommended_action}")
    print(f"⚠️ Risk Level: {decision.risk_assessment:.2f}")
    
    # Get mitigation strategies
    if decision.options:
        mitigation = decision.options[0].get('mitigation_strategies', [])
        print(f"🛡️ Mitigation Strategies: {', '.join(mitigation)}")

async def example_parallel_coordination():
    """Example: ML-powered parallel agent coordination."""
    print("\n⚡ ML Parallel Coordination Example")
    print("-" * 40)
    
    # Get the global orchestrator instance
    orchestrator = get_ml_enhanced_orchestrator()
    
    # Define agent requests for parallel execution
    agent_requests = [
        {
            'id': 'backend-gateway-expert',
            'context': {'task': 'optimize_api_endpoints'},
            'allow_instances': True,
            'max_instances': 2
        },
        {
            'id': 'security-validator',
            'context': {'task': 'security_audit'},
            'allow_instances': True,
            'max_instances': 1
        },
        {
            'id': 'user-experience-auditor',
            'context': {'task': 'ui_validation'},
            'allow_instances': True,
            'max_instances': 2
        }
    ]
    
    print(f"🚀 Executing {len(agent_requests)} agent types in parallel")
    
    # Execute with ML coordination
    results = await orchestrator.execute_parallel_agents(agent_requests, allow_multiple_instances=True)
    
    print(f"📊 ML Coordination Decision: {results['ml_coordination']['decision_type']}")
    print(f"📈 Risk Assessment: {results['ml_coordination']['risk_assessment']:.2f}")
    print(f"🎯 Coordination Groups: {len(results['ml_coordination']['options'])}")
    print(f"✅ Agents Executed: {results['total_agents_executed']}")
    
    # Show execution results summary
    for group_name, group_results in results['execution_results'].items():
        if isinstance(group_results, dict) and 'status' not in group_results:
            agent_count = len([k for k in group_results.keys() if 'instance' in k])
            print(f"   📦 {group_name}: {agent_count} agent instances")

async def example_streaming_orchestration():
    """Example: Streaming-based orchestration for complex fixes."""
    print("\n🌊 ML Streaming Orchestration Example")
    print("-" * 40)
    
    orchestrator = get_ml_enhanced_orchestrator()
    
    # Define fix context with detected violations
    fix_context = {
        'violations': [
            'ml_integration',
            'parallel_execution', 
            'validation_architecture',
            'file_organization'
        ],
        'priority': 'high',
        'complexity': 0.9
    }
    
    print(f"🔧 Violations Detected: {len(fix_context['violations'])}")
    print(f"⚡ Priority: {fix_context['priority']}")
    print(f"📊 Complexity: {fix_context['complexity']}")
    
    # Start streaming orchestration
    result = await orchestrator.start_streaming_orchestration(fix_context)
    print(f"🎯 Result: {result}")

def demonstrate_fallback_features():
    """Demonstrate the fallback numpy functionality."""
    print("\n🔧 Fallback Features Demonstration")
    print("-" * 40)
    
    # Import numpy (real or fallback)
    from ml_enhanced_orchestrator import np
    
    # Test mathematical operations
    test_datasets = [
        [1, 2, 3, 4, 5],
        [10, 20, 30],
        [100],
        []
    ]
    
    print(f"📊 Using {'real numpy' if HAS_NUMPY else 'fallback numpy'}")
    
    for i, data in enumerate(test_datasets):
        if data:
            mean_val = np.mean(data)
            std_val = np.std(data)
            print(f"   Dataset {i+1} {data}: mean={mean_val:.2f}, std={std_val:.2f}")
        else:
            mean_val = np.mean(data)
            std_val = np.std(data)
            print(f"   Dataset {i+1} {data}: mean={mean_val}, std={std_val} (empty dataset)")

async def demonstrate_orchestrator_status():
    """Demonstrate orchestrator status and info functions."""
    print("\n📋 Orchestrator Status & Information")
    print("-" * 40)
    
    orchestrator = get_ml_enhanced_orchestrator()
    
    # Get workflow status
    status = await orchestrator.get_workflow_status()
    print(f"🔄 Workflow Active: {status['active']}")
    print(f"🆔 Workflow ID: {status['workflow_id']}")
    
    # Get available agents
    agents = orchestrator.get_available_agents()
    print(f"🤖 Available Agents: {len(agents)}")
    
    # Show agent categories
    categories = {}
    for agent_id, agent_info in agents.items():
        agent_type = agent_info['agent_type']
        if agent_type not in categories:
            categories[agent_type] = 0
        categories[agent_type] += 1
    
    for category, count in categories.items():
        print(f"   📦 {category}: {count} agents")
    
    # Get orchestration phases
    phases = orchestrator.get_orchestration_phases()
    print(f"⚙️ Orchestration Phases: {len(phases)}")
    for phase in phases[:3]:  # Show first 3 phases
        print(f"   {phase['phase']}: {phase['name']}")
    print(f"   ... and {len(phases)-3} more phases")

async def main():
    """Run all examples."""
    print("🎯 ML-Enhanced Orchestrator Usage Examples")
    print("=" * 60)
    
    # Check dependency status
    from ml_enhanced_orchestrator import HAS_NUMPY
    try:
        import structlog
        has_structlog = True
    except ImportError:
        has_structlog = False
    
    print(f"📦 Dependencies: numpy={HAS_NUMPY}, structlog={has_structlog}")
    print()
    
    # Run examples
    await example_agent_selection()
    await example_risk_assessment()
    await example_parallel_coordination()
    await example_streaming_orchestration()
    
    # Demonstrate fallback features
    demonstrate_fallback_features()
    
    # Show orchestrator status
    await demonstrate_orchestrator_status()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed successfully!")
    print("🎉 ML-Enhanced Orchestrator is working perfectly!")

if __name__ == "__main__":
    # Set up the environment
    sys.path.append('.')
    
    # Run all examples
    asyncio.run(main())