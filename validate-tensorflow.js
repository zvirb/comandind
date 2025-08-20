#!/usr/bin/env node

/**
 * TensorFlow.js Validation Script
 * Provides concrete evidence for TensorFlow.js performance claims
 */

import { TensorFlowManager } from './src/ai/TensorFlowManager.js';

async function validateTensorFlowJS() {
    console.log('🔍 TENSORFLOW.JS VALIDATION - COLLECTING CONCRETE EVIDENCE');
    console.log('================================================================');
    
    const evidenceLog = [];
    
    function logEvidence(category, message, data = null) {
        const timestamp = new Date().toISOString();
        const evidence = {
            timestamp,
            category,
            message,
            data
        };
        evidenceLog.push(evidence);
        console.log(`[${timestamp}] [${category}] ${message}`);
        if (data) console.log('   Data:', JSON.stringify(data, null, 2));
    }
    
    try {
        // Initialize TensorFlow Manager
        logEvidence('INIT', 'Initializing TensorFlow.js Manager...');
        const tfManager = new TensorFlowManager();
        
        // Test initialization
        logEvidence('INIT', 'Starting TensorFlow.js initialization...');
        const startInit = performance.now();
        const initSuccess = await tfManager.initialize();
        const initTime = performance.now() - startInit;
        
        logEvidence('INIT', `Initialization ${initSuccess ? 'SUCCESS' : 'FAILED'}`, {
            success: initSuccess,
            initializationTime: `${initTime.toFixed(2)}ms`
        });
        
        if (!initSuccess) {
            throw new Error('TensorFlow.js initialization failed');
        }
        
        // Get backend information
        const status = tfManager.getStatus();
        logEvidence('BACKEND', 'Backend Status Retrieved', {
            backend: status.backend,
            initialized: status.initialized,
            currentBackend: status.tensorFlow?.backend || 'unknown'
        });
        
        // Perform inference timing tests
        logEvidence('PERFORMANCE', 'Starting inference timing validation...');
        const inferenceTimes = [];
        const iterations = 50;
        
        for (let i = 0; i < iterations; i++) {
            const result = await tfManager.testInference();
            if (result.success) {
                inferenceTimes.push(result.inferenceTime);
                if (i < 5) {
                    logEvidence('INFERENCE', `Inference ${i + 1} completed`, {
                        time: `${result.inferenceTime.toFixed(3)}ms`,
                        outputShape: result.outputShape,
                        outputSize: result.outputSize
                    });
                }
            }
        }
        
        // Calculate inference statistics
        const avgInference = inferenceTimes.reduce((a, b) => a + b, 0) / inferenceTimes.length;
        const minInference = Math.min(...inferenceTimes);
        const maxInference = Math.max(...inferenceTimes);
        const medianInference = inferenceTimes.sort((a, b) => a - b)[Math.floor(inferenceTimes.length / 2)];
        
        logEvidence('PERFORMANCE', 'Inference timing analysis complete', {
            iterations: iterations,
            averageTime: `${avgInference.toFixed(3)}ms`,
            minTime: `${minInference.toFixed(3)}ms`,
            maxTime: `${maxInference.toFixed(3)}ms`,
            medianTime: `${medianInference.toFixed(3)}ms`,
            targetClaim: '1-2ms',
            targetMet: avgInference <= 2 ? 'YES' : 'NO'
        });
        
        // Memory usage validation
        const memoryInfo = status.memory;
        logEvidence('MEMORY', 'Memory usage analysis', {
            currentUsage: `${memoryInfo.currentMemoryUsage?.toFixed(2) || 'N/A'}MB`,
            peakUsage: `${memoryInfo.peakMemoryUsage?.toFixed(2) || 'N/A'}MB`,
            tensorCount: memoryInfo.tensorCount || 'N/A',
            targetClaim: '<50MB',
            targetMet: (memoryInfo.currentMemoryUsage || 0) < 50 ? 'YES' : 'NO'
        });
        
        // Performance test (built-in)
        logEvidence('PERFORMANCE', 'Running built-in performance test...');
        await tfManager.performanceTest();
        
        const finalStatus = tfManager.getStatus();
        logEvidence('PERFORMANCE', 'Built-in performance test completed', {
            averageInferenceTime: `${finalStatus.performance.averageInferenceTime?.toFixed(3) || 'N/A'}ms`,
            totalInferences: finalStatus.performance.inferenceCount || 0,
            slowInferences: finalStatus.performance.slowInferences || 0
        });
        
        // Backend capability assessment
        const capabilities = tfManager.getCapabilities();
        logEvidence('CAPABILITIES', 'Backend capabilities assessed', {
            available: capabilities.available,
            backend: capabilities.backend,
            webglSupport: capabilities.webglSupport,
            performanceClass: capabilities.performanceClass,
            memoryClass: capabilities.memoryClass
        });
        
        // Final validation assessment
        const performanceTarget = avgInference <= 2;
        const memoryTarget = (memoryInfo.currentMemoryUsage || 0) < 50;
        const backendWorking = capabilities.available;
        const overallSuccess = performanceTarget && memoryTarget && backendWorking;
        
        logEvidence('VALIDATION', 'FINAL ASSESSMENT', {
            performanceTargetMet: performanceTarget ? 'YES' : 'NO',
            memoryTargetMet: memoryTarget ? 'YES' : 'NO',
            backendFunctional: backendWorking ? 'YES' : 'NO',
            overallValidation: overallSuccess ? 'PASS' : 'FAIL',
            claims: {
                webglBackend: status.backend === 'webgl' ? 'VERIFIED' : 'FAILED',
                cpuFallback: status.backend === 'cpu' ? 'FALLBACK_ACTIVE' : 'NOT_NEEDED',
                inferenceSpeed: `${avgInference.toFixed(3)}ms (claimed: 1-2ms)`,
                memoryUsage: `${memoryInfo.currentMemoryUsage?.toFixed(2) || 'N/A'}MB (claimed: <50MB)`
            }
        });
        
        // Cleanup
        tfManager.cleanup();
        logEvidence('CLEANUP', 'TensorFlow.js resources cleaned up');
        
        return {
            success: overallSuccess,
            evidence: evidenceLog,
            metrics: {
                backend: status.backend,
                avgInference,
                memoryUsage: memoryInfo.currentMemoryUsage || 0,
                performanceTarget,
                memoryTarget
            }
        };
        
    } catch (error) {
        logEvidence('ERROR', `Validation failed: ${error.message}`, {
            error: error.message,
            stack: error.stack
        });
        
        return {
            success: false,
            error: error.message,
            evidence: evidenceLog
        };
    }
}

// Run validation if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    validateTensorFlowJS().then(result => {
        console.log('\n================================================================');
        console.log('VALIDATION COMPLETE');
        console.log('================================================================');
        console.log(`Success: ${result.success}`);
        if (result.metrics) {
            console.log('Metrics:', JSON.stringify(result.metrics, null, 2));
        }
        process.exit(result.success ? 0 : 1);
    }).catch(error => {
        console.error('Validation error:', error);
        process.exit(1);
    });
}

export { validateTensorFlowJS };