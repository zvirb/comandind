"""
Backend monitoring and performance endpoints.

This module provides endpoints for monitoring API performance,
tracking response times, and validating system health.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.dependencies import get_current_user
from shared.database.models import User
from shared.utils.database_setup import get_db
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory performance tracking (in production, use Redis)
performance_metrics = {
    "response_times": [],
    "endpoint_stats": {},
    "error_count": 0,
    "total_requests": 0
}

@router.get("/metrics/performance", tags=["Monitoring"])
async def get_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Get API performance metrics including response times and endpoint statistics.
    """
    try:
        # Calculate average response times for the last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_times = [
            rt for rt in performance_metrics["response_times"] 
            if rt["timestamp"] > one_hour_ago
        ]
        
        avg_response_time = 0
        if recent_times:
            avg_response_time = sum(rt["duration"] for rt in recent_times) / len(recent_times)
        
        return {
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "total_requests": performance_metrics["total_requests"],
            "error_count": performance_metrics["error_count"],
            "recent_requests_count": len(recent_times),
            "endpoint_stats": performance_metrics["endpoint_stats"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )

@router.get("/metrics/database", tags=["Monitoring"])
async def get_database_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get database performance and connection metrics.
    """
    try:
        start_time = time.time()
        
        # Test database query performance
        db.execute(text("SELECT 1"))
        query_time = (time.time() - start_time) * 1000
        
        # Get basic database statistics
        user_count = db.query(User).count()
        
        try:
            from shared.database.models import Project
            project_count = db.query(Project).count()
        except Exception:
            project_count = 0
        
        try:
            from shared.database.models import Document
            document_count = db.query(Document).count()
        except Exception:
            document_count = 0
        
        return {
            "query_response_time_ms": round(query_time, 2),
            "total_users": user_count,
            "total_projects": project_count,
            "total_documents": document_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving database metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database metrics"
        )

@router.get("/validate/endpoints", tags=["Monitoring"])
async def validate_critical_endpoints():
    """
    Validate that critical API endpoints are responsive and returning expected status codes.
    """
    import httpx
    
    base_url = "http://localhost:8000"
    endpoints_to_test = [
        {"path": "/health", "expected_status": 200},
        {"path": "/api/v1/health", "expected_status": 200},
        {"path": "/api/v1/health/live", "expected_status": 200},
        {"path": "/", "expected_status": 200},
    ]
    
    results = []
    overall_healthy = True
    
    async with httpx.AsyncClient() as client:
        for endpoint in endpoints_to_test:
            try:
                start_time = time.time()
                response = await client.get(f"{base_url}{endpoint['path']}", timeout=5.0)
                response_time = (time.time() - start_time) * 1000
                
                is_healthy = response.status_code == endpoint['expected_status']
                if not is_healthy:
                    overall_healthy = False
                
                results.append({
                    "endpoint": endpoint['path'],
                    "status_code": response.status_code,
                    "expected_status": endpoint['expected_status'],
                    "response_time_ms": round(response_time, 2),
                    "healthy": is_healthy
                })
            except Exception as e:
                overall_healthy = False
                results.append({
                    "endpoint": endpoint['path'],
                    "status_code": None,
                    "expected_status": endpoint['expected_status'],
                    "response_time_ms": None,
                    "healthy": False,
                    "error": str(e)
                })
    
    return {
        "overall_healthy": overall_healthy,
        "endpoints": results,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/validate/authentication", tags=["Monitoring"])
async def validate_authentication_endpoints():
    """
    Validate authentication system endpoints and flows.
    """
    import httpx
    
    base_url = "http://localhost:8000"
    auth_endpoints = [
        {"path": "/api/v1/auth/csrf-token", "method": "GET"},
        {"path": "/api/v1/auth/status", "method": "GET"},
        {"path": "/api/auth/csrf-token", "method": "GET"},  # Legacy path
    ]
    
    results = []
    overall_healthy = True
    
    async with httpx.AsyncClient() as client:
        for endpoint in auth_endpoints:
            try:
                start_time = time.time()
                if endpoint["method"] == "GET":
                    response = await client.get(f"{base_url}{endpoint['path']}", timeout=5.0)
                else:
                    response = await client.post(f"{base_url}{endpoint['path']}", timeout=5.0)
                
                response_time = (time.time() - start_time) * 1000
                
                # For auth endpoints, we expect either 200 (success) or 401 (unauthorized)
                is_healthy = response.status_code in [200, 401]
                if not is_healthy:
                    overall_healthy = False
                
                results.append({
                    "endpoint": endpoint['path'],
                    "method": endpoint["method"],
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "healthy": is_healthy
                })
            except Exception as e:
                overall_healthy = False
                results.append({
                    "endpoint": endpoint['path'],
                    "method": endpoint["method"],
                    "status_code": None,
                    "response_time_ms": None,
                    "healthy": False,
                    "error": str(e)
                })
    
    return {
        "overall_healthy": overall_healthy,
        "auth_endpoints": results,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/system/info", tags=["Monitoring"])
async def get_system_info():
    """
    Get system information and runtime details.
    """
    try:
        import psutil
        import sys
        import platform
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "uptime_seconds": time.time() - psutil.boot_time(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving system info: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def track_request_performance(request: Request, response_time: float):
    """
    Track request performance metrics.
    This function should be called from middleware to track all requests.
    """
    global performance_metrics
    
    # Store recent response times (limit to last 1000 requests)
    performance_metrics["response_times"].append({
        "timestamp": datetime.now(),
        "duration": response_time,
        "path": request.url.path,
        "method": request.method
    })
    
    # Keep only recent entries
    if len(performance_metrics["response_times"]) > 1000:
        performance_metrics["response_times"] = performance_metrics["response_times"][-1000:]
    
    # Track endpoint-specific stats
    endpoint_key = f"{request.method} {request.url.path}"
    if endpoint_key not in performance_metrics["endpoint_stats"]:
        performance_metrics["endpoint_stats"][endpoint_key] = {
            "count": 0,
            "total_time": 0,
            "avg_time": 0
        }
    
    stats = performance_metrics["endpoint_stats"][endpoint_key]
    stats["count"] += 1
    stats["total_time"] += response_time
    stats["avg_time"] = stats["total_time"] / stats["count"]
    
    performance_metrics["total_requests"] += 1

def track_error():
    """
    Track API errors.
    This function should be called when errors occur.
    """
    global performance_metrics
    performance_metrics["error_count"] += 1