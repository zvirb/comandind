# Frontend Interaction Systems Design for Command and Independent Thought Iteration 2

**Research Date**: August 19, 2025  
**Agent**: WebUI Architect Agent  
**Focus**: High-performance unit selection, visual feedback, and input handling

## Executive Summary

This document presents a comprehensive design for efficient frontend interaction systems optimized for 50+ unit selection while maintaining 60+ FPS performance. The design integrates spatial partitioning algorithms, optimized visual feedback systems, and batched input handling with the existing PixiJS v7.3.3 foundation.

## Current Architecture Analysis

### PixiJS Foundation Strengths
- **5-layer rendering system**: Terrain, buildings, units, effects, UI with proper z-ordering
- **Camera system**: Smooth scrolling, zoom, bounds checking with world/screen coordinate conversion
- **Performance monitoring**: Draw call counting and sprite batching optimization
- **ECS integration**: Components for Transform, Velocity, Sprite, Health, Movement, Combat, AI

### Input System Assessment
- **Event delegation**: Basic mouse/keyboard event handling with listener management
- **Touch support**: Mobile compatibility with touchstart/move/end events
- **Performance gaps**: No event batching, limited coordinate optimization, missing spatial queries

## Unit Selection System Design

### 1. Spatial Partitioning Implementation

```javascript
// QuadTree spatial partition for O(log n) selection performance
class SelectionQuadTree {
    constructor(bounds, maxObjects = 10, maxLevels = 5) {
        this.bounds = bounds; // {x, y, width, height}
        this.maxObjects = maxObjects;
        this.maxLevels = maxLevels;
        this.level = 0;
        this.objects = [];
        this.nodes = [];
    }
    
    // Insert entity with spatial indexing
    insert(entity) {
        if (this.nodes.length > 0) {
            const index = this.getIndex(entity);
            if (index !== -1) {
                this.nodes[index].insert(entity);
                return;
            }
        }
        
        this.objects.push(entity);
        
        if (this.objects.length > this.maxObjects && this.level < this.maxLevels) {
            if (this.nodes.length === 0) {
                this.split();
            }
            
            // Redistribute objects to child nodes
            let i = 0;
            while (i < this.objects.length) {
                const index = this.getIndex(this.objects[i]);
                if (index !== -1) {
                    this.nodes[index].insert(this.objects.splice(i, 1)[0]);
                } else {
                    i++;
                }
            }
        }
    }
    
    // Efficient range query for selection rectangle
    retrieve(bounds) {
        const returnObjects = [...this.objects];
        
        if (this.nodes.length > 0) {
            const index = this.getIndex(bounds);
            if (index !== -1) {
                returnObjects.push(...this.nodes[index].retrieve(bounds));
            } else {
                // Check all quadrants if bounds crosses boundaries
                for (let i = 0; i < this.nodes.length; i++) {
                    returnObjects.push(...this.nodes[i].retrieve(bounds));
                }
            }
        }
        
        return returnObjects;
    }
}
```

### 2. Multi-Selection Algorithm

