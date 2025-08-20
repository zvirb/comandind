import * as PIXI from "pixi.js";
import { System } from "./System.js";
import { MovementComponent, TransformComponent, SelectableComponent, UnitComponent, BuildingComponent, VelocityComponent } from "./Component.js";
import { NavigationGrid } from "../pathfinding/NavigationGrid.js";
import { AStar } from "../pathfinding/AStar.js";
import { extendPathfindingSystem } from "./PathfindingSystemExtensions.js";

/**
 * Pathfinding System - Manages pathfinding and movement for all entities
 */
export class PathfindingSystem extends System {
    constructor(world, worldWidth = 2000, worldHeight = 2000) {
        super(world);
        this.priority = 3; // Run before movement system
        this.requiredComponents = [MovementComponent, TransformComponent];
        
        // Create navigation grid
        this.navGrid = new NavigationGrid(worldWidth, worldHeight, 16);
        
        // Create pathfinder
        this.pathfinder = new AStar(this.navGrid);
        
        // Track obstacles
        this.obstacles = new Map();
        
        // PERFORMANCE OPTIMIZATION 1: Enhanced Path Caching
        this.pathCache = new Map();
        this.cacheHits = 0;
        this.cacheMisses = 0;
        this.maxCacheSize = 500;
        this.cacheTimeout = 5000; // 5 seconds
        
        // PERFORMANCE OPTIMIZATION 2: Path Request Queue with Priority
        this.pathRequestQueue = [];
        this.maxPathsPerFrame = 3; // Limit pathfinding calculations per frame
        this.processingRequests = new Set();
        
        // PERFORMANCE OPTIMIZATION 3: Time-Slicing
        this.timeSliceLimit = 8; // 8ms max per frame for pathfinding
        this.currentTimeSlice = 0;
        
        // PERFORMANCE OPTIMIZATION 4: Spatial Partitioning
        this.spatialGrid = new Map();
        this.spatialCellSize = 128; // Larger cells for spatial queries
        this.spatialCols = Math.ceil(worldWidth / this.spatialCellSize);
        this.spatialRows = Math.ceil(worldHeight / this.spatialCellSize);
        
        // Performance tracking
        this.performanceStats = {
            pathsCalculatedThisFrame: 0,
            averagePathCalculationTime: 0,
            spatialQueriesPerFrame: 0,
            cacheHitRatio: 0
        };
        
        // Debug visualization
        this.debugMode = false;
        this.debugGraphics = null;
        this.pathVisuals = new Map();
        
        // Group movement
        this.groupMoveFormation = "box"; // box, line, wedge
        this.groupSpacing = 40;
        
        // Initialize spatial grid
        this.initializeSpatialGrid();
    }
    
    /**
     * Initialize debug visualization
     */
    enableDebugMode(pixiStage) {
        this.debugMode = true;
        
        // Create debug graphics layers
        this.debugGraphics = new PIXI.Container();
        this.debugGraphics.name = "pathfinding-debug";
        
        // Grid visualization
        this.gridGraphics = new PIXI.Graphics();
        this.debugGraphics.addChild(this.gridGraphics);
        
        // Path visualization
        this.pathGraphics = new PIXI.Graphics();
        this.debugGraphics.addChild(this.pathGraphics);
        
        pixiStage.addChild(this.debugGraphics);
        
        // Setup navigation grid debug
        this.navGrid.createDebugVisualization(this.gridGraphics);
        this.updateDebugGrid();
    }
    
    /**
     * Called when entity is added to system
     */
    onEntityAdded(entity) {
        // Register buildings as static obstacles
        if (entity.hasComponent(BuildingComponent)) {
            const transform = entity.getComponent(TransformComponent);
            const building = entity.getComponent(BuildingComponent);
            
            // Add to navigation grid as obstacle
            const width = 64; // Default building size
            const height = 64;
            this.navGrid.addStaticObstacle(transform.x, transform.y, width, height);
            this.obstacles.set(entity.id, { type: "static", entity });
        }
        // Register units as dynamic obstacles
        else if (entity.hasComponent(UnitComponent)) {
            const transform = entity.getComponent(TransformComponent);
            const radius = 8; // Unit collision radius
            
            this.navGrid.addDynamicObstacle(entity.id, transform.x, transform.y, radius);
            this.obstacles.set(entity.id, { type: "dynamic", entity });
        }
    }
    
