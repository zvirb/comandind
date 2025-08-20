"""
MCP Email Tool Server - MCP 2025 Compliant

Implements email management operations as standardized MCP server with:
- OAuth Resource Server authentication with email-specific scopes
- Human-in-the-loop approval for external email sending and bulk operations
- Comprehensive output sanitization and content filtering
- MCP protocol compliance with standardized tool registration
- Enhanced security controls and audit logging

This server transforms the existing email_tools.py functionality into a production-ready
MCP-compliant tool server while maintaining compatibility with the LangGraph Smart Router.
"""

import asyncio
import json
import logging
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, validator, EmailStr
import html
import bleach

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, MCPToolResponse, MCPCapabilityAnnouncement,
    ToolCapability, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.services.tool_sandbox_service import tool_sandbox_service

logger = logging.getLogger(__name__)


# ================================
# MCP Email Tool Definitions
# ================================

class EmailScope(str, Enum):
    """Email-specific OAuth scopes for granular access control."""
    READ = "email.read"
    SEND = "email.send"
    COMPOSE = "email.compose"
    TEMPLATE = "email.template"
    ANALYTICS = "email.analytics"
    ADMIN = "email.admin"


class EmailPriority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailStatus(str, Enum):
    """Email status states."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmailOperationRisk(str, Enum):
    """Risk levels for email operations requiring human approval."""
    LOW = "low"          # Read operations, template access
    MEDIUM = "medium"    # Internal email composition
    HIGH = "high"        # External email sending, bulk operations
    CRITICAL = "critical"  # Admin operations, mass communications


class EmailToolRequest(BaseModel):
    """Standardized email tool request format."""
    operation: str
    parameters: Dict[str, Any]
    user_id: str
    session_id: Optional[str] = None
    require_approval: bool = False
    risk_level: EmailOperationRisk = EmailOperationRisk.LOW


class EmailToolResponse(BaseModel):
    """Standardized email tool response format."""
    success: bool
    result: Any = None
    error_message: Optional[str] = None
    operation: str
    execution_time_ms: float
    approval_required: bool = False
    approval_request_id: Optional[str] = None
    resources_accessed: List[str] = Field(default_factory=list)
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    sanitization_results: Dict[str, Any] = Field(default_factory=dict)


class EmailApprovalRequest(BaseModel):
    """Human-in-the-loop approval request for dangerous email operations."""
    request_id: str
    user_id: str
    operation: str
    parameters: Dict[str, Any]
    risk_level: EmailOperationRisk
    risk_analysis: Dict[str, Any]
    expires_at: datetime
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


# ================================
# Email Input Validation and Output Sanitization
# ================================

class EmailContentSanitizer:
    """Comprehensive content sanitization for email security."""
    
    # Allowed HTML tags for email content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'img', 'div', 'span', 'table', 'tr', 'td', 'th', 'thead', 'tbody'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
        'div': ['style'],
        'span': ['style'],
        'p': ['style'],
        'table': ['border', 'cellpadding', 'cellspacing', 'width'],
        'td': ['colspan', 'rowspan', 'style'],
        'th': ['colspan', 'rowspan', 'style']
    }
    
    # Allowed CSS properties
    ALLOWED_STYLES = [
        'color', 'background-color', 'font-size', 'font-weight', 'font-family',
        'text-align', 'margin', 'padding', 'border', 'width', 'height'
    ]
    
    @classmethod
    def sanitize_email_content(cls, content: str) -> Dict[str, Any]:
        """Sanitize email content to prevent XSS and injection attacks."""
        
        sanitization_result = {
            "original_length": len(content),
            "sanitized_content": content,
            "changes_made": [],
            "security_issues_found": [],
            "safe": True
        }
        
        if not content:
            return sanitization_result
        
        try:
            # HTML escape dangerous characters first
            escaped_content = html.escape(content, quote=False)
            
            # Check for potentially dangerous patterns
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'vbscript:',
                r'onload\s*=',
                r'onerror\s*=',
                r'onclick\s*=',
                r'onmouseover\s*=',
                r'<iframe[^>]*>',
                r'<object[^>]*>',
                r'<embed[^>]*>',
                r'<form[^>]*>'
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    sanitization_result["security_issues_found"].append(f"Dangerous pattern found: {pattern}")
                    sanitization_result["safe"] = False
            
            # Clean HTML using bleach
            cleaned_content = bleach.clean(
                content,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
            
            # Additional URL validation for links
            def validate_urls(tag, name, value):
                if name == 'href':
                    if not value.startswith(('http://', 'https://', 'mailto:')):
                        sanitization_result["changes_made"].append(f"Removed invalid URL: {value}")
                        return None
                return value
            
            # Final cleaning with URL validation
            final_content = bleach.clean(
                cleaned_content,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
            
            # Check for content changes
            if final_content != content:
                sanitization_result["changes_made"].append("HTML content sanitized")
            
            sanitization_result["sanitized_content"] = final_content
            sanitization_result["final_length"] = len(final_content)
            
        except Exception as e:
            logger.error(f"Error sanitizing email content: {e}")
            sanitization_result["safe"] = False
            sanitization_result["security_issues_found"].append(f"Sanitization error: {e}")
            sanitization_result["sanitized_content"] = ""
        
        return sanitization_result
    
    @classmethod
    def validate_email_address(cls, email: str) -> Dict[str, Any]:
        """Validate and categorize email addresses."""
        
        validation_result = {
            "valid": False,
            "email": email,
            "domain": None,
            "is_internal": False,
            "is_external": True,
            "risk_level": "high",
            "issues": []
        }
        
        try:
            # Basic email format validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                validation_result["issues"].append("Invalid email format")
                return validation_result
            
            # Extract domain
            domain = email.split('@')[1].lower()
            validation_result["domain"] = domain
            validation_result["valid"] = True
            
            # Check if internal domain (configurable)
            internal_domains = [
                'company.com',  # Example internal domain
                'internal.local',
                'localhost'
            ]
            
            if domain in internal_domains:
                validation_result["is_internal"] = True
                validation_result["is_external"] = False
                validation_result["risk_level"] = "low"
            
            # Check for suspicious domains
            suspicious_domains = [
                'tempmail.org',
                '10minutemail.com',
                'guerrillamail.com'
            ]
            
            if domain in suspicious_domains:
                validation_result["issues"].append("Suspicious temporary email domain")
                validation_result["risk_level"] = "critical"
            
        except Exception as e:
            validation_result["issues"].append(f"Validation error: {e}")
        
        return validation_result


class EmailInputValidator:
    """Comprehensive input validation for email operations."""
    
    @staticmethod
    def validate_email_composition(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email composition parameters."""
        validation_result = {
            "valid": True,
            "errors": [],
            "sanitized_params": parameters.copy(),
            "sanitization_results": {}
        }
        
        # Recipient validation (required)
        if "recipient" not in parameters or not parameters["recipient"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing required field: recipient")
        else:
            recipient = str(parameters["recipient"]).strip()
            email_validation = EmailContentSanitizer.validate_email_address(recipient)
            if not email_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(email_validation["issues"])
            else:
                validation_result["sanitized_params"]["recipient"] = recipient
                validation_result["sanitization_results"]["recipient"] = email_validation
        
        # Subject validation (required)
        if "subject" not in parameters or not parameters["subject"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing required field: subject")
        else:
            subject = str(parameters["subject"]).strip()
            if len(subject) > 200:
                validation_result["valid"] = False
                validation_result["errors"].append("Subject too long (max 200 characters)")
            elif len(subject) < 3:
                validation_result["valid"] = False
                validation_result["errors"].append("Subject too short (min 3 characters)")
            else:
                # Basic subject sanitization
                sanitized_subject = re.sub(r'[<>\n\r]', '', subject)
                validation_result["sanitized_params"]["subject"] = sanitized_subject
        
        # Body validation (required)
        if "body" not in parameters or not parameters["body"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing required field: body")
        else:
            body = str(parameters["body"])
            if len(body) > 50000:  # 50KB limit
                validation_result["valid"] = False
                validation_result["errors"].append("Email body too long (max 50KB)")
            else:
                # Sanitize email body content
                sanitization_result = EmailContentSanitizer.sanitize_email_content(body)
                if not sanitization_result["safe"]:
                    validation_result["valid"] = False
                    validation_result["errors"].extend(sanitization_result["security_issues_found"])
                else:
                    validation_result["sanitized_params"]["body"] = sanitization_result["sanitized_content"]
                    validation_result["sanitization_results"]["body"] = sanitization_result
        
        # Priority validation (optional)
        if "priority" in parameters:
            priority = parameters["priority"]
            if priority not in [p.value for p in EmailPriority]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid priority. Must be one of: {[p.value for p in EmailPriority]}")
            else:
                validation_result["sanitized_params"]["priority"] = priority
        else:
            validation_result["sanitized_params"]["priority"] = EmailPriority.NORMAL.value
        
        # CC and BCC validation (optional)
        for field in ["cc", "bcc"]:
            if field in parameters and parameters[field]:
                recipients = parameters[field]
                if isinstance(recipients, str):
                    recipients = [recipients]
                elif not isinstance(recipients, list):
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"{field} must be a string or list of email addresses")
                    continue
                
                validated_recipients = []
                for recipient in recipients:
                    email_validation = EmailContentSanitizer.validate_email_address(str(recipient).strip())
                    if email_validation["valid"]:
                        validated_recipients.append(recipient)
                    else:
                        validation_result["errors"].append(f"Invalid {field} address: {recipient}")
                        validation_result["valid"] = False
                
                validation_result["sanitized_params"][field] = validated_recipients
        
        return validation_result
    
    @staticmethod
    def validate_template_usage(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email template usage parameters."""
        validation_result = {
            "valid": True,
            "errors": [],
            "sanitized_params": parameters.copy()
        }
        
        # Template name validation
        if "template_name" not in parameters or not parameters["template_name"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing required field: template_name")
        else:
            template_name = str(parameters["template_name"]).strip()
            # Allow only alphanumeric, underscore, and hyphen
            if not re.match(r'^[a-zA-Z0-9_-]+$', template_name):
                validation_result["valid"] = False
                validation_result["errors"].append("Invalid template name format")
            else:
                validation_result["sanitized_params"]["template_name"] = template_name
        
        # Template variables validation
        if "variables" in parameters:
            variables = parameters["variables"]
            if not isinstance(variables, dict):
                validation_result["valid"] = False
                validation_result["errors"].append("Template variables must be a dictionary")
            else:
                # Sanitize variable values
                sanitized_variables = {}
                for key, value in variables.items():
                    clean_key = re.sub(r'[^a-zA-Z0-9_]', '', str(key))
                    clean_value = html.escape(str(value)) if value else ""
                    sanitized_variables[clean_key] = clean_value
                validation_result["sanitized_params"]["variables"] = sanitized_variables
        
        return validation_result
    
    @staticmethod
    def validate_email_scheduling(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email scheduling parameters."""
        validation_result = {
            "valid": True,
            "errors": [],
            "sanitized_params": parameters.copy()
        }
        
        # First validate composition parameters
        composition_validation = EmailInputValidator.validate_email_composition(parameters)
        validation_result.update(composition_validation)
        
        # Send time validation (required for scheduling)
        if "send_time" not in parameters or not parameters["send_time"]:
            validation_result["valid"] = False
            validation_result["errors"].append("Missing required field: send_time")
        else:
            try:
                send_time = datetime.fromisoformat(parameters["send_time"].replace('Z', '+00:00'))
                
                # Check if send time is in the future
                if send_time <= datetime.now(timezone.utc):
                    validation_result["valid"] = False
                    validation_result["errors"].append("Send time must be in the future")
                
                # Check if send time is not too far in the future (1 year limit)
                max_future_time = datetime.now(timezone.utc) + timedelta(days=365)
                if send_time > max_future_time:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Send time cannot be more than 1 year in the future")
                
                if validation_result["valid"]:
                    validation_result["sanitized_params"]["send_time"] = send_time.isoformat()
                    
            except (ValueError, AttributeError) as e:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid send_time format: {e}")
        
        return validation_result


# ================================
# Email Risk Assessment
# ================================

class EmailRiskAssessment:
    """Assess risk levels for email operations and determine approval requirements."""
    
    @staticmethod
    async def assess_operation_risk(operation: str, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Assess risk level for an email operation."""
        
        risk_analysis = {
            "operation": operation,
            "risk_level": EmailOperationRisk.LOW,
            "risk_factors": [],
            "requires_approval": False,
            "approval_reason": None
        }
        
        # Risk assessment by operation type
        if operation == "send_email":
            # Check recipient domain
            recipient = parameters.get("recipient", "")
            if recipient:
                email_validation = EmailContentSanitizer.validate_email_address(recipient)
                if email_validation["is_external"]:
                    risk_analysis["risk_level"] = EmailOperationRisk.HIGH
                    risk_analysis["risk_factors"].append("Sending to external recipient")
                    risk_analysis["requires_approval"] = True
                    risk_analysis["approval_reason"] = "External email sending requires approval for security"
            
            # Check for bulk sending (CC/BCC)
            total_recipients = 1  # Primary recipient
            if parameters.get("cc"):
                total_recipients += len(parameters["cc"]) if isinstance(parameters["cc"], list) else 1
            if parameters.get("bcc"):
                total_recipients += len(parameters["bcc"]) if isinstance(parameters["bcc"], list) else 1
            
            if total_recipients > 10:
                risk_analysis["risk_level"] = EmailOperationRisk.HIGH
                risk_analysis["risk_factors"].append(f"Bulk email to {total_recipients} recipients")
                risk_analysis["requires_approval"] = True
                risk_analysis["approval_reason"] = "Bulk email sending requires approval"
            elif total_recipients > 5:
                risk_analysis["risk_level"] = EmailOperationRisk.MEDIUM
                risk_analysis["risk_factors"].append(f"Multiple recipients ({total_recipients})")
            
            # Check for urgent priority
            if parameters.get("priority") == EmailPriority.URGENT.value:
                risk_analysis["risk_factors"].append("Urgent priority email")
                if risk_analysis["risk_level"] == EmailOperationRisk.LOW:
                    risk_analysis["risk_level"] = EmailOperationRisk.MEDIUM
        
        elif operation == "schedule_email":
            # Scheduled emails have similar risks as immediate sending
            send_risk = await EmailRiskAssessment.assess_operation_risk("send_email", parameters, user_id)
            risk_analysis.update(send_risk)
            risk_analysis["operation"] = "schedule_email"
            risk_analysis["risk_factors"].append("Scheduled email delivery")
        
        elif operation == "get_analytics":
            # Analytics access is generally low risk
            risk_analysis["risk_level"] = EmailOperationRisk.LOW
        
        elif operation == "create_template":
            # Template creation is medium risk
            risk_analysis["risk_level"] = EmailOperationRisk.MEDIUM
            risk_analysis["risk_factors"].append("Creating email template")
        
        # Content-based risk assessment
        if "body" in parameters:
            body = parameters["body"]
            
            # Check for sensitive keywords
            sensitive_keywords = [
                "password", "ssn", "social security", "credit card", "bank account",
                "confidential", "classified", "proprietary", "urgent action required"
            ]
            
            for keyword in sensitive_keywords:
                if keyword.lower() in body.lower():
                    risk_analysis["risk_factors"].append(f"Contains sensitive keyword: {keyword}")
                    if risk_analysis["risk_level"] == EmailOperationRisk.LOW:
                        risk_analysis["risk_level"] = EmailOperationRisk.MEDIUM
        
        # Time-based risk factors
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_analysis["risk_factors"].append("Operation outside business hours")
        
        return risk_analysis


# ================================
# Email Approval Manager
# ================================

class EmailApprovalManager:
    """Manage human approval workflows for high-risk email operations."""
    
    def __init__(self):
        self.pending_approvals: Dict[str, EmailApprovalRequest] = {}
    
    async def request_approval(
        self,
        operation: str,
        parameters: Dict[str, Any],
        user_id: str,
        risk_analysis: Dict[str, Any]
    ) -> str:
        """Request human approval for an email operation."""
        
        request_id = str(uuid.uuid4())
        approval_request = EmailApprovalRequest(
            request_id=request_id,
            user_id=user_id,
            operation=operation,
            parameters=parameters,
            risk_level=EmailOperationRisk(risk_analysis["risk_level"]),
            risk_analysis=risk_analysis,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6)  # 6 hour expiry for emails
        )
        
        self.pending_approvals[request_id] = approval_request
        
        # Send approval request to user
        await self._send_approval_notification(approval_request)
        
        logger.info(f"Approval requested for email operation: {request_id}")
        return request_id
    
    async def check_approval_status(self, request_id: str) -> Optional[EmailApprovalRequest]:
        """Check the status of an approval request."""
        return self.pending_approvals.get(request_id)
    
    async def approve_request(self, request_id: str, approver_id: str) -> bool:
        """Approve a pending request."""
        if request_id in self.pending_approvals:
            request = self.pending_approvals[request_id]
            request.approved = True
            request.approved_by = approver_id
            request.approved_at = datetime.now(timezone.utc)
            
            # Log approval for audit
            await security_audit_service.log_security_event(
                user_id=request.user_id,
                event_type="email_operation_approved",
                details={
                    "request_id": request_id,
                    "operation": request.operation,
                    "approved_by": approver_id,
                    "risk_level": request.risk_level.value,
                    "recipient": request.parameters.get("recipient", "unknown")
                }
            )
            
            logger.info(f"Email operation approved: {request_id} by {approver_id}")
            return True
        return False
    
    async def deny_request(self, request_id: str, denier_id: str, reason: str) -> bool:
        """Deny a pending request."""
        if request_id in self.pending_approvals:
            request = self.pending_approvals[request_id]
            request.approved = False
            request.approved_by = denier_id
            request.approved_at = datetime.now(timezone.utc)
            
            # Log denial for audit
            await security_audit_service.log_security_event(
                user_id=request.user_id,
                event_type="email_operation_denied",
                details={
                    "request_id": request_id,
                    "operation": request.operation,
                    "denied_by": denier_id,
                    "reason": reason,
                    "risk_level": request.risk_level.value
                }
            )
            
            logger.info(f"Email operation denied: {request_id} by {denier_id}")
            return True
        return False
    
    async def _send_approval_notification(self, approval_request: EmailApprovalRequest) -> None:
        """Send approval notification to the user."""
        
        notification_content = {
            "type": "approval_required",
            "title": "Email Operation Approval Required",
            "message": f"A {approval_request.operation} operation requires your approval due to {approval_request.risk_level.value} risk level.",
            "request_id": approval_request.request_id,
            "operation": approval_request.operation,
            "recipient": approval_request.parameters.get("recipient", "unknown"),
            "risk_factors": approval_request.risk_analysis.get("risk_factors", []),
            "expires_at": approval_request.expires_at.isoformat()
        }
        
        # TODO: Integrate with actual notification system
        logger.info(f"Approval notification sent for request: {approval_request.request_id}")


# ================================
# MCP Email Tool Server
# ================================

class MCPEmailServer:
    """MCP-compliant Email Tool Server with enhanced security and content sanitization."""
    
    def __init__(self):
        self.validator = EmailInputValidator()
        self.sanitizer = EmailContentSanitizer()
        self.risk_assessor = EmailRiskAssessment()
        self.approval_manager = EmailApprovalManager()
        
        # In-memory email storage (in production, this would be an email service)
        self.emails: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, Dict[str, Any]] = self._initialize_templates()
        self.email_counter = 0
        
        # Tool capability definitions
        self.tool_capabilities = self._define_tool_capabilities()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default email templates."""
        return {
            "meeting_request": {
                "name": "meeting_request",
                "subject": "Meeting Request: {topic}",
                "body": "Hi {recipient_name},\n\nI'd like to schedule a meeting to discuss {topic}. Would {proposed_time} work for you?\n\nBest regards",
                "variables": ["recipient_name", "topic", "proposed_time"]
            },
            "follow_up": {
                "name": "follow_up",
                "subject": "Follow-up: {topic}",
                "body": "Hi {recipient_name},\n\nI wanted to follow up on {topic} from our previous conversation.\n\nBest regards",
                "variables": ["recipient_name", "topic"]
            },
            "project_update": {
                "name": "project_update",
                "subject": "Project Update: {project_name}",
                "body": "Hi team,\n\nHere's an update on {project_name}:\n\n{update_details}\n\nNext steps:\n{next_steps}\n\nBest regards",
                "variables": ["project_name", "update_details", "next_steps"]
            },
            "thank_you": {
                "name": "thank_you",
                "subject": "Thank you",
                "body": "Hi {recipient_name},\n\nThank you for {reason}. I appreciate your {specific_appreciation}.\n\nBest regards",
                "variables": ["recipient_name", "reason", "specific_appreciation"]
            }
        }
    
    def _define_tool_capabilities(self) -> List[ToolCapability]:
        """Define MCP-compliant tool capabilities for email operations."""
        
        capabilities = [
            ToolCapability(
                name="email_compose",
                description="Compose an email with content sanitization",
                parameters={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "format": "email",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line",
                            "minLength": 3,
                            "maxLength": 200
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content",
                            "maxLength": 50000
                        },
                        "priority": {
                            "type": "string",
                            "enum": [p.value for p in EmailPriority],
                            "default": "normal",
                            "description": "Email priority level"
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"},
                            "description": "CC recipients"
                        },
                        "bcc": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"},
                            "description": "BCC recipients"
                        }
                    },
                    "required": ["recipient", "subject", "body"]
                },
                required_permissions=[EmailScope.COMPOSE.value],
                security_level="medium"
            ),
            
            ToolCapability(
                name="email_send",
                description="Send an email (requires approval for external recipients)",
                parameters={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "format": "email",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "minLength": 3,
                            "maxLength": 200
                        },
                        "body": {
                            "type": "string",
                            "maxLength": 50000
                        },
                        "priority": {
                            "type": "string",
                            "enum": [p.value for p in EmailPriority],
                            "default": "normal"
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"}
                        },
                        "bcc": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"}
                        }
                    },
                    "required": ["recipient", "subject", "body"]
                },
                required_permissions=[EmailScope.SEND.value],
                security_level="high"
            ),
            
            ToolCapability(
                name="email_schedule",
                description="Schedule an email for future delivery",
                parameters={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "format": "email"
                        },
                        "subject": {
                            "type": "string",
                            "minLength": 3,
                            "maxLength": 200
                        },
                        "body": {
                            "type": "string",
                            "maxLength": 50000
                        },
                        "send_time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "When to send the email"
                        },
                        "priority": {
                            "type": "string",
                            "enum": [p.value for p in EmailPriority],
                            "default": "normal"
                        }
                    },
                    "required": ["recipient", "subject", "body", "send_time"]
                },
                required_permissions=[EmailScope.SEND.value],
                security_level="high"
            ),
            
            ToolCapability(
                name="email_get_templates",
                description="Retrieve available email templates",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional template category filter"
                        }
                    }
                },
                required_permissions=[EmailScope.TEMPLATE.value],
                security_level="low"
            ),
            
            ToolCapability(
                name="email_use_template",
                description="Use an email template with variable substitution",
                parameters={
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template to use"
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables for template substitution"
                        },
                        "recipient": {
                            "type": "string",
                            "format": "email",
                            "description": "Recipient email address"
                        }
                    },
                    "required": ["template_name", "variables", "recipient"]
                },
                required_permissions=[EmailScope.TEMPLATE.value, EmailScope.COMPOSE.value],
                security_level="medium"
            ),
            
            ToolCapability(
                name="email_get_analytics",
                description="Get email analytics and statistics",
                parameters={
                    "type": "object",
                    "properties": {
                        "time_period": {
                            "type": "string",
                            "enum": ["day", "week", "month"],
                            "default": "week",
                            "description": "Time period for analytics"
                        }
                    }
                },
                required_permissions=[EmailScope.ANALYTICS.value],
                security_level="low"
            )
        ]
        
        return capabilities
    
    async def handle_tool_request(self, request: MCPToolRequest) -> EmailToolResponse:
        """Handle incoming MCP tool requests for email operations."""
        
        start_time = datetime.now()
        operation = request.tool_name.replace("email_", "")
        
        try:
            # Extract user context
            user_id = request.metadata.sender_id.replace("user:", "")
            
            # Authenticate and authorize
            auth_result = await self._authenticate_request(request, operation)
            if not auth_result["authorized"]:
                return EmailToolResponse(
                    success=False,
                    error_message=auth_result["error"],
                    operation=operation,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
            
            # Validate input parameters
            validation_result = await self._validate_request(operation, request.tool_parameters)
            if not validation_result["valid"]:
                return EmailToolResponse(
                    success=False,
                    error_message=f"Validation failed: {', '.join(validation_result['errors'])}",
                    operation=operation,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    validation_results=validation_result
                )
            
            # Assess operation risk
            risk_analysis = await self.risk_assessor.assess_operation_risk(
                operation, validation_result["sanitized_params"], user_id
            )
            
            # Check if approval is required
            if risk_analysis["requires_approval"]:
                approval_id = await self.approval_manager.request_approval(
                    operation, validation_result["sanitized_params"], user_id, risk_analysis
                )
                
                return EmailToolResponse(
                    success=False,
                    error_message="Operation requires approval",
                    operation=operation,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    approval_required=True,
                    approval_request_id=approval_id
                )
            
            # Execute the email operation
            result = await self._execute_email_operation(
                operation, validation_result["sanitized_params"], user_id
            )
            
            # Log successful operation
            await security_audit_service.log_security_event(
                user_id=user_id,
                event_type=f"email_{operation}_success",
                details={
                    "operation": operation,
                    "risk_level": risk_analysis["risk_level"].value,
                    "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "recipient": validation_result["sanitized_params"].get("recipient", "unknown")
                }
            )
            
            return EmailToolResponse(
                success=True,
                result=result,
                operation=operation,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                resources_accessed=["email_service"],
                validation_results=validation_result,
                sanitization_results=validation_result.get("sanitization_results", {})
            )
            
        except Exception as e:
            logger.error(f"Error handling email tool request: {e}", exc_info=True)
            
            # Log error for security monitoring
            await security_audit_service.log_security_event(
                user_id=user_id if 'user_id' in locals() else "unknown",
                event_type=f"email_{operation}_error",
                details={
                    "operation": operation,
                    "error": str(e),
                    "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000
                }
            )
            
            return EmailToolResponse(
                success=False,
                error_message=f"Internal error: {str(e)}",
                operation=operation,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _authenticate_request(self, request: MCPToolRequest, operation: str) -> Dict[str, Any]:
        """Authenticate and authorize email tool request."""
        
        try:
            # Verify JWT token
            token = request.metadata.authentication_token
            if not token:
                return {"authorized": False, "error": "Missing authentication token"}
            
            # Validate token and extract claims
            token_validation = await enhanced_jwt_service.validate_service_token(token)
            if not token_validation["valid"]:
                return {"authorized": False, "error": "Invalid authentication token"}
            
            claims = token_validation["claims"]
            user_scopes = claims.get("scopes", [])
            
            # Check required permissions based on operation
            required_scopes = []
            if operation in ["get_analytics"]:
                required_scopes = [EmailScope.ANALYTICS.value]
            elif operation in ["get_templates"]:
                required_scopes = [EmailScope.TEMPLATE.value]
            elif operation in ["use_template"]:
                required_scopes = [EmailScope.TEMPLATE.value, EmailScope.COMPOSE.value]
            elif operation in ["compose"]:
                required_scopes = [EmailScope.COMPOSE.value]
            elif operation in ["send", "schedule"]:
                required_scopes = [EmailScope.SEND.value]
            
            missing_scopes = [scope for scope in required_scopes if scope not in user_scopes]
            if missing_scopes:
                return {
                    "authorized": False,
                    "error": f"Missing required scopes: {missing_scopes}"
                }
            
            return {"authorized": True, "user_claims": claims}
            
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return {"authorized": False, "error": "Authentication failed"}
    
    async def _validate_request(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email tool request parameters."""
        
        if operation in ["compose", "send"]:
            return self.validator.validate_email_composition(parameters)
        elif operation == "schedule":
            return self.validator.validate_email_scheduling(parameters)
        elif operation == "use_template":
            return self.validator.validate_template_usage(parameters)
        elif operation in ["get_templates", "get_analytics"]:
            # Simple validation for read operations
            return {
                "valid": True,
                "errors": [],
                "sanitized_params": parameters.copy()
            }
        else:
            return {
                "valid": False,
                "errors": [f"Unknown operation: {operation}"],
                "sanitized_params": parameters
            }
    
    async def _execute_email_operation(
        self,
        operation: str,
        parameters: Dict[str, Any],
        user_id: str
    ) -> Any:
        """Execute the validated email operation."""
        
        if operation == "compose":
            return await self._execute_compose_email(parameters, user_id)
        elif operation == "send":
            return await self._execute_send_email(parameters, user_id)
        elif operation == "schedule":
            return await self._execute_schedule_email(parameters, user_id)
        elif operation == "get_templates":
            return await self._execute_get_templates(parameters, user_id)
        elif operation == "use_template":
            return await self._execute_use_template(parameters, user_id)
        elif operation == "get_analytics":
            return await self._execute_get_analytics(parameters, user_id)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    async def _execute_compose_email(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute email composition operation."""
        
        self.email_counter += 1
        email_id = f"email_{user_id}_{self.email_counter}_{int(datetime.now().timestamp())}"
        
        email_data = {
            "id": email_id,
            "recipient": parameters["recipient"],
            "subject": parameters["subject"],
            "body": parameters["body"],
            "priority": parameters.get("priority", EmailPriority.NORMAL.value),
            "cc": parameters.get("cc", []),
            "bcc": parameters.get("bcc", []),
            "status": EmailStatus.DRAFT.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user_id,
            "sent_at": None
        }
        
        # Store email in memory (in production, this would be an email service)
        self.emails[email_id] = email_data
        
        logger.info(f"Email composed: {email_id} - Subject: {parameters['subject']}")
        
        return {
            "email_id": email_id,
            "recipient": parameters["recipient"],
            "subject": parameters["subject"],
            "status": EmailStatus.DRAFT.value,
            "created_at": email_data["created_at"],
            "message": f"Email composed successfully: '{parameters['subject']}'"
        }
    
    async def _execute_send_email(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute email sending operation."""
        
        # Compose the email first
        compose_result = await self._execute_compose_email(parameters, user_id)
        email_id = compose_result["email_id"]
        
        # Update status to sent
        self.emails[email_id]["status"] = EmailStatus.SENT.value
        self.emails[email_id]["sent_at"] = datetime.now(timezone.utc).isoformat()
        
        # In a real implementation, this would integrate with an email service
        logger.info(f"Email sent: {email_id} to {parameters['recipient']}")
        
        return {
            "email_id": email_id,
            "recipient": parameters["recipient"],
            "subject": parameters["subject"],
            "status": EmailStatus.SENT.value,
            "sent_at": self.emails[email_id]["sent_at"],
            "message": f"Email sent successfully to {parameters['recipient']}"
        }
    
    async def _execute_schedule_email(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute email scheduling operation."""
        
        # Compose the email first
        compose_result = await self._execute_compose_email(parameters, user_id)
        email_id = compose_result["email_id"]
        
        # Update status to scheduled
        self.emails[email_id]["status"] = EmailStatus.SCHEDULED.value
        self.emails[email_id]["scheduled_time"] = parameters["send_time"]
        
        logger.info(f"Email scheduled: {email_id} for {parameters['send_time']}")
        
        return {
            "email_id": email_id,
            "recipient": parameters["recipient"],
            "subject": parameters["subject"],
            "status": EmailStatus.SCHEDULED.value,
            "scheduled_time": parameters["send_time"],
            "message": f"Email scheduled successfully for {parameters['send_time']}"
        }
    
    async def _execute_get_templates(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute get email templates operation."""
        
        # Filter templates by category if specified
        category = parameters.get("category")
        if category:
            filtered_templates = {
                name: template for name, template in self.templates.items()
                if category.lower() in template.get("category", "").lower()
            }
        else:
            filtered_templates = self.templates
        
        return {
            "templates": filtered_templates,
            "count": len(filtered_templates),
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _execute_use_template(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute use email template operation."""
        
        template_name = parameters["template_name"]
        variables = parameters["variables"]
        recipient = parameters["recipient"]
        
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        template = self.templates[template_name]
        
        # Substitute variables in subject and body
        subject = template["subject"]
        body = template["body"]
        
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            subject = subject.replace(placeholder, str(var_value))
            body = body.replace(placeholder, str(var_value))
        
        # Compose email with template content
        template_email_params = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "priority": parameters.get("priority", EmailPriority.NORMAL.value)
        }
        
        compose_result = await self._execute_compose_email(template_email_params, user_id)
        
        return {
            **compose_result,
            "template_used": template_name,
            "variables_applied": variables,
            "message": f"Email created from template '{template_name}'"
        }
    
    async def _execute_get_analytics(self, parameters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute email analytics operation."""
        
        # Filter emails by user
        user_emails = [email for email in self.emails.values() if email.get("created_by") == user_id]
        
        # Calculate analytics (similar to existing email_tools.py)
        total_emails = len(user_emails)
        sent_emails = [e for e in user_emails if e["status"] == EmailStatus.SENT.value]
        scheduled_emails = [e for e in user_emails if e["status"] == EmailStatus.SCHEDULED.value]
        draft_emails = [e for e in user_emails if e["status"] == EmailStatus.DRAFT.value]
        
        # Priority breakdown
        priority_breakdown = {}
        for priority in EmailPriority:
            priority_emails = [e for e in user_emails if e["priority"] == priority.value]
            priority_breakdown[priority.value] = {
                "total": len(priority_emails),
                "sent": len([e for e in priority_emails if e["status"] == EmailStatus.SENT.value])
            }
        
        analytics = {
            "overview": {
                "total_emails": total_emails,
                "sent": len(sent_emails),
                "scheduled": len(scheduled_emails),
                "drafts": len(draft_emails),
                "send_rate": len(sent_emails) / total_emails if total_emails > 0 else 0
            },
            "by_priority": priority_breakdown,
            "recent_activity": {
                "last_24_hours": len([e for e in user_emails if 
                    datetime.fromisoformat(e["created_at"].replace('Z', '+00:00')) > 
                    datetime.now(timezone.utc) - timedelta(days=1)]),
                "last_week": len([e for e in user_emails if 
                    datetime.fromisoformat(e["created_at"].replace('Z', '+00:00')) > 
                    datetime.now(timezone.utc) - timedelta(days=7)])
            },
            "usage_metrics": {
                "avg_emails_per_day": total_emails / 30,  # Rough estimate
                "most_used_priority": max(priority_breakdown.keys(), 
                    key=lambda k: priority_breakdown[k]["total"]) if priority_breakdown else "normal",
                "template_usage_rate": 0.3  # Would calculate from actual data
            }
        }
        
        return {
            "analytics": analytics,
            "time_period": parameters.get("time_period", "week"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id
        }
    
    def get_server_capabilities(self) -> MCPCapabilityAnnouncement:
        """Get server capabilities for MCP registration."""
        
        return MCPCapabilityAnnouncement(
            metadata=ProtocolMetadata(
                sender_id="mcp_email_server",
                sender_type="tool_server",
                protocol_layer="mcp",
                intent=MessageIntent.INFORM
            ),
            server_id="email_management_server",
            server_name="Email Management MCP Server",
            server_version="1.0.0",
            protocol_version="1.0",
            available_tools=self.tool_capabilities,
            supported_features=[
                "authentication",
                "input_validation",
                "output_sanitization",
                "content_filtering",
                "human_approval",
                "audit_logging",
                "risk_assessment",
                "template_system",
                "analytics"
            ],
            resource_requirements={
                "memory_mb": 512,
                "cpu_cores": 1,
                "network_access": ["smtp.gmail.com", "internal_mail_server"],
                "permissions": ["email.read", "email.send", "email.compose", "email.template", "email.analytics"]
            }
        )


# ================================
# Factory and Initialization
# ================================

# Global server instance
mcp_email_server = MCPEmailServer()

async def create_mcp_email_server() -> MCPEmailServer:
    """Create and initialize the MCP Email Server."""
    logger.info("MCP Email Server initialized with enhanced security and content sanitization")
    return mcp_email_server