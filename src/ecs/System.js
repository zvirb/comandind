import * as PIXI from "pixi.js";
import { 
    TransformComponent, 
    VelocityComponent, 
    SpriteComponent, 
    HealthComponent,
    MovementComponent,
    CombatComponent,
    AIComponent
} from "./Component.js";

/**
 * Base System class
 * Systems contain the logic that operates on entities with specific components
 */
export class System {
    constructor(world) {
        this.world = world;
        this.entities = new Set();
        this.entityReferences = new WeakSet(); // Weak references to prevent memory leaks
        this.requiredComponents = [];
        this.priority = 0;
        this.destroyed = false;
    }
    
    /**
     * Check if entity matches system requirements
     */
    matchesEntity(entity) {
        return this.requiredComponents.every(ComponentType => 
            entity.hasComponent(ComponentType)
        );
    }
    
    /**
     * Add entity to system
     */
    addEntity(entity) {
        if (this.destroyed) return;
        
        if (!entity || !entity.isValid()) {
            console.warn(`Attempting to add invalid entity to system ${this.constructor.name}`);
            return;
        }
        
        if (this.matchesEntity(entity)) {
            this.entities.add(entity);
            this.entityReferences.add(entity);
            this.onEntityAdded(entity);
        }
    }
    
    /**
     * Remove entity from system
     */
    removeEntity(entity) {
        if (this.entities.has(entity)) {
            this.entities.delete(entity);
            this.onEntityRemoved(entity);
        }
    }
    
    /**
     * Called when entity is added
     */
    onEntityAdded() {
        // Override in subclasses
    }
    
    /**
     * Called when entity is removed
     */
    onEntityRemoved() {
        // Override in subclasses
    }
    
    /**
     * Update system logic
     */
    update() {
        if (this.destroyed) return;
        
        // Clean up invalid entities before processing
        const invalidEntities = [];
        for (const entity of this.entities) {
            if (!entity || !entity.isValid()) {
                invalidEntities.push(entity);
            }
        }
        
        for (const entity of invalidEntities) {
            this.removeEntity(entity);
        }
        
        // Override in subclasses
    }
    
    /**
     * Render system (if needed)
     */
    render() {
        if (this.destroyed) return;
        
        // Clean up invalid entities before rendering
        const invalidEntities = [];
        for (const entity of this.entities) {
            if (!entity || !entity.isValid()) {
                invalidEntities.push(entity);
            }
        }
        
        for (const entity of invalidEntities) {
            this.removeEntity(entity);
        }
        
        // Override in subclasses
    }
    
    /**
     * Destroy system and cleanup all references
     */
    destroy() {
        if (this.destroyed) return;
        
        this.destroyed = true;
        
        // Cleanup all entity references
        for (const entity of this.entities) {
            this.onEntityRemoved(entity);
        }
        
        this.entities.clear();
        this.world = null;
    }
    
    /**
     * Get system memory usage information
     */
    getMemoryInfo() {
        return {
            name: this.constructor.name,
            entityCount: this.entities.size,
            priority: this.priority,
            destroyed: this.destroyed
        };
    }
}

/**
 * Movement System - Handles entity movement and physics
 */
export class MovementSystem extends System {
    constructor(world) {
        super(world);
        this.requiredComponents = [TransformComponent, VelocityComponent];
        this.priority = 1;
    }
    
    update(deltaTime) {
        super.update(deltaTime); // Call base class cleanup
        
        for (const entity of this.entities) {
            if (!entity.isValid()) continue;
            
            const transform = entity.getComponent(TransformComponent);
            const velocity = entity.getComponent(VelocityComponent);
            
            // Validate components exist
            if (!transform || !velocity) continue;
            
            // Store previous position for interpolation
            transform.storePrevious();
            
            // Apply velocity
            transform.x += velocity.vx * deltaTime;
            transform.y += velocity.vy * deltaTime;
            
            // Apply friction
            velocity.vx *= velocity.friction;
            velocity.vy *= velocity.friction;
            
            // Clamp to max speed
            velocity.clampToMaxSpeed();
        }
    }
}

/**
 * Rendering System - Updates sprite positions and visual properties
 */
export class RenderingSystem extends System {
    constructor(world, pixiStage) {
        super(world);
        this.requiredComponents = [TransformComponent, SpriteComponent];
        this.pixiStage = pixiStage;
        this.priority = 10;
    }
    
    onEntityAdded(entity) {
        const spriteComp = entity.getComponent(SpriteComponent);
        if (spriteComp.texture && !spriteComp.sprite) {
            // Create PIXI sprite
            spriteComp.sprite = new PIXI.Sprite(spriteComp.texture);
            spriteComp.sprite.anchor.set(spriteComp.anchor.x, spriteComp.anchor.y);
            this.pixiStage.addChild(spriteComp.sprite);
        }
    }
    
