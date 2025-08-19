# WebStrike Command - Performance Optimization

## Sprite Batching Optimization

```javascript
class SpriteBatcher {
  constructor(gl, maxSprites = 1000) {
    this.gl = gl;
    this.maxSprites = maxSprites;
    this.vertices = new Float32Array(maxSprites * 6 * 4); // 6 vertices, 4 components each
    this.indices = new Uint16Array(maxSprites * 6);
    this.currentTexture = null;
    this.spriteCount = 0;
    
    // Pre-calculate indices for all sprites
    for (let i = 0; i < maxSprites; i++) {
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
  
  draw(texture, x, y, width, height, srcX, srcY, srcW, srcH) {
    if (this.currentTexture !== texture || this.spriteCount >= this.maxSprites) {
      this.flush();
      this.currentTexture = texture;
    }
    
    const index = this.spriteCount * 24; // 6 vertices * 4 components
    
    // Top-left vertex
    this.vertices[index] = x;
    this.vertices[index + 1] = y;
    this.vertices[index + 2] = srcX / texture.width;
    this.vertices[index + 3] = srcY / texture.height;
    
    // Top-right vertex
    this.vertices[index + 4] = x + width;
    this.vertices[index + 5] = y;
    this.vertices[index + 6] = (srcX + srcW) / texture.width;
    this.vertices[index + 7] = srcY / texture.height;
    
    // Bottom-right vertex
    this.vertices[index + 8] = x + width;
    this.vertices[index + 9] = y + height;
    this.vertices[index + 10] = (srcX + srcW) / texture.width;
    this.vertices[index + 11] = (srcY + srcH) / texture.height;
    
    // Bottom-left vertex
    this.vertices[index + 12] = x;
    this.vertices[index + 13] = y + height;
    this.vertices[index + 14] = srcX / texture.width;
    this.vertices[index + 15] = (srcY + srcH) / texture.height;
    
    this.spriteCount++;
  }
  
  flush() {
    if (this.spriteCount === 0) return;
    
    // Upload vertices to GPU and draw
    this.gl.bufferData(this.gl.ARRAY_BUFFER, this.vertices, this.gl.DYNAMIC_DRAW);
    this.gl.drawElements(this.gl.TRIANGLES, this.spriteCount * 6, this.gl.UNSIGNED_SHORT, 0);
    
    this.spriteCount = 0;
  }
}
```

## Quadtree Spatial Indexing

```javascript
class Quadtree {
  constructor(bounds, maxObjects = 10, maxLevels = 5, level = 0) {
    this.maxObjects = maxObjects;
    this.maxLevels = maxLevels;
    this.level = level;
    this.bounds = bounds; // {x, y, width, height}
    this.objects = [];
    this.nodes = [];
  }
  
  clear() {
    this.objects = [];
    for (let node of this.nodes) {
      node.clear();
    }
    this.nodes = [];
  }
  
  split() {
    const subWidth = this.bounds.width / 2;
    const subHeight = this.bounds.height / 2;
    const x = this.bounds.x;
    const y = this.bounds.y;
    
    this.nodes[0] = new Quadtree({
      x: x + subWidth, y: y, width: subWidth, height: subHeight
    }, this.maxObjects, this.maxLevels, this.level + 1);
    
    this.nodes[1] = new Quadtree({
      x: x, y: y, width: subWidth, height: subHeight
    }, this.maxObjects, this.maxLevels, this.level + 1);
    
    this.nodes[2] = new Quadtree({
      x: x, y: y + subHeight, width: subWidth, height: subHeight
    }, this.maxObjects, this.maxLevels, this.level + 1);
    
    this.nodes[3] = new Quadtree({
      x: x + subWidth, y: y + subHeight, width: subWidth, height: subHeight
    }, this.maxObjects, this.maxLevels, this.level + 1);
  }
  
  getIndex(obj) {
    const index = -1;
    const verticalMidpoint = this.bounds.x + (this.bounds.width / 2);
    const horizontalMidpoint = this.bounds.y + (this.bounds.height / 2);
    
    const topQuadrant = (obj.y < horizontalMidpoint && obj.y + obj.height < horizontalMidpoint);
    const bottomQuadrant = (obj.y > horizontalMidpoint);
    
    if (obj.x < verticalMidpoint && obj.x + obj.width < verticalMidpoint) {
      if (topQuadrant) return 1;
      else if (bottomQuadrant) return 2;
    } else if (obj.x > verticalMidpoint) {
      if (topQuadrant) return 0;
      else if (bottomQuadrant) return 3;
    }
    
    return index;
  }
  
  insert(obj) {
    if (this.nodes.length > 0) {
      const index = this.getIndex(obj);
      if (index !== -1) {
        this.nodes[index].insert(obj);
        return;
      }
    }
    
    this.objects.push(obj);
    
    if (this.objects.length > this.maxObjects && this.level < this.maxLevels) {
      if (this.nodes.length === 0) {
        this.split();
      }
      
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
  
  retrieve(returnObjects, obj) {
    const index = this.getIndex(obj);
    
    if (index !== -1 && this.nodes.length > 0) {
      this.nodes[index].retrieve(returnObjects, obj);
    }
    
    returnObjects.push(...this.objects);
    return returnObjects;
  }
}
```

