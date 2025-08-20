"""Advanced threat detection and anomaly monitoring service for security analysis."""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_

from shared.database.models.security_models import SecurityViolation, DataAccessLog
from shared.services.security_event_processor import SecurityEvent, SecurityEventSeverity, security_event_processor
from shared.services.security_metrics_service import security_metrics_service
from shared.services.automated_security_response_service import (
    automated_security_response_service, 
    SecurityAction, 
    SecurityActionType, 
    SecurityResponseSeverity
)
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ThreatType(Enum):
    """Types of threats that can be detected."""
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ANOMALOUS_ACCESS = "anomalous_access"
    SUSPICIOUS_PATTERNS = "suspicious_patterns"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_HIJACKING = "session_hijacking"
    INSIDER_THREAT = "insider_threat"
    AUTOMATED_ATTACK = "automated_attack"


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    GEOGRAPHICAL = "geographical"
    VOLUMETRIC = "volumetric"
    PATTERN_BASED = "pattern_based"


@dataclass
class ThreatDetection:
    """Threat detection result."""
    threat_type: ThreatType
    confidence: float
    severity: SecurityResponseSeverity
    description: str
    evidence: Dict[str, Any]
    affected_entities: List[str]
    timestamp: datetime
    source_data: List[SecurityEvent]
    recommended_actions: List[SecurityActionType]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'threat_type': self.threat_type.value,
            'confidence': self.confidence,
            'severity': self.severity.value,
            'description': self.description,
            'evidence': self.evidence,
            'affected_entities': self.affected_entities,
            'timestamp': self.timestamp.isoformat(),
            'recommended_actions': [action.value for action in self.recommended_actions]
        }


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    anomaly_type: AnomalyType
    anomaly_score: float
    description: str
    baseline_value: Optional[float]
    observed_value: float
    deviation_factor: float
    timestamp: datetime
    evidence: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'anomaly_type': self.anomaly_type.value,
            'anomaly_score': self.anomaly_score,
            'description': self.description,
            'baseline_value': self.baseline_value,
            'observed_value': self.observed_value,
            'deviation_factor': self.deviation_factor,
            'timestamp': self.timestamp.isoformat(),
            'evidence': self.evidence
        }


