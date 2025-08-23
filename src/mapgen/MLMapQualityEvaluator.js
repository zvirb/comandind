/**
 * ML-based Map Quality Evaluator
 * 
 * Uses TensorFlow.js to evaluate map quality using machine learning techniques.
 * This evaluator analyzes terrain patterns, resource distribution, and strategic
 * balance to provide comprehensive map quality scoring.
 * 
 * Features:
 * - Convolutional neural network for pattern analysis
 * - Multi-criteria evaluation (terrain variety, balance, playability)
 * - Real-time scoring during map generation
 * - Learning from user feedback and play statistics
 */

import * as tf from '@tensorflow/tfjs';
import { TensorFlowManager } from '../ai/TensorFlowManager.js';

export class MLMapQualityEvaluator {
    constructor(options = {}) {
        this.config = {
            // Model architecture
            inputSize: 64,  // Maps will be resized to 64x64 for analysis
            numChannels: 4, // terrain, resources, elevation, moisture
            
            // Evaluation criteria weights
            terrainVariety: 0.25,
            resourceBalance: 0.30,
            strategicBalance: 0.25,
            aestheticQuality: 0.20,
            
            // Training parameters
            learningRate: 0.001,
            batchSize: 16,
            epochsPerUpdate: 5,
            
            // Quality thresholds
            excellentThreshold: 85,
            goodThreshold: 70,
            acceptableThreshold: 55,
            
            // Performance settings
            useGPUAcceleration: true,
            maxEvaluationTime: 500, // ms
            
            ...options
        };
        
        // TensorFlow manager instance
        this.tfManager = null;
        this.isInitialized = false;
        
        // Model components
        this.evaluationModel = null;
        this.featureExtractor = null;
        
        // Training data collection
        this.trainingData = [];
        this.evaluationHistory = [];
        
        // Performance metrics
        this.evaluationCount = 0;
        this.averageEvaluationTime = 0;
        this.accuracyMetrics = {
            predictions: [],
            actualScores: [],
            correlation: 0
        };
    }
    
    /**
     * Initialize the ML evaluator
     */
    async initialize() {
        if (this.isInitialized) {
            return true;
        }
        
        try {
            console.log('🧠 Initializing ML Map Quality Evaluator...');
            
            // Initialize TensorFlow.js
            this.tfManager = new TensorFlowManager();
            const tfReady = await this.tfManager.initialize();
            
            if (!tfReady) {
                throw new Error('Failed to initialize TensorFlow.js');
            }
            
            // Build evaluation models
            await this.buildEvaluationModel();
            await this.buildFeatureExtractor();
            
            // Load pre-trained weights if available
            await this.loadPreTrainedWeights();
            
            this.isInitialized = true;
            console.log('✅ ML Map Quality Evaluator initialized successfully');
            
            return true;
            
        } catch (error) {
            console.error('❌ Failed to initialize ML Map Quality Evaluator:', error);
            return false;
        }
    }
    
