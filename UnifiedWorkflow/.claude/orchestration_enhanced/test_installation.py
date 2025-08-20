#!/usr/bin/env python3
"""Installation Test Script for ML-Enhanced Orchestrator

Quick test to validate that the ML-Enhanced Orchestrator is properly installed
and working with all dependencies (including fallbacks).
"""

import sys
import asyncio
import traceback

def test_imports():
    """Test that all core imports work."""
    print("Testing imports...")
    
    try:
        from ml_enhanced_orchestrator import (
            MLDecisionEngine,
            MLEnhancedOrchestrator,
            MLModelType,
            HAS_NUMPY
        )
        print("  ✓ Core ML orchestrator imports successful")
        
        # Test numpy status
        if HAS_NUMPY:
            print("  ✓ Using real numpy library")
        else:
            print("  ⚠ Using fallback numpy implementation")
        
        return True, (MLDecisionEngine, MLEnhancedOrchestrator, MLModelType)
        
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        traceback.print_exc()
        return False, None

def test_instantiation(classes):
    """Test that classes can be instantiated."""
    print("Testing instantiation...")
    
    try:
        MLDecisionEngine, MLEnhancedOrchestrator, MLModelType = classes
        
        engine = MLDecisionEngine()
        print("  ✓ MLDecisionEngine created")
        
        orchestrator = MLEnhancedOrchestrator()
        print("  ✓ MLEnhancedOrchestrator created")
        
        return True, (engine, orchestrator)
        
    except Exception as e:
        print(f"  ✗ Instantiation failed: {e}")
        traceback.print_exc()
        return False, None

async def test_functionality(instances):
    """Test core ML functionality."""
    print("Testing ML functionality...")
    
    try:
        engine, orchestrator = instances
        
        # Test ML decision making
        context = {
            'task_type': 'test_task',
            'complexity': 0.5,
            'available_agents': [{
                'id': 'test-agent',
                'capabilities': ['testing'],
                'specializations': ['validation']
            }]
        }
        
        from ml_enhanced_orchestrator import MLModelType
        decision = await engine.make_decision(MLModelType.AGENT_SELECTION, context)
        print("  ✓ ML decision making works")
        print(f"    Recommendation: {decision.recommended_action}")
        
        # Test workflow status
        status = await orchestrator.get_workflow_status()
        print("  ✓ Workflow status retrieval works")
        print(f"    Active: {status['active']}")
        
        # Test agent registry
        agents = orchestrator.get_available_agents()
        print("  ✓ Agent registry works")
        print(f"    Available agents: {len(agents)}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_fallbacks():
    """Test fallback implementations."""
    print("Testing fallback implementations...")
    
    try:
        # Test numpy fallback directly
        from ml_enhanced_orchestrator import np
        
        test_data = [1, 2, 3, 4, 5]
        mean_val = np.mean(test_data)
        std_val = np.std(test_data)
        
        print(f"  ✓ Math functions work: mean={mean_val}, std={std_val:.2f}")
        
        # Test edge cases
        empty_mean = np.mean([])
        empty_std = np.std([])
        single_std = np.std([5])
        
        print(f"  ✓ Edge cases handled: empty_mean={empty_mean}, empty_std={empty_std}, single_std={single_std}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Fallback test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("ML-Enhanced Orchestrator Installation Test")
    print("=" * 50)
    
    # Test imports
    import_success, classes = test_imports()
    if not import_success:
        print("\n✗ Installation test FAILED - imports not working")
        return False
    
    print()
    
    # Test instantiation
    instantiation_success, instances = test_instantiation(classes)
    if not instantiation_success:
        print("\n✗ Installation test FAILED - instantiation not working")
        return False
    
    print()
    
    # Test functionality
    functionality_success = await test_functionality(instances)
    if not functionality_success:
        print("\n✗ Installation test FAILED - functionality not working")
        return False
    
    print()
    
    # Test fallbacks
    fallback_success = test_fallbacks()
    if not fallback_success:
        print("\n✗ Installation test FAILED - fallbacks not working")
        return False
    
    print("\n" + "=" * 50)
    print("✓ ALL TESTS PASSED!")
    print("🎉 ML-Enhanced Orchestrator is ready for use!")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    # Run the async test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)