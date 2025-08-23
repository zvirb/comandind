/**
 * Integration Example - Using Map Generation Tests with Existing System
 * 
 * This example demonstrates how to integrate the comprehensive test suite
 * with your existing map generation workflow and how to use the testing
 * framework for validation and quality assurance.
 */

import MapGenerationTests, { MapGenerationDemo } from './MapGenerationTests.js';
import {
    AdvancedMapGenerator,
    createCompetitiveGenerator,
    createCampaignGenerator,
    validateMap
} from '../index.js';

/**
 * Example 1: Basic Integration with Existing Workflow
 */
async function basicIntegrationExample() {
    console.log('🔧 Basic Integration Example');
    console.log('============================\n');
    
    // Create your map generator as usual
    const generator = new AdvancedMapGenerator({
        width: 40,
        height: 30,
        playerCount: 2,
        algorithm: 'symmetric',
        climate: 'temperate'
    });
    
    // Generate a map
    const mapData = await generator.generateMap();
    console.log(`Generated map: ${mapData.metadata.width}x${mapData.metadata.height}`);
    console.log(`Quality score: ${mapData.validation.overall.score}/100`);
    
    // Use the test suite to validate your map
    const additionalValidation = validateMap(mapData, {
        resourceBalanceTolerance: 0.10, // Stricter balance
        minBuildablePercentage: 0.65    // More buildable area required
    });
    
    console.log(`Additional validation score: ${additionalValidation.overall.score}/100`);
    
    if (additionalValidation.overall.valid) {
        console.log('✅ Map passes additional validation criteria');
    } else {
        console.log('❌ Map failed additional validation');
        console.log('Issues:', additionalValidation.suggestions || 'No specific suggestions');
    }
}

/**
 * Example 2: Quality Assurance Pipeline
 */
async function qualityAssurancePipeline() {
    console.log('\n🛡️ Quality Assurance Pipeline Example');
    console.log('====================================\n');
    
    const testSuite = new MapGenerationTests({
        enablePerformanceTesting: true,
        generateExampleMaps: false, // Skip examples for QA
        minValidationScore: 80,     // High quality threshold
        maxGenerationTimeMs: 3000   // Performance requirement
    });
    
    console.log('Running QA validation tests...');
    
    // Run specific test suites for QA
    await testSuite.runWFCTests();
    await testSuite.runSymmetricMapTests();
    await testSuite.runResourceDistributionTests();
    await testSuite.runMapQualityTests();
    
    const results = testSuite.testResults;
    const overallPassRate = results.overall.passed / 
        (results.overall.passed + results.overall.failed) * 100;
    
    console.log(`\nQA Results: ${overallPassRate.toFixed(1)}% pass rate`);
    
    if (overallPassRate >= 95) {
        console.log('✅ System passes QA validation - ready for production');
    } else if (overallPassRate >= 80) {
        console.log('⚠️ System has minor issues - review recommended');
    } else {
        console.log('❌ System fails QA validation - fixes required');
    }
}

/**
 * Example 3: Performance Benchmarking
 */
async function performanceBenchmarking() {
    console.log('\n⚡ Performance Benchmarking Example');
    console.log('==================================\n');
    
    const testSuite = new MapGenerationTests({
        enablePerformanceTesting: true,
        testMapSizes: [
            { width: 30, height: 20, name: 'medium' },
            { width: 60, height: 40, name: 'large' }
        ],
        algorithmTests: ['classic', 'wfc', 'symmetric', 'hybrid']
    });
    
    console.log('Running performance benchmarks...');
    await testSuite.runPerformanceTests();
    
    const performance = testSuite.testResults.performance;
    console.log('\nBenchmark Results:');
    
    if (performance.generationSpeed) {
        console.log('Generation Speed (average):');
        for (const [algorithm, time] of Object.entries(performance.generationSpeed)) {
            console.log(`  ${algorithm}: ${time.toFixed(2)}ms`);
        }
    }
    
    if (performance.memory_medium) {
        console.log(`Memory Usage - Medium Map: ${performance.memory_medium.toFixed(2)}MB`);
    }
    
    if (performance.memory_large) {
        console.log(`Memory Usage - Large Map: ${performance.memory_large.toFixed(2)}MB`);
    }
}

/**
 * Example 4: Custom Test Integration
 */
