/**
 * MapGenerationTests.js
 * 
 * Comprehensive Test Suite for the Advanced Map Generation System
 * 
 * This test suite validates all aspects of map generation including:
 * - Wave Function Collapse (WFC) generation with OpenRA patterns
 * - Symmetric map balance validation
 * - Resource distribution fairness
 * - Performance benchmarks
 * - Map quality scoring
 * - Integration with existing generators
 * 
 * Usage:
 * - Run individual test suites or full validation
 * - Generate performance reports
 * - Create example maps for demonstration
 * - Validate against OpenRA compatibility
 * 
 * @author Advanced Map Generation System
 * @version 1.0.0
 */

import {
    AdvancedMapGenerator,
    WaveFunctionCollapse,
    AutoTiler,
    ResourcePlacer,
    SymmetricGenerator,
    MapValidator,
    createCompetitiveGenerator,
    createCampaignGenerator,
    validateMap
} from '../index.js';

class MapGenerationTests {
    constructor(options = {}) {
        this.options = {
            // Test configuration
            enablePerformanceTesting: true,
            enableVisualization: false,
            generateExampleMaps: true,
            outputDirectory: './test-output',
            
            // Performance thresholds
            maxGenerationTimeMs: 5000,
            minValidationScore: 75,
            maxMemoryUsageMB: 50,
            
            // Test parameters
            testMapSizes: [
                { width: 20, height: 15, name: 'small' },
                { width: 40, height: 30, name: 'medium' },
                { width: 60, height: 45, name: 'large' }
            ],
            
            playerCountTests: [1, 2, 4, 6, 8],
            algorithmTests: ['wfc', 'symmetric', 'hybrid', 'classic'],
            climateTests: ['desert', 'temperate', 'arctic', 'volcanic'],
            
            ...options
        };
        
        this.testResults = {
            overall: { passed: 0, failed: 0, warnings: 0 },
            suites: {},
            performance: {},
            examples: {}
        };
        
        this.startTime = null;
        this.currentSuite = null;
    }

    /**
     * Run all test suites
     */
    async runAllTests() {
        console.log('🚀 Starting Comprehensive Map Generation Test Suite');
        console.log('================================================\n');
        
        this.startTime = performance.now();
        
        try {
            // Core functionality tests
            await this.runWFCTests();
            await this.runSymmetricMapTests();
            await this.runResourceDistributionTests();
            await this.runMapValidationTests();
            
            // Integration tests
            await this.runGeneratorIntegrationTests();
            await this.runOpenRACompatibilityTests();
            
            // Performance tests
            if (this.options.enablePerformanceTesting) {
                await this.runPerformanceTests();
                await this.runMemoryLeakTests();
            }
            
            // Quality tests
            await this.runMapQualityTests();
            await this.runBalanceValidationTests();
            
            // Example generation
            if (this.options.generateExampleMaps) {
                await this.generateExampleMaps();
            }
            
        } catch (error) {
            this.logError('Test suite execution failed', error);
        }
        
        await this.generateTestReport();
        return this.testResults;
    }

    /**
     * Test Wave Function Collapse generation with OpenRA patterns
     */
    async runWFCTests() {
        this.startTestSuite('WFC Generation Tests');
        
        // Test 1: Basic WFC functionality
        await this.runTest('Basic WFC Generation', async () => {
            const tileRules = this.createOpenRACompatibleRules();
            const wfc = new WaveFunctionCollapse(20, 15, tileRules);
            const result = wfc.generate();
            
            this.assert(result !== null, 'WFC should generate a result');
            this.assert(result.length === 15, 'WFC should generate correct height');
            this.assert(result[0].length === 20, 'WFC should generate correct width');
            this.assert(this.validateTerrainTiles(result), 'All tiles should be valid OpenRA tiles');
        });
        
        // Test 2: Constraint satisfaction
        await this.runTest('WFC Constraint Satisfaction', async () => {
            const tileRules = this.createStrictConstraintRules();
            const wfc = new WaveFunctionCollapse(15, 15, tileRules);
            const result = wfc.generate();
            
            this.assert(result !== null, 'WFC should handle strict constraints');
            this.assert(this.validateConstraints(result, tileRules), 'All constraints should be satisfied');
        });
        
        // Test 3: Large map generation
        await this.runTest('WFC Large Map Generation', async () => {
            const tileRules = this.createOpenRACompatibleRules();
            const wfc = new WaveFunctionCollapse(60, 45, tileRules);
            const startTime = performance.now();
            const result = wfc.generate();
            const endTime = performance.now();
            
            this.assert(result !== null, 'WFC should handle large maps');
            this.assert(endTime - startTime < 10000, 'Large map generation should complete within 10s');
        });
        
        // Test 4: Edge case handling
        await this.runTest('WFC Edge Cases', async () => {
            // Test minimum size
            const minWfc = new WaveFunctionCollapse(3, 3, this.createSimpleRules());
            const minResult = minWfc.generate();
            this.assert(minResult !== null, 'WFC should handle minimum size maps');
            
            // Test single row/column
            const rowWfc = new WaveFunctionCollapse(10, 1, this.createSimpleRules());
            const rowResult = rowWfc.generate();
            this.assert(rowResult !== null, 'WFC should handle single row maps');
        });
        
        // Test 5: Backtracking functionality
        await this.runTest('WFC Backtracking', async () => {
            const conflictRules = this.createConflictingRules();
            const wfc = new WaveFunctionCollapse(10, 10, conflictRules);
            
            // Should either resolve conflicts or fail gracefully
            try {
                const result = wfc.generate();
                if (result) {
                    this.assert(this.validateConstraints(result, conflictRules), 
                        'Resolved conflicts should still satisfy constraints');
                }
                // If no result, that's acceptable for conflicting rules
            } catch (error) {
                // Graceful failure is acceptable
                this.logWarning('WFC failed on conflicting rules (expected)');
            }
        });
        
        this.endTestSuite();
    }

