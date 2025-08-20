"""
Communication Protocol Stack Schemas

Defines the schema structures for the three-layer communication protocol:
1. Model Context Protocol (MCP) - Layer 1: External tool integration
2. Agent-to-Agent (A2A) Protocol - Layer 2: Peer-to-peer communication  
3. Agent Communication Protocol (ACP) - Layer 3: Workflow orchestration

Intent-based messaging with JSON-LD structure for semantic interoperability.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


# ================================
# Intent-Based Message Framework
# ================================

class MessageIntent(str, Enum):
    """Performative communication intents following speech act theory."""
    # Informative acts
    INFORM = "inform"
    NOTIFY = "notify"
    REPORT = "report"
    
    # Directive acts
    REQUEST = "request"
    COMMAND = "command"
    DELEGATE = "delegate"
    
    # Commissive acts
    PROMISE = "promise"
    CONFIRM = "confirm"
    COMMIT = "commit"
    
    # Expressive acts
    QUERY = "query"
    PROPOSE = "propose"
    SUGGEST = "suggest"
    
    # Declarative acts
    DECLARE = "declare"
    ANNOUNCE = "announce"
    REGISTER = "register"


class MessagePriority(str, Enum):
    """Message priority levels for routing and processing."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal" 
    LOW = "low"
    BACKGROUND = "background"


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ================================
# Base Protocol Message Structure
# ================================

class ProtocolMetadata(BaseModel):
    """Common metadata for all protocol messages."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sender_id: str
    sender_type: str  # "agent", "service", "user"
    recipients: List[str] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    causality_chain: List[str] = Field(default_factory=list)
    
    # Protocol layer identification
    protocol_layer: str  # "mcp", "a2a", "acp"
    protocol_version: str = "1.0"
    
    # Message semantics
    intent: MessageIntent
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    
    # Context and routing
    domain: Optional[str] = None  # Application domain (calendar, documents, etc.)
    requires_response: bool = False
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Security context
    authentication_token: Optional[str] = None
    permission_scope: List[str] = Field(default_factory=list)


class BaseProtocolMessage(BaseModel):
    """Base structure for all protocol messages with JSON-LD semantics."""
    # JSON-LD context
    context: str = Field(default="https://ai-workflow-engine.local/protocol/v1", alias="@context")
    message_type: str = Field(alias="@type")
    
    # Protocol metadata
    metadata: ProtocolMetadata
    
    # Message payload
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Semantic annotations
    ontology_terms: List[str] = Field(default_factory=list)
    semantic_tags: Dict[str, Any] = Field(default_factory=dict)
    
    # Error handling
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


# ================================
# Layer 1: Model Context Protocol (MCP)
# ================================

class ToolCapability(BaseModel):
    """Definition of a tool capability."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = Field(default_factory=list)
    supported_formats: List[str] = Field(default_factory=list)
    rate_limits: Optional[Dict[str, Any]] = None


class ExternalResourceSpec(BaseModel):
    """Specification for external resource access."""
    resource_type: str  # "api", "database", "file_system", "service"
    endpoint_url: Optional[str] = None
    authentication_method: str  # "oauth2", "api_key", "jwt", "none"
    required_scopes: List[str] = Field(default_factory=list)
    connection_params: Dict[str, Any] = Field(default_factory=dict)


class MCPToolRequest(BaseProtocolMessage):
    """MCP request for tool execution."""
    message_type: str = Field(default="mcp:tool_request")
    
    # Tool execution details
    tool_name: str
    tool_parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Resource access requirements
    required_resources: List[ExternalResourceSpec] = Field(default_factory=list)
    permission_grants: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution preferences
    async_execution: bool = True
    streaming_response: bool = False
    result_format: str = "json"


class MCPToolResponse(BaseProtocolMessage):
    """MCP response from tool execution."""
    message_type: str = Field(default="mcp:tool_response")
    
    # Execution results
    tool_result: Any = None
    execution_status: str  # "success", "error", "timeout"
    execution_time_ms: float
    
    # Tool metrics
    tokens_consumed: Optional[int] = None
    api_calls_made: int = 0
    resources_accessed: List[str] = Field(default_factory=list)
    
    # Security audit trail
    permissions_used: List[str] = Field(default_factory=list)
    security_events: List[Dict[str, Any]] = Field(default_factory=list)


class MCPCapabilityAnnouncement(BaseProtocolMessage):
    """MCP capability announcement from tool server."""
    message_type: str = Field(default="mcp:capability_announcement")
    
    # Server capabilities
    server_id: str
    server_version: str
    available_tools: List[ToolCapability]
    supported_protocols: List[str] = Field(default_factory=list)
    
    # Service information
    service_status: str = "available"
    health_endpoint: Optional[str] = None
    documentation_url: Optional[str] = None


