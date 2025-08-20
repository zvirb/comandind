/**
 * Integration Tests for Game Systems
 * Tests interaction between ECS World, AI, Pathfinding, and Core systems
 */

import { World } from '../../src/ecs/World.js';
import { AIComponent } from '../../src/ai/components/AIComponent.js';
import { AStar } from '../../src/pathfinding/AStar.js';

// Mock implementations for integration testing
class MockTransformComponent {
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
    this.rotation = 0;
    this.scale = 1;
  }
}

class MockMovementComponent {
  constructor() {
    this.velocity = { x: 0, y: 0 };
    this.speed = 100;
    this.target = null;
    this.path = [];
    this.currentPathIndex = 0;
  }
}

class MockHealthComponent {
  constructor(maxHealth = 100) {
    this.maxHealth = maxHealth;
    this.currentHealth = maxHealth;
    this.isAlive = true;
  }

  takeDamage(amount) {
    this.currentHealth = Math.max(0, this.currentHealth - amount);
    this.isAlive = this.currentHealth > 0;
  }

  heal(amount) {
    this.currentHealth = Math.min(this.maxHealth, this.currentHealth + amount);
  }
}

class MockAISystem {
  constructor(world) {
    this.world = world;
    this.priority = 10;
    this.entities = new Set();
    this.destroyed = false;
  }

  addEntity(entity) {
    if (entity.hasComponent(AIComponent)) {
      this.entities.add(entity);
    }
  }

  removeEntity(entity) {
    this.entities.delete(entity);
  }

  update(deltaTime) {
    if (this.destroyed) return;

    for (const entity of this.entities) {
      const aiComponent = entity.getComponent(AIComponent);
      const transform = entity.getComponent(MockTransformComponent);
      
      if (!aiComponent || !transform || !aiComponent.enabled) continue;

      // Simulate AI decision making
      if (aiComponent.shouldMakeDecision()) {
        this.makeAIDecision(entity, aiComponent, transform, deltaTime);
        aiComponent.markDecisionMade();
      }

      // Update tactical context
      const gameState = this.createGameStateForEntity(entity);
      aiComponent.updateTacticalContext(gameState);
    }
  }

  makeAIDecision(entity, aiComponent, transform, deltaTime) {
    const decision = this.calculateBestAction(entity, aiComponent, transform);
    
    if (decision.action === 'move') {
      const movement = entity.getComponent(MockMovementComponent);
      if (movement) {
        movement.target = decision.target;
        this.requestPathfinding(entity, transform, decision.target);
      }
    } else if (decision.action === 'attack') {
      this.performAttack(entity, decision.target);
    }

    // Learn from decision
    const reward = this.calculateReward(decision, entity);
    aiComponent.learnFromExperience(reward, decision.action, 'pending');
  }

  calculateBestAction(entity, aiComponent, transform) {
    // Simple AI logic for testing
    const nearbyEnemies = this.findNearbyEnemies(entity, 200);
    
    if (nearbyEnemies.length > 0 && aiComponent.tacticalContext.alertLevel === 'combat') {
      return {
        action: 'attack',
        target: nearbyEnemies[0],
        confidence: 0.8
      };
    }

    // Default: move to random location
    return {
      action: 'move',
      target: {
        x: transform.x + (Math.random() - 0.5) * 200,
        y: transform.y + (Math.random() - 0.5) * 200
      },
      confidence: 0.3
    };
  }

  findNearbyEnemies(entity, radius) {
    const transform = entity.getComponent(MockTransformComponent);
    const enemies = [];

    for (const otherEntity of this.world.entities) {
      if (otherEntity === entity) continue;
      
      const otherTransform = otherEntity.getComponent(MockTransformComponent);
      const otherHealth = otherEntity.getComponent(MockHealthComponent);
      
      if (!otherTransform || !otherHealth || !otherHealth.isAlive) continue;

      const distance = Math.sqrt(
        Math.pow(otherTransform.x - transform.x, 2) +
        Math.pow(otherTransform.y - transform.y, 2)
      );

      if (distance <= radius) {
        enemies.push({
          entity: otherEntity,
          distance,
          position: { x: otherTransform.x, y: otherTransform.y }
        });
      }
    }

    return enemies.sort((a, b) => a.distance - b.distance);
  }

  requestPathfinding(entity, fromTransform, target) {
    // This would integrate with actual pathfinding system
    const movement = entity.getComponent(MockMovementComponent);
    if (movement) {
      movement.path = [
        { x: fromTransform.x, y: fromTransform.y },
        { x: target.x, y: target.y }
      ];
      movement.currentPathIndex = 0;
    }
  }

