/**
 * Manual test script to validate texture atlas fix
 * Run this in browser console after game loads
 */

// Wait for game to be available
function waitForGame() {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 50;
        
        const check = () => {
            if (window.game && window.game.textureAtlasManager) {
                resolve(window.game);
            } else if (attempts++ >= maxAttempts) {
                reject(new Error('Game not found after 25 seconds'));
            } else {
                setTimeout(check, 500);
            }
        };
        
        check();
    });
}

// Test texture atlas functionality
async function testTextureAtlas() {
    console.log('🧪 Starting Texture Atlas Validation...');
    
    try {
        // Wait for game
        const game = await waitForGame();
        console.log('✅ Game found');
        
        const manager = game.textureAtlasManager;
        console.log('✅ TextureAtlasManager found');
        
        // Test 1: Check sprite configs
        if (manager.spriteConfigs) {
            console.log('✅ Sprite configs loaded');
            console.log('📁 Available configs:', Object.keys(manager.spriteConfigs));
        } else {
            console.error('❌ No sprite configs');
            return false;
        }
        
        // Test 2: Test texture loading
        console.log('🖼️ Testing texture loading...');
        
        const testSprites = ['gdi-medium-tank', 'gdi-construction-yard', 'nod-recon-bike'];
        const results = [];
        
        for (const spriteKey of testSprites) {
            try {
                console.log(`Testing sprite: ${spriteKey}`);
                
                // Test creating animated sprite
                const sprite = manager.createAnimatedSprite(spriteKey, 'move');
                
                const result = {
                    spriteKey,
                    success: !!sprite,
                    type: sprite ? sprite.constructor.name : null,
                    hasTexture: sprite && !!sprite.texture,
                    textureValid: false
                };
                
                if (sprite && sprite.texture) {
                    // Test texture dimensions access (the main fix)
                    try {
                        let width, height;
                        const texture = sprite.texture;
                        
                        if (texture.baseTexture) {
                            // PIXI v6 style
                            width = texture.baseTexture.width;
                            height = texture.baseTexture.height;
                        } else if (texture.source) {
                            // PIXI v7+ style
                            width = texture.source.width || texture.source.pixelWidth || texture.width;
                            height = texture.source.height || texture.source.pixelHeight || texture.height;
                        } else {
                            // Fallback
                            width = texture.width;
                            height = texture.height;
                        }
                        
                        if (width && height && width > 0 && height > 0) {
                            result.textureValid = true;
                            result.dimensions = `${width}x${height}`;
                            console.log(`✅ ${spriteKey}: ${width}x${height}`);
                        } else {
                            console.warn(`⚠️ ${spriteKey}: Invalid dimensions ${width}x${height}`);
                        }
                        
                    } catch (dimError) {
                        console.error(`❌ ${spriteKey}: Dimension access failed:`, dimError);
                    }
                } else {
                    console.warn(`⚠️ ${spriteKey}: No texture found`);
                }
                
                results.push(result);
                
            } catch (error) {
                console.error(`❌ ${spriteKey} failed:`, error);
                results.push({
                    spriteKey,
                    success: false,
                    error: error.message
                });
            }
        }
        
        // Test 3: Memory usage
        try {
            const memoryUsage = manager.getMemoryUsage();
            console.log('📊 Memory usage:', memoryUsage);
        } catch (memError) {
            console.warn('⚠️ Memory usage check failed:', memError);
        }
        
        // Test 4: Check for error messages
        const hasWidthErrors = window.textureAtlasErrors || 
            (window.consoleErrors && window.consoleErrors.some(e => 
                e.includes('width') && e.includes('undefined')));
        
        // Summary
        console.log('\\n📋 TEST SUMMARY:');
        console.log('='.repeat(50));
        
        const successfulSprites = results.filter(r => r.success && r.textureValid).length;
        const totalSprites = results.length;
        
        console.log(`Sprites tested: ${totalSprites}`);
        console.log(`Successful: ${successfulSprites}`);
        console.log(`Failed: ${totalSprites - successfulSprites}`);
        console.log(`Width errors: ${hasWidthErrors ? 'YES' : 'NO'}`);
        
        results.forEach(result => {
            const status = result.success && result.textureValid ? '✅' : '❌';
            console.log(`${status} ${result.spriteKey}${result.dimensions ? ` (${result.dimensions})` : ''}`);
        });
        
        const allPassed = successfulSprites === totalSprites && !hasWidthErrors;
        
        console.log('='.repeat(50));
        if (allPassed) {
            console.log('🎉 ALL TESTS PASSED - TEXTURE ATLAS FIX SUCCESSFUL!');
        } else {
            console.log('⚠️ SOME TESTS FAILED - CHECK DETAILS ABOVE');
        }
        
        // Store results globally
        window.textureAtlasTestResults = {
            success: allPassed,
            results,
            hasWidthErrors,
            memoryUsage: manager.getMemoryUsage ? manager.getMemoryUsage() : null
        };
        
        return allPassed;
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        return false;
    }
}

// Auto-run if in browser
if (typeof window !== 'undefined') {
    window.testTextureAtlas = testTextureAtlas;
    
    // Run automatically after a delay
    setTimeout(() => {
        console.log('🚀 Auto-running texture atlas test...');
        testTextureAtlas();
    }, 3000);
}