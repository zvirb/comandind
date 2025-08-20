"""
Mission Statement Contradiction Detection Service
Analyzes user requests against their mission statement and interview responses
to identify potential contradictions and provide guidance.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from shared.database.models import User, MissionInterview, SemanticInsight, AIAnalysisHistory
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.smart_ai_models import TokenMetrics
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class MissionContradictionService:
    """
    Service for detecting contradictions between user requests and their mission statement,
    interview responses, and personal goals.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
    async def assess_mission_alignment(self, user_id: int, user_request: str, 
                                     session_id: str) -> Tuple[bool, float, str, TokenMetrics]:
        """
        Assess if a user request contradicts their mission statement and goals.
        
        Args:
            user_id: The user ID
            user_request: The user's current request
            session_id: The session ID for logging
            
        Returns:
            Tuple of (has_contradiction, contradiction_score, analysis_text, token_metrics)
        """
        try:
            # Get user profile and mission data
            user_profile = await self._get_user_profile(user_id)
            
            if not user_profile:
                logger.warning(f"No user profile found for user {user_id}")
                return False, 0.0, "No user profile available for contradiction analysis", TokenMetrics()
            
            # Extract mission and goal information
            mission_context = await self._extract_mission_context(user_profile)
            
            if not mission_context:
                logger.info(f"No mission statement or goals found for user {user_id}")
                return False, 0.0, "No mission statement or goals available for analysis", TokenMetrics()
            
            # Perform LLM-based contradiction analysis
            analysis_result, token_metrics = await self._analyze_contradiction(
                user_request, mission_context, session_id
            )
            
            # Store analysis in database
            await self._store_analysis_result(user_id, user_request, mission_context, analysis_result)
            
            return (
                analysis_result["has_contradiction"],
                analysis_result["contradiction_score"],
                analysis_result["analysis_text"],
                token_metrics
            )
            
        except Exception as e:
            logger.error(f"Error assessing mission alignment: {e}", exc_info=True)
            return False, 0.0, "Error occurred during mission alignment analysis", TokenMetrics()
    
    async def _get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile with mission statement and interview data."""
        try:
            # Get database session
            with next(get_db()) as db:
                # Get user with mission statement
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None
                
                # Get latest mission interview
                mission_interview = db.query(MissionInterview).filter(
                    MissionInterview.user_id == user_id,
                    MissionInterview.status == "completed"
                ).order_by(MissionInterview.completed_at.desc()).first()
                
                return {
                    "user_id": user.id,
                    "mission_statement": user.mission_statement,
                    "personal_goals": user.personal_goals,
                    "work_style_preferences": user.work_style_preferences,
                    "productivity_patterns": user.productivity_patterns,
                    "interview_insights": user.interview_insights,
                    "project_preferences": user.project_preferences,
                    "mission_interview": {
                        "responses": mission_interview.responses if mission_interview else None,
                        "analysis_results": mission_interview.analysis_results if mission_interview else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}", exc_info=True)
            return None
    
    async def _extract_mission_context(self, user_profile: Dict[str, Any]) -> Optional[str]:
        """Extract and format mission context for analysis."""
        try:
            mission_parts = []
            
            # Add mission statement
            if user_profile.get("mission_statement"):
                mission_parts.append(f"Mission Statement: {user_profile['mission_statement']}")
            
            # Add personal goals
            if user_profile.get("personal_goals"):
                goals = user_profile["personal_goals"]
                if isinstance(goals, dict):
                    goals_text = []
                    for key, value in goals.items():
                        if isinstance(value, (str, int, float)):
                            goals_text.append(f"{key}: {value}")
                        elif isinstance(value, list):
                            goals_text.append(f"{key}: {', '.join(map(str, value))}")
                    if goals_text:
                        mission_parts.append(f"Personal Goals: {'; '.join(goals_text)}")
            
            # Add work style preferences
            if user_profile.get("work_style_preferences"):
                work_style = user_profile["work_style_preferences"]
                if isinstance(work_style, dict):
                    style_text = []
                    for key, value in work_style.items():
                        if isinstance(value, (str, int, float)):
                            style_text.append(f"{key}: {value}")
                    if style_text:
                        mission_parts.append(f"Work Style Preferences: {'; '.join(style_text)}")
            
            # Add key interview insights
            if user_profile.get("interview_insights"):
                insights = user_profile["interview_insights"]
                if isinstance(insights, dict):
                    key_insights = []
                    for key, value in insights.items():
                        if key in ["core_values", "priorities", "motivations", "long_term_goals"]:
                            if isinstance(value, str):
                                key_insights.append(f"{key}: {value}")
                            elif isinstance(value, list):
                                key_insights.append(f"{key}: {', '.join(map(str, value))}")
                    if key_insights:
                        mission_parts.append(f"Interview Insights: {'; '.join(key_insights)}")
            
            # Add interview responses if available
            mission_interview = user_profile.get("mission_interview", {})
            if mission_interview.get("responses"):
                responses = mission_interview["responses"]
                if isinstance(responses, dict):
                    key_responses = []
                    for question, answer in responses.items():
                        if isinstance(answer, str) and len(answer) > 10:  # Only meaningful responses
                            key_responses.append(f"Q: {question} A: {answer[:200]}...")
                    if key_responses:
                        mission_parts.append(f"Interview Responses: {'; '.join(key_responses[:3])}")  # Limit to 3 responses
            
            return "\n\n".join(mission_parts) if mission_parts else None
            
        except Exception as e:
            logger.error(f"Error extracting mission context: {e}", exc_info=True)
            return None
    
    async def _analyze_contradiction(self, user_request: str, mission_context: str, 
                                   session_id: str) -> Tuple[Dict[str, Any], TokenMetrics]:
        """Perform LLM-based contradiction analysis."""
        try:
            analysis_prompt = f"""
