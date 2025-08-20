"""
Smart AI Models for Enhanced GraphState
Contains Pydantic models for advanced agentic patterns including:
- Token tracking and metrics
- Human context integration
- Confidence-based routing
- Interactive pause mechanisms
- Memory and critique systems
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ConfidenceLevel(str, Enum):
    """Confidence levels for dynamic routing decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReflectionDepth(str, Enum):
    """Levels of reflection depth for intra-request iteration."""
    BASIC = "basic"  # Simple validation and error checking
    MODERATE = "moderate"  # Structured critique with external grounding
    DEEP = "deep"  # Multi-perspective analysis with debate


class ReflectionPersona(str, Enum):
    """Personas for structured critique to elicit targeted feedback."""
    TEACHER = "teacher"  # Pedagogical, helps improve understanding
    EXPERT_REVIEWER = "expert_reviewer"  # Technical precision and accuracy
    DEVILS_ADVOCATE = "devils_advocate"  # Challenges assumptions and finds flaws
    END_USER = "end_user"  # Focuses on practical usability
    QUALITY_ASSURANCE = "quality_assurance"  # Systematic error detection


class TaskStatus(str, Enum):
    """Current phase of the agent's operation."""
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    AWAITING_HUMAN_INPUT = "awaiting_human_input"
    COMPLETED = "completed"
    FAILED = "failed"


class PauseReason(str, Enum):
    """Reasons for pausing execution to await human input."""
    LOW_CONFIDENCE = "low_confidence"
    ERROR_RECOVERY = "error_recovery"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    PLAN_REVIEW = "plan_review"
    TOOL_SELECTION = "tool_selection"
    QUALITY_CHECK = "quality_check"
    MISSION_CONTRADICTION = "mission_contradiction"
    TIMEOUT = "timeout"


