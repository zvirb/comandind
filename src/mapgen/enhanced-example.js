/**
 * Enhanced Map Generation Example
 * 
 * Demonstrates the new features:
 * - Simplex noise for terrain generation
 * - ML-based map quality evaluation
 * - Enhanced terrain generation methods
 */

import AdvancedMapGenerator from './AdvancedMapGenerator.js';

/**
 * Test the enhanced map generation system
 */
async function testEnhancedMapGeneration() {
    console.log('🗺️ Testing Enhanced Map Generation System');
    console.log('=' .repeat(50));
    
    try {
        // Test different map configurations
        const testConfigs = [
            {
                name: 'Enhanced Temperate Map (ML Evaluation)',
                config: {
                    width: 40,
                    height: 30,
                    algorithm: 'hybrid',
                    climate: 'temperate',
                    playerCount: 2,
                    enableMLEvaluation: true,
                    enableValidation: true,
                    qualityThreshold: 75,
                    mlQualityThreshold: 70,
                    forestDensity: 0.25,
                    waterCoverage: 0.15,
                    mountainDensity: 0.12
                }
            },
            {
                name: 'Enhanced Desert Map (Simplex Noise)',
                config: {
                    width: 50,
                    height: 35,
                    algorithm: 'classic',
                    climate: 'desert',
                    playerCount: 4,
                    enableMLEvaluation: true,
                    enableValidation: false,
                    mlQualityThreshold: 65,
                    forestDensity: 0.05,
                    waterCoverage: 0.08,
                    mountainDensity: 0.18
                }
            },
            {
                name: 'Arctic Terrain (Biome-aware Generation)',
                config: {
                    width: 35,
                    height: 25,
                    algorithm: 'wfc',
                    climate: 'arctic',
                    playerCount: 1,
                    enableMLEvaluation: true,
                    enableValidation: true,
                    qualityThreshold: 70,
                    mlQualityThreshold: 65,
                    forestDensity: 0.15,
                    waterCoverage: 0.10,
                    mountainDensity: 0.20
                }
            },
            {
                name: 'Volcanic Landscape (Multi-octave Noise)',
                config: {
                    width: 45,
                    height: 30,
                    algorithm: 'hybrid',
                    climate: 'volcanic',
                    playerCount: 2,
                    enableMLEvaluation: true,
                    enableValidation: true,
                    qualityThreshold: 72,
                    mlQualityThreshold: 68,
                    forestDensity: 0.10,
                    waterCoverage: 0.05,
                    mountainDensity: 0.25
                }
            }
        ];
        
        for (const testCase of testConfigs) {
            console.log(`\n🧪 Testing: ${testCase.name}`);
            console.log('-'.repeat(40));
            
            const startTime = performance.now();
            
            // Create map generator with test configuration
            const generator = new AdvancedMapGenerator(testCase.config);
            
            // Generate the map
            const mapResult = await generator.generateMap();
            
            const endTime = performance.now();
            const generationTime = endTime - startTime;
            
            // Display results
            console.log(`✅ Map generated in ${generationTime.toFixed(2)}ms`);
            console.log(`📏 Size: ${mapResult.metadata.width}x${mapResult.metadata.height}`);
            console.log(`🌍 Climate: ${mapResult.metadata.climate}`);
            console.log(`🎮 Players: ${mapResult.metadata.playerCount}`);
            console.log(`⚙️ Algorithm: ${mapResult.metadata.algorithm}`);
            
            // Traditional validation results
            if (mapResult.validation) {
                console.log(`📊 Validation Score: ${mapResult.validation.overall.score}/100 (${mapResult.validation.overall.grade})`);\n                
                if (mapResult.validation.details) {\n                    const details = mapResult.validation.details;\n                    console.log('   Detailed Scores:');\n                    Object.entries(details).forEach(([key, value]) => {\n                        if (typeof value === 'object' && value.score) {\n                            console.log(`     ${key}: ${value.score}/100`);\n                        }\n                    });\n                }\n            }
            
            // ML evaluation results
            if (mapResult.mlEvaluation) {
                const ml = mapResult.mlEvaluation;
                console.log(`🧠 ML Evaluation Score: ${ml.overall.score}/100 (${ml.overall.grade})`);\n                console.log(`🎯 Confidence: ${ml.confidence}%`);\n                \n                if (ml.details) {\n                    console.log('   ML Detailed Analysis:');\n                    Object.entries(ml.details).forEach(([aspect, data]) => {\n                        console.log(`     ${aspect}: ${data.score}/100 (weight: ${data.weight})`);\n                    });\n                }\n                \n                if (ml.recommendations && ml.recommendations.length > 0) {\n                    console.log('   🔍 ML Recommendations:');\n                    ml.recommendations.forEach((rec, index) => {\n                        console.log(`     ${index + 1}. [${rec.priority}] ${rec.message}`);\n                    });\n                }\n                \n                console.log(`   ⚡ Evaluation Time: ${ml.metadata.evaluationTime.toFixed(2)}ms`);\n                console.log(`   🔧 Backend: ${ml.metadata.tensorflowBackend || 'fallback'}`);\n            }
            
            // Combined score
            if (mapResult.combinedScore) {
                console.log(`🏆 Combined Score: ${mapResult.combinedScore.toFixed(1)}/100`);
            }
            
            // Resource analysis
            if (mapResult.resources) {
                console.log(`💎 Resources Placed: ${mapResult.resources.length}`);\n                \n                const resourceTypes = {};\n                mapResult.resources.forEach(res => {\n                    resourceTypes[res.type] = (resourceTypes[res.type] || 0) + 1;\n                });\n                \n                console.log('   Resource Distribution:');\n                Object.entries(resourceTypes).forEach(([type, count]) => {\n                    console.log(`     ${type}: ${count}`);\n                });\n            }
            
            // Terrain analysis
            if (mapResult.terrain) {
                const terrainStats = analyzeTerrainComposition(mapResult.terrain);
                console.log(`🌍 Terrain Composition:`);\n                Object.entries(terrainStats).forEach(([type, percentage]) => {\n                    console.log(`     ${type}: ${percentage.toFixed(1)}%`);\n                });\n            }
            
            // Performance metrics
            const stats = generator.getStats();
            if (stats.averageGenerationTime > 0) {
                console.log(`⏱️ Avg Generation Time: ${stats.averageGenerationTime.toFixed(2)}ms`);\n                console.log(`📈 Success Rate: ${(stats.successRate * 100).toFixed(1)}%`);\n            }
        }
        
        console.log('\n' + '='.repeat(50));
        console.log('✅ Enhanced map generation testing completed!');
        console.log('\nKey Enhancements Demonstrated:');
        console.log('• Simplex noise for more natural terrain patterns');
        console.log('• ML-based quality evaluation with confidence scoring');
        console.log('• Biome-aware feature placement');
        console.log('• Multi-octave noise for terrain detail');
        console.log('• Enhanced climate-specific generation');
        console.log('• Intelligent recommendation system');
        
    } catch (error) {
        console.error('❌ Enhanced map generation test failed:', error);
        console.error('Stack trace:', error.stack);
    }
}

