"""
Mission-Aligned Suggestions Service
Generates proactive suggestions to help users further their mission statement
by analyzing their calendar, tasks, and opportunities.
Now uses LangGraph for automatic progress monitoring.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field

from shared.database.models import User, Task, Event, Document, SemanticInsight, AIAnalysisHistory
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.smart_ai_models import TokenMetrics
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class MissionSuggestionsState(BaseModel):
    """State object for the mission suggestions workflow."""
    # Input data
    user_id: int
    session_id: str
    
    # Workflow state data
    user_context: Dict[str, Any] = Field(default_factory=dict)
    current_opportunities: Dict[str, Any] = Field(default_factory=dict)
    calendar_analysis: Dict[str, Any] = Field(default_factory=dict)
    
    # Results
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    token_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class MissionSuggestionsService:
    """
    Service for generating proactive mission-aligned suggestions based on user profile,
    calendar, tasks, and opportunities.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
    async def generate_mission_suggestions(self, user_id: int, 
                                         session_id: str) -> Tuple[List[Dict[str, Any]], TokenMetrics]:
        """
        Generate proactive suggestions to help user further their mission statement.
        
        Args:
            user_id: The user ID
            session_id: The session ID for logging
            
        Returns:
            Tuple of (suggestions_list, token_metrics)
        """
        try:
            # Get user profile and mission data
            user_context = await self._get_user_context(user_id)
            
            if not user_context or not user_context.get("mission_statement"):
                logger.info(f"No mission statement found for user {user_id}")
                return [], TokenMetrics()
            
            # Get current opportunities and calendar
            current_opportunities = await self._get_current_opportunities(user_id)
            calendar_analysis = await self._get_calendar_analysis(user_id)
            
            # Generate mission-aligned suggestions
            suggestions, token_metrics = await self._analyze_mission_opportunities(
                user_context, current_opportunities, calendar_analysis, session_id
            )
            
            # Store suggestions in database
            await self._store_suggestions(user_id, suggestions, user_context)
            
            return suggestions, token_metrics
            
        except Exception as e:
            logger.error(f"Error generating mission suggestions: {e}", exc_info=True)
            return [], TokenMetrics()
    
    async def _get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive user context for mission analysis."""
        try:
            with next(get_db()) as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None
                
                return {
                    "user_id": user.id,
                    "mission_statement": user.mission_statement,
                    "personal_goals": user.personal_goals,
                    "work_style_preferences": user.work_style_preferences,
                    "productivity_patterns": user.productivity_patterns,
                    "project_preferences": user.project_preferences,
                    "interview_insights": user.interview_insights,
                    "timezone": user.timezone or "UTC"
                }
                
        except Exception as e:
            logger.error(f"Error getting user context: {e}", exc_info=True)
            return None
    
    async def _get_current_opportunities(self, user_id: int) -> Dict[str, Any]:
        """Get current tasks, documents, and opportunities for analysis."""
        try:
            with next(get_db()) as db:
                # Get active tasks
                active_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status.in_(["pending", "in_progress"])
                ).order_by(Task.priority.desc(), Task.created_at.desc()).limit(20).all()
                
                # Get recent documents
                recent_docs = db.query(Document).filter(
                    Document.user_id == user_id
                ).order_by(Document.created_at.desc()).limit(10).all()
                
                # Get high-priority incomplete tasks
                priority_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.priority >= 7,
                    Task.status != "completed"
                ).order_by(Task.priority.desc()).limit(10).all()
                
                # Get tasks with semantic analysis
                semantic_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.semantic_category.isnot(None)
                ).order_by(Task.created_at.desc()).limit(15).all()
                
                return {
                    "active_tasks": [
                        {
                            "id": str(task.id),
                            "title": task.title,
                            "description": task.description,
                            "priority": task.priority,
                            "status": task.status,
                            "due_date": task.due_date.isoformat() if task.due_date else None,
                            "semantic_category": task.semantic_category,
                            "semantic_keywords": task.semantic_keywords,
                            "estimated_duration": task.estimated_duration_minutes
                        }
                        for task in active_tasks
                    ],
                    "recent_documents": [
                        {
                            "id": str(doc.id),
                            "title": doc.title,
                            "content_type": doc.content_type,
                            "semantic_keywords": doc.semantic_keywords,
                            "semantic_category": doc.semantic_category,
                            "created_at": doc.created_at.isoformat()
                        }
                        for doc in recent_docs
                    ],
                    "priority_tasks": [
                        {
                            "id": str(task.id),
                            "title": task.title,
                            "description": task.description,
                            "priority": task.priority,
                            "semantic_category": task.semantic_category
                        }
                        for task in priority_tasks
                    ],
                    "semantic_tasks": [
                        {
                            "id": str(task.id),
                            "title": task.title,
                            "semantic_category": task.semantic_category,
                            "semantic_summary": task.semantic_summary
                        }
                        for task in semantic_tasks
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting current opportunities: {e}", exc_info=True)
            return {}
    
    async def _get_calendar_analysis(self, user_id: int) -> Dict[str, Any]:
        """Get calendar analysis for the next 7 days."""
        try:
            with next(get_db()) as db:
                # Get events for the next 7 days
                start_date = datetime.now()
                end_date = start_date + timedelta(days=7)
                
                upcoming_events = db.query(Event).filter(
                    Event.user_id == user_id,
                    Event.event_date >= start_date,
                    Event.event_date <= end_date
                ).order_by(Event.event_date).all()
                
                # Analyze calendar patterns
                calendar_data = {
                    "upcoming_events": [
                        {
                            "id": str(event.id),
                            "title": event.title,
                            "description": event.description,
                            "event_date": event.event_date.isoformat(),
                            "duration_minutes": event.duration_minutes,
                            "semantic_category": event.semantic_category,
                            "semantic_keywords": event.semantic_keywords,
                            "movability_score": event.movability_score
                        }
                        for event in upcoming_events
                    ],
                    "total_events": len(upcoming_events),
                    "busy_days": self._analyze_busy_days(upcoming_events),
                    "free_time_blocks": self._analyze_free_time(upcoming_events)
                }
                
                return calendar_data
                
        except Exception as e:
            logger.error(f"Error getting calendar analysis: {e}", exc_info=True)
            return {}
    
    def _analyze_busy_days(self, events: List[Event]) -> List[str]:
        """Analyze which days are busy based on event density."""
        day_counts = {}
        for event in events:
            day = event.event_date.date().isoformat()
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Consider days with 3+ events as busy
        return [day for day, count in day_counts.items() if count >= 3]
    
    def _analyze_free_time(self, events: List[Event]) -> List[str]:
        """Analyze potential free time blocks."""
        # Simple analysis - could be more sophisticated
        busy_days = set()
        for event in events:
            busy_days.add(event.event_date.date())
        
        free_days = []
        for i in range(7):
            check_date = datetime.now().date() + timedelta(days=i)
            if check_date not in busy_days:
                free_days.append(check_date.isoformat())
        
        return free_days
    
    async def _analyze_mission_opportunities(self, user_context: Dict[str, Any], 
                                          opportunities: Dict[str, Any],
                                          calendar_analysis: Dict[str, Any],
                                          session_id: str) -> Tuple[List[Dict[str, Any]], TokenMetrics]:
        """Analyze mission alignment and generate suggestions."""
        try:
            mission_statement = user_context.get("mission_statement", "")
            personal_goals = user_context.get("personal_goals", {})
            
            analysis_prompt = f"""
