"""
User History Router
API endpoints for user history summarization
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from shared.database.models import User, UserHistorySummary
from shared.services.user_history_summarization_service import user_history_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary")
async def get_user_history_summary(
    period: str = "all_time",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's history summary for specified period.
    """
    try:
        valid_periods = ["weekly", "monthly", "quarterly", "all_time"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        summary = await user_history_service.get_user_summary(db, current_user.id, period)
        
        if not summary:
            return {
                "message": "No history data available for this period",
                "period": period,
                "user_id": current_user.id,
                "has_summary": False
            }
        
        return {
            "summary": {
                "id": str(summary.id),
                "period": summary.summary_period,
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "total_sessions": summary.total_sessions,
                "total_messages": summary.total_messages,
                "total_tokens_used": summary.total_tokens_used,
                "executive_summary": summary.executive_summary,
                "primary_domains": summary.primary_domains,
                "frequent_topics": summary.frequent_topics,
                "key_preferences": summary.key_preferences,
                "skill_areas": summary.skill_areas,
                "preferred_tools": summary.preferred_tools,
                "interaction_patterns": summary.interaction_patterns,
                "complexity_preference": summary.complexity_preference,
                "important_context": summary.important_context,
                "recurring_themes": summary.recurring_themes,
                "engagement_score": summary.engagement_score,
                "satisfaction_indicators": summary.satisfaction_indicators,
                "created_at": summary.created_at.isoformat(),
                "updated_at": summary.updated_at.isoformat(),
                "version": summary.version
            },
            "has_summary": True
        }
        
    except Exception as e:
        logger.error(f"Error getting user history summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user history summary"
        )


@router.post("/summary/generate")
async def generate_user_history_summary(
    background_tasks: BackgroundTasks,
    period: str = "all_time",
    force_regenerate: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate or regenerate user's history summary.
    """
    try:
        valid_periods = ["weekly", "monthly", "quarterly", "all_time"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Start background task for summary generation
        def generate_summary_task():
            try:
                import asyncio
                asyncio.run(user_history_service.generate_user_summary(
                    db, current_user.id, period, force_regenerate
                ))
            except Exception as e:
                logger.error(f"Background summary generation failed: {e}")
        
        background_tasks.add_task(generate_summary_task)
        
        return {
            "message": "Summary generation started",
            "period": period,
            "user_id": current_user.id,
            "force_regenerate": force_regenerate,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error starting summary generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to start summary generation"
        )


@router.get("/summary/status")
async def get_summary_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get status of user's history summaries.
    """
    try:
        summaries = db.query(UserHistorySummary).filter(
            UserHistorySummary.user_id == current_user.id
        ).all()
        
        summary_status = {}
        for summary in summaries:
            summary_status[summary.summary_period] = {
                "exists": True,
                "last_updated": summary.updated_at.isoformat(),
                "version": summary.version,
                "total_sessions": summary.total_sessions,
                "total_messages": summary.total_messages
            }
        
        # Check for missing periods
        all_periods = ["weekly", "monthly", "quarterly", "all_time"]
        for period in all_periods:
            if period not in summary_status:
                summary_status[period] = {
                    "exists": False,
                    "last_updated": None,
                    "version": 0,
                    "total_sessions": 0,
                    "total_messages": 0
                }
        
        return {
            "user_id": current_user.id,
            "summaries": summary_status,
            "has_any_summary": len(summaries) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting summary status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get summary status"
        )


@router.get("/loading-context")
async def get_loading_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get loading context for chat initialization.
    This endpoint is called when starting a new chat session.
    """
    try:
        # Get the most recent all_time summary
        summary = await user_history_service.get_user_summary(db, current_user.id, "all_time")
        
        if not summary:
            return {
                "has_context": False,
                "message": "Building your user profile...",
                "is_new_user": True
            }
        
        # Extract key context for chat initialization
        loading_context = {
            "has_context": True,
            "executive_summary": summary.executive_summary,
            "primary_domains": summary.primary_domains[:3],  # Top 3
            "frequent_topics": summary.frequent_topics[:5],  # Top 5
            "preferred_tools": summary.preferred_tools[:3],  # Top 3
            "complexity_preference": summary.complexity_preference,
            "important_context": summary.important_context,
            "interaction_patterns": summary.interaction_patterns,
            "last_updated": summary.updated_at.isoformat(),
            "total_sessions": summary.total_sessions,
            "is_new_user": summary.total_sessions < 5
        }
        
        return loading_context
        
    except Exception as e:
        logger.error(f"Error getting loading context: {e}", exc_info=True)
        # Return fallback context
        return {
            "has_context": False,
            "message": "Preparing your personalized experience...",
            "is_new_user": True
        }