import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Wifi, WifiOff, AlertTriangle, CheckCircle, XCircle, 
  RefreshCw, MessageSquare, Mic, Volume2, Database,
  Clock, Activity
} from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';

/**
 * ServiceStatusIndicator Component
 * Monitors and displays the health status of backend services
 * Provides graceful degradation information and service recovery status
 */
const ServiceStatusIndicatorComponent = ({ className = "", compact = false }) => {
  const [services, setServices] = useState({
    chat: { status: 'checking', name: 'Chat Service', port: 8007, lastCheck: null },
    voice: { status: 'checking', name: 'Voice Service', port: 8006, lastCheck: null },
    api: { status: 'checking', name: 'Main API', port: 8000, lastCheck: null },
    database: { status: 'checking', name: 'Database', port: null, lastCheck: null }
  });
  const [hasInitialized, setHasInitialized] = useState(false);
  
  const [isExpanded, setIsExpanded] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Check service health
  const checkServiceHealth = useCallback(async (serviceKey, endpoint) => {
    try {
      const response = await SecureAuth.makeSecureRequest(endpoint, {
        timeout: 5000 // 5 second timeout
      });
      
      if (response.ok) {
        const data = await response.json().catch(() => ({ status: 'unknown' }));
        return {
          status: data.status === 'healthy' ? 'online' : 'degraded',
          details: data,
          lastCheck: new Date()
        };
      } else {
        return {
          status: 'offline',
          details: { error: `HTTP ${response.status}` },
          lastCheck: new Date()
        };
      }
    } catch (error) {
      return {
        status: 'offline',
        details: { error: error.message },
        lastCheck: new Date()
      };
    }
  }, []);

  // Check all services
  const checkAllServices = useCallback(async () => {
    setIsRefreshing(true);
    
    const serviceChecks = [
      { key: 'api', endpoint: '/api/v1/health' },
      { key: 'chat', endpoint: '/api/v1/chat/health' }, // Proxied through main API
      { key: 'voice', endpoint: '/api/v1/voice/health' }, // Proxied through main API
      { key: 'database', endpoint: '/api/v1/database/health' } // Proxied through main API
    ];

    const results = await Promise.allSettled(
      serviceChecks.map(async ({ key, endpoint }) => {
        const result = await checkServiceHealth(key, endpoint);
        return { key, ...result };
      })
    );

    setServices(prevServices => {
      const newServices = { ...prevServices };
      
      results.forEach((result, index) => {
        const serviceKey = serviceChecks[index].key;
        
        if (result.status === 'fulfilled') {
          newServices[serviceKey] = {
            ...newServices[serviceKey],
            ...result.value
          };
        } else {
          newServices[serviceKey] = {
            ...newServices[serviceKey],
            status: 'offline',
            details: { error: 'Check failed' },
            lastCheck: new Date()
          };
        }
      });
      
      return newServices;
    });
    
    // Mark as initialized after first check
    if (!hasInitialized) {
      setHasInitialized(true);
    }
    
    setLastUpdate(new Date());
    setIsRefreshing(false);
  }, [checkServiceHealth]);

  // Initial check and periodic updates with Page Visibility API optimization
  useEffect(() => {
    let isVisible = !document.hidden;
    let activeInterval = null;

    const startPolling = () => {
      if (activeInterval) clearInterval(activeInterval);
      // Optimized: Increased from 30s to 5 minutes for reduced server load
      activeInterval = setInterval(checkAllServices, 300000);
    };

    const stopPolling = () => {
      if (activeInterval) {
        clearInterval(activeInterval);
        activeInterval = null;
      }
    };

    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
      if (isVisible) {
        // Check services immediately when tab becomes visible
        checkAllServices();
        startPolling();
      } else {
        // Stop polling when tab is hidden to save resources
        stopPolling();
      }
    };

    // Initial check
    checkAllServices();
    
    // Start polling if visible
    if (isVisible) {
      startPolling();
    }

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [checkAllServices]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'degraded':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'offline':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'checking':
      default:
        return <RefreshCw className="w-4 h-4 text-gray-400 animate-spin" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'border-green-500 bg-green-500/10';
      case 'degraded': return 'border-yellow-500 bg-yellow-500/10';
      case 'offline': return 'border-red-500 bg-red-500/10';
      case 'checking':
      default: return 'border-gray-500 bg-gray-500/10';
    }
  };

  const getServiceIcon = (serviceKey) => {
    switch (serviceKey) {
      case 'chat': return <MessageSquare className="w-4 h-4" />;
      case 'voice': return <Mic className="w-4 h-4" />;
      case 'database': return <Database className="w-4 h-4" />;
      case 'api': 
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getOverallStatus = () => {
    const statuses = Object.values(services).map(s => s.status);
    
    if (statuses.some(s => s === 'checking')) return 'checking';
    if (statuses.every(s => s === 'online')) return 'online';
    if (statuses.some(s => s === 'offline')) return 'degraded';
    return 'degraded';
  };

  const getOnlineCount = () => {
    return Object.values(services).filter(s => s.status === 'online').length;
  };

  const formatLastUpdate = () => {
    const now = new Date();
    const diff = Math.floor((now - lastUpdate) / 1000);
    
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  if (compact) {
    return (
      <div className={`service-status-compact ${className}`}>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`flex items-center space-x-2 px-3 py-2 rounded-lg border transition-all ${getStatusColor(getOverallStatus())}`}
        >
          {getStatusIcon(getOverallStatus())}
          <span className="text-sm font-medium">
            {getOnlineCount()}/{Object.keys(services).length} Services
          </span>
          <Clock className="w-3 h-3 text-gray-400" />
          <span className="text-xs text-gray-400">{formatLastUpdate()}</span>
        </button>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              className="absolute top-full left-0 mt-2 w-80 bg-gray-900/95 backdrop-blur-lg border border-gray-800 rounded-lg shadow-xl z-50"
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white">Service Status</h3>
                  <button
                    onClick={checkAllServices}
                    disabled={isRefreshing}
                    className="p-1 text-gray-400 hover:text-white transition"
                  >
                    <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  </button>
                </div>
                
                <div className="space-y-2">
                  {Object.entries(services).map(([key, service]) => (
                    <ServiceStatusRow key={key} serviceKey={key} service={service} />
                  ))}
                </div>
                
                <div className="mt-3 pt-3 border-t border-gray-800 text-xs text-gray-400">
                  Last updated: {formatLastUpdate()}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className={`service-status ${className}`}>
      <div className="bg-gray-900/50 backdrop-blur-lg border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold text-white">System Status</h3>
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-full border ${getStatusColor(getOverallStatus())}`}>
              {getStatusIcon(getOverallStatus())}
              <span className="text-sm font-medium capitalize">{getOverallStatus()}</span>
            </div>
          </div>
          
          <button
            onClick={checkAllServices}
            disabled={isRefreshing}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-white ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(services).map(([key, service]) => (
            <ServiceStatusCard key={key} serviceKey={key} service={service} />
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
          <span>Last updated: {formatLastUpdate()}</span>
          <span>{getOnlineCount()} of {Object.keys(services).length} services online</span>
        </div>
      </div>
    </div>
  );
};

const ServiceStatusRow = React.memo(({ serviceKey, service }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'online': return <CheckCircle className="w-3 h-3 text-green-400" />;
      case 'degraded': return <AlertTriangle className="w-3 h-3 text-yellow-400" />;
      case 'offline': return <XCircle className="w-3 h-3 text-red-400" />;
      case 'checking':
      default: return <RefreshCw className="w-3 h-3 text-gray-400 animate-spin" />;
    }
  };

  const getServiceIcon = (serviceKey) => {
    switch (serviceKey) {
      case 'chat': return <MessageSquare className="w-3 h-3 text-blue-400" />;
      case 'voice': return <Mic className="w-3 h-3 text-purple-400" />;
      case 'database': return <Database className="w-3 h-3 text-green-400" />;
      case 'api': 
      default: return <Activity className="w-3 h-3 text-orange-400" />;
    }
  };

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center space-x-2">
        {getServiceIcon(serviceKey)}
        <span className="text-sm font-medium text-white">{service.name}</span>
        {service.port && (
          <span className="text-xs text-gray-500">:{service.port}</span>
        )}
      </div>
      <div className="flex items-center space-x-2">
        {getStatusIcon(service.status)}
        <span className="text-xs capitalize text-gray-300">{service.status}</span>
      </div>
    </div>
  );
});

const ServiceStatusCard = React.memo(({ serviceKey, service }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'online': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'degraded': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'offline': return <XCircle className="w-4 h-4 text-red-400" />;
      case 'checking':
      default: return <RefreshCw className="w-4 h-4 text-gray-400 animate-spin" />;
    }
  };

  const getServiceIcon = (serviceKey) => {
    switch (serviceKey) {
      case 'chat': return <MessageSquare className="w-5 h-5 text-blue-400" />;
      case 'voice': return <Mic className="w-5 h-5 text-purple-400" />;
      case 'database': return <Database className="w-5 h-5 text-green-400" />;
      case 'api': 
      default: return <Activity className="w-5 h-5 text-orange-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online': return 'border-green-500 bg-green-500/10';
      case 'degraded': return 'border-yellow-500 bg-yellow-500/10';
      case 'offline': return 'border-red-500 bg-red-500/10';
      case 'checking':
      default: return 'border-gray-500 bg-gray-500/10';
    }
  };

  return (
    <div className={`p-3 rounded-lg border transition-all ${getStatusColor(service.status)}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {getServiceIcon(serviceKey)}
          <span className="font-medium text-white">{service.name}</span>
        </div>
        {getStatusIcon(service.status)}
      </div>
      
      <div className="flex items-center justify-between text-sm">
        <span className="capitalize text-gray-300">{service.status}</span>
        {service.port && (
          <span className="text-gray-500">Port {service.port}</span>
        )}
      </div>
      
      {service.details?.error && (
        <div className="mt-2 text-xs text-red-400 truncate">
          Error: {service.details.error}
        </div>
      )}
    </div>
  );
});

// Enhanced memoization with custom comparison to prevent unnecessary re-renders
const ServiceStatusIndicator = React.memo(ServiceStatusIndicatorComponent, (prevProps, nextProps) => {
  // Only re-render if className or compact prop changes
  return prevProps.className === nextProps.className && prevProps.compact === nextProps.compact;
});

export default ServiceStatusIndicator;