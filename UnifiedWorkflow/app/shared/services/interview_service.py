"""
Service for managing user interviews and analysis.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.models import MissionInterview, User, AIAnalysisHistory
from shared.schemas.interview_schemas import (
    MissionInterviewCreate, 
    InterviewSessionUpdate,
    InterviewAnalysisResult,
    UserProfileUpdate
)

logger = logging.getLogger(__name__)


class InterviewService:
    """Service for managing user interviews and AI analysis."""
    
    # Predefined question sets for different interview types
    INTERVIEW_QUESTIONS = {
        "mission_statement": [
            "What drives you to get up in the morning? What gives your life meaning and purpose?",
            "If you could solve one major problem in the world, what would it be and why?",
            "What activities make you lose track of time because you're so engaged?",
            "What values are most important to you in your work and personal life?",
            "How do you want to be remembered? What legacy do you want to leave?",
            "What achievements are you most proud of, and what made them meaningful?",
            "When you imagine your ideal future, what does it look like?",
            "What skills or talents do you have that you'd like to use more?",
            "What challenges or obstacles have shaped who you are today?",
            "If you had unlimited resources, how would you spend your time?"
        ],
        "work_style": [
            "Do you prefer working alone or in a team? Why?",
            "What time of day are you most productive?",
            "How do you prefer to receive feedback - directly, in writing, or through discussions?",
            "What kind of work environment helps you do your best work?",
            "How do you typically approach new projects or challenges?",
            "What motivates you more - autonomy or clear direction?",
            "How do you prefer to communicate with colleagues and supervisors?",
            "What helps you stay organized and manage your workload?"
        ],
        "productivity": [
            "What tools or systems do you currently use to stay organized?",
            "What are your biggest productivity challenges?",
            "How do you currently prioritize your tasks?",
            "What distracts you the most during work?",
            "When do you feel most creative and focused?",
            "How do you handle interruptions and unexpected tasks?",
            "What habits have helped you be more productive?",
            "How do you balance urgent tasks with important long-term goals?"
        ]
    }

    @staticmethod
    def create_interview(db: Session, user_id: int, interview_data: MissionInterviewCreate) -> MissionInterview:
        """Create a new interview session."""
        try:
            # Generate questions based on interview type
            questions = InterviewService._generate_questions(interview_data.interview_type)
            
            interview = MissionInterview(
                user_id=user_id,
                interview_type=interview_data.interview_type,
                llm_model=interview_data.llm_model,
                status="in_progress",
                questions={"questions": questions, "total": len(questions)},
                responses={},
                analysis_results={},
                recommendations={}
            )
            
            db.add(interview)
            db.commit()
            db.refresh(interview)
            
            logger.info(f"Created interview {interview.id} for user {user_id}")
            return interview
            
        except Exception as e:
            logger.error(f"Error creating interview for user {user_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_user_interviews(db: Session, user_id: int, limit: int = 10) -> List[MissionInterview]:
        """Get user's interview history."""
        try:
            return db.query(MissionInterview)\
                     .filter(MissionInterview.user_id == user_id)\
                     .order_by(desc(MissionInterview.created_at))\
                     .limit(limit)\
                     .all()
        except Exception as e:
            logger.error(f"Error fetching interviews for user {user_id}: {e}")
            return []

    @staticmethod
    def get_interview_by_id(db: Session, interview_id: uuid.UUID, user_id: int) -> Optional[MissionInterview]:
        """Get interview by ID (with user ownership check)."""
        try:
            return db.query(MissionInterview)\
                     .filter(MissionInterview.id == interview_id)\
                     .filter(MissionInterview.user_id == user_id)\
                     .first()
        except Exception as e:
            logger.error(f"Error fetching interview {interview_id}: {e}")
            return None

    @staticmethod
    def update_interview_responses(
        db: Session, 
        interview_id: uuid.UUID, 
        user_id: int, 
        update_data: InterviewSessionUpdate
    ) -> Optional[MissionInterview]:
        """Update interview with user responses."""
        try:
            interview = InterviewService.get_interview_by_id(db, interview_id, user_id)
            if not interview:
                return None
            
            # Merge new responses with existing ones
            current_responses = interview.responses or {}
            current_responses.update(update_data.responses)
            interview.responses = current_responses
            
            # Update status if provided
            if update_data.status:
                interview.status = update_data.status
                if update_data.status == "completed":
                    interview.completed_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(interview)
            
            logger.info(f"Updated interview {interview_id} responses")
            return interview
            
        except Exception as e:
            logger.error(f"Error updating interview {interview_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def get_current_question(interview: MissionInterview) -> Tuple[Optional[str], int, bool]:
        """Get the current question for an interview session."""
        try:
            questions = interview.questions.get("questions", [])
            responses = interview.responses or {}
            
            # Find first unanswered question
            for i, question in enumerate(questions):
                question_key = f"question_{i}"
                if question_key not in responses:
                    return question, i + 1, False
            
            # All questions answered
            return None, len(questions), True
            
        except Exception as e:
            logger.error(f"Error getting current question for interview {interview.id}: {e}")
            return None, 0, False

    @staticmethod
    def analyze_interview_responses(interview: MissionInterview) -> InterviewAnalysisResult:
        """Analyze interview responses and generate insights."""
        try:
            responses = interview.responses or {}
            questions = interview.questions.get("questions", [])
            
            # Basic analysis logic (to be enhanced with LLM integration)
            analysis = InterviewAnalysisResult()
            
            if interview.interview_type == "mission_statement":
                analysis = InterviewService._analyze_mission_responses(questions, responses)
            elif interview.interview_type == "work_style":
                analysis = InterviewService._analyze_work_style_responses(questions, responses)
            elif interview.interview_type == "productivity":
                analysis = InterviewService._analyze_productivity_responses(questions, responses)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing interview {interview.id}: {e}")
            return InterviewAnalysisResult()

    @staticmethod
    def update_user_profile_from_interview(
        db: Session, 
        user_id: int, 
        analysis: InterviewAnalysisResult
    ) -> bool:
        """Update user profile based on interview analysis."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Update user profile fields
            if analysis.mission_statement:
                user.mission_statement = analysis.mission_statement
            
            if analysis.personal_goals:
                user.personal_goals = {"goals": analysis.personal_goals, "updated_at": datetime.now(timezone.utc).isoformat()}
            
            if analysis.work_style:
                user.work_style_preferences = analysis.work_style
            
            if analysis.productivity_patterns:
                user.productivity_patterns = analysis.productivity_patterns
            
            # Store insights
            insights = {
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "confidence_score": analysis.confidence_score,
                "recommendations": analysis.recommendations
            }
            user.interview_insights = insights
            user.last_interview_date = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Updated user {user_id} profile from interview analysis")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile from interview: {e}")
            db.rollback()
            return False

    @staticmethod
    def _generate_questions(interview_type: str) -> List[str]:
        """Generate questions for interview type."""
        return InterviewService.INTERVIEW_QUESTIONS.get(interview_type, [])

    @staticmethod
    def _analyze_mission_responses(questions: List[str], responses: Dict[str, Any]) -> InterviewAnalysisResult:
        """Analyze mission statement interview responses."""
        # Basic keyword-based analysis (to be enhanced with LLM)
        mission_keywords = []
        goals = []
        values = []
        
        for key, response in responses.items():
            if isinstance(response, str):
                response_lower = response.lower()
                
                # Extract mission-related keywords
                if any(word in response_lower for word in ["purpose", "meaning", "drive", "passion"]):
                    mission_keywords.append(response)
                
                # Extract goals
                if any(word in response_lower for word in ["want", "goal", "achieve", "future"]):
                    goals.append(response)
                
                # Extract values
                if any(word in response_lower for word in ["value", "important", "believe", "principle"]):
                    values.append(response)
        
        # Generate a basic mission statement
        mission_statement = "Based on your responses, you are driven by " + \
                          " and ".join(mission_keywords[:2]) if mission_keywords else None
        
        return InterviewAnalysisResult(
            mission_statement=mission_statement,
            personal_goals=goals[:5],
            work_style={"values": values},
            confidence_score=0.7,
            recommendations=[
                "Consider refining your mission statement based on your core values",
                "Set specific, actionable goals aligned with your purpose"
            ]
        )

    @staticmethod
    def _analyze_work_style_responses(questions: List[str], responses: Dict[str, Any]) -> InterviewAnalysisResult:
        """Analyze work style interview responses."""
        work_style = {
            "collaboration_preference": "unknown",
            "optimal_work_time": "unknown",
            "communication_style": "unknown",
            "work_environment": "unknown"
        }
        
        for key, response in responses.items():
            if isinstance(response, str):
                response_lower = response.lower()
                
                if "team" in response_lower or "collaborate" in response_lower:
                    work_style["collaboration_preference"] = "team-oriented"
                elif "alone" in response_lower or "independent" in response_lower:
                    work_style["collaboration_preference"] = "independent"
                
                if "morning" in response_lower:
                    work_style["optimal_work_time"] = "morning"
                elif "evening" in response_lower or "night" in response_lower:
                    work_style["optimal_work_time"] = "evening"
        
        return InterviewAnalysisResult(
            work_style=work_style,
            confidence_score=0.6,
            recommendations=[
                "Optimize your schedule based on your peak productivity times",
                "Communicate your work style preferences to your team"
            ]
        )

    @staticmethod
    def _analyze_productivity_responses(questions: List[str], responses: Dict[str, Any]) -> InterviewAnalysisResult:
        """Analyze productivity interview responses."""
        productivity_patterns = {
            "organization_tools": [],
            "main_challenges": [],
            "peak_performance_times": [],
            "distraction_sources": []
        }
        
        for key, response in responses.items():
            if isinstance(response, str):
                response_lower = response.lower()
                
                # Extract tools mentioned
                if any(tool in response_lower for tool in ["calendar", "todo", "notebook", "app", "system"]):
                    productivity_patterns["organization_tools"].append(response)
                
                # Extract challenges
                if any(word in response_lower for word in ["challenge", "difficult", "struggle", "problem"]):
                    productivity_patterns["main_challenges"].append(response)
        
        return InterviewAnalysisResult(
            productivity_patterns=productivity_patterns,
            confidence_score=0.6,
            recommendations=[
                "Consider implementing time-blocking techniques",
                "Identify and minimize your main distraction sources",
                "Experiment with productivity tools that match your work style"
            ]
        )