You are a mission alignment analyst. Analyze whether the user's current request contradicts or aligns with their stated mission, goals, and preferences.

USER'S MISSION & GOALS:
{mission_context}

CURRENT USER REQUEST:
{user_request}

Please provide a detailed analysis covering:

1. CONTRADICTION ASSESSMENT:
   - Does the request directly contradict the mission statement? (Yes/No)
   - Does it conflict with stated personal goals? (Yes/No)  
   - Does it go against work style preferences? (Yes/No)
   - Does it contradict interview insights? (Yes/No)

2. CONTRADICTION SCORE:
   - Provide a score from 0.0 to 1.0 where:
     * 0.0 = Perfect alignment with mission and goals
     * 0.3 = Minor misalignment but generally acceptable
     * 0.5 = Moderate contradiction requiring attention
     * 0.7 = Significant contradiction requiring discussion
     * 1.0 = Complete contradiction with core mission/values

3. SPECIFIC CONTRADICTIONS:
   - List specific aspects of the request that contradict the mission
   - Explain why each contradiction is concerning
   - Identify which values or goals are being compromised

4. GUIDANCE:
   - Suggest how to modify the request to better align with the mission
   - Recommend alternative approaches that honor the user's stated goals
   - Provide questions for the user to consider

5. DECISION RECOMMENDATION:
   - Should the request be: APPROVED / MODIFIED / REJECTED / DISCUSS_FURTHER
   - Explain your reasoning for this recommendation

