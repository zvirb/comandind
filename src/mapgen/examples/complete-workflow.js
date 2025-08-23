/**
 * Complete OpenRA Extraction to Map Generation Workflow
 * 
 * This example demonstrates the complete pipeline from OpenRA sprite/map extraction
 * to advanced map generation using the Command & Conquer clone's map generation system.
 * 
 * Workflow:
 * 1. Extract OpenRA assets and maps
 * 2. Train WFC from OpenRA map patterns
 * 3. Generate new maps using the trained system
 * 4. Validate and optimize map quality
 * 5. Export maps for use in the game
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Import map generation components
import AdvancedMapGenerator from '../AdvancedMapGenerator.js';
import OpenRAMapExtractor from '../OpenRAMapExtractor.js';
import WFCTrainingDataGenerator from '../WFCTrainingDataGenerator.js';
import MapPatternAnalyzer from '../MapPatternAnalyzer.js';
import WaveFunctionCollapse from '../WaveFunctionCollapse.js';
import MapValidator from '../MapValidator.js';
import ResourcePlacer from '../ResourcePlacer.js';
import { createMapGenerator, createCompetitiveGenerator, validateMap } from '../index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Configuration for the complete workflow
 */
const WORKFLOW_CONFIG = {
    // OpenRA extraction settings
    openRA: {
        mapsDirectory: './openra-maps',
        spritesDirectory: './public/assets/sprites/cnc-converted',
        extractionOutput: './extracted-maps',
        fallbackToExamples: true
    },
    
    // WFC training settings
    training: {
        minPatternOccurrences: 2,
        patternSize: 2,
        includeDiagonals: false,
        augmentPatterns: true,
        filterRareTiles: true,
        rareThreshold: 0.001,
        outputPath: './wfc-training-data.json'
    },
    
    // Map generation settings
    generation: {
        outputDirectory: './generated-maps',
        mapCount: 5,
        mapSizes: [
            { width: 40, height: 30, name: 'small' },
            { width: 60, height: 45, name: 'medium' },
            { width: 80, height: 60, name: 'large' }
        ],
        playerCounts: [2, 4, 6, 8]
    },
    
    // Quality validation settings
    validation: {
        qualityThreshold: 75,
        enableMLValidation: false, // Set to true if TensorFlow is available
        resourceBalanceTolerance: 0.15,
        minBuildablePercentage: 0.6
    }
};

/**
 * Step 1: Extract OpenRA Assets and Maps
 */
async function extractOpenRAAssets() {
    console.log('=== Step 1: OpenRA Asset Extraction ===\n');
    
    const extractor = new OpenRAMapExtractor();
    let extractedMaps = [];
    
    try {
        // Check for OpenRA maps directory
        if (fs.existsSync(WORKFLOW_CONFIG.openRA.mapsDirectory)) {
            console.log('Found OpenRA maps directory, extracting...');
            extractedMaps = await extractor.extractDirectory(WORKFLOW_CONFIG.openRA.mapsDirectory);
            console.log(`✓ Extracted ${extractedMaps.length} OpenRA maps`);
        } else {
            console.log('OpenRA maps directory not found.');
            
            if (WORKFLOW_CONFIG.openRA.fallbackToExamples) {
                console.log('Using built-in example maps for demonstration...');
                extractedMaps = createExampleMaps();
                console.log(`✓ Created ${extractedMaps.length} example maps`);
            } else {
                throw new Error('No maps available for extraction');
            }
        }
        
        // Display extraction statistics
        const stats = extractor.getStatistics();
        console.log('Extraction Statistics:');
        console.log(`- Total maps processed: ${stats.mapsProcessed || extractedMaps.length}`);
        console.log(`- Successful extractions: ${stats.successful || extractedMaps.length}`);
        console.log(`- Failed extractions: ${stats.failed || 0}`);
        console.log(`- Unique tile types found: ${stats.uniqueTiles || 'calculating...'}`);
        
        // Save extracted maps
        await saveExtractedMaps(extractedMaps, WORKFLOW_CONFIG.openRA.extractionOutput);
        
        return extractedMaps;
        
    } catch (error) {
        console.error('❌ Error during OpenRA extraction:', error.message);
        
        if (WORKFLOW_CONFIG.openRA.fallbackToExamples) {
            console.log('Falling back to example maps...');
            return createExampleMaps();
        }
        
        throw error;
    }
}

