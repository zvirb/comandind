"""
Chat Storage Service
Handles storage of chat messages to Qdrant and session summaries to PostgreSQL
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.orm import Session

from worker.services.qdrant_service import QdrantService
from worker.services.ollama_service import invoke_llm_with_tokens
from shared.database.models import ChatMessage, ChatSessionSummary, User
from shared.utils.database_setup import get_db
from worker.graph_types import GraphState

logger = logging.getLogger(__name__)


class ChatStorageService:
    """Service for storing chat messages and generating session summaries."""
    
    def __init__(self):
        self.qdrant_service = QdrantService()
    
    async def store_chat_session(self, state: GraphState, session_start_time: datetime, 
                                session_end_time: datetime) -> bool:
        """
        Store complete chat session: individual messages to Qdrant and summary to PostgreSQL.
        """
        try:
            logger.info(f"Storing chat session {state.session_id} with {len(state.messages)} messages")
            
            # Store individual messages to both PostgreSQL and Qdrant concurrently
            message_storage_tasks = []
            for i, message in enumerate(state.messages):
                task = asyncio.create_task(
                    self._store_individual_message(state, message, i, session_start_time)
                )
                message_storage_tasks.append(task)
            
            # Generate and store session summary concurrently
            summary_task = asyncio.create_task(
                self._generate_and_store_session_summary(state, session_start_time, session_end_time)
            )
            
            # Wait for all storage operations to complete
            message_results = await asyncio.gather(*message_storage_tasks, return_exceptions=True)
            summary_result = await summary_task
            
            # Check for failures
            failed_messages = [i for i, result in enumerate(message_results) if isinstance(result, Exception)]
            if failed_messages:
                logger.warning(f"Failed to store {len(failed_messages)} messages from session {state.session_id}")
            
            successful_messages = len(message_results) - len(failed_messages)
            logger.info(f"Successfully stored {successful_messages}/{len(state.messages)} messages and session summary")
            
            return summary_result and successful_messages > 0
            
        except Exception as e:
            logger.error(f"Error storing chat session {state.session_id}: {e}", exc_info=True)
            return False
    
    async def _store_individual_message(self, state: GraphState, message: BaseMessage, 
                                      message_order: int, session_start_time: datetime) -> bool:
        """Store individual message to both PostgreSQL and Qdrant."""
        try:
            if not hasattr(message, 'content') or not message.content:
                return True  # Skip empty messages
            
            # Determine message type
            message_type = "human" if isinstance(message, HumanMessage) else "ai"
            if hasattr(message, 'type'):
                message_type = message.type
            
            # Generate unique message ID
            message_id = str(uuid.uuid4())
            
            # Store to PostgreSQL
            postgres_success = await self._store_message_to_postgres(
                message_id=message_id,
                session_id=state.session_id,
                user_id=int(state.user_id) if state.user_id else None,
                message_type=message_type,
                content=message.content,
                message_order=message_order,
                conversation_domain=state.conversation_domain,
                tool_used=state.selected_tool,
                plan_step=state.plan_step if hasattr(state, 'plan_step') else None,
                confidence_score=state.confidence_score if hasattr(state, 'confidence_score') else None
            )
            
            # Store to Qdrant for semantic search
            qdrant_point_id = None
            if postgres_success and state.user_id:
                try:
                    qdrant_point_id = await self.qdrant_service.store_chat_message(
                        message_id=message_id,
                        content=message.content,
                        user_id=int(state.user_id),
                        session_id=state.session_id,
                        message_type=message_type,
                        message_order=message_order,
                        conversation_domain=state.conversation_domain,
                        tool_used=state.selected_tool,
                        plan_step=state.plan_step if hasattr(state, 'plan_step') else None
                    )
                    
                    # Update PostgreSQL record with Qdrant point ID
                    if qdrant_point_id:
                        await self._update_message_qdrant_id(message_id, qdrant_point_id)
                        
                except Exception as e:
                    logger.warning(f"Failed to store message to Qdrant: {e}")
                    # Continue even if Qdrant storage fails
            
            return postgres_success
            
        except Exception as e:
            logger.error(f"Error storing individual message: {e}", exc_info=True)
            return False
    
    async def _store_message_to_postgres(self, message_id: str, session_id: str, user_id: Optional[int],
                                       message_type: str, content: str, message_order: int,
                                       conversation_domain: Optional[str], tool_used: Optional[str],
                                       plan_step: Optional[int], confidence_score: Optional[float]) -> bool:
        """Store message to PostgreSQL database."""
        try:
            def store_message():
                with next(get_db()) as db:
                    chat_message = ChatMessage(
                        id=uuid.UUID(message_id),
                        session_id=session_id,
                        user_id=user_id,
                        message_type=message_type,
                        content=content,
                        message_order=message_order,
                        conversation_domain=conversation_domain,
                        tool_used=tool_used,
                        plan_step=plan_step,
                        confidence_score=confidence_score
                    )
                    
                    db.add(chat_message)
                    db.commit()
                    return True
            
            # Run database operation in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, store_message)
            
        except Exception as e:
            logger.error(f"Error storing message to PostgreSQL: {e}", exc_info=True)
            return False
    
    async def _update_message_qdrant_id(self, message_id: str, qdrant_point_id: str) -> bool:
        """Update message record with Qdrant point ID."""
        try:
            def update_message():
                with next(get_db()) as db:
                    message = db.query(ChatMessage).filter(ChatMessage.id == uuid.UUID(message_id)).first()
                    if message:
                        message.qdrant_point_id = qdrant_point_id
                        db.commit()
                        return True
                    return False
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, update_message)
            
        except Exception as e:
            logger.error(f"Error updating message Qdrant ID: {e}", exc_info=True)
            return False
    
    async def _generate_and_store_session_summary(self, state: GraphState, 
                                                session_start_time: datetime,
                                                session_end_time: datetime) -> bool:
        """Generate comprehensive session summary and store to PostgreSQL."""
        try:
            logger.info(f"Generating session summary for {state.session_id}")
            
            # Build conversation text for analysis
            conversation_text = []
            for message in state.messages:
                if hasattr(message, 'type') and hasattr(message, 'content'):
                    role = "User" if message.type == "human" else "Assistant"
                    conversation_text.append(f"{role}: {message.content}")
            
            full_conversation = "\n".join(conversation_text)
            
            # Generate comprehensive summary using LLM
            summary_data = await self._generate_session_analysis(full_conversation, state)
            
            # Store summary to PostgreSQL
            return await self._store_session_summary_to_postgres(
                state, session_start_time, session_end_time, summary_data
            )
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}", exc_info=True)
            return False
    
    async def _generate_session_analysis(self, conversation_text: str, state: GraphState) -> Dict[str, Any]:
        """Use LLM to analyze conversation and extract structured summary data."""
        try:
            analysis_prompt = f"""Analyze this conversation and extract structured information for storage.