# ================================
# Layer 2: Agent-to-Agent (A2A) Protocol
# ================================

class AgentCapability(BaseModel):
    """Agent capability description."""
    capability_id: str
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    processing_time_estimate: Optional[float] = None
    confidence_level: float = Field(ge=0.0, le=1.0, default=0.8)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class AgentProfile(BaseModel):
    """Complete agent profile for discovery and negotiation."""
    agent_id: str
    agent_name: str
    agent_type: str  # "research_specialist", "personal_assistant", etc.
    version: str
    
    # Capabilities
    capabilities: List[AgentCapability]
    specializations: List[str] = Field(default_factory=list)
    supported_domains: List[str] = Field(default_factory=list)
    
    # Resource requirements and constraints
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    max_concurrent_tasks: int = 1
    average_response_time: Optional[float] = None
    
    # Communication preferences
    preferred_protocols: List[str] = Field(default_factory=list)
    communication_patterns: List[str] = Field(default_factory=list)
    
    # Status information
    availability_status: str = "available"  # "available", "busy", "offline"
    current_load: float = Field(ge=0.0, le=1.0, default=0.0)
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class A2ADirectMessage(BaseProtocolMessage):
    """Direct agent-to-agent communication message."""
    message_type: str = Field(default="a2a:direct_message")
    
    # Communication details
    target_agent_id: str
    message_content: str
    content_type: str = "text/plain"
    
    # Conversation context
    conversation_context: Dict[str, Any] = Field(default_factory=dict)
    message_sequence: int = 1
    
    # Response expectations
    expects_response: bool = False
    response_timeout_seconds: Optional[int] = None
    response_format: Optional[str] = None


class A2ACapabilityNegotiation(BaseProtocolMessage):
    """Agent capability negotiation message."""
    message_type: str = Field(default="a2a:capability_negotiation")
    
    # Negotiation details
    negotiation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    negotiation_type: str  # "request", "offer", "accept", "reject", "counter"
    
    # Capability requirements/offers
    required_capabilities: List[str] = Field(default_factory=list)
    offered_capabilities: List[AgentCapability] = Field(default_factory=list)
    
    # Negotiation parameters
    task_parameters: Dict[str, Any] = Field(default_factory=dict)
    resource_constraints: Dict[str, Any] = Field(default_factory=dict)
    quality_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Agreement terms
    proposed_terms: Dict[str, Any] = Field(default_factory=dict)
    agreement_duration: Optional[int] = None  # seconds


class A2AAgentDiscovery(BaseProtocolMessage):
    """Agent discovery and registration message."""
    message_type: str = Field(default="a2a:agent_discovery")
    
    # Discovery operation
    discovery_type: str  # "register", "query", "response", "heartbeat"
    
    # Agent information
    agent_profile: Optional[AgentProfile] = None
    query_criteria: Dict[str, Any] = Field(default_factory=dict)
    discovered_agents: List[AgentProfile] = Field(default_factory=list)
    
    # Registry management
    registry_operation: Optional[str] = None  # "add", "update", "remove"
    time_to_live: int = 3600  # Agent registration TTL in seconds


# ================================
# Layer 3: Agent Communication Protocol (ACP)
# ================================

class WorkflowStep(BaseModel):
    """Individual step in a workflow."""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_name: str
    step_type: str  # "sequential", "parallel", "conditional", "loop"
    
    # Step execution
    assigned_agent: Optional[str] = None
    required_capabilities: List[str] = Field(default_factory=list)
    input_requirements: Dict[str, Any] = Field(default_factory=dict)
    output_specification: Dict[str, Any] = Field(default_factory=dict)
    
    # Step dependencies
    depends_on: List[str] = Field(default_factory=list)
    blocks: List[str] = Field(default_factory=list)
    
    # Execution control
    timeout_seconds: Optional[int] = None
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    failure_policy: str = "abort"  # "abort", "continue", "retry"
    
    # Status tracking
    status: str = "pending"  # "pending", "executing", "completed", "failed"
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str
    workflow_version: str = "1.0"
    
    # Workflow structure
    steps: List[WorkflowStep]
    execution_order: List[str] = Field(default_factory=list)
    parallel_groups: List[List[str]] = Field(default_factory=list)
    
    # Workflow metadata
    description: str = ""
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Execution configuration
    max_execution_time: Optional[int] = None  # seconds
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    quality_gates: List[Dict[str, Any]] = Field(default_factory=list)
    
    # State management
    state_persistence: bool = True
    checkpoint_strategy: str = "step_completion"  # "step_completion", "phase_completion", "none"


