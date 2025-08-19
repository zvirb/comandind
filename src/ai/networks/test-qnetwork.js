/**
 * Test script for QNetwork functionality
 * Verifies network initialization, prediction, and basic performance
 */

import * as tf from '@tensorflow/tfjs';
import { QNetwork } from './QNetwork.js';
import { NetworkConfig } from './NetworkConfig.js';

// Configure TensorFlow.js for testing
tf.setBackend('cpu'); // Use CPU for consistent testing

/**
 * Test basic network functionality
 */
async function testQNetwork() {
    console.log('🧪 Testing QNetwork functionality...\n');
    
    try {
        // 1. Test network initialization
        console.log('1️⃣ Testing network initialization...');
        const network = new QNetwork(NetworkConfig);
        const modelInfo = network.getModelInfo();
        
        console.log('✅ Network initialized successfully');
        console.log(`   Input size: ${modelInfo.architecture.inputSize}`);
        console.log(`   Hidden size: ${modelInfo.architecture.hiddenSize}`);
        console.log(`   Output size: ${modelInfo.architecture.outputSize}`);
        console.log(`   Total parameters: ${modelInfo.architecture.totalParams}`);
        console.log(`   Memory usage: ${modelInfo.performance.memoryUsage.toFixed(2)} MB\n`);
        
        // 2. Test prediction
        console.log('2️⃣ Testing Q-value prediction...');
        
        // Create sample state (36 dimensions as specified)
        const sampleState = Array.from({ length: 36 }, (_, i) => Math.random() * 2 - 1);
        const batchedStates = [sampleState, sampleState.map(x => x * 0.5)];
        
        const startTime = performance.now();
        const qValues = network.predict(batchedStates);
        const endTime = performance.now();
        
        console.log('✅ Prediction successful');
        console.log(`   Input shape: [${batchedStates.length}, ${batchedStates[0].length}]`);
        console.log(`   Output shape: [${qValues.shape}]`);
        console.log(`   Inference time: ${(endTime - startTime).toFixed(2)} ms`);
        
        // Print sample Q-values
        const qValuesData = await qValues.data();
        console.log(`   Sample Q-values: [${Array.from(qValuesData.slice(0, 8)).map(x => x.toFixed(3)).join(', ')}...]\n`);
        
        qValues.dispose();
        
        // 3. Test target network prediction
        console.log('3️⃣ Testing target network prediction...');
        const targetQValues = network.predictTarget(batchedStates);
        console.log('✅ Target prediction successful');
        console.log(`   Target output shape: [${targetQValues.shape}]\n`);
        targetQValues.dispose();
        
        // 4. Test training update (with mock data)
        console.log('4️⃣ Testing training update...');
        
        const mockBatch = {
            states: [
                Array.from({ length: 36 }, () => Math.random()),
                Array.from({ length: 36 }, () => Math.random())
            ],
            actions: [2, 5],
            rewards: [1.0, 0.5],
            nextStates: [
                Array.from({ length: 36 }, () => Math.random()),
                Array.from({ length: 36 }, () => Math.random())
            ],
            dones: [false, true]
        };
        
        const trainingResult = await network.update(mockBatch);
        console.log('✅ Training update successful');
        console.log(`   Loss: ${trainingResult.loss.toFixed(4)}`);
        console.log(`   Training step: ${trainingResult.step}`);
        console.log(`   Update time: ${trainingResult.inferenceTime.toFixed(2)} ms\n`);
        
        // 5. Test performance validation
        console.log('5️⃣ Testing performance validation...');
        const validation = network.validatePerformance();
        
        console.log('✅ Performance validation completed');
        console.log(`   Overall passed: ${validation.passed}`);
        console.log(`   Memory budget met: ${validation.details.memoryBudget} (${validation.metrics.memoryUsage.toFixed(2)}/${NetworkConfig.MAX_MEMORY_MB} MB)`);
        console.log(`   Inference speed met: ${validation.details.inferenceSpeed} (${network.inferenceTime.toFixed(2)}/${NetworkConfig.TARGET_INFERENCE_MS} ms)`);
        console.log(`   Architecture valid: ${validation.details.architecture}`);
        console.log(`   Compilation valid: ${validation.details.compilation}\n`);
        
        // 6. Test model save/load (simulated)
        console.log('6️⃣ Testing model persistence...');
        try {
            // Note: In Node.js environment, localStorage save might not work
            // This is primarily for browser environments
            console.log('⚠️  Model save/load testing skipped (requires browser localStorage)');
            console.log('   Save/load functionality available for browser environments\n');
        } catch (error) {
            console.log('⚠️  Model persistence test skipped:', error.message, '\n');
        }
        
        // 7. Memory cleanup test
        console.log('7️⃣ Testing memory cleanup...');
        const memoryBefore = tf.memory();
        network.dispose();
        const memoryAfter = tf.memory();
        
        console.log('✅ Memory cleanup completed');
        console.log(`   Tensors before: ${memoryBefore.numTensors}`);
        console.log(`   Tensors after: ${memoryAfter.numTensors}`);
        console.log(`   Memory freed: ${((memoryBefore.numBytes - memoryAfter.numBytes) / 1024 / 1024).toFixed(2)} MB\n`);
        
        console.log('🎉 All tests completed successfully!');
        
        return {
            success: true,
            results: {
                initialization: true,
                prediction: true,
                targetPrediction: true,
                training: true,
                validation: validation.passed,
                cleanup: true
            }
        };
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Run performance benchmark
 */
async function benchmarkPerformance() {
    console.log('\n🏃 Running performance benchmark...\n');
    
    const network = new QNetwork(NetworkConfig);
    const iterations = 100;
    
    // Benchmark prediction speed
    const states = Array.from({ length: 32 }, () => 
        Array.from({ length: 36 }, () => Math.random() * 2 - 1)
    );
    
    const times = [];
    
    for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        const qValues = network.predict(states);
        qValues.dispose();
        times.push(performance.now() - start);
    }
    
    const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    
    console.log(`📊 Prediction Performance (${iterations} iterations):`);
    console.log(`   Average: ${avgTime.toFixed(2)} ms`);
    console.log(`   Minimum: ${minTime.toFixed(2)} ms`);
    console.log(`   Maximum: ${maxTime.toFixed(2)} ms`);
    console.log(`   Target: ${NetworkConfig.TARGET_INFERENCE_MS} ms`);
    console.log(`   Performance: ${avgTime <= NetworkConfig.TARGET_INFERENCE_MS ? '✅ PASS' : '❌ FAIL'}\n`);
    
    network.dispose();
    
    return {
        averageTime: avgTime,
        targetMet: avgTime <= NetworkConfig.TARGET_INFERENCE_MS
    };
}

// Run tests if this file is executed directly
if (typeof window === 'undefined' && import.meta.url === `file://${process.argv[1]}`) {
    testQNetwork()
        .then(result => {
            if (result.success) {
                return benchmarkPerformance();
            } else {
                console.error('Basic tests failed, skipping benchmark');
                process.exit(1);
            }
        })
        .then(benchmark => {
            console.log('🏁 All tests and benchmarks completed!');
            process.exit(benchmark.targetMet ? 0 : 1);
        })
        .catch(error => {
            console.error('Test execution failed:', error);
            process.exit(1);
        });
}

export { testQNetwork, benchmarkPerformance };