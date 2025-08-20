/**
 * Enhanced Performance Optimization Utilities
 * Provides advanced tools for React performance, API optimization, and animation control
 */

import React, { memo, useCallback, useMemo, useState, useEffect, useRef, useReducer } from 'react';

/**
 * Enhanced API request manager with timeouts and AbortController
 */
export class APIRequestManager {
  constructor() {
    this.activeRequests = new Map();
    this.requestCounter = 0;
  }

  /**
   * Make request with timeout and automatic abort
   * @param {string} url - Request URL
   * @param {Object} options - Request options
   * @param {number} timeout - Timeout in milliseconds (default: 10000)
   */
  async makeRequest(url, options = {}, timeout = 10000) {
    const requestId = ++this.requestCounter;
    const controller = new AbortController();
    
    // Set up timeout
    const timeoutId = setTimeout(() => {
      controller.abort();
      this.activeRequests.delete(requestId);
    }, timeout);

    // Store request for potential cancellation
    this.activeRequests.set(requestId, { controller, timeoutId, url });

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      this.activeRequests.delete(requestId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      this.activeRequests.delete(requestId);

      if (error.name === 'AbortError') {
        throw new Error('Request timed out');
      }
      throw error;
    }
  }

  /**
   * Cancel all active requests
   */
  cancelAllRequests() {
    for (const [id, request] of this.activeRequests) {
      request.controller.abort();
      clearTimeout(request.timeoutId);
    }
    this.activeRequests.clear();
  }

  /**
   * Get active request count
   */
  getActiveRequestCount() {
    return this.activeRequests.size;
  }
}

// Global API manager instance
export const globalAPIManager = new APIRequestManager();

/**
 * Hook for API requests with timeout and loading states
 * @param {string} url - Request URL
 * @param {Object} options - Request options
 * @param {number} timeout - Timeout in milliseconds
 */
export const useAPIRequest = (url, options = {}, timeout = 10000) => {
  const [state, setState] = useState({
    data: null,
    loading: false,
    error: null
  });

  const makeRequest = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const response = await globalAPIManager.makeRequest(url, options, timeout);
      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      setState(prev => ({ ...prev, loading: false, error: error.message }));
      throw error;
    }
  }, [url, JSON.stringify(options), timeout]);

  return { ...state, makeRequest };
};

/**
 * Hook for batch API requests with timeout
 * @param {Array} requests - Array of request objects [{url, options}]
 * @param {number} timeout - Timeout in milliseconds
 */
export const useBatchAPIRequests = (requests, timeout = 10000) => {
  const [state, setState] = useState({
    data: {},
    loading: false,
    error: null,
    completedCount: 0
  });

  const makeBatchRequest = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null, completedCount: 0 }));

    try {
      const promises = requests.map(async (request, index) => {
        try {
          const response = await globalAPIManager.makeRequest(
            request.url, 
            request.options || {}, 
            timeout
          );
          const data = await response.json();
          setState(prev => ({ 
            ...prev, 
            completedCount: prev.completedCount + 1,
            data: { ...prev.data, [index]: { success: true, data } }
          }));
          return { success: true, data, index };
        } catch (error) {
          setState(prev => ({ 
            ...prev, 
            completedCount: prev.completedCount + 1,
            data: { ...prev.data, [index]: { success: false, error: error.message } }
          }));
          return { success: false, error: error.message, index };
        }
      });

      const results = await Promise.allSettled(promises);
      const finalData = {};
      
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          finalData[index] = result.value;
        } else {
          finalData[index] = { success: false, error: result.reason?.message || 'Unknown error' };
        }
      });

      setState(prev => ({ ...prev, loading: false, data: finalData }));
      return finalData;
    } catch (error) {
      setState(prev => ({ ...prev, loading: false, error: error.message }));
      throw error;
    }
  }, [requests, timeout]);

  return { ...state, makeBatchRequest };
};

/**
 * Advanced React.memo with deep comparison for complex props
 * @param {React.Component} Component - Component to memoize
 * @param {Array} dependencyKeys - Keys to watch for changes
 */
export const memoizeWithDependencies = (Component, dependencyKeys = []) => {
  return memo(Component, (prevProps, nextProps) => {
    // Fast path: reference equality
    if (prevProps === nextProps) return true;

    // Check specific dependency keys
    for (const key of dependencyKeys) {
      if (prevProps[key] !== nextProps[key]) {
        return false;
      }
    }

    // Check all other props for changes
    const prevKeys = Object.keys(prevProps);
    const nextKeys = Object.keys(nextProps);

    if (prevKeys.length !== nextKeys.length) return false;

    for (const key of prevKeys) {
      if (!dependencyKeys.includes(key) && prevProps[key] !== nextProps[key]) {
        return false;
      }
    }

    return true;
  });
};

