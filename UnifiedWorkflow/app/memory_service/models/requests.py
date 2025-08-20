"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class MemoryAddRequest(BaseModel):
    """Request model for adding new memory content."""
    
    content: str = Field(
        ..., 
        min_length=1, 
        max_length=10000,
        description="Memory content to be processed and stored"
    )
    content_type: str = Field(
        default="text",
        description="Type of content (text, note, conversation, etc.)"
    )
    source: Optional[str] = Field(
        None,
        max_length=100,
        description="Source of the memory (user, system, import, etc.)"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="List of tags for categorization"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the memory"
    )
    
    @validator('content')
    def validate_content(cls, v):
        """Validate content is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError('Content cannot be empty or just whitespace')
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags list."""
        if v is not None:
            # Remove duplicates and empty tags
            v = [tag.strip() for tag in v if tag and tag.strip()]
            v = list(set(v))  # Remove duplicates
            if len(v) > 20:
                raise ValueError('Maximum 20 tags allowed')
        return v


class MemoryAddResponse(BaseModel):
    """Response model for memory addition."""
    
    memory_id: UUID = Field(description="Unique identifier of the created memory")
    processed_content: str = Field(description="LLM-processed content")
    summary: Optional[str] = Field(description="Generated summary")
    confidence_score: Optional[float] = Field(description="Processing confidence score")
    related_memories: List[UUID] = Field(default=[], description="IDs of related memories found")
    processing_time_ms: float = Field(description="Total processing time in milliseconds")
    status: str = Field(default="success", description="Processing status")
    
    class Config:
        json_encoders = {
            UUID: str
        }


class MemorySearchRequest(BaseModel):
    """Request model for searching memories."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query for finding relevant memories"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for results"
    )
    content_type_filter: Optional[str] = Field(
        None,
        description="Filter results by content type"
    )
    source_filter: Optional[str] = Field(
        None,
        description="Filter results by source"
    )
    tags_filter: Optional[List[str]] = Field(
        None,
        description="Filter results by tags (any match)"
    )
    date_from: Optional[datetime] = Field(
        None,
        description="Search memories created after this date"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="Search memories created before this date"
    )
    include_summary_only: bool = Field(
        default=False,
        description="Return only summaries instead of full content"
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or just whitespace')
        return v.strip()
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Validate date range is logical."""
        if v and 'date_from' in values and values['date_from']:
            if v <= values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v


class MemorySearchResult(BaseModel):
    """Individual search result model."""
    
    memory_id: UUID = Field(description="Unique identifier of the memory")
    content: str = Field(description="Memory content (full or summary based on request)")
    summary: Optional[str] = Field(description="Memory summary")
    content_type: str = Field(description="Type of content")
    source: Optional[str] = Field(description="Source of the memory")
    tags: Optional[List[str]] = Field(description="Associated tags")
    
    # Search-specific fields
    similarity_score: float = Field(description="Similarity score to the search query")
    relevance_score: Optional[float] = Field(description="Overall relevance score")
    
    # Metadata
    created_at: datetime = Field(description="Memory creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    access_count: int = Field(description="Number of times accessed")
    consolidation_count: int = Field(description="Number of consolidations")
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""
    
    results: List[MemorySearchResult] = Field(description="List of matching memories")
    total_count: int = Field(description="Total number of matching memories")
    query: str = Field(description="Original search query")
    processing_time_ms: float = Field(description="Search processing time in milliseconds")
    similarity_threshold_used: float = Field(description="Similarity threshold applied")
    
    # Search statistics
    postgres_results: int = Field(default=0, description="Number of results from PostgreSQL")
    qdrant_results: int = Field(default=0, description="Number of results from Qdrant")
    hybrid_fusion_applied: bool = Field(default=False, description="Whether hybrid fusion was applied")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(description="Overall service status")
    timestamp: float = Field(description="Health check timestamp")
    checks: Dict[str, Any] = Field(description="Individual component health checks")
    version: str = Field(default="1.0.0", description="Service version")
    uptime_seconds: Optional[float] = Field(description="Service uptime in seconds")