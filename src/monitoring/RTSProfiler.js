/**
 * RTS Performance Profiler
 * Comprehensive profiling system for Command & Independent Thought
 * Monitors pathfinding, selection, resource systems, and overall performance
 */

export class RTSProfiler {
    constructor() {
        this.enabled = true;
        this.startTime = performance.now();
        
        // Performance targets
        this.targets = {
            fps: 60,
            minFps: 45,
            maxFrameTime: 16.67,
            maxPathfindingTime: 5,
            maxSelectionTime: 16,
            maxMemory: 200,
            maxEntities: 200
        };
        
        // Profiling data storage
        this.metrics = {
            frame: {
                fps: 0,
                frameTime: 0,
                frameCount: 0,
                frameTimes: new Array(300).fill(16.67), // 5 seconds at 60fps
                frameTimeIndex: 0,
                lastFrameTime: performance.now()
            },
            pathfinding: {
                totalCalculations: 0,
                totalTime: 0,
                averageTime: 0,
                longestPath: 0,
                cacheHits: 0,
                cacheMisses: 0,
                queueLength: 0,
                activePaths: new Map(),
                pathHistogram: new Array(10).fill(0), // 0-1ms, 1-2ms, etc.
                spatialQueries: 0,
                gridUpdates: 0
            },
            selection: {
                totalSelections: 0,
                totalTime: 0,
                averageTime: 0,
                largestSelection: 0,
                dragSelections: 0,
                clickSelections: 0,
                multiSelections: 0,
                selectionHistogram: new Array(10).fill(0), // by entity count
                lastSelectionSize: 0,
                selectionEventsPerSecond: 0
            },
            resources: {
                tickRate: 0,
                totalTicks: 0,
                economyBalance: 0,
                resourceTransactions: 0,
                buildingCount: 0,
                unitCount: 0,
                resourceEvents: [],
                productionRate: 0,
                consumptionRate: 0
            },
            memory: {
                usedJSHeapSize: 0,
                totalJSHeapSize: 0,
                jsHeapSizeLimit: 0,
                entityCount: 0,
                componentCount: 0,
                systemCount: 0,
                textureMemory: 0,
                audioMemory: 0
            },
            network: {
                packetsPerSecond: 0,
                bytesPerSecond: 0,
                latency: 0,
                packetLoss: 0,
                connectionQuality: 'excellent'
            },
            alerts: []
        };
        
        // Performance history for trending
        this.history = {
            fps: [],
            pathfindingTime: [],
            selectionTime: [],
            memoryUsage: [],
            entityCount: [],
            maxHistoryLength: 300 // 5 minutes of data
        };
        
        this.startProfiling();
    }
    
    /**
     * Start profiling systems
     */
    startProfiling() {
        if (!this.enabled) return;
        
        console.log('🔬 Starting RTS Performance Profiler');
        
        // Start frame profiling
        this.startFrameProfiling();
        
        // Start memory profiling
        this.startMemoryProfiling();
        
        // Setup alert system
        this.setupAlertSystem();
    }
    
    /**
     * Start frame performance profiling
     */
    startFrameProfiling() {
        const updateFrameMetrics = () => {
            if (!this.enabled) return;
            
            const now = performance.now();
            const deltaTime = now - this.metrics.frame.lastFrameTime;
            
            // Update frame timing
            this.metrics.frame.frameTimes[this.metrics.frame.frameTimeIndex] = deltaTime;
            this.metrics.frame.frameTimeIndex = (this.metrics.frame.frameTimeIndex + 1) % this.metrics.frame.frameTimes.length;
            
            // Calculate average frame time and FPS
            const avgFrameTime = this.metrics.frame.frameTimes.reduce((a, b) => a + b, 0) / this.metrics.frame.frameTimes.length;
            this.metrics.frame.frameTime = avgFrameTime;
            this.metrics.frame.fps = 1000 / avgFrameTime;
            this.metrics.frame.frameCount++;
            this.metrics.frame.lastFrameTime = now;
            
            // Update history
            this.updateHistory('fps', this.metrics.frame.fps);
            
            requestAnimationFrame(updateFrameMetrics);
        };
        
        requestAnimationFrame(updateFrameMetrics);
    }
    
