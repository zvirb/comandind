"""
Pydantic models (schemas) for data validation and serialization.

This module acts as a central hub, re-exporting schemas from more specific
modules to maintain a consistent public API for the rest of the application.
"""

# Use absolute imports. Pylint is configured via .pylintrc to find the 'backend' package.
from .calendar_schemas import (
    DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY,
    Event,
    Movability,
    TimePreferences,
)
# Import enums from their new central location in the shared module.
from ..database.models import DocumentStatus, EventCategory, UserRole, UserStatus
from .document_schemas import (
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
)
from .task_schemas import (
    Task, TaskCreate, TaskUpdate,
    SubtaskGenerationContext, SubtaskGenerationRequest, SubtaskGenerationResponse,
    GeneratedSubtask
)
from .task_feedback_schemas import TaskFeedback, TaskFeedbackCreate
from .token_schemas import Token, TokenData
from .user_schemas import (
    PaginatedUsers,
    UserRead as User,
    UserCreate,    
    UserUpdate,
)

# To make Pylint happy about unused imports when this file is just a re-exporter,
# we can use __all__ to explicitly declare what we're exporting. This also
# controls what 'from schemas import *' would import in other modules.
__all__ = [
    # calendar_schemas
    "DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY",
    "Event",
    "Movability",
    "TimePreferences",
    # database_models (enums)
    "DocumentStatus",
    "EventCategory",
    "UserRole",
    "UserStatus",
    # document_schemas
    "Document",
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUploadResponse",
    # task_schemas
    "Task",
    "TaskCreate", 
    "TaskUpdate",
    "SubtaskGenerationContext",
    "SubtaskGenerationRequest",
    "SubtaskGenerationResponse",
    "GeneratedSubtask",
    # task_feedback_schemas
    "TaskFeedback",
    "TaskFeedbackCreate",
    # token_schemas
    "Token",
    "TokenData",
    # user_schemas
    "PaginatedUsers",
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
]
