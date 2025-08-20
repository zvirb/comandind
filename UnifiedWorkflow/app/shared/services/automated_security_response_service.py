"""Automated security response service for real-time threat mitigation and incident response."""

import asyncio
import json
import logging
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_

from shared.database.models.security_models import (
    SecurityViolation, 
    SecurityAction as SecurityActionModel,
    SecurityActionType as SecurityActionTypeModel,
    SecurityActionStatus
)
from shared.services.security_event_processor import SecurityEvent, SecurityEventSeverity, security_event_processor
from shared.services.security_metrics_service import security_metrics_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityActionType(Enum):
    """Types of automated security actions."""
    IP_BLOCK = "ip_block"
    USER_SUSPEND = "user_suspend"
    RATE_LIMIT = "rate_limit"
    ACCOUNT_LOCKOUT = "account_lockout"
    SERVICE_ISOLATION = "service_isolation"
    ALERT_ESCALATION = "alert_escalation"
    THREAT_QUARANTINE = "threat_quarantine"


class SecurityResponseSeverity(Enum):
    """Severity levels for security responses."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityAction:
    """Security action data structure."""
    action_type: SecurityActionType
    severity: SecurityResponseSeverity
    target: str  # IP address, user ID, service name, etc.
    reason: str
    evidence: Dict[str, Any]
    expiration: Optional[datetime] = None
    auto_created: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AutomatedSecurityResponseService:
    """Service for automated security incident response and threat mitigation."""
    
    def __init__(self):
        self.logger = logger
        self.running = False
        self.response_tasks: Set[asyncio.Task] = set()
        
        # Redis connection for real-time coordination
        self.redis_client: Optional[redis.Redis] = None
        
        # Active security actions tracking
        self.active_ip_blocks: Dict[str, SecurityAction] = {}
        self.active_user_suspensions: Dict[int, SecurityAction] = {}
        self.active_rate_limits: Dict[str, Dict[str, Any]] = {}
        
        # Threat detection thresholds
        self.threat_thresholds = {
            'auth_failure_rate': 5,      # failures per minute
            'auth_failure_burst': 10,    # failures in 5 minutes
            'violation_rate': 3,         # violations per minute
            'data_access_spike': 50,     # excessive data access
            'anomaly_score': 0.8,        # anomaly detection threshold
            'rate_limit_violations': 10   # rate limit violations per minute
        }
        
        # Response escalation rules
        self.escalation_rules = {
            SecurityEventSeverity.LOW: SecurityResponseSeverity.LOW,
            SecurityEventSeverity.MEDIUM: SecurityResponseSeverity.MEDIUM,
            SecurityEventSeverity.HIGH: SecurityResponseSeverity.HIGH,
            SecurityEventSeverity.CRITICAL: SecurityResponseSeverity.CRITICAL
        }
        
        # Automatic action rules
        self.auto_action_rules = {
            'brute_force_attack': [SecurityActionType.IP_BLOCK, SecurityActionType.ACCOUNT_LOCKOUT],
            'excessive_violations': [SecurityActionType.RATE_LIMIT, SecurityActionType.ALERT_ESCALATION],
            'anomaly_detection': [SecurityActionType.ALERT_ESCALATION, SecurityActionType.THREAT_QUARANTINE],
            'sandbox_violation': [SecurityActionType.SERVICE_ISOLATION, SecurityActionType.ALERT_ESCALATION],
            'data_exfiltration': [SecurityActionType.USER_SUSPEND, SecurityActionType.ALERT_ESCALATION],
            'privilege_escalation': [SecurityActionType.USER_SUSPEND, SecurityActionType.ALERT_ESCALATION]
        }
    
    async def start_response_service(self) -> None:
        """Start automated security response service."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting automated security response service")
        
        try:
            # Initialize Redis connection
            await self._init_redis_connection()
            
            # Load existing security actions from database
            await self._load_existing_actions()
            
            # Start response monitoring tasks
            tasks = [
                self._monitor_security_events(),
                self._process_threat_patterns(),
                self._enforce_active_blocks(),
                self._cleanup_expired_actions(),
                self._escalate_persistent_threats(),
                self._monitor_system_health()
            ]
            
            for task_coro in tasks:
                task = asyncio.create_task(task_coro)
                self.response_tasks.add(task)
                task.add_done_callback(self.response_tasks.discard)
            
            self.logger.info(f"Started {len(tasks)} security response tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to start security response service: {str(e)}")
            self.running = False
            raise
    
    async def stop_response_service(self) -> None:
        """Stop automated security response service."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping automated security response service")
        
        # Cancel all response tasks
        for task in list(self.response_tasks):
            task.cancel()
        
        # Wait for tasks to complete
        if self.response_tasks:
            await asyncio.gather(*self.response_tasks, return_exceptions=True)
        
        self.response_tasks.clear()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info("Automated security response service stopped")
    
    async def execute_security_action(
        self,
        action: SecurityAction,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """Execute a security action."""
        try:
            self.logger.info(f"Executing security action: {action.action_type.value} for {action.target}")
            
            success = False
            
            if action.action_type == SecurityActionType.IP_BLOCK:
                success = await self._execute_ip_block(action)
            elif action.action_type == SecurityActionType.USER_SUSPEND:
                success = await self._execute_user_suspension(action)
            elif action.action_type == SecurityActionType.RATE_LIMIT:
                success = await self._execute_rate_limit(action)
            elif action.action_type == SecurityActionType.ACCOUNT_LOCKOUT:
                success = await self._execute_account_lockout(action)
            elif action.action_type == SecurityActionType.SERVICE_ISOLATION:
                success = await self._execute_service_isolation(action)
            elif action.action_type == SecurityActionType.ALERT_ESCALATION:
                success = await self._execute_alert_escalation(action)
            elif action.action_type == SecurityActionType.THREAT_QUARANTINE:
                success = await self._execute_threat_quarantine(action)
            
            if success:
                # Log action to audit system
                await self._log_security_action(action, user_id, session_id)
                
                # Update metrics
                security_metrics_service.record_threat_detection(
                    threat_type="automated_response",
                    severity=action.severity.value,
                    source="security_response_service"
                )
                
                # Store action in Redis for coordination
                await self._store_action_in_redis(action)
                
                self.logger.info(f"Successfully executed security action: {action.action_type.value}")
            else:
                self.logger.error(f"Failed to execute security action: {action.action_type.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing security action: {str(e)}")
            return False
    
    async def check_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is currently blocked."""
        try:
            # Check local cache first
            if ip_address in self.active_ip_blocks:
                action = self.active_ip_blocks[ip_address]
                if action.expiration and action.expiration > datetime.utcnow():
                    return True
                else:
                    # Expired, remove from cache
                    del self.active_ip_blocks[ip_address]
            
            # Check Redis for distributed coordination
            if self.redis_client:
                blocked = await self.redis_client.get(f"ip_block:{ip_address}")
                return blocked is not None
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking IP block status: {str(e)}")
            return False
    
    async def check_user_suspended(self, user_id: int) -> bool:
        """Check if a user is currently suspended."""
        try:
            # Check local cache first
            if user_id in self.active_user_suspensions:
                action = self.active_user_suspensions[user_id]
                if action.expiration and action.expiration > datetime.utcnow():
                    return True
                else:
                    # Expired, remove from cache
                    del self.active_user_suspensions[user_id]
            
            # Check Redis for distributed coordination
            if self.redis_client:
                suspended = await self.redis_client.get(f"user_suspend:{user_id}")
                return suspended is not None
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking user suspension status: {str(e)}")
            return False
    
    async def analyze_threat_pattern(self, events: List[SecurityEvent]) -> Optional[Dict[str, Any]]:
        """Analyze a pattern of security events for automated response."""
        try:
            if not events:
                return None
            
            # Group events by type and severity
            event_analysis = {
                'total_events': len(events),
                'time_span': (max(e.timestamp for e in events) - min(e.timestamp for e in events)).total_seconds(),
                'severity_distribution': defaultdict(int),
                'event_types': defaultdict(int),
                'source_ips': defaultdict(int),
                'affected_users': set(),
                'services': set()
            }
            
            for event in events:
                event_analysis['severity_distribution'][event.severity.value] += 1
                event_analysis['event_types'][event.event_type.value] += 1
                
                if event.ip_address:
                    event_analysis['source_ips'][event.ip_address] += 1
                if event.user_id:
                    event_analysis['affected_users'].add(event.user_id)
                if event.service_name:
                    event_analysis['services'].add(event.service_name)
            
            # Analyze patterns
            threat_patterns = []
            
            # Check for brute force attack
            if self._detect_brute_force_pattern(event_analysis):
                threat_patterns.append({
                    'type': 'brute_force_attack',
                    'confidence': 0.9,
                    'target_ips': list(event_analysis['source_ips'].keys()),
                    'recommended_actions': self.auto_action_rules['brute_force_attack']
                })
            
            # Check for privilege escalation
            if self._detect_privilege_escalation_pattern(event_analysis):
                threat_patterns.append({
                    'type': 'privilege_escalation',
                    'confidence': 0.8,
                    'affected_users': list(event_analysis['affected_users']),
                    'recommended_actions': self.auto_action_rules['privilege_escalation']
                })
            
            # Check for data exfiltration
            if self._detect_data_exfiltration_pattern(event_analysis):
                threat_patterns.append({
                    'type': 'data_exfiltration',
                    'confidence': 0.7,
                    'affected_users': list(event_analysis['affected_users']),
                    'recommended_actions': self.auto_action_rules['data_exfiltration']
                })
            
            if threat_patterns:
                return {
                    'analysis': event_analysis,
                    'patterns': threat_patterns,
                    'recommended_severity': self._calculate_response_severity(event_analysis)
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing threat pattern: {str(e)}")
            return None
    
    # Internal methods
    
    async def _init_redis_connection(self) -> None:
        """Initialize Redis connection for coordination."""
        try:
            redis_url = getattr(settings, 'redis_url', 'redis://redis:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            self.logger.info("Redis connection established for security response coordination")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {str(e)}. Coordination disabled.")
            self.redis_client = None
    
    async def _load_existing_actions(self) -> None:
        """Load existing security actions from database."""
        try:
            async for session in get_async_session():
                # Load active IP blocks
                result = await session.execute(
                    text("""
                        SELECT action_details, created_at
                        FROM audit.security_actions
                        WHERE action_type = 'ip_block'
                        AND (expiration IS NULL OR expiration > NOW())
                        AND status = 'active'
                    """)
                )
                
                for row in result.fetchall():
                    details = json.loads(row.action_details)
                    if 'target_ip' in details:
                        action = SecurityAction(
                            action_type=SecurityActionType.IP_BLOCK,
                            severity=SecurityResponseSeverity.HIGH,
                            target=details['target_ip'],
                            reason=details.get('reason', 'Restored from database'),
                            evidence=details,
                            created_at=row.created_at,
                            auto_created=False
                        )
                        self.active_ip_blocks[details['target_ip']] = action
                
                self.logger.info(f"Loaded {len(self.active_ip_blocks)} existing IP blocks")
                
        except Exception as e:
            self.logger.error(f"Error loading existing security actions: {str(e)}")
    
    async def _monitor_security_events(self) -> None:
        """Monitor security events for automated response."""
        while self.running:
            try:
                # This would integrate with the security event processor
                # For now, monitor database for recent violations
                async for session in get_async_session():
                    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
                    
                    # Check for brute force attacks
                    result = await session.execute(
                        text("""
                            SELECT ip_address, COUNT(*) as failure_count
                            FROM audit.security_violations
                            WHERE violation_type LIKE '%AUTH%'
                            AND severity IN ('HIGH', 'CRITICAL')
                            AND created_at >= :since
                            GROUP BY ip_address
                            HAVING COUNT(*) >= :threshold
                        """),
                        {'since': five_minutes_ago, 'threshold': self.threat_thresholds['auth_failure_burst']}
                    )
                    
                    for row in result.fetchall():
                        if row.ip_address and not await self.check_ip_blocked(row.ip_address):
                            action = SecurityAction(
                                action_type=SecurityActionType.IP_BLOCK,
                                severity=SecurityResponseSeverity.HIGH,
                                target=row.ip_address,
                                reason=f"Brute force attack detected: {row.failure_count} failures in 5 minutes",
                                evidence={'failure_count': row.failure_count, 'time_window': '5 minutes'},
                                expiration=datetime.utcnow() + timedelta(hours=1)
                            )
                            
                            await self.execute_security_action(action)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error monitoring security events: {str(e)}")
                await asyncio.sleep(60)
    
    async def _process_threat_patterns(self) -> None:
        """Process detected threat patterns for automated response."""
        while self.running:
            try:
                # This would analyze patterns from the security event processor
                # For demonstration, check for specific patterns in the database
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error processing threat patterns: {str(e)}")
                await asyncio.sleep(300)
    
    async def _enforce_active_blocks(self) -> None:
        """Enforce active security blocks and restrictions."""
        while self.running:
            try:
                # Update rate limiting enforcement
                await self._update_rate_limits()
                
                # Sync with Redis for distributed enforcement
                if self.redis_client:
                    await self._sync_with_redis()
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error enforcing active blocks: {str(e)}")
                await asyncio.sleep(30)
    
    async def _cleanup_expired_actions(self) -> None:
        """Clean up expired security actions."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Clean up expired IP blocks
                expired_ips = [
                    ip for ip, action in self.active_ip_blocks.items()
                    if action.expiration and action.expiration <= current_time
                ]
                
                for ip in expired_ips:
                    del self.active_ip_blocks[ip]
                    if self.redis_client:
                        await self.redis_client.delete(f"ip_block:{ip}")
                    self.logger.info(f"Removed expired IP block for {ip}")
                
                # Clean up expired user suspensions
                expired_users = [
                    user_id for user_id, action in self.active_user_suspensions.items()
                    if action.expiration and action.expiration <= current_time
                ]
                
                for user_id in expired_users:
                    del self.active_user_suspensions[user_id]
                    if self.redis_client:
                        await self.redis_client.delete(f"user_suspend:{user_id}")
                    self.logger.info(f"Removed expired user suspension for user {user_id}")
                
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error cleaning up expired actions: {str(e)}")
                await asyncio.sleep(300)
    
    async def _escalate_persistent_threats(self) -> None:
        """Escalate persistent threats that require manual intervention."""
        while self.running:
            try:
                # Check for threats that have persisted despite automated responses
                async for session in get_async_session():
                    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                    
                    # Find IPs with repeated violations despite blocks
                    result = await session.execute(
                        text("""
                            SELECT ip_address, COUNT(*) as violation_count
                            FROM audit.security_violations
                            WHERE created_at >= :since
                            AND ip_address IN (
                                SELECT DISTINCT target
                                FROM audit.security_actions
                                WHERE action_type = 'ip_block'
                                AND created_at >= :since
                            )
                            GROUP BY ip_address
                            HAVING COUNT(*) >= 5
                        """),
                        {'since': one_hour_ago}
                    )
                    
                    for row in result.fetchall():
                        # Escalate to manual review
                        escalation_action = SecurityAction(
                            action_type=SecurityActionType.ALERT_ESCALATION,
                            severity=SecurityResponseSeverity.CRITICAL,
                            target=row.ip_address,
                            reason=f"Persistent threat: {row.violation_count} violations despite IP block",
                            evidence={'violation_count': row.violation_count, 'escalation_reason': 'persistent_threat'}
                        )
                        
                        await self.execute_security_action(escalation_action)
                
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Error escalating persistent threats: {str(e)}")
                await asyncio.sleep(1800)
    
    async def _monitor_system_health(self) -> None:
        """Monitor security response system health."""
        while self.running:
            try:
                # Check system responsiveness
                health_metrics = {
                    'active_ip_blocks': len(self.active_ip_blocks),
                    'active_user_suspensions': len(self.active_user_suspensions),
                    'redis_connected': self.redis_client is not None,
                    'response_tasks_running': len(self.response_tasks)
                }
                
                # Log health status
                self.logger.debug(f"Security response system health: {health_metrics}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring system health: {str(e)}")
                await asyncio.sleep(300)
    
    # Action execution methods
    
    async def _execute_ip_block(self, action: SecurityAction) -> bool:
        """Execute IP block action."""
        try:
            # Validate IP address
            ip = ipaddress.ip_address(action.target)
            
            # Store in local cache
            self.active_ip_blocks[action.target] = action
            
            # Store in Redis for distributed coordination
            if self.redis_client:
                expiration_seconds = None
                if action.expiration:
                    expiration_seconds = int((action.expiration - datetime.utcnow()).total_seconds())
                
                await self.redis_client.set(
                    f"ip_block:{action.target}",
                    json.dumps(asdict(action), default=str),
                    ex=expiration_seconds
                )
            
            self.logger.info(f"IP block executed for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing IP block: {str(e)}")
            return False
    
    async def _execute_user_suspension(self, action: SecurityAction) -> bool:
        """Execute user suspension action."""
        try:
            user_id = int(action.target)
            
            # Store in local cache
            self.active_user_suspensions[user_id] = action
            
            # Store in Redis for distributed coordination
            if self.redis_client:
                expiration_seconds = None
                if action.expiration:
                    expiration_seconds = int((action.expiration - datetime.utcnow()).total_seconds())
                
                await self.redis_client.set(
                    f"user_suspend:{user_id}",
                    json.dumps(asdict(action), default=str),
                    ex=expiration_seconds
                )
            
            self.logger.info(f"User suspension executed for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing user suspension: {str(e)}")
            return False
    
    async def _execute_rate_limit(self, action: SecurityAction) -> bool:
        """Execute rate limiting action."""
        try:
            # Implement rate limiting logic
            limit_key = action.target
            self.active_rate_limits[limit_key] = {
                'action': action,
                'requests': deque(),
                'limit': action.evidence.get('limit', 10),
                'window': action.evidence.get('window', 60)
            }
            
            self.logger.info(f"Rate limit executed for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing rate limit: {str(e)}")
            return False
    
    async def _execute_account_lockout(self, action: SecurityAction) -> bool:
        """Execute account lockout action."""
        try:
            # This would integrate with user management system
            self.logger.info(f"Account lockout executed for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing account lockout: {str(e)}")
            return False
    
    async def _execute_service_isolation(self, action: SecurityAction) -> bool:
        """Execute service isolation action."""
        try:
            # This would integrate with container orchestration
            self.logger.info(f"Service isolation executed for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing service isolation: {str(e)}")
            return False
    
    async def _execute_alert_escalation(self, action: SecurityAction) -> bool:
        """Execute alert escalation action."""
        try:
            # This would integrate with alerting system
            escalation_data = {
                'action': asdict(action),
                'timestamp': datetime.utcnow().isoformat(),
                'escalation_level': action.severity.value
            }
            
            # Could send to webhook, email, or incident management system
            self.logger.warning(f"SECURITY ESCALATION: {action.reason} for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing alert escalation: {str(e)}")
            return False
    
    async def _execute_threat_quarantine(self, action: SecurityAction) -> bool:
        """Execute threat quarantine action."""
        try:
            # This would isolate the threat while preserving evidence
            self.logger.info(f"Threat quarantine executed for {action.target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing threat quarantine: {str(e)}")
            return False
    
    # Helper methods
    
    def _detect_brute_force_pattern(self, analysis: Dict[str, Any]) -> bool:
        """Detect brute force attack pattern."""
        auth_failures = analysis['event_types'].get('authentication', 0)
        time_span = analysis['time_span']
        
        if time_span > 0:
            failure_rate = auth_failures / (time_span / 60)  # failures per minute
            return failure_rate >= self.threat_thresholds['auth_failure_rate']
        
        return False
    
    def _detect_privilege_escalation_pattern(self, analysis: Dict[str, Any]) -> bool:
        """Detect privilege escalation pattern."""
        authz_violations = analysis['event_types'].get('authorization', 0)
        critical_events = analysis['severity_distribution'].get('critical', 0)
        
        return authz_violations >= 3 and critical_events >= 1
    
    def _detect_data_exfiltration_pattern(self, analysis: Dict[str, Any]) -> bool:
        """Detect data exfiltration pattern."""
        data_access = analysis['event_types'].get('data_access', 0)
        time_span = analysis['time_span']
        
        if time_span > 0:
            access_rate = data_access / (time_span / 60)  # accesses per minute
            return access_rate >= self.threat_thresholds['data_access_spike']
        
        return False
    
    def _calculate_response_severity(self, analysis: Dict[str, Any]) -> SecurityResponseSeverity:
        """Calculate appropriate response severity."""
        critical_count = analysis['severity_distribution'].get('critical', 0)
        high_count = analysis['severity_distribution'].get('high', 0)
        
        if critical_count >= 3:
            return SecurityResponseSeverity.CRITICAL
        elif critical_count >= 1 or high_count >= 5:
            return SecurityResponseSeverity.HIGH
        elif high_count >= 1:
            return SecurityResponseSeverity.MEDIUM
        else:
            return SecurityResponseSeverity.LOW
    
    async def _log_security_action(
        self,
        action: SecurityAction,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log security action to audit system."""
        try:
            async for session in get_async_session():
                await security_audit_service.log_security_action(
                    session=session,
                    action_type=action.action_type.value,
                    target=action.target,
                    reason=action.reason,
                    evidence=action.evidence,
                    severity=action.severity.value,
                    user_id=user_id,
                    session_id=session_id,
                    auto_created=action.auto_created
                )
        except Exception as e:
            self.logger.error(f"Failed to log security action: {str(e)}")
    
    async def _store_action_in_redis(self, action: SecurityAction) -> None:
        """Store security action in Redis for coordination."""
        try:
            if self.redis_client:
                key = f"security_action:{action.action_type.value}:{action.target}"
                await self.redis_client.set(
                    key,
                    json.dumps(asdict(action), default=str),
                    ex=86400  # 24 hours
                )
        except Exception as e:
            self.logger.error(f"Failed to store action in Redis: {str(e)}")
    
    async def _update_rate_limits(self) -> None:
        """Update rate limiting enforcement."""
        try:
            current_time = datetime.utcnow().timestamp()
            
            for limit_key, limit_data in self.active_rate_limits.items():
                # Clean old requests outside the window
                window = limit_data['window']
                requests = limit_data['requests']
                
                while requests and requests[0] < current_time - window:
                    requests.popleft()
        except Exception as e:
            self.logger.error(f"Error updating rate limits: {str(e)}")
    
    async def _sync_with_redis(self) -> None:
        """Sync security actions with Redis for distributed coordination."""
        try:
            if not self.redis_client:
                return
            
            # Sync IP blocks
            keys = await self.redis_client.keys("ip_block:*")
            for key in keys:
                ip = key.split(":", 1)[1]
                if ip not in self.active_ip_blocks:
                    action_data = await self.redis_client.get(key)
                    if action_data:
                        action_dict = json.loads(action_data)
                        action = SecurityAction(**action_dict)
                        self.active_ip_blocks[ip] = action
            
        except Exception as e:
            self.logger.error(f"Error syncing with Redis: {str(e)}")


# Global automated security response service instance
automated_security_response_service = AutomatedSecurityResponseService()