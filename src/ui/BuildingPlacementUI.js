/**
 * BuildingPlacementUI - Grid-based building placement system
 * 
 * Advanced building placement interface with ghost previews, validation feedback,
 * and grid snapping. Provides intuitive visual feedback for valid/invalid
 * placement locations with real-time collision detection.
 * 
 * Features:
 * - Ghost preview rendering with transparency
 * - Grid-based snapping and validation
 * - Collision detection with existing structures
 * - Resource requirement validation
 * - Power grid connectivity checks
 * - Terrain suitability analysis
 * - Multi-cell building support
 * - Placement animation effects
 */

import * as PIXI from 'pixi.js';

export class BuildingPlacementUI {
    constructor(app, camera, world, options = {}) {
        this.app = app;
        this.camera = camera;
        this.world = world;
        this.renderer = app.renderer;
        
        // Configuration
        this.config = {
            gridSize: options.gridSize || 32,
            gridColor: options.gridColor || 0x404040,
            gridAlpha: options.gridAlpha || 0.3,
            validColor: options.validColor || 0x00ff00,
            invalidColor: options.invalidColor || 0xff0000,
            ghostAlpha: options.ghostAlpha || 0.6,
            snapToGrid: options.snapToGrid !== false,
            showGrid: options.showGrid !== false,
            showRadius: options.showRadius !== false,
            enableSounds: options.enableSounds !== false
        };
        
        // Placement state
        this.isPlacementMode = false;
        this.currentBuilding = null;
        this.ghostSprite = null;
        this.validationOverlay = null;
        this.buildingData = null;
        this.mousePosition = { x: 0, y: 0 };
        this.gridPosition = { x: 0, y: 0 };
        this.isValidPlacement = false;
        
        // Containers for UI elements
        this.placementContainer = new PIXI.Container();
        this.placementContainer.name = 'building-placement';
        this.placementContainer.sortableChildren = true;
        
        this.gridContainer = new PIXI.Container();
        this.gridContainer.name = 'placement-grid';
        this.gridContainer.zIndex = 5;
        
        this.ghostContainer = new PIXI.Container();
        this.ghostContainer.name = 'placement-ghost';
        this.ghostContainer.zIndex = 10;
        
        this.overlayContainer = new PIXI.Container();
        this.overlayContainer.name = 'placement-overlay';
        this.overlayContainer.zIndex = 15;
        
        // Add containers in order
        this.placementContainer.addChild(this.gridContainer);
        this.placementContainer.addChild(this.ghostContainer);
        this.placementContainer.addChild(this.overlayContainer);
        
        // Add to UI layer
        app.stage.addChild(this.placementContainer);
        
        // Grid graphics
        this.gridGraphics = new PIXI.Graphics();
        this.gridContainer.addChild(this.gridGraphics);
        
        // Validation cache
        this.validationCache = new Map();
        this.cacheTimeout = 100; // ms
        
        // Event handlers
        this.eventHandlers = [];
        this.isDestroyed = false;
        
        // Building database (will be populated from game data)
        this.buildingDatabase = new Map();
        
        // Resource validator reference
        this.resourceValidator = null;
        
        this.init();
    }
    
    /**
     * Initialize the building placement UI
     */
    init() {
        console.log('🏗️  Initializing BuildingPlacementUI...');
        
        // Load building definitions
        this.loadBuildingData();
        
        // Setup input handlers
        this.setupInputHandlers();
        
        // Initially hidden
        this.placementContainer.visible = false;
        
        console.log('✅ BuildingPlacementUI initialized');
    }
    
