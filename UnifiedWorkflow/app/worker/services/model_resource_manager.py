"""
Model Resource Manager - Parallel processing architecture with GPU constraint management
Implements parameter-based model categorization and parallel execution limits based on model parameters.
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import subprocess
import json

logger = logging.getLogger(__name__)


class ModelCategory(str, Enum):
    """Model categories based on parameter count for resource management."""
    SMALL_1B = "1b"        # ~1 billion parameters
    MEDIUM_4B = "4b"       # ~4 billion parameters  
    LARGE_8B = "8b"        # ~8 billion parameters
    XLARGE_10B = "10b+"    # 10+ billion parameters


@dataclass
class ModelInfo:
    """Information about a model including resource requirements."""
    name: str
    category: ModelCategory
    parameter_count: int
    estimated_memory_gb: float
    is_loaded: bool = False
    load_time: Optional[datetime] = None
    last_used: Optional[datetime] = None


@dataclass
class ParallelExecutionLimits:
    """Parallel execution limits based on model categories."""
    small_1b_limit: int = 5     # 5 models at 1B parameters simultaneously
    medium_4b_limit: int = 4    # 4 models at 4B parameters simultaneously
    large_8b_limit: int = 3     # 3 models at 8B parameters simultaneously
    xlarge_10b_limit: int = 1   # Only one at a time for 10+ billion parameters


@dataclass
class ResourceStatus:
    """Current resource utilization status."""
    loaded_models: Dict[str, ModelInfo] = field(default_factory=dict)
    active_executions: Dict[ModelCategory, int] = field(default_factory=lambda: {
        ModelCategory.SMALL_1B: 0,
        ModelCategory.MEDIUM_4B: 0,
        ModelCategory.LARGE_8B: 0,
        ModelCategory.XLARGE_10B: 0
    })
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    pending_requests: List[Tuple[str, str]] = field(default_factory=list)  # (expert_id, model_name)


class ModelResourceManager:
    """
    Manages model loading, GPU resources, and parallel execution constraints.
    Ensures efficient resource utilization and prevents GPU memory exhaustion.
    """
    
    def __init__(self):
        self.limits = ParallelExecutionLimits()
        self.status = ResourceStatus()
        self.model_registry = self._initialize_model_registry()
        self._execution_lock = asyncio.Lock()
        self._model_loading_locks: Dict[str, asyncio.Lock] = {}
        
    def _initialize_model_registry(self) -> Dict[str, ModelInfo]:
        """Initialize the registry of known models with their parameter counts."""
        return {
            # 1B parameter models
            "llama3.2:1b": ModelInfo("llama3.2:1b", ModelCategory.SMALL_1B, 1000000000, 2.0),
            "qwen2.5:1.5b": ModelInfo("qwen2.5:1.5b", ModelCategory.SMALL_1B, 1500000000, 3.0),
            
            # 3-4B parameter models
            "llama3.2:3b": ModelInfo("llama3.2:3b", ModelCategory.MEDIUM_4B, 3000000000, 6.0),
            "phi3:3.8b": ModelInfo("phi3:3.8b", ModelCategory.MEDIUM_4B, 3800000000, 7.5),
            "qwen2.5:3b": ModelInfo("qwen2.5:3b", ModelCategory.MEDIUM_4B, 3000000000, 6.0),
            
            # 7-8B parameter models
            "llama3.1:8b": ModelInfo("llama3.1:8b", ModelCategory.LARGE_8B, 8000000000, 16.0),
            "mistral:7b": ModelInfo("mistral:7b", ModelCategory.LARGE_8B, 7000000000, 14.0),
            "qwen2.5:7b": ModelInfo("qwen2.5:7b", ModelCategory.LARGE_8B, 7000000000, 14.0),
            "gemma2:9b": ModelInfo("gemma2:9b", ModelCategory.LARGE_8B, 9000000000, 18.0),
            
            # 10B+ parameter models
            "llama3.1:70b": ModelInfo("llama3.1:70b", ModelCategory.XLARGE_10B, 70000000000, 140.0),
            "qwen2.5:14b": ModelInfo("qwen2.5:14b", ModelCategory.XLARGE_10B, 14000000000, 28.0),
            "qwen2.5:32b": ModelInfo("qwen2.5:32b", ModelCategory.XLARGE_10B, 32000000000, 64.0),
            "llama3.1:405b": ModelInfo("llama3.1:405b", ModelCategory.XLARGE_10B, 405000000000, 810.0),
        }
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get model information, inferring category if not in registry."""
        if model_name in self.model_registry:
            return self.model_registry[model_name]
        
        # Try to infer category from model name
        category = self._infer_model_category(model_name)
        if category:
            estimated_params = self._estimate_parameters_from_category(category)
            estimated_memory = estimated_params / 500000000  # Rough estimate: 500M params per GB
            
            model_info = ModelInfo(
                name=model_name,
                category=category,
                parameter_count=estimated_params,
                estimated_memory_gb=estimated_memory
            )
            
            # Add to registry for future use
            self.model_registry[model_name] = model_info
            return model_info
        
        logger.warning(f"Unknown model {model_name}, treating as medium (4B) category")
        return ModelInfo(
            name=model_name,
            category=ModelCategory.MEDIUM_4B,
            parameter_count=4000000000,
            estimated_memory_gb=8.0
        )
    
    def _infer_model_category(self, model_name: str) -> Optional[ModelCategory]:
        """Infer model category from model name patterns."""
        name_lower = model_name.lower()
        
        # Look for parameter indicators in model name
        if re.search(r'(1b|1\.5b)', name_lower):
            return ModelCategory.SMALL_1B
        elif re.search(r'(3b|4b)', name_lower):
            return ModelCategory.MEDIUM_4B
        elif re.search(r'(7b|8b|9b)', name_lower):
            return ModelCategory.LARGE_8B
        elif re.search(r'(14b|32b|70b|405b)', name_lower):
            return ModelCategory.XLARGE_10B
        
        return None
    
    def _estimate_parameters_from_category(self, category: ModelCategory) -> int:
        """Estimate parameter count from category."""
        estimates = {
            ModelCategory.SMALL_1B: 1000000000,
            ModelCategory.MEDIUM_4B: 4000000000,
            ModelCategory.LARGE_8B: 8000000000,
            ModelCategory.XLARGE_10B: 14000000000
        }
        return estimates[category]
    
    async def check_execution_availability(self, model_name: str) -> Tuple[bool, str]:
        """
        Check if a model can be executed based on current resource constraints.
        
        Returns:
            Tuple of (can_execute, reason)
        """
        async with self._execution_lock:
            model_info = self.get_model_info(model_name)
            if not model_info:
                return False, f"Unknown model: {model_name}"
            
            category = model_info.category
            current_executions = self.status.active_executions[category]
            
            # Check category-specific limits
            limits = {
                ModelCategory.SMALL_1B: self.limits.small_1b_limit,
                ModelCategory.MEDIUM_4B: self.limits.medium_4b_limit,
                ModelCategory.LARGE_8B: self.limits.large_8b_limit,
                ModelCategory.XLARGE_10B: self.limits.xlarge_10b_limit
            }
            
            if current_executions >= limits[category]:
                return False, f"Execution limit reached for {category.value} models ({current_executions}/{limits[category]})"
            
            # Check GPU memory availability (if we can monitor it)
            try:
                gpu_info = await self._get_gpu_info()
                if gpu_info:
                    available_memory = gpu_info['memory_total'] - gpu_info['memory_used']
                    required_memory = model_info.estimated_memory_gb * 1024  # Convert to MB
                    
                    if available_memory < required_memory:
                        return False, f"Insufficient GPU memory: need {required_memory:.1f}MB, have {available_memory:.1f}MB"
            except Exception as e:
                logger.warning(f"Could not check GPU memory: {e}")
            
            return True, "Available"
    
    async def reserve_execution_slot(self, model_name: str, expert_id: str) -> bool:
        """
        Reserve an execution slot for a model/expert combination.
        
        Returns:
            True if slot was reserved, False otherwise
        """
        async with self._execution_lock:
            can_execute, reason = await self.check_execution_availability(model_name)
            
            if not can_execute:
                logger.info(f"Cannot reserve slot for {expert_id} with {model_name}: {reason}")
                # Add to pending queue
                self.status.pending_requests.append((expert_id, model_name))
                return False
            
            # Reserve the slot
            model_info = self.get_model_info(model_name)
            self.status.active_executions[model_info.category] += 1
            
            logger.info(f"Reserved execution slot for {expert_id} with {model_name} ({model_info.category.value})")
            logger.info(f"Active executions: {dict(self.status.active_executions)}")
            
            return True
    
    async def release_execution_slot(self, model_name: str, expert_id: str):
        """Release an execution slot and process pending requests."""
        async with self._execution_lock:
            model_info = self.get_model_info(model_name)
            if self.status.active_executions[model_info.category] > 0:
                self.status.active_executions[model_info.category] -= 1
                
                logger.info(f"Released execution slot for {expert_id} with {model_name}")
                logger.info(f"Active executions: {dict(self.status.active_executions)}")
                
                # Process pending requests
                await self._process_pending_requests()
    
    async def _process_pending_requests(self):
        """Process pending requests that might now be able to execute."""
        if not self.status.pending_requests:
            return
        
        processed_requests = []
        
        for expert_id, model_name in self.status.pending_requests[:]:
            can_execute, _ = await self.check_execution_availability(model_name)
            if can_execute:
                model_info = self.get_model_info(model_name)
                self.status.active_executions[model_info.category] += 1
                processed_requests.append((expert_id, model_name))
                logger.info(f"Processed pending request for {expert_id} with {model_name}")
        
        # Remove processed requests from pending queue
        for request in processed_requests:
            if request in self.status.pending_requests:
                self.status.pending_requests.remove(request)
    
    async def _get_gpu_info(self) -> Optional[Dict[str, float]]:
        """Get GPU memory information using nvidia-smi."""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=memory.used,memory.total', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Take first GPU
                    memory_used, memory_total = lines[0].split(', ')
                    return {
                        'memory_used': float(memory_used),
                        'memory_total': float(memory_total)
                    }
        except Exception as e:
            logger.debug(f"Could not get GPU info: {e}")
        
        return None
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource utilization status for monitoring."""
        gpu_info = await self._get_gpu_info()
        
        return {
            "execution_limits": {
                "small_1b": self.limits.small_1b_limit,
                "medium_4b": self.limits.medium_4b_limit,
                "large_8b": self.limits.large_8b_limit,
                "xlarge_10b": self.limits.xlarge_10b_limit
            },
            "active_executions": dict(self.status.active_executions),
            "pending_requests": len(self.status.pending_requests),
            "loaded_models": list(self.status.loaded_models.keys()),
            "gpu_memory": gpu_info,
            "model_registry_size": len(self.model_registry)
        }
    
    def get_compatible_agents_for_parallel_execution(
        self, 
        agent_model_pairs: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        Determine which agent/model pairs can be executed in parallel.
        
        Args:
            agent_model_pairs: List of (expert_id, model_name) tuples
            
        Returns:
            List of (expert_id, model_name) tuples that can execute in parallel
        """
        compatible_pairs = []
        category_counts = {category: 0 for category in ModelCategory}
        
        for expert_id, model_name in agent_model_pairs:
            model_info = self.get_model_info(model_name)
            if not model_info:
                continue
            
            category = model_info.category
            current_count = category_counts[category]
            
            # Check if adding this model would exceed limits
            limits = {
                ModelCategory.SMALL_1B: self.limits.small_1b_limit,
                ModelCategory.MEDIUM_4B: self.limits.medium_4b_limit,
                ModelCategory.LARGE_8B: self.limits.large_8b_limit,
                ModelCategory.XLARGE_10B: self.limits.xlarge_10b_limit
            }
            
            if current_count < limits[category]:
                compatible_pairs.append((expert_id, model_name))
                category_counts[category] += 1
            else:
                logger.info(f"Skipping {expert_id} ({model_name}) - category {category.value} limit reached")
        
        return compatible_pairs
    
    async def batch_reserve_slots(self, agent_model_pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Reserve execution slots for multiple agent/model pairs.
        
        Returns:
            List of successfully reserved (expert_id, model_name) pairs
        """
        reserved_pairs = []
        
        async with self._execution_lock:
            for expert_id, model_name in agent_model_pairs:
                can_execute, reason = await self.check_execution_availability(model_name)
                
                if can_execute:
                    model_info = self.get_model_info(model_name)
                    self.status.active_executions[model_info.category] += 1
                    reserved_pairs.append((expert_id, model_name))
                    
                    logger.info(f"Batch reserved slot for {expert_id} with {model_name}")
                else:
                    logger.info(f"Could not batch reserve {expert_id} with {model_name}: {reason}")
                    # Add to pending queue
                    self.status.pending_requests.append((expert_id, model_name))
        
        logger.info(f"Batch reserved {len(reserved_pairs)} out of {len(agent_model_pairs)} requested slots")
        return reserved_pairs


# Global instance
model_resource_manager = ModelResourceManager()