**Conversation:**
{conversation_text}

**Session Context:**
- Domain: {state.conversation_domain or 'general'}
- Tools used: {state.selected_tool or 'none'}
- Expert questions: {len(state.expert_questions) if hasattr(state, 'expert_questions') else 0}

**Analysis Required:**
Extract and format as JSON:
{{
  "summary": "Comprehensive 2-3 sentence summary of the conversation",
  "key_topics": ["topic1", "topic2", "topic3"],
  "decisions_made": ["decision1", "decision2"],
  "user_preferences": {{"preference_category": "preference_value"}},
  "tools_used": ["tool1", "tool2"],
  "complexity_level": "low|medium|high",
  "resolution_status": "completed|partial|interrupted",
  "search_keywords": ["keyword1", "keyword2", "keyword3"],
  "follow_up_suggested": true/false,
  "follow_up_tasks": ["task1", "task2"]
}}

**Guidelines:**
- Summary should capture main purpose and outcome
- Key topics should be specific and searchable
- Decisions should be actionable choices made by user
- User preferences should capture stated likes/dislikes/requirements
- Search keywords should help find this conversation later
- Follow-up tasks should be specific actionable items

Analyze the conversation:"""

            # Use reflection model for analysis
            model_name = state.reflection_model if hasattr(state, 'reflection_model') else "llama3.2:3b"
            
            messages = [
                {"role": "system", "content": "You are an expert conversation analyzer. Extract structured information from conversations and format as valid JSON."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages,
                model_name,
                category="session_analysis"
            )
            
            # Parse JSON response
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
                        "summary": analysis_data.get("summary", "Conversation completed"),
                        "key_topics": analysis_data.get("key_topics", []),
                        "decisions_made": analysis_data.get("decisions_made", []),
                        "user_preferences": analysis_data.get("user_preferences", {}),
                        "tools_used": analysis_data.get("tools_used", []),
                        "complexity_level": analysis_data.get("complexity_level", "medium"),
                        "resolution_status": analysis_data.get("resolution_status", "completed"),
                        "search_keywords": analysis_data.get("search_keywords", []),
                        "follow_up_suggested": analysis_data.get("follow_up_suggested", False),
                        "follow_up_tasks": analysis_data.get("follow_up_tasks", [])
                    }
                    
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM analysis as JSON, using fallback")
            
            # Fallback analysis
            return {
                "summary": f"Conversation in {state.conversation_domain or 'general'} domain with {len(state.messages)} messages",
                "key_topics": [state.conversation_domain] if state.conversation_domain else [],
                "decisions_made": [],
                "user_preferences": {},
                "tools_used": [state.selected_tool] if state.selected_tool else [],
                "complexity_level": "medium",
                "resolution_status": "completed",
                "search_keywords": [state.conversation_domain] if state.conversation_domain else [],
                "follow_up_suggested": False,
                "follow_up_tasks": []
            }
            
        except Exception as e:
            logger.error(f"Error in LLM session analysis: {e}", exc_info=True)
            # Return minimal fallback data
            return {
                "summary": "Conversation completed",
                "key_topics": [],
                "decisions_made": [],
                "user_preferences": {},
                "tools_used": [],
                "complexity_level": "medium", 
                "resolution_status": "completed",
                "search_keywords": [],
                "follow_up_suggested": False,
                "follow_up_tasks": []
            }
    
    async def _store_session_summary_to_postgres(self, state: GraphState,
                                               session_start_time: datetime,
                                               session_end_time: datetime,
                                               summary_data: Dict[str, Any]) -> bool:
        """Store session summary to PostgreSQL."""
        try:
            def store_summary():
                with next(get_db()) as db:
                    # Calculate metrics
                    message_count = len(state.messages)
                    total_tokens = getattr(state.token_usage, 'total_tokens', None) if hasattr(state, 'token_usage') else None
                    plans_created = 1 if state.selected_tool == "PLANNER_TOOL_ID" else 0
                    expert_questions = len(state.expert_questions) if hasattr(state, 'expert_questions') else 0
                    
                    session_summary = ChatSessionSummary(
                        session_id=state.session_id,
                        user_id=int(state.user_id) if state.user_id else None,
                        started_at=session_start_time,
                        ended_at=session_end_time,
                        message_count=message_count,
                        total_tokens_used=total_tokens,
                        conversation_domain=state.conversation_domain,
                        summary=summary_data["summary"],
                        key_topics=summary_data["key_topics"],
                        decisions_made=summary_data["decisions_made"],
                        user_preferences=summary_data["user_preferences"],
                        tools_used=summary_data["tools_used"],
                        plans_created=plans_created,
                        expert_questions_asked=expert_questions,
                        complexity_level=summary_data["complexity_level"],
                        resolution_status=summary_data["resolution_status"],
                        search_keywords=summary_data["search_keywords"],
                        follow_up_suggested=summary_data["follow_up_suggested"],
                        follow_up_tasks=summary_data["follow_up_tasks"]
                    )
                    
                    db.add(session_summary)
                    db.commit()
                    return True
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, store_summary)
            
            if success:
                logger.info(f"Successfully stored session summary for {state.session_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error storing session summary to PostgreSQL: {e}", exc_info=True)
            return False
    
    async def search_chat_history(self, user_id: int, query: str, limit: int = 10,
                                content_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search user's chat history using semantic search."""
        try:
            # Default to searching chat messages
            if content_types is None:
                content_types = ["chat"]
            
            # Search Qdrant for relevant messages
            search_results = await self.qdrant_service.search_points(
                query_text=query,
                limit=limit,
                user_id=user_id,
                content_types=content_types
            )
            
            # Format results for return
            formatted_results = []
            for result in search_results:
                if hasattr(result, 'payload') and result.payload:
                    formatted_results.append({
                        "score": result.score,
                        "content": result.payload.get("text", ""),
                        "session_id": result.payload.get("session_id", ""),
                        "message_type": result.payload.get("message_type", ""),
                        "timestamp": result.payload.get("timestamp", ""),
                        "conversation_domain": result.payload.get("conversation_domain", ""),
                        "tool_used": result.payload.get("tool_used", "")
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching chat history: {e}", exc_info=True)
            return []


# Global instance
chat_storage_service = ChatStorageService()