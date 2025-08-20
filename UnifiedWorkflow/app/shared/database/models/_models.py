"""Defines the SQLAlchemy ORM models for the application.""" # pylint: disable=unsubscriptable-object
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import func
from shared.utils.database_setup import Base
# Removed FastAPI-Users dependency

# Import auth models for relationships
from .auth_models import RegisteredDevice, UserTwoFactorAuth, PasskeyCredential
from .secure_token_models import SecureTokenStorage, AuthenticationSession

# Note: Helios Multi-Agent framework models are imported via __init__.py to avoid circular imports

class UserRole(str, enum.Enum):
    """Enumeration for user roles."""
    ADMIN = "admin"
    USER = "user"

class UserStatus(str, enum.Enum):
    """Enumeration for user account statuses."""
    PENDING = "pending_approval"
    ACTIVE = "active"
    DISABLED = "disabled"

class DocumentStatus(str, enum.Enum):
    """Enumeration for document processing statuses."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class EventCategory(str, enum.Enum):
    """Enumeration for event categories."""
    WORK = "Work"
    HEALTH = "Health"
    LEISURE = "Leisure"
    FAMILY = "Family"
    FITNESS = "Fitness"
    DEFAULT = "Default"

class TaskStatus(str, enum.Enum):
    """Enumeration for task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"

class TaskPriority(str, enum.Enum):
    """Enumeration for task priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskType(str, enum.Enum):
    """Enumeration for task types."""
    GENERAL = "general"
    CODING = "coding"
    REVIEW = "review"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MEETING = "meeting"
    RESEARCH = "research"
    OPPORTUNITY = "opportunity"


class SystemSetting(Base):
    """Represents a system-wide setting."""
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

# User model based on the security audit's recommendations
class User(Base):
    """Represents a user in the system."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Core authentication fields (previously inherited from SQLAlchemyBaseUserTable)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Additional fields for role and status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.USER
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserStatus.PENDING
    )

    tfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tfa_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # User settings columns
    theme: Mapped[Optional[str]] = mapped_column(String, default="dark", nullable=True)
    notifications_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    selected_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String, default="UTC", nullable=True)
    chat_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    initial_assessment_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    tool_selection_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    embeddings_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    coding_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    
    # Granular Node-Specific Models
    executive_assessment_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    confidence_assessment_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    tool_routing_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    simple_planning_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    wave_function_specialist_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:1b", nullable=True)
    wave_function_refinement_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.1:8b", nullable=True)
    plan_validation_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    plan_comparison_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    reflection_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    final_response_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    
    # Fast Conversational Model (dedicated for immediate responses)
    fast_conversational_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:1b", nullable=True)
    calendar_event_weights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    agent_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Enhanced user profile columns
    mission_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personal_goals: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    work_style_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    productivity_patterns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    interview_insights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    last_interview_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    project_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    default_code_style: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    git_integrations: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Web Search API Configuration (user-level settings)
    web_search_provider: Mapped[Optional[str]] = mapped_column(String, default="disabled", nullable=True)  # "tavily", "serpapi", "disabled"
    web_search_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Encrypted API key
    
    # Expert Group Model Configuration (per-expert model assignments)
    project_manager_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    technical_expert_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.1:8b", nullable=True)
    business_analyst_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    creative_director_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    research_specialist_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.1:8b", nullable=True)
    planning_expert_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    socratic_expert_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    wellbeing_coach_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    personal_assistant_model: Mapped[Optional[str]] = mapped_column(String, default="mistral:7b", nullable=True)
    data_analyst_model: Mapped[Optional[str]] = mapped_column(String, default="qwen2.5:7b", nullable=True)
    output_formatter_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)
    quality_assurance_model: Mapped[Optional[str]] = mapped_column(String, default="llama3.2:3b", nullable=True)

    # Bidirectional relationships
    documents: Mapped[List["Document"]] = relationship(back_populates="user")
    calendars: Mapped[List["Calendar"]] = relationship(back_populates="user")
    oauth_tokens: Mapped[List["UserOAuthToken"]] = relationship(back_populates="user")
    profile: Mapped[Optional["UserProfile"]] = relationship("UserProfile", back_populates="user", uselist=False)
    
    # 2FA and device management relationships
    registered_devices: Mapped[List["RegisteredDevice"]] = relationship("RegisteredDevice", back_populates="user")
    two_factor_auth: Mapped[Optional["UserTwoFactorAuth"]] = relationship("UserTwoFactorAuth", back_populates="user", uselist=False)
    passkey_credentials: Mapped[List["PasskeyCredential"]] = relationship("PasskeyCredential", back_populates="user")
    
    # Agent configuration relationships (using Helios Multi-Agent framework model)
    # TEMPORARILY DISABLED: AgentConfiguration model is not yet active due to incomplete migration
    # agent_configurations: Mapped[List["AgentConfiguration"]] = relationship("AgentConfiguration", back_populates="user")
    
    # Legacy agent configuration relationships (being phased out)
    legacy_agent_configurations: Mapped[List["LegacyAgentConfiguration"]] = relationship("LegacyAgentConfiguration", back_populates="created_by_user")
    
    # Security tier relationship
    security_tier: Mapped[Optional["UserSecurityTier"]] = relationship("UserSecurityTier", back_populates="user", uselist=False)
    
    # Secure token and session management relationships
    secure_tokens: Mapped[List["SecureTokenStorage"]] = relationship("SecureTokenStorage", back_populates="user", cascade="all, delete-orphan")
    auth_sessions: Mapped[List["AuthenticationSession"]] = relationship("AuthenticationSession", back_populates="user", cascade="all, delete-orphan")
    
    # Unified memory store relationships
    chat_sessions: Mapped[List["ChatModeSession"]] = relationship("ChatModeSession", back_populates="user")


