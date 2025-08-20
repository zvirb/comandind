"""
Unified WebSocket Authentication Service
Aligns WebSocket authentication with the unified authentication router.

This service:
- Uses standardized JWT format from unified authentication
- Integrates with Session-JWT bridge for consistent validation
- Provides fallback compatibility with existing WebSocket implementations
- Maintains security hardening from secure_websocket_auth
"""

import asyncio
import hashlib
import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List

from fastapi import WebSocket, WebSocketException, status
import jwt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.models import User, UserStatus
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings
from app.shared.services.websocket_token_bridge import get_websocket_bridge

logger = logging.getLogger(__name__)
settings = get_settings()

class UnifiedWebSocketAuth:
    """
    Unified WebSocket authentication aligned with unified authentication router.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.user_connections: Dict[int, Set[str]] = {}
        self.failed_auth_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}
    
    async def authenticate_websocket(
        self, 
        websocket: WebSocket,
        db_session: AsyncSession,
        allow_query_token: bool = False  # For backward compatibility
    ) -> Dict[str, Any]:
        """
        Authenticate WebSocket connection using unified authentication standards.
        
        Args:
            websocket: WebSocket connection
            db_session: Database session
            allow_query_token: Allow token from query params (legacy support)
            
        Returns:
            Dict with connection info and authenticated user
        """
        try:
            client_ip = self._get_client_ip(websocket)
            
            # Check if IP is blocked
            if self._is_ip_blocked(client_ip):
                logger.warning(f"Blocked IP attempted WebSocket connection: {client_ip}")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="IP address blocked"
                )
            
            # Extract JWT token (header preferred, query param fallback)
            token = self._extract_token(websocket, allow_query_token)
            if not token:
                await self._record_auth_failure(client_ip, "missing_token")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Authorization required: Bearer token in header or query param"
                )
            
            # Validate token using standardized format validation
            validation_result = await self._validate_unified_token(token, client_ip, db_session)
            
            if not validation_result["valid"]:
                await self._record_auth_failure(client_ip, "invalid_token")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=validation_result.get("error", "Invalid token")
                )
            
            user = validation_result["user"]
            payload = validation_result["payload"]
            
            # Generate connection info
            connection_id = secrets.token_urlsafe(16)
            session_id = payload.get("session_id", secrets.token_urlsafe(16))
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Store connection info
            connection_info = {
                "connection_id": connection_id,
                "user_id": user.id,
                "user": user,
                "session_id": session_id,
                "websocket": websocket,
                "connected_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "client_ip": client_ip,
                "user_agent": websocket.headers.get("user-agent", "unknown"),
                "token_payload": payload,
                "is_active": True
            }
            
            self.active_connections[connection_id] = connection_info
            
            # Track user connections
            if user.id not in self.user_connections:
                self.user_connections[user.id] = set()
            self.user_connections[user.id].add(connection_id)
            
            logger.info(f"Unified WebSocket authentication successful: user {user.id}, connection {connection_id}")
            
            return connection_info
            
        except WebSocketException:
            raise
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await self._record_auth_failure(client_ip, "system_error")
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Authentication system error"
            )
    
    def _extract_token(self, websocket: WebSocket, allow_query_token: bool = False) -> Optional[str]:
        """
        Extract authentication token from WebSocket request.
        
        SECURITY ENHANCED: Supports both JWT tokens and bridge tokens.
        Bridge tokens are preferred for new connections.
        """
        # Try Authorization header first (for JWT tokens)
        auth_header = websocket.headers.get("authorization", "")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]
        
        # Try WebSocket bridge token header (SECURE METHOD)
        bridge_token = websocket.headers.get("x-bridge-token", "")
        if bridge_token:
            logger.debug("WebSocket bridge token detected")
            return f"bridge:{bridge_token}"  # Mark as bridge token
        
        # SECURITY FIX: Query parameter support REMOVED to prevent token exposure
        if allow_query_token:
            logger.warning("Query parameter authentication disabled for security - use bridge tokens")
        
        return None
    
    async def _validate_unified_token(
        self, 
        token: str, 
        client_ip: str, 
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Validate authentication token (JWT or bridge token) using unified standards.
        """
        try:
            # Check if this is a bridge token
            if token.startswith("bridge:"):
                return await self._validate_bridge_token(token[7:], client_ip, db_session)
            
            # Standard JWT validation
            # Import the SessionJWTBridge from unified auth router
            from api.routers.unified_auth_router import SessionJWTBridge
            
            # Validate token format and consistency
            validation_result = await SessionJWTBridge.validate_session_jwt_consistency(
                token=token, 
                db_session=db_session
            )
            
            if not validation_result["valid"]:
                return {
                    "valid": False,
                    "error": validation_result.get("error", "Token validation failed"),
                    "format_error": not validation_result.get("format_valid", False)
                }
            
            payload = validation_result["payload"]
            
            # Extract user ID from standardized format
            user_id = None
            if "id" in payload:
                user_id = payload["id"]
            elif "sub" in payload:
                sub_value = payload["sub"]
                if isinstance(sub_value, int):
                    user_id = sub_value
                elif isinstance(sub_value, str) and sub_value.isdigit():
                    user_id = int(sub_value)
                elif isinstance(sub_value, str) and "@" in sub_value:
                    # Legacy format where sub is email, get ID from payload
                    user_id = payload.get("id")
            
            if not user_id:
                return {
                    "valid": False,
                    "error": "Invalid token format: missing user ID"
                }
            
            # Fetch user from database
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {
                    "valid": False,
                    "error": "User not found"
                }
            
            if user.status != UserStatus.ACTIVE or not user.is_active:
                return {
                    "valid": False,
                    "error": "User account not active"
                }
            
            return {
                "valid": True,
                "user": user,
                "payload": payload,
                "user_id": user_id
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token expired"
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "error": f"Invalid token: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {
                "valid": False,
                "error": "Token validation failed"
            }
    
    async def _validate_bridge_token(
        self, 
        bridge_token_id: str, 
        client_ip: str, 
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Validate WebSocket bridge token.
        """
        try:
            bridge = get_websocket_bridge()
            
            # Validate bridge token and get user info
            user_id, original_token_hash = await bridge.validate_bridge_token(
                token_id=bridge_token_id,
                client_ip=client_ip
            )
            
            # Fetch user from database
            result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {user_id} not found for bridge token")
                return {
                    "valid": False,
                    "error": "User not found"
                }
            
            if not user.is_active:
                logger.warning(f"Inactive user {user_id} attempted WebSocket connection")
                return {
                    "valid": False,
                    "error": "Account is disabled"
                }
            
            logger.info(f"Bridge token validated for user {user_id} from IP {client_ip}")
            
            return {
                "valid": True,
                "user_id": user_id,
                "user": user,
                "auth_method": "bridge_token",
                "original_token_hash": original_token_hash
            }
            
        except Exception as e:
            logger.error(f"Bridge token validation error: {e}")
            return {
                "valid": False,
                "error": f"Bridge token validation failed: {str(e)}"
            }
    
    def _get_client_ip(self, websocket: WebSocket) -> str:
        """Extract client IP address from WebSocket."""
        # Try X-Forwarded-For header first (for proxy setups)
        forwarded_for = websocket.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Try X-Real-IP header
        real_ip = websocket.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return getattr(websocket.client, "host", "unknown") if websocket.client else "unknown"
    
    async def _record_auth_failure(self, client_ip: str, failure_type: str) -> None:
        """Record authentication failure for rate limiting."""
        now = datetime.now(timezone.utc)
        
        # Track failed attempts
        if client_ip not in self.failed_auth_attempts:
            self.failed_auth_attempts[client_ip] = []
        
        self.failed_auth_attempts[client_ip].append(now)
        
        # Clean old attempts (older than 1 hour)
        cutoff_time = now - timedelta(hours=1)
        self.failed_auth_attempts[client_ip] = [
            attempt for attempt in self.failed_auth_attempts[client_ip]
            if attempt > cutoff_time
        ]
        
        # Block IP if too many failures
        if len(self.failed_auth_attempts[client_ip]) >= 10:
            self.blocked_ips[client_ip] = now + timedelta(hours=24)
            logger.warning(f"IP blocked due to auth failures: {client_ip}")
    
    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP address is currently blocked."""
        if client_ip not in self.blocked_ips:
            return False
        
        if datetime.now(timezone.utc) > self.blocked_ips[client_ip]:
            del self.blocked_ips[client_ip]
            return False
        
        return True
    
    async def disconnect_connection(self, connection_id: str, reason: str = "normal_closure") -> None:
        """Disconnect and cleanup WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[connection_id]
        user_id = connection_info["user_id"]
        websocket = connection_info["websocket"]
        
        try:
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason=reason)
        except Exception as e:
            logger.error(f"Error closing WebSocket {connection_id}: {e}")
        
        # Remove from tracking
        del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}, reason: {reason}")
    
    async def send_message_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """Send message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return 0
        
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.user_connections[user_id].copy():
            if connection_id not in self.active_connections:
                failed_connections.append(connection_id)
                continue
            
            connection_info = self.active_connections[connection_id]
            websocket = connection_info["websocket"]
            
            try:
                await websocket.send_text(json.dumps(message))
                connection_info["last_activity"] = datetime.now(timezone.utc)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect_connection(connection_id, "send_failure")
        
        return sent_count
    
    async def cleanup_stale_connections(self) -> None:
        """Clean up stale connections."""
        stale_connections = []
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        for connection_id, connection_info in self.active_connections.items():
            if connection_info["last_activity"] < stale_threshold:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.disconnect_connection(connection_id, "stale_connection")
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        total_connections = len(self.active_connections)
        total_users = len(self.user_connections)
        blocked_ips = len(self.blocked_ips)
        
        return {
            "total_connections": total_connections,
            "total_users": total_users,
            "blocked_ips": blocked_ips,
            "auth_method": "unified_authentication",
            "jwt_format": "standardized"
        }

# Global unified WebSocket authenticator instance
unified_websocket_auth = UnifiedWebSocketAuth()

# Compatibility functions for existing WebSocket implementations
async def authenticate_websocket_unified(
    websocket: WebSocket, 
    session_id: str = None,
    allow_legacy: bool = True
) -> Dict[str, Any]:
    """
    Compatibility wrapper for existing WebSocket authentication.
    """
    async with get_async_session() as db_session:
        return await unified_websocket_auth.authenticate_websocket(
            websocket=websocket,
            db_session=db_session,
            allow_query_token=allow_legacy
        )

def get_websocket_auth_stats() -> Dict[str, Any]:
    """Get WebSocket authentication statistics."""
    return unified_websocket_auth.get_connection_stats()