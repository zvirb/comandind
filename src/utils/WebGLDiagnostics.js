/**
 * WebGL Diagnostics Utility for Command & Independent Thought
 * 
 * Comprehensive diagnostic tool for WebGL issues, context problems,
 * texture management, and performance analysis
 */

import { BrowserCompatibilityChecker } from "../rendering/BrowserCompatibilityChecker.js";

export class WebGLDiagnostics {
    constructor() {
        this.results = {
            timestamp: Date.now(),
            browser: null,
            webgl: null,
            context: null,
            textures: null,
            performance: null,
            recommendations: []
        };
        
        this.tests = [];
        this.warnings = [];
        this.errors = [];
    }
    
    /**
     * Run complete diagnostic suite
     */
    async runDiagnostics() {
        console.log("🔬 Starting WebGL Diagnostic Suite...");
        console.log("=====================================");
        
        try {
            // Phase 1: Browser Compatibility
            await this.testBrowserCompatibility();
            
            // Phase 2: WebGL Context Tests
            await this.testWebGLContext();
            
            // Phase 3: Texture System Tests
            await this.testTextureSystem();
            
            // Phase 4: Performance Tests
            await this.testPerformance();
            
            // Phase 5: Stress Tests
            await this.runStressTests();
            
            // Generate final report
            this.generateReport();
            
        } catch (error) {
            this.errors.push(`Diagnostic suite failed: ${error.message}`);
            console.error("❌ Diagnostic suite failed:", error);
        }
        
        console.log("✅ WebGL Diagnostics Complete");
        return this.getReport();
    }
    
    /**
     * Test browser compatibility
     */
    async testBrowserCompatibility() {
        console.log("🧪 Testing Browser Compatibility...");

        const compatChecker = new BrowserCompatibilityChecker();
        const report = compatChecker.getReport();

        this.results.browser = report;

        if (!report.compatible) {
            this.errors.push("Browser is not compatible with WebGL");
            return;
        }

        this.addTest("Browser Compatibility", "PASS", "Browser supports required WebGL features");

        // Add specific warnings from compatibility check
        report.warnings.forEach(warning => this.warnings.push(warning));
        report.errors.forEach(error => this.errors.push(error));
    }

    /**
     * Test WebGL context creation and stability
     */
    async testWebGLContext() {
        console.log("🧪 Testing WebGL Context...");

        const canvas = document.createElement("canvas");
        canvas.width = 512;
        canvas.height = 512;

        // Test WebGL2 context
        let gl2 = null;
        try {
            gl2 = canvas.getContext("webgl2");
            if (gl2) {
                this.addTest("WebGL2 Context", "PASS", "WebGL2 context created successfully");
                await this.testContextStability(gl2, "WebGL2");
            } else {
                this.addTest("WebGL2 Context", "FAIL", "WebGL2 context creation failed");
            }
        } catch (error) {
            this.addTest("WebGL2 Context", "ERROR", `WebGL2 error: ${error.message}`);
        }

        // Test WebGL1 context
        let gl1 = null;
        try {
            gl1 = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
            if (gl1) {
                this.addTest("WebGL1 Context", "PASS", "WebGL1 context created successfully");
                await this.testContextStability(gl1, "WebGL1");

                // Use WebGL1 for remaining tests if WebGL2 failed
                if (!gl2) {
                    await this.testWebGLCapabilities(gl1);
                }
            } else {
                this.addTest("WebGL1 Context", "FAIL", "WebGL1 context creation failed");
                this.errors.push("No WebGL context available");
            }
        } catch (error) {
            this.addTest("WebGL1 Context", "ERROR", `WebGL1 error: ${error.message}`);
        }

        // Test with the best available context
        const gl = gl2 || gl1;
        if (gl) {
            await this.testWebGLCapabilities(gl);
            await this.testShaderCompilation(gl);
            await this.testBufferOperations(gl);
            await this.testFramebufferOperations(gl);
        }

        this.results.context = {
            webgl2Available: !!gl2,
            webgl1Available: !!gl1,
            preferredContext: gl2 ? "webgl2" : gl1 ? "webgl" : "none"
        };
    }

