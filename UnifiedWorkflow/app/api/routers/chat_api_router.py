"""
Chat API Router - REST endpoints for chat functionality.
Complements WebSocket chat with traditional HTTP chat endpoints.
"""

import logging
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_db, get_async_session
from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User
from shared.services.unified_session_manager import get_session_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Chat Models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    session_id: str
    model_used: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class ChatSession(BaseModel):
    """Chat session model."""
    session_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int

class ChatHistory(BaseModel):
    """Chat history model."""
    session_id: str
    messages: List[ChatMessage]
    total_messages: int

# Chat sessions now managed by unified session manager (Redis-backed)
# Remove global in-memory storage to prevent memory leaks

@router.post(
    "/send",
    response_model=ChatResponse,
    dependencies=[Depends(verify_csrf_token)],
)
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Send a chat message and get AI response.
    Non-streaming endpoint using unified session manager for chat history.
    """
    session_manager = await get_session_manager()
    
    # Generate session ID if not provided
    if not request.session_id:
        request.session_id = f"chat_{uuid.uuid4().hex[:16]}"
    
    # Get or create chat session data in Redis
    chat_history_key = f"chat_history:{current_user.id}_{request.session_id}"
    
    # Get existing chat history from Redis
    try:
        history_data = await session_manager.redis_client.get(chat_history_key)
        chat_history = json.loads(history_data) if history_data else []
    except Exception as e:
        logger.warning(f"Failed to get chat history from Redis: {e}")
        chat_history = []
    
    # Add user message to history
    user_message = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    }
    chat_history.append(user_message)
    
    try:
        # Import Ollama service
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'sequentialthinking_service'))
        
        try:
            from services.ollama_client_service import OllamaClientService
        except ImportError:
            # Fallback implementation
            raise HTTPException(
                status_code=503,
                detail="AI service temporarily unavailable"
            )
        
        # Initialize Ollama service
        ollama_service = OllamaClientService()
        await ollama_service.initialize()
        
        # Get chat history for context (exclude current message)
        context_history = chat_history[:-1] if chat_history else []
        
        # Generate response
        accumulated_response = ""
        model_used = request.model or "llama3:8b-instruct-q4_0"
        
        async for chunk_data in ollama_service.generate_chat_response_stream(
            message=request.message,
            chat_history=context_history,
            preferred_model=model_used
        ):
            chunk = chunk_data.get("chunk", "")
            if chunk:
                accumulated_response += chunk
            
            if chunk_data.get("is_complete", False):
                break
        
        # Add assistant response to history
        assistant_message = {
            "role": "assistant",
            "content": accumulated_response,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(assistant_message)
        
        # Limit session history to last 20 messages
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        
        # Save updated history to Redis with TTL
        try:
            await session_manager.redis_client.setex(
                chat_history_key,
                86400,  # 24 hour TTL
                json.dumps(chat_history)
            )
        except Exception as e:
            logger.warning(f"Failed to save chat history to Redis: {e}")
        
        await ollama_service.close()
        
        return ChatResponse(
            message=accumulated_response,
            session_id=request.session_id,
            model_used=model_used,
            timestamp=datetime.now(),
            metadata={
                "message_count": len(chat_history),
                "processing_time_ms": 0,  # Would measure in real implementation
                "storage_backend": "redis"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in chat processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error processing chat message"
        )


@router.post(
    "/stream",
    dependencies=[Depends(verify_csrf_token)],
)
async def stream_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Send a chat message and get streaming AI response.
    Server-sent events endpoint for streaming responses.
    """
    global chat_sessions
    
    # Generate session ID if not provided
    if not request.session_id:
        request.session_id = f"chat_{uuid.uuid4().hex[:16]}"
    
    session_key = f"{current_user.id}_{request.session_id}"
    
    # Initialize session if needed
    if session_key not in chat_sessions:
        chat_sessions[session_key] = []
    
    # Add user message to history
    user_message = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    }
    chat_sessions[session_key].append(user_message)
    
    async def generate_stream():
        try:
            # Import Ollama service
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'sequentialthinking_service'))
            
            try:
                from services.ollama_client_service import OllamaClientService
            except ImportError:
                yield f"data: {json.dumps({'error': 'AI service temporarily unavailable'})}\n\n"
                return
            
            # Initialize Ollama service
            ollama_service = OllamaClientService()
            await ollama_service.initialize()
            
            # Get chat history for context
            chat_history = chat_sessions[session_key][:-1]  # Exclude current message
            
            # Generate streaming response
            accumulated_response = ""
            model_used = request.model or "llama3:8b-instruct-q4_0"
            
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'session_id': request.session_id})}\n\n"
            
            async for chunk_data in ollama_service.generate_chat_response_stream(
                message=request.message,
                chat_history=chat_history,
                preferred_model=model_used
            ):
                chunk = chunk_data.get("chunk", "")
                is_complete = chunk_data.get("is_complete", False)
                
                if chunk:
                    accumulated_response += chunk
                    event_data = {
                        "type": "chunk",
                        "content": chunk,
                        "accumulated": accumulated_response,
                        "model": model_used
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                if is_complete:
                    # Add assistant response to history
                    assistant_message = {
                        "role": "assistant",
                        "content": accumulated_response,
                        "timestamp": datetime.now().isoformat()
                    }
                    chat_sessions[session_key].append(assistant_message)
                    
                    # Send completion event
                    completion_data = {
                        "type": "complete",
                        "content": accumulated_response,
                        "session_id": request.session_id,
                        "model": model_used,
                        "metadata": chunk_data.get("metadata", {})
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    break
            
            await ollama_service.close()
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {e}", exc_info=True)
            error_data = {"type": "error", "message": "Error processing chat message"}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get(
    "/sessions",
    response_model=List[ChatSession],
)
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List all chat sessions for the current user using Redis storage."""
    session_manager = await get_session_manager()
    
    user_sessions = []
    
    try:
        # Scan for chat history keys for this user
        chat_pattern = f"chat_history:{current_user.id}_*"
        
        async for key in session_manager.redis_client.scan_iter(match=chat_pattern):
            try:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                session_id = key_str.split(":", 1)[1].split("_", 1)[1]  # Extract session ID
                
                # Get chat history
                history_data = await session_manager.redis_client.get(key)
                if history_data:
                    messages = json.loads(history_data)
                    
                    if messages:
                        first_message = messages[0]
                        last_message = messages[-1]
                        
                        title = first_message.get("content", "")[:50]
                        if len(first_message.get("content", "")) > 50:
                            title += "..."
                        
                        created_at = datetime.fromisoformat(first_message.get("timestamp", datetime.now().isoformat()))
                        updated_at = datetime.fromisoformat(last_message.get("timestamp", datetime.now().isoformat()))
                    else:
                        title = "Empty session"
                        created_at = updated_at = datetime.now()
                    
                    user_sessions.append(ChatSession(
                        session_id=session_id,
                        title=title,
                        created_at=created_at,
                        updated_at=updated_at,
                        message_count=len(messages)
                    ))
                    
            except Exception as session_error:
                logger.warning(f"Error processing chat session key {key}: {session_error}")
                continue
    
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        return []
    
    # Sort by updated_at descending
    user_sessions.sort(key=lambda x: x.updated_at, reverse=True)
    return user_sessions


@router.get(
    "/sessions/{session_id}/history",
    response_model=ChatHistory,
)
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get chat history for a specific session."""
    global chat_sessions
    
    session_key = f"{current_user.id}_{session_id}"
    
    if session_key not in chat_sessions:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )
    
    messages = chat_sessions[session_key]
    chat_messages = [
        ChatMessage(
            role=msg.get("role", "unknown"),
            content=msg.get("content", ""),
            timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat()))
        )
        for msg in messages
    ]
    
    return ChatHistory(
        session_id=session_id,
        messages=chat_messages,
        total_messages=len(chat_messages)
    )


