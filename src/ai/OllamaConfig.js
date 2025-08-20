/**
 * OllamaConfig - Basic configuration for Ollama connection testing
 * Minimal configuration focused on connection validation
 */

export const OllamaConfig = {
    // Connection settings
    host: "http://127.0.0.1:11434",
    model: "llama3.1:8b",
    fallbackModel: "llama3.2:3b",
    
    // Timeout settings (focused on quick responses)
    connectionTimeout: 5000, // 5 seconds for connection test
    requestTimeout: 500,     // 500ms for quick responses
    
    // Circuit breaker settings
    maxFailures: 3,          // Open circuit after 3 failures
    resetTimeout: 30000,     // 30 seconds before retry
    
    // Test configuration
    testPrompt: "Analyze: 5 enemy tanks approaching",
    
    // API endpoints
    endpoints: {
        tags: "/api/tags",
        generate: "/api/generate",
        health: "/api/tags"  // Using tags endpoint as health check
    },
    
    // Default request options
    defaultOptions: {
        temperature: 0.3,
        num_predict: 50,
        stop: ["###", "---"]
    }
};

export default OllamaConfig;