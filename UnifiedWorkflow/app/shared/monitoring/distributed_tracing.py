"""
Distributed tracing implementation for the AI Workflow Engine.

This module provides:
- Request flow tracing across services
- Performance analysis and bottleneck identification
- Error correlation across the system
- Integration with OpenTelemetry
- Custom span creation and context propagation
"""

import time
import uuid
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from enum import Enum
import traceback

# OpenTelemetry imports (optional - graceful degradation if not available)
try:
    from opentelemetry import trace, context, propagate
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from shared.monitoring.structured_logging import get_logger
from shared.monitoring.prometheus_metrics import metrics

logger = get_logger(__name__)


class SpanKind(Enum):
    """Span kind enumeration."""
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class SpanData:
    """Container for span data."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    kind: SpanKind = SpanKind.INTERNAL
    service_name: str = "ai_workflow_engine"
    tags: Dict[str, Any] = None
    logs: List[Dict[str, Any]] = None
    baggage: Dict[str, str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []
        if self.baggage is None:
            self.baggage = {}
    
    def finish(self, status: SpanStatus = SpanStatus.OK, error: str = None):
        """Finish the span."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
        if error:
            self.error = error
    
    def add_tag(self, key: str, value: Any):
        """Add a tag to the span."""
        self.tags[key] = value
    
    def add_log(self, event: str, **kwargs):
        """Add a log entry to the span."""
        log_entry = {
            'timestamp': time.time(),
            'event': event,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def set_baggage(self, key: str, value: str):
        """Set baggage item."""
        self.baggage[key] = value


# Context variables for trace propagation
current_trace_id: ContextVar[str] = ContextVar('current_trace_id', default='')
current_span_id: ContextVar[str] = ContextVar('current_span_id', default='')
current_span: ContextVar[Optional[SpanData]] = ContextVar('current_span', default=None)


class TraceCollector:
    """
    Collects and manages distributed traces.
    
    Features:
    - In-memory trace storage with configurable retention
    - Trace analysis and performance insights
    - Error correlation and debugging support
    - Integration with external tracing systems
    """
    
    def __init__(self, 
                 retention_hours: int = 24,
                 max_traces: int = 10000,
                 enable_sampling: bool = True,
                 sampling_rate: float = 0.1):
        
        self.retention_hours = retention_hours
        self.max_traces = max_traces
        self.enable_sampling = enable_sampling
        self.sampling_rate = sampling_rate
        
        # Storage
        self.traces: Dict[str, List[SpanData]] = {}
        self.span_index: Dict[str, SpanData] = {}
        self.service_operations: Dict[str, set] = defaultdict(set)
        
        # Performance tracking
        self.operation_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # OpenTelemetry integration
        self.otel_tracer = None
        if OPENTELEMETRY_AVAILABLE:
            self._setup_opentelemetry()
        
        logger.info("TraceCollector initialized")
    
    def _setup_opentelemetry(self):
        """Setup OpenTelemetry tracing."""
        try:
            # Create tracer provider
            trace.set_tracer_provider(TracerProvider())
            
            # Configure Jaeger exporter (if Jaeger is available)
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
            )
            
            # Create span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Get tracer
            self.otel_tracer = trace.get_tracer(__name__)
            
            logger.info("OpenTelemetry tracing configured with Jaeger")
        
        except Exception as e:
            logger.warning(f"Failed to setup OpenTelemetry: {str(e)}")
            self.otel_tracer = None
    
    def should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        if not self.enable_sampling:
            return True
        
        import random
        return random.random() < self.sampling_rate
    
    def start_span(self,
                   operation_name: str,
                   parent_span: Optional[SpanData] = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   service_name: str = "ai_workflow_engine",
                   tags: Dict[str, Any] = None) -> SpanData:
        """Start a new span."""
        
        # Generate IDs
        span_id = str(uuid.uuid4())
        
        if parent_span:
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        else:
            trace_id = current_trace_id.get() or str(uuid.uuid4())
            parent_span_id = current_span_id.get() or None
        
        # Create span
        span = SpanData(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            kind=kind,
            service_name=service_name,
            tags=tags or {}
        )
        
        # Store span
        self.span_index[span_id] = span
        
        if trace_id not in self.traces:
            self.traces[trace_id] = []
        self.traces[trace_id].append(span)
        
        # Track service operations
        self.service_operations[service_name].add(operation_name)
        
        # Set as current span
        current_trace_id.set(trace_id)
        current_span_id.set(span_id)
        current_span.set(span)
        
        logger.debug(f"Started span: {operation_name} (trace_id={trace_id}, span_id={span_id})")
        
        return span
    
    def finish_span(self, span: SpanData, 
                   status: SpanStatus = SpanStatus.OK,
                   error: str = None):
        """Finish a span."""
        span.finish(status, error)
        
        # Record performance stats
        self.operation_stats[span.operation_name].append({
            'duration': span.duration,
            'timestamp': span.end_time,
            'status': status,
            'service': span.service_name
        })
        
        # Track error patterns
        if status == SpanStatus.ERROR:
            error_key = f"{span.service_name}:{span.operation_name}"
            self.error_patterns[error_key] += 1
        
        # Update Prometheus metrics
        self._update_trace_metrics(span)
        
        logger.debug(f"Finished span: {span.operation_name} "
                    f"(duration={span.duration:.3f}s, status={status.value})")
        
        # Cleanup old traces periodically
        if len(self.traces) > self.max_traces:
            self._cleanup_old_traces()
    
    def _update_trace_metrics(self, span: SpanData):
        """Update Prometheus metrics with span data."""
        try:
            # Record request duration
            metrics.http_request_duration_seconds.labels(
                method=span.tags.get('http.method', 'unknown'),
                endpoint=span.tags.get('http.route', span.operation_name)
            ).observe(span.duration)
            
            # Record service operation duration
            if span.service_name and span.operation_name:
                operation_key = f"{span.service_name}.{span.operation_name}"
                
                # Use AI task metrics for AI-related operations
                if 'ai' in span.operation_name.lower() or 'task' in span.operation_name.lower():
                    metrics.ai_task_duration_seconds.labels(
                        task_type=span.tags.get('task.type', 'unknown'),
                        model=span.tags.get('ai.model', 'unknown')
                    ).observe(span.duration)
        
        except Exception as e:
            logger.warning(f"Failed to update trace metrics: {str(e)}")
    
    def _cleanup_old_traces(self):
        """Clean up old traces to prevent memory exhaustion."""
        try:
            cutoff_time = time.time() - (self.retention_hours * 3600)
            traces_to_remove = []
            
            for trace_id, spans in self.traces.items():
                if all(span.start_time < cutoff_time for span in spans):
                    traces_to_remove.append(trace_id)
            
            for trace_id in traces_to_remove:
                spans = self.traces.pop(trace_id, [])
                for span in spans:
                    self.span_index.pop(span.span_id, None)
            
            if traces_to_remove:
                logger.debug(f"Cleaned up {len(traces_to_remove)} old traces")
        
        except Exception as e:
            logger.error(f"Error cleaning up traces: {str(e)}")
    
    def get_trace(self, trace_id: str) -> Optional[List[SpanData]]:
        """Get trace by ID."""
        return self.traces.get(trace_id)
    
    def get_span(self, span_id: str) -> Optional[SpanData]:
        """Get span by ID."""
        return self.span_index.get(span_id)
    
    def get_operation_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """Get operation performance statistics."""
        if operation_name:
            stats_data = list(self.operation_stats[operation_name])
        else:
            stats_data = []
            for op_stats in self.operation_stats.values():
                stats_data.extend(list(op_stats))
        
        if not stats_data:
            return {}
        
        durations = [s['duration'] for s in stats_data]
        
        return {
            'count': len(stats_data),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'p50_duration': sorted(durations)[len(durations) // 2],
            'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
            'p99_duration': sorted(durations)[int(len(durations) * 0.99)],
            'error_count': sum(1 for s in stats_data if s['status'] == SpanStatus.ERROR),
        }
    
    def get_service_map(self) -> Dict[str, Any]:
        """Generate service dependency map."""
        service_map = {
            'services': list(self.service_operations.keys()),
            'operations': dict(self.service_operations),
            'dependencies': []
        }
        
        # Analyze dependencies from traces
        dependencies = defaultdict(set)
        
        for spans in self.traces.values():
            for span in spans:
                if span.parent_span_id:
                    parent_span = self.span_index.get(span.parent_span_id)
                    if parent_span and parent_span.service_name != span.service_name:
                        dependencies[parent_span.service_name].add(span.service_name)
        
        # Convert to list format
        for service, deps in dependencies.items():
            for dep in deps:
                service_map['dependencies'].append({
                    'source': service,
                    'target': dep
                })
        
        return service_map


# Global trace collector
trace_collector = TraceCollector()


class TracingSpan:
    """Context manager for distributed tracing spans."""
    
    def __init__(self,
                 operation_name: str,
                 kind: SpanKind = SpanKind.INTERNAL,
                 service_name: str = "ai_workflow_engine",
                 tags: Dict[str, Any] = None):
        
        self.operation_name = operation_name
        self.kind = kind
        self.service_name = service_name
        self.tags = tags or {}
        self.span: Optional[SpanData] = None
        self.parent_span = current_span.get()
    
    def __enter__(self) -> SpanData:
        """Enter the span context."""
        self.span = trace_collector.start_span(
            operation_name=self.operation_name,
            parent_span=self.parent_span,
            kind=self.kind,
            service_name=self.service_name,
            tags=self.tags
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context."""
        if self.span:
            status = SpanStatus.ERROR if exc_type else SpanStatus.OK
            error = str(exc_val) if exc_val else None
            trace_collector.finish_span(self.span, status, error)


def trace_operation(operation_name: str = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   service_name: str = "ai_workflow_engine",
                   capture_args: bool = False,
                   capture_result: bool = False):
    """
    Decorator for automatic operation tracing.
    
    Usage:
        @trace_operation("database_query", kind=SpanKind.CLIENT)
        async def get_user(user_id: str):
            # Your code here
            pass
    """
    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tags = {
                'function.name': func.__name__,
                'function.module': func.__module__
            }
            
            if capture_args and args:
                tags['function.args'] = str(args)[:200]  # Truncate long args
            
            if capture_args and kwargs:
                tags['function.kwargs'] = str(kwargs)[:200]
            
            with TracingSpan(op_name, kind, service_name, tags) as span:
                try:
                    result = await func(*args, **kwargs)
                    
                    if capture_result:
                        span.add_tag('function.result', str(result)[:200])
                    
                    return result
                
                except Exception as e:
                    span.add_tag('error', str(e))
                    span.add_log('exception', exception=str(e), traceback=traceback.format_exc())
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tags = {
                'function.name': func.__name__,
                'function.module': func.__module__
            }
            
            if capture_args and args:
                tags['function.args'] = str(args)[:200]
            
            if capture_args and kwargs:
                tags['function.kwargs'] = str(kwargs)[:200]
            
            with TracingSpan(op_name, kind, service_name, tags) as span:
                try:
                    result = func(*args, **kwargs)
                    
                    if capture_result:
                        span.add_tag('function.result', str(result)[:200])
                    
                    return result
                
                except Exception as e:
                    span.add_tag('error', str(e))
                    span.add_log('exception', exception=str(e), traceback=traceback.format_exc())
                    raise
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def create_child_span(operation_name: str, **kwargs) -> SpanData:
    """Create a child span from current context."""
    parent_span = current_span.get()
    return trace_collector.start_span(operation_name, parent_span, **kwargs)


def get_current_trace_id() -> str:
    """Get current trace ID."""
    return current_trace_id.get()


def get_current_span_id() -> str:
    """Get current span ID."""
    return current_span_id.get()


def get_current_span() -> Optional[SpanData]:
    """Get current span."""
    return current_span.get()


def inject_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject trace headers for HTTP propagation."""
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()
    
    if trace_id and span_id:
        headers['X-Trace-Id'] = trace_id
        headers['X-Span-Id'] = span_id
        headers['X-Parent-Span-Id'] = span_id
    
    return headers


def extract_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Extract trace headers from HTTP request."""
    extracted = {}
    
    trace_id = headers.get('X-Trace-Id') or headers.get('x-trace-id')
    if trace_id:
        extracted['trace_id'] = trace_id
    
    parent_span_id = headers.get('X-Parent-Span-Id') or headers.get('x-parent-span-id')
    if parent_span_id:
        extracted['parent_span_id'] = parent_span_id
    
    return extracted


def set_trace_context(trace_id: str, parent_span_id: str = None):
    """Set trace context from extracted headers."""
    current_trace_id.set(trace_id)
    if parent_span_id:
        current_span_id.set(parent_span_id)


# Utility functions for common tracing scenarios
def trace_http_request(method: str, url: str, status_code: int = None) -> TracingSpan:
    """Create span for HTTP request."""
    tags = {
        'http.method': method,
        'http.url': url,
        'span.kind': 'client'
    }
    
    if status_code:
        tags['http.status_code'] = status_code
    
    return TracingSpan(f"HTTP {method}", SpanKind.CLIENT, tags=tags)


def trace_database_query(operation: str, table: str = None) -> TracingSpan:
    """Create span for database query."""
    tags = {
        'db.operation': operation,
        'span.kind': 'client'
    }
    
    if table:
        tags['db.table'] = table
    
    return TracingSpan(f"DB {operation}", SpanKind.CLIENT, tags=tags)


def trace_ai_task(task_type: str, model: str = None) -> TracingSpan:
    """Create span for AI task processing."""
    tags = {
        'ai.task_type': task_type,
        'span.kind': 'internal'
    }
    
    if model:
        tags['ai.model'] = model
    
    return TracingSpan(f"AI {task_type}", SpanKind.INTERNAL, tags=tags)


# Integration with FastAPI (middleware)
class TracingMiddleware:
    """FastAPI middleware for distributed tracing."""
    
    def __init__(self, app, service_name: str = "ai_workflow_engine"):
        self.app = app
        self.service_name = service_name
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract trace context from headers
        headers = dict(scope.get("headers", []))
        header_dict = {k.decode(): v.decode() for k, v in headers.items()}
        
        trace_context = extract_trace_headers(header_dict)
        
        if trace_context.get('trace_id'):
            set_trace_context(
                trace_context['trace_id'],
                trace_context.get('parent_span_id')
            )
        
        # Create span for request
        method = scope["method"]
        path = scope["path"]
        
        tags = {
            'http.method': method,
            'http.path': path,
            'http.scheme': scope.get("scheme"),
            'span.kind': 'server'
        }
        
        with TracingSpan(f"HTTP {method} {path}", SpanKind.SERVER, self.service_name, tags):
            await self.app(scope, receive, send)