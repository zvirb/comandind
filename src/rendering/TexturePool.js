import * as PIXI from 'pixi.js';

/**
 * Advanced Texture Pool with LRU Cache and Memory Management
 * Handles texture reuse, memory pressure relief, and GPU resource optimization
 */
export class TexturePool {
    constructor(options = {}) {
        this.maxCacheSize = options.maxCacheSize || 100; // Max textures in LRU cache
        this.maxMemoryMB = options.maxMemoryMB || 256;   // Max texture memory in MB
        this.cleanupThreshold = options.cleanupThreshold || 0.8; // Cleanup when 80% full
        
        // LRU Cache for texture reuse
        this.textureCache = new Map();
        this.accessOrder = new Map(); // Track access time for LRU
        this.accessCounter = 0;
        
        // Memory tracking
        this.currentMemoryBytes = 0;
        this.memoryByTexture = new Map();
        
        // Object pooling for PIXI objects
        this.spritePool = [];
        this.animatedSpritePool = [];
        this.containerPool = [];
        
        // Texture reference counting
        this.referenceCount = new Map();
        this.pendingDisposal = new Set();
        
        // Performance monitoring
        this.stats = {
            cacheHits: 0,
            cacheMisses: 0,
            memoryCleanups: 0,
            objectsPooled: 0,
            texturesDisposed: 0
        };
        
        // Automatic cleanup interval
        this.cleanupInterval = setInterval(() => this.performMaintenance(), 30000);
        
        console.log('🎮 TexturePool initialized with', {
            maxCacheSize: this.maxCacheSize,
            maxMemoryMB: this.maxMemoryMB,
            cleanupThreshold: this.cleanupThreshold
        });
    }
    
    /**
     * Get or create texture with caching and memory management
     */
    getTexture(key, createFn) {
        // Check LRU cache first
        if (this.textureCache.has(key)) {
            this.stats.cacheHits++;
            this.updateAccessTime(key);
            const cachedEntry = this.textureCache.get(key);
            this.incrementReference(key);
            return cachedEntry.texture;
        }
        
        this.stats.cacheMisses++;
        
        // Create new texture
        const texture = createFn();
        if (!texture) return null;
        
        // Calculate memory usage
        const memoryBytes = this.calculateTextureMemory(texture);
        
        // Check if we need to free memory before adding
        if (this.needsMemoryCleanup(memoryBytes)) {
            this.performMemoryCleanup(memoryBytes);
        }
        
        // Store in cache
        this.textureCache.set(key, {
            texture,
            createdAt: Date.now(),
            lastAccessed: Date.now(),
            memoryBytes
        });
        
        this.updateAccessTime(key);
        this.memoryByTexture.set(key, memoryBytes);
        this.currentMemoryBytes += memoryBytes;
        this.referenceCount.set(key, 1);
        
        // Enforce cache size limit
        this.enforceCacheLimit();
        
        return texture;
    }
    
    /**
     * Get sprite from pool or create new one
     */
    getSprite(texture) {
        let sprite;
        
        if (this.spritePool.length > 0) {
            sprite = this.spritePool.pop();
            sprite.texture = texture;
            sprite.visible = true;
            sprite.alpha = 1;
            sprite.rotation = 0;
            sprite.scale.set(1, 1);
            sprite.position.set(0, 0);
            sprite.anchor.set(0);
            this.stats.objectsPooled++;
        } else {
            sprite = new PIXI.Sprite(texture);
        }
        
        return sprite;
    }
    
    /**
     * Get animated sprite from pool or create new one
     */
    getAnimatedSprite(textures) {
        let sprite;
        
        if (this.animatedSpritePool.length > 0) {
            sprite = this.animatedSpritePool.pop();
            sprite.textures = textures;
            sprite.visible = true;
            sprite.alpha = 1;
            sprite.rotation = 0;
            sprite.scale.set(1, 1);
            sprite.position.set(0, 0);
            sprite.anchor.set(0);
            sprite.stop();
            sprite.currentFrame = 0;
            this.stats.objectsPooled++;
        } else {
            sprite = new PIXI.AnimatedSprite(textures);
        }
        
        return sprite;
    }
    
