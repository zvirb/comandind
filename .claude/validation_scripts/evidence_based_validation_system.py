#!/usr/bin/env python3
"""
Evidence-Based Validation Proof System

Implements comprehensive evidence collection and validation proof management
to prevent false positive validation claims. Every validation assertion must
be backed by concrete, verifiable evidence.

This system addresses the critical orchestration failure where validation
claimed 100% success while HTTP 500 errors were actively occurring.
"""

import asyncio
import json
import logging
import time
import traceback
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvidenceType(Enum):
    """Types of evidence that can be collected."""
    HTTP_RESPONSE = "http_response"
    DATABASE_QUERY = "database_query"
    LOG_ENTRY = "log_entry"
    METRIC_VALUE = "metric_value"
    SCREENSHOT = "screenshot"
    FILE_CONTENT = "file_content"
    SYSTEM_STATE = "system_state"
    PERFORMANCE_MEASUREMENT = "performance_measurement"
    ERROR_TRACE = "error_trace"
    VALIDATION_PROOF = "validation_proof"

class EvidenceQuality(Enum):
    """Quality levels of evidence."""
    HIGH = "high"          # Direct, concrete evidence
    MEDIUM = "medium"      # Indirect but reliable evidence  
    LOW = "low"           # Circumstantial evidence
    INSUFFICIENT = "insufficient"  # Cannot support claims

class ValidationClaim(Enum):
    """Types of validation claims that require evidence."""
    SYSTEM_HEALTHY = "system_healthy"
    ENDPOINT_ACCESSIBLE = "endpoint_accessible"
    AUTHENTICATION_WORKING = "authentication_working"
    DATABASE_CONNECTED = "database_connected"
    SCHEMA_VALID = "schema_valid"
    PERFORMANCE_ACCEPTABLE = "performance_acceptable"
    ERROR_COUNT_REDUCED = "error_count_reduced"
    USER_WORKFLOW_FUNCTIONAL = "user_workflow_functional"

@dataclass
class Evidence:
    """Single piece of evidence supporting a validation claim."""
    evidence_id: str
    evidence_type: EvidenceType
    claim_supporting: ValidationClaim
    timestamp: str
    data: Dict[str, Any]
    quality: EvidenceQuality
    confidence_score: float  # 0.0-1.0
    source_system: str
    validation_context: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.evidence_id:
            self.evidence_id = f"evidence_{uuid.uuid4().hex[:8]}"

@dataclass
class ValidationAssertion:
    """A validation claim with supporting evidence."""
    assertion_id: str
    claim: ValidationClaim
    claim_description: str
    asserted_value: Any
    evidence_required_minimum: int  # Minimum pieces of evidence needed
    evidence_collected: List[Evidence]
    assertion_valid: bool
    confidence_score: float  # Aggregate confidence from evidence
    timestamp: str
    validation_context: str
    failure_reasons: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.assertion_id:
            self.assertion_id = f"assertion_{uuid.uuid4().hex[:8]}"

@dataclass
class EvidenceValidationReport:
    """Comprehensive evidence validation report."""
    validation_id: str
    timestamp: str
    total_assertions: int
    assertions_validated: int
    assertions_failed: int
    total_evidence_collected: int
    evidence_quality_distribution: Dict[str, int]
    assertion_results: List[ValidationAssertion]
    critical_evidence_gaps: List[str]
    false_positive_risks: List[str]
    recommendations: List[str]
    overall_validation_confidence: float
    execution_time_ms: float