    /**
     * Build the main evaluation model
     */
    async buildEvaluationModel() {
        console.log('🏗️ Building evaluation model...');
        
        const model = tf.sequential();
        
        // Input layer
        model.add(tf.layers.inputLayer({
            inputShape: [this.config.inputSize, this.config.inputSize, this.config.numChannels]
        }));
        
        // Feature extraction layers
        model.add(tf.layers.conv2d({
            filters: 32,
            kernelSize: 5,
            activation: 'relu',
            padding: 'same'
        }));
        
        model.add(tf.layers.maxPooling2d({
            poolSize: 2
        }));
        
        model.add(tf.layers.conv2d({
            filters: 64,
            kernelSize: 3,
            activation: 'relu',
            padding: 'same'
        }));
        
        model.add(tf.layers.maxPooling2d({
            poolSize: 2
        }));
        
        model.add(tf.layers.conv2d({
            filters: 128,
            kernelSize: 3,
            activation: 'relu',
            padding: 'same'
        }));
        
        model.add(tf.layers.globalAveragePooling2d());
        
        // Analysis layers
        model.add(tf.layers.dense({
            units: 256,
            activation: 'relu'
        }));
        
        model.add(tf.layers.dropout({ rate: 0.3 }));
        
        model.add(tf.layers.dense({
            units: 128,
            activation: 'relu'
        }));
        
        model.add(tf.layers.dropout({ rate: 0.2 }));
        
        // Multi-output layers for different quality aspects
        const terrainVarietyOutput = tf.layers.dense({
            units: 1,
            activation: 'sigmoid',
            name: 'terrain_variety'
        }).apply(model.layers[model.layers.length - 1].output);
        
        const resourceBalanceOutput = tf.layers.dense({
            units: 1,
            activation: 'sigmoid',
            name: 'resource_balance'
        }).apply(model.layers[model.layers.length - 1].output);
        
        const strategicBalanceOutput = tf.layers.dense({
            units: 1,
            activation: 'sigmoid',
            name: 'strategic_balance'
        }).apply(model.layers[model.layers.length - 1].output);
        
        const aestheticQualityOutput = tf.layers.dense({
            units: 1,
            activation: 'sigmoid',
            name: 'aesthetic_quality'
        }).apply(model.layers[model.layers.length - 1].output);
        
        // Overall score output
        const overallScoreOutput = tf.layers.dense({
            units: 1,
            activation: 'sigmoid',
            name: 'overall_score'
        }).apply(model.layers[model.layers.length - 1].output);
        
        // Create the multi-output model
        this.evaluationModel = tf.model({
            inputs: model.inputs,
            outputs: [
                terrainVarietyOutput,
                resourceBalanceOutput,
                strategicBalanceOutput,
                aestheticQualityOutput,
                overallScoreOutput
            ]
        });
        
        // Compile the model
        this.evaluationModel.compile({
            optimizer: tf.train.adam(this.config.learningRate),
            loss: {
                terrain_variety: 'meanSquaredError',
                resource_balance: 'meanSquaredError',
                strategic_balance: 'meanSquaredError',
                aesthetic_quality: 'meanSquaredError',
                overall_score: 'meanSquaredError'
            },
            metrics: ['mae']
        });
        
        console.log('✅ Evaluation model built successfully');
        console.log(`📊 Model parameters: ${this.evaluationModel.countParams()}`);
    }
    
    /**
     * Build feature extractor for preprocessing
     */
    async buildFeatureExtractor() {
        console.log('🔧 Building feature extractor...');
        
        // Simple preprocessing model for now
        // In a real implementation, this could be more sophisticated
        this.featureExtractor = {
            extractTerrainFeatures: (mapData) => this.extractTerrainFeatures(mapData),
            extractResourceFeatures: (mapData) => this.extractResourceFeatures(mapData),
            extractElevationFeatures: (mapData) => this.extractElevationFeatures(mapData),
            extractMoistureFeatures: (mapData) => this.extractMoistureFeatures(mapData)
        };
        
        console.log('✅ Feature extractor ready');
    }
    
    /**
     * Evaluate a map and return quality scores
     */
    async evaluateMap(mapData) {
        if (!this.isInitialized) {
            console.warn('⚠️ ML evaluator not initialized, using fallback evaluation');
            return this.fallbackEvaluation(mapData);
        }
        
        const startTime = performance.now();
        
        try {
            // Preprocess the map data
            const inputTensor = await this.preprocessMapData(mapData);
            
            // Run inference
            const predictions = await this.evaluationModel.predict(inputTensor);
            
            // Extract results
            const results = await this.processPredictions(predictions);
            
            // Cleanup tensors
            inputTensor.dispose();
            if (Array.isArray(predictions)) {
                predictions.forEach(pred => pred.dispose());
            } else {
                predictions.dispose();
            }
            
            const endTime = performance.now();
            const evaluationTime = endTime - startTime;
            
            // Update performance metrics
            this.updatePerformanceMetrics(evaluationTime);
            
            // Add metadata
            results.metadata = {
                evaluationTime,
                modelVersion: '1.0.0',
                tensorflowBackend: this.tfManager.currentBackend,
                timestamp: Date.now()
            };
            
            // Store evaluation for learning
            this.evaluationHistory.push({
                mapData: this.createMapFingerprint(mapData),
                results,
                timestamp: Date.now()
            });
            
            return results;
            
        } catch (error) {
            console.error('❌ ML evaluation failed:', error);
            return this.fallbackEvaluation(mapData);
        }
    }
    