  performAttack(entity, target) {
    const targetHealth = target.entity.getComponent(MockHealthComponent);
    if (targetHealth) {
      targetHealth.takeDamage(25);
    }
  }

  calculateReward(decision, entity) {
    // Simple reward calculation for testing
    const health = entity.getComponent(MockHealthComponent);
    if (!health) return 0;

    if (decision.action === 'attack' && decision.confidence > 0.7) {
      return 0.5; // Good combat decision
    } else if (decision.action === 'move') {
      return 0.1; // Neutral movement
    }

    return 0;
  }

  createGameStateForEntity(entity) {
    const transform = entity.getComponent(MockTransformComponent);
    const nearbyEntities = this.findNearbyEnemies(entity, 300);

    return {
      nearbyEntities: nearbyEntities.map(enemy => ({
        entity: enemy.entity,
        distance: enemy.distance,
        angle: Math.atan2(
          enemy.position.y - transform.y,
          enemy.position.x - transform.x
        )
      }))
    };
  }

  destroy() {
    this.destroyed = true;
    this.entities.clear();
  }
}

class MockMovementSystem {
  constructor(world) {
    this.world = world;
    this.priority = 5;
    this.entities = new Set();
    this.destroyed = false;
  }

  addEntity(entity) {
    if (entity.hasComponent(MockMovementComponent) && entity.hasComponent(MockTransformComponent)) {
      this.entities.add(entity);
    }
  }

  removeEntity(entity) {
    this.entities.delete(entity);
  }

  update(deltaTime) {
    if (this.destroyed) return;

    for (const entity of this.entities) {
      const movement = entity.getComponent(MockMovementComponent);
      const transform = entity.getComponent(MockTransformComponent);

      if (!movement || !transform) continue;

      this.updateMovement(entity, movement, transform, deltaTime);
    }
  }

  updateMovement(entity, movement, transform, deltaTime) {
    if (movement.path.length > 0 && movement.currentPathIndex < movement.path.length) {
      const target = movement.path[movement.currentPathIndex];
      const dx = target.x - transform.x;
      const dy = target.y - transform.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance < 5) {
        // Reached waypoint
        movement.currentPathIndex++;
      } else {
        // Move towards waypoint
        const moveDistance = movement.speed * (deltaTime / 1000);
        transform.x += (dx / distance) * moveDistance;
        transform.y += (dy / distance) * moveDistance;
      }
    }
  }

  destroy() {
    this.destroyed = true;
    this.entities.clear();
  }
}

