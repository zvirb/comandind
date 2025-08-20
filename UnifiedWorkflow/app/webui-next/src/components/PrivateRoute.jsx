import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthStateMachine } from '../utils/authStateMachine';

const PrivateRoute = ({ children }) => {
  const { 
    isAuthenticated, 
    isLoading, 
    isRestoring, 
    refreshAuth, 
    restoreSession, 
    error,
    isDegradedMode,
    backendIntegrationStatus,
    checkServiceHealth,
    checkAuthStatus,
    lastCheck
  } = useAuth();
  const location = useLocation();
  
  // Circuit breaker state for authentication failures
  const [circuitBreaker, setCircuitBreaker] = useState({
    failureCount: 0,
    lastFailure: null,
    isOpen: false,
    nextRetryTime: null
  });
  
  // Request deduplication state
  const activeRequests = useRef(new Set());
  
  // Enhanced throttling with exponential backoff
  const throttleRef = useRef({
    lastNavigationCheck: 0,
    currentPathname: '',
    isProcessing: false,
    exponentialBackoffMs: 1000 // Start with 1 second
  });
  
  // Authentication state machine for preventing invalid transitions
  const stateMachine = useRef(new AuthStateMachine());
  
  // Circuit breaker utilities
  const canMakeAuthRequest = useCallback(() => {
    const now = Date.now();
    
    // Check if circuit breaker is open
    if (circuitBreaker.isOpen) {
      if (now < circuitBreaker.nextRetryTime) {
        return false; // Circuit breaker still open
      }
      // Reset circuit breaker after timeout
      setCircuitBreaker(prev => ({ ...prev, isOpen: false, failureCount: 0 }));
    }
    
    return true;
  }, [circuitBreaker]);
  
  const recordAuthFailure = useCallback(() => {
    const now = Date.now();
    setCircuitBreaker(prev => {
      const newFailureCount = prev.failureCount + 1;
      const shouldOpen = newFailureCount >= 3; // Open circuit after 3 failures
      const backoffMs = Math.min(1000 * Math.pow(2, newFailureCount), 30000); // Max 30s
      
      return {
        failureCount: newFailureCount,
        lastFailure: now,
        isOpen: shouldOpen,
        nextRetryTime: shouldOpen ? now + backoffMs : null
      };
    });
    
    // Update exponential backoff
    throttleRef.current.exponentialBackoffMs = Math.min(
      throttleRef.current.exponentialBackoffMs * 2, 
      30000 // Max 30 seconds
    );
  }, []);
  
  const recordAuthSuccess = useCallback(() => {
    setCircuitBreaker({ failureCount: 0, lastFailure: null, isOpen: false, nextRetryTime: null });
    throttleRef.current.exponentialBackoffMs = 1000; // Reset backoff
  }, []);
  
  // Request deduplication utility
  const makeDeduplicatedRequest = useCallback(async (requestKey, requestFn) => {
    if (activeRequests.current.has(requestKey)) {
      console.log('PrivateRoute: Skipping duplicate request:', requestKey);
      return null;
    }
    
    activeRequests.current.add(requestKey);
    try {
      const result = await requestFn();
      return result;
    } finally {
      activeRequests.current.delete(requestKey);
    }
  }, []);
  
  // SIMPLIFIED navigation protection with aggressive throttling to prevent loops
  useEffect(() => {
    const pathname = location.pathname;
    
    // AGGRESSIVE throttling - only check auth if absolutely necessary
    if (throttleRef.current.isProcessing || 
        throttleRef.current.currentPathname === pathname ||
        !canMakeAuthRequest()) {
      return;
    }
    
    const now = Date.now();
    const minInterval = Math.max(throttleRef.current.exponentialBackoffMs, 60000); // MINIMUM 60 seconds
    
    // Prevent rapid navigation checks that cause auth loops
    if (now - throttleRef.current.lastNavigationCheck < minInterval) {
      console.log(`PrivateRoute: Navigation throttled - ${Math.ceil((minInterval - (now - throttleRef.current.lastNavigationCheck)) / 1000)}s remaining`);
      return;
    }
    
    throttleRef.current.isProcessing = true;
    throttleRef.current.currentPathname = pathname;
    throttleRef.current.lastNavigationCheck = now;
    
    const handleNavigationProtection = async () => {
      try {
        // Only perform auth checks for unauthenticated users or critical failures
        if (!isLoading && !isRestoring && !isAuthenticated && !error) {
          await makeDeduplicatedRequest('session-restore', async () => {
            console.log('PrivateRoute: Attempting session restoration for:', pathname);
            try {
              const restored = await restoreSession();
              if (restored) {
                recordAuthSuccess();
                return true;
              } else {
                recordAuthFailure();
                return false;
              }
            } catch (restoreError) {
              console.error('PrivateRoute: Session restoration failed:', restoreError);
              recordAuthFailure();
              throw restoreError;
            }
          });
        }
        // IMPORTANT: Remove continuous auth checks for authenticated users to prevent loops
        
      } catch (error) {
        console.error('PrivateRoute: Navigation protection error:', error);
        recordAuthFailure();
      } finally {
        // Reset processing flag with MUCH longer delay to prevent loops
        setTimeout(() => {
          throttleRef.current.isProcessing = false;
        }, 60000); // 60 second cooldown to prevent rapid auth calls
      }
    };

    // ONLY trigger for clearly unauthenticated users to prevent auth loops
    if (isAuthenticated === false && !error) {
      const timeoutId = setTimeout(handleNavigationProtection, 2000); // Longer delay
      return () => clearTimeout(timeoutId);
    } else {
      // For authenticated users or loading states, do nothing to prevent loops
      throttleRef.current.isProcessing = false;
    }
    
  }, [location.pathname]); // Remove isAuthenticated dependency to prevent loops

  console.log('PrivateRoute: Current authentication state:', { 
    isAuthenticated, 
    isLoading, 
    isRestoring, 
    error,
    pathname: location.pathname,
    circuitBreakerOpen: circuitBreaker.isOpen,
    failureCount: circuitBreaker.failureCount
  });

  // Loading state while checking authentication or restoring session
  if (isLoading || isRestoring || isAuthenticated === null) {
    const loadingMessage = isRestoring ? 'Restoring session...' : 
                          circuitBreaker.isOpen ? 'Waiting to retry authentication...' :
                          'Verifying session...';
    
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-purple-400 animate-pulse">{loadingMessage}</div>
          {location.pathname !== '/chat' && (
            <div className="text-gray-500 text-sm">
              Ensuring session continuity for {location.pathname}
            </div>
          )}
          {isDegradedMode && (
            <div className="text-orange-400 text-xs">
              Service in degraded mode - Enhanced session validation
            </div>
          )}
          {circuitBreaker.isOpen && (
            <div className="text-red-400 text-xs">
              Authentication rate limited - Retrying in {Math.ceil((circuitBreaker.nextRetryTime - Date.now()) / 1000)}s
            </div>
          )}
          {backendIntegrationStatus && backendIntegrationStatus !== 'unknown' && (
            <div className="text-gray-600 text-xs">
              Integration: {backendIntegrationStatus}
            </div>
          )}
        </div>
      </div>
    );
  }

  // If not authenticated after restoration attempts, redirect to login page
  if (!isAuthenticated) {
    console.log('PrivateRoute: Redirecting to login - authentication failed after restoration attempts');
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // If authenticated, render the protected component
  console.log('PrivateRoute: Authentication successful, rendering protected component for:', location.pathname);
  return children;
};

// Memoize PrivateRoute to prevent unnecessary re-renders that trigger auth loops
export default memo(PrivateRoute, (prevProps, nextProps) => {
  // Only re-render if children actually change
  return prevProps.children === nextProps.children;
});