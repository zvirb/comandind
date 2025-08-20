"""
Base schemas for the application.
"""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')

class GenericResponse(BaseModel, Generic[T]):
    """
    A generic response model for API endpoints.
    """
    success: bool = Field(..., description="Indicates if the request was successful.")
    message: str = Field(..., description="A message providing details about the response.")
    data: Optional[T] = Field(None, description="The data payload of the response.")
