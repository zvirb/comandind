import * as PIXI from 'pixi.js';

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
            console.warn('⚠️ WebGL context not available for GPU monitoring');
            return;
        }
        
        // Get GPU capabilities
        this.memoryStats.maxTextureSize = this.gl.getParameter(this.gl.MAX_TEXTURE_SIZE);
        this.memoryStats.maxTextureUnits = this.gl.getParameter(this.gl.MAX_TEXTURE_IMAGE_UNITS);
        
        // Check for memory-related extensions
        const memoryExt = this.gl.getExtension('WEBGL_debug_renderer_info');
        if (memoryExt) {
            this.memoryStats.extensions.add('WEBGL_debug_renderer_info');
            this.gpuVendor = this.gl.getParameter(memoryExt.UNMASKED_VENDOR_WEBGL);
            this.gpuRenderer = this.gl.getParameter(memoryExt.UNMASKED_RENDERER_WEBGL);
        }
        
        // Check for other useful extensions
        const extensions = [
            'WEBGL_lose_context',
            'OES_vertex_array_object',
            'OES_element_index_uint',
            'EXT_texture_filter_anisotropic'
        ];
        
        extensions.forEach(ext => {
            if (this.gl.getExtension(ext)) {
                this.memoryStats.extensions.add(ext);
            }
        });
        
        console.log('🖥️ GPU Monitor initialized:', {
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
        let level = 'low';
        
        if (pressure >= this.memoryPressureThresholds.high) {
            level = 'high';
        } else if (pressure >= this.memoryPressureThresholds.medium) {
            level = 'medium';
        }
        
        // Trigger callbacks for this pressure level and higher
        const callbacks = this.memoryPressureCallbacks.get(level);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(pressure, level);
                } catch (error) {
                    console.error('Memory pressure callback error:', error);
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
        
        console.log('🧹 Forcing GPU resource cleanup...');
        
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
                memoryPressure: (memoryPressure * 100).toFixed(1) + '%',
                drawCalls: this.memoryStats.totalDrawCalls
            },
            gpu: {
                vendor: this.gpuVendor || 'Unknown',
                renderer: this.gpuRenderer || 'Unknown',
                maxTextureSize: this.memoryStats.maxTextureSize,
                maxTextureUnits: this.memoryStats.maxTextureUnits,
                webGLVersion: this.isWebGL2 ? 2 : 1,
                extensions: Array.from(this.memoryStats.extensions)
            },
            thresholds: this.memoryPressureThresholds,
            history: this.performanceHistory.slice(-20) // Last 20 entries
        };\n    }\n    \n    /**\n     * Get performance trends\n     */\n    getPerformanceTrends() {\n        if (this.performanceHistory.length < 2) {\n            return { trend: 'insufficient_data' };\n        }\n        \n        const recent = this.performanceHistory.slice(-10);\n        const memoryTrend = this.calculateTrend(recent.map(p => p.textureMemoryMB));\n        const textureTrend = this.calculateTrend(recent.map(p => p.activeTextures));\n        const pressureTrend = this.calculateTrend(recent.map(p => p.memoryPressure));\n        \n        return {\n            memory: memoryTrend,\n            textures: textureTrend,\n            pressure: pressureTrend,\n            recommendation: this.getOptimizationRecommendation(memoryTrend, pressureTrend)\n        };\n    }\n    \n    /**\n     * Calculate trend direction for a data series\n     */\n    calculateTrend(data) {\n        if (data.length < 2) return 'stable';\n        \n        const first = data[0];\n        const last = data[data.length - 1];\n        const change = (last - first) / Math.max(first, 1);\n        \n        if (change > 0.1) return 'increasing';\n        if (change < -0.1) return 'decreasing';\n        return 'stable';\n    }\n    \n    /**\n     * Get optimization recommendations\n     */\n    getOptimizationRecommendation(memoryTrend, pressureTrend) {\n        if (pressureTrend === 'increasing') {\n            return 'Consider reducing texture quality or implementing more aggressive cleanup';\n        }\n        \n        if (memoryTrend === 'increasing') {\n            return 'Monitor texture usage and consider implementing texture atlasing';\n        }\n        \n        return 'Memory usage is stable - no immediate action required';\n    }\n    \n    /**\n     * Check if WebGL context is lost\n     */\n    isContextLost() {\n        return this.gl && this.gl.isContextLost();\n    }\n    \n    /**\n     * Handle WebGL context loss\n     */\n    handleContextLoss() {\n        console.error('🚨 WebGL context lost!');\n        \n        // Clear all memory tracking\n        this.memoryStats.textureMemory = 0;\n        this.memoryStats.activeTextures = 0;\n        this.memoryStats.totalDrawCalls = 0;\n        \n        // Notify all callbacks about context loss\n        for (const callbacks of this.memoryPressureCallbacks.values()) {\n            callbacks.forEach(callback => {\n                try {\n                    callback(1.0, 'context_lost');\n                } catch (error) {\n                    console.error('Context loss callback error:', error);\n                }\n            });\n        }\n    }\n    \n    /**\n     * Start continuous monitoring\n     */\n    startMonitoring(interval = 5000) {\n        if (this.monitoringInterval) {\n            clearInterval(this.monitoringInterval);\n        }\n        \n        this.monitoringInterval = setInterval(() => {\n            if (!this.isContextLost()) {\n                this.updateMemoryStats();\n            } else {\n                this.handleContextLoss();\n            }\n        }, interval);\n        \n        console.log(`📊 Started GPU memory monitoring (${interval}ms interval)`);\n    }\n    \n    /**\n     * Stop monitoring\n     */\n    stopMonitoring() {\n        if (this.monitoringInterval) {\n            clearInterval(this.monitoringInterval);\n            this.monitoringInterval = null;\n        }\n        \n        console.log('⏹️ Stopped GPU memory monitoring');\n    }\n    \n    /**\n     * Destroy monitor and clean up\n     */\n    destroy() {\n        this.stopMonitoring();\n        \n        // Clear all callbacks\n        this.memoryPressureCallbacks.clear();\n        \n        // Clear history\n        this.performanceHistory = [];\n        \n        console.log('🔚 GPU Memory Monitor destroyed');\n    }\n}\n\n// Global GPU monitor instance\nexport let globalGPUMonitor = null;\n\n/**\n * Initialize global GPU monitor\n */\nexport function initializeGPUMonitor(renderer) {\n    if (globalGPUMonitor) {\n        globalGPUMonitor.destroy();\n    }\n    \n    globalGPUMonitor = new GPUMemoryMonitor(renderer);\n    globalGPUMonitor.startMonitoring();\n    \n    return globalGPUMonitor;\n}