You are a mission-aligned productivity assistant. Analyze the user's current situation and provide 3-5 proactive suggestions to help them further their mission statement.

USER'S MISSION STATEMENT:
{mission_statement}

PERSONAL GOALS:
{personal_goals}

CURRENT TASKS AND OPPORTUNITIES:
Active Tasks: {len(opportunities.get('active_tasks', []))} tasks
Priority Tasks: {opportunities.get('priority_tasks', [])}
Recent Documents: {opportunities.get('recent_documents', [])}

CALENDAR ANALYSIS:
Upcoming Events: {calendar_analysis.get('total_events', 0)} events in next 7 days
Busy Days: {calendar_analysis.get('busy_days', [])}
Free Time Blocks: {calendar_analysis.get('free_time_blocks', [])}

TASK ANALYSIS:
{self._format_task_analysis(opportunities.get('active_tasks', []))}

Based on this analysis, provide 3-5 specific, actionable suggestions that would help the user advance their mission statement. Consider:

1. **Mission Alignment**: How can current tasks be optimized to better serve the mission?
2. **Time Optimization**: How can calendar time be better utilized for mission-critical activities?
3. **Priority Adjustment**: What tasks should be prioritized based on mission alignment?
4. **New Opportunities**: What new tasks or activities would advance the mission?
5. **Resource Optimization**: How can existing resources be better leveraged?

