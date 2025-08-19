/**
 * WebGL Context Manager for Command & Independent Thought
 * 
 * Handles WebGL context loss/restore, texture management, and GPU memory pressure
 * Critical for maintaining stability with thousands of sprites and large texture atlases
 */

import * as PIXI from 'pixi.js';

export class WebGLContextManager {
    constructor(application) {
        this.app = application;
        this.canvas = null;
        this.gl = null;
        this.contextLost = false;
        this.restoreAttempts = 0;
        this.maxRestoreAttempts = 5;
        this.retryDelays = [1000, 2000, 5000, 10000, 20000]; // Progressive backoff in ms
        
        // Context monitoring
        this.contextStats = {
            textureUnitsUsed: 0,
            maxTextureUnits: 0,
            textureMemoryUsed: 0,
            maxTextureSize: 0,
            drawingBufferSize: { width: 0, height: 0 }
        };
        
        // Texture management
        this.textureCache = new Map();
        this.texturePool = new Map();
        this.pendingTextures = new Set();
        
        // Context state management
        this.contextState = {
            viewport: { x: 0, y: 0, width: 0, height: 0 },
            clearColor: [0, 0, 0, 1],
            blendMode: null,
            activeProgram: null,
            boundTextures: new Map(),
            vertexArrays: new Map(),
            framebuffers: new Map()
        };
        
        // Recovery system
        this.recoveryState = {
            isRecovering: false,
            recoveryStartTime: 0,
            recoveryTimeout: 30000, // 30 seconds
            progressCallback: null,
            validationSteps: []
        };
        
        // Extension support tracking
        this.extensions = {
            required: ['WEBGL_lose_context'],
            optional: ['EXT_texture_filter_anisotropic', 'WEBGL_compressed_texture_s3tc'],
            supported: new Map(),
            fallbacks: new Map()
        };
        
        // Memory pressure thresholds (in MB)
        this.memoryThresholds = {
            warning: 512,    // 512MB
            critical: 1024,  // 1GB
            maximum: 2048    // 2GB
        };
        
        // Fallback options
        this.fallbackOptions = {
            reduceTextureQuality: true,
            disableAntialiasing: true,
            reduceMaxTextureSize: true,
            enableTextureCompression: true,
            enableCanvasFallback: true,
            maxCanvasSize: 2048
        };
        
        // User notification system
        this.notificationState = {
            currentNotification: null,
            notificationQueue: [],
            showUserFeedback: true
        };
        
        // Event listener tracking for cleanup
        this.isDestroyed = false;
        this.contextLostHandler = null;
        this.contextRestoredHandler = null;
        this.memoryMonitorInterval = null;
        
        this.init();
    }
    
    /**
     * Initialize context management
     */
    init() {
        console.log('🔧 Initializing WebGL Context Manager...');
        
        // Set up context event listeners after application is ready
        if (this.app && this.app.view) {
            this.setupContextListeners();
            this.analyzeWebGLCapabilities();
        } else {
            console.warn('⚠️ Application not ready, deferring context setup');
        }
    }
    
    /**
     * Set up WebGL context event listeners
     */
    setupContextListeners() {
        this.canvas = this.app.view;
        this.gl = this.app.renderer.gl;
        
        if (!this.canvas || !this.gl) {
            console.error('❌ Failed to get canvas or WebGL context');
            return;
        }
        
        // Store initial context state
        this.captureContextState();
        
        // Validate and cache extension support
        this.validateExtensions();
        
        // Create bound handlers for proper cleanup
        this.contextLostHandler = (event) => {
            if (this.isDestroyed) return;
            
            console.error('🚨 WebGL Context Lost!');
            event.preventDefault(); // Prevent default browser behavior
            
            // Enhanced logging
            const contextInfo = {
                timestamp: Date.now(),
                reason: event.statusMessage || 'Unknown',
                userAgent: navigator.userAgent,
                viewport: [this.gl?.drawingBufferWidth, this.gl?.drawingBufferHeight],
                memoryPressure: this.contextStats.textureMemoryUsed
            };
            
            console.error('Context loss details:', contextInfo);
            this.handleContextLost(contextInfo);
        };
        
        this.contextRestoredHandler = (event) => {
            if (this.isDestroyed) return;
            
            console.log('✅ WebGL Context Restored');
            const restoreInfo = {
                timestamp: Date.now(),
                attempt: this.restoreAttempts,
                timeLost: Date.now() - (this.contextLostTime || Date.now())
            };
            
            this.handleContextRestored(restoreInfo);
        };
        
        // Add event listeners with bound handlers
        this.canvas.addEventListener('webglcontextlost', this.contextLostHandler);
        this.canvas.addEventListener('webglcontextrestored', this.contextRestoredHandler);
        
        // Monitor memory pressure
        this.startMemoryMonitoring();
        
        // Setup periodic health checks
        this.startHealthMonitoring();
        
        console.log('✅ Enhanced WebGL context listeners established');
    }
    
    /**
     * Analyze WebGL capabilities and limits
     */
    analyzeWebGLCapabilities() {
        if (!this.gl) {
            console.error('❌ No WebGL context available for analysis');
            return;
        }
        
        const gl = this.gl;
        
        // Gather context information
        this.contextStats.maxTextureUnits = gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS);
        this.contextStats.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        this.contextStats.drawingBufferSize = {
            width: gl.drawingBufferWidth,
            height: gl.drawingBufferHeight
        };
        
        // WebGL version and extensions
        const version = gl.getParameter(gl.VERSION);
        const renderer = gl.getParameter(gl.RENDERER);
        const vendor = gl.getParameter(gl.VENDOR);
        
        console.log('📊 WebGL Capabilities Analysis:');
        console.log(`   Version: ${version}`);
        console.log(`   Renderer: ${renderer}`);
        console.log(`   Vendor: ${vendor}`);
        console.log(`   Max Texture Units: ${this.contextStats.maxTextureUnits}`);
        console.log(`   Max Texture Size: ${this.contextStats.maxTextureSize}px`);
        console.log(`   Drawing Buffer: ${this.contextStats.drawingBufferSize.width}x${this.contextStats.drawingBufferSize.height}`);
        
        // Check for useful extensions
        const extensions = [
            'EXT_texture_filter_anisotropic',
            'WEBGL_compressed_texture_s3tc',
            'WEBGL_compressed_texture_pvrtc',
            'WEBGL_compressed_texture_etc1',
            'OES_texture_float',
            'ANGLE_instanced_arrays',
            'WEBGL_lose_context' // For testing
        ];
        
        console.log('   Extensions:');
        extensions.forEach(ext => {
            const supported = gl.getExtension(ext) !== null;
            console.log(`     ${ext}: ${supported ? '✅' : '❌'}`);
        });
        
        // Check memory info if available
        const memoryInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (memoryInfo) {
            const unmaskedRenderer = gl.getParameter(memoryInfo.UNMASKED_RENDERER_WEBGL);
            const unmaskedVendor = gl.getParameter(memoryInfo.UNMASKED_VENDOR_WEBGL);
            console.log(`   Unmasked Renderer: ${unmaskedRenderer}`);
            console.log(`   Unmasked Vendor: ${unmaskedVendor}`);
        }
    }
    
    /**
     * Handle WebGL context loss with enhanced recovery
     */
    handleContextLost(contextInfo = {}) {
        this.contextLost = true;
        this.contextLostTime = Date.now();
        this.restoreAttempts++;
        
        console.log(`🚨 Context Loss Event #${this.restoreAttempts}`);
        console.log('Loss details:', contextInfo);
        
        // Show user notification (if in browser environment)
        if (typeof document !== 'undefined') {
            this.showContextLossNotification();
        }
        
        // Stop all rendering operations gracefully
        this.pauseRenderingOperations();
        
        // Preserve current game state
        this.preserveGameState();
        
        // Clear texture caches and free memory
        this.clearTextureCaches();
        
        // Dispatch enhanced custom event
        const contextLostEvent = new CustomEvent('webgl-context-lost', {
            detail: {
                attempt: this.restoreAttempts,
                maxAttempts: this.maxRestoreAttempts,
                contextInfo,
                timestamp: this.contextLostTime,
                canFallback: this.fallbackOptions.enableCanvasFallback
            }
        });
        
        // Dispatch event if in browser environment
        if (typeof window !== 'undefined') {
            window.dispatchEvent(contextLostEvent);
        }
        
        // Try to force context restoration with improved logic
        this.attemptContextRestore();
    }
    
    /**
     * Handle WebGL context restoration with validation
     */
    async handleContextRestored(restoreInfo = {}) {
        console.log('✅ WebGL Context Restored Successfully');
        console.log('Restore info:', restoreInfo);
        
        // Mark recovery as in progress
        this.recoveryState.isRecovering = true;
        this.recoveryState.recoveryStartTime = Date.now();
        
        try {
            // Update progress notification
            this.updateContextNotification('Restoring WebGL context...', 'info');
            
            // Step 1: Validate context health
            const healthCheck = this.checkContextHealth();
            if (!healthCheck.healthy) {
                throw new Error(`Context unhealthy after restoration: ${healthCheck.reason}`);
            }
            
            // Step 2: Re-initialize WebGL state
            await this.reinitializeWebGLState();
            this.updateContextNotification('Reinitializing graphics state...', 'info');
            
            // Step 3: Restore context state
            this.restoreContextState();
            
            // Step 4: Reload critical textures progressively
            await this.reloadTextures((progress) => {
                this.updateContextNotification(`Loading textures... ${Math.round(progress * 100)}%`, 'info');
            });
            
            // Step 5: Validate rendering capabilities
            const renderTest = await this.validateRenderingCapabilities();
            if (!renderTest.success) {
                throw new Error(`Rendering validation failed: ${renderTest.reason}`);
            }
            
            // Step 6: Resume rendering operations
            this.resumeRenderingOperations();
            
            // Clear recovery state
            this.recoveryState.isRecovering = false;
            this.contextLost = false;
            
            // Success notification
            this.updateContextNotification('WebGL context restored successfully!', 'success');
            setTimeout(() => this.hideContextNotification(), 3000);
            
            // Dispatch restoration event with details
            const contextRestoredEvent = new CustomEvent('webgl-context-restored', {
                detail: {
                    restoreInfo,
                    recoveryTime: Date.now() - this.recoveryState.recoveryStartTime,
                    success: true
                }
            });
            if (typeof window !== 'undefined') {
                window.dispatchEvent(contextRestoredEvent);
            }
            
            console.log('🎉 Enhanced context restoration complete');
            
        } catch (error) {
            console.error('❌ Context restoration failed:', error);
            
            // Clear recovery state
            this.recoveryState.isRecovering = false;
            
            // Show error and attempt fallback
            this.updateContextNotification('WebGL restoration failed, attempting fallback...', 'error');
            
            // Try fallback or show error
            if (this.restoreAttempts <= this.maxRestoreAttempts) {
                setTimeout(() => this.attemptContextRestore(), 2000);
            } else {
                this.fallbackToCanvasRenderer();
            }
        }
    }
    
    /**
     * Intelligent context restoration with exponential backoff
     */
    attemptContextRestore() {
        if (this.restoreAttempts > this.maxRestoreAttempts) {
            console.error('💪 Max context restore attempts exceeded');
            this.updateContextNotification('WebGL restore failed, switching to Canvas mode...', 'warning');
            setTimeout(() => this.fallbackToCanvasRenderer(), 2000);
            return;
        }
        
        const delay = this.retryDelays[this.restoreAttempts - 1] || this.retryDelays[this.retryDelays.length - 1];
        
        console.log(`🔄 Attempting context restore (${this.restoreAttempts}/${this.maxRestoreAttempts}) in ${delay}ms`);
        
        // Update user notification
        this.updateContextNotification(
            `Attempting to restore WebGL... (${this.restoreAttempts}/${this.maxRestoreAttempts})`, 
            'info'
        );
        
        // Setup timeout for this restoration attempt
        const restoreTimeout = setTimeout(() => {
            console.warn(`⏰ Restore attempt ${this.restoreAttempts} timed out`);
            
            if (this.restoreAttempts < this.maxRestoreAttempts) {
                this.restoreAttempts++;
                this.attemptContextRestore();
            } else {
                this.fallbackToCanvasRenderer();
            }
        }, this.recoveryState.recoveryTimeout);
        
        // Try to get the context restoration extension
        setTimeout(() => {
            const loseContextExt = this.gl?.getExtension('WEBGL_lose_context');
            if (loseContextExt && loseContextExt.restoreContext) {
                try {
                    loseContextExt.restoreContext();
                    console.log(`🔄 Restore context called for attempt ${this.restoreAttempts}`);
                } catch (error) {
                    console.error('Error calling restoreContext:', error);
                    clearTimeout(restoreTimeout);
                    
                    if (this.restoreAttempts < this.maxRestoreAttempts) {
                        this.restoreAttempts++;
                        this.attemptContextRestore();
                    } else {
                        this.fallbackToCanvasRenderer();
                    }
                }
            } else {
                console.error('WEBGL_lose_context extension not available');
                clearTimeout(restoreTimeout);
                this.fallbackToCanvasRenderer();
            }
        }, delay);
    }
    
    /**
     * Fallback to Canvas renderer when WebGL fails permanently
     */
    fallbackToCanvasRenderer() {
        console.warn('⚠️ Falling back to Canvas renderer');
        
        try {
            // Create new PIXI app with Canvas renderer
            const canvasApp = new PIXI.Application({
                width: this.app.renderer.width,
                height: this.app.renderer.height,
                backgroundColor: this.app.renderer.backgroundColor,
                forceCanvas: true // Force Canvas renderer
            });
            
            // Replace the renderer
            const oldCanvas = this.app.view;
            const newCanvas = canvasApp.view;
            
            // Transfer DOM position
            if (oldCanvas.parentNode) {
                oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);
            }
            
            // Dispatch fallback event
            const fallbackEvent = new CustomEvent('webgl-fallback-canvas');
            if (typeof window !== 'undefined') {
                window.dispatchEvent(fallbackEvent);
            }
            
        } catch (error) {
            console.error('💀 Canvas fallback failed:', error);
            
            // Last resort - show error message
            this.showWebGLErrorMessage();
        }
    }
    
    /**
     * Show WebGL error message to user
     */
    showWebGLErrorMessage() {
        if (typeof document === 'undefined') return;
        
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 0, 0, 0.9);
            color: white;
            padding: 20px;
            border-radius: 10px;
            font-family: Arial, sans-serif;
            text-align: center;
            z-index: 10000;
        `;
        
        errorDiv.innerHTML = `
            <h3>WebGL Error</h3>
            <p>Your browser or graphics driver has encountered an issue.</p>
            <p>Please try:</p>
            <ul style="text-align: left;">
                <li>Refreshing the page</li>
                <li>Updating your browser</li>
                <li>Updating your graphics drivers</li>
                <li>Disabling browser extensions</li>
            </ul>
            <button onclick="window.location.reload()">Reload Page</button>
        `;
        
        if (document.body) {
            document.body.appendChild(errorDiv);
        }
    }
    
    /**
     * Re-initialize WebGL state after context restoration
     */
    reinitializeWebGLState() {
        if (!this.app || !this.app.renderer) return;
        
        const renderer = this.app.renderer;
        
        // Reconfigure renderer
        if (renderer.background) {
            renderer.background.alpha = 1;
            renderer.background.color = this.app.options?.backgroundColor || 0x1a1a1a;
        }
        
        // Re-enable texture garbage collection
        if (renderer.textureGC) {
            renderer.textureGC.maxIdle = 60 * 60;
            renderer.textureGC.checkPeriod = 60 * 10;
        }
        
        // Reconfigure batch renderer
        if (PIXI.BatchRenderer) {
            PIXI.BatchRenderer.defaultBatchSize = 4096;
        }
        
        console.log('✅ WebGL state reinitialized');
    }
    
    /**
     * Clear all texture caches
     */
    clearTextureCaches() {
        this.textureCache.clear();
        this.texturePool.clear();
        this.pendingTextures.clear();
        
        // Clear PIXI texture cache
        if (PIXI.utils && PIXI.utils.TextureCache) {
            Object.keys(PIXI.utils.TextureCache).forEach(key => {
                const texture = PIXI.utils.TextureCache[key];
                if (texture && texture.destroy) {
                    texture.destroy(true);
                }
                delete PIXI.utils.TextureCache[key];
            });
        }
        
        console.log('🗑️ Texture caches cleared');
    }
    
    /**
     * Reload critical textures after context restoration
     */
    async reloadTextures(progressCallback = null) {
        console.log('🔄 Reloading textures...');
        
        // This would typically reload game-critical textures
        // In a real implementation, you'd maintain a list of essential textures
        
        try {
            // Example: reload placeholder textures
            const placeholderTextures = [
                { key: 'unit_placeholder', size: 24 },
                { key: 'building_placeholder', size: 48 },
                { key: 'terrain_placeholder', size: 32 },
                { key: 'effect_placeholder', size: 16 }
            ];
            
            let loadedCount = 0;
            const totalCount = placeholderTextures.length;
            
            for (const textureInfo of placeholderTextures) {
                await this.createPlaceholderTexture(textureInfo.key, textureInfo.size);
                loadedCount++;
                
                // Report progress if callback provided
                if (progressCallback) {
                    progressCallback(loadedCount / totalCount);
                }
                
                // Small delay to prevent blocking
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            
            console.log('✅ Critical textures reloaded');
            
        } catch (error) {
            console.error('❌ Failed to reload textures:', error);
            throw error;
        }
    }
    
    /**
     * Create a placeholder texture
     */
    async createPlaceholderTexture(key, size) {
        if (typeof document === 'undefined') {
            // Return a mock texture for Node.js environment
            return { mock: true, key, size };
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        // Create simple colored rectangle
        ctx.fillStyle = '#666666';
        ctx.fillRect(0, 0, size, size);
        ctx.strokeStyle = '#333333';
        ctx.strokeRect(0, 0, size, size);
        
        // Convert to PIXI texture
        const texture = PIXI.Texture.from(canvas);
        this.textureCache.set(key, texture);
        
        return texture;
    }
    
    /**
     * Start memory monitoring
     */
    startMemoryMonitoring() {
        // Store interval ID for cleanup
        this.memoryMonitorInterval = setInterval(() => {
            if (!this.isDestroyed) {
                this.checkMemoryPressure();
            }
        }, 30000); // Check every 30 seconds
        
        console.log('📊 Memory monitoring started');
    }
    
    /**
     * Check for GPU memory pressure
     */
    checkMemoryPressure() {
        if (!this.gl || this.contextLost) return;
        
        try {
            // Estimate texture memory usage
            let estimatedMemory = 0;
            
            if (PIXI.utils && PIXI.utils.TextureCache) {
                Object.values(PIXI.utils.TextureCache).forEach(texture => {
                    if (texture && texture.baseTexture) {
                        const bt = texture.baseTexture;
                        // Estimate: width * height * 4 bytes (RGBA)
                        estimatedMemory += (bt.width || 0) * (bt.height || 0) * 4;
                    }
                });
            }
            
            this.contextStats.textureMemoryUsed = estimatedMemory;
            const memoryMB = estimatedMemory / (1024 * 1024);
            
            // Check thresholds
            if (memoryMB > this.memoryThresholds.critical) {
                console.warn(`🚨 Critical GPU memory usage: ${memoryMB.toFixed(2)}MB`);
                this.handleMemoryPressure('critical');
            } else if (memoryMB > this.memoryThresholds.warning) {
                console.warn(`⚠️ High GPU memory usage: ${memoryMB.toFixed(2)}MB`);
                this.handleMemoryPressure('warning');
            }
            
        } catch (error) {
            console.error('Error checking memory pressure:', error);
        }
    }
    
    /**
     * Handle memory pressure
     */
    handleMemoryPressure(level) {
        console.log(`🧹 Handling ${level} memory pressure`);
        
        // Trigger texture garbage collection
        if (this.app && this.app.renderer && this.app.renderer.textureGC) {
            this.app.renderer.textureGC.run();
        }
        
        // Clear unused textures from cache
        this.clearUnusedTextures();
        
        if (level === 'critical') {
            // More aggressive cleanup
            this.forceTextureCleanup();
            
            // Dispatch memory pressure event
            const memoryEvent = new CustomEvent('gpu-memory-pressure', {
                detail: { level, memoryMB: this.contextStats.textureMemoryUsed / (1024 * 1024) }
            });
            if (typeof window !== 'undefined') {
                window.dispatchEvent(memoryEvent);
            }
        }
    }
    
    /**
     * Clear unused textures
     */
    clearUnusedTextures() {
        let cleared = 0;
        
        if (PIXI.utils && PIXI.utils.TextureCache) {
            Object.keys(PIXI.utils.TextureCache).forEach(key => {
                const texture = PIXI.utils.TextureCache[key];
                
                // Check if texture has minimal references
                if (texture && texture._eventsCount === 0) {
                    texture.destroy(true);
                    delete PIXI.utils.TextureCache[key];
                    cleared++;
                }
            });
        }
        
        console.log(`🗑️ Cleared ${cleared} unused textures`);
    }
    
    /**
     * Force aggressive texture cleanup
     */
    forceTextureCleanup() {
        console.log('🧹 Performing aggressive texture cleanup');
        
        // Force garbage collection if available
        if (typeof window !== 'undefined' && window.gc && typeof window.gc === 'function') {
            window.gc();
        }
        
        // Clear our internal caches
        this.textureCache.clear();
        this.texturePool.clear();
    }
    
    /**
     * Check WebGL context health
     */
    checkContextHealth() {
        if (!this.gl) return { healthy: false, reason: 'No WebGL context' };
        
        try {
            // Test basic WebGL operations
            const error = this.gl.getError();
            const NO_ERROR = this.gl.NO_ERROR || 0;
            if (error !== NO_ERROR) {
                return { healthy: false, reason: `WebGL Error: ${error}` };
            }
            
            // Check if context is lost
            if (this.gl.isContextLost && this.gl.isContextLost()) {
                return { healthy: false, reason: 'Context is lost' };
            }
            
            return { healthy: true };
            
        } catch (error) {
            return { healthy: false, reason: error.message };
        }
    }
    
    /**
     * Get context statistics
     */
    getStats() {
        return {
            ...this.contextStats,
            contextLost: this.contextLost,
            restoreAttempts: this.restoreAttempts,
            health: this.checkContextHealth()
        };
    }
    
    /**
     * Force context loss for testing
     */
    testContextLoss() {
        if (this.gl) {
            const loseContextExt = this.gl.getExtension('WEBGL_lose_context');
            if (loseContextExt) {
                loseContextExt.loseContext();
                console.log('🧪 Context loss triggered for testing');
            }
        }
    }
    
    /**
     * Capture and store current WebGL context state
     */
    captureContextState() {
        if (!this.gl) return;
        
        const gl = this.gl;
        
        try {
            // Store viewport state
            const viewport = gl.getParameter(gl.VIEWPORT);
            this.contextState.viewport = {
                x: viewport[0],
                y: viewport[1], 
                width: viewport[2],
                height: viewport[3]
            };
            
            // Store clear color
            this.contextState.clearColor = gl.getParameter(gl.COLOR_CLEAR_VALUE) || [0, 0, 0, 1];
            
            // Store blend mode
            this.contextState.blendMode = {
                enabled: gl.getParameter(gl.BLEND),
                srcRGB: gl.getParameter(gl.BLEND_SRC_RGB),
                dstRGB: gl.getParameter(gl.BLEND_DST_RGB),
                srcAlpha: gl.getParameter(gl.BLEND_SRC_ALPHA),
                dstAlpha: gl.getParameter(gl.BLEND_DST_ALPHA)
            };
            
            console.log('📸 WebGL context state captured');
            
        } catch (error) {
            console.error('Error capturing context state:', error);
        }
    }
    
    /**
     * Validate WebGL extensions and setup fallbacks
     */
    validateExtensions() {
        if (!this.gl) return;
        
        const gl = this.gl;
        
        // Check required extensions
        this.extensions.required.forEach(ext => {
            const supported = gl.getExtension(ext) !== null;
            this.extensions.supported.set(ext, supported);
            
            if (!supported) {
                console.warn(`⚠️ Required extension ${ext} not supported`);
            }
        });
        
        // Check optional extensions with fallbacks
        this.extensions.optional.forEach(ext => {
            const supported = gl.getExtension(ext) !== null;
            this.extensions.supported.set(ext, supported);
            
            if (supported) {
                console.log(`✅ Optional extension ${ext} available`);
            } else {
                console.log(`ℹ️ Optional extension ${ext} not available - fallback will be used`);
            }
        });
        
        // Setup specific fallbacks
        if (!this.extensions.supported.get('EXT_texture_filter_anisotropic')) {
            this.extensions.fallbacks.set('anisotropic_filtering', 'disabled');
        }
        
        if (!this.extensions.supported.get('WEBGL_compressed_texture_s3tc')) {
            this.extensions.fallbacks.set('texture_compression', 'uncompressed');
        }
    }
    
    /**
     * Show context loss notification to user
     */
    showContextLossNotification() {
        if (!this.notificationState.showUserFeedback) return;
        
        const notification = this.createNotificationElement();
        notification.innerHTML = `
            <div class="context-notification-content">
                <div class="notification-icon">⚠️</div>
                <div class="notification-text">
                    <strong>Graphics Issue Detected</strong><br>
                    Attempting to restore WebGL context...
                </div>
                <div class="notification-progress">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.notificationState.currentNotification = notification;
        if (document.body) {
            document.body.appendChild(notification);
        }
    }
    
    /**
     * Update context notification with progress
     */
    updateContextNotification(message, type = 'info') {
        if (!this.notificationState.currentNotification) {
            this.showContextLossNotification();
        }
        
        const notification = this.notificationState.currentNotification;
        const textElement = notification.querySelector('.notification-text');
        const iconElement = notification.querySelector('.notification-icon');
        
        if (textElement) {
            textElement.innerHTML = `<strong>${this.getNotificationTitle(type)}</strong><br>${message}`;
        }
        
        if (iconElement) {
            iconElement.textContent = this.getNotificationIcon(type);
        }
        
        // Update notification styling based on type
        notification.className = `context-notification ${type}`;
    }
    
    /**
     * Hide context notification
     */
    hideContextNotification() {
        if (this.notificationState.currentNotification) {
            this.notificationState.currentNotification.remove();
            this.notificationState.currentNotification = null;
        }
    }
    
    /**
     * Create notification DOM element
     */
    createNotificationElement() {
        if (typeof document === 'undefined') {
            return { mock: true };
        }
        
        const notification = document.createElement('div');
        notification.className = 'context-notification info';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 10000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            border-left: 4px solid #2196F3;
        `;
        return notification;
    }
    
    /**
     * Get notification title based on type
     */
    getNotificationTitle(type) {
        switch (type) {
            case 'error': return 'Graphics Error';
            case 'warning': return 'Graphics Warning';
            case 'success': return 'Graphics Restored';
            default: return 'Graphics Status';
        }
    }
    
    /**
     * Get notification icon based on type
     */
    getNotificationIcon(type) {
        switch (type) {
            case 'error': return '❌';
            case 'warning': return '⚠️';
            case 'success': return '✅';
            default: return 'ℹ️';
        }
    }
    
    /**
     * Pause rendering operations gracefully
     */
    pauseRenderingOperations() {
        if (this.app && this.app.ticker) {
            this.app.ticker.stop();
            console.log('⏸️ Rendering operations paused');
        }
    }
    
    /**
     * Resume rendering operations
     */
    resumeRenderingOperations() {
        if (this.app && this.app.ticker && !this.app.ticker.started) {
            this.app.ticker.start();
            console.log('▶️ Rendering operations resumed');
        }
    }
    
    /**
     * Preserve current game state during context loss
     */
    preserveGameState() {
        // This would typically save current game state to localStorage
        // or send it to a server. For now, we'll just log it.
        console.log('💾 Game state preservation (placeholder)');
        
        // Example of what could be preserved:
        const gameState = {
            timestamp: Date.now(),
            contextLossCount: this.restoreAttempts,
            // Add actual game state here
        };
        
        // Save to localStorage if available (browser environment)
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('webgl_recovery_state', JSON.stringify(gameState));
        }
    }
    
    /**
     * Restore context state after successful restoration
     */
    restoreContextState() {
        if (!this.gl) return;
        
        const gl = this.gl;
        
        try {
            // Restore viewport
            const vp = this.contextState.viewport;
            gl.viewport(vp.x, vp.y, vp.width, vp.height);
            
            // Restore clear color
            const cc = this.contextState.clearColor;
            gl.clearColor(cc[0], cc[1], cc[2], cc[3]);
            
            // Restore blend state
            const blend = this.contextState.blendMode;
            if (blend.enabled) {
                gl.enable(gl.BLEND);
                gl.blendFuncSeparate(blend.srcRGB, blend.dstRGB, blend.srcAlpha, blend.dstAlpha);
            } else {
                gl.disable(gl.BLEND);
            }
            
            console.log('🔄 WebGL context state restored');
            
        } catch (error) {
            console.error('Error restoring context state:', error);
        }
    }
    
    /**
     * Validate rendering capabilities after restoration
     */
    async validateRenderingCapabilities() {
        if (!this.gl) {
            return { success: false, reason: 'No WebGL context available' };
        }
        
        const gl = this.gl;
        
        try {
            // Test basic rendering
            const testCanvas = typeof document !== 'undefined' ? document.createElement('canvas') : null;
            if (!testCanvas) {
                return { success: false, reason: 'Cannot create test canvas (no DOM)' };
            }
            testCanvas.width = testCanvas.height = 64;
            const testGl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
            
            if (!testGl) {
                return { success: false, reason: 'Cannot create test WebGL context' };
            }
            
            // Test shader compilation
            const vertexShader = testGl.createShader(testGl.VERTEX_SHADER);
            const fragmentShader = testGl.createShader(testGl.FRAGMENT_SHADER);
            
            testGl.shaderSource(vertexShader, `
                attribute vec2 position;
                void main() {
                    gl_Position = vec4(position, 0.0, 1.0);
                }
            `);
            
            testGl.shaderSource(fragmentShader, `
                precision mediump float;
                void main() {
                    gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
                }
            `);
            
            testGl.compileShader(vertexShader);
            testGl.compileShader(fragmentShader);
            
            if (!testGl.getShaderParameter(vertexShader, testGl.COMPILE_STATUS)) {
                return { success: false, reason: 'Vertex shader compilation failed' };
            }
            
            if (!testGl.getShaderParameter(fragmentShader, testGl.COMPILE_STATUS)) {
                return { success: false, reason: 'Fragment shader compilation failed' };
            }
            
            // Test program linking
            const program = testGl.createProgram();
            testGl.attachShader(program, vertexShader);
            testGl.attachShader(program, fragmentShader);
            testGl.linkProgram(program);
            
            if (!testGl.getProgramParameter(program, testGl.LINK_STATUS)) {
                return { success: false, reason: 'Shader program linking failed' };
            }
            
            // Test texture creation
            const texture = testGl.createTexture();
            if (!texture) {
                return { success: false, reason: 'Texture creation failed' };
            }
            
            // Test buffer creation
            const buffer = testGl.createBuffer();
            if (!buffer) {
                return { success: false, reason: 'Buffer creation failed' };
            }
            
            console.log('✅ Rendering capabilities validated');
            return { success: true };
            
        } catch (error) {
            return { success: false, reason: `Validation error: ${error.message}` };
        }
    }
    
    /**
     * Start periodic health monitoring
     */
    startHealthMonitoring() {
        setInterval(() => {
            const health = this.checkContextHealth();
            if (!health.healthy && !this.contextLost) {
                console.warn('⚠️ Context health check failed:', health.reason);
                
                // Dispatch warning event
                const warningEvent = new CustomEvent('webgl-health-warning', {
                    detail: health
                });
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(warningEvent);
                }
            }
        }, 10000); // Check every 10 seconds
        
        console.log('🏥 WebGL health monitoring started');
    }
    
    /**
     * Enhanced Canvas fallback with better integration
     */
    async fallbackToCanvasRenderer() {
        console.warn('⚠️ Falling back to Canvas renderer');
        
        this.updateContextNotification('Switching to Canvas renderer for stability...', 'warning');
        
        try {
            // Create new PIXI app with Canvas renderer
            const canvasOptions = {
                width: this.app.renderer.width,
                height: this.app.renderer.height,
                backgroundColor: this.app.renderer.backgroundColor || 0x1a1a1a,
                forceCanvas: true,
                resolution: Math.min(this.app.renderer.resolution || 1, 2), // Limit resolution for performance
                antialias: false // Disable for better Canvas performance
            };
            
            const canvasApp = new PIXI.Application(canvasOptions);
            
            // Wait for Canvas app to initialize
            await new Promise(resolve => {
                if (canvasApp.renderer) {
                    resolve();
                } else {
                    setTimeout(resolve, 100);
                }
            });
            
            // Transfer the stage content to new Canvas renderer
            const oldStage = this.app.stage;
            const newStage = canvasApp.stage;
            
            // Move children from old stage to new stage
            while (oldStage.children.length > 0) {
                const child = oldStage.removeChildAt(0);
                newStage.addChild(child);
            }
            
            // Replace the renderer in the DOM
            const oldCanvas = this.app.view;
            const newCanvas = canvasApp.view;
            
            if (oldCanvas.parentNode) {
                oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);
            }
            
            // Update application references
            this.app = canvasApp;
            this.canvas = newCanvas;
            this.gl = null; // No WebGL in Canvas mode
            this.fallbackMode = true;
            
            // Success notification
            this.updateContextNotification('Successfully switched to Canvas mode', 'success');
            setTimeout(() => this.hideContextNotification(), 5000);
            
            // Dispatch fallback event
            const fallbackEvent = new CustomEvent('webgl-fallback-canvas', {
                detail: {
                    reason: 'context_loss_recovery_failed',
                    canvasOptions
                }
            });
            if (typeof window !== 'undefined') {
                window.dispatchEvent(fallbackEvent);
            }
            
            console.log('✅ Successfully switched to Canvas renderer');
            
        } catch (error) {
            console.error('💀 Canvas fallback failed:', error);
            
            // Show critical error
            this.updateContextNotification('Graphics system failure. Please reload the page.', 'error');
            
            // Last resort - show error message
            this.showWebGLErrorMessage();
        }
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.isDestroyed) {
            console.warn('WebGLContextManager already destroyed');
            return;
        }
        
        console.log('🗑️ Destroying WebGL Context Manager...');
        
        this.isDestroyed = true;
        
        // Remove event listeners with proper handlers
        if (this.canvas) {
            if (this.contextLostHandler) {
                this.canvas.removeEventListener('webglcontextlost', this.contextLostHandler);
            }
            if (this.contextRestoredHandler) {
                this.canvas.removeEventListener('webglcontextrestored', this.contextRestoredHandler);
            }
        }
        
        // Clear memory monitoring interval
        if (this.memoryMonitorInterval) {
            clearInterval(this.memoryMonitorInterval);
            this.memoryMonitorInterval = null;
        }
        
        // Clear health monitoring interval (if exists)
        if (this.healthMonitorInterval) {
            clearInterval(this.healthMonitorInterval);
            this.healthMonitorInterval = null;
        }
        
        // Clear texture caches
        this.clearTextureCaches();
        
        // Clear recovery timeouts
        if (this.recoveryTimeout) {
            clearTimeout(this.recoveryTimeout);
            this.recoveryTimeout = null;
        }
        
        // Clear references
        this.canvas = null;
        this.gl = null;
        this.app = null;
        this.contextLostHandler = null;
        this.contextRestoredHandler = null;
        
        console.log('✅ WebGL Context Manager destroyed successfully');
    }
}