```javascript
class UnitSelectionSystem {
    constructor(world, camera, quadTree) {
        this.world = world;
        this.camera = camera;
        this.quadTree = quadTree;
        this.selectedUnits = new Set();
        this.selectionStartPos = null;
        this.selectionEndPos = null;
        this.isDragging = false;
        
        // Performance optimization: < 16ms response time
        this.selectionThrottleTime = 8; // 120fps for selection updates
        this.lastSelectionUpdate = 0;
    }
    
    // Single unit selection with hit testing optimization
    selectUnit(screenX, screenY, modifiers = {}) {
        const worldPos = this.camera.screenToWorld(screenX, screenY);
        const hitRadius = 20; // Selection tolerance in world units
        
        // Use spatial partitioning for efficient hit testing
        const candidates = this.quadTree.retrieve({
            x: worldPos.x - hitRadius,
            y: worldPos.y - hitRadius,
            width: hitRadius * 2,
            height: hitRadius * 2
        });
        
        let nearestUnit = null;
        let nearestDistance = hitRadius;
        
        for (const entity of candidates) {
            const transform = entity.getComponent(TransformComponent);
            const distance = Math.sqrt(
                Math.pow(transform.x - worldPos.x, 2) + 
                Math.pow(transform.y - worldPos.y, 2)
            );
            
            if (distance < nearestDistance) {
                nearestUnit = entity;
                nearestDistance = distance;
            }
        }
        
        if (nearestUnit) {
            this.handleUnitSelection(nearestUnit, modifiers);
        } else if (!modifiers.additive) {
            this.clearSelection();
        }
    }
    
    // Multi-unit drag selection with performance throttling
    startDragSelection(screenX, screenY) {
        this.selectionStartPos = this.camera.screenToWorld(screenX, screenY);
        this.isDragging = true;
    }
    
    updateDragSelection(screenX, screenY) {
        if (!this.isDragging) return;
        
        const now = performance.now();
        if (now - this.lastSelectionUpdate < this.selectionThrottleTime) {
            return; // Throttle updates for performance
        }
        this.lastSelectionUpdate = now;
        
        this.selectionEndPos = this.camera.screenToWorld(screenX, screenY);
        
        // Calculate selection rectangle
        const bounds = this.getSelectionBounds();
        
        // Use spatial partitioning for efficient rectangle selection
        const candidates = this.quadTree.retrieve(bounds);
        const unitsInSelection = new Set();
        
        for (const entity of candidates) {
            const transform = entity.getComponent(TransformComponent);
            if (this.pointInBounds(transform.x, transform.y, bounds)) {
                unitsInSelection.add(entity);
            }
        }
        
        // Update preview selection
        this.previewSelection = unitsInSelection;
    }
    
    completeDragSelection(modifiers = {}) {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        
        if (this.previewSelection) {
            if (!modifiers.additive) {
                this.clearSelection();
            }
            
            for (const unit of this.previewSelection) {
                this.selectedUnits.add(unit);
            }
            
            this.previewSelection = null;
            this.updateSelectionComponents();
        }
    }
    
    // Group selection management (Ctrl+click, Shift+click)
    handleUnitSelection(unit, modifiers) {
        if (modifiers.additive) {
            if (this.selectedUnits.has(unit)) {
                this.selectedUnits.delete(unit);
            } else {
                this.selectedUnits.add(unit);
            }
        } else if (modifiers.groupSelect) {
            this.selectedUnits.add(unit);
        } else {
            this.clearSelection();
            this.selectedUnits.add(unit);
        }
        
        this.updateSelectionComponents();
    }
}
```

## Visual Feedback Systems

### 1. Selection Indicators with Sprite Batching