## Object Pooling System

```javascript
class ObjectPool {
  constructor(createFn, resetFn, initialSize = 100) {
    this.createFn = createFn;
    this.resetFn = resetFn;
    this.pool = [];
    this.active = new Set();
    
    // Pre-populate pool
    for (let i = 0; i < initialSize; i++) {
      this.pool.push(this.createFn());
    }
  }
  
  get() {
    let obj;
    
    if (this.pool.length > 0) {
      obj = this.pool.pop();
    } else {
      obj = this.createFn();
    }
    
    this.active.add(obj);
    return obj;
  }
  
  release(obj) {
    if (this.active.has(obj)) {
      this.active.delete(obj);
      this.resetFn(obj);
      this.pool.push(obj);
    }
  }
  
  releaseAll() {
    for (let obj of this.active) {
      this.resetFn(obj);
      this.pool.push(obj);
    }
    this.active.clear();
  }
  
  getStats() {
    return {
      poolSize: this.pool.length,
      activeCount: this.active.size,
      totalCreated: this.pool.length + this.active.size
    };
  }
}

// Usage example
const bulletPool = new ObjectPool(
  () => new Bullet(), // Create function
  (bullet) => {       // Reset function
    bullet.x = 0;
    bullet.y = 0;
    bullet.velocity.x = 0;
    bullet.velocity.y = 0;
    bullet.active = false;
  },
  50 // Initial pool size
);
```

## Texture Atlas Management
- Combine multiple sprites into single textures
- Reduce draw calls and state changes
- Lazy loading based on visibility
- Texture compression (DXT1/DXT5 where supported)
- Mipmapping for different zoom levels

```javascript
class TextureAtlas {
  constructor(width = 2048, height = 2048) {
    this.width = width;
    this.height = height;
    this.canvas = document.createElement('canvas');
    this.canvas.width = width;
    this.canvas.height = height;
    this.context = this.canvas.getContext('2d');
    this.sprites = new Map();
    this.currentX = 0;
    this.currentY = 0;
    this.rowHeight = 0;
  }
  
  addSprite(name, image) {
    if (this.currentX + image.width > this.width) {
      this.currentX = 0;
      this.currentY += this.rowHeight;
      this.rowHeight = 0;
    }
    
    if (this.currentY + image.height > this.height) {
      throw new Error('Texture atlas is full');
    }
    
    this.context.drawImage(image, this.currentX, this.currentY);
    
    const spriteData = {
      x: this.currentX,
      y: this.currentY,
      width: image.width,
      height: image.height,
      u1: this.currentX / this.width,
      v1: this.currentY / this.height,
      u2: (this.currentX + image.width) / this.width,
      v2: (this.currentY + image.height) / this.height
    };
    
    this.sprites.set(name, spriteData);
    
    this.currentX += image.width;
    this.rowHeight = Math.max(this.rowHeight, image.height);
    
    return spriteData;
  }
  
  getSprite(name) {
    return this.sprites.get(name);
  }
  
  getTexture() {
    return this.canvas;
  }
}
```

## Memory Optimization
- Fixed-size arrays for game objects
- Avoid frequent garbage collection
- Reuse temporary objects and vectors
- Efficient data structures (TypedArrays)
- Memory pooling for frequent allocations

