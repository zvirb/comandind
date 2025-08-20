"""
Celery tasks for Action Queue Service
Implements workflow tasks with proper error handling and retries
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from celery import Celery
from celery.exceptions import Retry
import redis
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client for shared state
redis_client = redis.from_url("redis://redis:6379/0", decode_responses=True)

# Celery app instance (will be configured by main service)
celery_app = Celery('action_queue_service')

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_approval_request(self, workflow_id: str):
    """Initialize approval request in the system"""
    try:
        logger.info(f"Creating approval request for workflow: {workflow_id}")
        
        # Get workflow data
        workflow_key = f"workflow:{workflow_id}"
        workflow_data = redis_client.hgetall(workflow_key)
        
        if not workflow_data:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # Update workflow status
        redis_client.hset(workflow_key, "status", "in_progress")
        redis_client.hset(workflow_key, "started_at", datetime.utcnow().isoformat())
        
        logger.info(f"Approval request created for workflow: {workflow_id}")
        return {"status": "created", "workflow_id": workflow_id}
        
    except Exception as exc:
        logger.error(f"Error creating approval request {workflow_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def notify_approver(self, workflow_id: str, approver_id: str):
    """Send notification to an approver"""
    try:
        logger.info(f"Notifying approver {approver_id} for workflow: {workflow_id}")
        
        # Get workflow data
        workflow_key = f"workflow:{workflow_id}"
        workflow_data = redis_client.hgetall(workflow_key)
        
        if not workflow_data:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # In a real implementation, this would send email, push notification, etc.
        notification_data = {
            "type": "approval_request",
            "workflow_id": workflow_id,
            "approver_id": approver_id,
            "title": workflow_data.get("title", "Approval Required"),
            "description": workflow_data.get("description", ""),
            "created_at": workflow_data.get("created_at"),
            "expires_at": workflow_data.get("expires_at"),
            "notification_sent_at": datetime.utcnow().isoformat()
        }
        
        # Store notification record
        notification_key = f"notification:{workflow_id}:{approver_id}"
        redis_client.hmset(notification_key, notification_data)
        redis_client.expire(notification_key, 86400 * 7)  # 7 days
        
        # Simulate notification sending (email, push, etc.)
        # In production, integrate with actual notification services
        time.sleep(0.1)  # Simulate network call
        
        logger.info(f"Notification sent to approver {approver_id} for workflow: {workflow_id}")
        return {
            "status": "sent",
            "workflow_id": workflow_id,
            "approver_id": approver_id,
            "sent_at": notification_data["notification_sent_at"]
        }
        
    except Exception as exc:
        logger.error(f"Error notifying approver {approver_id} for workflow {workflow_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc

@celery_app.task(bind=True, max_retries=10, default_retry_delay=30)
def wait_for_approval(self, workflow_id: str):
    """Wait for approval response with polling"""
    try:
        logger.info(f"Waiting for approval for workflow: {workflow_id}")
        
        # Get workflow data
        workflow_key = f"workflow:{workflow_id}"
        workflow_data = redis_client.hgetall(workflow_key)
        
        if not workflow_data:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # Check for responses
        responses_key = f"workflow:{workflow_id}:responses"
        responses = redis_client.hgetall(responses_key)
        
        # Check if we have enough responses
        approver_ids = workflow_data.get("approver_ids", "").split(",")
        requires_all = workflow_data.get("requires_all_approvers", "False") == "True"
        
        if requires_all:
            # Need all approvers to respond
            if len(responses) >= len(approver_ids):
                logger.info(f"All approvers responded for workflow: {workflow_id}")
                return {"status": "all_responded", "workflow_id": workflow_id}
        else:
            # Need at least one response
            if len(responses) > 0:
                logger.info(f"At least one approver responded for workflow: {workflow_id}")
                return {"status": "response_received", "workflow_id": workflow_id}
        
        # Check if workflow has expired
        expires_at = workflow_data.get("expires_at")
        if expires_at:
            expire_time = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expire_time:
                redis_client.hset(workflow_key, "status", "expired")
                logger.info(f"Workflow {workflow_id} has expired")
                return {"status": "expired", "workflow_id": workflow_id}
        
        # Continue waiting if not enough responses and not expired
        logger.info(f"Still waiting for responses for workflow: {workflow_id}")
        raise self.retry(countdown=30, exc=Exception("Still waiting for approval"))
        
    except Retry:
        raise
    except Exception as exc:
        logger.error(f"Error waiting for approval for workflow {workflow_id}: {exc}")
        raise exc

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_approval_response(self, workflow_id: str, approver_id: str, approved: bool, comments: str = ""):
    """Process individual approval response"""
    try:
        logger.info(f"Processing approval response from {approver_id} for workflow: {workflow_id}")
        
        # Get workflow data
        workflow_key = f"workflow:{workflow_id}"
        workflow_data = redis_client.hgetall(workflow_key)
        
        if not workflow_data:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # Record the response processing
        response_log_key = f"workflow:{workflow_id}:response_log"
        response_log = {
            "approver_id": approver_id,
            "approved": approved,
            "comments": comments,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        redis_client.lpush(response_log_key, json.dumps(response_log))
        redis_client.expire(response_log_key, 86400 * 7)  # 7 days
        
        # Check if this response triggers workflow completion
        responses_key = f"workflow:{workflow_id}:responses"
        all_responses = redis_client.hgetall(responses_key)
        
        approver_ids = workflow_data.get("approver_ids", "").split(",")
        requires_all = workflow_data.get("requires_all_approvers", "False") == "True"
        
        should_complete = False
        if requires_all and len(all_responses) >= len(approver_ids):
            should_complete = True
        elif not requires_all and approved:
            # First approval completes the workflow
            should_complete = True
        elif not requires_all and not approved and len(all_responses) >= len(approver_ids):
            # All rejections also complete the workflow
            should_complete = True
        
        if should_complete:
            # Trigger workflow completion
            celery_app.send_task(
                'action_queue_service.tasks.process_approval_decision',
                args=[workflow_id],
                queue='approval_workflow'
            )
        
        logger.info(f"Processed approval response from {approver_id} for workflow: {workflow_id}")
        return {
            "status": "processed",
            "workflow_id": workflow_id,
            "approver_id": approver_id,
            "should_complete": should_complete
        }
        
    except Exception as exc:
        logger.error(f"Error processing approval response for workflow {workflow_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_approval_decision(self, workflow_id: str):
    """Process final approval decision and execute actions"""
    try:
        logger.info(f"Processing final approval decision for workflow: {workflow_id}")
        
        # Get workflow data
        workflow_key = f"workflow:{workflow_id}"
        workflow_data = redis_client.hgetall(workflow_key)
        
        if not workflow_data:
            raise Exception(f"Workflow {workflow_id} not found")
        
        # Analyze all responses
        responses_key = f"workflow:{workflow_id}:responses"
        all_responses = redis_client.hgetall(responses_key)
        
        approved_count = 0
        rejected_count = 0
        
        for approver_id, response_str in all_responses.items():
            response_data = eval(response_str)  # In production, use json.loads
            if response_data.get("approved"):
                approved_count += 1
            else:
                rejected_count += 1
        
        # Determine final decision
        requires_all = workflow_data.get("requires_all_approvers", "False") == "True"
        approver_ids = workflow_data.get("approver_ids", "").split(",")
        
        if requires_all:
            final_approved = approved_count == len(approver_ids)
        else:
            final_approved = approved_count > 0
        
        # Update workflow status
        final_status = "approved" if final_approved else "rejected"
        redis_client.hset(workflow_key, "status", final_status)
        redis_client.hset(workflow_key, "completed_at", datetime.utcnow().isoformat())
        redis_client.hset(workflow_key, "final_decision", final_approved)
        redis_client.hset(workflow_key, "approved_count", approved_count)
        redis_client.hset(workflow_key, "rejected_count", rejected_count)
        
        # Execute post-approval actions
        if final_approved:
            # In a real implementation, execute the approved action
            action_result = execute_approved_action(workflow_id, workflow_data)
            redis_client.hset(workflow_key, "action_result", json.dumps(action_result))
        
        # Send completion notifications
        send_completion_notifications(workflow_id, final_approved, workflow_data)
        
        logger.info(f"Completed approval workflow {workflow_id} with decision: {final_status}")
        return {
            "status": "completed",
            "workflow_id": workflow_id,
            "final_decision": final_approved,
            "approved_count": approved_count,
            "rejected_count": rejected_count
        }
        
    except Exception as exc:
        logger.error(f"Error processing approval decision for workflow {workflow_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=exc)
        raise exc

def execute_approved_action(workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the action that was approved"""
    try:
        action_type = workflow_data.get("metadata", {}).get("action_type", "generic")
        
        logger.info(f"Executing approved action '{action_type}' for workflow: {workflow_id}")
        
        # Simulate action execution based on type
        if action_type == "user_access":
            return {"action": "user_access_granted", "executed_at": datetime.utcnow().isoformat()}
        elif action_type == "budget_approval":
            return {"action": "budget_allocated", "executed_at": datetime.utcnow().isoformat()}
        else:
            return {"action": "generic_action_executed", "executed_at": datetime.utcnow().isoformat()}
            
    except Exception as e:
        logger.error(f"Error executing approved action for workflow {workflow_id}: {e}")
        return {"action": "execution_failed", "error": str(e)}

