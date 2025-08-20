import * as PIXI from 'pixi.js';
import { globalTexturePool } from './TexturePool.js';

export class TextureAtlasManager {
    constructor() {
        this.atlases = new Map();
        this.textures = new Map();
        this.loadQueue = [];
        this.isLoading = false;
        this.loadedBytes = 0;
        this.totalBytes = 0;
        
        // Memory management
        this.texturePool = globalTexturePool;
        this.memoryPressureThreshold = 0.8; // 80% memory usage triggers cleanup
        this.lastCleanupTime = 0;
        this.cleanupInterval = 60000; // Cleanup every 60 seconds
        this.textureUsageTracking = new Map();
        this.priorityQueue = new Map(); // Track texture priority for cleanup decisions
        
        // Sprite sheet configurations will be loaded from JSON
        this.spriteConfigs = null;
    }

    async initialize() {
        const config = await this.loadSpriteConfig();
        if (config) {
            this.buildSpriteConfigs(config);
        }
    }

    async loadSpriteConfig() {
        try {
            const response = await fetch('/assets/sprites/sprite-config.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const config = await response.json();
            if (!config || Object.keys(config).length === 0) {
                console.warn('⚠️ Sprite config file loaded, but it is empty. No sprites can be configured.');
            } else {
                console.log('✅ Sprite config loaded successfully.');
            }
            return config;
        } catch (error) {
            console.error('❌ Failed to load or parse sprite-config.json:', error);
            console.error('Ensure the file exists at /public/assets/sprites/sprite-config.json and is valid JSON.');
            this.spriteConfigs = {}; // Use empty config on failure
            return null;
        }
    }

    buildSpriteConfigs(config) {
        if (!config || Object.keys(config).length === 0) {
            console.warn('Cannot build sprite configs: config data is missing or empty.');
            this.spriteConfigs = {};
            return;
        }

        this.spriteConfigs = {};
        const basePath = '/assets/sprites';

        // Helper to process categories that might be nested differently (e.g., tiberium)
        const processCategory = (categoryName, categoryData) => {
            if (categoryName === 'tiberium') {
                // Handle flat tiberium structure
                for (const [tiberiumType, tiberiumData] of Object.entries(categoryData)) {
                    const key = `tiberium-${tiberiumType}`;
                    const url = `${basePath}/resources/${tiberiumType}.png`;
                    this.spriteConfigs[key] = { url, ...tiberiumData };
                }
            } else {
                // Handle nested faction structure
                for (const [faction, entities] of Object.entries(categoryData)) {
                    for (const [entityName, entityData] of Object.entries(entities)) {
                        const key = `${faction}-${entityName}`;
                        // Default to .png, but allow for exceptions for test assets.
                        let extension = 'png';
                        if (key === 'gdi-medium-tank') {
                            extension = 'svg'; // Our test asset is an SVG
                        }
                        const url = `${basePath}/${categoryName}/${faction}/${entityName}.${extension}`;
                        this.spriteConfigs[key] = { url, ...entityData };
                    }
                }
            }
        };

        for (const [category, data] of Object.entries(config)) {
            processCategory(category, data);
        }

        console.log('✅ Sprite configs built from JSON data.');
    }
    
    /**
     * Load a texture atlas or sprite sheet with memory management
     * @param {string} key - Unique identifier for the atlas
     * @param {string} url - URL to the image file
     * @param {Object} config - Configuration for sprite extraction
     */
    async loadAtlas(key, url, config = {}) {
        if (this.atlases.has(key)) {
            console.log(`Atlas '${key}' already loaded`);
            this.updateTextureUsage(key);
            return this.atlases.get(key);
        }
        
        // Check memory pressure before loading
        await this.checkMemoryPressure();
        
        try {
            // Use texture pool for caching and memory management
            const texture = this.texturePool.getTexture(key, () => PIXI.Assets.load(url));
            
            if (!texture) {
                throw new Error(`Failed to load texture from ${url}`);
            }
            
            // Store the atlas
            this.atlases.set(key, {
                texture,
                config,
                frames: new Map(),
                loadTime: Date.now(),
                lastAccessed: Date.now(),
                accessCount: 0
            });
            
            // Track texture usage
            this.textureUsageTracking.set(key, {
                loadTime: Date.now(),
                lastAccessed: Date.now(),
                accessCount: 0,
                memoryBytes: this.texturePool.calculateTextureMemory(texture),
                priority: config.priority || 1
            });
            
            // If config has frame dimensions, auto-generate frames
            if (config.frameWidth && config.frameHeight) {
                this.generateFrames(key, config);
            }
            
            console.log(`Atlas '${key}' loaded successfully with memory management`);
            return this.atlases.get(key);
            
        } catch (error) {
            console.error(`Failed to load atlas '${key}':`, error);
            throw error;
        }
    }
    
    /**
     * Generate frame textures from a sprite sheet with memory optimization
     */
    generateFrames(atlasKey, config) {
        const atlas = this.atlases.get(atlasKey);
        if (!atlas) return;
        
        const baseTexture = atlas.texture.baseTexture;
        const { frameWidth, frameHeight } = config;
        
        const columns = Math.floor(baseTexture.width / frameWidth);
        const rows = Math.floor(baseTexture.height / frameHeight);
        
        let frameIndex = 0;
        const frameTextures = new Map();
        
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < columns; x++) {
                const rect = new PIXI.Rectangle(
                    x * frameWidth,
                    y * frameHeight,
                    frameWidth,
                    frameHeight
                );
                
                const frameKey = `${atlasKey}_frame_${frameIndex}`;
                
                // Use texture pool for frame textures to enable reuse
                const frameTexture = this.texturePool.getTexture(frameKey, () => {
                    return new PIXI.Texture(baseTexture, rect);
                });
                
                atlas.frames.set(frameIndex, frameTexture);
                this.textures.set(frameKey, frameTexture);
                frameTextures.set(frameIndex, frameTexture);
                
                frameIndex++;
            }
        }
        