    onEntityRemoved(entity) {
        const spriteComp = entity.getComponent(SpriteComponent);
        if (spriteComp && spriteComp.sprite) {
            try {
                // Properly cleanup PIXI sprite
                if (this.pixiStage && spriteComp.sprite.parent) {
                    this.pixiStage.removeChild(spriteComp.sprite);
                }
                
                // Destroy sprite resources
                if (spriteComp.sprite.destroy) {
                    spriteComp.sprite.destroy({
                        children: true,
                        texture: false, // Don't destroy shared textures
                        baseTexture: false
                    });
                }
            } catch (error) {
                console.error(`Error cleaning up sprite for entity ${entity.id}:`, error);
            }
            
            spriteComp.sprite = null;
        }
    }
    
    render(interpolation) {
        super.render(interpolation); // Call base class cleanup
        
        for (const entity of this.entities) {
            if (!entity.isValid()) continue;
            
            const transform = entity.getComponent(TransformComponent);
            const spriteComp = entity.getComponent(SpriteComponent);
            
            // Validate components exist
            if (!transform || !spriteComp) continue;
            
            if (spriteComp.sprite && spriteComp.visible) {
                try {
                    // Use interpolation for smooth rendering
                    const interpolated = transform.getInterpolated(interpolation);
                    
                    spriteComp.sprite.x = interpolated.x;
                    spriteComp.sprite.y = interpolated.y;
                    spriteComp.sprite.rotation = interpolated.rotation;
                    spriteComp.sprite.scale.set(transform.scaleX, transform.scaleY);
                    spriteComp.sprite.alpha = spriteComp.alpha;
                    spriteComp.sprite.tint = spriteComp.tint;
                    spriteComp.sprite.visible = true;
                } catch (error) {
                    console.error(`Error rendering entity ${entity.id}:`, error);
                    // Remove broken sprite to prevent further errors
                    if (spriteComp.sprite) {
                        this.onEntityRemoved(entity);
                    }
                }
            }
        }
    }
}

/**
 * Unit Movement System - Handles C&C style unit movement with pathfinding
 */
export class UnitMovementSystem extends System {
    constructor(world) {
        super(world);
        this.requiredComponents = [TransformComponent, MovementComponent, VelocityComponent];
        this.priority = 2;
    }
    
    update(deltaTime) {
        for (const entity of this.entities) {
            if (!entity.active) continue;
            
            const transform = entity.getComponent(TransformComponent);
            const movement = entity.getComponent(MovementComponent);
            const velocity = entity.getComponent(VelocityComponent);
            
            if (!movement.isMoving || movement.path.length === 0) {
                velocity.vx = 0;
                velocity.vy = 0;
                continue;
            }
            
            // Get current path target
            const target = movement.path[movement.pathIndex];
            if (!target) continue;
            
            // Calculate direction to target
            const dx = target.x - transform.x;
            const dy = target.y - transform.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            // Check if reached target
            if (distance <= movement.arrivalDistance) {
                movement.pathIndex++;
                
                // Check if reached end of path
                if (movement.pathIndex >= movement.path.length) {
                    movement.stop();
                    velocity.vx = 0;
                    velocity.vy = 0;
                }
                continue;
            }
            
            // Move towards target
            const speed = movement.speed * deltaTime;
            velocity.vx = (dx / distance) * speed;
            velocity.vy = (dy / distance) * speed;
            
            // Update facing direction
            const angle = Math.atan2(dy, dx);
            transform.rotation = angle;
        }
    }
}

/**
 * Combat System - Handles attacking and damage
 */
export class CombatSystem extends System {
    constructor(world) {
        super(world);
        this.requiredComponents = [TransformComponent, CombatComponent];
        this.priority = 3;
    }
    
    update() {
        for (const entity of this.entities) {
            if (!entity.active) continue;
            const combat = entity.getComponent(CombatComponent);
            
            // Find targets in range
            if (!combat.target || !this.isInRange(entity, combat.target)) {
                combat.target = this.findNearestTarget(entity);
            }
            
            // Attack target if possible
            if (combat.target && combat.canAttack()) {
                this.performAttack(entity, combat.target);
            }
        }
    }
    
    isInRange(attacker, target) {
        if (!target.active) return false;
        
        const attackerTransform = attacker.getComponent(TransformComponent);
        const targetTransform = target.getComponent(TransformComponent);
        const attackerCombat = attacker.getComponent(CombatComponent);
        
        const dx = targetTransform.x - attackerTransform.x;
        const dy = targetTransform.y - attackerTransform.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        return distance <= attackerCombat.range;
    }
    
    findNearestTarget(entity) {
        const transform = entity.getComponent(TransformComponent);
        const combat = entity.getComponent(CombatComponent);
        
        let nearestTarget = null;
        let nearestDistance = combat.range;
        
        // Find enemies in range
        for (const potentialTarget of this.world.entities) {
            if (potentialTarget === entity || !potentialTarget.active) continue;
            
            // Check if target has health (can be damaged)
            if (!potentialTarget.hasComponent(HealthComponent)) continue;
            
            // TODO: Add faction checking here
            
            const targetTransform = potentialTarget.getComponent(TransformComponent);
            const dx = targetTransform.x - transform.x;
            const dy = targetTransform.y - transform.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance <= nearestDistance) {
                nearestTarget = potentialTarget;
                nearestDistance = distance;
            }
        }
        
