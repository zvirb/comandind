/**
 * Sprite Animation Validation Test
 * Tests the animation systems for the extracted sprites
 */

import puppeteer from 'puppeteer';

async function testSpriteAnimations() {
    console.log('🎭 SPRITE ANIMATION TEST SUITE');
    console.log('='.repeat(50));
    
    const browser = await puppeteer.launch({ 
        headless: false, // Show browser for visual inspection
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        defaultViewport: { width: 1280, height: 800 }
    });
    
    try {
        const page = await browser.newPage();
        
        // Collect console messages
        const consoleLogs = [];
        page.on('console', msg => {
            consoleLogs.push({
                type: msg.type(),
                text: msg.text()
            });
        });
        
        console.log('🌐 Loading application...');
        await page.goto('http://localhost:3002', { waitUntil: 'domcontentloaded' });
        
        // Wait for game initialization
        console.log('⏳ Waiting for game initialization...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Test animations
        const animationTest = await page.evaluate(() => {
            const results = {
                animationsStarted: [],
                animationTypes: {},
                directionalSprites: [],
                staticSprites: [],
                errors: []
            };
            
            if (!window.game?.textureAtlasManager) {
                results.errors.push('TextureAtlasManager not available');
                return results;
            }
            
            const manager = window.game.textureAtlasManager;
            const pixiApp = window.game.application?.app;
            
            if (!pixiApp) {
                results.errors.push('PIXI app not available');
                return results;
            }
            
            // Test sprites with different animation types
            const testSprites = [
                // Units with directional movement
                { id: 'gdi-medium-tank', type: 'unit', expectedAnim: 'move' },
                { id: 'nod-recon-bike', type: 'unit', expectedAnim: 'move' },
                { id: 'gdi-orca', type: 'air', expectedAnim: 'move' },
                
                // Structures with idle/active animations
                { id: 'gdi-construction-yard', type: 'structure', expectedAnim: 'idle' },
                { id: 'gdi-power-plant', type: 'structure', expectedAnim: 'idle' },
                { id: 'nod-obelisk', type: 'structure', expectedAnim: 'idle' },
                
                // Infantry with directional animations
                { id: 'gdi-minigunner', type: 'infantry', expectedAnim: 'move' },
                
                // Resources with idle animations
                { id: 'tiberium-green-1', type: 'resource', expectedAnim: 'idle' }
            ];
            
            let yPosition = 50;
            
            for (const testSprite of testSprites) {
                try {
                    const config = manager.getSpriteConfig(testSprite.id);
                    if (!config) {
                        results.errors.push(`No config for ${testSprite.id}`);
                        continue;
                    }
                    
                    // Check if it's a directional sprite
                    const isDirectional = config.directions && config.directions > 1;
                    
                    if (isDirectional) {
                        results.directionalSprites.push({
                            id: testSprite.id,
                            directions: config.directions
                        });
                    } else {
                        results.staticSprites.push(testSprite.id);
                    }
                    
                    // Try to create animated sprite
                    const sprite = manager.createAnimatedSprite(testSprite.id, testSprite.expectedAnim);
                    
                    if (sprite) {
                        // Position sprite on screen
                        sprite.x = 100 + (results.animationsStarted.length * 120);
                        sprite.y = yPosition;
                        
                        if (sprite.x > 1000) {
                            sprite.x = 100;
                            yPosition += 100;
                            sprite.y = yPosition;
                        }
                        
                        // Add to stage
                        pixiApp.stage.addChild(sprite);
                        
                        // Check animation properties
                        const hasAnimation = sprite.play && typeof sprite.play === 'function';
                        const animationFrames = sprite.totalFrames || sprite.textures?.length || 1;
                        
                        if (hasAnimation) {
                            // Start animation
                            sprite.play();
                            sprite.animationSpeed = 0.1; // Slow down for visibility
                            
                            results.animationsStarted.push({
                                id: testSprite.id,
                                type: testSprite.type,
                                animation: testSprite.expectedAnim,
                                frames: animationFrames,
                                playing: sprite.playing || false,
                                position: { x: sprite.x, y: sprite.y }
                            });
                        } else {
                            results.animationsStarted.push({
                                id: testSprite.id,
                                type: testSprite.type,
                                animation: 'static',
                                frames: 1,
                                playing: false,
                                position: { x: sprite.x, y: sprite.y }
                            });
                        }
                        
                        // Track animation types
                        if (!results.animationTypes[testSprite.type]) {
                            results.animationTypes[testSprite.type] = [];
                        }
                        results.animationTypes[testSprite.type].push(testSprite.id);
                        
                        // Add label using window.PIXI
                        if (window.PIXI && window.PIXI.Text) {
                            const label = new window.PIXI.Text(testSprite.id, {
                                fontSize: 12,
                                fill: 0xFFFFFF
                            });
                            label.x = sprite.x;
                            label.y = sprite.y - 20;
                            pixiApp.stage.addChild(label);
                        }
                        
                    } else {
                        results.errors.push(`Could not create sprite for ${testSprite.id}`);
                    }
                    
                } catch (err) {
                    results.errors.push(`${testSprite.id}: ${err.message}`);
                }
            }
            
            // Test switching animations for structures
            setTimeout(() => {
                console.log('Switching structure animations to active state...');
                for (const anim of results.animationsStarted) {
                    if (anim.type === 'structure') {
                        try {
                            const activeSprite = manager.createAnimatedSprite(anim.id, 'active');
                            if (activeSprite && activeSprite.play) {
                                activeSprite.play();
                            }
                        } catch (err) {
                            console.error(`Failed to switch ${anim.id} to active: ${err.message}`);
                        }
                    }
                }
            }, 5000);
            
            return results;
        });
        
        // Display results
        console.log('\n📊 ANIMATION TEST RESULTS:');
        console.log('='.repeat(40));
        
        console.log('\n🎬 Animations Started:');
        console.log(`Total: ${animationTest.animationsStarted.length}`);
        
        for (const anim of animationTest.animationsStarted) {
            const status = anim.playing ? '▶️ Playing' : '⏸️ Static';
            console.log(`  ${status} ${anim.id} (${anim.type}): ${anim.frames} frames at (${anim.position.x}, ${anim.position.y})`);
        }
        
        console.log('\n🧭 Directional Sprites:');
        if (animationTest.directionalSprites.length > 0) {
            for (const dir of animationTest.directionalSprites) {
                console.log(`  - ${dir.id}: ${dir.directions} directions`);
            }
        } else {
            console.log('  None found');
        }
        
        console.log('\n📍 Static Sprites:');
        if (animationTest.staticSprites.length > 0) {
            for (const staticId of animationTest.staticSprites) {
                console.log(`  - ${staticId}`);
            }
        } else {
            console.log('  None found');
        }
        
        console.log('\n📂 Animation Types:');
        for (const [type, sprites] of Object.entries(animationTest.animationTypes)) {
            console.log(`  ${type}: ${sprites.length} sprites`);
        }
        
        if (animationTest.errors.length > 0) {
            console.log('\n🚨 Errors:');
            for (const error of animationTest.errors) {
                console.log(`  - ${error}`);
            }
        }
        
        // Visual inspection time
        console.log('\n👁️ Visual inspection window open...');
        console.log('Animations are running. Structure animations will switch to active state after 5 seconds.');
        console.log('Close browser or press Ctrl+C to end test.');
        
        await new Promise(resolve => setTimeout(resolve, 20000));
        
        // Final assessment
        const animatedCount = animationTest.animationsStarted.filter(a => a.playing).length;
        const successRate = (animatedCount / animationTest.animationsStarted.length) * 100;
        
        console.log('\n' + '='.repeat(50));
        console.log('🏆 FINAL ASSESSMENT:');
        console.log(`Animated Sprites: ${animatedCount}/${animationTest.animationsStarted.length}`);
        console.log(`Success Rate: ${successRate.toFixed(1)}%`);
        console.log('Animation System:', successRate > 50 ? '✅ FUNCTIONAL' : '⚠️ NEEDS WORK');
        
        return {
            success: successRate > 50,
            animated: animatedCount,
            total: animationTest.animationsStarted.length,
            directional: animationTest.directionalSprites.length
        };
        
    } finally {
        await browser.close();
    }
}

// Run the test
testSpriteAnimations()
    .then(result => {
        console.log('\n✨ Animation Test Complete!');
        console.log(`Animated: ${result.animated}/${result.total}`);
        console.log(`Directional Sprites: ${result.directional}`);
        process.exit(result.success ? 0 : 1);
    })
    .catch(err => {
        console.error('❌ Test failed:', err.message);
        process.exit(1);
    });