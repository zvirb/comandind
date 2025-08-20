"""
Semantic Analysis Router - API endpoints for semantic task/event analysis
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User
from shared.services.semantic_analysis_service import SemanticAnalysisService
from shared.schemas.base import GenericResponse
from shared.schemas.semantic_schemas import (
    TaskSemanticAnalysisRequest,
    EventSemanticAnalysisRequest,
    SemanticAnalysisResult,
    SemanticUpdateRequest,
    BulkAnalysisResult,
    SemanticCategoriesResponse,
    SemanticInsightsListResponse,
    UnstructuredAnalysisRequest,
)
from worker.tools.unstructured_data_tool import run_unstructured_data_tool


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic"])


async def classify_user_intent(user_input: str) -> str:
    """
    Classify the user's intent as either SIMPLE_DATA_EXTRACTION or COMPLEX_PLANNING_REQUEST.
    """
    # For now, we'll use a simple keyword-based classification.
    # In the future, this could be replaced with a more sophisticated model.
    if "extract" in user_input.lower() or "get" in user_input.lower():
        return "SIMPLE_DATA_EXTRACTION"
    else:
        return "COMPLEX_PLANNING_REQUEST"


@router.post("/analyze/unstructured", response_model=GenericResponse)
async def analyze_unstructured_data(
    request: UnstructuredAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Analyze unstructured data using the appropriate tool based on intent.
    """
    try:
        intent = await classify_user_intent(request.user_input)

        if intent == "SIMPLE_DATA_EXTRACTION":
            logger.info("Intent: Simple Data Extraction. Routing to UnstructuredDataTool.")
            result = await run_unstructured_data_tool(request.user_input, request.context)
            return GenericResponse(
                success=True,
                message="Unstructured data analysis completed successfully",
                data={"result": result},
            )
        else:
            logger.info("Intent: Complex Planning. Routing to PlannerAgent.")
            # The user did not provide a planner agent, so we will just return a message for now.
            return GenericResponse(
                success=True,
                message="Complex planning request received. No planner agent available.",
                data={},
            )

    except Exception as e:
        logger.error(f"Error analyzing unstructured data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze unstructured data",
        )


