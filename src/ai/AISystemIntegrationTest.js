/**
 * AI System Integration Test
 * Demonstrates the integration of the new AI system with the existing ECS
 * Tests performance, functionality, and graceful degradation
 */

import { World } from '../ecs/World.js';
import { AISystem } from './systems/AISystem.js';
import { AIComponent } from './components/AIComponent.js';
import { 
    TransformComponent, 
    VelocityComponent, 
    HealthComponent, 
    MovementComponent,
    CombatComponent
} from '../ecs/Component.js';

/**
 * Integration test suite for AI system
 */
export class AISystemIntegrationTest {
    constructor() {
        this.world = null;
        this.aiSystem = null;
        this.testEntities = [];
        this.testResults = {
            totalTests: 0,
            passedTests: 0,
            failedTests: 0,
            errors: [],
            performance: {
                averageFrameTime: 0,
                maxFrameTime: 0,
                frameBudgetViolations: 0
            }
        };
    }
    
    /**
     * Run all integration tests
     */
    async runAllTests() {
        console.log('🧪 Starting AI System Integration Tests...');
        
        try {
            await this.setupTestEnvironment();
            await this.testBasicIntegration();
            await this.testAIDecisionMaking();
            await this.testPerformanceBudget();
            await this.testGracefulDegradation();
            await this.testEntityLifecycle();
            
            this.printTestResults();
            
        } catch (error) {
            console.error('❌ Test suite failed:', error);
            this.testResults.errors.push(`Test suite failure: ${error.message}`);
        } finally {
            this.cleanup();
        }
        
        return this.testResults;
    }
    
    /**
     * Set up test environment
     */
    async setupTestEnvironment() {
        console.log('🔧 Setting up test environment...');
        
        // Create world and AI system
        this.world = new World();
        this.aiSystem = new AISystem(this.world);
        this.world.addSystem(this.aiSystem);
        
        // Wait for AI system initialization
        let attempts = 0;
        while (!this.aiSystem.isAIInitialized && attempts < 30) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (!this.aiSystem.isAIInitialized) {
            console.warn('⚠️ AI system not fully initialized, testing degraded mode');
        }
        
        console.log('✅ Test environment ready');
    }
    
    /**
     * Test basic ECS integration
     */
    async testBasicIntegration() {
        console.log('🔍 Testing basic ECS integration...');
        
        try {
            // Test 1: AI System should be added to world
            this.assertTrue(this.world.systems.includes(this.aiSystem), 'AI System added to world');
            
            // Test 2: Create entity with AI component
            const entity = this.createTestEntity('basic');
            this.assertTrue(entity.hasComponent(AIComponent), 'Entity has AI component');
            
            // Test 3: AI System should track the entity
            this.assertTrue(this.aiSystem.entities.has(entity), 'AI System tracks AI entities');
            
            // Test 4: Update cycle should work without errors
            this.world.update(16.67); // 60 FPS
            this.assertTrue(true, 'Update cycle completed without errors');
            
            console.log('✅ Basic integration tests passed');
            
        } catch (error) {
            this.recordTestFailure('Basic Integration', error);
        }
    }
    
