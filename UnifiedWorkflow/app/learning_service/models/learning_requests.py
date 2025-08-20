"""
Learning Service Request Models
==============================

Pydantic models for learning service API requests including
outcome learning, pattern search, and performance analysis.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class OutcomeType(str, Enum):
    """Types of learning outcomes from cognitive services."""
    REASONING_SUCCESS = "reasoning_success"
    REASONING_FAILURE = "reasoning_failure"
    COORDINATION_SUCCESS = "coordination_success"
    COORDINATION_FAILURE = "coordination_failure"
    AGENT_SUCCESS = "agent_success"
    AGENT_FAILURE = "agent_failure"
    WORKFLOW_SUCCESS = "workflow_success"
    WORKFLOW_FAILURE = "workflow_failure"


class PatternSearchScope(str, Enum):
    """Scope for pattern searching."""
    LOCAL = "local"      # Current context only
    GLOBAL = "global"    # All stored patterns
    SIMILAR = "similar"  # Semantically similar contexts
    RECENT = "recent"    # Recently learned patterns


class PerformanceMetricType(str, Enum):
    """Types of performance metrics to analyze."""
    ACCURACY = "accuracy"
    SPEED = "speed"
    SUCCESS_RATE = "success_rate"
    RESOURCE_USAGE = "resource_usage"
    ERROR_RATE = "error_rate"
    COMPLETION_TIME = "completion_time"


class OutcomeLearningRequest(BaseModel):
    """Request to learn from a cognitive service outcome."""
    
    outcome_type: OutcomeType = Field(
        ..., description="Type of outcome to learn from"
    )
    service_name: str = Field(
        ..., description="Name of the service that generated the outcome"
    )
    context: Dict[str, Any] = Field(
        ..., description="Context in which the outcome occurred"
    )
    input_data: Dict[str, Any] = Field(
        ..., description="Input data that led to the outcome"
    )
    output_data: Optional[Dict[str, Any]] = Field(
        None, description="Output data from the successful outcome"
    )
    error_data: Optional[Dict[str, Any]] = Field(
        None, description="Error data from the failed outcome"
    )
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Performance metrics for the outcome"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the outcome occurred"
    )
    session_id: Optional[str] = Field(
        None, description="Session identifier for grouping related outcomes"
    )
    
    @validator('context', 'input_data')
    def validate_not_empty(cls, v):
        if not v:
            raise ValueError("Context and input_data cannot be empty")
        return v


class PatternSearchRequest(BaseModel):
    """Request to search for matching patterns."""
    
    context: Dict[str, Any] = Field(
        ..., description="Current context to find patterns for"
    )
    search_scope: PatternSearchScope = Field(
        default=PatternSearchScope.GLOBAL, 
        description="Scope of pattern search"
    )
    similarity_threshold: Optional[float] = Field(
        None, description="Override default similarity threshold"
    )
    max_results: int = Field(
        default=10, description="Maximum number of patterns to return"
    )
    include_metrics: bool = Field(
        default=True, description="Include pattern performance metrics"
    )
    filter_by_success: Optional[bool] = Field(
        None, description="Filter patterns by success rate if specified"
    )
    outcome_types: Optional[List[OutcomeType]] = Field(
        None, description="Filter patterns by outcome types"
    )
    
    @validator('similarity_threshold')
    def validate_threshold(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        return v
    
    @validator('max_results')
    def validate_max_results(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("Max results must be between 1 and 100")
        return v


class PatternApplicationRequest(BaseModel):
    """Request to apply a learned pattern to a new situation."""
    
    pattern_id: str = Field(
        ..., description="ID of the pattern to apply"
    )
    current_context: Dict[str, Any] = Field(
        ..., description="Current context to apply the pattern to"
    )
    adaptation_enabled: bool = Field(
        default=True, description="Allow pattern adaptation for context"
    )
    confidence_threshold: Optional[float] = Field(
        None, description="Override default confidence threshold"
    )
    dry_run: bool = Field(
        default=False, description="Test pattern application without execution"
    )
    expected_outcome: Optional[Dict[str, Any]] = Field(
        None, description="Expected outcome for validation"
    )
    
    @validator('confidence_threshold')
    def validate_confidence(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v


class PerformanceAnalysisRequest(BaseModel):
    """Request to analyze agent or workflow performance patterns."""
    
    analysis_type: str = Field(
        ..., description="Type of analysis (agent, workflow, service)"
    )
    subject_id: str = Field(
        ..., description="ID of the subject to analyze"
    )
    time_range: Optional[Dict[str, datetime]] = Field(
        None, description="Time range for analysis (start, end)"
    )
    metrics: List[PerformanceMetricType] = Field(
        default_factory=lambda: [PerformanceMetricType.SUCCESS_RATE],
        description="Performance metrics to analyze"
    )
    comparison_subjects: Optional[List[str]] = Field(
        None, description="Other subjects to compare against"
    )
    include_patterns: bool = Field(
        default=True, description="Include identified patterns in response"
    )
    include_recommendations: bool = Field(
        default=True, description="Include optimization recommendations"
    )
    granularity: str = Field(
        default="daily", description="Analysis granularity (hourly, daily, weekly)"
    )
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        valid_types = ['agent', 'workflow', 'service', 'system']
        if v not in valid_types:
            raise ValueError(f"Analysis type must be one of: {valid_types}")
        return v
    
    @validator('granularity')
    def validate_granularity(cls, v):
        valid_granularities = ['hourly', 'daily', 'weekly', 'monthly']
        if v not in valid_granularities:
            raise ValueError(f"Granularity must be one of: {valid_granularities}")
        return v


class RecommendationRequest(BaseModel):
    """Request for AI-driven optimization recommendations."""
    
    context: Dict[str, Any] = Field(
        ..., description="Current system context"
    )
    focus_areas: Optional[List[str]] = Field(
        None, description="Specific areas to focus recommendations on"
    )
    performance_goals: Dict[str, float] = Field(
        default_factory=dict, description="Performance targets"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict, description="System constraints to consider"
    )
    priority: str = Field(
        default="balanced", description="Recommendation priority (speed, accuracy, resource)"
    )
    include_rationale: bool = Field(
        default=True, description="Include explanation for recommendations"
    )
    max_recommendations: int = Field(
        default=5, description="Maximum number of recommendations"
    )
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ['speed', 'accuracy', 'resource', 'balanced']
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v
    
    @validator('max_recommendations')
    def validate_max_recommendations(cls, v):
        if v <= 0 or v > 20:
            raise ValueError("Max recommendations must be between 1 and 20")
        return v