/**
 * Performance monitoring hook with frame rate tracking
 * @param {string} componentName - Name for logging
 * @param {number} targetFPS - Target frame rate (default: 60)
 */
export const usePerformanceMonitor = (componentName, targetFPS = 60) => {
  const frameTimesRef = useRef([]);
  const lastFrameTimeRef = useRef(performance.now());
  const renderCountRef = useRef(0);
  const performanceDataRef = useRef({
    averageFPS: targetFPS,
    minFPS: targetFPS,
    maxFPS: targetFPS,
    renderCount: 0
  });

  const updatePerformanceMetrics = useCallback(() => {
    const now = performance.now();
    const frameTime = now - lastFrameTimeRef.current;
    lastFrameTimeRef.current = now;
    renderCountRef.current++;

    frameTimesRef.current.push(frameTime);
    if (frameTimesRef.current.length > 60) {
      frameTimesRef.current.shift();
    }

    if (frameTimesRef.current.length >= 10) {
      const avgFrameTime = frameTimesRef.current.reduce((a, b) => a + b, 0) / frameTimesRef.current.length;
      const currentFPS = 1000 / avgFrameTime;
      const minFrameTime = Math.min(...frameTimesRef.current);
      const maxFrameTime = Math.max(...frameTimesRef.current);

      performanceDataRef.current = {
        averageFPS: Math.round(currentFPS),
        minFPS: Math.round(1000 / maxFrameTime),
        maxFPS: Math.round(1000 / minFrameTime),
        renderCount: renderCountRef.current
      };

      // Warning for performance issues
      if (currentFPS < targetFPS * 0.8) {
        console.warn(`${componentName} performance warning: ${currentFPS.toFixed(1)}fps (target: ${targetFPS}fps)`);
      }
    }
  }, [componentName, targetFPS]);

  useEffect(() => {
    updatePerformanceMetrics();
  });

  return {
    getPerformanceData: () => performanceDataRef.current,
    updateMetrics: updatePerformanceMetrics
  };
};

/**
 * Advanced state reducer with performance optimizations
 * @param {Function} reducer - Reducer function
 * @param {*} initialState - Initial state
 * @param {Array} optimizationKeys - Keys that should trigger re-renders
 */
export const useOptimizedReducer = (reducer, initialState, optimizationKeys = []) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const previousStateRef = useRef(initialState);
  const optimizedStateRef = useRef(initialState);

  const optimizedDispatch = useCallback((action) => {
    const newState = reducer(state, action);
    
    // Check if optimization keys have changed
    let shouldUpdate = false;
    if (optimizationKeys.length > 0) {
      for (const key of optimizationKeys) {
        if (newState[key] !== previousStateRef.current[key]) {
          shouldUpdate = true;
          break;
        }
      }
    } else {
      shouldUpdate = newState !== previousStateRef.current;
    }

    if (shouldUpdate) {
      previousStateRef.current = newState;
      optimizedStateRef.current = newState;
      dispatch(action);
    }
  }, [state, reducer, optimizationKeys]);

  return [optimizedStateRef.current, optimizedDispatch];
};

/**
 * Hook for frame-rate aware animations
 * @param {Function} callback - Animation callback
 * @param {Array} dependencies - Dependencies array
 * @param {number} targetFPS - Target frame rate
 */
export const useFrameRateAwareAnimation = (callback, dependencies, targetFPS = 60) => {
  const animationRef = useRef();
  const lastFrameTimeRef = useRef(0);
  const frameIntervalRef = useRef(1000 / targetFPS);

  const animationLoop = useCallback((currentTime) => {
    if (currentTime - lastFrameTimeRef.current >= frameIntervalRef.current) {
      callback(currentTime);
      lastFrameTimeRef.current = currentTime;
    }
    animationRef.current = requestAnimationFrame(animationLoop);
  }, [callback]);

  useEffect(() => {
    frameIntervalRef.current = 1000 / targetFPS;
    animationRef.current = requestAnimationFrame(animationLoop);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [...dependencies, targetFPS, animationLoop]);

  return () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };
};

/**
 * Hook for adaptive performance based on device capabilities
 */
