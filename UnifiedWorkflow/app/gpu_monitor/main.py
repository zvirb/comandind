"""
GPU Performance Monitor Service
Monitors GPU utilization, memory usage, and ML workload performance
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response, PlainTextResponse
import asyncio
import psutil
import time
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
import httpx
from performance_optimizer import GPUPerformanceOptimizer, start_optimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GPU Performance Monitor", version="1.0.0")

# Global optimizer instance
optimizer = GPUPerformanceOptimizer()

# Data models
class GPUMetrics(BaseModel):
    gpu_id: int
    name: str
    memory_used: float
    memory_total: float
    memory_utilization: float
    gpu_utilization: float
    temperature: float
    power_usage: float
    power_limit: float

class MLWorkloadMetrics(BaseModel):
    service_name: str
    inference_time_avg: float
    inference_time_p95: float
    requests_per_second: float
    active_models: int
    memory_usage_mb: float

class SystemMetrics(BaseModel):
    cpu_utilization: float
    memory_used_gb: float
    memory_total_gb: float
    memory_utilization: float
    gpu_metrics: List[GPUMetrics]
    ml_workload_metrics: List[MLWorkloadMetrics]

# Global metrics storage
performance_history = []
current_metrics = None

def get_gpu_metrics() -> List[GPUMetrics]:
    """Get current GPU metrics using nvidia-smi"""
    try:
        # Run nvidia-smi to get GPU information
        result = subprocess.run([
            'nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,power.limit',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.error(f"nvidia-smi failed: {result.stderr}")
            return []
        
        gpu_metrics = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(', ')
                if len(parts) >= 8:
                    try:
                        gpu_id = int(parts[0])
                        name = parts[1]
                        memory_used = float(parts[2])
                        memory_total = float(parts[3])
                        gpu_util = float(parts[4])
                        temp = float(parts[5])
                        power_draw = float(parts[6]) if parts[6] != '[Not Supported]' else 0.0
                        power_limit = float(parts[7]) if parts[7] != '[Not Supported]' else 0.0
                        
                        gpu_metrics.append(GPUMetrics(
                            gpu_id=gpu_id,
                            name=name,
                            memory_used=memory_used,
                            memory_total=memory_total,
                            memory_utilization=(memory_used / memory_total) * 100 if memory_total > 0 else 0,
                            gpu_utilization=gpu_util,
                            temperature=temp,
                            power_usage=power_draw,
                            power_limit=power_limit
                        ))
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse GPU data line: {line}, error: {e}")
        
        return gpu_metrics
    except subprocess.TimeoutExpired:
        logger.error("nvidia-smi command timed out")
        return []
    except Exception as e:
        logger.error(f"Error getting GPU metrics: {e}")
        return []

async def get_ollama_metrics() -> Optional[MLWorkloadMetrics]:
    """Get Ollama performance metrics"""
    try:
        async with httpx.AsyncClient() as client:
            # Get loaded models
            models_response = await client.get("http://ollama:11434/api/tags", timeout=5.0)
            models_data = models_response.json()
            active_models = len(models_data.get('models', []))
            
            # Test inference performance
            start_time = time.time()
            test_response = await client.post(
                "http://ollama:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": "Test",
                    "stream": False
                },
                timeout=30.0
            )
            inference_time = time.time() - start_time
            
            # Get approximate memory usage (this is rough)
            memory_usage = 0
            try:
                proc_result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 'json', 'ai_workflow_engine-ollama-1'], capture_output=True, text=True, timeout=5)
                if proc_result.returncode == 0:
                    stats = json.loads(proc_result.stdout)
                    mem_usage_str = stats.get('MemUsage', '0B / 0B')
                    if '/' in mem_usage_str:
                        used_str = mem_usage_str.split('/')[0].strip()
                        # Convert to MB (rough approximation)
                        if 'GiB' in used_str:
                            memory_usage = float(used_str.replace('GiB', '').strip()) * 1024
                        elif 'MiB' in used_str:
                            memory_usage = float(used_str.replace('MiB', '').strip())
            except Exception as e:
                logger.warning(f"Could not get container memory stats: {e}")
            
            return MLWorkloadMetrics(
                service_name="ollama",
                inference_time_avg=inference_time,
                inference_time_p95=inference_time,  # Single sample
                requests_per_second=1.0 / inference_time if inference_time > 0 else 0,
                active_models=active_models,
                memory_usage_mb=memory_usage
            )
    except Exception as e:
        logger.warning(f"Error getting Ollama metrics: {e}")
        return None

def get_system_metrics() -> SystemMetrics:
    """Get comprehensive system metrics"""
    # Get CPU and memory metrics
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # Get GPU metrics
    gpu_metrics = get_gpu_metrics()
    
    return SystemMetrics(
        cpu_utilization=cpu_usage,
        memory_used_gb=memory.used / (1024**3),
        memory_total_gb=memory.total / (1024**3),
        memory_utilization=memory.percent,
        gpu_metrics=gpu_metrics,
        ml_workload_metrics=[]  # Will be filled by async call
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics/gpu")
async def get_gpu_metrics_endpoint():
    """Get current GPU metrics"""
    try:
        metrics = get_gpu_metrics()
        return {"gpu_metrics": metrics, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving GPU metrics: {str(e)}")

@app.get("/metrics/system")
async def get_system_metrics_endpoint():
    """Get comprehensive system metrics"""
    try:
        metrics = get_system_metrics()
        
        # Add ML workload metrics
        ollama_metrics = await get_ollama_metrics()
        if ollama_metrics:
            metrics.ml_workload_metrics.append(ollama_metrics)
        
        return {"system_metrics": metrics, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system metrics: {str(e)}")

@app.get("/metrics/performance")
async def get_performance_metrics():
    """Get performance analysis and recommendations"""
    try:
        gpu_metrics = get_gpu_metrics()
        ollama_metrics = await get_ollama_metrics()
        
        # Analyze performance
        analysis = {
            "gpu_utilization_avg": sum(gpu.gpu_utilization for gpu in gpu_metrics) / len(gpu_metrics) if gpu_metrics else 0,
            "gpu_memory_utilization_avg": sum(gpu.memory_utilization for gpu in gpu_metrics) / len(gpu_metrics) if gpu_metrics else 0,
            "total_gpu_memory_used_gb": sum(gpu.memory_used / 1024 for gpu in gpu_metrics),
            "inference_performance": ollama_metrics.dict() if ollama_metrics else None,
            "recommendations": []
        }
        
        # Generate recommendations
        if analysis["gpu_utilization_avg"] < 30:
            analysis["recommendations"].append("GPU utilization is low (<30%). Consider enabling GPU acceleration for ML workloads or optimizing compute kernels.")
        
        if analysis["gpu_memory_utilization_avg"] > 80:
            analysis["recommendations"].append("GPU memory utilization is high (>80%). Consider model optimization or distributed inference.")
        
        if ollama_metrics and ollama_metrics.inference_time_avg > 5.0:
            analysis["recommendations"].append("ML inference times are high (>5s). Consider model quantization or GPU optimization.")
        
        return {"performance_analysis": analysis, "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing performance: {str(e)}")

@app.post("/optimize/ollama")
async def optimize_ollama():
    """Trigger Ollama optimization"""
    try:
        recommendations = []
        
        # Check current GPU usage
        gpu_metrics = get_gpu_metrics()
        if gpu_metrics:
            max_gpu_util = max(gpu.gpu_utilization for gpu in gpu_metrics)
            if max_gpu_util < 50:
                recommendations.append("Consider enabling OLLAMA_NUM_PARALLEL=2 for better GPU utilization")
                recommendations.append("Enable OLLAMA_FLASH_ATTENTION=true for memory efficiency")
        
        # Check memory usage
        total_gpu_memory = sum(gpu.memory_total for gpu in gpu_metrics)
        used_gpu_memory = sum(gpu.memory_used for gpu in gpu_metrics)
        
        if total_gpu_memory > 0 and (used_gpu_memory / total_gpu_memory) > 0.8:
            recommendations.append("GPU memory usage is high. Consider model quantization or unloading unused models")
        
        return {
            "optimization_recommendations": recommendations,
            "current_config": {
                "gpu_count": len(gpu_metrics),
                "total_gpu_memory_gb": total_gpu_memory / 1024 if total_gpu_memory else 0,
                "used_gpu_memory_gb": used_gpu_memory / 1024 if used_gpu_memory else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating optimization recommendations: {str(e)}")

@app.post("/optimize/auto")
async def run_auto_optimization():
    """Run automatic GPU optimization"""
    try:
        result = await optimizer.optimize_ollama_configuration()
        return {
            "optimization_result": {
                "action_taken": result.action_taken,
                "expected_improvement": result.expected_improvement,
                "gpu_utilization_before": result.gpu_utilization_before,
                "gpu_utilization_after": result.gpu_utilization_after,
                "success": result.success,
                "error_message": result.error_message
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running auto optimization: {str(e)}")

@app.get("/optimize/status")
async def get_optimization_status():
    """Get current optimization status"""
    try:
        status = optimizer.get_optimization_status()
        return {"optimization_status": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting optimization status: {str(e)}")

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    try:
        gpu_metrics = get_gpu_metrics()
        ollama_metrics = await get_ollama_metrics()
        
        metrics_text = []
        
        # GPU metrics
        for gpu in gpu_metrics:
            metrics_text.append(f'gpu_utilization{{gpu_id="{gpu.gpu_id}",name="{gpu.name}"}} {gpu.gpu_utilization}')
            metrics_text.append(f'gpu_memory_used_mb{{gpu_id="{gpu.gpu_id}",name="{gpu.name}"}} {gpu.memory_used}')
            metrics_text.append(f'gpu_memory_total_mb{{gpu_id="{gpu.gpu_id}",name="{gpu.name}"}} {gpu.memory_total}')
            metrics_text.append(f'gpu_temperature{{gpu_id="{gpu.gpu_id}",name="{gpu.name}"}} {gpu.temperature}')
            metrics_text.append(f'gpu_power_usage{{gpu_id="{gpu.gpu_id}",name="{gpu.name}"}} {gpu.power_usage}')
        
        # ML workload metrics
        if ollama_metrics:
            metrics_text.append(f'ml_inference_time_seconds{{service="ollama"}} {ollama_metrics.inference_time_avg}')
            metrics_text.append(f'ml_requests_per_second{{service="ollama"}} {ollama_metrics.requests_per_second}')
            metrics_text.append(f'ml_active_models{{service="ollama"}} {ollama_metrics.active_models}')
        
        from fastapi import Response
        return Response(
            content='\n'.join(metrics_text) + '\n',
            media_type='text/plain; version=0.0.4; charset=utf-8',
            headers={'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Prometheus metrics: {str(e)}")

# Background task for continuous monitoring
async def monitoring_loop():
    """Background monitoring loop"""
    global current_metrics, performance_history
    
    while True:
        try:
            # Collect metrics
            system_metrics = get_system_metrics()
            ollama_metrics = await get_ollama_metrics()
            
            if ollama_metrics:
                system_metrics.ml_workload_metrics.append(ollama_metrics)
            
            current_metrics = system_metrics
            
            # Store in history (keep last 100 entries)
            performance_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": system_metrics.dict()
            })
            
            if len(performance_history) > 100:
                performance_history.pop(0)
            
            # Log key metrics
            if system_metrics.gpu_metrics:
                avg_gpu_util = sum(gpu.gpu_utilization for gpu in system_metrics.gpu_metrics) / len(system_metrics.gpu_metrics)
                total_gpu_memory = sum(gpu.memory_used for gpu in system_metrics.gpu_metrics)
                logger.info(f"GPU Utilization: {avg_gpu_util:.1f}%, GPU Memory Used: {total_gpu_memory:.1f}MB")
            
            if ollama_metrics:
                logger.info(f"Ollama Performance: {ollama_metrics.inference_time_avg:.2f}s inference, {ollama_metrics.requests_per_second:.2f} req/s")
        
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        
        await asyncio.sleep(30)  # Monitor every 30 seconds

@app.on_event("startup")
async def startup_event():
    """Start background monitoring and optimization"""
    asyncio.create_task(monitoring_loop())
    asyncio.create_task(start_optimizer())
    logger.info("GPU Performance Monitor and Optimizer started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8025)