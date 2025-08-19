import { Entity } from './Entity.js';

/**
 * World - ECS World manager that handles entities and systems
 * Coordinates all game logic through the entity-component-system pattern
 */
export class World {
    constructor() {
        this.entities = new Set();
        this.systems = [];
        this.entitiesToRemove = new Set();
        this.systemsNeedSorting = false;
        this.destroyed = false;
        this.creationTime = Date.now();
        this.memoryLeakDetection = {
            enabled: true,
            lastCheck: Date.now(),
            checkInterval: 10000, // 10 seconds
            entityLifetimeThreshold: 300000, // 5 minutes
            unusedEntityThreshold: 60000 // 1 minute
        };
    }
    
    /**
     * Create a new entity
     */
    createEntity() {
        const entity = new Entity();
        this.entities.add(entity);
        
        // Notify all systems about the new entity
        for (const system of this.systems) {
            system.addEntity(entity);
        }
        
        return entity;
    }
    
    /**
     * Remove an entity from the world
     */
    removeEntity(entity) {
        if (this.entities.has(entity)) {
            // Mark for removal (deferred to avoid issues during iteration)
            this.entitiesToRemove.add(entity);
        }
    }
    
    /**
     * Actually remove entities marked for removal
     */
    cleanupEntities() {
        for (const entity of this.entitiesToRemove) {
            if (this.entities.has(entity)) {
                try {
                    // Notify systems before cleanup
                    for (const system of this.systems) {
                        if (!system.destroyed) {
                            system.removeEntity(entity);
                        }
                    }
                    
                    // Remove from world
                    this.entities.delete(entity);
                    
                    // Cleanup entity
                    entity.destroy();
                } catch (error) {
                    console.error(`Error cleaning up entity ${entity.id}:`, error);
                    // Force remove even if cleanup failed
                    this.entities.delete(entity);
                }
            }
        }
        this.entitiesToRemove.clear();
    }
    
    /**
     * Add a system to the world
     */
    addSystem(system) {
        this.systems.push(system);
        this.systemsNeedSorting = true;
        
        // Add all existing entities to the new system
        for (const entity of this.entities) {
            system.addEntity(entity);
        }
        
        return system;
    }
    
    /**
     * Remove a system from the world
     */
    removeSystem(system) {
        const index = this.systems.indexOf(system);
        if (index !== -1) {
            this.systems.splice(index, 1);
        }
    }
    
    /**
     * Sort systems by priority
     */
    sortSystems() {
        if (this.systemsNeedSorting) {
            this.systems.sort((a, b) => a.priority - b.priority);
            this.systemsNeedSorting = false;
        }
    }
    
    /**
     * Update all systems (fixed timestep)
     */
    update(deltaTime) {
        this.sortSystems();
        
        // Update all systems
        for (const system of this.systems) {
            system.update(deltaTime);
        }
        
        // Remove entities marked for destruction
        for (const entity of this.entities) {
            if (!entity.active) {
                this.removeEntity(entity);
            }
        }
        
        // Clean up removed entities
        this.cleanupEntities();
    }
    
    /**
     * Render all systems (with interpolation)
     */
    render(interpolation) {
        this.sortSystems();
        
        // Render all systems
        for (const system of this.systems) {
            if (system.render) {
                system.render(interpolation);
            }
        }
    }
    
    /**
     * Get entities with specific components
     */
    getEntitiesWith(...ComponentTypes) {
        const matchingEntities = [];
        
        for (const entity of this.entities) {
            if (entity.active && ComponentTypes.every(ComponentType => entity.hasComponent(ComponentType))) {
                matchingEntities.push(entity);
            }
        }
        
        return matchingEntities;
    }
    
    /**
     * Get first entity with specific components
     */
    getFirstEntityWith(...ComponentTypes) {
        for (const entity of this.entities) {
            if (entity.active && ComponentTypes.every(ComponentType => entity.hasComponent(ComponentType))) {
                return entity;
            }
        }
        return null;
    }
    
    /**
     * Get all entities by component type
     */
    getEntitiesByComponent(ComponentType) {
        const matchingEntities = [];
        
        for (const entity of this.entities) {
            if (entity.active && entity.hasComponent(ComponentType)) {
                matchingEntities.push(entity);
            }
        }
        
        return matchingEntities;
    }
    
    /**
     * Get entity by ID
     */
    getEntityById(id) {
        for (const entity of this.entities) {
            if (entity.id === id) {
                return entity;
            }
        }
        return null;
    }
    
