"""Defines Celery tasks for the worker service."""
import logging
import os
import asyncio
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any

from worker.celery_app import celery_app, _db_state
from worker.services.document_processing_service import process_document
from worker.services.router_graph_service import run_router_graph
from worker.services.mission_suggestions_service import mission_suggestions_service
from worker.database_service import delete_document as delete_document_from_db
from worker.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


def _format_enhanced_response_for_chat(enhanced_response: str, confidence_score: float, 
                                     tools_used: list, insights: list) -> str:
    """Format enhanced response for direct chat display."""
    if not enhanced_response:
        return "Enhanced analysis completed, but no additional insights were generated."
    
    # Add confidence indicator
    confidence_emoji = "🎯" if confidence_score > 0.8 else "📊" if confidence_score > 0.6 else "🤔"
    formatted_text = f"{confidence_emoji} **Enhanced Analysis** (Confidence: {confidence_score:.1%})\n\n"
    
    # Add the main enhanced response
    formatted_text += enhanced_response
    
    # Add tools used if available
    if tools_used:
        formatted_text += f"\n\n🛠️ **Tools Used**: {', '.join(tools_used)}"
    
    # Add key insights if available
    if insights:
        formatted_text += "\n\n💡 **Key Insights**:\n"
        for insight in insights[:3]:  # Limit to top 3 insights
            formatted_text += f"• {insight}\n"
    
    return formatted_text


@contextmanager
def get_db_session():
    """Provides a transactional scope around a series of database operations."""
    if "session_factory" not in _db_state:
        raise RuntimeError("Database session factory not initialized in worker.")

    session = _db_state["session_factory"]()
    try:
        yield session
    finally:
        session.close()


@celery_app.task(name="tasks.execute_chat_graph")
def execute_chat_graph_task(session_id: str, user_id: str, user_input: str, current_graph_state_dict: Optional[Dict[str, Any]] = None):
    """Celery task to run the AI agent graph for a chat message."""
    logger.info(f"Worker executing chat graph for session_id: {session_id}")
    # The result of this can be sent back via WebSocket or stored in Redis
    # run_router_graph is an async function, so we need to use asyncio.run()
    
    async def run_graph_with_cleanup():
        """Wrapper to ensure proper cleanup of async resources."""
        try:
            return await run_router_graph(user_input, session_id, str(user_id), current_graph_state_dict)
        except Exception as e:
            logger.error(f"Error in run_router_graph: {e}")
            raise
    
    try:
        _response_content, _selected_tool_name, final_state_dict = asyncio.run(run_graph_with_cleanup())
        # (WebSocket logic to send final_state to client would go here)
        return final_state_dict
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            # This is often a cleanup issue, but the task likely completed successfully
            # Return a proper graph state with a helpful message
            logger.warning(f"Event loop closed error, but task may have completed: {e}")
            return {
                "user_input": user_input,
                "session_id": session_id,
                "user_id": str(user_id),
                "final_response": "I apologize, but there was a technical issue processing your request. The system experienced an event loop cleanup issue. Please try sending your message again.",
                "messages": [
                    {"type": "human", "content": user_input},
                    {"type": "ai", "content": "I apologize, but there was a technical issue processing your request. The system experienced an event loop cleanup issue. Please try sending your message again."}
                ]
            }
        else:
            raise


@celery_app.task(name="tasks.process_document_wrapper")
def process_document_wrapper_task(task_params: Dict[str, Any]):
    """
    Celery task wrapper for the asynchronous document processing pipeline.
    It retrieves a database session and runs the async processing function.
    """
    document_id = task_params.get("document_id")
    logger.info("Worker processing document_id: %s", document_id)

    try:
        with get_db_session() as db:
            # Run the async document processing function within the sync Celery task
            asyncio.run(process_document(db=db, **task_params))
    except Exception as e:
        logger.error(
            "Celery task tasks.process_document_wrapper failed for document_id %s: %s",
            document_id, e, exc_info=True
        )
        # The underlying process_document function handles setting the FAILED status.
        # Re-raise to ensure the task is marked as failed in Celery.
        raise


