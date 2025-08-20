import * as PIXI from "pixi.js";
import { globalTexturePool } from "./TexturePool.js";

/**
 * C&C Asset Loader - Integrates authentic C&C data with placeholder graphics
 * Loads unit stats, building data, and game rules from GitHub extraction
 */
export class CnCAssetLoader {
    constructor() {
        this.unitData = null;
        this.buildingData = null;
        this.gameRules = null;
        this.textures = new Map();
        
        // Memory management integration
        this.texturePool = globalTexturePool;
        this.lazyLoadQueue = new Map();
        this.textureUsageStats = new Map();
        this.maxConcurrentLoads = 3;
        this.currentLoads = 0;
        this.priorityTextures = new Set(); // High-priority textures to keep in memory
        
        // Placeholder colors for different factions/types
        this.placeholderColors = {
            gdi: {
                structures: "#0066ff",
                units: "#0088ff",
                power: "#00aa00"
            },
            nod: {
                structures: "#ff0000",
                units: "#ff4400",
                power: "#ff6600"
            },
            neutral: {
                tiberium: "#00ff00",
                terrain: "#ffdd88"
            }
        };
    }
    
    /**
     * Load all C&C game data
     */
    async loadGameData() {
        console.log("🎮 Loading C&C Game Data...");
        
        try {
            // Load extracted game data from public directory
            // Note: Files in /public are served from root in Vite
            const urls = [
                "/assets/cnc-data/units.json",
                "/assets/cnc-data/buildings.json",
                "/assets/cnc-data/rules.json"
            ];
            
            console.log("Fetching game data from:", urls);
            
            const [unitsResponse, buildingsResponse, rulesResponse] = await Promise.all([
                fetch(urls[0]),
                fetch(urls[1]),
                fetch(urls[2])
            ]);
            
            // Check if responses are ok
            if (!unitsResponse.ok) throw new Error(`Failed to load units.json: ${unitsResponse.status}`);
            if (!buildingsResponse.ok) throw new Error(`Failed to load buildings.json: ${buildingsResponse.status}`);
            if (!rulesResponse.ok) throw new Error(`Failed to load rules.json: ${rulesResponse.status}`);
            
            this.unitData = await unitsResponse.json();
            this.buildingData = await buildingsResponse.json();
            this.gameRules = await rulesResponse.json();
            
            console.log("✅ Game data loaded successfully");
            console.log(`   - ${Object.keys(this.unitData).length} unit types`);
            console.log(`   - ${Object.keys(this.buildingData).length} building types`);
            
            // NOTE: Placeholder textures are now deprecated.
            // Sprites are loaded via TextureAtlasManager.
            
            return true;
        } catch (error) {
            console.warn("⚠️ Failed to load game data, using defaults:", error.message);
            
            // Use default data if loading fails
            this.unitData = { DEFAULT_UNIT: { name: "Default Unit", health: 100, speed: 10 } };
            this.buildingData = { DEFAULT_BUILDING: { name: "Default Building", health: 500 } };
            this.gameRules = { defaultSpeed: 1.0 };
            
            // Still generate placeholder textures
            this.generatePlaceholderTextures();
            
            // Return true to allow game to continue with defaults
            return true;
        }
    }
    
