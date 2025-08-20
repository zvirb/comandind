/**
 * Performance Test Runner
 * Automated performance testing and benchmarking
 */

class PerformanceTestRunner {
  constructor() {
    this.results = [];
    this.isRunning = false;
    this.testConfigs = {
      loadTest: {
        name: 'Page Load Performance',
        metrics: ['FCP', 'LCP', 'FID', 'CLS', 'TTFB'],
        iterations: 5
      },
      memoryTest: {
        name: 'Memory Usage Test',
        metrics: ['heapUsed', 'heapTotal', 'heapLimit'],
        duration: 30000 // 30 seconds
      },
      renderTest: {
        name: 'Component Render Performance',
        metrics: ['renderTime', 'componentCount', 'updateTime'],
        iterations: 100
      },
      apiTest: {
        name: 'API Performance Test',
        metrics: ['responseTime', 'cacheHitRatio', 'throughput'],
        iterations: 50
      },
      webglTest: {
        name: 'WebGL Performance Test',
        metrics: ['fps', 'drawCalls', 'triangles', 'memory'],
        duration: 10000 // 10 seconds
      }
    };
  }

  /**
   * Run comprehensive performance test suite
   */
  async runFullTestSuite() {
    if (this.isRunning) {
      console.warn('Performance test already running');
      return;
    }

    this.isRunning = true;
    this.results = [];
    
    console.log('🚀 Starting comprehensive performance test suite...');
    
    try {
      // Run all test types
      await this.runLoadTest();
      await this.runMemoryTest();
      await this.runRenderTest();
      await this.runAPITest();
      await this.runWebGLTest();
      
      // Generate comprehensive report
      const report = this.generateReport();
      console.log('📊 Performance test complete!');
      console.table(report.summary);
      
      return report;
      
    } catch (error) {
      console.error('Performance test failed:', error);
      throw error;
    } finally {
      this.isRunning = false;
    }
  }

  /**
   * Test page load performance
   */
  async runLoadTest() {
    console.log('Testing page load performance...');
    
    const results = [];
    const config = this.testConfigs.loadTest;
    
    for (let i = 0; i < config.iterations; i++) {
      const startTime = performance.now();
      
      // Simulate page navigation
      await this.simulatePageLoad();
      
      const metrics = await this.collectWebVitals();
      results.push({
        iteration: i + 1,
        ...metrics,
        totalTime: performance.now() - startTime
      });
      
      // Wait between iterations
      await this.delay(1000);
    }
    
    this.results.push({
      testName: config.name,
      results,
      summary: this.calculateSummary(results, ['FCP', 'LCP', 'TTFB'])
    });
  }

  /**
   * Test memory usage over time
   */
  async runMemoryTest() {
    console.log('Testing memory usage...');
    
    if (!performance.memory) {
      console.warn('Memory API not available');
      return;
    }
    
    const results = [];
    const config = this.testConfigs.memoryTest;
    const startTime = Date.now();
    
    while (Date.now() - startTime < config.duration) {
      const memory = performance.memory;
      results.push({
        timestamp: Date.now(),
        heapUsed: Math.round(memory.usedJSHeapSize / 1024 / 1024),
        heapTotal: Math.round(memory.totalJSHeapSize / 1024 / 1024),
        heapLimit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024),
        usage: Math.round((memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100)
      });
      
      await this.delay(1000);
    }
    
    this.results.push({
      testName: config.name,
      results,
      summary: this.calculateMemorySummary(results)
    });
  }

  /**
   * Test component render performance
   */
  async runRenderTest() {
    console.log('Testing component render performance...');
    
    const results = [];
    const config = this.testConfigs.renderTest;
    
    for (let i = 0; i < config.iterations; i++) {
      const startTime = performance.now();
      
      // Trigger a re-render
      await this.triggerRerender();
      
      const endTime = performance.now();
      results.push({
        iteration: i + 1,
        renderTime: endTime - startTime,
        componentCount: this.getComponentCount()
      });
      
      // Small delay to prevent overwhelming
      if (i % 10 === 0) {
        await this.delay(10);
      }
    }
    
    this.results.push({
      testName: config.name,
      results,
      summary: this.calculateSummary(results, ['renderTime'])
    });
  }

