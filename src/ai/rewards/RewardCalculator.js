/**
 * Reward Calculator for RTS AI Learning
 * Implements reward calculation functions for all 16 RTS commands
 * 
 * This class evaluates the consequences of actions and calculates appropriate
 * rewards to guide Q-learning and neural network training.
 */

import { RewardConfig, getActionRewardConfig } from './RewardConfig.js';

export class RewardCalculator {
    constructor(options = {}) {
        this.config = RewardConfig;
        
        // Reward calculation state
        this.rewardHistory = [];
        this.maxHistoryLength = options.maxHistoryLength || 100;
        
        // Performance tracking
        this.averageReward = 0;
        this.totalRewards = 0;
        this.rewardCount = 0;
        
        // Learning adaptation
        this.performanceBaseline = 0;
        this.adaptiveScaling = options.adaptiveScaling !== undefined ? options.adaptiveScaling : true;
        
        // Debug mode
        this.debugMode = options.debugMode || false;
        this.rewardBreakdown = null;
    }

    /**
     * Calculate reward for a specific action and outcome
     * @param {number} actionId - The action ID (0-15)
     * @param {Object} gameState - Current game state
     * @param {Object} actionOutcome - Results of the action
     * @param {Object} unit - The unit that performed the action
     * @returns {number} Calculated reward value
     */
    calculateReward(actionId, gameState, actionOutcome, unit) {
        if (this.debugMode) {
            this.rewardBreakdown = { actionId, components: {} };
        }

        let totalReward = 0;
        
        try {
            // Get base reward for action type
            const baseReward = this.calculateBaseReward(actionId, actionOutcome);
            totalReward += baseReward;
            
            if (this.debugMode) {
                this.rewardBreakdown.components.base = baseReward;
            }

            // Apply situational modifiers
            const situationalReward = this.calculateSituationalReward(actionId, gameState, unit);
            totalReward += situationalReward;
            
            if (this.debugMode) {
                this.rewardBreakdown.components.situational = situationalReward;
            }

            // Apply context-specific bonuses/penalties
            const contextReward = this.calculateContextualReward(actionId, gameState, actionOutcome, unit);
            totalReward += contextReward;
            
            if (this.debugMode) {
                this.rewardBreakdown.components.contextual = contextReward;
            }

            // Apply learning and adaptation bonuses
            const learningReward = this.calculateLearningReward(actionId, actionOutcome, unit);
            totalReward += learningReward;
            
            if (this.debugMode) {
                this.rewardBreakdown.components.learning = learningReward;
            }

            // Apply scaling and clamping
            totalReward = this.applyRewardScaling(totalReward, actionId, gameState);
            
            // Record reward for tracking
            this.recordReward(totalReward);
            
            if (this.debugMode) {
                this.rewardBreakdown.total = totalReward;
                console.log('Reward breakdown:', this.rewardBreakdown);
            }

            return totalReward;

        } catch (error) {
            console.error('Error calculating reward:', error);
            return 0; // Safe fallback
        }
    }

    /**
     * Calculate base reward based on action type and immediate outcome
     */
    calculateBaseReward(actionId, outcome) {
        const actionConfig = getActionRewardConfig(actionId);
        let reward = 0;

        // Movement actions (0-7)
        if (actionId >= 0 && actionId <= 7) {
            reward += this.calculateMovementReward(actionId, outcome, actionConfig);
        }
        // Combat actions (8-10)
        else if (actionId >= 8 && actionId <= 10) {
            reward += this.calculateCombatReward(actionId, outcome, actionConfig);
        }
        // Tactical actions (11-13)
        else if (actionId >= 11 && actionId <= 13) {
            reward += this.calculateTacticalReward(actionId, outcome, actionConfig);
        }
        // Economic action (14)
        else if (actionId === 14) {
            reward += this.calculateEconomicReward(outcome, actionConfig);
        }
        // Idle action (15)
        else if (actionId === 15) {
            reward += this.calculateIdleReward(outcome, actionConfig);
        }

        return reward;
    }

