#!/usr/bin/env python3
"""
Priority Task Queue System
Manages tasks based on priority, dependencies, and resource availability
"""
import heapq
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import uuid


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class Priority(IntEnum):
    """Task priority levels (higher number = higher priority)"""
    CRITICAL = 10
    HIGH = 8
    URGENT = 7
    NORMAL = 5
    LOW = 3
    BACKGROUND = 1


@dataclass
class TaskDependency:
    """Task dependency definition"""
    task_id: str
    dependency_type: str  # 'completion', 'resource', 'data', 'agent'
    required_status: TaskStatus = TaskStatus.COMPLETED
    timeout_seconds: Optional[int] = None


@dataclass
class ResourceRequirement:
    """Resource requirement for task execution"""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_bandwidth: float = 0.0
    agent_slots: int = 1
    exclusive_resources: List[str] = field(default_factory=list)


@dataclass
class TaskMetadata:
    """Additional task metadata"""
    estimated_duration_minutes: float = 5.0
    retry_count: int = 0
    max_retries: int = 2
    created_by: str = "system"
    tags: Set[str] = field(default_factory=set)
    context_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PriorityTask:
    """Task with priority and dependency information"""
    task_id: str
    agent_name: str
    action: str
    parameters: Dict[str, Any]
    priority: Priority
    dependencies: List[TaskDependency] = field(default_factory=list)
    resource_requirements: ResourceRequirement = field(default_factory=ResourceRequirement)
    metadata: TaskMetadata = field(default_factory=TaskMetadata)
    
    # Runtime fields
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def __lt__(self, other):
        """Enable priority queue ordering"""
        # Higher priority values come first (max heap behavior)
        if self.priority != other.priority:
            return self.priority > other.priority
        # Break ties by creation time (older tasks first)
        return self.created_at < other.created_at


@dataclass
class AgentCapacity:
    """Agent capacity tracking"""
    agent_name: str
    max_concurrent_tasks: int = 1
    current_tasks: int = 0
    reserved_resources: ResourceRequirement = field(default_factory=ResourceRequirement)
    is_available: bool = True
    last_activity: datetime = field(default_factory=datetime.now)


