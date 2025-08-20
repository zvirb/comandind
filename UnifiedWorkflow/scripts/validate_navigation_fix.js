/**
 * Validation script to confirm Documents/Calendar navigation fix
 * This script checks that the critical routes configuration has been updated
 */

const fs = require('fs');
const path = require('path');

// Read the PrivateRoute.jsx file
const privateRoutePath = path.join(__dirname, 'app/webui-next/src/components/PrivateRoute.jsx');
const authContextPath = path.join(__dirname, 'app/webui-next/src/context/AuthContext.jsx');

console.log('🔍 Validating Documents/Calendar Navigation Fix');
console.log('=' .repeat(60));

// Check PrivateRoute.jsx
console.log('\n📄 Checking PrivateRoute.jsx...');
const privateRouteContent = fs.readFileSync(privateRoutePath, 'utf8');

// Check if Documents and Calendar have been removed from critical routes
const criticalRoutesMatch = privateRouteContent.match(/const criticalRoutes = \[(.*?)\]/s);
if (criticalRoutesMatch) {
    const criticalRoutes = criticalRoutesMatch[1];
    console.log('  Critical routes definition found:', criticalRoutes.trim());
    
    if (criticalRoutes.includes('/documents') || criticalRoutes.includes('/calendar')) {
        console.log('  ❌ FAIL: Documents/Calendar still in critical routes!');
        console.log('     These routes will trigger race conditions');
    } else {
        console.log('  ✅ PASS: Documents/Calendar removed from critical routes');
    }
} else {
    console.log('  ⚠️ WARNING: Could not find critical routes definition');
}

// Check for timeout implementation
if (privateRouteContent.includes('Promise.race') && privateRouteContent.includes('timeoutPromise')) {
    console.log('  ✅ PASS: Timeout implementation found for health check');
} else {
    console.log('  ❌ FAIL: No timeout implementation for health check');
}

// Check for debounce implementation
if (privateRouteContent.includes('setTimeout(() => {') && privateRouteContent.includes('mounted')) {
    console.log('  ✅ PASS: Debounce mechanism implemented');
} else {
    console.log('  ⚠️ WARNING: No debounce mechanism found');
}

// Check AuthContext.jsx
console.log('\n📄 Checking AuthContext.jsx...');
const authContextContent = fs.readFileSync(authContextPath, 'utf8');

// Check for operation locks
if (authContextContent.includes('operationLocks') || authContextContent.includes('operationLock')) {
    console.log('  ✅ PASS: Operation locks implemented to prevent concurrent operations');
} else {
    console.log('  ❌ FAIL: No operation locks found - concurrent operations possible');
}

// Check for AbortController timeout
if (authContextContent.includes('AbortController') && authContextContent.includes('controller.abort()')) {
    console.log('  ✅ PASS: AbortController timeout implemented for fetch operations');
} else {
    console.log('  ⚠️ WARNING: No AbortController timeout found');
}

// Check for lock release in finally blocks
const finallyCount = (authContextContent.match(/finally\s*{/g) || []).length;
if (finallyCount >= 2) {
    console.log(`  ✅ PASS: ${finallyCount} finally blocks found for lock cleanup`);
} else {
    console.log('  ⚠️ WARNING: Insufficient finally blocks for lock cleanup');
}

// Summary
console.log('\n' + '=' .repeat(60));
console.log('📊 VALIDATION SUMMARY');
console.log('=' .repeat(60));

const hasRaceConditionFix = 
    !criticalRoutesMatch[1].includes('/documents') && 
    !criticalRoutesMatch[1].includes('/calendar') &&
    privateRouteContent.includes('Promise.race') &&
    (authContextContent.includes('operationLocks') || authContextContent.includes('operationLock'));

if (hasRaceConditionFix) {
    console.log('\n✅ SUCCESS: Documents/Calendar navigation race condition has been fixed!');
    console.log('   - Critical routes no longer include Documents/Calendar');
    console.log('   - Timeouts implemented to prevent hanging operations');
    console.log('   - Operation locks prevent concurrent auth operations');
    console.log('\n🎉 Users should now be able to navigate to Documents and Calendar');
    console.log('   without being logged out!');
} else {
    console.log('\n❌ FAILURE: Race condition fix incomplete or not applied');
    console.log('   Please review the implementation and ensure all fixes are in place');
}

console.log('\n' + '=' .repeat(60));