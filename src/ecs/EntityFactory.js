import * as PIXI from "pixi.js";
import { 
    TransformComponent, 
    VelocityComponent, 
    SpriteComponent, 
    HealthComponent,
    UnitComponent,
    BuildingComponent,
    MovementComponent,
    CombatComponent,
    AIComponent,
    SelectableComponent,
    CommandComponent
} from "./Component.js";

/**
 * Entity Factory - Creates common entity types with appropriate components
 * Simplifies entity creation for C&C units, buildings, and other game objects
 */
export class EntityFactory {
    constructor(world, cncAssets, textureAtlasManager) {
        this.world = world;
        this.cncAssets = cncAssets;
        this.textureAtlasManager = textureAtlasManager;
    }
    
    /**
     * Create a C&C unit entity
     */
    async createUnit(unitKey, x = 0, y = 0, faction = "gdi") {
        const unitInfo = this.cncAssets.getUnitInfo(unitKey);
        if (!unitInfo) {
            console.warn(`Unit type '${unitKey}' not found`);
            return null;
        }
        
        // Use TextureAtlasManager to create the sprite
        const spriteKey = `${faction.toLowerCase()}-${unitKey.toLowerCase().replace(/_/g, "-")}`;
        const sprite = this.textureAtlasManager.createAnimatedSprite(spriteKey, "move");

        if (!sprite) {
            console.warn(`Could not create sprite for unit '${unitKey}' with key '${spriteKey}'`);
            return null;
        }
        
        // Create entity
        const entity = this.world.createEntity();
        
        // Add components
        entity.addComponent(new TransformComponent(x, y));
        entity.addComponent(new VelocityComponent(0, 0, unitInfo.speed || 50));
        entity.addComponent(new SpriteComponent(sprite));
        entity.addComponent(new HealthComponent(unitInfo.health || 100));
        entity.addComponent(new UnitComponent(unitKey, faction, unitInfo.cost || 0));
        entity.addComponent(new MovementComponent());
        entity.addComponent(new SelectableComponent(10)); // Units have higher selection priority
        entity.addComponent(new CommandComponent());
        
        // Add combat if unit can attack
        if (unitInfo.damage && unitInfo.damage > 0) {
            entity.addComponent(new CombatComponent(
                unitInfo.damage,
                unitInfo.range || 100,
                unitInfo.attackSpeed || 1.0
            ));
        }
        
        // Add AI for computer-controlled units
        const ai = new AIComponent("guard");
        ai.spawnX = x;
        ai.spawnY = y;
        entity.addComponent(ai);
        
        console.log(`Created unit: ${unitInfo.name} at (${x}, ${y})`);
        return entity;
    }
    
    /**
     * Create a C&C building entity
     */
    async createBuilding(buildingKey, x = 0, y = 0, faction = "gdi") {
        const buildingInfo = this.cncAssets.getBuildingInfo(buildingKey);
        if (!buildingInfo) {
            console.warn(`Building type '${buildingKey}' not found`);
            return null;
        }
        
        const texture = await this.cncAssets.getTexture(`building_${buildingKey}`);
        if (!texture) {
            console.warn(`Texture for building '${buildingKey}' not found`);
            return null;
        }
        
        // Create entity
        const entity = this.world.createEntity();
        
        // Add components
        entity.addComponent(new TransformComponent(x, y));
        entity.addComponent(new SpriteComponent(texture));
        entity.addComponent(new HealthComponent(buildingInfo.health || 200));
        entity.addComponent(new BuildingComponent(buildingKey, faction, buildingInfo.cost || 0));
        entity.addComponent(new SelectableComponent(5)); // Buildings have lower selection priority
        entity.addComponent(new CommandComponent());
        
        // Add combat for defensive buildings
        if (buildingInfo.damage && buildingInfo.damage > 0) {
            entity.addComponent(new CombatComponent(
                buildingInfo.damage,
                buildingInfo.range || 150,
                buildingInfo.attackSpeed || 0.5
            ));
            
            // Add AI for defensive structures
            const ai = new AIComponent("guard");
            ai.spawnX = x;
            ai.spawnY = y;
            ai.alertRadius = buildingInfo.range || 150;
            entity.addComponent(ai);
        }
        
        console.log(`Created building: ${buildingInfo.name} at (${x}, ${y})`);
        return entity;
    }
    
