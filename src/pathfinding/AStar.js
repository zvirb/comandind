/**
 * A* Pathfinding Algorithm
 * Finds optimal paths through the navigation grid
 */
export class AStar {
    constructor(navigationGrid) {
        this.grid = navigationGrid;
        this.maxSearchNodes = 1000; // Prevent infinite loops
        this.allowDiagonal = true;
        
        // Path smoothing
        this.smoothPath = true;
        
        // Caching for performance
        this.pathCache = new Map();
        this.cacheSize = 100;
    }
    
    /**
     * Find path from start to goal position (world coordinates)
     */
    findPath(startX, startY, goalX, goalY) {
        // Check cache first
        const cacheKey = `${startX},${startY}-${goalX},${goalY}`;
        if (this.pathCache.has(cacheKey)) {
            return [...this.pathCache.get(cacheKey)];
        }
        
        // Convert to grid coordinates
        const start = this.grid.worldToGrid(startX, startY);
        const goal = this.grid.worldToGrid(goalX, goalY);
        
        // Quick validation
        if (!this.grid.isWalkable(start.x, start.y)) {
            console.warn('Start position is not walkable');
            return [];
        }
        
        if (!this.grid.isWalkable(goal.x, goal.y)) {
            // Find nearest walkable cell to goal
            const nearestGoal = this.findNearestWalkable(goal.x, goal.y);
            if (!nearestGoal) {
                console.warn('No walkable path to goal');
                return [];
            }
            goal.x = nearestGoal.x;
            goal.y = nearestGoal.y;
        }
        
        // Run A* algorithm
        const gridPath = this.astar(start, goal);
        
        if (!gridPath || gridPath.length === 0) {
            return [];
        }
        
        // Convert grid path to world coordinates
        let worldPath = gridPath.map(node => 
            this.grid.gridToWorld(node.x, node.y)
        );
        
        // Smooth the path if enabled
        if (this.smoothPath && worldPath.length > 2) {
            worldPath = this.smoothPathPoints(worldPath);
        }
        
        // Cache the result
        this.addToCache(cacheKey, worldPath);
        
        return worldPath;
    }
    
    /**
     * Core A* algorithm
     */
    astar(start, goal) {
        const openSet = [];
        const closedSet = new Set();
        const cameFrom = new Map();
        
        // Node structure
        const createNode = (x, y, g = 0, h = 0) => ({
            x, y,
            g, // Cost from start
            h, // Heuristic to goal
            f: g + h // Total cost
        });
        
        // Start node
        const startNode = createNode(
            start.x, 
            start.y, 
            0, 
            this.grid.heuristic(start.x, start.y, goal.x, goal.y)
        );
        
        openSet.push(startNode);
        
        let nodesSearched = 0;
        
        while (openSet.length > 0 && nodesSearched < this.maxSearchNodes) {
            nodesSearched++;
            
            // Get node with lowest f score
            let currentIndex = 0;
            for (let i = 1; i < openSet.length; i++) {
                if (openSet[i].f < openSet[currentIndex].f) {
                    currentIndex = i;
                }
            }
            
            const current = openSet.splice(currentIndex, 1)[0];
            
            // Check if we reached the goal
            if (current.x === goal.x && current.y === goal.y) {
                return this.reconstructPath(cameFrom, current);
            }
            
            closedSet.add(`${current.x},${current.y}`);
            
            // Check all neighbors
            const neighbors = this.grid.getNeighbors(current.x, current.y, this.allowDiagonal);
            
            for (const neighbor of neighbors) {
                const neighborKey = `${neighbor.x},${neighbor.y}`;
                
                // Skip if already evaluated
                if (closedSet.has(neighborKey)) {
                    continue;
                }
                
                // Calculate tentative g score
                const movementCost = this.grid.getMovementCost(
                    current.x, current.y, 
                    neighbor.x, neighbor.y
                );
                const tentativeG = current.g + movementCost;
                
                // Check if neighbor is in open set
                let neighborNode = openSet.find(n => n.x === neighbor.x && n.y === neighbor.y);
                
                if (!neighborNode) {
                    // Add new node to open set
                    neighborNode = createNode(
                        neighbor.x,
                        neighbor.y,
                        tentativeG,
                        this.grid.heuristic(neighbor.x, neighbor.y, goal.x, goal.y)
                    );
                    openSet.push(neighborNode);
                    cameFrom.set(neighborKey, current);
                } else if (tentativeG < neighborNode.g) {
                    // Found better path to neighbor
                    neighborNode.g = tentativeG;
                    neighborNode.f = neighborNode.g + neighborNode.h;
                    cameFrom.set(neighborKey, current);
                }
            }
        }
        
        // No path found
        return [];
    }
    