```javascript
class SelectionVisualSystem extends System {
    constructor(world, pixiApp) {
        super(world);
        this.requiredComponents = [TransformComponent, SelectionComponent];
        this.pixiApp = pixiApp;
        
        // Create selection graphics container for batching
        this.selectionLayer = new PIXI.Container();
        this.selectionLayer.name = 'selection-indicators';
        pixiApp.stage.addChild(this.selectionLayer);
        
        // Pool selection indicators for performance
        this.indicatorPool = [];
        this.activeIndicators = new Map();
        
        // Selection ring texture for sprite batching
        this.createSelectionTextures();
    }
    
    createSelectionTextures() {
        // Create faction-colored selection ring textures
        this.selectionTextures = new Map();
        const factions = ['player', 'enemy', 'ally', 'neutral'];
        const colors = [0x00FF00, 0xFF0000, 0x0080FF, 0xFFFF00];
        
        factions.forEach((faction, index) => {
            const graphics = new PIXI.Graphics();
            graphics.beginFill(colors[index], 0.3);
            graphics.lineStyle(2, colors[index], 1.0);
            graphics.drawCircle(32, 32, 30);
            graphics.endFill();
            
            const texture = this.pixiApp.renderer.generateTexture(graphics);
            this.selectionTextures.set(faction, texture);
            graphics.destroy();
        });
    }
    
    onEntityAdded(entity) {
        const selection = entity.getComponent(SelectionComponent);
        if (selection.isSelected) {
            this.createSelectionIndicator(entity);
        }
    }
    
    onEntityRemoved(entity) {
        this.removeSelectionIndicator(entity);
    }
    
    // Efficient selection indicator management with object pooling
    createSelectionIndicator(entity) {
        const transform = entity.getComponent(TransformComponent);
        const selection = entity.getComponent(SelectionComponent);
        
        let indicator;
        if (this.indicatorPool.length > 0) {
            indicator = this.indicatorPool.pop();
        } else {
            const texture = this.selectionTextures.get(selection.faction);
            indicator = new PIXI.Sprite(texture);
            indicator.anchor.set(0.5);
        }
        
        indicator.x = transform.x;
        indicator.y = transform.y;
        indicator.alpha = selection.isSelected ? 1.0 : 0.5;
        indicator.visible = true;
        
        this.selectionLayer.addChild(indicator);
        this.activeIndicators.set(entity.id, indicator);
    }
    
    render(interpolation) {
        // Update selection indicator positions with interpolation
        for (const entity of this.entities) {
            const transform = entity.getComponent(TransformComponent);
            const selection = entity.getComponent(SelectionComponent);
            const indicator = this.activeIndicators.get(entity.id);
            
            if (indicator) {
                const interpolated = transform.getInterpolated(interpolation);
                indicator.x = interpolated.x;
                indicator.y = interpolated.y;
                indicator.alpha = selection.isSelected ? 1.0 : 0.5;
            }
        }
    }
}
```

### 2. Health Bar Rendering System

```javascript
class HealthBarSystem extends System {
    constructor(world, pixiApp) {
        super(world);
        this.requiredComponents = [TransformComponent, HealthComponent];
        this.pixiApp = pixiApp;
        
        // Create health bar layer above units
        this.healthBarLayer = new PIXI.Container();
        this.healthBarLayer.name = 'health-bars';
        pixiApp.layers.ui.addChild(this.healthBarLayer);
        
        // Health bar object pool
        this.healthBarPool = [];
        this.activeHealthBars = new Map();
        
        // Pre-create health bar graphics for batching
        this.createHealthBarTextures();
    }
    
    createHealthBarTextures() {
        // Background bar texture
        const bgGraphics = new PIXI.Graphics();
        bgGraphics.beginFill(0x000000, 0.7);
        bgGraphics.drawRoundedRect(0, 0, 32, 4, 2);
        bgGraphics.endFill();
        this.healthBarBgTexture = this.pixiApp.renderer.generateTexture(bgGraphics);
        bgGraphics.destroy();
        
        // Health fill textures (green to red gradient)
        this.healthFillTextures = [];
        const healthLevels = 10;
        for (let i = 0; i < healthLevels; i++) {
            const ratio = i / (healthLevels - 1);
            const red = Math.floor(255 * (1 - ratio));
            const green = Math.floor(255 * ratio);
            const color = (red << 16) | (green << 8) | 0;
            
            const fillGraphics = new PIXI.Graphics();
            fillGraphics.beginFill(color, 1.0);
            fillGraphics.drawRoundedRect(1, 1, 30, 2, 1);
            fillGraphics.endFill();
            
            this.healthFillTextures.push(
                this.pixiApp.renderer.generateTexture(fillGraphics)
            );
            fillGraphics.destroy();
        }
    }
    
    onEntityAdded(entity) {
        this.createHealthBar(entity);
    }
    
    onEntityRemoved(entity) {
        this.removeHealthBar(entity);
    }
    
    createHealthBar(entity) {
        let healthBar;
        if (this.healthBarPool.length > 0) {
            healthBar = this.healthBarPool.pop();
        } else {
            healthBar = {
                background: new PIXI.Sprite(this.healthBarBgTexture),
                fill: new PIXI.Sprite(this.healthFillTextures[9])
            };
            
            healthBar.background.addChild(healthBar.fill);
        }
        
        const transform = entity.getComponent(TransformComponent);
        healthBar.background.x = transform.x - 16;
        healthBar.background.y = transform.y - 25;
        
        this.healthBarLayer.addChild(healthBar.background);
        this.activeHealthBars.set(entity.id, healthBar);
    }
    
    render(interpolation) {
        for (const entity of this.entities) {
            const transform = entity.getComponent(TransformComponent);
            const health = entity.getComponent(HealthComponent);
            const healthBar = this.activeHealthBars.get(entity.id);
            
            if (healthBar) {
                const interpolated = transform.getInterpolated(interpolation);
                
                // Update position
                healthBar.background.x = interpolated.x - 16;
                healthBar.background.y = interpolated.y - 25;
                
                // Update health fill
                const healthRatio = health.current / health.maximum;
                const textureIndex = Math.floor(healthRatio * 9);
                healthBar.fill.texture = this.healthFillTextures[textureIndex];
                healthBar.fill.scale.x = healthRatio;
                
                // Hide health bar if at full health
                healthBar.background.visible = healthRatio < 1.0;
            }
        }
    }
}
```