    /**
     * Create a player-controlled unit (no AI)
     */
    createPlayerUnit(unitKey, x = 0, y = 0, faction = "gdi") {
        const entity = this.createUnit(unitKey, x, y, faction);
        if (entity) {
            // Remove AI component for player control
            entity.removeComponent(AIComponent);
            
            // Mark as player controlled
            const unitComp = entity.getComponent(UnitComponent);
            if (unitComp) {
                unitComp.playerControlled = true;
            }
        }
        return entity;
    }
    
    /**
     * Create a resource entity (Tiberium)
     */
    createTiberium(x = 0, y = 0, amount = 100) {
        const texture = this.cncAssets.getTexture("tiberium_green");
        if (!texture) {
            console.warn("Tiberium texture not found");
            return null;
        }
        
        const entity = this.world.createEntity();
        
        entity.addComponent(new TransformComponent(x, y));
        entity.addComponent(new SpriteComponent(texture));
        entity.addComponent(new HealthComponent(1)); // Can be depleted
        
        // Add resource component (we'll create this later)
        // entity.addComponent(new ResourceComponent('tiberium', amount));
        
        console.log(`Created Tiberium at (${x}, ${y})`);
        return entity;
    }
    
    /**
     * Create a projectile entity
     */
    createProjectile(x, y, targetX, targetY, damage = 10, speed = 200) {
        const entity = this.world.createEntity();
        
        // Calculate direction
        const dx = targetX - x;
        const dy = targetY - y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const vx = (dx / distance) * speed;
        const vy = (dy / distance) * speed;
        
        entity.addComponent(new TransformComponent(x, y));
        entity.addComponent(new VelocityComponent(vx, vy, speed));
        
        // Create simple projectile texture (small red dot)
        const projectileTexture = this.createProjectileTexture();
        entity.addComponent(new SpriteComponent(projectileTexture));
        
        // Add projectile component (we'll create this later)
        // entity.addComponent(new ProjectileComponent(damage, targetX, targetY));
        
        return entity;
    }
    
    /**
     * Create simple projectile texture
     */
    createProjectileTexture() {
        const canvas = document.createElement("canvas");
        canvas.width = 4;
        canvas.height = 4;
        const ctx = canvas.getContext("2d");
        
        ctx.fillStyle = "#ffff00";
        ctx.fillRect(0, 0, 4, 4);
        
        return PIXI.Texture.from(canvas);
    }
    
    /**
     * Create a group of units in formation
     */
    createUnitSquad(unitKey, centerX, centerY, count = 4, faction = "gdi", spacing = 40) {
        const units = [];
        const gridSize = Math.ceil(Math.sqrt(count));
        
        for (let i = 0; i < count; i++) {
            const row = Math.floor(i / gridSize);
            const col = i % gridSize;
            
            const x = centerX + (col - gridSize / 2) * spacing;
            const y = centerY + (row - gridSize / 2) * spacing;
            
            const unit = this.createUnit(unitKey, x, y, faction);
            if (unit) {
                units.push(unit);
            }
        }
        
        console.log(`Created squad of ${units.length} ${unitKey} units at (${centerX}, ${centerY})`);
        return units;
    }
    
    /**
     * Create a base layout with multiple buildings
     */
    createBase(centerX, centerY, faction = "gdi") {
        const buildings = [];
        
        // Get available buildings for faction
        const availableBuildings = this.cncAssets.getBuildingsByFaction(faction);
        
        if (availableBuildings.length === 0) {
            console.warn(`No buildings available for faction: ${faction}`);
            return buildings;
        }
        
        // Create construction yard at center
        const constructionYard = availableBuildings.find(b => 
            (b.key || "").toLowerCase().includes("construction") || 
            (b.key || "").toLowerCase().includes("mcv")
        );
        
        if (constructionYard) {
            const building = this.createBuilding(constructionYard.key, centerX, centerY, faction);
            if (building) buildings.push(building);
        }
        
        // Create power plant
        const powerPlant = availableBuildings.find(b => 
            (b.key || "").toLowerCase().includes("power") ||
            (b.key || "").toLowerCase().includes("plant")
        );
        
        if (powerPlant) {
            const building = this.createBuilding(powerPlant.key, centerX + 80, centerY, faction);
            if (building) buildings.push(building);
        }
        
        // Create barracks
        const barracks = availableBuildings.find(b => 
            (b.key || "").toLowerCase().includes("barracks") ||
            (b.key || "").toLowerCase().includes("hand")
        );
        
        if (barracks) {
            const building = this.createBuilding(barracks.key, centerX, centerY + 80, faction);
            if (building) buildings.push(building);
        }
        
        console.log(`Created ${faction} base with ${buildings.length} buildings at (${centerX}, ${centerY})`);
        return buildings;
    }
}