/**
 * Authentication Loop Validation Test Suite
 * 
 * This script validates that the authentication loop fixes are working correctly
 * by monitoring API call frequency and preventing rapid successive calls.
 */

class AuthLoopValidator {
  constructor() {
    this.apiCallLog = [];
    this.maxApiCallsPerMinute = 5; // Maximum allowed auth calls per minute
    this.testDuration = 60000; // 1 minute test
    this.intervalId = null;
  }

  /**
   * Start monitoring authentication API calls
   */
  startMonitoring() {
    console.log('🔍 Starting authentication loop validation...');
    
    // Intercept fetch calls to monitor auth endpoints
    this.originalFetch = window.fetch;
    window.fetch = this.interceptFetch.bind(this);
    
    // Start periodic validation
    this.intervalId = setInterval(() => {
      this.validateApiCallFrequency();
    }, 10000); // Check every 10 seconds
    
    // Stop monitoring after test duration
    setTimeout(() => {
      this.stopMonitoring();
    }, this.testDuration);
  }

  /**
   * Intercept and log authentication-related API calls
   */
  interceptFetch(url, options = {}) {
    const isAuthCall = this.isAuthenticationCall(url);
    
    if (isAuthCall) {
      this.logApiCall(url, options);
    }
    
    return this.originalFetch(url, options);
  }

  /**
   * Check if URL is an authentication-related endpoint
   */
  isAuthenticationCall(url) {
    const authEndpoints = [
      '/api/v1/session/validate',
      '/api/v1/auth/validate',
      '/api/v1/auth/login',
      '/api/v1/auth/refresh',
      '/api/v1/dashboard',
      '/api/v1/health/integration'
    ];
    
    return authEndpoints.some(endpoint => url.includes(endpoint));
  }

  /**
   * Log API call with timestamp
   */
  logApiCall(url, options) {
    const timestamp = Date.now();
    const method = options.method || 'GET';
    
    this.apiCallLog.push({
      url,
      method,
      timestamp,
      time: new Date(timestamp).toISOString()
    });
    
    console.log(`📡 Auth API Call: ${method} ${url} at ${new Date(timestamp).toLocaleTimeString()}`);
  }

  /**
   * Validate that API call frequency is within acceptable limits
   */
  validateApiCallFrequency() {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;
    
    // Count calls in the last minute
    const recentCalls = this.apiCallLog.filter(call => call.timestamp > oneMinuteAgo);
    const callsPerMinute = recentCalls.length;
    
    console.log(`📊 Authentication API calls in last minute: ${callsPerMinute}/${this.maxApiCallsPerMinute}`);
    
    if (callsPerMinute > this.maxApiCallsPerMinute) {
      console.error('❌ AUTHENTICATION LOOP DETECTED! Too many API calls per minute:', callsPerMinute);
      this.reportLoopDetection(recentCalls);
    } else {
      console.log('✅ Authentication call frequency is within normal limits');
    }
    
    // Check for rapid successive calls (< 5 seconds apart)
    this.detectRapidCalls(recentCalls);
  }

  /**
   * Detect rapid successive calls to the same endpoint
   */
  detectRapidCalls(calls) {
    const rapidCallThreshold = 5000; // 5 seconds
    
    for (let i = 1; i < calls.length; i++) {
      const currentCall = calls[i];
      const previousCall = calls[i - 1];
      
      if (currentCall.url === previousCall.url) {
        const timeDiff = currentCall.timestamp - previousCall.timestamp;
        
        if (timeDiff < rapidCallThreshold) {
          console.warn(`⚠️ Rapid successive calls detected: ${currentCall.url} (${timeDiff}ms apart)`);
          console.warn('This indicates potential authentication loop behavior');
        }
      }
    }
  }

  /**
   * Report authentication loop detection with details
   */
  reportLoopDetection(recentCalls) {
    console.group('🚨 AUTHENTICATION LOOP DETECTION REPORT');
    console.log('Recent API calls:', recentCalls);
    
    // Group by endpoint
    const callsByEndpoint = recentCalls.reduce((acc, call) => {
      acc[call.url] = (acc[call.url] || 0) + 1;
      return acc;
    }, {});
    
    console.log('Calls by endpoint:', callsByEndpoint);
    
    // Calculate average time between calls
    if (recentCalls.length > 1) {
      const timeSpan = recentCalls[recentCalls.length - 1].timestamp - recentCalls[0].timestamp;
      const averageInterval = timeSpan / (recentCalls.length - 1);
      console.log(`Average time between calls: ${averageInterval.toFixed(0)}ms`);
    }
    
    console.groupEnd();
  }

