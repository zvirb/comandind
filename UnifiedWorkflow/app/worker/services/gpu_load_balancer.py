"""
GPU Load Balancer - Multi-GPU Resource Distribution
Implements intelligent load balancing across multiple GPU devices for optimal resource utilization.
"""

import asyncio
import logging
import subprocess
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from worker.services.model_resource_manager import ModelCategory, model_resource_manager

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for GPU resource distribution."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    MEMORY_BASED = "memory_based"
    PERFORMANCE_BASED = "performance_based"
    AFFINITY_BASED = "affinity_based"


@dataclass
class GPUDevice:
    """Information about a GPU device."""
    device_id: int
    name: str
    memory_total_mb: float
    memory_used_mb: float = 0.0
    memory_free_mb: float = 0.0
    utilization_percent: float = 0.0
    temperature_celsius: float = 0.0
    power_usage_watts: float = 0.0
    active_models: List[str] = field(default_factory=list)
    active_requests: int = 0
    total_requests_processed: int = 0
    average_processing_time: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_available: bool = True


@dataclass
class LoadBalancingDecision:
    """Result of load balancing decision."""
    selected_gpu: int
    strategy_used: LoadBalancingStrategy
    decision_reason: str
    gpu_allocation: Dict[int, float]  # GPU ID -> load factor
    estimated_wait_time: float = 0.0
    confidence_score: float = 1.0


