"""Pydantic models (schemas) for document-related data."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Document Schemas ---
class DocumentBase(BaseModel):
    """Base schema for document properties."""
    content: str
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    pass


class Document(DocumentBase):
    """Schema for a document record, including database-generated fields."""
    id: uuid.UUID
    user_id: int
    created_at: datetime
    embedding: Optional[List[float]] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    """Schema for the response when a document is created or retrieved."""
    id: uuid.UUID
    filename: Optional[str] = None
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    """Schema for the response when a document upload is accepted."""
    message: str
    document_id: uuid.UUID