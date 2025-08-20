/**
 * React Performance Optimizer
 * Advanced hooks and components for React performance optimization
 */

import React, { 
  memo, 
  useCallback, 
  useMemo, 
  useState, 
  useEffect, 
  useRef, 
  Suspense,
  startTransition,
  useDeferredValue,
  useTransition
} from 'react';

/**
 * Higher-order component for performance optimization with advanced memoization
 */
export const withPerformanceOptimization = (Component, options = {}) => {
  const {
    skipProps = [],
    deepCompare = false,
    measurePerformance = false,
    errorBoundary = true
  } = options;

  const OptimizedComponent = memo(React.forwardRef((props, ref) => {
    const renderCountRef = useRef(0);
    const lastRenderTimeRef = useRef(performance.now());

    useEffect(() => {
      renderCountRef.current += 1;
      const currentTime = performance.now();
      const renderTime = currentTime - lastRenderTimeRef.current;
      
      if (measurePerformance && process.env.NODE_ENV === 'development') {
        console.log(`${Component.displayName || Component.name} - Render #${renderCountRef.current}, Time: ${renderTime.toFixed(2)}ms`);
      }
      
      lastRenderTimeRef.current = currentTime;
    });

    return <Component {...props} ref={ref} />;
  }), (prevProps, nextProps) => {
    // Custom comparison logic
    const prevKeys = Object.keys(prevProps).filter(key => !skipProps.includes(key));
    const nextKeys = Object.keys(nextProps).filter(key => !skipProps.includes(key));

    if (prevKeys.length !== nextKeys.length) {
      return false;
    }

    for (let key of prevKeys) {
      const prevValue = prevProps[key];
      const nextValue = nextProps[key];

      if (deepCompare && typeof prevValue === 'object' && typeof nextValue === 'object') {
        if (JSON.stringify(prevValue) !== JSON.stringify(nextValue)) {
          return false;
        }
      } else if (prevValue !== nextValue) {
        return false;
      }
    }

    return true;
  });

  OptimizedComponent.displayName = `withPerformanceOptimization(${Component.displayName || Component.name})`;

  if (errorBoundary) {
    return class ErrorBoundary extends React.Component {
      constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
      }

      static getDerivedStateFromError(error) {
        return { hasError: true, error };
      }

      componentDidCatch(error, errorInfo) {
        console.error('Component error caught by performance optimizer:', error, errorInfo);
      }

      render() {
        if (this.state.hasError) {
          return (
            <div className="p-4 bg-red-900/20 border border-red-600/50 rounded-lg">
              <h3 className="text-red-400 font-semibold mb-2">Component Error</h3>
              <p className="text-red-300 text-sm">{this.state.error?.message || 'An unexpected error occurred'}</p>
            </div>
          );
        }

        return <OptimizedComponent {...this.props} />;
      }
    };
  }

  return OptimizedComponent;
};

/**
 * Hook for optimized state updates with batching and transitions
 */
export const useOptimizedState = (initialValue, options = {}) => {
  const { 
    debounceTime = 0, 
    enableTransition = false,
    batchUpdates = true 
  } = options;

  const [state, setState] = useState(initialValue);
  const [isPending, startTransition] = useTransition();
  const timeoutRef = useRef(null);
  const pendingValueRef = useRef(initialValue);

  const optimizedSetState = useCallback((newValue) => {
    const valueToSet = typeof newValue === 'function' ? newValue(pendingValueRef.current) : newValue;
    pendingValueRef.current = valueToSet;

    if (debounceTime > 0) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        if (enableTransition) {
          startTransition(() => {
            setState(valueToSet);
          });
        } else {
          setState(valueToSet);
        }
      }, debounceTime);
    } else {
      if (enableTransition) {
        startTransition(() => {
          setState(valueToSet);
        });
      } else if (batchUpdates) {
        // Use React 18's automatic batching
        setState(valueToSet);
      } else {
        // Force synchronous update
        React.flushSync(() => {
          setState(valueToSet);
        });
      }
    }
  }, [debounceTime, enableTransition, batchUpdates]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [state, optimizedSetState, isPending];
};

/**
 * Hook for deferred values with priority scheduling
 */