    /**
     * Load building data from game configuration
     */
    async loadBuildingData() {
        try {
            // Load building definitions from assets
            const response = await fetch('/public/assets/cnc-data/buildings.json');
            const buildingData = await response.json();
            
            // Process building data
            for (const [buildingId, data] of Object.entries(buildingData)) {
                this.buildingDatabase.set(buildingId, {
                    id: buildingId,
                    name: data.name || buildingId,
                    width: data.width || 1,
                    height: data.height || 1,
                    cost: data.cost || 100,
                    power: data.power || 0,
                    powerRequired: data.powerRequired || 0,
                    terrain: data.terrain || ['clear'],
                    spriteSheet: data.spriteSheet || 'buildings',
                    spriteFrame: data.spriteFrame || buildingId,
                    buildTime: data.buildTime || 1000,
                    prerequisites: data.prerequisites || [],
                    description: data.description || ''
                });
            }
            
            console.log(`📋 Loaded ${this.buildingDatabase.size} building definitions`);
            
        } catch (error) {
            console.warn('⚠️ Failed to load building data, using defaults:', error);
            
            // Fallback building data
            this.buildingDatabase.set('barracks', {
                id: 'barracks',
                name: 'Barracks',
                width: 2,
                height: 2,
                cost: 300,
                power: -10,
                terrain: ['clear'],
                spriteSheet: 'buildings',
                spriteFrame: 'barracks'
            });
            
            this.buildingDatabase.set('power-plant', {
                id: 'power-plant',
                name: 'Power Plant',
                width: 2,
                height: 2,
                cost: 200,
                power: 100,
                terrain: ['clear'],
                spriteSheet: 'buildings',
                spriteFrame: 'power-plant'
            });
        }
    }
    
    /**
     * Setup input event handlers
     */
    setupInputHandlers() {
        // Mouse move handler for ghost preview
        const mouseMoveHandler = (event) => {
            if (this.isPlacementMode && !this.isDestroyed) {
                this.updateGhostPosition(event.clientX, event.clientY);
            }
        };
        
        // Mouse click handler for placement
        const mouseClickHandler = (event) => {
            if (this.isPlacementMode && event.button === 0) { // Left click
                if (this.isValidPlacement) {
                    this.placeBuilding();
                } else {
                    this.showInvalidPlacementFeedback();
                }
            } else if (event.button === 2) { // Right click - cancel
                this.cancelPlacement();
            }
        };
        
        // Keyboard handlers
        const keyHandler = (event) => {
            if (this.isPlacementMode) {
                if (event.key === 'Escape') {
                    this.cancelPlacement();
                } else if (event.key === 'r' || event.key === 'R') {
                    this.rotateBuildingPreview();
                }
            }
        };
        
        // Register handlers
        if (typeof window !== 'undefined') {
            window.addEventListener('mousemove', mouseMoveHandler);
            window.addEventListener('mousedown', mouseClickHandler);
            window.addEventListener('keydown', keyHandler);
            
            // Store for cleanup
            this.eventHandlers = [
                { type: 'mousemove', handler: mouseMoveHandler },
                { type: 'mousedown', handler: mouseClickHandler },
                { type: 'keydown', handler: keyHandler }
            ];
        }
    }
    
    /**
     * Start building placement mode
     */
    startPlacement(buildingId, resourceValidator = null) {
        if (this.isDestroyed) return false;
        
        const buildingData = this.buildingDatabase.get(buildingId);
        if (!buildingData) {
            console.error(`❌ Unknown building: ${buildingId}`);
            return false;
        }
        
        console.log(`🏗️  Starting placement for ${buildingData.name}`);
        
        this.isPlacementMode = true;
        this.currentBuilding = buildingId;
        this.buildingData = buildingData;
        this.resourceValidator = resourceValidator;
        
        // Show placement UI
        this.placementContainer.visible = true;
        
        // Create ghost sprite
        this.createGhostSprite();
        
        // Show grid if enabled
        if (this.config.showGrid) {
            this.showPlacementGrid();
        }
        
        // Change cursor
        if (typeof document !== 'undefined') {
            document.body.style.cursor = 'crosshair';
        }
        
        return true;
    }
    
