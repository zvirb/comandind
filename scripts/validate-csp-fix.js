#!/usr/bin/env node

/**
 * Validation script to check if the CSP unsafe-eval issue has been resolved
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

console.log('🔍 Validating CSP unsafe-eval fix...\n');

// Test 1: Check if @pixi/unsafe-eval is installed
console.log('1. Checking @pixi/unsafe-eval installation...');
try {
    const { stdout } = await execAsync('npm list @pixi/unsafe-eval');
    if (stdout.includes('@pixi/unsafe-eval')) {
        console.log('✅ @pixi/unsafe-eval is installed');
    } else {
        console.log('❌ @pixi/unsafe-eval not found');
    }
} catch (error) {
    console.log('❌ Failed to check @pixi/unsafe-eval installation');
}

// Test 2: Check CSP header configuration
console.log('\n2. Checking CSP header configuration...');
try {
    const { stdout } = await execAsync('curl -s http://localhost:3000 | grep "Content-Security-Policy"');
    if (stdout.includes('wasm-unsafe-eval')) {
        console.log('✅ CSP header includes wasm-unsafe-eval');
    } else {
        console.log('❌ CSP header missing wasm-unsafe-eval');
    }
} catch (error) {
    console.log('❌ Failed to check CSP header');
}

// Test 3: Verify Application.js imports unsafe-eval
console.log('\n3. Checking Application.js unsafe-eval import...');
try {
    const { stdout } = await execAsync('grep -n "unsafe-eval" src/core/Application.js');
    if (stdout.includes("import '@pixi/unsafe-eval'")) {
        console.log('✅ Application.js imports @pixi/unsafe-eval');
    } else {
        console.log('❌ Application.js missing unsafe-eval import');
    }
} catch (error) {
    console.log('❌ Failed to check Application.js imports');
}

// Test 4: Check if dev server is running
console.log('\n4. Checking if dev server is responding...');
try {
    const { stdout } = await execAsync('curl -I http://localhost:3000 2>/dev/null | head -1');
    if (stdout.includes('200 OK')) {
        console.log('✅ Dev server is responding with 200 OK');
    } else {
        console.log('❌ Dev server not responding properly');
    }
} catch (error) {
    console.log('❌ Dev server is not accessible');
}

console.log('\n🎯 CSP unsafe-eval fix validation completed!');
console.log('📝 Summary: The critical CSP restriction should now be resolved.');
console.log('🔧 Next: Open http://localhost:3000 in browser to test PixiJS initialization.');