class ACPWorkflowControl(BaseProtocolMessage):
    """Workflow orchestration control message."""
    message_type: str = Field(default="acp:workflow_control")
    
    # Workflow identification
    workflow_instance_id: str
    workflow_definition: Optional[WorkflowDefinition] = None
    
    # Control operation
    control_operation: str  # "start", "pause", "resume", "abort", "checkpoint"
    target_step_id: Optional[str] = None
    
    # Execution parameters
    execution_parameters: Dict[str, Any] = Field(default_factory=dict)
    override_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # State information
    current_state: Dict[str, Any] = Field(default_factory=dict)
    execution_progress: float = Field(ge=0.0, le=1.0, default=0.0)


class ACPTaskDelegation(BaseProtocolMessage):
    """Task delegation message."""
    message_type: str = Field(default="acp:task_delegation")
    
    # Task identification
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_workflow_id: Optional[str] = None
    
    # Task specification
    task_description: str
    task_type: str
    required_capabilities: List[str] = Field(default_factory=list)
    
    # Delegation details
    delegate_to: Optional[str] = None  # Specific agent ID
    delegation_criteria: Dict[str, Any] = Field(default_factory=dict)
    selection_strategy: str = "best_fit"  # "best_fit", "round_robin", "least_loaded"
    
    # Task parameters
    input_data: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Dict[str, Any] = Field(default_factory=dict)
    quality_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution constraints
    deadline: Optional[datetime] = None
    resource_budget: Optional[Dict[str, Any]] = None
    priority_override: Optional[MessagePriority] = None


class ACPSessionManagement(BaseProtocolMessage):
    """Session state management message."""
    message_type: str = Field(default="acp:session_management")
    
    # Session identification
    session_id: str
    session_type: str  # "conversation", "workflow", "collaboration"
    
    # Session operation
    session_operation: str  # "create", "update", "query", "close", "restore"
    
    # Session state
    session_state: Dict[str, Any] = Field(default_factory=dict)
    participants: List[str] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Session persistence
    persistence_level: str = "full"  # "none", "minimal", "full"
    retention_policy: Dict[str, Any] = Field(default_factory=dict)
    
    # Session metrics
    session_duration: Optional[float] = None
    message_count: int = 0
    active_workflows: List[str] = Field(default_factory=list)


# ================================
# Protocol Service Messages
# ================================

class ProtocolHealthCheck(BaseProtocolMessage):
    """Health check message for protocol services."""
    message_type: str = Field(default="protocol:health_check")
    
    # Service identification
    service_name: str
    service_version: str
    protocol_layers: List[str] = Field(default_factory=list)
    
    # Health information
    health_status: str = "healthy"  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    active_connections: int = 0
    processing_queue_size: int = 0
    
    # Performance metrics
    average_response_time: Optional[float] = None
    throughput_messages_per_second: Optional[float] = None
    error_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Resource utilization
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    disk_usage_mb: Optional[float] = None


class ProtocolError(BaseProtocolMessage):
    """Protocol-level error message."""
    message_type: str = Field(default="protocol:error")
    
    # Error identification
    error_code: str
    error_category: str  # "authentication", "authorization", "validation", "processing", "network"
    
    # Error details
    error_message: str
    error_details: Dict[str, Any] = Field(default_factory=dict)
    original_message_id: Optional[str] = None
    
    # Recovery information
    is_recoverable: bool = True
    suggested_actions: List[str] = Field(default_factory=list)
    retry_after_seconds: Optional[int] = None
    
    # Error context
    stack_trace: Optional[str] = None
    system_state: Dict[str, Any] = Field(default_factory=dict)


# ================================
# Message Validation and Utilities
# ================================

class MessageValidationResult(BaseModel):
    """Result of message validation."""
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    semantic_score: float = Field(ge=0.0, le=1.0, default=1.0)
    compliance_level: str = "full"  # "none", "partial", "full"


# Protocol message union type for type checking
ProtocolMessage = Union[
    MCPToolRequest,
    MCPToolResponse, 
    MCPCapabilityAnnouncement,
    A2ADirectMessage,
    A2ACapabilityNegotiation,
    A2AAgentDiscovery,
    ACPWorkflowControl,
    ACPTaskDelegation,
    ACPSessionManagement,
    ProtocolHealthCheck,
    ProtocolError
]