"""Shared types for the worker's graph-based processing system."""

from typing import Any, Dict, Optional, List
import uuid
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage
from worker.smart_ai_models import (
    TokenMetrics, HumanContextModel, PauseStateModel, PlanStep, CritiqueModel,
    ToolCallRecord, ErrorModel, ExternalContextItem, InteractionMetrics,
    ContextQueue, CritiqueHistory, ToolCallHistory, ExternalContext, PlanSteps,
    TaskStatus, ConfidenceLevel, ReflectionDepth, ReflectionPersona
)


def create_interaction_metrics() -> InteractionMetrics:
    """Create InteractionMetrics with a unique interaction_id."""
    return InteractionMetrics(interaction_id=str(uuid.uuid4()))


class GraphState(BaseModel):
    """State object that flows through the LangGraph router system."""
    user_input: str  # The most recent user query
    session_id: str
    user_id: Optional[str] = None
    selected_tool: Optional[str] = None
    tool_output: Optional[Dict[str, Any]] = None  # Output from the selected tool
    messages: List[BaseMessage] = Field(default_factory=list)  # type: ignore
    executive_decision: Optional[str] = None  # PLANNING or DIRECT decision from executive node
    routing_decision: Optional[str] = None  # DIRECT, PLANNING, or other routing decision
    conversation_summary: Optional[str] = None  # Summary of the conversation so far
    
    # Legacy planning fields (maintained for backwards compatibility)
    plan: List[str] = Field(default_factory=list)  # The list of sub-tasks for the agent to execute
    plan_step: int = 0  # The index of the current step in the plan
    critique: Optional[str] = None  # A critique of the last tool's output, for self-correction
    final_response: Optional[Any] = None  # The final response to the user for this turn
    retry_needed: bool = False  # Whether the reflection step determined a retry is needed
    selected_model: Optional[str] = None # The model selected by the user (legacy)
    
    # LLM Categories for specialized tasks (legacy)
    chat_model: Optional[str] = None
    initial_assessment_model: Optional[str] = None
    tool_selection_model: Optional[str] = None
    embeddings_model: Optional[str] = None
    coding_model: Optional[str] = None
    
    # Granular Node-Specific Models
    executive_assessment_model: Optional[str] = None
    confidence_assessment_model: Optional[str] = None
    tool_routing_model: Optional[str] = None
    simple_planning_model: Optional[str] = None
    wave_function_specialist_model: Optional[str] = None
    wave_function_refinement_model: Optional[str] = None
    plan_validation_model: Optional[str] = None
    plan_comparison_model: Optional[str] = None
    reflection_model: Optional[str] = None
    final_response_model: Optional[str] = None

    # --- NEW SMART AI FIELDS ---
    
    # Enhanced Planning System
    current_plan: PlanSteps = Field(default_factory=list, description="Structured plan with confidence scores")
    current_plan_step: int = Field(default=0, description="Current step in the structured plan")
    
    # Dynamic Expert System
    conversation_domain: Optional[str] = Field(default=None, description="Detected domain/topic of conversation")
    dynamic_experts: List[Dict[str, str]] = Field(default_factory=list, description="Context-specific experts for wave function planning")
    compressed_conversation_history: Optional[str] = Field(default=None, description="Compressed conversation history for memory efficiency")
    
    # Expert Questioning System
    expert_questions: List[Dict[str, str]] = Field(default_factory=list, description="Questions from experts needing clarification")
    expert_question_answers: Dict[str, str] = Field(default_factory=dict, description="Human answers to expert questions")
    awaiting_expert_clarification: bool = Field(default=False, description="Whether planning is paused waiting for human answers")
    expert_clarification_complete: bool = Field(default=False, description="Whether expert questioning round is complete")
    
    # Enhanced Reflection and Critique System (from smart_ai.txt)
    critique_history: CritiqueHistory = Field(default_factory=list, description="History of self-critiques")
    reflection_trigger_threshold: float = Field(default=0.6, description="Confidence threshold for triggering reflection")
    reflection_depth: ReflectionDepth = Field(default=ReflectionDepth.MODERATE, description="Current reflection depth setting")
    reflection_persona: ReflectionPersona = Field(default=ReflectionPersona.EXPERT_REVIEWER, description="Current reflection persona")
    reflection_enabled: bool = Field(default=True, description="Whether reflection is enabled for this session")
    max_reflection_cycles: int = Field(default=3, description="Maximum reflection cycles per step")
    
    # Confidence-Based Routing
    confidence_score: float = Field(default=0.5, description="LLM's confidence in current output (0-1)")
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="Confidence level enum")
    
    # Token Tracking and Metrics
    token_usage: TokenMetrics = Field(default_factory=TokenMetrics, description="Token usage tracking")
    interaction_metrics: InteractionMetrics = Field(default_factory=create_interaction_metrics, description="Interaction metrics")
    
    # Human-in-the-Loop Integration
    human_context_queue: ContextQueue = Field(default_factory=list, description="Queue of human-provided context")
    human_context_history: List[HumanContextModel] = Field(default_factory=list, description="History of human context")
    pause_state: PauseStateModel = Field(default_factory=PauseStateModel, description="Interactive pause state")
    
    # Tool Call Tracking
    tool_call_history: ToolCallHistory = Field(default_factory=list, description="Detailed tool call history")
    
    # External Context and Memory
    external_context: ExternalContext = Field(default_factory=list, description="Retrieved external context")
    memory_entries: List[str] = Field(default_factory=list, description="Memory entry IDs used this session")
    
    # Process Control
    iteration_count: int = Field(default=0, description="Number of iteration cycles")
    max_iterations: int = Field(default=10, description="Maximum allowed iterations")
    task_status: TaskStatus = Field(default=TaskStatus.PLANNING, description="Current task status")
    
    # Error Handling
    error_details: Optional[ErrorModel] = Field(default=None, description="Current error details")
    error_count: int = Field(default=0, description="Number of errors encountered")
    
    # Additional Control Fields
    tool_explanation_needed: bool = Field(default=False, description="Whether tool explanation is needed")
    awaiting_human_input: bool = Field(default=False, description="Whether waiting for human input")
    skip_reflection: bool = Field(default=False, description="Whether to skip reflection for this iteration")
    
    # Session and Context Management
    session_start_time: Optional[str] = Field(default=None, description="Session start timestamp")
    last_activity_time: Optional[str] = Field(default=None, description="Last activity timestamp")
    
    # Persistent Memory Context
    memory_context: Dict[str, Any] = Field(default_factory=dict, description="Comprehensive memory context from persistent memory service")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)