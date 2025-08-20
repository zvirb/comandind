"""Secure WebSocket Authentication Service - Fixes CVE-2024-WS002"""

import asyncio
import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Set, List
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketException, status
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.models import User, UserStatus
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_async_session
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecureWebSocketMessage:
    """Secure WebSocket message with encryption and integrity validation."""
    
    def __init__(self, message_type: str, data: Dict[str, Any], encrypted: bool = False):
        self.message_type = message_type
        self.data = data
        self.encrypted = encrypted
        self.message_id = secrets.token_urlsafe(16)
        self.timestamp = datetime.now(timezone.utc)
        self.signature = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "type": self.message_type,
            "data": self.data,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "encrypted": self.encrypted,
            "signature": self.signature
        }
    
    def encrypt(self, encryption_key: bytes) -> None:
        """Encrypt sensitive message data."""
        if self.encrypted:
            return
        
        try:
            fernet = Fernet(encryption_key)
            data_bytes = json.dumps(self.data).encode()
            encrypted_data = fernet.encrypt(data_bytes)
            
            self.data = {"encrypted_payload": base64.b64encode(encrypted_data).decode()}
            self.encrypted = True
            self.signature = self._generate_signature(encryption_key)
            
        except Exception as e:
            logger.error(f"Failed to encrypt WebSocket message: {e}")
            raise
    
    def decrypt(self, encryption_key: bytes) -> None:
        """Decrypt encrypted message data."""
        if not self.encrypted:
            return
        
        try:
            # Verify signature first
            if not self._verify_signature(encryption_key):
                raise ValueError("Message signature verification failed")
            
            fernet = Fernet(encryption_key)
            encrypted_payload = base64.b64decode(self.data["encrypted_payload"])
            decrypted_data = fernet.decrypt(encrypted_payload)
            
            self.data = json.loads(decrypted_data.decode())
            self.encrypted = False
            self.signature = None
            
        except Exception as e:
            logger.error(f"Failed to decrypt WebSocket message: {e}")
            raise
    
    def _generate_signature(self, key: bytes) -> str:
        """Generate message signature for integrity validation."""
        message_content = f"{self.message_type}:{self.message_id}:{self.timestamp.isoformat()}"
        signature = hashlib.hmac.new(key, message_content.encode(), hashlib.sha256).hexdigest()
        return signature
    
    def _verify_signature(self, key: bytes) -> bool:
        """Verify message signature."""
        if not self.signature:
            return False
        
        expected_signature = self._generate_signature(key)
        return secrets.compare_digest(self.signature, expected_signature)


