"""
Action Queue Service - Celery with RabbitMQ
Manages stateful, asynchronous user approval workflows with reliability and traceability.
Implements complex workflow orchestration using Celery Canvas primitives.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from celery import Celery, group, chain, chord
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis
import uvicorn
from pydantic import BaseModel
from enum import Enum

from app.shared.services.jwt_token_adapter import verify_jwt_token
from app.shared.services.metrics_exporter import MetricsExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@rabbitmq:5672//")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Initialize Celery app
celery_app = Celery(
    "action_queue_service",
    broker=RABBITMQ_URL,
    backend=REDIS_URL,
    include=['app.action_queue_service.tasks']
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Reliability settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Dead Letter Queue configuration
    task_routes={
        'action_queue_service.tasks.*': {
            'queue': 'approval_workflow',
            'routing_key': 'approval_workflow',
        }
    },
    
    # Result backend settings
    result_expires=3600,
    result_persistent=True,
)

# FastAPI app
app = FastAPI(
    title="Action Queue Service",
    description="Asynchronous workflow management with Celery and RabbitMQ",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client for state tracking
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
metrics = MetricsExporter("action_queue_service")

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class WorkflowStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ApprovalRequest(BaseModel):
    title: str
    description: str
    requester_id: str
    approver_ids: List[str]
    metadata: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None
    requires_all_approvers: bool = False

class WorkflowRequest(BaseModel):
    workflow_type: str
    parameters: Dict[str, Any] = {}
    priority: int = 5  # 1-10, 10 being highest
    scheduled_at: Optional[datetime] = None

class ActionQueueService:
    """Service for managing complex approval workflows"""
    
    def __init__(self):
        self.redis = redis_client
        
    async def create_approval_workflow(self, request: ApprovalRequest, user_id: str) -> str:
        """Create a new approval workflow using Celery Canvas"""
        try:
            workflow_id = f"approval_{int(time.time())}_{user_id}"
            
            # Store workflow metadata
            workflow_data = {
                "id": workflow_id,
                "title": request.title,
                "description": request.description,
                "requester_id": request.requester_id,
                "approver_ids": request.approver_ids,
                "status": WorkflowStatus.CREATED,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": request.expires_at.isoformat() if request.expires_at else None,
                "requires_all_approvers": request.requires_all_approvers,
                "metadata": request.metadata
            }
            
            await self._store_workflow(workflow_id, workflow_data)
            
            # Create Celery workflow using Canvas primitives
            if request.requires_all_approvers:
                # Use chord: notify all approvers, then process when all respond
                notification_tasks = group([
                    celery_app.send_task(
                        'action_queue_service.tasks.notify_approver',
                        args=[workflow_id, approver_id],
                        queue='approval_workflow'
                    ) for approver_id in request.approver_ids
                ])
                
                workflow = chord(notification_tasks)(
                    celery_app.send_task(
                        'action_queue_service.tasks.process_approval_decision',
                        args=[workflow_id],
                        queue='approval_workflow'
                    )
                )
            else:
                # Use chain: notify approvers, wait for first approval
                workflow = chain(
                    celery_app.send_task(
                        'action_queue_service.tasks.create_approval_request',
                        args=[workflow_id],
                        queue='approval_workflow'
                    ),
                    group([
                        celery_app.send_task(
                            'action_queue_service.tasks.notify_approver',
                            args=[workflow_id, approver_id],
                            queue='approval_workflow'
                        ) for approver_id in request.approver_ids
                    ]),
                    celery_app.send_task(
                        'action_queue_service.tasks.wait_for_approval',
                        args=[workflow_id],
                        queue='approval_workflow'
                    ),
                    celery_app.send_task(
                        'action_queue_service.tasks.process_approval_decision',
                        args=[workflow_id],
                        queue='approval_workflow'
                    )
                )
            
            # Execute workflow
            result = workflow.apply_async()
            
            # Update workflow with task ID
            workflow_data["celery_task_id"] = result.id
            workflow_data["status"] = WorkflowStatus.IN_PROGRESS
            await self._store_workflow(workflow_id, workflow_data)
            
            # Record metrics
            await metrics.record_counter("workflows_created", 1, {"type": "approval"})
            
            logger.info(f"Created approval workflow: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            logger.error(f"Error creating approval workflow: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")
    
    async def submit_approval_response(self, workflow_id: str, approver_id: str, 
                                     approved: bool, comments: str = "") -> Dict[str, Any]:
        """Submit an approval response"""
        try:
            # Get workflow data
            workflow_data = await self._get_workflow(workflow_id)
            if not workflow_data:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            # Verify approver authorization
            if approver_id not in workflow_data.get("approver_ids", []):
                raise HTTPException(status_code=403, detail="Not authorized to approve this request")
            
            # Check if already responded
            responses_key = f"workflow:{workflow_id}:responses"
            existing_response = self.redis.hget(responses_key, approver_id)
            if existing_response:
                raise HTTPException(status_code=400, detail="Already responded to this request")
            
            # Store approval response
            response_data = {
                "approver_id": approver_id,
                "approved": approved,
                "comments": comments,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis.hset(responses_key, approver_id, str(response_data))
            self.redis.expire(responses_key, 86400)  # 24 hours
            
            # Trigger workflow continuation
            celery_app.send_task(
                'action_queue_service.tasks.process_approval_response',
                args=[workflow_id, approver_id, approved, comments],
                queue='approval_workflow'
            )
            
            # Record metrics
            await metrics.record_counter("approval_responses", 1, {
                "approved": str(approved),
                "workflow_type": "approval"
            })
            
            return {
                "workflow_id": workflow_id,
                "approver_id": approver_id,
                "status": "received",
                "timestamp": response_data["timestamp"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting approval response: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        try:
            workflow_data = await self._get_workflow(workflow_id)
            if not workflow_data:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            # Get Celery task status if available
            task_status = None
            if "celery_task_id" in workflow_data:
                result = AsyncResult(workflow_data["celery_task_id"], app=celery_app)
                task_status = {
                    "task_id": result.id,
                    "state": result.state,
                    "info": result.info
                }
            
            # Get approval responses
            responses_key = f"workflow:{workflow_id}:responses"
            responses = {}
            for approver_id in workflow_data.get("approver_ids", []):
                response = self.redis.hget(responses_key, approver_id)
                if response:
                    responses[approver_id] = eval(response)  # In production, use json.loads
            
            return {
                "workflow": workflow_data,
                "task_status": task_status,
                "responses": responses,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
    
    async def _store_workflow(self, workflow_id: str, data: Dict[str, Any]):
        """Store workflow data in Redis"""
        key = f"workflow:{workflow_id}"
        self.redis.hmset(key, data)
        self.redis.expire(key, 86400 * 7)  # 7 days
    
    async def _get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow data from Redis"""
        key = f"workflow:{workflow_id}"
        data = self.redis.hgetall(key)
        return data if data else None

