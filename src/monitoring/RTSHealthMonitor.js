/**
 * RTS Health Monitor
 * Production-ready health monitoring for Command & Independent Thought
 * Validates gameplay systems, performance, and overall application health
 */

import { rtsDiagnostics } from './RTSDiagnostics.js';
import { rtsProfiler } from './RTSProfiler.js';

export class RTSHealthMonitor {
    constructor() {
        this.enabled = true;
        this.checkInterval = 30000; // 30 seconds
        this.healthCheckId = null;
        this.startTime = Date.now();
        
        // Health check configuration
        this.healthChecks = new Map([
            ['system', { enabled: true, weight: 0.3, lastCheck: null, status: 'unknown' }],
            ['performance', { enabled: true, weight: 0.25, lastCheck: null, status: 'unknown' }],
            ['gameplay', { enabled: true, weight: 0.25, lastCheck: null, status: 'unknown' }],
            ['resources', { enabled: true, weight: 0.1, lastCheck: null, status: 'unknown' }],
            ['network', { enabled: true, weight: 0.1, lastCheck: null, status: 'unknown' }]
        ]);
        
        // Health targets
        this.targets = {
            fps: { min: 45, target: 60, critical: 30 },
            frameTime: { max: 22, target: 16.67, critical: 50 },
            memory: { max: 200, critical: 300 }, // MB
            entities: { max: 200, critical: 500 },
            pathfindingTime: { max: 5, critical: 15 }, // ms
            selectionTime: { max: 16, critical: 50 }, // ms
            errorRate: { max: 0.1, critical: 1.0 }, // errors per minute
            responseTime: { max: 100, critical: 1000 } // ms
        };
        
        // Health status
        this.overallHealth = {
            status: 'unknown', // healthy, warning, critical, unknown
            score: 0,
            lastUpdate: null,
            issues: [],
            recommendations: []
        };
        
        // Historical health data
        this.healthHistory = [];
        this.maxHistorySize = 288; // 24 hours at 5-minute intervals
        
        // Alert system
        this.alerts = {
            active: new Map(),
            history: [],
            maxHistory: 100,
            cooldownPeriod: 300000 // 5 minutes
        };
        
        this.startHealthMonitoring();
        this.setupProductionValidation();
        
        console.log('🏥 RTS Health Monitor initialized');
    }
    
    /**
     * Start health monitoring
     */
    startHealthMonitoring() {
        if (this.healthCheckId) {
            clearInterval(this.healthCheckId);
        }
        
        // Initial health check
        setTimeout(() => this.performHealthCheck(), 5000);
        
        // Regular health checks
        this.healthCheckId = setInterval(() => {
            this.performHealthCheck();
        }, this.checkInterval);
        
        console.log(`🏥 Health monitoring started (interval: ${this.checkInterval / 1000}s)`);
    }
    
    /**
     * Setup production validation endpoints
     */
    setupProductionValidation() {
        // Add health endpoints to window for external access
        if (typeof window !== 'undefined') {
            window.RTSHealthAPI = {
                getHealth: () => this.getHealthStatus(),
                getDetailedHealth: () => this.getDetailedHealthStatus(),
                performCheck: () => this.performHealthCheck(),
                getMetrics: () => this.getHealthMetrics(),
                getAlerts: () => this.getActiveAlerts()
            };
            
            // Setup WebSocket endpoint if available
            this.setupWebSocketHealth();
        }
    }
    
