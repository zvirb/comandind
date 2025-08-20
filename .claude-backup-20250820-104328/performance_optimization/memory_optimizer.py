#!/usr/bin/env python3
"""
System-Wide Memory Optimizer
Implements the memory optimization strategies from config/memory_optimization.yml
"""

import asyncio
import httpx
import json
import logging
import psutil
from typing import Dict, List, Optional
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    def __init__(self):
        self.services = {
            "ollama": "http://localhost:11434",
            "api": "http://localhost:8000", 
            "coordination-service": "http://localhost:8001",
            "hybrid-memory-service": "http://localhost:8002",
            "reasoning-service": "http://localhost:8005",
            "gpu-monitor": "http://localhost:8025"
        }
        
    def get_memory_baseline(self) -> Dict:
        """Get current memory usage baseline"""
        memory = psutil.virtual_memory()
        return {
            "total_memory_gb": round(memory.total / 1024**3, 2),
            "used_memory_gb": round(memory.used / 1024**3, 2), 
            "available_memory_gb": round(memory.available / 1024**3, 2),
            "memory_percent": memory.percent,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_docker_memory_usage(self) -> Dict:
        """Get memory usage for Docker containers"""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                container_stats = {}
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            memory_usage = parts[1].strip()
                            memory_percent = parts[2].strip()
                            
                            container_stats[name] = {
                                "memory_usage": memory_usage,
                                "memory_percent": memory_percent
                            }
                
                return container_stats
            else:
                logger.error(f"Docker stats failed: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get Docker memory stats: {e}")
            return {}
    
    async def optimize_connection_pooling(self) -> Dict:
        """Optimize database connection pooling"""
        optimizations = []
        
        try:
            # Optimize API connection pooling
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.services['api']}/optimize/connections",
                    json={
                        "pool_size": 10,
                        "pool_overflow": 20,
                        "pool_timeout": 30
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    optimizations.append("API connection pooling optimized")
        except Exception as e:
            logger.warning(f"API connection pooling optimization failed: {e}")
        
        return {
            "optimizations_applied": optimizations,
            "status": "partial" if optimizations else "failed"
        }
    
    async def optimize_cache_strategies(self) -> Dict:
        """Optimize cache strategies across services"""
        optimizations = []
        
        try:
            # Optimize Redis cache
            redis_result = subprocess.run([
                "docker", "exec", "ai_workflow_engine-redis-1", 
                "redis-cli", "CONFIG", "SET", "maxmemory-policy", "allkeys-lru"
            ], capture_output=True, text=True, timeout=10)
            
            if redis_result.returncode == 0:
                optimizations.append("Redis cache policy optimized")
                
        except Exception as e:
            logger.warning(f"Redis optimization failed: {e}")
        
        try:
            # Set Redis memory limit
            redis_result = subprocess.run([
                "docker", "exec", "ai_workflow_engine-redis-1",
                "redis-cli", "CONFIG", "SET", "maxmemory", "512mb"
            ], capture_output=True, text=True, timeout=10)
            
            if redis_result.returncode == 0:
                optimizations.append("Redis memory limit set to 512MB")
                
        except Exception as e:
            logger.warning(f"Redis memory limit failed: {e}")
        
        return {
            "optimizations_applied": optimizations,
            "status": "completed" if optimizations else "failed"
        }
    
    async def force_garbage_collection(self) -> Dict:
        """Force garbage collection across Python services"""
        gc_results = []
        
        python_services = ["api", "coordination-service", "hybrid-memory-service", "reasoning-service"]
        
        for service in python_services:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.services[service]}/admin/gc",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        gc_results.append(f"{service}: GC successful")
                    else:
                        gc_results.append(f"{service}: GC endpoint not available")
            except Exception as e:
                gc_results.append(f"{service}: GC failed - {str(e)[:50]}")
        
        return {
            "gc_results": gc_results,
            "status": "completed"
        }
    
    def optimize_system_swappiness(self) -> Dict:
        """Optimize system swap settings"""
        try:
            # Set swappiness to 10 (reduce swap usage)
            result = subprocess.run([
                "sudo", "sysctl", "vm.swappiness=10"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {"swappiness_optimization": "success", "value": 10}
            else:
                return {"swappiness_optimization": "failed", "error": result.stderr}
                
        except Exception as e:
            return {"swappiness_optimization": "error", "message": str(e)}
    
    async def monitor_memory_pressure(self) -> Dict:
        """Monitor current memory pressure and identify high-usage processes"""
        memory = psutil.virtual_memory()
        
        # Get top memory-consuming processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'memory_info']):
            try:
                if proc.info['memory_percent'] > 1.0:  # Only processes using >1% memory
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory_percent': round(proc.info['memory_percent'], 2),
                        'memory_mb': round(proc.info['memory_info'].rss / 1024 / 1024, 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        
        return {
            "system_memory": {
                "total_gb": round(memory.total / 1024**3, 2),
                "used_percent": memory.percent,
                "available_gb": round(memory.available / 1024**3, 2),
                "pressure_level": "high" if memory.percent > 85 else "medium" if memory.percent > 70 else "low"
            },
            "top_memory_consumers": processes[:10],  # Top 10 processes
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_comprehensive_optimization(self) -> Dict:
        """Run comprehensive memory optimization"""
        logger.info("Starting comprehensive memory optimization...")
        
        # Get baseline
        baseline = self.get_memory_baseline()
        docker_baseline = self.get_docker_memory_usage()
        
        logger.info(f"Memory baseline - Used: {baseline['used_memory_gb']}GB ({baseline['memory_percent']}%)")
        
        results = {
            "baseline": baseline,
            "docker_baseline": docker_baseline,
            "optimizations": {}
        }
        
        # Run optimizations
        logger.info("Optimizing cache strategies...")
        cache_result = await self.optimize_cache_strategies()
        results["optimizations"]["cache"] = cache_result
        
        logger.info("Optimizing connection pooling...")
        pool_result = await self.optimize_connection_pooling()
        results["optimizations"]["connection_pooling"] = pool_result
        
        logger.info("Forcing garbage collection...")
        gc_result = await self.force_garbage_collection()
        results["optimizations"]["garbage_collection"] = gc_result
        
        logger.info("Optimizing system swappiness...")
        swap_result = self.optimize_system_swappiness()
        results["optimizations"]["swappiness"] = swap_result
        
        # Wait for optimizations to take effect
        await asyncio.sleep(10)
        
        # Get final measurements
        final_memory = self.get_memory_baseline()
        docker_final = self.get_docker_memory_usage()
        memory_pressure = await self.monitor_memory_pressure()
        
        results["final_measurements"] = {
            "memory": final_memory,
            "docker": docker_final,
            "pressure_analysis": memory_pressure
        }
        
        # Calculate improvements
        memory_improvement = baseline['memory_percent'] - final_memory['memory_percent']
        results["performance_improvement"] = {
            "memory_usage_reduction_percent": round(memory_improvement, 2),
            "memory_freed_gb": round(baseline['used_memory_gb'] - final_memory['used_memory_gb'], 2),
            "optimization_success": memory_improvement > 0
        }
        
        logger.info(f"Memory optimization completed. Freed: {results['performance_improvement']['memory_freed_gb']}GB")
        
        return results

async def main():
    """Main optimization execution"""
    optimizer = MemoryOptimizer()
    result = await optimizer.run_comprehensive_optimization()
    
    print(json.dumps(result, indent=2))
    
    # Print summary
    improvement = result["performance_improvement"]
    if improvement["optimization_success"]:
        print(f"\n✅ SUCCESS: Memory optimization completed!")
        print(f"   Memory freed: {improvement['memory_freed_gb']}GB")
        print(f"   Usage reduction: {improvement['memory_usage_reduction_percent']:.1f}%")
    else:
        print(f"\n⚠️  Memory optimization had minimal impact")
        print(f"   Consider investigating high memory consumers")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())