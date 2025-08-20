"""Evidence-based validation service with >85% accuracy requirement.

Implements systematic evidence evaluation using multiple validation criteria
and LLM-powered analysis to meet Phase 2 cognitive architecture standards.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, List, Optional
import structlog

from models.requests import Evidence, EvidenceValidationRequest
from models.responses import EvidenceAssessment, EvidenceValidationResponse
from .ollama_service import OllamaService
from .redis_service import RedisService

logger = structlog.get_logger(__name__)


class EvidenceValidator:
    """Advanced evidence validation with >85% accuracy requirement."""
    
    def __init__(
        self,
        ollama_service: OllamaService,
        redis_service: RedisService,
        validation_threshold: float = 0.85,
        use_cache: bool = True
    ):
        self.ollama_service = ollama_service
        self.redis_service = redis_service
        self.validation_threshold = validation_threshold
        self.use_cache = use_cache
        
        # Validation criteria weights
        self.criteria_weights = {
            "source_credibility": 0.25,
            "factual_consistency": 0.30,
            "statistical_validity": 0.20,
            "bias_assessment": 0.15,
            "verification_methods": 0.10
        }
        
    def _generate_evidence_hash(self, evidence: Evidence) -> str:
        """Generate unique hash for evidence item for caching."""
        content_str = f"{evidence.content}|{evidence.source or ''}|{evidence.confidence or 0}"
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    async def validate_evidence_batch(
        self,
        request: EvidenceValidationRequest,
        request_id: Optional[str] = None
    ) -> EvidenceValidationResponse:
        """Validate batch of evidence items with >85% accuracy requirement."""
        start_time = time.time()
        
        logger.info(
            "Starting evidence validation batch",
            request_id=request_id,
            evidence_count=len(request.evidence),
            require_high_confidence=request.require_high_confidence
        )
        
        try:
            # Validate individual evidence items concurrently
            validation_tasks = [
                self._validate_single_evidence(
                    evidence=evidence,
                    context=request.context,
                    validation_criteria=request.validation_criteria,
                    request_id=f"{request_id}_evidence_{i}" if request_id else f"evidence_{i}"
                )
                for i, evidence in enumerate(request.evidence)
            ]
            
            assessments = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            valid_assessments = []
            for i, assessment in enumerate(assessments):
                if isinstance(assessment, Exception):
                    logger.error(
                        "Evidence validation error",
                        evidence_index=i,
                        error=str(assessment),
                        request_id=request_id
                    )
                    # Create error assessment
                    valid_assessments.append(EvidenceAssessment(
                        evidence_id=f"evidence_{i}",
                        validity_score=0.0,
                        reliability_score=0.0,
                        confidence=0.0,
                        strengths=[],
                        weaknesses=[f"Validation error: {str(assessment)}"],
                        recommendations=["Retry validation with different approach"]
                    ))
                else:
                    valid_assessments.append(assessment)
            
            # Calculate overall validity
            overall_validity = self._calculate_overall_validity(valid_assessments)
            meets_threshold = (
                overall_validity >= self.validation_threshold
                if request.require_high_confidence
                else overall_validity >= 0.5  # Lower threshold for exploratory validation
            )
            
            # Generate summary
            summary = self._generate_validation_summary(
                valid_assessments,
                overall_validity,
                meets_threshold
            )
            
            # Calculate overall confidence
            confidence_scores = [a.confidence for a in valid_assessments if a.confidence > 0]
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            processing_time = time.time() - start_time
            
            # Record performance metrics
            await self.redis_service.record_performance_metric(
                "evidence_validation_time_ms",
                processing_time * 1000,
                tags={"evidence_count": str(len(request.evidence))}
            )
            
            await self.redis_service.record_performance_metric(
                "evidence_validation_accuracy",
                overall_validity,
                tags={"meets_threshold": str(meets_threshold)}
            )
            
            logger.info(
                "Evidence validation batch completed",
                request_id=request_id,
                overall_validity=overall_validity,
                meets_threshold=meets_threshold,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            return EvidenceValidationResponse(
                overall_validity=overall_validity,
                meets_threshold=meets_threshold,
                assessments=valid_assessments,
                summary=summary,
                processing_time_ms=round(processing_time * 1000, 2),
                validation_method="multi_criteria_llm_analysis",
                confidence_score=overall_confidence
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Evidence validation batch failed",
                request_id=request_id,
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2)
            )
            raise
    
    async def _validate_single_evidence(
        self,
        evidence: Evidence,
        context: Optional[str] = None,
        validation_criteria: Optional[List[str]] = None,
        request_id: Optional[str] = None
    ) -> EvidenceAssessment:
        """Validate individual evidence item."""
        evidence_hash = self._generate_evidence_hash(evidence)
        
        # Check cache if enabled
        if self.use_cache:
            cached_result = await self.redis_service.get_cached_evidence_validation(evidence_hash)
            if cached_result:
                logger.debug("Using cached evidence validation", 
                           evidence_hash=evidence_hash, request_id=request_id)
                return EvidenceAssessment(**cached_result)
        
        # Perform validation using LLM
        validation_prompt = self._build_validation_prompt(
            evidence, context, validation_criteria
        )
        
        # Request structured response
        response_format = {
            "validity_score": 0.0,
            "reliability_score": 0.0,
            "confidence": 0.0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "detailed_analysis": ""
        }
        
        llm_response = await self.ollama_service.generate_structured_reasoning(
            prompt=validation_prompt,
            response_format=response_format,
            system_prompt="You are an expert evidence evaluator. Provide thorough, objective analysis.",
            request_id=request_id
        )
        
        # Process LLM response
        assessment = self._process_validation_response(
            llm_response,
            evidence_hash,
            evidence
        )
        
        # Cache result if successful
        if self.use_cache and assessment.confidence > 0.5:
            await self.redis_service.cache_evidence_validation(
                evidence_hash,
                assessment.dict()
            )
        
        return assessment
    
    def _build_validation_prompt(
        self,
        evidence: Evidence,
        context: Optional[str] = None,
        validation_criteria: Optional[List[str]] = None
    ) -> str:
        """Build comprehensive validation prompt for LLM."""
        
        prompt_parts = [
            "Analyze the following evidence using systematic validation criteria:",
            f"\nEvidence Content: {evidence.content}",
        ]
        
        if evidence.source:
            prompt_parts.append(f"Source: {evidence.source}")
            
        if evidence.confidence is not None:
            prompt_parts.append(f"Source-Reported Confidence: {evidence.confidence}")
            
        if evidence.metadata:
            prompt_parts.append(f"Metadata: {json.dumps(evidence.metadata, indent=2)}")
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        # Add validation criteria
        prompt_parts.append("\nEvaluate this evidence using the following criteria:")
        
        criteria = validation_criteria or [
            "source_credibility",
            "factual_consistency", 
            "statistical_validity",
            "bias_assessment",
            "verification_methods"
        ]
        
        criteria_descriptions = {
            "source_credibility": "Assess the credibility and expertise of the source",
            "factual_consistency": "Check consistency with established facts and logical principles",
            "statistical_validity": "Evaluate statistical methods, sample sizes, and significance",
            "bias_assessment": "Identify potential biases, conflicts of interest, or limitations",
            "verification_methods": "Assess reproducibility and cross-verification possibilities"
        }
        
        for criterion in criteria:
            description = criteria_descriptions.get(criterion, f"Evaluate {criterion}")
            prompt_parts.append(f"- {criterion.title().replace('_', ' ')}: {description}")
        
        prompt_parts.extend([
            "\nProvide scores from 0.0 (lowest) to 1.0 (highest) for:",
            "- Validity Score: Overall validity of the evidence",
            "- Reliability Score: Reliability and trustworthiness",
            "- Confidence: Your confidence in this assessment",
            "",
            "Also provide:",
            "- Strengths: Key strengths of this evidence (list of strings)",
            "- Weaknesses: Limitations or concerns (list of strings)",  
            "- Recommendations: Suggestions for improvement or additional validation (list of strings)",
            "",
            "Focus on objective analysis. Be thorough but concise.",
            "Scores should reflect the actual quality of evidence, not wishful thinking."
        ])
        
        return "\n".join(prompt_parts)
    
    def _process_validation_response(
        self,
        llm_response: Dict[str, Any],
        evidence_hash: str,
        evidence: Evidence
    ) -> EvidenceAssessment:
        """Process LLM validation response into structured assessment."""
        
        try:
            if llm_response.get("parsing_success"):
                structured = llm_response["structured_response"]
                
                return EvidenceAssessment(
                    evidence_id=evidence_hash,
                    validity_score=max(0.0, min(1.0, float(structured.get("validity_score", 0.0)))),
                    reliability_score=max(0.0, min(1.0, float(structured.get("reliability_score", 0.0)))),
                    confidence=max(0.0, min(1.0, float(structured.get("confidence", 0.0)))),
                    strengths=structured.get("strengths", [])[:10],  # Limit to 10 items
                    weaknesses=structured.get("weaknesses", [])[:10],
                    recommendations=structured.get("recommendations", [])[:10]
                )
            else:
                # Fallback: parse from raw response
                raw_response = llm_response.get("response", "")
                return self._parse_fallback_response(raw_response, evidence_hash)
                
        except Exception as e:
            logger.error("Error processing validation response", 
                        evidence_hash=evidence_hash, error=str(e))
            
            # Return conservative assessment
            return EvidenceAssessment(
                evidence_id=evidence_hash,
                validity_score=0.3,  # Conservative default
                reliability_score=0.3,
                confidence=0.2,
                strengths=["Evidence provided"],
                weaknesses=["Unable to fully analyze", f"Processing error: {str(e)}"],
                recommendations=["Manual review required", "Resubmit for validation"]
            )
    
    def _parse_fallback_response(
        self,
        raw_response: str,
        evidence_hash: str
    ) -> EvidenceAssessment:
        """Fallback parsing when structured response fails."""
        
        # Simple heuristic parsing
        lines = raw_response.lower().split('\n')
        
        validity_score = 0.5
        reliability_score = 0.5
        confidence = 0.3
        
        # Look for score indicators
        for line in lines:
            if 'validity' in line and any(char.isdigit() for char in line):
                # Extract numbers
                numbers = [float(x) for x in line.split() if x.replace('.', '').isdigit()]
                if numbers:
                    validity_score = max(0.0, min(1.0, numbers[0]))
            
            if 'reliability' in line and any(char.isdigit() for char in line):
                numbers = [float(x) for x in line.split() if x.replace('.', '').isdigit()]
                if numbers:
                    reliability_score = max(0.0, min(1.0, numbers[0]))
            
            if 'confidence' in line and any(char.isdigit() for char in line):
                numbers = [float(x) for x in line.split() if x.replace('.', '').isdigit()]
                if numbers:
                    confidence = max(0.0, min(1.0, numbers[0]))
        
        return EvidenceAssessment(
            evidence_id=evidence_hash,
            validity_score=validity_score,
            reliability_score=reliability_score,
            confidence=confidence,
            strengths=["Evidence analyzed"],
            weaknesses=["Structured parsing failed"],
            recommendations=["Review raw analysis", "Reformat evidence"]
        )
    
    def _calculate_overall_validity(self, assessments: List[EvidenceAssessment]) -> float:
        """Calculate overall validity score from individual assessments."""
        if not assessments:
            return 0.0
        
        # Weighted average based on confidence scores
        weighted_sum = 0.0
        total_weight = 0.0
        
        for assessment in assessments:
            weight = assessment.confidence
            weighted_sum += assessment.validity_score * weight
            total_weight += weight
        
        if total_weight == 0:
            # Fallback to simple average
            return sum(a.validity_score for a in assessments) / len(assessments)
        
        return weighted_sum / total_weight
    
    def _generate_validation_summary(
        self,
        assessments: List[EvidenceAssessment],
        overall_validity: float,
        meets_threshold: bool
    ) -> str:
        """Generate human-readable summary of validation results."""
        
        summary_parts = []
        
        # Overall result
        if meets_threshold:
            summary_parts.append(f"Evidence validation successful with {overall_validity:.2%} overall validity.")
        else:
            summary_parts.append(f"Evidence validation shows {overall_validity:.2%} validity, below required threshold.")
        
        # Aggregate strengths and weaknesses
        all_strengths = []
        all_weaknesses = []
        
        for assessment in assessments:
            all_strengths.extend(assessment.strengths)
            all_weaknesses.extend(assessment.weaknesses)
        
        # Count common themes
        strength_counts = {}
        weakness_counts = {}
        
        for strength in all_strengths:
            strength_counts[strength] = strength_counts.get(strength, 0) + 1
            
        for weakness in all_weaknesses:
            weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1
        
        # Top strengths
        if strength_counts:
            top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            summary_parts.append(f"Key strengths: {', '.join([s[0] for s in top_strengths])}")
        
        # Top concerns
        if weakness_counts:
            top_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            summary_parts.append(f"Main concerns: {', '.join([w[0] for w in top_weaknesses])}")
        
        # Confidence assessment
        avg_confidence = sum(a.confidence for a in assessments) / len(assessments)
        if avg_confidence >= 0.8:
            summary_parts.append("High confidence in validation assessment.")
        elif avg_confidence >= 0.6:
            summary_parts.append("Moderate confidence in validation assessment.")
        else:
            summary_parts.append("Low confidence in validation assessment - manual review recommended.")
        
        return " ".join(summary_parts)