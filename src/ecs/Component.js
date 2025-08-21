/**
 * Base Component class
 * Components are pure data containers that represent different aspects of entities
 */
export class Component {
    constructor() {
        this.entity = null;
        this.destroyed = false;
        this.creationTime = Date.now();
    }
    
    /**
     * Called when component is destroyed
     */
    destroy() {
        if (this.destroyed) {
            console.warn(`Component ${this.constructor.name} already destroyed`);
            return;
        }
        this.destroyed = true;
        this.entity = null;
    }
    
    /**
     * Check if component is valid and attached to a living entity
     */
    isValid() {
        return !this.destroyed && this.entity && this.entity.isValid();
    }
}

/**
 * Transform Component - Position, rotation, scale
 */
export class TransformComponent extends Component {
    constructor(x = 0, y = 0, rotation = 0, scaleX = 1, scaleY = 1) {
        super();
        this.x = x;
        this.y = y;
        this.rotation = rotation;
        this.scaleX = scaleX;
        this.scaleY = scaleY;
        this.prevX = x;
        this.prevY = y;
        this.prevRotation = rotation;
    }
    
    /**
     * Store previous position for interpolation
     */
    storePrevious() {
        this.prevX = this.x;
        this.prevY = this.y;
        this.prevRotation = this.rotation;
    }
    
    /**
     * Get interpolated position
     */
    getInterpolated(alpha) {
        return {
            x: this.prevX + (this.x - this.prevX) * alpha,
            y: this.prevY + (this.y - this.prevY) * alpha,
            rotation: this.prevRotation + (this.rotation - this.prevRotation) * alpha
        };
    }
}

/**
 * Velocity Component - Movement speed and direction
 */
export class VelocityComponent extends Component {
    constructor(vx = 0, vy = 0, maxSpeed = 100) {
        super();
        this.vx = vx;
        this.vy = vy;
        this.maxSpeed = maxSpeed;
        this.friction = 0.95;
    }
    
    /**
     * Get current speed magnitude
     */
    getSpeed() {
        return Math.sqrt(this.vx * this.vx + this.vy * this.vy);
    }
    
    /**
     * Normalize velocity to max speed
     */
    clampToMaxSpeed() {
        const speed = this.getSpeed();
        if (speed > this.maxSpeed) {
            const scale = this.maxSpeed / speed;
            this.vx *= scale;
            this.vy *= scale;
        }
    }
}

/**
 * Sprite Component - Visual representation
 */
export class SpriteComponent extends Component {
    constructor(texture, anchor = { x: 0.5, y: 0.5 }) {
        super();
        this.texture = texture;
        this.anchor = anchor;
        this.sprite = null;
        this.visible = true;
        this.alpha = 1.0;
        this.tint = 0xffffff;
    }
    
    destroy() {
        if (this.destroyed) return;
        
        if (this.sprite) {
            try {
                // Properly cleanup PIXI sprite
                if (this.sprite.parent) {
                    this.sprite.parent.removeChild(this.sprite);
                }
                
                // Destroy sprite and release texture references
                if (this.sprite.destroy) {
                    this.sprite.destroy({
                        children: true,
                        texture: false, // Don't destroy shared textures
                        baseTexture: false
                    });
                }
            } catch (error) {
                console.error("Error destroying sprite:", error);
            }
            
            this.sprite = null;
        }
        
        // Clear texture reference
        this.texture = null;
        
        super.destroy();
    }
}

/**
 * Health Component - Hit points and damage
 */
export class HealthComponent extends Component {
    constructor(maxHealth = 100) {
        super();
        this.maxHealth = maxHealth;
        this.currentHealth = maxHealth;
        this.isDead = false;
        this.armor = 0;
        this.armorType = "none";
    }
    
    /**
     * Take damage
     */
    takeDamage(amount, damageType = "normal") {
        if (this.isDead) return;
        
        // Apply armor reduction
        const actualDamage = Math.max(0, amount - this.armor);
        this.currentHealth -= actualDamage;
        
        if (this.currentHealth <= 0) {
            this.currentHealth = 0;
            this.isDead = true;
        }
        
        return actualDamage;
    }
    
    /**
     * Heal unit
     */
    heal(amount) {
        if (this.isDead) return 0;
        
        const oldHealth = this.currentHealth;
        this.currentHealth = Math.min(this.maxHealth, this.currentHealth + amount);
        return this.currentHealth - oldHealth;
    }
    
    /**
     * Get health percentage
     */
    getHealthPercentage() {
        return this.currentHealth / this.maxHealth;
    }
}

/**
 * Unit Component - C&C specific unit data
 */
export class UnitComponent extends Component {
    constructor(unitType, faction, cost = 0) {
        super();
        this.unitType = unitType;
        this.faction = faction;
        this.cost = cost;
        this.selected = false;
        this.facing = 0; // 0-31 for 32 directions
        this.experience = 0;
        this.veterancy = "rookie"; // rookie, veteran, elite
        this.canAttack = true;
        this.canMove = true;
        this.sight = 4; // vision range
    }
}

/**
 * Building Component - C&C specific building data
 */
export class BuildingComponent extends Component {
    constructor(buildingType, faction, cost = 0) {
        super();
        this.buildingType = buildingType;
        this.faction = faction;
        this.cost = cost;
        this.powerOutput = 0;
        this.powerRequired = 0;
        this.constructing = false;
        this.constructionProgress = 0;
        this.active = true;
        this.sellable = true;
    }
}

/**
 * Movement Component - Pathfinding and movement state
 */
