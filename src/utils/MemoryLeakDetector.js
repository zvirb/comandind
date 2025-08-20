/**
 * Memory Leak Detection Utility
 * Provides comprehensive memory leak detection and monitoring for the ECS system
 */

export class MemoryLeakDetector {
    constructor() {
        this.monitoring = false;
        this.monitorInterval = null;
        this.snapshots = [];
        this.maxSnapshots = 10;
        this.alertThresholds = {
            entityGrowthRate: 100, // entities per second
            componentGrowthRate: 500, // components per second
            memoryGrowthRate: 10 * 1024 * 1024, // 10MB per second
            entityLifetime: 300000, // 5 minutes
            unusedEntityTime: 60000, // 1 minute
            maxEntitiesPerSystem: 1000
        };
        this.callbacks = new Set();
    }

    /**
     * Start monitoring the world for memory leaks
     */
    startMonitoring(world, intervalMs = 5000) {
        if (this.monitoring) {
            this.stopMonitoring();
        }

        this.monitoring = true;
        this.world = world;
        
        this.monitorInterval = setInterval(() => {
            this.takeSnapshot();
            this.analyzeSnapshots();
        }, intervalMs);

        console.log(`Memory leak detection started with ${intervalMs}ms interval`);
    }

    /**
     * Stop monitoring
     */
    stopMonitoring() {
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
        }
        this.monitoring = false;
        console.log("Memory leak detection stopped");
    }

    /**
     * Add callback for leak alerts
     */
    onLeakDetected(callback) {
        this.callbacks.add(callback);
    }

    /**
     * Remove leak detection callback
     */
    removeCallback(callback) {
        this.callbacks.delete(callback);
    }

    /**
     * Take a memory snapshot
     */
    takeSnapshot() {
        if (!this.world) return;

        const snapshot = {
            timestamp: Date.now(),
            worldStats: this.world.getStats(),
            entityDetails: this.getEntityDetails(),
            systemDetails: this.getSystemDetails(),
            componentCounts: this.getComponentCounts(),
            memoryUsage: this.getMemoryEstimate()
        };

        this.snapshots.push(snapshot);

        // Keep only recent snapshots
        if (this.snapshots.length > this.maxSnapshots) {
            this.snapshots.shift();
        }

        return snapshot;
    }

    /**
     * Get detailed entity information
     */
    getEntityDetails() {
        const details = [];
        const now = Date.now();

        for (const entity of this.world.entities) {
            const memInfo = entity.getMemoryInfo();
            details.push({
                ...memInfo,
                isValid: entity.isValid(),
                hasComponents: entity.components.size > 0,
                orphaned: !entity.isValid() && entity.components.size > 0
            });
        }

        return details;
    }

    /**
     * Get detailed system information
     */
    getSystemDetails() {
        const details = [];

        for (const system of this.world.systems) {
            const memInfo = system.getMemoryInfo ? system.getMemoryInfo() : {
                name: system.constructor.name,
                entityCount: system.entities.size,
                destroyed: system.destroyed || false
            };

            details.push({
                ...memInfo,
                hasWeakReferences: !!system.entityReferences,
                weakReferenceCount: system.entityReferences ? "unknown" : 0
            });
        }

        return details;
    }

    /**
     * Count components by type
     */
    getComponentCounts() {
        const counts = new Map();

        for (const entity of this.world.entities) {
            if (!entity.isValid()) continue;

            for (const component of entity.getAllComponents()) {
                const name = component.constructor.name;
                const current = counts.get(name) || { count: 0, valid: 0, invalid: 0 };
                current.count++;
                
                if (component.isValid && component.isValid()) {
                    current.valid++;
                } else {
                    current.invalid++;
                }
                
                counts.set(name, current);
            }
        }

        return Object.fromEntries(counts);
    }

    /**
     * Estimate memory usage
     */
    getMemoryEstimate() {
        const estimate = {
            entities: this.world.entities.size * 200, // rough estimate per entity
            components: 0,
            systems: this.world.systems.length * 1000, // rough estimate per system
            total: 0
        };

        // Estimate component memory
        for (const entity of this.world.entities) {
            estimate.components += entity.components.size * 100; // rough estimate per component
        }

        estimate.total = estimate.entities + estimate.components + estimate.systems;
        return estimate;
    }

    /**
     * Analyze snapshots for memory leaks
     */
    analyzeSnapshots() {
        if (this.snapshots.length < 2) return;

        const current = this.snapshots[this.snapshots.length - 1];
        const previous = this.snapshots[this.snapshots.length - 2];
        const timeDiff = (current.timestamp - previous.timestamp) / 1000; // seconds

        const analysis = this.performAnalysis(current, previous, timeDiff);
        
        if (analysis.leaksDetected.length > 0) {
            this.notifyLeakCallbacks(analysis);
        }

        return analysis;
    }

    /**
     * Perform detailed leak analysis
     */
    performAnalysis(current, previous, timeDiff) {
        const analysis = {
            timestamp: current.timestamp,
            leaksDetected: [],
            warnings: [],
            metrics: {}
        };

        // Entity growth rate
        const entityGrowth = current.worldStats.entityCount - previous.worldStats.entityCount;
        const entityGrowthRate = entityGrowth / timeDiff;
        analysis.metrics.entityGrowthRate = entityGrowthRate;

        if (entityGrowthRate > this.alertThresholds.entityGrowthRate) {
            analysis.leaksDetected.push({
                type: "entityGrowth",
                severity: "high",
                message: `High entity growth rate: ${entityGrowthRate.toFixed(2)} entities/second`,
                data: { entityGrowth, entityGrowthRate }
            });
        }

        // Component growth rate
        const prevComponentTotal = Object.values(previous.componentCounts).reduce((sum, comp) => sum + comp.count, 0);
        const currComponentTotal = Object.values(current.componentCounts).reduce((sum, comp) => sum + comp.count, 0);
        const componentGrowth = currComponentTotal - prevComponentTotal;
        const componentGrowthRate = componentGrowth / timeDiff;
        analysis.metrics.componentGrowthRate = componentGrowthRate;

        if (componentGrowthRate > this.alertThresholds.componentGrowthRate) {
            analysis.leaksDetected.push({
                type: "componentGrowth",
                severity: "high",
                message: `High component growth rate: ${componentGrowthRate.toFixed(2)} components/second`,
                data: { componentGrowth, componentGrowthRate }
            });
        }

        // Memory growth rate
        const memoryGrowth = current.memoryUsage.total - previous.memoryUsage.total;
        const memoryGrowthRate = memoryGrowth / timeDiff;
        analysis.metrics.memoryGrowthRate = memoryGrowthRate;

        if (memoryGrowthRate > this.alertThresholds.memoryGrowthRate) {
            analysis.leaksDetected.push({
                type: "memoryGrowth",
                severity: "high",
                message: `High memory growth rate: ${(memoryGrowthRate / 1024 / 1024).toFixed(2)} MB/second`,
                data: { memoryGrowth, memoryGrowthRate }
            });
        }

        // Invalid components
        const invalidComponents = Object.entries(current.componentCounts)
            .filter(([name, data]) => data.invalid > 0)
            .map(([name, data]) => ({ name, invalid: data.invalid }));

        if (invalidComponents.length > 0) {
            analysis.warnings.push({
                type: "invalidComponents",
                severity: "medium",
                message: `Invalid components detected: ${invalidComponents.map(c => `${c.name}(${c.invalid})`).join(", ")}`,
                data: invalidComponents
            });
        }

        // Long-lived entities
        const now = Date.now();
        const longLivedEntities = current.entityDetails.filter(entity => 
            entity.age > this.alertThresholds.entityLifetime
        );

        if (longLivedEntities.length > 0) {
            analysis.warnings.push({
                type: "longLivedEntities",
                severity: "low",
                message: `${longLivedEntities.length} entities have lived longer than ${this.alertThresholds.entityLifetime / 1000} seconds`,
                data: longLivedEntities
            });
        }

        // Unused entities
        const unusedEntities = current.entityDetails.filter(entity =>
            entity.timeSinceLastAccess > this.alertThresholds.unusedEntityTime
        );

        if (unusedEntities.length > 0) {
            analysis.warnings.push({
                type: "unusedEntities",
                severity: "medium",
                message: `${unusedEntities.length} entities haven't been accessed in ${this.alertThresholds.unusedEntityTime / 1000} seconds`,
                data: unusedEntities
            });
        }

        // System overload
        const overloadedSystems = current.systemDetails.filter(system =>
            system.entityCount > this.alertThresholds.maxEntitiesPerSystem
        );

        if (overloadedSystems.length > 0) {
            analysis.warnings.push({
                type: "systemOverload",
                severity: "medium",
                message: `Systems with too many entities: ${overloadedSystems.map(s => `${s.name}(${s.entityCount})`).join(", ")}`,
                data: overloadedSystems
            });
        }

        return analysis;
    }

    /**
     * Notify callbacks about detected leaks
     */
    notifyLeakCallbacks(analysis) {
        for (const callback of this.callbacks) {
            try {
                callback(analysis);
            } catch (error) {
                console.error("Error in leak detection callback:", error);
            }
        }
    }

    /**
     * Generate comprehensive report
     */
    generateReport() {
        if (this.snapshots.length === 0) {
            return { message: "No data available. Start monitoring first." };
        }

        const latest = this.snapshots[this.snapshots.length - 1];
        const oldest = this.snapshots[0];
        const timeSpan = (latest.timestamp - oldest.timestamp) / 1000;

        const report = {
            summary: {
                monitoringDuration: `${timeSpan.toFixed(1)} seconds`,
                snapshotCount: this.snapshots.length,
                currentEntityCount: latest.worldStats.entityCount,
                currentSystemCount: latest.worldStats.systemCount
            },
            trends: {},
            recommendations: []
        };

        if (this.snapshots.length >= 2) {
            const analysis = this.performAnalysis(latest, oldest, timeSpan);
            report.trends = analysis.metrics;
            
            if (analysis.leaksDetected.length > 0) {
                report.recommendations.push("High-priority memory leaks detected - investigate immediately");
            }
            
            if (analysis.warnings.length > 0) {
                report.recommendations.push(`${analysis.warnings.length} warnings detected - monitor closely`);
            }
        }

        return report;
    }

    /**
     * Force garbage collection check (if available)
     */
    forceGarbageCollection() {
        if (global.gc) {
            global.gc();
            return true;
        } else if (window && window.gc) {
            window.gc();
            return true;
        }
        return false;
    }

    /**
     * Get current memory usage (browser only)
     */
    getCurrentMemoryUsage() {
        if (performance.memory) {
            return {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            };
        }
        return null;
    }
}

// Global instance for easy access
export const memoryLeakDetector = new MemoryLeakDetector();