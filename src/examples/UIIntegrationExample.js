/**
 * UIIntegrationExample - Complete UI integration demonstration
 * 
 * This file demonstrates how to integrate the new UI systems into the existing
 * RTS game framework. Shows proper initialization order, event wiring, and
 * performance optimization techniques.
 * 
 * Integration points:
 * - Game loop integration
 * - ECS system coordination
 * - Input handling pipeline
 * - Performance monitoring
 * - Resource management
 */

import { Application } from '../core/Application.js';
import { GameLoop } from '../core/GameLoop.js';
import { InputHandler } from '../core/InputHandler.js';
import { Camera } from '../core/Camera.js';
import { World } from '../ecs/World.js';
import { UIManager } from '../ui/UIManager.js';
import { SelectionSystem } from '../ecs/SelectionSystem.js';
import { SpriteBatcher } from '../rendering/SpriteBatcher.js';

export class UIIntegratedGame {
    constructor(options = {}) {
        this.options = options;
        
        // Core systems
        this.app = null;
        this.gameLoop = null;
        this.inputHandler = null;
        this.camera = null;
        this.world = null;
        this.selectionSystem = null;
        this.spriteBatcher = null;
        
        // UI System
        this.uiManager = null;
        
        // Game state
        this.isInitialized = false;
        this.isPaused = false;
        
        // Performance tracking
        this.stats = {
            frameCount: 0,
            lastStatsUpdate: 0,
            avgFrameTime: 0
        };
        
        this.init();
    }
    
    /**
     * Initialize the complete game with UI integration
     */
    async init() {
        console.log('🎮 Initializing UI-integrated RTS game...');
        
        try {
            // Step 1: Initialize core application
            await this.initializeApplication();
            
            // Step 2: Initialize core game systems
            await this.initializeCoreSystems();
            
            // Step 3: Initialize ECS world and systems
            await this.initializeECS();
            
            // Step 4: Initialize UI Manager (this handles all UI subsystems)
            await this.initializeUIManager();
            
            // Step 5: Wire up system integrations
            this.setupSystemIntegrations();
            
            // Step 6: Create initial game content
            this.createInitialContent();
            
            // Step 7: Start the game loop
            this.startGameLoop();
            
            this.isInitialized = true;
            
            console.log('✅ UI-integrated game initialization complete!');
            
            // Show initialization complete message
            this.showInitializationComplete();
            
        } catch (error) {
            console.error('❌ Game initialization failed:', error);
            throw error;
        }
    }
    
    /**
     * Initialize PIXI application
     */
    async initializeApplication() {
        console.log('🖼️  Initializing PIXI Application...');
        
        this.app = new Application({
            width: 1280,
            height: 720,
            backgroundColor: 0x1a1a2e,
            antialias: true,
            powerPreference: 'high-performance'
        });
        
        await this.app.initialize();
        
        // Add sprite batcher for performance
        this.spriteBatcher = new SpriteBatcher(this.app.renderer, 1000);
        this.app.spriteBatcher = this.spriteBatcher; // Make available to UI systems
        
        console.log('✅ PIXI Application ready');
    }
    
    /**
     * Initialize core game systems
     */
    async initializeCoreSystems() {
        console.log('⚙️  Initializing core systems...');
        
        // Initialize input handler
        this.inputHandler = new InputHandler(this.app.view, {
            enableTouchEvents: true,
            enableMouseEvents: true,
            enableKeyboardEvents: true
        });
        
        // Initialize camera
        this.camera = new Camera(this.app, {
            worldWidth: 3200,
            worldHeight: 3200,
            viewWidth: 1280,
            viewHeight: 720,
            enableZoom: true,
            enablePan: true
        });
        
        // Initialize game loop
        this.gameLoop = new GameLoop({
            targetFPS: 60,
            enableInterpolation: true,
            enableDebugStats: true
        });
        
        console.log('✅ Core systems ready');
    }
    
    /**
     * Initialize ECS world and systems
     */
    async initializeECS() {
        console.log('🌍 Initializing ECS World...');
        
        // Create ECS world
        this.world = new World();
        
        // Initialize selection system (integrated with old approach)
        this.selectionSystem = new SelectionSystem(
            this.world,
            this.inputHandler,
            this.camera,
            this.app.stage
        );
        
        // Add systems to world
        this.world.addSystem(this.selectionSystem);
        
        // Note: Other game systems (pathfinding, combat, etc.) would be added here
        
        console.log('✅ ECS World ready');
    }
    
