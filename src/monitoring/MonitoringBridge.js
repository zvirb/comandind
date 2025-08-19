/**
 * RTS Monitoring Bridge
 * Integrates all monitoring systems and provides unified interface
 * for Command & Independent Thought performance monitoring
 */

import { rtsProfiler } from './RTSProfiler.js';
import { rtsDiagnostics } from './RTSDiagnostics.js';
import { rtsHealthMonitor } from './RTSHealthMonitor.js';

class MonitoringBridge {
    constructor() {
        this.enabled = true;
        this.wsConnection = null;
        this.monitoringEndpoint = 'ws://localhost:8082/ws';
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
        
        console.log('🌉 Initializing RTS Monitoring Bridge');
        
        // Setup global monitoring interface
        this.setupGlobalInterface();
        
        // Connect to monitoring systems
        this.connectToMonitoringSystems();
        
        // Setup WebSocket connection to external monitoring
        this.connectToExternalMonitoring();
        
        // Setup periodic sync
        this.startPeriodicSync();
        
        console.log('🌉 RTS Monitoring Bridge initialized');
    }
    
    /**
     * Setup global monitoring interface
     */
    setupGlobalInterface() {
        if (typeof window !== 'undefined') {
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
        try {\n            // Connect profiler\n            if (rtsProfiler) {\n                rtsProfiler.connectToMonitoring = (wsUrl) => {\n                    this.monitoringEndpoint = wsUrl;\n                    this.connectToExternalMonitoring();\n                };\n                this.integrationState.profilerConnected = true;\n                rtsDiagnostics.info('Profiler connected to monitoring bridge');\n            }\n            \n            // Connect diagnostics\n            if (rtsDiagnostics) {\n                this.integrationState.diagnosticsConnected = true;\n                rtsDiagnostics.info('Diagnostics connected to monitoring bridge');\n            }\n            \n            // Connect health monitor\n            if (rtsHealthMonitor) {\n                this.integrationState.healthMonitorConnected = true;\n                rtsDiagnostics.info('Health monitor connected to monitoring bridge');\n            }\n            \n        } catch (error) {\n            console.error('Failed to connect to monitoring systems:', error);\n        }\n    }\n    \n    /**\n     * Connect to external monitoring WebSocket\n     */\n    connectToExternalMonitoring() {\n        if (!this.enabled) return;\n        \n        try {\n            // Close existing connection\n            if (this.wsConnection) {\n                this.wsConnection.close();\n            }\n            \n            console.log(`🔌 Connecting to external monitoring: ${this.monitoringEndpoint}`);\n            \n            this.wsConnection = new WebSocket(this.monitoringEndpoint);\n            \n            this.wsConnection.onopen = () => {\n                console.log('✅ Connected to external monitoring');\n                this.integrationState.externalMonitoringConnected = true;\n                this.reconnectAttempts = 0;\n                \n                // Send initial state\n                this.sendInitialState();\n            };\n            \n            this.wsConnection.onclose = (event) => {\n                console.log('🔌 Disconnected from external monitoring');\n                this.integrationState.externalMonitoringConnected = false;\n                \n                // Attempt reconnection\n                if (this.reconnectAttempts < this.maxReconnectAttempts) {\n                    this.reconnectAttempts++;\n                    console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);\n                    \n                    setTimeout(() => {\n                        this.connectToExternalMonitoring();\n                    }, this.reconnectDelay * this.reconnectAttempts);\n                } else {\n                    console.error('❌ Maximum reconnection attempts reached');\n                }\n            };\n            \n            this.wsConnection.onerror = (error) => {\n                console.error('WebSocket connection error:', error);\n            };\n            \n            this.wsConnection.onmessage = (event) => {\n                try {\n                    const message = JSON.parse(event.data);\n                    this.handleExternalMessage(message);\n                } catch (error) {\n                    console.error('Failed to parse monitoring message:', error);\n                }\n            };\n            \n        } catch (error) {\n            console.error('Failed to connect to external monitoring:', error);\n        }\n    }\n    \n    /**\n     * Send initial state to external monitoring\n     */\n    sendInitialState() {\n        this.sendToExternalMonitoring({\n            type: 'monitoring_bridge_connected',\n            data: {\n                integrationState: this.integrationState,\n                initialMetrics: this.getPerformanceStats(),\n                initialHealth: this.getHealthStatus(),\n                timestamp: Date.now()\n            }\n        });\n    }\n    \n    /**\n     * Handle messages from external monitoring\n     */\n    handleExternalMessage(message) {\n        switch (message.type) {\n            case 'request_metrics':\n                this.sendToExternalMonitoring({\n                    type: 'metrics_response',\n                    data: this.getPerformanceStats(),\n                    timestamp: Date.now()\n                });\n                break;\n                \n            case 'request_health':\n                this.sendToExternalMonitoring({\n                    type: 'health_response',\n                    data: this.getHealthStatus(),\n                    timestamp: Date.now()\n                });\n                break;\n                \n            case 'force_health_check':\n                this.forceHealthCheck();\n                break;\n                \n            case 'set_monitoring_config':\n                this.updateMonitoringConfig(message.data);\n                break;\n                \n            default:\n                console.debug('Unknown monitoring message type:', message.type);\n        }\n    }\n    \n    /**\n     * Update metrics from monitoring systems\n     */\n    updateMetrics(type, data) {\n        const message = {\n            type: `${type}_metrics_update`,\n            data,\n            timestamp: Date.now()\n        };\n        \n        this.sendToExternalMonitoring(message);\n    }\n    \n    /**\n     * Get comprehensive performance statistics\n     */\n    getPerformanceStats() {\n        const stats = {\n            timestamp: Date.now(),\n            profiler: null,\n            diagnostics: null,\n            health: null\n        };\n        \n        try {\n            if (rtsProfiler && this.integrationState.profilerConnected) {\n                stats.profiler = rtsProfiler.getStats();\n            }\n        } catch (error) {\n            console.error('Failed to get profiler stats:', error);\n        }\n        \n        try {\n            if (rtsDiagnostics && this.integrationState.diagnosticsConnected) {\n                stats.diagnostics = rtsDiagnostics.getStats();\n            }\n        } catch (error) {\n            console.error('Failed to get diagnostics stats:', error);\n        }\n        \n        try {\n            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {\n                stats.health = rtsHealthMonitor.getHealthMetrics();\n            }\n        } catch (error) {\n            console.error('Failed to get health metrics:', error);\n        }\n        \n        return stats;\n    }\n    \n    /**\n     * Send log entry to external monitoring\n     */\n    sendLog(logEntry) {\n        const message = {\n            type: 'log_entry',\n            data: logEntry,\n            timestamp: Date.now()\n        };\n        \n        this.sendToExternalMonitoring(message);\n    }\n    \n    /**\n     * Send alert to external monitoring\n     */\n    sendAlert(alert) {\n        const message = {\n            type: 'alert',\n            data: alert,\n            timestamp: Date.now(),\n            priority: alert.severity === 'critical' ? 'high' : 'normal'\n        };\n        \n        this.sendToExternalMonitoring(message);\n        \n        // Also log locally\n        console.warn('🚨 Alert forwarded to external monitoring:', alert);\n    }\n    \n    /**\n     * Get current health status\n     */\n    getHealthStatus() {\n        try {\n            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {\n                return rtsHealthMonitor.getDetailedHealthStatus();\n            } else {\n                return {\n                    status: 'unknown',\n                    message: 'Health monitor not connected'\n                };\n            }\n        } catch (error) {\n            console.error('Failed to get health status:', error);\n            return {\n                status: 'error',\n                message: 'Failed to retrieve health status'\n            };\n        }\n    }\n    \n    /**\n     * Force health check\n     */\n    forceHealthCheck() {\n        try {\n            if (rtsHealthMonitor && this.integrationState.healthMonitorConnected) {\n                return rtsHealthMonitor.forceHealthCheck();\n            }\n        } catch (error) {\n            console.error('Failed to force health check:', error);\n        }\n    }\n    \n    /**\n     * Update monitoring configuration\n     */\n    updateMonitoringConfig(config) {\n        try {\n            if (config.profiler && rtsProfiler) {\n                if (config.profiler.enabled !== undefined) {\n                    rtsProfiler.setEnabled(config.profiler.enabled);\n                }\n            }\n            \n            if (config.diagnostics && rtsDiagnostics) {\n                if (config.diagnostics.logLevel) {\n                    rtsDiagnostics.setLogLevel(config.diagnostics.logLevel);\n                }\n                if (config.diagnostics.enabled !== undefined) {\n                    rtsDiagnostics.setEnabled(config.diagnostics.enabled);\n                }\n            }\n            \n            if (config.healthMonitor && rtsHealthMonitor) {\n                if (config.healthMonitor.checkInterval) {\n                    rtsHealthMonitor.setCheckInterval(config.healthMonitor.checkInterval);\n                }\n                if (config.healthMonitor.enabled !== undefined) {\n                    rtsHealthMonitor.setEnabled(config.healthMonitor.enabled);\n                }\n            }\n            \n            console.log('📝 Monitoring configuration updated:', config);\n            \n        } catch (error) {\n            console.error('Failed to update monitoring configuration:', error);\n        }\n    }\n    \n    /**\n     * Send message to external monitoring\n     */\n    sendToExternalMonitoring(message) {\n        if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {\n            try {\n                this.wsConnection.send(JSON.stringify(message));\n            } catch (error) {\n                console.error('Failed to send message to external monitoring:', error);\n            }\n        }\n    }\n    \n    /**\n     * Start periodic sync with external monitoring\n     */\n    startPeriodicSync() {\n        setInterval(() => {\n            if (this.integrationState.externalMonitoringConnected) {\n                // Send periodic metrics update\n                this.sendToExternalMonitoring({\n                    type: 'periodic_sync',\n                    data: {\n                        metrics: this.getPerformanceStats(),\n                        health: this.getHealthStatus(),\n                        integrationState: this.integrationState\n                    },\n                    timestamp: Date.now()\n                });\n            }\n        }, 60000); // Every minute\n    }\n    \n    /**\n     * Export all monitoring data\n     */\n    exportAllData() {\n        const exportData = {\n            metadata: {\n                exportTime: new Date().toISOString(),\n                monitoringBridge: '1.0.0'\n            },\n            integrationState: this.integrationState,\n            performanceStats: this.getPerformanceStats(),\n            healthStatus: this.getHealthStatus()\n        };\n        \n        // Add individual system reports if available\n        try {\n            if (rtsProfiler && this.integrationState.profilerConnected) {\n                exportData.profilerReport = rtsProfiler.generateReport();\n            }\n        } catch (error) {\n            exportData.profilerError = error.message;\n        }\n        \n        try {\n            if (rtsDiagnostics && this.integrationState.diagnosticsConnected) {\n                exportData.diagnosticsReport = rtsDiagnostics.generateDiagnosticReport();\n            }\n        } catch (error) {\n            exportData.diagnosticsError = error.message;\n        }\n        \n        // Create downloadable file\n        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });\n        const url = URL.createObjectURL(blob);\n        \n        const a = document.createElement('a');\n        a.href = url;\n        a.download = `rts-monitoring-export-${Date.now()}.json`;\n        document.body.appendChild(a);\n        a.click();\n        document.body.removeChild(a);\n        URL.revokeObjectURL(url);\n        \n        console.log('📊 Complete monitoring data exported');\n        \n        return exportData;\n    }\n    \n    /**\n     * Get connection status\n     */\n    getConnectionStatus() {\n        return {\n            bridge: this.enabled,\n            integrationState: this.integrationState,\n            externalMonitoring: {\n                connected: this.integrationState.externalMonitoringConnected,\n                endpoint: this.monitoringEndpoint,\n                reconnectAttempts: this.reconnectAttempts,\n                wsReadyState: this.wsConnection ? this.wsConnection.readyState : null\n            }\n        };\n    }\n    \n    /**\n     * Enable or disable monitoring bridge\n     */\n    setEnabled(enabled) {\n        this.enabled = enabled;\n        \n        if (enabled) {\n            this.connectToExternalMonitoring();\n        } else {\n            if (this.wsConnection) {\n                this.wsConnection.close();\n            }\n        }\n        \n        console.log(`🌉 Monitoring Bridge ${enabled ? 'enabled' : 'disabled'}`);\n    }\n    \n    /**\n     * Cleanup and disconnect\n     */\n    disconnect() {\n        this.setEnabled(false);\n        \n        // Cleanup global interface\n        if (typeof window !== 'undefined' && window.RTSMonitoringBridge) {\n            delete window.RTSMonitoringBridge;\n        }\n        \n        console.log('🌉 Monitoring Bridge disconnected');\n    }\n}\n\n// Global monitoring bridge instance\nexport const monitoringBridge = new MonitoringBridge();