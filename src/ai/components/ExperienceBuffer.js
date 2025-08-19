/**
 * Experience Buffer for Deep Q-Learning
 * Implements experience replay memory for training neural networks
 * Stores transitions (state, action, reward, nextState, done) for batch learning
 */
export class ExperienceBuffer {
    constructor(options = {}) {
        // Buffer configuration
        this.maxSize = options.maxSize || 1000; // Maximum number of experiences to store
        this.batchSize = options.batchSize || 32; // Default batch size for sampling
        
        // Storage arrays for experience tuples
        this.states = [];
        this.actions = [];
        this.rewards = [];
        this.nextStates = [];
        this.doneFlags = [];
        
        // Buffer management
        this.currentIndex = 0;
        this.isFull = false;
        this.totalExperiences = 0;
        
        // Sampling options
        this.prioritizedReplay = options.prioritizedReplay || false;
        this.priorities = []; // For prioritized experience replay
        this.alpha = options.alpha || 0.6; // Prioritization exponent
        this.beta = options.beta || 0.4; // Importance sampling exponent
        this.betaIncrement = options.betaIncrement || 0.001;
        this.maxPriority = 1.0;
        
        // Performance tracking
        this.addCount = 0;
        this.sampleCount = 0;
    }
    
    /**
     * Adds a new experience tuple to the buffer
     * @param {Float32Array} state - Current state vector (36D)
     * @param {number} action - Action ID (0-15)
     * @param {number} reward - Reward received
     * @param {Float32Array} nextState - Next state vector (36D)
     * @param {boolean} done - Whether episode ended
     * @param {number} priority - Priority for prioritized replay (optional)
     */
    add(state, action, reward, nextState, done, priority = null) {
        // Validate inputs
        if (!this.isValidState(state) || !this.isValidState(nextState)) {
            console.warn('ExperienceBuffer: Invalid state dimensions');
            return false;
        }
        
        if (!this.isValidAction(action)) {
            console.warn('ExperienceBuffer: Invalid action ID');
            return false;
        }
        
        // Store experience at current index
        this.states[this.currentIndex] = new Float32Array(state);
        this.actions[this.currentIndex] = action;
        this.rewards[this.currentIndex] = reward;
        this.nextStates[this.currentIndex] = new Float32Array(nextState);
        this.doneFlags[this.currentIndex] = done;
        
        // Handle prioritized replay
        if (this.prioritizedReplay) {
            const priorityValue = priority !== null ? priority : this.maxPriority;
            this.priorities[this.currentIndex] = Math.pow(priorityValue, this.alpha);
        }
        
        // Update buffer state
        this.currentIndex = (this.currentIndex + 1) % this.maxSize;
        this.addCount++;
        this.totalExperiences = Math.min(this.totalExperiences + 1, this.maxSize);
        
        if (!this.isFull && this.currentIndex === 0) {
            this.isFull = true;
        }
        
        return true;
    }
    
    /**
     * Samples a batch of experiences from the buffer
     * @param {number} batchSize - Number of experiences to sample
     * @returns {Object} Batch of experiences
     */
    sample(batchSize = null) {
        const actualBatchSize = batchSize || this.batchSize;
        
        if (this.size() < actualBatchSize) {
            console.warn(`ExperienceBuffer: Not enough experiences (${this.size()}) for batch size ${actualBatchSize}`);
            return null;
        }
        
        let indices;
        let weights = null;
        
        if (this.prioritizedReplay) {
            const samplingResult = this.prioritizedSample(actualBatchSize);
            indices = samplingResult.indices;
            weights = samplingResult.weights;
        } else {
            indices = this.uniformSample(actualBatchSize);
        }
        
        // Extract batch data
        const batch = {
            states: indices.map(i => new Float32Array(this.states[i])),
            actions: indices.map(i => this.actions[i]),
            rewards: indices.map(i => this.rewards[i]),
            nextStates: indices.map(i => new Float32Array(this.nextStates[i])),
            doneFlags: indices.map(i => this.doneFlags[i]),
            indices: indices,
            weights: weights
        };
        
        this.sampleCount++;
        return batch;
    }
    
    /**
     * Uniform random sampling
     */
    uniformSample(batchSize) {
        const indices = [];
        const availableSize = this.size();
        
        for (let i = 0; i < batchSize; i++) {
            const randomIndex = Math.floor(Math.random() * availableSize);
            indices.push(randomIndex);
        }
        
        return indices;
    }
    
    /**
     * Prioritized sampling based on priorities
     */
    prioritizedSample(batchSize) {
        const availableSize = this.size();
        const totalPriority = this.priorities.slice(0, availableSize).reduce((sum, p) => sum + p, 0);
        
        const indices = [];
        const weights = [];
        
        // Calculate importance sampling weights
        const maxWeight = Math.pow(availableSize * Math.min(...this.priorities.slice(0, availableSize)), -this.beta);
        
        for (let i = 0; i < batchSize; i++) {
            const randomValue = Math.random() * totalPriority;
            let cumulativePriority = 0;
            let selectedIndex = 0;
            
            // Find index based on priority distribution
            for (let j = 0; j < availableSize; j++) {
                cumulativePriority += this.priorities[j];
                if (cumulativePriority >= randomValue) {
                    selectedIndex = j;
                    break;
                }
            }
            
            indices.push(selectedIndex);
            
            // Calculate importance sampling weight
            const probability = this.priorities[selectedIndex] / totalPriority;
            const weight = Math.pow(availableSize * probability, -this.beta) / maxWeight;
            weights.push(weight);
        }
        
        return { indices, weights };
    }
    
