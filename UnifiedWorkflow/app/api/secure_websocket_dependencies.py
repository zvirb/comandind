"""Secure WebSocket Dependencies with Enhanced Authentication and Security."""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User, UserRole
from shared.services.secure_websocket_auth import (
    secure_websocket_auth, 
    SecureWebSocketConnection, 
    SecureWebSocketMessage
)
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def get_secure_websocket_connection(
    websocket: WebSocket,
    session_id: str,
    require_mtls: bool = False,
    required_role: Optional[UserRole] = None,
    rate_limit_messages: int = 100,
    rate_limit_window_hours: int = 1
):
    """
    Context manager for secure WebSocket connections with comprehensive security.
    
    Features:
    - Header-based JWT authentication (fixes CVE-2024-WS002)
    - Enhanced JWT service integration
    - Optional mTLS certificate validation
    - Role-based access control
    - Rate limiting and abuse prevention
    - Automatic connection cleanup
    - Security audit logging
    """
    connection = None
    db_session = None
    
    try:
        # Get database session
        async for db in get_async_session():
            db_session = db
            break
        
        if not db_session:
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Database connection failed"
            )
        
        # Authenticate WebSocket connection using headers
        connection = await secure_websocket_auth.authenticate_websocket_header(
            websocket=websocket,
            session_id=session_id,
            db_session=db_session,
            require_mtls=require_mtls
        )
        
        # Validate user role if required
        if required_role and connection.user.role != required_role:
            await security_audit_service.log_security_violation(
                session=db_session,
                violation_type="INSUFFICIENT_WEBSOCKET_PERMISSIONS",
                severity="MEDIUM",
                violation_details={
                    "required_role": required_role.value,
                    "user_role": connection.user.role.value,
                    "session_id": session_id
                },
                user_id=connection.user.id,
                ip_address=connection.connection_metadata.get("ip_address"),
                blocked=True
            )
            
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Role {required_role.value} required"
            )
        
        # Set up rate limiting parameters
        connection.rate_limit_messages = rate_limit_messages
        connection.rate_limit_window_hours = rate_limit_window_hours
        
        # Send connection established message
        welcome_message = SecureWebSocketMessage(
            message_type="connection_established",
            data={
                "connection_id": connection.connection_id,
                "session_id": session_id,
                "user_id": connection.user.id,
                "user_email": connection.user.email,
                "connected_at": connection.connected_at.isoformat(),
                "security_features": {
                    "header_auth": True,
                    "rate_limiting": True,
                    "message_encryption": True,
                    "mtls_enabled": require_mtls,
                    "mtls_verified": connection.connection_metadata.get("cert_verified", False)
                }
            }
        )
        
        await connection.send_secure_message(welcome_message, encrypt_sensitive=False)
        
        logger.info(f"Secure WebSocket connection established: {connection.connection_id}")
        
        yield connection
        
    except WebSocketException:
        raise
    except Exception as e:
        logger.error(f"Secure WebSocket connection error: {e}")
        if connection:
            await connection.close_with_reason(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Connection setup failed"
            )
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Connection setup failed"
        )
    
    finally:
        # Cleanup connection
        if connection:
            await secure_websocket_auth.disconnect_connection(
                connection.connection_id,
                reason="context_cleanup"
            )
        
        # Close database session
        if db_session:
            await db_session.close()


class SecureWebSocketMessageHandler:
    """Secure WebSocket message handler with encryption and validation."""
    
    def __init__(self, connection: SecureWebSocketConnection):
        self.connection = connection
        self.message_handlers: Dict[str, Callable] = {}
        self.middleware_stack: List[Callable] = []
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler for specific message type."""
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the processing stack."""
        self.middleware_stack.append(middleware)
        logger.debug(f"Added middleware: {middleware.__name__}")
    
    async def process_message(self, raw_message: str) -> None:
        """Process incoming WebSocket message with security validation."""
        try:
            # Check rate limiting
            if not self.connection.check_rate_limit():
                error_message = SecureWebSocketMessage(
                    message_type="error",
                    data={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "error_message": "Message rate limit exceeded",
                        "retry_after_seconds": 3600
                    }
                )
                await self.connection.send_secure_message(error_message)
                
                # Close connection for severe rate limit violations
                await self.connection.close_with_reason(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Rate limit exceeded"
                )
                return
            
            # Parse message
            import json
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError:
                await self._send_error("INVALID_JSON", "Message must be valid JSON")
                return
            
            # Validate message structure
            if not isinstance(message_data, dict) or "type" not in message_data:
                await self._send_error("INVALID_MESSAGE_FORMAT", "Message must have 'type' field")
                return
            
            message_type = message_data["type"]
            message_payload = message_data.get("data", {})
            
            # Create secure message object
            secure_message = SecureWebSocketMessage(
                message_type=message_type,
                data=message_payload,
                encrypted=message_data.get("encrypted", False)
            )
            
            # Decrypt if necessary
            if secure_message.encrypted:
                try:
                    secure_message.decrypt(self.connection.encryption_key)
                except Exception as e:
                    logger.error(f"Message decryption failed: {e}")
                    await self._send_error("DECRYPTION_FAILED", "Failed to decrypt message")
                    return
            
            # Apply middleware stack
            for middleware in self.middleware_stack:
                try:
                    await middleware(self.connection, secure_message)
                except Exception as e:
                    logger.error(f"Middleware error: {e}")
                    await self._send_error("MIDDLEWARE_ERROR", "Message processing failed")
                    return
            
            # Handle specific message types
            await self._route_message(secure_message)
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            await self._send_error("PROCESSING_ERROR", "Internal message processing error")
    
    async def _route_message(self, message: SecureWebSocketMessage) -> None:
        """Route message to appropriate handler."""
        message_type = message.message_type
        
        # Handle built-in message types
        if message_type == "heartbeat":
            await self._handle_heartbeat(message)
        elif message_type == "ping":
            await self._handle_ping(message)
        elif message_type in self.message_handlers:
            try:
                await self.message_handlers[message_type](self.connection, message)
            except Exception as e:
                logger.error(f"Handler error for {message_type}: {e}")
                await self._send_error("HANDLER_ERROR", f"Failed to process {message_type}")
        else:
            await self._send_error("UNKNOWN_MESSAGE_TYPE", f"Unknown message type: {message_type}")
    
    async def _handle_heartbeat(self, message: SecureWebSocketMessage) -> None:
        """Handle heartbeat message."""
        self.connection.update_heartbeat()
        
        response = SecureWebSocketMessage(
            message_type="heartbeat_ack",
            data={
                "server_timestamp": self.connection.last_heartbeat.isoformat(),
                "connection_health": "healthy" if self.connection.is_healthy else "degraded"
            }
        )
        
        await self.connection.send_secure_message(response)
    
    async def _handle_ping(self, message: SecureWebSocketMessage) -> None:
        """Handle ping message."""
        response = SecureWebSocketMessage(
            message_type="pong",
            data={
                "timestamp": self.connection.last_activity.isoformat()
            }
        )
        
        await self.connection.send_secure_message(response)
    
    async def _send_error(self, error_code: str, error_message: str) -> None:
        """Send error message to client."""
        error_msg = SecureWebSocketMessage(
            message_type="error",
            data={
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": self.connection.last_activity.isoformat()
            }
        )
        
        await self.connection.send_secure_message(error_msg)


