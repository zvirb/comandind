#!/usr/bin/env python3
"""
Unified Health Monitoring Framework for Cognitive Services
Provides centralized health monitoring, automated recovery, and evidence collection
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import docker
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import redis.asyncio as redis
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
health_check_counter = Counter(
    'cognitive_service_health_checks_total',
    'Total number of health checks performed',
    ['service', 'status']
)

service_health_gauge = Gauge(
    'cognitive_service_health_status',
    'Current health status of cognitive services (1=healthy, 0=unhealthy)',
    ['service']
)

health_check_duration = Histogram(
    'cognitive_service_health_check_duration_seconds',
    'Duration of health checks',
    ['service']
)

recovery_attempts = Counter(
    'cognitive_service_recovery_attempts_total',
    'Total number of recovery attempts',
    ['service', 'action', 'result']
)

service_uptime_gauge = Gauge(
    'cognitive_service_uptime_seconds',
    'Service uptime in seconds',
    ['service']
)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery action types"""
    RESTART = "restart"
    SCALE = "scale"
    RECONNECT = "reconnect"
    ALERT = "alert"
    NONE = "none"


@dataclass
class ServiceHealth:
    """Service health information"""
    name: str
    status: HealthStatus
    endpoint: str
    port: int
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    consecutive_failures: int = 0
    uptime_seconds: float = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "status": self.status.value,
            "endpoint": self.endpoint,
            "port": self.port,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
            "consecutive_failures": self.consecutive_failures,
            "uptime_seconds": self.uptime_seconds
        }


@dataclass
class RecoveryResult:
    """Recovery action result"""
    service: str
    action: RecoveryAction
    success: bool
    timestamp: datetime
    message: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "service": self.service,
            "action": self.action.value,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message
        }


