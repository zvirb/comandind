# 🎮 GAME ENGINE EMERGENCY CONTEXT PACKAGE
## ECS World Class & Entity Management Crisis (4,000 tokens max)

### IMMEDIATE CRITICAL ERROR
**Priority 1 Fix Required**: `TypeError: this.world.cleanup is not a function`
- **Location**: ECS system attempting to call cleanup on World instance
- **Impact**: Application crashes, prevents game startup
- **Fix Scope**: Add cleanup() method to World class or create alias

### ECS WORLD CLASS ANALYSIS REQUIRED

#### Current World Class Structure Investigation:
```javascript
// Expected in: src/ecs/World.js or similar
class World {
  constructor() {
    this.entities = new Map();
    this.components = new Map(); 
    this.systems = [];
  }
  
  // MISSING: cleanup() method causing the error
  // Required: Implement cleanup to prevent crashes
}
```

#### Entity Creation vs Rendering Pipeline Issue:
**Problem**: Users see "green spinning squares" instead of RTS game elements
**Investigation Required**:
1. **Entity Creation**: Are entities being created but not rendering?
2. **Component Assignment**: Are components properly attached to entities?
3. **Rendering Integration**: Does PixiJS receive proper entity data?
4. **Sprite Creation**: Are sprites being created from entity data?

#### PixiJS Sprite Display System:
```javascript
// Expected integration pattern:
class RenderingSystem {
  update(entities) {
    entities.forEach(entity => {
      // Are sprites being created for each entity?
      // Are sprites added to the stage properly?
      // Do sprites reflect entity component data?
    });
  }
}
```

### COMPONENT SYSTEM INTEGRATION
#### Required Analysis:
- **Position Component**: Entity positioning vs sprite positioning
- **Sprite Component**: Texture assignment and visual representation
- **Transform Component**: Scale, rotation, visibility states
- **Game Object Component**: Unit type, building type, resource type

### ENTITY LIFECYCLE INVESTIGATION
#### Creation Pipeline:
1. **Entity Registration**: `world.createEntity()`
2. **Component Assignment**: `entity.addComponent()`
3. **System Processing**: Systems should process entities
4. **Rendering Update**: Sprites should reflect entity state

#### Missing Link Analysis:
- Are entities created but systems not processing them?
- Are systems processing but not updating sprites?
- Are sprites created but not visible (positioning/layer issues)?
- Are components properly structured for rendering?

### PERFORMANCE METRICS CORRELATION
#### Current Status:
- **Technical Performance**: 64,809 FPS (excellent)
- **Health Checks**: 0.491ms (excellent)
- **User Experience**: BROKEN (only green squares)

#### Investigation Required:
- High performance suggests entity creation is working
- Missing gameplay suggests rendering/display issues
- Need to correlate entity count with sprite count

### CRITICAL DEBUGGING POINTS
1. **Console Errors**: Check for ECS-related errors beyond cleanup
2. **Entity Count**: Verify entities are being created
3. **Component Verification**: Ensure components are properly attached
4. **Sprite Creation**: Verify PixiJS sprites are generated
5. **Stage Addition**: Confirm sprites are added to display stage
6. **Texture Loading**: Verify game textures are loading properly

### EMERGENCY FIX PRIORITY ORDER
1. **Fix cleanup() method** - Immediate crash prevention
2. **Verify entity creation** - Ensure entities exist
3. **Check component attachment** - Verify component system
4. **Investigate sprite rendering** - PixiJS integration
5. **Validate display pipeline** - End-to-end rendering

### SUCCESS CRITERIA
✅ No ECS cleanup errors in console
✅ Entities successfully created in World
✅ Components properly attached to entities
✅ Systems processing entities correctly
✅ PixiJS sprites created and displayed
✅ Game elements visible (not just green squares)
✅ Performance maintained during fixes

### TOOLS REQUIRED
- **Read**: Examine ECS system files and World class
- **Edit**: Fix cleanup method and any integration issues
- **Bash**: Test application startup and error checking
- **Grep**: Search for entity creation and rendering patterns
- **LS/Glob**: Locate ECS system files and dependencies

### COORDINATION
- **Report findings** to Main Claude for integration
- **Coordinate with** codebase-research-analyst for system investigation
- **Support** ui-regression-debugger with entity/sprite correlation
- **Ensure** atomic-git-synchronizer for rollback capability