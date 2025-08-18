import * as PIXI from 'pixi.js';

export class Application {
    constructor(options = {}) {
        this.options = {
            width: options.width || 1280,
            height: options.height || 720,
            backgroundColor: options.backgroundColor || 0x1a1a1a,
            antialias: options.antialias !== undefined ? options.antialias : true,
            resolution: options.resolution || window.devicePixelRatio || 1,
            autoDensity: options.autoDensity !== undefined ? options.autoDensity : true,
            powerPreference: options.powerPreference || 'high-performance',
            ...options
        };
        
        this.app = null;
        this.renderer = null;
        this.stage = null;
        this.view = null;
        this.drawCalls = 0;
        
        // Layers for different game elements
        this.layers = {
            terrain: null,
            units: null,
            buildings: null,
            effects: null,
            ui: null
        };
    }
    
    async initialize() {
        // Check WebGL support
        const webglVersion = this.checkWebGLSupport();
        if (!webglVersion) {
            throw new Error('WebGL is not supported in this browser');
        }
        
        console.log(`Initializing with WebGL${webglVersion}`);
        
        // Create PixiJS application (v7 syntax - synchronous)
        this.app = new PIXI.Application({
            width: this.options.width,
            height: this.options.height,
            backgroundColor: this.options.backgroundColor,
            antialias: this.options.antialias,
            resolution: this.options.resolution,
            autoDensity: this.options.autoDensity,
            powerPreference: this.options.powerPreference,
            // WebGL configuration for v7
            forceCanvas: false,
            sharedTicker: true,
            sharedLoader: true
        });
        
        // Store references (in v7, app is ready immediately)
        this.renderer = this.app.renderer;
        this.stage = this.app.stage;
        this.view = this.app.view; // Note: 'view' not 'canvas' in v7
        
        // Configure renderer for optimal performance
        this.configureRenderer();
        
        // Create layer containers
        this.createLayers();
        
        // Add canvas to DOM
        const container = document.getElementById('game-container');
        if (container) {
            container.appendChild(this.view);
        } else {
            document.body.appendChild(this.view);
        }
        
        // Setup render call counter
        this.setupDrawCallCounter();
        
        return this;
    }
    
    checkWebGLSupport() {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
        
        if (!gl) {
            return null;
        }
        
        // Return WebGL version
        return canvas.getContext('webgl2') ? 2 : 1;
    }
    
    configureRenderer() {
        // Configure PIXI settings for v7 (using non-deprecated methods)
        PIXI.settings.ROUND_PIXELS = true;
        
        // Configure batch renderer if available
        if (PIXI.BatchRenderer) {
            PIXI.BatchRenderer.defaultBatchSize = 4096;
        }
        
        // Enable texture garbage collection for v7
        if (this.renderer.textureGC) {
            this.renderer.textureGC.maxIdle = 60 * 60; // 1 hour
            this.renderer.textureGC.checkPeriod = 60 * 10; // Check every 10 minutes
        }
        
        // Set background using new API
        if (this.renderer.background) {
            this.renderer.background.alpha = 1;
            this.renderer.background.color = this.options.backgroundColor;
        }
        
        // Note: clearBeforeRender and preserveDrawingBuffer are read-only in v7
        // They are set during renderer creation
        
        // Enable multi-texture batching if available
        if (this.renderer.gl) {
            const gl = this.renderer.gl;
            const maxTextures = gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS);
            console.log(`Max texture units available: ${maxTextures}`);
        }
    }
    
    createLayers() {
        // Create layer containers in rendering order
        this.layers.terrain = new PIXI.Container();
        this.layers.terrain.name = 'terrain';
        this.layers.terrain.sortableChildren = false;
        
        this.layers.buildings = new PIXI.Container();
        this.layers.buildings.name = 'buildings';
        this.layers.buildings.sortableChildren = true;
        
        this.layers.units = new PIXI.Container();
        this.layers.units.name = 'units';
        this.layers.units.sortableChildren = true;
        
        this.layers.effects = new PIXI.Container();
        this.layers.effects.name = 'effects';
        this.layers.effects.sortableChildren = false;
        
        this.layers.ui = new PIXI.Container();
        this.layers.ui.name = 'ui';
        this.layers.ui.sortableChildren = false;
        
        // Add layers to stage in correct order
        this.stage.addChild(this.layers.terrain);
        this.stage.addChild(this.layers.buildings);
        this.stage.addChild(this.layers.units);
        this.stage.addChild(this.layers.effects);
        this.stage.addChild(this.layers.ui);
    }
    
    setupDrawCallCounter() {
        // Override render method to count draw calls
        const originalRender = this.renderer.render.bind(this.renderer);
        let frameDrawCalls = 0;
        
        // Hook into WebGL context to count draw calls
        if (this.renderer.gl) {
            const gl = this.renderer.gl;
            const originalDrawElements = gl.drawElements.bind(gl);
            const originalDrawArrays = gl.drawArrays.bind(gl);
            
            gl.drawElements = function(...args) {
                frameDrawCalls++;
                return originalDrawElements.apply(this, args);
            };
            
            gl.drawArrays = function(...args) {
                frameDrawCalls++;
                return originalDrawArrays.apply(this, args);
            };
        }
        
        this.renderer.render = (...args) => {
            frameDrawCalls = 0;
            const result = originalRender(...args);
            this.drawCalls = frameDrawCalls;
            return result;
        };
    }
    
    render(interpolation = 1) {
        // Render with interpolation support
        this.renderer.render(this.stage);
    }
    
    resize(width, height) {
        this.renderer.resize(width, height);
        this.view.style.width = `${width}px`;
        this.view.style.height = `${height}px`;
    }
    
    destroy() {
        this.app.destroy(true, {
            children: true,
            texture: true,
            baseTexture: true
        });
    }
    
    // Helper method to add sprites to appropriate layer
    addToLayer(displayObject, layerName) {
        if (this.layers[layerName]) {
            this.layers[layerName].addChild(displayObject);
        } else {
            console.warn(`Layer '${layerName}' does not exist`);
            this.stage.addChild(displayObject);
        }
    }
    
    // Get statistics for performance monitoring
    getStats() {
        return {
            drawCalls: this.drawCalls,
            textureCount: Object.keys(PIXI.utils.TextureCache).length || 0,
            spriteCount: this.countSprites(this.stage),
            rendererType: this.renderer.type === 1 ? 'WebGL' : 'Canvas' // v7 uses numeric types
        };
    }
    
    countSprites(container) {
        let count = 0;
        container.children.forEach(child => {
            if (child instanceof PIXI.Sprite) {
                count++;
            }
            if (child instanceof PIXI.Container) {
                count += this.countSprites(child);
            }
        });
        return count;
    }
}