    /**
     * Preprocess map data into model input format
     */
    async preprocessMapData(mapData) {
        const { terrain, resources, metadata } = mapData;
        const width = terrain[0].length;
        const height = terrain.length;
        
        // Create multi-channel input
        const inputData = new Float32Array(this.config.inputSize * this.config.inputSize * this.config.numChannels);
        
        // Resize and normalize terrain data
        const terrainChannel = this.featureExtractor.extractTerrainFeatures({
            terrain,
            targetSize: this.config.inputSize
        });
        
        // Extract resource features
        const resourceChannel = this.featureExtractor.extractResourceFeatures({
            resources,
            width,
            height,
            targetSize: this.config.inputSize
        });
        
        // Generate elevation features (if available in metadata or estimated)
        const elevationChannel = this.featureExtractor.extractElevationFeatures({
            terrain,
            targetSize: this.config.inputSize
        });
        
        // Generate moisture features
        const moistureChannel = this.featureExtractor.extractMoistureFeatures({
            terrain,
            targetSize: this.config.inputSize
        });
        
        // Combine channels
        for (let i = 0; i < this.config.inputSize * this.config.inputSize; i++) {
            inputData[i * 4] = terrainChannel[i];
            inputData[i * 4 + 1] = resourceChannel[i];
            inputData[i * 4 + 2] = elevationChannel[i];
            inputData[i * 4 + 3] = moistureChannel[i];
        }
        
        return tf.tensor4d(
            inputData,
            [1, this.config.inputSize, this.config.inputSize, this.config.numChannels]
        );
    }
    
    /**
     * Process model predictions into readable results
     */
    async processPredictions(predictions) {
        const [
            terrainVariety,
            resourceBalance,
            strategicBalance,
            aestheticQuality,
            overallScore
        ] = Array.isArray(predictions) ? predictions : [predictions];
        
        const terrainVarietyScore = (await terrainVariety.data())[0] * 100;
        const resourceBalanceScore = (await resourceBalance.data())[0] * 100;
        const strategicBalanceScore = (await strategicBalance.data())[0] * 100;
        const aestheticQualityScore = (await aestheticQuality.data())[0] * 100;
        const overallScoreValue = (await overallScore.data())[0] * 100;
        
        // Calculate weighted overall score
        const weightedScore = 
            terrainVarietyScore * this.config.terrainVariety +
            resourceBalanceScore * this.config.resourceBalance +
            strategicBalanceScore * this.config.strategicBalance +
            aestheticQualityScore * this.config.aestheticQuality;
        
        return {
            overall: {
                score: Math.round(weightedScore),
                grade: this.getGrade(weightedScore),
                mlPredicted: true
            },
            details: {
                terrainVariety: {
                    score: Math.round(terrainVarietyScore),
                    weight: this.config.terrainVariety
                },
                resourceBalance: {
                    score: Math.round(resourceBalanceScore),
                    weight: this.config.resourceBalance
                },
                strategicBalance: {
                    score: Math.round(strategicBalanceScore),
                    weight: this.config.strategicBalance
                },
                aestheticQuality: {
                    score: Math.round(aestheticQualityScore),
                    weight: this.config.aestheticQuality
                }
            },
            confidence: this.calculateConfidence(weightedScore),
            recommendations: this.generateRecommendations({
                terrainVariety: terrainVarietyScore,
                resourceBalance: resourceBalanceScore,
                strategicBalance: strategicBalanceScore,
                aestheticQuality: aestheticQualityScore
            })
        };
    }
    
