# Backend Implementation Context Package - Phase 5

**Target**: Backend Gateway Expert, Schema Database Expert, Performance Profiler  
**Priority**: Critical - Core performance foundation  
**Dependencies**: None (foundational)  
**Performance Target**: 50+ units, <5ms pathfinding, 60+ FPS

## Critical Performance Optimizations Required

### 1. Spatial Partitioning (MANDATORY)
```javascript
// QuadTree implementation for O(log n) vs O(n) queries
class SpatialQuadTree {
  constructor(bounds, maxObjects = 10, maxLevels = 5) {
    this.bounds = bounds;
    this.maxObjects = maxObjects;
    this.maxLevels = maxLevels;
    this.objects = [];
    this.nodes = [];
  }
  
  insert(entity) {
    // Critical: Reduces selection from O(n) to O(log n)
    // PathfindingSystem already has 128px spatial grid - extend this
  }
  
  retrieve(bounds) {
    // Used by SelectionSystem and CollisionDetection
    // Target: <1ms for 200+ entities
  }
}
```

### 2. A* Pathfinding with Binary Heap
```javascript
class AStarPathfinder {
  constructor(grid) {
    this.grid = grid;
    this.openSet = new BinaryHeap(node => node.fCost);
    this.pathCache = new Map(); // 500 path cache limit
  }
  
  findPath(startX, startY, endX, endY) {
    // Target: <5ms per path calculation
    // Use existing PathfindingSystem patterns
    // Time-slice with 8ms budget per frame
  }
}
```

### 3. ECS Component Extensions
```javascript
// Add to existing Component.js
export class ResourceComponent extends Component {
  constructor(resourceType, amount, maxAmount) {
    super();
    this.resourceType = resourceType; // 'tiberium'
    this.amount = amount;
    this.maxAmount = maxAmount || amount;
    this.regenerationRate = 0.1; // bails per second
    this.harvestable = true;
  }
}

export class HarvesterAIComponent extends Component {
  constructor() {
    super();
    this.state = 'IDLE'; // IDLE, SEEKING, HARVESTING, RETURNING, UNLOADING
    this.currentCredits = 0;
    this.maxCapacity = 700; // C&C authentic
    this.harvestRate = 25; // credits per second
    this.assignedRefinery = null;
    this.targetField = null;
    this.efficiencyScore = 1.0;
  }
}

export class InteractionComponent extends Component {
  constructor() {
    super();
    this.hitRadius = 20;
    this.selectionLayer = 'units';
    this.priority = 0;
    this.isInteractable = true;
  }
}
```

## System Integration Points

### Priority 0: SpatialSystem (Foundational)
- **Input**: All entities with TransformComponent
- **Output**: QuadTree for spatial queries, getNearbyEntities()
- **Integration**: PathfindingSystem, SelectionSystem, CollisionSystem
- **Performance**: 128px grid cells, <2ms update time

### Priority 1: Enhanced PathfindingSystem 
- **Extend existing**: PathfindingSystem.js already has excellent foundation
- **Add**: Binary heap optimization, path caching (500 paths), flow fields
- **Integration**: GroupMovementSystem, HarvesterAISystem
- **Performance**: <5ms per path, 3 paths per frame max

### Priority 4: HarvesterAISystem
- **Dependencies**: SpatialSystem, PathfindingSystem, EconomicSystem
- **Components**: HarvesterAIComponent, ResourceComponent
- **State Machine**: IDLE → SEEKING → HARVESTING → RETURNING → UNLOADING
- **Performance**: 10Hz update rate, batch processing 50 harvesters

### Priority 5: EconomicSystem
- **Components**: EconomicComponent, ResourceComponent
- **Features**: Credit tracking, transaction validation, Tiberium mechanics
- **Integration**: HarvesterAISystem, ConstructionSystem
- **Performance**: 20Hz credit calculation, 1KB/sec network sync

## Implementation Sequence

1. **Week 1**: Extend existing PathfindingSystem with binary heap and caching
2. **Week 2**: Create SpatialSystem using PathfindingSystem spatial patterns  
3. **Week 3**: Implement HarvesterAISystem with state machine
4. **Week 4**: Add EconomicSystem with authentic C&C mechanics
5. **Week 5**: Performance optimization and batch processing

## Critical Technical Specifications

### Tiberium Economics (C&C Authentic)
```javascript
const TIBERIUM_CONSTANTS = {
  BAIL_VALUE: 25,           // Credits per bail
  HARVESTER_CAPACITY: 700,  // 28 bails total
  HARVEST_RATE: 25,         // Credits per second
  REFINERY_UNLOAD_TIME: 3000, // 3 seconds
  FIELD_REGENERATION: 0.1   // Bails per second
};
```

### Performance Targets
- **Pathfinding**: <5ms per unit, 3 requests per frame max
- **Spatial Queries**: <1ms for 50 units in 200px radius
- **AI Updates**: <3ms for 50 harvesters at 10Hz
- **Memory**: <50MB for backend systems
- **Network**: <1KB/sec per player for economic sync

### Integration with Existing Code
- **Leverage**: PathfindingSystem spatial grid (128px cells)
- **Extend**: Existing ECS Component.js and System.js
- **Maintain**: Performance patterns from PathfindingSystem
- **Preserve**: MovementComponent, TransformComponent integration

## Error Handling & Rollback
- **Pathfinding Failures**: Fallback to direct movement
- **AI State Corruption**: Reset to IDLE state with efficiency penalty
- **Resource Depletion**: Dynamic field discovery and load balancing
- **Performance Degradation**: Adaptive batch sizing and frame budgets

## Success Validation
- **Unit Test**: A* algorithm correctness, path optimization
- **Load Test**: 50+ units pathfinding simultaneously 
- **Performance Test**: Maintain 60 FPS with full economic activity
- **Integration Test**: Harvester → Refinery → Credit flow validation