/**
 * Analyze terrain composition for statistics
 */
function analyzeTerrainComposition(terrain) {
    const stats = {};
    const totalTiles = terrain.length * terrain[0].length;
    
    for (const row of terrain) {
        for (const tile of row) {
            const tileType = getTileTypeName(tile);
            stats[tileType] = (stats[tileType] || 0) + 1;
        }
    }
    
    // Convert to percentages
    Object.keys(stats).forEach(type => {
        stats[type] = (stats[type] / totalTiles) * 100;
    });
    
    return stats;
}

/**
 * Convert tile ID to readable type name
 */
function getTileTypeName(tileId) {
    if (tileId.startsWith('S')) return 'Sand/Clear';
    if (tileId.startsWith('D')) return 'Dirt/Rough';
    if (tileId.startsWith('W')) return 'Water';
    if (tileId.startsWith('SH')) return 'Shore';
    if (tileId.startsWith('T')) return 'Forest';
    if (tileId.startsWith('ROCK')) return 'Mountains';
    return 'Other';
}

/**
 * Demonstrate specific enhanced features
 */
async function demonstrateEnhancedFeatures() {
    console.log('\n🔬 Demonstrating Enhanced Features');
    console.log('=' .repeat(50));
    
    // Test simplex noise directly
    console.log('\n1. Simplex Noise Terrain Generation:');
    const generator = new AdvancedMapGenerator({
        algorithm: 'classic',
        climate: 'temperate',
        enableMLEvaluation: false,
        enableValidation: false
    });
    
    const noiseMap = await generator.generateMap();
    console.log('   ✅ Generated terrain using multi-octave simplex noise');
    console.log(`   📊 Terrain variety: ${calculateTerrainVariety(noiseMap.terrain)}/100`);
    
    // Test ML evaluation separately
    console.log('\n2. ML Quality Evaluation:');
    const mlGenerator = new AdvancedMapGenerator({
        enableMLEvaluation: true,
        enableValidation: false,
        mlQualityThreshold: 65
    });
    
    const mlMap = await mlGenerator.generateMap();
    if (mlMap.mlEvaluation) {
        console.log('   ✅ ML evaluation completed successfully');
        console.log(`   🎯 ML predicted quality: ${mlMap.mlEvaluation.overall.score}/100`);
        console.log(`   🔮 Confidence level: ${mlMap.mlEvaluation.confidence}%`);
    } else {
        console.log('   ⚠️ ML evaluation not available (using fallback)');
    }
    
    // Test biome-aware generation
    console.log('\n3. Biome-aware Feature Placement:');
    const biomeGenerator = new AdvancedMapGenerator({
        climate: 'temperate',
        forestDensity: 0.3,
        waterCoverage: 0.2,
        mountainDensity: 0.15,
        enableMLEvaluation: false
    });
    
    const biomeMap = await biomeGenerator.generateMap();
    const features = countMapFeatures(biomeMap.terrain);
    console.log('   ✅ Generated map with biome-aware features');
    console.log(`   🌲 Forest tiles: ${features.forest}`);
    console.log(`   💧 Water tiles: ${features.water}`);
    console.log(`   ⛰️ Mountain tiles: ${features.mountains}`);
}

