# Frontend Implementation Context Package - Phase 5

**Target**: UI Architect, UX Architect, UI Debugger  
**Priority**: High - User interaction foundation  
**Dependencies**: Backend SpatialSystem (QuadTree)  
**Performance Target**: <16ms selection, 50+ units, 60+ FPS

## Critical Performance Optimizations Required

### 1. Selection System with Spatial Optimization
```javascript
class UnitSelectionSystem {
  constructor(world, camera, quadTree) {
    this.selectedUnits = new Set();
    this.quadTree = quadTree; // From backend SpatialSystem
    this.selectionThrottleTime = 8; // 120fps selection updates
    this.lastSelectionUpdate = 0;
  }
  
  selectUnit(screenX, screenY, modifiers = {}) {
    const worldPos = this.camera.screenToWorld(screenX, screenY);
    const hitRadius = 20;
    
    // Critical: Use spatial partitioning - O(log n) vs O(n)
    const candidates = this.quadTree.retrieve({
      x: worldPos.x - hitRadius,
      y: worldPos.y - hitRadius,
      width: hitRadius * 2,
      height: hitRadius * 2
    });
    
    // Target: <16ms response time
  }
}
```

### 2. Batched Visual Feedback System
```javascript
class SelectionVisualSystem extends System {
  constructor(world, pixiApp) {
    super(world);
    this.selectionLayer = new PIXI.Container();
    this.indicatorPool = []; // Object pooling
    this.activeIndicators = new Map();
    
    // Pre-create faction textures for sprite batching
    this.createSelectionTextures();
  }
  
  createSelectionTextures() {
    // Faction colors: player(green), enemy(red), ally(blue), neutral(yellow)
    const factions = ['player', 'enemy', 'ally', 'neutral'];
    const colors = [0x00FF00, 0xFF0000, 0x0080FF, 0xFFFF00];
    
    // Use sprite batching vs individual graphics
    // Target: Maintain PixiJS batch efficiency
  }
}
```

### 3. Optimized Input Handling
```javascript
class OptimizedInputHandler extends InputHandler {
  constructor(element, camera) {
    super(element);
    this.inputQueue = [];
    this.maxInputQueueSize = 10;
    this.coordCache = new Map(); // Coordinate transformation caching
    this.mouseSmoothingFactor = 0.8;
    
    // Batch non-critical events in requestAnimationFrame
  }
  
  queueInput(type, event) {
    // Batch mousemove events, process critical events immediately
    // Target: <5ms input processing delay
  }
}
```

## UI Component Integration

### Enhanced Selection Components
```javascript
export class SelectionComponent extends Component {
  constructor() {
    super();
    this.isSelected = false;
    this.isHovered = false;
    this.selectionTime = 0;
    this.faction = 'neutral';
    this.canBeSelected = true;
    this.priority = 0; // For overlapping units
  }
}

export class UIOverlayComponent extends Component {
  constructor() {
    super();
    this.showHealthBar = false;
    this.showSelectionIndicator = false;
    this.uiScale = 1.0;
    this.fadeDistance = 1000; // Distance-based UI culling
  }
}
```

## System Integration Points

### Priority 2: Enhanced SelectionSystem
- **Dependencies**: Backend SpatialSystem (QuadTree)
- **Input**: Optimized InputHandler with event batching
- **Components**: SelectionComponent, InteractionComponent
- **Performance**: <16ms selection response, spatial query optimization

### Priority 6: UIStateSystem
- **Dependencies**: SelectionSystem, Camera
- **Function**: Synchronize UI state, distance-based culling
- **Performance**: 8ms update budget, batch state updates

### Priority 7: SelectionVisualSystem  
- **Dependencies**: UIStateSystem, SelectionComponent
- **Features**: Sprite batching, object pooling, faction colors
- **Performance**: Maintain PixiJS batch efficiency, <2ms render time

### Priority 8: HealthBarSystem
- **Dependencies**: UIStateSystem, HealthComponent
- **Features**: LOD system, damage indicators, pooled graphics
- **Performance**: Show only selected/nearby units, <2ms render time

## Visual Feedback Specifications

### Selection Indicators
- **Faction Colors**: Green (player), Red (enemy), Blue (ally), Yellow (neutral)
- **Visual States**: Selected (solid), Hovered (50% alpha), Preview (animated)
- **Priority Indication**: Veterans (gold), Elites (platinum borders)
- **Formation Lines**: Visual connections for grouped units

### Health Bar System
- **LOD**: Show for selected units or when zoomed in (<500px distance)
- **Color Coding**: Green → Yellow → Red based on health percentage
- **Animation**: Flash red on damage, smooth health transitions
- **Batch Rendering**: Use texture atlas for consistent performance

## Performance Optimization Strategies

### 1. Object Pooling
```javascript
class UIElementPool {
  constructor(createFn, resetFn, initialSize = 50) {
    this.pool = [];
    this.active = new Set();
    
    // Pre-populate pool for selection indicators, health bars
    for (let i = 0; i < initialSize; i++) {
      this.pool.push(createFn());
    }
  }
}
```

### 2. Input Event Batching
- **Critical Events**: mousedown, mouseup (immediate processing)
- **Batched Events**: mousemove (processed in requestAnimationFrame)
- **Throttling**: Drag selection updates at 120fps maximum
- **Coordinate Caching**: Cache screen-to-world transformations per frame

### 3. Visual Culling
- **Distance-based**: Hide UI elements beyond fade distance
- **Camera-based**: Only process entities in viewport + margin
- **Selection-based**: Prioritize selected unit visuals
- **LOD System**: Simplified indicators when zoomed out

## Integration with Existing PixiJS Architecture

### Leverage Existing Systems
- **5-layer rendering**: Add selection to UI layer
- **Camera system**: Use existing screenToWorld conversion
- **Performance monitoring**: Extend draw call tracking
- **ECS integration**: Build on Transform/Sprite components

### Maintain Compatibility  
- **Sprite batching**: Use shared textures for selection indicators
- **Layer system**: Respect existing terrain/units/buildings/effects/UI order
- **Event system**: Extend current InputHandler vs replacing
- **Component patterns**: Follow existing SelectableComponent structure

## Implementation Sequence

1. **Week 1**: Enhanced SelectionSystem with spatial optimization
2. **Week 2**: Selection visual system with sprite batching
3. **Week 3**: Health bar system with LOD and pooling
4. **Week 4**: Optimized input handling with event batching
5. **Week 5**: Performance tuning and visual polish

## Error Handling & Rollback
- **Selection Failures**: Fallback to linear search if QuadTree unavailable
- **Visual Corruption**: Reset object pools and recreate visual elements
- **Input Lag**: Disable batching and process events immediately
- **Performance Issues**: Reduce LOD quality and disable non-essential effects

## Success Validation
- **Response Time**: <16ms for any selection operation
- **Batch Efficiency**: Maintain PixiJS sprite batching
- **Multi-unit**: Handle 50+ unit selection smoothly
- **Memory**: <100MB for UI systems total
- **Integration**: Seamless with existing camera/input systems