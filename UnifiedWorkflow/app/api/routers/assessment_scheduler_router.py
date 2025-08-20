# api/routers/assessment_scheduler_router.py
"""
API router for managing scheduled assessments.
Provides endpoints to configure and monitor background assessment tasks.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_current_user
from shared.database.models import User
from worker.services.scheduled_assessment_service import (
    scheduled_assessment_service, 
    AssessmentType, 
    AssessmentSchedule,
    AssessmentResult
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ScheduleConfigRequest(BaseModel):
    assessment_type: str
    frequency_hours: int
    enabled: bool = True


class ScheduleUpdateRequest(BaseModel):
    frequency_hours: Optional[int] = None
    enabled: Optional[bool] = None


class AssessmentResultResponse(BaseModel):
    assessment_type: str
    timestamp: str
    confidence_score: float
    insights: List[str]
    recommendations: List[str]
    results: dict


class ScheduleResponse(BaseModel):
    assessment_type: str
    frequency_hours: int
    enabled: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None


@router.post("/initialize")
async def initialize_user_assessments(
    current_user: User = Depends(get_current_user)
):
    """
    Initialize default assessment schedules for a new user.
    """
    try:
        # Get default schedules
        default_configs = scheduled_assessment_service.get_default_schedules()
        
        # Add schedules for the user
        scheduled_assessment_service.add_user_schedule(current_user.id, default_configs)
        
        return {
            "message": "Assessment schedules initialized",
            "schedules_added": len(default_configs),
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error initializing assessments for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize assessments: {str(e)}")


@router.get("/schedules")
async def get_user_schedules(
    current_user: User = Depends(get_current_user)
) -> List[ScheduleResponse]:
    """
    Get current assessment schedules for the user.
    """
    try:
        schedules = scheduled_assessment_service.get_user_schedules(current_user.id)
        
        return [
            ScheduleResponse(
                assessment_type=schedule.assessment_type.value,
                frequency_hours=schedule.frequency_hours,
                enabled=schedule.enabled,
                last_run=schedule.last_run.isoformat() if schedule.last_run else None,
                next_run=schedule.next_run.isoformat() if schedule.next_run else None
            )
            for schedule in schedules
        ]
        
    except Exception as e:
        logger.error(f"Error getting schedules for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedules: {str(e)}")


@router.put("/schedules/{assessment_type}")
async def update_schedule(
    assessment_type: str,
    request: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update a specific assessment schedule.
    """
    try:
        # Validate assessment type
        try:
            assessment_enum = AssessmentType(assessment_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid assessment type: {assessment_type}")
        
        # Prepare updates
        updates = {}
        if request.frequency_hours is not None:
            updates["frequency_hours"] = request.frequency_hours
        if request.enabled is not None:
            updates["enabled"] = request.enabled
        
        # Update schedule
        success = scheduled_assessment_service.update_schedule(
            current_user.id, 
            assessment_enum, 
            **updates
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Assessment schedule not found")
        
        return {
            "message": "Schedule updated successfully",
            "assessment_type": assessment_type,
            "updates": updates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.get("/results")
async def get_assessment_results(
    assessment_type: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[AssessmentResultResponse]:
    """
    Get recent assessment results for the user.
    """
    try:
        # Convert assessment type if provided
        assessment_enum = None
        if assessment_type:
            try:
                assessment_enum = AssessmentType(assessment_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid assessment type: {assessment_type}")
        
        # Get results
        results = scheduled_assessment_service.get_user_assessment_results(
            current_user.id, 
            assessment_enum, 
            limit
        )
        
        return [
            AssessmentResultResponse(
                assessment_type=result.assessment_type.value,
                timestamp=result.timestamp.isoformat(),
                confidence_score=result.confidence_score,
                insights=result.insights,
                recommendations=result.recommendations,
                results=result.results
            )
            for result in results
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assessment results for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get assessment results: {str(e)}")


@router.post("/run/{assessment_type}")
async def run_assessment_now(
    assessment_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger an assessment to run immediately.
    """
    try:
        # Validate assessment type
        try:
            assessment_enum = AssessmentType(assessment_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid assessment type: {assessment_type}")
        
        # Run assessment immediately
        result = await scheduled_assessment_service._run_assessment(current_user.id, assessment_enum)
        
        if result:
            # Store result in cache
            if current_user.id not in scheduled_assessment_service.results_cache:
                scheduled_assessment_service.results_cache[current_user.id] = []
            scheduled_assessment_service.results_cache[current_user.id].append(result)
            
            return {
                "message": "Assessment completed successfully",
                "assessment_type": assessment_type,
                "timestamp": result.timestamp.isoformat(),
                "confidence_score": result.confidence_score,
                "insights_count": len(result.insights),
                "recommendations_count": len(result.recommendations)
            }
        else:
            return {
                "message": "Assessment completed but no results generated",
                "assessment_type": assessment_type
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running assessment {assessment_type} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run assessment: {str(e)}")


@router.get("/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get status of the assessment scheduler and user's assessment activity.
    """
    try:
        user_schedules = scheduled_assessment_service.get_user_schedules(current_user.id)
        user_results = scheduled_assessment_service.get_user_assessment_results(current_user.id, limit=50)
        
        # Calculate stats
        enabled_schedules = sum(1 for s in user_schedules if s.enabled)
        total_assessments = len(user_results)
        recent_assessments = len([r for r in user_results if (datetime.now() - r.timestamp).days <= 7])
        
        return {
            "scheduler_running": scheduled_assessment_service.running,
            "user_stats": {
                "total_schedules": len(user_schedules),
                "enabled_schedules": enabled_schedules,
                "total_assessments_completed": total_assessments,
                "assessments_last_7_days": recent_assessments,
                "last_assessment": user_results[0].timestamp.isoformat() if user_results else None
            },
            "available_assessment_types": [at.value for at in AssessmentType]
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/start-scheduler")
async def start_scheduler(
    current_user: User = Depends(get_current_user)
):
    """
    Start the assessment scheduler (admin function).
    """
    try:
        if not scheduled_assessment_service.running:
            await scheduled_assessment_service.start_scheduler()
            return {"message": "Assessment scheduler started"}
        else:
            return {"message": "Assessment scheduler already running"}
            
    except Exception as e:
        logger.error(f"Error starting assessment scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/stop-scheduler")
async def stop_scheduler(
    current_user: User = Depends(get_current_user)
):
    """
    Stop the assessment scheduler (admin function).
    """
    try:
        if scheduled_assessment_service.running:
            await scheduled_assessment_service.stop_scheduler()
            return {"message": "Assessment scheduler stopped"}
        else:
            return {"message": "Assessment scheduler not running"}
            
    except Exception as e:
        logger.error(f"Error stopping assessment scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")