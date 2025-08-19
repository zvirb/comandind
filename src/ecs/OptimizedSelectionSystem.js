import * as PIXI from 'pixi.js';
import { System } from './System.js';
import { SelectableComponent, TransformComponent, SpriteComponent, HealthComponent, CommandComponent, MovementComponent } from './Component.js';
import { QuadTree } from '../utils/QuadTree.js';

/**
 * Optimized Selection System - Uses QuadTree spatial partitioning for O(log n) selection
 * Targets <16ms response time for selection operations with 200+ entities
 */
export class OptimizedSelectionSystem extends System {
    constructor(world, inputHandler, camera, stage) {
        super(world);
        this.priority = 5; // Priority 5 - runs after movement but before rendering
        this.requiredComponents = [SelectableComponent, TransformComponent];
        this.inputHandler = inputHandler;
        this.camera = camera;
        this.stage = stage;
        
        // Selection state
        this.selectedEntities = new Set();
        this.hoveredEntity = null;
        
        // Box selection state
        this.isBoxSelecting = false;
        this.boxSelectStart = { x: 0, y: 0 };
        this.boxSelectEnd = { x: 0, y: 0 };
        this.selectionBox = null;
        
        // QuadTree spatial partitioning for O(log n) selection
        this.worldBounds = { x: 0, y: 0, width: 2000, height: 2000 };
        this.spatialTree = new QuadTree(this.worldBounds, 10, 5);
        this.spatialUpdateInterval = 100; // Update spatial tree every 100ms
        this.lastSpatialUpdate = 0;
        
        // Performance tracking
        this.performanceStats = {
            lastSelectionTime: 0,
            averageSelectionTime: 0,
            spatialQueries: 0,
            entityCount: 0,
            quadTreeDepth: 0
        };
        
        // Visual elements container
        this.selectionGraphics = new PIXI.Container();
        this.selectionGraphics.name = 'optimized-selection';
        stage.addChild(this.selectionGraphics);
        
        // Selection box graphics
        this.createSelectionBox();
        
        // Event listener tracking for cleanup
        this.eventHandlers = new Map();
        this.isDestroyed = false;
        
        // Setup input handlers
        this.setupInputHandlers();
        
        // Cache for frequently accessed entities
        this.entityCache = new Map();
        this.cacheInvalidateInterval = 500; // Invalidate cache every 500ms
        this.lastCacheInvalidation = 0;
    }
    
    /**
     * Create the selection box graphic for box selection
     */
    createSelectionBox() {
        this.selectionBoxGraphic = new PIXI.Graphics();
        this.selectionBoxGraphic.visible = false;
        this.selectionGraphics.addChild(this.selectionBoxGraphic);
    }
    
    /**
     * Setup input event handlers
     */
    setupInputHandlers() {
        if (this.isDestroyed || !this.inputHandler) return;
        
        // Create bound handlers for proper cleanup
        const mousedownHandler = (event) => {
            if (this.isDestroyed) return;
            if (event.button === 0) { // Left click
                this.handleLeftMouseDown(event);
            } else if (event.button === 2) { // Right click
                this.handleRightMouseDown(event);
            }
        };
        
        const mousemoveHandler = (event) => {
            if (this.isDestroyed) return;
            this.handleMouseMove(event);
        };
        
        const mouseupHandler = (event) => {
            if (this.isDestroyed) return;
            if (event.button === 0) { // Left click release
                this.handleLeftMouseUp(event);
            }
        };
        
        const keydownHandler = (event) => {
            if (this.isDestroyed) return;
            this.handleKeyDown(event);
        };
        
        // Store handlers for cleanup
        this.eventHandlers.set('mousedown', mousedownHandler);
        this.eventHandlers.set('mousemove', mousemoveHandler);
        this.eventHandlers.set('mouseup', mouseupHandler);
        this.eventHandlers.set('keydown', keydownHandler);
        
        // Register event handlers
        this.inputHandler.on('mousedown', mousedownHandler);
        this.inputHandler.on('mousemove', mousemoveHandler);
        this.inputHandler.on('mouseup', mouseupHandler);
        this.inputHandler.on('keydown', keydownHandler);
        
        console.log('✅ OptimizedSelectionSystem input handlers setup completed');
    }
    