    /**
     * Updates priorities for prioritized replay
     * @param {Array} indices - Indices of experiences to update
     * @param {Array} priorities - New priority values
     */
    updatePriorities(indices, priorities) {
        if (!this.prioritizedReplay) return;
        
        for (let i = 0; i < indices.length; i++) {
            if (indices[i] < this.size()) {
                this.priorities[indices[i]] = Math.pow(priorities[i], this.alpha);
                this.maxPriority = Math.max(this.maxPriority, priorities[i]);
            }
        }
    }
    
    /**
     * Gets a single random experience
     */
    sampleOne() {
        if (this.size() === 0) return null;
        
        const randomIndex = Math.floor(Math.random() * this.size());
        return {
            state: new Float32Array(this.states[randomIndex]),
            action: this.actions[randomIndex],
            reward: this.rewards[randomIndex],
            nextState: new Float32Array(this.nextStates[randomIndex]),
            done: this.doneFlags[randomIndex],
            index: randomIndex
        };
    }
    
    /**
     * Gets the most recent experience
     */
    getLatest() {
        if (this.size() === 0) return null;
        
        const latestIndex = this.currentIndex === 0 ? this.size() - 1 : this.currentIndex - 1;
        return {
            state: new Float32Array(this.states[latestIndex]),
            action: this.actions[latestIndex],
            reward: this.rewards[latestIndex],
            nextState: new Float32Array(this.nextStates[latestIndex]),
            done: this.doneFlags[latestIndex],
            index: latestIndex
        };
    }
    
    /**
     * Returns current number of stored experiences
     */
    size() {
        return this.totalExperiences;
    }
    
    /**
     * Checks if buffer is full
     */
    isFull() {
        return this.isFull;
    }
    
    /**
     * Checks if buffer has enough experiences for training
     */
    canSample(batchSize = null) {
        const requiredSize = batchSize || this.batchSize;
        return this.size() >= requiredSize;
    }
    
    /**
     * Clears all experiences from buffer
     */
    clear() {
        this.states = [];
        this.actions = [];
        this.rewards = [];
        this.nextStates = [];
        this.doneFlags = [];
        this.priorities = [];
        
        this.currentIndex = 0;
        this.isFull = false;
        this.totalExperiences = 0;
        this.addCount = 0;
        this.sampleCount = 0;
        this.maxPriority = 1.0;
    }
    
    /**
     * Gets buffer statistics
     */
    getStats() {
        const averageReward = this.size() > 0 ? 
            this.rewards.slice(0, this.size()).reduce((sum, r) => sum + r, 0) / this.size() : 0;
        
        return {
            size: this.size(),
            maxSize: this.maxSize,
            isFull: this.isFull,
            addCount: this.addCount,
            sampleCount: this.sampleCount,
            averageReward: averageReward,
            prioritizedReplay: this.prioritizedReplay,
            beta: this.beta
        };
    }
    
    /**
     * Updates beta for importance sampling annealing
     */
    updateBeta() {
        if (this.prioritizedReplay) {
            this.beta = Math.min(1.0, this.beta + this.betaIncrement);
        }
    }
    
    /**
     * Validates state vector dimensions
     */
    isValidState(state) {
        return state && state.length === 36;
    }
    
    /**
     * Validates action ID
     */
    isValidAction(action) {
        return typeof action === 'number' && action >= 0 && action <= 15;
    }
    
    /**
     * Exports buffer data for persistence
     */
    export() {
        return {
            states: this.states.slice(0, this.size()).map(state => Array.from(state)),
            actions: this.actions.slice(0, this.size()),
            rewards: this.rewards.slice(0, this.size()),
            nextStates: this.nextStates.slice(0, this.size()).map(state => Array.from(state)),
            doneFlags: this.doneFlags.slice(0, this.size()),
            priorities: this.prioritizedReplay ? this.priorities.slice(0, this.size()) : null,
            config: {
                maxSize: this.maxSize,
                batchSize: this.batchSize,
                prioritizedReplay: this.prioritizedReplay,
                alpha: this.alpha,
                beta: this.beta
            }
        };
    }
    
    /**
     * Imports buffer data from exported format
     */
    import(data) {
        this.clear();
        
        // Restore configuration
        if (data.config) {
            this.maxSize = data.config.maxSize || this.maxSize;
            this.batchSize = data.config.batchSize || this.batchSize;
            this.prioritizedReplay = data.config.prioritizedReplay || false;
            this.alpha = data.config.alpha || this.alpha;
            this.beta = data.config.beta || this.beta;
        }
        
        // Restore experiences
        const count = Math.min(data.states.length, this.maxSize);
        for (let i = 0; i < count; i++) {
            const priority = data.priorities ? data.priorities[i] : null;
            this.add(
                new Float32Array(data.states[i]),
                data.actions[i],
                data.rewards[i],
                new Float32Array(data.nextStates[i]),
                data.doneFlags[i],
                priority
            );
        }
    }
}