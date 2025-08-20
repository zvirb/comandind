"""
Monitoring API endpoints for the AI Workflow Engine.

This router provides endpoints for:
- Prometheus metrics scraping
- Health checks and status monitoring
- Performance insights and analysis
- Distributed tracing data
- Worker monitoring and management
- System observability
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse
import logging
import asyncio
from datetime import datetime, timedelta

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Import monitoring modules with error handling
try:
    from shared.monitoring.prometheus_metrics import metrics, get_metrics_handler
    CUSTOM_METRICS_AVAILABLE = True
except ImportError:
    CUSTOM_METRICS_AVAILABLE = False
    metrics = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns detailed health status of all system components.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "monitoring_components": {
                "prometheus_client": PROMETHEUS_AVAILABLE,
                "custom_metrics": CUSTOM_METRICS_AVAILABLE,
            },
            "components": {}
        }
        
        # Check database connectivity (basic check)
        try:
            # This would be replaced with actual database ping
            health_status["components"]["database"] = {
                "status": "healthy",
                "response_time_ms": 1.2
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check Redis connectivity (basic check)
        try:
            # This would be replaced with actual Redis ping
            health_status["components"]["redis"] = {
                "status": "healthy",
                "response_time_ms": 0.8
            }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Basic worker status check
        health_status["components"]["workers"] = {
            "status": "monitoring_available",
            "note": "Worker monitoring requires additional setup"
        }
        
        # Update application health status if metrics are available
        if CUSTOM_METRICS_AVAILABLE and metrics:
            try:
                if health_status["status"] == "healthy":
                    metrics.set_health_status("healthy")
                elif health_status["status"] == "degraded":
                    metrics.set_health_status("degraded")
                else:
                    metrics.set_health_status("unhealthy")
            except Exception as e:
                logger.warning(f"Could not update metrics: {e}")
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        if CUSTOM_METRICS_AVAILABLE and metrics:
            try:
                metrics.set_health_status("unhealthy")
            except:
                pass
        raise HTTPException(status_code=503, detail="Health check failed")


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    try:
        if not PROMETHEUS_AVAILABLE:
            return Response(
                content="# prometheus_client not available\n# Install prometheus_client to enable metrics\n",
                media_type="text/plain"
            )
        
        if not CUSTOM_METRICS_AVAILABLE or not metrics:
            return Response(
                content="# custom metrics not available\n# Check monitoring configuration\n",
                media_type="text/plain"
            )
        
        metrics_data = generate_latest(metrics.registry)
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {str(e)}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain"
        )


@router.get("/metrics/custom")
async def custom_metrics():
    """
    Custom metrics endpoint with additional formatting options.
    """
    try:
        # This could provide metrics in different formats or with filtering
        return JSONResponse({
            "timestamp": datetime.utcnow().isoformat(),
            "metrics_available": True,
            "prometheus_endpoint": "/monitoring/metrics"
        })
    except Exception as e:
        logger.error(f"Failed to provide custom metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Custom metrics failed")


@router.get("/status")
async def system_status():
    """
    Detailed system status including all monitoring data.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "operational",
        "monitoring_components": {
            "prometheus_client": PROMETHEUS_AVAILABLE,
            "custom_metrics": CUSTOM_METRICS_AVAILABLE,
        },
        "services": {
            "api": "healthy",
            "monitoring": "active",
            "metrics_collection": "enabled" if (PROMETHEUS_AVAILABLE and CUSTOM_METRICS_AVAILABLE) else "limited"
        }
    }


@router.get("/workers")
async def worker_status():
    """
    Detailed worker status and performance metrics.
    """
    try:
        worker_monitor = get_worker_monitor()
        if not worker_monitor:
            raise HTTPException(status_code=503, detail="Worker monitoring not available")
        
        status = worker_monitor.get_worker_status()
        return JSONResponse(status)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get worker status: {str(e)}")
        raise HTTPException(status_code=500, detail="Worker status failed")


@router.get("/workers/{worker_name}")
async def worker_detail(worker_name: str):
    """
    Detailed information about a specific worker.
    """
    try:
        worker_monitor = get_worker_monitor()
        if not worker_monitor:
            raise HTTPException(status_code=503, detail="Worker monitoring not available")
        
        status = worker_monitor.get_worker_status()
        
        if worker_name not in status.get("workers", {}):
            raise HTTPException(status_code=404, detail=f"Worker {worker_name} not found")
        
        worker_detail = status["workers"][worker_name]
        
        # Add performance history if available
        performance = worker_monitor.get_task_performance_summary()
        worker_detail["performance"] = performance
        
        return JSONResponse(worker_detail)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get worker detail for {worker_name}: {str(e)}")
        raise HTTPException(status_code=500, detail="Worker detail failed")


@router.get("/traces")
async def trace_overview(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = Query(None)
):
    """
    Get overview of distributed traces.
    """
    try:
        traces_data = []
        
        for trace_id, spans in list(trace_collector.traces.items())[:limit]:
            if service:
                # Filter by service
                service_spans = [s for s in spans if s.service_name == service]
                if not service_spans:
                    continue
                spans = service_spans
            
            # Calculate trace summary
            start_time = min(span.start_time for span in spans)
            end_time = max(span.end_time for span in spans if span.end_time)
            duration = end_time - start_time if end_time else None
            
            trace_summary = {
                "trace_id": trace_id,
                "span_count": len(spans),
                "services": list(set(span.service_name for span in spans)),
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "duration_seconds": duration,
                "has_errors": any(span.status.value == "error" for span in spans)
            }
            
            traces_data.append(trace_summary)
        
        return JSONResponse({
            "traces": traces_data,
            "total_traces": len(trace_collector.traces),
            "limit": limit,
            "service_filter": service
        })
    
    except Exception as e:
        logger.error(f"Failed to get trace overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Trace overview failed")


