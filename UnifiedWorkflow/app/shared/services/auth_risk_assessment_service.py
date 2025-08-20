"""
Authentication Risk Assessment Service

Advanced risk assessment module with dynamic scoring that integrates with the authentication
learning system to provide real-time, adaptive risk evaluation for authentication attempts.

Features:
- Dynamic risk threshold adjustment
- Multi-factor risk analysis
- Behavioral baseline learning
- Threat intelligence integration
- Evidence-weighted scoring
"""

import json
import time
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

from shared.services.auth_pattern_detection_service import (
    AuthEventType, RiskLevel, RiskAssessment, auth_pattern_detection_service
)
from shared.services.security_audit_service import security_audit_service
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

class RiskFactorType(Enum):
    """Risk factor categories for assessment"""
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    FREQUENCY = "frequency"
    BEHAVIORAL = "behavioral"
    DEVICE = "device"
    NETWORK = "network"
    HISTORICAL = "historical"
    THREAT_INTEL = "threat_intel"

@dataclass
class RiskFactor:
    """Individual risk factor in assessment"""
    factor_type: RiskFactorType
    factor_name: str
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    weight: float     # Importance weight
    evidence: Dict[str, Any]
    source: str
    timestamp: datetime

@dataclass
class UserRiskProfile:
    """User risk profile for baseline comparison"""
    user_id: int
    baseline_risk: float
    typical_locations: List[str]
    typical_hours: List[int]
    typical_devices: List[str]
    login_frequency_pattern: Dict[str, float]
    security_violations_count: int
    last_updated: datetime
    profile_confidence: float

@dataclass
class DynamicThreshold:
    """Dynamic risk threshold configuration"""
    threshold_id: str
    risk_level: RiskLevel
    base_threshold: float
    current_threshold: float
    adjustment_factor: float
    last_adjustment: datetime
    adjustment_history: List[Tuple[datetime, float, str]]  # (time, threshold, reason)

