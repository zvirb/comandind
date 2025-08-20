"""
Smart Router API
API endpoints for enhanced smart router with user approval workflow
"""

import logging
import secrets
import time
from typing import Dict, Any, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import asyncio

from api.dependencies import get_current_user, get_db, verify_csrf_token
from shared.database.models import User
from worker.services.enhanced_smart_router_service import enhanced_smart_router

logger = logging.getLogger(__name__)

# Track request patterns and errors for additional protection
_request_patterns = defaultdict(list)
_error_patterns = defaultdict(list)
_user_request_counts = defaultdict(lambda: {"count": 0, "reset_time": time.time()})

router = APIRouter()


def _track_request_pattern(user_id: str, endpoint: str) -> bool:
    """
    Track request patterns to detect flooding attempts.
    Returns True if request should be blocked.
    """
    current_time = time.time()
    
    # Clean old entries (older than 1 minute)
    cutoff_time = current_time - 60
    _request_patterns[user_id] = [req for req in _request_patterns[user_id] if req['time'] > cutoff_time]
    
    # Add current request
    _request_patterns[user_id].append({
        'time': current_time,
        'endpoint': endpoint
    })
    
    # Check for suspicious patterns
    recent_requests = [req for req in _request_patterns[user_id] if req['time'] > current_time - 30]
    
    # More than 10 requests in 30 seconds to same endpoint is suspicious
    endpoint_count = sum(1 for req in recent_requests if req['endpoint'] == endpoint)
    if endpoint_count > 10:
        logger.warning(f"Potential flooding detected for user {user_id} on endpoint {endpoint}: {endpoint_count} requests in 30s")
        return True
    
    return False


def _track_error_pattern(user_id: str, endpoint: str, error: str) -> None:
    """Track error patterns to detect cascading failures."""
    current_time = time.time()
    
    # Clean old entries (older than 5 minutes)
    cutoff_time = current_time - 300
    _error_patterns[user_id] = [err for err in _error_patterns[user_id] if err['time'] > cutoff_time]
    
    # Add current error
    _error_patterns[user_id].append({
        'time': current_time,
        'endpoint': endpoint,
        'error': error
    })
    
    # Log if error rate is high
    recent_errors = [err for err in _error_patterns[user_id] if err['time'] > current_time - 60]
    if len(recent_errors) > 5:
        logger.error(f"High error rate detected for user {user_id}: {len(recent_errors)} errors in 1 minute")


def _should_throttle_user(user_id: str) -> tuple[bool, str]:
    """
    Check if user should be throttled based on request patterns.
    Returns (should_throttle, reason).
    """
    current_time = time.time()
    user_data = _user_request_counts[user_id]
    
    # Reset counter every minute
    if current_time - user_data["reset_time"] > 60:
        user_data["count"] = 0
        user_data["reset_time"] = current_time
    
    # Increment request count
    user_data["count"] += 1
    
    # Throttle if more than 15 smart router requests per minute
    if user_data["count"] > 15:
        return True, f"Too many smart router requests: {user_data['count']} in the last minute"
    
    return False, ""


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PlanApprovalRequest(BaseModel):
    plan_id: str
    approved: bool
    modifications: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None


