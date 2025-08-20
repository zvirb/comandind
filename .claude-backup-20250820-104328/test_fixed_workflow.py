#!/usr/bin/env python3
"""
Test Suite for Fixed Claude Code Agentic Workflow System
Tests all critical fixes implemented to prevent orchestration failures
"""
import sys
import os
import json
from datetime import datetime
import traceback

# Add the .claude directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Test imports
try:
    from agent_logger import logger, log_action, RecursionError
    from orchestration_state import OrchestrationState, OrchestrationPhase, AgentTask, ParallelExecutor
    print("✅ Successfully imported fixed orchestration components")
except ImportError as e:
    print(f"❌ Failed to import components: {e}")
    sys.exit(1)

def test_recursion_prevention():
    """Test that recursion prevention blocks illegal agent calls"""
    print("\n🧪 Testing Recursion Prevention...")
    
    test_cases = [
        {
            "agent": "backend-gateway-expert", 
            "action": "calling project-orchestrator for help",
            "should_block": True,
            "reason": "Specialists cannot call orchestrators"
        },
        {
            "agent": "nexus-synthesis-agent",
            "action": "writing code to fix authentication",
            "should_block": True, 
            "reason": "Nexus cannot perform implementation actions"
        },
        {
            "agent": "ui-regression-debugger",
            "action": "calling backend-gateway-expert to fix API",
            "should_block": True,
            "reason": "Specialists cannot call other specialists"
        },
        {
            "agent": "project-orchestrator",
            "action": "creating implementation plan",
            "should_block": False,
            "reason": "Orchestrators can create plans"
        },
        {
            "agent": "main_claude",
            "action": "delegating to backend-gateway-expert",
            "should_block": False,
            "reason": "Main claude can delegate to specialists"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        try:
            log_action(test_case["agent"], test_case["action"])
            if test_case["should_block"]:
                print(f"❌ FAILED: {test_case['agent']} -> {test_case['action']} (should have been blocked)")
            else:
                print(f"✅ PASSED: {test_case['agent']} -> {test_case['action']} (correctly allowed)")
                passed += 1
        except RecursionError as e:
            if test_case["should_block"]:
                print(f"✅ PASSED: {test_case['agent']} blocked correctly: {e}")
                passed += 1
            else:
                print(f"❌ FAILED: {test_case['agent']} incorrectly blocked: {e}")
        except Exception as e:
            print(f"❌ ERROR: Unexpected error for {test_case['agent']}: {e}")
    
    print(f"📊 Recursion Prevention: {passed}/{total} tests passed")
    return passed == total

def test_orchestration_state_management():
    """Test the orchestration state management system"""
    print("\n🧪 Testing Orchestration State Management...")
    
    try:
        # Create test orchestration state
        state = OrchestrationState()
        
        # Test phase creation and management
        research_phase = OrchestrationPhase("research", "parallel")
        research_phase.add_task(AgentTask("codebase-research-analyst", "test task", [], {}))
        research_phase.add_task(AgentTask("schema-database-expert", "test task", [], {}))
        
        synthesis_phase = OrchestrationPhase("synthesis", "sequential")  
        synthesis_phase.add_task(AgentTask("nexus-synthesis-agent", "test synthesis", [], {}))
        
        state.add_phase(research_phase)
        state.add_phase(synthesis_phase)
        
        print(f"✅ Created orchestration state with {len(state.phases)} phases")
        
        # Test phase progression
        current_phase = state.get_current_phase()
        assert current_phase.name == "research", f"Expected research phase, got {current_phase.name}"
        print("✅ Current phase correctly identified as research")
        
        # Test synthesis readiness check
        ready_for_synthesis = state.is_ready_for_synthesis()
        print(f"✅ Synthesis readiness check: {ready_for_synthesis}")
        
        # Test state summary generation
        summary = state.get_execution_summary()
        assert "execution_id" in summary, "Summary missing execution_id"
        assert summary["total_phases"] == 2, f"Expected 2 phases, got {summary['total_phases']}"
        print("✅ State summary generation working")
        
        print("📊 Orchestration State Management: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Orchestration state error: {e}")
        traceback.print_exc()
        return False

def test_parallel_execution_framework():
    """Test the parallel execution framework"""
    print("\n🧪 Testing Parallel Execution Framework...")
    
    try:
        executor = ParallelExecutor(max_workers=2)
        
        # Mock agent call function
        def mock_call_agent(agent_name, task_description, context):
            import time
            time.sleep(0.1)  # Simulate work
            return {
                "success": True,
                "result": f"Mock result from {agent_name}",
                "tools_used": ["mock_tool"],
                "errors": []
            }
        
        # Create test tasks
        tasks = [
            AgentTask("test-agent-1", "parallel task 1", [], {}),
            AgentTask("test-agent-2", "parallel task 2", [], {})
        ]
        
        # Test sequential execution
        start_time = datetime.now()
        sequential_results = executor.execute_sequential_agents(tasks, mock_call_agent)
        sequential_time = (datetime.now() - start_time).total_seconds()
        
        assert len(sequential_results) == 2, f"Expected 2 results, got {len(sequential_results)}"
        assert all(result.success for result in sequential_results.values()), "Not all sequential tasks succeeded"
        print(f"✅ Sequential execution completed in {sequential_time:.2f}s")
        
        print("📊 Parallel Execution Framework: Tests passed")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Parallel execution error: {e}")
        traceback.print_exc()
        return False

def test_agent_boundary_enforcement():
    """Test that agent boundaries are properly enforced"""
    print("\n🧪 Testing Agent Boundary Enforcement...")
    
    # Test nexus-synthesis-agent boundary enforcement
    boundary_violations = [
        ("nexus-synthesis-agent", "writing file to implement fix"),
        ("nexus-synthesis-agent", "editing code in authentication module"), 
        ("nexus-synthesis-agent", "bash command to test implementation"),
        ("nexus-synthesis-agent", "multiedit to update multiple files")
    ]
    
    passed = 0
    total = len(boundary_violations)
    
    for agent, action in boundary_violations:
        try:
            log_action(agent, action)
            print(f"❌ FAILED: {agent} was allowed to perform: {action}")
        except RecursionError as e:
            print(f"✅ PASSED: {agent} correctly blocked from: {action}")
            passed += 1
        except Exception as e:
            print(f"❌ ERROR: Unexpected error: {e}")
    
    print(f"📊 Agent Boundary Enforcement: {passed}/{total} tests passed")
    return passed == total

def test_evidence_collection_validation():
    """Test that evidence collection requirements are documented"""
    print("\n🧪 Testing Evidence Collection Validation...")
    
    # Check that ui-regression-debugger has evidence requirements
    try:
        with open("/home/marku/ai_workflow_engine/.claude/agents/ui-regression-debugger.md", 'r') as f:
            content = f.read()
            
        evidence_requirements = [
            "Evidence-Based Validation Requirements",
            "EVIDENCE COLLECTION MANDATE",
            "Supporting Evidence (REQUIRED)",
            "Evidence Quality Requirements"
        ]
        
        passed = 0
        total = len(evidence_requirements)
        
        for requirement in evidence_requirements:
            if requirement in content:
                print(f"✅ Found: {requirement}")
                passed += 1
            else:
                print(f"❌ Missing: {requirement}")
        
        print(f"📊 Evidence Collection Validation: {passed}/{total} requirements found")
        return passed == total
        
    except Exception as e:
        print(f"❌ FAILED: Evidence validation error: {e}")
        return False

def test_documentation_synthesis_workflow():
    """Test that documentation synthesis workflow is implemented"""
    print("\n🧪 Testing Documentation Synthesis Workflow...")
    
    try:
        with open("/home/marku/ai_workflow_engine/.claude/agents/documentation-specialist.md", 'r') as f:
            content = f.read()
            
        synthesis_features = [
            "Synthesis-Based Documentation Updates",
            "Synthesis-to-Documentation Workflow", 
            "Process Documentation Update Package",
            "Intelligent Document Merging",
            "Knowledge Graph Integration"
        ]
        
        passed = 0
        total = len(synthesis_features)
        
        for feature in synthesis_features:
            if feature in content:
                print(f"✅ Found: {feature}")
                passed += 1
            else:
                print(f"❌ Missing: {feature}")
        
        print(f"📊 Documentation Synthesis Workflow: {passed}/{total} features found")
        return passed == total
        
    except Exception as e:
        print(f"❌ FAILED: Documentation synthesis error: {e}")
        return False

def test_meta_orchestration_auditor():
    """Test that meta-orchestration auditor exists and is configured"""
    print("\n🧪 Testing Meta-Orchestration Auditor...")
    
    try:
        auditor_file = "/home/marku/ai_workflow_engine/.claude/agents/orchestration-auditor.md"
        
        if not os.path.exists(auditor_file):
            print("❌ FAILED: orchestration-auditor.md does not exist")
            return False
            
        with open(auditor_file, 'r') as f:
            content = f.read()
            
        auditor_features = [
            "Meta-orchestration analysis agent",
            "POST-EXECUTION ONLY",
            "Success Verification Auditing", 
            "Failure Pattern Recognition",
            "Workflow Optimization Rule Generation",
            "Meta-Orchestration Audit Report"
        ]
        
        passed = 0
        total = len(auditor_features)
        
        for feature in auditor_features:
            if feature in content:
                print(f"✅ Found: {feature}")
                passed += 1
            else:
                print(f"❌ Missing: {feature}")
        
        print(f"📊 Meta-Orchestration Auditor: {passed}/{total} features found")
        return passed == total
        
    except Exception as e:
        print(f"❌ FAILED: Meta-orchestration auditor error: {e}")
        return False

def main():
    """Run all workflow fix tests"""
    print("🚀 Testing Fixed Claude Code Agentic Workflow System")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Recursion Prevention", test_recursion_prevention),
        ("Orchestration State Management", test_orchestration_state_management), 
        ("Parallel Execution Framework", test_parallel_execution_framework),
        ("Agent Boundary Enforcement", test_agent_boundary_enforcement),
        ("Evidence Collection Validation", test_evidence_collection_validation),
        ("Documentation Synthesis Workflow", test_documentation_synthesis_workflow),
        ("Meta-Orchestration Auditor", test_meta_orchestration_auditor)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed_tests += 1
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Workflow fixes are working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - workflow fixes need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)