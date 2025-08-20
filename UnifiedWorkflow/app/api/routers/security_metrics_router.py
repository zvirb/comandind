"""Security metrics API router for Prometheus integration and monitoring endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.services.security_metrics_service import security_metrics_service
from shared.services.automated_security_response_service import automated_security_response_service
from shared.services.security_event_processor import security_event_processor
from shared.services.query_performance_service import query_performance_service, get_performance_summary, get_optimization_recommendations
from api.dependencies import get_current_user
from shared.database.models import User
from shared.utils.database_setup import get_async_session, get_database_stats
from shared.utils.error_handler import error_handler, create_error_context
from api.middleware.error_middleware import monitor_performance

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/security",
    tags=["Security Metrics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint for security monitoring.
    
    Returns security metrics in Prometheus format for scraping.
    """
    try:
        # Generate Prometheus metrics
        return generate_latest()
    except Exception as e:
        logger.error(f"Error generating security metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health")
async def get_security_monitoring_health():
    """
    Get security monitoring system health status.
    
    Returns health information for all security monitoring components.
    """
    try:
        health_status = {
            "security_metrics_service": {
                "status": "running" if security_metrics_service.running else "stopped",
                "monitoring_tasks": len(security_metrics_service.monitoring_tasks)
            },
            "security_event_processor": {
                "status": "running" if security_event_processor.running else "stopped",
                "processing_tasks": len(security_event_processor.processing_tasks),
                "regular_queue_size": security_event_processor.event_queue.qsize(),
                "high_priority_queue_size": security_event_processor.high_priority_queue.qsize()
            },
            "automated_response_service": {
                "status": "running" if automated_security_response_service.running else "stopped",
                "response_tasks": len(automated_security_response_service.response_tasks),
                "active_ip_blocks": len(automated_security_response_service.active_ip_blocks),
                "active_user_suspensions": len(automated_security_response_service.active_user_suspensions)
            }
        }
        
        # Determine overall health
        all_running = all(
            component["status"] == "running" 
            for component in health_status.values()
        )
        
        overall_status = "healthy" if all_running else "degraded"
        
        return {
            "overall_status": overall_status,
            "timestamp": security_metrics_service.metrics.security_monitoring_status._value.get_sample_value(),
            "components": health_status
        }
        
    except Exception as e:
        logger.error(f"Error getting security health status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/summary")
async def get_security_metrics_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Get security metrics summary.
    
    Returns a comprehensive summary of security metrics for dashboard display.
    Requires authentication.
    """
    try:
        summary = await security_metrics_service.get_security_metrics_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting security metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get metrics summary")


@router.get("/active-blocks")
async def get_active_security_blocks(
    current_user: User = Depends(get_current_user)
):
    """
    Get currently active security blocks and restrictions.
    
    Returns information about active IP blocks, user suspensions, and other security measures.
    Requires authentication with admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        active_blocks = {
            "ip_blocks": [
                {
                    "ip_address": ip,
                    "reason": action.reason,
                    "created_at": action.created_at.isoformat(),
                    "expiration": action.expiration.isoformat() if action.expiration else None,
                    "severity": action.severity.value
                }
                for ip, action in automated_security_response_service.active_ip_blocks.items()
            ],
            "user_suspensions": [
                {
                    "user_id": user_id,
                    "reason": action.reason,
                    "created_at": action.created_at.isoformat(),
                    "expiration": action.expiration.isoformat() if action.expiration else None,
                    "severity": action.severity.value
                }
                for user_id, action in automated_security_response_service.active_user_suspensions.items()
            ],
            "rate_limits": list(automated_security_response_service.active_rate_limits.keys())
        }
        
        return active_blocks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active security blocks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get active blocks")


