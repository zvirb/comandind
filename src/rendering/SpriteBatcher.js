/**
 * WebStrike Command - Custom Sprite Batcher
 * 
 * High-performance sprite batching system optimized for RTS games
 * with thousands of units. Implements advanced culling, sorting,
 * and instanced rendering techniques for maximum performance.
 */

import * as PIXI from "pixi.js";

/**
 * Advanced sprite batching system for RTS games
 * 
 * Features:
 * - Dynamic batching based on texture and blend mode
 * - Frustum culling for off-screen sprites
 * - Depth sorting for proper rendering order
 * - Instanced rendering for identical sprites
 * - Memory pooling for reduced garbage collection
 * - LOD (Level of Detail) system for distant sprites
 */
export class SpriteBatcher {
    constructor(renderer, maxSpritesPerBatch = 1000) {
        this.renderer = renderer;
        this.maxSpritesPerBatch = maxSpritesPerBatch;
        
        // Batching configuration
        this.config = {
            enableCulling: true,
            enableSorting: true,
            enableInstancing: true,
            enableLOD: true,
            lodDistance: 500,
            cullMargin: 100
        };
        
        // Batch management
        this.batches = new Map(); // texture -> batch data
        this.spritePools = new Map(); // texture -> sprite pool
        this.instancePools = new Map(); // texture -> instance pool
        
        // Culling and viewport
        this.viewport = {
            x: 0,
            y: 0,
            width: 1920,
            height: 1080
        };
        
        // Performance tracking
        this.stats = {
            totalSprites: 0,
            visibleSprites: 0,
            batches: 0,
            drawCalls: 0,
            culledSprites: 0,
            instancedSprites: 0,
            lodSprites: 0
        };
        
        // Geometry and buffer management
        this.geometryPool = [];
        this.bufferPool = [];
        this.maxPoolSize = 50;
        
        // LOD system
        this.lodLevels = [
            { distance: 0, scale: 1.0, detail: "high" },
            { distance: 300, scale: 0.8, detail: "medium" },
            { distance: 600, scale: 0.6, detail: "low" },
            { distance: 1000, scale: 0.4, detail: "minimal" }
        ];
        
        // Instancing support
        this.instancedBatches = new Map();
        this.instanceBuffer = null;
        this.instanceGeometry = null;
        
        this.init();
    }

    /**
     * Initialize the sprite batcher
     */
    init() {
        console.log("🎨 Initializing SpriteBatcher...");
        
        // Check for instancing support
        this.supportsInstancing = this.checkInstancedRenderingSupport();
        
        // Create instance rendering resources if supported
        if (this.supportsInstancing && this.config.enableInstancing) {
            this.initInstancedRendering();
        }
        
        // Set up buffer pools
        this.initBufferPools();
        
        console.log(`✅ SpriteBatcher initialized (Instancing: ${this.supportsInstancing ? "ON" : "OFF"})`);
    }

    /**
     * Check if instanced rendering is supported
     */
    checkInstancedRenderingSupport() {
        if (this.renderer.type !== PIXI.RENDERER_TYPE.WEBGL) {
            return false;
        }
        
        const gl = this.renderer.gl;
        return !!(gl.getExtension("ANGLE_instanced_arrays") || 
                 gl instanceof WebGL2RenderingContext);
    }

    /**
     * Initialize instanced rendering resources
     */
    initInstancedRendering() {
        // Create instanced geometry
        this.instanceGeometry = new PIXI.Geometry();
        
        // Define quad vertices (position + UV)
        const vertices = new Float32Array([
            // x, y, u, v
            -0.5, -0.5, 0, 0,
            0.5, -0.5, 1, 0,
            0.5,  0.5, 1, 1,
            -0.5,  0.5, 0, 1
        ]);
        
        const indices = new Uint16Array([0, 1, 2, 0, 2, 3]);
        
        this.instanceGeometry.addAttribute("aVertexPosition", vertices, 2);
        this.instanceGeometry.addAttribute("aTextureCoord", vertices, 2, false, PIXI.TYPES.FLOAT, 4 * 4, 2 * 4);
        this.instanceGeometry.addIndex(indices);
        
        console.log("🔧 Instanced rendering initialized");
    }

    /**
     * Initialize buffer pools for memory management
     */
    initBufferPools() {
        // Pre-allocate some geometries and buffers
        for (let i = 0; i < 10; i++) {
            this.geometryPool.push(new PIXI.Geometry());
            this.bufferPool.push(new Float32Array(this.maxSpritesPerBatch * 4 * 6)); // 4 verts, 6 components
        }
        
        console.log("💾 Buffer pools initialized");
    }