  /**
   * Test API performance with caching
   */
  async runAPITest() {
    console.log('Testing API performance...');
    
    const results = [];
    const config = this.testConfigs.apiTest;
    
    // Import API optimizer
    const apiOptimizer = (await import('./apiOptimizer.js')).default;
    
    for (let i = 0; i < config.iterations; i++) {
      const startTime = performance.now();
      
      try {
        // Make test API call
        await apiOptimizer.request({
          url: '/test-endpoint',
          method: 'GET',
          cache: true
        });
        
        const endTime = performance.now();
        const stats = apiOptimizer.getStats();
        
        results.push({
          iteration: i + 1,
          responseTime: endTime - startTime,
          cacheHitRatio: parseFloat(stats.cacheHitRatio),
          totalRequests: stats.totalRequests
        });
        
      } catch (error) {
        // Expected for test endpoint
        results.push({
          iteration: i + 1,
          responseTime: performance.now() - startTime,
          error: true
        });
      }
      
      await this.delay(50);
    }
    
    this.results.push({
      testName: config.name,
      results,
      summary: this.calculateSummary(results, ['responseTime'])
    });
  }

  /**
   * Test WebGL performance
   */
  async runWebGLTest() {
    console.log('Testing WebGL performance...');
    
    const results = [];
    const config = this.testConfigs.webglTest;
    
    // Import WebGL performance manager
    const webglManager = (await import('./webglPerformanceManager.js')).default;
    
    if (!webglManager.renderer) {
      console.warn('WebGL not initialized, skipping WebGL test');
      return;
    }
    
    const startTime = Date.now();
    
    while (Date.now() - startTime < config.duration) {
      const stats = webglManager.getStats();
      results.push({
        timestamp: Date.now(),
        fps: stats.fps,
        drawCalls: stats.drawCalls,
        triangles: stats.triangles,
        geometries: stats.memory.geometries,
        textures: stats.memory.textures
      });
      
      await this.delay(100);
    }
    
    this.results.push({
      testName: config.name,
      results,
      summary: this.calculateWebGLSummary(results)
    });
  }