export const useDeferredOptimizedValue = (value, options = {}) => {
  const { 
    priority = 'normal', // 'low', 'normal', 'high'
    timeSlice = 5 // milliseconds per time slice
  } = options;

  const deferredValue = useDeferredValue(value);
  const [processedValue, setProcessedValue] = useState(value);
  const processingRef = useRef(false);

  useEffect(() => {
    if (deferredValue === processedValue || processingRef.current) {
      return;
    }

    processingRef.current = true;

    const processValue = () => {
      try {
        // Simulate processing work that can be interrupted
        const startTime = performance.now();
        
        // Process in small time slices to avoid blocking
        const processChunk = () => {
          if (performance.now() - startTime < timeSlice) {
            // Continue processing
            setProcessedValue(deferredValue);
            processingRef.current = false;
          } else {
            // Yield to browser and continue later
            setTimeout(processChunk, 0);
          }
        };

        if (priority === 'high') {
          // Process immediately for high priority
          setProcessedValue(deferredValue);
          processingRef.current = false;
        } else if (priority === 'low') {
          // Use requestIdleCallback for low priority
          if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
              setProcessedValue(deferredValue);
              processingRef.current = false;
            });
          } else {
            setTimeout(() => {
              setProcessedValue(deferredValue);
              processingRef.current = false;
            }, 16); // ~60fps fallback
          }
        } else {
          // Normal priority with time slicing
          processChunk();
        }
      } catch (error) {
        console.error('Error processing deferred value:', error);
        setProcessedValue(deferredValue);
        processingRef.current = false;
      }
    };

    processValue();
  }, [deferredValue, processedValue, priority, timeSlice]);

  return processedValue;
};

/**
 * Hook for virtualized scrolling with dynamic sizing
 */
export const useVirtualizedList = (items, options = {}) => {
  const {
    itemHeight = 50,
    containerHeight = 400,
    overscan = 5,
    estimateHeight = null,
    onScroll = null
  } = options;

  const [scrollOffset, setScrollOffset] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState(new Map());
  const containerRef = useRef(null);
  const itemRefs = useRef(new Map());

  // Calculate visible range
  const visibleRange = useMemo(() => {
    let currentOffset = 0;
    let startIndex = 0;
    let endIndex = 0;

    // Find start index
    for (let i = 0; i < items.length; i++) {
      const height = measuredHeights.get(i) || estimateHeight?.(i) || itemHeight;
      if (currentOffset + height > scrollOffset) {
        startIndex = Math.max(0, i - overscan);
        break;
      }
      currentOffset += height;
    }

    // Find end index
    currentOffset = 0;
    for (let i = 0; i < items.length; i++) {
      const height = measuredHeights.get(i) || estimateHeight?.(i) || itemHeight;
      if (i >= startIndex) {
        currentOffset += height;
        if (currentOffset >= containerHeight + (overscan * itemHeight)) {
          endIndex = Math.min(items.length - 1, i + overscan);
          break;
        }
      }
    }

    return { startIndex, endIndex: endIndex || items.length - 1 };
  }, [items.length, scrollOffset, containerHeight, overscan, itemHeight, measuredHeights, estimateHeight]);

  // Calculate total height and offset
  const { totalHeight, offsetY } = useMemo(() => {
    let total = 0;
    let offset = 0;

    for (let i = 0; i < items.length; i++) {
      const height = measuredHeights.get(i) || estimateHeight?.(i) || itemHeight;
      if (i < visibleRange.startIndex) {
        offset += height;
      }
      total += height;
    }

    return { totalHeight: total, offsetY: offset };
  }, [items.length, visibleRange.startIndex, measuredHeights, estimateHeight, itemHeight]);

  // Get visible items
  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.startIndex, visibleRange.endIndex + 1).map((item, index) => ({
      item,
      index: visibleRange.startIndex + index,
      key: `${visibleRange.startIndex + index}`
    }));
  }, [items, visibleRange.startIndex, visibleRange.endIndex]);

  // Handle scroll
  const handleScroll = useCallback((event) => {
    const newScrollOffset = event.target.scrollTop;
    setScrollOffset(newScrollOffset);
    onScroll?.(newScrollOffset);
  }, [onScroll]);

  // Measure item height
  const measureItem = useCallback((index, element) => {
    if (element) {
      const height = element.getBoundingClientRect().height;
      setMeasuredHeights(prev => new Map(prev).set(index, height));
      itemRefs.current.set(index, element);
    }
  }, []);

  return {
    containerRef,
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll,
    measureItem,
    scrollToIndex: useCallback((index) => {
      if (containerRef.current) {
        let offset = 0;
        for (let i = 0; i < index; i++) {
          offset += measuredHeights.get(i) || estimateHeight?.(i) || itemHeight;
        }
        containerRef.current.scrollTop = offset;
      }
    }, [measuredHeights, estimateHeight, itemHeight])
  };
};

/**
 * Hook for optimized event handlers with automatic cleanup
 */
