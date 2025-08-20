/**
 * Advanced Request Debouncer and Rate Limiter
 * Prevents rapid API requests and implements proper interval management
 */

export class RequestDebouncer {
  constructor(options = {}) {
    this.options = {
      minimumInterval: options.minimumInterval || 1000, // Minimum 1 second between requests
      maxConcurrentRequests: options.maxConcurrentRequests || 3,
      requestTimeout: options.requestTimeout || 10000,
      enableAggressiveDebouncing: options.enableAggressiveDebouncing !== false,
      ...options
    };

    // Request tracking
    this.activeRequests = new Map();
    this.requestHistory = new Map();
    this.requestCounters = new Map();
    this.lastRequestTimes = new Map();
    
    // Debouncing
    this.debouncedRequests = new Map();
    this.requestQueue = [];
    
    // Rate limiting
    this.rateLimitWindows = new Map();
    this.rateLimitCounters = new Map();
    
    // Circuit breaker
    this.circuitBreakers = new Map();
    
    console.log('RequestDebouncer initialized with aggressive anti-loop protection');
  }

  /**
   * Create a debounced request function for a specific endpoint
   */
  createDebouncedRequest(endpoint, customOptions = {}) {
    const options = { ...this.options, ...customOptions };
    const requestKey = this.getRequestKey(endpoint, options.method || 'GET');
    
    return async (requestConfig = {}) => {
      // Check circuit breaker
      if (this.isCircuitBreakerOpen(requestKey)) {
        console.warn(`Request circuit breaker open for ${requestKey}`);
        throw new Error(`Circuit breaker open for ${requestKey}`);
      }

      // Aggressive interval checking
      const now = Date.now();
      const lastRequestTime = this.lastRequestTimes.get(requestKey) || 0;
      const timeSinceLastRequest = now - lastRequestTime;
      
      if (timeSinceLastRequest < options.minimumInterval) {
        const waitTime = options.minimumInterval - timeSinceLastRequest;
        console.log(`RequestDebouncer: Enforcing ${waitTime}ms wait for ${requestKey}`);
        
        if (options.enableAggressiveDebouncing) {
          // Return existing promise if available, otherwise wait
          const existingPromise = this.activeRequests.get(requestKey);
          if (existingPromise) {
            console.log(`RequestDebouncer: Returning existing promise for ${requestKey}`);
            return existingPromise;
          }
          
          // Force wait for minimum interval
          await this.delay(waitTime);
        }
      }

      // Check rate limits
      if (this.isRateLimited(requestKey, options)) {
        console.warn(`Rate limit exceeded for ${requestKey}`);
        throw new Error(`Rate limit exceeded for ${requestKey}`);
      }

      // Execute request with deduplication
      return this.executeRequest(requestKey, endpoint, requestConfig, options);
    };
  }

  /**
   * Execute request with full protection
   */
  async executeRequest(requestKey, endpoint, requestConfig, options) {
    // Check for existing active request (deduplication)
    if (this.activeRequests.has(requestKey)) {
      console.log(`RequestDebouncer: Deduplicating request for ${requestKey}`);
      return this.activeRequests.get(requestKey);
    }

    // Create request promise
    const requestPromise = this.makeActualRequest(endpoint, requestConfig, options);
    
    // Track active request
    this.activeRequests.set(requestKey, requestPromise);
    this.lastRequestTimes.set(requestKey, Date.now());
    
    try {
      const result = await requestPromise;
      
      // Record successful request
      this.recordRequestSuccess(requestKey);
      
      return result;
      
    } catch (error) {
      // Record failed request
      this.recordRequestFailure(requestKey, error);
      throw error;
      
    } finally {
      // Clean up
      this.activeRequests.delete(requestKey);
    }
  }

