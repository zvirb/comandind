/**
 * Offline Manager
 * Handles offline functionality, caching, and sync when online
 */

import { notifications } from './notificationSystem';

class OfflineManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.listeners = new Set();
    this.cache = new Map();
    this.pendingRequests = [];
    this.cachePrefix = 'aiwfe_cache_';
    this.maxCacheSize = 50; // Maximum cached items
    this.cacheExpiry = 24 * 60 * 60 * 1000; // 24 hours

    this.initializeListeners();
    this.loadCacheFromStorage();
  }

  /**
   * Initialize network status listeners
   */
  initializeListeners() {
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));
    
    // Listen for visibility change to check connection when app becomes visible
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
  }

  /**
   * Handle online event
   */
  handleOnline() {
    this.isOnline = true;
    notifications.handleConnectivity(true);
    this.notifyListeners(true);
    this.processPendingRequests();
  }

  /**
   * Handle offline event
   */
  handleOffline() {
    this.isOnline = false;
    notifications.handleConnectivity(false);
    this.notifyListeners(false);
  }

  /**
   * Handle visibility change (check connection when app becomes visible)
   */
  handleVisibilityChange() {
    if (!document.hidden) {
      this.checkConnection();
    }
  }

  /**
   * Check actual network connection (beyond navigator.onLine)
   */
  async checkConnection() {
    try {
      const response = await fetch('/api/health', {
        method: 'HEAD',
        cache: 'no-cache',
        timeout: 5000
      });
      
      const wasOnline = this.isOnline;
      this.isOnline = response.ok;
      
      if (wasOnline !== this.isOnline) {
        if (this.isOnline) {
          this.handleOnline();
        } else {
          this.handleOffline();
        }
      }
    } catch (error) {
      if (this.isOnline) {
        this.handleOffline();
      }
    }
  }

  /**
   * Add listener for online/offline status changes
   * @param {Function} callback - Callback function
   */
  addListener(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Notify all listeners of status change
   * @param {boolean} isOnline - Current online status
   */
  notifyListeners(isOnline) {
    this.listeners.forEach(callback => callback(isOnline));
  }

  /**
   * Get current online status
   */
  getOnlineStatus() {
    return this.isOnline;
  }

  /**
   * Cache data with expiry
   * @param {string} key - Cache key
   * @param {any} data - Data to cache
   */
  cacheData(key, data) {
    const cacheItem = {
      data,
      timestamp: Date.now(),
      expires: Date.now() + this.cacheExpiry
    };

    this.cache.set(key, cacheItem);
    this.saveCacheToStorage();
    
    // Clean up old entries if cache is too large
    if (this.cache.size > this.maxCacheSize) {
      this.cleanupCache();
    }
  }

  /**
   * Get cached data
   * @param {string} key - Cache key
   * @returns {any|null} Cached data or null if not found/expired
   */
  getCachedData(key) {
    const cacheItem = this.cache.get(key);
    
    if (!cacheItem) {
      return null;
    }

    // Check if expired
    if (Date.now() > cacheItem.expires) {
      this.cache.delete(key);
      return null;
    }

    return cacheItem.data;
  }

  /**
   * Clean up expired cache entries
   */
  cleanupCache() {
    const now = Date.now();
    const entriesToDelete = [];

    for (const [key, item] of this.cache.entries()) {
      if (now > item.expires) {
        entriesToDelete.push(key);
      }
    }

    // If not enough expired entries, remove oldest entries
    if (entriesToDelete.length === 0 && this.cache.size > this.maxCacheSize) {
      const sortedEntries = Array.from(this.cache.entries())
        .sort(([,a], [,b]) => a.timestamp - b.timestamp);
      
      const itemsToRemove = sortedEntries.slice(0, this.cache.size - this.maxCacheSize);
      entriesToDelete.push(...itemsToRemove.map(([key]) => key));
    }

    entriesToDelete.forEach(key => this.cache.delete(key));
    this.saveCacheToStorage();
  }

  /**
   * Save cache to localStorage
   */
  saveCacheToStorage() {
    try {
      const cacheData = Object.fromEntries(this.cache);
      localStorage.setItem(`${this.cachePrefix}data`, JSON.stringify(cacheData));
    } catch (error) {
      console.error('Failed to save cache to storage:', error);
    }
  }

  /**
   * Load cache from localStorage
   */
  loadCacheFromStorage() {
    try {
      const cacheData = localStorage.getItem(`${this.cachePrefix}data`);
      if (cacheData) {
        const parsedData = JSON.parse(cacheData);
        this.cache = new Map(Object.entries(parsedData));
        this.cleanupCache(); // Clean expired entries
      }
    } catch (error) {
      console.error('Failed to load cache from storage:', error);
      this.cache = new Map();
    }
  }

  /**
   * Make a request with offline support
   * @param {string} url - Request URL
   * @param {Object} options - Fetch options
   * @param {Object} cacheOptions - Cache configuration
   */
  async makeRequest(url, options = {}, cacheOptions = {}) {
    const {
      cacheKey = url,
      useCache = true,
      cacheFirst = false,
      skipCacheOnError = false
    } = cacheOptions;

    // Check cache first if requested or offline
    if ((cacheFirst || !this.isOnline) && useCache) {
      const cachedData = this.getCachedData(cacheKey);
      if (cachedData) {
        return {
          data: cachedData,
          fromCache: true,
          online: this.isOnline
        };
      }
    }

    // If offline and no cache, queue the request
    if (!this.isOnline) {
      return this.queueRequest(url, options, cacheOptions);
    }

    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Cache successful responses
      if (useCache) {
        this.cacheData(cacheKey, data);
      }

      return {
        data,
        fromCache: false,
        online: true,
        response
      };
    } catch (error) {
      // Try cache as fallback if request fails
      if (skipCacheOnError && useCache) {
        const cachedData = this.getCachedData(cacheKey);
        if (cachedData) {
          return {
            data: cachedData,
            fromCache: true,
            online: this.isOnline,
            error
          };
        }
      }

      throw error;
    }
  }

  /**
   * Queue request for when online
   * @param {string} url - Request URL
   * @param {Object} options - Fetch options
   * @param {Object} cacheOptions - Cache configuration
   */
  queueRequest(url, options, cacheOptions) {
    return new Promise((resolve, reject) => {
      this.pendingRequests.push({
        url,
        options,
        cacheOptions,
        resolve,
        reject,
        timestamp: Date.now()
      });

      // Notify user that request is queued
      notifications.info('Request queued for when connection is restored', {
        title: 'Offline Mode',
        duration: 3000
      });
    });
  }

  /**
   * Process pending requests when back online
   */
  async processPendingRequests() {
    const requests = [...this.pendingRequests];
    this.pendingRequests = [];

    if (requests.length > 0) {
      notifications.info(`Processing ${requests.length} queued requests`, {
        title: 'Syncing Data',
        duration: 2000
      });
    }

    for (const request of requests) {
      try {
        const result = await this.makeRequest(
          request.url,
          request.options,
          request.cacheOptions
        );
        request.resolve(result);
      } catch (error) {
        request.reject(error);
      }
    }
  }

  /**
   * Clear all cached data
   */
  clearCache() {
    this.cache.clear();
    try {
      localStorage.removeItem(`${this.cachePrefix}data`);
    } catch (error) {
      console.error('Failed to clear cache from storage:', error);
    }
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    const now = Date.now();
    let expiredCount = 0;
    let totalSize = 0;

    for (const [key, item] of this.cache.entries()) {
      if (now > item.expires) {
        expiredCount++;
      }
      totalSize += JSON.stringify(item).length;
    }

    return {
      totalItems: this.cache.size,
      expiredItems: expiredCount,
      approximateSize: totalSize,
      maxSize: this.maxCacheSize
    };
  }
}

// Create global instance
const offlineManager = new OfflineManager();

// Export convenience functions
export const offline = {
  isOnline: () => offlineManager.getOnlineStatus(),
  addListener: (callback) => offlineManager.addListener(callback),
  makeRequest: (url, options, cacheOptions) => offlineManager.makeRequest(url, options, cacheOptions),
  cacheData: (key, data) => offlineManager.cacheData(key, data),
  getCachedData: (key) => offlineManager.getCachedData(key),
  clearCache: () => offlineManager.clearCache(),
  getCacheStats: () => offlineManager.getCacheStats(),
  checkConnection: () => offlineManager.checkConnection()
};

export default offlineManager;