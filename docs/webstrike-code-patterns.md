# WebStrike Command - Code Patterns & Implementation Examples

## Core Engine Patterns

### Game State Management
```javascript
class GameStateManager {
  constructor() {
    this.currentState = 'menu';
    this.states = new Map();
    this.stateHistory = [];
    this.transitionCallbacks = new Map();
  }
  
  registerState(name, stateObject) {
    this.states.set(name, stateObject);
  }
  
  transition(newState, data = null) {
    const current = this.states.get(this.currentState);
    const next = this.states.get(newState);
    
    // Execute transition callbacks
    const callbacks = this.transitionCallbacks.get(this.currentState + '->' + newState);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
    
    // State cleanup and initialization
    if (current && current.exit) current.exit();
    this.stateHistory.push(this.currentState);
    this.currentState = newState;
    if (next && next.enter) next.enter(data);
  }
  
  update(deltaTime) {
    const state = this.states.get(this.currentState);
    if (state && state.update) {
      state.update(deltaTime);
    }
  }
  
  render(renderer) {
    const state = this.states.get(this.currentState);
    if (state && state.render) {
      state.render(renderer);
    }
  }
}

// Usage example
const stateManager = new GameStateManager();
stateManager.registerState('menu', new MenuState());
stateManager.registerState('game', new GameplayState());
stateManager.registerState('paused', new PauseState());
```

### Entity Component System (ECS)
```javascript
class Entity {
  constructor(id) {
    this.id = id;
    this.components = new Map();
    this.active = true;
  }
  
  addComponent(component) {
    this.components.set(component.constructor.name, component);
    component.entity = this;
    return this;
  }
  
  removeComponent(componentType) {
    const componentName = typeof componentType === 'string' ? 
      componentType : componentType.name;
    
    const component = this.components.get(componentName);
    if (component) {
      this.components.delete(componentName);
      component.entity = null;
    }
    return this;
  }
  
  getComponent(componentType) {
    const componentName = typeof componentType === 'string' ? 
      componentType : componentType.name;
    return this.components.get(componentName);
  }
  
  hasComponent(componentType) {
    const componentName = typeof componentType === 'string' ? 
      componentType : componentType.name;
    return this.components.has(componentName);
  }
}

// Component examples
class PositionComponent {
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
    this.previousX = x;
    this.previousY = y;
  }
}

class VelocityComponent {
  constructor(dx = 0, dy = 0) {
    this.dx = dx;
    this.dy = dy;
  }
}

class SpriteComponent {
  constructor(texture, width = 32, height = 32) {
    this.texture = texture;
    this.width = width;
    this.height = height;
    this.visible = true;
    this.rotation = 0;
    this.scale = 1;
  }
}

// System example
class MovementSystem {
  constructor() {
    this.entities = [];
  }
  
  addEntity(entity) {
    if (entity.hasComponent(PositionComponent) && 
        entity.hasComponent(VelocityComponent)) {
      this.entities.push(entity);
    }
  }
  
  update(deltaTime) {
    for (let entity of this.entities) {
      const position = entity.getComponent(PositionComponent);
      const velocity = entity.getComponent(VelocityComponent);
      
      position.previousX = position.x;
      position.previousY = position.y;
      position.x += velocity.dx * deltaTime;
      position.y += velocity.dy * deltaTime;
    }
  }
}
```

## Rendering Optimization Patterns