def send_completion_notifications(workflow_id: str, approved: bool, workflow_data: Dict[str, Any]):
    """Send notifications about workflow completion"""
    try:
        logger.info(f"Sending completion notifications for workflow: {workflow_id}")
        
        # Notify requester
        requester_id = workflow_data.get("requester_id")
        if requester_id:
            notification_data = {
                "type": "workflow_completed",
                "workflow_id": workflow_id,
                "recipient_id": requester_id,
                "approved": approved,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Store notification (in production, send actual notification)
            notification_key = f"notification:completion:{workflow_id}:{requester_id}"
            redis_client.hmset(notification_key, notification_data)
            redis_client.expire(notification_key, 86400 * 7)  # 7 days
        
        logger.info(f"Completion notifications sent for workflow: {workflow_id}")
        
    except Exception as e:
        logger.error(f"Error sending completion notifications for workflow {workflow_id}: {e}")

# Dead Letter Queue handlers
@celery_app.task(bind=True)
def handle_failed_task(self, task_id: str, task_name: str, error_message: str):
    """Handle tasks that have failed all retries"""
    logger.error(f"Task {task_name} ({task_id}) has failed permanently: {error_message}")
    
    # Store failed task information for manual review
    failed_task_key = f"failed_task:{task_id}"
    failed_task_data = {
        "task_id": task_id,
        "task_name": task_name,
        "error_message": error_message,
        "failed_at": datetime.utcnow().isoformat(),
        "requires_manual_review": True
    }
    
    redis_client.hmset(failed_task_key, failed_task_data)
    redis_client.expire(failed_task_key, 86400 * 30)  # 30 days
    
    # In production, send alert to operations team
    logger.critical(f"MANUAL REVIEW REQUIRED: Task {task_id} failed permanently")