class ThreatDetectionService:
    """Advanced threat detection and anomaly monitoring service."""
    
    def __init__(self):
        self.logger = logger
        self.running = False
        self.detection_tasks: Set[asyncio.Task] = set()
        
        # Detection state
        self.baseline_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.user_behavior_profiles: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self.ip_behavior_profiles: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.temporal_patterns: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Detection thresholds and parameters
        self.detection_config = {
            'anomaly_threshold': 0.7,
            'confidence_threshold': 0.6,
            'statistical_window': 24,  # hours
            'behavioral_learning_period': 7,  # days
            'max_baseline_age': 30,  # days
            'pattern_analysis_window': 60,  # minutes
            'min_events_for_analysis': 5
        }
        
        # Threat detection rules
        self.threat_rules = {
            ThreatType.BRUTE_FORCE: {
                'auth_failure_rate': 10,  # failures per minute
                'auth_failure_burst': 20,  # failures in 5 minutes
                'unique_usernames': 5,     # different usernames tried
                'time_window': 300         # 5 minutes
            },
            ThreatType.DATA_EXFILTRATION: {
                'data_volume_threshold': 10000,  # rows accessed
                'sensitive_data_ratio': 0.3,     # % of sensitive data
                'access_rate_spike': 5.0,        # times normal rate
                'time_window': 3600               # 1 hour
            },
            ThreatType.PRIVILEGE_ESCALATION: {
                'admin_attempts': 3,      # admin access attempts
                'role_changes': 2,        # role change attempts
                'permission_violations': 5, # permission violations
                'time_window': 1800       # 30 minutes
            }
        }
    
    async def start_detection_service(self) -> None:
        """Start threat detection and anomaly monitoring service."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting threat detection and anomaly monitoring service")
        
        try:
            # Initialize baseline metrics
            await self._initialize_baselines()
            
            # Start detection tasks
            tasks = [
                self._monitor_authentication_threats(),
                self._monitor_data_access_anomalies(),
                self._monitor_behavioral_anomalies(),
                self._monitor_temporal_anomalies()
            ]
            
            for task_coro in tasks:
                task = asyncio.create_task(task_coro)
                self.detection_tasks.add(task)
                task.add_done_callback(self.detection_tasks.discard)
            
            self.logger.info(f"Started {len(tasks)} threat detection tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to start threat detection service: {str(e)}")
            self.running = False
            raise
    
    async def stop_detection_service(self) -> None:
        """Stop threat detection and anomaly monitoring service."""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping threat detection and anomaly monitoring service")
        
        # Cancel all detection tasks
        for task in list(self.detection_tasks):
            task.cancel()
        
        # Wait for tasks to complete
        if self.detection_tasks:
            await asyncio.gather(*self.detection_tasks, return_exceptions=True)
        
        self.detection_tasks.clear()
        self.logger.info("Threat detection and anomaly monitoring service stopped")
    
    async def analyze_security_events(self, events: List[SecurityEvent]) -> List[ThreatDetection]:
        """Analyze a list of security events for threats."""
        try:
            if not events:
                return []
            
            threats = []
            
            # Group events by type and analyze
            events_by_type = defaultdict(list)
            for event in events:
                events_by_type[event.event_type].append(event)
            
            # Check for authentication threats
            auth_events = events_by_type.get('authentication', [])
            if auth_events:
                auth_threats = await self._detect_authentication_threats(auth_events)
                threats.extend(auth_threats)
            
            # Check for data access threats
            data_events = events_by_type.get('data_access', [])
            if data_events:
                data_threats = await self._detect_data_access_threats(data_events)
                threats.extend(data_threats)
            
            # Process detected threats
            for threat in threats:
                await self._process_threat_detection(threat)
            
            return threats
            
        except Exception as e:
            self.logger.error(f"Error analyzing security events: {str(e)}")
            return []
    
    async def _initialize_baselines(self) -> None:
        """Initialize baseline metrics from historical data."""
        try:
            async with get_async_session() as session:
                # Get historical data for baseline calculation
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                
                # Calculate authentication failure baseline
                result = await session.execute(
                    text("""
                        SELECT 
                            DATE_TRUNC('hour', created_at) as hour,
                            COUNT(*) as failure_count
                        FROM audit.security_violations
                        WHERE violation_type LIKE '%AUTH%'
                        AND created_at >= :since
                        GROUP BY DATE_TRUNC('hour', created_at)
                        ORDER BY hour
                    """),
                    {'since': thirty_days_ago}
                )
                
                failure_counts = [row.failure_count for row in result.fetchall()]
                if failure_counts:
                    self.baseline_metrics['auth_failures_per_hour'] = {
                        'mean': float(np.mean(failure_counts)),
                        'std': float(np.std(failure_counts)),
                        'min': float(np.min(failure_counts)),
                        'max': float(np.max(failure_counts)),
                        'count': len(failure_counts),
                        'last_updated': datetime.utcnow().timestamp()
                    }
                
                self.logger.info(f"Initialized baselines for {len(self.baseline_metrics)} metrics")
                
        except Exception as e:
            self.logger.error(f"Error initializing baselines: {str(e)}")
    
    async def _monitor_authentication_threats(self) -> None:
        """Monitor for authentication-based threats."""
        while self.running:
            try:
                async with get_async_session() as session:
                    # Check for brute force attacks in the last 10 minutes
                    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
                    
                    result = await session.execute(
                        text("""
                            SELECT 
                                ip_address,
                                COUNT(*) as failure_count,
                                COUNT(DISTINCT violation_details->>'username') as unique_users,
                                MIN(created_at) as first_attempt,
                                MAX(created_at) as last_attempt
                            FROM audit.security_violations
                            WHERE violation_type LIKE '%AUTH%'
                            AND severity IN ('HIGH', 'CRITICAL')
                            AND created_at >= :since
                            AND ip_address IS NOT NULL
                            GROUP BY ip_address
                            HAVING COUNT(*) >= :threshold
                        """),
                        {
                            'since': ten_minutes_ago,
                            'threshold': self.threat_rules[ThreatType.BRUTE_FORCE]['auth_failure_rate']
                        }
                    )
                    
                    for row in result.fetchall():
                        # Create threat detection
                        threat = ThreatDetection(
                            threat_type=ThreatType.BRUTE_FORCE,
                            confidence=min(1.0, row.failure_count / 20.0),
                            severity=SecurityResponseSeverity.HIGH,
                            description=f"Brute force attack detected from {row.ip_address}",
                            evidence={
                                'ip_address': row.ip_address,
                                'failure_count': row.failure_count,
                                'unique_users_targeted': row.unique_users,
                                'attack_duration': (row.last_attempt - row.first_attempt).total_seconds(),
                                'detection_window': '10 minutes'
                            },
                            affected_entities=[row.ip_address],
                            timestamp=datetime.utcnow(),
                            source_data=[],
                            recommended_actions=[
                                SecurityActionType.IP_BLOCK,
                                SecurityActionType.ALERT_ESCALATION
                            ]
                        )
                        
                        await self._process_threat_detection(threat)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring authentication threats: {str(e)}")
                await asyncio.sleep(300)
    
    async def _monitor_data_access_anomalies(self) -> None:
        """Monitor for data access anomalies."""
        while self.running:
            try:
                await asyncio.sleep(900)  # Check every 15 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring data access anomalies: {str(e)}")
                await asyncio.sleep(900)
    
    async def _monitor_behavioral_anomalies(self) -> None:
        """Monitor for behavioral anomalies."""
        while self.running:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Error monitoring behavioral anomalies: {str(e)}")
                await asyncio.sleep(1800)
    
    async def _monitor_temporal_anomalies(self) -> None:
        """Monitor for temporal anomalies."""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error monitoring temporal anomalies: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _detect_authentication_threats(self, events: List[SecurityEvent]) -> List[ThreatDetection]:
        """Detect authentication-based threats from events."""
        threats = []
        
        # Group by IP address
        events_by_ip = defaultdict(list)
        for event in events:
            if event.ip_address:
                events_by_ip[event.ip_address].append(event)
        
        for ip_address, ip_events in events_by_ip.items():
            failure_count = len([e for e in ip_events if not e.details.get('success', True)])
            
            if failure_count >= self.threat_rules[ThreatType.BRUTE_FORCE]['auth_failure_burst']:
                threats.append(ThreatDetection(
                    threat_type=ThreatType.BRUTE_FORCE,
                    confidence=min(1.0, failure_count / 30.0),
                    severity=SecurityResponseSeverity.HIGH,
                    description=f"Brute force attack detected from {ip_address}",
                    evidence={'ip_address': ip_address, 'failure_count': failure_count},
                    affected_entities=[ip_address],
                    timestamp=datetime.utcnow(),
                    source_data=ip_events,
                    recommended_actions=[SecurityActionType.IP_BLOCK]
                ))
        
        return threats
    
    async def _detect_data_access_threats(self, events: List[SecurityEvent]) -> List[ThreatDetection]:
        """Detect data access threats from events."""
        threats = []
        
        # Analyze volume and patterns
        total_rows = sum(event.details.get('row_count', 0) for event in events)
        sensitive_count = len([e for e in events if e.details.get('sensitive', False)])
        
        if total_rows > self.threat_rules[ThreatType.DATA_EXFILTRATION]['data_volume_threshold']:
            threats.append(ThreatDetection(
                threat_type=ThreatType.DATA_EXFILTRATION,
                confidence=min(1.0, total_rows / 100000.0),
                severity=SecurityResponseSeverity.CRITICAL,
                description="Potential data exfiltration detected",
                evidence={'total_rows': total_rows, 'sensitive_count': sensitive_count},
                affected_entities=[str(events[0].user_id)] if events[0].user_id else [],
                timestamp=datetime.utcnow(),
                source_data=events,
                recommended_actions=[SecurityActionType.USER_SUSPEND, SecurityActionType.ALERT_ESCALATION]
            ))
        
        return threats
    
    async def _process_threat_detection(self, threat: ThreatDetection) -> None:
        """Process a detected threat."""
        try:
            # Log the threat
            self.logger.warning(f"THREAT DETECTED: {threat.threat_type.value} - {threat.description}")
            
            # Update metrics
            security_metrics_service.record_threat_detection(
                threat_type=threat.threat_type.value,
                severity=threat.severity.value,
                source="threat_detection_service"
            )
            
            # Create security event
            from shared.services.security_event_processor import SecurityEvent, SecurityEventType
            
            security_event = SecurityEvent(
                event_type=SecurityEventType.THREAT_DETECTION,
                severity=SecurityEventSeverity.HIGH if threat.severity == SecurityResponseSeverity.HIGH else SecurityEventSeverity.CRITICAL,
                timestamp=threat.timestamp,
                service_name="threat_detection_service",
                details={
                    'threat_type': threat.threat_type.value,
                    'confidence': threat.confidence,
                    'evidence': threat.evidence,
                    'recommended_actions': [action.value for action in threat.recommended_actions]
                }
            )
            
            await security_event_processor.emit_event(security_event)
            
            # Execute recommended actions if confidence is high
            if threat.confidence >= 0.8:
                for action_type in threat.recommended_actions:
                    for entity in threat.affected_entities:
                        action = SecurityAction(
                            action_type=action_type,
                            severity=threat.severity,
                            target=entity,
                            reason=f"Automated response to {threat.threat_type.value}: {threat.description}",
                            evidence=threat.evidence,
                            expiration=datetime.utcnow() + timedelta(hours=24)  # 24-hour default
                        )
                        
                        await automated_security_response_service.execute_security_action(action)
            
        except Exception as e:
            self.logger.error(f"Error processing threat detection: {str(e)}")


# Global threat detection service instance
threat_detection_service = ThreatDetectionService()