/**
 * AdvancedMapGenerator - Main Map Generation System
 * 
 * This is the primary map generation system that combines all advanced
 * algorithms including Wave Function Collapse, Auto-Tiling, Resource
 * Placement, Symmetric Generation, and Validation systems.
 * 
 * Key Features:
 * - Unified interface for all map generation systems
 * - Customizable generation parameters inspired by Genesis Project
 * - Support for single-player and multiplayer maps
 * - Comprehensive validation and balance checking
 * - Integration with existing C&C tile systems
 * - Performance optimization and caching
 */

import { createNoise2D } from 'simplex-noise';
import WaveFunctionCollapse from './WaveFunctionCollapse.js';
import AutoTiler from './AutoTiler.js';
import ResourcePlacer from './ResourcePlacer.js';
import SymmetricGenerator from './SymmetricGenerator.js';
import MapValidator from './MapValidator.js';
import MLMapQualityEvaluator from './MLMapQualityEvaluator.js';

class AdvancedMapGenerator {
    constructor(options = {}) {
        // Default generation parameters
        this.config = {
            // Map dimensions
            width: 40,
            height: 30,
            tileSize: 32,
            
            // Generation method
            algorithm: 'hybrid', // 'wfc', 'symmetric', 'hybrid', 'classic'
            
            // Environment parameters (Genesis Project inspired)
            climate: 'temperate', // 'desert', 'temperate', 'arctic', 'volcanic'
            mountainDensity: 0.1, // 0.0 - 1.0
            waterCoverage: 0.15, // 0.0 - 0.5
            forestDensity: 0.2, // 0.0 - 0.5
            
            // Resource parameters
            resourceDensity: 0.08, // Percentage of map with resources
            resourceBalance: true,
            multipleResourceTypes: true,
            
            // Multiplayer settings
            playerCount: 1,
            symmetryType: 'rotational', // 'rotational', 'mirror', 'point'
            startingAreaSize: 8,
            expansionSites: 2,
            
            // Quality settings
            enableAutoTiling: true,
            enableValidation: true,
            enableMLEvaluation: true,
            maxGenerationAttempts: 5,
            qualityThreshold: 75, // Minimum validation score
            mlQualityThreshold: 70, // Minimum ML evaluation score
            
            // Performance settings
            useWFC: true,
            wfcIterations: 1000,
            optimizeForPerformance: false,
            
            ...options
        };
        
        // Initialize noise generators
        this.initializeNoiseGenerators();
        
        // Initialize subsystems
        this.initializeSubsystems();
        
        // Generation state
        this.lastGenerationResult = null;
        this.generationStats = {
            totalAttempts: 0,
            successfulGenerations: 0,
            averageScore: 0,
            generationTimes: []
        };
    }

