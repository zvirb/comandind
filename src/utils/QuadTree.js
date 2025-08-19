/**
 * QuadTree - Spatial partitioning data structure for fast 2D spatial queries
 * Provides O(log n) entity lookup instead of O(n) linear search
 * Optimized for RTS games with 200+ entities
 */
export class QuadTree {
    constructor(bounds, maxEntities = 10, maxLevels = 5, level = 0) {
        this.level = level;
        this.maxEntities = maxEntities;
        this.maxLevels = maxLevels;
        this.bounds = bounds; // { x, y, width, height }
        this.entities = [];
        this.nodes = []; // 4 child nodes: NE, NW, SW, SE
        
        // Performance tracking
        this.queryCount = 0;
        this.insertCount = 0;
        this.depth = 0;
    }
    
    /**
     * Clear the quadtree
     */
    clear() {
        this.entities = [];
        
        for (let i = 0; i < this.nodes.length; i++) {
            if (this.nodes[i]) {
                this.nodes[i].clear();
            }
        }
        
        this.nodes = [];
    }
    
    /**
     * Split the node into 4 quadrants
     */
    split() {
        const subWidth = this.bounds.width / 2;
        const subHeight = this.bounds.height / 2;
        const x = this.bounds.x;
        const y = this.bounds.y;
        
        // NE (0)
        this.nodes[0] = new QuadTree(
            { x: x + subWidth, y: y, width: subWidth, height: subHeight },
            this.maxEntities,
            this.maxLevels,
            this.level + 1
        );
        
        // NW (1)
        this.nodes[1] = new QuadTree(
            { x: x, y: y, width: subWidth, height: subHeight },
            this.maxEntities,
            this.maxLevels,
            this.level + 1
        );
        
        // SW (2)
        this.nodes[2] = new QuadTree(
            { x: x, y: y + subHeight, width: subWidth, height: subHeight },
            this.maxEntities,
            this.maxLevels,
            this.level + 1
        );
        
        // SE (3)
        this.nodes[3] = new QuadTree(
            { x: x + subWidth, y: y + subHeight, width: subWidth, height: subHeight },
            this.maxEntities,
            this.maxLevels,
            this.level + 1
        );
    }
    
    /**
     * Determine which node the entity belongs to
     * Returns -1 if entity doesn't completely fit within a child node
     */
    getIndex(entity) {
        let index = -1;
        const verticalMidpoint = this.bounds.x + (this.bounds.width / 2);
        const horizontalMidpoint = this.bounds.y + (this.bounds.height / 2);
        
        // Get entity bounds
        const entityBounds = this.getEntityBounds(entity);
        
        // Entity can completely fit within the top quadrants
        const topQuadrant = (entityBounds.y < horizontalMidpoint && 
                           entityBounds.y + entityBounds.height < horizontalMidpoint);
        
        // Entity can completely fit within the bottom quadrants
        const bottomQuadrant = (entityBounds.y > horizontalMidpoint);
        
        // Entity can completely fit within the left quadrants
        if (entityBounds.x < verticalMidpoint && 
            entityBounds.x + entityBounds.width < verticalMidpoint) {
            if (topQuadrant) {
                index = 1; // NW
            } else if (bottomQuadrant) {
                index = 2; // SW
            }
        }
        // Entity can completely fit within the right quadrants
        else if (entityBounds.x > verticalMidpoint) {
            if (topQuadrant) {
                index = 0; // NE
            } else if (bottomQuadrant) {
                index = 3; // SE
            }
        }
        
        return index;
    }
    
    /**
     * Get entity bounds for spatial calculations
     */
    getEntityBounds(entity) {
        // Support different entity formats
        if (entity.transform) {
            return {
                x: entity.transform.x,
                y: entity.transform.y,
                width: entity.bounds?.width || 16,
                height: entity.bounds?.height || 16
            };
        }
        
        // ECS component format
        if (entity.getComponent) {
            const transform = entity.getComponent('TransformComponent');
            const selectable = entity.getComponent('SelectableComponent');
            
            if (transform) {
                const radius = selectable?.selectableRadius || 16;
                return {
                    x: transform.x - radius,
                    y: transform.y - radius,
                    width: radius * 2,
                    height: radius * 2
                };
            }
        }
        
        // Fallback: direct position
        return {
            x: entity.x || 0,
            y: entity.y || 0,
            width: entity.width || 16,
            height: entity.height || 16
        };
    }
    
