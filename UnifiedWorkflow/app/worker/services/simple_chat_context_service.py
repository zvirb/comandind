"""
Simple Chat Context Service - Context-Aware Chat with RAG Integration

Simplified version that integrates with existing chat storage and Qdrant services
for immediate context awareness and memory capabilities.

Features:
- Context retrieval from existing chat history
- Memory formation using existing chat storage
- Session continuity via existing session management
- RAG capabilities via Qdrant integration
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc

from shared.database.models import User, ChatMessage, ChatSessionSummary
from shared.utils.database_setup import get_db
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from worker.services.qdrant_service import QdrantService
from worker.services.chat_storage_service import chat_storage_service
from worker.services.centralized_resource_service import centralized_resource_service, ComplexityLevel

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    """Represents contextual information for a chat session."""
    session_id: str
    user_id: int
    context_items: List[Dict[str, Any]]
    relevance_scores: List[float]
    total_tokens: int
    retrieval_time_ms: float
    memory_formation_enabled: bool = True


class SimpleChatContextService:
    """
    Simplified context-aware Simple Chat service that integrates with existing infrastructure.
    """
    
    def __init__(self):
        self.qdrant_service = QdrantService()
        self.max_context_tokens = 4000  # Maximum tokens for context
        self.context_retrieval_timeout = 0.003  # 3ms requirement (for future optimization)
        self.memory_formation_threshold = 0.7  # Minimum importance for memory formation
    
    async def get_chat_context(self, user_id: int, session_id: str, 
                              current_message: str) -> ChatContext:
        """
        Retrieve relevant context for current chat message using existing services.
        
        Args:
            user_id: User ID for context isolation
            session_id: Current session ID
            current_message: User's current message
            
        Returns:
            ChatContext with relevant information
        """
        start_time = datetime.now()
        
        try:
            # Phase 1: Get recent session history from existing chat storage
            session_context = await self._get_session_history(user_id, session_id)
            
            # Phase 2: Get semantic context from Qdrant if available
            semantic_context = await self._get_semantic_context(user_id, current_message, session_id)
            
            # Combine all context
            all_context = session_context + semantic_context
            
            # Phase 3: Rank and filter context by relevance
            ranked_context = self._rank_and_filter_context(all_context, current_message)
            
            # Calculate retrieval performance
            end_time = datetime.now()
            retrieval_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Estimate token count for context
            total_tokens = sum(
                len(item.get("content", "").split()) * 1.3  # Rough token estimation
                for item in ranked_context
            )
            
            relevance_scores = [item.get("relevance_score", 0.0) for item in ranked_context]
            
            logger.info(f"Context retrieval for user {user_id}: {len(ranked_context)} items, "
                       f"{retrieval_time_ms:.2f}ms, {total_tokens:.0f} tokens")
            
            return ChatContext(
                session_id=session_id,
                user_id=user_id,
                context_items=ranked_context,
                relevance_scores=relevance_scores,
                total_tokens=int(total_tokens),
                retrieval_time_ms=retrieval_time_ms
            )
                
        except Exception as e:
            logger.error(f"Error retrieving chat context: {e}", exc_info=True)
            # Return empty context on error
            return ChatContext(
                session_id=session_id,
                user_id=user_id,
                context_items=[],
                relevance_scores=[],
                total_tokens=0,
                retrieval_time_ms=0.0,
                memory_formation_enabled=False
            )
    
    async def _get_session_history(self, user_id: int, session_id: str) -> List[Dict[str, Any]]:
        """Get recent conversation history from current session."""
        try:
            def get_history_sync():
                with next(get_db()) as db:
                    # Get recent chat messages from this session
                    recent_messages = db.query(ChatMessage).filter(
                        ChatMessage.session_id == session_id,
                        ChatMessage.user_id == user_id
                    ).order_by(desc(ChatMessage.created_at)).limit(5).all()
                    
                    history_items = []
                    for msg in recent_messages:
                        history_items.append({
                            "type": "session_history",
                            "content": msg.content,
                            "message_type": msg.message_type,
                            "timestamp": msg.created_at,
                            "message_order": msg.message_order,
                            "relevance_score": 0.9  # High relevance for recent session history
                        })
                    
                    return history_items
            
            # Run database operation in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, get_history_sync)
            
        except Exception as e:
            logger.error(f"Error retrieving session history: {e}")
            return []
    
    async def _get_semantic_context(self, user_id: int, query_text: str, 
                                  exclude_session: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar context using existing Qdrant integration.
        """
        try:
            # Use existing chat storage service for semantic search
            search_results = await chat_storage_service.search_chat_history(
                user_id=user_id,
                query=query_text,
                limit=5,
                content_types=["chat"]
            )
            
            semantic_items = []
            for result in search_results:
                # Skip results from current session if specified
                if exclude_session and result.get("session_id") == exclude_session:
                    continue
                
                semantic_items.append({
                    "type": "semantic_context",
                    "content": result.get("content", ""),
                    "session_id": result.get("session_id", ""),
                    "message_type": result.get("message_type", ""),
                    "timestamp": result.get("timestamp", ""),
                    "conversation_domain": result.get("conversation_domain", ""),
                    "relevance_score": result.get("score", 0.5)
                })
            
            return semantic_items
            
        except Exception as e:
            logger.error(f"Error in semantic context retrieval: {e}")
            return []
    
    def _rank_and_filter_context(self, context_items: List[Dict[str, Any]], 
                                current_message: str) -> List[Dict[str, Any]]:
        """
        Rank context items by relevance and filter to stay within token limits.
        """
        try:
            # Simple relevance scoring based on recency and type
            for item in context_items:
                base_score = item.get("relevance_score", 0.5)
                
                # Boost recent items
                if "timestamp" in item and item["timestamp"]:
                    if isinstance(item["timestamp"], str):
                        try:
                            timestamp = datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.now(timezone.utc)
                    else:
                        timestamp = item["timestamp"]
                    
                    age_hours = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
                    recency_boost = max(0, 1 - (age_hours / 24))  # Decay over 24 hours
                    base_score += recency_boost * 0.2
                
                # Boost by context type priority
                context_type = item.get("type", "unknown")
                if context_type == "session_history":
                    base_score += 0.3
                elif context_type == "semantic_context":
                    base_score += 0.1
                
                item["final_relevance_score"] = min(1.0, base_score)
            
            # Sort by relevance score
            context_items.sort(key=lambda x: x.get("final_relevance_score", 0), reverse=True)
            
            # Filter to stay within token limits
            filtered_items = []
            total_tokens = 0
            
            for item in context_items:
                item_tokens = len(item.get("content", "").split()) * 1.3
                if total_tokens + item_tokens <= self.max_context_tokens:
                    filtered_items.append(item)
                    total_tokens += item_tokens
                else:
                    break
            
            return filtered_items
            
        except Exception as e:
            logger.error(f"Error ranking and filtering context: {e}")
            return context_items[:5]  # Return first 5 items as fallback
    
    async def form_memory(self, user_id: int, session_id: str, 
                         conversation_content: str, user_message: str, 
                         ai_response: str) -> bool:
        """
        Form memories from conversation using existing chat storage infrastructure.
        
        Args:
            user_id: User ID for memory isolation
            session_id: Session ID for context
            conversation_content: Full conversation context
            user_message: Current user message
            ai_response: AI response
            
        Returns:
            True if memory formation successful
        """
        try:
            # For now, rely on existing chat storage service for memory formation
            # This stores the conversation in both PostgreSQL and Qdrant automatically
            
            # Create a simple graph state for compatibility with existing storage
            from worker.graph_types import GraphState
            from langchain_core.messages import HumanMessage, AIMessage
            
            # Create messages for storage
            messages = [
                HumanMessage(content=user_message),
                AIMessage(content=ai_response)
            ]
            
            # Create minimal graph state
            graph_state = GraphState(
                session_id=session_id,
                user_id=str(user_id),
                messages=messages,
                conversation_domain="simple_chat"
            )
            
            # Store via existing chat storage service
            session_start = datetime.now(timezone.utc) - timedelta(minutes=1)
            session_end = datetime.now(timezone.utc)
            
            success = await chat_storage_service.store_chat_session(
                state=graph_state,
                session_start_time=session_start,
                session_end_time=session_end
            )
            
            if success:
                logger.info(f"Memory formation completed for user {user_id}, session {session_id}")
            
            return success
                
        except Exception as e:
            logger.error(f"Error in memory formation: {e}", exc_info=True)
            return False
    
    async def manage_session_continuity(self, user_id: int, new_session_id: str, 
                                      parent_session_id: Optional[str] = None) -> bool:
        """
        Manage session continuity using existing session infrastructure.
        
        Args:
            user_id: User ID for context isolation
            new_session_id: New session ID
            parent_session_id: Optional parent session for context transfer
            
        Returns:
            True if session continuity established
        """
        try:
            # For now, session continuity is handled by the context retrieval process
            # Future enhancement: implement session linking in unified memory tables
            
            logger.info(f"Session continuity managed for user {user_id}, session {new_session_id}")
            return True
                
        except Exception as e:
            logger.error(f"Error managing session continuity: {e}")
            return False
    
    async def cleanup_expired_context(self, user_id: Optional[int] = None) -> int:
        """
        Clean up expired context items (placeholder for future implementation).
        
        Args:
            user_id: Optional user ID to limit cleanup to specific user
            
        Returns:
            Number of items cleaned up
        """
        try:
            # For now, rely on existing chat storage cleanup mechanisms
            # Future enhancement: implement context-specific cleanup
            
            logger.info(f"Context cleanup completed")
            return 0
                
        except Exception as e:
            logger.error(f"Error in context cleanup: {e}")
            return 0


# Global service instance
simple_chat_context_service = SimpleChatContextService()