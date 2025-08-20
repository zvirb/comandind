#!/usr/bin/env python3
"""
API Gateway Health Monitor with Circuit Breaker Implementation
Monitors service health and implements circuit breaker patterns for resilient routing.
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import yaml
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class CircuitBreaker:
    """Circuit breaker implementation for service health monitoring"""
    
    def __init__(self, service_name: str, failure_threshold: int = 5, 
                 timeout: int = 30, reset_timeout: int = 60, 
                 half_open_max_calls: int = 3):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        
    def can_execute(self) -> bool:
        """Check if service call can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit breaker for {self.service_name} moved to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
            
    def record_success(self):
        """Record successful service call"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker for {self.service_name} moved to CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
            
    def record_failure(self):
        """Record failed service call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {self.service_name} moved to OPEN (half-open failure)")
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {self.service_name} moved to OPEN (threshold reached)")
            
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        return time.time() - self.last_failure_time >= self.reset_timeout
        
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "can_execute": self.can_execute()
        }

class GatewayHealthMonitor:
    """API Gateway health monitoring with circuit breaker patterns"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/home/marku/ai_workflow_engine/config/service_routing.yml"
        self.config = self._load_config()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_status: Dict[str, ServiceStatus] = {}
        self.last_health_check: Dict[str, float] = {}
        
        # Initialize circuit breakers
        self._initialize_circuit_breakers()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load service routing configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file loading fails"""
        return {
            "services": {
                "voice-interaction-service": {"container": "voice-interaction-service:8006"},
                "chat-service": {"container": "chat-service:8007"},
                "coordination-service": {"container": "coordination-service:8001"},
                "hybrid-memory-service": {"container": "hybrid-memory-service:8002"},
            },
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 5,
                "timeout": 30,
                "reset_timeout": 60,
                "half_open_max_calls": 3
            },
            "health_monitoring": {
                "enabled": True,
                "check_interval": 30,
                "timeout": 10,
                "retry_attempts": 3,
                "unhealthy_threshold": 3
            }
        }
        
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all services"""
        cb_config = self.config.get("circuit_breaker", {})
        
        for service_name in self.config.get("services", {}):
            self.circuit_breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                failure_threshold=cb_config.get("failure_threshold", 5),
                timeout=cb_config.get("timeout", 30),
                reset_timeout=cb_config.get("reset_timeout", 60),
                half_open_max_calls=cb_config.get("half_open_max_calls", 3)
            )
            self.service_status[service_name] = ServiceStatus.UNKNOWN
            
    async def check_service_health(self, service_name: str, container: str) -> bool:
        """Check health of a specific service"""
        if not self.circuit_breakers[service_name].can_execute():
            logger.debug(f"Circuit breaker open for {service_name}, skipping health check")
            return False
            
        try:
            # Extract host and port from container string
            if ":" in container:
                host, port = container.split(":")
            else:
                host, port = container, "80"
                
            # Construct health check URL
            health_url = f"http://{host}:{port}/health"
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.get("health_monitoring", {}).get("timeout", 10)
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Health check passed for {service_name}: {data.get('status')}")
                        self.circuit_breakers[service_name].record_success()
                        self.service_status[service_name] = ServiceStatus.HEALTHY
                        self.last_health_check[service_name] = time.time()
                        return True
                    else:
                        logger.warning(f"Health check failed for {service_name}: HTTP {response.status}")
                        self.circuit_breakers[service_name].record_failure()
                        self.service_status[service_name] = ServiceStatus.UNHEALTHY
                        return False
                        
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {service_name}")
            self.circuit_breakers[service_name].record_failure()
            self.service_status[service_name] = ServiceStatus.UNHEALTHY
            return False
        except Exception as e:
            logger.error(f"Health check error for {service_name}: {e}")
            self.circuit_breakers[service_name].record_failure()
            self.service_status[service_name] = ServiceStatus.UNHEALTHY
            return False
            
    async def monitor_all_services(self):
        """Monitor health of all configured services"""
        services = self.config.get("services", {})
        tasks = []
        
        for service_name, service_config in services.items():
            container = service_config.get("container", "")
            if container:
                task = self.check_service_health(service_name, container)
                tasks.append((service_name, task))
                
        # Execute all health checks concurrently
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Log results
        for i, (service_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Health check exception for {service_name}: {result}")
                self.circuit_breakers[service_name].record_failure()
                self.service_status[service_name] = ServiceStatus.UNHEALTHY
            elif result:
                logger.info(f"✓ {service_name} is healthy")
            else:
                logger.warning(f"✗ {service_name} is unhealthy")
                
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall gateway and service status"""
        healthy_services = sum(1 for status in self.service_status.values() 
                             if status == ServiceStatus.HEALTHY)
        total_services = len(self.service_status)
        
        overall_health = "healthy" if healthy_services == total_services else "degraded"
        if healthy_services == 0:
            overall_health = "critical"
            
        return {
            "overall_health": overall_health,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "services": {
                name: {
                    "status": status.value,
                    "circuit_breaker": cb.get_status(),
                    "last_check": self.last_health_check.get(name, 0)
                }
                for name, (status, cb) in zip(
                    self.service_status.items(),
                    [(status, self.circuit_breakers[name]) for name, status in self.service_status.items()]
                )
            },
            "timestamp": time.time(),
            "config_loaded": bool(self.config)
        }
        
    def get_degradation_message(self, service_name: str) -> str:
        """Get user-friendly degradation message for service"""
        degradation_messages = self.config.get("health_monitoring", {}).get("degradation_messages", {})
        return degradation_messages.get(
            service_name, 
            f"{service_name} temporarily offline. Some functionality may be limited."
        )
        
    async def run_monitoring_loop(self):
        """Run continuous health monitoring loop"""
        check_interval = self.config.get("health_monitoring", {}).get("check_interval", 30)
        
        logger.info(f"Starting API Gateway health monitoring (interval: {check_interval}s)")
        
        while True:
            try:
                await self.monitor_all_services()
                
                # Log overall status periodically
                status = self.get_overall_status()
                logger.info(f"Gateway Status: {status['overall_health']} "
                          f"({status['healthy_services']}/{status['total_services']} services healthy)")
                
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Health monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)

async def main():
    """Main entry point"""
    # Get config path from environment or use default
    config_path = os.getenv("GATEWAY_CONFIG_PATH", "/home/marku/ai_workflow_engine/config/service_routing.yml")
    
    monitor = GatewayHealthMonitor(config_path)
    
    # Run initial health check
    logger.info("Running initial health check...")
    await monitor.monitor_all_services()
    
    # Print initial status
    status = monitor.get_overall_status()
    print(json.dumps(status, indent=2))
    
    # If running as script (not imported), start monitoring loop
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        await monitor.run_monitoring_loop()

if __name__ == "__main__":
    asyncio.run(main())