    /**
     * Generate a complete map based on configuration
     * @param {Object} customConfig - Override default configuration
     * @returns {Object} - Complete map data with terrain, resources, and metadata
     */
    async generateMap(customConfig = {}) {
        const startTime = performance.now();
        const config = { ...this.config, ...customConfig };
        
        let bestResult = null;
        let bestScore = 0;
        
        for (let attempt = 1; attempt <= config.maxGenerationAttempts; attempt++) {
            try {
                console.log(`Map generation attempt ${attempt}/${config.maxGenerationAttempts}`);
                
                // Generate map based on algorithm choice
                const result = await this.generateMapInternal(config, attempt);
                
                // Validate if enabled
                let validationResult = null;
                let mlEvaluationResult = null;
                
                if (config.enableValidation) {
                    validationResult = this.validator.validateMap(result);
                    result.validation = validationResult;
                    
                    console.log(`Validation score: ${validationResult.overall.score}/100 (${validationResult.overall.grade})`);
                }
                
                // ML evaluation if enabled
                if (config.enableMLEvaluation && this.mlEvaluator && this.mlEvaluator.isInitialized) {
                    mlEvaluationResult = await this.mlEvaluator.evaluateMap(result);
                    result.mlEvaluation = mlEvaluationResult;
                    
                    console.log(`ML evaluation score: ${mlEvaluationResult.overall.score}/100 (${mlEvaluationResult.overall.grade}) - Confidence: ${mlEvaluationResult.confidence}%`);
                    
                    if (mlEvaluationResult.recommendations && mlEvaluationResult.recommendations.length > 0) {
                        console.log(`ML recommendations: ${mlEvaluationResult.recommendations.length} suggestions`);
                    }
                }
                
                // Calculate combined score
                let combinedScore = 0;
                if (validationResult && mlEvaluationResult) {
                    // Weight traditional validation and ML evaluation
                    combinedScore = (validationResult.overall.score * 0.6) + (mlEvaluationResult.overall.score * 0.4);
                } else if (validationResult) {
                    combinedScore = validationResult.overall.score;
                } else if (mlEvaluationResult) {
                    combinedScore = mlEvaluationResult.overall.score;
                } else {
                    combinedScore = 75; // Default acceptable score
                }
                
                // Check if this result is better than previous attempts
                if (combinedScore > bestScore) {
                    bestScore = combinedScore;
                    bestResult = result;
                    bestResult.combinedScore = combinedScore;
                }
                
                // Determine if score meets threshold
                const meetsValidationThreshold = !config.enableValidation || (validationResult && validationResult.overall.score >= config.qualityThreshold);
                const meetsMLThreshold = !config.enableMLEvaluation || !this.mlEvaluator?.isInitialized || (mlEvaluationResult && mlEvaluationResult.overall.score >= config.mlQualityThreshold);
                
                if (meetsValidationThreshold && meetsMLThreshold) {
                    bestResult = result;
                    bestResult.combinedScore = combinedScore;
                    break;
                }
                
                if (!config.enableValidation && !config.enableMLEvaluation) {
                    bestResult = result;
                    break;
                }
                
            } catch (error) {
                console.warn(`Generation attempt ${attempt} failed:`, error.message);
                continue;
            }
            
            this.generationStats.totalAttempts++;
        }
        
        if (!bestResult) {
            throw new Error('Failed to generate acceptable map after maximum attempts');
        }
        
        // Record statistics
        const endTime = performance.now();
        const generationTime = endTime - startTime;
        this.updateGenerationStats(bestResult, generationTime);
        
        this.lastGenerationResult = bestResult;
        return bestResult;
    }

    /**
     * Internal map generation logic
     */
    async generateMapInternal(config, attempt) {
        // Step 1: Generate base terrain
        const terrain = await this.generateBaseTerrain(config, attempt);
        
        // Step 2: Apply auto-tiling if enabled
        let processedTerrain = terrain;
        if (config.enableAutoTiling) {
            const tilingResult = this.autoTiler.autoTile(terrain, {
                enableTransitions: true,
                enableCorners: true,
                enableVariation: true
            });
            processedTerrain = tilingResult.base;
        }
        
        // Step 3: Generate starting positions
        const startingPositions = this.generateStartingPositions(config, processedTerrain);
        
        // Step 4: Place resources
        const resources = this.generateResources(config, processedTerrain, startingPositions);
        
        // Step 5: Add final touches
        const finalizedMap = this.finalizeMap(processedTerrain, resources, config);
        
        // Step 6: Create complete result
        return {
            terrain: finalizedMap,
            resources: resources,
            startingPositions: startingPositions,
            metadata: {
                width: config.width,
                height: config.height,
                algorithm: config.algorithm,
                climate: config.climate,
                playerCount: config.playerCount,
                generationAttempt: attempt,
                timestamp: Date.now(),
                config: { ...config }
            }
        };
    }

    /**
     * Generate base terrain using selected algorithm
     */
    async generateBaseTerrain(config, attempt) {
        switch (config.algorithm) {
            case 'wfc':
                return this.generateTerrainWithWFC(config, attempt);
                
            case 'symmetric':
                return this.generateSymmetricTerrain(config, attempt);
                
            case 'hybrid':
                return this.generateHybridTerrain(config, attempt);
                
            case 'classic':
            default:
                return this.generateClassicTerrain(config, attempt);
        }
    }

    /**
     * Generate terrain using Wave Function Collapse
     */
    generateTerrainWithWFC(config, attempt) {
        // Create terrain rules based on climate and parameters
        const tileRules = this.createWFCRules(config);
        
        // Initialize WFC system
        const wfc = new WaveFunctionCollapse(config.width, config.height, tileRules);
        
        // Generate terrain
        const terrain = wfc.generate();
        
        // Post-process based on climate
        return this.applyClimateEffects(terrain, config);
    }

    /**
     * Generate symmetric terrain for multiplayer
     */
    generateSymmetricTerrain(config, attempt) {
        if (config.playerCount < 2) {
            throw new Error('Symmetric generation requires at least 2 players');
        }
        
        // Create symmetric generator
        const symGenerator = new SymmetricGenerator(
            config.width, 
            config.height, 
            config.playerCount,
            {
                symmetryType: config.symmetryType,
                startingAreaRadius: config.startingAreaSize,
                resourceBalance: config.resourceBalance
            }
        );
        
        // Use classic generator as base
        const baseGenerator = (width, height, rng) => {
            return this.generateClassicTerrainInternal(width, height, config, rng);
        };
        
        const result = symGenerator.generateSymmetricMap(baseGenerator);
        return result.terrain;
    }

