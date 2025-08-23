import * as PIXI from 'pixi.js';
import { TextureAtlasManager } from '../rendering/TextureAtlasManager.js';
import { CnCAssetLoader } from '../rendering/CnCAssetLoader.js';
import { globalTexturePool } from '../rendering/TexturePool.js';
import { GPUMemoryMonitor } from './GPUMemoryMonitor.js';

/**
 * Texture Memory Performance Test
 * Validates the effectiveness of texture pooling, LRU cache, and memory management
 */
export class TextureMemoryTest {
    constructor() {
        this.app = null;
        this.atlasManager = null;
        this.assetLoader = null;
        this.gpuMonitor = null;
        this.testResults = [];
        this.sprites = [];
    }
    
    /**
     * Initialize PIXI application for testing
     */
    async initializePIXI() {
        // Create PIXI application
        this.app = new PIXI.Application({
            width: 800,
            height: 600,
            backgroundColor: 0x1099bb,
            antialias: true
        });

        // Initialize managers
        this.atlasManager = new TextureAtlasManager();
        this.assetLoader = new CnCAssetLoader();
        this.gpuMonitor = new GPUMemoryMonitor(this.app.renderer);

        // Load game data
        await this.assetLoader.loadGameData();

        console.log('✅ PIXI Test Environment Initialized');
    }

    /**
     * Test 1: Basic texture pooling efficiency
     */
    async testTexturePooling() {
        console.log('🧪 Testing Texture Pooling...');

        const startTime = performance.now();
        const startMemory = globalTexturePool.getMemoryStats();

        // Create multiple sprites using the same texture
        const textureKey = 'unit_GDI_MEDIUM_TANK';
        const sprites = [];

        for (let i = 0; i < 100; i++) {
            const sprite = await this.assetLoader.createUnit('GDI_MEDIUM_TANK', i * 10, i * 10);
            if (sprite) {
                sprites.push(sprite);
                this.app.stage.addChild(sprite);
            }
        }

        const endTime = performance.now();
        const endMemory = globalTexturePool.getMemoryStats();

        const result = {
            test: 'Texture Pooling',
            duration: `${(endTime - startTime).toFixed(2)}ms`,
            spritesCreated: sprites.length,
            cacheHitRate: endMemory.cacheHitRate || 'N/A',
            memoryUsed: `${endMemory.currentMemoryMB}MB`,
            pooledObjects: endMemory.pooledSprites + endMemory.pooledAnimatedSprites
        };

        this.testResults.push(result);
        console.log('📊 Texture Pooling Results:', result);

        // Clean up
        sprites.forEach(sprite => {
            this.app.stage.removeChild(sprite);
            this.assetLoader.returnSprite(sprite);
        });

        return result;
    }

    /**
     * Test 2: Memory pressure and cleanup
     */
    async testMemoryPressure() {
        console.log('🧪 Testing Memory Pressure Management...');

        const startStats = globalTexturePool.getMemoryStats();
        const sprites = [];

        // Create many different textures to trigger memory pressure
        const unitTypes = this.assetLoader.getAvailableUnits();
        const buildingTypes = this.assetLoader.getAvailableBuildings();

        // Load many textures
        for (let i = 0; i < Math.min(50, unitTypes.length); i++) {
            const sprite = await this.assetLoader.createUnit(unitTypes[i], i * 5, i * 5);
            if (sprite) {
                sprites.push(sprite);
                this.app.stage.addChild(sprite);
            }
        }

        for (let i = 0; i < Math.min(20, buildingTypes.length); i++) {
            const sprite = await this.assetLoader.createBuilding(buildingTypes[i], i * 10, 300 + i * 10);
            if (sprite) {
                sprites.push(sprite);
                this.app.stage.addChild(sprite);
            }
        }

        const beforeCleanupStats = globalTexturePool.getMemoryStats();

        // Trigger cleanup
        globalTexturePool.performMaintenance();
        this.atlasManager.performSmartCleanup();
        this.assetLoader.performMemoryCleanup();

        const afterCleanupStats = globalTexturePool.getMemoryStats();

        const result = {
            test: 'Memory Pressure',
            spritesCreated: sprites.length,
            beforeCleanup: `${beforeCleanupStats.currentMemoryMB}MB`,
            afterCleanup: `${afterCleanupStats.currentMemoryMB}MB`,
            memorySaved: `${(parseFloat(beforeCleanupStats.currentMemoryMB) - parseFloat(afterCleanupStats.currentMemoryMB)).toFixed(1)}MB`,
            cleanupEfficiency: `${((parseFloat(beforeCleanupStats.currentMemoryMB) - parseFloat(afterCleanupStats.currentMemoryMB)) / parseFloat(beforeCleanupStats.currentMemoryMB) * 100).toFixed(1)}%`
        };

        this.testResults.push(result);
        console.log('📊 Memory Pressure Results:', result);

        // Clean up
        sprites.forEach(sprite => {
            this.app.stage.removeChild(sprite);
            this.assetLoader.returnSprite(sprite);
        });

        return result;
    }