/**
 * Step 2: Analyze Map Patterns and Train WFC
 */
async function trainWFCFromMaps(extractedMaps) {
    console.log('\n=== Step 2: Map Pattern Analysis & WFC Training ===\n');
    
    // Analyze map patterns
    console.log('Analyzing map patterns...');
    const analyzer = new MapPatternAnalyzer();
    const analysisResults = analyzer.analyzeMaps(extractedMaps);
    
    console.log(`✓ Found ${analysisResults.aggregatePatterns.commonBasePatterns.length} base patterns`);
    console.log(`✓ Found ${analysisResults.aggregatePatterns.commonFeatures.length} terrain features`);
    console.log(`✓ Found ${analysisResults.aggregatePatterns.chokePoints.length} choke point patterns`);
    
    // Save analysis results
    await analyzer.exportAnalysis(analysisResults, './map-pattern-analysis.json');
    
    // Generate WFC training data
    console.log('\nGenerating WFC training data...');
    const trainingGenerator = new WFCTrainingDataGenerator();
    
    // Configure training parameters
    trainingGenerator.updateConfig(WORKFLOW_CONFIG.training);
    
    const trainingData = trainingGenerator.generateTrainingData(extractedMaps);
    
    console.log('Training Data Summary:');
    console.log(`- Unique tiles: ${trainingData.metadata.uniqueTiles}`);
    console.log(`- Adjacency rules: ${Object.keys(trainingData.tileRules).length}`);
    console.log(`- Pattern library: ${trainingData.patterns.length} patterns`);
    console.log(`- Coverage: ${(trainingData.metadata.coverage * 100).toFixed(1)}%`);
    
    // Save training data
    await trainingGenerator.saveTrainingData(trainingData, WORKFLOW_CONFIG.training.outputPath);
    console.log(`✓ Training data saved to ${WORKFLOW_CONFIG.training.outputPath}`);
    
    return { analysisResults, trainingData };
}

/**
 * Step 3: Generate Maps Using Multiple Algorithms
 */
async function generateMapsWithVariousAlgorithms(trainingData) {
    console.log('\n=== Step 3: Advanced Map Generation ===\n');
    
    const generatedMaps = [];
    
    // Ensure output directory exists
    ensureDirectory(WORKFLOW_CONFIG.generation.outputDirectory);
    
    for (const size of WORKFLOW_CONFIG.generation.mapSizes) {
        for (const playerCount of WORKFLOW_CONFIG.generation.playerCounts) {
            console.log(`Generating ${size.name} ${playerCount}-player maps...`);
            
            // 1. WFC-based generation using trained data
            const wfcMap = await generateWFCMap(trainingData, size, playerCount);
            if (wfcMap) {
                generatedMaps.push(wfcMap);
                console.log(`  ✓ WFC map generated`);
            }
            
            // 2. Competitive symmetric generation
            const competitiveMap = await generateCompetitiveMap(size, playerCount);
            if (competitiveMap) {
                generatedMaps.push(competitiveMap);
                console.log(`  ✓ Competitive map generated`);
            }
            
            // 3. Hybrid generation (WFC + symmetric)
            const hybridMap = await generateHybridMap(trainingData, size, playerCount);
            if (hybridMap) {
                generatedMaps.push(hybridMap);
                console.log(`  ✓ Hybrid map generated`);
            }
        }
    }
    
    console.log(`\n✓ Generated ${generatedMaps.length} total maps`);
    return generatedMaps;
}

/**
 * Step 4: Validate and Optimize Map Quality
 */
