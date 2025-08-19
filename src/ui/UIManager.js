/**
 * UIManager - Central coordinator for all UI systems
 * 
 * Main integration point that coordinates all UI subsystems for optimal
 * performance and consistent user experience. Manages system lifecycle,
 * performance monitoring, and cross-system communication.
 * 
 * Integrates:
 * - SelectionRenderer (optimized selection visuals)
 * - InputBatcher (batched input processing)
 * - BuildingPlacementUI (building placement system)
 * - ResourceEconomyUI (economic interface)
 * - VisualFeedbackSystem (comprehensive effects)
 * - UIUpdateManager (DOM update optimization)
 * 
 * Features:
 * - Centralized performance monitoring
 * - System coordination and event routing
 * - Mobile/desktop optimization switching
 * - Accessibility mode support
 * - Debug interface for development
 */

import { SelectionRenderer } from './SelectionRenderer.js';
import { InputBatcher } from '../core/InputBatcher.js';
import { BuildingPlacementUI } from './BuildingPlacementUI.js';
import { ResourceEconomyUI } from './ResourceEconomyUI.js';
import { VisualFeedbackSystem } from './VisualFeedbackSystem.js';
import { UIUpdateManager } from '../core/UIUpdateManager.js';

export class UIManager {
    constructor(app, world, camera, inputHandler, options = {}) {
        this.app = app;
        this.world = world;
        this.camera = camera;
        this.inputHandler = inputHandler;
        
        // Configuration
        this.config = {
            enablePerformanceMonitoring: options.enablePerformanceMonitoring !== false,
            enableDebugInterface: options.enableDebugInterface || false,
            isMobile: options.isMobile || this.detectMobile(),
            enableAccessibilityMode: options.enableAccessibilityMode || false,
            performanceTarget: {
                fps: options.targetFPS || 60,
                maxUIUpdateTime: options.maxUIUpdateTime || 16, // ms
                maxInputLatency: options.maxInputLatency || 33 // ms
            },
            qualitySettings: {
                effects: options.effectQuality || 'high',
                animations: options.enableAnimations !== false,
                particles: options.enableParticles !== false
            }
        };
        
        // UI System instances
        this.systems = {
            uiUpdateManager: null,
            selectionRenderer: null,
            inputBatcher: null,
            buildingPlacement: null,
            resourceEconomy: null,
            visualFeedback: null
        };
        
        // System status tracking
        this.systemStatus = new Map();
        
        // Performance monitoring
        this.performance = {
            frameTime: 0,
            uiUpdateTime: 0,
            inputLatency: 0,
            memoryUsage: 0,
            lastFrameTime: performance.now(),
            frameCount: 0,
            fps: 60
        };
        
        // Event routing
        this.eventRoutes = new Map();
        
        // Debug interface state
        this.debugUI = null;
        this.showDebugStats = false;
        
        // Accessibility features
        this.accessibility = {
            highContrast: false,
            reduceMotion: false,
            screenReader: false,
            keyboardNavigation: false
        };
        
        this.isDestroyed = false;
        
        this.init();
    }
    
    /**
     * Initialize all UI systems
     */
    async init() {
        console.log('🎛️  Initializing UIManager...');
        
        try {
            // Initialize systems in dependency order
            await this.initializeUIUpdateManager();
            await this.initializeSelectionRenderer();
            await this.initializeInputBatcher();
            await this.initializeBuildingPlacement();
            await this.initializeResourceEconomy();
            await this.initializeVisualFeedback();
            
            // Setup system coordination
            this.setupSystemCoordination();
            
            // Setup event routing
            this.setupEventRouting();
            
            // Setup performance monitoring
            if (this.config.enablePerformanceMonitoring) {
                this.setupPerformanceMonitoring();
            }
            
            // Setup debug interface
            if (this.config.enableDebugInterface) {
                this.setupDebugInterface();
            }
            
            // Setup accessibility features
            this.setupAccessibilityFeatures();
            
            // Apply platform-specific optimizations
            this.applyPlatformOptimizations();
            
            console.log('✅ UIManager initialization complete');
            console.log(`📱 Platform: ${this.config.isMobile ? 'Mobile' : 'Desktop'}`);
            console.log(`♿ Accessibility: ${this.config.enableAccessibilityMode ? 'Enabled' : 'Disabled'}`);
            
        } catch (error) {
            console.error('❌ UIManager initialization failed:', error);
            throw error;
        }
    }
    
