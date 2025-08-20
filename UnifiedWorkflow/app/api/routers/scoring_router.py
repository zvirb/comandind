"""
Weighted Scoring Router - API endpoints for intelligent task/event scoring and recommendations
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User
from shared.services.weighted_scoring_service import WeightedScoringService
from shared.schemas.base import GenericResponse
from shared.schemas.semantic_schemas import (
    WeightedScoreRequest,
    WeightedScoreResponse,
    WeightedScoreResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


@router.post("/task/{task_id}", response_model=GenericResponse)
async def calculate_task_score(
    task_id: UUID,
    custom_weights: Optional[Dict[str, float]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Calculate weighted score for a specific task.
    
    Args:
        task_id: Task ID
        custom_weights: Optional custom scoring weights
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Task weighted score and breakdown
    """
    try:
        score_result = WeightedScoringService.calculate_task_weighted_score(
            db=db,
            task_id=str(task_id),
            user_id=current_user.id,
            custom_weights=custom_weights
        )
        
        if score_result['weighted_score'] == 0 and not score_result['score_breakdown']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or scoring failed"
            )
        
        logger.info(f"Calculated score for task {task_id}: {score_result['weighted_score']:.3f}")
        
        return GenericResponse(
            success=True,
            message=f"Task {task_id} score calculated successfully",
            data=score_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating task score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate task score"
        )


