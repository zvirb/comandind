import * as PIXI from "pixi.js";

/**
 * GPU Memory Monitor - Advanced WebGL memory tracking and optimization
 * Monitors texture memory, vertex buffers, and GPU performance
 */
export class GPUMemoryMonitor {
    constructor(renderer) {
        this.renderer = renderer;
        this.gl = renderer?.gl;
        this.isWebGL2 = renderer?.context?.webGLVersion === 2;
        
        // Memory tracking
        this.memoryStats = {
            textureMemory: 0,
            bufferMemory: 0,
            totalDrawCalls: 0,
            activeTextures: 0,
            activeBuffers: 0,
            maxTextureSize: 0,
            maxTextureUnits: 0,
            extensions: new Set()
        };
        
        // Performance tracking
        this.performanceHistory = [];
        this.maxHistoryLength = 100;
        this.lastUpdateTime = 0;
        this.updateInterval = 1000; // Update every second
        
        // Memory pressure tracking
        this.memoryPressureThresholds = {
            low: 0.6,    // 60% - Normal operation
            medium: 0.8, // 80% - Start cleanup
            high: 0.9    // 90% - Aggressive cleanup
        };
        
        // Callbacks for memory pressure events
        this.memoryPressureCallbacks = new Map();
        
        this.initializeMonitoring();
    }
    
    /**
     * Initialize GPU monitoring and gather system info
     */
    initializeMonitoring() {
        if (!this.gl) {
            console.warn("⚠️ WebGL context not available for GPU monitoring");
            return;
        }
        
        // Get GPU capabilities
        this.memoryStats.maxTextureSize = this.gl.getParameter(this.gl.MAX_TEXTURE_SIZE);
        this.memoryStats.maxTextureUnits = this.gl.getParameter(this.gl.MAX_TEXTURE_IMAGE_UNITS);
        
        // Check for memory-related extensions
        const memoryExt = this.gl.getExtension("WEBGL_debug_renderer_info");
        if (memoryExt) {
            this.memoryStats.extensions.add("WEBGL_debug_renderer_info");
            this.gpuVendor = this.gl.getParameter(memoryExt.UNMASKED_VENDOR_WEBGL);
            this.gpuRenderer = this.gl.getParameter(memoryExt.UNMASKED_RENDERER_WEBGL);
        }
        
        // Check for other useful extensions
        const extensions = [
            "WEBGL_lose_context",
            "OES_vertex_array_object",
            "OES_element_index_uint",
            "EXT_texture_filter_anisotropic"
        ];
        
        extensions.forEach(ext => {
            if (this.gl.getExtension(ext)) {
                this.memoryStats.extensions.add(ext);
            }
        });
        
        console.log("🖥️ GPU Monitor initialized:", {
            vendor: this.gpuVendor,
            renderer: this.gpuRenderer,
            maxTextureSize: this.memoryStats.maxTextureSize,
            maxTextureUnits: this.memoryStats.maxTextureUnits,
            extensions: Array.from(this.memoryStats.extensions)
        });
    }
    
    /**
     * Update memory statistics
     */
    updateMemoryStats() {
        const now = Date.now();
        if (now - this.lastUpdateTime < this.updateInterval) return;
        
        this.lastUpdateTime = now;
        
        if (!this.gl) return;
        
        // Estimate texture memory from PIXI texture cache
        let textureMemory = 0;
        let activeTextures = 0;
        
        // Iterate through PIXI texture cache
        for (const [url, texture] of PIXI.TextureCache) {
            if (texture && texture.baseTexture && texture.baseTexture.valid) {
                const baseTexture = texture.baseTexture;
                const bytes = baseTexture.width * baseTexture.height * 4; // RGBA
                textureMemory += bytes;
                activeTextures++;
            }
        }
        
        this.memoryStats.textureMemory = textureMemory;
        this.memoryStats.activeTextures = activeTextures;
        
        // Get WebGL stats if available
        if (this.renderer && this.renderer.textureGC) {
            this.memoryStats.totalDrawCalls = this.renderer.textureGC.count || 0;
        }
        
        // Calculate memory pressure
        const memoryPressure = this.calculateMemoryPressure();
        
        // Record performance history
        const perfSnapshot = {
            timestamp: now,
            textureMemoryMB: textureMemory / 1024 / 1024,
            activeTextures,
            memoryPressure,
            drawCalls: this.memoryStats.totalDrawCalls
        };
        
        this.performanceHistory.push(perfSnapshot);
        if (this.performanceHistory.length > this.maxHistoryLength) {
            this.performanceHistory.shift();
        }
        
        // Trigger memory pressure callbacks if needed
        this.checkMemoryPressure(memoryPressure);
    }
    
    /**
     * Calculate current memory pressure level
     */
    calculateMemoryPressure() {
        // Estimate based on texture memory and active textures
        const textureMemoryMB = this.memoryStats.textureMemory / 1024 / 1024;
        const estimatedMaxMemoryMB = 512; // Conservative estimate
        
        const memoryRatio = textureMemoryMB / estimatedMaxMemoryMB;
        const textureRatio = this.memoryStats.activeTextures / 1000; // Assume 1000 as high watermark
        
        // Combine ratios with weighting
        return Math.min(1.0, (memoryRatio * 0.7) + (textureRatio * 0.3));
    }
    
