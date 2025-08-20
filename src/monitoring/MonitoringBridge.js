/**
 * RTS Monitoring Bridge
 * Integrates all monitoring systems and provides unified interface
 * for Command & Independent Thought performance monitoring
 */

import { rtsProfiler } from "./RTSProfiler.js";
import { rtsDiagnostics } from "./RTSDiagnostics.js";
import { rtsHealthMonitor } from "./RTSHealthMonitor.js";

class MonitoringBridge {
    constructor() {
        this.enabled = true;
        this.wsConnection = null;
        this.monitoringEndpoint = "ws://localhost:8082/ws";
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 5000;
        
        // Integration state
        this.integrationState = {
            profilerConnected: false,
            diagnosticsConnected: false,
            healthMonitorConnected: false,
            externalMonitoringConnected: false
        };
        
        this.initialize();
    }
    
    /**
     * Initialize monitoring bridge
     */
    initialize() {
        if (!this.enabled) return;
        
        console.log("🌉 Initializing RTS Monitoring Bridge");
        
        // Setup global monitoring interface
        this.setupGlobalInterface();
        
        // Connect to monitoring systems
        this.connectToMonitoringSystems();
        
        // Setup WebSocket connection to external monitoring
        this.connectToExternalMonitoring();
        
        // Setup periodic sync
        this.startPeriodicSync();
        
        console.log("🌉 RTS Monitoring Bridge initialized");
    }
    
    /**
     * Setup global monitoring interface
     */
    setupGlobalInterface() {
        if (typeof window !== "undefined") {
            window.RTSMonitoringBridge = {
                // Performance metrics
                updateMetrics: (type, data) => this.updateMetrics(type, data),
                getPerformanceStats: () => this.getPerformanceStats(),
                
                // Logging and diagnostics
                sendLog: (logEntry) => this.sendLog(logEntry),
                sendAlert: (alert) => this.sendAlert(alert),
                
                // Health monitoring
                getHealthStatus: () => this.getHealthStatus(),
                forceHealthCheck: () => this.forceHealthCheck(),
                
                // System control
                setEnabled: (enabled) => this.setEnabled(enabled),
                exportData: () => this.exportAllData(),
                
                // WebSocket management
                reconnectMonitoring: () => this.connectToExternalMonitoring(),
                getConnectionStatus: () => this.getConnectionStatus()
            };
        }
    }
    
    /**
     * Connect to internal monitoring systems
     */
    connectToMonitoringSystems() {
        try {
            // Connect profiler
            if (rtsProfiler) {
                rtsProfiler.connectToMonitoring = (wsUrl) => {
                    this.monitoringEndpoint = wsUrl;
                    this.connectToExternalMonitoring();
                };
                this.integrationState.profilerConnected = true;
                rtsDiagnostics.info("Profiler connected to monitoring bridge");
            }

            // Connect diagnostics
            if (rtsDiagnostics) {
                this.integrationState.diagnosticsConnected = true;
                rtsDiagnostics.info("Diagnostics connected to monitoring bridge");
            }

            // Connect health monitor
            if (rtsHealthMonitor) {
                this.integrationState.healthMonitorConnected = true;
                rtsDiagnostics.info("Health monitor connected to monitoring bridge");
            }

        } catch (error) {
            console.error("Failed to connect to monitoring systems:", error);
        }
    }