    /**
     * Generate hybrid terrain combining multiple techniques
     */
    generateHybridTerrain(config, attempt) {
        // Start with WFC for coherent base
        const wfcTerrain = this.generateTerrainWithWFC(config, attempt);
        
        // Apply symmetric constraints for multiplayer
        if (config.playerCount > 1) {
            return this.applySymmetricConstraints(wfcTerrain, config);
        }
        
        return wfcTerrain;
    }

    /**
     * Generate classic terrain (enhanced version of existing TerrainGenerator)
     */
    generateClassicTerrain(config, attempt) {
        return this.generateClassicTerrainInternal(
            config.width, 
            config.height, 
            config,
            this.createSeededRNG(Date.now() + attempt)
        );
    }

    /**
     * Internal classic terrain generation
     */
    generateClassicTerrainInternal(width, height, config, rng) {
        const terrain = [];
        
        // Initialize with base terrain
        for (let y = 0; y < height; y++) {
            terrain[y] = [];
            for (let x = 0; x < width; x++) {
                terrain[y][x] = this.selectBaseTerrain(x, y, config, rng);
            }
        }
        
        // Add features based on climate
        this.addClimateFeatures(terrain, config, rng);
        
        return terrain;
    }

    /**
     * Select base terrain type based on position and climate using enhanced noise
     */
    selectBaseTerrain(x, y, config, rng) {
        // Use multi-layered simplex noise for more natural terrain
        const baseNoise = this.getEnhancedNoise(x, y, config);
        const detailNoise = this.noise2D(x * 0.3, y * 0.3) * 0.2;
        const combinedNoise = baseNoise + detailNoise;
        
        // Add some randomness for variation
        const randomFactor = (rng() - 0.5) * 0.1;
        const finalNoise = combinedNoise + randomFactor;
        
        return this.selectTerrainByClimate(finalNoise, config.climate);
    }

    /**
     * Add climate-specific features to terrain using enhanced biome generation
     */
    addClimateFeatures(terrain, config, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        // Generate biome maps for intelligent feature placement
        const biomeData = this.generateBiomeData(width, height, config);
        
        // Add water features based on coverage and elevation
        if (config.waterCoverage > 0) {
            this.addEnhancedWaterFeatures(terrain, config, biomeData, rng);
        }
        
        // Add forests based on moisture and temperature
        if (config.forestDensity > 0 && config.climate !== 'desert') {
            this.addBiomeAwareForests(terrain, config, biomeData, rng);
        }
        
        // Add mountains/rocks based on elevation and climate
        if (config.mountainDensity > 0) {
            this.addElevationBasedMountains(terrain, config, biomeData, rng);
        }
        
        // Add climate-specific decorative features
        this.addClimateDecorations(terrain, config, biomeData, rng);
    }

    /**
     * Add water features to terrain
     */
    addWaterFeatures(terrain, config, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        const targetWaterTiles = Math.floor(width * height * config.waterCoverage);
        
        // Place water bodies
        const waterBodies = Math.max(1, Math.floor(rng() * 3) + 1);
        
        for (let i = 0; i < waterBodies; i++) {
            const centerX = Math.floor(rng() * width);
            const centerY = Math.floor(rng() * height);
            const radius = Math.floor(rng() * 8) + 3;
            
            this.addWaterBody(terrain, centerX, centerY, radius, rng);
        }
    }

    /**
     * Add forest features to terrain
     */
    addForestFeatures(terrain, config, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        const forestClusters = Math.floor(config.forestDensity * 10) + 2;
        
        for (let i = 0; i < forestClusters; i++) {
            const centerX = Math.floor(rng() * width);
            const centerY = Math.floor(rng() * height);
            const size = Math.floor(rng() * 12) + 4;
            
            this.addForestCluster(terrain, centerX, centerY, size, config, rng);
        }
    }

    /**
     * Add mountain/rock features to terrain
     */
    addMountainFeatures(terrain, config, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        const rockFormations = Math.floor(config.mountainDensity * 15) + 3;
        
        for (let i = 0; i < rockFormations; i++) {
            const x = Math.floor(rng() * width);
            const y = Math.floor(rng() * height);
            const clusterSize = Math.floor(rng() * 4) + 2;
            
            this.addRockFormation(terrain, x, y, clusterSize, rng);
        }
    }