    /**
     * Initialize UI Update Manager
     */
    async initializeUIUpdateManager() {
        console.log('🔄 Initializing UIUpdateManager...');
        
        this.systems.uiUpdateManager = new UIUpdateManager({
            updateHz: this.config.isMobile ? 8 : 10, // Slower on mobile
            enableVirtualDOM: !this.config.isMobile // Disable virtual DOM on mobile for performance
        });
        
        this.systems.uiUpdateManager.start();
        this.systemStatus.set('uiUpdateManager', { status: 'active', errors: 0 });
        
        console.log('✅ UIUpdateManager ready');
    }
    
    /**
     * Initialize Selection Renderer
     */
    async initializeSelectionRenderer() {
        console.log('🎯 Initializing SelectionRenderer...');
        
        const spriteBatcher = this.app.spriteBatcher; // Assume app has SpriteBatcher
        
        this.systems.selectionRenderer = new SelectionRenderer(this.app, spriteBatcher, {
            poolSize: this.config.isMobile ? 50 : 100,
            enableAnimations: this.config.qualitySettings.animations,
            animationSpeed: this.config.isMobile ? 0.03 : 0.05
        });
        
        this.systemStatus.set('selectionRenderer', { status: 'active', errors: 0 });
        
        console.log('✅ SelectionRenderer ready');
    }
    
    /**
     * Initialize Input Batcher
     */
    async initializeInputBatcher() {
        console.log('⌨️  Initializing InputBatcher...');
        
        this.systems.inputBatcher = new InputBatcher(this.inputHandler, this.camera, {
            batchSize: this.config.isMobile ? 8 : 16,
            processFrequency: this.config.isMobile ? 30 : 60, // Lower frequency on mobile
            enableGestures: this.config.isMobile,
            enableDeduplication: true,
            touchThreshold: this.config.isMobile ? 6 : 4
        });
        
        this.systemStatus.set('inputBatcher', { status: 'active', errors: 0 });
        
        console.log('✅ InputBatcher ready');
    }
    
    /**
     * Initialize Building Placement UI
     */
    async initializeBuildingPlacement() {
        console.log('🏗️  Initializing BuildingPlacementUI...');
        
        this.systems.buildingPlacement = new BuildingPlacementUI(this.app, this.camera, this.world, {
            gridSize: 32,
            showGrid: !this.config.isMobile, // Hide grid on mobile for clarity
            enableSounds: true,
            snapToGrid: true
        });
        
        this.systemStatus.set('buildingPlacement', { status: 'active', errors: 0 });
        
        console.log('✅ BuildingPlacementUI ready');
    }
    
    /**
     * Initialize Resource Economy UI
     */
    async initializeResourceEconomy() {
        console.log('💰 Initializing ResourceEconomyUI...');
        
        this.systems.resourceEconomy = new ResourceEconomyUI(this.world, this.systems.uiUpdateManager, {
            updateInterval: this.config.isMobile ? 200 : 100, // Slower updates on mobile
            enableAnimations: this.config.qualitySettings.animations,
            enablePredictions: !this.config.isMobile // Disable predictions on mobile
        });
        
        this.systemStatus.set('resourceEconomy', { status: 'active', errors: 0 });
        
        console.log('✅ ResourceEconomyUI ready');
    }
    
    /**
     * Initialize Visual Feedback System
     */
    async initializeVisualFeedback() {
        console.log('✨ Initializing VisualFeedbackSystem...');
        
        this.systems.visualFeedback = new VisualFeedbackSystem(this.app, this.systems.selectionRenderer, {
            enableEffects: this.config.qualitySettings.effects !== 'off',
            effectQuality: this.config.qualitySettings.effects,
            maxParticles: this.config.isMobile ? 100 : 500,
            particlePoolSize: this.config.isMobile ? 50 : 200,
            enableScreenShake: !this.config.isMobile && this.config.qualitySettings.effects !== 'low',
            accessibilityMode: this.config.enableAccessibilityMode
        });
        
        this.systemStatus.set('visualFeedback', { status: 'active', errors: 0 });
        
        console.log('✅ VisualFeedbackSystem ready');
    }
    
