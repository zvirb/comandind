# /app/api/routers/chat_ws.py

import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Depends
from api.dependencies import get_current_user_ws
from shared.database.models import User

from ..progress_manager import progress_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Enhanced Chat WebSocket endpoint with robust authentication and error handling.
    Handles authentication manually to control WebSocket accept/reject flow.
    """
    import urllib.parse
    from typing import Optional
    
    # Manual authentication to control WebSocket handshake
    token: Optional[str] = None
    current_user: Optional[User] = None
    
    try:
        # Extract token from query parameter
        from urllib.parse import parse_qs
        query_params = parse_qs(str(websocket.url.query))
        token = query_params.get('token', [None])[0]
        
        # Extract token from WebSocket subprotocol if not in query
        if token is None:
            protocols = websocket.headers.get("sec-websocket-protocol", "")
            for protocol in protocols.split(","):
                protocol = protocol.strip()
                if protocol.startswith("Bearer."):
                    token = protocol[7:]  # Remove "Bearer." prefix
                    break
        
        if token is None:
            logger.error("No authentication token provided")
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        # Clean token
        decoded_token = urllib.parse.unquote(token)
        cleaned_token = decoded_token.strip('"').replace("Bearer ", "").strip()
        
        # Validate JWT
        from api.auth import SECRET_KEY, ALGORITHM
        import jwt
        
        payload = jwt.decode(
            cleaned_token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM],
            options={"verify_exp": True, "verify_nbf": False, "verify_iat": False, "verify_aud": False},
            leeway=60
        )
        
        # Extract user info
        user_email = None
        if "email" in payload and "sub" in payload:
            try:
                sub_value = payload.get("sub")
                if isinstance(sub_value, int) or sub_value.isdigit():
                    user_email = payload.get("email")
            except (ValueError, TypeError, AttributeError):
                pass
        
        if not user_email:
            sub_value = payload.get("sub")
            if sub_value and "@" in str(sub_value):
                user_email = sub_value
        
        if not user_email:
            logger.error("No email found in token")
            await websocket.close(code=1008, reason="Invalid token payload")
            return
        
        # Get user from database
        from shared.utils.database_setup import get_db
        from api.auth import get_user_by_email
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            current_user = get_user_by_email(db, email=user_email)
            if not current_user or not current_user.is_active:
                logger.error(f"User not found or inactive: {user_email}")
                await websocket.close(code=1008, reason="User not found or inactive")
                return
        finally:
            db.close()
        
        # Accept WebSocket connection after successful authentication
        await websocket.accept()
        
    except jwt.ExpiredSignatureError:
        logger.error("JWT token expired")
        await websocket.close(code=1008, reason="Token expired")
        return
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}", exc_info=True)
        await websocket.close(code=1011, reason="Authentication error")
        return
    
    # Extract session ID from query parameters or generate one
    session_id = query_params.get('session_id', [None])[0]
    if not session_id:
        import uuid
        session_id = f"chat_{uuid.uuid4().hex[:16]}"
    
    logger.info(f"Chat WebSocket connected: session {session_id} for user {current_user.id}")
    
    # Send initial connection confirmation
    await websocket.send_text(json.dumps({
        "type": "connection_confirmed",
        "session_id": session_id,
        "user_id": current_user.id,
        "message": "Chat WebSocket connected successfully",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        # Connect to progress manager for message handling
        await progress_manager.connect(websocket, current_user.id, session_id)
        
        while True:
            # Handle incoming messages from the client
            try:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "unknown")
                    
                    logger.debug(f"Received message type '{message_type}' for session {session_id}")
                    
                    if message_type == "ready":
                        # Client ready confirmation
                        await websocket.send_text(json.dumps({
                            "type": "ready_confirmed",
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                    elif message_type == "message" or message_type == "chat_message":
                        # Handle chat message - send to AI backend
                        await handle_chat_message(session_id, message, current_user.id, websocket)
                        
                    elif message_type == "ping":
                        # Handle ping messages to keep connection alive
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                        
                    else:
                        logger.debug(f"Forwarding message type '{message_type}' to progress manager")
                        # Forward other messages to progress manager
                        await progress_manager.broadcast_to_session(session_id, message)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON received from chat WebSocket client: {data[:200]}... Error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }))
                except Exception as e:
                    logger.error(f"Error processing chat WebSocket message: {e}", exc_info=True)
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "Message processing failed",
                        "details": str(e),
                        "timestamp": datetime.now().isoformat()
                    }))
                    
            except asyncio.CancelledError:
                logger.info(f"Chat WebSocket connection cancelled for session {session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket connection error for session {session_id}: {e}", exc_info=True)
                break
                
    except Exception as e:
        logger.error(f"Chat WebSocket error for session {session_id}: {e}", exc_info=True)
    finally:
        logger.info(f"Chat WebSocket disconnected: session {session_id} for user {current_user.id}")
        try:
            progress_manager.disconnect(session_id)
        except Exception as e:
            logger.error(f"Error disconnecting from progress manager: {e}")


@router.websocket("/chat/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Path(...),
    current_user: User = Depends(get_current_user_ws)
):
    """
    Handles the WebSocket connection for a specific chat session.
    Enhanced with human context integration.
    """
    await progress_manager.connect(websocket, current_user.id, session_id)
    try:
        while True:
            # Handle incoming messages from the client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "human_context":
                    # Handle human context submission
                    await handle_human_context(session_id, message, current_user.id)
                elif message_type == "mission_confirmation":
                    # Handle mission contradiction confirmation
                    await handle_mission_confirmation(session_id, message, current_user.id)
                elif message_type == "ping":
                    # Handle ping messages to keep connection alive
                    await websocket.send_text(json.dumps({"type": "pong"}))
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client: {data}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                
    except WebSocketDisconnect:
        progress_manager.disconnect(session_id)


async def handle_chat_message(session_id: str, message: dict, user_id: str, websocket: WebSocket):
    """
    Handle chat message by forwarding to AI backend and streaming response.
    
    Args:
        session_id: The session ID
        message: The WebSocket message containing chat content
        user_id: The user ID
        websocket: The WebSocket connection for sending responses
    """
    try:
        # Extract message content - handle both field names for compatibility
        content = message.get("content") or message.get("message", "")
        if not content:
            logger.warning("Empty chat message content received")
            return
        
        # Create chat task for AI backend
        chat_data = {
            "message": content,
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "stream": True  # Enable streaming responses
        }
        
        # Send confirmation that message was received
        await websocket.send_text(json.dumps({
            "type": "message_received",
            "content": content,
            "session_id": session_id,
            "status": "processing"
        }))
        
        # Send chat task to worker via Celery
        try:
            # Send directly to Celery task instead of Redis pub/sub
            from fastapi import Request
            import asyncio
            
            # Get the Celery app from FastAPI state  
            from api.main import app as fastapi_app
            
            # Check if we have access to the app state
            try:
                # In production, we'll have access to the app state
                # For testing, we'll create a Celery client
                celery_app = getattr(fastapi_app.state, 'celery_app', None)
                
                if celery_app is None:
                    # Fallback to creating Celery app
                    from celery import Celery
                    from shared.utils.config import get_settings
                    settings = get_settings()
                    celery_app = Celery(
                        "chat_client",
                        broker=str(settings.REDIS_URL),
                        backend=str(settings.REDIS_URL)
                    )
                
                # Execute the chat graph task
                task_result = celery_app.send_task(
                    "tasks.execute_chat_graph",
                    args=[session_id, user_id, content, None],  # session_id, user_id, user_input, current_graph_state_dict
                    queue="celery"
                )
                
                logger.info(f"Chat task sent to Celery worker: {task_result.id} for session {session_id}")
                
                # Send task ID confirmation to client
                await websocket.send_text(json.dumps({
                    "type": "task_started",
                    "task_id": task_result.id,
                    "session_id": session_id,
                    "status": "processing"
                }))
                
            except Exception as celery_error:
                logger.error(f"Failed to send Celery task: {celery_error}")
                
                # Fallback to Redis pub/sub method
                await progress_manager.send_chat_message(session_id, chat_data)
                logger.info(f"Fallback: Chat message sent via Redis pub/sub for session {session_id}")
            
            logger.info(f"Chat message forwarded to AI backend for session {session_id}: {content[:100]}...")
            
        except Exception as e:
            logger.error(f"Failed to send chat message to worker: {e}", exc_info=True)
            
            # Send error response to client
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": "Failed to process message. Please try again.",
                "session_id": session_id,
                "status": "error"
            }))
            
            # Also send a mock response to prevent UI hanging
            await websocket.send_text(json.dumps({
                "type": "message",
                "content": "I'm experiencing some technical difficulties. The chat system is being updated to connect to the AI backend. Please try again shortly.",
                "session_id": session_id,
                "status": "temporary_response"
            }))
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}", exc_info=True)
        
        # Send error response to client
        await websocket.send_text(json.dumps({
            "type": "error",
            "error": str(e),
            "session_id": session_id,
            "status": "error"
        }))


async def handle_human_context(session_id: str, message: dict, user_id: str):
    """
    Handle human context submission from the WebSocket client.
    
    Args:
        session_id: The session ID
        message: The WebSocket message containing human context
        user_id: The user ID
    """
    try:
        # Extract context from message
        context_text = message.get("context", "")
        context_type = message.get("context_type", "general")
        priority = message.get("priority", "medium")
        injection_point = message.get("injection_point", "user_input")
        
        if not context_text:
            logger.warning("Empty context text received")
            return
        
        # Create human context model data
        context_data = {
            "context_text": context_text,
            "timestamp": datetime.now().isoformat(),
            "injection_point": injection_point,
            "priority": priority,
            "context_type": context_type,
            "session_id": session_id
        }
        
        # Send human context to the worker via progress manager
        await progress_manager.send_human_context(session_id, context_data)
        
        # Broadcast confirmation to all clients in the session
        await progress_manager.broadcast_to_session(session_id, {
            "type": "human_context_submitted",
            "context": context_data,
            "status": "success"
        })
        
        logger.info(f"Human context submitted for session {session_id}: {context_text}")
        
    except Exception as e:
        logger.error(f"Error handling human context: {e}", exc_info=True)
        
        # Send error response to client
        await progress_manager.broadcast_to_session(session_id, {
            "type": "human_context_error",
            "error": str(e),
            "status": "error"
        })


async def handle_mission_confirmation(session_id: str, message: dict, user_id: str):
    """
    Handle mission contradiction confirmation from the WebSocket client.
    
    Args:
        session_id: The session ID
        message: The WebSocket message containing mission confirmation
        user_id: The user ID
    """
    try:
        # Extract confirmation from message
        confirmation = message.get("confirmation", "").upper()
        reasoning = message.get("reasoning", "")
        
        if confirmation not in ["YES", "NO"]:
            await progress_manager.broadcast_to_session(session_id, {
                "type": "mission_confirmation_error",
                "error": "Please respond with 'YES' or 'NO'",
                "status": "error"
            })
            return
        
        # Create human context for the confirmation
        context_data = {
            "context_text": f"Mission contradiction confirmation: {confirmation}. Reasoning: {reasoning}",
            "timestamp": datetime.now().isoformat(),
            "injection_point": "mission_confirmation",
            "priority": "high",
            "context_type": "confirmation",
            "session_id": session_id,
            "confirmation": confirmation,
            "reasoning": reasoning
        }
        
        # Send confirmation to the worker via progress manager
        await progress_manager.send_human_context(session_id, context_data)
        
        # Broadcast confirmation to all clients in the session
        await progress_manager.broadcast_to_session(session_id, {
            "type": "mission_confirmation_submitted",
            "confirmation": confirmation,
            "reasoning": reasoning,
            "status": "success"
        })
        
        logger.info(f"Mission confirmation submitted for session {session_id}: {confirmation}")
        
    except Exception as e:
        logger.error(f"Error handling mission confirmation: {e}", exc_info=True)
        
        # Send error response to client
        await progress_manager.broadcast_to_session(session_id, {
            "type": "mission_confirmation_error",
            "error": str(e),
            "status": "error"
        })
