/**
 * VisualFeedbackSystem - Comprehensive visual feedback manager
 * 
 * Centralized system for managing all visual feedback in the RTS game,
 * including unit selection, movement commands, building construction,
 * combat effects, and system notifications. Coordinates with all other
 * UI systems for consistent, efficient visual communication.
 * 
 * Features:
 * - Unified command visualization (movement, attack, build)
 * - Dynamic effect pooling and lifecycle management
 * - Audio-visual synchronization
 * - Context-sensitive feedback
 * - Performance-optimized particle systems
 * - Screen-space and world-space effects
 * - Accessibility considerations
 * - Mobile touch feedback
 */

import * as PIXI from "pixi.js";

export class VisualFeedbackSystem {
    constructor(app, selectionRenderer, options = {}) {
        this.app = app;
        this.selectionRenderer = selectionRenderer;
        this.renderer = app.renderer;
        
        // Configuration
        this.config = {
            enableEffects: options.enableEffects !== false,
            enableSound: options.enableSound !== false,
            effectQuality: options.effectQuality || "high", // high, medium, low
            maxParticles: options.maxParticles || 500,
            particlePoolSize: options.particlePoolSize || 200,
            fadeOutDuration: options.fadeOutDuration || 1000,
            pulseSpeed: options.pulseSpeed || 2.0,
            enableScreenShake: options.enableScreenShake !== false,
            accessibilityMode: options.accessibilityMode || false
        };
        
        // Effect containers organized by layer
        this.containers = {
            worldEffects: new PIXI.Container(),      // World-space effects (explosions, impacts)
            commandEffects: new PIXI.Container(),   // Command indicators (move, attack targets)
            unitEffects: new PIXI.Container(),      // Unit-attached effects (muzzle flashes, etc.)
            buildingEffects: new PIXI.Container(),  // Building effects (construction, damage)
            uiEffects: new PIXI.Container(),        // UI effects (notifications, highlights)
            screenEffects: new PIXI.Container()     // Screen-space effects (overlays, transitions)
        };
        
        // Add containers to stage in proper order
        Object.values(this.containers).forEach((container, index) => {
            container.zIndex = 100 + index * 10;
            container.sortableChildren = true;
            app.stage.addChild(container);
        });
        
        // Effect pools for performance
        this.effectPools = {
            particles: [],
            sprites: [],
            graphics: [],
            texts: []
        };
        
        // Active effects tracking
        this.activeEffects = new Map();
        this.commandMarkers = new Map();
        this.buildingEffects = new Map();
        this.screenEffects = new Map();
        
        // Effect templates
        this.effectTemplates = new Map();
        
        // Audio system reference (if available)
        this.audioSystem = null;
        
        // Screen shake state
        this.screenShake = {
            active: false,
            intensity: 0,
            duration: 0,
            elapsed: 0,
            offsetX: 0,
            offsetY: 0
        };
        
        // Performance tracking
        this.stats = {
            activeEffects: 0,
            particlesRendered: 0,
            poolHits: 0,
            poolMisses: 0,
            effectsCreated: 0,
            effectsDestroyed: 0
        };
        
        // Animation frame ID for cleanup
        this.animationId = null;
        
        this.isDestroyed = false;
        
        this.init();
    }
    
    /**
     * Initialize the visual feedback system
     */
    init() {
        console.log("✨ Initializing VisualFeedbackSystem...");
        
        // Create effect templates
        this.createEffectTemplates();
        
        // Initialize effect pools
        this.initializeEffectPools();
        
        // Start update loop
        this.startUpdateLoop();
        
        console.log(`✅ VisualFeedbackSystem initialized - Quality: ${this.config.effectQuality}`);
    }
    
