"""Hypothesis testing service for reality validation and evidence analysis.

Implements systematic hypothesis testing with statistical analysis and
Bayesian reasoning for cognitive architecture validation.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import structlog

from models.requests import HypothesisTestingRequest, Evidence
from models.responses import HypothesisTestingResponse, HypothesisResult
from .ollama_service import OllamaService
from .redis_service import RedisService

logger = structlog.get_logger(__name__)


class HypothesisTester:
    """Advanced hypothesis testing with reality validation integration."""
    
    def __init__(
        self,
        ollama_service: OllamaService,
        redis_service: RedisService,
        significance_threshold: float = 0.05
    ):
        self.ollama_service = ollama_service
        self.redis_service = redis_service
        self.significance_threshold = significance_threshold
        
        # Testing methodologies
        self.testing_methods = {
            "statistical": "Statistical hypothesis testing with significance analysis",
            "bayesian": "Bayesian inference and probability updating",
            "logical": "Logical consistency and deductive reasoning",
            "empirical": "Empirical evidence evaluation and pattern analysis",
            "comparative": "Comparative analysis with alternative hypotheses"
        }
    
    async def test_hypothesis(
        self,
        request: HypothesisTestingRequest,
        request_id: Optional[str] = None
    ) -> HypothesisTestingResponse:
        """Perform comprehensive hypothesis testing with reality validation."""
        start_time = time.time()
        
        logger.info(
            "Starting hypothesis testing",
            request_id=request_id,
            hypothesis=request.hypothesis[:100] + "..." if len(request.hypothesis) > 100 else request.hypothesis,
            evidence_count=len(request.evidence),
            significance_level=request.significance_level
        )
        
        try:
            # Determine optimal testing methodology
            methodology = await self._select_testing_methodology(request, request_id)
            
            # Analyze evidence in parallel
            evidence_analysis = await self._analyze_evidence_batch(
                request.evidence, request.hypothesis, request.context, request_id
            )
            
            # Perform hypothesis test
            hypothesis_result = await self._perform_hypothesis_test(
                request, evidence_analysis, methodology, request_id
            )
            
            # Generate recommendations
            recommendations = await self._generate_testing_recommendations(
                request, hypothesis_result, evidence_analysis, request_id
            )
            
            processing_time = time.time() - start_time
            
            # Record performance metrics
            await self.redis_service.record_performance_metric(
                "hypothesis_testing_time_ms",
                processing_time * 1000,
                tags={
                    "methodology": methodology,
                    "evidence_count": str(len(request.evidence))
                }
            )
            
            await self.redis_service.record_performance_metric(
                "hypothesis_confidence_score",
                hypothesis_result.confidence_score,
                tags={"test_result": hypothesis_result.test_result}
            )
            
            logger.info(
                "Hypothesis testing completed",
                request_id=request_id,
                test_result=hypothesis_result.test_result,
                confidence_score=hypothesis_result.confidence_score,
                methodology=methodology,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            return HypothesisTestingResponse(
                hypothesis=request.hypothesis,
                result=hypothesis_result,
                methodology=methodology,
                evidence_analysis=evidence_analysis.get("summary", "Evidence analysis completed"),
                recommendations=recommendations,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Hypothesis testing failed",
                request_id=request_id,
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2)
            )
            raise
    
    async def _select_testing_methodology(
        self,
        request: HypothesisTestingRequest,
        request_id: Optional[str] = None
    ) -> str:
        """Select optimal testing methodology based on hypothesis and evidence."""
        
        methodology_prompt = f"""
        Analyze the following hypothesis and evidence to determine the most appropriate testing methodology:
        
        Hypothesis: {request.hypothesis}
        
        Available Evidence Types:
        """ + "\n".join([
            f"- {evidence.source or 'Unknown source'}: {evidence.content[:100]}..."
            for evidence in request.evidence
        ]) + f"""
        
        Context: {request.context or 'No additional context'}
        
        Available methodologies:
        - statistical: For quantitative data and measurable outcomes
        - bayesian: For updating beliefs with new evidence and uncertainty
        - logical: For logical consistency and deductive reasoning
        - empirical: For observational evidence and pattern analysis
        - comparative: For comparing with alternative explanations
        
        Select the single most appropriate methodology and explain why in 1-2 sentences.
        Consider the nature of the hypothesis, available evidence types, and context.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=methodology_prompt,
                system_prompt="You are a research methodology expert. Select the most appropriate testing approach.",
                temperature=0.2,
                request_id=request_id
            )
            
            response_text = llm_response.get("response", "").lower()
            
            # Extract methodology
            for method in self.testing_methods.keys():
                if method in response_text:
                    logger.info("Selected testing methodology", 
                               method=method, request_id=request_id)
                    return method
            
            # Default to empirical if unclear
            logger.info("Defaulting to empirical methodology", request_id=request_id)
            return "empirical"
            
        except Exception as e:
            logger.error("Failed to select methodology", error=str(e))
            return "empirical"  # Safe default
    
    async def _analyze_evidence_batch(
        self,
        evidence_items: List[Evidence],
        hypothesis: str,
        context: Optional[str],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze evidence items in batch for hypothesis relevance."""
        
        # Analyze evidence items concurrently
        analysis_tasks = [
            self._analyze_single_evidence(evidence, hypothesis, context, f"{request_id}_evidence_{i}")
            for i, evidence in enumerate(evidence_items)
        ]
        
        analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Process results
        valid_analyses = []
        supporting_evidence = []
        contradicting_evidence = []
        
        for i, analysis in enumerate(analyses):
            if isinstance(analysis, Exception):
                logger.error("Evidence analysis error", 
                           evidence_index=i, error=str(analysis))
                continue
            
            valid_analyses.append(analysis)
            
            if analysis.get("supports_hypothesis", False):
                supporting_evidence.append(analysis.get("relevance_summary", ""))
            elif analysis.get("contradicts_hypothesis", False):
                contradicting_evidence.append(analysis.get("relevance_summary", ""))
        
        # Generate overall evidence summary
        summary_prompt = f"""
        Summarize the following evidence analysis for hypothesis testing:
        
        Hypothesis: {hypothesis}
        
        Supporting Evidence ({len(supporting_evidence)} items):
        """ + "\n".join(supporting_evidence) + f"""
        
        Contradicting Evidence ({len(contradicting_evidence)} items):
        """ + "\n".join(contradicting_evidence) + """
        
        Provide a concise 2-3 sentence summary of the evidence landscape.
        Focus on the overall strength and balance of evidence.
        """
        
        try:
            summary_response = await self.ollama_service.generate_reasoning(
                prompt=summary_prompt,
                system_prompt="You are analyzing evidence for hypothesis testing. Be objective and balanced.",
                temperature=0.3,
                request_id=request_id
            )
            summary = summary_response.get("response", "Evidence analysis completed.")
        except Exception:
            summary = f"Analyzed {len(valid_analyses)} evidence items with mixed findings."
        
        return {
            "analyses": valid_analyses,
            "supporting_count": len(supporting_evidence),
            "contradicting_count": len(contradicting_evidence),
            "summary": summary
        }
    
    async def _analyze_single_evidence(
        self,
        evidence: Evidence,
        hypothesis: str,
        context: Optional[str],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze single evidence item for hypothesis relevance."""
        
        analysis_prompt = f"""
        Analyze how this evidence relates to the given hypothesis:
        
        Hypothesis: {hypothesis}
        
        Evidence: {evidence.content}
        Source: {evidence.source or 'Unknown'}
        Source Confidence: {evidence.confidence or 'Not specified'}
        
        Context: {context or 'No additional context'}
        
        Evaluate:
        1. Does this evidence support, contradict, or is neutral to the hypothesis?
        2. How strong is this evidence (considering source, methodology, sample size, etc.)?
        3. What are the key implications for the hypothesis?
        4. Are there any limitations or caveats?
        
        Provide clear classification: supports_hypothesis, contradicts_hypothesis, or neutral.
        """
        
        # Request structured response
        response_format = {
            "supports_hypothesis": False,
            "contradicts_hypothesis": False,
            "neutral": True,
            "strength_score": 0.5,
            "relevance_score": 0.5,
            "relevance_summary": "",
            "limitations": []
        }
        
        llm_response = await self.ollama_service.generate_structured_reasoning(
            prompt=analysis_prompt,
            response_format=response_format,
            system_prompt="You are evaluating evidence for hypothesis testing. Be precise and objective.",
            request_id=request_id
        )
        
        # Process response
        if llm_response.get("parsing_success"):
            return llm_response["structured_response"]
        else:
            # Fallback analysis
            raw_response = llm_response.get("response", "").lower()
            supports = "support" in raw_response and "hypothesis" in raw_response
            contradicts = "contradict" in raw_response or "against" in raw_response
            
            return {
                "supports_hypothesis": supports and not contradicts,
                "contradicts_hypothesis": contradicts and not supports,
                "neutral": not supports and not contradicts,
                "strength_score": 0.5,
                "relevance_score": 0.5,
                "relevance_summary": evidence.content[:100] + "..." if len(evidence.content) > 100 else evidence.content,
                "limitations": ["Analysis parsing failed"]
            }
    
    async def _perform_hypothesis_test(
        self,
        request: HypothesisTestingRequest,
        evidence_analysis: Dict[str, Any],
        methodology: str,
        request_id: Optional[str] = None
    ) -> HypothesisResult:
        """Perform the actual hypothesis test using selected methodology."""
        
        test_prompt = f"""
        Perform {methodology} hypothesis testing for the following scenario:
        
        Hypothesis: {request.hypothesis}
        
        Evidence Summary:
        - Supporting evidence: {evidence_analysis.get('supporting_count', 0)} items
        - Contradicting evidence: {evidence_analysis.get('contradicting_count', 0)} items
        - Analysis: {evidence_analysis.get('summary', 'No summary available')}
        
        Significance Level: {request.significance_level}
        
        Alternative Hypotheses to Consider:
        """ + "\n".join(request.alternative_hypotheses or ["No alternative hypotheses provided"]) + f"""
        
        Using {methodology} methodology ({self.testing_methods.get(methodology, '')}):
        
        1. Evaluate the strength of evidence for and against the hypothesis
        2. Consider statistical significance and effect sizes where applicable
        3. Assess the probability of the hypothesis being true
        4. Compare with alternative explanations
        5. Determine overall test result: supported, not_supported, or inconclusive
        
        Provide your analysis with confidence score (0.0-1.0) and reasoning.
        """
        
        # Request structured response
        response_format = {
            "test_result": "inconclusive",
            "confidence_score": 0.5,
            "p_value": None,
            "effect_size": None,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "alternative_hypotheses": [],
            "reasoning": ""
        }
        
        llm_response = await self.ollama_service.generate_structured_reasoning(
            prompt=test_prompt,
            response_format=response_format,
            system_prompt=f"You are a {methodology} expert performing rigorous hypothesis testing.",
            request_id=request_id
        )
        
        # Process response
        if llm_response.get("parsing_success"):
            structured = llm_response["structured_response"]
            
            return HypothesisResult(
                test_result=structured.get("test_result", "inconclusive"),
                confidence_score=max(0.0, min(1.0, float(structured.get("confidence_score", 0.5)))),
                p_value=structured.get("p_value"),
                effect_size=structured.get("effect_size"),
                supporting_evidence=structured.get("supporting_evidence", [])[:10],
                contradicting_evidence=structured.get("contradicting_evidence", [])[:10],
                alternative_hypotheses=structured.get("alternative_hypotheses", request.alternative_hypotheses or [])
            )
        else:
            # Fallback processing
            return self._process_fallback_test_result(
                llm_response.get("response", ""),
                evidence_analysis,
                request
            )
    
    def _process_fallback_test_result(
        self,
        raw_response: str,
        evidence_analysis: Dict[str, Any],
        request: HypothesisTestingRequest
    ) -> HypothesisResult:
        """Process test result when structured parsing fails."""
        
        raw_lower = raw_response.lower()
        
        # Determine test result from keywords
        if "supported" in raw_lower and "not supported" not in raw_lower:
            test_result = "supported"
            confidence = 0.7
        elif "not supported" in raw_lower or "reject" in raw_lower:
            test_result = "not_supported"
            confidence = 0.7
        else:
            test_result = "inconclusive"
            confidence = 0.5
        
        # Adjust confidence based on evidence balance
        supporting_count = evidence_analysis.get("supporting_count", 0)
        contradicting_count = evidence_analysis.get("contradicting_count", 0)
        
        if supporting_count > contradicting_count * 2:
            confidence = min(1.0, confidence * 1.2)
        elif contradicting_count > supporting_count * 2:
            confidence = min(1.0, confidence * 1.2)
        else:
            confidence *= 0.8  # Lower confidence for balanced evidence
        
        return HypothesisResult(
            test_result=test_result,
            confidence_score=confidence,
            p_value=None,
            effect_size=None,
            supporting_evidence=[f"Evidence analysis completed with {supporting_count} supporting items"],
            contradicting_evidence=[f"Evidence analysis completed with {contradicting_count} contradicting items"],
            alternative_hypotheses=request.alternative_hypotheses or []
        )
    
    async def _generate_testing_recommendations(
        self,
        request: HypothesisTestingRequest,
        result: HypothesisResult,
        evidence_analysis: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> List[str]:
        """Generate recommendations for further hypothesis testing."""
        
        recommendations_prompt = f"""
        Based on the following hypothesis testing results, provide recommendations for further testing or validation:
        
        Original Hypothesis: {request.hypothesis}
        Test Result: {result.test_result}
        Confidence Score: {result.confidence_score:.2f}
        
        Evidence Summary:
        - Supporting: {evidence_analysis.get('supporting_count', 0)} items
        - Contradicting: {evidence_analysis.get('contradicting_count', 0)} items
        
        Current Limitations:
        - Significance level: {request.significance_level}
        - Available evidence quality varies
        
        Provide 3-5 specific, actionable recommendations for:
        1. Improving the quality of testing
        2. Gathering additional evidence
        3. Refining the hypothesis if needed
        4. Next steps based on current results
        
        Focus on practical steps that could strengthen the analysis.
        Each recommendation should be one clear sentence.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=recommendations_prompt,
                system_prompt="You are a research expert providing methodological recommendations.",
                temperature=0.3,
                request_id=request_id
            )
            
            response_text = llm_response.get("response", "")
            
            # Extract recommendations
            recommendations = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    recommendation = line.lstrip('-•0123456789. ').strip()
                    if recommendation and len(recommendation) > 15:
                        recommendations.append(recommendation)
            
            if not recommendations:
                # Fallback recommendations based on result
                if result.test_result == "inconclusive":
                    recommendations = [
                        "Gather additional evidence to strengthen the analysis",
                        "Consider extending the observation period or sample size",
                        "Refine the hypothesis to be more specific and testable"
                    ]
                elif result.confidence_score < 0.7:
                    recommendations = [
                        "Seek higher quality evidence sources",
                        "Consider alternative testing methodologies",
                        "Validate findings through independent replication"
                    ]
                else:
                    recommendations = [
                        "Monitor for new evidence that might challenge or support findings",
                        "Consider expanding the scope to related hypotheses",
                        "Document assumptions and limitations for future reference"
                    ]
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error("Failed to generate testing recommendations", error=str(e))
            return [
                "Continue monitoring for additional evidence",
                "Consider replicating the analysis with different approaches",
                "Review and refine hypothesis based on current findings",
                "Seek peer review of methodology and conclusions"
            ]