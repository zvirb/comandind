/**
 * Ollama Strategic Advisor - AI-powered strategic analysis for RTS gameplay
 * Provides battlefield analysis, tactical recommendations, and natural language command interpretation
 * Integrates with local Ollama instance for privacy-first AI assistance
 */

import { EventEmitter } from 'events';

export class OllamaStrategicAdvisor extends EventEmitter {
    constructor(options = {}) {
        super();
        
        // Configuration
        this.config = {
            // Ollama connection settings
            host: options.host || 'http://127.0.0.1:11434',
            model: options.model || 'llama3.1:8b',
            fallbackModel: options.fallbackModel || 'llama3.2:3b',
            
            // Performance optimization
            maxResponseTime: options.maxResponseTime || 500, // ms
            streamEnabled: options.streamEnabled !== false,
            contextWindowSize: options.contextWindowSize || 4096,
            
            // Strategic analysis settings
            analysisInterval: options.analysisInterval || 10000, // ms
            priorityThreshold: options.priorityThreshold || 0.7,
            confidenceThreshold: options.confidenceThreshold || 0.6,
            
            // Privacy and fallback settings
            offlineMode: options.offlineMode || false,
            enableFallback: options.enableFallback !== false,
            retryAttempts: options.retryAttempts || 3,
            
            // Context management
            maxGameStateTokens: options.maxGameStateTokens || 2000,
            compressionEnabled: options.compressionEnabled !== false
        };
        
        // Connection state
        this.connected = false;
        this.healthy = false;
        this.lastHealthCheck = 0;
        this.healthCheckInterval = 30000; // 30 seconds
        
        // Request management
        this.activeRequests = new Map();
        this.requestQueue = [];
        this.circuitBreaker = {
            state: 'closed', // closed, open, half-open
            failures: 0,
            maxFailures: 5,
            timeout: 60000, // 1 minute
            lastFailureTime: 0
        };
        
        // Context management
        this.gameStateHistory = [];
        this.maxHistoryLength = 10;
        this.compressionCache = new Map();
        
        // Performance tracking
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            averageResponseTime: 0,
            cachehits: 0
        };
        
        // Prompt templates
        this.promptTemplates = this.initializePromptTemplates();
        
        // Command mapping for natural language
        this.commandMapping = this.initializeCommandMapping();
        
        // Fallback system
        this.fallbackStrategies = this.initializeFallbackStrategies();
        