    /**
     * Update spatial partitioning tree with current entity positions
     */
    updateSpatialTree() {
        const now = Date.now();
        if (now - this.lastSpatialUpdate < this.spatialUpdateInterval) {
            return; // Skip update if not enough time has passed
        }
        
        const startTime = performance.now();
        
        // Clear and rebuild spatial tree
        this.spatialTree.clear();
        
        // Insert all selectable entities
        for (const entity of this.entities) {
            const transform = entity.getComponent(TransformComponent);
            const selectable = entity.getComponent(SelectableComponent);
            
            if (transform && selectable && entity.active) {
                // Create spatial representation of entity
                const spatialEntity = {
                    entity: entity,
                    transform: transform,
                    selectable: selectable,
                    getComponent: (type) => entity.getComponent(type),
                    x: transform.x,
                    y: transform.y,
                    bounds: {
                        width: selectable.selectableRadius * 2,
                        height: selectable.selectableRadius * 2
                    }
                };
                
                this.spatialTree.insert(spatialEntity);
            }
        }
        
        this.lastSpatialUpdate = now;
        
        // Update performance stats
        const updateTime = performance.now() - startTime;
        this.performanceStats.entityCount = this.entities.size;
        this.performanceStats.quadTreeDepth = this.spatialTree.getMaxDepth();
        
        if (updateTime > 5) { // Log if spatial update takes too long
            console.warn(`Spatial tree update took ${updateTime.toFixed(2)}ms for ${this.entities.size} entities`);
        }
    }
    
    /**
     * Get entity at world position using QuadTree (O(log n) instead of O(n))
     */
    getEntityAtPosition(x, y) {
        const startTime = performance.now();
        this.performanceStats.spatialQueries++;
        
        // Use QuadTree for fast spatial lookup
        const searchRadius = 20; // Slightly larger than typical selectable radius
        const nearbyEntities = this.spatialTree.queryRadius(x, y, searchRadius);
        
        let closestEntity = null;
        let closestDistance = Infinity;
        
        // Find the closest selectable entity within selection radius
        for (const spatialEntity of nearbyEntities) {
            const entity = spatialEntity.entity;
            const transform = spatialEntity.transform;
            const selectable = spatialEntity.selectable;
            
            if (!entity.active || !transform || !selectable) continue;
            
            const distance = Math.sqrt(
                Math.pow(transform.x - x, 2) + 
                Math.pow(transform.y - y, 2)
            );
            
            if (distance <= selectable.selectableRadius && distance < closestDistance) {
                closestDistance = distance;
                closestEntity = entity;
            }
        }
        
        // Update performance tracking
        const selectionTime = performance.now() - startTime;
        this.performanceStats.lastSelectionTime = selectionTime;
        this.performanceStats.averageSelectionTime = 
            (this.performanceStats.averageSelectionTime * 0.9) + (selectionTime * 0.1);
        
        return closestEntity;
    }
    
    /**
     * Select entities within a box using QuadTree optimization
     */
    selectEntitiesInBox(minX, minY, maxX, maxY, addToSelection = false) {
        const startTime = performance.now();
        
        if (!addToSelection) {
            this.clearSelection();
        }
        
        // Use QuadTree for fast rectangular query
        const entitiesInBox = this.spatialTree.queryRect(minX, minY, maxX - minX, maxY - minY);
        
        for (const spatialEntity of entitiesInBox) {
            const entity = spatialEntity.entity;
            const transform = spatialEntity.transform;
            const selectable = spatialEntity.selectable;
            
            if (entity.active && transform && selectable) {
                // Double-check bounds (QuadTree gives approximate results)
                if (transform.x >= minX && transform.x <= maxX &&
                    transform.y >= minY && transform.y <= maxY) {
                    this.selectEntity(entity);
                }
            }
        }
        
        const selectionTime = performance.now() - startTime;
        console.log(`Box selection took ${selectionTime.toFixed(2)}ms for ${entitiesInBox.length} potential entities`);
    }
    
