/**
 * Performance Testing and Benchmarking Utilities
 * Provides tools to measure and validate frontend performance optimizations
 */

import { globalAPIManager } from './performanceOptimizationEnhanced';

/**
 * Performance metrics collector
 */
export class PerformanceMetrics {
  constructor() {
    this.metrics = {
      renderTimes: [],
      apiFetchTimes: [],
      animationFrameRates: [],
      memoryUsage: [],
      domUpdateTimes: [],
      componentMountTimes: []
    };
    this.startTimes = new Map();
    this.observers = [];
    this.isCollecting = false;
  }

  /**
   * Start collecting performance metrics
   */
  startCollection() {
    this.isCollecting = true;
    this.setupPerformanceObservers();
    console.log('📊 Performance metrics collection started');
  }

  /**
   * Stop collecting metrics and return summary
   */
  stopCollection() {
    this.isCollecting = false;
    this.cleanupObservers();
    const summary = this.generateSummary();
    console.log('📊 Performance metrics collection stopped');
    return summary;
  }

  /**
   * Set up performance observers
   */
  setupPerformanceObservers() {
    // Observe paint timing
    if ('PerformanceObserver' in window) {
      try {
        const paintObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              this.metrics.renderTimes.push({
                type: 'FCP',
                time: entry.startTime,
                timestamp: Date.now()
              });
            }
          }
        });
        paintObserver.observe({ entryTypes: ['paint'] });
        this.observers.push(paintObserver);
      } catch (error) {
        console.warn('Paint observer not supported:', error);
      }

      // Observe navigation timing
      try {
        const navigationObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.metrics.renderTimes.push({
              type: 'navigation',
              domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
              loadComplete: entry.loadEventEnd - entry.loadEventStart,
              timestamp: Date.now()
            });
          }
        });
        navigationObserver.observe({ entryTypes: ['navigation'] });
        this.observers.push(navigationObserver);
      } catch (error) {
        console.warn('Navigation observer not supported:', error);
      }

      // Observe resource timing for API calls
      try {
        const resourceObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name.includes('/api/')) {
              this.metrics.apiFetchTimes.push({
                url: entry.name,
                duration: entry.duration,
                responseStart: entry.responseStart - entry.requestStart,
                timestamp: Date.now()
              });
            }
          }
        });
        resourceObserver.observe({ entryTypes: ['resource'] });
        this.observers.push(resourceObserver);
      } catch (error) {
        console.warn('Resource observer not supported:', error);
      }
    }

    // Monitor memory usage
    this.memoryMonitorInterval = setInterval(() => {
      if (this.isCollecting && 'memory' in performance) {
        this.metrics.memoryUsage.push({
          used: performance.memory.usedJSHeapSize,
          total: performance.memory.totalJSHeapSize,
          limit: performance.memory.jsHeapSizeLimit,
          timestamp: Date.now()
        });
      }
    }, 5000); // Every 5 seconds
  }

  /**
   * Clean up observers
   */
  cleanupObservers() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    
    if (this.memoryMonitorInterval) {
      clearInterval(this.memoryMonitorInterval);
    }
  }

  /**
   * Mark the start of a performance measurement
   * @param {string} label - Label for the measurement
   */
  markStart(label) {
    this.startTimes.set(label, performance.now());
  }

  /**
   * Mark the end of a performance measurement
   * @param {string} label - Label for the measurement
   * @param {string} category - Category of measurement
   */
  markEnd(label, category = 'general') {
    const startTime = this.startTimes.get(label);
    if (startTime) {
      const duration = performance.now() - startTime;
      
      switch (category) {
        case 'render':
          this.metrics.renderTimes.push({
            type: label,
            duration,
            timestamp: Date.now()
          });
          break;
        case 'api':
          this.metrics.apiFetchTimes.push({
            label,
            duration,
            timestamp: Date.now()
          });
          break;
        case 'animation':
          this.metrics.animationFrameRates.push({
            label,
            duration,
            fps: duration > 0 ? 1000 / duration : 0,
            timestamp: Date.now()
          });
          break;
        case 'component':
          this.metrics.componentMountTimes.push({
            component: label,
            duration,
            timestamp: Date.now()
          });
          break;
        default:
          this.metrics.domUpdateTimes.push({
            label,
            duration,
            timestamp: Date.now()
          });
      }
      
      this.startTimes.delete(label);
      
      if (this.isCollecting) {
        console.log(`⏱️ ${label} (${category}): ${duration.toFixed(2)}ms`);
      }
    }
  }

  /**
   * Record animation frame rate
   * @param {number} fps - Frames per second
   * @param {string} label - Animation label
   */
  recordFrameRate(fps, label = 'animation') {
    if (this.isCollecting) {
      this.metrics.animationFrameRates.push({
        label,
        fps,
        timestamp: Date.now()
      });
    }
  }

  /**
   * Generate performance summary
   */
  generateSummary() {
    const summary = {
      renderPerformance: this.analyzeRenderTimes(),
      apiPerformance: this.analyzeAPITimes(),
      animationPerformance: this.analyzeAnimationFrameRates(),
      memoryUsage: this.analyzeMemoryUsage(),
      componentPerformance: this.analyzeComponentTimes(),
      recommendations: []
    };

    // Generate recommendations
    summary.recommendations = this.generateRecommendations(summary);

    return summary;
  }

  /**
   * Analyze render times
   */
  analyzeRenderTimes() {
    if (this.metrics.renderTimes.length === 0) {
      return { average: 0, max: 0, min: 0, count: 0 };
    }

    const times = this.metrics.renderTimes.map(r => r.duration || r.time).filter(t => t > 0);
    return {
      average: times.reduce((a, b) => a + b, 0) / times.length,
      max: Math.max(...times),
      min: Math.min(...times),
      count: times.length,
      details: this.metrics.renderTimes
    };
  }

  /**
   * Analyze API call times
   */
  analyzeAPITimes() {
    if (this.metrics.apiFetchTimes.length === 0) {
      return { average: 0, max: 0, min: 0, count: 0 };
    }

    const times = this.metrics.apiFetchTimes.map(r => r.duration);
    return {
      average: times.reduce((a, b) => a + b, 0) / times.length,
      max: Math.max(...times),
      min: Math.min(...times),
      count: times.length,
      slowest: this.metrics.apiFetchTimes.reduce((prev, current) => 
        prev.duration > current.duration ? prev : current
      ),
      details: this.metrics.apiFetchTimes
    };
  }

  /**
   * Analyze animation frame rates
   */
  analyzeAnimationFrameRates() {
    if (this.metrics.animationFrameRates.length === 0) {
      return { average: 0, max: 0, min: 0, count: 0, target: 60 };
    }

    const frameRates = this.metrics.animationFrameRates.map(r => r.fps);
    const average = frameRates.reduce((a, b) => a + b, 0) / frameRates.length;
    
    return {
      average,
      max: Math.max(...frameRates),
      min: Math.min(...frameRates),
      count: frameRates.length,
      target: 60,
      performance: average >= 55 ? 'excellent' : average >= 45 ? 'good' : average >= 30 ? 'fair' : 'poor',
      details: this.metrics.animationFrameRates
    };
  }

  /**
   * Analyze memory usage
   */
  analyzeMemoryUsage() {
    if (this.metrics.memoryUsage.length === 0) {
      return { trend: 'unknown', peak: 0, average: 0 };
    }

    const usedMemory = this.metrics.memoryUsage.map(m => m.used);
    const average = usedMemory.reduce((a, b) => a + b, 0) / usedMemory.length;
    const peak = Math.max(...usedMemory);
    
    // Simple trend analysis
    const firstHalf = usedMemory.slice(0, Math.floor(usedMemory.length / 2));
    const secondHalf = usedMemory.slice(Math.floor(usedMemory.length / 2));
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    
    const trend = secondAvg > firstAvg * 1.1 ? 'increasing' : 
                  secondAvg < firstAvg * 0.9 ? 'decreasing' : 'stable';

    return {
      trend,
      peak,
      average,
      latest: usedMemory[usedMemory.length - 1],
      details: this.metrics.memoryUsage
    };
  }

  /**
   * Analyze component mount times
   */
  analyzeComponentTimes() {
    if (this.metrics.componentMountTimes.length === 0) {
      return { average: 0, max: 0, count: 0 };
    }

    const times = this.metrics.componentMountTimes.map(c => c.duration);
    return {
      average: times.reduce((a, b) => a + b, 0) / times.length,
      max: Math.max(...times),
      count: times.length,
      slowest: this.metrics.componentMountTimes.reduce((prev, current) => 
        prev.duration > current.duration ? prev : current
      ),
      details: this.metrics.componentMountTimes
    };
  }

  /**
   * Generate performance recommendations
   */
  generateRecommendations(summary) {
    const recommendations = [];

    // Render performance recommendations
    if (summary.renderPerformance.average > 100) {
      recommendations.push({
        category: 'Rendering',
        severity: 'high',
        message: `Average render time of ${summary.renderPerformance.average.toFixed(0)}ms is too high. Consider using React.memo or useMemo.`
      });
    }

    // API performance recommendations
    if (summary.apiPerformance.average > 1000) {
      recommendations.push({
        category: 'API',
        severity: 'medium',
        message: `Average API response time of ${summary.apiPerformance.average.toFixed(0)}ms is slow. Consider implementing request caching or timeout optimization.`
      });
    }

    // Animation performance recommendations
    if (summary.animationPerformance.average < 45) {
      recommendations.push({
        category: 'Animation',
        severity: 'high',
        message: `Animation FPS of ${summary.animationPerformance.average.toFixed(1)} is below target. Consider reducing animation complexity or enabling GPU acceleration.`
      });
    }

    // Memory usage recommendations
    if (summary.memoryUsage.trend === 'increasing') {
      recommendations.push({
        category: 'Memory',
        severity: 'medium',
        message: 'Memory usage is increasing over time. Check for memory leaks in event listeners or component cleanup.'
      });
    }

    // Component performance recommendations
    if (summary.componentPerformance.average > 50) {
      recommendations.push({
        category: 'Components',
        severity: 'medium',
        message: `Average component mount time of ${summary.componentPerformance.average.toFixed(0)}ms is high. Consider lazy loading or component optimization.`
      });
    }

    return recommendations;
  }

  /**
   * Export metrics data
   */
  exportData() {
    return {
      timestamp: Date.now(),
      metrics: this.metrics,
      summary: this.generateSummary()
    };
  }
}

