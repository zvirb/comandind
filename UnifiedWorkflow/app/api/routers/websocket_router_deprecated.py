# DEPRECATED WebSocket Router - Contains Critical Security Vulnerabilities
# CVE-2024-WS002: JWT Token Exposure in Query Parameters
# 
# This file is deprecated and should not be used in production.
# Use enhanced_secure_websocket_router.py for new implementations.
# This file is kept for reference and migration purposes only.

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
import jwt

# Import the singleton progress_manager instance
from ..progress_manager import progress_manager
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# SECURITY WARNING: This function contains critical vulnerabilities
async def authenticate_websocket_deprecated(token: str) -> int:
    """
    DEPRECATED: Authenticate WebSocket connection using JWT token from query parameters.
    
    CRITICAL SECURITY VULNERABILITY (CVE-2024-WS002):
    This function accepts tokens from query parameters which exposes them in:
    - Browser history and cache
    - Server access logs
    - Referrer headers
    - Proxy and CDN logs
    - Network monitoring tools
    
    REMEDIATION: Use header-based authentication from enhanced_secure_websocket_router.py
    """
    logger.error("SECURITY VIOLATION: Using deprecated WebSocket authentication with query parameters")
    logger.error("CVE-2024-WS002: JWT token exposed in query parameters - IMMEDIATE SECURITY RISK")
    logger.error("RECOMMENDED ACTION: Migrate to enhanced_secure_websocket_router.py immediately")
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY.get_secret_value(), algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        # Log the security violation
        logger.warning(f"SECURITY AUDIT: JWT token {token[:20]}... exposed in query parameters for user {user_id}")
        
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# DEPRECATED ENDPOINTS - CONTAIN SECURITY VULNERABILITIES
@router.websocket("/ws/deprecated/agent/{session_id}")
async def deprecated_websocket_endpoint(websocket: WebSocket, session_id: str, token: str = Query(...)):
    """
    DEPRECATED: WebSocket endpoint with security vulnerabilities.
    
    SECURITY ISSUES:
    - CVE-2024-WS002: Token in query parameters
    - Missing rate limiting
    - No message encryption
    - Insufficient logging controls
    - No connection health monitoring
    
    USE: /ws/v2/secure/agent/{session_id} from enhanced_secure_websocket_router.py
    """
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="DEPRECATED: Use secure WebSocket endpoints - CVE-2024-WS002"
    )
    logger.error(f"SECURITY VIOLATION: Attempt to use deprecated WebSocket endpoint /ws/deprecated/agent/{session_id}")

@router.websocket("/ws/deprecated/focus-nudge/{client_id}")
async def deprecated_focus_nudge_websocket(websocket: WebSocket, client_id: str, token: str = Query(...)):
    """
    DEPRECATED: Focus Nudge WebSocket endpoint with security vulnerabilities.
    """
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="DEPRECATED: Use secure WebSocket endpoints - CVE-2024-WS002"
    )
    logger.error(f"SECURITY VIOLATION: Attempt to use deprecated Focus Nudge WebSocket endpoint for client {client_id}")

@router.websocket("/ws/deprecated/helios/{session_id}")
async def deprecated_helios_websocket_endpoint(websocket: WebSocket, session_id: str, token: str = Query(...)):
    """
    DEPRECATED: Helios WebSocket endpoint with security vulnerabilities.
    """
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="DEPRECATED: Use secure WebSocket endpoints - CVE-2024-WS002"
    )
    logger.error(f"SECURITY VIOLATION: Attempt to use deprecated Helios WebSocket endpoint for session {session_id}")

# The original vulnerable functions are preserved for reference only
# DO NOT USE THESE IN PRODUCTION

async def handle_helios_client_message_deprecated(user_id: int, session_id: str, message: dict, websocket: WebSocket):
    """DEPRECATED: Contains security vulnerabilities - no input validation, logging sensitive data"""
    pass

async def handle_focus_nudge_client_message_deprecated(user_id: int, client_id: str, message: dict):
    """DEPRECATED: Contains security vulnerabilities - no input validation"""
    pass