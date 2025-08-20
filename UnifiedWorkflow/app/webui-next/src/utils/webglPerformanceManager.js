/**
 * WebGL Performance Manager
 * Advanced performance monitoring and optimization for Three.js applications
 */

class WebGLPerformanceManager {
  constructor() {
    this.stats = {
      fps: 60,
      frameTime: 16.67,
      drawCalls: 0,
      triangles: 0,
      geometries: 0,
      textures: 0,
      memory: {
        geometries: 0,
        textures: 0,
        programs: 0
      }
    };
    
    this.performanceLevel = 'high'; // high, medium, low
    this.adaptiveQuality = true;
    this.frameHistory = [];
    this.maxFrameHistory = 60;
    this.performanceThresholds = {
      high: { minFps: 55, maxDrawCalls: 200, maxTriangles: 100000 },
      medium: { minFps: 40, maxDrawCalls: 150, maxTriangles: 75000 },
      low: { minFps: 25, maxDrawCalls: 100, maxTriangles: 50000 }
    };
    
    this.optimizations = {
      frustumCulling: true,
      occlusionCulling: false,
      lodSystem: true,
      instancedRendering: true,
      batchGeometry: true,
      textureCompression: true,
      shaderOptimization: true
    };

    this.resourcePools = {
      geometries: new Map(),
      materials: new Map(),
      textures: new Map()
    };

    // Performance isolation to prevent React interference
    this.initialized = false;
    this.reactIsolation = true;
    this.lastLogTime = 0;
    this.logThrottleInterval = 30000; // Log performance changes max once per 30 seconds

    this.bindMethods();
  }

  bindMethods() {
    this.update = this.update.bind(this);
    this.analyzePerformance = this.analyzePerformance.bind(this);
    // this.optimizeScene = this.optimizeScene.bind(this); // Method not defined yet
  }

  /**
   * Initialize performance monitoring for a Three.js renderer
   * Prevents multiple initializations to avoid React interference
   */
  init(renderer, scene, camera) {
    // Prevent multiple initializations that cause React cascade issues
    if (this.initialized) {
      console.log('WebGL Performance Manager already initialized, skipping...');
      return this;
    }

    this.renderer = renderer;
    this.scene = scene;
    this.camera = camera;
    
    // Setup WebGL context lost/restored handlers first
    this.setupContextLostHandlers();
    
    // Enable WebGL extensions for better performance
    this.enableWebGLExtensions();
    
    // Setup performance monitoring with React isolation
    this.setupPerformanceMonitoring();
    
    // Initialize object pools
    this.initializeResourcePools();
    
    this.initialized = true;
    console.log('WebGL Performance Manager initialized (React-isolated)');
    return this;
  }

  /**
   * Setup WebGL context lost and restored event handlers
   */
  setupContextLostHandlers() {
    if (!this.renderer) return;

    const canvas = this.renderer.domElement;
    
    // Context lost handler
    canvas.addEventListener('webglcontextlost', (event) => {
      console.warn('[WebGLPerformanceManager] WebGL context lost');
      event.preventDefault(); // Prevent default behavior
      
      this.isContextLost = true;
      this.contextLostTime = Date.now();
      
      // Pause all animations and updates
      this.pauseAnimations();
      
      // Notify other systems
      this.notifyContextLost();
      
      // Start recovery attempts
      this.scheduleContextRecovery();
    }, false);
    
    // Context restored handler
    canvas.addEventListener('webglcontextrestored', (event) => {
      console.log('[WebGLPerformanceManager] WebGL context restored');
      
      this.isContextLost = false;
      this.contextRestoredTime = Date.now();
      
      // Reinitialize resources
      this.reinitializeAfterContextLoss();
      
      // Resume animations
      this.resumeAnimations();
      
      // Notify other systems
      this.notifyContextRestored();
    }, false);
  }

  /**
   * Pause all animations when context is lost
   */
  pauseAnimations() {
    this.animationsPaused = true;
    
    // Stop performance monitoring
    if (this.performanceMonitorInterval) {
      clearInterval(this.performanceMonitorInterval);
      this.performanceMonitorInterval = null;
    }
    
    // Stop memory monitoring
    if (this.memoryMonitorInterval) {
      clearInterval(this.memoryMonitorInterval);
      this.memoryMonitorInterval = null;
    }
  }

