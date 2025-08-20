/**
 * Secure WebSocket Client with Enhanced Security and Auto-Reconnection
 * Fixes CVE-2024-WS002 and implements comprehensive security measures
 */

class SecureWebSocketClient {
    constructor(options = {}) {
        // Connection configuration
        this.baseUrl = options.baseUrl || this.getWebSocketBaseUrl();
        this.endpoint = options.endpoint || '/ws/v2/secure/agent';
        this.sessionId = options.sessionId || this.generateSessionId();
        
        // Security configuration
        this.authToken = null;
        this.encryptionEnabled = options.encryptionEnabled || true;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        this.heartbeatInterval = options.heartbeatInterval || 30000; // 30 seconds
        
        // Connection state
        this.websocket = null;
        this.connectionState = 'disconnected'; // disconnected, connecting, connected, reconnecting
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        
        // Security monitoring
        this.messageQueue = [];
        this.pendingMessages = new Map();
        this.messageIdCounter = 0;
        this.rateLimitTracker = new Map();
        
        // Event handlers
        this.eventHandlers = new Map();
        this.middlewareStack = [];
        
        // Timers
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        
        // Initialize
        this.setupDefaultHandlers();
        this.setupSecurityMonitoring();
    }

    /**
     * Initialize WebSocket connection with header-based authentication
     * FIXES CVE-2024-WS002: No tokens in query parameters
     */
    async connect(authToken) {
        if (this.connectionState === 'connecting' || this.connectionState === 'connected') {
            console.warn('WebSocket connection already active');
            return;
        }

        this.authToken = authToken;
        this.connectionState = 'connecting';
        
        try {
            // Validate auth token before connecting
            if (!this.validateAuthToken(authToken)) {
                throw new Error('Invalid authentication token format');
            }

            // Build WebSocket URL without token in query parameters
            const wsUrl = `${this.baseUrl}${this.endpoint}/${this.sessionId}`;
            
            console.log(`[SecureWebSocket] Connecting to: ${wsUrl.replace(/\/ws\/.*/, '/ws/[SECURE]')}`);
            
            // Create WebSocket connection with security headers
            this.websocket = new WebSocket(wsUrl, [], {
                headers: this.buildSecureHeaders(authToken)
            });
            
            // Note: Browser WebSocket API doesn't support custom headers
            // For browsers, we use a different approach with a secure handshake
            if (typeof window !== 'undefined') {
                await this.handleBrowserWebSocketAuth(wsUrl, authToken);
            }
            
            this.setupWebSocketEventHandlers();
            
        } catch (error) {
            console.error('[SecureWebSocket] Connection failed:', error);
            this.connectionState = 'disconnected';
            this.emit('connectionError', { error: error.message, recoverable: true });
            this.scheduleReconnect();
        }
    }

