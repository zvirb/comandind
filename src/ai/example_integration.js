/**
 * Example Integration - How to use OllamaClient in the game
 * This shows basic integration patterns without modifying existing game code
 */

import { OllamaClient } from './OllamaClient.js';

/**
 * Example game AI integration using OllamaClient
 */
export class GameAIIntegration {
    constructor(gameConfig = {}) {
        // Initialize Ollama client with game-specific config
        this.ollama = new OllamaClient({
            requestTimeout: gameConfig.aiTimeout || 300, // Faster timeout for real-time game
            maxFailures: 2, // Open circuit breaker faster in game context
            testPrompt: "Tactical analysis ready"
        });
        
        this.isInitialized = false;
        this.lastAnalysis = null;
        this.analysisCache = new Map();
    }
    
    /**
     * Initialize AI system (call this during game startup)
     */
    async initialize() {
        console.log('🎮 Initializing Game AI Integration...');
        
        try {
            const connected = await this.ollama.testConnection();
            if (connected) {
                console.log('✅ AI system ready');
                this.isInitialized = true;
                
                // Test with game-specific prompt
                const testResult = await this.ollama.sendTestPrompt(
                    "System ready. Awaiting battlefield analysis requests."
                );
                
                if (testResult.success) {
                    console.log('✅ AI tactical analysis confirmed');
                }
            } else {
                console.log('⚠️ AI system unavailable, using fallback strategies');
                this.isInitialized = false;
            }
        } catch (error) {
            console.warn('⚠️ AI initialization failed:', error.message);
            this.isInitialized = false;
        }
        
        return this.isInitialized;
    }
    
    /**
     * Analyze game state and provide tactical recommendations
     * @param {Object} gameState - Current game state
     * @returns {Promise<Object>} Analysis result
     */
    async analyzeGameState(gameState) {
        // Check if AI is available
        if (!this.ollama.isAvailable()) {
            return this.getFallbackAnalysis(gameState);
        }
        
        // Create cache key for similar game states
        const stateKey = this.createStateKey(gameState);
        if (this.analysisCache.has(stateKey)) {
            console.log('🎯 Using cached analysis');
            return this.analysisCache.get(stateKey);
        }
        
        try {
            // Create tactical prompt
            const prompt = this.createTacticalPrompt(gameState);
            
            // Get AI analysis
            const result = await this.ollama.sendTestPrompt(prompt);
            
            if (result.success) {
                const analysis = this.parseAIResponse(result.response);
                
                // Cache successful analysis
                this.analysisCache.set(stateKey, analysis);
                this.lastAnalysis = analysis;
                
                console.log('🧠 AI tactical analysis completed');
                return analysis;
            } else {
                console.log('⚠️ AI analysis failed, using fallback');
                return this.getFallbackAnalysis(gameState);
            }
            
        } catch (error) {
            console.warn('❌ AI analysis error:', error.message);
            return this.getFallbackAnalysis(gameState);
        }
    }
    
    /**
     * Get streaming tactical advice (for real-time scenarios)
     * @param {Object} gameState - Current game state  
     * @param {Function} onChunk - Callback for each response chunk
     */
    async getStreamingAdvice(gameState, onChunk) {
        if (!this.ollama.isAvailable()) {
            onChunk("AI unavailable - using basic tactical protocols");
            return;
        }
        
        try {
            const prompt = this.createUrgentTacticalPrompt(gameState);
            const stream = this.ollama.generateStream(prompt);
            
            for await (const chunk of stream) {
                onChunk(chunk);
            }
            
        } catch (error) {
            onChunk(`Error: ${error.message}`);
        }
    }
    
    /**
     * Get AI system status for game UI
     */
    getAIStatus() {
        const status = this.ollama.getStatus();
        return {
            available: status.available,
            connected: status.connected,
            healthy: status.healthy,
            responseTime: status.metrics.averageResponseTime,
            circuitBreakerState: status.circuitBreaker.state,
            fallbackMode: !status.available
        };
    }
    