export class MovementComponent extends Component {
    constructor() {
        super();
        this.targetX = null;
        this.targetY = null;
        this.path = [];
        this.pathIndex = 0;
        this.isMoving = false;
        this.speed = 50; // pixels per second
        this.turnRate = 180; // degrees per second
        this.arrivalDistance = 5; // pixels
    }
    
    /**
     * Set movement target
     */
    setTarget(x, y) {
        this.targetX = x;
        this.targetY = y;
        this.path = [{ x, y }]; // Simple direct path for now
        this.pathIndex = 0;
        this.isMoving = true;
    }
    
    /**
     * Clear movement target
     */
    stop() {
        this.targetX = null;
        this.targetY = null;
        this.path = [];
        this.pathIndex = 0;
        this.isMoving = false;
    }
}

/**
 * Combat Component - Attack capabilities
 */
export class CombatComponent extends Component {
    constructor(damage = 10, range = 100, attackSpeed = 1.0) {
        super();
        this.damage = damage;
        this.range = range;
        this.attackSpeed = attackSpeed; // attacks per second
        this.lastAttackTime = 0;
        this.target = null;
        this.canAttackGround = false;
        this.canAttackAir = true;
        this.ammo = -1; // -1 = unlimited
        this.damageType = "normal";
    }
    
    /**
     * Check if can attack now
     */
    canAttack() {
        const now = Date.now();
        const cooldown = 1000 / this.attackSpeed;
        return (now - this.lastAttackTime) >= cooldown;
    }
    
    /**
     * Record attack
     */
    attack() {
        this.lastAttackTime = Date.now();
        if (this.ammo > 0) {
            this.ammo--;
        }
    }
}

/**
 * AI Component - Artificial intelligence behavior
 */
export class AIComponent extends Component {
    constructor(behaviorType = "idle") {
        super();
        this.behaviorType = behaviorType; // idle, guard, patrol, attack, harvest
        this.state = "idle";
        this.lastThinkTime = 0;
        this.thinkInterval = 100; // ms between AI updates
        this.alertRadius = 200;
        this.leashRadius = 300; // max distance from spawn point
        this.spawnX = 0;
        this.spawnY = 0;
    }
    
    /**
     * Check if AI should think
     */
    shouldThink() {
        const now = Date.now();
        return (now - this.lastThinkTime) >= this.thinkInterval;
    }
    
    /**
     * Update think timer
     */
    think() {
        this.lastThinkTime = Date.now();
    }
}

/**
 * Selectable Component - Makes entity selectable by player
 */
export class SelectableComponent extends Component {
    constructor(selectionPriority = 0) {
        super();
        this.isSelected = false;
        this.isHovered = false;
        this.selectionPriority = selectionPriority; // Higher priority selected first
        this.selectionGroup = null; // For grouping units (Ctrl+1, Ctrl+2, etc.)
        this.selectionBox = null; // Visual selection indicator
        this.healthBar = null; // Visual health bar
        this.selectableRadius = 16; // Click detection radius
    }
    
    /**
     * Select this entity
     */
    select() {
        this.isSelected = true;
    }
    
    /**
     * Deselect this entity
     */
    deselect() {
        this.isSelected = false;
    }
    
    /**
     * Toggle selection state
     */
    toggleSelection() {
        this.isSelected = !this.isSelected;
    }
    
    destroy() {
        if (this.destroyed) return;
        
        // Cleanup selection box
        if (this.selectionBox) {
            try {
                if (this.selectionBox.parent) {
                    this.selectionBox.parent.removeChild(this.selectionBox);
                }
                if (this.selectionBox.destroy) {
                    this.selectionBox.destroy({ children: true });
                }
            } catch (error) {
                console.error("Error destroying selection box:", error);
            }
            this.selectionBox = null;
        }
        
        // Cleanup health bar
        if (this.healthBar) {
            try {
                if (this.healthBar.parent) {
                    this.healthBar.parent.removeChild(this.healthBar);
                }
                if (this.healthBar.destroy) {
                    this.healthBar.destroy({ children: true });
                }
            } catch (error) {
                console.error("Error destroying health bar:", error);
            }
            this.healthBar = null;
        }
        
        super.destroy();
    }
}

/**
 * Command Component - Stores unit commands and orders
 */
export class CommandComponent extends Component {
    constructor() {
        super();
        this.currentCommand = null; // move, attack, guard, patrol, stop
        this.commandQueue = []; // Queue of commands
        this.commandTarget = null; // Target entity or position
        this.rallyPoint = null; // For buildings that produce units
        this.stance = "guard"; // aggressive, guard, hold
        this.formation = null; // Formation when moving in group
    }
    
    /**
     * Issue a new command
     */
    issueCommand(command, target = null, queued = false) {
        const newCommand = { command, target };
        if (queued && this.currentCommand) {
            this.commandQueue.push(newCommand);
        } else {
            // Overwrite current command and clear queue
            this.commandQueue = [newCommand];
            this.nextCommand();
        }
    }

    /**
     * Completes the current command and gets the next one from the queue.
     * @returns {boolean} - True if there is a new command, false otherwise.
     */
    nextCommand() {
        if (this.commandQueue.length > 0) {
            const next = this.commandQueue.shift();
            this.currentCommand = next.command;
            this.commandTarget = next.target;
            return true;
        } else {
            this.currentCommand = null;
            this.commandTarget = null;
            return false;
        }
    }
    
    /**
     * Clear all commands
     */
    clearCommands() {
        this.currentCommand = null;
        this.commandQueue = [];
        this.commandTarget = null;
    }
}