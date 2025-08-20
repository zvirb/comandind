# Ollama LLM Integration Specifications for RTS Strategic AI Advisor

## Executive Summary

This document provides comprehensive specifications for integrating Ollama LLM into the Command & Independent Thought RTS game as a strategic AI advisor. The integration enables real-time battlefield analysis, natural language command processing, and strategic recommendations while maintaining <500ms response times and privacy-first local processing.

## System Architecture

### Core Components

#### 1. **OllamaStrategicAdvisor Class**
- **Location**: `/src/ai/OllamaStrategicAdvisor.js`
- **Purpose**: Primary interface for LLM integration
- **Key Features**:
  - WebSocket-style streaming communication
  - Circuit breaker pattern for reliability
  - Context window management (4096 tokens)
  - Fallback mechanisms for offline operation
  - Performance optimization for <500ms responses

#### 2. **Connection Management**
```javascript
// Configuration
{
  host: 'http://127.0.0.1:11434',  // Local Ollama instance
  model: 'llama3.1:8b',            // Primary model
  fallbackModel: 'llama3.2:3b',    // Lightweight fallback
  maxResponseTime: 500,            // Performance target (ms)
  streamEnabled: true,             // Real-time streaming
  contextWindowSize: 4096          // Token limit
}
```

#### 3. **Privacy and Security**
- **Local Processing**: All LLM inference runs locally via Ollama
- **No Data Transmission**: Game state never leaves local machine
- **Offline Capability**: Graceful degradation when Ollama unavailable
- **Circuit Breaker**: Automatic fallback on service failures

## Technical Implementation

### WebSocket Client Pattern

```javascript
// Streaming response handling
async handleStreamResponse(response) {
  const reader = response.body.getReader();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    // Emit real-time tokens for immediate UI feedback
    this.emit('stream-token', data.response);
  }
}
```

### Context Window Management

#### Game State Compression Strategy
```javascript
// Efficient game state serialization
compressGameState(gameState) {
  return {
    // Essential battlefield data (≤2000 tokens)
    units: this.summarizeUnits(gameState.units),
    buildings: this.summarizeBuildings(gameState.buildings),
    resources: this.summarizeResources(gameState.economy),
    
    // Strategic context
    threats: this.identifyThreats(gameState),
    opportunities: this.identifyOpportunities(gameState),
    phase: this.determineGamePhase(gameState)
  };
}
```

#### Memory Management
- **Context Window**: 4096 tokens maximum
- **Game State Allocation**: ≤2000 tokens
- **Prompt Template**: ≤1000 tokens  
- **Response Buffer**: ≤1096 tokens
- **Compression Cache**: LRU cache with 50 entry limit

### Prompt Engineering Patterns

#### Strategic Analysis Template
```javascript
strategicAnalysis: `### Role
You are an expert RTS military analyst providing tactical battlefield analysis.

### Context
Current game state: {gameState}
Game phase: {gamePhase}

### Task
Analyze the battlefield and provide strategic recommendations in JSON format:

{
  "threats": [{"type": "threat_type", "severity": "high", "description": "..."}],
  "opportunities": [{"type": "opportunity_type", "potential": "high", "description": "..."}],
  "recommendations": [{"priority": "high", "action": "build_tanks", "description": "..."}]
}

### Instructions
- Focus on actionable intelligence
- Prioritize immediate threats
- Consider resource efficiency
- Provide specific recommendations`
```

#### Command Parsing Template
```javascript
commandParsing: `### Role
You are a natural language command parser for an RTS game.

### Task
Parse this command into structured action: "{command}"

Response format:
{
  "type": "build|attack|move|select",
  "parameters": {"target": "...", "quantity": 1},
  "confidence": 0.9
}

### Available Commands
build, attack, move, select, stop, hold, patrol`
```

### Response Parsing and Validation

#### Structured JSON Output Processing
```javascript
parseStrategicResponse(response) {
  try {
    // Extract JSON from response
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return this.validateResponse(parsed);
    }
    
    // Fallback to text parsing
    return this.parseTextResponse(response);
  } catch (error) {
    return this.createDefaultAnalysis(response);
  }
}
```

#### Command Validation
```javascript
validateCommand(command) {
  const validTypes = ['build', 'attack', 'move', 'select', 'stop', 'hold', 'patrol'];
  
  if (!validTypes.includes(command.type)) {
    throw new Error(`Invalid command type: ${command.type}`);
  }
  
  if (command.confidence < 0.6) {
    console.warn('Low confidence command detected');
  }
  
  return command;
}
```

