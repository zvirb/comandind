# WebStrike Command - Technical Architecture

## Rendering Engine: PixiJS
- Optimal performance for sprite-heavy RTS games (47 FPS with 10,000 sprites)
- WebGL-based sprite batching system
- Custom SpriteBatcher class with maxSprites = 1000
- Texture atlas management with lazy loading

```javascript
class SpriteBatcher {
  constructor(gl, maxSprites = 1000) {
    this.gl = gl;
    this.maxSprites = maxSprites;
    this.vertices = new Float32Array(maxSprites * 6 * 4);
    this.currentTexture = null;
    this.spriteCount = 0;
  }
  
  draw(texture, x, y, width, height, srcX, srcY, srcW, srcH) {
    if (this.currentTexture !== texture) {
      this.flush(); // Render current batch
      this.currentTexture = texture;
    }
    // Add sprite vertices to batch
    const index = this.spriteCount * 24;
    // ... vertex positioning code
    this.spriteCount++;
  }
}
```

## Multiplayer Architecture: Colyseus + WebRTC Hybrid
- **Colyseus** for reliable state synchronization and room management
- **WebRTC data channels** for low-latency unit commands
- **STUN/TURN servers** (Coturn or Xirsys) for NAT traversal
- **Client-server architecture** (not lockstep) for flexibility
- Server maintains authoritative game state
- Client-side prediction for responsive controls
- Server reconciliation for validation
- Delta compression for bandwidth optimization

## AI Framework: TensorFlow.js + Ollama LLM
- GPU-accelerated learning in browsers
- Q-Learning with experience replay buffer (10,000 capacity)
- Neural network: 128x128 dense layers with ReLU activation
- State representation: normalized position, health, enemy proximity, resources, terrain
- Ollama WebSocket integration for strategic analysis
- Response caching and async processing

```javascript
const model = tf.sequential({
  layers: [
    tf.layers.dense({units: 128, activation: 'relu', inputShape: [stateSize]}),
    tf.layers.dense({units: 128, activation: 'relu'}),
    tf.layers.dense({units: actionSize})
  ]
});
```

## Game Loop Architecture
- Fixed timestep with interpolation
- Smooth camera scrolling with bounds checking
- Entity-Component System (ECS)
- Object pooling for frequently created objects

## Spatial Indexing: Quadtree Implementation
- Efficient collision detection and unit queries
- maxObjects = 10, maxLevels = 5
- Dynamic insertion and removal

```javascript
class Quadtree {
  constructor(bounds, maxObjects = 10, maxLevels = 5, level = 0) {
    this.maxObjects = maxObjects;
    this.maxLevels = maxLevels;
    this.bounds = bounds;
    this.objects = [];
    this.nodes = [];
  }
}
```

## Asset Management
- Texture atlas with compression
- Sprite extraction via XCC Mixer
- Frank Klepacki soundtrack (619.8MB complete collection)
- Sound effects from original AUD files

## Development Tools
- webpack bundler with terser optimization
- ESLint + Prettier for code quality
- Jest for unit testing
- Playwright for integration testing
- Lighthouse for performance testing