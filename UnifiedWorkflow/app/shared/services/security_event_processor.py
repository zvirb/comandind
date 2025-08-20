"""Real-time security event processing service for comprehensive security monitoring."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.security_metrics_service import security_metrics_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityEventType(Enum):
    """Security event types for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    TOOL_EXECUTION = "tool_execution"
    WEBSOCKET_CONNECTION = "websocket_connection"
    CROSS_SERVICE_AUTH = "cross_service_auth"
    SECURITY_VIOLATION = "security_violation"
    NETWORK_REQUEST = "network_request"
    RATE_LIMIT = "rate_limit"
    THREAT_DETECTION = "threat_detection"
    SYSTEM_HEALTH = "system_health"
    AUDIT_LOG = "audit_log"


class SecurityEventSeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    timestamp: datetime
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    service_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityEvent':
        """Create event from dictionary."""
        data['event_type'] = SecurityEventType(data['event_type'])
        data['severity'] = SecurityEventSeverity(data['severity'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class SecurityEventProcessor:
    """Real-time security event processing service."""
    
    def __init__(self):
        self.logger = logger
        self.running = False
        self.processing_tasks: Set[asyncio.Task] = set()
        
        # Event handlers by type
        self.event_handlers: Dict[SecurityEventType, List[Callable]] = defaultdict(list)
        
        # Event queues and processing
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.high_priority_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Redis connection for event streaming
        self.redis_client: Optional[redis.Redis] = None
        
        # Event correlation and pattern detection
        self.event_correlation: Dict[str, List[SecurityEvent]] = defaultdict(list)
        self.pattern_detectors: List[Callable] = []
        
        # Rate limiting and throttling
        self.event_rates: Dict[str, deque] = defaultdict(lambda: deque())
        self.max_events_per_minute = 1000
        
        # Initialize event handlers
        self._register_default_handlers()
    
    async def start_processing(self) -> None:
        """Start real-time security event processing."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting security event processing service")
        
        try:
            # Initialize Redis connection
            await self._init_redis_connection()
            
            # Start processing tasks
            tasks = [
                self._process_high_priority_events(),
                self._process_regular_events(),
                self._monitor_event_patterns(),
                self._cleanup_correlation_data(),
                self._stream_events_to_redis(),
                self._monitor_event_rates()
            ]
            
            for task_coro in tasks:
                task = asyncio.create_task(task_coro)
                self.processing_tasks.add(task)
                task.add_done_callback(self.processing_tasks.discard)
            
            self.logger.info(f"Started {len(tasks)} security event processing tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to start security event processing: {str(e)}")
            self.running = False
            raise
    
    async def stop_processing(self) -> None:
        """Stop security event processing."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping security event processing service")
        
        # Cancel all processing tasks
        for task in list(self.processing_tasks):
            task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        self.processing_tasks.clear()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info("Security event processing stopped")
    
    async def emit_event(self, event: SecurityEvent) -> None:
        """Emit a security event for processing."""
        try:
            # Check rate limiting
            if not self._check_rate_limit(event):
                self.logger.warning(f"Rate limit exceeded for event type {event.event_type.value}")
                return
            
            # Route to appropriate queue based on severity
            if event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                if self.high_priority_queue.full():
                    self.logger.warning("High priority event queue is full, dropping event")
                    return
                await self.high_priority_queue.put(event)
            else:
                if self.event_queue.full():
                    self.logger.warning("Regular event queue is full, dropping event")
                    return
                await self.event_queue.put(event)
            
            # Update metrics
            security_metrics_service.record_threat_detection(
                threat_type="event_processing",
                severity=event.severity.value,
                source="event_processor"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to emit security event: {str(e)}")
    
    def register_event_handler(
        self, 
        event_type: SecurityEventType, 
        handler: Callable[[SecurityEvent], None]
    ) -> None:
        """Register an event handler for a specific event type."""
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for {event_type.value} events")
    
    def register_pattern_detector(self, detector: Callable[[List[SecurityEvent]], Optional[Dict[str, Any]]]) -> None:
        """Register a pattern detector function."""
        self.pattern_detectors.append(detector)
        self.logger.debug("Registered pattern detector")
    
    # Event Creation Helpers
    
    async def emit_authentication_event(
        self,
        user_id: Optional[int],
        success: bool,
        service_name: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit authentication event."""
        severity = SecurityEventSeverity.LOW if success else SecurityEventSeverity.MEDIUM
        
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            service_name=service_name,
            ip_address=ip_address,
            details={
                'success': success,
                'failure_reason': failure_reason,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    async def emit_authorization_event(
        self,
        user_id: int,
        resource: str,
        action: str,
        granted: bool,
        service_name: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit authorization event."""
        severity = SecurityEventSeverity.LOW if granted else SecurityEventSeverity.HIGH
        
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            service_name=service_name,
            details={
                'resource': resource,
                'action': action,
                'granted': granted,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    async def emit_data_access_event(
        self,
        user_id: int,
        table_name: str,
        access_type: str,
        row_count: int,
        sensitive: bool,
        service_name: str,
        session_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit data access event."""
        severity = SecurityEventSeverity.MEDIUM if sensitive else SecurityEventSeverity.LOW
        
        event = SecurityEvent(
            event_type=SecurityEventType.DATA_ACCESS,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            service_name=service_name,
            details={
                'table_name': table_name,
                'access_type': access_type,
                'row_count': row_count,
                'sensitive': sensitive,
                'response_time_ms': response_time_ms,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    async def emit_security_violation_event(
        self,
        violation_type: str,
        severity: SecurityEventSeverity,
        service_name: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        blocked: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit security violation event."""
        event = SecurityEvent(
            event_type=SecurityEventType.SECURITY_VIOLATION,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            service_name=service_name,
            ip_address=ip_address,
            details={
                'violation_type': violation_type,
                'blocked': blocked,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    async def emit_tool_execution_event(
        self,
        tool_name: str,
        user_id: int,
        success: bool,
        security_level: str,
        service_name: str,
        session_id: Optional[str] = None,
        sandbox_violation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit tool execution security event."""
        severity = SecurityEventSeverity.HIGH if sandbox_violation else SecurityEventSeverity.LOW
        
        event = SecurityEvent(
            event_type=SecurityEventType.TOOL_EXECUTION,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            service_name=service_name,
            details={
                'tool_name': tool_name,
                'success': success,
                'security_level': security_level,
                'sandbox_violation': sandbox_violation,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    async def emit_websocket_event(
        self,
        connection_id: str,
        event_type: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        auth_failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit WebSocket security event."""
        severity = SecurityEventSeverity.MEDIUM if auth_failure_reason else SecurityEventSeverity.LOW
        
        event = SecurityEvent(
            event_type=SecurityEventType.WEBSOCKET_CONNECTION,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            details={
                'connection_id': connection_id,
                'event_type': event_type,
                'auth_failure_reason': auth_failure_reason,
                **(details or {})
            }
        )
        
        await self.emit_event(event)
    
    # Internal Processing Methods
    
    async def _init_redis_connection(self) -> None:
        """Initialize Redis connection for event streaming."""
        try:
            redis_url = getattr(settings, 'redis_url', 'redis://redis:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            self.logger.info("Redis connection established for security event streaming")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {str(e)}. Event streaming disabled.")
            self.redis_client = None
    
    def _check_rate_limit(self, event: SecurityEvent) -> bool:
        """Check if event rate limit is exceeded."""
        current_time = datetime.utcnow().timestamp()
        rate_key = f"{event.event_type.value}:{event.service_name or 'unknown'}"
        
        # Clean old entries
        rate_window = self.event_rates[rate_key]
        while rate_window and rate_window[0] < current_time - 60:  # 1 minute window
            rate_window.popleft()
        
        # Check rate limit
        if len(rate_window) >= self.max_events_per_minute:
            return False
        
        # Add current event
        rate_window.append(current_time)
        return True
    
    def _register_default_handlers(self) -> None:
        """Register default event handlers."""
        # Authentication event handler
        async def handle_authentication_event(event: SecurityEvent):
            details = event.details or {}
            security_metrics_service.record_authentication_attempt(
                service=event.service_name or "unknown",
                status="success" if details.get('success', False) else "failed",
                user_type="admin" if event.user_id == 1 else "regular",
                failure_reason=details.get('failure_reason'),
                ip_address=event.ip_address
            )
        
        self.register_event_handler(SecurityEventType.AUTHENTICATION, handle_authentication_event)
        
        # Authorization event handler
        async def handle_authorization_event(event: SecurityEvent):
            details = event.details or {}
            if not details.get('granted', True):
                security_metrics_service.record_authorization_violation(
                    service=event.service_name or "unknown",
                    violation_type=f"access_denied_{details.get('action', 'unknown')}",
                    severity=event.severity.value
                )
        
        self.register_event_handler(SecurityEventType.AUTHORIZATION, handle_authorization_event)
        
        # Data access event handler
        async def handle_data_access_event(event: SecurityEvent):
            details = event.details or {}
            security_metrics_service.record_data_access(
                service=event.service_name or "unknown",
                access_type=details.get('access_type', 'unknown'),
                table_name=details.get('table_name', 'unknown'),
                row_count=details.get('row_count', 1),
                sensitive=details.get('sensitive', False),
                response_time_seconds=details.get('response_time_ms', 0) / 1000.0
            )
        
        self.register_event_handler(SecurityEventType.DATA_ACCESS, handle_data_access_event)
        
        # Security violation event handler
        async def handle_security_violation_event(event: SecurityEvent):
            details = event.details or {}
            security_metrics_service.record_security_violation(
                violation_type=details.get('violation_type', 'unknown'),
                severity=event.severity.value,
                service=event.service_name or "unknown",
                blocked=details.get('blocked', True)
            )
        
        self.register_event_handler(SecurityEventType.SECURITY_VIOLATION, handle_security_violation_event)
        
        # Tool execution event handler
        async def handle_tool_execution_event(event: SecurityEvent):
            details = event.details or {}
            security_metrics_service.record_tool_execution_security(
                tool_name=details.get('tool_name', 'unknown'),
                security_level=details.get('security_level', 'unknown'),
                status="success" if details.get('success', False) else "failed"
            )
            
            if details.get('sandbox_violation'):
                security_metrics_service.record_sandbox_violation(
                    tool_name=details.get('tool_name', 'unknown'),
                    violation_type=details.get('sandbox_violation', 'unknown')
                )
        
        self.register_event_handler(SecurityEventType.TOOL_EXECUTION, handle_tool_execution_event)
        
        # WebSocket event handler
        async def handle_websocket_event(event: SecurityEvent):
            details = event.details or {}
            security_metrics_service.record_websocket_connection(
                status=details.get('event_type', 'unknown'),
                auth_method="jwt"
            )
            
            if details.get('auth_failure_reason'):
                security_metrics_service.record_websocket_auth_failure(
                    failure_reason=details.get('auth_failure_reason', 'unknown')
                )
        
        self.register_event_handler(SecurityEventType.WEBSOCKET_CONNECTION, handle_websocket_event)
    
    async def _process_high_priority_events(self) -> None:
        """Process high priority security events."""
        while self.running:
            try:
                # Wait for high priority events with timeout
                event = await asyncio.wait_for(
                    self.high_priority_queue.get(), 
                    timeout=1.0
                )
                
                await self._handle_event(event)
                
                # Mark task as done
                self.high_priority_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing high priority event: {str(e)}")
    
    async def _process_regular_events(self) -> None:
        """Process regular priority security events."""
        while self.running:
            try:
                # Wait for regular events with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(), 
                    timeout=1.0
                )
                
                await self._handle_event(event)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing regular event: {str(e)}")
    
    async def _handle_event(self, event: SecurityEvent) -> None:
        """Handle a security event."""
        try:
            # Add to correlation data
            if event.correlation_id:
                self.event_correlation[event.correlation_id].append(event)
            
            # Execute registered handlers
            handlers = self.event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self.logger.error(f"Event handler failed: {str(e)}")
            
            # Log to audit system for critical events
            if event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                await self._log_critical_event(event)
            
        except Exception as e:
            self.logger.error(f"Failed to handle security event: {str(e)}")
    
    async def _log_critical_event(self, event: SecurityEvent) -> None:
        """Log critical security events to audit system."""
        try:
            async with get_async_session() as session:
                await security_audit_service.log_security_violation(
                    session=session,
                    violation_type=f"{event.event_type.value}_critical",
                    severity=event.severity.value.upper(),
                    violation_details=event.details or {},
                    user_id=event.user_id,
                    session_id=event.session_id,
                    ip_address=event.ip_address,
                    blocked=True
                )
        except Exception as e:
            self.logger.error(f"Failed to log critical event to audit system: {str(e)}")
    
    async def _monitor_event_patterns(self) -> None:
        """Monitor for security event patterns."""
        while self.running:
            try:
                # Run pattern detectors on correlation data
                for correlation_id, events in list(self.event_correlation.items()):
                    if len(events) >= 2:  # Need at least 2 events for pattern
                        for detector in self.pattern_detectors:
                            try:
                                pattern_result = detector(events)
                                if pattern_result:
                                    await self._handle_pattern_detection(correlation_id, pattern_result)
                            except Exception as e:
                                self.logger.error(f"Pattern detector failed: {str(e)}")
                
                await asyncio.sleep(30)  # Check patterns every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring event patterns: {str(e)}")
                await asyncio.sleep(30)
    
    async def _handle_pattern_detection(self, correlation_id: str, pattern: Dict[str, Any]) -> None:
        """Handle detected security pattern."""
        try:
            self.logger.warning(f"Security pattern detected: {pattern}")
            
            # Create pattern detection event
            pattern_event = SecurityEvent(
                event_type=SecurityEventType.THREAT_DETECTION,
                severity=SecurityEventSeverity.HIGH,
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id,
                details={
                    'pattern_type': pattern.get('type', 'unknown'),
                    'confidence': pattern.get('confidence', 0.0),
                    'description': pattern.get('description', ''),
                    'events_analyzed': len(self.event_correlation[correlation_id])
                }
            )
            
            await self.emit_event(pattern_event)
            
        except Exception as e:
            self.logger.error(f"Failed to handle pattern detection: {str(e)}")
    
    async def _cleanup_correlation_data(self) -> None:
        """Clean up old correlation data."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=1)  # Keep 1 hour of data
                
                expired_correlations = []
                for correlation_id, events in self.event_correlation.items():
                    # Remove old events
                    recent_events = [e for e in events if e.timestamp > cutoff_time]
                    
                    if recent_events:
                        self.event_correlation[correlation_id] = recent_events
                    else:
                        expired_correlations.append(correlation_id)
                
                # Remove expired correlations
                for correlation_id in expired_correlations:
                    del self.event_correlation[correlation_id]
                
                await asyncio.sleep(600)  # Clean up every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error cleaning up correlation data: {str(e)}")
                await asyncio.sleep(600)
    
    async def _stream_events_to_redis(self) -> None:
        """Stream security events to Redis for real-time monitoring."""
        if not self.redis_client:
            return
        
        while self.running:
            try:
                # This would stream processed events to Redis for external consumption
                # For now, just maintain the connection
                await self.redis_client.ping()
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error streaming events to Redis: {str(e)}")
                await asyncio.sleep(60)
    
    async def _monitor_event_rates(self) -> None:
        """Monitor event processing rates."""
        while self.running:
            try:
                # Log current queue sizes
                regular_queue_size = self.event_queue.qsize()
                high_priority_queue_size = self.high_priority_queue.qsize()
                
                if regular_queue_size > 5000:
                    self.logger.warning(f"Regular event queue is large: {regular_queue_size}")
                
                if high_priority_queue_size > 500:
                    self.logger.warning(f"High priority event queue is large: {high_priority_queue_size}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring event rates: {str(e)}")
                await asyncio.sleep(60)


# Global security event processor instance
security_event_processor = SecurityEventProcessor()