Format your response as follows:
CONTRADICTION_FOUND: [Yes/No]
CONTRADICTION_SCORE: [0.0-1.0]
SPECIFIC_CONTRADICTIONS: [List of contradictions]
GUIDANCE: [Specific guidance and recommendations]
DECISION: [APPROVED/MODIFIED/REJECTED/DISCUSS_FURTHER]
REASONING: [Detailed explanation of your analysis and recommendation]
"""

            messages = [
                {"role": "system", "content": "You are a mission alignment analyst focused on helping users make decisions that align with their stated values and goals."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="mission_analysis"
            )
            
            # Parse the response
            analysis_result = self._parse_analysis_response(response)
            
            return analysis_result, token_metrics
            
        except Exception as e:
            logger.error(f"Error in contradiction analysis: {e}", exc_info=True)
            return {
                "has_contradiction": False,
                "contradiction_score": 0.0,
                "analysis_text": "Error occurred during analysis",
                "specific_contradictions": [],
                "guidance": "Unable to analyze due to error",
                "decision": "APPROVED",
                "reasoning": "Analysis failed, defaulting to approval"
            }, TokenMetrics()
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        try:
            lines = response.strip().split('\n')
            result = {
                "has_contradiction": False,
                "contradiction_score": 0.0,
                "analysis_text": response,
                "specific_contradictions": [],
                "guidance": "",
                "decision": "APPROVED",
                "reasoning": ""
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith('CONTRADICTION_FOUND:'):
                    result["has_contradiction"] = 'yes' in line.lower()
                elif line.startswith('CONTRADICTION_SCORE:'):
                    try:
                        score = float(line.split(':')[1].strip())
                        result["contradiction_score"] = max(0.0, min(1.0, score))
                    except ValueError:
                        result["contradiction_score"] = 0.0
                elif line.startswith('SPECIFIC_CONTRADICTIONS:'):
                    contradictions = line.split(':', 1)[1].strip()
                    result["specific_contradictions"] = [c.strip() for c in contradictions.split(';') if c.strip()]
                elif line.startswith('GUIDANCE:'):
                    result["guidance"] = line.split(':', 1)[1].strip()
                elif line.startswith('DECISION:'):
                    decision = line.split(':', 1)[1].strip().upper()
                    if decision in ["APPROVED", "MODIFIED", "REJECTED", "DISCUSS_FURTHER"]:
                        result["decision"] = decision
                elif line.startswith('REASONING:'):
                    result["reasoning"] = line.split(':', 1)[1].strip()
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}", exc_info=True)
            return {
                "has_contradiction": False,
                "contradiction_score": 0.0,
                "analysis_text": response,
                "specific_contradictions": [],
                "guidance": "Unable to parse analysis",
                "decision": "APPROVED",
                "reasoning": "Parse error, defaulting to approval"
            }
    
    async def _store_analysis_result(self, user_id: int, user_request: str, 
                                   mission_context: str, analysis_result: Dict[str, Any]):
        """Store the analysis result in the database."""
        try:
            with next(get_db()) as db:
                # Store in SemanticInsight
                insight = SemanticInsight(
                    user_id=user_id,
                    content_type="user_request",
                    insight_type="mission_contradiction",
                    insight_value={
                        "user_request": user_request,
                        "mission_context": mission_context,
                        "analysis_result": analysis_result
                    },
                    confidence_score=1.0 - analysis_result["contradiction_score"],  # Higher confidence = lower contradiction
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME
                )
                db.add(insight)
                
                # Store in AIAnalysisHistory
                history = AIAnalysisHistory(
                    user_id=user_id,
                    analysis_type="mission_contradiction",
                    input_data={
                        "user_request": user_request,
                        "mission_context": mission_context
                    },
                    output_data=analysis_result,
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME,
                    processing_time_ms=0  # Could add timing if needed
                )
                db.add(history)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing analysis result: {e}", exc_info=True)
    
    async def get_recent_contradiction_analyses(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent contradiction analyses for a user."""
        try:
            with next(get_db()) as db:
                insights = db.query(SemanticInsight).filter(
                    SemanticInsight.user_id == user_id,
                    SemanticInsight.insight_type == "mission_contradiction"
                ).order_by(SemanticInsight.created_at.desc()).limit(limit).all()
                
                return [
                    {
                        "id": str(insight.id),
                        "created_at": insight.created_at.isoformat(),
                        "user_request": insight.insight_value.get("user_request", ""),
                        "analysis_result": insight.insight_value.get("analysis_result", {}),
                        "confidence_score": insight.confidence_score
                    }
                    for insight in insights
                ]
                
        except Exception as e:
            logger.error(f"Error getting recent analyses: {e}", exc_info=True)
            return []


# Singleton instance
mission_contradiction_service = MissionContradictionService()