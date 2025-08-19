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
        const originalSelectEntity = this.selectionSystem.selectEntity.bind(this.selectionSystem);\n        const originalDeselectEntity = this.selectionSystem.deselectEntity.bind(this.selectionSystem);\n        const originalClearSelection = this.selectionSystem.clearSelection.bind(this.selectionSystem);\n        \n        // Enhance selectEntity to use new selection renderer\n        this.selectionSystem.selectEntity = (entity) => {\n            const result = originalSelectEntity(entity);\n            \n            // Use new selection renderer\n            const transform = entity.getComponent('TransformComponent');\n            const health = entity.getComponent('HealthComponent');\n            \n            if (transform) {\n                this.uiManager.systems.selectionRenderer?.showSelection(entity.id, transform, health);\n                this.uiManager.systems.visualFeedback?.showSelectionPulse(entity);\n            }\n            \n            return result;\n        };\n        \n        // Enhance deselectEntity\n        this.selectionSystem.deselectEntity = (entity) => {\n            const result = originalDeselectEntity(entity);\n            \n            // Hide selection visuals\n            this.uiManager.systems.selectionRenderer?.hideSelection(entity.id);\n            \n            return result;\n        };\n        \n        // Enhance clearSelection\n        this.selectionSystem.clearSelection = () => {\n            const result = originalClearSelection();\n            \n            // Clear all selection visuals\n            this.uiManager.systems.selectionRenderer?.clearAll();\n            \n            return result;\n        };\n        \n        // Override command handling to use new visual feedback\n        const originalIssueCommand = this.selectionSystem.issueCommandToSelected.bind(this.selectionSystem);\n        \n        this.selectionSystem.issueCommandToSelected = (command, target, queued = false) => {\n            const result = originalIssueCommand(command, target, queued);\n            \n            // Show visual feedback based on command type\n            if (command === 'move' && target) {\n                this.uiManager.systems.visualFeedback?.showMoveCommand(target.x, target.y, queued);\n                \n                // Emit game event\n                window.dispatchEvent(new CustomEvent('command:move', {\n                    detail: { x: target.x, y: target.y, queued: queued }\n                }));\n            }\n            \n            return result;\n        };\n        \n        console.log('🎯 Selection system integrated with new UI systems');\n    }\n    \n    /**\n     * Setup game event handlers\n     */\n    setupGameEventHandlers() {\n        // Handle building placement events\n        window.addEventListener('buildingPlacement:buildingPlaced', (event) => {\n            const { type, position, data } = event.detail;\n            \n            console.log(`🏗️  Building placed: ${type} at (${position.x}, ${position.y})`);\n            \n            // Create building entity in ECS world\n            this.createBuildingEntity(type, position, data);\n            \n            // Update resource tracking\n            this.updateResources(-data.cost);\n        });\n        \n        // Handle unit damage events\n        window.addEventListener('unit:damaged', (event) => {\n            const { entity, damage, damageType } = event.detail;\n            \n            // Show damage feedback\n            this.uiManager.systems.visualFeedback?.showUnitDamage(entity, damage, damageType);\n        });\n        \n        // Handle resource collection events\n        window.addEventListener('resource:collected', (event) => {\n            const { x, y, amount, type } = event.detail;\n            \n            // Show resource gain feedback\n            this.uiManager.systems.visualFeedback?.showResourceGain(x, y, amount, type);\n            \n            // Update resource tracking\n            this.updateResources(amount);\n        });\n    }\n    \n    /**\n     * Setup UI event handlers\n     */\n    setupUIEventHandlers() {\n        // Handle keyboard shortcuts\n        document.addEventListener('keydown', (event) => {\n            this.handleKeyboardInput(event);\n        });\n        \n        // Handle window resize\n        window.addEventListener('resize', () => {\n            this.handleResize();\n        });\n        \n        // Handle visibility change (tab switching)\n        document.addEventListener('visibilitychange', () => {\n            if (document.hidden) {\n                this.pauseGame();\n            } else {\n                this.resumeGame();\n            }\n        });\n    }\n    \n    /**\n     * Setup resource tracking for economy UI\n     */\n    setupResourceTracking() {\n        // Initialize starting resources\n        this.gameResources = {\n            credits: 5000,\n            power: 200,\n            tiberium: 0\n        };\n        \n        // Update resource UI periodically\n        setInterval(() => {\n            this.updateResourceUI();\n        }, 1000);\n    }\n    \n    /**\n     * Update resource values\n     */\n    updateResources(creditChange) {\n        this.gameResources.credits = Math.max(0, this.gameResources.credits + creditChange);\n        this.updateResourceUI();\n    }\n    \n    /**\n     * Update resource UI with current values\n     */\n    updateResourceUI() {\n        // This would typically read from actual game state\n        // For demo purposes, we'll simulate resource changes\n        \n        // Simulate income from harvesters\n        this.gameResources.credits += Math.random() * 10;\n        \n        // The ResourceEconomyUI will automatically update through the UIManager\n    }\n    \n    /**\n     * Create initial game content for demonstration\n     */\n    createInitialContent() {\n        console.log('🎨 Creating initial game content...');\n        \n        // Create some test entities for selection demonstration\n        this.createTestEntities();\n        \n        // Show welcome message\n        setTimeout(() => {\n            this.uiManager.systems.visualFeedback?.showAlert(\n                640, 300, \n                'Welcome to the RTS Game!\\nPress F12 for debug interface',\n                'info'\n            );\n        }, 2000);\n    }\n    \n    /**\n     * Create test entities for demonstration\n     */\n    createTestEntities() {\n        // Create test units\n        for (let i = 0; i < 5; i++) {\n            const entity = this.world.createEntity();\n            \n            // Add components\n            entity.addComponent('TransformComponent', {\n                x: 400 + i * 80,\n                y: 400,\n                rotation: 0\n            });\n            \n            entity.addComponent('SelectableComponent', {\n                selectableRadius: 20,\n                isSelected: false\n            });\n            \n            entity.addComponent('HealthComponent', {\n                maxHealth: 100,\n                currentHealth: 100 - i * 10\n            });\n            \n            entity.addComponent('MovementComponent', {\n                speed: 50,\n                targetX: null,\n                targetY: null\n            });\n            \n            // Add visual representation (simplified)\n            const sprite = new PIXI.Graphics();\n            sprite.beginFill(0x00ff00);\n            sprite.drawCircle(0, 0, 15);\n            sprite.endFill();\n            sprite.position.set(400 + i * 80, 400);\n            \n            this.app.layers.units.addChild(sprite);\n            \n            entity.addComponent('SpriteComponent', { sprite: sprite });\n        }\n        \n        console.log('🎮 Created 5 test entities');\n    }\n    \n    /**\n     * Create building entity when building is placed\n     */\n    createBuildingEntity(type, position, data) {\n        const entity = this.world.createEntity();\n        \n        entity.addComponent('TransformComponent', {\n            x: position.x,\n            y: position.y,\n            rotation: 0\n        });\n        \n        entity.addComponent('BuildingComponent', {\n            type: type,\n            width: data.width,\n            height: data.height,\n            power: data.power,\n            isConstructed: false,\n            constructionProgress: 0\n        });\n        \n        // Simulate construction progress\n        const constructionInterval = setInterval(() => {\n            const buildingComp = entity.getComponent('BuildingComponent');\n            buildingComp.constructionProgress += 10;\n            \n            // Show construction effects\n            this.uiManager.systems.visualFeedback?.showConstructionProgress(\n                position.x, position.y, buildingComp.constructionProgress / 100\n            );\n            \n            if (buildingComp.constructionProgress >= 100) {\n                buildingComp.isConstructed = true;\n                clearInterval(constructionInterval);\n                \n                console.log(`🏗️  ${type} construction completed`);\n            }\n        }, 200);\n        \n        return entity;\n    }\n    \n    /**\n     * Start the main game loop\n     */\n    startGameLoop() {\n        console.log('🔄 Starting game loop...');\n        \n        this.gameLoop.start((deltaTime, interpolation) => {\n            this.update(deltaTime);\n            this.render(interpolation);\n        });\n        \n        console.log('✅ Game loop started');\n    }\n    \n    /**\n     * Main update function\n     */\n    update(deltaTime) {\n        if (this.isPaused) return;\n        \n        // Update ECS world\n        this.world.update(deltaTime);\n        \n        // Update UI systems\n        this.uiManager.update(deltaTime);\n        \n        // Update camera\n        this.camera.update(deltaTime);\n        \n        // Update performance stats\n        this.updatePerformanceStats(deltaTime);\n    }\n    \n    /**\n     * Main render function\n     */\n    render(interpolation) {\n        if (this.isPaused) return;\n        \n        // Render the scene\n        this.app.render(interpolation);\n        \n        // Update sprite batcher if available\n        if (this.spriteBatcher && this.camera) {\n            const sprites = this.getAllSprites();\n            this.spriteBatcher.render(sprites, this.camera);\n        }\n    }\n    \n    /**\n     * Get all sprites for batching\n     */\n    getAllSprites() {\n        const sprites = [];\n        \n        // Collect sprites from all layers\n        for (const layer of Object.values(this.app.layers)) {\n            layer.children.forEach(child => {\n                if (child instanceof PIXI.Sprite) {\n                    sprites.push(child);\n                }\n            });\n        }\n        \n        return sprites;\n    }\n    \n    /**\n     * Handle keyboard input\n     */\n    handleKeyboardInput(event) {\n        switch (event.key) {\n            case 'b':\n            case 'B':\n                // Start building placement\n                this.startBuildingPlacement();\n                break;\n                \n            case 'Escape':\n                // Cancel any active UI mode\n                this.cancelActiveUIMode();\n                break;\n                \n            case 'p':\n            case 'P':\n                // Pause/unpause game\n                this.togglePause();\n                break;\n        }\n    }\n    \n    /**\n     * Start building placement mode\n     */\n    startBuildingPlacement() {\n        const buildingPlacement = this.uiManager.systems.buildingPlacement;\n        \n        if (buildingPlacement && !buildingPlacement.isInPlacementMode()) {\n            // Create simple resource validator\n            const resourceValidator = {\n                canAfford: (cost) => this.gameResources.credits >= cost,\n                deductCost: (cost) => { this.gameResources.credits -= cost; }\n            };\n            \n            buildingPlacement.startPlacement('barracks', resourceValidator);\n            console.log('🏗️  Building placement mode started');\n        }\n    }\n    \n    /**\n     * Cancel active UI mode\n     */\n    cancelActiveUIMode() {\n        const buildingPlacement = this.uiManager.systems.buildingPlacement;\n        \n        if (buildingPlacement && buildingPlacement.isInPlacementMode()) {\n            buildingPlacement.cancelPlacement();\n        }\n        \n        // Clear selection\n        this.selectionSystem.clearSelection();\n    }\n    \n    /**\n     * Toggle pause state\n     */\n    togglePause() {\n        if (this.isPaused) {\n            this.resumeGame();\n        } else {\n            this.pauseGame();\n        }\n    }\n    \n    /**\n     * Pause the game\n     */\n    pauseGame() {\n        this.isPaused = true;\n        this.gameLoop.pause();\n        console.log('⏸️  Game paused');\n    }\n    \n    /**\n     * Resume the game\n     */\n    resumeGame() {\n        this.isPaused = false;\n        this.gameLoop.resume();\n        console.log('▶️  Game resumed');\n    }\n    \n    /**\n     * Handle window resize\n     */\n    handleResize() {\n        const width = window.innerWidth;\n        const height = window.innerHeight;\n        \n        this.app.resize(width, height);\n        this.camera.updateViewSize(width, height);\n        \n        console.log(`📐 Resized to ${width}x${height}`);\n    }\n    \n    /**\n     * Update performance statistics\n     */\n    updatePerformanceStats(deltaTime) {\n        this.stats.frameCount++;\n        this.stats.avgFrameTime = (this.stats.avgFrameTime + deltaTime) / 2;\n        \n        const now = Date.now();\n        if (now - this.stats.lastStatsUpdate > 1000) {\n            // Log performance stats every second\n            const uiStats = this.uiManager.getPerformanceStats();\n            \n            console.debug(`📊 Performance: ${uiStats.fps} FPS, ${uiStats.drawCalls} draws, ${uiStats.sprites} sprites`);\n            \n            this.stats.lastStatsUpdate = now;\n            this.stats.frameCount = 0;\n        }\n    }\n    \n    /**\n     * Show initialization complete message\n     */\n    showInitializationComplete() {\n        setTimeout(() => {\n            this.uiManager.systems.visualFeedback?.showAlert(\n                640, 200,\n                'UI Integration Demo Ready!\\n\\nControls:\\nB - Build mode\\nP - Pause\\nF12 - Debug',\n                'info'\n            );\n        }, 1000);\n    }\n    \n    /**\n     * Detect mobile device\n     */\n    detectMobile() {\n        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||\n               (navigator.maxTouchPoints && navigator.maxTouchPoints > 1);\n    }\n    \n    /**\n     * Get current game state for external access\n     */\n    getGameState() {\n        return {\n            isInitialized: this.isInitialized,\n            isPaused: this.isPaused,\n            resources: { ...this.gameResources },\n            entityCount: this.world ? this.world.entities.length : 0,\n            selectedCount: this.selectionSystem ? this.selectionSystem.selectedEntities.size : 0,\n            performance: this.uiManager ? this.uiManager.getPerformanceStats() : {}\n        };\n    }\n    \n    /**\n     * Cleanup and destroy the game\n     */\n    destroy() {\n        console.log('🗑️ Destroying UI-integrated game...');\n        \n        // Stop game loop\n        if (this.gameLoop) {\n            this.gameLoop.stop();\n        }\n        \n        // Destroy UI manager (handles all UI systems)\n        if (this.uiManager) {\n            this.uiManager.destroy();\n        }\n        \n        // Destroy ECS systems\n        if (this.selectionSystem) {\n            this.selectionSystem.destroy();\n        }\n        \n        if (this.world) {\n            this.world.destroy();\n        }\n        \n        // Destroy core systems\n        if (this.spriteBatcher) {\n            this.spriteBatcher.destroy();\n        }\n        \n        if (this.inputHandler) {\n            this.inputHandler.destroy();\n        }\n        \n        if (this.app) {\n            this.app.destroy();\n        }\n        \n        console.log('✅ Game destroyed successfully');\n    }\n}\n\n// Export for use in other modules\nexport default UIIntegratedGame;\n\n// Usage example:\n/*\nconst game = new UIIntegratedGame({\n    enableDebug: true,\n    effectQuality: 'high',\n    enableAnimations: true,\n    enableParticles: true\n});\n\n// The game will automatically initialize and start\n// Access game state: game.getGameState()\n// Destroy when done: game.destroy()\n*/"