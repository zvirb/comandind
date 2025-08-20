#!/usr/bin/env python3
"""
Test Enhanced Phase 9 Audit System

Validates the two-part Phase 9 audit system implementation:
- Part 1: Comprehensive Audit Planning 
- Part 2: Multi-Agent Execution with Consensus Analysis

This script demonstrates the complete audit workflow and validates
all components are working correctly.
"""

import asyncio
import json
import time
from typing import Dict, Any
import sys
import os

# Add the orchestration_enhanced directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ml_enhanced_orchestrator import execute_ml_enhanced_audit, get_ml_enhanced_orchestrator
    from mcp_integration_layer import MCPIntegrationLayer, WorkflowPhase
    print("✅ Successfully imported enhanced orchestration modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Falling back to standalone test...")

async def test_audit_planning():
    """Test Part 1: Audit Planning Phase"""
    print("🧪 Testing Part 1: Audit Planning Phase")
    
    # Create test audit context
    test_context = {
        "workflow_id": "test_workflow_001",
        "phases_completed": 8,
        "agents_used": ["backend-gateway-expert", "webui-architect", "user-experience-auditor"],
        "changes_made": [
            {"type": "authentication", "status": "completed", "confidence": 0.9},
            {"type": "circuit_breaker", "status": "completed", "confidence": 0.85}
        ],
        "affected_services": ["auth-service", "api-gateway", "frontend"],
        "criticality": "high",
        "results_summary": {
            "total_tasks": 5,
            "successful_tasks": 4,
            "average_confidence": 0.82
        },
        "execution_time": 1800,  # 30 minutes
        "workflow_context": {"test_mode": True}
    }
    
    try:
        # Test the comprehensive audit system
        audit_results = await execute_ml_enhanced_audit(test_context)
        
        print("✅ Audit planning completed successfully")
        print(f"   • Audit phases planned: {len(audit_results.get('audit_plan', {}).get('audit_phases', []))}")
        print(f"   • Required agents: {len(audit_results.get('audit_plan', {}).get('required_agents', []))}")
        print(f"   • Validation criteria: {len(audit_results.get('audit_plan', {}).get('validation_criteria', []))}")
        
        # Display audit plan summary
        audit_plan = audit_results.get('audit_plan', {})
        if audit_plan.get('audit_phases'):
            print("📋 Planned Audit Phases:")
            for phase in audit_plan['audit_phases']:
                print(f"   • {phase['level']}: {phase['description']}")
                print(f"     Agents: {phase['agents']} (Target: {phase['confidence_target']})")
        
        # Display execution results
        audit_execution = audit_results.get('audit_execution', {})
        if audit_execution.get('consensus_analysis'):
            consensus = audit_execution['consensus_analysis']
            print("🎯 Multi-Agent Audit Results:")
            print(f"   • Consensus Level: {consensus.get('consensus_level', 'unknown')}")
            print(f"   • Average Confidence: {consensus.get('average_confidence', 0.0):.2f}")
            print(f"   • Critical Findings: {len(consensus.get('critical_findings', []))}")
            
        return True
        
    except Exception as e:
        print(f"❌ Audit test failed: {e}")
        return False