    /**
     * Calculate movement reward (actions 0-7)
     */
    calculateMovementReward(actionId, outcome, config) {
        let reward = 0;

        // Basic movement success/failure
        if (outcome.moveSuccessful) {
            reward += config.moveSuccess;
        } else if (outcome.blocked) {
            reward += config.moveBlocked;
        }

        // Distance to objective considerations
        if (outcome.distanceToObjective !== undefined) {
            const previousDistance = outcome.previousDistanceToObjective || Infinity;
            if (outcome.distanceToObjective < previousDistance) {
                reward += config.moveTowardObjective;
            } else if (outcome.distanceToObjective > previousDistance) {
                reward += config.moveAwayFromObjective;
            }
        }

        // Objective reached
        if (outcome.objectiveReached) {
            reward += config.reachObjective;
        }

        // Exploration bonus
        if (outcome.newAreaExplored) {
            reward += config.exploreNewArea;
        }

        // Position quality
        if (outcome.positionImproved) {
            reward += config.improvePosition;
        } else if (outcome.positionWorsened) {
            reward += config.worsenPosition;
        }

        // Path efficiency
        if (outcome.efficientPath) {
            reward += config.efficientPathBonus;
        } else if (outcome.inefficientPath) {
            reward += config.inefficientPathPenalty;
        }

        // Formation maintenance
        if (outcome.formationMaintained) {
            reward += config.maintainFormation;
        } else if (outcome.formationBroken) {
            reward += config.breakFormation;
        }

        // Threat assessment
        if (outcome.movedIntoThreat) {
            reward += config.moveIntoThreat;
        }

        return reward;
    }

    /**
     * Calculate combat reward (actions 8-10)
     */
    calculateCombatReward(actionId, outcome, config) {
        let reward = 0;

        // Damage dealt
        if (outcome.damageDealt && outcome.damageDealt > 0) {
            reward += outcome.damageDealt * config.damageDealt;
        }

        // Enemy elimination
        if (outcome.enemyEliminated) {
            reward += config.enemyEliminated;
        }

        // Target selection bonuses based on action type
        if (outcome.attackSuccessful) {
            switch (actionId) {
                case 8: // Attack nearest
                    reward += config.attackNearestReward;
                    break;
                case 9: // Attack weakest
                    reward += config.attackWeakestReward;
                    break;
                case 10: // Attack strongest
                    reward += config.attackStrongestReward;
                    break;
            }
        }

        // Combat efficiency bonuses
        if (outcome.criticalHit) {
            reward += config.criticalHit;
        }
        if (outcome.firstStrike) {
            reward += config.firstStrikeBonus;
        }
        if (outcome.focusFire) {
            reward += config.focusFireBonus;
        }
        if (outcome.flanking) {
            reward += config.flanking;
        }
        if (outcome.ambush) {
            reward += config.ambush;
        }
        if (outcome.counterAttack) {
            reward += config.counterAttack;
        }

        // Combat failures and penalties
        if (outcome.missedAttack) {
            reward += config.missedAttack;
        }
        if (outcome.friendlyFire) {
            reward += config.friendlyFire;
        }
        if (outcome.attackOutOfRange) {
            reward += config.attackOutOfRange;
        }
        if (outcome.overkill) {
            reward += config.overkillPenalty;
        }

        // Health-based combat modifiers
        if (outcome.unitHealthPercentage !== undefined) {
            if (outcome.unitHealthPercentage < 0.3 && outcome.attackSuccessful) {
                reward += config.lowHealthCombat;
            } else if (outcome.unitHealthPercentage > 0.7) {
                reward += config.healthyEngagement;
            }
        }

        return reward;
    }