  /**
   * Stop monitoring and restore original fetch
   */
  stopMonitoring() {
    console.log('🏁 Stopping authentication loop validation...');
    
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    
    if (this.originalFetch) {
      window.fetch = this.originalFetch;
    }
    
    this.generateReport();
  }

  /**
   * Generate final validation report
   */
  generateReport() {
    console.group('📋 AUTHENTICATION LOOP VALIDATION REPORT');
    
    const totalCalls = this.apiCallLog.length;
    const uniqueEndpoints = [...new Set(this.apiCallLog.map(call => call.url))];
    
    console.log(`Total authentication API calls: ${totalCalls}`);
    console.log(`Unique endpoints called: ${uniqueEndpoints.length}`);
    console.log('Endpoints:', uniqueEndpoints);
    
    if (totalCalls === 0) {
      console.log('✅ No authentication API calls detected during monitoring period');
      console.log('This suggests successful loop prevention or no authentication activity');
    } else if (totalCalls <= this.maxApiCallsPerMinute) {
      console.log('✅ Authentication call frequency is within acceptable limits');
      console.log('Loop prevention measures appear to be working correctly');
    } else {
      console.warn('⚠️ High authentication API call frequency detected');
      console.warn('Consider reviewing throttling and caching mechanisms');
    }
    
    // Timeline analysis
    if (this.apiCallLog.length > 1) {
      const firstCall = this.apiCallLog[0];
      const lastCall = this.apiCallLog[this.apiCallLog.length - 1];
      const totalTime = lastCall.timestamp - firstCall.timestamp;
      const callsPerSecond = totalCalls / (totalTime / 1000);
      
      console.log(`Timeline: ${new Date(firstCall.timestamp).toLocaleTimeString()} - ${new Date(lastCall.timestamp).toLocaleTimeString()}`);
      console.log(`Average calls per second: ${callsPerSecond.toFixed(2)}`);
    }
    
    console.groupEnd();
    
    return {
      totalCalls,
      uniqueEndpoints,
      apiCallLog: this.apiCallLog,
      passedValidation: totalCalls <= this.maxApiCallsPerMinute
    };
  }

  /**
   * Test specific scenarios that previously caused loops
   */
  testScenarios() {
    console.log('🧪 Testing authentication loop scenarios...');
    
    // Test 1: Rapid navigation
    console.log('Test 1: Rapid navigation simulation');
    setTimeout(() => {
      window.history.pushState({}, '', '/dashboard');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }, 1000);
    
    setTimeout(() => {
      window.history.pushState({}, '', '/chat');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }, 2000);
    
    setTimeout(() => {
      window.history.pushState({}, '', '/dashboard');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }, 3000);
    
    // Test 2: Component re-render simulation
    console.log('Test 2: Component re-render simulation');
    setTimeout(() => {
      const event = new Event('resize');
      window.dispatchEvent(event);
    }, 5000);
    
    console.log('Authentication loop scenarios initiated. Monitor output for results.');
  }
}

// Auto-start validation when script is loaded
if (typeof window !== 'undefined') {
  window.authLoopValidator = new AuthLoopValidator();
  
  // Add console commands for manual testing
  window.startAuthValidation = () => {
    window.authLoopValidator.startMonitoring();
  };
  
  window.testAuthScenarios = () => {
    window.authLoopValidator.testScenarios();
  };
  
  window.stopAuthValidation = () => {
    window.authLoopValidator.stopMonitoring();
  };
  
  console.log('🔧 Authentication Loop Validator loaded');
  console.log('Commands available:');
  console.log('  startAuthValidation() - Start monitoring');
  console.log('  testAuthScenarios() - Test problematic scenarios');
  console.log('  stopAuthValidation() - Stop monitoring and get report');
}

export default AuthLoopValidator;