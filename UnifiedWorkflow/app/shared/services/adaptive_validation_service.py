"""
Adaptive Validation Service

Implements a risk-based validation checkpoint system that dynamically adjusts
security requirements based on authentication patterns and risk assessments.

Features:
- Risk-based validation checkpoints
- Adaptive security controls
- Evidence-based bypass mechanisms
- Learning-based effectiveness tracking
- Non-invasive integration with existing auth flow
"""

import json
import time
import logging
import uuid
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_, func, desc

from shared.services.auth_pattern_detection_service import (
    AuthEvent, AuthEventType, RiskLevel, ValidationCheckpoint, 
    auth_pattern_detection_service
)
from shared.services.auth_risk_assessment_service import (
    RiskAssessment, auth_risk_assessment_service
)
from shared.services.security_audit_service import security_audit_service
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

class ValidationType(Enum):
    """Types of validation checkpoints"""
    ADDITIONAL_FACTOR = "additional_factor"
    CAPTCHA = "captcha"
    DELAYED_RESPONSE = "delayed_response"
    ENHANCED_MONITORING = "enhanced_monitoring"
    DEVICE_VERIFICATION = "device_verification"
    LOCATION_VERIFICATION = "location_verification"
    ADMIN_APPROVAL = "admin_approval"
    TEMPORARY_BLOCK = "temporary_block"
    PROGRESSIVE_DELAY = "progressive_delay"

class ValidationResult(Enum):
    """Results of validation checkpoint evaluation"""
    ALLOW = "allow"
    CHALLENGE = "challenge"
    BLOCK = "block"
    MONITOR = "monitor"
    BYPASS = "bypass"

@dataclass
class ValidationChallenge:
    """Validation challenge presented to user"""
    challenge_id: str
    challenge_type: ValidationType
    challenge_data: Dict[str, Any]
    difficulty_level: float  # 0.0 to 1.0
    max_attempts: int
    expires_at: datetime
    bypass_code: Optional[str]
    success_required: bool

@dataclass
class ValidationOutcome:
    """Result of validation checkpoint processing"""
    outcome_id: str
    checkpoint_id: str
    validation_result: ValidationResult
    challenge: Optional[ValidationChallenge]
    additional_data: Dict[str, Any]
    processing_time_ms: float
    reason: str
    confidence: float
    timestamp: datetime

@dataclass
class CheckpointEffectiveness:
    """Tracking effectiveness of validation checkpoints"""
    checkpoint_id: str
    total_triggers: int
    successful_blocks: int
    false_positives: int
    bypass_rate: float
    user_completion_rate: float
    average_completion_time: float
    effectiveness_score: float
    last_updated: datetime

