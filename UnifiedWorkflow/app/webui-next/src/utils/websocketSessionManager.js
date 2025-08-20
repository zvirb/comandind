/**
 * WebSocket Session Manager - Maintain WebSocket connections across navigation
 * Prevents connection loss when users navigate between features
 */

import { SecureAuth } from './secureAuth';

class WebSocketSessionManager {
  constructor() {
    this.connections = new Map(); // Store active connections by endpoint
    this.reconnectAttempts = new Map(); // Track reconnection attempts
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second delay
    this.sessionListeners = new Set(); // Session change listeners
  }

  /**
   * Get or create a persistent WebSocket connection
   */
  async getConnection(endpoint, protocols = [], options = {}) {
    const connectionKey = this.getConnectionKey(endpoint, protocols);
    
    // Return existing connection if still valid
    if (this.connections.has(connectionKey)) {
      const connection = this.connections.get(connectionKey);
      if (connection.readyState === WebSocket.OPEN) {
        console.log('WebSocketSessionManager: Reusing existing connection for', endpoint);
        return connection;
      }
      
      // Clean up invalid connection
      this.cleanup(connectionKey);
    }

    // Create new connection with session persistence
    return this.createConnection(endpoint, protocols, options, connectionKey);
  }

  /**
   * Create a new WebSocket connection with session management
   */
  async createConnection(endpoint, protocols, options, connectionKey) {
    try {
      // Get current authentication token
      const token = SecureAuth.getAuthToken();
      if (!token) {
        throw new Error('No authentication token available for WebSocket connection');
      }

      // Construct WebSocket URL with JWT query parameter (new authentication method)
      const wsUrl = this.constructWebSocketURL(endpoint, token);
      
      console.log('WebSocketSessionManager: Creating authenticated connection to', endpoint);
      console.log('WebSocketSessionManager: Using JWT query parameter authentication');
      
      // Create WebSocket connection with JWT query parameter authentication
      const ws = new WebSocket(wsUrl, protocols);
      
      // Set up connection lifecycle handlers
      this.setupConnectionHandlers(ws, connectionKey, endpoint, protocols, options);
      
      // Store connection
      this.connections.set(connectionKey, ws);
      this.reconnectAttempts.set(connectionKey, 0);
      
      // Add session management properties
      ws.sessionManaged = true;
      ws.endpoint = endpoint;
      ws.protocols = protocols;
      ws.options = options;
      ws.connectionKey = connectionKey;
      ws.isAuthenticated = true; // Mark as authenticated connection
      
      return ws;
      
    } catch (error) {
      console.error('WebSocketSessionManager: Failed to create connection:', error);
      throw error;
    }
  }