@router.post("/manual-action")
async def create_manual_security_action(
    action_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Create a manual security action.
    
    Allows administrators to manually create security actions like IP blocks or user suspensions.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        from shared.services.automated_security_response_service import (
            SecurityAction, 
            SecurityActionType, 
            SecurityResponseSeverity
        )
        from datetime import datetime, timedelta
        
        # Validate required fields
        required_fields = ["action_type", "target", "reason"]
        for field in required_fields:
            if field not in action_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create security action
        action = SecurityAction(
            action_type=SecurityActionType(action_data["action_type"]),
            severity=SecurityResponseSeverity(action_data.get("severity", "MEDIUM")),
            target=action_data["target"],
            reason=action_data["reason"],
            evidence=action_data.get("evidence", {"manual_action": True}),
            expiration=datetime.utcnow() + timedelta(hours=action_data.get("duration_hours", 24)),
            auto_created=False
        )
        
        # Execute the action
        success = await automated_security_response_service.execute_security_action(
            action, 
            user_id=current_user.id
        )
        
        if success:
            return {
                "success": True,
                "message": f"Security action {action.action_type.value} created successfully",
                "action": {
                    "type": action.action_type.value,
                    "target": action.target,
                    "reason": action.reason,
                    "expiration": action.expiration.isoformat() if action.expiration else None
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to execute security action")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid action data: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating manual security action: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create security action")


@router.delete("/action/{action_type}/{target}")
async def revoke_security_action(
    action_type: str,
    target: str,
    current_user: User = Depends(get_current_user)
):
    """
    Revoke an active security action.
    
    Allows administrators to manually revoke security actions like IP blocks or user suspensions.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        revoked = False
        
        # Handle different action types
        if action_type == "ip_block" and target in automated_security_response_service.active_ip_blocks:
            del automated_security_response_service.active_ip_blocks[target]
            
            # Remove from Redis if available
            if automated_security_response_service.redis_client:
                await automated_security_response_service.redis_client.delete(f"ip_block:{target}")
            
            revoked = True
            
        elif action_type == "user_suspend":
            try:
                user_id = int(target)
                if user_id in automated_security_response_service.active_user_suspensions:
                    del automated_security_response_service.active_user_suspensions[user_id]
                    
                    # Remove from Redis if available
                    if automated_security_response_service.redis_client:
                        await automated_security_response_service.redis_client.delete(f"user_suspend:{user_id}")
                    
                    revoked = True
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        if revoked:
            return {
                "success": True,
                "message": f"Security action {action_type} for {target} revoked successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Security action not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking security action: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to revoke security action")


@router.post("/alerts/webhook")
async def security_alert_webhook(
    request: Request,
    alert_data: Dict[str, Any]
):
    """
    Webhook endpoint for external security alerts.
    
    Receives alerts from AlertManager or other security tools and processes them
    through the security event system.
    """
    try:
        # Log the incoming alert
        logger.info(f"Received security alert webhook: {alert_data}")
        
        # Process alerts from AlertManager format
        if "alerts" in alert_data:
            for alert in alert_data["alerts"]:
                # Extract alert information
                alert_name = alert.get("labels", {}).get("alertname", "unknown")
                severity = alert.get("labels", {}).get("severity", "medium")
                status = alert.get("status", "firing")
                
                if status == "firing":
                    # Create security event for the alert
                    from shared.services.security_event_processor import (
                        SecurityEvent, 
                        SecurityEventType, 
                        SecurityEventSeverity
                    )
                    from datetime import datetime
                    
                    # Map alert severity to security event severity
                    severity_mapping = {
                        "critical": SecurityEventSeverity.CRITICAL,
                        "high": SecurityEventSeverity.HIGH,
                        "warning": SecurityEventSeverity.MEDIUM,
                        "info": SecurityEventSeverity.LOW
                    }
                    
                    event_severity = severity_mapping.get(severity.lower(), SecurityEventSeverity.MEDIUM)
                    
                    security_event = SecurityEvent(
                        event_type=SecurityEventType.THREAT_DETECTION,
                        severity=event_severity,
                        timestamp=datetime.utcnow(),
                        service_name="alertmanager",
                        details={
                            "alert_name": alert_name,
                            "alert_data": alert,
                            "source": "webhook"
                        }
                    )
                    
                    # Emit the security event
                    await security_event_processor.emit_event(security_event)
        
        return {"status": "received", "processed_alerts": len(alert_data.get("alerts", []))}
        
    except Exception as e:
        logger.error(f"Error processing security alert webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process alert webhook")


@router.get("/check-ip/{ip_address}")
async def check_ip_status(
    ip_address: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if an IP address is blocked or restricted.
    
    Returns the security status of a specific IP address.
    Requires authentication.
    """
    try:
        is_blocked = await automated_security_response_service.check_ip_blocked(ip_address)
        
        block_info = None
        if is_blocked and ip_address in automated_security_response_service.active_ip_blocks:
            action = automated_security_response_service.active_ip_blocks[ip_address]
            block_info = {
                "reason": action.reason,
                "created_at": action.created_at.isoformat(),
                "expiration": action.expiration.isoformat() if action.expiration else None,
                "severity": action.severity.value
            }
        
        return {
            "ip_address": ip_address,
            "is_blocked": is_blocked,
            "block_info": block_info
        }
        
    except Exception as e:
        logger.error(f"Error checking IP status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check IP status")


@router.get("/check-user/{user_id}")
async def check_user_status(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a user is suspended or restricted.
    
    Returns the security status of a specific user.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges or is checking their own status
        if not (hasattr(current_user, 'is_admin') and current_user.is_admin) and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Admin privileges required or can only check own status")
        
        is_suspended = await automated_security_response_service.check_user_suspended(user_id)
        
        suspension_info = None
        if is_suspended and user_id in automated_security_response_service.active_user_suspensions:
            action = automated_security_response_service.active_user_suspensions[user_id]
            suspension_info = {
                "reason": action.reason,
                "created_at": action.created_at.isoformat(),
                "expiration": action.expiration.isoformat() if action.expiration else None,
                "severity": action.severity.value
            }
        
        return {
            "user_id": user_id,
            "is_suspended": is_suspended,
            "suspension_info": suspension_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking user status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check user status")


# === QUERY PERFORMANCE MONITORING ENDPOINTS ===

@router.get("/query-performance/summary")
@monitor_performance("get_query_performance_summary")
async def get_query_performance_summary(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get query performance summary and database statistics.
    
    Returns comprehensive performance metrics including slow queries,
    connection pool statistics, and optimization recommendations.
    Requires authentication.
    """
    try:
        # Check if user has admin privileges for detailed metrics
        is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
        
        # Get performance summary
        performance_summary = await get_performance_summary()
        
        # Get database connection pool stats
        db_stats = get_database_stats()
        
        # Get basic optimization recommendations for non-admin users
        # Full recommendations only for admins
        recommendations = await get_optimization_recommendations()
        if not is_admin:
            # Filter recommendations to only show high-priority ones for regular users
            recommendations = [r for r in recommendations if r.get("priority") == "HIGH"]
        
        result = {
            "performance_summary": performance_summary,
            "database_pool_stats": db_stats,
            "optimization_recommendations": recommendations,
            "user_access_level": "admin" if is_admin else "user"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting query performance summary: {str(e)}")
        context = create_error_context(request, user_id=current_user.id)
        raise error_handler.internal_server_error(
            message="Failed to get query performance summary",
            details={"error": str(e)},
            context=context
        )


@router.get("/query-performance/details/{query_hash}")
@monitor_performance("get_query_details")
async def get_query_performance_details(
    query_hash: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed performance metrics for a specific query.
    
    Returns detailed execution statistics, timing data, and recent
    slow executions for the specified query hash.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
            context = create_error_context(request, user_id=current_user.id)
            raise error_handler.authorization_error(
                message="Admin privileges required for detailed query metrics",
                context=context
            )
        
        # Get detailed query metrics
        query_details = await query_performance_service.get_query_details(query_hash)
        
        if not query_details:
            context = create_error_context(request, user_id=current_user.id)
            raise error_handler.not_found_error(
                resource="Query",
                resource_id=query_hash,
                context=context
            )
        
        return {
            "query_hash": query_hash,
            "query_details": query_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting query details: {str(e)}")
        context = create_error_context(request, user_id=current_user.id)
        raise error_handler.internal_server_error(
            message="Failed to get query details",
            details={"query_hash": query_hash, "error": str(e)},
            context=context
        )


@router.get("/query-performance/recommendations")
@monitor_performance("get_query_optimization_recommendations")
async def get_query_optimization_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get database query optimization recommendations.
    
    Returns AI-generated recommendations for improving query performance
    based on collected metrics and common optimization patterns.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
            context = create_error_context(request, user_id=current_user.id)
            raise error_handler.authorization_error(
                message="Admin privileges required for optimization recommendations",
                context=context
            )
        
        # Get optimization recommendations
        recommendations = await get_optimization_recommendations()
        
        return {
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "high_priority_count": len([r for r in recommendations if r.get("priority") == "HIGH"]),
            "generated_at": query_performance_service._metrics and datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {str(e)}")
        context = create_error_context(request, user_id=current_user.id)
        raise error_handler.internal_server_error(
            message="Failed to get optimization recommendations",
            details={"error": str(e)},
            context=context
        )


@router.post("/query-performance/clear-metrics")
@monitor_performance("clear_query_metrics")
async def clear_query_performance_metrics(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Clear all collected query performance metrics.
    
    Resets all performance data - useful for testing or after
    implementing optimizations to get fresh baseline metrics.
    Requires admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not (hasattr(current_user, 'is_admin') and current_user.is_admin):
            context = create_error_context(request, user_id=current_user.id)
            raise error_handler.authorization_error(
                message="Admin privileges required to clear metrics",
                context=context
            )
        
        # Clear all metrics
        await query_performance_service.clear_metrics()
        
        logger.info(f"Query performance metrics cleared by admin user {current_user.id}")
        
        return {
            "success": True,
            "message": "Query performance metrics cleared successfully",
            "cleared_at": datetime.utcnow().isoformat(),
            "cleared_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing query metrics: {str(e)}")
        context = create_error_context(request, user_id=current_user.id)
        raise error_handler.internal_server_error(
            message="Failed to clear query metrics",
            details={"error": str(e)},
            context=context
        )


@router.get("/database-stats")
@monitor_performance("get_database_statistics")
async def get_database_statistics(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get current database connection pool statistics.
    
    Returns real-time information about database connection usage,
    pool configuration, and connection health.
    Requires authentication.
    """
    try:
        # Get database statistics
        db_stats = get_database_stats()
        
        # Add timestamp and additional metadata
        enhanced_stats = {
            "database_statistics": db_stats,
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_enabled": query_performance_service.monitoring_enabled,
            "total_queries_monitored": query_performance_service.total_queries
        }
        
        return enhanced_stats
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {str(e)}")
        context = create_error_context(request, user_id=current_user.id)
        raise error_handler.internal_server_error(
            message="Failed to get database statistics",
            details={"error": str(e)},
            context=context
        )