    /**
     * Clear all entities and systems
     */
    clear() {
        if (this.destroyed) return;
        
        // Clean up all systems first
        for (const system of this.systems) {
            try {
                if (system.destroy) {
                    system.destroy();
                }
            } catch (error) {
                console.error(`Error destroying system ${system.constructor.name}:`, error);
            }
        }
        
        // Clean up all entities
        for (const entity of this.entities) {
            try {
                entity.destroy();
            } catch (error) {
                console.error(`Error destroying entity ${entity.id}:`, error);
            }
        }
        
        this.entities.clear();
        this.entitiesToRemove.clear();
        this.systems = [];
        this.systemsNeedSorting = false;
    }
    
    /**
     * Destroy world and cleanup all resources
     */
    destroy() {
        if (this.destroyed) return;
        
        this.destroyed = true;
        this.clear();
    }
    
    /**
     * Memory leak detection - identifies potential memory leaks
     */
    detectMemoryLeaks() {
        if (!this.memoryLeakDetection.enabled) return null;
        
        const now = Date.now();
        if (now - this.memoryLeakDetection.lastCheck < this.memoryLeakDetection.checkInterval) {
            return null;
        }
        
        this.memoryLeakDetection.lastCheck = now;
        
        const leaks = {
            longLivedEntities: [],
            unusedEntities: [],
            orphanedComponents: [],
            systemLeaks: []
        };
        
        // Check for long-lived entities
        for (const entity of this.entities) {
            const age = now - entity.creationTime;
            const timeSinceLastAccess = now - entity.lastAccessTime;
            
            if (age > this.memoryLeakDetection.entityLifetimeThreshold) {
                leaks.longLivedEntities.push({
                    id: entity.id,
                    age,
                    timeSinceLastAccess,
                    componentCount: entity.components.size
                });
            }
            
            if (timeSinceLastAccess > this.memoryLeakDetection.unusedEntityThreshold) {
                leaks.unusedEntities.push({
                    id: entity.id,
                    timeSinceLastAccess,
                    componentCount: entity.components.size
                });
            }
        }
        
        // Check for system memory issues
        for (const system of this.systems) {
            if (system.entities.size > 1000) { // Arbitrary threshold
                leaks.systemLeaks.push({
                    name: system.constructor.name,
                    entityCount: system.entities.size
                });
            }
        }
        
        return leaks;
    }
    
    /**
     * Get world statistics
     */
    getStats() {
        return {
            entityCount: this.entities.size,
            systemCount: this.systems.length,
            pendingRemoval: this.entitiesToRemove.size
        };
    }
    
    /**
     * Debug: Print world state
     */
    debugPrint() {
        console.log('=== ECS World Debug ===');
        console.log(`Entities: ${this.entities.size}`);
        console.log(`Systems: ${this.systems.length}`);
        console.log(`Pending removal: ${this.entitiesToRemove.size}`);
        console.log(`World age: ${Date.now() - this.creationTime}ms`);
        
        // Print system info
        console.log('Systems:');
        for (const system of this.systems) {
            const memInfo = system.getMemoryInfo ? system.getMemoryInfo() : { entityCount: system.entities.size };
            console.log(`  - ${system.constructor.name} (priority: ${system.priority}, entities: ${memInfo.entityCount}, destroyed: ${system.destroyed || false})`);
        }
        
        // Print entity component summary
        const componentCounts = new Map();
        const invalidEntities = [];
        for (const entity of this.entities) {
            if (!entity.isValid()) {
                invalidEntities.push(entity.id);
                continue;
            }
            
            for (const component of entity.getAllComponents()) {
                const name = component.constructor.name;
                componentCounts.set(name, (componentCounts.get(name) || 0) + 1);
            }
        }
        
        console.log('Component usage:');
        for (const [name, count] of componentCounts.entries()) {
            console.log(`  - ${name}: ${count}`);
        }
        
        if (invalidEntities.length > 0) {
            console.warn(`Invalid entities detected: ${invalidEntities.join(', ')}`);
        }
        
        // Print memory leak detection results
        const leaks = this.detectMemoryLeaks();
        if (leaks) {
            console.log('Memory leak detection:');
            if (leaks.longLivedEntities.length > 0) {
                console.warn(`  Long-lived entities: ${leaks.longLivedEntities.length}`);
            }
            if (leaks.unusedEntities.length > 0) {
                console.warn(`  Unused entities: ${leaks.unusedEntities.length}`);
            }
            if (leaks.systemLeaks.length > 0) {
                console.warn(`  System leaks: ${leaks.systemLeaks.length}`);
            }
        }
    }
    
    /**
     * Get comprehensive memory usage information
     */
    getMemoryUsage() {
        const entityMemory = [];
        for (const entity of this.entities) {
            entityMemory.push(entity.getMemoryInfo());
        }
        
        const systemMemory = [];
        for (const system of this.systems) {
            if (system.getMemoryInfo) {
                systemMemory.push(system.getMemoryInfo());
            }
        }
        
        return {
            worldStats: this.getStats(),
            entities: entityMemory,
            systems: systemMemory,
            memoryLeaks: this.detectMemoryLeaks()
        };
    }
}