For each suggestion, provide:
- A clear, actionable title
- A detailed description of the action
- Why it aligns with the mission
- Expected impact (high/medium/low)
- Estimated time commitment
- Priority level (1-5)

Format your response as JSON:
{{
  "suggestions": [
    {{
      "title": "Clear, actionable title",
      "description": "Detailed description of the suggested action",
      "mission_alignment": "How this aligns with the user's mission",
      "expected_impact": "high/medium/low",
      "time_commitment": "Estimated time needed",
      "priority": 1-5,
      "category": "optimization/new_task/priority_adjustment/time_management",
      "actionable_steps": ["Step 1", "Step 2", "Step 3"]
    }}
  ]
}}
"""

            messages = [
                {"role": "system", "content": "You are a mission-aligned productivity assistant focused on helping users achieve their stated mission and goals through strategic action recommendations."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, token_metrics = await invoke_llm_with_tokens(
                messages,
                self.settings.OLLAMA_GENERATION_MODEL_NAME,
                category="mission_suggestions"
            )
            
            # Parse suggestions
            suggestions = self._parse_suggestions_response(response)
            
            return suggestions, token_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing mission opportunities: {e}", exc_info=True)
            return [], TokenMetrics()
    
    def _format_task_analysis(self, tasks: List[Dict[str, Any]]) -> str:
        """Format task analysis for the LLM prompt."""
        if not tasks:
            return "No active tasks found."
        
        analysis = []
        for task in tasks[:10]:  # Limit to 10 tasks for prompt efficiency
            analysis.append(f"• {task['title']} (Priority: {task['priority']}, Status: {task['status']})")
            if task.get('semantic_category'):
                analysis.append(f"  Category: {task['semantic_category']}")
        
        return "\n".join(analysis)
    
    def _parse_suggestions_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the LLM response into structured suggestions."""
        try:
            import json
            
            # Try to find JSON in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                if "suggestions" in parsed:
                    return parsed["suggestions"]
            
            # Fallback: parse manually if JSON parsing fails
            return self._parse_suggestions_manually(response)
            
        except Exception as e:
            logger.error(f"Error parsing suggestions response: {e}", exc_info=True)
            return self._parse_suggestions_manually(response)
    
    def _parse_suggestions_manually(self, response: str) -> List[Dict[str, Any]]:
        """Manual parsing fallback for suggestions."""
        suggestions = []
        
        # Simple fallback - create a single suggestion from the response
        suggestions.append({
            "title": "Mission-Aligned Action",
            "description": response[:500] + "..." if len(response) > 500 else response,
            "mission_alignment": "Generated based on mission statement analysis",
            "expected_impact": "medium",
            "time_commitment": "To be determined",
            "priority": 3,
            "category": "optimization",
            "actionable_steps": ["Review the detailed analysis", "Identify specific actions", "Create implementation plan"]
        })
        
        return suggestions
    
    async def _store_suggestions(self, user_id: int, suggestions: List[Dict[str, Any]], 
                                user_context: Dict[str, Any]):
        """Store mission suggestions in the database."""
        try:
            with next(get_db()) as db:
                # Store in SemanticInsight
                insight = SemanticInsight(
                    user_id=user_id,
                    content_type="mission_suggestions",
                    insight_type="proactive_suggestions",
                    insight_value={
                        "suggestions": suggestions,
                        "generated_at": datetime.now().isoformat(),
                        "mission_context": user_context.get("mission_statement", ""),
                        "suggestion_count": len(suggestions)
                    },
                    confidence_score=0.8,  # High confidence in mission-aligned suggestions
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME
                )
                db.add(insight)
                
                # Store in AIAnalysisHistory
                history = AIAnalysisHistory(
                    user_id=user_id,
                    analysis_type="mission_suggestions",
                    input_data={
                        "mission_statement": user_context.get("mission_statement", ""),
                        "personal_goals": user_context.get("personal_goals", {}),
                        "analysis_timestamp": datetime.now().isoformat()
                    },
                    output_data={
                        "suggestions": suggestions,
                        "suggestion_count": len(suggestions)
                    },
                    model_used=self.settings.OLLAMA_GENERATION_MODEL_NAME
                )
                db.add(history)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing mission suggestions: {e}", exc_info=True)
    
    async def get_recent_suggestions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent mission suggestions for a user."""
        try:
            with next(get_db()) as db:
                insights = db.query(SemanticInsight).filter(
                    SemanticInsight.user_id == user_id,
                    SemanticInsight.insight_type == "proactive_suggestions"
                ).order_by(SemanticInsight.created_at.desc()).limit(limit).all()
                
                return [
                    {
                        "id": str(insight.id),
                        "created_at": insight.created_at.isoformat(),
                        "suggestions": insight.insight_value.get("suggestions", []),
                        "suggestion_count": insight.insight_value.get("suggestion_count", 0)
                    }
                    for insight in insights
                ]
                
        except Exception as e:
            logger.error(f"Error getting recent suggestions: {e}", exc_info=True)
            return []

    def _format_suggestions_for_chat(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format mission suggestions for chat display."""
        if not suggestions:
            return "I analyzed your mission and current activities, but couldn't generate specific suggestions at this time."
        
        formatted_text = f"🎯 **Mission-Aligned Suggestions** ({len(suggestions)} recommendations)\n\n"
        
        for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to top 5
            title = suggestion.get("title", "Unnamed suggestion")
            description = suggestion.get("description", "")
            impact = suggestion.get("expected_impact", "medium").upper()
            priority = suggestion.get("priority", 3)
            
            # Add priority emoji
            priority_emoji = "🔥" if priority >= 4 else "⭐" if priority >= 3 else "💡"
            impact_emoji = "🚀" if impact == "HIGH" else "📈" if impact == "MEDIUM" else "💬"
            
            formatted_text += f"{priority_emoji} **{title}**\n"
            formatted_text += f"{impact_emoji} *{impact} impact* | Priority: {priority}/5\n"
            
            if description:
                # Truncate long descriptions
                desc_preview = description[:150] + "..." if len(description) > 150 else description
                formatted_text += f"{desc_preview}\n"
            
            formatted_text += "\n"
        
        formatted_text += "💡 These suggestions are based on your mission statement and current activity patterns."
        
        return formatted_text

    async def generate_mission_suggestions_with_progress(self, user_id: int, 
                                                       session_id: str) -> Tuple[List[Dict[str, Any]], TokenMetrics]:
        """
        Generate mission suggestions using LangGraph with automatic progress monitoring.
        
        Args:
            user_id: The user ID
            session_id: The session ID for logging
            
        Returns:
            Tuple of (suggestions_list, token_metrics)
        """
        try:
            # Create mission suggestions state
            suggestions_state = MissionSuggestionsState(
                user_id=user_id,
                session_id=session_id
            )
            
            logger.info(f"Starting LangGraph mission suggestions workflow for user {user_id}")
            
            # Get progress manager for automatic broadcasting
            from worker.services.progress_manager import progress_manager
            
            # Broadcast workflow start
            await progress_manager.broadcast_workflow_start(
                session_id, 
                f"Generating mission-aligned suggestions"
            )
            
            # Run the suggestions workflow with astream for progress monitoring
            config = RunnableConfig(recursion_limit=10)
            workflow_start_time = datetime.now()
            nodes_executed = 0
            
            final_state = None
            async for event in compiled_suggestions_workflow.astream(suggestions_state.model_dump(), config=config):
                nodes_executed += 1
                
                for node_name, node_state in event.items():
                    # Broadcast automatic progress update for this node
                    try:
                        node_execution_time = (datetime.now() - workflow_start_time).total_seconds()
                        await progress_manager.broadcast_node_transition(
                            session_id, f"suggestions_{node_name}", node_state, node_execution_time
                        )
                        logger.debug(f"Broadcasted suggestions progress for node: {node_name}")
                    except Exception as e:
                        logger.warning(f"Failed to broadcast suggestions progress for {node_name}: {e}")
                
                # Store the final state
                final_state = event
            
            # Calculate total execution time
            total_execution_time = (datetime.now() - workflow_start_time).total_seconds()
            
            # Extract final results from the last state
            if final_state:
                last_key = list(final_state.keys())[-1]
                final_suggestions_state = final_state[last_key]
                
                # Broadcast workflow completion
                suggestions_count = len(final_suggestions_state.get("suggestions", []))
                await progress_manager.broadcast_workflow_complete(
                    session_id, 
                    f"Generated {suggestions_count} mission-aligned suggestions",
                    total_execution_time, 
                    nodes_executed
                )
                
                # Post mission suggestions directly to chat if we have results
                suggestions = final_suggestions_state.get("suggestions", [])
                if suggestions and session_id:
                    from worker.services.progress_manager import AgentNames
                    
                    # Format suggestions as a nice message
                    suggestion_text = self._format_suggestions_for_chat(suggestions)
                    await progress_manager.broadcast_agent_message(
                        session_id,
                        AgentNames.MISSION_ANALYZER,
                        suggestion_text,
                        agent_type="mission analysis",
                        metadata={"suggestions_count": len(suggestions)},
                        formatted=True
                    )
                
                # Format result to match expected structure
                suggestions = final_suggestions_state.get("suggestions", [])
                token_metrics = TokenMetrics(**final_suggestions_state.get("token_metrics", {}))
                
                return suggestions, token_metrics
            else:
                # Fallback if no final state
                logger.warning("No final state from suggestions workflow")
                return [], TokenMetrics()
            
        except Exception as e:
            logger.error(f"Error in LangGraph suggestions workflow: {e}", exc_info=True)
            
            # Broadcast error if possible
            try:
                from worker.services.progress_manager import progress_manager
                await progress_manager.broadcast_workflow_complete(
                    session_id,
                    f"Suggestions failed: {str(e)}",
                    0.0,
                    0
                )
            except:
                pass
            
            # Fallback to original method
            logger.info("Falling back to original suggestions method")
            return await self.generate_mission_suggestions(user_id, session_id)


