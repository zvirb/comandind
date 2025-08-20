"""
Protocol Security Service

Implements comprehensive security and authentication across all protocol layers,
including JWT validation, role-based access control, message encryption,
audit logging, and threat detection.
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum
from dataclasses import dataclass

import jwt
import redis.asyncio as redis
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from shared.schemas.protocol_schemas import BaseProtocolMessage, ProtocolMetadata, MessageIntent
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# Security Models
# ================================

class SecurityLevel(str, Enum):
    """Security classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AuthenticationMethod(str, Enum):
    """Supported authentication methods."""
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    MUTUAL_TLS = "mutual_tls"
    AGENT_CERTIFICATE = "agent_certificate"


class PermissionScope(str, Enum):
    """Permission scopes for protocol operations."""
    # MCP permissions
    TOOL_EXECUTE = "tool.execute"
    TOOL_REGISTER = "tool.register"
    TOOL_ADMIN = "tool.admin"
    
    # A2A permissions
    AGENT_REGISTER = "agent.register"
    AGENT_DISCOVER = "agent.discover"
    AGENT_MESSAGE = "agent.message"
    AGENT_NEGOTIATE = "agent.negotiate"
    
    # ACP permissions
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_EXECUTE = "workflow.execute"
    WORKFLOW_ADMIN = "workflow.admin"
    TASK_DELEGATE = "task.delegate"
    SESSION_MANAGE = "session.manage"
    
    # Administrative permissions
    PROTOCOL_ADMIN = "protocol.admin"
    SECURITY_AUDIT = "security.audit"
    METRICS_READ = "metrics.read"


class SecurityContext(BaseModel):
    """Security context for protocol operations."""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    authentication_method: AuthenticationMethod
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Permissions and roles
    roles: List[str] = Field(default_factory=list)
    permissions: List[PermissionScope] = Field(default_factory=list)
    scope_restrictions: Dict[str, Any] = Field(default_factory=dict)
    
    # Security attributes
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    allowed_protocols: List[str] = Field(default_factory=lambda: ["mcp", "a2a", "acp"])
    rate_limit_tier: str = "standard"
    
    # Session information
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Trust and risk
    trust_score: float = Field(ge=0.0, le=1.0, default=0.8)
    risk_indicators: List[str] = Field(default_factory=list)


