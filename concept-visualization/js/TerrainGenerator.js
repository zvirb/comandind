// Command & Conquer style terrain generator
// Creates realistic-looking maps with proper tile transitions and coherent battlefield features
// Enhanced with Wave Function Collapse algorithm integration for improved terrain coherence

import { WaveFunctionCollapse } from '../../src/mapgen/index.js';

class TerrainGenerator {
    constructor(width, height, options = {}) {
        this.width = width;
        this.height = height;
        this.map = [];
        this.tiberiumFields = [];
        
        // Enhanced options
        this.options = {
            useWFC: false, // Enable Wave Function Collapse for better coherence
            climate: 'temperate', // 'desert', 'temperate', 'arctic', 'volcanic'
            resourceBalance: true,
            qualityThreshold: 70,
            enableValidation: true,
            ...options
        };
        
        // Climate-based terrain configurations
        this.climateConfigs = this.initializeClimateConfigs();
        
        // WFC rules for terrain coherence
        this.wfcRules = this.initializeWFCRules();
        
        // Define terrain types with proper C&C tile mappings
        this.terrainTypes = {
            // Sand terrain (clear, buildable)
            SAND: { 
                tiles: ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08'], 
                frequency: 0.45,
                buildable: true
            },
            // Dirt/rough terrain (buildable but looks different)
            DIRT: { 
                tiles: ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08'], 
                frequency: 0.35,
                buildable: true
            },
            // Water (non-buildable)
            WATER: { 
                tiles: ['W1', 'W2'], 
                frequency: 0.05,
                buildable: false
            },
            // Shore transitions
            SHORE: { 
                tiles: ['SH1', 'SH2', 'SH3', 'SH4', 'SH5', 'SH6'], 
                frequency: 0.03,
                buildable: false
            },
            // Trees (decorative, non-buildable)
            TREE: { 
                tiles: ['T01', 'T02', 'T03', 'T05', 'T06', 'T07', 'T08', 'T09'], 
                frequency: 0.08,
                buildable: false
            },
            // Rock formations (decorative, non-buildable)
            ROCK: { 
                tiles: ['ROCK1', 'ROCK2', 'ROCK3', 'ROCK4', 'ROCK5', 'ROCK6', 'ROCK7'], 
                frequency: 0.04,
                buildable: false
            }
        };
        
        // Seed for deterministic generation
        this.seed = 12345;
        
        // Map quality metrics
        this.qualityMetrics = {
            terrainCoherence: 0,
            resourceBalance: 0,
            buildableArea: 0,
            strategicBalance: 0,
            overallScore: 0
        };
    }
    
    // Initialize climate-specific terrain configurations
    initializeClimateConfigs() {
        return {
            desert: {
                primaryTerrain: 'SAND',
                secondaryTerrain: 'DIRT',
                waterFrequency: 0.02,
                forestFrequency: 0.01,
                rockFrequency: 0.08,
                temperatureRange: [35, 50],
                humidityRange: [5, 25]
            },
            temperate: {
                primaryTerrain: 'SAND',
                secondaryTerrain: 'DIRT', 
                waterFrequency: 0.05,
                forestFrequency: 0.08,
                rockFrequency: 0.04,
                temperatureRange: [15, 25],
                humidityRange: [40, 70]
            },
            arctic: {
                primaryTerrain: 'DIRT',
                secondaryTerrain: 'SAND',
                waterFrequency: 0.03, // Frozen water
                forestFrequency: 0.02, // Sparse vegetation
                rockFrequency: 0.06,
                temperatureRange: [-10, 5],
                humidityRange: [30, 60]
            },
            volcanic: {
                primaryTerrain: 'DIRT',
                secondaryTerrain: 'ROCK',
                waterFrequency: 0.01, // Lava pools
                forestFrequency: 0.03,
                rockFrequency: 0.15,
                temperatureRange: [25, 40],
                humidityRange: [20, 50]
            }
        };
    }
    
