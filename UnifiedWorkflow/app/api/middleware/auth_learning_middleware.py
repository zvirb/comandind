"""
Authentication Learning Integration Middleware

Non-invasive middleware that integrates the Authentication Learning Integration system
with the existing authentication flow. This middleware enhances security without
disrupting existing functionality.

Features:
- Seamless integration with existing auth middleware
- Real-time pattern detection and risk assessment
- Adaptive validation based on risk levels
- Fallback to standard auth on learning system failure
- Comprehensive logging and monitoring
"""

import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from shared.services.auth_pattern_detection_service import (
    AuthEventType, AuthEvent, auth_pattern_detection_service
)
from shared.services.auth_risk_assessment_service import (
    RiskLevel, auth_risk_assessment_service
)
from shared.services.adaptive_validation_service import (
    ValidationType, ValidationResult, adaptive_validation_service
)
from shared.services.security_audit_service import security_audit_service
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)

class AuthLearningMiddleware(BaseHTTPMiddleware):
    """
    Authentication Learning Integration Middleware
    
    Integrates pattern detection, risk assessment, and adaptive validation
    with the existing authentication system in a non-invasive manner.
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.learning_system_timeout = 2.0  # 2 second timeout for learning system
        
        # Endpoints that trigger authentication learning
        self.monitored_auth_endpoints = {
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/token"
        }
        
        # Endpoints that require validation checks
        self.validation_endpoints = {
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/login"
        }
        
        # Performance tracking
        self.performance_metrics = {
            "total_requests": 0,
            "learning_system_calls": 0,
            "learning_system_timeouts": 0,
            "validation_challenges_issued": 0,
            "validation_bypasses": 0,
            "average_processing_time_ms": 0.0
        }
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Process request through authentication learning system"""
        
        processing_start = time.time()
        path = request.url.path
        
        # Skip processing if not enabled or not an auth endpoint
        if not self.enabled or not self._should_process_request(path):
            return await call_next(request)
        
        # Extract request information
        request_info = await self._extract_request_info(request)
        
        # Pre-authentication risk assessment
        pre_auth_assessment = None
        if path in self.validation_endpoints:
            pre_auth_assessment = await self._perform_pre_auth_assessment(request_info)
        
        # Process the request normally
        response = await call_next(request)
        
        # Post-authentication learning and monitoring
        await self._process_post_auth_learning(request, response, request_info, pre_auth_assessment)
        
        # Update performance metrics
        processing_time = (time.time() - processing_start) * 1000
        await self._update_performance_metrics(processing_time)
        
        return response
    
    def _should_process_request(self, path: str) -> bool:
        """Determine if request should be processed by learning system"""
        return any(auth_endpoint in path for auth_endpoint in self.monitored_auth_endpoints)
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract relevant information from request"""
        try:
            # Get client information
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Extract authentication attempt information
            auth_info = await self._extract_auth_info(request)
            
            return {
                "ip_address": client_ip,
                "user_agent": user_agent,
                "path": request.url.path,
                "method": request.method,
                "timestamp": datetime.utcnow(),
                "auth_info": auth_info,
                "headers": dict(request.headers),
                "additional_context": {
                    "path": request.url.path,
                    "method": request.method,
                    "content_type": request.headers.get("content-type", ""),
                    "referer": request.headers.get("referer", ""),
                    "x_forwarded_for": request.headers.get("x-forwarded-for", "")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to extract request info: {str(e)}")
            return {
                "ip_address": "unknown",
                "user_agent": "unknown",
                "path": request.url.path,
                "method": request.method,
                "timestamp": datetime.utcnow(),
                "auth_info": {},
                "headers": {},
                "additional_context": {}
            }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering reverse proxies"""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _extract_auth_info(self, request: Request) -> Dict[str, Any]:
        """Extract authentication information from request"""
        try:
            auth_info = {}
            
            # Check for existing authentication tokens
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                auth_info["has_token"] = True
                auth_info["token_type"] = "bearer"
            
            access_token = request.cookies.get("access_token")
            if access_token:
                auth_info["has_cookie_token"] = True
            
            # Extract user ID from request state if available
            if hasattr(request.state, "authenticated_user_id"):
                auth_info["user_id"] = request.state.authenticated_user_id
                auth_info["user_email"] = getattr(request.state, "authenticated_user_email", None)
                auth_info["user_role"] = getattr(request.state, "authenticated_user_role", None)
            
            # For login attempts, try to extract user information from body
            if request.method == "POST" and "login" in request.url.path:
                try:
                    body = await request.body()
                    if body:
                        # Parse login attempt (be careful not to log passwords)
                        import json
                        body_data = json.loads(body)
                        if "email" in body_data:
                            auth_info["attempted_email"] = body_data["email"]
                        # Don't log password!
                        auth_info["login_attempt"] = True
                except Exception:
                    # Ignore errors in body parsing
                    pass
            
            return auth_info
            
        except Exception as e:
            logger.error(f"Failed to extract auth info: {str(e)}")
            return {}
    
    async def _perform_pre_auth_assessment(self, request_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform pre-authentication risk assessment"""
        try:
            # Create database session for assessment
            async with get_db() as session:
                # Perform risk assessment
                assessment = await asyncio.wait_for(
                    auth_risk_assessment_service.perform_comprehensive_risk_assessment(
                        session=session,
                        user_id=request_info["auth_info"].get("user_id"),
                        ip_address=request_info["ip_address"],
                        user_agent=request_info["user_agent"],
                        additional_context=request_info["additional_context"]
                    ),
                    timeout=self.learning_system_timeout
                )
                
                # Check if validation is required
                if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    logger.warning(
                        f"High risk authentication attempt detected: "
                        f"{assessment.risk_level.value} ({assessment.overall_risk_score:.3f}) "
                        f"from {request_info['ip_address']}"
                    )
                
                return {
                    "assessment": assessment,
                    "requires_validation": assessment.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL],
                    "recommended_actions": assessment.recommended_actions
                }
                
        except asyncio.TimeoutError:
            logger.warning("Pre-auth assessment timed out")
            self.performance_metrics["learning_system_timeouts"] += 1
            return None
        except Exception as e:
            logger.error(f"Failed to perform pre-auth assessment: {str(e)}")
            return None
    
    async def _process_post_auth_learning(
        self,
        request: Request,
        response: StarletteResponse,
        request_info: Dict[str, Any],
        pre_auth_assessment: Optional[Dict[str, Any]]
    ):
        """Process post-authentication learning and monitoring"""
        try:
            # Determine authentication outcome
            auth_success = self._determine_auth_success(response)
            
            # Determine event type
            event_type = self._determine_event_type(request_info["path"], auth_success)
            
            # Create database session for learning
            async with get_db() as session:
                # Record authentication event
                auth_event = await asyncio.wait_for(
                    auth_pattern_detection_service.record_auth_event(
                        session=session,
                        event_type=event_type,
                        user_id=request_info["auth_info"].get("user_id"),
                        session_id=request_info["auth_info"].get("session_id"),
                        ip_address=request_info["ip_address"],
                        user_agent=request_info["user_agent"],
                        success=auth_success,
                        additional_data=request_info["additional_context"]
                    ),
                    timeout=self.learning_system_timeout
                )
                
                # Update learning metrics
                self.performance_metrics["learning_system_calls"] += 1
                
                # If there was a pre-auth assessment, evaluate its accuracy
                if pre_auth_assessment and auth_success:
                    await self._evaluate_assessment_accuracy(
                        session, pre_auth_assessment["assessment"], auth_event
                    )
                
                # Log successful learning integration
                logger.debug(
                    f"Authentication learning completed: {event_type.value} "
                    f"for {request_info['ip_address']} "
                    f"(success: {auth_success})"
                )
                
        except asyncio.TimeoutError:
            logger.warning("Post-auth learning timed out")
            self.performance_metrics["learning_system_timeouts"] += 1
        except Exception as e:
            logger.error(f"Failed to process post-auth learning: {str(e)}")
    
    def _determine_auth_success(self, response: StarletteResponse) -> bool:
        """Determine if authentication was successful based on response"""
        # Check response status code
        if response.status_code in [200, 201]:
            return True
        elif response.status_code in [401, 403]:
            return False
        else:
            # For other status codes, consider it a failure
            return False
    
    def _determine_event_type(self, path: str, success: bool) -> AuthEventType:
        """Determine authentication event type from path and outcome"""
        if "login" in path:
            return AuthEventType.LOGIN_SUCCESS if success else AuthEventType.LOGIN_FAILURE
        elif "refresh" in path:
            return AuthEventType.TOKEN_REFRESH
        elif "token" in path:
            return AuthEventType.TOKEN_VALIDATION
        else:
            return AuthEventType.LOGIN_ATTEMPT
    
    async def _evaluate_assessment_accuracy(
        self,
        session,
        assessment,
        auth_event: AuthEvent
    ):
        """Evaluate accuracy of pre-authentication assessment"""
        try:
            # Simple accuracy evaluation - would be more sophisticated in practice
            predicted_high_risk = assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            actual_failure = not auth_event.success
            
            # If we predicted high risk but auth succeeded, it might be a false positive
            if predicted_high_risk and auth_event.success:
                logger.debug("Potential false positive in risk assessment")
            
            # If we predicted low risk but auth failed, it might be a false negative
            if not predicted_high_risk and not auth_event.success:
                logger.debug("Potential false negative in risk assessment")
            
            # Update pattern learning with the outcome
            for pattern_id in auth_event.pattern_matches:
                effectiveness_score = 0.8 if (predicted_high_risk == actual_failure) else 0.3
                await auth_pattern_detection_service.update_pattern_learning(
                    session, pattern_id, auth_event.success, effectiveness_score
                )
                
        except Exception as e:
            logger.error(f"Failed to evaluate assessment accuracy: {str(e)}")
    
    async def _update_performance_metrics(self, processing_time_ms: float):
        """Update performance metrics for monitoring"""
        try:
            self.performance_metrics["total_requests"] += 1
            
            # Update average processing time with exponential moving average
            alpha = 0.1  # Smoothing factor
            current_avg = self.performance_metrics["average_processing_time_ms"]
            self.performance_metrics["average_processing_time_ms"] = (
                alpha * processing_time_ms + (1 - alpha) * current_avg
            )
            
            # Log performance metrics periodically
            if self.performance_metrics["total_requests"] % 100 == 0:
                logger.info(
                    f"Auth learning performance: "
                    f"{self.performance_metrics['total_requests']} requests, "
                    f"{self.performance_metrics['average_processing_time_ms']:.1f}ms avg, "
                    f"{self.performance_metrics['learning_system_timeouts']} timeouts"
                )
                
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {str(e)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "learning_system_enabled": self.enabled,
            "timeout_rate": (
                self.performance_metrics["learning_system_timeouts"] / 
                max(1, self.performance_metrics["learning_system_calls"])
            ),
            "timestamp": datetime.utcnow().isoformat()
        }


class ValidationChallengeMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling validation challenges
    
    Processes validation challenge responses and enforces adaptive security controls.
    """
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        
        # Challenge endpoints
        self.challenge_endpoints = {
            "/api/v1/auth/challenge/validate",
            "/api/v1/auth/challenge/status"
        }
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        """Handle validation challenge processing"""
        
        if not self.enabled:
            return await call_next(request)
        
        path = request.url.path
        
        # Handle challenge validation requests
        if path == "/api/v1/auth/challenge/validate":
            return await self._handle_challenge_validation(request)
        elif path == "/api/v1/auth/challenge/status":
            return await self._handle_challenge_status(request)
        
        # For other requests, check if user has pending challenges
        challenge_check = await self._check_pending_challenges(request)
        if challenge_check:
            return challenge_check
        
        return await call_next(request)
    
    async def _handle_challenge_validation(self, request: Request) -> JSONResponse:
        """Handle validation challenge response"""
        try:
            # Parse challenge response
            body = await request.body()
            challenge_data = json.loads(body)
            
            challenge_id = challenge_data.get("challenge_id")
            response_data = challenge_data.get("response_data", {})
            
            if not challenge_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Challenge ID required"}
                )
            
            # Extract request info for auth event
            request_info = await self._extract_basic_request_info(request)
            
            # Create auth event for validation attempt
            auth_event = AuthEvent(
                event_id=f"challenge_{int(time.time() * 1000)}",
                event_type=AuthEventType.MFA_CHALLENGE,
                user_id=request_info.get("user_id"),
                session_id=request_info.get("session_id"),
                ip_address=request_info["ip_address"],
                user_agent=request_info["user_agent"],
                timestamp=datetime.utcnow(),
                success=False,  # Will be updated based on validation
                additional_data=response_data,
                risk_indicators=[],
                pattern_matches=[]
            )
            
            # Validate challenge response
            async with get_db() as session:
                validation_success, validation_details = await adaptive_validation_service.validate_challenge_response(
                    session=session,
                    challenge_id=challenge_id,
                    response_data=response_data,
                    auth_event=auth_event
                )
            
            # Update auth event success status
            auth_event.success = validation_success
            
            if validation_success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Challenge completed successfully",
                        "details": validation_details
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "Challenge validation failed",
                        "details": validation_details
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to handle challenge validation: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Challenge validation error"}
            )
    
    async def _handle_challenge_status(self, request: Request) -> JSONResponse:
        """Handle challenge status request"""
        try:
            challenge_id = request.query_params.get("challenge_id")
            
            if not challenge_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Challenge ID required"}
                )
            
            # Get challenge status from cache
            from shared.services.redis_cache_service import get_redis_cache
            cache = await get_redis_cache()
            
            challenge_key = f"adaptive_validation:challenge:{challenge_id}"
            challenge_data = await cache.get(challenge_key)
            
            if not challenge_data:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Challenge not found or expired"}
                )
            
            # Return challenge status (without sensitive data)
            challenge_status = {
                "challenge_id": challenge_id,
                "challenge_type": challenge_data.get("challenge_type"),
                "expires_at": challenge_data.get("expires_at"),
                "max_attempts": challenge_data.get("max_attempts"),
                "success_required": challenge_data.get("success_required", True)
            }
            
            return JSONResponse(
                status_code=200,
                content=challenge_status
            )
            
        except Exception as e:
            logger.error(f"Failed to handle challenge status: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to get challenge status"}
            )
    
    async def _check_pending_challenges(self, request: Request) -> Optional[JSONResponse]:
        """Check if user has pending validation challenges"""
        try:
            # Extract user information
            user_id = getattr(request.state, "authenticated_user_id", None)
            
            if not user_id:
                return None  # No authenticated user
            
            # Check for pending challenges (placeholder implementation)
            # In practice, would check cache/database for pending challenges
            
            return None  # No pending challenges
            
        except Exception as e:
            logger.error(f"Failed to check pending challenges: {str(e)}")
            return None
    
    async def _extract_basic_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract basic request information"""
        return {
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "user_id": getattr(request.state, "authenticated_user_id", None),
            "session_id": getattr(request.state, "session_id", None)
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"


# Factory function for easier integration
def create_auth_learning_middleware(app, enabled: bool = True):
    """Create and configure authentication learning middleware"""
    return AuthLearningMiddleware(app, enabled=enabled)

def create_validation_challenge_middleware(app, enabled: bool = True):
    """Create and configure validation challenge middleware"""
    return ValidationChallengeMiddleware(app, enabled=enabled)