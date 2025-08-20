"""
Task management tools for productivity workflows.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress" 
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

def create_task(title: str, description: str = "", priority: str = "medium", 
               due_date: Optional[str] = None, tags: List[str] = None) -> Dict[str, Any]:
    """
    Create a new task.
    
    Args:
        title: Task title
        description: Task description
        priority: Task priority (low, medium, high, urgent)
        due_date: Due date in ISO format
        tags: List of tags for categorization
    
    Returns:
        Dictionary containing task creation details
    """
    try:
        task_id = f"task_{int(datetime.now().timestamp())}"
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": TaskStatus.TODO.value,
            "created_at": datetime.now().isoformat(),
            "due_date": due_date,
            "tags": tags or [],
            "estimated_time": None,
            "actual_time": None
        }
        
        logger.info(f"Task created: {task_id} - {title}")
        return {
            "success": True,
            "message": f"Task '{title}' created successfully",
            "task": task
        }
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return {
            "success": False,
            "message": f"Failed to create task: {str(e)}"
        }

def update_task_status(task_id: str, status: str, notes: str = "") -> Dict[str, Any]:
    """
    Update the status of a task.
    
    Args:
        task_id: Task identifier
        status: New status (todo, in_progress, blocked, completed, cancelled)
        notes: Optional notes about the status change
    
    Returns:
        Dictionary containing update confirmation
    """
    try:
        update_data = {
            "task_id": task_id,
            "old_status": "todo",  # In real implementation, fetch from database
            "new_status": status,
            "updated_at": datetime.now().isoformat(),
            "notes": notes
        }
        
        # If completing task, record completion time
        if status == TaskStatus.COMPLETED.value:
            update_data["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} status updated to {status}")
        return {
            "success": True,
            "message": f"Task status updated to {status}",
            "update_data": update_data
        }
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        return {
            "success": False,
            "message": f"Failed to update task status: {str(e)}"
        }

def get_task_list(status_filter: Optional[str] = None, priority_filter: Optional[str] = None,
                  tag_filter: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """
    Get a filtered list of tasks.
    
    Args:
        status_filter: Filter by task status
        priority_filter: Filter by priority level
        tag_filter: Filter by specific tag
        limit: Maximum number of tasks to return
    
    Returns:
        Dictionary containing filtered task list
    """
    try:
        # In a real implementation, this would query the database
        sample_tasks = [
            {
                "id": "task_1",
                "title": "Complete project documentation",
                "priority": "high",
                "status": "in_progress",
                "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
                "tags": ["documentation", "project"]
            },
            {
                "id": "task_2", 
                "title": "Review pull requests",
                "priority": "medium",
                "status": "todo",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "tags": ["code-review", "development"]
            },
            {
                "id": "task_3",
                "title": "Update dependencies",
                "priority": "low",
                "status": "todo",
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "tags": ["maintenance", "development"]
            }
        ]
        
        # Apply filters
        filtered_tasks = sample_tasks
        if status_filter:
            filtered_tasks = [t for t in filtered_tasks if t["status"] == status_filter]
        if priority_filter:
            filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority_filter]
        if tag_filter:
            filtered_tasks = [t for t in filtered_tasks if tag_filter in t["tags"]]
        
        # Apply limit
        filtered_tasks = filtered_tasks[:limit]
        
        return {
            "success": True,
            "tasks": filtered_tasks,
            "count": len(filtered_tasks),
            "filters_applied": {
                "status": status_filter,
                "priority": priority_filter,
                "tag": tag_filter
            }
        }
    except Exception as e:
        logger.error(f"Error getting task list: {e}")
        return {
            "success": False,
            "message": f"Failed to get task list: {str(e)}"
        }

def prioritize_tasks(task_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Automatically prioritize tasks based on due dates, priority levels, and dependencies.
    
    Args:
        task_list: List of task dictionaries
    
    Returns:
        Dictionary containing prioritized task list
    """
    try:
        prioritized_tasks = []
        
        for task in task_list:
            score = 0
            
            # Priority level scoring
            priority_scores = {
                "urgent": 100,
                "high": 75,
                "medium": 50,
                "low": 25
            }
            score += priority_scores.get(task.get("priority", "medium"), 50)
            
            # Due date scoring (closer due dates get higher scores)
            if task.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(task["due_date"].replace('Z', '+00:00'))
                    days_until_due = (due_date - datetime.now()).days
                    if days_until_due < 0:  # Overdue
                        score += 200
                    elif days_until_due <= 1:  # Due today/tomorrow
                        score += 150
                    elif days_until_due <= 3:  # Due within 3 days
                        score += 100
                    elif days_until_due <= 7:  # Due within a week
                        score += 50
                except:
                    pass  # Invalid date format
            
            # Status scoring (in_progress tasks get slight priority)
            if task.get("status") == "in_progress":
                score += 25
            
            task_with_score = {**task, "priority_score": score}
            prioritized_tasks.append(task_with_score)
        
        # Sort by priority score
        prioritized_tasks.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return {
            "success": True,
            "prioritized_tasks": prioritized_tasks,
            "count": len(prioritized_tasks)
        }
    except Exception as e:
        logger.error(f"Error prioritizing tasks: {e}")
        return {
            "success": False,
            "message": f"Failed to prioritize tasks: {str(e)}"
        }

