"""
API router for mission statement interviews and user profiling.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User
from shared.schemas.interview_schemas import (
    MissionInterview,
    MissionInterviewCreate,
    InterviewListResponse,
    InterviewSessionResponse,
    InterviewSessionUpdate,
    InterviewQuestionSet,
    InterviewAnalysisResult
)
from shared.services.interview_service import InterviewService
from shared.services.smart_ai_interview_service import smart_ai_interview_service
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/question-sets", response_model=List[InterviewQuestionSet])
async def get_available_question_sets(
    current_user: User = Depends(get_current_user)
):
    """Get available interview question sets."""
    question_sets = [
        InterviewQuestionSet(
            questions=InterviewService.INTERVIEW_QUESTIONS["mission_statement"],
            interview_type="mission_statement",
            estimated_duration=15,
            description="Discover your core purpose, values, and life mission through thoughtful reflection"
        ),
        InterviewQuestionSet(
            questions=InterviewService.INTERVIEW_QUESTIONS["work_style"],
            interview_type="work_style",
            estimated_duration=10,
            description="Understand your optimal work environment, collaboration preferences, and communication style"
        ),
        InterviewQuestionSet(
            questions=InterviewService.INTERVIEW_QUESTIONS["productivity"],
            interview_type="productivity",
            estimated_duration=10,
            description="Identify your productivity patterns, challenges, and optimization opportunities"
        )
    ]
    return question_sets


@router.post("/start", response_model=InterviewSessionResponse, dependencies=[Depends(verify_csrf_token)])
async def start_interview(
    interview_data: MissionInterviewCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new interview session."""
    try:
        # Create new interview
        interview = InterviewService.create_interview(db, current_user.id, interview_data)
        
        # Get first question
        current_question, question_number, is_complete = InterviewService.get_current_question(interview)
        total_questions = interview.questions.get("total", 0)
        
        response = InterviewSessionResponse(
            interview_id=interview.id,
            current_question=current_question,
            question_number=question_number,
            total_questions=total_questions,
            progress_percentage=0.0,
            is_complete=is_complete,
            next_action="answer_question" if current_question else "complete"
        )
        
        logger.info(f"Started interview {interview.id} for user {current_user.id}")
        return response
        
    except Exception as e:
        logger.error(f"Error starting interview for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview session"
        )


