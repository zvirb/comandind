// import { oauth } from './oauth'; // Not needed for base auth functionality

// Request deduplication and rate limiting for SecureAuth
const RequestManager = {
  activeRequests: new Map(),
  rateLimiter: {
    attempts: 0,
    lastAttempt: 0,
    backoffMs: 1000,
    maxBackoffMs: 30000
  },
  
  // Deduplicate requests by key
  async makeRequest(key, requestFn) {
    if (this.activeRequests.has(key)) {
      console.log(`SecureAuth: Returning existing request for ${key}`);
      return this.activeRequests.get(key);
    }
    
    const promise = (async () => {
      try {
        return await requestFn();
      } finally {
        this.activeRequests.delete(key);
      }
    })();
    
    this.activeRequests.set(key, promise);
    return promise;
  },
  
  // Check if we should rate limit
  shouldRateLimit() {
    const now = Date.now();
    const timeSinceLastAttempt = now - this.rateLimiter.lastAttempt;
    
    if (this.rateLimiter.attempts >= 3 && timeSinceLastAttempt < this.rateLimiter.backoffMs) {
      return true;
    }
    
    // Reset if enough time has passed
    if (timeSinceLastAttempt > this.rateLimiter.backoffMs * 2) {
      this.rateLimiter.attempts = 0;
      this.rateLimiter.backoffMs = 1000;
    }
    
    return false;
  },
  
  // Record request attempt
  recordAttempt(success = true) {
    const now = Date.now();
    this.rateLimiter.lastAttempt = now;
    
    if (!success) {
      this.rateLimiter.attempts += 1;
      this.rateLimiter.backoffMs = Math.min(
        this.rateLimiter.backoffMs * 2,
        this.rateLimiter.maxBackoffMs
      );
    } else {
      this.rateLimiter.attempts = 0;
      this.rateLimiter.backoffMs = 1000;
    }
  }
};