    /**
     * Test AI decision making pipeline
     */
    async testAIDecisionMaking() {
        console.log('🧠 Testing AI decision making...');
        
        try {
            // Create test entities
            const combatEntity = this.createTestEntity('combat');
            const harvesterEntity = this.createTestEntity('harvester');
            
            const combatAI = combatEntity.getComponent(AIComponent);
            const harvesterAI = harvesterEntity.getComponent(AIComponent);
            
            // Test 1: AI components should be properly initialized
            this.assertTrue(combatAI.enabled, 'Combat AI is enabled');
            this.assertTrue(harvesterAI.enabled, 'Harvester AI is enabled');
            
            // Test 2: Different behavior types should be set
            this.assertEqual(combatAI.behaviorType, 'combatUnit', 'Combat unit behavior type');
            this.assertEqual(harvesterAI.behaviorType, 'harvester', 'Harvester behavior type');
            
            // Test 3: Decision timing should work
            this.assertTrue(combatAI.shouldMakeDecision(), 'Combat AI should make initial decision');
            
            // Test 4: Run several update cycles to trigger decisions
            for (let i = 0; i < 10; i++) {
                this.world.update(16.67);
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            
            // Test 5: AI should have made decisions
            this.assertTrue(combatAI.lastDecisionTime > 0, 'Combat AI made decisions');
            this.assertTrue(harvesterAI.lastDecisionTime > 0, 'Harvester AI made decisions');
            
            console.log('✅ AI decision making tests passed');
            
        } catch (error) {
            this.recordTestFailure('AI Decision Making', error);
        }
    }
    
    /**
     * Test performance budget compliance
     */
    async testPerformanceBudget() {
        console.log('⏱️ Testing performance budget...');
        
        try {
            // Create many AI entities to stress test
            const entityCount = 50;
            const stressEntities = [];
            
            for (let i = 0; i < entityCount; i++) {
                stressEntities.push(this.createTestEntity('combat'));
            }
            
            // Measure frame times over multiple updates
            const frameTimes = [];
            const targetBudget = 10; // 10ms budget
            
            for (let frame = 0; frame < 30; frame++) {
                const startTime = performance.now();
                this.world.update(16.67);
                const frameTime = performance.now() - startTime;
                frameTimes.push(frameTime);
                
                if (frameTime > targetBudget) {
                    this.testResults.performance.frameBudgetViolations++;
                }
                
                await new Promise(resolve => setTimeout(resolve, 1));
            }
            
            // Calculate performance metrics
            const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
            const maxFrameTime = Math.max(...frameTimes);
            
            this.testResults.performance.averageFrameTime = avgFrameTime;
            this.testResults.performance.maxFrameTime = maxFrameTime;
            
            // Test 1: Average frame time should be reasonable
            this.assertTrue(avgFrameTime < targetBudget * 2, `Average frame time (${avgFrameTime.toFixed(2)}ms) within 2x budget`);
            
            // Test 2: No more than 20% frame budget violations
            const violationRate = this.testResults.performance.frameBudgetViolations / frameTimes.length;
            this.assertTrue(violationRate < 0.2, `Frame budget violation rate (${(violationRate * 100).toFixed(1)}%) under 20%`);
            
            // Test 3: AI system should report reasonable performance
            const aiStatus = this.aiSystem.getSystemStatus();
            this.assertTrue(aiStatus.performance.performanceClass !== 'critical', 'AI system not in critical performance state');
            
            console.log(`✅ Performance tests passed (avg: ${avgFrameTime.toFixed(2)}ms, max: ${maxFrameTime.toFixed(2)}ms)`);
            
        } catch (error) {
            this.recordTestFailure('Performance Budget', error);
        }
    }
    
    /**
     * Test graceful degradation when AI fails
     */
    async testGracefulDegradation() {
        console.log('🛡️ Testing graceful degradation...');
        
        try {
            // Test 1: System should handle entities without AI gracefully
            const nonAIEntity = this.world.createEntity();
            nonAIEntity.addComponent(new TransformComponent(100, 100));
            
            this.world.update(16.67);
            this.assertTrue(nonAIEntity.isValid(), 'Non-AI entities should continue working');
            
            // Test 2: System should handle disabled AI components
            const aiEntity = this.createTestEntity('combat');
            const aiComponent = aiEntity.getComponent(AIComponent);
            aiComponent.enabled = false;
            
            this.world.update(16.67);
            this.assertTrue(aiEntity.isValid(), 'Entities with disabled AI should continue working');
            
            // Test 3: System should continue working even if TensorFlow fails
            const systemStatus = this.aiSystem.getSystemStatus();
            this.assertTrue(systemStatus.enabled, 'AI system remains enabled even with potential TensorFlow issues');
            
            console.log('✅ Graceful degradation tests passed');
            
        } catch (error) {
            this.recordTestFailure('Graceful Degradation', error);
        }
    }
    
    /**
     * Test entity lifecycle with AI
     */
    async testEntityLifecycle() {
        console.log('🔄 Testing entity lifecycle...');
        
        try {
            // Test 1: Entity creation and AI initialization
            const entity = this.createTestEntity('guard');
            const aiComponent = entity.getComponent(AIComponent);
            
            this.assertTrue(this.aiSystem.entities.has(entity), 'New entity added to AI system');
            this.assertNotNull(aiComponent.qLearning, 'Q-learning component initialized');
            
            // Test 2: Entity updates and state changes
            aiComponent.setState('combat');
            this.assertEqual(aiComponent.currentState, 'combat', 'AI state updated correctly');
            
            // Test 3: Entity removal and cleanup
            entity.active = false;
            this.world.update(16.67); // This should trigger cleanup
            
            this.assertFalse(this.aiSystem.entities.has(entity), 'Removed entity cleaned up from AI system');
            this.assertTrue(aiComponent.destroyed, 'AI component properly destroyed');
            
            console.log('✅ Entity lifecycle tests passed');
            
        } catch (error) {
            this.recordTestFailure('Entity Lifecycle', error);
        }
    }
    
    /**
     * Create a test entity with specified AI type
     */
    createTestEntity(aiType = 'combatUnit') {
        const entity = this.world.createEntity();
        
        // Add basic components
        entity.addComponent(new TransformComponent(
            Math.random() * 800, 
            Math.random() * 600
        ));
        entity.addComponent(new VelocityComponent());
        entity.addComponent(new HealthComponent(100));
        entity.addComponent(new MovementComponent());
        entity.addComponent(new CombatComponent());
        
        // Add AI component with appropriate configuration
        const aiConfig = {
            behaviorType: aiType === 'combat' ? 'combatUnit' : aiType, // Fix behavior type mapping
            enableQLearning: true,
            decisionInterval: 100, // Faster decisions for testing
            debugMode: true
        };
        
        entity.addComponent(new AIComponent(aiConfig));
        
        this.testEntities.push(entity);
        return entity;
    }
    
    /**
     * Assertion helpers
     */
    assertTrue(condition, message) {
        this.testResults.totalTests++;
        if (condition) {
            this.testResults.passedTests++;
        } else {
            this.testResults.failedTests++;
            this.testResults.errors.push(`ASSERT TRUE FAILED: ${message}`);
            throw new Error(`Assertion failed: ${message}`);
        }
    }
    
    assertFalse(condition, message) {
        this.assertTrue(!condition, message);
    }
    
    assertEqual(actual, expected, message) {
        this.assertTrue(actual === expected, `${message} (expected: ${expected}, actual: ${actual})`);
    }
    
    assertNotNull(value, message) {
        this.assertTrue(value !== null && value !== undefined, message);
    }
    
    /**
     * Record test failure
     */
    recordTestFailure(testName, error) {
        this.testResults.failedTests++;
        this.testResults.errors.push(`${testName}: ${error.message}`);
        console.error(`❌ ${testName} failed:`, error);
    }
    
    /**
     * Print comprehensive test results
     */
    printTestResults() {
        console.log('\n🏁 AI System Integration Test Results');
        console.log('======================================');
        console.log(`Total Tests: ${this.testResults.totalTests}`);
        console.log(`Passed: ${this.testResults.passedTests}`);
        console.log(`Failed: ${this.testResults.failedTests}`);
        console.log(`Success Rate: ${((this.testResults.passedTests / this.testResults.totalTests) * 100).toFixed(1)}%`);
        
        console.log('\nPerformance Metrics:');
        console.log(`Average Frame Time: ${this.testResults.performance.averageFrameTime.toFixed(2)}ms`);
        console.log(`Max Frame Time: ${this.testResults.performance.maxFrameTime.toFixed(2)}ms`);
        console.log(`Frame Budget Violations: ${this.testResults.performance.frameBudgetViolations}`);
        
        if (this.aiSystem) {
            const systemStatus = this.aiSystem.getSystemStatus();
            console.log('\nAI System Status:');
            console.log(`Enabled: ${systemStatus.enabled}`);
            console.log(`Initialized: ${systemStatus.initialized}`);
            console.log(`Entity Count: ${systemStatus.entityCount}`);
            console.log(`Performance Class: ${systemStatus.performance.performanceClass}`);
            console.log(`TensorFlow Backend: ${systemStatus.tensorFlow.backend || 'none'}`);
        }
        
        if (this.testResults.errors.length > 0) {
            console.log('\nErrors:');
            this.testResults.errors.forEach((error, index) => {
                console.log(`${index + 1}. ${error}`);
            });
        }
        
        const overallResult = this.testResults.failedTests === 0 ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED';
        console.log(`\n${overallResult}\n`);
    }
    
    /**
     * Cleanup test resources
     */
    cleanup() {
        if (this.world) {
            this.world.destroy();
        }
        this.testEntities = [];
    }
}

/**
 * Simple test runner function
 */
export async function runAIIntegrationTest() {
    const testSuite = new AISystemIntegrationTest();
    return await testSuite.runAllTests();
}

// Export for use in browser console or testing environments
if (typeof window !== 'undefined') {
    window.runAIIntegrationTest = runAIIntegrationTest;
    window.AISystemIntegrationTest = AISystemIntegrationTest;
}