    /**
     * Update viewport for culling calculations
     */
    updateViewport(camera) {
        this.viewport.x = camera.x - this.config.cullMargin;
        this.viewport.y = camera.y - this.config.cullMargin;
        this.viewport.width = camera.viewWidth + (this.config.cullMargin * 2);
        this.viewport.height = camera.viewHeight + (this.config.cullMargin * 2);
    }

    /**
     * Batch and render sprites
     */
    render(sprites, camera) {
        // Reset stats
        this.resetStats();
        
        // Update viewport for culling
        this.updateViewport(camera);
        
        // Clear previous batches
        this.clearBatches();
        
        // Process sprites
        const visibleSprites = this.cullSprites(sprites, camera);
        const sortedSprites = this.sortSprites(visibleSprites);
        const batches = this.createBatches(sortedSprites, camera);
        
        // Render batches
        this.renderBatches(batches);
        
        // Update statistics
        this.stats.totalSprites = sprites.length;
        this.stats.visibleSprites = visibleSprites.length;
        this.stats.batches = batches.length;
        
        return this.stats;
    }

    /**
     * Cull sprites outside the viewport
     */
    cullSprites(sprites, camera) {
        if (!this.config.enableCulling) {
            return sprites;
        }
        
        const visibleSprites = [];
        const viewport = this.viewport;
        
        for (const sprite of sprites) {
            if (this.isSpriteVisible(sprite, viewport)) {
                visibleSprites.push(sprite);
            } else {
                this.stats.culledSprites++;
            }
        }
        
        return visibleSprites;
    }

    /**
     * Check if sprite is visible in viewport
     */
    isSpriteVisible(sprite, viewport) {
        const bounds = sprite.getBounds();
        
        return !(bounds.x > viewport.x + viewport.width ||
                bounds.x + bounds.width < viewport.x ||
                bounds.y > viewport.y + viewport.height ||
                bounds.y + bounds.height < viewport.y);
    }

    /**
     * Sort sprites for optimal rendering
     */
    sortSprites(sprites) {
        if (!this.config.enableSorting) {
            return sprites;
        }
        
        // Sort by:
        // 1. Z-index (depth)
        // 2. Texture (for batching)
        // 3. Blend mode
        return sprites.sort((a, b) => {
            // Z-index first
            if (a.zIndex !== b.zIndex) {
                return a.zIndex - b.zIndex;
            }
            
            // Then by texture
            const textureA = a.texture?.baseTexture?.uid || 0;
            const textureB = b.texture?.baseTexture?.uid || 0;
            if (textureA !== textureB) {
                return textureA - textureB;
            }
            
            // Then by blend mode
            return (a.blendMode || 0) - (b.blendMode || 0);
        });
    }

    /**
     * Create optimized batches from sorted sprites
     */
    createBatches(sprites, camera) {
        const batches = [];
        let currentBatch = null;
        
        for (const sprite of sprites) {
            // Determine LOD level
            const lodLevel = this.getLODLevel(sprite, camera);
            
            // Get batch key
            const batchKey = this.getBatchKey(sprite, lodLevel);
            
            // Start new batch if needed
            if (!currentBatch || currentBatch.key !== batchKey || 
                currentBatch.sprites.length >= this.maxSpritesPerBatch) {
                
                if (currentBatch) {
                    batches.push(currentBatch);
                }
                
                currentBatch = {
                    key: batchKey,
                    texture: sprite.texture,
                    blendMode: sprite.blendMode || PIXI.BLEND_MODES.NORMAL,
                    lodLevel: lodLevel,
                    sprites: [],
                    instanceData: null
                };
            }
            
            currentBatch.sprites.push(sprite);
        }
        
        if (currentBatch && currentBatch.sprites.length > 0) {
            batches.push(currentBatch);
        }
        
        return batches;
    }

    /**
     * Get LOD level for sprite based on distance from camera
     */
    getLODLevel(sprite, camera) {
        if (!this.config.enableLOD) {
            return this.lodLevels[0];
        }
        
        // Calculate distance from camera center
        const dx = sprite.x - (camera.x + camera.viewWidth / 2);
        const dy = sprite.y - (camera.y + camera.viewHeight / 2);
        const distance = Math.sqrt(dx * dx + dy * dy) / camera.scale;
        
        // Find appropriate LOD level
        for (let i = this.lodLevels.length - 1; i >= 0; i--) {
            if (distance >= this.lodLevels[i].distance) {
                return this.lodLevels[i];
            }
        }
        
        return this.lodLevels[0];
    }