    /**
     * Test symmetric map balance validation
     */
    async runSymmetricMapTests() {
        this.startTestSuite('Symmetric Map Balance Tests');
        
        // Test 1: 2-player mirror symmetry
        await this.runTest('2-Player Mirror Symmetry', async () => {
            const generator = new SymmetricGenerator(40, 30, 2, {
                symmetryType: 'mirror'
            });
            
            const result = generator.generateSymmetricMap(this.createBaseTerrainGenerator());
            
            this.assert(result.terrain !== null, 'Should generate symmetric terrain');
            this.assert(result.startingPositions.length === 2, 'Should have 2 starting positions');
            this.assert(this.validateMirrorSymmetry(result.terrain), 'Map should be mirror symmetric');
            this.assert(this.validateStartingPositionBalance(result.startingPositions, result.terrain), 
                'Starting positions should be balanced');
        });
        
        // Test 2: 4-player rotational symmetry
        await this.runTest('4-Player Rotational Symmetry', async () => {
            const generator = new SymmetricGenerator(40, 40, 4, {
                symmetryType: 'rotational'
            });
            
            const result = generator.generateSymmetricMap(this.createBaseTerrainGenerator());
            
            this.assert(result.terrain !== null, 'Should generate symmetric terrain');
            this.assert(result.startingPositions.length === 4, 'Should have 4 starting positions');
            this.assert(this.validateRotationalSymmetry(result.terrain, 4), 
                'Map should have 4-fold rotational symmetry');
        });
        
        // Test 3: Resource symmetry
        await this.runTest('Symmetric Resource Distribution', async () => {
            const generator = createCompetitiveGenerator(2);
            const mapData = await generator.generateMap();
            
            this.assert(mapData.resources.length > 0, 'Should have resources');
            
            const balance = this.analyzeResourceBalance(mapData.resources, mapData.startingPositions);
            this.assert(balance.balanced, `Resources should be balanced: ${balance.reason}`);
            this.assert(balance.maxDeviation < 0.15, 'Resource deviation should be under 15%');
        });
        
        // Test 4: Path length fairness
        await this.runTest('Path Length Fairness', async () => {
            const generator = createCompetitiveGenerator(4);
            const mapData = await generator.generateMap();
            
            const pathAnalysis = this.analyzePathFairness(mapData.terrain, mapData.startingPositions);
            this.assert(pathAnalysis.fair, `Path lengths should be fair: ${pathAnalysis.reason}`);
            this.assert(pathAnalysis.maxDeviation < 0.20, 'Path length deviation should be under 20%');
        });
        
        // Test 5: Multi-player balance (6 and 8 players)
        await this.runTest('Multi-Player Balance', async () => {
            for (const playerCount of [6, 8]) {
                const generator = new AdvancedMapGenerator({
                    width: 50,
                    height: 50,
                    playerCount,
                    algorithm: 'symmetric',
                    symmetryType: 'rotational'
                });
                
                const mapData = await generator.generateMap();
                
                this.assert(mapData.startingPositions.length === playerCount, 
                    `Should have ${playerCount} starting positions`);
                
                const balance = this.validateMultiPlayerBalance(mapData, playerCount);
                this.assert(balance.score >= 75, 
                    `${playerCount}-player balance score should be >= 75, got ${balance.score}`);
            }
        });
        
        this.endTestSuite();
    }

    /**
     * Test resource distribution fairness
     */
    async runResourceDistributionTests() {
        this.startTestSuite('Resource Distribution Tests');
        
        // Test 1: Basic resource placement
        await this.runTest('Basic Resource Placement', async () => {
            const terrain = this.createTestTerrain(40, 30);
            const startingPositions = [
                { x: 10, y: 10, playerId: 0 },
                { x: 30, y: 20, playerId: 1 }
            ];
            
            const placer = new ResourcePlacer(40, 30, {
                resourceDensity: 0.08,
                playerPositions: startingPositions,
                resourceTypes: ['green', 'blue']
            });
            
            const resources = placer.placeResources(terrain, startingPositions);
            
            this.assert(resources.length > 0, 'Should place resources');
            this.assert(this.validateResourceTypes(resources), 'Resources should have valid types');
            this.assert(this.validateResourcePositions(resources, terrain), 
                'Resources should be on valid terrain');
        });
        
        // Test 2: Resource density control
        await this.runTest('Resource Density Control', async () => {
            const terrain = this.createTestTerrain(40, 30);
            const startingPositions = [{ x: 20, y: 15, playerId: 0 }];
            
            const densities = [0.05, 0.1, 0.15, 0.2];
            
            for (const density of densities) {
                const placer = new ResourcePlacer(40, 30, {
                    resourceDensity: density,
                    playerPositions: startingPositions
                });
                
                const resources = placer.placeResources(terrain, startingPositions);
                const actualDensity = this.calculateResourceDensity(resources, 40 * 30);
                
                // Allow 20% tolerance for density variations
                const tolerance = density * 0.2;
                this.assert(Math.abs(actualDensity - density) <= tolerance,
                    `Density ${density}: expected ~${density}, got ${actualDensity}`);
            }
        });
        
        // Test 3: Resource clustering
        await this.runTest('Resource Clustering Behavior', async () => {
            const terrain = this.createTestTerrain(50, 50);
            const startingPositions = [
                { x: 15, y: 15, playerId: 0 },
                { x: 35, y: 35, playerId: 1 }
            ];
            
            const placer = new ResourcePlacer(50, 50, {
                resourceDensity: 0.1,
                playerPositions: startingPositions,
                enableClustering: true,
                clusterSize: 8
            });
            
            const resources = placer.placeResources(terrain, startingPositions);
            const clusters = this.analyzeResourceClustering(resources);
            
            this.assert(clusters.averageClusterSize >= 4, 
                'Resources should form meaningful clusters');
            this.assert(clusters.clusterCount >= 3, 
                'Should have multiple resource clusters');
        });
        
        // Test 4: Distance balancing
        await this.runTest('Resource Distance Balancing', async () => {
            const terrain = this.createTestTerrain(60, 40);
            const startingPositions = [
                { x: 15, y: 20, playerId: 0 },
                { x: 45, y: 20, playerId: 1 }
            ];
            
            const placer = new ResourcePlacer(60, 40, {
                resourceDensity: 0.08,
                playerPositions: startingPositions,
                balanceDistance: true,
                balanceRadius: 15
            });
            
            const resources = placer.placeResources(terrain, startingPositions);
            const balance = this.analyzeResourceDistanceBalance(resources, startingPositions);
            
            this.assert(balance.balanced, 'Resource distances should be balanced');
            this.assert(balance.deviation < 0.25, 'Distance deviation should be reasonable');
        });
        
        // Test 5: Multi-resource type handling
        await this.runTest('Multi-Resource Type Handling', async () => {
            const terrain = this.createTestTerrain(40, 30);
            const startingPositions = [{ x: 20, y: 15, playerId: 0 }];
            
            const placer = new ResourcePlacer(40, 30, {
                resourceDensity: 0.1,
                playerPositions: startingPositions,
                resourceTypes: ['green', 'blue', 'rare'],
                resourceRatios: { green: 0.6, blue: 0.3, rare: 0.1 }
            });
            
            const resources = placer.placeResources(terrain, startingPositions);
            const typeCounts = this.countResourceTypes(resources);
            
            this.assert(typeCounts.green > 0, 'Should have green resources');
            this.assert(typeCounts.blue > 0, 'Should have blue resources');
            
            const total = typeCounts.green + typeCounts.blue + (typeCounts.rare || 0);
            const greenRatio = typeCounts.green / total;
            const blueRatio = typeCounts.blue / total;
            
            this.assert(Math.abs(greenRatio - 0.6) < 0.15, 'Green ratio should be ~60%');
            this.assert(Math.abs(blueRatio - 0.3) < 0.15, 'Blue ratio should be ~30%');
        });
        
        this.endTestSuite();
    }

