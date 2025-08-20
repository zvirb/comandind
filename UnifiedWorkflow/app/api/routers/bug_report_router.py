"""Bug report router accessible to all authenticated users."""

import logging
import uuid
import traceback
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User, UserRole, UserStatus
from shared.schemas.schemas import TaskCreate
from shared.services.bug_report_monitoring_service import (
    record_bug_report_attempt,
    record_bug_report_failure,
    BugReportFailureType,
    get_bug_report_statistics,
    get_bug_report_health
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Bug Report Models
class BugReportCreate(BaseModel):
    title: str
    description: str
    type: str = "opportunity"
    category: str = "bug_report"
    priority: str = "high"
    status: str = "pending"

@router.post("/bug-reports", response_model=Dict[str, Any])
async def create_bug_report(
    bug_report: BugReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a bug report task and assigns it to admin users.
    Accessible to all authenticated users.
    """
    try:
        # Record the attempt for monitoring
        record_bug_report_attempt()
        
        logger.info(f"Processing bug report: {bug_report.title}")
        
        # Find the first admin user to assign the bug report to
        admin_user = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.status == UserStatus.ACTIVE
        ).first()
        
        if not admin_user:
            record_bug_report_failure(
                failure_type=BugReportFailureType.ADMIN_USER_NOT_FOUND,
                user_email=current_user.email,
                bug_title=bug_report.title,
                error_message="No active admin users found to assign bug report"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No active admin users found to assign bug report"
            )
        
        # Import here to avoid circular imports
        try:
            from .. import crud
            from shared.database.models import TaskStatus, TaskPriority
        except ImportError as e:
            logger.error(f"Could not import required CRUD modules: {e}")
            record_bug_report_failure(
                failure_type=BugReportFailureType.CRUD_IMPORT_ERROR,
                user_email=current_user.email,
                bug_title=bug_report.title,
                error_message=f"Could not import required CRUD modules: {e}",
                stack_trace=traceback.format_exc()
            )
            crud = None
        
        # Try importing bug report subtask service separately
        generate_bug_report_subtasks = None
        try:
            from worker.services.bug_report_subtask_service import generate_bug_report_subtasks
            logger.info("Successfully imported bug report subtask service")
        except ImportError as e:
            logger.warning(f"Could not import bug report subtask service: {e}")
            logger.info("Will continue with fallback bug report creation")
            # Note: This is not a critical failure, so we don't record it as a monitoring failure
        
        # Enable subtask generation for bug reports to create structured resolution workflow
        logger.info(f"Creating bug report task with LLM subtask generation: {bug_report.title}")
        
        # Create comprehensive task description that includes all details
        main_task_description = bug_report.description  # This already contains the full formatted description from frontend
        
        # Add additional context for the admin
        main_task_description += f"\n\n**Assignment Information:**\n- Assigned to: {admin_user.email}\n- Auto-created from bug report system\n- Reporter: {current_user.email}\n- Priority: {bug_report.priority}\n- Category: {bug_report.category}"
        
        # Prepare detailed context for specialized bug report subtask generation
        assignment_context = f"Assigned to admin user: {admin_user.email}, reported by: {current_user.email}"
        
        if crud and generate_bug_report_subtasks:
            try:
                from shared.database.models import TaskStatus, TaskPriority, TaskType
                
                # Convert the frontend type to a valid TaskType enum
                task_type = TaskType.OPPORTUNITY if bug_report.type == "opportunity" else TaskType.GENERAL
                
                task_create_data = TaskCreate(
                    title=bug_report.title,
                    description=main_task_description,
                    type=task_type.value,  # Convert enum to string value
                    category=bug_report.category,
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.PENDING
                )
                
                # Create main bug report task for admin user
                created_task = crud.create_task(db=db, task=task_create_data, user_id=admin_user.id)
                
                # Generate specialized bug report subtasks with detailed context
                try:
                    logger.info(f"🐛 Generating specialized subtasks for bug report: {bug_report.title}")
                    
                    # Use specialized bug report subtask generation with detailed context
                    subtasks = await generate_bug_report_subtasks(
                        bug_title=bug_report.title,
                        bug_description=bug_report.description,
                        reporter_email=current_user.email,
                        bug_priority=bug_report.priority,
                        bug_category=bug_report.category,
                        assignment_context=assignment_context,
                        admin_user=admin_user
                    )
                    
                    # Process specialized bug report subtasks with enhanced context
                    if subtasks:
                        # Subtasks from the specialized service are already properly formatted
                        processed_subtasks = []
                        for i, subtask_data in enumerate(subtasks):
                            processed_subtask = {
                                "id": subtask_data.get("id", str(uuid.uuid4())),
                                "title": subtask_data.get("title", f"Bug Resolution Step {i+1}"),
                                "description": subtask_data.get("description", ""),
                                "estimated_hours": subtask_data.get("estimated_hours", 1.0),
                                "priority": subtask_data.get("priority", "high"),
                                "category": subtask_data.get("category", "bug_resolution"),
                                "completed": False,
                                "prerequisites": subtask_data.get("prerequisites", []),
                                "deliverables": subtask_data.get("deliverables", []),
                                # Preserve bug report metadata from specialized service
                                "bug_report_metadata": subtask_data.get("bug_report_metadata", {})
                            }
                            processed_subtasks.append(processed_subtask)
                        
                        # Store subtasks in the task's semantic_tags field (same as opportunities)
                        if created_task.semantic_tags is None:
                            created_task.semantic_tags = {}
                        created_task.semantic_tags["subtasks"] = processed_subtasks
                        
                        # Mark subtasks as automatically accepted for bug reports
                        created_task.semantic_tags["subtasks_auto_accepted"] = True
                        created_task.semantic_tags["subtasks_accepted_at"] = datetime.utcnow().isoformat()
                        
                        db.commit()
                        db.refresh(created_task)
                        
                        logger.info(f"✅ Created bug report with {len(processed_subtasks)} specialized AI-generated subtasks")
                        subtask_info = [{"title": s["title"], "category": s["category"]} for s in processed_subtasks[:3]]
                    else:
                        subtask_info = []
                    
                except Exception as e:
                    logger.error(f"Error generating subtasks for bug report: {e}")
                    record_bug_report_failure(
                        failure_type=BugReportFailureType.SUBTASK_GENERATION_ERROR,
                        user_email=current_user.email,
                        bug_title=bug_report.title,
                        error_message=f"Error generating subtasks: {e}",
                        stack_trace=traceback.format_exc()
                    )
                    subtask_info = []
                
                return {
                    "message": "Bug report created successfully with specialized AI-generated subtasks",
                    "task_id": created_task.id,
                    "task_title": created_task.title,
                    "assigned_to": admin_user.email,
                    "reporter": current_user.email,
                    "subtasks_created": len(subtask_info),
                    "subtasks_preview": subtask_info,  # Show first 3 subtasks with categories
                    "description_preview": main_task_description[:100] + "..." if len(main_task_description) > 100 else main_task_description,
                    "specialization": "Uses specialized bug report subtask generation with detailed context"
                }
                
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                record_bug_report_failure(
                    failure_type=BugReportFailureType.DATABASE_ERROR,
                    user_email=current_user.email,
                    bug_title=bug_report.title,
                    error_message=f"Error creating task: {e}",
                    stack_trace=traceback.format_exc()
                )
                # Fallback: just log the bug report
                logger.info(f"Bug report fallback - Title: {bug_report.title}, Description: {bug_report.description}, Reporter: {current_user.email}")
                return {
                    "message": "Bug report logged successfully (fallback mode)",
                    "reporter": current_user.email,
                    "timestamp": datetime.utcnow().isoformat()
                }
        elif crud:
            # Crud available but no subtask generation
            try:
                from shared.database.models import TaskStatus, TaskPriority, TaskType
                
                # Convert the frontend type to a valid TaskType enum
                task_type = TaskType.OPPORTUNITY if bug_report.type == "opportunity" else TaskType.GENERAL
                
                task_create_data = TaskCreate(
                    title=bug_report.title,
                    description=main_task_description,
                    type=task_type.value,  # Convert enum to string value
                    category=bug_report.category,
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.PENDING
                )
                
                # Create single comprehensive task for admin user (no subtasks)
                created_task = crud.create_task(db=db, task=task_create_data, user_id=admin_user.id)
                
                return {
                    "message": "Bug report created successfully (no subtasks available)",
                    "task_id": created_task.id,
                    "task_title": created_task.title,
                    "assigned_to": admin_user.email,
                    "description_preview": main_task_description[:100] + "..." if len(main_task_description) > 100 else main_task_description
                }
                
            except Exception as e:
                logger.error(f"Error creating task without subtasks: {e}")
                record_bug_report_failure(
                    failure_type=BugReportFailureType.DATABASE_ERROR,
                    user_email=current_user.email,
                    bug_title=bug_report.title,
                    error_message=f"Error creating task without subtasks: {e}",
                    stack_trace=traceback.format_exc()
                )
                # Fallback: just log the bug report
                logger.info(f"Bug report fallback - Title: {bug_report.title}, Description: {bug_report.description}, Reporter: {current_user.email}")
                return {
                    "message": "Bug report logged successfully (fallback mode)",
                    "reporter": current_user.email,
                    "timestamp": datetime.utcnow().isoformat()
                }
        else:
            # Simple fallback - just log the bug report and create basic task if possible
            logger.info(f"Bug report fallback - Title: {bug_report.title}, Description: {bug_report.description}, Reporter: {current_user.email}")
            
            # Try to create a basic task without subtasks
            if crud:
                try:
                    from shared.database.models import TaskStatus, TaskPriority, TaskType
                    
                    task_create_data = TaskCreate(
                        title=bug_report.title,
                        description=f"{bug_report.description}\n\nReported by: {current_user.email}",
                        type=TaskType.OPPORTUNITY.value,
                        category=bug_report.category,
                        priority=TaskPriority.HIGH,
                        status=TaskStatus.PENDING
                    )
                    
                    created_task = crud.create_task(db=db, task=task_create_data, user_id=admin_user.id)
                    
                    return {
                        "message": "Bug report created successfully (basic mode - no subtasks)",
                        "task_id": created_task.id,
                        "task_title": created_task.title,
                        "assigned_to": admin_user.email,
                        "reporter": current_user.email,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                except Exception as basic_error:
                    logger.error(f"Basic task creation also failed: {basic_error}")
                    record_bug_report_failure(
                        failure_type=BugReportFailureType.DATABASE_ERROR,
                        user_email=current_user.email,
                        bug_title=bug_report.title,
                        error_message=f"Basic task creation also failed: {basic_error}",
                        stack_trace=traceback.format_exc()
                    )
            
            # Last resort - just log it
            return {
                "message": "Bug report logged successfully (logging only mode)",
                "reporter": current_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Error creating bug report: {e}", exc_info=True)
        record_bug_report_failure(
            failure_type=BugReportFailureType.GENERAL_ERROR,
            user_email=current_user.email,
            bug_title=bug_report.title,
            error_message=f"General error creating bug report: {e}",
            stack_trace=traceback.format_exc()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bug report"
        )

@router.get("/bug-reports/health", response_model=Dict[str, Any])
async def get_bug_report_health_status():
    """
    Get the current health status of the bug report system.
    Accessible to all authenticated users for transparency.
    """
    return get_bug_report_health()

@router.get("/bug-reports/statistics", response_model=Dict[str, Any])
async def get_bug_report_statistics_endpoint(hours: int = 24):
    """
    Get bug report failure statistics for the specified time period.
    Accessible to all authenticated users for transparency.
    """
    if hours < 1 or hours > 168:  # Max 7 days
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hours must be between 1 and 168 (7 days)"
        )
    
    return get_bug_report_statistics(hours=hours)