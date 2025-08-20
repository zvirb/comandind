import * as tf from "@tensorflow/tfjs";
import { TrainingConfig, validateTrainingConfig, getPhaseConfig } from "./TrainingConfig.js";
import { ExperienceBuffer } from "../components/ExperienceBuffer.js";

/**
 * Training Manager for Q-Learning Neural Networks
 * Implements the core training loop with experience replay, target networks,
 * and comprehensive performance tracking
 */
export class TrainingManager {
    constructor(options = {}) {
        // Configuration
        this.config = { ...TrainingConfig, ...options.config };
        this.validateConfiguration();

        // Training state
        this.isTraining = false;
        this.isPaused = false;
        this.currentEpisode = 0;
        this.currentStep = 0;
        this.trainingStep = 0;
        this.lastTargetUpdate = 0;
        this.currentPhase = "warmup";

        // Networks
        this.qNetwork = options.qNetwork || null;
        this.targetNetwork = options.targetNetwork || null;
        this.optimizer = null;

        // Experience buffer
        this.experienceBuffer = options.experienceBuffer || new ExperienceBuffer({
            maxSize: 10000,
            batchSize: this.config.learning.batchSize,
            prioritizedReplay: this.config.performance.prioritizedReplay
        });

        // Performance tracking
        this.metrics = {
            episode: {
                rewards: [],
                lengths: [],
                losses: [],
                explorationRates: [],
                qValues: []
            },
            training: {
                totalLoss: 0,
                lossHistory: [],
                gradientNorms: [],
                weightsStats: [],
                batchCount: 0,
                convergenceScore: 0
            },
            performance: {
                trainTime: 0,
                inferenceTime: 0,
                memoryUsage: [],
                fps: 0,
                lastEpisodeTime: 0
            },
            validation: {
                scores: [],
                successRates: [],
                lastValidation: null
            }
        };

        // Training timers and intervals
        this.timers = {
            episode: null,
            training: null,
            validation: null,
            checkpoint: null
        };

        // Early stopping
        this.earlyStopping = {
            bestScore: -Infinity,
            patienceCounter: 0,
            shouldStop: false
        };

        // Checkpointing
        this.checkpoints = {
            lastSave: 0,
            bestRewardSave: null,
            directory: this.config.checkpoints.saveDirectory
        };

        // Bind methods for async execution
        this.trainStep = this.trainStep.bind(this);
        this.runTrainingLoop = this.runTrainingLoop.bind(this);
        this.validatePerformance = this.validatePerformance.bind(this);

        console.log("🧠 Training Manager initialized with configuration:", {
            batchSize: this.config.learning.batchSize,
            learningRate: this.config.learning.learningRate,
            targetUpdateFreq: this.config.learning.targetUpdateFrequency,
            maxEpisodes: this.config.training.maxEpisodes
        });
    }

    /**
     * Validates the training configuration
     */
    validateConfiguration() {
        const validation = validateTrainingConfig(this.config);
        
        if (!validation.valid) {
            throw new Error(`Invalid training configuration: ${validation.errors.join(", ")}`);
        }

        if (validation.warnings.length > 0) {
            console.warn("⚠️ Training configuration warnings:", validation.warnings);
        }
    }

    /**
     * Initializes neural networks and optimizer
     */
    async initializeNetworks() {
        if (!this.qNetwork) {
            this.qNetwork = this.createQNetwork();
        }

        if (!this.targetNetwork) {
            this.targetNetwork = this.createQNetwork();
            this.updateTargetNetwork(); // Initialize target with Q-network weights
        }

        if (!this.optimizer) {
            this.optimizer = this.createOptimizer();
        }

        console.log("🔧 Neural networks initialized:", {
            qNetwork: this.qNetwork.summary ? "Custom Model" : "TensorFlow Model",
            targetNetwork: "Initialized",
            optimizer: this.config.optimizer.type
        });
    }

