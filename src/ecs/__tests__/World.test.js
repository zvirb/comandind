/**
 * Unit Tests for ECS World
 * Tests entity management, system coordination, and memory management
 */

import { World } from "../World.js";

// Mock Entity and System classes for testing
class MockEntity {
    constructor(id = `entity-${Date.now()}-${Math.random()}`) {
        this.id = id;
        this.active = true;
        this.destroyed = false;
        this.components = new Map();
        this.creationTime = Date.now();
        this.lastAccessTime = Date.now();
    }

    hasComponent(ComponentType) {
        const name = typeof ComponentType === "string" ? ComponentType : ComponentType.name;
        return this.components.has(name);
    }

    getComponent(ComponentType) {
        const name = typeof ComponentType === "string" ? ComponentType : ComponentType.name;
        return this.components.get(name);
    }

    addComponent(component) {
        this.components.set(component.constructor.name, component);
        return this;
    }

    getAllComponents() {
        return Array.from(this.components.values());
    }

    isValid() {
        return this.active && !this.destroyed;
    }

    destroy() {
        this.destroyed = true;
        this.active = false;
        this.components.clear();
    }
}

class MockSystem {
    constructor(priority = 0) {
        this.priority = priority;
        this.entities = new Set();
        this.destroyed = false;
        this.updateCalled = false;
        this.renderCalled = false;
    }

    addEntity(entity) {
        this.entities.add(entity);
    }

    removeEntity(entity) {
        this.entities.delete(entity);
    }

    update(deltaTime) {
        this.updateCalled = true;
        this.lastDeltaTime = deltaTime;
    }

    render(interpolation) {
        this.renderCalled = true;
        this.lastInterpolation = interpolation;
    }

    destroy() {
        this.destroyed = true;
        this.entities.clear();
    }

    getMemoryInfo() {
        return {
            entityCount: this.entities.size,
            destroyed: this.destroyed
        };
    }
}

class MockComponent {
    constructor(name = "MockComponent") {
        this.name = name;
    }
}