    /**
     * Called when entity is removed from system
     */
    onEntityRemoved(entity) {
        // Remove from navigation grid
        if (this.obstacles.has(entity.id)) {
            const obstacle = this.obstacles.get(entity.id);
            
            if (obstacle.type === "dynamic") {
                this.navGrid.removeDynamicObstacle(entity.id);
            }
            // Static obstacles remain (buildings don't move)
            
            this.obstacles.delete(entity.id);
        }
        
        // OPTIMIZATION: Clean up spatial grid
        if (entity._spatialKey) {
            const cell = this.spatialGrid.get(entity._spatialKey);
            if (cell) {
                cell.delete(entity);
            }
        }
        
        // OPTIMIZATION: Remove from processing requests
        this.processingRequests.delete(entity.id);
        
        // Clean up path visuals
        if (this.pathVisuals.has(entity.id)) {
            const visual = this.pathVisuals.get(entity.id);
            if (visual.parent) {
                visual.parent.removeChild(visual);
            }
            this.pathVisuals.delete(entity.id);
        }
    }
    
    /**
     * Update pathfinding for all entities with performance optimizations
     */
    update(deltaTime) {
        const frameStartTime = performance.now();
        this.performanceStats.pathsCalculatedThisFrame = 0;
        this.performanceStats.spatialQueriesPerFrame = 0;
        
        // OPTIMIZATION: Process path requests with time-slicing
        this.processPathRequestQueue(frameStartTime);
        
        // Update entities and handle movement
        for (const entity of this.entities) {
            const movement = entity.getComponent(MovementComponent);
            const transform = entity.getComponent(TransformComponent);
            
            // Update spatial partitioning
            this.updateEntitySpatialPosition(entity);
            
            // Check if entity needs a new path
            if (movement.isMoving && movement.targetX !== null && movement.targetY !== null) {
                // Use cached path or queue new request if no path exists
                if (movement.path.length === 0) {
                    this.requestPath(entity);
                }
                
                // Follow the path
                if (movement.path.length > 0) {
                    this.followPath(entity, deltaTime);
                    
                    // OPTIMIZATION: Check if path needs recalculation due to obstacles
                    if (this.shouldRecalculatePath(entity)) {
                        this.invalidatePath(entity);
                        this.requestPath(entity);
                    }
                }
            }
            
            // Update dynamic obstacle position (less frequently)
            if (entity.hasComponent(UnitComponent) && Math.random() < 0.1) { // 10% chance per frame
                this.navGrid.updateDynamicObstacle(entity.id, transform.x, transform.y, 8);
            }
        }
        
        // Clean up old cache entries periodically
        if (Math.random() < 0.01) { // 1% chance per frame
            this.cleanupPathCache();
        }
        
        // Update performance statistics
        this.updatePerformanceStats();
        
        // Update debug visualization
        if (this.debugMode) {
            this.updateDebugVisualization();
        }
    }
    
    /**
     * OPTIMIZATION: Initialize spatial grid for fast entity queries
     */
    initializeSpatialGrid() {
        for (let y = 0; y < this.spatialRows; y++) {
            for (let x = 0; x < this.spatialCols; x++) {
                this.spatialGrid.set(`${x},${y}`, new Set());
            }
        }
    }
    
    /**
     * OPTIMIZATION: Update entity position in spatial grid
     */
    updateEntitySpatialPosition(entity) {
        const transform = entity.getComponent(TransformComponent);
        const cellX = Math.floor(transform.x / this.spatialCellSize);
        const cellY = Math.floor(transform.y / this.spatialCellSize);
        const newKey = `${cellX},${cellY}`;
        
        // Remove from old cell if exists
        if (entity._spatialKey && entity._spatialKey !== newKey) {
            const oldCell = this.spatialGrid.get(entity._spatialKey);
            if (oldCell) {
                oldCell.delete(entity);
            }
        }
        
        // Add to new cell
        if (cellX >= 0 && cellX < this.spatialCols && cellY >= 0 && cellY < this.spatialRows) {
            const cell = this.spatialGrid.get(newKey);
            if (cell) {
                cell.add(entity);
                entity._spatialKey = newKey;
            }
        }
    }
    
