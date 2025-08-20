# In app/shared/services/smart_ai_interview_service.py
import os
import logging
from typing import Tuple, Optional
from shared.services.adaptive_socratic_interview_service import adaptive_socratic_interview_service
from worker.smart_ai_models import TokenMetrics

logger = logging.getLogger(__name__)

class SmartAIInterviewService:
    """
    Smart AI Interview Service - Now using the adaptive Socratic approach
    that treats interview frameworks as guides and adapts to user context.
    """
    
    def __init__(self):
        self.adaptive_service = adaptive_socratic_interview_service
    
    def _get_guide_content(self, filename: str) -> str:
        """Helper to read the content of the guide files."""
        path = os.path.join("documents", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: Critical guidance document '{filename}' not found."

    async def initiate_assessment(self, user_id: int, assessment_type: str, 
                                session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Initiate an adaptive assessment that uses frameworks as guides
        and personalizes questions based on user context and history.
        """
        try:
            # Map assessment types to interview types
            interview_type_mapping = {
                "personal_life_statement": "mission_statement",
                "mission_statement": "mission_statement", 
                "work_style_assessment": "work_style",
                "productivity_patterns": "productivity_patterns"
            }
            
            interview_type = interview_type_mapping.get(assessment_type, "mission_statement")
            
            logger.info(f"Initiating adaptive {interview_type} interview for user {user_id}")
            
            # Use the adaptive service to create personalized opening
            response, token_metrics = await self.adaptive_service.initiate_adaptive_interview(
                user_id=user_id,
                interview_type=interview_type,
                session_id=session_id
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error in adaptive interview initiation: {e}", exc_info=True)
            fallback_response = """Hello. I'm here to help you explore what matters most to you through thoughtful conversation. 
            
Rather than giving you answers, I'll ask questions that help you discover your own insights. 

To begin, can you think of a moment recently when you felt truly engaged and energized by what you were doing? I'm curious about what made that experience meaningful to you."""
            
            return fallback_response, TokenMetrics()
    
    async def continue_assessment(self, user_id: int, user_response: str, 
                                assessment_type: str, session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Continue the assessment by generating adaptive follow-up questions
        based on the user's response and accumulated context.
        """
        try:
            # Map assessment types to interview types
            interview_type_mapping = {
                "personal_life_statement": "mission_statement",
                "mission_statement": "mission_statement",
                "work_style_assessment": "work_style", 
                "productivity_patterns": "productivity_patterns"
            }
            
            interview_type = interview_type_mapping.get(assessment_type, "mission_statement")
            
            logger.info(f"Continuing adaptive {interview_type} interview for user {user_id}")
            
            # Use adaptive service to generate contextual follow-up
            response, token_metrics = await self.adaptive_service.continue_adaptive_interview(
                user_id=user_id,
                user_response=user_response,
                interview_type=interview_type,
                session_id=session_id
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error continuing adaptive interview: {e}", exc_info=True)
            
            # Intelligent fallback based on user response
            fallback_response = f"""That's really insightful. When you mentioned "{user_response[:50]}{'...' if len(user_response) > 50 else ''}", it made me curious about something deeper.
            
What does that experience tell you about what you value most? I'm interested in understanding what drives those feelings you described."""
            
            return fallback_response, TokenMetrics()

# Ensure you have a singleton or dependency-injected instance of the service
smart_ai_interview_service = SmartAIInterviewService()
