/**
 * Advanced AI System for ECS Integration
 * Integrates TensorFlow.js, Q-learning, and Behavior Trees for intelligent unit decisions
 * Respects frame budget and provides graceful degradation
 */

import { System } from '../../ecs/System.js';
import { TransformComponent } from '../../ecs/Component.js';
import { TensorFlowManager } from '../TensorFlowManager.js';
import { QLearningComponent } from '../components/QLearningComponent.js';
import { TreeNode, NodeStatus, createNodeFromConfigSync } from '../behaviorTree/TreeNode.js';
import { SelectorNode, SequenceNode, ActionNode } from '../behaviorTree/BasicNodes.js';

// Import the unified AI component
import { AIComponent } from '../components/AIComponent.js';

/**
 * Performance monitoring for AI system
 */
class AIPerformanceMonitor {
    constructor() {
        this.frameBudget = 10; // 10ms budget per frame for AI
        this.currentFrameTime = 0;
        this.totalProcessingTime = 0;
        this.processedEntities = 0;
        this.skippedEntities = 0;
        this.averageEntityTime = 0;
        this.performanceClass = 'normal'; // normal, degraded, critical
        
        // Statistics for adaptation
        this.frameHistory = [];
        this.maxHistoryLength = 60; // 1 second at 60 FPS
        this.lastPerformanceCheck = Date.now();
        this.performanceCheckInterval = 1000; // Check every second
    }
    
    startFrame() {
        this.currentFrameTime = 0;
        this.processedEntities = 0;
        this.skippedEntities = 0;
    }
    
    recordEntityProcessing(processingTime) {
        this.currentFrameTime += processingTime;
        this.totalProcessingTime += processingTime;
        this.processedEntities++;
        
        // Update running average
        if (this.processedEntities > 0) {
            this.averageEntityTime = this.totalProcessingTime / this.processedEntities;
        }
    }
    
    recordEntitySkipped() {
        this.skippedEntities++;
    }
    
    endFrame() {
        // Store frame performance
        this.frameHistory.push({
            frameTime: this.currentFrameTime,
            processed: this.processedEntities,
            skipped: this.skippedEntities,
            timestamp: Date.now()
        });
        
        // Keep history manageable
        if (this.frameHistory.length > this.maxHistoryLength) {
            this.frameHistory.shift();
        }
        
        // Update performance class
        this.updatePerformanceClass();
    }
    
    hasFrameBudget() {
        return this.currentFrameTime < this.frameBudget;
    }
    
    getRemainingBudget() {
        return Math.max(0, this.frameBudget - this.currentFrameTime);
    }
    
    updatePerformanceClass() {
        const now = Date.now();
        if (now - this.lastPerformanceCheck < this.performanceCheckInterval) {
            return;
        }
        
        this.lastPerformanceCheck = now;
        
        if (this.frameHistory.length === 0) return;
        
        // Calculate average frame time over last second
        const recentFrames = this.frameHistory.slice(-60);
        const avgFrameTime = recentFrames.reduce((sum, frame) => sum + frame.frameTime, 0) / recentFrames.length;
        const avgSkipped = recentFrames.reduce((sum, frame) => sum + frame.skipped, 0) / recentFrames.length;
        
        if (avgFrameTime > this.frameBudget * 1.5 || avgSkipped > 2) {
            this.performanceClass = 'critical';
        } else if (avgFrameTime > this.frameBudget || avgSkipped > 0) {
            this.performanceClass = 'degraded';
        } else {
            this.performanceClass = 'normal';
        }
    }
    
    getPerformanceReport() {
        return {
            frameBudget: this.frameBudget,
            currentFrameTime: this.currentFrameTime,
            remainingBudget: this.getRemainingBudget(),
            averageEntityTime: this.averageEntityTime,
            processedThisFrame: this.processedEntities,
            skippedThisFrame: this.skippedEntities,
            performanceClass: this.performanceClass,
            frameHistory: this.frameHistory.slice(-10) // Last 10 frames
        };
    }
}