    /**
     * Cancel building placement
     */
    cancelPlacement() {
        if (!this.isPlacementMode) return;
        
        console.log('🚫 Canceling building placement');
        
        this.isPlacementMode = false;
        this.currentBuilding = null;
        this.buildingData = null;
        this.resourceValidator = null;
        
        // Hide placement UI
        this.placementContainer.visible = false;
        
        // Clean up ghost sprite
        this.clearGhostSprite();
        
        // Clear grid
        this.clearPlacementGrid();
        
        // Clear validation cache
        this.validationCache.clear();
        
        // Restore cursor
        if (typeof document !== 'undefined') {
            document.body.style.cursor = 'default';
        }
        
        // Emit cancel event
        this.emit('placementCanceled', { buildingId: this.currentBuilding });
    }
    
    /**
     * Create ghost sprite for building preview
     */
    createGhostSprite() {
        this.clearGhostSprite();
        
        if (!this.buildingData) return;
        
        // Create placeholder sprite (in real implementation, load from texture atlas)
        const graphics = new PIXI.Graphics();
        const width = this.buildingData.width * this.config.gridSize;
        const height = this.buildingData.height * this.config.gridSize;
        
        // Draw building outline
        graphics.lineStyle(2, 0xffffff, 0.8);
        graphics.beginFill(0x0066cc, 0.3);
        graphics.drawRect(0, 0, width, height);
        graphics.endFill();
        
        // Add building icon/text
        const style = new PIXI.TextStyle({
            fontFamily: 'Arial',
            fontSize: 12,
            fill: 0xffffff,
            align: 'center'
        });
        
        const text = new PIXI.Text(this.buildingData.name, style);
        text.anchor.set(0.5);
        text.position.set(width / 2, height / 2);
        
        // Create container for ghost
        this.ghostSprite = new PIXI.Container();
        this.ghostSprite.addChild(graphics);
        this.ghostSprite.addChild(text);
        this.ghostSprite.alpha = this.config.ghostAlpha;
        
        // Add validation overlay
        this.validationOverlay = new PIXI.Graphics();
        this.ghostSprite.addChild(this.validationOverlay);
        
        this.ghostContainer.addChild(this.ghostSprite);
    }
    
    /**
     * Clear ghost sprite
     */
    clearGhostSprite() {
        if (this.ghostSprite) {
            this.ghostContainer.removeChild(this.ghostSprite);
            this.ghostSprite.destroy({ children: true });
            this.ghostSprite = null;
            this.validationOverlay = null;
        }
    }
    
    /**
     * Show placement grid
     */
    showPlacementGrid() {
        this.clearPlacementGrid();
        
        // Get viewport bounds
        const bounds = this.getViewportBounds();
        
        // Calculate grid lines
        const startX = Math.floor(bounds.left / this.config.gridSize) * this.config.gridSize;
        const endX = Math.ceil(bounds.right / this.config.gridSize) * this.config.gridSize;
        const startY = Math.floor(bounds.top / this.config.gridSize) * this.config.gridSize;
        const endY = Math.ceil(bounds.bottom / this.config.gridSize) * this.config.gridSize;
        
        this.gridGraphics.lineStyle(1, this.config.gridColor, this.config.gridAlpha);
        
        // Draw vertical lines
        for (let x = startX; x <= endX; x += this.config.gridSize) {
            this.gridGraphics.moveTo(x, startY);
            this.gridGraphics.lineTo(x, endY);
        }
        
        // Draw horizontal lines
        for (let y = startY; y <= endY; y += this.config.gridSize) {
            this.gridGraphics.moveTo(startX, y);
            this.gridGraphics.lineTo(endX, y);
        }
    }
    
    /**
     * Clear placement grid
     */
    clearPlacementGrid() {
        this.gridGraphics.clear();
    }
    
    /**
     * Get current viewport bounds in world coordinates
     */
    getViewportBounds() {
        if (!this.camera) {
            return { left: 0, right: 800, top: 0, bottom: 600 };
        }
        
        return {
            left: this.camera.x - this.camera.viewWidth / 2,
            right: this.camera.x + this.camera.viewWidth / 2,
            top: this.camera.y - this.camera.viewHeight / 2,
            bottom: this.camera.y + this.camera.viewHeight / 2
        };
    }
    