    /**
     * Creates a Q-network with the specified architecture
     */
    createQNetwork() {
        const model = tf.sequential();
        
        // Input layer
        model.add(tf.layers.dense({
            inputShape: [this.config.network.inputSize],
            units: this.config.network.hiddenLayers[0],
            activation: this.config.network.activation,
            kernelRegularizer: this.config.network.l2Regularization > 0 ? 
                tf.regularizers.l2({ l2: this.config.network.l2Regularization }) : null
        }));

        // Add dropout if specified
        if (this.config.network.dropout > 0) {
            model.add(tf.layers.dropout({ rate: this.config.network.dropout }));
        }

        // Hidden layers
        for (let i = 1; i < this.config.network.hiddenLayers.length; i++) {
            model.add(tf.layers.dense({
                units: this.config.network.hiddenLayers[i],
                activation: this.config.network.activation,
                kernelRegularizer: this.config.network.l2Regularization > 0 ? 
                    tf.regularizers.l2({ l2: this.config.network.l2Regularization }) : null
            }));

            if (this.config.network.dropout > 0) {
                model.add(tf.layers.dropout({ rate: this.config.network.dropout }));
            }

            if (this.config.network.batchNormalization) {
                model.add(tf.layers.batchNormalization());
            }
        }

        // Output layer
        model.add(tf.layers.dense({
            units: this.config.network.outputSize,
            activation: this.config.network.outputActivation
        }));

        return model;
    }

    /**
     * Creates optimizer based on configuration
     */
    createOptimizer() {
        const config = this.config.optimizer;
        
        switch (config.type.toLowerCase()) {
        case "adam":
            return tf.train.adam(
                this.config.learning.learningRate,
                config.beta1,
                config.beta2,
                config.epsilon
            );
        case "sgd":
            return tf.train.sgd(this.config.learning.learningRate);
        case "rmsprop":
            return tf.train.rmsprop(
                this.config.learning.learningRate,
                config.rho,
                config.momentum,
                config.epsilon
            );
        default:
            throw new Error(`Unknown optimizer type: ${config.type}`);
        }
    }

    /**
     * Starts the training process
     */
    async startTraining() {
        if (this.isTraining) {
            console.warn("⚠️ Training is already running");
            return;
        }

        console.log("🚀 Starting Q-Learning training...");
        
        await this.initializeNetworks();
        
        this.isTraining = true;
        this.isPaused = false;
        this.currentEpisode = 0;
        this.currentStep = 0;
        this.trainingStep = 0;

        // Reset metrics
        this.resetMetrics();

        // Start the main training loop
        this.runTrainingLoop();
    }

    /**
     * Main training loop - runs asynchronously
     */
    async runTrainingLoop() {
        while (this.isTraining && this.currentEpisode < this.config.training.maxEpisodes) {
            if (this.isPaused) {
                await this.sleep(100);
                continue;
            }

            const episodeStartTime = performance.now();
            
            try {
                // Run episode
                const episodeResult = await this.runEpisode();
                
                // Update metrics
                this.updateEpisodeMetrics(episodeResult, episodeStartTime);
                
                // Perform training if enough experiences
                if (this.shouldTrain()) {
                    await this.performTraining();
                }

                // Update target network periodically
                if (this.shouldUpdateTarget()) {
                    this.updateTargetNetwork();
                }

                // Validation
                if (this.shouldValidate()) {
                    await this.validatePerformance();
                }

                // Checkpointing
                if (this.shouldSaveCheckpoint()) {
                    await this.saveCheckpoint();
                }

                // Check early stopping
                if (this.shouldStopEarly()) {
                    console.log("🛑 Early stopping triggered");
                    break;
                }

                // Update training phase
                this.updateTrainingPhase();

                // Logging
                if (this.shouldLog()) {
                    this.logProgress();
                }

                this.currentEpisode++;

            } catch (error) {
                console.error("❌ Episode failed:", error);
                
                // Implement error recovery or stop training
                if (this.currentEpisode > 10) {
                    console.error("💀 Too many consecutive failures, stopping training");
                    break;
                }
            }

            // Yield control to prevent blocking
            await this.sleep(1);
        }

        this.isTraining = false;
        console.log("✅ Training completed");
        
        await this.finalizeTraining();
    }

    /**
     * Simulates an episode - this would integrate with the game environment
     */
    async runEpisode() {
        let totalReward = 0;
        let stepCount = 0;
        let qValueSum = 0;
        
        // Reset episode state
        const initialState = this.createRandomState(); // Placeholder
        let currentState = initialState;
        let done = false;

        while (!done && stepCount < this.config.training.maxStepsPerEpisode) {
            // Select action using epsilon-greedy
            const action = await this.selectAction(currentState);
            
            // Execute action in environment (simulated)
            const stepResult = this.simulateEnvironmentStep(currentState, action);
            const { nextState, reward, isDone } = stepResult;

            // Store experience
            this.experienceBuffer.add(
                currentState, action, reward, nextState, isDone
            );

            // Update state and accumulate metrics
            currentState = nextState;
            totalReward += reward;
            qValueSum += await this.getMaxQValue(currentState);
            stepCount++;
            done = isDone;

            this.currentStep++;

            // Yield periodically to prevent blocking
            if (stepCount % 10 === 0) {
                await this.sleep(1);
            }
        }

        return {
            totalReward,
            stepCount,
            averageQValue: qValueSum / stepCount,
            success: totalReward > 0 // Simple success criteria
        };
    }

