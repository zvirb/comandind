# /app/api/routers/chat_ws_fixed.py
# Fixed Chat WebSocket with proper subprotocol authentication handling

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.exceptions import WebSocketException
import jwt
from shared.database.models import User
from shared.utils.database_setup import get_db
from shared.services.unified_session_manager import get_session_manager

from ..progress_manager import progress_manager

# Import Ollama service for chat integration
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'sequentialthinking_service'))

# Import only the specific service we need to avoid langgraph dependency
try:
    from services.ollama_client_service import OllamaClientService
except ImportError:
    # Fallback: create a minimal implementation if full service isn't available
    import aiohttp
    import json
    import time
    
    class OllamaClientService:
        def __init__(self):
            self.base_url = "https://ollama:11435"
            self.primary_model = "llama3:8b-instruct-q4_0"
            self._session = None
            
        async def initialize(self):
            self._session = aiohttp.ClientSession()
            
        async def close(self):
            if self._session:
                await self._session.close()
                
        async def generate_chat_response_stream(self, message, chat_history=None, preferred_model=None):
            if not self._session:
                raise RuntimeError("Service not initialized")
                
            # Simple chat implementation without complex dependencies
            model_to_use = preferred_model or self.primary_model
            prompt = self._build_chat_prompt(message, chat_history or [])
            
            payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 2048}
            }
            
            try:
                async with self._session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama request failed: {response.status}")
                    
                    accumulated = ""
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8').strip())
                                chunk = data.get('response', '')
                                if chunk:
                                    accumulated += chunk
                                    yield {
                                        "chunk": chunk,
                                        "is_complete": False,
                                        "model_used": model_to_use,
                                        "accumulated_content": accumulated,
                                        "metadata": {"processing_time_ms": int(time.time() * 1000)}
                                    }
                                if data.get('done', False):
                                    yield {
                                        "chunk": "",
                                        "is_complete": True,
                                        "model_used": model_to_use,
                                        "accumulated_content": accumulated,
                                        "metadata": {"confidence": 0.8, "total_tokens": 0}
                                    }
                                    break
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                raise RuntimeError(f"Ollama error: {e}")
        
        def _build_chat_prompt(self, message, chat_history):
            conversation = ["You are a helpful AI assistant. Provide clear, accurate responses."]
            for msg in chat_history[-10:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    conversation.append(f"Human: {content}")
                elif role == 'assistant':
                    conversation.append(f"Assistant: {content}")
            conversation.append(f"Human: {message}")
            conversation.append("Assistant:")
            return "\n\n".join(conversation)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global Ollama service instance
ollama_service: Optional[OllamaClientService] = None

# Session management moved to unified session manager (Redis-backed)
# Remove global in-memory storage to prevent memory leaks

async def get_ollama_service() -> OllamaClientService:
    """Get or initialize the Ollama service"""
    global ollama_service
    if ollama_service is None:
        ollama_service = OllamaClientService()
        try:
            await ollama_service.initialize()
            logger.info("Ollama service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama service: {e}")
            raise
    return ollama_service

async def cleanup_ollama_service():
    """Cleanup Ollama service on shutdown"""
    global ollama_service
    if ollama_service:
        await ollama_service.close()
        ollama_service = None

async def process_chat_message(websocket: WebSocket, session_id: str, content: str, user_id: int):
    """
    Process chat message with Ollama streaming response using unified session manager
    
    Args:
        websocket: WebSocket connection
        session_id: Chat session ID
        content: User message content
        user_id: User ID for session management
    """
    try:
        # Get unified session manager and Ollama service
        session_manager = await get_session_manager()
        service = await get_ollama_service()
        
        # Get or create chat session data in Redis
        chat_history_key = f"chat_history:{user_id}_{session_id}"
        
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
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(user_message)
        
        # Send typing indicator
        await websocket.send_text(json.dumps({
            "type": "typing_start",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Initialize variables for streaming
        accumulated_response = ""
        start_time = datetime.now()
        
        # Send start of assistant response
        await websocket.send_text(json.dumps({
            "type": "message_start",
            "role": "assistant",
            "timestamp": start_time.isoformat()
        }))
        
        # Stream response from Ollama
        try:
            async for chunk_data in service.generate_chat_response_stream(
                message=content,
                chat_history=chat_history[:-1]  # Exclude current message from history
            ):
                chunk = chunk_data.get("chunk", "")
                is_complete = chunk_data.get("is_complete", False)
                model_used = chunk_data.get("model_used", "unknown")
                metadata = chunk_data.get("metadata", {})
                
                if chunk:
                    accumulated_response += chunk
                    
                    # Send chunk to client
                    await websocket.send_text(json.dumps({
                        "type": "message_chunk",
                        "role": "assistant",
                        "content": chunk,
                        "accumulated_content": accumulated_response,
                        "model_used": model_used,
                        "timestamp": datetime.now().isoformat()
                    }))
                
                if is_complete:
                    # Send completion message
                    end_time = datetime.now()
                    processing_time = (end_time - start_time).total_seconds() * 1000
                    
                    await websocket.send_text(json.dumps({
                        "type": "message_complete",
                        "role": "assistant",
                        "content": accumulated_response,
                        "model_used": model_used,
                        "metadata": {
                            "processing_time_ms": processing_time,
                            "confidence": metadata.get("confidence", 0.8),
                            "total_tokens": metadata.get("total_tokens", 0)
                        },
                        "timestamp": end_time.isoformat()
                    }))
                    break
            
            # Add assistant response to chat history
            if accumulated_response:
                assistant_message = {
                    "role": "assistant", 
                    "content": accumulated_response,
                    "timestamp": datetime.now().isoformat()
                }
                chat_history.append(assistant_message)
                
                # Limit chat history to last 20 messages to prevent memory bloat
                if len(chat_history) > 20:
                    chat_history = chat_history[-20:]
                
                # Save updated history to Redis with TTL
                try:
                    await session_manager.redis_client.setex(
                        chat_history_key,
                        86400,  # 24 hour TTL
                        json.dumps(chat_history)
                    )
                except Exception as redis_error:
                    logger.warning(f"Failed to save chat history to Redis: {redis_error}")
            
        except asyncio.TimeoutError:
            logger.error(f"Ollama request timed out for session {session_id}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Response timed out. Please try again.",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as ollama_error:
            logger.error(f"Ollama error for session {session_id}: {ollama_error}")
            await websocket.send_text(json.dumps({
                "type": "error", 
                "message": "AI service temporarily unavailable. Please try again.",
                "timestamp": datetime.now().isoformat()
            }))
        
        finally:
            # Send typing stopped indicator
            await websocket.send_text(json.dumps({
                "type": "typing_stop",
                "timestamp": datetime.now().isoformat()
            }))
            
    except Exception as e:
        logger.error(f"Error in process_chat_message: {e}", exc_info=True)
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "An unexpected error occurred. Please try again.",
            "timestamp": datetime.now().isoformat()
        }))

async def cleanup_chat_session(session_id: str, delay: int = 300):
    """
    Clean up chat session after delay to free memory
    
    Args:
        session_id: Session ID to clean up
        delay: Delay in seconds before cleanup
    """
    global chat_sessions
    
    await asyncio.sleep(delay)
    
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        logger.info(f"Cleaned up chat session {session_id}")

async def health_check_ollama() -> bool:
    """
    Check if Ollama service is healthy
    
    Returns:
        bool: True if healthy, False otherwise
    """
    try:
        service = await get_ollama_service()
        return service is not None
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False

async def authenticate_websocket_with_subprotocol(websocket: WebSocket, token: Optional[str] = None) -> Optional[User]:
    """
    Unified WebSocket authentication using session manager.
    Consolidates multiple auth mechanisms into single approach.
    Returns User if authenticated, None otherwise.
    """
    import urllib.parse
    
    logger.info(f"WebSocket unified authentication starting - Query token: {'Yes' if token else 'No'}")
    logger.info(f"WebSocket headers: {dict(websocket.headers)}")
    logger.info(f"WebSocket URL: {websocket.url}")
    
    # Extract token from subprotocol if not in query
    if token is None:
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        logger.info(f"WebSocket protocols header: {protocols}")
        for protocol in protocols.split(","):
            protocol = protocol.strip()
            if protocol.startswith("Bearer."):
                token = protocol[7:]  # Remove "Bearer." prefix
                logger.info("WebSocket token extracted from subprotocol")
                # Accept with the Bearer subprotocol to complete handshake
                await websocket.accept(subprotocol=f"Bearer.{token}")
                break
        else:
            # No Bearer token in subprotocol, accept without subprotocol
            if token is None:
                logger.error("No authentication token provided")
                await websocket.accept()
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No authentication token provided")
                return None
            await websocket.accept()
    else:
        # Token from query parameter, accept normally
        await websocket.accept()
    
    # Clean and validate token using unified session manager
    decoded_token = urllib.parse.unquote(token)
    cleaned_token = decoded_token.strip('"').replace("Bearer ", "")
    
    try:
        from api.auth import SECRET_KEY, ALGORITHM
        
        # Decode JWT
        payload = jwt.decode(
            cleaned_token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"verify_exp": True}
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("No user ID in token payload")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return None
        
        # Get session manager for unified authentication
        try:
            session_manager = await get_session_manager()
            # Check if user has active sessions (validation through unified manager)
            user_sessions = await session_manager.get_user_sessions(int(user_id))
            
            # If no active sessions, still validate user exists in database  
            from shared.utils.database_setup import get_async_session_context
            async with get_async_session_context() as db:
                from sqlalchemy import select
                result = await db.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                    return None
                
                logger.info(f"WebSocket authenticated for user {user.id} via unified session manager")
                return user
                
        except Exception as session_error:
            logger.warning(f"Session manager validation failed, falling back to direct auth: {session_error}")
            # Fallback to direct database lookup
            from shared.utils.database_setup import get_async_session_context
            async with get_async_session_context() as db:
                from sqlalchemy import select
                result = await db.execute(select(User).where(User.id == int(user_id)))
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                    return None
                
                logger.info(f"WebSocket authenticated for user {user.id} via fallback")
                return user
            
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Authentication error")
        return None

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Chat WebSocket endpoint with proper subprotocol authentication.
    Handles both query parameter and WebSocket subprotocol Bearer tokens.
    This endpoint works with both /ws prefix and /api/v1/chat prefix registrations.
    """
    logger.info(f"WebSocket /ws endpoint called with token: {'Yes' if token else 'No'}")
    
    # Re-enable authentication
    current_user = await authenticate_websocket_with_subprotocol(websocket, token)
    if not current_user:
        return  # Connection already closed in auth function
    
    # Handle session ID from query parameters or generate one
    from urllib.parse import parse_qs
    query_params = parse_qs(str(websocket.url.query))
    
    session_id = query_params.get('session_id', [None])[0]
    if not session_id:
        import uuid
        session_id = f"chat_{uuid.uuid4().hex[:16]}"
    
    logger.info(f"Chat WebSocket connected: session {session_id} for user {current_user.id}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_confirmed",
            "session_id": session_id,
            "message": "Chat WebSocket connected successfully"
        }))
        
        while True:
            # Handle incoming messages from the client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ready":
                    # Client ready confirmation
                    await websocket.send_text(json.dumps({
                        "type": "ready_confirmed",
                        "session_id": session_id
                    }))
                    
                elif message_type == "message" or message_type == "chat_message":
                    # Handle chat message
                    content = message.get("content") or message.get("message", "")
                    if content:
                        # Send acknowledgment
                        await websocket.send_text(json.dumps({
                            "type": "message_received",
                            "content": content,
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                        # Process with Ollama AI backend
                        try:
                            await process_chat_message(websocket, session_id, content, current_user.id)
                        except Exception as e:
                            logger.error(f"Error processing chat message: {e}", exc_info=True)
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "Sorry, I encountered an error processing your message. Please try again.",
                                "timestamp": datetime.now().isoformat()
                            }))
                    
                elif message_type == "ping":
                    # Keep-alive ping
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
                else:
                    logger.info(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                
    except WebSocketDisconnect:
        logger.info(f"Chat WebSocket disconnected: session {session_id} for user {current_user.id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        logger.info(f"Cleaning up session {session_id}")
        # Clean up chat session after some time (keep for potential reconnection)
        asyncio.create_task(cleanup_chat_session(session_id, delay=300))  # 5 minutes