    /**
     * Setup coordination between systems
     */
    setupSystemCoordination() {
        console.log('🔗 Setting up system coordination...');
        
        // Connect selection renderer to input events
        if (this.systems.inputBatcher && this.systems.selectionRenderer) {
            this.systems.inputBatcher.on('mousedown', (event) => {
                if (event.button === 0) { // Left click
                    this.handleSelectionInput(event);
                }
            }, 'high');
        }
        
        // Connect building placement to resource economy
        if (this.systems.buildingPlacement && this.systems.resourceEconomy) {
            window.addEventListener('buildingPlacement:buildingPlaced', (event) => {
                const buildingData = event.detail;
                this.systems.visualFeedback?.showBuildingPlaced(
                    buildingData.position.x,
                    buildingData.position.y,
                    buildingData.data
                );
            });
        }
        
        // Connect visual feedback to various events
        if (this.systems.visualFeedback) {
            // Selection events
            window.addEventListener('entity:selected', (event) => {
                this.systems.visualFeedback.showSelectionPulse(event.detail.entity);
            });
            
            // Command events
            window.addEventListener('command:move', (event) => {
                this.systems.visualFeedback.showMoveCommand(
                    event.detail.x,
                    event.detail.y,
                    event.detail.queued
                );
            });
            
            window.addEventListener('command:attack', (event) => {
                this.systems.visualFeedback.showAttackCommand(
                    event.detail.x,
                    event.detail.y,
                    event.detail.target
                );
            });
        }
        
        console.log('✅ System coordination setup complete');
    }
    
    /**
     * Setup event routing between systems
     */
    setupEventRouting() {
        // Route input events through the batcher
        this.eventRoutes.set('input', this.systems.inputBatcher);
        
        // Route selection events through selection renderer
        this.eventRoutes.set('selection', this.systems.selectionRenderer);
        
        // Route building events through placement system
        this.eventRoutes.set('building', this.systems.buildingPlacement);
        
        // Route resource events through economy UI
        this.eventRoutes.set('resource', this.systems.resourceEconomy);
        
        // Route visual effects through feedback system
        this.eventRoutes.set('effects', this.systems.visualFeedback);
    }
    
    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        console.log('📊 Setting up performance monitoring...');
        
        let lastTime = performance.now();
        let frameCount = 0;
        
        const monitorLoop = () => {
            if (this.isDestroyed) return;
            
            const currentTime = performance.now();
            const deltaTime = currentTime - lastTime;
            
            // Update performance metrics
            this.performance.frameTime = deltaTime;
            this.performance.frameCount++;
            frameCount++;
            
            // Calculate FPS every second
            if (frameCount >= 60) {
                this.performance.fps = Math.round(1000 / (deltaTime / 60));
                frameCount = 0;
            }
            
            // Check performance targets
            this.checkPerformanceTargets();
            
            // Update UI with performance stats
            this.updatePerformanceDisplay();
            
            lastTime = currentTime;
            requestAnimationFrame(monitorLoop);
        };
        
        requestAnimationFrame(monitorLoop);
        
