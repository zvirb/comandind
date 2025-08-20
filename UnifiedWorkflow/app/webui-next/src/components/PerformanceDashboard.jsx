/**
 * Performance Dashboard Component
 * Real-time performance monitoring and optimization controls
 */

import React, { useState, useEffect, useRef, memo } from 'react';
import { Monitor, Cpu, Zap, Database, Network, TrendingUp, Settings, X } from 'lucide-react';
import { withPerformanceOptimization } from '../utils/reactPerformanceOptimizer';
import webglPerformanceManager from '../utils/webglPerformanceManager';
import apiOptimizer from '../utils/apiOptimizer';

const PerformanceDashboard = memo(({ isOpen, onClose }) => {
  const [metrics, setMetrics] = useState({
    webgl: null,
    api: null,
    browser: null,
    memory: null
  });
  
  const [autoOptimize, setAutoOptimize] = useState(true);
  const [performanceLevel, setPerformanceLevel] = useState('high');
  const intervalRef = useRef(null);

  // Collect performance metrics with Page Visibility API optimization
  useEffect(() => {
    if (!isOpen) return;

    let isVisible = !document.hidden;
    let activeInterval = null;

    const collectMetrics = () => {
      // WebGL metrics
      const webglStats = webglPerformanceManager.getStats();
      
      // API metrics
      const apiStats = apiOptimizer.getStats();
      
      // Browser metrics
      const browserStats = {
        fps: getFPS(),
        memory: getMemoryUsage(),
        timing: getNavigationTiming(),
        webVitals: getWebVitals()
      };

      setMetrics(prevMetrics => {
        const newMetrics = {
          webgl: webglStats,
          api: apiStats,
          browser: browserStats,
          timestamp: Date.now()
        };
        // Maintain previous data during loading to prevent UI clearing
        return prevMetrics ? { ...prevMetrics, ...newMetrics } : newMetrics;
      });
    };

    const startPolling = () => {
      if (activeInterval) clearInterval(activeInterval);
      // Optimized: Increased from 2s to 10s for better performance
      activeInterval = setInterval(collectMetrics, 10000);
    };

    const stopPolling = () => {
      if (activeInterval) {
        clearInterval(activeInterval);
        activeInterval = null;
      }
    };

    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
      if (isVisible) {
        // Resume polling when tab becomes visible
        collectMetrics(); // Immediate update
        startPolling();
      } else {
        // Pause polling when tab is hidden
        stopPolling();
      }
    };

    // Initial collection
    collectMetrics();

    // Start polling if visible
    if (isVisible) {
      startPolling();
    }

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    intervalRef.current = activeInterval;

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isOpen]);

  // Auto-optimization logic
  useEffect(() => {
    if (!autoOptimize || !metrics.webgl) return;

    const { fps, drawCalls, triangles } = metrics.webgl;
    
    if (fps < 30 && performanceLevel !== 'low') {
      setPerformanceLevel('low');
      optimizePerformance('low');
    } else if (fps < 45 && performanceLevel === 'high') {
      setPerformanceLevel('medium');
      optimizePerformance('medium');
    } else if (fps > 55 && performanceLevel !== 'high') {
      setPerformanceLevel('high');
      optimizePerformance('high');
    }
  }, [metrics.webgl, autoOptimize, performanceLevel]);

  const optimizePerformance = (level) => {
    // Apply WebGL optimizations
    webglPerformanceManager.performanceLevel = level;
    webglPerformanceManager.applyPerformanceSettings();

    // Clear API cache if memory is high
    if (level === 'low') {
      apiOptimizer.clearCache();
    }

    console.log(`Performance optimized to ${level} level`);
  };

  const getFPS = () => {
    // Simple FPS calculation
    const now = performance.now();
    if (!getFPS.lastTime) {
      getFPS.lastTime = now;
      getFPS.frames = 0;
      return 0;
    }
    
    getFPS.frames++;
    const elapsed = now - getFPS.lastTime;
    
    if (elapsed >= 1000) {
      const fps = Math.round((getFPS.frames * 1000) / elapsed);
      getFPS.lastTime = now;
      getFPS.frames = 0;
      return fps;
    }
    
    return getFPS.currentFPS || 0;
  };

  const getMemoryUsage = () => {
    if (!performance.memory) return null;
    
    const memory = performance.memory;
    return {
      used: Math.round(memory.usedJSHeapSize / 1024 / 1024),
      total: Math.round(memory.totalJSHeapSize / 1024 / 1024),
      limit: Math.round(memory.jsHeapSizeLimit / 1024 / 1024),
      percentage: Math.round((memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100)
    };
  };

  const getNavigationTiming = () => {
    const navigation = performance.getEntriesByType('navigation')[0];
    if (!navigation) return null;

    return {
      dns: Math.round(navigation.domainLookupEnd - navigation.domainLookupStart),
      connect: Math.round(navigation.connectEnd - navigation.connectStart),
      request: Math.round(navigation.responseStart - navigation.requestStart),
      response: Math.round(navigation.responseEnd - navigation.responseStart),
      dom: Math.round(navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart),
      load: Math.round(navigation.loadEventEnd - navigation.loadEventStart)
    };
  };

  const getWebVitals = () => {
    // This would integrate with real Web Vitals measurement
    return {
      fcp: 1200, // First Contentful Paint
      lcp: 2100, // Largest Contentful Paint
      fid: 85,   // First Input Delay
      cls: 0.08  // Cumulative Layout Shift
    };
  };

  const handleForceOptimization = () => {
    // Force immediate optimization
    webglPerformanceManager.forceCleanup();
    apiOptimizer.clearCache();
    
    // Trigger garbage collection if available
    if (window.gc) {
      window.gc();
    }
  };

  const getPerformanceColor = (value, thresholds) => {
    if (value <= thresholds.good) return 'text-green-400';
    if (value <= thresholds.warning) return 'text-yellow-400';
    return 'text-red-400';
  };

  const formatBytes = (bytes) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let unitIndex = 0;
    let value = bytes;
    
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }
    
    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Monitor className="text-blue-400" size={24} />
            <h2 className="text-xl font-semibold text-white">Performance Dashboard</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4 mb-6 p-4 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-optimize"
              checked={autoOptimize}
              onChange={(e) => setAutoOptimize(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="auto-optimize" className="text-white">Auto-optimize</label>
          </div>

          <select
            value={performanceLevel}
            onChange={(e) => setPerformanceLevel(e.target.value)}
            className="bg-gray-700 text-white rounded px-3 py-1"
          >
            <option value="high">High Quality</option>
            <option value="medium">Medium Quality</option>
            <option value="low">Low Quality</option>
          </select>

          <button
            onClick={handleForceOptimization}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <Zap size={16} />
            Force Optimize
          </button>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {/* WebGL Performance */}
          <div className="bg-gray-800 rounded-lg p-4">
            {metrics.webgl ? (
              <div>
              <div className="flex items-center gap-2 mb-3">
                <Cpu className="text-purple-400" size={20} />
                <h3 className="font-semibold text-white">WebGL</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">FPS:</span>
                  <span className={getPerformanceColor(metrics.webgl.fps, { good: 55, warning: 30 })}>
                    {metrics.webgl.fps}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Draw Calls:</span>
                  <span className={getPerformanceColor(metrics.webgl.drawCalls, { good: 100, warning: 200 })}>
                    {metrics.webgl.drawCalls}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Triangles:</span>
                  <span className={getPerformanceColor(metrics.webgl.triangles, { good: 50000, warning: 100000 })}>
                    {metrics.webgl.triangles.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Geometries:</span>
                  <span className="text-white">{metrics.webgl.geometries}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Textures:</span>
                  <span className="text-white">{metrics.webgl.textures}</span>
                </div>
              </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Cpu className="text-purple-400" size={20} />
                  <h3 className="font-semibold text-white">WebGL</h3>
                </div>
                <div className="space-y-2 text-sm text-center py-8">
                  <div className="animate-pulse text-gray-400">Loading metrics...</div>
                </div>
              </div>
            )}
          </div>

          {/* API Performance */}
          <div className="bg-gray-800 rounded-lg p-4">
            {metrics.api ? (
              <div>
              <div className="flex items-center gap-2 mb-3">
                <Network className="text-green-400" size={20} />
                <h3 className="font-semibold text-white">API</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Total Requests:</span>
                  <span className="text-white">{metrics.api.totalRequests}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Cache Hit Ratio:</span>
                  <span className="text-green-400">{metrics.api.cacheHitRatio}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg Response:</span>
                  <span className="text-white">{metrics.api.avgResponseTime}ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Cache Size:</span>
                  <span className="text-white">{metrics.api.cacheSize} entries</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Errors:</span>
                  <span className={metrics.api.errors > 0 ? 'text-red-400' : 'text-green-400'}>
                    {metrics.api.errors}
                  </span>
                </div>
              </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Network className="text-green-400" size={20} />
                  <h3 className="font-semibold text-white">API</h3>
                </div>
                <div className="space-y-2 text-sm text-center py-8">
                  <div className="animate-pulse text-gray-400">Loading metrics...</div>
                </div>
              </div>
            )}
          </div>

          {/* Memory Usage */}
          <div className="bg-gray-800 rounded-lg p-4">
            {metrics.browser?.memory ? (
              <div>
              <div className="flex items-center gap-2 mb-3">
                <Database className="text-orange-400" size={20} />
                <h3 className="font-semibold text-white">Memory</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Used:</span>
                  <span className="text-white">{metrics.browser.memory.used} MB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Total:</span>
                  <span className="text-white">{metrics.browser.memory.total} MB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Limit:</span>
                  <span className="text-white">{metrics.browser.memory.limit} MB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Usage:</span>
                  <span className={getPerformanceColor(metrics.browser.memory.percentage, { good: 50, warning: 80 })}>
                    {metrics.browser.memory.percentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      metrics.browser.memory.percentage > 80 ? 'bg-red-400' :
                      metrics.browser.memory.percentage > 50 ? 'bg-yellow-400' : 'bg-green-400'
                    }`}
                    style={{ width: `${metrics.browser.memory.percentage}%` }}
                  />
                </div>
              </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Database className="text-orange-400" size={20} />
                  <h3 className="font-semibold text-white">Memory</h3>
                </div>
                <div className="space-y-2 text-sm text-center py-8">
                  <div className="animate-pulse text-gray-400">Loading metrics...</div>
                </div>
              </div>
            )}
          </div>

          {/* Web Vitals */}
          <div className="bg-gray-800 rounded-lg p-4">
            {metrics.browser?.webVitals ? (
              <div>
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="text-blue-400" size={20} />
                <h3 className="font-semibold text-white">Web Vitals</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">FCP:</span>
                  <span className={getPerformanceColor(metrics.browser.webVitals.fcp, { good: 1800, warning: 3000 })}>
                    {metrics.browser.webVitals.fcp}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">LCP:</span>
                  <span className={getPerformanceColor(metrics.browser.webVitals.lcp, { good: 2500, warning: 4000 })}>
                    {metrics.browser.webVitals.lcp}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">FID:</span>
                  <span className={getPerformanceColor(metrics.browser.webVitals.fid, { good: 100, warning: 300 })}>
                    {metrics.browser.webVitals.fid}ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">CLS:</span>
                  <span className={getPerformanceColor(metrics.browser.webVitals.cls * 1000, { good: 100, warning: 250 })}>
                    {metrics.browser.webVitals.cls.toFixed(3)}
                  </span>
                </div>
              </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="text-blue-400" size={20} />
                  <h3 className="font-semibold text-white">Web Vitals</h3>
                </div>
                <div className="space-y-2 text-sm text-center py-8">
                  <div className="animate-pulse text-gray-400">Loading metrics...</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Timing */}
        {metrics.browser?.timing && (
          <div className="mt-6 bg-gray-800 rounded-lg p-4">
            <h3 className="font-semibold text-white mb-3">Navigation Timing</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-sm">
              <div className="text-center">
                <div className="text-gray-400">DNS</div>
                <div className="text-white font-semibold">{metrics.browser.timing.dns}ms</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Connect</div>
                <div className="text-white font-semibold">{metrics.browser.timing.connect}ms</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Request</div>
                <div className="text-white font-semibold">{metrics.browser.timing.request}ms</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Response</div>
                <div className="text-white font-semibold">{metrics.browser.timing.response}ms</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">DOM</div>
                <div className="text-white font-semibold">{metrics.browser.timing.dom}ms</div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Load</div>
                <div className="text-white font-semibold">{metrics.browser.timing.load}ms</div>
              </div>
            </div>
          </div>
        )}

        {/* Performance Recommendations */}
        <div className="mt-6 bg-gray-800 rounded-lg p-4">
          <h3 className="font-semibold text-white mb-3">Recommendations</h3>
          <div className="space-y-2 text-sm">
            {metrics.webgl && metrics.webgl.fps < 30 && (
              <div className="text-yellow-400">• Consider reducing WebGL complexity or enabling low-quality mode</div>
            )}
            {metrics.api && metrics.api.cacheHitRatio < '50%' && (
              <div className="text-yellow-400">• API cache hit ratio is low, consider increasing cache TTL</div>
            )}
            {metrics.browser?.memory && metrics.browser.memory.percentage > 80 && (
              <div className="text-red-400">• High memory usage detected, consider clearing caches</div>
            )}
            {metrics.webgl && metrics.webgl.drawCalls > 200 && (
              <div className="text-yellow-400">• High draw calls detected, consider batching or instancing</div>
            )}
            {(!metrics.webgl || metrics.webgl.fps > 55) && 
             (!metrics.browser?.memory || metrics.browser.memory.percentage < 50) && (
              <div className="text-green-400">• Performance is optimal</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

PerformanceDashboard.displayName = 'PerformanceDashboard';

export default withPerformanceOptimization(PerformanceDashboard, {
  measurePerformance: true,
  skipProps: ['isOpen']
});