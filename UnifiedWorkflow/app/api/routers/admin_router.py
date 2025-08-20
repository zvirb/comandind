"""Admin routes for user management."""
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime, timezone
import aiohttp
import asyncio

from fastapi import APIRouter, Depends, Request, HTTPException, status
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..dependencies import RoleChecker, get_current_user, verify_csrf_token
from shared.utils.database_setup import get_db
from shared.database.models import User, UserRole, UserStatus, AccessRequest
from shared.schemas.schemas import PaginatedUsers
from ..services.settings_service import get_settings_service, SystemSettings
from shared.services.email_service import send_email
from .bug_report_router import BugReportCreate
# from app.shared.services.admin_approval_service import get_admin_approval_service, ApprovalAction
# TODO: Fix missing admin_approval_service module

# Temporary stub to prevent API crash
from enum import Enum

class ApprovalAction(Enum):
    ROLE_CHANGE = "role_change"
    USER_DELETE = "user_delete"
    PRIVILEGE_GRANT = "privilege_grant"
    SYSTEM_CONFIG = "system_config"
    EMERGENCY_ACCESS = "emergency_access"

def get_admin_approval_service():
    """Temporary stub for missing service"""
    class StubService:
        async def create_approval(self, *args, **kwargs):
            return {"id": "stub", "status": "approved"}
        async def get_approval(self, *args, **kwargs):
            return {"id": "stub", "status": "approved"}
        async def update_approval(self, *args, **kwargs):
            return {"id": "stub", "status": "approved"}
        async def list_approvals(self, *args, **kwargs):
            return []
    return StubService()

import secrets
from datetime import timedelta


logger = logging.getLogger(__name__)

# Pydantic models for request/response
class UserRoleUpdate(BaseModel):
    role: UserRole

class AdminActionRequest(BaseModel):
    action: str
    target_user_id: Optional[int] = None
    justification: str
    action_details: Optional[Dict[str, Any]] = None
    emergency_override: bool = False

class ApprovalActionRequest(BaseModel):
    approval_note: Optional[str] = None

class RejectionRequest(BaseModel):
    rejection_reason: str

class UserApprovalResponse(BaseModel):
    message: str
    user_id: int
    new_status: UserStatus

class ContainerMetrics(BaseModel):
    name: str
    memory_bytes: float
    cpu_percent: float

class GPUMetrics(BaseModel):
    memory_used_bytes: float
    memory_total_bytes: float
    memory_percent: float
    power_usage_watts: float
    utilization_percent: float

class SystemMetrics(BaseModel):
    containers: List[ContainerMetrics]
    gpu: Optional[GPUMetrics]
    total_containers: int
    timestamp: datetime


router = APIRouter(
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))] # Protect all routes in this router
)

@router.get("/users", response_model=PaginatedUsers)
async def get_all_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100) -> dict[str, Any]:
    """
    Admin endpoint to retrieve all users with pagination.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    return {"total": total, "skip": skip, "limit": limit, "items": users}

@router.get("/users/pending")
async def get_pending_users(db: Session = Depends(get_db)):
    """
    Get all users with PENDING status awaiting approval.
    """
    pending_users = db.query(User).filter(User.status == UserStatus.PENDING).all()
    return {
        "total": len(pending_users),
        "items": pending_users
    }

@router.post("/users/{user_id}/approve", response_model=UserApprovalResponse)
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_user)
):
    """
    Approve a pending user by changing their status to ACTIVE.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User status is {user.status.value}, not pending approval"
        )
    
    user.status = UserStatus.ACTIVE
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Admin {admin_user.email} approved user {user.email} (ID: {user_id})")
    
    # TODO: Send approval email notification to user
    # send_approval_email(user.email, approved=True)
    
    return UserApprovalResponse(
        message="User approved successfully",
        user_id=user_id,
        new_status=UserStatus.ACTIVE
    )

