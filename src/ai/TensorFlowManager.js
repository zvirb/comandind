/**
 * TensorFlow.js WebGL Backend Manager
 * Handles initialization, fallback, and performance monitoring for ML features
 */

import * as tf from '@tensorflow/tfjs';
import { MLConfig } from './MLConfig.js';

export class TensorFlowManager {
    constructor() {
        this.isInitialized = false;
        this.currentBackend = null;
        this.initializationAttempts = 0;
        this.maxInitAttempts = 3;
        
        // Performance tracking
        this.performanceMetrics = {
            inferenceCount: 0,
            totalInferenceTime: 0,
            averageInferenceTime: 0,
            lastInferenceTime: 0,
            slowInferences: 0,
            memoryLeaks: 0
        };
        
        // Memory management
        this.memoryTracker = {
            tensorCount: 0,
            lastGC: Date.now(),
            peakMemoryUsage: 0,
            currentMemoryUsage: 0
        };
        
        // Test tensors for validation
        this.testTensors = [];
        
        // Bind methods
        this.performanceTest = this.performanceTest.bind(this);
        this.cleanup = this.cleanup.bind(this);
        
        // Setup cleanup on page unload
        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', this.cleanup);
        }
    }

    /**
     * Initialize TensorFlow.js with WebGL backend and fallback support
     */
    async initialize() {
        if (this.isInitialized) {
            console.warn('TensorFlow.js is already initialized');
            return true;
        }

        this.initializationAttempts++;
        
        if (MLConfig.debug.logBackendInit) {
            console.log(`🧠 Initializing TensorFlow.js (attempt ${this.initializationAttempts}/${this.maxInitAttempts})`);
        }

        try {
            // Set up TensorFlow.js flags before backend initialization
            this.configureTensorFlowFlags();
            
            // Try to initialize with preferred backend (WebGL)
            const success = await this.initializeWithBackend(MLConfig.backend.preferred);
            
            if (success) {
                this.isInitialized = true;
                this.currentBackend = MLConfig.backend.preferred;
                
                // Perform validation test
                const testResult = await this.validateBackend();
                if (!testResult.success) {
                    console.warn('⚠️ Backend validation failed, attempting fallback');
                    return this.fallbackToNextBackend();
                }
                
                // Run performance test
                await this.performanceTest();
                
                // Start memory monitoring
                this.startMemoryMonitoring();
                
                if (MLConfig.debug.logBackendInit) {
                    console.log(`✅ TensorFlow.js initialized successfully with ${this.currentBackend} backend`);
                }
                
                return true;
            } else {
                return this.fallbackToNextBackend();
            }
            
        } catch (error) {
            console.error('❌ TensorFlow.js initialization failed:', error);
            return this.fallbackToNextBackend();
        }
    }

    /**
     * Configure TensorFlow.js flags for optimal performance
     */
    configureTensorFlowFlags() {
        // Enable debug mode if requested
        if (MLConfig.debug.enableTFDebug) {
            tf.ENV.set('DEBUG', true);
        }
        
        // WebGL-specific flags
        if (MLConfig.backend.preferred === 'webgl') {
            // Force float32 precision if configured
            if (!MLConfig.backend.webgl.forceHalfFloat) {
                tf.ENV.set('WEBGL_FORCE_F16_TEXTURES', false);
            }
            
            // Disable numerical problem checking for performance
            if (!MLConfig.backend.webgl.checkNumericalProblems) {
                tf.ENV.set('WEBGL_CHECK_NUMERICAL_PROBLEMS', false);
            }
            
            // Memory growth setting
            if (MLConfig.backend.webgl.memoryGrowth) {
                tf.ENV.set('WEBGL_DELETE_TEXTURE_THRESHOLD', 0);
            }
        }
        
        // CPU backend configuration
        if (MLConfig.backend.cpu.numThreads > 0) {
            tf.ENV.set('WASM_HAS_MULTITHREAD_SUPPORT', true);
        }
        
        if (MLConfig.debug.verbose) {
            console.log('🔧 TensorFlow.js flags configured:', {
                DEBUG: tf.ENV.getBool('DEBUG'),
                WEBGL_FORCE_F16_TEXTURES: tf.ENV.getBool('WEBGL_FORCE_F16_TEXTURES'),
                WEBGL_CHECK_NUMERICAL_PROBLEMS: tf.ENV.getBool('WEBGL_CHECK_NUMERICAL_PROBLEMS')
            });
        }
    }

    /**
     * Initialize with specific backend
     */
    async initializeWithBackend(backendName) {
        try {
            await tf.setBackend(backendName);
            await tf.ready();
            
            // Verify backend is actually set
            const actualBackend = tf.getBackend();
            if (actualBackend !== backendName) {
                console.warn(`⚠️ Requested ${backendName} backend, but got ${actualBackend}`);
                return false;
            }
            
            return true;
            
        } catch (error) {
            console.error(`❌ Failed to initialize ${backendName} backend:`, error);
            return false;
        }
    }

    /**
     * Fallback to the next available backend
     */
    async fallbackToNextBackend() {
        if (this.initializationAttempts >= this.maxInitAttempts) {
            console.error('💀 All backend initialization attempts failed');
            return false;
        }

        // Try CPU backend as fallback
        console.log('🔄 Attempting CPU backend fallback...');
        
        try {
            const success = await this.initializeWithBackend('cpu');
            if (success) {
                this.isInitialized = true;
                this.currentBackend = 'cpu';
                
                console.warn('⚠️ Running on CPU backend - performance may be reduced');
                
                // Still validate and test
                const testResult = await this.validateBackend();
                if (testResult.success) {
                    await this.performanceTest();
                    this.startMemoryMonitoring();
                    return true;
                }
            }
        } catch (error) {
            console.error('❌ CPU backend fallback failed:', error);
        }

        return false;
    }

    /**
     * Validate backend with simple tensor operations
     */
    async validateBackend() {
        try {
            // Create test tensors
            const a = tf.tensor2d([[1, 2], [3, 4]]);
            const b = tf.tensor2d([[5, 6], [7, 8]]);
            
            // Perform basic operations
            const sum = tf.add(a, b);
            const product = tf.matMul(a, b);
            
            // Get results to ensure computation completes
            const sumData = await sum.data();
            const productData = await product.data();
            
            // Verify expected results
            const expectedSum = [6, 8, 10, 12];
            const expectedProduct = [19, 22, 43, 50];
            
            const sumValid = expectedSum.every((val, i) => Math.abs(val - sumData[i]) < 0.001);
            const productValid = expectedProduct.every((val, i) => Math.abs(val - productData[i]) < 0.001);
            
            // Cleanup test tensors
            a.dispose();
            b.dispose();
            sum.dispose();
            product.dispose();
            
            if (sumValid && productValid) {
                if (MLConfig.debug.verbose) {
                    console.log('✅ Backend validation passed');
                }
                return { success: true };
            } else {
                console.error('❌ Backend validation failed - incorrect computation results');
                return { success: false, reason: 'Incorrect computation results' };
            }
            
        } catch (error) {
            console.error('❌ Backend validation failed:', error);
            return { success: false, reason: error.message };
        }
    }

    /**
     * Run performance test to measure inference speed
     */
    async performanceTest() {
        if (!this.isInitialized) {
            console.warn('⚠️ TensorFlow.js not initialized, skipping performance test');
            return;
        }

        try {
            const testSize = 32;
            const iterations = 10;
            
            console.log(`🚀 Running performance test (${iterations} iterations, ${testSize}x${testSize} tensors)`);
            
            const times = [];
            
            for (let i = 0; i < iterations; i++) {
                const start = performance.now();
                
                // Create test tensor
                const input = tf.randomNormal([testSize, testSize]);
                
                // Perform computations
                const result = tf.tidy(() => {
                    const conv = tf.conv2d(
                        input.expandDims(0).expandDims(-1), 
                        tf.randomNormal([3, 3, 1, 1]), 
                        [1, 1], 
                        'same'
                    );
                    return tf.relu(conv);
                });
                
                // Wait for GPU completion
                await result.data();
                
                const end = performance.now();
                times.push(end - start);
                
                // Cleanup
                input.dispose();
                result.dispose();
            }
            
            const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);
            
            // Store performance metrics
            this.performanceMetrics.averageInferenceTime = avgTime;
            this.performanceMetrics.lastInferenceTime = avgTime;
            
            console.log(`📊 Performance Test Results (${this.currentBackend} backend):`);
            console.log(`   Average: ${avgTime.toFixed(2)}ms`);
            console.log(`   Min: ${minTime.toFixed(2)}ms`);
            console.log(`   Max: ${maxTime.toFixed(2)}ms`);
            
            // Check against thresholds
            if (avgTime > MLConfig.performance.thresholds.criticalInference) {
                console.warn(`⚠️ Critical performance warning: Average inference time (${avgTime.toFixed(2)}ms) exceeds critical threshold (${MLConfig.performance.thresholds.criticalInference}ms)`);
            } else if (avgTime > MLConfig.performance.thresholds.slowInference) {
                console.warn(`⚠️ Performance warning: Average inference time (${avgTime.toFixed(2)}ms) exceeds slow threshold (${MLConfig.performance.thresholds.slowInference}ms)`);
            } else {
                console.log('✅ Performance test passed - inference times within acceptable limits');
            }
            
            // Check frame budget compliance
            if (avgTime > MLConfig.performance.thresholds.frameBudget) {
                console.warn(`⚠️ Frame budget warning: Inference time may impact 60 FPS target`);
            }
            
        } catch (error) {
            console.error('❌ Performance test failed:', error);
        }
    }

    /**
     * Start memory monitoring
     */
    startMemoryMonitoring() {
        if (!MLConfig.memory.gcFrequency) return;
        
        const monitorInterval = setInterval(() => {
            this.checkMemoryUsage();
            
            // Perform garbage collection if needed
            if (Date.now() - this.memoryTracker.lastGC > (MLConfig.memory.gcFrequency * 16.67)) {
                this.performGarbageCollection();
            }
        }, 5000); // Check every 5 seconds
        
        // Store interval for cleanup
        this.memoryMonitorInterval = monitorInterval;
    }

    /**
     * Check current memory usage
     */
    checkMemoryUsage() {
        const memInfo = tf.memory();
        
        this.memoryTracker.tensorCount = memInfo.numTensors;
        this.memoryTracker.currentMemoryUsage = memInfo.numBytes / (1024 * 1024); // Convert to MB
        
        if (this.memoryTracker.currentMemoryUsage > this.memoryTracker.peakMemoryUsage) {
            this.memoryTracker.peakMemoryUsage = this.memoryTracker.currentMemoryUsage;
        }
        
        if (MLConfig.debug.logMemoryUsage) {
            console.log(`🧠 Memory usage: ${this.memoryTracker.currentMemoryUsage.toFixed(2)}MB, Tensors: ${this.memoryTracker.tensorCount}`);
        }
        
        // Check for memory leaks
        if (this.memoryTracker.currentMemoryUsage > MLConfig.memory.maxGpuMemory) {
            console.warn(`⚠️ High memory usage detected: ${this.memoryTracker.currentMemoryUsage.toFixed(2)}MB`);
            this.performGarbageCollection();
        }
    }

    /**
     * Perform garbage collection
     */
    performGarbageCollection() {
        try {
            const beforeMemory = tf.memory();
            
            // Dispose of any test tensors
            this.testTensors.forEach(tensor => {
                if (!tensor.isDisposed) {
                    tensor.dispose();
                }
            });
            this.testTensors = [];
            
            // Force TensorFlow.js garbage collection
            tf.disposeVariables();
            
            const afterMemory = tf.memory();
            const freedMemory = (beforeMemory.numBytes - afterMemory.numBytes) / (1024 * 1024);
            
            this.memoryTracker.lastGC = Date.now();
            
            if (MLConfig.debug.logMemoryUsage && freedMemory > 0) {
                console.log(`🗑️ Garbage collection freed ${freedMemory.toFixed(2)}MB`);
            }
            
        } catch (error) {
            console.error('❌ Garbage collection failed:', error);
        }
    }

    /**
     * Get current status and metrics
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            backend: this.currentBackend,
            performance: { ...this.performanceMetrics },
            memory: { 
                ...this.memoryTracker,
                tfMemory: this.isInitialized ? tf.memory() : null
            },
            config: MLConfig
        };
    }

    /**
     * Get backend capabilities
     */
    getCapabilities() {
        if (!this.isInitialized) {
            return { available: false };
        }
        
        return {
            available: true,
            backend: this.currentBackend,
            webglSupport: this.currentBackend === 'webgl',
            performanceClass: this.performanceMetrics.averageInferenceTime < MLConfig.performance.thresholds.slowInference ? 'fast' : 'slow',
            memoryClass: this.memoryTracker.peakMemoryUsage < MLConfig.memory.maxGpuMemory * 0.5 ? 'low' : 'high'
        };
    }

    /**
     * Create a simple test inference (placeholder for future AI models)
     */
    async testInference(inputData = null) {
        if (!this.isInitialized) {
            throw new Error('TensorFlow.js not initialized');
        }

        const start = performance.now();
        
        try {
            // Create test input if none provided
            const input = inputData || tf.randomNormal([1, 32, 32, 1]);
            
            // Simple test operation (placeholder for actual model inference)
            const result = tf.tidy(() => {
                const conv = tf.conv2d(input, tf.randomNormal([3, 3, 1, 8]), [1, 1], 'same');
                const relu = tf.relu(conv);
                // Use maxPool2d instead of globalMaxPool for broader compatibility
                return tf.maxPool(relu, [2, 2], [2, 2], 'valid');
            });
            
            // Wait for completion
            const output = await result.data();
            
            const end = performance.now();
            const inferenceTime = end - start;
            
            // Update performance metrics
            this.performanceMetrics.inferenceCount++;
            this.performanceMetrics.totalInferenceTime += inferenceTime;
            this.performanceMetrics.lastInferenceTime = inferenceTime;
            this.performanceMetrics.averageInferenceTime = 
                this.performanceMetrics.totalInferenceTime / this.performanceMetrics.inferenceCount;
            
            if (inferenceTime > MLConfig.performance.thresholds.slowInference) {
                this.performanceMetrics.slowInferences++;
            }
            
            // Cleanup
            if (!inputData) input.dispose();
            result.dispose();
            
            return {
                success: true,
                inferenceTime,
                outputShape: result.shape,
                outputSize: output.length
            };
            
        } catch (error) {
            const end = performance.now();
            console.error('❌ Test inference failed:', error);
            
            return {
                success: false,
                error: error.message,
                inferenceTime: end - start
            };
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('🧹 Cleaning up TensorFlow.js resources...');
        
        try {
            // Clear memory monitor
            if (this.memoryMonitorInterval) {
                clearInterval(this.memoryMonitorInterval);
            }
            
            // Dispose test tensors
            this.testTensors.forEach(tensor => {
                if (!tensor.isDisposed) {
                    tensor.dispose();
                }
            });
            this.testTensors = [];
            
            // Dispose variables and perform final GC
            if (this.isInitialized) {
                tf.disposeVariables();
            }
            
            this.isInitialized = false;
            this.currentBackend = null;
            
            console.log('✅ TensorFlow.js cleanup completed');
            
        } catch (error) {
            console.error('❌ Cleanup failed:', error);
        }
    }

    /**
     * Reinitialize if needed (useful for context loss recovery)
     */
    async reinitialize() {
        console.log('🔄 Reinitializing TensorFlow.js...');
        this.cleanup();
        this.initializationAttempts = 0;
        return this.initialize();
    }
}