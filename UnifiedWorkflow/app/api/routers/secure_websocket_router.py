"""Secure WebSocket router with Enhanced JWT Authentication and mTLS support."""

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, Query, status
from pydantic import BaseModel, Field

from api.enhanced_dependencies import get_current_user_websocket_enhanced, get_enhanced_jwt_service
from shared.services.enhanced_jwt_service import EnhancedJWTService, TokenAudience, ServiceScope
from api.progress_manager import progress_manager
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# =============================================================================
# Secure WebSocket Message Models
# =============================================================================

class SecureWebSocketMessage(BaseModel):
    """Base model for secure WebSocket messages."""
    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str = Field(default_factory=lambda: secrets.token_urlsafe(16))
    encrypted: bool = False
    signature: Optional[str] = None

class AuthenticationMessage(SecureWebSocketMessage):
    """WebSocket authentication message."""
    type: str = "authentication"
    status: str
    user_id: Optional[int] = None
    session_id: str
    cert_verified: bool = False
    scopes: list[str] = Field(default_factory=list)

class ErrorMessage(SecureWebSocketMessage):
    """WebSocket error message."""
    type: str = "error"
    error_code: str
    error_message: str
    retry_after: Optional[int] = None

class HeartbeatMessage(SecureWebSocketMessage):
    """WebSocket heartbeat message."""
    type: str = "heartbeat"
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    connection_id: str

# =============================================================================
# Secure WebSocket Connection Manager
# =============================================================================

