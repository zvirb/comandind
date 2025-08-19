/**
 * Reward Configuration for RTS AI Learning
 * Defines reward values and parameters for all 16 RTS commands
 * 
 * Reward Philosophy:
 * - Positive rewards for achieving objectives and good tactical decisions
 * - Negative rewards for failures, damage, and poor positioning
 * - Reward shaping to guide learning toward effective behaviors
 * - Balanced rewards across different command types to encourage diverse strategies
 */

export const RewardConfig = {
    // Global reward parameters
    global: {
        // Scaling factors for different reward types
        movementScale: 1.0,
        combatScale: 2.0,       // Combat more important than movement
        economicScale: 1.5,     // Economy important for long-term success
        tacticalScale: 1.2,     // Tactical positioning moderately important
        
        // Time-based decay for rewards
        timeDecayFactor: 0.95,  // Rewards decay over time to encourage quick action
        maxRewardMagnitude: 100, // Cap rewards to prevent extreme values
        
        // Learning shaping parameters
        explorationBonus: 2,    // Small bonus for trying new actions
        repetitionPenalty: -1,  // Small penalty for repeating same action
        diversityBonus: 5,      // Bonus for using varied strategies
    },

    // Movement commands (actions 0-7: 8 directional movement)
    movement: {
        // Base rewards for movement
        moveSuccess: 1,         // Basic reward for successful movement
        moveBlocked: -2,        // Penalty for blocked movement
        moveIntoThreat: -5,     // Penalty for moving into dangerous areas
        
        // Objective-based movement rewards
        moveTowardObjective: 3,     // Moving closer to assigned objective
        moveAwayFromObjective: -2,  // Moving away from objective
        reachObjective: 15,         // Reaching the objective location
        
        // Exploration and positioning
        exploreNewArea: 5,      // Bonus for exploring unseen territory
        improvePosition: 3,     // Better tactical position (higher ground, cover)
        worsenPosition: -2,     // Moving to worse tactical position
        
        // Distance and efficiency
        efficientPathBonus: 2,  // Following optimal path
        inefficientPathPenalty: -1, // Taking longer routes unnecessarily
        stuckPenalty: -3,       // Not moving when should be moving
        
        // Formation and coordination
        maintainFormation: 2,   // Staying in formation with allies
        breakFormation: -1,     // Breaking away from formation inappropriately
    },

    // Combat commands (actions 8-10: attack nearest/weakest/strongest)
    combat: {
        // Damage and elimination rewards
        damageDealt: 0.5,       // Per point of damage dealt to enemies
        enemyEliminated: 50,    // Large reward for eliminating enemy unit
        criticalHit: 10,        // Bonus for critical hits or effective damage
        
        // Target selection rewards
        attackNearestReward: 5,     // Reward for attacking nearest (action 8)
        attackWeakestReward: 8,     // Higher reward for attacking weakest (action 9)
        attackStrongestReward: 3,   // Lower reward for attacking strongest (action 10)
        
        // Combat efficiency
        firstStrikeBonus: 5,    // Attacking before being attacked
        focusFireBonus: 8,      // Multiple units attacking same target
        overkillPenalty: -3,    // Attacking already dying enemies
        
        // Tactical combat
        flanking: 10,           // Attacking from favorable angle
        ambush: 15,             // Surprise attack bonus
        counterAttack: 8,       // Defensive attack when threatened
        
        // Combat failures
        missedAttack: -1,       // Missing an attack
        friendlyFire: -20,      // Damaging allied units
        attackOutOfRange: -2,   // Attempting impossible attacks
        
        // Survival and health management
        lowHealthCombat: -5,    // Fighting when critically injured
        healthyEngagement: 2,   // Fighting at good health levels
    },

    // Tactical commands (actions 11-13: retreat, hold position, patrol)
    tactical: {
        // Retreat command (action 11)
        retreat: {
            successfulEscape: 30,       // Successfully escaping when outnumbered
            retreatWhenDamaged: 20,     // Retreating when health is low
            unnecessaryRetreat: -5,     // Retreating when winning
            retreatToSafety: 15,        // Reaching safe position
            retreatIntoThreat: -10,     // Retreating into more danger
            liveToFightAgain: 25,       // Surviving through tactical retreat
        },
        
        // Hold position command (action 12)
        holdPosition: {
            defendObjective: 10,        // Holding important positions
            blockEnemyAdvance: 8,       // Preventing enemy movement
            maintainWatch: 3,           // Surveillance and early warning
            holdWhenAttacked: 5,        // Standing ground under fire
            holdUnnecessarily: -2,      // Holding when should be mobile
            fortifyPosition: 6,         // Taking defensive advantage of terrain
        },
        
        // Patrol command (action 13)
        patrol: {
            areaCoverage: 2,            // Per area unit covered efficiently
            enemyDetection: 10,         // Spotting enemy units while patrolling
            routeCompletion: 5,         // Completing patrol route
            vigilantPatrol: 3,          // Maintaining alertness during patrol
            patrolWhenNeeded: 5,        // Patrolling when no immediate threats
            inefficientPatrol: -2,      // Poor patrol routes or timing
        },
    },

    // Economic command (action 14: gather resource)
    economic: {
        // Resource gathering
        resourceGathered: 25,       // Per resource unit collected
        efficientGathering: 5,      // Taking shortest route to resources
        fullLoadBonus: 10,          // Maximizing cargo before returning
        
        // Resource management
        newResourceDiscovery: 15,   // Finding new resource deposits
        protectResources: 8,        // Defending resource sites
        shareResourceInfo: 5,       // Communicating resource locations
        
        // Economic efficiency
        minimizeEmptyTrips: 3,      // Avoiding unnecessary travel
        prioritizeHighValue: 8,     // Choosing valuable resources first
        sustainableGathering: 5,    // Not depleting resources too quickly
        
        // Economic failures
        gatherUnderFire: -8,        // Gathering while being attacked
        loseResources: -15,         // Dropping resources due to damage
        ignoreBetterResources: -3,  // Missing more efficient gathering opportunities
    },

    // Passive command (action 15: idle)
    idle: {
        // Appropriate idle behavior
        waitForOrders: 1,           // Standing by when no clear action
        conserveEnergy: 2,          // Resting when not needed
        alertIdling: 3,             // Being ready to respond while idle
        
        // Inappropriate idle behavior
        idleWhenNeeded: -5,         // Not acting when action is required
        idleUnderFire: -10,         // Standing still while being attacked
        wasteOpportunity: -8,       // Missing obvious beneficial actions
        idleTooLong: -3,            // Being inactive for extended periods
    },

    // Situational modifiers that apply to all actions
    situational: {
        // Health-based modifiers
        healthMultipliers: {
            critical: 0.5,          // 0-25% health: reduced rewards
            low: 0.8,               // 25-50% health: slightly reduced
            healthy: 1.0,           // 50-100% health: normal rewards
        },
        
        // Threat level modifiers
        threatMultipliers: {
            noThreat: 1.0,          // Safe environment
            lowThreat: 1.1,         // Minor threats: slight bonus for good decisions
            highThreat: 1.3,        // Major threats: higher rewards for survival
            critical: 1.5,          // Extreme danger: maximum reward scaling
        },
        
        // Time pressure modifiers
        urgencyMultipliers: {
            relaxed: 1.0,           // No time pressure
            moderate: 1.1,          // Some urgency
            urgent: 1.2,            // High urgency
            critical: 1.4,          // Critical timing
        },
        
        // Team coordination bonuses
        teamwork: {
            coordinatedAction: 5,    // Acting in sync with team
            supportAllies: 8,        // Helping teammates
            teamObjective: 10,       // Contributing to team goals
            loneWolfPenalty: -3,     // Ignoring team when coordination needed
        },
        
        // Learning and adaptation bonuses
        learning: {
            improvementBonus: 3,     // Performing better than recent average
            consistencyBonus: 2,     // Maintaining good performance
            adaptationBonus: 5,      // Successfully adapting to new situations
            regressionPenalty: -2,   // Performing worse than capability
        },
    },

    // Special reward scenarios that override base calculations
    special: {
        // Major achievements
        missionSuccess: 100,        // Completing primary objectives
        saveAlly: 40,              // Rescuing endangered teammate
        perfectExecution: 30,       // Flawless performance in complex situation
        
        // Major failures
        missionFailure: -100,       // Failing primary objectives
        allyDestroyed: -30,         // Ally lost due to poor coordination
        catastrophicFailure: -50,   // Major tactical blunder
        
        // Learning milestones
        firstTimeSuccess: 20,       // Successfully performing new action type
        mastery: 15,               // Consistently excellent performance
        breakthrough: 25,           // Overcoming persistent challenge
    },

    // Meta-learning parameters for reward system evolution
    metaLearning: {
        // Adaptive reward scaling
        rewardDecay: 0.999,         // Gradually reduce reward magnitudes over time
        difficultyScaling: 1.05,    // Increase standards as performance improves
        
        // Performance-based adjustments
        performanceThresholds: {
            excellent: 0.8,         // Top 20% performance
            good: 0.6,             // Top 40% performance  
            average: 0.4,          // Average performance
            poor: 0.2,             // Bottom 20% performance
        },
        
        // Dynamic reward adjustment
        rewardAdaptation: {
            increaseForImprovement: 1.1,
            decreaseForMastery: 0.95,
            resetForRegression: 1.0,
        },
    },
};