    /**
     * Generate starting positions based on player count and map type
     */
    generateStartingPositions(config, terrain) {
        if (config.playerCount === 1) {
            return [{
                playerId: 0,
                x: Math.floor(config.width * 0.25),
                y: Math.floor(config.height * 0.25),
                team: 0
            }];
        }
        
        // For multiplayer, generate balanced positions
        const positions = [];
        const centerX = Math.floor(config.width / 2);
        const centerY = Math.floor(config.height / 2);
        const radius = Math.min(config.width, config.height) * 0.35;
        
        for (let i = 0; i < config.playerCount; i++) {
            const angle = (i * 2 * Math.PI) / config.playerCount;
            const x = Math.round(centerX + Math.cos(angle) * radius);
            const y = Math.round(centerY + Math.sin(angle) * radius);
            
            positions.push({
                playerId: i,
                x: Math.max(config.startingAreaSize, Math.min(config.width - config.startingAreaSize, x)),
                y: Math.max(config.startingAreaSize, Math.min(config.height - config.startingAreaSize, y)),
                team: i % 2 // Simple team assignment
            });
        }
        
        return positions;
    }

    /**
     * Generate resources using ResourcePlacer
     */
    generateResources(config, terrain, startingPositions) {
        const resourcePlacer = new ResourcePlacer(config.width, config.height, {
            resourceDensity: config.resourceDensity,
            playerPositions: startingPositions,
            resourceTypes: config.multipleResourceTypes ? ['green', 'blue'] : ['green'],
            expansionResources: config.expansionSites > 0,
            balanceRadius: config.startingAreaSize * 1.5
        });
        
        return resourcePlacer.placeResources(terrain, startingPositions);
    }

    /**
     * Apply final touches and optimizations to map
     */
    finalizeMap(terrain, resources, config) {
        // Ensure starting areas are clear and buildable
        this.clearStartingAreas(terrain, config);
        
        // Apply final terrain smoothing
        if (!config.optimizeForPerformance) {
            this.smoothTerrain(terrain);
        }
        
        return terrain;
    }

    /**
     * Initialize all subsystems
     */
    initializeSubsystems() {
        // Initialize auto-tiler with C&C compatible tiles
        this.autoTiler = new AutoTiler();
        
        // Initialize validator with appropriate thresholds
        this.validator = new MapValidator({
            resourceBalanceTolerance: 0.15,
            minBuildablePercentage: 0.6,
            validateBalance: this.config.playerCount > 1
        });
        
        // Initialize ML evaluator if enabled
        if (this.config.enableMLEvaluation) {
            this.mlEvaluator = new MLMapQualityEvaluator({
                terrainVariety: 0.25,
                resourceBalance: 0.30,
                strategicBalance: 0.25,
                aestheticQuality: 0.20,
                useGPUAcceleration: true
            });
            
            // Initialize asynchronously (don't block map generation)
            this.mlEvaluator.initialize().catch(error => {
                console.warn('⚠️ ML evaluator initialization failed, continuing without ML evaluation:', error.message);
                this.mlEvaluator = null;
            });
        }
    }

    /**
     * Create WFC rules based on configuration
     */
    createWFCRules(config) {
        const rules = {};
        
        // Base terrain tiles
        const sandTiles = ['S01', 'S02', 'S03', 'S04'];
        const dirtTiles = ['D01', 'D02', 'D03', 'D04'];
        const waterTiles = ['W1', 'W2'];
        const shoreTiles = ['SH1', 'SH2', 'SH3'];
        const treeTiles = ['T01', 'T02', 'T03', 'T05'];
        const rockTiles = ['ROCK1', 'ROCK2', 'ROCK3'];
        
        // Create rules for each tile
        this.createTileRules(rules, sandTiles, 0.5, sandTiles.concat(dirtTiles, shoreTiles));
        this.createTileRules(rules, dirtTiles, 0.3, dirtTiles.concat(sandTiles, treeTiles));
        this.createTileRules(rules, waterTiles, config.waterCoverage, waterTiles.concat(shoreTiles));
        this.createTileRules(rules, shoreTiles, 0.05, shoreTiles.concat(sandTiles, waterTiles));
        this.createTileRules(rules, treeTiles, config.forestDensity, treeTiles.concat(dirtTiles));
        this.createTileRules(rules, rockTiles, config.mountainDensity, rockTiles.concat(sandTiles, dirtTiles));
        
        return rules;
    }

