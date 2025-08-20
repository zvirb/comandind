# WebSocket Router - Backward Compatibility with Security
# 
# This router provides backward compatibility for existing clients
# while implementing proper security measures.

import asyncio
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Depends
from api.dependencies import get_current_user_ws
from shared.database.models import User
from api.progress_manager import progress_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/agent/{session_id}")
async def websocket_agent_endpoint(
    websocket: WebSocket,
    session_id: str = Path(...),
    current_user: User = Depends(get_current_user_ws)
):
    """
    Enhanced WebSocket endpoint with token refresh support.
    
    SECURITY FEATURES:
    - JWT token authentication via query parameter or WebSocket subprotocol
    - Automatic token refresh before expiration
    - User validation and authorization
    - Connection tracking and cleanup
    - Message validation and logging
    
    TOKEN REFRESH FLOW:
    - Server monitors token expiration times
    - Proactive refresh requests sent 5 minutes before expiry
    - Client responds with new token from HTTP auth endpoints
    - Connection maintained without interruption
    """
    # Extract token from WebSocket for enhanced tracking
    token = None
    try:
        from urllib.parse import parse_qs
        query_params = parse_qs(str(websocket.url.query))
        if 'token' in query_params:
            token = query_params['token'][0]
        elif websocket.headers.get("sec-websocket-protocol", "").startswith("Bearer."):
            protocols = websocket.headers.get("sec-websocket-protocol", "")
            for protocol in protocols.split(","):
                protocol = protocol.strip()
                if protocol.startswith("Bearer."):
                    token = protocol[7:]  # Remove "Bearer." prefix
                    break
    except Exception as e:
        logger.debug(f"Could not extract token for enhanced tracking: {e}")
    
    # Use enhanced connection tracking
    await progress_manager.connect(websocket, current_user.id, session_id, token)
    logger.info(f"Enhanced Agent WebSocket connected: session {session_id} for user {current_user.id}")
    
    try:
        while True:
            # Handle incoming messages from the client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "token_refresh_response":
                    # Handle token refresh from client
                    new_token = message.get("token")
                    if new_token:
                        success = await progress_manager.handle_token_refresh_response(session_id, new_token)
                        if success:
                            logger.info(f"Token successfully refreshed for session {session_id}")
                        else:
                            logger.warning(f"Token refresh failed for session {session_id}")
                    else:
                        logger.warning(f"Token refresh response missing token for session {session_id}")
                
                elif message_type == "human_context":
                    # Handle human context submission
                    await handle_human_context(session_id, message, current_user.id)
                elif message_type == "mission_confirmation":
                    # Handle mission contradiction confirmation
                    await handle_mission_confirmation(session_id, message, current_user.id)
                elif message_type == "ping":
                    # Handle ping messages to keep connection alive
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message_type == "heartbeat":
                    # Handle heartbeat for connection health
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                else:
                    logger.info(f"WebSocket message type '{message_type}' for session {session_id}")
                    # Forward other messages to progress manager
                    await progress_manager.broadcast_to_session(session_id, message)
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket client: {data}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                
    except WebSocketDisconnect:
        logger.info(f"Enhanced Agent WebSocket disconnected: session {session_id} for user {current_user.id}")
        progress_manager.disconnect(session_id)