    /**
     * Check memory pressure and trigger callbacks
     */
    checkMemoryPressure(pressure) {
        let level = "low";
        
        if (pressure >= this.memoryPressureThresholds.high) {
            level = "high";
        } else if (pressure >= this.memoryPressureThresholds.medium) {
            level = "medium";
        }
        
        // Trigger callbacks for this pressure level and higher
        const callbacks = this.memoryPressureCallbacks.get(level);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(pressure, level);
                } catch (error) {
                    console.error("Memory pressure callback error:", error);
                }
            });
        }
    }
    
    /**
     * Register callback for memory pressure events
     */
    onMemoryPressure(level, callback) {
        if (!this.memoryPressureCallbacks.has(level)) {
            this.memoryPressureCallbacks.set(level, new Set());
        }
        this.memoryPressureCallbacks.get(level).add(callback);
    }
    
    /**
     * Remove memory pressure callback
     */
    offMemoryPressure(level, callback) {
        const callbacks = this.memoryPressureCallbacks.get(level);
        if (callbacks) {
            callbacks.delete(callback);
        }
    }
    
    /**
     * Force garbage collection of GPU resources
     */
    forceGPUCleanup() {
        if (!this.renderer) return;
        
        console.log("🧹 Forcing GPU resource cleanup...");
        
        // Force PIXI garbage collection
        if (this.renderer.textureGC) {
            this.renderer.textureGC.run();
        }
        
        // Clear WebGL state
        if (this.gl) {
            this.gl.flush();
            this.gl.finish();
        }
        
        // Update stats after cleanup
        setTimeout(() => this.updateMemoryStats(), 100);
    }
    
    /**
     * Get detailed memory statistics
     */
    getDetailedStats() {
        this.updateMemoryStats();
        
        const current = this.performanceHistory[this.performanceHistory.length - 1];
        const memoryPressure = this.calculateMemoryPressure();
        
        return {
            current: {
                textureMemoryMB: (this.memoryStats.textureMemory / 1024 / 1024).toFixed(1),
                activeTextures: this.memoryStats.activeTextures,
                memoryPressure: (memoryPressure * 100).toFixed(1) + "%",
                drawCalls: this.memoryStats.totalDrawCalls
            },
            gpu: {
                vendor: this.gpuVendor || "Unknown",
                renderer: this.gpuRenderer || "Unknown",
                maxTextureSize: this.memoryStats.maxTextureSize,
                maxTextureUnits: this.memoryStats.maxTextureUnits,
                webGLVersion: this.isWebGL2 ? 2 : 1,
                extensions: Array.from(this.memoryStats.extensions)
            },
            thresholds: this.memoryPressureThresholds,
            history: this.performanceHistory.slice(-20) // Last 20 entries
        };
    }

    /**
     * Get performance trends
     */
    getPerformanceTrends() {
        if (this.performanceHistory.length < 2) {
            return { trend: "insufficient_data" };
        }

        const recent = this.performanceHistory.slice(-10);
        const memoryTrend = this.calculateTrend(recent.map(p => p.textureMemoryMB));
        const textureTrend = this.calculateTrend(recent.map(p => p.activeTextures));
        const pressureTrend = this.calculateTrend(recent.map(p => p.memoryPressure));

        return {
            memory: memoryTrend,
            textures: textureTrend,
            pressure: pressureTrend,
            recommendation: this.getOptimizationRecommendation(memoryTrend, pressureTrend)
        };
    }

    /**
     * Calculate trend direction for a data series
     */
    calculateTrend(data) {
        if (data.length < 2) return "stable";

        const first = data[0];
        const last = data[data.length - 1];
        const change = (last - first) / Math.max(first, 1);

        if (change > 0.1) return "increasing";
        if (change < -0.1) return "decreasing";
        return "stable";
    }

    /**
     * Get optimization recommendations
     */
    getOptimizationRecommendation(memoryTrend, pressureTrend) {
        if (pressureTrend === "increasing") {
            return "Consider reducing texture quality or implementing more aggressive cleanup";
        }

        if (memoryTrend === "increasing") {
            return "Monitor texture usage and consider implementing texture atlasing";
        }

        return "Memory usage is stable - no immediate action required";
    }

    /**
     * Check if WebGL context is lost
     */
    isContextLost() {
        return this.gl && this.gl.isContextLost();
    }

    /**
     * Handle WebGL context loss
     */
    handleContextLoss() {
        console.error("🚨 WebGL context lost!");

        // Clear all memory tracking
        this.memoryStats.textureMemory = 0;
        this.memoryStats.activeTextures = 0;
        this.memoryStats.totalDrawCalls = 0;

        // Notify all callbacks about context loss
        for (const callbacks of this.memoryPressureCallbacks.values()) {
            callbacks.forEach(callback => {
                try {
                    callback(1.0, "context_lost");
                } catch (error) {
                    console.error("Context loss callback error:", error);
                }
            });
        }
    }

    /**
     * Start continuous monitoring
     */
    startMonitoring(interval = 5000) {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }

        this.monitoringInterval = setInterval(() => {
            if (!this.isContextLost()) {
                this.updateMemoryStats();
            } else {
                this.handleContextLoss();
            }
        }, interval);

        console.log(`📊 Started GPU memory monitoring (${interval}ms interval)`);
    }

    /**
     * Stop monitoring
     */
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }

        console.log("⏹️ Stopped GPU memory monitoring");
    }

    /**
     * Destroy monitor and clean up
     */
    destroy() {
        this.stopMonitoring();

        // Clear all callbacks
        this.memoryPressureCallbacks.clear();

        // Clear history
        this.performanceHistory = [];

        console.log("🔚 GPU Memory Monitor destroyed");
    }
}

// Global GPU monitor instance
export let globalGPUMonitor = null;

/**
 * Initialize global GPU monitor
 */
export function initializeGPUMonitor(renderer) {
    if (globalGPUMonitor) {
        globalGPUMonitor.destroy();
    }

    globalGPUMonitor = new GPUMemoryMonitor(renderer);
    globalGPUMonitor.startMonitoring();

    return globalGPUMonitor;
}