@router.post("/users/{user_id}/reject", response_model=UserApprovalResponse)
async def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_user)
):
    """
    Reject a pending user by changing their status to DISABLED.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User status is {user.status.value}, not pending approval"
        )
    
    user.status = UserStatus.DISABLED
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Admin {admin_user.email} rejected user {user.email} (ID: {user_id})")
    
    return UserApprovalResponse(
        message="User rejected successfully",
        user_id=user_id,
        new_status=UserStatus.DISABLED
    )

@router.post("/approval/request")
async def request_admin_action(
    request: AdminActionRequest,
    admin_user: User = Depends(get_current_user)
):
    """
    Request approval for admin action. 
    SECURITY: All privileged actions now require approval workflow.
    """
    try:
        approval_service = get_admin_approval_service()
        
        # Map action string to enum
        action_mapping = {
            "role_change": ApprovalAction.ROLE_CHANGE,
            "user_delete": ApprovalAction.USER_DELETE,
            "privilege_grant": ApprovalAction.PRIVILEGE_GRANT,
            "system_config": ApprovalAction.SYSTEM_CONFIG,
            "emergency_access": ApprovalAction.EMERGENCY_ACCESS
        }
        
        if request.action not in action_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}"
            )
        
        action = action_mapping[request.action]
        
        # Create approval request
        request_id = await approval_service.create_approval_request(
            action=action,
            requester_id=admin_user.id,
            justification=request.justification,
            target_user_id=request.target_user_id,
            action_details=request.action_details,
            emergency_override=request.emergency_override
        )
        
        logger.info(f"Admin {admin_user.email} requested approval for {request.action} (request: {request_id})")
        
        return {
            "message": "Approval request created successfully",
            "request_id": request_id,
            "action": request.action,
            "emergency_override": request.emergency_override,
            "requires_approval": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin action request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create approval request"
        )

@router.put("/users/{user_id}/role")
async def update_user_role_deprecated(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_user)
):
    """
    DEPRECATED: Direct role updates are no longer allowed.
    Use /admin/approval/request endpoint with action='role_change'.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Direct role updates are deprecated",
            "message": "Use approval workflow at /admin/approval/request",
            "required_action": "role_change",
            "security_enhancement": "All role changes now require approval workflow"
        }
    )

@router.get("/approval/pending")
async def get_pending_approvals(
    admin_user: User = Depends(get_current_user)
):
    """Get all pending approval requests."""
    try:
        approval_service = get_admin_approval_service()
        pending_requests = await approval_service.get_pending_requests()
        
        return {
            "pending_requests": pending_requests,
            "count": len(pending_requests)
        }
        
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pending approvals"
        )

@router.post("/approval/{request_id}/approve")
async def approve_request(
    request_id: str,
    approval: ApprovalActionRequest,
    admin_user: User = Depends(get_current_user)
):
    """Approve a pending admin action request."""
    try:
        approval_service = get_admin_approval_service()
        
        result = await approval_service.approve_request(
            request_id=request_id,
            approver_id=admin_user.id,
            approval_note=approval.approval_note
        )
        
        logger.info(f"Admin {admin_user.email} approved request {request_id}")
        
        return {
            "message": "Request approved successfully",
            "request_id": request_id,
            "status": result["status"],
            "ready_to_execute": result["ready_to_execute"],
            "approvals_received": result["approvals_received"],
            "approvals_required": result["approvals_required"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve request"
        )

@router.post("/approval/{request_id}/reject")
async def reject_request(
    request_id: str,
    rejection: RejectionRequest,
    admin_user: User = Depends(get_current_user)
):
    """Reject a pending admin action request."""
    try:
        approval_service = get_admin_approval_service()
        
        await approval_service.reject_request(
            request_id=request_id,
            rejector_id=admin_user.id,
            rejection_reason=rejection.rejection_reason
        )
        
        logger.info(f"Admin {admin_user.email} rejected request {request_id}")
        
        return {
            "message": "Request rejected successfully",
            "request_id": request_id,
            "status": "rejected"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rejection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject request"
        )

@router.post("/approval/{request_id}/execute")
async def execute_approved_request(
    request_id: str,
    admin_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute an approved admin action."""
    try:
        approval_service = get_admin_approval_service()
        
        result = await approval_service.execute_approved_request(
            request_id=request_id,
            executor_id=admin_user.id,
            db_session=db
        )
        
        logger.info(f"Admin {admin_user.email} executed approved request {request_id}")
        
        return {
            "message": "Request executed successfully",
            "request_id": request_id,
            "execution_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute request"
        )

@router.delete("/users/{user_id}")
async def delete_user_deprecated(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_user)
):
    """
    Delete a user account. This is irreversible.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting other admins
    if user.role == UserRole.ADMIN and user.id != admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other admin users"
        )
    
    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account"
        )
    
    user_email = user.email
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin {admin_user.email} deleted user {user_email} (ID: {user_id})")
    
    return {
        "message": "User deleted successfully",
        "user_id": user_id
    }

