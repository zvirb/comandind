"""
Monitoring Aggregation Service

Provides centralized health monitoring and service status aggregation
for all containers in the AI Workflow Engine infrastructure.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import httpx
import psutil
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Service configuration
SERVICE_CONFIGS = {
    "coordination-service": {"port": 8001, "endpoint": "/health"},
    "hybrid-memory-service": {"port": 8002, "endpoint": "/health"},
    "learning-service": {"port": 8005, "endpoint": "/health"},
    "perception-service": {"port": 8001, "endpoint": "/health", "internal_port": 8004},
    "reasoning-service": {"port": 8005, "endpoint": "/health"},
    "infrastructure-recovery-service": {"port": 8010, "endpoint": "/health"},
    "api": {"port": 8000, "endpoint": "/health"},
    "webui": {"port": 3001, "endpoint": "/"},
    "chat-service": {"port": 8007, "endpoint": "/health"},
    "voice-interaction-service": {"port": 8006, "endpoint": "/health"},
    "nudge-service": {"port": 8008, "endpoint": "/health"},
    "recommendation-service": {"port": 8009, "endpoint": "/health"},
    "external-api-service": {"port": 8010, "endpoint": "/health", "internal_port": 8012},
    "postgres": {"port": 5432, "check_type": "tcp"},
    "redis": {"port": 6379, "check_type": "tcp"},
    "qdrant": {"port": 6333, "endpoint": "/healthz", "protocol": "https", "verify_ssl": False},
    "ollama": {"port": 11434, "endpoint": "/"},
    "prometheus": {"port": 9090, "endpoint": "/-/healthy"},
    "grafana": {"port": 3000, "endpoint": "/api/health"},
    "alertmanager": {"port": 9093, "endpoint": "/-/healthy"},
    "elasticsearch": {"port": 9200, "endpoint": "/_cluster/health"},
    "kibana": {"port": 5601, "endpoint": "/api/status"},
    "rabbitmq": {"port": 15672, "endpoint": "/api/health/checks/alarms"},
    "kafka": {"port": 9092, "check_type": "tcp"},
    "zookeeper": {"port": 2181, "check_type": "tcp"}
}

# Prometheus metrics
health_check_counter = Counter('monitoring_health_checks_total', 'Total health checks', ['service', 'status'])
service_status_gauge = Gauge('monitoring_service_status', 'Service status (1=healthy, 0=unhealthy)', ['service'])
health_check_duration = Histogram('monitoring_health_check_duration_seconds', 'Health check duration', ['service'])
system_cpu_gauge = Gauge('monitoring_system_cpu_percent', 'System CPU usage percentage')
system_memory_gauge = Gauge('monitoring_system_memory_percent', 'System memory usage percentage')
system_disk_gauge = Gauge('monitoring_system_disk_percent', 'System disk usage percentage')

app = FastAPI(title="Monitoring Aggregation Service", version="1.0.0")

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class ServiceHealth(BaseModel):
    name: str
    status: ServiceStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SystemHealth(BaseModel):
    overall_status: ServiceStatus
    services: List[ServiceHealth]
    system_metrics: Dict[str, float]
    timestamp: datetime
    critical_services_down: List[str]
    warnings: List[str]

class MonitoringService:
    def __init__(self):
        self.redis_client = None
        self.health_cache: Dict[str, ServiceHealth] = {}
        self.check_interval = 30  # seconds
        self.critical_services = [
            "api", "postgres", "redis", "ollama", "coordination-service"
        ]
        
    async def initialize(self):
        """Initialize connections and start monitoring"""
        try:
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self.redis_client.ping()
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}")
            self.redis_client = None
    
    async def check_http_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """Check HTTP/HTTPS endpoint health"""
        protocol = config.get('protocol', 'http')
        port = config.get('internal_port', config['port'])
        endpoint = config.get('endpoint', '/health')
        verify_ssl = config.get('verify_ssl', True)
        
        url = f"{protocol}://{service_name}:{port}{endpoint}"
        
        start_time = time.time()
        try:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
                response = await client.get(url)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ServiceHealth(
                        name=service_name,
                        status=ServiceStatus.HEALTHY,
                        last_check=datetime.now(),
                        response_time_ms=response_time
                    )
                else:
                    return ServiceHealth(
                        name=service_name,
                        status=ServiceStatus.UNHEALTHY,
                        last_check=datetime.now(),
                        response_time_ms=response_time,
                        error_message=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            return ServiceHealth(
                name=service_name,
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    async def check_tcp_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """Check TCP port connectivity"""
        port = config['port']
        start_time = time.time()
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(service_name, port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name=service_name,
                status=ServiceStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=response_time
            )
        except Exception as e:
            return ServiceHealth(
                name=service_name,
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                error_message=str(e)
            )
    
    async def check_service_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """Check individual service health"""
        check_type = config.get('check_type', 'http')
        
        with health_check_duration.labels(service=service_name).time():
            if check_type == 'tcp':
                result = await self.check_tcp_health(service_name, config)
            else:
                result = await self.check_http_health(service_name, config)
        
        # Update metrics
        health_check_counter.labels(service=service_name, status=result.status).inc()
        service_status_gauge.labels(service=service_name).set(
            1 if result.status == ServiceStatus.HEALTHY else 0
        )
        
        # Cache result
        self.health_cache[service_name] = result
        
        # Store in Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"health:{service_name}",
                    60,
                    json.dumps({
                        "status": result.status,
                        "last_check": result.last_check.isoformat(),
                        "response_time_ms": result.response_time_ms,
                        "error_message": result.error_message
                    })
                )
            except Exception:
                pass
        
        return result
    
    async def check_all_services(self) -> List[ServiceHealth]:
        """Check health of all configured services"""
        tasks = []
        for service_name, config in SERVICE_CONFIGS.items():
            tasks.append(self.check_service_health(service_name, config))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_results = []
        for result in results:
            if isinstance(result, ServiceHealth):
                health_results.append(result)
            else:
                # Handle exceptions
                health_results.append(ServiceHealth(
                    name="unknown",
                    status=ServiceStatus.UNKNOWN,
                    last_check=datetime.now(),
                    error_message=str(result)
                ))
        
        return health_results
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get system-level metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Update Prometheus metrics
            system_cpu_gauge.set(cpu_percent)
            system_memory_gauge.set(memory.percent)
            system_disk_gauge.set(disk.percent)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_system_health(self) -> SystemHealth:
        """Get comprehensive system health status"""
        services = await self.check_all_services()
        system_metrics = self.get_system_metrics()
        
        # Determine overall status
        critical_down = []
        warnings = []
        unhealthy_count = 0
        
        for service in services:
            if service.status != ServiceStatus.HEALTHY:
                unhealthy_count += 1
                if service.name in self.critical_services:
                    critical_down.append(service.name)
                else:
                    warnings.append(f"{service.name} is {service.status}")
        
        if critical_down:
            overall_status = ServiceStatus.UNHEALTHY
        elif unhealthy_count > len(services) * 0.3:  # More than 30% unhealthy
            overall_status = ServiceStatus.DEGRADED
        elif warnings:
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY
        
        # Add system metric warnings
        if system_metrics.get("cpu_percent", 0) > 80:
            warnings.append(f"High CPU usage: {system_metrics['cpu_percent']}%")
        if system_metrics.get("memory_percent", 0) > 85:
            warnings.append(f"High memory usage: {system_metrics['memory_percent']}%")
        if system_metrics.get("disk_percent", 0) > 90:
            warnings.append(f"High disk usage: {system_metrics['disk_percent']}%")
        
        return SystemHealth(
            overall_status=overall_status,
            services=services,
            system_metrics=system_metrics,
            timestamp=datetime.now(),
            critical_services_down=critical_down,
            warnings=warnings
        )

# Initialize monitoring service
monitor = MonitoringService()

@app.on_event("startup")
async def startup():
    """Initialize monitoring on startup"""
    await monitor.initialize()
    
    # Start background monitoring task
    async def background_monitor():
        while True:
            try:
                await monitor.check_all_services()
            except Exception as e:
                print(f"Background monitoring error: {e}")
            await asyncio.sleep(monitor.check_interval)
    
    asyncio.create_task(background_monitor())

@app.get("/health")
async def health():
    """Service health check endpoint"""
    return {"status": "healthy", "service": "monitoring-aggregation"}

@app.get("/status")
async def get_status():
    """Get current system status"""
    health = await monitor.get_system_health()
    return health

@app.get("/services")
async def get_services():
    """Get all monitored services"""
    return {"services": list(SERVICE_CONFIGS.keys())}

@app.get("/services/{service_name}")
async def get_service_status(service_name: str):
    """Get specific service status"""
    if service_name not in SERVICE_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    if service_name in monitor.health_cache:
        return monitor.health_cache[service_name]
    
    # Check service if not in cache
    config = SERVICE_CONFIGS[service_name]
    result = await monitor.check_service_health(service_name, config)
    return result

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/critical")
async def get_critical_status():
    """Get critical services status only"""
    results = []
    for service_name in monitor.critical_services:
        if service_name in monitor.health_cache:
            results.append(monitor.health_cache[service_name])
        else:
            config = SERVICE_CONFIGS.get(service_name)
            if config:
                result = await monitor.check_service_health(service_name, config)
                results.append(result)
    
    all_healthy = all(s.status == ServiceStatus.HEALTHY for s in results)
    
    return {
        "all_critical_healthy": all_healthy,
        "critical_services": results
    }

@app.post("/refresh")
async def refresh_status():
    """Force refresh all service statuses"""
    results = await monitor.check_all_services()
    return {"refreshed": len(results), "services": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)