/**
 * Main AI System for ECS
 * Coordinates TensorFlow, Q-learning, and Behavior Trees within frame budget
 */
export class AISystem extends System {
    constructor(world) {
        super(world);
        this.requiredComponents = [TransformComponent, AIComponent];
        this.priority = 15; // Run after most other systems
        
        // Initialize AI managers
        this.tensorFlowManager = new TensorFlowManager();
        this.isAIInitialized = false;
        this.initializationAttempts = 0;
        this.maxInitAttempts = 3;
        
        // Performance monitoring
        this.performanceMonitor = new AIPerformanceMonitor();
        
        // Decision scheduling
        this.entityDecisionQueue = [];
        this.currentEntityIndex = 0;
        
        // System state
        this.isSystemEnabled = true;
        this.gracefulDegradation = true;
        
        // Statistics
        this.stats = {
            totalDecisions: 0,
            successfulDecisions: 0,
            failedDecisions: 0,
            averageDecisionTime: 0,
            systemUptime: Date.now()
        };
        
        // Default behavior trees
        this.behaviorTreeTemplates = this.createDefaultBehaviorTrees();
        
        // Start initialization
        this.initializeAISystem();
    }
    
    /**
     * Initialize the AI system asynchronously
     */
    async initializeAISystem() {
        if (this.isAIInitialized) return;
        
        this.initializationAttempts++;
        console.log(`🤖 Initializing AI System (attempt ${this.initializationAttempts}/${this.maxInitAttempts})`);
        
        try {
            // Initialize TensorFlow
            const tfInitialized = await this.tensorFlowManager.initialize();
            
            if (tfInitialized) {
                console.log('✅ AI System initialized successfully');
                this.isAIInitialized = true;
                
                // Run a test to validate everything works
                await this.validateAISystem();
            } else {
                console.warn('⚠️ TensorFlow initialization failed, AI will run in degraded mode');
                this.handleInitializationFailure();
            }
            
        } catch (error) {
            console.error('❌ AI System initialization failed:', error);
            this.handleInitializationFailure();
        }
    }
    
    /**
     * Handle AI initialization failure
     */
    handleInitializationFailure() {
        if (this.initializationAttempts >= this.maxInitAttempts) {
            console.error('💀 AI System failed to initialize after maximum attempts');
            this.isSystemEnabled = false;
        } else {
            console.log('🔄 Retrying AI initialization in degraded mode...');
            // Enable basic AI without TensorFlow
            this.isAIInitialized = true;
            this.gracefulDegradation = true;
        }
    }
    
    /**
     * Validate AI system with test operations
     */
    async validateAISystem() {
        try {
            // Test TensorFlow if available
            if (this.tensorFlowManager.isInitialized) {
                const testResult = await this.tensorFlowManager.testInference();
                if (!testResult.success) {
                    console.warn('⚠️ TensorFlow test failed, disabling ML features');
                    this.gracefulDegradation = true;
                }
            }
            
            console.log('✅ AI System validation completed');
            
        } catch (error) {
            console.error('❌ AI System validation failed:', error);
            this.gracefulDegradation = true;
        }
    }
    
