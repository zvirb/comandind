"""
Project management API router.

This module provides RESTful endpoints for project CRUD operations,
including creating, reading, updating, and deleting projects for authenticated users.
"""
import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from api.dependencies import get_current_user
from shared.database.models import User
from shared.schemas.project_schemas import (
    ProjectCreate,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectUpdateResponse,
)
from shared.services.project_service import (
    create_project,
    delete_project,
    get_all_projects,
    get_project_by_id_and_user,
    get_projects_by_language,
    get_projects_by_status,
    update_project,
    get_projects_count,
    get_projects_statistics,
    bulk_update_project_status,
)
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/projects",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project for the authenticated user."
)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((OperationalError, SQLAlchemyError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Project creation retry {retry_state.attempt_number}/3 for user {current_user.id}"
    )
)
async def create_user_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project for the current user with enhanced error handling and retry logic."""
    try:
        # Validate project data before creation
        if not project_data.name or len(project_data.name.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name is required and cannot be empty"
            )
        
        if len(project_data.name) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name cannot exceed 255 characters"
            )
        
        project = create_project(db, project_data, current_user.id)
        logger.info(f"Successfully created project '{project.name}' for user {current_user.id}")
        
        return ProjectCreateResponse(
            message=f"Project '{project.name}' created successfully",
            project=ProjectResponse.model_validate(project)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except IntegrityError as e:
        logger.error("Database integrity error creating project for user %s: %s", current_user.id, e, exc_info=True)
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with this name already exists. Please choose a different name."
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project data provided. Please check your input and try again."
            ) from e
    except OperationalError as e:
        logger.error("Database operational error creating project for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error creating project for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating project. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error creating project for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again or contact support if the issue persists."
        ) from e


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Retrieve all projects for the authenticated user."
)
async def list_user_projects(
    status_filter: Optional[str] = None,
    language_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all projects for the current user with optional filtering and enhanced error handling."""
    try:
        # Validate filter parameters
        valid_statuses = ["active", "completed", "archived", "on_hold"]
        if status_filter and status_filter.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Must be one of: {', '.join(valid_statuses)}"
            )
        
        start_time = datetime.now()
        
        if status_filter:
            projects = get_projects_by_status(db, current_user.id, status_filter.lower())
        elif language_filter:
            # Sanitize language filter
            language_filter = language_filter.strip().lower()
            if len(language_filter) > 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Language filter too long"
                )
            projects = get_projects_by_language(db, current_user.id, language_filter)
        else:
            projects = get_all_projects(db, current_user.id)
        
        project_responses = [ProjectResponse.model_validate(project) for project in projects]
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Retrieved {len(project_responses)} projects for user {current_user.id} in {query_time:.3f}s")
        
        return ProjectListResponse(
            projects=project_responses,
            total=len(project_responses)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except OperationalError as e:
        logger.error("Database operational error retrieving projects for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error retrieving projects for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving projects. Please refresh and try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error retrieving projects for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while loading projects. Please refresh the page."
        ) from e


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get a specific project",
    description="Retrieve a specific project by ID for the authenticated user."
)
async def get_user_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project by ID with enhanced validation and error handling."""
    try:
        # Validate UUID format
        if not isinstance(project_id, uuid.UUID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format"
            )
        
        project = get_project_by_id_and_user(db, project_id, current_user.id)
        if not project:
            logger.warning(f"Project {project_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found. It may have been deleted or you don't have permission to access it."
            )
        
        logger.info(f"Successfully retrieved project {project_id} for user {current_user.id}")
        return ProjectResponse.model_validate(project)
        
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error("Database operational error retrieving project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error retrieving project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving the project. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error retrieving project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while loading the project. Please try again."
        ) from e


@router.put(
    "/projects/{project_id}",
    response_model=ProjectUpdateResponse,
    summary="Update a project",
    description="Update an existing project for the authenticated user."
)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((OperationalError, SQLAlchemyError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Project update retry {retry_state.attempt_number}/3 for project {project_id}"
    )
)
async def update_user_project(
    project_id: uuid.UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing project with enhanced validation and error handling."""
    try:
        # Validate UUID format
        if not isinstance(project_id, uuid.UUID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format"
            )
        
        # Validate update data
        if project_data.name is not None:
            if not project_data.name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project name cannot be empty"
                )
            if len(project_data.name) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project name cannot exceed 255 characters"
                )
        
        project = update_project(db, project_id, project_data, current_user.id)
        if not project:
            logger.warning(f"Project {project_id} not found for user {current_user.id} during update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found. It may have been deleted or you don't have permission to update it."
            )
        
        logger.info(f"Successfully updated project {project_id} for user {current_user.id}")
        return ProjectUpdateResponse(
            message=f"Project '{project.name}' updated successfully",
            project=ProjectResponse.model_validate(project)
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error("Database integrity error updating project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A project with this name already exists. Please choose a different name."
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid update data provided. Please check your input and try again."
            ) from e
    except OperationalError as e:
        logger.error("Database operational error updating project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error updating project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating project. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error updating project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the project. Please try again."
        ) from e


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectDeleteResponse,
    summary="Delete a project",
    description="Delete an existing project for the authenticated user."
)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((OperationalError, SQLAlchemyError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Project deletion retry {retry_state.attempt_number}/3 for project {project_id}"
    )
)
async def delete_user_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an existing project with enhanced validation and error handling."""
    try:
        # Validate UUID format
        if not isinstance(project_id, uuid.UUID):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format"
            )
        
        success = delete_project(db, project_id, current_user.id)
        if not success:
            logger.warning(f"Project {project_id} not found for user {current_user.id} during deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found. It may have already been deleted or you don't have permission to delete it."
            )
        
        logger.info(f"Successfully deleted project {project_id} for user {current_user.id}")
        return ProjectDeleteResponse(
            message="Project deleted successfully",
            project_id=project_id
        )
        
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error("Database operational error deleting project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error deleting project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting project. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error deleting project %s for user %s: %s", project_id, current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the project. Please try again."
        ) from e


@router.get(
    "/projects/stats/summary",
    summary="Get project statistics",
    description="Get summary statistics for the user's projects."
)
async def get_project_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project statistics for the current user with enhanced error handling and performance tracking."""
    try:
        start_time = datetime.now()
        all_projects = get_all_projects(db, current_user.id)
        
        # Calculate statistics with safe handling
        total_projects = len(all_projects)
        active_projects = len([p for p in all_projects if p.status and p.status.lower() == "active"])
        completed_projects = len([p for p in all_projects if p.status and p.status.lower() == "completed"])
        archived_projects = len([p for p in all_projects if p.status and p.status.lower() == "archived"])
        on_hold_projects = len([p for p in all_projects if p.status and p.status.lower() == "on_hold"])
        
        # Language distribution with safe handling
        languages = {}
        for project in all_projects:
            if project.programming_language and project.programming_language.strip():
                lang = project.programming_language.lower().strip()
                languages[lang] = languages.get(lang, 0) + 1
        
        # Framework distribution with safe handling
        frameworks = {}
        for project in all_projects:
            if project.framework and project.framework.strip():
                framework = project.framework.lower().strip()
                frameworks[framework] = frameworks.get(framework, 0) + 1
        
        # Calculate recent activity (projects created in last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_projects = len([
            p for p in all_projects 
            if hasattr(p, 'created_at') and p.created_at and p.created_at >= thirty_days_ago
        ])
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Generated project statistics for user {current_user.id} in {query_time:.3f}s")
        
        return {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "archived_projects": archived_projects,
            "on_hold_projects": on_hold_projects,
            "recent_projects": recent_projects,
            "language_distribution": dict(sorted(languages.items(), key=lambda x: x[1], reverse=True)),
            "framework_distribution": dict(sorted(frameworks.items(), key=lambda x: x[1], reverse=True)),
            "generated_at": datetime.now().isoformat(),
            "query_time_seconds": round(query_time, 3)
        }
        
    except OperationalError as e:
        logger.error("Database operational error retrieving project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error retrieving project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving statistics. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error retrieving project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while loading statistics. Please refresh and try again."
        ) from e