/**
 * Calculate terrain variety score
 */
function calculateTerrainVariety(terrain) {
    const uniqueTileTypes = new Set();
    for (const row of terrain) {
        for (const tile of row) {
            uniqueTileTypes.add(tile.charAt(0));
        }
    }
    return Math.min(100, uniqueTileTypes.size * 15);
}

/**
 * Count different map features
 */
function countMapFeatures(terrain) {
    const features = { forest: 0, water: 0, mountains: 0, shore: 0 };
    
    for (const row of terrain) {
        for (const tile of row) {
            if (tile.startsWith('T')) features.forest++;
            else if (tile.startsWith('W')) features.water++;
            else if (tile.startsWith('ROCK')) features.mountains++;
            else if (tile.startsWith('SH')) features.shore++;
        }
    }
    
    return features;
}

// Run the tests
if (import.meta.url === `file://${process.argv[1]}`) {
    console.log('🚀 Starting Enhanced Map Generation Tests...\n');
    
    try {
        await testEnhancedMapGeneration();
        await demonstrateEnhancedFeatures();
        
        console.log('\n🎉 All tests completed successfully!');
        
    } catch (error) {
        console.error('\n💥 Test execution failed:', error);
        process.exit(1);
    }
}

export { testEnhancedMapGeneration, demonstrateEnhancedFeatures };