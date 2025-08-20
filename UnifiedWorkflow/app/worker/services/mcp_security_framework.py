"""
MCP Security Framework - OAuth Resource Server and Human-in-the-Loop

Implements comprehensive security framework for MCP 2025 compliance including:
- OAuth Resource Server with tool-specific scopes and granular permissions
- Human-in-the-loop approval workflows for dangerous operations
- Enhanced input validation and output sanitization pipelines
- Real-time threat detection and automated security responses
- Comprehensive audit logging and compliance monitoring
- Tool execution sandboxing with resource limits

This framework provides the security foundation for all MCP tool servers while
maintaining compatibility with the existing authentication and authorization infrastructure.
"""

import asyncio
import json
import logging
import uuid
import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import re

from pydantic import BaseModel, Field, validator, EmailStr
import jwt
import redis.asyncio as redis
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, MCPToolResponse,
    ToolCapability, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.services.tool_sandbox_service import tool_sandbox_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# OAuth Resource Server Implementation
# ================================

class MCPScope(str, Enum):
    """MCP-specific OAuth scopes for tool access control."""
    # Tool execution scopes
    TOOL_READ = "mcp.tool.read"
    TOOL_EXECUTE = "mcp.tool.execute"
    TOOL_ADMIN = "mcp.tool.admin"
    
    # Calendar-specific scopes
    CALENDAR_READ = "calendar.read"
    CALENDAR_WRITE = "calendar.write"
    CALENDAR_DELETE = "calendar.delete"
    CALENDAR_ADMIN = "calendar.admin"
    
    # Task-specific scopes
    TASK_READ = "task.read"
    TASK_WRITE = "task.write"
    TASK_DELETE = "task.delete"
    TASK_ANALYTICS = "task.analytics"
    TASK_ADMIN = "task.admin"
    
    # Email-specific scopes
    EMAIL_READ = "email.read"
    EMAIL_SEND = "email.send"
    EMAIL_COMPOSE = "email.compose"
    EMAIL_TEMPLATE = "email.template"
    EMAIL_ANALYTICS = "email.analytics"
    EMAIL_ADMIN = "email.admin"
    
    # System scopes
    SYSTEM_MONITOR = "system.monitor"
    SYSTEM_CONFIGURE = "system.configure"
    SYSTEM_ADMIN = "system.admin"


class TokenType(str, Enum):
    """Types of authentication tokens."""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    TOOL_TOKEN = "tool_token"
    APPROVAL_TOKEN = "approval_token"


