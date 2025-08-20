import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import WebSocket
import redis.asyncio as redis
from datetime import datetime, timezone, timedelta
import jwt

logger = logging.getLogger(__name__)

class WebSocketConnectionInfo:
    """Enhanced connection information with token management."""
    def __init__(self, websocket: WebSocket, user_id: int, session_id: str, token: str = None):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id
        self.token = token
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.token_expires_at: Optional[datetime] = None
        self.refresh_scheduled = False
        self.refresh_attempts = 0
        self.max_refresh_attempts = 3
        
        # Extract token expiration if token is provided
        if token:
            self._extract_token_expiry(token)
    
    def _extract_token_expiry(self, token: str) -> None:
        """Extract expiration time from JWT token."""
        try:
            from api.auth import SECRET_KEY, ALGORITHM
            # Decode without verification to get expiry (verification handled elsewhere)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                self.token_expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                logger.debug(f"Token expiry extracted for session {self.session_id}: {self.token_expires_at}")
        except Exception as e:
            logger.warning(f"Failed to extract token expiry for session {self.session_id}: {e}")
    
    def is_token_near_expiry(self, minutes_before: int = 5) -> bool:
        """Check if token will expire within the specified minutes."""
        if not self.token_expires_at:
            return False
        
        threshold = datetime.now(timezone.utc) + timedelta(minutes=minutes_before)
        return self.token_expires_at <= threshold
    
    def is_token_expired(self) -> bool:
        """Check if token has already expired."""
        if not self.token_expires_at:
            return False
        
        return datetime.now(timezone.utc) >= self.token_expires_at
    
    def should_schedule_refresh(self) -> bool:
        """Determine if token refresh should be scheduled."""
        return (
            self.is_token_near_expiry(5) and
            not self.refresh_scheduled and
            self.refresh_attempts < self.max_refresh_attempts
        )
    
    def update_token(self, new_token: str) -> None:
        """Update connection with new token information."""
        self.token = new_token
        self.refresh_scheduled = False
        self.refresh_attempts = 0
        self._extract_token_expiry(new_token)
        logger.info(f"Token updated for session {self.session_id}, new expiry: {self.token_expires_at}")