## Performance Optimization

### Sub-500ms Response Time Strategy

#### 1. **Model Selection**
- **Primary**: `llama3.1:8b` (balanced performance/quality)
- **Fallback**: `llama3.2:3b` (faster inference)
- **Streaming**: Token-by-token delivery for perceived speed

#### 2. **Request Optimization**
```javascript
// Optimized request parameters
{
  temperature: 0.3,        // Lower temperature for consistency
  top_p: 0.9,             // Focused sampling
  num_predict: 300,       // Limited output length
  stop: ['###', '---']    // Early termination markers
}
```

#### 3. **Caching Strategy**
- **Compression Cache**: Reuse processed game states
- **Analysis Cache**: Cache recent strategic analyses
- **Pattern Cache**: Store common command patterns
- **LRU Eviction**: Automatic cache management

#### 4. **Circuit Breaker Pattern**
```javascript
circuitBreaker: {
  state: 'closed',        // closed, open, half-open
  failures: 0,
  maxFailures: 5,
  timeout: 60000,         // 1 minute recovery time
  lastFailureTime: 0
}
```

### Fallback Mechanisms

#### 1. **Offline Mode Capabilities**
```javascript
getOfflineAnalysis(gameState) {
  const analysis = {
    recommendations: [],
    threats: [],
    opportunities: [],
    source: 'offline-rules'
  };
  
  // Rule-based analysis
  if (gameState.economy.credits < 1000) {
    analysis.recommendations.push({
      priority: 'high',
      action: 'focus_economy',
      description: 'Low credits - prioritize resource gathering'
    });
  }
  
  return analysis;
}
```

#### 2. **Command Pattern Matching**
```javascript
commandMapping: {
  'build tank': { type: 'build', parameters: { unit: 'tank', quantity: 1 } },
  'attack enemy': { type: 'attack', parameters: { target: 'enemy' } },
  'select all': { type: 'select', parameters: { target: 'all' } }
}
```

#### 3. **Graceful Degradation**
- **Service Unavailable**: Display "AI Advisor Offline" message
- **Partial Functionality**: Basic rule-based recommendations
- **User Feedback**: Clear status indicators
- **Automatic Recovery**: Seamless reconnection when service restored

## Integration with Existing Game Systems

### Input Handler Integration

```javascript
// Natural language command processing
inputHandler.on('voice-command', async (command) => {
  try {
    const parsedCommand = await strategicAdvisor.parseCommand(command.text);
    gameCommandSystem.execute(parsedCommand);
  } catch (error) {
    ui.showMessage('Command not recognized');
  }
});
```

### Game Loop Integration

```javascript
// Periodic strategic analysis
class GameLoop {
  async update(deltaTime) {
    // Standard game update
    super.update(deltaTime);
    
    // Strategic analysis every 10 seconds
    if (this.shouldRunAnalysis()) {
      const gameState = this.world.exportState();
      const analysis = await this.strategicAdvisor.analyzeGameState(gameState);
      this.ui.updateStrategicOverlay(analysis);
    }
  }
}
```

### UI Integration

```javascript
// Strategic advice display
class StrategicUI {
  displayAnalysis(analysis) {
    // Threat indicators
    this.threatPanel.update(analysis.threats);
    
    // Recommended actions
    this.actionPanel.update(analysis.recommendations);
    
    // Opportunity highlights
    this.opportunityOverlay.highlight(analysis.opportunities);
  }
}
```

## Natural Language Command System

### Supported Command Categories

#### 1. **Unit Management**
- "Build 5 tanks"
- "Select all infantry" 
- "Move units north"
- "Attack enemy base"

#### 2. **Economic Commands**
- "Build refinery"
- "Send harvester to resources"
- "Focus on economy"

#### 3. **Strategic Commands**
- "Defend the base"
- "Prepare for attack"
- "Scout the area"

### Command Processing Pipeline

```javascript
async parseCommand(naturalLanguageCommand, gameContext) {
  // 1. Preprocess command
  const normalizedCommand = this.normalizeCommand(naturalLanguageCommand);
  
  // 2. Check offline patterns first (fast path)
  const offlineResult = this.parseCommandOffline(normalizedCommand);
  if (offlineResult.confidence > 0.8) {
    return offlineResult;
  }
  
  // 3. Use LLM for complex parsing
  const llmResult = await this.parseCommandWithLLM(normalizedCommand, gameContext);
  
  // 4. Validate and return
  return this.validateCommand(llmResult);
}
```

## Error Handling and Monitoring

### Health Monitoring

