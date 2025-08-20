"""Multi-step reasoning chain processing engine.

Implements structured reasoning chains with logical consistency validation,
alternative path exploration, and confidence tracking.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
import structlog

from models.requests import ReasoningChainRequest, ReasoningStep, Evidence
from models.responses import ReasoningChainResponse, ReasoningChainResult
from services.ollama_service import OllamaService
from services.redis_service import RedisService

logger = structlog.get_logger(__name__)


class ReasoningEngine:
    """Advanced multi-step reasoning chain processor with logical validation."""
    
    def __init__(
        self,
        ollama_service: OllamaService,
        redis_service: RedisService,
        max_reasoning_steps: int = 10,
        confidence_threshold: float = 0.7
    ):
        self.ollama_service = ollama_service
        self.redis_service = redis_service
        self.max_reasoning_steps = max_reasoning_steps
        self.confidence_threshold = confidence_threshold
        
        # Reasoning patterns for different types
        self.reasoning_patterns = {
            "deductive": "Start with general principles and derive specific conclusions",
            "inductive": "Observe specific cases and generalize to broader patterns",
            "abductive": "Find the best explanation for observed phenomena",
            "mixed": "Combine multiple reasoning approaches as appropriate"
        }
    
    async def process_reasoning_chain(
        self,
        request: ReasoningChainRequest,
        request_id: Optional[str] = None
    ) -> ReasoningChainResponse:
        """Process multi-step reasoning chain with logical validation."""
        start_time = time.time()
        
        logger.info(
            "Starting reasoning chain processing",
            request_id=request_id,
            reasoning_type=request.reasoning_type,
            max_steps=request.max_steps,
            premise=request.initial_premise[:100] + "..." if len(request.initial_premise) > 100 else request.initial_premise
        )
        
        try:
            # Initialize reasoning state
            reasoning_state = await self._initialize_reasoning_state(request, request_id)
            
            # Build reasoning chain step by step
            reasoning_result = await self._build_reasoning_chain(
                request, reasoning_state, request_id
            )
            
            # Perform validation checks
            validation_checks = await self._perform_validation_checks(
                reasoning_result, request, request_id
            )
            
            processing_time = time.time() - start_time
            
            # Record performance metrics
            await self.redis_service.record_performance_metric(
                "reasoning_chain_time_ms",
                processing_time * 1000,
                tags={
                    "reasoning_type": request.reasoning_type,
                    "steps_count": str(len(reasoning_result.steps)),
                    "confidence": f"{reasoning_result.overall_confidence:.2f}"
                }
            )
            
            await self.redis_service.record_performance_metric(
                "reasoning_chain_confidence",
                reasoning_result.overall_confidence,
                tags={"reasoning_type": request.reasoning_type}
            )
            
            # Store reasoning state for potential continuation
            if request_id:
                await self.redis_service.store_reasoning_state(
                    request_id,
                    {
                        "final_result": reasoning_result.dict(),
                        "original_request": request.dict(),
                        "processing_time_ms": processing_time * 1000,
                        "validation_checks": validation_checks
                    }
                )
            
            logger.info(
                "Reasoning chain processing completed",
                request_id=request_id,
                steps_generated=len(reasoning_result.steps),
                overall_confidence=reasoning_result.overall_confidence,
                logical_consistency=reasoning_result.logical_consistency,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
            return ReasoningChainResponse(
                initial_premise=request.initial_premise,
                goal=request.goal,
                result=reasoning_result,
                reasoning_type=request.reasoning_type,
                validation_checks=validation_checks,
                processing_time_ms=round(processing_time * 1000, 2)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Reasoning chain processing failed",
                request_id=request_id,
                error=str(e),
                processing_time_ms=round(processing_time * 1000, 2)
            )
            raise
    
    async def _initialize_reasoning_state(
        self,
        request: ReasoningChainRequest,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize reasoning state with context and evidence."""
        
        state = {
            "premise": request.initial_premise,
            "goal": request.goal,
            "context": request.context or "",
            "reasoning_type": request.reasoning_type,
            "evidence": [e.dict() for e in (request.evidence or [])],
            "max_steps": min(request.max_steps or 10, self.max_reasoning_steps),
            "current_step": 0,
            "steps_history": [],
            "confidence_history": [],
            "assumptions_made": [],
            "alternative_paths": []
        }
        
        # Store initial state in Redis
        if request_id:
            await self.redis_service.store_reasoning_state(request_id, state)
        
        return state
    
    async def _build_reasoning_chain(
        self,
        request: ReasoningChainRequest,
        reasoning_state: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> ReasoningChainResult:
        """Build the reasoning chain step by step."""
        
        steps = []
        current_premise = request.initial_premise
        step_confidences = []
        key_assumptions = []
        potential_flaws = []
        alternative_paths = []
        
        # Generate reasoning steps iteratively
        for step_num in range(1, reasoning_state["max_steps"] + 1):
            logger.debug("Processing reasoning step", 
                        step_number=step_num, request_id=request_id)
            
            # Generate next step
            step_result = await self._generate_reasoning_step(
                current_premise=current_premise,
                goal=request.goal,
                step_number=step_num,
                context=request.context,
                reasoning_type=request.reasoning_type,
                previous_steps=steps,
                evidence=request.evidence,
                request_id=f"{request_id}_step_{step_num}" if request_id else f"step_{step_num}"
            )
            
            if not step_result:
                logger.warning("Failed to generate reasoning step", 
                              step_number=step_num, request_id=request_id)
                break
            
            steps.append(step_result)
            step_confidences.append(step_result.get("confidence", 0.5))
            
            # Collect assumptions and potential issues
            if "assumptions" in step_result:
                key_assumptions.extend(step_result["assumptions"])
            if "potential_flaws" in step_result:
                potential_flaws.extend(step_result["potential_flaws"])
            if "alternatives" in step_result:
                alternative_paths.extend(step_result["alternatives"])
            
            # Update premise for next step
            current_premise = step_result.get("conclusion", current_premise)
            
            # Update reasoning state
            reasoning_state["current_step"] = step_num
            reasoning_state["steps_history"] = steps
            reasoning_state["confidence_history"] = step_confidences
            
            if request_id:
                await self.redis_service.update_reasoning_state(
                    request_id, {"current_step": step_num, "steps_history": steps}
                )
            
            # Check if we've reached the goal
            goal_reached = await self._check_goal_reached(
                current_premise, request.goal, step_result, request_id
            )
            
            if goal_reached:
                logger.info("Reasoning goal reached", 
                           step_number=step_num, request_id=request_id)
                break
        
        # Calculate overall metrics
        overall_confidence = sum(step_confidences) / len(step_confidences) if step_confidences else 0.0
        logical_consistency = await self._calculate_logical_consistency(steps, request_id)
        
        # Generate final conclusion
        final_conclusion = await self._generate_final_conclusion(
            steps, request.goal, request.initial_premise, request_id
        )
        
        return ReasoningChainResult(
            steps=steps,
            final_conclusion=final_conclusion,
            overall_confidence=overall_confidence,
            logical_consistency=logical_consistency,
            key_assumptions=list(set(key_assumptions))[:10],  # Remove duplicates, limit
            potential_flaws=list(set(potential_flaws))[:10],
            alternative_paths=list(set(alternative_paths))[:10]
        )
    
    async def _generate_reasoning_step(
        self,
        current_premise: str,
        goal: str,
        step_number: int,
        context: Optional[str],
        reasoning_type: str,
        previous_steps: List[Dict[str, Any]],
        evidence: Optional[List[Evidence]],
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate a single reasoning step."""
        
        # Build step generation prompt
        step_prompt = self._build_step_prompt(
            current_premise, goal, step_number, context, reasoning_type, previous_steps, evidence
        )
        
        # Request structured response
        response_format = {
            "step": step_number,
            "premise": current_premise,
            "inference": "",
            "conclusion": "",
            "confidence": 0.5,
            "assumptions": [],
            "potential_flaws": [],
            "alternatives": [],
            "reasoning_type_used": reasoning_type
        }
        
        try:
            llm_response = await self.ollama_service.generate_structured_reasoning(
                prompt=step_prompt,
                response_format=response_format,
                system_prompt=f"You are performing {reasoning_type} reasoning. Be logical and precise.",
                request_id=request_id
            )
            
            if llm_response.get("parsing_success"):
                step_result = llm_response["structured_response"]
                step_result["step"] = step_number
                return step_result
            else:
                # Fallback parsing
                return self._parse_fallback_step(
                    llm_response.get("response", ""),
                    step_number,
                    current_premise
                )
                
        except Exception as e:
            logger.error("Failed to generate reasoning step", 
                        step_number=step_number, error=str(e), request_id=request_id)
            return None
    
    def _build_step_prompt(
        self,
        current_premise: str,
        goal: str,
        step_number: int,
        context: Optional[str],
        reasoning_type: str,
        previous_steps: List[Dict[str, Any]],
        evidence: Optional[List[Evidence]]
    ) -> str:
        """Build prompt for reasoning step generation."""
        
        prompt_parts = [
            f"Perform step {step_number} of {reasoning_type} reasoning:",
            f"\nCurrent Premise: {current_premise}",
            f"Goal: {goal}",
        ]
        
        if context:
            prompt_parts.append(f"Context: {context}")
        
        # Add evidence if available
        if evidence:
            prompt_parts.append("\nAvailable Evidence:")
            for i, evid in enumerate(evidence[:5]):  # Limit evidence items
                prompt_parts.append(f"- {evid.content[:100]}{'...' if len(evid.content) > 100 else ''}")
        
        # Add previous steps summary
        if previous_steps:
            prompt_parts.append(f"\nPrevious Steps Summary:")
            for prev_step in previous_steps[-3:]:  # Show last 3 steps
                step_num = prev_step.get("step", "?")
                conclusion = prev_step.get("conclusion", "No conclusion")
                prompt_parts.append(f"Step {step_num}: {conclusion}")
        
        # Add reasoning guidance
        reasoning_guidance = self.reasoning_patterns.get(reasoning_type, "Apply logical reasoning")
        prompt_parts.append(f"\nReasoning Approach: {reasoning_guidance}")
        
        prompt_parts.extend([
            "\nFor this step:",
            "1. Make a clear logical inference from the current premise",
            "2. State any assumptions you're making",
            "3. Identify potential flaws or limitations",
            "4. Consider alternative reasoning paths",
            "5. Provide a confidence score (0.0-1.0) for this step",
            "",
            "Structure your response to show:",
            "- Inference: The logical connection you're making",
            "- Conclusion: What this step concludes",
            "- Assumptions: What you're assuming to be true",
            "- Potential Flaws: Weaknesses in this reasoning",
            "- Alternatives: Other possible reasoning paths",
            "",
            "Be precise and avoid overconfident claims."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_fallback_step(
        self,
        raw_response: str,
        step_number: int,
        current_premise: str
    ) -> Dict[str, Any]:
        """Parse reasoning step when structured response fails."""
        
        lines = raw_response.split('\n')
        
        inference = ""
        conclusion = current_premise  # Default to no change
        confidence = 0.5
        assumptions = []
        potential_flaws = []
        alternatives = []
        
        # Simple extraction logic
        for line in lines:
            line_lower = line.lower().strip()
            
            if line_lower.startswith("inference:") or "inference" in line_lower:
                inference = line.split(":", 1)[-1].strip()
            elif line_lower.startswith("conclusion:") or "conclusion" in line_lower:
                conclusion = line.split(":", 1)[-1].strip()
            elif line_lower.startswith("confidence:") or "confidence" in line_lower:
                # Extract confidence score
                words = line.split()
                for word in words:
                    try:
                        num = float(word.replace(",", "").replace("(", "").replace(")", ""))
                        if 0 <= num <= 1:
                            confidence = num
                            break
                        elif 0 <= num <= 10:
                            confidence = num / 10.0
                            break
                    except ValueError:
                        continue
        
        return {
            "step": step_number,
            "premise": current_premise,
            "inference": inference or f"Logical step {step_number}",
            "conclusion": conclusion,
            "confidence": confidence,
            "assumptions": assumptions,
            "potential_flaws": ["Parsing limitations may affect accuracy"],
            "alternatives": alternatives,
            "reasoning_type_used": "mixed"
        }
    
    async def _check_goal_reached(
        self,
        current_premise: str,
        goal: str,
        step_result: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> bool:
        """Check if the reasoning goal has been reached."""
        
        goal_check_prompt = f"""
        Evaluate if the current reasoning has sufficiently addressed the goal:
        
        Original Goal: {goal}
        Current Conclusion: {current_premise}
        Latest Step: {step_result.get('conclusion', 'No conclusion')}
        
        Has the goal been adequately reached or addressed?
        Consider:
        1. Is the goal directly answered or resolved?
        2. Has sufficient reasoning been provided?
        3. Are the key questions addressed?
        
        Respond with "YES" if goal is reached, "NO" if more steps needed.
        Provide brief explanation.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=goal_check_prompt,
                system_prompt="You are evaluating reasoning completeness. Be objective.",
                temperature=0.1,
                request_id=request_id
            )
            
            response_text = llm_response.get("response", "").upper()
            return "YES" in response_text[:10]  # Check first part of response
            
        except Exception as e:
            logger.error("Failed to check goal reached", error=str(e))
            return False  # Continue reasoning if uncertain
    
    async def _calculate_logical_consistency(
        self,
        steps: List[Dict[str, Any]],
        request_id: Optional[str] = None
    ) -> float:
        """Calculate logical consistency score for the reasoning chain."""
        
        if len(steps) < 2:
            return 1.0  # Single step is consistent by definition
        
        consistency_prompt = f"""
        Evaluate the logical consistency of this reasoning chain:
        
        Reasoning Steps:
        """ + "\n".join([
            f"Step {step.get('step', i+1)}: {step.get('premise', '')} → {step.get('conclusion', '')}"
            for i, step in enumerate(steps)
        ]) + """
        
        Assess:
        1. Do the steps follow logically from each other?
        2. Are there any contradictions between steps?
        3. Are the inferences valid given the premises?
        4. Is the overall chain coherent?
        
        Provide a consistency score from 0.0 (completely inconsistent) to 1.0 (perfectly consistent).
        Focus on logical validity, not factual accuracy.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=consistency_prompt,
                system_prompt="You are a logic expert evaluating reasoning consistency.",
                temperature=0.1,
                request_id=request_id
            )
            
            response_text = llm_response.get("response", "")
            
            # Extract consistency score
            words = response_text.split()
            for word in words:
                try:
                    score = float(word.replace(",", "").replace("(", "").replace(")", ""))
                    if 0 <= score <= 1:
                        return score
                    elif 0 <= score <= 10:
                        return score / 10.0
                except ValueError:
                    continue
            
            # Fallback: heuristic based on response content
            if "consistent" in response_text.lower() and "not" not in response_text.lower():
                return 0.8
            elif "inconsistent" in response_text.lower():
                return 0.3
            else:
                return 0.6
                
        except Exception as e:
            logger.error("Failed to calculate logical consistency", error=str(e))
            return 0.6  # Neutral score on failure
    
    async def _generate_final_conclusion(
        self,
        steps: List[Dict[str, Any]],
        goal: str,
        initial_premise: str,
        request_id: Optional[str] = None
    ) -> str:
        """Generate final conclusion from reasoning chain."""
        
        if not steps:
            return f"No reasoning steps generated. Original premise: {initial_premise}"
        
        conclusion_prompt = f"""
        Synthesize a final conclusion from this reasoning chain:
        
        Initial Premise: {initial_premise}
        Goal: {goal}
        
        Reasoning Steps:
        """ + "\n".join([
            f"{i+1}. {step.get('conclusion', 'No conclusion')}"
            for i, step in enumerate(steps)
        ]) + """
        
        Provide a clear, concise final conclusion that:
        1. Addresses the original goal
        2. Summarizes the key findings
        3. Acknowledges the reasoning process
        4. Is supported by the steps taken
        
        Keep it to 2-3 sentences maximum.
        """
        
        try:
            llm_response = await self.ollama_service.generate_reasoning(
                prompt=conclusion_prompt,
                system_prompt="You are synthesizing a reasoning conclusion. Be clear and accurate.",
                temperature=0.2,
                request_id=request_id
            )
            
            return llm_response.get("response", steps[-1].get("conclusion", initial_premise))
            
        except Exception as e:
            logger.error("Failed to generate final conclusion", error=str(e))
            return steps[-1].get("conclusion", f"Reasoning completed: {initial_premise}")
    
    async def _perform_validation_checks(
        self,
        reasoning_result: ReasoningChainResult,
        request: ReasoningChainRequest,
        request_id: Optional[str] = None
    ) -> List[str]:
        """Perform validation checks on the reasoning chain."""
        
        checks = []
        
        # Check 1: Logical consistency
        if reasoning_result.logical_consistency >= 0.8:
            checks.append("Logical consistency: PASS (high consistency)")
        elif reasoning_result.logical_consistency >= 0.6:
            checks.append("Logical consistency: MODERATE (some inconsistencies noted)")
        else:
            checks.append("Logical consistency: CONCERN (low consistency score)")
        
        # Check 2: Evidence support
        evidence_count = len(request.evidence or [])
        if evidence_count > 0:
            checks.append(f"Evidence support: {evidence_count} evidence items incorporated")
        else:
            checks.append("Evidence support: No external evidence provided")
        
        # Check 3: Assumption tracking
        assumption_count = len(reasoning_result.key_assumptions)
        if assumption_count <= 3:
            checks.append(f"Assumption tracking: {assumption_count} key assumptions identified")
        else:
            checks.append(f"Assumption tracking: CONCERN ({assumption_count} assumptions may indicate complexity)")
        
        # Check 4: Alternative consideration
        alternative_count = len(reasoning_result.alternative_paths)
        if alternative_count > 0:
            checks.append(f"Alternative consideration: {alternative_count} alternative paths explored")
        else:
            checks.append("Alternative consideration: Limited alternative path exploration")
        
        # Check 5: Confidence assessment
        if reasoning_result.overall_confidence >= 0.8:
            checks.append("Confidence assessment: HIGH confidence in reasoning")
        elif reasoning_result.overall_confidence >= 0.6:
            checks.append("Confidence assessment: MODERATE confidence")
        else:
            checks.append("Confidence assessment: LOW confidence - review recommended")
        
        return checks