async function validateAndOptimizeMaps(generatedMaps) {
    console.log('\n=== Step 4: Map Quality Validation & Optimization ===\n');
    
    const validator = new MapValidator({
        resourceBalanceTolerance: WORKFLOW_CONFIG.validation.resourceBalanceTolerance,
        minBuildablePercentage: WORKFLOW_CONFIG.validation.minBuildablePercentage
    });
    
    const validatedMaps = [];
    
    for (const mapData of generatedMaps) {
        console.log(`Validating map: ${mapData.name}`);
        
        // Validate map quality
        const validation = validator.validateMap(mapData);
        mapData.validation = validation;
        
        console.log(`  Score: ${validation.overall.score}/100 (${validation.overall.grade})`);
        
        // Apply optimizations if score is below threshold
        if (validation.overall.score < WORKFLOW_CONFIG.validation.qualityThreshold) {
            console.log(`  Optimizing map (score below ${WORKFLOW_CONFIG.validation.qualityThreshold})...`);
            
            const optimizedMap = await optimizeMap(mapData, validation);
            if (optimizedMap) {
                const revalidation = validator.validateMap(optimizedMap);
                optimizedMap.validation = revalidation;
                
                console.log(`  ✓ Optimized score: ${revalidation.overall.score}/100`);
                validatedMaps.push(optimizedMap);
            } else {
                validatedMaps.push(mapData);
            }
        } else {
            console.log(`  ✓ Map meets quality threshold`);
            validatedMaps.push(mapData);
        }
    }
    
    return validatedMaps;
}

/**
 * Step 5: Export Maps for Game Use
 */
async function exportMapsForGame(validatedMaps) {
    console.log('\n=== Step 5: Export Maps for Game Integration ===\n');
    
    const exportDirectory = path.join(WORKFLOW_CONFIG.generation.outputDirectory, 'game-ready');
    ensureDirectory(exportDirectory);
    
    const exportedMaps = [];
    
    for (const mapData of validatedMaps) {
        // Only export high-quality maps
        if (mapData.validation.overall.score >= WORKFLOW_CONFIG.validation.qualityThreshold) {
            const exportPath = path.join(exportDirectory, `${mapData.name}.json`);
            
            // Create game-compatible format
            const gameMap = {
                id: mapData.name.toLowerCase().replace(/\s+/g, '-'),
                name: mapData.name,
                width: mapData.width,
                height: mapData.height,
                playerCount: mapData.playerCount,
                terrain: mapData.terrain,
                resources: mapData.resources || [],
                startingPositions: mapData.startingPositions || [],
                metadata: {
                    algorithm: mapData.algorithm,
                    generated: new Date().toISOString(),
                    quality: mapData.validation.overall,
                    version: '1.0.0'
                }
            };
            
            // Save map file
            fs.writeFileSync(exportPath, JSON.stringify(gameMap, null, 2));
            exportedMaps.push(gameMap);
            
            console.log(`✓ Exported: ${mapData.name} (${mapData.validation.overall.score}/100)`);
        } else {
            console.log(`⚠ Skipped: ${mapData.name} (quality too low: ${mapData.validation.overall.score}/100)`);
        }
    }
    
    // Create map index file
    const mapIndex = {
        version: '1.0.0',
        generated: new Date().toISOString(),
        maps: exportedMaps.map(map => ({
            id: map.id,
            name: map.name,
            playerCount: map.playerCount,
            size: `${map.width}x${map.height}`,
            quality: map.metadata.quality.score,
            algorithm: map.metadata.algorithm
        }))
    };
    
    fs.writeFileSync(path.join(exportDirectory, 'map-index.json'), JSON.stringify(mapIndex, null, 2));
    
    console.log(`\n✓ Exported ${exportedMaps.length} maps for game use`);
    console.log(`✓ Map index created at: ${path.join(exportDirectory, 'map-index.json')}`);
    
    return exportedMaps;
}

/**
 * Helper Functions
 */

async function generateWFCMap(trainingData, size, playerCount) {
    try {
        const wfc = new WaveFunctionCollapse(size.width, size.height, trainingData.tileRules);
        const terrain = wfc.generate();
        
        const resourcePlacer = new ResourcePlacer(size.width, size.height, {
            resourceDensity: 0.08,
            resourceTypes: ['green', 'blue'],
            playerCount: playerCount
        });
        
        const startingPositions = generateStartingPositions(size.width, size.height, playerCount);
        const resources = resourcePlacer.placeResources(terrain, startingPositions);
        
        return {
            name: `WFC ${size.name} ${playerCount}P`,
            algorithm: 'wfc',
            width: size.width,
            height: size.height,
            playerCount: playerCount,
            terrain: terrain,
            resources: resources,
            startingPositions: startingPositions,
            stats: wfc.getStats()
        };
    } catch (error) {
        console.error(`  ❌ Failed to generate WFC map: ${error.message}`);
        return null;
    }
}