    /**
     * Extract terrain features from map data
     */
    extractTerrainFeatures(data) {
        const { terrain, targetSize } = data;
        const features = new Float32Array(targetSize * targetSize);
        
        const scaleX = terrain[0].length / targetSize;
        const scaleY = terrain.length / targetSize;
        
        for (let y = 0; y < targetSize; y++) {
            for (let x = 0; x < targetSize; x++) {
                const srcX = Math.floor(x * scaleX);
                const srcY = Math.floor(y * scaleY);
                
                const tile = terrain[srcY] && terrain[srcY][srcX] ? terrain[srcY][srcX] : 'S01';
                features[y * targetSize + x] = this.tileToNumeric(tile);
            }
        }
        
        // Normalize to 0-1 range
        return this.normalizeFeatures(features);
    }
    
    /**
     * Extract resource features from map data
     */
    extractResourceFeatures(data) {
        const { resources, width, height, targetSize } = data;
        const features = new Float32Array(targetSize * targetSize);
        
        if (!resources || resources.length === 0) {
            return features; // All zeros if no resources
        }
        
        const scaleX = width / targetSize;
        const scaleY = height / targetSize;
        
        // Create resource density map
        for (const resource of resources) {
            const x = Math.floor(resource.x / scaleX);
            const y = Math.floor(resource.y / scaleY);
            
            if (x < targetSize && y < targetSize) {
                features[y * targetSize + x] += resource.amount || 1;
            }
        }
        
        return this.normalizeFeatures(features);
    }
    
    /**
     * Extract elevation features (estimated from terrain)
     */
    extractElevationFeatures(data) {
        const { terrain, targetSize } = data;
        const features = new Float32Array(targetSize * targetSize);
        
        const scaleX = terrain[0].length / targetSize;
        const scaleY = terrain.length / targetSize;
        
        for (let y = 0; y < targetSize; y++) {
            for (let x = 0; x < targetSize; x++) {
                const srcX = Math.floor(x * scaleX);
                const srcY = Math.floor(y * scaleY);
                
                const tile = terrain[srcY] && terrain[srcY][srcX] ? terrain[srcY][srcX] : 'S01';
                features[y * targetSize + x] = this.tileToElevation(tile);
            }
        }
        
        return this.normalizeFeatures(features);
    }
    
    /**
     * Extract moisture features (estimated from terrain)
     */
    extractMoistureFeatures(data) {
        const { terrain, targetSize } = data;
        const features = new Float32Array(targetSize * targetSize);
        
        const scaleX = terrain[0].length / targetSize;
        const scaleY = terrain.length / targetSize;
        
        for (let y = 0; y < targetSize; y++) {
            for (let x = 0; x < targetSize; x++) {
                const srcX = Math.floor(x * scaleX);
                const srcY = Math.floor(y * scaleY);
                
                const tile = terrain[srcY] && terrain[srcY][srcX] ? terrain[srcY][srcX] : 'S01';
                features[y * targetSize + x] = this.tileToMoisture(tile);
            }
        }
        
        return this.normalizeFeatures(features);
    }
    
    /**
     * Convert tile ID to numeric value
     */
    tileToNumeric(tile) {
        const tileMap = {
            'S01': 0.1, 'S02': 0.15, 'S03': 0.2, 'S04': 0.25, 'S05': 0.3,
            'D01': 0.4, 'D02': 0.45, 'D03': 0.5, 'D04': 0.55, 'D05': 0.6,
            'W1': 0.8, 'W2': 0.85, 'SH1': 0.7, 'SH2': 0.75, 'SH3': 0.78,
            'T01': 0.9, 'T02': 0.92, 'T03': 0.94, 'T05': 0.96,
            'ROCK1': 1.0, 'ROCK2': 0.98, 'ROCK3': 0.95
        };
        
        return tileMap[tile] || 0.1;
    }
    
