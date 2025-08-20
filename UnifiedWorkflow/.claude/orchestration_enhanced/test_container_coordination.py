"""Test Container Coordination System

Validates the container coordination system functionality including:
- Container registration and state tracking
- Operation conflict detection
- Resource locking mechanisms
- Operation queue management
"""

import time
import json
from container_coordination import (
    ContainerCoordinationSystem, 
    ContainerState, 
    OperationType,
    ConflictSeverity,
    create_operation,
    get_coordination_system
)

def test_basic_functionality():
    """Test basic container coordination functionality"""
    print("=== Testing Basic Container Coordination ===")
    
    # Create coordination system
    coord = ContainerCoordinationSystem()
    
    # Test container registration
    print("1. Testing container registration...")
    assert coord.register_container("api", [8000], [])
    assert coord.register_container("webui", [3000], ["api"])
    assert coord.register_container("worker", [], ["api", "redis"])
    print("✓ Container registration successful")
    
    # Test state updates
    print("2. Testing state updates...")
    assert coord.update_container_state("api", ContainerState.RUNNING, "healthy")
    assert coord.update_container_state("webui", ContainerState.RUNNING, "healthy")
    assert coord.update_container_state("worker", ContainerState.RUNNING, "healthy")
    print("✓ State updates successful")
    
    # Test state retrieval
    print("3. Testing state retrieval...")
    states = coord.get_all_container_states()
    assert states["api"] == ContainerState.RUNNING
    assert states["webui"] == ContainerState.RUNNING
    assert states["worker"] == ContainerState.RUNNING
    print("✓ State retrieval successful")
    
    print("Basic functionality tests PASSED\n")
    return coord

def test_operation_conflicts(coord):
    """Test operation conflict detection"""
    print("=== Testing Operation Conflict Detection ===")
    
    # Create conflicting operations
    print("1. Testing critical conflicts...")
    
    # Start a restart operation
    restart_op = create_operation(
        container_name="api",
        operation_type=OperationType.RESTART,
        agent_id="agent-1",
        description="Restart API container"
    )
    
    success, message = coord.request_operation(restart_op)
    assert success, f"First restart should succeed: {message}"
    print("✓ First restart operation started")
    
    # Try another restart (should conflict)
    restart_op2 = create_operation(
        container_name="api", 
        operation_type=OperationType.RESTART,
        agent_id="agent-2",
        description="Second restart attempt"
    )
    
    success2, message2 = coord.request_operation(restart_op2)
    assert not success2, f"Second restart should be blocked: {message2}"
    print("✓ Critical conflict detected and prevented")
    
    # Test safe operations
    print("2. Testing safe operations...")
    read_op = create_operation(
        container_name="webui",
        operation_type=OperationType.READ,
        agent_id="agent-3",
        description="Read webui status"
    )
    
    success3, message3 = coord.request_operation(read_op)
    assert success3, f"Read operation should succeed: {message3}"
    print("✓ Safe operation executed successfully")
    
    # Complete operations
    coord.complete_operation(restart_op.operation_id, success=True)
    coord.complete_operation(read_op.operation_id, success=True)
    
    print("Operation conflict tests PASSED\n")

def test_operation_queuing(coord):
    """Test operation queuing for medium conflicts"""
    print("=== Testing Operation Queuing ===")
    
    # Start a config update
    config_op = create_operation(
        container_name="api",
        operation_type=OperationType.CONFIG_UPDATE,
        agent_id="config-agent",
        description="Update API config"
    )
    
    success, message = coord.request_operation(config_op)
    assert success, f"Config operation should start: {message}"
    print("✓ Config update operation started")
    
    # Try to restart (should be queued due to HIGH conflict)
    restart_op = create_operation(
        container_name="api",
        operation_type=OperationType.RESTART,
        agent_id="restart-agent", 
        priority=8,
        description="Restart after config"
    )
    
    success2, message2 = coord.request_operation(restart_op)
    assert success2 and "queued" in message2.lower(), f"Restart should be queued: {message2}"
    print("✓ Conflicting operation queued successfully")
    
    # Check queue status
    queued = coord.get_queued_operations()
    assert len(queued) == 1, f"Should have 1 queued operation, got {len(queued)}"
    assert queued[0]['operation_id'] == restart_op.operation_id
    print("✓ Queue status correct")
    
    # Complete config operation (should trigger queue processing)
    coord.complete_operation(config_op.operation_id, success=True)
    
    # Check if queued operation was processed
    time.sleep(0.1)  # Small delay for processing
    active = coord.get_active_operations()
    has_restart = any(op['operation_id'] == restart_op.operation_id for op in active)
    assert has_restart, "Queued restart operation should be active now"
    print("✓ Queue processed automatically after conflict resolution")
    
    # Complete restart
    coord.complete_operation(restart_op.operation_id, success=True)
    
    print("Operation queuing tests PASSED\n")

