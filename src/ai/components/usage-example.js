/**
 * Usage Example for Q-Learning Components
 * Demonstrates integration with existing ECS system
 * This file shows how to use the components but doesn't implement actual learning
 */

import { QLearningComponent, ExperienceBuffer } from "./index.js";
import { Entity } from "../../ecs/Entity.js";
import { UnitComponent, AIComponent } from "../../ecs/Component.js";

/**
 * Example: Creating a unit with Q-learning capability
 */
export function createQLearningUnit(x, y, unitType) {
    const entity = new Entity();
    
    // Add standard RTS components
    entity.addComponent(new UnitComponent(unitType, "gdi", 100));
    entity.addComponent(new AIComponent("ai_qlearning"));
    
    // Add Q-learning component with custom parameters
    const qLearning = new QLearningComponent({
        epsilon: 0.2,           // 20% exploration rate
        learningRate: 0.001,    // Slow, stable learning
        discountFactor: 0.95,   // Focus on long-term rewards
        decisionInterval: 300,  // Make decisions every 300ms
        isTraining: true        // Enable learning mode
    });
    
    entity.addComponent(qLearning);
    
    return entity;
}

/**
 * Example: Setting up experience replay for training
 */
export function createTrainingBuffer() {
    // Create experience buffer with prioritized replay
    const buffer = new ExperienceBuffer({
        maxSize: 10000,         // Store up to 10k experiences
        batchSize: 64,          // Train on batches of 64
        prioritizedReplay: true, // Use priority sampling
        alpha: 0.6,             // Prioritization strength
        beta: 0.4               // Importance sampling
    });
    
    return buffer;
}

/**
 * Example: Basic Q-learning decision loop (structure only)
 */
export function processQLearningDecision(entity, gameState, experienceBuffer) {
    const qlearning = entity.getComponent("QLearningComponent");
    if (!qlearning || !qlearning.shouldMakeDecision()) {
        return null;
    }
    
    // Update state representation from game situation
    qlearning.updateState(gameState);
    
    // Select action using epsilon-greedy strategy
    const decision = qlearning.selectAction();
    
    // Mark decision timing
    qlearning.markDecisionMade();
    
    // Store experience in buffer (when reward is calculated later)
    // This would happen after action execution and reward calculation
    // experienceBuffer.add(previousState, action, reward, currentState, done);
    
    return {
        action: decision.action,
        isExploration: decision.isExploration,
        actionId: decision.actionId
    };
}

/**
 * Example: Training batch processing (structure only)
 */
export function processTrainingBatch(experienceBuffer, qNetwork) {
    if (!experienceBuffer.canSample()) {
        return null;
    }
    
    // Sample batch of experiences
    const batch = experienceBuffer.sample();
    if (!batch) return null;
    
    // TODO: Neural network training would happen here
    // 1. Forward pass through Q-network
    // 2. Calculate target Q-values
    // 3. Backpropagation and weight updates
    // 4. Update experience priorities if using prioritized replay
    
    console.log(`Training batch: ${batch.states.length} experiences`);
    
    return {
        batchSize: batch.states.length,
        averageReward: batch.rewards.reduce((sum, r) => sum + r, 0) / batch.rewards.length
    };
}

/**
 * Example: Episode management
 */
export function startNewEpisode(entity) {
    const qlearning = entity.getComponent("QLearningComponent");
    if (qlearning) {
        qlearning.startNewEpisode();
        console.log(`Started episode ${qlearning.getLearningStats().episodeCount}`);
    }
}

/**
 * Example: Getting learning progress
 */
export function getTrainingProgress(entity, experienceBuffer) {
    const qlearning = entity.getComponent("QLearningComponent");
    if (!qlearning) return null;
    
    return {
        learning: qlearning.getLearningStats(),
        buffer: experienceBuffer.getStats(),
        readyForTraining: experienceBuffer.canSample()
    };
}

// Export example functions
export default {
    createQLearningUnit,
    createTrainingBuffer,
    processQLearningDecision,
    processTrainingBatch,
    startNewEpisode,
    getTrainingProgress
};