    /**
     * Test 3: GPU memory monitoring
     */
    async testGPUMonitoring() {
        console.log('🧪 Testing GPU Memory Monitoring...');

        // Initialize GPU monitoring
        this.gpuMonitor.startMonitoring(1000);

        // Create memory pressure
        const sprites = [];
        for (let i = 0; i < 50; i++) {
            const sprite = this.atlasManager.createAnimatedSprite('gdi-medium-tank', 'move');
            if (sprite) {
                sprite.x = Math.random() * 700;
                sprite.y = Math.random() * 500;
                sprites.push(sprite);
                this.app.stage.addChild(sprite);
            }
        }

        // Wait for monitoring to collect data
        await new Promise(resolve => setTimeout(resolve, 2000));

        const gpuStats = this.gpuMonitor.getDetailedStats();
        const trends = this.gpuMonitor.getPerformanceTrends();

        const result = {
            test: 'GPU Monitoring',
            gpuVendor: gpuStats.gpu.vendor,
            gpuRenderer: gpuStats.gpu.renderer,
            textureMemory: gpuStats.current.textureMemoryMB + 'MB',
            activeTextures: gpuStats.current.activeTextures,
            memoryPressure: gpuStats.current.memoryPressure,
            trends: trends,
            webGLVersion: gpuStats.gpu.webGLVersion
        };

        this.testResults.push(result);
        console.log('📊 GPU Monitoring Results:', result);

        // Clean up
        sprites.forEach(sprite => {
            this.app.stage.removeChild(sprite);
            globalTexturePool.returnSprite(sprite);
        });

        this.gpuMonitor.stopMonitoring();

        return result;
    }

    /**
     * Test 4: LRU cache effectiveness
     */
    async testLRUCache() {
        console.log('🧪 Testing LRU Cache...');

        const cacheSize = 20;
        const testIterations = 50;

        // Configure smaller cache for testing
        const oldMaxCacheSize = globalTexturePool.maxCacheSize;
        globalTexturePool.maxCacheSize = cacheSize;

        const startStats = globalTexturePool.getMemoryStats();

        // Access textures in patterns to test LRU
        const unitTypes = this.assetLoader.getAvailableUnits().slice(0, 30); // More than cache size

        for (let i = 0; i < testIterations; i++) {
            const unitType = unitTypes[i % unitTypes.length];
            const sprite = await this.assetLoader.createUnit(unitType, 0, 0);
            if (sprite) {
                this.assetLoader.returnSprite(sprite);
            }
        }

        const endStats = globalTexturePool.getMemoryStats();

        const result = {
            test: 'LRU Cache',
            cacheSize: cacheSize,
            testIterations: testIterations,
            uniqueTextures: unitTypes.length,
            cacheHitRate: `${((globalTexturePool.stats.cacheHits / (globalTexturePool.stats.cacheHits + globalTexturePool.stats.cacheMisses)) * 100).toFixed(1)}%`,
            finalCachedTextures: endStats.cachedTextures,
            memoryCleanups: globalTexturePool.stats.memoryCleanups
        };

        this.testResults.push(result);
        console.log('📊 LRU Cache Results:', result);

        // Restore original cache size
        globalTexturePool.maxCacheSize = oldMaxCacheSize;

        return result;
    }

    /**
     * Run all tests and generate report
     */
    async runAllTests() {
        console.log('🚀 Starting Texture Memory Optimization Tests...');

        try {
            await this.initializePIXI();

            // Run tests in sequence
            await this.testTexturePooling();
            await this.testMemoryPressure();
            await this.testGPUMonitoring();
            await this.testLRUCache();

            // Generate final report
            const report = this.generateReport();
            console.log('📋 Final Test Report:', report);

            return report;

        } catch (error) {
            console.error('❌ Test execution failed:', error);
            throw error;
        } finally {
            await this.cleanup();
        }
    }

    /**
     * Generate comprehensive test report
     */
    generateReport() {
        const poolStats = globalTexturePool.getMemoryStats();
        const assetStats = this.assetLoader.getMemoryStats();

        return {
            timestamp: new Date().toISOString(),
            testResults: this.testResults,
            finalStats: {
                texturePool: poolStats,
                assetLoader: assetStats
            },
            performance: {
                totalCacheHits: globalTexturePool.stats.cacheHits,
                totalCacheMisses: globalTexturePool.stats.cacheMisses,
                totalCleanups: globalTexturePool.stats.memoryCleanups,
                objectsPooled: globalTexturePool.stats.objectsPooled,
                texturesDisposed: globalTexturePool.stats.texturesDisposed
            },
            conclusions: this.generateConclusions()
        };
    }

    /**
     * Generate test conclusions
     */
    generateConclusions() {
        const cacheHitRate = globalTexturePool.stats.cacheHits /
            Math.max(1, globalTexturePool.stats.cacheHits + globalTexturePool.stats.cacheMisses);

        return {
            texturePoolingEffective: cacheHitRate > 0.7,
            memoryManagementActive: globalTexturePool.stats.memoryCleanups > 0,
            objectPoolingWorking: globalTexturePool.stats.objectsPooled > 0,
            overallRating: this.calculateOverallRating(cacheHitRate)
        };
    }

    /**
     * Calculate overall optimization rating
     */
    calculateOverallRating(cacheHitRate) {
        let score = 0;

        // Cache hit rate (40% of score)
        score += cacheHitRate * 0.4;

        // Memory cleanup activity (30% of score)
        if (globalTexturePool.stats.memoryCleanups > 0) score += 0.3;

        // Object pooling usage (30% of score)
        if (globalTexturePool.stats.objectsPooled > 0) score += 0.3;

        if (score >= 0.9) return 'Excellent';
        if (score >= 0.7) return 'Good';
        if (score >= 0.5) return 'Fair';
        return 'Needs Improvement';
    }

    /**
     * Clean up test resources
     */
    async cleanup() {
        console.log('🧹 Cleaning up test resources...');

        if (this.app) {
            this.app.stage.removeChildren();
        }

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

        console.log('✅ Test cleanup completed');
    }
}

// Export test runner function for easy use
export async function runTextureMemoryTest() {
    const test = new TextureMemoryTest();
    return await test.runAllTests();
}