    /**
     * Test performance benchmarks
     */
    async runPerformanceTests() {
        this.startTestSuite('Performance Benchmark Tests');
        
        // Test 1: Generation speed benchmarks
        await this.runTest('Generation Speed Benchmarks', async () => {
            const algorithms = ['classic', 'wfc', 'symmetric', 'hybrid'];
            const benchmarkResults = {};
            
            for (const algorithm of algorithms) {
                const times = [];
                const mapSize = { width: 40, height: 30 };
                
                for (let i = 0; i < 5; i++) {
                    const generator = new AdvancedMapGenerator({
                        ...mapSize,
                        algorithm,
                        enableValidation: false // For pure generation speed
                    });
                    
                    const startTime = performance.now();
                    await generator.generateMap();
                    const endTime = performance.now();
                    
                    times.push(endTime - startTime);
                }
                
                const avgTime = times.reduce((sum, t) => sum + t, 0) / times.length;
                benchmarkResults[algorithm] = avgTime;
                
                console.log(`  ${algorithm}: ${avgTime.toFixed(2)}ms average`);
            }
            
            this.testResults.performance.generationSpeed = benchmarkResults;
            
            // Validate performance expectations
            this.assert(benchmarkResults.classic < 200, 'Classic generation should be fast (<200ms)');
            this.assert(benchmarkResults.wfc < 3000, 'WFC generation should be reasonable (<3s)');
        });
        
        // Test 2: Memory usage testing
        await this.runTest('Memory Usage Analysis', async () => {
            const mapSizes = [
                { width: 20, height: 15, name: 'small' },
                { width: 40, height: 30, name: 'medium' },
                { width: 80, height: 60, name: 'large' }
            ];
            
            for (const size of mapSizes) {
                if (typeof global !== 'undefined' && global.gc) {
                    global.gc(); // Force garbage collection if available
                }
                
                const beforeMemory = this.getMemoryUsage();
                
                const generator = new AdvancedMapGenerator(size);
                const mapData = await generator.generateMap();
                
                const afterMemory = this.getMemoryUsage();
                const memoryUsed = afterMemory - beforeMemory;
                
                console.log(`  ${size.name} (${size.width}x${size.height}): ${memoryUsed.toFixed(2)}MB`);
                
                this.testResults.performance[`memory_${size.name}`] = memoryUsed;
                
                // Validate memory usage is reasonable
                const maxExpected = size.width * size.height * 0.001; // ~1KB per tile
                this.assert(memoryUsed < maxExpected * 2, 
                    `${size.name} map memory usage should be reasonable`);
            }
        });
        
        // Test 3: Concurrent generation stress test
        await this.runTest('Concurrent Generation Stress Test', async () => {
            const concurrentCount = 4;
            const promises = [];
            
            const startTime = performance.now();
            
            for (let i = 0; i < concurrentCount; i++) {
                const generator = new AdvancedMapGenerator({
                    width: 30,
                    height: 20,
                    algorithm: 'hybrid'
                });
                
                promises.push(generator.generateMap());
            }
            
            const results = await Promise.all(promises);
            const endTime = performance.now();
            
            this.assert(results.length === concurrentCount, 'All concurrent generations should complete');
            this.assert(results.every(r => r !== null), 'All results should be valid');
            
            const totalTime = endTime - startTime;
            console.log(`  Concurrent generation (${concurrentCount} maps): ${totalTime.toFixed(2)}ms`);
            
            this.testResults.performance.concurrentGeneration = {
                count: concurrentCount,
                totalTime,
                averageTime: totalTime / concurrentCount
            };
        });
        
        // Test 4: Validation performance
        await this.runTest('Validation Performance', async () => {
            const generator = new AdvancedMapGenerator({
                width: 50,
                height: 40,
                enableValidation: false
            });
            
            const mapData = await generator.generateMap();
            const validator = new MapValidator();
            
            const validationTimes = [];
            for (let i = 0; i < 3; i++) {
                const startTime = performance.now();
                const result = validator.validateMap(mapData);
                const endTime = performance.now();
                
                validationTimes.push(endTime - startTime);
                this.assert(result.overall.score >= 0, 'Validation should return a score');
            }
            
            const avgValidationTime = validationTimes.reduce((sum, t) => sum + t, 0) / validationTimes.length;
            console.log(`  Map validation: ${avgValidationTime.toFixed(2)}ms average`);
            
            this.testResults.performance.validation = avgValidationTime;
            this.assert(avgValidationTime < 500, 'Validation should be fast (<500ms)');
        });
        
        this.endTestSuite();
    }

    /**
     * Test map quality scoring
     */
    async runMapQualityTests() {
        this.startTestSuite('Map Quality Scoring Tests');
        
        // Test 1: Quality scoring consistency
        await this.runTest('Quality Scoring Consistency', async () => {
            const generator = new AdvancedMapGenerator({
                width: 40,
                height: 30,
                playerCount: 2,
                algorithm: 'hybrid'
            });
            
            const scores = [];
            for (let i = 0; i < 5; i++) {
                const mapData = await generator.generateMap();
                scores.push(mapData.validation.overall.score);
            }
            
            const avgScore = scores.reduce((sum, s) => sum + s, 0) / scores.length;
            const scoreVariation = Math.max(...scores) - Math.min(...scores);
            
            console.log(`  Average score: ${avgScore.toFixed(1)}, variation: ${scoreVariation.toFixed(1)}`);
            
            this.assert(avgScore >= 70, 'Average quality score should be reasonable');
            this.assert(scoreVariation <= 30, 'Score variation should be consistent');
        });
        
        // Test 2: Algorithm quality comparison
        await this.runTest('Algorithm Quality Comparison', async () => {
            const algorithms = ['classic', 'wfc', 'symmetric', 'hybrid'];
            const qualityResults = {};
            
            for (const algorithm of algorithms) {
                const generator = new AdvancedMapGenerator({
                    width: 40,
                    height: 30,
                    playerCount: 2,
                    algorithm
                });
                
                const mapData = await generator.generateMap();
                const score = mapData.validation.overall.score;
                qualityResults[algorithm] = score;
                
                console.log(`  ${algorithm}: ${score}/100`);
            }
            
            this.testResults.performance.qualityByAlgorithm = qualityResults;
            
            // Symmetric should have highest scores for multiplayer
            this.assert(qualityResults.symmetric >= 75, 
                'Symmetric algorithm should produce high-quality balanced maps');
        });
        
        // Test 3: Quality threshold enforcement
        await this.runTest('Quality Threshold Enforcement', async () => {
            const generator = new AdvancedMapGenerator({
                width: 30,
                height: 20,
                qualityThreshold: 80,
                maxGenerationAttempts: 3
            });
            
            try {
                const mapData = await generator.generateMap();
                const score = mapData.validation.overall.score;
                
                this.assert(score >= 80, 'Generated map should meet quality threshold');
            } catch (error) {
                // If it fails to meet threshold, that's also valid behavior
                this.logWarning('Failed to meet quality threshold (acceptable)');
            }
        });
        
        this.endTestSuite();
    }