    /**
     * Calculate tactical reward (actions 11-13)
     */
    calculateTacticalReward(actionId, outcome, config) {
        let reward = 0;

        switch (actionId) {
            case 11: // Retreat
                if (outcome.successfulEscape) reward += config.successfulEscape;
                if (outcome.retreatWhenDamaged) reward += config.retreatWhenDamaged;
                if (outcome.unnecessaryRetreat) reward += config.unnecessaryRetreat;
                if (outcome.retreatedToSafety) reward += config.retreatToSafety;
                if (outcome.retreatedIntoThreat) reward += config.retreatIntoThreat;
                if (outcome.liveToFightAgain) reward += config.liveToFightAgain;
                break;

            case 12: // Hold Position
                if (outcome.defendedObjective) reward += config.defendObjective;
                if (outcome.blockedEnemyAdvance) reward += config.blockEnemyAdvance;
                if (outcome.maintainedWatch) reward += config.maintainWatch;
                if (outcome.heldUnderFire) reward += config.holdWhenAttacked;
                if (outcome.holdUnnecessarily) reward += config.holdUnnecessarily;
                if (outcome.fortifiedPosition) reward += config.fortifyPosition;
                break;

            case 13: // Patrol
                if (outcome.areaCovered) {
                    reward += outcome.areaCovered * config.areaCoverage;
                }
                if (outcome.enemyDetected) reward += config.enemyDetection;
                if (outcome.routeCompleted) reward += config.routeCompletion;
                if (outcome.vigilantPatrol) reward += config.vigilantPatrol;
                if (outcome.patrolWhenNeeded) reward += config.patrolWhenNeeded;
                if (outcome.inefficientPatrol) reward += config.inefficientPatrol;
                break;
        }

        return reward;
    }

    /**
     * Calculate economic reward (action 14)
     */
    calculateEconomicReward(outcome, config) {
        let reward = 0;

        // Resource gathering
        if (outcome.resourcesGathered && outcome.resourcesGathered > 0) {
            reward += outcome.resourcesGathered * config.resourceGathered;
        }

        // Efficiency bonuses
        if (outcome.efficientGathering) {
            reward += config.efficientGathering;
        }
        if (outcome.fullLoad) {
            reward += config.fullLoadBonus;
        }
        if (outcome.minimizedEmptyTrips) {
            reward += config.minimizeEmptyTrips;
        }
        if (outcome.prioritizedHighValue) {
            reward += config.prioritizeHighValue;
        }

        // Discovery and strategic bonuses
        if (outcome.newResourceDiscovered) {
            reward += config.newResourceDiscovery;
        }
        if (outcome.protectedResources) {
            reward += config.protectResources;
        }
        if (outcome.sharedResourceInfo) {
            reward += config.shareResourceInfo;
        }
        if (outcome.sustainableGathering) {
            reward += config.sustainableGathering;
        }

        // Economic failures
        if (outcome.gatheredUnderFire) {
            reward += config.gatherUnderFire;
        }
        if (outcome.lostResources) {
            reward += config.loseResources;
        }
        if (outcome.ignoredBetterResources) {
            reward += config.ignoreBetterResources;
        }

        return reward;
    }

    /**
     * Calculate idle reward (action 15)
     */
    calculateIdleReward(outcome, config) {
        let reward = 0;

        // Appropriate idle behavior
        if (outcome.waitingForOrders) {
            reward += config.waitForOrders;
        }
        if (outcome.conservingEnergy) {
            reward += config.conserveEnergy;
        }
        if (outcome.alertIdling) {
            reward += config.alertIdling;
        }

        // Inappropriate idle behavior
        if (outcome.idleWhenNeeded) {
            reward += config.idleWhenNeeded;
        }
        if (outcome.idleUnderFire) {
            reward += config.idleUnderFire;
        }
        if (outcome.wastedOpportunity) {
            reward += config.wasteOpportunity;
        }
        if (outcome.idleTooLong) {
            reward += config.idleTooLong;
        }

        return reward;
    }

