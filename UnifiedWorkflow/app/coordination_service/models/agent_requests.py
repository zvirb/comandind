"""Agent assignment and management request models."""

from typing import List, Dict, Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class TaskPriority(str, Enum):
    """Task execution priorities."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class ContextCompressionLevel(str, Enum):
    """Context compression levels."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TaskAssignment(BaseModel):
    """Individual task assignment for an agent."""
    
    task_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier for the task"
    )
    
    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the agent to assign the task to"
    )
    
    task_description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Detailed task description"
    )
    
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task execution priority"
    )
    
    estimated_duration_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=480,
        description="Estimated task duration in minutes"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on"
    )
    
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Required agent capabilities for this task"
    )
    
    task_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific context information"
    )
    
    success_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Criteria for determining task success"
    )
    
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for this task"
    )
    
    timeout_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=120,
        description="Task timeout in minutes"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "analyze_security_vulnerabilities",
                "agent_name": "security-validator",
                "task_description": "Analyze codebase for security vulnerabilities and provide recommendations",
                "priority": "high",
                "estimated_duration_minutes": 30,
                "dependencies": ["code_analysis_complete"],
                "required_capabilities": ["security_testing", "vulnerability_assessment"],
                "task_context": {
                    "target_files": ["auth.py", "api.py"],
                    "security_standards": ["OWASP", "NIST"],
                    "previous_findings": []
                },
                "success_criteria": {
                    "vulnerabilities_found": True,
                    "recommendations_provided": True,
                    "confidence_score": 0.85
                },
                "max_retries": 2,
                "timeout_minutes": 45
            }
        }


class ContextRequirement(BaseModel):
    """Context generation requirements for an agent."""
    
    agent_name: str = Field(
        ...,
        description="Agent name for context generation"
    )
    
    max_tokens: int = Field(
        default=4000,
        ge=500,
        le=8000,
        description="Maximum tokens for context package"
    )
    
    include_sections: List[str] = Field(
        default_factory=lambda: ["task_description", "relevant_context", "success_criteria"],
        description="Sections to include in context package"
    )
    
    exclude_sections: List[str] = Field(
        default_factory=list,
        description="Sections to exclude from context package"
    )
    
    compression_level: ContextCompressionLevel = Field(
        default=ContextCompressionLevel.MODERATE,
        description="Context compression level"
    )
    
    prioritize_recent: bool = Field(
        default=True,
        description="Prioritize recent context over older information"
    )
    
    include_related_tasks: bool = Field(
        default=True,
        description="Include context from related tasks"
    )
    
    custom_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom context to include"
    )
    
    context_filters: Optional[List[str]] = Field(
        default=None,
        description="Filters to apply to context generation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "agent_name": "security-validator",
                "max_tokens": 3500,
                "include_sections": [
                    "task_description",
                    "code_analysis_results", 
                    "security_requirements",
                    "previous_findings"
                ],
                "exclude_sections": ["debug_logs"],
                "compression_level": "moderate",
                "prioritize_recent": True,
                "include_related_tasks": True,
                "custom_context": {
                    "security_framework": "OWASP",
                    "compliance_requirements": ["SOC2", "GDPR"]
                },
                "context_filters": ["high_severity_only", "actionable_items"]
            }
        }


class AgentAssignmentRequest(BaseModel):
    """Request to assign agents to workflow tasks."""
    
    workflow_id: str = Field(
        ...,
        min_length=1,
        description="Workflow identifier"
    )
    
    assignments: List[TaskAssignment] = Field(
        ...,
        min_items=1,
        max_items=15,
        description="Task assignments for agents"
    )
    
    context_requirements: List[ContextRequirement] = Field(
        default_factory=list,
        description="Context generation requirements for agents"
    )
    
    execution_strategy: str = Field(
        default="optimal",
        description="Execution strategy (parallel, sequential, optimal)"
    )
    
    enable_fallback_agents: bool = Field(
        default=True,
        description="Enable automatic fallback to alternative agents"
    )
    
    global_timeout_minutes: Optional[int] = Field(
        default=None,
        ge=5,
        le=480,
        description="Global timeout for all assignments"
    )
    
    notification_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Notification preferences for assignment updates"
    )
    
    @validator('assignments')
    def validate_assignments(cls, v):
        if not v:
            raise ValueError("At least one task assignment is required")
        
        # Check for duplicate task IDs
        task_ids = [assignment.task_id for assignment in v]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")
        
        # Validate agent names
        agent_names = [assignment.agent_name for assignment in v]
        if not agent_names:
            raise ValueError("At least one agent must be assigned")
        
        return v
    
    @validator('context_requirements')
    def validate_context_requirements(cls, v, values):
        if not v:
            return v
        
        # Check that context requirements match assigned agents
        assignments = values.get('assignments', [])
        assigned_agents = {assignment.agent_name for assignment in assignments}
        
        for req in v:
            if req.agent_name not in assigned_agents:
                raise ValueError(f"Context requirement for unassigned agent: {req.agent_name}")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "wf_auth_implementation_123",
                "assignments": [
                    {
                        "task_id": "security_analysis",
                        "agent_name": "security-validator",
                        "task_description": "Analyze authentication implementation for security vulnerabilities",
                        "priority": "high",
                        "estimated_duration_minutes": 30,
                        "required_capabilities": ["security_testing", "vulnerability_assessment"],
                        "task_context": {
                            "target_files": ["auth.py", "middleware.py"],
                            "security_standards": ["OWASP", "NIST"]
                        }
                    },
                    {
                        "task_id": "code_review",
                        "agent_name": "code-quality-guardian",
                        "task_description": "Review authentication code for quality and best practices",
                        "priority": "medium",
                        "dependencies": ["security_analysis"],
                        "required_capabilities": ["code_analysis", "best_practices"]
                    }
                ],
                "context_requirements": [
                    {
                        "agent_name": "security-validator",
                        "max_tokens": 3500,
                        "compression_level": "moderate",
                        "include_sections": ["security_requirements", "code_analysis"]
                    }
                ],
                "execution_strategy": "optimal",
                "enable_fallback_agents": True,
                "global_timeout_minutes": 120
            }
        }


class AgentStatusRequest(BaseModel):
    """Request for agent status information."""
    
    agent_names: Optional[List[str]] = Field(
        default=None,
        description="Specific agents to query (all if not specified)"
    )
    
    include_inactive: bool = Field(
        default=False,
        description="Include inactive agents in response"
    )
    
    include_metrics: bool = Field(
        default=True,
        description="Include performance metrics"
    )
    
    include_current_tasks: bool = Field(
        default=True,
        description="Include current task assignments"
    )
    
    include_capabilities: bool = Field(
        default=False,
        description="Include agent capabilities"
    )
    
    metrics_time_range_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Time range for metrics in hours"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "agent_names": ["security-validator", "code-quality-guardian"],
                "include_inactive": False,
                "include_metrics": True,
                "include_current_tasks": True,
                "include_capabilities": True,
                "metrics_time_range_hours": 24
            }
        }