    /**
     * Get container from pool or create new one
     */
    getContainer() {
        let container;
        
        if (this.containerPool.length > 0) {
            container = this.containerPool.pop();
            container.removeChildren();
            container.visible = true;
            container.alpha = 1;
            container.rotation = 0;
            container.scale.set(1, 1);
            container.position.set(0, 0);
            this.stats.objectsPooled++;
        } else {
            container = new PIXI.Container();
        }
        
        return container;
    }
    
    /**
     * Return sprite to pool for reuse
     */
    returnSprite(sprite) {
        if (!sprite || sprite.destroyed) return;
        
        // Clean sprite state
        if (sprite.parent) {
            sprite.parent.removeChild(sprite);
        }
        
        sprite.texture = PIXI.Texture.EMPTY;
        sprite.visible = false;
        
        // Return to appropriate pool
        if (sprite instanceof PIXI.AnimatedSprite) {
            if (this.animatedSpritePool.length < 50) {
                this.animatedSpritePool.push(sprite);
            } else {
                sprite.destroy();
            }
        } else {
            if (this.spritePool.length < 100) {
                this.spritePool.push(sprite);
            } else {
                sprite.destroy();
            }
        }
    }
    
    /**
     * Return container to pool for reuse
     */
    returnContainer(container) {
        if (!container || container.destroyed) return;
        
        if (container.parent) {
            container.parent.removeChild(container);
        }
        
        container.removeChildren();
        
        if (this.containerPool.length < 20) {
            this.containerPool.push(container);
        } else {
            container.destroy();
        }
    }
    
    /**
     * Release texture reference and dispose if no longer needed
     */
    releaseTexture(key) {
        if (!this.referenceCount.has(key)) return;
        
        const count = this.referenceCount.get(key) - 1;
        this.referenceCount.set(key, count);
        
        if (count <= 0) {
            this.pendingDisposal.add(key);
        }
    }
    
    /**
     * Force dispose texture and free GPU memory
     */
    disposeTexture(key) {
        if (!this.textureCache.has(key)) return;
        
        const entry = this.textureCache.get(key);
        
        // Destroy texture and free GPU memory
        if (entry.texture && !entry.texture.destroyed) {
            entry.texture.destroy(true);
            this.stats.texturesDisposed++;
        }
        
        // Update memory tracking
        const memoryBytes = this.memoryByTexture.get(key) || 0;
        this.currentMemoryBytes = Math.max(0, this.currentMemoryBytes - memoryBytes);
        
        // Remove from caches
        this.textureCache.delete(key);
        this.accessOrder.delete(key);
        this.memoryByTexture.delete(key);
        this.referenceCount.delete(key);
        this.pendingDisposal.delete(key);
    }
    
    /**
     * Calculate memory usage of a texture
     */
    calculateTextureMemory(texture) {
        if (!texture || !texture.baseTexture) return 0;
        
        const baseTexture = texture.baseTexture;
        // RGBA = 4 bytes per pixel
        return baseTexture.width * baseTexture.height * 4;
    }
    
    /**
     * Check if memory cleanup is needed
     */
    needsMemoryCleanup(additionalBytes = 0) {
        const totalBytes = this.currentMemoryBytes + additionalBytes;
        const maxBytes = this.maxMemoryMB * 1024 * 1024;
        return totalBytes > (maxBytes * this.cleanupThreshold);
    }
    
    /**
     * Perform memory cleanup using LRU strategy
     */
    performMemoryCleanup(targetBytes = 0) {
        console.log('🧹 Performing texture memory cleanup...');
        this.stats.memoryCleanups++;
        
        const maxBytes = this.maxMemoryMB * 1024 * 1024;
        const targetMemory = Math.max(maxBytes * 0.6, this.currentMemoryBytes - targetBytes);
        
        // Sort by last access time (LRU first)
        const sortedEntries = Array.from(this.accessOrder.entries())
            .sort((a, b) => a[1] - b[1]);
        
        let cleaned = 0;
        for (const [key] of sortedEntries) {
            if (this.currentMemoryBytes <= targetMemory) break;
            
            // Skip if texture has active references
            const refCount = this.referenceCount.get(key) || 0;
            if (refCount > 0) continue;
            
            this.disposeTexture(key);
            cleaned++;
        }
        
        console.log(`🧹 Cleaned ${cleaned} textures, memory: ${(this.currentMemoryBytes / 1024 / 1024).toFixed(1)}MB`);
    }
    
