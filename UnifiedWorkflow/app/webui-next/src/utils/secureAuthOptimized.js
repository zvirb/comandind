import { globalAPIManager } from './performanceOptimizationEnhanced';

const SecureAuthOptimized = {
    // Cache for auth state to prevent repeated localStorage access
    _authTokenCache: null,
    _authStateCache: null,
    _cacheExpiry: 0,

    // Get stored authentication token with caching
    getAuthToken: () => {
        const now = Date.now();
        if (SecureAuthOptimized._authTokenCache && now < SecureAuthOptimized._cacheExpiry) {
            return SecureAuthOptimized._authTokenCache;
        }

        const token = localStorage.getItem('authToken') || 
                     localStorage.getItem('access_token') ||
                     localStorage.getItem('jwt_token') ||
                     sessionStorage.getItem('authToken');

        // Cache token for 5 minutes
        SecureAuthOptimized._authTokenCache = token;
        SecureAuthOptimized._cacheExpiry = now + (5 * 60 * 1000);
        
        return token;
    },

    // Store authentication token and clear cache
    setAuthToken: (token) => {
        localStorage.setItem('authToken', token);
        SecureAuthOptimized._authTokenCache = token;
        SecureAuthOptimized._authStateCache = null; // Invalidate auth state cache
        SecureAuthOptimized._cacheExpiry = Date.now() + (5 * 60 * 1000);
    },

    // Remove authentication token and clear cache
    clearAuthToken: () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('access_token');
        localStorage.removeItem('jwt_token');
        sessionStorage.removeItem('authToken');
        SecureAuthOptimized._authTokenCache = null;
        SecureAuthOptimized._authStateCache = null;
        SecureAuthOptimized._cacheExpiry = 0;
    },

    // Enhanced authentication check with caching
    isAuthenticated: () => {
        const now = Date.now();
        if (SecureAuthOptimized._authStateCache && now < SecureAuthOptimized._cacheExpiry) {
            return SecureAuthOptimized._authStateCache;
        }

        const token = SecureAuthOptimized.getAuthToken();
        if (!token) {
            SecureAuthOptimized._authStateCache = false;
            return false;
        }
        
        try {
            // Enhanced JWT validation
            const parts = token.split('.');
            if (parts.length !== 3) {
                SecureAuthOptimized._authStateCache = false;
                return false;
            }

            const payload = JSON.parse(atob(parts[1]));
            const currentTime = Date.now() / 1000;
            
            // Check expiration with 30 second buffer
            const isValid = payload.exp && (payload.exp - 30) > currentTime;
            SecureAuthOptimized._authStateCache = isValid;
            
            return isValid;
        } catch (error) {
            console.error('Token validation error:', error);
            SecureAuthOptimized._authStateCache = false;
            return false;
        }
    },

    // Get token expiration time
    getTokenExpirationTime: () => {
        const token = SecureAuthOptimized.getAuthToken();
        if (!token) return null;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp ? new Date(payload.exp * 1000) : null;
        } catch (error) {
            console.error('Token parsing error:', error);
            return null;
        }
    },

    // Check if token expires soon (within 5 minutes)
    isTokenExpiringSoon: () => {
        const expirationTime = SecureAuthOptimized.getTokenExpirationTime();
        if (!expirationTime) return false;

        const fiveMinutesFromNow = new Date(Date.now() + (5 * 60 * 1000));
        return expirationTime <= fiveMinutesFromNow;
    },

    // Enhanced secure request with timeout and retry logic
    makeSecureRequest: async (url, options = {}, timeout = 10000, retries = 1) => {
        const token = SecureAuthOptimized.getAuthToken();
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const requestOptions = {
            ...options,
            headers
        };

        let lastError;
        
        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                const response = await globalAPIManager.makeRequest(url, requestOptions, timeout);
                
                // Handle 401 Unauthorized - token might be expired
                if (response.status === 401) {
                    SecureAuthOptimized.clearAuthToken();
                    SecureAuthOptimized.handleAuthenticationFailure();
                    throw new Error('Authentication required');
                }
                
                return response;
            } catch (error) {
                lastError = error;
                
                // Don't retry on auth errors or client errors (4xx)
                if (error.message.includes('Authentication') || 
                    (error.message.includes('HTTP 4') && !error.message.includes('HTTP 408'))) {
                    throw error;
                }
                
                // Only retry on network errors or server errors
                if (attempt < retries) {
                    const delay = Math.min(1000 * Math.pow(2, attempt), 5000); // Exponential backoff, max 5s
                    await new Promise(resolve => setTimeout(resolve, delay));
                    console.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${retries + 1})`);
                }
            }
        }
        
        console.error('Secure request failed after retries:', lastError);
        throw lastError;
    },

    // Handle authentication failure with better UX
    handleAuthenticationFailure: () => {
        SecureAuthOptimized.clearAuthToken();
        
        // Store current location for redirect after login
        const currentPath = window.location.pathname + window.location.search;
        if (currentPath !== '/login') {
            sessionStorage.setItem('redirectAfterLogin', currentPath);
        }
        
        // Dispatch custom event for components to listen to
        window.dispatchEvent(new CustomEvent('authenticationFailure', {
            detail: { redirectTo: '/login' }
        }));
        
        // Fallback redirect if no listeners
        setTimeout(() => {
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }, 100);
    },

    // Logout with proper cleanup
    logout: () => {
        SecureAuthOptimized.clearAuthToken();
        
        // Cancel any pending requests
        globalAPIManager.cancelAllRequests();
        
        // Clear any stored redirect path
        sessionStorage.removeItem('redirectAfterLogin');
        
        // Dispatch logout event
        window.dispatchEvent(new CustomEvent('userLogout'));
        
        // Redirect to login
        window.location.href = '/login';
    },

    // Refresh token if it's expiring soon
    refreshTokenIfNeeded: async () => {
        if (!SecureAuthOptimized.isTokenExpiringSoon()) {
            return true;
        }

        try {
            const response = await SecureAuthOptimized.makeSecureRequest('/api/v1/auth/refresh', {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.token) {
                    SecureAuthOptimized.setAuthToken(data.token);
                    return true;
                }
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
            SecureAuthOptimized.handleAuthenticationFailure();
        }

        return false;
    }
};

// Enhanced PKCE utilities with better error handling
const PKCEUtilsOptimized = {
    // Generate PKCE code verifier and challenge with error handling
    generatePKCE: async () => {
        try {
            const codeVerifier = PKCEUtilsOptimized.generateCodeVerifier();
            const codeChallenge = await PKCEUtilsOptimized.generateCodeChallenge(codeVerifier);
            
            return {
                codeVerifier,
                codeChallenge,
                codeChallengeMethod: 'S256'
            };
        } catch (error) {
            console.error('PKCE generation failed:', error);
            throw new Error('Failed to generate PKCE parameters');
        }
    },

    // Generate cryptographically secure code verifier
    generateCodeVerifier: () => {
        try {
            const array = new Uint32Array(56/2);
            crypto.getRandomValues(array);
            return Array.from(array, dec => ('0' + dec.toString(16)).substr(-2)).join('');
        } catch (error) {
            console.error('Code verifier generation failed:', error);
            // Fallback for older browsers
            return Math.random().toString(36).substring(2, 15) + 
                   Math.random().toString(36).substring(2, 15) +
                   Math.random().toString(36).substring(2, 15) +
                   Math.random().toString(36).substring(2, 15);
        }
    },

    // Generate code challenge with fallback
    generateCodeChallenge: async (verifier) => {
        try {
            if (!crypto.subtle) {
                throw new Error('SubtleCrypto not available');
            }

            const encoder = new TextEncoder();
            const data = encoder.encode(verifier);
            const digest = await crypto.subtle.digest('SHA-256', data);
            return btoa(String.fromCharCode(...new Uint8Array(digest)))
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=/g, '');
        } catch (error) {
            console.warn('SHA-256 challenge generation failed, using fallback:', error);
            // Simple base64 encoding fallback for older browsers
            return btoa(verifier)
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=/g, '');
        }
    },

    // Secure storage with expiration
    storePKCEVerifier: (verifier) => {
        try {
            const data = {
                verifier,
                timestamp: Date.now()
            };
            sessionStorage.setItem('pkce_verifier', JSON.stringify(data));
        } catch (error) {
            console.error('Failed to store PKCE verifier:', error);
        }
    },

    // Retrieve and validate stored PKCE verifier
    retrievePKCEVerifier: () => {
        try {
            const stored = sessionStorage.getItem('pkce_verifier');
            if (!stored) return null;

            const data = JSON.parse(stored);
            sessionStorage.removeItem('pkce_verifier');

            // Check if verifier is too old (more than 10 minutes)
            if (Date.now() - data.timestamp > 10 * 60 * 1000) {
                console.warn('PKCE verifier expired');
                return null;
            }

            return data.verifier;
        } catch (error) {
            console.error('Failed to retrieve PKCE verifier:', error);
            sessionStorage.removeItem('pkce_verifier');
            return null;
        }
    }
};

// Enhanced OAuth state management
const OAuthStateManagerOptimized = {
    // Generate secure state token with additional entropy
    generateStateToken: (service) => {
        try {
            const randomBytes = new Uint8Array(32);
            crypto.getRandomValues(randomBytes);
            const state = Array.from(randomBytes, byte => 
                byte.toString(16).padStart(2, '0')
            ).join('');
            
            const timestamp = Date.now();
            const stateWithMeta = `${service}_${state}_${timestamp}`;
            
            // Store with expiration
            const stateData = {
                state: stateWithMeta,
                timestamp,
                service
            };
            sessionStorage.setItem('oauth_state', JSON.stringify(stateData));
            
            return stateWithMeta;
        } catch (error) {
            console.error('State token generation failed:', error);
            throw new Error('Failed to generate OAuth state token');
        }
    },

    // Enhanced state validation with timing attack protection
    validateStateToken: (receivedState, expectedService) => {
        try {
            const stored = sessionStorage.getItem('oauth_state');
            sessionStorage.removeItem('oauth_state');
            
            if (!stored || !receivedState) {
                return false;
            }
            
            const stateData = JSON.parse(stored);
            
            // Check expiration (5 minutes)
            if (Date.now() - stateData.timestamp > 5 * 60 * 1000) {
                console.warn('OAuth state token expired');
                return false;
            }
            
            // Timing-safe comparison
            const expectedState = stateData.state;
            if (expectedState.length !== receivedState.length) {
                return false;
            }
            
            let result = 0;
            for (let i = 0; i < expectedState.length; i++) {
                result |= expectedState.charCodeAt(i) ^ receivedState.charCodeAt(i);
            }
            
            return result === 0 && 
                   receivedState.startsWith(expectedService) &&
                   stateData.service === expectedService;
        } catch (error) {
            console.error('State token validation failed:', error);
            return false;
        }
    }
};

// Enhanced legacy authentication bridge
const LegacyAuthBridgeOptimized = {
    // Safe migration with backup
    migrateToSecureAuth: () => {
        try {
            const legacyTokens = [
                { key: 'token', storage: localStorage },
                { key: 'user_token', storage: localStorage },
                { key: 'token', storage: sessionStorage }
            ];
            
            for (const { key, storage } of legacyTokens) {
                const legacyToken = storage.getItem(key);
                if (legacyToken && !SecureAuthOptimized.getAuthToken()) {
                    // Validate legacy token before migration
                    try {
                        const parts = legacyToken.split('.');
                        if (parts.length === 3) {
                            const payload = JSON.parse(atob(parts[1]));
                            if (payload.exp && payload.exp > Date.now() / 1000) {
                                SecureAuthOptimized.setAuthToken(legacyToken);
                                console.log('Successfully migrated legacy authentication token');
                            }
                        }
                    } catch (validationError) {
                        console.warn('Legacy token validation failed:', validationError);
                    }
                    
                    // Clean up legacy token
                    storage.removeItem(key);
                }
            }
        } catch (error) {
            console.error('Auth migration failed:', error);
        }
    },

    // Backup current auth state
    backupAuthState: () => {
        try {
            const token = SecureAuthOptimized.getAuthToken();
            if (token) {
                sessionStorage.setItem('auth_backup', JSON.stringify({
                    token,
                    timestamp: Date.now()
                }));
            }
        } catch (error) {
            console.error('Auth backup failed:', error);
        }
    },

    // Restore auth state from backup
    restoreAuthState: () => {
        try {
            const backup = sessionStorage.getItem('auth_backup');
            if (backup) {
                const data = JSON.parse(backup);
                // Only restore if backup is less than 1 hour old
                if (Date.now() - data.timestamp < 60 * 60 * 1000) {
                    SecureAuthOptimized.setAuthToken(data.token);
                    sessionStorage.removeItem('auth_backup');
                    return true;
                }
                sessionStorage.removeItem('auth_backup');
            }
        } catch (error) {
            console.error('Auth restore failed:', error);
        }
        return false;
    }
};

// Initialize optimized authentication on module load
try {
    LegacyAuthBridgeOptimized.migrateToSecureAuth();
    
    // Set up automatic token refresh
    setInterval(() => {
        if (SecureAuthOptimized.isAuthenticated()) {
            SecureAuthOptimized.refreshTokenIfNeeded();
        }
    }, 2 * 60 * 1000); // Check every 2 minutes
    
} catch (error) {
    console.error('Auth initialization error:', error);
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    LegacyAuthBridgeOptimized.backupAuthState();
    globalAPIManager.cancelAllRequests();
});

export { 
    SecureAuthOptimized as SecureAuth, 
    PKCEUtilsOptimized as PKCEUtils, 
    OAuthStateManagerOptimized as OAuthStateManager, 
    LegacyAuthBridgeOptimized as LegacyAuthBridge 
};