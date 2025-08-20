"""ML Service Bus - Centralized ML Service Coordination

Provides unified access to all ML services for agent orchestration with
intelligent load balancing, fallback mechanisms, and performance optimization.

Key Features:
- Unified API for all ML services (reasoning, perception, memory, coordination, learning)
- Intelligent service discovery and health monitoring
- Load balancing and request routing optimization
- Fallback mechanisms and graceful degradation
- Performance metrics and optimization
- Circuit breaker patterns for reliability
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
import structlog
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger(__name__)

# Metrics
ML_SERVICE_REQUESTS = Counter(
    'ml_service_bus_requests_total',
    'Total ML service requests',
    ['service', 'endpoint', 'status']
)
ML_SERVICE_LATENCY = Histogram(
    'ml_service_bus_latency_seconds',
    'ML service request latency',
    ['service', 'endpoint']
)
ML_SERVICE_HEALTH = Gauge(
    'ml_service_bus_health_score',
    'ML service health scores',
    ['service']
)

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

@dataclass
class ServiceEndpoint:
    """ML service endpoint configuration."""
    name: str
    base_url: str
    health_endpoint: str = "/health"
    timeout: float = 30.0
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    priority: int = 1  # Lower number = higher priority
    
    # Runtime state
    status: ServiceStatus = field(default=ServiceStatus.OFFLINE)
    last_health_check: float = field(default=0.0)
    consecutive_failures: int = field(default=0)
    circuit_breaker_until: float = field(default=0.0)
    avg_response_time: float = field(default=0.0)
    success_rate: float = field(default=1.0)

@dataclass
class MLRequest:
    """Unified ML service request."""
    service: str
    endpoint: str
    data: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid4()))
    timeout: Optional[float] = None
    priority: int = 1  # Lower number = higher priority
    require_high_confidence: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MLResponse:
    """Unified ML service response."""
    success: bool
    data: Dict[str, Any]
    service: str
    endpoint: str
    request_id: str
    response_time_ms: float
    confidence_score: Optional[float] = None
    service_health: ServiceStatus = ServiceStatus.HEALTHY
    error_message: Optional[str] = None
    fallback_used: bool = False

class MLServiceBus:
    """Centralized ML service coordination and communication bus."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize ML Service Bus with configuration."""
        self.config = config or {}
        self.services: Dict[str, ServiceEndpoint] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = self.config.get('health_check_interval', 30.0)
        self._load_balancing_strategy = self.config.get('load_balancing', 'round_robin')
        
        # Default service configurations
        self._default_services = {
            'reasoning': {
                'base_url': 'http://reasoning-service:8003',
                'timeout': 30.0,
                'priority': 1
            },
            'perception': {
                'base_url': 'http://perception-service:8004',
                'timeout': 30.0,
                'priority': 2
            },
            'memory': {
                'base_url': 'http://memory-service:8005',
                'timeout': 20.0,
                'priority': 1
            },
            'coordination': {
                'base_url': 'http://coordination-service:8001',
                'timeout': 25.0,
                'priority': 1
            },
            'learning': {
                'base_url': 'http://learning-service:8002',
                'timeout': 35.0,
                'priority': 3
            }
        }
        
        # Initialize services from configuration
        self._initialize_services()
        
        logger.info("ML Service Bus initialized", 
                   services=list(self.services.keys()),
                   load_balancing=self._load_balancing_strategy)
    
    def _initialize_services(self):
        """Initialize service endpoints from configuration."""
        # Add default services
        for service_name, config in self._default_services.items():
            self.services[service_name] = ServiceEndpoint(
                name=service_name,
                base_url=config['base_url'],
                timeout=config['timeout'],
                priority=config['priority']
            )
        
        # Override with user configuration
        user_services = self.config.get('services', {})
        for service_name, config in user_services.items():
            if service_name in self.services:
                # Update existing service
                endpoint = self.services[service_name]
                endpoint.base_url = config.get('base_url', endpoint.base_url)
                endpoint.timeout = config.get('timeout', endpoint.timeout)
                endpoint.priority = config.get('priority', endpoint.priority)
            else:
                # Add new service
                self.services[service_name] = ServiceEndpoint(
                    name=service_name,
                    base_url=config['base_url'],
                    timeout=config.get('timeout', 30.0),
                    priority=config.get('priority', 5)
                )
    
    async def start(self):
        """Start the ML Service Bus."""
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=60.0)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        # Initial health check
        await self._check_all_services_health()
        
        logger.info("ML Service Bus started", healthy_services=self._get_healthy_services())
    
    async def stop(self):
        """Stop the ML Service Bus."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("ML Service Bus stopped")
    
    async def request(self, ml_request: MLRequest) -> MLResponse:
        """Execute ML service request with intelligent routing and fallbacks."""
        start_time = time.time()
        
        logger.info("Processing ML request", 
                   service=ml_request.service,
                   endpoint=ml_request.endpoint,
                   request_id=ml_request.request_id)
        
        # Validate service exists
        if ml_request.service not in self.services:
            return MLResponse(
                success=False,
                data={},
                service=ml_request.service,
                endpoint=ml_request.endpoint,
                request_id=ml_request.request_id,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Service '{ml_request.service}' not configured"
            )
        
        # Get service endpoint
        service = self.services[ml_request.service]
        
        # Check circuit breaker
        if self._is_circuit_breaker_open(service):
            logger.warning("Circuit breaker open for service", service=ml_request.service)
            return await self._handle_circuit_breaker_response(ml_request, start_time)
        
        # Execute request with retries
        max_retries = service.max_retries
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await self._execute_request(service, ml_request)
                
                # Update service health metrics
                response_time = (time.time() - start_time) * 1000
                self._update_service_metrics(service, True, response_time)
                
                # Record metrics
                ML_SERVICE_REQUESTS.labels(
                    service=ml_request.service,
                    endpoint=ml_request.endpoint,
                    status='success'
                ).inc()
                ML_SERVICE_LATENCY.labels(
                    service=ml_request.service,
                    endpoint=ml_request.endpoint
                ).observe(response_time / 1000)
                
                return MLResponse(
                    success=True,
                    data=response,
                    service=ml_request.service,
                    endpoint=ml_request.endpoint,
                    request_id=ml_request.request_id,
                    response_time_ms=response_time,
                    confidence_score=response.get('confidence_score'),
                    service_health=service.status
                )
                
            except Exception as e:
                last_error = e
                response_time = (time.time() - start_time) * 1000
                self._update_service_metrics(service, False, response_time)
                
                logger.warning("ML request attempt failed", 
                              service=ml_request.service,
                              attempt=attempt + 1,
                              error=str(e))
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All attempts failed
        response_time = (time.time() - start_time) * 1000
        ML_SERVICE_REQUESTS.labels(
            service=ml_request.service,
            endpoint=ml_request.endpoint,
            status='error'
        ).inc()
        
        return MLResponse(
            success=False,
            data={},
            service=ml_request.service,
            endpoint=ml_request.endpoint,
            request_id=ml_request.request_id,
            response_time_ms=response_time,
            service_health=service.status,
            error_message=str(last_error)
        )
    
    async def _execute_request(self, service: ServiceEndpoint, ml_request: MLRequest) -> Dict[str, Any]:
        """Execute HTTP request to ML service."""
        url = f"{service.base_url.rstrip('/')}/{ml_request.endpoint.lstrip('/')}"
        timeout = ml_request.timeout or service.timeout
        
        headers = {
            'Content-Type': 'application/json',
            'X-Request-ID': ml_request.request_id,
            'X-ML-Priority': str(ml_request.priority)
        }
        
        async with self.session.post(
            url,
            json=ml_request.data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    def _is_circuit_breaker_open(self, service: ServiceEndpoint) -> bool:
        """Check if circuit breaker is open for service."""
        if service.consecutive_failures >= service.circuit_breaker_threshold:
            if time.time() < service.circuit_breaker_until:
                return True
            else:
                # Reset circuit breaker
                service.consecutive_failures = 0
                service.circuit_breaker_until = 0.0
        return False
    
    async def _handle_circuit_breaker_response(self, ml_request: MLRequest, start_time: float) -> MLResponse:
        """Handle circuit breaker response with fallback."""
        response_time = (time.time() - start_time) * 1000
        
        # Try to find fallback service
        fallback_response = await self._try_fallback_service(ml_request)
        if fallback_response:
            fallback_response.fallback_used = True
            return fallback_response
        
        return MLResponse(
            success=False,
            data={},
            service=ml_request.service,
            endpoint=ml_request.endpoint,
            request_id=ml_request.request_id,
            response_time_ms=response_time,
            error_message="Service unavailable (circuit breaker open) and no fallback available"
        )
    
    async def _try_fallback_service(self, ml_request: MLRequest) -> Optional[MLResponse]:
        """Try to find and use fallback service."""
        # For now, implement simple fallback logic
        # This could be enhanced with more sophisticated fallback strategies
        
        if ml_request.service == 'reasoning' and 'memory' in self.services:
            # Use memory service for simple reasoning tasks
            fallback_request = MLRequest(
                service='memory',
                endpoint='search',
                data={'query': str(ml_request.data), 'limit': 5},
                request_id=ml_request.request_id
            )
            return await self.request(fallback_request)
        
        return None
    
    def _update_service_metrics(self, service: ServiceEndpoint, success: bool, response_time: float):
        """Update service health metrics."""
        if success:
            service.consecutive_failures = 0
            service.status = ServiceStatus.HEALTHY
        else:
            service.consecutive_failures += 1
            if service.consecutive_failures >= service.circuit_breaker_threshold:
                service.status = ServiceStatus.UNHEALTHY
                service.circuit_breaker_until = time.time() + service.circuit_breaker_timeout
            elif service.consecutive_failures >= 2:
                service.status = ServiceStatus.DEGRADED
        
        # Update response time (exponential moving average)
        alpha = 0.1
        service.avg_response_time = (alpha * response_time + 
                                   (1 - alpha) * service.avg_response_time)
        
        # Update health metric
        health_score = 1.0 if service.status == ServiceStatus.HEALTHY else (
            0.5 if service.status == ServiceStatus.DEGRADED else 0.0
        )
        ML_SERVICE_HEALTH.labels(service=service.name).set(health_score)
    
    async def _health_monitor(self):
        """Background task for continuous health monitoring."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_services_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health monitor error", error=str(e))
    
    async def _check_all_services_health(self):
        """Check health of all services."""
        tasks = []
        for service_name, service in self.services.items():
            task = asyncio.create_task(self._check_service_health(service))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service_health(self, service: ServiceEndpoint):
        """Check health of individual service."""
        try:
            url = f"{service.base_url.rstrip('/')}/{service.health_endpoint.lstrip('/')}"
            
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10.0)
            ) as response:
                if response.status == 200:
                    health_data = await response.json()
                    if health_data.get('status') == 'healthy':
                        service.status = ServiceStatus.HEALTHY
                        service.consecutive_failures = 0
                    else:
                        service.status = ServiceStatus.DEGRADED
                else:
                    service.status = ServiceStatus.UNHEALTHY
                    service.consecutive_failures += 1
                    
        except Exception as e:
            service.status = ServiceStatus.OFFLINE
            service.consecutive_failures += 1
            logger.debug("Service health check failed", 
                        service=service.name, error=str(e))
        
        service.last_health_check = time.time()
        
        # Update Prometheus metric
        health_score = {
            ServiceStatus.HEALTHY: 1.0,
            ServiceStatus.DEGRADED: 0.5,
            ServiceStatus.UNHEALTHY: 0.1,
            ServiceStatus.OFFLINE: 0.0
        }.get(service.status, 0.0)
        
        ML_SERVICE_HEALTH.labels(service=service.name).set(health_score)
    
    def _get_healthy_services(self) -> List[str]:
        """Get list of healthy services."""
        return [
            name for name, service in self.services.items()
            if service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
        ]
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        return {
            name: {
                'status': service.status.value,
                'base_url': service.base_url,
                'last_health_check': service.last_health_check,
                'consecutive_failures': service.consecutive_failures,
                'avg_response_time': service.avg_response_time,
                'priority': service.priority
            }
            for name, service in self.services.items()
        }
    
    async def batch_request(self, requests: List[MLRequest]) -> List[MLResponse]:
        """Execute multiple ML requests concurrently."""
        tasks = [self.request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append(MLResponse(
                    success=False,
                    data={},
                    service=requests[i].service,
                    endpoint=requests[i].endpoint,
                    request_id=requests[i].request_id,
                    response_time_ms=0,
                    error_message=str(response)
                ))
            else:
                results.append(response)
        
        return results

# Global ML Service Bus instance
_ml_service_bus: Optional[MLServiceBus] = None

async def get_ml_service_bus(config: Dict[str, Any] = None) -> MLServiceBus:
    """Get or create global ML Service Bus instance."""
    global _ml_service_bus
    
    if _ml_service_bus is None:
        _ml_service_bus = MLServiceBus(config)
        await _ml_service_bus.start()
    
    return _ml_service_bus

async def shutdown_ml_service_bus():
    """Shutdown global ML Service Bus instance."""
    global _ml_service_bus
    
    if _ml_service_bus:
        await _ml_service_bus.stop()
        _ml_service_bus = None

# Context manager for ML Service Bus
@asynccontextmanager
async def ml_service_bus_context(config: Dict[str, Any] = None):
    """Context manager for ML Service Bus lifecycle."""
    bus = MLServiceBus(config)
    await bus.start()
    try:
        yield bus
    finally:
        await bus.stop()