@celery_app.task(name="tasks.delete_document")
def delete_document_task(document_id: str, user_id: int, file_path: str):
    """
    Celery task to delete a document and its associated data.
    This includes the physical file, the database record, and vector embeddings.
    """
    logger.info(
        "Worker deleting document_id: %s for user_id: %s", document_id, user_id
    )
    doc_uuid = uuid.UUID(document_id)

    # 1. Delete the physical file from the shared volume.
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("Successfully deleted physical file: %s", file_path)
        else:
            logger.warning("File not found, could not delete: %s", file_path)
    except OSError as e:
        logger.error("Error deleting file %s: %s", file_path, e, exc_info=True)
        # Continue to at least attempt to delete DB/vector records.

    # 2. Delete document chunks from the vector store (Qdrant).
    try:
        qdrant_service = QdrantService()
        # This assumes a method exists to delete all vectors associated with a document_id.
        # This is a critical part of the RAG pipeline cleanup.
        qdrant_service.delete_by_document_id(document_id=document_id)
        logger.info("Successfully deleted vector embeddings for document_id: %s", document_id)
    except Exception as e:
        logger.error(
            "Error deleting vectors from Qdrant for document_id %s: %s",
            document_id, e, exc_info=True
        )
        # Log and continue to ensure the primary DB record is deleted.

    # 3. Delete the document record from the PostgreSQL database.
    try:
        with get_db_session() as db:
            deleted = delete_document_from_db(db, document_id=doc_uuid, user_id=user_id)
            if deleted:
                logger.info("Successfully deleted database record for document_id: %s", document_id)
            else:
                logger.warning(
                    "Could not find or delete database record for document_id: %s. "
                    "It may have already been deleted.", document_id
                )
    except Exception as e:
        logger.error(
            "Error deleting database record for document_id %s: %s", document_id, e, exc_info=True
        )
        raise  # Re-raise to mark the task as failed.


