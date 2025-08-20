/**
 * Advanced Performance Optimization Utilities
 * Enhanced with dynamic imports, service workers, and advanced caching
 */

import React, { memo, useCallback, useMemo, useState, useEffect, useRef, Suspense, lazy } from 'react';

/**
 * Advanced lazy loading with preloading and error boundaries
 */
export const createLazyComponent = (importFn, fallback = null, preload = false) => {
  const LazyComponent = lazy(importFn);
  
  // Preload on hover or focus
  const preloadComponent = () => {
    importFn().catch(err => console.warn('Preload failed:', err));
  };

  const WithPreload = React.forwardRef((props, ref) => (
    <div 
      onMouseEnter={preload ? preloadComponent : undefined}
      onFocus={preload ? preloadComponent : undefined}
    >
      <Suspense fallback={fallback}>
        <LazyComponent {...props} ref={ref} />
      </Suspense>
    </div>
  ));

  WithPreload.displayName = `LazyWithPreload(${LazyComponent.name || 'Component'})`;
  WithPreload.preload = preloadComponent;

  return WithPreload;
};

/**
 * Smart chunk loading hook with priority and caching
 */
export const useSmartChunkLoading = (chunks, priority = 'low') => {
  const [loadedChunks, setLoadedChunks] = useState(new Set());
  const [loadingChunks, setLoadingChunks] = useState(new Set());
  const abortControllerRef = useRef(new AbortController());

  const loadChunk = useCallback(async (chunkName, chunkLoader) => {
    if (loadedChunks.has(chunkName) || loadingChunks.has(chunkName)) {
      return;
    }

    setLoadingChunks(prev => new Set([...prev, chunkName]));

    try {
      // Use scheduler for priority-based loading
      if ('scheduler' in window && window.scheduler.postTask) {
        await window.scheduler.postTask(chunkLoader, { 
          priority: priority,
          signal: abortControllerRef.current.signal 
        });
      } else {
        await chunkLoader();
      }
      
      setLoadedChunks(prev => new Set([...prev, chunkName]));
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.warn(`Failed to load chunk ${chunkName}:`, error);
      }
    } finally {
      setLoadingChunks(prev => {
        const next = new Set(prev);
        next.delete(chunkName);
        return next;
      });
    }
  }, [loadedChunks, loadingChunks, priority]);

  const loadChunks = useCallback(() => {
    chunks.forEach(({ name, loader }) => {
      loadChunk(name, loader);
    });
  }, [chunks, loadChunk]);

  useEffect(() => {
    return () => {
      abortControllerRef.current.abort();
    };
  }, []);

  return {
    loadChunks,
    loadedChunks,
    loadingChunks,
    isChunkLoaded: (chunkName) => loadedChunks.has(chunkName),
    isChunkLoading: (chunkName) => loadingChunks.has(chunkName)
  };
};

/**
 * Advanced virtual scrolling with dynamic item sizing
 */