        return nearestTarget;
    }
    
    performAttack(attacker, target) {
        const attackerCombat = attacker.getComponent(CombatComponent);
        const targetHealth = target.getComponent(HealthComponent);
        
        if (!targetHealth || targetHealth.isDead) return;
        
        // Perform attack
        attackerCombat.attack();
        const damage = targetHealth.takeDamage(attackerCombat.damage, attackerCombat.damageType);
        
        console.log(`Entity ${attacker.id} attacked Entity ${target.id} for ${damage} damage`);
        
        // Check if target died
        if (targetHealth.isDead) {
            console.log(`Entity ${target.id} was destroyed`);
            // Target will be cleaned up by the World
        }
    }
}

/**
 * AI System - Handles artificial intelligence behaviors
 */
export class AISystem extends System {
    constructor(world) {
        super(world);
        this.requiredComponents = [TransformComponent, AIComponent];
        this.priority = 4;
    }
    
    update() {
        for (const entity of this.entities) {
            if (!entity.active) continue;
            
            const ai = entity.getComponent(AIComponent);
            
            if (!ai.shouldThink()) continue;
            
            ai.think();
            this.updateBehavior(entity);
        }
    }
    
    updateBehavior(entity) {
        const ai = entity.getComponent(AIComponent);
        
        switch (ai.behaviorType) {
        case "idle":
            this.handleIdleBehavior(entity);
            break;
        case "guard":
            this.handleGuardBehavior(entity);
            break;
        case "patrol":
            this.handlePatrolBehavior(entity);
            break;
        case "attack":
            this.handleAttackBehavior(entity);
            break;
        }
    }
    
    handleIdleBehavior(entity) {
        // Just stand around, maybe look for enemies
        const ai = entity.getComponent(AIComponent);
        const nearbyEnemy = this.findNearbyEnemy(entity, ai.alertRadius);
        
        if (nearbyEnemy) {
            ai.behaviorType = "attack";
            
            // Set movement target if entity can move
            if (entity.hasComponent(MovementComponent)) {
                const movement = entity.getComponent(MovementComponent);
                const enemyTransform = nearbyEnemy.getComponent(TransformComponent);
                movement.setTarget(enemyTransform.x, enemyTransform.y);
            }
        }
    }
    
    handleGuardBehavior(entity) {
        // Similar to idle but returns to spawn point
        const ai = entity.getComponent(AIComponent);
        const transform = entity.getComponent(TransformComponent);
        
        // Check distance from spawn
        const dx = transform.x - ai.spawnX;
        const dy = transform.y - ai.spawnY;
        const distanceFromSpawn = Math.sqrt(dx * dx + dy * dy);
        
        if (distanceFromSpawn > ai.leashRadius) {
            // Return to spawn
            if (entity.hasComponent(MovementComponent)) {
                const movement = entity.getComponent(MovementComponent);
                movement.setTarget(ai.spawnX, ai.spawnY);
            }
        } else {
            this.handleIdleBehavior(entity);
        }
    }
    
    handlePatrolBehavior(entity) {
        // TODO: Implement patrol behavior
        this.handleGuardBehavior(entity);
    }
    
    handleAttackBehavior(entity) {
        // Actively pursue and attack enemies
        const ai = entity.getComponent(AIComponent);
        const nearbyEnemy = this.findNearbyEnemy(entity, ai.alertRadius);
        
        if (!nearbyEnemy) {
            ai.behaviorType = "guard";
            return;
        }
        
        // Move towards enemy if not in combat range
        if (entity.hasComponent(MovementComponent) && entity.hasComponent(CombatComponent)) {
            const movement = entity.getComponent(MovementComponent);
            const combat = entity.getComponent(CombatComponent);
            const enemyTransform = nearbyEnemy.getComponent(TransformComponent);
            
            if (!combat.target || combat.target !== nearbyEnemy) {
                movement.setTarget(enemyTransform.x, enemyTransform.y);
            }
        }
    }
    
    findNearbyEnemy(entity, radius) {
        const transform = entity.getComponent(TransformComponent);
        
        for (const potentialEnemy of this.world.entities) {
            if (potentialEnemy === entity || !potentialEnemy.active) continue;
            
            // TODO: Add proper faction checking
            
            const enemyTransform = potentialEnemy.getComponent(TransformComponent);
            if (!enemyTransform) continue;
            
            const dx = enemyTransform.x - transform.x;
            const dy = enemyTransform.y - transform.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance <= radius) {
                return potentialEnemy;
            }
        }
        
        return null;
    }
}