class SecureWebSocketConnection:
    """Secure WebSocket connection with enhanced security features."""
    
    def __init__(self, websocket: WebSocket, user: User, session_id: str):
        self.websocket = websocket
        self.user = user
        self.session_id = session_id
        self.connection_id = secrets.token_urlsafe(16)
        self.connected_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.message_count = 0
        self.rate_limit_count = 0
        self.rate_limit_reset = datetime.now(timezone.utc) + timedelta(hours=1)
        self.encryption_key = self._generate_encryption_key()
        self.authenticated = True
        self.is_healthy = True
        self.connection_metadata = {
            "user_agent": "",
            "ip_address": "",
            "cert_verified": False
        }
    
    def _generate_encryption_key(self) -> bytes:
        """Generate connection-specific encryption key."""
        password = f"{self.user.id}:{self.session_id}:{self.connected_at.isoformat()}"
        salt = hashlib.sha256(f"{settings.JWT_SECRET_KEY.get_secret_value()}:{self.connection_id}".encode()).digest()[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
        self.message_count += 1
    
    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now(timezone.utc)
        self.is_healthy = True
    
    def check_rate_limit(self, max_messages: int = 100, window_hours: int = 1) -> bool:
        """Check if connection is within rate limits."""
        now = datetime.now(timezone.utc)
        
        # Reset rate limit window if expired
        if now > self.rate_limit_reset:
            self.rate_limit_count = 0
            self.rate_limit_reset = now + timedelta(hours=window_hours)
        
        # Check limit
        if self.rate_limit_count >= max_messages:
            return False
        
        self.rate_limit_count += 1
        return True
    
    def is_connection_stale(self, timeout_minutes: int = 30) -> bool:
        """Check if connection is stale due to inactivity."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        return self.last_activity < timeout_threshold
    
    def is_heartbeat_expired(self, timeout_seconds: int = 300) -> bool:
        """Check if heartbeat has expired."""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        return self.last_heartbeat < timeout_threshold
    
    async def send_secure_message(self, message: SecureWebSocketMessage, encrypt_sensitive: bool = False) -> bool:
        """Send secure message through WebSocket connection."""
        try:
            # Encrypt sensitive messages
            if encrypt_sensitive and message.message_type in ["user_data", "token_refresh", "sensitive_update"]:
                message.encrypt(self.encryption_key)
            
            # Send message
            message_dict = message.to_dict()
            await self.websocket.send_text(json.dumps(message_dict))
            
            self.update_activity()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send secure WebSocket message: {e}")
            self.is_healthy = False
            return False
    
    async def close_with_reason(self, code: int, reason: str) -> None:
        """Close connection with specific code and reason."""
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.error(f"Error closing WebSocket connection: {e}")


class SecureWebSocketAuthenticator:
    """Secure WebSocket authentication service using header-based tokens."""
    
    def __init__(self):
        self.active_connections: Dict[str, SecureWebSocketConnection] = {}
        self.user_connections: Dict[int, Set[str]] = {}
        self.failed_auth_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}
    
    async def authenticate_websocket_header(
        self, 
        websocket: WebSocket, 
        session_id: str,
        db_session: AsyncSession,
        require_mtls: bool = False
    ) -> SecureWebSocketConnection:
        """
        Authenticate WebSocket connection using Authorization header.
        FIXES CVE-2024-WS002 by eliminating query parameter token exposure.
        """
        try:
            # Extract IP address for rate limiting and audit
            client_ip = self._get_client_ip(websocket)
            
            # Check if IP is blocked
            if self._is_ip_blocked(client_ip):
                logger.warning(f"Blocked IP attempted WebSocket connection: {client_ip}")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="IP address blocked due to security violations"
                )
            
            # Extract JWT token from Authorization header
            token = self._extract_token_from_headers(websocket)
            if not token:
                await self._record_auth_failure(client_ip, "missing_token")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Authorization header with Bearer token required"
                )
            
            # Validate JWT token using enhanced JWT service
            token_validation = await enhanced_jwt_service.verify_token(
                session=db_session,
                token=token,
                required_scopes=["api_stream", "websocket_access"],
                ip_address=client_ip,
                user_agent=websocket.headers.get("user-agent", "unknown")
            )
            
            if not token_validation["valid"]:
                await self._record_auth_failure(client_ip, "invalid_token")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid or expired token"
                )
            
            user_id = token_validation["user_id"]
            
            # Fetch user from database
            from sqlalchemy import select
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user or user.status != UserStatus.ACTIVE:
                await self._record_auth_failure(client_ip, "invalid_user")
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User account not found or inactive"
                )
            
            # Validate mTLS certificate if required
            cert_info = None
            if require_mtls:
                cert_info = self._validate_mtls_certificate(websocket)
                if not cert_info:
                    await self._record_auth_failure(client_ip, "mtls_required")
                    raise WebSocketException(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Valid mTLS client certificate required"
                    )
            
            # Create secure connection
            connection = SecureWebSocketConnection(websocket, user, session_id)
            connection.connection_metadata.update({
                "user_agent": websocket.headers.get("user-agent", "unknown"),
                "ip_address": client_ip,
                "cert_verified": bool(cert_info)
            })
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Register connection
            self.active_connections[connection.connection_id] = connection
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection.connection_id)
            
            # Log successful authentication
            await security_audit_service.log_data_access(
                session=db_session,
                user_id=user_id,
                service_name="secure_websocket_auth",
                access_type="WEBSOCKET_AUTH_SUCCESS",
                table_name="websocket_connections",
                row_count=1,
                sensitive_data_accessed=False,
                access_pattern={
                    "session_id": session_id,
                    "connection_id": connection.connection_id,
                    "ip_address": client_ip,
                    "mtls_verified": bool(cert_info)
                },
                session_id=session_id,
                ip_address=client_ip
            )
            
            logger.info(f"Secure WebSocket authentication successful: user {user_id}, session {session_id}")
            return connection
            
        except WebSocketException:
            raise
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await self._record_auth_failure(client_ip, "system_error")
            raise WebSocketException(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Authentication system error"
            )
    
    def _extract_token_from_headers(self, websocket: WebSocket) -> Optional[str]:
        """Extract JWT token from WebSocket Authorization header."""
        auth_header = websocket.headers.get("authorization")
        if not auth_header:
            return None
        
        # Parse "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
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
    
    def _validate_mtls_certificate(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Validate mTLS client certificate from headers."""
        cert_subject = websocket.headers.get("x-client-certificate-subject")
        cert_verified = websocket.headers.get("x-client-certificate-verified")
        cert_fingerprint = websocket.headers.get("x-client-certificate-fingerprint")
        
        if cert_subject and cert_verified == "success":
            return {
                "subject": cert_subject,
                "verified": True,
                "fingerprint": cert_fingerprint
            }
        
        return None
    
    async def _record_auth_failure(self, client_ip: str, failure_type: str) -> None:
        """Record authentication failure for rate limiting and security monitoring."""
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
            self.blocked_ips[client_ip] = now + timedelta(hours=24)  # Block for 24 hours
            logger.warning(f"IP address blocked due to repeated auth failures: {client_ip}")
    
    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP address is currently blocked."""
        if client_ip not in self.blocked_ips:
            return False
        
        # Check if block has expired
        if datetime.now(timezone.utc) > self.blocked_ips[client_ip]:
            del self.blocked_ips[client_ip]
            return False
        
        return True
    
    async def disconnect_connection(self, connection_id: str, reason: str = "normal_closure") -> None:
        """Disconnect and cleanup WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        user_id = connection.user.id
        
        try:
            # Close WebSocket connection
            await connection.close_with_reason(
                code=status.WS_1000_NORMAL_CLOSURE,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Error closing WebSocket connection {connection_id}: {e}")
        
        # Remove from tracking
        del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket connection disconnected: {connection_id}, reason: {reason}")
    
    async def cleanup_stale_connections(self) -> None:
        """Clean up stale and unhealthy connections."""
        stale_connections = []
        
        for connection_id, connection in self.active_connections.items():
            if connection.is_connection_stale() or connection.is_heartbeat_expired():
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.disconnect_connection(connection_id, "stale_connection")
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        total_connections = len(self.active_connections)
        total_users = len(self.user_connections)
        healthy_connections = sum(1 for conn in self.active_connections.values() if conn.is_healthy)
        mtls_connections = sum(1 for conn in self.active_connections.values() 
                              if conn.connection_metadata.get("cert_verified", False))
        
        return {
            "total_connections": total_connections,
            "healthy_connections": healthy_connections,
            "total_users": total_users,
            "mtls_connections": mtls_connections,
            "blocked_ips": len(self.blocked_ips),
            "health_rate": healthy_connections / total_connections if total_connections > 0 else 0,
            "mtls_rate": mtls_connections / total_connections if total_connections > 0 else 0
        }
    
    async def broadcast_to_user(self, user_id: int, message: SecureWebSocketMessage, encrypt_sensitive: bool = False) -> int:
        """Broadcast message to all connections for a specific user."""
        if user_id not in self.user_connections:
            return 0
        
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.user_connections[user_id].copy():
            if connection_id not in self.active_connections:
                failed_connections.append(connection_id)
                continue
            
            connection = self.active_connections[connection_id]
            success = await connection.send_secure_message(message, encrypt_sensitive)
            
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect_connection(connection_id, "send_failure")
        
        return sent_count


# Global secure WebSocket authenticator instance
secure_websocket_auth = SecureWebSocketAuthenticator()