/**
 * Performance Optimization Utilities
 * Provides tools for React performance, lazy loading, and virtual scrolling
 */

import React, { memo, useCallback, useMemo, useState, useEffect, useRef } from 'react';

/**
 * Higher-order component for React.memo with custom comparison
 * @param {React.Component} Component - Component to memoize
 * @param {Function} areEqual - Custom comparison function
 */
export const withMemo = (Component, areEqual) => {
  return memo(Component, areEqual);
};

/**
 * Deep comparison function for complex props
 * @param {Object} prevProps - Previous props
 * @param {Object} nextProps - Next props
 */
export const deepPropsEqual = (prevProps, nextProps) => {
  const keys1 = Object.keys(prevProps);
  const keys2 = Object.keys(nextProps);

  if (keys1.length !== keys2.length) {
    return false;
  }

  for (let key of keys1) {
    if (prevProps[key] !== nextProps[key]) {
      // For objects and arrays, do a shallow comparison
      if (typeof prevProps[key] === 'object' && typeof nextProps[key] === 'object') {
        if (JSON.stringify(prevProps[key]) !== JSON.stringify(nextProps[key])) {
          return false;
        }
      } else {
        return false;
      }
    }
  }

  return true;
};

/**
 * Optimized list comparison function
 * Only re-renders if list items actually changed
 * @param {Object} prevProps - Previous props
 * @param {Object} nextProps - Next props
 */
export const listPropsEqual = (prevProps, nextProps) => {
  // Compare non-list props normally
  const { items: prevItems, ...prevOtherProps } = prevProps;
  const { items: nextItems, ...nextOtherProps } = nextProps;

  if (!deepPropsEqual(prevOtherProps, nextOtherProps)) {
    return false;
  }

  // Compare list lengths
  if (!prevItems || !nextItems || prevItems.length !== nextItems.length) {
    return false;
  }

  // Compare list items by ID or shallow comparison
  for (let i = 0; i < prevItems.length; i++) {
    const prevItem = prevItems[i];
    const nextItem = nextItems[i];

    if (prevItem.id && nextItem.id) {
      // Compare by ID if available
      if (prevItem.id !== nextItem.id) {
        return false;
      }
    } else {
      // Shallow comparison for objects without ID
      if (JSON.stringify(prevItem) !== JSON.stringify(nextItem)) {
        return false;
      }
    }
  }

  return true;
};

/**
 * Hook for virtual scrolling implementation
 * @param {Array} items - Full list of items
 * @param {number} itemHeight - Height of each item in pixels
 * @param {number} containerHeight - Height of scrollable container
 * @param {number} overscan - Number of items to render outside viewport
 */
export const useVirtualScrolling = (items, itemHeight, containerHeight, overscan = 5) => {
  const [scrollTop, setScrollTop] = useState(0);
  const scrollElementRef = useRef(null);

  const startIndex = useMemo(() => {
    return Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  }, [scrollTop, itemHeight, overscan]);

  const endIndex = useMemo(() => {
    return Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );
  }, [scrollTop, containerHeight, itemHeight, items.length, overscan]);

  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex + 1).map((item, index) => ({
      ...item,
      index: startIndex + index
    }));
  }, [items, startIndex, endIndex]);

  const totalHeight = useMemo(() => {
    return items.length * itemHeight;
  }, [items.length, itemHeight]);

  const offsetY = useMemo(() => {
    return startIndex * itemHeight;
  }, [startIndex, itemHeight]);

  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll,
    scrollElementRef
  };
};

/**
 * Hook for lazy loading with intersection observer
 * @param {Object} options - Intersection observer options
 */
export const useLazyLoading = (options = {}) => {
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const targetRef = useRef(null);

  const defaultOptions = {
    threshold: 0.1,
    rootMargin: '50px',
    ...options
  };

  useEffect(() => {
    const target = targetRef.current;
    if (!target) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !hasLoaded) {
        setIsIntersecting(true);
        setHasLoaded(true);
      }
    }, defaultOptions);

    observer.observe(target);

    return () => {
      if (target) {
        observer.unobserve(target);
      }
    };
  }, [hasLoaded, defaultOptions]);

  return { targetRef, isIntersecting, hasLoaded };
};

