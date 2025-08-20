import { Component } from "../../ecs/Component.js";

/**
 * Q-Learning Component for AI decision making
 * Stores Q-learning state, action space, and parameters for neural network integration
 */
export class QLearningComponent extends Component {
    constructor(options = {}) {
        super();
        
        // Learning parameters
        this.epsilon = options.epsilon !== undefined ? options.epsilon : 0.1; // Exploration rate
        this.learningRate = options.learningRate !== undefined ? options.learningRate : 0.001;
        this.discountFactor = options.discountFactor !== undefined ? options.discountFactor : 0.95;
        
        // State representation (36-dimensional vector)
        this.currentState = this.createEmptyState();
        this.previousState = this.createEmptyState();
        
        // Action space (16 commands)
        this.actionSpace = this.defineActionSpace();
        this.lastAction = null;
        this.lastReward = 0;
        
        // Neural network integration hooks
        this.qNetwork = null; // Placeholder for future neural network
        this.targetNetwork = null; // Placeholder for target network
        
        // Training state
        this.isTraining = options.isTraining !== undefined ? options.isTraining : true;
        this.episodeCount = 0;
        this.totalReward = 0;
        this.stepCount = 0;
        
        // Performance tracking
        this.averageReward = 0;
        this.rewardHistory = [];
        this.maxRewardHistoryLength = 100;
        
        // Decision timing
        this.lastDecisionTime = 0;
        this.decisionInterval = options.decisionInterval || 500; // ms between decisions
    }
    
    /**
     * Creates an empty 36-dimensional state vector
     * State representation for RTS unit:
     * [0-7]: Own unit properties (health, position, facing, etc.)
     * [8-15]: Enemy threat analysis (nearest threats, distances)
     * [16-23]: Resource/objective proximity and status
     * [24-31]: Tactical situation (ally support, terrain advantages)
     * [32-35]: High-level strategic context
     */
    createEmptyState() {
        return new Float32Array(36);
    }
    
    /**
     * Defines the 16-action command space for RTS units
     */
    defineActionSpace() {
        return [
            // Movement actions (8 directions)
            { id: 0, name: "move_north", type: "movement", direction: { x: 0, y: -1 } },
            { id: 1, name: "move_northeast", type: "movement", direction: { x: 1, y: -1 } },
            { id: 2, name: "move_east", type: "movement", direction: { x: 1, y: 0 } },
            { id: 3, name: "move_southeast", type: "movement", direction: { x: 1, y: 1 } },
            { id: 4, name: "move_south", type: "movement", direction: { x: 0, y: 1 } },
            { id: 5, name: "move_southwest", type: "movement", direction: { x: -1, y: 1 } },
            { id: 6, name: "move_west", type: "movement", direction: { x: -1, y: 0 } },
            { id: 7, name: "move_northwest", type: "movement", direction: { x: -1, y: -1 } },
            
            // Combat actions
            { id: 8, name: "attack_nearest", type: "combat", priority: "nearest" },
            { id: 9, name: "attack_weakest", type: "combat", priority: "weakest" },
            { id: 10, name: "attack_strongest", type: "combat", priority: "strongest" },
            
            // Tactical actions
            { id: 11, name: "retreat", type: "tactical", behavior: "defensive" },
            { id: 12, name: "hold_position", type: "tactical", behavior: "hold" },
            { id: 13, name: "patrol", type: "tactical", behavior: "patrol" },
            
            // Special actions
            { id: 14, name: "gather_resource", type: "economy", target: "resource" },
            { id: 15, name: "idle", type: "passive", behavior: "wait" }
        ];
    }
    
