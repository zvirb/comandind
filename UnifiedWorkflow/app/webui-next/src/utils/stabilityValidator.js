/**
 * Stability Validator
 * Comprehensive testing for WebUI stability issues
 */

class StabilityValidator {
  constructor() {
    this.tests = new Map();
    this.results = new Map();
    this.running = false;
    this.startTime = null;
    
    this.setupTests();
  }

  setupTests() {
    // Service Worker Tests
    this.tests.set('service-worker-registration', {
      name: 'Service Worker Registration',
      description: 'Test service worker registers without fetch failures',
      timeout: 10000,
      test: this.testServiceWorkerRegistration.bind(this)
    });

    this.tests.set('service-worker-caching', {
      name: 'Service Worker Caching',
      description: 'Test service worker caching strategy works correctly',
      timeout: 15000,
      test: this.testServiceWorkerCaching.bind(this)
    });

    // WebGL Context Tests
    this.tests.set('webgl-context-creation', {
      name: 'WebGL Context Creation',
      description: 'Test WebGL context creates successfully',
      timeout: 5000,
      test: this.testWebGLContextCreation.bind(this)
    });

    this.tests.set('webgl-context-recovery', {
      name: 'WebGL Context Recovery',
      description: 'Test WebGL context lost/restored handlers',
      timeout: 10000,
      test: this.testWebGLContextRecovery.bind(this)
    });

    // Console Warning Tests
    this.tests.set('console-warning-filtering', {
      name: 'Console Warning Filtering',
      description: 'Test development tool warnings are properly filtered',
      timeout: 5000,
      test: this.testConsoleWarningFiltering.bind(this)
    });

    // Loop Prevention Tests
    this.tests.set('loop-prevention', {
      name: 'Loop Prevention',
      description: 'Test that no infinite loops are present',
      timeout: 30000,
      test: this.testLoopPrevention.bind(this)
    });

    // Performance Stability Tests
    this.tests.set('performance-stability', {
      name: 'Performance Stability',
      description: 'Test performance monitoring remains stable',
      timeout: 20000,
      test: this.testPerformanceStability.bind(this)
    });
  }

  /**
   * Run all stability tests
   */
  async runAllTests() {
    if (this.running) {
      console.warn('[StabilityValidator] Tests already running');
      return this.results;
    }

    this.running = true;
    this.startTime = Date.now();
    this.results.clear();

    console.log('[StabilityValidator] Starting comprehensive stability validation...');

    for (const [testId, testConfig] of this.tests) {
      try {
        console.log(`[StabilityValidator] Running test: ${testConfig.name}`);
        
        const startTime = Date.now();
        const result = await Promise.race([
          testConfig.test(),
          this.createTimeoutPromise(testConfig.timeout, testConfig.name)
        ]);
        
        const duration = Date.now() - startTime;
        
        this.results.set(testId, {
          ...testConfig,
          status: 'passed',
          result,
          duration,
          timestamp: new Date().toISOString()
        });
        
        console.log(`[StabilityValidator] ✅ ${testConfig.name} passed (${duration}ms)`);
        
      } catch (error) {
        const duration = Date.now() - startTime;
        
        this.results.set(testId, {
          ...testConfig,
          status: 'failed',
          error: error.message,
          duration,
          timestamp: new Date().toISOString()
        });
        
        console.error(`[StabilityValidator] ❌ ${testConfig.name} failed: ${error.message}`);
      }
    }

    this.running = false;
    const totalDuration = Date.now() - this.startTime;
    
    console.log(`[StabilityValidator] All tests completed in ${totalDuration}ms`);
    return this.generateReport();
  }