    /**
     * Test context stability and loss/restore
     */
    async testContextStability(gl, contextType) {
        try {
            // Test context loss extension
            const loseExt = gl.getExtension("WEBGL_lose_context");
            if (loseExt) {
                this.addTest(`${contextType} Context Loss Extension`, "PASS", "Context loss extension available");

                // Test context loss/restore (be careful with this)
                // We'll just verify the extension exists rather than actually losing context
                if (typeof loseExt.loseContext === "function" && typeof loseExt.restoreContext === "function") {
                    this.addTest(`${contextType} Context Loss/Restore`, "PASS", "Context loss/restore methods available");
                } else {
                    this.addTest(`${contextType} Context Loss/Restore`, "FAIL", "Context loss/restore methods missing");
                }
            } else {
                this.addTest(`${contextType} Context Loss Extension`, "FAIL", "Context loss extension not available");
                this.warnings.push("Context loss extension not available - context recovery not possible");
            }

            // Test context stability indicators
            if (gl.isContextLost()) {
                this.addTest(`${contextType} Context Status`, "FAIL", "Context is already lost");
                this.errors.push(`${contextType} context is lost`);
            } else {
                this.addTest(`${contextType} Context Status`, "PASS", "Context is active and stable");
            }

        } catch (error) {
            this.addTest(`${contextType} Context Stability`, "ERROR", `Stability test failed: ${error.message}`);
        }
    }

    /**
     * Test WebGL capabilities and limits
     */
    async testWebGLCapabilities(gl) {
        console.log("🧪 Testing WebGL Capabilities...");

        const capabilities = {};

        try {
            // Basic parameters
            const params = {
                "MAX_TEXTURE_SIZE": gl.MAX_TEXTURE_SIZE,
                "MAX_TEXTURE_IMAGE_UNITS": gl.MAX_TEXTURE_IMAGE_UNITS,
                "MAX_VERTEX_ATTRIBS": gl.MAX_VERTEX_ATTRIBS,
                "MAX_VERTEX_UNIFORM_VECTORS": gl.MAX_VERTEX_UNIFORM_VECTORS,
                "MAX_FRAGMENT_UNIFORM_VECTORS": gl.MAX_FRAGMENT_UNIFORM_VECTORS,
                "MAX_VARYING_VECTORS": gl.MAX_VARYING_VECTORS,
                "MAX_VIEWPORT_DIMS": gl.MAX_VIEWPORT_DIMS,
                "MAX_RENDERBUFFER_SIZE": gl.MAX_RENDERBUFFER_SIZE
            };

            Object.entries(params).forEach(([name, param]) => {
                try {
                    const value = gl.getParameter(param);
                    capabilities[name] = value;

                    // Check against minimum requirements
                    const result = this.validateParameter(name, value);
                    this.addTest(`WebGL ${name}`, result.status, result.message);

                } catch (error) {
                    this.addTest(`WebGL ${name}`, "ERROR", `Failed to query: ${error.message}`);
                }
            });

            // Test extensions
            const extensions = this.testWebGLExtensions(gl);
            capabilities.extensions = extensions;

            this.results.webgl = capabilities;

        } catch (error) {
            this.addTest("WebGL Capabilities", "ERROR", `Capabilities test failed: ${error.message}`);
        }
    }

    /**
     * Validate WebGL parameters against requirements
     */
    validateParameter(name, value) {
        const requirements = {
            "MAX_TEXTURE_SIZE": { min: 2048, recommended: 4096 },
            "MAX_TEXTURE_IMAGE_UNITS": { min: 8, recommended: 16 },
            "MAX_VERTEX_ATTRIBS": { min: 8, recommended: 16 },
            "MAX_VERTEX_UNIFORM_VECTORS": { min: 128, recommended: 256 },
            "MAX_FRAGMENT_UNIFORM_VECTORS": { min: 16, recommended: 32 },
            "MAX_VARYING_VECTORS": { min: 8, recommended: 16 }
        };

        const req = requirements[name];
        if (!req) {
            return { status: "INFO", message: `${name}: ${Array.isArray(value) ? value.join("x") : value}` };
        }

        const val = Array.isArray(value) ? Math.min(...value) : value;

        if (val < req.min) {
            return { status: "FAIL", message: `${name}: ${val} (below minimum ${req.min})` };
        } else if (val < req.recommended) {
            return { status: "WARN", message: `${name}: ${val} (below recommended ${req.recommended})` };
        } else {
            return { status: "PASS", message: `${name}: ${val} (meets requirements)` };
        }
    }