export const useOptimizedEventHandler = (eventType, handler, element = window, options = {}) => {
  const { 
    throttle = 0, 
    debounce = 0, 
    passive = true,
    capture = false 
  } = options;

  const handlerRef = useRef(handler);
  const timeoutRef = useRef(null);
  const lastCallRef = useRef(0);

  // Update handler ref when handler changes
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  // Create optimized handler
  const optimizedHandler = useCallback((event) => {
    const now = Date.now();

    if (debounce > 0) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        handlerRef.current(event);
      }, debounce);
    } else if (throttle > 0) {
      if (now - lastCallRef.current >= throttle) {
        lastCallRef.current = now;
        handlerRef.current(event);
      }
    } else {
      handlerRef.current(event);
    }
  }, [debounce, throttle]);

  useEffect(() => {
    const targetElement = element?.current || element;
    if (!targetElement || !targetElement.addEventListener) {
      return;
    }

    const eventOptions = { passive, capture };
    targetElement.addEventListener(eventType, optimizedHandler, eventOptions);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      targetElement.removeEventListener(eventType, optimizedHandler, eventOptions);
    };
  }, [eventType, optimizedHandler, element, passive, capture]);
};

/**
 * Hook for component visibility detection with performance optimization
 */
export const useVisibilityOptimization = (options = {}) => {
  const {
    threshold = 0,
    rootMargin = '0px',
    freezeOnceVisible = true,
    triggerOnce = false
  } = options;

  const [isVisible, setIsVisible] = useState(false);
  const [hasBeenVisible, setHasBeenVisible] = useState(false);
  const elementRef = useRef(null);
  const observerRef = useRef(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !('IntersectionObserver' in window)) {
      return;
    }

    // Don't observe if already been visible and triggerOnce is true
    if (hasBeenVisible && triggerOnce) {
      return;
    }

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        const isElementVisible = entry.isIntersecting;
        
        if (!freezeOnceVisible || !hasBeenVisible) {
          setIsVisible(isElementVisible);
        }

        if (isElementVisible && !hasBeenVisible) {
          setHasBeenVisible(true);
        }

        // Disconnect after first visibility if triggerOnce is true
        if (isElementVisible && triggerOnce) {
          observerRef.current?.disconnect();
        }
      },
      { threshold, rootMargin }
    );

    observerRef.current.observe(element);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [threshold, rootMargin, freezeOnceVisible, triggerOnce, hasBeenVisible]);

  return {
    elementRef,
    isVisible,
    hasBeenVisible
  };
};

/**
 * Performance-optimized list component with virtualization
 */
export const OptimizedList = memo(({
  items,
  renderItem,
  itemHeight = 50,
  height = 400,
  width = '100%',
  overscan = 5,
  onScroll,
  className = '',
  estimateHeight,
  ...props
}) => {
  const {
    containerRef,
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll,
    measureItem
  } = useVirtualizedList(items, {
    itemHeight,
    containerHeight: height,
    overscan,
    onScroll,
    estimateHeight
  });

  return (
    <div
      ref={containerRef}
      className={`overflow-auto ${className}`}
      style={{ height, width }}
      onScroll={handleScroll}
      {...props}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetY}px)` }}>
          {visibleItems.map(({ item, index, key }) => (
            <div
              key={key}
              ref={(el) => measureItem(index, el)}
              style={{ minHeight: itemHeight }}
            >
              {renderItem(item, index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

OptimizedList.displayName = 'OptimizedList';

/**
 * Lazy component with preloading capabilities
 */
export const createOptimizedLazyComponent = (importFn, options = {}) => {
  const {
    fallback = <div className="animate-pulse bg-gray-800 h-32 rounded"></div>,
    preloadDelay = 2000,
    errorFallback = <div className="text-red-400">Failed to load component</div>
  } = options;

  const LazyComponent = React.lazy(importFn);
  let preloadTimer = null;

  const OptimizedLazyComponent = React.forwardRef((props, ref) => {
    const [error, setError] = useState(null);

    const preload = useCallback(() => {
      if (preloadTimer) return;
      
      preloadTimer = setTimeout(() => {
        importFn().catch(err => {
          console.warn('Preload failed:', err);
          setError(err);
        });
      }, preloadDelay);
    }, []);

    useEffect(() => {
      return () => {
        if (preloadTimer) {
          clearTimeout(preloadTimer);
          preloadTimer = null;
        }
      };
    }, []);

    if (error) {
      return errorFallback;
    }

    return (
      <div onMouseEnter={preload} onFocus={preload}>
        <Suspense fallback={fallback}>
          <LazyComponent {...props} ref={ref} />
        </Suspense>
      </div>
    );
  });

  OptimizedLazyComponent.displayName = `OptimizedLazy(${LazyComponent.name || 'Component'})`;
  OptimizedLazyComponent.preload = () => importFn();

  return OptimizedLazyComponent;
};

export default {
  withPerformanceOptimization,
  useOptimizedState,
  useDeferredOptimizedValue,
  useVirtualizedList,
  useOptimizedEventHandler,
  useVisibilityOptimization,
  OptimizedList,
  createOptimizedLazyComponent
};