    /**
     * OPTIMIZATION: Fast spatial query for nearby entities
     */
    getNearbyEntities(centerX, centerY, radius) {
        this.performanceStats.spatialQueriesPerFrame++;
        
        const result = [];
        const cellRadius = Math.ceil(radius / this.spatialCellSize);
        const centerCellX = Math.floor(centerX / this.spatialCellSize);
        const centerCellY = Math.floor(centerY / this.spatialCellSize);
        
        for (let dy = -cellRadius; dy <= cellRadius; dy++) {
            for (let dx = -cellRadius; dx <= cellRadius; dx++) {
                const cellX = centerCellX + dx;
                const cellY = centerCellY + dy;
                
                if (cellX >= 0 && cellX < this.spatialCols && cellY >= 0 && cellY < this.spatialRows) {
                    const cell = this.spatialGrid.get(`${cellX},${cellY}`);
                    if (cell) {
                        for (const entity of cell) {
                            const transform = entity.getComponent(TransformComponent);
                            const distance = Math.sqrt(
                                Math.pow(transform.x - centerX, 2) + 
                                Math.pow(transform.y - centerY, 2)
                            );
                            if (distance <= radius) {
                                result.push(entity);
                            }
                        }
                    }
                }
            }
        }
        
        return result;
    }
    
    /**
     * Calculate path for an entity (legacy method - kept for compatibility)
     */
    calculatePath(entity) {
        // Redirect to optimized request system
        this.requestPath(entity);
    }
    
    /**
     * Make entity follow its path
     */
    followPath(entity, deltaTime) {
        const movement = entity.getComponent(MovementComponent);
        const transform = entity.getComponent(TransformComponent);
        
        if (movement.pathIndex >= movement.path.length) {
            // Reached end of path
            movement.stop();
            return;
        }
        
        // Get current waypoint
        const waypoint = movement.path[movement.pathIndex];
        
        // Calculate direction to waypoint
        const dx = waypoint.x - transform.x;
        const dy = waypoint.y - transform.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // Check if reached waypoint
        if (distance <= movement.arrivalDistance) {
            movement.pathIndex++;
            
            // Check if this was the last waypoint
            if (movement.pathIndex >= movement.path.length) {
                movement.stop();
            }
            return;
        }
        
        // Move towards waypoint
        const moveDistance = movement.speed * deltaTime;
        
        if (distance > 0) {
            // Normalize direction and apply speed
            const vx = (dx / distance) * movement.speed;
            const vy = (dy / distance) * movement.speed;
            
            // Update velocity component if entity has one
            const velocity = entity.getComponent(VelocityComponent);
            if (velocity) {
                velocity.vx = vx;
                velocity.vy = vy;
            } else {
                // Direct position update
                transform.x += (dx / distance) * moveDistance;
                transform.y += (dy / distance) * moveDistance;
            }
            
            // Update rotation to face movement direction
            if (entity.hasComponent(UnitComponent)) {
                const unit = entity.getComponent(UnitComponent);
                unit.facing = Math.atan2(dy, dx);
                transform.rotation = unit.facing;
            }
        }
    }
    
    /**
     * Calculate group movement formation
     */
    calculateGroupMovement(entities, targetX, targetY) {
        if (entities.length === 0) return;
        
        // Calculate center of group
        let centerX = 0, centerY = 0;
        for (const entity of entities) {
            const transform = entity.getComponent(TransformComponent);
            centerX += transform.x;
            centerY += transform.y;
        }
        centerX /= entities.length;
        centerY /= entities.length;
        
        // Calculate formation positions
        const positions = this.getFormationPositions(
            entities.length, 
            targetX, 
            targetY,
            this.groupMoveFormation
        );
        
        // Assign positions to entities
        entities.forEach((entity, index) => {
            const movement = entity.getComponent(MovementComponent);
            if (movement && positions[index]) {
                movement.setTarget(positions[index].x, positions[index].y);
            }
        });
    }
    
    /**
     * Get formation positions for group movement
     */
    getFormationPositions(count, centerX, centerY, formation = "box") {
        const positions = [];
        const spacing = this.groupSpacing;
        
        switch (formation) {
        case "box": {
            const cols = Math.ceil(Math.sqrt(count));
            const rows = Math.ceil(count / cols);
                
            for (let i = 0; i < count; i++) {
                const row = Math.floor(i / cols);
                const col = i % cols;
                    
                positions.push({
                    x: centerX + (col - cols/2) * spacing,
                    y: centerY + (row - rows/2) * spacing
                });
            }
            break;
        }
            
        case "line": {
            for (let i = 0; i < count; i++) {
                positions.push({
                    x: centerX + (i - count/2) * spacing,
                    y: centerY
                });
            }
            break;
        }
            
        case "wedge": {
            let row = 0;
            let posInRow = 0;
            let maxInRow = 1;
                
            for (let i = 0; i < count; i++) {
                positions.push({
                    x: centerX + (posInRow - maxInRow/2) * spacing,
                    y: centerY + row * spacing
                });
                    
                posInRow++;
                if (posInRow >= maxInRow) {
                    row++;
                    maxInRow = Math.min(row + 1, 5); // Cap at 5 wide
                    posInRow = 0;
                }
            }
            break;
        }
        }
        
        return positions;
    }
    