# --- LangGraph Workflow Nodes ---

async def get_user_context_node(state: MissionSuggestionsState) -> Dict[str, Any]:
    """Get comprehensive user context for mission analysis."""
    try:
        service = mission_suggestions_service
        user_context = await service._get_user_context(state.user_id)
        
        if not user_context or not user_context.get("mission_statement"):
            return {
                "error_message": "No mission statement found",
                "user_context": {}
            }
        
        return {"user_context": user_context}
        
    except Exception as e:
        logger.error(f"Error getting user context: {e}")
        return {
            "error_message": f"Error getting user context: {str(e)}",
            "user_context": {}
        }


async def get_opportunities_node(state: MissionSuggestionsState) -> Dict[str, Any]:
    """Get current opportunities and tasks."""
    try:
        service = mission_suggestions_service
        opportunities = await service._get_current_opportunities(state.user_id)
        return {"current_opportunities": opportunities}
        
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}")
        return {"current_opportunities": {}}


async def get_calendar_analysis_node(state: MissionSuggestionsState) -> Dict[str, Any]:
    """Get calendar analysis."""
    try:
        service = mission_suggestions_service
        calendar_analysis = await service._get_calendar_analysis(state.user_id)
        return {"calendar_analysis": calendar_analysis}
        
    except Exception as e:
        logger.error(f"Error getting calendar analysis: {e}")
        return {"calendar_analysis": {}}


