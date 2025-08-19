/**
 * Pathfinding Performance Test Suite
 * Tests the optimized pathfinding system to validate 60 FPS performance goals
 */

import { PathfindingSystem } from '../ecs/PathfindingSystem.js';
import { NavigationGrid } from '../pathfinding/NavigationGrid.js';
import { AStar } from '../pathfinding/AStar.js';
import { PerformanceBenchmark } from './PerformanceBenchmark.js';

export class PathfindingPerformanceTest {
    constructor() {
        this.testResults = [];
        this.world = null;
        this.pathfindingSystem = null;
        
        // Test configurations
        this.testConfigs = {
            'small_scale': {
                unitCount: 10,
                mapSize: 500,
                duration: 5000,
                targetFPS: 60
            },
            'medium_scale': {
                unitCount: 25,
                mapSize: 1000,
                duration: 10000,
                targetFPS: 60
            },
            'large_scale': {
                unitCount: 50,
                mapSize: 1500,
                duration: 15000,
                targetFPS: 55
            },
            'stress_test': {
                unitCount: 100,
                mapSize: 2000,
                duration: 20000,
                targetFPS: 45
            }
        };
    }
    
    /**
     * Initialize test environment
     */
    async setupTestEnvironment() {
        console.log('🚀 Setting up pathfinding performance test environment...');
        
        // Create mock world
        this.world = {
            entities: new Set(),
            entityIdCounter: 0,
            
            createEntity() {
                const entity = {
                    id: this.entityIdCounter++,
                    active: true,
                    components: new Map(),
                    
                    addComponent(name, data) {
                        this.components.set(name, data);
                    },
                    
                    getComponent(name) {
                        return this.components.get(name);
                    },
                    
                    hasComponent(name) {
                        return this.components.has(name);
                    },
                    
                    removeComponent(name) {
                        this.components.delete(name);
                    }
                };\
                
                this.entities.add(entity);
                return entity;
            },
            
            removeEntity(entity) {
                entity.active = false;
                this.entities.delete(entity);
            },
            
            getStats() {
                return {\n                    entityCount: this.entities.size,\n                    systemCount: 1\n                };\n            }\n        };\n        \n        console.log('✅ Test environment ready');\n    }\n    \n    /**\n     * Run comprehensive pathfinding performance tests\n     */\n    async runPerformanceTests() {\n        await this.setupTestEnvironment();\n        \n        console.log('\\n🎯 Starting Pathfinding Performance Tests\\n');\n        console.log('=' .repeat(60));\n        \n        for (const [testName, config] of Object.entries(this.testConfigs)) {\n            console.log(`\\n📋 Running test: ${testName}`);\n            console.log(`   Units: ${config.unitCount}, Map: ${config.mapSize}x${config.mapSize}`);\n            console.log(`   Duration: ${config.duration}ms, Target FPS: ${config.targetFPS}`);\n            \n            try {\n                const result = await this.runSingleTest(testName, config);\n                this.testResults.push(result);\n                \n                // Print immediate results\n                this.printTestResult(result);\n                \n                // Wait between tests\n                await new Promise(resolve => setTimeout(resolve, 2000));\n            } catch (error) {\n                console.error(`❌ Test ${testName} failed:`, error.message);\n                this.testResults.push({\n                    testName,\n                    success: false,\n                    error: error.message\n                });\n            }\n        }\n        \n        // Generate comprehensive report\n        this.generatePerformanceReport();\n        \n        return this.testResults;\n    }\n    \n    /**\n     * Run a single performance test\n     */\n    async runSingleTest(testName, config) {\n        const startTime = performance.now();\n        \n        // Create pathfinding system\n        const pathfindingSystem = new PathfindingSystem(\n            this.world, \n            config.mapSize, \n            config.mapSize\n        );\n        \n        // Create test entities\n        const entities = [];\n        for (let i = 0; i < config.unitCount; i++) {\n            const entity = this.createTestEntity(config.mapSize);\n            entities.push(entity);\n        }\n        \n        // Performance tracking\n        const performanceData = {\n            frameCount: 0,\n            totalFrameTime: 0,\n            minFPS: Infinity,\n            maxFPS: 0,\n            pathCalculations: 0,\n            cacheHits: 0,\n            cacheMisses: 0,\n            spatialQueries: 0\n        };\n        \n        // Simulation loop\n        const deltaTime = 16.67; // ~60 FPS\n        let elapsedTime = 0;\n        let lastFrameTime = performance.now();\n        \n        while (elapsedTime < config.duration) {\n            const frameStartTime = performance.now();\n            \n            // Simulate random movement commands\n            this.simulateMovementCommands(entities, config.mapSize);\n            \n            // Update pathfinding system\n            pathfindingSystem.update(deltaTime);\n            \n            // Collect performance metrics\n            const frameTime = performance.now() - frameStartTime;\n            const fps = 1000 / frameTime;\n            \n            performanceData.frameCount++;\n            performanceData.totalFrameTime += frameTime;\n            performanceData.minFPS = Math.min(performanceData.minFPS, fps);\n            performanceData.maxFPS = Math.max(performanceData.maxFPS, fps);\n            \n            // Collect pathfinding stats\n            const stats = pathfindingSystem.getStats();\n            if (stats.performance) {\n                performanceData.pathCalculations += stats.performance.pathsCalculatedThisFrame || 0;\n                performanceData.spatialQueries += stats.performance.spatialQueriesPerFrame || 0;\n            }\n            \n            elapsedTime += deltaTime;\n            \n            // Yield control to prevent blocking\n            if (performanceData.frameCount % 60 === 0) {\n                await new Promise(resolve => setTimeout(resolve, 1));\n            }\n        }\n        \n        // Cleanup\n        entities.forEach(entity => this.world.removeEntity(entity));\n        \n        // Calculate final statistics\n        const avgFPS = performanceData.frameCount / (performanceData.totalFrameTime / 1000);\n        const avgFrameTime = performanceData.totalFrameTime / performanceData.frameCount;\n        \n        const result = {\n            testName,\n            success: avgFPS >= config.targetFPS * 0.9, // Allow 10% tolerance\n            duration: performance.now() - startTime,\n            config,\n            metrics: {\n                averageFPS: avgFPS,\n                minimumFPS: performanceData.minFPS,\n                maximumFPS: performanceData.maxFPS,\n                averageFrameTime: avgFrameTime,\n                frameCount: performanceData.frameCount,\n                pathCalculations: performanceData.pathCalculations,\n                spatialQueries: performanceData.spatialQueries,\n                targetMet: avgFPS >= config.targetFPS\n            },\n            pathfindingStats: pathfindingSystem.getStats()\n        };\n        \n        return result;\n    }\n    \n    /**\n     * Create a test entity with movement components\n     */\n    createTestEntity(mapSize) {\n        const entity = this.world.createEntity();\n        \n        // Add required components\n        entity.addComponent('TransformComponent', {\n            x: Math.random() * mapSize,\n            y: Math.random() * mapSize,\n            rotation: 0\n        });\n        \n        entity.addComponent('MovementComponent', {\n            speed: 50 + Math.random() * 100,\n            isMoving: false,\n            targetX: null,\n            targetY: null,\n            path: [],\n            pathIndex: 0,\n            arrivalDistance: 5,\n            \n            setTarget(x, y) {\n                this.targetX = x;\n                this.targetY = y;\n                this.isMoving = true;\n                this.path = [];\n                this.pathIndex = 0;\n            },\n            \n            stop() {\n                this.isMoving = false;\n                this.targetX = null;\n                this.targetY = null;\n                this.path = [];\n                this.pathIndex = 0;\n            }\n        });\n        \n        entity.addComponent('UnitComponent', {\n            facing: 0,\n            unitType: 'test_unit'\n        });\n        \n        return entity;\n    }\n    \n    /**\n     * Simulate random movement commands for entities\n     */\n    simulateMovementCommands(entities, mapSize) {\n        // Randomly assign movement targets to simulate player commands\n        const commandProbability = 0.02; // 2% chance per frame per unit\n        \n        entities.forEach(entity => {\n            if (Math.random() < commandProbability) {\n                const movement = entity.getComponent('MovementComponent');\n                const targetX = Math.random() * mapSize;\n                const targetY = Math.random() * mapSize;\n                \n                movement.setTarget(targetX, targetY);\n            }\n        });\n    }\n    \n    /**\n     * Print individual test result\n     */\n    printTestResult(result) {\n        const { testName, success, metrics, config } = result;\n        \n        console.log(`\\n📊 Results for ${testName}:`);\n        console.log('   ' + '=' .repeat(50));\n        console.log(`   ✅ Success: ${success ? 'PASSED' : 'FAILED'}`);\n        console.log(`   🎯 Target FPS: ${config.targetFPS} | Achieved: ${metrics.averageFPS.toFixed(1)}`);\n        console.log(`   📈 FPS Range: ${metrics.minimumFPS.toFixed(1)} - ${metrics.maximumFPS.toFixed(1)}`);\n        console.log(`   ⏱️  Frame Time: ${metrics.averageFrameTime.toFixed(2)}ms`);\n        console.log(`   🧮 Path Calculations: ${metrics.pathCalculations}`);\n        console.log(`   🔍 Spatial Queries: ${metrics.spatialQueries}`);\n        \n        if (result.pathfindingStats && result.pathfindingStats.performance) {\n            const perf = result.pathfindingStats.performance;\n            console.log(`   💾 Cache Hit Ratio: ${(perf.cacheHitRatio * 100).toFixed(1)}%`);\n            console.log(`   ⏳ Avg Path Time: ${perf.averagePathCalculationTime.toFixed(2)}ms`);\n            console.log(`   📋 Queue Length: ${perf.queueLength}`);\n        }\n        \n        if (!success) {\n            console.log(`   ⚠️  Performance below target by ${(config.targetFPS - metrics.averageFPS).toFixed(1)} FPS`);\n        }\n    }\n    \n    /**\n     * Generate comprehensive performance report\n     */\n    generatePerformanceReport() {\n        console.log('\\n' + '=' .repeat(80));\n        console.log('🏆 PATHFINDING PERFORMANCE REPORT');\n        console.log('=' .repeat(80));\n        \n        const successfulTests = this.testResults.filter(r => r.success);\n        const failedTests = this.testResults.filter(r => !r.success);\n        \n        console.log(`\\n📈 Test Summary:`);\n        console.log(`   Total Tests: ${this.testResults.length}`);\n        console.log(`   Passed: ${successfulTests.length} ✅`);\n        console.log(`   Failed: ${failedTests.length} ${failedTests.length > 0 ? '❌' : ''}`);\n        console.log(`   Success Rate: ${(successfulTests.length / this.testResults.length * 100).toFixed(1)}%`);\n        \n        if (successfulTests.length > 0) {\n            const avgFPS = successfulTests.reduce((sum, test) => sum + test.metrics.averageFPS, 0) / successfulTests.length;\n            const avgFrameTime = successfulTests.reduce((sum, test) => sum + test.metrics.averageFrameTime, 0) / successfulTests.length;\n            const totalPathCalcs = successfulTests.reduce((sum, test) => sum + test.metrics.pathCalculations, 0);\n            \n            console.log(`\\n🎯 Performance Metrics:`);\n            console.log(`   Overall Average FPS: ${avgFPS.toFixed(1)}`);\n            console.log(`   Overall Frame Time: ${avgFrameTime.toFixed(2)}ms`);\n            console.log(`   Total Path Calculations: ${totalPathCalcs}`);\n            console.log(`   60+ FPS Target: ${avgFPS >= 60 ? '✅ MET' : '❌ NOT MET'}`);\n        }\n        \n        if (failedTests.length > 0) {\n            console.log(`\\n⚠️  Performance Issues Detected:`);\n            failedTests.forEach(test => {\n                const shortfall = test.config.targetFPS - test.metrics.averageFPS;\n                console.log(`   • ${test.testName}: ${shortfall.toFixed(1)} FPS below target`);\n            });\n        }\n        \n        // Optimization recommendations\n        this.generateOptimizationRecommendations();\n        \n        console.log('\\n' + '=' .repeat(80));\n    }\n    \n    /**\n     * Generate optimization recommendations based on test results\n     */\n    generateOptimizationRecommendations() {\n        console.log(`\\n💡 Optimization Recommendations:`);\n        \n        const hasFailures = this.testResults.some(r => !r.success);\n        const highPathCalculations = this.testResults.some(r => r.metrics.pathCalculations > 1000);\n        const lowCacheHitRate = this.testResults.some(r => \n            r.pathfindingStats?.performance?.cacheHitRatio < 0.7\n        );\n        \n        if (!hasFailures) {\n            console.log(`   ✅ All performance targets met! System is well optimized.`);\n        } else {\n            console.log(`   🔧 Consider the following optimizations:`);\n            \n            if (highPathCalculations) {\n                console.log(`   • Reduce maximum paths per frame (currently processing many paths)`);\n                console.log(`   • Increase spatial partitioning cell size to reduce queries`);\n            }\n            \n            if (lowCacheHitRate) {\n                console.log(`   • Increase path cache timeout for better hit rates`);\n                console.log(`   • Optimize cache key generation for more cache reuse`);\n            }\n            \n            console.log(`   • Consider implementing hierarchical pathfinding for long distances`);\n            console.log(`   • Enable flow field pathfinding for large group movements`);\n            console.log(`   • Optimize navigation grid resolution vs. accuracy trade-offs`);\n        }\n    }\n    \n    /**\n     * Export test results for analysis\n     */\n    exportResults() {\n        return {\n            timestamp: new Date().toISOString(),\n            testResults: this.testResults,\n            summary: {\n                totalTests: this.testResults.length,\n                passedTests: this.testResults.filter(r => r.success).length,\n                failedTests: this.testResults.filter(r => !r.success).length,\n                averageFPS: this.testResults\n                    .filter(r => r.success)\n                    .reduce((sum, test, _, arr) => sum + test.metrics.averageFPS / arr.length, 0)\n            }\n        };\n    }\n}