@router.post("/chat")
async def smart_chat(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Process chat message with enhanced smart routing and flood protection.
    """
    user_id = str(current_user.id)
    endpoint = "smart_chat"
    
    try:
        # Check for user throttling
        should_throttle, throttle_reason = _should_throttle_user(user_id)
        if should_throttle:
            logger.warning(f"Throttling user {user_id}: {throttle_reason}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": throttle_reason,
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Check for request flooding patterns
        if _track_request_pattern(user_id, endpoint):
            logger.warning(f"Blocking potential flood request from user {user_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Request pattern blocked",
                    "message": "Too many similar requests detected. Please wait before retrying.",
                    "retry_after": 30
                },
                headers={"Retry-After": "30"}
            )
        
        session_id = request.session_id or f"session_{current_user.id}_{secrets.token_urlsafe(16)}"
        
        # Add request timeout and validation
        start_time = time.time()
        
        result = await enhanced_smart_router.process_user_request(
            user_input=request.message,
            user_id=current_user.id,
            session_id=session_id,
            context=request.context
        )
        
        processing_time = time.time() - start_time
        
        # Log slow requests for monitoring
        if processing_time > 10:
            logger.warning(f"Slow smart router request for user {user_id}: {processing_time:.2f}s")
        
        return {
            "response": result.get("response", ""),
            "status": result.get("status", "completed"),
            "requires_approval": result.get("requires_approval", False),
            "plan_id": result.get("plan_id"),
            "plan": result.get("plan"),
            "session_id": session_id,
            "metadata": result.get("metadata", {}),
            "processing_time": round(processing_time, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in smart chat for user {user_id}: {e}", exc_info=True)
        
        # Track error pattern
        _track_error_pattern(user_id, endpoint, error_msg)
        
        raise HTTPException(
            status_code=500,
            detail="Failed to process chat message"
        )


@router.post("/chat/stream")
async def smart_chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process chat message with streaming updates.
    """
    
    async def generate_stream():
        """Generate streaming response."""
        session_id = request.session_id or f"session_{current_user.id}_{secrets.token_urlsafe(16)}"
        
        # Store updates to send
        updates_queue = asyncio.Queue()
        
        async def stream_callback(update):
            await updates_queue.put(update)
        
        # Start processing in background
        async def process_request():
            try:
                result = await enhanced_smart_router.process_user_request(
                    user_input=request.message,
                    user_id=current_user.id,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    context=request.context
                )
                
                # Send final result
                await updates_queue.put({
                    "type": "final_result",
                    "result": result,
                    "session_id": session_id
                })
                
            except Exception as e:
                logger.error(f"Error in streaming request: {e}")
                await updates_queue.put({
                    "type": "error",
                    "error": str(e)
                })
            finally:
                await updates_queue.put(None)  # Signal end
        
        # Start background processing
        task = asyncio.create_task(process_request())
        
        try:
            # Stream updates
            while True:
                update = await updates_queue.get()
                if update is None:  # End signal
                    break
                
                yield f"data: {json.dumps(update)}\n\n"
                
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Exception as e:
            logger.error(f"Error in stream generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/plan/approve", dependencies=[Depends(verify_csrf_token)])
async def approve_plan(
    request: PlanApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approve or reject a proposed execution plan.
    """
    try:
        if request.approved:
            result = await enhanced_smart_router.approve_plan(
                plan_id=request.plan_id,
                user_id=current_user.id,
                modifications=request.modifications
            )
        else:
            result = await enhanced_smart_router.reject_plan(
                plan_id=request.plan_id,
                user_id=current_user.id,
                feedback=request.feedback
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in plan approval: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process plan approval"
        )


@router.post("/plan/approve/stream")
async def approve_plan_stream(
    request: PlanApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve plan with streaming execution updates.
    """
    
    async def generate_stream():
        """Generate streaming response for plan execution."""
        updates_queue = asyncio.Queue()
        
        async def stream_callback(update):
            await updates_queue.put(update)
        
        async def execute_plan():
            try:
                if request.approved:
                    result = await enhanced_smart_router.approve_plan(
                        plan_id=request.plan_id,
                        user_id=current_user.id,
                        modifications=request.modifications,
                        stream_callback=stream_callback
                    )
                else:
                    result = await enhanced_smart_router.reject_plan(
                        plan_id=request.plan_id,
                        user_id=current_user.id,
                        feedback=request.feedback
                    )
                
                await updates_queue.put({
                    "type": "final_result",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Error in plan execution: {e}")
                await updates_queue.put({
                    "type": "error",
                    "error": str(e)
                })
            finally:
                await updates_queue.put(None)  # Signal end
        
        # Start execution
        task = asyncio.create_task(execute_plan())
        
        try:
            while True:
                update = await updates_queue.get()
                if update is None:
                    break
                
                yield f"data: {json.dumps(update)}\n\n"
                
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Exception as e:
            logger.error(f"Error in stream generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.get("/plan/status/{plan_id}")
async def get_plan_status(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get status of a specific plan.
    """
    try:
        if plan_id not in enhanced_smart_router.active_plans:
            raise HTTPException(
                status_code=404,
                detail="Plan not found or expired"
            )
        
        plan = enhanced_smart_router.active_plans[plan_id]
        
        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "created_at": plan.created_at.isoformat(),
            "approved_at": plan.approved_at.isoformat() if plan.approved_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
            "steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "status": step.status,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": step.error
                }
                for step in plan.steps
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get plan status"
        )


@router.get("/plans/active")
async def get_active_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all active plans for the current user.
    """
    try:
        user_plans = []
        
        for plan_id, plan in enhanced_smart_router.active_plans.items():
            # Note: In a real implementation, you'd want to store user_id in the plan
            # For now, we'll return all plans
            user_plans.append({
                "plan_id": plan_id,
                "user_input": plan.user_input,
                "status": plan.status.value,
                "created_at": plan.created_at.isoformat(),
                "step_count": len(plan.steps)
            })
        
        return {
            "active_plans": user_plans,
            "total_count": len(user_plans)
        }
        
    except Exception as e:
        logger.error(f"Error getting active plans: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get active plans"
        )


@router.get("/protection-status")
async def get_protection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current protection status and metrics for monitoring.
    Admin-level endpoint for observing protection effectiveness.
    """
    user_id = str(current_user.id)
    current_time = time.time()
    
    try:
        # Get user's request patterns
        user_requests = [req for req in _request_patterns[user_id] if req['time'] > current_time - 300]  # Last 5 minutes
        user_errors = [err for err in _error_patterns[user_id] if err['time'] > current_time - 300]
        
        # Calculate request frequency by endpoint
        endpoint_counts = {}
        for req in user_requests:
            endpoint = req['endpoint']
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
        
        # Calculate error rate
        total_requests = len(user_requests)
        total_errors = len(user_errors)
        error_rate = (total_errors / total_requests) if total_requests > 0 else 0
        
        return {
            "user_id": user_id,
            "protection_metrics": {
                "requests_last_5_minutes": total_requests,
                "errors_last_5_minutes": total_errors,
                "error_rate": round(error_rate, 3),
                "request_counts_by_endpoint": endpoint_counts,
                "current_rate_limit_status": _user_request_counts[user_id]
            },
            "recent_activity": {
                "recent_requests": [
                    {
                        "endpoint": req['endpoint'],
                        "timestamp": req['time'],
                        "time_ago_seconds": round(current_time - req['time'], 1)
                    }
                    for req in user_requests[-10:]  # Last 10 requests
                ],
                "recent_errors": [
                    {
                        "endpoint": err['endpoint'],
                        "error": err['error'][:100] + "..." if len(err['error']) > 100 else err['error'],
                        "timestamp": err['time'],
                        "time_ago_seconds": round(current_time - err['time'], 1)
                    }
                    for err in user_errors[-5:]  # Last 5 errors
                ]
            },
            "protection_status": {
                "active_protections": [
                    "TaskRateLimitMiddleware",
                    "RequestDeduplicationMiddleware", 
                    "CircuitBreakerMiddleware",
                    "SmartRouter flood detection"
                ],
                "thresholds": {
                    "smart_router_requests_per_minute": 15,
                    "flooding_detection_threshold": "10 requests in 30 seconds",
                    "task_requests_per_minute": 10,
                    "subtask_generations_per_10_minutes": 5
                }
            },
            "timestamp": current_time
        }
        
    except Exception as e:
        logger.error(f"Error getting protection status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get protection status"
        )