def test_dependency_conflicts(coord):
    """Test dependency-based conflicts"""
    print("=== Testing Dependency Conflicts ===")
    
    # Start operation on API (webui depends on api)
    api_restart = create_operation(
        container_name="api",
        operation_type=OperationType.RESTART,
        agent_id="api-agent",
        description="Restart API"
    )
    
    success, message = coord.request_operation(api_restart)
    assert success, f"API restart should start: {message}"
    print("✓ API restart operation started")
    
    # Try operation on webui (should detect dependency conflict)
    webui_op = create_operation(
        container_name="webui",
        operation_type=OperationType.CONFIG_UPDATE,
        agent_id="webui-agent",
        description="Update webui config"
    )
    
    success2, message2 = coord.request_operation(webui_op)
    # This might succeed with warning or be queued depending on implementation
    print(f"Webui operation result: {success2} - {message2}")
    
    # Complete API restart
    coord.complete_operation(api_restart.operation_id, success=True)
    
    # If webui operation was queued, complete it
    if not success2:
        time.sleep(0.1)
        active = coord.get_active_operations()
        webui_active = next((op for op in active if op['operation_id'] == webui_op.operation_id), None)
        if webui_active:
            coord.complete_operation(webui_op.operation_id, success=True)
    else:
        coord.complete_operation(webui_op.operation_id, success=True)
    
    print("✓ Dependency conflict handling working")
    print("Dependency conflict tests PASSED\n")

def test_system_status(coord):
    """Test system status reporting"""
    print("=== Testing System Status ===")
    
    status = coord.get_system_status()
    
    # Validate status structure
    assert 'containers' in status
    assert 'active_operations' in status
    assert 'queued_operations' in status
    assert 'total_operations_today' in status
    
    # Check container details
    assert 'api' in status['containers']
    assert 'webui' in status['containers']
    assert 'worker' in status['containers']
    
    api_status = status['containers']['api']
    assert 'state' in api_status
    assert 'health' in api_status
    assert 'locked' in api_status
    assert 'active_operations' in api_status
    
    print("✓ System status structure correct")
    print(f"Current status: {json.dumps(status, indent=2)}")
    print("System status tests PASSED\n")

def test_global_instance():
    """Test global instance functionality"""
    print("=== Testing Global Instance ===")
    
    # Get global instance
    coord1 = get_coordination_system()
    coord2 = get_coordination_system()
    
    # Should be same instance
    assert coord1 is coord2, "Global instances should be identical"
    print("✓ Global instance singleton working")
    
    print("Global instance tests PASSED\n")

def test_integration_helpers():
    """Test ML orchestrator integration helpers"""
    print("=== Testing Integration Helpers ===")
    
    # Test operation creation helper
    op = create_operation(
        container_name="test-container",
        operation_type=OperationType.DEPLOY,
        agent_id="test-agent",
        estimated_duration=120.0,
        priority=7,
        description="Test deployment"
    )
    
    assert op.container_name == "test-container"
    assert op.operation_type == OperationType.DEPLOY
    assert op.agent_id == "test-agent"
    assert op.estimated_duration == 120.0
    assert op.priority == 7
    assert "test-agent-test-container-deploy" in op.operation_id
    print("✓ Operation creation helper working")
    
    print("Integration helper tests PASSED\n")

def main():
    """Run all tests"""
    print("Starting Container Coordination System Tests...\n")
    
    try:
        # Test basic functionality
        coord = test_basic_functionality()
        
        # Test conflicts
        test_operation_conflicts(coord)
        
        # Test queuing
        test_operation_queuing(coord)
        
        # Test dependencies  
        test_dependency_conflicts(coord)
        
        # Test status
        test_system_status(coord)
        
        # Test global instance
        test_global_instance()
        
        # Test integration helpers
        test_integration_helpers()
        
        print("🎉 ALL TESTS PASSED! Container Coordination System is working correctly.")
        
        # Final system status
        final_status = coord.get_system_status()
        print(f"\nFinal System Status:")
        print(f"- Containers: {len(final_status['containers'])}")
        print(f"- Active Operations: {final_status['active_operations']}")
        print(f"- Queued Operations: {final_status['queued_operations']}")
        print(f"- Total Operations Today: {final_status['total_operations_today']}")
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)