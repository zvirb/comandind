/**
 * Unified AI Component for ECS Integration
 * Combines Q-learning, behavior trees, and TensorFlow integration into a single component
 * Replaces the basic AIComponent in the ECS system with advanced AI capabilities
 */

import { Component } from '../../ecs/Component.js';
import { QLearningComponent } from './QLearningComponent.js';

/**
 * Advanced AI Component that integrates all AI subsystems
 * This component coordinates between Q-learning, behavior trees, and neural networks
 */
export class AIComponent extends Component {
    constructor(options = {}) {
        super();
        
        // Basic AI settings
        this.enabled = options.enabled !== undefined ? options.enabled : true;
        this.behaviorType = options.behaviorType || 'combatUnit'; // combatUnit, harvester, guard, scout
        this.aiLevel = options.aiLevel || 'normal'; // basic, normal, advanced, expert
        
        // Decision timing
        this.lastDecisionTime = 0;
        this.decisionInterval = options.decisionInterval || 500; // ms between AI decisions
        this.adaptiveDecisionTiming = options.adaptiveDecisionTiming !== undefined ? options.adaptiveDecisionTiming : true;
        
        // Q-Learning integration
        this.enableQLearning = options.enableQLearning !== undefined ? options.enableQLearning : true;
        this.qLearning = null; // Will be initialized by AISystem
        this.qLearningConfig = {
            epsilon: options.epsilon || 0.1,
            learningRate: options.learningRate || 0.001,
            discountFactor: options.discountFactor || 0.95,
            isTraining: options.isTraining !== undefined ? options.isTraining : true
        };
        
        // Behavior Tree integration
        this.behaviorTree = null; // Will be assigned by AISystem
        this.behaviorTreeType = options.behaviorTreeType || null; // Override default behavior tree
        this.behaviorContext = {}; // Context data for behavior tree execution
        
        // Neural Network integration (TensorFlow)
        this.enableNeuralNetwork = options.enableNeuralNetwork !== undefined ? options.enableNeuralNetwork : false;
        this.neuralNetworkModel = null; // Placeholder for future TensorFlow model
        this.neuralNetworkInputSize = 36; // State vector size
        this.neuralNetworkOutputSize = 16; // Action space size
        
        // Performance and adaptation
        this.performanceMetrics = {
            decisionsPerSecond: 0,
            averageDecisionTime: 0,
            successRate: 0,
            rewardRate: 0,
            adaptationScore: 0
        };
        
        // State management
        this.currentState = 'initializing'; // initializing, idle, thinking, acting, learning
        this.lastStateChange = Date.now();
        this.stateHistory = [];
        this.maxStateHistoryLength = 20;
        
        // Learning and adaptation
        this.experienceLevel = options.experienceLevel || 0; // 0-100 scale
        this.adaptationRate = options.adaptationRate || 0.1;
        this.learningEnabled = options.learningEnabled !== undefined ? options.learningEnabled : true;
        
        // Tactical awareness
        this.tacticalContext = {
            alertLevel: 'normal', // calm, alert, combat, panic
            lastThreatSeen: 0,
            lastDamageTaken: 0,
            alliesNearby: 0,
            enemiesNearby: 0,
            resourcesNearby: 0
        };
        
        // Memory and knowledge
        this.memory = {
            knownEnemies: new Map(), // entity ID -> last known position/status
            knownResources: new Map(), // resource ID -> last known status
            patrolPoints: [], // For patrol behavior
            homePosition: null, // For guard/return behavior
            lastObjectives: [] // Recent objectives/commands
        };
        
        // Communication and coordination
        this.teamId = options.teamId || null;
        this.squadId = options.squadId || null;
        this.commanderId = options.commanderId || null; // For hierarchical AI
        this.communicationRange = options.communicationRange || 300;
        
        // Debugging and monitoring
        this.debugMode = options.debugMode || false;
        this.debugInfo = {
            lastDecision: null,
            lastAction: null,
            lastReward: 0,
            decisionReason: '',
            performanceWarnings: []
        };
        
        // Initialize state
        this.setState('idle');
    }
    
    /**
     * Set the AI state and track state history
     */
    setState(newState) {
        if (newState === this.currentState) return;
        
        const oldState = this.currentState;
        this.currentState = newState;
        this.lastStateChange = Date.now();
        
        // Track state history
        this.stateHistory.push({
            state: newState,
            timestamp: Date.now(),
            previousState: oldState
        });
        
        // Keep history manageable
        if (this.stateHistory.length > this.maxStateHistoryLength) {
            this.stateHistory.shift();
        }
        
        if (this.debugMode) {
            console.log(`AI Entity ${this.entity?.id}: ${oldState} → ${newState}`);
        }
    }
    
