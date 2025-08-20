"""Workflow request models for the Coordination Service."""

from typing import List, Dict, Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class WorkflowType(str, Enum):
    """Supported workflow types."""
    NEW_FEATURE = "new_feature"
    BUG_FIX = "bug_fix"
    SYSTEM_INTEGRATION = "system_integration"
    SECURITY_AUDIT = "security_audit"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    CUSTOM = "custom"


class WorkflowPriority(str, Enum):
    """Workflow execution priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(str, Enum):
    """Workflow execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"
    AUTO = "auto"  # Let system decide based on dependencies


class WorkflowCreateRequest(BaseModel):
    """Request to create a new multi-agent workflow."""
    
    workflow_type: WorkflowType = Field(
        ..., 
        description="Type of workflow to create"
    )
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Human-readable workflow name"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed workflow description"
    )
    
    priority: WorkflowPriority = Field(
        default=WorkflowPriority.MEDIUM,
        description="Workflow execution priority"
    )
    
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.AUTO,
        description="How agents should be executed"
    )
    
    required_agents: List[str] = Field(
        ...,
        min_items=1,
        max_items=15,
        description="List of required agent names"
    )
    
    optional_agents: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="List of optional agent names"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial context for the workflow"
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-specific parameters"
    )
    
    timeout_minutes: Optional[int] = Field(
        default=60,
        ge=1,
        le=240,
        description="Workflow timeout in minutes"
    )
    
    enable_recovery: bool = Field(
        default=True,
        description="Enable automatic recovery on failure"
    )
    
    enable_optimization: bool = Field(
        default=True,
        description="Enable workflow optimization"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed agents"
    )
    
    dependencies: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Agent execution dependencies"
    )
    
    success_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Criteria for determining workflow success"
    )
    
    @validator('required_agents')
    def validate_required_agents(cls, v):
        if not v:
            raise ValueError("At least one required agent must be specified")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Required agents list contains duplicates")
        
        return v
    
    @validator('optional_agents')
    def validate_optional_agents(cls, v, values):
        if not v:
            return v
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Optional agents list contains duplicates")
        
        # Check for overlap with required agents
        required = values.get('required_agents', [])
        if any(agent in required for agent in v):
            raise ValueError("Optional agents cannot overlap with required agents")
        
        return v
    
    @validator('context')
    def validate_context(cls, v):
        # Rough estimate of context size (in characters)
        context_str = str(v)
        if len(context_str) > 10000:  # ~2500 tokens
            raise ValueError("Initial context is too large (max ~2500 tokens)")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_type": "new_feature",
                "name": "Implement User Authentication",
                "description": "Add JWT-based authentication system",
                "priority": "high",
                "execution_mode": "mixed",
                "required_agents": [
                    "project-orchestrator",
                    "codebase-research-analyst", 
                    "security-validator"
                ],
                "optional_agents": [
                    "test-automation-engineer",
                    "documentation-specialist"
                ],
                "context": {
                    "project_phase": "Phase 2",
                    "target_files": ["auth.py", "models.py"],
                    "requirements": ["JWT tokens", "password hashing", "role-based access"]
                },
                "parameters": {
                    "security_level": "high",
                    "compliance_requirements": ["GDPR", "SOC2"]
                },
                "timeout_minutes": 90,
                "enable_recovery": True,
                "enable_optimization": True,
                "max_retries": 3,
                "success_criteria": {
                    "tests_pass": True,
                    "security_scan_pass": True,
                    "documentation_complete": True
                }
            }
        }


class WorkflowPauseRequest(BaseModel):
    """Request to pause a workflow."""
    
    preserve_state: bool = Field(
        default=True,
        description="Whether to preserve workflow state"
    )
    
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for pausing the workflow"
    )
    
    graceful_shutdown: bool = Field(
        default=True,
        description="Allow running agents to complete before pausing"
    )
    
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Timeout for graceful shutdown"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "preserve_state": True,
                "reason": "System maintenance required",
                "graceful_shutdown": True,
                "timeout_seconds": 120
            }
        }


class WorkflowResumeRequest(BaseModel):
    """Request to resume a paused workflow."""
    
    regenerate_context: bool = Field(
        default=True,
        description="Whether to regenerate context packages for agents"
    )
    
    reset_failed_agents: bool = Field(
        default=False,
        description="Reset any previously failed agents"
    )
    
    update_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated parameters for the workflow"
    )
    
    priority_override: Optional[WorkflowPriority] = Field(
        default=None,
        description="Override workflow priority on resume"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "regenerate_context": True,
                "reset_failed_agents": False,
                "update_parameters": {
                    "retry_count": 1,
                    "timeout_extension": 30
                },
                "priority_override": "high"
            }
        }


class WorkflowModifyRequest(BaseModel):
    """Request to modify an active workflow."""
    
    add_agents: List[str] = Field(
        default_factory=list,
        description="Agents to add to the workflow"
    )
    
    remove_agents: List[str] = Field(
        default_factory=list,
        description="Agents to remove from the workflow"
    )
    
    update_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context updates to apply"
    )
    
    update_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameter updates to apply"
    )
    
    new_priority: Optional[WorkflowPriority] = Field(
        default=None,
        description="New priority for the workflow"
    )
    
    extend_timeout_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Minutes to extend the workflow timeout"
    )
    
    @validator('add_agents', 'remove_agents')
    def no_duplicates(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Agent lists cannot contain duplicates")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "add_agents": ["performance-profiler"],
                "remove_agents": [],
                "update_context": {
                    "optimization_target": "response_time"
                },
                "update_parameters": {
                    "max_latency_ms": 200
                },
                "new_priority": "high",
                "extend_timeout_minutes": 30
            }
        }