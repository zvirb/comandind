"""Multi-criteria decision analysis with confidence scoring.

Implements systematic decision evaluation using weighted criteria,
trade-off analysis, and risk assessment for cognitive decision making.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
import structlog

from models.requests import MultiCriteriaDecisionRequest, DecisionCriteria, DecisionOption
from models.responses import MultiCriteriaDecisionResponse, DecisionEvaluation
from .ollama_service import OllamaService
from .redis_service import RedisService

logger = structlog.get_logger(__name__)


class DecisionAnalyzer:
    """Advanced multi-criteria decision analysis with confidence scoring."""
    
    def __init__(
        self,
        ollama_service: OllamaService,
        redis_service: RedisService,
        confidence_threshold: float = 0.7
    ):
        self.ollama_service = ollama_service
        self.redis_service = redis_service
        self.confidence_threshold = confidence_threshold
        
    async def analyze_decision(
        self,
        request: MultiCriteriaDecisionRequest,
        request_id: Optional[str] = None
    ) -> MultiCriteriaDecisionResponse:
        """Perform comprehensive multi-criteria decision analysis."""
        start_time = time.time()
        
        logger.info(
            "Starting multi-criteria decision analysis",
            request_id=request_id,
            options_count=len(request.options),
            criteria_count=len(request.criteria),
            context=request.context[:100] + "..." if len(request.context) > 100 else request.context
        )
        
        try:
            # Evaluate all options concurrently
            evaluation_tasks = [
                self._evaluate_option(
                    option=option,
                    criteria=request.criteria,
                    context=request.context,
                    additional_constraints=request.additional_constraints,
                    request_id=f"{request_id}_option_{i}" if request_id else f"option_{i}"
                )
                for i, option in enumerate(request.options)
            ]
            
            evaluations = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
            
            # Process evaluation results
            valid_evaluations = []
            for i, evaluation in enumerate(evaluations):
                if isinstance(evaluation, Exception):
                    logger.error(
                        "Option evaluation error",
                        option_index=i,
                        option_name=request.options[i].name,
                        error=str(evaluation),
                        request_id=request_id
                    )
                    # Create fallback evaluation
                    valid_evaluations.append(self._create_fallback_evaluation(
                        request.options[i], request.criteria, str(evaluation)
                    ))
                else:
                    valid_evaluations.append(evaluation)
            
            # Determine recommendation
            recommended_option, confidence_score = self._select_recommendation(valid_evaluations)
            
            # Generate decision rationale
            rationale = await self._generate_decision_rationale(
                request, valid_evaluations, recommended_option, request_id
            )
            
            # Perform sensitivity analysis
            sensitivity_analysis = self._perform_sensitivity_analysis(
                valid_evaluations, request.criteria
            )
            
            # Generate risk mitigation strategies
            risk_mitigation = await self._generate_risk_mitigation(
                request, recommended_option, valid_evaluations, request_id
            )
            
            processing_time = time.time() - start_time
            
            # Record performance metrics
            await self.redis_service.record_performance_metric(
                "decision_analysis_time_ms",
                processing_time * 1000,
                tags={
                    "options_count": str(len(request.options)),
                    "criteria_count": str(len(request.criteria))
                }
            )
            
            await self.redis_service.record_performance_metric(
                "decision_confidence_score",
                confidence_score,
                tags={"recommended_option": recommended_option}
            )
            
            logger.info(
                "Multi-criteria decision analysis completed",
                request_id=request_id,
                recommended_option=recommended_option,
                confidence_score=confidence_score,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            return MultiCriteriaDecisionResponse(
                recommended_option=recommended_option,
                confidence_score=confidence_score,
                evaluations=valid_evaluations,
                decision_rationale=rationale,
                sensitivity_analysis=sensitivity_analysis,
                risk_mitigation=risk_mitigation,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Multi-criteria decision analysis failed",
                request_id=request_id,
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2)
            )
            raise
    
    async def _evaluate_option(
        self,
        option: DecisionOption,
        criteria: List[DecisionCriteria],
        context: str,
        additional_constraints: Optional[List[str]] = None,
        request_id: Optional[str] = None
    ) -> DecisionEvaluation:
        """Evaluate a single option against all criteria."""
        
        evaluation_prompt = self._build_evaluation_prompt(
            option, criteria, context, additional_constraints
        )
        
        # Request structured response
        response_format = {
            "criteria_scores": {criterion.name: 0.0 for criterion in criteria},
            "overall_score": 0.0,
            "strengths": [],
            "weaknesses": [],
            "risk_factors": [],
            "implementation_considerations": [],
            "detailed_analysis": ""
        }
        
        llm_response = await self.ollama_service.generate_structured_reasoning(
            prompt=evaluation_prompt,
            response_format=response_format,
            system_prompt="You are an expert decision analyst. Provide thorough, objective evaluation.",
            request_id=request_id
        )
        
        # Process response
        return self._process_evaluation_response(llm_response, option, criteria)
    
    def _build_evaluation_prompt(
        self,
        option: DecisionOption,
        criteria: List[DecisionCriteria],
        context: str,
        additional_constraints: Optional[List[str]] = None
    ) -> str:
        """Build comprehensive evaluation prompt for option analysis."""
        
        prompt_parts = [
            f"Evaluate the following decision option using multi-criteria analysis:",
            f"\nOption: {option.name}",
            f"Description: {option.description or 'No description provided'}",
            f"Context: {context}",
        ]
        
        # Add option attributes
        if option.attributes:
            prompt_parts.append(f"\nOption Attributes:")
            for key, value in option.attributes.items():
                prompt_parts.append(f"- {key}: {value}")
        
        # Add criteria details
        prompt_parts.append(f"\nEvaluation Criteria:")
        for criterion in criteria:
            prompt_parts.append(
                f"- {criterion.name} (Weight: {criterion.weight:.2f}): "
                f"{criterion.description or 'Evaluate performance on this criterion'}"
            )
        
        # Add constraints
        if additional_constraints:
            prompt_parts.append(f"\nAdditional Constraints:")
            for constraint in additional_constraints:
                prompt_parts.append(f"- {constraint}")
        
        prompt_parts.extend([
            "\nFor each criterion, provide a score from 0.0 (worst) to 1.0 (best).",
            "Calculate the overall weighted score using the provided weights.",
            "",
            "Also identify:",
            "- Strengths: Key advantages of this option (list of strings)",
            "- Weaknesses: Limitations or disadvantages (list of strings)",
            "- Risk Factors: Potential risks or challenges (list of strings)",
            "- Implementation Considerations: Practical aspects to consider (list of strings)",
            "",
            "Provide objective analysis based on the option attributes and your understanding.",
            "Consider trade-offs, feasibility, and long-term implications."
        ])
        
        return "\n".join(prompt_parts)
    
    def _process_evaluation_response(
        self,
        llm_response: Dict[str, Any],
        option: DecisionOption,
        criteria: List[DecisionCriteria]
    ) -> DecisionEvaluation:
        """Process LLM evaluation response into structured evaluation."""
        
        try:
            if llm_response.get("parsing_success"):
                structured = llm_response["structured_response"]
                
                # Extract and validate criteria scores
                criteria_scores = {}
                for criterion in criteria:
                    score = structured.get("criteria_scores", {}).get(criterion.name, 0.5)
                    criteria_scores[criterion.name] = max(0.0, min(1.0, float(score)))
                
                # Calculate weighted overall score
                overall_score = sum(
                    criteria_scores.get(criterion.name, 0.0) * criterion.weight
                    for criterion in criteria
                )
                
                return DecisionEvaluation(
                    option_name=option.name,
                    overall_score=overall_score,
                    criteria_scores=criteria_scores,
                    strengths=structured.get("strengths", [])[:15],  # Limit items
                    weaknesses=structured.get("weaknesses", [])[:15],
                    risk_factors=structured.get("risk_factors", [])[:10],
                    implementation_considerations=structured.get("implementation_considerations", [])[:10]
                )
            else:
                # Fallback parsing
                return self._parse_fallback_evaluation(llm_response.get("response", ""), option, criteria)
                
        except Exception as e:
            logger.error("Error processing evaluation response", 
                        option_name=option.name, error=str(e))
            
            return self._create_fallback_evaluation(option, criteria, str(e))
    
    def _parse_fallback_evaluation(
        self,
        raw_response: str,
        option: DecisionOption,
        criteria: List[DecisionCriteria]
    ) -> DecisionEvaluation:
        """Fallback parsing when structured response fails."""
        
        # Heuristic scoring based on response content
        lines = raw_response.lower().split('\n')
        
        criteria_scores = {}
        for criterion in criteria:
            # Look for criterion mentions and nearby scores
            score = 0.5  # Default neutral score
            criterion_lower = criterion.name.lower()
            
            for line in lines:
                if criterion_lower in line and any(char.isdigit() for char in line):
                    # Extract numbers from the line
                    numbers = []
                    for word in line.split():
                        try:
                            if '.' in word:
                                num = float(word.strip('()[]{},.'))
                                if 0 <= num <= 1:
                                    numbers.append(num)
                            elif word.isdigit():
                                num = int(word)
                                if 0 <= num <= 10:
                                    numbers.append(num / 10.0)  # Normalize to 0-1
                        except ValueError:
                            continue
                    
                    if numbers:
                        score = numbers[0]
                        break
            
            criteria_scores[criterion.name] = score
        
        # Calculate overall score
        overall_score = sum(
            criteria_scores.get(criterion.name, 0.0) * criterion.weight
            for criterion in criteria
        )
        
        return DecisionEvaluation(
            option_name=option.name,
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            strengths=[f"Option has potential in {option.name}"],
            weaknesses=["Limited analysis due to parsing issues"],
            risk_factors=["Analysis quality uncertain"],
            implementation_considerations=["Requires detailed review"]
        )
    
    def _create_fallback_evaluation(
        self,
        option: DecisionOption,
        criteria: List[DecisionCriteria],
        error_message: str
    ) -> DecisionEvaluation:
        """Create fallback evaluation for failed analysis."""
        
        # Conservative scoring
        criteria_scores = {criterion.name: 0.3 for criterion in criteria}
        overall_score = 0.3
        
        return DecisionEvaluation(
            option_name=option.name,
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            strengths=["Option available for consideration"],
            weaknesses=[f"Analysis error: {error_message}", "Unable to complete full evaluation"],
            risk_factors=["Evaluation uncertainty", "May require manual analysis"],
            implementation_considerations=["Review analysis methodology", "Consider alternative evaluation"]
        )
    
    def _select_recommendation(
        self,
        evaluations: List[DecisionEvaluation]
    ) -> Tuple[str, float]:
        """Select recommended option and calculate confidence score."""
        
        if not evaluations:
            return "No valid options", 0.0
        
        # Sort by overall score
        sorted_evaluations = sorted(evaluations, key=lambda x: x.overall_score, reverse=True)
        top_option = sorted_evaluations[0]
        
        # Calculate confidence based on score separation
        if len(sorted_evaluations) > 1:
            score_gap = top_option.overall_score - sorted_evaluations[1].overall_score
            # Higher confidence with larger gaps
            confidence_score = min(1.0, 0.5 + score_gap * 2.0)
        else:
            # Single option - moderate confidence
            confidence_score = 0.7
        
        # Adjust confidence based on absolute score
        if top_option.overall_score < 0.3:
            confidence_score *= 0.5  # Low confidence for poor options
        elif top_option.overall_score > 0.8:
            confidence_score = min(1.0, confidence_score * 1.2)  # Higher confidence for excellent options
        
        return top_option.option_name, confidence_score
    
    async def _generate_decision_rationale(
        self,
        request: MultiCriteriaDecisionRequest,
        evaluations: List[DecisionEvaluation],
        recommended_option: str,
        request_id: Optional[str] = None
    ) -> str:
        """Generate comprehensive decision rationale."""
        
        # Find recommended evaluation
        recommended_eval = next(
            (e for e in evaluations if e.option_name == recommended_option),
            None
        )
        
        if not recommended_eval:
            return f"Recommendation based on analysis, but detailed rationale unavailable."
        
        rationale_prompt = f"""
        Generate a clear, persuasive rationale for the following decision recommendation:
        
        Decision Context: {request.context}
        
        Recommended Option: {recommended_option}
        Overall Score: {recommended_eval.overall_score:.2f}
        
        Criteria Performance:
        """ + "\n".join([
            f"- {criterion}: {recommended_eval.criteria_scores.get(criterion, 0.0):.2f}"
            for criterion in recommended_eval.criteria_scores.keys()
        ]) + f"""
        
        Key Strengths:
        """ + "\n".join([f"- {strength}" for strength in recommended_eval.strengths[:5]]) + f"""
        
        Alternative Options Considered:
        """ + "\n".join([
            f"- {eval.option_name}: {eval.overall_score:.2f}"
            for eval in evaluations if eval.option_name != recommended_option
        ]) + """
        
        Provide a concise, compelling rationale that explains:
        1. Why this option is the best choice
        2. How it balances the different criteria
        3. What makes it superior to alternatives
        4. Key benefits and value proposition
        
        Keep it professional and fact-based, around 2-3 sentences.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=rationale_prompt,
                system_prompt="You are a decision analyst providing clear recommendations.",
                temperature=0.2,
                request_id=request_id
            )
            
            return llm_response.get("response", f"Recommended based on highest overall score ({recommended_eval.overall_score:.2f}).")
            
        except Exception as e:
            logger.error("Failed to generate decision rationale", error=str(e))
            return f"Recommended based on superior performance across evaluation criteria with {recommended_eval.overall_score:.2%} overall score."
    
    def _perform_sensitivity_analysis(
        self,
        evaluations: List[DecisionEvaluation],
        criteria: List[DecisionCriteria]
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on criteria weights."""
        
        if len(evaluations) < 2:
            return {"message": "Insufficient options for sensitivity analysis"}
        
        # Test weight variations
        sensitivity_results = {}
        
        for criterion in criteria:
            # Test ±20% weight changes
            original_weight = criterion.weight
            
            for variation in [-0.2, 0.2]:
                test_weights = {}
                total_other_weight = 1.0 - original_weight
                
                # Adjust this criterion's weight
                new_weight = max(0.0, min(1.0, original_weight + variation))
                test_weights[criterion.name] = new_weight
                
                # Redistribute remaining weight proportionally
                remaining_weight = 1.0 - new_weight
                for other_criterion in criteria:
                    if other_criterion.name != criterion.name:
                        if total_other_weight > 0:
                            prop_weight = other_criterion.weight / total_other_weight
                            test_weights[other_criterion.name] = remaining_weight * prop_weight
                        else:
                            test_weights[other_criterion.name] = remaining_weight / (len(criteria) - 1)
                
                # Recalculate scores with new weights
                test_rankings = []
                for evaluation in evaluations:
                    new_score = sum(
                        evaluation.criteria_scores.get(crit_name, 0.0) * weight
                        for crit_name, weight in test_weights.items()
                    )
                    test_rankings.append((evaluation.option_name, new_score))
                
                test_rankings.sort(key=lambda x: x[1], reverse=True)
                test_winner = test_rankings[0][0]
                
                key = f"{criterion.name}_{'+' if variation > 0 else '-'}20%"
                sensitivity_results[key] = test_winner
        
        # Analyze stability
        original_winner = max(evaluations, key=lambda x: x.overall_score).option_name
        stable_results = sum(1 for winner in sensitivity_results.values() if winner == original_winner)
        stability_pct = (stable_results / len(sensitivity_results)) * 100 if sensitivity_results else 100
        
        return {
            "weight_variations": sensitivity_results,
            "recommendation_stability": f"{stability_pct:.1f}%",
            "analysis_summary": f"Recommendation remains stable in {stable_results}/{len(sensitivity_results)} weight variation scenarios"
        }
    
    async def _generate_risk_mitigation(
        self,
        request: MultiCriteriaDecisionRequest,
        recommended_option: str,
        evaluations: List[DecisionEvaluation],
        request_id: Optional[str] = None
    ) -> List[str]:
        """Generate risk mitigation strategies for recommended option."""
        
        recommended_eval = next(
            (e for e in evaluations if e.option_name == recommended_option),
            None
        )
        
        if not recommended_eval or not recommended_eval.risk_factors:
            return ["No significant risks identified", "Monitor implementation progress"]
        
        mitigation_prompt = f"""
        Generate specific, actionable risk mitigation strategies for the following decision:
        
        Recommended Option: {recommended_option}
        Context: {request.context}
        
        Identified Risk Factors:
        """ + "\n".join([f"- {risk}" for risk in recommended_eval.risk_factors]) + """
        
        Implementation Considerations:
        """ + "\n".join([f"- {consideration}" for consideration in recommended_eval.implementation_considerations]) + """
        
        Provide 3-5 specific, actionable mitigation strategies that address these risks.
        Focus on practical steps that can be taken to reduce risk and improve success probability.
        Each strategy should be one clear sentence.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=mitigation_prompt,
                system_prompt="You are a risk management expert providing practical mitigation strategies.",
                temperature=0.3,
                request_id=request_id
            )
            
            response_text = llm_response.get("response", "")
            
            # Extract strategies from response
            strategies = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    # Clean up formatting
                    strategy = line.lstrip('-•0123456789. ').strip()
                    if strategy and len(strategy) > 10:
                        strategies.append(strategy)
            
            if not strategies:
                # Fallback strategies
                strategies = [
                    "Monitor progress closely with regular checkpoints",
                    "Develop contingency plans for identified risk scenarios",
                    "Establish clear success metrics and early warning indicators"
                ]
            
            return strategies[:5]  # Limit to 5 strategies
            
        except Exception as e:
            logger.error("Failed to generate risk mitigation strategies", error=str(e))
            return [
                "Implement gradual rollout approach",
                "Establish monitoring and feedback mechanisms", 
                "Prepare contingency plans for major risks",
                "Regular progress reviews and adjustments"
            ]