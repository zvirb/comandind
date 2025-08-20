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
        console.log("🔍 Performing Browser Compatibility Check...");
        
        this.checkBrowserInfo();
        this.checkDeviceInfo();
        this.checkWebGLSupport();
        this.checkCanvasLimits();
        this.checkPerformanceHints();
        this.generateRecommendations();
        
        console.log("✅ Browser Compatibility Check Complete");
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
            { name: "Chrome", pattern: /Chrome\/([0-9.]+)/, engine: "Blink" },
            { name: "Firefox", pattern: /Firefox\/([0-9.]+)/, engine: "Gecko" },
            { name: "Safari", pattern: /Safari\/[0-9.]+ .*Version\/([0-9.]+)/, engine: "WebKit" },
            { name: "Edge", pattern: /Edg\/([0-9.]+)/, engine: "Blink" },
            { name: "Opera", pattern: /OPR\/([0-9.]+)/, engine: "Blink" },
            { name: "IE", pattern: /MSIE ([0-9.]+)/, engine: "Trident" }
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
        
        return { name: "Unknown", version: "Unknown", engine: "Unknown" };
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
            touchSupport: "ontouchstart" in window,
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
        
        console.log(`📱 Device: ${this.capabilities.device.mobile ? "Mobile" : "Desktop"} (Performance: ${this.capabilities.device.performanceTier})`);
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
            if (cores >= 8 && pixelRatio >= 3) return "high";
            if (cores >= 4 && pixelRatio >= 2) return "medium";
            return "low";
        } else {
            // Desktop device classification
            if (cores >= 8 && screenSize >= 1920 * 1080) return "high";
            if (cores >= 4 && screenSize >= 1280 * 720) return "medium";
            return "low";
        }
    }
    
    /**
     * Check browser-specific issues
     */
    checkBrowserSpecificIssues(browser) {
        switch (browser.name) {
        case "Safari":
            if (parseFloat(browser.version) < 14) {
                this.warnings.push("Safari versions before 14 may have WebGL context loss issues");
            }
            // Safari has strict memory limits on mobile
            if (this.capabilities.device.mobile) {
                this.warnings.push("Safari on iOS has strict memory limits - reduce texture sizes");
            }
            break;
                
        case "Firefox":
            if (parseFloat(browser.version) < 90) {
                this.warnings.push("Firefox versions before 90 may have WebGL2 compatibility issues");
            }
            break;
                
        case "Chrome":
            // Chrome generally has good WebGL support
            break;
                
        case "IE":
            this.errors.push("Internet Explorer is not supported - please use a modern browser");
            break;
        }
    }

    /**
     * Check WebGL support and capabilities
     */
    checkWebGLSupport() {
        const canvas = document.createElement("canvas");
        let webgl1 = null;
        let webgl2 = null;

        try {
            webgl2 = canvas.getContext("webgl2", {
                alpha: false,
                antialias: true,
                depth: false,
                powerPreference: "high-performance"
            });
        } catch (e) {
            console.warn("WebGL2 context creation failed:", e);
        }

        if (!webgl2) {
            try {
                webgl1 = canvas.getContext("webgl", {
                    alpha: false,
                    antialias: true,
                    depth: false,
                    powerPreference: "high-performance"
                }) || canvas.getContext("experimental-webgl");
            } catch (e) {
                console.warn("WebGL1 context creation failed:", e);
            }
        }

        const gl = webgl2 || webgl1;

        if (!gl) {
            this.errors.push("WebGL is not supported in this browser");
            this.capabilities.webgl = { supported: false };
            return;
        }

        // Gather WebGL capabilities
        this.capabilities.webgl = {
            supported: true,
            version: webgl2 ? 2 : 1,
            vendor: gl.getParameter(gl.VENDOR),
            renderer: gl.getParameter(gl.RENDERER),
            version_string: gl.getParameter(gl.VERSION),
            shading_language_version: gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
        };

        // Get WebGL limits
        this.limits.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        this.limits.maxTextureUnits = gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS);
        this.limits.maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
        this.limits.maxViewportDims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);
        this.limits.maxRenderBufferSize = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);

        // Check for important extensions
        this.capabilities.webgl.extensions = this.checkWebGLExtensions(gl);

        // Estimate GPU memory
        this.limits.estimatedGPUMemory = this.estimateGPUMemory();

        // Check for potential issues
        this.checkWebGLIssues(gl);

        console.log(`🎮 WebGL${this.capabilities.webgl.version} supported`);
        console.log(`   Renderer: ${this.capabilities.webgl.renderer}`);
        console.log(`   Max Texture Size: ${this.limits.maxTextureSize}px`);
        console.log(`   Max Texture Units: ${this.limits.maxTextureUnits}`);
    }

    /**
     * Check for WebGL extensions
     */
    checkWebGLExtensions(gl) {
        const importantExtensions = [
            "ANGLE_instanced_arrays",
            "EXT_texture_filter_anisotropic",
            "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_pvrtc",
            "WEBGL_compressed_texture_etc1",
            "OES_texture_float",
            "OES_texture_half_float",
            "WEBGL_depth_texture",
            "WEBGL_lose_context",
            "OES_vertex_array_object"
        ];

        const supported = {};

        for (const ext of importantExtensions) {
            supported[ext] = gl.getExtension(ext) !== null;
        }

        return supported;
    }

    /**
     * Check for WebGL-specific issues
     */
    checkWebGLIssues(gl) {
        // Check for software rendering
        const renderer = this.capabilities.webgl.renderer.toLowerCase();
        if (renderer.includes("software") || renderer.includes("swiftshader")) {
            this.warnings.push("Software WebGL rendering detected - performance will be limited");
        }

        // Check texture unit count
        if (this.limits.maxTextureUnits < 8) {
            this.warnings.push(`Low texture unit count (${this.limits.maxTextureUnits}) - may limit batching efficiency`);
        }

        // Check texture size limits
        if (this.limits.maxTextureSize < 2048) {
            this.warnings.push(`Small max texture size (${this.limits.maxTextureSize}px) - texture atlases will be limited`);
        }

        // Check for mobile GPU limitations
        if (this.capabilities.device.mobile) {
            if (renderer.includes("adreno") && renderer.includes("3")) {
                this.warnings.push("Older Adreno GPU detected - may have WebGL stability issues");
            }
            if (renderer.includes("mali-400")) {
                this.warnings.push("Mali-400 GPU detected - has known WebGL limitations");
            }
        }
    }

    /**
     * Estimate GPU memory based on renderer string and device characteristics
     */
    estimateGPUMemory() {
        const renderer = this.capabilities.webgl?.renderer?.toLowerCase() || "";

        // Mobile devices
        if (this.capabilities.device.mobile) {
            if (renderer.includes("adreno 6") || renderer.includes("mali-g7")) {
                return 1024; // 1GB - high-end mobile
            } else if (renderer.includes("adreno 5") || renderer.includes("mali-g5")) {
                return 512; // 512MB - mid-range mobile
            } else {
                return 256; // 256MB - low-end mobile
            }
        }

        // Desktop/laptop
        if (renderer.includes("nvidia") || renderer.includes("geforce")) {
            if (renderer.includes("rtx") || renderer.includes("gtx 16") || renderer.includes("gtx 20")) {
                return 8192; // 8GB - high-end NVIDIA
            } else if (renderer.includes("gtx")) {
                return 4096; // 4GB - mid-range NVIDIA
            } else {
                return 2048; // 2GB - entry-level NVIDIA
            }
        }

        if (renderer.includes("amd") || renderer.includes("radeon")) {
            if (renderer.includes("rx 6") || renderer.includes("rx 5700")) {
                return 8192; // 8GB - high-end AMD
            } else if (renderer.includes("rx 5") || renderer.includes("rx 4")) {
                return 4096; // 4GB - mid-range AMD
            } else {
                return 2048; // 2GB - entry-level AMD
            }
        }

        if (renderer.includes("intel")) {
            if (renderer.includes("iris xe") || renderer.includes("iris pro")) {
                return 1024; // 1GB - high-end Intel integrated
            } else {
                return 512; // 512MB - standard Intel integrated
            }
        }

        // Fallback based on texture size limits
        if (this.limits.maxTextureSize >= 8192) {
            return 2048;
        } else if (this.limits.maxTextureSize >= 4096) {
            return 1024;
        } else {
            return 512;
        }
    }

    /**
     * Check canvas size limits
     */
    checkCanvasLimits() {
        const testCanvas = document.createElement("canvas");
        const ctx = testCanvas.getContext("2d");

        // Test maximum canvas size
        this.limits.maxCanvasSize = this.findMaxCanvasSize(testCanvas, ctx);

        this.capabilities.canvas = {
            supported: !!ctx,
            maxWidth: this.limits.maxCanvasSize.width,
            maxHeight: this.limits.maxCanvasSize.height,
            maxArea: this.limits.maxCanvasSize.area
        };

        console.log(`🖼️ Canvas limits: ${this.limits.maxCanvasSize.width}x${this.limits.maxCanvasSize.height}`);

        // Check if requested game size exceeds limits
        const gameWidth = 1280;
        const gameHeight = 720;

        if (gameWidth > this.limits.maxCanvasSize.width || gameHeight > this.limits.maxCanvasSize.height) {
            this.warnings.push(`Game size (${gameWidth}x${gameHeight}) exceeds canvas limits`);
        }
    }

    /**
     * Binary search for maximum canvas size
     */
    findMaxCanvasSize(canvas, ctx) {
        // Test common problematic sizes first
        const testSizes = [
            { width: 32767, height: 32767 }, // Theoretical max for 16-bit
            { width: 16384, height: 16384 }, // Common GPU limit
            { width: 8192, height: 8192 },   // Older GPU limit
            { width: 4096, height: 4096 },   // Mobile GPU limit
            { width: 2048, height: 2048 }    // Conservative limit
        ];

        for (const size of testSizes) {
            if (this.testCanvasSize(canvas, ctx, size.width, size.height)) {
                return {
                    width: size.width,
                    height: size.height,
                    area: size.width * size.height
                };
            }
        }

        // Fallback to very conservative size
        return { width: 1024, height: 1024, area: 1048576 };
    }

    /**
     * Test if canvas can handle specific dimensions
     */
    testCanvasSize(canvas, ctx, width, height) {
        try {
            canvas.width = width;
            canvas.height = height;

            // Try to draw something to verify it works
            ctx.fillStyle = "#ff0000";
            ctx.fillRect(0, 0, 1, 1);

            // Check if we can read pixels back
            const imageData = ctx.getImageData(0, 0, 1, 1);
            return imageData.data[0] === 255; // Red channel should be 255

        } catch (error) {
            return false;
        }
    }

    /**
     * Check performance hints and capabilities
     */
    checkPerformanceHints() {
        // Check memory available
        const memory = navigator.deviceMemory || this.estimateMemory();

        // Check connection quality
        const connection = navigator.connection || {};

        this.capabilities.performance = {
            deviceMemory: memory,
            hardwareConcurrency: navigator.hardwareConcurrency || 1,
            connectionType: connection.effectiveType || "unknown",
            downlink: connection.downlink || 0,
            rtt: connection.rtt || 0,
            saveData: connection.saveData || false
        };

        console.log(`⚡ Performance: ${memory}GB RAM, ${this.capabilities.performance.hardwareConcurrency} cores`);
    }

    /**
     * Estimate device memory if not available
     */
    estimateMemory() {
        if (this.capabilities.device.mobile) {
            // Mobile device memory estimation
            if (this.capabilities.device.performanceTier === "high") return 8;
            if (this.capabilities.device.performanceTier === "medium") return 4;
            return 2;
        } else {
            // Desktop memory estimation
            if (this.capabilities.device.performanceTier === "high") return 16;
            if (this.capabilities.device.performanceTier === "medium") return 8;
            return 4;
        }
    }

    /**
     * Generate performance recommendations
     */
    generateRecommendations() {
        const perf = this.capabilities.device.performanceTier;
        const mobile = this.capabilities.device.mobile;
        const webglVersion = this.capabilities.webgl.version;
        const gpuMemory = this.limits.estimatedGPUMemory;

        // WebGL version recommendation
        this.recommendations.useWebGL2 = webglVersion === 2 && !mobile;

        // Antialiasing recommendation
        this.recommendations.enableAntialiasing = perf === "high" && gpuMemory > 1024;

        // Sprite count recommendations
        if (perf === "high" && !mobile) {
            this.recommendations.maxSpriteCount = 5000;
        } else if (perf === "medium") {
            this.recommendations.maxSpriteCount = 2000;
        } else {
            this.recommendations.maxSpriteCount = 1000;
        }

        // Texture atlas size recommendations
        if (this.limits.maxTextureSize >= 4096 && gpuMemory > 1024) {
            this.recommendations.textureAtlasSize = 4096;
        } else if (this.limits.maxTextureSize >= 2048) {
            this.recommendations.textureAtlasSize = 2048;
        } else {
            this.recommendations.textureAtlasSize = 1024;
        }

        // Batch size recommendations
        if (this.limits.maxTextureUnits >= 16 && perf === "high") {
            this.recommendations.batchSize = 2000;
        } else if (this.limits.maxTextureUnits >= 8) {
            this.recommendations.batchSize = 1000;
        } else {
            this.recommendations.batchSize = 500;
        }

        // Additional mobile optimizations
        if (mobile) {
            this.recommendations.maxSpriteCount = Math.floor(this.recommendations.maxSpriteCount * 0.6);
            this.recommendations.batchSize = Math.floor(this.recommendations.batchSize * 0.8);
            this.recommendations.enableAntialiasing = false;
        }

        console.log("💡 Generated performance recommendations");
    }

    /**
     * Log comprehensive results
     */
    logResults() {
        console.log("\
📊 Browser Compatibility Report:");
        console.log("================================");

        // Browser info
        console.log(`🌐 Browser: ${this.capabilities.browser.name} ${this.capabilities.browser.version}`);
        console.log(`📱 Device: ${this.capabilities.device.mobile ? "Mobile" : "Desktop"} (${this.capabilities.device.performanceTier} performance)`);

        // WebGL support
        if (this.capabilities.webgl.supported) {
            console.log(`🎮 WebGL${this.capabilities.webgl.version}: ✅ Supported`);
            console.log(`   GPU: ${this.capabilities.webgl.renderer}`);
            console.log(`   Memory: ~${this.limits.estimatedGPUMemory}MB`);
        } else {
            console.log("🎮 WebGL: ❌ Not supported");
        }

        // Recommendations
        console.log("\
💡 Recommendations:");
        console.log(`   Use WebGL2: ${this.recommendations.useWebGL2 ? "✅" : "❌"}`);
        console.log(`   Enable Antialiasing: ${this.recommendations.enableAntialiasing ? "✅" : "❌"}`);
        console.log(`   Max Sprites: ${this.recommendations.maxSpriteCount}`);
        console.log(`   Texture Atlas Size: ${this.recommendations.textureAtlasSize}px`);
        console.log(`   Batch Size: ${this.recommendations.batchSize}`);

        // Warnings
        if (this.warnings.length > 0) {
            console.log("\
⚠️ Warnings:");
            this.warnings.forEach(warning => console.log(`   - ${warning}`));
        }

        // Errors
        if (this.errors.length > 0) {
            console.log("\
❌ Errors:");
            this.errors.forEach(error => console.log(`   - ${error}`));
        }

        console.log("================================\
");
    }

    /**
     * Get compatibility report as object
     */
    getReport() {
        return {
            capabilities: this.capabilities,
            limits: this.limits,
            recommendations: this.recommendations,
            warnings: this.warnings,
            errors: this.errors,
            compatible: this.errors.length === 0
        };
    }

    /**
     * Check if browser is compatible
     */
    isCompatible() {
        return this.errors.length === 0;
    }

    /**
     * Get WebGL context with optimal settings
     */
    createOptimalWebGLContext(canvas) {
        const contextOptions = {
            alpha: false,
            antialias: this.recommendations.enableAntialiasing,
            depth: false,
            powerPreference: "high-performance",
            premultipliedAlpha: true,
            preserveDrawingBuffer: false,
            stencil: true
        };

        // Try WebGL2 if recommended
        if (this.recommendations.useWebGL2) {
            const gl2 = canvas.getContext("webgl2", contextOptions);
            if (gl2) return gl2;
        }

        // Fallback to WebGL1
        return canvas.getContext("webgl", contextOptions) ||
               canvas.getContext("experimental-webgl", contextOptions);
    }
}

// Utility function for easy checking
export function checkBrowserCompatibility() {
    return new BrowserCompatibilityChecker();
}