    /**
     * Generate placeholder textures with memory optimization
     */
    generatePlaceholderTextures() {
        console.log("🎨 Generating optimized placeholder textures...");
        
        const batchSize = 10;
        const unitKeys = Object.entries(this.unitData);
        const buildingKeys = Object.entries(this.buildingData);
        
        // Process units in batches to prevent memory spikes
        this.processBatches(unitKeys, batchSize, ([unitKey, unitInfo]) => {
            const faction = (unitInfo.faction || "neutral").toLowerCase();
            const textureKey = `unit_${unitKey}`;
            
            const texture = this.texturePool.getTexture(textureKey, () => {
                return this.createPlaceholderTexture(
                    unitKey.includes("MAMMOTH") ? 32 : 24,
                    unitKey.includes("MAMMOTH") ? 32 : 24,
                    this.placeholderColors[faction]?.units || "#666666",
                    unitInfo.name
                );
            });
            
            this.textures.set(textureKey, texture);
            this.trackTextureUsage(textureKey, {
                type: "unit",
                faction,
                priority: this.getTexturePriority(unitKey, "unit"),
                memoryBytes: this.texturePool.calculateTextureMemory(texture)
            });
        });
        
        // Process buildings in batches
        this.processBatches(buildingKeys, batchSize, ([buildingKey, buildingInfo]) => {
            let width = 48, height = 48;
            
            // Special sizes for certain buildings
            if (buildingKey.includes("REFINERY")) {
                width = 72;
            }
            if (buildingKey.includes("OBELISK")) {
                width = 24;
                height = 48;
            }
            
            const faction = (buildingInfo.faction || "neutral").toLowerCase();
            const textureKey = `building_${buildingKey}`;
            
            const texture = this.texturePool.getTexture(textureKey, () => {
                return this.createPlaceholderTexture(
                    width,
                    height,
                    this.placeholderColors[faction]?.structures || "#666666",
                    buildingInfo.name
                );
            });
            
            this.textures.set(textureKey, texture);
            this.trackTextureUsage(textureKey, {
                type: "building",
                faction,
                priority: this.getTexturePriority(buildingKey, "building"),
                memoryBytes: this.texturePool.calculateTextureMemory(texture)
            });
            
            // Mark core buildings as high priority
            if (buildingKey.includes("CONSTRUCTION_YARD") || buildingKey.includes("POWER")) {
                this.priorityTextures.add(textureKey);
            }
        });
        
        // Generate resource placeholders
        const tiberiumKey = "tiberium_green";
        const tiberiumTexture = this.texturePool.getTexture(tiberiumKey, () => {
            return this.createPlaceholderTexture(
                24, 24,
                this.placeholderColors.neutral.tiberium,
                "TIB"
            );
        });
        this.textures.set(tiberiumKey, tiberiumTexture);
        this.priorityTextures.add(tiberiumKey);
        
        console.log(`✅ Generated ${this.textures.size} optimized placeholder textures`);
        console.log(`📊 Memory usage: ${(this.getCurrentMemoryUsage() / 1024 / 1024).toFixed(1)}MB`);
    }
    
    /**
     * Create a colored rectangle placeholder texture
     */
    createPlaceholderTexture(width, height, color, label) {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        
        // Fill with faction color
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, width, height);
        
