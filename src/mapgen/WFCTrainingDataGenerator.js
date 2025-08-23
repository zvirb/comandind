/**
 * WFC Training Data Generator
 * 
 * Converts extracted OpenRA map data into Wave Function Collapse training datasets.
 * Analyzes tile patterns and generates adjacency rules, frequency distributions,
 * and constraint sets for the WFC algorithm.
 * 
 * Key features:
 * - Analyzes tile adjacency patterns from real maps
 * - Generates WFC-compatible rule sets
 * - Calculates tile frequency distributions
 * - Creates optimized training datasets
 * - Supports pattern augmentation and filtering
 */

import fs from 'fs';
import path from 'path';

class WFCTrainingDataGenerator {
    constructor() {
        // Adjacency tracking: tile -> direction -> Set of compatible tiles
        this.adjacencyRules = new Map();
        
        // Tile frequency tracking
        this.tileFrequencies = new Map();
        
        // Pattern occurrence tracking for N-tile patterns
        this.patternOccurrences = new Map();
        
        // Configuration
        this.config = {
            // Minimum occurrences for a pattern to be considered valid
            minPatternOccurrences: 2,
            
            // Whether to include diagonal adjacencies
            includeDiagonals: false,
            
            // Pattern size for N-tile pattern extraction (2x2, 3x3, etc.)
            patternSize: 2,
            
            // Whether to augment patterns with rotations and reflections
            augmentPatterns: true,
            
            // Filter rare tiles from training data
            filterRareTiles: true,
            rareThreshold: 0.001, // Tiles appearing less than 0.1% are considered rare
            
            // Weight adjustments for specific tile types
            tileWeights: {
                'S': 1.2,   // Slightly prefer sand (buildable)
                'D': 1.1,   // Slightly prefer dirt (buildable)
                'W': 0.8,   // Slightly reduce water frequency
                'T': 0.9,   // Slightly reduce tree frequency
                'ROCK': 0.7 // Reduce rock frequency
            }
        };
        
        // Statistics
        this.stats = {
            mapsProcessed: 0,
            tilesAnalyzed: 0,
            uniquePatterns: 0,
            adjacencyRules: 0
        };
    }
    
    /**
     * Process extracted map data to generate training data
     * @param {Array} extractedMaps - Array of extracted map data from OpenRAMapExtractor
     * @returns {Object} WFC training data with rules and frequencies
     */
    generateTrainingData(extractedMaps) {
        console.log(`Generating training data from ${extractedMaps.length} maps...`);
        
        // Reset data structures
        this.resetData();
        
        // Process each map
        for (const mapData of extractedMaps) {
            if (!mapData || !mapData.terrain) continue;
            
            this.processMap(mapData);
            this.stats.mapsProcessed++;
        }
        
        // Post-process and optimize rules
        const processedRules = this.postProcessRules();
        
        // Generate final training dataset
        const trainingData = this.compileTrainingData(processedRules);
        
        console.log(`Training data generation complete. Stats:`, this.stats);
        
        return trainingData;
    }
    
