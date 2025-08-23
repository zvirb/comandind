/**
 * Advanced Map Generation System - Usage Examples
 * 
 * This file demonstrates how to use the advanced map generation system
 * in various scenarios and configurations.
 */

import AdvancedMapGenerator, { 
    createCompetitiveGenerator, 
    createCampaignGenerator,
    validateMap,
    getAvailablePresets
} from './index.js';

// Example 1: Basic Map Generation
async function basicExample() {
    console.log('\n=== Basic Map Generation Example ===');
    
    const generator = new AdvancedMapGenerator({
        width: 40,
        height: 30,
        algorithm: 'hybrid',
        climate: 'temperate'
    });
    
    try {
        const mapData = await generator.generateMap();
        
        console.log('Generated map:', {
            dimensions: `${mapData.metadata.width}x${mapData.metadata.height}`,
            algorithm: mapData.metadata.algorithm,
            climate: mapData.metadata.climate,
            resourceFields: mapData.resources.length,
            validationScore: mapData.validation?.overall.score || 'N/A'
        });
        
        return mapData;
    } catch (error) {
        console.error('Generation failed:', error.message);
        return null;
    }
}

// Example 2: Competitive 1v1 Map
async function competitive1v1Example() {
    console.log('\n=== Competitive 1v1 Map Example ===');
    
    const generator = createCompetitiveGenerator(2);
    
    try {
        const mapData = await generator.generateMap({
            climate: 'desert',
            qualityThreshold: 85
        });
        
        console.log('1v1 Map generated:', {
            players: mapData.startingPositions.length,
            symmetry: mapData.metadata.symmetryType || 'N/A',
            score: mapData.validation.overall.score,
            grade: mapData.validation.overall.grade,
            balanced: mapData.validation.overall.valid
        });
        
        // Show starting positions
        mapData.startingPositions.forEach((pos, i) => {
            console.log(`Player ${i + 1}: (${pos.x}, ${pos.y})`);
        });
        
        return mapData;
    } catch (error) {
        console.error('1v1 generation failed:', error.message);
        return null;
    }
}

// Example 3: Large 4-Player Map with Custom Settings
async function large4PlayerExample() {
    console.log('\n=== Large 4-Player Map Example ===');
    
    const generator = new AdvancedMapGenerator({
        width: 60,
        height: 45,
        playerCount: 4,
        algorithm: 'symmetric',
        symmetryType: 'rotational',
        
        // Environment settings
        climate: 'temperate',
        mountainDensity: 0.12,
        waterCoverage: 0.18,
        forestDensity: 0.25,
        
        // Resource settings
        resourceDensity: 0.10,
        resourceBalance: true,
        multipleResourceTypes: true,
        
        // Quality settings
        enableValidation: true,
        qualityThreshold: 80,
        maxGenerationAttempts: 3
    });
    
    try {
        const mapData = await generator.generateMap();
        
        console.log('Large 4-player map:', {
            size: `${mapData.metadata.width}x${mapData.metadata.height}`,
            players: mapData.startingPositions.length,
            resources: {
                totalFields: mapData.resources.length,
                totalTiles: mapData.resources.reduce((sum, field) => sum + field.length, 0)
            },
            validation: {
                score: mapData.validation.overall.score,
                issues: mapData.validation.suggestions.length
            }
        });
        
        // Show any validation issues
        if (mapData.validation.suggestions.length > 0) {
            console.log('Validation suggestions:');
            mapData.validation.suggestions.slice(0, 3).forEach(suggestion => {
                console.log(`- ${suggestion.message}`);
            });
        }
        
        return mapData;
    } catch (error) {
        console.error('Large map generation failed:', error.message);
        return null;
    }
}

// Example 4: Campaign Map with Custom Terrain
async function campaignMapExample() {
    console.log('\n=== Campaign Map Example ===');
    
    const generator = createCampaignGenerator({
        climate: 'volcanic',
        mountainDensity: 0.20,
        waterCoverage: 0.05,
        forestDensity: 0.10,
        resourceDensity: 0.12,
        enableValidation: false // Skip validation for faster generation
    });
    
    try {
        const mapData = await generator.generateMap();
        
        console.log('Campaign map generated:', {
            climate: mapData.metadata.climate,
            singlePlayer: mapData.startingPositions.length === 1,
            resourceRich: mapData.resources.length > 6,
            terrainComplex: 'volcanic setting'
        });
        
        return mapData;
    } catch (error) {
        console.error('Campaign generation failed:', error.message);
        return null;
    }
}