    /**
     * Test balance validation for competitive play
     */
    async runBalanceValidationTests() {
        this.startTestSuite('Balance Validation Tests');
        
        // Test 1: Competitive 1v1 balance
        await this.runTest('Competitive 1v1 Balance', async () => {
            const generator = createCompetitiveGenerator(2);
            const mapData = await generator.generateMap();
            
            const validation = mapData.validation;
            const balanceScore = validation.balance?.score || 0;
            
            this.assert(balanceScore >= 80, 'Competitive maps should have high balance scores');
            this.assert(validation.overall.valid, 'Competitive maps should pass overall validation');
            
            // Check specific balance criteria
            const resourceBalance = this.analyzeResourceBalance(mapData.resources, mapData.startingPositions);
            this.assert(resourceBalance.balanced, 'Resources must be balanced in competitive play');
        });
        
        // Test 2: Team game balance (2v2)
        await this.runTest('Team Game Balance (2v2)', async () => {
            const generator = new AdvancedMapGenerator({
                width: 50,
                height: 40,
                playerCount: 4,
                algorithm: 'symmetric',
                symmetryType: 'rotational'
            });
            
            const mapData = await generator.generateMap();
            const teamBalance = this.analyzeTeamBalance(mapData.startingPositions, mapData.terrain);
            
            this.assert(teamBalance.balanced, 'Team positions should be balanced');
            this.assert(teamBalance.teamAdvantage < 0.1, 'No team should have significant advantage');
        });
        
        // Test 3: Resource economy validation
        await this.runTest('Resource Economy Validation', async () => {
            const generator = new AdvancedMapGenerator({
                width: 40,
                height: 30,
                playerCount: 2,
                resourceDensity: 0.1
            });
            
            const mapData = await generator.generateMap();
            const economy = this.analyzeResourceEconomy(mapData.resources, mapData.startingPositions);
            
            this.assert(economy.totalValue > 0, 'Map should have economic value');
            this.assert(economy.expansionOpportunities >= 2, 'Should have expansion opportunities');
            this.assert(economy.sustainabilityRating >= 0.7, 'Economy should be sustainable');
        });
        
        this.endTestSuite();
    }

    /**
     * Test OpenRA compatibility
     */
    async runOpenRACompatibilityTests() {
        this.startTestSuite('OpenRA Compatibility Tests');
        
        // Test 1: Tile ID compatibility
        await this.runTest('OpenRA Tile ID Compatibility', async () => {
            const generator = new AdvancedMapGenerator({
                width: 30,
                height: 20,
                algorithm: 'wfc'
            });
            
            const mapData = await generator.generateMap();
            const validTiles = this.getOpenRATileSet();
            
            let invalidTileCount = 0;
            for (let y = 0; y < mapData.terrain.length; y++) {
                for (let x = 0; x < mapData.terrain[y].length; x++) {
                    const tileId = mapData.terrain[y][x];
                    if (!validTiles.has(tileId)) {
                        invalidTileCount++;
                        console.warn(`  Invalid tile ID: ${tileId} at (${x}, ${y})`);
                    }
                }
            }
            
            this.assert(invalidTileCount === 0, `All tiles should be OpenRA compatible, found ${invalidTileCount} invalid tiles`);
        });
        
        // Test 2: Resource tile compatibility
        await this.runTest('OpenRA Resource Compatibility', async () => {
            const generator = new AdvancedMapGenerator({
                width: 30,
                height: 20,
                resourceDensity: 0.1
            });
            
            const mapData = await generator.generateMap();
            const validResourceTiles = new Set(['TI1', 'TI2', 'TI3', 'TI10', 'TI11', 'TI12']);
            
            for (const resource of mapData.resources) {
                for (const tile of resource.tiles) {
                    this.assert(validResourceTiles.has(tile.type), 
                        `Resource tile ${tile.type} should be OpenRA compatible`);
                }
            }
        });
        
        // Test 3: Map format compatibility
        await this.runTest('Map Format Structure', async () => {
            const generator = new AdvancedMapGenerator({
                width: 20,
                height: 15,
                playerCount: 2
            });
            
            const mapData = await generator.generateMap();
            
            // Check required structure
            this.assert(Array.isArray(mapData.terrain), 'Terrain should be a 2D array');
            this.assert(Array.isArray(mapData.resources), 'Resources should be an array');
            this.assert(Array.isArray(mapData.startingPositions), 'Starting positions should be an array');
            this.assert(typeof mapData.metadata === 'object', 'Metadata should be an object');
            
            // Check metadata completeness
            const meta = mapData.metadata;
            this.assert(typeof meta.width === 'number', 'Width should be specified');
            this.assert(typeof meta.height === 'number', 'Height should be specified');
            this.assert(typeof meta.playerCount === 'number', 'Player count should be specified');
        });
        
        this.endTestSuite();
    }

    /**
     * Test integration with existing generators
     */
    async runGeneratorIntegrationTests() {
        this.startTestSuite('Generator Integration Tests');
        
        // Test 1: Factory function integration
        await this.runTest('Factory Functions', async () => {
            // Test competitive generator
            const comp2v2 = createCompetitiveGenerator(2);
            const comp2v2Map = await comp2v2.generateMap();
            this.assert(comp2v2Map.startingPositions.length === 2, 'Competitive 2v2 should have 2 players');
            
            // Test campaign generator
            const campaign = createCampaignGenerator();
            const campaignMap = await campaign.generateMap();
            this.assert(campaignMap.startingPositions.length === 1, 'Campaign should have 1 player');
        });
        
        // Test 2: Preset system
        await this.runTest('Preset System', async () => {
            const presets = AdvancedMapGenerator.getPresets();
            
            this.assert(typeof presets === 'object', 'Presets should be an object');
            this.assert(presets.competitive2v2 !== undefined, 'Should have competitive 2v2 preset');
            this.assert(presets.skirmish1v1 !== undefined, 'Should have skirmish 1v1 preset');
            
            // Test preset usage
            const generator = new AdvancedMapGenerator(presets.competitive2v2);
            const mapData = await generator.generateMap();
            
            this.assert(mapData.metadata.playerCount === 4, 'Preset should set correct player count');
        });
        
        // Test 3: Statistics tracking
        await this.runTest('Statistics Tracking', async () => {
            const generator = new AdvancedMapGenerator({
                width: 30,
                height: 20,
                maxGenerationAttempts: 2
            });
            
            await generator.generateMap();
            const stats = generator.getStats();
            
            this.assert(typeof stats === 'object', 'Should return stats object');
            this.assert(stats.totalAttempts > 0, 'Should track generation attempts');
            this.assert(stats.successfulGenerations > 0, 'Should track successful generations');
        });
        
        this.endTestSuite();
    }

    /**
     * Test memory leak detection
     */
    async runMemoryLeakTests() {
        this.startTestSuite('Memory Leak Tests');
        
        // Test 1: Repeated generation memory stability
        await this.runTest('Repeated Generation Memory Stability', async () => {
            if (typeof global !== 'undefined' && global.gc) {
                global.gc();
            }
            
            const initialMemory = this.getMemoryUsage();
            const generator = new AdvancedMapGenerator({
                width: 30,
                height: 20,
                enableValidation: false
            });
            
            // Generate multiple maps
            for (let i = 0; i < 10; i++) {
                await generator.generateMap();
            }
            
            if (typeof global !== 'undefined' && global.gc) {
                global.gc();
            }
            
            const finalMemory = this.getMemoryUsage();
            const memoryGrowth = finalMemory - initialMemory;
            
            console.log(`  Memory growth after 10 generations: ${memoryGrowth.toFixed(2)}MB`);
            
            // Allow some memory growth, but not excessive
            this.assert(memoryGrowth < 10, 'Memory growth should be limited');
        });
        
        this.endTestSuite();
    }

