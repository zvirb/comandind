"""
Project-related Pydantic schemas for API serialization and validation.

This module provides a set of schemas for project-related operations,
ensuring consistent data validation and serialization across the API.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    """Base schema for project data."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    project_type: Optional[str] = Field(None, max_length=100, description="Type of project (web, mobile, etc.)")
    programming_language: Optional[str] = Field(None, max_length=50, description="Primary programming language")
    framework: Optional[str] = Field(None, max_length=100, description="Framework or technology stack")
    repository_url: Optional[str] = Field(None, max_length=500, description="Git repository URL")
    local_path: Optional[str] = Field(None, max_length=500, description="Local development path")
    status: str = Field(default="active", description="Project status")
    project_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional project metadata")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    project_type: Optional[str] = Field(None, max_length=100, description="Type of project")
    programming_language: Optional[str] = Field(None, max_length=50, description="Primary programming language")
    framework: Optional[str] = Field(None, max_length=100, description="Framework or technology stack")
    repository_url: Optional[str] = Field(None, max_length=500, description="Git repository URL")
    local_path: Optional[str] = Field(None, max_length=500, description="Local development path")
    status: Optional[str] = Field(None, description="Project status")
    project_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional project metadata")


class ProjectResponse(ProjectBase):
    """Schema for project responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Project unique identifier")
    user_id: int = Field(..., description="User ID who owns the project")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Project last update timestamp")


class ProjectListResponse(BaseModel):
    """Schema for project list responses."""
    projects: list[ProjectResponse] = Field(..., description="List of projects")
    total: int = Field(..., description="Total number of projects")


class ProjectCreateResponse(BaseModel):
    """Schema for project creation response."""
    message: str = Field(..., description="Success message")
    project: ProjectResponse = Field(..., description="Created project data")


class ProjectUpdateResponse(BaseModel):
    """Schema for project update response."""
    message: str = Field(..., description="Success message")
    project: ProjectResponse = Field(..., description="Updated project data")


class ProjectDeleteResponse(BaseModel):
    """Schema for project deletion response."""
    message: str = Field(..., description="Success message")
    project_id: uuid.UUID = Field(..., description="Deleted project ID")