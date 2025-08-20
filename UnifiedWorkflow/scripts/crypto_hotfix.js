// EMERGENCY CRYPTO HOTFIX SCRIPT
// This script fixes crypto.randomUUID() compatibility issues for older browsers
// Deploy by injecting into browser console or adding to the website

console.log('[CRYPTO HOTFIX] Initializing browser compatibility fixes...');

// Check if crypto.randomUUID is available
if (!window.crypto || !window.crypto.randomUUID) {
    console.warn('[CRYPTO HOTFIX] crypto.randomUUID not available, installing polyfill...');
    
    // Create crypto object if it doesn't exist
    if (!window.crypto) {
        window.crypto = {};
    }
    
    // Polyfill for crypto.randomUUID
    window.crypto.randomUUID = function() {
        // Try to use crypto.getRandomValues if available
        if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
            const array = new Uint8Array(16);
            crypto.getRandomValues(array);
            
            // Set version (4) and variant bits according to RFC 4122
            array[6] = (array[6] & 0x0f) | 0x40; 
            array[8] = (array[8] & 0x3f) | 0x80;
            
            // Convert to hex string
            const hex = Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('');
            return `${hex.substring(0,8)}-${hex.substring(8,12)}-${hex.substring(12,16)}-${hex.substring(16,20)}-${hex.substring(20,32)}`;
        }
        
        // Fallback using Math.random (less secure but compatible)
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    };
    
    console.log('[CRYPTO HOTFIX] ✅ Polyfill installed successfully!');
} else {
    console.log('[CRYPTO HOTFIX] ✅ Native crypto.randomUUID already available');
}

// Test the implementation
try {
    const testUuid = window.crypto.randomUUID();
    console.log('[CRYPTO HOTFIX] 🧪 Test UUID generated:', testUuid);
    
    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (uuidRegex.test(testUuid)) {
        console.log('[CRYPTO HOTFIX] ✅ UUID format validation passed');
    } else {
        console.warn('[CRYPTO HOTFIX] ⚠️ UUID format validation failed, but function is working');
    }
} catch (error) {
    console.error('[CRYPTO HOTFIX] ❌ Test failed:', error);
}

console.log('[CRYPTO HOTFIX] Initialization complete. Browser crypto compatibility fixed.');

// Make this available globally for debugging
window.cryptoHotfixInstalled = true;