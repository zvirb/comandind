#!/usr/bin/env python3
"""
Shared metrics exporter module for cognitive services
Provides Prometheus-compatible metrics endpoints
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

# Common metrics for all services
request_count = Counter(
    'cognitive_service_requests_total',
    'Total number of requests',
    ['service', 'method', 'endpoint', 'status']
)

request_duration = Histogram(
    'cognitive_service_request_duration_seconds',
    'Request duration in seconds',
    ['service', 'method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_connections = Gauge(
    'cognitive_service_active_connections',
    'Number of active connections',
    ['service']
)

service_info = Gauge(
    'cognitive_service_info',
    'Service information',
    ['service', 'version', 'status']
)

error_count = Counter(
    'cognitive_service_errors_total',
    'Total number of errors',
    ['service', 'error_type', 'endpoint']
)

# Service-specific metrics
learning_patterns_stored = Gauge(
    'learning_service_patterns_stored',
    'Number of patterns stored in learning service'
)

learning_knowledge_nodes = Gauge(
    'learning_service_knowledge_graph_nodes',
    'Number of nodes in knowledge graph'
)

learning_knowledge_edges = Gauge(
    'learning_service_knowledge_graph_edges',
    'Number of edges in knowledge graph'
)

reasoning_decisions_made = Counter(
    'reasoning_service_decisions_total',
    'Total number of reasoning decisions made',
    ['decision_type']
)

reasoning_hypothesis_tested = Counter(
    'reasoning_service_hypotheses_tested_total',
    'Total number of hypotheses tested'
)

coordination_active_workflows = Gauge(
    'coordination_service_active_workflows',
    'Number of active workflows'
)

coordination_agents_registered = Gauge(
    'coordination_service_agents_registered',
    'Number of registered agents'
)

memory_vectors_stored = Gauge(
    'memory_service_vectors_stored',
    'Number of vectors stored in memory service'
)

memory_retrieval_latency = Histogram(
    'memory_service_retrieval_latency_seconds',
    'Memory retrieval latency',
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)


def track_request_metrics(service_name: str):
    """Decorator to track request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            endpoint = kwargs.get('request', {}).get('path', 'unknown')
            method = kwargs.get('request', {}).get('method', 'unknown')
            
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                error_count.labels(
                    service=service_name,
                    error_type=type(e).__name__,
                    endpoint=endpoint
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                request_count.labels(
                    service=service_name,
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                request_duration.labels(
                    service=service_name,
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator


def update_service_metrics(service_name: str, health_data: dict):
    """Update service-specific metrics based on health data"""
    try:
        # Update service info
        service_info.labels(
            service=service_name,
            version=health_data.get('version', 'unknown'),
            status=health_data.get('status', 'unknown')
        ).set(1)
        
        # Update service-specific metrics
        if service_name == 'learning-service':
            if 'patterns_stored' in health_data:
                learning_patterns_stored.set(health_data['patterns_stored'])
            if 'knowledge_graph_nodes' in health_data:
                learning_knowledge_nodes.set(health_data['knowledge_graph_nodes'])
            if 'knowledge_graph_edges' in health_data:
                learning_knowledge_edges.set(health_data['knowledge_graph_edges'])
                
        elif service_name == 'reasoning-service':
            perf_metrics = health_data.get('performance_metrics', {})
            if 'total_decisions' in perf_metrics:
                for decision_type, count in perf_metrics.get('decisions_by_type', {}).items():
                    reasoning_decisions_made.labels(decision_type=decision_type).inc(count)
            if 'hypotheses_tested' in perf_metrics:
                reasoning_hypothesis_tested.inc(perf_metrics['hypotheses_tested'])
                
        elif service_name == 'coordination-service':
            if 'workflow_manager' in health_data:
                coordination_active_workflows.set(
                    health_data['workflow_manager'].get('active_workflows', 0)
                )
            if 'agent_registry' in health_data:
                coordination_agents_registered.set(
                    health_data['agent_registry'].get('total_agents', 0)
                )
                
        elif service_name == 'hybrid-memory-service':
            checks = health_data.get('checks', {})
            if 'qdrant' in checks:
                qdrant_info = checks['qdrant'].get('collection_info', {})
                memory_vectors_stored.set(qdrant_info.get('points_count', 0))
                
    except Exception as e:
        logger.error(f"Failed to update metrics for {service_name}: {e}")


async def metrics_endpoint(request):
    """Generate Prometheus metrics endpoint response"""
    metrics = generate_latest()
    return web.Response(body=metrics, content_type=CONTENT_TYPE_LATEST)


def setup_metrics_endpoint(app, service_name: str):
    """Setup metrics endpoint for a service"""
    from aiohttp import web
    
    # Add metrics endpoint
    app.router.add_get('/metrics', metrics_endpoint)
    
    # Initialize service info
    service_info.labels(
        service=service_name,
        version='1.0.0',
        status='starting'
    ).set(1)
    
    logger.info(f"Metrics endpoint configured for {service_name}")
    
    return app