    /**
     * Check if AI should make a decision now
     */
    shouldMakeDecision() {
        const now = Date.now();
        const timeSinceLastDecision = now - this.lastDecisionTime;
        
        // Adaptive timing based on situation
        let effectiveInterval = this.decisionInterval;
        
        if (this.adaptiveDecisionTiming) {
            // Make decisions faster in combat or high-alert situations
            switch (this.tacticalContext.alertLevel) {
                case 'combat':
                    effectiveInterval *= 0.5; // 2x faster
                    break;
                case 'alert':
                    effectiveInterval *= 0.75; // 25% faster
                    break;
                case 'panic':
                    effectiveInterval *= 0.3; // 3x faster
                    break;
                default:
                    // Normal timing
                    break;
            }
            
            // Slower decisions for less experienced units
            const experienceFactor = 1 - (this.experienceLevel / 200); // 0.5 to 1.0
            effectiveInterval *= (0.5 + experienceFactor);
        }
        
        return timeSinceLastDecision >= effectiveInterval;
    }
    
    /**
     * Mark that a decision was made
     */
    markDecisionMade(decision = null) {
        this.lastDecisionTime = Date.now();
        
        if (decision) {
            this.debugInfo.lastDecision = decision;
            this.setState('acting');
        }
        
        // Update performance metrics
        this.updatePerformanceMetrics();
    }
    
    /**
     * Update tactical context based on game situation
     */
    updateTacticalContext(gameState) {
        if (!gameState) return;
        
        const now = Date.now();
        
        // Count nearby allies and enemies
        this.tacticalContext.alliesNearby = 0;
        this.tacticalContext.enemiesNearby = 0;
        this.tacticalContext.resourcesNearby = 0;
        
        if (gameState.nearbyEntities) {
            for (const nearby of gameState.nearbyEntities) {
                // TODO: Implement proper faction checking
                // For now, treat all others as potential enemies
                if (nearby.distance < 100) {
                    this.tacticalContext.enemiesNearby++;
                }
            }
        }
        
        // Update alert level based on context
        this.updateAlertLevel();
        
        // Update memory with new information
        this.updateMemory(gameState);
    }
    
    /**
     * Update alert level based on tactical situation
     */
    updateAlertLevel() {
        const now = Date.now();
        let newAlertLevel = 'calm';
        
        // Recent damage increases alert
        if (now - this.tacticalContext.lastDamageTaken < 5000) { // 5 seconds
            newAlertLevel = 'combat';
        }
        // Recent threats increase alert
        else if (now - this.tacticalContext.lastThreatSeen < 10000) { // 10 seconds
            newAlertLevel = 'alert';
        }
        // Enemies nearby
        else if (this.tacticalContext.enemiesNearby > 0) {
            newAlertLevel = 'alert';
        }
        // Outnumbered = panic
        if (this.tacticalContext.enemiesNearby > this.tacticalContext.alliesNearby + 2) {
            newAlertLevel = 'panic';
        }
        
        this.tacticalContext.alertLevel = newAlertLevel;
    }
    
    /**
     * Update memory with new game state information
     */
    updateMemory(gameState) {
        const now = Date.now();
        
        // Update known entities
        if (gameState.nearbyEntities) {
            for (const nearby of gameState.nearbyEntities) {
                const entityId = nearby.entity.id;
                
                // TODO: Classify entities as enemies, allies, resources, etc.
                // For now, treat as potential enemies
                this.memory.knownEnemies.set(entityId, {
                    lastSeen: now,
                    position: {
                        x: nearby.entity.getComponent?.('TransformComponent')?.x,
                        y: nearby.entity.getComponent?.('TransformComponent')?.y
                    },
                    distance: nearby.distance,
                    angle: nearby.angle
                });
            }
        }
        
        // Clean up old memory entries (older than 30 seconds)
        const memoryTimeout = 30000;
        for (const [entityId, info] of this.memory.knownEnemies.entries()) {
            if (now - info.lastSeen > memoryTimeout) {
                this.memory.knownEnemies.delete(entityId);
            }
        }
    }
    
    /**
     * Get the most important known threat
     */
    getPrimaryThreat() {
        let closestThreat = null;
        let closestDistance = Infinity;
        
        for (const [entityId, info] of this.memory.knownEnemies.entries()) {
            if (info.distance < closestDistance) {
                closestDistance = info.distance;
                closestThreat = info;
            }
        }
        
        return closestThreat;
    }
    