        // Add border
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, width, height);
        
        // Add text label
        ctx.fillStyle = "#ffffff";
        ctx.font = `${Math.min(width/6, 8)}px Arial`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        
        // Truncate label to fit
        const maxChars = Math.floor(width / 6);
        const displayLabel = label.length > maxChars ? label.substring(0, maxChars) : label;
        ctx.fillText(displayLabel, width/2, height/2);
        
        // Convert to PIXI texture
        return PIXI.Texture.from(canvas);
    }
    
    /**
     * Get unit information by key
     */
    getUnitInfo(unitKey) {
        return this.unitData[unitKey] || null;
    }
    
    /**
     * Get building information by key
     */
    getBuildingInfo(buildingKey) {
        return this.buildingData[buildingKey] || null;
    }
    
    /**
     * Get texture by key with lazy loading and usage tracking
     */
    async getTexture(key, priority = 1) {
        // Check cache first
        let texture = this.textures.get(key);
        
        if (texture) {
            this.updateTextureUsage(key);
            return texture;
        }
        
        // Check if it's in lazy load queue
        if (this.lazyLoadQueue.has(key)) {
            const loadPromise = this.lazyLoadQueue.get(key);
            texture = await loadPromise;
            return texture;
        }
        
        // Lazy load if not found
        return await this.lazyLoadTexture(key, priority);
    }
    
    /**
     * Lazy load texture with memory management
     */
    async lazyLoadTexture(key, priority = 1) {
        if (this.currentLoads >= this.maxConcurrentLoads) {
            // Wait for a slot to become available
            await this.waitForLoadSlot();
        }
        
        this.currentLoads++;
        
        const loadPromise = this.performLazyLoad(key, priority)
            .finally(() => {
                this.currentLoads--;
                this.lazyLoadQueue.delete(key);
            });
        
        this.lazyLoadQueue.set(key, loadPromise);
        return await loadPromise;
    }
    
    /**
     * Perform the actual lazy loading
     */
    async performLazyLoad(key, priority) {
        // Try to regenerate placeholder if it's a known type
        if (key.startsWith("unit_") || key.startsWith("building_")) {
            const type = key.split("_")[0];
            const entityKey = key.substring(type.length + 1);
            
            let entityInfo, color, dimensions;
            
            if (type === "unit" && this.unitData[entityKey]) {
                entityInfo = this.unitData[entityKey];
                const faction = (entityInfo.faction || "neutral").toLowerCase();
                color = this.placeholderColors[faction]?.units || "#666666";
                dimensions = entityKey.includes("MAMMOTH") ? [32, 32] : [24, 24];
            } else if (type === "building" && this.buildingData[entityKey]) {
                entityInfo = this.buildingData[entityKey];
                const faction = (entityInfo.faction || "neutral").toLowerCase();
                color = this.placeholderColors[faction]?.structures || "#666666";
                dimensions = [48, 48];
                
                if (entityKey.includes("REFINERY")) dimensions = [72, 48];
                if (entityKey.includes("OBELISK")) dimensions = [24, 48];
            }
            
            if (entityInfo) {
                const texture = this.texturePool.getTexture(key, () => {
                    return this.createPlaceholderTexture(
                        dimensions[0], dimensions[1], color, entityInfo.name
                    );
                });
                
                this.textures.set(key, texture);
                this.trackTextureUsage(key, {
                    type,
                    priority,
                    memoryBytes: this.texturePool.calculateTextureMemory(texture),
                    lazyLoaded: true
                });
                
                return texture;
            }
        }
        
        console.warn(`❌ Could not lazy load texture: ${key}`);
        return null;
    }
    
    /**
     * Wait for a load slot to become available
     */
    async waitForLoadSlot() {
        return new Promise(resolve => {
            const checkSlot = () => {
                if (this.currentLoads < this.maxConcurrentLoads) {
                    resolve();
                } else {
                    setTimeout(checkSlot, 10);
                }
            };
            checkSlot();
        });
    }
    
    /**
     * Original getTexture method (synchronous)
     */
    getTextureSync(key) {
        const texture = this.textures.get(key);
        if (texture) {
            this.updateTextureUsage(key);
        }
        return texture || null;
    }
    
    /**
     * Create a unit sprite with authentic stats using texture pool
     */
    async createUnit(unitKey, x = 0, y = 0) {
        const unitInfo = this.getUnitInfo(unitKey);
        const texture = await this.getTexture(`unit_${unitKey}`, this.getTexturePriority(unitKey, "unit"));
        
        if (!unitInfo || !texture) {
            console.warn(`Unit '${unitKey}' not found`);
            return null;
        }
        
        // Use texture pool for sprite creation
        const sprite = this.texturePool.getSprite(texture);
        sprite.x = x;
        sprite.y = y;
        sprite.anchor.set(0.5);
        
        // Add authentic C&C properties
        sprite.unitData = {
            ...unitInfo,
            currentHealth: unitInfo.health,
            facing: 0, // 0-31 for 32 directions
            selected: false,
            moving: false,
            textureKey: `unit_${unitKey}` // Track texture for cleanup
        };
        
        return sprite;
    }
    
    /**
     * Synchronous unit creation for backward compatibility
     */
    createUnitSync(unitKey, x = 0, y = 0) {
        const unitInfo = this.getUnitInfo(unitKey);
        const texture = this.getTextureSync(`unit_${unitKey}`);
        
        if (!unitInfo || !texture) {
            console.warn(`Unit '${unitKey}' not found`);
            return null;
        }
        
        const sprite = this.texturePool.getSprite(texture);
        sprite.x = x;
        sprite.y = y;
        sprite.anchor.set(0.5);
        
        sprite.unitData = {
            ...unitInfo,
            currentHealth: unitInfo.health,
            facing: 0,
            selected: false,
            moving: false,
            textureKey: `unit_${unitKey}`
        };
        
        return sprite;
    }
    
    /**
     * Create a building sprite with authentic stats using texture pool
     */
    async createBuilding(buildingKey, x = 0, y = 0) {
        const buildingInfo = this.getBuildingInfo(buildingKey);
        const texture = await this.getTexture(`building_${buildingKey}`, this.getTexturePriority(buildingKey, "building"));
        
        if (!buildingInfo || !texture) {
            console.warn(`Building '${buildingKey}' not found`);
            return null;
        }
        
        // Use texture pool for sprite creation
        const sprite = this.texturePool.getSprite(texture);
        sprite.x = x;
        sprite.y = y;
        sprite.anchor.set(0.5);
        
        // Add authentic C&C properties
        sprite.buildingData = {
            ...buildingInfo,
            currentHealth: buildingInfo.health,
            powerOutput: buildingInfo.power || 0,
            active: true,
            constructing: false,
            textureKey: `building_${buildingKey}`
        };
        
        return sprite;
    }
    
    /**
     * Synchronous building creation for backward compatibility
     */
    createBuildingSync(buildingKey, x = 0, y = 0) {
        const buildingInfo = this.getBuildingInfo(buildingKey);
        const texture = this.getTextureSync(`building_${buildingKey}`);
        
        if (!buildingInfo || !texture) {
            console.warn(`Building '${buildingKey}' not found`);
            return null;
        }
        
        const sprite = this.texturePool.getSprite(texture);
        sprite.x = x;
        sprite.y = y;
        sprite.anchor.set(0.5);
        
        sprite.buildingData = {
            ...buildingInfo,
            currentHealth: buildingInfo.health,
            powerOutput: buildingInfo.power || 0,
            active: true,
            constructing: false,
            textureKey: `building_${buildingKey}`
        };
        
        return sprite;
    }
    
    /**
     * Get all available units
     */
    getAvailableUnits() {
        return Object.keys(this.unitData || {});
    }
    
    /**
     * Get all available buildings
     */
    getAvailableBuildings() {
        return Object.keys(this.buildingData || {});
    }
    
    /**
     * Get units by faction
     */
    getUnitsByFaction(faction) {
        if (!this.unitData) return [];
        
        return Object.entries(this.unitData)
            .filter(([key, unit]) => (unit.faction || "").toLowerCase() === faction.toLowerCase())
            .map(([key, unit]) => ({ key, ...unit }));
    }
    
    /**
     * Get buildings by faction
     */
    getBuildingsByFaction(faction) {
        if (!this.buildingData) return [];
        
        return Object.entries(this.buildingData)
            .filter(([key, building]) => (building.faction || "").toLowerCase() === faction.toLowerCase())
            .map(([key, building]) => ({ key, ...building }));
    }
    
    /**
     * Process items in batches to prevent memory spikes
     */
    processBatches(items, batchSize, processFn) {
        for (let i = 0; i < items.length; i += batchSize) {
            const batch = items.slice(i, i + batchSize);
            batch.forEach(processFn);
            
            // Small delay between batches to prevent blocking
            if (i + batchSize < items.length) {
                setTimeout(() => {}, 0);
            }
        }
    }
    
    /**
     * Get texture priority based on type and key
     */
    getTexturePriority(entityKey, type) {
        // High priority for core game elements
        if (type === "building") {
            if (entityKey.includes("CONSTRUCTION_YARD")) return 10;
            if (entityKey.includes("POWER")) return 9;
            if (entityKey.includes("BARRACKS")) return 8;
            if (entityKey.includes("REFINERY")) return 8;
            return 5;
        }
        
        if (type === "unit") {
            if (entityKey.includes("INFANTRY")) return 7;
            if (entityKey.includes("TANK")) return 6;
            if (entityKey.includes("MAMMOTH")) return 5;
            return 4;
        }
        
        return 3;
    }
    
    /**
     * Track texture usage for memory optimization
     */
    trackTextureUsage(key, stats) {
        this.textureUsageStats.set(key, {
            ...stats,
            createdAt: Date.now(),
            lastAccessed: Date.now(),
            accessCount: 0
        });
    }
    
    /**
     * Update texture usage statistics
     */
    updateTextureUsage(key) {
        const stats = this.textureUsageStats.get(key);
        if (stats) {
            stats.lastAccessed = Date.now();
            stats.accessCount++;
        }
    }
    
    /**
     * Get current memory usage of all textures
     */
    getCurrentMemoryUsage() {
        let totalBytes = 0;
        for (const stats of this.textureUsageStats.values()) {
            totalBytes += stats.memoryBytes || 0;
        }
        return totalBytes;
    }
    
    /**
     * Return sprite to texture pool
     */
    returnSprite(sprite) {
        if (!sprite) return;
        
        // Release texture reference if tracked
        if (sprite.unitData?.textureKey) {
            this.texturePool.releaseTexture(sprite.unitData.textureKey);
        }
        if (sprite.buildingData?.textureKey) {
            this.texturePool.releaseTexture(sprite.buildingData.textureKey);
        }
        
        // Return sprite to pool
        this.texturePool.returnSprite(sprite);
    }
    
    /**
     * Preload high-priority textures
     */
    async preloadCriticalTextures() {
        console.log("🚀 Preloading critical textures...");
        
        const criticalTextures = [];
        
        // Core buildings for both factions
        const coreBuildings = [
            "GDI_CONSTRUCTION_YARD",
            "NOD_CONSTRUCTION_YARD",
            "GDI_POWER_PLANT",
            "NOD_POWER_PLANT",
            "GDI_BARRACKS",
            "NOD_BARRACKS"
        ];
        
        const coreUnits = [
            "GDI_MINIGUNNER",
            "NOD_MINIGUNNER",
            "GDI_MEDIUM_TANK",
            "NOD_LIGHT_TANK"
        ];
        
        // Load core buildings
        for (const buildingKey of coreBuildings) {
            if (this.buildingData[buildingKey]) {
                criticalTextures.push(this.getTexture(`building_${buildingKey}`, 10));
            }
        }
        
        // Load core units
        for (const unitKey of coreUnits) {
            if (this.unitData[unitKey]) {
                criticalTextures.push(this.getTexture(`unit_${unitKey}`, 8));
            }
        }
        
        // Load resource textures
        criticalTextures.push(this.getTexture("tiberium_green", 9));
        
        await Promise.all(criticalTextures);
        console.log("✅ Critical textures preloaded");
    }
    
    /**
     * Perform memory cleanup
     */
    performMemoryCleanup() {
        console.log("🧹 Performing asset loader memory cleanup...");
        
        const now = Date.now();
        const maxIdleTime = 300000; // 5 minutes
        let cleaned = 0;
        
        // Clean up unused textures
        for (const [key, stats] of this.textureUsageStats.entries()) {
            const idleTime = now - stats.lastAccessed;
            const isLowPriority = stats.priority < 5;
            const isLowUsage = stats.accessCount < 3;
            
            // Skip priority textures
            if (this.priorityTextures.has(key)) continue;
            
            if (idleTime > maxIdleTime && (isLowPriority || isLowUsage)) {
                // Release from texture pool
                this.texturePool.releaseTexture(key);
                
                // Remove from our cache
                this.textures.delete(key);
                this.textureUsageStats.delete(key);
                
                cleaned++;
            }
        }
        
        // Trigger texture pool cleanup
        this.texturePool.performMaintenance();
        
        console.log(`🧹 Cleaned ${cleaned} unused asset textures`);
        return cleaned;
    }
    
    /**
     * Get comprehensive memory statistics
     */
    getMemoryStats() {
        const poolStats = this.texturePool.getMemoryStats();
        const assetMemory = this.getCurrentMemoryUsage();
        
        return {
            assetLoader: {
                totalTextures: this.textures.size,
                memoryMB: (assetMemory / 1024 / 1024).toFixed(1),
                priorityTextures: this.priorityTextures.size,
                lazyLoadQueue: this.lazyLoadQueue.size,
                currentLoads: this.currentLoads,
                usageStats: {
                    avgAccessCount: this.textureUsageStats.size > 0 ?
                        Array.from(this.textureUsageStats.values())
                            .reduce((sum, s) => sum + s.accessCount, 0) / this.textureUsageStats.size : 0,
                    totalAccesses: Array.from(this.textureUsageStats.values())
                        .reduce((sum, s) => sum + s.accessCount, 0)
                }
            },
            texturePool: poolStats
        };
    }
    
    /**
     * Destroy asset loader and clean up all resources
     */
    destroy() {
        console.log("🔚 Destroying CnCAssetLoader...");
        
        // Clean up all textures
        for (const key of this.textures.keys()) {
            this.texturePool.releaseTexture(key);
        }
        
        // Clear all collections
        this.textures.clear();
        this.textureUsageStats.clear();
        this.lazyLoadQueue.clear();
        this.priorityTextures.clear();
        
        // Clear data
        this.unitData = null;
        this.buildingData = null;
        this.gameRules = null;
        
        console.log("✅ CnCAssetLoader destroyed");
    }
}