    /**
     * Selects action using epsilon-greedy policy
     */
    async selectAction(state) {
        const epsilon = this.getCurrentEpsilon();
        
        if (Math.random() < epsilon) {
            // Random exploration
            return Math.floor(Math.random() * this.config.network.outputSize);
        } else {
            // Exploitation using Q-network
            return this.getBestAction(state);
        }
    }

    /**
     * Gets the best action from Q-network
     */
    async getBestAction(state) {
        const stateTensor = tf.tensor2d([state]);
        const qValues = this.qNetwork.predict(stateTensor);
        const bestAction = (await qValues.argMax(-1).data())[0];
        
        stateTensor.dispose();
        qValues.dispose();
        
        return bestAction;
    }

    /**
     * Gets maximum Q-value for a state
     */
    async getMaxQValue(state) {
        const stateTensor = tf.tensor2d([state]);
        const qValues = this.qNetwork.predict(stateTensor);
        const maxQ = (await qValues.max(-1).data())[0];
        
        stateTensor.dispose();
        qValues.dispose();
        
        return maxQ;
    }

    /**
     * Performs a training step with experience replay
     */
    async performTraining() {
        if (!this.experienceBuffer.canSample()) {
            return;
        }

        const batch = this.experienceBuffer.sample();
        if (!batch) return;

        const trainingStartTime = performance.now();

        try {
            // Compute loss and train
            const loss = await this.trainOnBatch(batch);
            
            // Update metrics
            this.metrics.training.totalLoss += loss;
            this.metrics.training.lossHistory.push(loss);
            this.metrics.training.batchCount++;
            this.trainingStep++;

            // Keep loss history bounded
            if (this.metrics.training.lossHistory.length > this.config.monitoring.lossHistorySize) {
                this.metrics.training.lossHistory.shift();
            }

            const trainingTime = performance.now() - trainingStartTime;
            this.metrics.performance.trainTime += trainingTime;

            if (this.config.debug.logLoss && this.trainingStep % 100 === 0) {
                console.log(`📊 Training step ${this.trainingStep}, Loss: ${loss.toFixed(4)}, Time: ${trainingTime.toFixed(2)}ms`);
            }

        } catch (error) {
            console.error("❌ Training step failed:", error);
        }
    }

    /**
     * Trains the Q-network on a batch using the Bellman equation
     */
    async trainOnBatch(batch) {
        const { states, actions, rewards, nextStates, doneFlags } = batch;
        
        // Convert to tensors
        const statesTensor = tf.tensor2d(states);
        const nextStatesTensor = tf.tensor2d(nextStates);
        const rewardsTensor = tf.tensor1d(rewards);
        const actionsTensor = tf.tensor1d(actions, "int32");
        const donesTensor = tf.tensor1d(doneFlags.map(d => d ? 0 : 1)); // Invert done flags

        let loss = 0;

        try {
            // Compute target Q-values using target network
            const nextQValues = this.targetNetwork.predict(nextStatesTensor);
            const maxNextQValues = nextQValues.max(-1);
            
            // Compute target values: r + γ * max(Q'(s', a'))
            const targets = rewardsTensor.add(
                maxNextQValues.mul(donesTensor).mul(this.config.learning.discountFactor)
            );

            // Train using gradient descent
            const f = () => {
                const currentQValues = this.qNetwork.predict(statesTensor);
                const actionMask = tf.oneHot(actionsTensor, this.config.network.outputSize);
                const selectedQValues = currentQValues.mul(actionMask).sum(-1);
                
                // Mean squared error loss
                const loss = tf.losses.meanSquaredError(targets, selectedQValues);
                return loss;
            };

            const { value, grads } = tf.variableGrads(f);
            loss = await value.data();
            
            // Apply gradients with optional clipping
            if (this.config.optimizer.clipNorm > 0) {
                const clippedGrads = {};
                for (const key in grads) {
                    clippedGrads[key] = tf.clipByNorm(grads[key], this.config.optimizer.clipNorm);
                }
                this.optimizer.applyGradients(clippedGrads);
                
                // Cleanup clipped gradients
                Object.values(clippedGrads).forEach(grad => grad.dispose());
            } else {
                this.optimizer.applyGradients(grads);
            }

            // Cleanup
            value.dispose();
            Object.values(grads).forEach(grad => grad.dispose());
            nextQValues.dispose();
            maxNextQValues.dispose();
            targets.dispose();

        } finally {
            // Cleanup tensors
            statesTensor.dispose();
            nextStatesTensor.dispose();
            rewardsTensor.dispose();
            actionsTensor.dispose();
            donesTensor.dispose();
        }

        return loss[0] || 0;
    }

