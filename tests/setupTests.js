/**
 * Jest Setup File
 * Global test configuration and utilities for RTS game testing
 */

// Global test utilities
global.console = {
  ...console,
  // Suppress console.log in tests unless explicitly enabled
  log: process.env.VERBOSE_TESTS ? console.log : jest.fn(),
  debug: process.env.VERBOSE_TESTS ? console.debug : jest.fn(),
  info: process.env.VERBOSE_TESTS ? console.info : jest.fn(),
  warn: console.warn,
  error: console.error,
};

// Mock requestAnimationFrame for game loop testing
global.requestAnimationFrame = (callback) => {
  return setTimeout(callback, 16); // ~60 FPS
};

global.cancelAnimationFrame = (id) => {
  clearTimeout(id);
};

// Mock performance.now for timing tests
Object.defineProperty(global.performance, 'now', {
  writable: true,
  value: jest.fn(() => Date.now()),
});

// Mock PIXI.js globals for headless testing
global.HTMLCanvasElement = class {
  constructor() {
    this.width = 800;
    this.height = 600;
    this.style = {};
  }
  
  getContext() {
    return {
      clearRect: jest.fn(),
      drawImage: jest.fn(),
      fillRect: jest.fn(),
      strokeRect: jest.fn(),
      save: jest.fn(),
      restore: jest.fn(),
      translate: jest.fn(),
      scale: jest.fn(),
      rotate: jest.fn(),
    };
  }
  
  toDataURL() {
    return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
  }
};

// Mock WebGL context for PIXI.js
global.WebGLRenderingContext = class {
  constructor() {
    // Mock WebGL methods
    const noop = () => {};
    const noopReturn = () => null;
    
    this.createShader = noopReturn;
    this.shaderSource = noop;
    this.compileShader = noop;
    this.createProgram = noopReturn;
    this.attachShader = noop;
    this.linkProgram = noop;
    this.useProgram = noop;
    this.createBuffer = noopReturn;
    this.bindBuffer = noop;
    this.bufferData = noop;
    this.getAttribLocation = () => 0;
    this.enableVertexAttribArray = noop;
    this.vertexAttribPointer = noop;
    this.drawArrays = noop;
    this.getUniformLocation = noopReturn;
    this.uniform1f = noop;
    this.uniform2f = noop;
    this.uniform3f = noop;
    this.uniform4f = noop;
    this.uniformMatrix4fv = noop;
    this.viewport = noop;
    this.clear = noop;
    this.clearColor = noop;
    this.enable = noop;
    this.disable = noop;
    this.blendFunc = noop;
    this.getParameter = () => 'Mock WebGL';
  }
};

// Mock ResizeObserver for UI components
global.ResizeObserver = class ResizeObserver {
  constructor(callback) {
    this.callback = callback;
  }
  
  observe() {
    // Mock implementation
  }
  
  unobserve() {
    // Mock implementation
  }
  
  disconnect() {
    // Mock implementation
  }
};

// Mock AudioContext for game audio
global.AudioContext = class {
  constructor() {
    this.destination = {};
    this.state = 'running';
    this.currentTime = 0;
  }
  
  createOscillator() {
    return {
      connect: jest.fn(),
      start: jest.fn(),
      stop: jest.fn(),
      frequency: { value: 440 }
    };
  }
  
  createGain() {
    return {
      connect: jest.fn(),
      gain: { value: 1 }
    };
  }
  
  resume() {
    return Promise.resolve();
  }
};

// Mock fetch for API calls
if (!global.fetch) {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
      text: () => Promise.resolve(''),
    })
  );
}

// Mock WebSocket for multiplayer testing
global.WebSocket = class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.CONNECTING = 0;
    this.OPEN = 1;
    this.CLOSING = 2;
    this.CLOSED = 3;
    
    // Simulate connection after a timeout
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 10);
  }
  
  send(data) {
    // Mock send implementation
  }
  
  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }
};

// Test utilities for game state
global.createMockGameState = () => ({
  entities: new Map(),
  systems: [],
  camera: { x: 0, y: 0, scale: 1 },
  inputState: {
    mouse: { x: 0, y: 0, buttons: [] },
    keyboard: { keys: new Set() }
  },
  time: {
    current: Date.now(),
    delta: 16.67 // ~60 FPS
  }
});

