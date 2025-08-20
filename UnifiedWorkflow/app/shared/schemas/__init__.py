"""Initializes the schemas package and makes the schemas available for import."""
from .calendar_schemas import (
    DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY,
    Event,
    Movability,
    TimePreferences,
)
from .document_schemas import (
    Document,
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentUploadResponse,
)
from .token_schemas import Token, TokenData
from .user_schemas import (
    PaginatedUsers,
    UserRead,
    UserRead as User,
    UserCreate,
    UserUpdate,
)
from .project_schemas import (
    ProjectBase,
    ProjectCreate,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectUpdateResponse,
)

__all__ = [
    "DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY",
    "Event",
    "Movability",
    "TimePreferences",
    "Document",
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUploadResponse",
    "Token",
    "TokenData",
    "PaginatedUsers",
    "User",
    "UserRead",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "ProjectBase",
    "ProjectCreate",
    "ProjectCreateResponse",
    "ProjectDeleteResponse",
    "ProjectListResponse",
    "ProjectResponse",
    "ProjectUpdate",
    "ProjectUpdateResponse",
]