    /**
     * Initialize UI Manager (coordinates all UI systems)
     */
    async initializeUIManager() {
        console.log('🎛️  Initializing UI Manager...');
        
        // Detect if running on mobile for optimization
        const isMobile = this.detectMobile();
        
        this.uiManager = new UIManager(this.app, this.world, this.camera, this.inputHandler, {
            enablePerformanceMonitoring: true,
            enableDebugInterface: this.options.enableDebug || false,
            isMobile: isMobile,
            enableAccessibilityMode: false, // Can be enabled based on user preference
            targetFPS: 60,
            effectQuality: this.options.effectQuality || (isMobile ? 'medium' : 'high'),
            enableAnimations: this.options.enableAnimations !== false,
            enableParticles: this.options.enableParticles !== false
        });
        
        await this.uiManager.init();
        
        console.log('✅ UI Manager ready');
    }
    
    /**
     * Setup integrations between systems
     */
    setupSystemIntegrations() {
        console.log('🔗 Setting up system integrations...');
        
        // Integrate old selection system with new UI systems
        this.integrateSelectionSystem();
        
        // Setup game event handlers
        this.setupGameEventHandlers();
        
        // Setup UI event handlers
        this.setupUIEventHandlers();
        
        // Setup resource tracking
        this.setupResourceTracking();
        
        console.log('✅ System integrations complete');
    }
    
    /**
     * Integrate existing selection system with new UI systems
     */
    integrateSelectionSystem() {
        // Override selection system methods to use new UI systems
        const originalSelectEntity = this.selectionSystem.selectEntity.bind(this.selectionSystem);
        const originalDeselectEntity = this.selectionSystem.deselectEntity.bind(this.selectionSystem);
        const originalClearSelection = this.selectionSystem.clearSelection.bind(this.selectionSystem);

        // Enhance selectEntity to use new selection renderer
        this.selectionSystem.selectEntity = (entity) => {
            const result = originalSelectEntity(entity);

            // Use new selection renderer
            const transform = entity.getComponent('TransformComponent');
            const health = entity.getComponent('HealthComponent');

            if (transform) {
                this.uiManager.systems.selectionRenderer?.showSelection(entity.id, transform, health);
                this.uiManager.systems.visualFeedback?.showSelectionPulse(entity);
            }

            return result;
        };

        // Enhance deselectEntity
        this.selectionSystem.deselectEntity = (entity) => {
            const result = originalDeselectEntity(entity);

            // Hide selection visuals
            this.uiManager.systems.selectionRenderer?.hideSelection(entity.id);

            return result;
        };

        // Enhance clearSelection
        this.selectionSystem.clearSelection = () => {
            const result = originalClearSelection();

            // Clear all selection visuals
            this.uiManager.systems.selectionRenderer?.clearAll();

            return result;
        };

        // Override command handling to use new visual feedback
        const originalIssueCommand = this.selectionSystem.issueCommandToSelected.bind(this.selectionSystem);

        this.selectionSystem.issueCommandToSelected = (command, target, queued = false) => {
            const result = originalIssueCommand(command, target, queued);

            // Show visual feedback based on command type
            if (command === 'move' && target) {
                this.uiManager.systems.visualFeedback?.showMoveCommand(target.x, target.y, queued);

                // Emit game event
                window.dispatchEvent(new CustomEvent('command:move', {
                    detail: { x: target.x, y: target.y, queued: queued }
                }));
            }

            return result;
        };

        console.log('🎯 Selection system integrated with new UI systems');
    }

    /**
     * Setup game event handlers
     */
    setupGameEventHandlers() {
        // Handle building placement events
        window.addEventListener('buildingPlacement:buildingPlaced', (event) => {
            const { type, position, data } = event.detail;

            console.log(`🏗️  Building placed: ${type} at (${position.x}, ${position.y})`);

            // Create building entity in ECS world
            this.createBuildingEntity(type, position, data);

            // Update resource tracking
            this.updateResources(-data.cost);
        });

        // Handle unit damage events
        window.addEventListener('unit:damaged', (event) => {
            const { entity, damage, damageType } = event.detail;

            // Show damage feedback
            this.uiManager.systems.visualFeedback?.showUnitDamage(entity, damage, damageType);
        });

        // Handle resource collection events
        window.addEventListener('resource:collected', (event) => {
            const { x, y, amount, type } = event.detail;

            // Show resource gain feedback
            this.uiManager.systems.visualFeedback?.showResourceGain(x, y, amount, type);

            // Update resource tracking
            this.updateResources(amount);
        });
    }

    /**
     * Setup UI event handlers
     */
    setupUIEventHandlers() {
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            this.handleKeyboardInput(event);
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        // Handle visibility change (tab switching)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseGame();
            } else {
                this.resumeGame();
            }
        });
    }

    /**
     * Setup resource tracking for economy UI
     */
    setupResourceTracking() {
        // Initialize starting resources
        this.gameResources = {
            credits: 5000,
            power: 200,
            tiberium: 0
        };

        // Update resource UI periodically
        setInterval(() => {
            this.updateResourceUI();
        }, 1000);
    }

    /**
     * Update resource values
     */
    updateResources(creditChange) {
        this.gameResources.credits = Math.max(0, this.gameResources.credits + creditChange);
        this.updateResourceUI();
    }

    /**
     * Update resource UI with current values
     */
    updateResourceUI() {
        // This would typically read from actual game state
        // For demo purposes, we'll simulate resource changes

        // Simulate income from harvesters
        this.gameResources.credits += Math.random() * 10;

        // The ResourceEconomyUI will automatically update through the UIManager
    }

    /**
     * Create initial game content for demonstration
     */
    createInitialContent() {
        console.log('🎨 Creating initial game content...');

        // Create some test entities for selection demonstration
        this.createTestEntities();

        // Show welcome message
        setTimeout(() => {
            this.uiManager.systems.visualFeedback?.showAlert(
                640, 300,
                'Welcome to the RTS Game!\\nPress F12 for debug interface',
                'info'
            );
        }, 2000);
    }

    /**
     * Create test entities for demonstration
     */
    createTestEntities() {
        // Create test units
        for (let i = 0; i < 5; i++) {
            const entity = this.world.createEntity();

            // Add components
            entity.addComponent('TransformComponent', {
                x: 400 + i * 80,
                y: 400,
                rotation: 0
            });

            entity.addComponent('SelectableComponent', {
                selectableRadius: 20,
                isSelected: false
            });

            entity.addComponent('HealthComponent', {
                maxHealth: 100,
                currentHealth: 100 - i * 10
            });

            entity.addComponent('MovementComponent', {
                speed: 50,
                targetX: null,
                targetY: null
            });

            // Add visual representation (simplified)
            const sprite = new PIXI.Graphics();
            sprite.beginFill(0x00ff00);
            sprite.drawCircle(0, 0, 15);
            sprite.endFill();
            sprite.position.set(400 + i * 80, 400);

            this.app.layers.units.addChild(sprite);

            entity.addComponent('SpriteComponent', { sprite: sprite });
        }

        console.log('🎮 Created 5 test entities');
    }

    /**
     * Create building entity when building is placed
     */
    createBuildingEntity(type, position, data) {
        const entity = this.world.createEntity();

        entity.addComponent('TransformComponent', {
            x: position.x,
            y: position.y,
            rotation: 0
        });

        entity.addComponent('BuildingComponent', {
            type: type,
            width: data.width,
            height: data.height,
            power: data.power,
            isConstructed: false,
            constructionProgress: 0
        });

        // Simulate construction progress
        const constructionInterval = setInterval(() => {
            const buildingComp = entity.getComponent('BuildingComponent');
            buildingComp.constructionProgress += 10;

            // Show construction effects
            this.uiManager.systems.visualFeedback?.showConstructionProgress(
                position.x, position.y, buildingComp.constructionProgress / 100
            );

            if (buildingComp.constructionProgress >= 100) {
                buildingComp.isConstructed = true;
                clearInterval(constructionInterval);

                console.log(`🏗️  ${type} construction completed`);
            }
        }, 200);

        return entity;
    }

    /**
     * Start the main game loop
     */
    startGameLoop() {
        console.log('🔄 Starting game loop...');

        this.gameLoop.start((deltaTime, interpolation) => {
            this.update(deltaTime);
            this.render(interpolation);
        });

        console.log('✅ Game loop started');
    }

    /**
     * Main update function
     */
    update(deltaTime) {
        if (this.isPaused) return;

        // Update ECS world
        this.world.update(deltaTime);

        // Update UI systems
        this.uiManager.update(deltaTime);

        // Update camera
        this.camera.update(deltaTime);

        // Update performance stats
        this.updatePerformanceStats(deltaTime);
    }

    /**
     * Main render function
     */
    render(interpolation) {
        if (this.isPaused) return;

        // Render the scene
        this.app.render(interpolation);

        // Update sprite batcher if available
        if (this.spriteBatcher && this.camera) {
            const sprites = this.getAllSprites();
            this.spriteBatcher.render(sprites, this.camera);
        }
    }

    /**
     * Get all sprites for batching
     */
    getAllSprites() {
        const sprites = [];

        // Collect sprites from all layers
        for (const layer of Object.values(this.app.layers)) {
            layer.children.forEach(child => {
                if (child instanceof PIXI.Sprite) {
                    sprites.push(child);
                }
            });
        }

        return sprites;
    }

    /**
     * Handle keyboard input
     */
    handleKeyboardInput(event) {
        switch (event.key) {
            case 'b':
            case 'B':
                // Start building placement
                this.startBuildingPlacement();
                break;

            case 'Escape':
                // Cancel any active UI mode
                this.cancelActiveUIMode();
                break;

            case 'p':
            case 'P':
                // Pause/unpause game
                this.togglePause();
                break;
        }
    }

    /**
     * Start building placement mode
     */
    startBuildingPlacement() {
        const buildingPlacement = this.uiManager.systems.buildingPlacement;

        if (buildingPlacement && !buildingPlacement.isInPlacementMode()) {
            // Create simple resource validator
            const resourceValidator = {
                canAfford: (cost) => this.gameResources.credits >= cost,
                deductCost: (cost) => { this.gameResources.credits -= cost; }
            };

            buildingPlacement.startPlacement('barracks', resourceValidator);
            console.log('🏗️  Building placement mode started');
        }
    }

    /**
     * Cancel active UI mode
     */
    cancelActiveUIMode() {
        const buildingPlacement = this.uiManager.systems.buildingPlacement;

        if (buildingPlacement && buildingPlacement.isInPlacementMode()) {
            buildingPlacement.cancelPlacement();
        }

        // Clear selection
        this.selectionSystem.clearSelection();
    }

    /**
     * Toggle pause state
     */
    togglePause() {
        if (this.isPaused) {
            this.resumeGame();
        } else {
            this.pauseGame();
        }
    }

    /**
     * Pause the game
     */
    pauseGame() {
        this.isPaused = true;
        this.gameLoop.pause();
        console.log('⏸️  Game paused');
    }

    /**
     * Resume the game
     */
    resumeGame() {
        this.isPaused = false;
        this.gameLoop.resume();
        console.log('▶️  Game resumed');
    }

    /**
     * Handle window resize
     */
    handleResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        this.app.resize(width, height);
        this.camera.updateViewSize(width, height);

        console.log(`📐 Resized to ${width}x${height}`);
    }

    /**
     * Update performance statistics
     */
    updatePerformanceStats(deltaTime) {
        this.stats.frameCount++;
        this.stats.avgFrameTime = (this.stats.avgFrameTime + deltaTime) / 2;

        const now = Date.now();
        if (now - this.stats.lastStatsUpdate > 1000) {
            // Log performance stats every second
            const uiStats = this.uiManager.getPerformanceStats();

            console.debug(`📊 Performance: ${uiStats.fps} FPS, ${uiStats.drawCalls} draws, ${uiStats.sprites} sprites`);

            this.stats.lastStatsUpdate = now;
            this.stats.frameCount = 0;
        }
    }

    /**
     * Show initialization complete message
     */
    showInitializationComplete() {
        setTimeout(() => {
            this.uiManager.systems.visualFeedback?.showAlert(
                640, 200,
                'UI Integration Demo Ready!\\n\\nControls:\\nB - Build mode\\nP - Pause\\nF12 - Debug',
                'info'
            );
        }, 1000);
    }

    /**
     * Detect mobile device
     */
    detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (navigator.maxTouchPoints && navigator.maxTouchPoints > 1);
    }

    /**
     * Get current game state for external access
     */
    getGameState() {
        return {
            isInitialized: this.isInitialized,
            isPaused: this.isPaused,
            resources: { ...this.gameResources },
            entityCount: this.world ? this.world.entities.length : 0,
            selectedCount: this.selectionSystem ? this.selectionSystem.selectedEntities.size : 0,
            performance: this.uiManager ? this.uiManager.getPerformanceStats() : {}
        };
    }

    /**
     * Cleanup and destroy the game
     */
    destroy() {
        console.log('🗑️ Destroying UI-integrated game...');

        // Stop game loop
        if (this.gameLoop) {
            this.gameLoop.stop();
        }

        // Destroy UI manager (handles all UI systems)
        if (this.uiManager) {
            this.uiManager.destroy();
        }

        // Destroy ECS systems
        if (this.selectionSystem) {
            this.selectionSystem.destroy();
        }

        if (this.world) {
            this.world.destroy();
        }

        // Destroy core systems
        if (this.spriteBatcher) {
            this.spriteBatcher.destroy();
        }

        if (this.inputHandler) {
            this.inputHandler.destroy();
        }

        if (this.app) {
            this.app.destroy();
        }

        console.log('✅ Game destroyed successfully');
    }
}

// Export for use in other modules
export default UIIntegratedGame;

// Usage example:
/*
const game = new UIIntegratedGame({
    enableDebug: true,
    effectQuality: 'high',
    enableAnimations: true,
    enableParticles: true
});

// The game will automatically initialize and start
// Access game state: game.getGameState()
// Destroy when done: game.destroy()
*/
