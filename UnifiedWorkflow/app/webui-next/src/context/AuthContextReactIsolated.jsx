import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { SecureAuth } from '../utils/secureAuth';
import sessionErrorHandler from '../utils/sessionErrorHandler';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState({
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
  });
  
  // Operation locks to prevent concurrent auth operations and WebGL interference
  const operationLocksRef = useRef({
    healthCheck: false,
    sessionRestore: false,
    authRefresh: false,
    webglIsolation: true // Flag to isolate from WebGL operations
  });
  
  // Enhanced throttling to prevent WebGL performance monitoring interference
  const throttleRefs = useRef({
    lastHealthCheck: 0,
    lastAuthCheck: 0,
    lastSessionRestore: 0,
    webglInterferenceCount: 0,
    lastWebglInterference: 0
  });

  // WebGL interference detection and mitigation
  const detectWebGLInterference = useCallback(() => {
    const now = Date.now();
    const timeSinceLastInterference = now - throttleRefs.current.lastWebglInterference;
    
    // If we detect frequent auth operations (potential WebGL interference)
    if (timeSinceLastInterference < 5000) { // Less than 5 seconds
      throttleRefs.current.webglInterferenceCount++;
      if (throttleRefs.current.webglInterferenceCount > 3) {
        console.warn('AuthContext: Detected potential WebGL interference, enabling enhanced isolation');
        operationLocksRef.current.webglIsolation = true;
        return true;
      }
    } else {
      // Reset counter if interference stops
      throttleRefs.current.webglInterferenceCount = 0;
    }
    
    throttleRefs.current.lastWebglInterference = now;
    return false;
  }, []);

  // Check service health with WebGL isolation
  const checkServiceHealth = useCallback(async () => {
    // Enhanced interference detection
    if (detectWebGLInterference()) {
      return { serviceHealth: authState.serviceHealth, isDegradedMode: authState.isDegradedMode };
    }

    if (operationLocksRef.current.healthCheck) {
      console.log('AuthContext: Health check already in progress, skipping... (WebGL-isolated)');
      return { serviceHealth: authState.serviceHealth, isDegradedMode: authState.isDegradedMode };
    }
    
    operationLocksRef.current.healthCheck = true;
    
    try {
      console.log('AuthContext: Checking backend integration service health... (WebGL-isolated)');
      
      let serviceHealth = { ...authState.serviceHealth };
      let isDegradedMode = false;
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // Increased timeout for stability
        
        const healthResponse = await fetch('/api/v1/health/integration', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Cache-Control': 'no-cache' },
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (healthResponse.ok) {
          const healthData = await healthResponse.json();
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
      } catch (healthError) {
        console.warn('AuthContext: Service health check failed, assuming degraded mode (WebGL-isolated):', healthError);
        isDegradedMode = true;
      }
      
      // Batch state update to prevent WebGL interference
      requestAnimationFrame(() => {
        setAuthState(prev => ({
          ...prev,
          serviceHealth,
          isDegradedMode,
          backendIntegrationStatus: isDegradedMode ? 'degraded' : 'healthy'
        }));
      });
      
      return { serviceHealth, isDegradedMode };
      
    } catch (error) {
      console.error('AuthContext: Service health check error (WebGL-isolated):', error);
      requestAnimationFrame(() => {
        setAuthState(prev => ({
          ...prev,
          isDegradedMode: true,
          backendIntegrationStatus: 'error'
        }));
      });
      return { serviceHealth: authState.serviceHealth, isDegradedMode: true };
    } finally {
      operationLocksRef.current.healthCheck = false;
    }
  }, []); // No dependencies to prevent WebGL cascade

  // Session restoration with WebGL isolation
  const restoreSession = useCallback(async () => {
    if (operationLocksRef.current.sessionRestore) {
      console.log('AuthContext: Session restoration already in progress, skipping... (WebGL-isolated)');
      return authState.isAuthenticated;
    }
    
    operationLocksRef.current.sessionRestore = true;
    
    try {
      console.log('AuthContext: Starting session restoration... (WebGL-isolated)');
      
      // Batch initial state update
      requestAnimationFrame(() => {
        setAuthState(prev => ({ ...prev, isRestoring: true, error: null }));
      });

      const { isDegradedMode } = await checkServiceHealth();

      let sessionValidationResponse;
      try {
        sessionValidationResponse = await fetch('/api/v1/session/validate', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Integration-Layer': 'true',
            'X-WebGL-Isolated': 'true' // Signal WebGL isolation
          }
        });
      } catch (fetchError) {
        console.warn('AuthContext: Session validation service unavailable, using fallback (WebGL-isolated)');
        const fallbackAuth = await sessionErrorHandler.handleSessionServiceError(
          'sessionValidation',
          fetchError,
          () => sessionErrorHandler.getFallbackAuthentication()
        );
        
        if (fallbackAuth.valid) {
          requestAnimationFrame(() => {
            setAuthState(prev => ({
              ...prev,
              isAuthenticated: true,
              isLoading: false,
              isRestoring: false,
              user: {
                id: fallbackAuth.user_id,
                email: fallbackAuth.email,
                role: fallbackAuth.role
              },
              error: null,
              lastCheck: Date.now(),
              isDegradedMode: true,
              backendIntegrationStatus: 'fallback'
            }));
          });
          return true;
        } else {
          requestAnimationFrame(() => {
            setAuthState(prev => ({
              ...prev,
              isAuthenticated: false,
              isLoading: false,
              isRestoring: false,
              user: null,
              sessionInfo: null,
              error: isDegradedMode ? 'Session service degraded' : 'Session service unavailable',
              lastCheck: Date.now(),
              isDegradedMode: true
            }));
          });
          return false;
        }
      }

      if (sessionValidationResponse.ok) {
        const sessionData = await sessionValidationResponse.json();
        
        if (sessionData.valid || sessionData.authenticated) {
          console.log('AuthContext: Session restored successfully via integration layer (WebGL-isolated)');
          
          try {
            const sessionInfoResponse = await fetch('/api/v1/session/info', {
              credentials: 'include',
              headers: { 
                'Cache-Control': 'no-cache',
                'X-Integration-Layer': 'true',
                'X-WebGL-Isolated': 'true'
              }
            });
            
            let sessionInfo = null;
            if (sessionInfoResponse.ok) {
              sessionInfo = await sessionInfoResponse.json();
            }

            requestAnimationFrame(() => {
              setAuthState(prev => ({
                ...prev,
                isAuthenticated: true,
                isLoading: false,
                isRestoring: false,
                user: {
                  id: sessionData.user_id || sessionData.id,
                  email: sessionData.email,
                  role: sessionData.role,
                  session_id: sessionInfo?.session_id || sessionData.session_id || 'unknown'
                },
                sessionInfo,
                error: null,
                lastCheck: Date.now(),
                backendIntegrationStatus: isDegradedMode ? 'degraded' : 'healthy'
              }));
            });

            return true;
          } catch (infoError) {
            console.warn('Could not fetch session info (WebGL-isolated):', infoError);
            requestAnimationFrame(() => {
              setAuthState(prev => ({
                ...prev,
                isAuthenticated: true,
                isLoading: false,
                isRestoring: false,
                user: {
                  id: sessionData.user_id || sessionData.id,
                  email: sessionData.email,
                  role: sessionData.role
                },
                error: null,
                lastCheck: Date.now(),
                backendIntegrationStatus: isDegradedMode ? 'degraded' : 'healthy'
              }));
            });
            return true;
          }
        }
      }

      console.log('AuthContext: No valid session, falling back to legacy auth check (WebGL-isolated)');
      const legacyAuthenticated = await SecureAuth.isAuthenticated();
      
      requestAnimationFrame(() => {
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
      });

      return legacyAuthenticated;

    } catch (error) {
      console.error('Session restoration failed (WebGL-isolated):', error);
      requestAnimationFrame(() => {
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
      });
      return false;
    } finally {
      operationLocksRef.current.sessionRestore = false;
    }
  }, [checkServiceHealth]);

  // Enhanced auth status check with WebGL isolation
  const checkAuthStatus = useCallback(async (forceRefresh = false) => {
    const now = Date.now();
    
    // Enhanced throttling to prevent WebGL interference - increased to 3 minutes
    if (!forceRefresh && authState.lastCheck && (now - authState.lastCheck) < 180000) {
      return authState.isAuthenticated;
    }

    // Detect and prevent WebGL interference
    if (detectWebGLInterference() && !forceRefresh) {
      console.log('AuthContext: WebGL interference detected, throttling auth check');
      return authState.isAuthenticated;
    }

    if (operationLocksRef.current.authRefresh) {
      console.log('AuthContext: Auth refresh already in progress, skipping... (WebGL-isolated)');
      return authState.isAuthenticated;
    }

    operationLocksRef.current.authRefresh = true;

    try {
      requestAnimationFrame(() => {
        setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      });

      const token = SecureAuth.getAuthToken();
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          const currentTime = Date.now() / 1000;
          const timeUntilExpiry = payload.exp - currentTime;
          
          if (timeUntilExpiry > 0 && timeUntilExpiry < 300) {
            console.log('AuthContext: Proactively refreshing token (WebGL-isolated)', Math.round(timeUntilExpiry), 'seconds)');
            const refreshed = await SecureAuth.refreshToken();
            if (!refreshed) {
              console.log('AuthContext: Token refresh failed, will validate current token (WebGL-isolated)');
            }
          }
        } catch (error) {
          console.debug('Could not parse token for refresh check (WebGL-isolated):', error);
        }
      }

      try {
        const sessionValidationResponse = await fetch('/api/v1/session/validate', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Integration-Layer': 'true',
            'X-WebGL-Isolated': 'true'
          }
        });

        if (sessionValidationResponse.ok) {
          const sessionData = await sessionValidationResponse.json();
          
          if (sessionData.valid) {
            const user = {
              id: sessionData.user_id,
              email: sessionData.email,
              role: sessionData.role,
              exp: Math.floor(Date.now() / 1000) + (sessionData.expires_in_minutes * 60)
            };

            let sessionWarning = null;
            if (sessionData.expires_in_minutes && sessionData.expires_in_minutes < 5) {
              sessionWarning = {
                timeLeft: Math.max(0, sessionData.expires_in_minutes),
                type: 'expiring'
              };
            }

            requestAnimationFrame(() => {
              setAuthState(prev => ({
                ...prev,
                isAuthenticated: true,
                isLoading: false,
                user,
                error: null,
                lastCheck: now,
                sessionWarning
              }));
            });

            return true;
          }
        }
      } catch (sessionError) {
        console.debug('Session validation failed, falling back to legacy auth (WebGL-isolated):', sessionError);
      }

      const authenticated = await SecureAuth.isAuthenticated();
      
      let user = null;
      if (authenticated) {
        const currentToken = SecureAuth.getAuthToken();
        if (currentToken) {
          try {
            const payload = JSON.parse(atob(currentToken.split('.')[1]));
            user = {
              id: payload.id,
              email: payload.email,
              role: payload.role,
              session_id: payload.session_id,
              exp: payload.exp
            };
          } catch (error) {
            console.debug('Could not parse user from token (WebGL-isolated):', error);
          }
        }
      }

      let sessionWarning = null;
      if (authenticated && user && user.exp) {
        const timeUntilExpiry = user.exp - (Date.now() / 1000);
        if (timeUntilExpiry < 300) {
          sessionWarning = {
            timeLeft: Math.max(0, Math.round(timeUntilExpiry / 60)),
            type: 'expiring'
          };
        }
      }

      requestAnimationFrame(() => {
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: authenticated,
          isLoading: false,
          user,
          error: null,
          lastCheck: now,
          sessionWarning
        }));
      });

      return authenticated;
    } catch (error) {
      console.error('Auth status check failed (WebGL-isolated):', error);
      requestAnimationFrame(() => {
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: false,
          isLoading: false,
          user: null,
          error: error.message,
          lastCheck: now,
          sessionWarning: null
        }));
      });
      return false;
    } finally {
      operationLocksRef.current.authRefresh = false;
    }
  }, []); // No dependencies to prevent cascade

  const login = useCallback(async (credentials) => {
    try {
      requestAnimationFrame(() => {
        setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      });
      
      await checkServiceHealth();
      
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Integration-Layer': 'true',
          'X-WebGL-Isolated': 'true'
        },
        credentials: 'include',
        body: JSON.stringify(credentials)
      });

      if (response.ok) {
        const data = await response.json();
        await checkAuthStatus(true);
        return { success: true, data };
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
    } catch (error) {
      requestAnimationFrame(() => {
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false, 
          error: error.message,
          isAuthenticated: false,
          user: null,
          isDegradedMode: true
        }));
      });
      return { success: false, error: error.message };
    }
  }, [checkServiceHealth, checkAuthStatus]);

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
      console.error('Logout error (WebGL-isolated):', error);
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: Date.now()
      });
    }
  }, []);

  const refreshAuth = useCallback(() => {
    return checkAuthStatus(true);
  }, [checkAuthStatus]);

  const extendSession = useCallback(async () => {
    try {
      requestAnimationFrame(() => {
        setAuthState(prev => ({ ...prev, isLoading: true, sessionWarning: null }));
      });
      
      const refreshed = await SecureAuth.refreshToken();
      if (refreshed) {
        await checkAuthStatus(true);
        return { success: true };
      } else {
        return { success: false, error: 'Failed to extend session' };
      }
    } catch (error) {
      console.error('Session extension failed (WebGL-isolated):', error);
      return { success: false, error: error.message };
    }
  }, [checkAuthStatus]);

  // Restore session on mount with WebGL isolation
  useEffect(() => {
    // Delay initial session restoration to prevent WebGL interference
    const timeoutId = setTimeout(() => {
      restoreSession();
    }, 100);
    
    return () => clearTimeout(timeoutId);
  }, []);

  // Enhanced periodic auth status check with WebGL isolation
  useEffect(() => {
    const interval = setInterval(() => {
      // Skip if WebGL interference detected
      if (operationLocksRef.current.webglIsolation && throttleRefs.current.webglInterferenceCount > 2) {
        console.log('AuthContext: Skipping periodic check due to WebGL interference');
        return;
      }

      if (authState.isAuthenticated && authState.user) {
        const now = Date.now() / 1000;
        const timeUntilExpiry = authState.user.exp - now;
        
        if (timeUntilExpiry < 600) {
          console.log('AuthContext: Session expires soon, triggering refresh check (WebGL-isolated)');
          checkAuthStatus(true);
        } else if (timeUntilExpiry < 1800) {
          checkAuthStatus();
        }
      }
    }, 600000); // Increased to 10 minutes for WebGL isolation

    return () => clearInterval(interval);
  }, [authState.isAuthenticated, authState.user]);

  // Enhanced session activity tracking with WebGL isolation
  useEffect(() => {
    const trackActivity = () => {
      // Skip activity tracking if WebGL interference detected
      if (operationLocksRef.current.webglIsolation && throttleRefs.current.webglInterferenceCount > 2) {
        return;
      }

      if (authState.isAuthenticated && authState.user) {
        const now = Date.now() / 1000;
        const timeUntilExpiry = authState.user.exp - now;
        
        if (timeUntilExpiry < 1800) {
          console.log('AuthContext: User activity detected, refreshing session (WebGL-isolated)');
          checkAuthStatus(true);
        }
      }
    };

    const events = ['click', 'keypress', 'scroll', 'mousemove'];
    let activityTimeout;

    const debouncedTrackActivity = () => {
      clearTimeout(activityTimeout);
      activityTimeout = setTimeout(trackActivity, 60000); // Increased debounce for WebGL isolation
    };

    events.forEach(event => {
      document.addEventListener(event, debouncedTrackActivity, { passive: true });
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, debouncedTrackActivity);
      });
      clearTimeout(activityTimeout);
    };
  }, [authState.isAuthenticated, authState.user]);

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