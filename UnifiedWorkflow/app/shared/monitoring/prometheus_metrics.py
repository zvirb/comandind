"""
Prometheus metrics configuration and instrumentation for the AI Workflow Engine.

This module provides comprehensive metrics collection for:
- HTTP request/response metrics
- Application performance metrics
- Business logic metrics
- Security metrics
- Database metrics
- Cache metrics
- Worker queue metrics
"""

from typing import Dict, List, Optional, Any
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Enum, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.registry import REGISTRY
import time
import logging
from contextvars import ContextVar
from functools import wraps

logger = logging.getLogger(__name__)

# Context variable for request tracing
request_id_context: ContextVar[str] = ContextVar('request_id', default='')

class PrometheusMetrics:
    """Centralized Prometheus metrics registry for AI Workflow Engine."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or REGISTRY
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # ==============================================================================
        # HTTP REQUEST METRICS
        # ==============================================================================
        
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests processed',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
            registry=self.registry
        )
        
        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'Size of HTTP requests in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'Size of HTTP responses in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # ==============================================================================
        # APPLICATION PERFORMANCE METRICS
        # ==============================================================================
        
        self.active_requests = Gauge(
            'active_requests',
            'Number of active HTTP requests',
            registry=self.registry
        )
        
        self.app_info = Info(
            'app_info',
            'Application information',
            registry=self.registry
        )
        
        self.app_health_status = Enum(
            'app_health_status',
            'Application health status',
            states=['healthy', 'degraded', 'unhealthy'],
            registry=self.registry
        )
        
        # ==============================================================================
        # AUTHENTICATION AND SECURITY METRICS
        # ==============================================================================
        
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['method', 'status'],
            registry=self.registry
        )
        
        self.auth_session_duration_seconds = Histogram(
            'auth_session_duration_seconds',
            'Duration of authentication sessions',
            buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400),
            registry=self.registry
        )
        
        self.auth_failed_attempts = Counter(
            'auth_failed_attempts_total',
            'Total failed authentication attempts',
            ['reason', 'user_agent', 'ip_range'],
            registry=self.registry
        )
        
        self.auth_account_lockouts = Counter(
            'auth_account_lockouts_total',
            'Total account lockouts',
            ['reason'],
            registry=self.registry
        )
        
        self.auth_mfa_bypass_attempts = Counter(
            'auth_mfa_bypass_attempts_total',
            'MFA bypass attempts',
            ['method'],
            registry=self.registry
        )
        
        self.security_events = Counter(
            'security_events_total',
            'Security events detected',
            ['event_type', 'severity', 'source'],
            registry=self.registry
        )
        
        # ==============================================================================
        # DATABASE METRICS
        # ==============================================================================
        
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            ['database', 'pool'],
            registry=self.registry
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query execution time',
            ['operation', 'table'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        self.db_queries_total = Counter(
            'db_queries_total',
            'Total database queries executed',
            ['operation', 'table', 'status'],
            registry=self.registry
        )
        
        self.db_transaction_duration_seconds = Histogram(
            'db_transaction_duration_seconds',
            'Database transaction duration',
            ['status'],
            registry=self.registry
        )
        
        # ==============================================================================
        # CACHE METRICS
        # ==============================================================================
        
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'cache_name', 'status'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio',
            ['cache_name'],
            registry=self.registry
        )
        
        self.cache_size_bytes = Gauge(
            'cache_size_bytes',
            'Cache size in bytes',
            ['cache_name'],
            registry=self.registry
        )
        
        # ==============================================================================
        # AI WORKFLOW METRICS
        # ==============================================================================
        
        self.ai_tasks_total = Counter(
            'ai_tasks_total',
            'Total AI tasks processed',
            ['task_type', 'model', 'status'],
            registry=self.registry
        )
        
        self.ai_task_duration_seconds = Histogram(
            'ai_task_duration_seconds',
            'AI task processing duration',
            ['task_type', 'model'],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1200),
            registry=self.registry
        )
        
        self.ai_tasks_queue_depth = Gauge(
            'ai_tasks_queue_depth',
            'Number of tasks in AI processing queue',
            ['queue_name'],
            registry=self.registry
        )
        
        self.ai_model_resource_utilization = Gauge(
            'ai_model_resource_utilization',
            'AI model resource utilization percentage',
            ['model', 'resource_type'],
            registry=self.registry
        )
        
        # ==============================================================================
        # BUSINESS METRICS
        # ==============================================================================
        
        self.user_requests_total = Counter(
            'user_requests_total',
            'Total user requests',
            ['user_type', 'endpoint'],
            registry=self.registry
        )
        
        self.user_registrations_total = Counter(
            'user_registrations_total',
            'Total user registrations',
            ['source'],
            registry=self.registry
        )
        
        self.user_deletions_total = Counter(
            'user_deletions_total',
            'Total user account deletions',
            ['reason'],
            registry=self.registry
        )
        
        self.api_quota_used = Gauge(
            'api_quota_used',
            'API quota used by user',
            ['user_id', 'quota_type'],
            registry=self.registry
        )
        
        self.api_quota_limit = Gauge(
            'api_quota_limit',
            'API quota limit for user',
            ['user_id', 'quota_type'],
            registry=self.registry
        )
        
        self.api_rate_limit_hits = Counter(
            'api_rate_limit_hits_total',
            'API rate limit hits',
            ['user_id', 'endpoint'],
            registry=self.registry
        )
        
        # ==============================================================================
        # DATA PROCESSING METRICS
        # ==============================================================================
        
        self.data_processing_duration_seconds = Histogram(
            'data_processing_duration_seconds',
            'Data processing operation duration',
            ['operation_type', 'data_type'],
            registry=self.registry
        )
        
        self.data_validation_attempts_total = Counter(
            'data_validation_attempts_total',
            'Total data validation attempts',
            ['data_type', 'validation_type'],
            registry=self.registry
        )
        
        self.data_validation_failures_total = Counter(
            'data_validation_failures_total',
            'Total data validation failures',
            ['data_type', 'validation_type', 'error_type'],
            registry=self.registry
        )
        
        self.data_storage_bytes_total = Gauge(
            'data_storage_bytes_total',
            'Total data storage used in bytes',
            ['storage_type', 'data_classification'],
            registry=self.registry
        )
        
        # ==============================================================================
        # COMPLIANCE AND AUDIT METRICS
        # ==============================================================================
        
        self.data_retention_policy_violations_total = Counter(
            'data_retention_policy_violations_total',
            'Data retention policy violations',
            ['policy_type', 'data_type'],
            registry=self.registry
        )
        
        self.personal_data_access_without_consent_total = Counter(
            'personal_data_access_without_consent_total',
            'Personal data access without consent',
            ['access_type', 'data_category'],
            registry=self.registry
        )
        
        self.audit_log_gaps_detected_total = Counter(
            'audit_log_gaps_detected_total',
            'Audit log gaps detected',
            ['log_type', 'service'],
            registry=self.registry
        )
        
        # ==============================================================================
        # COST OPTIMIZATION METRICS
        # ==============================================================================
        
        self.estimated_infrastructure_cost_usd = Gauge(
            'estimated_infrastructure_cost_usd',
            'Estimated infrastructure cost in USD',
            ['service', 'resource_type'],
            registry=self.registry
        )
        
        self.idle_compute_resources_cost_usd = Gauge(
            'idle_compute_resources_cost_usd',
            'Estimated cost of idle compute resources',
            ['service', 'resource_type'],
            registry=self.registry
        )
    
    def set_app_info(self, version: str, git_commit: str, build_time: str):
        """Set application information."""
        self.app_info.info({
            'version': version,
            'git_commit': git_commit,
            'build_time': build_time
        })
    
    def set_health_status(self, status: str):
        """Set application health status."""
        self.app_health_status.state(status)
    
    def record_request_metrics(self, method: str, endpoint: str, status: int, 
                             duration: float, request_size: int = 0, response_size: int = 0):
        """Record HTTP request metrics."""
        status_str = str(status)
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_str
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def record_auth_attempt(self, method: str, status: str, **kwargs):
        """Record authentication attempt."""
        self.auth_attempts_total.labels(method=method, status=status).inc()
        
        if status == 'failure':
            reason = kwargs.get('reason', 'unknown')
            user_agent = kwargs.get('user_agent', 'unknown')
            ip_range = kwargs.get('ip_range', 'unknown')
            
            self.auth_failed_attempts.labels(
                reason=reason,
                user_agent=user_agent,
                ip_range=ip_range
            ).inc()
    
    def record_security_event(self, event_type: str, severity: str, source: str):
        """Record security event."""
        self.security_events.labels(
            event_type=event_type,
            severity=severity,
            source=source
        ).inc()
    
    def record_db_query(self, operation: str, table: str, duration: float, status: str = 'success'):
        """Record database query metrics."""
        self.db_queries_total.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        self.db_query_duration_seconds.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def record_ai_task(self, task_type: str, model: str, duration: float, status: str):
        """Record AI task processing metrics."""
        self.ai_tasks_total.labels(
            task_type=task_type,
            model=model,
            status=status
        ).inc()
        
        self.ai_task_duration_seconds.labels(
            task_type=task_type,
            model=model
        ).observe(duration)
    
    def update_queue_depth(self, queue_name: str, depth: int):
        """Update queue depth metric."""
        self.ai_tasks_queue_depth.labels(queue_name=queue_name).set(depth)
    
    def record_cache_operation(self, operation: str, cache_name: str, status: str):
        """Record cache operation."""
        self.cache_operations_total.labels(
            operation=operation,
            cache_name=cache_name,
            status=status
        ).inc()
    
    def update_cache_hit_ratio(self, cache_name: str, ratio: float):
        """Update cache hit ratio."""
        self.cache_hit_ratio.labels(cache_name=cache_name).set(ratio)
    
    def get_metrics_handler(self):
        """Get metrics handler for Prometheus scraping."""
        def metrics_handler():
            return generate_latest(self.registry), 200, {'Content-Type': CONTENT_TYPE_LATEST}
        return metrics_handler


# Global metrics instance
metrics = PrometheusMetrics()


def monitor_http_requests(func):
    """Decorator to monitor HTTP requests."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        metrics.active_requests.inc()
        try:
            response = await func(*args, **kwargs)
            
            duration = time.time() - start_time
            
            # Extract request details (this would depend on your FastAPI setup)
            method = getattr(args[0], 'method', 'GET') if args else 'GET'
            endpoint = getattr(args[0], 'url', {}).get('path', '/') if args else '/'
            status = getattr(response, 'status_code', 200)
            
            metrics.record_request_metrics(
                method=method,
                endpoint=endpoint,
                status=status,
                duration=duration
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            method = getattr(args[0], 'method', 'GET') if args else 'GET'
            endpoint = getattr(args[0], 'url', {}).get('path', '/') if args else '/'
            
            metrics.record_request_metrics(
                method=method,
                endpoint=endpoint,
                status=500,
                duration=duration
            )
            
            raise
        
        finally:
            metrics.active_requests.dec()
    
    return wrapper


def monitor_database_queries(operation: str, table: str = 'unknown'):
    """Decorator to monitor database queries."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                metrics.record_db_query(
                    operation=operation,
                    table=table,
                    duration=duration,
                    status='success'
                )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                
                metrics.record_db_query(
                    operation=operation,
                    table=table,
                    duration=duration,
                    status='error'
                )
                
                raise
        
        return wrapper
    return decorator


def monitor_ai_tasks(task_type: str, model: str = 'unknown'):
    """Decorator to monitor AI task processing."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                metrics.record_ai_task(
                    task_type=task_type,
                    model=model,
                    duration=duration,
                    status='success'
                )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                
                metrics.record_ai_task(
                    task_type=task_type,
                    model=model,
                    duration=duration,
                    status='error'
                )
                
                raise
        
        return wrapper
    return decorator


# Global metrics handler function (for monitoring router compatibility)
def get_metrics_handler():
    """Get global metrics handler for Prometheus scraping."""
    return metrics.get_metrics_handler()


# Utility functions for manual metric recording
def record_user_registration(source: str = 'web'):
    """Record user registration."""
    metrics.user_registrations_total.labels(source=source).inc()


def record_user_request(user_type: str, endpoint: str):
    """Record user request."""
    metrics.user_requests_total.labels(user_type=user_type, endpoint=endpoint).inc()


def update_api_quota(user_id: str, quota_type: str, used: int, limit: int):
    """Update API quota metrics."""
    metrics.api_quota_used.labels(user_id=user_id, quota_type=quota_type).set(used)
    metrics.api_quota_limit.labels(user_id=user_id, quota_type=quota_type).set(limit)


def record_rate_limit_hit(user_id: str, endpoint: str):
    """Record rate limit hit."""
    metrics.api_rate_limit_hits.labels(user_id=user_id, endpoint=endpoint).inc()