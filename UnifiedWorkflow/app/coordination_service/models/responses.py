"""Response models for the Coordination Service API."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status queries."""
    
    workflow_id: str = Field(..., description="Unique workflow identifier")
    current_state: str = Field(..., description="Current workflow state")
    sequence_number: int = Field(..., description="State sequence number")
    checkpoint_id: str = Field(..., description="Current checkpoint identifier")
    created_at: float = Field(..., description="Workflow creation timestamp")
    execution_time_seconds: float = Field(..., description="Total execution time")
    is_active: bool = Field(..., description="Whether workflow is currently active")
    is_complete: bool = Field(..., description="Whether workflow is complete")
    progress_percentage: Optional[float] = Field(None, description="Completion percentage if available")
    estimated_completion: Optional[float] = Field(None, description="Estimated completion timestamp")
    state_data: Dict[str, Any] = Field(default_factory=dict, description="Current state data")
    recovery_metadata: Optional[Dict[str, Any]] = Field(None, description="Recovery metadata if applicable")
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "wf_auth_implementation_123",
                "current_state": "running",
                "sequence_number": 5,
                "checkpoint_id": "checkpoint_wf_auth_implementation_123_1703875200",
                "created_at": 1703875000.0,
                "execution_time_seconds": 200.0,
                "is_active": True,
                "is_complete": False,
                "progress_percentage": 65.0,
                "estimated_completion": 1703876000.0,
                "state_data": {
                    "agents_assigned": 3,
                    "completed_tasks": 2,
                    "current_phase": "implementation"
                },
                "recovery_metadata": None
            }
        }


class AgentStatusResponse(BaseModel):
    """Response model for agent status information."""
    
    agent_name: str = Field(..., description="Agent name")
    category: str = Field(..., description="Agent category")
    status: str = Field(..., description="Current agent status")
    current_workload: int = Field(..., description="Current number of assigned tasks")
    max_concurrent: int = Field(..., description="Maximum concurrent tasks")
    utilization_rate: float = Field(..., description="Current utilization rate (0.0 to 1.0)")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    last_seen: float = Field(..., description="Last heartbeat timestamp")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    endpoint_url: Optional[str] = Field(None, description="Agent endpoint URL")
    version: str = Field(default="1.0.0", description="Agent version")
    
    class Config:
        schema_extra = {
            "example": {
                "agent_name": "security-validator",
                "category": "security-quality",
                "status": "available",
                "current_workload": 2,
                "max_concurrent": 3,
                "utilization_rate": 0.67,
                "capabilities": ["security_testing", "vulnerability_assessment", "real_time_validation"],
                "last_seen": 1703875200.0,
                "performance_metrics": {
                    "success_rate": 0.95,
                    "avg_response_time": 120.5,
                    "total_tasks_completed": 47
                },
                "endpoint_url": "http://security-validator:8080",
                "version": "1.0.0"
            }
        }


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""
    
    timestamp: float = Field(..., description="Metrics timestamp")
    window_seconds: int = Field(..., description="Time window for metrics")
    metrics: Dict[str, Dict[str, float]] = Field(..., description="Performance metrics by type")
    active_alerts: int = Field(..., description="Number of active performance alerts")
    system_health: str = Field(..., description="Overall system health status")
    
    class Config:
        schema_extra = {
            "example": {
                "timestamp": 1703875200.0,
                "window_seconds": 300,
                "metrics": {
                    "workflow_completion_time": {
                        "current": 480.5,
                        "avg": 520.2,
                        "min": 360.1,
                        "max": 720.8,
                        "count": 12
                    },
                    "agent_utilization": {
                        "current": 0.72,
                        "avg": 0.68,
                        "min": 0.45,
                        "max": 0.89,
                        "count": 25
                    }
                },
                "active_alerts": 2,
                "system_health": "good"
            }
        }


class WorkflowAnalyticsResponse(BaseModel):
    """Response model for workflow analytics."""
    
    workflow_statistics: Dict[str, Any] = Field(..., description="Workflow execution statistics")
    agent_utilization: Dict[str, Any] = Field(..., description="Agent utilization statistics")
    performance_insights: Dict[str, Any] = Field(..., description="Performance analysis insights")
    system_health: Dict[str, Any] = Field(..., description="System health indicators")
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_statistics": {
                    "total_active": 8,
                    "running": 5,
                    "completed": 142,
                    "completion_rate": 0.94,
                    "avg_completion_time_minutes": 12.5
                },
                "agent_utilization": {
                    "total_agents": 47,
                    "busy_agents": 12,
                    "utilization_rate": 0.26,
                    "avg_workload": 0.8
                },
                "performance_insights": {
                    "bottleneck_agents": ["security-validator", "performance-profiler"],
                    "optimization_opportunities": [
                        "Underutilized agents: documentation-specialist, project-janitor",
                        "Consider scaling high-demand agents"
                    ],
                    "resource_recommendations": [
                        "Consider scaling high-demand agents: security-validator",
                        "Consider increasing max_concurrent_workflows"
                    ]
                },
                "system_health": {
                    "orchestration_running": True,
                    "queue_length": 3,
                    "active_assignments": 18
                }
            }
        }


