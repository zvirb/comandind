# 🖱️ UI/UX EMERGENCY CONTEXT PACKAGE
## Mouse Coordinate & Selection System Crisis (3,000 tokens max)

### CRITICAL MOUSE COORDINATE ISSUE
**Priority 3 Fix Required**: Selection box appears elsewhere after viewport scrolling
- **Symptom**: User clicks one location, selection box appears in different location
- **Impact**: User interaction completely broken, unusable interface
- **Root Cause**: Camera viewport transformation not updating mouse coordinates

### CAMERA VIEWPORT TRANSFORMATION ANALYSIS

#### Expected Camera Class Structure:
```javascript
// Located in: src/core/Camera.js or similar
class Camera {
  constructor() {
    this.x = 0;
    this.y = 0;
    this.zoom = 1;
  }
  
  // CRITICAL METHOD: May be broken
  screenToWorld(screenX, screenY) {
    return {
      x: (screenX / this.zoom) + this.x,
      y: (screenY / this.zoom) + this.y
    };
  }
  
  // Investigation needed: viewport change handling
  updateViewport(deltaX, deltaY) {
    this.x += deltaX;
    this.y += deltaY;
    // Are mouse coordinate transforms updated here?
  }
}
```

### MOUSE EVENT HANDLING PIPELINE

#### Input Handling Chain Investigation:
1. **Mouse Event Capture**: Browser mouse events on canvas
2. **Coordinate Extraction**: Raw screen coordinates from event
3. **Camera Transformation**: screenToWorld() conversion
4. **Game World Coordinates**: Final coordinates for game logic
5. **Selection Box Display**: Visual feedback to user

#### Critical Failure Points:
- **Viewport State**: Does camera store correct viewport position?
- **Transform Timing**: Is transformation called after viewport changes?
- **Coordinate Caching**: Are old coordinates being used?
- **Event Binding**: Are mouse events properly bound to updated camera?

### SELECTION SYSTEM INTERACTION

#### Selection Box Rendering:
```javascript
// Expected pattern in selection system:
class SelectionSystem {
  onMouseDown(screenX, screenY) {
    // CRITICAL: This transformation may be broken
    const worldCoords = camera.screenToWorld(screenX, screenY);
    this.startSelection(worldCoords.x, worldCoords.y);
  }
  
  onMouseMove(screenX, screenY) {
    const worldCoords = camera.screenToWorld(screenX, screenY);
    this.updateSelectionBox(worldCoords.x, worldCoords.y);
  }
}
```

#### Viewport Change Integration:
- **Camera Movement**: User scrolls/pans the viewport
- **Coordinate Update**: Mouse coordinates should reflect new viewport
- **Selection Accuracy**: Selection box should appear where user expects
- **Visual Feedback**: Immediate response to user input

### INPUT HANDLER INVESTIGATION

#### Input Configuration Analysis:
- **Event Listeners**: Are mouse events properly configured?
- **Canvas Binding**: Is mouse input bound to correct canvas element?
- **Coordinate System**: Screen vs world coordinate consistency
- **Transform Matrix**: PixiJS transformation integration

#### Expected Input Flow:
```javascript
class InputHandler {
  handleMouseDown(event) {
    const rect = canvas.getBoundingClientRect();
    const screenX = event.clientX - rect.left;
    const screenY = event.clientY - rect.top;
    
    // CRITICAL POINT: Camera transformation
    const worldCoords = this.camera.screenToWorld(screenX, screenY);
    this.selectionSystem.startSelection(worldCoords);
  }
}
```

### USER INTERACTION FLOW VALIDATION

#### Complete Interaction Sequence:
1. **User clicks** on canvas at visual location
2. **Browser captures** mouse event with screen coordinates
3. **Input handler** extracts coordinates relative to canvas
4. **Camera transforms** screen coordinates to world coordinates
5. **Selection system** uses world coordinates for game logic
6. **Rendering system** displays selection box at world location
7. **User sees** selection box where they expect it

#### Failure Analysis Required:
- **Step 3-4**: Camera transformation accuracy after viewport changes
- **Step 5-6**: Selection system coordinate usage
- **Step 7**: Visual feedback alignment with user expectations

### VIEWPORT SCROLLING INTEGRATION

#### Scrolling Mechanics:
- **Pan Input**: Mouse drag or keyboard arrow keys
- **Camera Update**: Viewport position changes
- **Coordinate System**: World coordinates shift relative to screen
- **Mouse Transform**: screenToWorld must account for new viewport

#### Critical Debug Points:
1. **Camera State**: Log camera x,y position during scrolling
2. **Transform Accuracy**: Verify screenToWorld calculations
3. **Selection Coordinates**: Log world coordinates from mouse input
4. **Box Position**: Compare expected vs actual selection box location

### EMERGENCY FIX STRATEGY

#### Investigation Priority:
1. **Camera State Verification**: Is viewport position correctly stored?
2. **Transform Method Audit**: screenToWorld implementation accuracy
3. **Event Timing**: Are transforms applied immediately after viewport changes?
4. **Coordinate Consistency**: Screen-to-world-to-screen round-trip accuracy

#### Quick Fix Approaches:
- **Transform Refresh**: Force coordinate transform update after camera moves
- **State Synchronization**: Ensure camera state reflects actual viewport
- **Event Rebinding**: Refresh mouse event handlers after viewport changes
- **Coordinate Validation**: Add debugging logs for coordinate transformation

### SUCCESS CRITERIA
✅ Mouse clicks register at expected visual locations
✅ Selection box appears where user clicked
✅ Viewport scrolling doesn't break mouse interaction
✅ Coordinate transformation accurate after camera movement
✅ User can select game elements reliably
✅ No coordinate desync between visual and functional elements

### TOOLS REQUIRED
- **Read**: Camera class, InputHandler, SelectionSystem files
- **Edit**: Fix coordinate transformation and viewport integration
- **Bash**: Test mouse interaction and viewport scrolling
- **Grep**: Search for mouse event handling and coordinate transforms

### COORDINATION
- **Report** coordinate transformation findings to Main Claude
- **Support** game-engine-architect with entity selection integration
- **Coordinate** with user-experience-auditor for interaction testing