@celery_app.task(name="tasks.execute_mission_suggestions")
def execute_mission_suggestions_task(user_id: int, session_id: str):
    """
    Celery task to generate mission-aligned suggestions for a user.
    This is typically called on login if the user has a mission statement.
    """
    logger.info(f"Worker generating mission suggestions for user_id: {user_id}, session_id: {session_id}")
    
    async def generate_suggestions():
        """Async wrapper for mission suggestions generation."""
        try:
            suggestions, token_metrics = await mission_suggestions_service.generate_mission_suggestions(
                user_id, session_id
            )
            
            # Log the results
            logger.info(f"Generated {len(suggestions)} mission suggestions for user {user_id}")
            logger.info(f"Token usage: {token_metrics.input_tokens} input, {token_metrics.output_tokens} output")
            
            return {
                "success": True,
                "user_id": user_id,
                "session_id": session_id,
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
                "token_usage": {
                    "input_tokens": token_metrics.input_tokens,
                    "output_tokens": token_metrics.output_tokens,
                    "total_tokens": token_metrics.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating mission suggestions for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "session_id": session_id,
                "error": str(e),
                "suggestions": []
            }
    
    try:
        result = asyncio.run(generate_suggestions())
        return result
    except Exception as e:
        logger.error(f"Error in mission suggestions task: {e}", exc_info=True)
        raise


@celery_app.task(name="tasks.execute_background_workflow")
def execute_background_workflow_task(
    session_id: str, 
    user_id: str, 
    user_input: str, 
    fast_response: str,
    current_graph_state_dict: Optional[Dict[str, Any]] = None
):
    """
    Background task for complex LangGraph processing.
    
    This runs the full sophisticated workflow with reflection, planning, etc.
    while the user already has a fast response to interact with.
    """
    logger.info(f"Background workflow executing for session {session_id}: {user_input[:100]}...")
    
    async def run_enhanced_workflow():
        """Enhanced workflow with deeper processing."""
        try:
            # Run the full LangGraph workflow
            response_content, selected_tool_name, final_state_dict = await run_router_graph(
                user_input, session_id, str(user_id), current_graph_state_dict
            )
            
            # Extract insights and enhanced information
            enhanced_response = ""
            confidence_score = final_state_dict.get("confidence_score", 0.5)
            tools_used = []
            insights = []
            
            # Process the final state to extract useful information
            if final_state_dict.get("final_response"):
                if isinstance(final_state_dict["final_response"], dict):
                    enhanced_response = final_state_dict["final_response"].get("response", str(final_state_dict["final_response"]))
                else:
                    enhanced_response = str(final_state_dict["final_response"])
            elif response_content:
                enhanced_response = response_content
            
            # Extract tools used
            if selected_tool_name:
                tools_used.append(selected_tool_name)
            
            # Extract insights from reflection and planning
            if final_state_dict.get("critique_history"):
                for critique in final_state_dict["critique_history"]:
                    if hasattr(critique, 'specific_issues') and critique.specific_issues:
                        insights.extend([f"Reflection: {issue}" for issue in critique.specific_issues[:2]])
            
            if final_state_dict.get("plan"):
                insights.append(f"Planned approach with {len(final_state_dict['plan'])} steps")
            
            # Check if this is significantly different/better than fast response
            is_enhanced = (
                len(enhanced_response) > len(fast_response) * 1.5 or
                tools_used or
                confidence_score > 0.8 or
                len(insights) > 0
            )
            
            return {
                "session_id": session_id,
                "user_input": user_input,
                "fast_response": fast_response,
                "enhanced_response": enhanced_response if is_enhanced else None,
                "confidence_score": confidence_score,
                "tools_used": tools_used,
                "insights": insights,
                "is_enhanced": is_enhanced,
                "final_state": final_state_dict
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced workflow: {e}", exc_info=True)
            return {
                "session_id": session_id,
                "user_input": user_input,
                "fast_response": fast_response,
                "enhanced_response": None,
                "error": str(e),
                "confidence_score": 0.3,
                "tools_used": [],
                "insights": [f"Background processing encountered an error: {str(e)[:100]}"],
                "is_enhanced": False
            }
    
    try:
        result = asyncio.run(run_enhanced_workflow())
        
        # Post enhanced result directly to chat via agent message
        try:
            from worker.services.progress_manager import progress_manager, AgentNames
            
            if result.get("is_enhanced") and result.get("enhanced_response"):
                # Determine agent name based on tools used
                tools_used = result.get("tools_used", [])
                agent_name = AgentNames.ROUTER_INTELLIGENCE  # Default
                agent_type = "enhanced analysis"
                
                # Customize agent name based on primary tool used
                if tools_used:
                    primary_tool = tools_used[0]
                    if "document" in primary_tool.lower():
                        agent_name = AgentNames.DOCUMENT_ANALYZER
                        agent_type = "document analysis"
                    elif "calendar" in primary_tool.lower():
                        agent_name = AgentNames.CALENDAR_ASSISTANT
                        agent_type = "calendar management"
                    elif "email" in primary_tool.lower():
                        agent_name = AgentNames.EMAIL_ASSISTANT
                        agent_type = "email assistance"
                    elif "task" in primary_tool.lower():
                        agent_name = AgentNames.TASK_MANAGER
                        agent_type = "task management"
                
                # Format enhanced response for chat
                formatted_response = _format_enhanced_response_for_chat(
                    result.get("enhanced_response"), 
                    result.get("confidence_score", 0.5),
                    tools_used,
                    result.get("insights", [])
                )
                
                # Use sync version for Celery compatibility
                progress_manager.broadcast_agent_message_sync(
                    session_id,
                    agent_name,
                    formatted_response,
                    agent_type=agent_type,
                    metadata={
                        "confidence_score": result.get("confidence_score", 0.5),
                        "tools_used": tools_used,
                        "insights_count": len(result.get("insights", []))
                    },
                    formatted=True
                )
                    
            else:
                # Still broadcast background_complete for non-enhanced results
                progress_manager.broadcast_to_session_sync_sync(session_id, {
                    "type": "background_complete",
                    "content": "Analysis complete",
                    "confidence_score": result.get("confidence_score", 0.5)
                })
                
        except Exception as e:
            logger.warning(f"Failed to broadcast background completion: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Background workflow task failed: {e}", exc_info=True)
        raise


@celery_app.task(name="tasks.process_user_feedback")
def process_user_feedback_task(
    session_id: str,
    user_id: str,
    message_id: str,
    feedback_type: str,
    feedback_details: str = "",
    timestamp: str = ""
):
    """
    Process user feedback to improve confidence ratings and system performance.
    
    This task analyzes user feedback and updates the confidence system,
    correction memory, and learning mechanisms.
    """
    logger.info(f"Processing feedback for session {session_id}, message {message_id}: {feedback_type}")
    
    async def process_feedback():
        """Process feedback and update systems."""
        try:
            from worker.services.correction_memory_service import correction_memory_service
            from worker.services.step_oversight_service import step_oversight_service
            
            # Create a mock state for feedback processing
            mock_state = type('MockState', (), {
                'user_input': f"Feedback processing for message {message_id}",
                'session_id': session_id,
                'user_id': user_id,
                'selected_tool': 'feedback_processor'
            })()
            
            feedback_score = 1.0 if feedback_type == "thumbs_up" else -0.5
            
            # Store feedback as learning experience
            if feedback_type == "thumbs_down":
                # Negative feedback - store as correction pattern
                failure_info = {
                    "action": f"Response to user message (session: {session_id})",
                    "tool_name": "conversational_response",
                    "error_message": f"User provided negative feedback: {feedback_details or 'Response not helpful'}",
                    "error_type": "user_feedback_negative",
                    "context": f"Message ID: {message_id}, Feedback: {feedback_details}",
                    "step_description": "User interaction response",
                    "feedback_score": feedback_score,
                    "timestamp": timestamp
                }
                
                success = await correction_memory_service.store_failure_pattern(mock_state, failure_info)
                logger.info(f"Stored negative feedback as correction pattern: {success}")
                
            elif feedback_type == "thumbs_up":
                # Positive feedback - could be used to reinforce good patterns
                logger.info(f"Positive feedback received for message {message_id}")
                
                # Track successful interaction
                step_oversight_service.track_successful_step(session_id)
            
            # Update confidence calibration based on feedback
            try:
                from shared.services.confidence_calibration_service import confidence_calibration_service
                from shared.utils.database_setup import get_db
                from shared.database.models import ChatMessage
                
                # Get the original message to retrieve confidence score
                with next(get_db()) as db:
                    message = db.query(ChatMessage).filter(
                        ChatMessage.message_id == message_id
                    ).first()
                    
                    if message and message.confidence_score is not None:
                        calibration_result = confidence_calibration_service.update_confidence_based_on_feedback(
                            message_id, feedback_type, message.confidence_score
                        )
                        logger.info(f"Confidence calibration updated: {calibration_result}")
                        
                        # Store calibration insights in response
                        return {
                            "session_id": session_id,
                            "message_id": message_id,
                            "feedback_type": feedback_type,
                            "feedback_score": feedback_score,
                            "processed": True,
                            "stored_as_learning": feedback_type == "thumbs_down",
                            "confidence_calibration": calibration_result
                        }
                    else:
                        logger.warning(f"Could not find message {message_id} or confidence score for calibration")
                        
            except Exception as e:
                logger.error(f"Error updating confidence calibration: {e}")
                # Continue with basic feedback processing even if calibration fails
            
            # Default return for cases where confidence calibration isn't available
            return {
                "session_id": session_id,
                "message_id": message_id,
                "feedback_type": feedback_type,
                "feedback_score": feedback_score,
                "processed": True,
                "stored_as_learning": feedback_type == "thumbs_down"
            }
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}", exc_info=True)
            return {
                "session_id": session_id,
                "message_id": message_id,
                "feedback_type": feedback_type,
                "processed": False,
                "error": str(e)
            }
    
    try:
        result = asyncio.run(process_feedback())
        logger.info(f"Feedback processing complete for {message_id}: {result.get('processed', False)}")
        return result
        
    except Exception as e:
        logger.error(f"Feedback processing task failed: {e}", exc_info=True)
        raise