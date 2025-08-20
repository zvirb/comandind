"""
Authentication Pattern Detection Service

A meta-learning system for security validation that enhances existing authentication infrastructure
by detecting patterns, assessing risks, and adapting validation strategies.

This service implements:
1. Pattern Detection Engine for authentication events
2. Risk Assessment Module with dynamic scoring
3. Adaptive Validation checkpoint system
4. Evidence Scoring mechanism
5. Non-invasive integration with existing auth middleware
"""

import json
import time
import hashlib
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_, func, desc

from shared.database.models.security_models import SecurityViolation, SecurityAction
from shared.services.security_audit_service import security_audit_service
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

class AuthEventType(Enum):
    """Authentication event types for pattern analysis"""
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_VALIDATION = "token_validation"
    LOGOUT = "logout"
    PASSWORD_RESET = "password_reset"
    MFA_CHALLENGE = "mfa_challenge"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

class RiskLevel(Enum):
    """Risk assessment levels"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuthEvent:
    """Authentication event for pattern analysis"""
    event_id: str
    event_type: AuthEventType
    user_id: Optional[int]
    session_id: Optional[str]
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    additional_data: Dict[str, Any]
    risk_indicators: List[str]
    pattern_matches: List[str]

@dataclass
class AuthPattern:
    """Detected authentication pattern"""
    pattern_id: str
    pattern_type: str  # "frequency", "geographic", "temporal", "behavioral", "threat"
    pattern_name: str
    description: str
    detection_algorithm: str
    confidence_score: float
    risk_level: RiskLevel
    indicators: List[str]
    evidence_count: int
    first_detected: datetime
    last_updated: datetime
    mitigation_actions: List[str]

@dataclass
class RiskAssessment:
    """Risk assessment for authentication attempt"""
    assessment_id: str
    user_id: Optional[int]
    session_id: Optional[str]
    overall_risk_score: float
    risk_level: RiskLevel
    contributing_factors: Dict[str, float]
    pattern_matches: List[str]
    recommended_actions: List[str]
    confidence: float
    assessment_time: datetime
    expires_at: datetime

@dataclass
class ValidationCheckpoint:
    """Adaptive validation checkpoint"""
    checkpoint_id: str
    checkpoint_type: str  # "additional_auth", "captcha", "delay", "monitoring", "block"
    trigger_conditions: Dict[str, Any]
    validation_strength: float
    bypass_conditions: Dict[str, Any]
    success_rate: float
    false_positive_rate: float
    created_at: datetime
    effectiveness_score: float

class AuthPatternDetectionService:
    """
    Authentication Pattern Detection and Learning Service
    
    Provides meta-learning capabilities for security validation including:
    - Real-time pattern detection in authentication events
    - Dynamic risk assessment with adaptive thresholds
    - Evidence-based validation checkpoint system
    - Continuous learning from security events
    """
    
    def __init__(self):
        self.logger = logger
        self._cache = None
        
        # Pattern storage
        self.detected_patterns: Dict[str, AuthPattern] = {}
        self.active_checkpoints: Dict[str, ValidationCheckpoint] = {}
        self.user_risk_profiles: Dict[int, Dict[str, Any]] = {}
        
        # Learning parameters
        self.pattern_confidence_threshold = 0.7
        self.risk_decay_factor = 0.95  # Risk score decay over time
        self.learning_window_hours = 24
        self.minimum_pattern_evidence = 5
        
        # Cache TTL configurations
        self.pattern_cache_ttl = 1800  # 30 minutes
        self.risk_cache_ttl = 300     # 5 minutes
        self.user_profile_cache_ttl = 3600  # 1 hour
        
        # Pattern detection algorithms
        self.frequency_analyzers = {}
        self.geographic_analyzers = {}
        self.temporal_analyzers = {}
        self.behavioral_analyzers = {}
        
        # Risk assessment weights
        self.risk_weights = {
            "geographic_anomaly": 0.3,
            "temporal_anomaly": 0.2,
            "frequency_anomaly": 0.25,
            "behavioral_anomaly": 0.15,
            "known_threat_pattern": 0.8,
            "device_fingerprint_mismatch": 0.4,
            "previous_violations": 0.6
        }
        
        self._initialize_pattern_detectors()
    
    async def _get_cache(self):
        """Get Redis cache instance with lazy initialization"""
        if not self._cache:
            self._cache = await get_redis_cache()
        return self._cache
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache keys for auth patterns"""
        key_parts = [prefix] + [str(arg) for arg in args]
        base_key = ":auth_pattern:".join(key_parts)
        
        # Hash long keys to prevent Redis key length issues
        if len(base_key) > 200:
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"auth_pattern:{prefix}:hash:{key_hash}"
        
        return f"auth_pattern:{base_key}"
    
    def _initialize_pattern_detectors(self):
        """Initialize pattern detection algorithms"""
        # Frequency pattern detection
        self.frequency_analyzers = {
            "rapid_attempts": self._detect_rapid_login_attempts,
            "unusual_frequency": self._detect_unusual_frequency_patterns,
            "burst_activity": self._detect_burst_activity_patterns
        }
        
        # Geographic pattern detection
        self.geographic_analyzers = {
            "location_anomaly": self._detect_geographic_anomalies,
            "impossible_travel": self._detect_impossible_travel,
            "high_risk_locations": self._detect_high_risk_locations
        }
        
        # Temporal pattern detection
        self.temporal_analyzers = {
            "unusual_hours": self._detect_unusual_time_patterns,
            "session_duration": self._detect_session_duration_anomalies,
            "login_rhythm": self._detect_login_rhythm_patterns
        }
        
        # Behavioral pattern detection
        self.behavioral_analyzers = {
            "device_fingerprint": self._detect_device_fingerprint_anomalies,
            "user_agent_anomaly": self._detect_user_agent_anomalies,
            "navigation_pattern": self._detect_navigation_pattern_anomalies
        }
    
    async def record_auth_event(
        self,
        session: AsyncSession,
        event_type: AuthEventType,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        success: bool = True,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> AuthEvent:
        """
        Record authentication event and trigger pattern analysis
        """
        try:
            event_id = f"auth_{int(time.time() * 1000)}_{hashlib.md5(f'{user_id}_{ip_address}'.encode()).hexdigest()[:8]}"
            
            auth_event = AuthEvent(
                event_id=event_id,
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
                success=success,
                additional_data=additional_data or {},
                risk_indicators=[],
                pattern_matches=[]
            )
            
            # Perform real-time pattern analysis
            await self._analyze_event_patterns(session, auth_event)
            
            # Store event for historical analysis
            await self._store_auth_event(session, auth_event)
            
            # Trigger adaptive checkpoint evaluation
            if not success or auth_event.risk_indicators:
                await self._evaluate_adaptive_checkpoints(session, auth_event)
            
            self.logger.info(f"Recorded auth event: {event_type.value} for user {user_id} from {ip_address}")
            return auth_event
            
        except Exception as e:
            self.logger.error(f"Failed to record auth event: {str(e)}")
            raise
    
    async def assess_authentication_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        session_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment for authentication attempt
        """
        try:
            cache = await self._get_cache()
            risk_key = self._generate_cache_key("risk_assessment", user_id or "anonymous", ip_address)
            
            # Check cached assessment
            cached_assessment = await cache.get(risk_key)
            if cached_assessment:
                self.logger.debug(f"Using cached risk assessment for user {user_id}")
                return RiskAssessment(**cached_assessment)
            
            assessment_id = f"risk_{int(time.time() * 1000)}_{hashlib.md5(f'{user_id}_{ip_address}'.encode()).hexdigest()[:8]}"
            
            # Calculate risk factors
            contributing_factors = await self._calculate_risk_factors(
                session, user_id, ip_address, user_agent, additional_context or {}
            )
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(contributing_factors)
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Find matching patterns
            pattern_matches = await self._find_pattern_matches(session, user_id, ip_address, user_agent)
            
            # Generate recommendations
            recommended_actions = self._generate_risk_recommendations(
                overall_risk_score, risk_level, pattern_matches, contributing_factors
            )
            
            # Create risk assessment
            assessment = RiskAssessment(
                assessment_id=assessment_id,
                user_id=user_id,
                session_id=session_id,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                contributing_factors=contributing_factors,
                pattern_matches=pattern_matches,
                recommended_actions=recommended_actions,
                confidence=self._calculate_assessment_confidence(contributing_factors),
                assessment_time=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
            
            # Cache the assessment
            await cache.set(risk_key, asdict(assessment), ttl=self.risk_cache_ttl)
            
            # Log high-risk assessments
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await security_audit_service.log_security_violation(
                    session=session,
                    violation_type="HIGH_RISK_AUTH_ATTEMPT",
                    severity=risk_level.value.upper(),
                    violation_details={
                        "risk_score": overall_risk_score,
                        "contributing_factors": contributing_factors,
                        "pattern_matches": pattern_matches
                    },
                    user_id=user_id,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    blocked=False
                )
            
            self.logger.info(f"Risk assessment completed: {risk_level.value} ({overall_risk_score:.2f}) for user {user_id}")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Failed to assess authentication risk: {str(e)}")
            # Return minimal risk assessment on failure
            return RiskAssessment(
                assessment_id=f"error_{int(time.time())}",
                user_id=user_id,
                session_id=session_id,
                overall_risk_score=0.3,  # Moderate risk on error
                risk_level=RiskLevel.MEDIUM,
                contributing_factors={"assessment_error": 1.0},
                pattern_matches=[],
                recommended_actions=["additional_monitoring"],
                confidence=0.1,
                assessment_time=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=1)
            )
    
    async def create_adaptive_checkpoint(
        self,
        session: AsyncSession,
        checkpoint_type: str,
        trigger_conditions: Dict[str, Any],
        validation_strength: float = 0.8
    ) -> ValidationCheckpoint:
        """
        Create adaptive validation checkpoint based on learned patterns
        """
        try:
            checkpoint_id = f"checkpoint_{checkpoint_type}_{int(time.time())}"
            
            checkpoint = ValidationCheckpoint(
                checkpoint_id=checkpoint_id,
                checkpoint_type=checkpoint_type,
                trigger_conditions=trigger_conditions,
                validation_strength=validation_strength,
                bypass_conditions=self._generate_bypass_conditions(checkpoint_type),
                success_rate=0.8,  # Initial estimate
                false_positive_rate=0.1,  # Initial estimate
                created_at=datetime.utcnow(),
                effectiveness_score=0.0  # Will be calculated over time
            )
            
            # Store checkpoint
            self.active_checkpoints[checkpoint_id] = checkpoint
            
            # Log checkpoint creation
            await security_audit_service.log_security_action(
                session=session,
                action_type="CREATE_CHECKPOINT",
                target=checkpoint_type,
                reason="Adaptive security validation",
                evidence={
                    "trigger_conditions": trigger_conditions,
                    "validation_strength": validation_strength
                },
                severity="MEDIUM",
                auto_created=True
            )
            
            self.logger.info(f"Created adaptive checkpoint: {checkpoint_type} with strength {validation_strength}")
            return checkpoint
            
        except Exception as e:
            self.logger.error(f"Failed to create adaptive checkpoint: {str(e)}")
            raise
    
    async def evaluate_checkpoint_trigger(
        self,
        session: AsyncSession,
        checkpoint: ValidationCheckpoint,
        auth_event: AuthEvent
    ) -> bool:
        """
        Evaluate if authentication event should trigger validation checkpoint
        """
        try:
            trigger_conditions = checkpoint.trigger_conditions
            
            # Evaluate trigger conditions
            triggered = False
            
            # Risk score threshold
            if "min_risk_score" in trigger_conditions:
                risk_assessment = await self.assess_authentication_risk(
                    session, auth_event.user_id, auth_event.ip_address, auth_event.user_agent
                )
                if risk_assessment.overall_risk_score >= trigger_conditions["min_risk_score"]:
                    triggered = True
            
            # Pattern matches
            if "required_patterns" in trigger_conditions:
                required_patterns = trigger_conditions["required_patterns"]
                if any(pattern in auth_event.pattern_matches for pattern in required_patterns):
                    triggered = True
            
            # Event type conditions
            if "event_types" in trigger_conditions:
                if auth_event.event_type.value in trigger_conditions["event_types"]:
                    triggered = True
            
            # Frequency conditions
            if "max_frequency" in trigger_conditions:
                recent_events = await self._get_recent_events(
                    session, auth_event.user_id, auth_event.ip_address, timedelta(hours=1)
                )
                if len(recent_events) >= trigger_conditions["max_frequency"]:
                    triggered = True
            
            # Check bypass conditions
            if triggered:
                bypass_conditions = checkpoint.bypass_conditions
                
                # Trusted device bypass
                if "trusted_device" in bypass_conditions:
                    if auth_event.additional_data.get("device_trusted", False):
                        triggered = False
                
                # User role bypass
                if "admin_bypass" in bypass_conditions:
                    if auth_event.additional_data.get("user_role") == "admin":
                        triggered = False
            
            if triggered:
                self.logger.info(f"Checkpoint {checkpoint.checkpoint_id} triggered for user {auth_event.user_id}")
            
            return triggered
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate checkpoint trigger: {str(e)}")
            return False
    
    async def calculate_evidence_quality_score(
        self,
        session: AsyncSession,
        evidence_data: Dict[str, Any]
    ) -> float:
        """
        Calculate evidence quality score for security validation
        """
        try:
            quality_score = 0.0
            max_score = 0.0
            
            # Evidence source reliability
            source_reliability = evidence_data.get("source_reliability", 0.5)
            quality_score += source_reliability * 0.3
            max_score += 0.3
            
            # Data completeness
            required_fields = ["timestamp", "ip_address", "user_agent", "event_type"]
            completeness = sum(1 for field in required_fields if field in evidence_data) / len(required_fields)
            quality_score += completeness * 0.2
            max_score += 0.2
            
            # Temporal relevance (fresher evidence is better)
            if "timestamp" in evidence_data:
                try:
                    event_time = datetime.fromisoformat(evidence_data["timestamp"])
                    age_hours = (datetime.utcnow() - event_time).total_seconds() / 3600
                    temporal_score = max(0, 1 - (age_hours / 24))  # Score decreases over 24 hours
                    quality_score += temporal_score * 0.2
                except:
                    quality_score += 0.1  # Partial score for unparseable timestamp
                max_score += 0.2
            
            # Pattern correlation strength
            pattern_strength = evidence_data.get("pattern_correlation", 0.0)
            quality_score += pattern_strength * 0.15
            max_score += 0.15
            
            # Cross-validation with other sources
            cross_validation_score = evidence_data.get("cross_validation_score", 0.0)
            quality_score += cross_validation_score * 0.15
            max_score += 0.15
            
            # Normalize score
            if max_score > 0:
                normalized_score = quality_score / max_score
            else:
                normalized_score = 0.0
            
            # Apply quality thresholds
            if normalized_score < 0.3:
                quality_level = "poor"
            elif normalized_score < 0.6:
                quality_level = "moderate"
            elif normalized_score < 0.8:
                quality_level = "good"
            else:
                quality_level = "excellent"
            
            self.logger.debug(f"Evidence quality score: {normalized_score:.2f} ({quality_level})")
            return normalized_score
            
        except Exception as e:
            self.logger.error(f"Failed to calculate evidence quality score: {str(e)}")
            return 0.3  # Default moderate score on error
    
    async def update_pattern_learning(
        self,
        session: AsyncSession,
        pattern_id: str,
        validation_outcome: bool,
        effectiveness_score: float
    ):
        """
        Update pattern learning based on validation outcomes
        """
        try:
            if pattern_id in self.detected_patterns:
                pattern = self.detected_patterns[pattern_id]
                
                # Update confidence based on validation outcome
                if validation_outcome:
                    pattern.confidence_score = min(1.0, pattern.confidence_score * 1.05)
                else:
                    pattern.confidence_score = max(0.1, pattern.confidence_score * 0.95)
                
                # Update evidence count
                pattern.evidence_count += 1
                pattern.last_updated = datetime.utcnow()
                
                # Adjust risk level based on effectiveness
                if effectiveness_score > 0.8 and pattern.risk_level == RiskLevel.MEDIUM:
                    pattern.risk_level = RiskLevel.HIGH
                elif effectiveness_score < 0.3 and pattern.risk_level == RiskLevel.HIGH:
                    pattern.risk_level = RiskLevel.MEDIUM
                
                # Log pattern learning update
                await security_audit_service.log_security_action(
                    session=session,
                    action_type="UPDATE_PATTERN_LEARNING",
                    target=pattern_id,
                    reason="Pattern validation outcome",
                    evidence={
                        "validation_outcome": validation_outcome,
                        "effectiveness_score": effectiveness_score,
                        "new_confidence": pattern.confidence_score,
                        "evidence_count": pattern.evidence_count
                    },
                    severity="LOW",
                    auto_created=True
                )
                
                self.logger.info(f"Updated pattern learning for {pattern_id}: confidence={pattern.confidence_score:.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to update pattern learning: {str(e)}")
    
    # Pattern Detection Implementation Methods
    
    async def _analyze_event_patterns(self, session: AsyncSession, auth_event: AuthEvent):
        """Analyze authentication event for pattern matches"""
        try:
            detected_patterns = []
            
            # Run frequency analyzers
            for analyzer_name, analyzer_func in self.frequency_analyzers.items():
                if await analyzer_func(session, auth_event):
                    detected_patterns.append(f"frequency_{analyzer_name}")
            
            # Run geographic analyzers
            for analyzer_name, analyzer_func in self.geographic_analyzers.items():
                if await analyzer_func(session, auth_event):
                    detected_patterns.append(f"geographic_{analyzer_name}")
            
            # Run temporal analyzers
            for analyzer_name, analyzer_func in self.temporal_analyzers.items():
                if await analyzer_func(session, auth_event):
                    detected_patterns.append(f"temporal_{analyzer_name}")
            
            # Run behavioral analyzers
            for analyzer_name, analyzer_func in self.behavioral_analyzers.items():
                if await analyzer_func(session, auth_event):
                    detected_patterns.append(f"behavioral_{analyzer_name}")
            
            auth_event.pattern_matches = detected_patterns
            
            # Update risk indicators based on patterns
            if detected_patterns:
                auth_event.risk_indicators.extend(detected_patterns)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze event patterns: {str(e)}")
    
    async def _detect_rapid_login_attempts(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect rapid login attempts from same IP/user"""
        try:
            # Get recent events from same IP in last 5 minutes
            recent_events = await self._get_recent_events(
                session, auth_event.user_id, auth_event.ip_address, timedelta(minutes=5)
            )
            
            # Count failed login attempts
            failed_attempts = [e for e in recent_events if e.event_type == AuthEventType.LOGIN_FAILURE]
            
            return len(failed_attempts) >= 5
            
        except Exception as e:
            self.logger.error(f"Failed to detect rapid login attempts: {str(e)}")
            return False
    
    async def _detect_unusual_frequency_patterns(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect unusual frequency patterns in authentication attempts"""
        try:
            # Get recent events from same IP/user in last hour
            recent_events = await self._get_recent_events(
                session, auth_event.user_id, auth_event.ip_address, timedelta(hours=1)
            )
            
            # Check for unusual frequency (more than 20 attempts in an hour)
            return len(recent_events) > 20
            
        except Exception as e:
            self.logger.error(f"Failed to detect unusual frequency patterns: {str(e)}")
            return False
    
    async def _detect_burst_activity_patterns(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect burst activity patterns"""
        try:
            # Get recent events from same IP in last 10 minutes
            recent_events = await self._get_recent_events(
                session, auth_event.user_id, auth_event.ip_address, timedelta(minutes=10)
            )
            
            # Check for burst activity (more than 10 attempts in 10 minutes)
            return len(recent_events) > 10
            
        except Exception as e:
            self.logger.error(f"Failed to detect burst activity patterns: {str(e)}")
            return False
    
    async def _detect_geographic_anomalies(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect geographic location anomalies"""
        try:
            if not auth_event.user_id:
                return False
            
            # Get user's recent locations (simplified - would use GeoIP in practice)
            cache = await self._get_cache()
            user_locations_key = self._generate_cache_key("user_locations", auth_event.user_id)
            
            user_locations = await cache.get(user_locations_key) or []
            current_location = auth_event.ip_address  # Simplified
            
            # Check if location is new/unusual
            if current_location not in user_locations:
                if len(user_locations) > 0:  # Not first login
                    return True
                
                # Add current location to known locations
                user_locations.append(current_location)
                await cache.set(user_locations_key, user_locations[-10:], ttl=86400)  # Keep last 10 locations
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to detect geographic anomalies: {str(e)}")
            return False
    
    async def _detect_unusual_time_patterns(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect unusual login time patterns"""
        try:
            if not auth_event.user_id:
                return False
            
            # Get user's typical login hours
            cache = await self._get_cache()
            user_hours_key = self._generate_cache_key("user_hours", auth_event.user_id)
            
            typical_hours = await cache.get(user_hours_key) or []
            current_hour = auth_event.timestamp.hour
            
            # Check if current hour is unusual (simplified algorithm)
            if typical_hours:
                hour_counts = defaultdict(int)
                for hour in typical_hours:
                    hour_counts[hour] += 1
                
                # Consider unusual if less than 10% of typical activity
                if hour_counts[current_hour] < max(1, len(typical_hours) * 0.1):
                    return True
            
            # Update typical hours
            typical_hours.append(current_hour)
            await cache.set(user_hours_key, typical_hours[-100:], ttl=86400 * 7)  # Keep last 100 logins
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to detect unusual time patterns: {str(e)}")
            return False
    
    async def _detect_device_fingerprint_anomalies(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect device fingerprint anomalies"""
        try:
            if not auth_event.user_id:
                return False
            
            # Get user's known user agents
            cache = await self._get_cache()
            user_agents_key = self._generate_cache_key("user_agents", auth_event.user_id)
            
            known_agents = await cache.get(user_agents_key) or []
            current_agent = auth_event.user_agent
            
            # Simple similarity check (would be more sophisticated in practice)
            similar_agent = any(
                self._calculate_string_similarity(current_agent, known_agent) > 0.8
                for known_agent in known_agents
            )
            
            if not similar_agent and known_agents:
                return True
            
            # Add current user agent if not similar to existing ones
            if not similar_agent:
                known_agents.append(current_agent)
                await cache.set(user_agents_key, known_agents[-20:], ttl=86400 * 30)  # Keep for 30 days
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to detect device fingerprint anomalies: {str(e)}")
            return False
    
    async def _detect_impossible_travel(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect impossible travel patterns"""
        try:
            # Placeholder implementation - would calculate travel time between locations
            return False
        except Exception as e:
            self.logger.error(f"Failed to detect impossible travel: {str(e)}")
            return False
    
    async def _detect_high_risk_locations(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect logins from high-risk geographic locations"""
        try:
            # Placeholder implementation - would check against threat intelligence
            return False
        except Exception as e:
            self.logger.error(f"Failed to detect high-risk locations: {str(e)}")
            return False
    
    async def _detect_session_duration_anomalies(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect unusual session duration patterns"""
        try:
            # Placeholder implementation - would analyze session lengths
            return False
        except Exception as e:
            self.logger.error(f"Failed to detect session duration anomalies: {str(e)}")
            return False
    
    async def _detect_login_rhythm_patterns(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect unusual login rhythm patterns"""
        try:
            # Placeholder implementation - would analyze login timing patterns
            return False
        except Exception as e:
            self.logger.error(f"Failed to detect login rhythm patterns: {str(e)}")
            return False
    
    async def _detect_user_agent_anomalies(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect user agent anomalies"""
        try:
            # Check for suspicious user agent patterns
            suspicious_patterns = ["bot", "crawler", "python", "curl", "automated"]
            user_agent_lower = auth_event.user_agent.lower()
            return any(pattern in user_agent_lower for pattern in suspicious_patterns)
        except Exception as e:
            self.logger.error(f"Failed to detect user agent anomalies: {str(e)}")
            return False
    
    async def _detect_navigation_pattern_anomalies(self, session: AsyncSession, auth_event: AuthEvent) -> bool:
        """Detect navigation pattern anomalies"""
        try:
            # Placeholder implementation - would analyze navigation patterns
            return False
        except Exception as e:
            self.logger.error(f"Failed to detect navigation pattern anomalies: {str(e)}")
            return False
    
    # Risk Assessment Implementation Methods
    
    async def _calculate_risk_factors(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        additional_context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate individual risk factors"""
        try:
            risk_factors = {}
            
            # Geographic risk
            risk_factors["geographic_anomaly"] = await self._calculate_geographic_risk(
                session, user_id, ip_address
            )
            
            # Temporal risk
            risk_factors["temporal_anomaly"] = await self._calculate_temporal_risk(
                session, user_id
            )
            
            # Frequency risk
            risk_factors["frequency_anomaly"] = await self._calculate_frequency_risk(
                session, user_id, ip_address
            )
            
            # Device risk
            risk_factors["device_fingerprint_mismatch"] = await self._calculate_device_risk(
                session, user_id, user_agent
            )
            
            # Historical violations
            risk_factors["previous_violations"] = await self._calculate_violation_risk(
                session, user_id, ip_address
            )
            
            # Known threat patterns
            risk_factors["known_threat_pattern"] = await self._calculate_threat_pattern_risk(
                session, ip_address, user_agent
            )
            
            return risk_factors
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk factors: {str(e)}")
            return {"calculation_error": 0.5}
    
    def _calculate_overall_risk_score(self, contributing_factors: Dict[str, float]) -> float:
        """Calculate weighted overall risk score"""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for factor, score in contributing_factors.items():
                weight = self.risk_weights.get(factor, 0.1)  # Default weight
                total_weighted_score += score * weight
                total_weight += weight
            
            if total_weight > 0:
                overall_score = total_weighted_score / total_weight
            else:
                overall_score = 0.0
            
            # Apply non-linear scaling for better risk distribution
            return min(1.0, overall_score ** 0.8)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate overall risk score: {str(e)}")
            return 0.5
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from numeric score"""
        if risk_score < 0.2:
            return RiskLevel.MINIMAL
        elif risk_score < 0.4:
            return RiskLevel.LOW
        elif risk_score < 0.7:
            return RiskLevel.MEDIUM
        elif risk_score < 0.9:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    # Utility Methods
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        # Simple Jaccard similarity on character n-grams
        n = 3
        set1 = set(str1[i:i+n] for i in range(len(str1) - n + 1))
        set2 = set(str2[i:i+n] for i in range(len(str2) - n + 1))
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _get_recent_events(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        time_window: timedelta
    ) -> List[AuthEvent]:
        """Get recent authentication events for analysis"""
        try:
            # In practice, this would query a dedicated auth events table
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get recent events: {str(e)}")
            return []
    
    async def _store_auth_event(self, session: AsyncSession, auth_event: AuthEvent):
        """Store authentication event for historical analysis"""
        try:
            # Store in security audit log
            await security_audit_service.log_data_access(
                session=session,
                user_id=auth_event.user_id or 0,
                service_name="authentication",
                access_type=auth_event.event_type.value,
                table_name="auth_events",
                row_count=1,
                sensitive_data_accessed=True,
                access_pattern={
                    "success": auth_event.success,
                    "risk_indicators": auth_event.risk_indicators,
                    "pattern_matches": auth_event.pattern_matches
                },
                session_id=auth_event.session_id,
                ip_address=auth_event.ip_address
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store auth event: {str(e)}")
    
    # Placeholder methods for risk calculation (would be implemented with real data)
    
    async def _calculate_geographic_risk(self, session: AsyncSession, user_id: Optional[int], ip_address: str) -> float:
        """Calculate geographic risk factor"""
        return 0.1  # Placeholder
    
    async def _calculate_temporal_risk(self, session: AsyncSession, user_id: Optional[int]) -> float:
        """Calculate temporal risk factor"""
        return 0.1  # Placeholder
    
    async def _calculate_frequency_risk(self, session: AsyncSession, user_id: Optional[int], ip_address: str) -> float:
        """Calculate frequency risk factor"""
        return 0.1  # Placeholder
    
    async def _calculate_device_risk(self, session: AsyncSession, user_id: Optional[int], user_agent: str) -> float:
        """Calculate device risk factor"""
        return 0.1  # Placeholder
    
    async def _calculate_violation_risk(self, session: AsyncSession, user_id: Optional[int], ip_address: str) -> float:
        """Calculate previous violations risk factor"""
        return 0.1  # Placeholder
    
    async def _calculate_threat_pattern_risk(self, session: AsyncSession, ip_address: str, user_agent: str) -> float:
        """Calculate known threat pattern risk factor"""
        return 0.1  # Placeholder
    
    def _calculate_assessment_confidence(self, contributing_factors: Dict[str, float]) -> float:
        """Calculate confidence in risk assessment"""
        # Confidence based on number of factors and their variance
        if not contributing_factors:
            return 0.1
        
        factor_count = len(contributing_factors)
        factor_variance = np.var(list(contributing_factors.values())) if len(contributing_factors) > 1 else 0.0
        
        # More factors and lower variance = higher confidence
        confidence = min(1.0, (factor_count / 10.0) * (1.0 - factor_variance))
        return max(0.1, confidence)
    
    def _generate_bypass_conditions(self, checkpoint_type: str) -> Dict[str, Any]:
        """Generate bypass conditions for checkpoint type"""
        return {
            "trusted_device": True,
            "admin_bypass": checkpoint_type != "critical_security"
        }
    
    def _generate_risk_recommendations(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        pattern_matches: List[str],
        contributing_factors: Dict[str, float]
    ) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend(["block_authentication", "immediate_security_review"])
        elif risk_level == RiskLevel.HIGH:
            recommendations.extend(["require_additional_authentication", "enhanced_monitoring"])
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.extend(["additional_validation", "increased_logging"])
        else:
            recommendations.append("standard_monitoring")
        
        # Pattern-specific recommendations
        if "rapid_attempts" in pattern_matches:
            recommendations.append("implement_rate_limiting")
        if "geographic_anomaly" in pattern_matches:
            recommendations.append("verify_location")
        if "device_fingerprint_anomaly" in pattern_matches:
            recommendations.append("verify_device")
        
        return recommendations
    
    async def _find_pattern_matches(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str
    ) -> List[str]:
        """Find matching patterns for current context"""
        # Placeholder - would implement pattern matching logic
        return []
    
    async def _evaluate_adaptive_checkpoints(self, session: AsyncSession, auth_event: AuthEvent):
        """Evaluate if adaptive checkpoints should be triggered"""
        try:
            for checkpoint in self.active_checkpoints.values():
                triggered = await self.evaluate_checkpoint_trigger(session, checkpoint, auth_event)
                if triggered:
                    await security_audit_service.log_security_action(
                        session=session,
                        action_type="TRIGGER_CHECKPOINT",
                        target=checkpoint.checkpoint_id,
                        reason="Adaptive security validation triggered",
                        evidence={
                            "event_type": auth_event.event_type.value,
                            "pattern_matches": auth_event.pattern_matches,
                            "risk_indicators": auth_event.risk_indicators
                        },
                        severity="MEDIUM",
                        user_id=auth_event.user_id,
                        session_id=auth_event.session_id,
                        auto_created=True
                    )
        except Exception as e:
            self.logger.error(f"Failed to evaluate adaptive checkpoints: {str(e)}")


# Global service instance
auth_pattern_detection_service = AuthPatternDetectionService()