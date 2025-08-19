/**
 * Navigation Grid - Represents the walkable/blocked areas of the game world
 * Used for pathfinding calculations
 */
export class NavigationGrid {
    constructor(worldWidth, worldHeight, cellSize = 32) {
        this.worldWidth = worldWidth;
        this.worldHeight = worldHeight;
        this.cellSize = cellSize;
        
        // Calculate grid dimensions
        this.cols = Math.ceil(worldWidth / cellSize);
        this.rows = Math.ceil(worldHeight / cellSize);
        
        // Initialize grid (0 = walkable, 1 = blocked)
        this.grid = [];
        for (let y = 0; y < this.rows; y++) {
            this.grid[y] = new Array(this.cols).fill(0);
        }
        
        // Dynamic obstacles (units, buildings)
        this.dynamicObstacles = new Map();
        
        // Static obstacles (terrain, walls)
        this.staticObstacles = new Set();
        
        // Debug visualization
        this.debugMode = false;
        this.debugGraphics = null;
    }
    
    /**
     * Convert world coordinates to grid coordinates
     */
    worldToGrid(worldX, worldY) {
        return {
            x: Math.floor(worldX / this.cellSize),
            y: Math.floor(worldY / this.cellSize)
        };
    }
    
    /**
     * Convert grid coordinates to world coordinates (center of cell)
     */
    gridToWorld(gridX, gridY) {
        return {
            x: (gridX + 0.5) * this.cellSize,
            y: (gridY + 0.5) * this.cellSize
        };
    }
    
    /**
     * Check if grid coordinates are valid
     */
    isValidCell(x, y) {
        return x >= 0 && x < this.cols && y >= 0 && y < this.rows;
    }
    
    /**
     * Check if a cell is walkable
     */
    isWalkable(x, y) {
        if (!this.isValidCell(x, y)) return false;
        return this.grid[y][x] === 0;
    }
    
    /**
     * Set cell walkability
     */
    setWalkable(x, y, walkable) {
        if (this.isValidCell(x, y)) {
            this.grid[y][x] = walkable ? 0 : 1;
        }
    }
    
    /**
     * Add a static obstacle (permanent terrain)
     */
    addStaticObstacle(worldX, worldY, width, height) {
        const startGrid = this.worldToGrid(worldX - width/2, worldY - height/2);
        const endGrid = this.worldToGrid(worldX + width/2, worldY + height/2);
        
        for (let y = startGrid.y; y <= endGrid.y; y++) {
            for (let x = startGrid.x; x <= endGrid.x; x++) {
                if (this.isValidCell(x, y)) {
                    this.setWalkable(x, y, false);
                    this.staticObstacles.add(`${x},${y}`);
                }
            }
        }
    }
    
    /**
     * Add a dynamic obstacle (unit, building)
     */
    addDynamicObstacle(entityId, worldX, worldY, radius) {
        const gridPos = this.worldToGrid(worldX, worldY);
        const cellRadius = Math.ceil(radius / this.cellSize);
        
        const cells = [];
        for (let dy = -cellRadius; dy <= cellRadius; dy++) {
            for (let dx = -cellRadius; dx <= cellRadius; dx++) {
                const gx = gridPos.x + dx;
                const gy = gridPos.y + dy;
                
                if (this.isValidCell(gx, gy)) {
                    // Check if within circular radius
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist <= cellRadius) {
                        cells.push({ x: gx, y: gy });
                        this.setWalkable(gx, gy, false);
                    }
                }
            }
        }
        
