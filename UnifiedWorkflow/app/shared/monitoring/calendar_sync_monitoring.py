"""
Enhanced monitoring for calendar sync operations with focus on error detection.

This module provides:
- Calendar-specific metrics collection
- Database schema error detection (UndefinedColumn, NameError patterns)
- Circuit breaker monitoring
- Performance baseline tracking
- Alert generation for calendar sync failures
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import re

from prometheus_client import Counter, Histogram, Gauge, Summary
from shared.monitoring.prometheus_metrics import metrics
from shared.monitoring.distributed_tracing import trace_operation, TracingSpan, SpanKind

logger = logging.getLogger(__name__)


class CalendarSyncStatus(Enum):
    """Calendar sync status enumeration."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    SCHEMA_ERROR = "schema_error"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class ErrorPattern(Enum):
    """Error pattern classification."""
    UNDEFINED_COLUMN = "undefined_column"
    NAME_ERROR = "name_error"
    OAUTH_TOKEN_SCOPE = "oauth_token_scope_missing"
    DATABASE_SCHEMA = "database_schema_mismatch"
    AUTHENTICATION_FAILURE = "authentication_failure"
    NETWORK_TIMEOUT = "network_timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class CalendarSyncMetrics:
    """Container for calendar sync metrics."""
    user_id: int
    endpoint: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: CalendarSyncStatus = CalendarSyncStatus.SUCCESS
    error_pattern: Optional[ErrorPattern] = None
    error_message: Optional[str] = None
    events_synced: int = 0
    retry_count: int = 0
    circuit_breaker_triggered: bool = False


