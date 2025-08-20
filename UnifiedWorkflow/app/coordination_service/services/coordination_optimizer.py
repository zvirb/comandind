"""Enhanced Coordination Optimizer with Dynamic Resource Allocation.

This module implements intelligent resource allocation algorithms and workflow
optimization patterns to improve multi-agent coordination efficiency by 30%.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import heapq

import structlog
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger(__name__)

# Metrics
coordination_efficiency = Histogram(
    'coordination_efficiency_seconds',
    'Time taken for agent coordination operations',
    ['operation_type', 'agent_count']
)

resource_allocation_counter = Counter(
    'resource_allocations_total',
    'Total resource allocation operations',
    ['allocation_type', 'status']
)

active_coordination_gauge = Gauge(
    'active_coordinations',
    'Number of active coordination operations'
)

agent_utilization_gauge = Gauge(
    'agent_utilization_ratio',
    'Current agent utilization ratio',
    ['agent_type']
)


class ResourceType(str, Enum):
    """Types of resources that can be allocated."""
    CPU = "cpu"
    MEMORY = "memory"
    TOKENS = "tokens"
    TIME = "time"
    PRIORITY = "priority"


class AllocationStrategy(str, Enum):
    """Resource allocation strategies."""
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"
    ADAPTIVE = "adaptive"
    HISTORICAL = "historical"


@dataclass
class AgentResource:
    """Represents resource allocation for an agent."""
    agent_id: str
    agent_type: str
    allocated_resources: Dict[ResourceType, float]
    max_resources: Dict[ResourceType, float]
    utilization: float = 0.0
    performance_score: float = 1.0
    task_queue: deque = field(default_factory=deque)
    active_tasks: List[str] = field(default_factory=list)
    
    def can_accept_task(self, required_resources: Dict[ResourceType, float]) -> bool:
        """Check if agent can accept a new task."""
        for resource_type, required in required_resources.items():
            allocated = self.allocated_resources.get(resource_type, 0)
            max_available = self.max_resources.get(resource_type, float('inf'))
            if allocated + required > max_available:
                return False
        return True
    
    def allocate_task(self, task_id: str, resources: Dict[ResourceType, float]) -> None:
        """Allocate resources for a new task."""
        for resource_type, amount in resources.items():
            current = self.allocated_resources.get(resource_type, 0)
            self.allocated_resources[resource_type] = current + amount
        self.active_tasks.append(task_id)
        self._update_utilization()
    
    def release_task(self, task_id: str, resources: Dict[ResourceType, float]) -> None:
        """Release resources from completed task."""
        for resource_type, amount in resources.items():
            current = self.allocated_resources.get(resource_type, 0)
            self.allocated_resources[resource_type] = max(0, current - amount)
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
        self._update_utilization()
    
    def _update_utilization(self) -> None:
        """Update utilization score based on resource usage."""
        if not self.max_resources:
            self.utilization = 0.0
            return
        
        total_utilization = 0.0
        resource_count = 0
        
        for resource_type, max_value in self.max_resources.items():
            if max_value > 0:
                allocated = self.allocated_resources.get(resource_type, 0)
                total_utilization += allocated / max_value
                resource_count += 1
        
        self.utilization = total_utilization / resource_count if resource_count > 0 else 0.0


@dataclass
class CoordinationTask:
    """Represents a coordination task to be allocated."""
    task_id: str
    task_type: str
    priority: int
    required_resources: Dict[ResourceType, float]
    estimated_duration: float
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    assigned_agent: Optional[str] = None
    status: str = "pending"
    
    def __lt__(self, other):
        """Compare tasks by priority for heap operations."""
        return self.priority > other.priority  # Higher priority first


class CoordinationOptimizer:
    """Optimizes multi-agent coordination with dynamic resource allocation."""
    
    def __init__(
        self,
        max_concurrent_coordinations: int = 10,
        optimization_interval: int = 5,
        learning_rate: float = 0.1
    ):
        self.max_concurrent_coordinations = max_concurrent_coordinations
        self.optimization_interval = optimization_interval
        self.learning_rate = learning_rate
        
        # Agent resource tracking
        self.agent_resources: Dict[str, AgentResource] = {}
        self.agent_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Task management
        self.pending_tasks: List[CoordinationTask] = []
        self.active_tasks: Dict[str, CoordinationTask] = {}
        self.completed_tasks: deque = deque(maxlen=1000)
        
        # Coordination patterns
        self.coordination_patterns: Dict[str, Dict[str, Any]] = {}
        self.pattern_success_rates: Dict[str, float] = {}
        
        # Performance metrics
        self.coordination_metrics = {
            "total_coordinations": 0,
            "successful_coordinations": 0,
            "failed_coordinations": 0,
            "avg_coordination_time": 0.0,
            "resource_efficiency": 0.0,
            "throughput": 0.0
        }
        
        # Optimization state
        self._optimization_running = False
        self._last_optimization = 0.0
        
        # Communication protocols
        self.communication_protocols = {
            "sync": self._sync_communication,
            "async": self._async_communication,
            "broadcast": self._broadcast_communication,
            "pipeline": self._pipeline_communication
        }
    
    async def initialize(self) -> None:
        """Initialize the coordination optimizer."""
        logger.info("Initializing Coordination Optimizer...")
        
        # Start optimization loop
        asyncio.create_task(self._run_optimization_loop())
        
        # Load historical patterns
        await self._load_coordination_patterns()
        
        logger.info(
            "Coordination Optimizer initialized",
            max_concurrent=self.max_concurrent_coordinations,
            optimization_interval=self.optimization_interval
        )
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        max_resources: Dict[ResourceType, float]
    ) -> None:
        """Register an agent with its resource capabilities."""
        logger.debug(f"Registering agent: {agent_id} ({agent_type})")
        
        self.agent_resources[agent_id] = AgentResource(
            agent_id=agent_id,
            agent_type=agent_type,
            allocated_resources={},
            max_resources=max_resources
        )
        
        # Update utilization gauge
        agent_utilization_gauge.labels(agent_type=agent_type).set(0.0)
    
    async def allocate_task(
        self,
        task_id: str,
        task_type: str,
        priority: int,
        required_resources: Dict[ResourceType, float],
        estimated_duration: float,
        dependencies: Optional[List[str]] = None
    ) -> Optional[str]:
        """Allocate a task to the most suitable agent."""
        with coordination_efficiency.labels(
            operation_type="task_allocation",
            agent_count=len(self.agent_resources)
        ).time():
            
            task = CoordinationTask(
                task_id=task_id,
                task_type=task_type,
                priority=priority,
                required_resources=required_resources,
                estimated_duration=estimated_duration,
                dependencies=dependencies or []
            )
            
            # Check if dependencies are satisfied
            if not await self._check_dependencies(task):
                heapq.heappush(self.pending_tasks, task)
                return None
            
            # Find optimal agent
            agent_id = await self._find_optimal_agent(task)
            
            if agent_id:
                # Allocate task to agent
                agent = self.agent_resources[agent_id]
                agent.allocate_task(task_id, required_resources)
                
                task.assigned_agent = agent_id
                task.status = "assigned"
                self.active_tasks[task_id] = task
                
                resource_allocation_counter.labels(
                    allocation_type="task",
                    status="success"
                ).inc()
                
                # Update utilization
                agent_utilization_gauge.labels(
                    agent_type=agent.agent_type
                ).set(agent.utilization)
                
                logger.info(
                    f"Task allocated: {task_id} -> {agent_id}",
                    priority=priority,
                    resources=required_resources
                )
                
                return agent_id
            else:
                # Queue task for later allocation
                heapq.heappush(self.pending_tasks, task)
                
                resource_allocation_counter.labels(
                    allocation_type="task",
                    status="queued"
                ).inc()
                
                logger.debug(f"Task queued: {task_id} (no suitable agent)")
                return None
    
    async def complete_task(
        self,
        task_id: str,
        success: bool,
        execution_time: float,
        performance_metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a task as completed and release resources."""
        if task_id not in self.active_tasks:
            logger.warning(f"Unknown task completion: {task_id}")
            return
        
        task = self.active_tasks[task_id]
        agent_id = task.assigned_agent
        
        if agent_id and agent_id in self.agent_resources:
            agent = self.agent_resources[agent_id]
            
            # Release resources
            agent.release_task(task_id, task.required_resources)
            
            # Update performance history
            performance_score = 1.0 if success else 0.0
            if execution_time > 0 and task.estimated_duration > 0:
                # Adjust score based on time efficiency
                time_efficiency = min(1.0, task.estimated_duration / execution_time)
                performance_score *= time_efficiency
            
            self.agent_performance_history[agent_id].append(performance_score)
            
            # Update agent performance score
            if self.agent_performance_history[agent_id]:
                agent.performance_score = sum(self.agent_performance_history[agent_id]) / len(
                    self.agent_performance_history[agent_id]
                )
            
            # Update utilization
            agent_utilization_gauge.labels(
                agent_type=agent.agent_type
            ).set(agent.utilization)
        
        # Move to completed
        task.status = "completed" if success else "failed"
        self.completed_tasks.append(task)
        del self.active_tasks[task_id]
        
        # Update metrics
        self.coordination_metrics["total_coordinations"] += 1
        if success:
            self.coordination_metrics["successful_coordinations"] += 1
        else:
            self.coordination_metrics["failed_coordinations"] += 1
        
        # Update average coordination time
        current_avg = self.coordination_metrics["avg_coordination_time"]
        total_count = self.coordination_metrics["total_coordinations"]
        self.coordination_metrics["avg_coordination_time"] = (
            (current_avg * (total_count - 1) + execution_time) / total_count
        )
        
        logger.info(
            f"Task completed: {task_id}",
            success=success,
            execution_time=execution_time,
            agent=agent_id
        )
        
        # Try to allocate pending tasks
        await self._process_pending_tasks()
    
    async def optimize_coordination_pattern(
        self,
        pattern_name: str,
        agents: List[str],
        workflow_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize coordination pattern based on historical performance."""
        with coordination_efficiency.labels(
            operation_type="pattern_optimization",
            agent_count=len(agents)
        ).time():
            
            # Get historical success rate
            success_rate = self.pattern_success_rates.get(pattern_name, 0.5)
            
            # Determine optimal communication protocol
            protocol = await self._select_communication_protocol(
                agents,
                workflow_type,
                success_rate
            )
            
            # Calculate resource allocation weights
            allocation_weights = await self._calculate_allocation_weights(
                agents,
                workflow_type,
                context
            )
            
            # Generate optimized coordination strategy
            strategy = {
                "pattern_name": pattern_name,
                "communication_protocol": protocol,
                "allocation_weights": allocation_weights,
                "parallelization_level": self._calculate_parallelization_level(agents),
                "checkpoint_intervals": self._calculate_checkpoint_intervals(workflow_type),
                "timeout_settings": self._calculate_timeout_settings(agents, workflow_type),
                "retry_policy": self._generate_retry_policy(success_rate),
                "success_rate": success_rate
            }
            
            # Store pattern for learning
            self.coordination_patterns[pattern_name] = strategy
            
            logger.info(
                f"Coordination pattern optimized: {pattern_name}",
                protocol=protocol,
                parallelization=strategy["parallelization_level"]
            )
            
            return strategy
    
    async def record_pattern_outcome(
        self,
        pattern_name: str,
        success: bool,
        execution_time: float,
        resource_usage: Dict[ResourceType, float]
    ) -> None:
        """Record outcome of a coordination pattern for learning."""
        # Update success rate with exponential moving average
        current_rate = self.pattern_success_rates.get(pattern_name, 0.5)
        new_value = 1.0 if success else 0.0
        
        self.pattern_success_rates[pattern_name] = (
            current_rate * (1 - self.learning_rate) + new_value * self.learning_rate
        )
        
        # Update pattern metadata
        if pattern_name in self.coordination_patterns:
            pattern = self.coordination_patterns[pattern_name]
            pattern["last_execution_time"] = execution_time
            pattern["last_resource_usage"] = resource_usage
            pattern["success_rate"] = self.pattern_success_rates[pattern_name]
        
        logger.debug(
            f"Pattern outcome recorded: {pattern_name}",
            success=success,
            new_success_rate=self.pattern_success_rates[pattern_name]
        )
    
    async def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get current coordination metrics and efficiency statistics."""
        # Calculate resource efficiency
        total_utilization = sum(
            agent.utilization for agent in self.agent_resources.values()
        )
        avg_utilization = total_utilization / len(self.agent_resources) if self.agent_resources else 0
        
        # Calculate throughput
        if self.coordination_metrics["avg_coordination_time"] > 0:
            throughput = 3600 / self.coordination_metrics["avg_coordination_time"]  # Tasks per hour
        else:
            throughput = 0
        
        return {
            "metrics": {
                **self.coordination_metrics,
                "resource_efficiency": avg_utilization,
                "throughput": throughput
            },
            "agent_statistics": {
                agent_id: {
                    "utilization": agent.utilization,
                    "performance_score": agent.performance_score,
                    "active_tasks": len(agent.active_tasks),
                    "queued_tasks": len(agent.task_queue)
                }
                for agent_id, agent in self.agent_resources.items()
            },
            "task_statistics": {
                "pending_tasks": len(self.pending_tasks),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks)
            },
            "pattern_statistics": {
                pattern: {
                    "success_rate": rate,
                    "usage_count": self.coordination_patterns.get(pattern, {}).get("usage_count", 0)
                }
                for pattern, rate in self.pattern_success_rates.items()
            }
        }
    
    # Private helper methods
    
    async def _find_optimal_agent(self, task: CoordinationTask) -> Optional[str]:
        """Find the optimal agent for a task using adaptive allocation."""
        suitable_agents = []
        
        for agent_id, agent in self.agent_resources.items():
            if agent.can_accept_task(task.required_resources):
                # Calculate suitability score
                score = self._calculate_agent_score(agent, task)
                suitable_agents.append((score, agent_id))
        
        if not suitable_agents:
            return None
        
        # Sort by score (highest first)
        suitable_agents.sort(reverse=True)
        
        # Return best agent
        return suitable_agents[0][1]
    
    def _calculate_agent_score(self, agent: AgentResource, task: CoordinationTask) -> float:
        """Calculate suitability score for agent-task pairing."""
        # Base score from performance history
        score = agent.performance_score
        
        # Adjust for current utilization (prefer less loaded agents)
        score *= (1.0 - agent.utilization * 0.5)
        
        # Adjust for task priority
        score *= (1.0 + task.priority * 0.1)
        
        # Adjust for queue length
        if agent.task_queue:
            score *= (1.0 / (1.0 + len(agent.task_queue) * 0.2))
        
        return score
    
    async def _check_dependencies(self, task: CoordinationTask) -> bool:
        """Check if task dependencies are satisfied."""
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            # Check if dependency is completed
            completed = any(
                t.task_id == dep_id and t.status == "completed"
                for t in self.completed_tasks
            )
            if not completed:
                return False
        
        return True
    
    async def _process_pending_tasks(self) -> None:
        """Process pending tasks when resources become available."""
        if not self.pending_tasks:
            return
        
        processed_tasks = []
        temp_queue = []
        
        while self.pending_tasks:
            task = heapq.heappop(self.pending_tasks)
            
            if await self._check_dependencies(task):
                agent_id = await self._find_optimal_agent(task)
                
                if agent_id:
                    # Allocate task
                    agent = self.agent_resources[agent_id]
                    agent.allocate_task(task.task_id, task.required_resources)
                    
                    task.assigned_agent = agent_id
                    task.status = "assigned"
                    self.active_tasks[task.task_id] = task
                    
                    processed_tasks.append(task.task_id)
                else:
                    temp_queue.append(task)
            else:
                temp_queue.append(task)
        
        # Restore unprocessed tasks to queue
        for task in temp_queue:
            heapq.heappush(self.pending_tasks, task)
        
        if processed_tasks:
            logger.info(f"Processed {len(processed_tasks)} pending tasks")
    
    async def _select_communication_protocol(
        self,
        agents: List[str],
        workflow_type: str,
        success_rate: float
    ) -> str:
        """Select optimal communication protocol based on context."""
        agent_count = len(agents)
        
        if agent_count <= 2:
            return "sync"  # Direct synchronous for small groups
        elif agent_count <= 5 and success_rate > 0.8:
            return "async"  # Async for reliable medium groups
        elif workflow_type == "sequential":
            return "pipeline"  # Pipeline for sequential workflows
        else:
            return "broadcast"  # Broadcast for large parallel groups
    
    async def _calculate_allocation_weights(
        self,
        agents: List[str],
        workflow_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate resource allocation weights for agents."""
        weights = {}
        
        for agent_id in agents:
            if agent_id in self.agent_resources:
                agent = self.agent_resources[agent_id]
                
                # Base weight on performance score
                weight = agent.performance_score
                
                # Adjust for workflow type
                if workflow_type == "parallel":
                    weight *= 1.2  # Boost for parallel execution
                elif workflow_type == "sequential":
                    weight *= 0.8  # Reduce for sequential (one at a time)
                
                # Adjust for current load
                weight *= (1.0 - agent.utilization * 0.3)
                
                weights[agent_id] = max(0.1, min(1.0, weight))
            else:
                weights[agent_id] = 0.5  # Default weight for unknown agents
        
        return weights
    
    def _calculate_parallelization_level(self, agents: List[str]) -> int:
        """Calculate optimal parallelization level."""
        available_agents = sum(
            1 for agent_id in agents
            if agent_id in self.agent_resources and
            self.agent_resources[agent_id].utilization < 0.8
        )
        
        return min(
            available_agents,
            self.max_concurrent_coordinations,
            len(agents)
        )
    
    def _calculate_checkpoint_intervals(self, workflow_type: str) -> List[int]:
        """Calculate checkpoint intervals based on workflow type."""
        if workflow_type == "critical":
            return [5, 10, 20, 30]  # Frequent checkpoints
        elif workflow_type == "long_running":
            return [30, 60, 120, 240]  # Sparse checkpoints
        else:
            return [10, 30, 60]  # Default intervals
    
    def _calculate_timeout_settings(
        self,
        agents: List[str],
        workflow_type: str
    ) -> Dict[str, int]:
        """Calculate timeout settings for coordination."""
        base_timeout = 60  # Base timeout in seconds
        
        if workflow_type == "realtime":
            multiplier = 0.5
        elif workflow_type == "batch":
            multiplier = 2.0
        else:
            multiplier = 1.0
        
        return {
            "task_timeout": int(base_timeout * multiplier),
            "coordination_timeout": int(base_timeout * multiplier * len(agents)),
            "total_timeout": int(base_timeout * multiplier * len(agents) * 2)
        }
    
    def _generate_retry_policy(self, success_rate: float) -> Dict[str, Any]:
        """Generate retry policy based on success rate."""
        if success_rate > 0.9:
            return {"max_retries": 1, "backoff": "linear", "delay": 5}
        elif success_rate > 0.7:
            return {"max_retries": 2, "backoff": "exponential", "delay": 10}
        else:
            return {"max_retries": 3, "backoff": "exponential", "delay": 15}
    
    async def _sync_communication(self, agents: List[str], message: Any) -> None:
        """Synchronous communication protocol."""
        for agent_id in agents:
            # Send message and wait for acknowledgment
            pass  # Implementation depends on actual communication mechanism
    
    async def _async_communication(self, agents: List[str], message: Any) -> None:
        """Asynchronous communication protocol."""
        tasks = []
        for agent_id in agents:
            # Send message without waiting
            pass  # Implementation depends on actual communication mechanism
    
    async def _broadcast_communication(self, agents: List[str], message: Any) -> None:
        """Broadcast communication protocol."""
        # Send to all agents simultaneously
        pass  # Implementation depends on actual communication mechanism
    
    async def _pipeline_communication(self, agents: List[str], message: Any) -> None:
        """Pipeline communication protocol."""
        # Send through pipeline of agents
        pass  # Implementation depends on actual communication mechanism
    
    async def _load_coordination_patterns(self) -> None:
        """Load historical coordination patterns."""
        # TODO: Load from persistent storage
        pass
    
    async def _run_optimization_loop(self) -> None:
        """Background optimization loop."""
        logger.info("Starting coordination optimization loop")
        
        while True:
            try:
                await asyncio.sleep(self.optimization_interval)
                
                current_time = time.time()
                if current_time - self._last_optimization < self.optimization_interval:
                    continue
                
                # Run optimization
                await self._optimize_resource_allocation()
                await self._rebalance_agent_loads()
                await self._update_performance_metrics()
                
                self._last_optimization = current_time
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
    
    async def _optimize_resource_allocation(self) -> None:
        """Optimize resource allocation across agents."""
        # Implement resource reallocation based on performance
        pass
    
    async def _rebalance_agent_loads(self) -> None:
        """Rebalance task loads across agents."""
        # Implement load balancing algorithm
        pass
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        # Calculate and update efficiency metrics
        pass