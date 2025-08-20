"""Enhanced authentication middleware service with race condition prevention."""

import asyncio
import json
import logging
import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Callable, Awaitable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

import jwt
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.auth_queue_service import (
    auth_queue_service, AuthOperationType, AuthOperationStatus
)
from shared.services.secure_token_storage_service import (
    secure_token_storage, TokenType, StorageType
)
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthenticationState(Enum):
    """Authentication states."""
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REFRESHING = "token_refreshing"
    SESSION_EXTENDING = "session_extending"
    LOGOUT_PENDING = "logout_pending"


class SessionWarningType(Enum):
    """Types of session warnings."""
    EXPIRY_WARNING = "expiry_warning"
    ACTIVITY_WARNING = "activity_warning"
    SECURITY_WARNING = "security_warning"
    EXTENSION_AVAILABLE = "extension_available"


@dataclass
class AuthContext:
    """Authentication context for a request."""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    token_jti: Optional[str] = None
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    auth_state: AuthenticationState = AuthenticationState.UNAUTHENTICATED
    token_expires_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    session_warnings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestQueue:
    """Queue for API requests during authentication state changes."""
    pending_requests: List[Dict[str, Any]] = field(default_factory=list)
    processing: bool = False
    max_queue_size: int = 50
    timeout_seconds: int = 30


