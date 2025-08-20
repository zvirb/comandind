"""Container Coordination System for AI Workflow Engine

Provides comprehensive container state tracking, operation conflict detection,
resource locking, and operation coordination for parallel agent execution.

This system prevents operation conflicts during parallel orchestration by:
- Tracking real-time container states
- Detecting and preventing conflicting operations
- Implementing resource locking mechanisms
- Coordinating operation queues safely

Key Features:
- Real-time container state monitoring
- Operation conflict detection and prevention
- Resource locking and unlocking
- Operation queue management
- Container health monitoring
- Recovery mechanisms for failed operations
"""

import asyncio
import json
import time
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContainerState(Enum):
    """Container operational states"""
    RUNNING = "running"
    STOPPED = "stopped" 
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    ERROR = "error"
    UNKNOWN = "unknown"

class OperationType(Enum):
    """Container operation types"""
    READ = "read"              # Safe read operations
    CONFIG_UPDATE = "config"   # Configuration updates
    RESTART = "restart"        # Container restart
    STOP = "stop"             # Container stop
    START = "start"           # Container start
    DEPLOY = "deploy"         # Service deployment
    SCALE = "scale"           # Scaling operations
    HEALTH_CHECK = "health"   # Health monitoring

class ConflictSeverity(Enum):
    """Conflict severity levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    
    def __lt__(self, other):
        if isinstance(other, ConflictSeverity):
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, ConflictSeverity):
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, ConflictSeverity):
            return self.value > other.value
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, ConflictSeverity):
            return self.value >= other.value
        return NotImplemented

@dataclass
class ContainerOperation:
    """Represents a container operation"""
    operation_id: str
    container_name: str
    operation_type: OperationType
    agent_id: str
    started_at: float
    estimated_duration: float
    priority: int = 5  # 1-10, higher is more priority
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'operation_id': self.operation_id,
            'container_name': self.container_name,
            'operation_type': self.operation_type.value,
            'agent_id': self.agent_id,
            'started_at': self.started_at,
            'estimated_duration': self.estimated_duration,
            'priority': self.priority,
            'description': self.description
        }

@dataclass
class ContainerInfo:
    """Container information and state"""
    name: str
    state: ContainerState
    last_updated: float
    health_status: str = "unknown"
    ports: List[int] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = []
        if self.dependencies is None:
            self.dependencies = []

class ContainerCoordinationSystem:
    """Main container coordination system"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize container coordination system"""
        self.containers: Dict[str, ContainerInfo] = {}
        self.active_operations: Dict[str, ContainerOperation] = {}
        self.operation_queue: List[ContainerOperation] = []
        self.locks: Dict[str, Set[str]] = {}  # container -> set of operation_ids
        self.conflict_matrix: Dict[Tuple[OperationType, OperationType], ConflictSeverity] = {}
        self.operation_history: List[Dict[str, Any]] = []
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Configuration
        self.config = self._load_config(config_path)
        
        # Initialize conflict matrix
        self._initialize_conflict_matrix()
        
        # Start monitoring
        self._start_monitoring()
        
        logger.info("Container Coordination System initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration"""
        default_config = {
            'max_concurrent_operations_per_container': 3,
            'operation_timeout_seconds': 300,
            'health_check_interval_seconds': 30,
            'queue_max_size': 100,
            'enable_auto_recovery': True
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def _initialize_conflict_matrix(self):
        """Initialize operation conflict matrix"""
        # Define which operations conflict with each other
        conflicts = [
            # Critical conflicts - cannot run simultaneously
            ((OperationType.RESTART, OperationType.RESTART), ConflictSeverity.CRITICAL),
            ((OperationType.RESTART, OperationType.STOP), ConflictSeverity.CRITICAL),
            ((OperationType.RESTART, OperationType.START), ConflictSeverity.CRITICAL),
            ((OperationType.STOP, OperationType.START), ConflictSeverity.CRITICAL),
            ((OperationType.DEPLOY, OperationType.RESTART), ConflictSeverity.CRITICAL),
            ((OperationType.DEPLOY, OperationType.STOP), ConflictSeverity.CRITICAL),
            
            # High conflicts - should be queued
            ((OperationType.CONFIG_UPDATE, OperationType.RESTART), ConflictSeverity.HIGH),
            ((OperationType.CONFIG_UPDATE, OperationType.DEPLOY), ConflictSeverity.HIGH),
            ((OperationType.SCALE, OperationType.RESTART), ConflictSeverity.HIGH),
            ((OperationType.SCALE, OperationType.DEPLOY), ConflictSeverity.HIGH),
            
            # Medium conflicts - can run with caution
            ((OperationType.CONFIG_UPDATE, OperationType.CONFIG_UPDATE), ConflictSeverity.MEDIUM),
            ((OperationType.HEALTH_CHECK, OperationType.RESTART), ConflictSeverity.MEDIUM),
            
            # Low conflicts - minor coordination needed
            ((OperationType.READ, OperationType.CONFIG_UPDATE), ConflictSeverity.LOW),
            ((OperationType.READ, OperationType.SCALE), ConflictSeverity.LOW),
            
            # No conflicts - safe to run simultaneously
            ((OperationType.READ, OperationType.READ), ConflictSeverity.NONE),
            ((OperationType.READ, OperationType.HEALTH_CHECK), ConflictSeverity.NONE),
            ((OperationType.HEALTH_CHECK, OperationType.HEALTH_CHECK), ConflictSeverity.NONE),
        ]
        
        # Populate matrix (symmetrical)
        for (op1, op2), severity in conflicts:
            self.conflict_matrix[(op1, op2)] = severity
            self.conflict_matrix[(op2, op1)] = severity
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        # In a real implementation, this would start async tasks
        # For now, we'll use synchronous monitoring
        pass
    
    def register_container(self, name: str, ports: List[int] = None, 
                          dependencies: List[str] = None) -> bool:
        """Register a container in the coordination system"""
        with self.lock:
            if name in self.containers:
                logger.warning(f"Container {name} already registered")
                return False
            
            self.containers[name] = ContainerInfo(
                name=name,
                state=ContainerState.UNKNOWN,
                last_updated=time.time(),
                ports=ports or [],
                dependencies=dependencies or []
            )
            self.locks[name] = set()
            
            logger.info(f"Registered container: {name}")
            return True
    
    def update_container_state(self, name: str, state: ContainerState, 
                              health_status: str = "unknown") -> bool:
        """Update container state"""
        with self.lock:
            if name not in self.containers:
                # Auto-register if not exists
                self.register_container(name)
            
            self.containers[name].state = state
            self.containers[name].health_status = health_status
            self.containers[name].last_updated = time.time()
            
            logger.debug(f"Updated container {name} state to {state.value}")
            return True
    
    def get_container_state(self, name: str) -> Optional[ContainerState]:
        """Get current container state"""
        with self.lock:
            if name in self.containers:
                return self.containers[name].state
            return None
    
    def get_all_container_states(self) -> Dict[str, ContainerState]:
        """Get all container states"""
        with self.lock:
            return {name: info.state for name, info in self.containers.items()}
    
    def request_operation(self, operation: ContainerOperation) -> Tuple[bool, str]:
        """Request a container operation"""
        with self.lock:
            # Validate container exists
            if operation.container_name not in self.containers:
                self.register_container(operation.container_name)
            
            # Check for conflicts
            conflicts = self._check_operation_conflicts(operation)
            
            if not conflicts:
                # No conflicts, execute immediately
                return self._execute_operation(operation)
            
            # Handle conflicts based on severity
            max_severity = max(conflict['severity'] for conflict in conflicts)
            
            if max_severity >= ConflictSeverity.CRITICAL:
                return False, f"Critical conflict detected: {conflicts}"
            
            elif max_severity >= ConflictSeverity.HIGH:
                # Queue the operation
                if len(self.operation_queue) >= self.config['queue_max_size']:
                    return False, "Operation queue is full"
                
                self.operation_queue.append(operation)
                self.operation_queue.sort(key=lambda op: (-op.priority, op.started_at))
                
                return True, f"Operation queued due to conflicts: {len(conflicts)} conflicts"
            
            else:
                # Medium/Low conflicts - execute with warning
                success, message = self._execute_operation(operation)
                if success:
                    message += f" (Warning: {len(conflicts)} minor conflicts detected)"
                return success, message
    
    def _check_operation_conflicts(self, operation: ContainerOperation) -> List[Dict[str, Any]]:
        """Check for operation conflicts"""
        conflicts = []
        container_name = operation.container_name
        
        # Check against active operations on same container
        for active_op in self.active_operations.values():
            if active_op.container_name == container_name:
                conflict_severity = self._get_conflict_severity(
                    operation.operation_type, 
                    active_op.operation_type
                )
                
                if conflict_severity > ConflictSeverity.NONE:
                    conflicts.append({
                        'conflicting_operation': active_op.operation_id,
                        'conflicting_type': active_op.operation_type.value,
                        'severity': conflict_severity,
                        'agent': active_op.agent_id
                    })
        
        # Check dependency conflicts
        container_info = self.containers[container_name]
        for dep_name in container_info.dependencies:
            for active_op in self.active_operations.values():
                if active_op.container_name == dep_name:
                    # Check if operation on dependency conflicts
                    if active_op.operation_type in [OperationType.STOP, OperationType.RESTART]:
                        conflicts.append({
                            'conflicting_operation': active_op.operation_id,
                            'conflicting_type': active_op.operation_type.value,
                            'severity': ConflictSeverity.HIGH,
                            'agent': active_op.agent_id,
                            'type': 'dependency_conflict',
                            'dependency': dep_name
                        })
        
        return conflicts
    
    def _get_conflict_severity(self, op1: OperationType, op2: OperationType) -> ConflictSeverity:
        """Get conflict severity between two operation types"""
        return self.conflict_matrix.get((op1, op2), ConflictSeverity.NONE)
    
    def _execute_operation(self, operation: ContainerOperation) -> Tuple[bool, str]:
        """Execute a container operation"""
        try:
            # Add operation lock
            self.locks[operation.container_name].add(operation.operation_id)
            self.active_operations[operation.operation_id] = operation
            
            # Record operation start
            self.operation_history.append({
                'operation_id': operation.operation_id,
                'container': operation.container_name,
                'type': operation.operation_type.value,
                'agent': operation.agent_id,
                'started_at': operation.started_at,
                'status': 'started'
            })
            
            logger.info(f"Started operation {operation.operation_id} on {operation.container_name}")
            return True, f"Operation {operation.operation_id} started successfully"
            
        except Exception as e:
            logger.error(f"Failed to execute operation {operation.operation_id}: {e}")
            return False, f"Failed to execute operation: {e}"
    
    def complete_operation(self, operation_id: str, success: bool = True, 
                          error_message: str = "") -> bool:
        """Mark an operation as completed"""
        with self.lock:
            if operation_id not in self.active_operations:
                logger.warning(f"Operation {operation_id} not found in active operations")
                return False
            
            operation = self.active_operations[operation_id]
            
            # Remove locks
            self.locks[operation.container_name].discard(operation_id)
            del self.active_operations[operation_id]
            
            # Record completion
            self.operation_history.append({
                'operation_id': operation_id,
                'container': operation.container_name,
                'type': operation.operation_type.value,
                'agent': operation.agent_id,
                'completed_at': time.time(),
                'duration': time.time() - operation.started_at,
                'status': 'success' if success else 'failed',
                'error': error_message
            })
            
            # Process queue
            self._process_operation_queue()
            
            logger.info(f"Completed operation {operation_id} ({'success' if success else 'failed'})")
            return True
    
    def _process_operation_queue(self):
        """Process queued operations"""
        if not self.operation_queue:
            return
        
        # Try to execute queued operations
        executed = []
        for i, operation in enumerate(self.operation_queue):
            conflicts = self._check_operation_conflicts(operation)
            max_severity = max((conflict['severity'] for conflict in conflicts), 
                             default=ConflictSeverity.NONE)
            
            if max_severity < ConflictSeverity.HIGH:
                # Can execute now
                success, message = self._execute_operation(operation)
                if success:
                    executed.append(i)
                    logger.info(f"Executed queued operation {operation.operation_id}")
        
        # Remove executed operations from queue
        for i in reversed(executed):
            self.operation_queue.pop(i)
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get all active operations"""
        with self.lock:
            return [op.to_dict() for op in self.active_operations.values()]
    
    def get_queued_operations(self) -> List[Dict[str, Any]]:
        """Get all queued operations"""
        with self.lock:
            return [op.to_dict() for op in self.operation_queue]
    
    def get_container_locks(self) -> Dict[str, List[str]]:
        """Get current container locks"""
        with self.lock:
            return {container: list(locks) for container, locks in self.locks.items()}
    
    def is_container_locked(self, container_name: str, 
                           operation_types: List[OperationType] = None) -> bool:
        """Check if container is locked for specific operation types"""
        with self.lock:
            if container_name not in self.locks:
                return False
            
            if not operation_types:
                # Check if any locks exist
                return len(self.locks[container_name]) > 0
            
            # Check for specific operation type conflicts
            for op_id in self.locks[container_name]:
                if op_id in self.active_operations:
                    active_op = self.active_operations[op_id]
                    for op_type in operation_types:
                        severity = self._get_conflict_severity(op_type, active_op.operation_type)
                        if severity >= ConflictSeverity.HIGH:
                            return True
            
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self.lock:
            return {
                'containers': {
                    name: {
                        'state': info.state.value,
                        'health': info.health_status,
                        'last_updated': info.last_updated,
                        'ports': info.ports,
                        'dependencies': info.dependencies,
                        'locked': len(self.locks.get(name, [])) > 0,
                        'active_operations': len([op for op in self.active_operations.values() 
                                                if op.container_name == name])
                    }
                    for name, info in self.containers.items()
                },
                'active_operations': len(self.active_operations),
                'queued_operations': len(self.operation_queue),
                'total_operations_today': len([h for h in self.operation_history 
                                             if h.get('started_at', 0) > time.time() - 86400])
            }
    
    def force_unlock_container(self, container_name: str, reason: str = "") -> bool:
        """Force unlock a container (emergency use only)"""
        with self.lock:
            if container_name not in self.locks:
                return False
            
            # Clear all locks
            operation_ids = list(self.locks[container_name])
            self.locks[container_name].clear()
            
            # Mark active operations as failed
            for op_id in operation_ids:
                if op_id in self.active_operations:
                    operation = self.active_operations[op_id]
                    del self.active_operations[op_id]
                    
                    self.operation_history.append({
                        'operation_id': op_id,
                        'container': container_name,
                        'type': operation.operation_type.value,
                        'agent': operation.agent_id,
                        'completed_at': time.time(),
                        'status': 'force_cancelled',
                        'error': f"Force unlocked: {reason}"
                    })
            
            logger.warning(f"Force unlocked container {container_name}: {reason}")
            
            # Process queue
            self._process_operation_queue()
            
            return True
    
    def cleanup_expired_operations(self, timeout_seconds: Optional[int] = None) -> int:
        """Clean up expired operations"""
        if timeout_seconds is None:
            timeout_seconds = self.config['operation_timeout_seconds']
        
        expired_count = 0
        current_time = time.time()
        
        with self.lock:
            expired_ops = []
            for op_id, operation in self.active_operations.items():
                if current_time - operation.started_at > timeout_seconds:
                    expired_ops.append(op_id)
            
            for op_id in expired_ops:
                self.complete_operation(op_id, success=False, 
                                      error_message="Operation timeout")
                expired_count += 1
                logger.warning(f"Expired operation {op_id} due to timeout")
        
        return expired_count

# Global instance for easy access
_coordination_system = None

def get_coordination_system(config_path: Optional[str] = None) -> ContainerCoordinationSystem:
    """Get or create the global coordination system instance"""
    global _coordination_system
    if _coordination_system is None:
        _coordination_system = ContainerCoordinationSystem(config_path)
    return _coordination_system

def create_operation(container_name: str, operation_type: OperationType, 
                    agent_id: str, estimated_duration: float = 60.0,
                    priority: int = 5, description: str = "") -> ContainerOperation:
    """Helper function to create a container operation"""
    operation_id = f"{agent_id}-{container_name}-{operation_type.value}-{int(time.time())}"
    
    return ContainerOperation(
        operation_id=operation_id,
        container_name=container_name,
        operation_type=operation_type,
        agent_id=agent_id,
        started_at=time.time(),
        estimated_duration=estimated_duration,
        priority=priority,
        description=description
    )

# Integration helpers for the ML orchestrator
def integrate_with_ml_orchestrator(ml_orchestrator) -> bool:
    """Integrate container coordination with ML orchestrator"""
    try:
        coordination_system = get_coordination_system()
        
        # Register known containers
        containers = [
            ('api', [8000], []),
            ('webui', [3000], ['api']),
            ('worker', [], ['api', 'redis', 'postgres']),
            ('postgres', [5432], []),
            ('redis', [6379], []),
            ('voice-interaction-service', [8006], ['api']),
            ('chat-service', [8007], ['api']),
            ('prometheus', [9090], [])
        ]
        
        for name, ports, deps in containers:
            coordination_system.register_container(name, ports, deps)
        
        # Monkey patch ML orchestrator methods
        original_get_container_states = getattr(ml_orchestrator, '_get_container_states', None)
        original_detect_conflicts = getattr(ml_orchestrator, '_detect_container_conflicts', None)
        
        async def enhanced_get_container_states():
            """Enhanced container state retrieval"""
            states = coordination_system.get_all_container_states()
            return {name: state.value for name, state in states.items()}
        
        async def enhanced_detect_conflicts(context):
            """Enhanced conflict detection using coordination system"""
            operations = context.get('operations', [])
            conflicts = []
            
            for op_data in operations:
                container = op_data.get('container')
                op_type_str = op_data.get('type', 'read')
                agent_id = op_data.get('agent_id', 'unknown')
                
                # Convert to proper operation type
                try:
                    op_type = OperationType(op_type_str)
                except ValueError:
                    op_type = OperationType.READ
                
                # Create operation
                operation = create_operation(
                    container_name=container,
                    operation_type=op_type,
                    agent_id=agent_id,
                    description=op_data.get('description', '')
                )
                
                # Check conflicts
                operation_conflicts = coordination_system._check_operation_conflicts(operation)
                
                if operation_conflicts:
                    conflicts.extend(operation_conflicts)
            
            # Return in ML orchestrator format
            return ml_orchestrator.MLDecisionPoint(
                decision_type="container_conflict",
                options=[{
                    'conflicts': conflicts,
                    'safe_operations': [op for op in operations if not any(
                        conflict['conflicting_operation'] == op.get('operation_id') 
                        for conflict in conflicts
                    )],
                    'resolution_strategy': 'queue_conflicting_operations'
                }],
                confidence=0.9,
                reasoning="Enhanced conflict detection using container coordination system",
                risk_assessment=len(conflicts) / len(operations) if operations else 0.0
            )
        
        # Apply patches safely
        if original_get_container_states:
            ml_orchestrator._get_container_states = enhanced_get_container_states
        
        if original_detect_conflicts:
            ml_orchestrator._detect_container_conflicts = enhanced_detect_conflicts
        
        # Add coordination system reference
        ml_orchestrator.container_coordination = coordination_system
        
        logger.info("Successfully integrated container coordination with ML orchestrator")
        return True
        
    except Exception as e:
        logger.error(f"Failed to integrate with ML orchestrator: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    coordination_system = get_coordination_system()
    
    # Register containers
    coordination_system.register_container("api", [8000], [])
    coordination_system.register_container("webui", [3000], ["api"])
    coordination_system.register_container("worker", [], ["api", "redis"])
    
    # Update states
    coordination_system.update_container_state("api", ContainerState.RUNNING, "healthy")
    coordination_system.update_container_state("webui", ContainerState.RUNNING, "healthy")
    coordination_system.update_container_state("worker", ContainerState.RUNNING, "healthy")
    
    # Test operation
    operation = create_operation(
        container_name="api",
        operation_type=OperationType.CONFIG_UPDATE,
        agent_id="backend-gateway-expert",
        description="Update API configuration"
    )
    
    success, message = coordination_system.request_operation(operation)
    print(f"Operation request: {success} - {message}")
    
    # Show system status
    status = coordination_system.get_system_status()
    print(f"System status: {json.dumps(status, indent=2)}")