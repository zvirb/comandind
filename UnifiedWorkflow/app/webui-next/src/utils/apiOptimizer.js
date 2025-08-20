/**
 * API Optimization and Caching System
 * Advanced caching, batching, and performance optimization for API calls
 */

import { useState, useCallback, useRef, useEffect } from 'react';

class APIOptimizer {
  constructor(options = {}) {
    this.options = {
      baseURL: options.baseURL || '/api',
      timeout: options.timeout || 10000,
      maxCacheSize: options.maxCacheSize || 100,
      defaultCacheTTL: options.defaultCacheTTL || 300000, // 5 minutes
      maxRetries: options.maxRetries || 3,
      retryDelay: options.retryDelay || 1000,
      enableBatching: options.enableBatching !== false,
      batchDelay: options.batchDelay || 10,
      enableCompression: options.enableCompression !== false,
      ...options
    };

    // Cache storage
    this.cache = new Map();
    this.cacheTimestamps = new Map();
    this.cachePriorities = new Map();

    // Request batching
    this.batchQueue = new Map();
    this.batchTimeouts = new Map();

    // Request deduplication
    this.pendingRequests = new Map();

    // Performance monitoring
    this.stats = {
      totalRequests: 0,
      cacheHits: 0,
      cacheMisses: 0,
      networkRequests: 0,
      batchedRequests: 0,
      errors: 0,
      avgResponseTime: 0,
      totalResponseTime: 0
    };

    // Request interceptors
    this.requestInterceptors = [];
    this.responseInterceptors = [];

    this.initializeCache();
  }

  /**
   * Initialize cache with cleanup mechanisms
   */
  initializeCache() {
    // Periodic cache cleanup
    this.cacheCleanupInterval = setInterval(() => {
      this.cleanupExpiredCache();
    }, 60000); // Clean every minute

    // Memory pressure handling
    if ('memory' in performance) {
      this.memoryMonitorInterval = setInterval(() => {
        const memory = performance.memory;
        const memoryUsage = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
        
        if (memoryUsage > 0.8) {
          console.warn('High memory usage, clearing API cache');
          this.clearCache();
        }
      }, 30000);
    }
  }