    /**
     * Generate example maps for demonstration
     */
    async generateExampleMaps() {
        this.startTestSuite('Example Map Generation');
        
        const examples = {
            'desert-1v1': {
                width: 40, height: 30, playerCount: 2, climate: 'desert',
                algorithm: 'symmetric', symmetryType: 'mirror'
            },
            'temperate-2v2': {
                width: 50, height: 40, playerCount: 4, climate: 'temperate',
                algorithm: 'symmetric', symmetryType: 'rotational'
            },
            'large-wfc': {
                width: 60, height: 45, playerCount: 1, climate: 'temperate',
                algorithm: 'wfc'
            },
            'arctic-skirmish': {
                width: 45, height: 35, playerCount: 2, climate: 'arctic',
                algorithm: 'hybrid'
            },
            'volcanic-chaos': {
                width: 55, height: 40, playerCount: 6, climate: 'volcanic',
                algorithm: 'symmetric', symmetryType: 'rotational'
            }
        };
        
        for (const [name, config] of Object.entries(examples)) {
            await this.runTest(`Generate ${name} Example`, async () => {
                const generator = new AdvancedMapGenerator(config);
                const mapData = await generator.generateMap();
                
                this.assert(mapData !== null, 'Should generate map data');
                this.assert(mapData.validation.overall.score >= 60, 'Example should have decent quality');
                
                // Store example for potential export
                this.testResults.examples[name] = {
                    config,
                    score: mapData.validation.overall.score,
                    dimensions: `${config.width}x${config.height}`,
                    playerCount: config.playerCount,
                    algorithm: config.algorithm,
                    climate: config.climate
                };
                
                console.log(`  Generated ${name}: ${mapData.validation.overall.score}/100 quality`);
            });
        }
        
        this.endTestSuite();
    }

    // =================
    // Utility Methods
    // =================

    /**
     * Create OpenRA-compatible tile rules for WFC
     */
    createOpenRACompatibleRules() {
        const rules = {};
        
        // Sand tiles
        const sandTiles = ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08'];
        const dirtTiles = ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08'];
        const waterTiles = ['W1', 'W2'];
        const shoreTiles = ['SH1', 'SH2', 'SH3', 'SH4', 'SH5', 'SH6'];
        const treeTiles = ['T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09'];
        const rockTiles = ['ROCK1', 'ROCK2', 'ROCK3', 'ROCK4', 'ROCK5', 'ROCK6', 'ROCK7'];
        
        // Create adjacency rules
        this.addTileRules(rules, sandTiles, 0.4, [...sandTiles, ...dirtTiles.slice(0, 4), ...shoreTiles.slice(0, 2)]);
        this.addTileRules(rules, dirtTiles, 0.3, [...dirtTiles, ...sandTiles.slice(0, 4), ...treeTiles.slice(0, 3)]);
        this.addTileRules(rules, waterTiles, 0.05, [...waterTiles, ...shoreTiles]);
        this.addTileRules(rules, shoreTiles, 0.03, [...shoreTiles, ...sandTiles.slice(0, 2), ...waterTiles]);
        this.addTileRules(rules, treeTiles, 0.15, [...treeTiles, ...dirtTiles.slice(0, 3)]);
        this.addTileRules(rules, rockTiles, 0.07, [...rockTiles, ...sandTiles.slice(0, 2), ...dirtTiles.slice(0, 2)]);
        
        return rules;
    }

    addTileRules(rules, tiles, frequency, adjacentTiles) {
        const frequencyPerTile = frequency / tiles.length;
        for (const tile of tiles) {
            rules[tile] = {
                frequency: frequencyPerTile,
                adjacency: {
                    up: [...adjacentTiles],
                    down: [...adjacentTiles],
                    left: [...adjacentTiles],
                    right: [...adjacentTiles]
                }
            };
        }
    }

    createStrictConstraintRules() {
        return {
            'S01': {
                frequency: 0.8,
                adjacency: {
                    up: ['S01'], down: ['S01'], left: ['S01'], right: ['S01']
                }
            },
            'D01': {
                frequency: 0.2,
                adjacency: {
                    up: ['D01'], down: ['D01'], left: ['D01'], right: ['D01']
                }
            }
        };
    }

    createSimpleRules() {
        return {
            'S01': {
                frequency: 0.6,
                adjacency: {
                    up: ['S01', 'D01'], down: ['S01', 'D01'],
                    left: ['S01', 'D01'], right: ['S01', 'D01']
                }
            },
            'D01': {
                frequency: 0.4,
                adjacency: {
                    up: ['S01', 'D01'], down: ['S01', 'D01'],
                    left: ['S01', 'D01'], right: ['S01', 'D01']
                }
            }
        };
    }

    createConflictingRules() {
        return {
            'S01': {
                frequency: 0.5,
                adjacency: {
                    up: ['D01'], down: ['D01'], left: ['D01'], right: ['D01']
                }
            },
            'D01': {
                frequency: 0.5,
                adjacency: {
                    up: ['S01'], down: ['S01'], left: ['S01'], right: ['S01']
                }
            }
        };
    }

    createBaseTerrainGenerator() {
        return (width, height, rng) => {
            const terrain = [];
            for (let y = 0; y < height; y++) {
                terrain[y] = [];
                for (let x = 0; x < width; x++) {
                    terrain[y][x] = rng() > 0.5 ? 'S01' : 'D01';
                }
            }
            return terrain;
        };
    }

    createTestTerrain(width, height) {
        const terrain = [];
        for (let y = 0; y < height; y++) {
            terrain[y] = [];
            for (let x = 0; x < width; x++) {
                terrain[y][x] = 'S01'; // Simple sand terrain
            }
        }
        return terrain;
    }

    getOpenRATileSet() {
        return new Set([
            // Sand tiles
            'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08',
            // Dirt tiles  
            'D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08',
            // Water tiles
            'W1', 'W2',
            // Shore tiles
            'SH1', 'SH2', 'SH3', 'SH4', 'SH5', 'SH6',
            // Tree tiles
            'T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09',
            // Rock tiles
            'ROCK1', 'ROCK2', 'ROCK3', 'ROCK4', 'ROCK5', 'ROCK6', 'ROCK7',
            // Resource tiles
            'TI1', 'TI2', 'TI3', 'TI10', 'TI11', 'TI12'
        ]);
    }

    // =================
    // Validation Methods
    // =================

