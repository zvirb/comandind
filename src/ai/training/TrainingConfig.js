/**
 * Training Configuration for Q-Learning System
 * Defines hyperparameters and settings for neural network training
 */

export const TrainingConfig = {
    // Learning parameters
    learning: {
        learningRate: 0.001,          // Learning rate for neural network
        batchSize: 32,                // Number of experiences per training batch
        discountFactor: 0.95,         // Gamma - future reward discount
        targetUpdateFrequency: 100,   // Steps between target network updates
        minExperiencesForTraining: 1000, // Minimum experiences before training starts
    },

    // Exploration parameters
    exploration: {
        epsilonStart: 1.0,           // Initial exploration rate
        epsilonEnd: 0.01,            // Final exploration rate
        epsilonDecaySteps: 10000,    // Steps over which epsilon decays
        epsilonDecayRate: 0.995,     // Exponential decay rate per step
    },

    // Training loop parameters
    training: {
        trainingFrequency: 4,        // Train every N steps
        saveFrequency: 100,          // Save checkpoint every N episodes
        validationFrequency: 50,     // Validate performance every N episodes
        maxEpisodes: 10000,          // Maximum training episodes
        maxStepsPerEpisode: 1000,    // Maximum steps per episode
        convergenceThreshold: 0.01,  // Loss threshold for convergence
        convergenceWindow: 100,      // Episodes to check for convergence
    },

    // Performance monitoring
    monitoring: {
        logFrequency: 10,            // Log metrics every N episodes
        lossHistorySize: 1000,       // Number of loss values to keep
        rewardHistorySize: 1000,     // Number of reward values to keep
        trackGradients: false,       // Track gradient statistics
        trackWeights: false,         // Track weight statistics
    },

    // Memory management
    memory: {
        maxBatchesInMemory: 100,     // Maximum training batches to keep in memory
        gcFrequency: 1000,           // Garbage collection frequency (steps)
        memoryWarningThreshold: 500, // MB threshold for memory warning
    },

    // Model architecture (for neural network creation)
    network: {
        inputSize: 36,               // State vector size
        outputSize: 16,              // Action space size
        hiddenLayers: [128, 128, 64], // Hidden layer sizes
        activation: "relu",          // Activation function
        outputActivation: "linear",  // Output layer activation
        dropout: 0.1,                // Dropout rate
        batchNormalization: false,   // Use batch normalization
        l2Regularization: 0.0001,    // L2 regularization strength
    },

    // Optimizer settings
    optimizer: {
        type: "adam",                // Optimizer type: 'adam', 'sgd', 'rmsprop'
        beta1: 0.9,                  // Adam beta1 parameter
        beta2: 0.999,                // Adam beta2 parameter
        epsilon: 1e-8,               // Adam epsilon parameter
        momentum: 0.9,               // SGD momentum
        rho: 0.9,                    // RMSprop rho parameter
        clipNorm: 1.0,               // Gradient clipping norm
    },

    // Validation settings
    validation: {
        episodes: 10,                // Episodes for validation
        explorationRate: 0.05,       // Epsilon during validation
        maxStepsPerEpisode: 500,     // Max steps per validation episode
        requirementTargets: {
            averageReward: 100,      // Target average reward
            successRate: 0.8,        // Target success rate
            episodeLength: 200,      // Target episode length
        }
    },

    // Checkpoint settings
    checkpoints: {
        saveDirectory: "./checkpoints",  // Directory to save checkpoints
        keepLastN: 10,               // Number of checkpoints to keep
        saveOnBestReward: true,      // Save when achieving best reward
        saveOnConvergence: true,     // Save when converged
        compressionLevel: 6,         // Compression level for saved models
    },

    // Debug and logging
    debug: {
        verbose: false,              // Verbose logging
        logLoss: true,               // Log training loss
        logRewards: true,            // Log episode rewards
        logExploration: true,        // Log exploration statistics
        logMemoryUsage: true,        // Log memory usage
        logTimings: true,            // Log training timings
        visualizeNetwork: false,     // Enable network visualization
        saveGradientStats: false,    // Save gradient statistics
    },

    // Performance optimization
    performance: {
        useWebWorker: false,         // Use web worker for training (future)
        batchTrainingAsync: true,    // Async batch training
        prioritizedReplay: false,    // Use prioritized experience replay
        doubleQLearning: false,      // Use Double Q-Learning
        duelingNetwork: false,       // Use Dueling DQN architecture
        frameSkipping: 1,            // Number of frames to skip
    },

    // Early stopping
    earlyStopping: {
        enabled: true,               // Enable early stopping
        patience: 500,               // Episodes to wait without improvement
        minDelta: 0.001,             // Minimum improvement threshold
        monitorMetric: "averageReward", // Metric to monitor: 'loss' or 'averageReward'
        mode: "max",                 // 'min' for loss, 'max' for reward
    },

    // Training phases
    phases: {
        warmup: {
            episodes: 100,           // Warmup episodes with random actions
            explorationRate: 1.0,    // High exploration during warmup
        },
        exploration: {
            episodes: 2000,          // Exploration phase episodes
            explorationDecay: true,  // Decay exploration during this phase
        },
        exploitation: {
            episodes: 5000,          // Exploitation phase episodes
            explorationRate: 0.05,   // Low exploration rate
        },
        finetuning: {
            episodes: 3000,          // Fine-tuning episodes
            learningRate: 0.0001,    // Reduced learning rate
            explorationRate: 0.01,   // Minimal exploration
        }
    }
};

