"""
Security-Enhanced Circuit Breaker Middleware

This middleware implements advanced circuit breaker patterns for authentication
security with comprehensive monitoring and proactive alerting.

Features:
- Redis connectivity circuit breaker
- Authentication failure rate monitoring  
- Security event logging
- Prometheus metrics integration
- Real-time alerting capabilities
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, Enum as PrometheusEnum

from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = 0
    HALF_OPEN = 1  
    OPEN = 2

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 30
    success_threshold: int = 3
    timeout: int = 10
    monitoring_window: int = 60

@dataclass  
class SecurityMetrics:
    total_requests: int = 0
    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0
    recovery_attempts: int = 0
    loop_prevention_triggers: int = 0
    security_violations: Dict[str, int] = field(default_factory=dict)

# Prometheus metrics for security monitoring
auth_circuit_state = PrometheusEnum(
    'circuit_breaker_state',
    'Current state of the authentication circuit breaker',
    ['service'],
    states=['CLOSED', 'HALF_OPEN', 'OPEN']
)

auth_requests_total = Counter(
    'circuit_breaker_requests_total',
    'Total requests processed by circuit breaker',
    ['service', 'status']
)

auth_failures_total = Counter(
    'circuit_breaker_failures_total', 
    'Total failures detected by circuit breaker',
    ['service', 'failure_type']
)

auth_recovery_time = Histogram(
    'circuit_breaker_recovery_time_seconds',
    'Time taken for circuit breaker recovery',
    ['service']
)

auth_loop_prevention_total = Counter(
    'circuit_breaker_loop_prevention_total',
    'Authentication loop prevention triggers',
    ['service', 'prevention_type']
)

redis_connection_health = Gauge(
    'redis_connection_health',
    'Redis connection health status (0=unhealthy, 1=healthy)',
    ['instance']
)

security_events_total = Counter(
    'security_events_total',
    'Security events detected',
    ['event_type', 'severity']
)

class SecurityCircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Advanced security circuit breaker with Redis connectivity monitoring,
    authentication security, and comprehensive alerting.
    """
    
    def __init__(self, app, config: CircuitBreakerConfig = None):
        super().__init__(app)
        self.config = config or CircuitBreakerConfig()
        
        # Circuit breaker states per service
        self.circuits = {
            'authentication': {
                'state': CircuitState.CLOSED,
                'metrics': SecurityMetrics(),
                'last_state_change': time.time()
            },
            'redis': {
                'state': CircuitState.CLOSED,
                'metrics': SecurityMetrics(),
                'last_state_change': time.time()
            }
        }
        
        # Security monitoring
        self.security_patterns = {
            'brute_force': {'threshold': 10, 'window': 60},
            'token_manipulation': {'threshold': 5, 'window': 30},
            'session_hijacking': {'threshold': 3, 'window': 300}
        }
        
        self.request_tracking = {}
        
        # Initialize Prometheus metrics
        auth_circuit_state.labels(service='authentication').state('CLOSED')
        auth_circuit_state.labels(service='redis').state('CLOSED')
        
        logger.info("Security Circuit Breaker Middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security circuit breaker."""
        start_time = time.time()
        
        try:
            # Security pre-checks
            await self._security_pre_validation(request)
            
            # Check circuit breaker states
            await self._check_circuit_states()
            
            # Process request if circuits allow
            if self._should_allow_request(request):
                response = await self._process_with_monitoring(request, call_next)
                await self._update_success_metrics(request)
                return response
            else:
                # Circuit breaker is open - return service unavailable
                await self._handle_circuit_open(request)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable - circuit breaker open"
                )
                
        except HTTPException:
            await self._handle_request_failure(request, "http_exception")
            raise
        except Exception as e:
            await self._handle_request_failure(request, "internal_error")
            logger.error(f"Circuit breaker middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            # Always record timing
            response_time = time.time() - start_time
            auth_recovery_time.labels(service='authentication').observe(response_time)
    
    async def _security_pre_validation(self, request: Request):
        """Perform security validation before processing request."""
        client_ip = self._get_client_ip(request)
        path = str(request.url.path)
        
        # Track request patterns for security monitoring
        current_time = time.time()
        
        if client_ip not in self.request_tracking:
            self.request_tracking[client_ip] = {
                'requests': [],
                'failed_auths': [],
                'suspicious_patterns': []
            }
        
        # Add current request
        self.request_tracking[client_ip]['requests'].append({
            'timestamp': current_time,
            'path': path,
            'method': request.method
        })
        
        # Clean old tracking data (older than 5 minutes)
        cutoff_time = current_time - 300
        for ip, data in self.request_tracking.items():
            data['requests'] = [r for r in data['requests'] if r['timestamp'] > cutoff_time]
            data['failed_auths'] = [r for r in data['failed_auths'] if r['timestamp'] > cutoff_time]
        
        # Check for suspicious patterns
        await self._detect_security_threats(client_ip, path, current_time)
    
    async def _detect_security_threats(self, client_ip: str, path: str, timestamp: float):
        """Detect potential security threats."""
        client_data = self.request_tracking.get(client_ip, {})
        recent_requests = client_data.get('requests', [])
        
        # Brute force detection
        auth_requests = [r for r in recent_requests if 'auth' in r['path'] or 'login' in r['path']]
        if len(auth_requests) > self.security_patterns['brute_force']['threshold']:
            security_events_total.labels(event_type='brute_force', severity='high').inc()
            await self._trigger_security_alert('brute_force', client_ip, {
                'request_count': len(auth_requests),
                'time_window': self.security_patterns['brute_force']['window']
            })
        
        # Rate limiting check
        recent_count = len([r for r in recent_requests if timestamp - r['timestamp'] < 10])
        if recent_count > 20:  # More than 20 requests in 10 seconds
            security_events_total.labels(event_type='rate_limit_exceeded', severity='medium').inc()
            auth_failures_total.labels(service='authentication', failure_type='rate_limit').inc()
        
        # Path traversal attempts
        if any(suspicious in path for suspicious in ['../', '..\\', '/etc/', '/proc/']):
            security_events_total.labels(event_type='path_traversal', severity='high').inc()
            await self._trigger_security_alert('path_traversal', client_ip, {'path': path})
    
    async def _check_circuit_states(self):
        """Check and update circuit breaker states."""
        current_time = time.time()
        
        for service_name, circuit in self.circuits.items():
            state = circuit['state']
            metrics = circuit['metrics']
            
            if state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if current_time - circuit['last_state_change'] > self.config.recovery_timeout:
                    await self._transition_to_half_open(service_name)
            
            elif state == CircuitState.HALF_OPEN:
                # Check if we have enough successes to close
                if metrics.successes >= self.config.success_threshold:
                    await self._transition_to_closed(service_name)
                # Or if we should open again due to failures
                elif metrics.failures > 0:
                    await self._transition_to_open(service_name)
            
            elif state == CircuitState.CLOSED:
                # Check if we should open due to too many failures
                failure_rate = self._calculate_failure_rate(metrics)
                if failure_rate > 0.5 and metrics.failures >= self.config.failure_threshold:
                    await self._transition_to_open(service_name)
        
        # Update Redis connectivity health
        await self._check_redis_health()
    
    async def _check_redis_health(self):
        """Monitor Redis connectivity health."""
        try:
            redis = await get_redis_cache()
            # Simple health check
            await redis.ping()
            redis_connection_health.labels(instance='ai_workflow_engine-redis-1').set(1)
            
            # Update circuit state if it was failing
            if self.circuits['redis']['state'] == CircuitState.OPEN:
                await self._handle_redis_recovery()
                
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_connection_health.labels(instance='ai_workflow_engine-redis-1').set(0)
            
            # Update circuit breaker
            self.circuits['redis']['metrics'].failures += 1
            auth_failures_total.labels(service='redis', failure_type='connection_failure').inc()
            
            if self.circuits['redis']['state'] == CircuitState.CLOSED:
                await self._transition_to_open('redis')
    
    def _should_allow_request(self, request: Request) -> bool:
        """Determine if request should be allowed through circuit breaker."""
        path = str(request.url.path)
        
        # Always allow health checks
        if '/health' in path:
            return True
        
        # Check authentication circuit for auth-related paths
        if any(auth_path in path for auth_path in ['/auth', '/login', '/session']):
            auth_state = self.circuits['authentication']['state']
            if auth_state == CircuitState.OPEN:
                return False
            elif auth_state == CircuitState.HALF_OPEN:
                # Allow limited requests to test recovery
                return self.circuits['authentication']['metrics'].recovery_attempts < 3
        
        # Check Redis circuit for operations requiring Redis
        if any(redis_path in path for redis_path in ['/api/', '/session/validate']):
            redis_state = self.circuits['redis']['state']
            if redis_state == CircuitState.OPEN:
                return False
        
        return True
    
    async def _process_with_monitoring(self, request: Request, call_next):
        """Process request with comprehensive monitoring."""
        start_time = time.time()
        path = str(request.url.path)
        
        try:
            response = await call_next(request)
            
            # Monitor for authentication-related responses
            if any(auth_path in path for auth_path in ['/auth', '/login', '/session']):
                if response.status_code >= 400:
                    await self._handle_auth_failure(request, response.status_code)
                else:
                    await self._handle_auth_success(request)
            
            # Record successful request
            auth_requests_total.labels(service='authentication', status='success').inc()
            
            return response
            
        except Exception as e:
            await self._handle_request_failure(request, str(e))
            raise
    
    async def _handle_auth_failure(self, request: Request, status_code: int):
        """Handle authentication failure with security monitoring."""
        client_ip = self._get_client_ip(request)
        
        # Record failed authentication
        if client_ip in self.request_tracking:
            self.request_tracking[client_ip]['failed_auths'].append({
                'timestamp': time.time(),
                'status_code': status_code,
                'path': str(request.url.path)
            })
        
        # Update circuit breaker metrics
        self.circuits['authentication']['metrics'].failures += 1
        auth_failures_total.labels(service='authentication', failure_type='auth_failure').inc()
        
        # Check for authentication loop prevention
        await self._check_authentication_loops(client_ip)
    
    async def _check_authentication_loops(self, client_ip: str):
        """Detect and prevent authentication loops."""
        if client_ip not in self.request_tracking:
            return
        
        failed_auths = self.request_tracking[client_ip]['failed_auths']
        recent_failures = [f for f in failed_auths if time.time() - f['timestamp'] < 30]
        
        if len(recent_failures) > 5:  # More than 5 auth failures in 30 seconds
            self.circuits['authentication']['metrics'].loop_prevention_triggers += 1
            auth_loop_prevention_total.labels(
                service='authentication', 
                prevention_type='rapid_failures'
            ).inc()
            
            await self._trigger_security_alert('authentication_loop', client_ip, {
                'failure_count': len(recent_failures),
                'time_window': 30
            })
    
    async def _handle_auth_success(self, request: Request):
        """Handle successful authentication."""
        self.circuits['authentication']['metrics'].successes += 1
        auth_requests_total.labels(service='authentication', status='success').inc()
    
    async def _handle_request_failure(self, request: Request, error: str):
        """Handle general request failure."""
        path = str(request.url.path)
        
        if any(auth_path in path for auth_path in ['/auth', '/login', '/session']):
            self.circuits['authentication']['metrics'].failures += 1
            auth_failures_total.labels(service='authentication', failure_type='request_error').inc()
        
        auth_requests_total.labels(service='authentication', status='failure').inc()
    
    async def _transition_to_open(self, service: str):
        """Transition circuit breaker to OPEN state."""
        self.circuits[service]['state'] = CircuitState.OPEN
        self.circuits[service]['last_state_change'] = time.time()
        self.circuits[service]['metrics'].recovery_attempts = 0
        
        auth_circuit_state.labels(service=service).state('OPEN')
        
        logger.warning(f"Circuit breaker OPENED for service: {service}")
        
        await self._trigger_security_alert('circuit_breaker_open', service, {
            'failure_count': self.circuits[service]['metrics'].failures,
            'service': service
        })
    
    async def _transition_to_half_open(self, service: str):
        """Transition circuit breaker to HALF_OPEN state."""
        self.circuits[service]['state'] = CircuitState.HALF_OPEN
        self.circuits[service]['last_state_change'] = time.time()
        self.circuits[service]['metrics'].successes = 0
        self.circuits[service]['metrics'].failures = 0
        
        auth_circuit_state.labels(service=service).state('HALF_OPEN')
        
        logger.info(f"Circuit breaker HALF-OPEN for service: {service}")
    
    async def _transition_to_closed(self, service: str):
        """Transition circuit breaker to CLOSED state."""
        self.circuits[service]['state'] = CircuitState.CLOSED
        self.circuits[service]['last_state_change'] = time.time()
        
        # Reset metrics
        self.circuits[service]['metrics'] = SecurityMetrics()
        
        auth_circuit_state.labels(service=service).state('CLOSED')
        
        logger.info(f"Circuit breaker CLOSED for service: {service}")
    
    async def _handle_circuit_open(self, request: Request):
        """Handle request when circuit breaker is open."""
        path = str(request.url.path)
        client_ip = self._get_client_ip(request)
        
        # Log circuit breaker activation
        logger.warning(f"Circuit breaker blocked request from {client_ip} to {path}")
        
        # Update metrics
        auth_requests_total.labels(service='authentication', status='circuit_open').inc()
    
    async def _trigger_security_alert(self, alert_type: str, source: str, details: Dict[str, Any]):
        """Trigger security alert for monitoring systems."""
        alert_data = {
            'type': alert_type,
            'source': source,
            'timestamp': time.time(),
            'details': details,
            'severity': self._get_alert_severity(alert_type)
        }
        
        logger.warning(f"Security Alert: {alert_type} from {source} - {details}")
        
        # Here you would integrate with your alerting system
        # For now, we log and update metrics
        security_events_total.labels(
            event_type=alert_type, 
            severity=alert_data['severity']
        ).inc()
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """Determine alert severity based on type."""
        high_severity = ['brute_force', 'path_traversal', 'circuit_breaker_open']
        medium_severity = ['authentication_loop', 'rate_limit_exceeded']
        
        if alert_type in high_severity:
            return 'high'
        elif alert_type in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_failure_rate(self, metrics: SecurityMetrics) -> float:
        """Calculate current failure rate."""
        total = metrics.successes + metrics.failures
        if total == 0:
            return 0.0
        return metrics.failures / total
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        forwarded = request.headers.get('X-Forwarded')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    async def _handle_redis_recovery(self):
        """Handle Redis service recovery."""
        logger.info("Redis service recovered - updating circuit breaker")
        
        self.circuits['redis']['metrics'].successes += 1
        if self.circuits['redis']['state'] == CircuitState.HALF_OPEN:
            await self._transition_to_closed('redis')
    
    async def _update_success_metrics(self, request: Request):
        """Update metrics for successful requests."""
        path = str(request.url.path)
        
        if any(auth_path in path for auth_path in ['/auth', '/login', '/session']):
            self.circuits['authentication']['metrics'].successes += 1
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status for monitoring."""
        return {
            service: {
                'state': circuit['state'].name,
                'metrics': {
                    'total_requests': circuit['metrics'].total_requests,
                    'failures': circuit['metrics'].failures,
                    'successes': circuit['metrics'].successes,
                    'failure_rate': self._calculate_failure_rate(circuit['metrics']),
                    'last_failure': circuit['metrics'].last_failure_time,
                    'loop_prevention_triggers': circuit['metrics'].loop_prevention_triggers
                },
                'last_state_change': circuit['last_state_change']
            }
            for service, circuit in self.circuits.items()
        }