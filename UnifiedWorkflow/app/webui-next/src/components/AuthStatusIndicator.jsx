import React, { useState } from 'react';
import { Shield, ShieldAlert, ShieldCheck, Loader, Wifi, WifiOff, Clock, RefreshCw, AlertTriangle, Settings } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const AuthStatusIndicator = ({ showDetails = false }) => {
  const { 
    isAuthenticated, 
    isLoading, 
    isRestoring, 
    user, 
    error, 
    lastCheck, 
    sessionWarning, 
    sessionInfo, 
    extendSession,
    serviceHealth,
    isDegradedMode,
    backendIntegrationStatus
  } = useAuth();
  const [isExtending, setIsExtending] = useState(false);

  const getStatusIcon = () => {
    if (isLoading || isRestoring) {
      return <Loader className="w-4 h-4 animate-spin text-yellow-400" />;
    }
    
    if (error) {
      return <ShieldAlert className="w-4 h-4 text-red-400" />;
    }
    
    if (isDegradedMode && isAuthenticated) {
      return <AlertTriangle className="w-4 h-4 text-orange-400 animate-pulse" />;
    }
    
    if (sessionWarning) {
      return <Clock className="w-4 h-4 text-orange-400 animate-pulse" />;
    }
    
    if (isAuthenticated) {
      return <ShieldCheck className="w-4 h-4 text-green-400" />;
    }
    
    return <Shield className="w-4 h-4 text-gray-400" />;
  };

  const getStatusText = () => {
    if (isLoading) return 'Checking...';
    if (isRestoring) return 'Restoring Session...';
    if (error) return 'Auth Error';
    if (sessionWarning) return `Session expires in ${sessionWarning.timeLeft}m`;
    if (isAuthenticated) {
      if (isDegradedMode) {
        return backendIntegrationStatus === 'fallback' ? 'Fallback Mode' : 'Degraded Service';
      }
      return sessionInfo ? 'Session Active' : 'Authenticated';
    }
    return 'Not Authenticated';
  };

  const handleExtendSession = async () => {
    setIsExtending(true);
    try {
      const result = await extendSession();
      if (!result.success) {
        console.error('Failed to extend session:', result.error);
      }
    } catch (error) {
      console.error('Session extension error:', error);
    } finally {
      setIsExtending(false);
    }
  };

  const getStatusColor = () => {
    if (isLoading || isRestoring) return 'text-yellow-400';
    if (error) return 'text-red-400';
    if (sessionWarning) return 'text-orange-400';
    if (isAuthenticated) return 'text-green-400';
    return 'text-gray-400';
  };

  const getConnectionIcon = () => {
    if (isAuthenticated && !error) {
      return <Wifi className="w-3 h-3 text-green-400" />;
    }
    return <WifiOff className="w-3 h-3 text-red-400" />;
  };

  if (!showDetails) {
    return (
      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        {getConnectionIcon()}
        {sessionWarning && (
          <span className="text-xs text-orange-400 font-medium">
            {sessionWarning.timeLeft}m
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 backdrop-blur-lg rounded-lg border border-gray-800 p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-400">Authentication Status</h4>
        {getConnectionIcon()}
      </div>
      
      <div className="flex items-center space-x-2 mb-2">
        {getStatusIcon()}
        <span className={`text-sm font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>
      
      {user && (
        <div className="text-xs text-gray-500 space-y-1">
          <div>User: {user.email}</div>
          <div>Role: {user.role}</div>
          <div>Session: {user.session_id?.substring(0, 8)}...</div>
          {sessionInfo && (
            <>
              <div>Status: Session managed</div>
              <div>Created: {new Date(sessionInfo.session_created).toLocaleTimeString()}</div>
              <div>Expires: {new Date(sessionInfo.expires_at).toLocaleTimeString()}</div>
            </>
          )}
          <div className="flex items-center space-x-1">
            <span>Integration:</span>
            <span className={`font-medium ${
              backendIntegrationStatus === 'healthy' ? 'text-green-400' :
              backendIntegrationStatus === 'degraded' ? 'text-orange-400' :
              backendIntegrationStatus === 'fallback' ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {backendIntegrationStatus || 'unknown'}
            </span>
          </div>
        </div>
      )}
      
      {/* Service Health Details */}
      {isDegradedMode && showDetails && (
        <div className="mt-3 p-2 bg-orange-900/20 border border-orange-500/30 rounded">
          <div className="flex items-center space-x-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-orange-400" />
            <span className="text-xs font-medium text-orange-400">Service Health Status</span>
          </div>
          <div className="text-xs text-gray-400 space-y-1">
            {serviceHealth && Object.entries(serviceHealth).map(([service, status]) => (
              <div key={service} className="flex justify-between">
                <span className="capitalize">{service.replace(/([A-Z])/g, ' $1').toLowerCase()}:</span>
                <span className={`font-medium ${
                  status === 'healthy' ? 'text-green-400' :
                  status === 'degraded' ? 'text-orange-400' :
                  status === 'circuit_open' ? 'text-red-400' :
                  'text-gray-400'
                }`}>
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {sessionWarning && (
        <div className="mt-3 p-2 bg-orange-900/20 border border-orange-500/30 rounded">
          <div className="flex items-center justify-between">
            <div className="text-xs text-orange-400">
              Session expires in {sessionWarning.timeLeft} minute{sessionWarning.timeLeft !== 1 ? 's' : ''}
            </div>
            <button
              onClick={handleExtendSession}
              disabled={isExtending}
              className="flex items-center space-x-1 text-xs bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-1 rounded transition-colors"
            >
              {isExtending ? (
                <Loader className="w-3 h-3 animate-spin" />
              ) : (
                <RefreshCw className="w-3 h-3" />
              )}
              <span>{isExtending ? 'Extending...' : 'Extend'}</span>
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="text-xs text-red-400 mt-1">
          Error: {error}
        </div>
      )}
      
      {lastCheck && (
        <div className="text-xs text-gray-600 mt-1">
          Last check: {new Date(lastCheck).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default AuthStatusIndicator;