/**
 * Performance testing suite for specific scenarios
 */
export class PerformanceTestSuite {
  constructor() {
    this.tests = new Map();
    this.results = [];
  }

  /**
   * Register a performance test
   * @param {string} name - Test name
   * @param {Function} testFunction - Test function
   * @param {Object} options - Test options
   */
  registerTest(name, testFunction, options = {}) {
    this.tests.set(name, {
      function: testFunction,
      options: {
        timeout: 30000,
        iterations: 1,
        warmup: 0,
        ...options
      }
    });
  }

  /**
   * Run all registered tests
   */
  async runAllTests() {
    const results = [];
    
    for (const [name, test] of this.tests) {
      console.log(`🧪 Running performance test: ${name}`);
      const result = await this.runTest(name, test);
      results.push(result);
    }
    
    this.results = results;
    return this.generateTestReport();
  }

  /**
   * Run a specific test
   */
  async runTest(name, test) {
    const metrics = new PerformanceMetrics();
    const startTime = performance.now();
    
    try {
      // Warmup runs
      for (let i = 0; i < test.options.warmup; i++) {
        await test.function();
      }
      
      metrics.startCollection();
      
      // Actual test runs
      const iterationResults = [];
      for (let i = 0; i < test.options.iterations; i++) {
        const iterationStart = performance.now();
        await test.function();
        const iterationEnd = performance.now();
        iterationResults.push(iterationEnd - iterationStart);
      }
      
      const summary = metrics.stopCollection();
      const totalTime = performance.now() - startTime;
      
      return {
        name,
        success: true,
        totalTime,
        averageIteration: iterationResults.reduce((a, b) => a + b, 0) / iterationResults.length,
        iterations: iterationResults,
        metrics: summary,
        timestamp: Date.now()
      };
      
    } catch (error) {
      metrics.stopCollection();
      return {
        name,
        success: false,
        error: error.message,
        timestamp: Date.now()
      };
    }
  }

