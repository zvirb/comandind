"""Temporary router for tasks with auth bypass for debugging."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shared.schemas import schemas
from api import crud
from api.dependencies import get_db
from shared.database.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

# TEMPORARY: Default user for testing
DEFAULT_USER_ID = 6  # admin@aiwfe.com from database

@router.get("", response_model=List[schemas.Task])
async def get_tasks(db: Session = Depends(get_db)):
    """Retrieves all tasks for default user (TEMPORARY)."""
    return crud.get_tasks_by_user(db=db, user_id=DEFAULT_USER_ID)

@router.post("", response_model=schemas.Task)
async def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db)
):
    """Creates a new task for default user (TEMPORARY)."""
    return crud.create_task(db=db, task=task, user_id=DEFAULT_USER_ID)

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(
    task_id: str,
    task: schemas.TaskUpdate,
    db: Session = Depends(get_db)
):
    """Updates a task for default user (TEMPORARY)."""
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        return crud.update_task(db=db, task_id=task_id, task=task, user_id=DEFAULT_USER_ID)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Deletes a task for default user (TEMPORARY)."""
    try:
        if not task_id or task_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid task ID")
        
        crud.delete_task(db=db, task_id=task_id, user_id=DEFAULT_USER_ID)
        return {"message": f"Task {task_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")