    /**
     * Insert an entity into the quadtree
     */
    insert(entity) {
        this.insertCount++;
        
        // If we have child nodes, try to insert into them
        if (this.nodes.length > 0) {
            const index = this.getIndex(entity);
            
            if (index !== -1) {
                this.nodes[index].insert(entity);
                return;
            }
        }
        
        // Add entity to this node
        this.entities.push(entity);
        
        // If we exceed capacity and can still split, subdivide
        if (this.entities.length > this.maxEntities && 
            this.level < this.maxLevels) {
            
            // Split if we haven't already
            if (this.nodes.length === 0) {
                this.split();
            }
            
            // Move entities to child nodes
            let i = 0;
            while (i < this.entities.length) {
                const index = this.getIndex(this.entities[i]);
                if (index !== -1) {
                    const entity = this.entities.splice(i, 1)[0];
                    this.nodes[index].insert(entity);
                } else {
                    i++;
                }
            }
        }
    }
    
    /**
     * Retrieve all entities that could collide with the given bounds
     */
    retrieve(returnEntities, bounds) {
        this.queryCount++;
        
        // Get index of where bounds would fit
        const index = this.getIndexForBounds(bounds);
        
        // If we have child nodes, retrieve from the appropriate one
        if (this.nodes.length > 0) {
            if (index !== -1) {
                this.nodes[index].retrieve(returnEntities, bounds);
            } else {
                // Entity spans multiple quadrants, check all children
                for (let i = 0; i < this.nodes.length; i++) {
                    this.nodes[i].retrieve(returnEntities, bounds);
                }
            }
        }
        
        // Add entities from this node
        for (const entity of this.entities) {
            if (this.boundsIntersect(bounds, this.getEntityBounds(entity))) {
                returnEntities.push(entity);
            }
        }
        
        return returnEntities;
    }
    
    /**
     * Get index for bounds (similar to getIndex but for arbitrary bounds)
     */
    getIndexForBounds(bounds) {
        let index = -1;
        const verticalMidpoint = this.bounds.x + (this.bounds.width / 2);
        const horizontalMidpoint = this.bounds.y + (this.bounds.height / 2);
        
        // Check if bounds fit in top or bottom
        const topQuadrant = (bounds.y < horizontalMidpoint && 
                           bounds.y + bounds.height < horizontalMidpoint);
        const bottomQuadrant = (bounds.y > horizontalMidpoint);
        
        // Check if bounds fit in left or right
        if (bounds.x < verticalMidpoint && 
            bounds.x + bounds.width < verticalMidpoint) {
            if (topQuadrant) {
                index = 1; // NW
            } else if (bottomQuadrant) {
                index = 2; // SW
            }
        } else if (bounds.x > verticalMidpoint) {
            if (topQuadrant) {
                index = 0; // NE
            } else if (bottomQuadrant) {
                index = 3; // SE
            }
        }
        
        return index;
    }
    
    /**
     * Check if two bounds intersect
     */
    boundsIntersect(bounds1, bounds2) {
        return !(bounds1.x > bounds2.x + bounds2.width ||
                bounds1.x + bounds1.width < bounds2.x ||
                bounds1.y > bounds2.y + bounds2.height ||
                bounds1.y + bounds1.height < bounds2.y);
    }
    
    /**
     * Query entities within a radius from a point
     */
    queryRadius(centerX, centerY, radius) {
        const bounds = {
            x: centerX - radius,
            y: centerY - radius,
            width: radius * 2,
            height: radius * 2
        };
        
        const potentialEntities = [];
        this.retrieve(potentialEntities, bounds);
        
        // Filter by actual distance
        const result = [];
        for (const entity of potentialEntities) {
            const entityBounds = this.getEntityBounds(entity);
            const entityCenterX = entityBounds.x + entityBounds.width / 2;
            const entityCenterY = entityBounds.y + entityBounds.height / 2;
            
            const distance = Math.sqrt(
                Math.pow(entityCenterX - centerX, 2) + 
                Math.pow(entityCenterY - centerY, 2)
            );
            
            if (distance <= radius) {
                result.push(entity);
            }
        }
        
        return result;
    }
    
