/**
 * Service Worker for AI Workflow Engine
 * Implements caching strategies with proper error handling and fallbacks
 */

const CACHE_NAME = 'aiwfe-v1.0.0';
const RUNTIME_CACHE = 'aiwfe-runtime';

// Cache static assets
const STATIC_CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Network timeout for fetch requests
const NETWORK_TIMEOUT = 5000;

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[ServiceWorker] Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[ServiceWorker] Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .catch(error => {
        console.warn('[ServiceWorker] Failed to cache static assets:', error);
        // Continue installation even if caching fails
      })
  );
  
  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
              console.log('[ServiceWorker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .catch(error => {
        console.warn('[ServiceWorker] Failed to clean old caches:', error);
      })
  );
  
  // Take control immediately
  self.clients.claim();
});

// Helper function to create timeout promise
const timeoutPromise = (timeout) => {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Network timeout')), timeout);
  });
};

// Enhanced fetch handler with robust error handling
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-HTTP requests
  if (!url.protocol.startsWith('http')) {
    return;
  }
  
  // Skip Chrome extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }
  
  // Enhanced caching strategy with fallbacks
  event.respondWith(
    handleRequest(request)
      .catch(error => {
        console.warn('[ServiceWorker] Request failed:', error);
        return handleRequestFallback(request);
      })
  );
});

/**
 * Main request handler with caching strategy
 */
async function handleRequest(request) {
  const url = new URL(request.url);
  
  // For API requests, use network-first with timeout
  if (url.pathname.startsWith('/api/')) {
    return handleApiRequest(request);
  }
  
  // For static assets, use cache-first
  if (isStaticAsset(url.pathname)) {
    return handleStaticAsset(request);
  }
  
  // For HTML pages, use stale-while-revalidate
  if (request.destination === 'document') {
    return handleDocumentRequest(request);
  }
  
  // Default: network with cache fallback
  return handleDefaultRequest(request);
}

/**
 * Handle API requests with network-first strategy
 */
async function handleApiRequest(request) {
  try {
    // Try network first with timeout
    const networkResponse = await Promise.race([
      fetch(request.clone()),
      timeoutPromise(NETWORK_TIMEOUT)
    ]);
    
    if (networkResponse.ok) {
      return networkResponse;
    }
    
    throw new Error(`API request failed: ${networkResponse.status}`);
  } catch (error) {
    console.warn('[ServiceWorker] API request failed, checking cache:', error);
    
    // Fallback to cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('[ServiceWorker] Serving API response from cache');
      return cachedResponse;
    }
    
    // Return error response if no cache available
    return new Response(
      JSON.stringify({ 
        error: 'Service unavailable', 
        message: 'API is currently offline',
        offline: true 
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Handle static assets with cache-first strategy
 */
async function handleStaticAsset(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Update cache in background
    fetch(request).then(response => {
      if (response.ok) {
        caches.open(RUNTIME_CACHE).then(cache => {
          cache.put(request, response.clone());
        });
      }
    }).catch(() => {
      // Ignore background update failures
    });
    
    return cachedResponse;
  }
  
  // If not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      // Cache successful responses
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.warn('[ServiceWorker] Failed to fetch static asset:', error);
    throw error;
  }
}

/**
 * Handle document requests with stale-while-revalidate
 */
async function handleDocumentRequest(request) {
  const cachedResponse = await caches.match(request);
  
  // Always try to update in background
  const networkResponsePromise = fetch(request)
    .then(response => {
      if (response.ok) {
        caches.open(RUNTIME_CACHE).then(cache => {
          cache.put(request, response.clone());
        });
      }
      return response;
    })
    .catch(error => {
      console.warn('[ServiceWorker] Background document update failed:', error);
    });
  
  // Return cached version immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Otherwise wait for network
  return networkResponsePromise;
}

/**
 * Default request handler
 */
async function handleDefaultRequest(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok && request.method === 'GET') {
      // Cache successful GET requests
      const cache = await caches.open(RUNTIME_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    // Try cache as fallback
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

/**
 * Fallback handler for failed requests
 */
async function handleRequestFallback(request) {
  const url = new URL(request.url);
  
  // For HTML requests, return offline page
  if (request.destination === 'document') {
    return new Response(
      `<!DOCTYPE html>
      <html>
      <head>
        <title>Offline - AI Workflow Engine</title>
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
          .offline { color: #666; }
        </style>
      </head>
      <body>
        <div class="offline">
          <h1>You're offline</h1>
          <p>Please check your internet connection and try again.</p>
          <button onclick="location.reload()">Retry</button>
        </div>
      </body>
      </html>`,
      {
        status: 200,
        headers: { 'Content-Type': 'text/html' }
      }
    );
  }
  
  // For API requests, return structured error
  if (url.pathname.startsWith('/api/')) {
    return new Response(
      JSON.stringify({
        error: 'Network error',
        message: 'Unable to connect to server',
        offline: true
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
  
  // For other requests, return generic error
  return new Response('Network error', { status: 503 });
}

/**
 * Check if request is for a static asset
 */
function isStaticAsset(pathname) {
  const staticExtensions = [
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', 
    '.woff', '.woff2', '.ttf', '.eot', '.ico'
  ];
  
  return staticExtensions.some(ext => pathname.endsWith(ext));
}

// Handle service worker errors
self.addEventListener('error', event => {
  console.error('[ServiceWorker] Error:', event.error);
});

// Handle unhandled promise rejections
self.addEventListener('unhandledrejection', event => {
  console.error('[ServiceWorker] Unhandled rejection:', event.reason);
  event.preventDefault();
});

console.log('[ServiceWorker] Registered successfully');