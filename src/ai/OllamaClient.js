/**
 * OllamaClient - Basic HTTP client for Ollama connection testing
 * Minimal implementation focused on connection validation and circuit breaker pattern
 */

import { OllamaConfig } from "./OllamaConfig.js";

export class OllamaClient {
    constructor(config = {}) {
        this.config = { ...OllamaConfig, ...config };
        
        // Connection state
        this.isConnected = false;
        this.isHealthy = false;
        this.lastHealthCheck = 0;
        
        // Circuit breaker state
        this.circuitBreaker = {
            state: "closed", // closed, open, half-open
            failures: 0,
            lastFailureTime: 0
        };
        
        // Performance tracking
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            averageResponseTime: 0,
            lastResponseTime: 0
        };
    }
    
    /**
     * Test connection to Ollama service
     * @returns {Promise<boolean>} Connection success status
     */
    async testConnection() {
        const startTime = Date.now();
        let timeoutId;
        
        try {
            // Check circuit breaker
            if (this.circuitBreaker.state === "open") {
                const timeSinceLastFailure = Date.now() - this.circuitBreaker.lastFailureTime;
                if (timeSinceLastFailure < this.config.resetTimeout) {
                    console.log("🚫 Circuit breaker is open, skipping connection test");
                    return false;
                }
                // Transition to half-open
                this.circuitBreaker.state = "half-open";
                console.log("🔄 Circuit breaker transitioning to half-open");
            }
            
            const controller = new AbortController();
            timeoutId = setTimeout(() => {
                controller.abort();
            }, this.config.connectionTimeout);
            
            const response = await fetch(`${this.config.host}${this.config.endpoints.health}`, {
                method: "GET",
                signal: controller.signal,
                headers: { "Content-Type": "application/json" }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const responseTime = Date.now() - startTime;
            
            // Verify models are available
            const availableModels = data.models || [];
            const hasPreferredModel = availableModels.some(m => m.name === this.config.model);
            const hasFallbackModel = availableModels.some(m => m.name === this.config.fallbackModel);
            
            if (!hasPreferredModel && !hasFallbackModel) {
                throw new Error(`No compatible models available. Found: ${availableModels.map(m => m.name).join(", ")}`);
            }
            
            // Update connection state
            this.isConnected = true;
            this.isHealthy = true;
            this.lastHealthCheck = Date.now();
            
            // Reset circuit breaker on success
            if (this.circuitBreaker.state === "half-open") {
                this.circuitBreaker.state = "closed";
                this.circuitBreaker.failures = 0;
                console.log("✅ Circuit breaker reset to closed");
            }
            
            this.updateMetrics(true, responseTime);
            console.log(`✅ Connected to Ollama (${responseTime}ms) - Available models: ${availableModels.length}`);
            
            return true;
            
        } catch (error) {
            if (timeoutId) clearTimeout(timeoutId);
            const responseTime = Date.now() - startTime;
            
            this.isConnected = false;
            this.isHealthy = false;
            this.handleConnectionFailure(error);
            this.updateMetrics(false, responseTime);
            
            console.warn(`❌ Ollama connection failed (${responseTime}ms):`, error.message);
            return false;
        }
    }
    
    /**
     * Send a test prompt to Ollama
     * @param {string} prompt - The prompt to send (defaults to config test prompt)
     * @returns {Promise<Object>} Response from Ollama or error info
     */
    async sendTestPrompt(prompt = null) {
        if (!this.isConnected) {
            const connected = await this.testConnection();
            if (!connected) {
                return {
                    success: false,
                    error: "Not connected to Ollama",
                    fallback: true
                };
            }
        }
        
        const testPrompt = prompt || this.config.testPrompt;
        const startTime = Date.now();
        let timeoutId;
        
        try {
            const controller = new AbortController();
            timeoutId = setTimeout(() => {
                controller.abort();
            }, this.config.requestTimeout);
            
            const requestBody = {
                model: this.config.model,
                prompt: testPrompt,
                stream: false,
                options: this.config.defaultOptions
            };
            
            const response = await fetch(`${this.config.host}${this.config.endpoints.generate}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const responseTime = Date.now() - startTime;
            
            this.updateMetrics(true, responseTime);
            
            console.log(`✅ Test prompt successful (${responseTime}ms):`, data.response?.substring(0, 100) + "...");
            
            return {
                success: true,
                response: data.response,
                responseTime,
                model: this.config.model,
                fallback: false
            };
            
        } catch (error) {
            if (timeoutId) clearTimeout(timeoutId);
            const responseTime = Date.now() - startTime;
            this.updateMetrics(false, responseTime);
            
            // Handle timeout specifically
            if (error.name === "AbortError") {
                console.warn(`⏰ Test prompt timed out after ${this.config.requestTimeout}ms`);
                return {
                    success: false,
                    error: "Request timeout",
                    responseTime,
                    fallback: true
                };
            }
            
            this.handleConnectionFailure(error);
            console.warn(`❌ Test prompt failed (${responseTime}ms):`, error.message);
            
            return {
                success: false,
                error: error.message,
                responseTime,
                fallback: true
            };
        }
    }
    
    /**
     * Generate response using async generator for streaming
     * @param {string} prompt - The prompt to send
     * @yields {string} Response chunks
     */
    async* generateStream(prompt) {
        if (!this.isConnected && !(await this.testConnection())) {
            yield "Error: Cannot connect to Ollama service";
            return;
        }
        
        try {
            const requestBody = {
                model: this.config.model,
                prompt: prompt,
                stream: true,
                options: this.config.defaultOptions
            };
            
            const controller = new AbortController();
            let timeoutId = setTimeout(() => {
                controller.abort();
            }, this.config.requestTimeout * 4); // Longer timeout for streaming
            
            const response = await fetch(`${this.config.host}${this.config.endpoints.generate}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split("\n").filter(line => line.trim());
                    
                    for (const line of lines) {
                        try {
                            const data = JSON.parse(line);
                            if (data.response) {
                                yield data.response;
                            }
                            if (data.done) {
                                return;
                            }
                        } catch (parseError) {
                            console.warn("Failed to parse stream chunk:", parseError);
                        }
                    }
                }
            } finally {
                reader.releaseLock();
            }
            
        } catch (error) {
            if (timeoutId) clearTimeout(timeoutId);
            this.handleConnectionFailure(error);
            yield `Error: ${error.message}`;
        }
    }
    
    /**
     * Check if Ollama is available (quick health check)
     * @returns {boolean} Availability status
     */
    isAvailable() {
        if (this.circuitBreaker.state === "open") {
            return false;
        }
        
        // Consider healthy if we checked recently
        const timeSinceHealthCheck = Date.now() - this.lastHealthCheck;
        return this.isHealthy && timeSinceHealthCheck < 30000; // 30 seconds
    }
    
    /**
     * Get connection status and metrics
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            connected: this.isConnected,
            healthy: this.isHealthy,
            available: this.isAvailable(),
            model: this.config.model,
            host: this.config.host,
            lastHealthCheck: this.lastHealthCheck,
            circuitBreaker: {
                state: this.circuitBreaker.state,
                failures: this.circuitBreaker.failures,
                timeSinceLastFailure: Date.now() - this.circuitBreaker.lastFailureTime
            },
            metrics: { ...this.metrics }
        };
    }
    
    /**
     * Handle connection failures and update circuit breaker
     * @private
     */
    handleConnectionFailure(error) {
        this.circuitBreaker.failures++;
        this.circuitBreaker.lastFailureTime = Date.now();
        
        if (this.circuitBreaker.failures >= this.config.maxFailures) {
            console.warn(`⚡ Circuit breaker opened after ${this.circuitBreaker.failures} failures`);
            this.circuitBreaker.state = "open";
        }
    }
    
    /**
     * Update performance metrics
     * @private
     */
    updateMetrics(success, responseTime) {
        this.metrics.totalRequests++;
        this.metrics.lastResponseTime = responseTime;
        
        if (success) {
            this.metrics.successfulRequests++;
        }
        
        // Update rolling average
        const totalTime = this.metrics.averageResponseTime * (this.metrics.totalRequests - 1) + responseTime;
        this.metrics.averageResponseTime = Math.round(totalTime / this.metrics.totalRequests);
    }
    
    /**
     * Reset circuit breaker manually (for testing)
     */
    resetCircuitBreaker() {
        this.circuitBreaker.state = "closed";
        this.circuitBreaker.failures = 0;
        this.circuitBreaker.lastFailureTime = 0;
        console.log("🔄 Circuit breaker manually reset");
    }
    
    /**
     * Force a health check
     * @returns {Promise<boolean>} Health status
     */
    async checkHealth() {
        console.log("🔍 Performing manual health check...");
        return await this.testConnection();
    }
}

export default OllamaClient;