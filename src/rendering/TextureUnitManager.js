/**
 * Texture Unit Manager for Command & Independent Thought
 * 
 * Advanced texture unit allocation and management system that handles:
 * - Smart texture unit allocation and pooling
 * - GPU memory pressure monitoring
 * - Texture streaming and priority-based loading
 * - WebGL context restoration support
 */

export class TextureUnitManager {
    constructor(gl, maxTextureUnits) {
        this.gl = gl;
        this.maxTextureUnits = maxTextureUnits;
        this.isWebGL2 = gl instanceof WebGL2RenderingContext;
        
        // Texture unit allocation
        this.textureUnits = Array(maxTextureUnits).fill(null).map((_, index) => ({
            index: index,
            texture: null,
            lastUsed: 0,
            priority: 0,
            locked: false, // For persistent textures
            bindCount: 0
        }));
        
        // Reserve units for system use (framebuffers, etc.)
        this.reservedUnits = Math.min(2, Math.floor(maxTextureUnits * 0.1));
        this.availableUnits = maxTextureUnits - this.reservedUnits;
        
        // Texture management
        this.activeTextures = new Map(); // texture -> unit mapping
        this.textureQueue = []; // Priority queue for texture loading
        this.streamingTextures = new Set();
        
        // Memory tracking
        this.memoryStats = {
            totalAllocated: 0,
            totalUsed: 0,
            textureCount: 0,
            averageSize: 0,
            maxAllocation: this.estimateMaxGPUMemory()
        };
        
        // Performance settings
        this.config = {
            enableStreaming: true,
            streamingThreshold: 256, // MB
            priorityDecayRate: 0.1,
            gcInterval: 30000, // 30 seconds
            maxQueueSize: 100
        };
        
        // Statistics
        this.stats = {
            bindCalls: 0,
            cacheMisses: 0,
            cacheHits: 0,
            evictions: 0,
            streamingLoads: 0
        };
        
        this.init();
    }
    
    /**
     * Initialize the texture unit manager
     */
    init() {
        console.log("🎯 Texture Unit Manager initialized:");
        console.log(`   Total units: ${this.maxTextureUnits}`);
        console.log(`   Reserved units: ${this.reservedUnits}`);
        console.log(`   Available units: ${this.availableUnits}`);
        console.log(`   WebGL2: ${this.isWebGL2 ? "Yes" : "No"}`);
        console.log(`   Estimated max GPU memory: ${this.memoryStats.maxAllocation}MB`);
        
        // Start garbage collection cycle
        this.startGarbageCollection();
        
        // Set up memory monitoring
        this.startMemoryMonitoring();
    }
    
    /**
     * Estimate maximum GPU memory available
     */
    estimateMaxGPUMemory() {
        try {
            // Try to get memory info from WebGL extensions
            const debugInfo = this.gl.getExtension("WEBGL_debug_renderer_info");
            if (debugInfo) {
                const renderer = this.gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                
                // Basic heuristics based on common GPU patterns
                if (renderer.includes("Intel")) {
                    return 512; // Intel integrated typically 512MB-1GB
                } else if (renderer.includes("AMD") || renderer.includes("Radeon")) {
                    return 2048; // AMD cards typically 2GB+
                } else if (renderer.includes("NVIDIA") || renderer.includes("GeForce")) {
                    return 4096; // NVIDIA cards typically 4GB+
                }
            }
            
            // Fallback estimate based on device capabilities
            const maxTextureSize = this.gl.getParameter(this.gl.MAX_TEXTURE_SIZE);
            if (maxTextureSize >= 8192) {
                return 2048; // High-end
            } else if (maxTextureSize >= 4096) {
                return 1024; // Mid-range
            } else {
                return 512; // Low-end
            }
            
        } catch (error) {
            console.warn("Could not estimate GPU memory, using conservative default");
            return 512;
        }
    }
    
