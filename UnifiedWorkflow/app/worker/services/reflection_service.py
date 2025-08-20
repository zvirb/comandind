"""
Enhanced Reflection Service

Implements sophisticated self-critique and reflection capabilities based on smart_ai.txt research.
Provides structured reflection with persona-based critique, external grounding, and adaptive depth.
Now uses LangGraph for automatic progress monitoring.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.qdrant_service import QdrantService
from worker.smart_ai_models import (
    CritiqueModel, ReflectionPersona, ReflectionDepth, ReflectionCriteria,
    TokenMetrics, ToolCallRecord
)
from worker.graph_types import GraphState
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class ReflectionState(BaseModel):
    """State object for the reflection workflow."""
    # Input data
    state: Dict[str, Any] = Field(default_factory=dict)  # Original GraphState data
    output_to_critique: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    
    # Workflow state data
    external_grounding: List[str] = Field(default_factory=list)
    structured_critique: Dict[str, Any] = Field(default_factory=dict)
    verification_questions: List[str] = Field(default_factory=list)
    criteria_evaluation: Dict[str, Any] = Field(default_factory=dict)
    
    # Results
    critique_model: Optional[Dict[str, Any]] = None
    token_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ReflectionService:
    """
    Advanced reflection service implementing sophisticated self-critique techniques.
    Based on smart_ai.txt research for effective intra-request iteration.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.qdrant_service = QdrantService()
        
        # Persona-specific prompt templates for structured critique
        self.persona_prompts = {
            ReflectionPersona.TEACHER: {
                "role": "You are a helpful teacher who guides students to better understanding.",
                "focus": "pedagogical clarity, learning progression, and conceptual understanding",
                "style": "encouraging yet precise, identifying gaps in understanding"
            },
            ReflectionPersona.EXPERT_REVIEWER: {
                "role": "You are a domain expert conducting a technical peer review.",
                "focus": "technical accuracy, completeness, and professional standards",
                "style": "rigorous and precise, demanding high technical standards"
            },
            ReflectionPersona.DEVILS_ADVOCATE: {
                "role": "You are a critical devils advocate who challenges assumptions.",
                "focus": "potential flaws, edge cases, and alternative perspectives",
                "style": "skeptical and probing, actively looking for problems"
            },
            ReflectionPersona.END_USER: {
                "role": "You are an end user evaluating practical usability.",
                "focus": "practical utility, user experience, and real-world applicability",
                "style": "pragmatic and user-focused, concerned with actual usability"
            },
            ReflectionPersona.QUALITY_ASSURANCE: {
                "role": "You are a QA specialist conducting systematic quality testing.",
                "focus": "systematic error detection, edge cases, and reliability",
                "style": "methodical and thorough, following systematic evaluation criteria"
            }
        }
    
    async def should_trigger_reflection(self, state: GraphState, confidence_score: float) -> bool:
        """
        Determine if reflection should be triggered based on confidence and other factors.
        """
        if not state.reflection_enabled:
            return False
        
        # Check confidence threshold
        if confidence_score < state.reflection_trigger_threshold:
            logger.info(f"Reflection triggered by low confidence: {confidence_score:.2f} < {state.reflection_trigger_threshold:.2f}")
            return True
        
        # Check for error indicators in recent tool calls
        if state.tool_call_history:
            recent_call = state.tool_call_history[-1]
            if not recent_call.success or recent_call.error_message:
                logger.info("Reflection triggered by recent tool error")
                return True
        
        # Check if max reflection cycles reached
        current_reflection_count = len(state.critique_history)
        if current_reflection_count >= state.max_reflection_cycles:
            logger.info(f"Reflection skipped: max cycles reached ({current_reflection_count}/{state.max_reflection_cycles})")
            return False
        
        return False
    
    async def perform_reflection(self, state: GraphState, output_to_critique: str, 
                               context: Dict[str, Any]) -> CritiqueModel:
        """
        Perform sophisticated reflection using the specified persona and depth.
        """
        try:
            logger.info(f"Performing {state.reflection_depth} reflection with {state.reflection_persona} persona")
            
            # Generate external grounding data
            external_grounding = await self._gather_external_grounding(state, output_to_critique, context)
            
            # Generate structured critique
            critique_content = await self._generate_structured_critique(
                state, output_to_critique, context, external_grounding
            )
            
            # Generate verification questions (Chain-of-Verification technique)
            verification_questions = await self._generate_verification_questions(
                state, output_to_critique, critique_content
            )
            
            # Evaluate against specific criteria
            criteria_evaluation = await self._evaluate_criteria(
                state, output_to_critique, context, critique_content
            )
            
            # Create comprehensive critique model
            critique = CritiqueModel(
                critique_id=str(uuid.uuid4()),
                critique_text=critique_content["critique_text"],
                criticized_output_id=context.get("output_id"),
                reflection_persona=state.reflection_persona,
                reflection_depth=state.reflection_depth,
                external_grounding=external_grounding,
                verification_questions=verification_questions,
                criteria_evaluation=criteria_evaluation,
                suggested_revisions=critique_content.get("suggested_revisions", []),
                specific_issues=critique_content.get("specific_issues", []),
                missing_elements=critique_content.get("missing_elements", []),
                confidence_before=context.get("confidence_before", 0.5),
                confidence_after=critique_content.get("confidence_after", 0.5),
                retry_recommended=critique_content.get("retry_recommended", False),
                retry_strategy=critique_content.get("retry_strategy"),
                actionability_score=critique_content.get("actionability_score", 0.7)
            )
            
            logger.info(f"Reflection complete. Actionability: {critique.actionability_score:.2f}, Retry: {critique.retry_recommended}")
            return critique
            
        except Exception as e:
            logger.error(f"Error in reflection: {e}", exc_info=True)
            # Return minimal critique on error
            return CritiqueModel(
                critique_id=str(uuid.uuid4()),
                critique_text=f"Reflection error: {str(e)}",
                reflection_persona=state.reflection_persona,
                reflection_depth=ReflectionDepth.BASIC,
                confidence_before=context.get("confidence_before", 0.5),
                confidence_after=0.3,  # Lower confidence due to error
                retry_recommended=True,
                actionability_score=0.2
            )
    
    async def _gather_external_grounding(self, state: GraphState, output_to_critique: str, 
                                       context: Dict[str, Any]) -> List[str]:
        """
        Gather external data to ground the critique in factual observations.
        """
        grounding_data = []
        
        try:
            # Tool error messages (highest priority grounding)
            if state.tool_call_history:
                recent_call = state.tool_call_history[-1]
                if recent_call.error_message:
                    grounding_data.append(f"Tool Error: {recent_call.error_message}")
                
                # Tool output details
                if recent_call.output_result:
                    result_str = json.dumps(recent_call.output_result, indent=2)[:200]
                    grounding_data.append(f"Tool Output: {result_str}")
            
            # User context and constraints
            if context.get("user_context"):
                grounding_data.append(f"User Context: {context['user_context']}")
            
            # Previous critique lessons (correction memory)
            similar_critiques = await self._retrieve_similar_critiques(state, output_to_critique)
            for critique_info in similar_critiques[:3]:  # Top 3 similar
                grounding_data.append(f"Similar Past Issue: {critique_info}")
            
            # Current step information
            if state.plan and state.plan_step < len(state.plan):
                current_step = state.plan[state.plan_step]
                grounding_data.append(f"Current Step Goal: {current_step}")
            
            logger.debug(f"Gathered {len(grounding_data)} external grounding points")
            return grounding_data
            
        except Exception as e:
            logger.warning(f"Error gathering external grounding: {e}")
            return ["External grounding unavailable due to error"]
    
    async def _generate_structured_critique(self, state: GraphState, output_to_critique: str,
                                          context: Dict[str, Any], external_grounding: List[str]) -> Dict[str, Any]:
        """
        Generate structured critique using persona-based prompting and external grounding.
        """
        persona_config = self.persona_prompts[state.reflection_persona]
        grounding_text = "\n".join([f"- {item}" for item in external_grounding])
        
        # Depth-specific prompt adjustments
        depth_instructions = {
            ReflectionDepth.BASIC: "Perform a quick validation focusing on obvious errors and completeness.",
            ReflectionDepth.MODERATE: "Conduct a thorough analysis against specific criteria with external grounding.",
            ReflectionDepth.DEEP: "Perform comprehensive multi-perspective analysis considering edge cases and alternatives."
        }
        
        critique_prompt = f"""
{persona_config['role']}

**YOUR TASK:** Critically evaluate the following output with focus on {persona_config['focus']}.
**EVALUATION STYLE:** {persona_config['style']}
**ANALYSIS DEPTH:** {depth_instructions[state.reflection_depth]}

**OUTPUT TO CRITIQUE:**
{output_to_critique}

**EXTERNAL GROUNDING DATA:**
{grounding_text}

**USER CONTEXT:** {context.get('user_context', 'Not provided')}
**CONFIDENCE BEFORE CRITIQUE:** {context.get('confidence_before', 0.5)}

**EVALUATION CRITERIA:**
1. **Accuracy**: Is the output factually correct and free from errors?
2. **Completeness**: Does it fully address the user's request?
3. **Logical Consistency**: Are there any logical contradictions or gaps?
4. **Constraint Adherence**: Does it follow any specified constraints?
5. **Tool Appropriateness**: Were the right tools used correctly?
6. **User Intent Alignment**: Does it align with what the user actually wanted?

**SPECIFIC TASKS:**
1. Identify specific issues (be precise, not generic)
2. Point out missing elements that should be included
3. Suggest concrete revisions for improvement
4. Assess your confidence in the original output (0-1 scale)
5. Determine if a retry is recommended and what strategy to use

**OUTPUT FORMAT (JSON only):**
{{
  "critique_text": "detailed critique as {state.reflection_persona.value}",
  "specific_issues": ["issue 1", "issue 2", "issue 3"],
  "missing_elements": ["missing 1", "missing 2"],
  "suggested_revisions": ["revision 1", "revision 2"],
  "confidence_after": 0.0-1.0,
  "retry_recommended": boolean,
  "retry_strategy": "specific strategy if retry recommended",
  "actionability_score": 0.0-1.0
}}

Perform the critique and respond with JSON only:"""

        try:
            model = state.reflection_model or state.chat_model or "llama3.2:3b"
            
            messages = [
                {"role": "system", "content": f"You are a {state.reflection_persona.value} providing structured critique. Always respond with valid JSON only."},
                {"role": "user", "content": critique_prompt}
            ]
            
            response, tokens = await invoke_llm_with_tokens(
                messages, model, category="reflection"
            )
            
            # Update token tracking
            state.token_usage.add_tokens(tokens.input_tokens, tokens.output_tokens, "reflection")
            
            try:
                critique_data = json.loads(response)
                logger.debug(f"Generated structured critique with {len(critique_data.get('specific_issues', []))} issues")
                return critique_data
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse critique JSON: {e}")
                return {
                    "critique_text": response[:500],  # Fallback to raw response
                    "specific_issues": ["JSON parsing failed"],
                    "missing_elements": [],
                    "suggested_revisions": ["Improve response format"],
                    "confidence_after": 0.4,
                    "retry_recommended": True,
                    "retry_strategy": "Fix output format",
                    "actionability_score": 0.5
                }
                
        except Exception as e:
            logger.error(f"Error generating structured critique: {e}")
            return {
                "critique_text": f"Critique generation failed: {str(e)}",
                "specific_issues": ["Critique generation error"],
                "missing_elements": [],
                "suggested_revisions": [],
                "confidence_after": 0.3,
                "retry_recommended": True,
                "retry_strategy": "Investigate critique generation error",
                "actionability_score": 0.2
            }
    
    async def _generate_verification_questions(self, state: GraphState, output_to_critique: str, 
                                             critique_content: Dict[str, Any]) -> List[str]:
        """
        Generate verification questions using Chain-of-Verification (CoVe) technique.
        """
        try:
            verification_prompt = f"""Generate 3-5 specific verification questions that could be used to validate the accuracy and completeness of this output.

**OUTPUT TO VERIFY:** {output_to_critique[:300]}...
**IDENTIFIED ISSUES:** {', '.join(critique_content.get('specific_issues', []))}

**REQUIREMENTS:**
- Questions should be specific and answerable
- Focus on the most critical aspects for validation
- Help identify potential errors or omissions
- Be practical to verify with available tools

**FORMAT:** Return as a JSON array of strings.

Generate verification questions:"""

            model = state.reflection_model or "llama3.2:3b"
            messages = [
                {"role": "system", "content": "Generate specific verification questions as JSON array."},
                {"role": "user", "content": verification_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(messages, model, category="reflection")
            
            try:
                questions = json.loads(response)
                if isinstance(questions, list):
                    return questions[:5]  # Limit to 5 questions
                else:
                    return ["Verification question generation failed - invalid format"]
            except json.JSONDecodeError:
                # Fallback: extract questions from text
                lines = response.split('\n')
                questions = [line.strip() for line in lines if line.strip() and ('?' in line)]
                return questions[:5]
                
        except Exception as e:
            logger.warning(f"Error generating verification questions: {e}")
            return ["Could not generate verification questions"]
    
    async def _evaluate_criteria(self, state: GraphState, output_to_critique: str,
                                context: Dict[str, Any], critique_content: Dict[str, Any]) -> ReflectionCriteria:
        """
        Evaluate output against specific criteria for structured assessment.
        """
        try:
            criteria_prompt = f"""Evaluate this output against specific criteria. Rate each criterion from 0.0 (poor) to 1.0 (excellent).

**OUTPUT:** {output_to_critique[:200]}...
**CONTEXT:** {context.get('user_context', 'Not provided')}
**IDENTIFIED ISSUES:** {', '.join(critique_content.get('specific_issues', []))}

**CRITERIA TO EVALUATE:**
1. **accuracy**: Factual correctness and freedom from errors
2. **completeness**: Fully addresses the user's request  
3. **logical_consistency**: No contradictions or logical gaps
4. **adherence_to_constraints**: Follows specified constraints
5. **tool_appropriateness**: Correct tool selection and usage
6. **user_intent_alignment**: Matches what user actually wanted

**OUTPUT FORMAT (JSON only):**
{{
  "accuracy": 0.0-1.0,
  "completeness": 0.0-1.0,
  "logical_consistency": 0.0-1.0,
  "adherence_to_constraints": 0.0-1.0,
  "tool_appropriateness": 0.0-1.0,
  "user_intent_alignment": 0.0-1.0
}}

Evaluate and respond with JSON only:"""

            model = state.reflection_model or "llama3.2:3b"
            messages = [
                {"role": "system", "content": "Evaluate output against criteria. Respond with JSON only."},
                {"role": "user", "content": criteria_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(messages, model, category="reflection")
            
            try:
                criteria_data = json.loads(response)
                return ReflectionCriteria(**criteria_data)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Failed to parse criteria evaluation, using defaults")
                return ReflectionCriteria()
                
        except Exception as e:
            logger.warning(f"Error evaluating criteria: {e}")
            return ReflectionCriteria()
    
    async def _retrieve_similar_critiques(self, state: GraphState, output_to_critique: str) -> List[str]:
        """
        Retrieve similar past critiques from correction memory for learning.
        """
        try:
            if not state.user_id:
                return []
            
            # Search for similar critiques in Qdrant
            search_results = await self.qdrant_service.search_points(
                query_text=output_to_critique[:200],  # Use first part of output for similarity
                limit=3,
                user_id=int(state.user_id),
                content_types=["critique", "correction"]
            )
            
            similar_critiques = []
            for result in search_results:
                if hasattr(result, 'payload') and result.payload:
                    critique_text = result.payload.get('text', '')
                    if critique_text:
                        similar_critiques.append(critique_text[:100] + "...")
            
            return similar_critiques
            
        except Exception as e:
            logger.debug(f"Could not retrieve similar critiques: {e}")
            return []

    async def perform_reflection_with_progress(self, state: GraphState, output_to_critique: str, 
                                             context: Dict[str, Any]) -> CritiqueModel:
        """
        Perform sophisticated reflection using LangGraph with automatic progress monitoring.
        
        Args:
            state: Current graph state
            output_to_critique: The output to critique
            context: Additional context for the reflection
            
        Returns:
            CritiqueModel: Comprehensive critique results
        """
        try:
            # Create reflection state
            reflection_state = ReflectionState(
                state=state.__dict__ if hasattr(state, '__dict__') else {},
                output_to_critique=output_to_critique,
                context=context,
                session_id=state.session_id
            )
            
            logger.info(f"Starting LangGraph reflection with {state.reflection_persona} persona")
            
            # Get progress manager for automatic broadcasting
            from worker.services.progress_manager import progress_manager
            
            # Broadcast workflow start
            if state.session_id:
                await progress_manager.broadcast_workflow_start(
                    state.session_id, 
                    f"Reflection analysis with {state.reflection_persona.value} persona"
                )
            
            # Run the reflection workflow with astream for progress monitoring
            config = RunnableConfig(recursion_limit=10)
            workflow_start_time = datetime.now()
            nodes_executed = 0
            
            final_state = None
            async for event in compiled_reflection_workflow.astream(reflection_state.model_dump(), config=config):
                nodes_executed += 1
                
                for node_name, node_state in event.items():
                    # Broadcast automatic progress update for this node
                    if state.session_id:
                        try:
                            node_execution_time = (datetime.now() - workflow_start_time).total_seconds()
                            await progress_manager.broadcast_node_transition(
                                state.session_id, f"reflection_{node_name}", node_state, node_execution_time
                            )
                            logger.debug(f"Broadcasted reflection progress for node: {node_name}")
                        except Exception as e:
                            logger.warning(f"Failed to broadcast reflection progress for {node_name}: {e}")
                
                # Store the final state
                final_state = event
            
            # Calculate total execution time
            total_execution_time = (datetime.now() - workflow_start_time).total_seconds()
            
            # Extract final results from the last state
            if final_state:
                last_key = list(final_state.keys())[-1]
                final_reflection_state = final_state[last_key]
                
                # Broadcast workflow completion
                if state.session_id:
                    critique_summary = final_reflection_state.get("critique_model", {}).get("critique_text", "Reflection completed")
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id, 
                        f"Reflection complete: {critique_summary[:50]}...",
                        total_execution_time, 
                        nodes_executed
                    )
                
                # Convert result to CritiqueModel
                critique_data = final_reflection_state.get("critique_model", {})
                if critique_data:
                    return CritiqueModel(**critique_data)
                else:
                    # Fallback critique
                    return CritiqueModel(
                        critique_id=str(uuid.uuid4()),
                        critique_text="Reflection workflow completed with no critique data",
                        reflection_persona=state.reflection_persona,
                        reflection_depth=ReflectionDepth.BASIC,
                        confidence_before=context.get("confidence_before", 0.5),
                        confidence_after=0.5,
                        retry_recommended=False,
                        actionability_score=0.5
                    )
            else:
                # Fallback if no final state
                logger.warning("No final state from reflection workflow")
                return CritiqueModel(
                    critique_id=str(uuid.uuid4()),
                    critique_text="Reflection workflow completed with no final state",
                    reflection_persona=state.reflection_persona,
                    reflection_depth=ReflectionDepth.BASIC,
                    confidence_before=context.get("confidence_before", 0.5),
                    confidence_after=0.4,
                    retry_recommended=False,
                    actionability_score=0.3
                )
            
        except Exception as e:
            logger.error(f"Error in LangGraph reflection workflow: {e}", exc_info=True)
            
            # Broadcast error if possible
            if state.session_id:
                try:
                    from worker.services.progress_manager import progress_manager
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id,
                        f"Reflection failed: {str(e)}",
                        0.0,
                        0
                    )
                except:
                    pass
            
            # Fallback to original method
            logger.info("Falling back to original reflection method")
            return await self.perform_reflection(state, output_to_critique, context)


# --- LangGraph Workflow Nodes ---

async def gather_external_grounding_node(state: ReflectionState) -> Dict[str, Any]:
    """Gather external data to ground the critique in factual observations."""
    try:
        service = reflection_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        grounding_data = await service._gather_external_grounding(
            mock_state, state.output_to_critique, state.context
        )
        
        return {"external_grounding": grounding_data}
        
    except Exception as e:
        logger.error(f"Error gathering external grounding: {e}")
        return {"external_grounding": [f"Grounding error: {str(e)}"]}


async def generate_structured_critique_node(state: ReflectionState) -> Dict[str, Any]:
    """Generate structured critique using persona-based prompting."""
    try:
        service = reflection_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        critique_content = await service._generate_structured_critique(
            mock_state, state.output_to_critique, state.context, state.external_grounding
        )
        
        return {"structured_critique": critique_content}
        
    except Exception as e:
        logger.error(f"Error generating structured critique: {e}")
        return {
            "structured_critique": {
                "critique_text": f"Critique generation error: {str(e)}",
                "specific_issues": ["Critique generation failed"],
                "missing_elements": [],
                "suggested_revisions": [],
                "confidence_after": 0.3,
                "retry_recommended": True,
                "retry_strategy": "Fix critique generation",
                "actionability_score": 0.2
            }
        }


async def generate_verification_questions_node(state: ReflectionState) -> Dict[str, Any]:
    """Generate verification questions using Chain-of-Verification technique."""
    try:
        service = reflection_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        verification_questions = await service._generate_verification_questions(
            mock_state, state.output_to_critique, state.structured_critique
        )
        
        return {"verification_questions": verification_questions}
        
    except Exception as e:
        logger.error(f"Error generating verification questions: {e}")
        return {"verification_questions": [f"Verification error: {str(e)}"]}


async def evaluate_criteria_node(state: ReflectionState) -> Dict[str, Any]:
    """Evaluate output against specific criteria for structured assessment."""
    try:
        service = reflection_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        criteria_evaluation = await service._evaluate_criteria(
            mock_state, state.output_to_critique, state.context, state.structured_critique
        )
        
        return {"criteria_evaluation": criteria_evaluation.model_dump()}
        
    except Exception as e:
        logger.error(f"Error evaluating criteria: {e}")
        return {"criteria_evaluation": ReflectionCriteria().model_dump()}


async def create_critique_model_node(state: ReflectionState) -> Dict[str, Any]:
    """Create the final CritiqueModel from all gathered information."""
    try:
        # Extract persona and depth from state
        persona_value = state.state.get("reflection_persona", ReflectionPersona.EXPERT_REVIEWER.value)
        if isinstance(persona_value, str):
            persona = ReflectionPersona(persona_value)
        else:
            persona = persona_value

        depth_value = state.state.get("reflection_depth", ReflectionDepth.MODERATE.value)
        if isinstance(depth_value, str):
            depth = ReflectionDepth(depth_value)
        else:
            depth = depth_value

        # Create comprehensive critique model
        critique_model_data = {
            "critique_id": str(uuid.uuid4()),
            "critique_text": state.structured_critique.get("critique_text", "No critique generated"),
            "criticized_output_id": state.context.get("output_id"),
            "reflection_persona": persona,
            "reflection_depth": depth,
            "external_grounding": state.external_grounding,
            "verification_questions": state.verification_questions,
            "criteria_evaluation": ReflectionCriteria(**state.criteria_evaluation),
            "suggested_revisions": state.structured_critique.get("suggested_revisions", []),
            "specific_issues": state.structured_critique.get("specific_issues", []),
            "missing_elements": state.structured_critique.get("missing_elements", []),
            "confidence_before": state.context.get("confidence_before", 0.5),
            "confidence_after": state.structured_critique.get("confidence_after", 0.5),
            "retry_recommended": state.structured_critique.get("retry_recommended", False),
            "retry_strategy": state.structured_critique.get("retry_strategy"),
            "actionability_score": state.structured_critique.get("actionability_score", 0.7)
        }
        
        return {"critique_model": critique_model_data}
        
    except Exception as e:
        logger.error(f"Error creating critique model: {e}")
        fallback_model = {
            "critique_id": str(uuid.uuid4()),
            "critique_text": f"Critique model creation error: {str(e)}",
            "reflection_persona": ReflectionPersona.EXPERT_REVIEWER,
            "reflection_depth": ReflectionDepth.BASIC,
            "confidence_before": state.context.get("confidence_before", 0.5),
            "confidence_after": 0.3,
            "retry_recommended": True,
            "actionability_score": 0.2
        }
        return {"critique_model": fallback_model}


def should_continue_reflection(state: ReflectionState) -> str:
    """Decide whether to continue the reflection workflow or end due to errors."""
    if state.error_message:
        logger.info(f"Stopping reflection due to error: {state.error_message}")
        return "__end__"
    
    if not state.external_grounding:
        logger.info("No external grounding available, ending workflow")
        return "__end__"
        
    return "generate_structured_critique"


# Create the reflection workflow graph
reflection_workflow = StateGraph(ReflectionState)

# Add nodes
reflection_workflow.add_node("gather_grounding", RunnableLambda(gather_external_grounding_node))  # type: ignore
reflection_workflow.add_node("generate_structured_critique", RunnableLambda(generate_structured_critique_node))  # type: ignore
reflection_workflow.add_node("generate_verification_questions", RunnableLambda(generate_verification_questions_node))  # type: ignore
reflection_workflow.add_node("evaluate_criteria", RunnableLambda(evaluate_criteria_node))  # type: ignore
reflection_workflow.add_node("create_critique_model", RunnableLambda(create_critique_model_node))  # type: ignore

# Set entry point
reflection_workflow.set_entry_point("gather_grounding")

# Add edges
reflection_workflow.add_conditional_edges(
    "gather_grounding",
    should_continue_reflection,
    {
        "generate_structured_critique": "generate_structured_critique",
        "__end__": END
    }
)
reflection_workflow.add_edge("generate_structured_critique", "generate_verification_questions")
reflection_workflow.add_edge("generate_verification_questions", "evaluate_criteria")
reflection_workflow.add_edge("evaluate_criteria", "create_critique_model")
reflection_workflow.add_edge("create_critique_model", END)

# Compile the workflow
compiled_reflection_workflow = reflection_workflow.compile()


# Global instance
reflection_service = ReflectionService()