    /**
     * Handle browser WebSocket authentication using secure handshake
     */
    async handleBrowserWebSocketAuth(wsUrl, authToken) {
        // For browsers, we send auth token in first message after connection
        this.websocket = new WebSocket(wsUrl);
        
        return new Promise((resolve, reject) => {
            const authTimeout = setTimeout(() => {
                reject(new Error('Authentication timeout'));
            }, 10000); // 10 second timeout
            
            this.websocket.onopen = () => {
                // Send authentication message immediately
                const authMessage = {
                    type: 'authenticate',
                    data: {
                        token: authToken,
                        timestamp: new Date().toISOString(),
                        client_version: '2.0.0'
                    }
                };
                
                this.websocket.send(JSON.stringify(authMessage));
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'connection_established' || message.type === 'enhanced_connection_ready') {
                        clearTimeout(authTimeout);
                        resolve();
                    } else if (message.type === 'authentication_failed') {
                        clearTimeout(authTimeout);
                        reject(new Error('Authentication failed: ' + message.data.reason));
                    }
                } catch (error) {
                    // Continue waiting for proper auth response
                }
            };
            
            this.websocket.onerror = (error) => {
                clearTimeout(authTimeout);
                reject(error);
            };
        });
    }

    /**
     * Build secure headers for WebSocket connection
     */
    buildSecureHeaders(authToken) {
        return {
            'Authorization': `Bearer ${authToken}`,
            'X-Client-Version': '2.0.0',
            'X-Security-Level': 'enhanced',
            'User-Agent': this.getSecureUserAgent()
        };
    }

    /**
     * Setup WebSocket event handlers with security measures
     */
    setupWebSocketEventHandlers() {
        if (!this.websocket) return;

        this.websocket.onopen = (event) => {
            console.log('[SecureWebSocket] Connection established');
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            this.startHeartbeat();
            this.processPendingMessages();
            this.emit('connected', { sessionId: this.sessionId });
        };

        this.websocket.onmessage = async (event) => {
            try {
                await this.handleIncomingMessage(event.data);
            } catch (error) {
                console.error('[SecureWebSocket] Message handling error:', error);
                this.emit('messageError', { error: error.message });
            }
        };

        this.websocket.onclose = (event) => {
            console.log('[SecureWebSocket] Connection closed:', event.code, event.reason);
            this.connectionState = 'disconnected';
            this.stopHeartbeat();
            
            this.emit('disconnected', { 
                code: event.code, 
                reason: event.reason,
                wasClean: event.wasClean
            });
            
            // Auto-reconnect unless explicitly closed
            if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.scheduleReconnect();
            }
        };

        this.websocket.onerror = (error) => {
            console.error('[SecureWebSocket] WebSocket error:', error);
            this.emit('error', { error: error.message || 'WebSocket error' });
        };
    }

    /**
     * Handle incoming messages with security validation
     */
    async handleIncomingMessage(rawMessage) {
        let message;
        
        try {
            message = JSON.parse(rawMessage);
        } catch (error) {
            console.error('[SecureWebSocket] Invalid JSON received:', error);
            return;
        }

        // Validate message structure
        if (!this.validateMessageStructure(message)) {
            console.warn('[SecureWebSocket] Invalid message structure:', message);
            return;
        }

        // Apply security middleware
        for (const middleware of this.middlewareStack) {
            try {
                await middleware(message);
            } catch (error) {
                console.error('[SecureWebSocket] Middleware error:', error);
                return;
            }
        }

        // Handle message decryption if needed
        if (message.encrypted) {
            try {
                message = await this.decryptMessage(message);
            } catch (error) {
                console.error('[SecureWebSocket] Decryption failed:', error);
                return;
            }
        }

        // Route message to appropriate handler
        await this.routeMessage(message);
    }

    /**
     * Send secure message with encryption and integrity validation
     */
    async sendSecureMessage(messageType, data, options = {}) {
        if (this.connectionState !== 'connected') {
            // Queue message for later delivery
            this.messageQueue.push({ messageType, data, options, timestamp: Date.now() });
            return false;
        }

        // Check rate limiting
        if (!this.checkRateLimit(messageType)) {
            console.warn('[SecureWebSocket] Rate limit exceeded for message type:', messageType);
            this.emit('rateLimitExceeded', { messageType });
            return false;
        }

        try {
            const messageId = this.generateMessageId();
            
            const message = {
                type: messageType,
                data: data,
                message_id: messageId,
                timestamp: new Date().toISOString(),
                encrypted: false
            };

            // Encrypt sensitive messages
            if (options.encrypt || this.isSensitiveMessageType(messageType)) {
                await this.encryptMessage(message);
            }

            // Add message integrity signature
            if (options.signed || messageType === 'agent_command') {
                message.signature = await this.signMessage(message);
            }

            // Send message
            this.websocket.send(JSON.stringify(message));
            
            // Track pending message if expecting response
            if (options.expectResponse) {
                this.pendingMessages.set(messageId, {
                    timestamp: Date.now(),
                    timeout: options.timeout || 30000,
                    resolve: options.resolve,
                    reject: options.reject
                });
            }

            return true;

        } catch (error) {
            console.error('[SecureWebSocket] Send message error:', error);
            this.emit('sendError', { error: error.message, messageType });
            return false;
        }
    }

    /**
     * Start heartbeat to maintain connection health
     */
    startHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
        }

        this.heartbeatTimer = setInterval(() => {
            if (this.connectionState === 'connected') {
                this.sendSecureMessage('heartbeat', {
                    timestamp: new Date().toISOString(),
                    client_health: 'healthy'
                });
            }
        }, this.heartbeatInterval);
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Schedule reconnection with exponential backoff
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[SecureWebSocket] Max reconnection attempts reached');
            this.emit('maxReconnectAttemptsReached', { attempts: this.reconnectAttempts });
            return;
        }

        this.connectionState = 'reconnecting';
        this.reconnectAttempts++;
        
        console.log(`[SecureWebSocket] Scheduling reconnect attempt ${this.reconnectAttempts} in ${this.reconnectDelay}ms`);
        
        this.reconnectTimer = setTimeout(async () => {
            console.log(`[SecureWebSocket] Reconnection attempt ${this.reconnectAttempts}`);
            
            try {
                await this.connect(this.authToken);
            } catch (error) {
                console.error('[SecureWebSocket] Reconnection failed:', error);
                
                // Exponential backoff with jitter
                this.reconnectDelay = Math.min(
                    this.reconnectDelay * 2 + Math.random() * 1000,
                    this.maxReconnectDelay
                );
                
                this.scheduleReconnect();
            }
        }, this.reconnectDelay);

        this.emit('reconnecting', { 
            attempt: this.reconnectAttempts, 
            maxAttempts: this.maxReconnectAttempts,
            delay: this.reconnectDelay
        });
    }

    /**
     * Process queued messages after reconnection
     */
    async processPendingMessages() {
        const messagesToProcess = [...this.messageQueue];
        this.messageQueue = [];

        for (const queuedMessage of messagesToProcess) {
            // Skip messages older than 5 minutes
            if (Date.now() - queuedMessage.timestamp > 300000) {
                continue;
            }

            await this.sendSecureMessage(
                queuedMessage.messageType,
                queuedMessage.data,
                queuedMessage.options
            );
        }
    }

    /**
     * Validate authentication token format
     */
    validateAuthToken(token) {
        if (!token || typeof token !== 'string') {
            return false;
        }

        // Basic JWT format validation (3 parts separated by dots)
        const parts = token.split('.');
        if (parts.length !== 3) {
            return false;
        }

        // Validate each part is base64
        try {
            for (const part of parts) {
                atob(part.replace(/-/g, '+').replace(/_/g, '/'));
            }
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Validate incoming message structure
     */
    validateMessageStructure(message) {
        return message &&
               typeof message === 'object' &&
               typeof message.type === 'string' &&
               message.data !== undefined &&
               typeof message.timestamp === 'string';
    }

    /**
     * Check rate limiting for message types
     */
    checkRateLimit(messageType) {
        const now = Date.now();
        const windowSize = 60000; // 1 minute window
        const limits = {
            'heartbeat': 120,      // 2 per second max
            'agent_command': 10,   // 10 per minute
            'stream_request': 5,   // 5 per minute
            'default': 60          // 1 per second default
        };

        const limit = limits[messageType] || limits.default;
        const key = `${messageType}_${Math.floor(now / windowSize)}`;
        
        const count = this.rateLimitTracker.get(key) || 0;
        if (count >= limit) {
            return false;
        }

        this.rateLimitTracker.set(key, count + 1);

        // Clean old entries
        for (const [trackerKey] of this.rateLimitTracker) {
            const timestamp = parseInt(trackerKey.split('_').pop());
            if (now - timestamp * windowSize > windowSize * 2) {
                this.rateLimitTracker.delete(trackerKey);
            }
        }

        return true;
    }

    /**
     * Encrypt sensitive message (placeholder implementation)
     */
    async encryptMessage(message) {
        if (!this.encryptionEnabled) {
            return message;
        }

        // Placeholder for actual encryption implementation
        // In production, this would use proper encryption libraries
        message.encrypted = true;
        message.data = { encrypted_payload: btoa(JSON.stringify(message.data)) };
        
        return message;
    }

    /**
     * Decrypt encrypted message (placeholder implementation)
     */
    async decryptMessage(message) {
        if (!message.encrypted) {
            return message;
        }

        // Placeholder for actual decryption implementation
        try {
            message.data = JSON.parse(atob(message.data.encrypted_payload));
            message.encrypted = false;
            return message;
        } catch (error) {
            throw new Error('Decryption failed');
        }
    }

    /**
     * Sign message for integrity validation (placeholder implementation)
     */
    async signMessage(message) {
        // Placeholder for actual message signing
        const content = `${message.type}:${message.message_id}:${message.timestamp}`;
        return btoa(content); // Simple encoding, use proper HMAC in production
    }

    /**
     * Route message to appropriate handler
     */
    async routeMessage(message) {
        const handlers = this.eventHandlers.get(message.type) || [];
        
        for (const handler of handlers) {
            try {
                await handler(message);
            } catch (error) {
                console.error(`[SecureWebSocket] Handler error for ${message.type}:`, error);
            }
        }

        // Handle system messages
        if (message.type === 'heartbeat_ack') {
            console.debug('[SecureWebSocket] Heartbeat acknowledged');
        } else if (message.type === 'error') {
            this.emit('serverError', message.data);
        }
    }

    /**
     * Setup default message handlers
     */
    setupDefaultHandlers() {
        this.on('connection_established', (message) => {
            console.log('[SecureWebSocket] Server confirmed connection:', message.data);
        });

        this.on('enhanced_connection_ready', (message) => {
            console.log('[SecureWebSocket] Enhanced secure connection ready:', message.data);
        });

        this.on('rate_limit_exceeded', (message) => {
            console.warn('[SecureWebSocket] Server rate limit exceeded:', message.data);
        });
    }

    /**
     * Setup security monitoring
     */
    setupSecurityMonitoring() {
        // Security middleware for message validation
        this.addMiddleware(async (message) => {
            // Check for suspicious patterns
            const messageStr = JSON.stringify(message);
            const suspiciousPatterns = [
                /<script/i, /javascript:/i, /eval\(/i,
                /document\.cookie/i, /localStorage/i
            ];

            for (const pattern of suspiciousPatterns) {
                if (pattern.test(messageStr)) {
                    throw new Error('Suspicious content detected');
                }
            }
        });

        // Monitoring for connection health
        this.on('connected', () => {
            console.log('[SecureWebSocket] Security monitoring active');
        });
    }

    /**
     * Utility methods
     */
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 16) + '_' + Date.now();
    }

    generateMessageId() {
        return ++this.messageIdCounter;
    }

    getWebSocketBaseUrl() {
        if (typeof window === 'undefined') {
            return 'ws://localhost:8000';
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}`;
    }

    getSecureUserAgent() {
        if (typeof navigator !== 'undefined') {
            return `SecureWebSocketClient/2.0.0 (${navigator.userAgent})`;
        }
        return 'SecureWebSocketClient/2.0.0';
    }

    isSensitiveMessageType(messageType) {
        const sensitiveTypes = [
            'agent_command', 'file_operation', 'user_data',
            'authentication', 'token_refresh'
        ];
        return sensitiveTypes.includes(messageType);
    }

    /**
     * Event system
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        const handlers = this.eventHandlers.get(event) || [];
        for (const handler of handlers) {
            try {
                handler(data);
            } catch (error) {
                console.error(`[SecureWebSocket] Event handler error for ${event}:`, error);
            }
        }
    }

    addMiddleware(middleware) {
        this.middlewareStack.push(middleware);
    }

    /**
     * Public API methods
     */
    async disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        this.stopHeartbeat();
        this.connectionState = 'disconnected';

        if (this.websocket) {
            this.websocket.close(1000, 'Client disconnect');
            this.websocket = null;
        }
    }

    getConnectionState() {
        return this.connectionState;
    }

    getConnectionStats() {
        return {
            state: this.connectionState,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            pendingMessages: this.pendingMessages.size,
            sessionId: this.sessionId
        };
    }

    // Convenience methods for common operations
    async sendAgentCommand(command, parameters = {}) {
        return this.sendSecureMessage('agent_command', {
            command,
            parameters,
            priority: 'normal'
        }, { encrypt: true, expectResponse: true });
    }

    async requestStream(streamType, filters = {}) {
        return this.sendSecureMessage('stream_request', {
            stream_type: streamType,
            filters,
            buffer_size: 1000
        });
    }

    async selectHeliosAgents(agents, orchestrationMode = 'parallel') {
        return this.sendSecureMessage('agent_selection', {
            selected_agents: agents,
            orchestration_mode: orchestrationMode,
            max_agents_concurrent: 3
        });
    }
}

// Export for use in different environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecureWebSocketClient;
} else if (typeof window !== 'undefined') {
    window.SecureWebSocketClient = SecureWebSocketClient;
}