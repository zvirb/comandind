/**
 * Secure Error Handler - Consolidated error handling with XSS protection
 * Prevents XSS attacks, removes sensitive information, implements rate limiting
 */

class SecureErrorHandler {
    constructor() {
        this.errors = [];
        this.maxErrors = 50;
        this.rateLimitWindow = 60000; // 1 minute
        this.maxErrorsPerWindow = 20;
        this.errorCounts = new Map(); // Track errors per time window
        this.sensitivePatterns = [
            /\/home\/[^\/]+/g, // Home directory paths
            /\/Users\/[^\/]+/g, // macOS user paths
            /C:\\Users\\[^\\]+/g, // Windows user paths
            /password[=:]\s*['"]\w+['"]/gi, // Password fields
            /token[=:]\s*['"]\w+['"]/gi, // Token fields
            /key[=:]\s*['"]\w+['"]/gi, // API keys
            /secret[=:]\s*['"]\w+['"]/gi, // Secrets
            /localhost:\d+/g, // Local ports
            /127\.0\.0\.1:\d+/g, // Local IPs with ports
        ];
        this.initialized = false;
        this.storagePrefix = 'secure_errors_';
        this.storageQuotaLimit = 2 * 1024 * 1024; // 2MB limit for error storage
    }

    /**
     * Initialize the error handler with security measures
     */
    initialize() {
        if (this.initialized) return;

        this.loadPersistedErrors();
        this.setupGlobalErrorHandlers();
        this.setupStorageQuotaManagement();
        this.initialized = true;

        console.log('🛡️ Secure Error Handler initialized');
    }

    /**
     * Sanitize text to prevent XSS attacks
     */
    sanitizeText(text) {
        if (!text) return '';
        
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\//g, '&#x2F;');
    }

    /**
     * Remove sensitive information from error messages and stack traces
     */
    sanitizeErrorContent(content) {
        let sanitized = this.sanitizeText(content);
        
        // Remove sensitive patterns
        this.sensitivePatterns.forEach(pattern => {
            sanitized = sanitized.replace(pattern, '[REDACTED]');
        });

        // Limit stack trace depth to prevent information disclosure
        const lines = sanitized.split('\n');
        if (lines.length > 10) {
            sanitized = lines.slice(0, 10).join('\n') + '\n[Stack trace truncated for security]';
        }

        return sanitized;
    }

    /**
     * Check rate limiting to prevent abuse
     */
    checkRateLimit() {
        const now = Date.now();
        const windowKey = Math.floor(now / this.rateLimitWindow);
        
        // Clean old windows
        for (const [key] of this.errorCounts) {
            if (key < windowKey - 1) {
                this.errorCounts.delete(key);
            }
        }

        const currentCount = this.errorCounts.get(windowKey) || 0;
        
        if (currentCount >= this.maxErrorsPerWindow) {
            console.warn('🚨 Error rate limit exceeded, dropping error');
            return false;
        }

        this.errorCounts.set(windowKey, currentCount + 1);
        return true;
    }

    /**
     * Capture and process errors securely
     */
    captureError(error, source = 'unknown', extraInfo = {}) {
        // Rate limiting check
        if (!this.checkRateLimit()) {
            return false;
        }

        const errorInfo = {
            id: this.generateSecureId(),
            timestamp: new Date().toISOString(),
            source: this.sanitizeText(source),
            message: this.sanitizeErrorContent(error?.message || String(error)),
            stack: this.sanitizeErrorContent(error?.stack || 'No stack trace'),
            filename: this.sanitizeFilename(error?.filename || extraInfo.filename || 'unknown'),
            lineno: this.sanitizeNumber(error?.lineno || extraInfo.lineno || 0),
            colno: this.sanitizeNumber(error?.colno || extraInfo.colno || 0),
            userAgent: this.sanitizeText(navigator.userAgent),
            url: this.sanitizeUrl(location.href),
            severity: this.determineSeverity(error),
            extraInfo: this.sanitizeExtraInfo(extraInfo)
        };

        this.errors.push(errorInfo);
        
        // Maintain max errors limit
        if (this.errors.length > this.maxErrors) {
            this.errors.splice(0, this.errors.length - this.maxErrors);
        }

        this.persistErrors();
        this.notifyErrorCaptured(errorInfo);

        return true;
    }

    /**
     * Generate a secure, non-predictable ID
     */
    generateSecureId() {
        return 'err_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Sanitize filename to remove sensitive paths
     */
    sanitizeFilename(filename) {
        let sanitized = this.sanitizeText(filename);
        
        // Keep only the filename, not the full path
        const parts = sanitized.split(/[\/\\]/);
        const justFilename = parts[parts.length - 1];
        
        // If it's a URL, keep the last part
        if (sanitized.includes('://')) {
            const urlParts = sanitized.split('/');
            return urlParts[urlParts.length - 1] || 'unknown';
        }
        
        return justFilename || 'unknown';
    }

    /**
     * Sanitize numeric values
     */
    sanitizeNumber(num) {
        const parsed = parseInt(num, 10);
        return isNaN(parsed) ? 0 : Math.max(0, Math.min(999999, parsed)); // Reasonable bounds
    }

    /**
     * Sanitize URL to remove sensitive information
     */
    sanitizeUrl(url) {
        try {
            const urlObj = new URL(url);
            // Remove query parameters that might contain sensitive data
            urlObj.search = '';
            urlObj.hash = '';
            return this.sanitizeText(urlObj.toString());
        } catch {
            return '[Invalid URL]';
        }
    }

    /**
     * Sanitize extra info object
     */
    sanitizeExtraInfo(extraInfo) {
        const sanitized = {};
        const allowedKeys = ['type', 'context', 'component', 'action', 'severity'];
        
        allowedKeys.forEach(key => {
            if (extraInfo[key] !== undefined) {
                sanitized[key] = this.sanitizeText(String(extraInfo[key]));
            }
        });

        return sanitized;
    }

    /**
     * Determine error severity for prioritization
     */
    determineSeverity(error) {
        const message = (error?.message || '').toLowerCase();
        
        if (message.includes('script error') || message.includes('network')) {
            return 'low';
        }
        if (message.includes('reference') || message.includes('undefined')) {
            return 'medium';
        }
        if (message.includes('syntax') || message.includes('security')) {
            return 'high';
        }
        
        return 'medium';
    }

    /**
     * Setup global error handlers
     */
    setupGlobalErrorHandlers() {
        // Window error handler
        window.addEventListener('error', (event) => {
            event.preventDefault();
            this.captureError(event.error, 'window_error', {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                type: 'javascript_error'
            });
        }, true);

        // Promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            event.preventDefault();
            this.captureError(
                new Error(`Promise rejection: ${event.reason?.message || event.reason}`),
                'promise_rejection',
                {
                    type: 'promise_rejection',
                    reason: String(event.reason)
                }
            );
        }, true);

        // Console error override (secure)
        const originalConsoleError = console.error;
        let consoleErrorInProgress = false;

        console.error = (...args) => {
            originalConsoleError.apply(console, args);
            
            if (consoleErrorInProgress) return;
            
            const errorMessage = args.join(' ');
            if (errorMessage && !errorMessage.includes('[CAPTURED')) {
                consoleErrorInProgress = true;
                try {
                    this.captureError(
                        new Error(`Console Error: ${errorMessage}`),
                        'console_error',
                        { type: 'console_error' }
                    );
                } finally {
                    consoleErrorInProgress = false;
                }
            }
        };
    }

    /**
     * Setup localStorage quota management to prevent exhaustion
     */
    setupStorageQuotaManagement() {
        // Monitor storage usage and clean up if needed
        setInterval(() => {
            try {
                const currentUsage = this.getStorageUsage();
                if (currentUsage > this.storageQuotaLimit) {
                    this.cleanupOldErrors();
                }
            } catch (error) {
                console.warn('Storage quota check failed:', error);
            }
        }, 30000); // Check every 30 seconds
    }

    /**
     * Get current storage usage for error data
     */
    getStorageUsage() {
        let totalSize = 0;
        for (let key in localStorage) {
            if (key.startsWith(this.storagePrefix)) {
                totalSize += localStorage.getItem(key).length;
            }
        }
        return totalSize;
    }

    /**
     * Clean up old errors to free storage space
     */
    cleanupOldErrors() {
        // Remove oldest errors first
        const oldErrorCount = this.errors.length;
        this.errors = this.errors.slice(-Math.floor(this.maxErrors * 0.7)); // Keep only 70%
        
        this.persistErrors();
        
        console.log(`🧹 Cleaned up ${oldErrorCount - this.errors.length} old errors to free storage space`);
    }

    /**
     * Persist errors to localStorage securely
     */
    persistErrors() {
        try {
            const errorData = {
                errors: this.errors,
                timestamp: Date.now(),
                version: '1.0'
            };
            
            const serialized = JSON.stringify(errorData);
            
            // Check if we're approaching quota limits
            if (serialized.length > this.storageQuotaLimit * 0.8) {
                this.cleanupOldErrors();
                return; // Try again after cleanup
            }
            
            localStorage.setItem(this.storagePrefix + 'data', serialized);
        } catch (error) {
            if (error.name === 'QuotaExceededError') {
                this.cleanupOldErrors();
                console.warn('🚨 Storage quota exceeded, cleaned up old errors');
            } else {
                console.warn('Failed to persist errors:', error);
            }
        }
    }

    /**
     * Load persisted errors on startup
     */
    loadPersistedErrors() {
        try {
            const stored = localStorage.getItem(this.storagePrefix + 'data');
            if (stored) {
                const errorData = JSON.parse(stored);
                if (errorData.errors && Array.isArray(errorData.errors)) {
                    this.errors = errorData.errors.slice(-this.maxErrors); // Ensure limit
                }
            }
        } catch (error) {
            console.warn('Failed to load persisted errors:', error);
            this.errors = [];
        }
    }

    /**
     * Get errors for display (already sanitized)
     */
    getErrors(limit = null) {
        const errors = limit ? this.errors.slice(-limit) : this.errors;
        return [...errors].reverse(); // Return newest first, as a copy
    }

    /**
     * Clear all errors
     */
    clearErrors() {
        this.errors = [];
        this.errorCounts.clear();
        
        // Clear all error-related localStorage entries
        const keysToRemove = [];
        for (let key in localStorage) {
            if (key.startsWith(this.storagePrefix) || 
                key.includes('error') || 
                key.includes('emergency')) {
                keysToRemove.push(key);
            }
        }
        
        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
        });
        
        console.log('🧹 All errors cleared');
    }

    /**
     * Notify that an error was captured (for UI updates)
     */
    notifyErrorCaptured(errorInfo) {
        // Dispatch custom event for UI components to listen to
        const event = new CustomEvent('secureErrorCaptured', {
            detail: {
                id: errorInfo.id,
                severity: errorInfo.severity,
                timestamp: errorInfo.timestamp,
                source: errorInfo.source
            }
        });
        window.dispatchEvent(event);
    }

    /**
     * Get error statistics
     */
    getStats() {
        const severityCounts = this.errors.reduce((acc, err) => {
            acc[err.severity] = (acc[err.severity] || 0) + 1;
            return acc;
        }, {});

        const sourceCounts = this.errors.reduce((acc, err) => {
            acc[err.source] = (acc[err.source] || 0) + 1;
            return acc;
        }, {});

        return {
            totalErrors: this.errors.length,
            severityCounts,
            sourceCounts,
            storageUsage: this.getStorageUsage(),
            rateLimitStatus: {
                currentWindow: Math.floor(Date.now() / this.rateLimitWindow),
                currentCount: this.errorCounts.get(Math.floor(Date.now() / this.rateLimitWindow)) || 0,
                maxPerWindow: this.maxErrorsPerWindow
            }
        };
    }
}

// Export singleton instance
export const secureErrorHandler = new SecureErrorHandler();

// Auto-initialize when module is loaded
if (typeof window !== 'undefined') {
    secureErrorHandler.initialize();
}