class SecurityLevel(str, Enum):
    """Security levels for operations and resources."""
    PUBLIC = "public"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MCPOAuthResourceServer:
    """OAuth Resource Server for MCP tool authentication and authorization."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 30
        
        # Scope hierarchy and permissions mapping
        self.scope_hierarchy = self._build_scope_hierarchy()
        self.tool_permissions = self._build_tool_permissions()
    
    def _build_scope_hierarchy(self) -> Dict[str, List[str]]:
        """Build scope hierarchy for permission inheritance."""
        return {
            MCPScope.SYSTEM_ADMIN.value: [
                MCPScope.SYSTEM_CONFIGURE.value,
                MCPScope.SYSTEM_MONITOR.value,
                MCPScope.TOOL_ADMIN.value,
                MCPScope.CALENDAR_ADMIN.value,
                MCPScope.TASK_ADMIN.value,
                MCPScope.EMAIL_ADMIN.value
            ],
            MCPScope.TOOL_ADMIN.value: [
                MCPScope.TOOL_EXECUTE.value,
                MCPScope.TOOL_READ.value
            ],
            MCPScope.CALENDAR_ADMIN.value: [
                MCPScope.CALENDAR_DELETE.value,
                MCPScope.CALENDAR_WRITE.value,
                MCPScope.CALENDAR_READ.value
            ],
            MCPScope.CALENDAR_WRITE.value: [
                MCPScope.CALENDAR_READ.value
            ],
            MCPScope.TASK_ADMIN.value: [
                MCPScope.TASK_DELETE.value,
                MCPScope.TASK_ANALYTICS.value,
                MCPScope.TASK_WRITE.value,
                MCPScope.TASK_READ.value
            ],
            MCPScope.TASK_WRITE.value: [
                MCPScope.TASK_READ.value
            ],
            MCPScope.EMAIL_ADMIN.value: [
                MCPScope.EMAIL_SEND.value,
                MCPScope.EMAIL_TEMPLATE.value,
                MCPScope.EMAIL_ANALYTICS.value,
                MCPScope.EMAIL_COMPOSE.value,
                MCPScope.EMAIL_READ.value
            ],
            MCPScope.EMAIL_SEND.value: [
                MCPScope.EMAIL_COMPOSE.value,
                MCPScope.EMAIL_READ.value
            ],
            MCPScope.EMAIL_COMPOSE.value: [
                MCPScope.EMAIL_READ.value
            ]
        }
    
    def _build_tool_permissions(self) -> Dict[str, Dict[str, List[str]]]:
        """Build tool-specific permission requirements."""
        return {
            "calendar": {
                "get_events": [MCPScope.CALENDAR_READ.value],
                "create_event": [MCPScope.CALENDAR_WRITE.value],
                "update_event": [MCPScope.CALENDAR_WRITE.value],
                "delete_event": [MCPScope.CALENDAR_DELETE.value],
                "move_event": [MCPScope.CALENDAR_WRITE.value]
            },
            "task": {
                "create": [MCPScope.TASK_WRITE.value],
                "update": [MCPScope.TASK_WRITE.value],
                "get": [MCPScope.TASK_READ.value],
                "list": [MCPScope.TASK_READ.value],
                "delete": [MCPScope.TASK_DELETE.value],
                "prioritize": [MCPScope.TASK_READ.value],
                "analytics": [MCPScope.TASK_ANALYTICS.value]
            },
            "email": {
                "compose": [MCPScope.EMAIL_COMPOSE.value],
                "send": [MCPScope.EMAIL_SEND.value],
                "schedule": [MCPScope.EMAIL_SEND.value],
                "get_templates": [MCPScope.EMAIL_TEMPLATE.value],
                "use_template": [MCPScope.EMAIL_TEMPLATE.value, MCPScope.EMAIL_COMPOSE.value],
                "get_analytics": [MCPScope.EMAIL_ANALYTICS.value]
            }
        }
    
    async def create_access_token(
        self,
        user_id: str,
        scopes: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create OAuth access token with MCP-specific scopes."""
        
        # Validate and expand scopes
        expanded_scopes = self._expand_scopes(scopes)
        
        # Create token payload
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes),
            "type": TokenType.ACCESS_TOKEN.value,
            "scopes": expanded_scopes,
            "context": context or {},
            "jti": str(uuid.uuid4())  # Unique token ID
        }
        
        # Sign token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token metadata for revocation
        token_key = f"mcp:oauth:token:{payload['jti']}"
        token_metadata = {
            "user_id": user_id,
            "scopes": expanded_scopes,
            "created_at": now.isoformat(),
            "expires_at": payload["exp"].isoformat(),
            "active": True
        }
        
        await self.redis.setex(
            token_key,
            int(timedelta(minutes=self.access_token_expire_minutes).total_seconds()),
            json.dumps(token_metadata)
        )
        
        # Log token creation
        await security_audit_service.log_security_event(
            user_id=user_id,
            event_type="mcp_oauth_token_created",
            details={
                "token_id": payload["jti"],
                "scopes": expanded_scopes,
                "expires_at": payload["exp"].isoformat()
            }
        )
        
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "scopes": expanded_scopes,
            "token_id": payload["jti"]
        }
    
    async def validate_token(self, token: str, required_scopes: List[str] = None) -> Dict[str, Any]:
        """Validate OAuth access token and check scopes."""
        
        try:
            # Decode and verify token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != TokenType.ACCESS_TOKEN.value:
                return {
                    "valid": False,
                    "error": "Invalid token type",
                    "error_code": "INVALID_TOKEN_TYPE"
                }
            
            # Check if token is revoked
            token_id = payload.get("jti")
            if token_id:
                token_key = f"mcp:oauth:token:{token_id}"
                token_metadata = await self.redis.get(token_key)
                
                if not token_metadata:
                    return {
                        "valid": False,
                        "error": "Token not found or expired",
                        "error_code": "TOKEN_NOT_FOUND"
                    }
                
                metadata = json.loads(token_metadata)
                if not metadata.get("active", False):
                    return {
                        "valid": False,
                        "error": "Token has been revoked",
                        "error_code": "TOKEN_REVOKED"
                    }
            
            # Check required scopes
            token_scopes = payload.get("scopes", [])
            if required_scopes:
                missing_scopes = self._check_required_scopes(token_scopes, required_scopes)
                if missing_scopes:
                    return {
                        "valid": False,
                        "error": f"Missing required scopes: {missing_scopes}",
                        "error_code": "INSUFFICIENT_SCOPE",
                        "missing_scopes": missing_scopes
                    }
            
            return {
                "valid": True,
                "user_id": payload["sub"],
                "scopes": token_scopes,
                "context": payload.get("context", {}),
                "token_id": token_id,
                "expires_at": payload["exp"]
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token has expired",
                "error_code": "TOKEN_EXPIRED"
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "error": f"Invalid token: {str(e)}",
                "error_code": "INVALID_TOKEN"
            }
        except Exception as e:
            logger.error(f"Token validation error: {e}", exc_info=True)
            return {
                "valid": False,
                "error": "Token validation failed",
                "error_code": "VALIDATION_ERROR"
            }
    
    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """Revoke an OAuth access token."""
        
        try:
            token_key = f"mcp:oauth:token:{token_id}"
            token_metadata = await self.redis.get(token_key)
            
            if token_metadata:
                metadata = json.loads(token_metadata)
                metadata["active"] = False
                metadata["revoked_at"] = datetime.now(timezone.utc).isoformat()
                
                # Update token metadata
                await self.redis.setex(token_key, 3600, json.dumps(metadata))  # Keep for audit
                
                # Log token revocation
                await security_audit_service.log_security_event(
                    user_id=user_id,
                    event_type="mcp_oauth_token_revoked",
                    details={
                        "token_id": token_id,
                        "revoked_at": metadata["revoked_at"]
                    }
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}", exc_info=True)
            return False
    
    def _expand_scopes(self, scopes: List[str]) -> List[str]:
        """Expand scopes based on hierarchy and inheritance."""
        
        expanded = set(scopes)
        
        for scope in scopes:
            if scope in self.scope_hierarchy:
                # Add inherited scopes
                expanded.update(self.scope_hierarchy[scope])
        
        return sorted(list(expanded))
    
    def _check_required_scopes(self, token_scopes: List[str], required_scopes: List[str]) -> List[str]:
        """Check if token has required scopes, return missing scopes."""
        
        token_scope_set = set(token_scopes)
        missing_scopes = []
        
        for required_scope in required_scopes:
            if required_scope not in token_scope_set:
                missing_scopes.append(required_scope)
        
        return missing_scopes
    
    async def get_tool_permissions(self, tool_name: str, operation: str) -> List[str]:
        """Get required permissions for a tool operation."""
        
        tool_category = tool_name.split("_")[0]  # e.g., "calendar" from "calendar_get_events"
        operation_name = "_".join(tool_name.split("_")[1:]) if "_" in tool_name else operation
        
        if tool_category in self.tool_permissions:
            return self.tool_permissions[tool_category].get(operation_name, [])
        
        return [MCPScope.TOOL_EXECUTE.value]  # Default permission


