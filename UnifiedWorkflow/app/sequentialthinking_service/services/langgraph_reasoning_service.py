"""
LangGraph-based reasoning service with Redis checkpointing and self-healing
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple, TypedDict, Annotated
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from ..config import get_settings
from ..models import (
    ReasoningRequest, ReasoningResponse, ThoughtStep, ReasoningState,
    ErrorContext, ErrorType, RecoveryPlan, ThoughtStatus
)
from .redis_checkpoint_service import RedisCheckpointService
from .ollama_client_service import OllamaClientService
from .memory_integration_service import MemoryIntegrationService

logger = logging.getLogger(__name__)
settings = get_settings()


class ReasoningGraphState(TypedDict):
    """State structure for the reasoning graph"""
    session_id: str
    original_query: str
    current_step: int
    max_steps: int
    reasoning_steps: List[Dict[str, Any]]
    current_thought: str
    final_answer: Optional[str]
    confidence_score: float
    
    # Context and memory
    context_items: List[Dict[str, Any]]
    memory_integration_enabled: bool
    
    # Error handling
    error_count: int
    last_error: Optional[Dict[str, Any]]
    recovery_plan: Optional[Dict[str, Any]]
    
    # Control flags
    needs_more_steps: bool
    validation_required: bool
    self_correction_enabled: bool
    
    # Metadata
    user_id: Optional[str]
    started_at: str
    processing_times: List[int]
    models_used: List[str]
    

class LangGraphReasoningService:
    """
    Advanced reasoning service using LangGraph with self-healing capabilities
    """
    
    def __init__(self):
        self.redis_checkpoint: Optional[RedisCheckpointService] = None
        self.ollama_client: Optional[OllamaClientService] = None
        self.memory_service: Optional[MemoryIntegrationService] = None
        
        self.reasoning_graph: Optional[StateGraph] = None
        self.compiled_graph = None
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(
        self, 
        redis_checkpoint: RedisCheckpointService,
        ollama_client: OllamaClientService, 
        memory_service: MemoryIntegrationService
    ) -> None:
        """Initialize the reasoning service with dependencies"""
        try:
            self.redis_checkpoint = redis_checkpoint
            self.ollama_client = ollama_client
            self.memory_service = memory_service
            
            # Build and compile the reasoning graph
            self._build_reasoning_graph()
            
            logger.info("LangGraph reasoning service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph reasoning service: {e}")
            raise
    
    def _build_reasoning_graph(self) -> None:
        """Build the self-healing reasoning graph"""
        
        # Define the state graph
        workflow = StateGraph(ReasoningGraphState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("thinker", self._thinking_node)
        workflow.add_node("validator", self._validation_node)
        workflow.add_node("memory_integrator", self._memory_integration_node)
        workflow.add_node("error_handler", self._error_handling_node)
        workflow.add_node("recovery_planner", self._recovery_planning_node)
        workflow.add_node("finalizer", self._finalization_node)
        
        # Define entry point
        workflow.set_entry_point("planner")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "planner",
            self._should_integrate_memory,
            {
                "integrate_memory": "memory_integrator",
                "start_thinking": "thinker"
            }
        )
        
        workflow.add_edge("memory_integrator", "thinker")
        
        workflow.add_conditional_edges(
            "thinker",
            self._thinking_decision,
            {
                "continue_thinking": "thinker",
                "validate": "validator", 
                "error": "error_handler",
                "complete": "finalizer"
            }
        )
        
        workflow.add_conditional_edges(
            "validator",
            self._validation_decision,
            {
                "valid": "finalizer",
                "needs_correction": "thinker",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "error_handler",
            self._error_recovery_decision,
            {
                "retry": "thinker",
                "plan_recovery": "recovery_planner",
                "give_up": "finalizer"
            }
        )
        
        workflow.add_conditional_edges(
            "recovery_planner", 
            self._recovery_execution_decision,
            {
                "rollback_and_retry": "thinker",
                "context_adjustment": "memory_integrator", 
                "give_up": "finalizer"
            }
        )
        
        workflow.add_edge("finalizer", END)
        
        # Compile with Redis checkpointing
        checkpointer = self.redis_checkpoint.get_checkpoint_saver()
        self.compiled_graph = workflow.compile(checkpointer=checkpointer)
        
        logger.info("Reasoning graph compiled successfully with Redis checkpointing")
    
    async def execute_reasoning(self, request: ReasoningRequest) -> ReasoningResponse:
        """
        Execute sequential reasoning with self-healing capabilities
        
        Args:
            request: Reasoning request with query and parameters
            
        Returns:
            Complete reasoning response with steps and result
        """
        session_id = request.session_id or str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        try:
            # Initialize reasoning state
            initial_state = ReasoningGraphState(
                session_id=session_id,
                original_query=request.query,
                current_step=0,
                max_steps=request.max_steps,
                reasoning_steps=[],
                current_thought="",
                final_answer=None,
                confidence_score=0.5,
                context_items=[],
                memory_integration_enabled=request.enable_memory_integration,
                error_count=0,
                last_error=None,
                recovery_plan=None,
                needs_more_steps=True,
                validation_required=request.enable_self_correction,
                self_correction_enabled=request.enable_self_correction,
                user_id=request.user_id,
                started_at=started_at.isoformat(),
                processing_times=[],
                models_used=[]
            )
            
            # Store active session
            self._active_sessions[session_id] = {
                "request": request,
                "started_at": started_at,
                "state": "running"
            }
            
            # Execute the reasoning graph
            config = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": request.max_steps * 3  # Allow for retries
            }
            
            final_state = None
            step_count = 0
            
            # Execute graph with step-by-step processing
            async for state in self.compiled_graph.astream(initial_state, config):
                step_count += 1
                final_state = state
                
                # Update session tracking
                if session_id in self._active_sessions:
                    self._active_sessions[session_id]["last_update"] = datetime.utcnow()
                
                # Prevent infinite loops
                if step_count > request.max_steps * 5:
                    logger.warning(f"Reasoning session {session_id} exceeded maximum iterations")
                    break
            
            if not final_state:
                raise RuntimeError("Reasoning graph execution produced no final state")
            
            # Build response from final state
            response = self._build_response(final_state, started_at)
            
            # Store successful reasoning outcome
            if response.success and self.memory_service:
                await self.memory_service.store_reasoning_outcome(
                    query=request.query,
                    reasoning_steps=[step.thought for step in response.reasoning_steps],
                    final_answer=response.final_answer or "No final answer",
                    success=response.success,
                    user_id=request.user_id
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Reasoning execution failed for session {session_id}: {e}")
            
            # Create error response
            error_response = ReasoningResponse(
                session_id=session_id,
                query=request.query,
                state=ReasoningState.FAILED,
                confidence_score=0.0,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_context=ErrorContext(
                    error_type=ErrorType.RESOURCE_ERROR,
                    error_message=str(e),
                    timestamp=datetime.utcnow()
                )
            )
            
            return error_response
            
        finally:
            # Clean up session tracking
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
    
    # Graph Node Implementations
    
    async def _planner_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Planning node - analyzes query and prepares reasoning strategy"""
        
        logger.debug(f"Planning reasoning for session {state['session_id']}")
        
        try:
            # Analyze query complexity and create initial plan
            planning_prompt = f"""
            Analyze this query and create a reasoning strategy:
            
            Query: {state['original_query']}
            
            Please provide:
            1. What type of reasoning is needed?
            2. What are the key components to address?
            3. What approach would be most effective?
            4. How many steps might this reasonably take?
            
            Provide a brief analysis to guide the reasoning process.
            """
            
            planning_result = await self.ollama_client.generate_reasoning_step(
                planning_prompt,
                {"task": "planning", "session_id": state["session_id"]}
            )
            
            # Add planning step
            planning_step = ThoughtStep(
                step_number=0,
                thought=f"Planning: {planning_result['content']}",
                status=ThoughtStatus.COMPLETED,
                confidence=planning_result["confidence"],
                model_used=planning_result["model_used"],
                processing_time_ms=planning_result["processing_time_ms"]
            )
            
            # Update state
            state["reasoning_steps"].append(planning_step.dict())
            state["processing_times"].append(planning_result["processing_time_ms"])
            state["models_used"].append(planning_result["model_used"])
            
            return state
            
        except Exception as e:
            logger.error(f"Planning node error: {e}")
            state["error_count"] += 1
            state["last_error"] = {
                "type": ErrorType.MODEL_ERROR,
                "message": str(e),
                "node": "planner"
            }
            return state
    
    async def _memory_integration_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Memory integration node - retrieves relevant context"""
        
        logger.debug(f"Integrating memory for session {state['session_id']}")
        
        try:
            if self.memory_service and state["memory_integration_enabled"]:
                # Get relevant context from memory service
                context_result = await self.memory_service.get_relevant_context(
                    query=state["original_query"],
                    user_id=state["user_id"],
                    context_limit=3,
                    similarity_threshold=0.7
                )
                
                state["context_items"] = context_result.get("context_items", [])
                
                # Add memory integration step
                memory_step = ThoughtStep(
                    step_number=len(state["reasoning_steps"]),
                    thought=f"Memory Integration: Found {len(state['context_items'])} relevant context items",
                    status=ThoughtStatus.COMPLETED,
                    context_used=context_result.get("sources", []),
                    confidence=0.8
                )
                
                state["reasoning_steps"].append(memory_step.dict())
            
            return state
            
        except Exception as e:
            logger.error(f"Memory integration error: {e}")
            # Don't fail the entire reasoning for memory errors
            return state
    
    async def _thinking_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Core thinking node - performs reasoning steps"""
        
        current_step = state["current_step"] + 1
        logger.debug(f"Thinking step {current_step} for session {state['session_id']}")
        
        try:
            # Build reasoning prompt with context
            thinking_prompt = self._build_thinking_prompt(state, current_step)
            
            # Generate reasoning step
            reasoning_result = await self.ollama_client.generate_reasoning_step(
                thinking_prompt,
                {"task": "reasoning", "step": current_step, "session_id": state["session_id"]}
            )
            
            # Create thought step
            thought_step = ThoughtStep(
                step_number=current_step,
                thought=reasoning_result["content"],
                status=ThoughtStatus.COMPLETED,
                confidence=reasoning_result["confidence"],
                model_used=reasoning_result["model_used"],
                processing_time_ms=reasoning_result["processing_time_ms"]
            )
            
            # Update state
            state["current_step"] = current_step
            state["current_thought"] = reasoning_result["content"]
            state["reasoning_steps"].append(thought_step.dict())
            state["processing_times"].append(reasoning_result["processing_time_ms"])
            state["models_used"].append(reasoning_result["model_used"])
            
            # Update confidence score (weighted average)
            total_confidence = sum(step.get("confidence", 0.5) for step in state["reasoning_steps"])
            state["confidence_score"] = total_confidence / len(state["reasoning_steps"])
            
            return state
            
        except Exception as e:
            logger.error(f"Thinking node error: {e}")
            state["error_count"] += 1
            state["last_error"] = {
                "type": ErrorType.MODEL_ERROR,
                "message": str(e),
                "node": "thinker",
                "step": current_step
            }
            return state
    
    async def _validation_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Validation node - checks reasoning quality"""
        
        logger.debug(f"Validating reasoning for session {state['session_id']}")
        
        try:
            if not state["validation_required"] or not state["reasoning_steps"]:
                return state
            
            # Extract reasoning steps for validation
            reasoning_steps = [step["thought"] for step in state["reasoning_steps"]]
            
            # Validate reasoning
            validation_result = await self.ollama_client.validate_reasoning(
                original_query=state["original_query"],
                reasoning_steps=reasoning_steps,
                final_answer=state.get("final_answer", "In progress")
            )
            
            # Add validation step
            validation_step = ThoughtStep(
                step_number=len(state["reasoning_steps"]),
                thought=f"Validation: {validation_result['validation_reasoning']}",
                status=ThoughtStatus.COMPLETED,
                confidence=validation_result["confidence"]
            )
            
            state["reasoning_steps"].append(validation_step.dict())
            
            # Update validation status
            if not validation_result["is_valid"] and validation_result["issues"]:
                state["validation_required"] = True
                state["current_thought"] = f"Validation issues found: {'; '.join(validation_result['issues'])}"
            
            return state
            
        except Exception as e:
            logger.error(f"Validation node error: {e}")
            return state
    
    async def _error_handling_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Error handling node - manages errors and recovery"""
        
        logger.debug(f"Handling error for session {state['session_id']}")
        
        try:
            if state["last_error"]:
                error_info = state["last_error"]
                
                # Log error details
                logger.warning(f"Reasoning error in {error_info['node']}: {error_info['message']}")
                
                # Create error context
                error_context = ErrorContext(
                    error_type=ErrorType(error_info["type"]),
                    error_message=error_info["message"],
                    failed_step=error_info.get("step"),
                    retry_count=state["error_count"],
                    timestamp=datetime.utcnow()
                )
                
                # Add error handling step
                error_step = ThoughtStep(
                    step_number=len(state["reasoning_steps"]),
                    thought=f"Error encountered: {error_info['message']}. Retry count: {state['error_count']}",
                    status=ThoughtStatus.FAILED,
                    confidence=0.1
                )
                
                state["reasoning_steps"].append(error_step.dict())
            
            return state
            
        except Exception as e:
            logger.error(f"Error handling node error: {e}")
            return state
    
    async def _recovery_planning_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Recovery planning node - creates recovery strategies"""
        
        logger.debug(f"Planning recovery for session {state['session_id']}")
        
        try:
            if state["last_error"]:
                # Extract failed reasoning for recovery planning
                failed_reasoning = [step["thought"] for step in state["reasoning_steps"]]
                
                # Create error context
                error_context = ErrorContext(
                    error_type=ErrorType(state["last_error"]["type"]),
                    error_message=state["last_error"]["message"],
                    failed_step=state["last_error"].get("step"),
                    retry_count=state["error_count"]
                )
                
                # Generate recovery plan
                recovery_result = await self.ollama_client.generate_recovery_plan(
                    error_context, failed_reasoning
                )
                
                # Store recovery plan
                state["recovery_plan"] = recovery_result
                
                # Add recovery planning step
                recovery_step = ThoughtStep(
                    step_number=len(state["reasoning_steps"]),
                    thought=f"Recovery Plan: {recovery_result['plan_content'][:200]}...",
                    status=ThoughtStatus.COMPLETED,
                    confidence=recovery_result["confidence"]
                )
                
                state["reasoning_steps"].append(recovery_step.dict())
            
            return state
            
        except Exception as e:
            logger.error(f"Recovery planning error: {e}")
            return state
    
    async def _finalization_node(self, state: ReasoningGraphState) -> ReasoningGraphState:
        """Finalization node - concludes reasoning and produces final answer"""
        
        logger.debug(f"Finalizing reasoning for session {state['session_id']}")
        
        try:
            # Generate final answer if not already present
            if not state.get("final_answer"):
                finalization_prompt = f"""
                Based on the following reasoning process, provide a clear, concise final answer:
                
                Original Query: {state['original_query']}
                
                Reasoning Steps:
                {chr(10).join(f"{i+1}. {step['thought']}" for i, step in enumerate(state['reasoning_steps']) if step.get('thought'))}
                
                Please provide a definitive final answer that addresses the original query.
                """
                
                final_result = await self.ollama_client.generate_reasoning_step(
                    finalization_prompt,
                    {"task": "finalization", "session_id": state["session_id"]}
                )
                
                state["final_answer"] = final_result["content"]
                state["models_used"].append(final_result["model_used"])
                state["processing_times"].append(final_result["processing_time_ms"])
            
            # Mark as completed
            state["needs_more_steps"] = False
            
            return state
            
        except Exception as e:
            logger.error(f"Finalization error: {e}")
            state["final_answer"] = f"Reasoning process completed with errors. Last error: {str(e)}"
            return state
    
    # Decision Functions for Conditional Edges
    
    def _should_integrate_memory(self, state: ReasoningGraphState) -> str:
        """Decide whether to integrate memory"""
        if state["memory_integration_enabled"] and self.memory_service:
            return "integrate_memory"
        return "start_thinking"
    
    def _thinking_decision(self, state: ReasoningGraphState) -> str:
        """Decide next action after thinking"""
        
        # Check for errors
        if state["last_error"] and state["error_count"] > 0:
            return "error"
        
        # Check if we need more thinking steps
        if (state["current_step"] < state["max_steps"] and 
            state["needs_more_steps"] and
            not self._is_reasoning_complete(state)):
            return "continue_thinking"
        
        # Check if validation is needed
        if state["validation_required"] and state["self_correction_enabled"]:
            return "validate"
        
        # Otherwise, complete
        return "complete"
    
    def _validation_decision(self, state: ReasoningGraphState) -> str:
        """Decide action after validation"""
        
        # Check for validation errors
        if state["last_error"]:
            return "error"
        
        # Check if reasoning needs correction
        validation_steps = [step for step in state["reasoning_steps"] 
                           if "validation" in step.get("thought", "").lower()]
        
        if validation_steps:
            last_validation = validation_steps[-1]
            if ("issues found" in last_validation.get("thought", "").lower() and 
                state["current_step"] < state["max_steps"]):
                return "needs_correction"
        
        return "valid"
    
    def _error_recovery_decision(self, state: ReasoningGraphState) -> str:
        """Decide recovery strategy after error"""
        
        error_count = state["error_count"]
        max_retries = settings.MAX_RETRY_ATTEMPTS
        
        if error_count < max_retries:
            # Simple retry for first few errors
            if error_count <= 2:
                return "retry"
            else:
                return "plan_recovery"
        else:
            return "give_up"
    
    def _recovery_execution_decision(self, state: ReasoningGraphState) -> str:
        """Decide how to execute recovery plan"""
        
        if state.get("recovery_plan"):
            plan_content = state["recovery_plan"].get("plan_content", "").lower()
            
            if "rollback" in plan_content:
                return "rollback_and_retry"
            elif "context" in plan_content or "memory" in plan_content:
                return "context_adjustment"
        
        return "give_up"
    
    # Helper Methods
    
    def _build_thinking_prompt(self, state: ReasoningGraphState, step: int) -> str:
        """Build a comprehensive thinking prompt"""
        
        context_section = ""
        if state["context_items"]:
            context_items = state["context_items"][:3]  # Limit context
            context_section = f"\n\nRelevant Context:\n"
            for i, item in enumerate(context_items):
                context_section += f"{i+1}. {item.get('content', '')[:200]}...\n"
        
        previous_steps = ""
        if state["reasoning_steps"]:
            previous_steps = f"\n\nPrevious Reasoning Steps:\n"
            for i, step_data in enumerate(state["reasoning_steps"][-3:], 1):  # Last 3 steps
                previous_steps += f"{i}. {step_data.get('thought', '')}\n"
        
        return f"""You are conducting step {step} of a reasoning process.

