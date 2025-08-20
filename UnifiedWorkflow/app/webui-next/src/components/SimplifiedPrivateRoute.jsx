import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/SimplifiedAuthContext';

const SimplifiedPrivateRoute = ({ children }) => {
  const { 
    isAuthenticated, 
    isLoading, 
    error,
    restoreSession,
    circuitBreakerStatus,
    getCircuitBreakerStatus
  } = useAuth();
  const location = useLocation();
  const [navigationAttempted, setNavigationAttempted] = useState(false);

  // Simplified navigation protection - single atomic operation
  useEffect(() => {
    let mounted = true;
    
    const handleNavigationProtection = async () => {
      if (!mounted || navigationAttempted) return;
      
      // If we appear to be losing authentication state during navigation,
      // attempt session restoration once
      if (!isLoading && !isAuthenticated && !error) {
        console.log('PrivateRoute: Potential session loss detected, attempting restoration for route:', location.pathname);
        setNavigationAttempted(true);
        
        try {
          const restored = await restoreSession();
          if (!restored) {
            console.log('PrivateRoute: Session restoration failed for route:', location.pathname);
          }
        } catch (restoreError) {
          console.error('PrivateRoute: Session restoration error:', restoreError);
        }
      }
    };

    // Simple debounced protection
    const timeoutId = setTimeout(() => {
      if (mounted) {
        handleNavigationProtection();
      }
    }, 100);
    
    return () => {
      mounted = false;
      clearTimeout(timeoutId);
    };
  }, [location.pathname, isAuthenticated, isLoading, error, restoreSession, navigationAttempted]);

  // Reset navigation attempt on route change
  useEffect(() => {
    setNavigationAttempted(false);
  }, [location.pathname]);

  console.log('PrivateRoute: Current authentication state:', { 
    isAuthenticated, 
    isLoading, 
    error,
    pathname: location.pathname,
    circuitBreakerStatus
  });

  // Enhanced loading state with circuit breaker awareness
  if (isLoading || isAuthenticated === null) {
    const circuitStatus = getCircuitBreakerStatus();
    
    let loadingMessage = 'Verifying session...';
    let statusColor = 'text-purple-400';
    let statusInfo = null;
    
    if (circuitBreakerStatus === 'open') {
      loadingMessage = 'Authentication temporarily paused...';
      statusColor = 'text-orange-400';
      statusInfo = 'System protection active - retrying shortly';
    } else if (circuitBreakerStatus === 'performance_pause') {
      loadingMessage = 'Optimizing performance...';
      statusColor = 'text-blue-400';
      statusInfo = 'Authentication paused for better performance';
    } else if (circuitBreakerStatus === 'timeout') {
      loadingMessage = 'Connection taking longer than usual...';
      statusColor = 'text-yellow-400';
      statusInfo = 'Please wait while we establish connection';
    }
    
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="flex flex-col items-center space-y-4 max-w-md text-center">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          <div className={`${statusColor} animate-pulse font-medium`}>{loadingMessage}</div>
          
          {statusInfo && (
            <div className="text-gray-400 text-sm">
              {statusInfo}
            </div>
          )}
          
          <div className="text-gray-500 text-sm">
            Accessing {location.pathname}
          </div>
          
          {/* Circuit breaker status indicator */}
          {circuitBreakerStatus !== 'closed' && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 mt-4">
              <div className="text-xs text-gray-400 mb-1">System Status</div>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  circuitBreakerStatus === 'open' ? 'bg-orange-500' :
                  circuitBreakerStatus === 'performance_pause' ? 'bg-blue-500' :
                  circuitBreakerStatus === 'timeout' ? 'bg-yellow-500' :
                  'bg-gray-500'
                }`}></div>
                <span className="text-xs text-gray-300 capitalize">
                  {circuitBreakerStatus.replace('_', ' ')}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Enhanced error state with circuit breaker information
  if (error && circuitBreakerStatus === 'error') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="flex flex-col items-center space-y-4 max-w-md text-center">
          <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 19.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div className="text-red-400 font-medium">Authentication Error</div>
          <div className="text-gray-400 text-sm">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
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

export default SimplifiedPrivateRoute;