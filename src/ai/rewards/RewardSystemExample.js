/**
 * Example integration of Reward System with Q-Learning Component
 * Demonstrates how to use the reward calculator with the existing AI system
 */

import { RewardCalculator, createOutcome } from './RewardCalculator.js';
import { QLearningComponent } from '../components/QLearningComponent.js';

/**
 * Example class showing reward system integration
 */
export class RewardSystemExample {
    constructor() {
        this.rewardCalculator = new RewardCalculator({
            debugMode: false,
            adaptiveScaling: true
        });
        
        this.qLearning = new QLearningComponent({
            epsilon: 0.1,
            learningRate: 0.001,
            discountFactor: 0.95,
            isTraining: true
        });
        
        // Example game state
        this.currentGameState = {
            threatLevel: 'low',
            urgencyLevel: 'moderate',
            teamwork: {
                coordinatedAction: false,
                supportingAllies: false,
                teamObjective: false,
                loneWolf: false
            }
        };
        
        // Example unit
        this.unit = {
            id: 'unit_001',
            health: 100,
            maxHealth: 100,
            position: { x: 100, y: 100 },
            faction: 'player'
        };
    }

    /**
     * Simulate a complete action-reward cycle
     */
    simulateActionRewardCycle() {
        console.log('Starting action-reward simulation...\n');
        
        // 1. Update Q-learning state
        this.qLearning.updateState(this.currentGameState);
        
        // 2. Select an action
        const actionSelection = this.qLearning.selectAction();
        console.log(`Selected action: ${actionSelection.action.name} (ID: ${actionSelection.actionId})`);
        console.log(`Exploration: ${actionSelection.isExploration}`);
        
        // 3. Simulate action execution and outcome
        const outcome = this.simulateActionOutcome(actionSelection.actionId);
        console.log('Action outcome:', this.summarizeOutcome(outcome));
        
        // 4. Calculate reward
        const reward = this.rewardCalculator.calculateReward(
            actionSelection.actionId,
            this.currentGameState,
            outcome,
            this.unit
        );
        
        console.log(`Calculated reward: ${reward.toFixed(2)}`);
        
        // 5. Feed reward back to Q-learning
        this.qLearning.receiveReward(reward);
        this.qLearning.markDecisionMade();
        
        // 6. Update game state based on outcome
        this.updateGameStateFromOutcome(outcome);
        
        console.log('Action-reward cycle completed.\n');
        
        return {
            action: actionSelection,
            outcome,
            reward,
            stats: this.qLearning.getLearningStats()
        };
    }

    /**
     * Simulate the outcome of an action
     */
    simulateActionOutcome(actionId) {
        const action = this.qLearning.getAction(actionId);
        let outcome = createOutcome();
        
        // Simulate different outcomes based on action type
        switch (action.type) {
            case 'movement':
                outcome = this.simulateMovementOutcome(actionId);
                break;
            case 'combat':
                outcome = this.simulateCombatOutcome(actionId);
                break;
            case 'tactical':
                outcome = this.simulateTacticalOutcome(actionId);
                break;
            case 'economy':
                outcome = this.simulateEconomicOutcome();
                break;
            case 'passive':
                outcome = this.simulateIdleOutcome();
                break;
        }
        
        return outcome;
    }

    /**
     * Simulate movement action outcomes
     */
    simulateMovementOutcome(actionId) {
        const success = Math.random() > 0.1; // 90% success rate
        const exploreNew = Math.random() > 0.7; // 30% chance to explore new area
        const improvePosition = Math.random() > 0.6; // 40% chance to improve position
        
        return createOutcome({
            moveSuccessful: success,
            blocked: !success,
            newAreaExplored: success && exploreNew,
            positionImproved: success && improvePosition,
            efficientPath: success && Math.random() > 0.5,
            formationMaintained: Math.random() > 0.3,
            distanceToObjective: Math.random() * 200,
            previousDistanceToObjective: Math.random() * 250
        });
    }

    /**
     * Simulate combat action outcomes
     */
    simulateCombatOutcome(actionId) {
        const hitChance = 0.7; // 70% hit chance
        const hit = Math.random() < hitChance;
        const damage = hit ? Math.floor(Math.random() * 20) + 5 : 0;
        const elimination = hit && Math.random() > 0.8; // 20% chance of elimination on hit
        
        return createOutcome({
            attackSuccessful: hit,
            damageDealt: damage,
            enemyEliminated: elimination,
            criticalHit: hit && Math.random() > 0.9,
            firstStrike: Math.random() > 0.6,
            focusFire: Math.random() > 0.7,
            missedAttack: !hit,
            unitHealthPercentage: this.unit.health / this.unit.maxHealth
        });
    }

    /**
     * Simulate tactical action outcomes
     */
    simulateTacticalOutcome(actionId) {
        const action = this.qLearning.getAction(actionId);
        
        switch (action.name) {
            case 'retreat':
                return createOutcome({
                    successfulEscape: Math.random() > 0.3,
                    retreatWhenDamaged: this.unit.health < this.unit.maxHealth * 0.5,
                    retreatedToSafety: Math.random() > 0.4,
                    liveToFightAgain: Math.random() > 0.6
                });
                
            case 'hold_position':
                return createOutcome({
                    defendedObjective: Math.random() > 0.5,
                    maintainedWatch: Math.random() > 0.3,
                    heldUnderFire: Math.random() > 0.7,
                    fortifiedPosition: Math.random() > 0.6
                });
                
            case 'patrol':
                return createOutcome({
                    areaCovered: Math.floor(Math.random() * 5) + 1,
                    enemyDetected: Math.random() > 0.8,
                    routeCompleted: Math.random() > 0.4,
                    vigilantPatrol: Math.random() > 0.5
                });
                
            default:
                return createOutcome();
        }
    }

