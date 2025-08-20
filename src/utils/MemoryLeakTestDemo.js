/**
 * Memory Leak Test Demo
 * Demonstrates the memory leak fixes and detection capabilities
 */

import { World } from "../ecs/World.js";
import { Entity } from "../ecs/Entity.js";
import { 
    TransformComponent, 
    SpriteComponent, 
    VelocityComponent,
    HealthComponent
} from "../ecs/Component.js";
import { MovementSystem, RenderingSystem } from "../ecs/System.js";
import { memoryLeakDetector } from "./MemoryLeakDetector.js";

export class MemoryLeakTestDemo {
    constructor() {
        this.world = new World();
        this.setupSystems();
        this.setupMemoryDetection();
    }

    setupSystems() {
        // Add systems (without PIXI for testing)
        this.world.addSystem(new MovementSystem(this.world));
        // Note: RenderingSystem requires PIXI stage, skipping for pure ECS test
    }

    setupMemoryDetection() {
        // Setup memory leak detection
        memoryLeakDetector.onLeakDetected((analysis) => {
            console.warn("🚨 Memory leak detected:", analysis);
        });
        
        memoryLeakDetector.startMonitoring(this.world, 2000); // Check every 2 seconds
    }

    /**
     * Test 1: Proper entity cleanup
     */
    testEntityCleanup() {
        console.log("\n=== Test 1: Entity Cleanup ===");
        
        const initialCount = this.world.entities.size;
        console.log(`Initial entities: ${initialCount}`);

        // Create entities
        const entities = [];
        for (let i = 0; i < 100; i++) {
            const entity = this.world.createEntity();
            entity.addComponent(new TransformComponent(i * 10, i * 10));
            entity.addComponent(new VelocityComponent(1, 1));
            entity.addComponent(new HealthComponent(100));
            entities.push(entity);
        }

        console.log(`After creation: ${this.world.entities.size} entities`);

        // Update world to process entities
        this.world.update(0.016); // 60 FPS

        // Remove entities
        entities.forEach(entity => {
            this.world.removeEntity(entity);
        });

        // Process cleanup
        this.world.update(0.016);

        console.log(`After cleanup: ${this.world.entities.size} entities`);
        console.log(`Cleanup successful: ${this.world.entities.size === initialCount}`);

        // Check for orphaned components
        let orphanedComponents = 0;
        for (const entity of entities) {
            if (entity.components.size > 0 && !entity.isValid()) {
                orphanedComponents++;
            }
        }
        console.log(`Orphaned components: ${orphanedComponents}`);
    }

    /**
     * Test 2: Component duplication detection
     */
    testComponentDuplication() {
        console.log("\n=== Test 2: Component Duplication Detection ===");

        const entity = this.world.createEntity();
        
        // Add component first time
        entity.addComponent(new TransformComponent(10, 20));
        console.log(`Components after first add: ${entity.components.size}`);

        // Try to add same component type again (should warn and replace)
        entity.addComponent(new TransformComponent(30, 40));
        console.log(`Components after second add: ${entity.components.size}`);

        const transform = entity.getComponent(TransformComponent);
        console.log(`Transform position: (${transform.x}, ${transform.y}) - should be (30, 40)`);

        // Cleanup
        this.world.removeEntity(entity);
        this.world.update(0.016);
    }

    /**
     * Test 3: Entity lifecycle validation
     */
    testEntityLifecycleValidation() {
        console.log("\n=== Test 3: Entity Lifecycle Validation ===");

        const entity = this.world.createEntity();
        entity.addComponent(new TransformComponent(0, 0));
        
        console.log(`Entity valid before destroy: ${entity.isValid()}`);
        console.log(`Entity active before destroy: ${entity.active}`);

        // Destroy entity
        entity.destroy();
        
        console.log(`Entity valid after destroy: ${entity.isValid()}`);
        console.log(`Entity active after destroy: ${entity.active}`);
        console.log(`Entity destroyed flag: ${entity.destroyed}`);

        // Try to add component to destroyed entity (should warn)
        entity.addComponent(new VelocityComponent(1, 1));
        
        // Cleanup
        this.world.update(0.016);
    }

    /**
     * Test 4: Memory leak detection
     */
    async testMemoryLeakDetection() {
        console.log("\n=== Test 4: Memory Leak Detection ===");

        // Create a scenario that might trigger leak detection
        const entities = [];
        
        // Create many entities rapidly
        for (let i = 0; i < 500; i++) {
            const entity = this.world.createEntity();
            entity.addComponent(new TransformComponent(Math.random() * 1000, Math.random() * 1000));
            entity.addComponent(new VelocityComponent(Math.random() * 10, Math.random() * 10));
            entities.push(entity);
        }

        console.log(`Created ${entities.length} entities`);

        // Wait a bit for memory detector to analyze
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Create more entities without cleaning up (potential leak)
        for (let i = 0; i < 300; i++) {
            const entity = this.world.createEntity();
            entity.addComponent(new TransformComponent(Math.random() * 1000, Math.random() * 1000));
        }

        console.log(`Total entities now: ${this.world.entities.size}`);

        // Wait for detection
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Generate report
        const report = memoryLeakDetector.generateReport();
        console.log("Memory leak report:", report);

        // Cleanup
        entities.forEach(entity => this.world.removeEntity(entity));
        this.world.update(0.016);
    }

    /**
     * Test 5: System cleanup
     */
    testSystemCleanup() {
        console.log("\n=== Test 5: System Cleanup ===");

        const system = new MovementSystem(this.world);
        this.world.addSystem(system);

        // Add some entities
        for (let i = 0; i < 10; i++) {
            const entity = this.world.createEntity();
            entity.addComponent(new TransformComponent(i * 10, i * 10));
            entity.addComponent(new VelocityComponent(1, 1));
        }

        console.log(`System entities before cleanup: ${system.entities.size}`);

        // Destroy system
        system.destroy();
        
        console.log(`System entities after destroy: ${system.entities.size}`);
        console.log(`System destroyed flag: ${system.destroyed}`);

        // Try to update destroyed system (should return early)
        system.update(0.016);
        
        this.world.clear();
    }

    /**
     * Run all tests
     */
    async runAllTests() {
        console.log("🧪 Starting ECS Memory Leak Tests...\n");

        try {
            this.testEntityCleanup();
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            this.testComponentDuplication();
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            this.testEntityLifecycleValidation();
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            await this.testMemoryLeakDetection();
            
            this.testSystemCleanup();
            
            console.log("\n✅ All tests completed!");
            
            // Final world state
            this.world.debugPrint();
            
        } catch (error) {
            console.error("❌ Test failed:", error);
        } finally {
            this.cleanup();
        }
    }

    /**
     * Cleanup test environment
     */
    cleanup() {
        memoryLeakDetector.stopMonitoring();
        this.world.destroy();
        console.log("\n🧹 Test environment cleaned up");
    }
}

// Export for direct usage
export default MemoryLeakTestDemo;