        console.log(`Generated ${frameIndex} optimized frames for atlas '${atlasKey}'`);
        
        // Update atlas with frame count for memory calculations
        atlas.frameCount = frameIndex;
        atlas.estimatedFrameMemory = frameIndex * frameWidth * frameHeight * 4; // RGBA bytes
    }
    
    /**
     * Load multiple atlases with progress tracking
     */
    async loadMultipleAtlases(atlasConfigs, onProgress) {
        const total = atlasConfigs.length;
        let loaded = 0;
        
        for (const config of atlasConfigs) {
            await this.loadAtlas(config.key, config.url, config);
            loaded++;
            
            if (onProgress) {
                onProgress(loaded / total);
            }
        }
    }
    
    /**
     * Load sprites based on predefined configurations
     */
    async loadSpriteSet(spriteKey, onProgress) {
        const config = this.spriteConfigs[spriteKey];
        if (!config) {
            console.error(`No configuration found for sprite '${spriteKey}'`);
            return null;
        }
        
        // Load the atlas
        await this.loadAtlas(spriteKey, config.url, config);
        
        if (onProgress) {
            onProgress(1);
        }
        
        return this.getAtlas(spriteKey);
    }
    
    /**
     * Lazy load sprites - load only when needed
     */
    async lazyLoadSprite(spriteKey) {
        if (this.atlases.has(spriteKey)) {
            return this.atlases.get(spriteKey);
        }
        
        // Add to queue if not already loading
        if (!this.loadQueue.includes(spriteKey)) {
            this.loadQueue.push(spriteKey);
        }
        
        // Process queue if not already processing
        if (!this.isLoading) {
            await this.processLoadQueue();
        }
        
        return this.atlases.get(spriteKey);
    }
    
    /**
     * Process the lazy load queue
     */
    async processLoadQueue() {
        if (this.loadQueue.length === 0 || this.isLoading) {
            return;
        }
        
        this.isLoading = true;
        
        while (this.loadQueue.length > 0) {
            const spriteKey = this.loadQueue.shift();
            await this.loadSpriteSet(spriteKey);
        }
        
        this.isLoading = false;
    }
    
    /**
     * Get a specific frame texture with usage tracking
     */
    getFrameTexture(atlasKey, frameIndex) {
        const atlas = this.atlases.get(atlasKey);
        if (!atlas) {
            console.warn(`Atlas '${atlasKey}' not loaded`);
            return null;
        }
        
        // Update usage tracking
        this.updateTextureUsage(atlasKey);
        
        const frameTexture = atlas.frames.get(frameIndex);
        if (frameTexture) {
            // Increment frame-specific usage if needed
            const frameKey = `${atlasKey}_frame_${frameIndex}`;
            this.updateTextureUsage(frameKey);
        }
        
        return frameTexture || null;
    }
    
    /**
     * Get animation frames for a sprite
     */
    getAnimationFrames(spriteKey, animationName) {
        const config = this.spriteConfigs[spriteKey];
        if (!config || !config.animations[animationName]) {
            return [];
        }
        
        const animation = config.animations[animationName];
        const frames = [];
        
        for (const frameIndex of animation.frames) {
            const texture = this.getFrameTexture(spriteKey, frameIndex);
            if (texture) {
                frames.push(texture);
            }
        }
        
        return frames;
    }
    
    /**
     * Create an animated sprite using texture pool
     */
    createAnimatedSprite(spriteKey, animationName) {
        const frames = this.getAnimationFrames(spriteKey, animationName);
        if (frames.length === 0) {
            console.warn(`No frames found for animation '${animationName}' of sprite '${spriteKey}'`);
            return null;
        }
        
        // Use texture pool for sprite creation
        const sprite = this.texturePool.getAnimatedSprite(frames);
        const config = this.spriteConfigs[spriteKey];
        
        if (config && config.animations[animationName]) {
            sprite.animationSpeed = config.animations[animationName].speed;
            sprite.play();
        }
        
        // Track sprite creation for memory monitoring
        this.updateTextureUsage(spriteKey);
        
        return sprite;
    }
    
    /**
     * Get atlas by key
     */
    getAtlas(key) {
        return this.atlases.get(key);
    }
    
    /**
     * Get texture by key
     */
    getTexture(key) {
        return this.textures.get(key);
    }
    
    /**
     * Update texture usage tracking
     */
    updateTextureUsage(key) {
        const usage = this.textureUsageTracking.get(key);
        if (usage) {
            usage.lastAccessed = Date.now();
            usage.accessCount++;
        }
        
        const atlas = this.atlases.get(key);
        if (atlas) {
            atlas.lastAccessed = Date.now();
            atlas.accessCount++;
        }
    }
    
    /**
     * Check memory pressure and trigger cleanup if needed
     */
    async checkMemoryPressure() {
        const memoryStats = this.texturePool.getMemoryStats();
        const utilizationPercent = parseFloat(memoryStats.utilization);
        
        if (utilizationPercent > (this.memoryPressureThreshold * 100)) {
            console.log(`🚨 Memory pressure detected: ${utilizationPercent}% utilization`);
            await this.performSmartCleanup();
        }
        
        // Periodic cleanup regardless of pressure
        const now = Date.now();
        if (now - this.lastCleanupTime > this.cleanupInterval) {
            await this.performMaintenanceCleanup();
            this.lastCleanupTime = now;
        }
    }
    
    /**
     * Perform smart cleanup based on usage patterns
     */
    async performSmartCleanup() {
        console.log('🧹 Performing smart atlas cleanup...');
        let cleaned = 0;
        
        // Get all atlases sorted by priority and usage
        const atlasEntries = Array.from(this.atlases.entries())
            .map(([key, atlas]) => {
                const usage = this.textureUsageTracking.get(key) || {};
                return {
                    key,
                    atlas,
                    usage,
                    score: this.calculateCleanupScore(key, atlas, usage)
                };
            })
            .sort((a, b) => a.score - b.score); // Lower score = higher priority for cleanup
        
        // Clean up low-priority, unused textures
        const now = Date.now();
        const maxIdleTime = 300000; // 5 minutes
        
        for (const { key, atlas, usage } of atlasEntries) {
            const idleTime = now - (usage.lastAccessed || 0);
            const isLowPriority = (usage.priority || 1) <= 2;
            const isLowUsage = (usage.accessCount || 0) < 5;
            
            if (idleTime > maxIdleTime && (isLowPriority || isLowUsage)) {
                await this.disposeAtlas(key);
                cleaned++;
                
                // Check if we've reduced memory pressure enough
                const memoryStats = this.texturePool.getMemoryStats();
                if (parseFloat(memoryStats.utilization) < 60) break;
            }
        }
        
        console.log(`🧹 Smart cleanup disposed ${cleaned} atlases`);
    }
    
    /**
     * Calculate cleanup score for prioritization
     */
    calculateCleanupScore(key, atlas, usage) {
        const now = Date.now();
        const idleTime = now - (usage.lastAccessed || now);
        const accessFrequency = (usage.accessCount || 0) / Math.max(1, (now - (usage.loadTime || now)) / 60000); // per minute
        const priority = usage.priority || 1;
        const memoryWeight = usage.memoryBytes || 0;
        
        // Lower score = higher cleanup priority
        return (
            (priority * 1000) +
            (accessFrequency * -500) +
            (idleTime / 1000) +
            (memoryWeight / 100000)
        );
    }
    
    /**
     * Perform maintenance cleanup
     */
    async performMaintenanceCleanup() {
        console.log('🔧 Performing maintenance cleanup...');
        
        // Clean up texture pool
        this.texturePool.performMaintenance();
        
        // Remove stale usage tracking
        const now = Date.now();
        const maxStaleTime = 600000; // 10 minutes
        
        for (const [key, usage] of this.textureUsageTracking.entries()) {
            if (now - usage.lastAccessed > maxStaleTime && !this.atlases.has(key)) {
                this.textureUsageTracking.delete(key);
            }
        }
    }
    
    /**
     * Dispose a specific atlas and clean up resources
     */
    async disposeAtlas(key) {
        const atlas = this.atlases.get(key);
        if (!atlas) return;
        
        // Release texture from pool
        this.texturePool.releaseTexture(key);
        
        // Clean up frame textures
        for (const [frameIndex] of atlas.frames) {
            const frameKey = `${key}_frame_${frameIndex}`;
            this.texturePool.releaseTexture(frameKey);
            this.textures.delete(frameKey);
        }
        
        // Remove atlas
        this.atlases.delete(key);
        this.textureUsageTracking.delete(key);
        
        console.log(`🗑️ Disposed atlas '${key}'`);
    }
    
    /**
     * Clear unused textures with improved algorithm
     */
    clearUnused() {
        console.log('🧹 Clearing unused textures...');
        let cleared = 0;
        
        const now = Date.now();
        const unusedThreshold = 180000; // 3 minutes
        
        for (const [key, atlas] of this.atlases.entries()) {
            const usage = this.textureUsageTracking.get(key);
            const idleTime = now - (usage?.lastAccessed || 0);
            const accessCount = usage?.accessCount || 0;
            
            // Consider unused if idle for a while and low access count
            if (idleTime > unusedThreshold && accessCount < 3) {
                this.disposeAtlas(key);
                cleared++;
            }
        }
        
        console.log(`Cleared ${cleared} unused atlases`);
        return cleared;
    }
    
    /**
     * Destroy all loaded atlases with proper cleanup
     */
    destroy() {
        console.log('🔚 Destroying TextureAtlasManager...');
        
        // Dispose all atlases through texture pool
        for (const key of this.atlases.keys()) {
            this.disposeAtlas(key);
        }
        
        // Clear all collections
        this.atlases.clear();
        this.textures.clear();
        this.textureUsageTracking.clear();
        this.priorityQueue.clear();
        this.loadQueue = [];
        
        console.log('✅ TextureAtlasManager destroyed');
    }
    
    /**
     * Get comprehensive memory usage statistics
     */
    getMemoryUsage() {
        let totalBytes = 0;
        let frameBytes = 0;
        let atlasCount = 0;
        let frameCount = 0;
        
        this.atlases.forEach((atlas, key) => {
            atlasCount++;
            const baseTexture = atlas.texture.baseTexture;
            const atlasBytes = baseTexture.width * baseTexture.height * 4;
            totalBytes += atlasBytes;
            
            // Add frame memory estimation
            if (atlas.estimatedFrameMemory) {
                frameBytes += atlas.estimatedFrameMemory;
                frameCount += atlas.frameCount || 0;
            }
        });
        
        // Get texture pool statistics
        const poolStats = this.texturePool.getMemoryStats();
        
        return {
            bytes: totalBytes,
            megabytes: (totalBytes / 1048576).toFixed(2),
            frameBytes,
            frameMegabytes: (frameBytes / 1048576).toFixed(2),
            atlasCount,
            frameCount,
            poolStats,
            usage: this.textureUsageTracking.size,
            efficiency: {
                avgAccessPerAtlas: atlasCount > 0 ? Array.from(this.textureUsageTracking.values())
                    .reduce((sum, u) => sum + (u.accessCount || 0), 0) / atlasCount : 0,
                memoryPerAccess: totalBytes > 0 ? totalBytes / Math.max(1, 
                    Array.from(this.textureUsageTracking.values())
                    .reduce((sum, u) => sum + (u.accessCount || 0), 0)) : 0
            }
        };
    }
    
    /**
     * Get detailed performance metrics
     */
    getPerformanceMetrics() {
        const memoryUsage = this.getMemoryUsage();
        const poolStats = this.texturePool.getMemoryStats();
        
        return {
            memory: memoryUsage,
            pool: poolStats,
            cacheEfficiency: {
                hitRate: this.texturePool.stats.cacheHits / 
                    Math.max(1, this.texturePool.stats.cacheHits + this.texturePool.stats.cacheMisses),
                totalHits: this.texturePool.stats.cacheHits,
                totalMisses: this.texturePool.stats.cacheMisses,
                cleanupCount: this.texturePool.stats.memoryCleanups
            },
            loadingMetrics: {
                queueLength: this.loadQueue.length,
                isLoading: this.isLoading,
                loadedBytes: this.loadedBytes,
                totalBytes: this.totalBytes
            }
        };
    }
}