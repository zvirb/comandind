import * as PIXI from 'pixi.js';
// Enable CSP support for unsafe-eval restrictions
import '@pixi/unsafe-eval';
import { WebGLContextManager } from '../rendering/WebGLContextManager.js';

export class Application {
    constructor(options = {}) {
        this.options = {
            width: options.width || 1280,
            height: options.height || 720,
            backgroundColor: options.backgroundColor || 0x1a1a1a,
            antialias: options.antialias !== undefined ? options.antialias : true,
            resolution: options.resolution || (typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1,
            autoDensity: options.autoDensity !== undefined ? options.autoDensity : true,
            powerPreference: options.powerPreference || 'high-performance',
            ...options
        };
        
        this.app = null;
        this.renderer = null;
        this.stage = null;
        this.view = null;
        this.drawCalls = 0;
        this.contextManager = null;
        this.webglVersion = 0;
        this.fallbackMode = false;
        
        // WebGL2 specific features
        this.webgl2Features = {
            instancing: false,
            textureArrays: false,
            uniformBuffers: false
        };
        
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
        // Check WebGL support with detailed analysis
        const webglResult = this.checkWebGLSupport();
        if (!webglResult.supported) {
            console.warn('⚠️ WebGL not supported, attempting Canvas fallback');
            return this.initializeCanvasFallback(webglResult.reason);
        }
        
        this.webglVersion = webglResult.version;
        console.log(`🎮 Initializing with WebGL${this.webglVersion}`);
        
        try {
            // Create PixiJS application with enhanced error handling
            this.app = await this.createPixiApplication();
            
            // Initialize context manager after successful app creation
            this.contextManager = new WebGLContextManager(this.app);
            
            // Set up WebGL2 feature detection
            if (this.webglVersion === 2) {
                this.detectWebGL2Features();
            }
            
        } catch (error) {
            console.error('❌ Failed to create WebGL application:', error);
            return this.initializeCanvasFallback(error.message);
        }
        
        // Store references (in v7, app is ready immediately)
        this.renderer = this.app.renderer;
        this.stage = this.app.stage;
        // PixiJS v7 canvas access - use renderer.view or app.canvas
        this.view = this.app.canvas || this.app.view || this.renderer.view;
        
        // Complete the initialization process
        return this.completeInitialization();
    }
    
    checkWebGLSupport() {
        const canvas = document.createElement('canvas');
        let gl = null;
        let version = 0;
        let reason = '';
        
        try {
            // Try WebGL2 first
            gl = canvas.getContext('webgl2', {
                powerPreference: this.options.powerPreference,
                antialias: this.options.antialias,
                alpha: false
            });
            
            if (gl) {
                version = 2;
            } else {
                // Fallback to WebGL1
                gl = canvas.getContext('webgl', {
                    powerPreference: this.options.powerPreference,
                    antialias: this.options.antialias,
                    alpha: false
                }) || canvas.getContext('experimental-webgl');
                
                if (gl) {
                    version = 1;
                } else {
                    reason = 'WebGL not supported by browser';
                }
            }
            
            if (gl) {
                // Test basic WebGL functionality
                const testSuccess = this.testBasicWebGLFunctionality(gl);
                if (!testSuccess.success) {
                    gl = null;
                    reason = testSuccess.reason;
                }
            }
            
        } catch (error) {
            gl = null;
            reason = `WebGL initialization error: ${error.message}`;
        }
        
        // Cleanup test canvas
        if (canvas.parentNode) {
            canvas.parentNode.removeChild(canvas);
        }
        
        return {
            supported: !!gl,
            version: version,
            reason: reason,
            context: gl
        };
    }
    
    /**
     * Test basic WebGL functionality
     */
    testBasicWebGLFunctionality(gl) {
        try {
            // Test shader compilation
            const vertexShader = gl.createShader(gl.VERTEX_SHADER);
            const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
            
            gl.shaderSource(vertexShader, 'attribute vec2 position; void main() { gl_Position = vec4(position, 0.0, 1.0); }');
            gl.shaderSource(fragmentShader, 'precision mediump float; void main() { gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0); }');
            
            gl.compileShader(vertexShader);
            gl.compileShader(fragmentShader);
            
            if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
                return { success: false, reason: 'Vertex shader compilation failed' };
            }
            
            if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
                return { success: false, reason: 'Fragment shader compilation failed' };
            }
            
            // Test program linking
            const program = gl.createProgram();
            gl.attachShader(program, vertexShader);
            gl.attachShader(program, fragmentShader);
            gl.linkProgram(program);
            
            if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
                return { success: false, reason: 'Shader program linking failed' };
            }
            
            // Test buffer creation
            const buffer = gl.createBuffer();
            if (!buffer) {
                return { success: false, reason: 'Buffer creation failed' };
            }
            
            // Test texture creation
            const texture = gl.createTexture();
            if (!texture) {
                return { success: false, reason: 'Texture creation failed' };
            }
            