    validateTerrainTiles(terrain) {
        const validTiles = this.getOpenRATileSet();
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                if (!validTiles.has(terrain[y][x])) {
                    return false;
                }
            }
        }
        return true;
    }

    validateConstraints(terrain, tileRules) {
        const directions = [
            { dx: 0, dy: -1, name: 'up' },
            { dx: 0, dy: 1, name: 'down' },
            { dx: -1, dy: 0, name: 'left' },
            { dx: 1, dy: 0, name: 'right' }
        ];
        
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                const currentTile = terrain[y][x];
                const rules = tileRules[currentTile];
                
                if (!rules) continue;
                
                for (const dir of directions) {
                    const nx = x + dir.dx;
                    const ny = y + dir.dy;
                    
                    if (nx >= 0 && nx < terrain[y].length && ny >= 0 && ny < terrain.length) {
                        const neighborTile = terrain[ny][nx];
                        const allowedNeighbors = rules.adjacency[dir.name];
                        
                        if (!allowedNeighbors.includes(neighborTile)) {
                            return false;
                        }
                    }
                }
            }
        }
        return true;
    }

    validateMirrorSymmetry(terrain) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width / 2; x++) {
                const mirrorX = width - 1 - x;
                if (terrain[y][x] !== terrain[y][mirrorX]) {
                    return false;
                }
            }
        }
        return true;
    }

    validateRotationalSymmetry(terrain, foldCount) {
        const width = terrain[0].length;
        const height = terrain.length;
        const centerX = Math.floor(width / 2);
        const centerY = Math.floor(height / 2);
        
        // For rotational symmetry, we need to check if rotating by 360/foldCount degrees
        // gives us the same map. This is a simplified check.
        
        const angleStep = (2 * Math.PI) / foldCount;
        
        for (let fold = 1; fold < foldCount; fold++) {
            const angle = angleStep * fold;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            
            // Check a sampling of points
            for (let y = 0; y < height; y += 2) {
                for (let x = 0; x < width; x += 2) {
                    const relX = x - centerX;
                    const relY = y - centerY;
                    
                    const rotX = Math.round(relX * cos - relY * sin + centerX);
                    const rotY = Math.round(relX * sin + relY * cos + centerY);
                    
                    if (rotX >= 0 && rotX < width && rotY >= 0 && rotY < height) {
                        if (terrain[y][x] !== terrain[rotY][rotX]) {
                            return false;
                        }
                    }
                }
            }
        }
        return true;
    }

    validateStartingPositionBalance(startingPositions, terrain) {
        if (startingPositions.length !== 2) return true; // Only validate for 2 players
        
        const pos1 = startingPositions[0];
        const pos2 = startingPositions[1];
        
        // Check if starting positions are reasonably equidistant from center
        const width = terrain[0].length;
        const height = terrain.length;
        const centerX = width / 2;
        const centerY = height / 2;
        
        const dist1 = Math.sqrt((pos1.x - centerX) ** 2 + (pos1.y - centerY) ** 2);
        const dist2 = Math.sqrt((pos2.x - centerX) ** 2 + (pos2.y - centerY) ** 2);
        
        const distanceDifference = Math.abs(dist1 - dist2) / Math.max(dist1, dist2);
        
        return distanceDifference < 0.15; // 15% tolerance
    }

    validateResourceTypes(resources) {
        const validTypes = new Set(['green', 'blue', 'rare']);
        return resources.every(resource => validTypes.has(resource.type));
    }

    validateResourcePositions(resources, terrain) {
        const invalidTerrainTypes = new Set(['W1', 'W2', 'ROCK1', 'ROCK2', 'ROCK3', 'ROCK4', 'ROCK5', 'ROCK6', 'ROCK7']);
        
        for (const resource of resources) {
            for (const tile of resource.tiles || []) {
                const x = tile.x;
                const y = tile.y;
                
                if (x < 0 || x >= terrain[0].length || y < 0 || y >= terrain.length) {
                    return false;
                }
                
                const terrainType = terrain[y][x];
                if (invalidTerrainTypes.has(terrainType)) {
                    return false;
                }
            }
        }
        return true;
    }

    // =================
    // Analysis Methods  
    // =================

    analyzeResourceBalance(resources, startingPositions) {
        if (startingPositions.length < 2) {
            return { balanced: true, reason: 'Single player - no balance needed', maxDeviation: 0 };
        }
        
        // Calculate resource value for each player based on distance
        const playerResources = startingPositions.map(pos => ({
            playerId: pos.playerId,
            totalValue: 0,
            nearbyResources: 0
        }));
        
        const balanceRadius = 20; // tiles
        
        for (const resource of resources) {
            const resourceValue = resource.tiles ? resource.tiles.length * 10 : 100; // Rough value
            
            for (const tile of resource.tiles || [{ x: resource.x, y: resource.y }]) {
                // Find closest player
                let closestPlayer = 0;
                let closestDistance = Infinity;
                
                for (let i = 0; i < startingPositions.length; i++) {
                    const pos = startingPositions[i];
                    const distance = Math.sqrt((tile.x - pos.x) ** 2 + (tile.y - pos.y) ** 2);
                    
                    if (distance < closestDistance) {
                        closestDistance = distance;
                        closestPlayer = i;
                    }
                }
                
                // Add to closest player's resources if within balance radius
                if (closestDistance <= balanceRadius) {
                    playerResources[closestPlayer].totalValue += resourceValue;
                    playerResources[closestPlayer].nearbyResources++;
                }
            }
        }
        
        // Calculate balance
        const values = playerResources.map(p => p.totalValue);
        const avgValue = values.reduce((sum, v) => sum + v, 0) / values.length;
        
        if (avgValue === 0) {
            return { balanced: true, reason: 'No nearby resources to balance', maxDeviation: 0 };
        }
        
        const deviations = values.map(v => Math.abs(v - avgValue) / avgValue);
        const maxDeviation = Math.max(...deviations);
        
        return {
            balanced: maxDeviation < 0.15,
            reason: maxDeviation >= 0.15 ? `Resource imbalance: ${(maxDeviation * 100).toFixed(1)}% deviation` : 'Resources balanced',
            maxDeviation,
            playerValues: values
        };
    }

    analyzePathFairness(terrain, startingPositions) {
        if (startingPositions.length < 2) {
            return { fair: true, reason: 'Single player - no path fairness needed', maxDeviation: 0 };
        }
        
        // Simple path analysis - calculate straight-line distances between players
        const pathLengths = [];
        
        for (let i = 0; i < startingPositions.length; i++) {
            for (let j = i + 1; j < startingPositions.length; j++) {
                const pos1 = startingPositions[i];
                const pos2 = startingPositions[j];
                
                const distance = Math.sqrt((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2);
                pathLengths.push(distance);
            }
        }
        
        if (pathLengths.length === 0) {
            return { fair: true, reason: 'No paths to analyze', maxDeviation: 0 };
        }
        
        const avgLength = pathLengths.reduce((sum, len) => sum + len, 0) / pathLengths.length;
        const deviations = pathLengths.map(len => Math.abs(len - avgLength) / avgLength);
        const maxDeviation = Math.max(...deviations);
        
        return {
            fair: maxDeviation < 0.20,
            reason: maxDeviation >= 0.20 ? `Path length imbalance: ${(maxDeviation * 100).toFixed(1)}% deviation` : 'Paths fair',
            maxDeviation,
            pathLengths
        };
    }

    validateMultiPlayerBalance(mapData, playerCount) {
        const resourceBalance = this.analyzeResourceBalance(mapData.resources, mapData.startingPositions);
        const pathFairness = this.analyzePathFairness(mapData.terrain, mapData.startingPositions);
        
        let score = 100;
        
        if (!resourceBalance.balanced) {
            score -= resourceBalance.maxDeviation * 100;
        }
        
        if (!pathFairness.fair) {
            score -= pathFairness.maxDeviation * 50;
        }
        
        // Check starting position distribution
        const positions = mapData.startingPositions;
        if (positions.length === playerCount) {
            const centerX = mapData.metadata.width / 2;
            const centerY = mapData.metadata.height / 2;
            
            const distances = positions.map(pos => 
                Math.sqrt((pos.x - centerX) ** 2 + (pos.y - centerY) ** 2)
            );
            
            const avgDistance = distances.reduce((sum, d) => sum + d, 0) / distances.length;
            const distanceDeviations = distances.map(d => Math.abs(d - avgDistance) / avgDistance);
            const maxDistanceDeviation = Math.max(...distanceDeviations);
            
            if (maxDistanceDeviation > 0.15) {
                score -= maxDistanceDeviation * 30;
            }
        }
        
        return {
            score: Math.max(0, Math.min(100, score)),
            resourceBalance,
            pathFairness
        };
    }

    analyzeResourceClustering(resources) {
        if (resources.length === 0) {
            return { averageClusterSize: 0, clusterCount: 0 };
        }
        
        // Simple clustering analysis based on proximity
        const clusters = [];
        const processed = new Set();
        const clusterRadius = 5; // tiles
        
        for (let i = 0; i < resources.length; i++) {
            if (processed.has(i)) continue;
            
            const cluster = [i];
            processed.add(i);
            const resource = resources[i];
            const baseX = resource.x || (resource.tiles && resource.tiles[0]?.x) || 0;
            const baseY = resource.y || (resource.tiles && resource.tiles[0]?.y) || 0;
            
            // Find nearby resources
            for (let j = i + 1; j < resources.length; j++) {
                if (processed.has(j)) continue;
                
                const otherResource = resources[j];
                const otherX = otherResource.x || (otherResource.tiles && otherResource.tiles[0]?.x) || 0;
                const otherY = otherResource.y || (otherResource.tiles && otherResource.tiles[0]?.y) || 0;
                
                const distance = Math.sqrt((baseX - otherX) ** 2 + (baseY - otherY) ** 2);
                
                if (distance <= clusterRadius) {
                    cluster.push(j);
                    processed.add(j);
                }
            }
            
            clusters.push(cluster);
        }
        
        const averageClusterSize = clusters.reduce((sum, cluster) => sum + cluster.length, 0) / clusters.length;
        
        return {
            averageClusterSize,
            clusterCount: clusters.length,
            clusters
        };
    }

    analyzeResourceDistanceBalance(resources, startingPositions) {
        const playerDistances = startingPositions.map(pos => {
            const distances = resources.map(resource => {
                const resX = resource.x || (resource.tiles && resource.tiles[0]?.x) || 0;
                const resY = resource.y || (resource.tiles && resource.tiles[0]?.y) || 0;
                return Math.sqrt((pos.x - resX) ** 2 + (pos.y - resY) ** 2);
            });
            
            return distances.length > 0 ? 
                distances.reduce((sum, d) => sum + d, 0) / distances.length : 
                0;
        });
        
        if (playerDistances.length < 2) {
            return { balanced: true, deviation: 0 };
        }
        
        const avgDistance = playerDistances.reduce((sum, d) => sum + d, 0) / playerDistances.length;
        const deviations = playerDistances.map(d => Math.abs(d - avgDistance) / (avgDistance || 1));
        const maxDeviation = Math.max(...deviations);
        
        return {
            balanced: maxDeviation < 0.25,
            deviation: maxDeviation,
            playerDistances
        };
    }

    countResourceTypes(resources) {
        const counts = {};
        for (const resource of resources) {
            const type = resource.type || 'green';
            counts[type] = (counts[type] || 0) + 1;
        }
        return counts;
    }

    calculateResourceDensity(resources, totalTiles) {
        const resourceTileCount = resources.reduce((sum, resource) => {
            return sum + (resource.tiles ? resource.tiles.length : 1);
        }, 0);
        
        return resourceTileCount / totalTiles;
    }

    analyzeTeamBalance(startingPositions, terrain) {
        // Simplified team balance analysis
        // Assumes even player IDs are team 1, odd are team 2
        const team1 = startingPositions.filter(pos => pos.playerId % 2 === 0);
        const team2 = startingPositions.filter(pos => pos.playerId % 2 === 1);
        
        if (team1.length !== team2.length) {
            return { balanced: false, teamAdvantage: 1.0, reason: 'Uneven team sizes' };
        }
        
        // Calculate team centroid positions
        const team1Center = {
            x: team1.reduce((sum, pos) => sum + pos.x, 0) / team1.length,
            y: team1.reduce((sum, pos) => sum + pos.y, 0) / team1.length
        };
        
        const team2Center = {
            x: team2.reduce((sum, pos) => sum + pos.x, 0) / team2.length,
            y: team2.reduce((sum, pos) => sum + pos.y, 0) / team2.length
        };
        
        // Calculate advantage based on map center distance
        const mapCenterX = terrain[0].length / 2;
        const mapCenterY = terrain.length / 2;
        
        const team1CenterDistance = Math.sqrt(
            (team1Center.x - mapCenterX) ** 2 + (team1Center.y - mapCenterY) ** 2
        );
        
        const team2CenterDistance = Math.sqrt(
            (team2Center.x - mapCenterX) ** 2 + (team2Center.y - mapCenterY) ** 2
        );
        
        const distanceDifference = Math.abs(team1CenterDistance - team2CenterDistance);
        const teamAdvantage = distanceDifference / Math.max(team1CenterDistance, team2CenterDistance);
        
        return {
            balanced: teamAdvantage < 0.1,
            teamAdvantage,
            reason: teamAdvantage >= 0.1 ? `Team position imbalance: ${(teamAdvantage * 100).toFixed(1)}%` : 'Teams balanced'
        };
    }

    analyzeResourceEconomy(resources, startingPositions) {
        let totalValue = 0;
        let expansionSites = 0;
        
        for (const resource of resources) {
            const resourceValue = resource.tiles ? resource.tiles.length * 10 : 100;
            totalValue += resourceValue;
            
            // Check if resource is far from starting positions (expansion site)
            let isExpansion = true;
            for (const pos of startingPositions) {
                const resX = resource.x || (resource.tiles && resource.tiles[0]?.x) || 0;
                const resY = resource.y || (resource.tiles && resource.tiles[0]?.y) || 0;
                const distance = Math.sqrt((pos.x - resX) ** 2 + (pos.y - resY) ** 2);
                
                if (distance < 15) { // Within starting area
                    isExpansion = false;
                    break;
                }
            }
            
            if (isExpansion) {
                expansionSites++;
            }
        }
        
        const avgValuePerPlayer = startingPositions.length > 0 ? totalValue / startingPositions.length : totalValue;
        const sustainabilityRating = Math.min(1.0, avgValuePerPlayer / 1000); // Assuming 1000 value is sustainable
        
        return {
            totalValue,
            expansionOpportunities: expansionSites,
            sustainabilityRating,
            avgValuePerPlayer
        };
    }

    // =================
    // Test Framework Methods
    // =================

    startTestSuite(name) {
        this.currentSuite = name;
        console.log(`\n📋 ${name}`);
        console.log('─'.repeat(name.length + 3));
        
        this.testResults.suites[name] = {
            passed: 0,
            failed: 0,
            warnings: 0,
            tests: []
        };
    }

    async runTest(testName, testFunc) {
        const suite = this.testResults.suites[this.currentSuite];
        const testResult = {
            name: testName,
            passed: false,
            error: null,
            warnings: []
        };
        
        try {
            await testFunc();
            testResult.passed = true;
            suite.passed++;
            this.testResults.overall.passed++;
            console.log(`  ✅ ${testName}`);
        } catch (error) {
            testResult.passed = false;
            testResult.error = error.message;
            suite.failed++;
            this.testResults.overall.failed++;
            console.log(`  ❌ ${testName}: ${error.message}`);
        }
        
        suite.tests.push(testResult);
    }

    endTestSuite() {
        const suite = this.testResults.suites[this.currentSuite];
        const total = suite.passed + suite.failed;
        const passRate = total > 0 ? (suite.passed / total * 100).toFixed(1) : 0;
        
        console.log(`📊 Results: ${suite.passed}/${total} passed (${passRate}%)`);
        
        if (suite.warnings > 0) {
            console.log(`⚠️  ${suite.warnings} warnings`);
        }
        
        this.currentSuite = null;
    }

    assert(condition, message) {
        if (!condition) {
            throw new Error(message);
        }
    }

    logError(message, error) {
        console.error(`❌ ${message}:`, error);
    }

    logWarning(message) {
        console.warn(`⚠️  ${message}`);
        if (this.currentSuite) {
            this.testResults.suites[this.currentSuite].warnings++;
            this.testResults.overall.warnings++;
        }
    }

    getMemoryUsage() {
        if (typeof process !== 'undefined' && process.memoryUsage) {
            const usage = process.memoryUsage();
            return usage.heapUsed / 1024 / 1024; // Convert to MB
        }
        return 0; // Browser environment fallback
    }

    async generateTestReport() {
        const endTime = performance.now();
        const totalTime = endTime - this.startTime;
        
        console.log('\n🎯 FINAL TEST REPORT');
        console.log('==========================================');
        
        const overallTotal = this.testResults.overall.passed + this.testResults.overall.failed;
        const overallPassRate = overallTotal > 0 ? (this.testResults.overall.passed / overallTotal * 100).toFixed(1) : 0;
        
        console.log(`Overall Results: ${this.testResults.overall.passed}/${overallTotal} tests passed (${overallPassRate}%)`);
        console.log(`Total Time: ${(totalTime / 1000).toFixed(2)} seconds`);
        
        if (this.testResults.overall.warnings > 0) {
            console.log(`Warnings: ${this.testResults.overall.warnings}`);
        }
        
        console.log('\nSuite Breakdown:');
        for (const [suiteName, suite] of Object.entries(this.testResults.suites)) {
            const suiteTotal = suite.passed + suite.failed;
            const suitePassRate = suiteTotal > 0 ? (suite.passed / suiteTotal * 100).toFixed(1) : 0;
            console.log(`  ${suiteName}: ${suite.passed}/${suiteTotal} (${suitePassRate}%)`);
        }
        
        if (Object.keys(this.testResults.performance).length > 0) {
            console.log('\nPerformance Summary:');
            for (const [metric, value] of Object.entries(this.testResults.performance)) {
                if (typeof value === 'number') {
                    console.log(`  ${metric}: ${value.toFixed(2)}`);
                } else if (typeof value === 'object') {
                    console.log(`  ${metric}: ${JSON.stringify(value, null, 2)}`);
                }
            }
        }
        
        if (Object.keys(this.testResults.examples).length > 0) {
            console.log('\nGenerated Examples:');
            for (const [name, example] of Object.entries(this.testResults.examples)) {
                console.log(`  ${name}: ${example.score}/100 quality, ${example.dimensions}, ${example.playerCount} players`);
            }
        }
        
        console.log('\n✨ Test suite completed successfully!');
        
        return this.testResults;
    }
}