    /**
     * Calculate situational modifiers based on game state
     */
    calculateSituationalReward(actionId, gameState, unit) {
        let modifier = 1.0;
        let additionalReward = 0;

        // Health-based modifiers
        if (unit && unit.health !== undefined && unit.maxHealth !== undefined) {
            const healthPercentage = unit.health / unit.maxHealth;
            if (healthPercentage <= 0.25) {
                modifier *= this.config.situational.healthMultipliers.critical;
            } else if (healthPercentage <= 0.5) {
                modifier *= this.config.situational.healthMultipliers.low;
            } else {
                modifier *= this.config.situational.healthMultipliers.healthy;
            }
        }

        // Threat level modifiers
        if (gameState && gameState.threatLevel !== undefined) {
            switch (gameState.threatLevel) {
                case 'none':
                    modifier *= this.config.situational.threatMultipliers.noThreat;
                    break;
                case 'low':
                    modifier *= this.config.situational.threatMultipliers.lowThreat;
                    break;
                case 'high':
                    modifier *= this.config.situational.threatMultipliers.highThreat;
                    break;
                case 'critical':
                    modifier *= this.config.situational.threatMultipliers.critical;
                    break;
            }
        }

        // Time pressure modifiers
        if (gameState && gameState.urgencyLevel !== undefined) {
            switch (gameState.urgencyLevel) {
                case 'relaxed':
                    modifier *= this.config.situational.urgencyMultipliers.relaxed;
                    break;
                case 'moderate':
                    modifier *= this.config.situational.urgencyMultipliers.moderate;
                    break;
                case 'urgent':
                    modifier *= this.config.situational.urgencyMultipliers.urgent;
                    break;
                case 'critical':
                    modifier *= this.config.situational.urgencyMultipliers.critical;
                    break;
            }
        }

        // Team coordination bonuses
        if (gameState && gameState.teamwork !== undefined) {
            if (gameState.teamwork.coordinatedAction) {
                additionalReward += this.config.situational.teamwork.coordinatedAction;
            }
            if (gameState.teamwork.supportingAllies) {
                additionalReward += this.config.situational.teamwork.supportAllies;
            }
            if (gameState.teamwork.teamObjective) {
                additionalReward += this.config.situational.teamwork.teamObjective;
            }
            if (gameState.teamwork.loneWolf) {
                additionalReward += this.config.situational.teamwork.loneWolfPenalty;
            }
        }

        return additionalReward * modifier;
    }

    /**
     * Calculate contextual rewards based on broader game context
     */
    calculateContextualReward(actionId, gameState, outcome, unit) {
        let reward = 0;

        // Special achievements
        if (outcome.missionSuccess) {
            reward += this.config.special.missionSuccess;
        }
        if (outcome.savedAlly) {
            reward += this.config.special.saveAlly;
        }
        if (outcome.perfectExecution) {
            reward += this.config.special.perfectExecution;
        }

        // Major failures
        if (outcome.missionFailure) {
            reward += this.config.special.missionFailure;
        }
        if (outcome.allyDestroyed) {
            reward += this.config.special.allyDestroyed;
        }
        if (outcome.catastrophicFailure) {
            reward += this.config.special.catastrophicFailure;
        }

        // Learning milestones
        if (outcome.firstTimeSuccess) {
            reward += this.config.special.firstTimeSuccess;
        }
        if (outcome.mastery) {
            reward += this.config.special.mastery;
        }
        if (outcome.breakthrough) {
            reward += this.config.special.breakthrough;
        }

        return reward;
    }

    /**
     * Calculate learning and adaptation bonuses
     */
    calculateLearningReward(actionId, outcome, unit) {
        let reward = 0;

        // Performance improvement
        if (outcome.performanceBetter) {
            reward += this.config.situational.learning.improvementBonus;
        }

        // Consistency bonus
        if (outcome.consistentPerformance) {
            reward += this.config.situational.learning.consistencyBonus;
        }

        // Adaptation bonus
        if (outcome.adaptedToSituation) {
            reward += this.config.situational.learning.adaptationBonus;
        }

        // Regression penalty
        if (outcome.performanceWorse) {
            reward += this.config.situational.learning.regressionPenalty;
        }

        return reward;
    }

    /**
     * Apply final scaling and clamping to reward
     */
    applyRewardScaling(reward, actionId, gameState) {
        // Apply action type scaling
        if (actionId >= 0 && actionId <= 7) {
            reward *= this.config.global.movementScale;
        } else if (actionId >= 8 && actionId <= 10) {
            reward *= this.config.global.combatScale;
        } else if (actionId === 14) {
            reward *= this.config.global.economicScale;
        } else if (actionId >= 11 && actionId <= 13) {
            reward *= this.config.global.tacticalScale;
        }

        // Apply adaptive scaling if enabled
        if (this.adaptiveScaling && this.rewardCount > 10) {
            const performanceRatio = this.averageReward / this.performanceBaseline;
            if (performanceRatio > 1.2) {
                // Performance is high, make rewards more challenging
                reward *= 0.9;
            } else if (performanceRatio < 0.8) {
                // Performance is low, make rewards more encouraging
                reward *= 1.1;
            }
        }

        // Clamp to maximum magnitude
        const maxMagnitude = this.config.global.maxRewardMagnitude;
        reward = Math.max(-maxMagnitude, Math.min(maxMagnitude, reward));

        return reward;
    }

