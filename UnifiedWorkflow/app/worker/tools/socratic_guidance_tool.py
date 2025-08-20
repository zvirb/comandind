"""
Socratic Method Guidance Tool
Uses gentle questioning to guide users toward their mission statement alignment.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from shared.database.models import User, Task, AIAnalysisHistory
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.smart_ai_models import TokenMetrics
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class SocraticGuidanceTool:
    """
    Tool that uses the Socratic method to gently guide users toward mission alignment
    through thoughtful questioning and reflection.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.name = "socratic_guidance"
        self.description = "Use gentle Socratic questioning to guide users toward mission alignment"
    
    async def invoke(self, user_id: int, user_request: str, current_context: str = "",
                    session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Generate adaptive Socratic questions to guide user toward deeper self-understanding.
        
        Args:
            user_id: The user ID
            user_request: The user's current request or statement
            current_context: Additional context about the situation
            session_id: Session ID for tracking
            
        Returns:
            Tuple of (socratic_response, token_metrics)
        """
        try:
            # Get comprehensive user context
            user_profile = await self._get_user_profile(user_id)
            
            # Generate adaptive Socratic response based on context
            socratic_response, token_metrics = await self._generate_adaptive_socratic_response(
                user_request, user_profile, current_context, session_id
            )
            
            # Store the interaction
            await self._store_socratic_interaction(
                user_id, user_request, socratic_response, {"context": current_context}, session_id
            )
            
            return socratic_response, token_metrics
            
        except Exception as e:
            logger.error(f"Error in Socratic guidance tool: {e}", exc_info=True)
            return "I'd like to help you think through this decision. Can you tell me more about what's driving this choice?", TokenMetrics()
    
    async def _get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get user profile information for context."""
        try:
            with next(get_db()) as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {}
                
                # Get recent tasks for additional context
                recent_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status.in_(["pending", "in_progress", "completed"])
                ).order_by(Task.created_at.desc()).limit(5).all()
                
                return {
                    "mission_statement": user.mission_statement,
                    "personal_goals": user.personal_goals,
                    "work_style_preferences": user.work_style_preferences,
                    "productivity_patterns": user.productivity_patterns,
                    "interview_insights": user.interview_insights,
                    "recent_tasks": [
                        {
                            "title": task.title,
                            "description": task.description,
                            "priority": task.priority,
                            "status": task.status,
                            "semantic_category": task.semantic_category
                        } for task in recent_tasks
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}", exc_info=True)
            return {}
    
    async def _handle_no_mission_statement(self, user_request: str, 
                                         user_profile: Dict[str, Any]) -> Tuple[str, TokenMetrics]:
        """Handle cases where user doesn't have a mission statement."""
        try:
            prompt = f"""
The user has made this request: "{user_request}"

However, they don't have a defined mission statement yet. Use gentle Socratic questioning 
to help them think about their deeper purpose and values that might guide this decision.

Create a thoughtful response that:
1. Acknowledges their request
2. Gently guides them to reflect on their deeper motivations
3. Asks 1-2 open-ended questions that help them think about their values
4. Encourages self-discovery rather than giving direct advice

Keep the tone warm, supportive, and genuinely curious about their perspective.
"""

            messages = [
                {"role": "system", "content": "You are a wise mentor who uses gentle Socratic questioning to help people discover their own insights and values."},
                {"role": "user", "content": prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="socratic_guidance"
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error handling no mission statement: {e}", exc_info=True)
            return "I'd like to help you think through this. What's most important to you in making this decision?", TokenMetrics()
    
    async def _analyze_misalignment(self, user_request: str, user_profile: Dict[str, Any],
                                  current_context: str) -> Dict[str, Any]:
        """Analyze how the user's request might misalign with their mission."""
        try:
            analysis_prompt = f"""
Analyze the potential misalignment between this user's request and their mission statement.

USER REQUEST: "{user_request}"
CURRENT CONTEXT: "{current_context}"

USER MISSION STATEMENT: "{user_profile.get('mission_statement', '')}"
PERSONAL GOALS: {user_profile.get('personal_goals', {})}
WORK STYLE: {user_profile.get('work_style_preferences', {})}

Recent tasks context: {user_profile.get('recent_tasks', [])}

Identify:
1. Specific areas where the request might diverge from their mission
2. Underlying values or priorities that might be in conflict
3. Potential positive intentions behind the request
4. Areas where they might need to reflect more deeply

Format as JSON:
{{
  "misalignment_areas": ["area1", "area2"],
  "conflicting_values": ["value1", "value2"],
  "positive_intentions": ["intention1", "intention2"],
  "reflection_opportunities": ["opportunity1", "opportunity2"],
  "severity": "low/medium/high"
}}
"""

            messages = [
                {"role": "system", "content": "You are an expert at analyzing value alignment and identifying areas for reflection."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="socratic_analysis"
            )
            
            # Parse the analysis
            try:
                import json
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
            
            return {
                "misalignment_areas": ["general alignment"],
                "conflicting_values": ["unknown"],
                "positive_intentions": ["user autonomy"],
                "reflection_opportunities": ["values clarification"],
                "severity": "medium"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing misalignment: {e}", exc_info=True)
            return {}
    
    async def _generate_socratic_questions(self, user_request: str, user_profile: Dict[str, Any],
                                         misalignment_analysis: Dict[str, Any],
                                         current_context: str) -> Tuple[str, TokenMetrics]:
        """Generate Socratic questions to guide the user."""
        try:
            socratic_prompt = f"""
You are a wise mentor using the Socratic method to help someone reflect on their choices 
and align with their deeper purpose. Generate a thoughtful response with gentle questions.

USER REQUEST: "{user_request}"
CURRENT CONTEXT: "{current_context}"

USER'S MISSION STATEMENT: "{user_profile.get('mission_statement', '')}"
PERSONAL GOALS: {user_profile.get('personal_goals', {})}

MISALIGNMENT ANALYSIS:
- Areas of concern: {misalignment_analysis.get('misalignment_areas', [])}
- Conflicting values: {misalignment_analysis.get('conflicting_values', [])}
- Positive intentions: {misalignment_analysis.get('positive_intentions', [])}
- Reflection opportunities: {misalignment_analysis.get('reflection_opportunities', [])}
- Severity: {misalignment_analysis.get('severity', 'medium')}

Create a response that:
1. Acknowledges their request without judgment
2. Gently introduces 2-3 thoughtful questions that help them reflect
3. Connects to their stated mission and values
4. Encourages self-discovery rather than giving direct advice
5. Maintains a warm, supportive tone

Use questions like:
- "What aspects of this align with your mission to...?"
- "How might this decision impact your goal of...?"
- "What would the person you want to become do in this situation?"
- "What values are most important to you in this decision?"
- "How does this choice serve your deeper purpose?"

Keep the response conversational and genuinely curious about their perspective.
"""

            messages = [
                {"role": "system", "content": "You are a wise mentor who uses gentle Socratic questioning to help people discover their own insights and align with their values."},
                {"role": "user", "content": socratic_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="socratic_guidance"
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error generating Socratic questions: {e}", exc_info=True)
            return "I'd like to help you think through this. How does this decision connect to what matters most to you?", TokenMetrics()
    
    async def _generate_adaptive_socratic_response(self, user_request: str, user_profile: Dict[str, Any],
                                                 current_context: str, session_id: Optional[str] = None) -> Tuple[str, TokenMetrics]:
        """
        Generate adaptive Socratic questions based on user context and request.
        Uses the Socratic method as a guide, not a script, adapting to the specific user.
        """
        try:
            system_prompt = """You are a masterful Socratic questioner who helps people discover deeper truths about themselves. Your approach:

1. Use the Socratic method as a GUIDE, not a rigid script
2. Adapt questions based on what you know about this specific person
3. Reference their past experiences, stated values, and current context
4. Ask questions that reveal underlying assumptions and values
5. Create psychological safety through warmth and genuine curiosity
6. Probe gently but persistently toward deeper self-understanding

NEVER give advice or answers - only ask insightful questions that lead to self-discovery."""

            user_prompt = f"""A person has made this request/statement: "{user_request}"

CURRENT CONTEXT: {current_context}

WHAT I KNOW ABOUT THEM:
- Mission Statement: {user_profile.get('mission_statement', 'Not yet defined')}
- Personal Goals: {user_profile.get('personal_goals', {})}
- Work Style: {user_profile.get('work_style_preferences', {})}
- Productivity Patterns: {user_profile.get('productivity_patterns', {})}
- Interview Insights: {user_profile.get('interview_insights', {})}
- Recent Tasks: {[task.get('title', '') for task in user_profile.get('recent_tasks', [])][:3]}

TASK:
Generate ONE perfectly crafted Socratic question that:
1. Connects directly to their specific request and context
2. Uses what you know about their values, goals, and patterns
3. Helps them discover something new about themselves
4. Feels personally relevant and insightful
5. Maintains warmth and genuine curiosity

Focus on helping them explore the deeper motivations and values behind their request."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="adaptive_socratic_guidance"
            )
            
            return response, token_metrics
            
        except Exception as e:
            logger.error(f"Error generating adaptive Socratic response: {e}", exc_info=True)
            return f"I'm curious about what's driving this decision for you. Given what you've shared before about {user_profile.get('personal_goals', {}).get('primary_goal', 'your goals')}, how does this request connect to what matters most to you?", TokenMetrics()
    
    async def _store_socratic_interaction(self, user_id: int, user_request: str,
                                        socratic_response: str, misalignment_analysis: Dict[str, Any],
                                        session_id: Optional[str] = None):
        """Store the Socratic interaction for learning and tracking."""
        try:
            with next(get_db()) as db:
                analysis_history = AIAnalysisHistory(
                    user_id=user_id,
                    analysis_type="socratic_guidance",
                    input_data={
                        "user_request": user_request,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    },
                    output_data={
                        "socratic_response": socratic_response,
                        "misalignment_analysis": misalignment_analysis
                    },
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME
                )
                
                db.add(analysis_history)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing Socratic interaction: {e}", exc_info=True)
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the tool definition for the AI system."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "The user's current request or statement"
                    },
                    "current_context": {
                        "type": "string",
                        "description": "Additional context about the situation"
                    }
                },
                "required": ["user_request"]
            },
            "when_to_use": [
                "When user's request might contradict their mission statement",
                "When user seems to be making decisions that don't align with their stated values",
                "When user would benefit from deeper reflection on their choices",
                "When gentle guidance toward mission alignment would be helpful",
                "When user appears to be acting impulsively or without considering their deeper purpose"
            ]
        }


# Global instance
socratic_guidance_tool = SocraticGuidanceTool()