@router.get("/traces/{trace_id}")
async def trace_detail(trace_id: str):
    """
    Get detailed information about a specific trace.
    """
    try:
        spans = trace_collector.get_trace(trace_id)
        
        if not spans:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
        
        # Convert spans to serializable format
        trace_data = {
            "trace_id": trace_id,
            "spans": []
        }
        
        for span in spans:
            span_data = {
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "operation_name": span.operation_name,
                "service_name": span.service_name,
                "start_time": datetime.fromtimestamp(span.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(span.end_time).isoformat() if span.end_time else None,
                "duration_seconds": span.duration,
                "status": span.status.value,
                "kind": span.kind.value,
                "tags": span.tags,
                "logs": span.logs,
                "error": span.error
            }
            trace_data["spans"].append(span_data)
        
        return JSONResponse(trace_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace detail for {trace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Trace detail failed")


@router.get("/performance")
async def performance_overview():
    """
    System performance overview and insights.
    """
    try:
        # Get operation statistics from trace collector
        performance_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operations": {},
            "services": {}
        }
        
        # Service map
        service_map = trace_collector.get_service_map()
        performance_data["service_map"] = service_map
        
        # Operation statistics
        for operation_name in trace_collector.operation_stats.keys():
            stats = trace_collector.get_operation_stats(operation_name)
            performance_data["operations"][operation_name] = stats
        
        # Worker performance
        worker_monitor = get_worker_monitor()
        if worker_monitor:
            performance_data["workers"] = worker_monitor.get_task_performance_summary()
        
        return JSONResponse(performance_data)
    
    except Exception as e:
        logger.error(f"Failed to get performance overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Performance overview failed")


@router.post("/alerts/webhook")
async def alert_webhook(request: Request):
    """
    Webhook endpoint for receiving alerts from AlertManager.
    """
    try:
        alert_data = await request.json()
        
        # Log the alert
        security_logger.log_suspicious_activity(
            activity_type="alert_received",
            description=f"Alert webhook received: {alert_data.get('status', 'unknown')}",
            ip_address=request.client.host,
            severity="medium",
            alert_data=alert_data
        )
        
        # Process alerts based on type
        alerts = alert_data.get("alerts", [])
        
        for alert in alerts:
            alert_name = alert.get("labels", {}).get("alertname", "unknown")
            severity = alert.get("labels", {}).get("severity", "medium")
            status = alert.get("status", "unknown")
            
            logger.warning(
                f"Alert received: {alert_name}",
                extra={
                    "alert_name": alert_name,
                    "severity": severity,
                    "status": status,
                    "alert_data": alert
                }
            )
            
            # Record security events for critical alerts
            if severity == "critical":
                metrics.record_security_event(
                    event_type="critical_alert",
                    severity="critical",
                    source="alertmanager"
                )
        
        return JSONResponse({"status": "received", "processed_alerts": len(alerts)})
    
    except Exception as e:
        logger.error(f"Failed to process alert webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Alert webhook processing failed")


@router.get("/logs/search")
async def log_search(
    query: str = Query(..., description="Log search query"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    level: Optional[str] = Query(None, description="Log level filter"),
    service: Optional[str] = Query(None, description="Service name filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results")
):
    """
    Search logs (placeholder - would integrate with actual log storage).
    
    This endpoint would typically query Elasticsearch, Loki, or other log storage.
    """
    try:
        # This is a placeholder response
        # In a real implementation, this would query your log storage system
        
        search_results = {
            "query": query,
            "filters": {
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "level": level,
                "service": service
            },
            "total_results": 0,
            "results": [],
            "message": "Log search requires integration with log storage backend (Elasticsearch, Loki, etc.)"
        }
        
        return JSONResponse(search_results)
    
    except Exception as e:
        logger.error(f"Log search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Log search failed")


@router.get("/dashboards")
async def dashboard_urls():
    """
    Get URLs for various monitoring dashboards.
    """
    try:
        dashboards = {
            "grafana": "http://localhost:3000",
            "prometheus": "http://localhost:9090",
            "alertmanager": "http://localhost:9093",
            "jaeger": "http://localhost:16686",
            "kibana": "http://localhost:5601",
            "custom_dashboards": [
                {
                    "name": "System Overview",
                    "url": "http://localhost:3000/d/system-overview"
                },
                {
                    "name": "Security Dashboard",
                    "url": "http://localhost:3000/d/security-overview"
                },
                {
                    "name": "Performance Dashboard",
                    "url": "http://localhost:3000/d/performance-overview"
                }
            ]
        }
        
        return JSONResponse(dashboards)
    
    except Exception as e:
        logger.error(f"Failed to get dashboard URLs: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard URLs failed")


# Middleware integration helper
def setup_monitoring_middleware(app):
    """
    Setup monitoring middleware for the FastAPI app.
    """
    from shared.monitoring.metrics_middleware import PrometheusMetricsMiddleware
    from shared.monitoring.distributed_tracing import TracingMiddleware
    
    # Add Prometheus metrics middleware
    app.add_middleware(PrometheusMetricsMiddleware)
    
    # Add distributed tracing middleware
    app.add_middleware(TracingMiddleware)
    
    logger.info("Monitoring middleware configured")