class TokenMetrics(BaseModel):
    """Token usage tracking for cost optimization."""
    input_tokens: int = Field(default=0, description="Total input tokens used")
    output_tokens: int = Field(default=0, description="Total output tokens generated")
    total_tokens: int = Field(default=0, description="Total tokens (input + output)")
    tool_selection_tokens: int = Field(default=0, description="Tokens used for tool selection")
    reflection_tokens: int = Field(default=0, description="Tokens used for reflection/critique")
    confidence_tokens: int = Field(default=0, description="Tokens used for confidence assessment")
    memory_retrieval_tokens: int = Field(default=0, description="Tokens used for memory operations")
    human_context_tokens: int = Field(default=0, description="Additional tokens from human context")
    
    def add_tokens(self, input_tokens: int, output_tokens: int, category: str = "general"):
        """Add tokens to the appropriate category."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens
        
        # Add to specific categories
        if category == "tool_selection":
            self.tool_selection_tokens += input_tokens + output_tokens
        elif category == "reflection":
            self.reflection_tokens += input_tokens + output_tokens
        elif category == "confidence":
            self.confidence_tokens += input_tokens + output_tokens
        elif category == "memory":
            self.memory_retrieval_tokens += input_tokens + output_tokens
        elif category == "human_context":
            self.human_context_tokens += input_tokens + output_tokens


class HumanContextModel(BaseModel):
    """Human-provided context during interactive streaming."""
    context_text: str = Field(description="The human-provided context or feedback")
    timestamp: datetime = Field(default_factory=datetime.now, description="When context was provided")
    injection_point: str = Field(description="Where in the process context was injected")
    priority: str = Field(default="medium", description="Priority level (high/medium/low)")
    context_type: str = Field(default="general", description="Type of context (constraint/preference/clarification/correction)")
    session_id: str = Field(description="Session ID for the context")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PauseStateModel(BaseModel):
    """State management for interactive pauses."""
    is_paused: bool = Field(default=False, description="Whether execution is currently paused")
    pause_reason: Optional[PauseReason] = Field(default=None, description="Reason for the pause")
    pause_message: Optional[str] = Field(default=None, description="Message displayed to user during pause")
    pause_timeout: int = Field(default=30, description="Timeout in seconds for pause")
    pause_start_time: Optional[datetime] = Field(default=None, description="When pause started")
    awaiting_context: bool = Field(default=False, description="Whether waiting for human context")
    context_prompt: Optional[str] = Field(default=None, description="Prompt for human context")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlanStep(BaseModel):
    """Individual step in a structured plan."""
    step_id: str = Field(description="Unique identifier for the step")
    description: str = Field(description="Human-readable description of the step")
    tool_id: Optional[str] = Field(default=None, description="Tool to use for this step")
    dependencies: List[str] = Field(default_factory=list, description="Step IDs this step depends on")
    confidence_score: float = Field(default=0.5, description="Confidence in this step (0-1)")
    estimated_tokens: int = Field(default=100, description="Estimated token cost for this step")
    status: str = Field(default="pending", description="Status: pending/in_progress/completed/failed")
    human_context_required: bool = Field(default=False, description="Whether human context is needed")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReflectionCriteria(BaseModel):
    """Specific criteria for structured critique evaluation."""
    accuracy: Optional[float] = Field(default=None, description="Factual accuracy score (0-1)")
    completeness: Optional[float] = Field(default=None, description="Completeness score (0-1)")
    logical_consistency: Optional[float] = Field(default=None, description="Logical consistency score (0-1)")
    adherence_to_constraints: Optional[float] = Field(default=None, description="Constraint adherence score (0-1)")
    tool_appropriateness: Optional[float] = Field(default=None, description="Tool selection appropriateness (0-1)")
    user_intent_alignment: Optional[float] = Field(default=None, description="Alignment with user intent (0-1)")
    
    def overall_score(self) -> float:
        """Calculate overall reflection score."""
        scores = [s for s in [self.accuracy, self.completeness, self.logical_consistency, 
                             self.adherence_to_constraints, self.tool_appropriateness, self.user_intent_alignment] if s is not None]
        return sum(scores) / len(scores) if scores else 0.5


class CritiqueModel(BaseModel):
    """Enhanced self-critique and reflection tracking with sophisticated prompting techniques."""
    critique_id: str = Field(description="Unique identifier for the critique")
    critique_text: str = Field(description="The critique content")
    criticized_output_id: Optional[str] = Field(default=None, description="ID of the output being critiqued")
    
    # Enhanced reflection fields from smart_ai.txt
    reflection_persona: ReflectionPersona = Field(description="Persona used for critique (teacher, expert, etc.)")
    reflection_depth: ReflectionDepth = Field(description="Depth of reflection performed")
    external_grounding: List[str] = Field(default_factory=list, description="External data used to ground critique")
    verification_questions: List[str] = Field(default_factory=list, description="Generated verification questions")
    criteria_evaluation: ReflectionCriteria = Field(default_factory=ReflectionCriteria, description="Structured criteria scores")
    
    # Revision and improvement tracking
    suggested_revisions: List[str] = Field(default_factory=list, description="Suggested improvements")
    specific_issues: List[str] = Field(default_factory=list, description="Specific issues identified")
    missing_elements: List[str] = Field(default_factory=list, description="Missing elements identified")
    
    # Confidence and decision support
    timestamp: datetime = Field(default_factory=datetime.now, description="When critique was generated")
    confidence_before: float = Field(description="Confidence before critique")
    confidence_after: float = Field(description="Confidence after critique")
    retry_recommended: bool = Field(default=False, description="Whether retry is recommended")
    retry_strategy: Optional[str] = Field(default=None, description="Recommended retry approach")
    
    # Human interaction
    human_feedback: Optional[str] = Field(default=None, description="Human feedback on the critique")
    actionability_score: float = Field(default=0.5, description="How actionable the critique is (0-1)")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolCallRecord(BaseModel):
    """Detailed logging of tool interactions."""
    call_id: str = Field(description="Unique identifier for the tool call")
    tool_id: str = Field(description="Tool that was called")
    tool_name: str = Field(description="Human-readable tool name")
    input_args: Dict[str, Any] = Field(description="Arguments passed to the tool")
    output_result: Optional[Any] = Field(default=None, description="Result from the tool")
    error_message: Optional[str] = Field(default=None, description="Error message if tool failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="When tool was called")
    execution_time: float = Field(default=0.0, description="Time taken to execute in seconds")
    tokens_used: TokenMetrics = Field(default_factory=TokenMetrics, description="Tokens used for this call")
    success: bool = Field(default=True, description="Whether the tool call succeeded")
    human_context_influenced: bool = Field(default=False, description="Whether human context influenced this call")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ErrorModel(BaseModel):
    """Structured error information for correction memory."""
    error_id: str = Field(description="Unique identifier for the error")
    error_type: str = Field(description="Type of error (tool_error/llm_error/validation_error)")
    error_message: str = Field(description="Detailed error message")
    error_context: Dict[str, Any] = Field(description="Context when error occurred")
    tool_name: Optional[str] = Field(default=None, description="Tool that caused the error")
    timestamp: datetime = Field(default_factory=datetime.now, description="When error occurred")
    recovery_attempted: bool = Field(default=False, description="Whether recovery was attempted")
    recovery_successful: bool = Field(default=False, description="Whether recovery succeeded")
    human_intervention: bool = Field(default=False, description="Whether human intervention was needed")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExternalContextItem(BaseModel):
    """External context retrieved from memory or RAG."""
    context_id: str = Field(description="Unique identifier for the context")
    content: str = Field(description="The context content")
    source: str = Field(description="Source of the context (rag/memory/correction_memory)")
    relevance_score: float = Field(description="Relevance score (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When context was retrieved")
    tokens_used: int = Field(default=0, description="Tokens used to retrieve this context")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class MemoryEntry(BaseModel):
    """Entry for persistent memory storage."""
    entry_id: str = Field(description="Unique identifier for the memory entry")
    content: str = Field(description="The memory content")
    entry_type: str = Field(description="Type: success/failure/correction/pattern")
    session_id: str = Field(description="Session where this memory was created")
    user_id: Optional[str] = Field(default=None, description="User who created this memory")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding for semantic search")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    timestamp: datetime = Field(default_factory=datetime.now, description="When memory was created")
    usage_count: int = Field(default=0, description="How often this memory has been retrieved")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class InteractionMetrics(BaseModel):
    """Metrics for a complete interaction."""
    interaction_id: str = Field(description="Unique identifier for the interaction")
    total_tokens: TokenMetrics = Field(default_factory=TokenMetrics, description="Total token usage")
    execution_time: float = Field(default=0.0, description="Total execution time in seconds")
    plan_steps_completed: int = Field(default=0, description="Number of plan steps completed")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
    reflection_cycles: int = Field(default=0, description="Number of reflection cycles")
    human_interactions: int = Field(default=0, description="Number of human interactions")
    confidence_adjustments: int = Field(default=0, description="Number of confidence adjustments")
    errors_encountered: int = Field(default=0, description="Number of errors encountered")
    success_rate: float = Field(default=1.0, description="Success rate (0-1)")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


# Convenience type aliases
ContextQueue = List[HumanContextModel]
CritiqueHistory = List[CritiqueModel]
ToolCallHistory = List[ToolCallRecord]
ExternalContext = List[ExternalContextItem]
PlanSteps = List[PlanStep]