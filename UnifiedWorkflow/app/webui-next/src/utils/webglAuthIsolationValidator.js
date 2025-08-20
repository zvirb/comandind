/**
 * WebGL-Authentication Isolation Validator
 * Validates that WebGL operations don't interfere with authentication flow
 */

class WebGLAuthIsolationValidator {
  constructor() {
    this.metrics = {
      authRequestCount: 0,
      webglEventCount: 0,
      reactRenderCount: 0,
      contextLostEvents: 0,
      performanceAdaptations: 0,
      interferenceDetected: false,
      lastAuthRequest: 0,
      lastWebglEvent: 0,
      consecutiveAuthRequests: 0,
      maxConsecutiveAuthRequests: 0
    };
    
    this.thresholds = {
      maxAuthRequestsPerMinute: 20,
      maxReactRendersPerMinute: 600,
      maxConsecutiveAuthRequests: 5,
      authRequestFloodWindow: 30000, // 30 seconds
      webglEventFloodWindow: 5000    // 5 seconds
    };
    
    this.monitoring = false;
    this.originalFetch = null;
    this.originalConsoleLog = null;
    this.mutationObserver = null;
    
    this.bindMethods();
  }
  
  bindMethods() {
    this.startMonitoring = this.startMonitoring.bind(this);
    this.stopMonitoring = this.stopMonitoring.bind(this);
    this.checkInterference = this.checkInterference.bind(this);
    this.generateReport = this.generateReport.bind(this);
  }
  
  /**
   * Start monitoring WebGL and authentication interactions
   */
  startMonitoring() {
    if (this.monitoring) {
      console.warn('WebGL-Auth isolation monitoring already active');
      return;
    }
    
    console.log('Starting WebGL-Authentication isolation monitoring...');
    this.monitoring = true;
    this.resetMetrics();
    
    // Monitor fetch requests for authentication patterns
    this.monitorFetchRequests();
    
    // Monitor console logs for WebGL events
    this.monitorConsoleOutput();
    
    // Monitor DOM mutations for React render patterns
    this.monitorDOMMutations();
    
    // Monitor WebGL-specific events
    this.monitorWebGLEvents();
    
    // Periodic interference checking
    this.interferenceCheckInterval = setInterval(() => {
      this.checkInterference();
    }, 10000); // Check every 10 seconds
  }
  
  /**
   * Stop monitoring and generate final report
   */
  stopMonitoring() {
    if (!this.monitoring) {
      console.warn('WebGL-Auth isolation monitoring not active');
      return null;
    }
    
    console.log('Stopping WebGL-Authentication isolation monitoring...');
    this.monitoring = false;
    
    // Restore original functions
    if (this.originalFetch) {
      window.fetch = this.originalFetch;
    }
    
    if (this.originalConsoleLog) {
      console.log = this.originalConsoleLog;
    }
    
    // Cleanup observers
    if (this.mutationObserver) {
      this.mutationObserver.disconnect();
    }
    
    if (this.interferenceCheckInterval) {
      clearInterval(this.interferenceCheckInterval);
    }
    
    return this.generateReport();
  }
  
  /**
   * Monitor fetch requests for authentication patterns
   */
  monitorFetchRequests() {
    this.originalFetch = window.fetch;
    
    window.fetch = (...args) => {
      const url = args[0];
      const now = Date.now();
      
      if (typeof url === 'string' && (
        url.includes('/api/v1/auth/') || 
        url.includes('/api/v1/session/') ||
        url.includes('/api/v1/health/')
      )) {
        this.metrics.authRequestCount++;
        
        // Check for consecutive auth requests (potential flooding)
        if (now - this.metrics.lastAuthRequest < 1000) { // Less than 1 second apart
          this.metrics.consecutiveAuthRequests++;
          this.metrics.maxConsecutiveAuthRequests = Math.max(
            this.metrics.maxConsecutiveAuthRequests,
            this.metrics.consecutiveAuthRequests
          );
        } else {
          this.metrics.consecutiveAuthRequests = 0;
        }
        
        this.metrics.lastAuthRequest = now;
        
        console.log(`[ISOLATION-MONITOR] Auth request: ${url} (consecutive: ${this.metrics.consecutiveAuthRequests})`);
      }
      
      return this.originalFetch.apply(this, args);
    };
  }
  
  /**
   * Monitor console output for WebGL events
   */
  monitorConsoleOutput() {
    this.originalConsoleLog = console.log;
    
    console.log = (...args) => {
      const message = args.join(' ');
      const now = Date.now();
      
      // Track WebGL-related console messages
      if (message.includes('WebGL') || 
          message.includes('Galaxy animation') || 
          message.includes('Performance Manager') ||
          message.includes('context lost') ||
          message.includes('Performance level')) {
        
        this.metrics.webglEventCount++;
        this.metrics.lastWebglEvent = now;
        
        if (message.includes('Performance level')) {
          this.metrics.performanceAdaptations++;
        }
        
        if (message.includes('context lost')) {
          this.metrics.contextLostEvents++;
        }
        
        console.log(`[ISOLATION-MONITOR] WebGL event: ${message}`);
      }
      
      return this.originalConsoleLog.apply(this, args);
    };
  }
  