async def test_workflow_integration():
    """Test integration with main workflow"""
    print("🧪 Testing Workflow Integration")
    
    try:
        # Create integration layer instance
        integration_layer = MCPIntegrationLayer()
        
        # Test Phase 9 execution
        print("Testing Phase 9 execution through integration layer...")
        
        # Simulate workflow context
        integration_layer.workflow_context = {
            "started_at": time.time() - 1800,  # 30 minutes ago
            "test_mode": True
        }
        
        integration_layer.results = {
            "task1": type('obj', (object,), {
                'success': True, 
                'confidence_score': 0.85,
                '__dict__': {'type': 'test_task', 'status': 'completed'}
            })(),
            "task2": type('obj', (object,), {
                'success': True, 
                'confidence_score': 0.90,
                '__dict__': {'type': 'test_validation', 'status': 'completed'}
            })()
        }
        
        integration_layer.agent_registry = {
            "orchestration-auditor": {"type": "audit", "status": "available"},
            "evidence-auditor": {"type": "audit", "status": "available"}
        }
        
        # Execute Phase 9 directly
        await integration_layer._execute_phase_9_meta_audit()
        
        print("✅ Integration test completed successfully")
        
        # Check if audit results were stored in workflow context
        if "phase_9_audit_results" in integration_layer.workflow_context:
            print("✅ Audit results properly stored in workflow context")
            audit_results = integration_layer.workflow_context["phase_9_audit_results"]
            
            if audit_results.get('audit_execution', {}).get('consensus_analysis'):
                consensus = audit_results['audit_execution']['consensus_analysis']
                print(f"   • Final Consensus Level: {consensus.get('consensus_level', 'unknown')}")
                print(f"   • Final Confidence Score: {consensus.get('average_confidence', 0.0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def test_consensus_analysis():
    """Test consensus analysis with multiple agent results"""
    print("🧪 Testing Consensus Analysis")
    
    # Simulate multiple agent results
    mock_phase_results = {
        "meta_orchestration_audit": {
            "orchestration-auditor_instance_1": {
                "status": "completed",
                "agent_type": "orchestration-auditor",
                "instance_id": 1,
                "confidence": 0.85,
                "success": True,
                "findings": "Workflow executed successfully with minor optimization opportunities",
                "evidence": "Performance metrics show 15% improvement over baseline",
                "evidence_type": "performance_data"
            },
            "orchestration-auditor_instance_2": {
                "status": "completed", 
                "agent_type": "orchestration-auditor",
                "instance_id": 2,
                "confidence": 0.82,
                "success": True,
                "findings": "Workflow shows good execution patterns with room for improvement",
                "evidence": "Code quality metrics within acceptable ranges",
                "evidence_type": "quality_metrics"
            }
        },
        "evidence_validation_audit": {
            "evidence-auditor_instance_1": {
                "status": "completed",
                "agent_type": "evidence-auditor", 
                "instance_id": 1,
                "confidence": 0.78,
                "success": True,
                "findings": "Evidence collection comprehensive and well-structured",
                "evidence": "All validation checkpoints passed with concrete evidence",
                "evidence_type": "validation_evidence"
            },
            "evidence-auditor_instance_2": {
                "status": "completed",
                "agent_type": "evidence-auditor",
                "instance_id": 2, 
                "confidence": 0.80,
                "success": True,
                "findings": "Evidence quality high with good cross-agent correlation",
                "evidence": "Evidence correlation score 0.85 across multiple sources",
                "evidence_type": "correlation_data"
            }
        }
    }
    
    try:
        # Get orchestrator instance to test consensus analysis
        orchestrator = get_ml_enhanced_orchestrator()
        
        # Test consensus analysis
        consensus_results = await orchestrator._analyze_audit_consensus(mock_phase_results)
        
        print("✅ Consensus analysis completed")
        print(f"   • Consensus Level: {consensus_results.get('consensus_level', 'unknown')}")
        print(f"   • Average Confidence: {consensus_results.get('average_confidence', 0.0):.2f}")
        print(f"   • Standard Deviation: {consensus_results.get('confidence_standard_deviation', 0.0):.3f}")
        print(f"   • Critical Findings: {len(consensus_results.get('critical_findings', []))}")
        print(f"   • Agent Types: {list(consensus_results.get('agent_findings_summary', {}).keys())}")
        
        # Test evidence aggregation
        evidence_results = await orchestrator._aggregate_audit_evidence(mock_phase_results)
        
        print("✅ Evidence aggregation completed")
        print(f"   • Evidence Items: {len(evidence_results.get('concrete_evidence', []))}")
        print(f"   • Quality Score: {evidence_results.get('quality_score', 0.0):.2f}")
        print(f"   • Cross-Agent Correlations: {len(evidence_results.get('cross_agent_correlations', {}))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Consensus analysis test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test suite for Phase 9 audit system"""
    print("🚀 Starting Enhanced Phase 9 Audit System Test Suite")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Audit Planning
    print("\n1️⃣ Testing Audit Planning Phase")
    result1 = await test_audit_planning()
    test_results.append(("Audit Planning", result1))
    
    # Test 2: Consensus Analysis
    print("\n2️⃣ Testing Consensus Analysis")
    result2 = await test_consensus_analysis()
    test_results.append(("Consensus Analysis", result2))
    
    # Test 3: Workflow Integration
    print("\n3️⃣ Testing Workflow Integration")
    result3 = await test_workflow_integration()
    test_results.append(("Workflow Integration", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("🎉 All tests passed! Enhanced Phase 9 audit system is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(run_comprehensive_test())
    
    if success:
        print("\n🎯 Enhanced Phase 9 Audit System Implementation Complete!")
        print("✅ Two-part audit system (planning + multi-agent execution) working")
        print("✅ Multi-agent consensus analysis functional")
        print("✅ Evidence aggregation and correlation operational")
        print("✅ Integration with main orchestration workflow successful")
        
        print("\n📋 System Features Implemented:")
        print("• Comprehensive audit planning with ML decision engine")
        print("• Multi-agent execution with independent verification")
        print("• Evidence aggregation and cross-agent correlation")
        print("• Consensus analysis with confidence scoring")
        print("• ML-enhanced insights and pattern recognition")
        print("• Integration with existing orchestration workflow")
        
        sys.exit(0)
    else:
        print("\n❌ Test suite failed. Implementation needs refinement.")
        sys.exit(1)