    /**
     * Update ghost position based on mouse coordinates
     */
    updateGhostPosition(screenX, screenY) {
        if (!this.ghostSprite || !this.buildingData) return;
        
        // Convert screen to world coordinates
        const worldPos = this.camera ? 
            this.camera.screenToWorld(screenX, screenY) : 
            { x: screenX, y: screenY };
        
        this.mousePosition = worldPos;
        
        // Snap to grid if enabled
        if (this.config.snapToGrid) {
            const gridX = Math.floor(worldPos.x / this.config.gridSize) * this.config.gridSize;
            const gridY = Math.floor(worldPos.y / this.config.gridSize) * this.config.gridSize;
            
            this.gridPosition = { x: gridX, y: gridY };
            this.ghostSprite.position.set(gridX, gridY);
        } else {
            this.gridPosition = worldPos;
            this.ghostSprite.position.set(worldPos.x, worldPos.y);
        }
        
        // Validate placement and update visuals
        this.validatePlacement();
        this.updateValidationOverlay();
    }
    
    /**
     * Validate current placement location
     */
    validatePlacement() {
        if (!this.buildingData || !this.gridPosition) {
            this.isValidPlacement = false;
            return;
        }
        
        // Check cache first
        const cacheKey = `${this.gridPosition.x}_${this.gridPosition.y}`;
        const cached = this.validationCache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
            this.isValidPlacement = cached.valid;
            return;
        }
        
        let valid = true;
        const reasons = [];
        
        // 1. Check if position is within world bounds
        if (!this.isWithinWorldBounds(this.gridPosition, this.buildingData)) {
            valid = false;
            reasons.push('Outside world bounds');
        }
        
        // 2. Check for collision with existing buildings
        if (valid && this.hasCollisionWithBuildings(this.gridPosition, this.buildingData)) {
            valid = false;
            reasons.push('Collision with existing building');
        }
        
        // 3. Check terrain suitability
        if (valid && !this.isTerrainSuitable(this.gridPosition, this.buildingData)) {
            valid = false;
            reasons.push('Unsuitable terrain');
        }
        
        // 4. Check resource requirements
        if (valid && this.resourceValidator && !this.resourceValidator.canAfford(this.buildingData.cost)) {
            valid = false;
            reasons.push('Insufficient resources');
        }
        
        // 5. Check power requirements
        if (valid && this.buildingData.powerRequired > 0) {
            const availablePower = this.calculateAvailablePower();
            if (availablePower < this.buildingData.powerRequired) {
                valid = false;
                reasons.push('Insufficient power');
            }
        }
        
        // 6. Check prerequisites
        if (valid && this.buildingData.prerequisites.length > 0) {
            if (!this.hasPrerequisites(this.buildingData.prerequisites)) {
                valid = false;
                reasons.push('Missing prerequisites');
            }
        }
        
        this.isValidPlacement = valid;
        
        // Cache result
        this.validationCache.set(cacheKey, {
            valid: valid,
            reasons: reasons,
            timestamp: Date.now()
        });
        
