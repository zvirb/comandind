#!/usr/bin/env python3
"""
Comprehensive Health Monitoring Service for AI Workflow Engine
Provides unified health monitoring, metrics export, and automated recovery
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import aiohttp
from aiohttp import web
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import docker
from docker.errors import DockerException
import redis.asyncio as redis
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
service_health_gauge = Gauge(
    'service_health_status',
    'Health status of services (1=healthy, 0=unhealthy)',
    ['service', 'component']
)

service_response_time = Histogram(
    'service_health_check_duration_seconds',
    'Duration of health check requests',
    ['service']
)

service_check_total = Counter(
    'service_health_checks_total',
    'Total number of health checks performed',
    ['service', 'status']
)

recovery_attempts = Counter(
    'service_recovery_attempts_total',
    'Total number of recovery attempts',
    ['service', 'action']
)

alert_triggered = Counter(
    'health_alerts_triggered_total',
    'Total number of health alerts triggered',
    ['service', 'severity']
)

# Service configuration
SERVICES = {
    'learning-service': {
        'url': 'http://learning-service:8003/health',
        'port': 8003,
        'container_name': 'ai_workflow_engine-learning-service-1',
        'critical': True,
        'max_retries': 3,
        'timeout': 5
    },
    'reasoning-service': {
        'url': 'http://reasoning-service:8005/health',
        'port': 8005,
        'container_name': 'ai_workflow_engine-reasoning-service-1',
        'critical': True,
        'max_retries': 3,
        'timeout': 5
    },
    'coordination-service': {
        'url': 'http://coordination-service:8001/health',
        'port': 8001,
        'container_name': 'ai_workflow_engine-coordination-service-1',
        'critical': True,
        'max_retries': 3,
        'timeout': 5
    },
    'hybrid-memory-service': {
        'url': 'http://hybrid-memory-service:8002/health',
        'port': 8002,
        'container_name': 'ai_workflow_engine-hybrid-memory-service-1',
        'critical': True,
        'max_retries': 3,
        'timeout': 5
    },
    'perception-service': {
        'url': 'http://perception-service:8004/health',
        'port': 8004,
        'container_name': 'ai_workflow_engine-perception-service-1',
        'critical': False,
        'max_retries': 2,
        'timeout': 5
    },
    'api': {
        'url': 'http://api:8000/health',
        'port': 8000,
        'container_name': 'ai_workflow_engine-api-1',
        'critical': True,
        'max_retries': 3,
        'timeout': 5
    },
    'infrastructure-recovery-service': {
        'url': 'http://infrastructure-recovery-service:8010/health',
        'port': 8010,
        'container_name': 'ai_workflow_engine-infrastructure-recovery-service-1',
        'critical': False,
        'max_retries': 2,
        'timeout': 5
    }
}

# Infrastructure services
INFRASTRUCTURE_SERVICES = {
    'redis': {
        'host': 'redis',
        'port': 6379,
        'critical': True
    },
    'postgres': {
        'host': 'postgres',
        'port': 5432,
        'critical': True
    },
    'qdrant': {
        'url': 'http://qdrant:6333/health',
        'critical': True
    },
    'neo4j': {
        'url': 'http://neo4j:7474',
        'critical': True
    },
    'ollama': {
        'url': 'http://ollama:11434/api/tags',
        'critical': False
    }
}


class HealthMonitor:
    """Comprehensive health monitoring with automated recovery"""
    
    def __init__(self):
        self.docker_client = None
        self.redis_client = None
        self.session = None
        self.health_history = defaultdict(list)
        self.recovery_in_progress = set()
        self.last_alert = {}
        self.alert_cooldown = 300  # 5 minutes between alerts
        
    async def initialize(self):
        """Initialize connections and clients"""
        try:
            # Initialize Docker client
            self.docker_client = docker.from_env()
            
            # Initialize Redis client
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                decode_responses=True
            )
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            
            logger.info("Health monitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize health monitor: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def check_service_health(self, service_name: str, config: Dict) -> Dict[str, Any]:
        """Check health of a single service"""
        start_time = time.time()
        result = {
            'service': service_name,
            'timestamp': datetime.utcnow().isoformat(),
            'healthy': False,
            'response_time': 0,
            'details': {},
            'error': None
        }
        
        try:
            async with self.session.get(
                config['url'],
                timeout=aiohttp.ClientTimeout(total=config.get('timeout', 5))
            ) as response:
                result['response_time'] = time.time() - start_time
                result['status_code'] = response.status
                
                if response.status == 200:
                    data = await response.json()
                    result['healthy'] = data.get('status') == 'healthy'
                    result['details'] = data
                else:
                    result['error'] = f"HTTP {response.status}"
                    
        except asyncio.TimeoutError:
            result['error'] = "Timeout"
        except aiohttp.ClientError as e:
            result['error'] = str(e)
        except Exception as e:
            result['error'] = f"Unexpected error: {e}"
        
        # Update metrics
        service_response_time.labels(service=service_name).observe(result['response_time'])
        service_check_total.labels(service=service_name, status='success' if result['healthy'] else 'failure').inc()
        service_health_gauge.labels(service=service_name, component='main').set(1 if result['healthy'] else 0)
        
        # Store in history
        self.health_history[service_name].append(result)
        if len(self.health_history[service_name]) > 100:
            self.health_history[service_name].pop(0)
        
        return result
    
    async def check_infrastructure_health(self, name: str, config: Dict) -> Dict[str, Any]:
        """Check health of infrastructure components"""
        result = {
            'component': name,
            'timestamp': datetime.utcnow().isoformat(),
            'healthy': False,
            'error': None
        }
        
        try:
            if name == 'redis':
                # Check Redis
                test_client = redis.Redis(
                    host=config['host'],
                    port=config['port'],
                    decode_responses=True
                )
                await test_client.ping()
                result['healthy'] = True
                await test_client.aclose()
                
            elif name == 'postgres':
                # Check PostgreSQL (simple TCP connection test)
                reader, writer = await asyncio.open_connection(
                    config['host'], config['port']
                )
                writer.close()
                await writer.wait_closed()
                result['healthy'] = True
                
            elif 'url' in config:
                # Check HTTP-based services
                async with self.session.get(
                    config['url'],
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    result['healthy'] = response.status in [200, 204]
                    
        except Exception as e:
            result['error'] = str(e)
        
        # Update metrics
        service_health_gauge.labels(service=f"infra_{name}", component='main').set(1 if result['healthy'] else 0)
        
        return result
    
    async def perform_recovery(self, service_name: str, config: Dict) -> bool:
        """Perform automated recovery actions for a service"""
        if service_name in self.recovery_in_progress:
            logger.info(f"Recovery already in progress for {service_name}")
            return False
        
        self.recovery_in_progress.add(service_name)
        recovery_successful = False
        
        try:
            container_name = config.get('container_name')
            if not container_name:
                logger.warning(f"No container name configured for {service_name}")
                return False
            
            # Try to restart the container
            logger.info(f"Attempting to restart {service_name} container: {container_name}")
            recovery_attempts.labels(service=service_name, action='restart').inc()
            
            try:
                container = self.docker_client.containers.get(container_name)
                container.restart(timeout=30)
                logger.info(f"Container {container_name} restarted successfully")
                
                # Wait for service to come up
                await asyncio.sleep(10)
                
                # Verify service is healthy
                health_check = await self.check_service_health(service_name, config)
                recovery_successful = health_check['healthy']
                
                if recovery_successful:
                    logger.info(f"Recovery successful for {service_name}")
                    await self.store_recovery_event(service_name, 'restart', 'success')
                else:
                    logger.warning(f"Service {service_name} still unhealthy after restart")
                    await self.store_recovery_event(service_name, 'restart', 'failed')
                    
            except docker.errors.NotFound:
                logger.error(f"Container {container_name} not found")
                recovery_attempts.labels(service=service_name, action='restart_failed').inc()
            except docker.errors.APIError as e:
                logger.error(f"Docker API error during recovery: {e}")
                recovery_attempts.labels(service=service_name, action='restart_error').inc()
                
        except Exception as e:
            logger.error(f"Recovery failed for {service_name}: {e}")
            recovery_attempts.labels(service=service_name, action='error').inc()
        finally:
            self.recovery_in_progress.discard(service_name)
        
        return recovery_successful
    
    async def store_recovery_event(self, service: str, action: str, result: str):
        """Store recovery event in Redis for analysis"""
        if self.redis_client:
            event = {
                'service': service,
                'action': action,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            try:
                await self.redis_client.lpush(
                    f"recovery_events:{service}",
                    json.dumps(event)
                )
                # Keep only last 100 events
                await self.redis_client.ltrim(f"recovery_events:{service}", 0, 99)
            except Exception as e:
                logger.error(f"Failed to store recovery event: {e}")
    
    async def trigger_alert(self, service: str, severity: str, message: str):
        """Trigger alert for service issues"""
        now = datetime.utcnow()
        last_alert_time = self.last_alert.get(service, datetime.min)
        
        # Check cooldown period
        if (now - last_alert_time).total_seconds() < self.alert_cooldown:
            return
        
        alert_triggered.labels(service=service, severity=severity).inc()
        self.last_alert[service] = now
        
        alert_data = {
            'service': service,
            'severity': severity,
            'message': message,
            'timestamp': now.isoformat()
        }
        
        # Store alert in Redis
        if self.redis_client:
            try:
                await self.redis_client.lpush(
                    'health_alerts',
                    json.dumps(alert_data)
                )
                await self.redis_client.ltrim('health_alerts', 0, 999)
            except Exception as e:
                logger.error(f"Failed to store alert: {e}")
        
        logger.warning(f"ALERT [{severity}] {service}: {message}")
    
    async def analyze_health_trends(self, service: str) -> Dict[str, Any]:
        """Analyze health trends for a service"""
        history = self.health_history.get(service, [])
        if not history:
            return {'trend': 'unknown', 'reliability': 0}
        
        recent_checks = history[-10:] if len(history) >= 10 else history
        healthy_count = sum(1 for check in recent_checks if check['healthy'])
        reliability = healthy_count / len(recent_checks)
        
        # Determine trend
        if len(history) < 3:
            trend = 'insufficient_data'
        else:
            recent_health = [check['healthy'] for check in history[-3:]]
            if all(recent_health):
                trend = 'stable_healthy'
            elif not any(recent_health):
                trend = 'critical'
            elif recent_health[-1] and not recent_health[0]:
                trend = 'recovering'
            elif not recent_health[-1] and recent_health[0]:
                trend = 'degrading'
            else:
                trend = 'unstable'
        
        return {
            'trend': trend,
            'reliability': reliability,
            'recent_failures': len(recent_checks) - healthy_count,
            'avg_response_time': sum(check['response_time'] for check in recent_checks) / len(recent_checks)
        }
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Check all services
                for service_name, config in SERVICES.items():
                    health = await self.check_service_health(service_name, config)
                    
                    if not health['healthy']:
                        # Analyze trends
                        trends = await self.analyze_health_trends(service_name)
                        
                        # Determine if recovery is needed
                        if trends['trend'] in ['critical', 'degrading'] and config.get('critical'):
                            await self.trigger_alert(
                                service_name,
                                'critical' if trends['trend'] == 'critical' else 'warning',
                                f"Service unhealthy - Trend: {trends['trend']}, Reliability: {trends['reliability']:.2%}"
                            )
                            
                            # Attempt recovery for critical services
                            if trends['reliability'] < 0.5:  # Less than 50% healthy
                                await self.perform_recovery(service_name, config)
                
                # Check infrastructure
                for infra_name, config in INFRASTRUCTURE_SERVICES.items():
                    health = await self.check_infrastructure_health(infra_name, config)
                    if not health['healthy'] and config.get('critical'):
                        await self.trigger_alert(
                            f"infrastructure_{infra_name}",
                            'critical',
                            f"Infrastructure component {infra_name} is unhealthy"
                        )
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)


class HealthAPI:
    """API endpoints for health monitoring"""
    
    def __init__(self, monitor: HealthMonitor):
        self.monitor = monitor
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.metrics_endpoint)
        self.app.router.add_get('/api/services', self.get_services_status)
        self.app.router.add_get('/api/services/{service}', self.get_service_detail)
        self.app.router.add_post('/api/services/{service}/recover', self.trigger_recovery)
        self.app.router.add_get('/api/alerts', self.get_alerts)
        self.app.router.add_get('/api/trends/{service}', self.get_trends)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    async def metrics_endpoint(self, request):
        """Prometheus metrics endpoint"""
        metrics = generate_latest()
        # Extract only the media type without charset parameter for aiohttp compatibility
        content_type = CONTENT_TYPE_LATEST.split(';')[0].strip()
        return web.Response(body=metrics, content_type=content_type, charset='utf-8')
    
    async def get_services_status(self, request):
        """Get status of all services"""
        statuses = {}
        
        for service_name in SERVICES:
            history = self.monitor.health_history.get(service_name, [])
            if history:
                latest = history[-1]
                trends = await self.monitor.analyze_health_trends(service_name)
                statuses[service_name] = {
                    'healthy': latest['healthy'],
                    'last_check': latest['timestamp'],
                    'response_time': latest['response_time'],
                    'trend': trends['trend'],
                    'reliability': trends['reliability']
                }
            else:
                statuses[service_name] = {
                    'healthy': None,
                    'last_check': None,
                    'trend': 'unknown'
                }
        
        return web.json_response(statuses)
    
    async def get_service_detail(self, request):
        """Get detailed status of a specific service"""
        service = request.match_info['service']
        
        if service not in SERVICES:
            return web.json_response({'error': 'Service not found'}, status=404)
        
        history = self.monitor.health_history.get(service, [])
        trends = await self.monitor.analyze_health_trends(service)
        
        # Get recovery events
        recovery_events = []
        if self.monitor.redis_client:
            try:
                events = await self.monitor.redis_client.lrange(
                    f"recovery_events:{service}", 0, 9
                )
                recovery_events = [json.loads(event) for event in events]
            except Exception as e:
                logger.error(f"Failed to fetch recovery events: {e}")
        
        return web.json_response({
            'service': service,
            'configuration': SERVICES[service],
            'current_health': history[-1] if history else None,
            'trends': trends,
            'history': history[-20:],  # Last 20 checks
            'recovery_events': recovery_events,
            'recovery_in_progress': service in self.monitor.recovery_in_progress
        })
    
    async def trigger_recovery(self, request):
        """Manually trigger recovery for a service"""
        service = request.match_info['service']
        
        if service not in SERVICES:
            return web.json_response({'error': 'Service not found'}, status=404)
        
        success = await self.monitor.perform_recovery(service, SERVICES[service])
        
        return web.json_response({
            'service': service,
            'recovery_triggered': True,
            'success': success
        })
    
    async def get_alerts(self, request):
        """Get recent alerts"""
        alerts = []
        if self.monitor.redis_client:
            try:
                alert_data = await self.monitor.redis_client.lrange('health_alerts', 0, 49)
                alerts = [json.loads(alert) for alert in alert_data]
            except Exception as e:
                logger.error(f"Failed to fetch alerts: {e}")
        
        return web.json_response({'alerts': alerts})
    
    async def get_trends(self, request):
        """Get health trends for a service"""
        service = request.match_info['service']
        
        if service not in SERVICES:
            return web.json_response({'error': 'Service not found'}, status=404)
        
        trends = await self.monitor.analyze_health_trends(service)
        return web.json_response(trends)


async def main():
    """Main entry point"""
    monitor = HealthMonitor()
    await monitor.initialize()
    
    # Create API
    api = HealthAPI(monitor)
    
    # Start monitoring loop
    monitor_task = asyncio.create_task(monitor.monitor_loop())
    
    # Start web server
    runner = web.AppRunner(api.app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8888)
    await site.start()
    
    logger.info("Health monitoring service started on port 8888")
    
    try:
        await asyncio.gather(monitor_task)
    except KeyboardInterrupt:
        logger.info("Shutting down health monitor")
    finally:
        await monitor.cleanup()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())