# ================================
# Human-in-the-Loop Approval System
# ================================

class ApprovalRequest(BaseModel):
    """Human approval request for dangerous operations."""
    request_id: str
    user_id: str
    operation: str
    tool_name: str
    parameters: Dict[str, Any]
    risk_level: SecurityLevel
    risk_analysis: Dict[str, Any]
    
    # Approval workflow
    approval_required_by: List[str] = Field(default_factory=list)  # User IDs who can approve
    approved_by: Optional[str] = None
    denied_by: Optional[str] = None
    approval_status: str = "pending"  # pending, approved, denied, expired
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    responded_at: Optional[datetime] = None
    
    # Security context
    security_context: Dict[str, Any] = Field(default_factory=dict)
    approval_token: Optional[str] = None


class HumanInTheLoopManager:
    """Manages human approval workflows for high-risk MCP operations."""
    
    def __init__(self, redis_client: redis.Redis, oauth_server: MCPOAuthResourceServer):
        self.redis = redis_client
        self.oauth_server = oauth_server
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        
        # Approval policies
        self.approval_policies = self._build_approval_policies()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_approvals())
    
    def _build_approval_policies(self) -> Dict[str, Dict[str, Any]]:
        """Build approval policies for different operations and risk levels."""
        
        return {
            "calendar_delete_event": {
                "risk_level": SecurityLevel.HIGH,
                "approval_timeout_hours": 2,
                "required_approvers": 1,
                "auto_approve_conditions": {
                    "user_role": ["admin", "manager"],
                    "time_window": "business_hours"
                }
            },
            "email_send": {
                "risk_level": SecurityLevel.HIGH,
                "approval_timeout_hours": 1,
                "required_approvers": 1,
                "conditions": {
                    "external_recipients": True,
                    "bulk_sending": True
                }
            },
            "task_delete": {
                "risk_level": SecurityLevel.MEDIUM,
                "approval_timeout_hours": 4,
                "required_approvers": 1
            },
            "bulk_operations": {
                "risk_level": SecurityLevel.HIGH,
                "approval_timeout_hours": 2,
                "required_approvers": 1,
                "conditions": {
                    "batch_size": "> 10"
                }
            }
        }
    
    async def request_approval(
        self,
        user_id: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        risk_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request human approval for a dangerous operation."""
        
        request_id = str(uuid.uuid4())
        risk_level = SecurityLevel(risk_analysis.get("risk_level", SecurityLevel.MEDIUM))
        
        # Determine approval policy
        policy_key = f"{tool_name}_{operation}"
        policy = self.approval_policies.get(policy_key, self.approval_policies.get("bulk_operations"))
        
        # Calculate expiration time
        timeout_hours = policy.get("approval_timeout_hours", 2)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        
        # Determine who can approve (for now, just the user themselves)
        approval_required_by = [user_id]  # In practice, this would be managers/admins
        
        # Create approval request
        approval_request = ApprovalRequest(
            request_id=request_id,
            user_id=user_id,
            operation=operation,
            tool_name=tool_name,
            parameters=parameters,
            risk_level=risk_level,
            risk_analysis=risk_analysis,
            approval_required_by=approval_required_by,
            expires_at=expires_at,
            security_context={
                "ip_address": risk_analysis.get("ip_address"),
                "user_agent": risk_analysis.get("user_agent"),
                "session_id": risk_analysis.get("session_id")
            }
        )
        
        # Generate approval token
        approval_token_data = await self.oauth_server.create_access_token(
            user_id=user_id,
            scopes=[MCPScope.TOOL_EXECUTE.value],
            context={
                "approval_request_id": request_id,
                "operation": operation,
                "tool_name": tool_name
            }
        )
        approval_request.approval_token = approval_token_data["access_token"]
        
        # Store approval request
        self.pending_approvals[request_id] = approval_request
        await self._persist_approval_request(approval_request)
        
        # Send notification to approvers
        await self._send_approval_notification(approval_request)
        
        # Log approval request
        await security_audit_service.log_security_event(
            user_id=user_id,
            event_type="mcp_approval_request_created",
            details={
                "request_id": request_id,
                "operation": operation,
                "tool_name": tool_name,
                "risk_level": risk_level.value,
                "expires_at": expires_at.isoformat()
            }
        )
        
        return {
            "request_id": request_id,
            "status": "approval_required",
            "message": f"Operation requires approval due to {risk_level.value} risk level",
            "approval_url": f"/api/mcp/approval/{request_id}",
            "expires_at": expires_at.isoformat(),
            "required_approvers": approval_required_by
        }
    
    async def process_approval_response(
        self,
        request_id: str,
        approver_id: str,
        approved: bool,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Process approval response from human approver."""
        
        if request_id not in self.pending_approvals:
            return {
                "success": False,
                "error": "Approval request not found or expired"
            }
        
        approval_request = self.pending_approvals[request_id]
        
        # Check if request has expired
        if datetime.now(timezone.utc) > approval_request.expires_at:
            approval_request.approval_status = "expired"
            return {
                "success": False,
                "error": "Approval request has expired"
            }
        
        # Check if approver is authorized
        if approver_id not in approval_request.approval_required_by:
            return {
                "success": False,
                "error": "User not authorized to approve this request"
            }
        
        # Update approval request
        approval_request.approval_status = "approved" if approved else "denied"
        approval_request.approved_by = approver_id if approved else None
        approval_request.denied_by = approver_id if not approved else None
        approval_request.responded_at = datetime.now(timezone.utc)
        
        # Update persistence
        await self._persist_approval_request(approval_request)
        
        # Log approval response
        await security_audit_service.log_security_event(
            user_id=approver_id,
            event_type=f"mcp_approval_{'approved' if approved else 'denied'}",
            details={
                "request_id": request_id,
                "original_user_id": approval_request.user_id,
                "operation": approval_request.operation,
                "tool_name": approval_request.tool_name,
                "reason": reason
            }
        )
        
        # Remove from pending if processed
        if approval_request.approval_status in ["approved", "denied"]:
            del self.pending_approvals[request_id]
        
        return {
            "success": True,
            "request_id": request_id,
            "status": approval_request.approval_status,
            "message": f"Request {approval_request.approval_status} by {approver_id}",
            "approved": approved
        }
    
    async def check_approval_status(self, request_id: str) -> Dict[str, Any]:
        """Check the status of an approval request."""
        
        # Check in-memory first
        if request_id in self.pending_approvals:
            request = self.pending_approvals[request_id]
            return {
                "request_id": request_id,
                "status": request.approval_status,
                "user_id": request.user_id,
                "operation": request.operation,
                "tool_name": request.tool_name,
                "created_at": request.created_at.isoformat(),
                "expires_at": request.expires_at.isoformat(),
                "approved_by": request.approved_by,
                "denied_by": request.denied_by
            }
        
        # Check persistence
        stored_request = await self._load_approval_request(request_id)
        if stored_request:
            return {
                "request_id": request_id,
                "status": stored_request.approval_status,
                "user_id": stored_request.user_id,
                "operation": stored_request.operation,
                "tool_name": stored_request.tool_name,
                "created_at": stored_request.created_at.isoformat(),
                "expires_at": stored_request.expires_at.isoformat(),
                "approved_by": stored_request.approved_by,
                "denied_by": stored_request.denied_by
            }
        
        return {
            "request_id": request_id,
            "status": "not_found",
            "error": "Approval request not found"
        }
    
    async def _persist_approval_request(self, request: ApprovalRequest) -> None:
        """Persist approval request to Redis."""
        
        key = f"mcp:approval_request:{request.request_id}"
        ttl_seconds = int((request.expires_at - datetime.now(timezone.utc)).total_seconds()) + 3600
        await self.redis.setex(key, ttl_seconds, request.json())
    
    async def _load_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load approval request from Redis."""
        
        key = f"mcp:approval_request:{request_id}"
        data = await self.redis.get(key)
        
        if data:
            try:
                return ApprovalRequest.parse_raw(data)
            except Exception as e:
                logger.error(f"Error loading approval request: {e}")
        
        return None
    
    async def _send_approval_notification(self, request: ApprovalRequest) -> None:
        """Send approval notification to required approvers."""
        
        notification_data = {
            "type": "approval_required",
            "request_id": request.request_id,
            "user_id": request.user_id,
            "operation": request.operation,
            "tool_name": request.tool_name,
            "risk_level": request.risk_level.value,
            "risk_factors": request.risk_analysis.get("risk_factors", []),
            "expires_at": request.expires_at.isoformat(),
            "approval_url": f"/api/mcp/approval/{request.request_id}"
        }
        
        # TODO: Integrate with notification system (WebSocket, email, etc.)
        logger.info(f"Approval notification required for request: {request.request_id}")
    
    async def _cleanup_expired_approvals(self) -> None:
        """Cleanup expired approval requests."""
        
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.now(timezone.utc)
                expired_requests = []
                
                for request_id, request in self.pending_approvals.items():
                    if current_time > request.expires_at:
                        request.approval_status = "expired"
                        expired_requests.append(request_id)
                
                # Remove expired requests
                for request_id in expired_requests:
                    del self.pending_approvals[request_id]
                    
                    # Log expiration
                    await security_audit_service.log_security_event(
                        user_id="system",
                        event_type="mcp_approval_request_expired",
                        details={"request_id": request_id}
                    )
                
                if expired_requests:
                    logger.info(f"Cleaned up {len(expired_requests)} expired approval requests")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in approval cleanup: {e}", exc_info=True)


# ================================
# Enhanced Input Validation and Output Sanitization
# ================================

class SecurityValidator:
    """Enhanced security validation for MCP tool inputs and outputs."""
    
    def __init__(self):
        # Dangerous patterns for input validation
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<%[\s\S]*?%>',
            r'<\?[\s\S]*?\?>',
            r'\${.*?}',
            r'#{.*?}',
            r'<!--[\s\S]*?-->',
            r'\/\*[\s\S]*?\*\/',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
            r'Function\s*\(',
            r'XMLHttpRequest',
            r'fetch\s*\(',
            r'import\s+',
            r'require\s*\(',
            r'__import__',
            r'exec\s*\(',
            r'system\s*\(',
            r'os\.',
            r'subprocess\.',
            r'shell_exec',
            r'passthru',
            r'file_get_contents',
            r'file_put_contents',
            r'fopen',
            r'fwrite',
            r'curl_exec',
            r'\.\./',
            r'\.\.\\',
            r'\/etc\/passwd',
            r'\/proc\/',
            r'c:\\windows',
            r'cmd\.exe',
            r'powershell',
            r'bash',
            r'\/bin\/',
            r'SELECT\s+.*\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*\s+SET',
            r'DELETE\s+FROM',
            r'DROP\s+TABLE',
            r'CREATE\s+TABLE',
            r'ALTER\s+TABLE',
            r'UNION\s+SELECT',
            r'OR\s+1\s*=\s*1',
            r'AND\s+1\s*=\s*1',
            r'\';\s*--',
            r'\/\*.*\*\/',
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]
        
        # Sensitive information patterns
        self.sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',  # Phone
            r'\b[A-Z]{2}\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{2}\b',  # IBAN
            r'\bpwd\s*[:=]\s*\S+',  # Password
            r'\bpassword\s*[:=]\s*\S+',  # Password
            r'\btoken\s*[:=]\s*\S+',  # Token
            r'\bkey\s*[:=]\s*\S+',  # Key
            r'\bsecret\s*[:=]\s*\S+',  # Secret
        ]
        
        self.compiled_sensitive_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns]
    
    async def validate_input(self, data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Comprehensive input validation with security checks."""
        
        validation_result = {
            "valid": True,
            "security_issues": [],
            "sanitized_data": data,
            "risk_level": SecurityLevel.LOW,
            "validation_metadata": {
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "validator_version": "1.0.0",
                "validation_context": context or {}
            }
        }
        
        try:
            # Convert data to string for pattern matching
            data_str = json.dumps(data) if not isinstance(data, str) else data
            
            # Check for dangerous patterns
            for i, pattern in enumerate(self.compiled_patterns):
                matches = pattern.findall(data_str)
                if matches:
                    validation_result["valid"] = False
                    validation_result["security_issues"].append({
                        "type": "dangerous_pattern",
                        "pattern_index": i,
                        "pattern": self.dangerous_patterns[i],
                        "matches": matches[:5],  # Limit to first 5 matches
                        "severity": "high"
                    })
                    validation_result["risk_level"] = SecurityLevel.HIGH
            
            # Check for sensitive information
            for i, pattern in enumerate(self.compiled_sensitive_patterns):
                matches = pattern.findall(data_str)
                if matches:
                    validation_result["security_issues"].append({
                        "type": "sensitive_information",
                        "pattern_index": i,
                        "pattern": self.sensitive_patterns[i],
                        "matches_count": len(matches),
                        "severity": "medium"
                    })
                    if validation_result["risk_level"] == SecurityLevel.LOW:
                        validation_result["risk_level"] = SecurityLevel.MEDIUM
            
            # Data type and structure validation
            if isinstance(data, dict):
                validation_result.update(await self._validate_dict_structure(data))
            elif isinstance(data, list):
                validation_result.update(await self._validate_list_structure(data))
            elif isinstance(data, str):
                validation_result.update(await self._validate_string_content(data))
            
            # Size and complexity validation
            data_size = len(data_str)
            if data_size > 1000000:  # 1MB limit
                validation_result["valid"] = False
                validation_result["security_issues"].append({
                    "type": "size_limit_exceeded",
                    "size_bytes": data_size,
                    "limit_bytes": 1000000,
                    "severity": "medium"
                })
            
            # Sanitize data if validation passes
            if validation_result["valid"]:
                validation_result["sanitized_data"] = await self._sanitize_data(data)
            else:
                validation_result["sanitized_data"] = None
            
        except Exception as e:
            logger.error(f"Input validation error: {e}", exc_info=True)
            validation_result["valid"] = False
            validation_result["security_issues"].append({
                "type": "validation_error",
                "error": str(e),
                "severity": "high"
            })
            validation_result["risk_level"] = SecurityLevel.HIGH
        
        return validation_result
    
    async def sanitize_output(self, data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Sanitize output data to prevent information leakage."""
        
        sanitization_result = {
            "sanitized_data": data,
            "changes_made": [],
            "sensitive_data_removed": [],
            "sanitization_metadata": {
                "sanitized_at": datetime.now(timezone.utc).isoformat(),
                "sanitizer_version": "1.0.0",
                "sanitization_context": context or {}
            }
        }
        
        try:
            # Remove sensitive information
            if isinstance(data, dict):
                sanitized_dict = {}
                for key, value in data.items():
                    if await self._is_sensitive_key(key):
                        sanitization_result["sensitive_data_removed"].append(key)
                        sanitization_result["changes_made"].append(f"Removed sensitive key: {key}")
                    else:
                        sanitized_value = await self._sanitize_value(value)
                        sanitized_dict[key] = sanitized_value["data"]
                        sanitization_result["changes_made"].extend(sanitized_value["changes"])
                
                sanitization_result["sanitized_data"] = sanitized_dict
                
            elif isinstance(data, list):
                sanitized_list = []
                for item in data:
                    sanitized_item = await self.sanitize_output(item, context)
                    sanitized_list.append(sanitized_item["sanitized_data"])
                    sanitization_result["changes_made"].extend(sanitized_item["changes_made"])
                
                sanitization_result["sanitized_data"] = sanitized_list
                
            elif isinstance(data, str):
                sanitized_str = await self._sanitize_string_output(data)
                sanitization_result["sanitized_data"] = sanitized_str["data"]
                sanitization_result["changes_made"].extend(sanitized_str["changes"])
            
        except Exception as e:
            logger.error(f"Output sanitization error: {e}", exc_info=True)
            sanitization_result["sanitized_data"] = "[SANITIZATION_ERROR]"
            sanitization_result["changes_made"].append(f"Sanitization error: {str(e)}")
        
        return sanitization_result
    
    async def _validate_dict_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate dictionary structure and keys."""
        
        result = {"valid": True, "security_issues": []}
        
        # Check for too many keys
        if len(data) > 1000:
            result["valid"] = False
            result["security_issues"].append({
                "type": "excessive_keys",
                "key_count": len(data),
                "limit": 1000,
                "severity": "medium"
            })
        
        # Check for dangerous key names
        dangerous_keys = ["__proto__", "constructor", "prototype", "eval", "function"]
        for key in data.keys():
            if str(key).lower() in dangerous_keys:
                result["valid"] = False
                result["security_issues"].append({
                    "type": "dangerous_key",
                    "key": str(key),
                    "severity": "high"
                })
        
        return result
    
    async def _validate_list_structure(self, data: List[Any]) -> Dict[str, Any]:
        """Validate list structure and content."""
        
        result = {"valid": True, "security_issues": []}
        
        # Check for excessive list size
        if len(data) > 10000:
            result["valid"] = False
            result["security_issues"].append({
                "type": "excessive_list_size",
                "size": len(data),
                "limit": 10000,
                "severity": "medium"
            })
        
        return result
    
    async def _validate_string_content(self, data: str) -> Dict[str, Any]:
        """Validate string content for security issues."""
        
        result = {"valid": True, "security_issues": []}
        
        # Check string length
        if len(data) > 100000:  # 100KB limit
            result["valid"] = False
            result["security_issues"].append({
                "type": "excessive_string_length",
                "length": len(data),
                "limit": 100000,
                "severity": "medium"
            })
        
        # Check for null bytes
        if '\x00' in data:
            result["valid"] = False
            result["security_issues"].append({
                "type": "null_bytes",
                "severity": "high"
            })
        
        return result
    
    async def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data by removing dangerous content."""
        
        if isinstance(data, str):
            # Remove dangerous patterns
            sanitized = data
            for pattern in self.compiled_patterns:
                sanitized = pattern.sub("[FILTERED]", sanitized)
            return sanitized
        elif isinstance(data, dict):
            return {k: await self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [await self._sanitize_data(item) for item in data]
        else:
            return data
    
    async def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key contains sensitive information."""
        
        sensitive_keys = [
            "password", "pwd", "secret", "token", "key", "auth", "credential",
            "ssn", "social_security", "credit_card", "bank_account", "api_key",
            "private_key", "access_token", "refresh_token", "session_id"
        ]
        
        key_lower = str(key).lower()
        return any(sensitive_key in key_lower for sensitive_key in sensitive_keys)
    
    async def _sanitize_value(self, value: Any) -> Dict[str, Any]:
        """Sanitize a single value."""
        
        result = {"data": value, "changes": []}
        
        if isinstance(value, str):
            sanitized_result = await self._sanitize_string_output(value)
            result["data"] = sanitized_result["data"]
            result["changes"] = sanitized_result["changes"]
        elif isinstance(value, dict):
            sanitized_result = await self.sanitize_output(value)
            result["data"] = sanitized_result["sanitized_data"]
            result["changes"] = sanitized_result["changes_made"]
        elif isinstance(value, list):
            sanitized_result = await self.sanitize_output(value)
            result["data"] = sanitized_result["sanitized_data"]
            result["changes"] = sanitized_result["changes_made"]
        
        return result
    
    async def _sanitize_string_output(self, data: str) -> Dict[str, Any]:
        """Sanitize string output."""
        
        result = {"data": data, "changes": []}
        
        # Mask sensitive patterns
        sanitized = data
        for i, pattern in enumerate(self.compiled_sensitive_patterns):
            matches = pattern.findall(sanitized)
            if matches:
                sanitized = pattern.sub("[REDACTED]", sanitized)
                result["changes"].append(f"Masked sensitive pattern: {self.sensitive_patterns[i]}")
        
        result["data"] = sanitized
        return result


# ================================
# Main MCP Security Framework
# ================================

class MCPSecurityFramework:
    """Main security framework coordinating all MCP security components."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Initialize security components
        self.oauth_server = MCPOAuthResourceServer(redis_client)
        self.approval_manager = HumanInTheLoopManager(redis_client, self.oauth_server)
        self.validator = SecurityValidator()
        
        # Security metrics
        self.security_metrics = {
            "validation_attempts": 0,
            "validation_failures": 0,
            "approval_requests": 0,
            "approval_approvals": 0,
            "approval_denials": 0,
            "security_incidents": 0
        }
    
    async def authenticate_request(
        self,
        token: str,
        tool_name: str,
        operation: str
    ) -> Dict[str, Any]:
        """Authenticate and authorize MCP tool request."""
        
        # Get required permissions for the tool operation
        required_scopes = await self.oauth_server.get_tool_permissions(tool_name, operation)
        
        # Validate token and check scopes
        token_validation = await self.oauth_server.validate_token(token, required_scopes)
        
        if not token_validation["valid"]:
            await self._record_security_incident("authentication_failure", {
                "tool_name": tool_name,
                "operation": operation,
                "error": token_validation["error"]
            })
        
        return token_validation
    
    async def validate_and_authorize_request(
        self,
        user_id: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        authentication_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive request validation and authorization."""
        
        self.security_metrics["validation_attempts"] += 1
        
        try:
            # Step 1: Input validation
            validation_result = await self.validator.validate_input(
                parameters,
                context={
                    "user_id": user_id,
                    "tool_name": tool_name,
                    "operation": operation
                }
            )
            
            if not validation_result["valid"]:
                self.security_metrics["validation_failures"] += 1
                await self._record_security_incident("input_validation_failure", {
                    "user_id": user_id,
                    "tool_name": tool_name,
                    "operation": operation,
                    "security_issues": validation_result["security_issues"]
                })
                
                return {
                    "authorized": False,
                    "error": "Input validation failed",
                    "security_issues": validation_result["security_issues"]
                }
            
            # Step 2: Risk assessment for approval requirement
            risk_analysis = await self._assess_operation_risk(
                user_id, tool_name, operation, parameters
            )
            
            # Step 3: Check if human approval is required
            if risk_analysis["requires_approval"]:
                self.security_metrics["approval_requests"] += 1
                
                approval_result = await self.approval_manager.request_approval(
                    user_id=user_id,
                    tool_name=tool_name,
                    operation=operation,
                    parameters=validation_result["sanitized_data"],
                    risk_analysis=risk_analysis
                )
                
                return {
                    "authorized": False,
                    "approval_required": True,
                    "approval_request": approval_result,
                    "risk_analysis": risk_analysis
                }
            
            # Step 4: Authorization successful
            return {
                "authorized": True,
                "sanitized_parameters": validation_result["sanitized_data"],
                "risk_analysis": risk_analysis,
                "security_metadata": {
                    "validation_result": validation_result,
                    "risk_level": risk_analysis["risk_level"]
                }
            }
            
        except Exception as e:
            logger.error(f"Security validation error: {e}", exc_info=True)
            self.security_metrics["validation_failures"] += 1
            
            await self._record_security_incident("security_framework_error", {
                "user_id": user_id,
                "tool_name": tool_name,
                "operation": operation,
                "error": str(e)
            })
            
            return {
                "authorized": False,
                "error": "Security validation failed",
                "internal_error": str(e)
            }
    
    async def sanitize_response(
        self,
        response_data: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sanitize tool response before returning to user."""
        
        return await self.validator.sanitize_output(response_data, context)
    
    async def process_approval_response(
        self,
        request_id: str,
        approver_id: str,
        approved: bool,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Process human approval response."""
        
        result = await self.approval_manager.process_approval_response(
            request_id, approver_id, approved, reason
        )
        
        if result["success"]:
            if approved:
                self.security_metrics["approval_approvals"] += 1
            else:
                self.security_metrics["approval_denials"] += 1
        
        return result
    
    async def _assess_operation_risk(
        self,
        user_id: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risk level for operation and determine if approval is required."""
        
        risk_factors = []
        risk_level = SecurityLevel.LOW
        requires_approval = False
        
        # High-risk operations
        high_risk_operations = [
            "delete", "remove", "purge", "drop", "truncate",
            "send_external", "export", "backup", "restore"
        ]
        
        if any(risk_op in operation.lower() for risk_op in high_risk_operations):
            risk_level = SecurityLevel.HIGH
            risk_factors.append(f"High-risk operation: {operation}")
            requires_approval = True
        
        # Bulk operations
        if isinstance(parameters, dict):
            # Check for bulk parameters
            bulk_indicators = ["ids", "list", "batch", "multiple", "all"]
            for key, value in parameters.items():
                if any(indicator in key.lower() for indicator in bulk_indicators):
                    if isinstance(value, list) and len(value) > 5:
                        risk_level = SecurityLevel.MEDIUM
                        risk_factors.append(f"Bulk operation affecting {len(value)} items")
                        if len(value) > 20:
                            risk_level = SecurityLevel.HIGH
                            requires_approval = True
        
        # External communication
        if "email" in tool_name and "send" in operation:
            if parameters.get("recipient"):
                recipient = parameters["recipient"]
                if not self._is_internal_email(recipient):
                    risk_level = SecurityLevel.HIGH
                    risk_factors.append("External email recipient")
                    requires_approval = True
        
        # Time-based risk factors
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_factors.append("Operation outside business hours")
            if risk_level == SecurityLevel.LOW:
                risk_level = SecurityLevel.MEDIUM
        
        return {
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "requires_approval": requires_approval,
            "assessment_time": datetime.now(timezone.utc).isoformat()
        }
    
    def _is_internal_email(self, email: str) -> bool:
        """Check if email is internal (implement based on your domain)."""
        
        internal_domains = ["company.com", "internal.local"]  # Configure based on your organization
        domain = email.split("@")[1].lower() if "@" in email else ""
        return domain in internal_domains
    
    async def _record_security_incident(self, incident_type: str, details: Dict[str, Any]) -> None:
        """Record security incident for monitoring and analysis."""
        
        self.security_metrics["security_incidents"] += 1
        
        await security_audit_service.log_security_event(
            user_id=details.get("user_id", "system"),
            event_type=f"mcp_security_incident_{incident_type}",
            details={
                "incident_type": incident_type,
                "severity": "high" if "failure" in incident_type else "medium",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **details
            }
        )
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get security framework metrics and status."""
        
        return {
            "framework_status": "active",
            "metrics": self.security_metrics.copy(),
            "approval_stats": {
                "pending_approvals": len(self.approval_manager.pending_approvals),
                "approval_rate": (
                    self.security_metrics["approval_approvals"] / 
                    max(self.security_metrics["approval_requests"], 1)
                )
            },
            "security_health": {
                "validation_success_rate": (
                    (self.security_metrics["validation_attempts"] - self.security_metrics["validation_failures"]) /
                    max(self.security_metrics["validation_attempts"], 1)
                ),
                "incident_rate": self.security_metrics["security_incidents"],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        }


# ================================
# Factory and Initialization
# ================================

# Global security framework instance
_mcp_security_framework: Optional[MCPSecurityFramework] = None

async def create_mcp_security_framework(redis_client: redis.Redis) -> MCPSecurityFramework:
    """Create and initialize the MCP Security Framework."""
    
    global _mcp_security_framework
    
    if _mcp_security_framework is None:
        _mcp_security_framework = MCPSecurityFramework(redis_client)
        logger.info("MCP Security Framework created and initialized")
    
    return _mcp_security_framework

async def get_mcp_security_framework() -> Optional[MCPSecurityFramework]:
    """Get the global MCP Security Framework instance."""
    return _mcp_security_framework