class AuthRiskAssessmentService:
    """
    Advanced Authentication Risk Assessment Service
    
    Provides dynamic, learning-based risk assessment for authentication attempts
    with adaptive thresholds and multi-factor analysis.
    """
    
    def __init__(self):
        self.logger = logger
        self._cache = None
        
        # Risk assessment configuration
        self.assessment_weights = {
            RiskFactorType.GEOGRAPHIC: 0.20,
            RiskFactorType.TEMPORAL: 0.15,
            RiskFactorType.FREQUENCY: 0.20,
            RiskFactorType.BEHAVIORAL: 0.15,
            RiskFactorType.DEVICE: 0.10,
            RiskFactorType.NETWORK: 0.10,
            RiskFactorType.HISTORICAL: 0.25,
            RiskFactorType.THREAT_INTEL: 0.35
        }
        
        # Dynamic threshold management
        self.dynamic_thresholds = {
            RiskLevel.LOW: DynamicThreshold(
                threshold_id="low_risk",
                risk_level=RiskLevel.LOW,
                base_threshold=0.2,
                current_threshold=0.2,
                adjustment_factor=0.05,
                last_adjustment=datetime.utcnow(),
                adjustment_history=[]
            ),
            RiskLevel.MEDIUM: DynamicThreshold(
                threshold_id="medium_risk",
                risk_level=RiskLevel.MEDIUM,
                base_threshold=0.4,
                current_threshold=0.4,
                adjustment_factor=0.05,
                last_adjustment=datetime.utcnow(),
                adjustment_history=[]
            ),
            RiskLevel.HIGH: DynamicThreshold(
                threshold_id="high_risk",
                risk_level=RiskLevel.HIGH,
                base_threshold=0.7,
                current_threshold=0.7,
                adjustment_factor=0.05,
                last_adjustment=datetime.utcnow(),
                adjustment_history=[]
            ),
            RiskLevel.CRITICAL: DynamicThreshold(
                threshold_id="critical_risk",
                risk_level=RiskLevel.CRITICAL,
                base_threshold=0.9,
                current_threshold=0.9,
                adjustment_factor=0.03,
                last_adjustment=datetime.utcnow(),
                adjustment_history=[]
            )
        }
        
        # User risk profiles cache
        self.user_profiles: Dict[int, UserRiskProfile] = {}
        
        # Cache TTL configurations
        self.profile_cache_ttl = 3600  # 1 hour
        self.assessment_cache_ttl = 300  # 5 minutes
        self.factor_cache_ttl = 600   # 10 minutes
        
        # Risk factor analyzers
        self.risk_analyzers = {
            RiskFactorType.GEOGRAPHIC: self._analyze_geographic_risk,
            RiskFactorType.TEMPORAL: self._analyze_temporal_risk,
            RiskFactorType.FREQUENCY: self._analyze_frequency_risk,
            RiskFactorType.BEHAVIORAL: self._analyze_behavioral_risk,
            RiskFactorType.DEVICE: self._analyze_device_risk,
            RiskFactorType.NETWORK: self._analyze_network_risk,
            RiskFactorType.HISTORICAL: self._analyze_historical_risk,
            RiskFactorType.THREAT_INTEL: self._analyze_threat_intel_risk
        }
        
        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_decay = 0.95
        self.profile_update_threshold = 0.7
        
    async def _get_cache(self):
        """Get Redis cache instance with lazy initialization"""
        if not self._cache:
            self._cache = await get_redis_cache()
        return self._cache
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache keys for risk assessment"""
        key_parts = [prefix] + [str(arg) for arg in args]
        base_key = ":risk_assessment:".join(key_parts)
        
        if len(base_key) > 200:
            import hashlib
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"risk_assessment:{prefix}:hash:{key_hash}"
        
        return f"risk_assessment:{base_key}"
    
    async def perform_comprehensive_risk_assessment(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        session_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment with dynamic thresholds
        """
        try:
            assessment_start = time.time()
            
            # Get or create user risk profile
            user_profile = await self._get_user_risk_profile(session, user_id) if user_id else None
            
            # Analyze all risk factors
            risk_factors = await self._analyze_all_risk_factors(
                session, user_id, ip_address, user_agent, user_profile, additional_context or {}
            )
            
            # Calculate weighted risk score
            overall_risk_score = self._calculate_weighted_risk_score(risk_factors)
            
            # Apply dynamic thresholds
            risk_level = self._determine_risk_level_with_dynamic_thresholds(overall_risk_score)
            
            # Generate evidence-based confidence score
            confidence = self._calculate_assessment_confidence(risk_factors)
            
            # Extract contributing factors for legacy compatibility
            contributing_factors = {
                factor.factor_name: factor.risk_score 
                for factor in risk_factors
            }
            
            # Find pattern matches
            pattern_matches = await self._find_advanced_pattern_matches(
                session, user_id, ip_address, user_agent, risk_factors
            )
            
            # Generate adaptive recommendations
            recommendations = self._generate_adaptive_recommendations(
                overall_risk_score, risk_level, risk_factors, pattern_matches
            )
            
            # Create comprehensive assessment
            assessment = RiskAssessment(
                assessment_id=f"risk_{int(time.time() * 1000)}_{user_id or 'anon'}",
                user_id=user_id,
                session_id=session_id,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                contributing_factors=contributing_factors,
                pattern_matches=pattern_matches,
                recommended_actions=recommendations,
                confidence=confidence,
                assessment_time=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=5)
            )
            
            # Cache assessment
            cache = await self._get_cache()
            cache_key = self._generate_cache_key("assessment", user_id or "anon", ip_address)
            await cache.set(cache_key, asdict(assessment), ttl=self.assessment_cache_ttl)
            
            # Update user profile if applicable
            if user_profile and user_id:
                await self._update_user_risk_profile(
                    session, user_profile, risk_factors, overall_risk_score
                )
            
            # Log high-risk assessments with detailed factors
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._log_high_risk_assessment(
                    session, assessment, risk_factors, user_profile
                )
            
            # Update dynamic thresholds based on assessment outcomes
            await self._update_dynamic_thresholds(risk_level, overall_risk_score)
            
            assessment_time = (time.time() - assessment_start) * 1000
            self.logger.info(
                f"Risk assessment completed in {assessment_time:.1f}ms: "
                f"{risk_level.value} ({overall_risk_score:.3f}) for user {user_id}"
            )
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Failed to perform comprehensive risk assessment: {str(e)}")
            
            # Return safe fallback assessment
            return RiskAssessment(
                assessment_id=f"error_{int(time.time())}",
                user_id=user_id,
                session_id=session_id,
                overall_risk_score=0.5,  # Moderate risk on error
                risk_level=RiskLevel.MEDIUM,
                contributing_factors={"assessment_error": 1.0},
                pattern_matches=[],
                recommended_actions=["additional_monitoring", "manual_review"],
                confidence=0.1,
                assessment_time=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=1)
            )
    
    async def _get_user_risk_profile(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> Optional[UserRiskProfile]:
        """Get or create user risk profile"""
        try:
            cache = await self._get_cache()
            profile_key = self._generate_cache_key("user_profile", user_id)
            
            # Check cache first
            cached_profile = await cache.get(profile_key)
            if cached_profile:
                return UserRiskProfile(**cached_profile)
            
            # Check if profile exists in memory
            if user_id in self.user_profiles:
                profile = self.user_profiles[user_id]
                
                # Cache the profile
                await cache.set(profile_key, asdict(profile), ttl=self.profile_cache_ttl)
                return profile
            
            # Create new profile
            profile = await self._create_user_risk_profile(session, user_id)
            if profile:
                self.user_profiles[user_id] = profile
                await cache.set(profile_key, asdict(profile), ttl=self.profile_cache_ttl)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to get user risk profile for user {user_id}: {str(e)}")
            return None
    
    async def _create_user_risk_profile(
        self, 
        session: AsyncSession, 
        user_id: int
    ) -> Optional[UserRiskProfile]:
        """Create new user risk profile from historical data"""
        try:
            # In a real implementation, this would analyze historical auth logs
            # For now, create a basic profile
            
            profile = UserRiskProfile(
                user_id=user_id,
                baseline_risk=0.3,  # Default baseline
                typical_locations=[],
                typical_hours=[],
                typical_devices=[],
                login_frequency_pattern={},
                security_violations_count=0,
                last_updated=datetime.utcnow(),
                profile_confidence=0.1  # Low confidence for new profile
            )
            
            self.logger.info(f"Created new risk profile for user {user_id}")
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create user risk profile: {str(e)}")
            return None
    
    async def _analyze_all_risk_factors(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> List[RiskFactor]:
        """Analyze all risk factors for the authentication attempt"""
        try:
            risk_factors = []
            
            # Analyze each risk factor type
            for factor_type, analyzer_func in self.risk_analyzers.items():
                try:
                    factor = await analyzer_func(
                        session, user_id, ip_address, user_agent, user_profile, additional_context
                    )
                    if factor:
                        risk_factors.append(factor)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {factor_type.value} risk: {str(e)}")
                    
                    # Add error factor with minimal risk
                    risk_factors.append(RiskFactor(
                        factor_type=factor_type,
                        factor_name=f"{factor_type.value}_analysis_error",
                        risk_score=0.2,
                        confidence=0.1,
                        weight=self.assessment_weights.get(factor_type, 0.1),
                        evidence={"error": str(e)},
                        source="error_handler",
                        timestamp=datetime.utcnow()
                    ))
            
            return risk_factors
            
        except Exception as e:
            self.logger.error(f"Failed to analyze risk factors: {str(e)}")
            return []
    
    def _calculate_weighted_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate weighted overall risk score from individual factors"""
        try:
            if not risk_factors:
                return 0.5  # Default moderate risk
            
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for factor in risk_factors:
                # Weight by both configured weight and confidence
                effective_weight = factor.weight * factor.confidence
                total_weighted_score += factor.risk_score * effective_weight
                total_weight += effective_weight
            
            if total_weight > 0:
                weighted_score = total_weighted_score / total_weight
            else:
                weighted_score = 0.5
            
            # Apply non-linear scaling for better risk distribution
            # High confidence factors have more influence
            confidence_adjustment = np.mean([f.confidence for f in risk_factors])
            adjusted_score = weighted_score * (0.7 + 0.3 * confidence_adjustment)
            
            return min(1.0, max(0.0, adjusted_score))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate weighted risk score: {str(e)}")
            return 0.5
    
    def _determine_risk_level_with_dynamic_thresholds(self, risk_score: float) -> RiskLevel:
        """Determine risk level using dynamic thresholds"""
        try:
            # Sort thresholds by value
            sorted_thresholds = sorted(
                self.dynamic_thresholds.values(),
                key=lambda t: t.current_threshold
            )
            
            # Find appropriate risk level
            for threshold in sorted_thresholds:
                if risk_score >= threshold.current_threshold:
                    continue
                return threshold.risk_level
            
            # If score exceeds all thresholds, return highest level
            return RiskLevel.CRITICAL
            
        except Exception as e:
            self.logger.error(f"Failed to determine risk level: {str(e)}")
            return RiskLevel.MEDIUM
    
    def _calculate_assessment_confidence(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate confidence in the risk assessment"""
        try:
            if not risk_factors:
                return 0.1
            
            # Confidence based on factor count, individual confidences, and evidence quality
            factor_count_score = min(1.0, len(risk_factors) / 8.0)  # More factors = higher confidence
            
            avg_factor_confidence = np.mean([f.confidence for f in risk_factors])
            
            # Evidence quality score based on recency and source reliability
            evidence_scores = []
            for factor in risk_factors:
                age_hours = (datetime.utcnow() - factor.timestamp).total_seconds() / 3600
                recency_score = max(0.1, 1.0 - (age_hours / 24.0))  # Decay over 24 hours
                
                source_reliability = {
                    "user_history": 0.9,
                    "threat_intelligence": 0.8,
                    "pattern_analysis": 0.7,
                    "heuristic": 0.6,
                    "error_handler": 0.2
                }.get(factor.source, 0.5)
                
                evidence_scores.append(recency_score * source_reliability)
            
            avg_evidence_quality = np.mean(evidence_scores) if evidence_scores else 0.5
            
            # Combined confidence score
            overall_confidence = (
                factor_count_score * 0.3 +
                avg_factor_confidence * 0.4 +
                avg_evidence_quality * 0.3
            )
            
            return min(1.0, max(0.1, overall_confidence))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate assessment confidence: {str(e)}")
            return 0.5
    
    # Risk Factor Analyzers
    
    async def _analyze_geographic_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze geographic risk factors"""
        try:
            risk_score = 0.1  # Default low risk
            confidence = 0.5
            evidence = {"ip_address": ip_address}
            
            if user_profile and user_profile.typical_locations:
                # Check if IP is in typical locations (simplified)
                if ip_address not in user_profile.typical_locations:
                    risk_score = 0.6  # Moderate risk for new location
                    evidence["location_anomaly"] = True
                    confidence = 0.8
                else:
                    risk_score = 0.1  # Low risk for known location
                    evidence["known_location"] = True
                    confidence = 0.9
            
            # Check for high-risk geographic regions (placeholder)
            high_risk_patterns = ["192.168.", "10.0.", "172.16."]  # Internal IPs (lower risk)
            if any(pattern in ip_address for pattern in high_risk_patterns):
                risk_score *= 0.5  # Lower risk for internal IPs
                evidence["internal_network"] = True
            
            return RiskFactor(
                factor_type=RiskFactorType.GEOGRAPHIC,
                factor_name="geographic_location_analysis",
                risk_score=risk_score,
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.GEOGRAPHIC],
                evidence=evidence,
                source="pattern_analysis",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze geographic risk: {str(e)}")
            return None
    
    async def _analyze_temporal_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze temporal risk factors"""
        try:
            current_hour = datetime.utcnow().hour
            risk_score = 0.1
            confidence = 0.6
            evidence = {"login_hour": current_hour}
            
            if user_profile and user_profile.typical_hours:
                # Check if current hour is typical for user
                hour_frequency = user_profile.typical_hours.count(current_hour)
                total_logins = len(user_profile.typical_hours)
                
                if total_logins > 0:
                    hour_probability = hour_frequency / total_logins
                    
                    if hour_probability < 0.05:  # Less than 5% of logins at this hour
                        risk_score = 0.7
                        evidence["unusual_hour"] = True
                        confidence = 0.8
                    elif hour_probability > 0.2:  # More than 20% of logins at this hour
                        risk_score = 0.1
                        evidence["typical_hour"] = True
                        confidence = 0.9
            
            # General time-based risk (late night/early morning slightly higher risk)
            if current_hour in [1, 2, 3, 4, 5]:
                risk_score += 0.1
                evidence["late_night_access"] = True
            
            return RiskFactor(
                factor_type=RiskFactorType.TEMPORAL,
                factor_name="temporal_pattern_analysis",
                risk_score=min(1.0, risk_score),
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.TEMPORAL],
                evidence=evidence,
                source="pattern_analysis",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze temporal risk: {str(e)}")
            return None
    
    async def _analyze_frequency_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze frequency-based risk factors"""
        try:
            risk_score = 0.1
            confidence = 0.7
            evidence = {}
            
            # Get recent authentication attempts (placeholder implementation)
            cache = await self._get_cache()
            recent_attempts_key = self._generate_cache_key("recent_attempts", ip_address)
            recent_attempts = await cache.get(recent_attempts_key) or []
            
            # Count recent attempts
            current_time = time.time()
            recent_count = len([
                attempt for attempt in recent_attempts 
                if current_time - attempt < 300  # Last 5 minutes
            ])
            
            # Update recent attempts
            recent_attempts.append(current_time)
            recent_attempts = [t for t in recent_attempts if current_time - t < 3600]  # Keep last hour
            await cache.set(recent_attempts_key, recent_attempts, ttl=3600)
            
            evidence["recent_attempts_count"] = recent_count
            
            # Assess frequency risk
            if recent_count > 10:  # More than 10 attempts in 5 minutes
                risk_score = 0.9
                evidence["high_frequency_detected"] = True
                confidence = 0.9
            elif recent_count > 5:  # 5-10 attempts in 5 minutes
                risk_score = 0.6
                evidence["moderate_frequency_detected"] = True
                confidence = 0.8
            elif recent_count > 2:  # 2-5 attempts in 5 minutes
                risk_score = 0.3
                evidence["elevated_frequency_detected"] = True
                confidence = 0.7
            
            return RiskFactor(
                factor_type=RiskFactorType.FREQUENCY,
                factor_name="authentication_frequency_analysis",
                risk_score=risk_score,
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.FREQUENCY],
                evidence=evidence,
                source="pattern_analysis",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze frequency risk: {str(e)}")
            return None
    
    async def _analyze_behavioral_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze behavioral risk factors"""
        try:
            risk_score = 0.1
            confidence = 0.6
            evidence = {"user_agent": user_agent[:100]}  # Truncate for security
            
            # Analyze user agent patterns
            if user_profile and user_profile.typical_devices:
                # Simple similarity check for user agents
                agent_similarity_scores = []
                for known_agent in user_profile.typical_devices:
                    similarity = self._calculate_user_agent_similarity(user_agent, known_agent)
                    agent_similarity_scores.append(similarity)
                
                if agent_similarity_scores:
                    max_similarity = max(agent_similarity_scores)
                    evidence["max_device_similarity"] = max_similarity
                    
                    if max_similarity < 0.3:  # Very different from known devices
                        risk_score = 0.8
                        evidence["unknown_device"] = True
                        confidence = 0.8
                    elif max_similarity > 0.8:  # Very similar to known device
                        risk_score = 0.1
                        evidence["known_device"] = True
                        confidence = 0.9
                    else:  # Moderate similarity
                        risk_score = 0.4
                        evidence["similar_device"] = True
                        confidence = 0.7
            
            # Check for suspicious user agent patterns
            suspicious_patterns = [
                "bot", "crawler", "spider", "scraper", "automated",
                "python", "curl", "wget", "postman"
            ]
            
            if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
                risk_score += 0.3
                evidence["suspicious_user_agent"] = True
                confidence = 0.9
            
            return RiskFactor(
                factor_type=RiskFactorType.BEHAVIORAL,
                factor_name="behavioral_pattern_analysis",
                risk_score=min(1.0, risk_score),
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.BEHAVIORAL],
                evidence=evidence,
                source="pattern_analysis",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze behavioral risk: {str(e)}")
            return None
    
    async def _analyze_device_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze device-based risk factors"""
        try:
            risk_score = 0.2
            confidence = 0.5
            evidence = {}
            
            # Extract device information from user agent
            device_info = self._extract_device_info(user_agent)
            evidence.update(device_info)
            
            # Check for mobile vs desktop patterns
            if device_info.get("is_mobile"):
                evidence["device_type"] = "mobile"
                # Mobile devices might have slightly higher risk due to easier compromise
                risk_score += 0.1
            else:
                evidence["device_type"] = "desktop"
            
            # Check for outdated browsers/systems (security risk)
            if self._is_outdated_browser(user_agent):
                risk_score += 0.3
                evidence["outdated_browser"] = True
                confidence = 0.8
            
            # Check for headless browsers (automation risk)
            if self._is_headless_browser(user_agent):
                risk_score += 0.5
                evidence["headless_browser"] = True
                confidence = 0.9
            
            return RiskFactor(
                factor_type=RiskFactorType.DEVICE,
                factor_name="device_security_analysis",
                risk_score=min(1.0, risk_score),
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.DEVICE],
                evidence=evidence,
                source="heuristic",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze device risk: {str(e)}")
            return None
    
    async def _analyze_network_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze network-based risk factors"""
        try:
            risk_score = 0.1
            confidence = 0.6
            evidence = {"source_ip": ip_address}
            
            # Check for private IP ranges (generally lower risk)
            if self._is_private_ip(ip_address):
                risk_score = 0.1
                evidence["private_network"] = True
                confidence = 0.8
            
            # Check for Tor exit nodes (placeholder - would use real threat intel)
            if self._is_tor_exit_node(ip_address):
                risk_score = 0.9
                evidence["tor_exit_node"] = True
                confidence = 0.9
            
            # Check for VPN/proxy indicators (placeholder)
            if self._is_vpn_proxy(ip_address):
                risk_score = 0.5
                evidence["vpn_proxy_detected"] = True
                confidence = 0.7
            
            # Check for residential vs datacenter IP (placeholder)
            if self._is_datacenter_ip(ip_address):
                risk_score += 0.2
                evidence["datacenter_ip"] = True
                confidence = 0.7
            
            return RiskFactor(
                factor_type=RiskFactorType.NETWORK,
                factor_name="network_security_analysis",
                risk_score=min(1.0, risk_score),
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.NETWORK],
                evidence=evidence,
                source="threat_intelligence",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze network risk: {str(e)}")
            return None
    
    async def _analyze_historical_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze historical risk factors"""
        try:
            risk_score = 0.1
            confidence = 0.7
            evidence = {}
            
            if user_profile:
                # User's historical security violations
                violation_count = user_profile.security_violations_count
                evidence["violation_count"] = violation_count
                
                if violation_count > 10:
                    risk_score = 0.8
                    evidence["high_violation_history"] = True
                elif violation_count > 5:
                    risk_score = 0.5
                    evidence["moderate_violation_history"] = True
                elif violation_count > 0:
                    risk_score = 0.3
                    evidence["some_violation_history"] = True
                
                # User's baseline risk
                baseline_risk = user_profile.baseline_risk
                risk_score = max(risk_score, baseline_risk)
                evidence["baseline_risk"] = baseline_risk
                
                # Profile confidence affects our confidence
                confidence = min(confidence, user_profile.profile_confidence)
            
            # Check for historical issues with this IP (placeholder)
            ip_violation_count = await self._get_ip_violation_history(session, ip_address)
            evidence["ip_violation_count"] = ip_violation_count
            
            if ip_violation_count > 5:
                risk_score += 0.4
                evidence["high_ip_violation_history"] = True
            elif ip_violation_count > 0:
                risk_score += 0.2
                evidence["some_ip_violation_history"] = True
            
            return RiskFactor(
                factor_type=RiskFactorType.HISTORICAL,
                factor_name="historical_security_analysis",
                risk_score=min(1.0, risk_score),
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.HISTORICAL],
                evidence=evidence,
                source="user_history",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze historical risk: {str(e)}")
            return None
    
    async def _analyze_threat_intel_risk(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        user_profile: Optional[UserRiskProfile],
        additional_context: Dict[str, Any]
    ) -> Optional[RiskFactor]:
        """Analyze threat intelligence risk factors"""
        try:
            risk_score = 0.1
            confidence = 0.8  # High confidence in threat intel
            evidence = {}
            
            # Check against threat intelligence feeds (placeholder implementations)
            
            # Malicious IP check
            if await self._is_malicious_ip(ip_address):
                risk_score = 0.95
                evidence["malicious_ip"] = True
                confidence = 0.95
            
            # Botnet IP check
            elif await self._is_botnet_ip(ip_address):
                risk_score = 0.85
                evidence["botnet_ip"] = True
                confidence = 0.9
            
            # Known scanner IP check
            elif await self._is_scanner_ip(ip_address):
                risk_score = 0.7
                evidence["scanner_ip"] = True
                confidence = 0.8
            
            # Suspicious user agent patterns
            if await self._is_malicious_user_agent(user_agent):
                risk_score = max(risk_score, 0.8)
                evidence["malicious_user_agent"] = True
                confidence = 0.9
            
            # Reputation scoring
            ip_reputation = await self._get_ip_reputation_score(ip_address)
            if ip_reputation < 0.3:  # Low reputation
                risk_score = max(risk_score, 0.6)
                evidence["low_ip_reputation"] = ip_reputation
                confidence = 0.8
            
            evidence["threat_intel_checked"] = True
            
            return RiskFactor(
                factor_type=RiskFactorType.THREAT_INTEL,
                factor_name="threat_intelligence_analysis",
                risk_score=risk_score,
                confidence=confidence,
                weight=self.assessment_weights[RiskFactorType.THREAT_INTEL],
                evidence=evidence,
                source="threat_intelligence",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze threat intelligence risk: {str(e)}")
            return None
    
    # Utility Methods
    
    def _calculate_user_agent_similarity(self, ua1: str, ua2: str) -> float:
        """Calculate similarity between user agents"""
        if not ua1 or not ua2:
            return 0.0
        
        # Simple token-based similarity
        tokens1 = set(ua1.lower().split())
        tokens2 = set(ua2.lower().split())
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_device_info(self, user_agent: str) -> Dict[str, Any]:
        """Extract device information from user agent"""
        info = {
            "is_mobile": False,
            "browser": "unknown",
            "os": "unknown"
        }
        
        ua_lower = user_agent.lower()
        
        # Mobile detection
        mobile_indicators = ["mobile", "android", "iphone", "ipad", "tablet"]
        info["is_mobile"] = any(indicator in ua_lower for indicator in mobile_indicators)
        
        # Browser detection (simplified)
        if "chrome" in ua_lower:
            info["browser"] = "chrome"
        elif "firefox" in ua_lower:
            info["browser"] = "firefox"
        elif "safari" in ua_lower:
            info["browser"] = "safari"
        elif "edge" in ua_lower:
            info["browser"] = "edge"
        
        # OS detection (simplified)
        if "windows" in ua_lower:
            info["os"] = "windows"
        elif "macos" in ua_lower or "mac os" in ua_lower:
            info["os"] = "macos"
        elif "linux" in ua_lower:
            info["os"] = "linux"
        elif "android" in ua_lower:
            info["os"] = "android"
        elif "ios" in ua_lower:
            info["os"] = "ios"
        
        return info
    
    def _is_outdated_browser(self, user_agent: str) -> bool:
        """Check if browser appears to be outdated (placeholder)"""
        # This would implement real browser version checking
        outdated_indicators = ["ie 6", "ie 7", "ie 8", "chrome/50", "firefox/40"]
        return any(indicator in user_agent.lower() for indicator in outdated_indicators)
    
    def _is_headless_browser(self, user_agent: str) -> bool:
        """Check if browser appears to be headless"""
        headless_indicators = ["headless", "phantomjs", "puppeteer", "selenium"]
        return any(indicator in user_agent.lower() for indicator in headless_indicators)
    
    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP is in private range"""
        private_patterns = ["192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", 
                           "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                           "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                           "127.", "localhost"]
        return any(ip_address.startswith(pattern) for pattern in private_patterns)
    
    # Placeholder threat intelligence methods (would integrate with real services)
    
    def _is_tor_exit_node(self, ip_address: str) -> bool:
        """Check if IP is a known Tor exit node (placeholder)"""
        return False  # Would integrate with Tor exit list
    
    def _is_vpn_proxy(self, ip_address: str) -> bool:
        """Check if IP is a VPN/proxy (placeholder)"""
        return False  # Would integrate with VPN detection service
    
    def _is_datacenter_ip(self, ip_address: str) -> bool:
        """Check if IP is from a datacenter (placeholder)"""
        return False  # Would integrate with IP classification service
    
    async def _is_malicious_ip(self, ip_address: str) -> bool:
        """Check if IP is known malicious (placeholder)"""
        return False  # Would integrate with threat intelligence feeds
    
    async def _is_botnet_ip(self, ip_address: str) -> bool:
        """Check if IP is part of a botnet (placeholder)"""
        return False  # Would integrate with botnet tracking
    
    async def _is_scanner_ip(self, ip_address: str) -> bool:
        """Check if IP is known scanner (placeholder)"""
        return False  # Would integrate with scanner detection
    
    async def _is_malicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is known malicious (placeholder)"""
        return False  # Would integrate with user agent threat intel
    
    async def _get_ip_reputation_score(self, ip_address: str) -> float:
        """Get IP reputation score (placeholder)"""
        return 0.8  # Would integrate with reputation services
    
    async def _get_ip_violation_history(self, session: AsyncSession, ip_address: str) -> int:
        """Get historical violation count for IP (placeholder)"""
        return 0  # Would query security violations table
    
    # Additional methods for profile management and threshold adjustment
    
    async def _update_user_risk_profile(
        self,
        session: AsyncSession,
        profile: UserRiskProfile,
        risk_factors: List[RiskFactor],
        overall_risk_score: float
    ):
        """Update user risk profile based on current assessment"""
        try:
            # Update baseline risk with exponential moving average
            profile.baseline_risk = (
                profile.baseline_risk * (1 - self.learning_rate) +
                overall_risk_score * self.learning_rate
            )
            
            # Extract location and time patterns from current assessment
            for factor in risk_factors:
                if factor.factor_type == RiskFactorType.GEOGRAPHIC:
                    ip = factor.evidence.get("ip_address")
                    if ip and ip not in profile.typical_locations:
                        profile.typical_locations.append(ip)
                        # Keep only recent locations
                        profile.typical_locations = profile.typical_locations[-20:]
                
                elif factor.factor_type == RiskFactorType.TEMPORAL:
                    hour = factor.evidence.get("login_hour")
                    if hour is not None:
                        profile.typical_hours.append(hour)
                        # Keep only recent hours
                        profile.typical_hours = profile.typical_hours[-100:]
            
            # Update profile confidence
            profile.profile_confidence = min(1.0, profile.profile_confidence * 1.02)
            profile.last_updated = datetime.utcnow()
            
            # Cache updated profile
            cache = await self._get_cache()
            profile_key = self._generate_cache_key("user_profile", profile.user_id)
            await cache.set(profile_key, asdict(profile), ttl=self.profile_cache_ttl)
            
            self.user_profiles[profile.user_id] = profile
            
        except Exception as e:
            self.logger.error(f"Failed to update user risk profile: {str(e)}")
    
    async def _update_dynamic_thresholds(self, assessed_level: RiskLevel, risk_score: float):
        """Update dynamic thresholds based on assessment outcomes"""
        try:
            # This would implement machine learning-based threshold adjustment
            # For now, just log the assessment for future analysis
            self.logger.debug(f"Risk assessment: {assessed_level.value} ({risk_score:.3f})")
            
        except Exception as e:
            self.logger.error(f"Failed to update dynamic thresholds: {str(e)}")
    
    async def _log_high_risk_assessment(
        self,
        session: AsyncSession,
        assessment: RiskAssessment,
        risk_factors: List[RiskFactor],
        user_profile: Optional[UserRiskProfile]
    ):
        """Log detailed information for high-risk assessments"""
        try:
            detailed_evidence = {
                "assessment_id": assessment.assessment_id,
                "risk_score": assessment.overall_risk_score,
                "risk_level": assessment.risk_level.value,
                "risk_factors": [
                    {
                        "type": f.factor_type.value,
                        "name": f.factor_name,
                        "score": f.risk_score,
                        "confidence": f.confidence,
                        "evidence": f.evidence
                    }
                    for f in risk_factors
                ],
                "user_profile_available": user_profile is not None,
                "assessment_confidence": assessment.confidence
            }
            
            await security_audit_service.log_security_violation(
                session=session,
                violation_type="HIGH_RISK_AUTHENTICATION",
                severity=assessment.risk_level.value.upper(),
                violation_details=detailed_evidence,
                user_id=assessment.user_id,
                session_id=assessment.session_id,
                blocked=False  # Assessment doesn't block, just informs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log high-risk assessment: {str(e)}")
    
    async def _find_advanced_pattern_matches(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        ip_address: str,
        user_agent: str,
        risk_factors: List[RiskFactor]
    ) -> List[str]:
        """Find advanced pattern matches based on risk factors"""
        try:
            patterns = []
            
            # Analyze risk factor combinations for pattern detection
            high_risk_factors = [f for f in risk_factors if f.risk_score > 0.6]
            
            if len(high_risk_factors) >= 2:
                patterns.append("multiple_high_risk_factors")
            
            # Geographic + temporal anomaly pattern
            geographic_risk = next((f for f in risk_factors if f.factor_type == RiskFactorType.GEOGRAPHIC), None)
            temporal_risk = next((f for f in risk_factors if f.factor_type == RiskFactorType.TEMPORAL), None)
            
            if (geographic_risk and geographic_risk.risk_score > 0.5 and
                temporal_risk and temporal_risk.risk_score > 0.5):
                patterns.append("geographic_temporal_anomaly")
            
            # Frequency + device anomaly pattern
            frequency_risk = next((f for f in risk_factors if f.factor_type == RiskFactorType.FREQUENCY), None)
            device_risk = next((f for f in risk_factors if f.factor_type == RiskFactorType.DEVICE), None)
            
            if (frequency_risk and frequency_risk.risk_score > 0.6 and
                device_risk and device_risk.risk_score > 0.5):
                patterns.append("frequency_device_anomaly")
            
            # Threat intelligence pattern
            threat_risk = next((f for f in risk_factors if f.factor_type == RiskFactorType.THREAT_INTEL), None)
            if threat_risk and threat_risk.risk_score > 0.7:
                patterns.append("threat_intelligence_match")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to find pattern matches: {str(e)}")
            return []
    
    def _generate_adaptive_recommendations(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        risk_factors: List[RiskFactor],
        pattern_matches: List[str]
    ) -> List[str]:
        """Generate adaptive recommendations based on detailed risk analysis"""
        try:
            recommendations = []
            
            # Base recommendations by risk level
            if risk_level == RiskLevel.CRITICAL:
                recommendations.extend(["block_authentication", "immediate_security_review", "notify_security_team"])
            elif risk_level == RiskLevel.HIGH:
                recommendations.extend(["require_additional_authentication", "enhanced_monitoring", "security_review"])
            elif risk_level == RiskLevel.MEDIUM:
                recommendations.extend(["additional_validation", "increased_logging", "monitor_session"])
            else:
                recommendations.append("standard_monitoring")
            
            # Factor-specific recommendations
            for factor in risk_factors:
                if factor.risk_score > 0.7:
                    if factor.factor_type == RiskFactorType.GEOGRAPHIC:
                        recommendations.append("verify_location")
                    elif factor.factor_type == RiskFactorType.DEVICE:
                        recommendations.append("verify_device")
                    elif factor.factor_type == RiskFactorType.FREQUENCY:
                        recommendations.append("implement_rate_limiting")
                    elif factor.factor_type == RiskFactorType.THREAT_INTEL:
                        recommendations.append("block_immediately")
            
            # Pattern-specific recommendations
            if "multiple_high_risk_factors" in pattern_matches:
                recommendations.append("comprehensive_security_check")
            if "threat_intelligence_match" in pattern_matches:
                recommendations.append("investigate_threat_source")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec not in seen:
                    seen.add(rec)
                    unique_recommendations.append(rec)
            
            return unique_recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate adaptive recommendations: {str(e)}")
            return ["additional_monitoring", "manual_review"]


# Global service instance
auth_risk_assessment_service = AuthRiskAssessmentService()