class CognitiveServiceMonitor:
    """Main health monitoring class for cognitive services"""
    
    # Service configuration
    SERVICES = {
        "learning-service": {
            "port": 8010,
            "endpoint": "/health",
            "container_name": "ai_workflow_engine-learning_service_1",
            "critical": True,
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.ALERT]
        },
        "reasoning-service": {
            "port": 8005,
            "endpoint": "/health",
            "container_name": "ai_workflow_engine-reasoning_service_1",
            "critical": True,
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.RECONNECT, RecoveryAction.ALERT]
        },
        "coordination-service": {
            "port": 8001,
            "endpoint": "/health",
            "container_name": "ai_workflow_engine-coordination_service_1",
            "critical": True,
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.ALERT]
        },
        "hybrid-memory-service": {
            "port": 8002,
            "endpoint": "/health",
            "container_name": "ai_workflow_engine-hybrid_memory_service_1",
            "critical": False,
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.RECONNECT, RecoveryAction.ALERT]
        },
        "perception-service": {
            "port": 8003,
            "endpoint": "/health",
            "container_name": "ai_workflow_engine-perception_service_1",
            "critical": False,
            "recovery_actions": [RecoveryAction.RESTART, RecoveryAction.ALERT]
        }
    }
    
    def __init__(self, 
                 check_interval: int = 30,
                 recovery_threshold: int = 3,
                 evidence_dir: str = "/tmp/health_monitoring"):
        """
        Initialize the health monitor
        
        Args:
            check_interval: Seconds between health checks
            recovery_threshold: Consecutive failures before recovery action
            evidence_dir: Directory for storing evidence
        """
        self.check_interval = check_interval
        self.recovery_threshold = recovery_threshold
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Service state tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        self.recovery_history: List[RecoveryResult] = []
        self.docker_client = None
        self.redis_client = None
        self.session = None
        
        # Service start times for uptime tracking
        self.service_start_times: Dict[str, datetime] = {}
        
    async def initialize(self):
        """Initialize connections and resources"""
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            
            # Initialize Redis client
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            await self.redis_client.ping()
            
            # Initialize HTTP session
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Health monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize health monitor: {e}")
            raise
            
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
            
    async def check_service_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """
        Check health of a single service
        
        Args:
            service_name: Name of the service
            config: Service configuration
            
        Returns:
            ServiceHealth object
        """
        start_time = time.time()
        
        try:
            # Perform health check
            url = f"http://localhost:{config['port']}{config['endpoint']}"
            
            async with self.session.get(url) as response:
                response_time_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Determine health status from response
                    status = HealthStatus.HEALTHY
                    if data.get('status') == 'unhealthy':
                        status = HealthStatus.UNHEALTHY
                    elif data.get('status') == 'degraded':
                        status = HealthStatus.DEGRADED
                    
                    # Calculate uptime
                    uptime = 0
                    if service_name in self.service_start_times:
                        uptime = (datetime.now() - self.service_start_times[service_name]).total_seconds()
                    else:
                        self.service_start_times[service_name] = datetime.now()
                    
                    health = ServiceHealth(
                        name=service_name,
                        status=status,
                        endpoint=config['endpoint'],
                        port=config['port'],
                        last_check=datetime.now(),
                        response_time_ms=response_time_ms,
                        metadata=data,
                        consecutive_failures=0,
                        uptime_seconds=uptime
                    )
                    
                    # Update metrics
                    service_health_gauge.labels(service=service_name).set(
                        1 if status == HealthStatus.HEALTHY else 0
                    )
                    service_uptime_gauge.labels(service=service_name).set(uptime)
                    
                else:
                    # Non-200 response
                    health = ServiceHealth(
                        name=service_name,
                        status=HealthStatus.UNHEALTHY,
                        endpoint=config['endpoint'],
                        port=config['port'],
                        last_check=datetime.now(),
                        response_time_ms=response_time_ms,
                        error_message=f"HTTP {response.status}",
                        consecutive_failures=self._get_consecutive_failures(service_name) + 1
                    )
                    
                    service_health_gauge.labels(service=service_name).set(0)
                    
        except asyncio.TimeoutError:
            health = ServiceHealth(
                name=service_name,
                status=HealthStatus.UNHEALTHY,
                endpoint=config['endpoint'],
                port=config['port'],
                last_check=datetime.now(),
                response_time_ms=-1,
                error_message="Health check timeout",
                consecutive_failures=self._get_consecutive_failures(service_name) + 1
            )
            
            service_health_gauge.labels(service=service_name).set(0)
            
        except Exception as e:
            health = ServiceHealth(
                name=service_name,
                status=HealthStatus.UNKNOWN,
                endpoint=config['endpoint'],
                port=config['port'],
                last_check=datetime.now(),
                response_time_ms=-1,
                error_message=str(e),
                consecutive_failures=self._get_consecutive_failures(service_name) + 1
            )
            
            service_health_gauge.labels(service=service_name).set(0)
            
        # Record metrics
        health_check_counter.labels(
            service=service_name,
            status=health.status.value
        ).inc()
        
        if health.response_time_ms > 0:
            health_check_duration.labels(service=service_name).observe(
                health.response_time_ms / 1000
            )
            
        # Store health status
        self.service_health[service_name] = health
        
        # Store in Redis for persistence
        await self._store_health_redis(service_name, health)
        
        return health
        
    def _get_consecutive_failures(self, service_name: str) -> int:
        """Get consecutive failure count for a service"""
        if service_name in self.service_health:
            return self.service_health[service_name].consecutive_failures
        return 0
        
    async def _store_health_redis(self, service_name: str, health: ServiceHealth):
        """Store health status in Redis"""
        try:
            key = f"cognitive:health:{service_name}"
            await self.redis_client.setex(
                key,
                300,  # 5 minute TTL
                json.dumps(health.to_dict())
            )
        except Exception as e:
            logger.error(f"Failed to store health in Redis: {e}")
            
    async def perform_recovery(self, service_name: str, config: Dict) -> Optional[RecoveryResult]:
        """
        Perform recovery actions for unhealthy service
        
        Args:
            service_name: Name of the service
            config: Service configuration
            
        Returns:
            RecoveryResult if action taken, None otherwise
        """
        health = self.service_health.get(service_name)
        
        if not health or health.consecutive_failures < self.recovery_threshold:
            return None
            
        # Determine recovery action based on configuration
        for action in config.get('recovery_actions', []):
            if action == RecoveryAction.RESTART:
                result = await self._restart_container(service_name, config)
                if result.success:
                    return result
                    
            elif action == RecoveryAction.RECONNECT:
                result = await self._reconnect_service(service_name, config)
                if result.success:
                    return result
                    
            elif action == RecoveryAction.ALERT:
                result = await self._send_alert(service_name, health)
                return result
                
        return None
        
    async def _restart_container(self, service_name: str, config: Dict) -> RecoveryResult:
        """Restart Docker container"""
        try:
            container_name = config['container_name']
            container = self.docker_client.containers.get(container_name)
            
            logger.info(f"Restarting container {container_name}")
            container.restart(timeout=30)
            
            # Wait for container to be healthy
            await asyncio.sleep(10)
            
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.RESTART,
                success=True,
                timestamp=datetime.now(),
                message=f"Container {container_name} restarted successfully"
            )
            
            # Reset failure counter and start time
            if service_name in self.service_health:
                self.service_health[service_name].consecutive_failures = 0
            self.service_start_times[service_name] = datetime.now()
            
            recovery_attempts.labels(
                service=service_name,
                action="restart",
                result="success"
            ).inc()
            
            logger.info(f"Container restart successful: {container_name}")
            
        except Exception as e:
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.RESTART,
                success=False,
                timestamp=datetime.now(),
                message=f"Container restart failed: {e}"
            )
            
            recovery_attempts.labels(
                service=service_name,
                action="restart",
                result="failure"
            ).inc()
            
            logger.error(f"Container restart failed: {e}")
            
        self.recovery_history.append(result)
        await self._store_recovery_evidence(result)
        
        return result
        
    async def _reconnect_service(self, service_name: str, config: Dict) -> RecoveryResult:
        """Attempt to reconnect service dependencies"""
        try:
            # Service-specific reconnection logic
            if service_name == "reasoning-service":
                # Trigger Redis reconnection
                await self._trigger_service_reconnect(config['port'], "/reconnect")
                
            elif service_name == "hybrid-memory-service":
                # Trigger database reconnection
                await self._trigger_service_reconnect(config['port'], "/reconnect")
                
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.RECONNECT,
                success=True,
                timestamp=datetime.now(),
                message=f"Service {service_name} reconnection triggered"
            )
            
            recovery_attempts.labels(
                service=service_name,
                action="reconnect",
                result="success"
            ).inc()
            
        except Exception as e:
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.RECONNECT,
                success=False,
                timestamp=datetime.now(),
                message=f"Reconnection failed: {e}"
            )
            
            recovery_attempts.labels(
                service=service_name,
                action="reconnect",
                result="failure"
            ).inc()
            
        self.recovery_history.append(result)
        await self._store_recovery_evidence(result)
        
        return result
        
    async def _trigger_service_reconnect(self, port: int, endpoint: str):
        """Trigger service reconnection endpoint"""
        url = f"http://localhost:{port}{endpoint}"
        async with self.session.post(url) as response:
            if response.status != 200:
                raise Exception(f"Reconnect endpoint returned {response.status}")
                
    async def _send_alert(self, service_name: str, health: ServiceHealth) -> RecoveryResult:
        """Send alert for service failure"""
        try:
            # Store alert in Redis
            alert = {
                "service": service_name,
                "status": health.status.value,
                "error": health.error_message,
                "consecutive_failures": health.consecutive_failures,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_client.lpush(
                "cognitive:alerts",
                json.dumps(alert)
            )
            
            # Trim to keep only last 100 alerts
            await self.redis_client.ltrim("cognitive:alerts", 0, 99)
            
            logger.warning(f"ALERT: Service {service_name} is {health.status.value}")
            
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.ALERT,
                success=True,
                timestamp=datetime.now(),
                message=f"Alert sent for {service_name}: {health.error_message}"
            )
            
            recovery_attempts.labels(
                service=service_name,
                action="alert",
                result="success"
            ).inc()
            
        except Exception as e:
            result = RecoveryResult(
                service=service_name,
                action=RecoveryAction.ALERT,
                success=False,
                timestamp=datetime.now(),
                message=f"Alert failed: {e}"
            )
            
            recovery_attempts.labels(
                service=service_name,
                action="alert",
                result="failure"
            ).inc()
            
        self.recovery_history.append(result)
        
        return result
        
    async def _store_recovery_evidence(self, result: RecoveryResult):
        """Store recovery action evidence"""
        try:
            # Store in file system
            evidence_file = self.evidence_dir / f"recovery_{result.service}_{int(result.timestamp.timestamp())}.json"
            with open(evidence_file, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
                
            # Store in Redis
            await self.redis_client.lpush(
                f"cognitive:recovery:{result.service}",
                json.dumps(result.to_dict())
            )
            
            # Keep only last 50 recovery attempts per service
            await self.redis_client.ltrim(f"cognitive:recovery:{result.service}", 0, 49)
            
        except Exception as e:
            logger.error(f"Failed to store recovery evidence: {e}")
            
    async def collect_evidence(self):
        """Collect comprehensive health evidence"""
        evidence = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": self._calculate_overall_health(),
            "services": {},
            "recent_recoveries": [r.to_dict() for r in self.recovery_history[-10:]],
            "alerts": []
        }
        
        # Collect service health
        for service_name, health in self.service_health.items():
            evidence["services"][service_name] = health.to_dict()
            
        # Collect recent alerts
        try:
            alerts = await self.redis_client.lrange("cognitive:alerts", 0, 9)
            evidence["alerts"] = [json.loads(alert) for alert in alerts]
        except Exception:
            pass
            
        # Store evidence
        evidence_file = self.evidence_dir / f"health_evidence_{int(time.time())}.json"
        with open(evidence_file, 'w') as f:
            json.dump(evidence, f, indent=2)
            
        # Clean old evidence files (keep last 100)
        evidence_files = sorted(self.evidence_dir.glob("health_evidence_*.json"))
        for old_file in evidence_files[:-100]:
            old_file.unlink()
            
        return evidence
        
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health"""
        if not self.service_health:
            return "unknown"
            
        critical_services = [s for s, c in self.SERVICES.items() if c.get('critical', False)]
        critical_healthy = all(
            self.service_health.get(s, ServiceHealth(
                name=s,
                status=HealthStatus.UNKNOWN,
                endpoint="",
                port=0,
                last_check=datetime.now(),
                response_time_ms=-1
            )).status == HealthStatus.HEALTHY
            for s in critical_services
        )
        
        if critical_healthy:
            # Check non-critical services
            total = len(self.service_health)
            healthy = sum(1 for h in self.service_health.values() 
                         if h.status == HealthStatus.HEALTHY)
            
            if healthy == total:
                return "healthy"
            elif healthy >= total * 0.8:
                return "degraded"
            else:
                return "unhealthy"
        else:
            return "critical"
            
    async def run_health_checks(self):
        """Run health checks for all services"""
        tasks = []
        
        for service_name, config in self.SERVICES.items():
            task = self.check_service_health(service_name, config)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for recovery needs
        for service_name, config in self.SERVICES.items():
            health = self.service_health.get(service_name)
            
            if health and health.status != HealthStatus.HEALTHY:
                await self.perform_recovery(service_name, config)
                
        # Collect evidence
        await self.collect_evidence()
        
    async def get_dashboard_data(self) -> Dict:
        """Get data for health dashboard"""
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": self._calculate_overall_health(),
            "services": {
                name: health.to_dict() 
                for name, health in self.service_health.items()
            },
            "recovery_history": [
                r.to_dict() for r in self.recovery_history[-20:]
            ],
            "metrics": {
                "total_services": len(self.SERVICES),
                "healthy_services": sum(
                    1 for h in self.service_health.values() 
                    if h.status == HealthStatus.HEALTHY
                ),
                "total_recoveries": len(self.recovery_history),
                "successful_recoveries": sum(
                    1 for r in self.recovery_history if r.success
                )
            }
        }
        
    async def run(self):
        """Main monitoring loop"""
        await self.initialize()
        
        try:
            while True:
                try:
                    await self.run_health_checks()
                    logger.info(f"Health check completed. Overall: {self._calculate_overall_health()}")
                    
                except Exception as e:
                    logger.error(f"Error in health check cycle: {e}")
                    
                await asyncio.sleep(self.check_interval)
                
        finally:
            await self.cleanup()


# FastAPI application for health dashboard
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

app = FastAPI(title="Cognitive Services Health Monitor")
monitor: Optional[CognitiveServiceMonitor] = None


@app.on_event("startup")
async def startup_event():
    """Initialize monitor on startup"""
    global monitor
    monitor = CognitiveServiceMonitor()
    asyncio.create_task(monitor.run())
    

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "health-monitor"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/api/dashboard")
async def dashboard_api():
    """Dashboard API endpoint"""
    if monitor:
        return JSONResponse(content=await monitor.get_dashboard_data())
    return JSONResponse(
        content={"error": "Monitor not initialized"},
        status_code=503
    )


@app.get("/api/services/{service_name}")
async def service_details(service_name: str):
    """Get details for a specific service"""
    if monitor and service_name in monitor.service_health:
        return JSONResponse(
            content=monitor.service_health[service_name].to_dict()
        )
    return JSONResponse(
        content={"error": "Service not found"},
        status_code=404
    )


@app.post("/api/services/{service_name}/recover")
async def trigger_recovery(service_name: str):
    """Manually trigger recovery for a service"""
    if monitor and service_name in monitor.SERVICES:
        result = await monitor.perform_recovery(
            service_name, 
            monitor.SERVICES[service_name]
        )
        if result:
            return JSONResponse(content=result.to_dict())
        return JSONResponse(
            content={"message": "No recovery action needed"},
            status_code=200
        )
    return JSONResponse(
        content={"error": "Service not found"},
        status_code=404
    )


@app.get("/")
async def dashboard():
    """Health monitoring dashboard"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cognitive Services Health Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            h1 { color: #333; }
            .dashboard { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .service { margin: 10px 0; padding: 15px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
            .healthy { background: #d4edda; border: 1px solid #c3e6cb; }
            .unhealthy { background: #f8d7da; border: 1px solid #f5c6cb; }
            .degraded { background: #fff3cd; border: 1px solid #ffeeba; }
            .unknown { background: #e2e3e5; border: 1px solid #d6d8db; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .metric { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
            .metric-value { font-size: 2em; font-weight: bold; color: #007bff; }
            .recovery-btn { padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; }
            .recovery-btn:hover { background: #0056b3; }
            #overall-status { padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>🧠 Cognitive Services Health Monitor</h1>
        <div class="dashboard">
            <div id="overall-status"></div>
            <div class="metrics" id="metrics"></div>
            <h2>Service Status</h2>
            <div id="services"></div>
            <h2>Recent Recovery Actions</h2>
            <div id="recovery"></div>
        </div>
        
        <script>
            async function updateDashboard() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();
                    
                    // Update overall status
                    const overallDiv = document.getElementById('overall-status');
                    overallDiv.className = data.overall_health;
                    overallDiv.textContent = `Overall System Health: ${data.overall_health.toUpperCase()}`;
                    
                    // Update metrics
                    const metricsDiv = document.getElementById('metrics');
                    metricsDiv.innerHTML = `
                        <div class="metric">
                            <div>Total Services</div>
                            <div class="metric-value">${data.metrics.total_services}</div>
                        </div>
                        <div class="metric">
                            <div>Healthy Services</div>
                            <div class="metric-value">${data.metrics.healthy_services}</div>
                        </div>
                        <div class="metric">
                            <div>Total Recoveries</div>
                            <div class="metric-value">${data.metrics.total_recoveries}</div>
                        </div>
                        <div class="metric">
                            <div>Successful Recoveries</div>
                            <div class="metric-value">${data.metrics.successful_recoveries}</div>
                        </div>
                    `;
                    
                    // Update services
                    const servicesDiv = document.getElementById('services');
                    servicesDiv.innerHTML = '';
                    
                    for (const [name, health] of Object.entries(data.services)) {
                        const serviceDiv = document.createElement('div');
                        serviceDiv.className = `service ${health.status}`;
                        serviceDiv.innerHTML = `
                            <div>
                                <strong>${name}</strong>
                                <br>Status: ${health.status}
                                <br>Response Time: ${health.response_time_ms.toFixed(2)}ms
                                <br>Uptime: ${(health.uptime_seconds / 60).toFixed(1)} minutes
                                ${health.error_message ? `<br>Error: ${health.error_message}` : ''}
                            </div>
                            <button class="recovery-btn" onclick="triggerRecovery('${name}')">Recover</button>
                        `;
                        servicesDiv.appendChild(serviceDiv);
                    }
                    
                    // Update recovery history
                    const recoveryDiv = document.getElementById('recovery');
                    recoveryDiv.innerHTML = '';
                    
                    if (data.recovery_history.length > 0) {
                        const list = document.createElement('ul');
                        data.recovery_history.slice(-5).reverse().forEach(recovery => {
                            const item = document.createElement('li');
                            item.textContent = `${recovery.service} - ${recovery.action} - ${recovery.success ? 'Success' : 'Failed'} - ${recovery.message}`;
                            list.appendChild(item);
                        });
                        recoveryDiv.appendChild(list);
                    } else {
                        recoveryDiv.textContent = 'No recent recovery actions';
                    }
                    
                } catch (error) {
                    console.error('Failed to update dashboard:', error);
                }
            }
            
            async function triggerRecovery(serviceName) {
                try {
                    const response = await fetch(`/api/services/${serviceName}/recover`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    alert(`Recovery action: ${result.message || 'No action needed'}`);
                    updateDashboard();
                } catch (error) {
                    alert('Failed to trigger recovery: ' + error);
                }
            }
            
            // Update dashboard every 10 seconds
            updateDashboard();
            setInterval(updateDashboard, 10000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    # Run the monitoring service
    uvicorn.run(app, host="0.0.0.0", port=8888)