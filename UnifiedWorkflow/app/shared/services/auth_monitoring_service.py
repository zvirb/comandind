"""
Authentication Monitoring Service
Comprehensive monitoring for JWT authentication system with metrics collection,
anomaly detection, and performance tracking.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from prometheus_client import Counter, Histogram, Gauge, Info
from dataclasses import dataclass, asdict
import json
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class AuthenticationEvent:
    """Authentication event data structure."""
    user_id: Optional[int]
    user_email: Optional[str]
    event_type: str  # login_success, login_failure, token_validation, token_refresh
    authentication_method: str  # bearer_token, cookie, websocket
    client_ip: Optional[str]
    user_agent: Optional[str]
    timestamp: float
    response_time_ms: float
    error_message: Optional[str] = None
    session_id: Optional[str] = None

class AuthMonitoringService:
    """
    Centralized authentication monitoring with Prometheus metrics and anomaly detection.
    """
    
    def __init__(self, namespace: str = "auth"):
        self.namespace = namespace
        
        # Authentication Success/Failure Metrics
        self.auth_attempts_total = Counter(
            f'{namespace}_attempts_total',
            'Total authentication attempts',
            ['method', 'result', 'user_role']
        )
        
        self.auth_failures_total = Counter(
            f'{namespace}_failures_total', 
            'Authentication failures by reason',
            ['reason', 'method']
        )
        
        # JWT Token Metrics
        self.jwt_tokens_created_total = Counter(
            f'{namespace}_jwt_tokens_created_total',
            'Total JWT tokens created',
            ['token_type']
        )
        
        self.jwt_tokens_validated_total = Counter(
            f'{namespace}_jwt_tokens_validated_total',
            'Total JWT tokens validated',
            ['result', 'validation_type']
        )
        
        self.jwt_token_validation_time = Histogram(
            f'{namespace}_jwt_validation_duration_seconds',
            'JWT token validation time',
            buckets=(0.001, 0.005, 0.010, 0.025, 0.050, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
        
        # Authentication Response Time Metrics
        self.auth_response_time = Histogram(
            f'{namespace}_response_time_seconds',
            'Authentication response time',
            ['method', 'endpoint'],
            buckets=(0.001, 0.005, 0.010, 0.025, 0.050, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
        
        # SECRET_KEY Consistency Metrics
        self.secret_key_health = Gauge(
            f'{namespace}_secret_key_health',
            'SECRET_KEY consistency service health (1=healthy, 0=unhealthy)'
        )
        
        self.secret_key_mismatches_total = Counter(
            f'{namespace}_secret_key_mismatches_total',
            'Total SECRET_KEY mismatch errors'
        )
        
        self.secret_key_refreshes_total = Counter(
            f'{namespace}_secret_key_refreshes_total',
            'Total SECRET_KEY refresh operations'
        )
        
        # Session and Cache Metrics
        self.active_sessions_count = Gauge(
            f'{namespace}_active_sessions',
            'Number of active authentication sessions'
        )
        
        self.cache_hits_total = Counter(
            f'{namespace}_cache_hits_total',
            'Authentication cache hits',
            ['cache_type']
        )
        
        self.cache_misses_total = Counter(
            f'{namespace}_cache_misses_total',
            'Authentication cache misses',
            ['cache_type']
        )
        
        # Anomaly Detection Metrics
        self.anomaly_detections_total = Counter(
            f'{namespace}_anomalies_total',
            'Authentication anomalies detected',
            ['anomaly_type', 'severity']
        )
        
        self.failed_attempts_by_ip = Counter(
            f'{namespace}_failed_attempts_by_ip_total',
            'Failed authentication attempts by IP',
            ['client_ip']
        )
        
        # WebSocket Authentication Metrics
        self.websocket_auth_attempts_total = Counter(
            f'{namespace}_websocket_auth_attempts_total',
            'WebSocket authentication attempts',
            ['result']
        )
        
        # Bearer Token Fix Monitoring
        self.bearer_token_consistency_score = Gauge(
            f'{namespace}_bearer_token_consistency_score',
            'Bearer token consistency score (0-100)'
        )
        
        # Performance Target Metrics
        self.performance_target_compliance = Gauge(
            f'{namespace}_performance_target_compliance',
            'Authentication performance target compliance (1=met, 0=not met)',
            ['target_type']
        )
        
        # Internal state for anomaly detection
        self._recent_events: List[AuthenticationEvent] = []
        self._max_recent_events = 1000
        self._anomaly_thresholds = {
            'max_failures_per_ip_per_minute': 10,
            'max_response_time_ms': 1000,
            'min_success_rate_percent': 95.0
        }
        
        # Initialize health status
        self.secret_key_health.set(1.0)
        
    def record_auth_attempt(self, event: AuthenticationEvent) -> None:
        """Record an authentication attempt with comprehensive metrics."""
        try:
            # Add to recent events for anomaly detection
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_recent_events:
                self._recent_events.pop(0)
            
            # Basic authentication metrics
            result = 'success' if event.error_message is None else 'failure'
            user_role = 'unknown'  # Will be determined from user context
            
            self.auth_attempts_total.labels(
                method=event.authentication_method,
                result=result,
                user_role=user_role
            ).inc()
            
            # Record response time
            response_time_seconds = event.response_time_ms / 1000.0
            self.auth_response_time.labels(
                method=event.authentication_method,
                endpoint='auth'
            ).observe(response_time_seconds)
            
            # Record failures with details
            if event.error_message:
                failure_reason = self._categorize_failure(event.error_message)
                self.auth_failures_total.labels(
                    reason=failure_reason,
                    method=event.authentication_method
                ).inc()
                
                # Track failed attempts by IP for anomaly detection
                if event.client_ip:
                    self.failed_attempts_by_ip.labels(
                        client_ip=event.client_ip
                    ).inc()
            
            # Check for anomalies
            self._check_for_anomalies(event)
            
            logger.debug(f"Recorded auth event: {event.event_type} for {event.user_email}")
            
        except Exception as e:
            logger.error(f"Failed to record authentication event: {e}")
    
    def record_jwt_operation(self, operation_type: str, result: str, validation_time_ms: Optional[float] = None) -> None:
        """Record JWT token operations."""
        try:
            if operation_type == 'create':
                self.jwt_tokens_created_total.labels(token_type='access').inc()
            elif operation_type == 'validate':
                self.jwt_tokens_validated_total.labels(
                    result=result,
                    validation_type='bearer'
                ).inc()
                
                if validation_time_ms is not None:
                    self.jwt_token_validation_time.observe(validation_time_ms / 1000.0)
            
            logger.debug(f"Recorded JWT operation: {operation_type} with result: {result}")
            
        except Exception as e:
            logger.error(f"Failed to record JWT operation: {e}")
    
    def record_secret_key_event(self, event_type: str, healthy: bool = True) -> None:
        """Record SECRET_KEY consistency service events."""
        try:
            if event_type == 'mismatch':
                self.secret_key_mismatches_total.inc()
                self.secret_key_health.set(0.0)
            elif event_type == 'refresh':
                self.secret_key_refreshes_total.inc()
                if healthy:
                    self.secret_key_health.set(1.0)
            
            logger.info(f"SECRET_KEY event recorded: {event_type}, healthy: {healthy}")
            
        except Exception as e:
            logger.error(f"Failed to record SECRET_KEY event: {e}")
    
    def record_cache_operation(self, cache_type: str, hit: bool) -> None:
        """Record authentication cache operations."""
        try:
            if hit:
                self.cache_hits_total.labels(cache_type=cache_type).inc()
            else:
                self.cache_misses_total.labels(cache_type=cache_type).inc()
                
        except Exception as e:
            logger.error(f"Failed to record cache operation: {e}")
    
    def record_websocket_auth(self, success: bool) -> None:
        """Record WebSocket authentication attempts."""
        try:
            result = 'success' if success else 'failure'
            self.websocket_auth_attempts_total.labels(result=result).inc()
            
        except Exception as e:
            logger.error(f"Failed to record WebSocket auth: {e}")
    
    def update_active_sessions(self, count: int) -> None:
        """Update active sessions count."""
        try:
            self.active_sessions_count.set(count)
        except Exception as e:
            logger.error(f"Failed to update active sessions: {e}")
    
    def update_bearer_token_consistency(self, score: float) -> None:
        """Update Bearer token consistency score (0-100)."""
        try:
            self.bearer_token_consistency_score.set(max(0.0, min(100.0, score)))
        except Exception as e:
            logger.error(f"Failed to update bearer token consistency: {e}")
    
    def check_performance_targets(self, avg_response_time_ms: float) -> None:
        """Check if authentication performance targets are being met."""
        try:
            # Target: <50ms average response time
            response_time_target_met = avg_response_time_ms < 50.0
            self.performance_target_compliance.labels(
                target_type='response_time'
            ).set(1.0 if response_time_target_met else 0.0)
            
            # Calculate success rate from recent events
            if self._recent_events:
                recent_successes = sum(1 for e in self._recent_events[-100:] if e.error_message is None)
                success_rate = (recent_successes / min(100, len(self._recent_events))) * 100
                
                success_rate_target_met = success_rate >= self._anomaly_thresholds['min_success_rate_percent']
                self.performance_target_compliance.labels(
                    target_type='success_rate'
                ).set(1.0 if success_rate_target_met else 0.0)
            
        except Exception as e:
            logger.error(f"Failed to check performance targets: {e}")
    
    def _categorize_failure(self, error_message: str) -> str:
        """Categorize authentication failure reason."""
        error_lower = error_message.lower()
        
        if 'token' in error_lower and ('expired' in error_lower or 'exp' in error_lower):
            return 'token_expired'
        elif 'token' in error_lower and 'invalid' in error_lower:
            return 'token_invalid'
        elif 'signature' in error_lower:
            return 'signature_mismatch'
        elif 'secret' in error_lower or 'key' in error_lower:
            return 'secret_key_mismatch'
        elif 'user' in error_lower and 'not found' in error_lower:
            return 'user_not_found'
        elif 'credentials' in error_lower:
            return 'invalid_credentials'
        elif 'csrf' in error_lower:
            return 'csrf_failure'
        else:
            return 'unknown'
    
    def _check_for_anomalies(self, event: AuthenticationEvent) -> None:
        """Check for authentication anomalies."""
        try:
            # Check for too many failures from single IP
            if event.client_ip and event.error_message:
                recent_failures_from_ip = sum(
                    1 for e in self._recent_events[-60:]  # Last 60 events as proxy for 1 minute
                    if e.client_ip == event.client_ip and e.error_message is not None
                )
                
                if recent_failures_from_ip >= self._anomaly_thresholds['max_failures_per_ip_per_minute']:
                    self.anomaly_detections_total.labels(
                        anomaly_type='excessive_failures_per_ip',
                        severity='high'
                    ).inc()
                    logger.warning(f"Anomaly detected: {recent_failures_from_ip} failures from IP {event.client_ip}")
            
            # Check for unusually slow response times
            if event.response_time_ms > self._anomaly_thresholds['max_response_time_ms']:
                self.anomaly_detections_total.labels(
                    anomaly_type='slow_response',
                    severity='medium'
                ).inc()
                logger.warning(f"Anomaly detected: Slow auth response {event.response_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get authentication system health summary."""
        try:
            recent_events_count = len(self._recent_events)
            recent_failures = sum(1 for e in self._recent_events if e.error_message is not None)
            success_rate = ((recent_events_count - recent_failures) / max(1, recent_events_count)) * 100
            
            if self._recent_events:
                avg_response_time = sum(e.response_time_ms for e in self._recent_events) / len(self._recent_events)
            else:
                avg_response_time = 0.0
            
            return {
                'secret_key_healthy': bool(self.secret_key_health._value.get()),
                'recent_events_count': recent_events_count,
                'success_rate_percent': round(success_rate, 2),
                'average_response_time_ms': round(avg_response_time, 2),
                'performance_target_met': avg_response_time < 50.0,
                'bearer_token_consistency_score': self.bearer_token_consistency_score._value.get(),
                'active_sessions': int(self.active_sessions_count._value.get()),
                'anomalies_detected': recent_failures > (recent_events_count * 0.05)  # >5% failure rate
            }
            
        except Exception as e:
            logger.error(f"Failed to generate health summary: {e}")
            return {'error': str(e)}

# Global singleton instance
auth_monitoring_service = AuthMonitoringService()