        // Initialize connection
        this.initialize();
    }
    
    /**
     * Initialize the Ollama connection and health monitoring
     */
    async initialize() {
        console.log('🤖 Initializing Ollama Strategic Advisor...');
        
        try {
            // Test initial connection
            await this.testConnection();
            
            // Start health monitoring
            this.startHealthMonitoring();
            
            // Pre-warm the model if needed
            if (this.config.streamEnabled) {
                await this.warmupModel();
            }
            
            console.log('✅ Ollama Strategic Advisor initialized successfully');
            this.emit('initialized');
            
        } catch (error) {
            console.warn('⚠️ Ollama initialization failed, using fallback mode:', error.message);
            this.config.offlineMode = true;
            this.emit('fallback-activated', 'initialization-failed');
        }
    }
    
    /**
     * Test connection to Ollama service
     */
    async testConnection() {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        try {
            const response = await fetch(`${this.config.host}/api/tags`, {
                method: 'GET',
                signal: controller.signal,
                headers: { 'Content-Type': 'application/json' }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.connected = true;
            this.healthy = true;
            this.lastHealthCheck = Date.now();
            
            // Verify our preferred model is available
            const availableModels = data.models || [];
            const hasPreferredModel = availableModels.some(m => m.name === this.config.model);
            const hasFallbackModel = availableModels.some(m => m.name === this.config.fallbackModel);
            
            if (!hasPreferredModel && !hasFallbackModel) {
                throw new Error(`Neither preferred model (${this.config.model}) nor fallback model (${this.config.fallbackModel}) are available`);
            }
            
            if (!hasPreferredModel && hasFallbackModel) {
                console.warn(`⚠️ Preferred model ${this.config.model} not available, using fallback ${this.config.fallbackModel}`);
                this.config.model = this.config.fallbackModel;
            }
            
            console.log(`✅ Connected to Ollama at ${this.config.host}, using model: ${this.config.model}`);
            return true;
            
        } catch (error) {
            clearTimeout(timeoutId);
            this.connected = false;
            this.healthy = false;
            throw error;
        }
    }
    
    /**
     * Start periodic health monitoring
     */
    startHealthMonitoring() {
        setInterval(async () => {
            try {
                await this.testConnection();
                
                // Reset circuit breaker on successful health check
                if (this.circuitBreaker.state === 'open') {
                    console.log('🔄 Circuit breaker transitioning to half-open');
                    this.circuitBreaker.state = 'half-open';
                }
                
            } catch (error) {
                this.handleConnectionFailure(error);
            }
        }, this.healthCheckInterval);
    }
    
    /**
     * Handle connection failures and circuit breaker logic
     */
    handleConnectionFailure(error) {
        this.connected = false;
        this.healthy = false;
        this.circuitBreaker.failures++;
        this.circuitBreaker.lastFailureTime = Date.now();
        
        console.warn(`❌ Ollama connection failed (${this.circuitBreaker.failures}/${this.circuitBreaker.maxFailures}):`, error.message);
        
        if (this.circuitBreaker.failures >= this.circuitBreaker.maxFailures) {
            console.warn('⚡ Circuit breaker opened - switching to offline mode');
            this.circuitBreaker.state = 'open';
            this.config.offlineMode = true;
            this.emit('circuit-breaker-opened');
        }
        
        this.emit('connection-failed', error);
    }
    
    /**
     * Warm up the model with a simple request
     */
    async warmupModel() {
        try {
            const warmupPrompt = "Ready for strategic analysis.";
            await this.makeRequest({
                model: this.config.model,
                prompt: warmupPrompt,
                stream: false,
                options: {
                    num_predict: 10,
                    temperature: 0.1
                }
            });
            console.log('🔥 Model warmed up successfully');
        } catch (error) {
            console.warn('⚠️ Model warmup failed:', error.message);
        }
    }
    
    /**
     * Make a request to Ollama with circuit breaker and retry logic
     */
    async makeRequest(requestBody, retryCount = 0) {
        // Check circuit breaker
        if (this.circuitBreaker.state === 'open') {
            const timeSinceLastFailure = Date.now() - this.circuitBreaker.lastFailureTime;
            if (timeSinceLastFailure < this.circuitBreaker.timeout) {
                throw new Error('Circuit breaker is open');
            } else {
                console.log('🔄 Circuit breaker timeout expired, transitioning to half-open');
                this.circuitBreaker.state = 'half-open';
            }
        }
        
        const requestId = this.generateRequestId();
        const startTime = Date.now();
        
        try {
            this.activeRequests.set(requestId, { startTime, requestBody });
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                controller.abort();
            }, this.config.maxResponseTime);
            
            const response = await fetch(`${this.config.host}/api/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            let result;
            if (requestBody.stream) {
                result = await this.handleStreamResponse(response);
            } else {
                result = await response.json();
            }
            
            // Update metrics
            const responseTime = Date.now() - startTime;
            this.updateMetrics(true, responseTime);
            
            // Reset circuit breaker on success
            if (this.circuitBreaker.state === 'half-open') {
                console.log('✅ Circuit breaker reset to closed');
                this.circuitBreaker.state = 'closed';
                this.circuitBreaker.failures = 0;
            }
            
            return result;
            
        } catch (error) {
            this.updateMetrics(false, Date.now() - startTime);
            
            // Handle timeout specifically
            if (error.name === 'AbortError') {
                console.warn(`⏰ Request ${requestId} timed out after ${this.config.maxResponseTime}ms`);
                throw new Error('Request timeout');
            }
            
            // Retry logic
            if (retryCount < this.config.retryAttempts) {
                console.warn(`🔄 Retrying request ${requestId} (attempt ${retryCount + 1}/${this.config.retryAttempts})`);
                await this.delay(1000 * (retryCount + 1)); // Exponential backoff
                return this.makeRequest(requestBody, retryCount + 1);
            }
            
            // Record failure for circuit breaker
            this.circuitBreaker.failures++;
            this.circuitBreaker.lastFailureTime = Date.now();
            
            throw error;
            
        } finally {
            this.activeRequests.delete(requestId);
        }
    }
    
    /**
     * Handle streaming response from Ollama
     */
    async handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim());
                
                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        if (data.response) {
                            fullResponse += data.response;
                            this.emit('stream-token', data.response);
                        }
                        if (data.done) {
                            return { response: fullResponse, ...data };
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse stream chunk:', parseError);
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
        
        return { response: fullResponse };
    }
    
    /**
     * Analyze current battlefield situation and provide strategic recommendations
     */
    async analyzeGameState(gameState) {
        if (this.config.offlineMode) {
            return this.getOfflineAnalysis(gameState);
        }
        
        try {
            // Compress game state for efficient context usage
            const compressedState = this.compressGameState(gameState);
            
            // Build strategic analysis prompt
            const prompt = this.buildStrategicPrompt(compressedState);
            
            // Make request to Ollama
            const response = await this.makeRequest({
                model: this.config.model,
                prompt: prompt,
                stream: this.config.streamEnabled,
                options: {
                    temperature: 0.3, // Lower temperature for more consistent analysis
                    top_p: 0.9,
                    num_predict: 300,
                    stop: ['###', '---']
                }
            });
            
            // Parse and validate response
            const analysis = this.parseStrategicResponse(response.response);
            
            // Cache successful analysis
            this.cacheAnalysis(gameState, analysis);
            
            return analysis;
            
        } catch (error) {
            console.warn('Strategic analysis failed:', error.message);
            
            // Try fallback strategies
            if (this.config.enableFallback) {
                return this.getOfflineAnalysis(gameState);
            }
            
            throw error;
        }
    }
    
    /**
     * Parse natural language commands into game actions
     */
    async parseCommand(naturalLanguageCommand, gameContext = {}) {
        if (this.config.offlineMode) {
            return this.parseCommandOffline(naturalLanguageCommand, gameContext);
        }
        
        try {
            const prompt = this.buildCommandPrompt(naturalLanguageCommand, gameContext);
            
            const response = await this.makeRequest({
                model: this.config.model,
                prompt: prompt,
                stream: false,
                options: {
                    temperature: 0.1, // Very low temperature for precise command parsing
                    top_p: 0.8,
                    num_predict: 150,
                    stop: ['###', '---', 'Human:']
                }
            });
            
            return this.parseCommandResponse(response.response);
            
        } catch (error) {
            console.warn('Command parsing failed:', error.message);
            return this.parseCommandOffline(naturalLanguageCommand, gameContext);
        }
    }
    
    /**
     * Compress game state to fit within context window
     */
    compressGameState(gameState) {
        const cacheKey = this.generateStateHash(gameState);
        
        if (this.compressionCache.has(cacheKey)) {
            this.metrics.cachehits++;
            return this.compressionCache.get(cacheKey);
        }
        
        const compressed = {
            // Essential battlefield information
            units: this.summarizeUnits(gameState.units || []),
            buildings: this.summarizeBuildings(gameState.buildings || []),
            resources: this.summarizeResources(gameState.economy || {}),
            
            // Strategic context
            mapInfo: {
                size: gameState.mapSize || 'unknown',
                terrain: gameState.terrain || 'mixed'
            },
            
            // Threats and opportunities
            threats: this.identifyThreats(gameState),
            opportunities: this.identifyOpportunities(gameState),
            
            // Current objectives
            objectives: gameState.objectives || [],
            
            // Time context
            gameTime: gameState.gameTime || 0,
            phase: this.determineGamePhase(gameState)
        };
        
        // Cache the compression
        this.compressionCache.set(cacheKey, compressed);
        
        // Limit cache size
        if (this.compressionCache.size > 50) {
            const firstKey = this.compressionCache.keys().next().value;
            this.compressionCache.delete(firstKey);
        }
        
        return compressed;
    }
    
    /**
     * Build strategic analysis prompt using role-based prompting
     */
    buildStrategicPrompt(gameState) {
        const template = this.promptTemplates.strategicAnalysis;
        
        return template
            .replace('{gameState}', JSON.stringify(gameState, null, 2))
            .replace('{timestamp}', new Date().toISOString())
            .replace('{gamePhase}', gameState.phase || 'mid-game');
    }
    
    /**
     * Build command parsing prompt
     */
    buildCommandPrompt(command, context) {
        const template = this.promptTemplates.commandParsing;
        
        const availableCommands = Object.keys(this.commandMapping).join(', ');
        
        return template
            .replace('{command}', command)
            .replace('{context}', JSON.stringify(context, null, 2))
            .replace('{availableCommands}', availableCommands);
    }
    
    /**
     * Parse strategic analysis response
     */
    parseStrategicResponse(response) {
        try {
            // Try to extract JSON from response
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
            
            // Fallback to structured text parsing
            return this.parseTextResponse(response);
            
        } catch (error) {
            console.warn('Failed to parse strategic response:', error);
            return this.createDefaultAnalysis(response);
        }
    }
    
    /**
     * Parse command response into structured action
     */
    parseCommandResponse(response) {
        try {
            // Try to extract JSON command
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                const parsed = JSON.parse(jsonMatch[0]);
                return this.validateCommand(parsed);
            }
            
            // Fallback to keyword extraction
            return this.extractCommandFromText(response);
            
        } catch (error) {
            console.warn('Failed to parse command response:', error);
            return { type: 'unknown', confidence: 0, raw: response };
        }
    }
    
    /**
     * Offline analysis using rule-based system
     */
    getOfflineAnalysis(gameState) {
        console.log('🔄 Using offline strategic analysis');
        
        const analysis = {
            type: 'strategic_analysis',
            confidence: 0.7,
            timestamp: Date.now(),
            recommendations: [],
            threats: [],
            opportunities: [],
            source: 'offline-rules'
        };
        
        // Basic rule-based analysis
        if (gameState.economy && gameState.economy.credits < 1000) {
            analysis.recommendations.push({
                priority: 'high',
                action: 'focus_economy',
                description: 'Low credits detected - prioritize resource gathering'
            });
        }
        
        if (gameState.units && gameState.units.length < 5) {
            analysis.recommendations.push({
                priority: 'medium',
                action: 'build_units',
                description: 'Limited military force - consider unit production'
            });
        }
        
        return analysis;
    }
    
    /**
     * Offline command parsing using pattern matching
     */
    parseCommandOffline(command, context) {
        console.log('🔄 Using offline command parsing');
        
        const lowerCommand = command.toLowerCase();
        
        // Check command patterns
        for (const [pattern, action] of Object.entries(this.commandMapping)) {
            if (lowerCommand.includes(pattern)) {
                return {
                    type: action.type,
                    parameters: action.extractParams ? action.extractParams(command) : {},
                    confidence: 0.8,
                    source: 'offline-pattern-matching'
                };
            }
        }
        
        return {
            type: 'unknown',
            confidence: 0,
            raw: command,
            source: 'offline-fallback'
        };
    }
    
    /**
     * Initialize prompt templates for different use cases
     */
    initializePromptTemplates() {
        return {
            strategicAnalysis: `### Role
You are an expert RTS (Real-Time Strategy) military analyst providing tactical battlefield analysis.

### Context
Current game state: {gameState}
Analysis timestamp: {timestamp}
Game phase: {gamePhase}

### Task
Analyze the battlefield situation and provide strategic recommendations in the following JSON format:

{
  "type": "strategic_analysis",
  "confidence": 0.0-1.0,
  "threats": [
    {"type": "threat_type", "severity": "low|medium|high", "description": "brief_description"}
  ],
  "opportunities": [
    {"type": "opportunity_type", "potential": "low|medium|high", "description": "brief_description"}
  ],
  "recommendations": [
    {"priority": "low|medium|high", "action": "action_type", "description": "detailed_recommendation"}
  ],
  "next_analysis_in": "seconds"
}

### Instructions
- Focus on actionable intelligence
- Prioritize immediate threats and opportunities
- Consider resource efficiency
- Provide specific unit/building recommendations
- Keep analysis concise but informative

### Analysis`,

            commandParsing: `### Role
You are a natural language command parser for an RTS game.

### Available Commands
{availableCommands}

### Context
Game state: {context}

### Task
Parse this natural language command into a structured game action: "{command}"

Respond with this JSON format:
{
  "type": "command_type",
  "parameters": {
    "target": "target_if_applicable",
    "quantity": "number_if_applicable",
    "location": "coordinates_if_applicable"
  },
  "confidence": 0.0-1.0,
  "description": "human_readable_description"
}

### Instructions
- Extract specific targets, quantities, and locations
- Map to available game commands
- Return highest confidence interpretation
- If ambiguous, choose most likely interpretation

### Parsed Command`
        };
    }
    
    /**
     * Initialize command mapping for natural language processing
     */
    initializeCommandMapping() {
        return {
            'build': {
                type: 'build',
                extractParams: (cmd) => {
                    const unitMatch = cmd.match(/(tank|infantry|harvester|refinery|barracks|factory)/i);
                    const quantityMatch = cmd.match(/(\d+)/);
                    return {
                        unit: unitMatch ? unitMatch[1].toLowerCase() : null,
                        quantity: quantityMatch ? parseInt(quantityMatch[1]) : 1
                    };
                }
            },
            'attack': {
                type: 'attack',
                extractParams: (cmd) => {
                    const targetMatch = cmd.match(/(base|enemy|unit|building)/i);
                    return {
                        target: targetMatch ? targetMatch[1].toLowerCase() : 'enemy'
                    };
                }
            },
            'move': {
                type: 'move',
                extractParams: (cmd) => {
                    const directionMatch = cmd.match(/(north|south|east|west|up|down|left|right)/i);
                    return {
                        direction: directionMatch ? directionMatch[1].toLowerCase() : null
                    };
                }
            },
            'select': {
                type: 'select',
                extractParams: (cmd) => {
                    const allMatch = cmd.match(/all/i);
                    const typeMatch = cmd.match(/(tank|infantry|harvester)/i);
                    return {
                        target: allMatch ? 'all' : (typeMatch ? typeMatch[1].toLowerCase() : null)
                    };
                }
            },
            'stop': { type: 'stop' },
            'hold': { type: 'hold_position' },
            'patrol': { type: 'patrol' }
        };
    }
    
    /**
     * Initialize fallback strategies for when Ollama is unavailable
     */
    initializeFallbackStrategies() {
        return {
            // Rule-based strategic advice
            economicPriority: (gameState) => {
                if (!gameState.economy || gameState.economy.credits < 500) {
                    return { action: 'build_harvester', priority: 'high' };
                }
                return null;
            },
            
            // Basic threat assessment
            threatAssessment: (gameState) => {
                if (gameState.units && gameState.units.length < 3) {
                    return { threat: 'insufficient_defense', severity: 'medium' };
                }
                return null;
            },
            
            // Simple command templates
            commandTemplates: {
                'build tank': { type: 'build', parameters: { unit: 'tank', quantity: 1 } },
                'attack enemy': { type: 'attack', parameters: { target: 'enemy' } },
                'select all': { type: 'select', parameters: { target: 'all' } }
            }
        };
    }
    
    /**
     * Utility methods
     */
    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    generateStateHash(state) {
        const stateStr = JSON.stringify(state);
        let hash = 0;
        for (let i = 0; i < stateStr.length; i++) {
            const char = stateStr.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash.toString();
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    updateMetrics(success, responseTime) {
        this.metrics.totalRequests++;
        if (success) {
            this.metrics.successfulRequests++;
        }
        
        // Update average response time
        const totalTime = this.metrics.averageResponseTime * (this.metrics.totalRequests - 1) + responseTime;
        this.metrics.averageResponseTime = totalTime / this.metrics.totalRequests;
    }
    
    /**
     * Get performance metrics and health status
     */
    getStatus() {
        return {
            connected: this.connected,
            healthy: this.healthy,
            model: this.config.model,
            offlineMode: this.config.offlineMode,
            circuitBreaker: {
                state: this.circuitBreaker.state,
                failures: this.circuitBreaker.failures
            },
            metrics: { ...this.metrics },
            activeRequests: this.activeRequests.size,
            queuedRequests: this.requestQueue.length
        };
    }
    
    /**
     * Cleanup resources
     */
    destroy() {
        console.log('🗑️ Destroying Ollama Strategic Advisor...');
        
        // Cancel active requests
        this.activeRequests.clear();
        this.requestQueue = [];
        
        // Clear caches
        this.compressionCache.clear();
        this.gameStateHistory = [];
        
        // Remove all listeners
        this.removeAllListeners();
        
        console.log('✅ Ollama Strategic Advisor destroyed');
    }
    
    // Additional helper methods for game state analysis would be implemented here
    summarizeUnits(units) { return units.slice(0, 10); } // Simplified
    summarizeBuildings(buildings) { return buildings.slice(0, 5); } // Simplified
    summarizeResources(economy) { return { credits: economy.credits || 0 }; } // Simplified
    identifyThreats(gameState) { return []; } // Simplified
    identifyOpportunities(gameState) { return []; } // Simplified
    determineGamePhase(gameState) { return 'mid-game'; } // Simplified
    parseTextResponse(response) { return { type: 'text', content: response }; } // Simplified
    createDefaultAnalysis(response) { return { type: 'default', content: response }; } // Simplified
    validateCommand(command) { return command; } // Simplified
    extractCommandFromText(text) { return { type: 'extracted', raw: text }; } // Simplified
    cacheAnalysis(gameState, analysis) { /* Implementation */ } // Simplified
}