/**
 * Helper function to get action-specific reward configuration
 * @param {number} actionId - The action ID (0-15)
 * @returns {Object} Action-specific reward configuration
 */
export function getActionRewardConfig(actionId) {
    // Movement actions (0-7)
    if (actionId >= 0 && actionId <= 7) {
        return RewardConfig.movement;
    }
    
    // Combat actions (8-10)
    if (actionId >= 8 && actionId <= 10) {
        return RewardConfig.combat;
    }
    
    // Tactical actions (11-13)
    if (actionId >= 11 && actionId <= 13) {
        switch (actionId) {
            case 11: return RewardConfig.tactical.retreat;
            case 12: return RewardConfig.tactical.holdPosition;
            case 13: return RewardConfig.tactical.patrol;
        }
    }
    
    // Economic action (14)
    if (actionId === 14) {
        return RewardConfig.economic;
    }
    
    // Idle action (15)
    if (actionId === 15) {
        return RewardConfig.idle;
    }
    
    return {};
}

/**
 * Validate reward configuration
 * @returns {boolean} True if configuration is valid
 */
export function validateRewardConfig() {
    try {
        // Check that all required sections exist
        const requiredSections = ['global', 'movement', 'combat', 'tactical', 'economic', 'idle', 'situational', 'special'];
        for (const section of requiredSections) {
            if (!RewardConfig[section]) {
                console.error(`Missing reward config section: ${section}`);
                return false;
            }
        }
        
        // Check that reward values are reasonable
        const checkRewardRange = (obj, path = '') => {
            for (const [key, value] of Object.entries(obj)) {
                if (typeof value === 'number') {
                    if (Math.abs(value) > RewardConfig.global.maxRewardMagnitude) {
                        console.warn(`Reward value ${path}.${key} (${value}) exceeds maximum magnitude`);
                    }
                } else if (typeof value === 'object' && value !== null) {
                    checkRewardRange(value, path ? `${path}.${key}` : key);
                }
            }
        };
        
        checkRewardRange(RewardConfig);
        
        console.log('Reward configuration validation successful');
        return true;
        
    } catch (error) {
        console.error('Error validating reward configuration:', error);
        return false;
    }
}