        // Store for later removal
        this.dynamicObstacles.set(entityId, cells);
    }
    
    /**
     * Remove a dynamic obstacle
     */
    removeDynamicObstacle(entityId) {
        const cells = this.dynamicObstacles.get(entityId);
        if (!cells) return;
        
        // Mark cells as walkable again (unless they're static obstacles)
        for (const cell of cells) {
            if (!this.staticObstacles.has(`${cell.x},${cell.y}`)) {
                this.setWalkable(cell.x, cell.y, true);
            }
        }
        
        this.dynamicObstacles.delete(entityId);
    }
    
    /**
     * Update dynamic obstacle position
     */
    updateDynamicObstacle(entityId, newWorldX, newWorldY, radius) {
        this.removeDynamicObstacle(entityId);
        this.addDynamicObstacle(entityId, newWorldX, newWorldY, radius);
    }
    
    /**
     * Get neighbors of a cell (8-directional)
     */
    getNeighbors(x, y, allowDiagonal = true) {
        const neighbors = [];
        
        // Cardinal directions
        const cardinals = [
            { x: x - 1, y: y },     // West
            { x: x + 1, y: y },     // East
            { x: x, y: y - 1 },     // North
            { x: x, y: y + 1 }      // South
        ];
        
        for (const pos of cardinals) {
            if (this.isWalkable(pos.x, pos.y)) {
                neighbors.push(pos);
            }
        }
        
        // Diagonal directions
        if (allowDiagonal) {
            const diagonals = [
                { x: x - 1, y: y - 1 }, // NW
                { x: x + 1, y: y - 1 }, // NE
                { x: x - 1, y: y + 1 }, // SW
                { x: x + 1, y: y + 1 }  // SE
            ];
            
            for (const pos of diagonals) {
                // Check if diagonal is walkable and both adjacent cells are walkable
                // (prevents cutting corners around obstacles)
                if (this.isWalkable(pos.x, pos.y)) {
                    const horizontalClear = this.isWalkable(pos.x, y);
                    const verticalClear = this.isWalkable(x, pos.y);
                    
                    if (horizontalClear && verticalClear) {
                        neighbors.push(pos);
                    }
                }
            }
        }
        
        return neighbors;
    }
    
    /**
     * Get cost to move between two adjacent cells
     */
    getMovementCost(fromX, fromY, toX, toY) {
        // Diagonal movement costs more (sqrt(2) ≈ 1.414)
        const dx = Math.abs(toX - fromX);
        const dy = Math.abs(toY - fromY);
        
        if (dx === 1 && dy === 1) {
            return 1.414; // Diagonal
        }
        return 1.0; // Cardinal
    }
    
    /**
     * Calculate heuristic distance (for A*)
     */
    heuristic(x1, y1, x2, y2) {
        // Using octile distance (diagonal distance for 8-directional movement)
        const dx = Math.abs(x2 - x1);
        const dy = Math.abs(y2 - y1);
        const D = 1;
        const D2 = 1.414;
        
        return D * (dx + dy) + (D2 - 2 * D) * Math.min(dx, dy);
    }
    
    /**
     * Create debug visualization
     */
    createDebugVisualization(pixiGraphics) {
        this.debugGraphics = pixiGraphics;
        this.debugMode = true;
    }
    
    /**
     * Update debug visualization
     */
    updateDebugVisualization() {
        if (!this.debugMode || !this.debugGraphics) return;
        
        this.debugGraphics.clear();
        
        // Draw grid
        for (let y = 0; y < this.rows; y++) {
            for (let x = 0; x < this.cols; x++) {
                const worldPos = this.gridToWorld(x, y);
                const isBlocked = !this.isWalkable(x, y);
                
                if (isBlocked) {
                    // Draw blocked cells
                    this.debugGraphics.beginFill(0xff0000, 0.3);
                    this.debugGraphics.drawRect(
                        worldPos.x - this.cellSize/2,
                        worldPos.y - this.cellSize/2,
                        this.cellSize,
                        this.cellSize
                    );
                    this.debugGraphics.endFill();
                } else {
                    // Draw walkable cell borders
                    this.debugGraphics.lineStyle(1, 0x00ff00, 0.1);
                    this.debugGraphics.drawRect(
                        worldPos.x - this.cellSize/2,
                        worldPos.y - this.cellSize/2,
                        this.cellSize,
                        this.cellSize
                    );
                }
            }
        }
    }
    
    /**
     * Clear all obstacles
     */
    clear() {
        for (let y = 0; y < this.rows; y++) {
            for (let x = 0; x < this.cols; x++) {
                this.grid[y][x] = 0;
            }
        }
        this.dynamicObstacles.clear();
        this.staticObstacles.clear();
    }
    
    /**
     * Get grid statistics
     */
    getStats() {
        let walkable = 0;
        let blocked = 0;
        
        for (let y = 0; y < this.rows; y++) {
            for (let x = 0; x < this.cols; x++) {
                if (this.isWalkable(x, y)) {
                    walkable++;
                } else {
                    blocked++;
                }
            }
        }
        
        return {
            totalCells: this.cols * this.rows,
            walkableCells: walkable,
            blockedCells: blocked,
            dynamicObstacles: this.dynamicObstacles.size,
            staticObstacles: this.staticObstacles.size
        };
    }
}