    /**
     * Query entities within a rectangular area
     */
    queryRect(x, y, width, height) {
        const bounds = { x, y, width, height };
        const result = [];
        this.retrieve(result, bounds);
        return result;
    }
    
    /**
     * Find the nearest entity to a point
     */
    findNearest(x, y, filter = null) {
        // Start with a small radius and expand if needed
        let radius = 32;
        let maxRadius = Math.max(this.bounds.width, this.bounds.height);
        
        while (radius <= maxRadius) {
            const entities = this.queryRadius(x, y, radius);
            
            if (entities.length > 0) {
                let nearest = null;
                let nearestDistance = Infinity;
                
                for (const entity of entities) {
                    if (filter && !filter(entity)) continue;
                    
                    const entityBounds = this.getEntityBounds(entity);
                    const entityCenterX = entityBounds.x + entityBounds.width / 2;
                    const entityCenterY = entityBounds.y + entityBounds.height / 2;
                    
                    const distance = Math.sqrt(
                        Math.pow(entityCenterX - x, 2) + 
                        Math.pow(entityCenterY - y, 2)
                    );
                    
                    if (distance < nearestDistance) {
                        nearestDistance = distance;
                        nearest = entity;
                    }
                }
                
                if (nearest) return nearest;
            }
            
            radius *= 2; // Double the search radius
        }
        
        return null;
    }
    
    /**
     * Remove an entity from the quadtree
     */
    remove(entity) {
        // Remove from this node
        const index = this.entities.indexOf(entity);
        if (index !== -1) {
            this.entities.splice(index, 1);
            return true;
        }
        
        // Try to remove from child nodes
        if (this.nodes.length > 0) {
            const nodeIndex = this.getIndex(entity);
            if (nodeIndex !== -1) {
                return this.nodes[nodeIndex].remove(entity);
            } else {
                // Try all child nodes
                for (let i = 0; i < this.nodes.length; i++) {
                    if (this.nodes[i].remove(entity)) {
                        return true;
                    }
                }
            }
        }
        
        return false;
    }
    
    /**
     * Get total entity count in tree
     */
    getTotalEntities() {
        let total = this.entities.length;
        
        for (const node of this.nodes) {
            total += node.getTotalEntities();
        }
        
        return total;
    }
    
    /**
     * Get maximum depth of the tree
     */
    getMaxDepth() {
        if (this.nodes.length === 0) {
            return this.level;
        }
        
        let maxDepth = this.level;
        for (const node of this.nodes) {
            maxDepth = Math.max(maxDepth, node.getMaxDepth());
        }
        
        return maxDepth;
    }
    
    /**
     * Get performance statistics
     */
    getStats() {
        return {
            level: this.level,
            entityCount: this.entities.length,
            totalEntities: this.getTotalEntities(),
            maxDepth: this.getMaxDepth(),
            queryCount: this.queryCount,
            insertCount: this.insertCount,
            hasChildren: this.nodes.length > 0,
            bounds: { ...this.bounds }
        };
    }
    
    /**
     * Reset performance counters
     */
    resetStats() {
        this.queryCount = 0;
        this.insertCount = 0;
        
        for (const node of this.nodes) {
            node.resetStats();
        }
    }
    
    /**
     * Rebuild the entire tree (useful for dynamic entities)
     */
    rebuild(entities) {
        this.clear();
        
        for (const entity of entities) {
            this.insert(entity);
        }
    }
}

/**
 * SpatialHashGrid - Alternative spatial partitioning for very dense areas
 * Uses fixed-size grid cells for consistent O(1) insertion/removal
 */
export class SpatialHashGrid {
    constructor(worldWidth, worldHeight, cellSize = 64) {
        this.cellSize = cellSize;
        this.cols = Math.ceil(worldWidth / cellSize);
        this.rows = Math.ceil(worldHeight / cellSize);
        this.grid = new Map();
        
        // Performance tracking
        this.queryCount = 0;
        this.insertCount = 0;
    }
    
    /**
     * Get cell key for position
     */
    getCellKey(x, y) {
        const cellX = Math.floor(x / this.cellSize);
        const cellY = Math.floor(y / this.cellSize);
        return `${cellX},${cellY}`;
    }
    