  /**
   * Make the actual HTTP request
   */
  async makeActualRequest(endpoint, config, options) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.requestTimeout);

    try {
      const response = await fetch(endpoint, {
        method: config.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...config.headers
        },
        body: config.data ? JSON.stringify(config.data) : undefined,
        credentials: 'include',
        signal: controller.signal,
        ...config
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
      
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Check if circuit breaker is open
   */
  isCircuitBreakerOpen(requestKey) {
    const breaker = this.circuitBreakers.get(requestKey);
    if (!breaker) return false;
    
    if (breaker.isOpen && Date.now() < breaker.nextRetryTime) {
      return true;
    }
    
    if (breaker.isOpen && Date.now() >= breaker.nextRetryTime) {
      // Reset circuit breaker
      breaker.isOpen = false;
      breaker.failureCount = 0;
      console.log(`Circuit breaker reset for ${requestKey}`);
    }
    
    return false;
  }

  /**
   * Check rate limiting
   */
  isRateLimited(requestKey, options) {
    const now = Date.now();
    const windowSize = options.rateLimitWindow || 60000; // 1 minute window
    const maxRequests = options.maxRequestsPerWindow || 10;
    
    const window = this.rateLimitWindows.get(requestKey) || now;
    const counter = this.rateLimitCounters.get(requestKey) || 0;
    
    // Reset window if expired
    if (now - window >= windowSize) {
      this.rateLimitWindows.set(requestKey, now);
      this.rateLimitCounters.set(requestKey, 1);
      return false;
    }
    
    // Check if limit exceeded
    if (counter >= maxRequests) {
      return true;
    }
    
    // Increment counter
    this.rateLimitCounters.set(requestKey, counter + 1);
    return false;
  }

  /**
   * Record successful request
   */
  recordRequestSuccess(requestKey) {
    const breaker = this.circuitBreakers.get(requestKey) || {
      failureCount: 0,
      isOpen: false,
      nextRetryTime: null
    };
    
    breaker.failureCount = 0;
    breaker.isOpen = false;
    this.circuitBreakers.set(requestKey, breaker);
  }

  /**
   * Record failed request
   */
  recordRequestFailure(requestKey, error) {
    const breaker = this.circuitBreakers.get(requestKey) || {
      failureCount: 0,
      isOpen: false,
      nextRetryTime: null
    };
    
    breaker.failureCount += 1;
    
    // Open circuit breaker after 3 failures
    if (breaker.failureCount >= 3) {
      breaker.isOpen = true;
      breaker.nextRetryTime = Date.now() + (30000 * Math.pow(2, Math.min(breaker.failureCount - 3, 4))); // Max 8 minutes
      console.warn(`Circuit breaker opened for ${requestKey} after ${breaker.failureCount} failures`);
    }
    
    this.circuitBreakers.set(requestKey, breaker);
  }

  /**
   * Generate request key for deduplication
   */
  getRequestKey(endpoint, method = 'GET', params = null) {
    const paramString = params ? JSON.stringify(params) : '';
    return `${method.toUpperCase()}_${endpoint}_${paramString}`;
  }

  /**
   * Utility delay function
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      activeRequests: this.activeRequests.size,
      totalEndpoints: this.lastRequestTimes.size,
      circuitBreakersOpen: Array.from(this.circuitBreakers.values()).filter(b => b.isOpen).length,
      rateLimitedEndpoints: this.rateLimitCounters.size
    };
  }

  /**
   * Clear all state (for cleanup)
   */
  reset() {
    this.activeRequests.clear();
    this.requestHistory.clear();
    this.requestCounters.clear();
    this.lastRequestTimes.clear();
    this.debouncedRequests.clear();
    this.rateLimitWindows.clear();
    this.rateLimitCounters.clear();
    this.circuitBreakers.clear();
    console.log('RequestDebouncer reset');
  }
}

// Create singleton instance with aggressive anti-loop settings
const requestDebouncer = new RequestDebouncer({
  minimumInterval: 2000, // Minimum 2 seconds between identical requests
  maxRequestsPerWindow: 5, // Max 5 requests per minute per endpoint
  rateLimitWindow: 60000, // 1 minute window
  enableAggressiveDebouncing: true,
  requestTimeout: 8000
});

export default requestDebouncer;

// React hook for debounced requests
export const useDebouncedRequest = (endpoint, options = {}) => {
  const debouncedRequest = requestDebouncer.createDebouncedRequest(endpoint, options);
  
  return {
    request: debouncedRequest,
    stats: requestDebouncer.getStats()
  };
};

// Helper to create anti-loop fetch wrapper
export const createAntiLoopFetch = (endpoint, options = {}) => {
  return requestDebouncer.createDebouncedRequest(endpoint, {
    minimumInterval: 3000, // Even more aggressive for critical endpoints
    enableAggressiveDebouncing: true,
    ...options
  });
};