    // Initialize Wave Function Collapse rules for terrain coherence
    initializeWFCRules() {
        return {
            // Sand tiles - compatible with each other and dirt
            'S01': { compatible: { north: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], south: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], east: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], west: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'] }},
            'S02': { compatible: { north: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], south: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], east: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], west: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'] }},
            'S03': { compatible: { north: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], south: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], east: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], west: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'] }},
            'S04': { compatible: { north: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], south: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], east: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'], west: ['S01', 'S02', 'S03', 'S04', 'D01', 'D02'] }},
            
            // Dirt tiles - compatible with sand and each other
            'D01': { compatible: { north: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], south: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], east: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], west: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'] }},
            'D02': { compatible: { north: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], south: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], east: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], west: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'] }},
            'D03': { compatible: { north: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], south: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], east: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], west: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'] }},
            'D04': { compatible: { north: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], south: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], east: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'], west: ['D01', 'D02', 'D03', 'D04', 'S01', 'S02'] }},
            
            // Water tiles - need shore transitions
            'W1': { compatible: { north: ['W1', 'W2', 'SH1', 'SH2'], south: ['W1', 'W2', 'SH1', 'SH2'], east: ['W1', 'W2', 'SH1', 'SH2'], west: ['W1', 'W2', 'SH1', 'SH2'] }},
            'W2': { compatible: { north: ['W1', 'W2', 'SH1', 'SH2'], south: ['W1', 'W2', 'SH1', 'SH2'], east: ['W1', 'W2', 'SH1', 'SH2'], west: ['W1', 'W2', 'SH1', 'SH2'] }},
            
            // Shore tiles - transition between water and land
            'SH1': { compatible: { north: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], south: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], east: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], west: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'] }},
            'SH2': { compatible: { north: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], south: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], east: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], west: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'] }},
            'SH3': { compatible: { north: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], south: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], east: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'], west: ['SH1', 'SH2', 'SH3', 'W1', 'W2', 'S01', 'D01'] }},
            
            // Trees - cluster together and avoid water
            'T01': { compatible: { north: ['T01', 'T02', 'T03', 'S01', 'D01'], south: ['T01', 'T02', 'T03', 'S01', 'D01'], east: ['T01', 'T02', 'T03', 'S01', 'D01'], west: ['T01', 'T02', 'T03', 'S01', 'D01'] }},
            'T02': { compatible: { north: ['T01', 'T02', 'T03', 'S01', 'D01'], south: ['T01', 'T02', 'T03', 'S01', 'D01'], east: ['T01', 'T02', 'T03', 'S01', 'D01'], west: ['T01', 'T02', 'T03', 'S01', 'D01'] }},
            'T03': { compatible: { north: ['T01', 'T02', 'T03', 'S01', 'D01'], south: ['T01', 'T02', 'T03', 'S01', 'D01'], east: ['T01', 'T02', 'T03', 'S01', 'D01'], west: ['T01', 'T02', 'T03', 'S01', 'D01'] }},
            
            // Rocks - standalone or small clusters
            'ROCK1': { compatible: { north: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], south: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], east: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], west: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'] }},
            'ROCK2': { compatible: { north: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], south: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], east: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], west: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'] }},
            'ROCK3': { compatible: { north: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], south: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], east: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'], west: ['ROCK1', 'ROCK2', 'S01', 'D01', 'D02'] }}
        };
    }
    
    generateMap() {
        if (this.options.useWFC) {
            return this.generateMapWithWFC();
        }
        
        return this.generateMapClassic();
    }
    
    // Enhanced map generation with WFC algorithm
    generateMapWithWFC() {
        try {
            // Create WFC instance with our terrain rules
            const wfc = new WaveFunctionCollapse(this.width, this.height, this.wfcRules);
            
            // Generate base terrain using WFC
            const wfcResult = wfc.generate();
            
            if (wfcResult.success) {
                this.map = wfcResult.result;
                console.log('WFC terrain generation successful');
            } else {
                console.warn('WFC generation failed, using fallback');
                return this.generateMapClassic();
            }
            
            // Apply climate-specific adjustments
            this.applyClimateSettings();
            
            // Add strategic elements
            this.addStrategicFeatures();
            
            // Add balanced resource deposits
            this.addBalancedTiberiumFields();
            
            // Validate and optimize
            if (this.options.enableValidation) {
                this.validateAndOptimizeMap();
            }
            
            // Calculate quality metrics
            this.calculateQualityMetrics();
            
            return {
                map: this.map,
                tiberiumFields: this.tiberiumFields,
                metadata: {
                    width: this.width,
                    height: this.height,
                    climate: this.options.climate,
                    quality: this.qualityMetrics,
                    generationMethod: 'WFC'
                }
            };
            
        } catch (error) {
            console.warn('WFC generation error:', error.message);
            return this.generateMapClassic();
        }
    }
    
    // Classic generation method (fallback)
    generateMapClassic() {
        // Initialize with base terrain layer (sand/dirt mix)
        this.initializeBaseTerrain();
        
        // Add major terrain features in proper order
        this.addWaterFeature();           // Water body with shores
        this.addForestRegions();          // Tree clusters
        this.addRockFormations();         // Scattered rocks
        this.addDirtPatches();           // Additional dirt/rough areas
        this.addTiberiumFields();        // Resource deposits
        
        // Apply terrain transitions and blending
        this.smoothTransitions();
        this.addDetailVariation();
        
        return {
            map: this.map,
            tiberiumFields: this.tiberiumFields,
            metadata: {
                width: this.width,
                height: this.height,
                terrainTypes: Object.keys(this.terrainTypes)
            }
        };
    }
    
    initializeBaseTerrain() {
        // Create base layer with coherent sand/dirt regions
        for (let y = 0; y < this.height; y++) {
            this.map[y] = [];
            for (let x = 0; x < this.width; x++) {
                // Use multiple layers of noise for realistic terrain distribution
                const primaryNoise = this.coherentNoise(x * 0.08, y * 0.08);
                const secondaryNoise = this.coherentNoise(x * 0.15, y * 0.15) * 0.5;
                const localVariation = this.coherentNoise(x * 0.3, y * 0.3) * 0.3;
                
                const terrainValue = primaryNoise + secondaryNoise + localVariation;
                
                if (terrainValue > 0.2) {
                    // Sand terrain - more common, good for building
                    const sandTiles = this.terrainTypes.SAND.tiles;
                    this.map[y][x] = sandTiles[Math.floor(this.seededRandom(x, y) * sandTiles.length)];
                } else {
                    // Dirt terrain - provides variation
                    const dirtTiles = this.terrainTypes.DIRT.tiles;
                    this.map[y][x] = dirtTiles[Math.floor(this.seededRandom(x + 1000, y) * dirtTiles.length)];
                }
            }
        }
    }
    
    addWaterFeature() {
        // Add a natural-looking water feature in bottom-left corner
        const waterRegion = {
            centerX: 6,
            centerY: this.height - 8,
            maxRadius: 8
        };
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const distance = Math.sqrt(
                    Math.pow(x - waterRegion.centerX, 2) + 
                    Math.pow(y - waterRegion.centerY, 2)
                );
                
                // Create organic water shape with noise
                const shapeNoise = this.coherentNoise(x * 0.2, y * 0.2) * 0.3;
                const effectiveRadius = waterRegion.maxRadius + shapeNoise;
                
                if (distance < effectiveRadius - 2) {
                    // Deep water
                    const waterTiles = this.terrainTypes.WATER.tiles;
                    this.map[y][x] = waterTiles[Math.floor(this.seededRandom(x, y) * waterTiles.length)];
                } else if (distance < effectiveRadius) {
                    // Shore transition - only if not already water
                    if (!this.map[y][x] || !this.map[y][x].startsWith('W')) {
                        const shoreTiles = this.terrainTypes.SHORE.tiles;
                        this.map[y][x] = shoreTiles[Math.floor(this.seededRandom(x + 500, y) * shoreTiles.length)];
                    }
                }
            }
        }
    }
    
    addForestRegions() {
        // Add multiple forest clusters for a natural battlefield look
        const forestRegions = [
            { centerX: this.width - 10, centerY: 6, radius: 8 },   // Top-right main forest
            { centerX: 15, centerY: 5, radius: 4 },                // Small forest patch
            { centerX: this.width - 6, centerY: 18, radius: 3 }    // Small southern forest
        ];
        
        forestRegions.forEach((region, regionIndex) => {
            for (let y = Math.max(0, region.centerY - region.radius); 
                 y < Math.min(this.height, region.centerY + region.radius); y++) {
                for (let x = Math.max(0, region.centerX - region.radius); 
                     x < Math.min(this.width, region.centerX + region.radius); x++) {
                    
                    const distance = Math.sqrt(
                        Math.pow(x - region.centerX, 2) + 
                        Math.pow(y - region.centerY, 2)
                    );
                    
                    // Skip water areas
                    if (this.map[y][x] && (this.map[y][x].startsWith('W') || this.map[y][x].startsWith('SH'))) {
                        continue;
                    }
                    
                    // Create organic forest shape
                    const forestNoise = this.coherentNoise(x * 0.25, y * 0.25) * 0.4;
                    const treeDensity = this.seededRandom(x + regionIndex * 1000, y);
                    
                    if (distance < region.radius + forestNoise && treeDensity < 0.65) {
                        const treeTiles = this.terrainTypes.TREE.tiles;
                        this.map[y][x] = treeTiles[Math.floor(this.seededRandom(x, y + regionIndex * 100) * treeTiles.length)];
                    }
                }
            }
        });
    }
    
    addDirtPatches() {
        // Add strategic patches of dirt/rough terrain for battlefield realism
        const dirtRegions = [
            { centerX: 20, centerY: 12, radius: 6 },  // Central battlefield area
            { centerX: 8, centerY: 20, radius: 4 },   // Southern rough area
            { centerX: 32, centerY: 25, radius: 5 }   // Eastern rough area
        ];
        
        dirtRegions.forEach((region, regionIndex) => {
            for (let y = Math.max(0, region.centerY - region.radius); 
                 y < Math.min(this.height, region.centerY + region.radius); y++) {
                for (let x = Math.max(0, region.centerX - region.radius); 
                     x < Math.min(this.width, region.centerX + region.radius); x++) {
                    
                    // Skip protected terrain types
                    if (this.map[y][x] && (
                        this.map[y][x].startsWith('W') || 
                        this.map[y][x].startsWith('SH') ||
                        this.map[y][x].startsWith('T')
                    )) {
                        continue;
                    }
                    
                    const distance = Math.sqrt(
                        Math.pow(x - region.centerX, 2) + 
                        Math.pow(y - region.centerY, 2)
                    );
                    
                    // Create organic dirt patches with noise
                    const patchNoise = this.coherentNoise(x * 0.3, y * 0.3) * 0.35;
                    const patchDensity = this.seededRandom(x + regionIndex * 2000, y);
                    
                    if (distance < region.radius + patchNoise && patchDensity < 0.7) {
                        const dirtTiles = this.terrainTypes.DIRT.tiles;
                        this.map[y][x] = dirtTiles[Math.floor(this.seededRandom(x + 3000, y) * dirtTiles.length)];
                    }
                }
            }
        });
    }
    
    addRockFormations() {
        // Add strategic rock formations for battlefield cover and aesthetics
        const rockFormations = [
            { x: 12, y: 8, clusterSize: 3 },
            { x: 28, y: 22, clusterSize: 2 },
            { x: 35, y: 12, clusterSize: 4 },
            { x: 6, y: 15, clusterSize: 2 },
            { x: 22, y: 6, clusterSize: 3 },
            { x: 18, y: 20, clusterSize: 2 }
        ];
        
        rockFormations.forEach((formation, formationIndex) => {
            // Place main rock
            if (this.isValidRockPosition(formation.x, formation.y)) {
                const rockTiles = this.terrainTypes.ROCK.tiles;
                const rockIndex = Math.floor(this.seededRandom(formation.x, formation.y) * rockTiles.length);
                this.map[formation.y][formation.x] = rockTiles[rockIndex];
                
                // Add cluster rocks around the main rock
                const clusterPositions = [
                    [-1, 0], [1, 0], [0, -1], [0, 1],  // Adjacent
                    [-1, -1], [1, 1], [-1, 1], [1, -1] // Diagonal
                ];
                
                let rocksPlaced = 0;
                for (const [dx, dy] of clusterPositions) {
                    if (rocksPlaced >= formation.clusterSize - 1) break;
                    
                    const rockX = formation.x + dx;
                    const rockY = formation.y + dy;
                    
                    if (this.isValidRockPosition(rockX, rockY) && 
                        this.seededRandom(rockX + formationIndex * 100, rockY) < 0.6) {
                        const clusterRockIndex = Math.floor(this.seededRandom(rockX + 1000, rockY) * rockTiles.length);
                        this.map[rockY][rockX] = rockTiles[clusterRockIndex];
                        rocksPlaced++;
                    }
                }
            }
        });
    }
    
    addTiberiumFields() {
        // Add strategic tiberium resource deposits
        const tiberiumDeposits = [
            { centerX: 10, centerY: 10, radius: 4, type: 'green' },  // Northwest deposit
            { centerX: 28, centerY: 8, radius: 3, type: 'green' },   // Northeast deposit  
            { centerX: 6, centerY: 25, radius: 3, type: 'blue' },    // Southwest blue deposit
            { centerX: 35, centerY: 20, radius: 4, type: 'green' }   // Southeast deposit
        ];
        
        this.tiberiumFields = [];
        
        tiberiumDeposits.forEach((deposit, depositIndex) => {
            const tiberiumPatch = [];
            
            for (let y = Math.max(0, deposit.centerY - deposit.radius); 
                 y < Math.min(this.height, deposit.centerY + deposit.radius); y++) {
                for (let x = Math.max(0, deposit.centerX - deposit.radius); 
                     x < Math.min(this.width, deposit.centerX + deposit.radius); x++) {
                    
                    // Skip protected terrain
                    if (this.map[y] && this.map[y][x] && (
                        this.map[y][x].startsWith('W') || 
                        this.map[y][x].startsWith('SH') ||
                        this.map[y][x].startsWith('T') ||
                        this.map[y][x].startsWith('ROCK')
                    )) {
                        continue;
                    }
                    
                    const distance = Math.sqrt(
                        Math.pow(x - deposit.centerX, 2) + 
                        Math.pow(y - deposit.centerY, 2)
                    );
                    
                    // Create organic tiberium deposit shape
                    const tiberiumNoise = this.coherentNoise(x * 0.4, y * 0.4) * 0.3;
                    const tiberiumDensity = this.seededRandom(x + depositIndex * 5000, y);
                    
                    if (distance < deposit.radius + tiberiumNoise && tiberiumDensity < 0.7) {
                        tiberiumPatch.push({ 
                            x, 
                            y, 
                            type: deposit.type,
                            density: Math.max(0.3, 1.0 - distance / deposit.radius)
                        });
                    }
                }
            }
            
            if (tiberiumPatch.length > 0) {
                this.tiberiumFields.push(tiberiumPatch);
            }
        });
    }
    
    smoothTransitions() {
        // Enhance terrain transitions for more natural battlefield appearance
        const tempMap = this.map.map(row => [...row]); // Copy for modifications
        
        for (let y = 1; y < this.height - 1; y++) {
            for (let x = 1; x < this.width - 1; x++) {
                const current = this.map[y][x];
                
                // Get all 8 neighbors
                const neighbors = [
                    this.map[y - 1][x - 1], this.map[y - 1][x], this.map[y - 1][x + 1],
                    this.map[y][x - 1],                            this.map[y][x + 1],
                    this.map[y + 1][x - 1], this.map[y + 1][x], this.map[y + 1][x + 1]
                ];
                
                const waterNeighbors = neighbors.filter(n => n && n.startsWith('W')).length;
                const treeNeighbors = neighbors.filter(n => n && n.startsWith('T')).length;
                const rockNeighbors = neighbors.filter(n => n && n.startsWith('ROCK')).length;
                
                // Enhanced shore transitions
                if (waterNeighbors > 0 && !current.startsWith('W') && !current.startsWith('SH')) {
                    if (waterNeighbors >= 1) {
                        const shoreTiles = this.terrainTypes.SHORE.tiles;
                        tempMap[y][x] = shoreTiles[Math.floor(this.seededRandom(x + 10000, y) * shoreTiles.length)];
                    }
                }
                
                // Blend terrain at forest edges
                if (treeNeighbors > 0 && treeNeighbors < 4 && current.startsWith('S')) {
                    // Convert some sand near forests to dirt for more natural look
                    if (this.seededRandom(x + 20000, y) < 0.3) {
                        const dirtTiles = this.terrainTypes.DIRT.tiles;
                        tempMap[y][x] = dirtTiles[Math.floor(this.seededRandom(x + 30000, y) * dirtTiles.length)];
                    }
                }
            }
        }
        
        this.map = tempMap;
    }
    
    addDetailVariation() {
        // Add final detail pass to break up monotonous areas
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const current = this.map[y][x];
                
                // Add variation to large uniform areas
                if (current.startsWith('S') || current.startsWith('D')) {
                    const variation = this.seededRandom(x + 40000, y);
                    
                    if (variation < 0.05) {
                        // Occasionally switch sand/dirt types for variation
                        if (current.startsWith('S')) {
                            const dirtTiles = this.terrainTypes.DIRT.tiles;
                            this.map[y][x] = dirtTiles[Math.floor(this.seededRandom(x + 50000, y) * dirtTiles.length)];
                        } else if (current.startsWith('D')) {
                            const sandTiles = this.terrainTypes.SAND.tiles;
                            this.map[y][x] = sandTiles[Math.floor(this.seededRandom(x + 60000, y) * sandTiles.length)];
                        }
                    }
                }
            }
        }
    }
    
    isValidRockPosition(x, y) {
        return x >= 0 && x < this.width && 
               y >= 0 && y < this.height &&
               this.map[y] && this.map[y][x] &&
               !this.map[y][x].startsWith('W') &&
               !this.map[y][x].startsWith('SH') &&
               !this.map[y][x].startsWith('T') &&
               !this.map[y][x].startsWith('ROCK');
    }
    
    // Seeded random function for deterministic generation
    seededRandom(x, y) {
        const seed = (x * 73856093) ^ (y * 19349663) ^ (this.seed * 83492791);
        const n = Math.sin(seed) * 43758.5453123;
        return n - Math.floor(n);
    }
    
    // Improved noise function for coherent terrain features
    coherentNoise(x, y) {
        // Multi-octave noise for natural terrain variation
        const octave1 = Math.sin(x * 1.0) * Math.cos(y * 1.0) * 0.5;
        const octave2 = Math.sin(x * 2.1) * Math.cos(y * 1.9) * 0.25;
        const octave3 = Math.sin(x * 4.3) * Math.cos(y * 3.8) * 0.125;
        
        return (octave1 + octave2 + octave3) * 0.8;
    }
    
    getTiberiumFields() {
        return this.tiberiumFields || [];
    }
    
    // Get terrain type at specific coordinates
    getTerrainAt(x, y) {
        if (x < 0 || x >= this.width || y < 0 || y >= this.height) {
            return null;
        }
        return this.map[y][x];
    }
    
    // Check if position is buildable
    isBuildable(x, y) {
        const terrain = this.getTerrainAt(x, y);
        if (!terrain) return false;
        
        // Check against terrain type properties
        for (const [typeName, typeData] of Object.entries(this.terrainTypes)) {
            if (typeData.tiles.some(tile => terrain.startsWith(tile))) {
                return typeData.buildable;
            }
        }
        
        return false; // Default to non-buildable if unknown
    }
    
    // Apply climate-specific terrain adjustments
    applyClimateSettings() {
        const config = this.climateConfigs[this.options.climate];
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const currentTile = this.map[y][x];
                
                // Apply climate-specific tile variations
                if (this.seededRandom(x + 10000, y) < 0.1) {
                    if (this.options.climate === 'desert') {
                        // More sand variations in desert
                        if (currentTile.startsWith('D')) {
                            const sandTiles = this.terrainTypes.SAND.tiles;
                            this.map[y][x] = sandTiles[Math.floor(this.seededRandom(x + 20000, y) * sandTiles.length)];
                        }
                    } else if (this.options.climate === 'volcanic') {
                        // More rock formations in volcanic
                        if (currentTile.startsWith('S') && this.seededRandom(x + 30000, y) < 0.05) {
                            const rockTiles = this.terrainTypes.ROCK.tiles;
                            this.map[y][x] = rockTiles[Math.floor(this.seededRandom(x + 40000, y) * rockTiles.length)];
                        }
                    }
                }
            }
        }
    }
    
    // Add strategic terrain features for balanced gameplay
    addStrategicFeatures() {
        // Add strategic chokepoints
        this.addChokePoints();
        
        // Add high ground positions
        this.addHighGround();
        
        // Add strategic cover
        this.addStrategicCover();
    }
    
    addChokePoints() {
        // Create natural chokepoints using terrain features
        const chokePoints = [
            { x: Math.floor(this.width * 0.3), y: Math.floor(this.height * 0.5), width: 3, height: 8 },
            { x: Math.floor(this.width * 0.7), y: Math.floor(this.height * 0.5), width: 3, height: 8 }
        ];
        
        chokePoints.forEach(choke => {
            for (let y = choke.y - choke.height/2; y < choke.y + choke.height/2; y++) {
                for (let x = choke.x - choke.width/2; x < choke.x + choke.width/2; x++) {
                    if (x >= 0 && x < this.width && y >= 0 && y < this.height) {
                        if (this.seededRandom(x + 50000, y) < 0.6) {
                            const rockTiles = this.terrainTypes.ROCK.tiles;
                            this.map[y][x] = rockTiles[Math.floor(this.seededRandom(x + 60000, y) * rockTiles.length)];
                        }
                    }
                }
            }
        });
    }
    
    addHighGround() {
        // Add elevated positions for tactical advantage
        const highGroundSpots = [
            { x: Math.floor(this.width * 0.25), y: Math.floor(this.height * 0.25), radius: 4 },
            { x: Math.floor(this.width * 0.75), y: Math.floor(this.height * 0.75), radius: 4 },
            { x: Math.floor(this.width * 0.5), y: Math.floor(this.height * 0.1), radius: 3 },
            { x: Math.floor(this.width * 0.5), y: Math.floor(this.height * 0.9), radius: 3 }
        ];
        
        highGroundSpots.forEach(spot => {
            for (let y = spot.y - spot.radius; y <= spot.y + spot.radius; y++) {
                for (let x = spot.x - spot.radius; x <= spot.x + spot.radius; x++) {
                    if (x >= 0 && x < this.width && y >= 0 && y < this.height) {
                        const distance = Math.sqrt(Math.pow(x - spot.x, 2) + Math.pow(y - spot.y, 2));
                        if (distance <= spot.radius && this.seededRandom(x + 70000, y) < 0.4) {
                            const rockTiles = this.terrainTypes.ROCK.tiles;
                            this.map[y][x] = rockTiles[Math.floor(this.seededRandom(x + 80000, y) * rockTiles.length)];
                        }
                    }
                }
            }
        });
    }
    
    addStrategicCover() {
        // Add scattered cover elements for tactical gameplay
        const coverSpots = Math.floor(this.width * this.height * 0.02); // 2% coverage
        
        for (let i = 0; i < coverSpots; i++) {
            const x = Math.floor(this.seededRandom(i, 0) * this.width);
            const y = Math.floor(this.seededRandom(0, i) * this.height);
            
            // Skip if already occupied by special terrain
            if (this.map[y] && this.map[y][x] && 
                !this.map[y][x].startsWith('W') && 
                !this.map[y][x].startsWith('SH') &&
                this.seededRandom(x + 90000, y) < 0.7) {
                
                const coverType = this.seededRandom(x + 100000, y) < 0.5 ? 'TREE' : 'ROCK';
                const tiles = this.terrainTypes[coverType].tiles;
                this.map[y][x] = tiles[Math.floor(this.seededRandom(x + 110000, y) * tiles.length)];
            }
        }
    }
    
    // Enhanced tiberium placement with resource balancing
    addBalancedTiberiumFields() {
        if (!this.options.resourceBalance) {
            return this.addTiberiumFields(); // Use original method
        }
        
        // Calculate strategic positions for balanced resource distribution
        const resourceZones = this.calculateResourceZones();
        
        this.tiberiumFields = [];
        
        resourceZones.forEach((zone, zoneIndex) => {
            const tiberiumPatch = [];
            const resourceType = zone.type;
            
            // Create organic deposit shape around zone center
            for (let y = zone.centerY - zone.radius; y <= zone.centerY + zone.radius; y++) {
                for (let x = zone.centerX - zone.radius; x <= zone.centerX + zone.radius; x++) {
                    if (x >= 0 && x < this.width && y >= 0 && y < this.height) {
                        // Skip protected terrain
                        if (this.map[y] && this.map[y][x] &&
                            (this.map[y][x].startsWith('W') || 
                             this.map[y][x].startsWith('SH') ||
                             this.map[y][x].startsWith('T') ||
                             this.map[y][x].startsWith('ROCK'))) {
                            continue;
                        }
                        
                        const distance = Math.sqrt(
                            Math.pow(x - zone.centerX, 2) + 
                            Math.pow(y - zone.centerY, 2)
                        );
                        
                        // Create organic deposit with noise
                        const depositNoise = this.coherentNoise(x * 0.4, y * 0.4) * 0.3;
                        const depositChance = Math.max(0, 1 - (distance / (zone.radius + depositNoise)));
                        
                        if (this.seededRandom(x + zoneIndex * 1000, y) < depositChance * 0.8) {
                            const density = Math.max(0.3, depositChance);
                            tiberiumPatch.push({ 
                                x, 
                                y, 
                                type: resourceType,
                                density: density,
                                zone: zoneIndex
                            });
                        }
                    }
                }
            }
            
            if (tiberiumPatch.length > 0) {
                this.tiberiumFields.push(tiberiumPatch);
            }
        });
        
        console.log(`Generated ${this.tiberiumFields.length} balanced resource zones`);
    }
    
    calculateResourceZones() {
        // Calculate strategic resource placement for balanced gameplay
        const zones = [];
        
        // Base resource zones (equidistant from starting positions)
        const baseZones = [
            { centerX: Math.floor(this.width * 0.2), centerY: Math.floor(this.height * 0.3), radius: 3, type: 'green', priority: 'high' },
            { centerX: Math.floor(this.width * 0.8), centerY: Math.floor(this.height * 0.7), radius: 3, type: 'green', priority: 'high' },
        ];
        
        // Contested middle resources
        const contestedZones = [
            { centerX: Math.floor(this.width * 0.5), centerY: Math.floor(this.height * 0.5), radius: 4, type: 'blue', priority: 'high' },
            { centerX: Math.floor(this.width * 0.3), centerY: Math.floor(this.height * 0.7), radius: 2, type: 'green', priority: 'medium' },
            { centerX: Math.floor(this.width * 0.7), centerY: Math.floor(this.height * 0.3), radius: 2, type: 'green', priority: 'medium' }
        ];
        
        // Expansion resources
        const expansionZones = [
            { centerX: Math.floor(this.width * 0.1), centerY: Math.floor(this.height * 0.8), radius: 2, type: 'green', priority: 'low' },
            { centerX: Math.floor(this.width * 0.9), centerY: Math.floor(this.height * 0.2), radius: 2, type: 'green', priority: 'low' }
        ];
        
        zones.push(...baseZones, ...contestedZones, ...expansionZones);
        
        // Validate zone positions (ensure they're on buildable terrain nearby)
        zones.forEach(zone => {
            zone.isValid = this.validateResourceZone(zone);
        });
        
        return zones.filter(zone => zone.isValid);
    }
    
    validateResourceZone(zone) {
        // Check if there's enough buildable terrain around the resource zone
        let buildableCount = 0;
        const checkRadius = zone.radius + 3;
        
        for (let y = zone.centerY - checkRadius; y <= zone.centerY + checkRadius; y++) {
            for (let x = zone.centerX - checkRadius; x <= zone.centerX + checkRadius; x++) {
                if (x >= 0 && x < this.width && y >= 0 && y < this.height) {
                    if (this.isBuildable(x, y)) {
                        buildableCount++;
                    }
                }
            }
        }
        
        const totalArea = (checkRadius * 2 + 1) * (checkRadius * 2 + 1);
        const buildableRatio = buildableCount / totalArea;
        
        return buildableRatio > 0.4; // At least 40% buildable area around resource
    }
    
    // Map validation and optimization
    validateAndOptimizeMap() {
        let optimizationPasses = 0;
        const maxPasses = 3;
        
        while (optimizationPasses < maxPasses) {
            const issues = this.identifyMapIssues();
            
            if (issues.length === 0) {
                break; // Map is valid
            }
            
            console.log(`Optimization pass ${optimizationPasses + 1}: fixing ${issues.length} issues`);
            this.fixMapIssues(issues);
            optimizationPasses++;
        }
        
        // Final quality check
        const finalScore = this.calculateQualityScore();
        if (finalScore < this.options.qualityThreshold) {
            console.warn(`Map quality below threshold: ${finalScore} < ${this.options.qualityThreshold}`);
        }
    }
    
    identifyMapIssues() {
        const issues = [];
        
        // Check for isolated water bodies
        const waterClusters = this.findWaterClusters();
        waterClusters.forEach(cluster => {
            if (cluster.size < 4) {
                issues.push({ type: 'isolated_water', cluster });
            }
        });
        
        // Check for insufficient buildable area
        const buildableRatio = this.calculateBuildableRatio();
        if (buildableRatio < 0.6) {
            issues.push({ type: 'insufficient_buildable', ratio: buildableRatio });
        }
        
        // Check for resource accessibility
        this.tiberiumFields.forEach((field, index) => {
            if (!this.isResourceAccessible(field)) {
                issues.push({ type: 'inaccessible_resource', fieldIndex: index });
            }
        });
        
        return issues;
    }
    
    fixMapIssues(issues) {
        issues.forEach(issue => {
            switch (issue.type) {
                case 'isolated_water':
                    this.fixIsolatedWater(issue.cluster);
                    break;
                case 'insufficient_buildable':
                    this.increaseBuildableArea();
                    break;
                case 'inaccessible_resource':
                    this.fixResourceAccess(issue.fieldIndex);
                    break;
            }
        });
    }
    
    fixIsolatedWater(cluster) {
        // Convert small isolated water to shore or land
        cluster.tiles.forEach(tile => {
            if (this.seededRandom(tile.x + 200000, tile.y) < 0.5) {
                const shoreTiles = this.terrainTypes.SHORE.tiles;
                this.map[tile.y][tile.x] = shoreTiles[Math.floor(this.seededRandom(tile.x + 300000, tile.y) * shoreTiles.length)];
            } else {
                const sandTiles = this.terrainTypes.SAND.tiles;
                this.map[tile.y][tile.x] = sandTiles[Math.floor(this.seededRandom(tile.x + 400000, tile.y) * sandTiles.length)];
            }
        });
    }
    
    increaseBuildableArea() {
        // Convert some decorative terrain to buildable terrain
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const tile = this.map[y][x];
                if (tile.startsWith('T') && this.seededRandom(x + 500000, y) < 0.3) {
                    // Convert some trees to buildable terrain
                    const sandTiles = this.terrainTypes.SAND.tiles;
                    this.map[y][x] = sandTiles[Math.floor(this.seededRandom(x + 600000, y) * sandTiles.length)];
                }
            }
        }
    }
    
    fixResourceAccess(fieldIndex) {
        // Ensure there are paths to resource fields
        const field = this.tiberiumFields[fieldIndex];
        if (field && field.length > 0) {
            const center = field[0]; // Use first tile as reference
            
            // Create access paths by clearing some obstacles
            const directions = [[0, -1], [1, 0], [0, 1], [-1, 0]];
            directions.forEach(([dx, dy]) => {
                for (let i = 1; i <= 3; i++) {
                    const checkX = center.x + dx * i;
                    const checkY = center.y + dy * i;
                    
                    if (checkX >= 0 && checkX < this.width && 
                        checkY >= 0 && checkY < this.height) {
                        
                        if (this.map[checkY][checkX].startsWith('ROCK') || 
                            this.map[checkY][checkX].startsWith('T')) {
                            
                            const sandTiles = this.terrainTypes.SAND.tiles;
                            this.map[checkY][checkX] = sandTiles[Math.floor(this.seededRandom(checkX + 700000, checkY) * sandTiles.length)];
                        }
                    }
                }
            });
        }
    }
    
    // Calculate comprehensive quality metrics
    calculateQualityMetrics() {
        this.qualityMetrics.terrainCoherence = this.calculateTerrainCoherence();
        this.qualityMetrics.resourceBalance = this.calculateResourceBalance();
        this.qualityMetrics.buildableArea = this.calculateBuildableRatio() * 100;
        this.qualityMetrics.strategicBalance = this.calculateStrategicBalance();
        
        // Overall score (weighted average)
        this.qualityMetrics.overallScore = (
            this.qualityMetrics.terrainCoherence * 0.25 +
            this.qualityMetrics.resourceBalance * 0.35 +
            this.qualityMetrics.buildableArea * 0.2 +
            this.qualityMetrics.strategicBalance * 0.2
        );
        
        console.log('Map Quality Metrics:', this.qualityMetrics);
    }
    
    calculateQualityScore() {
        this.calculateQualityMetrics();
        return this.qualityMetrics.overallScore;
    }
    
    calculateTerrainCoherence() {
        let coherentTransitions = 0;
        let totalTransitions = 0;
        
        for (let y = 0; y < this.height - 1; y++) {
            for (let x = 0; x < this.width - 1; x++) {
                const current = this.map[y][x];
                const right = this.map[y][x + 1];
                const down = this.map[y + 1][x];
                
                totalTransitions += 2;
                
                // Check if transitions are coherent
                if (this.areTerrainTypesCompatible(current, right)) {
                    coherentTransitions++;
                }
                if (this.areTerrainTypesCompatible(current, down)) {
                    coherentTransitions++;
                }
            }
        }
        
        return (coherentTransitions / totalTransitions) * 100;
    }
    
    calculateResourceBalance() {
        if (this.tiberiumFields.length === 0) return 0;
        
        const fieldSizes = this.tiberiumFields.map(field => field.length);
        const avgSize = fieldSizes.reduce((a, b) => a + b, 0) / fieldSizes.length;
        
        // Calculate variance in field sizes (lower variance = better balance)
        const variance = fieldSizes.reduce((acc, size) => acc + Math.pow(size - avgSize, 2), 0) / fieldSizes.length;
        const coefficient = Math.sqrt(variance) / avgSize;
        
        // Convert to score (lower coefficient = higher score)
        return Math.max(0, 100 - (coefficient * 100));
    }
    
    calculateStrategicBalance() {
        // Measure distribution of strategic elements (cover, high ground, etc.)
        const quadrants = [0, 0, 0, 0]; // NW, NE, SW, SE
        const midX = this.width / 2;
        const midY = this.height / 2;
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const tile = this.map[y][x];
                if (tile.startsWith('ROCK') || tile.startsWith('T')) {
                    const quadrant = (x < midX ? 0 : 1) + (y < midY ? 0 : 2);
                    quadrants[quadrant]++;
                }
            }
        }
        
        // Calculate balance (lower variance = better balance)
        const avgElements = quadrants.reduce((a, b) => a + b, 0) / 4;
        const variance = quadrants.reduce((acc, count) => acc + Math.pow(count - avgElements, 2), 0) / 4;
        const coefficient = avgElements > 0 ? Math.sqrt(variance) / avgElements : 1;
        
        return Math.max(0, 100 - (coefficient * 50));
    }
    
    areTerrainTypesCompatible(tile1, tile2) {
        // Check if two terrain types should naturally be adjacent
        const type1 = tile1.charAt(0);
        const type2 = tile2.charAt(0);
        
        // Same type is always compatible
        if (type1 === type2) return true;
        
        // Define compatible type pairs
        const compatiblePairs = new Set([
            'SD', 'DS', // Sand-Dirt
            'SW', 'WS', 'WH', 'HW', 'HS', 'SH', 'HD', 'DH', // Water-Shore-Land
            'ST', 'TS', 'DT', 'TD', // Land-Trees
            'SR', 'RS', 'DR', 'RD'  // Land-Rocks
        ]);
        
        return compatiblePairs.has(type1 + type2);
    }
    
    // Helper methods for validation
    findWaterClusters() {
        const visited = Array(this.height).fill().map(() => Array(this.width).fill(false));
        const clusters = [];
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (!visited[y][x] && this.map[y][x].startsWith('W')) {
                    const cluster = this.floodFill(x, y, visited, tile => tile.startsWith('W'));
                    clusters.push({ size: cluster.length, tiles: cluster });
                }
            }
        }
        
        return clusters;
    }
    
    floodFill(startX, startY, visited, condition) {
        const stack = [{x: startX, y: startY}];
        const result = [];
        
        while (stack.length > 0) {
            const {x, y} = stack.pop();
            
            if (x < 0 || x >= this.width || y < 0 || y >= this.height || 
                visited[y][x] || !condition(this.map[y][x])) {
                continue;
            }
            
            visited[y][x] = true;
            result.push({x, y});
            
            // Add neighbors
            stack.push({x: x + 1, y}, {x: x - 1, y}, {x, y: y + 1}, {x, y: y - 1});
        }
        
        return result;
    }
    
    calculateBuildableRatio() {
        let buildableCount = 0;
        let totalCount = 0;
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                totalCount++;
                if (this.isBuildable(x, y)) {
                    buildableCount++;
                }
            }
        }
        
        return buildableCount / totalCount;
    }
    
    isResourceAccessible(field) {
        if (!field || field.length === 0) return false;
        
        // Check if there are buildable tiles adjacent to the resource field
        const resourceTiles = new Set(field.map(tile => `${tile.x},${tile.y}`));
        
        for (const tile of field) {
            const directions = [[0, -1], [1, 0], [0, 1], [-1, 0]];
            
            for (const [dx, dy] of directions) {
                const checkX = tile.x + dx;
                const checkY = tile.y + dy;
                
                if (checkX >= 0 && checkX < this.width && 
                    checkY >= 0 && checkY < this.height &&
                    !resourceTiles.has(`${checkX},${checkY}`) &&
                    this.isBuildable(checkX, checkY)) {
                    return true; // Found accessible buildable tile
                }
            }
        }
        
        return false; // No accessible buildable tiles found
    }
    
    // Get map summary for debugging
    getMapSummary() {
        const terrainCount = {};
        let totalTiles = 0;
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const terrain = this.map[y][x];
                const prefix = terrain.substring(0, terrain.indexOf('0') > 0 ? terrain.indexOf('0') - 1 : 3);
                terrainCount[prefix] = (terrainCount[prefix] || 0) + 1;
                totalTiles++;
            }
        }
        
        return {
            dimensions: { width: this.width, height: this.height },
            totalTiles,
            terrainDistribution: terrainCount,
            tiberiumFields: this.tiberiumFields.length,
            totalTiberiumTiles: this.tiberiumFields.reduce((sum, field) => sum + field.length, 0)
        };
    }
}

export default TerrainGenerator;