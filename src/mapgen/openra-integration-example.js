/**
 * OpenRA Integration Example
 * 
 * Demonstrates how to use the OpenRA map extraction and WFC training system
 * to generate authentic C&C-style maps.
 */

import OpenRAMapExtractor from './OpenRAMapExtractor.js';
import WFCTrainingDataGenerator from './WFCTrainingDataGenerator.js';
import MapPatternAnalyzer from './MapPatternAnalyzer.js';
import WaveFunctionCollapse from './WaveFunctionCollapse.js';
import fs from 'fs';
import path from 'path';

/**
 * Complete workflow for extracting OpenRA maps and training WFC
 */
async function trainWFCFromOpenRAMaps() {
    console.log('=== OpenRA Map Extraction & WFC Training System ===\n');
    
    // Step 1: Extract maps from OpenRA
    console.log('Step 1: Extracting OpenRA maps...');
    const extractor = new OpenRAMapExtractor();
    
    // Example: Extract maps from a directory
    // You'll need to provide actual OpenRA map files
    const mapsDirectory = './openra-maps'; // Update this path
    
    let extractedMaps = [];
    
    // Check if we have .oramap files
    if (fs.existsSync(mapsDirectory)) {
        extractedMaps = await extractor.extractDirectory(mapsDirectory);
        console.log(`Extracted ${extractedMaps.length} maps`);
    } else {
        console.log('No OpenRA maps directory found, using example data...');
        // Create example map data for demonstration
        extractedMaps = createExampleMaps();
    }
    
    // Display extraction statistics
    const extractionStats = extractor.getStatistics();
    console.log('Extraction Statistics:', extractionStats);
    console.log('');
    
    // Step 2: Analyze map patterns
    console.log('Step 2: Analyzing map patterns...');
    const analyzer = new MapPatternAnalyzer();
    const analysisResults = analyzer.analyzeMaps(extractedMaps);
    
    console.log(`Found ${analysisResults.aggregatePatterns.commonBasePatterns.length} base patterns`);
    console.log(`Found ${analysisResults.aggregatePatterns.commonFeatures.length} terrain features`);
    console.log('');
    
    // Save analysis results
    analyzer.exportAnalysis(analysisResults, './map-analysis.json');
    
    // Step 3: Generate WFC training data
    console.log('Step 3: Generating WFC training data...');
    const trainingGenerator = new WFCTrainingDataGenerator();
    
    // Configure training parameters
    trainingGenerator.updateConfig({
        minPatternOccurrences: 2,
        includeDiagonals: false,
        patternSize: 2,
        augmentPatterns: true,
        filterRareTiles: true,
        rareThreshold: 0.001
    });
    
    const trainingData = trainingGenerator.generateTrainingData(extractedMaps);
    
    console.log('Training Data Summary:');
    console.log(`- Unique tiles: ${trainingData.metadata.uniqueTiles}`);
    console.log(`- Adjacency rules: ${Object.keys(trainingData.tileRules).length}`);
    console.log(`- Pattern library: ${trainingData.patterns.length} patterns`);
    console.log('');
    
    // Save training data
    await trainingGenerator.saveTrainingData(trainingData, './wfc-training-data.json');
    
    // Step 4: Use trained data with WFC
    console.log('Step 4: Generating map with trained WFC...');
    const wfc = new WaveFunctionCollapse(40, 30, trainingData.tileRules);
    
    const generatedMap = wfc.generate();
    console.log('Map generation complete!');
    
    // Display generation statistics
    const wfcStats = wfc.getStats();
    console.log('WFC Generation Statistics:', wfcStats);
    
    // Save generated map
    saveGeneratedMap(generatedMap, './generated-map.json');
    
    // Display recommendations
    console.log('\n=== Recommendations for Map Generation ===');
    analysisResults.recommendations.forEach(rec => {
        console.log(`[${rec.priority.toUpperCase()}] ${rec.category}: ${rec.suggestion}`);
        if (rec.details) {
            console.log(`  Details: ${rec.details}`);
        }
    });
    
    return {
        extractedMaps,
        analysisResults,
        trainingData,
        generatedMap
    };
}

/**
 * Create example maps for demonstration
 */