class CognitiveEventResponse(BaseModel):
    """Response model for cognitive event processing."""
    
    event_id: str = Field(..., description="Unique event identifier")
    processed: bool = Field(..., description="Whether event was processed")
    workflow_updates: List[str] = Field(default_factory=list, description="Workflow IDs that were updated")
    processed_at: float = Field(..., description="Processing completion timestamp")
    processing_result: Optional[Dict[str, Any]] = Field(None, description="Processing result details")
    
    class Config:
        schema_extra = {
            "example": {
                "event_id": "evt_reasoning_complete_456",
                "processed": True,
                "workflow_updates": ["wf_auth_implementation_123"],
                "processed_at": 1703875200.0,
                "processing_result": {
                    "action_taken": "learning_feedback_sent",
                    "confidence_score": 0.92,
                    "feedback_type": "reasoning_performance"
                }
            }
        }


class AgentAssignmentResponse(BaseModel):
    """Response model for agent assignment operations."""
    
    workflow_id: str = Field(..., description="Workflow identifier")
    assignments: List[Dict[str, Any]] = Field(..., description="Created agent assignments")
    context_packages_generated: int = Field(..., description="Number of context packages generated")
    assigned_at: float = Field(..., description="Assignment timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "wf_auth_implementation_123",
                "assignments": [
                    {
                        "agent_name": "security-validator",
                        "task_id": "security_analysis",
                        "status": "assigned",
                        "context_package_id": "ctx_wf_auth_implementation_123_security_validator_1703875200"
                    },
                    {
                        "agent_name": "code-quality-guardian",
                        "task_id": "code_review",
                        "status": "assigned",
                        "context_package_id": "ctx_wf_auth_implementation_123_code_quality_guardian_1703875205"
                    }
                ],
                "context_packages_generated": 2,
                "assigned_at": 1703875200.0
            }
        }


class ActiveAgentsResponse(BaseModel):
    """Response model for active agent assignments."""
    
    total_active: int = Field(..., description="Total number of active agents")
    agents: List[AgentStatusResponse] = Field(..., description="Active agent details")
    last_updated: float = Field(..., description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "total_active": 5,
                "agents": [
                    {
                        "agent_name": "security-validator",
                        "category": "security-quality",
                        "status": "busy",
                        "current_workload": 2,
                        "max_concurrent": 3,
                        "utilization_rate": 0.67,
                        "capabilities": ["security_testing", "vulnerability_assessment"],
                        "last_seen": 1703875200.0,
                        "performance_metrics": {"success_rate": 0.95},
                        "version": "1.0.0"
                    }
                ],
                "last_updated": 1703875200.0
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: float = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "Validation Error",
                "detail": "Required agents not available: security-validator",
                "timestamp": 1703875200.0,
                "request_id": "req_12345"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    timestamp: float = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    service: str = Field(..., description="Service name")
    redis_connected: bool = Field(..., description="Redis connection status")
    agent_registry: Dict[str, Any] = Field(..., description="Agent registry status")
    workflow_manager: Dict[str, Any] = Field(..., description="Workflow manager status")
    performance: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    uptime_seconds: float = Field(..., description="Service uptime")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": 1703875200.0,
                "version": "1.0.0",
                "service": "coordination-service",
                "redis_connected": True,
                "agent_registry": {
                    "total_agents": 47,
                    "status": "operational"
                },
                "workflow_manager": {
                    "active_workflows": 8,
                    "status": "operational"
                },
                "performance": {
                    "avg_response_time": 0.15,
                    "completion_rate": 0.95
                },
                "uptime_seconds": 3600.0
            }
        }


class DetailedStatusResponse(BaseModel):
    """Detailed service status response model."""
    
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: float = Field(..., description="Status timestamp")
    uptime_seconds: float = Field(..., description="Service uptime")
    redis: Optional[Dict[str, Any]] = Field(None, description="Redis service status")
    agents: Optional[Dict[str, Any]] = Field(None, description="Agent registry status")
    workflows: Optional[Dict[str, Any]] = Field(None, description="Workflow manager status")
    cognitive_events: Optional[Dict[str, Any]] = Field(None, description="Cognitive event handler status")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance monitor status")
    orchestrator: Optional[Dict[str, Any]] = Field(None, description="Orchestrator status")
    
    class Config:
        schema_extra = {
            "example": {
                "service": "coordination-service",
                "version": "1.0.0",
                "timestamp": 1703875200.0,
                "uptime_seconds": 3600.0,
                "redis": {
                    "connection_status": "connected",
                    "total_operations": 1250,
                    "cache_hit_rate": 0.87
                },
                "agents": {
                    "total_agents": 47,
                    "available_agents": 35,
                    "routing_success_rate": 0.98
                },
                "workflows": {
                    "active_workflows": 8,
                    "recovery_in_progress": False,
                    "last_checkpoint_time": 1703875100.0
                },
                "cognitive_events": {
                    "processing_status": "running",
                    "queue_size": 2,
                    "processed_events": 324
                },
                "performance": {
                    "monitoring_running": True,
                    "active_alerts": 1,
                    "avg_processing_time": 0.05
                },
                "orchestrator": {
                    "orchestration_status": "running",
                    "active_workflows": 8,
                    "queued_workflows": 2
                }
            }
        }