class EvidenceBasedValidationSystem:
    """
    Comprehensive evidence-based validation system that prevents false positives
    by requiring concrete proof for all validation claims.
    
    Key Principles:
    1. Every validation claim must have supporting evidence
    2. Evidence quality determines claim confidence
    3. Insufficient evidence invalidates claims
    4. Multiple evidence sources increase confidence
    5. Evidence contradictions trigger investigation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validation_id = f"evidence_validation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.evidence_storage_path = Path(config.get('evidence_path', '.claude/logs/evidence_proofs'))
        self.evidence_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Evidence requirements for each claim type
        self.evidence_requirements = {
            ValidationClaim.SYSTEM_HEALTHY: {
                'minimum_evidence': 3,
                'required_types': [EvidenceType.HTTP_RESPONSE, EvidenceType.METRIC_VALUE, EvidenceType.LOG_ENTRY],
                'minimum_confidence': 0.8
            },
            ValidationClaim.ENDPOINT_ACCESSIBLE: {
                'minimum_evidence': 2,
                'required_types': [EvidenceType.HTTP_RESPONSE],
                'minimum_confidence': 0.9
            },
            ValidationClaim.AUTHENTICATION_WORKING: {
                'minimum_evidence': 2,
                'required_types': [EvidenceType.HTTP_RESPONSE, EvidenceType.LOG_ENTRY],
                'minimum_confidence': 0.85
            },
            ValidationClaim.DATABASE_CONNECTED: {
                'minimum_evidence': 2, 
                'required_types': [EvidenceType.DATABASE_QUERY, EvidenceType.PERFORMANCE_MEASUREMENT],
                'minimum_confidence': 0.9
            },
            ValidationClaim.SCHEMA_VALID: {
                'minimum_evidence': 1,
                'required_types': [EvidenceType.DATABASE_QUERY],
                'minimum_confidence': 0.95
            },
            ValidationClaim.PERFORMANCE_ACCEPTABLE: {
                'minimum_evidence': 3,
                'required_types': [EvidenceType.PERFORMANCE_MEASUREMENT, EvidenceType.METRIC_VALUE],
                'minimum_confidence': 0.7
            },
            ValidationClaim.ERROR_COUNT_REDUCED: {
                'minimum_evidence': 2,
                'required_types': [EvidenceType.METRIC_VALUE, EvidenceType.LOG_ENTRY],
                'minimum_confidence': 0.8
            },
            ValidationClaim.USER_WORKFLOW_FUNCTIONAL: {
                'minimum_evidence': 3,
                'required_types': [EvidenceType.SCREENSHOT, EvidenceType.HTTP_RESPONSE, EvidenceType.SYSTEM_STATE],
                'minimum_confidence': 0.8
            }
        }
        
        self.evidence_database: List[Evidence] = []
        self.assertions: List[ValidationAssertion] = []

    async def validate_with_evidence(self, validation_data: Dict[str, Any]) -> EvidenceValidationReport:
        """
        Execute evidence-based validation for given validation data.
        
        Args:
            validation_data: Dictionary containing validation results and claims
            
        Returns:
            Comprehensive evidence validation report
        """
        start_time = time.time()
        logger.info(f"🔍 Starting evidence-based validation - ID: {self.validation_id}")
        
        # Extract validation claims from data
        claims = await self._extract_validation_claims(validation_data)
        
        # Process each claim
        for claim_info in claims:
            await self._process_validation_claim(claim_info)
        
        # Analyze evidence quality and completeness
        evidence_analysis = await self._analyze_evidence_quality()
        
        # Detect false positive risks
        false_positive_risks = await self._detect_false_positive_risks()
        
        # Generate recommendations
        recommendations = self._generate_evidence_recommendations()
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate summary statistics
        assertions_validated = sum(1 for assertion in self.assertions if assertion.assertion_valid)
        assertions_failed = len(self.assertions) - assertions_validated
        
        quality_distribution = {}
        for evidence in self.evidence_database:
            quality_key = evidence.quality.value
            quality_distribution[quality_key] = quality_distribution.get(quality_key, 0) + 1
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence()
        
        logger.info(f"✅ Evidence validation complete - Overall confidence: {overall_confidence:.2f}")
        
        return EvidenceValidationReport(
            validation_id=self.validation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_assertions=len(self.assertions),
            assertions_validated=assertions_validated,
            assertions_failed=assertions_failed,
            total_evidence_collected=len(self.evidence_database),
            evidence_quality_distribution=quality_distribution,
            assertion_results=self.assertions.copy(),
            critical_evidence_gaps=evidence_analysis.get('critical_gaps', []),
            false_positive_risks=false_positive_risks,
            recommendations=recommendations,
            overall_validation_confidence=overall_confidence,
            execution_time_ms=execution_time
        )

    async def _extract_validation_claims(self, validation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract validation claims from validation data."""
        claims = []
        
        # Extract claims from orchestration results
        if 'overall_assessment' in validation_data:
            assessment = validation_data['overall_assessment']
            if assessment.get('success') or assessment.get('status') == 'healthy':
                claims.append({
                    'claim': ValidationClaim.SYSTEM_HEALTHY,
                    'description': 'System reported as healthy/successful',
                    'asserted_value': True,
                    'context': 'orchestration_assessment',
                    'source_data': assessment
                })
        
        # Extract endpoint accessibility claims
        if 'critical_endpoint_validation' in validation_data:
            endpoint_results = validation_data['critical_endpoint_validation'].get('results', {})
            for endpoint_name, result in endpoint_results.items():
                if result.get('healthy', False):
                    claims.append({
                        'claim': ValidationClaim.ENDPOINT_ACCESSIBLE,
                        'description': f'Endpoint {endpoint_name} reported as healthy',
                        'asserted_value': True,
                        'context': f'endpoint_validation_{endpoint_name}',
                        'source_data': result
                    })
                    
                    # Also check authentication if status was not 401/403
                    if result.get('status_code', 500) not in [401, 403]:
                        claims.append({
                            'claim': ValidationClaim.AUTHENTICATION_WORKING,
                            'description': f'Authentication working for {endpoint_name}',
                            'asserted_value': True,
                            'context': f'auth_validation_{endpoint_name}',
                            'source_data': result
                        })
        
        # Extract database claims
        if 'database_validation' in validation_data:
            db_results = validation_data['database_validation']
            if db_results.get('connection_successful', False):
                claims.append({
                    'claim': ValidationClaim.DATABASE_CONNECTED,
                    'description': 'Database connection reported as successful',
                    'asserted_value': True,
                    'context': 'database_connection',
                    'source_data': db_results
                })
        
        # Extract error count claims
        if 'error_analysis' in validation_data:
            error_data = validation_data['error_analysis']
            if error_data.get('error_count_reduced', False):
                claims.append({
                    'claim': ValidationClaim.ERROR_COUNT_REDUCED,
                    'description': 'Error count reported as reduced',
                    'asserted_value': True,
                    'context': 'error_analysis',
                    'source_data': error_data
                })
        
        logger.info(f"📋 Extracted {len(claims)} validation claims for evidence verification")
        return claims

    async def _process_validation_claim(self, claim_info: Dict[str, Any]):
        """Process a single validation claim by collecting and analyzing evidence."""
        claim = claim_info['claim']
        
        logger.info(f"🔍 Processing claim: {claim.value}")
        
        # Create assertion
        assertion = ValidationAssertion(
            assertion_id="",  # Will be auto-generated
            claim=claim,
            claim_description=claim_info['description'],
            asserted_value=claim_info['asserted_value'],
            evidence_required_minimum=self.evidence_requirements[claim]['minimum_evidence'],
            evidence_collected=[],
            assertion_valid=False,
            confidence_score=0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            validation_context=claim_info['context']
        )
        
        # Collect evidence for this claim
        evidence_collected = await self._collect_evidence_for_claim(claim, claim_info)
        assertion.evidence_collected = evidence_collected
        
        # Add to evidence database
        self.evidence_database.extend(evidence_collected)
        
        # Validate the assertion
        await self._validate_assertion(assertion)
        
        # Store the assertion
        self.assertions.append(assertion)

    async def _collect_evidence_for_claim(self, claim: ValidationClaim, 
                                        claim_info: Dict[str, Any]) -> List[Evidence]:
        """Collect evidence to support a validation claim."""
        evidence_list = []
        source_data = claim_info.get('source_data', {})
        context = claim_info['context']
        
        if claim == ValidationClaim.SYSTEM_HEALTHY:
            evidence_list.extend(await self._collect_system_health_evidence(source_data, context))
            
        elif claim == ValidationClaim.ENDPOINT_ACCESSIBLE:
            evidence_list.extend(await self._collect_endpoint_evidence(source_data, context))
            
        elif claim == ValidationClaim.AUTHENTICATION_WORKING:
            evidence_list.extend(await self._collect_authentication_evidence(source_data, context))
            
        elif claim == ValidationClaim.DATABASE_CONNECTED:
            evidence_list.extend(await self._collect_database_evidence(source_data, context))
            
        elif claim == ValidationClaim.ERROR_COUNT_REDUCED:
            evidence_list.extend(await self._collect_error_count_evidence(source_data, context))
        
        logger.info(f"📊 Collected {len(evidence_list)} pieces of evidence for {claim.value}")
        return evidence_list

    async def _collect_system_health_evidence(self, source_data: Dict[str, Any], 
                                            context: str) -> List[Evidence]:
        """Collect evidence for system health claims."""
        evidence = []
        
        # Check for HTTP response evidence
        if 'endpoints_tested' in source_data:
            evidence.append(Evidence(
                evidence_id="",  # Auto-generated
                evidence_type=EvidenceType.HTTP_RESPONSE,
                claim_supporting=ValidationClaim.SYSTEM_HEALTHY,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "endpoints_tested": source_data.get('endpoints_tested', 0),
                    "healthy_endpoints": source_data.get('healthy_endpoints', 0),
                    "failing_endpoints": source_data.get('failing_endpoints', 0)
                },
                quality=EvidenceQuality.HIGH if source_data.get('failing_endpoints', 0) == 0 else EvidenceQuality.LOW,
                confidence_score=0.9 if source_data.get('failing_endpoints', 0) == 0 else 0.1,
                source_system="orchestration_validator",
                validation_context=context
            ))
        
        # Check actual error logs for contradicting evidence
        try:
            error_log_evidence = await self._check_error_logs_for_contradictions()
            if error_log_evidence:
                evidence.append(error_log_evidence)
        except Exception as e:
            logger.warning(f"Could not check error logs: {e}")
        
        return evidence

    async def _collect_endpoint_evidence(self, source_data: Dict[str, Any], 
                                       context: str) -> List[Evidence]:
        """Collect evidence for endpoint accessibility claims."""
        evidence = []
        
        status_code = source_data.get('status_code')
        response_time = source_data.get('response_time_ms')
        
        if status_code is not None:
            # Determine evidence quality based on status code
            quality = EvidenceQuality.HIGH
            confidence = 0.9
            
            if status_code >= 500:
                quality = EvidenceQuality.INSUFFICIENT
                confidence = 0.0
            elif status_code in [401, 403]:
                quality = EvidenceQuality.LOW  # Authentication issue, not accessibility
                confidence = 0.3
            elif status_code >= 400:
                quality = EvidenceQuality.MEDIUM
                confidence = 0.6
            
            evidence.append(Evidence(
                evidence_id="",
                evidence_type=EvidenceType.HTTP_RESPONSE,
                claim_supporting=ValidationClaim.ENDPOINT_ACCESSIBLE,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "status_code": status_code,
                    "response_time_ms": response_time,
                    "url": source_data.get('url', ''),
                    "healthy_claimed": source_data.get('healthy', False)
                },
                quality=quality,
                confidence_score=confidence,
                source_system="endpoint_validator",
                validation_context=context
            ))
        
        return evidence

    async def _collect_authentication_evidence(self, source_data: Dict[str, Any], 
                                             context: str) -> List[Evidence]:
        """Collect evidence for authentication working claims."""
        evidence = []
        
        status_code = source_data.get('status_code')
        
        if status_code is not None:
            # Authentication evidence analysis
            quality = EvidenceQuality.INSUFFICIENT
            confidence = 0.0
            
            if status_code in [200, 201, 202, 204]:
                quality = EvidenceQuality.HIGH
                confidence = 0.95
            elif status_code in [401, 403]:
                quality = EvidenceQuality.HIGH  # High quality evidence of auth failure
                confidence = 0.0  # But zero confidence for working claim
            
            evidence.append(Evidence(
                evidence_id="",
                evidence_type=EvidenceType.HTTP_RESPONSE,
                claim_supporting=ValidationClaim.AUTHENTICATION_WORKING,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "status_code": status_code,
                    "auth_attempted": True,
                    "url": source_data.get('url', ''),
                    "user_console_match": source_data.get('user_console_match', False)
                },
                quality=quality,
                confidence_score=confidence,
                source_system="endpoint_validator",
                validation_context=context,
                metadata={
                    "auth_failure_detected": status_code in [401, 403]
                }
            ))
        
        return evidence

    async def _collect_database_evidence(self, source_data: Dict[str, Any], 
                                       context: str) -> List[Evidence]:
        """Collect evidence for database connection claims.""" 
        evidence = []
        
        if source_data.get('connection_successful'):
            evidence.append(Evidence(
                evidence_id="",
                evidence_type=EvidenceType.DATABASE_QUERY,
                claim_supporting=ValidationClaim.DATABASE_CONNECTED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "connection_test_passed": True,
                    "query_executed": source_data.get('query_executed', False),
                    "response_time_ms": source_data.get('response_time_ms', 0)
                },
                quality=EvidenceQuality.HIGH,
                confidence_score=0.9,
                source_system="database_validator",
                validation_context=context
            ))
        
        return evidence

    async def _collect_error_count_evidence(self, source_data: Dict[str, Any], 
                                          context: str) -> List[Evidence]:
        """Collect evidence for error count reduction claims."""
        evidence = []
        
        current_count = source_data.get('current_error_count')
        previous_count = source_data.get('previous_error_count')
        
        if current_count is not None and previous_count is not None:
            # Calculate actual change
            reduction = previous_count - current_count
            reduction_percentage = (reduction / previous_count) * 100 if previous_count > 0 else 0
            
            quality = EvidenceQuality.HIGH
            confidence = 0.9 if reduction > 0 else 0.1
            
            evidence.append(Evidence(
                evidence_id="",
                evidence_type=EvidenceType.METRIC_VALUE,
                claim_supporting=ValidationClaim.ERROR_COUNT_REDUCED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "current_error_count": current_count,
                    "previous_error_count": previous_count,
                    "actual_reduction": reduction,
                    "reduction_percentage": reduction_percentage,
                    "claimed_reduction": source_data.get('claimed_reduction', False)
                },
                quality=quality,
                confidence_score=confidence,
                source_system="error_analyzer",
                validation_context=context,
                metadata={
                    "error_count_increased": reduction < 0
                }
            ))
        
        return evidence

    async def _check_error_logs_for_contradictions(self) -> Optional[Evidence]:
        """Check actual error logs for evidence contradicting health claims."""
        try:
            error_log_path = Path("logs/error_summary.log")
            if not error_log_path.exists():
                return None
            
            # Read recent error log content
            with open(error_log_path, 'r') as f:
                log_content = f.read()
            
            # Extract error information
            error_data = {}
            if "ERROR COUNTS BY SEVERITY:" in log_content:
                lines = log_content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("ERROR:"):
                        error_count = int(line.split()[1]) if len(line.split()) > 1 else 0
                        error_data['total_errors'] = error_count
                    elif "RECENT CRITICAL/ERROR ENTRIES" in line:
                        # Count recent critical entries
                        recent_errors = []
                        for j in range(i+1, min(i+21, len(lines))):  # Next 20 lines
                            if lines[j].strip() and '[ERROR]' in lines[j]:
                                recent_errors.append(lines[j].strip())
                        error_data['recent_errors'] = recent_errors
                        break
            
            # Determine evidence quality based on error count
            total_errors = error_data.get('total_errors', 0)
            recent_error_count = len(error_data.get('recent_errors', []))
            
            quality = EvidenceQuality.HIGH
            confidence = 0.0 if total_errors > 1000 else 0.5  # System not healthy if many errors
            
            return Evidence(
                evidence_id="",
                evidence_type=EvidenceType.LOG_ENTRY,
                claim_supporting=ValidationClaim.SYSTEM_HEALTHY,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data={
                    "total_error_count": total_errors,
                    "recent_error_count": recent_error_count,
                    "log_file_checked": str(error_log_path),
                    "contradicts_health_claim": total_errors > 1000
                },
                quality=quality,
                confidence_score=confidence,
                source_system="log_analyzer",
                validation_context="error_log_verification",
                metadata={
                    "high_error_count_detected": total_errors > 1000,
                    "recent_errors_detected": recent_error_count > 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error checking logs: {e}")
            return None

    async def _validate_assertion(self, assertion: ValidationAssertion):
        """Validate an assertion based on collected evidence."""
        requirements = self.evidence_requirements[assertion.claim]
        
        # Check minimum evidence requirement
        evidence_count = len(assertion.evidence_collected)
        min_required = requirements['minimum_evidence']
        
        if evidence_count < min_required:
            assertion.assertion_valid = False
            assertion.failure_reasons.append(
                f"Insufficient evidence: {evidence_count} collected, {min_required} required"
            )
            assertion.confidence_score = 0.0
            return
        
        # Check evidence types
        evidence_types_present = set(ev.evidence_type for ev in assertion.evidence_collected)
        required_types = set(requirements['required_types'])
        missing_types = required_types - evidence_types_present
        
        if missing_types:
            assertion.assertion_valid = False
            assertion.failure_reasons.append(
                f"Missing required evidence types: {[t.value for t in missing_types]}"
            )
            assertion.confidence_score = 0.0
            return
        
        # Calculate aggregate confidence
        if assertion.evidence_collected:
            confidence_scores = [ev.confidence_score for ev in assertion.evidence_collected]
            assertion.confidence_score = sum(confidence_scores) / len(confidence_scores)
        else:
            assertion.confidence_score = 0.0
        
        # Check minimum confidence threshold
        min_confidence = requirements['minimum_confidence']
        if assertion.confidence_score < min_confidence:
            assertion.assertion_valid = False
            assertion.failure_reasons.append(
                f"Confidence too low: {assertion.confidence_score:.2f}, minimum {min_confidence}"
            )
            return
        
        # Check for contradicting evidence
        contradicting_evidence = [ev for ev in assertion.evidence_collected if ev.confidence_score < 0.5]
        if contradicting_evidence:
            assertion.assertion_valid = False
            assertion.failure_reasons.append(
                f"Contradicting evidence found: {len(contradicting_evidence)} pieces with low confidence"
            )
            return
        
        # Assertion passes validation
        assertion.assertion_valid = True
        logger.info(f"✅ Assertion validated: {assertion.claim.value} (confidence: {assertion.confidence_score:.2f})")

    async def _analyze_evidence_quality(self) -> Dict[str, Any]:
        """Analyze the quality and completeness of collected evidence."""
        analysis = {
            'critical_gaps': [],
            'quality_issues': [],
            'strength_areas': []
        }
        
        # Check for critical evidence gaps
        for assertion in self.assertions:
            if not assertion.assertion_valid:
                gap_description = f"Claim '{assertion.claim.value}' lacks sufficient evidence"
                analysis['critical_gaps'].append(gap_description)
        
        # Analyze evidence quality distribution
        insufficient_evidence = [ev for ev in self.evidence_database if ev.quality == EvidenceQuality.INSUFFICIENT]
        if insufficient_evidence:
            analysis['quality_issues'].append(
                f"{len(insufficient_evidence)} pieces of insufficient quality evidence"
            )
        
        # Identify strength areas
        high_quality_evidence = [ev for ev in self.evidence_database if ev.quality == EvidenceQuality.HIGH]
        if len(high_quality_evidence) > len(self.evidence_database) * 0.7:  # 70% high quality
            analysis['strength_areas'].append("Strong evidence quality overall")
        
        return analysis

    async def _detect_false_positive_risks(self) -> List[str]:
        """Detect potential false positive validation risks."""
        risks = []
        
        # Check for claims with contradicting evidence
        for assertion in self.assertions:
            contradicting_count = sum(1 for ev in assertion.evidence_collected if ev.confidence_score < 0.5)
            if contradicting_count > 0 and assertion.assertion_valid:
                risks.append(
                    f"Claim '{assertion.claim.value}' validated despite {contradicting_count} contradicting evidence pieces"
                )
        
        # Check for system health claims with error evidence
        system_health_assertions = [a for a in self.assertions if a.claim == ValidationClaim.SYSTEM_HEALTHY]
        for assertion in system_health_assertions:
            error_evidence = [ev for ev in assertion.evidence_collected 
                            if ev.evidence_type == EvidenceType.LOG_ENTRY 
                            and ev.data.get('contradicts_health_claim', False)]
            if error_evidence and assertion.assertion_valid:
                risks.append(
                    "System health claimed valid despite error log evidence contradicting claim"
                )
        
        # Check for authentication claims with failure evidence  
        auth_assertions = [a for a in self.assertions if a.claim == ValidationClaim.AUTHENTICATION_WORKING]
        for assertion in auth_assertions:
            auth_failure_evidence = [ev for ev in assertion.evidence_collected
                                   if ev.metadata.get('auth_failure_detected', False)]
            if auth_failure_evidence and assertion.assertion_valid:
                risks.append(
                    f"Authentication claimed working despite evidence of auth failures"
                )
        
        return risks

    def _calculate_overall_confidence(self) -> float:
        """Calculate overall validation confidence score."""
        if not self.assertions:
            return 0.0
        
        # Weight by claim importance
        claim_weights = {
            ValidationClaim.SYSTEM_HEALTHY: 3.0,
            ValidationClaim.DATABASE_CONNECTED: 2.5,
            ValidationClaim.AUTHENTICATION_WORKING: 2.5,
            ValidationClaim.ENDPOINT_ACCESSIBLE: 2.0,
            ValidationClaim.ERROR_COUNT_REDUCED: 1.5,
            ValidationClaim.SCHEMA_VALID: 2.0,
            ValidationClaim.PERFORMANCE_ACCEPTABLE: 1.0,
            ValidationClaim.USER_WORKFLOW_FUNCTIONAL: 2.0
        }
        
        weighted_confidence_sum = 0.0
        total_weight = 0.0
        
        for assertion in self.assertions:
            weight = claim_weights.get(assertion.claim, 1.0)
            confidence = assertion.confidence_score if assertion.assertion_valid else 0.0
            
            weighted_confidence_sum += confidence * weight
            total_weight += weight
        
        return weighted_confidence_sum / total_weight if total_weight > 0 else 0.0

    def _generate_evidence_recommendations(self) -> List[str]:
        """Generate recommendations based on evidence analysis."""
        recommendations = []
        
        # Failed assertions recommendations
        failed_assertions = [a for a in self.assertions if not a.assertion_valid]
        if failed_assertions:
            recommendations.append(
                f"CRITICAL: {len(failed_assertions)} validation claims lack sufficient evidence"
            )
            recommendations.append(
                "All validation claims must have concrete supporting evidence before being considered valid"
            )
        
        # Evidence quality recommendations
        insufficient_evidence = [ev for ev in self.evidence_database if ev.quality == EvidenceQuality.INSUFFICIENT]
        if insufficient_evidence:
            recommendations.append(
                f"Improve evidence quality: {len(insufficient_evidence)} pieces of insufficient evidence detected"
            )
        
        # False positive risk recommendations
        system_health_claims = [a for a in self.assertions 
                              if a.claim == ValidationClaim.SYSTEM_HEALTHY and a.assertion_valid]
        if system_health_claims:
            error_evidence = [ev for ev in self.evidence_database 
                            if ev.evidence_type == EvidenceType.LOG_ENTRY 
                            and ev.data.get('contradicts_health_claim', False)]
            if error_evidence:
                recommendations.append(
                    "WARNING: System health validated despite contradicting error log evidence"
                )
                recommendations.append(
                    "Review error logs and resolve contradictions before claiming system health"
                )
        
        # Success recommendations
        if all(a.assertion_valid for a in self.assertions) and not insufficient_evidence:
            recommendations.append(
                "All validation claims properly supported by high-quality evidence"
            )
        
        return recommendations

    async def save_evidence_report(self, report: EvidenceValidationReport, 
                                 output_path: Optional[Path] = None) -> Path:
        """Save evidence validation report to file."""
        if output_path is None:
            output_path = self.evidence_storage_path / f"evidence_report_{report.validation_id}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dictionaries for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"💾 Evidence validation report saved to: {output_path}")
        return output_path

    async def save_evidence_database(self, output_path: Optional[Path] = None) -> Path:
        """Save complete evidence database to file."""
        if output_path is None:
            output_path = self.evidence_storage_path / f"evidence_database_{self.validation_id}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        evidence_data = {
            'validation_id': self.validation_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_evidence': len(self.evidence_database),
            'evidence': [asdict(evidence) for evidence in self.evidence_database]
        }
        
        with open(output_path, 'w') as f:
            json.dump(evidence_data, f, indent=2, default=str)
        
        logger.info(f"💾 Evidence database saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    # Example usage
    config = {
        'evidence_path': '.claude/logs/evidence_proofs'
    }
    
    # Sample validation data that might come from orchestration
    sample_validation_data = {
        'overall_assessment': {
            'success': True,
            'status': 'healthy',
            'confidence': 100
        },
        'critical_endpoint_validation': {
            'results': {
                'categories_api': {
                    'status_code': 401,
                    'healthy': True,  # This is the false positive!
                    'user_console_match': False
                },
                'tasks_api': {
                    'status_code': 200,
                    'healthy': True,
                    'response_time_ms': 150
                }
            }
        },
        'error_analysis': {
            'current_error_count': 53066,  # Actual current count
            'previous_error_count': 34205,  # Previous count
            'error_count_reduced': False  # Truth: errors increased
        }
    }
    
    evidence_system = EvidenceBasedValidationSystem(config)
    
    # Run evidence-based validation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        evidence_report = loop.run_until_complete(
            evidence_system.validate_with_evidence(sample_validation_data)
        )
        
        print("\n" + "="*80)
        print("EVIDENCE-BASED VALIDATION REPORT")
        print("="*80)
        print(f"Validation ID: {evidence_report.validation_id}")
        print(f"Overall Confidence: {evidence_report.overall_validation_confidence:.2f}")
        print(f"Assertions Validated: {evidence_report.assertions_validated}/{evidence_report.total_assertions}")
        print(f"Evidence Collected: {evidence_report.total_evidence_collected}")
        print()
        
        if evidence_report.critical_evidence_gaps:
            print("❌ CRITICAL EVIDENCE GAPS:")
            for gap in evidence_report.critical_evidence_gaps:
                print(f"   - {gap}")
            print()
        
        if evidence_report.false_positive_risks:
            print("⚠️  FALSE POSITIVE RISKS:")
            for risk in evidence_report.false_positive_risks:
                print(f"   - {risk}")
            print()
        
        if evidence_report.recommendations:
            print("💡 RECOMMENDATIONS:")
            for rec in evidence_report.recommendations:
                print(f"   - {rec}")
            print()
        
        # Show assertion results
        print("📋 ASSERTION RESULTS:")
        for assertion in evidence_report.assertion_results:
            status_emoji = "✅" if assertion.assertion_valid else "❌"
            print(f"   {status_emoji} {assertion.claim.value}: "
                  f"confidence {assertion.confidence_score:.2f} "
                  f"({len(assertion.evidence_collected)} evidence)")
            if assertion.failure_reasons:
                for reason in assertion.failure_reasons:
                    print(f"      - {reason}")
        
        # Save reports
        loop.run_until_complete(evidence_system.save_evidence_report(evidence_report))
        loop.run_until_complete(evidence_system.save_evidence_database())
        
    finally:
        loop.close()