    /**
     * Handle left mouse button down with optimized entity detection
     */
    handleLeftMouseDown(event) {
        const worldPos = this.camera.screenToWorld(event.clientX, event.clientY);
        
        // Start box selection
        this.isBoxSelecting = true;
        this.boxSelectStart = { x: event.clientX, y: event.clientY };
        this.boxSelectEnd = { x: event.clientX, y: event.clientY };
        
        // Use optimized entity lookup
        const clickedEntity = this.getEntityAtPosition(worldPos.x, worldPos.y);
        
        if (!event.shiftKey && !event.ctrlKey) {
            // Clear selection if not using modifier keys
            this.clearSelection();
        }
        
        if (clickedEntity) {
            if (event.ctrlKey) {
                // Toggle selection with Ctrl
                this.toggleEntitySelection(clickedEntity);
            } else {
                // Select clicked entity
                this.selectEntity(clickedEntity);
            }
        }
    }
    
    /**
     * Handle left mouse button up with optimized box selection
     */
    handleLeftMouseUp(event) {
        if (this.isBoxSelecting) {
            const worldStart = this.camera.screenToWorld(this.boxSelectStart.x, this.boxSelectStart.y);
            const worldEnd = this.camera.screenToWorld(this.boxSelectEnd.x, this.boxSelectEnd.y);
            
            // Calculate box bounds
            const minX = Math.min(worldStart.x, worldEnd.x);
            const maxX = Math.max(worldStart.x, worldEnd.x);
            const minY = Math.min(worldStart.y, worldEnd.y);
            const maxY = Math.max(worldStart.y, worldEnd.y);
            
            // Check if it's a box selection (not just a click)
            const boxWidth = Math.abs(this.boxSelectEnd.x - this.boxSelectStart.x);
            const boxHeight = Math.abs(this.boxSelectEnd.y - this.boxSelectStart.y);
            
            if (boxWidth > 5 || boxHeight > 5) {
                // Perform optimized box selection
                this.selectEntitiesInBox(minX, minY, maxX, maxY, event.shiftKey);
            }
            
            // Hide selection box
            this.isBoxSelecting = false;
            this.selectionBoxGraphic.visible = false;
        }
    }
    
    /**
     * Handle right mouse button down (issue commands)
     */
    handleRightMouseDown(event) {
        const worldPos = this.camera.screenToWorld(event.clientX, event.clientY);
        
        // Issue move command to selected units
        if (this.selectedEntities.size > 0) {
            this.issueCommandToSelected('move', { x: worldPos.x, y: worldPos.y }, event.shiftKey);
            
            // Show move marker effect
            this.showCommandMarker(worldPos.x, worldPos.y, 'move');
        }
    }
    
    /**
     * Handle mouse move with optimized hover detection
     */
    handleMouseMove(event) {
        const worldPos = this.camera.screenToWorld(event.clientX, event.clientY);
        
        // Update box selection
        if (this.isBoxSelecting) {
            this.boxSelectEnd = { x: event.clientX, y: event.clientY };
            this.updateSelectionBox();
        } else {
            // Update hover state with optimized lookup
            const hoveredEntity = this.getEntityAtPosition(worldPos.x, worldPos.y);
            this.updateHoverState(hoveredEntity);
        }
    }
    
    /**
     * Handle keyboard input
     */
    handleKeyDown(event) {
        // Ctrl+A - Select all units
        if (event.ctrlKey && event.key === 'a') {
            const activeElement = document.activeElement;
            const isGameFocused = activeElement === document.body || 
                                activeElement === this.stage.canvas || 
                                activeElement.closest('#game-container');
            
            if (isGameFocused && this.selectedEntities.size > 0) {
                event.preventDefault();
                this.selectAllUnits();
                console.log('🎯 Selected all units with Ctrl+A');
            }
        }
        
        // Escape - Clear selection
        if (event.key === 'Escape') {
            this.clearSelection();
        }
        
        // Delete - Destroy selected units (for testing)
        if (event.key === 'Delete') {
            this.destroySelected();
        }
        
        // Number keys for control groups
        if (event.key >= '1' && event.key <= '9') {
            const groupNumber = parseInt(event.key);
            if (event.ctrlKey) {
                this.createControlGroup(groupNumber);
            } else {
                this.selectControlGroup(groupNumber);
            }
        }
    }
    