async function generateCompetitiveMap(size, playerCount) {
    try {
        const generator = createCompetitiveGenerator(playerCount);
        generator.updateConfig({
            width: size.width,
            height: size.height,
            enableValidation: true,
            resourceBalance: true
        });
        
        const mapData = await generator.generateMap();
        mapData.name = `Competitive ${size.name} ${playerCount}P`;
        mapData.algorithm = 'competitive';
        
        return mapData;
    } catch (error) {
        console.error(`  ❌ Failed to generate competitive map: ${error.message}`);
        return null;
    }
}

async function generateHybridMap(trainingData, size, playerCount) {
    try {
        const generator = new AdvancedMapGenerator({
            width: size.width,
            height: size.height,
            playerCount: playerCount,
            algorithm: 'hybrid',
            wfcTrainingData: trainingData,
            symmetryType: playerCount <= 4 ? 'rotational' : 'mirror',
            resourceBalance: true,
            enableValidation: true
        });
        
        const mapData = await generator.generateMap();
        mapData.name = `Hybrid ${size.name} ${playerCount}P`;
        mapData.algorithm = 'hybrid';
        
        return mapData;
    } catch (error) {
        console.error(`  ❌ Failed to generate hybrid map: ${error.message}`);
        return null;
    }
}

async function optimizeMap(mapData, validation) {
    // Apply optimization strategies based on validation issues
    let optimizedMap = JSON.parse(JSON.stringify(mapData)); // Deep clone
    
    if (!validation.accessibility.allReachable) {
        console.log('    Fixing accessibility issues...');
        optimizedMap = fixAccessibilityIssues(optimizedMap);
    }
    
    if (!validation.resources.balanced) {
        console.log('    Balancing resources...');
        optimizedMap = balanceResources(optimizedMap);
    }
    
    if (validation.buildable.percentage < WORKFLOW_CONFIG.validation.minBuildablePercentage) {
        console.log('    Increasing buildable area...');
        optimizedMap = increaseBuildableArea(optimizedMap);
    }
    
    optimizedMap.name += ' (Optimized)';
    return optimizedMap;
}

function fixAccessibilityIssues(mapData) {
    // Simple accessibility fix: replace impassable terrain with passable alternatives
    const terrain = mapData.terrain;
    
    for (let y = 0; y < terrain.length; y++) {
        for (let x = 0; x < terrain[y].length; x++) {
            const tile = terrain[y][x];
            
            // Replace water with shore if isolated
            if (tile.startsWith('W') && isIsolatedWater(terrain, x, y)) {
                terrain[y][x] = `SH${Math.floor(Math.random() * 6) + 1}`;
            }
            
            // Replace rocks with dirt if blocking important paths
            if (tile.startsWith('ROCK') && isBlockingPath(terrain, x, y)) {
                terrain[y][x] = `D0${Math.floor(Math.random() * 8) + 1}`;
            }
        }
    }
    
    return mapData;
}

function balanceResources(mapData) {
    if (!mapData.resources || mapData.resources.length === 0) {
        return mapData;
    }
    
    // Redistribute resources more evenly among starting positions
    const resourcePlacer = new ResourcePlacer(mapData.width, mapData.height, {
        resourceDensity: 0.08,
        resourceTypes: ['green', 'blue'],
        playerCount: mapData.playerCount,
        balanceRadius: 15
    });
    
    mapData.resources = resourcePlacer.placeResources(mapData.terrain, mapData.startingPositions);
    return mapData;
}

function increaseBuildableArea(mapData) {
    // Convert some impassable terrain to buildable terrain
    const terrain = mapData.terrain;
    let conversions = 0;
    const maxConversions = Math.floor(mapData.width * mapData.height * 0.1); // Convert up to 10%
    
    for (let y = 0; y < terrain.length && conversions < maxConversions; y++) {
        for (let x = 0; x < terrain[y].length && conversions < maxConversions; x++) {
            const tile = terrain[y][x];
            
            // Convert rocks and trees to dirt/sand if near starting positions
            if ((tile.startsWith('ROCK') || tile.startsWith('T0')) && 
                isNearStartingPosition(mapData.startingPositions, x, y, 8)) {
                terrain[y][x] = Math.random() > 0.5 ? 
                    `S0${Math.floor(Math.random() * 8) + 1}` : 
                    `D0${Math.floor(Math.random() * 8) + 1}`;
                conversions++;
            }
        }
    }
    
    return mapData;
}