    /**
     * Enforce cache size limits
     */
    enforceCacheLimit() {
        if (this.textureCache.size <= this.maxCacheSize) return;
        
        const excessCount = this.textureCache.size - this.maxCacheSize;
        const sortedEntries = Array.from(this.accessOrder.entries())
            .sort((a, b) => a[1] - b[1]);
        
        for (let i = 0; i < excessCount; i++) {
            const [key] = sortedEntries[i];
            const refCount = this.referenceCount.get(key) || 0;
            
            // Only remove if no active references
            if (refCount <= 0) {
                this.disposeTexture(key);
            }
        }
    }
    
    /**
     * Update access time for LRU tracking
     */
    updateAccessTime(key) {
        this.accessOrder.set(key, ++this.accessCounter);
    }
    
    /**
     * Increment reference count
     */
    incrementReference(key) {
        const current = this.referenceCount.get(key) || 0;
        this.referenceCount.set(key, current + 1);
    }
    
    /**
     * Perform regular maintenance tasks
     */
    performMaintenance() {
        // Dispose pending textures
        const disposalList = Array.from(this.pendingDisposal);
        for (const key of disposalList) {
            const refCount = this.referenceCount.get(key) || 0;
            if (refCount <= 0) {
                this.disposeTexture(key);
            }
        }
        
        // Memory pressure check
        if (this.needsMemoryCleanup()) {
            this.performMemoryCleanup();
        }
        
        // Log stats periodically
        if (Math.random() < 0.1) { // 10% chance each maintenance cycle
            this.logStats();
        }
    }
    
    /**
     * Get current memory usage statistics
     */
    getMemoryStats() {
        return {
            currentMemoryMB: (this.currentMemoryBytes / 1024 / 1024).toFixed(1),
            maxMemoryMB: this.maxMemoryMB,
            utilization: ((this.currentMemoryBytes / (this.maxMemoryMB * 1024 * 1024)) * 100).toFixed(1),
            cachedTextures: this.textureCache.size,
            maxCacheSize: this.maxCacheSize,
            pooledSprites: this.spritePool.length,
            pooledAnimatedSprites: this.animatedSpritePool.length,
            pooledContainers: this.containerPool.length
        };
    }
    
    /**
     * Log performance statistics
     */
    logStats() {
        const memStats = this.getMemoryStats();
        console.log('📊 TexturePool Stats:', {
            ...memStats,
            cacheHitRate: `${((this.stats.cacheHits / (this.stats.cacheHits + this.stats.cacheMisses)) * 100).toFixed(1)}%`,
            performance: this.stats
        });
    }
    
    /**
     * Clear all cached textures and reset pool
     */
    clear() {
        console.log('🧹 Clearing texture pool...');
        
        // Dispose all textures
        for (const key of this.textureCache.keys()) {
            this.disposeTexture(key);
        }
        
        // Clear object pools
        this.spritePool.forEach(sprite => sprite.destroy());
        this.animatedSpritePool.forEach(sprite => sprite.destroy());
        this.containerPool.forEach(container => container.destroy());
        
        // Reset all collections
        this.textureCache.clear();
        this.accessOrder.clear();
        this.memoryByTexture.clear();
        this.referenceCount.clear();
        this.pendingDisposal.clear();
        this.spritePool = [];
        this.animatedSpritePool = [];
        this.containerPool = [];
        
        this.currentMemoryBytes = 0;
        this.accessCounter = 0;
        
        console.log('✅ TexturePool cleared');
    }
    
    /**
     * Shutdown and cleanup
     */
    destroy() {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }
        
        this.clear();
        console.log('🔚 TexturePool destroyed');
    }
}

// Global texture pool instance
export const globalTexturePool = new TexturePool({
    maxCacheSize: 150,
    maxMemoryMB: 512,
    cleanupThreshold: 0.75
});