```javascript
class MemoryManager {
  constructor() {
    // Reusable temporary objects
    this.tempVector = {x: 0, y: 0};
    this.tempRect = {x: 0, y: 0, width: 0, height: 0};
    this.tempArray = [];
    
    // Fixed-size arrays for game objects
    this.maxUnits = 1000;
    this.units = new Array(this.maxUnits);
    this.unitCount = 0;
    
    // TypedArrays for efficient data storage
    this.unitPositions = new Float32Array(this.maxUnits * 2); // x, y pairs
    this.unitHealths = new Float32Array(this.maxUnits);
  }
  
  getTempVector(x = 0, y = 0) {
    this.tempVector.x = x;
    this.tempVector.y = y;
    return this.tempVector;
  }
  
  getTempRect(x = 0, y = 0, width = 0, height = 0) {
    this.tempRect.x = x;
    this.tempRect.y = y;
    this.tempRect.width = width;
    this.tempRect.height = height;
    return this.tempRect;
  }
  
  addUnit(unit) {
    if (this.unitCount < this.maxUnits) {
      const index = this.unitCount++;
      this.units[index] = unit;
      this.unitPositions[index * 2] = unit.x;
      this.unitPositions[index * 2 + 1] = unit.y;
      this.unitHealths[index] = unit.health;
      return index;
    }
    return -1; // Array full
  }
  
  removeUnit(index) {
    if (index < this.unitCount) {
      // Move last unit to this position
      const lastIndex = --this.unitCount;
      this.units[index] = this.units[lastIndex];
      this.unitPositions[index * 2] = this.unitPositions[lastIndex * 2];
      this.unitPositions[index * 2 + 1] = this.unitPositions[lastIndex * 2 + 1];
      this.unitHealths[index] = this.unitHealths[lastIndex];
    }
  }
}
```

## Rendering Optimizations
- **Frustum culling** for off-screen objects
- **Level-of-detail (LOD)** for distant units
- **Occlusion culling** for hidden objects
- **Instanced rendering** for identical objects
- **Depth sorting optimization**

## CPU Optimizations
- **Web Workers** for pathfinding calculations
- **Distributed AI processing** across frames
- **Cached calculation results**
- **Spatial hashing** for collision detection
- **Incremental updates** instead of full recalculations

## Bandwidth Optimizations
- **Delta compression** for state updates
- **Binary serialization** protocols
- **Predictive interpolation**
- **Selective update broadcasting**
- **Asset caching and compression**

## Performance Targets
- **60+ FPS** with 200+ units on screen
- **<200MB** baseline memory usage
- **<16ms** frame time consistency
- **<5ms** pathfinding for 100 units
- **<2ms** fog of war updates per frame

## Performance Monitoring

```javascript
class PerformanceMonitor {
  constructor() {
    this.frameCount = 0;
    this.lastTime = performance.now();
    this.fps = 0;
    this.frameTime = 0;
    this.memoryUsage = 0;
    
    this.metrics = {
      render: 0,
      update: 0,
      physics: 0,
      ai: 0
    };
  }
  
  startFrame() {
    this.frameStart = performance.now();
  }
  
  endFrame() {
    const now = performance.now();
    this.frameTime = now - this.frameStart;
    this.frameCount++;
    
    if (now - this.lastTime >= 1000) {
      this.fps = (this.frameCount * 1000) / (now - this.lastTime);
      this.frameCount = 0;
      this.lastTime = now;
      
      if (performance.memory) {
        this.memoryUsage = performance.memory.usedJSHeapSize / 1024 / 1024; // MB
      }
      
      this.reportMetrics();
    }
  }
  
  measureOperation(name, operation) {
    const start = performance.now();
    const result = operation();
    const duration = performance.now() - start;
    
    if (this.metrics[name] !== undefined) {
      this.metrics[name] = duration;
    }
    
    return result;
  }
  
  reportMetrics() {
    console.log(`FPS: ${this.fps.toFixed(1)}, Frame Time: ${this.frameTime.toFixed(2)}ms, Memory: ${this.memoryUsage.toFixed(1)}MB`);
    
    if (this.fps < 47) {
      console.warn('Performance below target FPS');
    }
    
    if (this.memoryUsage > 500) {
      console.warn('Memory usage above target');
    }
  }
}
```