### Sprite Batching System
```javascript
class SpriteBatcher {
  constructor(gl, maxSprites = 1000) {
    this.gl = gl;
    this.maxSprites = maxSprites;
    this.vertices = new Float32Array(maxSprites * 6 * 4); // 6 vertices, 4 components
    this.indices = new Uint16Array(maxSprites * 6);
    this.currentTexture = null;
    this.spriteCount = 0;
    this.shader = this.createShader();
    
    // Pre-calculate indices
    this.generateIndices();
    this.createBuffers();
  }
  
  generateIndices() {
    for (let i = 0; i < this.maxSprites; i++) {
      const offset = i * 6;
      const vertexOffset = i * 4;
      
      this.indices[offset] = vertexOffset;
      this.indices[offset + 1] = vertexOffset + 1;
      this.indices[offset + 2] = vertexOffset + 2;
      this.indices[offset + 3] = vertexOffset + 2;
      this.indices[offset + 4] = vertexOffset + 3;
      this.indices[offset + 5] = vertexOffset;
    }
  }
  
  createBuffers() {
    this.vertexBuffer = this.gl.createBuffer();
    this.indexBuffer = this.gl.createBuffer();
    
    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER, this.indexBuffer);
    this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, this.indices, this.gl.STATIC_DRAW);
  }
  
  draw(texture, transform, sourceRect) {
    if (this.currentTexture !== texture || this.spriteCount >= this.maxSprites) {
      this.flush();
      this.currentTexture = texture;
    }
    
    this.addSpriteToBuffer(transform, sourceRect, texture);
    this.spriteCount++;
  }
  
  addSpriteToBuffer(transform, sourceRect, texture) {
    const index = this.spriteCount * 24; // 6 vertices * 4 components
    const {x, y, width, height, rotation} = transform;
    const {sx, sy, sw, sh} = sourceRect;
    
    // Calculate rotated corners
    const cos = Math.cos(rotation);
    const sin = Math.sin(rotation);
    const halfWidth = width * 0.5;
    const halfHeight = height * 0.5;
    
    // Four corners relative to center
    const corners = [
      {x: -halfWidth, y: -halfHeight}, // Top-left
      {x: halfWidth, y: -halfHeight},  // Top-right
      {x: halfWidth, y: halfHeight},   // Bottom-right
      {x: -halfWidth, y: halfHeight}   // Bottom-left
    ];
    
    // UV coordinates
    const u1 = sx / texture.width;
    const v1 = sy / texture.height;
    const u2 = (sx + sw) / texture.width;
    const v2 = (sy + sh) / texture.height;
    const uvs = [
      {u: u1, v: v1}, {u: u2, v: v1},
      {u: u2, v: v2}, {u: u1, v: v2}
    ];
    
    // Transform and add vertices
    for (let i = 0; i < 4; i++) {
      const corner = corners[i];
      const uv = uvs[i];
      
      // Rotate around center
      const rotX = corner.x * cos - corner.y * sin;
      const rotY = corner.x * sin + corner.y * cos;
      
      // Translate to world position
      const worldX = rotX + x;
      const worldY = rotY + y;
      
      // Add to buffer
      const vertIndex = index + i * 4;
      this.vertices[vertIndex] = worldX;
      this.vertices[vertIndex + 1] = worldY;
      this.vertices[vertIndex + 2] = uv.u;
      this.vertices[vertIndex + 3] = uv.v;
    }
  }
  
  flush() {
    if (this.spriteCount === 0) return;
    
    this.gl.useProgram(this.shader.program);
    this.gl.bindTexture(this.gl.TEXTURE_2D, this.currentTexture.glTexture);
    
    this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.vertexBuffer);
    this.gl.bufferData(this.gl.ARRAY_BUFFER, this.vertices, this.gl.DYNAMIC_DRAW);
    
    // Set up vertex attributes
    this.gl.enableVertexAttribArray(this.shader.position);
    this.gl.enableVertexAttribArray(this.shader.texCoord);
    
    this.gl.vertexAttribPointer(this.shader.position, 2, this.gl.FLOAT, false, 16, 0);
    this.gl.vertexAttribPointer(this.shader.texCoord, 2, this.gl.FLOAT, false, 16, 8);
    
    this.gl.drawElements(this.gl.TRIANGLES, this.spriteCount * 6, this.gl.UNSIGNED_SHORT, 0);
    
    this.spriteCount = 0;
  }
}
```