async def analyze_mission_opportunities_node(state: MissionSuggestionsState) -> Dict[str, Any]:
    """Analyze mission alignment and generate suggestions."""
    try:
        service = mission_suggestions_service
        suggestions, token_metrics = await service._analyze_mission_opportunities(
            state.user_context, 
            state.current_opportunities, 
            state.calendar_analysis, 
            state.session_id
        )
        
        return {
            "suggestions": suggestions,
            "token_metrics": token_metrics.model_dump() if hasattr(token_metrics, 'model_dump') else token_metrics
        }
        
    except Exception as e:
        logger.error(f"Error analyzing mission opportunities: {e}")
        return {
            "suggestions": [],
            "token_metrics": {},
            "error_message": f"Analysis error: {str(e)}"
        }


async def store_suggestions_node(state: MissionSuggestionsState) -> Dict[str, Any]:
    """Store the generated suggestions in the database."""
    try:
        service = mission_suggestions_service
        await service._store_suggestions(state.user_id, state.suggestions, state.user_context)
        return {}  # No state changes needed
        
    except Exception as e:
        logger.error(f"Error storing suggestions: {e}")
        return {"error_message": f"Storage error: {str(e)}"}


def should_continue_workflow(state: MissionSuggestionsState) -> str:
    """Decide whether to continue the workflow or end due to errors."""
    if state.error_message:
        logger.info(f"Stopping workflow due to error: {state.error_message}")
        return "__end__"
    
    if not state.user_context:
        logger.info("No user context available, ending workflow")
        return "__end__"
        
    return "get_opportunities"


