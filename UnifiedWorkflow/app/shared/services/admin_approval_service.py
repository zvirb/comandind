"""
Admin Approval Workflow Service

Implements secure approval workflows for admin privilege changes:
- Multi-step privilege escalation approval
- Audit trail for all privilege changes
- Time-limited approval windows
- Emergency override with additional logging
"""

import os
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from shared.database.models import User, UserRole

logger = logging.getLogger(__name__)

class ApprovalAction(str, Enum):
    """Types of admin actions requiring approval"""
    ROLE_CHANGE = "role_change"
    USER_DELETE = "user_delete"
    PRIVILEGE_GRANT = "privilege_grant"
    SYSTEM_CONFIG = "system_config"
    EMERGENCY_ACCESS = "emergency_access"

class ApprovalStatus(str, Enum):
    """Status of approval requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"

@dataclass
class ApprovalRequest:
    """Admin approval request"""
    request_id: str
    action: ApprovalAction
    requester_id: int
    target_user_id: Optional[int]
    action_details: Dict[str, Any]
    justification: str
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus
    approvers_required: int
    approvals_received: List[Dict[str, Any]]
    emergency_override: bool = False

class AdminApprovalService:
    """
    Service for managing admin privilege approval workflows.
    
    Security Features:
    - Multi-admin approval requirements
    - Time-limited approval windows
    - Comprehensive audit logging
    - Emergency override with enhanced logging
    - Automatic expiration of pending requests
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Approval requirements by action type
        self.approval_requirements = {
            ApprovalAction.ROLE_CHANGE: {
                "approvers_required": 2,
                "approval_window_hours": 24,
                "emergency_override_allowed": True
            },
            ApprovalAction.USER_DELETE: {
                "approvers_required": 2,
                "approval_window_hours": 48,
                "emergency_override_allowed": False
            },
            ApprovalAction.PRIVILEGE_GRANT: {
                "approvers_required": 3,
                "approval_window_hours": 24,
                "emergency_override_allowed": True
            },
            ApprovalAction.SYSTEM_CONFIG: {
                "approvers_required": 2,
                "approval_window_hours": 12,
                "emergency_override_allowed": True
            },
            ApprovalAction.EMERGENCY_ACCESS: {
                "approvers_required": 1,
                "approval_window_hours": 2,
                "emergency_override_allowed": True
            }
        }
        
        # Redis keys
        self.APPROVAL_PREFIX = "admin:approval:"
        self.PENDING_REQUESTS = "admin:pending_requests"
        self.AUDIT_LOG_PREFIX = "admin:audit:"
        
        self._redis_pool: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection with connection pooling."""
        if self._redis_pool is None:
            self._redis_pool = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True
            )
        return self._redis_pool
    
    def _generate_request_id(self) -> str:
        """Generate unique request identifier."""
        return f"req-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(8)}"
    
    async def _store_approval_request(self, request: ApprovalRequest) -> None:
        """Store approval request in Redis."""
        redis_client = await self._get_redis()
        
        request_data = {
            "action": request.action.value,
            "requester_id": request.requester_id,
            "target_user_id": request.target_user_id or 0,
            "action_details": str(request.action_details),
            "justification": request.justification,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat(),
            "status": request.status.value,
            "approvers_required": request.approvers_required,
            "approvals_received": str(request.approvals_received),
            "emergency_override": request.emergency_override
        }
        
        # Store request data
        await redis_client.hset(f"{self.APPROVAL_PREFIX}{request.request_id}", mapping=request_data)
        
        # Add to pending requests set
        if request.status == ApprovalStatus.PENDING:
            await redis_client.sadd(self.PENDING_REQUESTS, request.request_id)
        
        # Set expiration
        ttl = int((request.expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await redis_client.expire(f"{self.APPROVAL_PREFIX}{request.request_id}", ttl)
        
        logger.info(f"Stored approval request {request.request_id} for action {request.action.value}")
    
    async def _load_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load approval request from Redis."""
        redis_client = await self._get_redis()
        
        request_data = await redis_client.hgetall(f"{self.APPROVAL_PREFIX}{request_id}")
        if not request_data:
            return None
        
        try:
            return ApprovalRequest(
                request_id=request_id,
                action=ApprovalAction(request_data["action"]),
                requester_id=int(request_data["requester_id"]),
                target_user_id=int(request_data["target_user_id"]) if int(request_data["target_user_id"]) > 0 else None,
                action_details=eval(request_data["action_details"]),
                justification=request_data["justification"],
                created_at=datetime.fromisoformat(request_data["created_at"]),
                expires_at=datetime.fromisoformat(request_data["expires_at"]),
                status=ApprovalStatus(request_data["status"]),
                approvers_required=int(request_data["approvers_required"]),
                approvals_received=eval(request_data["approvals_received"]),
                emergency_override=request_data["emergency_override"].lower() == "true"
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse approval request {request_id}: {e}")
            return None
    
    async def _log_audit_event(
        self, 
        event_type: str, 
        user_id: int, 
        details: Dict[str, Any],
        request_id: str = None
    ) -> None:
        """Log audit event for admin actions."""
        redis_client = await self._get_redis()
        
        audit_entry = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": str(details),
            "request_id": request_id or "direct"
        }
        
        # Store audit log entry
        audit_key = f"{self.AUDIT_LOG_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        await redis_client.lpush(audit_key, str(audit_entry))
        
        # Keep audit logs for 90 days
        await redis_client.expire(audit_key, 90 * 24 * 3600)
        
        logger.info(f"Audit log: {event_type} by user {user_id}")
    
    async def create_approval_request(
        self,
        action: ApprovalAction,
        requester_id: int,
        justification: str,
        target_user_id: Optional[int] = None,
        action_details: Optional[Dict[str, Any]] = None,
        emergency_override: bool = False
    ) -> str:
        """
        Create a new approval request.
        
        Args:
            action: Type of admin action requiring approval
            requester_id: ID of user requesting the action
            justification: Business justification for the action
            target_user_id: ID of user being affected (if applicable)
            action_details: Additional details about the action
            emergency_override: Whether this is an emergency override request
            
        Returns:
            Request ID for tracking the approval
        """
        now = datetime.now(timezone.utc)
        requirements = self.approval_requirements[action]
        
        # Emergency override validation
        if emergency_override and not requirements["emergency_override_allowed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Emergency override not allowed for action {action.value}"
            )
        
        # Adjust requirements for emergency override
        if emergency_override:
            approvers_required = 1
            approval_window_hours = 1  # 1 hour for emergency
        else:
            approvers_required = requirements["approvers_required"]
            approval_window_hours = requirements["approval_window_hours"]
        
        request = ApprovalRequest(
            request_id=self._generate_request_id(),
            action=action,
            requester_id=requester_id,
            target_user_id=target_user_id,
            action_details=action_details or {},
            justification=justification,
            created_at=now,
            expires_at=now + timedelta(hours=approval_window_hours),
            status=ApprovalStatus.PENDING,
            approvers_required=approvers_required,
            approvals_received=[],
            emergency_override=emergency_override
        )
        
        await self._store_approval_request(request)
        
        # Log the request creation
        await self._log_audit_event(
            event_type="approval_request_created",
            user_id=requester_id,
            details={
                "action": action.value,
                "target_user_id": target_user_id,
                "emergency_override": emergency_override,
                "justification": justification
            },
            request_id=request.request_id
        )
        
        return request.request_id
    
    async def approve_request(
        self,
        request_id: str,
        approver_id: int,
        approval_note: str = None
    ) -> Dict[str, Any]:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request to approve
            approver_id: ID of the approving admin
            approval_note: Optional note from the approver
            
        Returns:
            Dictionary with approval status and next steps
        """
        request = await self._load_approval_request(request_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        # Check if request is still pending
        if request.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request is already {request.status.value}"
            )
        
        # Check if request has expired
        if datetime.now(timezone.utc) > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            await self._store_approval_request(request)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval request has expired"
            )
        
        # Check if approver is the requester (prevent self-approval)
        if approver_id == request.requester_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve your own request"
            )
        
        # Check if approver already approved
        for approval in request.approvals_received:
            if approval.get("approver_id") == approver_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already approved this request"
                )
        
        # Add approval
        approval = {
            "approver_id": approver_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "note": approval_note or ""
        }
        request.approvals_received.append(approval)
        
        # Check if we have enough approvals
        if len(request.approvals_received) >= request.approvers_required:
            request.status = ApprovalStatus.APPROVED
            
            # Remove from pending requests
            redis_client = await self._get_redis()
            await redis_client.srem(self.PENDING_REQUESTS, request_id)
        
        await self._store_approval_request(request)
        
        # Log the approval
        await self._log_audit_event(
            event_type="approval_granted",
            user_id=approver_id,
            details={
                "request_id": request_id,
                "action": request.action.value,
                "note": approval_note or "",
                "approvals_count": len(request.approvals_received),
                "required_count": request.approvers_required
            },
            request_id=request_id
        )
        
        return {
            "status": request.status.value,
            "approvals_received": len(request.approvals_received),
            "approvals_required": request.approvers_required,
            "ready_to_execute": request.status == ApprovalStatus.APPROVED,
            "expires_at": request.expires_at.isoformat()
        }
    
    async def reject_request(
        self,
        request_id: str,
        rejector_id: int,
        rejection_reason: str
    ) -> None:
        """
        Reject a pending request.
        
        Args:
            request_id: ID of the request to reject
            rejector_id: ID of the rejecting admin
            rejection_reason: Reason for rejection
        """
        request = await self._load_approval_request(request_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        if request.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request is already {request.status.value}"
            )
        
        request.status = ApprovalStatus.REJECTED
        await self._store_approval_request(request)
        
        # Remove from pending requests
        redis_client = await self._get_redis()
        await redis_client.srem(self.PENDING_REQUESTS, request_id)
        
        # Log the rejection
        await self._log_audit_event(
            event_type="approval_rejected",
            user_id=rejector_id,
            details={
                "request_id": request_id,
                "action": request.action.value,
                "reason": rejection_reason
            },
            request_id=request_id
        )
    
    async def execute_approved_request(
        self,
        request_id: str,
        executor_id: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """
        Execute an approved admin action.
        
        Args:
            request_id: ID of the approved request
            executor_id: ID of the admin executing the action
            db_session: Database session for executing the action
            
        Returns:
            Dictionary with execution results
        """
        request = await self._load_approval_request(request_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        if request.status != ApprovalStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request is not approved (status: {request.status.value})"
            )
        
        # Execute the approved action
        execution_result = await self._execute_action(request, executor_id, db_session)
        
        # Mark as executed
        request.status = ApprovalStatus.EXECUTED
        await self._store_approval_request(request)
        
        # Log the execution
        await self._log_audit_event(
            event_type="approval_executed",
            user_id=executor_id,
            details={
                "request_id": request_id,
                "action": request.action.value,
                "execution_result": execution_result
            },
            request_id=request_id
        )
        
        return execution_result
    
    async def _execute_action(
        self,
        request: ApprovalRequest,
        executor_id: int,
        db_session: Session
    ) -> Dict[str, Any]:
        """Execute the specific admin action."""
        try:
            if request.action == ApprovalAction.ROLE_CHANGE:
                return await self._execute_role_change(request, db_session)
            elif request.action == ApprovalAction.USER_DELETE:
                return await self._execute_user_delete(request, db_session)
            else:
                raise ValueError(f"Unknown action type: {request.action}")
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute action: {str(e)}"
            )
    
    async def _execute_role_change(self, request: ApprovalRequest, db_session: Session) -> Dict[str, Any]:
        """Execute role change action."""
        target_user = db_session.query(User).filter(User.id == request.target_user_id).first()
        if not target_user:
            raise ValueError("Target user not found")
        
        old_role = target_user.role
        new_role = UserRole(request.action_details.get("new_role"))
        
        target_user.role = new_role
        target_user.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        
        return {
            "action": "role_change",
            "user_id": target_user.id,
            "old_role": old_role.value,
            "new_role": new_role.value,
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _execute_user_delete(self, request: ApprovalRequest, db_session: Session) -> Dict[str, Any]:
        """Execute user deletion action."""
        target_user = db_session.query(User).filter(User.id == request.target_user_id).first()
        if not target_user:
            raise ValueError("Target user not found")
        
        user_email = target_user.email
        db_session.delete(target_user)
        db_session.commit()
        
        return {
            "action": "user_delete",
            "user_id": request.target_user_id,
            "user_email": user_email,
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_pending_requests(self, requester_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        redis_client = await self._get_redis()
        pending_request_ids = await redis_client.smembers(self.PENDING_REQUESTS)
        
        requests = []
        for request_id in pending_request_ids:
            request = await self._load_approval_request(request_id)
            if request and (requester_id is None or request.requester_id == requester_id):
                requests.append({
                    "request_id": request.request_id,
                    "action": request.action.value,
                    "requester_id": request.requester_id,
                    "target_user_id": request.target_user_id,
                    "justification": request.justification,
                    "created_at": request.created_at.isoformat(),
                    "expires_at": request.expires_at.isoformat(),
                    "approvals_received": len(request.approvals_received),
                    "approvals_required": request.approvers_required,
                    "emergency_override": request.emergency_override
                })
        
        return requests
    
    async def cleanup_expired_requests(self) -> int:
        """Clean up expired approval requests."""
        redis_client = await self._get_redis()
        pending_request_ids = await redis_client.smembers(self.PENDING_REQUESTS)
        
        expired_count = 0
        now = datetime.now(timezone.utc)
        
        for request_id in pending_request_ids:
            request = await self._load_approval_request(request_id)
            if request and now > request.expires_at:
                request.status = ApprovalStatus.EXPIRED
                await self._store_approval_request(request)
                await redis_client.srem(self.PENDING_REQUESTS, request_id)
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired approval requests")
        
        return expired_count

# Global instance
_admin_approval_service: Optional[AdminApprovalService] = None

def get_admin_approval_service() -> AdminApprovalService:
    """Get the global admin approval service instance."""
    global _admin_approval_service
    
    if _admin_approval_service is None:
        _admin_approval_service = AdminApprovalService()
    
    return _admin_approval_service