    /**
     * Updates the current state vector based on game situation
     * This method signature is ready for future implementation
     */
    updateState(gameState) {
        // Store previous state
        this.previousState.set(this.currentState);
        
        // TODO: Implement state extraction from game situation
        // This will analyze the unit's environment and fill the 36D vector
        
        // Placeholder: Copy some basic values for structure
        if (gameState) {
            // Example state updates (to be implemented)
            // this.currentState[0] = gameState.unit.health / gameState.unit.maxHealth;
            // this.currentState[1] = gameState.unit.x / gameState.mapWidth;
            // this.currentState[2] = gameState.unit.y / gameState.mapHeight;
            // ... more state extraction logic
        }
    }
    
    /**
     * Selects an action using epsilon-greedy strategy
     * Returns action ID and whether it was exploratory
     */
    selectAction() {
        let actionId;
        let isExploration = false;
        
        if (this.isTraining && Math.random() < this.epsilon) {
            // Exploration: random action
            actionId = Math.floor(Math.random() * this.actionSpace.length);
            isExploration = true;
        } else {
            // Exploitation: best action from Q-network
            if (this.qNetwork) {
                // TODO: Implement neural network prediction
                actionId = this.getBestActionFromNetwork();
            } else {
                // Fallback: random action if no network available
                actionId = Math.floor(Math.random() * this.actionSpace.length);
                isExploration = true;
            }
        }
        
        this.lastAction = actionId;
        return {
            actionId,
            action: this.actionSpace[actionId],
            isExploration
        };
    }
    
    /**
     * Placeholder for neural network action selection
     */
    getBestActionFromNetwork() {
        // TODO: Implement neural network forward pass
        // For now, return a simple heuristic or random action
        return Math.floor(Math.random() * this.actionSpace.length);
    }
    
    /**
     * Records reward for the last action taken
     */
    receiveReward(reward) {
        this.lastReward = reward;
        this.totalReward += reward;
        this.stepCount++;
        
        // Update reward history for performance tracking
        this.rewardHistory.push(reward);
        if (this.rewardHistory.length > this.maxRewardHistoryLength) {
            this.rewardHistory.shift();
        }
        
        // Calculate running average
        this.averageReward = this.rewardHistory.reduce((sum, r) => sum + r, 0) / this.rewardHistory.length;
    }
    
    /**
     * Checks if enough time has passed for a new decision
     */
    shouldMakeDecision() {
        const now = Date.now();
        return (now - this.lastDecisionTime) >= this.decisionInterval;
    }
    
    /**
     * Updates decision timing
     */
    markDecisionMade() {
        this.lastDecisionTime = Date.now();
    }
    
    /**
     * Starts a new episode (resets episode-specific state)
     */
    startNewEpisode() {
        this.episodeCount++;
        this.totalReward = 0;
        this.stepCount = 0;
        this.lastAction = null;
        this.lastReward = 0;
        
        // Reset state vectors
        this.currentState.fill(0);
        this.previousState.fill(0);
    }
    
    /**
     * Gets current learning statistics
     */
    getLearningStats() {
        return {
            epsilon: this.epsilon,
            episodeCount: this.episodeCount,
            totalReward: this.totalReward,
            averageReward: this.averageReward,
            stepCount: this.stepCount,
            isTraining: this.isTraining
        };
    }
    
    /**
     * Updates exploration rate (epsilon decay)
     */
    updateEpsilon(newEpsilon) {
        this.epsilon = Math.max(0.01, newEpsilon); // Minimum exploration rate
    }
    
    /**
     * Sets training mode
     */
    setTrainingMode(training) {
        this.isTraining = training;
    }
    
    /**
     * Gets action by ID
     */
    getAction(actionId) {
        return this.actionSpace[actionId] || null;
    }
    
    /**
     * Gets action by name
     */
    getActionByName(actionName) {
        return this.actionSpace.find(action => action.name === actionName) || null;
    }
    
    /**
     * Component cleanup
     */
    destroy() {
        if (this.destroyed) return;
        
        // Clear neural network references
        this.qNetwork = null;
        this.targetNetwork = null;
        
        // Clear arrays
        this.rewardHistory = [];
        this.currentState = null;
        this.previousState = null;
        this.actionSpace = null;
        
        super.destroy();
    }
}