    /**
     * Test WebGL extensions
     */
    testWebGLExtensions(gl) {
        const criticalExtensions = [
            "ANGLE_instanced_arrays",
            "EXT_texture_filter_anisotropic",
            "WEBGL_lose_context",
            "OES_vertex_array_object"
        ];

        const usefulExtensions = [
            "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_pvrtc",
            "WEBGL_compressed_texture_etc1",
            "OES_texture_float",
            "OES_texture_half_float",
            "WEBGL_depth_texture"
        ];

        const extensions = {};

        [...criticalExtensions, ...usefulExtensions].forEach(ext => {
            const supported = gl.getExtension(ext) !== null;
            extensions[ext] = supported;

            const isCritical = criticalExtensions.includes(ext);
            const status = supported ? "PASS" : (isCritical ? "WARN" : "INFO");
            const message = `${ext}: ${supported ? "Available" : "Not available"}${isCritical && !supported ? " (may impact performance)" : ""}`;

            this.addTest(`Extension ${ext}`, status, message);
        });

        return extensions;
    }

    /**
     * Test shader compilation
     */
    async testShaderCompilation(gl) {
        console.log("🧪 Testing Shader Compilation...");

        const vertexShaderSource = `
            attribute vec2 aPosition;
            attribute vec2 aTexCoord;
            varying vec2 vTexCoord;
            void main() {
                gl_Position = vec4(aPosition, 0.0, 1.0);
                vTexCoord = aTexCoord;
            }
        `;

        const fragmentShaderSource = `
            precision mediump float;
            varying vec2 vTexCoord;
            uniform sampler2D uTexture;
            void main() {
                gl_FragColor = texture2D(uTexture, vTexCoord);
            }
        `;

        try {
            // Test vertex shader
            const vertexShader = this.compileShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
            if (vertexShader) {
                this.addTest("Vertex Shader Compilation", "PASS", "Vertex shader compiled successfully");
            } else {
                this.addTest("Vertex Shader Compilation", "FAIL", "Vertex shader compilation failed");
                return;
            }

            // Test fragment shader
            const fragmentShader = this.compileShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
            if (fragmentShader) {
                this.addTest("Fragment Shader Compilation", "PASS", "Fragment shader compiled successfully");
            } else {
                this.addTest("Fragment Shader Compilation", "FAIL", "Fragment shader compilation failed");
                return;
            }

            // Test program linking
            const program = gl.createProgram();
            gl.attachShader(program, vertexShader);
            gl.attachShader(program, fragmentShader);
            gl.linkProgram(program);

            if (gl.getProgramParameter(program, gl.LINK_STATUS)) {
                this.addTest("Shader Program Linking", "PASS", "Shader program linked successfully");
            } else {
                const linkLog = gl.getProgramInfoLog(program);
                this.addTest("Shader Program Linking", "FAIL", `Program linking failed: ${linkLog}`);
            }

            // Cleanup
            gl.deleteShader(vertexShader);
            gl.deleteShader(fragmentShader);
            gl.deleteProgram(program);

        } catch (error) {
            this.addTest("Shader System", "ERROR", `Shader test failed: ${error.message}`);
        }
    }