    /**
     * Updates target network with Q-network weights
     */
    updateTargetNetwork() {
        const qWeights = this.qNetwork.getWeights();
        this.targetNetwork.setWeights(qWeights);
        this.lastTargetUpdate = this.trainingStep;
        
        if (this.config.debug.verbose) {
            console.log(`🎯 Target network updated at step ${this.trainingStep}`);
        }
    }

    /**
     * Simulates an environment step (placeholder)
     */
    simulateEnvironmentStep(state, action) {
        // This would be replaced with actual game environment interaction
        const nextState = state.map((val, i) => val + (Math.random() - 0.5) * 0.1);
        const reward = Math.random() * 10 - 5; // Random reward between -5 and 5
        const done = Math.random() < 0.01; // 1% chance of episode end
        
        return {
            nextState: new Float32Array(nextState),
            reward,
            isDone: done
        };
    }

    /**
     * Creates a random state vector (placeholder)
     */
    createRandomState() {
        return new Float32Array(36).map(() => Math.random() * 2 - 1);
    }

    /**
     * Gets current exploration rate (epsilon)
     */
    getCurrentEpsilon() {
        const config = this.config.exploration;
        const step = this.currentStep;
        
        if (step >= config.epsilonDecaySteps) {
            return config.epsilonEnd;
        }
        
        // Linear decay
        const decayProgress = step / config.epsilonDecaySteps;
        return config.epsilonStart - (config.epsilonStart - config.epsilonEnd) * decayProgress;
    }

    /**
     * Checks if training should occur
     */
    shouldTrain() {
        return this.experienceBuffer.size() >= this.config.learning.minExperiencesForTraining &&
               this.currentStep % this.config.training.trainingFrequency === 0;
    }

    /**
     * Checks if target network should be updated
     */
    shouldUpdateTarget() {
        return (this.trainingStep - this.lastTargetUpdate) >= this.config.learning.targetUpdateFrequency;
    }

    /**
     * Checks if validation should occur
     */
    shouldValidate() {
        return this.currentEpisode % this.config.training.validationFrequency === 0 && 
               this.currentEpisode > 0;
    }

    /**
     * Checks if checkpoint should be saved
     */
    shouldSaveCheckpoint() {
        return this.currentEpisode % this.config.training.saveFrequency === 0 && 
               this.currentEpisode > 0;
    }

    /**
     * Checks if early stopping should occur
     */
    shouldStopEarly() {
        if (!this.config.earlyStopping.enabled) return false;
        
        return this.earlyStopping.shouldStop;
    }

    /**
     * Checks if progress should be logged
     */
    shouldLog() {
        return this.currentEpisode % this.config.monitoring.logFrequency === 0;
    }

    /**
     * Updates episode metrics
     */
    updateEpisodeMetrics(episodeResult, episodeStartTime) {
        const episodeTime = performance.now() - episodeStartTime;
        
        this.metrics.episode.rewards.push(episodeResult.totalReward);
        this.metrics.episode.lengths.push(episodeResult.stepCount);
        this.metrics.episode.qValues.push(episodeResult.averageQValue);
        this.metrics.episode.explorationRates.push(this.getCurrentEpsilon());
        
        this.metrics.performance.lastEpisodeTime = episodeTime;
        
        // Keep episode history bounded
        const maxHistory = this.config.monitoring.rewardHistorySize;
        if (this.metrics.episode.rewards.length > maxHistory) {
            this.metrics.episode.rewards.shift();
            this.metrics.episode.lengths.shift();
            this.metrics.episode.qValues.shift();
            this.metrics.episode.explorationRates.shift();
        }

        // Update early stopping
        this.updateEarlyStopping(episodeResult.totalReward);
    }

