/**
 * Sprite Rendering Test Suite
 * Tests the extracted sprites from MIX files and their integration with the game
 */

import puppeteer from 'puppeteer';

async function testSpriteRendering() {
    console.log('🎮 SPRITE RENDERING TEST SUITE');
    console.log('='.repeat(50));
    
    const browser = await puppeteer.launch({ 
        headless: false, // Show browser for visual inspection
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Collect console messages
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
        
        console.log('🌐 Loading application on port 3002...');
        await page.goto('http://localhost:3002', { waitUntil: 'domcontentloaded' });
        
        // Wait for game initialization
        console.log('⏳ Waiting for game initialization...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Test sprite loading and rendering
        const spriteTest = await page.evaluate(() => {
            const results = {
                gameLoaded: false,
                textureManagerLoaded: false,
                spritesLoaded: [],
                spriteRendering: [],
                errors: []
            };
            
            // Check basic game components
            results.gameLoaded = typeof window.game !== 'undefined';
            results.textureManagerLoaded = results.gameLoaded && typeof window.game.textureAtlasManager !== 'undefined';
            
            if (!results.textureManagerLoaded) {
                results.errors.push('TextureAtlasManager not available');
                return results;
            }
            
            const manager = window.game.textureAtlasManager;
            
            // Test extracted sprite categories
            const testCategories = {
                'GDI Units': ['gdi-medium-tank', 'gdi-mammoth-tank', 'gdi-apc', 'gdi-artillery', 'gdi-mlrs', 'gdi-orca'],
                'NOD Units': ['nod-light-tank', 'nod-flame-tank', 'nod-stealth-tank', 'nod-recon-bike', 'nod-buggy', 'nod-apache'],
                'GDI Structures': ['gdi-construction-yard', 'gdi-power-plant', 'gdi-barracks', 'gdi-refinery', 'gdi-war-factory'],
                'NOD Structures': ['nod-temple', 'nod-hand-of-nod', 'nod-airfield', 'nod-obelisk', 'nod-turret'],
                'Infantry': ['gdi-minigunner', 'gdi-grenadier', 'gdi-rocket-soldier', 'nod-flamethrower'],
                'Resources': ['tiberium-green-1', 'tiberium-green-2', 'tiberium-blue-1']
            };
            
            // Check if sprites are loaded
            for (const [category, sprites] of Object.entries(testCategories)) {
                for (const spriteId of sprites) {
                    try {
                        // Check if sprite config exists
                        const hasConfig = manager.getSpriteConfig(spriteId) !== null;
                        
                        if (hasConfig) {
                            results.spritesLoaded.push({
                                id: spriteId,
                                category: category,
                                loaded: true
                            });
                            
                            // Try to create and render sprite
                            try {
                                const sprite = manager.createAnimatedSprite(spriteId, 'idle') || 
                                             manager.createAnimatedSprite(spriteId, 'move');
                                
                                if (sprite) {
                                    // Get the PIXI app from the game's application
                                    const pixiApp = window.game.application?.app;
                                    if (!pixiApp) {
                                        throw new Error('PIXI app not available');
                                    }
                                    
                                    // Add to stage temporarily for rendering test
                                    pixiApp.stage.addChild(sprite);
                                    sprite.x = 100 + (results.spriteRendering.length * 50) % 500;
                                    sprite.y = 100 + Math.floor((results.spriteRendering.length * 50) / 500) * 50;
                                    
                                    // Check texture dimensions
                                    const texture = sprite.texture;
                                    const width = texture?.width || texture?.frame?.width;
                                    const height = texture?.height || texture?.frame?.height;
                                    
                                    results.spriteRendering.push({
                                        id: spriteId,
                                        rendered: true,
                                        width: width,
                                        height: height,
                                        visible: sprite.visible,
                                        position: { x: sprite.x, y: sprite.y }
                                    });
                                    
                                    // Remove after test
                                    setTimeout(() => {
                                        pixiApp.stage.removeChild(sprite);
                                    }, 10000); // Keep for 10 seconds for visual inspection
                                } else {
                                    results.spriteRendering.push({
                                        id: spriteId,
                                        rendered: false,
                                        error: 'Could not create sprite'
                                    });
                                }
                            } catch (renderErr) {
                                results.spriteRendering.push({
                                    id: spriteId,
                                    rendered: false,
                                    error: renderErr.message
                                });
                            }
                        } else {
                            results.spritesLoaded.push({
                                id: spriteId,
                                category: category,
                                loaded: false,
                                error: 'Config not found'
                            });
                        }
                    } catch (err) {
                        results.errors.push(`${spriteId}: ${err.message}`);
                    }
                }
            }
            
            // Get texture atlas stats
            results.atlasStats = {
                totalConfigs: Object.keys(manager.spriteConfigs || {}).length,
                loadedTextures: Object.keys(manager.loadedTextures || {}).length
            };
            
            return results;
        });
        
        // Display results
        console.log('\n📊 SPRITE RENDERING TEST RESULTS:');
        console.log('='.repeat(40));
        console.log('Game Loaded:', spriteTest.gameLoaded ? '✅' : '❌');
        console.log('Texture Manager:', spriteTest.textureManagerLoaded ? '✅' : '❌');
        
        if (spriteTest.atlasStats) {
            console.log('\n📈 Atlas Statistics:');
            console.log('Total Configs:', spriteTest.atlasStats.totalConfigs);
            console.log('Loaded Textures:', spriteTest.atlasStats.loadedTextures);
        }
        
        console.log('\n🎨 Sprite Loading Status:');
        const loadedCount = spriteTest.spritesLoaded.filter(s => s.loaded).length;
        const failedCount = spriteTest.spritesLoaded.filter(s => !s.loaded).length;
        console.log(`Loaded: ${loadedCount}/${spriteTest.spritesLoaded.length}`);
        
        if (failedCount > 0) {
            console.log('\n❌ Failed to load:');
            spriteTest.spritesLoaded.filter(s => !s.loaded).forEach(s => {
                console.log(`  - ${s.id}: ${s.error || 'Unknown error'}`);
            });
        }
        
        console.log('\n🖼️ Sprite Rendering Results:');
        const renderedCount = spriteTest.spriteRendering.filter(s => s.rendered).length;
        console.log(`Successfully Rendered: ${renderedCount}/${spriteTest.spriteRendering.length}`);
        
        // Group by success/failure
        const successful = spriteTest.spriteRendering.filter(s => s.rendered);
        const failed = spriteTest.spriteRendering.filter(s => !s.rendered);
        
        if (successful.length > 0) {
            console.log('\n✅ Successfully rendered sprites:');
            successful.forEach(s => {
                console.log(`  - ${s.id}: ${s.width}x${s.height} at (${s.position.x}, ${s.position.y})`);
            });
        }
        
        if (failed.length > 0) {
            console.log('\n❌ Failed to render:');
            failed.forEach(s => {
                console.log(`  - ${s.id}: ${s.error}`);
            });
        }
        
        // Error summary
        if (spriteTest.errors.length > 0) {
            console.log('\n🚨 Errors encountered:');
            spriteTest.errors.forEach(err => console.log(`  - ${err}`));
        }
        
        // Wait for visual inspection
        console.log('\n👁️ Browser window open for visual inspection...');
        console.log('Sprites are displayed on the canvas for 10 seconds.');
        console.log('Close browser or press Ctrl+C to end test.');
        
        await new Promise(resolve => setTimeout(resolve, 15000));
        
        // Final assessment
        const successRate = (renderedCount / spriteTest.spriteRendering.length) * 100;
        console.log('\n' + '='.repeat(50));
        console.log('🏆 FINAL ASSESSMENT:');
        console.log(`Success Rate: ${successRate.toFixed(1)}%`);
        console.log('Status:', successRate > 80 ? '✅ EXCELLENT' : successRate > 50 ? '⚠️ PARTIAL SUCCESS' : '❌ NEEDS WORK');
        
        return {
            success: successRate > 50,
            loadedCount,
            renderedCount,
            totalTested: spriteTest.spriteRendering.length
        };
        
    } finally {
        await browser.close();
    }
}

// Run the test
testSpriteRendering()
    .then(result => {
        console.log('\n✨ Test Complete!');
        console.log(`Sprites Loaded: ${result.loadedCount}`);
        console.log(`Sprites Rendered: ${result.renderedCount}/${result.totalTested}`);
        process.exit(result.success ? 0 : 1);
    })
    .catch(err => {
        console.error('❌ Test failed:', err.message);
        process.exit(1);
    });