```javascript
// Continuous health checks
startHealthMonitoring() {
  setInterval(async () => {
    try {
      await this.testConnection();
      this.handleHealthyConnection();
    } catch (error) {
      this.handleConnectionFailure(error);
    }
  }, 30000); // 30-second intervals
}
```

### Performance Metrics

```javascript
metrics: {
  totalRequests: 0,
  successfulRequests: 0,
  averageResponseTime: 0,
  cacheHits: 0,
  circuitBreakerTrips: 0
}
```

### Error Recovery

```javascript
// Retry with exponential backoff
async makeRequestWithRetry(request, retryCount = 0) {
  try {
    return await this.makeRequest(request);
  } catch (error) {
    if (retryCount < this.config.retryAttempts) {
      await this.delay(1000 * (retryCount + 1));
      return this.makeRequestWithRetry(request, retryCount + 1);
    }
    throw error;
  }
}
```

## Deployment and Configuration

### System Requirements

#### Minimum Hardware
- **CPU**: 4-core processor
- **RAM**: 8GB available memory
- **Storage**: 10GB for model files
- **GPU**: Optional (CPU inference supported)

#### Recommended Hardware
- **CPU**: 8-core processor
- **RAM**: 16GB available memory
- **GPU**: RTX 3060 or equivalent (5x performance boost)

### Ollama Installation

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama3.1:8b
ollama pull llama3.2:3b

# Start Ollama service
ollama serve
```

### Game Configuration

```javascript
// Initialize strategic advisor
const strategicAdvisor = new OllamaStrategicAdvisor({
  host: 'http://127.0.0.1:11434',
  model: 'llama3.1:8b',
  maxResponseTime: 500,
  streamEnabled: true,
  enableFallback: true
});

// Integration with game systems
game.addSystem(strategicAdvisor);
```

## Testing and Validation

### Performance Testing

```javascript
// Response time validation
describe('Performance Tests', () => {
  it('should respond within 500ms', async () => {
    const startTime = Date.now();
    const result = await advisor.analyzeGameState(mockGameState);
    const responseTime = Date.now() - startTime;
    
    expect(responseTime).toBeLessThan(500);
  });
});
```

### Integration Testing

```javascript
// End-to-end command processing
describe('Command Integration', () => {
  it('should parse "build 3 tanks" correctly', async () => {
    const command = await advisor.parseCommand("build 3 tanks");
    
    expect(command.type).toBe('build');
    expect(command.parameters.unit).toBe('tank');
    expect(command.parameters.quantity).toBe(3);
  });
});
```

### Fallback Testing

```javascript
// Offline mode validation
describe('Fallback Tests', () => {
  it('should provide analysis when Ollama unavailable', async () => {
    advisor.config.offlineMode = true;
    const analysis = await advisor.analyzeGameState(mockGameState);
    
    expect(analysis.source).toBe('offline-rules');
    expect(analysis.recommendations).toHaveLength.greaterThan(0);
  });
});
```

## Privacy Considerations

### Data Handling
- **Local Processing**: All AI inference occurs locally
- **No Telemetry**: No data transmitted to external services
- **Game State Privacy**: Strategic information never leaves local machine
- **User Commands**: Voice/text commands processed locally only

### Security Features
- **Network Isolation**: Can operate without internet connection
- **Sandboxed Execution**: Ollama runs in controlled environment
- **Resource Limits**: Memory and CPU usage bounded
- **Fail-Safe Operation**: Graceful degradation on component failure

## Future Enhancements

### Planned Features
1. **Multi-Model Ensemble**: Combine different models for specialized tasks
2. **Adaptive Learning**: Tune responses based on player preferences
3. **Voice Integration**: Direct speech-to-text processing
4. **Advanced Context**: Historical game analysis and pattern recognition
5. **Multiplayer Coordination**: Team strategy recommendations

### Scalability Considerations
- **Model Swapping**: Hot-swap models based on performance requirements
- **Distributed Processing**: Multi-instance Ollama for load balancing
- **Cloud Fallback**: Optional cloud LLM when local resources insufficient
- **Edge Optimization**: Specialized models for mobile/embedded deployment

## Conclusion

This integration provides a sophisticated AI strategic advisor that maintains privacy, performance, and reliability while enhancing the RTS gaming experience. The system is designed to be resilient, performant, and user-friendly, with comprehensive fallback mechanisms ensuring continuous operation regardless of underlying service availability.

The implementation balances the power of modern LLMs with the practical requirements of real-time gaming, delivering sub-500ms response times while providing meaningful strategic insights and natural language command processing capabilities.