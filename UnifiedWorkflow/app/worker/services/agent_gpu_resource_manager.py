"""
Agent GPU Resource Manager - Enhanced GPU resource allocation for Agent Abstraction Layer
Manages 3x RTX Titan X GPU assignments, load balancing, and optimization for heterogeneous agent workloads.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

import psutil
import subprocess
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from shared.database.models import (
    AgentConfiguration, 
    GPUResourceAllocation, 
    ModelInstance,
    AgentType, 
    GPUAssignmentStrategy, 
    ModelLoadStrategy
)
from shared.utils.database_setup import get_db_session_factory
from worker.services.gpu_monitor_service import gpu_monitor_service, GPUMetrics

logger = logging.getLogger(__name__)


class AllocationStrategy(str, Enum):
    """GPU allocation strategies for agent assignments."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    MEMORY_OPTIMIZED = "memory_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    AGENT_AFFINITY = "agent_affinity"


class LoadBalancingMode(str, Enum):
    """Load balancing modes for multi-agent scenarios."""
    STATIC = "static"          # Fixed assignments
    DYNAMIC = "dynamic"        # Real-time load balancing
    PREDICTIVE = "predictive"  # ML-based prediction


@dataclass
class GPUAllocationRequest:
    """Request for GPU resource allocation."""
    agent_type: AgentType
    model_name: str
    estimated_memory_mb: float
    priority: int
    max_wait_time_seconds: int = 30
    preferred_gpu_id: Optional[int] = None
    fallback_allowed: bool = True


@dataclass
class GPUAllocationResult:
    """Result of GPU allocation request."""
    success: bool
    allocated_gpu_id: Optional[int]
    allocated_memory_mb: float
    wait_time_seconds: float
    error_message: Optional[str] = None
    alternative_suggestions: List[int] = None


@dataclass
class AgentWorkload:
    """Current workload information for an agent."""
    agent_type: AgentType
    active_requests: int
    total_memory_mb: float
    avg_processing_time_ms: float
    last_activity: datetime


