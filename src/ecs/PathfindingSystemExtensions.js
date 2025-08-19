/**
 * Performance optimization extensions for PathfindingSystem
 * These methods extend the PathfindingSystem with additional helper functions
 */

// Add these methods to the PathfindingSystem prototype to avoid modifying the original file structure
export function extendPathfindingSystem(PathfindingSystemClass) {
    /**
     * OPTIMIZATION: Generate cache key for path requests
     */
    PathfindingSystemClass.prototype.getPathCacheKey = function(startX, startY, targetX, targetY) {
        // Round to grid cells to increase cache hit rate
        const gridSize = this.navGrid.cellSize;
        const roundedStartX = Math.round(startX / gridSize) * gridSize;
        const roundedStartY = Math.round(startY / gridSize) * gridSize;
        const roundedTargetX = Math.round(targetX / gridSize) * gridSize;
        const roundedTargetY = Math.round(targetY / gridSize) * gridSize;
        
        return `${roundedStartX},${roundedStartY}-${roundedTargetX},${roundedTargetY}`;
    };
    
    /**
     * OPTIMIZATION: Cache path result
     */
    PathfindingSystemClass.prototype.cachePathResult = function(cacheKey, path) {
        if (this.pathCache.size >= this.maxCacheSize) {
            // Remove oldest entries (simple LRU)
            const oldestKey = this.pathCache.keys().next().value;
            this.pathCache.delete(oldestKey);
        }
        
        this.pathCache.set(cacheKey, {
            path: [...path],
            timestamp: performance.now()
        });
    };
    
    /**
     * OPTIMIZATION: Check if path needs recalculation
     */
    PathfindingSystemClass.prototype.shouldRecalculatePath = function(entity) {
        const movement = entity.getComponent('MovementComponent');
        const transform = entity.getComponent('TransformComponent');
        
        // Don't recalculate too frequently
        if (!movement.lastPathUpdate || 
            (performance.now() - movement.lastPathUpdate) < 1000) {
            return false;
        }
        
        // Check if path is blocked by dynamic obstacles
        if (movement.path.length > 0 && movement.pathIndex < movement.path.length) {
            const nextWaypoint = movement.path[movement.pathIndex];
            const nearbyEntities = this.getNearbyEntities(nextWaypoint.x, nextWaypoint.y, 32);
            
            // If other units are blocking the next waypoint
            if (nearbyEntities.length > 2) { // Allow some tolerance
                movement.lastPathUpdate = performance.now();
                return true;
            }
        }
        
        return false;
    };
    
    /**
     * OPTIMIZATION: Invalidate cached path
     */
    PathfindingSystemClass.prototype.invalidatePath = function(entity) {
        const movement = entity.getComponent('MovementComponent');
        const transform = entity.getComponent('TransformComponent');
        
        const cacheKey = this.getPathCacheKey(
            transform.x, transform.y,
            movement.targetX, movement.targetY
        );
        
        this.pathCache.delete(cacheKey);
        movement.path = [];
        movement.pathIndex = 0;
    };
    
    /**
     * OPTIMIZATION: Clean up old cache entries
     */
    PathfindingSystemClass.prototype.cleanupPathCache = function() {
        const now = performance.now();
        const keysToDelete = [];
        
        for (const [key, value] of this.pathCache.entries()) {
            if ((now - value.timestamp) > this.cacheTimeout) {
                keysToDelete.push(key);
            }
        }
        
        keysToDelete.forEach(key => this.pathCache.delete(key));
    };
    
    /**
     * OPTIMIZATION: Update performance statistics
     */
    PathfindingSystemClass.prototype.updatePerformanceStats = function() {
        this.performanceStats.cacheHitRatio = 
            this.cacheHits / Math.max(1, this.cacheHits + this.cacheMisses);
    };
    
    /**
     * OPTIMIZATION: Get performance recommendations
     */
    PathfindingSystemClass.prototype.getPerformanceRecommendations = function() {
        const stats = this.getStats();
        const recommendations = [];
        
        // Cache performance
        if (stats.performance.cacheHitRatio < 0.7) {
            recommendations.push({
                category: 'caching',
                priority: 'high',
                issue: 'Low cache hit ratio',
                suggestion: 'Consider increasing cache timeout or grid rounding precision'
            });
        }
        
        // Queue performance
        if (stats.performance.queueLength > 10) {
            recommendations.push({
                category: 'queueing',
                priority: 'medium',
                issue: 'High path request queue length',
                suggestion: 'Consider increasing maxPathsPerFrame or improving path priority calculation'
            });
        }
        
        // Calculation time
        if (stats.performance.averagePathCalculationTime > 5) {
            recommendations.push({
                category: 'performance',
                priority: 'high',
                issue: 'Long path calculation times',
                suggestion: 'Consider reducing navigation grid resolution or implementing hierarchical pathfinding'
            });
        }
        
        // Spatial query frequency
        if (stats.performance.spatialQueriesPerFrame > 50) {
            recommendations.push({
                category: 'spatial',
                priority: 'medium',
                issue: 'High spatial query frequency',
                suggestion: 'Consider increasing spatial cell size or reducing query frequency'
            });
        }
        
        return recommendations;
    };
    
    /**
     * OPTIMIZATION: Reset performance counters
     */
    PathfindingSystemClass.prototype.resetPerformanceCounters = function() {
        this.cacheHits = 0;
        this.cacheMisses = 0;
        this.performanceStats = {
            pathsCalculatedThisFrame: 0,
            averagePathCalculationTime: 0,
            spatialQueriesPerFrame: 0,
            cacheHitRatio: 0
        };
    };
}