/**
 * Session Error Handler - Graceful degradation when session services are unavailable
 * Ensures the application remains functional even when session management fails
 */

import { SecureAuth } from './secureAuth';

class SessionErrorHandler {
  constructor() {
    this.serviceStatus = {
      sessionValidation: true,
      sessionInfo: true,
      sessionRefresh: true,
      lastChecked: null
    };
    this.fallbackMessages = new Map();
    this.retryCount = new Map();
    this.maxRetries = 3;
    this.checkInterval = 30000; // 30 seconds
  }

  /**
   * Handle session service errors with graceful degradation
   */
  async handleSessionServiceError(serviceName, error, fallbackAction = null) {
    console.warn(`SessionErrorHandler: ${serviceName} service error:`, error);
    
    // Update service status
    this.serviceStatus[serviceName] = false;
    this.serviceStatus.lastChecked = Date.now();
    
    // Get retry count
    const retries = this.retryCount.get(serviceName) || 0;
    
    // Determine error type and response
    const errorResponse = this.categorizeError(error, serviceName);
    
    // Handle based on error severity
    switch (errorResponse.severity) {
      case 'critical':
        return this.handleCriticalError(serviceName, error, fallbackAction);
      
      case 'recoverable':
        return this.handleRecoverableError(serviceName, error, retries, fallbackAction);
      
      case 'temporary':
        return this.handleTemporaryError(serviceName, error, retries, fallbackAction);
      
      default:
        return this.handleUnknownError(serviceName, error, fallbackAction);
    }
  }

  /**
   * Categorize error by type and severity
   */
  categorizeError(error, serviceName) {
    const errorMessage = error.message?.toLowerCase() || '';
    
    // Network/connectivity errors (temporary)
    if (errorMessage.includes('fetch') || 
        errorMessage.includes('network') || 
        errorMessage.includes('timeout') ||
        error.code === 'NETWORK_ERROR') {
      return {
        type: 'network',
        severity: 'temporary',
        message: 'Network connectivity issue'
      };
    }
    
    // Authentication errors (recoverable)
    if (errorMessage.includes('unauthorized') ||
        errorMessage.includes('authentication') ||
        error.status === 401) {
      return {
        type: 'authentication',
        severity: 'recoverable',
        message: 'Authentication required'
      };
    }
    
    // Server errors (temporary to recoverable)
    if (errorMessage.includes('server') ||
        error.status >= 500) {
      return {
        type: 'server',
        severity: 'temporary',
        message: 'Server temporarily unavailable'
      };
    }
    
    // Service unavailable (temporary)
    if (error.status === 503 ||
        errorMessage.includes('unavailable')) {
      return {
        type: 'service',
        severity: 'temporary',
        message: 'Service temporarily unavailable'
      };
    }
    
    // Unknown errors (critical)
    return {
      type: 'unknown',
      severity: 'critical',
      message: 'Unexpected error occurred'
    };
  }

  /**
   * Handle critical errors - require immediate fallback
   */
  async handleCriticalError(serviceName, error, fallbackAction) {
    console.error(`SessionErrorHandler: Critical error in ${serviceName}:`, error);
    
    // Store fallback message
    this.fallbackMessages.set(serviceName, {
      type: 'critical',
      message: `${serviceName} service is unavailable. Using fallback authentication.`,
      timestamp: Date.now(),
      canRetry: false
    });
    
    // Execute fallback if provided
    if (fallbackAction) {
      try {
        return await fallbackAction();
      } catch (fallbackError) {
        console.error(`SessionErrorHandler: Fallback action failed:`, fallbackError);
        return this.getMinimalFallback(serviceName);
      }
    }
    
    return this.getMinimalFallback(serviceName);
  }

  /**
   * Handle recoverable errors - attempt retry with fallback
   */
  async handleRecoverableError(serviceName, error, retries, fallbackAction) {
    console.warn(`SessionErrorHandler: Recoverable error in ${serviceName} (attempt ${retries + 1}):`, error);
    
    if (retries < this.maxRetries) {
      // Increment retry count
      this.retryCount.set(serviceName, retries + 1);
      
      // Store retry message
      this.fallbackMessages.set(serviceName, {
        type: 'recoverable',
        message: `${serviceName} experiencing issues. Retrying... (${retries + 1}/${this.maxRetries})`,
        timestamp: Date.now(),
        canRetry: true,
        retryCount: retries + 1
      });
      
      // Exponential backoff delay
      const delay = Math.pow(2, retries) * 1000;
      await this.sleep(delay);
      
      // Return retry indicator
      return {
        shouldRetry: true,
        delay,
        message: `Retrying ${serviceName} in ${delay}ms`
      };
    } else {
      // Max retries reached, fall back
      console.error(`SessionErrorHandler: Max retries reached for ${serviceName}`);
      return this.handleCriticalError(serviceName, error, fallbackAction);
    }
  }

