/**
 * Deep Q-Network (DQN) implementation using TensorFlow.js
 * Provides Q-value approximation for reinforcement learning
 */

import * as tf from "@tensorflow/tfjs";
import { NetworkConfig } from "./NetworkConfig.js";

export class QNetwork {
    constructor(config = NetworkConfig) {
        this.config = config;
        this.model = null;
        this.targetModel = null;
        this.isCompiled = false;
        this.trainingStep = 0;
        
        // Performance tracking
        this.inferenceTime = 0;
        this.memoryUsage = 0;
        
        // Initialize models
        this.initializeModel();
        this.initializeTargetModel();
    }
    
    /**
     * Initialize the main Q-network model
     */
    initializeModel() {
        try {
            this.model = tf.sequential({
                layers: [
                    // Input layer
                    tf.layers.dense({
                        inputShape: [this.config.INPUT_SIZE],
                        units: this.config.HIDDEN_SIZE,
                        activation: this.config.ACTIVATION,
                        kernelRegularizer: tf.regularizers.l2({ l2: this.config.L2_REGULARIZATION }),
                        name: "hidden_layer"
                    }),
                    
                    // Dropout for regularization
                    tf.layers.dropout({
                        rate: this.config.DROPOUT_RATE,
                        name: "dropout_layer"
                    }),
                    
                    // Output layer (Q-values)
                    tf.layers.dense({
                        units: this.config.OUTPUT_SIZE,
                        activation: this.config.OUTPUT_ACTIVATION,
                        name: "output_layer"
                    })
                ]
            });
            
            this.compileModel();
            console.log("Q-Network model initialized successfully");
            
        } catch (error) {
            console.error("Failed to initialize Q-Network model:", error);
            throw error;
        }
    }
    
    /**
     * Initialize target network (copy of main network)
     */
    initializeTargetModel() {
        if (!this.model) {
            throw new Error("Main model must be initialized before target model");
        }
        
        try {
            // Clone the model architecture
            this.targetModel = tf.sequential({
                layers: [
                    tf.layers.dense({
                        inputShape: [this.config.INPUT_SIZE],
                        units: this.config.HIDDEN_SIZE,
                        activation: this.config.ACTIVATION,
                        kernelRegularizer: tf.regularizers.l2({ l2: this.config.L2_REGULARIZATION }),
                        name: "target_hidden_layer"
                    }),
                    tf.layers.dropout({
                        rate: this.config.DROPOUT_RATE,
                        name: "target_dropout_layer"
                    }),
                    tf.layers.dense({
                        units: this.config.OUTPUT_SIZE,
                        activation: this.config.OUTPUT_ACTIVATION,
                        name: "target_output_layer"
                    })
                ]
            });
            
            this.targetModel.compile({
                optimizer: this.config.OPTIMIZER,
                loss: this.config.LOSS_FUNCTION
            });
            
            // Copy weights from main model
            this.updateTargetNetwork();
            console.log("Target network initialized successfully");
            
        } catch (error) {
            console.error("Failed to initialize target network:", error);
            throw error;
        }
    }
    
    /**
     * Compile the model with optimizer and loss function
     */
    compileModel() {
        if (!this.model) {
            throw new Error("Model must be initialized before compilation");
        }
        
        this.model.compile({
            optimizer: tf.train.adam(this.config.LEARNING_RATE),
            loss: this.config.LOSS_FUNCTION,
            metrics: ["mse"]
        });
        
        this.isCompiled = true;
        console.log("Model compiled successfully");
    }
    
    /**
     * Predict Q-values for given states
     * @param {tf.Tensor|Array} states - Input states
     * @param {boolean} training - Whether in training mode (affects dropout)
     * @returns {tf.Tensor} Q-values for each action
     */
    predict(states, training = false) {
        if (!this.model || !this.isCompiled) {
            throw new Error("Model must be compiled before prediction");
        }
        
        const startTime = performance.now();
        
        try {
            // Ensure input is a tensor
            const stateTensor = states instanceof tf.Tensor ? states : tf.tensor2d(states);
            
            // Perform prediction
            const qValues = this.model.predict(stateTensor, { training });
            
            // Track performance
            this.inferenceTime = performance.now() - startTime;
            
            // Clean up input tensor if we created it
            if (!(states instanceof tf.Tensor)) {
                stateTensor.dispose();
            }
            
            return qValues;
            
        } catch (error) {
            console.error("Prediction failed:", error);
            throw error;
        }
    }
    
    /**
     * Predict Q-values using target network
     * @param {tf.Tensor|Array} states - Input states
     * @returns {tf.Tensor} Target Q-values
     */
    predictTarget(states) {
        if (!this.targetModel) {
            throw new Error("Target model must be initialized");
        }
        
        try {
            const stateTensor = states instanceof tf.Tensor ? states : tf.tensor2d(states);
            const targetQValues = this.targetModel.predict(stateTensor);
            
            if (!(states instanceof tf.Tensor)) {
                stateTensor.dispose();
            }
            
            return targetQValues;
            
        } catch (error) {
            console.error("Target prediction failed:", error);
            throw error;
        }
    }
    