        console.log('✅ Performance monitoring active');
    }
    
    /**
     * Check performance targets and adjust quality if needed
     */
    checkPerformanceTargets() {
        const { fps, frameTime } = this.performance;
        const { performanceTarget } = this.config;
        
        // Auto-adjust quality if performance is poor
        if (fps < performanceTarget.fps * 0.8) { // 80% of target
            this.autoAdjustQuality('down');
        } else if (fps > performanceTarget.fps * 1.1) { // 110% of target
            this.autoAdjustQuality('up');
        }
        
        // Warn about performance issues
        if (frameTime > performanceTarget.maxUIUpdateTime * 2) {
            console.warn(`⚠️ High frame time: ${frameTime.toFixed(2)}ms`);
        }
    }
    
    /**
     * Auto-adjust quality settings based on performance
     */
    autoAdjustQuality(direction) {
        if (direction === 'down') {
            // Reduce quality
            if (this.config.qualitySettings.effects === 'high') {
                this.config.qualitySettings.effects = 'medium';
                this.systems.visualFeedback?.updateConfig({ effectQuality: 'medium' });
            } else if (this.config.qualitySettings.effects === 'medium') {
                this.config.qualitySettings.effects = 'low';
                this.systems.visualFeedback?.updateConfig({ effectQuality: 'low' });
            }
            
            console.log(`📉 Quality adjusted down: ${this.config.qualitySettings.effects}`);
            
        } else if (direction === 'up') {
            // Increase quality
            if (this.config.qualitySettings.effects === 'low') {
                this.config.qualitySettings.effects = 'medium';
                this.systems.visualFeedback?.updateConfig({ effectQuality: 'medium' });
            } else if (this.config.qualitySettings.effects === 'medium') {
                this.config.qualitySettings.effects = 'high';
                this.systems.visualFeedback?.updateConfig({ effectQuality: 'high' });
            }
            
            console.log(`📈 Quality adjusted up: ${this.config.qualitySettings.effects}`);
        }
    }
    
    /**
     * Update performance display
     */
    updatePerformanceDisplay() {
        if (!this.systems.uiUpdateManager) return;
        
        const stats = this.getPerformanceStats();
        
        this.systems.uiUpdateManager.updatePerformanceStats({
            fps: stats.fps,
            drawCalls: stats.drawCalls,
            spriteCount: stats.sprites,
            memory: stats.memoryMB
        });
    }
    
    /**
     * Setup debug interface
     */
    setupDebugInterface() {
        console.log('🐛 Setting up debug interface...');
        
        // Create debug UI overlay
        this.createDebugUI();
        
        // Keyboard shortcut to toggle debug (F12)
        document.addEventListener('keydown', (event) => {
            if (event.key === 'F12') {
                event.preventDefault();
                this.toggleDebugInterface();
            }
        });
        
        console.log('✅ Debug interface ready (F12 to toggle)');
    }
    
    /**
     * Create debug UI overlay
     */
    createDebugUI() {
        const debugContainer = document.createElement('div');
        debugContainer.id = 'ui-debug-interface';
        debugContainer.innerHTML = `
            <div class="debug-panel">
                <div class="debug-header">🎛️ UI Debug Interface</div>
                <div class="debug-content">
                    <div class="debug-section">
                        <h4>Performance</h4>
                        <div id="debug-performance">Loading...</div>
                    </div>
                    <div class="debug-section">
                        <h4>Systems Status</h4>
                        <div id="debug-systems">Loading...</div>
                    </div>
                    <div class="debug-section">
                        <h4>Active Effects</h4>
                        <div id="debug-effects">Loading...</div>
                    </div>
                    <div class="debug-section">
                        <h4>Controls</h4>
                        <button id="debug-clear-effects">Clear Effects</button>
                        <button id="debug-reset-quality">Reset Quality</button>
                        <button id="debug-force-gc">Force GC</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add styles
        const styles = document.createElement('style');
        styles.textContent = `
            #ui-debug-interface {
                position: fixed;
                top: 50%;
                right: 10px;
                transform: translateY(-50%);
                background: rgba(0, 0, 0, 0.9);
                border: 2px solid #00ff00;
                border-radius: 8px;
                color: #00ff00;
                font-family: monospace;
                font-size: 12px;
                width: 300px;
                z-index: 9999;
                display: none;
            }
            
            .debug-panel {
                padding: 0;
            }
            
            .debug-header {
                background: rgba(0, 255, 0, 0.2);
                padding: 8px 12px;
                border-bottom: 1px solid #00ff00;
                font-weight: bold;
            }
            
            .debug-content {
                padding: 12px;
                max-height: 500px;
                overflow-y: auto;
            }
            
            .debug-section {
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 1px solid #333;
            }
            
            .debug-section h4 {
                margin: 0 0 8px 0;
                color: #ffff00;
            }
            
            .debug-section button {
                background: rgba(0, 255, 0, 0.2);
                border: 1px solid #00ff00;
                color: #00ff00;
                padding: 4px 8px;
                margin: 2px;
                cursor: pointer;
                font-size: 10px;
            }
            
            .debug-section button:hover {
                background: rgba(0, 255, 0, 0.3);
            }
        `;
        
        document.head.appendChild(styles);
        document.body.appendChild(debugContainer);
        
        this.debugUI = debugContainer;
        
        // Setup debug controls
        document.getElementById('debug-clear-effects')?.addEventListener('click', () => {
            this.systems.visualFeedback?.clearAllEffects();
        });
        
        document.getElementById('debug-reset-quality')?.addEventListener('click', () => {
            this.resetQualitySettings();
        });
        
        document.getElementById('debug-force-gc')?.addEventListener('click', () => {
            if (window.gc) {
                window.gc();
                console.log('🗑️ Garbage collection forced');
            } else {
                console.warn('GC not available');
            }
        });
        
        // Start debug update loop
        this.startDebugUpdateLoop();
    }
    
    /**
     * Start debug update loop
     */
    startDebugUpdateLoop() {
        const updateDebug = () => {
            if (this.isDestroyed || !this.showDebugStats) return;
            
            this.updateDebugDisplay();
            setTimeout(updateDebug, 500); // Update every 500ms
        };
        
        updateDebug();
    }
    
    /**
     * Update debug display
     */
    updateDebugDisplay() {
        if (!this.debugUI) return;
        
        // Performance stats
        const perfElement = document.getElementById('debug-performance');
        if (perfElement) {
            const stats = this.getPerformanceStats();
            perfElement.innerHTML = `
                FPS: ${stats.fps}<br>
                Frame Time: ${stats.frameTime.toFixed(2)}ms<br>
                Draw Calls: ${stats.drawCalls}<br>
                Sprites: ${stats.sprites}<br>
                Memory: ${stats.memoryMB}MB
            `;
        }
        
        // System status
        const systemsElement = document.getElementById('debug-systems');
        if (systemsElement) {
            let statusHTML = '';
            for (const [name, status] of this.systemStatus) {
                const statusColor = status.status === 'active' ? '#00ff00' : '#ff0000';
                statusHTML += `<span style="color: ${statusColor}">●</span> ${name}<br>`;
            }
            systemsElement.innerHTML = statusHTML;
        }
        
        // Active effects
        const effectsElement = document.getElementById('debug-effects');
        if (effectsElement) {
            const effectStats = this.systems.visualFeedback?.getStats() || {};
            effectsElement.innerHTML = `
                Active: ${effectStats.activeEffects || 0}<br>
                Pool Hits: ${effectStats.poolHits || 0}<br>
                Pool Misses: ${effectStats.poolMisses || 0}<br>
                Created: ${effectStats.effectsCreated || 0}<br>
                Destroyed: ${effectStats.effectsDestroyed || 0}
            `;
        }
    }
    
    /**
     * Toggle debug interface visibility
     */
    toggleDebugInterface() {
        if (!this.debugUI) return;
        
        this.showDebugStats = !this.showDebugStats;
        this.debugUI.style.display = this.showDebugStats ? 'block' : 'none';
        
        console.log(`🐛 Debug interface ${this.showDebugStats ? 'shown' : 'hidden'}`);
    }
    
    /**
     * Setup accessibility features
     */
    setupAccessibilityFeatures() {
        if (!this.config.enableAccessibilityMode) return;
        
        console.log('♿ Setting up accessibility features...');
        
        // Check for user preferences
        this.detectAccessibilityPreferences();
        
        // Apply accessibility modifications
        this.applyAccessibilityModifications();
        
        console.log('✅ Accessibility features configured');
    }
    
    /**
     * Detect accessibility preferences
     */
    detectAccessibilityPreferences() {
        // Check for reduced motion preference
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            this.accessibility.reduceMotion = true;
            console.log('🔄 Reduced motion detected');
        }
        
        // Check for high contrast preference
        if (window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches) {
            this.accessibility.highContrast = true;
            console.log('🎨 High contrast detected');
        }
    }
    
    /**
     * Apply accessibility modifications
     */
    applyAccessibilityModifications() {
        if (this.accessibility.reduceMotion) {
            // Disable animations for reduced motion
            this.config.qualitySettings.animations = false;
            this.systems.selectionRenderer?.setAnimationsEnabled(false);
            this.systems.visualFeedback?.updateConfig({ enableEffects: false });
        }
        
        if (this.accessibility.highContrast) {
            // Apply high contrast colors
            // This would modify color schemes across all UI systems
            console.log('🎨 High contrast mode applied');
        }
    }
    
    /**
     * Apply platform-specific optimizations
     */
    applyPlatformOptimizations() {
        console.log(`🔧 Applying ${this.config.isMobile ? 'mobile' : 'desktop'} optimizations...`);
        
        if (this.config.isMobile) {
            // Mobile optimizations
            this.config.qualitySettings.effects = 'medium';
            
            // Reduce update frequencies
            this.systems.uiUpdateManager?.setUpdateRate(8);
            
            // Disable expensive features
            this.systems.visualFeedback?.updateConfig({
                enableScreenShake: false,
                particlePoolSize: 50,
                maxParticles: 100
            });
            
            console.log('📱 Mobile optimizations applied');
        } else {
            // Desktop optimizations
            console.log('💻 Desktop optimizations applied');
        }
    }
    
    /**
     * Detect if running on mobile device
     */
    detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (navigator.maxTouchPoints && navigator.maxTouchPoints > 1);
    }
    
    /**
     * Handle selection input
     */
    handleSelectionInput(event) {
        // Process selection through systems
        const worldPos = { x: event.worldX, y: event.worldY };
        
        // Check if clicking on an entity
        const clickedEntity = this.getEntityAtPosition(worldPos.x, worldPos.y);
        
        if (clickedEntity) {
            this.selectEntity(clickedEntity, event.shiftKey);
        } else if (!event.shiftKey) {
            this.clearSelection();
        }
    }
    
    /**
     * Get entity at world position
     */
    getEntityAtPosition(x, y) {
        if (!this.world) return null;
        
        for (const entity of this.world.entities) {
            if (!entity.active) continue;
            
            const transform = entity.getComponent('TransformComponent');
            const selectable = entity.getComponent('SelectableComponent');
            
            if (transform && selectable) {
                const distance = Math.hypot(transform.x - x, transform.y - y);
                if (distance <= selectable.selectableRadius) {
                    return entity;
                }
            }
        }
        
        return null;
    }
    
    /**
     * Select entity
     */
    selectEntity(entity, addToSelection = false) {
        // Emit selection event
        const selectionEvent = new CustomEvent('entity:selected', {
            detail: { entity: entity, addToSelection: addToSelection }
        });
        window.dispatchEvent(selectionEvent);
        
        // Update selection renderer
        const transform = entity.getComponent('TransformComponent');
        const health = entity.getComponent('HealthComponent');
        
        if (transform) {
            this.systems.selectionRenderer?.showSelection(entity.id, transform, health);
        }
    }
    
    /**
     * Clear all selections
     */
    clearSelection() {
        // Clear selection renderer
        this.systems.selectionRenderer?.clearAll();
        
        // Emit clear event
        const clearEvent = new CustomEvent('selection:cleared');
        window.dispatchEvent(clearEvent);
    }
    
    /**
     * Update all UI systems
     */
    update(deltaTime) {
        if (this.isDestroyed) return;
        
        // Update systems that need manual updates
        this.systems.selectionRenderer?.update(deltaTime);
        this.systems.buildingPlacement?.update(deltaTime);
        this.systems.visualFeedback?.update(deltaTime);
        
        // Update performance tracking
        this.performance.lastFrameTime = performance.now();
    }
    
    /**
     * Get comprehensive performance statistics
     */
    getPerformanceStats() {
        const appStats = this.app.getStats ? this.app.getStats() : {};
        
        return {
            fps: this.performance.fps,
            frameTime: this.performance.frameTime,
            drawCalls: appStats.drawCalls || 0,
            sprites: appStats.spriteCount || 0,
            memoryMB: this.getMemoryUsage(),
            systems: {
                selection: this.systems.selectionRenderer?.getStats() || {},
                input: this.systems.inputBatcher?.getStats() || {},
                building: this.systems.buildingPlacement?.isInPlacementMode() || false,
                resource: this.systems.resourceEconomy?.getStats() || {},
                effects: this.systems.visualFeedback?.getStats() || {}
            }
        };
    }
    
    /**
     * Get approximate memory usage
     */
    getMemoryUsage() {
        if (performance.memory) {
            return Math.round(performance.memory.usedJSHeapSize / (1024 * 1024));
        }
        return 0;
    }
    
    /**
     * Reset quality settings to default
     */
    resetQualitySettings() {
        this.config.qualitySettings = {
            effects: 'high',
            animations: true,
            particles: true
        };
        
        // Update all systems
        this.systems.selectionRenderer?.setAnimationsEnabled(true);
        this.systems.visualFeedback?.updateConfig({ effectQuality: 'high' });
        
        console.log('⚙️  Quality settings reset to defaults');
    }
    
    /**
     * Get system status for external monitoring
     */
    getSystemStatus() {
        return Object.fromEntries(this.systemStatus);
    }
    
    /**
     * Force update all UI systems
     */
    forceUpdate() {
        this.systems.resourceEconomy?.forceUpdate();
        this.systems.uiUpdateManager?.forceUpdate();
        
        console.log('🔄 Forced UI update');
    }
    
    /**
     * Destroy all UI systems
     */
    destroy() {
        if (this.isDestroyed) return;
        
        console.log('🗑️ Destroying UIManager...');
        this.isDestroyed = true;
        
        // Destroy all systems
        Object.values(this.systems).forEach(system => {
            if (system && system.destroy) {
                try {
                    system.destroy();
                } catch (error) {
                    console.error('❌ Error destroying UI system:', error);
                }
            }
        });
        
        // Remove debug UI
        if (this.debugUI && this.debugUI.parentNode) {
            this.debugUI.parentNode.removeChild(this.debugUI);
        }
        
        // Clear data structures
        this.systemStatus.clear();
        this.eventRoutes.clear();
        
        console.log('✅ UIManager destroyed successfully');
    }
}