const SecureAuth = {
    // Get stored authentication token (aligned with unified backend)
    getAuthToken: () => {
        // Primary: Check cookies first (unified backend preference)
        return document.cookie
            .split('; ')
            .find(row => row.startsWith('access_token='))
            ?.split('=')[1] || 
            // Fallback: localStorage for backward compatibility
            localStorage.getItem('authToken') || 
            localStorage.getItem('access_token') ||
            localStorage.getItem('jwt_token') ||
            sessionStorage.getItem('authToken');
    },

    // Store authentication token (use cookies for unified backend compatibility)
    setAuthToken: (token) => {
        // Store in localStorage for backward compatibility
        localStorage.setItem('authToken', token);
        // Note: Cookies are managed by backend via set_auth_cookies()
    },

    // Remove authentication token (clear all storage)
    clearAuthToken: () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('access_token');
        localStorage.removeItem('jwt_token');
        sessionStorage.removeItem('authToken');
        // Clear cookies by setting expiration date in past
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    },

    // Get CSRF token from cookies
    getCSRFToken: () => {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='))
            ?.split('=')[1];
    },

    // Check if user is authenticated with rate limiting and deduplication
    isAuthenticated: async () => {
        return RequestManager.makeRequest('isAuthenticated', async () => {
            console.log('SecureAuth.isAuthenticated: Starting unified check...');
            
            // Rate limiting check
            if (RequestManager.shouldRateLimit()) {
                console.log('SecureAuth.isAuthenticated: Rate limited, assuming not authenticated');
                RequestManager.recordAttempt(false);
                return false;
            }
            
            try {
                // First check if we have a valid token
                const token = SecureAuth.getAuthToken();
                console.log('SecureAuth.isAuthenticated: Token exists:', !!token);
                
                if (token) {
                    try {
                        // Basic JWT validation
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        const currentTime = Date.now() / 1000;
                        
                        // Validate unified backend format
                        const requiredFields = ['sub', 'email', 'id', 'role', 'session_id'];
                        const hasUnifiedFormat = requiredFields.every(field => field in payload);
                        
                        if (payload.exp > currentTime && hasUnifiedFormat) {
                            console.log('SecureAuth.isAuthenticated: Valid unified token found');
                            RequestManager.recordAttempt(true);
                            return true;
                        }
                    } catch (error) {
                        console.error('Token validation error:', error);
                        SecureAuth.clearAuthToken();
                    }
                }
                
                // Check authentication via unified backend with timeout
                console.log('SecureAuth.isAuthenticated: Checking unified backend authentication...');
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout
                
                const response = await fetch('/api/v1/auth/validate', {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    },
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    const data = await response.json();
                    const isValid = data.valid === true;
                    RequestManager.recordAttempt(isValid);
                    return isValid;
                }
                
                console.log('SecureAuth.isAuthenticated: Authentication validation failed');
                RequestManager.recordAttempt(false);
                return false;
                
            } catch (error) {
                console.error('Authentication check failed:', error);
                RequestManager.recordAttempt(false);
                return false;
            }
        });
    },

    // Token refresh with deduplication and rate limiting
    refreshToken: async () => {
        return RequestManager.makeRequest('refreshToken', async () => {
            // Rate limiting check
            if (RequestManager.shouldRateLimit()) {
                console.log('SecureAuth.refreshToken: Rate limited');
                RequestManager.recordAttempt(false);
                return false;
            }
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);
                
                const response = await fetch('/api/v1/auth/refresh', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    console.log('SecureAuth.refreshToken: Token refreshed successfully');
                    RequestManager.recordAttempt(true);
                    return true;
                }
                
                console.log('SecureAuth.refreshToken: Token refresh failed, status:', response.status);
                RequestManager.recordAttempt(false);
                return false;
                
            } catch (error) {
                console.error('Token refresh error:', error);
                RequestManager.recordAttempt(false);
                return false;
            }
        });
    },

    // Enhanced secure request with retry logic and deduplication
    makeSecureRequest: async (url, options = {}) => {
        const requestKey = `${options.method || 'GET'}_${url}_${JSON.stringify(options.body || {})}`;
        
        return RequestManager.makeRequest(requestKey, async () => {
            const token = SecureAuth.getAuthToken();
            const csrfToken = SecureAuth.getCSRFToken();
            
            const headers = {
                ...options.headers
            };

            // Only set Content-Type if not FormData
            if (!(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
            }

            // Add Authorization header if token available
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Add CSRF token for state-changing requests
            if (csrfToken && ['POST', 'PUT', 'DELETE', 'PATCH'].includes((options.method || 'GET').toUpperCase())) {
                headers['X-CSRF-TOKEN'] = csrfToken;
            }

            const requestOptions = {
                ...options,
                headers,
                credentials: 'include'
            };

            try {
                // Add timeout to prevent hanging requests
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
                
                const response = await fetch(url, { 
                    ...requestOptions, 
                    signal: controller.signal 
                });
                
                clearTimeout(timeoutId);
                
                // Handle 401 with single retry attempt
                if (response.status === 401) {
                    console.log('SecureAuth.makeSecureRequest: 401 detected, attempting token refresh...');
                    
                    const refreshed = await SecureAuth.refreshToken();
                    if (refreshed) {
                        const newToken = SecureAuth.getAuthToken();
                        if (newToken) {
                            headers['Authorization'] = `Bearer ${newToken}`;
                        }
                        
                        const retryResponse = await fetch(url, { ...requestOptions, headers });
                        if (retryResponse.ok || retryResponse.status !== 401) {
                            return retryResponse;
                        }
                    }
                    
                    // Authentication failed after retry
                    console.log('SecureAuth.makeSecureRequest: Authentication failed after retry');
                    SecureAuth.clearAuthToken();
                    window.location.href = '/login';
                    throw new Error('Authentication required');
                }
                
                // Handle 429 Too Many Requests
                if (response.status === 429) {
                    console.warn('SecureAuth.makeSecureRequest: Rate limited by server');
                    RequestManager.recordAttempt(false);
                    throw new Error('Rate limited by server');
                }
                
                return response;
                
            } catch (error) {
                console.error('Secure request error:', error);
                
                // Record failed attempts for rate limiting
                if (error.name === 'AbortError') {
                    RequestManager.recordAttempt(false);
                }
                
                throw error;
            }
        });
    },

    // Handle authentication failure
    handleAuthenticationFailure: () => {
        console.log('SecureAuth.handleAuthenticationFailure: Clearing tokens and redirecting to login');
        SecureAuth.clearAuthToken();
        window.location.href = '/login';
    },

    // Logout user (unified backend compatible)
    logout: async () => {
        console.log('SecureAuth.logout: Starting unified logout...');
        
        try {
            // Call unified backend logout endpoint
            const response = await fetch('/api/v1/auth/logout', {
                method: 'POST',
                credentials: 'include', // Include cookies
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('SecureAuth.logout: Backend logout response:', response.status);
        } catch (error) {
            console.error('Backend logout failed:', error);
        }
        
        // Clear frontend tokens regardless of backend response
        SecureAuth.clearAuthToken();
        
        // Redirect to login
        window.location.href = '/login';
    }
};

const PKCEUtils = {
    // Generate PKCE code verifier and challenge
    generatePKCE: () => {
        const codeVerifier = PKCEUtils.generateCodeVerifier();
        const codeChallenge = PKCEUtils.generateCodeChallenge(codeVerifier);
        
        return {
            codeVerifier,
            codeChallenge,
            codeChallengeMethod: 'S256'
        };
    },

    // Generate random code verifier
    generateCodeVerifier: () => {
        const array = new Uint32Array(56/2);
        crypto.getRandomValues(array);
        return Array.from(array, dec => ('0' + dec.toString(16)).substr(-2)).join('');
    },

    // Generate code challenge from verifier
    generateCodeChallenge: async (verifier) => {
        const encoder = new TextEncoder();
        const data = encoder.encode(verifier);
        const digest = await crypto.subtle.digest('SHA-256', data);
        return btoa(String.fromCharCode(...new Uint8Array(digest)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    },

    // Store PKCE verifier securely
    storePKCEVerifier: (verifier) => {
        sessionStorage.setItem('pkce_verifier', verifier);
    },

    // Retrieve stored PKCE verifier
    retrievePKCEVerifier: () => {
        const verifier = sessionStorage.getItem('pkce_verifier');
        sessionStorage.removeItem('pkce_verifier'); // One-time use
        return verifier;
    }
};

const OAuthStateManager = {
    // Generate secure state token
    generateStateToken: (service) => {
        const randomBytes = new Uint8Array(32);
        crypto.getRandomValues(randomBytes);
        const state = Array.from(randomBytes, byte => byte.toString(16).padStart(2, '0')).join('');
        const stateWithService = `${service}_${state}`;
        
        // Store state for validation
        sessionStorage.setItem('oauth_state', stateWithService);
        return stateWithService;
    },

    // Validate state token
    validateStateToken: (receivedState, expectedService) => {
        const storedState = sessionStorage.getItem('oauth_state');
        sessionStorage.removeItem('oauth_state'); // One-time use
        
        if (!storedState || !receivedState) {
            return false;
        }
        
        return storedState === receivedState && receivedState.startsWith(expectedService);
    }
};

const LegacyAuthBridge = {
    // Bridge for legacy authentication methods
    migrateToSecureAuth: () => {
        // Check for legacy tokens and migrate them
        const legacyToken = localStorage.getItem('token') || 
                           localStorage.getItem('user_token') ||
                           sessionStorage.getItem('token');
        
        if (legacyToken && !SecureAuth.getAuthToken()) {
            SecureAuth.setAuthToken(legacyToken);
            // Clean up legacy tokens
            localStorage.removeItem('token');
            localStorage.removeItem('user_token');
            sessionStorage.removeItem('token');
        }
    }
};

// Initialize authentication on module load
try {
    LegacyAuthBridge.migrateToSecureAuth();
} catch (error) {
    console.error('Auth migration error:', error);
}

export { SecureAuth, PKCEUtils, OAuthStateManager, LegacyAuthBridge };