function createExampleMaps() {
    const maps = [];
    
    // Example map 1: Simple symmetric map
    const map1 = {
        name: 'Example Valley',
        width: 30,
        height: 30,
        terrain: []
    };
    
    // Generate terrain with patterns
    for (let y = 0; y < 30; y++) {
        map1.terrain[y] = [];
        for (let x = 0; x < 30; x++) {
            // Create a valley pattern
            const distFromCenter = Math.abs(x - 15) + Math.abs(y - 15);
            
            if (distFromCenter < 5) {
                // Center area - buildable
                map1.terrain[y][x] = `S0${(x + y) % 8 + 1}`;
            } else if (distFromCenter < 8) {
                // Transition area
                map1.terrain[y][x] = Math.random() > 0.5 ? `D0${(x + y) % 8 + 1}` : `S0${(x + y) % 8 + 1}`;
            } else if (distFromCenter < 12) {
                // Outer area - mixed terrain
                const rand = Math.random();
                if (rand < 0.3) {
                    map1.terrain[y][x] = `T0${(x + y) % 8 + 1}`;
                } else if (rand < 0.4) {
                    map1.terrain[y][x] = `ROCK${(x + y) % 7 + 1}`;
                } else {
                    map1.terrain[y][x] = `D0${(x + y) % 8 + 1}`;
                }
            } else {
                // Edge area
                if (x < 3 || x > 26 || y < 3 || y > 26) {
                    map1.terrain[y][x] = Math.random() > 0.7 ? 'W1' : 'W2';
                } else {
                    map1.terrain[y][x] = `D0${(x + y) % 8 + 1}`;
                }
            }
        }
    }
    
    maps.push(map1);
    
    // Example map 2: Choke point map
    const map2 = {
        name: 'Desert Pass',
        width: 25,
        height: 25,
        terrain: []
    };
    
    // Generate terrain with choke points
    for (let y = 0; y < 25; y++) {
        map2.terrain[y] = [];
        for (let x = 0; x < 25; x++) {
            // Create mountain passes
            if ((x === 12 && (y < 8 || y > 16)) || (y === 12 && (x < 8 || x > 16))) {
                map2.terrain[y][x] = `ROCK${(x + y) % 7 + 1}`;
            } else if (Math.abs(x - 12) < 2 || Math.abs(y - 12) < 2) {
                // Pass areas
                map2.terrain[y][x] = `D0${(x + y) % 8 + 1}`;
            } else if ((x < 10 && y < 10) || (x > 14 && y > 14)) {
                // Base areas
                map2.terrain[y][x] = `S0${(x + y) % 8 + 1}`;
            } else {
                // Mixed terrain
                const rand = Math.random();
                if (rand < 0.6) {
                    map2.terrain[y][x] = `D0${(x + y) % 8 + 1}`;
                } else if (rand < 0.8) {
                    map2.terrain[y][x] = `S0${(x + y) % 8 + 1}`;
                } else {
                    map2.terrain[y][x] = `T0${(x + y) % 5 + 1}`;
                }
            }
        }
    }
    
    maps.push(map2);
    
    return maps;
}

/**
 * Save generated map to file
 */
function saveGeneratedMap(map, outputPath) {
    const mapData = {
        width: map[0].length,
        height: map.length,
        terrain: map,
        generatedAt: new Date().toISOString()
    };
    
    fs.writeFileSync(outputPath, JSON.stringify(mapData, null, 2));
    console.log(`Generated map saved to: ${outputPath}`);
}

/**
 * Load and apply pre-trained WFC rules
 */
async function loadTrainedWFC(trainingDataPath) {
    try {
        const trainingData = JSON.parse(fs.readFileSync(trainingDataPath, 'utf8'));
        console.log(`Loaded training data with ${Object.keys(trainingData.tileRules).length} tile rules`);
        
        return trainingData;
    } catch (error) {
        console.error('Error loading training data:', error.message);
        return null;
    }
}

/**
 * Generate multiple maps using trained data
 */
async function generateMapBatch(trainingData, count = 5) {
    const maps = [];
    
    for (let i = 0; i < count; i++) {
        console.log(`Generating map ${i + 1}/${count}...`);
        
        const wfc = new WaveFunctionCollapse(40, 30, trainingData.tileRules);
        const map = wfc.generate();
        
        maps.push({
            id: i + 1,
            terrain: map,
            stats: wfc.getStats()
        });
    }
    
    return maps;
}

/**
 * Validate generated map quality
 */
function validateMapQuality(map, analyzer) {
    const mapData = {
        name: 'Generated Map',
        width: map[0].length,
        height: map.length,
        terrain: map
    };
    
    const analysis = analyzer.analyzeMap(mapData);
    
    const quality = {
        hasBases: analysis.bases.length >= 2,
        hasChokePoints: analysis.chokePoints.length > 0,
        hasFeatures: analysis.terrainFeatures.length > 3,
        isBalanced: analysis.balance.overall > 0.6,
        tacticalValue: analysis.tacticalValue,
        overallScore: 0
    };
    
    // Calculate overall quality score
    quality.overallScore = (
        (quality.hasBases ? 25 : 0) +
        (quality.hasChokePoints ? 20 : 0) +
        (quality.hasFeatures ? 20 : 0) +
        (quality.isBalanced ? 25 : 0) +
        (quality.tacticalValue / 100 * 10)
    );
    
    return quality;
}

// Main execution
if (import.meta.url === `file://${process.argv[1]}`) {
    console.log('Running OpenRA WFC Training System...\n');
    
    trainWFCFromOpenRAMaps()
        .then(results => {
            console.log('\n=== Training Complete ===');
            console.log('System is ready to generate authentic C&C-style maps!');
            
            // Validate a generated map
            const analyzer = new MapPatternAnalyzer();
            const quality = validateMapQuality(results.generatedMap, analyzer);
            
            console.log('\nGenerated Map Quality:');
            console.log(`- Has bases: ${quality.hasBases ? 'Yes' : 'No'}`);
            console.log(`- Has choke points: ${quality.hasChokePoints ? 'Yes' : 'No'}`);
            console.log(`- Has terrain features: ${quality.hasFeatures ? 'Yes' : 'No'}`);
            console.log(`- Is balanced: ${quality.isBalanced ? 'Yes' : 'No'}`);
            console.log(`- Tactical value: ${quality.tacticalValue}/100`);
            console.log(`- Overall quality score: ${quality.overallScore}/100`);
        })
        .catch(error => {
            console.error('Error during training:', error);
        });
}

export {
    trainWFCFromOpenRAMaps,
    loadTrainedWFC,
    generateMapBatch,
    validateMapQuality,
    createExampleMaps
};