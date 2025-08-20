/**
 * Authentication Loop Prevention Utilities
 * 
 * This module provides utilities to prevent rapid authentication API calls
 * that cause visual cycling and poor user experience.
 */

class AuthLoopPrevention {
  constructor() {
    this.requestTimestamps = new Map();
    this.defaultThrottleMs = 30000; // 30 seconds minimum between requests
    this.circuitBreakerThreshold = 3;
    this.circuitBreakerTimeout = 60000; // 1 minute
    this.failureCounts = new Map();
    this.circuitStates = new Map();
  }

  /**
   * Check if a request should be throttled
   * @param {string} requestKey - Unique identifier for the request type
   * @param {number} customThrottleMs - Custom throttle time in milliseconds
   * @returns {boolean} True if request should be blocked
   */
  shouldThrottle(requestKey, customThrottleMs = this.defaultThrottleMs) {
    const now = Date.now();
    const lastRequest = this.requestTimestamps.get(requestKey) || 0;
    const timeSinceLastRequest = now - lastRequest;
    
    // Check circuit breaker
    if (this.isCircuitOpen(requestKey)) {
      console.log(`AuthLoopPrevention: Circuit breaker open for ${requestKey}`);
      return true;
    }
    
    if (timeSinceLastRequest < customThrottleMs) {
      const remainingTime = Math.ceil((customThrottleMs - timeSinceLastRequest) / 1000);
      console.log(`AuthLoopPrevention: Throttling ${requestKey} - ${remainingTime}s remaining`);
      return true;
    }
    
    return false;
  }

  /**
   * Record a successful request
   * @param {string} requestKey - Unique identifier for the request type
   */
  recordSuccess(requestKey) {
    this.requestTimestamps.set(requestKey, Date.now());
    this.failureCounts.set(requestKey, 0);
    this.circuitStates.set(requestKey, { isOpen: false, openTime: null });
    console.log(`AuthLoopPrevention: Success recorded for ${requestKey}`);
  }

  /**
   * Record a failed request
   * @param {string} requestKey - Unique identifier for the request type
   */
  recordFailure(requestKey) {
    const failures = (this.failureCounts.get(requestKey) || 0) + 1;
    this.failureCounts.set(requestKey, failures);
    
    if (failures >= this.circuitBreakerThreshold) {
      this.circuitStates.set(requestKey, {
        isOpen: true,
        openTime: Date.now()
      });
      console.warn(`AuthLoopPrevention: Circuit breaker opened for ${requestKey} after ${failures} failures`);
    }
  }

  /**
   * Check if circuit breaker is open for a request type
   * @param {string} requestKey - Unique identifier for the request type
   * @returns {boolean} True if circuit is open
   */
  isCircuitOpen(requestKey) {
    const circuitState = this.circuitStates.get(requestKey);
    if (!circuitState || !circuitState.isOpen) {
      return false;
    }
    
    const now = Date.now();
    if (now - circuitState.openTime > this.circuitBreakerTimeout) {
      // Reset circuit breaker
      this.circuitStates.set(requestKey, { isOpen: false, openTime: null });
      this.failureCounts.set(requestKey, 0);
      console.log(`AuthLoopPrevention: Circuit breaker reset for ${requestKey}`);
      return false;
    }
    
    return true;
  }

  /**
   * Get remaining throttle time for a request
   * @param {string} requestKey - Unique identifier for the request type
   * @param {number} customThrottleMs - Custom throttle time in milliseconds
   * @returns {number} Remaining time in milliseconds
   */
  getRemainingThrottleTime(requestKey, customThrottleMs = this.defaultThrottleMs) {
    const now = Date.now();
    const lastRequest = this.requestTimestamps.get(requestKey) || 0;
    const timeSinceLastRequest = now - lastRequest;
    
    return Math.max(0, customThrottleMs - timeSinceLastRequest);
  }

  /**
   * Clear all throttling state (for testing or reset)
   */
  reset() {
    this.requestTimestamps.clear();
    this.failureCounts.clear();
    this.circuitStates.clear();
    console.log('AuthLoopPrevention: All state cleared');
  }

  /**
   * Get current status for debugging
   */
  getStatus() {
    return {
      activeThrottles: Array.from(this.requestTimestamps.entries()).map(([key, timestamp]) => ({
        key,
        lastRequestTime: new Date(timestamp).toISOString(),
        remainingThrottleMs: this.getRemainingThrottleTime(key)
      })),
      circuitBreakers: Array.from(this.circuitStates.entries()).map(([key, state]) => ({
        key,
        isOpen: state.isOpen,
        openTime: state.openTime ? new Date(state.openTime).toISOString() : null,
        failures: this.failureCounts.get(key) || 0
      }))
    };
  }
}

// Singleton instance
const authLoopPrevention = new AuthLoopPrevention();

export default authLoopPrevention;

// Common request keys for consistency
export const REQUEST_KEYS = {
  SESSION_VALIDATE: 'session_validate',
  AUTH_CHECK: 'auth_check',
  HEALTH_CHECK: 'health_check',
  SESSION_RESTORE: 'session_restore',
  TOKEN_REFRESH: 'token_refresh',
  DASHBOARD_DATA: 'dashboard_data'
};

/**
 * Helper function to wrap async functions with loop prevention
 * @param {string} requestKey - Unique identifier for the request type
 * @param {Function} requestFn - Async function to execute
 * @param {number} throttleMs - Custom throttle time in milliseconds
 * @returns {Promise} Result of requestFn or null if throttled
 */
export const withLoopPrevention = async (requestKey, requestFn, throttleMs) => {
  if (authLoopPrevention.shouldThrottle(requestKey, throttleMs)) {
    return null;
  }
  
  try {
    const result = await requestFn();
    authLoopPrevention.recordSuccess(requestKey);
    return result;
  } catch (error) {
    authLoopPrevention.recordFailure(requestKey);
    throw error;
  }
};