### Camera System with Smooth Following
```javascript
class Camera {
  constructor(viewportWidth, viewportHeight) {
    this.x = 0;
    this.y = 0;
    this.targetX = 0;
    this.targetY = 0;
    this.viewportWidth = viewportWidth;
    this.viewportHeight = viewportHeight;
    this.zoom = 1;
    this.targetZoom = 1;
    this.smoothing = 0.1;
    this.bounds = null;
    this.shake = {x: 0, y: 0, intensity: 0, duration: 0};
  }
  
  setTarget(x, y) {
    this.targetX = x;
    this.targetY = y;
  }
  
  setBounds(minX, minY, maxX, maxY) {
    this.bounds = {minX, minY, maxX, maxY};
  }
  
  setZoom(zoom) {
    this.targetZoom = Math.max(0.1, Math.min(3.0, zoom));
  }
  
  shake(intensity, duration) {
    this.shake.intensity = intensity;
    this.shake.duration = duration;
  }
  
  update(deltaTime) {
    // Smooth camera movement
    const lerpFactor = 1 - Math.pow(1 - this.smoothing, deltaTime * 60);
    
    this.x += (this.targetX - this.x) * lerpFactor;
    this.y += (this.targetY - this.y) * lerpFactor;
    this.zoom += (this.targetZoom - this.zoom) * lerpFactor;
    
    // Apply bounds
    if (this.bounds) {
      const halfWidth = (this.viewportWidth / this.zoom) * 0.5;
      const halfHeight = (this.viewportHeight / this.zoom) * 0.5;
      
      this.x = Math.max(this.bounds.minX + halfWidth, 
                       Math.min(this.bounds.maxX - halfWidth, this.x));
      this.y = Math.max(this.bounds.minY + halfHeight, 
                       Math.min(this.bounds.maxY - halfHeight, this.y));
    }
    
    // Update screen shake
    if (this.shake.duration > 0) {
      this.shake.duration -= deltaTime;
      this.shake.x = (Math.random() - 0.5) * this.shake.intensity;
      this.shake.y = (Math.random() - 0.5) * this.shake.intensity;
    } else {
      this.shake.x = 0;
      this.shake.y = 0;
    }
  }
  
  getTransform() {
    return {
      x: -this.x + this.viewportWidth * 0.5 + this.shake.x,
      y: -this.y + this.viewportHeight * 0.5 + this.shake.y,
      scaleX: this.zoom,
      scaleY: this.zoom
    };
  }
  
  worldToScreen(worldX, worldY) {
    const transform = this.getTransform();
    return {
      x: (worldX + transform.x) * transform.scaleX,
      y: (worldY + transform.y) * transform.scaleY
    };
  }
  
  screenToWorld(screenX, screenY) {
    const transform = this.getTransform();
    return {
      x: (screenX / transform.scaleX) - transform.x,
      y: (screenY / transform.scaleY) - transform.y
    };
  }
}
```

## Pathfinding Implementation