    /**
     * Generate batch key for grouping sprites
     */
    getBatchKey(sprite, lodLevel) {
        const textureId = sprite.texture?.baseTexture?.uid || 0;
        const blendMode = sprite.blendMode || 0;
        const lodId = lodLevel.detail;
        
        return `${textureId}_${blendMode}_${lodId}`;
    }

    /**
     * Render all batches
     */
    renderBatches(batches) {
        for (const batch of batches) {
            if (this.shouldUseInstancing(batch)) {
                this.renderInstancedBatch(batch);
            } else {
                this.renderStandardBatch(batch);
            }
            
            this.stats.drawCalls++;
        }
    }

    /**
     * Check if batch should use instanced rendering
     */
    shouldUseInstancing(batch) {
        return this.supportsInstancing && 
               this.config.enableInstancing && 
               batch.sprites.length > 10 && // Minimum threshold
               this.areSpritesInstanceable(batch.sprites);
    }

    /**
     * Check if sprites in batch can be instanced
     */
    areSpritesInstanceable(sprites) {
        if (sprites.length === 0) return false;
        
        const first = sprites[0];
        const firstTexture = first.texture;
        const firstBlendMode = first.blendMode || PIXI.BLEND_MODES.NORMAL;
        
        // Check if all sprites use same texture and blend mode
        for (let i = 1; i < sprites.length; i++) {
            const sprite = sprites[i];
            if (sprite.texture !== firstTexture || 
                (sprite.blendMode || PIXI.BLEND_MODES.NORMAL) !== firstBlendMode) {
                return false;
            }
        }
        
        return true;
    }

    /**
     * Render batch using instanced rendering
     */
    renderInstancedBatch(batch) {
        // Prepare instance data
        const instanceData = this.prepareInstanceData(batch.sprites, batch.lodLevel);
        
        // Create or get instance buffer
        const instanceBuffer = this.getInstanceBuffer(instanceData);
        
        // Set up instanced geometry
        const geometry = this.instanceGeometry.clone();
        geometry.addAttribute("aInstanceTransform", instanceBuffer, 4, false, PIXI.TYPES.FLOAT, 0, 0, true);
        geometry.addAttribute("aInstanceColor", instanceBuffer, 4, false, PIXI.TYPES.FLOAT, 16, 16, true);
        
        // Create mesh with instanced geometry
        const material = this.getInstancedMaterial(batch.texture, batch.blendMode);
        const mesh = new PIXI.Mesh(geometry, material);
        
        // Render
        this.renderer.render(mesh);
        
        this.stats.instancedSprites += batch.sprites.length;
        
        // Return resources to pool
        this.returnGeometryToPool(geometry);
    }

    /**
     * Prepare instance data for batch
     */
    prepareInstanceData(sprites, lodLevel) {
        const instanceCount = sprites.length;
        const dataPerInstance = 8; // 4 for transform matrix, 4 for color
        const buffer = new Float32Array(instanceCount * dataPerInstance);
        
        for (let i = 0; i < instanceCount; i++) {
            const sprite = sprites[i];
            const offset = i * dataPerInstance;
            
            // Transform matrix (simplified 2D)
            const scale = sprite.scale.x * lodLevel.scale;
            const cos = Math.cos(sprite.rotation) * scale;
            const sin = Math.sin(sprite.rotation) * scale;
            
            buffer[offset + 0] = cos;     // a
            buffer[offset + 1] = sin;     // b
            buffer[offset + 2] = -sin;    // c
            buffer[offset + 3] = cos;     // d
            buffer[offset + 4] = sprite.x; // tx
            buffer[offset + 5] = sprite.y; // ty
            
            // Color and alpha
            const tint = sprite.tint || 0xFFFFFF;
            buffer[offset + 6] = ((tint >> 16) & 0xFF) / 255; // r
            buffer[offset + 7] = ((tint >> 8) & 0xFF) / 255;  // g
            buffer[offset + 8] = (tint & 0xFF) / 255;         // b
            buffer[offset + 9] = sprite.alpha || 1.0;         // a
        }
        
        return buffer;
    }

    /**
     * Get or create instance buffer
     */
    getInstanceBuffer(data) {
        // For simplicity, create new buffer each time
        // In production, implement buffer pooling
        return new PIXI.Buffer(data, false, false);
    }

