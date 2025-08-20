from pydantic import BaseModel, computed_field, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from shared.database.models import TaskStatus, TaskPriority, TaskType

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None

class TaskCreate(TaskBase):
    type: str  # This will be mapped to task_type in CRUD
    status: Optional[TaskStatus] = TaskStatus.PENDING
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM

class Task(TaskBase):
    id: UUID
    status: TaskStatus
    priority: TaskPriority
    task_type: TaskType
    created_at: datetime
    updated_at: Optional[datetime] = None
    semantic_tags: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        return str(value)

    @computed_field
    @property
    def completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED
    
    @computed_field
    @property
    def type(self) -> str:
        return self.task_type.value if self.task_type else "general"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    completed: Optional[bool] = None


# Subtask generation schemas
class SubtaskGenerationContext(BaseModel):
    """Context information for subtask generation"""
    user_context: Optional[str] = Field(
        default="",
        description="Additional context about the user's situation, preferences, or constraints"
    )
    supplementary_context: Optional[str] = Field(
        default="",
        description="Additional contextual information like deadlines, resources, or specific requirements"
    )
    preferred_categories: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred subtask categories (e.g., 'research', 'planning', 'execution')"
    )
    time_constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Time-related constraints like available hours per day, deadline, etc."
    )
    skill_level: Optional[str] = Field(
        default="intermediate",
        description="User's skill level for this type of task (beginner, intermediate, advanced)"
    )
    preferred_approach: Optional[str] = Field(
        default="balanced",
        description="Preferred approach style (methodical, agile, creative, etc.)"
    )


class GeneratedSubtask(BaseModel):
    """A single generated subtask"""
    id: str
    title: str
    description: str
    estimated_hours: float = Field(ge=0.1, le=20.0)
    priority: Optional[str] = "medium"
    category: Optional[str] = "execution"
    completed: bool = False
    prerequisites: Optional[List[str]] = Field(default_factory=list)
    deliverables: Optional[List[str]] = Field(default_factory=list)


class SubtaskGenerationRequest(BaseModel):
    """Request schema for subtask generation"""
    context: SubtaskGenerationContext = Field(default_factory=SubtaskGenerationContext)
    force_regenerate: bool = Field(
        default=False,
        description="Force regeneration even if subtasks already exist"
    )
    max_subtasks: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of subtasks to generate"
    )
    include_analysis: bool = Field(
        default=True,
        description="Include analysis information about the opportunity"
    )


class SubtaskGenerationResponse(BaseModel):
    """Response schema for subtask generation"""
    subtasks: List[GeneratedSubtask]
    analysis: Optional[Dict[str, Any]] = None
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[float] = None