export const useAdaptivePerformance = () => {
  const [performanceLevel, setPerformanceLevel] = useState('high');
  const [deviceCapabilities, setDeviceCapabilities] = useState({});

  useEffect(() => {
    const assessDeviceCapabilities = () => {
      const capabilities = {
        deviceMemory: navigator.deviceMemory || 4,
        hardwareConcurrency: navigator.hardwareConcurrency || 4,
        connectionType: navigator.connection?.effectiveType || '4g',
        isMobile: /Mobi|Android/i.test(navigator.userAgent),
        prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
      };

      setDeviceCapabilities(capabilities);

      // Determine performance level
      let level = 'high';
      
      if (capabilities.prefersReducedMotion) {
        level = 'low';
      } else if (capabilities.isMobile && capabilities.deviceMemory < 4) {
        level = 'low';
      } else if (capabilities.deviceMemory < 6 || capabilities.hardwareConcurrency < 4) {
        level = 'medium';
      }

      setPerformanceLevel(level);
    };

    assessDeviceCapabilities();

    // Monitor connection changes
    if (navigator.connection) {
      navigator.connection.addEventListener('change', assessDeviceCapabilities);
      return () => {
        navigator.connection.removeEventListener('change', assessDeviceCapabilities);
      };
    }
  }, []);

  const getOptimizedSettings = useCallback((highSettings, mediumSettings, lowSettings) => {
    switch (performanceLevel) {
      case 'high':
        return highSettings;
      case 'medium':
        return mediumSettings;
      case 'low':
        return lowSettings;
      default:
        return highSettings;
    }
  }, [performanceLevel]);

  return {
    performanceLevel,
    deviceCapabilities,
    getOptimizedSettings
  };
};

/**
 * Error boundary HOC with performance recovery
 * @param {React.Component} Component - Component to wrap
 * @param {Function} onError - Error handler
 * @param {Function} performanceRecovery - Performance recovery callback
 */
export const withPerformanceErrorBoundary = (Component, onError, performanceRecovery) => {
  return class PerformanceErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { 
        hasError: false, 
        error: null, 
        errorCount: 0,
        performanceMode: 'normal'
      };
    }

    static getDerivedStateFromError(error) {
      return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
      console.error('Performance error boundary:', error, errorInfo);
      
      this.setState(prevState => ({
        errorCount: prevState.errorCount + 1
      }));

      // If multiple errors, switch to performance recovery mode
      if (this.state.errorCount > 2 && performanceRecovery) {
        this.setState({ performanceMode: 'recovery' });
        performanceRecovery();
      }

      if (onError) {
        onError(error, errorInfo);
      }
    }

    handleRetry = () => {
      this.setState({ 
        hasError: false, 
        error: null,
        performanceMode: this.state.errorCount > 1 ? 'safe' : 'normal'
      });
    };

    render() {
      if (this.state.hasError) {
        return (
          <div className="p-4 bg-red-900/20 border border-red-600/50 rounded-lg">
            <h3 className="text-red-400 font-semibold mb-2">Performance Error</h3>
            <p className="text-red-300 text-sm mb-3">
              {this.state.error?.message || 'An unexpected performance error occurred'}
            </p>
            <button
              onClick={this.handleRetry}
              className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition text-sm"
            >
              Retry {this.state.performanceMode === 'safe' ? '(Safe Mode)' : ''}
            </button>
          </div>
        );
      }

      return <Component {...this.props} performanceMode={this.state.performanceMode} />;
    }
  };
};

/**
 * Optimized image component with lazy loading and performance monitoring
 */
export const PerformanceOptimizedImage = memo(({ 
  src, 
  alt, 
  className, 
  placeholder, 
  onLoad,
  onError,
  ...props 
}) => {
  const [imageState, setImageState] = useState({
    loaded: false,
    error: false,
    loadTime: 0
  });
  const loadStartTimeRef = useRef(0);
  const imageRef = useRef(null);

  const handleImageLoad = useCallback((event) => {
    const loadTime = performance.now() - loadStartTimeRef.current;
    setImageState(prev => ({ ...prev, loaded: true, loadTime }));
    
    if (onLoad) onLoad(event);
    
    // Log slow loading images
    if (loadTime > 1000) {
      console.warn(`Slow image load: ${src} took ${loadTime.toFixed(0)}ms`);
    }
  }, [src, onLoad]);

  const handleImageError = useCallback((event) => {
    setImageState(prev => ({ ...prev, error: true }));
    if (onError) onError(event);
  }, [onError]);

  useEffect(() => {
    if (src) {
      loadStartTimeRef.current = performance.now();
      setImageState({ loaded: false, error: false, loadTime: 0 });
    }
  }, [src]);

  return (
    <div className={className} {...props}>
      {src && !imageState.error && (
        <img
          ref={imageRef}
          src={src}
          alt={alt}
          onLoad={handleImageLoad}
          onError={handleImageError}
          style={{
            opacity: imageState.loaded ? 1 : 0,
            transition: 'opacity 0.3s ease'
          }}
        />
      )}
      {(!imageState.loaded || imageState.error) && placeholder && (
        <div className="bg-gray-800 animate-pulse rounded">
          {imageState.error ? (
            <div className="text-gray-400 p-4 text-center text-sm">
              Failed to load image
            </div>
          ) : (
            placeholder
          )}
        </div>
      )}
    </div>
  );
});

PerformanceOptimizedImage.displayName = 'PerformanceOptimizedImage';