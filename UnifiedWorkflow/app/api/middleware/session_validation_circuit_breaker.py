"""
Session Validation Circuit Breaker

Prevents infinite authentication loops by implementing circuit breaker pattern
specifically for session validation endpoints.
"""

import time
import logging
from typing import Dict, Optional
from enum import Enum
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class SessionValidationCircuitBreaker(BaseHTTPMiddleware):
    """
    Circuit breaker specifically for session validation endpoints.
    
    Prevents infinite authentication loops by:
    1. Tracking request frequency per client
    2. Opening circuit when too many requests from same client
    3. Returning cached responses for recently validated sessions
    """
    
    def __init__(
        self, 
        app,
        max_requests_per_client: int = 30,  # Max session validation requests per minute per client
        circuit_open_duration: int = 60,    # Keep circuit open for 60 seconds
        validation_cache_duration: int = 30  # Cache validation results for 30 seconds
    ):
        super().__init__(app)
        self.max_requests_per_client = max_requests_per_client
        self.circuit_open_duration = circuit_open_duration
        self.validation_cache_duration = validation_cache_duration
        
        # Circuit breaker state per client
        self.client_circuits: Dict[str, Dict] = {}
        # Validation result cache per client
        self.validation_cache: Dict[str, Dict] = {}
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use IP + User-Agent for client identification
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        return f"{client_ip}_{hash(user_agent)}"
    
    def _is_session_validation_endpoint(self, path: str) -> bool:
        """Check if this is a session validation endpoint."""
        return path in [
            "/api/v1/session/validate",
            "/api/session/validate",
            "/session/validate"
        ]
    
    def _get_circuit_state(self, client_id: str) -> CircuitState:
        """Get current circuit state for client."""
        if client_id not in self.client_circuits:
            self.client_circuits[client_id] = {
                "state": CircuitState.CLOSED,
                "request_count": 0,
                "last_reset": time.time(),
                "opened_at": None
            }
        
        circuit = self.client_circuits[client_id]
        current_time = time.time()
        
        # Reset request count every minute
        if current_time - circuit["last_reset"] >= 60:
            circuit["request_count"] = 0
            circuit["last_reset"] = current_time
            if circuit["state"] == CircuitState.OPEN:
                circuit["state"] = CircuitState.HALF_OPEN
        
        # Check if circuit should close after being open
        if circuit["state"] == CircuitState.OPEN and circuit["opened_at"]:
            if current_time - circuit["opened_at"] >= self.circuit_open_duration:
                circuit["state"] = CircuitState.HALF_OPEN
        
        return circuit["state"]
    
    def _increment_request_count(self, client_id: str) -> None:
        """Increment request count and update circuit state."""
        circuit = self.client_circuits[client_id]
        circuit["request_count"] += 1
        
        # Open circuit if too many requests
        if circuit["request_count"] > self.max_requests_per_client:
            if circuit["state"] != CircuitState.OPEN:
                logger.warning(f"Opening circuit breaker for client {client_id}: {circuit['request_count']} requests/minute")
                circuit["state"] = CircuitState.OPEN
                circuit["opened_at"] = time.time()
    
    def _get_cached_validation(self, client_id: str) -> Optional[Dict]:
        """Get cached validation result if available and valid."""
        if client_id not in self.validation_cache:
            return None
        
        cache_entry = self.validation_cache[client_id]
        current_time = time.time()
        
        if current_time - cache_entry["timestamp"] > self.validation_cache_duration:
            # Cache expired
            del self.validation_cache[client_id]
            return None
        
        return cache_entry["response"]
    
    def _cache_validation(self, client_id: str, response_data: Dict) -> None:
        """Cache validation response."""
        self.validation_cache[client_id] = {
            "response": response_data,
            "timestamp": time.time()
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through circuit breaker."""
        
        # Only apply to session validation endpoints
        if not self._is_session_validation_endpoint(request.url.path):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        circuit_state = self._get_circuit_state(client_id)
        
        # Check for cached validation first
        cached_response = self._get_cached_validation(client_id)
        if cached_response:
            logger.debug(f"Returning cached session validation for client {client_id}")
            response = JSONResponse(content=cached_response)
            response.headers["X-Circuit-Breaker"] = "cache-hit"
            response.headers["Cache-Control"] = "private, max-age=30"
            return response
        
        # Handle circuit breaker states
        if circuit_state == CircuitState.OPEN:
            # Circuit is open - return cached response or failure
            logger.warning(f"Circuit breaker OPEN for client {client_id} - blocking session validation")
            
            # Try to return last known good validation if available
            if client_id in self.validation_cache:
                cache_entry = self.validation_cache[client_id]
                # Return even expired cache during circuit open
                response_data = cache_entry["response"].copy()
                response_data["message"] = "Using cached validation (circuit breaker active)"
                
                response = JSONResponse(content=response_data)
                response.headers["X-Circuit-Breaker"] = "open-cached"
                response.headers["Cache-Control"] = "private, max-age=60"
                return response
            
            # No cache available - return generic valid response to prevent frontend loops
            response_data = {
                "valid": True,
                "message": "Session validation temporarily limited (circuit breaker active)",
                "circuit_breaker": "active"
            }
            
            response = JSONResponse(content=response_data)
            response.headers["X-Circuit-Breaker"] = "open-fallback"
            response.headers["Cache-Control"] = "private, max-age=60"
            return response
        
        # Increment request count for rate limiting
        self._increment_request_count(client_id)
        
        # Process request normally
        try:
            response = await call_next(request)
            
            # Cache successful validation responses
            if response.status_code == 200:
                # Read response content to cache it
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                try:
                    import json
                    response_data = json.loads(response_body.decode())
                    
                    # Only cache successful validations
                    if response_data.get("valid", False):
                        self._cache_validation(client_id, response_data)
                        logger.debug(f"Cached session validation for client {client_id}")
                        
                except Exception as e:
                    logger.debug(f"Could not cache response: {e}")
                
                # Recreate response with cached body
                new_response = JSONResponse(content=json.loads(response_body.decode()))
                new_response.headers.update(response.headers)
                new_response.headers["X-Circuit-Breaker"] = f"closed-{circuit_state.value}"
                return new_response
            
            # Mark circuit state in response headers
            response.headers["X-Circuit-Breaker"] = f"closed-{circuit_state.value}"
            return response
            
        except Exception as e:
            logger.error(f"Session validation error for client {client_id}: {e}")
            
            # Return cached response if available during errors
            if client_id in self.validation_cache:
                cache_entry = self.validation_cache[client_id]
                response_data = cache_entry["response"].copy()
                response_data["message"] = "Using cached validation (service error)"
                
                response = JSONResponse(content=response_data)
                response.headers["X-Circuit-Breaker"] = "error-cached"
                return response
            
            # No cache - return generic error
            response_data = {
                "valid": False,
                "message": "Session validation service temporarily unavailable"
            }
            
            response = JSONResponse(content=response_data, status_code=503)
            response.headers["X-Circuit-Breaker"] = "error-fallback"
            return response