  /**
   * Handle temporary errors - brief retry with degraded service
   */
  async handleTemporaryError(serviceName, error, retries, fallbackAction) {
    console.warn(`SessionErrorHandler: Temporary error in ${serviceName}:`, error);
    
    // Store temporary message
    this.fallbackMessages.set(serviceName, {
      type: 'temporary',
      message: `${serviceName} temporarily unavailable. Some features may be limited.`,
      timestamp: Date.now(),
      canRetry: true,
      retryCount: retries
    });
    
    // Quick retry for temporary issues
    if (retries < 2) {
      this.retryCount.set(serviceName, retries + 1);
      await this.sleep(2000); // 2 second delay for temporary errors
      
      return {
        shouldRetry: true,
        delay: 2000,
        message: `${serviceName} temporarily unavailable, retrying...`
      };
    }
    
    // Use fallback for persistent temporary errors
    if (fallbackAction) {
      try {
        const result = await fallbackAction();
        return {
          ...result,
          degraded: true,
          message: `Using fallback for ${serviceName}`
        };
      } catch (fallbackError) {
        return this.getMinimalFallback(serviceName);
      }
    }
    
    return this.getMinimalFallback(serviceName);
  }

  /**
   * Handle unknown errors
   */
  async handleUnknownError(serviceName, error, fallbackAction) {
    console.error(`SessionErrorHandler: Unknown error in ${serviceName}:`, error);
    
    this.fallbackMessages.set(serviceName, {
      type: 'unknown',
      message: `${serviceName} encountered an unexpected error. Please refresh the page.`,
      timestamp: Date.now(),
      canRetry: false
    });
    
    return this.getMinimalFallback(serviceName);
  }

  /**
   * Get minimal fallback response
   */
  getMinimalFallback(serviceName) {
    switch (serviceName) {
      case 'sessionValidation':
        return {
          valid: false,
          message: 'Session validation unavailable',
          fallback: true
        };
      
      case 'sessionInfo':
        return {
          user_id: null,
          email: null,
          role: null,
          message: 'Session info unavailable',
          fallback: true
        };
      
      case 'sessionRefresh':
        return {
          success: false,
          message: 'Session refresh unavailable',
          fallback: true
        };
      
      default:
        return {
          success: false,
          message: `${serviceName} unavailable`,
          fallback: true
        };
    }
  }

  /**
   * Check if service is available
   */
  isServiceAvailable(serviceName) {
    const status = this.serviceStatus[serviceName];
    const lastChecked = this.serviceStatus.lastChecked;
    
    // Consider service available if we haven't checked recently or status is true
    if (!lastChecked || (Date.now() - lastChecked) > this.checkInterval) {
      return true; // Optimistic availability
    }
    
    return status;
  }

  /**
   * Get current error messages for UI display
   */
  getActiveMessages() {
    const now = Date.now();
    const activeMessages = [];
    
    this.fallbackMessages.forEach((message, serviceName) => {
      // Show messages for last 5 minutes
      if (now - message.timestamp < 300000) {
        activeMessages.push({
          serviceName,
          ...message
        });
      }
    });
    
    return activeMessages;
  }

  /**
   * Clear error message for service
   */
  clearMessage(serviceName) {
    this.fallbackMessages.delete(serviceName);
    this.retryCount.delete(serviceName);
    this.serviceStatus[serviceName] = true;
  }

  /**
   * Reset all error states
   */
  reset() {
    this.fallbackMessages.clear();
    this.retryCount.clear();
    Object.keys(this.serviceStatus).forEach(key => {
      if (key !== 'lastChecked') {
        this.serviceStatus[key] = true;
      }
    });
  }

  /**
   * Sleep utility for delays
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get fallback authentication using legacy method
   */
  async getFallbackAuthentication() {
    try {
      console.log('SessionErrorHandler: Using fallback authentication');
      
      // Use legacy SecureAuth method
      const isAuth = await SecureAuth.isAuthenticated();
      
      if (isAuth) {
        const token = SecureAuth.getAuthToken();
        if (token) {
          try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return {
              valid: true,
              user_id: payload.id,
              email: payload.email,
              role: payload.role,
              expires_in_minutes: Math.floor((payload.exp - Date.now() / 1000) / 60),
              message: 'Fallback authentication successful',
              fallback: true
            };
          } catch (parseError) {
            console.warn('SessionErrorHandler: Could not parse token:', parseError);
          }
        }
        
        return {
          valid: true,
          message: 'Authenticated via fallback method',
          fallback: true
        };
      }
      
      return {
        valid: false,
        message: 'Not authenticated',
        fallback: true
      };
      
    } catch (error) {
      console.error('SessionErrorHandler: Fallback authentication failed:', error);
      return {
        valid: false,
        message: 'Authentication check failed',
        fallback: true
      };
    }
  }
}

// Create singleton instance
const sessionErrorHandler = new SessionErrorHandler();

export default sessionErrorHandler;
export { SessionErrorHandler };