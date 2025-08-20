/**
 * RTS Diagnostics and Logging System
 * Comprehensive logging, error tracking, and diagnostic tools for Command & Independent Thought
 */

export class RTSDiagnostics {
    constructor() {
        this.enabled = true;
        this.logLevel = "info"; // debug, info, warn, error
        this.maxLogs = 1000;
        this.startTime = performance.now();
        
        // Log storage
        this.logs = [];
        this.errors = [];
        this.gameplayEvents = [];
        this.performanceEvents = [];
        
        // Diagnostic state
        this.diagnosticData = {
            browserInfo: this.getBrowserInfo(),
            systemInfo: this.getSystemInfo(),
            gameState: {},
            lastError: null,
            errorCount: 0,
            warningCount: 0,
            fatalErrors: []
        };
        
        // Event listeners for error tracking
        this.setupErrorHandling();
        
        console.log("📊 RTS Diagnostics System initialized");
    }
    
    /**
     * Get browser information
     */
    getBrowserInfo() {
        const navigator = window.navigator;
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine,
            hardwareConcurrency: navigator.hardwareConcurrency,
            memory: performance.memory ? {
                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
                totalJSHeapSize: performance.memory.totalJSHeapSize,
                usedJSHeapSize: performance.memory.usedJSHeapSize
            } : null
        };
    }
    
    /**
     * Get system information
     */
    getSystemInfo() {
        return {
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            },
            window: {
                innerWidth: window.innerWidth,
                innerHeight: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio
            },
            performance: {
                timeOrigin: performance.timeOrigin,
                timing: performance.timing ? {
                    navigationStart: performance.timing.navigationStart,
                    loadEventEnd: performance.timing.loadEventEnd,
                    domContentLoadedEventEnd: performance.timing.domContentLoadedEventEnd
                } : null
            }
        };
    }
    
    /**
     * Setup error handling
     */
    setupErrorHandling() {
        // Global error handler
        window.addEventListener("error", (event) => {
            this.logError("JavaScript Error", {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error ? event.error.stack : null
            });
        });
        
        // Unhandled promise rejection handler
        window.addEventListener("unhandledrejection", (event) => {
            this.logError("Unhandled Promise Rejection", {
                reason: event.reason,
                promise: event.promise,
                stack: event.reason && event.reason.stack ? event.reason.stack : null
            });
        });
        
        // Resource loading errors
        window.addEventListener("error", (event) => {
            if (event.target !== window) {
                this.logError("Resource Loading Error", {
                    element: event.target.tagName,
                    source: event.target.src || event.target.href,
                    message: "Failed to load resource"
                });
            }
        }, true);
    }
    
    /**
     * Log debug message
     */
    debug(message, data = {}) {
        this.log("debug", message, data);
    }
    
    /**
     * Log info message
     */
    info(message, data = {}) {
        this.log("info", message, data);
    }
    
    /**
     * Log warning message
     */
    warn(message, data = {}) {
        this.log("warn", message, data);
        this.diagnosticData.warningCount++;
    }
    
    /**
     * Log error message
     */
    error(message, data = {}) {
        this.log("error", message, data);
        this.logError(message, data);
    }
    
    /**
     * Log fatal error
     */
    fatal(message, data = {}) {
        this.log("fatal", message, data);
        this.diagnosticData.fatalErrors.push({
            timestamp: Date.now(),
            message,
            data,
            uptime: this.getUptime()
        });
        
        // Send fatal error to monitoring system immediately
        this.sendCriticalAlert("FATAL_ERROR", message, data);
    }
    
    /**
     * Generic log method
     */
    log(level, message, data = {}) {
        if (!this.enabled || !this.shouldLog(level)) {
            return;
        }
        
        const logEntry = {
            id: Date.now() + Math.random(),
            timestamp: Date.now(),
            level,
            message,
            data,
            uptime: this.getUptime(),
            stack: level === "error" || level === "fatal" ? this.getCallStack() : null
        };
        
        // Add to logs array
        this.logs.unshift(logEntry);
        
        // Keep logs within limit
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(0, this.maxLogs);
        }
        
        // Console output
        this.outputToConsole(logEntry);
        
        // Send to external monitoring if configured
        this.sendToExternalMonitoring(logEntry);
    }
    
    /**
     * Log error with additional tracking
     */
    logError(message, data = {}) {
        this.diagnosticData.errorCount++;
        this.diagnosticData.lastError = {
            timestamp: Date.now(),
            message,
            data,
            stack: this.getCallStack()
        };
        
        const errorEntry = {
            id: Date.now() + Math.random(),
            timestamp: Date.now(),
            message,
            data,
            stack: this.getCallStack(),
            gameState: this.captureGameState(),
            browserInfo: this.getBrowserInfo(),
            uptime: this.getUptime()
        };
        
        this.errors.unshift(errorEntry);
        
        // Keep errors within limit
        if (this.errors.length > 100) {
            this.errors = this.errors.slice(0, 100);
        }
    }
    
    /**
     * Log gameplay event
     */
    logGameplayEvent(eventType, eventData = {}) {
        if (!this.enabled) return;
        
        const event = {
            id: Date.now() + Math.random(),
            timestamp: Date.now(),
            type: eventType,
            data: eventData,
            uptime: this.getUptime(),
            gameState: this.captureGameState()
        };
        
        this.gameplayEvents.unshift(event);
        
        // Keep events within limit
        if (this.gameplayEvents.length > 500) {
            this.gameplayEvents = this.gameplayEvents.slice(0, 500);
        }
        
        // Log significant gameplay events
        if (this.isSignificantEvent(eventType)) {
            this.info(`Gameplay Event: ${eventType}`, eventData);
        }
    }
    
    /**
     * Log performance event
     */
    logPerformanceEvent(eventType, metrics = {}) {
        if (!this.enabled) return;
        
        const event = {
            id: Date.now() + Math.random(),
            timestamp: Date.now(),
            type: eventType,
            metrics,
            uptime: this.getUptime()
        };
        
        this.performanceEvents.unshift(event);
        
        // Keep events within limit
        if (this.performanceEvents.length > 300) {
            this.performanceEvents = this.performanceEvents.slice(0, 300);
        }
        
        // Log performance issues
        if (this.isPerformanceIssue(eventType, metrics)) {
            this.warn(`Performance Issue: ${eventType}`, metrics);
        }
    }
    
    /**
     * Capture current game state for diagnostics
     */
    captureGameState() {
        try {
            // This would be customized based on your game's state management
            return {
                entityCount: window.gameWorld ? window.gameWorld.getStats().entityCount : 0,
                selectedEntities: window.selectionSystem ? window.selectionSystem.getSelectedCount() : 0,
                activePathfinding: window.pathfindingSystem ? window.pathfindingSystem.getActiveCount() : 0,
                gameTime: window.gameLoop ? window.gameLoop.getElapsedTime() : 0,
                paused: window.gameLoop ? window.gameLoop.isPaused() : false,
                loading: window.gameState ? window.gameState.isLoading : false
            };
        } catch (error) {
            return { error: "Failed to capture game state" };
        }
    }
    
    /**
     * Check if event is significant for logging
     */
    isSignificantEvent(eventType) {
        const significantEvents = [
            "unit_created",
            "building_constructed",
            "unit_destroyed",
            "building_destroyed",
            "resource_depleted",
            "player_defeated",
            "game_won",
            "game_lost",
            "connection_lost",
            "critical_error"
        ];
        
        return significantEvents.includes(eventType);
    }
    
    /**
     * Check if performance event indicates an issue
     */
    isPerformanceIssue(eventType, metrics) {
        const performanceThresholds = {
            fps_drop: (metrics) => metrics.fps && metrics.fps < 30,
            frame_time_spike: (metrics) => metrics.frameTime && metrics.frameTime > 50,
            memory_spike: (metrics) => metrics.memoryUsage && metrics.memoryUsage > 250,
            pathfinding_slow: (metrics) => metrics.pathfindingTime && metrics.pathfindingTime > 10,
            selection_slow: (metrics) => metrics.selectionTime && metrics.selectionTime > 30
        };
        
        const checker = performanceThresholds[eventType];
        return checker ? checker(metrics) : false;
    }
    
    /**
     * Get current uptime
     */
    getUptime() {
        return (performance.now() - this.startTime) / 1000;
    }
    
    /**
     * Get call stack
     */
    getCallStack() {
        try {
            throw new Error();
        } catch (e) {
            return e.stack;
        }
    }
    
    /**
     * Check if should log based on level
     */
    shouldLog(level) {
        const levels = ["debug", "info", "warn", "error", "fatal"];
        const currentLevelIndex = levels.indexOf(this.logLevel);
        const messageLevelIndex = levels.indexOf(level);
        
        return messageLevelIndex >= currentLevelIndex;
    }
    
    /**
     * Output log to console
     */
    outputToConsole(logEntry) {
        const { level, message, data, timestamp } = logEntry;
        const timeStr = new Date(timestamp).toISOString();
        
        const logMessage = `[${timeStr}] [${level.toUpperCase()}] ${message}`;
        
        switch (level) {
        case "debug":
            console.debug(logMessage, data);
            break;
        case "info":
            console.info(logMessage, data);
            break;
        case "warn":
            console.warn(logMessage, data);
            break;
        case "error":
        case "fatal":
            console.error(logMessage, data);
            break;
        default:
            console.log(logMessage, data);
        }
    }
    
    /**
     * Send log to external monitoring system
     */
    sendToExternalMonitoring(logEntry) {
        // Implementation would depend on your monitoring service
        if (window.RTSMonitoringBridge) {
            window.RTSMonitoringBridge.sendLog(logEntry);
        }
    }
    
    /**
     * Send critical alert
     */
    sendCriticalAlert(type, message, data) {
        console.error(`🚨 CRITICAL ALERT [${type}]: ${message}`, data);
        
        // Send to external monitoring
        if (window.RTSMonitoringBridge) {
            window.RTSMonitoringBridge.sendAlert({
                type,
                message,
                data,
                timestamp: Date.now(),
                severity: "critical"
            });
        }
    }
    
    /**
     * Generate diagnostic report
     */
    generateDiagnosticReport() {
        return {
            timestamp: new Date().toISOString(),
            uptime: this.getUptime(),
            diagnosticData: this.diagnosticData,
            recentLogs: this.logs.slice(0, 50),
            recentErrors: this.errors.slice(0, 20),
            recentGameplayEvents: this.gameplayEvents.slice(0, 30),
            recentPerformanceEvents: this.performanceEvents.slice(0, 20),
            systemHealth: this.getSystemHealth(),
            recommendations: this.getRecommendations()
        };
    }
    
    /**
     * Get system health assessment
     */
    getSystemHealth() {
        const errorRate = this.diagnosticData.errorCount / (this.getUptime() / 60); // errors per minute
        const hasRecentFatal = this.diagnosticData.fatalErrors.some(
            error => Date.now() - error.timestamp < 300000 // 5 minutes
        );
        
        let status = "healthy";
        let issues = [];
        
        if (hasRecentFatal) {
            status = "critical";
            issues.push("Recent fatal errors detected");
        } else if (errorRate > 1) {
            status = "degraded";
            issues.push(`High error rate: ${errorRate.toFixed(2)} errors/minute`);
        } else if (this.diagnosticData.warningCount > 10) {
            status = "warning";
            issues.push("Multiple warnings detected");
        }
        
        return {
            status,
            issues,
            errorRate,
            warningCount: this.diagnosticData.warningCount,
            fatalErrorCount: this.diagnosticData.fatalErrors.length
        };
    }
    
    /**
     * Get recommendations based on diagnostic data
     */
    getRecommendations() {
        const recommendations = [];
        const health = this.getSystemHealth();
        
        if (health.errorRate > 0.5) {
            recommendations.push({
                type: "stability",
                priority: "high",
                message: "High error rate detected. Review recent errors and implement fixes."
            });
        }
        
        if (this.diagnosticData.fatalErrors.length > 0) {
            recommendations.push({
                type: "critical",
                priority: "critical",
                message: "Fatal errors detected. Investigate and resolve immediately."
            });
        }
        
        const recentPerformanceIssues = this.performanceEvents.filter(
            event => Date.now() - event.timestamp < 300000 // 5 minutes
        ).length;
        
        if (recentPerformanceIssues > 5) {
            recommendations.push({
                type: "performance",
                priority: "medium",
                message: "Multiple performance issues detected. Consider optimization."
            });
        }
        
        return recommendations;
    }
    
    /**
     * Export diagnostic data
     */
    exportDiagnosticData() {
        const data = {
            metadata: {
                exportTime: new Date().toISOString(),
                uptime: this.getUptime(),
                version: "1.0.0"
            },
            diagnostics: this.generateDiagnosticReport()
        };
        
        // Create downloadable file
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement("a");
        a.href = url;
        a.download = `rts-diagnostics-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log("📊 Diagnostic data exported");
    }
    
    /**
     * Clear all diagnostic data
     */
    clearDiagnostics() {
        this.logs = [];
        this.errors = [];
        this.gameplayEvents = [];
        this.performanceEvents = [];
        this.diagnosticData.errorCount = 0;
        this.diagnosticData.warningCount = 0;
        this.diagnosticData.fatalErrors = [];
        this.diagnosticData.lastError = null;
        
        console.log("📊 Diagnostic data cleared");
    }
    
    /**
     * Set log level
     */
    setLogLevel(level) {
        const validLevels = ["debug", "info", "warn", "error", "fatal"];
        if (validLevels.includes(level)) {
            this.logLevel = level;
            console.log(`📊 Log level set to: ${level}`);
        } else {
            console.error("📊 Invalid log level:", level);
        }
    }
    
    /**
     * Enable or disable diagnostics
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`📊 RTS Diagnostics ${enabled ? "enabled" : "disabled"}`);
    }
    
    /**
     * Get diagnostic statistics
     */
    getStats() {
        return {
            uptime: this.getUptime(),
            logCount: this.logs.length,
            errorCount: this.errors.length,
            gameplayEventCount: this.gameplayEvents.length,
            performanceEventCount: this.performanceEvents.length,
            health: this.getSystemHealth(),
            memoryUsage: this.diagnosticData.browserInfo.memory
        };
    }
}

// Global diagnostics instance
export const rtsDiagnostics = new RTSDiagnostics();