    /**
     * Start memory profiling
     */
    startMemoryProfiling() {
        const updateMemoryMetrics = () => {
            if (!this.enabled) return;
            
            if (performance.memory) {
                this.metrics.memory.usedJSHeapSize = performance.memory.usedJSHeapSize / 1048576; // MB
                this.metrics.memory.totalJSHeapSize = performance.memory.totalJSHeapSize / 1048576; // MB
                this.metrics.memory.jsHeapSizeLimit = performance.memory.jsHeapSizeLimit / 1048576; // MB
            }
            
            // Update history
            this.updateHistory('memoryUsage', this.metrics.memory.usedJSHeapSize);
        };
        
        // Update memory metrics every second
        setInterval(updateMemoryMetrics, 1000);
    }
    
    /**
     * Profile pathfinding operation
     */
    profilePathfinding(operation, startTime, endTime, pathLength = 0, cached = false) {
        if (!this.enabled) return;
        
        const duration = endTime - startTime;
        
        // Update pathfinding metrics
        this.metrics.pathfinding.totalCalculations++;
        this.metrics.pathfinding.totalTime += duration;
        this.metrics.pathfinding.averageTime = this.metrics.pathfinding.totalTime / this.metrics.pathfinding.totalCalculations;
        this.metrics.pathfinding.longestPath = Math.max(this.metrics.pathfinding.longestPath, pathLength);
        
        if (cached) {
            this.metrics.pathfinding.cacheHits++;
        } else {
            this.metrics.pathfinding.cacheMisses++;
        }
        
        // Update histogram
        const histogramIndex = Math.min(Math.floor(duration), 9);
        this.metrics.pathfinding.pathHistogram[histogramIndex]++;
        
        // Update history
        this.updateHistory('pathfindingTime', duration);
        
        // Check for performance issues
        if (duration > this.targets.maxPathfindingTime) {
            this.addAlert('pathfinding_slow', `Pathfinding took ${duration.toFixed(2)}ms (target: ${this.targets.maxPathfindingTime}ms)`, {
                duration,
                pathLength,
                operation
            });
        }
        
        this.broadcastMetrics('pathfinding', {
            averageCalculationTime: this.metrics.pathfinding.averageTime,
            pathsPerSecond: this.getPathsPerSecond(),
            cacheHitRatio: this.getCacheHitRatio(),
            queueLength: this.metrics.pathfinding.queueLength,
            spatialQueries: this.metrics.pathfinding.spatialQueries
        });
    }
    
    /**
     * Profile selection operation
     */
    profileSelection(selectionType, entityCount, startTime, endTime) {
        if (!this.enabled) return;
        
        const duration = endTime - startTime;
        
        // Update selection metrics
        this.metrics.selection.totalSelections++;
        this.metrics.selection.totalTime += duration;
        this.metrics.selection.averageTime = this.metrics.selection.totalTime / this.metrics.selection.totalSelections;
        this.metrics.selection.largestSelection = Math.max(this.metrics.selection.largestSelection, entityCount);
        this.metrics.selection.lastSelectionSize = entityCount;
        
        // Update selection type counters
        switch (selectionType) {
            case 'drag':
                this.metrics.selection.dragSelections++;
                break;
            case 'click':
                this.metrics.selection.clickSelections++;
                break;
            case 'multi':
                this.metrics.selection.multiSelections++;
                break;
        }
        
        // Update histogram by entity count
        const histogramIndex = Math.min(Math.floor(entityCount / 10), 9);
        this.metrics.selection.selectionHistogram[histogramIndex]++;
        
        // Update history
        this.updateHistory('selectionTime', duration);
        
        // Check for performance issues
        if (duration > this.targets.maxSelectionTime) {
            this.addAlert('selection_slow', `Selection took ${duration.toFixed(2)}ms (target: ${this.targets.maxSelectionTime}ms)`, {
                duration,
                entityCount,
                selectionType
            });
        }
        
        this.broadcastMetrics('selection', {
            averageSelectionTime: this.metrics.selection.averageTime,
            lastSelectionSize: entityCount,
            selectionEventsPerSecond: this.getSelectionsPerSecond(),
            dragSelectionTime: duration
        });
    }
    
