import React, { useState, useEffect, useRef } from 'react';
import { Activity, AlertTriangle, CheckCircle, XCircle, Zap } from 'lucide-react';

const WebGLPerformanceIsolationMonitor = ({ isOpen, onClose }) => {
  const [metrics, setMetrics] = useState({
    webglFps: 0,
    webglFrameTime: 0,
    authRequestCount: 0,
    webglContextLost: 0,
    reactRenderCount: 0,
    isolationEffective: true,
    performanceLevel: 'high',
    memoryUsage: 0,
    lastUpdate: Date.now()
  });

  const [history, setHistory] = useState([]);
  const metricsRef = useRef(metrics);
  const intervalRef = useRef(null);
  const authRequestCountRef = useRef(0);
  const renderCountRef = useRef(0);

  // Monitor authentication request patterns
  useEffect(() => {
    const originalFetch = window.fetch;
    
    window.fetch = function(...args) {
      const url = args[0];
      if (typeof url === 'string' && (
        url.includes('/api/v1/auth/') || 
        url.includes('/api/v1/session/') ||
        url.includes('/api/v1/health/')
      )) {
        authRequestCountRef.current++;
      }
      return originalFetch.apply(this, args);
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  // Monitor React render patterns
  useEffect(() => {
    const observer = new MutationObserver(() => {
      renderCountRef.current++;
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: false
    });

    return () => observer.disconnect();
  }, []);

  // Performance monitoring loop
  useEffect(() => {
    if (!isOpen) return;

    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const timeDelta = now - metricsRef.current.lastUpdate;
      
      // Calculate rates per minute
      const authRequestRate = (authRequestCountRef.current / timeDelta) * 60000;
      const renderRate = (renderCountRef.current / timeDelta) * 60000;
      
      // Check for performance interference patterns
      const authFloodThreshold = 20; // More than 20 auth requests per minute indicates flooding
      const renderFloodThreshold = 600; // More than 600 renders per minute indicates cascade
      
      const isolationEffective = authRequestRate < authFloodThreshold && renderRate < renderFloodThreshold;
      
      // Get WebGL performance data if available
      let webglMetrics = {
        fps: 60,
        frameTime: 16.67,
        performanceLevel: 'high',
        contextLost: 0
      };

      // Try to get data from WebGL Performance Manager
      try {
        if (window.webglPerformanceManager && window.webglPerformanceManager.getStats) {
          const stats = window.webglPerformanceManager.getStats();
          webglMetrics = {
            fps: stats.fps || 0,
            frameTime: stats.frameTime || 0,
            performanceLevel: stats.performanceLevel || 'unknown',
            contextLost: 0 // This would need to be tracked separately
          };
        }
      } catch (error) {
        console.debug('Could not access WebGL Performance Manager stats');
      }

      // Get memory usage
      let memoryUsage = 0;
      if (performance.memory) {
        memoryUsage = Math.round((performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100);
      }

      const newMetrics = {
        webglFps: webglMetrics.fps,
        webglFrameTime: webglMetrics.frameTime,
        authRequestCount: authRequestCountRef.current,
        authRequestRate: Math.round(authRequestRate),
        renderRate: Math.round(renderRate),
        webglContextLost: webglMetrics.contextLost,
        reactRenderCount: renderCountRef.current,
        isolationEffective,
        performanceLevel: webglMetrics.performanceLevel,
        memoryUsage,
        lastUpdate: now
      };

      setMetrics(newMetrics);
      metricsRef.current = newMetrics;

      // Add to history (keep last 20 samples)
      setHistory(prev => {
        const newHistory = [...prev, {
          timestamp: now,
          authRequestRate: Math.round(authRequestRate),
          renderRate: Math.round(renderRate),
          fps: webglMetrics.fps,
          memoryUsage,
          isolationEffective
        }];
        return newHistory.slice(-20);
      });

      // Reset counters
      authRequestCountRef.current = 0;
      renderCountRef.current = 0;

    }, 5000); // Update every 5 seconds

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isOpen]);

  const getStatusColor = (effective) => {
    return effective ? 'text-green-400' : 'text-red-400';
  };

  const getStatusIcon = (effective) => {
    return effective ? <CheckCircle size={16} /> : <XCircle size={16} />;
  };

  const getPerformanceLevelColor = (level) => {
    switch (level) {
      case 'high': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center space-x-2">
            <Activity className="text-blue-400" size={20} />
            <h2 className="text-xl font-semibold text-white">WebGL Performance Isolation Monitor</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-300">Isolation Status</span>
                <span className={getStatusColor(metrics.isolationEffective)}>
                  {getStatusIcon(metrics.isolationEffective)}
                </span>
              </div>
              <div className={`text-lg font-semibold ${getStatusColor(metrics.isolationEffective)}`}>
                {metrics.isolationEffective ? 'Effective' : 'Interference Detected'}
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-300">WebGL Performance</span>
                <Zap className={getPerformanceLevelColor(metrics.performanceLevel)} size={16} />
              </div>
              <div className={`text-lg font-semibold ${getPerformanceLevelColor(metrics.performanceLevel)}`}>
                {metrics.performanceLevel.toUpperCase()} ({Math.round(metrics.webglFps)} FPS)
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-300">Memory Usage</span>
                <span className={metrics.memoryUsage > 80 ? 'text-red-400' : 'text-green-400'}>
                  {metrics.memoryUsage > 80 ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
                </span>
              </div>
              <div className={`text-lg font-semibold ${metrics.memoryUsage > 80 ? 'text-red-400' : 'text-green-400'}`}>
                {metrics.memoryUsage}%
              </div>
            </div>
          </div>

          {/* Detailed Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Real-time Metrics */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Current Metrics</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-300">WebGL Frame Rate:</span>
                  <span className="text-white font-mono">{Math.round(metrics.webglFps)} FPS</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Frame Time:</span>
                  <span className="text-white font-mono">{metrics.webglFrameTime.toFixed(2)} ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Auth Requests/min:</span>
                  <span className={`font-mono ${metrics.authRequestRate > 20 ? 'text-red-400' : 'text-green-400'}`}>
                    {metrics.authRequestRate || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">React Renders/min:</span>
                  <span className={`font-mono ${metrics.renderRate > 600 ? 'text-red-400' : 'text-green-400'}`}>
                    {metrics.renderRate || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">WebGL Context Lost:</span>
                  <span className="text-white font-mono">{metrics.webglContextLost}</span>
                </div>
              </div>
            </div>

            {/* Performance History */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Performance History</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {history.slice(-10).reverse().map((entry, index) => (
                  <div key={index} className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                    <div className="flex space-x-2">
                      <span className={entry.isolationEffective ? 'text-green-400' : 'text-red-400'}>
                        {entry.isolationEffective ? '✓' : '✗'}
                      </span>
                      <span className="text-white font-mono w-12 text-right">
                        {Math.round(entry.fps)}fps
                      </span>
                      <span className="text-gray-300 font-mono w-8 text-right">
                        {entry.memoryUsage}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Isolation Recommendations */}
          <div className="mt-6 bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-4">Isolation Analysis</h3>
            <div className="space-y-2 text-sm">
              {metrics.authRequestRate > 20 && (
                <div className="flex items-center space-x-2 text-red-400">
                  <AlertTriangle size={16} />
                  <span>High authentication request rate detected - possible WebGL interference</span>
                </div>
              )}
              {metrics.renderRate > 600 && (
                <div className="flex items-center space-x-2 text-red-400">
                  <AlertTriangle size={16} />
                  <span>High React render rate detected - potential cascade from WebGL events</span>
                </div>
              )}
              {metrics.webglFps < 30 && (
                <div className="flex items-center space-x-2 text-yellow-400">
                  <AlertTriangle size={16} />
                  <span>Low WebGL frame rate - may impact overall application performance</span>
                </div>
              )}
              {metrics.memoryUsage > 80 && (
                <div className="flex items-center space-x-2 text-red-400">
                  <AlertTriangle size={16} />
                  <span>High memory usage - cleanup recommended</span>
                </div>
              )}
              {metrics.isolationEffective && (
                <div className="flex items-center space-x-2 text-green-400">
                  <CheckCircle size={16} />
                  <span>WebGL operations successfully isolated from React authentication flow</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebGLPerformanceIsolationMonitor;