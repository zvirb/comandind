import * as PIXI from "pixi.js";
import { TextureAtlasManager } from "../rendering/TextureAtlasManager.js";
import { CnCAssetLoader } from "../rendering/CnCAssetLoader.js";
import { globalTexturePool } from "../rendering/TexturePool.js";
import { initializeGPUMonitor } from "../utils/GPUMemoryMonitor.js";

/**
 * Texture Memory Optimization Demo
 * Demonstrates the usage of the new texture memory management system
 */
export class TextureOptimizationDemo {
    constructor() {
        this.app = null;
        this.atlasManager = null;
        this.assetLoader = null;
        this.gpuMonitor = null;
        this.sprites = [];
        this.isRunning = false;

        // Demo controls
        this.spawnRate = 2; // sprites per second
        this.maxSprites = 200;
        this.cleanupInterval = 10000; // 10 seconds
    }

    /**
     * Initialize the demo
     */
    async initialize() {
        console.log("🚀 Initializing Texture Optimization Demo...");

        // Create PIXI application
        this.app = new PIXI.Application({
            width: 1200,
            height: 800,
            backgroundColor: 0x1a1a2e,
            antialias: true,
            powerPreference: "high-performance"
        });

        // Append to DOM if running in browser
        if (typeof document !== "undefined") {
            document.body.appendChild(this.app.view);
        }

        // Initialize texture management systems
        this.atlasManager = new TextureAtlasManager();
        this.assetLoader = new CnCAssetLoader();
        this.gpuMonitor = initializeGPUMonitor(this.app.renderer);

        // Configure texture pool for demo
        globalTexturePool.maxCacheSize = 50;  // Smaller cache for demo
        globalTexturePool.maxMemoryMB = 128;  // Limited memory for testing
        globalTexturePool.cleanupThreshold = 0.7;

        // Load game data
        await this.assetLoader.loadGameData();

        // Preload critical textures
        await this.assetLoader.preloadCriticalTextures();

        // Setup memory pressure monitoring
        this.setupMemoryPressureHandling();

        // Create UI
        this.createUI();

        console.log("✅ Demo initialization complete");
    }

    /**
     * Setup memory pressure event handling
     */
    setupMemoryPressureHandling() {
        // Register for different pressure levels
        globalTexturePool.onMemoryPressure("medium", (pressure, level) => {
            console.log(`⚠️ Medium memory pressure: ${(pressure * 100).toFixed(1)}%`);
            this.updateUI(`Memory pressure: ${(pressure * 100).toFixed(1)}%`, "orange");
        });

        globalTexturePool.onMemoryPressure("high", (pressure, level) => {
            console.log(`🚨 High memory pressure: ${(pressure * 100).toFixed(1)}%`);
            this.updateUI(`HIGH memory pressure: ${(pressure * 100).toFixed(1)}%`, "red");

            // Trigger aggressive cleanup
            this.performCleanup();
        });
    }

    /**
     * Create simple UI for demo information
     */
    createUI() {
        // Create UI container
        this.ui = new PIXI.Container();
        this.app.stage.addChild(this.ui);

        // Background for UI
        const uiBackground = new PIXI.Graphics();
        uiBackground.beginFill(0x000000, 0.8);
        uiBackground.drawRect(10, 10, 400, 200);
        uiBackground.endFill();
        this.ui.addChild(uiBackground);

        // Title text
        const title = new PIXI.Text("Texture Memory Optimization Demo", {
            fontFamily: "Arial",
            fontSize: 18,
            fill: 0xffffff,
            fontWeight: "bold"
        });
        title.position.set(20, 20);
        this.ui.addChild(title);

        // Stats text
        this.statsText = new PIXI.Text("", {
            fontFamily: "Arial",
            fontSize: 12,
            fill: 0xaaaaaa
        });
        this.statsText.position.set(20, 50);
        this.ui.addChild(this.statsText);

        // Status text
        this.statusText = new PIXI.Text("Starting demo...", {
            fontFamily: "Arial",
            fontSize: 12,
            fill: 0x00ff00
        });
        this.statusText.position.set(20, 170);
        this.ui.addChild(this.statusText);

        // Instructions
        const instructions = new PIXI.Text(
            "Demo automatically spawns sprites and manages memory.\nWatch the stats to see optimization in action.",
            {
                fontFamily: "Arial",
                fontSize: 10,
                fill: 0xcccccc,
                wordWrap: true,
                wordWrapWidth: 380
            }
        );
        instructions.position.set(20, 190);
        this.ui.addChild(instructions);
    }

    /**
     * Update UI with current status
     */
    updateUI(status, color = "white") {
        if (!this.statusText) return;

        this.statusText.text = status;
        this.statusText.style.fill = color;
    }

    /**
     * Update stats display
     */
    updateStats() {
        if (!this.statsText) return;

        const poolStats = globalTexturePool.getMemoryStats();
        const assetStats = this.assetLoader.getMemoryStats();
        const gpuStats = this.gpuMonitor?.getDetailedStats();

        const stats = [
            `Active Sprites: ${this.sprites.length}`,
            `Texture Memory: ${poolStats.currentMemoryMB}MB / ${poolStats.maxMemoryMB}MB`,
            `Cache Hit Rate: ${((globalTexturePool.stats.cacheHits / Math.max(1, globalTexturePool.stats.cacheHits + globalTexturePool.stats.cacheMisses)) * 100).toFixed(1)}%`,
            `Pooled Objects: ${poolStats.pooledSprites + poolStats.pooledAnimatedSprites}`,
            `Memory Cleanups: ${globalTexturePool.stats.memoryCleanups}`,
            `GPU Textures: ${gpuStats?.current.activeTextures || "N/A"}`,
            `Utilization: ${poolStats.utilization}%`
        ];

        this.statsText.text = stats.join("\n");
    }