class CalendarSyncMonitor:
    """
    Enhanced monitoring for calendar sync operations.
    
    Features:
    - Error pattern detection and classification
    - Performance baseline tracking
    - Circuit breaker monitoring
    - Alert generation for critical patterns
    - Database schema error tracking
    """
    
    def __init__(self):
        self.sync_history: deque = deque(maxlen=1000)
        self.error_patterns: Dict[ErrorPattern, int] = defaultdict(int)
        self.user_failure_counts: Dict[int, int] = defaultdict(int)
        self.schema_errors: List[Dict[str, Any]] = []
        
        # Performance baselines
        self.baseline_duration: Optional[float] = None
        self.baseline_success_rate: Optional[float] = None
        
        # Initialize Prometheus metrics
        self._initialize_metrics()
        
        logger.info("CalendarSyncMonitor initialized")
    
    def _initialize_metrics(self):
        """Initialize calendar-specific Prometheus metrics."""
        
        # Calendar sync operation metrics
        self.calendar_sync_requests_total = Counter(
            'calendar_sync_requests_total',
            'Total calendar sync requests',
            ['user_id', 'endpoint', 'status', 'error_pattern']
        )
        
        self.calendar_sync_duration_seconds = Histogram(
            'calendar_sync_duration_seconds',
            'Calendar sync operation duration',
            ['endpoint', 'status'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 60.0)
        )
        
        self.calendar_sync_events_synced = Histogram(
            'calendar_sync_events_synced',
            'Number of events synced per operation',
            buckets=(0, 1, 5, 10, 25, 50, 100, 200, 500)
        )
        
        # Error pattern metrics
        self.calendar_sync_schema_errors_total = Counter(
            'calendar_sync_schema_errors_total',
            'Calendar sync database schema errors',
            ['error_type', 'table_name', 'column_name']
        )
        
        self.calendar_sync_oauth_token_errors_total = Counter(
            'calendar_sync_oauth_token_errors_total',
            'OAuth token related errors in calendar sync',
            ['error_subtype', 'user_id']
        )
        
        # Circuit breaker metrics
        self.calendar_sync_circuit_breaker_state = Gauge(
            'calendar_sync_circuit_breaker_state',
            'Calendar sync circuit breaker state (0=closed, 1=open)',
            ['user_id']
        )
        
        self.calendar_sync_consecutive_failures = Gauge(
            'calendar_sync_consecutive_failures',
            'Consecutive calendar sync failures per user',
            ['user_id']
        )
        
        # Performance baseline metrics
        self.calendar_sync_baseline_duration = Gauge(
            'calendar_sync_baseline_duration_seconds',
            'Calendar sync baseline duration in seconds'
        )
        
        self.calendar_sync_baseline_success_rate = Gauge(
            'calendar_sync_baseline_success_rate',
            'Calendar sync baseline success rate (0-1)'
        )
        
        # Health metrics
        self.calendar_sync_health_score = Gauge(
            'calendar_sync_health_score',
            'Calendar sync health score (0-100)',
            ['time_window']
        )
    
    def classify_error_pattern(self, error_message: str) -> ErrorPattern:
        """Classify error message into known patterns."""
        if not error_message:
            return ErrorPattern.UNKNOWN
        
        error_lower = error_message.lower()
        
        # Database schema errors
        if re.search(r'column.*does not exist', error_lower):
            return ErrorPattern.UNDEFINED_COLUMN
        if 'user_oauth_tokens.scope' in error_lower:
            return ErrorPattern.OAUTH_TOKEN_SCOPE
        if re.search(r'(undefinedcolumn|programmingerror)', error_lower):
            return ErrorPattern.DATABASE_SCHEMA
        
        # Python errors
        if 'nameerror' in error_lower:
            return ErrorPattern.NAME_ERROR
        
        # Authentication errors
        if re.search(r'(unauthorized|expired|token)', error_lower):
            return ErrorPattern.AUTHENTICATION_FAILURE
        
        # Network errors
        if re.search(r'(timeout|connection|network)', error_lower):
            return ErrorPattern.NETWORK_TIMEOUT
        
        # Rate limiting
        if re.search(r'(rate.limit|quota)', error_lower):
            return ErrorPattern.RATE_LIMIT
        
        return ErrorPattern.UNKNOWN
    
    @trace_operation("calendar_sync_monitor.start_sync", kind=SpanKind.INTERNAL)
    def start_sync_monitoring(self, user_id: int, endpoint: str) -> CalendarSyncMetrics:
        """Start monitoring a calendar sync operation."""
        sync_metrics = CalendarSyncMetrics(
            user_id=user_id,
            endpoint=endpoint,
            start_time=time.time()
        )
        
        logger.debug(f"Started monitoring calendar sync for user {user_id} on {endpoint}")
        return sync_metrics
    
    @trace_operation("calendar_sync_monitor.finish_sync", kind=SpanKind.INTERNAL)
    def finish_sync_monitoring(self, sync_metrics: CalendarSyncMetrics, 
                             status: CalendarSyncStatus,
                             error_message: Optional[str] = None,
                             events_synced: int = 0,
                             retry_count: int = 0):
        """Finish monitoring a calendar sync operation."""
        sync_metrics.end_time = time.time()
        sync_metrics.duration = sync_metrics.end_time - sync_metrics.start_time
        sync_metrics.status = status
        sync_metrics.events_synced = events_synced
        sync_metrics.retry_count = retry_count
        
        if error_message:
            sync_metrics.error_message = error_message
            sync_metrics.error_pattern = self.classify_error_pattern(error_message)
        
        # Update metrics
        self._update_prometheus_metrics(sync_metrics)
        
        # Update failure counts for circuit breaker
        self._update_failure_tracking(sync_metrics)
        
        # Store in history
        self.sync_history.append(sync_metrics)
        
        # Check for schema errors
        if sync_metrics.error_pattern in [ErrorPattern.UNDEFINED_COLUMN, 
                                        ErrorPattern.DATABASE_SCHEMA,
                                        ErrorPattern.OAUTH_TOKEN_SCOPE]:
            self._record_schema_error(sync_metrics)
        
        # Update baselines periodically
        if len(self.sync_history) % 10 == 0:
            self._update_baselines()
        
        logger.info(f"Finished monitoring calendar sync: user={sync_metrics.user_id}, "
                   f"status={status.value}, duration={sync_metrics.duration:.2f}s, "
                   f"events={events_synced}, pattern={sync_metrics.error_pattern}")
    
    def _update_prometheus_metrics(self, sync_metrics: CalendarSyncMetrics):
        """Update Prometheus metrics with sync data."""
        
        # Request counter
        self.calendar_sync_requests_total.labels(
            user_id=str(sync_metrics.user_id),
            endpoint=sync_metrics.endpoint,
            status=sync_metrics.status.value,
            error_pattern=sync_metrics.error_pattern.value if sync_metrics.error_pattern else 'none'
        ).inc()
        
        # Duration histogram
        self.calendar_sync_duration_seconds.labels(
            endpoint=sync_metrics.endpoint,
            status=sync_metrics.status.value
        ).observe(sync_metrics.duration)
        
        # Events synced
        self.calendar_sync_events_synced.observe(sync_metrics.events_synced)
        
        # Schema errors
        if sync_metrics.error_pattern == ErrorPattern.UNDEFINED_COLUMN:
            # Extract table and column from error message
            table_name = "user_oauth_tokens"  # Known from logs
            column_name = "scope"  # Known from logs
            
            self.calendar_sync_schema_errors_total.labels(
                error_type="undefined_column",
                table_name=table_name,
                column_name=column_name
            ).inc()
        
        # OAuth token errors
        if sync_metrics.error_pattern == ErrorPattern.OAUTH_TOKEN_SCOPE:
            self.calendar_sync_oauth_token_errors_total.labels(
                error_subtype="missing_scope_column",
                user_id=str(sync_metrics.user_id)
            ).inc()
    
    def _update_failure_tracking(self, sync_metrics: CalendarSyncMetrics):
        """Update failure tracking for circuit breaker logic."""
        user_id = sync_metrics.user_id
        
        if sync_metrics.status in [CalendarSyncStatus.FAILURE, 
                                 CalendarSyncStatus.SCHEMA_ERROR,
                                 CalendarSyncStatus.AUTH_ERROR]:
            self.user_failure_counts[user_id] += 1
        else:
            # Reset on success
            self.user_failure_counts[user_id] = 0
        
        # Update circuit breaker state metric
        failure_count = self.user_failure_counts[user_id]
        circuit_breaker_open = failure_count >= 3
        
        self.calendar_sync_circuit_breaker_state.labels(
            user_id=str(user_id)
        ).set(1 if circuit_breaker_open else 0)
        
        self.calendar_sync_consecutive_failures.labels(
            user_id=str(user_id)
        ).set(failure_count)
        
        if circuit_breaker_open:
            sync_metrics.circuit_breaker_triggered = True
    
    def _record_schema_error(self, sync_metrics: CalendarSyncMetrics):
        """Record detailed schema error for analysis."""
        schema_error = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': sync_metrics.user_id,
            'endpoint': sync_metrics.endpoint,
            'error_pattern': sync_metrics.error_pattern.value,
            'error_message': sync_metrics.error_message,
            'duration': sync_metrics.duration
        }
        
        self.schema_errors.append(schema_error)
        
        # Keep only recent schema errors
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.schema_errors = [
            err for err in self.schema_errors 
            if datetime.fromisoformat(err['timestamp']) > cutoff_time
        ]
        
        logger.error(f"Schema error recorded: {schema_error}")
    
    def _update_baselines(self):
        """Update performance baselines based on recent successful operations."""
        if not self.sync_history:
            return
        
        # Get successful operations from last 24 hours
        cutoff_time = time.time() - 86400  # 24 hours
        recent_successful = [
            sync for sync in self.sync_history
            if (sync.start_time > cutoff_time and 
                sync.status == CalendarSyncStatus.SUCCESS and
                sync.duration is not None)
        ]
        
        if not recent_successful:
            return
        
        # Calculate baseline duration (95th percentile of successful operations)
        durations = [sync.duration for sync in recent_successful]
        durations.sort()
        if durations:
            baseline_duration = durations[int(len(durations) * 0.95)]
            self.baseline_duration = baseline_duration
            self.calendar_sync_baseline_duration.set(baseline_duration)
        
        # Calculate success rate
        total_recent = [
            sync for sync in self.sync_history
            if sync.start_time > cutoff_time
        ]
        
        if total_recent:
            success_rate = len(recent_successful) / len(total_recent)
            self.baseline_success_rate = success_rate
            self.calendar_sync_baseline_success_rate.set(success_rate)
        
        # Calculate health scores for different time windows
        for window_hours in [1, 6, 24]:
            health_score = self._calculate_health_score(window_hours)
            self.calendar_sync_health_score.labels(
                time_window=f"{window_hours}h"
            ).set(health_score)
    
    def _calculate_health_score(self, window_hours: int) -> float:
        """Calculate calendar sync health score for a time window."""
        cutoff_time = time.time() - (window_hours * 3600)
        
        window_syncs = [
            sync for sync in self.sync_history
            if sync.start_time > cutoff_time
        ]
        
        if not window_syncs:
            return 100.0  # No data means healthy
        
        # Success rate component (0-50 points)
        successful = sum(1 for sync in window_syncs 
                        if sync.status == CalendarSyncStatus.SUCCESS)
        success_rate = successful / len(window_syncs)
        success_score = success_rate * 50
        
        # Performance component (0-30 points)
        performance_score = 30.0
        if self.baseline_duration:
            avg_duration = sum(sync.duration for sync in window_syncs 
                             if sync.duration) / len(window_syncs)
            if avg_duration > self.baseline_duration * 2:
                performance_score = 10.0
            elif avg_duration > self.baseline_duration * 1.5:
                performance_score = 20.0
        
        # Error pattern component (0-20 points)
        schema_errors = sum(1 for sync in window_syncs 
                          if sync.error_pattern in [ErrorPattern.UNDEFINED_COLUMN,
                                                  ErrorPattern.DATABASE_SCHEMA,
                                                  ErrorPattern.OAUTH_TOKEN_SCOPE])
        if schema_errors == 0:
            error_score = 20.0
        elif schema_errors < len(window_syncs) * 0.1:  # Less than 10%
            error_score = 15.0
        elif schema_errors < len(window_syncs) * 0.25:  # Less than 25%
            error_score = 10.0
        else:
            error_score = 0.0
        
        return min(100.0, success_score + performance_score + error_score)
    
    def get_sync_statistics(self, user_id: Optional[int] = None, 
                           hours: int = 24) -> Dict[str, Any]:
        """Get calendar sync statistics for monitoring dashboard."""
        cutoff_time = time.time() - (hours * 3600)
        
        # Filter data
        filtered_syncs = [
            sync for sync in self.sync_history
            if (sync.start_time > cutoff_time and 
                (user_id is None or sync.user_id == user_id))
        ]
        
        if not filtered_syncs:
            return {
                'total_syncs': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
                'total_events_synced': 0,
                'error_patterns': {},
                'health_score': 100.0
            }
        
        successful = [sync for sync in filtered_syncs 
                     if sync.status == CalendarSyncStatus.SUCCESS]
        
        # Count error patterns
        error_pattern_counts = defaultdict(int)
        for sync in filtered_syncs:
            if sync.error_pattern:
                error_pattern_counts[sync.error_pattern.value] += 1
        
        return {
            'total_syncs': len(filtered_syncs),
            'success_rate': len(successful) / len(filtered_syncs),
            'avg_duration': sum(s.duration for s in filtered_syncs if s.duration) / len(filtered_syncs),
            'total_events_synced': sum(s.events_synced for s in filtered_syncs),
            'error_patterns': dict(error_pattern_counts),
            'health_score': self._calculate_health_score(hours),
            'schema_errors_count': len([s for s in filtered_syncs 
                                      if s.error_pattern in [ErrorPattern.UNDEFINED_COLUMN,
                                                           ErrorPattern.DATABASE_SCHEMA,
                                                           ErrorPattern.OAUTH_TOKEN_SCOPE]]),
            'baseline_duration': self.baseline_duration,
            'baseline_success_rate': self.baseline_success_rate
        }
    
    def get_recent_schema_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent schema errors for troubleshooting."""
        return self.schema_errors[-limit:]
    
    def should_trigger_alert(self, sync_metrics: CalendarSyncMetrics) -> Dict[str, Any]:
        """Determine if an alert should be triggered."""
        alerts = {}
        
        # Schema error alert (critical)
        if sync_metrics.error_pattern in [ErrorPattern.UNDEFINED_COLUMN,
                                        ErrorPattern.DATABASE_SCHEMA,
                                        ErrorPattern.OAUTH_TOKEN_SCOPE]:
            alerts['schema_error'] = {
                'severity': 'critical',
                'message': f'Database schema error in calendar sync: {sync_metrics.error_message}',
                'user_id': sync_metrics.user_id,
                'error_pattern': sync_metrics.error_pattern.value
            }
        
        # Circuit breaker alert
        if sync_metrics.circuit_breaker_triggered:
            alerts['circuit_breaker'] = {
                'severity': 'high',
                'message': f'Calendar sync circuit breaker opened for user {sync_metrics.user_id}',
                'user_id': sync_metrics.user_id,
                'consecutive_failures': self.user_failure_counts[sync_metrics.user_id]
            }
        
        # Performance degradation alert
        if (self.baseline_duration and sync_metrics.duration and 
            sync_metrics.duration > self.baseline_duration * 3):
            alerts['performance_degradation'] = {
                'severity': 'medium',
                'message': f'Calendar sync performance degradation detected',
                'duration': sync_metrics.duration,
                'baseline': self.baseline_duration,
                'user_id': sync_metrics.user_id
            }
        
        return alerts


# Global calendar sync monitor instance
calendar_sync_monitor = CalendarSyncMonitor()


# Convenience functions for easy integration
def start_calendar_sync_monitoring(user_id: int, endpoint: str) -> CalendarSyncMetrics:
    """Start monitoring a calendar sync operation."""
    return calendar_sync_monitor.start_sync_monitoring(user_id, endpoint)


def finish_calendar_sync_monitoring(sync_metrics: CalendarSyncMetrics,
                                   status: CalendarSyncStatus,
                                   error_message: Optional[str] = None,
                                   events_synced: int = 0,
                                   retry_count: int = 0):
    """Finish monitoring a calendar sync operation."""
    calendar_sync_monitor.finish_sync_monitoring(
        sync_metrics, status, error_message, events_synced, retry_count
    )


def get_calendar_sync_health() -> Dict[str, Any]:
    """Get calendar sync health statistics."""
    return calendar_sync_monitor.get_sync_statistics()


def check_schema_error_alerts() -> List[Dict[str, Any]]:
    """Check for recent schema error alerts."""
    recent_errors = calendar_sync_monitor.get_recent_schema_errors(limit=5)
    return [
        {
            'timestamp': error['timestamp'],
            'user_id': error['user_id'],
            'error_pattern': error['error_pattern'],
            'message': error['error_message']
        }
        for error in recent_errors
    ]