"""
Learning Service Response Models
===============================

Pydantic models for learning service API responses including
learning outcomes, pattern matches, and recommendations.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from .patterns import LearningPattern, PatternMatch, PatternApplication, PatternMetrics
from .knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge


class LearningStatus(str, Enum):
    """Status of learning operations."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class RecommendationType(str, Enum):
    """Types of optimization recommendations."""
    PERFORMANCE = "performance"
    ACCURACY = "accuracy"
    RESOURCE = "resource"
    STRATEGY = "strategy"
    CONFIGURATION = "configuration"


class LearningResponse(BaseModel):
    """Response from learning outcome processing."""
    
    status: LearningStatus = Field(
        ..., description="Status of the learning operation"
    )
    patterns_learned: int = Field(
        default=0, description="Number of new patterns learned"
    )
    patterns_updated: int = Field(
        default=0, description="Number of existing patterns updated"
    )
    knowledge_graph_updates: int = Field(
        default=0, description="Number of knowledge graph updates"
    )
    learning_insights: List[str] = Field(
        default_factory=list, description="Key insights from the learning process"
    )
    pattern_ids: List[str] = Field(
        default_factory=list, description="IDs of patterns that were created/updated"
    )
    confidence_score: float = Field(
        default=0.0, description="Confidence in the learning outcome"
    )
    processing_time: float = Field(
        default=0.0, description="Time taken to process the learning request"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class PatternSearchResponse(BaseModel):
    """Response from pattern search operations."""
    
    status: LearningStatus = Field(
        ..., description="Status of the search operation"
    )
    matches: List[PatternMatch] = Field(
        default_factory=list, description="Matched patterns with similarity scores"
    )
    total_found: int = Field(
        default=0, description="Total number of patterns found"
    )
    search_time: float = Field(
        default=0.0, description="Time taken for the search"
    )
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Filters that were applied"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations based on search results"
    )
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of confidence scores"
    )


class PatternApplicationResponse(BaseModel):
    """Response from pattern application operations."""
    
    status: LearningStatus = Field(
        ..., description="Status of the application operation"
    )
    application_result: Optional[PatternApplication] = Field(
        None, description="Result of the pattern application"
    )
    adapted_pattern: Optional[LearningPattern] = Field(
        None, description="Pattern after adaptation to current context"
    )
    confidence_score: float = Field(
        default=0.0, description="Confidence in the application success"
    )
    success_probability: float = Field(
        default=0.0, description="Predicted probability of success"
    )
    recommended_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Recommended parameters for execution"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Warnings about the application"
    )
    validation_results: Dict[str, Any] = Field(
        default_factory=dict, description="Results of pattern validation"
    )


class KnowledgeGraphResponse(BaseModel):
    """Response from knowledge graph operations."""
    
    nodes: List[KnowledgeGraphNode] = Field(
        default_factory=list, description="Graph nodes in the result"
    )
    edges: List[KnowledgeGraphEdge] = Field(
        default_factory=list, description="Graph edges in the result"
    )
    total_nodes: int = Field(
        default=0, description="Total number of nodes in the graph"
    )
    total_edges: int = Field(
        default=0, description="Total number of edges in the graph"
    )
    query_time: float = Field(
        default=0.0, description="Time taken for the graph query"
    )
    visualization_data: Optional[Dict[str, Any]] = Field(
        None, description="Data for graph visualization"
    )
    insights: List[str] = Field(
        default_factory=list, description="Insights derived from the graph"
    )


class PerformanceInsight(BaseModel):
    """Individual performance insight."""
    
    type: str = Field(
        ..., description="Type of insight (trend, anomaly, opportunity)"
    )
    description: str = Field(
        ..., description="Human-readable description"
    )
    impact: str = Field(
        ..., description="Potential impact (high, medium, low)"
    )
    confidence: float = Field(
        ..., description="Confidence in the insight"
    )
    data_points: List[Dict[str, Any]] = Field(
        default_factory=list, description="Supporting data points"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended actions based on insight"
    )


class PerformanceAnalysisResponse(BaseModel):
    """Response from performance analysis operations."""
    
    status: LearningStatus = Field(
        ..., description="Status of the analysis operation"
    )
    subject_id: str = Field(
        ..., description="ID of the analyzed subject"
    )
    analysis_period: Dict[str, datetime] = Field(
        ..., description="Period covered by the analysis"
    )
    metrics: Dict[str, PatternMetrics] = Field(
        default_factory=dict, description="Performance metrics results"
    )
    patterns_identified: List[LearningPattern] = Field(
        default_factory=list, description="Performance patterns identified"
    )
    insights: List[PerformanceInsight] = Field(
        default_factory=list, description="Performance insights"
    )
    comparisons: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Comparisons with other subjects"
    )
    trends: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict, description="Trend data for each metric"
    )
    analysis_time: float = Field(
        default=0.0, description="Time taken for the analysis"
    )


class OptimizationRecommendation(BaseModel):
    """Individual optimization recommendation."""
    
    type: RecommendationType = Field(
        ..., description="Type of recommendation"
    )
    title: str = Field(
        ..., description="Short title for the recommendation"
    )
    description: str = Field(
        ..., description="Detailed description"
    )
    expected_impact: Dict[str, float] = Field(
        default_factory=dict, description="Expected impact on metrics"
    )
    implementation_effort: str = Field(
        ..., description="Implementation effort (low, medium, high)"
    )
    priority: int = Field(
        ..., description="Priority ranking (1-10)"
    )
    confidence: float = Field(
        ..., description="Confidence in the recommendation"
    )
    prerequisites: List[str] = Field(
        default_factory=list, description="Prerequisites for implementation"
    )
    risks: List[str] = Field(
        default_factory=list, description="Potential risks"
    )
    rationale: Optional[str] = Field(
        None, description="Explanation for the recommendation"
    )
    supporting_patterns: List[str] = Field(
        default_factory=list, description="Pattern IDs that support this recommendation"
    )


class RecommendationResponse(BaseModel):
    """Response from recommendation generation."""
    
    status: LearningStatus = Field(
        ..., description="Status of the recommendation generation"
    )
    recommendations: List[OptimizationRecommendation] = Field(
        default_factory=list, description="Generated recommendations"
    )
    context_analysis: Dict[str, Any] = Field(
        default_factory=dict, description="Analysis of the provided context"
    )
    opportunity_score: float = Field(
        default=0.0, description="Overall optimization opportunity score"
    )
    focus_areas: List[str] = Field(
        default_factory=list, description="Key areas identified for improvement"
    )
    baseline_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Current baseline performance metrics"
    )
    projected_improvements: Dict[str, float] = Field(
        default_factory=dict, description="Projected improvements if recommendations are implemented"
    )
    generation_time: float = Field(
        default=0.0, description="Time taken to generate recommendations"
    )


class HealthCheckResponse(BaseModel):
    """Health check response for the learning service."""
    
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_version: str = Field(default="1.0.0")
    
    # Database Connections
    neo4j_connected: bool = Field(default=False)
    qdrant_connected: bool = Field(default=False)
    redis_connected: bool = Field(default=False)
    
    # System Metrics
    patterns_stored: int = Field(default=0)
    knowledge_graph_nodes: int = Field(default=0)
    knowledge_graph_edges: int = Field(default=0)
    active_learning_sessions: int = Field(default=0)
    
    # Performance Metrics
    average_response_time: float = Field(default=0.0)
    pattern_recognition_accuracy: float = Field(default=0.0)
    application_success_rate: float = Field(default=0.0)
    
    uptime_seconds: float = Field(default=0.0)