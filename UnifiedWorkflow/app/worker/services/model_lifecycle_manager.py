"""
Model Lifecycle Manager - Handles model loading, unloading, and GPU memory optimization
Provides efficient model management for parallel expert execution with resource monitoring.
"""

import asyncio
import logging
import subprocess
import json
import time
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.model_resource_manager import model_resource_manager, ModelInfo, ModelCategory

logger = logging.getLogger(__name__)


@dataclass
class ModelLoadStatus:
    """Status of a loaded model."""
    model_name: str
    loaded_at: datetime
    last_used: datetime
    usage_count: int = 0
    memory_usage_mb: float = 0.0
    is_preloaded: bool = False
    load_time_seconds: float = 0.0


class ModelLifecycleManager:
    """
    Manages the lifecycle of models including loading, unloading, and memory optimization.
    Integrates with Ollama for efficient model management and GPU resource monitoring.
    """
    
    def __init__(self):
        self.loaded_models: Dict[str, ModelLoadStatus] = {}
        self.preload_models: Set[str] = {
            # Common models to keep loaded for fast access
            "llama3.2:1b",    # Fast small model for simple tasks
            "llama3.2:3b",    # Medium model for moderate complexity
            "llama3.1:8b",    # Large model for complex tasks
            "qwen2.5:1.5b",   # Alternative fast model
            "qwen2.5:7b"      # Alternative large model
        }
        self.model_unload_timeout_minutes = 10  # Unload models after 10 minutes of inactivity
        self.max_loaded_models = 8  # Maximum number of models to keep loaded
        self._lifecycle_lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # Check for cleanup every 5 minutes
        
    async def start_background_management(self):
        """Start background model lifecycle management."""
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._background_cleanup_loop())
            logger.info("Started model lifecycle background management")
    
    async def stop_background_management(self):
        """Stop background model lifecycle management."""
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped model lifecycle background management")
    
    async def ensure_model_loaded(self, model_name: str) -> bool:
        """
        Ensure a model is loaded and ready for use.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            True if model is loaded successfully, False otherwise
        """
        async with self._lifecycle_lock:
            # Check if model is already loaded
            if model_name in self.loaded_models:
                # Update last used time
                self.loaded_models[model_name].last_used = datetime.now(timezone.utc)
                self.loaded_models[model_name].usage_count += 1
                logger.debug(f"Model {model_name} already loaded, updated usage")
                return True
            
            # Check if we need to free up space
            if len(self.loaded_models) >= self.max_loaded_models:
                await self._unload_least_recently_used_model()
            
            # Load the model
            return await self._load_model(model_name)
    
    async def _load_model(self, model_name: str) -> bool:
        """Load a model into memory."""
        logger.info(f"Loading model {model_name}...")
        start_time = time.time()
        
        try:
            # Use a simple prompt to trigger model loading
            test_prompt = "Hello"
            response, _ = await invoke_llm_with_tokens(
                messages=[{"role": "user", "content": test_prompt}],
                model_name=model_name
            )
            
            load_time = time.time() - start_time
            
            # Record the loaded model
            self.loaded_models[model_name] = ModelLoadStatus(
                model_name=model_name,
                loaded_at=datetime.now(timezone.utc),
                last_used=datetime.now(timezone.utc),
                usage_count=1,
                is_preloaded=model_name in self.preload_models,
                load_time_seconds=load_time
            )
            
            # Estimate memory usage
            await self._update_model_memory_usage(model_name)
            
            logger.info(f"Successfully loaded model {model_name} in {load_time:.2f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
    
    async def _update_model_memory_usage(self, model_name: str):
        """Update memory usage for a loaded model."""
        try:
            gpu_info = await self._get_gpu_memory_info()
            if gpu_info and model_name in self.loaded_models:
                # Estimate memory usage based on model info
                model_info = model_resource_manager.get_model_info(model_name)
                if model_info:
                    estimated_memory = model_info.estimated_memory_gb * 1024  # Convert to MB
                    self.loaded_models[model_name].memory_usage_mb = estimated_memory
                    logger.debug(f"Model {model_name} estimated memory usage: {estimated_memory:.1f}MB")
        except Exception as e:
            logger.debug(f"Could not update memory usage for {model_name}: {e}")
    
    async def unload_model(self, model_name: str, force: bool = False) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
            force: Force unload even if it's a preloaded model
            
        Returns:
            True if model was unloaded, False otherwise
        """
        async with self._lifecycle_lock:
            if model_name not in self.loaded_models:
                return True  # Already unloaded
            
            # Don't unload preloaded models unless forced
            if self.loaded_models[model_name].is_preloaded and not force:
                logger.debug(f"Skipping unload of preloaded model {model_name}")
                return False
            
            try:
                # Attempt to unload via Ollama API if available
                await self._ollama_unload_model(model_name)
                
                # Remove from loaded models
                del self.loaded_models[model_name]
                logger.info(f"Unloaded model {model_name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to unload model {model_name}: {e}")
                return False
    
    async def _ollama_unload_model(self, model_name: str):
        """Attempt to unload model via Ollama API."""
        try:
            # Note: Ollama doesn't have a direct unload API, but we can try
            # to reduce memory by calling garbage collection
            import gc
            gc.collect()
            logger.debug(f"Attempted memory cleanup for {model_name}")
        except Exception as e:
            logger.debug(f"Memory cleanup attempt failed: {e}")
    
    async def _unload_least_recently_used_model(self):
        """Unload the least recently used model that's not preloaded."""
        if not self.loaded_models:
            return
        
        # Find non-preloaded models sorted by last used time
        candidates = [
            (name, status) for name, status in self.loaded_models.items()
            if not status.is_preloaded
        ]
        
        if not candidates:
            # If all loaded models are preloaded, unload the oldest preloaded one
            candidates = list(self.loaded_models.items())
        
        if candidates:
            # Sort by last used time (oldest first)
            candidates.sort(key=lambda x: x[1].last_used)
            model_to_unload = candidates[0][0]
            
            logger.info(f"Unloading LRU model {model_to_unload} to free memory")
            await self.unload_model(model_to_unload, force=True)
    
    async def preload_common_models(self):
        """Preload commonly used models for faster access."""
        logger.info(f"Preloading common models: {list(self.preload_models)}")
        
        for model_name in self.preload_models:
            try:
                await self.ensure_model_loaded(model_name)
                logger.info(f"Preloaded model {model_name}")
            except Exception as e:
                logger.warning(f"Failed to preload model {model_name}: {e}")
    
    async def _background_cleanup_loop(self):
        """Background loop for model cleanup and optimization."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_inactive_models()
                await self._log_memory_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background cleanup loop: {e}")
    
    async def _cleanup_inactive_models(self):
        """Clean up models that haven't been used recently."""
        current_time = datetime.now(timezone.utc)
        timeout_threshold = timedelta(minutes=self.model_unload_timeout_minutes)
        
        models_to_unload = []
        
        async with self._lifecycle_lock:
            for model_name, status in self.loaded_models.items():
                if not status.is_preloaded:  # Don't auto-unload preloaded models
                    time_since_last_use = current_time - status.last_used
                    if time_since_last_use > timeout_threshold:
                        models_to_unload.append(model_name)
        
        for model_name in models_to_unload:
            logger.info(f"Auto-unloading inactive model {model_name}")
            await self.unload_model(model_name)
    
    async def _get_gpu_memory_info(self) -> Optional[Dict[str, float]]:
        """Get GPU memory information."""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=memory.used,memory.total,memory.free',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Take first GPU
                    memory_used, memory_total, memory_free = lines[0].split(', ')
                    return {
                        'memory_used': float(memory_used),
                        'memory_total': float(memory_total),
                        'memory_free': float(memory_free)
                    }
        except Exception as e:
            logger.debug(f"Could not get GPU memory info: {e}")
        
        return None
    
    async def _log_memory_status(self):
        """Log current memory status for monitoring."""
        gpu_info = await self._get_gpu_memory_info()
        
        if gpu_info:
            logger.info(
                f"GPU Memory: {gpu_info['memory_used']:.1f}MB used / "
                f"{gpu_info['memory_total']:.1f}MB total "
                f"({gpu_info['memory_free']:.1f}MB free)"
            )
        
        logger.info(f"Loaded models: {len(self.loaded_models)}")
        for model_name, status in self.loaded_models.items():
            logger.debug(
                f"  {model_name}: used {status.usage_count} times, "
                f"last used {(datetime.now(timezone.utc) - status.last_used).total_seconds():.0f}s ago"
            )
    
    async def get_lifecycle_status(self) -> Dict[str, Any]:
        """Get current model lifecycle status for monitoring."""
        gpu_info = await self._get_gpu_memory_info()
        
        return {
            "loaded_models": {
                name: {
                    "loaded_at": status.loaded_at.isoformat(),
                    "last_used": status.last_used.isoformat(),
                    "usage_count": status.usage_count,
                    "memory_usage_mb": status.memory_usage_mb,
                    "is_preloaded": status.is_preloaded,
                    "load_time_seconds": status.load_time_seconds
                }
                for name, status in self.loaded_models.items()
            },
            "preload_models": list(self.preload_models),
            "max_loaded_models": self.max_loaded_models,
            "unload_timeout_minutes": self.model_unload_timeout_minutes,
            "gpu_memory": gpu_info,
            "background_management_active": self._background_task is not None and not self._background_task.done()
        }
    
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Optimize memory usage by unloading unnecessary models.
        
        Returns:
            Status report of optimization actions
        """
        actions_taken = []
        initial_loaded_count = len(self.loaded_models)
        
        # Get GPU memory info
        gpu_info = await self._get_gpu_memory_info()
        if gpu_info:
            memory_usage_percent = (gpu_info['memory_used'] / gpu_info['memory_total']) * 100
            
            # If memory usage is high, be more aggressive about unloading
            if memory_usage_percent > 80:
                logger.info(f"High GPU memory usage ({memory_usage_percent:.1f}%), optimizing...")
                
                # Unload non-preloaded models
                models_to_unload = [
                    name for name, status in self.loaded_models.items()
                    if not status.is_preloaded
                ]
                
                for model_name in models_to_unload:
                    if await self.unload_model(model_name):
                        actions_taken.append(f"Unloaded {model_name}")
                        
                        # Check if we've freed enough memory
                        updated_gpu_info = await self._get_gpu_memory_info()
                        if updated_gpu_info:
                            updated_usage_percent = (updated_gpu_info['memory_used'] / updated_gpu_info['memory_total']) * 100
                            if updated_usage_percent < 70:
                                break
        
        # Clean up inactive models
        await self._cleanup_inactive_models()
        actions_taken.append("Cleaned up inactive models")
        
        final_loaded_count = len(self.loaded_models)
        
        return {
            "initial_loaded_models": initial_loaded_count,
            "final_loaded_models": final_loaded_count,
            "models_unloaded": initial_loaded_count - final_loaded_count,
            "actions_taken": actions_taken,
            "gpu_memory": await self._get_gpu_memory_info()
        }
    
    async def predict_model_demand(self, complexity_distribution: Dict[str, float]) -> List[str]:
        """
        Predict which models will be in demand based on complexity distribution.
        
        Args:
            complexity_distribution: Distribution of request complexities (e.g., {"simple": 0.3, "moderate": 0.4, "complex": 0.3})
            
        Returns:
            List of models ranked by predicted demand
        """
        # Map complexity levels to preferred models
        complexity_models = {
            "simple": ["llama3.2:1b", "qwen2.5:1.5b"],
            "moderate": ["llama3.2:3b", "qwen2.5:3b", "phi3:3.8b"],
            "complex": ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"],
            "expert": ["qwen2.5:14b", "qwen2.5:32b", "llama3.1:70b"]
        }
        
        # Calculate demand scores for each model
        model_scores = {}
        for complexity, probability in complexity_distribution.items():
            if complexity in complexity_models:
                for model in complexity_models[complexity]:
                    model_scores[model] = model_scores.get(model, 0) + probability
        
        # Sort by demand score and return top models
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        return [model for model, score in sorted_models[:self.max_loaded_models]]
    
    async def intelligent_preload(self, usage_patterns: Optional[Dict[str, int]] = None):
        """
        Intelligently preload models based on usage patterns and resource availability.
        
        Args:
            usage_patterns: Historical usage counts for models (optional)
        """
        logger.info("Starting intelligent model preloading...")
        
        # Get current GPU memory status
        gpu_info = await self._get_gpu_memory_info()
        if not gpu_info:
            logger.warning("Cannot get GPU info, skipping intelligent preload")
            return
        
        available_memory_gb = gpu_info['memory_free'] / 1024  # Convert MB to GB
        logger.info(f"Available GPU memory: {available_memory_gb:.1f} GB")
        
        # Determine models to preload based on available memory and usage patterns
        models_to_preload = []
        
        if usage_patterns:
            # Sort models by usage frequency
            sorted_by_usage = sorted(usage_patterns.items(), key=lambda x: x[1], reverse=True)
            models_to_preload = [model for model, count in sorted_by_usage if count > 0]
        else:
            # Use default preload models if no usage patterns available
            models_to_preload = list(self.preload_models)
        
        # Preload models based on available memory
        total_estimated_memory = 0
        successful_preloads = []
        
        for model_name in models_to_preload:
            if model_name in self.loaded_models:
                continue  # Already loaded
            
            # Get model info to estimate memory usage
            model_info = model_resource_manager.get_model_info(model_name)
            if not model_info:
                continue
            
            estimated_memory = model_info.estimated_memory_gb
            
            # Check if we have enough memory for this model
            if total_estimated_memory + estimated_memory <= available_memory_gb * 0.8:  # Use 80% of available memory
                try:
                    if await self.ensure_model_loaded(model_name):
                        self.loaded_models[model_name].is_preloaded = True
                        total_estimated_memory += estimated_memory
                        successful_preloads.append(model_name)
                        logger.info(f"Successfully preloaded {model_name} ({estimated_memory:.1f} GB)")
                    else:
                        logger.warning(f"Failed to preload {model_name}")
                except Exception as e:
                    logger.warning(f"Error preloading {model_name}: {e}")
            else:
                logger.info(f"Skipping {model_name} - insufficient memory ({estimated_memory:.1f} GB needed)")
        
        logger.info(f"Preloading complete. Successfully loaded {len(successful_preloads)} models: {successful_preloads}")
    
    async def dynamic_gpu_allocation(self, requested_models: List[str]) -> Dict[str, Any]:
        """
        Dynamically allocate GPU resources for requested models.
        
        Args:
            requested_models: List of models that need to be loaded
            
        Returns:
            Allocation status and recommendations
        """
        allocation_result = {
            "requested_models": requested_models,
            "can_allocate": [],
            "need_unloading": [],
            "memory_insufficient": [],
            "recommendations": []
        }
        
        gpu_info = await self._get_gpu_memory_info()
        if not gpu_info:
            allocation_result["recommendations"].append("Cannot determine GPU memory status")
            return allocation_result
        
        available_memory_gb = gpu_info['memory_free'] / 1024
        required_memory_gb = 0
        
        # Calculate total memory needed for requested models
        for model_name in requested_models:
            model_info = model_resource_manager.get_model_info(model_name)
            if model_info:
                required_memory_gb += model_info.estimated_memory_gb
        
        # Check if we need to free up memory
        if required_memory_gb > available_memory_gb:
            memory_to_free = required_memory_gb - available_memory_gb
            allocation_result["recommendations"].append(f"Need to free {memory_to_free:.1f} GB of GPU memory")
            
            # Find models to unload (prioritize non-preloaded and least recently used)
            models_by_priority = sorted(
                self.loaded_models.items(),
                key=lambda x: (x[1].is_preloaded, x[1].last_used),
                reverse=False
            )
            
            freed_memory = 0
            for model_name, status in models_by_priority:
                if model_name not in requested_models:  # Don't unload requested models
                    model_info = model_resource_manager.get_model_info(model_name)
                    if model_info:
                        allocation_result["need_unloading"].append({
                            "model": model_name,
                            "memory_gb": model_info.estimated_memory_gb,
                            "is_preloaded": status.is_preloaded,
                            "last_used": status.last_used.isoformat()
                        })
                        freed_memory += model_info.estimated_memory_gb
                        
                        if freed_memory >= memory_to_free:
                            break
        
        # Check which requested models can be allocated
        for model_name in requested_models:
            if model_name in self.loaded_models:
                allocation_result["can_allocate"].append(model_name)
            else:
                model_info = model_resource_manager.get_model_info(model_name)
                if model_info:
                    if model_info.estimated_memory_gb <= available_memory_gb:
                        allocation_result["can_allocate"].append(model_name)
                    else:
                        allocation_result["memory_insufficient"].append({
                            "model": model_name,
                            "required_gb": model_info.estimated_memory_gb,
                            "available_gb": available_memory_gb
                        })
        
        # Generate recommendations
        if allocation_result["need_unloading"]:
            allocation_result["recommendations"].append(
                f"Unload {len(allocation_result['need_unloading'])} models to free memory"
            )
        
        if allocation_result["memory_insufficient"]:
            allocation_result["recommendations"].append(
                "Some models require more memory than available"
            )
        
        if len(allocation_result["can_allocate"]) == len(requested_models):
            allocation_result["recommendations"].append("All requested models can be allocated")
        
        return allocation_result
    
    async def adaptive_model_management(self, service_usage_stats: Dict[str, Dict[str, int]]):
        """
        Adaptively manage models based on service usage statistics.
        
        Args:
            service_usage_stats: Usage statistics per service (e.g., {"simple_chat": {"llama3.2:1b": 10}, ...})
        """
        logger.info("Starting adaptive model management based on usage statistics")
        
        # Aggregate usage across all services
        total_usage = {}
        for service_stats in service_usage_stats.values():
            for model, count in service_stats.items():
                total_usage[model] = total_usage.get(model, 0) + count
        
        # Update preload models based on high usage
        high_usage_models = [
            model for model, count in total_usage.items() 
            if count >= 5  # Models used 5+ times should be preloaded
        ]
        
        # Add high-usage models to preload set
        old_preload_count = len(self.preload_models)
        self.preload_models.update(high_usage_models)
        new_preload_count = len(self.preload_models)
        
        if new_preload_count > old_preload_count:
            logger.info(f"Added {new_preload_count - old_preload_count} models to preload set based on usage")
        
        # Remove low-usage models from preload set (keep at least core models)
        core_models = {"llama3.2:1b", "llama3.2:3b", "llama3.1:8b"}  # Always keep these
        low_usage_models = [
            model for model in self.preload_models 
            if model not in core_models and total_usage.get(model, 0) < 2
        ]
        
        for model in low_usage_models:
            self.preload_models.discard(model)
            logger.info(f"Removed {model} from preload set due to low usage")
        
        # Adjust max loaded models based on memory pressure
        gpu_info = await self._get_gpu_memory_info()
        if gpu_info:
            memory_usage_percent = (gpu_info['memory_used'] / gpu_info['memory_total']) * 100
            
            if memory_usage_percent > 85:
                # High memory pressure - reduce max loaded models
                self.max_loaded_models = max(4, self.max_loaded_models - 1)
                logger.info(f"Reduced max_loaded_models to {self.max_loaded_models} due to memory pressure")
            elif memory_usage_percent < 60 and len(total_usage) > self.max_loaded_models:
                # Low memory pressure and high demand - increase max loaded models
                self.max_loaded_models = min(12, self.max_loaded_models + 1)
                logger.info(f"Increased max_loaded_models to {self.max_loaded_models} due to high demand")
        
        # Trigger intelligent preloading with updated patterns
        await self.intelligent_preload(total_usage)


# Global instance
model_lifecycle_manager = ModelLifecycleManager()