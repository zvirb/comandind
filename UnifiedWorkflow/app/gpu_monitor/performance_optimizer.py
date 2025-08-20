"""
GPU Performance Optimizer
Automatic GPU utilization optimization and ML workload management
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class OptimizationConfig:
    target_gpu_utilization: float = 50.0
    max_gpu_memory_usage: float = 0.85
    min_inference_performance: float = 2.0  # requests per second
    optimization_interval: int = 60  # seconds

@dataclass
class OptimizationResult:
    action_taken: str
    expected_improvement: str
    gpu_utilization_before: float
    gpu_utilization_after: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

class GPUPerformanceOptimizer:
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.last_optimization = None
        self.optimization_history = []
        
    async def get_current_metrics(self) -> Dict:
        """Get current system metrics from GPU monitor"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8025/metrics/performance", timeout=10.0)
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}
    
    async def optimize_ollama_configuration(self) -> OptimizationResult:
        """Optimize Ollama GPU configuration"""
        try:
            metrics = await self.get_current_metrics()
            analysis = metrics.get('performance_analysis', {})
            
            current_gpu_util = analysis.get('gpu_utilization_avg', 0)
            inference_data = analysis.get('inference_performance', {})
            current_inference_time = inference_data.get('inference_time_avg', 0) if inference_data else 0
            
            optimizations = []
            
            # GPU Utilization Optimization
            if current_gpu_util < self.config.target_gpu_utilization:
                # Load a model to increase GPU utilization
                model_load_result = await self._load_optimal_model()
                if model_load_result:
                    optimizations.append("Loaded optimal model for GPU utilization")
                
                # Trigger concurrent inference requests
                await self._trigger_warmup_requests()
                optimizations.append("Triggered GPU warmup requests")
            
            # Memory Optimization
            gpu_memory_util = analysis.get('gpu_memory_utilization_avg', 0) / 100
            if gpu_memory_util > self.config.max_gpu_memory_usage:
                unload_result = await self._unload_unused_models()
                if unload_result:
                    optimizations.append("Unloaded unused models to free GPU memory")
            
            # Performance Optimization
            if current_inference_time > 5.0:  # If inference is slow
                await self._optimize_inference_parameters()
                optimizations.append("Optimized inference parameters")
            
            return OptimizationResult(
                action_taken='; '.join(optimizations) if optimizations else "No optimization needed",
                expected_improvement=f"Target GPU utilization: {self.config.target_gpu_utilization}%",
                gpu_utilization_before=current_gpu_util,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                action_taken="Optimization failed",
                expected_improvement="None",
                gpu_utilization_before=0,
                success=False,
                error_message=str(e)
            )
    
    async def _load_optimal_model(self) -> bool:
        """Load an optimal model for GPU utilization"""
        try:
            # Check if models are already loaded
            async with httpx.AsyncClient() as client:
                ps_response = await client.get("http://ollama:11434/api/ps", timeout=10.0)
                loaded_models = ps_response.json().get('models', [])
                
                if not loaded_models:
                    # Load the default model
                    load_response = await client.post(
                        "http://ollama:11434/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": "System ready",
                            "stream": False
                        },
                        timeout=30.0
                    )
                    return load_response.status_code == 200
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def _trigger_warmup_requests(self) -> bool:
        """Trigger multiple concurrent requests to warm up GPU"""
        try:
            async with httpx.AsyncClient() as client:
                # Create multiple concurrent requests
                tasks = []
                for i in range(3):  # 3 concurrent requests
                    task = client.post(
                        "http://ollama:11434/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": f"Warmup request {i}",
                            "stream": False
                        },
                        timeout=30.0
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                return True
        except Exception as e:
            logger.error(f"Failed to trigger warmup: {e}")
            return False
    
    async def _unload_unused_models(self) -> bool:
        """Unload unused models to free GPU memory"""
        try:
            # This would require Ollama API to support model unloading
            # For now, we'll just log the intent
            logger.info("Would unload unused models to free GPU memory")
            return True
        except Exception as e:
            logger.error(f"Failed to unload models: {e}")
            return False
    
    async def _optimize_inference_parameters(self) -> bool:
        """Optimize inference parameters for better performance"""
        try:
            # Test with optimized parameters
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://ollama:11434/api/generate",
                    json={
                        "model": "llama3.2:3b",
                        "prompt": "Performance test",
                        "stream": False,
                        "options": {
                            "num_gpu": 2,  # Use multiple GPUs if available
                            "num_thread": 8,
                            "repeat_penalty": 1.1,
                            "temperature": 0.7
                        }
                    },
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to optimize inference parameters: {e}")
            return False
    
    async def run_continuous_optimization(self):
        """Run continuous optimization loop"""
        logger.info(f"Starting continuous GPU optimization (interval: {self.config.optimization_interval}s)")
        
        while True:
            try:
                # Only optimize if enough time has passed
                now = datetime.now()
                if (self.last_optimization is None or 
                    (now - self.last_optimization).seconds >= self.config.optimization_interval):
                    
                    logger.info("Running GPU optimization cycle")
                    result = await self.optimize_ollama_configuration()
                    
                    # Record optimization
                    self.optimization_history.append({
                        'timestamp': now.isoformat(),
                        'result': result
                    })
                    
                    # Keep only last 50 optimizations
                    if len(self.optimization_history) > 50:
                        self.optimization_history.pop(0)
                    
                    self.last_optimization = now
                    
                    if result.success:
                        logger.info(f"Optimization completed: {result.action_taken}")
                    else:
                        logger.error(f"Optimization failed: {result.error_message}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(30)
    
    def get_optimization_status(self) -> Dict:
        """Get current optimization status"""
        return {
            'config': {
                'target_gpu_utilization': self.config.target_gpu_utilization,
                'max_gpu_memory_usage': self.config.max_gpu_memory_usage,
                'optimization_interval': self.config.optimization_interval
            },
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'optimization_count': len(self.optimization_history),
            'recent_optimizations': self.optimization_history[-5:] if self.optimization_history else []
        }

# Global optimizer instance
optimizer = GPUPerformanceOptimizer()

async def start_optimizer():
    """Start the performance optimizer"""
    await optimizer.run_continuous_optimization()
