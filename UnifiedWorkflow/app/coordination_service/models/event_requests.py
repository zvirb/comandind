"""Cognitive event request models."""

from typing import Dict, Any, Optional, List
from enum import Enum
import time

from pydantic import BaseModel, Field, validator


class EventType(str, Enum):
    """Types of cognitive events."""
    REASONING_COMPLETE = "reasoning_complete"
    VALIDATION_COMPLETE = "validation_complete"
    LEARNING_UPDATE = "learning_update"
    MEMORY_STORED = "memory_stored"
    PERCEPTION_ANALYSIS = "perception_analysis"
    AGENT_STATUS_CHANGE = "agent_status_change"
    WORKFLOW_STATE_CHANGE = "workflow_state_change"
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_REPORT = "error_report"


class EventPriority(str, Enum):
    """Event processing priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CognitiveEventRequest(BaseModel):
    """Request containing a cognitive event from other services."""
    
    event_type: EventType = Field(
        ...,
        description="Type of cognitive event"
    )
    
    event_id: Optional[str] = Field(
        default=None,
        description="Unique event identifier (auto-generated if not provided)"
    )
    
    source_service: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the service that generated the event"
    )
    
    workflow_id: Optional[str] = Field(
        default=None,
        description="Associated workflow ID"
    )
    
    agent_name: Optional[str] = Field(
        default=None,
        description="Associated agent name"
    )
    
    priority: EventPriority = Field(
        default=EventPriority.MEDIUM,
        description="Event processing priority"
    )
    
    event_data: Dict[str, Any] = Field(
        ...,
        description="Event-specific data payload"
    )
    
    timestamp: Optional[float] = Field(
        default_factory=time.time,
        description="Event timestamp (Unix timestamp)"
    )
    
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for related events"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )
    
    requires_response: bool = Field(
        default=False,
        description="Whether this event requires a response"
    )
    
    response_timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=300,
        description="Timeout for response if required"
    )
    
    @validator('event_data')
    def validate_event_data(cls, v):
        if not v:
            raise ValueError("Event data cannot be empty")
        
        # Estimate payload size
        payload_str = str(v)
        if len(payload_str) > 50000:  # ~12,500 tokens
            raise ValueError("Event payload is too large")
        
        return v
    
    @validator('response_timeout_seconds')
    def validate_response_timeout(cls, v, values):
        requires_response = values.get('requires_response', False)
        
        if requires_response and v is None:
            raise ValueError("Response timeout must be specified when response is required")
        
        if not requires_response and v is not None:
            raise ValueError("Response timeout should not be specified when response is not required")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "reasoning_complete",
                "source_service": "reasoning-service",
                "workflow_id": "wf_auth_implementation_123",
                "priority": "high",
                "event_data": {
                    "reasoning_type": "evidence_validation",
                    "confidence_score": 0.92,
                    "result_summary": "Authentication implementation meets security requirements",
                    "evidence_count": 5,
                    "processing_time_ms": 1250,
                    "recommendations": [
                        "Add rate limiting to login endpoint",
                        "Implement stronger password requirements"
                    ]
                },
                "timestamp": 1703875200.0,
                "correlation_id": "reasoning_session_456",
                "metadata": {
                    "service_version": "1.0.0",
                    "model_used": "llama3.2:3b",
                    "validation_threshold": 0.85
                },
                "requires_response": False
            }
        }


class EventBatchRequest(BaseModel):
    """Request to process multiple cognitive events in batch."""
    
    events: List[CognitiveEventRequest] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="Batch of cognitive events to process"
    )
    
    batch_id: Optional[str] = Field(
        default=None,
        description="Unique batch identifier"
    )
    
    processing_priority: EventPriority = Field(
        default=EventPriority.MEDIUM,
        description="Overall batch processing priority"
    )
    
    parallel_processing: bool = Field(
        default=True,
        description="Whether events can be processed in parallel"
    )
    
    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first failure"
    )
    
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=1800,
        description="Timeout for entire batch processing"
    )
    
    @validator('events')
    def validate_events(cls, v):
        if not v:
            raise ValueError("At least one event is required")
        
        # Check for duplicate event IDs
        event_ids = [event.event_id for event in v if event.event_id]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("Duplicate event IDs in batch")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "events": [
                    {
                        "event_type": "reasoning_complete",
                        "source_service": "reasoning-service", 
                        "workflow_id": "wf_123",
                        "event_data": {"confidence": 0.9}
                    },
                    {
                        "event_type": "validation_complete",
                        "source_service": "reasoning-service",
                        "workflow_id": "wf_123",
                        "event_data": {"valid": True}
                    }
                ],
                "processing_priority": "high",
                "parallel_processing": True,
                "fail_fast": False,
                "timeout_seconds": 120
            }
        }


class EventSubscriptionRequest(BaseModel):
    """Request to subscribe to cognitive events."""
    
    subscription_id: Optional[str] = Field(
        default=None,
        description="Unique subscription identifier"
    )
    
    event_types: List[EventType] = Field(
        ...,
        min_items=1,
        description="Event types to subscribe to"
    )
    
    source_services: Optional[List[str]] = Field(
        default=None,
        description="Filter by source services (all if not specified)"
    )
    
    workflow_filter: Optional[str] = Field(
        default=None,
        description="Filter by workflow ID pattern"
    )
    
    agent_filter: Optional[str] = Field(
        default=None,
        description="Filter by agent name pattern"
    )
    
    priority_filter: Optional[List[EventPriority]] = Field(
        default=None,
        description="Filter by event priorities"
    )
    
    callback_url: Optional[str] = Field(
        default=None,
        description="URL to receive event notifications"
    )
    
    webhook_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom headers for webhook calls"
    )
    
    batch_events: bool = Field(
        default=False,
        description="Batch events before sending"
    )
    
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum events per batch"
    )
    
    batch_timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=300,
        description="Maximum time to wait for batch completion"
    )
    
    active: bool = Field(
        default=True,
        description="Whether subscription is active"
    )
    
    @validator('batch_size')
    def validate_batch_size(cls, v, values):
        batch_events = values.get('batch_events', False)
        
        if batch_events and v is None:
            raise ValueError("Batch size must be specified when batching is enabled")
        
        if not batch_events and v is not None:
            raise ValueError("Batch size should not be specified when batching is disabled")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "event_types": ["reasoning_complete", "validation_complete"],
                "source_services": ["reasoning-service"],
                "priority_filter": ["high", "critical"],
                "callback_url": "https://api.example.com/events/webhook",
                "webhook_headers": {
                    "Authorization": "Bearer token123",
                    "Content-Type": "application/json"
                },
                "batch_events": True,
                "batch_size": 10,
                "batch_timeout_seconds": 30,
                "active": True
            }
        }