    /**
     * Record reward for tracking and adaptation
     */
    recordReward(reward) {
        this.rewardHistory.push(reward);
        
        if (this.rewardHistory.length > this.maxHistoryLength) {
            this.rewardHistory.shift();
        }

        this.totalRewards += reward;
        this.rewardCount++;
        this.averageReward = this.totalRewards / this.rewardCount;

        // Update performance baseline periodically
        if (this.rewardCount % 50 === 0) {
            this.performanceBaseline = this.averageReward;
        }
    }

    /**
     * Get reward calculation statistics
     */
    getRewardStats() {
        return {
            averageReward: this.averageReward,
            totalRewards: this.totalRewards,
            rewardCount: this.rewardCount,
            recentRewards: this.rewardHistory.slice(-10),
            performanceBaseline: this.performanceBaseline,
        };
    }

    /**
     * Reset reward calculator state
     */
    reset() {
        this.rewardHistory = [];
        this.averageReward = 0;
        this.totalRewards = 0;
        this.rewardCount = 0;
        this.performanceBaseline = 0;
        this.rewardBreakdown = null;
    }

    /**
     * Set debug mode
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }

    /**
     * Get the last reward breakdown (only available in debug mode)
     */
    getLastRewardBreakdown() {
        return this.rewardBreakdown;
    }
}

/**
 * Static helper function to create a simple outcome object
 * @param {Object} basicOutcome - Basic outcome properties
 * @returns {Object} Structured outcome object
 */
export function createOutcome(basicOutcome = {}) {
    return {
        // Movement outcomes
        moveSuccessful: false,
        blocked: false,
        distanceToObjective: undefined,
        previousDistanceToObjective: undefined,
        objectiveReached: false,
        newAreaExplored: false,
        positionImproved: false,
        positionWorsened: false,
        efficientPath: false,
        inefficientPath: false,
        formationMaintained: false,
        formationBroken: false,
        movedIntoThreat: false,

        // Combat outcomes
        damageDealt: 0,
        enemyEliminated: false,
        attackSuccessful: false,
        criticalHit: false,
        firstStrike: false,
        focusFire: false,
        flanking: false,
        ambush: false,
        counterAttack: false,
        missedAttack: false,
        friendlyFire: false,
        attackOutOfRange: false,
        overkill: false,
        unitHealthPercentage: undefined,

        // Tactical outcomes
        successfulEscape: false,
        retreatWhenDamaged: false,
        unnecessaryRetreat: false,
        retreatedToSafety: false,
        retreatedIntoThreat: false,
        liveToFightAgain: false,
        defendedObjective: false,
        blockedEnemyAdvance: false,
        maintainedWatch: false,
        heldUnderFire: false,
        holdUnnecessarily: false,
        fortifiedPosition: false,
        areaCovered: 0,
        enemyDetected: false,
        routeCompleted: false,
        vigilantPatrol: false,
        patrolWhenNeeded: false,
        inefficientPatrol: false,

        // Economic outcomes
        resourcesGathered: 0,
        efficientGathering: false,
        fullLoad: false,
        minimizedEmptyTrips: false,
        prioritizedHighValue: false,
        newResourceDiscovered: false,
        protectedResources: false,
        sharedResourceInfo: false,
        sustainableGathering: false,
        gatheredUnderFire: false,
        lostResources: false,
        ignoredBetterResources: false,

        // Idle outcomes
        waitingForOrders: false,
        conservingEnergy: false,
        alertIdling: false,
        idleWhenNeeded: false,
        idleUnderFire: false,
        wastedOpportunity: false,
        idleTooLong: false,

        // Special outcomes
        missionSuccess: false,
        savedAlly: false,
        perfectExecution: false,
        missionFailure: false,
        allyDestroyed: false,
        catastrophicFailure: false,
        firstTimeSuccess: false,
        mastery: false,
        breakthrough: false,

        // Learning outcomes
        performanceBetter: false,
        consistentPerformance: false,
        adaptedToSituation: false,
        performanceWorse: false,

        // Override with provided values
        ...basicOutcome
    };
}