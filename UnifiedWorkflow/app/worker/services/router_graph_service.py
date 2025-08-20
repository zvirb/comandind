# services/router_graph_service.py
"""
Simplified router graph service that delegates to the modular router system.
This maintains compatibility with existing task interfaces while using the new simplified architecture.
"""

import logging
from typing import Optional, List, Dict, Any, Union, Tuple, cast, TypedDict
from datetime import datetime

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    messages_from_dict,
)
from worker.graph_types import GraphState
from worker.services.router_modules.router_core import run_router_graph as run_simplified_router
from worker.services.chat_storage_service import ChatStorageService
from shared.services.persistent_memory_service import persistent_memory_service
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)


class BaseMessageDict(TypedDict):
    """Type definition for serialized BaseMessage dictionaries."""
    type: str
    content: str


# --- Helper Functions ---
def _serialize_messages(messages: List[BaseMessage]) -> List[dict]:
    """
    Serializes BaseMessage objects to dictionaries for JSON storage.
    This is necessary when storing state in JSON-based stores or returning from Celery tasks.
    """
    serialized_messages = []
    for msg in messages:
        try:
            # Convert BaseMessage to dict using LangChain's built-in method
            msg_dict = msg.model_dump()  # Updated for Pydantic v2
            serialized_messages.append(msg_dict)
        except Exception as e:
            logger.warning(f"Could not serialize message: {msg}. Error: {e}")
    return serialized_messages


def _deserialize_messages(messages: List[Union[BaseMessageDict, BaseMessage]]) -> List[BaseMessage]:    
    """
    Safely deserializes a list that may contain message dictionaries into BaseMessage objects.
    This is necessary when loading state from a JSON-based store like a database.
    """
    processed_messages: List[BaseMessage] = []
    if not messages:
        return []
    for m_data in messages:
        if isinstance(m_data, dict) and "type" in m_data and "content" in m_data:
            try:
                deserialized_list = messages_from_dict([cast(dict, m_data)])
                if deserialized_list:
                    processed_messages.append(deserialized_list[0])
            except Exception as e:
                logger.warning(f"Could not deserialize a message dictionary: {m_data}. Error: {e}")
        else:
            processed_messages.append(m_data)
        # Silently discard other types (like None or malformed data) that are not valid messages.
    return processed_messages


