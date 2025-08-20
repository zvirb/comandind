import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Calendar,
  Folder,
  Mail,
  CheckCircle,
  XCircle,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  Trash2
} from 'lucide-react';
import { 
  getOAuthStatus, 
  initiateOAuthConnection, 
  handleOAuthCallback,
  getServiceInfo,
  GOOGLE_SERVICES 
} from '../utils/oauth';
import { OAuthStateManager } from '../utils/secureAuth';
import { SecureAuth } from '../utils/secureAuth';

const GoogleOAuthIntegration = () => {
  const [oauthStatus, setOauthStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState({});
  const [error, setError] = useState(null);

  // Load OAuth status on component mount
  useEffect(() => {
    loadOAuthStatus();
  }, []);

  // Handle OAuth callback from URL params
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('code') && urlParams.has('state')) {
      handleOAuthReturn(urlParams);
    }
  }, []);

  const loadOAuthStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const status = await getOAuthStatus();
      setOauthStatus(status.data || {});
    } catch (error) {
      console.error('Failed to load OAuth status:', error);
      setError('Failed to load Google services status');
      // Set empty status so UI still renders
      setOauthStatus({});
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthReturn = async (urlParams) => {
    try {
      setLoading(true);
      await handleOAuthCallback(urlParams);
      
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Reload status
      await loadOAuthStatus();
    } catch (error) {
      console.error('OAuth callback failed:', error);
      setError(`OAuth connection failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (service) => {
    try {
      setConnecting(prev => ({ ...prev, [service]: true }));
      setError(null);
      
      await initiateOAuthConnection(service);
      // OAuth will redirect to Google, so this component will unmount
    } catch (error) {
      console.error(`Failed to connect ${service}:`, error);
      setError(`Failed to connect to ${getServiceInfo(service).name}`);
      setConnecting(prev => ({ ...prev, [service]: false }));
    }
  };

  const handleDisconnect = async (service) => {
    try {
      setConnecting(prev => ({ ...prev, [service]: true }));
      setError(null);
      
      const response = await SecureAuth.makeSecureRequest(`/api/v1/oauth/google/disconnect/${service}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to disconnect ${service}`);
      }
      
      // Reload status
      await loadOAuthStatus();
    } catch (error) {
      console.error(`Failed to disconnect ${service}:`, error);
      setError(`Failed to disconnect from ${getServiceInfo(service).name}`);
    } finally {
      setConnecting(prev => ({ ...prev, [service]: false }));
    }
  };

  const getServiceIcon = (service) => {
    switch (service) {
      case GOOGLE_SERVICES.CALENDAR:
        return <Calendar className="w-6 h-6" />;
      case GOOGLE_SERVICES.DRIVE:
        return <Folder className="w-6 h-6" />;
      case GOOGLE_SERVICES.GMAIL:
        return <Mail className="w-6 h-6" />;
      default:
        return <ExternalLink className="w-6 h-6" />;
    }
  };

  const getConnectionStatus = (service) => {
    const status = oauthStatus[service];
    if (!status) return { connected: false, expired: false, health: 'disconnected' };
    
    const now = Date.now();
    const lastSyncDate = status.last_sync ? new Date(status.last_sync).getTime() : null;
    const syncHealthThreshold = 24 * 60 * 60 * 1000; // 24 hours
    
    let health = 'connected';
    if (status.token_expired) health = 'expired';
    else if (lastSyncDate && (now - lastSyncDate > syncHealthThreshold)) health = 'stale';
    
    return {
      connected: status.connected || false,
      expired: status.token_expired || false,
      lastSync: status.last_sync || null,
      email: status.email || null,
      health: health,
      tokenExpiresAt: status.token_expires_at || null,
      syncInterval: status.sync_interval || null
    };
  };

  const renderServiceCard = (service) => {
    const serviceInfo = getServiceInfo(service);
    const status = getConnectionStatus(service);
    const isConnecting = connecting[service];

    const healthIndicatorColors = {
        'connected': 'border-green-800 hover:border-green-700',
        'expired': 'border-yellow-800 hover:border-yellow-700',
        'stale': 'border-orange-800 hover:border-orange-700',
        'disconnected': 'border-gray-800 hover:border-gray-700'
      };

      return (
        <motion.div
          key={service}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 bg-gray-900/50 rounded-lg border ${healthIndicatorColors[status.health]} transition-colors`}
        >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`w-12 h-12 ${serviceInfo.color} rounded-lg flex items-center justify-center text-white`}>
              {getServiceIcon(service)}
            </div>
            <div>
              <h3 className="font-medium text-white">{serviceInfo.name}</h3>
              <p className="text-sm text-gray-400">{serviceInfo.description}</p>
              {status.connected && status.email && (
                <p className="text-xs text-gray-500 mt-1">Connected as: {status.email}</p>
              )}
              {status.connected && status.lastSync && (
                <p className="text-xs text-gray-500">Last sync: {new Date(status.lastSync).toLocaleDateString()}</p>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Connection Status */}
            {status.health === 'connected' && (
              <div className="flex items-center space-x-1 text-green-400">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm">Connected</span>
              </div>
            )}
            
            {status.health === 'expired' && (
              <div className="flex items-center space-x-1 text-yellow-400">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">Token Expired</span>
              </div>
            )}
            
            {status.health === 'stale' && (
              <div className="flex items-center space-x-1 text-orange-400">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">Sync Stale</span>
              </div>
            )}
            
            {status.health === 'disconnected' && (
              <div className="flex items-center space-x-1 text-gray-400">
                <XCircle className="w-4 h-4" />
                <span className="text-sm">Not Connected</span>
              </div>
            )}

            {/* Action Button */}
            {!status.connected || status.expired ? (
              <button
                onClick={() => handleConnect(service)}
                disabled={isConnecting}
                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConnecting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    <span>{status.expired ? 'Reconnect' : 'Connect'}</span>
                  </>
                )}
              </button>
            ) : (
              <div className="flex space-x-2">
                <button
                  onClick={() => handleConnect(service)}
                  disabled={isConnecting}
                  className="flex items-center space-x-1 px-3 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
                  title="Refresh connection and validate OAuth token"
                >
                  <RefreshCw className={`w-4 h-4 ${isConnecting ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={() => handleDisconnect(service)}
                  disabled={isConnecting}
                  className="flex items-center space-x-1 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  title="Disconnect service"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
        <span className="ml-2 text-gray-400">Loading Google services...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Google Services Integration</h2>
        <button
          onClick={loadOAuthStatus}
          className="flex items-center space-x-2 px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
          title="Refresh status"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-red-900/20 border border-red-800 rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
          </div>
        </motion.div>
      )}

      <div className="space-y-4">
        {Object.values(GOOGLE_SERVICES).map(service => renderServiceCard(service))}
      </div>

      <div className="p-4 bg-blue-900/20 border border-blue-800 rounded-lg">
        <div className="flex items-center space-x-2 mb-2">
          <AlertCircle className="w-5 h-5 text-blue-400" />
          <span className="font-medium text-blue-400">Integration Information</span>
        </div>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Connecting to Google services will redirect you to Google's authorization page</li>
          <li>• You can revoke access at any time from your Google Account settings</li>
          <li>• Tokens are automatically refreshed to maintain connection</li>
          <li>• All data access follows Google's security and privacy policies</li>
        </ul>
      </div>
    </div>
  );
};

export default GoogleOAuthIntegration;