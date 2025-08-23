/**
 * AutoTiler - Advanced Bitmasking and Auto-Tiling System
 * 
 * This system provides intelligent automatic tile selection based on 
 * neighboring terrain types using bitmasking algorithms. It handles
 * complex transitions like shorelines, cliff edges, and forest borders.
 * 
 * Key Features:
 * - 8-directional bitmasking for smooth transitions
 * - Support for multiple terrain layers (base, transition, overlay)
 * - Corner handling for complex junction tiles
 * - Weighted tile selection for variation
 * - Compatible with C&C terrain tile sets
 */

class AutoTiler {
    constructor(tileDefinitions) {
        // Initialize constants first
        // Bitmasking constants for 8-directional neighbors
        this.NEIGHBORS = {
            NORTH: 1,      // 0001
            EAST: 2,       // 0010  
            SOUTH: 4,      // 0100
            WEST: 8,       // 1000
            NORTHEAST: 16, // 0001 0000
            SOUTHEAST: 32, // 0010 0000
            SOUTHWEST: 64, // 0100 0000
            NORTHWEST: 128 // 1000 0000
        };
        
        // Initialize tile definitions after NEIGHBORS is set
        this.tileDefinitions = tileDefinitions || this.getDefaultTileDefinitions();
        
        // Commonly used bitmask patterns
        this.PATTERNS = {
            ISOLATED: 0,
            HORIZONTAL: this.NEIGHBORS.EAST | this.NEIGHBORS.WEST,
            VERTICAL: this.NEIGHBORS.NORTH | this.NEIGHBORS.SOUTH,
            CORNER_NE: this.NEIGHBORS.NORTH | this.NEIGHBORS.EAST,
            CORNER_NW: this.NEIGHBORS.NORTH | this.NEIGHBORS.WEST,
            CORNER_SE: this.NEIGHBORS.SOUTH | this.NEIGHBORS.EAST,
            CORNER_SW: this.NEIGHBORS.SOUTH | this.NEIGHBORS.WEST,
            T_NORTH: this.NEIGHBORS.EAST | this.NEIGHBORS.WEST | this.NEIGHBORS.SOUTH,
            T_EAST: this.NEIGHBORS.NORTH | this.NEIGHBORS.SOUTH | this.NEIGHBORS.WEST,
            T_SOUTH: this.NEIGHBORS.EAST | this.NEIGHBORS.WEST | this.NEIGHBORS.NORTH,
            T_WEST: this.NEIGHBORS.NORTH | this.NEIGHBORS.SOUTH | this.NEIGHBORS.EAST,
            CROSS: this.NEIGHBORS.NORTH | this.NEIGHBORS.EAST | this.NEIGHBORS.SOUTH | this.NEIGHBORS.WEST
        };
        
        // Precomputed tile lookup tables for performance
        this.tileLookupCache = new Map();
        this.initializeLookupCache();
    }