    /**
     * Select a single entity
     */
    selectEntity(entity) {
        const selectable = entity.getComponent(SelectableComponent);
        if (selectable && !selectable.isSelected) {
            selectable.select();
            this.selectedEntities.add(entity);
            this.createSelectionVisuals(entity);
        }
    }
    
    /**
     * Deselect a single entity
     */
    deselectEntity(entity) {
        const selectable = entity.getComponent(SelectableComponent);
        if (selectable && selectable.isSelected) {
            selectable.deselect();
            this.selectedEntities.delete(entity);
            this.removeSelectionVisuals(entity);
        }
    }
    
    /**
     * Toggle entity selection
     */
    toggleEntitySelection(entity) {
        const selectable = entity.getComponent(SelectableComponent);
        if (selectable) {
            if (selectable.isSelected) {
                this.deselectEntity(entity);
            } else {
                this.selectEntity(entity);
            }
        }
    }
    
    /**
     * Clear all selections
     */
    clearSelection() {
        for (const entity of this.selectedEntities) {
            const selectable = entity.getComponent(SelectableComponent);
            if (selectable) {
                selectable.deselect();
                this.removeSelectionVisuals(entity);
            }
        }
        this.selectedEntities.clear();
    }
    
    /**
     * Select all units using QuadTree
     */
    selectAllUnits() {
        this.clearSelection();
        
        // Use QuadTree to get all entities efficiently
        const allEntities = this.spatialTree.queryRect(
            this.worldBounds.x, 
            this.worldBounds.y, 
            this.worldBounds.width, 
            this.worldBounds.height
        );
        
        for (const spatialEntity of allEntities) {
            const entity = spatialEntity.entity;
            const selectable = entity.getComponent(SelectableComponent);
            
            if (entity.active && selectable) {
                this.selectEntity(entity);
            }
        }
    }
    
    /**
     * Create selection visuals for an entity
     */
    createSelectionVisuals(entity) {
        const selectable = entity.getComponent(SelectableComponent);
        const transform = entity.getComponent(TransformComponent);
        
        if (!selectable || !transform) return;
        
        // Create selection box
        const selectionBox = new PIXI.Graphics();
        selectionBox.lineStyle(2, 0x00ff00, 1);
        selectionBox.drawRect(-20, -20, 40, 40);
        selectionBox.position.set(transform.x, transform.y);
        selectable.selectionBox = selectionBox;
        this.selectionGraphics.addChild(selectionBox);
        
        // Create health bar
        const health = entity.getComponent(HealthComponent);
        if (health) {
            const healthBar = new PIXI.Container();
            
            // Background
            const bgBar = new PIXI.Graphics();
            bgBar.beginFill(0x000000, 0.5);
            bgBar.drawRect(-15, -30, 30, 4);
            bgBar.endFill();
            
            // Health fill
            const fillBar = new PIXI.Graphics();
            const healthPercent = health.getHealthPercentage();
            const color = healthPercent > 0.6 ? 0x00ff00 : healthPercent > 0.3 ? 0xffff00 : 0xff0000;
            fillBar.beginFill(color, 1);
            fillBar.drawRect(-15, -30, 30 * healthPercent, 4);
            fillBar.endFill();
            
            healthBar.addChild(bgBar);
            healthBar.addChild(fillBar);
            healthBar.position.set(transform.x, transform.y);
            
            selectable.healthBar = healthBar;
            this.selectionGraphics.addChild(healthBar);
        }
    }
    
    /**
     * Remove selection visuals for an entity
     */
    removeSelectionVisuals(entity) {
        const selectable = entity.getComponent(SelectableComponent);
        if (!selectable) return;
        
        if (selectable.selectionBox) {
            this.selectionGraphics.removeChild(selectable.selectionBox);
            selectable.selectionBox = null;
        }
        
        if (selectable.healthBar) {
            this.selectionGraphics.removeChild(selectable.healthBar);
            selectable.healthBar = null;
        }
    }
    
    /**
     * Update hover state
     */
    updateHoverState(entity) {
        // Clear previous hover
        if (this.hoveredEntity && this.hoveredEntity !== entity) {
            const selectable = this.hoveredEntity.getComponent(SelectableComponent);
            if (selectable) {
                selectable.isHovered = false;
            }
        }
        
        // Set new hover
        this.hoveredEntity = entity;
        if (entity) {
            const selectable = entity.getComponent(SelectableComponent);
            if (selectable) {
                selectable.isHovered = true;
            }
        }
    }
    
