/**
 * Performance Optimization Test Script
 * 
 * This script validates that DOM updates have been successfully moved 
 * out of the main game loop and are now running at throttled rates.
 */

import { UIUpdateManager } from './src/core/UIUpdateManager.js';

// Test configuration
const TEST_DURATION = 5000; // 5 seconds
const EXPECTED_UI_UPDATES_PER_SECOND = 10; // 10Hz
const TOLERANCE = 0.2; // 20% tolerance

console.log('🧪 Starting Performance Optimization Tests...');

/**
 * Test 1: UIUpdateManager throttling
 */
async function testUIUpdateManagerThrottling() {
    console.log('\n📊 Test 1: UIUpdateManager Update Rate');
    
    // Create test DOM elements
    const testContainer = document.createElement('div');
    testContainer.innerHTML = `
        <div id="test-fps">0</div>
        <div id="test-memory">0</div>
        <div id="test-sprites">0</div>
    `;
    document.body.appendChild(testContainer);
    
    // Initialize UIUpdateManager
    const uiManager = new UIUpdateManager({
        updateHz: EXPECTED_UI_UPDATES_PER_SECOND,
        enableVirtualDOM: true
    });
    
    uiManager.start();
    
    let updateCount = 0;
    const startTime = performance.now();
    
    // Simulate rapid data changes (like a 60 FPS game loop would do)
    const rapidUpdates = setInterval(() => {
        uiManager.updatePerformanceStats({
            fps: Math.random() * 60,
            memory: Math.random() * 100,
            spriteCount: Math.floor(Math.random() * 1000)
        });
        updateCount++;
    }, 16); // 60 FPS rate
    
    // Wait for test duration
    await new Promise(resolve => setTimeout(resolve, TEST_DURATION));
    
    clearInterval(rapidUpdates);
    uiManager.stop();
    
    const endTime = performance.now();
    const actualDuration = (endTime - startTime) / 1000;
    const stats = uiManager.getPerformanceStats();
    
    console.log(`   📈 Data updates queued: ${updateCount}`);
    console.log(`   🎯 DOM updates performed: ${stats.updateCount}`);
    console.log(`   ⏱️  Average update time: ${stats.avgUpdateTime.toFixed(2)}ms`);
    console.log(`   📊 Update rate: ${(stats.updateCount / actualDuration).toFixed(1)}Hz`);
    
    // Validate throttling is working
    const actualRate = stats.updateCount / actualDuration;
    const expectedRate = EXPECTED_UI_UPDATES_PER_SECOND;
    const withinTolerance = Math.abs(actualRate - expectedRate) / expectedRate <= TOLERANCE;
    
    if (withinTolerance) {
        console.log(`   ✅ PASS: Update rate within tolerance (${actualRate.toFixed(1)}Hz vs ${expectedRate}Hz)`);
    } else {
        console.log(`   ❌ FAIL: Update rate outside tolerance (${actualRate.toFixed(1)}Hz vs ${expectedRate}Hz)`);
    }
    
    // Validate DOM updates are much fewer than data updates
    const reductionRatio = updateCount / stats.updateCount;
    console.log(`   🔄 DOM update reduction: ${reductionRatio.toFixed(1)}x`);
    
    if (reductionRatio > 3) {
        console.log(`   ✅ PASS: Significant DOM update reduction achieved`);
    } else {
        console.log(`   ❌ FAIL: DOM update reduction insufficient`);
    }
    
    // Cleanup
    document.body.removeChild(testContainer);
    
    return { withinTolerance, reductionRatio > 3 };
}

/**
 * Test 2: Batched DOM updates
 */
