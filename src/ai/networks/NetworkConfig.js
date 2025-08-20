/**
 * Neural Network Configuration for Q-Learning
 * Defines architecture and hyperparameters for Deep Q-Network (DQN)
 */

export const NetworkConfig = {
    // Network Architecture
    INPUT_SIZE: 36,          // State vector dimensions
    HIDDEN_SIZE: 64,         // Hidden layer neurons
    OUTPUT_SIZE: 16,         // Q-values for each action
    
    // Learning Parameters
    LEARNING_RATE: 0.001,    // Adam optimizer learning rate
    DISCOUNT_FACTOR: 0.95,   // Gamma for Q-learning
    EPSILON: 0.1,            // Exploration rate
    EPSILON_DECAY: 0.995,    // Epsilon decay per episode
    EPSILON_MIN: 0.01,       // Minimum epsilon value
    
    // Training Configuration
    BATCH_SIZE: 32,          // Training batch size
    MEMORY_SIZE: 10000,      // Experience replay buffer size
    TARGET_UPDATE_FREQ: 100, // Target network update frequency
    
    // Performance Constraints
    MAX_MEMORY_MB: 50,       // Maximum memory budget
    TARGET_INFERENCE_MS: 5,  // Target inference time
    
    // Model Configuration
    ACTIVATION: "relu",      // Hidden layer activation
    OUTPUT_ACTIVATION: "linear", // Output layer activation (Q-values)
    LOSS_FUNCTION: "meanSquaredError",
    OPTIMIZER: "adam",
    
    // Regularization
    DROPOUT_RATE: 0.1,       // Dropout for regularization
    L2_REGULARIZATION: 0.01, // L2 weight decay
    
    // Model Persistence
    MODEL_SAVE_PATH: "qnetwork-model",
    CHECKPOINT_FREQUENCY: 1000, // Save every N training steps
    
    // WebGL Backend Settings
    WEBGL_PACK: true,        // Enable WebGL texture packing
    WEBGL_FORCE_F16_TEXTURES: false, // Use float16 for memory efficiency
    
    // Validation
    VALIDATION_SPLIT: 0.1,   // Fraction for validation
    EARLY_STOPPING_PATIENCE: 50, // Stop if no improvement
    
    /**
     * Get optimized configuration for different environments
     */
    getEnvironmentConfig(environment = "browser") {
        const configs = {
            browser: {
                ...this,
                BATCH_SIZE: 16,           // Smaller batches for browser
                WEBGL_FORCE_F16_TEXTURES: true, // Memory optimization
            },
            node: {
                ...this,
                BATCH_SIZE: 64,           // Larger batches for Node.js
                WEBGL_PACK: false,        // Not needed in Node
            },
            mobile: {
                ...this,
                HIDDEN_SIZE: 32,          // Smaller network
                BATCH_SIZE: 8,            // Very small batches
                MAX_MEMORY_MB: 25,        // Stricter memory limit
                WEBGL_FORCE_F16_TEXTURES: true,
            }
        };
        
        return configs[environment] || this;
    },
    
    /**
     * Validate configuration parameters
     */
    validate() {
        const errors = [];
        
        if (this.INPUT_SIZE <= 0) errors.push("INPUT_SIZE must be positive");
        if (this.HIDDEN_SIZE <= 0) errors.push("HIDDEN_SIZE must be positive");
        if (this.OUTPUT_SIZE <= 0) errors.push("OUTPUT_SIZE must be positive");
        if (this.LEARNING_RATE <= 0 || this.LEARNING_RATE >= 1) {
            errors.push("LEARNING_RATE must be between 0 and 1");
        }
        if (this.DISCOUNT_FACTOR < 0 || this.DISCOUNT_FACTOR > 1) {
            errors.push("DISCOUNT_FACTOR must be between 0 and 1");
        }
        if (this.BATCH_SIZE <= 0) errors.push("BATCH_SIZE must be positive");
        
        if (errors.length > 0) {
            throw new Error(`NetworkConfig validation failed: ${errors.join(", ")}`);
        }
        
        return true;
    }
};

// Export individual configurations for specific use cases
export const COMPACT_CONFIG = NetworkConfig.getEnvironmentConfig("mobile");
export const PERFORMANCE_CONFIG = NetworkConfig.getEnvironmentConfig("node");
export const BROWSER_CONFIG = NetworkConfig.getEnvironmentConfig("browser");

export default NetworkConfig;