## Input Handling Optimization

### 1. Event Batching and Coordinate Transformation

```javascript
class OptimizedInputHandler extends InputHandler {
    constructor(element, camera) {
        super(element);
        this.camera = camera;
        
        // Input batching for performance
        this.inputQueue = [];
        this.isProcessingInput = false;
        this.maxInputQueueSize = 10;
        
        // Coordinate transformation caching
        this.coordCache = new Map();
        this.coordCacheFrame = 0;
        
        // Mouse position smoothing for responsive feel
        this.smoothedMousePos = { x: 0, y: 0 };
        this.mouseSmoothingFactor = 0.8;
        
        this.setupOptimizedEventListeners();
    }
    
    setupOptimizedEventListeners() {
        // Use requestAnimationFrame for batched input processing
        const processInputBatch = () => {
            if (this.inputQueue.length > 0) {
                const batchedInputs = this.inputQueue.splice(0);
                this.processBatchedInputs(batchedInputs);
            }
            requestAnimationFrame(processInputBatch);
        };
        requestAnimationFrame(processInputBatch);
        
        // High-frequency mouse move event with throttling
        this.element.addEventListener('mousemove', (e) => {
            this.queueInput('mousemove', e);
        }, { passive: true });
        
        // Critical events processed immediately
        this.element.addEventListener('mousedown', (e) => {
            this.processInputImmediate('mousedown', e);
        });
        
        this.element.addEventListener('mouseup', (e) => {
            this.processInputImmediate('mouseup', e);
        });
    }
    
    queueInput(type, event) {
        // Batch non-critical inputs for performance
        if (this.inputQueue.length >= this.maxInputQueueSize) {
            this.inputQueue.shift(); // Remove oldest input
        }
        
        this.inputQueue.push({
            type,
            event: {
                clientX: event.clientX,
                clientY: event.clientY,
                button: event.button,
                ctrlKey: event.ctrlKey,
                shiftKey: event.shiftKey,
                timestamp: performance.now()
            }
        });
    }
    
    processInputImmediate(type, event) {
        const worldPos = this.getWorldPosition(event.clientX, event.clientY);
        
        // Smooth mouse position for responsive feel
        this.smoothedMousePos.x = this.smoothedMousePos.x * this.mouseSmoothingFactor + 
                                  worldPos.x * (1 - this.mouseSmoothingFactor);
        this.smoothedMousePos.y = this.smoothedMousePos.y * this.mouseSmoothingFactor + 
                                  worldPos.y * (1 - this.mouseSmoothingFactor);
        
        this.emit(type, {
            ...event,
            worldX: worldPos.x,
            worldY: worldPos.y,
            smoothedWorldX: this.smoothedMousePos.x,
            smoothedWorldY: this.smoothedMousePos.y
        });
    }
    
    processBatchedInputs(inputs) {
        // Process only the latest mousemove event to reduce computation
        const latestMouseMove = inputs.filter(input => input.type === 'mousemove').pop();
        
        if (latestMouseMove) {
            const worldPos = this.getWorldPosition(
                latestMouseMove.event.clientX, 
                latestMouseMove.event.clientY
            );
            
            this.mousePosition.x = latestMouseMove.event.clientX;
            this.mousePosition.y = latestMouseMove.event.clientY;
            
            this.emit('mousemove', {
                ...latestMouseMove.event,
                worldX: worldPos.x,
                worldY: worldPos.y
            });
        }
    }
    
    // Cached coordinate transformation for performance
    getWorldPosition(screenX, screenY) {
        const frameKey = `${this.coordCacheFrame}_${screenX}_${screenY}`;
        
        if (this.coordCache.has(frameKey)) {
            return this.coordCache.get(frameKey);
        }
        
        const worldPos = this.camera.screenToWorld(screenX, screenY);
        this.coordCache.set(frameKey, worldPos);
        
        return worldPos;
    }
    
    // Clear coordinate cache each frame
    onFrameStart() {
        this.coordCacheFrame++;
        this.coordCache.clear();
    }
}
```

