"""Router for handling task-related operations."""
import logging
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from shared.schemas import schemas
from api import crud
from api.dependencies import get_db, get_current_user, verify_csrf_token
from shared.database.models import User, Task

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("", response_model=List[schemas.Task])
async def get_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieves all tasks for the current user.
    """
    return crud.get_tasks_by_user(db=db, user_id=current_user.id)

@router.post("", response_model=schemas.Task, dependencies=[Depends(verify_csrf_token)])
async def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new task for the current user.
    """
    return crud.create_task(db=db, task=task, user_id=current_user.id)

@router.put("/{task_id}", response_model=schemas.Task, dependencies=[Depends(verify_csrf_token)])
async def update_task(
    task_id: str,
    task: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates a task for the current user.
    """
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        return crud.update_task(db=db, task_id=task_id, task=task, user_id=current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/{task_id}", dependencies=[Depends(verify_csrf_token)])
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a task for the current user.
    """
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        crud.delete_task(db=db, task_id=task_id, user_id=current_user.id)
        return {
            "message": f"Task {task_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

@router.post("/opportunities/{opportunity_id}/feedback", response_model=schemas.TaskFeedback, dependencies=[Depends(verify_csrf_token)])
async def create_opportunity_feedback(
    opportunity_id: str,
    feedback: schemas.TaskFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits feedback for a completed opportunity.
    """
    try:
        # Here you would also add logic to mark the opportunity itself as 'achieved'
        # For example:
        # crud.update_opportunity_status(db, opportunity_id, status="achieved")
        
        return crud.create_opportunity_feedback(
            db=db, 
            feedback=feedback, 
            opportunity_id=opportunity_id, 
            user_id=current_user.id
        )
    except Exception as e:
        logger.error(f"Failed to create opportunity feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create feedback: {str(e)}")

# Subtask endpoints
@router.post("/{task_id}/subtasks/generate", response_model=schemas.SubtaskGenerationResponse, dependencies=[Depends(verify_csrf_token)])
async def generate_subtasks(
    task_id: str,
    request: schemas.SubtaskGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI subtasks for a task with comprehensive context support."""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"🎯 Generating subtasks for task {task_id}, user {current_user.id}")
        logger.debug(f"📋 Request context: {request.context}")
        logger.debug(f"⚙️ Request settings: max_subtasks={request.max_subtasks}, include_analysis={request.include_analysis}")
        
        if not task_id or task_id == "undefined":
            logger.error(f"Invalid task ID provided: {task_id}")
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        # Convert string task_id to UUID
        try:
            task_uuid = uuid.UUID(task_id)
            logger.debug(f"Successfully converted task_id to UUID: {task_uuid}")
        except ValueError as uuid_error:
            logger.error(f"UUID conversion failed for task_id {task_id}: {uuid_error}")
            raise HTTPException(status_code=400, detail=f"Invalid task ID format: {str(uuid_error)}")
        
        # Get the task
        db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == current_user.id).first()
        if not db_task:
            logger.error(f"Task not found: {task_uuid} for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"📝 Found task: {db_task.title} (ID: {db_task.id})")
        
        # Build comprehensive context from request
        comprehensive_context = {
            "user_context": request.context.user_context or "",
            "supplementary_context": request.context.supplementary_context or "",
            "skill_level": request.context.skill_level,
            "preferred_approach": request.context.preferred_approach,
            "time_constraints": request.context.time_constraints,
            "preferred_categories": request.context.preferred_categories,
            "max_subtasks": request.max_subtasks
        }
        
        # Enhance supplementary context with user preferences
        enhanced_supplementary = request.context.supplementary_context or ""
        if request.context.time_constraints:
            enhanced_supplementary += f" Time constraints: {request.context.time_constraints}."
        if request.context.preferred_categories:
            enhanced_supplementary += f" Preferred categories: {', '.join(request.context.preferred_categories)}."
        if request.context.skill_level != "intermediate":
            enhanced_supplementary += f" User skill level: {request.context.skill_level}."
        if request.context.preferred_approach != "balanced":
            enhanced_supplementary += f" Preferred approach: {request.context.preferred_approach}."
        
        # Generate contextual subtasks using LLM
        from worker.services.opportunity_subtask_service import generate_contextual_subtasks
        
        try:
            logger.info(f"🤖 Generating contextual subtasks for opportunity: {db_task.title}")
            logger.info(f"📊 Context length - user: {len(comprehensive_context['user_context'])}, supplementary: {len(enhanced_supplementary)}")
            
            # Prepare regeneration context if available
            regeneration_context = None
            if hasattr(request.context, 'previous_attempts') and request.context.previous_attempts:
                logger.info(f"🔄 Using regeneration context from previous attempts")
                regeneration_context = {
                    'selected_tasks': request.context.selected_subtasks or [],
                    'rejected_tasks': request.context.rejected_subtasks or [],
                    'attempt': request.context.attempt + 1 if hasattr(request.context, 'attempt') else len(request.context.previous_attempts) + 1
                }
                logger.info(f"📊 Regeneration context: {len(regeneration_context['selected_tasks'])} selected, {len(regeneration_context['rejected_tasks'])} rejected, attempt #{regeneration_context['attempt']}")

            suggested_subtasks = await generate_contextual_subtasks(
                opportunity_title=db_task.title,
                opportunity_description=db_task.description or "",
                user_context=comprehensive_context["user_context"],
                supplementary_context=enhanced_supplementary,
                current_user=current_user,
                regeneration_context=regeneration_context
            )
            logger.info(f"✅ Generated {len(suggested_subtasks)} contextual subtasks")
            
            # Convert to response format
            generated_subtasks = []
            for subtask in suggested_subtasks:
                generated_subtasks.append(schemas.GeneratedSubtask(
                    id=subtask.get("id", str(uuid.uuid4())),
                    title=subtask.get("title", ""),
                    description=subtask.get("description", ""),
                    estimated_hours=subtask.get("estimated_hours", 1.0),
                    priority=subtask.get("priority", "medium"),
                    category=subtask.get("category", "execution"),
                    completed=subtask.get("completed", False),
                    prerequisites=subtask.get("prerequisites", []),
                    deliverables=subtask.get("deliverables", [])
                ))
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            return schemas.SubtaskGenerationResponse(
                subtasks=generated_subtasks,
                analysis=None if not request.include_analysis else {
                    "opportunity_type": "contextual_generation",
                    "generation_method": "llm_contextual",
                    "context_factors_used": [
                        "user_context" if comprehensive_context["user_context"] else None,
                        "supplementary_context" if enhanced_supplementary else None,
                        "skill_level" if request.context.skill_level != "intermediate" else None,
                        "preferred_approach" if request.context.preferred_approach != "balanced" else None,
                        "time_constraints" if request.context.time_constraints else None
                    ]
                },
                generation_metadata={
                    "task_title": db_task.title,
                    "context_length": len(comprehensive_context["user_context"]) + len(enhanced_supplementary),
                    "requested_max_subtasks": request.max_subtasks,
                    "actual_subtasks_generated": len(generated_subtasks),
                    "generation_method": "llm_contextual"
                },
                confidence_score=0.85,  # High confidence for successful LLM generation
                processing_time_ms=processing_time_ms
            )
            
        except Exception as llm_error:
            logger.warning(f"⚠️ LLM subtask generation failed, using fallback: {llm_error}")
            # Fallback to more generic but still contextual subtasks
            fallback_subtasks = []
            
            # Generate contextual fallback based on user preferences
            skill_level = request.context.skill_level
            categories = request.context.preferred_categories or ["research", "planning", "execution"]
            
            # Adjust subtasks based on skill level
            if skill_level == "beginner":
                fallback_data = [
                    ("Research and understand", "Learn about the fundamentals and gather basic information", 2.0, "research"),
                    ("Practice basics", "Start with simple exercises or tutorials", 3.0, "learning"),
                    ("Create first attempt", "Make an initial simple version or prototype", 2.5, "execution"),
                    ("Get feedback and improve", "Share with others and refine based on input", 1.5, "review")
                ]
            elif skill_level == "advanced":
                fallback_data = [
                    ("Strategic analysis", "Conduct in-depth analysis of requirements and constraints", 1.5, "research"),
                    ("Design optimal approach", "Create comprehensive plan with alternatives", 1.0, "planning"),
                    ("Execute with excellence", "Implement using best practices and advanced techniques", 3.0, "execution")
                ]
            else:  # intermediate
                fallback_data = [
                    ("Research and analyze requirements", "Gather information, identify requirements, and understand scope", 1.5, "research"),
                    ("Create detailed action plan", "Develop step-by-step approach with timeline", 1.0, "planning"),
                    ("Execute and complete", "Implement the planned approach and achieve objectives", 3.0, "execution")
                ]
            
            for title_prefix, description, hours, category in fallback_data[:request.max_subtasks]:
                fallback_subtasks.append(schemas.GeneratedSubtask(
                    id=str(uuid.uuid4()),
                    title=f"{title_prefix} for {db_task.title}",
                    description=description,
                    estimated_hours=hours,
                    priority="medium",
                    category=category,
                    completed=False
                ))
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            return schemas.SubtaskGenerationResponse(
                subtasks=fallback_subtasks,
                analysis=None if not request.include_analysis else {
                    "opportunity_type": "fallback_generation",
                    "generation_method": "rule_based_fallback",
                    "fallback_reason": str(llm_error),
                    "skill_level_considered": skill_level
                },
                generation_metadata={
                    "task_title": db_task.title,
                    "generation_method": "rule_based_fallback",
                    "requested_max_subtasks": request.max_subtasks,
                    "actual_subtasks_generated": len(fallback_subtasks),
                    "fallback_triggered": True
                },
                confidence_score=0.6,  # Lower confidence for fallback
                processing_time_ms=processing_time_ms
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate subtasks for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate subtasks: {str(e)}")

@router.post("/{task_id}/subtasks", dependencies=[Depends(verify_csrf_token)])
async def create_subtasks(
    task_id: str,
    subtasks_data: Dict[str, List[Dict[str, Any]]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create subtasks for a task."""
    try:
        logger.info(f"Creating subtasks for task {task_id}, user {current_user.id}")
        logger.debug(f"Received subtasks_data: {subtasks_data}")
        
        if not task_id or task_id == "undefined":
            logger.error(f"Invalid task ID provided: {task_id}")
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        # Convert string task_id to UUID
        try:
            task_uuid = uuid.UUID(task_id)
            logger.debug(f"Successfully converted task_id to UUID: {task_uuid}")
        except ValueError as uuid_error:
            logger.error(f"UUID conversion failed for task_id {task_id}: {uuid_error}")
            raise HTTPException(status_code=400, detail=f"Invalid task ID format: {str(uuid_error)}")
        
        # Get the task
        db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == current_user.id).first()
        if not db_task:
            logger.error(f"Task not found: {task_uuid} for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Found task: {db_task.title} (ID: {db_task.id})")
        
        subtasks = subtasks_data.get("subtasks", [])
        logger.debug(f"Extracted subtasks: {subtasks}")
        
        if not subtasks:
            logger.warning("No subtasks provided in request")
            return {"subtasks": [], "message": "No subtasks to create"}
        
        # Ensure each subtask has an ID
        for i, subtask in enumerate(subtasks):
            if "id" not in subtask:
                subtask["id"] = str(uuid.uuid4())
                logger.debug(f"Generated ID for subtask {i}: {subtask['id']}")
            if "completed" not in subtask:
                subtask["completed"] = False
        
        logger.debug(f"Processed subtasks: {subtasks}")
        
        # Store subtasks in the task's JSON field
        if db_task.semantic_tags is None:
            db_task.semantic_tags = {}
            logger.debug("Initialized empty semantic_tags")
        
        # Use semantic_tags JSONB field to store subtasks
        db_task.semantic_tags["subtasks"] = subtasks
        logger.info(f"Updated semantic_tags with {len(subtasks)} subtasks")
        
        try:
            db.commit()
            logger.info("Database commit successful")
        except Exception as commit_error:
            logger.error(f"Database commit failed: {commit_error}", exc_info=True)
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database commit failed: {str(commit_error)}")
        
        try:
            db.refresh(db_task)
            logger.debug("Database refresh successful")
        except Exception as refresh_error:
            logger.error(f"Database refresh failed: {refresh_error}", exc_info=True)
            # Don't fail the request if refresh fails
        
        logger.info(f"Successfully created {len(subtasks)} subtasks for task {task_id}")
        return {"subtasks": subtasks, "message": "Subtasks created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating subtasks for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create subtasks: {str(e)}")

@router.put("/{task_id}/subtasks/{subtask_id}", dependencies=[Depends(verify_csrf_token)])
async def update_subtask(
    task_id: str,
    subtask_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific subtask."""
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        # Convert string task_id to UUID
        task_uuid = uuid.UUID(task_id)
        
        # Get the task
        db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == current_user.id).first()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get subtasks from semantic_tags
        if not db_task.semantic_tags or "subtasks" not in db_task.semantic_tags:
            raise HTTPException(status_code=404, detail="No subtasks found for this task")
        
        subtasks = db_task.semantic_tags["subtasks"]
        
        # Find and update the specific subtask
        subtask_found = False
        for subtask in subtasks:
            if subtask.get("id") == subtask_id:
                subtask.update(updates)
                subtask_found = True
                break
        
        if not subtask_found:
            raise HTTPException(status_code=404, detail="Subtask not found")
        
        # Update the task
        db_task.semantic_tags = {**db_task.semantic_tags, "subtasks": subtasks}
        db.commit()
        db.refresh(db_task)
        
        # Return the updated subtask
        updated_subtask = next(s for s in subtasks if s.get("id") == subtask_id)
        return updated_subtask
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update subtask {subtask_id} for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update subtask: {str(e)}")

@router.delete("/{task_id}/subtasks/{subtask_id}", dependencies=[Depends(verify_csrf_token)])
async def delete_subtask(
    task_id: str,
    subtask_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific subtask."""
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        # Convert string task_id to UUID
        task_uuid = uuid.UUID(task_id)
        
        # Get the task
        db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == current_user.id).first()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get subtasks from semantic_tags
        if not db_task.semantic_tags or "subtasks" not in db_task.semantic_tags:
            raise HTTPException(status_code=404, detail="No subtasks found for this task")
        
        subtasks = db_task.semantic_tags["subtasks"]
        
        # Find and remove the specific subtask
        original_count = len(subtasks)
        subtasks = [s for s in subtasks if s.get("id") != subtask_id]
        
        if len(subtasks) == original_count:
            raise HTTPException(status_code=404, detail="Subtask not found")
        
        # Update the task
        db_task.semantic_tags = {**db_task.semantic_tags, "subtasks": subtasks}
        db.commit()
        
        return {"message": f"Subtask {subtask_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete subtask {subtask_id} for task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete subtask: {str(e)}")