  /**
   * Generate test report
   */
  generateTestReport() {
    const report = {
      totalTests: this.results.length,
      passedTests: this.results.filter(r => r.success).length,
      failedTests: this.results.filter(r => !r.success).length,
      results: this.results,
      summary: {},
      recommendations: []
    };

    // Generate summary statistics
    const successfulTests = this.results.filter(r => r.success);
    if (successfulTests.length > 0) {
      const totalTimes = successfulTests.map(r => r.totalTime);
      report.summary = {
        averageTestTime: totalTimes.reduce((a, b) => a + b, 0) / totalTimes.length,
        maxTestTime: Math.max(...totalTimes),
        minTestTime: Math.min(...totalTimes)
      };
    }

    return report;
  }
}

/**
 * Dashboard-specific performance tests
 */
export const dashboardPerformanceTests = {
  /**
   * Test dashboard loading performance
   */
  testDashboardLoad: async () => {
    const metrics = new PerformanceMetrics();
    metrics.markStart('dashboard-load');
    
    // Simulate dashboard data fetch
    try {
      const requests = [
        '/api/v1/dashboard',
        '/api/v1/performance_dashboard',
        '/api/v1/health'
      ];
      
      const startTime = performance.now();
      await Promise.allSettled(
        requests.map(url => 
          globalAPIManager.makeRequest(url, { method: 'GET' }, 10000)
        )
      );
      const endTime = performance.now();
      
      metrics.markEnd('dashboard-load', 'api');
      
      return {
        loadTime: endTime - startTime,
        requests: requests.length,
        success: true
      };
    } catch (error) {
      return {
        loadTime: 0,
        error: error.message,
        success: false
      };
    }
  },

  /**
   * Test animation performance
   */
  testAnimationPerformance: async () => {
    const metrics = new PerformanceMetrics();
    const frameRates = [];
    let frameCount = 0;
    const testDuration = 5000; // 5 seconds
    
    return new Promise((resolve) => {
      const startTime = performance.now();
      let lastFrameTime = startTime;
      
      const measureFrame = (currentTime) => {
        frameCount++;
        const frameTime = currentTime - lastFrameTime;
        const fps = frameTime > 0 ? 1000 / frameTime : 0;
        frameRates.push(fps);
        lastFrameTime = currentTime;
        
        if (currentTime - startTime < testDuration) {
          requestAnimationFrame(measureFrame);
        } else {
          const averageFPS = frameRates.reduce((a, b) => a + b, 0) / frameRates.length;
          resolve({
            averageFPS,
            minFPS: Math.min(...frameRates),
            maxFPS: Math.max(...frameRates),
            frameCount,
            testDuration,
            success: true
          });
        }
      };
      
      requestAnimationFrame(measureFrame);
    });
  }
};

