"""
Pydantic models for Sequential Thinking Service
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ThoughtStatus(str, Enum):
    """Status of a reasoning step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ReasoningState(str, Enum):
    """Overall reasoning session state"""
    INITIALIZED = "initialized"
    PLANNING = "planning"
    THINKING = "thinking"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


class ErrorType(str, Enum):
    """Types of reasoning errors"""
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error" 
    LOGIC_ERROR = "logic_error"
    CONTEXT_ERROR = "context_error"
    RESOURCE_ERROR = "resource_error"


class ThoughtStep(BaseModel):
    """Individual reasoning step"""
    step_number: int = Field(description="Sequential step number")
    thought: str = Field(description="The reasoning content")
    status: ThoughtStatus = Field(default=ThoughtStatus.PENDING)
    is_revision: bool = Field(default=False, description="Whether this revises previous thinking")
    revises_step: Optional[int] = Field(default=None, description="Step number being revised")
    branch_from_step: Optional[int] = Field(default=None, description="Branching point")
    branch_id: Optional[str] = Field(default=None, description="Branch identifier")
    context_used: List[str] = Field(default=[], description="Context sources used")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this step")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    model_used: Optional[str] = Field(default=None, description="LLM model used for this step")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorContext(BaseModel):
    """Context information for errors and recovery"""
    error_type: ErrorType
    error_message: str
    failed_step: Optional[int] = None
    stack_trace: Optional[str] = None
    model_response: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RecoveryPlan(BaseModel):
    """Plan for recovering from reasoning failures"""
    strategy: str = Field(description="Recovery strategy name")
    actions: List[str] = Field(description="Specific recovery actions")
    rollback_to_step: Optional[int] = Field(default=None, description="Step to rollback to")
    context_adjustments: Dict[str, Any] = Field(default={}, description="Context modifications")
    model_switch: Optional[str] = Field(default=None, description="Alternative model to use")
    estimated_success_rate: float = Field(default=0.5, ge=0.0, le=1.0)


class CheckpointInfo(BaseModel):
    """Information about reasoning checkpoints"""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reasoning_session_id: str
    step_number: int
    state: ReasoningState
    created_at: datetime = Field(default_factory=datetime.utcnow)
    redis_key: str
    size_bytes: Optional[int] = None
    is_rollback_point: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReasoningRequest(BaseModel):
    """Request for sequential reasoning"""
    query: str = Field(description="The problem or question to reason about")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")
    max_steps: int = Field(default=10, ge=1, le=50, description="Maximum reasoning steps")
    enable_memory_integration: bool = Field(default=True, description="Use memory service for context")
    enable_self_correction: bool = Field(default=True, description="Enable self-correction loops") 
    enable_checkpointing: bool = Field(default=True, description="Enable state checkpointing")
    priority: int = Field(default=5, ge=1, le=10, description="Processing priority")
    timeout_seconds: int = Field(default=300, ge=30, le=1800, description="Maximum processing time")
    model_preference: Optional[str] = Field(default=None, description="Preferred LLM model")
    user_id: Optional[str] = Field(default=None, description="User identifier for personalization")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class ReasoningResponse(BaseModel):
    """Response from sequential reasoning"""
    session_id: str
    query: str
    final_answer: Optional[str] = None
    reasoning_steps: List[ThoughtStep] = []
    state: ReasoningState
    total_steps: int = 0
    total_processing_time_ms: int = 0
    model_switches: int = 0
    error_recoveries: int = 0
    confidence_score: float = Field(ge=0.0, le=1.0)
    checkpoints_created: int = 0
    memory_integrations: int = 0
    
    # Error information (if failed)
    error_context: Optional[ErrorContext] = None
    recovery_attempted: bool = False
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    context_sources: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @property
    def success(self) -> bool:
        """Whether reasoning completed successfully"""
        return self.state == ReasoningState.COMPLETED and self.final_answer is not None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total processing duration in seconds"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ReasoningStatus(BaseModel):
    """Status check response for ongoing reasoning"""
    session_id: str
    state: ReasoningState
    current_step: int
    total_steps: int
    progress_percentage: float = Field(ge=0.0, le=100.0)
    estimated_completion_seconds: Optional[int] = None
    last_thought: Optional[str] = None
    error_context: Optional[ErrorContext] = None
    
    
class MemoryIntegrationRequest(BaseModel):
    """Request to integrate with memory service"""
    query: str
    context_limit: int = Field(default=3, ge=1, le=10)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    user_id: Optional[str] = None