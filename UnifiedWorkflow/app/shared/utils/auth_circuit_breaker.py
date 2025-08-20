"""
Authentication Circuit Breaker Utility
Prevents authentication refresh loop flooding through circuit breaker pattern.
"""

import time
import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit tripped, requests blocked
    HALF_OPEN = "half_open" # Testing single request to check recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for authentication circuit breaker."""
    failure_threshold: int = 3           # Failures before opening circuit
    recovery_timeout: int = 30           # Seconds to wait before trying again
    success_threshold: int = 1           # Successes in half-open to close circuit
    timeout: int = 10                    # Request timeout in seconds
    enable_performance_integration: bool = True  # Monitor WebGL/performance impact

@dataclass
class CircuitBreakerMetrics:
    """Metrics tracking for circuit breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    blocked_requests: int = 0
    circuit_open_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    webgl_context_lost_events: int = 0
    performance_triggered_pauses: int = 0

class AuthenticationCircuitBreaker:
    """
    Circuit breaker for authentication operations to prevent refresh loop flooding.
    
    Features:
    - CLOSED/OPEN/HALF_OPEN state management
    - WebGL performance integration
    - Automatic recovery with exponential backoff
    - Metrics collection for monitoring
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_request_time = None
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        
        # Performance monitoring
        self.performance_pause_until = None
        self.webgl_issues_detected = False
        
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result if circuit allows, raises CircuitBreakerOpen if blocked
            
        Raises:
            CircuitBreakerOpen: When circuit is open and requests are blocked
            CircuitBreakerTimeout: When request times out
        """
        async with self._lock:
            self.metrics.total_requests += 1
            
            # Check if performance pause is active
            if self._is_performance_paused():
                logger.debug("Circuit breaker paused due to performance issues")
                self.metrics.performance_triggered_pauses += 1
                raise CircuitBreakerPerformancePause("Authentication paused for performance recovery")
            
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if not self._should_attempt_reset():
                    self.metrics.blocked_requests += 1
                    raise CircuitBreakerOpen(f"Circuit breaker is OPEN. Blocking authentication requests.")
                else:
                    # Transition to half-open for testing
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN for recovery test")
            
            elif self.state == CircuitState.HALF_OPEN:
                # Only allow one request in half-open state
                if hasattr(self, '_half_open_request_active'):
                    self.metrics.blocked_requests += 1
                    raise CircuitBreakerOpen("Circuit breaker HALF_OPEN: test request already active")
                self._half_open_request_active = True
        
        try:
            # Execute the protected function with timeout
            start_time = time.time()
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.config.timeout
            )
            
            execution_time = time.time() - start_time
            logger.debug(f"Circuit breaker: Successful auth request in {execution_time:.2f}s")
            
            # Handle success
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Circuit breaker: Request timeout after {self.config.timeout}s")
            await self._on_failure("timeout")
            raise CircuitBreakerTimeout(f"Request timed out after {self.config.timeout} seconds")
            
        except Exception as e:
            logger.warning(f"Circuit breaker: Request failed with {type(e).__name__}: {e}")
            await self._on_failure(str(e))
            raise
            
        finally:
            # Clean up half-open request flag
            if hasattr(self, '_half_open_request_active'):
                delattr(self, '_half_open_request_active')
    
    async def _on_success(self):
        """Handle successful request."""
        async with self._lock:
            self.failure_count = 0
            self.success_count += 1
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
                    logger.info("Circuit breaker: Recovered! State changed to CLOSED")
    
    async def _on_failure(self, error_type: str):
        """Handle failed request."""
        async with self._lock:
            self.failure_count += 1
            self.success_count = 0
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = datetime.now()
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                if self.state != CircuitState.OPEN:
                    self.state = CircuitState.OPEN
                    self.metrics.circuit_open_count += 1
                    logger.warning(f"Circuit breaker: OPENED due to {self.failure_count} failures. "
                                 f"Latest: {error_type}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _is_performance_paused(self) -> bool:
        """Check if circuit breaker is paused due to performance issues."""
        if self.performance_pause_until is None:
            return False
        return time.time() < self.performance_pause_until
    
    def on_webgl_context_lost(self):
        """Handle WebGL context lost event to pause authentication."""
        if not self.config.enable_performance_integration:
            return
            
        self.webgl_issues_detected = True
        self.metrics.webgl_context_lost_events += 1
        # Pause authentication for 5 seconds during WebGL recovery
        self.performance_pause_until = time.time() + 5
        logger.warning("Circuit breaker: Pausing authentication due to WebGL context lost")
    
    def on_performance_issue(self, pause_duration: int = 3):
        """Handle general performance issues by pausing authentication."""
        if not self.config.enable_performance_integration:
            return
            
        self.performance_pause_until = time.time() + pause_duration
        logger.info(f"Circuit breaker: Pausing authentication for {pause_duration}s due to performance issue")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "is_performance_paused": self._is_performance_paused(),
            "webgl_issues_detected": self.webgl_issues_detected,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "blocked_requests": self.metrics.blocked_requests,
                "circuit_open_count": self.metrics.circuit_open_count,
                "webgl_context_lost_events": self.metrics.webgl_context_lost_events,
                "performance_triggered_pauses": self.metrics.performance_triggered_pauses,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "enable_performance_integration": self.config.enable_performance_integration,
            }
        }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.performance_pause_until = None
        self.webgl_issues_detected = False
        logger.info("Circuit breaker: Manually reset to CLOSED state")

# Exception classes
class CircuitBreakerException(Exception):
    """Base exception for circuit breaker errors."""
    pass

class CircuitBreakerOpen(CircuitBreakerException):
    """Raised when circuit breaker is open and blocking requests."""
    pass

class CircuitBreakerTimeout(CircuitBreakerException):
    """Raised when request times out."""
    pass

class CircuitBreakerPerformancePause(CircuitBreakerException):
    """Raised when circuit breaker is paused due to performance issues."""
    pass

# Global instance for authentication
auth_circuit_breaker = AuthenticationCircuitBreaker()

async def protected_auth_call(func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
    """
    Convenience function for making protected authentication calls.
    
    Usage:
        result = await protected_auth_call(some_auth_function, arg1, arg2)
    """
    return await auth_circuit_breaker.call(func, *args, **kwargs)

def get_auth_circuit_status() -> Dict[str, Any]:
    """Get current authentication circuit breaker status."""
    return auth_circuit_breaker.get_status()

def reset_auth_circuit():
    """Reset authentication circuit breaker."""
    auth_circuit_breaker.reset()

def notify_webgl_context_lost():
    """Notify circuit breaker of WebGL context lost event."""
    auth_circuit_breaker.on_webgl_context_lost()

def notify_performance_issue(pause_duration: int = 3):
    """Notify circuit breaker of performance issues."""
    auth_circuit_breaker.on_performance_issue(pause_duration)