async function customTestExample() {
    console.log('\n🎯 Custom Test Integration Example');
    console.log('=================================\n');
    
    // Create a custom test suite with your specific requirements
    class CustomMapTests extends MapGenerationTests {
        constructor(options) {
            super(options);
        }
        
        // Add your own custom tests
        async runCustomValidationTests() {
            this.startTestSuite('Custom Validation Tests');
            
            // Test 1: Custom terrain ratio validation
            await this.runTest('Terrain Type Ratios', async () => {
                const generator = new AdvancedMapGenerator({
                    width: 40,
                    height: 30,
                    climate: 'temperate'
                });
                
                const mapData = await generator.generateMap();
                const terrainCounts = this.analyzeTerrainTypes(mapData.terrain);
                
                // Your custom validation logic
                const sandRatio = terrainCounts.sand / terrainCounts.total;
                const dirtRatio = terrainCounts.dirt / terrainCounts.total;
                
                this.assert(sandRatio >= 0.4 && sandRatio <= 0.7, 
                    'Sand should be 40-70% of terrain');
                this.assert(dirtRatio >= 0.2 && dirtRatio <= 0.5,
                    'Dirt should be 20-50% of terrain');
            });
            
            // Test 2: Custom resource validation
            await this.runTest('Resource Proximity Rules', async () => {
                const generator = createCompetitiveGenerator(2);
                const mapData = await generator.generateMap();
                
                // Ensure no resources are too close to starting positions
                for (const startPos of mapData.startingPositions) {
                    for (const resource of mapData.resources) {
                        const distance = this.calculateDistance(startPos, resource);
                        this.assert(distance >= 5, 
                            'Resources should not be too close to starting positions');
                    }
                }
            });
            
            this.endTestSuite();
        }
        
        // Helper method for custom tests
        analyzeTerrainTypes(terrain) {
            const counts = { sand: 0, dirt: 0, water: 0, total: 0 };
            
            for (let y = 0; y < terrain.length; y++) {
                for (let x = 0; x < terrain[y].length; x++) {
                    const tile = terrain[y][x];
                    counts.total++;
                    
                    if (tile.startsWith('S')) counts.sand++;
                    else if (tile.startsWith('D')) counts.dirt++;
                    else if (tile.startsWith('W')) counts.water++;
                }
            }
            
            return counts;
        }
        
        calculateDistance(pos1, pos2) {
            const x1 = pos1.x;
            const y1 = pos1.y;
            const x2 = pos2.x || (pos2.tiles && pos2.tiles[0]?.x) || 0;
            const y2 = pos2.y || (pos2.tiles && pos2.tiles[0]?.y) || 0;
            
            return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        }
    }
    
    // Run your custom tests
    const customTests = new CustomMapTests({
        enablePerformanceTesting: false
    });
    
    await customTests.runCustomValidationTests();
    console.log('Custom tests completed!');
}

/**
 * Example 5: Continuous Integration Setup
 */
async function continuousIntegrationExample() {
    console.log('\n🔄 Continuous Integration Example');
    console.log('=================================\n');
    
    // Configuration for CI environment
    const ciTestOptions = {
        enablePerformanceTesting: true,
        generateExampleMaps: false,
        testMapSizes: [
            { width: 20, height: 15, name: 'small' }  // Faster for CI
        ],
        playerCountTests: [2, 4],
        algorithmTests: ['symmetric', 'hybrid'],
        maxGenerationTimeMs: 2000,  // Stricter timing for CI
        minValidationScore: 75
    };
    
    const ciTests = new MapGenerationTests(ciTestOptions);
    
    try {
        console.log('Running CI test suite...');
        const results = await ciTests.runAllTests();
        
        const passRate = results.overall.passed / 
            (results.overall.passed + results.overall.failed) * 100;
        
        console.log(`\nCI Results: ${results.overall.passed}/${results.overall.passed + results.overall.failed} tests passed (${passRate.toFixed(1)}%)`);
        
        // Export results for CI reporting
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const ciReport = {
            timestamp,
            passRate,
            testResults: results,
            environment: {
                nodeVersion: process.version,
                platform: process.platform
            }
        };
        
        console.log('CI test report generated');
        
        // In a real CI environment, you might save this to a file or send to a reporting service
        // fs.writeFileSync(`ci-report-${timestamp}.json`, JSON.stringify(ciReport, null, 2));
        
        if (passRate < 95) {
            throw new Error(`CI test failure: Pass rate ${passRate.toFixed(1)}% below required 95%`);
        }
        
        console.log('✅ All CI tests passed - build can proceed');
        
    } catch (error) {
        console.error('❌ CI tests failed:', error.message);
        process.exit(1);
    }
}

/**
 * Example 6: Interactive Testing Session
 */
async function interactiveTestingSession() {
    console.log('\n🎮 Interactive Testing Session Example');
    console.log('=====================================\n');
    
    // Create a demo instance for interactive testing
    const demo = new MapGenerationDemo();
    
    console.log('Running interactive demo...');
    await demo.runQuickDemo();
    
    // Generate some test maps for manual inspection
    console.log('\nGenerating test maps for manual inspection...');
    
    const testConfigs = [
        { name: 'competitive-1v1', playerCount: 2, algorithm: 'symmetric' },
        { name: 'large-wfc', width: 50, height: 40, algorithm: 'wfc' },
        { name: 'desert-skirmish', climate: 'desert', playerCount: 4 }
    ];
    
    for (const config of testConfigs) {
        const generator = new AdvancedMapGenerator({
            width: 40,
            height: 30,
            ...config
        });
        
        const mapData = await generator.generateMap();
        console.log(`${config.name}: ${mapData.validation.overall.score}/100 quality`);
    }
    
    console.log('\nInteractive session complete. Review generated maps manually.');
}

// Main execution function
async function runAllExamples() {
    console.log('🚀 Map Generation Test Integration Examples');
    console.log('==========================================\n');
    
    try {
        await basicIntegrationExample();
        await qualityAssurancePipeline();
        await performanceBenchmarking();
        await customTestExample();
        
        // Only run CI example if not in actual CI environment
        if (!process.env.CI) {
            await continuousIntegrationExample();
        }
        
        await interactiveTestingSession();
        
        console.log('\n✨ All examples completed successfully!');
        
    } catch (error) {
        console.error('❌ Example execution failed:', error);
        process.exit(1);
    }
}

// Export for use in other modules
export {
    basicIntegrationExample,
    qualityAssurancePipeline,
    performanceBenchmarking,
    customTestExample,
    continuousIntegrationExample,
    interactiveTestingSession
};

// Run examples if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    runAllExamples().catch(console.error);
}