function generateStartingPositions(width, height, playerCount) {
    const positions = [];
    const centerX = Math.floor(width / 2);
    const centerY = Math.floor(height / 2);
    const radius = Math.min(width, height) * 0.35;
    
    for (let i = 0; i < playerCount; i++) {
        const angle = (i / playerCount) * 2 * Math.PI;
        const x = Math.floor(centerX + Math.cos(angle) * radius);
        const y = Math.floor(centerY + Math.sin(angle) * radius);
        
        positions.push({ x, y, playerId: i + 1 });
    }
    
    return positions;
}

function createExampleMaps() {
    // Create example maps for demonstration
    return [
        {
            name: 'Example Valley',
            width: 30,
            height: 30,
            terrain: generateExampleTerrain(30, 30, 'valley')
        },
        {
            name: 'Desert Pass',
            width: 25,
            height: 25,
            terrain: generateExampleTerrain(25, 25, 'desert')
        },
        {
            name: 'Forest Clearing',
            width: 35,
            height: 35,
            terrain: generateExampleTerrain(35, 35, 'forest')
        }
    ];
}

function generateExampleTerrain(width, height, type) {
    const terrain = [];
    
    for (let y = 0; y < height; y++) {
        terrain[y] = [];
        for (let x = 0; x < width; x++) {
            const distFromCenter = Math.sqrt((x - width/2)**2 + (y - height/2)**2);
            const maxDist = Math.sqrt((width/2)**2 + (height/2)**2);
            const normalizedDist = distFromCenter / maxDist;
            
            let tile;
            switch (type) {
                case 'valley':
                    if (normalizedDist < 0.3) {
                        tile = `S0${(x + y) % 8 + 1}`;
                    } else if (normalizedDist < 0.6) {
                        tile = `D0${(x + y) % 8 + 1}`;
                    } else {
                        tile = Math.random() > 0.7 ? `T0${(x + y) % 9 + 1}` : `ROCK${(x + y) % 7 + 1}`;
                    }
                    break;
                case 'desert':
                    if (normalizedDist < 0.4) {
                        tile = `S0${(x + y) % 8 + 1}`;
                    } else {
                        tile = Math.random() > 0.8 ? `ROCK${(x + y) % 7 + 1}` : `D0${(x + y) % 8 + 1}`;
                    }
                    break;
                case 'forest':
                    if (normalizedDist < 0.3) {
                        tile = `S0${(x + y) % 8 + 1}`;
                    } else if (normalizedDist < 0.7) {
                        tile = Math.random() > 0.6 ? `T0${(x + y) % 9 + 1}` : `D0${(x + y) % 8 + 1}`;
                    } else {
                        tile = `T0${(x + y) % 9 + 1}`;
                    }
                    break;
                default:
                    tile = `S0${(x + y) % 8 + 1}`;
            }
            
            terrain[y][x] = tile;
        }
    }
    
    return terrain;
}

async function saveExtractedMaps(maps, outputPath) {
    ensureDirectory(outputPath);
    
    const extractionData = {
        extractedAt: new Date().toISOString(),
        mapCount: maps.length,
        maps: maps
    };
    
    fs.writeFileSync(path.join(outputPath, 'extracted-maps.json'), JSON.stringify(extractionData, null, 2));
    console.log(`✓ Extracted maps saved to: ${outputPath}`);
}

