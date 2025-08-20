"""
Mission Suggestions API Router
Provides endpoints for generating and retrieving mission-aligned suggestions.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from shared.utils.database_setup import get_db
from shared.database.models import User
from api.dependencies import get_current_user
try:
    from worker.services.mission_suggestions_service import mission_suggestions_service
except ImportError:
    # Fallback when worker services are not available in API container
    mission_suggestions_service = None
try:
    from worker.tasks import execute_mission_suggestions_task
except ImportError:
    # Fallback when worker tasks are not available in API container
    execute_mission_suggestions_task = None

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def generate_mission_suggestions(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate proactive mission-aligned suggestions for the current user.
    This endpoint is typically called on login if user has a mission statement.
    """
    try:
        # Check if worker services are available
        if mission_suggestions_service is None or execute_mission_suggestions_task is None:
            return {
                "success": False,
                "message": "Mission suggestions service is not available. Please ensure the worker service is running.",
                "suggestions": []
            }
        
        # Check if user has a mission statement
        if not current_user.mission_statement:
            return {
                "success": False,
                "message": "No mission statement found. Complete your mission interview first.",
                "suggestions": []
            }
        
        # Generate session ID for tracking
        import uuid
        session_id = str(uuid.uuid4())
        
        # Queue background task to generate suggestions
        background_tasks.add_task(
            execute_mission_suggestions_task,
            user_id=current_user.id,
            session_id=session_id
        )
        
        return {
            "success": True,
            "message": "Mission suggestions are being generated in the background.",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error generating mission suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating mission suggestions")


@router.get("/recent")
async def get_recent_suggestions(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent mission suggestions for the current user.
    """
    try:
        if mission_suggestions_service is None:
            return {
                "success": False,
                "message": "Mission suggestions service is not available. Please ensure the worker service is running.",
                "suggestions": []
            }
        
        suggestions = await mission_suggestions_service.get_recent_suggestions(
            current_user.id, limit
        )
        
        return {
            "success": True,
            "suggestions": suggestions,
            "total": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Error getting recent suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving suggestions")


@router.get("/current")
async def get_current_suggestions(
    current_user: User = Depends(get_current_user)
):
    """
    Get the most recent mission suggestions for the current user.
    """
    try:
        if mission_suggestions_service is None:
            return {
                "success": False,
                "message": "Mission suggestions service is not available. Please ensure the worker service is running.",
                "suggestions": []
            }
        
        suggestions = await mission_suggestions_service.get_recent_suggestions(
            current_user.id, 1
        )
        
        if not suggestions:
            return {
                "success": True,
                "message": "No recent suggestions found",
                "suggestions": []
            }
        
        return {
            "success": True,
            "suggestions": suggestions[0]["suggestions"],
            "generated_at": suggestions[0]["created_at"]
        }
        
    except Exception as e:
        logger.error(f"Error getting current suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving current suggestions")


@router.post("/immediate")
async def generate_immediate_suggestions(
    current_user: User = Depends(get_current_user)
):
    """
    Generate mission suggestions immediately (synchronous).
    Use this for testing or when immediate results are needed.
    """
    try:
        if mission_suggestions_service is None:
            return {
                "success": False,
                "message": "Mission suggestions service is not available. Please ensure the worker service is running.",
                "suggestions": []
            }
        
        # Check if user has a mission statement
        if not current_user.mission_statement:
            return {
                "success": False,
                "message": "No mission statement found. Complete your mission interview first.",
                "suggestions": []
            }
        
        # Generate session ID for tracking
        import uuid
        session_id = str(uuid.uuid4())
        
        # Generate suggestions immediately
        suggestions, token_metrics = await mission_suggestions_service.generate_mission_suggestions(
            current_user.id, session_id
        )
        
        return {
            "success": True,
            "message": "Mission suggestions generated successfully",
            "suggestions": suggestions,
            "token_usage": {
                "input_tokens": token_metrics.input_tokens,
                "output_tokens": token_metrics.output_tokens,
                "total_tokens": token_metrics.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating immediate suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error generating immediate suggestions")


@router.get("/check-eligibility")
async def check_mission_suggestions_eligibility(
    current_user: User = Depends(get_current_user)
):
    """
    Check if the user is eligible for mission suggestions.
    """
    try:
        has_mission = bool(current_user.mission_statement)
        has_goals = bool(current_user.personal_goals)
        
        return {
            "eligible": has_mission,
            "has_mission_statement": has_mission,
            "has_personal_goals": has_goals,
            "mission_statement": current_user.mission_statement if has_mission else None,
            "message": "Ready for mission suggestions" if has_mission else "Complete your mission interview to receive personalized suggestions"
        }
        
    except Exception as e:
        logger.error(f"Error checking eligibility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error checking eligibility")


@router.post("/mark-actioned/{suggestion_id}")
async def mark_suggestion_actioned(
    suggestion_id: str,
    action_taken: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a suggestion as actioned by the user.
    This helps track engagement and improve future suggestions.
    """
    try:
        # For now, just log the action
        # In a full implementation, you might want to store this in the database
        logger.info(f"User {current_user.id} actioned suggestion {suggestion_id}: {action_taken}")
        
        return {
            "success": True,
            "message": "Suggestion marked as actioned",
            "suggestion_id": suggestion_id,
            "action_taken": action_taken
        }
        
    except Exception as e:
        logger.error(f"Error marking suggestion as actioned: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error marking suggestion as actioned")