"""
Pydantic schemas for interview-related API operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MissionInterviewBase(BaseModel):
    """Base schema for mission interviews."""
    interview_type: str = Field(default="mission_statement", description="Type of interview")
    llm_model: Optional[str] = Field(None, description="LLM model used for the interview")


class MissionInterviewCreate(MissionInterviewBase):
    """Schema for creating a new mission interview."""
    pass


class InterviewQuestionResponse(BaseModel):
    """Schema for a single question-response pair."""
    question: str = Field(..., description="The interview question")
    response: Optional[str] = Field(None, description="User's response")
    timestamp: Optional[datetime] = Field(None, description="When the response was given")


class InterviewSessionUpdate(BaseModel):
    """Schema for updating an interview session."""
    responses: Dict[str, Any] = Field(default_factory=dict, description="User responses to questions")
    status: Optional[str] = Field(None, description="Current status of the interview")


class InterviewAnalysisResult(BaseModel):
    """Schema for interview analysis results."""
    mission_statement: Optional[str] = Field(None, description="Generated mission statement")
    personal_goals: List[str] = Field(default_factory=list, description="Identified personal goals")
    work_style: Dict[str, Any] = Field(default_factory=dict, description="Work style analysis")
    productivity_patterns: Dict[str, Any] = Field(default_factory=dict, description="Productivity insights")
    recommendations: List[str] = Field(default_factory=list, description="AI recommendations")
    confidence_score: Optional[float] = Field(None, description="Analysis confidence (0-1)")
    ai_optimization_insights: Optional[Dict[str, Any]] = Field(None, description="Smart AI optimization insights")


class MissionInterview(MissionInterviewBase):
    """Complete mission interview schema for API responses."""
    id: UUID
    user_id: int
    status: str
    questions: Optional[Dict[str, Any]] = None
    responses: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterviewListResponse(BaseModel):
    """Schema for listing user's interviews."""
    interviews: List[MissionInterview]
    total: int


class InterviewSessionResponse(BaseModel):
    """Schema for active interview session response."""
    interview_id: UUID
    current_question: Optional[str] = None
    question_number: int = 0
    total_questions: int = 0
    progress_percentage: float = 0.0
    is_complete: bool = False
    next_action: str = Field(..., description="What the user should do next")


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile based on interview results."""
    mission_statement: Optional[str] = None
    personal_goals: Optional[Dict[str, Any]] = None
    work_style_preferences: Optional[Dict[str, Any]] = None
    productivity_patterns: Optional[Dict[str, Any]] = None
    interview_insights: Optional[Dict[str, Any]] = None
    reflective_coach_summary: Optional[str] = None


class InterviewQuestionSet(BaseModel):
    """Schema for a set of interview questions."""
    questions: List[str] = Field(..., description="List of interview questions")
    interview_type: str = Field(..., description="Type of interview")
    estimated_duration: int = Field(..., description="Estimated duration in minutes")
    description: str = Field(..., description="Description of what this interview covers")