## ECS Integration Strategy

### 1. UI State Components

```javascript
// Selection component for tracking selection state
class SelectionComponent extends Component {
    constructor() {
        super();
        this.isSelected = false;
        this.isHovered = false;
        this.selectionTime = 0;
        this.faction = 'neutral';
        this.canBeSelected = true;
    }
}

// UI overlay component for health bars, selection indicators
class UIOverlayComponent extends Component {
    constructor() {
        super();
        this.showHealthBar = false;
        this.showSelectionIndicator = false;
        this.showStatusEffects = false;
        this.uiScale = 1.0;
        this.fadeDistance = 1000; // Distance at which UI elements fade
    }
}

// Input interaction component for hit testing
class InteractionComponent extends Component {
    constructor() {
        super();
        this.hitRadius = 20;
        this.interactionLayer = 'units';
        this.priority = 0; // For handling overlapping units
        this.isInteractable = true;
    }
}
```

### 2. UI State Synchronization System

```javascript
class UIStateSystem extends System {
    constructor(world, selectionSystem, camera) {
        super(world);
        this.requiredComponents = [TransformComponent, UIOverlayComponent];
        this.selectionSystem = selectionSystem;
        this.camera = camera;
        this.priority = 8; // Run before rendering systems
    }
    
    update(deltaTime) {
        const cameraPos = { x: this.camera.x, y: this.camera.y };
        const viewDistance = Math.max(this.camera.screenWidth, this.camera.screenHeight) / this.camera.scale;
        
        for (const entity of this.entities) {
            const transform = entity.getComponent(TransformComponent);
            const uiOverlay = entity.getComponent(UIOverlayComponent);
            const selection = entity.getComponent(SelectionComponent);
            
            // Distance-based UI element culling
            const distance = Math.sqrt(
                Math.pow(transform.x - cameraPos.x, 2) + 
                Math.pow(transform.y - cameraPos.y, 2)
            );
            
            // Update UI element visibility based on distance and selection
            const isNearCamera = distance < viewDistance;
            const isSelected = selection?.isSelected || false;
            
            uiOverlay.showHealthBar = isNearCamera && (isSelected || distance < uiOverlay.fadeDistance * 0.5);
            uiOverlay.showSelectionIndicator = isSelected;
            uiOverlay.uiScale = Math.max(0.5, Math.min(1.0, 1.0 - (distance / uiOverlay.fadeDistance)));
            
            // Sync with selection system
            if (selection && this.selectionSystem.selectedUnits.has(entity)) {
                selection.isSelected = true;
                selection.selectionTime = performance.now();
            } else if (selection) {
                selection.isSelected = false;
            }
        }
    }
}
```

## Performance Optimization Techniques

### 1. Object Pooling for UI Elements

