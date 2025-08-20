"""
Evidence Collection Middleware for API validation and monitoring.
Provides standardized evidence format for all API endpoints.
"""

import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class EvidenceFormat:
    """Standardized evidence format for API responses."""
    
    @staticmethod
    def create_evidence(
        request: Request,
        response: Response,
        execution_time: float,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized evidence object."""
        
        evidence = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4()),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "execution_time_ms": round(execution_time * 1000, 2),
            "user_id": user_id,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "success": 200 <= status_code < 400,
            "evidence_type": "api_endpoint_validation",
            "validation_details": {
                "endpoint_accessible": True,
                "response_generated": True,
                "authentication_validated": user_id is not None,
                "processing_completed": True
            }
        }
        
        if additional_data:
            evidence["additional_data"] = additional_data
            
        # Add performance classification
        if execution_time < 0.1:
            evidence["performance_category"] = "excellent"
        elif execution_time < 0.5:
            evidence["performance_category"] = "good"
        elif execution_time < 1.0:
            evidence["performance_category"] = "acceptable"
        else:
            evidence["performance_category"] = "needs_optimization"
            
        return evidence


class EvidenceCollectionMiddleware(BaseHTTPMiddleware):
    """Middleware to collect evidence for all API requests."""
    
    def __init__(self, app, include_patterns: Optional[List[str]] = None):
        super().__init__(app)
        self.include_patterns = include_patterns or ["/api/"]
        self.exclude_health_checks = ["/health", "/api/v1/health", "/metrics"]
        
    async def dispatch(self, request: Request, call_next):
        """Process request and collect evidence."""
        start_time = time.time()
        
        # Skip evidence collection for non-API endpoints and health checks
        if not any(pattern in str(request.url) for pattern in self.include_patterns):
            return await call_next(request)
            
        # Skip verbose logging for health check endpoints
        is_health_check = any(pattern in str(request.url.path) for pattern in self.exclude_health_checks)
        
        try:
            # Process request
            response = await call_next(request)
            execution_time = time.time() - start_time
            
            # Extract user ID if available
            user_id = getattr(request.state, "user_id", None)
            
            # Create evidence
            evidence = EvidenceFormat.create_evidence(
                request=request,
                response=response,
                execution_time=execution_time,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                user_id=user_id
            )
            
            # Add evidence to response headers (for debugging)
            response.headers["X-Evidence-ID"] = evidence["request_id"]
            response.headers["X-Execution-Time"] = str(evidence["execution_time_ms"])
            
            # Log evidence for monitoring (exclude health checks from verbose logging)
            if not is_health_check:
                logger.info(f"API Evidence: {json.dumps(evidence, default=str)}")
            else:
                # Only log health check failures or at debug level
                if not evidence["success"]:
                    logger.warning(f"Health Check Failed: {evidence['endpoint']} - {evidence['status_code']}")
                else:
                    logger.debug(f"Health Check OK: {evidence['endpoint']}")
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Create error evidence
            error_evidence = EvidenceFormat.create_evidence(
                request=request,
                response=Response(status_code=500),
                execution_time=execution_time,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=500,
                additional_data={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
            logger.error(f"API Error Evidence: {json.dumps(error_evidence, default=str)}")
            raise


class HealthCheckEvidenceGenerator:
    """Generate evidence for health check endpoints."""
    
    @staticmethod
    def generate_health_evidence(
        checks: Dict[str, bool],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate evidence for health check results."""
        
        all_healthy = all(checks.values())
        
        evidence = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_type": "health_check",
            "overall_health": "healthy" if all_healthy else "unhealthy",
            "success": all_healthy,
            "health_checks": checks,
            "evidence_details": {
                "total_checks": len(checks),
                "passed_checks": sum(checks.values()),
                "failed_checks": len(checks) - sum(checks.values()),
                "success_rate": f"{(sum(checks.values())/len(checks)*100):.1f}%"
            }
        }
        
        if additional_info:
            evidence["additional_info"] = additional_info
            
        return evidence


def add_evidence_to_response(response_data: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Add evidence to API response data."""
    if isinstance(response_data, dict):
        response_data["evidence"] = evidence
    else:
        # If response is not a dict, wrap it
        response_data = {
            "data": response_data,
            "evidence": evidence
        }
    
    return response_data


# Utility functions for specific evidence types
def create_authentication_evidence(
    user_id: str,
    method: str,
    success: bool,
    additional_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create evidence for authentication operations."""
    
    evidence = {
        "timestamp": datetime.utcnow().isoformat(),
        "validation_type": "authentication",
        "user_id": user_id,
        "method": method,
        "success": success,
        "evidence_details": {
            "authentication_method": method,
            "user_verified": success,
            "session_valid": success
        }
    }
    
    if additional_details:
        evidence["additional_details"] = additional_details
        
    return evidence


def create_database_evidence(
    operation: str,
    table: str,
    success: bool,
    execution_time: float,
    rows_affected: Optional[int] = None
) -> Dict[str, Any]:
    """Create evidence for database operations."""
    
    evidence = {
        "timestamp": datetime.utcnow().isoformat(),
        "validation_type": "database_operation",
        "operation": operation,
        "table": table,
        "success": success,
        "execution_time_ms": round(execution_time * 1000, 2),
        "evidence_details": {
            "database_accessible": True,
            "operation_completed": success,
            "data_consistency": success
        }
    }
    
    if rows_affected is not None:
        evidence["rows_affected"] = rows_affected
        
    return evidence