    /**
     * Create reusable effect templates
     */
    createEffectTemplates() {
        // Movement command marker
        this.effectTemplates.set("moveCommand", {
            type: "graphics",
            color: 0x00ff00,
            size: 20,
            duration: 2000,
            animation: "expand_fade"
        });
        
        // Attack command marker
        this.effectTemplates.set("attackCommand", {
            type: "graphics",
            color: 0xff0000,
            size: 25,
            duration: 2500,
            animation: "pulse_fade"
        });
        
        // Building placement success
        this.effectTemplates.set("buildingPlaced", {
            type: "particles",
            color: 0x00ff00,
            count: 20,
            duration: 3000,
            animation: "burst_up"
        });
        
        // Unit damage indicator
        this.effectTemplates.set("unitDamage", {
            type: "text",
            color: 0xff0000,
            fontSize: 16,
            duration: 1500,
            animation: "float_up"
        });
        
        // Resource collection
        this.effectTemplates.set("resourceGain", {
            type: "text",
            color: 0xffff00,
            fontSize: 14,
            duration: 2000,
            animation: "float_up"
        });
        
        // Construction progress
        this.effectTemplates.set("construction", {
            type: "particles",
            color: 0xffffff,
            count: 5,
            duration: 500,
            animation: "sparkle"
        });
        
        // Unit selection confirmation
        this.effectTemplates.set("selectionPulse", {
            type: "graphics",
            color: 0x00ffff,
            size: 40,
            duration: 800,
            animation: "pulse_once"
        });
        
        // Alert/notification
        this.effectTemplates.set("alert", {
            type: "graphics",
            color: 0xff8800,
            size: 60,
            duration: 4000,
            animation: "warning_pulse"
        });
        
        console.log(`📋 Created ${this.effectTemplates.size} effect templates`);
    }
    
    /**
     * Initialize effect pools
     */
    initializeEffectPools() {
        const poolSize = this.config.particlePoolSize;
        
        // Particle pool
        for (let i = 0; i < poolSize / 4; i++) {
            const particle = new PIXI.Graphics();
            particle.visible = false;
            particle.userData = { pooled: true };
            this.effectPools.particles.push(particle);
        }
        
        // Sprite pool
        for (let i = 0; i < poolSize / 4; i++) {
            const sprite = new PIXI.Sprite();
            sprite.visible = false;
            sprite.userData = { pooled: true };
            this.effectPools.sprites.push(sprite);
        }
        
        // Graphics pool
        for (let i = 0; i < poolSize / 4; i++) {
            const graphics = new PIXI.Graphics();
            graphics.visible = false;
            graphics.userData = { pooled: true };
            this.effectPools.graphics.push(graphics);
        }
        
        // Text pool
        for (let i = 0; i < poolSize / 4; i++) {
            const text = new PIXI.Text("", { fill: 0xffffff, fontSize: 12 });
            text.visible = false;
            text.userData = { pooled: true };
            this.effectPools.texts.push(text);
        }
        
        // Add pooled objects to appropriate containers
        this.effectPools.particles.forEach(p => this.containers.worldEffects.addChild(p));
        this.effectPools.sprites.forEach(s => this.containers.worldEffects.addChild(s));
        this.effectPools.graphics.forEach(g => this.containers.commandEffects.addChild(g));
        this.effectPools.texts.forEach(t => this.containers.uiEffects.addChild(t));
        
        console.log(`💾 Initialized effect pools with ${poolSize} objects`);
    }
    
    /**
     * Get object from pool or create new one
     */
    getFromPool(type) {
        const pool = this.effectPools[type];
        if (!pool) return null;
        
        // Find available object in pool
        const available = pool.find(obj => !obj.visible);
        
        if (available) {
            this.stats.poolHits++;
            this.resetPooledObject(available);
            return available;
        } else {
            // Pool exhausted, create new object
            this.stats.poolMisses++;
            console.warn(`🔄 Effect pool exhausted for ${type}, creating new object`);
            return this.createNewPoolObject(type);
        }
    }
    
    /**
     * Create new pool object when pool is exhausted
     */
    createNewPoolObject(type) {
        let obj;
        
        switch (type) {
        case "particles":
            obj = new PIXI.Graphics();
            this.containers.worldEffects.addChild(obj);
            this.effectPools.particles.push(obj);
            break;
        case "sprites":
            obj = new PIXI.Sprite();
            this.containers.worldEffects.addChild(obj);
            this.effectPools.sprites.push(obj);
            break;
        case "graphics":
            obj = new PIXI.Graphics();
            this.containers.commandEffects.addChild(obj);
            this.effectPools.graphics.push(obj);
            break;
        case "texts":
            obj = new PIXI.Text("", { fill: 0xffffff, fontSize: 12 });
            this.containers.uiEffects.addChild(obj);
            this.effectPools.texts.push(obj);
            break;
        default:
            return null;
        }
        
        obj.userData = { pooled: true };
        return obj;
    }
    