    /**
     * Create adjacency rules for a set of tiles
     */
    createTileRules(rules, tiles, frequency, adjacentTiles) {
        for (const tile of tiles) {
            rules[tile] = {
                frequency: frequency / tiles.length,
                adjacency: {
                    up: adjacentTiles,
                    down: adjacentTiles,
                    left: adjacentTiles,
                    right: adjacentTiles
                }
            };
        }
    }

    /**
     * Apply climate effects to generated terrain
     */
    applyClimateEffects(terrain, config) {
        // Climate-specific post-processing
        switch (config.climate) {
            case 'desert':
                this.applyDesertEffects(terrain);
                break;
            case 'arctic':
                this.applyArcticEffects(terrain);
                break;
            case 'volcanic':
                this.applyVolcanicEffects(terrain);
                break;
        }
        
        return terrain;
    }

    /**
     * Apply symmetric constraints to terrain
     */
    applySymmetricConstraints(terrain, config) {
        // This would apply symmetry rules to make terrain balanced
        // Implementation depends on specific symmetry requirements
        return terrain;
    }

    /**
     * Clear starting areas to ensure they're buildable
     */
    clearStartingAreas(terrain, config) {
        const positions = this.generateStartingPositions(config, terrain);
        
        for (const pos of positions) {
            const radius = config.startingAreaSize;
            
            for (let y = pos.y - radius; y <= pos.y + radius; y++) {
                for (let x = pos.x - radius; x <= pos.x + radius; x++) {
                    if (x >= 0 && x < config.width && y >= 0 && y < config.height) {
                        const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
                        if (distance <= radius) {
                            terrain[y][x] = 'S01'; // Clear, buildable terrain
                        }
                    }
                }
            }
        }
    }

    /**
     * Update generation statistics
     */
    updateGenerationStats(result, generationTime) {
        this.generationStats.totalAttempts++;
        if (result) {
            this.generationStats.successfulGenerations++;
            this.generationStats.generationTimes.push(generationTime);
            
            if (result.validation) {
                const scores = [...(this.generationStats.scores || []), result.validation.overall.score];
                this.generationStats.averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
                this.generationStats.scores = scores.slice(-10); // Keep last 10 scores
            }
        }
    }

    /**
     * Get generation statistics and performance info
     */
    getStats() {
        const avgTime = this.generationStats.generationTimes.length > 0 ?
            this.generationStats.generationTimes.reduce((sum, time) => sum + time, 0) / 
            this.generationStats.generationTimes.length : 0;
        
        return {
            ...this.generationStats,
            averageGenerationTime: avgTime,
            successRate: this.generationStats.totalAttempts > 0 ?
                this.generationStats.successfulGenerations / this.generationStats.totalAttempts : 0,
            lastGeneration: this.lastGenerationResult ? {
                timestamp: this.lastGenerationResult.metadata.timestamp,
                score: this.lastGenerationResult.validation?.overall.score,
                algorithm: this.lastGenerationResult.metadata.algorithm
            } : null
        };
    }

    /**
     * Get recommended settings for different map types
     */
    static getPresets() {
        return {
            competitive2v2: {
                playerCount: 4,
                algorithm: 'symmetric',
                symmetryType: 'rotational',
                resourceBalance: true,
                qualityThreshold: 85,
                enableValidation: true
            },
            
            skirmish1v1: {
                playerCount: 2,
                algorithm: 'symmetric', 
                symmetryType: 'mirror',
                resourceBalance: true,
                qualityThreshold: 80
            },
            
            campaign: {
                playerCount: 1,
                algorithm: 'hybrid',
                resourceBalance: false,
                qualityThreshold: 70,
                enableValidation: false
            },
            
            largeMap: {
                width: 60,
                height: 45,
                algorithm: 'wfc',
                resourceDensity: 0.12,
                qualityThreshold: 75
            },
            
            desertStorm: {
                climate: 'desert',
                waterCoverage: 0.05,
                forestDensity: 0.02,
                mountainDensity: 0.15
            },
            
            temperateValley: {
                climate: 'temperate',
                waterCoverage: 0.2,
                forestDensity: 0.25,
                mountainDensity: 0.1
            }
        };
    }

    // Enhanced utility methods
    initializeNoiseGenerators() {
        // Create multiple noise generators for different terrain features
        this.noise2D = createNoise2D();
        this.elevationNoise = createNoise2D();
        this.moistureNoise = createNoise2D();
        this.temperatureNoise = createNoise2D();
        this.detailNoise = createNoise2D();
    }
    