function ensureDirectory(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

// Utility functions for optimization
function isIsolatedWater(terrain, x, y) {
    const neighbors = [
        [-1, -1], [-1, 0], [-1, 1],
        [0, -1],           [0, 1],
        [1, -1],  [1, 0],  [1, 1]
    ];
    
    let waterNeighbors = 0;
    for (const [dx, dy] of neighbors) {
        const nx = x + dx;
        const ny = y + dy;
        
        if (nx >= 0 && nx < terrain[0].length && ny >= 0 && ny < terrain.length) {
            if (terrain[ny][nx].startsWith('W')) {
                waterNeighbors++;
            }
        }
    }
    
    return waterNeighbors < 2;
}

function isBlockingPath(terrain, x, y) {
    // Simple heuristic: check if this rock is in a corridor
    const width = terrain[0].length;
    const height = terrain.length;
    
    // Check horizontal corridor
    let leftClear = x > 0 && !terrain[y][x-1].startsWith('ROCK') && !terrain[y][x-1].startsWith('W');
    let rightClear = x < width-1 && !terrain[y][x+1].startsWith('ROCK') && !terrain[y][x+1].startsWith('W');
    
    // Check vertical corridor  
    let topClear = y > 0 && !terrain[y-1][x].startsWith('ROCK') && !terrain[y-1][x].startsWith('W');
    let bottomClear = y < height-1 && !terrain[y+1][x].startsWith('ROCK') && !terrain[y+1][x].startsWith('W');
    
    return (leftClear && rightClear) || (topClear && bottomClear);
}

function isNearStartingPosition(startingPositions, x, y, radius) {
    for (const pos of startingPositions) {
        const distance = Math.sqrt((x - pos.x)**2 + (y - pos.y)**2);
        if (distance <= radius) {
            return true;
        }
    }
    return false;
}

/**
 * Main Workflow Execution
 */
async function runCompleteWorkflow() {
    console.log('🚀 Starting Complete OpenRA to Map Generation Workflow\n');
    console.log('This workflow will:');
    console.log('1. Extract OpenRA assets and maps');
    console.log('2. Analyze patterns and train WFC');
    console.log('3. Generate maps with various algorithms');
    console.log('4. Validate and optimize map quality');
    console.log('5. Export maps for game use\n');
    
    const startTime = Date.now();
    
    try {
        // Step 1: Extract OpenRA assets
        const extractedMaps = await extractOpenRAAssets();
        
        // Step 2: Train WFC from maps
        const { analysisResults, trainingData } = await trainWFCFromMaps(extractedMaps);
        
        // Step 3: Generate maps
        const generatedMaps = await generateMapsWithVariousAlgorithms(trainingData);
        
        // Step 4: Validate and optimize
        const validatedMaps = await validateAndOptimizeMaps(generatedMaps);
        
        // Step 5: Export for game
        const exportedMaps = await exportMapsForGame(validatedMaps);
        
        const endTime = Date.now();
        const duration = (endTime - startTime) / 1000;
        
        console.log('\n🎉 Complete Workflow Finished Successfully!');
        console.log(`⏱ Total time: ${duration.toFixed(2)} seconds`);
        console.log(`📊 Generated ${generatedMaps.length} maps, exported ${exportedMaps.length} for game use`);
        console.log('\nWorkflow Summary:');
        console.log(`- Extracted maps: ${extractedMaps.length}`);
        console.log(`- Training patterns: ${trainingData.patterns.length}`);
        console.log(`- Generated maps: ${generatedMaps.length}`);
        console.log(`- High-quality maps: ${exportedMaps.length}`);
        console.log(`- Average quality: ${(validatedMaps.reduce((sum, map) => sum + map.validation.overall.score, 0) / validatedMaps.length).toFixed(1)}/100`);
        
        return {
            extractedMaps,
            analysisResults,
            trainingData,
            generatedMaps,
            validatedMaps,
            exportedMaps,
            duration
        };
        
    } catch (error) {
        console.error('❌ Workflow failed:', error.message);
        console.error('Stack trace:', error.stack);
        throw error;
    }
}

// Export the workflow and individual functions
export {
    runCompleteWorkflow,
    extractOpenRAAssets,
    trainWFCFromMaps,
    generateMapsWithVariousAlgorithms,
    validateAndOptimizeMaps,
    exportMapsForGame,
    WORKFLOW_CONFIG
};

// Run the workflow if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    runCompleteWorkflow()
        .then(results => {
            console.log('\n✅ Workflow completed successfully!');
            console.log('📁 Check the generated-maps directory for output files.');
            process.exit(0);
        })
        .catch(error => {
            console.error('\n💥 Workflow failed:', error.message);
            process.exit(1);
        });
}