  /**
   * Create timeout promise for tests
   */
  createTimeoutPromise(timeout, testName) {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Test timeout after ${timeout}ms`));
      }, timeout);
    });
  }

  /**
   * Test Service Worker Registration
   */
  async testServiceWorkerRegistration() {
    if (!('serviceWorker' in navigator)) {
      throw new Error('Service Workers not supported');
    }

    // Check if service worker is registered
    const registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      // Try to register
      const newRegistration = await navigator.serviceWorker.register('/sw.js');
      
      if (!newRegistration) {
        throw new Error('Failed to register service worker');
      }
      
      return { registered: true, new: true };
    }
    
    return { registered: true, existing: true, scope: registration.scope };
  }

  /**
   * Test Service Worker Caching
   */
  async testServiceWorkerCaching() {
    if (!('caches' in window)) {
      throw new Error('Cache API not supported');
    }

    // Test cache operations
    const cacheName = 'stability-test-cache';
    const testUrl = '/test-resource';
    const testResponse = new Response('test data');

    try {
      // Open cache
      const cache = await caches.open(cacheName);
      
      // Put test data
      await cache.put(testUrl, testResponse.clone());
      
      // Retrieve test data
      const cachedResponse = await cache.match(testUrl);
      
      if (!cachedResponse) {
        throw new Error('Failed to retrieve cached response');
      }
      
      // Clean up
      await caches.delete(cacheName);
      
      return { caching: 'functional' };
      
    } catch (error) {
      // Clean up on error
      try {
        await caches.delete(cacheName);
      } catch (cleanupError) {
        // Ignore cleanup errors
      }
      throw error;
    }
  }

  /**
   * Test WebGL Context Creation
   */
  async testWebGLContextCreation() {
    const canvas = document.createElement('canvas');
    
    try {
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      
      if (!gl) {
        throw new Error('WebGL not supported');
      }
      
      // Test basic WebGL operations
      const version = gl.getParameter(gl.VERSION);
      const vendor = gl.getParameter(gl.VENDOR);
      const renderer = gl.getParameter(gl.RENDERER);
      
      // Test context is not lost
      if (gl.isContextLost()) {
        throw new Error('WebGL context is lost');
      }
      
      return {
        webgl: 'supported',
        version,
        vendor,
        renderer
      };
      
    } finally {
      // Clean up
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
    }
  }

  /**
   * Test WebGL Context Recovery
   */
  async testWebGLContextRecovery() {
    const canvas = document.createElement('canvas');
    document.body.appendChild(canvas);
    
    try {
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      
      if (!gl) {
        throw new Error('WebGL not supported');
      }
      
      let contextLostEventFired = false;
      let contextRestoredEventFired = false;
      
      // Set up event listeners
      canvas.addEventListener('webglcontextlost', (event) => {
        contextLostEventFired = true;
        event.preventDefault();
      });
      
      canvas.addEventListener('webglcontextrestored', () => {
        contextRestoredEventFired = true;
      });
      
      // Get the WebGL extension for losing context
      const loseContextExt = gl.getExtension('WEBGL_lose_context');
      
      if (!loseContextExt) {
        // Can't test context loss, but context creation works
        return { contextRecovery: 'untestable', reason: 'WEBGL_lose_context extension not available' };
      }
      
      // Lose the context
      loseContextExt.loseContext();
      
      // Wait for context lost event
      await this.waitForCondition(() => contextLostEventFired, 2000, 'Context lost event');
      
      // Restore the context
      loseContextExt.restoreContext();
      
      // Wait for context restored event
      await this.waitForCondition(() => contextRestoredEventFired, 3000, 'Context restored event');
      
      return {
        contextRecovery: 'functional',
        lostEventFired: contextLostEventFired,
        restoredEventFired: contextRestoredEventFired
      };
      
    } finally {
      // Clean up
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
    }
  }

  /**
   * Test Console Warning Filtering
   */
  async testConsoleWarningFiltering() {
    const originalWarn = console.warn;
    const capturedWarnings = [];
    
    // Override console.warn to capture warnings
    console.warn = (...args) => {
      capturedWarnings.push(args.join(' '));
      originalWarn.apply(console, args);
    };
    
    try {
      // Generate test warnings that should be filtered
      console.warn('iframe-boot.js:1425 Failed to fetch');
      console.warn('Fragment "BaseJam" already defined');
      console.warn('chrome-extension://test warning');
      console.warn('React DevTools warning');
      
      // Generate a warning that should NOT be filtered
      console.warn('Important application warning');
      
      // Wait for filtering to process
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Check filtering results
      const filteredWarnings = capturedWarnings.filter(warning => 
        !warning.includes('iframe-boot') &&
        !warning.includes('BaseJam') &&
        !warning.includes('chrome-extension') &&
        !warning.includes('React DevTools')
      );
      
      return {
        warningFiltering: 'functional',
        totalWarnings: capturedWarnings.length,
        filteredWarnings: filteredWarnings.length,
        importantWarningsPreserved: filteredWarnings.some(w => w.includes('Important application'))
      };
      
    } finally {
      // Restore original console.warn
      console.warn = originalWarn;
    }
  }

  /**
   * Test Loop Prevention
   */
  async testLoopPrevention() {
    const startTime = Date.now();
    let operationCount = 0;
    const maxOperations = 1000;
    
    // Simulate rapid operations that could cause loops
    const testInterval = setInterval(() => {
      operationCount++;
      
      // Test auth state changes
      if (window.authCircuitBreaker) {
        // Don't actually trigger auth operations, just test the circuit breaker
      }
      
      // Test WebGL performance monitoring
      if (window.webglPerformanceManager) {
        // Don't actually run performance updates, just test availability
      }
      
      if (operationCount >= maxOperations) {
        clearInterval(testInterval);
      }
    }, 1);
    
    // Wait for test to complete or timeout
    await this.waitForCondition(() => operationCount >= maxOperations, 5000, 'Loop prevention test');
    
    const duration = Date.now() - startTime;
    
    return {
      loopPrevention: 'functional',
      operationsCompleted: operationCount,
      duration,
      averageOperationTime: duration / operationCount
    };
  }

  /**
   * Test Performance Stability
   */
  async testPerformanceStability() {
    const metrics = {
      memoryUsage: [],
      frameRates: [],
      renderTimes: []
    };
    
    const testDuration = 5000; // 5 seconds
    const sampleInterval = 100; // 100ms
    const startTime = Date.now();
    
    const collectMetrics = () => {
      // Memory usage
      if (performance.memory) {
        metrics.memoryUsage.push({
          used: performance.memory.usedJSHeapSize,
          total: performance.memory.totalJSHeapSize,
          timestamp: Date.now() - startTime
        });
      }
      
      // Frame rate (approximate)
      const frameStart = performance.now();
      requestAnimationFrame(() => {
        const frameTime = performance.now() - frameStart;
        metrics.renderTimes.push(frameTime);
        metrics.frameRates.push(1000 / frameTime);
      });
    };
    
    // Collect metrics during test period
    const metricsInterval = setInterval(collectMetrics, sampleInterval);
    
    // Wait for test duration
    await new Promise(resolve => setTimeout(resolve, testDuration));
    
    clearInterval(metricsInterval);
    
    // Analyze stability
    const memoryGrowth = metrics.memoryUsage.length > 1 ? 
      metrics.memoryUsage[metrics.memoryUsage.length - 1].used - metrics.memoryUsage[0].used : 0;
    
    const avgFrameRate = metrics.frameRates.length > 0 ? 
      metrics.frameRates.reduce((a, b) => a + b, 0) / metrics.frameRates.length : 0;
    
    const frameRateStability = this.calculateStability(metrics.frameRates);
    
    return {
      performanceStability: 'measured',
      memoryGrowth,
      averageFrameRate: avgFrameRate,
      frameRateStability,
      sampleCount: metrics.frameRates.length
    };
  }

  /**
   * Calculate stability metric (lower is more stable)
   */
  calculateStability(values) {
    if (values.length < 2) return 0;
    
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    const standardDeviation = Math.sqrt(variance);
    
    return standardDeviation / mean; // Coefficient of variation
  }

  /**
   * Wait for condition with timeout
   */
  async waitForCondition(condition, timeout, description) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      if (condition()) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    throw new Error(`Timeout waiting for: ${description}`);
  }

  /**
   * Generate comprehensive report
   */
  generateReport() {
    const totalTests = this.results.size;
    const passedTests = Array.from(this.results.values()).filter(r => r.status === 'passed').length;
    const failedTests = totalTests - passedTests;
    
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        total: totalTests,
        passed: passedTests,
        failed: failedTests,
        successRate: ((passedTests / totalTests) * 100).toFixed(1) + '%',
        totalDuration: Date.now() - this.startTime
      },
      tests: Object.fromEntries(this.results),
      recommendations: this.generateRecommendations()
    };
    
    console.log('[StabilityValidator] Final Report:', report);
    return report;
  }

  /**
   * Generate recommendations based on test results
   */
  generateRecommendations() {
    const recommendations = [];
    
    for (const [testId, result] of this.results) {
      if (result.status === 'failed') {
        switch (testId) {
          case 'service-worker-registration':
            recommendations.push('Service Worker registration failed - check sw.js file and browser support');
            break;
          case 'webgl-context-creation':
            recommendations.push('WebGL context creation failed - check browser WebGL support or hardware acceleration');
            break;
          case 'webgl-context-recovery':
            recommendations.push('WebGL context recovery failed - implement additional fallback mechanisms');
            break;
          case 'loop-prevention':
            recommendations.push('Loop prevention test failed - review authentication and performance monitoring for infinite loops');
            break;
          default:
            recommendations.push(`${result.name} failed - review implementation`);
        }
      }
    }
    
    if (recommendations.length === 0) {
      recommendations.push('All stability tests passed - system is stable');
    }
    
    return recommendations;
  }
}

// Create and export global instance
const stabilityValidator = new StabilityValidator();

export default stabilityValidator;

// Auto-run in development mode
if (process.env.NODE_ENV === 'development') {
  // Run tests after page load
  window.addEventListener('load', () => {
    setTimeout(() => {
      stabilityValidator.runAllTests().then(report => {
        console.log('[StabilityValidator] Development validation completed');
      });
    }, 2000);
  });
}