  /**
   * Set up WebSocket connection event handlers
   */
  setupConnectionHandlers(ws, connectionKey, endpoint, protocols, options) {
    const originalOnOpen = ws.onopen;
    const originalOnClose = ws.onclose;
    const originalOnError = ws.onerror;

    ws.onopen = (event) => {
      console.log('WebSocketSessionManager: Connection opened for', endpoint);
      this.reconnectAttempts.set(connectionKey, 0); // Reset reconnect attempts
      
      // Send session restoration message if this is a reconnection
      if (ws.isReconnection) {
        this.sendSessionRestoration(ws);
      }
      
      // Call original handler if exists
      if (originalOnOpen) {
        originalOnOpen.call(ws, event);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocketSessionManager: Connection closed for', endpoint, 'Code:', event.code);
      
      // Call original handler first
      if (originalOnClose) {
        originalOnClose.call(ws, event);
      }
      
      // Attempt reconnection if not a normal closure
      if (event.code !== 1000 && event.code !== 1001) {
        this.attemptReconnection(connectionKey, endpoint, protocols, options);
      } else {
        // Clean up for normal closures
        this.cleanup(connectionKey);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocketSessionManager: Connection error for', endpoint, event);
      
      // Call original handler if exists
      if (originalOnError) {
        originalOnError.call(ws, event);
      }
    };
  }

  /**
   * Attempt to reconnect a failed WebSocket connection
   */
  async attemptReconnection(connectionKey, endpoint, protocols, options) {
    const attempts = this.reconnectAttempts.get(connectionKey) || 0;
    
    if (attempts >= this.maxReconnectAttempts) {
      console.error('WebSocketSessionManager: Max reconnection attempts reached for', endpoint);
      this.cleanup(connectionKey);
      return;
    }

    console.log(`WebSocketSessionManager: Attempting reconnection ${attempts + 1}/${this.maxReconnectAttempts} for`, endpoint);
    
    // Exponential backoff delay
    const delay = this.reconnectDelay * Math.pow(2, attempts);
    
    setTimeout(async () => {
      try {
        this.reconnectAttempts.set(connectionKey, attempts + 1);
        
        // Create new connection
        const ws = await this.createConnection(endpoint, protocols, options, connectionKey);
        ws.isReconnection = true;
        
      } catch (error) {
        console.error('WebSocketSessionManager: Reconnection failed:', error);
        this.attemptReconnection(connectionKey, endpoint, protocols, options);
      }
    }, delay);
  }

  /**
   * Send session restoration message to newly connected WebSocket
   */
  sendSessionRestoration(ws) {
    try {
      const token = SecureAuth.getAuthToken();
      if (token) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        
        ws.send(JSON.stringify({
          type: 'session_restoration',
          session_id: payload.session_id || payload.sub || 'unknown',
          user_id: payload.id || payload.sub,
          timestamp: Date.now(),
          auth_method: 'integration_layer_normalized_jwt',
          integration_layer: true // Signal that we're using the integration layer
        }));
        
        console.log('WebSocketSessionManager: Sent integration layer session restoration message');
      }
    } catch (error) {
      console.error('WebSocketSessionManager: Failed to send session restoration:', error);
      // Send fallback restoration message
      try {
        ws.send(JSON.stringify({
          type: 'session_restoration',
          session_id: Date.now().toString(),
          timestamp: Date.now(),
          auth_method: 'integration_layer_fallback',
          integration_layer: true
        }));
      } catch (fallbackError) {
        console.error('WebSocketSessionManager: Fallback restoration also failed:', fallbackError);
      }
    }
  }

  /**
   * Construct WebSocket URL from endpoint with JWT authentication
   */
  constructWebSocketURL(endpoint, token = null) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    // Ensure endpoint starts with /
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    
    // For chat service, use new authentication method with JWT query parameter
    if (endpoint.includes('/chat/ws') || endpoint.includes('/ws/chat')) {
      const chatUrl = `${protocol}//${host}/ws/chat`;
      if (token) {
        return `${chatUrl}?token=${encodeURIComponent(token)}`;
      }
      return chatUrl;
    }
    
    // For other endpoints, use the original URL construction
    return `${protocol}//${host}${normalizedEndpoint}`;
  }

  /**
   * Generate connection key for endpoint and protocols
   */
  getConnectionKey(endpoint, protocols) {
    const protocolString = protocols.sort().join(',');
    return `${endpoint}|${protocolString}`;
  }

  /**
   * Clean up connection and related resources
   */
  cleanup(connectionKey) {
    const connection = this.connections.get(connectionKey);
    
    if (connection) {
      if (connection.readyState === WebSocket.OPEN) {
        connection.close(1000, 'Session cleanup');
      }
      
      this.connections.delete(connectionKey);
    }
    
    this.reconnectAttempts.delete(connectionKey);
  }

  /**
   * Handle authentication state changes
   */
  handleAuthChange(isAuthenticated) {
    if (!isAuthenticated) {
      // Close all connections when user logs out
      console.log('WebSocketSessionManager: Closing all connections due to logout');
      this.closeAllConnections();
    } else {
      // Notify session listeners about auth change
      this.sessionListeners.forEach(listener => {
        try {
          listener({ type: 'auth_restored', isAuthenticated });
        } catch (error) {
          console.error('WebSocketSessionManager: Session listener error:', error);
        }
      });
    }
  }

  /**
   * Close all active WebSocket connections
   */
  closeAllConnections() {
    this.connections.forEach((connection, key) => {
      this.cleanup(key);
    });
  }

  /**
   * Add a session change listener
   */
  addSessionListener(listener) {
    this.sessionListeners.add(listener);
    
    // Return cleanup function
    return () => {
      this.sessionListeners.delete(listener);
    };
  }

  /**
   * Get connection status for monitoring
   */
  getConnectionStatus() {
    const status = new Map();
    
    this.connections.forEach((connection, key) => {
      status.set(key, {
        readyState: connection.readyState,
        endpoint: connection.endpoint,
        isReconnection: connection.isReconnection || false,
        reconnectAttempts: this.reconnectAttempts.get(key) || 0
      });
    });
    
    return status;
  }

  /**
   * Destroy the session manager
   */
  destroy() {
    this.closeAllConnections();
    this.sessionListeners.clear();
  }
}

// Create singleton instance
const websocketSessionManager = new WebSocketSessionManager();

export default websocketSessionManager;
export { WebSocketSessionManager };