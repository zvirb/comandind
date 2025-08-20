/**
 * Frontend Authentication Circuit Breaker
 * Prevents authentication refresh loop flooding through circuit breaker pattern.
 */

// Circuit breaker states
const CircuitState = {
  CLOSED: 'closed',      // Normal operation
  OPEN: 'open',          // Circuit tripped, blocking requests
  HALF_OPEN: 'half_open' // Testing recovery
};

class AuthCircuitBreaker {
  constructor(config = {}) {
    this.config = {
      failureThreshold: config.failureThreshold || 3,
      recoveryTimeout: config.recoveryTimeout || 30000, // 30 seconds
      successThreshold: config.successThreshold || 1,
      timeout: config.timeout || 10000, // 10 seconds
      enablePerformanceIntegration: config.enablePerformanceIntegration !== false,
      ...config
    };
    
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.performancePauseUntil = null;
    this.webglIssuesDetected = false;
    
    // Metrics
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      blockedRequests: 0,
      circuitOpenCount: 0,
      webglContextLostEvents: 0,
      performanceTriggeredPauses: 0
    };
    
    // Set up WebGL context monitoring
    this.setupWebGLMonitoring();
  }
  
  /**
   * Execute function through circuit breaker protection
   */
  async call(func, ...args) {
    this.metrics.totalRequests++;
    
    // Check if performance pause is active
    if (this.isPerformancePaused()) {
      console.log('AuthCircuitBreaker: Paused due to performance issues');
      this.metrics.performanceTriggeredPauses++;
      throw new CircuitBreakerPerformancePause('Authentication paused for performance recovery');
    }
    
    // Check circuit state
    if (this.state === CircuitState.OPEN) {
      if (!this.shouldAttemptReset()) {
        this.metrics.blockedRequests++;
        throw new CircuitBreakerOpen(`Circuit breaker is OPEN. Blocking authentication requests.`);
      } else {
        // Transition to half-open for testing
        this.state = CircuitState.HALF_OPEN;
        console.log('AuthCircuitBreaker: Transitioning to HALF_OPEN for recovery test');
      }
    } else if (this.state === CircuitState.HALF_OPEN) {
      // Only allow one request in half-open state
      if (this.halfOpenRequestActive) {
        this.metrics.blockedRequests++;
        throw new CircuitBreakerOpen('Circuit breaker HALF_OPEN: test request already active');
      }
      this.halfOpenRequestActive = true;
    }
    
    try {
      // Execute the protected function with timeout
      const startTime = performance.now();
      const result = await this.executeWithTimeout(func, args);
      const executionTime = performance.now() - startTime;
      
      console.log(`AuthCircuitBreaker: Successful auth request in ${executionTime.toFixed(2)}ms`);
      
      // Handle success
      this.onSuccess();
      return result;
      
    } catch (error) {
      if (error.name === 'TimeoutError') {
        console.warn(`AuthCircuitBreaker: Request timeout after ${this.config.timeout}ms`);
        this.onFailure('timeout');
        throw new CircuitBreakerTimeout(`Request timed out after ${this.config.timeout} milliseconds`);
      } else {
        console.warn(`AuthCircuitBreaker: Request failed with ${error.constructor.name}: ${error.message}`);
        this.onFailure(error.message);
        throw error;
      }
    } finally {
      // Clean up half-open request flag
      this.halfOpenRequestActive = false;
    }
  }
  
  /**
   * Execute function with timeout
   */
  async executeWithTimeout(func, args) {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        const error = new Error('Request timeout');
        error.name = 'TimeoutError';
        reject(error);
      }, this.config.timeout);
      
      Promise.resolve(func(...args))
        .then(result => {
          clearTimeout(timeoutId);
          resolve(result);
        })
        .catch(error => {
          clearTimeout(timeoutId);
          reject(error);
        });
    });
  }
  
  /**
   * Handle successful request
   */
  onSuccess() {
    this.failureCount = 0;
    this.successCount++;
    this.metrics.successfulRequests++;
    
    if (this.state === CircuitState.HALF_OPEN) {
      if (this.successCount >= this.config.successThreshold) {
        this.state = CircuitState.CLOSED;
        this.successCount = 0;
        console.log('AuthCircuitBreaker: Recovered! State changed to CLOSED');
      }
    }
  }
  
  /**
   * Handle failed request
   */
  onFailure(errorType) {
    this.failureCount++;
    this.successCount = 0;
    this.metrics.failedRequests++;
    this.lastFailureTime = Date.now();
    
    if (this.failureCount >= this.config.failureThreshold) {
      if (this.state !== CircuitState.OPEN) {
        this.state = CircuitState.OPEN;
        this.metrics.circuitOpenCount++;
        console.warn(`AuthCircuitBreaker: OPENED due to ${this.failureCount} failures. Latest: ${errorType}`);
      }
    }
  }
  
  /**
   * Check if enough time has passed to attempt reset
   */
  shouldAttemptReset() {
    if (this.lastFailureTime === null) {
      return true;
    }
    return Date.now() - this.lastFailureTime >= this.config.recoveryTimeout;
  }
  
  /**
   * Check if circuit breaker is paused due to performance issues
   */
  isPerformancePaused() {
    if (this.performancePauseUntil === null) {
      return false;
    }
    return Date.now() < this.performancePauseUntil;
  }
  
  /**
   * Set up WebGL context monitoring
   */
  setupWebGLMonitoring() {
    if (!this.config.enablePerformanceIntegration) {
      return;
    }
    
    // Monitor for WebGL context lost events
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (gl) {
      canvas.addEventListener('webglcontextlost', (event) => {
        this.onWebGLContextLost();
        event.preventDefault();
      });
    }
    
    // Monitor for general performance issues
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach(entry => {
            // Check for long tasks that might indicate performance issues
            if (entry.entryType === 'longtask' && entry.duration > 100) {
              this.onPerformanceIssue(3); // 3 second pause
            }
          });
        });
        observer.observe({ entryTypes: ['longtask'] });
      } catch (e) {
        console.debug('AuthCircuitBreaker: PerformanceObserver not fully supported');
      }
    }
  }
  
  /**
   * Handle WebGL context lost event
   */
  onWebGLContextLost() {
    if (!this.config.enablePerformanceIntegration) {
      return;
    }
    
    this.webglIssuesDetected = true;
    this.metrics.webglContextLostEvents++;
    // Pause authentication for 5 seconds during WebGL recovery
    this.performancePauseUntil = Date.now() + 5000;
    console.warn('AuthCircuitBreaker: Pausing authentication due to WebGL context lost');
    
    // Notify backend if possible
    this.notifyBackendWebGLEvent();
  }
  
  /**
   * Handle general performance issues
   */
  onPerformanceIssue(pauseDuration = 3) {
    if (!this.config.enablePerformanceIntegration) {
      return;
    }
    
    this.performancePauseUntil = Date.now() + (pauseDuration * 1000);
    console.log(`AuthCircuitBreaker: Pausing authentication for ${pauseDuration}s due to performance issue`);
    
    // Notify backend if possible
    this.notifyBackendPerformanceIssue(pauseDuration);
  }
  
  /**
   * Notify backend of WebGL context lost event
   */
  async notifyBackendWebGLEvent() {
    try {
      await fetch('/api/v1/auth-circuit-breaker/notifications/webgl-context-lost', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          event_type: 'context_lost',
          timestamp: new Date().toISOString(),
          additional_info: 'Frontend WebGL monitoring detected context lost'
        })
      });
    } catch (error) {
      console.debug('AuthCircuitBreaker: Could not notify backend of WebGL event:', error);
    }
  }
  
  /**
   * Notify backend of performance issue
   */
  async notifyBackendPerformanceIssue(pauseDuration) {
    try {
      await fetch('/api/v1/auth-circuit-breaker/notifications/performance-issue', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          issue_type: 'long_task',
          severity: 'medium',
          pause_duration: pauseDuration,
          description: 'Frontend performance monitoring detected long task'
        })
      });
    } catch (error) {
      console.debug('AuthCircuitBreaker: Could not notify backend of performance issue:', error);
    }
  }
  
  /**
   * Get current circuit breaker status
   */
  getStatus() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      isPerformancePaused: this.isPerformancePaused(),
      webglIssuesDetected: this.webglIssuesDetected,
      metrics: { ...this.metrics },
      config: { ...this.config }
    };
  }
  
  /**
   * Manually reset circuit breaker
   */
  reset() {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = null;
    this.performancePauseUntil = null;
    this.webglIssuesDetected = false;
    console.log('AuthCircuitBreaker: Manually reset to CLOSED state');
  }
}