    /**
     * Get instanced material for texture
     */
    getInstancedMaterial(texture, blendMode) {
        // Create simple instanced shader material
        const vertexShader = `
            attribute vec2 aVertexPosition;
            attribute vec2 aTextureCoord;
            attribute vec4 aInstanceTransform;
            attribute vec4 aInstanceColor;
            
            uniform mat3 projectionMatrix;
            
            varying vec2 vTextureCoord;
            varying vec4 vColor;
            
            void main() {
                vec2 position = aVertexPosition;
                position.x = position.x * aInstanceTransform.x + position.y * aInstanceTransform.z + aInstanceTransform.w;
                position.y = position.x * aInstanceTransform.y + position.y * aInstanceTransform.w + aInstanceTransform.z;
                
                gl_Position = vec4((projectionMatrix * vec3(position, 1.0)).xy, 0.0, 1.0);
                vTextureCoord = aTextureCoord;
                vColor = aInstanceColor;
            }
        `;
        
        const fragmentShader = `
            precision mediump float;
            
            varying vec2 vTextureCoord;
            varying vec4 vColor;
            
            uniform sampler2D uSampler;
            
            void main() {
                gl_FragColor = texture2D(uSampler, vTextureCoord) * vColor;
            }
        `;
        
        return new PIXI.Shader.from(vertexShader, fragmentShader, {
            uSampler: texture
        });
    }

    /**
     * Render batch using standard rendering
     */
    renderStandardBatch(batch) {
        // Group sprites and render as traditional batch
        const sprites = batch.sprites;
        const lodLevel = batch.lodLevel;
        
        // Apply LOD scaling
        for (const sprite of sprites) {
            if (lodLevel.scale !== 1.0) {
                sprite.scale.x *= lodLevel.scale;
                sprite.scale.y *= lodLevel.scale;
                this.stats.lodSprites++;
            }
        }
        
        // Use PixiJS built-in batch renderer
        const batchRenderer = this.renderer.plugins.batch;
        if (batchRenderer) {
            batchRenderer.setObjectRenderer(this.renderer.plugins.sprite);
            
            for (const sprite of sprites) {
                batchRenderer.render(sprite);
            }
            
            batchRenderer.flush();
        }
        
        // Restore original scaling
        for (const sprite of sprites) {
            if (lodLevel.scale !== 1.0) {
                sprite.scale.x /= lodLevel.scale;
                sprite.scale.y /= lodLevel.scale;
            }
        }
    }

    /**
     * Get geometry from pool or create new
     */
    getGeometryFromPool() {
        return this.geometryPool.pop() || new PIXI.Geometry();
    }

    /**
     * Return geometry to pool
     */
    returnGeometryToPool(geometry) {
        if (this.geometryPool.length < this.maxPoolSize) {
            geometry.dispose();
            this.geometryPool.push(geometry);
        } else {
            geometry.destroy();
        }
    }

    /**
     * Clear all batches
     */
    clearBatches() {
        this.batches.clear();
        this.instancedBatches.clear();
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.stats.totalSprites = 0;
        this.stats.visibleSprites = 0;
        this.stats.batches = 0;
        this.stats.drawCalls = 0;
        this.stats.culledSprites = 0;
        this.stats.instancedSprites = 0;
        this.stats.lodSprites = 0;
    }

    /**
     * Get current statistics
     */
    getStats() {
        return { ...this.stats };
    }

    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log("⚙️  SpriteBatcher config updated:", this.config);
    }

    /**
     * Set maximum sprites per batch
     */
    setMaxSpritesPerBatch(max) {
        this.maxSpritesPerBatch = max;
        console.log(`📊 Max sprites per batch: ${max}`);
    }

    /**
     * Add LOD level
     */
    addLODLevel(distance, scale, detail) {
        this.lodLevels.push({ distance, scale, detail });
        this.lodLevels.sort((a, b) => a.distance - b.distance);
        console.log(`🔍 LOD level added: ${detail} at ${distance}px (${scale}x scale)`);
    }

    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        const total = this.stats.totalSprites;
        const visible = this.stats.visibleSprites;
        const instanced = this.stats.instancedSprites;
        const lod = this.stats.lodSprites;
        
        return {
            cullEfficiency: total > 0 ? ((total - visible) / total) : 0,
            instancedRatio: visible > 0 ? (instanced / visible) : 0,
            lodRatio: visible > 0 ? (lod / visible) : 0,
            batchEfficiency: this.stats.batches > 0 ? (visible / this.stats.batches) : 0,
            drawCallReduction: total > 0 ? (1 - this.stats.drawCalls / total) : 0
        };
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        // Clean up geometry pools
        for (const geometry of this.geometryPool) {
            geometry.destroy();
        }
        
        // Clean up instance resources
        if (this.instanceGeometry) {
            this.instanceGeometry.destroy();
        }
        
        // Clear maps
        this.batches.clear();
        this.spritePools.clear();
        this.instancePools.clear();
        this.instancedBatches.clear();
        
        console.log("🗑️  SpriteBatcher destroyed");
    }
}