# Global service instance
action_queue_service = ActionQueueService()

async def get_current_user(token: str = Depends(verify_jwt_token)) -> Dict[str, Any]:
    """Get current authenticated user"""
    return token

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Celery worker availability
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active_workers = len(stats) if stats else 0
        
        # Check RabbitMQ connection
        try:
            celery_app.broker_connection().ensure_connection(max_retries=3)
            broker_status = "connected"
        except Exception:
            broker_status = "disconnected"
        
        # Check Redis connection
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
        
        return {
            "status": "healthy",
            "service": "action-queue",
            "celery": {
                "active_workers": active_workers,
                "broker_status": broker_status
            },
            "redis": {
                "status": redis_status
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/workflows/approval")
async def create_approval_workflow(
    request: ApprovalRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new approval workflow"""
    workflow_id = await action_queue_service.create_approval_workflow(request, user.get("user_id"))
    return {"workflow_id": workflow_id, "status": "created"}

@app.post("/workflows/{workflow_id}/approve")
async def submit_approval(
    workflow_id: str,
    approved: bool,
    comments: str = "",
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Submit an approval response"""
    result = await action_queue_service.submit_approval_response(
        workflow_id, user.get("user_id"), approved, comments
    )
    return result

@app.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get workflow status"""
    return await action_queue_service.get_workflow_status(workflow_id)

@app.get("/workflows/my-pending")
async def get_pending_approvals(user: Dict[str, Any] = Depends(get_current_user)):
    """Get pending approvals for current user"""
    try:
        user_id = user.get("user_id")
        pending_workflows = []
        
        # Search for workflows where user is an approver
        # In production, use a proper indexing strategy
        for key in redis_client.scan_iter(match="workflow:*"):
            if ":responses" not in key:
                workflow_data = redis_client.hgetall(key)
                approver_ids = workflow_data.get("approver_ids", "").split(",")
                if user_id in approver_ids and workflow_data.get("status") == WorkflowStatus.IN_PROGRESS:
                    # Check if user has already responded
                    workflow_id = key.split(":")[1]
                    responses_key = f"workflow:{workflow_id}:responses"
                    if not redis_client.hexists(responses_key, user_id):
                        pending_workflows.append({
                            "workflow_id": workflow_id,
                            "title": workflow_data.get("title"),
                            "description": workflow_data.get("description"),
                            "created_at": workflow_data.get("created_at"),
                            "expires_at": workflow_data.get("expires_at")
                        })
        
        return {"pending_workflows": pending_workflows}
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending approvals: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        reload=False,
        log_level="info"
    )