/**
 * Machine Learning Configuration Constants
 * Contains configuration for TensorFlow.js initialization and ML features
 */

export const MLConfig = {
    // Backend configuration
    backend: {
        preferred: 'webgl',
        fallbacks: ['cpu'],
        // WebGL-specific settings
        webgl: {
            // Force 32-bit floats for better performance 
            // (some GPUs perform better with explicit precision)
            forceHalfFloat: false,
            // Enable optimizations for better performance
            checkNumericalProblems: false,
            // Allocate GPU memory efficiently 
            // (helps prevent out-of-memory errors on mobile)
            memoryGrowth: true,
            // Texture cache size in MB
            textureMemoryLimit: 256,
            // Max texture allocation attempts before fallback
            maxAllocationAttempts: 3
        },
        cpu: {
            // Number of threads for CPU backend (0 = auto)
            numThreads: 0,
            // Enable WASM SIMD if available
            enableWasmSIMD: true
        }
    },

    // Performance monitoring configuration
    performance: {
        // Track inference times
        enableInferenceTracking: true,
        // Memory usage monitoring
        enableMemoryTracking: true,
        // Log performance warnings
        logPerformanceWarnings: true,
        // Performance thresholds (milliseconds)
        thresholds: {
            // Warn if inference takes longer than this
            slowInference: 50,
            // Error if inference takes longer than this
            criticalInference: 200,
            // Frame budget for 60 FPS (16.67ms)
            frameBudget: 16
        }
    },

    // Memory management
    memory: {
        // Auto-dispose tensors after this many inference calls
        autoDisposeThreshold: 100,
        // Garbage collect memory every N frames
        gcFrequency: 300, // ~5 seconds at 60fps
        // Maximum GPU memory before forcing cleanup (MB)
        maxGpuMemory: 512,
        // Enable detailed memory debugging
        debugMemory: false
    },

    // Model configuration
    models: {
        // Placeholder for future AI model configurations
        pathfinding: {
            inputShape: [32, 32, 1], // 32x32 grid with 1 channel
            enabled: false
        },
        unitBehavior: {
            inputShape: [16], // 16 behavioral features
            enabled: false
        },
        strategicAnalysis: {
            inputShape: [64], // 64 strategic features
            enabled: false
        }
    },

    // Development and debugging
    debug: {
        // Enable TensorFlow.js debug mode
        enableTFDebug: false,
        // Log backend initialization details
        logBackendInit: true,
        // Log performance metrics
        logPerformanceMetrics: true,
        // Log memory usage
        logMemoryUsage: true,
        // Verbose logging for troubleshooting
        verbose: false
    }
};

// Environment-specific overrides
if (typeof window !== 'undefined') {
    // Browser-specific configurations
    if (navigator.hardwareConcurrency) {
        MLConfig.backend.cpu.numThreads = Math.min(navigator.hardwareConcurrency, 4);
    }
    
    // Mobile device detection and optimization
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile) {
        // Reduce memory limits for mobile devices
        MLConfig.backend.webgl.textureMemoryLimit = 128;
        MLConfig.memory.maxGpuMemory = 256;
        MLConfig.memory.gcFrequency = 150; // More frequent GC
        MLConfig.performance.thresholds.slowInference = 100; // More lenient on mobile
    }
    
    // Development vs production
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        MLConfig.debug.enableTFDebug = true;
        MLConfig.debug.verbose = true;
    }
}