# Security Middleware Functions
async def authentication_middleware(connection: SecureWebSocketConnection, message: SecureWebSocketMessage) -> None:
    """Validate that connection is still authenticated."""
    if not connection.authenticated:
        raise Exception("Connection not authenticated")


async def audit_middleware(connection: SecureWebSocketConnection, message: SecureWebSocketMessage) -> None:
    """Log message for security auditing."""
    # Only log non-sensitive message types
    if message.message_type not in ["heartbeat", "ping", "pong"]:
        logger.info(f"WebSocket message: user={connection.user.id}, type={message.message_type}, "
                   f"session={connection.session_id}")


async def rate_limit_middleware(connection: SecureWebSocketConnection, message: SecureWebSocketMessage) -> None:
    """Additional rate limiting for specific message types."""
    high_cost_messages = ["file_upload", "bulk_operation", "system_command"]
    
    if message.message_type in high_cost_messages:
        # Stricter rate limiting for expensive operations
        if not connection.check_rate_limit(max_messages=10, window_hours=1):
            raise Exception("Rate limit exceeded for high-cost operation")


async def content_validation_middleware(connection: SecureWebSocketConnection, message: SecureWebSocketMessage) -> None:
    """Validate message content for security threats."""
    # Check for suspicious patterns
    message_str = str(message.data)
    
    suspicious_patterns = [
        "<script", "javascript:", "eval(", "document.cookie",
        "localStorage", "sessionStorage", "XMLHttpRequest"
    ]
    
    for pattern in suspicious_patterns:
        if pattern.lower() in message_str.lower():
            logger.warning(f"Suspicious content detected in WebSocket message: {pattern}")
            raise Exception("Suspicious content detected")


# Dependency Functions
async def require_secure_websocket_agent(
    websocket: WebSocket,
    session_id: str
) -> SecureWebSocketConnection:
    """Dependency for secure agent WebSocket connections."""
    async with get_secure_websocket_connection(
        websocket=websocket,
        session_id=session_id,
        require_mtls=False,
        required_role=None,
        rate_limit_messages=100,
        rate_limit_window_hours=1
    ) as connection:
        yield connection


async def require_secure_websocket_admin(
    websocket: WebSocket,
    session_id: str
) -> SecureWebSocketConnection:
    """Dependency for secure admin WebSocket connections."""
    async with get_secure_websocket_connection(
        websocket=websocket,
        session_id=session_id,
        require_mtls=True,
        required_role=UserRole.ADMIN,
        rate_limit_messages=200,
        rate_limit_window_hours=1
    ) as connection:
        yield connection


async def require_secure_websocket_user(
    websocket: WebSocket,
    session_id: str
) -> SecureWebSocketConnection:
    """Dependency for secure user WebSocket connections."""
    async with get_secure_websocket_connection(
        websocket=websocket,
        session_id=session_id,
        require_mtls=False,
        required_role=None,
        rate_limit_messages=50,
        rate_limit_window_hours=1
    ) as connection:
        yield connection


# Connection Health Monitor
class WebSocketHealthMonitor:
    """Monitor WebSocket connection health and perform cleanup."""
    
    def __init__(self):
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 300  # 5 minutes
    
    async def start_monitoring(self) -> None:
        """Start health monitoring background task."""
        if self.monitoring_task and not self.monitoring_task.done():
            return
        
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("WebSocket health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("WebSocket health monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Clean up stale connections
                await secure_websocket_auth.cleanup_stale_connections()
                
                # Log connection statistics
                stats = secure_websocket_auth.get_connection_stats()
                logger.info(f"WebSocket stats: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")


# Global health monitor instance
websocket_health_monitor = WebSocketHealthMonitor()