    /**
     * Connect to external monitoring WebSocket
     */
    connectToExternalMonitoring() {
        if (!this.enabled) return;

        try {
            // Close existing connection
            if (this.wsConnection) {
                this.wsConnection.close();
            }

            console.log(`🔌 Connecting to external monitoring: ${this.monitoringEndpoint}`);

            this.wsConnection = new WebSocket(this.monitoringEndpoint);

            this.wsConnection.onopen = () => {
                console.log("✅ Connected to external monitoring");
                this.integrationState.externalMonitoringConnected = true;
                this.reconnectAttempts = 0;

                // Send initial state
                this.sendInitialState();
            };

            this.wsConnection.onclose = (event) => {
                console.log("🔌 Disconnected from external monitoring");
                this.integrationState.externalMonitoringConnected = false;

                // Attempt reconnection
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

                    setTimeout(() => {
                        this.connectToExternalMonitoring();
                    }, this.reconnectDelay * this.reconnectAttempts);
                } else {
                    console.error("❌ Maximum reconnection attempts reached");
                }
            };

            this.wsConnection.onerror = (error) => {
                console.error("WebSocket connection error:", error);
            };

            this.wsConnection.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleExternalMessage(message);
                } catch (error) {
                    console.error("Failed to parse monitoring message:", error);
                }
            };

        } catch (error) {
            console.error("Failed to connect to external monitoring:", error);
        }
    }

    /**
     * Send initial state to external monitoring
     */
    sendInitialState() {
        this.sendToExternalMonitoring({
            type: "monitoring_bridge_connected",
            data: {
                integrationState: this.integrationState,
                initialMetrics: this.getPerformanceStats(),
                initialHealth: this.getHealthStatus(),
                timestamp: Date.now()
            }
        });
    }

    /**
     * Handle messages from external monitoring
     */
    handleExternalMessage(message) {
        switch (message.type) {
        case "request_metrics":
            this.sendToExternalMonitoring({
                type: "metrics_response",
                data: this.getPerformanceStats(),
                timestamp: Date.now()
            });
            break;

        case "request_health":
            this.sendToExternalMonitoring({
                type: "health_response",
                data: this.getHealthStatus(),
                timestamp: Date.now()
            });
            break;

        case "force_health_check":
            this.forceHealthCheck();
            break;

        case "set_monitoring_config":
            this.updateMonitoringConfig(message.data);
            break;

        default:
            console.debug("Unknown monitoring message type:", message.type);
        }
    }

    /**
     * Update metrics from monitoring systems
     */
    updateMetrics(type, data) {
        const message = {
            type: `${type}_metrics_update`,
            data,
            timestamp: Date.now()
        };

        this.sendToExternalMonitoring(message);
    }

    /**
     * Get comprehensive performance statistics
     */
    getPerformanceStats() {
        const stats = {
            timestamp: Date.now(),
            profiler: null,
            diagnostics: null,
            health: null
        };

        try {
            if (rtsProfiler && this.integrationState.profilerConnected) {
                stats.profiler = rtsProfiler.getStats();
            }
        } catch (error) {
            console.error("Failed to get profiler stats:", error);
        }

        try {
            if (rtsDiagnostics && this.integrationState.diagnosticsConnected) {
                stats.diagnostics = rtsDiagnostics.getStats();
            }
        } catch (error) {
            console.error("Failed to get diagnostics stats:", error);
        }

        try {
            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {
                stats.health = rtsHealthMonitor.getHealthMetrics();
            }
        } catch (error) {
            console.error("Failed to get health metrics:", error);
        }

        return stats;
    }

    /**
     * Send log entry to external monitoring
     */
    sendLog(logEntry) {
        const message = {
            type: "log_entry",
            data: logEntry,
            timestamp: Date.now()
        };

        this.sendToExternalMonitoring(message);
    }

    /**
     * Send alert to external monitoring
     */
    sendAlert(alert) {
        const message = {
            type: "alert",
            data: alert,
            timestamp: Date.now(),
            priority: alert.severity === "critical" ? "high" : "normal"
        };

        this.sendToExternalMonitoring(message);

        // Also log locally
        console.warn("🚨 Alert forwarded to external monitoring:", alert);
    }

    /**
     * Get current health status
     */
    getHealthStatus() {
        try {
            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {
                return rtsHealthMonitor.getDetailedHealthStatus();
            } else {
                return {
                    status: "unknown",
                    message: "Health monitor not connected"
                };
            }
        } catch (error) {
            console.error("Failed to get health status:", error);
            return {
                status: "error",
                message: "Failed to retrieve health status"
            };
        }
    }

    /**
     * Force health check
     */
    forceHealthCheck() {
        try {
            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {
                return rtsHealthMonitor.forceHealthCheck();
            }
        } catch (error) {
            console.error("Failed to force health check:", error);
        }
    }

    /**
     * Update monitoring configuration
     */
    updateMonitoringConfig(config) {
        try {
            if (config.profiler && rtsProfiler) {
                if (config.profiler.enabled !== undefined) {
                    rtsProfiler.setEnabled(config.profiler.enabled);
                }
            }

            if (config.diagnostics && rtsDiagnostics) {
                if (config.diagnostics.logLevel) {
                    rtsDiagnostics.setLogLevel(config.diagnostics.logLevel);
                }
                if (config.diagnostics.enabled !== undefined) {
                    rtsDiagnostics.setEnabled(config.diagnostics.enabled);
                }
            }

            if (config.healthMonitor && rtsHealthMonitor) {
                if (config.healthMonitor.checkInterval) {
                    rtsHealthMonitor.setCheckInterval(config.healthMonitor.checkInterval);
                }
                if (config.healthMonitor.enabled !== undefined) {
                    rtsHealthMonitor.setEnabled(config.healthMonitor.enabled);
                }
            }

            console.log("📝 Monitoring configuration updated:", config);

        } catch (error) {
            console.error("Failed to update monitoring configuration:", error);
        }
    }

    /**
     * Send message to external monitoring
     */
    sendToExternalMonitoring(message) {
        if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
            try {
                this.wsConnection.send(JSON.stringify(message));
            } catch (error) {
                console.error("Failed to send message to external monitoring:", error);
            }
        }
    }

    /**
     * Start periodic sync with external monitoring
     */
    startPeriodicSync() {
        setInterval(() => {
            if (this.integrationState.externalMonitoringConnected) {
                // Send periodic metrics update
                this.sendToExternalMonitoring({
                    type: "periodic_sync",
                    data: {
                        metrics: this.getPerformanceStats(),
                        health: this.getHealthStatus(),
                        integrationState: this.integrationState
                    },
                    timestamp: Date.now()
                });
            }
        }, 60000); // Every minute
    }

    /**
     * Export all monitoring data
     */
    exportAllData() {
        const exportData = {
            metadata: {
                exportTime: new Date().toISOString(),
                monitoringBridge: "1.0.0"
            },
            integrationState: this.integrationState,
            performanceStats: this.getPerformanceStats(),
            healthStatus: this.getHealthStatus()
        };

        // Add individual system reports if available
        try {
            if (rtsProfiler && this.integrationState.profilerConnected) {
                exportData.profilerReport = rtsProfiler.generateReport();
            }
        } catch (error) {
            exportData.profilerError = error.message;
        }

        try {
            if (rtsDiagnostics && this.integrationState.diagnosticsConnected) {
                exportData.diagnosticsReport = rtsDiagnostics.generateDiagnosticReport();
            }
        } catch (error) {
            exportData.diagnosticsError = error.message;
        }

        // Create downloadable file
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = `rts-monitoring-export-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log("📊 Complete monitoring data exported");

        return exportData;
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            bridge: this.enabled,
            integrationState: this.integrationState,
            externalMonitoring: {
                connected: this.integrationState.externalMonitoringConnected,
                endpoint: this.monitoringEndpoint,
                reconnectAttempts: this.reconnectAttempts,
                wsReadyState: this.wsConnection ? this.wsConnection.readyState : null
            }
        };
    }

    /**
     * Enable or disable monitoring bridge
     */
    setEnabled(enabled) {
        this.enabled = enabled;

        if (enabled) {
            this.connectToExternalMonitoring();
        } else {
            if (this.wsConnection) {
                this.wsConnection.close();
            }
        }

        console.log(`🌉 Monitoring Bridge ${enabled ? "enabled" : "disabled"}`);
    }

    /**
     * Cleanup and disconnect
     */
    disconnect() {
        this.setEnabled(false);

        // Cleanup global interface
        if (typeof window !== "undefined" && window.RTSMonitoringBridge) {
            delete window.RTSMonitoringBridge;
        }

        console.log("🌉 Monitoring Bridge disconnected");
    }
}

// Global monitoring bridge instance
export const monitoringBridge = new MonitoringBridge();