// Example 5: Using Individual Components
async function componentExample() {
    console.log('\n=== Individual Components Example ===');
    
    // Import individual components
    const { WaveFunctionCollapse, ResourcePlacer, MapValidator } = await import('./index.js');
    
    // Create simple terrain using WFC
    const tileRules = createSimpleTileRules();
    const wfc = new WaveFunctionCollapse(30, 20, tileRules);
    const terrain = wfc.generate();
    
    console.log('WFC terrain generated:', {
        dimensions: `${terrain[0].length}x${terrain.length}`,
        stats: wfc.getStats()
    });
    
    // Add resources
    const startingPositions = [{ x: 5, y: 5 }, { x: 25, y: 15 }];
    const resourcePlacer = new ResourcePlacer(30, 20, {
        resourceDensity: 0.06,
        playerPositions: startingPositions
    });
    
    const resources = resourcePlacer.placeResources(terrain, startingPositions);
    console.log('Resources placed:', {
        fields: resources.length,
        totalTiles: resources.reduce((sum, field) => sum + field.length, 0)
    });
    
    // Validate the result
    const mapData = {
        terrain,
        resources,
        startingPositions,
        metadata: { width: 30, height: 20 }
    };
    
    const validation = validateMap(mapData);
    console.log('Validation result:', {
        score: validation.overall.score,
        valid: validation.overall.valid,
        issues: validation.suggestions.length
    });
    
    return mapData;
}

// Example 6: Performance Comparison
async function performanceExample() {
    console.log('\n=== Performance Comparison Example ===');
    
    const algorithms = ['classic', 'hybrid', 'wfc'];
    const results = {};
    
    for (const algorithm of algorithms) {
        const generator = new AdvancedMapGenerator({
            width: 40,
            height: 30,
            algorithm,
            enableValidation: false // For fair timing
        });
        
        const startTime = performance.now();
        
        try {
            await generator.generateMap();
            const endTime = performance.now();
            
            results[algorithm] = {
                time: Math.round(endTime - startTime),
                success: true
            };
        } catch (error) {
            results[algorithm] = {
                time: 0,
                success: false,
                error: error.message
            };
        }
    }
    
    console.log('Performance results:');
    Object.entries(results).forEach(([algorithm, result]) => {
        if (result.success) {
            console.log(`${algorithm.padEnd(10)}: ${result.time}ms`);
        } else {
            console.log(`${algorithm.padEnd(10)}: FAILED (${result.error})`);
        }
    });
    
    return results;
}

// Example 7: Presets Showcase
async function presetsExample() {
    console.log('\n=== Available Presets Example ===');
    
    const presets = getAvailablePresets();
    console.log('Available presets:', Object.keys(presets));
    
    // Try the temperate valley preset
    const generator = new AdvancedMapGenerator({
        ...presets.temperateValley,
        playerCount: 2,
        algorithm: 'hybrid',
        enableValidation: true
    });
    
    try {
        const mapData = await generator.generateMap();
        
        console.log('Temperate valley map:', {
            climate: mapData.metadata.climate,
            validation: mapData.validation.overall.score,
            features: {
                hasWater: mapData.terrain.some(row => row.some(tile => tile.startsWith('W'))),
                hasForests: mapData.terrain.some(row => row.some(tile => tile.startsWith('T'))),
                hasMountains: mapData.terrain.some(row => row.some(tile => tile.startsWith('ROCK')))
            }
        });
        
        return mapData;
    } catch (error) {
        console.error('Preset generation failed:', error.message);
        return null;
    }
}

// Helper function to create simple tile rules
function createSimpleTileRules() {
    const sandTiles = ['S01', 'S02', 'S03'];
    const dirtTiles = ['D01', 'D02', 'D03'];
    const waterTiles = ['W1', 'W2'];
    
    const rules = {};
    
    // Sand rules
    sandTiles.forEach(tile => {
        rules[tile] = {
            frequency: 0.5,
            adjacency: {
                up: [...sandTiles, ...dirtTiles],
                down: [...sandTiles, ...dirtTiles],
                left: [...sandTiles, ...dirtTiles],
                right: [...sandTiles, ...dirtTiles]
            }
        };
    });
    
    // Dirt rules
    dirtTiles.forEach(tile => {
        rules[tile] = {
            frequency: 0.3,
            adjacency: {
                up: [...dirtTiles, ...sandTiles],
                down: [...dirtTiles, ...sandTiles],
                left: [...dirtTiles, ...sandTiles],
                right: [...dirtTiles, ...sandTiles]
            }
        };
    });
    
    // Water rules
    waterTiles.forEach(tile => {
        rules[tile] = {
            frequency: 0.1,
            adjacency: {
                up: waterTiles,
                down: waterTiles,
                left: waterTiles,
                right: waterTiles
            }
        };
    });
    
    return rules;
}

// Main demo function
async function runExamples() {
    console.log('Advanced Map Generation System - Examples');
    console.log('=========================================');
    
    try {
        // Run examples
        await basicExample();
        await competitive1v1Example();
        await large4PlayerExample();
        await campaignMapExample();
        await componentExample();
        await performanceExample();
        await presetsExample();
        
        console.log('\n=== All Examples Completed Successfully ===');
        
    } catch (error) {
        console.error('Example execution failed:', error);
    }
}

// Export for use in other modules
export {
    basicExample,
    competitive1v1Example,
    large4PlayerExample,
    campaignMapExample,
    componentExample,
    performanceExample,
    presetsExample,
    runExamples
};

// Run examples if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    runExamples();
}