@router.get(
    "/projects/count",
    summary="Get projects count",
    description="Get the total number of projects for the authenticated user."
)
async def get_user_projects_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get total project count for the current user with optimized query."""
    try:
        count = get_projects_count(db, current_user.id)
        
        return {
            "total_projects": count,
            "user_id": current_user.id,
            "timestamp": datetime.now().isoformat()
        }
        
    except OperationalError as e:
        logger.error("Database operational error getting project count for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error getting project count for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving project count. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error getting project count for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while loading project count. Please try again."
        ) from e


@router.get(
    "/projects/stats/detailed",
    summary="Get detailed project statistics",
    description="Get comprehensive project statistics with optimized database queries."
)
async def get_detailed_project_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed project statistics for the current user with optimized queries."""
    try:
        stats = get_projects_statistics(db, current_user.id)
        
        # Add user context and timestamp
        stats.update({
            "user_id": current_user.id,
            "generated_at": datetime.now().isoformat()
        })
        
        logger.info(f"Generated detailed project statistics for user {current_user.id}")
        return stats
        
    except OperationalError as e:
        logger.error("Database operational error getting detailed project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error getting detailed project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving statistics. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error getting detailed project stats for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while loading detailed statistics. Please try again."
        ) from e


@router.put(
    "/projects/bulk/status",
    summary="Bulk update project status",
    description="Update the status of multiple projects in a single optimized operation."
)
async def bulk_update_projects_status(
    project_ids: List[uuid.UUID],
    new_status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk update project status with validation and optimization."""
    try:
        # Validate inputs
        if not project_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No project IDs provided"
            )
        
        if len(project_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update more than 100 projects at once"
            )
        
        # Validate status
        valid_statuses = ["active", "completed", "archived", "on_hold"]
        if new_status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Perform bulk update
        updated_count = bulk_update_project_status(
            db, current_user.id, project_ids, new_status.lower()
        )
        
        if updated_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No projects found or you don't have permission to update them"
            )
        
        logger.info(f"Bulk updated {updated_count} projects to status '{new_status}' for user {current_user.id}")
        
        return {
            "message": f"Successfully updated {updated_count} projects to status '{new_status}'",
            "updated_count": updated_count,
            "requested_count": len(project_ids),
            "new_status": new_status.lower(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Validation error in bulk update for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except OperationalError as e:
        logger.error("Database operational error in bulk update for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable. Please try again in a moment."
        ) from e
    except SQLAlchemyError as e:
        logger.error("Database error in bulk update for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during bulk update. Please try again."
        ) from e
    except Exception as e:
        logger.error("Unexpected error in bulk update for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during bulk update. Please try again."
        ) from e