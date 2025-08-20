"""
Service layer for project-related database operations.

This module provides a set of functions to interact with the Project model
in the database. It handles all CRUD operations for projects with proper
error handling and transaction management.
"""
import logging
import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_, text

from shared.database.models import Project
from shared.schemas.project_schemas import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)


def create_project(db: Session, project_data: ProjectCreate, user_id: int) -> Project:
    """
    Creates a new project record in the database.
    
    Args:
        db: Database session
        project_data: Project creation data
        user_id: ID of the user creating the project
        
    Returns:
        Created project instance
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    db_project = Project(
        id=uuid.uuid4(),
        user_id=user_id,
        name=project_data.name,
        description=project_data.description,
        project_type=project_data.project_type,
        programming_language=project_data.programming_language,
        framework=project_data.framework,
        repository_url=project_data.repository_url,
        local_path=project_data.local_path,
        status=project_data.status,
        project_metadata=project_data.project_metadata
    )
    
    try:
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        logger.info("Created project record with ID: %s for user: %s", db_project.id, user_id)
        return db_project
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error while creating project: %s", e, exc_info=True)
        raise


def get_all_projects(db: Session, user_id: int, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[Project]:
    """
    Retrieves all projects for a given user with optimized query and pagination.
    
    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of projects to return
        offset: Number of projects to skip for pagination
        
    Returns:
        List of projects ordered by creation date (newest first)
    """
    try:
        # Log query start time for performance monitoring
        start_time = datetime.now()
        
        query = db.query(Project).filter(
            Project.user_id == user_id
        ).order_by(Project.created_at.desc())
        
        # Add pagination if specified
        if limit is not None:
            query = query.limit(limit)
        if offset is not None and offset > 0:
            query = query.offset(offset)
        
        projects = query.all()
        
        # Log performance metrics
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Retrieved {len(projects)} projects for user {user_id} in {query_time:.3f}s")
        
        return projects
        
    except SQLAlchemyError as e:
        logger.error("Database error while retrieving projects for user %s: %s", user_id, e, exc_info=True)
        raise


def get_project_by_id_and_user(db: Session, project_id: uuid.UUID, user_id: int) -> Optional[Project]:
    """
    Retrieves a single project by its ID, ensuring it belongs to the specified user.
    
    Args:
        db: Database session
        project_id: Project UUID
        user_id: User ID (for ownership verification)
        
    Returns:
        Project instance if found and owned by user, None otherwise
    """
    try:
        return db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
    except SQLAlchemyError as e:
        logger.error("Database error while retrieving project %s for user %s: %s", project_id, user_id, e, exc_info=True)
        raise


def update_project(db: Session, project_id: uuid.UUID, project_data: ProjectUpdate, user_id: int) -> Optional[Project]:
    """
    Updates an existing project record.
    
    Args:
        db: Database session
        project_id: Project UUID
        project_data: Project update data
        user_id: User ID (for ownership verification)
        
    Returns:
        Updated project instance if found and owned by user, None otherwise
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        db_project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        
        if not db_project:
            return None
            
        # Update only provided fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_project, field):
                setattr(db_project, field, value)
        
        db.commit()
        db.refresh(db_project)
        logger.info("Updated project with ID: %s for user: %s", project_id, user_id)
        return db_project
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error while updating project %s: %s", project_id, e, exc_info=True)
        raise