export const useAdvancedVirtualScrolling = (
  items, 
  estimatedItemHeight = 50, 
  containerHeight, 
  overscan = 5,
  getItemHeight = null
) => {
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState(new Map());
  const scrollElementRef = useRef(null);

  const getItemHeightMemoized = useCallback((index) => {
    if (getItemHeight) {
      return getItemHeight(index);
    }
    return measuredHeights.get(index) || estimatedItemHeight;
  }, [getItemHeight, measuredHeights, estimatedItemHeight]);

  const { startIndex, endIndex, totalHeight, offsetY } = useMemo(() => {
    let accumulatedHeight = 0;
    let startIdx = 0;
    let endIdx = 0;
    
    // Find start index
    for (let i = 0; i < items.length; i++) {
      const itemHeight = getItemHeightMemoized(i);
      if (accumulatedHeight + itemHeight > scrollTop) {
        startIdx = Math.max(0, i - overscan);
        break;
      }
      accumulatedHeight += itemHeight;
    }

    // Find end index
    let visibleHeight = 0;
    for (let i = startIdx; i < items.length; i++) {
      const itemHeight = getItemHeightMemoized(i);
      visibleHeight += itemHeight;
      if (visibleHeight >= containerHeight + (overscan * estimatedItemHeight)) {
        endIdx = Math.min(items.length - 1, i + overscan);
        break;
      }
    }

    // Calculate total height
    const totalH = items.reduce((acc, _, index) => {
      return acc + getItemHeightMemoized(index);
    }, 0);

    // Calculate offset
    let offsetHeight = 0;
    for (let i = 0; i < startIdx; i++) {
      offsetHeight += getItemHeightMemoized(i);
    }

    return {
      startIndex: startIdx,
      endIndex: endIdx || items.length - 1,
      totalHeight: totalH,
      offsetY: offsetHeight
    };
  }, [items, scrollTop, containerHeight, overscan, estimatedItemHeight, getItemHeightMemoized]);

  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex + 1).map((item, index) => ({
      ...item,
      index: startIndex + index
    }));
  }, [items, startIndex, endIndex]);

  const handleScroll = useCallback((e) => {
    setScrollTop(e.target.scrollTop);
  }, []);

  const measureItem = useCallback((index, height) => {
    setMeasuredHeights(prev => {
      const next = new Map(prev);
      next.set(index, height);
      return next;
    });
  }, []);

  return {
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll,
    scrollElementRef,
    measureItem,
    startIndex,
    endIndex
  };
};

/**
 * Smart image loading with WebP support and progressive enhancement
 */
export const useSmartImageLoading = (src, options = {}) => {
  const [currentSrc, setCurrentSrc] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quality, setQuality] = useState('placeholder');
  
  const {
    placeholder = null,
    lowQuality = null,
    formats = ['webp', 'jpg'],
    sizes = '(max-width: 768px) 100vw, 50vw',
    priority = false
  } = options;

  useEffect(() => {
    let isCancelled = false;
    
    const loadImage = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Check WebP support
        const supportsWebP = await new Promise((resolve) => {
          const webp = new Image();
          webp.onload = webp.onerror = () => resolve(webp.height === 2);
          webp.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
        });

        // Determine best format
        const format = supportsWebP && formats.includes('webp') ? 'webp' : 'jpg';
        const imageSrc = typeof src === 'object' ? src[format] || src.jpg || src : src;

        // Load low quality first if available
        if (lowQuality && !isCancelled) {
          setCurrentSrc(lowQuality);
          setQuality('low');
        }

        // Load full quality image
        const img = new Image();
        
        if (priority) {
          img.loading = 'eager';
        }

        img.onload = () => {
          if (!isCancelled) {
            setCurrentSrc(imageSrc);
            setQuality('high');
            setIsLoading(false);
          }
        };

        img.onerror = () => {
          if (!isCancelled) {
            setError(new Error('Failed to load image'));
            setIsLoading(false);
          }
        };

        img.src = imageSrc;
        
      } catch (err) {
        if (!isCancelled) {
          setError(err);
          setIsLoading(false);
        }
      }
    };

    loadImage();

    return () => {
      isCancelled = true;
    };
  }, [src, lowQuality, formats, priority]);

  return {
    src: currentSrc,
    isLoading,
    error,
    quality
  };
};

/**
 * Resource preloading hook
 */
export const useResourcePreloading = () => {
  const preloadedResources = useRef(new Set());

  const preloadResource = useCallback((href, type = 'script', options = {}) => {
    if (preloadedResources.current.has(href)) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.href = href;
      link.as = type;
      
      if (options.crossorigin) {
        link.crossOrigin = options.crossorigin;
      }
      
      if (options.type) {
        link.type = options.type;
      }

      link.onload = () => {
        preloadedResources.current.add(href);
        resolve();
      };
      
      link.onerror = () => {
        reject(new Error(`Failed to preload ${href}`));
      };

      document.head.appendChild(link);
    });
  }, []);

  const preloadScript = useCallback((src, options = {}) => {
    return preloadResource(src, 'script', { type: 'text/javascript', ...options });
  }, [preloadResource]);

  const preloadStyle = useCallback((href, options = {}) => {
    return preloadResource(href, 'style', { type: 'text/css', ...options });
  }, [preloadResource]);

  const preloadImage = useCallback((src, options = {}) => {
    return preloadResource(src, 'image', options);
  }, [preloadResource]);

  const preloadFont = useCallback((href, options = {}) => {
    return preloadResource(href, 'font', { 
      type: 'font/woff2', 
      crossorigin: 'anonymous', 
      ...options 
    });
  }, [preloadResource]);

  return {
    preloadScript,
    preloadStyle,
    preloadImage,
    preloadFont,
    preloadResource
  };
};