    /**
     * OPTIMIZATION: Request path with priority queueing
     */
    requestPath(entity) {
        const movement = entity.getComponent(MovementComponent);
        const transform = entity.getComponent(TransformComponent);
        
        // Check cache first
        const cacheKey = this.getPathCacheKey(
            transform.x, transform.y,
            movement.targetX, movement.targetY
        );
        
        const cachedPath = this.pathCache.get(cacheKey);
        if (cachedPath && (performance.now() - cachedPath.timestamp) < this.cacheTimeout) {
            this.cacheHits++;
            movement.path = [...cachedPath.path];
            movement.pathIndex = 0;
            
            if (this.debugMode) {
                this.visualizePath(entity, movement.path);
            }
            return;
        }
        
        this.cacheMisses++;
        
        // Avoid duplicate requests
        if (this.processingRequests.has(entity.id)) {
            return;
        }
        
        // Calculate priority based on entity importance and urgency
        const priority = this.calculatePathPriority(entity);
        
        // Add to queue
        const request = {
            entity,
            priority,
            timestamp: performance.now(),
            cacheKey
        };
        
        this.pathRequestQueue.push(request);
        this.pathRequestQueue.sort((a, b) => b.priority - a.priority); // Higher priority first
        this.processingRequests.add(entity.id);
    }
    
    /**
     * OPTIMIZATION: Calculate priority for path requests
     */
    calculatePathPriority(entity) {
        let priority = 50; // Base priority
        
        // Higher priority for selected units
        if (entity.hasComponent(SelectableComponent)) {
            const selectable = entity.getComponent(SelectableComponent);
            if (selectable.isSelected) {
                priority += 30;
            }
        }
        
        // Higher priority for combat units
        if (entity.hasComponent("CombatComponent")) {
            priority += 20;
        }
        
        // Higher priority for units closer to camera/player view
        const transform = entity.getComponent(TransformComponent);
        const distanceFromCenter = Math.sqrt(
            Math.pow(transform.x - 600, 2) + // Assuming 1200px viewport
            Math.pow(transform.y - 400, 2)  // Assuming 800px viewport
        );
        priority += Math.max(0, 30 - distanceFromCenter / 50);
        
        return priority;
    }
    
    /**
     * OPTIMIZATION: Process path request queue with time-slicing
     */
    processPathRequestQueue(frameStartTime) {
        let processedCount = 0;
        
        while (this.pathRequestQueue.length > 0 && 
               processedCount < this.maxPathsPerFrame &&
               (performance.now() - frameStartTime) < this.timeSliceLimit) {
            
            const request = this.pathRequestQueue.shift();
            
            // Skip if entity no longer exists or doesn't need path
            if (!request.entity.active || !request.entity.getComponent(MovementComponent).isMoving) {
                this.processingRequests.delete(request.entity.id);
                continue;
            }
            
            this.calculatePathOptimized(request);
            processedCount++;
            this.performanceStats.pathsCalculatedThisFrame++;
        }
    }
    
    /**
     * Visualize path for debugging
     */
    visualizePath(entity, path) {
        if (!this.pathGraphics) return;
        
        // Remove old path visual
        if (this.pathVisuals.has(entity.id)) {
            const oldVisual = this.pathVisuals.get(entity.id);
            if (oldVisual.parent) {
                oldVisual.parent.removeChild(oldVisual);
            }
        }
        
        // Create new path visual
        const pathVisual = new PIXI.Graphics();
        
        // Draw path line
        pathVisual.lineStyle(2, 0x00ffff, 0.6);
        if (path.length > 0) {
            pathVisual.moveTo(path[0].x, path[0].y);
            for (let i = 1; i < path.length; i++) {
                pathVisual.lineTo(path[i].x, path[i].y);
            }
        }
        
        // Draw waypoints
        pathVisual.lineStyle(1, 0xffff00, 0.8);
        for (const point of path) {
            pathVisual.beginFill(0xffff00, 0.4);
            pathVisual.drawCircle(point.x, point.y, 3);
            pathVisual.endFill();
        }
        
        this.pathGraphics.addChild(pathVisual);
        this.pathVisuals.set(entity.id, pathVisual);
    }
    