    /**
     * Get enhanced multi-octave noise for terrain generation
     */
    getEnhancedNoise(x, y, config) {
        const scale = 0.05; // Base scale for terrain features
        
        // Multiple octaves for varied terrain detail
        const octave1 = this.noise2D(x * scale, y * scale) * 0.5;
        const octave2 = this.noise2D(x * scale * 2, y * scale * 2) * 0.25;
        const octave3 = this.noise2D(x * scale * 4, y * scale * 4) * 0.125;
        const octave4 = this.noise2D(x * scale * 8, y * scale * 8) * 0.0625;
        
        return octave1 + octave2 + octave3 + octave4;
    }
    
    /**
     * Get elevation-based noise for height mapping
     */
    getElevationNoise(x, y) {
        const scale = 0.03;
        return this.elevationNoise(x * scale, y * scale);
    }
    
    /**
     * Get moisture-based noise for vegetation placement
     */
    getMoistureNoise(x, y) {
        const scale = 0.08;
        return this.moistureNoise(x * scale, y * scale);
    }
    
    /**
     * Get temperature-based noise for climate variation
     */
    getTemperatureNoise(x, y) {
        const scale = 0.04;
        return this.temperatureNoise(x * scale, y * scale);
    }
    
    /**
     * Select terrain type based on climate and noise value
     */
    selectTerrainByClimate(noise, climate) {
        switch (climate) {
            case 'desert':
                if (noise > 0.4) return 'S01';
                else if (noise > 0.1) return 'S05';
                else if (noise > -0.2) return 'D01';
                else return 'D05';
                
            case 'temperate':
                if (noise > 0.5) return 'S01';
                else if (noise > 0.2) return 'S02';
                else if (noise > -0.1) return 'D01';
                else if (noise > -0.4) return 'D02';
                else return 'S02';
                
            case 'arctic':
                if (noise > 0.3) return 'S07';
                else if (noise > 0.0) return 'S08';
                else if (noise > -0.3) return 'S07';
                else return 'S08';
                
            case 'volcanic':
                if (noise > 0.4) return 'D07';
                else if (noise > 0.1) return 'D08';
                else if (noise > -0.2) return 'D07';
                else return 'S05';
                
            default:
                return noise > 0.0 ? 'S01' : 'D01';
        }
    }
    
    /**
     * Legacy coherent noise method (kept for compatibility)
     */
    coherentNoise(x, y, rng) {
        // Use simplex noise instead of sine/cosine approximation
        return this.getEnhancedNoise(x, y, {}) + (rng() - 0.5) * 0.1;
    }

    createSeededRNG(seed) {
        let currentSeed = seed;
        return function() {
            currentSeed = (currentSeed * 9301 + 49297) % 233280;
            return currentSeed / 233280;
        };
    }

    // Placeholder methods for terrain feature addition
    addWaterBody(terrain, centerX, centerY, radius, rng) {
        for (let y = centerY - radius; y <= centerY + radius; y++) {
            for (let x = centerX - radius; x <= centerX + radius; x++) {
                if (x >= 0 && x < terrain[0].length && y >= 0 && y < terrain.length) {
                    const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
                    if (distance <= radius - rng() * 2) {
                        terrain[y][x] = distance < radius - 1 ? 'W1' : 'SH1';
                    }
                }
            }
        }
    }

    /**
     * Generate biome data maps for intelligent feature placement
     */
    generateBiomeData(width, height, config) {
        const biomeData = {
            elevation: [],
            moisture: [],
            temperature: []
        };
        
        for (let y = 0; y < height; y++) {
            biomeData.elevation[y] = [];
            biomeData.moisture[y] = [];
            biomeData.temperature[y] = [];
            
            for (let x = 0; x < width; x++) {
                biomeData.elevation[y][x] = this.getElevationNoise(x, y);
                biomeData.moisture[y][x] = this.getMoistureNoise(x, y);
                biomeData.temperature[y][x] = this.getTemperatureNoise(x, y);
            }
        }
        
        return biomeData;
    }
    