    /**
     * Learn from experience and adapt behavior
     */
    learnFromExperience(reward, action, outcome) {
        if (!this.learningEnabled) return;
        
        // Update experience level
        this.experienceLevel = Math.min(100, this.experienceLevel + (reward > 0 ? 0.1 : -0.05));
        
        // Adapt decision timing based on performance
        if (this.adaptiveDecisionTiming) {
            if (reward > 0.5) {
                // Good decision, can afford to think a bit longer
                this.decisionInterval = Math.min(1000, this.decisionInterval * 1.05);
            } else if (reward < -0.5) {
                // Bad decision, need to react faster
                this.decisionInterval = Math.max(100, this.decisionInterval * 0.95);
            }
        }
        
        // Store learning information for debugging
        this.debugInfo.lastReward = reward;
        this.debugInfo.lastAction = action;
        
        // Update Q-learning if available
        if (this.qLearning) {
            this.qLearning.receiveReward(reward);
        }
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics() {
        const now = Date.now();
        
        // Calculate decisions per second (over last 10 seconds)
        const recentDecisions = this.stateHistory.filter(entry => 
            now - entry.timestamp < 10000 && entry.state === 'acting'
        ).length;
        
        this.performanceMetrics.decisionsPerSecond = recentDecisions / 10;
        
        // Update other metrics based on Q-learning component
        if (this.qLearning) {
            const stats = this.qLearning.getLearningStats();
            this.performanceMetrics.rewardRate = stats.averageReward;
        }
    }
    
    /**
     * Get AI status for debugging and monitoring
     */
    getAIStatus() {
        return {
            enabled: this.enabled,
            state: this.currentState,
            behaviorType: this.behaviorType,
            aiLevel: this.aiLevel,
            experienceLevel: this.experienceLevel,
            alertLevel: this.tacticalContext.alertLevel,
            timeSinceLastDecision: Date.now() - this.lastDecisionTime,
            decisionInterval: this.decisionInterval,
            enableQLearning: this.enableQLearning,
            enableNeuralNetwork: this.enableNeuralNetwork,
            performanceMetrics: { ...this.performanceMetrics },
            memorySize: {
                knownEnemies: this.memory.knownEnemies.size,
                knownResources: this.memory.knownResources.size,
                patrolPoints: this.memory.patrolPoints.length
            },
            debugInfo: this.debugMode ? { ...this.debugInfo } : null
        };
    }
    
    /**
     * Configure Q-learning parameters
     */
    configureQLearning(config) {
        Object.assign(this.qLearningConfig, config);
        
        if (this.qLearning) {
            // Update existing Q-learning component
            this.qLearning.epsilon = this.qLearningConfig.epsilon;
            this.qLearning.learningRate = this.qLearningConfig.learningRate;
            this.qLearning.discountFactor = this.qLearningConfig.discountFactor;
            this.qLearning.setTrainingMode(this.qLearningConfig.isTraining);
        }
    }
    
    /**
     * Set behavior tree override
     */
    setBehaviorTree(behaviorTree) {
        this.behaviorTree = behaviorTree;
    }
    
    /**
     * Set home position for guard/return behaviors
     */
    setHomePosition(x, y) {
        this.memory.homePosition = { x, y };
    }
    
    /**
     * Add patrol point for patrol behavior
     */
    addPatrolPoint(x, y) {
        this.memory.patrolPoints.push({ x, y });
    }
    
    /**
     * Clear patrol points
     */
    clearPatrolPoints() {
        this.memory.patrolPoints = [];
    }
    
    /**
     * Enable or disable learning
     */
    setLearningEnabled(enabled) {
        this.learningEnabled = enabled;
        if (this.qLearning) {
            this.qLearning.setTrainingMode(enabled);
        }
    }
    
    /**
     * Set debug mode
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }
    
    /**
     * Reset AI state to initial conditions
     */
    reset() {
        this.setState('idle');
        this.lastDecisionTime = 0;
        this.experienceLevel = 0;
        this.tacticalContext.alertLevel = 'normal';
        this.tacticalContext.lastThreatSeen = 0;
        this.tacticalContext.lastDamageTaken = 0;
        
        // Clear memory
        this.memory.knownEnemies.clear();
        this.memory.knownResources.clear();
        this.memory.lastObjectives = [];
        
        // Reset Q-learning
        if (this.qLearning) {
            this.qLearning.startNewEpisode();
        }
        
        // Clear debug info
        this.debugInfo.lastDecision = null;
        this.debugInfo.lastAction = null;
        this.debugInfo.lastReward = 0;
        this.debugInfo.performanceWarnings = [];
    }
    
    /**
     * Component cleanup
     */
    destroy() {
        if (this.destroyed) return;
        
        // Cleanup Q-learning component
        if (this.qLearning) {
            this.qLearning.destroy();
            this.qLearning = null;
        }
        
        // Clear behavior tree reference
        this.behaviorTree = null;
        
        // Clear memory structures
        this.memory.knownEnemies.clear();
        this.memory.knownResources.clear();
        this.memory.patrolPoints = [];
        this.stateHistory = [];
        
        super.destroy();
    }
}