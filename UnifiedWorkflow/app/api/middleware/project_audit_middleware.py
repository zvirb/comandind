"""
Project audit middleware for logging and monitoring project operations.

This middleware provides comprehensive audit logging, rate limiting, and monitoring
for project-related API operations with user context and performance tracking.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ProjectAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for project operations audit logging and monitoring.
    
    Features:
    - Detailed audit logging for all project operations
    - Performance monitoring and slow query detection
    - User activity tracking
    - Error pattern analysis
    - Rate limiting for project creation
    """
    
    def __init__(self, app, max_projects_per_hour: int = 50, slow_query_threshold: float = 2.0):
        super().__init__(app)
        self.max_projects_per_hour = max_projects_per_hour
        self.slow_query_threshold = slow_query_threshold
        self.user_project_counts: Dict[int, list] = {}  # user_id -> list of timestamps
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with audit logging and monitoring."""
        
        # Only process project-related endpoints
        if not self._is_project_endpoint(request.url.path):
            return await call_next(request)
        
        start_time = time.time()
        user_id = await self._get_user_id(request)
        operation = self._determine_operation(request)
        
        # Log request start
        audit_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "operation": operation,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "user_agent": request.headers.get("user-agent"),
            "ip_address": self._get_client_ip(request),
            "request_id": request.headers.get("x-request-id"),
        }
        
        logger.info(f"Project operation started: {operation} by user {user_id}")
        
        try:
            # Check rate limits for project creation
            if operation == "create_project" and user_id:
                if not await self._check_rate_limit(user_id):
                    logger.warning(f"Rate limit exceeded for user {user_id} on project creation")
                    audit_data.update({
                        "result": "rate_limited",
                        "error": "Project creation rate limit exceeded"
                    })
                    self._log_audit(audit_data)
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Too many projects created. Limit: {self.max_projects_per_hour} per hour",
                            "retry_after": 3600,
                            "current_hour_count": len(self.user_project_counts.get(user_id, []))
                        }
                    )
            
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Update audit data with response information
            audit_data.update({
                "status_code": response.status_code,
                "response_time_seconds": round(response_time, 3),
                "result": "success" if response.status_code < 400 else "error"
            })
            
            # Check for slow queries
            if response_time > self.slow_query_threshold:
                audit_data["slow_query"] = True
                logger.warning(f"Slow project operation detected: {operation} took {response_time:.3f}s for user {user_id}")
            
            # Track successful project creation for rate limiting
            if operation == "create_project" and response.status_code == 201 and user_id:
                await self._track_project_creation(user_id)
            
            # Log successful operation
            logger.info(f"Project operation completed: {operation} by user {user_id} in {response_time:.3f}s")
            
        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            audit_data.update({
                "result": "error",
                "error": str(e),
                "response_time_seconds": round(response_time, 3),
                "status_code": 500
            })
            
            logger.error(f"Project operation failed: {operation} by user {user_id}: {e}", exc_info=True)
            
            # Re-raise the exception
            raise
        
        finally:
            # Always log audit data
            self._log_audit(audit_data)
        
        return response
    
    def _is_project_endpoint(self, path: str) -> bool:
        """Check if the request is for a project-related endpoint."""
        project_paths = [
            "/api/v1/projects",
            "/projects"
        ]
        return any(path.startswith(project_path) for project_path in project_paths)
    
    async def _get_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from request context."""
        try:
            # Try to get user from request state (set by auth middleware)
            if hasattr(request.state, 'user') and request.state.user:
                return getattr(request.state.user, 'id', None)
            
            # Try to get from JWT token in headers
            auth_header = request.headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # In a real implementation, decode JWT here
                # For now, return None to indicate user could not be determined
                pass
                
        except Exception as e:
            logger.debug(f"Could not determine user ID: {e}")
        
        return None
    
    def _determine_operation(self, request: Request) -> str:
        """Determine the type of project operation from the request."""
        path = request.url.path
        method = request.method
        
        if method == "POST" and path.endswith("/projects"):
            return "create_project"
        elif method == "GET" and "/projects/" in path and path.count("/") > 3:
            return "get_project"
        elif method == "GET" and path.endswith("/projects"):
            return "list_projects"
        elif method == "PUT" and "/projects/" in path:
            return "update_project"
        elif method == "DELETE" and "/projects/" in path:
            return "delete_project"
        elif "stats" in path or "statistics" in path:
            return "get_project_stats"
        else:
            return f"{method.lower()}_project_endpoint"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client's IP address, considering proxies."""
        # Check for forwarded IP first (from load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded project creation rate limit."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old timestamps
        if user_id in self.user_project_counts:
            self.user_project_counts[user_id] = [
                timestamp for timestamp in self.user_project_counts[user_id]
                if timestamp > hour_ago
            ]
        else:
            self.user_project_counts[user_id] = []
        
        # Check if under limit
        current_count = len(self.user_project_counts[user_id])
        return current_count < self.max_projects_per_hour
    
    async def _track_project_creation(self, user_id: int) -> None:
        """Track a successful project creation for rate limiting."""
        now = datetime.now()
        
        if user_id not in self.user_project_counts:
            self.user_project_counts[user_id] = []
        
        self.user_project_counts[user_id].append(now)
        
        # Clean up old entries to prevent memory growth
        hour_ago = now - timedelta(hours=1)
        self.user_project_counts[user_id] = [
            timestamp for timestamp in self.user_project_counts[user_id]
            if timestamp > hour_ago
        ]
    
    def _log_audit(self, audit_data: Dict[str, Any]) -> None:
        """Log audit data in structured format."""
        # Create a structured audit log entry
        audit_entry = {
            "audit_type": "project_operation",
            "timestamp": audit_data.get("timestamp"),
            "user_id": audit_data.get("user_id"),
            "operation": audit_data.get("operation"),
            "method": audit_data.get("method"),
            "path": audit_data.get("path"),
            "status_code": audit_data.get("status_code"),
            "response_time": audit_data.get("response_time_seconds"),
            "result": audit_data.get("result"),
            "ip_address": audit_data.get("ip_address"),
            "user_agent": audit_data.get("user_agent"),
        }
        
        # Add error information if present
        if "error" in audit_data:
            audit_entry["error"] = audit_data["error"]
        
        # Add slow query flag if present
        if audit_data.get("slow_query"):
            audit_entry["slow_query"] = True
        
        # Log as structured JSON for log aggregation systems
        logger.info(f"PROJECT_AUDIT: {json.dumps(audit_entry)}")
        
        # Also log performance metrics separately for monitoring
        if "response_time_seconds" in audit_data:
            response_time = audit_data["response_time_seconds"]
            operation = audit_data.get("operation", "unknown")
            logger.info(f"PROJECT_PERFORMANCE: operation={operation} response_time={response_time}s user_id={audit_data.get('user_id')}")