    /**
     * Reset AI system (for game restart scenarios)
     */
    reset() {
        this.ollama.resetCircuitBreaker();
        this.analysisCache.clear();
        this.lastAnalysis = null;
        console.log('🔄 AI system reset');
    }
    
    // Private helper methods
    
    createStateKey(gameState) {
        // Simple state hash for caching
        const key = `${gameState.playerUnits || 0}_${gameState.enemyUnits || 0}_${gameState.resources || 0}`;
        return key;
    }
    
    createTacticalPrompt(gameState) {
        return `Tactical Analysis Request:
Units: ${gameState.playerUnits || 0} friendly, ${gameState.enemyUnits || 0} enemy
Resources: ${gameState.resources || 0} credits
Map Control: ${gameState.mapControl || 'unknown'}
Immediate Threats: ${gameState.threats || 'none detected'}

Provide concise tactical recommendation (max 50 words).`;
    }
    
    createUrgentTacticalPrompt(gameState) {
        return `URGENT: Enemy contact!
Friendly: ${gameState.playerUnits || 0} units
Enemy: ${gameState.enemyUnits || 0} units  
Status: ${gameState.combatStatus || 'engaged'}

Immediate tactical advice:`;
    }
    
    parseAIResponse(response) {
        // Basic response parsing
        return {
            type: 'ai_analysis',
            recommendation: response.trim(),
            confidence: 0.8,
            timestamp: Date.now(),
            source: 'ollama'
        };
    }
    
    getFallbackAnalysis(gameState) {
        // Simple rule-based fallback
        const analysis = {
            type: 'fallback_analysis',
            recommendation: '',
            confidence: 0.6,
            timestamp: Date.now(),
            source: 'fallback'
        };
        
        // Basic tactical rules
        if (gameState.enemyUnits > gameState.playerUnits) {
            analysis.recommendation = "Enemy has numerical advantage - consider defensive positioning";
        } else if (gameState.resources < 500) {
            analysis.recommendation = "Low resources - prioritize economy and harvesting";
        } else if (gameState.playerUnits > gameState.enemyUnits) {
            analysis.recommendation = "Numerical advantage confirmed - consider offensive action";
        } else {
            analysis.recommendation = "Maintain current strategy - situation stable";
        }
        
        return analysis;
    }
}

/**
 * Example usage patterns for the game
 */
export class GameAIExamples {
    static async demoBasicUsage() {
        console.log('🎮 Demo: Basic AI Integration');
        
        const ai = new GameAIIntegration({ aiTimeout: 500 });
        await ai.initialize();
        
        // Example game state
        const gameState = {
            playerUnits: 8,
            enemyUnits: 12,
            resources: 750,
            mapControl: 'contested',
            threats: 'enemy tank formation approaching'
        };
        
        // Get tactical analysis
        const analysis = await ai.analyzeGameState(gameState);
        console.log('📊 Analysis:', analysis);
        
        // Check AI status
        const status = ai.getAIStatus();
        console.log('🔍 AI Status:', status);
    }
    
    static async demoStreamingAdvice() {
        console.log('🌊 Demo: Streaming Tactical Advice');
        
        const ai = new GameAIIntegration();
        await ai.initialize();
        
        const urgentState = {
            playerUnits: 5,
            enemyUnits: 8,
            combatStatus: 'under attack',
            threats: 'multiple enemy units'
        };
        
        await ai.getStreamingAdvice(urgentState, (chunk) => {
            console.log('📡 AI Advice:', chunk);
        });
    }
    
    static async demoFallbackBehavior() {
        console.log('🔄 Demo: Fallback Behavior');
        
        // Create AI with very aggressive circuit breaker for demo
        const ai = new GameAIIntegration({ maxFailures: 1 });
        
        const gameState = {
            playerUnits: 3,
            enemyUnits: 1,
            resources: 1200
        };
        
        // This will use fallback since Ollama isn't available
        const analysis = await ai.analyzeGameState(gameState);
        console.log('📊 Fallback Analysis:', analysis);
    }
}

export default GameAIIntegration;