  /**
   * Add request interceptor
   */
  addRequestInterceptor(interceptor) {
    this.requestInterceptors.push(interceptor);
    return () => {
      const index = this.requestInterceptors.indexOf(interceptor);
      if (index > -1) {
        this.requestInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Add response interceptor
   */
  addResponseInterceptor(interceptor) {
    this.responseInterceptors.push(interceptor);
    return () => {
      const index = this.responseInterceptors.indexOf(interceptor);
      if (index > -1) {
        this.responseInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Main request method with optimization
   */
  async request(config) {
    const startTime = performance.now();
    this.stats.totalRequests++;

    try {
      // Apply request interceptors
      let processedConfig = { ...config };
      for (const interceptor of this.requestInterceptors) {
        processedConfig = await interceptor(processedConfig);
      }

      // Normalize config
      const normalizedConfig = this.normalizeConfig(processedConfig);
      const cacheKey = this.generateCacheKey(normalizedConfig);

      // Check cache first
      if (normalizedConfig.cache !== false) {
        const cachedResponse = this.getCachedResponse(cacheKey);
        if (cachedResponse) {
          this.stats.cacheHits++;
          this.updateResponseTime(startTime);
          return cachedResponse;
        }
        this.stats.cacheMisses++;
      }

      // Check for pending identical requests (deduplication)
      if (this.pendingRequests.has(cacheKey)) {
        return await this.pendingRequests.get(cacheKey);
      }

      // Create request promise
      const requestPromise = this.executeRequest(normalizedConfig);
      this.pendingRequests.set(cacheKey, requestPromise);

      try {
        const response = await requestPromise;
        
        // Apply response interceptors
        let processedResponse = response;
        for (const interceptor of this.responseInterceptors) {
          processedResponse = await interceptor(processedResponse, normalizedConfig);
        }

        // Cache successful responses
        if (normalizedConfig.cache !== false && response.ok) {
          this.setCachedResponse(cacheKey, processedResponse, normalizedConfig.cacheTTL);
        }

        this.updateResponseTime(startTime);
        return processedResponse;

      } finally {
        this.pendingRequests.delete(cacheKey);
      }

    } catch (error) {
      this.stats.errors++;
      this.updateResponseTime(startTime);
      throw this.enhanceError(error, config);
    }
  }

  /**
   * Execute HTTP request with retries and optimization
   */
  async executeRequest(config) {
    const { url, method = 'GET', data, headers = {}, timeout, retries = this.options.maxRetries } = config;
    
    // Setup request options
    const requestOptions = {
      method: method.toUpperCase(),
      headers: {
        'Content-Type': 'application/json',
        ...headers
      },
      signal: AbortSignal.timeout(timeout || this.options.timeout)
    };

    // Add request body for non-GET requests
    if (data && method.toLowerCase() !== 'get') {
      if (this.options.enableCompression && JSON.stringify(data).length > 1024) {
        // Compress large payloads
        requestOptions.body = await this.compressData(data);
        requestOptions.headers['Content-Encoding'] = 'gzip';
      } else {
        requestOptions.body = JSON.stringify(data);
      }
    }

    // Attempt request with retries
    let lastError;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        this.stats.networkRequests++;
        
        const response = await fetch(this.buildURL(url), requestOptions);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Parse response
        const contentType = response.headers.get('content-type');
        let responseData;
        
        if (contentType && contentType.includes('application/json')) {
          responseData = await response.json();
        } else {
          responseData = await response.text();
        }

        return {
          data: responseData,
          status: response.status,
          headers: Object.fromEntries(response.headers.entries()),
          ok: response.ok,
          url: response.url
        };

      } catch (error) {
        lastError = error;
        
        // Don't retry on certain errors
        if (error.name === 'AbortError' || 
            (error.message && error.message.includes('HTTP 4'))) {
          break;
        }

        // Wait before retry
        if (attempt < retries) {
          await this.delay(this.options.retryDelay * Math.pow(2, attempt));
        }
      }
    }

    throw lastError;
  }

  /**
   * Batch multiple requests together
   */
  async batchRequest(requests) {
    if (!this.options.enableBatching || requests.length === 1) {
      return Promise.all(requests.map(req => this.request(req)));
    }

    this.stats.batchedRequests += requests.length;

    // Group requests by endpoint for batching
    const batchGroups = new Map();
    
    requests.forEach((request, index) => {
      const batchKey = `${request.method || 'GET'}_${request.url}`;
      if (!batchGroups.has(batchKey)) {
        batchGroups.set(batchKey, []);
      }
      batchGroups.get(batchKey).push({ ...request, _originalIndex: index });
    });

    // Execute batched requests
    const results = new Array(requests.length);
    const promises = [];

    for (const [batchKey, batchRequests] of batchGroups) {
      if (batchRequests.length === 1) {
        // Single request, execute normally
        const request = batchRequests[0];
        promises.push(
          this.request(request).then(result => {
            results[request._originalIndex] = result;
          })
        );
      } else {
        // Multiple requests, create batch request
        promises.push(
          this.executeBatchRequest(batchRequests).then(batchResults => {
            batchResults.forEach((result, i) => {
              results[batchRequests[i]._originalIndex] = result;
            });
          })
        );
      }
    }

    await Promise.all(promises);
    return results;
  }

  /**
   * Execute a batch of similar requests
   */
  async executeBatchRequest(requests) {
    const batchPayload = requests.map(req => ({
      id: req._originalIndex,
      method: req.method || 'GET',
      url: req.url,
      data: req.data,
      headers: req.headers
    }));

    const batchResponse = await this.request({
      url: '/batch',
      method: 'POST',
      data: { requests: batchPayload },
      cache: false
    });

    return batchResponse.data.responses;
  }

  /**
   * Smart caching with priority and TTL
   */
  setCachedResponse(key, response, ttl = this.options.defaultCacheTTL) {
    // Implement cache size limit with LRU eviction
    if (this.cache.size >= this.options.maxCacheSize) {
      this.evictLRUCache();
    }

    this.cache.set(key, response);
    this.cacheTimestamps.set(key, Date.now());
    this.cachePriorities.set(key, Date.now()); // Use timestamp as priority

    // Set custom TTL if provided
    if (ttl !== this.options.defaultCacheTTL) {
      setTimeout(() => {
        this.cache.delete(key);
        this.cacheTimestamps.delete(key);
        this.cachePriorities.delete(key);
      }, ttl);
    }
  }

  /**
   * Get cached response if valid
   */
  getCachedResponse(key) {
    if (!this.cache.has(key)) {
      return null;
    }

    const timestamp = this.cacheTimestamps.get(key);
    const age = Date.now() - timestamp;

    if (age > this.options.defaultCacheTTL) {
      this.cache.delete(key);
      this.cacheTimestamps.delete(key);
      this.cachePriorities.delete(key);
      return null;
    }

    // Update priority (move to end for LRU)
    this.cachePriorities.set(key, Date.now());
    return this.cache.get(key);
  }

  /**
   * Evict least recently used cache entries
   */
  evictLRUCache() {
    // Find oldest entry by priority
    let oldestKey = null;
    let oldestPriority = Infinity;

    for (const [key, priority] of this.cachePriorities) {
      if (priority < oldestPriority) {
        oldestPriority = priority;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey);
      this.cacheTimestamps.delete(oldestKey);
      this.cachePriorities.delete(oldestKey);
    }
  }

  /**
   * Clean up expired cache entries
   */
  cleanupExpiredCache() {
    const now = Date.now();
    const toDelete = [];

    for (const [key, timestamp] of this.cacheTimestamps) {
      if (now - timestamp > this.options.defaultCacheTTL) {
        toDelete.push(key);
      }
    }

    toDelete.forEach(key => {
      this.cache.delete(key);
      this.cacheTimestamps.delete(key);
      this.cachePriorities.delete(key);
    });

    if (toDelete.length > 0) {
      console.log(`Cleaned up ${toDelete.length} expired cache entries`);
    }
  }

  /**
   * Generate cache key from request config
   */
  generateCacheKey(config) {
    const { url, method = 'GET', data, headers } = config;
    const keyData = {
      url,
      method: method.toUpperCase(),
      data: data || null,
      // Only include cache-relevant headers
      headers: headers ? this.filterCacheableHeaders(headers) : null
    };
    
    return btoa(JSON.stringify(keyData));
  }

  /**
   * Filter headers that should affect caching
   */
  filterCacheableHeaders(headers) {
    const cacheableHeaders = ['authorization', 'x-api-key', 'accept-language'];
    const filtered = {};
    
    for (const [key, value] of Object.entries(headers)) {
      if (cacheableHeaders.includes(key.toLowerCase())) {
        filtered[key] = value;
      }
    }
    
    return filtered;
  }

  /**
   * Normalize request configuration
   */
  normalizeConfig(config) {
    return {
      url: config.url,
      method: (config.method || 'GET').toUpperCase(),
      data: config.data || null,
      headers: config.headers || {},
      timeout: config.timeout || this.options.timeout,
      cache: config.cache !== false,
      cacheTTL: config.cacheTTL || this.options.defaultCacheTTL,
      retries: config.retries !== undefined ? config.retries : this.options.maxRetries
    };
  }

  /**
   * Build full URL
   */
  buildURL(url) {
    if (url.startsWith('http')) {
      return url;
    }
    return `${this.options.baseURL}${url.startsWith('/') ? '' : '/'}${url}`;
  }

  /**
   * Compress data for large payloads
   */
  async compressData(data) {
    const jsonString = JSON.stringify(data);
    
    if ('CompressionStream' in window) {
      const stream = new CompressionStream('gzip');
      const writer = stream.writable.getWriter();
      const reader = stream.readable.getReader();
      
      writer.write(new TextEncoder().encode(jsonString));
      writer.close();
      
      const chunks = [];
      let done = false;
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          chunks.push(value);
        }
      }
      
      return new Uint8Array(chunks.reduce((acc, chunk) => [...acc, ...chunk], []));
    }
    
    // Fallback to uncompressed
    return jsonString;
  }

  /**
   * Enhance error with additional context
   */
  enhanceError(error, config) {
    const enhancedError = new Error(error.message);
    enhancedError.name = error.name;
    enhancedError.config = config;
    enhancedError.timestamp = Date.now();
    enhancedError.stack = error.stack;
    
    // Add network information if available
    if ('connection' in navigator) {
      enhancedError.networkInfo = {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      };
    }
    
    return enhancedError;
  }

  /**
   * Update response time statistics
   */
  updateResponseTime(startTime) {
    const responseTime = performance.now() - startTime;
    this.stats.totalResponseTime += responseTime;
    this.stats.avgResponseTime = this.stats.totalResponseTime / this.stats.totalRequests;
  }

  /**
   * Utility delay function
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get performance statistics
   */
  getStats() {
    return {
      ...this.stats,
      cacheHitRatio: this.stats.totalRequests > 0 
        ? (this.stats.cacheHits / this.stats.totalRequests * 100).toFixed(2) + '%'
        : '0%',
      cacheSize: this.cache.size,
      avgResponseTime: Math.round(this.stats.avgResponseTime * 100) / 100
    };
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.cache.clear();
    this.cacheTimestamps.clear();
    this.cachePriorities.clear();
    console.log('API cache cleared');
  }

  /**
   * Preload data
   */
  async preload(configs) {
    const preloadPromises = configs.map(config => 
      this.request({ ...config, priority: 'low' }).catch(error => {
        console.warn('Preload failed:', error);
        return null;
      })
    );
    
    const results = await Promise.allSettled(preloadPromises);
    const successful = results.filter(r => r.status === 'fulfilled').length;
    
    console.log(`Preloaded ${successful}/${configs.length} requests`);
    return results;
  }

  /**
   * Cleanup resources
   */
  dispose() {
    if (this.cacheCleanupInterval) {
      clearInterval(this.cacheCleanupInterval);
    }
    
    if (this.memoryMonitorInterval) {
      clearInterval(this.memoryMonitorInterval);
    }
    
    this.clearCache();
    this.pendingRequests.clear();
    this.batchQueue.clear();
    
    for (const timeout of this.batchTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.batchTimeouts.clear();
    
    console.log('API Optimizer disposed');
  }
}

// React hooks for API optimization
export const useOptimizedAPI = (apiOptimizer) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const request = useCallback(async (config) => {
    // Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setLoading(true);
    setError(null);

    try {
      const response = await apiOptimizer.request({
        ...config,
        signal: abortControllerRef.current.signal
      });
      
      return response;
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err);
        throw err;
      }
    } finally {
      setLoading(false);
    }
  }, [apiOptimizer]);

  const batch = useCallback(async (configs) => {
    setLoading(true);
    setError(null);

    try {
      const responses = await apiOptimizer.batchRequest(configs);
      return responses;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiOptimizer]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    request,
    batch,
    loading,
    error,
    stats: apiOptimizer.getStats()
  };
};

// Create singleton instance
const apiOptimizer = new APIOptimizer({
  baseURL: '/api',
  maxCacheSize: 200,
  defaultCacheTTL: 300000, // 5 minutes
  enableBatching: true,
  enableCompression: true
});

export default apiOptimizer;