  /**
   * Resume animations when context is restored
   */
  resumeAnimations() {
    this.animationsPaused = false;
    
    // Restart monitoring
    this.setupPerformanceMonitoring();
  }

  /**
   * Notify other systems about context lost
   */
  notifyContextLost() {
    // Emit custom event for other components to handle
    window.dispatchEvent(new CustomEvent('webgl-context-lost', {
      detail: {
        timestamp: this.contextLostTime,
        manager: this
      }
    }));
    
    // Notify auth circuit breaker if available
    if (window.authCircuitBreaker && typeof window.authCircuitBreaker.onWebGLContextLost === 'function') {
      window.authCircuitBreaker.onWebGLContextLost();
    }
  }

  /**
   * Notify other systems about context restored
   */
  notifyContextRestored() {
    const recoveryTime = this.contextRestoredTime - this.contextLostTime;
    
    window.dispatchEvent(new CustomEvent('webgl-context-restored', {
      detail: {
        timestamp: this.contextRestoredTime,
        recoveryTime,
        manager: this
      }
    }));
    
    console.log(`[WebGLPerformanceManager] Context recovered in ${recoveryTime}ms`);
  }

  /**
   * Schedule context recovery attempts
   */
  scheduleContextRecovery() {
    // Try to force context restoration after a delay
    setTimeout(() => {
      if (this.isContextLost) {
        console.log('[WebGLPerformanceManager] Attempting to force context recovery');
        this.attemptContextRecovery();
      }
    }, 1000);
  }

  /**
   * Attempt to recover WebGL context
   */
  attemptContextRecovery() {
    if (!this.renderer || !this.isContextLost) return;

    try {
      // Try to get the WebGL context again
      const gl = this.renderer.getContext();
      
      if (gl.isContextLost()) {
        console.log('[WebGLPerformanceManager] Context still lost, will retry');
        
        // Schedule another recovery attempt
        setTimeout(() => this.attemptContextRecovery(), 2000);
      } else {
        console.log('[WebGLPerformanceManager] Context recovery successful');
        this.isContextLost = false;
        this.reinitializeAfterContextLoss();
      }
    } catch (error) {
      console.warn('[WebGLPerformanceManager] Context recovery failed:', error);
      
      // Fallback: Create degraded mode
      this.enableDegradedMode();
    }
  }

  /**
   * Reinitialize resources after context restoration
   */
  reinitializeAfterContextLoss() {
    try {
      // Clear resource pools
      this.resourcePools.geometries.clear();
      this.resourcePools.materials.clear();
      this.resourcePools.textures.clear();
      
      // Re-enable WebGL extensions
      this.enableWebGLExtensions();
      
      // Reinitialize resource pools
      this.initializeResourcePools();
      
      // Reset performance stats
      this.stats = {
        ...this.stats,
        fps: 60,
        frameTime: 16.67,
        drawCalls: 0,
        triangles: 0
      };
      
      console.log('[WebGLPerformanceManager] Resources reinitialized after context restoration');
    } catch (error) {
      console.error('[WebGLPerformanceManager] Failed to reinitialize after context loss:', error);
      this.enableDegradedMode();
    }
  }

  /**
   * Enable degraded mode when WebGL is unavailable
   */
  enableDegradedMode() {
    this.degradedMode = true;
    this.performanceLevel = 'low';
    
    console.warn('[WebGLPerformanceManager] Enabling degraded mode - WebGL operations limited');
    
    // Notify application about degraded mode
    window.dispatchEvent(new CustomEvent('webgl-degraded-mode', {
      detail: {
        timestamp: Date.now(),
        reason: 'Context loss recovery failed'
      }
    }));
  }