@router.post("/analyze/task", response_model=GenericResponse)
async def analyze_task_semantics(
    request: TaskSemanticAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Analyze semantic meaning of a task.
    
    Args:
        request: Task analysis request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Semantic analysis results
    """
    try:
        # Extract user profile for personalization
        user_profile = SemanticAnalysisService._extract_user_profile(current_user)
        
        # Perform semantic analysis
        analysis = SemanticAnalysisService.analyze_task_semantics(
            task_text=request.task_text,
            task_description=request.task_description,
            user_profile=user_profile,
        )
        
        logger.info(f"Task semantic analysis completed for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message="Task semantic analysis completed successfully",
            data=analysis,
        )
        
    except Exception as e:
        logger.error(f"Error analyzing task semantics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze task semantics",
        )


@router.post("/analyze/event", response_model=GenericResponse)
async def analyze_event_semantics(
    request: EventSemanticAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Analyze semantic meaning of an event.
    
    Args:
        request: Event analysis request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Semantic analysis results
    """
    try:
        # Extract user profile for personalization
        user_profile = SemanticAnalysisService._extract_user_profile(current_user)
        
        # Perform semantic analysis
        analysis = SemanticAnalysisService.analyze_event_semantics(
            event_title=request.event_title,
            event_description=request.event_description,
            event_location=request.event_location,
            user_profile=user_profile,
        )
        
        logger.info(f"Event semantic analysis completed for user {current_user.id}")
        
        return GenericResponse(
            success=True,
            message="Event semantic analysis completed successfully",
            data=analysis,
        )
        
    except Exception as e:
        logger.error(f"Error analyzing event semantics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze event semantics",
        )


@router.post("/update/task/{task_id}", response_model=GenericResponse)
async def update_task_semantic_fields(
    task_id: UUID,
    request: SemanticUpdateRequest = Body(default_factory=SemanticUpdateRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Update semantic fields for a specific task.
    
    Args:
        task_id: Task ID
        request: Update request with options
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Update status
    """
    try:
        success = SemanticAnalysisService.update_task_semantic_fields(
            db=db,
            task_id=str(task_id),
            user_id=current_user.id,
            force_update=request.force_update,
        )
        
        if success:
            logger.info(f"Updated semantic fields for task {task_id}")
            return GenericResponse(
                success=True,
                message=f"Task {task_id} semantic fields updated successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or update failed",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task semantic fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task semantic fields",
        )


@router.post("/update/event/{event_id}", response_model=GenericResponse)
async def update_event_semantic_fields(
    event_id: UUID,
    request: SemanticUpdateRequest = Body(default_factory=SemanticUpdateRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Update semantic fields for a specific event.
    
    Args:
        event_id: Event ID
        request: Update request with options
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Update status
    """
    try:
        success = SemanticAnalysisService.update_event_semantic_fields(
            db=db,
            event_id=str(event_id),
            user_id=current_user.id,
            force_update=request.force_update,
        )
        
        if success:
            logger.info(f"Updated semantic fields for event {event_id}")
            return GenericResponse(
                success=True,
                message=f"Event {event_id} semantic fields updated successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found or update failed",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event semantic fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event semantic fields",
        )


@router.post("/bulk/analyze", response_model=GenericResponse)
async def bulk_analyze_user_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Perform bulk semantic analysis for all user's tasks and events.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Analysis statistics
    """
    try:
        stats = SemanticAnalysisService.bulk_analyze_user_content(
            db=db, user_id=current_user.id
        )
        
        logger.info(f"Bulk semantic analysis completed for user {current_user.id}: {stats}")
        
        return GenericResponse(
            success=True,
            message="Bulk semantic analysis completed successfully",
            data=stats,
        )
        
    except Exception as e:
        logger.error(f"Error in bulk semantic analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk semantic analysis",
        )


@router.get("/categories", response_model=SemanticCategoriesResponse)
async def get_semantic_categories() -> SemanticCategoriesResponse:
    """
    Get available semantic categories and keywords.
    
    Returns:
        Available semantic categories
    """
    try:
        return SemanticCategoriesResponse(
            task_categories=SemanticAnalysisService.TASK_CATEGORIES,
            event_categories=SemanticAnalysisService.EVENT_CATEGORIES,
            priority_keywords=SemanticAnalysisService.PRIORITY_KEYWORDS,
        )
        
    except Exception as e:
        logger.error(f"Error retrieving semantic categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve semantic categories",
        )


@router.get("/insights/{content_type}", response_model=GenericResponse)
async def get_user_semantic_insights(
    content_type: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericResponse:
    """
    Get user's semantic insights by content type.
    
    Args:
        content_type: Type of content ('task' or 'event')
        limit: Maximum number of insights to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        User's semantic insights
    """
    try:
        from shared.database.models import SemanticInsight
        
        if content_type not in ["task", "event"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content type must be 'task' or 'event'",
            )
        
        insights = (
            db.query(SemanticInsight)
            .filter(
                SemanticInsight.user_id == current_user.id,
                SemanticInsight.content_type == content_type,
                SemanticInsight.insight_type == "semantic_analysis",
            )
            .order_by(SemanticInsight.created_at.desc())
            .limit(limit)
            .all()
        )
        
        insights_data = []
        for insight in insights:
            insights_data.append(
                {
                    "id": str(insight.id),
                    "content_id": insight.content_id,
                    "content_type": insight.content_type,
                    "insight_value": insight.insight_value,
                    "confidence_score": insight.confidence_score,
                    "created_at": insight.created_at.isoformat(),
                    "model_used": insight.model_used,
                }
            )
        
        return GenericResponse(
            success=True,
            message=f"Retrieved {len(insights_data)} semantic insights for {content_type}",
            data={"insights": insights_data},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving semantic insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve semantic insights",
        )
