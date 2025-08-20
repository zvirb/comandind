import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { SecureAuth } from '../utils/secureAuth';
import { 
  protectedAuthCall, 
  getAuthCircuitStatus, 
  CircuitBreakerOpen, 
  CircuitBreakerTimeout, 
  CircuitBreakerPerformancePause 
} from '../utils/authCircuitBreaker';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  // Simplified state management - reduced from 17 to 8 core variables
  const [authState, setAuthState] = useState({
    isAuthenticated: null,
    isLoading: true,
    user: null,
    error: null,
    lastCheck: null,
    sessionInfo: null,
    isDegradedMode: false,
    circuitBreakerStatus: 'closed'
  });

  // Atomic authentication operation to replace multiple async operations
  const performAtomicAuthOperation = useCallback(async (operation) => {
    console.log(`AuthContext: Starting atomic auth operation: ${operation}`);
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await protectedAuthCall(async () => {
        switch (operation) {
          case 'session_restore':
            return await restoreSessionInternal();
          case 'auth_check':
            return await checkAuthStatusInternal();
          case 'login':
            return await loginInternal(...arguments);
          default:
            throw new Error(`Unknown operation: ${operation}`);
        }
      });

      return result;

    } catch (error) {
      if (error instanceof CircuitBreakerOpen) {
        console.log('AuthContext: Circuit breaker is OPEN, auth operations blocked');
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false,
          error: 'Authentication temporarily unavailable due to system protection',
          circuitBreakerStatus: 'open'
        }));
        return false;
      } else if (error instanceof CircuitBreakerTimeout) {
        console.warn('AuthContext: Auth operation timed out');
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false,
          error: 'Authentication request timed out',
          circuitBreakerStatus: 'timeout'
        }));
        return false;
      } else if (error instanceof CircuitBreakerPerformancePause) {
        console.log('AuthContext: Auth paused for performance recovery');
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false,
          error: 'Authentication paused for performance optimization',
          circuitBreakerStatus: 'performance_pause'
        }));
        return false;
      } else {
        console.error('AuthContext: Auth operation failed:', error);
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false,
          error: error.message,
          circuitBreakerStatus: 'error'
        }));
        return false;
      }
    }
  }, []);

  // Internal session restoration (simplified)
  const restoreSessionInternal = async () => {
    console.log('AuthContext: Starting simplified session restoration');

    try {
      // Single unified session validation call
      const sessionResponse = await fetch('/api/v1/session/validate', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      });

      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        
        if (sessionData.valid) {
          console.log('AuthContext: Session restored successfully');
          
          setAuthState(prev => ({
            ...prev,
            isAuthenticated: true,
            isLoading: false,
            user: {
              id: sessionData.user_id,
              email: sessionData.email,
              role: sessionData.role,
            },
            sessionInfo: sessionData,
            error: null,
            lastCheck: Date.now(),
            isDegradedMode: false,
            circuitBreakerStatus: 'closed'
          }));

          return true;
        }
      }

      // Fallback to legacy authentication
      const legacyAuthenticated = await SecureAuth.isAuthenticated();
      
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: legacyAuthenticated,
        isLoading: false,
        user: null,
        sessionInfo: null,
        error: legacyAuthenticated ? null : 'Session expired',
        lastCheck: Date.now(),
        isDegradedMode: !legacyAuthenticated,
        circuitBreakerStatus: 'closed'
      }));

      return legacyAuthenticated;

    } catch (error) {
      console.error('Session restoration failed:', error);
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: false,
        isLoading: false,
        user: null,
        sessionInfo: null,
        error: 'Session restoration failed',
        lastCheck: Date.now(),
        isDegradedMode: true,
        circuitBreakerStatus: 'error'
      }));
      return false;
    }
  };

  // Internal auth status check (simplified)
  const checkAuthStatusInternal = async (forceRefresh = false) => {
    const now = Date.now();
    
    // Circuit breaker aware throttling - check circuit status first
    const circuitStatus = getAuthCircuitStatus();
    if (circuitStatus.state === 'open' && !forceRefresh) {
      console.log('AuthContext: Skipping auth check - circuit breaker is OPEN');
      return authState.isAuthenticated;
    }

    // Intelligent throttling based on circuit breaker health
    const throttleTime = circuitStatus.metrics.failedRequests > 5 ? 300000 : 120000; // 5 or 2 minutes
    if (!forceRefresh && authState.lastCheck && (now - authState.lastCheck) < throttleTime) {
      return authState.isAuthenticated;
    }

    try {
      // Single session validation call (no complex health checks)
      const sessionResponse = await fetch('/api/v1/session/validate', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      });

      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        
        if (sessionData.valid) {
          const user = {
            id: sessionData.user_id,
            email: sessionData.email,
            role: sessionData.role,
          };

          setAuthState(prev => ({
            ...prev,
            isAuthenticated: true,
            isLoading: false,
            user,
            error: null,
            lastCheck: now,
            circuitBreakerStatus: 'closed'
          }));

          return true;
        }
      }

      // Fallback to legacy check
      const authenticated = await SecureAuth.isAuthenticated();
      
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: authenticated,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: now,
        circuitBreakerStatus: 'closed'
      }));

      return authenticated;

    } catch (error) {
      console.error('Auth status check failed:', error);
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: error.message,
        lastCheck: now,
        circuitBreakerStatus: 'error'
      }));
      return false;
    }
  };

  // Public API methods using atomic operations
  const restoreSession = useCallback(() => {
    return performAtomicAuthOperation('session_restore');
  }, [performAtomicAuthOperation]);

  const checkAuthStatus = useCallback((forceRefresh = false) => {
    return performAtomicAuthOperation('auth_check', forceRefresh);
  }, [performAtomicAuthOperation]);

  const refreshAuth = useCallback(() => {
    return checkAuthStatus(true);
  }, [checkAuthStatus]);

  const login = async (credentials) => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const result = await protectedAuthCall(async () => {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(credentials)
        });

        if (response.ok) {
          const data = await response.json();
          // Update auth state with login response
          await checkAuthStatus(true);
          return { success: true, data };
        } else {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Login failed');
        }
      });

      return result;
    } catch (error) {
      if (error instanceof CircuitBreakerOpen) {
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false, 
          error: 'Login temporarily unavailable due to system protection',
          isAuthenticated: false,
          user: null,
          circuitBreakerStatus: 'open'
        }));
      } else {
        setAuthState(prev => ({ 
          ...prev, 
          isLoading: false, 
          error: error.message,
          isAuthenticated: false,
          user: null,
          circuitBreakerStatus: 'error'
        }));
      }
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      await SecureAuth.logout();
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: Date.now(),
        sessionInfo: null,
        isDegradedMode: false,
        circuitBreakerStatus: 'closed'
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Clear state anyway
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        lastCheck: Date.now(),
        sessionInfo: null,
        isDegradedMode: false,
        circuitBreakerStatus: 'closed'
      });
    }
  };

  // Simplified session monitoring - removed complex activity tracking
  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  // Circuit breaker aware periodic check
  useEffect(() => {
    const interval = setInterval(() => {
      if (authState.isAuthenticated && authState.user) {
        const circuitStatus = getAuthCircuitStatus();
        
        // Only do periodic checks if circuit is healthy
        if (circuitStatus.state === 'closed' && !circuitStatus.isPerformancePaused) {
          // Less frequent checks to reduce load
          const now = Date.now();
          if (now - (authState.lastCheck || 0) > 600000) { // 10 minutes
            console.log('AuthContext: Periodic auth check (circuit breaker aware)');
            checkAuthStatus();
          }
        }
      }
    }, 300000); // Check every 5 minutes

    return () => clearInterval(interval);
  }, [authState.isAuthenticated, authState.user, authState.lastCheck, checkAuthStatus]);

  // Update circuit breaker status periodically
  useEffect(() => {
    const statusInterval = setInterval(() => {
      const circuitStatus = getAuthCircuitStatus();
      setAuthState(prev => ({ ...prev, circuitBreakerStatus: circuitStatus.state }));
    }, 10000); // Update every 10 seconds

    return () => clearInterval(statusInterval);
  }, []);

  const value = {
    ...authState,
    login,
    logout,
    refreshAuth,
    checkAuthStatus,
    restoreSession,
    // Expose circuit breaker status for UI feedback
    getCircuitBreakerStatus: getAuthCircuitStatus
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;