    /**
     * Updates early stopping logic
     */
    updateEarlyStopping(currentScore) {
        if (!this.config.earlyStopping.enabled) return;
        
        const config = this.config.earlyStopping;
        
        if (config.mode === "max" && currentScore > this.earlyStopping.bestScore + config.minDelta) {
            this.earlyStopping.bestScore = currentScore;
            this.earlyStopping.patienceCounter = 0;
        } else if (config.mode === "min" && currentScore < this.earlyStopping.bestScore - config.minDelta) {
            this.earlyStopping.bestScore = currentScore;
            this.earlyStopping.patienceCounter = 0;
        } else {
            this.earlyStopping.patienceCounter++;
        }
        
        if (this.earlyStopping.patienceCounter >= config.patience) {
            this.earlyStopping.shouldStop = true;
        }
    }

    /**
     * Updates training phase based on episode count
     */
    updateTrainingPhase() {
        const phases = this.config.phases;
        const episode = this.currentEpisode;
        
        let newPhase = this.currentPhase;
        
        if (episode >= phases.warmup.episodes + phases.exploration.episodes + phases.exploitation.episodes) {
            newPhase = "finetuning";
        } else if (episode >= phases.warmup.episodes + phases.exploration.episodes) {
            newPhase = "exploitation";
        } else if (episode >= phases.warmup.episodes) {
            newPhase = "exploration";
        } else {
            newPhase = "warmup";
        }
        
        if (newPhase !== this.currentPhase) {
            console.log(`🔄 Entering ${newPhase} phase at episode ${episode}`);
            this.currentPhase = newPhase;
            
            // Update configuration for new phase
            const phaseConfig = getPhaseConfig(newPhase, this.config);
            this.config = phaseConfig;
            
            // Update optimizer learning rate if needed
            if (this.optimizer && this.config.learning.learningRate !== this.optimizer.learningRate) {
                this.optimizer.learningRate = this.config.learning.learningRate;
            }
        }
    }

    /**
     * Validates performance with dedicated episodes
     */
    async validatePerformance() {
        console.log("🔍 Running validation...");
        
        const validationConfig = this.config.validation;
        const results = [];
        
        for (let i = 0; i < validationConfig.episodes; i++) {
            // Run episode with low exploration
            const oldEpsilon = this.config.exploration.epsilonStart;
            this.config.exploration.epsilonStart = validationConfig.explorationRate;
            
            const result = await this.runEpisode();
            results.push(result);
            
            // Restore exploration rate
            this.config.exploration.epsilonStart = oldEpsilon;
        }
        
        const averageReward = results.reduce((sum, r) => sum + r.totalReward, 0) / results.length;
        const successRate = results.filter(r => r.success).length / results.length;
        const averageLength = results.reduce((sum, r) => sum + r.stepCount, 0) / results.length;
        
        const validationResult = {
            averageReward,
            successRate,
            averageLength,
            episode: this.currentEpisode,
            timestamp: Date.now()
        };
        
        this.metrics.validation.scores.push(averageReward);
        this.metrics.validation.successRates.push(successRate);
        this.metrics.validation.lastValidation = validationResult;
        
        console.log(`📈 Validation results: Avg Reward: ${averageReward.toFixed(2)}, Success Rate: ${(successRate * 100).toFixed(1)}%, Avg Length: ${averageLength.toFixed(1)}`);
        
        return validationResult;
    }

    /**
     * Saves training checkpoint
     */
    async saveCheckpoint() {
        try {
            const checkpoint = {
                episode: this.currentEpisode,
                step: this.currentStep,
                trainingStep: this.trainingStep,
                metrics: this.metrics,
                config: this.config,
                timestamp: Date.now()
            };
            
            // In a real implementation, this would save to storage
            console.log(`💾 Checkpoint saved at episode ${this.currentEpisode}`);
            
            this.checkpoints.lastSave = this.currentEpisode;
            
            // Save best reward checkpoint
            const currentReward = this.getAverageReward();
            if (!this.checkpoints.bestRewardSave || currentReward > this.checkpoints.bestRewardSave.reward) {
                this.checkpoints.bestRewardSave = {
                    reward: currentReward,
                    episode: this.currentEpisode,
                    checkpoint
                };
                console.log(`🏆 New best reward checkpoint: ${currentReward.toFixed(2)}`);
            }
            
        } catch (error) {
            console.error("❌ Failed to save checkpoint:", error);
        }
    }