class AgentGPUResourceManager:
    """
    Enhanced GPU resource manager for the Agent Abstraction Layer.
    
    Features:
    - Intelligent allocation across 3x RTX Titan X GPUs
    - Dynamic load balancing and optimization
    - Agent-specific performance monitoring
    - Automatic failover and recovery
    - Memory optimization and sharing
    """
    
    def __init__(self):
        self.db_session_factory = get_db_session_factory()
        self._allocation_lock = asyncio.Lock()
        self._gpu_states: Dict[int, GPUResourceAllocation] = {}
        self._agent_workloads: Dict[AgentType, AgentWorkload] = {}
        self._model_instances: Dict[str, ModelInstance] = {}
        
        # Configuration
        self.gpu_count = 3  # 3x RTX Titan X GPUs
        self.max_memory_utilization = 0.90  # 90% max memory usage
        self.load_balance_interval = 30  # Load balance every 30 seconds
        self.allocation_strategy = AllocationStrategy.LEAST_LOADED
        self.load_balancing_mode = LoadBalancingMode.DYNAMIC
        
        # Performance tracking
        self._allocation_history: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[int, List[GPUMetrics]] = {0: [], 1: [], 2: []}
        
        # Background task
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize GPU resource manager."""
        logger.info("Initializing Agent GPU Resource Manager...")
        
        try:
            # Load GPU states from database
            await self._load_gpu_states()
            
            # Initialize model instances tracking
            await self._load_model_instances()
            
            # Start background monitoring
            await self._start_monitoring()
            
            # Perform initial load balancing
            await self._perform_load_balancing()
            
            logger.info("Agent GPU Resource Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GPU Resource Manager: {e}", exc_info=True)
            raise
    
    async def _load_gpu_states(self):
        """Load GPU allocation states from database."""
        async with self._allocation_lock:
            with self.db_session_factory() as db:
                gpu_allocations = db.query(GPUResourceAllocation).all()
                
                for gpu_alloc in gpu_allocations:
                    self._gpu_states[gpu_alloc.gpu_id] = gpu_alloc
                    
                    # Reset active agent count and allocated memory on startup
                    gpu_alloc.active_agent_count = 0
                    gpu_alloc.allocated_memory_mb = 0.0
                    gpu_alloc.available_memory_mb = gpu_alloc.gpu_memory_total_mb
                    gpu_alloc.last_updated = datetime.now(timezone.utc)
                
                db.commit()
                logger.info(f"Loaded {len(self._gpu_states)} GPU states")
    
    async def _load_model_instances(self):
        """Load model instance tracking from database."""
        with self.db_session_factory() as db:
            instances = db.query(ModelInstance).filter(
                ModelInstance.is_loaded == True
            ).all()
            
            for instance in instances:
                self._model_instances[instance.model_name] = instance
            
            logger.info(f"Loaded {len(self._model_instances)} model instances")
    
    async def _start_monitoring(self):
        """Start background monitoring and optimization."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop for GPU optimization."""
        while True:
            try:
                await asyncio.sleep(self.load_balance_interval)
                
                # Update GPU metrics
                await self._update_gpu_metrics()
                
                # Perform load balancing if needed
                if self.load_balancing_mode == LoadBalancingMode.DYNAMIC:
                    await self._perform_load_balancing()
                
                # Cleanup stale allocations
                await self._cleanup_stale_allocations()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GPU monitoring loop: {e}", exc_info=True)
    
    async def allocate_gpu_for_agent(self, request: GPUAllocationRequest) -> GPUAllocationResult:
        """
        Allocate GPU resources for a specific agent.
        
        Args:
            request: GPU allocation request with agent details
            
        Returns:
            GPU allocation result with assigned GPU and memory
        """
        start_time = datetime.now()
        
        async with self._allocation_lock:
            try:
                # Check if agent has existing allocation
                existing_gpu = await self._get_existing_allocation(request.agent_type)
                if existing_gpu is not None:
                    gpu_state = self._gpu_states[existing_gpu]
                    if self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                        await self._update_allocation(existing_gpu, request)
                        wait_time = (datetime.now() - start_time).total_seconds()
                        return GPUAllocationResult(
                            success=True,
                            allocated_gpu_id=existing_gpu,
                            allocated_memory_mb=request.estimated_memory_mb,
                            wait_time_seconds=wait_time
                        )
                
                # Find best GPU for allocation
                best_gpu = await self._find_best_gpu(request)
                if best_gpu is None:
                    return GPUAllocationResult(
                        success=False,
                        allocated_gpu_id=None,
                        allocated_memory_mb=0.0,
                        wait_time_seconds=0.0,
                        error_message="No suitable GPU available",
                        alternative_suggestions=await self._get_alternative_suggestions(request)
                    )
                
                # Allocate GPU resources
                await self._update_allocation(best_gpu, request)
                
                wait_time = (datetime.now() - start_time).total_seconds()
                
                # Record allocation history
                self._allocation_history.append({
                    "timestamp": start_time.isoformat(),
                    "agent_type": request.agent_type.value,
                    "allocated_gpu": best_gpu,
                    "memory_mb": request.estimated_memory_mb,
                    "wait_time_seconds": wait_time
                })
                
                logger.info(f"Allocated GPU {best_gpu} for {request.agent_type} ({request.estimated_memory_mb:.1f}MB)")
                
                return GPUAllocationResult(
                    success=True,
                    allocated_gpu_id=best_gpu,
                    allocated_memory_mb=request.estimated_memory_mb,
                    wait_time_seconds=wait_time
                )
                
            except Exception as e:
                wait_time = (datetime.now() - start_time).total_seconds()
                logger.error(f"GPU allocation failed for {request.agent_type}: {e}")
                
                return GPUAllocationResult(
                    success=False,
                    allocated_gpu_id=None,
                    allocated_memory_mb=0.0,
                    wait_time_seconds=wait_time,
                    error_message=str(e)
                )
    
    async def _get_existing_allocation(self, agent_type: AgentType) -> Optional[int]:
        """Check if agent already has GPU allocation."""
        with self.db_session_factory() as db:
            config = db.query(AgentConfiguration).filter(
                and_(
                    AgentConfiguration.agent_type == agent_type,
                    AgentConfiguration.is_active == True,
                    AgentConfiguration.gpu_assignment.isnot(None)
                )
            ).first()
            
            return config.gpu_assignment if config else None
    
    def _can_accommodate_request(self, gpu_state: GPUResourceAllocation, memory_mb: float) -> bool:
        """Check if GPU can accommodate the memory request."""
        required_memory = gpu_state.allocated_memory_mb + memory_mb
        max_memory = gpu_state.gpu_memory_total_mb * self.max_memory_utilization
        return required_memory <= max_memory
    
    async def _find_best_gpu(self, request: GPUAllocationRequest) -> Optional[int]:
        """Find the best GPU for allocation based on strategy."""
        if request.preferred_gpu_id is not None:
            gpu_state = self._gpu_states.get(request.preferred_gpu_id)
            if gpu_state and gpu_state.is_available and not gpu_state.maintenance_mode:
                if self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                    return request.preferred_gpu_id
        
        # Apply allocation strategy
        if self.allocation_strategy == AllocationStrategy.LEAST_LOADED:
            return await self._find_least_loaded_gpu(request)
        elif self.allocation_strategy == AllocationStrategy.MEMORY_OPTIMIZED:
            return await self._find_memory_optimized_gpu(request)
        elif self.allocation_strategy == AllocationStrategy.PERFORMANCE_OPTIMIZED:
            return await self._find_performance_optimized_gpu(request)
        elif self.allocation_strategy == AllocationStrategy.ROUND_ROBIN:
            return await self._find_round_robin_gpu(request)
        else:
            return await self._find_least_loaded_gpu(request)
    
    async def _find_least_loaded_gpu(self, request: GPUAllocationRequest) -> Optional[int]:
        """Find GPU with least current load."""
        best_gpu = None
        best_score = float('inf')
        
        for gpu_id, gpu_state in self._gpu_states.items():
            if not gpu_state.is_available or gpu_state.maintenance_mode:
                continue
            
            if not self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                continue
            
            # Calculate load score (lower is better)
            memory_ratio = gpu_state.allocated_memory_mb / gpu_state.gpu_memory_total_mb
            agent_count_weight = gpu_state.active_agent_count * 0.1
            utilization_weight = (gpu_state.utilization_percent or 0) * 0.01
            
            load_score = memory_ratio + agent_count_weight + utilization_weight
            
            if load_score < best_score:
                best_score = load_score
                best_gpu = gpu_id
        
        return best_gpu
    
    async def _find_memory_optimized_gpu(self, request: GPUAllocationRequest) -> Optional[int]:
        """Find GPU with best memory fit."""
        best_gpu = None
        best_fit_score = float('inf')
        
        for gpu_id, gpu_state in self._gpu_states.items():
            if not gpu_state.is_available or gpu_state.maintenance_mode:
                continue
            
            if not self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                continue
            
            # Calculate memory fit score (how well the request fits available memory)
            available_memory = gpu_state.available_memory_mb
            fit_score = abs(available_memory - request.estimated_memory_mb)
            
            if fit_score < best_fit_score:
                best_fit_score = fit_score
                best_gpu = gpu_id
        
        return best_gpu
    
    async def _find_performance_optimized_gpu(self, request: GPUAllocationRequest) -> Optional[int]:
        """Find GPU with best performance characteristics."""
        best_gpu = None
        best_performance = 0.0
        
        for gpu_id, gpu_state in self._gpu_states.items():
            if not gpu_state.is_available or gpu_state.maintenance_mode:
                continue
            
            if not self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                continue
            
            # Calculate performance score based on temperature and utilization
            temp_score = max(0, 100 - (gpu_state.temperature_celsius or 70)) / 100
            util_score = max(0, 100 - (gpu_state.utilization_percent or 50)) / 100
            performance_score = (temp_score + util_score) / 2
            
            if performance_score > best_performance:
                best_performance = performance_score
                best_gpu = gpu_id
        
        return best_gpu
    
    async def _find_round_robin_gpu(self, request: GPUAllocationRequest) -> Optional[int]:
        """Find GPU using round-robin allocation."""
        # Simple round-robin based on total allocations
        allocation_counts = {gpu_id: state.active_agent_count for gpu_id, state in self._gpu_states.items()}
        
        for gpu_id in sorted(allocation_counts.keys()):
            gpu_state = self._gpu_states[gpu_id]
            if gpu_state.is_available and not gpu_state.maintenance_mode:
                if self._can_accommodate_request(gpu_state, request.estimated_memory_mb):
                    return gpu_id
        
        return None
    
    async def _update_allocation(self, gpu_id: int, request: GPUAllocationRequest):
        """Update GPU allocation state."""
        gpu_state = self._gpu_states[gpu_id]
        
        with self.db_session_factory() as db:
            # Update GPU state
            gpu_alloc = db.query(GPUResourceAllocation).filter(
                GPUResourceAllocation.gpu_id == gpu_id
            ).first()
            
            if gpu_alloc:
                gpu_alloc.allocated_memory_mb += request.estimated_memory_mb
                gpu_alloc.available_memory_mb = gpu_alloc.gpu_memory_total_mb - gpu_alloc.allocated_memory_mb
                gpu_alloc.active_agent_count += 1
                gpu_alloc.last_updated = datetime.now(timezone.utc)
                
                # Update local state
                self._gpu_states[gpu_id] = gpu_alloc
                
                # Update agent configuration with GPU assignment
                agent_config = db.query(AgentConfiguration).filter(
                    AgentConfiguration.agent_type == request.agent_type
                ).first()
                
                if agent_config:
                    agent_config.gpu_assignment = gpu_id
                    agent_config.updated_at = datetime.now(timezone.utc)
                
                db.commit()
    
    async def release_gpu_for_agent(self, agent_type: AgentType, memory_mb: float) -> bool:
        """Release GPU resources for an agent."""
        async with self._allocation_lock:
            try:
                with self.db_session_factory() as db:
                    # Find agent's current GPU assignment
                    config = db.query(AgentConfiguration).filter(
                        AgentConfiguration.agent_type == agent_type
                    ).first()
                    
                    if not config or config.gpu_assignment is None:
                        return True  # Nothing to release
                    
                    gpu_id = config.gpu_assignment
                    
                    # Update GPU allocation
                    gpu_alloc = db.query(GPUResourceAllocation).filter(
                        GPUResourceAllocation.gpu_id == gpu_id
                    ).first()
                    
                    if gpu_alloc:
                        gpu_alloc.allocated_memory_mb = max(0, gpu_alloc.allocated_memory_mb - memory_mb)
                        gpu_alloc.available_memory_mb = gpu_alloc.gpu_memory_total_mb - gpu_alloc.allocated_memory_mb
                        gpu_alloc.active_agent_count = max(0, gpu_alloc.active_agent_count - 1)
                        gpu_alloc.last_updated = datetime.now(timezone.utc)
                        
                        # Update local state
                        self._gpu_states[gpu_id] = gpu_alloc
                        
                        db.commit()
                        
                        logger.info(f"Released GPU {gpu_id} resources for {agent_type} ({memory_mb:.1f}MB)")
                        return True
                
            except Exception as e:
                logger.error(f"Failed to release GPU resources for {agent_type}: {e}")
                return False
        
        return False
    
    async def _update_gpu_metrics(self):
        """Update GPU performance metrics."""
        try:
            current_metrics = await gpu_monitor_service.get_current_metrics()
            if current_metrics:
                gpu_id = current_metrics.gpu_id
                self._performance_metrics[gpu_id].append(current_metrics)
                
                # Keep only recent metrics (last hour)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                self._performance_metrics[gpu_id] = [
                    m for m in self._performance_metrics[gpu_id]
                    if m.timestamp > cutoff_time
                ]
                
                # Update database GPU state
                with self.db_session_factory() as db:
                    gpu_alloc = db.query(GPUResourceAllocation).filter(
                        GPUResourceAllocation.gpu_id == gpu_id
                    ).first()
                    
                    if gpu_alloc:
                        gpu_alloc.utilization_percent = current_metrics.gpu_utilization_percent
                        gpu_alloc.temperature_celsius = current_metrics.temperature_celsius
                        gpu_alloc.power_draw_watts = current_metrics.power_draw_watts
                        gpu_alloc.last_updated = datetime.now(timezone.utc)
                        
                        self._gpu_states[gpu_id] = gpu_alloc
                        db.commit()
        
        except Exception as e:
            logger.debug(f"Error updating GPU metrics: {e}")
    
    async def _perform_load_balancing(self):
        """Perform load balancing across GPUs."""
        try:
            # Calculate load distribution
            load_distribution = {}
            for gpu_id, state in self._gpu_states.items():
                memory_usage = state.allocated_memory_mb / state.gpu_memory_total_mb
                agent_count = state.active_agent_count
                utilization = state.utilization_percent or 0
                
                load_distribution[gpu_id] = {
                    "memory_usage": memory_usage,
                    "agent_count": agent_count,
                    "utilization": utilization,
                    "total_load": memory_usage * 0.5 + (agent_count * 0.1) + (utilization * 0.01)
                }
            
            # Check if rebalancing is needed
            loads = [info["total_load"] for info in load_distribution.values()]
            if len(loads) > 1:
                load_variance = max(loads) - min(loads)
                
                if load_variance > 0.3:  # Significant imbalance
                    logger.info(f"GPU load imbalance detected (variance: {load_variance:.2f}), considering rebalancing")
                    # TODO: Implement intelligent agent migration logic
        
        except Exception as e:
            logger.error(f"Error in load balancing: {e}")
    
    async def _cleanup_stale_allocations(self):
        """Clean up stale GPU allocations."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            # TODO: Implement cleanup logic for stale allocations
            # This would involve checking for agents that haven't been active
            # and cleaning up their GPU allocations
            
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
    
    async def _get_alternative_suggestions(self, request: GPUAllocationRequest) -> List[int]:
        """Get alternative GPU suggestions when allocation fails."""
        suggestions = []
        
        for gpu_id, state in self._gpu_states.items():
            if state.is_available and not state.maintenance_mode:
                # Calculate how much memory would need to be freed
                required_memory = state.allocated_memory_mb + request.estimated_memory_mb
                max_memory = state.gpu_memory_total_mb * self.max_memory_utilization
                
                if required_memory <= state.gpu_memory_total_mb:  # Possible with cleanup
                    suggestions.append(gpu_id)
        
        return suggestions
    
    async def get_gpu_status(self) -> Dict[str, Any]:
        """Get comprehensive GPU resource status."""
        return {
            "gpu_states": {
                gpu_id: {
                    "gpu_name": state.gpu_name,
                    "memory_total_mb": state.gpu_memory_total_mb,
                    "memory_allocated_mb": state.allocated_memory_mb,
                    "memory_available_mb": state.available_memory_mb,
                    "memory_usage_percent": (state.allocated_memory_mb / state.gpu_memory_total_mb) * 100,
                    "active_agents": state.active_agent_count,
                    "utilization_percent": state.utilization_percent,
                    "temperature_celsius": state.temperature_celsius,
                    "is_available": state.is_available,
                    "maintenance_mode": state.maintenance_mode,
                    "last_updated": state.last_updated.isoformat()
                } for gpu_id, state in self._gpu_states.items()
            },
            "allocation_strategy": self.allocation_strategy.value,
            "load_balancing_mode": self.load_balancing_mode.value,
            "recent_allocations": self._allocation_history[-20:],  # Last 20 allocations
            "performance_summary": {
                gpu_id: {
                    "recent_metrics_count": len(metrics),
                    "avg_utilization": sum(m.gpu_utilization_percent for m in metrics) / len(metrics) if metrics else 0,
                    "avg_temperature": sum(m.temperature_celsius for m in metrics) / len(metrics) if metrics else 0
                } for gpu_id, metrics in self._performance_metrics.items()
            }
        }
    
    async def optimize_allocations(self) -> Dict[str, Any]:
        """Perform optimization of current GPU allocations."""
        optimization_results = {
            "actions_taken": [],
            "recommendations": [],
            "performance_improvement": 0.0
        }
        
        try:
            # Analyze current allocation efficiency
            total_memory_used = sum(state.allocated_memory_mb for state in self._gpu_states.values())
            total_memory_available = sum(state.gpu_memory_total_mb for state in self._gpu_states.values())
            current_efficiency = total_memory_used / total_memory_available
            
            # Generate optimization recommendations
            for gpu_id, state in self._gpu_states.items():
                memory_usage = state.allocated_memory_mb / state.gpu_memory_total_mb
                
                if memory_usage > 0.95:
                    optimization_results["recommendations"].append(
                        f"GPU {gpu_id} memory usage critical ({memory_usage*100:.1f}%) - consider load balancing"
                    )
                elif memory_usage < 0.1 and state.active_agent_count > 0:
                    optimization_results["recommendations"].append(
                        f"GPU {gpu_id} underutilized ({memory_usage*100:.1f}%) - consider consolidation"
                    )
            
            optimization_results["current_efficiency"] = current_efficiency
            
        except Exception as e:
            logger.error(f"Error in allocation optimization: {e}")
            optimization_results["error"] = str(e)
        
        return optimization_results


# Global instance
agent_gpu_resource_manager = AgentGPUResourceManager()