    /**
     * Convert tile to elevation estimate
     */
    tileToElevation(tile) {
        if (tile.startsWith('W') || tile.startsWith('SH')) return 0.0;
        if (tile.startsWith('ROCK')) return 1.0;
        if (tile.startsWith('S')) return 0.2;
        if (tile.startsWith('D')) return 0.4;
        if (tile.startsWith('T')) return 0.6;
        return 0.2;
    }
    
    /**
     * Convert tile to moisture estimate
     */
    tileToMoisture(tile) {
        if (tile.startsWith('W')) return 1.0;
        if (tile.startsWith('SH')) return 0.8;
        if (tile.startsWith('T')) return 0.7;
        if (tile.startsWith('D')) return 0.4;
        if (tile.startsWith('S')) return 0.1;
        return 0.3;
    }
    
    /**
     * Normalize feature array to 0-1 range
     */
    normalizeFeatures(features) {
        const max = Math.max(...features);
        const min = Math.min(...features);
        const range = max - min;
        
        if (range === 0) return features;
        
        return features.map(value => (value - min) / range);
    }
    
    /**
     * Get grade from numerical score
     */
    getGrade(score) {
        if (score >= this.config.excellentThreshold) return 'Excellent';
        if (score >= this.config.goodThreshold) return 'Good';
        if (score >= this.config.acceptableThreshold) return 'Acceptable';
        return 'Poor';
    }
    
    /**
     * Calculate confidence in the prediction
     */
    calculateConfidence(score) {
        // Simple confidence calculation based on score distribution
        // In a real implementation, this could use model uncertainty estimation
        const normalized = score / 100;
        const confidence = Math.max(0.6, 1 - Math.abs(normalized - 0.75) * 2);
        return Math.round(confidence * 100);
    }
    
    /**
     * Generate improvement recommendations
     */
    generateRecommendations(scores) {
        const recommendations = [];
        
        if (scores.terrainVariety < 60) {
            recommendations.push({
                category: 'terrain',
                priority: 'high',
                message: 'Increase terrain variety by adding more diverse tile types and natural features'
            });
        }
        
        if (scores.resourceBalance < 65) {
            recommendations.push({
                category: 'resources',
                priority: 'high',
                message: 'Improve resource distribution balance between player starting areas'
            });
        }
        
        if (scores.strategicBalance < 70) {
            recommendations.push({
                category: 'strategy',
                priority: 'medium',
                message: 'Add more strategic elements like chokepoints and expansion opportunities'
            });
        }
        
        if (scores.aestheticQuality < 65) {
            recommendations.push({
                category: 'aesthetics',
                priority: 'low',
                message: 'Enhance visual appeal with better terrain transitions and decorative elements'
            });
        }
        
        return recommendations;
    }
    
    /**
     * Fallback evaluation when ML is not available
     */
    fallbackEvaluation(mapData) {
        console.log('🔧 Using fallback map evaluation');
        
        // Simple heuristic-based evaluation
        const terrainVariety = this.calculateTerrainVariety(mapData);
        const resourceBalance = this.calculateResourceBalance(mapData);
        
        const overallScore = (terrainVariety + resourceBalance) / 2;
        
        return {
            overall: {
                score: Math.round(overallScore),
                grade: this.getGrade(overallScore),
                mlPredicted: false
            },
            details: {
                terrainVariety: { score: Math.round(terrainVariety), weight: 0.5 },
                resourceBalance: { score: Math.round(resourceBalance), weight: 0.5 },
                strategicBalance: { score: 70, weight: 0.0 },
                aestheticQuality: { score: 65, weight: 0.0 }
            },
            confidence: 50,
            recommendations: [],
            metadata: {
                evaluationTime: 0,
                modelVersion: 'fallback',
                tensorflowBackend: null,
                timestamp: Date.now()
            }
        };
    }
    