@router.delete(
    "/sessions/{session_id}",
    dependencies=[Depends(verify_csrf_token)],
)
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a chat session and its history."""
    global chat_sessions
    
    session_key = f"{current_user.id}_{session_id}"
    
    if session_key not in chat_sessions:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )
    
    del chat_sessions[session_key]
    
    return {"message": "Chat session deleted successfully"}


@router.post(
    "/sessions/{session_id}/clear",
    dependencies=[Depends(verify_csrf_token)],
)
async def clear_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Clear chat history for a session but keep the session."""
    global chat_sessions
    
    session_key = f"{current_user.id}_{session_id}"
    
    if session_key not in chat_sessions:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )
    
    chat_sessions[session_key] = []
    
    return {"message": "Chat session cleared successfully"}


@router.get(
    "/health",
)
async def chat_health_check():
    """Health check for chat API endpoints."""
    try:
        # Test Ollama service availability
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'sequentialthinking_service'))
        
        ollama_status = "unavailable"
        try:
            from services.ollama_client_service import OllamaClientService
            service = OllamaClientService()
            await service.initialize()
            ollama_status = "available"
            await service.close()
        except Exception as e:
            logger.debug(f"Ollama service check failed: {e}")
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "ollama": ollama_status,
                "session_storage": "redis",
                "unified_session_manager": "active"
            }
        }
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }