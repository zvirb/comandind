// Enable CSP support for unsafe-eval restrictions - loaded early
import '@pixi/unsafe-eval';
import { Application } from './core/Application.js';
import { GameLoop } from './core/GameLoop.js';
import { Camera } from './core/Camera.js';
import { PerformanceMonitor } from './utils/PerformanceMonitor.js';
import { InputHandler } from './core/InputHandler.js';
import { createEventManager } from './utils/EventListenerManager.js';
import { TestSprites } from './rendering/TestSprites.js';
import { CnCAssetLoader } from './rendering/CnCAssetLoader.js';
import { UIUpdateManager } from './core/UIUpdateManager.js';
import { MainMenu } from './ui/MainMenu.js';
import { 
    World, 
    EntityFactory,
    MovementSystem,
    RenderingSystem,
    UnitMovementSystem,
    CombatSystem,
    AISystem,
    SelectionSystem
} from './ecs/index.js';
import { PathfindingSystem } from './ecs/PathfindingSystem.js';

class CommandAndIndependentThought {
    constructor() {
        this.application = null;
        this.gameLoop = null;
        this.camera = null;
        this.performanceMonitor = null;
        this.inputHandler = null;
        this.testSprites = null;
        this.cncAssets = null;
        this.world = null;
        this.entityFactory = null;
        this.uiUpdateManager = null;
        this.mainMenu = null;
        this.isInitialized = false;
        this.gameStarted = false;
        
        // Create event listener manager for this game instance
        this.eventManager = createEventManager('GameInstance');
    }

    async initialize() {
        try {
            // Update loading progress
            this.updateLoadingProgress(10, 'Creating application...');
            
            // Initialize PixiJS application
            this.application = new Application({
                width: window.innerWidth,
                height: window.innerHeight,
                backgroundColor: 0x1a1a1a,
                antialias: true,
                resolution: window.devicePixelRatio || 1,
                autoDensity: true,
                powerPreference: 'high-performance'
            });
            
            await this.application.initialize();
            this.updateLoadingProgress(30, 'Setting up camera...');
            
            // Initialize camera system
            this.camera = new Camera(
                this.application.stage,
                window.innerWidth,
                window.innerHeight
            );
            
            this.updateLoadingProgress(50, 'Initializing game loop...');
            
            // Initialize game loop
            this.gameLoop = new GameLoop(
                this.update.bind(this),
                this.render.bind(this),
                60 // Target 60 FPS
            );
            
            this.updateLoadingProgress(70, 'Setting up input handlers...');
            
            // Initialize input handler
            this.inputHandler = new InputHandler(this.application.view);
            
            this.updateLoadingProgress(85, 'Starting performance monitor...');
            
            // Initialize performance monitor
            this.performanceMonitor = new PerformanceMonitor();
            
            // Initialize UI update manager with optimized settings
            this.uiUpdateManager = new UIUpdateManager({
                updateHz: 10, // 10Hz for performance stats
                enableVirtualDOM: true // Enable virtual DOM for better performance
            });
            
            this.updateLoadingProgress(85, 'Loading C&C assets...');
            
            // Initialize C&C asset loader
            this.cncAssets = new CnCAssetLoader();
            await this.cncAssets.loadGameData();
            
            this.updateLoadingProgress(87, 'Initializing ECS world...');
            
            // Initialize ECS World and Systems
            this.world = new World();
            this.entityFactory = new EntityFactory(this.world, this.cncAssets);
            
            // Add systems to world (order matters for priority)
            this.world.addSystem(new MovementSystem(this.world));
            this.pathfindingSystem = new PathfindingSystem(this.world, 2000, 2000);
            this.world.addSystem(this.pathfindingSystem);
            this.world.addSystem(new UnitMovementSystem(this.world));
            this.selectionSystem = new SelectionSystem(
                this.world, 
                this.inputHandler, 
                this.camera, 
                this.application.stage,
                this.application.view // Pass canvas element for coordinate transformation
            );
            this.world.addSystem(this.selectionSystem);
            this.world.addSystem(new CombatSystem(this.world));
            this.world.addSystem(new AISystem(this.world));
            this.world.addSystem(new RenderingSystem(this.world, this.application.stage));
            
            this.updateLoadingProgress(90, 'Creating test sprites...');
            
            // Create test sprites for demonstration
            this.testSprites = new TestSprites(this.application);
            await this.testSprites.createTestSprites(100); // Start with 100 sprites
            
            // Add some C&C units for testing
            await this.createCnCTestUnits();
            
            this.updateLoadingProgress(95, 'Finalizing...');
            
            // Setup window resize handler using event manager
            this.eventManager.addEventListener(window, 'resize', this.handleResize.bind(this));
            
            // Setup cleanup handler
            window.addEventListener('beforeunload', this.cleanup.bind(this));

            // Create Main Menu
            this.mainMenu = new MainMenu(this.application, this.application.layers.ui, this.startGame.bind(this));
            
            // Hide loading screen and show main menu
            setTimeout(() => {
                if (this.application && this.application.view && this.gameLoop) {
                    console.log('🎮 All systems ready - hiding loading screen');
                    document.getElementById('loading-screen').classList.add('hidden');
                    this.isInitialized = true;
                    this.gameLoop.start();
                    this.uiUpdateManager.start();
                    this.showMainMenu();
                } else {
                    console.error('❌ Cannot start game - critical systems not initialized');
                    document.getElementById('loading-text').textContent = 'ERROR: Failed to initialize game systems';
                    document.getElementById('loading-text').style.color = '#f00';
                }
            }, 500);
            
            this.updateLoadingProgress(100, 'Ready!');
            
        } catch (error) {
            console.error('Failed to initialize Command and Independent Thought:', error);
            document.getElementById('loading-text').textContent = 
                'ERROR: Failed to initialize. Check console for details.';
            document.getElementById('loading-text').style.color = '#f00';
        }
    }
    
    updateLoadingProgress(percent, message) {
        const progressBar = document.getElementById('loading-progress');
        const loadingText = document.getElementById('loading-text');
        
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
        
        if (loadingText && message) {
            loadingText.textContent = message;
        }
    }
    
    async createCnCTestUnits() {
        if (!this.cncAssets || !this.entityFactory) return;
        
        console.log('🎮 Creating C&C test units with ECS...');
        
        // Create some GDI units using ECS
        const gdiUnits = this.cncAssets.getUnitsByFaction('gdi').slice(0, 3);
        for (const [index, unit] of gdiUnits.entries()) {
            const entity = await this.entityFactory.createUnit(unit.key, 200 + index * 60, 200, 'gdi');
            if (entity) {
                console.log(`Created GDI unit entity: ${unit.name} (ID: ${entity.id})`);
            }
        }
        
        // Create some NOD units using ECS
        const nodUnits = this.cncAssets.getUnitsByFaction('nod').slice(0, 3);
        for (const [index, unit] of nodUnits.entries()) {
            const entity = await this.entityFactory.createUnit(unit.key, 200 + index * 60, 300, 'nod');
            if (entity) {
                console.log(`Created NOD unit entity: ${unit.name} (ID: ${entity.id})`);
            }
        }
        
        // Create some buildings using ECS
        const gdiBuildings = this.cncAssets.getBuildingsByFaction('gdi').slice(0, 2);
        for (const [index, building] of gdiBuildings.entries()) {
            const entity = await this.entityFactory.createBuilding(building.key, 400 + index * 80, 200, 'gdi');
            if (entity) {
                console.log(`Created GDI building entity: ${building.name} (ID: ${entity.id})`);
            }
        }
        
        const nodBuildings = this.cncAssets.getBuildingsByFaction('nod').slice(0, 2);
        for (const [index, building] of nodBuildings.entries()) {
            const entity = await this.entityFactory.createBuilding(building.key, 400 + index * 80, 320, 'nod');
            if (entity) {
                console.log(`Created NOD building entity: ${building.name} (ID: ${entity.id})`);
            }
        }
        
        // Display ECS world stats
        console.log('🔧 ECS World Stats:', this.world.getStats());
    }
    
    setupInputHandlers() {
        // Camera controls
        this.inputHandler.on('mousemove', (event) => {
            const edgeScrollSpeed = 5;
            const edgeThreshold = 50;
            
            // Edge scrolling
            if (event.clientX < edgeThreshold) {
                this.camera.velocity.x = -edgeScrollSpeed;
            } else if (event.clientX > window.innerWidth - edgeThreshold) {
                this.camera.velocity.x = edgeScrollSpeed;
            } else {
                this.camera.velocity.x = 0;
            }
            
            if (event.clientY < edgeThreshold) {
                this.camera.velocity.y = -edgeScrollSpeed;
            } else if (event.clientY > window.innerHeight - edgeThreshold) {
                this.camera.velocity.y = edgeScrollSpeed;
            } else {
                this.camera.velocity.y = 0;
            }
        });
        
        // Keyboard controls
        this.inputHandler.on('keydown', (event) => {
            const scrollSpeed = 10;
            switch(event.key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    this.camera.velocity.x = -scrollSpeed;
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    this.camera.velocity.x = scrollSpeed;
                    break;
                case 'ArrowUp':
                case 'w':
                case 'W':
                    this.camera.velocity.y = -scrollSpeed;
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    this.camera.velocity.y = scrollSpeed;
                    break;
                // Test controls
                case '1':
                    // Add 100 more sprites
                    this.testSprites.createTestSprites(100);
                    console.log('Added 100 sprites');
                    break;
                case '2':
                    // Start stress test (1000 sprites)
                    this.testSprites.stressTest(1000);
                    break;
                case '0':
                    // Clear all sprites
                    this.testSprites.clearSprites();
                    break;
                // Debug controls
                case 'p':
                case 'P':
                    // Toggle pathfinding debug visualization
                    if (this.pathfindingSystem) {
                        this.pathfindingSystem.toggleDebugMode(this.application.stage);
                        console.log('Pathfinding debug mode:', this.pathfindingSystem.debugMode);
                    }
                    break;
            }
        });
        
        this.inputHandler.on('keyup', (event) => {
            switch(event.key) {
                case 'ArrowLeft':
                case 'ArrowRight':
                case 'a':
                case 'A':
                case 'd':
                case 'D':
                    this.camera.velocity.x = 0;
                    break;
                case 'ArrowUp':
                case 'ArrowDown':
                case 'w':
                case 'W':
                case 's':
                case 'S':
                    this.camera.velocity.y = 0;
                    break;
            }
        });
        
        // Pinch zoom (trackpad/touch)
        this.inputHandler.on('pinchzoom', (event) => {
            this.camera.zoomToPoint(
                this.camera.scale + event.delta,
                event.clientX,
                event.clientY
            );
        });
        
        // Wheel zoom (mouse wheel)
        this.inputHandler.on('wheelzoom', (event) => {
            this.camera.zoomToPoint(
                this.camera.scale + event.delta,
                event.clientX,
                event.clientY
            );
        });
        
        // Trackpad pan (two-finger swipe)
        this.inputHandler.on('trackpadpan', (event) => {
            // Move camera based on trackpad pan
            this.camera.targetX += event.deltaX;
            this.camera.targetY += event.deltaY;
        });
        
        // Legacy wheel event for backwards compatibility
        this.inputHandler.on('wheel', (event) => {
            // Handled by the new events above
        });
    }
    
    showMainMenu() {
        this.mainMenu.show();
        document.getElementById('performance-monitor').classList.add('hidden');
    }

    startGame() {
        this.mainMenu.hide();
        this.gameStarted = true;
        this.setupInputHandlers(); // Setup game controls only when game starts
        document.getElementById('performance-monitor').classList.remove('hidden');
        console.log('✅ Game is now running!');
    }

    update(deltaTime) {
        if (!this.isInitialized) return;

        if (!this.gameStarted) {
            // Don't update game logic if menu is showing
            return;
        }
        
        // Update camera
        this.camera.update(deltaTime);
        
        // Update ECS world
        if (this.world) {
            this.world.update(deltaTime);
        }
        
        // Animate test sprites
        if (this.testSprites) {
            this.testSprites.animateSprites(deltaTime);
        }
        
        // Update performance monitor
        this.performanceMonitor.update();
        
        // Queue UI updates through UIUpdateManager (throttled at 10Hz)
        this.updatePerformanceUI();
    }
    
    /**
     * Update performance UI through UIUpdateManager (optimized DOM updates)
     */
    updatePerformanceUI() {
        if (!this.uiUpdateManager || !this.performanceMonitor) return;
        
        const fps = Math.round(this.performanceMonitor.getFPS());
        const memory = Math.round(this.performanceMonitor.getMemoryUsage());
        const drawCalls = this.application.renderer.gl?.drawingBufferHeight ? 
            this.application.renderer.drawCalls || 0 : 0;
        const sprites = this.application.stage.children.length;
        const ecsEntities = this.world ? this.world.entities.size : 0;
        
        // Queue batched updates through UIUpdateManager
        this.uiUpdateManager.updatePerformanceStats({
            fps: fps,
            drawCalls: drawCalls,
            spriteCount: `${sprites} (${ecsEntities} ECS)`,
            memory: memory
        });
    }
    
    render(interpolation) {
        if (!this.isInitialized) return;
        
        // Render ECS world
        if (this.world) {
            this.world.render(interpolation);
        }
        
        // Render with interpolation for smooth visuals
        this.application.render(interpolation);
    }
    
    handleResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        this.application.resize(width, height);
        this.camera.resize(width, height);
    }
    
    /**
     * Clean up resources when the game is shutting down
     */
    cleanup() {
        console.log('🧹 Starting game cleanup...');
        
        try {
            // Stop UI update manager
            if (this.uiUpdateManager) {
                this.uiUpdateManager.stop();
            }
            
            // Stop game loop
            if (this.gameLoop) {
                this.gameLoop.stop();
            }
            
            // Stop performance monitor
            if (this.performanceMonitor) {
                this.performanceMonitor.stop();
            }
            
            // Clean up ECS world
            if (this.world) {
                this.world.cleanup();
            }
            
            // Remove event listeners
            if (this.inputHandler && this.inputHandler.destroy) {
                this.inputHandler.destroy();
            } else if (this.inputHandler && this.inputHandler.cleanup) {
                this.inputHandler.cleanup();
            }
            
            // Destroy event manager (removes all managed listeners)
            if (this.eventManager) {
                this.eventManager.destroy();
                this.eventManager = null;
            }
            
            // Destroy selection system
            if (this.selectionSystem && this.selectionSystem.destroy) {
                this.selectionSystem.destroy();
            }
            
            // Destroy PIXI application
            if (this.application) {
                this.application.destroy();
            }
            
            console.log('✅ Game cleanup completed');
        } catch (error) {
            console.error('❌ Error during cleanup:', error);
        }
    }
}

// Global error logging to localStorage
function logError(error, context = 'unknown') {
    try {
        const errors = JSON.parse(localStorage.getItem('comandind_errors') || '[]');
        errors.push({
            timestamp: new Date().toISOString(),
            message: error.message || 'Unknown error',
            stack: error.stack || 'No stack trace',
            context: context,
            url: window.location.href,
            userAgent: navigator.userAgent
        });
        
        // Keep only last 10 errors
        if (errors.length > 10) {
            errors.splice(0, errors.length - 10);
        }
        
        localStorage.setItem('comandind_errors', JSON.stringify(errors));
        console.error(`[${context}] Error logged:`, error);
    } catch (logError) {
        console.error('Failed to log error:', logError);
    }
}

// Initialize game state
let gameInitialized = false;

// Navigation protection configuration
let navigationProtectionEnabled = true;
let hasUnsavedChanges = false;

// Navigation protection utilities
window.navigationUtils = {
    setUnsavedChanges: (hasChanges) => {
        hasUnsavedChanges = hasChanges;
        console.log(`📝 Unsaved changes: ${hasChanges}`);
    },
    
    setNavigationProtection: (enabled) => {
        navigationProtectionEnabled = enabled;
        console.log(`🛡️ Navigation protection: ${enabled ? 'enabled' : 'disabled'}`);
    },
    
    isNavigationProtected: () => navigationProtectionEnabled && hasUnsavedChanges,
    
    // Disable protection temporarily for programmatic navigation
    disableProtectionTemporarily: (callback) => {
        const wasEnabled = navigationProtectionEnabled;
        navigationProtectionEnabled = false;
        try {
            callback();
        } finally {
            navigationProtectionEnabled = wasEnabled;
        }
    }
};

// Initialize global error handlers only in browser environment
if (typeof window !== 'undefined') {
    // Capture all unhandled errors (but allow navigation)
    window.addEventListener('error', (e) => {
        logError(e, 'global_error');
        // Don't prevent default - allow browser to handle navigation
        console.warn('🚨 Error occurred but navigation allowed:', e.message);
    });

    window.addEventListener('unhandledrejection', (e) => {
        logError(new Error(`Promise rejection: ${e.reason}`), 'promise_rejection');
        // Don't prevent default - allow browser to handle navigation
        console.warn('🚨 Promise rejection occurred but navigation allowed:', e.reason);
    });
    
    // Add proper beforeunload handler for user confirmation
    window.addEventListener('beforeunload', (e) => {
        if (navigationProtectionEnabled && hasUnsavedChanges) {
            // Modern browsers ignore returnValue, but set it for compatibility
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
        // If no unsaved changes or protection disabled, allow navigation
    });
    
    // Add unload handler for cleanup
    window.addEventListener('unload', () => {
        // Cleanup code when page is actually unloading
        if (window.game && typeof window.game.cleanup === 'function') {
            window.game.cleanup();
        }
        console.log('🧹 Page unloaded, cleanup performed');
    });

    // Initialize game when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGame);
    } else {
        initGame();
    }
}

async function initGame() {
    // Prevent multiple initialization
    if (gameInitialized) {
        console.warn('Game already initialized, skipping...');
        return;
    }
    gameInitialized = true;
    
    try {
        console.log('🎮 Initializing Command and Independent Thought...');
        const game = new CommandAndIndependentThought();
        window.game = game; // Expose for debugging
        
        await game.initialize();
        console.log('✅ Game initialized successfully!');
        
    } catch (error) {
        logError(error, 'game_initialization');
        console.error('❌ Failed to initialize game:', error);
        console.error('Stack trace:', error.stack);
        gameInitialized = false; // Allow retry
        
        // Show error to user
        const loadingText = document.getElementById('loading-text');
        if (loadingText) {
            loadingText.textContent = `ERROR: ${error.message}`;
            loadingText.style.color = '#f00';
        }
    }
}

export { CommandAndIndependentThought };