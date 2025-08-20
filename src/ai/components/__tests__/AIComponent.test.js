/**
 * Unit Tests for AIComponent
 * Tests core AI functionality, decision making, learning, and state management
 */

import { AIComponent } from "../AIComponent.js";
import { Component } from "../../../ecs/Component.js";

describe("AIComponent", () => {
    let aiComponent;
    let mockEntity;

    beforeEach(() => {
    // Create fresh AI component for each test
        aiComponent = new AIComponent();
    
        // Create mock entity
        mockEntity = createMockEntity("test-ai-entity");
        aiComponent.entity = mockEntity;
    });

    afterEach(() => {
    // Clean up
        if (aiComponent && !aiComponent.destroyed) {
            aiComponent.destroy();
        }
    });

    describe("Component Creation and Initialization", () => {
        test("should create AIComponent with default values", () => {
            expect(aiComponent).toBeInstanceOf(Component);
            expect(aiComponent.enabled).toBe(true);
            expect(aiComponent.behaviorType).toBe("combatUnit");
            expect(aiComponent.aiLevel).toBe("normal");
            expect(aiComponent.currentState).toBe("idle");
            expect(aiComponent.learningEnabled).toBe(true);
        });

        test("should create AIComponent with custom options", () => {
            const customOptions = {
                enabled: false,
                behaviorType: "harvester",
                aiLevel: "expert",
                decisionInterval: 1000,
                epsilon: 0.2,
                debugMode: true
            };

            const customAI = new AIComponent(customOptions);

            expect(customAI.enabled).toBe(false);
            expect(customAI.behaviorType).toBe("harvester");
            expect(customAI.aiLevel).toBe("expert");
            expect(customAI.decisionInterval).toBe(1000);
            expect(customAI.qLearningConfig.epsilon).toBe(0.2);
            expect(customAI.debugMode).toBe(true);

            customAI.destroy();
        });

        test("should initialize with proper memory structures", () => {
            expect(aiComponent.memory.knownEnemies).toBeInstanceOf(Map);
            expect(aiComponent.memory.knownResources).toBeInstanceOf(Map);
            expect(aiComponent.memory.patrolPoints).toEqual([]);
            expect(aiComponent.memory.lastObjectives).toEqual([]);
        });

        test("should initialize with proper tactical context", () => {
            expect(aiComponent.tacticalContext.alertLevel).toBe("normal");
            expect(aiComponent.tacticalContext.enemiesNearby).toBe(0);
            expect(aiComponent.tacticalContext.alliesNearby).toBe(0);
            expect(aiComponent.tacticalContext.resourcesNearby).toBe(0);
        });
    });

    describe("State Management", () => {
        test("should set and track state changes", () => {
            expect(aiComponent.currentState).toBe("idle");
      
            aiComponent.setState("thinking");
      
            expect(aiComponent.currentState).toBe("thinking");
            expect(aiComponent.stateHistory).toHaveLength(1);
            expect(aiComponent.stateHistory[0].state).toBe("thinking");
            expect(aiComponent.stateHistory[0].previousState).toBe("idle");
        });

        test("should not change state if already in that state", () => {
            const initialHistoryLength = aiComponent.stateHistory.length;
      
            aiComponent.setState("idle");
      
            expect(aiComponent.stateHistory).toHaveLength(initialHistoryLength);
        });

        test("should maintain state history with maximum length", () => {
            // Fill state history beyond maximum
            for (let i = 0; i < 25; i++) {
                aiComponent.setState(`state-${i}`);
            }
      
            expect(aiComponent.stateHistory.length).toBeLessThanOrEqual(aiComponent.maxStateHistoryLength);
            expect(aiComponent.stateHistory.length).toBe(aiComponent.maxStateHistoryLength);
        });

        test("should log state changes in debug mode", () => {
            aiComponent.debugMode = true;
            aiComponent.entity = { id: "test-123" };
      
            const consoleSpy = jest.spyOn(console, "log").mockImplementation();
      
            aiComponent.setState("combat");
      
            expect(consoleSpy).toHaveBeenCalledWith(
                expect.stringContaining("AI Entity test-123: idle → combat")
            );
      
            consoleSpy.mockRestore();
        });
    });

    describe("Decision Making", () => {
        test("should determine when to make decisions based on timing", () => {
            // Fresh component should be ready for decision
            expect(aiComponent.shouldMakeDecision()).toBe(true);
      
            // After marking decision made, should not be ready immediately
            aiComponent.markDecisionMade();
            expect(aiComponent.shouldMakeDecision()).toBe(false);
      
            // After enough time passes, should be ready again
            const futureTime = Date.now() + aiComponent.decisionInterval + 100;
            jest.spyOn(Date, "now").mockReturnValue(futureTime);
      
            expect(aiComponent.shouldMakeDecision()).toBe(true);
      
            Date.now.mockRestore();
        });

        test("should adapt decision timing based on alert level", () => {
            aiComponent.adaptiveDecisionTiming = true;
            aiComponent.tacticalContext.alertLevel = "combat";
      
            const originalInterval = aiComponent.decisionInterval;
            aiComponent.markDecisionMade();
      
            // In combat, should be ready for decisions faster
            const combatTime = Date.now() + (originalInterval * 0.5) + 10;
            jest.spyOn(Date, "now").mockReturnValue(combatTime);
      
            expect(aiComponent.shouldMakeDecision()).toBe(true);
      
            Date.now.mockRestore();
        });

        test("should mark decisions and update state", () => {
            const decision = { action: "move", target: { x: 100, y: 100 } };
      
            aiComponent.markDecisionMade(decision);
      
            expect(aiComponent.debugInfo.lastDecision).toEqual(decision);
            expect(aiComponent.currentState).toBe("acting");
            expect(aiComponent.lastDecisionTime).toBeGreaterThan(0);
        });

        test("should update performance metrics on decision", () => {
            const initialMetrics = { ...aiComponent.performanceMetrics };
      
            aiComponent.markDecisionMade();
      
            // Performance metrics should be updated
            expect(aiComponent.performanceMetrics).not.toEqual(initialMetrics);
        });
    });

    describe("Tactical Context Updates", () => {
        test("should update tactical context with game state", () => {
            const mockGameState = {
                nearbyEntities: [
                    { entity: createMockEntity("enemy-1"), distance: 50 },
                    { entity: createMockEntity("enemy-2"), distance: 150 }
                ]
            };
      
            aiComponent.updateTacticalContext(mockGameState);
      
            expect(aiComponent.tacticalContext.enemiesNearby).toBe(2);
        });

        test("should update alert level based on threats", () => {
            // Test damage taken increases alert
            aiComponent.tacticalContext.lastDamageTaken = Date.now();
            aiComponent.updateAlertLevel();
            expect(aiComponent.tacticalContext.alertLevel).toBe("combat");
      
            // Test enemies nearby increases alert
            aiComponent.tacticalContext.lastDamageTaken = 0;
            aiComponent.tacticalContext.enemiesNearby = 2;
            aiComponent.updateAlertLevel();
            expect(aiComponent.tacticalContext.alertLevel).toBe("alert");
      
            // Test being outnumbered causes panic
            aiComponent.tacticalContext.enemiesNearby = 5;
            aiComponent.tacticalContext.alliesNearby = 1;
            aiComponent.updateAlertLevel();
            expect(aiComponent.tacticalContext.alertLevel).toBe("panic");
        });

        test("should handle null game state gracefully", () => {
            expect(() => {
                aiComponent.updateTacticalContext(null);
            }).not.toThrow();
      
            expect(() => {
                aiComponent.updateTacticalContext(undefined);
            }).not.toThrow();
        });
    });

    describe("Memory Management", () => {
        test("should update memory with nearby entities", () => {
            const mockGameState = {
                nearbyEntities: [
                    {
                        entity: {
                            id: "enemy-123",
                            getComponent: jest.fn(() => ({ x: 100, y: 200 }))
                        },
                        distance: 75,
                        angle: 45
                    }
                ]
            };
      
            aiComponent.updateMemory(mockGameState);
      
            expect(aiComponent.memory.knownEnemies.has("enemy-123")).toBe(true);
            const enemyInfo = aiComponent.memory.knownEnemies.get("enemy-123");
            expect(enemyInfo.distance).toBe(75);
            expect(enemyInfo.angle).toBe(45);
        });

        test("should clean up old memory entries", () => {
            // Add old memory entry
            const oldTime = Date.now() - 60000; // 60 seconds ago
            aiComponent.memory.knownEnemies.set("old-enemy", {
                lastSeen: oldTime,
                position: { x: 0, y: 0 }
            });
      
            // Update memory (this should trigger cleanup)
            aiComponent.updateMemory({ nearbyEntities: [] });
      
            expect(aiComponent.memory.knownEnemies.has("old-enemy")).toBe(false);
        });

        test("should identify primary threat", () => {
            // Add multiple threats
            aiComponent.memory.knownEnemies.set("far-enemy", {
                distance: 200,
                position: { x: 200, y: 0 }
            });
      
            aiComponent.memory.knownEnemies.set("close-enemy", {
                distance: 50,
                position: { x: 50, y: 0 }
            });
      
            const primaryThreat = aiComponent.getPrimaryThreat();
      
            expect(primaryThreat.distance).toBe(50);
        });

        test("should return null when no threats exist", () => {
            const primaryThreat = aiComponent.getPrimaryThreat();
            expect(primaryThreat).toBeNull();
        });
    });

    describe("Learning and Experience", () => {
        test("should learn from positive experiences", () => {
            const initialExperience = aiComponent.experienceLevel;
            const initialInterval = aiComponent.decisionInterval;
      
            aiComponent.learnFromExperience(0.8, "move", "success");
      
            expect(aiComponent.experienceLevel).toBeGreaterThan(initialExperience);
            expect(aiComponent.debugInfo.lastReward).toBe(0.8);
        });

        test("should adapt decision timing based on performance", () => {
            const initialInterval = aiComponent.decisionInterval;
      
            // Good reward should increase interval slightly (think more)
            aiComponent.learnFromExperience(0.6, "attack", "success");
            expect(aiComponent.decisionInterval).toBeGreaterThan(initialInterval);
      
            // Bad reward should decrease interval (react faster)
            aiComponent.decisionInterval = initialInterval;
            aiComponent.learnFromExperience(-0.6, "retreat", "failure");
            expect(aiComponent.decisionInterval).toBeLessThan(initialInterval);
        });

        test("should respect learning enabled flag", () => {
            aiComponent.learningEnabled = false;
            const initialExperience = aiComponent.experienceLevel;
      
            aiComponent.learnFromExperience(1.0, "move", "success");
      
            expect(aiComponent.experienceLevel).toBe(initialExperience);
        });

        test("should cap experience level at maximum", () => {
            aiComponent.experienceLevel = 99;
      
            // Large positive reward
            aiComponent.learnFromExperience(5.0, "move", "success");
      
            expect(aiComponent.experienceLevel).toBeLessThanOrEqual(100);
        });
    });

    describe("Q-Learning Integration", () => {
        test("should configure Q-learning parameters", () => {
            const newConfig = {
                epsilon: 0.05,
                learningRate: 0.002,
                discountFactor: 0.99
            };
      
            aiComponent.configureQLearning(newConfig);
      
            expect(aiComponent.qLearningConfig.epsilon).toBe(0.05);
            expect(aiComponent.qLearningConfig.learningRate).toBe(0.002);
            expect(aiComponent.qLearningConfig.discountFactor).toBe(0.99);
        });

        test("should update existing Q-learning component when configured", () => {
            // Mock Q-learning component
            const mockQLearning = {
                epsilon: 0.1,
                learningRate: 0.001,
                discountFactor: 0.95,
                setTrainingMode: jest.fn(),
                receiveReward: jest.fn(),
                destroy: jest.fn()
            };
      
            aiComponent.qLearning = mockQLearning;
      
            aiComponent.configureQLearning({ epsilon: 0.05 });
      
            expect(mockQLearning.epsilon).toBe(0.05);
        });
    });

    describe("Utility Methods", () => {
        test("should provide comprehensive AI status", () => {
            const status = aiComponent.getAIStatus();
      
            expect(status).toHaveProperty("enabled");
            expect(status).toHaveProperty("state");
            expect(status).toHaveProperty("behaviorType");
            expect(status).toHaveProperty("experienceLevel");
            expect(status).toHaveProperty("alertLevel");
            expect(status).toHaveProperty("performanceMetrics");
            expect(status).toHaveProperty("memorySize");
        });

        test("should include debug info when debug mode enabled", () => {
            aiComponent.debugMode = true;
            const status = aiComponent.getAIStatus();
      
            expect(status.debugInfo).toBeDefined();
            expect(status.debugInfo).toHaveProperty("lastDecision");
            expect(status.debugInfo).toHaveProperty("lastAction");
        });

        test("should not include debug info when debug mode disabled", () => {
            aiComponent.debugMode = false;
            const status = aiComponent.getAIStatus();
      
            expect(status.debugInfo).toBeNull();
        });

        test("should set behavior tree", () => {
            const mockBehaviorTree = { type: "combat", nodes: [] };
      
            aiComponent.setBehaviorTree(mockBehaviorTree);
      
            expect(aiComponent.behaviorTree).toBe(mockBehaviorTree);
        });

        test("should manage patrol points", () => {
            aiComponent.addPatrolPoint(100, 100);
            aiComponent.addPatrolPoint(200, 200);
      
            expect(aiComponent.memory.patrolPoints).toHaveLength(2);
            expect(aiComponent.memory.patrolPoints[0]).toEqual({ x: 100, y: 100 });
      
            aiComponent.clearPatrolPoints();
      
            expect(aiComponent.memory.patrolPoints).toHaveLength(0);
        });

        test("should set home position", () => {
            aiComponent.setHomePosition(150, 300);
      
            expect(aiComponent.memory.homePosition).toEqual({ x: 150, y: 300 });
        });

        test("should toggle learning enabled", () => {
            const mockQLearning = { setTrainingMode: jest.fn() };
            aiComponent.qLearning = mockQLearning;
      
            aiComponent.setLearningEnabled(false);
      
            expect(aiComponent.learningEnabled).toBe(false);
            expect(mockQLearning.setTrainingMode).toHaveBeenCalledWith(false);
        });
    });

    describe("Component Lifecycle", () => {
        test("should reset to initial state", () => {
            // Modify state
            aiComponent.setState("combat");
            aiComponent.experienceLevel = 50;
            aiComponent.tacticalContext.alertLevel = "panic";
            aiComponent.memory.knownEnemies.set("enemy", { data: "test" });
      
            // Reset
            aiComponent.reset();
      
            expect(aiComponent.currentState).toBe("idle");
            expect(aiComponent.experienceLevel).toBe(0);
            expect(aiComponent.tacticalContext.alertLevel).toBe("normal");
            expect(aiComponent.memory.knownEnemies.size).toBe(0);
        });

        test("should clean up resources on destroy", () => {
            const mockQLearning = { destroy: jest.fn() };
            aiComponent.qLearning = mockQLearning;
            aiComponent.memory.knownEnemies.set("enemy", {});
      
            aiComponent.destroy();
      
            expect(mockQLearning.destroy).toHaveBeenCalled();
            expect(aiComponent.qLearning).toBeNull();
            expect(aiComponent.memory.knownEnemies.size).toBe(0);
            expect(aiComponent.destroyed).toBe(true);
        });

        test("should handle multiple destroy calls gracefully", () => {
            expect(() => {
                aiComponent.destroy();
                aiComponent.destroy();
            }).not.toThrow();
        });
    });

    describe("Performance and Edge Cases", () => {
        test("should handle rapid state changes", () => {
            for (let i = 0; i < 100; i++) {
                aiComponent.setState(`state-${i % 5}`);
            }
      
            expect(aiComponent.stateHistory.length).toBeLessThanOrEqual(aiComponent.maxStateHistoryLength);
        });

        test("should handle empty nearby entities", () => {
            const gameState = { nearbyEntities: [] };
      
            expect(() => {
                aiComponent.updateTacticalContext(gameState);
            }).not.toThrow();
      
            expect(aiComponent.tacticalContext.enemiesNearby).toBe(0);
        });

        test("should handle malformed game state", () => {
            const malformedStates = [
                { nearbyEntities: null },
                { nearbyEntities: undefined },
                { nearbyEntities: [{ entity: null }] },
                { nearbyEntities: [{ distance: "invalid" }] }
            ];
      
            malformedStates.forEach(state => {
                expect(() => {
                    aiComponent.updateTacticalContext(state);
                }).not.toThrow();
            });
        });

        test("should maintain performance with large memory", () => {
            // Add many memory entries
            for (let i = 0; i < 1000; i++) {
                aiComponent.memory.knownEnemies.set(`enemy-${i}`, {
                    lastSeen: Date.now(),
                    distance: Math.random() * 500
                });
            }
      
            const start = performance.now();
            const primaryThreat = aiComponent.getPrimaryThreat();
            const end = performance.now();
      
            expect(end - start).toBeLessThan(100); // Should complete in under 100ms
            expect(primaryThreat).toBeDefined();
        });
    });
});