# Create the suggestions workflow graph
suggestions_workflow = StateGraph(MissionSuggestionsState)

# Add nodes
suggestions_workflow.add_node("get_user_context", RunnableLambda(get_user_context_node))  # type: ignore
suggestions_workflow.add_node("get_opportunities", RunnableLambda(get_opportunities_node))  # type: ignore
suggestions_workflow.add_node("get_calendar_analysis", RunnableLambda(get_calendar_analysis_node))  # type: ignore
suggestions_workflow.add_node("analyze_opportunities", RunnableLambda(analyze_mission_opportunities_node))  # type: ignore
suggestions_workflow.add_node("store_suggestions", RunnableLambda(store_suggestions_node))  # type: ignore

# Set entry point
suggestions_workflow.set_entry_point("get_user_context")

# Add edges
suggestions_workflow.add_conditional_edges(
    "get_user_context",
    should_continue_workflow,
    {
        "get_opportunities": "get_opportunities",
        "__end__": END
    }
)
suggestions_workflow.add_edge("get_opportunities", "get_calendar_analysis") 
suggestions_workflow.add_edge("get_calendar_analysis", "analyze_opportunities")
suggestions_workflow.add_edge("analyze_opportunities", "store_suggestions")
suggestions_workflow.add_edge("store_suggestions", END)

# Compile the workflow
compiled_suggestions_workflow = suggestions_workflow.compile()


# Singleton instance
mission_suggestions_service = MissionSuggestionsService()