            // Cleanup
            gl.deleteShader(vertexShader);
            gl.deleteShader(fragmentShader);
            gl.deleteProgram(program);
            gl.deleteBuffer(buffer);
            gl.deleteTexture(texture);
            
            return { success: true };
            
        } catch (error) {
            return { success: false, reason: `WebGL functionality test failed: ${error.message}` };
        }
    }
    
    /**
     * Create PIXI application with enhanced configuration
     */
    async createPixiApplication() {
        const appConfig = {
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
            sharedLoader: true,
            // Enhanced context attributes
            alpha: false,
            premultipliedAlpha: true,
            preserveDrawingBuffer: false,
            stencil: true,
            depth: false
        };
        
        // Create application with retry logic
        let attempts = 0;
        const maxAttempts = 3;
        
        while (attempts < maxAttempts) {
            try {
                const app = new PIXI.Application(appConfig);
                
                // Verify the application was created successfully
                if (!app || !app.renderer || !app.stage) {
                    throw new Error('PIXI Application incomplete after creation');
                }
                
                // Test that WebGL context is working
                if (app.renderer.type === PIXI.RENDERER_TYPE.WEBGL && !app.renderer.gl) {
                    throw new Error('WebGL renderer created but no GL context available');
                }
                
                return app;
                
            } catch (error) {
                attempts++;
                console.warn(`⚠️ PIXI Application creation attempt ${attempts}/${maxAttempts} failed:`, error.message);
                
                if (attempts < maxAttempts) {
                    // Try with reduced settings on retry
                    if (attempts === 2) {
                        appConfig.antialias = false;
                        appConfig.resolution = 1;
                    }
                    
                    // Wait before retry
                    await new Promise(resolve => setTimeout(resolve, 100 * attempts));
                } else {
                    throw error;
                }
            }
        }
    }
    
    /**
     * Initialize Canvas fallback when WebGL fails
     */
    async initializeCanvasFallback(reason) {
        console.log(`🎨 Initializing Canvas fallback (Reason: ${reason})`);
        this.fallbackMode = true;
        
        try {
            this.app = new PIXI.Application({
                width: this.options.width,
                height: this.options.height,
                backgroundColor: this.options.backgroundColor,
                forceCanvas: true // Force Canvas renderer
            });
            
            console.warn('⚠️ Running in Canvas mode - performance may be reduced');
            
        } catch (error) {
            console.error('💀 Canvas fallback also failed:', error);
            throw new Error(`Both WebGL and Canvas initialization failed. WebGL: ${reason}, Canvas: ${error.message}`);
        }
        
        // Continue with standard initialization
        this.renderer = this.app.renderer;
        this.stage = this.app.stage;
        this.view = this.app.canvas || this.app.view || this.renderer.view;
        
        // Add fallback indicator
        this.addFallbackIndicator();
        
        return this.completeInitialization();
    }
    
    /**
     * Detect WebGL2 specific features
     */
    detectWebGL2Features() {
        if (!this.renderer || !this.renderer.gl) return;
        
        const gl = this.renderer.gl;
        
        // Check for instancing support
        this.webgl2Features.instancing = gl instanceof WebGL2RenderingContext;
        
        // Check for texture arrays
        try {
            const ext = gl.getExtension('WEBGL_texture_arrays') || 
                       (gl instanceof WebGL2RenderingContext);
            this.webgl2Features.textureArrays = !!ext;
        } catch (e) {
            this.webgl2Features.textureArrays = false;
        }
        
        // Check for uniform buffer objects
        this.webgl2Features.uniformBuffers = gl instanceof WebGL2RenderingContext;
        
        console.log('🔧 WebGL2 Features:', this.webgl2Features);
    }
    
    /**
     * Add visual indicator for fallback mode
     */
    addFallbackIndicator() {
        const indicator = document.createElement('div');
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(255, 165, 0, 0.9);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 1000;
        `;
        indicator.textContent = 'Canvas Mode';
        indicator.title = 'Running in Canvas fallback mode - WebGL unavailable';
        
        document.body.appendChild(indicator);
        
        // Remove after 10 seconds
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 10000);
    }
    
    /**
     * Complete initialization after renderer setup
     */
    completeInitialization() {
        // CRITICAL FIX: Verify canvas element exists
        if (!this.view) {
            console.error('PIXI Application view/canvas is null!');
            console.error('App object:', this.app);
            console.error('Available properties:', Object.keys(this.app));
            throw new Error('PIXI Application failed to create canvas element');
        }
        
        console.log('✅ PIXI Application created successfully');
        console.log('Canvas element:', this.view);
        console.log('Canvas dimensions:', this.view.width, 'x', this.view.height);
        
        // Configure renderer for optimal performance
        this.configureRenderer();
        
        // Create layer containers
        this.createLayers();
        
        // Add canvas to DOM
        const container = document.getElementById('game-container');
        if (container) {
            console.log('Adding canvas to game-container');
            container.appendChild(this.view);
            console.log('✅ Canvas successfully added to DOM');
        } else {
            console.warn('game-container not found, adding to document.body');
            document.body.appendChild(this.view);
            console.log('✅ Canvas added to document.body');
        }
        
        // Verify canvas is in DOM and visible
        if (!document.body.contains(this.view)) {
            throw new Error('Canvas was not properly added to DOM');
        }
        
        // Log canvas styling for debugging
        console.log('Canvas computed style:', {
            display: window.getComputedStyle(this.view).display,
            visibility: window.getComputedStyle(this.view).visibility,
            width: window.getComputedStyle(this.view).width,
            height: window.getComputedStyle(this.view).height
        });
        
        // Setup render call counter
        this.setupDrawCallCounter();
        
        return this;
    }
    
    configureRenderer() {
        // Configure PIXI settings for v7 (using non-deprecated methods)
        PIXI.settings.ROUND_PIXELS = true;
        
        // Configure batch renderer if available
        if (PIXI.BatchRenderer) {
            // Adjust batch size based on renderer type and device capabilities
            if (this.fallbackMode) {
                PIXI.BatchRenderer.defaultBatchSize = 1024; // Smaller for Canvas
            } else {
                PIXI.BatchRenderer.defaultBatchSize = this.webglVersion === 2 ? 8192 : 4096;
            }
        }
        
        // Enable texture garbage collection for v7
        if (this.renderer.textureGC) {
            this.renderer.textureGC.maxIdle = 60 * 60; // 1 hour
            this.renderer.textureGC.checkPeriod = 60 * 10; // Check every 10 minutes
            
            // More aggressive GC for fallback mode
            if (this.fallbackMode) {
                this.renderer.textureGC.maxIdle = 30 * 60; // 30 minutes
                this.renderer.textureGC.checkPeriod = 60 * 5; // Check every 5 minutes
            }
        }
        
        // Set background using new API
        if (this.renderer.background) {
            this.renderer.background.alpha = 1;
            this.renderer.background.color = this.options.backgroundColor;
        }
        
        // WebGL-specific configuration
        if (this.renderer.gl && !this.fallbackMode) {
            const gl = this.renderer.gl;
            
            try {
                // Get and log WebGL capabilities
                const maxTextures = gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS);
                const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
                const maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
                const maxVaryingVectors = gl.getParameter(gl.MAX_VARYING_VECTORS);
                
                console.log('📊 WebGL Capabilities:');
                console.log(`   Max texture units: ${maxTextures}`);
                console.log(`   Max texture size: ${maxTextureSize}px`);
                console.log(`   Max vertex attributes: ${maxVertexAttribs}`);
                console.log(`   Max varying vectors: ${maxVaryingVectors}`);
                
                // Check for useful extensions
                const extensions = [
                    'OES_vertex_array_object',
                    'WEBGL_depth_texture',
                    'EXT_texture_filter_anisotropic',
                    'WEBGL_compressed_texture_s3tc'
                ];
                
                console.log('   Available extensions:');
                extensions.forEach(ext => {
                    const supported = gl.getExtension(ext) !== null;
                    console.log(`     ${ext}: ${supported ? '✅' : '❌'}`);
                });
                
                // Configure WebGL state for optimal performance
                gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
                
                // Warn about potential issues
                if (maxTextures < 8) {
                    console.warn('⚠️ Low texture unit count - may impact batching performance');
                }
                
                if (maxTextureSize < 2048) {
                    console.warn('⚠️ Small max texture size - may impact atlas efficiency');
                }
                
            } catch (error) {
                console.error('❌ Error querying WebGL capabilities:', error);
            }
        } else if (this.fallbackMode) {
            console.log('🎨 Canvas renderer configured with reduced settings');
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
        // Clean up context manager first
        if (this.contextManager) {
            this.contextManager.destroy();
            this.contextManager = null;
        }
        
        // Destroy PIXI application
        if (this.app) {
            this.app.destroy(true, {
                children: true,
                texture: true,
                baseTexture: true
            });
        }
        
        console.log('🗑️ Application destroyed');
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
        const baseStats = {
            drawCalls: this.drawCalls,
            textureCount: Object.keys(PIXI.utils.TextureCache).length || 0,
            spriteCount: this.countSprites(this.stage),
            rendererType: this.renderer.type === 1 ? 'WebGL' : 'Canvas', // v7 uses numeric types
            webglVersion: this.webglVersion,
            fallbackMode: this.fallbackMode
        };
        
        // Add WebGL context stats if available
        if (this.contextManager) {
            const contextStats = this.contextManager.getStats();
            baseStats.context = {
                healthy: contextStats.health.healthy,
                lost: contextStats.contextLost,
                restoreAttempts: contextStats.restoreAttempts,
                textureMemoryMB: (contextStats.textureMemoryUsed / (1024 * 1024)).toFixed(2),
                maxTextureUnits: contextStats.maxTextureUnits,
                maxTextureSize: contextStats.maxTextureSize
            };
        }
        
        // Add WebGL2 feature availability
        if (this.webglVersion === 2) {
            baseStats.webgl2Features = this.webgl2Features;
        }
        
        return baseStats;
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