    /**
     * Update network weights using experience batch
     * @param {Object} batch - Training batch {states, actions, rewards, nextStates, dones}
     * @returns {Object} Training metrics
     */
    async update(batch) {
        if (!this.model || !this.isCompiled) {
            throw new Error("Model must be compiled before training");
        }
        
        const { states, actions, rewards, nextStates, dones } = batch;
        
        try {
            // Simplified training approach to avoid tensor dtype issues
            const stateTensor = tf.tensor2d(states);
            const nextStateTensor = tf.tensor2d(nextStates);
            
            // Get current and next Q-values
            const currentQValues = this.model.predict(stateTensor);
            const nextQValues = this.targetModel.predict(nextStateTensor);
            
            // Create target Q-values using tidy to manage memory
            const targetQValuesResult = await tf.tidy(() => {
                const currentQValuesArray = currentQValues.arraySync();
                const nextQValuesArray = nextQValues.arraySync();
                
                // Compute targets manually for better control
                const targets = currentQValuesArray.map((qVals, i) => {
                    const newQVals = [...qVals];
                    const action = actions[i];
                    const reward = rewards[i];
                    const done = dones[i];
                    
                    const maxNextQ = Math.max(...nextQValuesArray[i]);
                    const target = reward + (done ? 0 : this.config.DISCOUNT_FACTOR * maxNextQ);
                    
                    newQVals[action] = target;
                    return newQVals;
                });
                
                return tf.tensor2d(targets);
            });
            
            // Train the model
            const history = await this.model.fit(stateTensor, targetQValuesResult, {
                epochs: 1,
                verbose: 0,
                batchSize: this.config.BATCH_SIZE
            });
            
            // Clean up tensors
            stateTensor.dispose();
            nextStateTensor.dispose();
            currentQValues.dispose();
            nextQValues.dispose();
            targetQValuesResult.dispose();
            
            this.trainingStep++;
            
            // Update target network periodically
            if (this.trainingStep % this.config.TARGET_UPDATE_FREQ === 0) {
                this.updateTargetNetwork();
            }
            
            return {
                loss: history.history.loss[0],
                step: this.trainingStep,
                inferenceTime: this.inferenceTime
            };
            
        } catch (error) {
            console.error("Training update failed:", error);
            throw error;
        }
    }
    
    /**
     * Update target network weights from main network
     */
    updateTargetNetwork() {
        if (!this.model || !this.targetModel) {
            throw new Error("Both models must be initialized");
        }
        
        try {
            const weights = this.model.getWeights();
            this.targetModel.setWeights(weights);
            console.log("Target network updated");
            
        } catch (error) {
            console.error("Failed to update target network:", error);
            throw error;
        }
    }
    
    /**
     * Save the model to storage
     * @param {string} path - Save path
     * @returns {Promise} Save promise
     */
    async saveModel(path = this.config.MODEL_SAVE_PATH) {
        if (!this.model) {
            throw new Error("Model must be initialized before saving");
        }
        
        try {
            const saveResult = await this.model.save(`localstorage://${path}`);
            console.log("Model saved successfully:", saveResult);
            return saveResult;
            
        } catch (error) {
            console.error("Failed to save model:", error);
            throw error;
        }
    }
    
    /**
     * Load a saved model
     * @param {string} path - Load path
     * @returns {Promise} Load promise
     */
    async loadModel(path = this.config.MODEL_SAVE_PATH) {
        try {
            this.model = await tf.loadLayersModel(`localstorage://${path}`);
            this.compileModel();
            this.initializeTargetModel();
            console.log("Model loaded successfully");
            
        } catch (error) {
            console.error("Failed to load model:", error);
            throw error;
        }
    }
    
    /**
     * Get model summary and performance metrics
     * @returns {Object} Model information
     */
    getModelInfo() {
        if (!this.model) {
            return { error: "Model not initialized" };
        }
        
        const memoryInfo = tf.memory();
        
        return {
            architecture: {
                inputSize: this.config.INPUT_SIZE,
                hiddenSize: this.config.HIDDEN_SIZE,
                outputSize: this.config.OUTPUT_SIZE,
                totalParams: this.model.countParams()
            },
            performance: {
                inferenceTime: this.inferenceTime,
                trainingStep: this.trainingStep,
                memoryUsage: memoryInfo.numBytes / (1024 * 1024) // MB
            },
            config: this.config,
            isCompiled: this.isCompiled,
            hasTargetNetwork: !!this.targetModel
        };
    }
    
    /**
     * Clean up resources
     */
    dispose() {
        if (this.model) {
            this.model.dispose();
            this.model = null;
        }
        
        if (this.targetModel) {
            this.targetModel.dispose();
            this.targetModel = null;
        }
        
        this.isCompiled = false;
        console.log("QNetwork resources disposed");
    }
    
    /**
     * Validate that the model meets performance requirements
     * @returns {Object} Validation results
     */
    validatePerformance() {
        const info = this.getModelInfo();
        const results = {
            memoryBudget: info.performance.memoryUsage <= this.config.MAX_MEMORY_MB,
            inferenceSpeed: this.inferenceTime <= this.config.TARGET_INFERENCE_MS,
            architecture: info.architecture.totalParams > 0,
            compilation: this.isCompiled
        };
        
        results.overall = Object.values(results).every(Boolean);
        
        return {
            passed: results.overall,
            details: results,
            metrics: info.performance
        };
    }
}

export default QNetwork;