/**
 * Performance budget monitoring
 */
export const usePerformanceBudget = (budgets = {}) => {
  const [metrics, setMetrics] = useState({});
  const [violations, setViolations] = useState([]);
  
  const defaultBudgets = {
    FCP: 1500, // First Contentful Paint
    LCP: 2500, // Largest Contentful Paint
    FID: 100,  // First Input Delay
    CLS: 0.1,  // Cumulative Layout Shift
    TTFB: 600, // Time to First Byte
    ...budgets
  };

  useEffect(() => {
    if (!('PerformanceObserver' in window)) {
      return;
    }

    const observers = [];

    // Observe Web Vitals
    const observeMetric = (type, callback) => {
      try {
        const observer = new PerformanceObserver((list) => {
          list.getEntries().forEach(callback);
        });
        observer.observe({ type, buffered: true });
        observers.push(observer);
      } catch (e) {
        console.warn(`Failed to observe ${type}:`, e);
      }
    };

    // First Contentful Paint
    observeMetric('paint', (entry) => {
      if (entry.name === 'first-contentful-paint') {
        const value = entry.startTime;
        setMetrics(prev => ({ ...prev, FCP: value }));
        
        if (value > defaultBudgets.FCP) {
          setViolations(prev => [...prev, {
            metric: 'FCP',
            value,
            budget: defaultBudgets.FCP,
            timestamp: Date.now()
          }]);
        }
      }
    });

    // Largest Contentful Paint
    observeMetric('largest-contentful-paint', (entry) => {
      const value = entry.startTime;
      setMetrics(prev => ({ ...prev, LCP: value }));
      
      if (value > defaultBudgets.LCP) {
        setViolations(prev => [...prev, {
          metric: 'LCP',
          value,
          budget: defaultBudgets.LCP,
          timestamp: Date.now()
        }]);
      }
    });

    // Layout Shift
    observeMetric('layout-shift', (entry) => {
      if (!entry.hadRecentInput) {
        setMetrics(prev => ({ 
          ...prev, 
          CLS: (prev.CLS || 0) + entry.value 
        }));
      }
    });

    // Navigation timing
    const navigationObserver = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        const ttfb = entry.responseStart - entry.requestStart;
        setMetrics(prev => ({ ...prev, TTFB: ttfb }));
        
        if (ttfb > defaultBudgets.TTFB) {
          setViolations(prev => [...prev, {
            metric: 'TTFB',
            value: ttfb,
            budget: defaultBudgets.TTFB,
            timestamp: Date.now()
          }]);
        }
      });
    });

    try {
      navigationObserver.observe({ type: 'navigation', buffered: true });
      observers.push(navigationObserver);
    } catch (e) {
      console.warn('Failed to observe navigation:', e);
    }

    return () => {
      observers.forEach(observer => observer.disconnect());
    };
  }, [defaultBudgets]);

  return {
    metrics,
    violations,
    budgets: defaultBudgets,
    isWithinBudget: (metric) => {
      const value = metrics[metric];
      const budget = defaultBudgets[metric];
      return value ? value <= budget : null;
    }
  };
};

/**
 * Advanced caching hook with service worker integration
 */
