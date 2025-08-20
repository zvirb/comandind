"""
Enhanced chat schemas with structured outputs for LangChain 0.3+ compatibility.
These schemas ensure type safety and consistency between front-end and back-end.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Enhanced enums for better type safety
class MessageType(str, Enum):
    """Message type enumeration for structured responses."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    FAST_RESPONSE = "fast_response"
    ENHANCED_RESPONSE = "enhanced_response"

class ChatMode(str, Enum):
    """Chat mode enumeration."""
    SMART_ROUTER = "smart-router"
    SOCRATIC_INTERVIEW = "socratic-interview"
    EXPERT_GROUP = "expert-group"
    DIRECT = "direct"

class ExecutiveDecision(str, Enum):
    """Executive node decision types."""
    DIRECT = "DIRECT"
    PLANNING = "PLANNING"

class ToolExecutionStatus(str, Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    PARTIAL = "partial"

# Request schemas (front-end to back-end)
class ChatMessageRequest(BaseModel):
    """Structured chat message request from front-end."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation continuity")
    mode: ChatMode = Field(ChatMode.SMART_ROUTER, description="Chat processing mode")
    current_graph_state: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Current graph state for multi-turn conversations")
    message_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Previous messages for context")
    user_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="User preferences and settings")
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json
    
    @classmethod
    def validate_to_json(cls, v):
        if isinstance(v, str):
            # Handle case where request comes as JSON string
            import json
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Help me schedule a meeting for tomorrow at 2 PM",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "mode": "smart-router",
                "current_graph_state": {},
                "message_history": [],
                "user_preferences": {"preferred_model": "llama3.2:3b"}
            }
        }

class FeedbackRequest(BaseModel):
    """User feedback request structure."""
    session_id: str = Field(..., description="Session identifier")
    message_id: str = Field(..., description="Message identifier")
    feedback: Literal["thumbs_up", "thumbs_down"] = Field(..., description="Feedback type")
    feedback_type: Optional[Literal["thumbs_up", "thumbs_down"]] = Field(None, description="Alternative field name for frontend compatibility")
    details: Optional[str] = Field(None, max_length=1000, description="Optional detailed feedback")

# Response schemas (back-end to front-end)
class ToolExecutionResult(BaseModel):
    """Structured tool execution result."""
    tool_name: str = Field(..., description="Name of the executed tool")
    status: ToolExecutionStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class IntermediateStep(BaseModel):
    """Intermediate processing step for streaming."""
    step_name: str = Field(..., description="Name of the processing step")
    description: str = Field(..., description="Human-readable description")
    status: Literal["started", "completed", "error"] = Field(..., description="Step status")
    output: Optional[Any] = Field(None, description="Step output if available")
    timestamp: datetime = Field(default_factory=datetime.now, description="Step timestamp")

class ChatResponse(BaseModel):
    """Structured chat response to front-end."""
    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session identifier")
    response: str = Field(..., description="Assistant response text")
    type: MessageType = Field(MessageType.ASSISTANT, description="Response message type")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    # Enhanced fields for LangChain 0.3+ features
    background_task_id: Optional[str] = Field(None, description="Background task identifier for enhancement")
    task_id: Optional[str] = Field(None, description="Celery task identifier for processing")
    processing_status: Optional[str] = Field("completed", description="Processing status (processing, completed, error)")
    is_enhanceable: bool = Field(False, description="Whether response can be enhanced")
    tool_results: List[ToolExecutionResult] = Field(default_factory=list, description="Tool execution results")
    intermediate_steps: List[IntermediateStep] = Field(default_factory=list, description="Processing steps")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Response confidence score")
    
    # Metadata and context
    executive_decision: Optional[ExecutiveDecision] = Field(None, description="Executive routing decision")
    model_used: Optional[str] = Field(None, description="LLM model used for response")
    processing_time_ms: Optional[float] = Field(None, description="Total processing time")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_123456789",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "I've scheduled your meeting for tomorrow at 2 PM.",
                "type": "assistant",
                "timestamp": "2025-07-23T12:00:00Z",
                "background_task_id": "task_987654321",
                "is_enhanceable": True,
                "tool_results": [
                    {
                        "tool_name": "calendar_create",
                        "status": "success",
                        "result": {"event_id": "evt_123"},
                        "execution_time_ms": 250.5
                    }
                ],
                "confidence_score": 0.95,
                "executive_decision": "DIRECT",
                "model_used": "llama3.2:3b",
                "processing_time_ms": 1200.5,
                "tokens_used": 150
            }
        }

# Streaming response schemas
class StreamingChunk(BaseModel):
    """Individual streaming response chunk."""
    chunk_id: str = Field(..., description="Chunk identifier")
    session_id: str = Field(..., description="Session identifier")
    type: Literal["text", "tool_call", "intermediate_step", "metadata"] = Field(..., description="Chunk type")
    content: Union[str, Dict[str, Any]] = Field(..., description="Chunk content")
    is_final: bool = Field(False, description="Whether this is the final chunk")
    timestamp: datetime = Field(default_factory=datetime.now, description="Chunk timestamp")

# Enhanced GraphState schema for better serialization
class EnhancedGraphState(BaseModel):
    """Enhanced GraphState with structured outputs and better typing."""
    user_input: str = Field(..., description="User input message")
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Tool execution
    selected_tool: Optional[str] = Field(None, description="Selected tool for execution")
    tool_output: Optional[ToolExecutionResult] = Field(None, description="Structured tool output")
    
    # Routing and decisions
    executive_decision: Optional[ExecutiveDecision] = Field(None, description="Executive routing decision")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Decision confidence")
    
    # Response generation
    final_response: Optional[str] = Field(None, description="Final response text")
    intermediate_steps: List[IntermediateStep] = Field(default_factory=list, description="Processing steps")
    
    # Model configuration
    selected_models: Dict[str, str] = Field(default_factory=dict, description="Selected models per task")
    
    # Metadata
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="State creation timestamp")
    
    class Config:
        # Enable serialization of complex types
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Ollama integration schemas for structured output
class OllamaStructuredRequest(BaseModel):
    """Structured request for Ollama with schema binding."""
    messages: List[Dict[str, str]] = Field(..., description="Message history")
    model: str = Field(..., description="Model name")
    response_schema: Optional[Dict[str, Any]] = Field(None, description="Expected response schema")
    temperature: float = Field(0.1, ge=0, le=2, description="Response creativity")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")

class OllamaStructuredResponse(BaseModel):
    """Structured response from Ollama."""
    content: Union[str, Dict[str, Any]] = Field(..., description="Response content")
    model: str = Field(..., description="Model used")
    tokens_used: int = Field(..., description="Tokens consumed")
    processing_time_ms: float = Field(..., description="Processing time")
    is_structured: bool = Field(False, description="Whether response follows provided schema")