    /**
     * Add enhanced water features based on elevation and moisture
     */
    addEnhancedWaterFeatures(terrain, config, biomeData, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        // Find low elevation areas for water placement
        const waterCandidates = [];
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (biomeData.elevation[y][x] < -0.2 && biomeData.moisture[y][x] > 0.1) {
                    waterCandidates.push({ x, y, score: -biomeData.elevation[y][x] + biomeData.moisture[y][x] });
                }
            }
        }
        
        // Sort by suitability and place water bodies
        waterCandidates.sort((a, b) => b.score - a.score);
        const maxWaterBodies = Math.floor(config.waterCoverage * 20);
        const waterBodiesPlaced = [];
        
        for (let i = 0; i < Math.min(maxWaterBodies, waterCandidates.length); i++) {
            const candidate = waterCandidates[i];
            
            // Check if too close to existing water bodies
            const tooClose = waterBodiesPlaced.some(existing => 
                Math.sqrt((existing.x - candidate.x) ** 2 + (existing.y - candidate.y) ** 2) < 8
            );
            
            if (!tooClose) {
                const radius = Math.floor(rng() * 6) + 3;
                this.addWaterBody(terrain, candidate.x, candidate.y, radius, rng);
                waterBodiesPlaced.push(candidate);
            }
        }
    }
    
    /**
     * Add forests based on biome conditions
     */
    addBiomeAwareForests(terrain, config, biomeData, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const elevation = biomeData.elevation[y][x];
                const moisture = biomeData.moisture[y][x];
                const temperature = biomeData.temperature[y][x];
                
                // Calculate forest probability based on biome conditions
                let forestProbability = 0;
                
                if (config.climate === 'temperate') {
                    forestProbability = Math.max(0, moisture * 0.5 + temperature * 0.2 - Math.abs(elevation) * 0.3);
                } else if (config.climate === 'arctic') {
                    forestProbability = Math.max(0, (moisture - 0.2) * 0.3 - temperature * 0.2);
                } else if (config.climate === 'volcanic') {
                    forestProbability = Math.max(0, moisture * 0.4 - elevation * 0.6);
                }
                
                forestProbability *= config.forestDensity * 2;
                
                if (rng() < forestProbability && !terrain[y][x].startsWith('W') && !terrain[y][x].startsWith('SH')) {
                    const treeTiles = this.getClimateTreeTiles(config.climate);
                    terrain[y][x] = treeTiles[Math.floor(rng() * treeTiles.length)];
                }
            }
        }
    }
    
    /**
     * Add mountains based on elevation data
     */
    addElevationBasedMountains(terrain, config, biomeData, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const elevation = biomeData.elevation[y][x];
                
                if (elevation > 0.4) {
                    const mountainProbability = (elevation - 0.4) * config.mountainDensity * 3;
                    
                    if (rng() < mountainProbability) {
                        const rockTiles = this.getClimateRockTiles(config.climate);
                        terrain[y][x] = rockTiles[Math.floor(rng() * rockTiles.length)];
                    }
                }
            }
        }
    }
    
    /**
     * Add climate-specific decorative features
     */
    addClimateDecorations(terrain, config, biomeData, rng) {
        const width = terrain[0].length;
        const height = terrain.length;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (rng() < 0.02) { // 2% chance for decorative features
                    this.addClimateSpecificDecoration(terrain, x, y, config, rng);
                }
            }
        }
    }
    
    /**
     * Get climate-appropriate tree tiles
     */
    getClimateTreeTiles(climate) {
        switch (climate) {
            case 'temperate':
                return ['T01', 'T02', 'T03', 'T05'];
            case 'arctic':
                return ['T05', 'T01']; // More sparse, hardy trees
            case 'volcanic':
                return ['T03', 'T05']; // More resistant vegetation
            default:
                return ['T01', 'T02', 'T03', 'T05'];
        }
    }
    
    /**
     * Get climate-appropriate rock tiles
     */
    getClimateRockTiles(climate) {
        switch (climate) {
            case 'volcanic':
                return ['ROCK3', 'ROCK2']; // Darker, volcanic rocks
            case 'arctic':
                return ['ROCK1', 'ROCK2']; // Lighter rocks
            default:
                return ['ROCK1', 'ROCK2', 'ROCK3'];
        }
    }
    
    /**
     * Add climate-specific decorative elements
     */
    addClimateSpecificDecoration(terrain, x, y, config, rng) {
        if (terrain[y][x].startsWith('W') || terrain[y][x].startsWith('SH') || 
            terrain[y][x].startsWith('T') || terrain[y][x].startsWith('ROCK')) {
            return; // Don't place decorations on occupied tiles
        }
        
        // Add subtle terrain variations based on climate
        const currentTile = terrain[y][x];
        const tileType = currentTile.charAt(0);
        
        if (config.climate === 'desert' && tileType === 'S') {
            // Add sand dune variations
            const sandVariations = ['S03', 'S04', 'S05', 'S06'];
            if (rng() < 0.3) {
                terrain[y][x] = sandVariations[Math.floor(rng() * sandVariations.length)];
            }
        } else if (config.climate === 'temperate' && tileType === 'D') {
            // Add dirt variations
            const dirtVariations = ['D02', 'D03', 'D04'];
            if (rng() < 0.2) {
                terrain[y][x] = dirtVariations[Math.floor(rng() * dirtVariations.length)];
            }
        }
    }
    
    addForestCluster(terrain, centerX, centerY, size, config, rng) {
        // This method is now largely replaced by addBiomeAwareForests
        // but kept for backward compatibility
        for (let i = 0; i < size; i++) {
            const angle = rng() * 2 * Math.PI;
            const distance = rng() * 5;
            const x = Math.round(centerX + Math.cos(angle) * distance);
            const y = Math.round(centerY + Math.sin(angle) * distance);
            
            if (x >= 0 && x < terrain[0].length && y >= 0 && y < terrain.length) {
                if (!terrain[y][x].startsWith('W') && !terrain[y][x].startsWith('SH')) {
                    const treeTiles = this.getClimateTreeTiles(config.climate);
                    terrain[y][x] = treeTiles[Math.floor(rng() * treeTiles.length)];
                }
            }
        }
    }

    addRockFormation(terrain, x, y, clusterSize, rng) {
        const rockTiles = ['ROCK1', 'ROCK2', 'ROCK3'];
        
        if (x >= 0 && x < terrain[0].length && y >= 0 && y < terrain.length) {
            terrain[y][x] = rockTiles[Math.floor(rng() * rockTiles.length)];
            
            // Add adjacent rocks
            const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
            let placed = 1;
            
            for (let i = 0; i < directions.length && placed < clusterSize; i++) {
                const [dx, dy] = directions[i];
                const nx = x + dx;
                const ny = y + dy;
                
                if (nx >= 0 && nx < terrain[0].length && ny >= 0 && ny < terrain.length &&
                    rng() < 0.6) {
                    terrain[ny][nx] = rockTiles[Math.floor(rng() * rockTiles.length)];
                    placed++;
                }
            }
        }
    }

    applyDesertEffects(terrain) {
        // Convert some terrain to more desert-appropriate tiles
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                if (terrain[y][x].startsWith('D')) {
                    // Convert some dirt to sand in desert climate
                    if (Math.random() < 0.3) {
                        terrain[y][x] = 'S05'; // More desert-like sand
                    }
                }
            }
        }
    }

    applyArcticEffects(terrain) {
        // Convert terrain to lighter, ice-like colors
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                if (terrain[y][x].startsWith('S')) {
                    terrain[y][x] = 'S07'; // Lighter sand for snow/ice
                } else if (terrain[y][x].startsWith('D')) {
                    terrain[y][x] = 'S08'; // Convert dirt to icy terrain
                }
            }
        }
    }

    applyVolcanicEffects(terrain) {
        // Add darker, more volcanic terrain
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                if (terrain[y][x].startsWith('S') && Math.random() < 0.4) {
                    terrain[y][x] = 'D08'; // Darker, volcanic dirt
                }
            }
        }
    }

    smoothTerrain(terrain) {
        // Apply basic smoothing to reduce harsh transitions
        const smoothed = terrain.map(row => [...row]);
        
        for (let y = 1; y < terrain.length - 1; y++) {
            for (let x = 1; x < terrain[y].length - 1; x++) {
                const neighbors = [
                    terrain[y-1][x], terrain[y+1][x],
                    terrain[y][x-1], terrain[y][x+1]
                ];
                
                // Find most common neighbor type
                const typeCount = {};
                for (const neighbor of neighbors) {
                    const type = neighbor.charAt(0);
                    typeCount[type] = (typeCount[type] || 0) + 1;
                }
                
                const mostCommon = Object.entries(typeCount)
                    .sort(([,a], [,b]) => b - a)[0];
                
                if (mostCommon && mostCommon[1] >= 3) {
                    // If 3+ neighbors are same type, convert this tile
                    const currentType = terrain[y][x].charAt(0);
                    if (currentType !== mostCommon[0] && 
                        !terrain[y][x].startsWith('ROCK') &&
                        !terrain[y][x].startsWith('T')) {
                        
                        const newTile = mostCommon[0] + '01';
                        smoothed[y][x] = newTile;
                    }
                }
            }
        }
        
        // Copy smoothed result back
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                terrain[y][x] = smoothed[y][x];
            }
        }
    }
}

export default AdvancedMapGenerator;