class GoogleService(str, enum.Enum):
    """Enumeration for Google services that can be connected via OAuth."""
    CALENDAR = "calendar"
    DRIVE = "drive"
    GMAIL = "gmail"


class UserOAuthToken(Base):
    """Stores OAuth tokens for users to connect to external services like Google."""
    __tablename__ = "user_oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    service: Mapped[GoogleService] = mapped_column(
        SQLAlchemyEnum(GoogleService, native_enum=True, name="googleservice"), 
        nullable=False
    )
    
    # OAuth token data
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Comma-separated scopes
    
    # Service-specific data
    service_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Google user ID
    service_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Connected Google email
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    
    # Validation constraints and unique constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'service', name='_user_service_token'),
        CheckConstraint(
            "token_expiry IS NULL OR token_expiry > created_at",
            name="check_token_expiry"
        ),
        CheckConstraint(
            "service_email IS NULL OR service_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name="check_service_email_format"
        ),
    )

    # Bidirectional relationships
    user: Mapped["User"] = relationship(back_populates="oauth_tokens")

class Document(Base):
    """Represents an uploaded document."""
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()  # pylint: disable=not-callable
    )
    status: Mapped[DocumentStatus] = mapped_column(
        SQLAlchemyEnum(DocumentStatus, native_enum=True, name="documentstatus"), default=DocumentStatus.PROCESSING, nullable=False
    )

    # Bidirectional relationships
    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

class DocumentChunk(Base):
    """Represents a chunk of a document, for processing and vectorization."""
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Enhanced semantic fields
    semantic_keywords: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    semantic_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    semantic_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint('document_id', 'chunk_index', name='_document_chunk_index_uc'),
    )


class ChatHistory(Base):
    """Stores the history of chat messages for a session."""
    __tablename__ = "chat_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    message: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()  # pylint: disable=not-callable
    )

class SessionState(Base):
    """Stores the state of a user session."""
    __tablename__ = "session_state"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()  # pylint: disable=not-callable
    )

class Calendar(Base):
    """Represents a user's calendar with validation constraints."""
    __tablename__ = "calendars"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, default="Default Calendar")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validation constraints
    __table_args__ = (
        CheckConstraint(
            "name IS NOT NULL AND LENGTH(TRIM(name)) > 0",
            name="check_calendar_name_not_empty"
        ),
    )

    # Bidirectional relationships
    user: Mapped["User"] = relationship(back_populates="calendars")
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="calendar", cascade="all, delete-orphan"
    )