class ConnectionManager:
    """Enhanced WebSocket connection manager with token refresh support."""
    def __init__(self):
        # Enhanced connection tracking with token management
        self.active_connections: Dict[str, WebSocketConnectionInfo] = {}
        # Maintain backward compatibility with legacy methods
        self.legacy_connections: Dict[str, List[WebSocket]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub_channel = "chat_progress"
        self.context_channel = "human_context"
        self.pubsub_task: Optional[asyncio.Task] = None
        self.token_monitor_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, user_id: int, session_id: str, token: str = None):
        """Accepts a new WebSocket connection with enhanced token tracking."""
        await websocket.accept()
        
        # Create enhanced connection info with token tracking
        connection_info = WebSocketConnectionInfo(websocket, user_id, session_id, token)
        self.active_connections[session_id] = connection_info
        
        # Maintain legacy compatibility
        if session_id not in self.legacy_connections:
            self.legacy_connections[session_id] = []
        self.legacy_connections[session_id].append(websocket)
        
        # Start token monitoring if not already running
        if not self.token_monitor_task:
            self.token_monitor_task = asyncio.create_task(self._monitor_token_expiry())
        
        logger.info(
            "Enhanced WebSocket connected for session_id: %s, user_id: %s. Token expiry: %s",
            session_id,
            user_id,
            connection_info.token_expires_at.isoformat() if connection_info.token_expires_at else "Unknown",
        )

    def disconnect(self, session_id: str):
        """Removes a WebSocket connection from the session's list."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(
                "WebSocket disconnected for session_id: %s. Remaining connections: %d",
                session_id,
                len(self.active_connections.get(session_id, [])),
            )

    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcasts a JSON message to all clients for a specific session."""
        # Use enhanced connection tracking when available
        if session_id in self.active_connections:
            connection_info = self.active_connections[session_id]
            try:
                await connection_info.websocket.send_json(message)
                connection_info.last_activity = datetime.now(timezone.utc)
                logger.debug(f"Message sent to enhanced session {session_id}")
            except Exception as e:
                logger.error(f"Failed to send message to enhanced session {session_id}: {e}")
                # Remove failed connection
                await self._remove_enhanced_connection(session_id)
        
        # Fallback to legacy connections for backward compatibility
        elif session_id in self.legacy_connections:
            tasks = [conn.send_json(message) for conn in self.legacy_connections[session_id]]
            if tasks:
                logger.info(
                    "Broadcasting message to %d legacy client(s) for session_id: %s",
                    len(tasks),
                    session_id,
                )
                await asyncio.gather(*tasks, return_exceptions=True)

    async def initialize_redis(self, settings):
        """Initialize Redis client for pub/sub communication using individual parameters."""
        try:
            # Use individual parameters like chat service instead of URL
            redis_password = settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USER,
                password=redis_password,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("ConnectionManager Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}", exc_info=True)
            self.redis_client = None

    async def start_redis_listener(self):
        """Start background task to listen for Redis pub/sub messages."""
        if not self.redis_client:
            logger.error("Redis client not initialized, cannot start listener")
            return

        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(self.pubsub_channel)
            logger.info(f"Started Redis pub/sub listener on channel: {self.pubsub_channel}")
            
            self.pubsub_task = asyncio.create_task(self._redis_listener(pubsub))
        except Exception as e:
            logger.error(f"Failed to start Redis listener: {e}", exc_info=True)

    async def _redis_listener(self, pubsub):
        """Background task that listens for Redis pub/sub messages and forwards to WebSocket."""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        session_id = payload.get("session_id")
                        chat_message = payload.get("message")
                        
                        if session_id and chat_message:
                            logger.debug(f"Received Redis message for session {session_id}: {chat_message}")
                            await self.broadcast_to_session(session_id, chat_message)
                        else:
                            logger.warning(f"Invalid Redis message format: {payload}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Redis listener error: {e}", exc_info=True)
        finally:
            await pubsub.close()

    async def stop_redis_listener(self):
        """Stop the Redis pub/sub listener."""
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
            logger.info("Redis pub/sub listener stopped")

        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis client closed")
    
    def add_connection(self, session_id: str, websocket: WebSocket):
        """Add a WebSocket connection to a session (alias for backwards compatibility)."""
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"Added WebSocket connection for session {session_id}. Total: {len(self.active_connections[session_id])}")
    
    def remove_connection(self, session_id: str, websocket: WebSocket):
        """Remove a specific WebSocket connection from a session."""
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                logger.info(f"Removed WebSocket connection for session {session_id}. Remaining: {len(self.active_connections[session_id])}")
                
                # Clean up empty session lists
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                    logger.info(f"Cleaned up empty connection list for session {session_id}")
            except ValueError:
                logger.warning(f"WebSocket connection not found for session {session_id} during removal")
    
    async def send_human_context(self, session_id: str, context_data: Dict[str, Any]):
        """Send human context to the worker via Redis pub/sub."""
        if not self.redis_client:
            logger.error("Redis client not initialized, cannot send human context")
            return
            
        try:
            await self.redis_client.publish(
                f"{self.context_channel}:{session_id}",
                json.dumps(context_data)
            )
            logger.info(f"Sent human context to worker for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to send human context for session {session_id}: {e}", exc_info=True)
    
    async def send_chat_message(self, session_id: str, chat_data: Dict[str, Any]):
        """Send chat message to the worker via Redis pub/sub for AI processing."""
        if not self.redis_client:
            logger.error("Redis client not initialized, cannot send chat message")
            return
            
        try:
            # Add task type to differentiate from human context
            chat_data["task_type"] = "chat_message"
            
            await self.redis_client.publish(
                f"chat_task:{session_id}",
                json.dumps(chat_data)
            )
            logger.info(f"Sent chat message to AI backend for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to send chat message for session {session_id}: {e}", exc_info=True)
    
    async def broadcast_plan_update(self, session_id: str, step_number: int, total_steps: int, current_step: str):
        """Broadcast plan execution progress update."""
        message = {
            "type": "plan_progress",
            "step_number": step_number,
            "total_steps": total_steps,
            "current_step": current_step,
            "progress_percentage": round((step_number / total_steps) * 100) if total_steps > 0 else 0
        }
        await self.broadcast_to_session(session_id, message)
        logger.info(f"Broadcasted plan update to session {session_id}: Step {step_number}/{total_steps}")
    
    async def broadcast_tool_selection(self, session_id: str, tool_id: str, confidence_score: float = 0.0):
        """Broadcast tool selection information."""
        message = {
            "type": "tool_selected",
            "tool_id": tool_id,
            "confidence_score": confidence_score,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_session(session_id, message)
        logger.info(f"Broadcasted tool selection to session {session_id}: {tool_id} (confidence: {confidence_score})")
    
    async def broadcast_step_completion(self, session_id: str, step_number: int, result: str):
        """Broadcast step completion information."""
        message = {
            "type": "step_completed",
            "step_number": step_number,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_session(session_id, message)
        logger.info(f"Broadcasted step completion to session {session_id}: Step {step_number}")
    
    async def broadcast_task_status(self, session_id: str, status: str, message: str = ""):
        """Broadcast general task status updates."""
        status_message = {
            "type": "task_status",
            "status": status,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast_to_session(session_id, status_message)
        logger.info(f"Broadcasted task status to session {session_id}: {status} - {message}")

    async def send_app_ranking_update(self, client_id: str, ranked_apps: List[str]):
        """Sends an app ranking update to a specific client."""
        message = {
            "type": "app_ranking_update",
            "client_id": client_id,
            "ranked_apps": ranked_apps,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        session_id = f"focus_client_{client_id}"
        await self.broadcast_to_session(session_id, message)

    def broadcast_to_session_sync(self, session_id: str, message: Dict[str, Any]):
        """Synchronously broadcasts a message to a session via Redis."""
        if not self.redis_client:
            logger.error("Redis client not initialized. Cannot broadcast synchronously.")
            return

        try:
            # This uses the async redis client in a blocking way.
            # This is not ideal, but it's the simplest way to achieve the goal
            # without adding a separate synchronous redis client.
            asyncio.run(self.redis_client.publish(
                self.pubsub_channel,
                json.dumps({"session_id": session_id, "message": message})
            ))
            logger.info(f"Synchronously broadcasted message to session {session_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast synchronously to session {session_id}: {e}", exc_info=True)
    
    async def _monitor_token_expiry(self):
        """Background task to monitor token expiration and trigger refresh requests."""
        logger.info("Starting WebSocket token expiry monitoring")
        
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                sessions_to_refresh = []
                for session_id, connection_info in self.active_connections.items():
                    if connection_info.should_schedule_refresh():
                        sessions_to_refresh.append(session_id)
                
                for session_id in sessions_to_refresh:
                    await self._request_token_refresh(session_id)
                    
            except asyncio.CancelledError:
                logger.info("Token expiry monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in token expiry monitoring: {e}", exc_info=True)
                # Continue monitoring despite errors
                await asyncio.sleep(10)
    
    async def _request_token_refresh(self, session_id: str):
        """Request token refresh from the client."""
        if session_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[session_id]
        connection_info.refresh_scheduled = True
        connection_info.refresh_attempts += 1
        
        refresh_message = {
            "type": "token_refresh_request",
            "expires_at": connection_info.token_expires_at.isoformat() if connection_info.token_expires_at else None,
            "refresh_deadline": (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat(),
            "message": "Your authentication token will expire soon. Please refresh to maintain connection."
        }
        
        try:
            await connection_info.websocket.send_json(refresh_message)
            logger.info(f"Token refresh request sent to session {session_id}")
        except Exception as e:
            logger.error(f"Failed to send token refresh request to session {session_id}: {e}")
            await self._remove_enhanced_connection(session_id)
    
    async def handle_token_refresh_response(self, session_id: str, new_token: str) -> bool:
        """Handle token refresh response from client."""
        if session_id not in self.active_connections:
            logger.warning(f"Received token refresh for unknown session: {session_id}")
            return False
        
        connection_info = self.active_connections[session_id]
        
        try:
            # Validate the new token
            from api.auth import SECRET_KEY, ALGORITHM
            payload = jwt.decode(new_token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Update connection with new token
            connection_info.update_token(new_token)
            
            # Send confirmation
            confirmation_message = {
                "type": "token_refresh_confirmed",
                "new_expires_at": connection_info.token_expires_at.isoformat() if connection_info.token_expires_at else None,
                "message": "Token successfully refreshed"
            }
            
            await connection_info.websocket.send_json(confirmation_message)
            logger.info(f"Token refresh completed for session {session_id}")
            return True
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Received expired token refresh for session {session_id}")
            await self._send_token_refresh_error(session_id, "Token already expired")
            return False
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token refresh for session {session_id}: {e}")
            await self._send_token_refresh_error(session_id, "Invalid token format")
            return False
        except Exception as e:
            logger.error(f"Error processing token refresh for session {session_id}: {e}")
            await self._send_token_refresh_error(session_id, "Token refresh failed")
            return False
    
    async def _send_token_refresh_error(self, session_id: str, error_message: str):
        """Send token refresh error message to client."""
        if session_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[session_id]
        error_response = {
            "type": "token_refresh_error",
            "error": error_message,
            "message": "Token refresh failed. Connection may be terminated soon."
        }
        
        try:
            await connection_info.websocket.send_json(error_response)
        except Exception as e:
            logger.error(f"Failed to send token refresh error to session {session_id}: {e}")
    
    async def _remove_enhanced_connection(self, session_id: str):
        """Remove enhanced connection and cleanup."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Removed enhanced WebSocket connection for session {session_id}")
        
        # Also cleanup legacy connections
        if session_id in self.legacy_connections:
            del self.legacy_connections[session_id]
    
    async def cleanup_expired_connections(self):
        """Clean up connections with expired tokens."""
        expired_sessions = []
        
        for session_id, connection_info in self.active_connections.items():
            if connection_info.is_token_expired() and connection_info.refresh_attempts >= connection_info.max_refresh_attempts:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired connection for session {session_id}")
            await self._remove_enhanced_connection(session_id)
            
            # Send final expiration message
            expiration_message = {
                "type": "connection_expired",
                "message": "Authentication token has expired. Please login again to reconnect."
            }
            
            try:
                # Try to send final message before disconnect
                connection_info = self.active_connections.get(session_id)
                if connection_info:
                    await connection_info.websocket.send_json(expiration_message)
                    await connection_info.websocket.close(code=1008, reason="Token expired")
            except Exception as e:
                logger.debug(f"Could not send final expiration message to {session_id}: {e}")

# Create a single, global instance of the ConnectionManager
progress_manager = ConnectionManager()