    /**
     * Reset pooled object to default state
     */
    resetPooledObject(obj) {
        obj.visible = false;
        obj.alpha = 1;
        obj.scale.set(1, 1);
        obj.rotation = 0;
        obj.position.set(0, 0);
        obj.tint = 0xffffff;
        
        if (obj instanceof PIXI.Graphics) {
            obj.clear();
        }
        
        if (obj instanceof PIXI.Text) {
            obj.text = "";
        }
    }
    
    /**
     * Return object to pool
     */
    returnToPool(obj) {
        if (obj && obj.userData && obj.userData.pooled) {
            this.resetPooledObject(obj);
        }
    }
    
    /**
     * Start the update loop
     */
    startUpdateLoop() {
        const updateLoop = (timestamp) => {
            if (this.isDestroyed) return;
            
            this.update(timestamp);
            this.animationId = requestAnimationFrame(updateLoop);
        };
        
        this.animationId = requestAnimationFrame(updateLoop);
    }
    
    /**
     * Update all active effects
     */
    update(timestamp) {
        // Update screen shake
        this.updateScreenShake();
        
        // Update active effects
        this.updateActiveEffects(timestamp);
        
        // Update performance stats
        this.stats.activeEffects = this.activeEffects.size;
    }
    
    /**
     * Update screen shake effect
     */
    updateScreenShake() {
        if (!this.screenShake.active) return;
        
        this.screenShake.elapsed += 16; // Assume 60fps
        
        if (this.screenShake.elapsed >= this.screenShake.duration) {
            // Stop screen shake
            this.screenShake.active = false;
            this.screenShake.offsetX = 0;
            this.screenShake.offsetY = 0;
            
            // Reset camera position
            if (this.app.stage) {
                this.app.stage.position.set(0, 0);
            }
        } else {
            // Calculate shake intensity
            const progress = this.screenShake.elapsed / this.screenShake.duration;
            const intensity = this.screenShake.intensity * (1 - progress);
            
            // Generate random offset
            this.screenShake.offsetX = (Math.random() - 0.5) * intensity;
            this.screenShake.offsetY = (Math.random() - 0.5) * intensity;
            
            // Apply shake to stage
            if (this.app.stage) {
                this.app.stage.position.set(this.screenShake.offsetX, this.screenShake.offsetY);
            }
        }
    }
    
    /**
     * Update all active effects
     */
    updateActiveEffects(timestamp) {
        const effectsToRemove = [];
        
        for (const [effectId, effect] of this.activeEffects) {
            const elapsed = timestamp - effect.startTime;
            const progress = elapsed / effect.duration;
            
            if (progress >= 1) {
                // Effect finished
                effectsToRemove.push(effectId);
                this.finalizeEffect(effect);
            } else {
                // Update effect animation
                this.updateEffect(effect, progress);
            }
        }
        
        // Remove finished effects
        for (const effectId of effectsToRemove) {
            this.activeEffects.delete(effectId);
            this.stats.effectsDestroyed++;
        }
    }
    
    /**
     * Update individual effect
     */
    updateEffect(effect, progress) {
        const obj = effect.object;
        if (!obj) return;
        
        switch (effect.animation) {
        case "expand_fade":
            obj.scale.set(1 + progress * 2);
            obj.alpha = 1 - progress;
            break;
                
        case "pulse_fade":
            const pulse = Math.sin(progress * Math.PI * 4);
            obj.scale.set(1 + pulse * 0.2);
            obj.alpha = 1 - progress;
            break;
                
        case "float_up":
            obj.y = effect.startY - (progress * 50);
            obj.alpha = 1 - Math.pow(progress, 2);
            break;
                
        case "burst_up":
            if (obj instanceof PIXI.Graphics) {
                // Particle burst animation
                obj.alpha = 1 - progress;
                obj.scale.set(1 + progress);
            }
            break;
                
        case "pulse_once":
            const oncePulse = Math.sin(progress * Math.PI);
            obj.scale.set(1 + oncePulse * 0.5);
            obj.alpha = 1 - Math.pow(progress, 3);
            break;
                
        case "warning_pulse":
            const warningPulse = Math.sin(progress * Math.PI * 8) * 0.5 + 0.5;
            obj.alpha = warningPulse * (1 - progress);
            break;
                
        case "sparkle":
            obj.rotation += 0.2;
            obj.alpha = Math.sin(progress * Math.PI);
            break;
        }
    }
    