    /**
     * Bind texture to optimal texture unit
     */
    bindTexture(texture, priority = 1.0) {
        this.stats.bindCalls++;
        
        // Check if texture is already bound
        if (this.activeTextures.has(texture)) {
            const unitIndex = this.activeTextures.get(texture);
            const unit = this.textureUnits[unitIndex];
            
            // Update usage statistics
            unit.lastUsed = Date.now();
            unit.priority = Math.max(unit.priority, priority);
            unit.bindCount++;
            
            // Activate the unit
            this.gl.activeTexture(this.gl.TEXTURE0 + unitIndex);
            this.stats.cacheHits++;
            
            return unitIndex;
        }
        
        this.stats.cacheMisses++;
        
        // Find best available unit
        const unitIndex = this.allocateTextureUnit(priority);
        if (unitIndex === -1) {
            console.warn("⚠️ No texture units available, forcing eviction");
            this.evictLeastRecentlyUsed();
            return this.bindTexture(texture, priority); // Retry
        }
        
        // Bind texture to unit
        const unit = this.textureUnits[unitIndex];
        
        // Evict current texture if needed
        if (unit.texture) {
            this.evictTexture(unitIndex);
        }
        
        // Bind new texture
        this.gl.activeTexture(this.gl.TEXTURE0 + unitIndex);
        this.gl.bindTexture(this.gl.TEXTURE_2D, texture);
        
        // Update tracking
        unit.texture = texture;
        unit.lastUsed = Date.now();
        unit.priority = priority;
        unit.bindCount++;
        
        this.activeTextures.set(texture, unitIndex);
        
        return unitIndex;
    }
    
    /**
     * Allocate optimal texture unit
     */
    allocateTextureUnit(priority) {
        const now = Date.now();
        let bestUnit = -1;
        let bestScore = -Infinity;
        
        // Look for empty units first
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            
            if (!unit.texture && !unit.locked) {
                return i;
            }
            
            // Score units for potential eviction
            if (!unit.locked) {
                const age = now - unit.lastUsed;
                const score = -unit.priority + (age * this.config.priorityDecayRate);
                
                if (score > bestScore && priority > unit.priority) {
                    bestScore = score;
                    bestUnit = i;
                }
            }
        }
        