class AuditEvent(BaseModel):
    """Security audit event."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Event classification
    event_type: str  # "authentication", "authorization", "protocol_violation", etc.
    severity: str = "info"  # "debug", "info", "warning", "error", "critical"
    
    # Context
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    protocol_layer: Optional[str] = None
    
    # Event details
    action: str
    resource: Optional[str] = None
    outcome: str  # "success", "failure", "blocked"
    
    # Security information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


# ================================
# Authentication Service
# ================================

class ProtocolAuthenticator:
    """Handles authentication for protocol messages and operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.jwt_secret = settings.JWT_SECRET_KEY.get_secret_value()
        self.jwt_algorithm = "HS256"
        self.token_cache: Dict[str, SecurityContext] = {}
        
    async def authenticate_message(self, message: BaseProtocolMessage) -> Optional[SecurityContext]:
        """Authenticate a protocol message."""
        try:
            auth_token = message.metadata.authentication_token
            if not auth_token:
                logger.warning("No authentication token provided in message")
                return None
                
            # Check cache first
            cache_key = self._generate_cache_key(auth_token)
            if cache_key in self.token_cache:
                context = self.token_cache[cache_key]
                if not self._is_context_expired(context):
                    return context
                else:
                    del self.token_cache[cache_key]
                    
            # Validate token
            context = await self._validate_authentication_token(auth_token, message.metadata)
            
            if context:
                # Cache valid context
                self.token_cache[cache_key] = context
                await self._record_authentication_event(context, "success", message.metadata)
                return context
            else:
                await self._record_authentication_event(None, "failure", message.metadata)
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            await self._record_authentication_event(None, "error", message.metadata, str(e))
            return None
            
    async def _validate_authentication_token(
        self,
        token: str,
        metadata: ProtocolMetadata
    ) -> Optional[SecurityContext]:
        """Validate authentication token and create security context."""
        try:
            # Determine authentication method
            if token.startswith("Bearer "):
                return await self._validate_jwt_token(token[7:], metadata)
            elif token.startswith("ApiKey "):
                return await self._validate_api_key(token[7:], metadata)
            elif token.startswith("Agent "):
                return await self._validate_agent_certificate(token[6:], metadata)
            else:
                # Assume JWT if no prefix
                return await self._validate_jwt_token(token, metadata)
                
        except Exception as e:
            logger.error(f"Token validation error: {e}", exc_info=True)
            return None
            
    async def _validate_jwt_token(self, token: str, metadata: ProtocolMetadata) -> Optional[SecurityContext]:
        """Validate JWT token."""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Extract user information
            user_id = payload.get("sub")
            if not user_id:
                return None
                
            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                return None
                
            # Get user roles and permissions from database/cache
            roles, permissions = await self._get_user_roles_and_permissions(user_id)
            
            # Create security context
            context = SecurityContext(
                user_id=user_id,
                authentication_method=AuthenticationMethod.JWT,
                roles=roles,
                permissions=permissions,
                session_id=metadata.conversation_id,
                security_level=self._determine_security_level(roles),
                trust_score=self._calculate_trust_score(user_id, payload)
            )
            
            return context
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT validation error: {e}", exc_info=True)
            return None
            
    async def _validate_api_key(self, api_key: str, metadata: ProtocolMetadata) -> Optional[SecurityContext]:
        """Validate API key."""
        try:
            # Look up API key in Redis/database
            key_data = await self.redis.get(f"api_key:{api_key}")
            if not key_data:
                return None
                
            key_info = json.loads(key_data)
            
            # Check expiration
            if key_info.get("expires_at"):
                expires_at = datetime.fromisoformat(key_info["expires_at"])
                if expires_at < datetime.now(timezone.utc):
                    return None
                    
            # Create security context
            context = SecurityContext(
                user_id=key_info.get("user_id"),
                agent_id=key_info.get("agent_id"),
                authentication_method=AuthenticationMethod.API_KEY,
                roles=key_info.get("roles", []),
                permissions=[PermissionScope(p) for p in key_info.get("permissions", [])],
                security_level=SecurityLevel(key_info.get("security_level", "internal")),
                rate_limit_tier=key_info.get("rate_limit_tier", "standard")
            )
            
            return context
            
        except Exception as e:
            logger.error(f"API key validation error: {e}", exc_info=True)
            return None
            
    async def _validate_agent_certificate(self, cert_token: str, metadata: ProtocolMetadata) -> Optional[SecurityContext]:
        """Validate agent certificate."""
        try:
            # This would validate a certificate-based agent authentication
            # For now, implement a simple agent token validation
            
            agent_data = await self.redis.get(f"agent_cert:{cert_token}")
            if not agent_data:
                return None
                
            agent_info = json.loads(agent_data)
            
            context = SecurityContext(
                agent_id=agent_info.get("agent_id"),
                authentication_method=AuthenticationMethod.AGENT_CERTIFICATE,
                roles=["agent"],
                permissions=[
                    PermissionScope.AGENT_MESSAGE,
                    PermissionScope.AGENT_DISCOVER,
                    PermissionScope.TOOL_EXECUTE
                ],
                security_level=SecurityLevel.INTERNAL,
                trust_score=agent_info.get("trust_score", 0.8)
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Agent certificate validation error: {e}", exc_info=True)
            return None
            
    async def _get_user_roles_and_permissions(self, user_id: str) -> Tuple[List[str], List[PermissionScope]]:
        """Get user roles and permissions from database."""
        try:
            # In a real implementation, this would query the user database
            # For now, provide default permissions based on user type
            
            # Check if it's an admin user
            admin_users = ["admin", "system", "1"]  # User ID 1 is typically admin
            
            if user_id in admin_users:
                roles = ["admin", "user"]
                permissions = [scope for scope in PermissionScope]
            else:
                roles = ["user"]
                permissions = [
                    PermissionScope.TOOL_EXECUTE,
                    PermissionScope.AGENT_DISCOVER,
                    PermissionScope.AGENT_MESSAGE,
                    PermissionScope.WORKFLOW_EXECUTE,
                    PermissionScope.TASK_DELEGATE,
                    PermissionScope.METRICS_READ
                ]
                
            return roles, permissions
            
        except Exception as e:
            logger.error(f"Error getting user roles/permissions: {e}", exc_info=True)
            return [], []
            
    def _determine_security_level(self, roles: List[str]) -> SecurityLevel:
        """Determine security level based on roles."""
        if "admin" in roles:
            return SecurityLevel.RESTRICTED
        elif "privileged" in roles:
            return SecurityLevel.CONFIDENTIAL
        else:
            return SecurityLevel.INTERNAL
            
    def _calculate_trust_score(self, user_id: str, token_payload: Dict[str, Any]) -> float:
        """Calculate trust score for user."""
        # Basic trust scoring - can be enhanced with ML models
        base_score = 0.8
        
        # Bonus for recent token
        iat = token_payload.get("iat")
        if iat:
            token_age = time.time() - iat
            if token_age < 300:  # Recent token (5 minutes)
                base_score += 0.1
                
        # Apply risk factors
        # (In production, check user behavior, location, etc.)
        
        return min(1.0, base_score)
        
    def _generate_cache_key(self, token: str) -> str:
        """Generate cache key for token."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]
        
    def _is_context_expired(self, context: SecurityContext) -> bool:
        """Check if security context is expired."""
        # Context expires after 1 hour
        return (datetime.now(timezone.utc) - context.authenticated_at).total_seconds() > 3600
        
    async def _record_authentication_event(
        self,
        context: Optional[SecurityContext],
        outcome: str,
        metadata: ProtocolMetadata,
        error_message: Optional[str] = None
    ) -> None:
        """Record authentication event for audit."""
        event = AuditEvent(
            event_type="authentication",
            severity="info" if outcome == "success" else "warning",
            user_id=context.user_id if context else None,
            agent_id=context.agent_id if context else None,
            session_id=metadata.conversation_id,
            protocol_layer=metadata.protocol_layer,
            action="authenticate",
            outcome=outcome,
            message=error_message,
            metadata={
                "sender_id": metadata.sender_id,
                "sender_type": metadata.sender_type,
                "intent": metadata.intent.value
            }
        )
        
        # Store audit event
        await self._store_audit_event(event)
        
    async def _store_audit_event(self, event: AuditEvent) -> None:
        """Store audit event in Redis."""
        try:
            audit_key = f"security:audit:{event.event_id}"
            await self.redis.setex(audit_key, 86400 * 7, event.json())  # 7 day retention
            
            # Also add to daily audit log
            date_key = f"security:daily_audit:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            await self.redis.lpush(date_key, event.event_id)
            await self.redis.expire(date_key, 86400 * 30)  # 30 day retention
            
        except Exception as e:
            logger.error(f"Error storing audit event: {e}", exc_info=True)


# ================================
# Authorization Service
# ================================

class ProtocolAuthorizer:
    """Handles authorization for protocol operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def authorize_operation(
        self,
        context: SecurityContext,
        operation: str,
        resource: Optional[str] = None,
        protocol_layer: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Authorize an operation based on security context."""
        try:
            # Check if user/agent has required permissions
            required_permission = self._get_required_permission(operation, protocol_layer)
            if required_permission and required_permission not in context.permissions:
                await self._record_authorization_event(context, operation, resource, "denied", "insufficient_permissions")
                return False
                
            # Check protocol layer restrictions
            if protocol_layer and protocol_layer not in context.allowed_protocols:
                await self._record_authorization_event(context, operation, resource, "denied", "protocol_not_allowed")
                return False
                
            # Check security level requirements
            if not self._check_security_level(context, operation, resource):
                await self._record_authorization_event(context, operation, resource, "denied", "security_level_insufficient")
                return False
                
            # Check rate limits
            if not await self._check_rate_limits(context, operation):
                await self._record_authorization_event(context, operation, resource, "denied", "rate_limit_exceeded")
                return False
                
            # Check trust score
            if context.trust_score < self._get_minimum_trust_score(operation):
                await self._record_authorization_event(context, operation, resource, "denied", "trust_score_insufficient")
                return False
                
            # Record successful authorization
            await self._record_authorization_event(context, operation, resource, "allowed")
            return True
            
        except Exception as e:
            logger.error(f"Authorization error: {e}", exc_info=True)
            await self._record_authorization_event(context, operation, resource, "error", str(e))
            return False
            
    def _get_required_permission(self, operation: str, protocol_layer: Optional[str]) -> Optional[PermissionScope]:
        """Get required permission for an operation."""
        permission_map = {
            # MCP operations
            "mcp.tool.execute": PermissionScope.TOOL_EXECUTE,
            "mcp.tool.register": PermissionScope.TOOL_REGISTER,
            
            # A2A operations
            "a2a.agent.register": PermissionScope.AGENT_REGISTER,
            "a2a.agent.discover": PermissionScope.AGENT_DISCOVER,
            "a2a.message.send": PermissionScope.AGENT_MESSAGE,
            "a2a.capability.negotiate": PermissionScope.AGENT_NEGOTIATE,
            
            # ACP operations
            "acp.workflow.create": PermissionScope.WORKFLOW_CREATE,
            "acp.workflow.execute": PermissionScope.WORKFLOW_EXECUTE,
            "acp.task.delegate": PermissionScope.TASK_DELEGATE,
            "acp.session.manage": PermissionScope.SESSION_MANAGE,
            
            # Administrative operations
            "protocol.admin": PermissionScope.PROTOCOL_ADMIN,
            "security.audit": PermissionScope.SECURITY_AUDIT,
            "metrics.read": PermissionScope.METRICS_READ
        }
        
        return permission_map.get(operation)
        
    def _check_security_level(self, context: SecurityContext, operation: str, resource: Optional[str]) -> bool:
        """Check if security level is sufficient for operation."""
        # Define minimum security levels for operations
        security_requirements = {
            "protocol.admin": SecurityLevel.RESTRICTED,
            "security.audit": SecurityLevel.CONFIDENTIAL,
            "acp.workflow.create": SecurityLevel.CONFIDENTIAL,
            "mcp.tool.register": SecurityLevel.CONFIDENTIAL
        }
        
        required_level = security_requirements.get(operation, SecurityLevel.INTERNAL)
        
        # Map security levels to numeric values for comparison
        level_values = {
            SecurityLevel.PUBLIC: 0,
            SecurityLevel.INTERNAL: 1,
            SecurityLevel.CONFIDENTIAL: 2,
            SecurityLevel.RESTRICTED: 3
        }
        
        return level_values[context.security_level] >= level_values[required_level]
        
    async def _check_rate_limits(self, context: SecurityContext, operation: str) -> bool:
        """Check rate limits for operation."""
        try:
            # Define rate limits per tier
            rate_limits = {
                "basic": {"requests_per_minute": 10, "requests_per_hour": 100},
                "standard": {"requests_per_minute": 50, "requests_per_hour": 1000},
                "premium": {"requests_per_minute": 200, "requests_per_hour": 5000},
                "unlimited": {"requests_per_minute": float('inf'), "requests_per_hour": float('inf')}
            }
            
            tier_limits = rate_limits.get(context.rate_limit_tier, rate_limits["standard"])
            
            # Check minute rate limit
            minute_key = f"rate_limit:{context.user_id or context.agent_id}:minute:{int(time.time() // 60)}"
            minute_count = await self.redis.get(minute_key) or "0"
            
            if int(minute_count) >= tier_limits["requests_per_minute"]:
                return False
                
            # Check hour rate limit
            hour_key = f"rate_limit:{context.user_id or context.agent_id}:hour:{int(time.time() // 3600)}"
            hour_count = await self.redis.get(hour_key) or "0"
            
            if int(hour_count) >= tier_limits["requests_per_hour"]:
                return False
                
            # Increment counters
            await self.redis.incr(minute_key)
            await self.redis.expire(minute_key, 60)
            await self.redis.incr(hour_key)
            await self.redis.expire(hour_key, 3600)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}", exc_info=True)
            return True  # Allow on error
            
    def _get_minimum_trust_score(self, operation: str) -> float:
        """Get minimum trust score required for operation."""
        trust_requirements = {
            "protocol.admin": 0.9,
            "acp.workflow.create": 0.8,
            "mcp.tool.register": 0.8,
            "a2a.agent.register": 0.7
        }
        
        return trust_requirements.get(operation, 0.5)
        
    async def _record_authorization_event(
        self,
        context: SecurityContext,
        operation: str,
        resource: Optional[str],
        outcome: str,
        reason: Optional[str] = None
    ) -> None:
        """Record authorization event for audit."""
        event = AuditEvent(
            event_type="authorization",
            severity="info" if outcome == "allowed" else "warning",
            user_id=context.user_id,
            agent_id=context.agent_id,
            session_id=context.session_id,
            action=operation,
            resource=resource,
            outcome=outcome,
            message=reason,
            risk_score=1.0 - context.trust_score if outcome == "denied" else 0.0,
            metadata={
                "security_level": context.security_level.value,
                "rate_limit_tier": context.rate_limit_tier,
                "roles": context.roles,
                "authentication_method": context.authentication_method.value
            }
        )
        
        # Store audit event
        await self._store_audit_event(event)
        
    async def _store_audit_event(self, event: AuditEvent) -> None:
        """Store audit event (shared implementation)."""
        try:
            audit_key = f"security:audit:{event.event_id}"
            await self.redis.setex(audit_key, 86400 * 7, event.json())
            
            date_key = f"security:daily_audit:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            await self.redis.lpush(date_key, event.event_id)
            await self.redis.expire(date_key, 86400 * 30)
            
        except Exception as e:
            logger.error(f"Error storing audit event: {e}", exc_info=True)


# ================================
# Message Encryption Service
# ================================

class MessageEncryption:
    """Handles message encryption/decryption for secure communication."""
    
    def __init__(self):
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
    def encrypt_message(self, message: BaseProtocolMessage) -> str:
        """Encrypt a protocol message."""
        try:
            message_json = message.json()
            encrypted_data = self.cipher.encrypt(message_json.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Message encryption error: {e}", exc_info=True)
            raise
            
    def decrypt_message(self, encrypted_data: str) -> BaseProtocolMessage:
        """Decrypt a protocol message."""
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            message_json = decrypted_data.decode()
            message_dict = json.loads(message_json)
            
            # Reconstruct message based on type
            message_type = message_dict.get("message_type", message_dict.get("@type"))
            
            # For now, return as BaseProtocolMessage
            # In production, map to specific message types
            return BaseProtocolMessage(**message_dict)
            
        except Exception as e:
            logger.error(f"Message decryption error: {e}", exc_info=True)
            raise
            
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key."""
        # In production, load from secure key management service
        # For now, generate a key (this should be persistent)
        return Fernet.generate_key()


# ================================
# Security Service Manager
# ================================

class ProtocolSecurityService:
    """Main security service for protocol stack."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.authenticator = ProtocolAuthenticator(redis_client)
        self.authorizer = ProtocolAuthorizer(redis_client)
        self.encryption = MessageEncryption()
        self.threat_detector = ThreatDetector(redis_client)
        
    async def validate_message_security(
        self,
        message: BaseProtocolMessage,
        operation: str,
        protocol_layer: str
    ) -> Tuple[bool, Optional[SecurityContext], Optional[str]]:
        """Validate complete message security (auth + authz)."""
        try:
            # Authenticate message
            context = await self.authenticator.authenticate_message(message)
            if not context:
                return False, None, "Authentication failed"
                
            # Check for threats
            threat_detected = await self.threat_detector.analyze_message(message, context)
            if threat_detected:
                return False, context, "Threat detected"
                
            # Authorize operation
            authorized = await self.authorizer.authorize_operation(
                context, operation, protocol_layer=protocol_layer
            )
            
            if not authorized:
                return False, context, "Authorization failed"
                
            return True, context, None
            
        except Exception as e:
            logger.error(f"Security validation error: {e}", exc_info=True)
            return False, None, f"Security validation error: {str(e)}"
            
    async def get_security_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get security metrics for monitoring."""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_range_hours)
            
            metrics = {
                "authentication_attempts": 0,
                "authentication_successes": 0,
                "authentication_failures": 0,
                "authorization_denials": 0,
                "threat_detections": 0,
                "unique_users": set(),
                "unique_agents": set(),
                "high_risk_events": 0
            }
            
            # Aggregate metrics from daily audit logs
            for i in range(time_range_hours // 24 + 1):
                date = (start_time + timedelta(days=i)).strftime('%Y-%m-%d')
                date_key = f"security:daily_audit:{date}"
                
                event_ids = await self.redis.lrange(date_key, 0, -1)
                
                for event_id in event_ids:
                    audit_key = f"security:audit:{event_id}"
                    event_data = await self.redis.get(audit_key)
                    
                    if event_data:
                        event = AuditEvent.parse_raw(event_data)
                        
                        # Filter by time range
                        if start_time <= event.timestamp <= end_time:
                            if event.event_type == "authentication":
                                metrics["authentication_attempts"] += 1
                                if event.outcome == "success":
                                    metrics["authentication_successes"] += 1
                                else:
                                    metrics["authentication_failures"] += 1
                                    
                            elif event.event_type == "authorization" and event.outcome == "denied":
                                metrics["authorization_denials"] += 1
                                
                            elif event.event_type == "threat_detection":
                                metrics["threat_detections"] += 1
                                
                            if event.risk_score > 0.7:
                                metrics["high_risk_events"] += 1
                                
                            if event.user_id:
                                metrics["unique_users"].add(event.user_id)
                            if event.agent_id:
                                metrics["unique_agents"].add(event.agent_id)
                                
            # Convert sets to counts
            metrics["unique_users"] = len(metrics["unique_users"])
            metrics["unique_agents"] = len(metrics["unique_agents"])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}", exc_info=True)
            return {}


# ================================
# Threat Detection
# ================================

class ThreatDetector:
    """Detects potential security threats in protocol messages."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def analyze_message(self, message: BaseProtocolMessage, context: SecurityContext) -> bool:
        """Analyze message for potential threats."""
        try:
            threat_score = 0.0
            
            # Check for suspicious patterns
            threat_score += await self._check_message_frequency(context)
            threat_score += await self._check_payload_anomalies(message)
            threat_score += await self._check_trust_degradation(context)
            
            # Threshold for threat detection
            if threat_score > 0.7:
                await self._record_threat_detection(message, context, threat_score)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Threat analysis error: {e}", exc_info=True)
            return False
            
    async def _check_message_frequency(self, context: SecurityContext) -> float:
        """Check for unusual message frequency."""
        user_id = context.user_id or context.agent_id
        if not user_id:
            return 0.0
            
        # Check messages in last minute
        minute_key = f"msg_freq:{user_id}:{int(time.time() // 60)}"
        count = await self.redis.get(minute_key) or "0"
        
        # Increment counter
        await self.redis.incr(minute_key)
        await self.redis.expire(minute_key, 60)
        
        # Calculate threat score based on frequency
        if int(count) > 100:  # Very high frequency
            return 0.8
        elif int(count) > 50:  # High frequency
            return 0.5
        elif int(count) > 20:  # Moderate frequency
            return 0.2
            
        return 0.0
        
    async def _check_payload_anomalies(self, message: BaseProtocolMessage) -> float:
        """Check for payload anomalies."""
        threat_score = 0.0
        
        # Check payload size
        payload_size = len(json.dumps(message.payload))
        if payload_size > 1024 * 1024:  # 1MB
            threat_score += 0.3
            
        # Check for suspicious content
        payload_str = json.dumps(message.payload).lower()
        suspicious_patterns = ["script", "eval", "exec", "system", "shell"]
        
        for pattern in suspicious_patterns:
            if pattern in payload_str:
                threat_score += 0.2
                
        return min(1.0, threat_score)
        
    async def _check_trust_degradation(self, context: SecurityContext) -> float:
        """Check for trust score degradation."""
        if context.trust_score < 0.3:
            return 0.9
        elif context.trust_score < 0.5:
            return 0.5
        elif context.trust_score < 0.7:
            return 0.2
            
        return 0.0
        
    async def _record_threat_detection(
        self,
        message: BaseProtocolMessage,
        context: SecurityContext,
        threat_score: float
    ) -> None:
        """Record threat detection event."""
        event = AuditEvent(
            event_type="threat_detection",
            severity="critical" if threat_score > 0.9 else "warning",
            user_id=context.user_id,
            agent_id=context.agent_id,
            session_id=context.session_id,
            protocol_layer=message.metadata.protocol_layer,
            action="threat_detected",
            outcome="blocked",
            risk_score=threat_score,
            message=f"Threat detected with score {threat_score:.2f}",
            metadata={
                "message_type": message.message_type,
                "sender_id": message.metadata.sender_id,
                "threat_score": threat_score
            }
        )
        
        # Store audit event
        audit_key = f"security:audit:{event.event_id}"
        await self.redis.setex(audit_key, 86400 * 7, event.json())
        
        # Add to threat log
        threat_key = f"security:threats:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        await self.redis.lpush(threat_key, event.event_id)
        await self.redis.expire(threat_key, 86400 * 30)


# ================================
# Security Factory
# ================================

async def create_protocol_security_service(redis_client: redis.Redis) -> ProtocolSecurityService:
    """Create and initialize protocol security service."""
    return ProtocolSecurityService(redis_client)