Original Query: {state['original_query']}

{context_section}{previous_steps}

Please provide the next logical reasoning step. Be specific, clear, and build upon previous insights.

Your reasoning for step {step}:"""
    
    def _is_reasoning_complete(self, state: ReasoningGraphState) -> bool:
        """Check if reasoning is complete"""
        
        if state.get("final_answer"):
            return True
        
        # Check if recent steps suggest completion
        recent_steps = state["reasoning_steps"][-2:] if len(state["reasoning_steps"]) >= 2 else []
        
        for step in recent_steps:
            thought = step.get("thought", "").lower()
            if any(word in thought for word in ["conclusion", "therefore", "final answer", "in summary"]):
                return True
        
        return False
    
    def _build_response(self, final_state: ReasoningGraphState, started_at: datetime) -> ReasoningResponse:
        """Build reasoning response from final state"""
        
        completed_at = datetime.utcnow()
        
        # Convert reasoning steps
        thought_steps = []
        for step_data in final_state["reasoning_steps"]:
            thought_step = ThoughtStep(**step_data)
            thought_steps.append(thought_step)
        
        # Determine final state
        if final_state.get("final_answer"):
            reasoning_state = ReasoningState.COMPLETED
        elif final_state["error_count"] > 0:
            reasoning_state = ReasoningState.FAILED
        else:
            reasoning_state = ReasoningState.COMPLETED
        
        # Build response
        response = ReasoningResponse(
            session_id=final_state["session_id"],
            query=final_state["original_query"],
            final_answer=final_state.get("final_answer"),
            reasoning_steps=thought_steps,
            state=reasoning_state,
            total_steps=len(thought_steps),
            total_processing_time_ms=sum(final_state["processing_times"]),
            model_switches=len(set(final_state["models_used"])),
            error_recoveries=final_state["error_count"],
            confidence_score=final_state["confidence_score"],
            checkpoints_created=final_state["current_step"],  # Approximate
            memory_integrations=1 if final_state["context_items"] else 0,
            started_at=started_at,
            completed_at=completed_at,
            context_sources=[item.get("source", "") for item in final_state["context_items"]]
        )
        
        # Add error context if failed
        if final_state.get("last_error"):
            error_info = final_state["last_error"]
            response.error_context = ErrorContext(
                error_type=ErrorType(error_info["type"]),
                error_message=error_info["message"],
                failed_step=error_info.get("step"),
                retry_count=final_state["error_count"],
                timestamp=completed_at
            )
            response.recovery_attempted = bool(final_state.get("recovery_plan"))
        
        return response
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active reasoning session"""
        return self._active_sessions.get(session_id)
    
    async def cancel_session(self, session_id: str) -> bool:
        """Cancel active reasoning session"""
        if session_id in self._active_sessions:
            self._active_sessions[session_id]["state"] = "cancelled"
            return True
        return False
    
    async def rollback_to_checkpoint(self, session_id: str, checkpoint_step: int) -> bool:
        """
        Rollback to a specific checkpoint step
        
        Args:
            session_id: The reasoning session ID
            checkpoint_step: The step number to rollback to
            
        Returns:
            Boolean indicating if rollback was successful
        """
        if not self.redis_checkpoint:
            return False
            
        try:
            # Get available checkpoints for the session
            checkpoints = await self.redis_checkpoint.get_rollback_checkpoints(session_id)
            
            # Find the checkpoint closest to the requested step
            target_checkpoint = None
            for checkpoint in checkpoints:
                if checkpoint.step_number <= checkpoint_step:
                    if target_checkpoint is None or checkpoint.step_number > target_checkpoint.step_number:
                        target_checkpoint = checkpoint
            
            if target_checkpoint:
                # Perform the rollback using Redis checkpoint service
                success = await self.redis_checkpoint.rollback_to_checkpoint(session_id, target_checkpoint)
                
                if success:
                    logger.info(f"Successfully rolled back session {session_id} to step {target_checkpoint.step_number}")
                else:
                    logger.error(f"Failed to rollback session {session_id} to step {checkpoint_step}")
                
                return success
            else:
                logger.warning(f"No suitable checkpoint found for rollback to step {checkpoint_step}")
                return False
                
        except Exception as e:
            logger.error(f"Error during rollback for session {session_id}: {e}")
            return False