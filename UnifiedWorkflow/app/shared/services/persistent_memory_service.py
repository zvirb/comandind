"""
Persistent Memory Service

Comprehensive memory system that combines:
1. Database-based chat context (conversation history)
2. Cross-chat persistent memory (user-specific context)
3. Semantic memory via Qdrant (meaningful context retrieval)

This service ensures that the AI has access to relevant context from:
- Current conversation history
- Previous conversations and patterns
- Semantically similar interactions
- User preferences and learned patterns
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, text

from shared.database.models import (
    User, ChatHistory, ChatMessage, ChatSessionSummary, 
    UserHistorySummary, Task, UserCategory
)
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.qdrant_service import QdrantService
from qdrant_client import models
from shared.services.user_history_summarization_service import UserHistorySummarizationService
from worker.utils.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class PersistentMemoryService:
    """
    Comprehensive memory service that maintains context across conversations.
    """
    
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.summarization_service = UserHistorySummarizationService()
        self.default_model = "llama3.2:3b"
        
        # Memory configuration
        self.max_conversation_history = 50  # Max messages to load from current session
        self.max_semantic_results = 10     # Max semantically similar messages
        self.max_summary_age_days = 7      # How recent summaries should be
        
    async def get_comprehensive_context(
        self, 
        user_id: int, 
        session_id: str, 
        current_message: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get comprehensive context from all memory sources.
        
        Returns:
            Dict containing:
            - conversation_history: Recent messages from current session
            - semantic_context: Semantically similar past interactions  
            - user_patterns: User-specific behavioral patterns and preferences
            - session_summary: Summary of current session if long
        """
        try:
            logger.info(f"Gathering comprehensive context for user {user_id}, session {session_id}")
            
            # Gather context from all sources in parallel
            context_tasks = [
                self._get_conversation_history(user_id, session_id, db),
                self._get_semantic_context(user_id, current_message, db),
                self._get_user_patterns(user_id, db),
                self._get_session_summary(user_id, session_id, db)
            ]
            
            results = await asyncio.gather(*context_tasks, return_exceptions=True)
            
            conversation_history = results[0] if not isinstance(results[0], Exception) else []
            semantic_context = results[1] if not isinstance(results[1], Exception) else []
            user_patterns = results[2] if not isinstance(results[2], Exception) else {}
            session_summary = results[3] if not isinstance(results[3], Exception) else None
            
            # Combine all context
            comprehensive_context = {
                "conversation_history": conversation_history,
                "semantic_context": semantic_context,
                "user_patterns": user_patterns,
                "session_summary": session_summary,
                "context_timestamp": datetime.utcnow().isoformat(),
                "context_sources": {
                    "conversation_messages": len(conversation_history),
                    "semantic_matches": len(semantic_context),
                    "has_user_patterns": bool(user_patterns),
                    "has_session_summary": session_summary is not None
                }
            }
            
            logger.info(f"Context gathered: {len(conversation_history)} messages, "
                       f"{len(semantic_context)} semantic matches, "
                       f"patterns: {bool(user_patterns)}")
            
            return comprehensive_context
            
        except Exception as e:
            logger.error(f"Error gathering comprehensive context: {e}", exc_info=True)
            return {"conversation_history": [], "semantic_context": [], "user_patterns": {}}
    
    async def _get_conversation_history(
        self, 
        user_id: int, 
        session_id: str, 
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history from current session."""
        try:
            # Get recent messages from current session
            chat_history = db.query(ChatHistory)\
                .filter(ChatHistory.session_id == session_id)\
                .order_by(desc(ChatHistory.created_at))\
                .limit(self.max_conversation_history)\
                .all()
            
            # Convert to message format
            messages = []
            for history_item in reversed(chat_history):  # Reverse to get chronological order
                if isinstance(history_item.message, dict):
                    messages.append({
                        "role": history_item.message.get("role", "user"),
                        "content": history_item.message.get("content", ""),
                        "timestamp": history_item.created_at.isoformat() if history_item.created_at else None
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def _get_semantic_context(
        self, 
        user_id: int, 
        current_message: str, 
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get semantically similar past interactions using Qdrant."""
        try:
            if not current_message.strip():
                return []
            
            # Generate embedding for current message
            embedding = await get_embeddings([current_message])
            if not embedding or not embedding[0]:
                logger.warning("Could not generate embedding for semantic search")
                return []
            
            # Search for similar messages in Qdrant
            client = await self.qdrant_service.client
            search_results = await client.search(
                collection_name="user_messages",
                query_vector=embedding[0],
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id", 
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=self.max_semantic_results,
                with_payload=True,
                score_threshold=0.7  # Only high-similarity matches
            )
            
            # Format results
            semantic_matches = []
            for result in search_results:
                if result.payload:
                    semantic_matches.append({
                        "content": result.payload.get("content", ""),
                        "response": result.payload.get("response", ""),
                        "timestamp": result.payload.get("timestamp"),
                        "similarity_score": result.score,
                        "session_id": result.payload.get("session_id", ""),
                        "context": result.payload.get("context", {})
                    })
            
            return semantic_matches
            
        except Exception as e:
            logger.error(f"Error getting semantic context: {e}")
            return []
    
    async def _get_user_patterns(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get user-specific patterns and preferences."""
        try:
            # Get user summary (patterns, preferences, etc.)
            user_summary = await self.summarization_service.generate_user_summary(
                db, user_id, period="last_30_days"
            )
            
            if user_summary:
                return {
                    "communication_style": user_summary.communication_preferences,
                    "interests": user_summary.primary_interests,
                    "work_patterns": user_summary.work_patterns,
                    "goals": user_summary.goals,
                    "preferences": user_summary.preferences,
                    "summary_generated": user_summary.created_at.isoformat(),
                    "summary_period": user_summary.summary_period
                }
            
            # Fallback: analyze recent activity patterns
            recent_messages = db.query(ChatMessage)\
                .filter(ChatMessage.user_id == user_id)\
                .filter(ChatMessage.created_at >= datetime.utcnow() - timedelta(days=30))\
                .order_by(desc(ChatMessage.created_at))\
                .limit(100)\
                .all()
            
            if recent_messages:
                # Extract basic patterns from recent activity
                patterns = await self._analyze_message_patterns(recent_messages)
                return patterns
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user patterns: {e}")
            return {}
    
    async def _get_session_summary(
        self, 
        user_id: int, 
        session_id: str, 
        db: Session
    ) -> Optional[str]:
        """Get summary of current session if it's long enough."""
        try:
            # Check if session has enough messages to warrant a summary
            message_count = db.query(func.count(ChatHistory.id))\
                .filter(ChatHistory.session_id == session_id)\
                .scalar()
            
            if message_count < 10:  # Not enough messages
                return None
            
            # Check if we already have a summary
            existing_summary = db.query(ChatSessionSummary)\
                .filter(ChatSessionSummary.session_id == session_id)\
                .first()
            
            if existing_summary:
                return existing_summary.summary
            
            # Generate new summary
            recent_messages = db.query(ChatHistory)\
                .filter(ChatHistory.session_id == session_id)\
                .order_by(ChatHistory.created_at)\
                .all()
            
            if len(recent_messages) >= 10:
                summary = await self._generate_session_summary(recent_messages)
                
                # Store the summary
                new_summary = ChatSessionSummary(
                    session_id=session_id,
                    user_id=user_id,
                    summary=summary,
                    message_count=len(recent_messages),
                    key_topics=[],  # Could be extracted from summary
                    sentiment="neutral"  # Could be analyzed
                )
                db.add(new_summary)
                db.commit()
                
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return None
    
    async def _analyze_message_patterns(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """Analyze patterns from recent messages."""
        try:
            # Extract basic patterns
            patterns = {
                "total_messages": len(messages),
                "avg_message_length": sum(len(msg.content) for msg in messages) / len(messages),
                "common_topics": [],
                "interaction_frequency": {},
                "preferred_tools": []
            }
            
            # Analyze interaction times
            for msg in messages:
                if msg.created_at:
                    hour = msg.created_at.hour
                    time_period = "morning" if 6 <= hour < 12 else \
                                "afternoon" if 12 <= hour < 18 else \
                                "evening" if 18 <= hour < 22 else "night"
                    patterns["interaction_frequency"][time_period] = \
                        patterns["interaction_frequency"].get(time_period, 0) + 1
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing message patterns: {e}")
            return {}
    
    async def _generate_session_summary(self, messages: List[ChatHistory]) -> str:
        """Generate a summary of the current session."""
        try:
            # Prepare messages for summarization
            conversation_text = ""
            for msg in messages[-20:]:  # Use last 20 messages
                if isinstance(msg.message, dict):
                    role = msg.message.get("role", "user")
                    content = msg.message.get("content", "")
                    conversation_text += f"{role}: {content}\n"
            
            if not conversation_text.strip():
                return "Empty conversation"
            
            summary_prompt = f"""
            Summarize this conversation session, focusing on:
            1. Main topics discussed
            2. Key decisions or outcomes
            3. User preferences or patterns shown
            4. Tasks or follow-ups mentioned
            
            Conversation:
            {conversation_text}
            
            Provide a concise but comprehensive summary in 2-3 sentences.
            """
            
            response, _ = await invoke_llm_with_tokens(
                [{"role": "user", "content": summary_prompt}],
                self.default_model
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}")
            return "Could not generate summary"
    
    async def store_message_for_semantic_search(
        self, 
        user_id: int, 
        session_id: str, 
        user_message: str, 
        assistant_response: str,
        db: Session
    ):
        """Store message pair in Qdrant for future semantic search."""
        try:
            # Generate embedding for the user message
            embedding = await get_embeddings([user_message])
            if not embedding or not embedding[0]:
                logger.warning("Could not generate embedding for message storage")
                return
            
            # Create point for Qdrant - use UUID for compatibility
            import uuid
            point_id = str(uuid.uuid4())
            
            payload = {
                "user_id": user_id,
                "session_id": session_id,
                "content": user_message,
                "response": assistant_response,
                "timestamp": datetime.utcnow().isoformat(),
                "context": {
                    "message_length": len(user_message),
                    "response_length": len(assistant_response)
                }
            }
            
            # Store in Qdrant
            client = await self.qdrant_service.client
            await client.upsert(
                collection_name="user_messages",
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding[0],
                        payload=payload
                    )
                ]
            )
            
            logger.debug(f"Stored message for semantic search: {point_id}")
            
        except Exception as e:
            logger.error(f"Error storing message for semantic search: {e}")
    
    async def update_conversation_context(
        self, 
        context: Dict[str, Any], 
        new_message: str, 
        new_response: str
    ) -> Dict[str, Any]:
        """Update context with new message and response."""
        try:
            # Add new exchange to conversation history
            context["conversation_history"].append({
                "role": "user",
                "content": new_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            context["conversation_history"].append({
                "role": "assistant", 
                "content": new_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Trim if too long
            if len(context["conversation_history"]) > self.max_conversation_history:
                context["conversation_history"] = context["conversation_history"][-self.max_conversation_history:]
            
            # Update metadata
            context["context_timestamp"] = datetime.utcnow().isoformat()
            context["context_sources"]["conversation_messages"] = len(context["conversation_history"])
            
            return context
            
        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            return context


# Global instance
persistent_memory_service = PersistentMemoryService()