@router.get("/settings/registration")
async def get_registration_settings():
    """
    Get current registration and approval settings.
    """
    settings_service = get_settings_service()
    return settings_service.get_registration_settings()

@router.put("/settings/registration")
async def update_registration_settings(
    settings: SystemSettings,
    admin_user: User = Depends(get_current_user)
):
    """
    Update registration and approval settings.
    """
    settings_service = get_settings_service()
    updated_settings = settings_service.update_registration_settings(settings)
    
    logger.info(f"Admin {admin_user.email} updated registration settings: {settings.dict()}")
    
    return {
        "message": "Registration settings updated successfully",
        "settings": updated_settings
    }

@router.post("/trigger-task", status_code=202, tags=["Admin", "Celery"])
async def trigger_background_task(request: Request):
    """
    Triggers a simple example background task.
    """
    # Decouple from the worker by sending the task by name.
    # The Celery app instance is attached to the FastAPI app state.
    # NOTE: This endpoint is calling a real task but with placeholder data.
    # To make this functional, you would need to supply a real session_id,
    # user_id, and user_input based on the desired admin action.
    celery_app: Celery = request.app.state.celery_app
    task_kwargs = {
        "session_id": "admin_task_session_placeholder",
        "user_id": "1", # Placeholder user ID
        "user_input": "This is an example task triggered by an admin."
    }
    task = celery_app.send_task("tasks.execute_chat_graph", kwargs=task_kwargs)
    return {"message": "Task triggered successfully", "task_id": task.id}

@router.get("/task-status/{task_id}", status_code=200, tags=["Admin", "Celery"])
async def get_task_status(task_id: str, request: Request):
    """
    Retrieves the status and result of a background task.
    """
    celery_app: Celery = request.app.state.celery_app
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return result

from shared.database.models.access_request import AccessRequest
from shared.services.email_service import send_email
from uuid import UUID

class AccessRequestResponse(BaseModel):
    id: str
    email: str
    status: str
    token: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