    /**
     * Logs training progress
     */
    logProgress() {
        const recentRewards = this.metrics.episode.rewards.slice(-10);
        const avgReward = recentRewards.reduce((sum, r) => sum + r, 0) / recentRewards.length;
        const avgLoss = this.metrics.training.lossHistory.slice(-10).reduce((sum, l) => sum + l, 0) / Math.min(10, this.metrics.training.lossHistory.length);
        const epsilon = this.getCurrentEpsilon();
        
        console.log(`📊 Episode ${this.currentEpisode}/${this.config.training.maxEpisodes} | Phase: ${this.currentPhase} | Avg Reward: ${avgReward.toFixed(2)} | Loss: ${avgLoss.toFixed(4)} | ε: ${epsilon.toFixed(3)} | Buffer: ${this.experienceBuffer.size()}`);
    }

    /**
     * Gets average reward over recent episodes
     */
    getAverageReward(episodes = 100) {
        const recentRewards = this.metrics.episode.rewards.slice(-episodes);
        return recentRewards.length > 0 ? 
            recentRewards.reduce((sum, r) => sum + r, 0) / recentRewards.length : 0;
    }

    /**
     * Pauses training
     */
    pause() {
        this.isPaused = true;
        console.log("⏸️ Training paused");
    }

    /**
     * Resumes training
     */
    resume() {
        this.isPaused = false;
        console.log("▶️ Training resumed");
    }

    /**
     * Stops training
     */
    stop() {
        this.isTraining = false;
        console.log("⏹️ Training stopped");
    }

    /**
     * Resets training metrics
     */
    resetMetrics() {
        this.metrics = {
            episode: {
                rewards: [],
                lengths: [],
                losses: [],
                explorationRates: [],
                qValues: []
            },
            training: {
                totalLoss: 0,
                lossHistory: [],
                gradientNorms: [],
                weightsStats: [],
                batchCount: 0,
                convergenceScore: 0
            },
            performance: {
                trainTime: 0,
                inferenceTime: 0,
                memoryUsage: [],
                fps: 0,
                lastEpisodeTime: 0
            },
            validation: {
                scores: [],
                successRates: [],
                lastValidation: null
            }
        };
    }

    /**
     * Finalizes training process
     */
    async finalizeTraining() {
        console.log("🏁 Finalizing training...");
        
        // Save final checkpoint
        await this.saveCheckpoint();
        
        // Final validation
        const finalValidation = await this.validatePerformance();
        
        // Generate training summary
        const summary = this.generateTrainingSummary();
        console.log("📋 Training Summary:", summary);
        
        // Clean up timers
        Object.values(this.timers).forEach(timer => {
            if (timer) clearInterval(timer);
        });
    }

    /**
     * Generates training summary
     */
    generateTrainingSummary() {
        const totalReward = this.metrics.episode.rewards.reduce((sum, r) => sum + r, 0);
        const avgReward = this.getAverageReward();
        const avgLoss = this.metrics.training.lossHistory.reduce((sum, l) => sum + l, 0) / 
                        Math.max(1, this.metrics.training.lossHistory.length);
        
        return {
            episodesCompleted: this.currentEpisode,
            totalSteps: this.currentStep,
            trainingSteps: this.trainingStep,
            totalReward,
            averageReward: avgReward,
            averageLoss: avgLoss,
            finalEpsilon: this.getCurrentEpsilon(),
            bufferSize: this.experienceBuffer.size(),
            bestReward: Math.max(...this.metrics.episode.rewards),
            convergenceAchieved: this.earlyStopping.shouldStop,
            trainingTime: this.metrics.performance.trainTime,
            phase: this.currentPhase
        };
    }

    /**
     * Gets current training status
     */
    getStatus() {
        return {
            isTraining: this.isTraining,
            isPaused: this.isPaused,
            currentEpisode: this.currentEpisode,
            currentStep: this.currentStep,
            trainingStep: this.trainingStep,
            phase: this.currentPhase,
            epsilon: this.getCurrentEpsilon(),
            averageReward: this.getAverageReward(),
            bufferSize: this.experienceBuffer.size(),
            metrics: { ...this.metrics }
        };
    }

    /**
     * Utility function for async delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Cleanup resources
     */
    destroy() {
        this.stop();
        
        // Dispose neural networks
        if (this.qNetwork) {
            this.qNetwork.dispose();
        }
        if (this.targetNetwork) {
            this.targetNetwork.dispose();
        }
        if (this.optimizer) {
            this.optimizer.dispose();
        }
        
        // Clear experience buffer
        if (this.experienceBuffer) {
            this.experienceBuffer.clear();
        }
        
        console.log("🧹 Training Manager destroyed");
    }
}