    /**
     * Process a single map to extract patterns
     */
    processMap(mapData) {
        const { terrain, width, height } = mapData;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const currentTile = terrain[y][x];
                
                // Update tile frequency
                this.updateTileFrequency(currentTile);
                
                // Analyze adjacencies
                this.analyzeAdjacencies(terrain, x, y, width, height);
                
                // Extract N-tile patterns
                if (this.config.patternSize > 1) {
                    this.extractPattern(terrain, x, y, width, height);
                }
                
                this.stats.tilesAnalyzed++;
            }
        }
    }
    
    /**
     * Update tile frequency count
     */
    updateTileFrequency(tile) {
        const count = this.tileFrequencies.get(tile) || 0;
        this.tileFrequencies.set(tile, count + 1);
    }
    
    /**
     * Analyze tile adjacencies at a position
     */
    analyzeAdjacencies(terrain, x, y, width, height) {
        const currentTile = terrain[y][x];
        
        // Initialize adjacency rules for this tile if needed
        if (!this.adjacencyRules.has(currentTile)) {
            this.adjacencyRules.set(currentTile, {
                up: new Map(),
                down: new Map(),
                left: new Map(),
                right: new Map()
            });
        }
        
        const rules = this.adjacencyRules.get(currentTile);
        
        // Check cardinal directions
        const directions = [
            { dx: 0, dy: -1, dir: 'up' },
            { dx: 0, dy: 1, dir: 'down' },
            { dx: -1, dy: 0, dir: 'left' },
            { dx: 1, dy: 0, dir: 'right' }
        ];
        
        for (const { dx, dy, dir } of directions) {
            const nx = x + dx;
            const ny = y + dy;
            
            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                const neighborTile = terrain[ny][nx];
                const count = rules[dir].get(neighborTile) || 0;
                rules[dir].set(neighborTile, count + 1);
            }
        }
        
        // Optionally check diagonal directions
        if (this.config.includeDiagonals) {
            const diagonals = [
                { dx: -1, dy: -1, dir: 'upLeft' },
                { dx: 1, dy: -1, dir: 'upRight' },
                { dx: -1, dy: 1, dir: 'downLeft' },
                { dx: 1, dy: 1, dir: 'downRight' }
            ];
            
            for (const { dx, dy, dir } of diagonals) {
                const nx = x + dx;
                const ny = y + dy;
                
                if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                    if (!rules[dir]) rules[dir] = new Map();
                    const neighborTile = terrain[ny][nx];
                    const count = rules[dir].get(neighborTile) || 0;
                    rules[dir].set(neighborTile, count + 1);
                }
            }
        }
    }
    
    /**
     * Extract N-tile patterns from the map
     */
    extractPattern(terrain, x, y, width, height) {
        const size = this.config.patternSize;
        
        // Check if we can extract a full pattern at this position
        if (x + size > width || y + size > height) return;
        
        // Extract pattern
        const pattern = [];
        for (let py = 0; py < size; py++) {
            const row = [];
            for (let px = 0; px < size; px++) {
                row.push(terrain[y + py][x + px]);
            }
            pattern.push(row);
        }
        
        // Convert pattern to string key
        const patternKey = this.patternToKey(pattern);
        
        // Update pattern occurrence count
        const count = this.patternOccurrences.get(patternKey) || 0;
        this.patternOccurrences.set(patternKey, count + 1);
        
        // Generate augmented patterns if enabled
        if (this.config.augmentPatterns) {
            this.generateAugmentedPatterns(pattern);
        }
    }
    
    /**
     * Convert pattern array to string key
     */
    patternToKey(pattern) {
        return pattern.map(row => row.join(',')).join('|');
    }
    
    /**
     * Generate augmented patterns (rotations and reflections)
     */
    generateAugmentedPatterns(pattern) {
        const size = pattern.length;
        
        // Rotate 90 degrees
        const rotate90 = [];
        for (let i = 0; i < size; i++) {
            const row = [];
            for (let j = size - 1; j >= 0; j--) {
                row.push(pattern[j][i]);
            }
            rotate90.push(row);
        }
        this.recordAugmentedPattern(rotate90);
        
        // Rotate 180 degrees
        const rotate180 = [];
        for (let i = size - 1; i >= 0; i--) {
            const row = [];
            for (let j = size - 1; j >= 0; j--) {
                row.push(pattern[i][j]);
            }
            rotate180.push(row);
        }
        this.recordAugmentedPattern(rotate180);
        
        // Rotate 270 degrees
        const rotate270 = [];
        for (let i = size - 1; i >= 0; i--) {
            const row = [];
            for (let j = 0; j < size; j++) {
                row.push(pattern[j][i]);
            }
            rotate270.push(row);
        }
        this.recordAugmentedPattern(rotate270);
        
        // Horizontal flip
        const flipH = [];
        for (let i = 0; i < size; i++) {
            const row = [];
            for (let j = size - 1; j >= 0; j--) {
                row.push(pattern[i][j]);
            }
            flipH.push(row);
        }
        this.recordAugmentedPattern(flipH);
        
        // Vertical flip
        const flipV = [];
        for (let i = size - 1; i >= 0; i--) {
            flipV.push([...pattern[i]]);
        }
        this.recordAugmentedPattern(flipV);
    }
    
    /**
     * Record an augmented pattern
     */
    recordAugmentedPattern(pattern) {
        const patternKey = this.patternToKey(pattern);
        const count = this.patternOccurrences.get(patternKey) || 0;
        this.patternOccurrences.set(patternKey, count + 0.5); // Weight augmented patterns less
    }
    
    /**
     * Post-process rules to filter and optimize
     */
    postProcessRules() {
        const processedRules = {};
        
        // Calculate total tile count for frequency normalization
        let totalTiles = 0;
        for (const count of this.tileFrequencies.values()) {
            totalTiles += count;
        }
        
        // Process each tile's rules
        for (const [tile, adjacencies] of this.adjacencyRules.entries()) {
            // Check if tile is rare and should be filtered
            if (this.config.filterRareTiles) {
                const frequency = (this.tileFrequencies.get(tile) || 0) / totalTiles;
                if (frequency < this.config.rareThreshold) {
                    continue; // Skip rare tiles
                }
            }
            
            processedRules[tile] = {
                frequency: this.calculateWeightedFrequency(tile, totalTiles),
                adjacency: {}
            };
            
            // Process each direction
            for (const [direction, neighbors] of Object.entries(adjacencies)) {
                if (neighbors instanceof Map) {
                    // Filter neighbors by minimum occurrence threshold
                    const validNeighbors = [];
                    let totalOccurrences = 0;
                    
                    for (const [neighborTile, count] of neighbors.entries()) {
                        if (count >= this.config.minPatternOccurrences) {
                            validNeighbors.push(neighborTile);
                            totalOccurrences += count;
                        }
                    }
                    
                    // Store valid neighbors
                    if (validNeighbors.length > 0) {
                        processedRules[tile].adjacency[direction] = validNeighbors;
                    }
                }
            }
            
            this.stats.adjacencyRules++;
        }
        
        return processedRules;
    }
    
    /**
     * Calculate weighted frequency for a tile
     */
    calculateWeightedFrequency(tile, totalTiles) {
        const baseFrequency = (this.tileFrequencies.get(tile) || 0) / totalTiles;
        
        // Apply weight adjustments based on tile type
        let weight = 1.0;
        for (const [prefix, multiplier] of Object.entries(this.config.tileWeights)) {
            if (tile.startsWith(prefix)) {
                weight = multiplier;
                break;
            }
        }
        
        return baseFrequency * weight;
    }
    
    /**
     * Compile final training data structure
     */
    compileTrainingData(processedRules) {
        // Extract unique patterns
        const patterns = [];
        for (const [patternKey, count] of this.patternOccurrences.entries()) {
            if (count >= this.config.minPatternOccurrences) {
                patterns.push({
                    pattern: patternKey,
                    occurrences: count
                });
            }
        }
        
        this.stats.uniquePatterns = patterns.length;
        
        // Compile training data
        const trainingData = {
            // Metadata
            metadata: {
                mapsProcessed: this.stats.mapsProcessed,
                tilesAnalyzed: this.stats.tilesAnalyzed,
                uniqueTiles: Object.keys(processedRules).length,
                uniquePatterns: patterns.length,
                generatedAt: new Date().toISOString(),
                config: this.config
            },
            
            // Tile rules for WFC
            tileRules: processedRules,
            
            // Pattern library
            patterns: patterns,
            
            // Tile frequency distribution
            tileFrequencies: this.normalizeTileFrequencies(),
            
            // Statistics
            statistics: this.generateStatistics()
        };
        
        return trainingData;
    }
    
    /**
     * Normalize tile frequencies to probabilities
     */
    normalizeTileFrequencies() {
        const normalized = {};
        let total = 0;
        
        for (const count of this.tileFrequencies.values()) {
            total += count;
        }
        
        for (const [tile, count] of this.tileFrequencies.entries()) {
            normalized[tile] = count / total;
        }
        
        return normalized;
    }
    
    /**
     * Generate detailed statistics
     */
    generateStatistics() {
        const stats = {
            totalTilesAnalyzed: this.stats.tilesAnalyzed,
            uniqueTileTypes: this.tileFrequencies.size,
            totalPatterns: this.patternOccurrences.size,
            validPatterns: this.stats.uniquePatterns,
            adjacencyRules: this.stats.adjacencyRules,
            
            // Tile type distribution
            tileTypeDistribution: {},
            
            // Most common patterns
            topPatterns: [],
            
            // Connectivity analysis
            averageConnections: 0
        };
        
        // Calculate tile type distribution
        const typeCount = new Map();
        for (const tile of this.tileFrequencies.keys()) {
            const type = tile.replace(/[0-9]/g, '');
            typeCount.set(type, (typeCount.get(type) || 0) + 1);
        }
        
        for (const [type, count] of typeCount.entries()) {
            stats.tileTypeDistribution[type] = count;
        }
        
        // Find top patterns
        const sortedPatterns = Array.from(this.patternOccurrences.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        stats.topPatterns = sortedPatterns.map(([pattern, count]) => ({
            pattern,
            occurrences: count
        }));
        
        // Calculate average connections per tile
        let totalConnections = 0;
        let tileCount = 0;
        for (const adjacencies of this.adjacencyRules.values()) {
            for (const neighbors of Object.values(adjacencies)) {
                if (neighbors instanceof Map) {
                    totalConnections += neighbors.size;
                }
            }
            tileCount++;
        }
        
        stats.averageConnections = tileCount > 0 ? 
            (totalConnections / (tileCount * 4)).toFixed(2) : 0;
        
        return stats;
    }
    
    /**
     * Save training data to file
     */
    async saveTrainingData(trainingData, outputPath) {
        try {
            const jsonData = JSON.stringify(trainingData, null, 2);
            fs.writeFileSync(outputPath, jsonData);
            console.log(`Training data saved to: ${outputPath}`);
            
            // Also save a compact version for production use
            const compactPath = outputPath.replace('.json', '.compact.json');
            const compactData = {
                tileRules: trainingData.tileRules,
                tileFrequencies: trainingData.tileFrequencies
            };
            fs.writeFileSync(compactPath, JSON.stringify(compactData));
            console.log(`Compact training data saved to: ${compactPath}`);
            
            return true;
        } catch (error) {
            console.error(`Error saving training data:`, error.message);
            return false;
        }
    }
    
    /**
     * Load existing training data
     */
    async loadTrainingData(filePath) {
        try {
            const data = fs.readFileSync(filePath, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error(`Error loading training data:`, error.message);
            return null;
        }
    }
    
    /**
     * Merge multiple training datasets
     */
    mergeTrainingData(datasets) {
        const merged = {
            metadata: {
                mergedAt: new Date().toISOString(),
                datasetsCount: datasets.length
            },
            tileRules: {},
            patterns: [],
            tileFrequencies: {}
        };
        
        // Merge tile rules
        for (const dataset of datasets) {
            if (!dataset.tileRules) continue;
            
            for (const [tile, rules] of Object.entries(dataset.tileRules)) {
                if (!merged.tileRules[tile]) {
                    merged.tileRules[tile] = rules;
                } else {
                    // Merge adjacency rules
                    for (const [dir, neighbors] of Object.entries(rules.adjacency)) {
                        if (!merged.tileRules[tile].adjacency[dir]) {
                            merged.tileRules[tile].adjacency[dir] = neighbors;
                        } else {
                            // Combine neighbor lists
                            const combined = new Set([
                                ...merged.tileRules[tile].adjacency[dir],
                                ...neighbors
                            ]);
                            merged.tileRules[tile].adjacency[dir] = Array.from(combined);
                        }
                    }
                    
                    // Average frequencies
                    merged.tileRules[tile].frequency = 
                        (merged.tileRules[tile].frequency + rules.frequency) / 2;
                }
            }
        }
        
        // Merge patterns
        const patternMap = new Map();
        for (const dataset of datasets) {
            if (!dataset.patterns) continue;
            
            for (const pattern of dataset.patterns) {
                const existing = patternMap.get(pattern.pattern) || 0;
                patternMap.set(pattern.pattern, existing + pattern.occurrences);
            }
        }
        
        merged.patterns = Array.from(patternMap.entries()).map(([pattern, occurrences]) => ({
            pattern,
            occurrences
        }));
        
        // Merge and normalize frequencies
        const freqCounts = new Map();
        for (const dataset of datasets) {
            if (!dataset.tileFrequencies) continue;
            
            for (const [tile, freq] of Object.entries(dataset.tileFrequencies)) {
                const current = freqCounts.get(tile) || [];
                current.push(freq);
                freqCounts.set(tile, current);
            }
        }
        
        for (const [tile, frequencies] of freqCounts.entries()) {
            merged.tileFrequencies[tile] = 
                frequencies.reduce((a, b) => a + b, 0) / frequencies.length;
        }
        
        return merged;
    }
    
    /**
     * Reset all data structures
     */
    resetData() {
        this.adjacencyRules.clear();
        this.tileFrequencies.clear();
        this.patternOccurrences.clear();
        this.stats = {
            mapsProcessed: 0,
            tilesAnalyzed: 0,
            uniquePatterns: 0,
            adjacencyRules: 0
        };
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
    }
}

export default WFCTrainingDataGenerator;