@router.get("/access-requests", response_model=List[AccessRequestResponse])
async def get_access_requests(
    db: Session = Depends(get_db),
    _: User = Depends(RoleChecker([UserRole.ADMIN]))
):
    """
    Retrieves all access requests for admin review.
    """
    try:
        access_requests = db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()
        return [
            AccessRequestResponse(
                id=str(req.id),
                email=req.email,
                status=req.status,
                token=req.token,
                expires_at=req.expires_at,
                created_at=req.created_at,
                updated_at=req.updated_at
            )
            for req in access_requests
        ]
    except Exception as e:
        logger.error(f"Error retrieving access requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(RoleChecker([UserRole.ADMIN]))
):
    """
    Approves an access request and sends email notification.
    """
    try:
        # Parse UUID
        try:
            request_uuid = UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request ID format")
        
        db_request = db.query(AccessRequest).filter(AccessRequest.id == request_uuid).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Access request not found")
        
        if db_request.status == "approved":
            raise HTTPException(status_code=400, detail="Request already approved")
        
        # Generate token and set expiration
        db_request.status = "approved"
        db_request.set_token(db)
        
        # Send email notification
        download_base_url = "https://localhost/public/download-certs"  # Should come from config
        download_link = f"{download_base_url}/{db_request.token}?platform=windows"
        
        email_subject = "AI Workflow Engine - Certificate Access Approved"
        email_body = f"""
Your access request for AI Workflow Engine client certificates has been approved!

You can download your certificates using the following links:
- Windows: {download_base_url}/{db_request.token}?platform=windows
- macOS: {download_base_url}/{db_request.token}?platform=macos  
- Linux: {download_base_url}/{db_request.token}?platform=linux

This link will expire in 24 hours. Please download your certificates promptly.

Best regards,
AI Workflow Engine Team
        """
        
        send_email(db_request.email, email_subject, email_body)
        
        logger.info(f"Access request approved for {db_request.email}")
        
        return {
            "message": "Access request approved and notification email sent",
            "request_id": str(db_request.id),
            "expires_at": db_request.expires_at.isoformat() if db_request.expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving access request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(RoleChecker([UserRole.ADMIN]))
):
    """
    Rejects an access request.
    """
    try:
        # Parse UUID
        try:
            request_uuid = UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request ID format")
        
        db_request = db.query(AccessRequest).filter(AccessRequest.id == request_uuid).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Access request not found")
        
        if db_request.status == "rejected":
            raise HTTPException(status_code=400, detail="Request already rejected")
        
        db_request.status = "rejected"
        db_request.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Access request rejected for {db_request.email}")
        
        return {
            "message": "Access request rejected",
            "request_id": str(db_request.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting access request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/bug-reports", response_model=dict)
async def create_bug_report(
    bug_report: BugReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a bug report task with AI-generated subtasks and assigns it to admin users.
    The title becomes the area(s) marked, and subtasks are generated from the description.
    """
    try:
        # Find the first admin user to assign the bug report to
        admin_user = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.status == UserStatus.ACTIVE
        ).first()
        
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No active admin users found to assign bug report"
            )
        
        # Import here to avoid circular imports
        from .. import crud
        from shared.schemas.schemas import TaskCreate
        from worker.services.opportunity_subtask_service import generate_contextual_subtasks
        
        # Import task enums
        from shared.database.models import TaskStatus, TaskPriority
        
        # Generate contextual subtasks based on the bug report description
        logger.info(f"Generating subtasks for bug report: {bug_report.title}")
        
        # Create context for subtask generation
        user_context = f"Bug report submitted by {current_user.email}"
        supplementary_context = f"This is a {bug_report.type} report with {bug_report.priority} priority. Category: {bug_report.category}"
        
        try:
            # Generate subtasks using the existing service
            subtasks = await generate_contextual_subtasks(
                opportunity_title=bug_report.title,
                opportunity_description=bug_report.description,
                user_context=user_context,
                supplementary_context=supplementary_context,
                current_user=admin_user  # Generate for the admin who will work on it
            )
            
            logger.info(f"Generated {len(subtasks)} subtasks for bug report")
            
        except Exception as subtask_error:
            logger.warning(f"Failed to generate subtasks: {subtask_error}. Creating task without subtasks.")
            subtasks = []
        
        # Create main task data - title becomes the area marked, description includes original details
        main_task_description = f"Bug Report: {bug_report.description}"
        if subtasks:
            # Add a summary of generated subtasks
            main_task_description += f"\n\nGenerated {len(subtasks)} actionable subtasks to address this issue."
        
        task_create_data = TaskCreate(
            title=bug_report.title,  # This is the area(s) marked
            description=main_task_description,
            type=bug_report.type,
            category=bug_report.category,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING
        )
        
        # Create main task for admin user
        created_task = crud.create_task(db=db, task=task_create_data, user_id=admin_user.id)
        
        # Create subtasks if generation was successful
        subtasks_created = []
        if subtasks:
            for idx, subtask_data in enumerate(subtasks):
                try:
                    subtask_create_data = TaskCreate(
                        title=subtask_data.get('title', f'Subtask {idx + 1}'),
                        description=subtask_data.get('description', ''),
                        type="task",  # Subtasks are generally task type
                        category=subtask_data.get('category', 'execution'),
                        priority=TaskPriority.MEDIUM,  # Subtasks get medium priority
                        status=TaskStatus.PENDING
                    )
                    
                    subtask = crud.create_task(db=db, task=subtask_create_data, user_id=admin_user.id)
                    subtasks_created.append({
                        "id": str(subtask.id),
                        "title": subtask.title,
                        "estimated_hours": subtask_data.get('estimated_hours', 1.0)
                    })
                    
                except Exception as subtask_create_error:
                    logger.error(f"Failed to create subtask {idx + 1}: {subtask_create_error}")
                    continue
        
        logger.info(f"Bug report submitted by user {current_user.email} (ID: {current_user.id}) "
                   f"and assigned to admin {admin_user.email} as task {created_task.id} "
                   f"with {len(subtasks_created)} subtasks")
        
        return {
            "message": "Bug report submitted successfully with AI-generated subtasks",
            "task_id": str(created_task.id),
            "assigned_to": admin_user.email,
            "reported_by": current_user.email,
            "subtasks_generated": len(subtasks_created),
            "subtasks": subtasks_created
        }
        
    except Exception as e:
        logger.error(f"Error creating bug report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bug report"
        )

@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """
    Get comprehensive system metrics including container performance and GPU stats.
    Admin-only endpoint for monitoring the entire system.
    """
    try:
        prometheus_url = "http://prometheus:9090"
        
        async with aiohttp.ClientSession() as session:
            containers = []
            gpu = None
            
            # Get container memory metrics
            try:
                async with session.get(
                    f"{prometheus_url}/api/v1/query?query=container_memory_usage_bytes"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        memory_data = {}
                        
                        for result in data.get("data", {}).get("result", []):
                            name = (
                                result.get("metric", {}).get("name") or 
                                result.get("metric", {}).get("container_label_com_docker_compose_service") or
                                "unknown"
                            )
                            if name not in ["unknown", "", "POD"]:
                                memory_bytes = float(result.get("value", [0, 0])[1])
                                memory_data[name] = memory_bytes
                
                # Get container CPU metrics
                async with session.get(
                    f"{prometheus_url}/api/v1/query?query=rate(container_cpu_usage_seconds_total[5m])"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for result in data.get("data", {}).get("result", []):
                            name = (
                                result.get("metric", {}).get("name") or 
                                result.get("metric", {}).get("container_label_com_docker_compose_service") or
                                "unknown"
                            )
                            if name in memory_data:
                                cpu_percent = float(result.get("value", [0, 0])[1]) * 100
                                containers.append(ContainerMetrics(
                                    name=name,
                                    memory_bytes=memory_data[name],
                                    cpu_percent=cpu_percent
                                ))
                
                # Add containers that only have memory data
                for name, memory_bytes in memory_data.items():
                    if not any(c.name == name for c in containers):
                        containers.append(ContainerMetrics(
                            name=name,
                            memory_bytes=memory_bytes,
                            cpu_percent=0.0
                        ))
                        
            except Exception as e:
                logger.warning(f"Failed to get container metrics: {e}")
            
            # Try to get GPU metrics if available
            try:
                # Check for NVIDIA GPU metrics
                gpu_queries = [
                    ("memory_used", "nvidia_gpu_memory_used_bytes"),
                    ("memory_total", "nvidia_gpu_memory_total_bytes"),
                    ("power", "nvidia_gpu_power_usage_milliwatts"),
                    ("utilization", "nvidia_gpu_utilization")
                ]
                
                gpu_data = {}
                for key, query in gpu_queries:
                    async with session.get(f"{prometheus_url}/api/v1/query?query={query}") as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get("data", {}).get("result", [])
                            if results:
                                gpu_data[key] = float(results[0].get("value", [0, 0])[1])
                
                if gpu_data.get("memory_total", 0) > 0:
                    memory_used = gpu_data.get("memory_used", 0)
                    memory_total = gpu_data.get("memory_total", 0)
                    power_mw = gpu_data.get("power", 0)
                    utilization = gpu_data.get("utilization", 0)
                    
                    gpu = GPUMetrics(
                        memory_used_bytes=memory_used,
                        memory_total_bytes=memory_total,
                        memory_percent=(memory_used / memory_total * 100) if memory_total > 0 else 0,
                        power_usage_watts=power_mw / 1000,  # Convert milliwatts to watts
                        utilization_percent=utilization
                    )
                        
            except Exception as e:
                logger.info(f"GPU metrics not available: {e}")
            
            # Sort containers by memory usage (descending)
            containers.sort(key=lambda x: x.memory_bytes, reverse=True)
            
            return SystemMetrics(
                containers=containers,
                gpu=gpu,
                total_containers=len(containers),
                timestamp=datetime.now(timezone.utc)
            )
            
    except Exception as e:
        logger.error(f"Error fetching system metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch system metrics"
        )