@router.post("/event/{event_id}", response_model=GenericResponse)
async def calculate_event_score(
    event_id: UUID,
    custom_weights: Optional[Dict[str, float]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Calculate weighted score for a specific event.
    
    Args:
        event_id: Event ID
        custom_weights: Optional custom scoring weights
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Event weighted score and breakdown
    """
    try:
        score_result = WeightedScoringService.calculate_event_weighted_score(
            db=db,
            event_id=str(event_id),
            user_id=current_user.id,
            custom_weights=custom_weights
        )
        
        if score_result['weighted_score'] == 0 and not score_result['score_breakdown']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found or scoring failed"
            )
        
        logger.info(f"Calculated score for event {event_id}: {score_result['weighted_score']:.3f}")
        
        return GenericResponse(
            success=True,
            message=f"Event {event_id} score calculated successfully",
            data=score_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating event score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate event score"
        )


@router.get("/tasks/ranked", response_model=GenericResponse)
async def get_ranked_tasks(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of tasks"),
    include_completed: bool = Query(False, description="Include completed tasks"),
    custom_weights: Optional[str] = Query(None, description="JSON string of custom weights"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Get user's tasks ranked by weighted score.
    
    Args:
        limit: Maximum number of tasks to return
        include_completed: Whether to include completed tasks
        custom_weights: Optional JSON string of custom weights
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Ranked list of tasks with scores
    """
    try:
        # Parse custom weights if provided
        weights = None
        if custom_weights:
            import json
            try:
                weights = json.loads(custom_weights)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format for custom_weights"
                )
        
        ranked_tasks = WeightedScoringService.rank_tasks_by_score(
            db=db,
            user_id=current_user.id,
            limit=limit,
            custom_weights=weights,
            filter_completed=not include_completed
        )
        
        logger.info(f"Retrieved {len(ranked_tasks)} ranked tasks for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message=f"Retrieved {len(ranked_tasks)} ranked tasks",
            data={
                "tasks": ranked_tasks,
                "total_count": len(ranked_tasks),
                "weights_used": weights or WeightedScoringService.DEFAULT_TASK_WEIGHTS
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ranked tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ranked tasks"
        )


@router.get("/recommendations/{recommendation_type}", response_model=GenericResponse)
async def get_task_recommendations(
    recommendation_type: str,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Get personalized task recommendations.
    
    Args:
        recommendation_type: Type of recommendation ('next_actions', 'quick_wins', 'important')
        limit: Maximum number of recommendations
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Personalized task recommendations
    """
    try:
        valid_types = ['next_actions', 'quick_wins', 'important']
        if recommendation_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid recommendation type. Must be one of: {', '.join(valid_types)}"
            )
        
        recommendations = WeightedScoringService.get_recommended_tasks(
            db=db,
            user_id=current_user.id,
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        logger.info(f"Generated {len(recommendations)} {recommendation_type} recommendations for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message=f"Generated {len(recommendations)} {recommendation_type} recommendations",
            data={
                "recommendations": recommendations,
                "recommendation_type": recommendation_type,
                "count": len(recommendations)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task recommendations"
        )


@router.get("/weights/defaults", response_model=GenericResponse)
async def get_default_weights() -> GenericResponse:
    """
    Get default scoring weights for tasks and events.
    
    Returns:
        Default weights configuration
    """
    try:
        weights_data = {
            "task_weights": WeightedScoringService.DEFAULT_TASK_WEIGHTS,
            "event_weights": WeightedScoringService.DEFAULT_EVENT_WEIGHTS,
            "category_priorities": WeightedScoringService.CATEGORY_PRIORITIES,
            "priority_multipliers": WeightedScoringService.PRIORITY_MULTIPLIERS,
            "complexity_adjustments": WeightedScoringService.COMPLEXITY_ADJUSTMENTS
        }
        
        return GenericResponse(
            success=True,
            message="Default weights retrieved successfully",
            data=weights_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving default weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default weights"
        )


@router.post("/batch/tasks", response_model=GenericResponse)
async def batch_score_tasks(
    task_ids: List[UUID] = Body(..., min_items=1, max_items=50),
    custom_weights: Optional[Dict[str, float]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Calculate weighted scores for multiple tasks in batch.
    
    Args:
        task_ids: List of task IDs to score
        custom_weights: Optional custom scoring weights
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Batch scoring results
    """
    try:
        results = []
        errors = []
        
        for task_id in task_ids:
            try:
                score_result = WeightedScoringService.calculate_task_weighted_score(
                    db=db,
                    task_id=str(task_id),
                    user_id=current_user.id,
                    custom_weights=custom_weights
                )
                
                if score_result['weighted_score'] > 0 or score_result['score_breakdown']:
                    results.append({
                        "task_id": str(task_id),
                        "score_data": score_result
                    })
                else:
                    errors.append({
                        "task_id": str(task_id),
                        "error": "Task not found or scoring failed"
                    })
                    
            except Exception as e:
                logger.error(f"Error scoring task {task_id}: {e}")
                errors.append({
                    "task_id": str(task_id),
                    "error": str(e)
                })
        
        # Sort results by score descending
        results.sort(key=lambda x: x['score_data']['weighted_score'], reverse=True)
        
        # Add rankings
        for i, result in enumerate(results):
            result['ranking'] = i + 1
        
        logger.info(f"Batch scored {len(results)} tasks with {len(errors)} errors for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message=f"Batch scored {len(results)} tasks with {len(errors)} errors",
            data={
                "results": results,
                "errors": errors,
                "total_requested": len(task_ids),
                "successful": len(results),
                "failed": len(errors)
            }
        )
        
    except Exception as e:
        logger.error(f"Error in batch task scoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform batch task scoring"
        )


@router.get("/insights/scoring", response_model=GenericResponse)
async def get_scoring_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> GenericResponse:
    """
    Get insights about user's scoring patterns and preferences.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Scoring insights and analytics
    """
    try:
        from shared.database.models import Task, TaskStatus
        from sqlalchemy import func
        
        # Get basic task statistics
        total_tasks = db.query(Task).filter(Task.user_id == current_user.id).count()
        completed_tasks = db.query(Task).filter(
            Task.user_id == current_user.id,
            Task.status == TaskStatus.COMPLETED
        ).count()
        
        # Get category distribution
        category_dist = db.query(
            Task.semantic_category,
            func.count(Task.id).label('count')
        ).filter(
            Task.user_id == current_user.id,
            Task.semantic_category.isnot(None)
        ).group_by(Task.semantic_category).all()
        
        category_distribution = {cat: count for cat, count in category_dist}
        
        # Get priority distribution
        priority_dist = db.query(
            Task.priority,
            func.count(Task.id).label('count')
        ).filter(
            Task.user_id == current_user.id,
            Task.priority.isnot(None)
        ).group_by(Task.priority).all()
        
        priority_distribution = {str(pri): count for pri, count in priority_dist}
        
        # Calculate completion rate by category
        completion_rates = {}
        for category, _ in category_dist:
            total_in_cat = db.query(Task).filter(
                Task.user_id == current_user.id,
                Task.semantic_category == category
            ).count()
            
            completed_in_cat = db.query(Task).filter(
                Task.user_id == current_user.id,
                Task.semantic_category == category,
                Task.status == TaskStatus.COMPLETED
            ).count()
            
            if total_in_cat > 0:
                completion_rates[category] = completed_in_cat / total_in_cat
        
        insights_data = {
            "task_statistics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
            },
            "category_distribution": category_distribution,
            "priority_distribution": priority_distribution,
            "completion_rates_by_category": completion_rates,
            "most_productive_category": max(completion_rates.items(), key=lambda x: x[1])[0] if completion_rates else None,
            "recommendations": []
        }
        
        # Generate personalized recommendations
        if completion_rates:
            best_category = max(completion_rates.items(), key=lambda x: x[1])
            worst_category = min(completion_rates.items(), key=lambda x: x[1])
            
            insights_data["recommendations"].extend([
                f"You complete {best_category[0]} tasks at a {best_category[1]:.1%} rate - consider scheduling more of these!",
                f"Focus on improving {worst_category[0]} tasks (current: {worst_category[1]:.1%} completion rate)"
            ])
        
        if total_tasks < 10:
            insights_data["recommendations"].append("Add more tasks to get better scoring insights and recommendations")
        
        logger.info(f"Generated scoring insights for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message="Scoring insights retrieved successfully",
            data=insights_data
        )
        
    except Exception as e:
        logger.error(f"Error getting scoring insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get scoring insights"
        )