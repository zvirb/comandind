"""
Session Validation Normalizer Middleware

Standardizes session validation responses across all endpoints.
Handles circuit breaker failures gracefully and provides consistent error responses.
Supports degraded mode operations when Redis or other services are unavailable.
"""

import logging
import time
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import asyncio

from shared.services.jwt_token_adapter import jwt_token_adapter, normalize_request_token
from shared.services.redis_cache_service import redis_cache

logger = logging.getLogger(__name__)


class SessionValidationNormalizer:
    """
    Middleware for normalizing session validation across service boundaries.
    
    Features:
    - Unified session validation responses
    - Circuit breaker integration for Redis failures
    - Degraded mode operation during service outages
    - Consistent error response format
    - Performance monitoring and metrics
    """
    
    def __init__(self):
        self.circuit_breaker_failures = {}
        self.degraded_mode_active = False
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds
        
        # Response templates for consistency
        self.response_templates = {
            "unauthorized": {
                "error": "authentication_required",
                "message": "Valid authentication token required",
                "code": "AUTH_001",
                "degraded_mode": False
            },
            "forbidden": {
                "error": "access_forbidden", 
                "message": "Insufficient permissions for this resource",
                "code": "AUTH_002",
                "degraded_mode": False
            },
            "token_expired": {
                "error": "token_expired",
                "message": "Authentication token has expired",
                "code": "AUTH_003", 
                "degraded_mode": False
            },
            "service_degraded": {
                "error": "service_degraded",
                "message": "Authentication service operating in degraded mode",
                "code": "AUTH_004",
                "degraded_mode": True
            },
            "validation_error": {
                "error": "validation_failed",
                "message": "Session validation failed",
                "code": "AUTH_005",
                "degraded_mode": False
            }
        }
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through session validation normalization.
        """
        start_time = time.time()
        
        try:
            # Skip validation for public endpoints
            if self._is_public_endpoint(request.url.path):
                response = await call_next(request)
                return response
            
            # Check service health periodically
            await self._check_service_health()
            
            # Normalize and validate session
            validation_result = await self._validate_session(request)
            
            if not validation_result["valid"]:
                return self._create_error_response(validation_result)
            
            # Add normalized session info to request state
            request.state.normalized_session = validation_result["session_data"]
            request.state.session_format = validation_result["format_type"] 
            request.state.degraded_mode = self.degraded_mode_active
            
            # Process request
            response = await call_next(request)
            
            # Add session validation headers to response
            self._add_session_headers(response, validation_result)
            
            # Log performance metrics
            processing_time = time.time() - start_time
            logger.debug(f"Session validation completed in {processing_time:.3f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"Session validation middleware error: {e}")
            
            # Return consistent error response
            error_response = self.response_templates["validation_error"].copy()
            error_response["details"] = "Internal validation error"
            error_response["degraded_mode"] = self.degraded_mode_active
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response
            )
    
    async def _validate_session(self, request: Request) -> Dict[str, Any]:
        """
        Validate session with normalized error handling.
        
        Returns:
            Dict with validation result and normalized session data
        """
        try:
            # Extract and normalize token
            normalized_token = normalize_request_token(request)
            
            if not normalized_token:
                return {
                    "valid": False,
                    "error_type": "unauthorized",
                    "message": "No valid authentication token found"
                }
            
            # Check if token is expired (fast check)
            if jwt_token_adapter.is_token_expired(request.cookies.get("access_token", "") or 
                                                request.headers.get("authorization", "").replace("Bearer ", "")):
                return {
                    "valid": False,
                    "error_type": "token_expired",
                    "message": "Authentication token has expired"
                }
            
            # Validate session state with Redis (with circuit breaker)
            session_valid = await self._validate_redis_session(normalized_token)
            
            if session_valid or self.degraded_mode_active:
                return {
                    "valid": True,
                    "session_data": {
                        "user_id": normalized_token.user_id,
                        "email": normalized_token.email,
                        "role": normalized_token.role.value,
                        "format_type": normalized_token.format_type
                    },
                    "format_type": normalized_token.format_type,
                    "degraded_mode": self.degraded_mode_active
                }
            else:
                return {
                    "valid": False,
                    "error_type": "validation_error",
                    "message": "Session validation failed"
                }
                
        except Exception as e:
            logger.warning(f"Session validation error: {e}")
            
            # In degraded mode, allow JWT-only validation
            if self.degraded_mode_active:
                try:
                    normalized_token = normalize_request_token(request)
                    if normalized_token:
                        return {
                            "valid": True,
                            "session_data": {
                                "user_id": normalized_token.user_id,
                                "email": normalized_token.email,
                                "role": normalized_token.role.value,
                                "format_type": normalized_token.format_type
                            },
                            "format_type": normalized_token.format_type,
                            "degraded_mode": True
                        }
                except Exception:
                    pass
            
            return {
                "valid": False,
                "error_type": "validation_error",
                "message": f"Session validation failed: {str(e)}"
            }
    
    async def _validate_redis_session(self, normalized_token) -> bool:
        """
        Validate session against Redis with circuit breaker pattern.
        """
        try:
            # Check circuit breaker status
            if self._is_circuit_open("redis"):
                logger.debug("Redis circuit breaker open, skipping validation")
                return False
            
            # Attempt Redis validation
            session_key = f"session:{normalized_token.user_id}"
            
            # Use timeout for Redis operations
            session_data = await asyncio.wait_for(
                redis_cache.get(session_key),
                timeout=2.0  # 2 second timeout
            )
            
            if session_data:
                # Reset circuit breaker on success
                self._reset_circuit_breaker("redis")
                return True
            else:
                logger.debug(f"No Redis session found for user {normalized_token.user_id}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning("Redis session validation timeout")
            self._record_circuit_breaker_failure("redis")
            return False
        except Exception as e:
            logger.warning(f"Redis session validation failed: {e}")
            self._record_circuit_breaker_failure("redis")
            return False
    
    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for a service"""
        if service not in self.circuit_breaker_failures:
            return False
            
        failures = self.circuit_breaker_failures[service]
        failure_threshold = 5
        time_window = 60  # seconds
        
        # Remove old failures outside time window
        current_time = time.time()
        failures[:] = [f for f in failures if current_time - f < time_window]
        
        return len(failures) >= failure_threshold
    
    def _record_circuit_breaker_failure(self, service: str):
        """Record a circuit breaker failure"""
        if service not in self.circuit_breaker_failures:
            self.circuit_breaker_failures[service] = []
        
        self.circuit_breaker_failures[service].append(time.time())
        
        # Enable degraded mode if Redis is failing
        if service == "redis" and self._is_circuit_open("redis"):
            self.degraded_mode_active = True
            logger.warning("Enabling degraded mode due to Redis failures")
    
    def _reset_circuit_breaker(self, service: str):
        """Reset circuit breaker on successful operation"""
        if service in self.circuit_breaker_failures:
            self.circuit_breaker_failures[service].clear()
            
        # Disable degraded mode if Redis is working
        if service == "redis":
            self.degraded_mode_active = False
            logger.info("Disabling degraded mode - Redis operational")
    
    async def _check_service_health(self):
        """Periodically check service health to manage degraded mode"""
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return
            
        self.last_health_check = current_time
        
        # Test Redis connectivity
        try:
            await asyncio.wait_for(redis_cache.ping(), timeout=1.0)
            if self.degraded_mode_active:
                logger.info("Redis recovered - disabling degraded mode")
                self.degraded_mode_active = False
                self._reset_circuit_breaker("redis")
        except Exception:
            if not self.degraded_mode_active:
                logger.warning("Redis health check failed - enabling degraded mode")
                self.degraded_mode_active = True
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authentication"""
        public_paths = [
            "/health",
            "/api/health", 
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password",
            "/api/auth/verify-email",
            "/docs",
            "/openapi.json",
            "/static/",
            "/api/auth/csrf-token"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    def _create_error_response(self, validation_result: Dict[str, Any]) -> JSONResponse:
        """Create standardized error response"""
        error_type = validation_result.get("error_type", "validation_error")
        template = self.response_templates.get(error_type, self.response_templates["validation_error"])
        
        response_data = template.copy()
        response_data["details"] = validation_result.get("message", "Validation failed")
        response_data["degraded_mode"] = self.degraded_mode_active
        
        # Map error types to HTTP status codes
        status_map = {
            "unauthorized": status.HTTP_401_UNAUTHORIZED,
            "forbidden": status.HTTP_403_FORBIDDEN,
            "token_expired": status.HTTP_401_UNAUTHORIZED,
            "service_degraded": status.HTTP_503_SERVICE_UNAVAILABLE,
            "validation_error": status.HTTP_401_UNAUTHORIZED
        }
        
        return JSONResponse(
            status_code=status_map.get(error_type, status.HTTP_401_UNAUTHORIZED),
            content=response_data
        )
    
    def _add_session_headers(self, response: Response, validation_result: Dict[str, Any]):
        """Add session validation headers to response"""
        if validation_result.get("valid"):
            session_data = validation_result.get("session_data", {})
            response.headers["X-Session-Format"] = session_data.get("format_type", "unknown")
            response.headers["X-Session-Valid"] = "true"
            response.headers["X-Degraded-Mode"] = str(self.degraded_mode_active).lower()
        else:
            response.headers["X-Session-Valid"] = "false"
            response.headers["X-Degraded-Mode"] = str(self.degraded_mode_active).lower()


# Global middleware instance
session_validation_normalizer = SessionValidationNormalizer()