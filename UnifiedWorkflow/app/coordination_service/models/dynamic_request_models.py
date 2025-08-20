"""Data models for dynamic agent request system."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RequestTypeEnum(str, Enum):
    """Types of dynamic agent requests."""
    RESEARCH = "research"
    VALIDATION = "validation"
    ANALYSIS = "analysis"
    EXPERTISE = "expertise"
    SUPPLEMENTAL_CONTEXT = "supplemental_context"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_ASSESSMENT = "performance_assessment"


class RequestUrgencyEnum(str, Enum):
    """Request urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatusEnum(str, Enum):
    """Request processing statuses."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    AGENT_SELECTED = "agent_selected"
    CONTEXT_GENERATED = "context_generated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class GapSeverityEnum(str, Enum):
    """Information gap severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InformationGapModel(BaseModel):
    """Model for information gaps."""
    gap_id: str
    gap_type: str
    description: str
    severity: GapSeverityEnum
    detected_by: str
    related_context: Dict[str, Any] = Field(default_factory=dict)
    suggested_expertise: List[str] = Field(default_factory=list)
    priority_score: Optional[int] = None


class DynamicAgentRequestCreate(BaseModel):
    """Request model for creating dynamic agent requests."""
    requesting_agent: str = Field(..., description="Name of the agent making the request")
    workflow_id: str = Field(..., description="ID of the current workflow")
    request_type: RequestTypeEnum = Field(..., description="Type of request")
    urgency: RequestUrgencyEnum = Field(default=RequestUrgencyEnum.MEDIUM, description="Request urgency level")
    description: str = Field(..., description="Description of what information is needed")
    specific_expertise_needed: List[str] = Field(default_factory=list, description="Specific expertise requirements")
    context_requirements: Dict[str, Any] = Field(default_factory=dict, description="Context requirements")
    information_gaps: List[InformationGapModel] = Field(default_factory=list, description="Detected information gaps")
    expected_output_format: str = Field(default="structured_analysis", description="Expected output format")
    max_response_tokens: int = Field(default=4000, description="Maximum response tokens")
    timeout_minutes: int = Field(default=30, description="Request timeout in minutes")


class DynamicAgentRequestResponse(BaseModel):
    """Response model for dynamic agent requests."""
    request_id: str
    status: RequestStatusEnum
    created_at: float
    requesting_agent: str
    workflow_id: str
    request_type: RequestTypeEnum
    urgency: RequestUrgencyEnum
    description: str
    assigned_agent: Optional[str] = None
    context_package_id: Optional[str] = None
    spawned_workflow_id: Optional[str] = None
    completed_at: Optional[float] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confidence_score: float = 0.0
    progress_percentage: float = 0.0
    estimated_completion: Optional[float] = None


class GapDetectionRequest(BaseModel):
    """Request model for gap detection."""
    agent_name: str = Field(..., description="Name of the agent")
    task_context: Dict[str, Any] = Field(..., description="Current task context")
    execution_log: List[str] = Field(..., description="Agent execution log")
    current_findings: Dict[str, Any] = Field(..., description="Current findings")


class GapDetectionResponse(BaseModel):
    """Response model for gap detection."""
    gaps_detected: List[InformationGapModel]
    gap_count: int
    high_priority_gaps: int
    auto_request_ids: List[str] = Field(default_factory=list, description="Auto-created request IDs")


class AgentRequestStatus(BaseModel):
    """Model for agent request status."""
    request_id: str
    status: RequestStatusEnum
    assigned_agent: Optional[str] = None
    progress_percentage: float = 0.0
    estimated_completion: Optional[float] = None
    response_available: bool = False


class AgentRequestResultsResponse(BaseModel):
    """Response model for agent request results."""
    request_id: str
    status: RequestStatusEnum
    response_data: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    processing_duration: Optional[float] = None
    assigned_agent: Optional[str] = None


class DynamicRequestMetrics(BaseModel):
    """Model for dynamic request system metrics."""
    total_requests: int
    completed_requests: int
    failed_requests: int
    active_requests: int
    queued_requests: int
    avg_response_time: float
    agent_spawn_rate: float
    success_rate: float


class ContextIntegrationRequest(BaseModel):
    """Request model for context integration."""
    requesting_agent: str = Field(..., description="Agent requesting integration")
    workflow_id: str = Field(..., description="Current workflow ID")
    request_id: str = Field(..., description="Dynamic request ID")
    original_context: Dict[str, Any] = Field(..., description="Original agent context")
    new_findings: Dict[str, Any] = Field(..., description="New findings to integrate")
    integration_strategy: str = Field(default="merge", description="Integration strategy")


class ContextIntegrationResponse(BaseModel):
    """Response model for context integration."""
    integration_id: str
    integrated_context: Dict[str, Any]
    integration_summary: Dict[str, Any]
    updated_context_package_id: Optional[str] = None
    confidence_improvement: float = 0.0


class AgentCommunicationProtocol(BaseModel):
    """Model for standardized agent communication."""
    message_type: str = Field(..., description="Type of communication message")
    sender_agent: str = Field(..., description="Sending agent name")
    recipient_agent: Optional[str] = Field(None, description="Target agent (None for broadcast)")
    workflow_id: str = Field(..., description="Associated workflow ID")
    message_data: Dict[str, Any] = Field(..., description="Message payload")
    priority: str = Field(default="medium", description="Message priority")
    expects_response: bool = Field(default=False, description="Whether a response is expected")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request/response")


class RequestTemplateModel(BaseModel):
    """Model for dynamic request templates."""
    template_id: str
    request_type: RequestTypeEnum
    template_name: str
    description: str
    default_urgency: RequestUrgencyEnum
    suggested_agents: List[str]
    context_requirements: Dict[str, Any]
    expected_output_format: str
    timeout_minutes: int
    usage_count: int = 0
    success_rate: float = 0.0