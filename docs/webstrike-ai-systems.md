# WebStrike Command - AI Systems

## Q-Learning Implementation

```javascript
const model = tf.sequential({
  layers: [
    tf.layers.dense({units: 128, activation: 'relu', inputShape: [stateSize]}),
    tf.layers.dense({units: 128, activation: 'relu'}),
    tf.layers.dense({units: actionSize})
  ]
});

// Experience replay with 10,000 capacity buffer
class ExperienceReplayBuffer {
  constructor(capacity = 10000) {
    this.capacity = capacity;
    this.experiences = [];
  }
  
  add(state, action, reward, nextState, done) {
    if (this.experiences.length >= this.capacity) {
      this.experiences.shift();
    }
    this.experiences.push({state, action, reward, nextState, done});
  }
  
  sample(batchSize) {
    const batch = [];
    for (let i = 0; i < batchSize; i++) {
      const randomIndex = Math.floor(Math.random() * this.experiences.length);
      batch.push(this.experiences[randomIndex]);
    }
    return batch;
  }
}
```

## State Representation
- **Normalized unit positions** (0-1 range)
- **Health status percentages**
- **Enemy proximity metrics**
- **Resource availability scores**
- **Terrain information** (passable/impassable)
- **Strategic objectives status**

## Behavior Trees for Unit Autonomy

```javascript
class BehaviorTree {
  constructor(rootNode) {
    this.root = rootNode;
  }
  
  update() {
    return this.root.run();
  }
}

// Selector node for decision branching
class Selector extends CompositeNode {
  run() {
    for (let child of this.children) {
      const result = child.run();
      if (result === 'SUCCESS') return 'SUCCESS';
    }
    return 'FAILURE';
  }
}

// Sequence node for sequential actions
class Sequence extends CompositeNode {
  run() {
    for (let child of this.children) {
      const result = child.run();
      if (result !== 'SUCCESS') return result;
    }
    return 'SUCCESS';
  }
}
```

## Goal-Oriented Action Planning (GOAP)

```javascript
class GoapAction {
  constructor(name, cost, preconditions, effects) {
    this.name = name;
    this.cost = cost;
    this.preconditions = preconditions; // {hasAxe: true, nearTree: true}
    this.effects = effects; // {hasWood: true}
  }
  
  checkPreconditions(worldState) {
    return Object.keys(this.preconditions).every(
      key => worldState[key] === this.preconditions[key]
    );
  }
  
  applyEffects(worldState) {
    return {...worldState, ...this.effects};
  }
}

class GoapPlanner {
  planActions(worldState, goals) {
    const openSet = [{state: worldState, actions: [], cost: 0}];
    const closedSet = new Set();
    
    while (openSet.length > 0) {
      const current = openSet.shift();
      
      if (this.goalsSatisfied(current.state, goals)) {
        return current.actions;
      }
      
      const stateKey = this.stateToKey(current.state);
      if (closedSet.has(stateKey)) continue;
      closedSet.add(stateKey);
      
      for (let action of this.availableActions) {
        if (action.checkPreconditions(current.state)) {
          const newState = action.applyEffects(current.state);
          const newActions = [...current.actions, action];
          const newCost = current.cost + action.cost;
          
          openSet.push({
            state: newState,
            actions: newActions,
            cost: newCost
          });
        }
      }
      
      // Sort by cost (A* pathfinding)
      openSet.sort((a, b) => a.cost - b.cost);
    }
    
    return null; // No plan found
  }
}
```

## Ollama LLM Integration

```javascript
class StrategicAI {
  constructor() {
    this.ollamaClient = new OllamaWebSocketClient();
    this.responseCache = new Map();
  }
  
  async getStrategicAdvice(gameState) {
    const stateHash = this.hashGameState(gameState);
    
    if (this.responseCache.has(stateHash)) {
      return this.responseCache.get(stateHash);
    }
    
    const prompt = this.buildStrategicPrompt(gameState);
    
    const response = await this.ollamaClient.chat({
      model: 'llama2',
      messages: [{
        role: 'system',
        content: 'You are an RTS strategy advisor. Analyze the current game state and recommend optimal base building decisions.'
      }, {
        role: 'user',
        content: prompt
      }]
    });
    
    this.responseCache.set(stateHash, response);
    return response;
  }
  
  buildStrategicPrompt(gameState) {
    return `
      Current Resources: ${gameState.credits}
      Units: ${gameState.units.length}
      Buildings: ${gameState.buildings.length}
      Enemy Threat Level: ${gameState.threatAssessment}
      Strategic Objectives: ${gameState.objectives.join(', ')}
      
      What should be the next strategic move?
    `;
  }
}
```

## Influence Maps
- Grid-based or node-based threat assessment
- Influence value propagation from key positions
- Strategic positioning optimization
- Dynamic updating based on unit movements

```javascript
class InfluenceMap {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.grid = new Float32Array(width * height);
  }
  
  addInfluence(x, y, value, falloff = 0.1) {
    const maxRadius = Math.sqrt(value / falloff);
    
    for (let dy = -maxRadius; dy <= maxRadius; dy++) {
      for (let dx = -maxRadius; dx <= maxRadius; dx++) {
        const nx = x + dx;
        const ny = y + dy;
        
        if (nx >= 0 && nx < this.width && ny >= 0 && ny < this.height) {
          const distance = Math.sqrt(dx * dx + dy * dy);
          const influence = Math.max(0, value - distance * falloff);
          const index = ny * this.width + nx;
          this.grid[index] += influence;
        }
      }
    }
  }
}
```

## Steering Behaviors
- **Seek:** Move toward target
- **Flee:** Move away from threat
- **Arrive:** Smooth deceleration at destination
- **Flocking:** Group cohesion and separation

## Visual Veterancy System
- Badge systems for experienced units
- Color coding for different experience levels
- Particle effects for elite units
- Performance bonuses tied to experience

## AI Performance Targets
- Learning convergence in < 1000 episodes
- Win rate > 40% vs human players
- Decision time < 1ms per unit
- Strategy quality validated by experts