  /**
   * Monitor DOM mutations for React render patterns
   */
  monitorDOMMutations() {
    this.mutationObserver = new MutationObserver((mutations) => {
      this.metrics.reactRenderCount += mutations.length;
    });
    
    this.mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: false
    });
  }
  
  /**
   * Monitor WebGL-specific events
   */
  monitorWebGLEvents() {
    // Monitor canvas creation/destruction
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
      const element = originalCreateElement.call(this, tagName);
      
      if (tagName.toLowerCase() === 'canvas') {
        console.log('[ISOLATION-MONITOR] Canvas element created');
        
        // Monitor WebGL context events
        element.addEventListener('webglcontextlost', () => {
          console.log('[ISOLATION-MONITOR] WebGL context lost event');
          webglAuthIsolationValidator.metrics.contextLostEvents++;
        });
        
        element.addEventListener('webglcontextrestored', () => {
          console.log('[ISOLATION-MONITOR] WebGL context restored event');
        });
      }
      
      return element;
    };
  }
  
  /**
   * Check for interference patterns
   */
  checkInterference() {
    const now = Date.now();
    const timeWindow = 60000; // 1 minute
    
    // Calculate rates per minute
    const authRequestRate = (this.metrics.authRequestCount / (now - this.startTime)) * timeWindow;
    const reactRenderRate = (this.metrics.reactRenderCount / (now - this.startTime)) * timeWindow;
    
    // Check for interference patterns
    const authFlooding = authRequestRate > this.thresholds.maxAuthRequestsPerMinute;
    const reactCascading = reactRenderRate > this.thresholds.maxReactRendersPerMinute;
    const consecutiveRequests = this.metrics.maxConsecutiveAuthRequests > this.thresholds.maxConsecutiveAuthRequests;
    
    const interferenceDetected = authFlooding || reactCascading || consecutiveRequests;
    
    if (interferenceDetected && !this.metrics.interferenceDetected) {
      console.warn('[ISOLATION-MONITOR] WebGL-Auth interference detected!');
      console.warn(`- Auth request rate: ${authRequestRate.toFixed(1)}/min (threshold: ${this.thresholds.maxAuthRequestsPerMinute})`);
      console.warn(`- React render rate: ${reactRenderRate.toFixed(1)}/min (threshold: ${this.thresholds.maxReactRendersPerMinute})`);
      console.warn(`- Max consecutive auth requests: ${this.metrics.maxConsecutiveAuthRequests} (threshold: ${this.thresholds.maxConsecutiveAuthRequests})`);
      
      this.metrics.interferenceDetected = true;
    }
    
    return {
      interferenceDetected,
      authRequestRate,
      reactRenderRate,
      consecutiveRequests: this.metrics.maxConsecutiveAuthRequests
    };
  }
  
  /**
   * Reset metrics for new monitoring session
   */
  resetMetrics() {
    this.metrics = {
      authRequestCount: 0,
      webglEventCount: 0,
      reactRenderCount: 0,
      contextLostEvents: 0,
      performanceAdaptations: 0,
      interferenceDetected: false,
      lastAuthRequest: 0,
      lastWebglEvent: 0,
      consecutiveAuthRequests: 0,
      maxConsecutiveAuthRequests: 0
    };
    
    this.startTime = Date.now();
  }
  
  /**
   * Generate comprehensive isolation report
   */
  generateReport() {
    const duration = Date.now() - this.startTime;
    const durationMinutes = duration / 60000;
    
    const authRequestRate = this.metrics.authRequestCount / durationMinutes;
    const webglEventRate = this.metrics.webglEventCount / durationMinutes;
    const reactRenderRate = this.metrics.reactRenderCount / durationMinutes;
    
    const isolationEffective = !this.metrics.interferenceDetected &&
                              authRequestRate < this.thresholds.maxAuthRequestsPerMinute &&
                              reactRenderRate < this.thresholds.maxReactRendersPerMinute &&
                              this.metrics.maxConsecutiveAuthRequests <= this.thresholds.maxConsecutiveAuthRequests;
    
    const report = {
      summary: {
        isolationEffective,
        monitoringDuration: `${durationMinutes.toFixed(1)} minutes`,
        interferenceDetected: this.metrics.interferenceDetected
      },
      
      metrics: {
        authentication: {
          totalRequests: this.metrics.authRequestCount,
          requestRate: `${authRequestRate.toFixed(1)}/min`,
          maxConsecutiveRequests: this.metrics.maxConsecutiveAuthRequests,
          floodingDetected: authRequestRate > this.thresholds.maxAuthRequestsPerMinute
        },
        
        webgl: {
          totalEvents: this.metrics.webglEventCount,
          eventRate: `${webglEventRate.toFixed(1)}/min`,
          contextLostEvents: this.metrics.contextLostEvents,
          performanceAdaptations: this.metrics.performanceAdaptations
        },
        
        react: {
          totalRenders: this.metrics.reactRenderCount,
          renderRate: `${reactRenderRate.toFixed(1)}/min`,
          cascadingDetected: reactRenderRate > this.thresholds.maxReactRendersPerMinute
        }
      },
      
      thresholds: {
        authRequestsPerMinute: this.thresholds.maxAuthRequestsPerMinute,
        reactRendersPerMinute: this.thresholds.maxReactRendersPerMinute,
        maxConsecutiveAuthRequests: this.thresholds.maxConsecutiveAuthRequests
      },
      
      recommendations: this.generateRecommendations(isolationEffective, authRequestRate, reactRenderRate)
    };
    
    this.logReport(report);
    return report;
  }
  
  /**
   * Generate recommendations based on monitoring results
   */
  generateRecommendations(isolationEffective, authRequestRate, reactRenderRate) {
    const recommendations = [];
    
    if (isolationEffective) {
      recommendations.push({
        type: 'success',
        message: 'WebGL operations are successfully isolated from authentication flow'
      });
    } else {
      recommendations.push({
        type: 'critical',
        message: 'WebGL-Authentication interference detected - immediate action required'
      });
    }
    
    if (authRequestRate > this.thresholds.maxAuthRequestsPerMinute) {
      recommendations.push({
        type: 'error',
        message: `High authentication request rate (${authRequestRate.toFixed(1)}/min) indicates WebGL interference`,
        action: 'Implement enhanced throttling in AuthContext'
      });
    }
    
    if (reactRenderRate > this.thresholds.maxReactRendersPerMinute) {
      recommendations.push({
        type: 'error',
        message: `High React render rate (${reactRenderRate.toFixed(1)}/min) indicates cascade effects`,
        action: 'Batch WebGL state updates and use requestAnimationFrame'
      });
    }
    
    if (this.metrics.contextLostEvents > 0) {
      recommendations.push({
        type: 'warning',
        message: `WebGL context lost ${this.metrics.contextLostEvents} times`,
        action: 'Implement better context recovery with debounced state updates'
      });
    }
    
    if (this.metrics.performanceAdaptations > 10) {
      recommendations.push({
        type: 'info',
        message: `Frequent performance adaptations (${this.metrics.performanceAdaptations})`,
        action: 'Consider more stable performance targets'
      });
    }
    
    return recommendations;
  }
  
  /**
   * Log comprehensive report to console
   */
  logReport(report) {
    console.log('\n=== WebGL-Authentication Isolation Report ===');
    console.log(`Isolation Effective: ${report.summary.isolationEffective ? '✅ YES' : '❌ NO'}`);
    console.log(`Monitoring Duration: ${report.summary.monitoringDuration}`);
    console.log(`Interference Detected: ${report.summary.interferenceDetected ? '⚠️ YES' : '✅ NO'}`);
    
    console.log('\n--- Authentication Metrics ---');
    console.log(`Total Requests: ${report.metrics.authentication.totalRequests}`);
    console.log(`Request Rate: ${report.metrics.authentication.requestRate}`);
    console.log(`Max Consecutive: ${report.metrics.authentication.maxConsecutiveRequests}`);
    console.log(`Flooding: ${report.metrics.authentication.floodingDetected ? '⚠️ YES' : '✅ NO'}`);
    
    console.log('\n--- WebGL Metrics ---');
    console.log(`Total Events: ${report.metrics.webgl.totalEvents}`);
    console.log(`Event Rate: ${report.metrics.webgl.eventRate}`);
    console.log(`Context Lost: ${report.metrics.webgl.contextLostEvents}`);
    console.log(`Performance Adaptations: ${report.metrics.webgl.performanceAdaptations}`);
    
    console.log('\n--- React Metrics ---');
    console.log(`Total Renders: ${report.metrics.react.totalRenders}`);
    console.log(`Render Rate: ${report.metrics.react.renderRate}`);
    console.log(`Cascading: ${report.metrics.react.cascadingDetected ? '⚠️ YES' : '✅ NO'}`);
    
    console.log('\n--- Recommendations ---');
    report.recommendations.forEach((rec, index) => {
      const icon = rec.type === 'success' ? '✅' : 
                   rec.type === 'critical' ? '🚨' : 
                   rec.type === 'error' ? '❌' : 
                   rec.type === 'warning' ? '⚠️' : 'ℹ️';
      console.log(`${index + 1}. ${icon} ${rec.message}`);
      if (rec.action) {
        console.log(`   Action: ${rec.action}`);
      }
    });
    
    console.log('\n=== End Report ===\n');
  }
  
  /**
   * Quick validation test
   */
  async quickValidation(durationMs = 30000) {
    console.log(`Starting quick WebGL-Auth isolation validation (${durationMs/1000}s)...`);
    
    this.startMonitoring();
    
    return new Promise((resolve) => {
      setTimeout(() => {
        const report = this.stopMonitoring();
        resolve(report);
      }, durationMs);
    });
  }
}

// Create singleton instance
const webglAuthIsolationValidator = new WebGLAuthIsolationValidator();

// Make available globally for testing
window.webglAuthIsolationValidator = webglAuthIsolationValidator;

export default webglAuthIsolationValidator;