    /**
     * Spawn random sprites
     */
    async spawnSprite() {
        if (this.sprites.length >= this.maxSprites) {
            // Remove oldest sprite
            const oldSprite = this.sprites.shift();
            if (oldSprite) {
                this.app.stage.removeChild(oldSprite);
                this.assetLoader.returnSprite(oldSprite);
            }
        }

        // Get random unit or building
        const units = this.assetLoader.getAvailableUnits();
        const buildings = this.assetLoader.getAvailableBuildings();
        const allTypes = [...units, ...buildings];

        if (allTypes.length === 0) return;

        const randomType = allTypes[Math.floor(Math.random() * allTypes.length)];
        const isUnit = units.includes(randomType);

        try {
            const sprite = isUnit
                ? await this.assetLoader.createUnit(randomType)
                : await this.assetLoader.createBuilding(randomType);

            if (sprite) {
                // Random position
                sprite.x = Math.random() * (this.app.screen.width - 100) + 50;
                sprite.y = Math.random() * (this.app.screen.height - 150) + 100;

                // Random scale for visual variety
                const scale = 0.5 + Math.random() * 0.5;
                sprite.scale.set(scale);

                // Random rotation
                sprite.rotation = Math.random() * Math.PI * 2;

                this.sprites.push(sprite);
                this.app.stage.addChild(sprite);
            }
        } catch (error) {
            console.warn("Failed to create sprite:", error);
        }
    }

    /**
     * Perform memory cleanup
     */
    performCleanup() {
        console.log("🧹 Performing memory cleanup...");

        // Clean up asset loader
        const assetCleaned = this.assetLoader.performMemoryCleanup();

        // Clean up atlas manager
        const atlasCleaned = this.atlasManager.clearUnused();

        // Force texture pool maintenance
        globalTexturePool.performMaintenance();

        // Force GPU cleanup
        if (this.gpuMonitor) {
            this.gpuMonitor.forceGPUCleanup();
        }

        this.updateUI(`Cleanup complete: ${assetCleaned + atlasCleaned} items freed`, "green");

        setTimeout(() => {
            this.updateUI("Demo running...", "white");
        }, 3000);
    }

    /**
     * Start the demo animation loop
     */
    start() {
        if (this.isRunning) return;

        this.isRunning = true;

        console.log("▶️ Starting texture optimization demo...");
        this.updateUI("Demo running...", "white");

        // Sprite spawning loop
        this.spawnInterval = setInterval(() => {
            if (this.isRunning) {
                this.spawnSprite();
            }
        }, 1000 / this.spawnRate);

        // Stats update loop
        this.statsInterval = setInterval(() => {
            if (this.isRunning) {
                this.updateStats();
            }
        }, 1000);

        // Periodic cleanup
        this.cleanupTimer = setInterval(() => {
            if (this.isRunning) {
                this.performCleanup();
            }
        }, this.cleanupInterval);

        // Add simple animation to sprites
        this.app.ticker.add(this.animate, this);
    }

    /**
     * Stop the demo
     */
    stop() {
        if (!this.isRunning) return;

        this.isRunning = false;

        console.log("⏹️ Stopping demo...");

        // Clear intervals
        if (this.spawnInterval) clearInterval(this.spawnInterval);
        if (this.statsInterval) clearInterval(this.statsInterval);
        if (this.cleanupTimer) clearInterval(this.cleanupTimer);

        // Remove ticker
        this.app.ticker.remove(this.animate, this);

        this.updateUI("Demo stopped", "red");
    }

    /**
     * Simple animation for visual effect
     */
    animate(delta) {
        // Slowly rotate all sprites
        this.sprites.forEach(sprite => {
            sprite.rotation += 0.01 * delta;
        });
    }

    /**
     * Clean up and destroy demo
     */
    async destroy() {
        console.log("🔚 Destroying demo...");

        this.stop();

        // Remove all sprites
        this.sprites.forEach(sprite => {
            this.app.stage.removeChild(sprite);
            this.assetLoader.returnSprite(sprite);
        });
        this.sprites = [];

        // Destroy systems
        if (this.gpuMonitor) {
            this.gpuMonitor.destroy();
        }

        if (this.assetLoader) {
            this.assetLoader.destroy();
        }

        if (this.atlasManager) {
            this.atlasManager.destroy();
        }

        // Clear texture pool
        globalTexturePool.clear();

        // Destroy PIXI app
        if (this.app) {
            this.app.destroy(true, {
                children: true,
                texture: true,
                baseTexture: true
            });
        }

        console.log("✅ Demo destroyed");
    }

    /**
     * Get current demo statistics
     */
    getStats() {
        return {
            isRunning: this.isRunning,
            activeSprites: this.sprites.length,
            maxSprites: this.maxSprites,
            spawnRate: this.spawnRate,
            texturePool: globalTexturePool.getMemoryStats(),
            assetLoader: this.assetLoader?.getMemoryStats(),
            gpu: this.gpuMonitor?.getDetailedStats()
        };
    }
}

// Export convenience function for easy demo setup
export async function runTextureOptimizationDemo() {
    const demo = new TextureOptimizationDemo();

    try {
        await demo.initialize();
        demo.start();

        console.log("✅ Texture optimization demo is running!");
        console.log("📊 Check browser console for performance stats");

        return demo;
    } catch (error) {
        console.error("❌ Failed to start demo:", error);
        await demo.destroy();
        throw error;
    }
}
