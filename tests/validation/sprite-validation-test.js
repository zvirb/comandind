// Comprehensive Sprite Validation Test
import { TextureAtlasManager } from './src/rendering/TextureAtlasManager.js';

class SpriteValidationTest {
    constructor() {
        this.atlasManager = new TextureAtlasManager();
        this.results = {
            totalSprites: 0,
            successfulLoads: 0,
            failedLoads: 0,
            spriteDetails: [],
            performanceMetrics: {},
            errors: []
        };
        this.startTime = performance.now();
    }
    
    async runComprehensiveValidation() {
        console.log('🚀 Starting comprehensive sprite validation...');
        
        try {
            // Initialize TextureAtlasManager with sprite configs
            await this.atlasManager.initialize();
            
            // Get all configured sprites
            const spriteConfigs = this.atlasManager.spriteConfigs;
            if (!spriteConfigs || Object.keys(spriteConfigs).length === 0) {
                throw new Error('No sprite configurations found');
            }
            
            console.log(`📋 Found ${Object.keys(spriteConfigs).length} sprite configurations`);
            this.results.totalSprites = Object.keys(spriteConfigs).length;
            
            // Test each sprite loading
            for (const [spriteKey, config] of Object.entries(spriteConfigs)) {
                await this.testSpriteLoading(spriteKey, config);
            }
            
            // Test TextureAtlasManager integration
            await this.testTextureAtlasIntegration();
            
            // Performance benchmarking
            await this.performanceBenchmarking();
            
            // Memory usage analysis
            this.analyzeMemoryUsage();
            
            // Generate validation report
            this.generateValidationReport();
            
        } catch (error) {
            console.error('❌ Validation failed:', error);
            this.results.errors.push({
                type: 'CRITICAL_ERROR',
                message: error.message,
                stack: error.stack
            });
        }
    }
    
    async testSpriteLoading(spriteKey, config) {
        const testStart = performance.now();
        
        try {
            console.log(`🔍 Testing sprite: ${spriteKey}`);
            
            // Test HTTP accessibility first
            const response = await fetch(config.url);
            const httpStatus = response.ok;
            
            if (!httpStatus) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Test TextureAtlasManager loading
            const atlas = await this.atlasManager.loadSpriteSet(spriteKey);
            
            const testEnd = performance.now();
            const loadTime = testEnd - testStart;
            
            this.results.successfulLoads++;
            this.results.spriteDetails.push({
                spriteKey,
                url: config.url,
                status: 'SUCCESS',
                loadTime: loadTime.toFixed(2) + 'ms',
                httpStatus: response.status,
                contentLength: response.headers.get('content-length') || 'unknown',
                atlas: atlas ? 'loaded' : 'null'
            });
            
            console.log(`✅ ${spriteKey}: loaded in ${loadTime.toFixed(2)}ms`);
            
        } catch (error) {
            this.results.failedLoads++;
            this.results.spriteDetails.push({
                spriteKey,
                url: config.url,
                status: 'FAILED',
                error: error.message
            });
            
            this.results.errors.push({
                type: 'SPRITE_LOAD_ERROR',
                spriteKey,
                url: config.url,
                message: error.message
            });
            
            console.error(`❌ ${spriteKey}: ${error.message}`);
        }
    }
    