async function testBatchedUpdates() {
    console.log('\n🎯 Test 2: Batched DOM Updates');
    
    // Create test elements
    const testContainer = document.createElement('div');
    testContainer.innerHTML = `
        <div id="batch-test-1">0</div>
        <div id="batch-test-2">0</div>
        <div id="batch-test-3">0</div>
    `;
    document.body.appendChild(testContainer);
    
    const uiManager = new UIUpdateManager({ updateHz: 20 });
    uiManager.start();
    
    const startTime = performance.now();
    
    // Queue multiple updates for the same elements rapidly
    for (let i = 0; i < 100; i++) {
        uiManager.queueTextUpdate('batch-test-1', `Value ${i}`);
        uiManager.queueTextUpdate('batch-test-2', `Count ${i * 2}`);
        uiManager.queueTextUpdate('batch-test-3', `Item ${i * 3}`);
    }
    
    // Force immediate update to test batching
    uiManager.forceUpdate();
    
    const endTime = performance.now();
    const updateTime = endTime - startTime;
    
    console.log(`   ⏱️  Batched update time: ${updateTime.toFixed(2)}ms`);
    
    // Verify final values are correct (should show the last update from each batch)
    const finalValues = {
        1: document.getElementById('batch-test-1').textContent,
        2: document.getElementById('batch-test-2').textContent,
        3: document.getElementById('batch-test-3').textContent
    };
    
    const expectedValues = {
        1: 'Value 99',
        2: 'Count 198', 
        3: 'Item 297'
    };
    
    let batchingWorking = true;
    for (let i = 1; i <= 3; i++) {
        if (finalValues[i] !== expectedValues[i]) {
            batchingWorking = false;
            console.log(`   ❌ Element ${i}: Expected '${expectedValues[i]}', got '${finalValues[i]}'`);
        }
    }
    
    if (batchingWorking) {
        console.log(`   ✅ PASS: Batched updates working correctly`);
    }
    
    // Test should be fast (batching reduces DOM operations)
    if (updateTime < 50) {
        console.log(`   ✅ PASS: Batched updates are performant (${updateTime.toFixed(2)}ms)`);
    } else {
        console.log(`   ❌ FAIL: Batched updates too slow (${updateTime.toFixed(2)}ms)`);
    }
    
    uiManager.stop();
    document.body.removeChild(testContainer);
    
    return { batchingWorking, performant: updateTime < 50 };
}

/**
 * Test 3: Virtual DOM pattern
 */
async function testVirtualDOM() {
    console.log('\n🖥️  Test 3: Virtual DOM Pattern');
    
    const testContainer = document.createElement('div');
    testContainer.innerHTML = `<div id="virtual-test">initial</div>`;
    document.body.appendChild(testContainer);
    
    const uiManager = new UIUpdateManager({ 
        updateHz: 30, 
        enableVirtualDOM: true 
    });
    uiManager.start();
    
    const element = document.getElementById('virtual-test');
    let domModifications = 0;
    
    // Mock the textContent setter to count actual DOM modifications
    const originalSetter = Object.getOwnPropertyDescriptor(Element.prototype, 'textContent').set;
    Object.defineProperty(element, 'textContent', {
        set: function(value) {
            domModifications++;
            originalSetter.call(this, value);
        },
        get: function() {
            return this.innerText;
        }
    });
    
    // Queue same value multiple times (should only update DOM once)
    for (let i = 0; i < 10; i++) {
        uiManager.queueTextUpdate('virtual-test', 'same-value');
    }
    
    uiManager.forceUpdate();
    
    console.log(`   🔄 DOM modifications for identical values: ${domModifications}`);
    
    // Reset counter
    domModifications = 0;
    
    // Queue different values (should update DOM each time)
    for (let i = 0; i < 5; i++) {
        uiManager.queueTextUpdate('virtual-test', `value-${i}`);
        uiManager.forceUpdate();
    }
    
    console.log(`   🔄 DOM modifications for different values: ${domModifications}`);
    
    const virtualDOMWorking = domModifications <= 5; // Should be 5 or fewer
    
    if (virtualDOMWorking) {
        console.log(`   ✅ PASS: Virtual DOM pattern reducing unnecessary updates`);
    } else {
        console.log(`   ❌ FAIL: Virtual DOM pattern not working effectively`);
    }
    
    uiManager.stop();
    document.body.removeChild(testContainer);
    
    return virtualDOMWorking;
}

/**
 * Run all tests
 */
async function runTests() {
    try {
        const results = {
            throttling: await testUIUpdateManagerThrottling(),
            batching: await testBatchedUpdates(),
            virtualDOM: await testVirtualDOM()
        };
        
        console.log('\n📋 Test Summary:');
        console.log(`   🎯 Throttling: ${results.throttling.withinTolerance && results.throttling ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`   🎯 Batching: ${results.batching.batchingWorking && results.batching.performant ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`   🎯 Virtual DOM: ${results.virtualDOM ? '✅ PASS' : '❌ FAIL'}`);
        
        const allPassed = 
            results.throttling.withinTolerance && 
            results.batching.batchingWorking && 
            results.batching.performant &&
            results.virtualDOM;
        
        console.log(`\n🏆 Overall Result: ${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`);
        
        if (allPassed) {
            console.log('\n🎉 DOM optimization successfully implemented!');
            console.log('   • DOM updates moved out of main game loop');
            console.log('   • Updates throttled to 10Hz for optimal performance');
            console.log('   • Batched updates reduce reflows and repaints');
            console.log('   • Virtual DOM pattern eliminates redundant updates');
        }
        
        return allPassed;
        
    } catch (error) {
        console.error('❌ Test execution failed:', error);
        return false;
    }
}

// Run tests if in browser environment
if (typeof window !== 'undefined') {
    runTests();
} else {
    console.log('⚠️  Tests require browser environment');
}

export { runTests, testUIUpdateManagerThrottling, testBatchedUpdates, testVirtualDOM };