    /**
     * Create default behavior trees for different unit types
     */
    createDefaultBehaviorTrees() {
        const nodeTypes = { SelectorNode, SequenceNode, ActionNode };
        
        return {
            // Basic combat unit behavior
            combatUnit: createNodeFromConfigSync({
                type: 'selector',
                name: 'Combat Unit AI',
                children: [
                    {
                        type: 'sequence',
                        name: 'Combat Sequence',
                        children: [
                            { type: 'action', name: 'Find Enemy', action: 'findEnemy' },
                            { type: 'action', name: 'Attack Enemy', action: 'attackEnemy' }
                        ]
                    },
                    {
                        type: 'sequence',
                        name: 'Patrol Sequence',
                        children: [
                            { type: 'action', name: 'Move to Patrol Point', action: 'patrol' },
                            { type: 'action', name: 'Wait', action: 'wait' }
                        ]
                    },
                    { type: 'action', name: 'Idle', action: 'idle' }
                ]
            }, nodeTypes),
            
            // Harvester unit behavior
            harvester: createNodeFromConfigSync({
                type: 'selector',
                name: 'Harvester AI',
                children: [
                    {
                        type: 'sequence',
                        name: 'Harvest Sequence',
                        children: [
                            { type: 'action', name: 'Find Resource', action: 'findResource' },
                            { type: 'action', name: 'Harvest Resource', action: 'harvest' },
                            { type: 'action', name: 'Return to Base', action: 'returnToBase' }
                        ]
                    },
                    { type: 'action', name: 'Idle', action: 'idle' }
                ]
            }, nodeTypes),
            
            // Guard unit behavior
            guard: createNodeFromConfigSync({
                type: 'selector',
                name: 'Guard AI',
                children: [
                    {
                        type: 'sequence',
                        name: 'Threat Response',
                        children: [
                            { type: 'action', name: 'Detect Threat', action: 'detectThreat' },
                            { type: 'action', name: 'Engage Threat', action: 'engageThreat' }
                        ]
                    },
                    { type: 'action', name: 'Hold Position', action: 'holdPosition' }
                ]
            }, nodeTypes)
        };
    }
    
    /**
     * Add entity to AI system
     */
    onEntityAdded(entity) {
        super.onEntityAdded(entity);
        
        const aiComponent = entity.getComponent(AIComponent);
        if (aiComponent) {
            // Initialize AI component if needed
            this.initializeEntityAI(entity, aiComponent);
            
            // Add to decision queue
            this.entityDecisionQueue.push(entity);
        }
    }
    
    /**
     * Remove entity from AI system
     */
    onEntityRemoved(entity) {
        super.onEntityRemoved(entity);
        
        // Remove from decision queue
        const index = this.entityDecisionQueue.indexOf(entity);
        if (index !== -1) {
            this.entityDecisionQueue.splice(index, 1);
        }
        
        // Cleanup AI resources
        const aiComponent = entity.getComponent(AIComponent);
        if (aiComponent && aiComponent.qLearning) {
            aiComponent.qLearning.destroy();
        }
    }
    
    /**
     * Initialize AI for a specific entity
     */
    initializeEntityAI(entity, aiComponent) {
        try {
            // Initialize Q-learning component if enabled
            if (aiComponent.enableQLearning && !aiComponent.qLearning) {
                aiComponent.qLearning = new QLearningComponent({
                    epsilon: 0.1,
                    learningRate: 0.001,
                    discountFactor: 0.95,
                    isTraining: true
                });
                aiComponent.qLearning.entity = entity;
            }
            
            // Assign behavior tree based on unit type or AI type
            if (!aiComponent.behaviorTree) {
                const behaviorType = aiComponent.behaviorType || 'combatUnit';
                aiComponent.behaviorTree = this.getBehaviorTreeForType(behaviorType);
            }
            
            // Set up decision timing
            if (!aiComponent.lastDecisionTime) {
                aiComponent.lastDecisionTime = Date.now();
                aiComponent.decisionInterval = aiComponent.decisionInterval || 500; // 500ms default
            }
            
        } catch (error) {
            console.error(`Error initializing AI for entity ${entity.id}:`, error);
        }
    }
    
    /**
     * Get behavior tree for specific unit type
     */
    getBehaviorTreeForType(behaviorType) {
        const template = this.behaviorTreeTemplates[behaviorType] || this.behaviorTreeTemplates.combatUnit;
        
        // Clone the tree to avoid shared state
        return this.cloneBehaviorTree(template);
    }
    
    /**
     * Clone a behavior tree for independent use
     */
    cloneBehaviorTree(tree) {
        // Simple clone - in production, implement proper deep cloning
        return tree;
    }
    