    async testTextureAtlasIntegration() {
        console.log('🔧 Testing TextureAtlasManager integration...');
        
        try {
            // Test sprite creation
            const testSprites = [
                'gdi-construction-yard',
                'nod-obelisk-of-light',
                'gdi-medium-tank',
                'tiberium-green'
            ];
            
            for (const spriteKey of testSprites) {
                if (this.atlasManager.spriteConfigs[spriteKey]) {
                    // Test animated sprite creation
                    const config = this.atlasManager.spriteConfigs[spriteKey];
                    const animations = config.animations || {};
                    
                    for (const animationName of Object.keys(animations)) {
                        try {
                            const sprite = this.atlasManager.createAnimatedSprite(spriteKey, animationName);
                            if (sprite) {
                                console.log(`✅ Created sprite: ${spriteKey}:${animationName}`);
                            } else {
                                console.warn(`⚠️ Sprite creation returned null: ${spriteKey}:${animationName}`);
                            }
                        } catch (error) {
                            console.error(`❌ Sprite creation failed: ${spriteKey}:${animationName} - ${error.message}`);
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('❌ Integration test failed:', error);
            this.results.errors.push({
                type: 'INTEGRATION_ERROR',
                message: error.message
            });
        }
    }
    
    async performanceBenchmarking() {
        console.log('⚡ Running performance benchmarks...');
        
        try {
            const benchmarkStart = performance.now();
            
            // Rapid loading test
            const rapidLoadStart = performance.now();
            for (const spriteKey of Object.keys(this.atlasManager.spriteConfigs).slice(0, 5)) {
                await this.atlasManager.lazyLoadSprite(spriteKey);
            }
            const rapidLoadEnd = performance.now();
            
            // Memory pressure test
            const memoryStart = this.atlasManager.getMemoryUsage();
            await this.atlasManager.checkMemoryPressure();
            const memoryEnd = this.atlasManager.getMemoryUsage();
            
            const benchmarkEnd = performance.now();
            
            this.results.performanceMetrics = {
                totalBenchmarkTime: (benchmarkEnd - benchmarkStart).toFixed(2) + 'ms',
                rapidLoadTime: (rapidLoadEnd - rapidLoadStart).toFixed(2) + 'ms',
                avgLoadTimePerSprite: this.results.spriteDetails
                    .filter(d => d.loadTime)
                    .reduce((sum, d) => sum + parseFloat(d.loadTime), 0) / 
                    Math.max(1, this.results.spriteDetails.filter(d => d.loadTime).length),
                memoryBefore: memoryStart,
                memoryAfter: memoryEnd,
                memoryDelta: (memoryEnd.bytes - memoryStart.bytes) + ' bytes'
            };
            
        } catch (error) {
            console.error('❌ Performance benchmarking failed:', error);
            this.results.errors.push({
                type: 'PERFORMANCE_ERROR',
                message: error.message
            });
        }
    }
    
    analyzeMemoryUsage() {
        try {
            const memoryUsage = this.atlasManager.getMemoryUsage();
            const performanceMetrics = this.atlasManager.getPerformanceMetrics();
            
            this.results.performanceMetrics.memoryAnalysis = {
                totalMemory: memoryUsage.megabytes + ' MB',
                frameMemory: memoryUsage.frameMegabytes + ' MB',
                atlasCount: memoryUsage.atlasCount,
                frameCount: memoryUsage.frameCount,
                efficiency: memoryUsage.efficiency,
                poolStats: performanceMetrics.pool,
                cacheEfficiency: performanceMetrics.cacheEfficiency
            };
            
        } catch (error) {
            console.error('❌ Memory analysis failed:', error);
        }
    }
    
    generateValidationReport() {
        const endTime = performance.now();
        const totalTime = endTime - this.startTime;
        
        this.results.summary = {
            totalExecutionTime: totalTime.toFixed(2) + 'ms',
            successRate: ((this.results.successfulLoads / this.results.totalSprites) * 100).toFixed(1) + '%',
            avgLoadTime: this.results.performanceMetrics.avgLoadTimePerSprite?.toFixed(2) + 'ms' || 'N/A',
            totalErrors: this.results.errors.length,
            validationStatus: this.results.errors.length === 0 && 
                            this.results.successfulLoads === this.results.totalSprites ? 
                            'PASS' : 'FAIL'
        };
        
        console.log('\n📊 VALIDATION SUMMARY:');
        console.log(`Total sprites: ${this.results.totalSprites}`);
        console.log(`Successful loads: ${this.results.successfulLoads}`);
        console.log(`Failed loads: ${this.results.failedLoads}`);
        console.log(`Success rate: ${this.results.summary.successRate}`);
        console.log(`Average load time: ${this.results.summary.avgLoadTime}`);
        console.log(`Validation status: ${this.results.summary.validationStatus}`);
        
        if (this.results.errors.length > 0) {
            console.log('\n❌ ERRORS:');
            this.results.errors.forEach(error => {
                console.log(`- ${error.type}: ${error.message}`);
            });
        }
    }
    
    getResults() {
        return this.results;
    }
}

// Execute validation
const validator = new SpriteValidationTest();
await validator.runComprehensiveValidation();

export { SpriteValidationTest };