def delete_project(db: Session, project_id: uuid.UUID, user_id: int) -> bool:
    """
    Deletes a project record from the database.
    
    Args:
        db: Database session
        project_id: Project UUID
        user_id: User ID (for ownership verification)
        
    Returns:
        True if project was deleted, False if not found or not owned by user
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        db_project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        
        if not db_project:
            return False
            
        db.delete(db_project)
        db.commit()
        logger.info("Deleted project with ID: %s for user: %s", project_id, user_id)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error while deleting project %s: %s", project_id, e, exc_info=True)
        raise


def get_projects_by_status(db: Session, user_id: int, status: str, limit: Optional[int] = None) -> List[Project]:
    """
    Retrieves projects for a user filtered by status with optimized query.
    
    Args:
        db: Database session
        user_id: User ID
        status: Project status to filter by
        limit: Maximum number of projects to return
        
    Returns:
        List of projects with specified status
    """
    try:
        start_time = datetime.now()
        
        # Use case-insensitive comparison and add indexing hint
        query = db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                func.lower(Project.status) == status.lower()
            )
        ).order_by(Project.created_at.desc())
        
        if limit is not None:
            query = query.limit(limit)
        
        projects = query.all()
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Retrieved {len(projects)} projects with status '{status}' for user {user_id} in {query_time:.3f}s")
        
        return projects
        
    except SQLAlchemyError as e:
        logger.error("Database error while retrieving projects by status for user %s: %s", user_id, e, exc_info=True)
        raise


def get_projects_by_language(db: Session, user_id: int, language: str, limit: Optional[int] = None) -> List[Project]:
    """
    Retrieves projects for a user filtered by programming language with optimized query.
    
    Args:
        db: Database session
        user_id: User ID
        language: Programming language to filter by
        limit: Maximum number of projects to return
        
    Returns:
        List of projects using specified language
    """
    try:
        start_time = datetime.now()
        
        # Sanitize input and optimize query
        safe_language = language.strip()
        
        # Use more precise filtering - exact match first, then partial
        query = db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                or_(
                    func.lower(Project.programming_language) == safe_language.lower(),
                    Project.programming_language.ilike(f"%{safe_language}%")
                )
            )
        ).order_by(
            # Exact matches first, then partial matches
            func.lower(Project.programming_language) == safe_language.lower(),
            Project.created_at.desc()
        )
        
        if limit is not None:
            query = query.limit(limit)
        
        projects = query.all()
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Retrieved {len(projects)} projects with language '{language}' for user {user_id} in {query_time:.3f}s")
        
        return projects
        
    except SQLAlchemyError as e:
        logger.error("Database error while retrieving projects by language for user %s: %s", user_id, e, exc_info=True)
        raise


def get_projects_count(db: Session, user_id: int) -> int:
    """
    Get total count of projects for a user with optimized query.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Total number of projects for the user
    """
    try:
        start_time = datetime.now()
        
        count = db.query(func.count(Project.id)).filter(
            Project.user_id == user_id
        ).scalar()
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Retrieved project count ({count}) for user {user_id} in {query_time:.3f}s")
        
        return count or 0
        
    except SQLAlchemyError as e:
        logger.error("Database error while counting projects for user %s: %s", user_id, e, exc_info=True)
        raise


def get_projects_statistics(db: Session, user_id: int) -> dict:
    """
    Get comprehensive project statistics for a user with optimized single query.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dictionary with comprehensive project statistics
    """
    try:
        start_time = datetime.now()
        
        # Single optimized query for all statistics
        stats_query = db.query(
            func.count(Project.id).label('total'),
            func.count(func.nullif(Project.status != 'active', False)).label('active'),
            func.count(func.nullif(Project.status != 'completed', False)).label('completed'),
            func.count(func.nullif(Project.status != 'archived', False)).label('archived'),
            func.count(func.nullif(Project.status != 'on_hold', False)).label('on_hold'),
            func.count(Project.programming_language).label('with_language'),
            func.count(Project.framework).label('with_framework')
        ).filter(Project.user_id == user_id)
        
        result = stats_query.first()
        
        # Get language and framework distributions with separate optimized queries
        language_stats = db.query(
            Project.programming_language,
            func.count(Project.id).label('count')
        ).filter(
            and_(
                Project.user_id == user_id,
                Project.programming_language.isnot(None),
                Project.programming_language != ''
            )
        ).group_by(Project.programming_language).all()
        
        framework_stats = db.query(
            Project.framework,
            func.count(Project.id).label('count')
        ).filter(
            and_(
                Project.user_id == user_id,
                Project.framework.isnot(None),
                Project.framework != ''
            )
        ).group_by(Project.framework).all()
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Generated comprehensive project statistics for user {user_id} in {query_time:.3f}s")
        
        return {
            'total_projects': result.total or 0,
            'active_projects': result.active or 0,
            'completed_projects': result.completed or 0,
            'archived_projects': result.archived or 0,
            'on_hold_projects': result.on_hold or 0,
            'projects_with_language': result.with_language or 0,
            'projects_with_framework': result.with_framework or 0,
            'language_distribution': {lang: count for lang, count in language_stats},
            'framework_distribution': {framework: count for framework, count in framework_stats},
            'query_time_seconds': round(query_time, 3)
        }
        
    except SQLAlchemyError as e:
        logger.error("Database error while generating project statistics for user %s: %s", user_id, e, exc_info=True)
        raise


def bulk_update_project_status(db: Session, user_id: int, project_ids: List[uuid.UUID], new_status: str) -> int:
    """
    Bulk update project status for multiple projects with optimized query.
    
    Args:
        db: Database session
        user_id: User ID (for security)
        project_ids: List of project UUIDs to update
        new_status: New status to set
        
    Returns:
        Number of projects updated
    """
    try:
        start_time = datetime.now()
        
        # Validate inputs
        if not project_ids:
            return 0
        
        if len(project_ids) > 100:  # Prevent excessive bulk operations
            raise ValueError("Cannot update more than 100 projects at once")
        
        # Perform bulk update with user_id check for security
        updated_count = db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.id.in_(project_ids)
            )
        ).update(
            {
                'status': new_status,
                'updated_at': datetime.now()
            },
            synchronize_session=False
        )
        
        db.commit()
        
        query_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Bulk updated {updated_count} projects to status '{new_status}' for user {user_id} in {query_time:.3f}s")
        
        return updated_count
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error during bulk project status update for user %s: %s", user_id, e, exc_info=True)
        raise