class Event(Base):
    """Represents an event in a calendar with validation constraints."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_event_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    calendar_id: Mapped[int] = mapped_column(ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    category: Mapped[EventCategory] = mapped_column(
        SQLAlchemyEnum(EventCategory, native_enum=True, name="eventcategory"), default=EventCategory.DEFAULT, nullable=False
    )
    movability_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_movable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()  # pylint: disable=not-callable
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()  # pylint: disable=not-callable
    )
    
    # Enhanced event fields
    semantic_keywords: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    semantic_embedding_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    semantic_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    semantic_tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String, default="meeting", nullable=True)
    attendees: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reminder_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=15, nullable=True)
    importance_weight: Mapped[Optional[float]] = mapped_column(Float, default=1.0, nullable=True)

    # Validation constraints for event integrity
    __table_args__ = (
        CheckConstraint(
            "summary IS NOT NULL AND LENGTH(TRIM(summary)) > 0",
            name="check_event_summary_not_empty"
        ),
        CheckConstraint(
            "end_time > start_time",
            name="check_event_time_valid"
        ),
    )

    calendar: Mapped["Calendar"] = relationship(back_populates="events")

class CategoryWeight(Base):
    """Represents the weight or importance of a task category."""
    __tablename__ = "category_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

class TimeBudget(Base):
    """Represents a user's time budget for a specific category and period."""
    __tablename__ = "time_budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    period: Mapped[str] = mapped_column(String, default="weekly", nullable=False)
    budgeted_hours: Mapped[float] = mapped_column(Float, nullable=False)


class Project(Base):
    """Represents a programming project."""
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    programming_language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    framework: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    project_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project")


class Task(Base):
    """Represents a task with enhanced features for semantic analysis and programming support."""
    __tablename__ = "tasks"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SQLAlchemyEnum(TaskStatus, native_enum=True, name="task_status"), default=TaskStatus.PENDING, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLAlchemyEnum(TaskPriority, native_enum=True, name="task_priority"), default=TaskPriority.MEDIUM, nullable=False
    )
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    
    # Semantic identification fields
    semantic_keywords: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    semantic_embedding_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    semantic_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    semantic_tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    semantic_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Weighted scoring system
    importance_weight: Mapped[float] = mapped_column(Float, default=1.0)
    urgency_weight: Mapped[float] = mapped_column(Float, default=1.0)
    complexity_weight: Mapped[float] = mapped_column(Float, default=1.0)
    user_priority_weight: Mapped[float] = mapped_column(Float, default=1.0)
    calculated_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Programming-specific fields
    task_type: Mapped[TaskType] = mapped_column(
        SQLAlchemyEnum(TaskType, native_enum=True, name="task_type"), default=TaskType.GENERAL, nullable=False
    )
    programming_language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    code_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    repository_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")


class UserProfile(Base):
    """Represents user profile information with comprehensive validation constraints."""
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, unique=True)
    
    # Basic information
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Address information (stored as JSON)
    personal_address: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Work information
    job_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_address: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Contact preferences
    preferred_contact_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emergency_contact: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Social and personal
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    twitter: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    github: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Preferences
    timezone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Validation constraints for data integrity
    __table_args__ = (
        CheckConstraint(
            "work_email IS NULL OR work_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}$'",
            name="check_email_format"
        ),
        CheckConstraint(
            "phone_number IS NULL OR phone_number ~ '^\\+?[1-9]\\d{1,14}$'",
            name="check_phone_format"
        ),
        CheckConstraint(
            "alternate_phone IS NULL OR alternate_phone ~ '^\\+?[1-9]\\d{1,14}$'",
            name="check_alternate_phone_format"
        ),
        CheckConstraint(
            "work_phone IS NULL OR work_phone ~ '^\\+?[1-9]\\d{1,14}$'",
            name="check_work_phone_format"
        ),
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")


class UserCategory(Base):
    """Represents user-defined categories with weights."""
    __tablename__ = "user_categories"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    category_type: Mapped[str] = mapped_column(String, default="custom", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emoji: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="📋")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class MissionInterview(Base):
    """Represents an AI-conducted interview session for mission statement analysis."""
    __tablename__ = "mission_interviews"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    interview_type: Mapped[str] = mapped_column(String, default="mission_statement")
    llm_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="in_progress")
    questions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    responses: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    analysis_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class SemanticInsight(Base):
    """Represents AI-generated insights about content."""
    __tablename__ = "semantic_insights"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    content_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    insight_type: Mapped[str] = mapped_column(String, nullable=False)
    insight_value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class CodeTemplate(Base):
    """Represents reusable code templates."""
    __tablename__ = "code_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    programming_language: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    template_content: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class AIAnalysisHistory(Base):
    """Represents the history of AI analysis operations."""
    __tablename__ = "ai_analysis_history"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String, nullable=False)
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class TaskFeedback(Base):
    __tablename__ = 'task_feedback'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to the user who completed the task
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    
    # Foreign key to the opportunity/task that was completed.
    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tasks.id'), nullable=False)
    
    # The data from your modal
    feeling: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'positive', 'negative'
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False) # 1-10
    energy: Mapped[int] = mapped_column(Integer, nullable=False) # 1-10
    
    # The category of the task at the time of completion
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Automatically captures the completion time
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # --- Suggested Additional Fields ---
    
    # Allows users to add qualitative notes about the task
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 
    
    # A simple way to track if the task was harder than expected
    blockers_encountered: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User")
    opportunity: Mapped["Task"] = relationship("Task")