export const useAdvancedCaching = () => {
  const [isServiceWorkerSupported, setIsServiceWorkerSupported] = useState(false);
  const [isServiceWorkerReady, setIsServiceWorkerReady] = useState(false);
  const [serviceWorkerError, setServiceWorkerError] = useState(null);
  
  useEffect(() => {
    const initServiceWorker = async () => {
      if ('serviceWorker' in navigator) {
        setIsServiceWorkerSupported(true);
        
        try {
          // Register service worker with enhanced error handling
          const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/',
            updateViaCache: 'imports'
          });
          
          console.log('[AdvancedCaching] Service Worker registered:', registration);
          
          // Handle service worker updates
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            console.log('[AdvancedCaching] Service Worker update found');
            
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('[AdvancedCaching] New Service Worker ready');
                // Optionally notify user about update
              }
            });
          });
          
          // Wait for service worker to be ready
          await navigator.serviceWorker.ready;
          setIsServiceWorkerReady(true);
          setServiceWorkerError(null);
          
        } catch (error) {
          console.warn('[AdvancedCaching] Service Worker registration failed:', error);
          setServiceWorkerError(error.message);
          // Continue without service worker
        }
      } else {
        console.warn('[AdvancedCaching] Service Workers not supported');
      }
    };
    
    initServiceWorker();
  }, []);

  const cacheResource = useCallback(async (url, data, options = {}) => {
    const { 
      ttl = 3600000, // 1 hour default
      storage = 'memory' // 'memory', 'localStorage', 'indexedDB'
    } = options;

    const cacheKey = `cache_${url}`;
    const cacheData = {
      data,
      timestamp: Date.now(),
      ttl
    };

    try {
      switch (storage) {
        case 'localStorage':
          localStorage.setItem(cacheKey, JSON.stringify(cacheData));
          break;
        case 'indexedDB':
          // Implement IndexedDB caching for large data
          break;
        default:
          // Memory cache using Map
          if (!window.__performanceCache) {
            window.__performanceCache = new Map();
          }
          window.__performanceCache.set(cacheKey, cacheData);
      }
    } catch (error) {
      console.warn('Failed to cache resource:', error);
    }
  }, []);

  const getCachedResource = useCallback((url, storage = 'memory') => {
    const cacheKey = `cache_${url}`;
    
    try {
      let cacheData;
      
      switch (storage) {
        case 'localStorage':
          const stored = localStorage.getItem(cacheKey);
          cacheData = stored ? JSON.parse(stored) : null;
          break;
        default:
          cacheData = window.__performanceCache?.get(cacheKey);
      }

      if (cacheData) {
        const isExpired = Date.now() - cacheData.timestamp > cacheData.ttl;
        if (!isExpired) {
          return cacheData.data;
        } else {
          // Clean up expired cache
          if (storage === 'localStorage') {
            localStorage.removeItem(cacheKey);
          } else {
            window.__performanceCache?.delete(cacheKey);
          }
        }
      }
    } catch (error) {
      console.warn('Failed to get cached resource:', error);
    }

    return null;
  }, []);

  const clearCache = useCallback((pattern = null) => {
    try {
      if (pattern) {
        // Clear specific pattern
        if (window.__performanceCache) {
          for (const [key] of window.__performanceCache) {
            if (key.includes(pattern)) {
              window.__performanceCache.delete(key);
            }
          }
        }
        
        // Clear from localStorage
        for (let i = localStorage.length - 1; i >= 0; i--) {
          const key = localStorage.key(i);
          if (key && key.includes(pattern)) {
            localStorage.removeItem(key);
          }
        }
      } else {
        // Clear all
        window.__performanceCache?.clear();
        localStorage.clear();
      }
    } catch (error) {
      console.warn('Failed to clear cache:', error);
    }
  }, []);

  return {
    isServiceWorkerSupported,
    isServiceWorkerReady,
    cacheResource,
    getCachedResource,
    clearCache
  };
};

export default {
  createLazyComponent,
  useSmartChunkLoading,
  useAdvancedVirtualScrolling,
  useSmartImageLoading,
  useResourcePreloading,
  usePerformanceBudget,
  useAdvancedCaching
};