def get_task_analytics() -> Dict[str, Any]:
    """
    Get task analytics and productivity metrics.
    
    Returns:
        Dictionary containing task analytics
    """
    analytics = {
        "overview": {
            "total_tasks": 15,
            "completed_today": 3,
            "in_progress": 4,
            "overdue": 1,
            "completion_rate": 0.78
        },
        "by_priority": {
            "urgent": {"total": 2, "completed": 1},
            "high": {"total": 5, "completed": 3},
            "medium": {"total": 6, "completed": 4},
            "low": {"total": 2, "completed": 2}
        },
        "productivity_trends": {
            "avg_completion_time": "2.5 days",
            "most_productive_day": "Tuesday",
            "common_delay_reasons": ["blocked by dependencies", "scope creep"]
        },
        "upcoming_deadlines": [
            {"title": "Project review", "due_date": "2025-07-23", "priority": "high"},
            {"title": "Documentation update", "due_date": "2025-07-24", "priority": "medium"}
        ]
    }
    
    return {
        "success": True,
        "analytics": analytics,
        "generated_at": datetime.now().isoformat()
    }

def create_task_template(name: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a reusable task template for common workflows.
    
    Args:
        name: Template name
        tasks: List of task dictionaries that make up the template
    
    Returns:
        Dictionary containing template creation confirmation
    """
    try:
        template = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "tasks": tasks,
            "task_count": len(tasks)
        }
        
        logger.info(f"Task template '{name}' created with {len(tasks)} tasks")
        return {
            "success": True,
            "message": f"Task template '{name}' created successfully",
            "template": template
        }
    except Exception as e:
        logger.error(f"Error creating task template: {e}")
        return {
            "success": False,
            "message": f"Failed to create task template: {str(e)}"
        }

def estimate_task_completion(task_id: str, similar_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate task completion time based on similar completed tasks.
    
    Args:
        task_id: Task identifier
        similar_tasks: List of similar completed tasks for reference
    
    Returns:
        Dictionary containing time estimation
    """
    try:
        if not similar_tasks:
            return {
                "success": True,
                "estimation": "No similar tasks found for reference",
                "estimated_hours": None
            }
        
        # Calculate average completion time from similar tasks
        total_hours = 0
        count = 0
        
        for task in similar_tasks:
            if task.get("actual_time"):
                total_hours += task["actual_time"]
                count += 1
        
        if count == 0:
            estimated_hours = 4  # Default estimate
        else:
            estimated_hours = total_hours / count
        
        # Add buffer for uncertainty
        estimated_hours_with_buffer = estimated_hours * 1.2
        
        return {
            "success": True,
            "task_id": task_id,
            "estimated_hours": round(estimated_hours_with_buffer, 1),
            "base_estimate": round(estimated_hours, 1),
            "confidence": "medium" if count >= 3 else "low",
            "reference_tasks_count": count
        }
    except Exception as e:
        logger.error(f"Error estimating task completion: {e}")
        return {
            "success": False,
            "message": f"Failed to estimate task completion: {str(e)}"
        }