    /**
     * Update debug grid visualization
     */
    updateDebugGrid() {
        if (this.navGrid && this.debugMode) {
            this.navGrid.updateDebugVisualization();
        }
    }
    
    /**
     * Update all debug visualizations
     */
    updateDebugVisualization() {
        // Update paths
        this.pathGraphics.clear();
        
        for (const entity of this.entities) {
            const movement = entity.getComponent(MovementComponent);
            if (movement.path.length > 0) {
                this.visualizePath(entity, movement.path);
            }
        }
    }
    
    /**
     * Toggle debug mode
     */
    toggleDebugMode(pixiStage) {
        if (this.debugMode) {
            // Disable debug mode
            this.debugMode = false;
            if (this.debugGraphics && this.debugGraphics.parent) {
                this.debugGraphics.parent.removeChild(this.debugGraphics);
            }
        } else {
            // Enable debug mode
            this.enableDebugMode(pixiStage);
        }
    }
    
    /**
     * OPTIMIZATION: Enhanced path calculation with caching
     */
    calculatePathOptimized(request) {
        const startTime = performance.now();
        const entity = request.entity;
        const movement = entity.getComponent(MovementComponent);
        const transform = entity.getComponent(TransformComponent);
        
        try {
            // Clear old path from navigation grid (so unit doesn't block itself)
            this.navGrid.removeDynamicObstacle(entity.id);
            
            // Find path with enhanced A*
            const path = this.pathfinder.findPathOptimized(
                transform.x, transform.y,
                movement.targetX, movement.targetY,
                entity
            );
            
            // Re-add unit to navigation grid
            if (entity.hasComponent(UnitComponent)) {
                this.navGrid.addDynamicObstacle(entity.id, transform.x, transform.y, 8);
            }
            
            if (path && path.length > 0) {
                // Remove first point (current position)
                if (path.length > 1) {
                    path.shift();
                }
                
                movement.path = path;
                movement.pathIndex = 0;
                
                // Cache the result
                this.cachePathResult(request.cacheKey, path);
                
                // Visualize path in debug mode
                if (this.debugMode) {
                    this.visualizePath(entity, path);
                }
            } else {
                // No path found
                movement.stop();
                if (this.debugMode) {
                    console.warn(`No path found for entity ${entity.id}`);
                }
            }
        } finally {
            this.processingRequests.delete(entity.id);
            
            // Update performance stats
            const calculationTime = performance.now() - startTime;
            this.performanceStats.averagePathCalculationTime = 
                (this.performanceStats.averagePathCalculationTime * 0.9) + (calculationTime * 0.1);
        }
    }
    
    /**
     * Get comprehensive pathfinding statistics
     */
    getStats() {
        return {
            gridStats: this.navGrid.getStats(),
            pathfinderStats: this.pathfinder.getStats(),
            obstacleCount: this.obstacles.size,
            debugMode: this.debugMode,
            
            // Performance optimization stats
            performance: {
                pathsCalculatedThisFrame: this.performanceStats.pathsCalculatedThisFrame,
                averagePathCalculationTime: this.performanceStats.averagePathCalculationTime,
                spatialQueriesPerFrame: this.performanceStats.spatialQueriesPerFrame,
                cacheHitRatio: this.performanceStats.cacheHitRatio,
                
                // Cache statistics
                cacheSize: this.pathCache.size,
                maxCacheSize: this.maxCacheSize,
                cacheHits: this.cacheHits,
                cacheMisses: this.cacheMisses,
                
                // Queue statistics
                queueLength: this.pathRequestQueue.length,
                maxPathsPerFrame: this.maxPathsPerFrame,
                timeSliceLimit: this.timeSliceLimit,
                
                // Spatial partitioning
                spatialCellSize: this.spatialCellSize,
                spatialGridSize: `${this.spatialCols}x${this.spatialRows}`
            }
        };
    }
}
// Apply performance extensions
extendPathfindingSystem(PathfindingSystem);
