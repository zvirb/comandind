"""
User History Summarization Service
Creates comprehensive summaries of user's chat history over time
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from shared.database.models import (
    User, UserHistorySummary, ChatSessionSummary, ChatMessage, 
    Task, UserCategory
)
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens

logger = logging.getLogger(__name__)


class UserHistorySummarizationService:
    """Service for generating and managing user history summaries."""
    
    def __init__(self):
        self.default_model = "llama3.2:3b"  # Fallback model
    
    async def generate_user_summary(
        self, 
        db: Session, 
        user_id: int, 
        period: str = "all_time",
        force_regenerate: bool = False
    ) -> Optional[UserHistorySummary]:
        """Generate a comprehensive summary of user's history."""
        try:
            logger.info(f"Generating user summary for user {user_id}, period: {period}")
            
            # Check if summary already exists and is recent
            if not force_regenerate:
                existing_summary = await self._get_existing_summary(db, user_id, period)
                if existing_summary:
                    logger.info(f"Using existing summary for user {user_id}")
                    return existing_summary
            
            # Determine date range
            period_start, period_end = self._get_period_dates(period)
            
            # Gather user data
            user_data = await self._gather_user_data(db, user_id, period_start, period_end)
            
            if not user_data or user_data['total_sessions'] == 0:
                logger.info(f"No data found for user {user_id} in period {period}")
                return None
            
            # Generate AI analysis
            analysis_results = await self._generate_ai_analysis(user_data, user_id)
            
            # Create or update summary
            summary = await self._create_or_update_summary(
                db, user_id, period, period_start, period_end, 
                user_data, analysis_results
            )
            
            logger.info(f"Successfully generated summary for user {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating user summary: {e}", exc_info=True)
            return None
    
    def _get_period_dates(self, period: str) -> tuple[datetime, datetime]:
        """Get start and end dates for the specified period."""
        end_date = datetime.utcnow()
        
        if period == "weekly":
            start_date = end_date - timedelta(weeks=1)
        elif period == "monthly":
            start_date = end_date - timedelta(days=30)
        elif period == "quarterly":
            start_date = end_date - timedelta(days=90)
        else:  # all_time
            start_date = datetime(2020, 1, 1)  # Far enough back
        
        return start_date, end_date
    
    async def _get_existing_summary(
        self, 
        db: Session, 
        user_id: int, 
        period: str
    ) -> Optional[UserHistorySummary]:
        """Check for existing recent summary."""
        try:
            # For all_time summaries, check if one exists from last week
            # For weekly/monthly, check if one exists from last day
            recency_threshold = datetime.utcnow() - (
                timedelta(days=7) if period == "all_time" else timedelta(days=1)
            )
            
            existing = db.query(UserHistorySummary).filter(
                UserHistorySummary.user_id == user_id,
                UserHistorySummary.summary_period == period,
                UserHistorySummary.created_at >= recency_threshold
            ).order_by(desc(UserHistorySummary.created_at)).first()
            
            return existing
            
        except Exception as e:
            logger.error(f"Error checking existing summary: {e}")
            return None
    
    async def _gather_user_data(
        self, 
        db: Session, 
        user_id: int, 
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Gather comprehensive user data for analysis."""
        try:
            user_data = {
                'user_id': user_id,
                'total_sessions': 0,
                'total_messages': 0,
                'total_tokens': 0,
                'session_summaries': [],
                'recent_messages': [],
                'domains': {},
                'tools_used': {},
                'tasks_completed': [],
                'user_categories': [],
                'interaction_patterns': {}
            }
            
            # Get session summaries
            session_summaries = db.query(ChatSessionSummary).filter(
                ChatSessionSummary.user_id == user_id,
                ChatSessionSummary.started_at >= start_date,
                ChatSessionSummary.ended_at <= end_date
            ).order_by(desc(ChatSessionSummary.started_at)).limit(50).all()
            
            for session in session_summaries:
                user_data['total_sessions'] += 1
                user_data['total_messages'] += session.message_count
                user_data['total_tokens'] += session.total_tokens_used or 0
                
                user_data['session_summaries'].append({
                    'summary': session.summary,
                    'key_topics': session.key_topics,
                    'decisions_made': session.decisions_made,
                    'user_preferences': session.user_preferences,
                    'tools_used': session.tools_used,
                    'complexity_level': session.complexity_level,
                    'resolution_status': session.resolution_status,
                    'started_at': session.started_at.isoformat()
                })
                
                # Aggregate domains
                if session.conversation_domain:
                    domain = session.conversation_domain
                    user_data['domains'][domain] = user_data['domains'].get(domain, 0) + 1
                
                # Aggregate tools
                for tool in session.tools_used:
                    user_data['tools_used'][tool] = user_data['tools_used'].get(tool, 0) + 1
            
            # Get recent chat messages for context
            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.created_at >= start_date,
                ChatMessage.message_type == 'human'  # Only user messages
            ).order_by(desc(ChatMessage.created_at)).limit(20).all()
            
            for message in recent_messages:
                user_data['recent_messages'].append({
                    'content': message.content[:500],  # Truncate for privacy
                    'conversation_domain': message.conversation_domain,
                    'created_at': message.created_at.isoformat()
                })
            
            # Get completed tasks
            completed_tasks = db.query(Task).filter(
                Task.user_id == user_id,
                Task.status == 'completed',
                Task.updated_at >= start_date
            ).order_by(desc(Task.updated_at)).limit(30).all()
            
            for task in completed_tasks:
                user_data['tasks_completed'].append({
                    'title': task.title,
                    'category': task.category,
                    'task_type': task.task_type.value if task.task_type else None,
                    'completed_at': task.updated_at.isoformat()
                })
            
            # Get user categories
            categories = db.query(UserCategory).filter(
                UserCategory.user_id == user_id
            ).all()
            
            for category in categories:
                user_data['user_categories'].append({
                    'name': category.category_name,
                    'type': category.category_type,
                    'weight': category.weight
                })
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error gathering user data: {e}", exc_info=True)
            return {}
    
    async def _generate_ai_analysis(self, user_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Use AI to analyze user data and generate insights."""
        try:
            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(user_data)
            
            # Get user's preferred model or use default
            model_name = self.default_model
            
            messages = [
                {
                    "role": "system", 
                    "content": """You are an expert user behavior analyst. Analyze the provided user data and generate comprehensive insights about their preferences, patterns, and growth areas. Format your response as valid JSON with the required fields."""
                },
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                model_name,
                category="user_analysis"
            )
            
            # Parse JSON response
            analysis_results = self._parse_analysis_response(response)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}", exc_info=True)
            return self._get_fallback_analysis(user_data)
    
    def _build_analysis_prompt(self, user_data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt from user data."""
        
        # Summarize session data
        session_count = user_data['total_sessions']
        message_count = user_data['total_messages']
        
        # Top domains
        top_domains = sorted(user_data['domains'].items(), key=lambda x: x[1], reverse=True)[:5]
        domain_summary = ", ".join([f"{domain} ({count})" for domain, count in top_domains])
        
        # Top tools
        top_tools = sorted(user_data['tools_used'].items(), key=lambda x: x[1], reverse=True)[:5]
        tools_summary = ", ".join([f"{tool} ({count})" for tool, count in top_tools])
        
        # Recent topics from session summaries
        recent_topics = []
        for session in user_data['session_summaries'][:10]:
            recent_topics.extend(session.get('key_topics', []))
        
        # Build prompt
        prompt = f"""Analyze this user's interaction history and provide comprehensive insights.

**User Activity Summary:**
- Total chat sessions: {session_count}
- Total messages: {message_count}
- Primary domains: {domain_summary or 'None'}
- Frequently used tools: {tools_summary or 'None'}
- Completed tasks: {len(user_data['tasks_completed'])}

**Recent Session Summaries:**
{chr(10).join([f"- {session['summary']}" for session in user_data['session_summaries'][:10]])}

**Recent Topics Discussed:**
{', '.join(set(recent_topics[:20]))}

**Task Completion Patterns:**
{chr(10).join([f"- {task['title']} ({task['category']})" for task in user_data['tasks_completed'][:10]])}

**Analysis Required:**
Generate a comprehensive user profile as JSON:

{{
  "executive_summary": "2-3 sentence summary of user's primary interests and engagement",
  "primary_domains": ["domain1", "domain2", "domain3"],
  "frequent_topics": ["topic1", "topic2", "topic3"],
  "key_preferences": {{"preference_type": "specific_preference"}},
  "skill_areas": ["skill1", "skill2", "skill3"],
  "preferred_tools": ["tool1", "tool2", "tool3"],
  "interaction_patterns": {{
    "session_frequency": "daily|weekly|monthly",
    "typical_session_length": "short|medium|long",
    "preferred_complexity": "low|medium|high",
    "communication_style": "brief|detailed|conversational"
  }},
  "complexity_preference": "low|medium|high",
  "important_context": "Key context that should be remembered about this user",
  "recurring_themes": ["theme1", "theme2", "theme3"],
  "engagement_indicators": {{
    "activity_level": "high|medium|low",
    "goal_completion": "excellent|good|needs_improvement",
    "feature_adoption": "early_adopter|steady|cautious"
  }},
  "growth_opportunities": ["opportunity1", "opportunity2"],
  "behavioral_insights": ["insight1", "insight2"]
}}

**Guidelines:**
- Focus on actionable insights that improve user experience
- Identify patterns that indicate user preferences and work style
- Highlight areas where the user excels and areas for growth
- Provide context that would help future interactions
- Be specific and evidence-based rather than generic

Analyze the user data:"""

        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse AI analysis response into structured data."""
        try:
            import json
            
            # Find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                analysis_data = json.loads(json_str)
                
                # Validate and provide defaults
                return {
                    "executive_summary": analysis_data.get("executive_summary", "Active user with diverse interests"),
                    "primary_domains": analysis_data.get("primary_domains", []),
                    "frequent_topics": analysis_data.get("frequent_topics", []),
                    "key_preferences": analysis_data.get("key_preferences", {}),
                    "skill_areas": analysis_data.get("skill_areas", []),
                    "preferred_tools": analysis_data.get("preferred_tools", []),
                    "interaction_patterns": analysis_data.get("interaction_patterns", {}),
                    "complexity_preference": analysis_data.get("complexity_preference", "medium"),
                    "important_context": analysis_data.get("important_context", ""),
                    "recurring_themes": analysis_data.get("recurring_themes", []),
                    "engagement_indicators": analysis_data.get("engagement_indicators", {}),
                    "growth_opportunities": analysis_data.get("growth_opportunities", []),
                    "behavioral_insights": analysis_data.get("behavioral_insights", [])
                }
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI analysis as JSON, using fallback")
        
        return self._get_fallback_analysis({})
    
    def _get_fallback_analysis(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI analysis fails."""
        return {
            "executive_summary": "User with active engagement across multiple domains",
            "primary_domains": list(user_data.get('domains', {}).keys())[:3],
            "frequent_topics": [],
            "key_preferences": {},
            "skill_areas": [],
            "preferred_tools": list(user_data.get('tools_used', {}).keys())[:3],
            "interaction_patterns": {
                "session_frequency": "regular",
                "typical_session_length": "medium",
                "preferred_complexity": "medium"
            },
            "complexity_preference": "medium",
            "important_context": "Regular user with consistent engagement",
            "recurring_themes": [],
            "engagement_indicators": {
                "activity_level": "medium",
                "goal_completion": "good"
            },
            "growth_opportunities": [],
            "behavioral_insights": []
        }
    
    async def _create_or_update_summary(
        self,
        db: Session,
        user_id: int,
        period: str,
        period_start: datetime,
        period_end: datetime,
        user_data: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> UserHistorySummary:
        """Create or update user history summary in database."""
        try:
            # Check for existing summary to update
            existing = db.query(UserHistorySummary).filter(
                UserHistorySummary.user_id == user_id,
                UserHistorySummary.summary_period == period
            ).first()
            
            if existing:
                # Update existing summary
                existing.period_start = period_start
                existing.period_end = period_end
                existing.version += 1
                existing.total_sessions = user_data['total_sessions']
                existing.total_messages = user_data['total_messages']
                existing.total_tokens_used = user_data['total_tokens']
                existing.primary_domains = analysis_results['primary_domains']
                existing.frequent_topics = analysis_results['frequent_topics']
                existing.key_preferences = analysis_results['key_preferences']
                existing.skill_areas = analysis_results['skill_areas']
                existing.preferred_tools = analysis_results['preferred_tools']
                existing.interaction_patterns = analysis_results['interaction_patterns']
                existing.complexity_preference = analysis_results['complexity_preference']
                existing.executive_summary = analysis_results['executive_summary']
                existing.important_context = analysis_results['important_context']
                existing.recurring_themes = analysis_results['recurring_themes']
                existing.satisfaction_indicators = analysis_results['engagement_indicators']
                existing.updated_at = datetime.utcnow()
                
                summary = existing
            else:
                # Create new summary
                summary = UserHistorySummary(
                    user_id=user_id,
                    summary_period=period,
                    period_start=period_start,
                    period_end=period_end,
                    total_sessions=user_data['total_sessions'],
                    total_messages=user_data['total_messages'],
                    total_tokens_used=user_data['total_tokens'],
                    primary_domains=analysis_results['primary_domains'],
                    frequent_topics=analysis_results['frequent_topics'],
                    key_preferences=analysis_results['key_preferences'],
                    skill_areas=analysis_results['skill_areas'],
                    preferred_tools=analysis_results['preferred_tools'],
                    interaction_patterns=analysis_results['interaction_patterns'],
                    complexity_preference=analysis_results['complexity_preference'],
                    executive_summary=analysis_results['executive_summary'],
                    important_context=analysis_results['important_context'],
                    recurring_themes=analysis_results['recurring_themes'],
                    satisfaction_indicators=analysis_results['engagement_indicators']
                )
                
                db.add(summary)
            
            db.commit()
            db.refresh(summary)
            
            logger.info(f"Successfully saved user summary for user {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error saving user summary: {e}", exc_info=True)
            db.rollback()
            raise
    
    async def get_user_summary(
        self, 
        db: Session, 
        user_id: int, 
        period: str = "all_time"
    ) -> Optional[UserHistorySummary]:
        """Get existing user summary or generate new one if needed."""
        try:
            # First try to get existing summary
            summary = await self._get_existing_summary(db, user_id, period)
            
            if summary:
                return summary
            
            # Generate new summary if none exists
            return await self.generate_user_summary(db, user_id, period)
            
        except Exception as e:
            logger.error(f"Error getting user summary: {e}", exc_info=True)
            return None
    
    async def schedule_summary_updates(self, db: Session) -> None:
        """Schedule summary updates for all active users."""
        try:
            logger.info("Starting scheduled summary updates")
            
            # Get active users who have had recent activity
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            active_users = db.query(User.id).join(ChatMessage).filter(
                ChatMessage.created_at >= cutoff_date
            ).distinct().all()
            
            tasks = []
            for user_tuple in active_users:
                user_id = user_tuple[0]
                task = asyncio.create_task(
                    self.generate_user_summary(db, user_id, "weekly")
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for result in results if not isinstance(result, Exception))
            logger.info(f"Completed scheduled updates: {successful}/{len(tasks)} successful")
            
        except Exception as e:
            logger.error(f"Error in scheduled summary updates: {e}", exc_info=True)


# Global instance
user_history_service = UserHistorySummarizationService()