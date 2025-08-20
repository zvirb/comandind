"""
Authentication Circuit Breaker API Router
Provides endpoints for circuit breaker status and control.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from shared.utils.auth_circuit_breaker import (
    get_auth_circuit_status,
    reset_auth_circuit,
    notify_webgl_context_lost,
    notify_performance_issue
)

logger = logging.getLogger(__name__)
router = APIRouter()

class WebGLEventNotification(BaseModel):
    """WebGL context lost event notification."""
    event_type: str = "context_lost"
    timestamp: Optional[str] = None
    additional_info: Optional[str] = None

class PerformanceIssueNotification(BaseModel):
    """Performance issue notification."""
    issue_type: str
    severity: str = "medium"  # low, medium, high
    pause_duration: int = 3
    description: Optional[str] = None

@router.get("/status")
async def get_circuit_breaker_status():
    """
    Get current authentication circuit breaker status.
    
    Returns circuit state, metrics, and configuration.
    """
    try:
        status = get_auth_circuit_status()
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "circuit_breaker": status,
                "message": f"Circuit breaker is in {status['state'].upper()} state"
            }
        )
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve circuit breaker status"
        )

@router.post("/reset")
async def reset_circuit_breaker():
    """
    Manually reset the authentication circuit breaker to CLOSED state.
    
    Use this endpoint to force recovery from OPEN state if needed.
    """
    try:
        reset_auth_circuit()
        status = get_auth_circuit_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "circuit_breaker": status,
                "message": "Circuit breaker reset to CLOSED state",
                "action": "manual_reset"
            }
        )
    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not reset circuit breaker"
        )

@router.post("/notifications/webgl-context-lost")
async def notify_webgl_event(notification: WebGLEventNotification):
    """
    Notify circuit breaker of WebGL context lost events.
    
    This helps the circuit breaker pause authentication during graphics issues.
    """
    try:
        logger.info(f"Received WebGL context lost notification: {notification.dict()}")
        
        notify_webgl_context_lost()
        status = get_auth_circuit_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "WebGL context lost event processed",
                "circuit_breaker_state": status["state"],
                "is_performance_paused": status["is_performance_paused"],
                "action": "webgl_pause_activated"
            }
        )
    except Exception as e:
        logger.error(f"Error processing WebGL context lost notification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not process WebGL notification"
        )

@router.post("/notifications/performance-issue")
async def notify_performance_event(notification: PerformanceIssueNotification):
    """
    Notify circuit breaker of performance issues.
    
    This helps the circuit breaker pause authentication during system stress.
    """
    try:
        logger.info(f"Received performance issue notification: {notification.dict()}")
        
        # Adjust pause duration based on severity
        pause_duration = notification.pause_duration
        if notification.severity == "high":
            pause_duration = min(pause_duration * 2, 10)  # Cap at 10 seconds
        elif notification.severity == "low":
            pause_duration = max(pause_duration // 2, 1)  # Minimum 1 second
        
        notify_performance_issue(pause_duration)
        status = get_auth_circuit_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Performance issue processed with {pause_duration}s pause",
                "circuit_breaker_state": status["state"],
                "is_performance_paused": status["is_performance_paused"],
                "pause_duration": pause_duration,
                "severity": notification.severity,
                "action": "performance_pause_activated"
            }
        )
    except Exception as e:
        logger.error(f"Error processing performance issue notification: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not process performance notification"
        )

@router.get("/health")
async def circuit_breaker_health_check():
    """
    Health check for circuit breaker service.
    """
    try:
        status = get_auth_circuit_status()
        
        # Determine health based on circuit state and metrics
        is_healthy = True
        health_issues = []
        
        if status["state"] == "open":
            is_healthy = False
            health_issues.append("Circuit breaker is in OPEN state")
        
        if status["metrics"]["circuit_open_count"] > 5:
            health_issues.append("High number of circuit opens detected")
        
        if status["metrics"]["webgl_context_lost_events"] > 10:
            health_issues.append("Frequent WebGL context lost events")
        
        return JSONResponse(
            status_code=200 if is_healthy else 503,
            content={
                "status": "healthy" if is_healthy else "degraded",
                "service": "authentication_circuit_breaker",
                "circuit_state": status["state"],
                "is_performance_paused": status["is_performance_paused"],
                "issues": health_issues,
                "metrics_summary": {
                    "total_requests": status["metrics"]["total_requests"],
                    "success_rate": (
                        status["metrics"]["successful_requests"] / max(status["metrics"]["total_requests"], 1) * 100
                    ),
                    "blocked_requests": status["metrics"]["blocked_requests"],
                    "circuit_opens": status["metrics"]["circuit_open_count"]
                }
            }
        )
    except Exception as e:
        logger.error(f"Error in circuit breaker health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "authentication_circuit_breaker",
                "error": str(e)
            }
        )