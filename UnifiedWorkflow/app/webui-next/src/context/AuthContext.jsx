import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { SecureAuth } from '../utils/secureAuth';
import sessionErrorHandler from '../utils/sessionErrorHandler';
import { AuthStateMachine } from '../utils/authStateMachine';
import requestDebouncer, { createAntiLoopFetch } from '../utils/requestDebouncer';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState(() => {
    // Initialize with cached state if available to prevent unnecessary API calls
    const cachedAuth = sessionStorage.getItem('auth_state_cache');
    const defaultState = {
      isAuthenticated: null,
      isLoading: true,
      user: null,
      error: null,
      lastCheck: null,
      sessionWarning: null,
      sessionInfo: null,
      isRestoring: true,
      serviceHealth: {
        jwtTokenAdapter: 'unknown',
        sessionValidationNormalizer: 'unknown',
        fallbackSessionProvider: 'unknown',
        websocketAuthGateway: 'unknown',
        serviceBoundaryCoordinator: 'unknown'
      },
      isDegradedMode: false,
      backendIntegrationStatus: 'unknown'
    };
    
    if (cachedAuth) {
      try {
        const parsed = JSON.parse(cachedAuth);
        const cacheAge = Date.now() - (parsed.cacheTimestamp || 0);
        // Use cache if less than 10 minutes old
        if (cacheAge < 600000) {
          console.log('AuthContext: Using cached auth state');
          return { ...defaultState, ...parsed, isLoading: false, isRestoring: false };
        }
      } catch (error) {
        console.error('AuthContext: Failed to parse cached auth state:', error);
      }
    }
    
    return defaultState;
  });
  
  // Operation locks to prevent concurrent auth operations
  const [operationLocks, setOperationLocks] = useState({
    healthCheck: false,
    sessionRestore: false,
    authRefresh: false
  });
  
  // Enhanced request deduplication and throttling
  const requestDeduplication = useRef({
    activeRequests: new Map(),
    throttleTimestamps: {
      lastHealthCheck: 0,
      lastAuthCheck: 0,
      lastSessionRestore: 0
    },
    circuitBreaker: {
      failureCount: 0,
      isOpen: false,
      nextRetryTime: null
    }
  });
  
  // Authentication state machine
  const stateMachine = useRef(new AuthStateMachine());
  
  // Anti-loop debounced request functions
  const debouncedHealthCheck = useRef(createAntiLoopFetch('/api/v1/health/integration', {
    minimumInterval: 30000, // 30 seconds minimum between health checks
    method: 'GET'
  }));
  
  const debouncedSessionValidation = useRef(createAntiLoopFetch('/api/v1/session/validate', {
    minimumInterval: 5000, // 5 seconds minimum between session validations
    method: 'POST'
  }));
  
  // Request deduplication utility
  const makeDeduplicatedRequest = useCallback(async (requestKey, requestFn) => {
    const activeRequests = requestDeduplication.current.activeRequests;
    
    // Return existing promise if request is already active
    if (activeRequests.has(requestKey)) {
      console.log(`AuthContext: Returning existing request for ${requestKey}`);
      return activeRequests.get(requestKey);
    }
    
    // Create new request promise
    const requestPromise = (async () => {
      try {
        return await requestFn();
      } finally {
        activeRequests.delete(requestKey);
      }
    })();
    
    activeRequests.set(requestKey, requestPromise);
    return requestPromise;
  }, []);
  
  // Circuit breaker utilities
  const canMakeRequest = useCallback(() => {
    const circuitBreaker = requestDeduplication.current.circuitBreaker;
    if (circuitBreaker.isOpen && Date.now() < circuitBreaker.nextRetryTime) {
      return false;
    }
    return true;
  }, []);
  
  const recordRequestFailure = useCallback(() => {
    const circuitBreaker = requestDeduplication.current.circuitBreaker;
    circuitBreaker.failureCount += 1;
    
    if (circuitBreaker.failureCount >= 5) {
      circuitBreaker.isOpen = true;
      circuitBreaker.nextRetryTime = Date.now() + (1000 * Math.pow(2, Math.min(circuitBreaker.failureCount - 5, 6))); // Max 64s
      console.warn('AuthContext: Circuit breaker opened due to repeated failures');
    }
  }, []);
  
  const recordRequestSuccess = useCallback(() => {
    const circuitBreaker = requestDeduplication.current.circuitBreaker;
    circuitBreaker.failureCount = 0;
    circuitBreaker.isOpen = false;
    circuitBreaker.nextRetryTime = null;
  }, []);

  // Optimized health check with deduplication and circuit breaker
  const checkServiceHealth = useCallback(async () => {
    if (!canMakeRequest()) {
      console.log('AuthContext: Health check blocked by circuit breaker');
      return { serviceHealth: authState.serviceHealth, isDegradedMode: true };
    }
    
    return makeDeduplicatedRequest('health-check', async () => {
      console.log('AuthContext: Executing unique health check...');
      
      try {
        // Throttle health checks - minimum 60 seconds apart for better performance
        const now = Date.now();
        const lastCheck = requestDeduplication.current.throttleTimestamps.lastHealthCheck;
        if (now - lastCheck < 60000) {
          console.log('AuthContext: Health check throttled (60s cooldown)');
          return { serviceHealth: authState.serviceHealth, isDegradedMode: authState.isDegradedMode };
        }
        
        requestDeduplication.current.throttleTimestamps.lastHealthCheck = now;
        
        // Use debounced health check to prevent rapid requests
        console.log('AuthContext: Using debounced health check to prevent API loops');
        const healthResponse = await debouncedHealthCheck.current({
          headers: { 'Cache-Control': 'no-cache' }
        });
        
        let serviceHealth = { ...authState.serviceHealth };
        let isDegradedMode = false;
        
        if (healthResponse && typeof healthResponse === 'object') {
          const healthData = healthResponse;
          serviceHealth = {
            jwtTokenAdapter: healthData.jwt_token_adapter || 'unknown',
            sessionValidationNormalizer: healthData.session_validation_normalizer || 'unknown',
            fallbackSessionProvider: healthData.fallback_session_provider || 'unknown',
            websocketAuthGateway: healthData.websocket_auth_gateway || 'unknown',
            serviceBoundaryCoordinator: healthData.service_boundary_coordinator || 'unknown'
          };
          
          isDegradedMode = Object.values(serviceHealth).some(status => 
            status === 'degraded' || status === 'error' || status === 'circuit_open'
          );
        } else {
          isDegradedMode = true;
        }
        
        const newState = {
          ...authState,
          serviceHealth,
          isDegradedMode,
          backendIntegrationStatus: isDegradedMode ? 'degraded' : 'healthy'
        };
        
        setAuthState(prev => newState);
        
        // Cache the updated state
        sessionStorage.setItem('auth_state_cache', JSON.stringify({
          ...newState,
          cacheTimestamp: Date.now()
        }));
        
        recordRequestSuccess();
        return { serviceHealth, isDegradedMode };
        
      } catch (error) {
        console.error('AuthContext: Health check failed:', error);
        recordRequestFailure();
        
        setAuthState(prev => ({
          ...prev,
          isDegradedMode: true,
          backendIntegrationStatus: 'error'
        }));
        
        return { serviceHealth: authState.serviceHealth, isDegradedMode: true };
      }
    });
  }, [makeDeduplicatedRequest, canMakeRequest, recordRequestSuccess, recordRequestFailure]);

  // Optimized session restoration with state machine validation
  const restoreSession = useCallback(async (isInitialLoad = false) => {
    if (!canMakeRequest()) {
      console.log('AuthContext: Session restore blocked by circuit breaker');
      return false;
    }
    
    // State machine validation with initial load bypass
    const currentState = { isAuthenticated: authState.isAuthenticated, isLoading: authState.isLoading, isRestoring: authState.isRestoring, error: !!authState.error };
    const transition = stateMachine.current.getValidTransition(currentState, 'restore_session', { isInitialLoad });
    
    if (!transition.isValid) {
      console.log('AuthContext: Session restore blocked by state machine:', transition.reason);
      return authState.isAuthenticated;
    }
    
    return makeDeduplicatedRequest('session-restore', async () => {
      console.log('AuthContext: Executing unique session restoration...');
      
      try {
        setAuthState(prev => ({ ...prev, isRestoring: true, error: null }));

        // Get service health status first
        const { isDegradedMode } = await checkServiceHealth();

        // Try unified session validation with debouncing
        console.log('AuthContext: Using debounced session validation to prevent API loops');
        const sessionData = await debouncedSessionValidation.current({
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Integration-Layer': 'true'
          }
        });

        if (sessionData && typeof sessionData === 'object') {
          
          if (sessionData.valid || sessionData.authenticated) {
            console.log('AuthContext: Session restored via integration layer');
            
            const newState = {
              isAuthenticated: true,
              isLoading: false,
              isRestoring: false,
              user: {
                id: sessionData.user_id || sessionData.id,
                email: sessionData.email,
                role: sessionData.role,
                session_id: sessionData.session_id || 'unknown'
              },
              error: null,
              lastCheck: Date.now(),
              backendIntegrationStatus: isDegradedMode ? 'degraded' : 'healthy',
              serviceHealth: authState.serviceHealth,
              isDegradedMode,
              sessionWarning: null,
              sessionInfo: sessionData
            };
            
            setAuthState(prev => ({ ...prev, ...newState }));
            
            // Cache successful authentication state
            sessionStorage.setItem('auth_state_cache', JSON.stringify({
              ...newState,
              cacheTimestamp: Date.now()
            }));

            recordRequestSuccess();
            return true;
          }
        }

        // Fallback to legacy authentication check
        console.log('AuthContext: Falling back to legacy auth check');
        const legacyAuthenticated = await SecureAuth.isAuthenticated();
        
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: legacyAuthenticated,
          isLoading: false,
          isRestoring: false,
          user: null,
          sessionInfo: null,
          error: legacyAuthenticated ? null : 'Session expired',
          lastCheck: Date.now()
        }));

        if (legacyAuthenticated) {
          recordRequestSuccess();
        } else {
          recordRequestFailure();
        }
        
        return legacyAuthenticated;

      } catch (error) {
        console.error('Session restoration failed:', error);
        recordRequestFailure();
        
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: false,
          isLoading: false,
          isRestoring: false,
          user: null,
          sessionInfo: null,
          error: 'Session restoration failed',
          lastCheck: Date.now()
        }));
        
        return false;
      }
    });
  }, [makeDeduplicatedRequest, canMakeRequest, checkServiceHealth, recordRequestSuccess, recordRequestFailure]);

  // Optimized auth status check with smart throttling
  const checkAuthStatus = useCallback(async (forceRefresh = false) => {
    if (!canMakeRequest() && !forceRefresh) {
      console.log('AuthContext: Auth status check blocked by circuit breaker');
      return authState.isAuthenticated;
    }
    
    const now = Date.now();
    const lastCheck = requestDeduplication.current.throttleTimestamps.lastAuthCheck;
    
    // AGGRESSIVE throttling to prevent authentication loops
    const throttleInterval = forceRefresh ? 30000 : 1800000; // 30s for forced, 30m for regular
    if (!forceRefresh && (now - lastCheck) < throttleInterval) {
      console.log(`AuthContext: Throttling auth check - ${Math.ceil((throttleInterval - (now - lastCheck)) / 1000)}s remaining`);
      return authState.isAuthenticated;
    }
    
    return makeDeduplicatedRequest(`auth-status-${forceRefresh}`, async () => {
      console.log('AuthContext: Executing auth status check, forced:', forceRefresh);
      
      try {
        requestDeduplication.current.throttleTimestamps.lastAuthCheck = now;
        setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

        // Try unified session validation first with debouncing
        console.log('AuthContext: Using debounced session validation in checkAuthStatus to prevent API loops');
        const sessionData = await debouncedSessionValidation.current({
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Integration-Layer': 'true'
          }
        });

        if (sessionData && typeof sessionData === 'object') {
          
          if (sessionData.valid) {
            const user = {
              id: sessionData.user_id,
              email: sessionData.email,
              role: sessionData.role,
              exp: Math.floor(Date.now() / 1000) + (sessionData.expires_in_minutes * 60)
            };

            setAuthState(prev => ({
              ...prev,
              isAuthenticated: true,
              isLoading: false,
              user,
              error: null,
              lastCheck: now
            }));

            recordRequestSuccess();
            return true;
          }
        }

        // Fallback to legacy authentication
        const authenticated = await SecureAuth.isAuthenticated();
        
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: authenticated,
          isLoading: false,
          user: authenticated ? prev.user : null,
          error: null,
          lastCheck: now
        }));

        if (authenticated) {
          recordRequestSuccess();
        } else {
          recordRequestFailure();
        }
        
        return authenticated;
        
      } catch (error) {
        console.error('Auth status check failed:', error);
        recordRequestFailure();
        
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: false,
          isLoading: false,
          user: null,
          error: error.message,
          lastCheck: now
        }));
        
        return false;
      }
    });
  }, [makeDeduplicatedRequest, canMakeRequest, recordRequestSuccess, recordRequestFailure]);

  const login = useCallback(async (credentials) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Check service health before login attempt
      await checkServiceHealth();
      
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Integration-Layer': 'true' // Use backend integration layer
        },
        credentials: 'include',
        body: JSON.stringify(credentials)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Update auth state with normalized JWT token handling
        await checkAuthStatus(true);
        
        return { success: true, data };
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
    } catch (error) {
      setAuthState(prev => ({ 
        ...prev, 
        isLoading: false, 
        error: error.message,
        isAuthenticated: false,
        user: null,
        isDegradedMode: true
      }));
      return { success: false, error: error.message };
    }
  }, [checkServiceHealth, checkAuthStatus]); // Depends on memoized functions

  const logout = useCallback(async () => {
    try {
      await SecureAuth.logout();
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: Date.now()
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Clear state anyway
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: Date.now()
      });
    }
  }, []); // No dependencies

  const refreshAuth = useCallback(() => {
    return checkAuthStatus(true);
  }, [checkAuthStatus]); // Only depends on memoized checkAuthStatus

  const extendSession = useCallback(async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, sessionWarning: null }));
      
      const refreshed = await SecureAuth.refreshToken();
      if (refreshed) {
        // Refresh auth state to get new token expiration
        await checkAuthStatus(true);
        return { success: true };
      } else {
        return { success: false, error: 'Failed to extend session' };
      }
    } catch (error) {
      console.error('Session extension failed:', error);
      return { success: false, error: error.message };
    }
  }, [checkAuthStatus]); // Only depends on memoized checkAuthStatus

  // Restore session on mount - single execution with initial load flag
  useEffect(() => {
    const initializeAuth = async () => {
      console.log('AuthContext: Initializing authentication on mount with initial load flag');
      
      // Reset state machine for new session to prevent contamination from previous sessions
      stateMachine.current.resetForNewSession();
      
      try {
        await restoreSession(true); // Pass isInitialLoad=true for initial session restoration
      } catch (error) {
        console.error('AuthContext: Initial auth restoration failed:', error);
      }
    };
    
    initializeAuth();
  }, []); // No dependencies - single execution on mount

  // DISABLED periodic auth checks to prevent loops - rely on user-initiated checks only
  useEffect(() => {
    console.log('AuthContext: Periodic auth checks DISABLED to prevent refresh loops');
    // Periodic checks are disabled to prevent authentication refresh loops
    // Authentication will be checked only on:
    // 1. Initial page load (restoreSession)
    // 2. User-initiated actions (login, refresh button)
    // 3. Navigation protection (PrivateRoute when needed)
    
    // Previous implementation caused rapid API calls leading to visual cycling
    return () => {}; // No cleanup needed
  }, []); // No dependencies - single execution

  const value = {
    ...authState,
    login,
    logout,
    refreshAuth,
    checkAuthStatus,
    extendSession,
    restoreSession,
    checkServiceHealth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};