class GPULoadBalancer:
    """
    Multi-GPU load balancer for intelligent resource distribution.
    Monitors GPU health, memory usage, and performance to optimize allocation.
    """
    
    def __init__(self):
        self.gpu_devices: Dict[int, GPUDevice] = {}
        self.current_strategy = LoadBalancingStrategy.MEMORY_BASED
        self.monitoring_interval = 5.0  # Update GPU info every 5 seconds
        self.model_gpu_affinity: Dict[str, int] = {}  # Model -> preferred GPU mapping
        self.request_history: List[Dict[str, Any]] = []
        
        # Load balancing weights and thresholds
        self.memory_weight = 0.4
        self.utilization_weight = 0.3
        self.performance_weight = 0.2
        self.affinity_weight = 0.1
        
        # Monitoring and management tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._balancer_lock = asyncio.Lock()
        
        # Performance optimization settings
        self.enable_dynamic_strategy = True
        self.enable_affinity_learning = True
        self.max_memory_threshold = 0.85  # 85% memory usage threshold
        self.max_utilization_threshold = 0.90  # 90% utilization threshold
    
    async def start_monitoring(self):
        """Start GPU monitoring and load balancing."""
        if self._monitoring_task is None or self._monitoring_task.done():
            await self.discover_gpus()
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started GPU load balancing monitoring")
    
    async def stop_monitoring(self):
        """Stop GPU monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped GPU load balancing monitoring")
    
    async def discover_gpus(self):
        """Discover available GPU devices."""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=index,name,memory.total', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        index, name, memory_total = line.split(', ')
                        gpu_id = int(index)
                        
                        self.gpu_devices[gpu_id] = GPUDevice(
                            device_id=gpu_id,
                            name=name.strip(),
                            memory_total_mb=float(memory_total)
                        )
                        
                        logger.info(f"Discovered GPU {gpu_id}: {name} with {memory_total}MB memory")
                
                if not self.gpu_devices:
                    logger.warning("No GPU devices discovered")
                else:
                    logger.info(f"Total GPUs discovered: {len(self.gpu_devices)}")
            else:
                logger.error(f"Failed to discover GPUs: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error discovering GPUs: {e}")
            # Create a fallback single GPU entry
            self.gpu_devices[0] = GPUDevice(
                device_id=0,
                name="Unknown GPU",
                memory_total_mb=24000.0  # Assume 24GB as default
            )
    
    async def _monitoring_loop(self):
        """Main monitoring loop for GPU status updates."""
        while True:
            try:
                await self.update_gpu_status()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GPU monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.monitoring_interval)
    
    async def update_gpu_status(self):
        """Update status for all GPU devices."""
        try:
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=index,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 6:
                            gpu_id = int(parts[0])
                            memory_used = float(parts[1]) if parts[1] != '[Not Supported]' else 0.0
                            memory_free = float(parts[2]) if parts[2] != '[Not Supported]' else 0.0
                            utilization = float(parts[3]) if parts[3] != '[Not Supported]' else 0.0
                            temperature = float(parts[4]) if parts[4] != '[Not Supported]' else 0.0
                            power = float(parts[5]) if parts[5] != '[Not Supported]' else 0.0
                            
                            if gpu_id in self.gpu_devices:
                                gpu = self.gpu_devices[gpu_id]
                                gpu.memory_used_mb = memory_used
                                gpu.memory_free_mb = memory_free
                                gpu.utilization_percent = utilization
                                gpu.temperature_celsius = temperature
                                gpu.power_usage_watts = power
                                gpu.last_updated = datetime.now(timezone.utc)
                                
                                # Check if GPU is available based on thresholds
                                memory_usage_ratio = memory_used / gpu.memory_total_mb
                                gpu.is_available = (
                                    memory_usage_ratio < self.max_memory_threshold and
                                    utilization < self.max_utilization_threshold * 100 and
                                    temperature < 85.0  # Temperature threshold in Celsius
                                )
                
                logger.debug(f"Updated status for {len(self.gpu_devices)} GPUs")
                
        except Exception as e:
            logger.warning(f"Failed to update GPU status: {e}")
    
    async def select_optimal_gpu(
        self, 
        model_name: str, 
        complexity: Any,  # Import locally to avoid circular dependency
        strategy: Optional[LoadBalancingStrategy] = None
    ) -> LoadBalancingDecision:
        """
        Select the optimal GPU for a given model and complexity.
        
        Args:
            model_name: Name of the model to allocate
            complexity: Complexity level of the request
            strategy: Load balancing strategy to use (optional)
            
        Returns:
            LoadBalancingDecision with allocation details
        """
        async with self._balancer_lock:
            if not self.gpu_devices:
                await self.discover_gpus()
            
            if not self.gpu_devices:
                raise Exception("No GPU devices available")
            
            # Use specified strategy or current default
            selected_strategy = strategy or self.current_strategy
            
            # Get model information for memory requirements
            model_info = model_resource_manager.get_model_info(model_name)
            required_memory_gb = model_info.estimated_memory_gb if model_info else 8.0
            required_memory_mb = required_memory_gb * 1024
            
            # Filter available GPUs that can handle the request
            available_gpus = [
                gpu for gpu in self.gpu_devices.values()
                if gpu.is_available and gpu.memory_free_mb >= required_memory_mb
            ]
            
            if not available_gpus:
                # Fall back to least loaded GPU even if it exceeds thresholds
                available_gpus = list(self.gpu_devices.values())
                if not available_gpus:
                    raise Exception("No GPUs available for allocation")
            
            # Apply load balancing strategy
            if selected_strategy == LoadBalancingStrategy.ROUND_ROBIN:
                decision = await self._round_robin_selection(available_gpus, model_name)
            elif selected_strategy == LoadBalancingStrategy.LEAST_LOADED:
                decision = await self._least_loaded_selection(available_gpus, model_name, required_memory_mb)
            elif selected_strategy == LoadBalancingStrategy.MEMORY_BASED:
                decision = await self._memory_based_selection(available_gpus, model_name, required_memory_mb)
            elif selected_strategy == LoadBalancingStrategy.PERFORMANCE_BASED:
                decision = await self._performance_based_selection(available_gpus, model_name, complexity)
            elif selected_strategy == LoadBalancingStrategy.AFFINITY_BASED:
                decision = await self._affinity_based_selection(available_gpus, model_name, required_memory_mb)
            else:
                # Default to memory-based
                decision = await self._memory_based_selection(available_gpus, model_name, required_memory_mb)
            
            # Record the decision for learning and optimization
            await self._record_allocation_decision(decision, model_name, complexity)
            
            return decision
    
    async def _round_robin_selection(self, available_gpus: List[GPUDevice], model_name: str) -> LoadBalancingDecision:
        """Round-robin GPU selection."""
        # Simple round-robin based on total requests processed
        min_requests = min(gpu.total_requests_processed for gpu in available_gpus)
        selected_gpu = next(gpu for gpu in available_gpus if gpu.total_requests_processed == min_requests)
        
        return LoadBalancingDecision(
            selected_gpu=selected_gpu.device_id,
            strategy_used=LoadBalancingStrategy.ROUND_ROBIN,
            decision_reason=f"Round-robin selection: GPU {selected_gpu.device_id} has fewest requests ({min_requests})",
            gpu_allocation={gpu.device_id: gpu.total_requests_processed / max(1, max(g.total_requests_processed for g in available_gpus)) for gpu in available_gpus},
            confidence_score=0.7
        )
    
    async def _least_loaded_selection(self, available_gpus: List[GPUDevice], model_name: str, required_memory_mb: float) -> LoadBalancingDecision:
        """Select GPU with least current load."""
        # Calculate load score based on active requests and utilization
        gpu_loads = {}
        for gpu in available_gpus:
            load_score = (
                gpu.active_requests * 0.5 +
                (gpu.utilization_percent / 100.0) * 0.3 +
                (gpu.memory_used_mb / gpu.memory_total_mb) * 0.2
            )
            gpu_loads[gpu.device_id] = load_score
        
        # Select GPU with minimum load
        min_load_gpu_id = min(gpu_loads, key=gpu_loads.get)
        selected_gpu = self.gpu_devices[min_load_gpu_id]
        
        return LoadBalancingDecision(
            selected_gpu=min_load_gpu_id,
            strategy_used=LoadBalancingStrategy.LEAST_LOADED,
            decision_reason=f"Least loaded: GPU {min_load_gpu_id} has load score {gpu_loads[min_load_gpu_id]:.3f}",
            gpu_allocation=gpu_loads,
            confidence_score=0.8
        )
    
    async def _memory_based_selection(self, available_gpus: List[GPUDevice], model_name: str, required_memory_mb: float) -> LoadBalancingDecision:
        """Select GPU based on memory availability."""
        # Calculate memory efficiency score
        memory_scores = {}
        for gpu in available_gpus:
            # Prefer GPUs with enough free memory but not excessive overhead
            memory_utilization = gpu.memory_used_mb / gpu.memory_total_mb
            free_memory_ratio = gpu.memory_free_mb / gpu.memory_total_mb
            
            # Score favors GPUs with good free memory but not completely empty
            if gpu.memory_free_mb >= required_memory_mb:
                memory_score = free_memory_ratio * (1 - abs(free_memory_ratio - 0.3))  # Prefer ~70% utilized
            else:
                memory_score = 0.0  # Insufficient memory
            
            memory_scores[gpu.device_id] = memory_score
        
        # Select GPU with best memory score
        if not any(score > 0 for score in memory_scores.values()):
            # No GPU has sufficient memory, pick the one with most free memory
            max_free_gpu = max(available_gpus, key=lambda g: g.memory_free_mb)
            selected_gpu_id = max_free_gpu.device_id
            confidence = 0.3  # Low confidence due to insufficient memory
        else:
            selected_gpu_id = max(memory_scores, key=memory_scores.get)
            confidence = 0.9
        
        return LoadBalancingDecision(
            selected_gpu=selected_gpu_id,
            strategy_used=LoadBalancingStrategy.MEMORY_BASED,
            decision_reason=f"Memory-based: GPU {selected_gpu_id} selected for optimal memory utilization",
            gpu_allocation=memory_scores,
            confidence_score=confidence
        )
    
    async def _performance_based_selection(self, available_gpus: List[GPUDevice], model_name: str, complexity: Any) -> LoadBalancingDecision:
        """Select GPU based on historical performance."""
        # Calculate performance scores based on average processing time and GPU specs
        performance_scores = {}
        for gpu in available_gpus:
            # Base score on inverse of average processing time (faster is better)
            if gpu.average_processing_time > 0:
                time_score = 1.0 / (1.0 + gpu.average_processing_time)
            else:
                time_score = 1.0  # No history, assume good performance
            
            # Factor in current utilization (prefer less utilized GPUs)
            utilization_penalty = gpu.utilization_percent / 100.0
            
            # Combine scores
            performance_score = time_score * (1.0 - utilization_penalty * 0.5)
            performance_scores[gpu.device_id] = performance_score
        
        # Select GPU with best performance score
        best_gpu_id = max(performance_scores, key=performance_scores.get)
        
        return LoadBalancingDecision(
            selected_gpu=best_gpu_id,
            strategy_used=LoadBalancingStrategy.PERFORMANCE_BASED,
            decision_reason=f"Performance-based: GPU {best_gpu_id} selected for best historical performance",
            gpu_allocation=performance_scores,
            confidence_score=0.85
        )
    
    async def _affinity_based_selection(self, available_gpus: List[GPUDevice], model_name: str, required_memory_mb: float) -> LoadBalancingDecision:
        """Select GPU based on model affinity (models already loaded)."""
        # Check if model is already loaded on any GPU
        affinity_scores = {}
        for gpu in available_gpus:
            score = 0.0
            
            # High score if model is already loaded on this GPU
            if model_name in gpu.active_models:
                score += 1.0
                
            # Medium score if similar models are loaded (same category)
            model_info = model_resource_manager.get_model_info(model_name)
            if model_info:
                for loaded_model in gpu.active_models:
                    loaded_model_info = model_resource_manager.get_model_info(loaded_model)
                    if loaded_model_info and loaded_model_info.category == model_info.category:
                        score += 0.3
            
            # Factor in memory availability
            if gpu.memory_free_mb >= required_memory_mb:
                score += 0.5
            
            affinity_scores[gpu.device_id] = score
        
        # Select GPU with best affinity score, fallback to memory-based if no affinity
        if max(affinity_scores.values()) > 0:
            selected_gpu_id = max(affinity_scores, key=affinity_scores.get)
            confidence = 0.9
            reason = f"Affinity-based: GPU {selected_gpu_id} selected for model affinity"
        else:
            # No affinity found, fall back to memory-based selection
            return await self._memory_based_selection(available_gpus, model_name, required_memory_mb)
        
        return LoadBalancingDecision(
            selected_gpu=selected_gpu_id,
            strategy_used=LoadBalancingStrategy.AFFINITY_BASED,
            decision_reason=reason,
            gpu_allocation=affinity_scores,
            confidence_score=confidence
        )
    
    async def _record_allocation_decision(self, decision: LoadBalancingDecision, model_name: str, complexity: Any):
        """Record allocation decision for learning and optimization."""
        allocation_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gpu_id": decision.selected_gpu,
            "model_name": model_name,
            "complexity": complexity.value,
            "strategy": decision.strategy_used.value,
            "confidence": decision.confidence_score
        }
        
        self.request_history.append(allocation_record)
        
        # Limit history size
        if len(self.request_history) > 1000:
            self.request_history = self.request_history[-500:]
        
        # Update model affinity learning
        if self.enable_affinity_learning:
            self.model_gpu_affinity[model_name] = decision.selected_gpu
    
    async def allocate_request(self, gpu_id: int, model_name: str, request_id: str):
        """Allocate a request to a specific GPU."""
        if gpu_id in self.gpu_devices:
            gpu = self.gpu_devices[gpu_id]
            gpu.active_requests += 1
            gpu.total_requests_processed += 1
            
            if model_name not in gpu.active_models:
                gpu.active_models.append(model_name)
            
            logger.debug(f"Allocated request {request_id} to GPU {gpu_id} for model {model_name}")
    
    async def deallocate_request(self, gpu_id: int, model_name: str, request_id: str, processing_time: float):
        """Deallocate a request from a GPU and update performance metrics."""
        if gpu_id in self.gpu_devices:
            gpu = self.gpu_devices[gpu_id]
            gpu.active_requests = max(0, gpu.active_requests - 1)
            
            # Update average processing time
            if gpu.average_processing_time == 0:
                gpu.average_processing_time = processing_time
            else:
                # Exponential moving average
                alpha = 0.1
                gpu.average_processing_time = (
                    alpha * processing_time + (1 - alpha) * gpu.average_processing_time
                )
            
            # Remove model from active models if no more requests
            if gpu.active_requests == 0 and model_name in gpu.active_models:
                gpu.active_models.remove(model_name)
            
            logger.debug(f"Deallocated request {request_id} from GPU {gpu_id}, processing time: {processing_time:.2f}s")
    
    async def get_load_balancer_status(self) -> Dict[str, Any]:
        """Get comprehensive load balancer status."""
        return {
            "strategy": self.current_strategy.value,
            "total_gpus": len(self.gpu_devices),
            "available_gpus": sum(1 for gpu in self.gpu_devices.values() if gpu.is_available),
            "gpu_details": {
                gpu_id: {
                    "name": gpu.name,
                    "memory_total_mb": gpu.memory_total_mb,
                    "memory_used_mb": gpu.memory_used_mb,
                    "memory_free_mb": gpu.memory_free_mb,
                    "utilization_percent": gpu.utilization_percent,
                    "temperature_celsius": gpu.temperature_celsius,
                    "active_models": gpu.active_models,
                    "active_requests": gpu.active_requests,
                    "total_requests_processed": gpu.total_requests_processed,
                    "average_processing_time": gpu.average_processing_time,
                    "is_available": gpu.is_available,
                    "last_updated": gpu.last_updated.isoformat()
                }
                for gpu_id, gpu in self.gpu_devices.items()
            },
            "model_affinity": self.model_gpu_affinity,
            "recent_allocations": len(self.request_history),
            "monitoring_active": self._monitoring_task is not None and not self._monitoring_task.done(),
            "settings": {
                "memory_weight": self.memory_weight,
                "utilization_weight": self.utilization_weight,
                "performance_weight": self.performance_weight,
                "affinity_weight": self.affinity_weight,
                "max_memory_threshold": self.max_memory_threshold,
                "max_utilization_threshold": self.max_utilization_threshold,
                "enable_dynamic_strategy": self.enable_dynamic_strategy,
                "enable_affinity_learning": self.enable_affinity_learning
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def optimize_strategy(self):
        """Dynamically optimize load balancing strategy based on performance."""
        if not self.enable_dynamic_strategy or len(self.request_history) < 20:
            return
        
        # Analyze recent performance by strategy
        recent_history = self.request_history[-50:]  # Last 50 requests
        strategy_performance = {}
        
        for record in recent_history:
            strategy = record["strategy"]
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {"count": 0, "avg_confidence": 0.0}
            
            strategy_performance[strategy]["count"] += 1
            strategy_performance[strategy]["avg_confidence"] += record["confidence"]
        
        # Calculate average confidence for each strategy
        for strategy_data in strategy_performance.values():
            if strategy_data["count"] > 0:
                strategy_data["avg_confidence"] /= strategy_data["count"]
        
        # Find best performing strategy
        if strategy_performance:
            best_strategy = max(
                strategy_performance, 
                key=lambda s: strategy_performance[s]["avg_confidence"]
            )
            
            # Switch strategy if significantly better
            if (strategy_performance[best_strategy]["avg_confidence"] > 0.8 and
                best_strategy != self.current_strategy.value):
                old_strategy = self.current_strategy
                self.current_strategy = LoadBalancingStrategy(best_strategy)
                logger.info(f"Optimized load balancing strategy from {old_strategy.value} to {best_strategy}")


# Global instance
gpu_load_balancer = GPULoadBalancer()