    /**
     * Profile resource system operation
     */
    profileResources(resourceData) {
        if (!this.enabled) return;
        
        this.metrics.resources = {
            ...this.metrics.resources,
            ...resourceData,
            totalTicks: this.metrics.resources.totalTicks + 1
        };
        
        this.broadcastMetrics('resources', this.metrics.resources);
    }
    
    /**
     * Update entity and component counts
     */
    updateEntityMetrics(entityCount, componentCount, systemCount) {
        if (!this.enabled) return;
        
        this.metrics.memory.entityCount = entityCount;
        this.metrics.memory.componentCount = componentCount;
        this.metrics.memory.systemCount = systemCount;
        
        // Update history
        this.updateHistory('entityCount', entityCount);
        
        // Check for performance issues
        if (entityCount > this.targets.maxEntities) {
            this.addAlert('entity_overflow', `Entity count exceeded limit: ${entityCount}/${this.targets.maxEntities}`, {
                entityCount,
                componentCount,
                systemCount
            });
        }
    }
    
    /**
     * Update performance history
     */
    updateHistory(metric, value) {
        if (!this.history[metric]) return;
        
        this.history[metric].push({
            timestamp: Date.now(),
            value: value
        });
        
        // Keep history within limits
        if (this.history[metric].length > this.history.maxHistoryLength) {
            this.history[metric].shift();
        }
    }
    
    /**
     * Add performance alert
     */
    addAlert(type, message, data = {}) {
        const alert = {
            id: Date.now() + Math.random(),
            type,
            message,
            timestamp: Date.now(),
            data,
            severity: this.getAlertSeverity(type)
        };
        
        this.metrics.alerts.unshift(alert);
        
        // Keep only last 50 alerts
        if (this.metrics.alerts.length > 50) {
            this.metrics.alerts = this.metrics.alerts.slice(0, 50);
        }
        
        console.warn(`🚨 RTS Performance Alert [${type}]: ${message}`, data);
    }
    
    /**
     * Get alert severity
     */
    getAlertSeverity(type) {
        const severityMap = {
            fps_low: 'critical',
            frame_time_high: 'warning',
            pathfinding_slow: 'warning',
            selection_slow: 'warning',
            entity_overflow: 'warning',
            memory_high: 'critical',
            system_error: 'critical'
        };
        
        return severityMap[type] || 'info';
    }
    
    /**
     * Calculate paths per second
     */
    getPathsPerSecond() {
        const recentPaths = this.history.pathfindingTime.filter(
            entry => Date.now() - entry.timestamp < 1000
        ).length;
        
        return recentPaths;
    }
    
    /**
     * Calculate cache hit ratio
     */
    getCacheHitRatio() {
        const totalRequests = this.metrics.pathfinding.cacheHits + this.metrics.pathfinding.cacheMisses;
        return totalRequests > 0 ? this.metrics.pathfinding.cacheHits / totalRequests : 0;
    }
    
    /**
     * Calculate selections per second
     */
    getSelectionsPerSecond() {
        const recentSelections = this.history.selectionTime.filter(
            entry => Date.now() - entry.timestamp < 1000
        ).length;
        
        return recentSelections;
    }
    
    /**
     * Setup alert system
     */
    setupAlertSystem() {
        setInterval(() => {
            if (!this.enabled) return;
            
            // Check FPS
            if (this.metrics.frame.fps < this.targets.minFps) {
                this.addAlert('fps_low', `FPS dropped to ${this.metrics.frame.fps.toFixed(1)} (target: ${this.targets.fps})`, {
                    fps: this.metrics.frame.fps,
                    frameTime: this.metrics.frame.frameTime
                });
            }
            
            // Check memory
            if (this.metrics.memory.usedJSHeapSize > this.targets.maxMemory) {
                this.addAlert('memory_high', `Memory usage exceeded limit: ${this.metrics.memory.usedJSHeapSize.toFixed(1)}MB/${this.targets.maxMemory}MB`, {
                    memoryUsage: this.metrics.memory.usedJSHeapSize
                });
            }
            
        }, 5000); // Check every 5 seconds
    }
    