    /**
     * Reconstruct path from A* result
     */
    reconstructPath(cameFrom, current) {
        const path = [current];
        let currentKey = `${current.x},${current.y}`;
        
        while (cameFrom.has(currentKey)) {
            current = cameFrom.get(currentKey);
            currentKey = `${current.x},${current.y}`;
            path.unshift(current);
        }
        
        return path;
    }
    
    /**
     * Find nearest walkable cell to target
     */
    findNearestWalkable(targetX, targetY, maxRadius = 5) {
        // Breadth-first search for nearest walkable
        const queue = [{ x: targetX, y: targetY, dist: 0 }];
        const visited = new Set([`${targetX},${targetY}`]);
        
        while (queue.length > 0) {
            const current = queue.shift();
            
            if (current.dist > maxRadius) {
                break;
            }
            
            if (this.grid.isWalkable(current.x, current.y)) {
                return current;
            }
            
            // Check all neighbors
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    if (dx === 0 && dy === 0) continue;
                    
                    const nx = current.x + dx;
                    const ny = current.y + dy;
                    const key = `${nx},${ny}`;
                    
                    if (!visited.has(key) && this.grid.isValidCell(nx, ny)) {
                        visited.add(key);
                        queue.push({ x: nx, y: ny, dist: current.dist + 1 });
                    }
                }
            }
        }
        
        return null;
    }
    
    /**
     * Smooth path using line-of-sight checks
     */
    smoothPathPoints(path) {
        if (path.length <= 2) return path;
        
        const smoothed = [path[0]];
        let currentIndex = 0;
        
        while (currentIndex < path.length - 1) {
            let furthestVisible = currentIndex + 1;
            
            // Find furthest point we can see directly
            for (let i = currentIndex + 2; i < path.length; i++) {
                if (this.hasLineOfSight(path[currentIndex], path[i])) {
                    furthestVisible = i;
                } else {
                    break;
                }
            }
            
            smoothed.push(path[furthestVisible]);
            currentIndex = furthestVisible;
        }
        
        return smoothed;
    }
    
    /**
     * Check if there's a clear line of sight between two points
     */
    hasLineOfSight(from, to) {
        const fromGrid = this.grid.worldToGrid(from.x, from.y);
        const toGrid = this.grid.worldToGrid(to.x, to.y);
        
        // Bresenham's line algorithm
        let x0 = fromGrid.x;
        let y0 = fromGrid.y;
        const x1 = toGrid.x;
        const y1 = toGrid.y;
        
        const dx = Math.abs(x1 - x0);
        const dy = Math.abs(y1 - y0);
        const sx = x0 < x1 ? 1 : -1;
        const sy = y0 < y1 ? 1 : -1;
        let err = dx - dy;
        
        while (true) {
            if (!this.grid.isWalkable(x0, y0)) {
                return false;
            }
            
            if (x0 === x1 && y0 === y1) {
                break;
            }
            
            const e2 = 2 * err;
            if (e2 > -dy) {
                err -= dy;
                x0 += sx;
            }
            if (e2 < dx) {
                err += dx;
                y0 += sy;
            }
        }
        
        return true;
    }
    
    /**
     * Add path to cache
     */
    addToCache(key, path) {
        // Limit cache size
        if (this.pathCache.size >= this.cacheSize) {
            // Remove oldest entry (first in map)
            const firstKey = this.pathCache.keys().next().value;
            this.pathCache.delete(firstKey);
        }
        
        this.pathCache.set(key, [...path]);
    }
    
    /**
     * Clear path cache
     */
    clearCache() {
        this.pathCache.clear();
    }
    
    /**
     * Get pathfinding statistics
     */
    getStats() {
        return {
            cacheSize: this.pathCache.size,
            maxCacheSize: this.cacheSize,
            allowDiagonal: this.allowDiagonal,
            smoothPath: this.smoothPath
        };
    }
}