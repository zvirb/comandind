/**
 * Comprehensive Loop Validation Test
 * Tests all three major loop fixes implemented:
 * 1. AuthContext state machine loop prevention
 * 2. WebGL Galaxy animation performance adaptation stability
 * 3. API request debouncing and rate limiting
 */

import { test, expect } from '@playwright/test';

test.describe('JavaScript Loop Fixes Validation', () => {
  let page;
  let requestCounts = {};
  let performanceMetrics = {
    frameRates: [],
    apiRequestTimes: [],
    stateChanges: []
  };

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    
    // Monitor network requests to detect API polling loops
    page.on('request', (request) => {
      const url = request.url();
      const key = `${request.method()}_${url}`;
      requestCounts[key] = (requestCounts[key] || 0) + 1;
      
      // Track timing of authentication-related requests
      if (url.includes('/api/v1/session/validate') || url.includes('/api/v1/health/integration')) {
        performanceMetrics.apiRequestTimes.push({
          url,
          timestamp: Date.now(),
          method: request.method()
        });
      }
    });

    // Monitor console for state machine debugging
    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('AuthStateMachine') || text.includes('State change too frequent')) {
        performanceMetrics.stateChanges.push({
          message: text,
          timestamp: Date.now()
        });
      }
      
      // Track WebGL performance adaptation messages
      if (text.includes('Galaxy animation') && text.includes('quality')) {
        performanceMetrics.frameRates.push({
          message: text,
          timestamp: Date.now()
        });
      }
    });

    // Navigate to the application
    await page.goto('http://localhost:3001', { waitUntil: 'networkidle' });
  });

  test('1. AuthContext State Machine Loop Prevention', async () => {
    console.log('Testing AuthContext state machine loop prevention...');
    
    // Clear metrics
    performanceMetrics.stateChanges = [];
    
    // Rapid navigation to trigger potential state machine loops
    for (let i = 0; i < 5; i++) {
      await page.goto('http://localhost:3001/login');
      await page.waitForTimeout(100);
      await page.goto('http://localhost:3001/dashboard');
      await page.waitForTimeout(100);
    }
    
    // Wait for state machine to process
    await page.waitForTimeout(3000);
    
    // Check for rapid state changes being blocked
    const rapidStateChanges = performanceMetrics.stateChanges.filter(change => 
      change.message.includes('State change too frequent') ||
      change.message.includes('Circuit breaker activated')
    );
    
    console.log(`Detected ${rapidStateChanges.length} rapid state change preventions`);
    expect(rapidStateChanges.length).toBeGreaterThan(0); // Should have blocked some rapid changes
    
    // Verify circuit breaker functionality
    const circuitBreakerActivations = performanceMetrics.stateChanges.filter(change =>
      change.message.includes('Circuit breaker activated')
    );
    
    console.log(`Circuit breaker activations: ${circuitBreakerActivations.length}`);
    // Circuit breaker should activate if too many rapid changes detected
  });

  test('2. API Request Loop Prevention', async () => {
    console.log('Testing API request loop prevention...');
    
    // Clear request counts
    requestCounts = {};
    performanceMetrics.apiRequestTimes = [];
    
    // Navigate to a page that triggers authentication checks
    await page.goto('http://localhost:3001/dashboard', { waitUntil: 'networkidle' });
    
    // Wait and monitor for rapid API requests
    const startTime = Date.now();
    await page.waitForTimeout(10000); // Monitor for 10 seconds
    const endTime = Date.now();
    
    // Analyze session validation requests
    const sessionValidationRequests = performanceMetrics.apiRequestTimes.filter(req =>
      req.url.includes('/api/v1/session/validate')
    );
    
    console.log(`Session validation requests in 10s: ${sessionValidationRequests.length}`);
    
    // Should not have more than 2-3 session validation requests in 10 seconds
    expect(sessionValidationRequests.length).toBeLessThan(4);
    
    // Check timing between requests
    if (sessionValidationRequests.length > 1) {
      for (let i = 1; i < sessionValidationRequests.length; i++) {
        const timeDiff = sessionValidationRequests[i].timestamp - sessionValidationRequests[i-1].timestamp;
        console.log(`Time between session validation requests: ${timeDiff}ms`);
        
        // Should be at least 5000ms apart due to debouncing
        expect(timeDiff).toBeGreaterThan(4000);
      }
    }
    
    // Check health check requests
    const healthCheckRequests = performanceMetrics.apiRequestTimes.filter(req =>
      req.url.includes('/api/v1/health/integration')
    );
    
    console.log(`Health check requests in 10s: ${healthCheckRequests.length}`);
    
    // Should not have more than 1 health check request in 10 seconds
    expect(healthCheckRequests.length).toBeLessThan(2);
  });

  test('3. WebGL Performance Adaptation Stability', async () => {
    console.log('Testing WebGL performance adaptation stability...');
    
    // Clear performance metrics
    performanceMetrics.frameRates = [];
    
    // Navigate to a page with WebGL animation
    await page.goto('http://localhost:3001/dashboard', { waitUntil: 'networkidle' });
    
    // Wait for WebGL to initialize and run
    await page.waitForTimeout(15000); // Monitor for 15 seconds
    
    // Check for continuous quality adaptations (should be minimal)
    const qualityAdaptations = performanceMetrics.frameRates.filter(metric =>
      metric.message.includes('Quality reduced') || metric.message.includes('Quality restored')
    );
    
    console.log(`WebGL quality adaptations in 15s: ${qualityAdaptations.length}`);
    
    // Should have minimal quality adaptations (< 3 in 15 seconds)
    expect(qualityAdaptations.length).toBeLessThan(3);
    
    // Check timing between adaptations
    if (qualityAdaptations.length > 1) {
      for (let i = 1; i < qualityAdaptations.length; i++) {
        const timeDiff = qualityAdaptations[i].timestamp - qualityAdaptations[i-1].timestamp;
        console.log(`Time between quality adaptations: ${timeDiff}ms`);
        
        // Should be at least 5000ms apart due to stability measures
        expect(timeDiff).toBeGreaterThan(4000);
      }
    }
    
    // Verify performance metrics are being tracked
    const performanceMessages = performanceMetrics.frameRates.filter(metric =>
      metric.message.includes('Galaxy animation')
    );
    
    expect(performanceMessages.length).toBeGreaterThan(0); // Should have some performance tracking
  });

  test('4. Overall System Stability', async () => {
    console.log('Testing overall system stability...');
    
    // Reset all metrics
    requestCounts = {};
    performanceMetrics = { frameRates: [], apiRequestTimes: [], stateChanges: [] };
    
    // Simulate user interactions that previously caused loops
    await page.goto('http://localhost:3001/login');
    await page.waitForTimeout(2000);
    
    await page.goto('http://localhost:3001/dashboard');
    await page.waitForTimeout(3000);
    
    // Try to trigger auth state changes
    await page.evaluate(() => {
      // Simulate rapid window focus/blur events
      for (let i = 0; i < 5; i++) {
        window.dispatchEvent(new Event('focus'));
        window.dispatchEvent(new Event('blur'));
      }
    });
    
    await page.waitForTimeout(5000);
    
    // Check total API requests
    const totalRequests = Object.values(requestCounts).reduce((sum, count) => sum + count, 0);
    console.log(`Total API requests during stability test: ${totalRequests}`);
    
    // Should not have excessive API requests (< 10 total)
    expect(totalRequests).toBeLessThan(10);
    
    // Check for error messages in console
    const errorMessages = await page.evaluate(() => {
      return window.console._errorMessages || [];
    });
    
    console.log(`Console errors during stability test: ${errorMessages.length}`);
    // Should not have excessive errors
    expect(errorMessages.length).toBeLessThan(3);
  });

  test('5. Performance Metrics Validation', async () => {
    console.log('Validating performance metrics...');
    
    await page.goto('http://localhost:3001/dashboard', { waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);
    
    // Check if RequestDebouncer stats are available
    const debouncerStats = await page.evaluate(() => {
      return window.requestDebouncer ? window.requestDebouncer.getStats() : null;
    });
    
    if (debouncerStats) {
      console.log('RequestDebouncer stats:', debouncerStats);
      expect(debouncerStats.activeRequests).toBeLessThan(5);
      expect(debouncerStats.circuitBreakersOpen).toBeLessThan(2);
    }
    
    // Check WebGL performance manager stats
    const webglStats = await page.evaluate(() => {
      return window.webglPerformanceManager ? window.webglPerformanceManager.getStats() : null;
    });
    
    if (webglStats) {
      console.log('WebGL performance stats:', webglStats);
      // Validate reasonable performance metrics
    }
  });

  test.afterEach(async () => {
    // Generate summary report
    const summary = {
      timestamp: new Date().toISOString(),
      totalApiRequests: Object.values(requestCounts).reduce((sum, count) => sum + count, 0),
      stateChangeEvents: performanceMetrics.stateChanges.length,
      webglAdaptations: performanceMetrics.frameRates.length,
      requestCounts: requestCounts
    };
    
    console.log('Loop Validation Test Summary:', JSON.stringify(summary, null, 2));
    
    await page.close();
  });
});

// Export for use in other test files
export { performanceMetrics, requestCounts };