@router.get("/", response_model=InterviewListResponse)
async def get_user_interviews(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interview history."""
    try:
        interviews = InterviewService.get_user_interviews(db, current_user.id, limit)
        return InterviewListResponse(
            interviews=interviews,
            total=len(interviews)
        )
    except Exception as e:
        logger.error(f"Error fetching interviews for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch interview history"
        )


@router.get("/{interview_id}", response_model=MissionInterview)
async def get_interview_details(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific interview details."""
    try:
        interview = InterviewService.get_interview_by_id(db, interview_id, current_user.id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        return interview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching interview {interview_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch interview details"
        )


@router.get("/{interview_id}/session", response_model=InterviewSessionResponse)
async def get_interview_session(
    interview_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current interview session state."""
    try:
        interview = InterviewService.get_interview_by_id(db, interview_id, current_user.id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        current_question, question_number, is_complete = InterviewService.get_current_question(interview)
        total_questions = interview.questions.get("total", 0)
        progress = (question_number - 1) / total_questions * 100 if total_questions > 0 else 0
        
        response = InterviewSessionResponse(
            interview_id=interview.id,
            current_question=current_question,
            question_number=question_number,
            total_questions=total_questions,
            progress_percentage=min(progress, 100.0),
            is_complete=is_complete,
            next_action="analyze" if is_complete else "answer_question"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interview session {interview_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interview session"
        )


@router.post("/{interview_id}/respond", response_model=InterviewSessionResponse, dependencies=[Depends(verify_csrf_token)])
async def respond_to_question(
    interview_id: UUID,
    update_data: InterviewSessionUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit response to interview question."""
    try:
        # Update interview with responses
        interview = InterviewService.update_interview_responses(
            db, interview_id, current_user.id, update_data
        )
        
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Get next question or completion status
        current_question, question_number, is_complete = InterviewService.get_current_question(interview)
        total_questions = interview.questions.get("total", 0)
        progress = (question_number - 1) / total_questions * 100 if total_questions > 0 else 0
        
        response = InterviewSessionResponse(
            interview_id=interview.id,
            current_question=current_question,
            question_number=question_number,
            total_questions=total_questions,
            progress_percentage=min(progress, 100.0),
            is_complete=is_complete,
            next_action="analyze" if is_complete else "answer_question"
        )
        
        logger.info(f"Updated interview {interview_id} with user response")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error responding to interview {interview_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit response"
        )


@router.post("/{interview_id}/analyze", response_model=InterviewAnalysisResult, dependencies=[Depends(verify_csrf_token)])
async def analyze_interview(
    interview_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze completed interview and update user profile."""
    try:
        interview = InterviewService.get_interview_by_id(db, interview_id, current_user.id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Check if interview is complete
        _, _, is_complete = InterviewService.get_current_question(interview)
        if not is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview is not yet complete"
            )
        
        # Analyze responses
        analysis = InterviewService.analyze_interview_responses(interview)
        
        # Update interview with analysis results
        interview.analysis_results = analysis.model_dump()
        interview.status = "analyzed"
        db.commit()
        
        # Update user profile
        InterviewService.update_user_profile_from_interview(
            db, current_user.id, analysis
        )
        
        logger.info(f"Analyzed interview {interview_id} and updated user profile")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing interview {interview_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze interview"
        )


@router.delete("/{interview_id}", dependencies=[Depends(verify_csrf_token)])
async def delete_interview(
    interview_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an interview."""
    try:
        interview = InterviewService.get_interview_by_id(db, interview_id, current_user.id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        db.delete(interview)
        db.commit()
        
        logger.info(f"Deleted interview {interview_id}")
        return {"message": "Interview deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting interview {interview_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interview"
        )


@router.get("/smart-ai/question-sets", response_model=List[InterviewQuestionSet])
async def get_smart_ai_question_sets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-enhanced interview question sets based on user context."""
    try:
        # Get base question sets
        base_question_sets = [
            {
                "questions": InterviewService.INTERVIEW_QUESTIONS["mission_statement"],
                "interview_type": "mission_statement",
                "estimated_duration": 20,  # Increased for enhanced questions
                "description": "AI-enhanced mission discovery that helps your AI assistant understand your purpose and values for better alignment"
            },
            {
                "questions": InterviewService.INTERVIEW_QUESTIONS["work_style"],
                "interview_type": "work_style",
                "estimated_duration": 15,
                "description": "AI-enhanced work style analysis that helps your AI assistant understand your collaboration and communication preferences"
            },
            {
                "questions": InterviewService.INTERVIEW_QUESTIONS["productivity"],
                "interview_type": "productivity",
                "estimated_duration": 15,
                "description": "AI-enhanced productivity analysis that helps your AI assistant optimize your workflow and task management"
            }
        ]
        
        # Enhance each question set with AI context
        enhanced_sets = []
        for base_set in base_question_sets:
            enhanced_questions, _ = await smart_ai_interview_service.generate_smart_interview_questions(
                db, current_user.id, base_set["interview_type"], base_set["questions"]
            )
            
            enhanced_sets.append(InterviewQuestionSet(
                questions=enhanced_questions,
                interview_type=base_set["interview_type"],
                estimated_duration=base_set["estimated_duration"],
                description=base_set["description"]
            ))
        
        return enhanced_sets
        
    except Exception as e:
        logger.error(f"Error getting smart AI question sets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI-enhanced question sets"
        )


@router.get("/smart-ai/mission-alignment-questions")
async def get_mission_alignment_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get questions specifically designed to help AI understand mission alignment."""
    try:
        questions, token_metrics = await smart_ai_interview_service.generate_mission_alignment_questions(
            db, current_user.id
        )
        
        return {
            "questions": questions,
            "purpose": "These questions help your AI assistant understand how to better align with your mission statement and detect potential contradictions",
            "estimated_duration": 10,
            "token_usage": {
                "input_tokens": token_metrics.input_tokens,
                "output_tokens": token_metrics.output_tokens,
                "total_tokens": token_metrics.total_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting mission alignment questions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate mission alignment questions"
        )


@router.post("/{interview_id}/analyze-with-ai", response_model=InterviewAnalysisResult, dependencies=[Depends(verify_csrf_token)])
async def analyze_interview_with_ai_context(
    interview_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze interview with AI context to optimize smart AI system performance."""
    try:
        interview = InterviewService.get_interview_by_id(db, interview_id, current_user.id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found"
            )
        
        # Check if interview is complete
        _, _, is_complete = InterviewService.get_current_question(interview)
        if not is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview is not yet complete"
            )
        
        # Analyze with AI context
        ai_analysis, token_metrics = await smart_ai_interview_service.analyze_responses_with_ai_context(
            db, interview, current_user.id
        )
        
        # Get base analysis
        base_analysis = InterviewService.analyze_interview_responses(interview)
        
        # Merge AI-enhanced analysis with base analysis
        enhanced_analysis = InterviewAnalysisResult(
            mission_statement=ai_analysis.get("mission_alignment_insights", {}).get("mission_statement_refined") or base_analysis.mission_statement,
            personal_goals=base_analysis.personal_goals,
            work_style=ai_analysis.get("ai_collaboration_preferences", {}),
            productivity_patterns=base_analysis.productivity_patterns,
            confidence_score=ai_analysis.get("confidence_score", 0.8),
            recommendations=ai_analysis.get("recommendations", []),
            ai_optimization_insights=ai_analysis.get("smart_ai_recommendations", {})
        )
        
        # Update interview with enhanced analysis
        interview.analysis_results = enhanced_analysis.model_dump()
        interview.status = "analyzed"
        db.commit()
        
        # Update user profile with AI-enhanced insights
        InterviewService.update_user_profile_from_interview(
            db, current_user.id, enhanced_analysis
        )
        
        # Store AI-specific insights in user profile
        user = db.query(User).filter(User.id == current_user.id).first()
        if user:
            ai_insights = user.interview_insights or {}
            ai_insights["ai_optimization"] = ai_analysis.get("smart_ai_recommendations", {})
            ai_insights["mission_alignment"] = ai_analysis.get("mission_alignment_insights", {})
            ai_insights["collaboration_preferences"] = ai_analysis.get("ai_collaboration_preferences", {})
            ai_insights["token_usage"] = {
                "input_tokens": token_metrics.input_tokens,
                "output_tokens": token_metrics.output_tokens,
                "total_tokens": token_metrics.total_tokens
            }
            user.interview_insights = ai_insights
            db.commit()
        
        logger.info(f"Analyzed interview {interview_id} with AI context and updated user profile")
        return enhanced_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing interview with AI context {interview_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze interview with AI context"
        )