describe("ECS World", () => {
    let world;

    beforeEach(() => {
        world = new World();
    
        // Mock Entity constructor for World.createEntity()
        world.Entity = MockEntity;
    });

    afterEach(() => {
        if (world && !world.destroyed) {
            world.destroy();
        }
    });

    describe("World Creation and Initialization", () => {
        test("should create world with default values", () => {
            expect(world.entities).toBeInstanceOf(Set);
            expect(world.systems).toEqual([]);
            expect(world.entitiesToRemove).toBeInstanceOf(Set);
            expect(world.destroyed).toBe(false);
            expect(world.creationTime).toBeGreaterThan(0);
            expect(world.memoryLeakDetection.enabled).toBe(true);
        });

        test("should initialize with empty collections", () => {
            expect(world.entities.size).toBe(0);
            expect(world.systems.length).toBe(0);
            expect(world.entitiesToRemove.size).toBe(0);
        });
    });

    describe("Entity Management", () => {
        test("should create new entity", () => {
            const entity = world.createEntity();
      
            expect(entity).toBeInstanceOf(MockEntity);
            expect(world.entities.has(entity)).toBe(true);
            expect(world.entities.size).toBe(1);
        });

        test("should add entity to all systems when created", () => {
            const system1 = new MockSystem();
            const system2 = new MockSystem();
      
            world.addSystem(system1);
            world.addSystem(system2);
      
            const entity = world.createEntity();
      
            expect(system1.entities.has(entity)).toBe(true);
            expect(system2.entities.has(entity)).toBe(true);
        });

        test("should mark entity for removal", () => {
            const entity = world.createEntity();
      
            world.removeEntity(entity);
      
            expect(world.entitiesToRemove.has(entity)).toBe(true);
            expect(world.entities.has(entity)).toBe(true); // Still in entities until cleanup
        });

        test("should not mark unknown entity for removal", () => {
            const foreignEntity = new MockEntity();
      
            world.removeEntity(foreignEntity);
      
            expect(world.entitiesToRemove.has(foreignEntity)).toBe(false);
        });

        test("should clean up marked entities", () => {
            const entity = world.createEntity();
            const system = new MockSystem();
            world.addSystem(system);
      
            world.removeEntity(entity);
            world.cleanupEntities();
      
            expect(world.entities.has(entity)).toBe(false);
            expect(world.entitiesToRemove.has(entity)).toBe(false);
            expect(system.entities.has(entity)).toBe(false);
            expect(entity.destroyed).toBe(true);
        });

        test("should handle entity cleanup errors gracefully", () => {
            const entity = world.createEntity();
            entity.destroy = jest.fn(() => { throw new Error("Cleanup error"); });
      
            const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      
            world.removeEntity(entity);
            world.cleanupEntities();
      
            expect(world.entities.has(entity)).toBe(false); // Still removed despite error
            expect(consoleSpy).toHaveBeenCalled();
      
            consoleSpy.mockRestore();
        });
    });

    describe("System Management", () => {
        test("should add system to world", () => {
            const system = new MockSystem();
      
            const result = world.addSystem(system);
      
            expect(result).toBe(system);
            expect(world.systems).toContain(system);
            expect(world.systemsNeedSorting).toBe(true);
        });

        test("should add existing entities to new system", () => {
            const entity1 = world.createEntity();
            const entity2 = world.createEntity();
      
            const system = new MockSystem();
            world.addSystem(system);
      
            expect(system.entities.has(entity1)).toBe(true);
            expect(system.entities.has(entity2)).toBe(true);
        });

        test("should remove system from world", () => {
            const system = new MockSystem();
            world.addSystem(system);
      
            world.removeSystem(system);
      
            expect(world.systems).not.toContain(system);
        });

        test("should handle removing non-existent system", () => {
            const system = new MockSystem();
      
            expect(() => {
                world.removeSystem(system);
            }).not.toThrow();
        });

        test("should sort systems by priority", () => {
            const system1 = new MockSystem(10);
            const system2 = new MockSystem(5);
            const system3 = new MockSystem(15);
      
            world.addSystem(system1);
            world.addSystem(system2);
            world.addSystem(system3);
      
            world.sortSystems();
      
            expect(world.systems[0]).toBe(system2); // Priority 5
            expect(world.systems[1]).toBe(system1); // Priority 10
            expect(world.systems[2]).toBe(system3); // Priority 15
            expect(world.systemsNeedSorting).toBe(false);
        });

        test("should not sort systems when not needed", () => {
            const system = new MockSystem();
            world.addSystem(system);
            world.sortSystems(); // First sort
      
            const sortSpy = jest.spyOn(world.systems, "sort");
      
            world.sortSystems(); // Second sort should be skipped
      
            expect(sortSpy).not.toHaveBeenCalled();
            sortSpy.mockRestore();
        });
    });

    describe("Update and Render Cycles", () => {
        test("should update all systems", () => {
            const system1 = new MockSystem();
            const system2 = new MockSystem();
      
            world.addSystem(system1);
            world.addSystem(system2);
      
            world.update(16.67);
      
            expect(system1.updateCalled).toBe(true);
            expect(system2.updateCalled).toBe(true);
            expect(system1.lastDeltaTime).toBe(16.67);
        });

        test("should render all systems with render method", () => {
            const system1 = new MockSystem();
            const system2 = new MockSystem();
      
            world.addSystem(system1);
            world.addSystem(system2);
      
            world.render(0.5);
      
            expect(system1.renderCalled).toBe(true);
            expect(system2.renderCalled).toBe(true);
            expect(system1.lastInterpolation).toBe(0.5);
        });

        test("should remove inactive entities during update", () => {
            const entity = world.createEntity();
            entity.active = false;
      
            world.update(16.67);
      
            expect(world.entitiesToRemove.has(entity)).toBe(true);
        });

        test("should clean up entities after update", () => {
            const entity = world.createEntity();
            world.removeEntity(entity);
      
            world.update(16.67);
      
            expect(world.entities.has(entity)).toBe(false);
        });

        test("should sort systems before update and render", () => {
            const system = new MockSystem();
            world.addSystem(system);
      
            const sortSpy = jest.spyOn(world, "sortSystems");
      
            world.update(16.67);
            world.render(0.5);
      
            expect(sortSpy).toHaveBeenCalledTimes(2);
            sortSpy.mockRestore();
        });
    });

    describe("Entity Queries", () => {
        test("should get entities with specific component", () => {
            const entity1 = world.createEntity();
            const entity2 = world.createEntity();
            const entity3 = world.createEntity();
      
            entity1.addComponent(new MockComponent("TestComponent"));
            entity2.addComponent(new MockComponent("TestComponent"));
      
            const entities = world.getEntitiesWith("TestComponent");
      
            expect(entities).toHaveLength(2);
            expect(entities).toContain(entity1);
            expect(entities).toContain(entity2);
            expect(entities).not.toContain(entity3);
        });

        test("should get entities with multiple components", () => {
            const entity1 = world.createEntity();
            const entity2 = world.createEntity();
      
            entity1.addComponent(new MockComponent("ComponentA"));
            entity1.addComponent(new MockComponent("ComponentB"));
            entity2.addComponent(new MockComponent("ComponentA"));
      
            const entities = world.getEntitiesWith("ComponentA", "ComponentB");
      
            expect(entities).toHaveLength(1);
            expect(entities).toContain(entity1);
        });

        test("should get first entity with components", () => {
            const entity1 = world.createEntity();
            const entity2 = world.createEntity();
      
            entity1.addComponent(new MockComponent("TestComponent"));
            entity2.addComponent(new MockComponent("TestComponent"));
      
            const entity = world.getFirstEntityWith("TestComponent");
      
            expect(entity).toBe(entity1); // Should return first found
        });

        test("should return null when no entity found", () => {
            const entity = world.getFirstEntityWith("NonExistentComponent");
      
            expect(entity).toBeNull();
        });

        test("should get entities by single component type", () => {
            const entity1 = world.createEntity();
            const entity2 = world.createEntity();
      
            entity1.addComponent(new MockComponent("TestComponent"));
      
            const entities = world.getEntitiesByComponent("TestComponent");
      
            expect(entities).toHaveLength(1);
            expect(entities).toContain(entity1);
        });

        test("should get entity by ID", () => {
            const entity = world.createEntity();
      
            const foundEntity = world.getEntityById(entity.id);
      
            expect(foundEntity).toBe(entity);
        });

        test("should return null for unknown entity ID", () => {
            const entity = world.getEntityById("unknown-id");
      
            expect(entity).toBeNull();
        });

        test("should skip inactive entities in queries", () => {
            const entity = world.createEntity();
            entity.addComponent(new MockComponent("TestComponent"));
            entity.active = false;
      
            const entities = world.getEntitiesWith("TestComponent");
      
            expect(entities).toHaveLength(0);
        });
    });

    describe("Memory Management and Leak Detection", () => {
        test("should detect long-lived entities", () => {
            const entity = world.createEntity();
            entity.creationTime = Date.now() - 400000; // 400 seconds ago
      
            const leaks = world.detectMemoryLeaks();
      
            expect(leaks).toBeDefined();
            expect(leaks.longLivedEntities).toHaveLength(1);
            expect(leaks.longLivedEntities[0].id).toBe(entity.id);
        });

        test("should detect unused entities", () => {
            const entity = world.createEntity();
            entity.lastAccessTime = Date.now() - 70000; // 70 seconds ago
      
            const leaks = world.detectMemoryLeaks();
      
            expect(leaks.unusedEntities).toHaveLength(1);
        });

        test("should detect system memory leaks", () => {
            const system = new MockSystem();
      
            // Add many fake entities to system
            for (let i = 0; i < 1500; i++) {
                system.entities.add({ id: `fake-${i}` });
            }
      
            world.addSystem(system);
      
            const leaks = world.detectMemoryLeaks();
      
            expect(leaks.systemLeaks).toHaveLength(1);
            expect(leaks.systemLeaks[0].entityCount).toBe(1500);
        });

        test("should respect memory leak detection interval", () => {
            world.memoryLeakDetection.lastCheck = Date.now();
      
            const leaks = world.detectMemoryLeaks();
      
            expect(leaks).toBeNull(); // Too soon for next check
        });

        test("should disable memory leak detection when configured", () => {
            world.memoryLeakDetection.enabled = false;
      
            const leaks = world.detectMemoryLeaks();
      
            expect(leaks).toBeNull();
        });
    });

    describe("World Statistics and Debugging", () => {
        test("should provide world statistics", () => {
            world.createEntity();
            world.createEntity();
            world.addSystem(new MockSystem());
      
            const stats = world.getStats();
      
            expect(stats.entityCount).toBe(2);
            expect(stats.systemCount).toBe(1);
            expect(stats.pendingRemoval).toBe(0);
        });

        test("should include pending removals in stats", () => {
            const entity = world.createEntity();
            world.removeEntity(entity);
      
            const stats = world.getStats();
      
            expect(stats.pendingRemoval).toBe(1);
        });

        test("should provide comprehensive memory usage info", () => {
            const entity = world.createEntity();
            entity.getMemoryInfo = jest.fn(() => ({ size: 100 }));
      
            const system = new MockSystem();
            world.addSystem(system);
      
            const memoryUsage = world.getMemoryUsage();
      
            expect(memoryUsage).toHaveProperty("worldStats");
            expect(memoryUsage).toHaveProperty("entities");
            expect(memoryUsage).toHaveProperty("systems");
            expect(memoryUsage).toHaveProperty("memoryLeaks");
        });

        test("should debug print world state", () => {
            const consoleSpy = jest.spyOn(console, "log").mockImplementation();
      
            world.createEntity();
            world.addSystem(new MockSystem());
      
            world.debugPrint();
      
            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining("=== ECS World Debug ===")
            );
      
            consoleSpy.mockRestore();
        });

        test("should warn about invalid entities in debug print", () => {
            const entity = world.createEntity();
            entity.isValid = jest.fn(() => false);
            entity.getAllComponents = jest.fn(() => []);
      
            const consoleSpy = jest.spyOn(console, "warn").mockImplementation();
      
            world.debugPrint();
      
            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining("Invalid entities detected")
            );
      
            consoleSpy.mockRestore();
        });
    });

    describe("World Cleanup and Destruction", () => {
        test("should clear all entities and systems", () => {
            const entity = world.createEntity();
            const system = new MockSystem();
            world.addSystem(system);
      
            world.clear();
      
            expect(world.entities.size).toBe(0);
            expect(world.systems.length).toBe(0);
            expect(entity.destroyed).toBe(true);
            expect(system.destroyed).toBe(true);
        });

        test("should handle system cleanup errors gracefully", () => {
            const system = new MockSystem();
            system.destroy = jest.fn(() => { throw new Error("System cleanup error"); });
            world.addSystem(system);
      
            const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      
            world.clear();
      
            expect(consoleSpy).toHaveBeenCalled();
            expect(world.systems.length).toBe(0);
      
            consoleSpy.mockRestore();
        });

        test("should destroy world and mark as destroyed", () => {
            world.destroy();
      
            expect(world.destroyed).toBe(true);
        });

        test("should handle multiple destroy calls", () => {
            world.destroy();
      
            expect(() => {
                world.destroy();
            }).not.toThrow();
        });

        test("should cleanup be alias for destroy", () => {
            world.cleanup();
      
            expect(world.destroyed).toBe(true);
        });

        test("should not perform operations on destroyed world", () => {
            world.destroy();
      
            world.clear(); // Should not throw
            expect(world.destroyed).toBe(true);
        });
    });

    describe("Edge Cases and Error Handling", () => {
        test("should handle entity destruction during iteration", () => {
            const entities = [];
            for (let i = 0; i < 5; i++) {
                entities.push(world.createEntity());
            }
      
            // Remove entities during cleanup
            entities.forEach(entity => world.removeEntity(entity));
      
            expect(() => {
                world.cleanupEntities();
            }).not.toThrow();
      
            expect(world.entities.size).toBe(0);
        });

        test("should handle system removal during update", () => {
            const system = new MockSystem();
            system.destroyed = true; // Mark as destroyed
            world.addSystem(system);
      
            expect(() => {
                world.update(16.67);
            }).not.toThrow();
        });

        test("should handle massive entity creation and removal", () => {
            const entities = [];
      
            // Create many entities
            for (let i = 0; i < 1000; i++) {
                entities.push(world.createEntity());
            }
      
            expect(world.entities.size).toBe(1000);
      
            // Remove all entities
            entities.forEach(entity => world.removeEntity(entity));
            world.cleanupEntities();
      
            expect(world.entities.size).toBe(0);
        });

        test("should handle null entity in operations", () => {
            expect(() => {
                world.removeEntity(null);
            }).not.toThrow();
      
            expect(() => {
                world.removeEntity(undefined);
            }).not.toThrow();
        });
    });
});