        return bestUnit;
    }
    
    /**
     * Evict texture from unit
     */
    evictTexture(unitIndex) {
        const unit = this.textureUnits[unitIndex];
        
        if (unit.texture) {
            this.activeTextures.delete(unit.texture);
            unit.texture = null;
            unit.priority = 0;
            this.stats.evictions++;
        }
    }
    
    /**
     * Evict least recently used texture
     */
    evictLeastRecentlyUsed() {
        let oldestUnit = -1;
        let oldestTime = Infinity;
        
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            
            if (unit.texture && !unit.locked && unit.lastUsed < oldestTime) {
                oldestTime = unit.lastUsed;
                oldestUnit = i;
            }
        }
        
        if (oldestUnit !== -1) {
            console.log(`🗑️ Evicting LRU texture from unit ${oldestUnit}`);
            this.evictTexture(oldestUnit);
        }
    }
    
    /**
     * Lock texture unit to prevent eviction
     */
    lockTexture(texture) {
        if (this.activeTextures.has(texture)) {
            const unitIndex = this.activeTextures.get(texture);
            this.textureUnits[unitIndex].locked = true;
            console.log(`🔒 Locked texture in unit ${unitIndex}`);
        }
    }
    
    /**
     * Unlock texture unit
     */
    unlockTexture(texture) {
        if (this.activeTextures.has(texture)) {
            const unitIndex = this.activeTextures.get(texture);
            this.textureUnits[unitIndex].locked = false;
            console.log(`🔓 Unlocked texture in unit ${unitIndex}`);
        }
    }
    
    /**
     * Preload texture with priority
     */
    preloadTexture(textureData, priority = 1.0) {
        const queueItem = {
            textureData,
            priority,
            timestamp: Date.now()
        };
        
        // Insert in priority queue
        let inserted = false;
        for (let i = 0; i < this.textureQueue.length; i++) {
            if (this.textureQueue[i].priority < priority) {
                this.textureQueue.splice(i, 0, queueItem);
                inserted = true;
                break;
            }
        }
        
        if (!inserted) {
            this.textureQueue.push(queueItem);
        }
        
        // Limit queue size
        while (this.textureQueue.length > this.config.maxQueueSize) {
            this.textureQueue.pop();
        }
        
        // Process queue if not busy
        if (!this.processingQueue) {
            this.processTextureQueue();
        }
    }
    
    /**
     * Process texture loading queue
     */
    async processTextureQueue() {
        if (this.processingQueue || this.textureQueue.length === 0) {
            return;
        }
        
        this.processingQueue = true;
        
        while (this.textureQueue.length > 0) {
            const item = this.textureQueue.shift();
            
            try {
                await this.loadTexture(item.textureData, item.priority);
                this.stats.streamingLoads++;
            } catch (error) {
                console.error("❌ Failed to load queued texture:", error);
            }
            
            // Check memory pressure
            if (this.isMemoryPressureHigh()) {
                console.warn("⚠️ High memory pressure, pausing texture queue processing");
                break;
            }
            
            // Yield to prevent blocking
            await new Promise(resolve => setTimeout(resolve, 0));
        }
        
        this.processingQueue = false;
    }
    
    /**
     * Load texture data
     */
    async loadTexture(textureData, priority) {
        // This would typically load texture from URL or create from data
        // For now, simulate texture loading
        
        const texture = this.gl.createTexture();
        this.gl.bindTexture(this.gl.TEXTURE_2D, texture);
        
        // Set texture parameters
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
        
        // Update memory tracking
        const size = this.estimateTextureSize(textureData.width || 512, textureData.height || 512);
        this.memoryStats.totalAllocated += size;
        this.memoryStats.textureCount++;
        this.updateAverageSize();
        
        return texture;
    }
    
    /**
     * Estimate texture memory usage
     */
    estimateTextureSize(width, height, format = "RGBA") {
        let bytesPerPixel = 4; // RGBA
        
        switch (format) {
        case "RGB": bytesPerPixel = 3; break;
        case "LUMINANCE_ALPHA": bytesPerPixel = 2; break;
        case "LUMINANCE": bytesPerPixel = 1; break;
        case "ALPHA": bytesPerPixel = 1; break;
        }
        
        // Include mipmap overhead (approximately 1.33x)
        const baseSize = width * height * bytesPerPixel;
        return Math.floor(baseSize * 1.33);
    }
    
    /**
     * Update average texture size
     */
    updateAverageSize() {
        if (this.memoryStats.textureCount > 0) {
            this.memoryStats.averageSize = this.memoryStats.totalAllocated / this.memoryStats.textureCount;
        }
    }
    
    /**
     * Check if memory pressure is high
     */
    isMemoryPressureHigh() {
        const usageRatio = this.memoryStats.totalAllocated / (this.memoryStats.maxAllocation * 1024 * 1024);
        return usageRatio > 0.85; // 85% threshold
    }
    
    /**
     * Start garbage collection cycle
     */
    startGarbageCollection() {
        setInterval(() => {
            this.performGarbageCollection();
        }, this.config.gcInterval);
    }
    
    /**
     * Perform garbage collection
     */
    performGarbageCollection() {
        const now = Date.now();
        const maxAge = 60000; // 1 minute
        let collected = 0;
        
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            
            if (unit.texture && !unit.locked && (now - unit.lastUsed) > maxAge) {
                this.evictTexture(i);
                collected++;
            }
        }
        
        if (collected > 0) {
            console.log(`🗑️ Garbage collection: freed ${collected} texture units`);
        }
    }
    
    /**
     * Start memory monitoring
     */
    startMemoryMonitoring() {
        setInterval(() => {
            this.updateMemoryStats();
            
            if (this.isMemoryPressureHigh()) {
                this.handleMemoryPressure();
            }
        }, 15000); // Check every 15 seconds
    }
    
    /**
     * Update memory statistics
     */
    updateMemoryStats() {
        // Recalculate memory usage
        let totalUsed = 0;
        
        for (const unit of this.textureUnits) {
            if (unit.texture) {
                // This is a rough estimate - in a real implementation,
                // you'd track actual texture sizes
                totalUsed += this.memoryStats.averageSize || 0;
            }
        }
        
        this.memoryStats.totalUsed = totalUsed;
    }
    
    /**
     * Handle memory pressure situation
     */
    handleMemoryPressure() {
        console.warn("⚠️ High GPU memory pressure detected");
        
        // Aggressive eviction of non-locked textures
        let evicted = 0;
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            
            if (unit.texture && !unit.locked && unit.priority < 0.5) {
                this.evictTexture(i);
                evicted++;
            }
        }
        
        console.log(`🗑️ Memory pressure cleanup: evicted ${evicted} low-priority textures`);
        
        // Pause texture queue processing temporarily
        if (evicted > 0) {
            setTimeout(() => {
                if (!this.processingQueue) {
                    this.processTextureQueue();
                }
            }, 5000);
        }
    }
    
    /**
     * Get current allocation stats
     */
    getStats() {
        const unitsInUse = this.textureUnits.filter(unit => unit.texture).length;
        const lockedUnits = this.textureUnits.filter(unit => unit.locked).length;
        
        return {
            ...this.stats,
            unitsTotal: this.maxTextureUnits,
            unitsReserved: this.reservedUnits,
            unitsInUse: unitsInUse,
            unitsLocked: lockedUnits,
            unitUtilization: (unitsInUse / this.availableUnits) * 100,
            queueLength: this.textureQueue.length,
            memoryAllocatedMB: (this.memoryStats.totalAllocated / (1024 * 1024)).toFixed(2),
            memoryUsedMB: (this.memoryStats.totalUsed / (1024 * 1024)).toFixed(2),
            memoryUtilization: ((this.memoryStats.totalUsed / (this.memoryStats.maxAllocation * 1024 * 1024)) * 100).toFixed(1),
            averageTextureSizeKB: (this.memoryStats.averageSize / 1024).toFixed(2)
        };
    }
    
    /**
     * Force clear all non-locked textures
     */
    clearAllTextures() {
        let cleared = 0;
        
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            
            if (unit.texture && !unit.locked) {
                this.evictTexture(i);
                cleared++;
            }
        }
        
        console.log(`🗑️ Force cleared ${cleared} texture units`);
        
        // Reset memory stats
        this.memoryStats.totalAllocated = 0;
        this.memoryStats.totalUsed = 0;
        this.memoryStats.textureCount = 0;
        this.memoryStats.averageSize = 0;
    }
    
    /**
     * Optimize texture unit allocation
     */
    optimize() {
        const before = this.getStats();
        
        // Compact active textures to lower-numbered units
        const activeTextures = [];
        
        // Collect all active textures with their priorities
        for (let i = this.reservedUnits; i < this.maxTextureUnits; i++) {
            const unit = this.textureUnits[i];
            if (unit.texture) {
                activeTextures.push({
                    texture: unit.texture,
                    priority: unit.priority,
                    lastUsed: unit.lastUsed,
                    locked: unit.locked
                });
                this.evictTexture(i);
            }
        }
        
        // Sort by priority and re-bind
        activeTextures.sort((a, b) => b.priority - a.priority);
        
        for (const textureInfo of activeTextures) {
            const unitIndex = this.bindTexture(textureInfo.texture, textureInfo.priority);
            if (textureInfo.locked) {
                this.lockTexture(textureInfo.texture);
            }
        }
        
        const after = this.getStats();
        
        console.log("🔧 Texture unit optimization complete:");
        console.log(`   Units in use: ${before.unitsInUse} → ${after.unitsInUse}`);
        console.log(`   Utilization: ${before.unitUtilization}% → ${after.unitUtilization}%`);
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        // Clear all textures
        this.clearAllTextures();
        
        // Clear queues and maps
        this.textureQueue = [];
        this.activeTextures.clear();
        this.streamingTextures.clear();
        
        console.log("🗑️ Texture Unit Manager destroyed");
    }
}