class AuthMiddlewareService:
    """Enhanced authentication middleware with race condition prevention."""
    
    def __init__(self):
        self.logger = logger
        self._request_queues: Dict[str, RequestQueue] = {}  # Per-user request queues
        self._auth_contexts: Dict[str, AuthContext] = {}  # Per-session contexts
        self._background_tasks: Dict[str, asyncio.Task] = {}  # Background token renewal tasks
        self._connection_health: Dict[str, Dict[str, Any]] = {}  # Connection health monitoring
        self._session_warnings: Dict[str, List[Dict[str, Any]]] = {}  # Session warnings
        self._initialized = False
    
    async def initialize(self):
        """Initialize the authentication middleware service."""
        if self._initialized:
            return
        
        try:
            # Initialize dependencies
            await auth_queue_service.start()
            await secure_token_storage.initialize()
            
            # Start background tasks
            asyncio.create_task(self._background_token_renewal_monitor())
            asyncio.create_task(self._session_activity_monitor())
            asyncio.create_task(self._connection_health_monitor())
            asyncio.create_task(self._cleanup_expired_contexts())
            
            self._initialized = True
            self.logger.info("AuthMiddlewareService initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AuthMiddlewareService: {str(e)}")
            raise
    
    async def authenticate_request(
        self,
        request: Request,
        session: AsyncSession,
        required_scopes: List[str] = None
    ) -> AuthContext:
        """Authenticate a request with race condition prevention."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Extract request information
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            device_fingerprint = request.headers.get("x-device-fingerprint")
            session_id = request.headers.get("x-session-id") or str(uuid.uuid4())
            
            # Get existing auth context or create new one
            auth_context = self._auth_contexts.get(session_id, AuthContext())
            auth_context.session_id = session_id
            auth_context.ip_address = ip_address
            auth_context.user_agent = user_agent
            auth_context.device_fingerprint = device_fingerprint
            
            # Extract token from request
            token = await self._extract_token(request, session_id)
            
            if not token:
                auth_context.auth_state = AuthenticationState.UNAUTHENTICATED
                self._auth_contexts[session_id] = auth_context
                return auth_context
            
            # Queue token validation to prevent race conditions
            try:
                operation_id = await auth_queue_service.queue_token_validation(
                    session=session,
                    token=token,
                    user_id=auth_context.user_id or 0,  # Will be updated after validation
                    required_scopes=required_scopes,
                    session_id=session_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Wait for validation result
                validation_result = await auth_queue_service.get_operation_result(
                    operation_id, timeout=10.0
                )
                
                if validation_result.get("valid"):
                    # Update auth context with validated information
                    auth_context.user_id = validation_result["user_id"]
                    auth_context.scopes = validation_result.get("scopes", [])
                    auth_context.token_jti = validation_result.get("jti")
                    auth_context.auth_state = AuthenticationState.AUTHENTICATED
                    auth_context.token_expires_at = datetime.fromisoformat(
                        validation_result["expires_at"]
                    )
                    auth_context.last_activity_at = datetime.now(timezone.utc)
                    
                    # Check for session warnings
                    await self._check_session_warnings(auth_context, session)
                    
                    # Start background token renewal if needed
                    await self._schedule_token_renewal(auth_context, token)
                    
                else:
                    auth_context.auth_state = AuthenticationState.TOKEN_EXPIRED
                
            except Exception as e:
                self.logger.error(f"Token validation failed: {str(e)}")
                auth_context.auth_state = AuthenticationState.UNAUTHENTICATED
                
                # Log authentication failure
                await security_audit_service.log_security_violation(
                    session=session,
                    violation_type="AUTHENTICATION_FAILED",
                    severity="MEDIUM",
                    violation_details={
                        "error": str(e),
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "session_id": session_id
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                    blocked=False
                )
            
            # Store updated context
            self._auth_contexts[session_id] = auth_context
            
            # Update connection health
            await self._update_connection_health(session_id, auth_context, True)
            
            return auth_context
            
        except Exception as e:
            self.logger.error(f"Authentication request failed: {str(e)}")
            
            # Return unauthenticated context on error
            error_context = AuthContext(
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                auth_state=AuthenticationState.UNAUTHENTICATED
            )
            
            self._auth_contexts[session_id] = error_context
            return error_context
    
    async def refresh_token_with_queuing(
        self,
        request: Request,
        response: Response,
        session: AsyncSession,
        session_id: str
    ) -> bool:
        """Refresh token with proper request queuing."""
        try:
            auth_context = self._auth_contexts.get(session_id)
            if not auth_context or not auth_context.user_id:
                return False
            
            # Set state to refreshing
            auth_context.auth_state = AuthenticationState.TOKEN_REFRESHING
            
            # Queue pending requests
            user_key = f"user_{auth_context.user_id}"
            if user_key not in self._request_queues:
                self._request_queues[user_key] = RequestQueue()
            
            request_queue = self._request_queues[user_key]
            request_queue.processing = True
            
            try:
                # Get refresh token
                refresh_token = await self._extract_refresh_token(request, session_id)
                if not refresh_token:
                    return False
                
                # Queue token refresh operation
                operation_id = await auth_queue_service.queue_token_refresh(
                    session=session,
                    user_id=auth_context.user_id,
                    refresh_token=refresh_token,
                    session_id=session_id,
                    ip_address=auth_context.ip_address,
                    user_agent=auth_context.user_agent
                )
                
                # Wait for refresh result
                refresh_result = await auth_queue_service.get_operation_result(
                    operation_id, timeout=15.0
                )
                
                if refresh_result.get("success"):
                    # Update tokens in secure storage
                    new_token = refresh_result["new_token"]
                    expires_at = datetime.fromisoformat(refresh_result["expires_at"])
                    
                    # Store new access token
                    await secure_token_storage.store_token(
                        session=session,
                        user_id=auth_context.user_id,
                        token_type=TokenType.ACCESS_TOKEN,
                        token_value=new_token,
                        session_id=session_id,
                        device_fingerprint=auth_context.device_fingerprint,
                        expires_at=expires_at,
                        storage_type=StorageType.SECURE_STORAGE
                    )
                    
                    # Update auth context
                    auth_context.auth_state = AuthenticationState.AUTHENTICATED
                    auth_context.token_expires_at = expires_at
                    auth_context.last_activity_at = datetime.now(timezone.utc)
                    
                    # Set new token in response cookies
                    await self._set_secure_auth_cookies(response, new_token, refresh_token)
                    
                    # Process queued requests
                    await self._process_queued_requests(user_key, new_token)
                    
                    self.logger.info(f"Token refreshed successfully for user {auth_context.user_id}")
                    return True
                
                return False
                
            finally:
                request_queue.processing = False
                
        except Exception as e:
            self.logger.error(f"Token refresh failed: {str(e)}")
            
            # Update auth context
            if auth_context:
                auth_context.auth_state = AuthenticationState.TOKEN_EXPIRED
            
            return False
    
    async def extend_session(
        self,
        session: AsyncSession,
        session_id: str,
        extension_minutes: int = 30
    ) -> bool:
        """Extend user session with activity-based renewal."""
        try:
            auth_context = self._auth_contexts.get(session_id)
            if not auth_context or not auth_context.user_id:
                return False
            
            # Set state to extending
            auth_context.auth_state = AuthenticationState.SESSION_EXTENDING
            
            # Get current token
            current_token = await secure_token_storage.retrieve_token(
                session=session,
                token_id=auth_context.token_jti or "",
                user_id=auth_context.user_id,
                session_id=session_id
            )
            
            if not current_token:
                return False
            
            # Queue session extension operation
            operation_id = await auth_queue_service.queue_session_extension(
                session=session,
                user_id=auth_context.user_id,
                current_token=current_token,
                session_id=session_id,
                ip_address=auth_context.ip_address
            )
            
            # Wait for extension result
            extension_result = await auth_queue_service.get_operation_result(
                operation_id, timeout=10.0
            )
            
            if extension_result.get("success"):
                # Update auth context
                extended_token = extension_result["extended_token"]
                expires_at = datetime.fromisoformat(extension_result["expires_at"])
                
                auth_context.auth_state = AuthenticationState.AUTHENTICATED
                auth_context.token_expires_at = expires_at
                auth_context.last_activity_at = datetime.now(timezone.utc)
                
                # Clear any expiry warnings
                auth_context.session_warnings = [
                    w for w in auth_context.session_warnings 
                    if w.get("type") != SessionWarningType.EXPIRY_WARNING.value
                ]
                
                self.logger.info(f"Session extended for user {auth_context.user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Session extension failed: {str(e)}")
            return False
    
    async def queue_api_request(
        self,
        user_id: int,
        request_callback: Callable[[], Awaitable[Dict[str, Any]]],
        session_id: Optional[str] = None,
        retry_count: int = 3,
        exponential_backoff: bool = True
    ) -> Dict[str, Any]:
        """Queue API request with retry logic and exponential backoff."""
        try:
            # Get or create request queue for user
            user_key = f"user_{user_id}"
            if user_key not in self._request_queues:
                self._request_queues[user_key] = RequestQueue()
            
            request_queue = self._request_queues[user_key]
            
            # Check if authentication is in progress
            auth_context = None
            if session_id:
                auth_context = self._auth_contexts.get(session_id)
            
            if (auth_context and 
                auth_context.auth_state in [
                    AuthenticationState.TOKEN_REFRESHING,
                    AuthenticationState.SESSION_EXTENDING
                ]):
                # Queue the request for later processing
                if len(request_queue.pending_requests) < request_queue.max_queue_size:
                    queued_request = {
                        "callback": request_callback,
                        "queued_at": datetime.now(timezone.utc),
                        "session_id": session_id,
                        "retry_count": retry_count,
                        "exponential_backoff": exponential_backoff
                    }
                    request_queue.pending_requests.append(queued_request)
                    
                    # Wait for queue processing
                    timeout = request_queue.timeout_seconds
                    start_time = time.time()
                    
                    while (time.time() - start_time < timeout and 
                           request_queue.processing):
                        await asyncio.sleep(0.1)
                    
                    # Check if our request was processed
                    for req in request_queue.pending_requests[:]:
                        if req["callback"] == request_callback:
                            request_queue.pending_requests.remove(req)
                            raise TimeoutError("Request timed out in queue")
                
                else:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Request queue full"
                    )
            
            # Execute request with retry logic
            last_exception = None
            
            for attempt in range(retry_count + 1):
                try:
                    result = await request_callback()
                    
                    # Update connection health on success
                    if session_id:
                        await self._update_connection_health(session_id, auth_context, True)
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Update connection health on failure
                    if session_id:
                        await self._update_connection_health(session_id, auth_context, False)
                    
                    if attempt < retry_count:
                        # Calculate backoff delay
                        if exponential_backoff:
                            delay = min(2 ** attempt, 30)  # Max 30 seconds
                        else:
                            delay = 1
                        
                        self.logger.warning(
                            f"API request failed (attempt {attempt + 1}/{retry_count + 1}), "
                            f"retrying in {delay}s: {str(e)}"
                        )
                        
                        await asyncio.sleep(delay)
                    else:
                        self.logger.error(f"API request failed after {retry_count + 1} attempts: {str(e)}")
            
            # All retries failed
            raise last_exception
            
        except Exception as e:
            self.logger.error(f"Queued API request failed: {str(e)}")
            raise
    
    async def logout_with_cleanup(
        self,
        request: Request,
        response: Response,
        session: AsyncSession,
        session_id: str,
        revoke_all_sessions: bool = False
    ):
        """Logout with comprehensive cleanup."""
        try:
            auth_context = self._auth_contexts.get(session_id)
            if not auth_context:
                return
            
            # Set logout state
            auth_context.auth_state = AuthenticationState.LOGOUT_PENDING
            user_id = auth_context.user_id
            
            if user_id:
                # Revoke tokens in secure storage
                if revoke_all_sessions:
                    await secure_token_storage.revoke_user_tokens(
                        session=session,
                        user_id=user_id,
                        reason="logout_all_sessions"
                    )
                else:
                    await secure_token_storage.revoke_user_tokens(
                        session=session,
                        user_id=user_id,
                        except_session_id=session_id,
                        reason="logout_single_session"
                    )
                
                # Cancel background token renewal
                renewal_task_key = f"renewal_{user_id}_{session_id}"
                if renewal_task_key in self._background_tasks:
                    self._background_tasks[renewal_task_key].cancel()
                    del self._background_tasks[renewal_task_key]
                
                # Clear request queue
                user_key = f"user_{user_id}"
                if user_key in self._request_queues:
                    del self._request_queues[user_key]
                
                # Log logout
                await security_audit_service.log_data_access(
                    session=session,
                    user_id=user_id,
                    service_name="auth_middleware",
                    access_type="LOGOUT",
                    table_name="user_sessions",
                    row_count=1,
                    sensitive_data_accessed=False,
                    access_pattern={
                        "session_id": session_id,
                        "revoke_all": revoke_all_sessions,
                        "logout_timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    session_id=session_id,
                    ip_address=auth_context.ip_address
                )
            
            # Clear auth context
            if session_id in self._auth_contexts:
                del self._auth_contexts[session_id]
            
            # Clear session warnings
            if session_id in self._session_warnings:
                del self._session_warnings[session_id]
            
            # Clear connection health
            if session_id in self._connection_health:
                del self._connection_health[session_id]
            
            # Clear cookies
            await self._clear_auth_cookies(response)
            
            self.logger.info(f"User {user_id} logged out successfully")
            
        except Exception as e:
            self.logger.error(f"Logout cleanup failed: {str(e)}")
    
    async def get_session_warnings(self, session_id: str) -> List[Dict[str, Any]]:
        """Get session warnings for a user."""
        auth_context = self._auth_contexts.get(session_id)
        if not auth_context:
            return []
        
        return auth_context.session_warnings
    
    async def get_connection_health(self, session_id: str) -> Dict[str, Any]:
        """Get connection health information."""
        return self._connection_health.get(session_id, {
            "status": "unknown",
            "last_check": None,
            "success_rate": 0.0,
            "average_response_time": 0.0,
            "consecutive_failures": 0
        })
    
    async def _extract_token(self, request: Request, session_id: str) -> Optional[str]:
        """Extract token from request with secure storage support."""
        # Try Authorization header first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try cookies
        access_token = request.cookies.get("access_token")
        if access_token:
            return access_token
        
        # Try secure storage (this would be handled client-side)
        # For server-side, we can check if there's a stored token ID
        token_id = request.headers.get("x-token-id")
        if token_id:
            # This would require the client to send the token ID
            # and we'd retrieve the actual token from secure storage
            pass
        
        return None
    
    async def _extract_refresh_token(self, request: Request, session_id: str) -> Optional[str]:
        """Extract refresh token from request."""
        # Try cookies first
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            return refresh_token
        
        # Try secure storage
        # This would be implemented similar to access token extraction
        
        return None
    
    async def _set_secure_auth_cookies(
        self,
        response: Response,
        access_token: str,
        refresh_token: str
    ):
        """Set secure authentication cookies."""
        import os
        
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,  # Accessible by JavaScript for WebSocket auth
            secure=is_production,
            samesite="lax" if not is_production else "strict",
            max_age=30 * 60,  # 30 minutes
            path="/"
        )
        
        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=is_production,
            samesite="lax" if not is_production else "strict",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
    
    async def _clear_auth_cookies(self, response: Response):
        """Clear authentication cookies."""
        import os
        
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        
        cookies_to_clear = ["access_token", "refresh_token", "csrf_token"]
        
        for cookie_name in cookies_to_clear:
            response.set_cookie(
                key=cookie_name,
                value="",
                httponly=True,
                secure=is_production,
                samesite="strict",
                max_age=0,
                expires=0,
                path="/"
            )
    
    async def _check_session_warnings(self, auth_context: AuthContext, session: AsyncSession):
        """Check for session warnings (expiry, activity, etc.)."""
        if not auth_context.token_expires_at:
            return
        
        current_time = datetime.now(timezone.utc)
        time_to_expiry = auth_context.token_expires_at - current_time
        
        # Check for expiry warning (5 minutes before expiration)
        if time_to_expiry.total_seconds() <= 300:
            warning = {
                "type": SessionWarningType.EXPIRY_WARNING.value,
                "message": f"Session expires in {int(time_to_expiry.total_seconds() / 60)} minutes",
                "severity": "warning",
                "action_required": True,
                "suggested_action": "extend_session",
                "expires_at": auth_context.token_expires_at.isoformat(),
                "created_at": current_time.isoformat()
            }
            
            # Add to warnings if not already present
            existing_warnings = [
                w for w in auth_context.session_warnings 
                if w.get("type") == SessionWarningType.EXPIRY_WARNING.value
            ]
            
            if not existing_warnings:
                auth_context.session_warnings.append(warning)
        
        # Check for activity warning (30 minutes of inactivity)
        if auth_context.last_activity_at:
            time_since_activity = current_time - auth_context.last_activity_at
            
            if time_since_activity.total_seconds() >= 1800:  # 30 minutes
                warning = {
                    "type": SessionWarningType.ACTIVITY_WARNING.value,
                    "message": f"No activity for {int(time_since_activity.total_seconds() / 60)} minutes",
                    "severity": "info",
                    "action_required": False,
                    "last_activity": auth_context.last_activity_at.isoformat(),
                    "created_at": current_time.isoformat()
                }
                
                # Add to warnings if not already present
                existing_warnings = [
                    w for w in auth_context.session_warnings 
                    if w.get("type") == SessionWarningType.ACTIVITY_WARNING.value
                ]
                
                if not existing_warnings:
                    auth_context.session_warnings.append(warning)
    
    async def _schedule_token_renewal(self, auth_context: AuthContext, current_token: str):
        """Schedule background token renewal."""
        if not auth_context.user_id or not auth_context.session_id:
            return
        
        task_key = f"renewal_{auth_context.user_id}_{auth_context.session_id}"
        
        # Cancel existing renewal task
        if task_key in self._background_tasks:
            self._background_tasks[task_key].cancel()
        
        # Schedule new renewal task
        renewal_task = asyncio.create_task(
            self._background_token_renewal(auth_context, current_token)
        )
        
        self._background_tasks[task_key] = renewal_task
    
    async def _background_token_renewal(self, auth_context: AuthContext, current_token: str):
        """Background task for token renewal."""
        try:
            if not auth_context.token_expires_at:
                return
            
            # Calculate renewal time (5 minutes before expiry)
            current_time = datetime.now(timezone.utc)
            time_to_renewal = auth_context.token_expires_at - current_time - timedelta(minutes=5)
            
            if time_to_renewal.total_seconds() > 0:
                await asyncio.sleep(time_to_renewal.total_seconds())
            
            # Check if context still exists and is authenticated
            if (auth_context.session_id not in self._auth_contexts or
                auth_context.auth_state != AuthenticationState.AUTHENTICATED):
                return
            
            # Attempt token renewal
            self.logger.info(f"Background token renewal for user {auth_context.user_id}")
            
            # This would trigger the actual renewal process
            # For now, just log the attempt
            
        except asyncio.CancelledError:
            self.logger.debug(f"Token renewal cancelled for user {auth_context.user_id}")
        except Exception as e:
            self.logger.error(f"Background token renewal failed: {str(e)}")
    
    async def _process_queued_requests(self, user_key: str, new_token: str):
        """Process queued requests after token refresh."""
        if user_key not in self._request_queues:
            return
        
        request_queue = self._request_queues[user_key]
        
        try:
            # Process pending requests
            while request_queue.pending_requests:
                queued_request = request_queue.pending_requests.pop(0)
                
                try:
                    # Execute the queued request
                    callback = queued_request["callback"]
                    await callback()
                    
                except Exception as e:
                    self.logger.error(f"Failed to process queued request: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Failed to process request queue: {str(e)}")
    
    async def _update_connection_health(
        self,
        session_id: str,
        auth_context: Optional[AuthContext],
        success: bool,
        response_time: Optional[float] = None
    ):
        """Update connection health metrics."""
        if session_id not in self._connection_health:
            self._connection_health[session_id] = {
                "status": "healthy",
                "last_check": datetime.now(timezone.utc),
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "consecutive_failures": 0,
                "response_times": []
            }
        
        health = self._connection_health[session_id]
        health["last_check"] = datetime.now(timezone.utc)
        health["total_requests"] += 1
        
        if success:
            health["successful_requests"] += 1
            health["consecutive_failures"] = 0
            health["status"] = "healthy"
        else:
            health["failed_requests"] += 1
            health["consecutive_failures"] += 1
            
            if health["consecutive_failures"] >= 3:
                health["status"] = "degraded"
            if health["consecutive_failures"] >= 5:
                health["status"] = "unhealthy"
        
        # Update success rate
        health["success_rate"] = health["successful_requests"] / health["total_requests"]
        
        # Update response time tracking
        if response_time:
            health["response_times"].append(response_time)
            
            # Keep only last 100 response times
            if len(health["response_times"]) > 100:
                health["response_times"].pop(0)
            
            # Update average
            health["average_response_time"] = sum(health["response_times"]) / len(health["response_times"])
    
    async def _background_token_renewal_monitor(self):
        """Monitor background token renewal tasks."""
        while True:
            try:
                # Clean up completed tasks
                completed_tasks = []
                for task_key, task in self._background_tasks.items():
                    if task.done():
                        completed_tasks.append(task_key)
                
                for task_key in completed_tasks:
                    del self._background_tasks[task_key]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Background renewal monitor error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _session_activity_monitor(self):
        """Monitor session activity and cleanup inactive sessions."""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                inactive_sessions = []
                
                for session_id, auth_context in self._auth_contexts.items():
                    if not auth_context.last_activity_at:
                        continue
                    
                    # Check for inactive sessions (2 hours)
                    time_since_activity = current_time - auth_context.last_activity_at
                    
                    if time_since_activity.total_seconds() >= 7200:  # 2 hours
                        inactive_sessions.append(session_id)
                
                # Clean up inactive sessions
                for session_id in inactive_sessions:
                    if session_id in self._auth_contexts:
                        self.logger.info(f"Cleaning up inactive session: {session_id}")
                        del self._auth_contexts[session_id]
                    
                    if session_id in self._session_warnings:
                        del self._session_warnings[session_id]
                    
                    if session_id in self._connection_health:
                        del self._connection_health[session_id]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Session activity monitor error: {str(e)}")
                await asyncio.sleep(300)
    
    async def _connection_health_monitor(self):
        """Monitor connection health and trigger alerts."""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                for session_id, health in self._connection_health.items():
                    # Check for unhealthy connections
                    if health["status"] == "unhealthy":
                        auth_context = self._auth_contexts.get(session_id)
                        
                        if auth_context and auth_context.user_id:
                            # Add connection warning
                            warning = {
                                "type": SessionWarningType.SECURITY_WARNING.value,
                                "message": "Connection issues detected",
                                "severity": "warning",
                                "action_required": False,
                                "details": {
                                    "consecutive_failures": health["consecutive_failures"],
                                    "success_rate": health["success_rate"]
                                },
                                "created_at": current_time.isoformat()
                            }
                            
                            auth_context.session_warnings.append(warning)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Connection health monitor error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_contexts(self):
        """Clean up expired authentication contexts."""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                expired_contexts = []
                
                for session_id, auth_context in self._auth_contexts.items():
                    # Check for expired tokens
                    if (auth_context.token_expires_at and 
                        auth_context.token_expires_at <= current_time):
                        expired_contexts.append(session_id)
                    
                    # Check for very old contexts (24 hours)
                    context_age = current_time - auth_context.last_activity_at if auth_context.last_activity_at else timedelta(hours=25)
                    
                    if context_age.total_seconds() >= 86400:  # 24 hours
                        expired_contexts.append(session_id)
                
                # Clean up expired contexts
                for session_id in expired_contexts:
                    if session_id in self._auth_contexts:
                        self.logger.info(f"Cleaning up expired context: {session_id}")
                        del self._auth_contexts[session_id]
                    
                    # Clean up related data
                    if session_id in self._session_warnings:
                        del self._session_warnings[session_id]
                    
                    if session_id in self._connection_health:
                        del self._connection_health[session_id]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Context cleanup error: {str(e)}")
                await asyncio.sleep(300)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


# Global authentication middleware service instance
auth_middleware_service = AuthMiddlewareService()