# --- Main Service Function ---
async def run_router_graph(
    user_input: str, 
    session_id: str, 
    user_id: Optional[str] = None, 
    current_graph_state_dict: Optional[Dict[str, Any]] = None
) -> Tuple[Union[Dict[str, Any], str], str, Dict[str, Any]]:
    """
    Main entry point for the router graph service.
    This is a simplified version that delegates to the modular router system.
    Maintains compatibility with existing task interfaces.
    """
    logger.info(f"run_router_graph called with user_input: '{user_input}', session_id: '{session_id}', user_id: '{user_id}'")
    
    try:
        # Handle message history from previous state
        if current_graph_state_dict:
            logger.debug(f"Existing graph state provided: {list(current_graph_state_dict.keys())}")
            messages_history_raw = current_graph_state_dict.get("messages", [])
            messages_history = _deserialize_messages(messages_history_raw)
        else:
            logger.debug("No existing graph state provided, starting fresh.")
            messages_history = []

        # Append the new user message to the history
        all_messages = messages_history + [HumanMessage(content=user_input)]
        
        # Convert user_id to int for the simplified router
        user_id_int = int(user_id) if user_id and user_id.isdigit() else 1
        
        # Get persistent memory context for enhanced AI responses
        memory_context = {}
        try:
            with get_db() as db:
                memory_context = await persistent_memory_service.get_comprehensive_context(
                    user_id=user_id_int,
                    session_id=session_id,
                    current_message=user_input,
                    db=db
                )
                logger.info(f"Retrieved memory context with {len(memory_context.get('conversation_history', []))} messages, "
                           f"{len(memory_context.get('semantic_context', []))} semantic matches")
        except Exception as e:
            logger.error(f"Error retrieving memory context: {e}")
            memory_context = {"conversation_history": [], "semantic_context": [], "user_patterns": {}}
        
        # Call the simplified router with memory context
        router_result = await run_simplified_router(
            user_input=user_input,
            messages=all_messages,
            user_id=user_id_int,
            session_id=session_id,
            chat_model="llama3.2:3b",
            memory_context=memory_context
        )
        
        # Extract response information with type safety
        response_content = router_result.get("response", "")
        
        # Ensure response_content is always a string
        if isinstance(response_content, dict):
            response_content = response_content.get("response", str(response_content))
        elif not isinstance(response_content, str):
            response_content = str(response_content)
        
        routing_decision = router_result.get("routing_decision", "DIRECT")
        confidence_score = router_result.get("confidence_score", 0.8)
        metadata = router_result.get("metadata", {})
        
        # Determine selected tool from routing decision or metadata
        selected_tool_name = "unstructured_interaction"  # Default
        if routing_decision == "PLANNING":
            selected_tool_name = "planner"
        elif "model_used" in metadata:
            selected_tool_name = f"llm_{metadata['model_used']}"
            
        # Build the final state dictionary for compatibility
        final_state_dict = {
            "user_input": user_input,
            "session_id": session_id,
            "user_id": user_id,
            "messages": all_messages,
            "final_response": response_content,
            "routing_decision": routing_decision,
            "confidence_score": confidence_score,
            "selected_tool": selected_tool_name,
            "tool_output": {"response": response_content},
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store the interaction for future semantic search
        try:
            with get_db() as db:
                await persistent_memory_service.store_message_for_semantic_search(
                    user_id=user_id_int,
                    session_id=session_id,
                    user_message=user_input,
                    assistant_response=response_content,
                    db=db
                )
                logger.debug("Stored message pair for semantic search")
        except Exception as e:
            logger.error(f"Error storing message for semantic search: {e}")
        
        # Update with any previous state that should be preserved
        if current_graph_state_dict:
            # Preserve certain fields from previous state
            preserved_fields = [
                "plan", "plan_step", "critique", "retry_needed", 
                "conversation_summary", "iteration_count"
            ]
            for field in preserved_fields:
                if field in current_graph_state_dict:
                    final_state_dict[field] = current_graph_state_dict[field]
        
        # Store chat interaction (fire and forget - don't fail if storage fails)
        try:
            chat_storage = ChatStorageService()
            await chat_storage.store_chat_interaction(
                session_id=session_id,
                user_id=user_id,
                user_message=user_input,
                ai_response=response_content,
                tool_used=selected_tool_name,
                metadata={
                    "routing_decision": routing_decision,
                    "confidence_score": confidence_score,
                    **metadata
                }
            )
        except Exception as e:
            logger.error(f"Failed to store chat interaction: {e}")
            # Don't fail the response if storage fails
        
        # Serialize the messages for JSON storage/Celery task return
        serializable_state_dict = final_state_dict.copy()
        if "messages" in serializable_state_dict and serializable_state_dict["messages"]:
            serializable_state_dict["messages"] = _serialize_messages(serializable_state_dict["messages"])
        
        logger.info(f"Router graph completed successfully for session {session_id}")
        return response_content, selected_tool_name, serializable_state_dict
        
    except Exception as e:
        logger.error(f"Error in router graph service: {e}", exc_info=True)
        
        # Return error response in expected format
        error_response = f"I encountered an error processing your request: {str(e)}"
        error_state = {
            "user_input": user_input,
            "session_id": session_id,
            "user_id": user_id,
            "messages": [
                {"type": "human", "content": user_input},
                {"type": "ai", "content": error_response}
            ],
            "final_response": error_response,
            "routing_decision": "ERROR",
            "confidence_score": 0.0,
            "selected_tool": "error_handler",
            "tool_output": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        }
        
        return error_response, "error_handler", error_state