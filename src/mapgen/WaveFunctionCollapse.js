/**
 * Wave Function Collapse Algorithm Implementation
 * 
 * This implementation provides coherent terrain generation using constraint-based
 * tile placement. The WFC algorithm ensures that adjacent tiles follow predefined
 * compatibility rules, creating natural-looking terrain transitions.
 * 
 * Key Features:
 * - Constraint-based tile placement
 * - Support for complex adjacency rules
 * - Backtracking for conflict resolution  
 * - Entropy-based tile selection
 * - Compatible with existing C&C tile definitions
 */

class WaveFunctionCollapse {
    constructor(width, height, tileRules) {
        this.width = width;
        this.height = height;
        this.tileRules = tileRules;
        
        // Wave function: array of possible states for each cell
        this.wave = [];
        
        // Track collapsed (finalized) cells
        this.collapsed = [];
        
        // Stack for backtracking
        this.backtrackStack = [];
        
        // Random seed for deterministic generation
        this.seed = Math.floor(Math.random() * 1000000);
        this.rng = this.createSeededRNG(this.seed);
        
        this.initializeWave();
    }

    /**
     * Initialize the wave function with all possible tiles for each cell
     */
    initializeWave() {
        const allTiles = Object.keys(this.tileRules);
        
        for (let y = 0; y < this.height; y++) {
            this.wave[y] = [];
            this.collapsed[y] = [];
            
            for (let x = 0; x < this.width; x++) {
                // Each cell starts with all possible tiles
                this.wave[y][x] = new Set(allTiles);
                this.collapsed[y][x] = false;
            }
        }
    }

    /**
     * Generate a complete map using Wave Function Collapse
     * Returns a 2D array of collapsed tile IDs
     */
    generate() {
        let attempts = 0;
        const maxAttempts = 1000;
        
        while (!this.isFullyCollapsed() && attempts < maxAttempts) {
            attempts++;
            
            // Find cell with minimum entropy (fewest possible states)
            const cellToCollapse = this.findMinEntropyCell();
            
            if (!cellToCollapse) {
                // No valid cells to collapse - might need backtracking
                if (this.backtrackStack.length > 0) {
                    this.backtrack();
                    continue;
                } else {
                    console.warn('WFC: No solution found, restarting...');
                    this.reset();
                    attempts = 0;
                    continue;
                }
            }
            
            // Save state for potential backtracking
            this.saveState(cellToCollapse);
            
            // Collapse the cell to a random valid state
            this.collapseCell(cellToCollapse.x, cellToCollapse.y);
            
            // Propagate constraints to neighboring cells
            if (!this.propagateConstraints(cellToCollapse.x, cellToCollapse.y)) {
                // Contradiction found - backtrack
                this.backtrack();
            }
        }
        
        if (attempts >= maxAttempts) {
            console.warn('WFC: Max attempts reached, returning partial result');
        }
        
        return this.extractResult();
    }