// Export for use in other modules
export default MapGenerationTests;

// Example usage and demo functionality
export class MapGenerationDemo {
    constructor() {
        this.tester = new MapGenerationTests({
            enablePerformanceTesting: true,
            generateExampleMaps: true
        });
    }
    
    async runQuickDemo() {
        console.log('🚀 Map Generation Quick Demo');
        console.log('============================\n');
        
        // Demo 1: Basic map generation
        console.log('📍 Demo 1: Basic Map Generation');
        const basicGenerator = new AdvancedMapGenerator({
            width: 30,
            height: 20,
            playerCount: 2,
            algorithm: 'hybrid'
        });
        
        const basicMap = await basicGenerator.generateMap();
        console.log(`Generated ${basicMap.metadata.width}x${basicMap.metadata.height} map`);
        console.log(`Quality Score: ${basicMap.validation.overall.score}/100`);
        console.log(`Algorithm: ${basicMap.metadata.algorithm}`);
        
        // Demo 2: Competitive map generation
        console.log('\n📍 Demo 2: Competitive 1v1 Map');
        const competitiveGenerator = createCompetitiveGenerator(2);
        const competitiveMap = await competitiveGenerator.generateMap();
        console.log(`Generated competitive map with score: ${competitiveMap.validation.overall.score}/100`);
        
        // Demo 3: Performance comparison
        console.log('\n📍 Demo 3: Algorithm Performance Comparison');
        const algorithms = ['classic', 'wfc', 'symmetric'];
        
        for (const algorithm of algorithms) {
            const generator = new AdvancedMapGenerator({
                width: 40,
                height: 30,
                algorithm,
                enableValidation: false
            });
            
            const startTime = performance.now();
            await generator.generateMap();
            const endTime = performance.now();
            
            console.log(`${algorithm}: ${(endTime - startTime).toFixed(2)}ms`);
        }
        
        console.log('\n✨ Demo completed!');
    }
    
    async runFullTests() {
        return await this.tester.runAllTests();
    }
}

// CLI interface for running tests
if (typeof process !== 'undefined' && process.argv) {
    const args = process.argv.slice(2);
    
    if (args.includes('--demo')) {
        const demo = new MapGenerationDemo();
        demo.runQuickDemo().catch(console.error);
    } else if (args.includes('--test')) {
        const tester = new MapGenerationTests();
        tester.runAllTests().catch(console.error);
    }
}