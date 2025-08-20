"""
Fast Conversational Router

Provides immediate lightweight responses while triggering background processing.
This router handles the "conversational frontend" part of the new architecture.
"""
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException
from celery import Celery

from ..dependencies import get_current_user
from shared.database.models import User, ChatMessage
from shared.schemas.user_schemas import UserSettings
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.chat_storage_service import chat_storage_service
from shared.utils.database_setup import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

class ConversationalService:
    """Service for providing fast conversational responses."""
    
    def __init__(self):
        self.default_fast_model = "llama3.2:1b"  # Default lightweight model
        
    async def generate_fast_response(self, user_message: str, context: Dict[str, Any] = None, fast_model: str = None) -> str:
        """Generate a fast acknowledgment and initial response."""
        
        # Use provided model or default
        model_to_use = fast_model or self.default_fast_model
        
        # Build context-aware prompt
        conversation_context = ""
        if context and context.get("recent_messages"):
            recent = context["recent_messages"][-3:]  # Last 3 messages
            conversation_context = "\n".join([
                f"{'User' if msg.get('sender') == 'user' else 'Assistant'}: {msg.get('text', '')}"
                for msg in recent
            ])
        
        system_prompt = """You are the Fast Response AI, part of an intelligent AI team designed to help users efficiently.

Your role as the team coordinator:
1. Provide immediate acknowledgment and initial guidance
2. Give helpful first-level analysis or direction 
3. Let users know which specialized agents will follow up with detailed analysis
4. Set clear expectations about the collaborative AI workflow

Team members who may follow up:
- Mission Analyzer: Mission-aligned suggestions and goal analysis
- Document Analyzer: Document processing and research
- Calendar Assistant: Scheduling and time management
- Task Manager: Task organization and planning
- Multi-Agent Debate: Complex decision analysis
- Reflection Critic: Quality assessment and improvements

Guidelines:
- Be conversational and friendly (2-3 sentences max)
- Provide immediate value where possible
- Explain which team members will assist: "I'll have our [Agent] help with..."
- Set proper expectations about the team approach

Examples:
User: "Help me plan my day"
Response: "I'd be happy to help you get started on planning your day! Based on your request, I'll have our Calendar Assistant and Task Manager provide you with a detailed schedule and priority analysis."

User: "Review this document for me"
Response: "I can see you want a document review. Let me get our Document Analyzer to examine this thoroughly and provide detailed insights and recommendations."

User: "I need mission-aligned suggestions"
Response: "Great! I'll connect you with our Mission Analyzer who specializes in creating personalized suggestions based on your goals and current activities."
"""

        user_prompt = f"""
Recent conversation:
{conversation_context}

Current user message: {user_message}

Provide a fast, helpful, conversational response:"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response, _ = await invoke_llm_with_tokens(
                messages, 
                model_to_use, 
                category="conversation"
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating fast response with model {model_to_use}: {e}")
            return f"I understand you want help with '{user_message[:50]}...'. Let me work on that for you - I'm preparing a detailed response right now!"

# Global service instance
conversational_service = ConversationalService()

async def store_individual_message(session_id: str, user_id: int, message_type: str, 
                                  content: str, message_order: int, db: Session) -> str:
    """Store individual message to database and return message ID."""
    try:
        message_id = str(uuid.uuid4())
        chat_message = ChatMessage(
            id=uuid.UUID(message_id),
            session_id=session_id,
            user_id=user_id,
            message_type=message_type,
            content=content,
            message_order=message_order
        )
        db.add(chat_message)
        db.commit()
        logger.debug(f"Stored {message_type} message {message_id} for session {session_id}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to store message: {e}")
        db.rollback()
        raise


async def get_recent_messages(session_id: str, user_id: int, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent messages from database for context."""
    try:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user_id
        ).order_by(ChatMessage.message_order.desc()).limit(limit).all()
        
        # Return in chronological order
        return [
            {
                "sender": "user" if msg.message_type == "human" else "assistant", 
                "text": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]
    except Exception as e:
        logger.error(f"Failed to get recent messages: {e}")
        return []


@router.post("/chat")
async def fast_chat_response(
    request: Request, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provides immediate conversational response while triggering background processing.
    
    This is the new "fast frontend" that gives immediate responses and stores individual messages.
    """
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        session_id = body.get("session_id") or str(uuid.uuid4())
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        logger.info(f"Fast chat request for session {session_id}: {user_message[:100]}...")
        
        # 1. Get current message count for proper ordering
        current_message_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id
        ).count()
        
        # 2. Store user message individually
        user_message_id = await store_individual_message(
            session_id=session_id,
            user_id=current_user.id,
            message_type="human",
            content=user_message,
            message_order=current_message_count,
            db=db
        )
        
        # 3. Get recent message history from database for context
        message_history = await get_recent_messages(session_id, current_user.id, db, limit=10)
        
        # 4. Generate immediate response using user's configured fast model
        user_fast_model = getattr(current_user, 'fast_conversational_model', None) or "llama3.2:1b"
        
        context = {
            "recent_messages": message_history,
            "user_id": current_user.id,
            "session_id": session_id
        }
        
        fast_response = await conversational_service.generate_fast_response(
            user_message, context, user_fast_model
        )
        
        # 5. Store AI response individually
        ai_message_id = await store_individual_message(
            session_id=session_id,
            user_id=current_user.id,
            message_type="ai",
            content=fast_response,
            message_order=current_message_count + 1,
            db=db
        )
        
        # 6. Trigger background processing for complex workflow
        try:
            celery_app: Celery = request.app.state.celery_app
            
            # Build graph state for background processing using individual messages
            all_messages = message_history + [
                {"sender": "user", "text": user_message, "timestamp": datetime.now().isoformat()},
                {"sender": "assistant", "text": fast_response, "timestamp": datetime.now().isoformat()}
            ]
            
            background_graph_state = {
                "chat_model": current_user.chat_model or "llama3.2:3b",
                "initial_assessment_model": current_user.initial_assessment_model or "llama3.2:3b",
                "tool_selection_model": current_user.tool_selection_model or "llama3.2:3b",
                "embeddings_model": current_user.embeddings_model or "llama3.2:3b",
                "coding_model": current_user.coding_model or "llama3.2:3b",
                # Add granular model fields
                "executive_assessment_model": getattr(current_user, 'executive_assessment_model', None) or current_user.initial_assessment_model or "llama3.2:3b",
                "confidence_assessment_model": getattr(current_user, 'confidence_assessment_model', None) or current_user.initial_assessment_model or "llama3.2:3b",
                "reflection_model": getattr(current_user, 'reflection_model', None) or current_user.chat_model or "llama3.2:3b",
                # Include individual messages instead of pairs
                "messages": [
                    {"type": msg.get("sender") == "user" and "human" or "ai", 
                     "content": msg.get("text", ""), 
                     "timestamp": msg.get("timestamp")}
                    for msg in all_messages
                ]
            }
            
            # Trigger background task
            background_task = celery_app.send_task(
                "tasks.execute_background_workflow",
                kwargs={
                    "session_id": session_id,
                    "user_id": str(current_user.id),
                    "user_input": user_message,
                    "fast_response": fast_response,
                    "current_graph_state_dict": background_graph_state
                }
            )
            
            background_task_id = background_task.id
            logger.info(f"Triggered background task {background_task_id} for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger background task: {e}")
            background_task_id = None
        
        # 7. Return immediate response with proper message IDs
        return {
            "response": fast_response,
            "session_id": session_id,
            "message_id": ai_message_id,
            "user_message_id": user_message_id,
            "timestamp": datetime.now().isoformat(),
            "background_task_id": background_task_id,
            "type": "fast_response"
        }
        
    except Exception as e:
        logger.error(f"Error in fast chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/background-status/{task_id}")
async def get_background_task_status(
    task_id: str,
    request: Request,
    _current_user: User = Depends(get_current_user)
):
    """Get status of background processing task."""
    try:
        celery_app: Celery = request.app.state.celery_app
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.failed():
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": str(task_result.result)
            }
        elif task_result.successful():
            result = task_result.result
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "enhanced_response": result.get("enhanced_response"),
                "insights": result.get("insights"),
                "confidence_score": result.get("confidence_score"),
                "tools_used": result.get("tools_used", [])
            }
        else:
            return {
                "task_id": task_id,
                "status": task_result.status,
                "progress": getattr(task_result, 'info', {})
            }
            
    except Exception as e:
        logger.error(f"Error checking background task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_message_feedback(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Handle user feedback on messages for confidence improvement."""
    try:
        body = await request.json()
        session_id = body.get("session_id")
        message_id = body.get("message_id")
        feedback_type = body.get("feedback_type")  # "thumbs_up", "thumbs_down"
        feedback_details = body.get("details", "")
        
        if not all([session_id, message_id, feedback_type]):
            raise HTTPException(status_code=400, detail="Missing required feedback data")
        
        # Trigger feedback processing task
        celery_app: Celery = request.app.state.celery_app
        
        feedback_task = celery_app.send_task(
            "tasks.process_user_feedback",
            kwargs={
                "session_id": session_id,
                "user_id": str(current_user.id),
                "message_id": message_id,
                "feedback_type": feedback_type,
                "feedback_details": feedback_details,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Feedback submitted for message {message_id}: {feedback_type}")
        
        return {
            "status": "success",
            "feedback_task_id": feedback_task.id,
            "message": "Feedback received and will be processed"
        }
        
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))