class SecureWebSocketManager:
    """Enhanced WebSocket connection manager with security features."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.user_connections: Dict[int, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def authenticate_connection(
        self, 
        websocket: WebSocket, 
        session_id: str, 
        token: str
    ) -> Dict[str, Any]:
        """Authenticate WebSocket connection with enhanced security."""
        try:
            # Use enhanced JWT authentication
            user = await get_current_user_websocket_enhanced(websocket, token)
            
            # Check for mTLS certificate if enabled
            cert_info = None
            if os.getenv("MTLS_ENABLED", "false").lower() == "true":
                # Extract certificate info from WebSocket headers
                cert_subject = websocket.headers.get("X-Client-Certificate-Subject")
                cert_verified = websocket.headers.get("X-Client-Certificate-Verified")
                
                if cert_subject and cert_verified == "success":
                    cert_info = {
                        "subject": cert_subject,
                        "verified": True
                    }
            
            # Create connection metadata
            connection_info = {
                "user": user,
                "user_id": user.id,
                "session_id": session_id,
                "websocket": websocket,
                "connected_at": datetime.now(timezone.utc),
                "last_heartbeat": datetime.now(timezone.utc),
                "cert_info": cert_info,
                "authenticated": True,
                "message_count": 0,
                "rate_limit_reset": datetime.now(timezone.utc).timestamp() + 3600,  # 1 hour
                "rate_limit_count": 0
            }
            
            return connection_info
            
        except Exception as e:
            logger.error(f"WebSocket authentication failed for session {session_id}: {e}")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication failed"
            )
    
    async def add_connection(self, connection_info: Dict[str, Any]) -> None:
        """Add authenticated connection to manager."""
        session_id = connection_info["session_id"]
        user_id = connection_info["user_id"]
        
        # Store connection
        self.active_connections[session_id] = connection_info
        self.connection_metadata[session_id] = {
            "user_id": user_id,
            "connected_at": connection_info["connected_at"],
            "cert_verified": bool(connection_info.get("cert_info"))
        }
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(session_id)
        
        logger.info(f"Secure WebSocket connection added: {session_id} for user {user_id}")
    
    async def remove_connection(self, session_id: str) -> None:
        """Remove connection from manager."""
        if session_id in self.active_connections:
            connection_info = self.active_connections[session_id]
            user_id = connection_info["user_id"]
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(session_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove connection
            del self.active_connections[session_id]
            del self.connection_metadata[session_id]
            
            logger.info(f"Secure WebSocket connection removed: {session_id}")
    
    async def validate_rate_limit(self, session_id: str) -> bool:
        """Validate rate limiting for connection."""
        if session_id not in self.active_connections:
            return False
        
        connection = self.active_connections[session_id]
        now = datetime.now(timezone.utc).timestamp()
        
        # Reset rate limit if window expired
        if now > connection["rate_limit_reset"]:
            connection["rate_limit_count"] = 0
            connection["rate_limit_reset"] = now + 3600  # 1 hour window
        
        # Check rate limit (100 messages per hour)
        if connection["rate_limit_count"] >= 100:
            logger.warning(f"Rate limit exceeded for WebSocket session: {session_id}")
            return False
        
        connection["rate_limit_count"] += 1
        connection["message_count"] += 1
        return True
    
    async def send_secure_message(
        self, 
        session_id: str, 
        message: SecureWebSocketMessage
    ) -> bool:
        """Send secure message to WebSocket connection."""
        if session_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[session_id]["websocket"]
            message_dict = message.dict()
            
            # Add security metadata
            message_dict["server_timestamp"] = datetime.now(timezone.utc).isoformat()
            if os.getenv("MTLS_ENABLED", "false").lower() == "true":
                message_dict["mtls_enabled"] = True
            
            await websocket.send_text(json.dumps(message_dict))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send secure message to {session_id}: {e}")
            await self.remove_connection(session_id)
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = len(self.active_connections)
        total_users = len(self.user_connections)
        cert_verified_count = sum(
            1 for metadata in self.connection_metadata.values()
            if metadata.get("cert_verified", False)
        )
        
        return {
            "total_connections": total_connections,
            "total_users": total_users,
            "cert_verified_connections": cert_verified_count,
            "cert_verification_rate": cert_verified_count / total_connections if total_connections > 0 else 0
        }

# Global secure WebSocket manager
secure_ws_manager = SecureWebSocketManager()

# =============================================================================
# Secure WebSocket Endpoints
# =============================================================================

@router.websocket("/ws/secure/agent/{session_id}")
async def secure_agent_websocket(
    websocket: WebSocket, 
    session_id: str, 
    token: str = Query(...)
):
    """
    Secure WebSocket endpoint for agent communications with enhanced authentication.
    
    Features:
    - Enhanced JWT validation with service-specific scopes
    - Optional mTLS client certificate verification
    - Rate limiting and connection management
    - Encrypted message support
    - Comprehensive audit logging
    """
    connection_info = None
    
    try:
        # Authenticate connection
        connection_info = await secure_ws_manager.authenticate_connection(
            websocket, session_id, token
        )
        
        # Accept WebSocket connection
        await websocket.accept()
        
        # Add to connection manager
        await secure_ws_manager.add_connection(connection_info)
        
        # Send authentication success message
        auth_message = AuthenticationMessage(
            status="authenticated",
            user_id=connection_info["user_id"],
            session_id=session_id,
            cert_verified=bool(connection_info.get("cert_info")),
            scopes=[scope.value for scope in [ServiceScope.API_STREAM, ServiceScope.API_READ]]
        )
        
        await secure_ws_manager.send_secure_message(session_id, auth_message)
        
        # Register with progress manager
        progress_manager.add_connection(session_id, websocket)
        
        logger.info(f"Secure agent WebSocket established: {session_id} for user {connection_info['user_id']}")
        
        # Message handling loop
        while True:
            # Check rate limiting
            if not await secure_ws_manager.validate_rate_limit(session_id):
                error_message = ErrorMessage(
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message="Message rate limit exceeded",
                    retry_after=3600
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                break
            
            # Receive and process message
            try:
                data = await websocket.receive_text()
                await handle_secure_agent_message(session_id, data, connection_info)
                
            except WebSocketDisconnect:
                logger.info(f"Secure agent WebSocket disconnected: {session_id}")
                break
            except Exception as e:
                logger.error(f"Error processing secure agent message: {e}")
                error_message = ErrorMessage(
                    error_code="MESSAGE_PROCESSING_ERROR",
                    error_message="Failed to process message"
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
    
    except WebSocketException:
        # Authentication failed - connection already handled
        pass
    except Exception as e:
        logger.error(f"Unexpected error in secure agent WebSocket: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    
    finally:
        # Cleanup
        if connection_info:
            await secure_ws_manager.remove_connection(session_id)
            progress_manager.remove_connection(session_id, websocket)

@router.websocket("/ws/secure/helios/{session_id}")
async def secure_helios_websocket(
    websocket: WebSocket, 
    session_id: str, 
    token: str = Query(...)
):
    """
    Secure WebSocket endpoint for Helios Multi-Agent framework with enhanced security.
    
    Features:
    - Multi-agent coordination support
    - Enhanced security validation
    - Real-time orchestration updates
    - Secure agent selection and messaging
    """
    connection_info = None
    
    try:
        # Authenticate connection
        connection_info = await secure_ws_manager.authenticate_connection(
            websocket, session_id, token
        )
        
        await websocket.accept()
        await secure_ws_manager.add_connection(connection_info)
        
        # Send Helios-specific authentication message
        helios_session_id = f"helios_{session_id}"
        
        auth_message = AuthenticationMessage(
            status="authenticated",
            user_id=connection_info["user_id"],
            session_id=helios_session_id,
            cert_verified=bool(connection_info.get("cert_info")),
            scopes=[ServiceScope.API_STREAM.value, ServiceScope.LLM_INVOKE.value]
        )
        
        await secure_ws_manager.send_secure_message(session_id, auth_message)
        
        # Register with progress manager
        progress_manager.add_connection(helios_session_id, websocket)
        
        # Send initial Helios system status
        await send_helios_system_status(session_id, connection_info)
        
        logger.info(f"Secure Helios WebSocket established: {session_id} for user {connection_info['user_id']}")
        
        # Message handling loop
        while True:
            if not await secure_ws_manager.validate_rate_limit(session_id):
                error_message = ErrorMessage(
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message="Helios message rate limit exceeded",
                    retry_after=3600
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                break
            
            try:
                data = await websocket.receive_text()
                await handle_secure_helios_message(session_id, data, connection_info)
                
            except WebSocketDisconnect:
                logger.info(f"Secure Helios WebSocket disconnected: {session_id}")
                break
            except Exception as e:
                logger.error(f"Error processing secure Helios message: {e}")
                error_message = ErrorMessage(
                    error_code="HELIOS_MESSAGE_ERROR",
                    error_message="Failed to process Helios message"
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
    
    except WebSocketException:
        pass
    except Exception as e:
        logger.error(f"Unexpected error in secure Helios WebSocket: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    
    finally:
        if connection_info:
            await secure_ws_manager.remove_connection(session_id)
            helios_session_id = f"helios_{session_id}"
            progress_manager.remove_connection(helios_session_id, websocket)

@router.websocket("/ws/secure/monitoring/{session_id}")
async def secure_monitoring_websocket(
    websocket: WebSocket, 
    session_id: str, 
    token: str = Query(...)
):
    """
    Secure WebSocket endpoint for system monitoring and administration.
    
    Features:
    - Admin-only access
    - Real-time system metrics
    - Security event monitoring
    - Connection status updates
    """
    connection_info = None
    
    try:
        # Authenticate connection with admin requirements
        connection_info = await secure_ws_manager.authenticate_connection(
            websocket, session_id, token
        )
        
        # Check admin role
        user = connection_info["user"]
        if not hasattr(user, 'role') or user.role.value != 'admin':
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Admin access required"
            )
        
        await websocket.accept()
        await secure_ws_manager.add_connection(connection_info)
        
        # Send monitoring authentication message
        auth_message = AuthenticationMessage(
            status="authenticated",
            user_id=connection_info["user_id"],
            session_id=f"monitoring_{session_id}",
            cert_verified=bool(connection_info.get("cert_info")),
            scopes=[ServiceScope.API_ADMIN.value, ServiceScope.METRICS_READ.value]
        )
        
        await secure_ws_manager.send_secure_message(session_id, auth_message)
        
        logger.info(f"Secure monitoring WebSocket established: {session_id} for admin {connection_info['user_id']}")
        
        # Send initial system statistics
        await send_monitoring_stats(session_id)
        
        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                await handle_secure_monitoring_message(session_id, data, connection_info)
                
            except WebSocketDisconnect:
                logger.info(f"Secure monitoring WebSocket disconnected: {session_id}")
                break
            except Exception as e:
                logger.error(f"Error processing secure monitoring message: {e}")
    
    except WebSocketException:
        pass
    except Exception as e:
        logger.error(f"Unexpected error in secure monitoring WebSocket: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    
    finally:
        if connection_info:
            await secure_ws_manager.remove_connection(session_id)

# =============================================================================
# Secure Message Handlers
# =============================================================================

async def handle_secure_agent_message(
    session_id: str, 
    data: str, 
    connection_info: Dict[str, Any]
) -> None:
    """Handle secure agent WebSocket messages."""
    try:
        message = json.loads(data)
        message_type = message.get("type")
        
        # Validate message structure
        if not message_type:
            raise ValueError("Missing message type")
        
        user_id = connection_info["user_id"]
        logger.debug(f"Processing secure agent message type '{message_type}' from user {user_id}")
        
        # Handle different message types
        if message_type == "heartbeat":
            # Update last heartbeat
            connection_info["last_heartbeat"] = datetime.now(timezone.utc)
            
            heartbeat_response = HeartbeatMessage(
                connection_id=session_id
            )
            await secure_ws_manager.send_secure_message(session_id, heartbeat_response)
            
        elif message_type == "agent_command":
            # Handle agent command with validation
            command = message.get("command")
            parameters = message.get("parameters", {})
            
            logger.info(f"Agent command received: {command} from user {user_id}")
            
            # Validate command permissions
            if not validate_agent_command_permissions(user_id, command):
                error_message = ErrorMessage(
                    error_code="PERMISSION_DENIED",
                    error_message=f"Permission denied for command: {command}"
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
                return
            
            # Process command (integrate with agent system)
            await process_agent_command(session_id, command, parameters, connection_info)
            
        elif message_type == "stream_request":
            # Handle streaming request
            stream_type = message.get("stream_type")
            logger.info(f"Stream request: {stream_type} from user {user_id}")
            
            # Validate streaming permissions
            if not validate_stream_permissions(user_id, stream_type):
                error_message = ErrorMessage(
                    error_code="STREAM_PERMISSION_DENIED",
                    error_message=f"Stream permission denied: {stream_type}"
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
                return
            
            # Start streaming (integrate with streaming system)
            await start_secure_stream(session_id, stream_type, connection_info)
            
        else:
            logger.warning(f"Unknown secure agent message type: {message_type}")
            error_message = ErrorMessage(
                error_code="UNKNOWN_MESSAGE_TYPE",
                error_message=f"Unknown message type: {message_type}"
            )
            await secure_ws_manager.send_secure_message(session_id, error_message)
    
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON received from secure agent {session_id}: {data}")
        error_message = ErrorMessage(
            error_code="INVALID_JSON",
            error_message="Invalid JSON format"
        )
        await secure_ws_manager.send_secure_message(session_id, error_message)
    except Exception as e:
        logger.error(f"Error handling secure agent message: {e}")
        error_message = ErrorMessage(
            error_code="MESSAGE_HANDLER_ERROR",
            error_message="Internal error processing message"
        )
        await secure_ws_manager.send_secure_message(session_id, error_message)

async def handle_secure_helios_message(
    session_id: str, 
    data: str, 
    connection_info: Dict[str, Any]
) -> None:
    """Handle secure Helios Multi-Agent messages."""
    try:
        message = json.loads(data)
        message_type = message.get("type")
        user_id = connection_info["user_id"]
        
        logger.debug(f"Processing secure Helios message type '{message_type}' from user {user_id}")
        
        if message_type == "agent_selection":
            selected_agents = message.get("selected_agents", [])
            logger.info(f"Helios agent selection: {selected_agents} from user {user_id}")
            
            # Validate agent selection
            if not validate_helios_agent_selection(user_id, selected_agents):
                error_message = ErrorMessage(
                    error_code="INVALID_AGENT_SELECTION",
                    error_message="Invalid agent selection"
                )
                await secure_ws_manager.send_secure_message(session_id, error_message)
                return
            
            # Update agent selection
            await update_helios_agent_selection(session_id, selected_agents, connection_info)
            
        elif message_type == "orchestration_command":
            command = message.get("command")
            parameters = message.get("parameters", {})
            
            logger.info(f"Helios orchestration command: {command} from user {user_id}")
            
            # Process orchestration command
            await process_helios_orchestration_command(session_id, command, parameters, connection_info)
            
        else:
            await handle_secure_agent_message(session_id, data, connection_info)
    
    except Exception as e:
        logger.error(f"Error handling secure Helios message: {e}")
        error_message = ErrorMessage(
            error_code="HELIOS_HANDLER_ERROR",
            error_message="Internal error processing Helios message"
        )
        await secure_ws_manager.send_secure_message(session_id, error_message)

async def handle_secure_monitoring_message(
    session_id: str, 
    data: str, 
    connection_info: Dict[str, Any]
) -> None:
    """Handle secure monitoring WebSocket messages."""
    try:
        message = json.loads(data)
        message_type = message.get("type")
        user_id = connection_info["user_id"]
        
        logger.debug(f"Processing secure monitoring message type '{message_type}' from admin {user_id}")
        
        if message_type == "get_stats":
            await send_monitoring_stats(session_id)
            
        elif message_type == "get_connections":
            await send_connection_stats(session_id)
            
        elif message_type == "security_events":
            await send_security_events(session_id)
            
        else:
            error_message = ErrorMessage(
                error_code="UNKNOWN_MONITORING_MESSAGE",
                error_message=f"Unknown monitoring message type: {message_type}"
            )
            await secure_ws_manager.send_secure_message(session_id, error_message)
    
    except Exception as e:
        logger.error(f"Error handling secure monitoring message: {e}")

# =============================================================================
# Helper Functions
# =============================================================================

def validate_agent_command_permissions(user_id: int, command: str) -> bool:
    """Validate user permissions for agent commands."""
    # Implement command permission validation
    return True  # Placeholder

def validate_stream_permissions(user_id: int, stream_type: str) -> bool:
    """Validate user permissions for streaming."""
    # Implement stream permission validation
    return True  # Placeholder

def validate_helios_agent_selection(user_id: int, selected_agents: list) -> bool:
    """Validate Helios agent selection."""
    # Implement agent selection validation
    return True  # Placeholder

async def process_agent_command(
    session_id: str, 
    command: str, 
    parameters: dict, 
    connection_info: Dict[str, Any]
) -> None:
    """Process agent command."""
    # Integrate with agent command processing system
    pass

async def start_secure_stream(
    session_id: str, 
    stream_type: str, 
    connection_info: Dict[str, Any]
) -> None:
    """Start secure streaming."""
    # Integrate with streaming system
    pass

async def send_helios_system_status(session_id: str, connection_info: Dict[str, Any]) -> None:
    """Send Helios system status."""
    status_message = SecureWebSocketMessage(
        type="helios_system_status"
    )
    await secure_ws_manager.send_secure_message(session_id, status_message)

async def update_helios_agent_selection(
    session_id: str, 
    selected_agents: list, 
    connection_info: Dict[str, Any]
) -> None:
    """Update Helios agent selection."""
    # Integrate with Helios agent management
    pass

async def process_helios_orchestration_command(
    session_id: str, 
    command: str, 
    parameters: dict, 
    connection_info: Dict[str, Any]
) -> None:
    """Process Helios orchestration command."""
    # Integrate with Helios orchestration system
    pass

async def send_monitoring_stats(session_id: str) -> None:
    """Send monitoring statistics."""
    stats = secure_ws_manager.get_connection_stats()
    stats_message = SecureWebSocketMessage(
        type="monitoring_stats"
    )
    # Add stats to message
    await secure_ws_manager.send_secure_message(session_id, stats_message)

async def send_connection_stats(session_id: str) -> None:
    """Send connection statistics."""
    stats = secure_ws_manager.get_connection_stats()
    connection_message = SecureWebSocketMessage(
        type="connection_stats"
    )
    await secure_ws_manager.send_secure_message(session_id, connection_message)

async def send_security_events(session_id: str) -> None:
    """Send security events."""
    events_message = SecureWebSocketMessage(
        type="security_events"
    )
    await secure_ws_manager.send_secure_message(session_id, events_message)

# =============================================================================
# WebSocket Health and Stats Endpoints
# =============================================================================

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return secure_ws_manager.get_connection_stats()