    /**
     * Insert entity into grid
     */
    insert(entity) {
        this.insertCount++;
        
        const bounds = this.getEntityBounds(entity);
        const keys = this.getCellKeysForBounds(bounds);
        
        entity._spatialKeys = keys;
        
        for (const key of keys) {
            if (!this.grid.has(key)) {
                this.grid.set(key, new Set());
            }
            this.grid.get(key).add(entity);
        }
    }
    
    /**
     * Remove entity from grid
     */
    remove(entity) {
        if (!entity._spatialKeys) return false;
        
        for (const key of entity._spatialKeys) {
            const cell = this.grid.get(key);
            if (cell) {
                cell.delete(entity);
                if (cell.size === 0) {
                    this.grid.delete(key);
                }
            }
        }
        
        delete entity._spatialKeys;
        return true;
    }
    
    /**
     * Get entity bounds (same as QuadTree)
     */
    getEntityBounds(entity) {
        if (entity.transform) {
            return {
                x: entity.transform.x,
                y: entity.transform.y,
                width: entity.bounds?.width || 16,
                height: entity.bounds?.height || 16
            };
        }
        
        if (entity.getComponent) {
            const transform = entity.getComponent('TransformComponent');
            const selectable = entity.getComponent('SelectableComponent');
            
            if (transform) {
                const radius = selectable?.selectableRadius || 16;
                return {
                    x: transform.x - radius,
                    y: transform.y - radius,
                    width: radius * 2,
                    height: radius * 2
                };
            }
        }
        
        return {
            x: entity.x || 0,
            y: entity.y || 0,
            width: entity.width || 16,
            height: entity.height || 16
        };
    }
    
    /**
     * Get all cell keys that bounds intersect
     */
    getCellKeysForBounds(bounds) {
        const keys = [];
        const startX = Math.floor(bounds.x / this.cellSize);
        const endX = Math.floor((bounds.x + bounds.width) / this.cellSize);
        const startY = Math.floor(bounds.y / this.cellSize);
        const endY = Math.floor((bounds.y + bounds.height) / this.cellSize);
        
        for (let y = startY; y <= endY; y++) {
            for (let x = startX; x <= endX; x++) {
                keys.push(`${x},${y}`);
            }
        }
        
        return keys;
    }
    
    /**
     * Query entities in radius
     */
    queryRadius(centerX, centerY, radius) {
        this.queryCount++;
        
        const bounds = {
            x: centerX - radius,
            y: centerY - radius,
            width: radius * 2,
            height: radius * 2
        };
        
        const keys = this.getCellKeysForBounds(bounds);
        const entities = new Set();
        
        for (const key of keys) {
            const cell = this.grid.get(key);
            if (cell) {
                for (const entity of cell) {
                    entities.add(entity);
                }
            }
        }
        
        // Filter by actual distance
        const result = [];
        for (const entity of entities) {
            const entityBounds = this.getEntityBounds(entity);
            const entityCenterX = entityBounds.x + entityBounds.width / 2;
            const entityCenterY = entityBounds.y + entityBounds.height / 2;
            
            const distance = Math.sqrt(
                Math.pow(entityCenterX - centerX, 2) + 
                Math.pow(entityCenterY - centerY, 2)
            );
            
            if (distance <= radius) {
                result.push(entity);
            }
        }
        
        return result;
    }
    
    /**
     * Query entities in rectangle
     */
    queryRect(x, y, width, height) {
        this.queryCount++;
        
        const bounds = { x, y, width, height };
        const keys = this.getCellKeysForBounds(bounds);
        const entities = new Set();
        
        for (const key of keys) {
            const cell = this.grid.get(key);
            if (cell) {
                for (const entity of cell) {
                    entities.add(entity);
                }
            }
        }
        
        return Array.from(entities);
    }
    
    /**
     * Get performance statistics
     */
    getStats() {
        return {
            cellSize: this.cellSize,
            gridSize: `${this.cols}x${this.rows}`,
            activeCells: this.grid.size,
            totalEntities: Array.from(this.grid.values()).reduce((sum, cell) => sum + cell.size, 0),
            queryCount: this.queryCount,
            insertCount: this.insertCount
        };
    }
    
    /**
     * Clear the grid
     */
    clear() {
        this.grid.clear();
    }
    
    /**
     * Reset performance counters
     */
    resetStats() {
        this.queryCount = 0;
        this.insertCount = 0;
    }
}