        // Emit validation event
        this.emit('validationChanged', {
            valid: valid,
            reasons: reasons,
            position: this.gridPosition,
            building: this.currentBuilding
        });
    }
    
    /**
     * Check if position is within world bounds
     */
    isWithinWorldBounds(position, buildingData) {
        // Simple bounds check - can be made more sophisticated
        const width = buildingData.width * this.config.gridSize;
        const height = buildingData.height * this.config.gridSize;
        
        return position.x >= 0 && 
               position.y >= 0 && 
               position.x + width <= 3200 && // World width
               position.y + height <= 3200;   // World height
    }
    
    /**
     * Check for collision with existing buildings
     */
    hasCollisionWithBuildings(position, buildingData) {
        if (!this.world) return false;
        
        // Get all building entities
        const buildings = this.world.entities.filter(entity => 
            entity.hasComponent('BuildingComponent') && entity.active
        );
        
        const buildingRect = {
            x: position.x,
            y: position.y,
            width: buildingData.width * this.config.gridSize,
            height: buildingData.height * this.config.gridSize
        };
        
        // Check overlap with each building
        for (const building of buildings) {
            const transform = building.getComponent('TransformComponent');
            const buildingComp = building.getComponent('BuildingComponent');
            
            if (transform && buildingComp) {
                const existingRect = {
                    x: transform.x,
                    y: transform.y,
                    width: buildingComp.width * this.config.gridSize,
                    height: buildingComp.height * this.config.gridSize
                };
                
                if (this.rectanglesOverlap(buildingRect, existingRect)) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    /**
     * Check if two rectangles overlap
     */
    rectanglesOverlap(rect1, rect2) {
        return !(rect1.x + rect1.width <= rect2.x ||
                rect2.x + rect2.width <= rect1.x ||
                rect1.y + rect1.height <= rect2.y ||
                rect2.y + rect2.height <= rect1.y);
    }
    
    /**
     * Check terrain suitability
     */
    isTerrainSuitable(position, buildingData) {
        // Simple terrain check - in real implementation, check terrain map
        // For now, assume all terrain is suitable for 'clear' requirement
        return buildingData.terrain.includes('clear');
    }
    
    /**
     * Calculate available power from existing buildings
     */
    calculateAvailablePower() {
        if (!this.world) return 100; // Default for testing
        
        let totalPower = 0;
        const buildings = this.world.entities.filter(entity => 
            entity.hasComponent('BuildingComponent') && entity.active
        );
        
        for (const building of buildings) {
            const buildingComp = building.getComponent('BuildingComponent');
            if (buildingComp && buildingComp.power) {
                totalPower += buildingComp.power;
            }
        }
        
        return totalPower;
    }
    
    /**
     * Check if prerequisites are met
     */
    hasPrerequisites(prerequisites) {
        if (!this.world || prerequisites.length === 0) return true;
        
        const buildings = this.world.entities.filter(entity => 
            entity.hasComponent('BuildingComponent') && entity.active
        );
        
        for (const prereq of prerequisites) {
            const hasPrereq = buildings.some(building => {
                const buildingComp = building.getComponent('BuildingComponent');
                return buildingComp && buildingComp.type === prereq;
            });
            
            if (!hasPrereq) return false;
        }
        
        return true;
    }
    
    /**
     * Update validation overlay visuals
     */
    updateValidationOverlay() {
        if (!this.validationOverlay || !this.buildingData) return;
        
        this.validationOverlay.clear();
        
        const width = this.buildingData.width * this.config.gridSize;
        const height = this.buildingData.height * this.config.gridSize;
        const color = this.isValidPlacement ? this.config.validColor : this.config.invalidColor;
        
        // Draw validation border
        this.validationOverlay.lineStyle(3, color, 0.8);
        this.validationOverlay.drawRect(0, 0, width, height);
        
        // Draw validation fill
        this.validationOverlay.beginFill(color, 0.1);
        this.validationOverlay.drawRect(0, 0, width, height);
        this.validationOverlay.endFill();
    }
    
    /**
     * Place the building at current position
     */
    placeBuilding() {
        if (!this.isValidPlacement || !this.buildingData || !this.gridPosition) return;
        
        console.log(`🏗️  Placing ${this.buildingData.name} at (${this.gridPosition.x}, ${this.gridPosition.y})`);
        
        // Create building data
        const buildingInfo = {
            type: this.currentBuilding,
            position: { ...this.gridPosition },
            data: { ...this.buildingData }
        };
        
        // Emit placement event
        this.emit('buildingPlaced', buildingInfo);
        
        // Show placement effect
        this.showPlacementEffect(this.gridPosition);
        
        // Deduct resources if validator is available
        if (this.resourceValidator) {
            this.resourceValidator.deductCost(this.buildingData.cost);
        }
        
        // End placement mode
        this.cancelPlacement();
    }
    
    /**
     * Show invalid placement feedback
     */
    showInvalidPlacementFeedback() {
        if (!this.ghostSprite) return;
        
        // Flash red to indicate invalid placement
        const originalTint = this.ghostSprite.tint;
        this.ghostSprite.tint = 0xff0000;
        
        setTimeout(() => {
            if (this.ghostSprite) {
                this.ghostSprite.tint = originalTint;
            }
        }, 200);
        
        // Show error text briefly
        this.showErrorMessage('Invalid placement location');
    }
    
    /**
     * Show placement effect animation
     */
    showPlacementEffect(position) {
        if (!this.buildingData) return;
        
        // Create effect sprite
        const effect = new PIXI.Graphics();
        effect.lineStyle(4, 0x00ff00, 1);
        effect.drawRect(0, 0, 
            this.buildingData.width * this.config.gridSize,
            this.buildingData.height * this.config.gridSize
        );
        effect.position.set(position.x, position.y);
        effect.zIndex = 20;
        
        this.overlayContainer.addChild(effect);
        
        // Animate effect
        let scale = 0.8;
        let alpha = 1;
        const animate = () => {
            scale += 0.05;
            alpha -= 0.05;
            
            effect.scale.set(scale);
            effect.alpha = alpha;
            
            if (alpha > 0) {
                requestAnimationFrame(animate);
            } else {
                this.overlayContainer.removeChild(effect);
                effect.destroy();
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    /**
     * Show error message
     */
    showErrorMessage(message) {
        // Create error text
        const style = new PIXI.TextStyle({
            fontFamily: 'Arial',
            fontSize: 16,
            fill: 0xff0000,
            align: 'center',
            fontWeight: 'bold'
        });
        
        const errorText = new PIXI.Text(message, style);
        errorText.anchor.set(0.5);
        errorText.position.set(this.mousePosition.x, this.mousePosition.y - 50);
        errorText.zIndex = 25;
        
        this.overlayContainer.addChild(errorText);
        
        // Remove after delay
        setTimeout(() => {
            if (this.overlayContainer.children.includes(errorText)) {
                this.overlayContainer.removeChild(errorText);
                errorText.destroy();
            }
        }, 2000);
    }
    
    /**
     * Rotate building preview (for future use)
     */
    rotateBuildingPreview() {
        // Placeholder for building rotation
        console.log('🔄 Building rotation not yet implemented');
    }
    
    /**
     * Update placement UI (called from game loop)
     */
    update(deltaTime) {
        if (this.isDestroyed || !this.isPlacementMode) return;
        
        // Update grid if camera moved
        if (this.config.showGrid) {
            this.showPlacementGrid();
        }
        
        // Clean old validation cache entries
        const now = Date.now();
        for (const [key, entry] of this.validationCache) {
            if (now - entry.timestamp > this.cacheTimeout * 5) {
                this.validationCache.delete(key);
            }
        }
    }
    
    /**
     * Simple event emitter
     */
    emit(eventType, data) {
        const event = new CustomEvent(`buildingPlacement:${eventType}`, {
            detail: data
        });
        
        if (typeof window !== 'undefined') {
            window.dispatchEvent(event);
        }
    }
    
    /**
     * Get available buildings
     */
    getAvailableBuildings() {
        return Array.from(this.buildingDatabase.values());
    }
    
    /**
     * Check if currently in placement mode
     */
    isInPlacementMode() {
        return this.isPlacementMode;
    }
    
    /**
     * Get current building data
     */
    getCurrentBuildingData() {
        return this.buildingData;
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.isDestroyed) return;
        
        console.log('🗑️ Destroying BuildingPlacementUI...');
        this.isDestroyed = true;
        
        // Cancel any active placement
        this.cancelPlacement();
        
        // Remove event listeners
        if (typeof window !== 'undefined') {
            for (const { type, handler } of this.eventHandlers) {
                window.removeEventListener(type, handler);
            }
        }
        
        // Clear validation cache
        this.validationCache.clear();
        
        // Remove from stage
        if (this.placementContainer.parent) {
            this.placementContainer.parent.removeChild(this.placementContainer);
        }
        
        // Destroy container
        this.placementContainer.destroy({ children: true });
        
        console.log('✅ BuildingPlacementUI destroyed successfully');
    }
}