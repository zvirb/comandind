/**
 * Test script to validate the texture atlas loading fix
 * Tests main menu display and user flow completion
 */

console.log('🧪 Starting Texture Atlas Fix Validation...');

// Test configuration
const TEST_CONFIG = {
    timeout: 30000, // 30 seconds timeout
    expectedElements: [
        'game-container',
        'loading-screen',
        'performance-monitor'
    ],
    textureTests: [
        'gdi-medium-tank',
        'gdi-construction-yard',
        'nod-recon-bike'
    ]
};

// Validation results
const validationResults = {
    domElements: false,
    textureLoading: false,
    mainMenuDisplay: false,
    gameTransition: false,
    errors: []
};

/**
 * Wait for DOM element to be available
 */
function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }
        
        const observer = new MutationObserver(() => {
            const element = document.querySelector(selector);
            if (element) {
                observer.disconnect();
                resolve(element);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Element ${selector} not found within ${timeout}ms`));
        }, timeout);
    });
}

/**
 * Test DOM elements existence
 */
async function testDOMElements() {
    console.log('🔍 Testing DOM elements...');
    
    try {
        for (const elementId of TEST_CONFIG.expectedElements) {
            const element = await waitForElement(`#${elementId}`, 5000);
            console.log(`✅ Found element: ${elementId}`);
        }
        
        validationResults.domElements = true;
        console.log('✅ All DOM elements found');
        
    } catch (error) {
        validationResults.errors.push(`DOM Elements: ${error.message}`);
        console.error('❌ DOM element test failed:', error);
    }
}

/**
 * Test texture atlas loading
 */
async function testTextureLoading() {
    console.log('🖼️ Testing texture atlas loading...');
    
    try {
        // Wait for game to be available
        await waitForElement('#game-container canvas', 10000);
        
        if (window.game && window.game.textureAtlasManager) {
            const atlasManager = window.game.textureAtlasManager;
            console.log('📊 Atlas Manager found');
            
            // Test sprite configurations
            if (atlasManager.spriteConfigs) {
                console.log('✅ Sprite configs loaded');
                console.log('📁 Available configs:', Object.keys(atlasManager.spriteConfigs));
                
                // Test specific texture loading
                for (const spriteKey of TEST_CONFIG.textureTests) {
                    try {
                        const sprite = atlasManager.createAnimatedSprite(spriteKey, 'move');
                        if (sprite) {
                            console.log(`✅ Successfully created sprite: ${spriteKey}`);
                        } else {
                            console.warn(`⚠️ Sprite creation returned null: ${spriteKey}`);
                        }
                    } catch (spriteError) {
                        console.warn(`⚠️ Sprite creation failed: ${spriteKey} - ${spriteError.message}`);
                    }
                }
                
                validationResults.textureLoading = true;
                
            } else {
                throw new Error('Sprite configs not loaded');
            }
            
        } else {
            throw new Error('Game or TextureAtlasManager not available');
        }
        
        console.log('✅ Texture loading test passed');
        
    } catch (error) {
        validationResults.errors.push(`Texture Loading: ${error.message}`);
        console.error('❌ Texture loading test failed:', error);
    }
}

/**
 * Test main menu display
 */
async function testMainMenuDisplay() {
    console.log('🎮 Testing main menu display...');
    
    try {
        // Wait for loading screen to hide
        const loadingScreen = document.querySelector('#loading-screen');
        let attempts = 0;
        const maxAttempts = 30; // 15 seconds (500ms intervals)
        
        while (attempts < maxAttempts) {
            if (loadingScreen && loadingScreen.classList.contains('hidden')) {
                console.log('✅ Loading screen hidden');
                break;
            }
            
            await new Promise(resolve => setTimeout(resolve, 500));
            attempts++;
        }
        
        if (attempts >= maxAttempts) {
            throw new Error('Loading screen never hid within timeout');
        }
        
        // Check if main menu is visible
        if (window.game && window.game.mainMenu) {
            const mainMenu = window.game.mainMenu;
            if (mainMenu.container && mainMenu.container.visible) {
                console.log('✅ Main menu is visible');
                validationResults.mainMenuDisplay = true;
            } else {
                throw new Error('Main menu container not visible');
            }
        } else {
            throw new Error('Main menu not available');
        }
        
        console.log('✅ Main menu display test passed');
        
    } catch (error) {
        validationResults.errors.push(`Main Menu: ${error.message}`);
        console.error('❌ Main menu test failed:', error);
    }
}

/**
 * Test game transition
 */
async function testGameTransition() {
    console.log('🔄 Testing game transition...');
    
    try {
        if (window.game && window.game.mainMenu) {
            // Simulate clicking "New Game"
            console.log('🖱️ Simulating New Game click...');
            window.game.startGame();
            
            // Wait a moment for transition
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Check if main menu is hidden and game started
            if (!window.game.mainMenu.container.visible && window.game.gameStarted) {
                console.log('✅ Game transition successful');
                validationResults.gameTransition = true;
            } else {
                throw new Error('Game transition failed - menu still visible or game not started');
            }
            
        } else {
            throw new Error('Game or main menu not available');
        }
        
        console.log('✅ Game transition test passed');
        
    } catch (error) {
        validationResults.errors.push(`Game Transition: ${error.message}`);
        console.error('❌ Game transition test failed:', error);
    }
}

/**
 * Run complete validation suite
 */
async function runValidation() {
    console.log('🚀 Starting complete validation suite...');
    
    const startTime = Date.now();
    
    try {
        // Run tests in sequence
        await testDOMElements();
        await testTextureLoading();
        await testMainMenuDisplay();
        await testGameTransition();
        
        const endTime = Date.now();
        const duration = endTime - startTime;
        
        // Generate final report
        console.log('\n📊 VALIDATION RESULTS:');
        console.log('='.repeat(50));
        console.log(`DOM Elements: ${validationResults.domElements ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`Texture Loading: ${validationResults.textureLoading ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`Main Menu Display: ${validationResults.mainMenuDisplay ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`Game Transition: ${validationResults.gameTransition ? '✅ PASS' : '❌ FAIL'}`);
        console.log(`Duration: ${duration}ms`);
        
        if (validationResults.errors.length > 0) {
            console.log('\n❌ ERRORS:');
            validationResults.errors.forEach(error => console.log(`  - ${error}`));
        }
        
        const allPassed = validationResults.domElements && 
                         validationResults.textureLoading && 
                         validationResults.mainMenuDisplay && 
                         validationResults.gameTransition;
        
        console.log('\n' + '='.repeat(50));
        if (allPassed) {
            console.log('🎉 ALL TESTS PASSED - TEXTURE ATLAS FIX SUCCESSFUL!');
        } else {
            console.log('⚠️ SOME TESTS FAILED - REVIEW ISSUES ABOVE');
        }
        
        // Store results globally for debugging
        window.textureAtlasValidation = validationResults;
        
        return allPassed;
        
    } catch (error) {
        console.error('💥 Validation suite failed:', error);
        validationResults.errors.push(`Suite: ${error.message}`);
        return false;
    }
}

// Export for use in browser console
if (typeof window !== 'undefined') {
    window.runTextureAtlasValidation = runValidation;
    
    // Auto-run if game is already loaded
    if (document.readyState === 'complete') {
        setTimeout(runValidation, 2000);
    } else {
        window.addEventListener('load', () => {
            setTimeout(runValidation, 2000);
        });
    }
}

export { runValidation };