/**
 * Create global performance monitoring instance
 */
export const globalPerformanceMonitor = new PerformanceMetrics();

/**
 * Utility to create performance test suite for components
 */
export const createComponentTestSuite = (componentName) => {
  const suite = new PerformanceTestSuite();
  
  suite.registerTest(`${componentName}-mount`, async () => {
    globalPerformanceMonitor.markStart(`${componentName}-mount`);
    // Component mounting would be tested here
    await new Promise(resolve => setTimeout(resolve, Math.random() * 100));
    globalPerformanceMonitor.markEnd(`${componentName}-mount`, 'component');
  });
  
  suite.registerTest(`${componentName}-render`, async () => {
    globalPerformanceMonitor.markStart(`${componentName}-render`);
    // Component rendering would be tested here
    await new Promise(resolve => setTimeout(resolve, Math.random() * 50));
    globalPerformanceMonitor.markEnd(`${componentName}-render`, 'render');
  });
  
  return suite;
};

// Auto-start performance monitoring in development
if (process.env.NODE_ENV === 'development') {
  console.log('🚀 Performance monitoring enabled for development');
  
  // Monitor page load performance
  window.addEventListener('load', () => {
    globalPerformanceMonitor.startCollection();
    
    // Stop collection after 2 minutes
    setTimeout(() => {
      const summary = globalPerformanceMonitor.stopCollection();
      console.log('📊 Performance Summary:', summary);
    }, 2 * 60 * 1000);
  });
}