### A* Pathfinding with Binary Heap
```javascript
class AStarPathfinder {
  constructor(grid) {
    this.grid = grid;
    this.openSet = new BinaryHeap(node => node.fCost);
    this.closedSet = new Set();
  }
  
  findPath(startX, startY, endX, endY) {
    this.openSet.clear();
    this.closedSet.clear();
    
    const startNode = this.grid.getNode(startX, startY);
    const endNode = this.grid.getNode(endX, endY);
    
    if (!startNode || !endNode || !endNode.walkable) {
      return null;
    }
    
    startNode.gCost = 0;
    startNode.hCost = this.getDistance(startNode, endNode);
    startNode.fCost = startNode.gCost + startNode.hCost;
    startNode.parent = null;
    
    this.openSet.push(startNode);
    
    while (this.openSet.size() > 0) {
      const currentNode = this.openSet.pop();
      this.closedSet.add(currentNode);
      
      if (currentNode === endNode) {
        return this.retracePath(startNode, endNode);
      }
      
      const neighbors = this.grid.getNeighbors(currentNode);
      
      for (let neighbor of neighbors) {
        if (!neighbor.walkable || this.closedSet.has(neighbor)) {
          continue;
        }
        
        const newGCost = currentNode.gCost + this.getDistance(currentNode, neighbor);
        
        if (newGCost < neighbor.gCost || !this.openSet.contains(neighbor)) {
          neighbor.gCost = newGCost;
          neighbor.hCost = this.getDistance(neighbor, endNode);
          neighbor.fCost = neighbor.gCost + neighbor.hCost;
          neighbor.parent = currentNode;
          
          if (!this.openSet.contains(neighbor)) {
            this.openSet.push(neighbor);
          } else {
            this.openSet.updateItem(neighbor);
          }
        }
      }
    }
    
    return null; // No path found
  }
  
  retracePath(startNode, endNode) {
    const path = [];
    let currentNode = endNode;
    
    while (currentNode !== startNode) {
      path.push({x: currentNode.x, y: currentNode.y});
      currentNode = currentNode.parent;
    }
    
    return path.reverse();
  }
  
  getDistance(nodeA, nodeB) {
    const dx = Math.abs(nodeA.x - nodeB.x);
    const dy = Math.abs(nodeA.y - nodeB.y);
    
    // Diagonal movement cost (14) vs straight (10)
    if (dx > dy) {
      return 14 * dy + 10 * (dx - dy);
    }
    return 14 * dx + 10 * (dy - dx);
  }
}

class BinaryHeap {
  constructor(scoreFunction) {
    this.content = [];
    this.scoreFunction = scoreFunction;
  }
  
  push(element) {
    this.content.push(element);
    this.sinkDown(this.content.length - 1);
  }
  
  pop() {
    const result = this.content[0];
    const end = this.content.pop();
    
    if (this.content.length > 0) {
      this.content[0] = end;
      this.bubbleUp(0);
    }
    
    return result;
  }
  
  size() {
    return this.content.length;
  }
  
  clear() {
    this.content = [];
  }
  
  contains(element) {
    return this.content.indexOf(element) !== -1;
  }
  
  sinkDown(n) {
    const element = this.content[n];
    
    while (n > 0) {
      const parentN = ((n + 1) >> 1) - 1;
      const parent = this.content[parentN];
      
      if (this.scoreFunction(element) < this.scoreFunction(parent)) {
        this.content[parentN] = element;
        this.content[n] = parent;
        n = parentN;
      } else {
        break;
      }
    }
  }
  
  bubbleUp(n) {
    const length = this.content.length;
    const element = this.content[n];
    const elemScore = this.scoreFunction(element);
    
    while (true) {
      const child2N = (n + 1) << 1;
      const child1N = child2N - 1;
      let swap = null;
      let child1Score;
      
      if (child1N < length) {
        const child1 = this.content[child1N];
        child1Score = this.scoreFunction(child1);
        
        if (child1Score < elemScore) {
          swap = child1N;
        }
      }
      
      if (child2N < length) {
        const child2 = this.content[child2N];
        const child2Score = this.scoreFunction(child2);
        
        if (child2Score < (swap === null ? elemScore : child1Score)) {
          swap = child2N;
        }
      }
      
      if (swap !== null) {
        this.content[n] = this.content[swap];
        this.content[swap] = element;
        n = swap;
      } else {
        break;
      }
    }
  }
}
```