class PriorityTaskQueue:
    """Manage tasks based on priority and dependencies"""
    
    def __init__(self, persistence_file: str = ".claude/logs/task_queue.json"):
        self.queue = []  # Priority queue (heap)
        self.tasks = {}  # task_id -> PriorityTask mapping
        self.dependencies_map = {}  # task_id -> set of dependent task_ids
        self.agent_capacities = {}  # agent_name -> AgentCapacity
        self.execution_history = []  # Completed/failed tasks
        
        # Persistence
        self.persistence_file = Path(persistence_file)
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Queue management
        self.lock = threading.RLock()
        self.max_history_size = 1000
        self.auto_cleanup_interval = 300  # 5 minutes
        
        # Resource tracking
        self.system_resources = ResourceRequirement(
            cpu_percent=100.0,
            memory_mb=psutil.virtual_memory().total / (1024*1024) * 0.8,  # 80% of system memory
            disk_mb=10000.0,  # 10GB
            network_bandwidth=100.0,  # 100 Mbps
            agent_slots=10
        )
        self.allocated_resources = ResourceRequirement()
        
        # Load persisted state
        self._load_state()
        
        # Start background processes
        self._start_background_processes()
    
    def add_task(self, agent_name: str, action: str, parameters: Dict[str, Any],
                 priority: Priority = Priority.NORMAL, 
                 depends_on: List[str] = None,
                 resource_requirements: ResourceRequirement = None,
                 metadata: TaskMetadata = None) -> str:
        """Add task to the priority queue"""
        
        with self.lock:
            task_id = str(uuid.uuid4())[:8]
            
            # Create dependencies
            dependencies = []
            if depends_on:
                for dep_id in depends_on:
                    dependencies.append(TaskDependency(
                        task_id=dep_id,
                        dependency_type='completion'
                    ))
            
            # Create task
            task = PriorityTask(
                task_id=task_id,
                agent_name=agent_name,
                action=action,
                parameters=parameters,
                priority=priority,
                dependencies=dependencies,
                resource_requirements=resource_requirements or ResourceRequirement(),
                metadata=metadata or TaskMetadata()
            )
            
            # Add to queue and mappings
            heapq.heappush(self.queue, task)
            self.tasks[task_id] = task
            
            # Update dependency mappings
            for dep in dependencies:
                if dep.task_id not in self.dependencies_map:
                    self.dependencies_map[dep.task_id] = set()
                self.dependencies_map[dep.task_id].add(task_id)
            
            # Ensure agent capacity exists
            if agent_name not in self.agent_capacities:
                self.agent_capacities[agent_name] = AgentCapacity(
                    agent_name=agent_name,
                    max_concurrent_tasks=self._get_default_agent_capacity(agent_name)
                )
            
            print(f"📋 [QUEUE] Added task {task_id}: {agent_name} -> {action} (priority: {priority.name})")
            
            # Auto-save state
            self._save_state()
            
            return task_id
    
    def get_next_executable_task(self, agent_filter: List[str] = None) -> Optional[PriorityTask]:
        """Get highest priority task with satisfied dependencies"""
        
        with self.lock:
            while self.queue:
                # Get highest priority task
                task = heapq.heappop(self.queue)
                
                # Skip if task is no longer pending
                if task.status != TaskStatus.PENDING:
                    continue
                
                # Skip if agent filter doesn't match
                if agent_filter and task.agent_name not in agent_filter:
                    # Re-queue the task
                    heapq.heappush(self.queue, task)
                    continue
                
                # Check if dependencies are satisfied
                if not self._dependencies_satisfied(task):
                    # Mark as blocked and re-queue
                    task.status = TaskStatus.BLOCKED
                    heapq.heappush(self.queue, task)
                    continue
                
                # Check if agent has capacity
                if not self._agent_has_capacity(task.agent_name):
                    # Re-queue and try next task
                    heapq.heappush(self.queue, task)
                    continue
                
                # Check if resources are available
                if not self._resources_available(task.resource_requirements):
                    # Re-queue and try next task
                    heapq.heappush(self.queue, task)
                    continue
                
                # Task is ready to execute
                task.status = TaskStatus.READY
                return task
            
            return None
    
    def start_task_execution(self, task_id: str, assigned_agent: str = None) -> bool:
        """Mark task as started and reserve resources"""
        
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.READY:
                return False
            
            # Reserve agent capacity
            agent_name = assigned_agent or task.agent_name
            if not self._reserve_agent_capacity(agent_name):
                return False
            
            # Reserve system resources
            if not self._reserve_resources(task.resource_requirements):
                self._release_agent_capacity(agent_name)
                return False
            
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.assigned_agent = agent_name
            
            print(f"🚀 [QUEUE] Started task {task_id}: {agent_name} -> {task.action}")
            
            self._save_state()
            return True
    
    def complete_task(self, task_id: str, result: Any = None, success: bool = True, 
                     error: str = None) -> bool:
        """Mark task as completed and release resources"""
        
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.RUNNING:
                return False
            
            # Update task status
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.result = result
            task.error = error
            
            # Release resources
            self._release_agent_capacity(task.assigned_agent or task.agent_name)
            self._release_resources(task.resource_requirements)
            
            # Move to history
            self.execution_history.append(task)
            
            # Update dependent tasks
            self._update_dependent_tasks(task_id)
            
            # Handle retries for failed tasks
            if not success and task.metadata.retry_count < task.metadata.max_retries:
                self._retry_task(task)
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} [QUEUE] Completed task {task_id}: {task.agent_name} -> {task.action}")
            
            self._save_state()
            return True
    
    def cancel_task(self, task_id: str, reason: str = "User cancelled") -> bool:
        """Cancel a pending or running task"""
        
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            # Release resources if task was running
            if task.status == TaskStatus.RUNNING:
                self._release_agent_capacity(task.assigned_agent or task.agent_name)
                self._release_resources(task.resource_requirements)
            
            # Update status
            task.status = TaskStatus.CANCELLED
            task.error = reason
            task.completed_at = datetime.now()
            
            print(f"🚫 [QUEUE] Cancelled task {task_id}: {reason}")
            
            self._save_state()
            return True
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get comprehensive queue status"""
        
        with self.lock:
            status_counts = {status: 0 for status in TaskStatus}
            agent_workload = {}
            priority_distribution = {p.name: 0 for p in Priority}
            
            # Count tasks by status
            for task in self.tasks.values():
                status_counts[task.status] += 1
                
                # Count by agent
                if task.agent_name not in agent_workload:
                    agent_workload[task.agent_name] = {'pending': 0, 'running': 0, 'completed': 0}
                
                if task.status == TaskStatus.PENDING:
                    agent_workload[task.agent_name]['pending'] += 1
                elif task.status == TaskStatus.RUNNING:
                    agent_workload[task.agent_name]['running'] += 1
                elif task.status == TaskStatus.COMPLETED:
                    agent_workload[task.agent_name]['completed'] += 1
                
                # Count by priority
                priority_distribution[task.priority.name] += 1
            
            # Calculate resource utilization
            resource_utilization = {
                'cpu_percent': (self.allocated_resources.cpu_percent / self.system_resources.cpu_percent) * 100,
                'memory_percent': (self.allocated_resources.memory_mb / self.system_resources.memory_mb) * 100,
                'agent_slots_used': sum(ac.current_tasks for ac in self.agent_capacities.values()),
                'agent_slots_total': sum(ac.max_concurrent_tasks for ac in self.agent_capacities.values())
            }
            
            return {
                'queue_size': len(self.queue),
                'total_tasks': len(self.tasks),
                'status_distribution': {k.value: v for k, v in status_counts.items()},
                'agent_workload': agent_workload,
                'priority_distribution': priority_distribution,
                'resource_utilization': resource_utilization,
                'execution_history_size': len(self.execution_history),
                'average_completion_time': self._calculate_average_completion_time()
            }
    
    def list_tasks(self, status_filter: List[TaskStatus] = None, 
                   agent_filter: List[str] = None, limit: int = 50) -> List[PriorityTask]:
        """List tasks with optional filtering"""
        
        with self.lock:
            filtered_tasks = []
            
            for task in self.tasks.values():
                # Apply status filter
                if status_filter and task.status not in status_filter:
                    continue
                
                # Apply agent filter
                if agent_filter and task.agent_name not in agent_filter:
                    continue
                
                filtered_tasks.append(task)
            
            # Sort by priority and creation time
            filtered_tasks.sort(key=lambda t: (-t.priority, t.created_at))
            
            return filtered_tasks[:limit]
    
    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task"""
        
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            
            # Calculate timing information
            age_seconds = (datetime.now() - task.created_at).total_seconds()
            execution_time = None
            if task.started_at and task.completed_at:
                execution_time = (task.completed_at - task.started_at).total_seconds()
            
            # Get dependency status
            dependency_status = []
            for dep in task.dependencies:
                dep_task = self.tasks.get(dep.task_id)
                dependency_status.append({
                    'task_id': dep.task_id,
                    'type': dep.dependency_type,
                    'status': dep_task.status.value if dep_task else 'unknown',
                    'satisfied': self._is_dependency_satisfied(dep)
                })
            
            return {
                'task_id': task.task_id,
                'agent_name': task.agent_name,
                'action': task.action,
                'parameters': task.parameters,
                'priority': task.priority.name,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'assigned_agent': task.assigned_agent,
                'age_seconds': age_seconds,
                'execution_time_seconds': execution_time,
                'retry_count': task.metadata.retry_count,
                'max_retries': task.metadata.max_retries,
                'dependencies': dependency_status,
                'resource_requirements': {
                    'cpu_percent': task.resource_requirements.cpu_percent,
                    'memory_mb': task.resource_requirements.memory_mb,
                    'disk_mb': task.resource_requirements.disk_mb,
                    'agent_slots': task.resource_requirements.agent_slots
                },
                'tags': list(task.metadata.tags),
                'error': task.error,
                'result_summary': str(task.result)[:200] + "..." if task.result and len(str(task.result)) > 200 else str(task.result)
            }
    
    def set_agent_capacity(self, agent_name: str, max_concurrent_tasks: int):
        """Set maximum concurrent tasks for an agent"""
        
        with self.lock:
            if agent_name not in self.agent_capacities:
                self.agent_capacities[agent_name] = AgentCapacity(agent_name=agent_name)
            
            self.agent_capacities[agent_name].max_concurrent_tasks = max_concurrent_tasks
            print(f"⚙️ [QUEUE] Set {agent_name} capacity to {max_concurrent_tasks} concurrent tasks")
    
    def pause_agent(self, agent_name: str):
        """Pause task execution for an agent"""
        
        with self.lock:
            if agent_name in self.agent_capacities:
                self.agent_capacities[agent_name].is_available = False
                print(f"⏸️ [QUEUE] Paused agent: {agent_name}")
    
    def resume_agent(self, agent_name: str):
        """Resume task execution for an agent"""
        
        with self.lock:
            if agent_name in self.agent_capacities:
                self.agent_capacities[agent_name].is_available = True
                print(f"▶️ [QUEUE] Resumed agent: {agent_name}")
    
    def _dependencies_satisfied(self, task: PriorityTask) -> bool:
        """Check if all task dependencies are satisfied"""
        
        for dependency in task.dependencies:
            if not self._is_dependency_satisfied(dependency):
                return False
        
        return True
    
    def _is_dependency_satisfied(self, dependency: TaskDependency) -> bool:
        """Check if a specific dependency is satisfied"""
        
        if dependency.task_id not in self.tasks:
            return False
        
        dep_task = self.tasks[dependency.task_id]
        
        # Check status requirement
        if dep_task.status != dependency.required_status:
            return False
        
        # Check timeout if specified
        if dependency.timeout_seconds:
            if dep_task.completed_at:
                time_since_completion = (datetime.now() - dep_task.completed_at).total_seconds()
                if time_since_completion > dependency.timeout_seconds:
                    return False
        
        return True
    
    def _agent_has_capacity(self, agent_name: str) -> bool:
        """Check if agent has capacity for another task"""
        
        if agent_name not in self.agent_capacities:
            return True
        
        capacity = self.agent_capacities[agent_name]
        return (capacity.is_available and 
                capacity.current_tasks < capacity.max_concurrent_tasks)
    
    def _resources_available(self, requirements: ResourceRequirement) -> bool:
        """Check if system resources are available"""
        
        # Check CPU
        if (self.allocated_resources.cpu_percent + requirements.cpu_percent) > self.system_resources.cpu_percent:
            return False
        
        # Check memory
        if (self.allocated_resources.memory_mb + requirements.memory_mb) > self.system_resources.memory_mb:
            return False
        
        # Check agent slots
        if (self.allocated_resources.agent_slots + requirements.agent_slots) > self.system_resources.agent_slots:
            return False
        
        return True
    
    def _reserve_agent_capacity(self, agent_name: str) -> bool:
        """Reserve agent capacity"""
        
        if not self._agent_has_capacity(agent_name):
            return False
        
        self.agent_capacities[agent_name].current_tasks += 1
        return True
    
    def _release_agent_capacity(self, agent_name: str):
        """Release agent capacity"""
        
        if agent_name in self.agent_capacities:
            self.agent_capacities[agent_name].current_tasks = max(0, 
                self.agent_capacities[agent_name].current_tasks - 1)
    
    def _reserve_resources(self, requirements: ResourceRequirement) -> bool:
        """Reserve system resources"""
        
        if not self._resources_available(requirements):
            return False
        
        self.allocated_resources.cpu_percent += requirements.cpu_percent
        self.allocated_resources.memory_mb += requirements.memory_mb
        self.allocated_resources.disk_mb += requirements.disk_mb
        self.allocated_resources.agent_slots += requirements.agent_slots
        
        return True
    
    def _release_resources(self, requirements: ResourceRequirement):
        """Release system resources"""
        
        self.allocated_resources.cpu_percent = max(0, self.allocated_resources.cpu_percent - requirements.cpu_percent)
        self.allocated_resources.memory_mb = max(0, self.allocated_resources.memory_mb - requirements.memory_mb)
        self.allocated_resources.disk_mb = max(0, self.allocated_resources.disk_mb - requirements.disk_mb)
        self.allocated_resources.agent_slots = max(0, self.allocated_resources.agent_slots - requirements.agent_slots)
    
    def _update_dependent_tasks(self, completed_task_id: str):
        """Update tasks that depend on the completed task"""
        
        if completed_task_id in self.dependencies_map:
            dependent_task_ids = self.dependencies_map[completed_task_id]
            
            for dep_task_id in dependent_task_ids:
                if dep_task_id in self.tasks:
                    dep_task = self.tasks[dep_task_id]
                    if dep_task.status == TaskStatus.BLOCKED:
                        # Re-check if task can now be executed
                        if self._dependencies_satisfied(dep_task):
                            dep_task.status = TaskStatus.PENDING
                            # Re-add to queue
                            heapq.heappush(self.queue, dep_task)
    
    def _retry_task(self, failed_task: PriorityTask):
        """Create retry task for failed task"""
        
        retry_id = f"{failed_task.task_id}_retry_{failed_task.metadata.retry_count + 1}"
        
        retry_task = PriorityTask(
            task_id=retry_id,
            agent_name=failed_task.agent_name,
            action=failed_task.action,
            parameters=failed_task.parameters.copy(),
            priority=failed_task.priority,
            dependencies=failed_task.dependencies.copy(),
            resource_requirements=failed_task.resource_requirements,
            metadata=TaskMetadata(
                estimated_duration_minutes=failed_task.metadata.estimated_duration_minutes,
                retry_count=failed_task.metadata.retry_count + 1,
                max_retries=failed_task.metadata.max_retries,
                created_by=failed_task.metadata.created_by,
                tags=failed_task.metadata.tags | {'retry'},
                context_data=failed_task.metadata.context_data.copy()
            )
        )
        
        # Add retry task to queue
        heapq.heappush(self.queue, retry_task)
        self.tasks[retry_id] = retry_task
        
        print(f"🔄 [QUEUE] Created retry task {retry_id} (attempt {retry_task.metadata.retry_count + 1})")
    
    def _get_default_agent_capacity(self, agent_name: str) -> int:
        """Get default capacity for agent type"""
        
        capacity_map = {
            'project-orchestrator': 3,
            'ui-regression-debugger': 1,
            'backend-gateway-expert': 2,
            'security-validator': 1,
            'schema-database-expert': 2,
            'codebase-research-analyst': 3,
            'nexus-synthesis-agent': 1
        }
        
        return capacity_map.get(agent_name, 1)
    
    def _calculate_average_completion_time(self) -> float:
        """Calculate average task completion time"""
        
        if not self.execution_history:
            return 0.0
        
        total_time = 0.0
        completed_tasks = 0
        
        for task in self.execution_history[-100:]:  # Last 100 tasks
            if task.started_at and task.completed_at:
                execution_time = (task.completed_at - task.started_at).total_seconds()
                total_time += execution_time
                completed_tasks += 1
        
        return total_time / max(1, completed_tasks)
    
    def _save_state(self):
        """Save queue state to disk"""
        
        try:
            # Prepare serializable data
            data = {
                'tasks': {
                    task_id: {
                        'task_id': task.task_id,
                        'agent_name': task.agent_name,
                        'action': task.action,
                        'parameters': task.parameters,
                        'priority': task.priority.value,
                        'status': task.status.value,
                        'created_at': task.created_at.isoformat(),
                        'started_at': task.started_at.isoformat() if task.started_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'dependencies': [
                            {
                                'task_id': dep.task_id,
                                'dependency_type': dep.dependency_type,
                                'required_status': dep.required_status.value,
                                'timeout_seconds': dep.timeout_seconds
                            } for dep in task.dependencies
                        ],
                        'resource_requirements': {
                            'cpu_percent': task.resource_requirements.cpu_percent,
                            'memory_mb': task.resource_requirements.memory_mb,
                            'disk_mb': task.resource_requirements.disk_mb,
                            'agent_slots': task.resource_requirements.agent_slots
                        },
                        'metadata': {
                            'estimated_duration_minutes': task.metadata.estimated_duration_minutes,
                            'retry_count': task.metadata.retry_count,
                            'max_retries': task.metadata.max_retries,
                            'tags': list(task.metadata.tags)
                        }
                    } for task_id, task in self.tasks.items()
                },
                'agent_capacities': {
                    agent_name: {
                        'max_concurrent_tasks': capacity.max_concurrent_tasks,
                        'current_tasks': capacity.current_tasks,
                        'is_available': capacity.is_available
                    } for agent_name, capacity in self.agent_capacities.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving queue state: {e}")
    
    def _load_state(self):
        """Load queue state from disk"""
        
        if not self.persistence_file.exists():
            return
        
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Restore tasks
            for task_id, task_data in data.get('tasks', {}).items():
                # Skip completed/failed tasks older than 24 hours
                created_at = datetime.fromisoformat(task_data['created_at'])
                if task_data['status'] in ['completed', 'failed', 'cancelled']:
                    if (datetime.now() - created_at).total_seconds() > 24 * 3600:
                        continue
                
                # Recreate task
                task = PriorityTask(
                    task_id=task_data['task_id'],
                    agent_name=task_data['agent_name'],
                    action=task_data['action'],
                    parameters=task_data['parameters'],
                    priority=Priority(task_data['priority']),
                    status=TaskStatus(task_data['status']),
                    created_at=created_at
                )
                
                if task_data['started_at']:
                    task.started_at = datetime.fromisoformat(task_data['started_at'])
                if task_data['completed_at']:
                    task.completed_at = datetime.fromisoformat(task_data['completed_at'])
                
                # Recreate dependencies
                for dep_data in task_data.get('dependencies', []):
                    dep = TaskDependency(
                        task_id=dep_data['task_id'],
                        dependency_type=dep_data['dependency_type'],
                        required_status=TaskStatus(dep_data['required_status']),
                        timeout_seconds=dep_data.get('timeout_seconds')
                    )
                    task.dependencies.append(dep)
                
                # Recreate resource requirements
                req_data = task_data.get('resource_requirements', {})
                task.resource_requirements = ResourceRequirement(
                    cpu_percent=req_data.get('cpu_percent', 0.0),
                    memory_mb=req_data.get('memory_mb', 0.0),
                    disk_mb=req_data.get('disk_mb', 0.0),
                    agent_slots=req_data.get('agent_slots', 1)
                )
                
                # Recreate metadata
                meta_data = task_data.get('metadata', {})
                task.metadata = TaskMetadata(
                    estimated_duration_minutes=meta_data.get('estimated_duration_minutes', 5.0),
                    retry_count=meta_data.get('retry_count', 0),
                    max_retries=meta_data.get('max_retries', 2),
                    tags=set(meta_data.get('tags', []))
                )
                
                # Add to collections
                self.tasks[task_id] = task
                
                # Add pending tasks to queue
                if task.status == TaskStatus.PENDING:
                    heapq.heappush(self.queue, task)
            
            # Restore agent capacities
            for agent_name, capacity_data in data.get('agent_capacities', {}).items():
                self.agent_capacities[agent_name] = AgentCapacity(
                    agent_name=agent_name,
                    max_concurrent_tasks=capacity_data.get('max_concurrent_tasks', 1),
                    current_tasks=capacity_data.get('current_tasks', 0),
                    is_available=capacity_data.get('is_available', True)
                )
            
        except Exception as e:
            print(f"Error loading queue state: {e}")
    
    def _start_background_processes(self):
        """Start background maintenance processes"""
        
        def cleanup_loop():
            while True:
                try:
                    time.sleep(self.auto_cleanup_interval)
                    self._cleanup_old_tasks()
                except Exception as e:
                    print(f"Queue cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_old_tasks(self):
        """Clean up old completed/failed tasks"""
        
        with self.lock:
            current_time = datetime.now()
            cleanup_threshold = current_time - timedelta(hours=24)
            
            old_task_ids = []
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.completed_at and task.completed_at < cleanup_threshold):
                    old_task_ids.append(task_id)
            
            # Remove old tasks
            for task_id in old_task_ids:
                if task_id in self.tasks:
                    del self.tasks[task_id]
            
            if old_task_ids:
                print(f"🧹 [QUEUE] Cleaned up {len(old_task_ids)} old tasks")
            
            # Limit execution history size
            if len(self.execution_history) > self.max_history_size:
                self.execution_history = self.execution_history[-self.max_history_size//2:]


# Import psutil here to avoid issues if not installed
try:
    import psutil
except ImportError:
    print("Warning: psutil not installed, using default system resource values")
    class MockPsutil:
        class virtual_memory:
            @staticmethod
            def total():
                return 8 * 1024 * 1024 * 1024  # 8GB default
    psutil = MockPsutil()


# Global queue instance
task_queue = PriorityTaskQueue()

def add_task(agent_name: str, action: str, parameters: Dict[str, Any], 
             priority: Priority = Priority.NORMAL, **kwargs) -> str:
    """Convenience function for adding tasks"""
    return task_queue.add_task(agent_name, action, parameters, priority, **kwargs)

def get_next_task(agent_filter: List[str] = None) -> Optional[PriorityTask]:
    """Convenience function for getting next task"""
    return task_queue.get_next_executable_task(agent_filter)

def complete_task(task_id: str, result: Any = None, success: bool = True, error: str = None) -> bool:
    """Convenience function for completing tasks"""
    return task_queue.complete_task(task_id, result, success, error)

def get_queue_status() -> Dict[str, Any]:
    """Convenience function for queue status"""
    return task_queue.get_queue_status()


if __name__ == "__main__":
    # Test the priority queue system
    print("Testing Priority Task Queue System...")
    
    # Add some test tasks
    task1 = add_task("codebase-research-analyst", "search_code", 
                    {"query": "authentication"}, Priority.HIGH)
    
    task2 = add_task("ui-regression-debugger", "test_login", 
                    {"url": "http://localhost:3000"}, Priority.CRITICAL,
                    depends_on=[task1])
    
    task3 = add_task("security-validator", "scan_vulnerabilities",
                    {"target": "app"}, Priority.NORMAL)
    
    print(f"✅ Added tasks: {task1}, {task2}, {task3}")
    
    # Get queue status
    status = get_queue_status()
    print(f"\n📊 Queue Status:")
    for key, value in status.items():
        print(f"  • {key}: {value}")
    
    # Get next executable task
    next_task = get_next_task()
    if next_task:
        print(f"\n🎯 Next executable task: {next_task.task_id} ({next_task.action})")
        
        # Start and complete the task
        if task_queue.start_task_execution(next_task.task_id):
            print("🚀 Task started")
            complete_task(next_task.task_id, {"status": "success"}, success=True)
            print("✅ Task completed")
        
        # Check status again
        updated_status = get_queue_status()
        print(f"\n📊 Updated Queue Status:")
        print(f"  • Completed tasks: {updated_status['status_distribution']['completed']}")
    else:
        print("\n⚠️ No executable tasks found")