    /**
     * Setup WebSocket health monitoring
     */
    setupWebSocketHealth() {
        if (window.WebSocket && window.gameWebSocket) {
            window.gameWebSocket.addEventListener('message', (event) => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'health_request') {
                        window.gameWebSocket.send(JSON.stringify({
                            type: 'health_response',
                            data: this.getHealthStatus(),
                            timestamp: Date.now()
                        }));
                    }
                } catch (error) {
                    // Ignore malformed messages
                }
            });
        }
    }
    
    /**
     * Perform comprehensive health check
     */
    async performHealthCheck() {
        if (!this.enabled) return;
        
        const checkStart = performance.now();
        const results = new Map();
        
        try {
            // Run all health checks in parallel
            const checkPromises = [];
            
            for (const [checkType, config] of this.healthChecks) {
                if (config.enabled) {
                    checkPromises.push(
                        this.runHealthCheck(checkType).then(result => {
                            results.set(checkType, result);
                            config.lastCheck = Date.now();
                            config.status = result.status;
                        }).catch(error => {
                            results.set(checkType, {
                                status: 'critical',
                                message: `Health check failed: ${error.message}`,
                                error: error.message
                            });
                            config.status = 'critical';
                        })
                    );
                }
            }
            
            await Promise.all(checkPromises);
            
            // Calculate overall health
            this.calculateOverallHealth(results);
            
            // Update health history
            this.updateHealthHistory();
            
            // Process alerts
            this.processHealthAlerts(results);
            
            const checkDuration = performance.now() - checkStart;
            rtsDiagnostics.debug('Health check completed', {
                duration: checkDuration,
                status: this.overallHealth.status,
                score: this.overallHealth.score
            });
            
        } catch (error) {
            rtsDiagnostics.error('Health check system error', { error: error.message });
            this.overallHealth.status = 'critical';
            this.overallHealth.issues.push('Health check system failure');
        }
    }
    
    /**
     * Run individual health check
     */
    async runHealthCheck(checkType) {
        switch (checkType) {
            case 'system':
                return this.checkSystemHealth();
            case 'performance':
                return this.checkPerformanceHealth();
            case 'gameplay':
                return this.checkGameplayHealth();
            case 'resources':
                return this.checkResourceHealth();
            case 'network':
                return this.checkNetworkHealth();
            default:
                throw new Error(`Unknown health check type: ${checkType}`);
        }
    }
    
    /**
     * Check system health
     */
    checkSystemHealth() {
        const issues = [];
        let score = 100;
        
        // Check browser compatibility
        if (!window.WebGL2RenderingContext) {
            issues.push('WebGL2 not supported');
            score -= 30;
        }
        
        // Check required APIs
        const requiredAPIs = ['requestAnimationFrame', 'performance', 'fetch'];
        for (const api of requiredAPIs) {
            if (!(api in window)) {
                issues.push(`Missing API: ${api}`);
                score -= 20;
            }
        }
        
        // Check memory availability
        if (performance.memory) {
            const memoryUsage = performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit;
            if (memoryUsage > 0.9) {
                issues.push('Memory usage critical');
                score -= 40;
            } else if (memoryUsage > 0.7) {
                issues.push('Memory usage high');
                score -= 20;
            }
        }
        
        // Check error rate
        const diagnosticStats = rtsDiagnostics.getStats();
        const errorRate = diagnosticStats.errorCount / (diagnosticStats.uptime / 60);
        if (errorRate > this.targets.errorRate.critical) {
            issues.push(`Critical error rate: ${errorRate.toFixed(2)}/min`);
            score -= 50;
        } else if (errorRate > this.targets.errorRate.max) {
            issues.push(`High error rate: ${errorRate.toFixed(2)}/min`);
            score -= 25;
        }
        
        return {
            status: score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical',
            score: Math.max(0, score),
            issues,
            metrics: {
                memoryUsage: performance.memory ? (performance.memory.usedJSHeapSize / 1048576) : 0,
                errorRate,
                uptime: diagnosticStats.uptime
            }
        };
    }
    
    /**
     * Check performance health
     */
    checkPerformanceHealth() {
        const issues = [];
        let score = 100;
        
        const profilerStats = rtsProfiler.getStats();
        
        // Check FPS
        if (profilerStats.fps < this.targets.fps.critical) {
            issues.push(`Critical FPS: ${profilerStats.fps.toFixed(1)}`);
            score -= 50;
        } else if (profilerStats.fps < this.targets.fps.min) {
            issues.push(`Low FPS: ${profilerStats.fps.toFixed(1)}`);
            score -= 30;
        }
        
        // Check frame time
        if (profilerStats.frameTime > this.targets.frameTime.critical) {
            issues.push(`Critical frame time: ${profilerStats.frameTime.toFixed(1)}ms`);
            score -= 40;
        } else if (profilerStats.frameTime > this.targets.frameTime.max) {
            issues.push(`High frame time: ${profilerStats.frameTime.toFixed(1)}ms`);
            score -= 20;
        }
        
        // Check memory usage
        if (profilerStats.memoryUsage > this.targets.memory.critical) {
            issues.push(`Critical memory usage: ${profilerStats.memoryUsage.toFixed(1)}MB`);
            score -= 40;
        } else if (profilerStats.memoryUsage > this.targets.memory.max) {
            issues.push(`High memory usage: ${profilerStats.memoryUsage.toFixed(1)}MB`);
            score -= 20;
        }
        
        return {
            status: score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical',
            score: Math.max(0, score),
            issues,
            metrics: profilerStats
        };
    }
    
    /**
     * Check gameplay health
     */
    checkGameplayHealth() {
        const issues = [];
        let score = 100;
        
        const profilerStats = rtsProfiler.getStats();
        
        // Check pathfinding performance
        if (profilerStats.pathfindingTime > this.targets.pathfindingTime.critical) {
            issues.push(`Critical pathfinding time: ${profilerStats.pathfindingTime.toFixed(1)}ms`);
            score -= 30;
        } else if (profilerStats.pathfindingTime > this.targets.pathfindingTime.max) {
            issues.push(`Slow pathfinding: ${profilerStats.pathfindingTime.toFixed(1)}ms`);
            score -= 15;
        }
        
        // Check selection performance
        if (profilerStats.selectionTime > this.targets.selectionTime.critical) {
            issues.push(`Critical selection time: ${profilerStats.selectionTime.toFixed(1)}ms`);
            score -= 25;
        } else if (profilerStats.selectionTime > this.targets.selectionTime.max) {
            issues.push(`Slow selection: ${profilerStats.selectionTime.toFixed(1)}ms`);
            score -= 10;
        }
        
        // Check entity count
        if (profilerStats.entityCount > this.targets.entities.critical) {
            issues.push(`Critical entity count: ${profilerStats.entityCount}`);
            score -= 30;
        } else if (profilerStats.entityCount > this.targets.entities.max) {
            issues.push(`High entity count: ${profilerStats.entityCount}`);
            score -= 15;
        }
        
        // Check for game system availability
        const gameSystemsHealthy = this.checkGameSystems();
        if (!gameSystemsHealthy.allHealthy) {
            issues.push(...gameSystemsHealthy.issues);
            score -= gameSystemsHealthy.penalties;
        }
        
        return {
            status: score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical',
            score: Math.max(0, score),
            issues,
            metrics: {
                pathfindingTime: profilerStats.pathfindingTime,
                selectionTime: profilerStats.selectionTime,
                entityCount: profilerStats.entityCount,
                gameSystems: gameSystemsHealthy.systems
            }
        };
    }
    
    /**
     * Check game systems availability
     */
    checkGameSystems() {
        const systems = {
            gameLoop: !!window.gameLoop,
            entityWorld: !!window.gameWorld,
            pathfindingSystem: !!window.pathfindingSystem,
            selectionSystem: !!window.selectionSystem,
            inputHandler: !!window.inputHandler,
            renderer: !!window.gameRenderer
        };
        
        const issues = [];
        let penalties = 0;
        
        for (const [systemName, available] of Object.entries(systems)) {
            if (!available) {
                issues.push(`${systemName} not available`);
                penalties += 20;
            }
        }
        
        return {
            allHealthy: issues.length === 0,
            systems,
            issues,
            penalties
        };
    }
    
    /**
     * Check resource health
     */
    checkResourceHealth() {
        const issues = [];
        let score = 100;
        
        // Check texture memory if available
        if (window.gameRenderer && window.gameRenderer.getTextureMemoryUsage) {
            const textureMemory = window.gameRenderer.getTextureMemoryUsage();
            if (textureMemory > 100) { // 100MB threshold
                issues.push(`High texture memory: ${textureMemory.toFixed(1)}MB`);
                score -= 15;
            }
        }
        
        // Check asset loading status
        if (window.assetLoader) {
            const loadingStats = window.assetLoader.getStats();
            if (loadingStats.failed > 0) {
                issues.push(`Failed to load ${loadingStats.failed} assets`);
                score -= loadingStats.failed * 5;
            }
        }
        
        return {
            status: score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical',
            score: Math.max(0, score),
            issues,
            metrics: {
                textureMemory: window.gameRenderer?.getTextureMemoryUsage?.() || 0,
                assetsLoaded: window.assetLoader?.getStats?.().loaded || 0,
                assetsFailed: window.assetLoader?.getStats?.().failed || 0
            }
        };
    }
    
    /**
     * Check network health
     */
    checkNetworkHealth() {
        const issues = [];
        let score = 100;
        
        // Check navigator.onLine
        if (!navigator.onLine) {
            issues.push('No network connection');
            score -= 100;
        }
        
        // Check WebSocket connection if available
        if (window.gameWebSocket) {
            if (window.gameWebSocket.readyState !== WebSocket.OPEN) {
                issues.push('WebSocket connection not open');
                score -= 30;
            }
        }
        
        return {
            status: score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical',
            score: Math.max(0, score),
            issues,
            metrics: {
                onLine: navigator.onLine,
                wsConnected: window.gameWebSocket?.readyState === WebSocket.OPEN
            }
        };
    }
    
    /**
     * Calculate overall health from individual checks
     */
    calculateOverallHealth(results) {
        let totalScore = 0;
        let totalWeight = 0;
        const issues = [];
        const recommendations = [];
        
        for (const [checkType, config] of this.healthChecks) {
            if (config.enabled && results.has(checkType)) {
                const result = results.get(checkType);
                totalScore += result.score * config.weight;
                totalWeight += config.weight;
                
                if (result.issues && result.issues.length > 0) {
                    issues.push(...result.issues.map(issue => `${checkType}: ${issue}`));
                }
            }
        }
        
        const overallScore = totalWeight > 0 ? totalScore / totalWeight : 0;
        let status = 'healthy';
        
        if (overallScore < 60) {
            status = 'critical';
            recommendations.push('System requires immediate attention');
        } else if (overallScore < 80) {
            status = 'warning';
            recommendations.push('System performance should be monitored');
        }
        
        // Add specific recommendations
        if (issues.some(issue => issue.includes('FPS') || issue.includes('frame time'))) {
            recommendations.push('Consider reducing visual effects or entity count');
        }
        
        if (issues.some(issue => issue.includes('memory'))) {
            recommendations.push('Investigate memory leaks or implement object pooling');
        }
        
        this.overallHealth = {
            status,
            score: Math.round(overallScore),
            lastUpdate: Date.now(),
            issues: issues.slice(0, 10), // Keep top 10 issues
            recommendations: recommendations.slice(0, 5) // Keep top 5 recommendations
        };
    }
    
    /**
     * Update health history
     */
    updateHealthHistory() {
        this.healthHistory.push({
            timestamp: Date.now(),
            status: this.overallHealth.status,
            score: this.overallHealth.score,
            issueCount: this.overallHealth.issues.length
        });
        
        // Keep history within limits
        if (this.healthHistory.length > this.maxHistorySize) {
            this.healthHistory = this.healthHistory.slice(-this.maxHistorySize);
        }
    }
    
    /**
     * Process health alerts
     */
    processHealthAlerts(results) {
        const now = Date.now();
        
        // Check for new alerts
        for (const [checkType, result] of results) {
            if (result.status === 'critical') {
                const alertId = `${checkType}_critical`;
                
                if (!this.alerts.active.has(alertId)) {
                    this.createAlert(alertId, `Critical health issue in ${checkType}`, result);
                }
            }
        }
        
        // Clean up resolved alerts
        for (const [alertId, alert] of this.alerts.active) {
            const checkType = alertId.split('_')[0];
            const currentResult = results.get(checkType);
            
            if (currentResult && currentResult.status !== 'critical') {
                this.resolveAlert(alertId, 'Health check recovered');
            } else if (now - alert.created > this.cooldownPeriod) {
                // Re-trigger alert after cooldown
                alert.lastTriggered = now;
                this.triggerAlert(alert);
            }
        }
    }
    
    /**
     * Create new alert
     */
    createAlert(id, message, data) {
        const alert = {
            id,
            message,
            data,
            created: Date.now(),
            lastTriggered: Date.now(),
            severity: 'critical'
        };
        
        this.alerts.active.set(id, alert);
        this.triggerAlert(alert);
        
        rtsDiagnostics.error(`Health Alert: ${message}`, data);
    }
    
    /**
     * Resolve alert
     */
    resolveAlert(id, resolution) {
        const alert = this.alerts.active.get(id);
        if (alert) {
            alert.resolved = Date.now();
            alert.resolution = resolution;
            
            // Move to history
            this.alerts.history.unshift(alert);
            this.alerts.active.delete(id);
            
            // Keep history within limits
            if (this.alerts.history.length > this.alerts.maxHistory) {
                this.alerts.history = this.alerts.history.slice(0, this.alerts.maxHistory);
            }
            
            rtsDiagnostics.info(`Health Alert Resolved: ${alert.message}`, { resolution });
        }
    }
    
    /**
     * Trigger alert
     */
    triggerAlert(alert) {
        console.error(`🚨 RTS Health Alert: ${alert.message}`, alert.data);
        
        // Send to external monitoring
        if (window.RTSMonitoringBridge) {
            window.RTSMonitoringBridge.sendAlert({
                type: 'health_alert',
                message: alert.message,
                data: alert.data,
                severity: alert.severity,
                timestamp: alert.lastTriggered
            });
        }
    }
    
    /**
     * Get current health status
     */
    getHealthStatus() {
        return {
            status: this.overallHealth.status,
            score: this.overallHealth.score,
            uptime: (Date.now() - this.startTime) / 1000,
            lastUpdate: this.overallHealth.lastUpdate,
            checks: Object.fromEntries(
                Array.from(this.healthChecks.entries()).map(([key, config]) => [
                    key, 
                    { status: config.status, lastCheck: config.lastCheck }
                ])
            )
        };
    }

    /**
     * Get detailed health status
     */
    getDetailedHealthStatus() {
        return {
            ...this.getHealthStatus(),
            issues: this.overallHealth.issues,
            recommendations: this.overallHealth.recommendations,
            alerts: {
                active: Array.from(this.alerts.active.values()),
                recent: this.alerts.history.slice(0, 10)
            },
            history: this.healthHistory.slice(-50) // Last 50 entries
        };
    }

    /**
     * Get health metrics for external monitoring
     */
    getHealthMetrics() {
        const profilerStats = rtsProfiler.getStats();
        const diagnosticStats = rtsDiagnostics.getStats();

        return {
            timestamp: Date.now(),
            uptime: (Date.now() - this.startTime) / 1000,
            overallHealth: this.overallHealth,
            performance: {
                fps: profilerStats.fps,
                frameTime: profilerStats.frameTime,
                memoryUsage: profilerStats.memoryUsage,
                entityCount: profilerStats.entityCount
            },
            diagnostics: {
                errorCount: diagnosticStats.errorCount,
                logCount: diagnosticStats.logCount
            },
            targets: this.targets
        };
    }

    /**
     * Get active alerts
     */
    getActiveAlerts() {
        return Array.from(this.alerts.active.values());
    }

    /**
     * Force health check
     */
    forceHealthCheck() {
        return this.performHealthCheck();
    }

    /**
     * Set health check interval
     */
    setCheckInterval(interval) {
        this.checkInterval = interval;
        this.startHealthMonitoring(); // Restart with new interval
        console.log(`🏥 Health check interval set to ${interval / 1000}s`);
    }

    /**
     * Enable or disable health monitoring
     */
    setEnabled(enabled) {
        this.enabled = enabled;

        if (enabled) {
            this.startHealthMonitoring();
        } else if (this.healthCheckId) {
            clearInterval(this.healthCheckId);
            this.healthCheckId = null;
        }

        console.log(`🏥 Health monitoring ${enabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Stop health monitoring
     */
    stop() {
        this.setEnabled(false);
        console.log('🏥 Health monitoring stopped');
    }
}

// Global health monitor instance
export const rtsHealthMonitor = new RTSHealthMonitor();