    /**
     * Broadcast metrics to monitoring systems
     */
    broadcastMetrics(type, data) {
        if (typeof window !== 'undefined' && window.RTSMonitoringBridge) {
            window.RTSMonitoringBridge.updateMetrics(type, data);
        }
        
        // Also broadcast to WebSocket if available
        if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
            this.wsConnection.send(JSON.stringify({
                type: `${type}_metrics`,
                data: data,
                timestamp: Date.now()
            }));
        }
    }
    
    /**
     * Connect to monitoring WebSocket
     */
    connectToMonitoring(wsUrl = 'ws://localhost:8080/ws') {
        try {
            this.wsConnection = new WebSocket(wsUrl);
            
            this.wsConnection.onopen = () => {
                console.log('🔌 Connected to RTS monitoring WebSocket');
            };
            
            this.wsConnection.onclose = () => {
                console.log('🔌 Disconnected from RTS monitoring WebSocket');
                // Attempt reconnection after 5 seconds
                setTimeout(() => this.connectToMonitoring(wsUrl), 5000);
            };
            
            this.wsConnection.onerror = (error) => {
                console.error('WebSocket connection error:', error);
            };
        } catch (error) {
            console.error('Failed to connect to monitoring WebSocket:', error);
        }
    }
    
    /**
     * Generate comprehensive performance report
     */
    generateReport() {
        const uptime = (performance.now() - this.startTime) / 1000;
        
        return {
            timestamp: new Date().toISOString(),
            uptime: uptime,
            performance: {
                fps: this.metrics.frame.fps,
                frameTime: this.metrics.frame.frameTime,
                frameCount: this.metrics.frame.frameCount
            },
            pathfinding: {
                totalCalculations: this.metrics.pathfinding.totalCalculations,
                averageTime: this.metrics.pathfinding.averageTime,
                cacheHitRatio: this.getCacheHitRatio(),
                pathsPerSecond: this.getPathsPerSecond(),
                queueLength: this.metrics.pathfinding.queueLength
            },
            selection: {
                totalSelections: this.metrics.selection.totalSelections,
                averageTime: this.metrics.selection.averageTime,
                selectionsPerSecond: this.getSelectionsPerSecond(),
                largestSelection: this.metrics.selection.largestSelection
            },
            resources: {
                tickRate: this.metrics.resources.tickRate,
                economyBalance: this.metrics.resources.economyBalance,
                buildingCount: this.metrics.resources.buildingCount,
                unitCount: this.metrics.resources.unitCount
            },
            memory: {
                usedJSHeapSize: this.metrics.memory.usedJSHeapSize,
                entityCount: this.metrics.memory.entityCount,
                componentCount: this.metrics.memory.componentCount
            },
            alerts: this.metrics.alerts.slice(0, 10),
            healthScore: this.calculateHealthScore(),
            recommendations: this.generateRecommendations()
        };
    }
    
    /**
     * Calculate overall system health score
     */
    calculateHealthScore() {
        let score = 100;
        
        // FPS penalty
        if (this.metrics.frame.fps < this.targets.fps) {
            score -= Math.max(0, (this.targets.fps - this.metrics.frame.fps) * 2);
        }
        
        // Memory penalty
        if (this.metrics.memory.usedJSHeapSize > this.targets.maxMemory) {
            score -= Math.min(30, (this.metrics.memory.usedJSHeapSize - this.targets.maxMemory) / 10);
        }
        
        // Pathfinding penalty
        if (this.metrics.pathfinding.averageTime > this.targets.maxPathfindingTime) {
            score -= Math.min(20, this.metrics.pathfinding.averageTime - this.targets.maxPathfindingTime);
        }
        
        // Selection penalty
        if (this.metrics.selection.averageTime > this.targets.maxSelectionTime) {
            score -= Math.min(10, this.metrics.selection.averageTime - this.targets.maxSelectionTime);
        }
        
        return Math.max(0, Math.round(score));
    }
    
    /**
     * Generate optimization recommendations
     */
    generateRecommendations() {
        const recommendations = [];
        
        if (this.metrics.frame.fps < this.targets.minFps) {
            recommendations.push({
                type: 'performance',
                priority: 'high',
                message: 'Consider reducing visual effects or entity count to improve FPS'
            });
        }
        
        if (this.metrics.pathfinding.averageTime > this.targets.maxPathfindingTime) {
            recommendations.push({
                type: 'pathfinding',
                priority: 'medium',
                message: 'Optimize pathfinding by reducing calculation frequency or improving caching'
            });
        }
        
        if (this.getCacheHitRatio() < 0.7) {
            recommendations.push({
                type: 'caching',
                priority: 'medium',
                message: 'Improve pathfinding cache hit ratio by increasing cache timeout or better cache keys'
            });
        }
        
        if (this.metrics.memory.usedJSHeapSize > this.targets.maxMemory * 0.8) {
            recommendations.push({
                type: 'memory',
                priority: 'high',
                message: 'Memory usage is high. Consider object pooling or garbage collection optimization'
            });
        }
        
        return recommendations;
    }
    
    /**
     * Get current performance stats
     */
    getStats() {
        return {
            fps: this.metrics.frame.fps,
            frameTime: this.metrics.frame.frameTime,
            entityCount: this.metrics.memory.entityCount,
            memoryUsage: this.metrics.memory.usedJSHeapSize,
            pathfindingTime: this.metrics.pathfinding.averageTime,
            selectionTime: this.metrics.selection.averageTime,
            healthScore: this.calculateHealthScore()
        };
    }
    
    /**
     * Enable or disable profiling
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        console.log(`🔬 RTS Profiler ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Reset all metrics
     */
    reset() {
        console.log('🔄 Resetting RTS Profiler metrics');
        
        // Reset all metrics to initial state
        this.metrics = {
            frame: {
                fps: 0,
                frameTime: 0,
                frameCount: 0,
                frameTimes: new Array(300).fill(16.67),
                frameTimeIndex: 0,
                lastFrameTime: performance.now()
            },
            pathfinding: {
                totalCalculations: 0,
                totalTime: 0,
                averageTime: 0,
                longestPath: 0,
                cacheHits: 0,
                cacheMisses: 0,
                queueLength: 0,
                activePaths: new Map(),
                pathHistogram: new Array(10).fill(0),
                spatialQueries: 0,
                gridUpdates: 0
            },
            selection: {
                totalSelections: 0,
                totalTime: 0,
                averageTime: 0,
                largestSelection: 0,
                dragSelections: 0,
                clickSelections: 0,
                multiSelections: 0,
                selectionHistogram: new Array(10).fill(0),
                lastSelectionSize: 0,
                selectionEventsPerSecond: 0
            },
            resources: {
                tickRate: 0,
                totalTicks: 0,
                economyBalance: 0,
                resourceTransactions: 0,
                buildingCount: 0,
                unitCount: 0,
                resourceEvents: [],
                productionRate: 0,
                consumptionRate: 0
            },
            memory: {
                usedJSHeapSize: 0,
                totalJSHeapSize: 0,
                jsHeapSizeLimit: 0,
                entityCount: 0,
                componentCount: 0,
                systemCount: 0,
                textureMemory: 0,
                audioMemory: 0
            },
            network: {
                packetsPerSecond: 0,
                bytesPerSecond: 0,
                latency: 0,
                packetLoss: 0,
                connectionQuality: 'excellent'
            },
            alerts: []
        };
        
        // Reset history
        Object.keys(this.history).forEach(key => {
            if (Array.isArray(this.history[key])) {
                this.history[key] = [];
            }
        });
        
        this.startTime = performance.now();
    }
}

// Global profiler instance
export const rtsProfiler = new RTSProfiler();