/**
 * Direct Texture Atlas Validation Test
 * Tests the critical path that was fixed to prevent width/height undefined errors
 */

import puppeteer from 'puppeteer';

async function validateTextureAtlasFix() {
    console.log('🧪 TEXTURE ATLAS FIX VALIDATION');
    console.log('='.repeat(50));
    
    const browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Collect console messages for error detection
        const consoleLogs = [];
        const errors = [];
        
        page.on('console', msg => {
            consoleLogs.push({
                type: msg.type(),
                text: msg.text(),
                timestamp: new Date().toISOString()
            });
        });
        
        page.on('pageerror', err => {
            errors.push({
                message: err.message,
                stack: err.stack
            });
        });
        
        console.log('🌐 Loading application...');
        await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
        
        // Wait for game to initialize
        console.log('⏳ Waiting for game initialization...');
        await new Promise(resolve => setTimeout(resolve, 15000));
        
        // Test texture atlas functionality
        const validation = await page.evaluate(() => {
            // Check if the critical components exist
            const hasGame = typeof window.game !== 'undefined';
            const hasTextureAtlasManager = hasGame && typeof window.game.textureAtlasManager !== 'undefined';
            const hasPIXI = typeof window.PIXI !== 'undefined';
            const hasApp = typeof window.app !== 'undefined';
            
            let textureTest = { success: false, details: 'Not tested' };
            
            if (hasGame && hasTextureAtlasManager) {
                try {
                    const manager = window.game.textureAtlasManager;
                    const spriteConfigs = manager.spriteConfigs || {};
                    const loadedTextures = manager.loadedTextures || {};
                    
                    // Test texture creation - this is where the width/height undefined error was occurring
                    let testResults = [];
                    const testSprites = ['gdi-medium-tank', 'gdi-construction-yard', 'nod-recon-bike'];
                    
                    for (const spriteId of testSprites) {
                        try {
                            const sprite = manager.createAnimatedSprite(spriteId, 'move');
                            if (sprite && sprite.texture) {
                                const width = sprite.texture.width;
                                const height = sprite.texture.height;
                                testResults.push({
                                    sprite: spriteId,
                                    success: true,
                                    width: width,
                                    height: height,
                                    hasUndefinedDimensions: width === undefined || height === undefined
                                });
                            } else {
                                testResults.push({
                                    sprite: spriteId,
                                    success: false,
                                    error: 'No sprite or texture created'
                                });
                            }
                        } catch (err) {
                            testResults.push({
                                sprite: spriteId,
                                success: false,
                                error: err.message
                            });
                        }
                    }
                    
                    textureTest = {
                        success: true,
                        spriteConfigCount: Object.keys(spriteConfigs).length,
                        loadedTextureCount: Object.keys(loadedTextures).length,
                        testResults: testResults,
                        undefinedDimensionErrors: testResults.filter(r => r.hasUndefinedDimensions).length
                    };
                } catch (err) {
                    textureTest = {
                        success: false,
                        error: err.message
                    };
                }
            }
            
            return {
                hasGame,
                hasTextureAtlasManager,
                hasPIXI,
                hasApp,
                pixiVersion: hasPIXI ? window.PIXI.VERSION : 'N/A',
                textureTest
            };
        });
        
        // Analyze results
        console.log('\n📊 VALIDATION RESULTS:');
        console.log('='.repeat(30));
        console.log('Game Instance:', validation.hasGame ? '✅' : '❌');
        console.log('TextureAtlasManager:', validation.hasTextureAtlasManager ? '✅' : '❌');
        console.log('PIXI.js:', validation.hasPIXI ? '✅' : '❌', `(${validation.pixiVersion})`);
        console.log('PIXI App:', validation.hasApp ? '✅' : '❌');
        
        console.log('\n🖼️ TEXTURE ATLAS TEST RESULTS:');
        if (validation.textureTest.success) {
            console.log('Sprite Configs Loaded:', validation.textureTest.spriteConfigCount);
            console.log('Textures Loaded:', validation.textureTest.loadedTextureCount);
            console.log('Undefined Dimension Errors:', validation.textureTest.undefinedDimensionErrors);
            
            console.log('\n📋 Individual Sprite Tests:');
            validation.textureTest.testResults.forEach(result => {
                if (result.success) {
                    console.log(`✅ ${result.sprite}: ${result.width}x${result.height}${result.hasUndefinedDimensions ? ' ⚠️ UNDEFINED DIMENSIONS' : ''}`);
                } else {
                    console.log(`❌ ${result.sprite}: ${result.error}`);
                }
            });
        } else {
            console.log('❌ Texture test failed:', validation.textureTest.error || validation.textureTest.details);
        }
        
        // Error analysis
        console.log('\n🚨 ERROR ANALYSIS:');
        const criticalErrors = errors.filter(e => 
            e.message.includes('width') || 
            e.message.includes('height') || 
            e.message.includes('undefined') ||
            e.message.includes('texture')
        );
        
        if (criticalErrors.length === 0) {
            console.log('✅ No critical texture/dimension errors detected');
        } else {
            console.log('❌ Critical errors found:');
            criticalErrors.forEach(err => console.log('  -', err.message));
        }
        
        const widthHeightErrors = consoleLogs.filter(log => 
            log.text.includes('width') && log.text.includes('undefined') ||
            log.text.includes('height') && log.text.includes('undefined')
        );
        
        console.log('\n📊 TEXTURE ATLAS FIX ASSESSMENT:');
        console.log('='.repeat(40));
        console.log('Width/Height Undefined Errors:', widthHeightErrors.length);
        console.log('Texture Creation Success:', validation.textureTest.success ? 'YES' : 'NO');
        console.log('Undefined Dimension Count:', validation.textureTest.success ? validation.textureTest.undefinedDimensionErrors : 'N/A');
        console.log('Fix Status:', 
            validation.textureTest.success && 
            validation.textureTest.undefinedDimensionErrors === 0 && 
            widthHeightErrors.length === 0 ? 
            '✅ SUCCESSFUL' : '❌ NEEDS ATTENTION'
        );
        
        return {
            fixSuccessful: validation.textureTest.success && 
                          validation.textureTest.undefinedDimensionErrors === 0 && 
                          widthHeightErrors.length === 0,
            validation,
            errors: errors.length,
            criticalErrors: criticalErrors.length
        };
        
    } finally {
        await browser.close();
    }
}

// Run validation
validateTextureAtlasFix()
    .then(result => {
        console.log('\n' + '='.repeat(50));
        console.log('🏆 FINAL ASSESSMENT:');
        console.log('Texture Atlas Fix:', result.fixSuccessful ? '✅ SUCCESSFUL' : '❌ FAILED');
        console.log('Production Ready:', result.fixSuccessful ? 'YES' : 'NO');
        process.exit(result.fixSuccessful ? 0 : 1);
    })
    .catch(err => {
        console.error('❌ Validation failed:', err.message);
        process.exit(1);
    });