```javascript
class UIElementPool {
    constructor(createFunction, resetFunction, initialSize = 50) {
        this.createFunction = createFunction;
        this.resetFunction = resetFunction;
        this.pool = [];
        this.active = new Set();
        
        // Pre-populate pool
        for (let i = 0; i < initialSize; i++) {
            this.pool.push(createFunction());
        }
    }
    
    acquire() {
        let element;
        if (this.pool.length > 0) {
            element = this.pool.pop();
        } else {
            element = this.createFunction();
        }
        
        this.active.add(element);
        return element;
    }
    
    release(element) {
        if (this.active.has(element)) {
            this.active.delete(element);
            this.resetFunction(element);
            this.pool.push(element);
        }
    }
    
    releaseAll() {
        for (const element of this.active) {
            this.resetFunction(element);
            this.pool.push(element);
        }
        this.active.clear();
    }
}
```

### 2. Spatial Query Optimization

```javascript
class SpatialQueryManager {
    constructor() {
        this.queryCache = new Map();
        this.cacheValidFrames = 3;
        this.currentFrame = 0;
    }
    
    // Cached spatial queries for repeated selection operations
    getCachedQuery(bounds, queryType) {
        const key = `${queryType}_${bounds.x}_${bounds.y}_${bounds.width}_${bounds.height}`;
        const cached = this.queryCache.get(key);
        
        if (cached && this.currentFrame - cached.frame < this.cacheValidFrames) {
            return cached.result;
        }
        
        return null;
    }
    
    setCachedQuery(bounds, queryType, result) {
        const key = `${queryType}_${bounds.x}_${bounds.y}_${bounds.width}_${bounds.height}`;
        this.queryCache.set(key, {
            result: [...result],
            frame: this.currentFrame
        });
    }
    
    onFrameStart() {
        this.currentFrame++;
        
        // Clean old cache entries
        if (this.currentFrame % 60 === 0) {
            for (const [key, cached] of this.queryCache.entries()) {
                if (this.currentFrame - cached.frame >= this.cacheValidFrames) {
                    this.queryCache.delete(key);
                }
            }
        }
    }
}
```

## Implementation Integration Plan

### Phase 1: Core Selection System (Week 1)
1. Implement QuadTree spatial partitioning
2. Create SelectionComponent and basic selection logic
3. Integrate with existing InputHandler
4. Add unit hit testing with spatial optimization

### Phase 2: Visual Feedback (Week 2)
1. Implement SelectionVisualSystem with sprite batching
2. Create HealthBarSystem with object pooling
3. Add faction-colored selection indicators
4. Optimize rendering performance to maintain 60+ FPS

### Phase 3: Advanced Input Handling (Week 3)
1. Implement OptimizedInputHandler with event batching
2. Add drag selection with performance throttling
3. Create coordinate transformation caching
4. Integrate with camera system for world/screen conversion

### Phase 4: ECS Integration & Polish (Week 4)
1. Implement UIStateSystem for state synchronization
2. Add UIOverlayComponent for advanced UI management
3. Create SpatialQueryManager for performance optimization
4. Performance testing with 50+ units

## Success Metrics

### Performance Targets
- **Selection Response Time**: < 16ms (60+ FPS maintained)
- **Multi-unit Selection**: Handle 50+ units efficiently
- **Memory Usage**: < 100MB for UI systems
- **Draw Call Optimization**: Maintain sprite batching efficiency

### Functional Requirements
- Single unit selection with left-click
- Multi-unit drag rectangle selection
- Group selection with Ctrl+click, Shift+click
- Visual feedback with faction-colored indicators
- Health bar rendering with damage indication
- Touch support for mobile compatibility

### Integration Success
- Seamless ECS component integration
- Maintained 60+ FPS with 50+ selectable units
- Responsive input handling with < 16ms latency
- Sprite batching preservation for visual elements

This comprehensive design provides a robust foundation for high-performance frontend interactions while maintaining the existing PixiJS architecture's strengths and addressing the specific requirements for Command and Independent Thought Iteration 2.