    /**
     * Simulate economic action outcomes
     */
    simulateEconomicOutcome() {
        const resourcesFound = Math.random() > 0.2; // 80% chance to find resources
        const amount = resourcesFound ? Math.floor(Math.random() * 10) + 1 : 0;
        
        return createOutcome({
            resourcesGathered: amount,
            efficientGathering: Math.random() > 0.4,
            fullLoad: amount >= 8,
            newResourceDiscovered: Math.random() > 0.9,
            protectedResources: Math.random() > 0.7,
            prioritizedHighValue: Math.random() > 0.6
        });
    }

    /**
     * Simulate idle action outcomes
     */
    simulateIdleOutcome() {
        return createOutcome({
            waitingForOrders: Math.random() > 0.3,
            conservingEnergy: Math.random() > 0.5,
            alertIdling: Math.random() > 0.4,
            wastedOpportunity: Math.random() > 0.8 // Rare but possible
        });
    }

    /**
     * Update game state based on action outcome
     */
    updateGameStateFromOutcome(outcome) {
        // Simulate threat level changes
        if (outcome.enemyEliminated) {
            this.currentGameState.threatLevel = 'low';
        } else if (outcome.enemyDetected) {
            this.currentGameState.threatLevel = 'high';
        }
        
        // Simulate health changes
        if (outcome.damageDealt > 0) {
            this.unit.health = Math.max(0, this.unit.health - Math.floor(Math.random() * 5));
        }
        
        // Simulate position changes for movement
        if (outcome.moveSuccessful) {
            this.unit.position.x += Math.floor(Math.random() * 20) - 10;
            this.unit.position.y += Math.floor(Math.random() * 20) - 10;
        }
    }

    /**
     * Create a human-readable summary of an outcome
     */
    summarizeOutcome(outcome) {
        const summary = [];
        
        if (outcome.moveSuccessful) summary.push('moved successfully');
        if (outcome.blocked) summary.push('movement blocked');
        if (outcome.attackSuccessful) summary.push(`dealt ${outcome.damageDealt} damage`);
        if (outcome.enemyEliminated) summary.push('eliminated enemy');
        if (outcome.resourcesGathered > 0) summary.push(`gathered ${outcome.resourcesGathered} resources`);
        if (outcome.successfulEscape) summary.push('escaped successfully');
        if (outcome.defendedObjective) summary.push('defended objective');
        if (outcome.newAreaExplored) summary.push('explored new area');
        
        return summary.length > 0 ? summary.join(', ') : 'no significant outcome';
    }

    /**
     * Run multiple simulation cycles
     */
    runSimulation(cycles = 10) {
        console.log(`Running ${cycles} action-reward cycles...\n`);
        
        const results = [];
        
        for (let i = 0; i < cycles; i++) {
            console.log(`--- Cycle ${i + 1} ---`);
            const result = this.simulateActionRewardCycle();
            results.push(result);
            
            // Update epsilon (exploration decay)
            this.qLearning.updateEpsilon(this.qLearning.epsilon * 0.99);
        }
        
        // Print final statistics
        console.log('=== Simulation Complete ===');
        console.log('Final Q-Learning stats:', this.qLearning.getLearningStats());
        console.log('Final Reward stats:', this.rewardCalculator.getRewardStats());
        
        // Action distribution
        const actionCounts = {};
        results.forEach(result => {
            const actionName = result.action.action.name;
            actionCounts[actionName] = (actionCounts[actionName] || 0) + 1;
        });
        
        console.log('\nAction distribution:');
        Object.entries(actionCounts).forEach(([action, count]) => {
            console.log(`  ${action}: ${count} times`);
        });
        
        return results;
    }

    /**
     * Test specific reward scenarios
     */
    testRewardScenarios() {
        console.log('Testing specific reward scenarios...\n');
        
        const scenarios = [
            {
                name: 'Successful Combat',
                actionId: 8, // attack_nearest
                outcome: createOutcome({
                    attackSuccessful: true,
                    damageDealt: 15,
                    enemyEliminated: true,
                    criticalHit: true
                })
            },
            {
                name: 'Resource Gathering',
                actionId: 14, // gather_resource
                outcome: createOutcome({
                    resourcesGathered: 8,
                    efficientGathering: true,
                    fullLoad: true,
                    newResourceDiscovered: true
                })
            },
            {
                name: 'Tactical Retreat',
                actionId: 11, // retreat
                outcome: createOutcome({
                    successfulEscape: true,
                    retreatWhenDamaged: true,
                    retreatedToSafety: true,
                    liveToFightAgain: true
                })
            },
            {
                name: 'Failed Movement',
                actionId: 0, // move_north
                outcome: createOutcome({
                    blocked: true,
                    moveIntoThreat: true,
                    inefficientPath: true
                })
            }
        ];
        
        scenarios.forEach(scenario => {
            const reward = this.rewardCalculator.calculateReward(
                scenario.actionId,
                this.currentGameState,
                scenario.outcome,
                this.unit
            );
            
            console.log(`${scenario.name}: ${reward.toFixed(2)} reward`);
        });
        
        console.log('\nReward scenario testing complete.\n');
    }
}

/**
 * Example usage
 */
export function runRewardSystemExample() {
    console.log('🤖 RTS AI Reward System Example\n');
    
    const example = new RewardSystemExample();
    
    // Test specific scenarios
    example.testRewardScenarios();
    
    // Run a simulation
    example.runSimulation(5);
    
    console.log('✨ Example completed!');
}

// Run example if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    runRewardSystemExample();
}