// Test utilities for ECS entities
global.createMockEntity = (id = 'test-entity') => ({
  id,
  active: true,
  components: new Map(),
  creationTime: Date.now(),
  lastAccessTime: Date.now(),
  
  addComponent(component) {
    this.components.set(component.constructor.name, component);
    return this;
  },
  
  removeComponent(ComponentType) {
    const name = typeof ComponentType === 'string' ? ComponentType : ComponentType.name;
    this.components.delete(name);
    return this;
  },
  
  getComponent(ComponentType) {
    const name = typeof ComponentType === 'string' ? ComponentType : ComponentType.name;
    return this.components.get(name);
  },
  
  hasComponent(ComponentType) {
    const name = typeof ComponentType === 'string' ? ComponentType : ComponentType.name;
    return this.components.has(name);
  },
  
  getAllComponents() {
    return Array.from(this.components.values());
  },
  
  isValid() {
    return this.active && !this.destroyed;
  },
  
  destroy() {
    this.destroyed = true;
    this.active = false;
    this.components.clear();
  }
});

// Test utilities for AI components
global.createMockAIComponent = (options = {}) => ({
  enabled: true,
  behaviorType: 'combatUnit',
  aiLevel: 'normal',
  currentState: 'idle',
  lastDecisionTime: 0,
  decisionInterval: 500,
  experienceLevel: 0,
  learningEnabled: true,
  debugMode: false,
  tacticalContext: {
    alertLevel: 'normal',
    enemiesNearby: 0,
    alliesNearby: 0
  },
  memory: {
    knownEnemies: new Map(),
    knownResources: new Map(),
    patrolPoints: []
  },
  performanceMetrics: {
    decisionsPerSecond: 0,
    averageDecisionTime: 0,
    successRate: 0
  },
  
  shouldMakeDecision: jest.fn(() => true),
  markDecisionMade: jest.fn(),
  updateTacticalContext: jest.fn(),
  learnFromExperience: jest.fn(),
  setState: jest.fn(),
  getAIStatus: jest.fn(() => ({ state: 'idle' })),
  reset: jest.fn(),
  destroy: jest.fn(),
  
  ...options
});

// Test utilities for pathfinding
global.createMockNavigationGrid = (width = 10, height = 10) => ({
  width,
  height,
  cellSize: 32,
  
  isWalkable: jest.fn(() => true),
  isValidCell: jest.fn(() => true),
  worldToGrid: jest.fn((x, y) => ({ x: Math.floor(x / 32), y: Math.floor(y / 32) })),
  gridToWorld: jest.fn((x, y) => ({ x: x * 32 + 16, y: y * 32 + 16 })),
  getNeighbors: jest.fn((x, y) => [
    { x: x + 1, y },
    { x: x - 1, y },
    { x, y: y + 1 },
    { x, y: y - 1 }
  ]),
  getMovementCost: jest.fn(() => 1),
  heuristic: jest.fn((x1, y1, x2, y2) => Math.abs(x2 - x1) + Math.abs(y2 - y1))
});

// Increase timeout for game tests
jest.setTimeout(30000);

// Custom matchers for game testing
expect.extend({
  toBeValidEntity(received) {
    const pass = received && 
                 typeof received.id === 'string' && 
                 received.active === true && 
                 !received.destroyed;
    
    if (pass) {
      return {
        message: () => `expected entity not to be valid`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected entity to be valid (have id, be active, not destroyed)`,
        pass: false,
      };
    }
  },
  
  toHaveComponent(received, ComponentType) {
    const pass = received && received.hasComponent && received.hasComponent(ComponentType);
    
    if (pass) {
      return {
        message: () => `expected entity not to have component ${ComponentType.name || ComponentType}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected entity to have component ${ComponentType.name || ComponentType}`,
        pass: false,
      };
    }
  },
  
  toBeWithinRange(received, center, maxDistance) {
    const distance = Math.sqrt(
      Math.pow(received.x - center.x, 2) + 
      Math.pow(received.y - center.y, 2)
    );
    const pass = distance <= maxDistance;
    
    if (pass) {
      return {
        message: () => `expected position to be outside range of ${maxDistance}`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected position to be within range of ${maxDistance}, but was ${distance}`,
        pass: false,
      };
    }
  }
});

// Global test configuration
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();
  
  // Reset performance.now
  performance.now.mockReturnValue(Date.now());
  
  // Reset console if mocked
  if (jest.isMockFunction(console.log)) {
    console.log.mockClear();
  }
});

afterEach(() => {
  // Clean up any global state
  // This helps prevent test pollution
});

// Global error handling for tests
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});