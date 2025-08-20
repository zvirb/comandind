"""Security metrics service for Prometheus integration and real-time security monitoring."""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from threading import Lock
from prometheus_client import Counter, Histogram, Gauge, Enum, start_http_server
from prometheus_client.core import CollectorRegistry, REGISTRY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_

from shared.database.models.security_models import SecurityViolation, DataAccessLog, AuditLog
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityMetricsCollector:
    """Prometheus metrics collector for security events."""
    
    def __init__(self):
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'security_auth_attempts_total',
            'Total authentication attempts',
            ['service', 'status', 'user_type']
        )
        
        self.auth_failures_total = Counter(
            'security_auth_failures_total',
            'Failed authentication attempts',
            ['service', 'failure_reason', 'ip_address']
        )
        
        self.jwt_token_operations_total = Counter(
            'security_jwt_operations_total',
            'JWT token operations',
            ['operation', 'status', 'token_type']
        )
        
        # Authorization metrics
        self.authz_violations_total = Counter(
            'security_authz_violations_total',
            'Authorization violations',
            ['service', 'violation_type', 'severity']
        )
        
        self.cross_service_auth_total = Counter(
            'security_cross_service_auth_total',
            'Cross-service authentication events',
            ['source_service', 'target_service', 'status']
        )
        
        # Security violation metrics
        self.security_violations_total = Counter(
            'security_violations_total',
            'Security violations by type and severity',
            ['violation_type', 'severity', 'service', 'blocked']
        )
        
        self.security_violation_rate = Gauge(
            'security_violation_rate_per_minute',
            'Security violations per minute',
            ['severity']
        )
        
        # Data access metrics
        self.data_access_total = Counter(
            'security_data_access_total',
            'Data access events',
            ['service', 'access_type', 'table_name', 'sensitive']
        )
        
        self.data_access_volume = Counter(
            'security_data_access_volume_total',
            'Total rows accessed',
            ['service', 'table_name']
        )
        
        self.data_access_response_time = Histogram(
            'security_data_access_response_time_seconds',
            'Data access response time',
            ['service', 'access_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Database security metrics
        self.database_connections_active = Gauge(
            'security_database_connections_active',
            'Active database connections with security context'
        )
        
        self.rls_policy_violations = Counter(
            'security_rls_policy_violations_total',
            'Row-level security policy violations',
            ['table_name', 'user_id']
        )
        
        # Tool execution security metrics
        self.tool_execution_security_total = Counter(
            'security_tool_execution_total',
            'Tool execution security events',
            ['tool_name', 'security_level', 'status']
        )
        
        self.sandbox_violations_total = Counter(
            'security_sandbox_violations_total',
            'Sandbox violation attempts',
            ['tool_name', 'violation_type']
        )
        
        # WebSocket security metrics
        self.websocket_connections_total = Counter(
            'security_websocket_connections_total',
            'WebSocket connection events',
            ['status', 'auth_method']
        )
        
        self.websocket_auth_failures_total = Counter(
            'security_websocket_auth_failures_total',
            'WebSocket authentication failures',
            ['failure_reason']
        )
        
        # Network security metrics
        self.network_requests_total = Counter(
            'security_network_requests_total',
            'Network requests with security validation',
            ['service', 'method', 'status_code']
        )
        
        self.ssl_certificate_status = Enum(
            'security_ssl_certificate_status',
            'SSL certificate status',
            ['service'],
            states=['valid', 'expired', 'expiring_soon', 'invalid']
        )
        
        # Resource usage security metrics
        self.resource_usage_violations = Counter(
            'security_resource_usage_violations_total',
            'Resource usage security violations',
            ['resource_type', 'violation_type', 'service']
        )
        
        self.concurrent_sessions_gauge = Gauge(
            'security_concurrent_sessions',
            'Concurrent user sessions',
            ['user_type']
        )
        
        # Threat detection metrics
        self.threat_detections_total = Counter(
            'security_threat_detections_total',
            'Threat detection events',
            ['threat_type', 'severity', 'source']
        )
        
        self.anomaly_scores = Histogram(
            'security_anomaly_scores',
            'Security anomaly detection scores',
            ['detection_type'],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
        )
        
        # Rate limiting metrics
        self.rate_limit_violations = Counter(
            'security_rate_limit_violations_total',
            'Rate limiting violations',
            ['endpoint', 'user_id', 'ip_address']
        )
        
        # Security audit metrics
        self.audit_log_entries_total = Counter(
            'security_audit_log_entries_total',
            'Audit log entries created',
            ['operation', 'table_name']
        )
        
        # System security health
        self.security_health_score = Gauge(
            'security_health_score',
            'Overall security health score (0-100)'
        )
        
        self.security_monitoring_status = Enum(
            'security_monitoring_status',
            'Security monitoring system status',
            states=['healthy', 'degraded', 'critical', 'offline']
        )


class SecurityMetricsService:
    """Comprehensive security metrics service with real-time monitoring."""
    
    def __init__(self):
        self.logger = logger
        self.metrics = SecurityMetricsCollector()
        self.running = False
        self.monitoring_tasks: Set[asyncio.Task] = set()
        
        # Rate limiting tracking
        self.rate_limit_windows: Dict[str, deque] = defaultdict(lambda: deque())
        self.rate_limit_lock = Lock()
        
        # Anomaly detection state
        self.baseline_metrics: Dict[str, Any] = {}
        self.anomaly_thresholds = {
            'auth_failure_rate': 0.1,  # 10% failure rate threshold
            'data_access_spike': 2.0,  # 2x baseline access rate
            'violation_burst': 5,      # 5 violations in 5 minutes
            'concurrent_sessions': 100  # Max concurrent sessions per user type
        }
        
        # Metrics HTTP server port
        self.metrics_port = getattr(settings, 'security_metrics_port', 9091)
        
    async def start_monitoring(self) -> None:
        """Start security metrics monitoring."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting security metrics monitoring service")
        
        try:
            # Start Prometheus metrics HTTP server
            start_http_server(self.metrics_port)
            self.logger.info(f"Security metrics HTTP server started on port {self.metrics_port}")
            
            # Start monitoring tasks
            tasks = [
                self._monitor_security_violations(),
                self._monitor_authentication_events(),
                self._monitor_data_access_patterns(),
                self._monitor_system_health(),
                self._calculate_security_health_score(),
                self._detect_security_anomalies(),
                self._monitor_rate_limits(),
                self._cleanup_old_metrics()
            ]
            
            for task_coro in tasks:
                task = asyncio.create_task(task_coro)
                self.monitoring_tasks.add(task)
                # Remove task from set when it completes
                task.add_done_callback(self.monitoring_tasks.discard)
            
            self.logger.info(f"Started {len(tasks)} security monitoring tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to start security monitoring: {str(e)}")
            self.running = False
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop security metrics monitoring."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping security metrics monitoring service")
        
        # Cancel all monitoring tasks
        for task in list(self.monitoring_tasks):
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        self.logger.info("Security metrics monitoring stopped")
    
    # Authentication and Authorization Metrics
    
    def record_authentication_attempt(
        self,
        service: str,
        status: str,
        user_type: str = "regular",
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Record authentication attempt."""
        self.metrics.auth_attempts_total.labels(
            service=service,
            status=status,
            user_type=user_type
        ).inc()
        
        if status == "failed" and failure_reason:
            self.metrics.auth_failures_total.labels(
                service=service,
                failure_reason=failure_reason,
                ip_address=ip_address or "unknown"
            ).inc()
    
    def record_jwt_operation(
        self,
        operation: str,
        status: str,
        token_type: str = "access"
    ) -> None:
        """Record JWT token operation."""
        self.metrics.jwt_token_operations_total.labels(
            operation=operation,
            status=status,
            token_type=token_type
        ).inc()
    
    def record_authorization_violation(
        self,
        service: str,
        violation_type: str,
        severity: str
    ) -> None:
        """Record authorization violation."""
        self.metrics.authz_violations_total.labels(
            service=service,
            violation_type=violation_type,
            severity=severity
        ).inc()
    
    def record_cross_service_auth(
        self,
        source_service: str,
        target_service: str,
        status: str
    ) -> None:
        """Record cross-service authentication event."""
        self.metrics.cross_service_auth_total.labels(
            source_service=source_service,
            target_service=target_service,
            status=status
        ).inc()
    
    # Security Violation Metrics
    
    def record_security_violation(
        self,
        violation_type: str,
        severity: str,
        service: str,
        blocked: bool = True
    ) -> None:
        """Record security violation."""
        self.metrics.security_violations_total.labels(
            violation_type=violation_type,
            severity=severity,
            service=service,
            blocked=str(blocked).lower()
        ).inc()
    
    # Data Access Metrics
    
    def record_data_access(
        self,
        service: str,
        access_type: str,
        table_name: str,
        row_count: int = 1,
        sensitive: bool = False,
        response_time_seconds: Optional[float] = None
    ) -> None:
        """Record data access event."""
        self.metrics.data_access_total.labels(
            service=service,
            access_type=access_type,
            table_name=table_name,
            sensitive=str(sensitive).lower()
        ).inc()
        
        self.metrics.data_access_volume.labels(
            service=service,
            table_name=table_name
        ).inc(row_count)
        
        if response_time_seconds is not None:
            self.metrics.data_access_response_time.labels(
                service=service,
                access_type=access_type
            ).observe(response_time_seconds)
    
    # Tool Execution and Sandbox Metrics
    
    def record_tool_execution_security(
        self,
        tool_name: str,
        security_level: str,
        status: str
    ) -> None:
        """Record tool execution security event."""
        self.metrics.tool_execution_security_total.labels(
            tool_name=tool_name,
            security_level=security_level,
            status=status
        ).inc()
    
    def record_sandbox_violation(
        self,
        tool_name: str,
        violation_type: str
    ) -> None:
        """Record sandbox violation."""
        self.metrics.sandbox_violations_total.labels(
            tool_name=tool_name,
            violation_type=violation_type
        ).inc()
    
    # WebSocket Security Metrics
    
    def record_websocket_connection(
        self,
        status: str,
        auth_method: str = "jwt"
    ) -> None:
        """Record WebSocket connection event."""
        self.metrics.websocket_connections_total.labels(
            status=status,
            auth_method=auth_method
        ).inc()
    
    def record_websocket_auth_failure(
        self,
        failure_reason: str
    ) -> None:
        """Record WebSocket authentication failure."""
        self.metrics.websocket_auth_failures_total.labels(
            failure_reason=failure_reason
        ).inc()
    
    # Network and SSL Metrics
    
    def record_network_request(
        self,
        service: str,
        method: str,
        status_code: int
    ) -> None:
        """Record network request with security validation."""
        self.metrics.network_requests_total.labels(
            service=service,
            method=method,
            status_code=str(status_code)
        ).inc()
    
    def update_ssl_certificate_status(
        self,
        service: str,
        status: str
    ) -> None:
        """Update SSL certificate status."""
        self.metrics.ssl_certificate_status.labels(service=service).state(status)
    
    # Resource Usage and Rate Limiting
    
    def record_resource_violation(
        self,
        resource_type: str,
        violation_type: str,
        service: str
    ) -> None:
        """Record resource usage violation."""
        self.metrics.resource_usage_violations.labels(
            resource_type=resource_type,
            violation_type=violation_type,
            service=service
        ).inc()
    
    def update_concurrent_sessions(
        self,
        user_type: str,
        count: int
    ) -> None:
        """Update concurrent sessions count."""
        self.metrics.concurrent_sessions_gauge.labels(user_type=user_type).set(count)
    
    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> bool:
        """Check if rate limit is exceeded."""
        current_time = time.time()
        
        with self.rate_limit_lock:
            window = self.rate_limit_windows[key]
            
            # Remove old entries outside the window
            while window and window[0] < current_time - window_seconds:
                window.popleft()
            
            # Check if limit is exceeded
            if len(window) >= limit:
                # Record rate limit violation
                parts = key.split(':')
                self.metrics.rate_limit_violations.labels(
                    endpoint=parts[0] if len(parts) > 0 else "unknown",
                    user_id=parts[1] if len(parts) > 1 else "unknown",
                    ip_address=parts[2] if len(parts) > 2 else "unknown"
                ).inc()
                return False
            
            # Add current request
            window.append(current_time)
            return True
    
    # Threat Detection Metrics
    
    def record_threat_detection(
        self,
        threat_type: str,
        severity: str,
        source: str,
        anomaly_score: Optional[float] = None
    ) -> None:
        """Record threat detection event."""
        self.metrics.threat_detections_total.labels(
            threat_type=threat_type,
            severity=severity,
            source=source
        ).inc()
        
        if anomaly_score is not None:
            self.metrics.anomaly_scores.labels(
                detection_type=threat_type
            ).observe(anomaly_score)
    
    # Audit and System Health
    
    def record_audit_log_entry(
        self,
        operation: str,
        table_name: str
    ) -> None:
        """Record audit log entry creation."""
        self.metrics.audit_log_entries_total.labels(
            operation=operation,
            table_name=table_name
        ).inc()
    
    def update_security_health_score(self, score: float) -> None:
        """Update overall security health score."""
        self.metrics.security_health_score.set(score)
    
    def update_monitoring_status(self, status: str) -> None:
        """Update security monitoring system status."""
        self.metrics.security_monitoring_status.state(status)
    
    # Monitoring Tasks
    
    async def _monitor_security_violations(self) -> None:
        """Monitor security violations from database."""
        while self.running:
            try:
                async for session in get_async_session():
                    # Get violations from the last minute
                    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
                    
                    result = await session.execute(
                        text("""
                            SELECT violation_type, severity, COUNT(*) as count
                            FROM audit.security_violations
                            WHERE created_at >= :since
                            GROUP BY violation_type, severity
                        """),
                        {'since': one_minute_ago}
                    )
                    
                    # Update violation rate metrics
                    for row in result.fetchall():
                        self.metrics.security_violation_rate.labels(
                            severity=row.severity
                        ).set(row.count)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring security violations: {str(e)}")
                await asyncio.sleep(60)
    
    async def _monitor_authentication_events(self) -> None:
        """Monitor authentication events and patterns."""
        while self.running:
            try:
                async for session in get_async_session():
                    # Monitor for brute force attacks
                    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
                    
                    result = await session.execute(
                        text("""
                            SELECT ip_address, COUNT(*) as failure_count
                            FROM audit.security_violations
                            WHERE violation_type LIKE '%AUTH%'
                            AND severity IN ('HIGH', 'CRITICAL')
                            AND created_at >= :since
                            GROUP BY ip_address
                            HAVING COUNT(*) >= 5
                        """),
                        {'since': five_minutes_ago}
                    )
                    
                    # Record potential brute force attacks
                    for row in result.fetchall():
                        self.record_threat_detection(
                            threat_type="brute_force",
                            severity="HIGH",
                            source=row.ip_address or "unknown",
                            anomaly_score=min(1.0, row.failure_count / 10.0)
                        )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring authentication events: {str(e)}")
                await asyncio.sleep(300)
    
    async def _monitor_data_access_patterns(self) -> None:
        """Monitor data access patterns for anomalies."""
        while self.running:
            try:
                async for session in get_async_session():
                    # Monitor for unusual data access patterns
                    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                    
                    result = await session.execute(
                        text("""
                            SELECT 
                                user_id,
                                service_name,
                                COUNT(*) as access_count,
                                SUM(row_count) as total_rows,
                                COUNT(CASE WHEN sensitive_data_accessed THEN 1 END) as sensitive_count
                            FROM audit.data_access_log
                            WHERE created_at >= :since
                            GROUP BY user_id, service_name
                            HAVING COUNT(*) > 100 OR SUM(row_count) > 10000
                        """),
                        {'since': one_hour_ago}
                    )
                    
                    # Record anomalous access patterns
                    for row in result.fetchall():
                        anomaly_score = min(1.0, max(
                            row.access_count / 200.0,  # Normalize access count
                            row.total_rows / 20000.0   # Normalize row count
                        ))
                        
                        self.record_threat_detection(
                            threat_type="data_access_anomaly",
                            severity="MEDIUM" if anomaly_score < 0.7 else "HIGH",
                            source=f"user_{row.user_id}",
                            anomaly_score=anomaly_score
                        )
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error monitoring data access patterns: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _monitor_system_health(self) -> None:
        """Monitor overall system security health."""
        while self.running:
            try:
                async for session in get_async_session():
                    # Check database security health
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
                    )
                    active_connections = result.scalar()
                    
                    self.metrics.database_connections_active.set(active_connections)
                    
                    # Update monitoring status based on system health
                    if active_connections > 100:
                        self.update_monitoring_status("degraded")
                    elif active_connections > 200:
                        self.update_monitoring_status("critical")
                    else:
                        self.update_monitoring_status("healthy")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring system health: {str(e)}")
                self.update_monitoring_status("offline")
                await asyncio.sleep(60)
    
    async def _calculate_security_health_score(self) -> None:
        """Calculate and update security health score."""
        while self.running:
            try:
                async for session in get_async_session():
                    # Get metrics for health score calculation
                    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                    
                    # Count violations by severity
                    violation_result = await session.execute(
                        text("""
                            SELECT severity, COUNT(*) as count
                            FROM audit.security_violations
                            WHERE created_at >= :since
                            GROUP BY severity
                        """),
                        {'since': one_hour_ago}
                    )
                    
                    violations = {row.severity: row.count for row in violation_result.fetchall()}
                    
                    # Calculate health score (0-100)
                    base_score = 100.0
                    
                    # Deduct points for violations
                    critical_violations = violations.get('CRITICAL', 0)
                    high_violations = violations.get('HIGH', 0)
                    medium_violations = violations.get('MEDIUM', 0)
                    low_violations = violations.get('LOW', 0)
                    
                    score_deduction = (
                        critical_violations * 10 +  # -10 points per critical
                        high_violations * 5 +       # -5 points per high
                        medium_violations * 2 +     # -2 points per medium
                        low_violations * 0.5        # -0.5 points per low
                    )
                    
                    health_score = max(0.0, base_score - score_deduction)
                    
                    self.update_security_health_score(health_score)
                    
                    self.logger.debug(f"Security health score updated: {health_score:.2f}")
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error calculating security health score: {str(e)}")
                await asyncio.sleep(300)
    
    async def _detect_security_anomalies(self) -> None:
        """Detect security anomalies using statistical analysis."""
        while self.running:
            try:
                # Use the security audit service's anomaly detection
                async for session in get_async_session():
                    anomalies = await security_audit_service.detect_security_anomalies(session)
                    
                    for anomaly in anomalies:
                        self.record_threat_detection(
                            threat_type=anomaly['anomaly_type'],
                            severity=anomaly['severity'],
                            source="system_detection"
                        )
                
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Error detecting security anomalies: {str(e)}")
                await asyncio.sleep(1800)
    
    async def _monitor_rate_limits(self) -> None:
        """Monitor and clean up rate limiting data."""
        while self.running:
            try:
                current_time = time.time()
                
                with self.rate_limit_lock:
                    # Clean up old rate limit windows
                    expired_keys = []
                    for key, window in self.rate_limit_windows.items():
                        # Remove entries older than 1 hour
                        while window and window[0] < current_time - 3600:
                            window.popleft()
                        
                        # Mark empty windows for removal
                        if not window:
                            expired_keys.append(key)
                    
                    # Remove expired keys
                    for key in expired_keys:
                        del self.rate_limit_windows[key]
                
                await asyncio.sleep(600)  # Clean up every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring rate limits: {str(e)}")
                await asyncio.sleep(600)
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics and optimize memory usage."""
        while self.running:
            try:
                # This would typically involve resetting counters or aggregating historical data
                # For now, just log the cleanup operation
                self.logger.debug("Performing security metrics cleanup")
                
                # In a production environment, you might:
                # 1. Export metrics to long-term storage
                # 2. Reset certain counters
                # 3. Compact histogram buckets
                # 4. Clean up rate limiting data
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error during metrics cleanup: {str(e)}")
                await asyncio.sleep(3600)
    
    async def get_security_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current security metrics."""
        try:
            async with get_async_session() as session:
                # Get recent violation counts
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                
                violation_result = await session.execute(
                    text("""
                        SELECT severity, COUNT(*) as count
                        FROM audit.security_violations
                        WHERE created_at >= :since
                        GROUP BY severity
                    """),
                    {'since': one_hour_ago}
                )
                
                violations_by_severity = {
                    row.severity: row.count for row in violation_result.fetchall()
                }
                
                # Get data access statistics
                access_result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_accesses,
                            COUNT(CASE WHEN sensitive_data_accessed THEN 1 END) as sensitive_accesses,
                            COUNT(DISTINCT user_id) as unique_users
                        FROM audit.data_access_log
                        WHERE created_at >= :since
                    """),
                    {'since': one_hour_ago}
                )
                
                access_stats = access_result.fetchone()
                
                return {
                    'timestamp': datetime.utcnow().isoformat(),
                    'violations_last_hour': violations_by_severity,
                    'data_access_last_hour': {
                        'total_accesses': access_stats.total_accesses,
                        'sensitive_accesses': access_stats.sensitive_accesses,
                        'unique_users': access_stats.unique_users
                    },
                    'rate_limit_windows': len(self.rate_limit_windows),
                    'monitoring_status': 'running' if self.running else 'stopped',
                    'active_tasks': len(self.monitoring_tasks)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting security metrics summary: {str(e)}")
            return {'error': str(e)}


# Global security metrics service instance
security_metrics_service = SecurityMetricsService()