class AdaptiveValidationService:
    """
    Adaptive Validation Service
    
    Provides risk-based validation checkpoints that adapt to security patterns
    and user behavior while maintaining usability.
    """
    
    def __init__(self):
        self.logger = logger
        self._cache = None
        
        # Validation configuration
        self.validation_configs = {
            ValidationType.ADDITIONAL_FACTOR: {
                "min_risk_score": 0.6,
                "max_attempts": 3,
                "timeout_minutes": 10,
                "difficulty_base": 0.7,
                "effectiveness_weight": 0.9
            },
            ValidationType.CAPTCHA: {
                "min_risk_score": 0.4,
                "max_attempts": 5,
                "timeout_minutes": 5,
                "difficulty_base": 0.5,
                "effectiveness_weight": 0.7
            },
            ValidationType.DELAYED_RESPONSE: {
                "min_risk_score": 0.3,
                "max_attempts": 1,
                "timeout_minutes": 0,
                "difficulty_base": 0.3,
                "effectiveness_weight": 0.6
            },
            ValidationType.DEVICE_VERIFICATION: {
                "min_risk_score": 0.7,
                "max_attempts": 2,
                "timeout_minutes": 15,
                "difficulty_base": 0.8,
                "effectiveness_weight": 0.9
            },
            ValidationType.LOCATION_VERIFICATION: {
                "min_risk_score": 0.6,
                "max_attempts": 3,
                "timeout_minutes": 10,
                "difficulty_base": 0.7,
                "effectiveness_weight": 0.8
            },
            ValidationType.ENHANCED_MONITORING: {
                "min_risk_score": 0.2,
                "max_attempts": 1,
                "timeout_minutes": 0,
                "difficulty_base": 0.1,
                "effectiveness_weight": 0.5
            },
            ValidationType.ADMIN_APPROVAL: {
                "min_risk_score": 0.9,
                "max_attempts": 1,
                "timeout_minutes": 120,
                "difficulty_base": 1.0,
                "effectiveness_weight": 1.0
            },
            ValidationType.TEMPORARY_BLOCK: {
                "min_risk_score": 0.95,
                "max_attempts": 0,
                "timeout_minutes": 60,
                "difficulty_base": 1.0,
                "effectiveness_weight": 1.0
            },
            ValidationType.PROGRESSIVE_DELAY: {
                "min_risk_score": 0.5,
                "max_attempts": 10,
                "timeout_minutes": 0,
                "difficulty_base": 0.4,
                "effectiveness_weight": 0.6
            }
        }
        
        # Active checkpoints and their effectiveness tracking
        self.active_checkpoints: Dict[str, ValidationCheckpoint] = {}
        self.checkpoint_effectiveness: Dict[str, CheckpointEffectiveness] = {}
        
        # Cache TTL configurations
        self.validation_cache_ttl = 300   # 5 minutes
        self.challenge_cache_ttl = 600    # 10 minutes
        self.effectiveness_cache_ttl = 1800  # 30 minutes
        
        # Learning parameters
        self.effectiveness_learning_rate = 0.1
        self.bypass_threshold = 0.8
        self.false_positive_threshold = 0.2
        
    async def _get_cache(self):
        """Get Redis cache instance with lazy initialization"""
        if not self._cache:
            self._cache = await get_redis_cache()
        return self._cache
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache keys for validation"""
        key_parts = [prefix] + [str(arg) for arg in args]
        base_key = ":adaptive_validation:".join(key_parts)
        
        if len(base_key) > 200:
            import hashlib
            key_hash = hashlib.md5(base_key.encode()).hexdigest()
            return f"adaptive_validation:{prefix}:hash:{key_hash}"
        
        return f"adaptive_validation:{base_key}"
    
    async def evaluate_validation_requirements(
        self,
        session: AsyncSession,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment
    ) -> ValidationOutcome:
        """
        Evaluate if validation checkpoint should be triggered and what type
        """
        try:
            evaluation_start = time.time()
            
            # Check if validation is required based on risk assessment
            validation_required, validation_type = await self._determine_validation_requirement(
                session, auth_event, risk_assessment
            )
            
            if not validation_required:
                return ValidationOutcome(
                    outcome_id=f"outcome_{int(time.time() * 1000)}",
                    checkpoint_id="none",
                    validation_result=ValidationResult.ALLOW,
                    challenge=None,
                    additional_data={"risk_score": risk_assessment.overall_risk_score},
                    processing_time_ms=(time.time() - evaluation_start) * 1000,
                    reason="Risk assessment below validation threshold",
                    confidence=risk_assessment.confidence,
                    timestamp=datetime.utcnow()
                )
            
            # Check for bypass conditions
            bypass_result = await self._check_bypass_conditions(
                session, auth_event, risk_assessment, validation_type
            )
            
            if bypass_result:
                return ValidationOutcome(
                    outcome_id=f"outcome_{int(time.time() * 1000)}",
                    checkpoint_id="bypassed",
                    validation_result=ValidationResult.BYPASS,
                    challenge=None,
                    additional_data={
                        "bypass_reason": bypass_result,
                        "risk_score": risk_assessment.overall_risk_score
                    },
                    processing_time_ms=(time.time() - evaluation_start) * 1000,
                    reason=f"Validation bypassed: {bypass_result}",
                    confidence=risk_assessment.confidence,
                    timestamp=datetime.utcnow()
                )
            
            # Create validation challenge
            challenge = await self._create_validation_challenge(
                session, auth_event, risk_assessment, validation_type
            )
            
            # Determine validation result
            if validation_type == ValidationType.TEMPORARY_BLOCK:
                validation_result = ValidationResult.BLOCK
            elif validation_type == ValidationType.ENHANCED_MONITORING:
                validation_result = ValidationResult.MONITOR
            else:
                validation_result = ValidationResult.CHALLENGE
            
            outcome = ValidationOutcome(
                outcome_id=f"outcome_{int(time.time() * 1000)}",
                checkpoint_id=challenge.challenge_id if challenge else "error",
                validation_result=validation_result,
                challenge=challenge,
                additional_data={
                    "validation_type": validation_type.value,
                    "risk_score": risk_assessment.overall_risk_score,
                    "risk_level": risk_assessment.risk_level.value
                },
                processing_time_ms=(time.time() - evaluation_start) * 1000,
                reason=f"Validation required: {validation_type.value}",
                confidence=risk_assessment.confidence,
                timestamp=datetime.utcnow()
            )
            
            # Log validation checkpoint trigger
            await self._log_validation_trigger(session, outcome, auth_event, risk_assessment)
            
            # Update checkpoint effectiveness tracking
            await self._update_checkpoint_effectiveness(validation_type, "trigger")
            
            processing_time = (time.time() - evaluation_start) * 1000
            self.logger.info(
                f"Validation evaluation completed in {processing_time:.1f}ms: "
                f"{validation_result.value} ({validation_type.value if validation_type else 'none'})"
            )
            
            return outcome
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate validation requirements: {str(e)}")
            
            # Return safe fallback outcome
            return ValidationOutcome(
                outcome_id=f"error_{int(time.time())}",
                checkpoint_id="error",
                validation_result=ValidationResult.MONITOR,
                challenge=None,
                additional_data={"error": str(e)},
                processing_time_ms=0.0,
                reason="Validation evaluation error",
                confidence=0.1,
                timestamp=datetime.utcnow()
            )
    
    async def _determine_validation_requirement(
        self,
        session: AsyncSession,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment
    ) -> Tuple[bool, Optional[ValidationType]]:
        """Determine if validation is required and what type"""
        try:
            risk_score = risk_assessment.overall_risk_score
            risk_level = risk_assessment.risk_level
            
            # Critical risk always requires strong validation
            if risk_level == RiskLevel.CRITICAL:
                if risk_score >= 0.95:
                    return True, ValidationType.TEMPORARY_BLOCK
                else:
                    return True, ValidationType.ADMIN_APPROVAL
            
            # High risk requires significant validation
            elif risk_level == RiskLevel.HIGH:
                # Check specific risk factors to determine validation type
                contributing_factors = risk_assessment.contributing_factors
                
                if contributing_factors.get("geographic_anomaly", 0) > 0.7:
                    return True, ValidationType.LOCATION_VERIFICATION
                elif contributing_factors.get("device_fingerprint_mismatch", 0) > 0.7:
                    return True, ValidationType.DEVICE_VERIFICATION
                elif contributing_factors.get("frequency_anomaly", 0) > 0.8:
                    return True, ValidationType.PROGRESSIVE_DELAY
                else:
                    return True, ValidationType.ADDITIONAL_FACTOR
            
            # Medium risk may require lighter validation
            elif risk_level == RiskLevel.MEDIUM:
                # Check for specific patterns
                if "rapid_attempts" in risk_assessment.pattern_matches:
                    return True, ValidationType.CAPTCHA
                elif risk_score > 0.5:
                    return True, ValidationType.DELAYED_RESPONSE
                else:
                    return True, ValidationType.ENHANCED_MONITORING
            
            # Low risk - enhanced monitoring only
            elif risk_level == RiskLevel.LOW and risk_score > 0.3:
                return True, ValidationType.ENHANCED_MONITORING
            
            # Minimal risk - no additional validation
            else:
                return False, None
                
        except Exception as e:
            self.logger.error(f"Failed to determine validation requirement: {str(e)}")
            return True, ValidationType.ENHANCED_MONITORING  # Safe fallback
    
    async def _check_bypass_conditions(
        self,
        session: AsyncSession,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment,
        validation_type: ValidationType
    ) -> Optional[str]:
        """Check if validation should be bypassed"""
        try:
            # Admin users can bypass some validations
            if auth_event.additional_data.get("user_role") == "admin":
                if validation_type in [ValidationType.CAPTCHA, ValidationType.DELAYED_RESPONSE]:
                    return "admin_user_bypass"
            
            # Trusted devices can bypass certain validations
            if auth_event.additional_data.get("device_trusted", False):
                if validation_type in [ValidationType.DEVICE_VERIFICATION, ValidationType.CAPTCHA]:
                    return "trusted_device_bypass"
            
            # Recent successful validation can bypass similar checks
            recent_validation = await self._get_recent_successful_validation(
                session, auth_event.user_id, validation_type
            )
            if recent_validation:
                return "recent_validation_bypass"
            
            # Emergency access codes
            emergency_code = auth_event.additional_data.get("emergency_access_code")
            if emergency_code and await self._validate_emergency_code(emergency_code):
                return "emergency_access_bypass"
            
            # High confidence in low risk assessment
            if (risk_assessment.confidence > 0.9 and 
                risk_assessment.overall_risk_score < 0.3 and
                validation_type == ValidationType.ENHANCED_MONITORING):
                return "high_confidence_low_risk_bypass"
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to check bypass conditions: {str(e)}")
            return None
    
    async def _create_validation_challenge(
        self,
        session: AsyncSession,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment,
        validation_type: ValidationType
    ) -> Optional[ValidationChallenge]:
        """Create appropriate validation challenge"""
        try:
            config = self.validation_configs.get(validation_type, {})
            challenge_id = f"challenge_{validation_type.value}_{int(time.time() * 1000)}"
            
            # Calculate difficulty based on risk score
            base_difficulty = config.get("difficulty_base", 0.5)
            risk_adjustment = risk_assessment.overall_risk_score * 0.3
            difficulty_level = min(1.0, base_difficulty + risk_adjustment)
            
            # Create challenge data based on type
            challenge_data = await self._generate_challenge_data(
                validation_type, difficulty_level, auth_event, risk_assessment
            )
            
            # Set expiration time
            timeout_minutes = config.get("timeout_minutes", 10)
            expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            
            # Generate bypass code for admin emergencies
            bypass_code = None
            if validation_type in [ValidationType.ADMIN_APPROVAL, ValidationType.TEMPORARY_BLOCK]:
                bypass_code = self._generate_bypass_code()
            
            challenge = ValidationChallenge(
                challenge_id=challenge_id,
                challenge_type=validation_type,
                challenge_data=challenge_data,
                difficulty_level=difficulty_level,
                max_attempts=config.get("max_attempts", 3),
                expires_at=expires_at,
                bypass_code=bypass_code,
                success_required=validation_type != ValidationType.ENHANCED_MONITORING
            )
            
            # Cache challenge for later validation
            cache = await self._get_cache()
            challenge_key = self._generate_cache_key("challenge", challenge_id)
            await cache.set(challenge_key, asdict(challenge), ttl=self.challenge_cache_ttl)
            
            self.logger.info(f"Created validation challenge: {validation_type.value} (difficulty: {difficulty_level:.2f})")
            return challenge
            
        except Exception as e:
            self.logger.error(f"Failed to create validation challenge: {str(e)}")
            return None
    
    async def _generate_challenge_data(
        self,
        validation_type: ValidationType,
        difficulty_level: float,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment
    ) -> Dict[str, Any]:
        """Generate specific challenge data based on validation type"""
        try:
            challenge_data = {
                "type": validation_type.value,
                "difficulty": difficulty_level,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if validation_type == ValidationType.ADDITIONAL_FACTOR:
                challenge_data.update({
                    "factor_type": "totp",  # Time-based One-Time Password
                    "instructions": "Please enter your authentication code from your mobile app",
                    "code_length": 6,
                    "time_window": 30
                })
                
            elif validation_type == ValidationType.CAPTCHA:
                # CAPTCHA difficulty based on risk
                captcha_complexity = "simple" if difficulty_level < 0.5 else "complex"
                challenge_data.update({
                    "captcha_type": "image_recognition",
                    "complexity": captcha_complexity,
                    "instructions": "Please complete the CAPTCHA to verify you are human",
                    "image_count": 3 if captcha_complexity == "simple" else 6
                })
                
            elif validation_type == ValidationType.DELAYED_RESPONSE:
                # Delay time based on risk and difficulty
                delay_seconds = max(5, int(difficulty_level * 30))
                challenge_data.update({
                    "delay_seconds": delay_seconds,
                    "instructions": f"Please wait {delay_seconds} seconds before proceeding",
                    "reason": "Security verification in progress"
                })
                
            elif validation_type == ValidationType.DEVICE_VERIFICATION:
                challenge_data.update({
                    "verification_method": "email_link",
                    "instructions": "Please check your email and click the verification link",
                    "email_hint": self._get_email_hint(auth_event),
                    "alternative_methods": ["sms_code", "security_questions"]
                })
                
            elif validation_type == ValidationType.LOCATION_VERIFICATION:
                challenge_data.update({
                    "verification_method": "location_confirmation",
                    "instructions": "Please confirm your current location",
                    "detected_location": self._get_location_hint(auth_event.ip_address),
                    "alternative_methods": ["trusted_contact_verification"]
                })
                
            elif validation_type == ValidationType.ENHANCED_MONITORING:
                challenge_data.update({
                    "monitoring_level": "enhanced",
                    "duration_minutes": 60,
                    "restrictions": ["limited_access", "additional_logging"],
                    "instructions": "Your session will be monitored for security purposes"
                })
                
            elif validation_type == ValidationType.ADMIN_APPROVAL:
                challenge_data.update({
                    "approval_required": True,
                    "escalation_level": "security_team",
                    "instructions": "This login requires administrator approval",
                    "contact_info": "security@company.com",
                    "ticket_id": f"SEC-{int(time.time())}"
                })
                
            elif validation_type == ValidationType.TEMPORARY_BLOCK:
                block_duration = max(60, int(difficulty_level * 300))  # 1-5 minutes
                challenge_data.update({
                    "block_duration_seconds": block_duration,
                    "reason": "Suspicious activity detected",
                    "instructions": f"Access temporarily blocked for {block_duration // 60} minutes",
                    "appeal_process": "contact_security_team"
                })
                
            elif validation_type == ValidationType.PROGRESSIVE_DELAY:
                # Get previous attempt count
                attempt_count = await self._get_recent_attempt_count(auth_event.ip_address)
                delay_seconds = min(300, 2 ** attempt_count)  # Exponential backoff, max 5 minutes
                
                challenge_data.update({
                    "delay_seconds": delay_seconds,
                    "attempt_count": attempt_count,
                    "instructions": f"Too many attempts. Please wait {delay_seconds} seconds",
                    "next_attempt_allowed": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
                })
            
            return challenge_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate challenge data: {str(e)}")
            return {"error": "Failed to generate challenge"}
    
    async def validate_challenge_response(
        self,
        session: AsyncSession,
        challenge_id: str,
        response_data: Dict[str, Any],
        auth_event: AuthEvent
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate user response to challenge"""
        try:
            # Retrieve challenge from cache
            cache = await self._get_cache()
            challenge_key = self._generate_cache_key("challenge", challenge_id)
            challenge_data = await cache.get(challenge_key)
            
            if not challenge_data:
                return False, {"error": "Challenge not found or expired"}
            
            challenge = ValidationChallenge(**challenge_data)
            
            # Check if challenge has expired
            if datetime.utcnow() > challenge.expires_at:
                return False, {"error": "Challenge expired"}
            
            # Validate response based on challenge type
            validation_result, validation_details = await self._validate_specific_challenge(
                challenge, response_data, auth_event
            )
            
            # Update challenge attempt count
            attempt_count = response_data.get("attempt_count", 1)
            if not validation_result and attempt_count >= challenge.max_attempts:
                # Max attempts reached, block further attempts
                await self._handle_challenge_failure(session, challenge, auth_event)
                return False, {"error": "Maximum attempts exceeded", "blocked": True}
            
            # Update effectiveness tracking
            if validation_result:
                await self._update_checkpoint_effectiveness(challenge.challenge_type, "success")
            else:
                await self._update_checkpoint_effectiveness(challenge.challenge_type, "failure")
            
            # Log validation outcome
            await self._log_challenge_outcome(
                session, challenge, validation_result, validation_details, auth_event
            )
            
            return validation_result, validation_details
            
        except Exception as e:
            self.logger.error(f"Failed to validate challenge response: {str(e)}")
            return False, {"error": "Validation error"}
    
    async def _validate_specific_challenge(
        self,
        challenge: ValidationChallenge,
        response_data: Dict[str, Any],
        auth_event: AuthEvent
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate specific challenge type"""
        try:
            challenge_type = challenge.challenge_type
            
            if challenge_type == ValidationType.ADDITIONAL_FACTOR:
                # Validate TOTP code (placeholder implementation)
                provided_code = response_data.get("totp_code", "")
                expected_code = "123456"  # Would integrate with TOTP library
                
                if provided_code == expected_code:
                    return True, {"factor_validated": True, "method": "totp"}
                else:
                    return False, {"error": "Invalid authentication code"}
                    
            elif challenge_type == ValidationType.CAPTCHA:
                # Validate CAPTCHA response (placeholder implementation)
                captcha_response = response_data.get("captcha_response", "")
                captcha_solution = challenge.challenge_data.get("solution", "correct")
                
                if captcha_response.lower() == captcha_solution.lower():
                    return True, {"captcha_validated": True}
                else:
                    return False, {"error": "Incorrect CAPTCHA response"}
                    
            elif challenge_type == ValidationType.DELAYED_RESPONSE:
                # Check if enough time has passed
                challenge_time = datetime.fromisoformat(challenge.challenge_data["timestamp"])
                required_delay = challenge.challenge_data["delay_seconds"]
                elapsed_time = (datetime.utcnow() - challenge_time).total_seconds()
                
                if elapsed_time >= required_delay:
                    return True, {"delay_satisfied": True, "elapsed_time": elapsed_time}
                else:
                    remaining_time = required_delay - elapsed_time
                    return False, {"error": f"Please wait {remaining_time:.0f} more seconds"}
                    
            elif challenge_type == ValidationType.DEVICE_VERIFICATION:
                # Validate device verification token (placeholder)
                verification_token = response_data.get("verification_token", "")
                if verification_token:  # Would validate with real token system
                    return True, {"device_verified": True, "token": verification_token}
                else:
                    return False, {"error": "Invalid verification token"}
                    
            elif challenge_type == ValidationType.LOCATION_VERIFICATION:
                # Validate location confirmation
                location_confirmed = response_data.get("location_confirmed", False)
                if location_confirmed:
                    return True, {"location_verified": True}
                else:
                    return False, {"error": "Location not confirmed"}
                    
            elif challenge_type == ValidationType.ENHANCED_MONITORING:
                # Enhanced monitoring always "succeeds" but applies restrictions
                return True, {"monitoring_applied": True, "restrictions": challenge.challenge_data.get("restrictions", [])}
                
            elif challenge_type == ValidationType.ADMIN_APPROVAL:
                # Check for admin approval or bypass code
                approval_code = response_data.get("approval_code", "")
                bypass_code = response_data.get("bypass_code", "")
                
                if bypass_code == challenge.bypass_code:
                    return True, {"approved": True, "method": "bypass_code"}
                elif approval_code:  # Would validate with admin approval system
                    return True, {"approved": True, "method": "admin_approval"}
                else:
                    return False, {"error": "Admin approval required"}
                    
            elif challenge_type == ValidationType.TEMPORARY_BLOCK:
                # Check if block period has expired
                challenge_time = datetime.fromisoformat(challenge.challenge_data["timestamp"])
                block_duration = challenge.challenge_data["block_duration_seconds"]
                elapsed_time = (datetime.utcnow() - challenge_time).total_seconds()
                
                if elapsed_time >= block_duration:
                    return True, {"block_expired": True, "elapsed_time": elapsed_time}
                else:
                    remaining_time = block_duration - elapsed_time
                    return False, {"error": f"Still blocked for {remaining_time:.0f} seconds"}
                    
            elif challenge_type == ValidationType.PROGRESSIVE_DELAY:
                # Similar to delayed response but with exponential backoff
                challenge_time = datetime.fromisoformat(challenge.challenge_data["timestamp"])
                required_delay = challenge.challenge_data["delay_seconds"]
                elapsed_time = (datetime.utcnow() - challenge_time).total_seconds()
                
                if elapsed_time >= required_delay:
                    return True, {"delay_satisfied": True, "attempt_count": challenge.challenge_data["attempt_count"]}
                else:
                    remaining_time = required_delay - elapsed_time
                    return False, {"error": f"Progressive delay: wait {remaining_time:.0f} more seconds"}
            
            # Unknown challenge type
            return False, {"error": "Unknown challenge type"}
            
        except Exception as e:
            self.logger.error(f"Failed to validate specific challenge: {str(e)}")
            return False, {"error": "Challenge validation error"}
    
    # Utility and Helper Methods
    
    def _generate_bypass_code(self) -> str:
        """Generate secure bypass code for emergency access"""
        return str(uuid.uuid4())[:8].upper()
    
    def _get_email_hint(self, auth_event: AuthEvent) -> str:
        """Get email hint for user (placeholder)"""
        # Would extract from user data
        return "user@example.com"
    
    def _get_location_hint(self, ip_address: str) -> str:
        """Get location hint from IP address (placeholder)"""
        # Would use GeoIP service
        return "Unknown Location"
    
    async def _get_recent_attempt_count(self, ip_address: str) -> int:
        """Get recent attempt count for progressive delay"""
        try:
            cache = await self._get_cache()
            attempt_key = self._generate_cache_key("attempt_count", ip_address)
            
            current_count = await cache.get(attempt_key) or 0
            new_count = current_count + 1
            
            # Store with exponential TTL
            ttl = min(3600, 60 * (2 ** new_count))  # Max 1 hour
            await cache.set(attempt_key, new_count, ttl=ttl)
            
            return current_count
            
        except Exception as e:
            self.logger.error(f"Failed to get recent attempt count: {str(e)}")
            return 0
    
    async def _get_recent_successful_validation(
        self,
        session: AsyncSession,
        user_id: Optional[int],
        validation_type: ValidationType
    ) -> bool:
        """Check if user has recently completed similar validation"""
        try:
            if not user_id:
                return False
            
            cache = await self._get_cache()
            validation_key = self._generate_cache_key("recent_validation", user_id, validation_type.value)
            
            recent_validation = await cache.get(validation_key)
            return recent_validation is not None
            
        except Exception as e:
            self.logger.error(f"Failed to check recent validation: {str(e)}")
            return False
    
    async def _validate_emergency_code(self, emergency_code: str) -> bool:
        """Validate emergency access code (placeholder)"""
        # Would integrate with emergency access system
        return emergency_code == "EMERGENCY_2024"
    
    async def _update_checkpoint_effectiveness(
        self,
        validation_type: ValidationType,
        outcome: str  # "trigger", "success", "failure", "bypass"
    ):
        """Update checkpoint effectiveness tracking"""
        try:
            checkpoint_id = f"checkpoint_{validation_type.value}"
            
            if checkpoint_id not in self.checkpoint_effectiveness:
                self.checkpoint_effectiveness[checkpoint_id] = CheckpointEffectiveness(
                    checkpoint_id=checkpoint_id,
                    total_triggers=0,
                    successful_blocks=0,
                    false_positives=0,
                    bypass_rate=0.0,
                    user_completion_rate=0.0,
                    average_completion_time=0.0,
                    effectiveness_score=0.0,
                    last_updated=datetime.utcnow()
                )
            
            effectiveness = self.checkpoint_effectiveness[checkpoint_id]
            
            if outcome == "trigger":
                effectiveness.total_triggers += 1
            elif outcome == "success":
                effectiveness.successful_blocks += 1
            elif outcome == "bypass":
                effectiveness.bypass_rate = (
                    effectiveness.bypass_rate * 0.9 + 0.1  # Exponential moving average
                )
            
            # Recalculate effectiveness score
            if effectiveness.total_triggers > 0:
                success_rate = effectiveness.successful_blocks / effectiveness.total_triggers
                effectiveness.effectiveness_score = (
                    success_rate * (1 - effectiveness.bypass_rate) * 
                    (1 - effectiveness.false_positives / max(1, effectiveness.total_triggers))
                )
            
            effectiveness.last_updated = datetime.utcnow()
            
            # Cache updated effectiveness
            cache = await self._get_cache()
            effectiveness_key = self._generate_cache_key("effectiveness", checkpoint_id)
            await cache.set(effectiveness_key, asdict(effectiveness), ttl=self.effectiveness_cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Failed to update checkpoint effectiveness: {str(e)}")
    
    async def _handle_challenge_failure(
        self,
        session: AsyncSession,
        challenge: ValidationChallenge,
        auth_event: AuthEvent
    ):
        """Handle challenge failure (max attempts exceeded)"""
        try:
            # Log security violation
            await security_audit_service.log_security_violation(
                session=session,
                violation_type="CHALLENGE_MAX_ATTEMPTS",
                severity="HIGH",
                violation_details={
                    "challenge_id": challenge.challenge_id,
                    "challenge_type": challenge.challenge_type.value,
                    "max_attempts": challenge.max_attempts
                },
                user_id=auth_event.user_id,
                session_id=auth_event.session_id,
                ip_address=auth_event.ip_address,
                user_agent=auth_event.user_agent,
                blocked=True
            )
            
            # Temporarily block the IP/user
            cache = await self._get_cache()
            block_key = self._generate_cache_key("blocked", auth_event.ip_address)
            await cache.set(block_key, {
                "reason": "max_challenge_attempts",
                "challenge_type": challenge.challenge_type.value,
                "blocked_at": datetime.utcnow().isoformat()
            }, ttl=1800)  # 30-minute block
            
        except Exception as e:
            self.logger.error(f"Failed to handle challenge failure: {str(e)}")
    
    async def _log_validation_trigger(
        self,
        session: AsyncSession,
        outcome: ValidationOutcome,
        auth_event: AuthEvent,
        risk_assessment: RiskAssessment
    ):
        """Log validation checkpoint trigger"""
        try:
            await security_audit_service.log_security_action(
                session=session,
                action_type="VALIDATION_CHECKPOINT_TRIGGER",
                target=outcome.checkpoint_id,
                reason=outcome.reason,
                evidence={
                    "validation_result": outcome.validation_result.value,
                    "risk_score": risk_assessment.overall_risk_score,
                    "risk_level": risk_assessment.risk_level.value,
                    "processing_time_ms": outcome.processing_time_ms,
                    "confidence": outcome.confidence
                },
                severity="MEDIUM",
                user_id=auth_event.user_id,
                session_id=auth_event.session_id,
                auto_created=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log validation trigger: {str(e)}")
    
    async def _log_challenge_outcome(
        self,
        session: AsyncSession,
        challenge: ValidationChallenge,
        success: bool,
        details: Dict[str, Any],
        auth_event: AuthEvent
    ):
        """Log challenge validation outcome"""
        try:
            await security_audit_service.log_security_action(
                session=session,
                action_type="CHALLENGE_VALIDATION",
                target=challenge.challenge_id,
                reason=f"Challenge {'completed' if success else 'failed'}",
                evidence={
                    "challenge_type": challenge.challenge_type.value,
                    "success": success,
                    "difficulty_level": challenge.difficulty_level,
                    "validation_details": details
                },
                severity="LOW" if success else "MEDIUM",
                user_id=auth_event.user_id,
                session_id=auth_event.session_id,
                auto_created=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log challenge outcome: {str(e)}")
    
    async def get_checkpoint_effectiveness_summary(self) -> Dict[str, Any]:
        """Get summary of checkpoint effectiveness"""
        try:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_checkpoints": len(self.checkpoint_effectiveness),
                "checkpoints": []
            }
            
            for checkpoint_id, effectiveness in self.checkpoint_effectiveness.items():
                checkpoint_summary = {
                    "checkpoint_id": checkpoint_id,
                    "total_triggers": effectiveness.total_triggers,
                    "success_rate": (effectiveness.successful_blocks / max(1, effectiveness.total_triggers)),
                    "bypass_rate": effectiveness.bypass_rate,
                    "effectiveness_score": effectiveness.effectiveness_score,
                    "last_updated": effectiveness.last_updated.isoformat()
                }
                summary["checkpoints"].append(checkpoint_summary)
            
            # Sort by effectiveness score
            summary["checkpoints"].sort(key=lambda x: x["effectiveness_score"], reverse=True)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get effectiveness summary: {str(e)}")
            return {"error": "Failed to generate summary"}


# Global service instance
adaptive_validation_service = AdaptiveValidationService()