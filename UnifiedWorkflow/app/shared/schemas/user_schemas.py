"""Pydantic models (schemas) for user-related data."""
from datetime import datetime
from typing import List, Optional
import uuid


from pydantic import BaseModel, ConfigDict, EmailStr
# Removed FastAPI-Users schemas - using custom Pydantic schemas

from shared.database.models import UserRole, UserStatus  # Import enums

class UserSettings(BaseModel):
    """Schema for user-specific settings."""

    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    selected_model: Optional[str] = None  # Selected Ollama model for chat
    timezone: Optional[str] = None  # User's timezone setting
    
    # LLM Categories for different use cases (legacy)
    chat_model: Optional[str] = None  # Model for general chat conversations
    initial_assessment_model: Optional[str] = None  # Model for initial request assessment
    tool_selection_model: Optional[str] = None  # Model for tool routing decisions
    embeddings_model: Optional[str] = None  # Model for document embeddings
    coding_model: Optional[str] = None  # Model for code generation and analysis
    fast_model: Optional[str] = None
    smart_model: Optional[str] = None
    planning_model: Optional[str] = None
    
    # Granular Node-Specific Models
    executive_assessment_model: Optional[str] = None  # Model for executive decision making
    confidence_assessment_model: Optional[str] = None  # Model for confidence scoring
    tool_routing_model: Optional[str] = None  # Model for tool selection
    simple_planning_model: Optional[str] = None  # Model for simple direct planning
    wave_function_specialist_model: Optional[str] = None  # Model for specialist planning
    wave_function_refinement_model: Optional[str] = None  # Model for plan refinement
    plan_validation_model: Optional[str] = None  # Model for plan validation
    plan_comparison_model: Optional[str] = None  # Model for comparing simple vs complex plans
    reflection_model: Optional[str] = None  # Model for self-reflection and critique
    final_response_model: Optional[str] = None  # Model for final response generation
    
    # Fast Conversational Model (dedicated for immediate responses)
    fast_conversational_model: Optional[str] = None  # Lightweight model for fast conversational responses
    
    # Expert Group Model Configuration (per-expert model assignments)
    project_manager_model: Optional[str] = None  # Model for Project Manager expert
    technical_expert_model: Optional[str] = None  # Model for Technical Expert
    business_analyst_model: Optional[str] = None  # Model for Business Analyst
    creative_director_model: Optional[str] = None  # Model for Creative Director
    research_specialist_model: Optional[str] = None  # Model for Research Specialist
    planning_expert_model: Optional[str] = None  # Model for Planning Expert
    socratic_expert_model: Optional[str] = None  # Model for Socratic Expert
    wellbeing_coach_model: Optional[str] = None  # Model for Wellbeing Coach
    personal_assistant_model: Optional[str] = None  # Model for Personal Assistant
    data_analyst_model: Optional[str] = None  # Model for Data Analyst
    output_formatter_model: Optional[str] = None  # Model for Output Formatter
    quality_assurance_model: Optional[str] = None  # Model for Quality Assurance
    
    # Calendar event type weights for prioritization
    calendar_event_weights: Optional[dict] = None  # Event type priorities

    # Agent settings for expert group chat
    agent_settings: Optional[dict] = None  # e.g., {"data_analyst_enabled": True}
    
    # Add any other settings fields you need here

# --- User Schemas ---
class UserRead(BaseModel):
    """Schema for reading user data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # User settings
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    selected_model: Optional[str] = None
    timezone: Optional[str] = None

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING

class UserUpdate(BaseModel):
    """Schema for updating user data."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    
    # User settings
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    selected_model: Optional[str] = None
    timezone: Optional[str] = None

class PaginatedUsers(BaseModel):
    """Schema for paginated user list response."""

    items: List[UserRead]
    total: int

class UserProfile(BaseModel):
    """Schema for a user's profile data."""

    user_id: int
    mission_statement: Optional[str] = None
    work_style_preferences: Optional[dict] = None
    productivity_patterns: Optional[dict] = None
    personal_goals: Optional[dict] = None
    reflective_coach_summary: Optional[str] = None
    constellation_relationships: Optional[List[dict]] = None
    
    # Add other profile fields as needed

    class Config:
        from_attributes = True
        
class UserProfileUpdate(BaseModel):
    """Schema for updating a user's profile."""

    mission_statement: Optional[str] = None
    work_style_preferences: Optional[dict] = None
    productivity_patterns: Optional[dict] = None
    personal_goals: Optional[dict] = None
    reflective_coach_summary: Optional[str] = None
    constellation_relationships: Optional[List[dict]] = None
    
    # Add other profile fields as needed
