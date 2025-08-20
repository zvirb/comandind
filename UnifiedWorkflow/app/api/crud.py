import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from fastapi import HTTPException
from shared.schemas import schemas
from shared.database.models import Task, TaskFeedback, TaskStatus

def get_tasks_by_user(db: Session, user_id: int):
    return db.query(Task).filter(Task.user_id == user_id).all()

def create_task(db: Session, task: schemas.TaskCreate, user_id: int):
    task_data = task.model_dump()
    task_data['task_type'] = task_data.pop('type')
    db_task = Task(**task_data, user_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: str, task: schemas.TaskUpdate, user_id: int):
    try:
        # Convert string task_id to UUID
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == user_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task.model_dump(exclude_unset=True).items():
        if key == 'type':
            setattr(db_task, 'task_type', value)
        elif key == 'completed':
            # Convert completed boolean to TaskStatus
            if value is True:
                setattr(db_task, 'status', TaskStatus.COMPLETED)
            elif value is False:
                setattr(db_task, 'status', TaskStatus.PENDING)
        else:
            setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: str, user_id: int):
    try:
        # Convert string task_id to UUID
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID format")
    
    db_task = db.query(Task).filter(Task.id == task_uuid, Task.user_id == user_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete any associated task feedback first to avoid foreign key constraint
    db.query(TaskFeedback).filter(TaskFeedback.opportunity_id == task_uuid).delete()
    
    # Now delete the task
    db.delete(db_task)
    db.commit()
    return db_task

def create_opportunity_feedback(db: Session, feedback: schemas.TaskFeedbackCreate, opportunity_id: str, user_id: int):
    # Convert string UUID to UUID object
    uuid_opportunity_id = uuid.UUID(opportunity_id)
    
    db_feedback = TaskFeedback(
        **feedback.model_dump(),
        opportunity_id=uuid_opportunity_id,
        user_id=user_id
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback