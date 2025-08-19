/**
 * Browser Compatibility Checker for Command & Independent Thought
 * 
 * Comprehensive browser and device capability detection system
 * Handles WebGL support, canvas size limits, memory constraints, and performance optimization
 */

export class BrowserCompatibilityChecker {
    constructor() {
        this.capabilities = {
            webgl: null,
            canvas: null,
            browser: null,
            device: null,
            performance: null
        };
        
        this.limits = {
            maxCanvasSize: null,
            maxTextureSize: null,
            maxTextureUnits: null,
            maxVertexAttribs: null,
            estimatedGPUMemory: null
        };
        
        this.recommendations = {
            useWebGL2: false,
            enableAntialiasing: false,
            maxSpriteCount: 1000,
            textureAtlasSize: 2048,
            batchSize: 1000
        };
        
        this.warnings = [];
        this.errors = [];
        
        this.performCheck();
    }
    
    /**
     * Perform comprehensive compatibility check
     */
    performCheck() {
        console.log('🔍 Performing Browser Compatibility Check...');
        
        this.checkBrowserInfo();
        this.checkDeviceInfo();
        this.checkWebGLSupport();
        this.checkCanvasLimits();
        this.checkPerformanceHints();
        this.generateRecommendations();
        
        console.log('✅ Browser Compatibility Check Complete');
        this.logResults();
    }
    
    /**
     * Check browser information and known issues
     */
    checkBrowserInfo() {
        const ua = navigator.userAgent;
        const browser = this.detectBrowser(ua);
        
        this.capabilities.browser = {
            name: browser.name,
            version: browser.version,
            engine: browser.engine,
            mobile: this.isMobile(),
            platform: navigator.platform,
            userAgent: ua
        };
        
        // Check for known browser issues
        this.checkBrowserSpecificIssues(browser);
        
        console.log(`🌐 Browser: ${browser.name} ${browser.version} (${browser.engine})`);
    }
    
    /**
     * Detect browser from user agent
     */
    detectBrowser(ua) {
        const browsers = [
            { name: 'Chrome', pattern: /Chrome\/([0-9.]+)/, engine: 'Blink' },
            { name: 'Firefox', pattern: /Firefox\/([0-9.]+)/, engine: 'Gecko' },
            { name: 'Safari', pattern: /Safari\/[0-9.]+ .*Version\/([0-9.]+)/, engine: 'WebKit' },
            { name: 'Edge', pattern: /Edg\/([0-9.]+)/, engine: 'Blink' },
            { name: 'Opera', pattern: /OPR\/([0-9.]+)/, engine: 'Blink' },
            { name: 'IE', pattern: /MSIE ([0-9.]+)/, engine: 'Trident' }
        ];
        
        for (const browser of browsers) {
            const match = ua.match(browser.pattern);
            if (match) {
                return {
                    name: browser.name,
                    version: match[1],
                    engine: browser.engine
                };
            }
        }
        
        return { name: 'Unknown', version: 'Unknown', engine: 'Unknown' };
    }
    
    /**
     * Check for mobile device
     */
    isMobile() {
        return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    /**
     * Check device information
     */
    checkDeviceInfo() {
        this.capabilities.device = {
            mobile: this.isMobile(),
            touchSupport: 'ontouchstart' in window,
            devicePixelRatio: window.devicePixelRatio || 1,
            screenWidth: screen.width,
            screenHeight: screen.height,
            availableWidth: screen.availWidth,
            availableHeight: screen.availHeight,
            colorDepth: screen.colorDepth,
            hardwareConcurrency: navigator.hardwareConcurrency || 1
        };
        
        // Estimate device performance tier
        this.capabilities.device.performanceTier = this.estimatePerformanceTier();
        
        console.log(`📱 Device: ${this.capabilities.device.mobile ? 'Mobile' : 'Desktop'} (Performance: ${this.capabilities.device.performanceTier})`);
    }
    
    /**
     * Estimate device performance tier
     */
    estimatePerformanceTier() {
        const cores = this.capabilities.device.hardwareConcurrency;
        const pixelRatio = this.capabilities.device.devicePixelRatio;
        const screenSize = this.capabilities.device.screenWidth * this.capabilities.device.screenHeight;
        
        if (this.capabilities.device.mobile) {
            // Mobile device classification
            if (cores >= 8 && pixelRatio >= 3) return 'high';
            if (cores >= 4 && pixelRatio >= 2) return 'medium';
            return 'low';
        } else {
            // Desktop device classification
            if (cores >= 8 && screenSize >= 1920 * 1080) return 'high';
            if (cores >= 4 && screenSize >= 1280 * 720) return 'medium';
            return 'low';
        }
    }
    
    /**
     * Check browser-specific issues
     */
    checkBrowserSpecificIssues(browser) {
        switch (browser.name) {
            case 'Safari':
                if (parseFloat(browser.version) < 14) {
                    this.warnings.push('Safari versions before 14 may have WebGL context loss issues');
                }
                // Safari has strict memory limits on mobile
                if (this.capabilities.device.mobile) {
                    this.warnings.push('Safari on iOS has strict memory limits - reduce texture sizes');
                }
                break;
                
            case 'Firefox':
                if (parseFloat(browser.version) < 90) {
                    this.warnings.push('Firefox versions before 90 may have WebGL2 compatibility issues');
                }
                break;
                
            case 'Chrome':
                // Chrome generally has good WebGL support
                break;
                
            case 'IE':
                this.errors.push('Internet Explorer is not supported - please use a modern browser');
                break;
        }\n    }\n    \n    /**\n     * Check WebGL support and capabilities\n     */\n    checkWebGLSupport() {\n        const canvas = document.createElement('canvas');\n        let webgl1 = null;\n        let webgl2 = null;\n        \n        try {\n            webgl2 = canvas.getContext('webgl2', {\n                alpha: false,\n                antialias: true,\n                depth: false,\n                powerPreference: 'high-performance'\n            });\n        } catch (e) {\n            console.warn('WebGL2 context creation failed:', e);\n        }\n        \n        if (!webgl2) {\n            try {\n                webgl1 = canvas.getContext('webgl', {\n                    alpha: false,\n                    antialias: true,\n                    depth: false,\n                    powerPreference: 'high-performance'\n                }) || canvas.getContext('experimental-webgl');\n            } catch (e) {\n                console.warn('WebGL1 context creation failed:', e);\n            }\n        }\n        \n        const gl = webgl2 || webgl1;\n        \n        if (!gl) {\n            this.errors.push('WebGL is not supported in this browser');\n            this.capabilities.webgl = { supported: false };\n            return;\n        }\n        \n        // Gather WebGL capabilities\n        this.capabilities.webgl = {\n            supported: true,\n            version: webgl2 ? 2 : 1,\n            vendor: gl.getParameter(gl.VENDOR),\n            renderer: gl.getParameter(gl.RENDERER),\n            version_string: gl.getParameter(gl.VERSION),\n            shading_language_version: gl.getParameter(gl.SHADING_LANGUAGE_VERSION)\n        };\n        \n        // Get WebGL limits\n        this.limits.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);\n        this.limits.maxTextureUnits = gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS);\n        this.limits.maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);\n        this.limits.maxViewportDims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);\n        this.limits.maxRenderBufferSize = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);\n        \n        // Check for important extensions\n        this.capabilities.webgl.extensions = this.checkWebGLExtensions(gl);\n        \n        // Estimate GPU memory\n        this.limits.estimatedGPUMemory = this.estimateGPUMemory();\n        \n        // Check for potential issues\n        this.checkWebGLIssues(gl);\n        \n        console.log(`🎮 WebGL${this.capabilities.webgl.version} supported`);\n        console.log(`   Renderer: ${this.capabilities.webgl.renderer}`);\n        console.log(`   Max Texture Size: ${this.limits.maxTextureSize}px`);\n        console.log(`   Max Texture Units: ${this.limits.maxTextureUnits}`);\n    }\n    \n    /**\n     * Check for WebGL extensions\n     */\n    checkWebGLExtensions(gl) {\n        const importantExtensions = [\n            'ANGLE_instanced_arrays',\n            'EXT_texture_filter_anisotropic',\n            'WEBGL_compressed_texture_s3tc',\n            'WEBGL_compressed_texture_pvrtc',\n            'WEBGL_compressed_texture_etc1',\n            'OES_texture_float',\n            'OES_texture_half_float',\n            'WEBGL_depth_texture',\n            'WEBGL_lose_context',\n            'OES_vertex_array_object'\n        ];\n        \n        const supported = {};\n        \n        for (const ext of importantExtensions) {\n            supported[ext] = gl.getExtension(ext) !== null;\n        }\n        \n        return supported;\n    }\n    \n    /**\n     * Check for WebGL-specific issues\n     */\n    checkWebGLIssues(gl) {\n        // Check for software rendering\n        const renderer = this.capabilities.webgl.renderer.toLowerCase();\n        if (renderer.includes('software') || renderer.includes('swiftshader')) {\n            this.warnings.push('Software WebGL rendering detected - performance will be limited');\n        }\n        \n        // Check texture unit count\n        if (this.limits.maxTextureUnits < 8) {\n            this.warnings.push(`Low texture unit count (${this.limits.maxTextureUnits}) - may limit batching efficiency`);\n        }\n        \n        // Check texture size limits\n        if (this.limits.maxTextureSize < 2048) {\n            this.warnings.push(`Small max texture size (${this.limits.maxTextureSize}px) - texture atlases will be limited`);\n        }\n        \n        // Check for mobile GPU limitations\n        if (this.capabilities.device.mobile) {\n            if (renderer.includes('adreno') && renderer.includes('3')) {\n                this.warnings.push('Older Adreno GPU detected - may have WebGL stability issues');\n            }\n            if (renderer.includes('mali-400')) {\n                this.warnings.push('Mali-400 GPU detected - has known WebGL limitations');\n            }\n        }\n    }\n    \n    /**\n     * Estimate GPU memory based on renderer string and device characteristics\n     */\n    estimateGPUMemory() {\n        const renderer = this.capabilities.webgl?.renderer?.toLowerCase() || '';\n        \n        // Mobile devices\n        if (this.capabilities.device.mobile) {\n            if (renderer.includes('adreno 6') || renderer.includes('mali-g7')) {\n                return 1024; // 1GB - high-end mobile\n            } else if (renderer.includes('adreno 5') || renderer.includes('mali-g5')) {\n                return 512; // 512MB - mid-range mobile\n            } else {\n                return 256; // 256MB - low-end mobile\n            }\n        }\n        \n        // Desktop/laptop\n        if (renderer.includes('nvidia') || renderer.includes('geforce')) {\n            if (renderer.includes('rtx') || renderer.includes('gtx 16') || renderer.includes('gtx 20')) {\n                return 8192; // 8GB - high-end NVIDIA\n            } else if (renderer.includes('gtx')) {\n                return 4096; // 4GB - mid-range NVIDIA\n            } else {\n                return 2048; // 2GB - entry-level NVIDIA\n            }\n        }\n        \n        if (renderer.includes('amd') || renderer.includes('radeon')) {\n            if (renderer.includes('rx 6') || renderer.includes('rx 5700')) {\n                return 8192; // 8GB - high-end AMD\n            } else if (renderer.includes('rx 5') || renderer.includes('rx 4')) {\n                return 4096; // 4GB - mid-range AMD\n            } else {\n                return 2048; // 2GB - entry-level AMD\n            }\n        }\n        \n        if (renderer.includes('intel')) {\n            if (renderer.includes('iris xe') || renderer.includes('iris pro')) {\n                return 1024; // 1GB - high-end Intel integrated\n            } else {\n                return 512; // 512MB - standard Intel integrated\n            }\n        }\n        \n        // Fallback based on texture size limits\n        if (this.limits.maxTextureSize >= 8192) {\n            return 2048;\n        } else if (this.limits.maxTextureSize >= 4096) {\n            return 1024;\n        } else {\n            return 512;\n        }\n    }\n    \n    /**\n     * Check canvas size limits\n     */\n    checkCanvasLimits() {\n        const testCanvas = document.createElement('canvas');\n        const ctx = testCanvas.getContext('2d');\n        \n        // Test maximum canvas size\n        this.limits.maxCanvasSize = this.findMaxCanvasSize(testCanvas, ctx);\n        \n        this.capabilities.canvas = {\n            supported: !!ctx,\n            maxWidth: this.limits.maxCanvasSize.width,\n            maxHeight: this.limits.maxCanvasSize.height,\n            maxArea: this.limits.maxCanvasSize.area\n        };\n        \n        console.log(`🖼️ Canvas limits: ${this.limits.maxCanvasSize.width}x${this.limits.maxCanvasSize.height}`);\n        \n        // Check if requested game size exceeds limits\n        const gameWidth = 1280;\n        const gameHeight = 720;\n        \n        if (gameWidth > this.limits.maxCanvasSize.width || gameHeight > this.limits.maxCanvasSize.height) {\n            this.warnings.push(`Game size (${gameWidth}x${gameHeight}) exceeds canvas limits`);\n        }\n    }\n    \n    /**\n     * Binary search for maximum canvas size\n     */\n    findMaxCanvasSize(canvas, ctx) {\n        // Test common problematic sizes first\n        const testSizes = [\n            { width: 32767, height: 32767 }, // Theoretical max for 16-bit\n            { width: 16384, height: 16384 }, // Common GPU limit\n            { width: 8192, height: 8192 },   // Older GPU limit\n            { width: 4096, height: 4096 },   // Mobile GPU limit\n            { width: 2048, height: 2048 }    // Conservative limit\n        ];\n        \n        for (const size of testSizes) {\n            if (this.testCanvasSize(canvas, ctx, size.width, size.height)) {\n                return {\n                    width: size.width,\n                    height: size.height,\n                    area: size.width * size.height\n                };\n            }\n        }\n        \n        // Fallback to very conservative size\n        return { width: 1024, height: 1024, area: 1048576 };\n    }\n    \n    /**\n     * Test if canvas can handle specific dimensions\n     */\n    testCanvasSize(canvas, ctx, width, height) {\n        try {\n            canvas.width = width;\n            canvas.height = height;\n            \n            // Try to draw something to verify it works\n            ctx.fillStyle = '#ff0000';\n            ctx.fillRect(0, 0, 1, 1);\n            \n            // Check if we can read pixels back\n            const imageData = ctx.getImageData(0, 0, 1, 1);\n            return imageData.data[0] === 255; // Red channel should be 255\n            \n        } catch (error) {\n            return false;\n        }\n    }\n    \n    /**\n     * Check performance hints and capabilities\n     */\n    checkPerformanceHints() {\n        // Check memory available\n        const memory = navigator.deviceMemory || this.estimateMemory();\n        \n        // Check connection quality\n        const connection = navigator.connection || {};\n        \n        this.capabilities.performance = {\n            deviceMemory: memory,\n            hardwareConcurrency: navigator.hardwareConcurrency || 1,\n            connectionType: connection.effectiveType || 'unknown',\n            downlink: connection.downlink || 0,\n            rtt: connection.rtt || 0,\n            saveData: connection.saveData || false\n        };\n        \n        console.log(`⚡ Performance: ${memory}GB RAM, ${this.capabilities.performance.hardwareConcurrency} cores`);\n    }\n    \n    /**\n     * Estimate device memory if not available\n     */\n    estimateMemory() {\n        if (this.capabilities.device.mobile) {\n            // Mobile device memory estimation\n            if (this.capabilities.device.performanceTier === 'high') return 8;\n            if (this.capabilities.device.performanceTier === 'medium') return 4;\n            return 2;\n        } else {\n            // Desktop memory estimation\n            if (this.capabilities.device.performanceTier === 'high') return 16;\n            if (this.capabilities.device.performanceTier === 'medium') return 8;\n            return 4;\n        }\n    }\n    \n    /**\n     * Generate performance recommendations\n     */\n    generateRecommendations() {\n        const perf = this.capabilities.device.performanceTier;\n        const mobile = this.capabilities.device.mobile;\n        const webglVersion = this.capabilities.webgl.version;\n        const gpuMemory = this.limits.estimatedGPUMemory;\n        \n        // WebGL version recommendation\n        this.recommendations.useWebGL2 = webglVersion === 2 && !mobile;\n        \n        // Antialiasing recommendation\n        this.recommendations.enableAntialiasing = perf === 'high' && gpuMemory > 1024;\n        \n        // Sprite count recommendations\n        if (perf === 'high' && !mobile) {\n            this.recommendations.maxSpriteCount = 5000;\n        } else if (perf === 'medium') {\n            this.recommendations.maxSpriteCount = 2000;\n        } else {\n            this.recommendations.maxSpriteCount = 1000;\n        }\n        \n        // Texture atlas size recommendations\n        if (this.limits.maxTextureSize >= 4096 && gpuMemory > 1024) {\n            this.recommendations.textureAtlasSize = 4096;\n        } else if (this.limits.maxTextureSize >= 2048) {\n            this.recommendations.textureAtlasSize = 2048;\n        } else {\n            this.recommendations.textureAtlasSize = 1024;\n        }\n        \n        // Batch size recommendations\n        if (this.limits.maxTextureUnits >= 16 && perf === 'high') {\n            this.recommendations.batchSize = 2000;\n        } else if (this.limits.maxTextureUnits >= 8) {\n            this.recommendations.batchSize = 1000;\n        } else {\n            this.recommendations.batchSize = 500;\n        }\n        \n        // Additional mobile optimizations\n        if (mobile) {\n            this.recommendations.maxSpriteCount = Math.floor(this.recommendations.maxSpriteCount * 0.6);\n            this.recommendations.batchSize = Math.floor(this.recommendations.batchSize * 0.8);\n            this.recommendations.enableAntialiasing = false;\n        }\n        \n        console.log('💡 Generated performance recommendations');\n    }\n    \n    /**\n     * Log comprehensive results\n     */\n    logResults() {\n        console.log('\\n📊 Browser Compatibility Report:');\n        console.log('================================');\n        \n        // Browser info\n        console.log(`🌐 Browser: ${this.capabilities.browser.name} ${this.capabilities.browser.version}`);\n        console.log(`📱 Device: ${this.capabilities.device.mobile ? 'Mobile' : 'Desktop'} (${this.capabilities.device.performanceTier} performance)`);\n        \n        // WebGL support\n        if (this.capabilities.webgl.supported) {\n            console.log(`🎮 WebGL${this.capabilities.webgl.version}: ✅ Supported`);\n            console.log(`   GPU: ${this.capabilities.webgl.renderer}`);\n            console.log(`   Memory: ~${this.limits.estimatedGPUMemory}MB`);\n        } else {\n            console.log('🎮 WebGL: ❌ Not supported');\n        }\n        \n        // Recommendations\n        console.log('\\n💡 Recommendations:');\n        console.log(`   Use WebGL2: ${this.recommendations.useWebGL2 ? '✅' : '❌'}`);\n        console.log(`   Enable Antialiasing: ${this.recommendations.enableAntialiasing ? '✅' : '❌'}`);\n        console.log(`   Max Sprites: ${this.recommendations.maxSpriteCount}`);\n        console.log(`   Texture Atlas Size: ${this.recommendations.textureAtlasSize}px`);\n        console.log(`   Batch Size: ${this.recommendations.batchSize}`);\n        \n        // Warnings\n        if (this.warnings.length > 0) {\n            console.log('\\n⚠️ Warnings:');\n            this.warnings.forEach(warning => console.log(`   - ${warning}`));\n        }\n        \n        // Errors\n        if (this.errors.length > 0) {\n            console.log('\\n❌ Errors:');\n            this.errors.forEach(error => console.log(`   - ${error}`));\n        }\n        \n        console.log('================================\\n');\n    }\n    \n    /**\n     * Get compatibility report as object\n     */\n    getReport() {\n        return {\n            capabilities: this.capabilities,\n            limits: this.limits,\n            recommendations: this.recommendations,\n            warnings: this.warnings,\n            errors: this.errors,\n            compatible: this.errors.length === 0\n        };\n    }\n    \n    /**\n     * Check if browser is compatible\n     */\n    isCompatible() {\n        return this.errors.length === 0;\n    }\n    \n    /**\n     * Get WebGL context with optimal settings\n     */\n    createOptimalWebGLContext(canvas) {\n        const contextOptions = {\n            alpha: false,\n            antialias: this.recommendations.enableAntialiasing,\n            depth: false,\n            powerPreference: 'high-performance',\n            premultipliedAlpha: true,\n            preserveDrawingBuffer: false,\n            stencil: true\n        };\n        \n        // Try WebGL2 if recommended\n        if (this.recommendations.useWebGL2) {\n            const gl2 = canvas.getContext('webgl2', contextOptions);\n            if (gl2) return gl2;\n        }\n        \n        // Fallback to WebGL1\n        return canvas.getContext('webgl', contextOptions) || \n               canvas.getContext('experimental-webgl', contextOptions);\n    }\n}\n\n// Utility function for easy checking\nexport function checkBrowserCompatibility() {\n    return new BrowserCompatibilityChecker();\n}