    /**
     * Main AI system update
     */
    update(deltaTime) {
        super.update(deltaTime);
        
        if (!this.isSystemEnabled) return;
        
        // Start performance monitoring for this frame
        this.performanceMonitor.startFrame();
        
        try {
            // Process entities within frame budget
            this.processAIEntities(deltaTime);
            
        } catch (error) {
            console.error('Error in AI system update:', error);
        } finally {
            // End performance monitoring
            this.performanceMonitor.endFrame();
        }
    }
    
    /**
     * Process AI entities with frame budget management
     */
    processAIEntities(deltaTime) {
        const entitiesToProcess = Array.from(this.entities);
        let processed = 0;
        
        for (const entity of entitiesToProcess) {
            // Check frame budget before processing each entity
            if (!this.performanceMonitor.hasFrameBudget()) {
                this.performanceMonitor.recordEntitySkipped();
                continue;
            }
            
            const startTime = performance.now();
            
            try {
                this.processEntityAI(entity, deltaTime);
                processed++;
                
                const processingTime = performance.now() - startTime;
                this.performanceMonitor.recordEntityProcessing(processingTime);
                
            } catch (error) {
                console.error(`Error processing AI for entity ${entity.id}:`, error);
                this.stats.failedDecisions++;
            }
        }
    }
    
    /**
     * Process AI for a single entity
     */
    processEntityAI(entity, deltaTime) {
        if (!entity.isValid()) return;
        
        const aiComponent = entity.getComponent(AIComponent);
        if (!aiComponent || !aiComponent.enabled) return;
        
        const transform = entity.getComponent(TransformComponent);
        if (!transform) return;
        
        // Check if it's time for a new decision
        if (!this.shouldMakeDecision(aiComponent)) return;
        
        const decisionStart = performance.now();
        
        try {
            // Execute the decision pipeline
            this.executeDecisionPipeline(entity, aiComponent, transform, deltaTime);
            
            // Update timing
            aiComponent.lastDecisionTime = Date.now();
            
            // Update statistics
            const decisionTime = performance.now() - decisionStart;
            this.updateDecisionStats(decisionTime, true);
            
        } catch (error) {
            console.error(`Decision pipeline failed for entity ${entity.id}:`, error);
            this.updateDecisionStats(performance.now() - decisionStart, false);
        }
    }
    
    /**
     * Check if entity should make a new decision
     */
    shouldMakeDecision(aiComponent) {
        const now = Date.now();
        return (now - aiComponent.lastDecisionTime) >= aiComponent.decisionInterval;
    }
    
    /**
     * Execute the complete decision pipeline: State → Q-learning → Behavior Tree → Action
     */
    executeDecisionPipeline(entity, aiComponent, transform, deltaTime) {
        // Step 1: Update state representation
        const gameState = this.extractGameState(entity, transform);
        
        // Step 2: Q-learning decision (if enabled and available)
        let qLearningAction = null;
        if (aiComponent.enableQLearning && aiComponent.qLearning && this.isAIInitialized) {
            qLearningAction = this.processQLearning(entity, aiComponent, gameState);
        }
        
        // Step 3: Behavior tree execution
        const behaviorAction = this.processBehaviorTree(entity, aiComponent, deltaTime, qLearningAction);
        
        // Step 4: Execute action through game systems
        if (behaviorAction) {
            this.executeAction(entity, behaviorAction);
        }
        
        // Step 5: Provide feedback to Q-learning (if applicable)
        if (qLearningAction && aiComponent.qLearning) {
            const reward = this.calculateReward(entity, gameState, behaviorAction);
            aiComponent.qLearning.receiveReward(reward);
        }
    }
    
    /**
     * Extract game state for AI decision making
     */
    extractGameState(entity, transform) {
        // Basic game state extraction
        // In production, this would be much more comprehensive
        return {
            entity: entity,
            position: { x: transform.x, y: transform.y },
            rotation: transform.rotation,
            timestamp: Date.now(),
            nearbyEntities: this.findNearbyEntities(entity, 200), // 200 pixel radius
            // TODO: Add more state information as needed
        };
    }
    