/**
 * Hook for debouncing values (useful for search inputs)
 * @param {any} value - Value to debounce
 * @param {number} delay - Delay in milliseconds
 */
export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook for throttling function calls
 * @param {Function} callback - Function to throttle
 * @param {number} delay - Delay in milliseconds
 */
export const useThrottle = (callback, delay) => {
  const throttledCallback = useCallback(
    (...args) => {
      let throttleTimer;
      if (!throttleTimer) {
        throttleTimer = setTimeout(() => {
          callback(...args);
          throttleTimer = null;
        }, delay);
      }
    },
    [callback, delay]
  );

  return throttledCallback;
};

/**
 * Hook for measuring component performance
 * @param {string} componentName - Name of component for logging
 */
export const usePerformanceMonitor = (componentName) => {
  const renderCount = useRef(0);
  const startTime = useRef(performance.now());

  useEffect(() => {
    renderCount.current += 1;
    const endTime = performance.now();
    const renderTime = endTime - startTime.current;

    if (process.env.NODE_ENV === 'development') {
      console.log(`${componentName} rendered ${renderCount.current} times. Last render took ${renderTime.toFixed(2)}ms`);
    }

    startTime.current = endTime;
  });

  return { renderCount: renderCount.current };
};

/**
 * Hook for optimistic updates
 * @param {any} initialData - Initial data value
 * @param {Function} updateFunction - Function to perform actual update
 */
export const useOptimisticUpdate = (initialData, updateFunction) => {
  const [data, setData] = useState(initialData);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState(null);

  const optimisticUpdate = useCallback(async (newData, optimisticData = newData) => {
    // Immediately update UI with optimistic data
    const previousData = data;
    setData(optimisticData);
    setIsUpdating(true);
    setError(null);

    try {
      // Perform actual update
      const result = await updateFunction(newData);
      setData(result || newData);
    } catch (err) {
      // Rollback on error
      setData(previousData);
      setError(err);
      console.error('Optimistic update failed:', err);
    } finally {
      setIsUpdating(false);
    }
  }, [data, updateFunction]);

  return {
    data,
    isUpdating,
    error,
    optimisticUpdate
  };
};

/**
 * HOC for error boundary functionality
 * @param {React.Component} Component - Component to wrap
 * @param {Function} onError - Error handler function
 */
export const withErrorBoundary = (Component, onError) => {
  return class ErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
      return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
      console.error('Component error:', error, errorInfo);
      if (onError) {
        onError(error, errorInfo);
      }
    }

    render() {
      if (this.state.hasError) {
        return (
          <div className="p-4 bg-red-900/20 border border-red-600/50 rounded-lg">
            <h3 className="text-red-400 font-semibold mb-2">Something went wrong</h3>
            <p className="text-red-300 text-sm">{this.state.error?.message || 'An unexpected error occurred'}</p>
          </div>
        );
      }

      return <Component {...this.props} />;
    }
  };
};

/**
 * Image lazy loading component
 */
export const LazyImage = memo(({ src, alt, className, placeholder, ...props }) => {
  const { targetRef, isIntersecting } = useLazyLoading();
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  const handleImageError = useCallback(() => {
    setImageError(true);
  }, []);

  return (
    <div ref={targetRef} className={className} {...props}>
      {isIntersecting && !imageError && (
        <img
          src={src}
          alt={alt}
          onLoad={handleImageLoad}
          onError={handleImageError}
          style={{
            opacity: imageLoaded ? 1 : 0,
            transition: 'opacity 0.3s ease'
          }}
        />
      )}
      {(!isIntersecting || !imageLoaded) && !imageError && placeholder && (
        <div className="bg-gray-800 animate-pulse rounded">
          {placeholder}
        </div>
      )}
      {imageError && (
        <div className="bg-gray-800 text-gray-400 p-4 rounded text-center">
          Failed to load image
        </div>
      )}
    </div>
  );
});

LazyImage.displayName = 'LazyImage';