### Flow Field Pathfinding
```javascript
class FlowFieldPathfinder {
  constructor(grid) {
    this.grid = grid;
    this.costField = null;
    this.flowField = null;
  }
  
  generateFlowField(goalX, goalY) {
    this.costField = this.generateCostField(goalX, goalY);
    this.flowField = this.generateDirectionField();
    return this.flowField;
  }
  
  generateCostField(goalX, goalY) {
    const width = this.grid.width;
    const height = this.grid.height;
    const costField = new Array(width * height).fill(Infinity);
    const queue = [];
    
    // Set goal cost to 0
    const goalIndex = goalY * width + goalX;
    costField[goalIndex] = 0;
    queue.push({x: goalX, y: goalY, cost: 0});
    
    // Dijkstra's algorithm to fill cost field
    while (queue.length > 0) {
      queue.sort((a, b) => a.cost - b.cost);
      const current = queue.shift();
      
      const neighbors = [
        {x: current.x + 1, y: current.y, cost: 1},
        {x: current.x - 1, y: current.y, cost: 1},
        {x: current.x, y: current.y + 1, cost: 1},
        {x: current.x, y: current.y - 1, cost: 1},
        {x: current.x + 1, y: current.y + 1, cost: 1.4},
        {x: current.x - 1, y: current.y + 1, cost: 1.4},
        {x: current.x + 1, y: current.y - 1, cost: 1.4},
        {x: current.x - 1, y: current.y - 1, cost: 1.4}
      ];
      
      for (let neighbor of neighbors) {
        if (neighbor.x < 0 || neighbor.x >= width || 
            neighbor.y < 0 || neighbor.y >= height) {
          continue;
        }
        
        if (!this.grid.isWalkable(neighbor.x, neighbor.y)) {
          continue;
        }
        
        const neighborIndex = neighbor.y * width + neighbor.x;
        const newCost = current.cost + neighbor.cost;
        
        if (newCost < costField[neighborIndex]) {
          costField[neighborIndex] = newCost;
          queue.push({x: neighbor.x, y: neighbor.y, cost: newCost});
        }
      }
    }
    
    return costField;
  }
  
  generateDirectionField() {
    const width = this.grid.width;
    const height = this.grid.height;
    const flowField = new Array(width * height);
    
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const index = y * width + x;
        
        if (!this.grid.isWalkable(x, y)) {
          flowField[index] = {x: 0, y: 0};
          continue;
        }
        
        let bestDirection = {x: 0, y: 0};
        let lowestCost = this.costField[index];
        
        // Check 8 neighbors
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            
            const nx = x + dx;
            const ny = y + dy;
            
            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
              const neighborIndex = ny * width + nx;
              const neighborCost = this.costField[neighborIndex];
              
              if (neighborCost < lowestCost) {
                lowestCost = neighborCost;
                bestDirection = {x: dx, y: dy};
              }
            }
          }
        }
        
        flowField[index] = bestDirection;
      }
    }
    
    return flowField;
  }
  
  getDirection(x, y) {
    const index = y * this.grid.width + x;
    return this.flowField ? this.flowField[index] : {x: 0, y: 0};
  }
}
```

## Input Handling Patterns

### Command Pattern for Input
```javascript
class Command {
  execute() {}
  undo() {}
}

class MoveCommand extends Command {
  constructor(unit, targetX, targetY) {
    super();
    this.unit = unit;
    this.targetX = targetX;
    this.targetY = targetY;
    this.originalX = unit.x;
    this.originalY = unit.y;
  }
  
  execute() {
    this.unit.moveTo(this.targetX, this.targetY);
  }
  
  undo() {
    this.unit.setPosition(this.originalX, this.originalY);
  }
}

class InputHandler {
  constructor() {
    this.commands = [];
    this.commandHistory = [];
    this.selectedUnits = new Set();
  }
  
  handleInput(inputType, data) {
    switch (inputType) {
      case 'rightClick':
        if (this.selectedUnits.size > 0) {
          const command = new MoveCommand(
            Array.from(this.selectedUnits), 
            data.x, 
            data.y
          );
          this.executeCommand(command);
        }
        break;
        
      case 'leftClick':
        this.handleSelection(data);
        break;
    }
  }
  
  executeCommand(command) {
    command.execute();
    this.commandHistory.push(command);
  }
  
  undo() {
    if (this.commandHistory.length > 0) {
      const command = this.commandHistory.pop();
      command.undo();
    }
  }
}
```