    /**
     * Find the cell with minimum entropy (excluding fully collapsed cells)
     */
    findMinEntropyCell() {
        let minEntropy = Infinity;
        let candidates = [];
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (!this.collapsed[y][x]) {
                    const entropy = this.wave[y][x].size;
                    
                    if (entropy === 0) {
                        // Contradiction found
                        return null;
                    }
                    
                    if (entropy < minEntropy) {
                        minEntropy = entropy;
                        candidates = [{x, y}];
                    } else if (entropy === minEntropy) {
                        candidates.push({x, y});
                    }
                }
            }
        }
        
        if (candidates.length === 0) return null;
        
        // Randomly select from candidates with equal minimum entropy
        return candidates[Math.floor(this.rng() * candidates.length)];
    }

    /**
     * Collapse a cell to a single tile state
     */
    collapseCell(x, y) {
        if (this.collapsed[y][x]) return;
        
        const possibleTiles = Array.from(this.wave[y][x]);
        if (possibleTiles.length === 0) {
            throw new Error(`WFC: No possible tiles for cell (${x}, ${y})`);
        }
        
        // Apply weighted selection based on tile frequency preferences
        const selectedTile = this.selectWeightedTile(possibleTiles, x, y);
        
        // Collapse to single tile
        this.wave[y][x] = new Set([selectedTile]);
        this.collapsed[y][x] = true;
    }

    /**
     * Select a tile with weighted probability based on terrain preferences
     */
    selectWeightedTile(tiles, x, y) {
        const weights = tiles.map(tile => {
            let weight = this.tileRules[tile].frequency || 1.0;
            
            // Apply positional biases for more natural distribution
            if (tile.startsWith('W')) {
                // Water prefers edges and corners
                const distFromEdge = Math.min(x, y, this.width - 1 - x, this.height - 1 - y);
                weight *= distFromEdge < 5 ? 2.0 : 0.3;
            } else if (tile.startsWith('T')) {
                // Trees prefer clusters and not near edges
                const distFromEdge = Math.min(x, y, this.width - 1 - x, this.height - 1 - y);
                weight *= distFromEdge > 3 ? 1.5 : 0.5;
            } else if (tile.startsWith('S')) {
                // Sand is generally preferred for gameplay
                weight *= 1.2;
            }
            
            return Math.max(weight, 0.1); // Ensure minimum weight
        });
        
        // Weighted random selection
        const totalWeight = weights.reduce((sum, w) => sum + w, 0);
        let random = this.rng() * totalWeight;
        
        for (let i = 0; i < tiles.length; i++) {
            random -= weights[i];
            if (random <= 0) {
                return tiles[i];
            }
        }
        
        // Fallback to last tile
        return tiles[tiles.length - 1];
    }

    /**
     * Propagate constraints after a cell collapse
     */
    propagateConstraints(startX, startY) {
        const propagationQueue = [{x: startX, y: startY}];
        
        while (propagationQueue.length > 0) {
            const {x, y} = propagationQueue.shift();
            
            // Check all four neighboring cells
            const neighbors = [
                {x: x - 1, y, direction: 'left'},
                {x: x + 1, y, direction: 'right'},
                {x, y: y - 1, direction: 'up'},
                {x, y: y + 1, direction: 'down'}
            ];
            
            for (const neighbor of neighbors) {
                if (!this.isValidCell(neighbor.x, neighbor.y)) continue;
                if (this.collapsed[neighbor.y][neighbor.x]) continue;
                
                const validTiles = this.getValidTilesFor(neighbor.x, neighbor.y);
                const currentTiles = this.wave[neighbor.y][neighbor.x];
                
                // Find intersection of valid and current tiles
                const newTiles = new Set([...currentTiles].filter(tile => validTiles.has(tile)));
                
                if (newTiles.size === 0) {
                    // Contradiction found
                    return false;
                }
                
                if (newTiles.size < currentTiles.size) {
                    // State changed - propagate further
                    this.wave[neighbor.y][neighbor.x] = newTiles;
                    propagationQueue.push({x: neighbor.x, y: neighbor.y});
                }
            }
        }
        
        return true;
    }

    /**
     * Get valid tiles for a cell based on all neighbors' constraints
     */
    getValidTilesFor(x, y) {
        const allTiles = Object.keys(this.tileRules);
        let validTiles = new Set(allTiles);
        
        // Check constraints from all neighbors
        const neighbors = [
            {x: x - 1, y, direction: 'left', opposite: 'right'},
            {x: x + 1, y, direction: 'right', opposite: 'left'},
            {x, y: y - 1, direction: 'up', opposite: 'down'},
            {x, y: y + 1, direction: 'down', opposite: 'up'}
        ];
        
        for (const neighbor of neighbors) {
            if (!this.isValidCell(neighbor.x, neighbor.y)) continue;
            
            const neighborTiles = this.wave[neighbor.y][neighbor.x];
            const compatibleTiles = new Set();
            
            // Check which tiles are compatible with any neighbor tile
            for (const neighborTile of neighborTiles) {
                const neighborRule = this.tileRules[neighborTile];
                if (neighborRule && neighborRule.adjacency && neighborRule.adjacency[neighbor.opposite]) {
                    for (const compatibleTile of neighborRule.adjacency[neighbor.opposite]) {
                        compatibleTiles.add(compatibleTile);
                    }
                }
            }
            
            // Intersect with current valid tiles
            if (compatibleTiles.size > 0) {
                validTiles = new Set([...validTiles].filter(tile => compatibleTiles.has(tile)));
            }
        }
        
        return validTiles;
    }

    /**
     * Save current state for backtracking
     */
    saveState(cellToCollapse) {
        const state = {
            x: cellToCollapse.x,
            y: cellToCollapse.y,
            wave: this.wave.map(row => row.map(cell => new Set(cell))),
            collapsed: this.collapsed.map(row => [...row])
        };
        
        this.backtrackStack.push(state);
        
        // Limit stack size to prevent memory issues
        if (this.backtrackStack.length > 50) {
            this.backtrackStack.shift();
        }
    }

    /**
     * Backtrack to previous state
     */
    backtrack() {
        if (this.backtrackStack.length === 0) return false;
        
        const state = this.backtrackStack.pop();
        this.wave = state.wave;
        this.collapsed = state.collapsed;
        
        return true;
    }

    /**
     * Check if all cells are collapsed
     */
    isFullyCollapsed() {
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (!this.collapsed[y][x]) return false;
            }
        }
        return true;
    }

    /**
     * Check if cell coordinates are valid
     */
    isValidCell(x, y) {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    /**
     * Reset the wave function to initial state
     */
    reset() {
        this.backtrackStack = [];
        this.initializeWave();
    }

    /**
     * Extract final result as 2D array of tile IDs
     */
    extractResult() {
        const result = [];
        
        for (let y = 0; y < this.height; y++) {
            result[y] = [];
            for (let x = 0; x < this.width; x++) {
                if (this.collapsed[y][x] && this.wave[y][x].size === 1) {
                    result[y][x] = Array.from(this.wave[y][x])[0];
                } else {
                    // Fallback for uncollapsed cells
                    const possibleTiles = Array.from(this.wave[y][x]);
                    result[y][x] = possibleTiles.length > 0 ? possibleTiles[0] : 'S01';
                }
            }
        }
        
        return result;
    }

    /**
     * Create seeded random number generator
     */
    createSeededRNG(seed) {
        let currentSeed = seed;
        return function() {
            currentSeed = (currentSeed * 9301 + 49297) % 233280;
            return currentSeed / 233280;
        };
    }

    /**
     * Get generation statistics for debugging
     */
    getStats() {
        let collapsedCount = 0;
        let totalEntropy = 0;
        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (this.collapsed[y][x]) collapsedCount++;
                totalEntropy += this.wave[y][x].size;
            }
        }
        
        return {
            totalCells: this.width * this.height,
            collapsedCells: collapsedCount,
            averageEntropy: totalEntropy / (this.width * this.height),
            backtrackStackSize: this.backtrackStack.length,
            seed: this.seed
        };
    }
}

export default WaveFunctionCollapse;