class ChatSessionSummary(Base):
    """Comprehensive summaries of completed chat sessions for quick reference and context."""
    __tablename__ = "chat_session_summaries"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Session metadata
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Content summaries
    conversation_domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g., "software_development", "cooking"
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # Comprehensive summary
    key_topics: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)  # ["API design", "React components"]
    decisions_made: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)  # User decisions/choices
    user_preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # Extracted preferences
    
    # Technical details
    tools_used: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)  # ["CalendarTool", "EmailTool"]
    plans_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expert_questions_asked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Quality metrics
    session_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # User satisfaction if provided
    complexity_level: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # "low", "medium", "high"
    resolution_status: Mapped[str] = mapped_column(String, nullable=False, default="completed")  # "completed", "partial", "interrupted"
    
    # Searchable content for quick reference
    search_keywords: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)  # For quick searching
    follow_up_suggested: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_tasks: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class ChatMessage(Base):
    """Individual chat messages for semantic search and detailed analysis."""
    __tablename__ = "chat_messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    message_type: Mapped[str] = mapped_column(String, nullable=False)  # "human", "ai", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_order: Mapped[int] = mapped_column(Integer, nullable=False)  # Order within session
    
    # Context and metadata
    conversation_domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tool_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    plan_step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Vector database reference
    qdrant_point_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    embedding_model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")

class MessageFeedback(Base):
    """Stores user feedback on individual messages."""
    __tablename__ = "message_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    feedback: Mapped[str] = mapped_column(String, nullable=False)  # "up" or "down"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserHistorySummary(Base):
    """Stores comprehensive summaries of user's chat history over time."""
    __tablename__ = "user_history_summaries"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Summary metadata
    summary_period: Mapped[str] = mapped_column(String, nullable=False)  # "weekly", "monthly", "all_time"
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Aggregated statistics
    total_sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Content analysis
    primary_domains: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    frequent_topics: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    key_preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    skill_areas: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    
    # Behavioral patterns
    preferred_tools: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    interaction_patterns: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    complexity_preference: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    
    # Summary content
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    important_context: Mapped[str] = mapped_column(Text, nullable=True)
    recurring_themes: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    
    # Quality metrics
    engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    satisfaction_indicators: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User")


class SystemPrompt(Base):
    """Stores system prompts with user-specific overrides and factory defaults."""
    __tablename__ = "system_prompts"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)  # NULL for factory defaults
    
    # Prompt identification
    prompt_key: Mapped[str] = mapped_column(String, nullable=False, index=True)  # e.g., "socratic_guidance", "chat_response"
    prompt_category: Mapped[str] = mapped_column(String, nullable=False, index=True)  # e.g., "chat", "interview", "analysis"
    prompt_name: Mapped[str] = mapped_column(String, nullable=False)  # Human-readable name
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Prompt content
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Variables that can be replaced in prompt
    
    # Metadata
    is_factory_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Performance metrics
    average_satisfaction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Ensure unique prompts per user per key
    __table_args__ = (UniqueConstraint('user_id', 'prompt_key', name='_user_prompt_key_uc'),)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")