    /**
     * Find nearby entities for state analysis
     */
    findNearbyEntities(entity, radius) {
        const transform = entity.getComponent(TransformComponent);
        const nearby = [];
        
        for (const otherEntity of this.world.entities) {
            if (otherEntity === entity || !otherEntity.isValid()) continue;
            
            const otherTransform = otherEntity.getComponent(TransformComponent);
            if (!otherTransform) continue;
            
            const dx = otherTransform.x - transform.x;
            const dy = otherTransform.y - transform.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance <= radius) {
                nearby.push({
                    entity: otherEntity,
                    distance: distance,
                    angle: Math.atan2(dy, dx)
                });
            }
        }
        
        return nearby;
    }
    
    /**
     * Process Q-learning decision
     */
    processQLearning(entity, aiComponent, gameState) {
        try {
            // Update Q-learning state
            aiComponent.qLearning.updateState(gameState);
            
            // Select action
            const actionResult = aiComponent.qLearning.selectAction();
            
            if (actionResult) {
                aiComponent.qLearning.markDecisionMade();
                return actionResult;
            }
            
        } catch (error) {
            console.error(`Q-learning error for entity ${entity.id}:`, error);
        }
        
        return null;
    }
    
    /**
     * Process behavior tree execution
     */
    processBehaviorTree(entity, aiComponent, deltaTime, qLearningAction) {
        if (!aiComponent.behaviorTree) return null;
        
        try {
            // Set context for behavior tree (including Q-learning suggestion)
            const context = {
                entity: entity,
                world: this.world,
                deltaTime: deltaTime,
                qLearningAction: qLearningAction,
                aiComponent: aiComponent
            };
            
            // Execute behavior tree
            aiComponent.behaviorTree.context = context;
            const status = aiComponent.behaviorTree.execute(deltaTime);
            
            // Extract action from behavior tree result
            if (status === NodeStatus.SUCCESS && aiComponent.behaviorTree.lastAction) {
                return aiComponent.behaviorTree.lastAction;
            }
            
        } catch (error) {
            console.error(`Behavior tree error for entity ${entity.id}:`, error);
        }
        
        return null;
    }
    
    /**
     * Execute an action through appropriate game systems
     */
    executeAction(entity, action) {
        if (!action || !action.type) return;
        
        try {
            switch (action.type) {
                case 'movement':
                    this.executeMovementAction(entity, action);
                    break;
                case 'combat':
                    this.executeCombatAction(entity, action);
                    break;
                case 'tactical':
                    this.executeTacticalAction(entity, action);
                    break;
                case 'economy':
                    this.executeEconomyAction(entity, action);
                    break;
                default:
                    console.warn(`Unknown action type: ${action.type}`);
            }
            
        } catch (error) {
            console.error(`Error executing action for entity ${entity.id}:`, error);
        }
    }
    
    /**
     * Execute movement actions
     */
    executeMovementAction(entity, action) {
        const movementComponent = entity.getComponent('MovementComponent');
        const transform = entity.getComponent(TransformComponent);
        
        if (!movementComponent || !transform) return;
        
        if (action.direction) {
            // Calculate target position based on direction
            const distance = action.distance || 100; // Default move distance
            const targetX = transform.x + (action.direction.x * distance);
            const targetY = transform.y + (action.direction.y * distance);
            
            movementComponent.setTarget(targetX, targetY);
        }
    }
    
    /**
     * Execute combat actions
     */
    executeCombatAction(entity, action) {
        const combatComponent = entity.getComponent('CombatComponent');
        if (!combatComponent) return;
        
        // Find target based on action priority
        const target = this.findCombatTarget(entity, action.priority);
        if (target) {
            combatComponent.target = target;
        }
    }
    
    /**
     * Execute tactical actions
     */
    executeTacticalAction(entity, action) {
        const aiComponent = entity.getComponent(AIComponent);
        if (!aiComponent) return;
        
        // Update AI behavior based on tactical decision
        aiComponent.behaviorType = action.behavior;
    }
    
    /**
     * Execute economy actions
     */
    executeEconomyAction(entity, action) {
        // Placeholder for economy-related actions
        console.log(`Executing economy action: ${action.name}`);
    }
    
    /**
     * Find combat target based on priority
     */
    findCombatTarget(entity, priority) {
        const nearby = this.findNearbyEntities(entity, 200);
        
        // Filter for enemies (placeholder - needs faction system)
        const enemies = nearby.filter(info => {
            // TODO: Implement proper faction checking
            return info.entity !== entity;
        });
        
        if (enemies.length === 0) return null;
        
        switch (priority) {
            case 'nearest':
                return enemies.sort((a, b) => a.distance - b.distance)[0]?.entity;
            case 'weakest':
                return enemies.sort((a, b) => {
                    const aHealth = a.entity.getComponent('HealthComponent')?.currentHealth || 100;
                    const bHealth = b.entity.getComponent('HealthComponent')?.currentHealth || 100;
                    return aHealth - bHealth;
                })[0]?.entity;
            case 'strongest':
                return enemies.sort((a, b) => {
                    const aHealth = a.entity.getComponent('HealthComponent')?.currentHealth || 100;
                    const bHealth = b.entity.getComponent('HealthComponent')?.currentHealth || 100;
                    return bHealth - aHealth;
                })[0]?.entity;
            default:
                return enemies[0]?.entity;
        }
    }
    
    /**
     * Calculate reward for Q-learning
     */
    calculateReward(entity, gameState, action) {
        // Basic reward calculation - should be enhanced based on game objectives
        let reward = 0;
        
        // Small base reward for making any decision
        reward += 0.1;
        
        // TODO: Add more sophisticated reward calculation based on:
        // - Unit survival
        // - Objective completion
        // - Resource efficiency
        // - Combat effectiveness
        
        return reward;
    }
    
    /**
     * Update decision statistics
     */
    updateDecisionStats(decisionTime, success) {
        this.stats.totalDecisions++;
        
        if (success) {
            this.stats.successfulDecisions++;
        } else {
            this.stats.failedDecisions++;
        }
        
        // Update average decision time
        this.stats.averageDecisionTime = 
            (this.stats.averageDecisionTime * (this.stats.totalDecisions - 1) + decisionTime) / this.stats.totalDecisions;
    }
    
    /**
     * Get system status and performance information
     */
    getSystemStatus() {
        return {
            enabled: this.isSystemEnabled,
            initialized: this.isAIInitialized,
            gracefulDegradation: this.gracefulDegradation,
            entityCount: this.entities.size,
            queueLength: this.entityDecisionQueue.length,
            performance: this.performanceMonitor.getPerformanceReport(),
            stats: {
                ...this.stats,
                uptime: Date.now() - this.stats.systemUptime
            },
            tensorFlow: this.tensorFlowManager.getStatus()
        };
    }
    
    /**
     * Enable or disable the AI system
     */
    setEnabled(enabled) {
        this.isSystemEnabled = enabled;
        console.log(`AI System ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Adjust frame budget for AI processing
     */
    setFrameBudget(budget) {
        this.performanceMonitor.frameBudget = Math.max(1, budget);
        console.log(`AI frame budget set to ${budget}ms`);
    }
    
    /**
     * Cleanup system resources
     */
    destroy() {
        if (this.destroyed) return;
        
        console.log('🧹 Cleaning up AI System...');
        
        // Cleanup TensorFlow
        if (this.tensorFlowManager) {
            this.tensorFlowManager.cleanup();
        }
        
        // Clear entity queue
        this.entityDecisionQueue = [];
        
        // Clear behavior trees
        this.behaviorTreeTemplates = {};
        
        super.destroy();
        
        console.log('✅ AI System cleanup completed');
    }
}