    /**
     * Finalize and cleanup effect
     */
    finalizeEffect(effect) {
        const obj = effect.object;
        if (!obj) return;
        
        // Return to pool
        this.returnToPool(obj);
        
        // Play completion sound if configured
        if (effect.sound && this.audioSystem) {
            this.audioSystem.play(effect.sound);
        }
    }
    
    /**
     * Show movement command visual feedback
     */
    showMoveCommand(x, y, queued = false) {
        if (!this.config.enableEffects) return;
        
        const template = this.effectTemplates.get("moveCommand");
        const obj = this.getFromPool("graphics");
        
        if (obj) {
            // Draw command marker
            obj.clear();
            obj.lineStyle(3, template.color, 0.8);
            obj.drawCircle(0, 0, template.size);
            
            // Add inner cross
            obj.moveTo(-10, 0);
            obj.lineTo(10, 0);
            obj.moveTo(0, -10);
            obj.lineTo(0, 10);
            
            obj.position.set(x, y);
            obj.visible = true;
            
            // Create effect data
            const effectId = `move_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: template.animation,
                duration: template.duration,
                startTime: performance.now(),
                startY: y,
                sound: "move_command"
            });
            
            this.stats.effectsCreated++;
        }
        
        // Add queued indicator if this is a queued command
        if (queued) {
            this.showQueuedCommandIndicator(x, y);
        }
        
        // Screen space ripple effect
        this.showScreenRipple(x, y, 0x00ff00);
    }
    
    /**
     * Show attack command visual feedback
     */
    showAttackCommand(x, y, targetEntity = null) {
        if (!this.config.enableEffects) return;
        
        const template = this.effectTemplates.get("attackCommand");
        const obj = this.getFromPool("graphics");
        
        if (obj) {
            // Draw attack marker
            obj.clear();
            obj.lineStyle(4, template.color, 1);
            obj.drawPolygon([
                -15, -10,  // Top left
                15, -10,   // Top right
                20, 0,     // Right point
                15, 10,    // Bottom right
                -15, 10,   // Bottom left
                -20, 0     // Left point
            ]);
            
            obj.position.set(x, y);
            obj.visible = true;
            
            const effectId = `attack_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: template.animation,
                duration: template.duration,
                startTime: performance.now(),
                sound: "attack_command"
            });
            