  /**
   * Collect Web Vitals metrics
   */
  async collectWebVitals() {
    return new Promise((resolve) => {
      const metrics = {};
      
      // First Contentful Paint
      const paintEntries = performance.getEntriesByType('paint');
      const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
      metrics.FCP = fcpEntry ? Math.round(fcpEntry.startTime) : null;
      
      // Time to First Byte
      const navEntry = performance.getEntriesByType('navigation')[0];
      metrics.TTFB = navEntry ? Math.round(navEntry.responseStart - navEntry.requestStart) : null;
      
      // Largest Contentful Paint
      if ('PerformanceObserver' in window) {
        try {
          const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            metrics.LCP = lastEntry ? Math.round(lastEntry.startTime) : null;
            observer.disconnect();
            resolve(metrics);
          });
          observer.observe({ type: 'largest-contentful-paint', buffered: true });
          
          // Fallback timeout
          setTimeout(() => {
            observer.disconnect();
            resolve(metrics);
          }, 1000);
        } catch (e) {
          resolve(metrics);
        }
      } else {
        resolve(metrics);
      }
    });
  }

  /**
   * Simulate page load for testing
   */
  async simulatePageLoad() {
    // Force a layout recalculation
    document.body.offsetHeight;
    
    // Simulate async loading
    await this.delay(Math.random() * 100);
    
    // Trigger any lazy-loaded content
    window.dispatchEvent(new Event('scroll'));
    
    await this.delay(50);
  }

  /**
   * Trigger a component re-render
   */
  async triggerRerender() {
    // Dispatch a custom event that components might listen to
    window.dispatchEvent(new CustomEvent('performance-test-rerender'));
    
    // Force a layout
    document.body.offsetHeight;
    
    await this.delay(1);
  }

  /**
   * Get estimated component count
   */
  getComponentCount() {
    // Rough estimate based on DOM elements with React-like attributes
    return document.querySelectorAll('[data-reactroot], [data-react-component]').length +
           Math.floor(document.querySelectorAll('div, span, button, input').length / 3);
  }

  /**
   * Calculate summary statistics
   */
  calculateSummary(results, metrics) {
    const summary = {};
    
    metrics.forEach(metric => {
      const values = results.map(r => r[metric]).filter(v => v !== null && v !== undefined);
      if (values.length > 0) {
        summary[metric] = {
          min: Math.min(...values),
          max: Math.max(...values),
          avg: Math.round(values.reduce((a, b) => a + b, 0) / values.length),
          median: this.calculateMedian(values)
        };
      }
    });
    
    return summary;
  }

  /**
   * Calculate memory-specific summary
   */
  calculateMemorySummary(results) {
    const heapUsed = results.map(r => r.heapUsed);
    const usage = results.map(r => r.usage);
    
    return {
      heapUsed: {
        min: Math.min(...heapUsed),
        max: Math.max(...heapUsed),
        avg: Math.round(heapUsed.reduce((a, b) => a + b, 0) / heapUsed.length),
        final: heapUsed[heapUsed.length - 1]
      },
      usage: {
        min: Math.min(...usage),
        max: Math.max(...usage),
        avg: Math.round(usage.reduce((a, b) => a + b, 0) / usage.length),
        final: usage[usage.length - 1]
      }
    };
  }

  /**
   * Calculate WebGL-specific summary
   */
  calculateWebGLSummary(results) {
    const fps = results.map(r => r.fps).filter(f => f > 0);
    const drawCalls = results.map(r => r.drawCalls);
    const triangles = results.map(r => r.triangles);
    
    return {
      fps: {
        min: Math.min(...fps),
        max: Math.max(...fps),
        avg: Math.round(fps.reduce((a, b) => a + b, 0) / fps.length)
      },
      drawCalls: {
        min: Math.min(...drawCalls),
        max: Math.max(...drawCalls),
        avg: Math.round(drawCalls.reduce((a, b) => a + b, 0) / drawCalls.length)
      },
      triangles: {
        min: Math.min(...triangles),
        max: Math.max(...triangles),
        avg: Math.round(triangles.reduce((a, b) => a + b, 0) / triangles.length)
      }
    };
  }

  /**
   * Calculate median value
   */
  calculateMedian(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  /**
   * Generate comprehensive performance report
   */
  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {},
      details: this.results,
      recommendations: []
    };

    // Create summary table
    this.results.forEach(result => {
      report.summary[result.testName] = result.summary;
    });

    // Generate recommendations
    report.recommendations = this.generateRecommendations();

    // Performance score
    report.performanceScore = this.calculatePerformanceScore();

    return report;
  }

  /**
   * Generate performance recommendations
   */
  generateRecommendations() {
    const recommendations = [];
    
    this.results.forEach(result => {
      const { testName, summary } = result;
      
      if (testName.includes('Load') && summary.FCP && summary.FCP.avg > 2000) {
        recommendations.push({
          category: 'Loading',
          priority: 'high',
          message: `First Contentful Paint is ${summary.FCP.avg}ms (target: <1800ms). Consider code splitting and lazy loading.`
        });
      }
      
      if (testName.includes('Memory') && summary.usage && summary.usage.max > 80) {
        recommendations.push({
          category: 'Memory',
          priority: 'high',
          message: `Memory usage peaked at ${summary.usage.max}%. Consider implementing memory cleanup.`
        });
      }
      
      if (testName.includes('WebGL') && summary.fps && summary.fps.avg < 45) {
        recommendations.push({
          category: 'Rendering',
          priority: 'medium',
          message: `Average FPS is ${summary.fps.avg} (target: >50fps). Consider reducing scene complexity.`
        });
      }
      
      if (testName.includes('Render') && summary.renderTime && summary.renderTime.avg > 16) {
        recommendations.push({
          category: 'Rendering',
          priority: 'medium',
          message: `Component render time is ${summary.renderTime.avg}ms (target: <16ms). Consider React.memo and useMemo.`
        });
      }
    });
    
    return recommendations;
  }

  /**
   * Calculate overall performance score (0-100)
   */
  calculatePerformanceScore() {
    let score = 100;
    
    this.results.forEach(result => {
      const { testName, summary } = result;
      
      // Deduct points for poor performance
      if (testName.includes('Load') && summary.FCP && summary.FCP.avg > 2000) {
        score -= 20;
      }
      
      if (testName.includes('Memory') && summary.usage && summary.usage.max > 80) {
        score -= 15;
      }
      
      if (testName.includes('WebGL') && summary.fps && summary.fps.avg < 45) {
        score -= 15;
      }
      
      if (testName.includes('Render') && summary.renderTime && summary.renderTime.avg > 16) {
        score -= 10;
      }
    });
    
    return Math.max(0, Math.min(100, score));
  }

  /**
   * Utility delay function
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Export results to JSON
   */
  exportResults() {
    const report = this.generateReport();
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `performance-report-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Create singleton instance
const performanceTestRunner = new PerformanceTestRunner();

// Global access for debugging
if (typeof window !== 'undefined') {
  window.performanceTestRunner = performanceTestRunner;
}

export default performanceTestRunner;