  /**
   * Enable WebGL extensions for performance and features
   */
  enableWebGLExtensions() {
    if (!this.renderer) return;

    const gl = this.renderer.getContext();
    const extensions = [
      'OES_vertex_array_object',
      'ANGLE_instanced_arrays',
      'EXT_disjoint_timer_query',
      'WEBGL_compressed_texture_s3tc',
      'WEBGL_compressed_texture_etc1',
      'WEBGL_compressed_texture_astc',
      'EXT_texture_filter_anisotropic'
    ];

    extensions.forEach(ext => {
      const extension = gl.getExtension(ext);
      if (extension) {
        console.log(`Enabled WebGL extension: ${ext}`);
      }
    });

    // Configure renderer for optimal performance
    this.renderer.sortObjects = false;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.info.autoReset = false;
  }

  /**
   * Setup performance monitoring with Web APIs
   */
  setupPerformanceMonitoring() {
    // Performance Observer for frame timing
    if ('PerformanceObserver' in window) {
      this.frameObserver = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (entry.entryType === 'measure' && entry.name === 'frame-render') {
            this.recordFrameTime(entry.duration);
          }
        });
      });

      try {
        this.frameObserver.observe({ entryTypes: ['measure'] });
      } catch (e) {
        console.warn('Failed to setup frame timing observer:', e);
      }
    }

    // Memory monitoring
    this.setupMemoryMonitoring();
  }

  /**
   * Setup memory usage monitoring with React isolation
   */
  setupMemoryMonitoring() {
    if (performance.memory && !this.memoryMonitorInterval) {
      this.memoryMonitorInterval = setInterval(() => {
        // Only run if WebGL is still active and not affecting React
        if (!this.reactIsolation || !this.renderer) return;

        const memory = performance.memory;
        if (memory.usedJSHeapSize > memory.jsHeapSizeLimit * 0.85) { // Higher threshold
          // Throttle warning logs to prevent React re-render cascades
          const now = Date.now();
          if (now - this.lastLogTime > this.logThrottleInterval) {
            console.warn('High memory usage detected, triggering cleanup');
            this.lastLogTime = now;
          }
          this.forceCleanup();
        }
      }, 10000); // Less frequent monitoring to reduce React interference
    }
  }

  /**
   * Initialize resource pools for object reuse
   */
  initializeResourcePools() {
    // Pre-allocate common geometries
    const commonGeometries = [
      { type: 'BoxGeometry', args: [1, 1, 1] },
      { type: 'SphereGeometry', args: [1, 32, 32] },
      { type: 'PlaneGeometry', args: [1, 1] },
      { type: 'CylinderGeometry', args: [1, 1, 1, 32] }
    ];

    commonGeometries.forEach(({ type, args }) => {
      const key = `${type}_${args.join('_')}`;
      if (!this.resourcePools.geometries.has(key)) {
        this.resourcePools.geometries.set(key, []);
      }
    });
  }

  /**
   * Update performance stats and adaptive quality
   */
  update(deltaTime = 16.67) {
    // Skip update if context is lost or animations are paused
    if (this.isContextLost || this.animationsPaused || this.degradedMode) {
      return;
    }
    
    const startTime = performance.now();
    
    // Mark frame start for timing
    performance.mark('frame-start');
    
    // Update stats
    this.updateStats(deltaTime);
    
    // Analyze and adapt performance
    if (this.adaptiveQuality) {
      this.analyzePerformance();
    }
    
    // Cleanup if needed
    this.checkCleanup();
    
    // Mark frame end and measure
    performance.mark('frame-end');
    performance.measure('frame-render', 'frame-start', 'frame-end');
    
    const updateTime = performance.now() - startTime;
    this.stats.updateTime = updateTime;
  }

  /**
   * Update performance statistics
   */
  updateStats(deltaTime) {
    // Frame rate calculation
    this.stats.frameTime = deltaTime;
    this.stats.fps = 1000 / deltaTime;
    
    // Add to frame history
    this.frameHistory.push(this.stats.fps);
    if (this.frameHistory.length > this.maxFrameHistory) {
      this.frameHistory.shift();
    }

    // Renderer stats
    if (this.renderer && this.renderer.info) {
      const info = this.renderer.info;
      this.stats.drawCalls = info.render.calls;
      this.stats.triangles = info.render.triangles;
      this.stats.geometries = info.memory.geometries;
      this.stats.textures = info.memory.textures;
      this.stats.memory = { ...info.memory };
    }
  }

  /**
   * Analyze performance and adjust quality settings
   */
  analyzePerformance() {
    if (this.frameHistory.length < 30) return; // Need enough samples

    const avgFps = this.frameHistory.reduce((a, b) => a + b, 0) / this.frameHistory.length;
    const currentThreshold = this.performanceThresholds[this.performanceLevel];

    // Check if we need to adjust performance level
    if (avgFps < currentThreshold.minFps && this.performanceLevel !== 'low') {
      this.decreasePerformanceLevel();
    } else if (avgFps > 55 && this.performanceLevel !== 'high') {
      this.increasePerformanceLevel();
    }

    // Check draw calls and geometry complexity
    if (this.stats.drawCalls > currentThreshold.maxDrawCalls) {
      this.optimizeRenderCalls();
    }

    if (this.stats.triangles > currentThreshold.maxTriangles) {
      this.optimizeGeometry();
    }
  }

  /**
   * Decrease performance level for better frame rate
   */
  decreasePerformanceLevel() {
    const levels = ['high', 'medium', 'low'];
    const currentIndex = levels.indexOf(this.performanceLevel);
    
    if (currentIndex < levels.length - 1) {
      this.performanceLevel = levels[currentIndex + 1];
      
      // Throttle logging to prevent React cascade issues
      const now = Date.now();
      if (now - this.lastLogTime > this.logThrottleInterval) {
        console.log(`Performance level decreased to: ${this.performanceLevel} (React-isolated)`);
        this.lastLogTime = now;
      }
      
      this.applyPerformanceSettings();
    }
  }

  /**
   * Increase performance level when performance allows
   */
  increasePerformanceLevel() {
    const levels = ['high', 'medium', 'low'];
    const currentIndex = levels.indexOf(this.performanceLevel);
    
    if (currentIndex > 0) {
      this.performanceLevel = levels[currentIndex - 1];
      
      // Throttle logging to prevent React cascade issues
      const now = Date.now();
      if (now - this.lastLogTime > this.logThrottleInterval) {
        console.log(`Performance level increased to: ${this.performanceLevel} (React-isolated)`);
        this.lastLogTime = now;
      }
      
      this.applyPerformanceSettings();
    }
  }

  /**
   * Apply performance settings based on current level
   */
  applyPerformanceSettings() {
    if (!this.renderer) return;

    const settings = {
      high: {
        pixelRatio: Math.min(window.devicePixelRatio, 2),
        antialias: true,
        shadows: true,
        toneMappingExposure: 1.0
      },
      medium: {
        pixelRatio: Math.min(window.devicePixelRatio, 1.5),
        antialias: true,
        shadows: true,
        toneMappingExposure: 0.8
      },
      low: {
        pixelRatio: 1,
        antialias: false,
        shadows: false,
        toneMappingExposure: 0.6
      }
    };

    const currentSettings = settings[this.performanceLevel];
    
    this.renderer.setPixelRatio(currentSettings.pixelRatio);
    this.renderer.shadowMap.enabled = currentSettings.shadows;
    this.renderer.toneMappingExposure = currentSettings.toneMappingExposure;

    // Trigger re-render with new settings
    if (this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  /**
   * Optimize render calls by batching and instancing
   */
  optimizeRenderCalls() {
    if (!this.scene) return;

    // Group similar objects for batching
    const batches = new Map();
    
    this.scene.traverse((object) => {
      if (object.isMesh && object.geometry && object.material) {
        const key = `${object.geometry.uuid}_${object.material.uuid}`;
        if (!batches.has(key)) {
          batches.set(key, []);
        }
        batches.get(key).push(object);
      }
    });

    // Create instanced meshes for groups with many objects
    batches.forEach((objects, key) => {
      if (objects.length > 10) {
        this.createInstancedMesh(objects);
      }
    });
  }

  /**
   * Create instanced mesh from array of similar objects
   */
  createInstancedMesh(objects) {
    if (objects.length === 0) return;

    const template = objects[0];
    const geometry = template.geometry;
    const material = template.material;

    // Create instanced mesh
    const instancedMesh = new THREE.InstancedMesh(geometry, material, objects.length);
    
    // Set instance matrices
    objects.forEach((object, index) => {
      object.updateMatrixWorld();
      instancedMesh.setMatrixAt(index, object.matrixWorld);
      
      // Remove original object
      if (object.parent) {
        object.parent.remove(object);
      }
    });

    instancedMesh.instanceMatrix.needsUpdate = true;
    
    // Add to scene
    this.scene.add(instancedMesh);
    
    console.log(`Created instanced mesh with ${objects.length} instances`);
  }

  /**
   * Optimize geometry complexity based on distance and screen size
   */
  optimizeGeometry() {
    if (!this.scene || !this.camera) return;

    this.scene.traverse((object) => {
      if (object.isMesh && object.geometry) {
        const distance = this.camera.position.distanceTo(object.position);
        const screenSize = this.calculateScreenSize(object, distance);
        
        // Apply LOD based on distance and screen size
        this.applyLOD(object, distance, screenSize);
      }
    });
  }

  /**
   * Calculate screen size of object
   */
  calculateScreenSize(object, distance) {
    if (!object.geometry.boundingSphere) {
      object.geometry.computeBoundingSphere();
    }
    
    const radius = object.geometry.boundingSphere.radius;
    const fov = this.camera.fov * Math.PI / 180;
    const screenHeight = 2 * Math.tan(fov / 2) * distance;
    const screenSize = (radius * 2) / screenHeight;
    
    return screenSize;
  }

  /**
   * Apply Level of Detail optimization
   */
  applyLOD(object, distance, screenSize) {
    if (screenSize < 0.01) {
      // Object is too small, hide it
      object.visible = false;
    } else if (screenSize < 0.05) {
      // Use low detail version
      this.applyLowDetailGeometry(object);
    } else if (screenSize < 0.2) {
      // Use medium detail version
      this.applyMediumDetailGeometry(object);
    } else {
      // Use high detail version
      object.visible = true;
    }
  }

  /**
   * Apply low detail geometry
   */
  applyLowDetailGeometry(object) {
    if (object.geometry.isBufferGeometry) {
      // Reduce geometry detail
      const positions = object.geometry.attributes.position;
      if (positions && positions.count > 100) {
        // Simplify geometry by reducing vertices
        // This is a simple implementation - in practice, use a proper decimation algorithm
        const simplified = this.simplifyGeometry(object.geometry, 0.3);
        object.geometry = simplified;
      }
    }
    object.visible = true;
  }

  /**
   * Apply medium detail geometry
   */
  applyMediumDetailGeometry(object) {
    if (object.geometry.isBufferGeometry) {
      const positions = object.geometry.attributes.position;
      if (positions && positions.count > 500) {
        const simplified = this.simplifyGeometry(object.geometry, 0.6);
        object.geometry = simplified;
      }
    }
    object.visible = true;
  }

  /**
   * Simplify geometry by reducing vertex count
   */
  simplifyGeometry(geometry, ratio) {
    // This is a placeholder for geometry simplification
    // In a real implementation, you would use a proper mesh decimation algorithm
    // For now, we'll just return the original geometry
    return geometry;
  }

  /**
   * Get or create geometry from pool
   */
  getPooledGeometry(type, ...args) {
    const key = `${type}_${args.join('_')}`;
    const pool = this.resourcePools.geometries.get(key) || [];
    
    if (pool.length > 0) {
      return pool.pop();
    }
    
    // Create new geometry if pool is empty
    switch (type) {
      case 'BoxGeometry':
        return new THREE.BoxGeometry(...args);
      case 'SphereGeometry':
        return new THREE.SphereGeometry(...args);
      case 'PlaneGeometry':
        return new THREE.PlaneGeometry(...args);
      case 'CylinderGeometry':
        return new THREE.CylinderGeometry(...args);
      default:
        console.warn(`Unknown geometry type: ${type}`);
        return null;
    }
  }

  /**
   * Return geometry to pool for reuse
   */
  returnGeometryToPool(geometry, type, ...args) {
    const key = `${type}_${args.join('_')}`;
    let pool = this.resourcePools.geometries.get(key);
    
    if (!pool) {
      pool = [];
      this.resourcePools.geometries.set(key, pool);
    }
    
    // Limit pool size to prevent memory leaks
    if (pool.length < 10) {
      pool.push(geometry);
    } else {
      geometry.dispose();
    }
  }

  /**
   * Check if cleanup is needed
   */
  checkCleanup() {
    const shouldCleanup = 
      this.stats.memory.geometries > 100 ||
      this.stats.memory.textures > 50 ||
      this.stats.drawCalls > 300;

    if (shouldCleanup) {
      this.performCleanup();
    }
  }

  /**
   * Perform cleanup of unused resources
   */
  performCleanup() {
    if (!this.renderer) return;

    // Dispose of unused geometries and materials
    this.scene?.traverse((object) => {
      if (object.isMesh) {
        if (object.geometry && object.geometry.dispose) {
          // Check if geometry is shared
          if (this.getGeometryRefCount(object.geometry) <= 1) {
            object.geometry.dispose();
          }
        }
        
        if (object.material) {
          if (Array.isArray(object.material)) {
            object.material.forEach(material => {
              if (this.getMaterialRefCount(material) <= 1) {
                material.dispose();
              }
            });
          } else if (this.getMaterialRefCount(object.material) <= 1) {
            object.material.dispose();
          }
        }
      }
    });

    // Force garbage collection of WebGL resources
    this.renderer.renderLists.dispose();
    this.renderer.info.reset();

    console.log('Performed WebGL cleanup');
  }

  /**
   * Force immediate cleanup
   */
  forceCleanup() {
    // Clear all pools
    this.resourcePools.geometries.clear();
    this.resourcePools.materials.clear();
    this.resourcePools.textures.clear();

    // Perform full cleanup
    this.performCleanup();

    // Reset frame history
    this.frameHistory = [];
  }

  /**
   * Get reference count for geometry
   */
  getGeometryRefCount(geometry) {
    let count = 0;
    this.scene?.traverse((object) => {
      if (object.isMesh && object.geometry === geometry) {
        count++;
      }
    });
    return count;
  }

  /**
   * Get reference count for material
   */
  getMaterialRefCount(material) {
    let count = 0;
    this.scene?.traverse((object) => {
      if (object.isMesh) {
        if (Array.isArray(object.material)) {
          if (object.material.includes(material)) count++;
        } else if (object.material === material) {
          count++;
        }
      }
    });
    return count;
  }

  /**
   * Get current performance statistics
   */
  getStats() {
    return {
      ...this.stats,
      performanceLevel: this.performanceLevel,
      avgFps: this.frameHistory.length > 0 
        ? this.frameHistory.reduce((a, b) => a + b, 0) / this.frameHistory.length 
        : 0,
      frameHistory: [...this.frameHistory]
    };
  }

  /**
   * Get performance recommendations
   */
  getRecommendations() {
    const recommendations = [];
    const stats = this.getStats();

    if (stats.fps < 30) {
      recommendations.push('Consider reducing scene complexity');
      recommendations.push('Enable adaptive quality settings');
    }

    if (stats.drawCalls > 200) {
      recommendations.push('Merge geometries to reduce draw calls');
      recommendations.push('Use instanced rendering for repeated objects');
    }

    if (stats.triangles > 100000) {
      recommendations.push('Implement Level of Detail (LOD) system');
      recommendations.push('Use geometry simplification for distant objects');
    }

    if (stats.memory.geometries > 100) {
      recommendations.push('Dispose of unused geometries');
      recommendations.push('Implement geometry pooling');
    }

    if (stats.memory.textures > 50) {
      recommendations.push('Optimize texture sizes');
      recommendations.push('Use texture atlasing');
      recommendations.push('Enable texture compression');
    }

    return recommendations;
  }

  /**
   * Cleanup when manager is destroyed
   */
  dispose() {
    if (this.frameObserver) {
      this.frameObserver.disconnect();
    }

    if (this.memoryMonitorInterval) {
      clearInterval(this.memoryMonitorInterval);
      this.memoryMonitorInterval = null;
    }

    this.forceCleanup();
    
    // Reset initialization state for proper cleanup
    this.initialized = false;
    this.reactIsolation = false;
    
    console.log('WebGL Performance Manager disposed (React-isolated)');
  }
}

// Create singleton instance
const webglPerformanceManager = new WebGLPerformanceManager();

export default webglPerformanceManager;