            this.stats.effectsCreated++;
        }
        
        // Target lock indicator if targeting specific entity
        if (targetEntity) {
            this.showTargetLock(targetEntity);
        }
        
        // Screen space crosshair
        this.showScreenCrosshair(x, y);
    }
    
    /**
     * Show building placement success feedback
     */
    showBuildingPlaced(x, y, buildingData) {
        if (!this.config.enableEffects) return;
        
        // Create construction completion effect
        const template = this.effectTemplates.get("buildingPlaced");
        
        // Particle burst effect
        for (let i = 0; i < template.count; i++) {
            const particle = this.getFromPool("particles");
            if (particle) {
                particle.clear();
                particle.beginFill(template.color, 0.8);
                particle.drawCircle(0, 0, 3);
                particle.endFill();
                
                // Random direction and speed
                const angle = (Math.PI * 2 * i) / template.count;
                const speed = 50 + Math.random() * 30;
                const targetX = x + Math.cos(angle) * speed;
                const targetY = y + Math.sin(angle) * speed - Math.random() * 20;
                
                particle.position.set(x, y);
                particle.visible = true;
                
                const effectId = `particle_${Date.now()}_${i}`;
                this.activeEffects.set(effectId, {
                    id: effectId,
                    object: particle,
                    animation: "burst_up",
                    duration: template.duration,
                    startTime: performance.now(),
                    startY: y,
                    targetX: targetX,
                    targetY: targetY
                });
            }
        }
        
        // Success text
        this.showFloatingText(x, y, `${buildingData.name} Completed!`, 0x00ff00);
        
        // Screen shake for larger buildings
        if (buildingData.width >= 2 || buildingData.height >= 2) {
            this.triggerScreenShake(5, 300);
        }
        
        this.stats.effectsCreated += template.count + 1;
    }
    
    /**
     * Show unit damage feedback
     */
    showUnitDamage(entity, damage, damageType = "normal") {
        if (!this.config.enableEffects) return;
        
        const transform = entity.getComponent("TransformComponent");
        if (!transform) return;
        
        // Damage number
        const color = damageType === "critical" ? 0xff0000 : 
            damageType === "heal" ? 0x00ff00 : 0xffffff;
        
        this.showFloatingText(
            transform.x + (Math.random() - 0.5) * 20,
            transform.y - 20,
            `-${damage}`,
            color,
            { fontSize: damageType === "critical" ? 18 : 14 }
        );
        
        // Impact effect
        this.showImpactEffect(transform.x, transform.y, damageType);
        
        // Screen shake for critical hits
        if (damageType === "critical") {
            this.triggerScreenShake(3, 200);
        }
    }
    
    /**
     * Show resource collection feedback
     */
    showResourceGain(x, y, amount, resourceType = "credits") {
        if (!this.config.enableEffects) return;
        
        const colors = {
            credits: 0xffff00,
            power: 0x00ffff,
            tiberium: 0x00ff00
        };
        
        const prefix = resourceType === "credits" ? "$" : "";
        this.showFloatingText(x, y, `+${prefix}${amount}`, colors[resourceType] || 0xffffff);
        
        // Small sparkle effect
        this.showSparkleEffect(x, y, colors[resourceType] || 0xffffff);
    }
    
    /**
     * Show construction progress feedback
     */
    showConstructionProgress(x, y, progress) {
        if (!this.config.enableEffects || Math.random() > 0.3) return; // Throttle
        
        const obj = this.getFromPool("particles");
        if (obj) {
            obj.clear();
            obj.beginFill(0xffffff, 0.6);
            obj.drawCircle(0, 0, 2);
            obj.endFill();
            
            // Random position around construction site
            const offsetX = (Math.random() - 0.5) * 60;
            const offsetY = (Math.random() - 0.5) * 60;
            
            obj.position.set(x + offsetX, y + offsetY);
            obj.visible = true;
            
            const effectId = `construction_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "sparkle",
                duration: 500,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show selection confirmation pulse
     */
    showSelectionPulse(entity) {
        if (!this.config.enableEffects) return;
        
        const transform = entity.getComponent("TransformComponent");
        if (!transform) return;
        
        const template = this.effectTemplates.get("selectionPulse");
        const obj = this.getFromPool("graphics");
        
        if (obj) {
            obj.clear();
            obj.lineStyle(3, template.color, 0.8);
            obj.drawCircle(0, 0, template.size);
            
            obj.position.set(transform.x, transform.y);
            obj.visible = true;
            
            const effectId = `selection_${Date.now()}_${entity.id}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: template.animation,
                duration: template.duration,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show alert/warning effect
     */
    showAlert(x, y, message, alertType = "warning") {
        if (!this.config.enableEffects) return;
        
        const colors = {
            warning: 0xff8800,
            error: 0xff0000,
            info: 0x00aaff
        };
        
        const template = this.effectTemplates.get("alert");
        const obj = this.getFromPool("graphics");
        
        if (obj) {
            obj.clear();
            obj.lineStyle(4, colors[alertType] || template.color, 1);
            obj.drawCircle(0, 0, template.size);
            
            // Add warning symbol
            obj.lineStyle(6, colors[alertType] || template.color, 1);
            obj.moveTo(0, -20);
            obj.lineTo(0, 0);
            obj.drawCircle(0, 15, 3);
            
            obj.position.set(x, y);
            obj.visible = true;
            
            const effectId = `alert_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "warning_pulse",
                duration: template.duration,
                startTime: performance.now(),
                sound: `alert_${alertType}`
            });
        }
        
        // Show message text
        if (message) {
            this.showFloatingText(x, y - 80, message, colors[alertType], {
                fontSize: 16,
                duration: 4000
            });
        }
    }
    
    /**
     * Show floating text effect
     */
    showFloatingText(x, y, text, color = 0xffffff, options = {}) {
        const obj = this.getFromPool("texts");
        if (!obj) return;
        
        obj.text = text;
        obj.style.fill = color;
        obj.style.fontSize = options.fontSize || 14;
        obj.style.fontWeight = options.fontWeight || "bold";
        obj.style.stroke = 0x000000;
        obj.style.strokeThickness = 2;
        
        obj.anchor.set(0.5);
        obj.position.set(x, y);
        obj.visible = true;
        
        const effectId = `text_${Date.now()}_${Math.random()}`;
        this.activeEffects.set(effectId, {
            id: effectId,
            object: obj,
            animation: "float_up",
            duration: options.duration || 2000,
            startTime: performance.now(),
            startY: y
        });
        
        this.stats.effectsCreated++;
    }
    
    /**
     * Show impact effect at position
     */
    showImpactEffect(x, y, type = "normal") {
        if (!this.config.enableEffects) return;
        
        const colors = {
            normal: 0xffffff,
            explosion: 0xff4400,
            critical: 0xff0000,
            heal: 0x00ff00
        };
        
        // Create radial impact lines
        const obj = this.getFromPool("graphics");
        if (obj) {
            obj.clear();
            obj.lineStyle(3, colors[type] || colors.normal, 1);
            
            const lineCount = type === "explosion" ? 12 : 8;
            for (let i = 0; i < lineCount; i++) {
                const angle = (Math.PI * 2 * i) / lineCount;
                const length = type === "explosion" ? 25 : 15;
                
                obj.moveTo(0, 0);
                obj.lineTo(Math.cos(angle) * length, Math.sin(angle) * length);
            }
            
            obj.position.set(x, y);
            obj.visible = true;
            
            const effectId = `impact_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "expand_fade",
                duration: type === "explosion" ? 1000 : 600,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show sparkle effect
     */
    showSparkleEffect(x, y, color = 0xffffff) {
        if (!this.config.enableEffects) return;
        
        for (let i = 0; i < 5; i++) {
            const obj = this.getFromPool("particles");
            if (obj) {
                obj.clear();
                obj.beginFill(color, 0.8);
                obj.drawPolygon([
                    0, -4,    // Top
                    2, -1,    // Top right
                    4, 0,     // Right
                    2, 1,     // Bottom right
                    0, 4,     // Bottom
                    -2, 1,    // Bottom left
                    -4, 0,    // Left
                    -2, -1    // Top left
                ]);
                obj.endFill();
                
                const offsetX = (Math.random() - 0.5) * 30;
                const offsetY = (Math.random() - 0.5) * 30;
                
                obj.position.set(x + offsetX, y + offsetY);
                obj.visible = true;
                
                const effectId = `sparkle_${Date.now()}_${i}`;
                this.activeEffects.set(effectId, {
                    id: effectId,
                    object: obj,
                    animation: "sparkle",
                    duration: 800 + Math.random() * 400,
                    startTime: performance.now()
                });
            }
        }
    }
    
    /**
     * Show queued command indicator
     */
    showQueuedCommandIndicator(x, y) {
        const obj = this.getFromPool("graphics");
        if (obj) {
            obj.clear();
            obj.lineStyle(2, 0xffff00, 0.6);
            obj.drawCircle(0, 0, 12);
            obj.beginFill(0xffff00, 0.3);
            obj.drawCircle(0, 0, 8);
            obj.endFill();
            
            obj.position.set(x, y);
            obj.visible = true;
            
            const effectId = `queued_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "pulse_fade",
                duration: 1500,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show screen-space ripple effect
     */
    showScreenRipple(worldX, worldY, color) {
        // Convert world coordinates to screen space
        // This would typically use the camera system
        // For now, use world coordinates directly
        
        const obj = this.getFromPool("graphics");
        if (obj) {
            obj.clear();
            obj.lineStyle(2, color, 0.4);
            obj.drawCircle(0, 0, 5);
            
            obj.position.set(worldX, worldY);
            obj.visible = true;
            
            const effectId = `ripple_${Date.now()}_${Math.random()}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "expand_fade",
                duration: 1000,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show target lock indicator
     */
    showTargetLock(entity) {
        const transform = entity.getComponent("TransformComponent");
        if (!transform) return;
        
        const obj = this.getFromPool("graphics");
        if (obj) {
            obj.clear();
            obj.lineStyle(3, 0xff0000, 1);
            
            // Draw targeting brackets
            const size = 25;
            // Top-left bracket
            obj.moveTo(-size, -size);
            obj.lineTo(-size + 8, -size);
            obj.moveTo(-size, -size);
            obj.lineTo(-size, -size + 8);
            
            // Top-right bracket
            obj.moveTo(size, -size);
            obj.lineTo(size - 8, -size);
            obj.moveTo(size, -size);
            obj.lineTo(size, -size + 8);
            
            // Bottom-left bracket
            obj.moveTo(-size, size);
            obj.lineTo(-size + 8, size);
            obj.moveTo(-size, size);
            obj.lineTo(-size, size - 8);
            
            // Bottom-right bracket
            obj.moveTo(size, size);
            obj.lineTo(size - 8, size);
            obj.moveTo(size, size);
            obj.lineTo(size, size - 8);
            
            obj.position.set(transform.x, transform.y);
            obj.visible = true;
            
            const effectId = `target_${Date.now()}_${entity.id}`;
            this.activeEffects.set(effectId, {
                id: effectId,
                object: obj,
                animation: "pulse_fade",
                duration: 3000,
                startTime: performance.now()
            });
        }
    }
    
    /**
     * Show screen crosshair
     */
    showScreenCrosshair(worldX, worldY) {
        // Implementation would show crosshair in screen space
        console.debug(`🎯 Crosshair at world position (${worldX}, ${worldY})`);
    }
    
    /**
     * Trigger screen shake effect
     */
    triggerScreenShake(intensity = 5, duration = 500) {
        if (!this.config.enableScreenShake) return;
        
        this.screenShake = {
            active: true,
            intensity: intensity,
            duration: duration,
            elapsed: 0,
            offsetX: 0,
            offsetY: 0
        };
        
        console.debug(`📳 Screen shake: ${intensity} intensity for ${duration}ms`);
    }
    
    /**
     * Set audio system reference
     */
    setAudioSystem(audioSystem) {
        this.audioSystem = audioSystem;
        console.log("🔊 Audio system connected to visual feedback");
    }
    
    /**
     * Clear all effects
     */
    clearAllEffects() {
        // Return all active effects to pools
        for (const [effectId, effect] of this.activeEffects) {
            this.returnToPool(effect.object);
        }
        
        this.activeEffects.clear();
        this.commandMarkers.clear();
        this.buildingEffects.clear();
        this.screenEffects.clear();
        
        console.log("🧹 All visual effects cleared");
    }
    
    /**
     * Get performance statistics
     */
    getStats() {
        return {
            ...this.stats,
            poolUtilization: {
                particles: this.effectPools.particles.filter(p => p.visible).length,
                sprites: this.effectPools.sprites.filter(s => s.visible).length,
                graphics: this.effectPools.graphics.filter(g => g.visible).length,
                texts: this.effectPools.texts.filter(t => t.visible).length
            },
            screenShakeActive: this.screenShake.active
        };
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        
        // Handle quality changes
        if (newConfig.effectQuality) {
            this.adjustQualitySettings();
        }
        
        console.log("⚙️  VisualFeedbackSystem config updated");
    }
    
    /**
     * Adjust settings based on quality level
     */
    adjustQualitySettings() {
        switch (this.config.effectQuality) {
        case "low":
            this.config.maxParticles = 100;
            this.config.enableScreenShake = false;
            break;
        case "medium":
            this.config.maxParticles = 300;
            this.config.enableScreenShake = true;
            break;
        case "high":
            this.config.maxParticles = 500;
            this.config.enableScreenShake = true;
            break;
        }
    }
    
    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this.isDestroyed) return;
        
        console.log("🗑️ Destroying VisualFeedbackSystem...");
        this.isDestroyed = true;
        
        // Cancel animation loop
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        // Clear all effects
        this.clearAllEffects();
        
        // Destroy all pooled objects
        Object.values(this.effectPools).forEach(pool => {
            pool.forEach(obj => {
                if (obj.destroy) {
                    obj.destroy();
                }
            });
        });
        
        // Remove containers from stage
        Object.values(this.containers).forEach(container => {
            if (container.parent) {
                container.parent.removeChild(container);
            }
            container.destroy({ children: true });
        });
        
        // Clear data structures
        this.effectTemplates.clear();
        this.activeEffects.clear();
        this.commandMarkers.clear();
        this.buildingEffects.clear();
        this.screenEffects.clear();
        
        console.log("✅ VisualFeedbackSystem destroyed successfully");
    }
}