/**
 * Gets configuration for a specific training phase
 */
export function getPhaseConfig(phase, baseConfig = TrainingConfig) {
    const phaseConfigs = {
        warmup: {
            ...baseConfig,
            exploration: {
                ...baseConfig.exploration,
                epsilonStart: baseConfig.phases.warmup.explorationRate,
                epsilonEnd: baseConfig.phases.warmup.explorationRate,
                epsilonDecaySteps: 1, // No decay during warmup
            }
        },
        
        exploration: {
            ...baseConfig,
            exploration: {
                ...baseConfig.exploration,
                epsilonDecaySteps: baseConfig.phases.exploration.episodes * 
                                  baseConfig.training.maxStepsPerEpisode / 4
            }
        },
        
        exploitation: {
            ...baseConfig,
            learning: {
                ...baseConfig.learning,
                learningRate: baseConfig.learning.learningRate * 0.5
            },
            exploration: {
                ...baseConfig.exploration,
                epsilonStart: baseConfig.phases.exploitation.explorationRate,
                epsilonEnd: baseConfig.phases.exploitation.explorationRate,
                epsilonDecaySteps: 1
            }
        },
        
        finetuning: {
            ...baseConfig,
            learning: {
                ...baseConfig.learning,
                learningRate: baseConfig.phases.finetuning.learningRate
            },
            exploration: {
                ...baseConfig.exploration,
                epsilonStart: baseConfig.phases.finetuning.explorationRate,
                epsilonEnd: baseConfig.phases.finetuning.explorationRate,
                epsilonDecaySteps: 1
            }
        }
    };

    return phaseConfigs[phase] || baseConfig;
}

/**
 * Validates training configuration
 */
export function validateTrainingConfig(config) {
    const errors = [];
    const warnings = [];

    // Required parameters
    if (!config.learning || config.learning.learningRate <= 0) {
        errors.push("Learning rate must be positive");
    }

    if (!config.learning || config.learning.batchSize <= 0) {
        errors.push("Batch size must be positive");
    }

    if (!config.network || config.network.inputSize !== 36) {
        errors.push("Input size must be 36 for state vector");
    }

    if (!config.network || config.network.outputSize !== 16) {
        errors.push("Output size must be 16 for action space");
    }

    // Warnings for suboptimal settings
    if (config.learning && config.learning.learningRate > 0.1) {
        warnings.push("Learning rate seems very high, may cause instability");
    }

    if (config.exploration && config.exploration.epsilonDecaySteps < 1000) {
        warnings.push("Epsilon decay seems too fast, may reduce exploration too quickly");
    }

    if (config.training && config.training.targetUpdateFrequency < 10) {
        warnings.push("Target update frequency is very low, may cause instability");
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings
    };
}

/**
 * Creates a configuration optimized for performance profiling
 */
export function createProfileConfig() {
    return {
        ...TrainingConfig,
        learning: {
            ...TrainingConfig.learning,
            batchSize: 16,                    // Smaller batches for profiling
            targetUpdateFrequency: 50,       // More frequent updates
        },
        training: {
            ...TrainingConfig.training,
            maxEpisodes: 100,                 // Fewer episodes for quick profiling
            trainingFrequency: 1,             // Train every step
            logFrequency: 1,                  // Log every episode
        },
        debug: {
            ...TrainingConfig.debug,
            verbose: true,
            logTimings: true,
            logMemoryUsage: true,
        },
        performance: {
            ...TrainingConfig.performance,
            batchTrainingAsync: false,        // Synchronous for profiling
        }
    };
}