describe('Game Systems Integration', () => {
  let world;
  let aiSystem;
  let movementSystem;
  let mockGrid;
  let pathfinder;

  beforeEach(() => {
    world = new World();
    world.Entity = function(id) {
      return createMockEntity(id);
    };

    mockGrid = createMockNavigationGrid(20, 20);
    pathfinder = new AStar(mockGrid);

    aiSystem = new MockAISystem(world);
    movementSystem = new MockMovementSystem(world);

    world.addSystem(movementSystem);
    world.addSystem(aiSystem);
  });

  afterEach(() => {
    if (world && !world.destroyed) {
      world.destroy();
    }
  });

  describe('ECS World Integration', () => {
    test('should manage entities across multiple systems', () => {
      // Create AI-controlled entity
      const entity = world.createEntity();
      entity.addComponent(new MockTransformComponent(100, 100));
      entity.addComponent(new MockMovementComponent());
      entity.addComponent(new AIComponent());
      entity.addComponent(new MockHealthComponent());

      expect(aiSystem.entities.has(entity)).toBe(true);
      expect(movementSystem.entities.has(entity)).toBe(true);
    });

    test('should remove entities from all systems when destroyed', () => {
      const entity = world.createEntity();
      entity.addComponent(new MockTransformComponent());
      entity.addComponent(new MockMovementComponent());
      entity.addComponent(new AIComponent());

      world.removeEntity(entity);
      world.cleanupEntities();

      expect(aiSystem.entities.has(entity)).toBe(false);
      expect(movementSystem.entities.has(entity)).toBe(false);
      expect(world.entities.has(entity)).toBe(false);
    });

    test('should maintain system priority order during updates', () => {
      const updateOrder = [];
      
      aiSystem.update = jest.fn(() => updateOrder.push('ai'));
      movementSystem.update = jest.fn(() => updateOrder.push('movement'));

      world.update(16.67);

      expect(updateOrder).toEqual(['movement', 'ai']); // Movement (priority 5) before AI (priority 10)
    });
  });

  describe('AI and Movement Integration', () => {
    test('should coordinate AI decisions with movement system', () => {
      const entity = world.createEntity();
      const transform = new MockTransformComponent(0, 0);
      const movement = new MockMovementComponent();
      const ai = new AIComponent({ behaviorType: 'combatUnit', decisionInterval: 100 });

      entity.addComponent(transform);
      entity.addComponent(movement);
      entity.addComponent(ai);

      // Run systems
      world.update(16.67);

      // AI should have made a decision
      expect(ai.debugInfo.lastDecision).toBeDefined();
      
      // Movement should have a target or path
      expect(movement.target || movement.path.length > 0).toBeTruthy();
    });

    test('should handle pathfinding integration', () => {
      const entity = world.createEntity();
      entity.addComponent(new MockTransformComponent(0, 0));
      entity.addComponent(new MockMovementComponent());
      entity.addComponent(new AIComponent());

      // Simulate AI requesting pathfinding
      const path = pathfinder.findPath(0, 0, 320, 320);
      const movement = entity.getComponent(MockMovementComponent);
      movement.path = path;

      // Run movement system
      movementSystem.update(16.67);

      const transform = entity.getComponent(MockTransformComponent);
      expect(transform.x).not.toBe(0); // Should have moved
      expect(transform.y).not.toBe(0);
    });

    test('should update AI tactical context based on world state', () => {
      // Create AI entity
      const aiEntity = world.createEntity();
      aiEntity.addComponent(new MockTransformComponent(100, 100));
      aiEntity.addComponent(new AIComponent());
      aiEntity.addComponent(new MockHealthComponent());

      // Create nearby enemy
      const enemyEntity = world.createEntity();
      enemyEntity.addComponent(new MockTransformComponent(150, 150));
      enemyEntity.addComponent(new MockHealthComponent());

      // Run AI system
      aiSystem.update(16.67);

      const ai = aiEntity.getComponent(AIComponent);
      expect(ai.tacticalContext.enemiesNearby).toBe(1);
    });
  });

  describe('Combat System Integration', () => {
    test('should handle combat between AI entities', () => {
      // Create attacker
      const attacker = world.createEntity();
      attacker.addComponent(new MockTransformComponent(100, 100));
      attacker.addComponent(new AIComponent({ behaviorType: 'combatUnit' }));
      attacker.addComponent(new MockHealthComponent());

      // Create target
      const target = world.createEntity();
      target.addComponent(new MockTransformComponent(120, 120));
      target.addComponent(new MockHealthComponent(50));

      // Force combat state
      const ai = attacker.getComponent(AIComponent);
      ai.tacticalContext.alertLevel = 'combat';

      // Run AI system multiple times
      for (let i = 0; i < 10; i++) {
        aiSystem.update(16.67);
      }

      const targetHealth = target.getComponent(MockHealthComponent);
      expect(targetHealth.currentHealth).toBeLessThan(50); // Should have taken damage
    });

    test('should handle entity death and cleanup', () => {
      const entity = world.createEntity();
      const health = new MockHealthComponent(10);
      entity.addComponent(new MockTransformComponent());
      entity.addComponent(health);

      // Deal fatal damage
      health.takeDamage(15);

      expect(health.isAlive).toBe(false);
      expect(health.currentHealth).toBe(0);
    });
  });

  describe('Performance Integration', () => {
    test('should handle many entities efficiently', () => {
      const entities = [];
      
      // Create many AI entities
      for (let i = 0; i < 50; i++) {
        const entity = world.createEntity();
        entity.addComponent(new MockTransformComponent(i * 10, i * 10));
        entity.addComponent(new MockMovementComponent());
        entity.addComponent(new AIComponent({ decisionInterval: 500 }));
        entity.addComponent(new MockHealthComponent());
        entities.push(entity);
      }

      const start = performance.now();
      
      // Run multiple updates
      for (let i = 0; i < 10; i++) {
        world.update(16.67);
      }
      
      const duration = performance.now() - start;
      
      expect(duration).toBeLessThan(1000); // Should complete within 1 second
      expect(world.entities.size).toBe(50);
    });

    test('should maintain stable frame rate with complex interactions', () => {
      // Create entities with complex interactions
      const entities = [];
      for (let i = 0; i < 20; i++) {
        const entity = world.createEntity();
        entity.addComponent(new MockTransformComponent(
          Math.random() * 500,
          Math.random() * 500
        ));
        entity.addComponent(new MockMovementComponent());
        entity.addComponent(new AIComponent({
          behaviorType: 'combatUnit',
          decisionInterval: 200,
          adaptiveDecisionTiming: true
        }));
        entity.addComponent(new MockHealthComponent());
        entities.push(entity);
      }

      const frameTimes = [];
      
      // Measure frame times
      for (let i = 0; i < 20; i++) {
        const start = performance.now();
        world.update(16.67);
        frameTimes.push(performance.now() - start);
      }

      const averageFrameTime = frameTimes.reduce((a, b) => a + b) / frameTimes.length;
      const maxFrameTime = Math.max(...frameTimes);

      expect(averageFrameTime).toBeLessThan(50); // 50ms average
      expect(maxFrameTime).toBeLessThan(100); // 100ms max
    });
  });

  describe('State Synchronization', () => {
    test('should maintain consistent state across systems', () => {
      const entity = world.createEntity();
      const transform = new MockTransformComponent(100, 100);
      const ai = new AIComponent();
      
      entity.addComponent(transform);
      entity.addComponent(ai);
      entity.addComponent(new MockMovementComponent());

      // Run multiple update cycles
      for (let i = 0; i < 5; i++) {
        world.update(16.67);
      }

      // Verify entity state is consistent
      expect(entity.isValid()).toBe(true);
      expect(transform.x).toBeGreaterThanOrEqual(0);
      expect(transform.y).toBeGreaterThanOrEqual(0);
      expect(ai.currentState).toBeDefined();
    });

    test('should handle system failures gracefully', () => {
      const entity = world.createEntity();
      entity.addComponent(new MockTransformComponent());
      entity.addComponent(new AIComponent());

      // Cause AI system to throw error
      const originalUpdate = aiSystem.update;
      aiSystem.update = jest.fn(() => {
        throw new Error('System failure');
      });

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      // Should not crash the world
      expect(() => {
        world.update(16.67);
      }).not.toThrow();

      expect(world.entities.has(entity)).toBe(true);

      consoleSpy.mockRestore();
      aiSystem.update = originalUpdate;
    });
  });

  describe('Memory Management Integration', () => {
    test('should properly clean up when systems are destroyed', () => {
      const entities = [];
      
      for (let i = 0; i < 10; i++) {
        const entity = world.createEntity();
        entity.addComponent(new MockTransformComponent());
        entity.addComponent(new AIComponent());
        entities.push(entity);
      }

      expect(aiSystem.entities.size).toBe(10);

      // Destroy world
      world.destroy();

      expect(aiSystem.destroyed).toBe(true);
      expect(movementSystem.destroyed).toBe(true);
      expect(world.entities.size).toBe(0);
    });

    test('should handle memory leaks in integrated systems', () => {
      // Create entities that might cause memory leaks
      const oldEntities = [];
      
      for (let i = 0; i < 5; i++) {
        const entity = world.createEntity();
        entity.addComponent(new MockTransformComponent());
        entity.addComponent(new AIComponent());
        entity.creationTime = Date.now() - 400000; // Very old entity
        oldEntities.push(entity);
      }

      const leaks = world.detectMemoryLeaks();
      
      expect(leaks).toBeDefined();
      expect(leaks.longLivedEntities.length).toBe(5);
    });
  });

  describe('Cross-System Communication', () => {
    test('should allow systems to communicate through world state', () => {
      const entity = world.createEntity();
      entity.addComponent(new MockTransformComponent(100, 100));
      entity.addComponent(new MockMovementComponent());
      entity.addComponent(new AIComponent());

      // AI system makes decision to move
      aiSystem.update(16.67);

      const movement = entity.getComponent(MockMovementComponent);
      const initialTarget = movement.target;

      // Movement system executes the movement
      movementSystem.update(16.67);

      const transform = entity.getComponent(MockTransformComponent);
      
      if (initialTarget) {
        // Should be moving towards target
        expect(transform.x).not.toBe(100);
        expect(transform.y).not.toBe(100);
      }
    });

    test('should handle cascading system effects', () => {
      // Create two entities that should interact
      const entity1 = world.createEntity();
      entity1.addComponent(new MockTransformComponent(100, 100));
      entity1.addComponent(new AIComponent({ behaviorType: 'combatUnit' }));
      entity1.addComponent(new MockHealthComponent());

      const entity2 = world.createEntity();
      entity2.addComponent(new MockTransformComponent(120, 120));
      entity2.addComponent(new AIComponent({ behaviorType: 'combatUnit' }));
      entity2.addComponent(new MockHealthComponent());

      // Run systems and observe interactions
      for (let i = 0; i < 5; i++) {
        world.update(16.67);
      }

      const ai1 = entity1.getComponent(AIComponent);
      const ai2 = entity2.getComponent(AIComponent);

      // Both AIs should be aware of each other
      expect(ai1.tacticalContext.enemiesNearby).toBeGreaterThan(0);
      expect(ai2.tacticalContext.enemiesNearby).toBeGreaterThan(0);
    });
  });
});