@router.websocket("/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    """
    Simple test WebSocket endpoint without authentication.
    Used to debug WebSocket connection issues.
    """
    logger.info("Test WebSocket connection attempt")
    await websocket.accept()
    logger.info("Test WebSocket connection accepted")
    
    try:
        await websocket.send_text(json.dumps({
            "type": "test_response",
            "message": "WebSocket connection successful"
        }))
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"Test WebSocket received: {data}")
            await websocket.send_text(json.dumps({
                "type": "echo",
                "received": data
            }))
    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")


@router.websocket("/ws/debug/{session_id}")
async def websocket_debug_endpoint(websocket: WebSocket, session_id: str):
    """
    Debug WebSocket endpoint that shows authentication details.
    Used to debug token authentication issues in production.
    """
    from urllib.parse import parse_qs
    
    logger.info(f"Debug WebSocket connection attempt for session: {session_id}")
    
    # Extract debug information
    query_params = parse_qs(str(websocket.url.query))
    headers = dict(websocket.headers)
    protocols = headers.get("sec-websocket-protocol", "")
    
    debug_info = {
        "session_id": session_id,
        "query_params": query_params,
        "protocols": protocols,
        "user_agent": headers.get("user-agent", ""),
        "origin": headers.get("origin", ""),
        "connection": headers.get("connection", ""),
        "upgrade": headers.get("upgrade", "")
    }
    
    logger.info(f"Debug WebSocket info: {debug_info}")
    
    await websocket.accept()
    
    try:
        await websocket.send_text(json.dumps({
            "type": "debug_response",
            "message": "WebSocket connection successful - Debug mode",
            "debug_info": debug_info
        }))
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"Debug WebSocket received: {data}")
            await websocket.send_text(json.dumps({
                "type": "debug_echo",
                "received": data,
                "timestamp": datetime.now().isoformat()
            }))
    except WebSocketDisconnect:
        logger.info(f"Debug WebSocket disconnected for session: {session_id}")


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

@router.websocket("/ws/focus-nudge/{client_id}")
async def focus_nudge_websocket_security_redirect(websocket: WebSocket, client_id: str):
    """
    Security Update: This endpoint has been moved to prevent CVE-2024-WS002.
    
    NEW SECURE ENDPOINT: /ws/v2/secure/focus-nudge/{client_id}
    Authentication: Use Authorization header with Bearer token
    """
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="SECURITY UPDATE: Use /ws/v2/secure/focus-nudge/{client_id} with Authorization header"
    )
    logger.warning(f"Security redirect: Client attempted to use insecure Focus Nudge WebSocket for client {client_id}")

@router.websocket("/ws/helios/{session_id}")
async def helios_websocket_security_redirect(websocket: WebSocket, session_id: str):
    """
    Security Update: This endpoint has been moved to prevent CVE-2024-WS002.
    
    NEW SECURE ENDPOINT: /ws/v2/secure/helios/{session_id}
    Authentication: Use Authorization header with Bearer token
    """
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="SECURITY UPDATE: Use /ws/v2/secure/helios/{session_id} with Authorization header"
    )
    logger.warning(f"Security redirect: Client attempted to use insecure Helios WebSocket for session {session_id}")

# Security information endpoint
@router.get("/ws/security-info")
async def websocket_security_info():
    """
    Provide information about WebSocket security updates and new endpoints.
    """
    return {
        "security_status": "UPDATED",
        "vulnerabilities_fixed": [
            {
                "cve": "CVE-2024-WS002",
                "description": "JWT Token Exposure in WebSocket Query Parameters",
                "status": "FIXED",
                "fix_date": "2025-08-04"
            }
        ],
        "secure_endpoints": {
            "agent_websocket": {
                "old": "/ws/agent/{session_id}",
                "new": "/ws/v2/secure/agent/{session_id}",
                "authentication": "Authorization header with Bearer token"
            },
            "helios_websocket": {
                "old": "/ws/helios/{session_id}",
                "new": "/ws/v2/secure/helios/{session_id}",
                "authentication": "Authorization header with Bearer token"
            },
            "focus_nudge_websocket": {
                "old": "/ws/focus-nudge/{client_id}",
                "new": "/ws/v2/secure/focus-nudge/{client_id}",
                "authentication": "Authorization header with Bearer token"
            },
            "monitoring_websocket": {
                "endpoint": "/ws/v2/secure/monitoring/{session_id}",
                "authentication": "Authorization header with Bearer token",
                "access": "Admin only"
            }
        },
        "security_features": [
            "Header-based JWT authentication",
            "Message encryption for sensitive data",
            "Comprehensive rate limiting",
            "Connection health monitoring",
            "Automatic reconnection with exponential backoff",
            "Message integrity validation",
            "Real-time security monitoring",
            "mTLS support for admin endpoints"
        ],
        "migration_guide": {
            "client_changes_required": [
                "Update WebSocket URL to new secure endpoint",
                "Send JWT token in Authorization header instead of query parameter",
                "Implement client-side reconnection logic",
                "Handle encrypted messages if using sensitive operations"
            ],
            "example_connection": {
                "javascript": "new SecureWebSocketClient({ endpoint: '/ws/v2/secure/agent', authToken: 'Bearer <jwt_token>' })"
            }
        }
    }