    /**
     * Compile a shader
     */
    compileShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            return shader;
        } else {
            const compileLog = gl.getShaderInfoLog(shader);
            console.error("Shader compilation error:", compileLog);
            gl.deleteShader(shader);
            return null;
        }
    }

    /**
     * Test buffer operations
     */
    async testBufferOperations(gl) {
        console.log("🧪 Testing Buffer Operations...");

        try {
            // Test vertex buffer creation
            const vertexBuffer = gl.createBuffer();
            if (vertexBuffer) {
                this.addTest("Vertex Buffer Creation", "PASS", "Vertex buffer created successfully");

                // Test buffer data
                const vertices = new Float32Array([-1, -1, 1, -1, 0, 1]);
                gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
                gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

                this.addTest("Buffer Data Upload", "PASS", "Buffer data uploaded successfully");

                gl.deleteBuffer(vertexBuffer);
            } else {
                this.addTest("Vertex Buffer Creation", "FAIL", "Failed to create vertex buffer");
            }

            // Test index buffer
            const indexBuffer = gl.createBuffer();
            if (indexBuffer) {
                const indices = new Uint16Array([0, 1, 2]);
                gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
                gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);

                this.addTest("Index Buffer Operations", "PASS", "Index buffer operations successful");

                gl.deleteBuffer(indexBuffer);
            } else {
                this.addTest("Index Buffer Creation", "FAIL", "Failed to create index buffer");
            }

        } catch (error) {
            this.addTest("Buffer Operations", "ERROR", `Buffer test failed: ${error.message}`);
        }
    }

    /**
     * Test framebuffer operations
     */
    async testFramebufferOperations(gl) {
        console.log("🧪 Testing Framebuffer Operations...");

        try {
            // Create framebuffer
            const framebuffer = gl.createFramebuffer();
            if (!framebuffer) {
                this.addTest("Framebuffer Creation", "FAIL", "Failed to create framebuffer");
                return;
            }

            gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);

            // Create texture for framebuffer
            const texture = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

            // Attach texture to framebuffer
            gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);

            // Check framebuffer status
            const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
            if (status === gl.FRAMEBUFFER_COMPLETE) {
                this.addTest("Framebuffer Operations", "PASS", "Framebuffer operations successful");
            } else {
                this.addTest("Framebuffer Operations", "FAIL", `Framebuffer incomplete: ${status}`);
            }

            // Cleanup
            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.deleteFramebuffer(framebuffer);
            gl.deleteTexture(texture);

        } catch (error) {
            this.addTest("Framebuffer Operations", "ERROR", `Framebuffer test failed: ${error.message}`);
        }
    }

    /**
     * Test texture system
     */
    async testTextureSystem() {
        console.log("🧪 Testing Texture System...");

        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

        if (!gl) {
            this.addTest("Texture System", "FAIL", "No WebGL context for texture testing");
            return;
        }

        const textureResults = {
            maxSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
            maxUnits: gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS),
            formats: {},
            compression: {},
            operations: {}
        };

        try {
            // Test basic texture creation
            const texture = gl.createTexture();
            if (texture) {
                gl.bindTexture(gl.TEXTURE_2D, texture);

                // Test basic texture upload
                const data = new Uint8Array([255, 0, 0, 255]); // Red pixel
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);

                this.addTest("Basic Texture Creation", "PASS", "Basic texture operations successful");
                textureResults.operations.basic = true;

                gl.deleteTexture(texture);
            } else {
                this.addTest("Basic Texture Creation", "FAIL", "Failed to create texture");
                textureResults.operations.basic = false;
            }

            // Test large texture creation
            await this.testLargeTexture(gl, textureResults);

            // Test texture formats
            await this.testTextureFormats(gl, textureResults);

            // Test texture compression
            await this.testTextureCompression(gl, textureResults);

        } catch (error) {
            this.addTest("Texture System", "ERROR", `Texture system test failed: ${error.message}`);
        }

        this.results.textures = textureResults;
    }

    /**
     * Test large texture handling
     */
    async testLargeTexture(gl, results) {
        try {
            const maxSize = results.maxSize;
            const testSizes = [512, 1024, 2048, Math.min(4096, maxSize)];

            for (const size of testSizes) {
                const texture = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, texture);

                try {
                    // Try to allocate texture of this size
                    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, size, size, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

                    const error = gl.getError();
                    if (error === gl.NO_ERROR) {
                        this.addTest(`Texture Size ${size}x${size}`, "PASS", `Successfully allocated ${size}x${size} texture`);
                        results.operations[`size_${size}`] = true;
                    } else {
                        this.addTest(`Texture Size ${size}x${size}`, "FAIL", `Failed to allocate ${size}x${size} texture (GL error: ${error})`);
                        results.operations[`size_${size}`] = false;
                    }
                } catch (error) {
                    this.addTest(`Texture Size ${size}x${size}`, "ERROR", `Exception allocating ${size}x${size}: ${error.message}`);
                    results.operations[`size_${size}`] = false;
                }

                gl.deleteTexture(texture);
            }
        } catch (error) {
            this.addTest("Large Texture Test", "ERROR", `Large texture test failed: ${error.message}`);
        }
    }

    /**
     * Test texture formats
     */
    async testTextureFormats(gl, results) {
        const formats = [
            { name: "RGBA", format: gl.RGBA, type: gl.UNSIGNED_BYTE },
            { name: "RGB", format: gl.RGB, type: gl.UNSIGNED_BYTE },
            { name: "LUMINANCE_ALPHA", format: gl.LUMINANCE_ALPHA, type: gl.UNSIGNED_BYTE },
            { name: "LUMINANCE", format: gl.LUMINANCE, type: gl.UNSIGNED_BYTE },
            { name: "ALPHA", format: gl.ALPHA, type: gl.UNSIGNED_BYTE }
        ];

        for (const fmt of formats) {
            try {
                const texture = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, texture);

                const size = fmt.format === gl.RGBA ? 4 : fmt.format === gl.RGB ? 3 : fmt.format === gl.LUMINANCE_ALPHA ? 2 : 1;
                const data = new Uint8Array(size).fill(255);

                gl.texImage2D(gl.TEXTURE_2D, 0, fmt.format, 1, 1, 0, fmt.format, fmt.type, data);

                const error = gl.getError();
                if (error === gl.NO_ERROR) {
                    this.addTest(`Texture Format ${fmt.name}`, "PASS", `${fmt.name} format supported`);
                    results.formats[fmt.name] = true;
                } else {
                    this.addTest(`Texture Format ${fmt.name}`, "FAIL", `${fmt.name} format failed (GL error: ${error})`);
                    results.formats[fmt.name] = false;
                }

                gl.deleteTexture(texture);

            } catch (error) {
                this.addTest(`Texture Format ${fmt.name}`, "ERROR", `${fmt.name} test failed: ${error.message}`);
                results.formats[fmt.name] = false;
            }
        }
    }

    /**
     * Test texture compression support
     */
    async testTextureCompression(gl, results) {
        const compressionExtensions = [
            "WEBGL_compressed_texture_s3tc",
            "WEBGL_compressed_texture_pvrtc",
            "WEBGL_compressed_texture_etc1",
            "WEBGL_compressed_texture_astc"
        ];

        for (const ext of compressionExtensions) {
            const extension = gl.getExtension(ext);
            const supported = extension !== null;

            results.compression[ext] = supported;
            this.addTest(`Compression ${ext}`, supported ? "PASS" : "INFO", `${ext}: ${supported ? "Available" : "Not available"}`);
        }
    }

    /**
     * Test performance characteristics
     */
    async testPerformance() {
        console.log("🧪 Testing Performance...");

        const canvas = document.createElement("canvas");
        canvas.width = 512;
        canvas.height = 512;
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

        if (!gl) {
            this.addTest("Performance Test", "FAIL", "No WebGL context for performance testing");
            return;
        }

        const performanceResults = {};

        try {
            // Test draw call performance
            const drawCallPerf = await this.measureDrawCallPerformance(gl);
            performanceResults.drawCalls = drawCallPerf;

            // Test texture bind performance
            const textureBindPerf = await this.measureTextureBindPerformance(gl);
            performanceResults.textureBinds = textureBindPerf;

            // Test memory allocation performance
            const memoryPerf = await this.measureMemoryPerformance(gl);
            performanceResults.memory = memoryPerf;

        } catch (error) {
            this.addTest("Performance Test", "ERROR", `Performance test failed: ${error.message}`);
        }

        this.results.performance = performanceResults;
    }

    /**
     * Measure draw call performance
     */
    async measureDrawCallPerformance(gl) {
        const iterations = 1000;
        const startTime = performance.now();

        // Create simple test setup
        const buffer = gl.createBuffer();
        const vertices = new Float32Array([-1, -1, 1, -1, 0, 1]);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

        // Measure draw calls
        for (let i = 0; i < iterations; i++) {
            gl.drawArrays(gl.TRIANGLES, 0, 3);
        }

        const endTime = performance.now();
        const duration = endTime - startTime;
        const callsPerSecond = (iterations / duration) * 1000;

        gl.deleteBuffer(buffer);

        const rating = callsPerSecond > 10000 ? "EXCELLENT" : callsPerSecond > 5000 ? "GOOD" : callsPerSecond > 1000 ? "FAIR" : "POOR";
        this.addTest("Draw Call Performance", "INFO", `${callsPerSecond.toFixed(0)} calls/sec (${rating})`);

        return { callsPerSecond, rating, duration, iterations };
    }

    /**
     * Measure texture binding performance
     */
    async measureTextureBindPerformance(gl) {
        const textureCount = 16;
        const bindIterations = 1000;

        // Create test textures
        const textures = [];
        for (let i = 0; i < textureCount; i++) {
            const texture = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 64, 64, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
            textures.push(texture);
        }

        // Measure binding performance
        const startTime = performance.now();

        for (let i = 0; i < bindIterations; i++) {
            const texture = textures[i % textureCount];
            gl.activeTexture(gl.TEXTURE0 + (i % 8));
            gl.bindTexture(gl.TEXTURE_2D, texture);
        }

        const endTime = performance.now();
        const duration = endTime - startTime;
        const bindsPerSecond = (bindIterations / duration) * 1000;

        // Cleanup
        textures.forEach(tex => gl.deleteTexture(tex));

        const rating = bindsPerSecond > 50000 ? "EXCELLENT" : bindsPerSecond > 20000 ? "GOOD" : bindsPerSecond > 10000 ? "FAIR" : "POOR";
        this.addTest("Texture Bind Performance", "INFO", `${bindsPerSecond.toFixed(0)} binds/sec (${rating})`);

        return { bindsPerSecond, rating, duration, iterations: bindIterations };
    }

    /**
     * Measure memory allocation performance
     */
    async measureMemoryPerformance(gl) {
        const allocationCount = 100;
        const textureSize = 256;

        const startTime = performance.now();
        const textures = [];

        // Allocate textures
        for (let i = 0; i < allocationCount; i++) {
            const texture = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, textureSize, textureSize, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
            textures.push(texture);
        }

        const allocEndTime = performance.now();

        // Deallocate textures
        textures.forEach(tex => gl.deleteTexture(tex));

        const deallocEndTime = performance.now();

        const allocDuration = allocEndTime - startTime;
        const deallocDuration = deallocEndTime - allocEndTime;
        const totalMemoryMB = (allocationCount * textureSize * textureSize * 4) / (1024 * 1024);

        const allocMBPerSec = totalMemoryMB / (allocDuration / 1000);
        const deallocMBPerSec = totalMemoryMB / (deallocDuration / 1000);

        this.addTest("Memory Allocation Performance", "INFO", `Alloc: ${allocMBPerSec.toFixed(1)} MB/sec, Dealloc: ${deallocMBPerSec.toFixed(1)} MB/sec`);

        return {
            allocMBPerSec,
            deallocMBPerSec,
            totalMemoryMB,
            allocDuration,
            deallocDuration
        };
    }

    /**
     * Run stress tests
     */
    async runStressTests() {
        console.log("🧪 Running Stress Tests...");

        try {
            await this.testMaxTextures();
            await this.testMaxDrawCalls();
            await this.testMemoryPressure();
        } catch (error) {
            this.addTest("Stress Tests", "ERROR", `Stress test failed: ${error.message}`);
        }
    }

    /**
     * Test maximum texture allocation
     */
    async testMaxTextures() {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

        if (!gl) return;

        const textures = [];
        let allocatedCount = 0;

        try {
            // Try to allocate textures until we hit limits
            for (let i = 0; i < 1000; i++) {
                const texture = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, texture);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

                const error = gl.getError();
                if (error !== gl.NO_ERROR) {
                    gl.deleteTexture(texture);
                    break;
                }

                textures.push(texture);
                allocatedCount++;

                // Check every 100 textures
                if (allocatedCount % 100 === 0) {
                    await new Promise(resolve => setTimeout(resolve, 0)); // Yield
                }
            }

        } catch (error) {
            console.warn("Texture allocation stopped due to error:", error);
        }

        // Cleanup
        textures.forEach(tex => gl.deleteTexture(tex));

        const memoryMB = (allocatedCount * 256 * 256 * 4) / (1024 * 1024);

        if (allocatedCount > 200) {
            this.addTest("Max Texture Allocation", "PASS", `Allocated ${allocatedCount} textures (${memoryMB.toFixed(1)}MB)`);
        } else if (allocatedCount > 50) {
            this.addTest("Max Texture Allocation", "WARN", `Limited to ${allocatedCount} textures (${memoryMB.toFixed(1)}MB)`);
        } else {
            this.addTest("Max Texture Allocation", "FAIL", `Only ${allocatedCount} textures allocated (${memoryMB.toFixed(1)}MB)`);
        }
    }

    /**
     * Test maximum draw calls per frame
     */
    async testMaxDrawCalls() {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

        if (!gl) return;

        const buffer = gl.createBuffer();
        const vertices = new Float32Array([-1, -1, 1, -1, 0, 1]);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

        const maxDrawCalls = 10000;
        const startTime = performance.now();

        for (let i = 0; i < maxDrawCalls; i++) {
            gl.drawArrays(gl.TRIANGLES, 0, 3);
        }

        const endTime = performance.now();
        const duration = endTime - startTime;
        const callsPerFrame = Math.floor(maxDrawCalls / (duration / 16.67)); // Assuming 60fps target

        gl.deleteBuffer(buffer);

        if (callsPerFrame > 1000) {
            this.addTest("Max Draw Calls", "PASS", `Can handle ${callsPerFrame} draw calls per frame (60fps)`);
        } else if (callsPerFrame > 500) {
            this.addTest("Max Draw Calls", "WARN", `Limited to ${callsPerFrame} draw calls per frame`);
        } else {
            this.addTest("Max Draw Calls", "FAIL", `Only ${callsPerFrame} draw calls per frame`);
        }
    }

    /**
     * Test memory pressure handling
     */
    async testMemoryPressure() {
        // This test is more observational - we check if the browser/GPU
        // handles memory pressure gracefully

        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

        if (!gl) return;

        let successfulAllocations = 0;
        let failedAllocations = 0;

        try {
            // Try to allocate increasingly large textures
            const sizes = [512, 1024, 2048, 4096, 8192];

            for (const size of sizes) {
                const textures = [];

                try {
                    // Allocate multiple textures of this size
                    for (let i = 0; i < 20; i++) {
                        const texture = gl.createTexture();
                        gl.bindTexture(gl.TEXTURE_2D, texture);
                        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, size, size, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

                        const error = gl.getError();
                        if (error === gl.NO_ERROR) {
                            textures.push(texture);
                            successfulAllocations++;
                        } else {
                            gl.deleteTexture(texture);
                            failedAllocations++;
                            break;
                        }
                    }
                } finally {
                    // Cleanup textures
                    textures.forEach(tex => gl.deleteTexture(tex));
                }

                // Force garbage collection if available
                if (window.gc && typeof window.gc === "function") {
                    window.gc();
                }
            }

        } catch (error) {
            this.addTest("Memory Pressure Test", "ERROR", `Memory pressure test failed: ${error.message}`);
            return;
        }

        const totalAttempts = successfulAllocations + failedAllocations;
        const successRate = (successfulAllocations / totalAttempts) * 100;

        if (successRate > 80) {
            this.addTest("Memory Pressure Handling", "PASS", `${successRate.toFixed(1)}% allocation success rate`);
        } else if (successRate > 50) {
            this.addTest("Memory Pressure Handling", "WARN", `${successRate.toFixed(1)}% allocation success rate`);
        } else {
            this.addTest("Memory Pressure Handling", "FAIL", `${successRate.toFixed(1)}% allocation success rate`);
        }
    }

    /**
     * Add test result
     */
    addTest(name, status, message) {
        const test = {
            name,
            status,
            message,
            timestamp: Date.now()
        };

        this.tests.push(test);

        const icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "ERROR": "💥",
            "INFO": "📊"
        }[status] || "❓";

        console.log(`${icon} ${name}: ${message}`);
    }

    /**
     * Generate final diagnostic report
     */
    generateReport() {
        const passCount = this.tests.filter(t => t.status === "PASS").length;
        const failCount = this.tests.filter(t => t.status === "FAIL").length;
        const warnCount = this.tests.filter(t => t.status === "WARN").length;
        const errorCount = this.tests.filter(t => t.status === "ERROR").length;

        console.log("\
📋 WebGL Diagnostic Report:");
        console.log("============================");
        console.log(`✅ Passed: ${passCount}`);
        console.log(`❌ Failed: ${failCount}`);
        console.log(`⚠️ Warnings: ${warnCount}`);
        console.log(`💥 Errors: ${errorCount}`);
        console.log(`📊 Total Tests: ${this.tests.length}`);

        // Generate recommendations based on test results
        this.generateDiagnosticRecommendations();

        if (this.recommendations.length > 0) {
            console.log("\
💡 Recommendations:");
            this.recommendations.forEach(rec => console.log(`   - ${rec}`));
        }
    }

    /**
     * Generate recommendations based on diagnostic results
     */
    generateDiagnosticRecommendations() {
        const failedTests = this.tests.filter(t => t.status === "FAIL" || t.status === "ERROR");

        if (failedTests.some(t => t.name.includes("WebGL"))) {
            this.recommendations.push("Consider using Canvas fallback mode for better compatibility");
        }

        if (failedTests.some(t => t.name.includes("Texture"))) {
            this.recommendations.push("Reduce texture sizes and use texture atlasing");
            this.recommendations.push("Enable texture compression if available");
        }

        if (failedTests.some(t => t.name.includes("Performance"))) {
            this.recommendations.push("Implement sprite batching to reduce draw calls");
            this.recommendations.push("Use level-of-detail (LOD) system for distant objects");
        }

        if (this.results.browser?.capabilities?.device?.mobile) {
            this.recommendations.push("Use mobile-optimized settings (smaller textures, fewer sprites)");
            this.recommendations.push("Implement aggressive texture garbage collection");
        }

        const warnTests = this.tests.filter(t => t.status === "WARN");
        if (warnTests.length > 5) {
            this.recommendations.push("Device has limited capabilities - consider reduced quality mode");
        }
    }

    /**
     * Get complete diagnostic report
     */
    getReport() {
        return {
            ...this.results,
            tests: this.tests,
            warnings: this.warnings,
            errors: this.errors,
            recommendations: this.recommendations,
            summary: {
                totalTests: this.tests.length,
                passed: this.tests.filter(t => t.status === "PASS").length,
                failed: this.tests.filter(t => t.status === "FAIL").length,
                warnings: this.tests.filter(t => t.status === "WARN").length,
                errors: this.tests.filter(t => t.status === "ERROR").length,
                overall: this.tests.filter(t => t.status === "FAIL" || t.status === "ERROR").length === 0 ? "HEALTHY" : "ISSUES_DETECTED"
            }
        };
    }
}

// Utility function for easy diagnostic testing
export async function runWebGLDiagnostics() {
    const diagnostics = new WebGLDiagnostics();
    return await diagnostics.runDiagnostics();
}
