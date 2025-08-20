"""
Container Performance Coordination Service
Eliminates operation conflicts and optimizes resource allocation
"""

import asyncio
import aioredis
import httpx
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    service_name: str
    cpu_usage: float
    memory_usage_mb: float
    response_time_ms: float
    requests_per_second: float
    health_status: str
    last_updated: str

@dataclass
class CoordinationRule:
    rule_id: str
    source_service: str
    target_services: List[str]
    coordination_type: str  # 'sequential', 'parallel', 'mutex', 'throttle'
    max_concurrent: Optional[int] = None
    delay_ms: Optional[int] = None
    priority: int = 5  # 1-10, higher is more important

@dataclass
class PerformanceOptimization:
    optimization_id: str
    service_name: str
    optimization_type: str
    parameters: Dict[str, Any]
    expected_improvement_percent: float
    applied_at: Optional[str] = None
    success: bool = False

class ContainerPerformanceCoordinator:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.coordination_rules = []
        self.service_metrics = {}
        self.active_optimizations = {}
        self.operation_locks = {}
        
        # Default coordination rules
        self._initialize_default_rules()
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(self.redis_url)
        logger.info("Performance Coordinator initialized")
    
    def _initialize_default_rules(self):
        """Initialize default coordination rules"""
        self.coordination_rules = [
            CoordinationRule(
                rule_id="ollama_exclusive",
                source_service="ollama",
                target_services=["reasoning-service", "learning-service", "hybrid-memory-service"],
                coordination_type="mutex",
                max_concurrent=2,
                priority=8
            ),
            CoordinationRule(
                rule_id="database_throttle",
                source_service="postgres",
                target_services=["api", "coordination-service", "reasoning-service"],
                coordination_type="throttle",
                max_concurrent=10,
                delay_ms=50,
                priority=7
            ),
            CoordinationRule(
                rule_id="gpu_sequential",
                source_service="gpu-monitor",
                target_services=["ollama", "voice-interaction-service"],
                coordination_type="sequential",
                delay_ms=100,
                priority=9
            ),
            CoordinationRule(
                rule_id="memory_coordination",
                source_service="hybrid-memory-service",
                target_services=["qdrant", "learning-service"],
                coordination_type="parallel",
                max_concurrent=3,
                priority=6
            )
        ]
    
    async def collect_service_metrics(self) -> Dict[str, ServiceMetrics]:
        """Collect performance metrics from all services"""
        services = [
            {"name": "api", "health_url": "http://api:8000/health"},
            {"name": "ollama", "health_url": "http://ollama:11434/"},
            {"name": "coordination-service", "health_url": "http://coordination-service:8001/health"},
            {"name": "hybrid-memory-service", "health_url": "http://hybrid-memory-service:8002/health"},
            {"name": "reasoning-service", "health_url": "http://reasoning-service:8005/health"},
            {"name": "gpu-monitor", "health_url": "http://gpu-monitor:8025/health"},
            {"name": "monitoring-service", "health_url": "http://monitoring-service:8020/health"}
        ]
        
        collected_metrics = {}
        
        for service in services:
            try:
                async with httpx.AsyncClient() as client:
                    start_time = asyncio.get_event_loop().time()
                    response = await client.get(service["health_url"], timeout=5.0)
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    
                    # Get additional metrics if available
                    metrics_url = service["health_url"].replace("/health", "/metrics")
                    try:
                        metrics_response = await client.get(metrics_url, timeout=3.0)
                        # Parse metrics if needed (simplified for now)
                    except:
                        pass  # Metrics endpoint may not exist
                    
                    collected_metrics[service["name"]] = ServiceMetrics(
                        service_name=service["name"],
                        cpu_usage=0.0,  # Would need container stats
                        memory_usage_mb=0.0,  # Would need container stats
                        response_time_ms=response_time,
                        requests_per_second=0.0,  # Would need historical data
                        health_status="healthy" if response.status_code == 200 else "unhealthy",
                        last_updated=datetime.utcnow().isoformat()
                    )
            except Exception as e:
                logger.warning(f"Failed to collect metrics for {service['name']}: {e}")
                collected_metrics[service["name"]] = ServiceMetrics(
                    service_name=service["name"],
                    cpu_usage=0.0,
                    memory_usage_mb=0.0,
                    response_time_ms=999999,
                    requests_per_second=0.0,
                    health_status="unhealthy",
                    last_updated=datetime.utcnow().isoformat()
                )
        
        self.service_metrics = collected_metrics
        return collected_metrics
    
    async def coordinate_operation(self, service_name: str, operation_type: str, 
                                 target_service: str) -> bool:
        """Coordinate operation between services based on rules"""
        # Find applicable coordination rules
        applicable_rules = [
            rule for rule in self.coordination_rules
            if (rule.source_service == service_name or service_name in rule.target_services)
            and (target_service in rule.target_services or rule.source_service == target_service)
        ]
        
        if not applicable_rules:
            return True  # No coordination needed
        
        # Apply highest priority rule
        rule = max(applicable_rules, key=lambda r: r.priority)
        
        lock_key = f"coordination_lock:{rule.rule_id}"
        operation_key = f"operation:{service_name}:{operation_type}:{target_service}"
        
        try:
            if rule.coordination_type == "mutex":
                # Mutual exclusion - only one operation at a time
                lock_acquired = await self._acquire_lock(lock_key, timeout=10)
                if not lock_acquired:
                    logger.info(f"Mutex coordination: {operation_key} waiting for lock")
                    return False
                
                # Store operation info
                await self.redis.setex(operation_key, 60, json.dumps({
                    "started_at": datetime.utcnow().isoformat(),
                    "rule_id": rule.rule_id,
                    "type": "mutex"
                }))
                
                return True
            
            elif rule.coordination_type == "throttle":
                # Throttle operations based on max_concurrent
                active_ops_key = f"active_ops:{rule.rule_id}"
                active_count = await self.redis.scard(active_ops_key)
                
                if active_count >= rule.max_concurrent:
                    logger.info(f"Throttle coordination: {operation_key} throttled (max: {rule.max_concurrent})")
                    if rule.delay_ms:
                        await asyncio.sleep(rule.delay_ms / 1000)
                    return False
                
                # Add to active operations
                await self.redis.sadd(active_ops_key, operation_key)
                await self.redis.expire(active_ops_key, 300)  # 5 minute expiry
                
                return True
            
            elif rule.coordination_type == "sequential":
                # Sequential execution with delay
                last_op_key = f"last_op:{rule.rule_id}"
                last_op_time = await self.redis.get(last_op_key)
                
                if last_op_time:
                    last_time = datetime.fromisoformat(last_op_time.decode())
                    time_since = (datetime.utcnow() - last_time).total_seconds() * 1000
                    
                    if time_since < rule.delay_ms:
                        wait_time = (rule.delay_ms - time_since) / 1000
                        logger.info(f"Sequential coordination: {operation_key} waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                
                # Update last operation time
                await self.redis.set(last_op_key, datetime.utcnow().isoformat())
                return True
            
            elif rule.coordination_type == "parallel":
                # Parallel execution with concurrency limit
                active_ops_key = f"parallel_ops:{rule.rule_id}"
                active_count = await self.redis.scard(active_ops_key)
                
                if active_count >= rule.max_concurrent:
                    logger.info(f"Parallel coordination: {operation_key} waiting (max: {rule.max_concurrent})")
                    return False
                
                # Add to active operations
                await self.redis.sadd(active_ops_key, operation_key)
                await self.redis.expire(active_ops_key, 300)
                
                return True
        
        except Exception as e:
            logger.error(f"Error in coordination for {operation_key}: {e}")
            return True  # Default to allowing operation if coordination fails
        
        return True
    
    async def _acquire_lock(self, lock_key: str, timeout: int = 10) -> bool:
        """Acquire a distributed lock with timeout"""
        try:
            lock_value = f"lock_{datetime.utcnow().isoformat()}"
            acquired = await self.redis.set(lock_key, lock_value, nx=True, ex=timeout)
            return bool(acquired)
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {e}")
            return False
    
    async def release_operation(self, service_name: str, operation_type: str, 
                              target_service: str):
        """Release operation coordination resources"""
        operation_key = f"operation:{service_name}:{operation_type}:{target_service}"
        
        try:
            # Remove from active operation sets
            for rule in self.coordination_rules:
                if rule.coordination_type in ["throttle", "parallel"]:
                    active_ops_key = f"{rule.coordination_type}_ops:{rule.rule_id}"
                    await self.redis.srem(active_ops_key, operation_key)
                
                elif rule.coordination_type == "mutex":
                    lock_key = f"coordination_lock:{rule.rule_id}"
                    await self.redis.delete(lock_key)
            
            # Clean up operation tracking
            await self.redis.delete(operation_key)
            
        except Exception as e:
            logger.error(f"Error releasing operation {operation_key}: {e}")
    
    async def optimize_performance(self) -> List[PerformanceOptimization]:
        """Analyze metrics and suggest/apply performance optimizations"""
        optimizations = []
        
        await self.collect_service_metrics()
        
        for service_name, metrics in self.service_metrics.items():
            # High response time optimization
            if metrics.response_time_ms > 200:
                optimization = PerformanceOptimization(
                    optimization_id=f"response_time_{service_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    service_name=service_name,
                    optimization_type="reduce_response_time",
                    parameters={
                        "current_response_time_ms": metrics.response_time_ms,
                        "target_response_time_ms": 100,
                        "optimization_method": "caching_and_connection_pooling"
                    },
                    expected_improvement_percent=50.0
                )
                optimizations.append(optimization)
            
            # Unhealthy service recovery
            if metrics.health_status == "unhealthy":
                optimization = PerformanceOptimization(
                    optimization_id=f"health_recovery_{service_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    service_name=service_name,
                    optimization_type="health_recovery",
                    parameters={
                        "recovery_action": "restart_or_circuit_breaker",
                        "health_check_interval": 30
                    },
                    expected_improvement_percent=100.0
                )
                optimizations.append(optimization)
        
        # Store optimizations in Redis
        for opt in optimizations:
            await self.redis.setex(
                f"optimization:{opt.optimization_id}",
                3600,  # 1 hour expiry
                json.dumps(asdict(opt))
            )
        
        return optimizations
    
    async def get_coordination_status(self) -> Dict:
        """Get current coordination status"""
        status = {
            "coordination_rules": [asdict(rule) for rule in self.coordination_rules],
            "service_metrics": {name: asdict(metrics) for name, metrics in self.service_metrics.items()},
            "active_optimizations": len(self.active_optimizations),
            "last_metrics_collection": datetime.utcnow().isoformat()
        }
        
        # Get active operations from Redis
        try:
            active_operations = []
            for rule in self.coordination_rules:
                if rule.coordination_type in ["throttle", "parallel"]:
                    active_ops_key = f"{rule.coordination_type}_ops:{rule.rule_id}"
                    ops = await self.redis.smembers(active_ops_key)
                    active_operations.extend([op.decode() for op in ops])
            
            status["active_operations"] = active_operations
        except Exception as e:
            logger.error(f"Error getting active operations: {e}")
            status["active_operations"] = []
        
        return status
    
    async def run_coordination_loop(self):
        """Run continuous coordination and optimization"""
        logger.info("Starting container performance coordination loop")
        
        while True:
            try:
                # Collect metrics
                await self.collect_service_metrics()
                
                # Run performance optimization
                optimizations = await self.optimize_performance()
                
                if optimizations:
                    logger.info(f"Generated {len(optimizations)} performance optimizations")
                
                # Log coordination status
                healthy_services = sum(1 for m in self.service_metrics.values() if m.health_status == "healthy")
                total_services = len(self.service_metrics)
                avg_response_time = sum(m.response_time_ms for m in self.service_metrics.values()) / total_services if total_services > 0 else 0
                
                logger.info(f"Coordination Status: {healthy_services}/{total_services} healthy, avg response: {avg_response_time:.1f}ms")
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(30)

# Global coordinator instance
coordinator = ContainerPerformanceCoordinator()

async def start_coordination():
    """Start the performance coordinator"""
    await coordinator.initialize()
    await coordinator.run_coordination_loop()