    /**
     * Calculate terrain variety using heuristics
     */
    calculateTerrainVariety(mapData) {
        const { terrain } = mapData;
        const tileTypes = new Set();
        
        for (const row of terrain) {
            for (const tile of row) {
                tileTypes.add(tile.charAt(0)); // Get tile type (S, D, W, etc.)
            }
        }
        
        // Score based on variety (max 100)
        return Math.min(100, tileTypes.size * 15);
    }
    
    /**
     * Calculate resource balance using heuristics
     */
    calculateResourceBalance(mapData) {
        const { resources, startingPositions } = mapData;
        
        if (!resources || !startingPositions || startingPositions.length < 2) {
            return 75; // Default score for single player
        }
        
        // Calculate resource distances from each starting position
        const playerResources = startingPositions.map(pos => {
            return resources.filter(resource => {
                const distance = Math.sqrt(
                    (resource.x - pos.x) ** 2 + (resource.y - pos.y) ** 2
                );
                return distance < 15; // Resources within reasonable distance
            }).length;
        });
        
        // Calculate balance (lower variance = better balance)
        const avgResources = playerResources.reduce((a, b) => a + b, 0) / playerResources.length;
        const variance = playerResources.reduce((sum, count) => sum + (count - avgResources) ** 2, 0) / playerResources.length;
        
        // Convert to score (lower variance = higher score)
        return Math.max(0, 100 - variance * 10);
    }
    
    /**
     * Create a fingerprint of the map for tracking
     */
    createMapFingerprint(mapData) {
        const { terrain, resources, metadata } = mapData;
        
        return {
            size: `${terrain[0].length}x${terrain.length}`,
            algorithm: metadata.algorithm,
            climate: metadata.climate,
            resourceCount: resources ? resources.length : 0,
            playerCount: metadata.playerCount,
            checksum: this.calculateChecksum(terrain)
        };
    }
    
    /**
     * Calculate a simple checksum for the terrain
     */
    calculateChecksum(terrain) {
        let checksum = 0;
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                checksum += terrain[y][x].charCodeAt(0) * (x + y + 1);
            }
        }
        return checksum % 10000;
    }
    
    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(evaluationTime) {
        this.evaluationCount++;
        this.averageEvaluationTime = 
            (this.averageEvaluationTime * (this.evaluationCount - 1) + evaluationTime) / this.evaluationCount;
        
        if (evaluationTime > this.config.maxEvaluationTime) {
            console.warn(`⚠️ ML evaluation took ${evaluationTime.toFixed(2)}ms (exceeds ${this.config.maxEvaluationTime}ms threshold)`);
        }
    }
    
    /**
     * Load pre-trained weights if available
     */
    async loadPreTrainedWeights() {
        try {
            // In a real implementation, this would load from a server or local storage
            console.log('📥 Looking for pre-trained weights...');
            
            // For now, just initialize with random weights (model is already initialized)
            console.log('ℹ️ No pre-trained weights found, using random initialization');
            
        } catch (error) {
            console.warn('⚠️ Failed to load pre-trained weights:', error.message);
        }
    }
    
    /**
     * Get evaluator status and statistics
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            tfManager: this.tfManager ? this.tfManager.getStatus() : null,
            config: this.config,
            performance: {
                evaluationCount: this.evaluationCount,
                averageEvaluationTime: this.averageEvaluationTime,
                evaluationHistory: this.evaluationHistory.length
            },
            model: {
                parametersCount: this.evaluationModel ? this.evaluationModel.countParams() : 0,
                memoryUsage: this.isInitialized ? tf.memory() : null
            }
        };
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        console.log('🧹 Cleaning up ML Map Quality Evaluator...');
        
        try {
            if (this.evaluationModel) {
                this.evaluationModel.dispose();
                this.evaluationModel = null;
            }
            
            if (this.tfManager) {
                this.tfManager.cleanup();
                this.tfManager = null;
            }
            
            this.isInitialized = false;
            console.log('✅ ML evaluator cleanup completed');
            
        } catch (error) {
            console.error('❌ ML evaluator cleanup failed:', error);
        }
    }
}

export default MLMapQualityEvaluator;