    /**
     * Update selection box visual
     */
    updateSelectionBox() {
        if (!this.isBoxSelecting) return;
        
        const startX = this.boxSelectStart.x;
        const startY = this.boxSelectStart.y;
        const endX = this.boxSelectEnd.x;
        const endY = this.boxSelectEnd.y;
        
        const minX = Math.min(startX, endX);
        const minY = Math.min(startY, endY);
        const width = Math.abs(endX - startX);
        const height = Math.abs(endY - startY);
        
        this.selectionBoxGraphic.clear();
        this.selectionBoxGraphic.lineStyle(2, 0x00ff00, 0.8);
        this.selectionBoxGraphic.beginFill(0x00ff00, 0.1);
        this.selectionBoxGraphic.drawRect(minX, minY, width, height);
        this.selectionBoxGraphic.endFill();
        this.selectionBoxGraphic.visible = true;
    }
    
    /**
     * Issue command to selected units
     */
    issueCommandToSelected(command, target, queued = false) {
        // Check if we have a pathfinding system for group movement
        const pathfindingSystem = this.world.systems.find(s => s.constructor.name === 'PathfindingSystem');
        
        if (command === 'move' && target) {
            // Use group movement if available and multiple units selected
            if (pathfindingSystem && this.selectedEntities.size > 1) {
                const entitiesArray = Array.from(this.selectedEntities);
                pathfindingSystem.calculateGroupMovement(entitiesArray, target.x, target.y);
            } else {
                // Individual movement for single unit or no pathfinding
                for (const entity of this.selectedEntities) {
                    const commandComp = entity.getComponent(CommandComponent);
                    const movement = entity.getComponent(MovementComponent);
                    
                    if (movement) {
                        movement.setTarget(target.x, target.y);
                        if (commandComp) {
                            commandComp.issueCommand('move', target, queued);
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Show command marker effect
     */
    showCommandMarker(x, y, type) {
        const marker = new PIXI.Graphics();
        marker.lineStyle(2, type === 'move' ? 0x00ff00 : 0xff0000, 1);
        marker.drawCircle(0, 0, 10);
        marker.position.set(x, y);
        marker.alpha = 1;
        
        this.selectionGraphics.addChild(marker);
        
        // Animate and remove
        let animFrame = 0;
        const animate = () => {
            animFrame++;
            marker.scale.set(1 + animFrame * 0.05);
            marker.alpha = 1 - animFrame * 0.05;
            
            if (animFrame < 20) {
                requestAnimationFrame(animate);
            } else {
                this.selectionGraphics.removeChild(marker);
            }
        };
        animate();
    }
    
    /**
     * Create control group
     */
    createControlGroup(groupNumber) {
        for (const entity of this.selectedEntities) {
            const selectable = entity.getComponent(SelectableComponent);
            if (selectable) {
                selectable.selectionGroup = groupNumber;
            }
        }
        console.log(`Created control group ${groupNumber} with ${this.selectedEntities.size} units`);
    }
    
    /**
     * Select control group using QuadTree optimization
     */
    selectControlGroup(groupNumber) {
        this.clearSelection();
        
        // Use QuadTree to efficiently find entities in the group
        const allEntities = this.spatialTree.queryRect(
            this.worldBounds.x, 
            this.worldBounds.y, 
            this.worldBounds.width, 
            this.worldBounds.height
        );
        
        for (const spatialEntity of allEntities) {
            const entity = spatialEntity.entity;
            const selectable = entity.getComponent(SelectableComponent);
            
            if (entity.active && selectable && selectable.selectionGroup === groupNumber) {
                this.selectEntity(entity);
            }
        }
    }
    
    /**
     * Destroy selected units (for testing)
     */
    destroySelected() {
        for (const entity of this.selectedEntities) {
            entity.active = false;
        }
        this.selectedEntities.clear();
    }
    
    /**
     * Called when entity is added to system
     */
    onEntityAdded(entity) {
        // Entity will be added to spatial tree on next update
    }
    
    /**
     * Called when entity is removed from system
     */
    onEntityRemoved(entity) {
        // Clean up if this entity was selected
        if (this.selectedEntities.has(entity)) {
            this.deselectEntity(entity);
        }
        
        // Remove from spatial tree (will be handled on next rebuild)
        this.spatialTree.remove(entity);
    }
    
    /**
     * Update selection system with optimized spatial partitioning
     */
    update(deltaTime) {
        if (this.isDestroyed) return;
        
        // Update spatial partitioning periodically
        this.updateSpatialTree();
        
        // Invalidate entity cache periodically
        const now = Date.now();
        if (now - this.lastCacheInvalidation > this.cacheInvalidateInterval) {
            this.entityCache.clear();
            this.lastCacheInvalidation = now;
        }
        
        // Update visual positions for selected entities
        for (const entity of this.selectedEntities) {
            const selectable = entity.getComponent(SelectableComponent);
            const transform = entity.getComponent(TransformComponent);
            
            if (selectable && transform) {
                // Update selection box position
                if (selectable.selectionBox) {
                    selectable.selectionBox.position.set(transform.x, transform.y);
                }
                
                // Update health bar
                if (selectable.healthBar) {
                    selectable.healthBar.position.set(transform.x, transform.y);
                    
                    // Update health bar fill
                    const health = entity.getComponent(HealthComponent);
                    if (health) {
                        const fillBar = selectable.healthBar.children[1];
                        if (fillBar) {
                            fillBar.clear();
                            const healthPercent = health.getHealthPercentage();
                            const color = healthPercent > 0.6 ? 0x00ff00 : 
                                        healthPercent > 0.3 ? 0xffff00 : 0xff0000;
                            fillBar.beginFill(color, 1);
                            fillBar.drawRect(-15, -30, 30 * healthPercent, 4);
                            fillBar.endFill();
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        return {
            ...this.performanceStats,
            selectedEntities: this.selectedEntities.size,
            spatialTreeStats: this.spatialTree.getStats(),
            cacheSize: this.entityCache.size
        };
    }
    
    /**
     * Clean up all event listeners and resources
     */
    destroy() {
        if (this.isDestroyed) {
            console.warn('OptimizedSelectionSystem already destroyed');
            return;
        }
        
        console.log('🗑️ Destroying OptimizedSelectionSystem...');
        
        this.isDestroyed = true;
        
        // Remove all input event handlers
        if (this.inputHandler && this.inputHandler.isAlive()) {
            for (const [eventType, handler] of this.eventHandlers) {
                try {
                    this.inputHandler.off(eventType, handler);
                } catch (error) {
                    console.warn(`Failed to remove ${eventType} handler:`, error);
                }
            }
        }
        
        // Clear event handlers
        this.eventHandlers.clear();
        
        // Clear all selections
        this.clearSelection();
        
        // Clean up spatial tree
        this.spatialTree.clear();
        
        // Clean up graphics
        if (this.selectionGraphics) {
            this.selectionGraphics.destroy({ children: true });
            if (this.stage && this.stage.children.includes(this.selectionGraphics)) {
                this.stage.removeChild(this.selectionGraphics);
            }
        }
        
        // Clear references
        this.selectedEntities.clear();
        this.entityCache.clear();
        this.inputHandler = null;
        this.camera = null;
        this.stage = null;
        this.selectionGraphics = null;
        this.selectionBoxGraphic = null;
        this.hoveredEntity = null;
        this.spatialTree = null;
        
        console.log('✅ OptimizedSelectionSystem destroyed successfully');
    }
    
    /**
     * Check if OptimizedSelectionSystem is destroyed
     */
    isAlive() {
        return !this.isDestroyed;
    }
    
    /**
     * Get event listener statistics for debugging
     */
    getListenerStats() {
        return {
            eventHandlers: this.eventHandlers.size,
            selectedEntities: this.selectedEntities.size,
            isDestroyed: this.isDestroyed,
            spatialTreeDepth: this.spatialTree ? this.spatialTree.getMaxDepth() : 0,
            spatialTreeEntities: this.spatialTree ? this.spatialTree.getTotalEntities() : 0
        };
    }
}