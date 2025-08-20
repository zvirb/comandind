"""
Semantic Analysis Schemas - Pydantic models for semantic analysis requests and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class TaskSemanticAnalysisRequest(BaseModel):
    """Request schema for task semantic analysis."""
    
    task_text: str = Field(..., min_length=1, max_length=500, description="Main task title/text")
    task_description: Optional[str] = Field(None, max_length=2000, description="Optional detailed description")
    
    @validator('task_text')
    def validate_task_text(cls, v):
        if not v.strip():
            raise ValueError('Task text cannot be empty')
        return v.strip()


class EventSemanticAnalysisRequest(BaseModel):
    """Request schema for event semantic analysis."""
    
    event_title: str = Field(..., min_length=1, max_length=500, description="Event title")
    event_description: Optional[str] = Field(None, max_length=2000, description="Optional event description")
    event_location: Optional[str] = Field(None, max_length=300, description="Optional event location")
    
    @validator('event_title')
    def validate_event_title(cls, v):
        if not v.strip():
            raise ValueError('Event title cannot be empty')
        return v.strip()


class SemanticAnalysisResult(BaseModel):
    """Semantic analysis result."""
    
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    semantic_category: str = Field(..., description="Assigned semantic category")
    priority_level: Optional[str] = Field(None, description="Priority level for tasks")
    importance_level: Optional[str] = Field(None, description="Importance level for events")
    complexity_level: Optional[str] = Field(None, description="Complexity level for tasks")
    time_information: Dict[str, Any] = Field(default_factory=dict, description="Time-related information")
    attendee_information: Optional[Dict[str, Any]] = Field(None, description="Attendee information for events")
    tags: List[str] = Field(default_factory=list, description="Generated tags")
    summary: str = Field(..., description="Analysis summary")
    personalization: Dict[str, Any] = Field(default_factory=dict, description="User-specific insights")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence score")
    analysis_timestamp: str = Field(..., description="Timestamp of analysis")


class SemanticUpdateRequest(BaseModel):
    """Request schema for updating semantic fields."""
    
    force_update: bool = Field(False, description="Force update even if already analyzed")


class BulkAnalysisResult(BaseModel):
    """Result of bulk semantic analysis."""
    
    tasks_analyzed: int = Field(..., ge=0, description="Number of tasks analyzed")
    events_analyzed: int = Field(..., ge=0, description="Number of events analyzed")
    errors: int = Field(..., ge=0, description="Number of errors encountered")


class SemanticCategoriesResponse(BaseModel):
    """Available semantic categories and keywords."""
    
    task_categories: Dict[str, List[str]] = Field(..., description="Task categories and keywords")
    event_categories: Dict[str, List[str]] = Field(..., description="Event categories and keywords")
    priority_keywords: Dict[str, List[str]] = Field(..., description="Priority level keywords")


class SemanticInsightResponse(BaseModel):
    """Semantic insight response."""
    
    id: str = Field(..., description="Insight ID")
    content_id: str = Field(..., description="Content ID")
    content_type: str = Field(..., description="Content type (task/event)")
    insight_value: Dict[str, Any] = Field(..., description="Insight data")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    created_at: str = Field(..., description="Creation timestamp")
    model_used: str = Field(..., description="Model used for analysis")


class SemanticInsightsListResponse(BaseModel):
    """List of semantic insights."""
    
    insights: List[SemanticInsightResponse] = Field(default_factory=list, description="List of insights")


class TaskSemanticUpdateResponse(BaseModel):
    """Response for task semantic field updates."""
    
    task_id: str = Field(..., description="Task ID")
    updated: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Update status message")


class EventSemanticUpdateResponse(BaseModel):
    """Response for event semantic field updates."""
    
    event_id: str = Field(..., description="Event ID")
    updated: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Update status message")


class SemanticAnalysisStats(BaseModel):
    """Statistics about semantic analysis."""
    
    total_tasks: int = Field(..., ge=0, description="Total tasks in system")
    analyzed_tasks: int = Field(..., ge=0, description="Number of analyzed tasks")
    total_events: int = Field(..., ge=0, description="Total events in system")
    analyzed_events: int = Field(..., ge=0, description="Number of analyzed events")
    most_common_categories: Dict[str, int] = Field(default_factory=dict, description="Most common categories")
    avg_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average confidence")


class SemanticSearchRequest(BaseModel):
    """Request for semantic search."""
    
    query: str = Field(..., min_length=1, max_length=300, description="Search query")
    content_type: Optional[str] = Field(None, description="Content type filter (task/event)")
    categories: Optional[List[str]] = Field(None, description="Category filters")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence score")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Search query cannot be empty')
        return v.strip()


class SemanticSearchResult(BaseModel):
    """Result of semantic search."""
    
    content_id: str = Field(..., description="Content ID")
    content_type: str = Field(..., description="Content type")
    title: str = Field(..., description="Content title")
    category: str = Field(..., description="Semantic category")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance")


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""
    
    results: List[SemanticSearchResult] = Field(default_factory=list, description="Search results")
    total_count: int = Field(..., ge=0, description="Total matching items")
    query: str = Field(..., description="Original search query")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")


class WeightedScoreRequest(BaseModel):
    """Request for weighted scoring."""
    
    content_ids: List[str] = Field(..., min_items=1, description="Content IDs to score")
    content_type: str = Field(..., description="Content type (task/event)")
    scoring_criteria: Dict[str, float] = Field(default_factory=dict, description="Custom scoring weights")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        if v not in ['task', 'event']:
            raise ValueError('Content type must be "task" or "event"')
        return v


class WeightedScoreResult(BaseModel):
    """Result of weighted scoring."""
    
    content_id: str = Field(..., description="Content ID")
    weighted_score: float = Field(..., ge=0.0, description="Calculated weighted score")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Score component breakdown")
    ranking: int = Field(..., ge=1, description="Ranking among scored items")


class WeightedScoreResponse(BaseModel):
    """Response for weighted scoring."""
    
    scores: List[WeightedScoreResult] = Field(default_factory=list, description="Weighted scores")
    scoring_criteria: Dict[str, float] = Field(default_factory=dict, description="Applied scoring criteria")
    total_scored: int = Field(..., ge=0, description="Number of items scored")


class UnstructuredAnalysisRequest(BaseModel):
    """Request schema for unstructured data analysis."""
    user_input: str = Field(..., description="The user's original prompt")
    context: str = Field(..., description="The block of text to be analyzed")