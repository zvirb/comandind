"""
Pattern Recognition Models
=========================

Models for learning patterns, pattern matching, and pattern applications
within the adaptive intelligence system.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class PatternType(str, Enum):
    """Types of learning patterns."""
    SEQUENTIAL = "sequential"          # Time-based sequences
    CONTEXTUAL = "contextual"          # Context-based patterns
    BEHAVIORAL = "behavioral"          # Agent behavior patterns
    PERFORMANCE = "performance"        # Performance patterns
    ERROR = "error"                   # Error and failure patterns
    SUCCESS = "success"               # Success patterns
    ADAPTIVE = "adaptive"             # Adaptive learning patterns
    META = "meta"                     # Meta-learning patterns


class PatternScope(str, Enum):
    """Scope of pattern applicability."""
    AGENT = "agent"                   # Single agent patterns
    WORKFLOW = "workflow"             # Workflow-level patterns
    SERVICE = "service"               # Service-level patterns
    SYSTEM = "system"                 # System-wide patterns
    CROSS_DOMAIN = "cross_domain"     # Cross-domain patterns


class PatternStatus(str, Enum):
    """Status of pattern lifecycle."""
    LEARNING = "learning"             # Pattern being learned
    ACTIVE = "active"                 # Active pattern ready for use
    VALIDATED = "validated"           # Pattern has been validated
    DEPRECATED = "deprecated"         # Pattern is outdated
    FAILED = "failed"                # Pattern consistently fails


class PatternMetrics(BaseModel):
    """Metrics for pattern performance and reliability."""
    
    applications: int = Field(default=0, description="Number of times applied")
    successes: int = Field(default=0, description="Number of successful applications")
    failures: int = Field(default=0, description="Number of failed applications")
    
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    average_execution_time: float = Field(default=0.0, description="Average execution time")
    
    last_success: Optional[datetime] = Field(None, description="Last successful application")
    last_failure: Optional[datetime] = Field(None, description="Last failed application")
    
    success_contexts: List[str] = Field(default_factory=list, description="Contexts where pattern succeeded")
    failure_contexts: List[str] = Field(default_factory=list, description="Contexts where pattern failed")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.applications == 0:
            return 0.0
        return (self.successes / self.applications) * 100.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.applications == 0:
            return 0.0
        return (self.failures / self.applications) * 100.0


class LearningPattern(BaseModel):
    """Core learning pattern model."""
    
    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique pattern identifier")
    pattern_type: PatternType = Field(..., description="Type of pattern")
    pattern_scope: PatternScope = Field(..., description="Scope of pattern applicability")
    
    # Pattern Definition
    name: str = Field(..., description="Human-readable pattern name")
    description: str = Field(..., description="Detailed pattern description")
    
    # Pattern Structure
    trigger_conditions: Dict[str, Any] = Field(..., description="Conditions that trigger this pattern")
    context_requirements: Dict[str, Any] = Field(..., description="Required context for pattern application")
    action_sequence: List[Dict[str, Any]] = Field(..., description="Sequence of actions in the pattern")
    expected_outcomes: Dict[str, Any] = Field(..., description="Expected outcomes from pattern application")
    
    # Pattern Metadata
    source_service: str = Field(..., description="Service that generated this pattern")
    learning_session_id: Optional[str] = Field(None, description="Learning session that created this pattern")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Pattern creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    # Pattern State
    status: PatternStatus = Field(default=PatternStatus.LEARNING, description="Current pattern status")
    confidence_score: float = Field(default=0.0, description="Confidence in pattern effectiveness")
    complexity_score: float = Field(default=0.0, description="Pattern complexity score")
    
    # Pattern Performance
    metrics: PatternMetrics = Field(default_factory=PatternMetrics, description="Pattern performance metrics")
    
    # Pattern Relationships
    parent_patterns: List[str] = Field(default_factory=list, description="Parent pattern IDs")
    child_patterns: List[str] = Field(default_factory=list, description="Child pattern IDs")
    related_patterns: List[str] = Field(default_factory=list, description="Related pattern IDs")
    
    # Pattern Adaptation
    adaptable: bool = Field(default=True, description="Whether pattern can be adapted to context")
    adaptation_rules: Dict[str, Any] = Field(default_factory=dict, description="Rules for pattern adaptation")
    
    # Pattern Validation
    validation_criteria: Dict[str, Any] = Field(default_factory=dict, description="Criteria for validating pattern success")
    validation_history: List[Dict[str, Any]] = Field(default_factory=list, description="History of pattern validations")
    
    @validator('confidence_score', 'complexity_score')
    def validate_scores(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Scores must be between 0 and 1")
        return v


class PatternRelationship(BaseModel):
    """Relationship between patterns."""
    
    relationship_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique relationship identifier")
    from_pattern_id: str = Field(..., description="Source pattern ID")
    to_pattern_id: str = Field(..., description="Target pattern ID")
    
    relationship_type: str = Field(..., description="Type of relationship (derives_from, precedes, enables, conflicts)")
    strength: float = Field(..., description="Strength of the relationship (0-1)")
    confidence: float = Field(..., description="Confidence in the relationship")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Relationship creation timestamp")
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting the relationship")
    
    @validator('strength', 'confidence')
    def validate_relationship_metrics(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Relationship metrics must be between 0 and 1")
        return v


class PatternMatch(BaseModel):
    """Result of pattern matching against context."""
    
    pattern: LearningPattern = Field(..., description="Matched pattern")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    confidence_score: float = Field(..., description="Confidence in the match")
    
    context_alignment: Dict[str, float] = Field(default_factory=dict, description="How well context aligns with pattern requirements")
    missing_requirements: List[str] = Field(default_factory=list, description="Requirements not met by current context")
    
    recommended_adaptations: List[Dict[str, Any]] = Field(default_factory=list, description="Recommended pattern adaptations")
    application_probability: float = Field(default=0.0, description="Probability of successful application")
    
    match_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional matching metadata")
    
    @validator('similarity_score', 'confidence_score', 'application_probability')
    def validate_match_scores(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Match scores must be between 0 and 1")
        return v


class PatternApplication(BaseModel):
    """Result of applying a pattern to a context."""
    
    application_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique application identifier")
    pattern_id: str = Field(..., description="ID of applied pattern")
    
    context: Dict[str, Any] = Field(..., description="Context the pattern was applied to")
    adaptations_made: List[Dict[str, Any]] = Field(default_factory=list, description="Adaptations made to the pattern")
    
    execution_start: datetime = Field(default_factory=datetime.utcnow, description="Application start time")
    execution_end: Optional[datetime] = Field(None, description="Application end time")
    
    status: str = Field(..., description="Application status (pending, running, success, failed)")
    success: Optional[bool] = Field(None, description="Whether application was successful")
    
    outcomes: Dict[str, Any] = Field(default_factory=dict, description="Actual outcomes from application")
    expected_outcomes: Dict[str, Any] = Field(default_factory=dict, description="Expected outcomes")
    
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    error_information: Optional[Dict[str, Any]] = Field(None, description="Error information if application failed")
    
    feedback: Optional[Dict[str, Any]] = Field(None, description="Feedback from the application")
    learning_insights: List[str] = Field(default_factory=list, description="Insights learned from this application")
    
    @property
    def execution_time(self) -> Optional[float]:
        """Calculate execution time in seconds."""
        if self.execution_end and self.execution_start:
            return (self.execution_end - self.execution_start).total_seconds()
        return None
    
    @property
    def outcome_alignment_score(self) -> float:
        """Calculate how well outcomes aligned with expectations."""
        if not self.outcomes or not self.expected_outcomes:
            return 0.0
        
        # Simplified alignment calculation
        total_keys = len(set(self.outcomes.keys()) | set(self.expected_outcomes.keys()))
        matching_keys = len(set(self.outcomes.keys()) & set(self.expected_outcomes.keys()))
        
        if total_keys == 0:
            return 1.0
            
        return matching_keys / total_keys


class PatternEvolutionEvent(BaseModel):
    """Event representing pattern evolution or change."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event identifier")
    pattern_id: str = Field(..., description="Pattern that evolved")
    
    event_type: str = Field(..., description="Type of evolution (created, updated, validated, deprecated)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the evolution occurred")
    
    before_state: Optional[Dict[str, Any]] = Field(None, description="Pattern state before evolution")
    after_state: Dict[str, Any] = Field(..., description="Pattern state after evolution")
    
    trigger_event: Dict[str, Any] = Field(..., description="Event that triggered the evolution")
    confidence_delta: float = Field(default=0.0, description="Change in confidence score")
    
    evidence: List[str] = Field(default_factory=list, description="Evidence supporting the evolution")
    impact_assessment: Dict[str, Any] = Field(default_factory=dict, description="Assessment of evolution impact")