// Exception classes
class CircuitBreakerException extends Error {
  constructor(message) {
    super(message);
    this.name = 'CircuitBreakerException';
  }
}

class CircuitBreakerOpen extends CircuitBreakerException {
  constructor(message) {
    super(message);
    this.name = 'CircuitBreakerOpen';
  }
}

class CircuitBreakerTimeout extends CircuitBreakerException {
  constructor(message) {
    super(message);
    this.name = 'CircuitBreakerTimeout';
  }
}

class CircuitBreakerPerformancePause extends CircuitBreakerException {
  constructor(message) {
    super(message);
    this.name = 'CircuitBreakerPerformancePause';
  }
}

// Global instance for authentication
const authCircuitBreaker = new AuthCircuitBreaker();

/**
 * Convenience function for making protected authentication calls
 */
export const protectedAuthCall = async (func, ...args) => {
  return await authCircuitBreaker.call(func, ...args);
};

/**
 * Get current authentication circuit breaker status
 */
export const getAuthCircuitStatus = () => {
  return authCircuitBreaker.getStatus();
};

/**
 * Reset authentication circuit breaker
 */
export const resetAuthCircuit = () => {
  authCircuitBreaker.reset();
};

/**
 * Manually notify circuit breaker of WebGL context lost
 */
export const notifyWebGLContextLost = () => {
  authCircuitBreaker.onWebGLContextLost();
};

/**
 * Manually notify circuit breaker of performance issues
 */
export const notifyPerformanceIssue = (pauseDuration = 3) => {
  authCircuitBreaker.onPerformanceIssue(pauseDuration);
};

export {
  AuthCircuitBreaker,
  CircuitBreakerException,
  CircuitBreakerOpen,
  CircuitBreakerTimeout,
  CircuitBreakerPerformancePause,
  authCircuitBreaker
};