    /**
     * Apply auto-tiling to a terrain map
     * @param {Array} terrainMap - 2D array of base terrain types
     * @param {Object} options - Tiling options
     * @returns {Object} - Processed map with transition tiles
     */
    autoTile(terrainMap, options = {}) {
        const {
            enableTransitions = true,
            enableCorners = true,
            enableVariation = true,
            layers = ['base', 'transition', 'overlay']
        } = options;
        
        const height = terrainMap.length;
        const width = terrainMap[0].length;
        
        // Initialize result with multiple layers
        const result = {
            base: this.deepCopy2D(terrainMap),
            transition: this.createEmptyLayer(width, height),
            overlay: this.createEmptyLayer(width, height),
            metadata: {
                width,
                height,
                processedTiles: 0,
                transitionTiles: 0,
                cornerTiles: 0
            }
        };
        
        // Process each cell for transitions
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const baseTile = terrainMap[y][x];
                const processedTile = this.processTileTransitions(
                    terrainMap, x, y, baseTile, {
                        enableTransitions,
                        enableCorners,
                        enableVariation
                    }
                );
                
                if (processedTile) {
                    if (processedTile.layer === 'base') {
                        result.base[y][x] = processedTile.tileId;
                    } else if (processedTile.layer === 'transition') {
                        result.transition[y][x] = processedTile.tileId;
                        result.metadata.transitionTiles++;
                    } else if (processedTile.layer === 'overlay') {
                        result.overlay[y][x] = processedTile.tileId;
                    }
                    
                    if (processedTile.isCorner) {
                        result.metadata.cornerTiles++;
                    }
                }
                
                result.metadata.processedTiles++;
            }
        }
        
        return result;
    }

    /**
     * Process transitions for a single tile
     */
    processTileTransitions(terrainMap, x, y, baseTile, options) {
        const height = terrainMap.length;
        const width = terrainMap[0].length;
        
        // Calculate bitmask for neighboring terrain
        let mask = 0;
        const neighbors = this.getNeighborTiles(terrainMap, x, y);
        
        // Check each direction for matching terrain type
        const terrainType = this.getTerrainType(baseTile);
        
        for (const [direction, neighborTile] of Object.entries(neighbors)) {
            if (neighborTile && this.getTerrainType(neighborTile) === terrainType) {
                mask |= this.NEIGHBORS[direction.toUpperCase()];
            }
        }
        
        // Special handling for shoreline transitions
        if (this.isWaterTile(baseTile)) {
            return this.processWaterTransition(terrainMap, x, y, mask, neighbors, options);
        }
        
        // Special handling for forest edges
        if (this.isTreeTile(baseTile)) {
            return this.processForestTransition(terrainMap, x, y, mask, neighbors, options);
        }
        
        // Special handling for cliff/elevation changes
        if (this.isRockTile(baseTile)) {
            return this.processRockTransition(terrainMap, x, y, mask, neighbors, options);
        }
        
        // Default terrain variation
        if (options.enableVariation && Math.random() < 0.1) {
            return this.selectVariationTile(baseTile, mask);
        }
        
        return null; // No change needed
    }

    /**
     * Process water shoreline transitions
     */
    processWaterTransition(terrainMap, x, y, mask, neighbors, options) {
        // Check if water tile is adjacent to land
        let hasLandNeighbor = false;
        const landDirections = [];
        
        for (const [direction, tile] of Object.entries(neighbors)) {
            if (tile && !this.isWaterTile(tile)) {
                hasLandNeighbor = true;
                landDirections.push(direction.toUpperCase());
            }
        }
        
        if (!hasLandNeighbor) {
            // Deep water - no transition needed
            return null;
        }
        
        // Calculate shore transition mask
        let shoreMask = 0;
        for (const direction of landDirections) {
            shoreMask |= this.NEIGHBORS[direction];
        }
        
        // Select appropriate shore tile based on mask
        const shoreTiles = this.tileDefinitions.shore;
        if (shoreTiles && shoreTiles[shoreMask]) {
            const tileOptions = shoreTiles[shoreMask];
            const selectedTile = this.selectFromWeightedList(tileOptions);
            
            return {
                tileId: selectedTile,
                layer: 'transition',
                isCorner: this.isCornerPattern(shoreMask),
                mask: shoreMask
            };
        }
        
        // Fallback to simple shore tile
        return {
            tileId: 'SH1',
            layer: 'transition',
            isCorner: false,
            mask: shoreMask
        };
    }

    /**
     * Process forest edge transitions
     */
    processForestTransition(terrainMap, x, y, mask, neighbors, options) {
        // Check for forest edge conditions
        let hasNonTreeNeighbor = false;
        
        for (const [direction, tile] of Object.entries(neighbors)) {
            if (tile && !this.isTreeTile(tile) && !this.isWaterTile(tile)) {
                hasNonTreeNeighbor = true;
                break;
            }
        }
        
        if (!hasNonTreeNeighbor) {
            // Deep forest - might add variation
            if (options.enableVariation && Math.random() < 0.15) {
                const treeTiles = this.tileDefinitions.trees.variations || ['T01', 'T02', 'T03'];
                return {
                    tileId: treeTiles[Math.floor(Math.random() * treeTiles.length)],
                    layer: 'base',
                    isCorner: false,
                    mask: mask
                };
            }
            return null;
        }
        
        // Forest edge - select appropriate tree tile
        const edgeTrees = this.tileDefinitions.trees.edge || ['T05', 'T06'];
        return {
            tileId: edgeTrees[Math.floor(Math.random() * edgeTrees.length)],
            layer: 'base',
            isCorner: false,
            mask: mask
        };
    }

    /**
     * Process rock formation transitions
     */
    processRockTransition(terrainMap, x, y, mask, neighbors, options) {
        // Rock formations don't typically have smooth transitions
        // Instead, we vary the rock type based on cluster size
        let rockNeighborCount = 0;
        
        for (const [direction, tile] of Object.entries(neighbors)) {
            if (tile && this.isRockTile(tile)) {
                rockNeighborCount++;
            }
        }
        
        // Select rock type based on clustering
        let rockTiles;
        if (rockNeighborCount >= 3) {
            // Dense cluster - use larger rocks
            rockTiles = ['ROCK4', 'ROCK5', 'ROCK6', 'ROCK7'];
        } else if (rockNeighborCount >= 1) {
            // Small cluster - use medium rocks
            rockTiles = ['ROCK2', 'ROCK3', 'ROCK4'];
        } else {
            // Isolated rock - use small rocks
            rockTiles = ['ROCK1', 'ROCK2'];
        }
        
        return {
            tileId: rockTiles[Math.floor(Math.random() * rockTiles.length)],
            layer: 'base',
            isCorner: false,
            mask: mask
        };
    }

    /**
     * Get neighboring tiles in all 8 directions
     */
    getNeighborTiles(terrainMap, x, y) {
        const height = terrainMap.length;
        const width = terrainMap[0].length;
        
        return {
            north: (y > 0) ? terrainMap[y - 1][x] : null,
            east: (x < width - 1) ? terrainMap[y][x + 1] : null,
            south: (y < height - 1) ? terrainMap[y + 1][x] : null,
            west: (x > 0) ? terrainMap[y][x - 1] : null,
            northeast: (y > 0 && x < width - 1) ? terrainMap[y - 1][x + 1] : null,
            southeast: (y < height - 1 && x < width - 1) ? terrainMap[y + 1][x + 1] : null,
            southwest: (y < height - 1 && x > 0) ? terrainMap[y + 1][x - 1] : null,
            northwest: (y > 0 && x > 0) ? terrainMap[y - 1][x - 1] : null
        };
    }

    /**
     * Initialize lookup cache for performance
     */
    initializeLookupCache() {
        // Pre-calculate common patterns
        const commonMasks = [
            0, // Isolated
            this.PATTERNS.HORIZONTAL,
            this.PATTERNS.VERTICAL,
            this.PATTERNS.CORNER_NE,
            this.PATTERNS.CORNER_NW,
            this.PATTERNS.CORNER_SE,
            this.PATTERNS.CORNER_SW,
            this.PATTERNS.CROSS
        ];
        
        for (const mask of commonMasks) {
            this.tileLookupCache.set(mask, this.calculateTileForMask(mask));
        }
    }

    /**
     * Calculate appropriate tile for a given mask
     */
    calculateTileForMask(mask) {
        // This would contain the logic for selecting tiles based on bitmask
        // Implementation depends on specific tile set organization
        return null;
    }

    /**
     * Helper functions for terrain type identification
     */
    isWaterTile(tile) {
        return tile && (tile.startsWith('W') || tile.includes('water'));
    }

    isTreeTile(tile) {
        return tile && (tile.startsWith('T') || tile.includes('tree'));
    }

    isRockTile(tile) {
        return tile && (tile.startsWith('ROCK') || tile.includes('rock'));
    }

    isShoreTile(tile) {
        return tile && (tile.startsWith('SH') || tile.includes('shore'));
    }

    getTerrainType(tile) {
        if (this.isWaterTile(tile)) return 'water';
        if (this.isTreeTile(tile)) return 'tree';
        if (this.isRockTile(tile)) return 'rock';
        if (this.isShoreTile(tile)) return 'shore';
        if (tile && tile.startsWith('D')) return 'dirt';
        if (tile && tile.startsWith('S')) return 'sand';
        return 'unknown';
    }

    /**
     * Check if mask represents a corner pattern
     */
    isCornerPattern(mask) {
        const cornerMasks = [
            this.PATTERNS.CORNER_NE,
            this.PATTERNS.CORNER_NW,
            this.PATTERNS.CORNER_SE,
            this.PATTERNS.CORNER_SW
        ];
        return cornerMasks.includes(mask);
    }

    /**
     * Select tile from weighted list
     */
    selectFromWeightedList(tileOptions) {
        if (Array.isArray(tileOptions)) {
            return tileOptions[Math.floor(Math.random() * tileOptions.length)];
        }
        
        if (typeof tileOptions === 'object') {
            const tiles = Object.keys(tileOptions);
            const weights = Object.values(tileOptions);
            
            const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
            let random = Math.random() * totalWeight;
            
            for (let i = 0; i < tiles.length; i++) {
                random -= weights[i];
                if (random <= 0) {
                    return tiles[i];
                }
            }
            
            return tiles[tiles.length - 1];
        }
        
        return tileOptions;
    }

    /**
     * Select variation tile for base terrain
     */
    selectVariationTile(baseTile, mask) {
        const terrainType = this.getTerrainType(baseTile);
        const variations = this.tileDefinitions.variations?.[terrainType];
        
        if (variations && variations.length > 1) {
            const filteredVariations = variations.filter(tile => tile !== baseTile);
            if (filteredVariations.length > 0) {
                return {
                    tileId: filteredVariations[Math.floor(Math.random() * filteredVariations.length)],
                    layer: 'base',
                    isCorner: false,
                    mask: mask
                };
            }
        }
        
        return null;
    }

    /**
     * Create empty layer
     */
    createEmptyLayer(width, height) {
        const layer = [];
        for (let y = 0; y < height; y++) {
            layer[y] = new Array(width).fill(null);
        }
        return layer;
    }

    /**
     * Deep copy 2D array
     */
    deepCopy2D(array) {
        return array.map(row => [...row]);
    }

    /**
     * Get default tile definitions for C&C terrain
     */
    getDefaultTileDefinitions() {
        return {
            shore: {
                // Shore transition patterns mapped to bitmasks
                [this.NEIGHBORS.NORTH]: ['SH1'],
                [this.NEIGHBORS.EAST]: ['SH2'], 
                [this.NEIGHBORS.SOUTH]: ['SH3'],
                [this.NEIGHBORS.WEST]: ['SH4'],
                [this.NEIGHBORS.NORTH | this.NEIGHBORS.EAST]: ['SH5'],
                [this.NEIGHBORS.SOUTH | this.NEIGHBORS.WEST]: ['SH6']
            },
            trees: {
                variations: ['T01', 'T02', 'T03', 'T05', 'T06', 'T07', 'T08', 'T09'],
                edge: ['T05', 'T06'],
                dense: ['T07', 'T08', 'T09']
            },
            rocks: {
                small: ['ROCK1', 'ROCK2'],
                medium: ['ROCK3', 'ROCK4'],
                large: ['ROCK5', 'ROCK6', 'ROCK7']
            },
            variations: {
                sand: ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08'],
                dirt: ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08'],
                water: ['W1', 'W2']
            }
        };
    }

    /**
     * Generate tileset rules for Wave Function Collapse compatibility
     */
    generateWFCRules() {
        const rules = {};
        const tileTypes = ['sand', 'dirt', 'water', 'shore', 'tree', 'rock'];
        
        for (const [terrainType, tiles] of Object.entries(this.tileDefinitions.variations || {})) {
            for (const tile of tiles) {
                rules[tile] = {
                    frequency: this.calculateTileFrequency(tile),
                    adjacency: this.generateAdjacencyRules(tile, terrainType)
                };
            }
        }
        
        return rules;
    }

    /**
     * Calculate frequency for WFC
     */
    calculateTileFrequency(tile) {
        if (tile.startsWith('S')) return 0.4; // Sand is common
        if (tile.startsWith('D')) return 0.3; // Dirt is moderately common
        if (tile.startsWith('W')) return 0.1; // Water is less common
        if (tile.startsWith('SH')) return 0.05; // Shore is rare
        if (tile.startsWith('T')) return 0.1; // Trees are uncommon
        if (tile.startsWith('ROCK')) return 0.05; // Rocks are rare
        return 0.1;
    }

    /**
     * Generate adjacency rules for WFC
     */
    generateAdjacencyRules(tile, terrainType) {
        const adjacency = {
            up: [],
            down: [],
            left: [],
            right: []
        };
        
        // Same terrain type is always compatible
        const compatibleTiles = this.tileDefinitions.variations[terrainType] || [tile];
        
        for (const direction of ['up', 'down', 'left', 'right']) {
            adjacency[direction] = [...compatibleTiles];
            
            // Add transition rules
            if (terrainType === 'sand') {
                adjacency[direction].push(...(this.tileDefinitions.variations.dirt || []));
            }
            if (terrainType === 'water') {
                adjacency[direction].push(...(this.tileDefinitions.shore[this.NEIGHBORS.NORTH] || []));
            }
        }
        
        return adjacency;
    }
}

export default AutoTiler;