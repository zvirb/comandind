# Economic Mechanics Research & Design for Command and Independent Thought Iteration 2
*Generated: 2025-08-19 | Schema Database Expert Agent*

## Executive Summary

This document provides comprehensive research and design for authentic Command & Conquer economic mechanics, focusing on resource management, harvester AI, construction economics, and performance optimization for multiplayer scale operations.

## 1. Current Asset Foundation Analysis

### Extracted C&C Data Integration
- **Units Data**: 6 authentic unit types with accurate costs (500-1500 credits)
- **Buildings Data**: 8 building types with realistic costs (300-5000 credits)
- **Economic Balance**: Authentic C&C pricing maintains strategic depth
- **Asset Loader**: CnCAssetLoader.js provides faction-specific texture generation
- **ECS Components**: UnitComponent and BuildingComponent include cost properties

### Key Economic Constants from C&C
```javascript
// Tiberium Resource System
const TIBERIUM_BAIL_VALUE = 25;           // Credits per bail
const HARVESTER_CAPACITY = 700;           // Total credits (28 bails)
const REFINERY_UNLOAD_TIME = 3000;        // 3 seconds unloading
const REFINERY_COST = 2000;               // Includes harvester

// Unit Cost Analysis
const UNIT_COSTS = {
  RECON_BIKE: 500,     // Fast scout
  LIGHT_TANK: 600,     // Basic combat
  MEDIUM_TANK: 800,    // Heavy assault
  STEALTH_TANK: 900,   // Special operations
  ORCA: 1200,          // Air superiority
  MAMMOTH_TANK: 1500   // Ultimate weapon
};

// Building Cost Analysis
const BUILDING_COSTS = {
  POWER_PLANT: 300,      // Essential infrastructure
  BARRACKS: 400,         // Infantry production
  REFINERY: 2000,        // Economic foundation
  OBELISK: 1500,         // Advanced defense
  CONSTRUCTION_YARD: 5000 // Base core
};
```

## 2. Resource Management System Design

### 2.1 Tiberium Field Generation System

```javascript
/**
 * TiberiumField - Spatial resource distribution with regeneration
 */
class TiberiumField {
  constructor(centerX, centerY, radius, density = 0.7) {
    this.centerX = centerX;
    this.centerY = centerY;
    this.radius = radius;
    this.density = density;
    this.chunks = new Map();  // Spatial partitioning
    this.regenerationRate = 0.1; // Bails per second
    this.maxBails = Math.floor(Math.PI * radius * radius * density / 100);
    
    this.generateField();
  }
  
  generateField() {
    const chunkSize = 64;  // 64x64 pixel chunks
    const chunks = Math.ceil(this.radius * 2 / chunkSize);
    
    for (let cx = 0; cx < chunks; cx++) {
      for (let cy = 0; cy < chunks; cy++) {
        const chunkX = this.centerX - this.radius + (cx * chunkSize);
        const chunkY = this.centerY - this.radius + (cy * chunkSize);
        
        // Distance-based density falloff
        const distance = Math.sqrt(
          Math.pow(chunkX - this.centerX, 2) + 
          Math.pow(chunkY - this.centerY, 2)
        );
        
        if (distance <= this.radius) {
          const densityMultiplier = 1 - (distance / this.radius);
          const chunkBails = Math.floor(
            (chunkSize * chunkSize / 100) * 
            this.density * 
            densityMultiplier
          );
          
          if (chunkBails > 0) {
            this.chunks.set(`${cx},${cy}`, {
              x: chunkX,
              y: chunkY,
              currentBails: chunkBails,
              maxBails: chunkBails,
              lastRegenTime: Date.now()
            });
          }
        }
      }
    }
  }
  
  /**
   * Harvest from specific location with spatial efficiency
   */
  harvest(x, y, maxAmount) {
    const chunkKey = this.getChunkKey(x, y);
    const chunk = this.chunks.get(chunkKey);
    
    if (!chunk || chunk.currentBails <= 0) {
      return 0;
    }
    
    const harvestedAmount = Math.min(maxAmount, chunk.currentBails);
    chunk.currentBails -= harvestedAmount;
    
    return harvestedAmount;
  }
  
  /**
   * Regenerate Tiberium over time
   */
  regenerate(deltaTime) {
    const regenAmount = this.regenerationRate * deltaTime;
    
    for (const chunk of this.chunks.values()) {
      if (chunk.currentBails < chunk.maxBails) {
        chunk.currentBails = Math.min(
          chunk.maxBails,
          chunk.currentBails + regenAmount
        );
      }
    }
  }
  
  getChunkKey(x, y) {
    const chunkSize = 64;
    const cx = Math.floor((x - this.centerX + this.radius) / chunkSize);
    const cy = Math.floor((y - this.centerY + this.radius) / chunkSize);
    return `${cx},${cy}`;
  }
}
```

### 2.2 Credit Accumulation and Validation

```javascript
/**
 * EconomicManager - Credit tracking and transaction validation
 */
class EconomicManager {
  constructor() {
    this.playerCredits = new Map();  // playerId -> credits
    this.transactionLog = [];        // Audit trail
    this.creditSources = new Map();  // Track credit generation
  }
  
  /**
   * Initialize player economy
   */
  initializePlayer(playerId, startingCredits = 10000) {
    this.playerCredits.set(playerId, startingCredits);
    this.logTransaction(playerId, 'INITIAL', startingCredits, 'Game start');
  }
  
  /**
   * Add credits with source tracking
   */
  addCredits(playerId, amount, source = 'UNKNOWN') {
    if (amount <= 0) return false;
    
    const currentCredits = this.getCredits(playerId);
    const newTotal = currentCredits + amount;
    
    this.playerCredits.set(playerId, newTotal);
    this.logTransaction(playerId, 'CREDIT', amount, source);
    
    return true;
  }
  
  /**
   * Spend credits with validation
   */
  spendCredits(playerId, amount, purpose = 'UNKNOWN') {
    if (amount <= 0) return false;
    
    const currentCredits = this.getCredits(playerId);
    if (currentCredits < amount) {
      console.warn(`Insufficient credits: ${currentCredits} < ${amount}`);
      return false;
    }
    
    const newTotal = currentCredits - amount;
    this.playerCredits.set(playerId, newTotal);
    this.logTransaction(playerId, 'DEBIT', -amount, purpose);
    
    return true;
  }
  
  /**
   * Get current credits
   */
  getCredits(playerId) {
    return this.playerCredits.get(playerId) || 0;
  }
  
  /**
   * Transaction logging for debugging and anti-cheat
   */
  logTransaction(playerId, type, amount, description) {
    this.transactionLog.push({
      timestamp: Date.now(),
      playerId,
      type,
      amount,
      description,
      balanceAfter: this.getCredits(playerId)
    });
    
    // Keep last 1000 transactions
    if (this.transactionLog.length > 1000) {
      this.transactionLog.shift();
    }
  }
  
  /**
   * Economic metrics for balance analysis
   */
  getEconomicMetrics(playerId) {
    const recentTransactions = this.transactionLog
      .filter(t => t.playerId === playerId)
      .slice(-100);
      
    const income = recentTransactions
      .filter(t => t.type === 'CREDIT')
      .reduce((sum, t) => sum + t.amount, 0);
      
    const expenses = recentTransactions
      .filter(t => t.type === 'DEBIT')
      .reduce((sum, t) => sum + Math.abs(t.amount), 0);
      
    return {
      currentCredits: this.getCredits(playerId),
      recentIncome: income,
      recentExpenses: expenses,
      netGain: income - expenses,
      transactionCount: recentTransactions.length
    };
  }
}
```

## 3. Harvester AI State Machine Design

### 3.1 Advanced State Machine Implementation

```javascript
/**
 * HarvesterAI - Sophisticated harvester behavior with pathfinding
 */
class HarvesterAI extends Component {
  constructor() {
    super();
    this.state = 'IDLE';
    this.subState = null;
    this.currentCredits = 0;
    this.maxCapacity = 700;
    this.harvestRate = 25;  // Credits per second
    this.assignedRefinery = null;
    this.targetField = null;
    this.targetChunk = null;
    this.pathfinder = null;
    
    // State timers
    this.stateEnterTime = Date.now();
    this.harvestStartTime = 0;
    this.unloadStartTime = 0;
    
    // Performance tracking
    this.totalHarvested = 0;
    this.tripsCompleted = 0;
    this.efficiencyScore = 1.0;
  }
  
  /**
   * Main state machine update
   */
  update(deltaTime, worldContext) {
    const prevState = this.state;
    
    switch (this.state) {
      case 'IDLE':
        this.handleIdleState(worldContext);
        break;
        
      case 'SEEKING_FIELD':
        this.handleSeekingFieldState(worldContext);
        break;
        
      case 'MOVING_TO_FIELD':
        this.handleMovingToFieldState(worldContext);
        break;
        
      case 'HARVESTING':
        this.handleHarvestingState(deltaTime, worldContext);
        break;
        
      case 'RETURNING_TO_REFINERY':
        this.handleReturningState(worldContext);
        break;
        
      case 'UNLOADING':
        this.handleUnloadingState(deltaTime, worldContext);
        break;
        
      case 'BLOCKED':
        this.handleBlockedState(worldContext);
        break;
    }
    
    // State change logging
    if (prevState !== this.state) {
      console.log(`Harvester ${this.entity.id}: ${prevState} -> ${this.state}`);
      this.stateEnterTime = Date.now();
    }
  }
  
  /**
   * IDLE - Waiting for assignment or field discovery
   */
  handleIdleState(worldContext) {
    if (!this.assignedRefinery) {
      this.assignedRefinery = this.findNearestRefinery(worldContext);
    }
    
    if (this.assignedRefinery) {
      this.transitionTo('SEEKING_FIELD');
    }
  }
  
  /**
   * SEEKING_FIELD - Find optimal Tiberium field
   */
  handleSeekingFieldState(worldContext) {
    const bestField = this.findOptimalTiberiumField(worldContext);
    
    if (bestField) {
      this.targetField = bestField.field;
      this.targetChunk = bestField.chunk;
      this.transitionTo('MOVING_TO_FIELD');
    } else {
      // No fields available, wait and retry
      setTimeout(() => {
        if (this.state === 'SEEKING_FIELD') {
          this.handleSeekingFieldState(worldContext);
        }
      }, 2000);
    }
  }
  
  /**
   * MOVING_TO_FIELD - Navigate to Tiberium field
   */
  handleMovingToFieldState(worldContext) {
    const movement = this.entity.getComponent(MovementComponent);
    const transform = this.entity.getComponent(TransformComponent);
    
    if (!movement.isMoving) {
      // Calculate path to field
      const targetX = this.targetChunk.x + 32; // Center of chunk
      const targetY = this.targetChunk.y + 32;
      
      const path = this.pathfinder.findPath(
        transform.x, transform.y,
        targetX, targetY,
        worldContext.navigationMesh
      );
      
      if (path.length > 0) {
        movement.setPath(path);
      } else {
        this.transitionTo('BLOCKED');
        return;
      }
    }
    
    // Check if arrived at field
    const distanceToTarget = Math.sqrt(
      Math.pow(transform.x - (this.targetChunk.x + 32), 2) +
      Math.pow(transform.y - (this.targetChunk.y + 32), 2)
    );
    
    if (distanceToTarget < 48) {
      movement.stop();
      this.harvestStartTime = Date.now();
      this.transitionTo('HARVESTING');
    }
  }
  
  /**
   * HARVESTING - Extract Tiberium from field
   */
  handleHarvestingState(deltaTime, worldContext) {
    const harvestAmount = this.harvestRate * deltaTime;
    const spaceRemaining = this.maxCapacity - this.currentCredits;
    const actualHarvest = Math.min(harvestAmount, spaceRemaining);
    
    if (actualHarvest > 0) {
      const harvested = this.targetField.harvest(
        this.targetChunk.x + 32,
        this.targetChunk.y + 32,
        actualHarvest / 25  // Convert credits to bails
      );
      
      const creditsHarvested = harvested * 25;
      this.currentCredits += creditsHarvested;
      this.totalHarvested += creditsHarvested;
      
      // Visual feedback
      this.showHarvestEffect(creditsHarvested);
    }
    
    // Check completion conditions
    if (this.currentCredits >= this.maxCapacity) {
      this.transitionTo('RETURNING_TO_REFINERY');
    } else if (this.targetField.getBailsAt(this.targetChunk.x, this.targetChunk.y) <= 0) {
      this.transitionTo('SEEKING_FIELD');
    }
  }
  
  /**
   * RETURNING_TO_REFINERY - Navigate back to refinery
   */
  handleReturningState(worldContext) {
    const movement = this.entity.getComponent(MovementComponent);
    const transform = this.entity.getComponent(TransformComponent);
    
    if (!movement.isMoving) {
      const refineryTransform = this.assignedRefinery.getComponent(TransformComponent);
      
      const path = this.pathfinder.findPath(
        transform.x, transform.y,
        refineryTransform.x, refineryTransform.y,
        worldContext.navigationMesh
      );
      
      if (path.length > 0) {
        movement.setPath(path);
      } else {
        this.transitionTo('BLOCKED');
        return;
      }
    }
    
    // Check if arrived at refinery
    const refineryTransform = this.assignedRefinery.getComponent(TransformComponent);
    const distanceToRefinery = Math.sqrt(
      Math.pow(transform.x - refineryTransform.x, 2) +
      Math.pow(transform.y - refineryTransform.y, 2)
    );
    
    if (distanceToRefinery < 64) {
      movement.stop();
      this.unloadStartTime = Date.now();
      this.transitionTo('UNLOADING');
    }
  }
  
  /**
   * UNLOADING - Transfer credits to player account
   */
  handleUnloadingState(deltaTime, worldContext) {
    const unloadDuration = 3000; // 3 seconds
    const elapsedTime = Date.now() - this.unloadStartTime;
    
    if (elapsedTime >= unloadDuration) {
      // Transfer credits to player
      const playerId = this.entity.getComponent(UnitComponent).playerId;
      worldContext.economicManager.addCredits(
        playerId, 
        this.currentCredits, 
        'HARVESTER_UNLOAD'
      );
      
      // Reset harvester
      this.currentCredits = 0;
      this.tripsCompleted++;
      this.updateEfficiencyScore();
      
      this.transitionTo('SEEKING_FIELD');
    }
  }
  
  /**
   * BLOCKED - Handle pathfinding failures and obstacles
   */
  handleBlockedState(worldContext) {
    const blockedDuration = Date.now() - this.stateEnterTime;
    
    if (blockedDuration > 5000) { // 5 seconds
      // Try alternative strategies
      this.targetField = null;
      this.targetChunk = null;
      this.transitionTo('SEEKING_FIELD');
    } else {
      // Wait for obstacle to clear
      setTimeout(() => {
        if (this.state === 'BLOCKED') {
          this.transitionTo('SEEKING_FIELD');
        }
      }, 1000);
    }
  }
  
  /**
   * Find optimal Tiberium field based on distance and density
   */
  findOptimalTiberiumField(worldContext) {
    const transform = this.entity.getComponent(TransformComponent);
    const tiberiumFields = worldContext.resourceManager.getTiberiumFields();
    
    let bestScore = -1;
    let bestField = null;
    let bestChunk = null;
    
    for (const field of tiberiumFields) {
      for (const [chunkKey, chunk] of field.chunks) {
        if (chunk.currentBails <= 0) continue;
        
        const distance = Math.sqrt(
          Math.pow(transform.x - chunk.x, 2) +
          Math.pow(transform.y - chunk.y, 2)
        );
        
        // Score = density / distance (higher is better)
        const score = chunk.currentBails / (distance + 1);
        
        if (score > bestScore) {
          bestScore = score;
          bestField = field;
          bestChunk = chunk;
        }
      }
    }
    
    return bestField ? { field: bestField, chunk: bestChunk, score: bestScore } : null;
  }
  
  /**
   * Calculate efficiency metrics
   */
  updateEfficiencyScore() {
    const avgCreditsPerTrip = this.totalHarvested / Math.max(this.tripsCompleted, 1);
    const targetCreditsPerTrip = 700; // Full capacity
    
    this.efficiencyScore = Math.min(1.0, avgCreditsPerTrip / targetCreditsPerTrip);
  }
  
  transitionTo(newState) {
    this.state = newState;
    this.subState = null;
  }
}
```

### 3.2 Pathfinding Integration

```javascript
/**
 * HarvesterPathfinder - Optimized pathfinding for economic units
 */
class HarvesterPathfinder {
  constructor() {
    this.cache = new Map(); // Path caching for performance
    this.cacheTimeout = 30000; // 30 seconds
  }
  
  /**
   * Find path with caching and optimization
   */
  findPath(startX, startY, endX, endY, navigationMesh) {
    const cacheKey = `${Math.floor(startX/32)},${Math.floor(startY/32)}-${Math.floor(endX/32)},${Math.floor(endY/32)}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
      return cached.path;
    }
    
    // A* pathfinding with economic unit preferences
    const path = this.aStarPath(startX, startY, endX, endY, navigationMesh);
    
    // Cache the result
    this.cache.set(cacheKey, {
      path: path,
      timestamp: Date.now()
    });
    
    return path;
  }
  
  /**
   * A* implementation optimized for harvesters
   */
  aStarPath(startX, startY, endX, endY, navigationMesh) {
    // Simplified A* implementation
    // Prefer paths that avoid combat zones and congested areas
    
    const nodeSize = 32;
    const startNode = { 
      x: Math.floor(startX / nodeSize), 
      y: Math.floor(startY / nodeSize),
      g: 0,
      h: this.heuristic(startX, startY, endX, endY),
      f: 0,
      parent: null
    };
    
    const endNode = {
      x: Math.floor(endX / nodeSize),
      y: Math.floor(endY / nodeSize)
    };
    
    startNode.f = startNode.g + startNode.h;
    
    const openList = [startNode];
    const closedList = new Set();
    
    while (openList.length > 0) {
      // Get node with lowest f score
      openList.sort((a, b) => a.f - b.f);
      const current = openList.shift();
      
      // Check if reached destination
      if (current.x === endNode.x && current.y === endNode.y) {
        return this.reconstructPath(current);
      }
      
      closedList.add(`${current.x},${current.y}`);
      
      // Explore neighbors
      for (const neighbor of this.getNeighbors(current, navigationMesh)) {
        const neighborKey = `${neighbor.x},${neighbor.y}`;
        
        if (closedList.has(neighborKey)) continue;
        
        const existingNode = openList.find(n => n.x === neighbor.x && n.y === neighbor.y);
        
        if (!existingNode) {
          neighbor.g = current.g + this.getMoveCost(current, neighbor);
          neighbor.h = this.heuristic(neighbor.x * nodeSize, neighbor.y * nodeSize, endX, endY);
          neighbor.f = neighbor.g + neighbor.h;
          neighbor.parent = current;
          openList.push(neighbor);
        } else if (neighbor.g < existingNode.g) {
          existingNode.g = neighbor.g;
          existingNode.f = existingNode.g + existingNode.h;
          existingNode.parent = current;
        }
      }
    }
    
    return []; // No path found
  }
  
  heuristic(x1, y1, x2, y2) {
    return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
  }
  
  getMoveCost(from, to) {
    // Base cost is distance
    let cost = Math.sqrt(Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2));
    
    // Add penalties for dangerous areas
    // (to be implemented based on game state)
    
    return cost;
  }
  
  reconstructPath(endNode) {
    const path = [];
    let current = endNode;
    
    while (current.parent) {
      path.unshift({ x: current.x * 32, y: current.y * 32 });
      current = current.parent;
    }
    
    return path;
  }
  
  getNeighbors(node, navigationMesh) {
    const neighbors = [];
    const directions = [
      [-1, -1], [-1, 0], [-1, 1],
      [0, -1],           [0, 1],
      [1, -1],  [1, 0],  [1, 1]
    ];
    
    for (const [dx, dy] of directions) {
      const x = node.x + dx;
      const y = node.y + dy;
      
      // Check bounds and passability
      if (this.isPassable(x, y, navigationMesh)) {
        neighbors.push({ x, y });
      }
    }
    
    return neighbors;
  }
  
  isPassable(x, y, navigationMesh) {
    // Check if position is passable for harvesters
    return navigationMesh.isPassable(x, y, 'harvester');
  }
}
```

## 4. Building Construction Economics

### 4.1 Construction Validation System

```javascript
/**
 * ConstructionManager - Building placement and economic validation
 */
class ConstructionManager {
  constructor(economicManager) {
    this.economicManager = economicManager;
    this.constructionQueue = new Map(); // playerId -> queue
    this.buildingPlacements = new Map(); // Track building positions
    this.techTree = new TechTree();
  }
  
  /**
   * Validate building construction request
   */
  canConstruct(playerId, buildingType, x, y) {
    const validation = {
      valid: true,
      errors: []
    };
    
    // Economic validation
    const buildingInfo = this.getBuildingInfo(buildingType);
    if (!buildingInfo) {
      validation.valid = false;
      validation.errors.push('Invalid building type');
      return validation;
    }
    
    const playerCredits = this.economicManager.getCredits(playerId);
    if (playerCredits < buildingInfo.cost) {
      validation.valid = false;
      validation.errors.push(`Insufficient credits: ${playerCredits} < ${buildingInfo.cost}`);
    }
    
    // Power validation
    const powerStatus = this.calculatePowerStatus(playerId);
    if (buildingInfo.power < 0 && (powerStatus.available + buildingInfo.power) < 0) {
      validation.valid = false;
      validation.errors.push('Insufficient power');
    }
    
    // Tech tree validation
    if (!this.techTree.canBuild(playerId, buildingType)) {
      validation.valid = false;
      validation.errors.push('Prerequisites not met');
    }
    
    // Placement validation
    if (!this.isValidPlacement(playerId, buildingType, x, y)) {
      validation.valid = false;
      validation.errors.push('Invalid placement location');
    }
    
    return validation;
  }
  
  /**
   * Start building construction
   */
  startConstruction(playerId, buildingType, x, y) {
    const validation = this.canConstruct(playerId, buildingType, x, y);
    
    if (!validation.valid) {
      console.warn(`Construction failed: ${validation.errors.join(', ')}`);
      return null;
    }
    
    const buildingInfo = this.getBuildingInfo(buildingType);
    
    // Deduct credits
    this.economicManager.spendCredits(
      playerId, 
      buildingInfo.cost, 
      `CONSTRUCT_${buildingType}`
    );
    
    // Create construction entity
    const constructionId = this.generateConstructionId();
    const construction = {
      id: constructionId,
      playerId,
      buildingType,
      x,
      y,
      startTime: Date.now(),
      buildTime: buildingInfo.buildTime || 10000, // 10 seconds default
      progress: 0,
      cost: buildingInfo.cost
    };
    
    // Add to queue
    let queue = this.constructionQueue.get(playerId);
    if (!queue) {
      queue = [];
      this.constructionQueue.set(playerId, queue);
    }
    queue.push(construction);
    
    console.log(`Started construction: ${buildingType} for player ${playerId}`);
    return constructionId;
  }
  
  /**
   * Update construction progress
   */
  updateConstruction(deltaTime) {
    for (const [playerId, queue] of this.constructionQueue) {
      for (let i = queue.length - 1; i >= 0; i--) {
        const construction = queue[i];
        const elapsed = Date.now() - construction.startTime;
        construction.progress = Math.min(1.0, elapsed / construction.buildTime);
        
        // Check if construction completed
        if (construction.progress >= 1.0) {
          this.completeConstruction(construction);
          queue.splice(i, 1);
        }
      }
    }
  }
  
  /**
   * Complete building construction
   */
  completeConstruction(construction) {
    const buildingInfo = this.getBuildingInfo(construction.buildingType);
    
    // Create building entity
    const building = this.createBuildingEntity(
      construction.buildingType,
      construction.x,
      construction.y,
      construction.playerId
    );
    
    // Update tech tree
    this.techTree.onBuildingCompleted(construction.playerId, construction.buildingType);
    
    // Special building effects
    if (construction.buildingType.includes('REFINERY')) {
      this.createHarvester(construction.x + 64, construction.y, construction.playerId);
    }
    
    console.log(`Construction completed: ${construction.buildingType}`);
    return building;
  }
  
  /**
   * Calculate power status for player
   */
  calculatePowerStatus(playerId) {
    const buildings = this.getPlayerBuildings(playerId);
    let generated = 0;
    let consumed = 0;
    
    for (const building of buildings) {
      const buildingInfo = this.getBuildingInfo(building.buildingType);
      if (buildingInfo.power > 0) {
        generated += buildingInfo.power;
      } else {
        consumed += Math.abs(buildingInfo.power);
      }
    }
    
    return {
      generated,
      consumed,
      available: generated - consumed,
      efficiency: generated > 0 ? Math.min(1.0, generated / consumed) : 0
    };
  }
  
  /**
   * Validate building placement
   */
  isValidPlacement(playerId, buildingType, x, y) {
    const buildingInfo = this.getBuildingInfo(buildingType);
    const width = buildingInfo.width || 48;
    const height = buildingInfo.height || 48;
    
    // Check for overlaps with existing buildings
    for (const [_, placement] of this.buildingPlacements) {
      if (this.rectanglesOverlap(
        x, y, width, height,
        placement.x, placement.y, placement.width, placement.height
      )) {
        return false;
      }
    }
    
    // Check terrain suitability
    // (to be implemented based on terrain system)
    
    // Check minimum distance from enemy buildings
    const enemyBuildings = this.getEnemyBuildings(playerId);
    for (const enemyBuilding of enemyBuildings) {
      const distance = Math.sqrt(
        Math.pow(x - enemyBuilding.x, 2) + Math.pow(y - enemyBuilding.y, 2)
      );
      if (distance < 100) { // Minimum 100 pixel separation
        return false;
      }
    }
    
    return true;
  }
  
  rectanglesOverlap(x1, y1, w1, h1, x2, y2, w2, h2) {
    return !(x1 + w1 < x2 || x2 + w2 < x1 || y1 + h1 < y2 || y2 + h2 < y1);
  }
  
  getBuildingInfo(buildingType) {
    // Integration with CnCAssetLoader
    return window.gameInstance?.cncAssets?.getBuildingInfo(buildingType);
  }
  
  generateConstructionId() {
    return `const_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### 4.2 Technology Tree System

```javascript
/**
 * TechTree - Building prerequisites and faction progression
 */
class TechTree {
  constructor() {
    this.playerProgress = new Map(); // playerId -> tech state
    this.prerequisites = this.initializePrerequisites();
  }
  
  initializePrerequisites() {
    return {
      // GDI Tech Tree
      'GDI_CONSTRUCTION_YARD': [],
      'GDI_POWER_PLANT': ['GDI_CONSTRUCTION_YARD'],
      'GDI_BARRACKS': ['GDI_CONSTRUCTION_YARD', 'GDI_POWER_PLANT'],
      'GDI_REFINERY': ['GDI_CONSTRUCTION_YARD', 'GDI_POWER_PLANT'],
      'GDI_WEAPONS_FACTORY': ['GDI_CONSTRUCTION_YARD', 'GDI_POWER_PLANT', 'GDI_REFINERY'],
      'GDI_COMMUNICATIONS_CENTER': ['GDI_BARRACKS'],
      'GDI_ADVANCED_GUARD_TOWER': ['GDI_BARRACKS'],
      
      // NOD Tech Tree
      'NOD_CONSTRUCTION_YARD': [],
      'NOD_POWER_PLANT': ['NOD_CONSTRUCTION_YARD'],
      'NOD_HAND_OF_NOD': ['NOD_CONSTRUCTION_YARD', 'NOD_POWER_PLANT'],
      'NOD_REFINERY': ['NOD_CONSTRUCTION_YARD', 'NOD_POWER_PLANT'],
      'NOD_AIRSTRIP': ['NOD_CONSTRUCTION_YARD', 'NOD_POWER_PLANT', 'NOD_REFINERY'],
      'NOD_OBELISK': ['NOD_HAND_OF_NOD', 'NOD_POWER_PLANT'],
      'NOD_TEMPLE_OF_NOD': ['NOD_OBELISK']
    };
  }
  
  /**
   * Initialize player tech progress
   */
  initializePlayer(playerId, faction) {
    this.playerProgress.set(playerId, {
      faction,
      completedBuildings: new Set(),
      availableBuildings: new Set([`${faction}_CONSTRUCTION_YARD`])
    });
  }
  
  /**
   * Check if player can build specific building type
   */
  canBuild(playerId, buildingType) {
    const progress = this.playerProgress.get(playerId);
    if (!progress) return false;
    
    return progress.availableBuildings.has(buildingType);
  }
  
  /**
   * Update tech tree when building is completed
   */
  onBuildingCompleted(playerId, buildingType) {
    const progress = this.playerProgress.get(playerId);
    if (!progress) return;
    
    progress.completedBuildings.add(buildingType);
    
    // Check what new buildings become available
    for (const [building, prereqs] of Object.entries(this.prerequisites)) {
      if (progress.availableBuildings.has(building)) continue;
      
      // Check if all prerequisites are met
      const canUnlock = prereqs.every(prereq => 
        progress.completedBuildings.has(prereq)
      );
      
      if (canUnlock) {
        progress.availableBuildings.add(building);
        console.log(`Tech unlocked for player ${playerId}: ${building}`);
      }
    }
  }
  
  /**
   * Get available buildings for player
   */
  getAvailableBuildings(playerId) {
    const progress = this.playerProgress.get(playerId);
    return progress ? Array.from(progress.availableBuildings) : [];
  }
  
  /**
   * Get tech progress for UI display
   */
  getTechProgress(playerId) {
    const progress = this.playerProgress.get(playerId);
    if (!progress) return null;
    
    return {
      faction: progress.faction,
      completed: Array.from(progress.completedBuildings),
      available: Array.from(progress.availableBuildings),
      locked: Object.keys(this.prerequisites).filter(building => 
        !progress.availableBuildings.has(building) && 
        !progress.completedBuildings.has(building)
      )
    };
  }
}
```

## 5. Performance Optimization Strategies

### 5.1 Efficient Economic Data Structures

```javascript
/**
 * Economic Component System optimized for scale
 */
class EconomicComponent extends Component {
  constructor(playerId) {
    super();
    this.playerId = playerId;
    this.credits = 0;
    this.income = 0;
    this.expenses = 0;
    this.lastUpdate = Date.now();
  }
}

/**
 * Economic System - Batch processing for performance
 */
class EconomicSystem {
  constructor() {
    this.updateInterval = 100; // Update every 100ms
    this.batchSize = 50; // Process 50 entities per batch
    this.lastUpdate = Date.now();
    this.economicEntities = [];
    this.processIndex = 0;
  }
  
  /**
   * Batch update economic entities
   */
  update(deltaTime, entities) {
    const now = Date.now();
    if (now - this.lastUpdate < this.updateInterval) return;
    
    // Collect all entities with economic components
    this.economicEntities = entities.filter(entity => 
      entity.hasComponent(EconomicComponent)
    );
    
    // Process in batches to avoid frame drops
    const endIndex = Math.min(
      this.processIndex + this.batchSize,
      this.economicEntities.length
    );
    
    for (let i = this.processIndex; i < endIndex; i++) {
      this.updateEconomicEntity(this.economicEntities[i], deltaTime);
    }
    
    this.processIndex = endIndex;
    
    // Reset batch if completed
    if (this.processIndex >= this.economicEntities.length) {
      this.processIndex = 0;
      this.lastUpdate = now;
    }
  }
  
  updateEconomicEntity(entity, deltaTime) {
    const economic = entity.getComponent(EconomicComponent);
    
    // Update resource generation/consumption
    if (entity.hasComponent(BuildingComponent)) {
      const building = entity.getComponent(BuildingComponent);
      
      // Power plants generate income
      if (building.buildingType.includes('POWER_PLANT')) {
        economic.income += 10 * deltaTime; // 10 credits per second
      }
      
      // Other buildings consume power (cost)
      if (building.powerRequired > 0) {
        economic.expenses += building.powerRequired * 0.1 * deltaTime;
      }
    }
    
    // Apply income/expense changes
    economic.credits += (economic.income - economic.expenses) * deltaTime;
  }
}
```

### 5.2 Resource Field Optimization

```javascript
/**
 * Optimized resource management with spatial indexing
 */
class ResourceManager {
  constructor() {
    this.spatialGrid = new SpatialGrid(128); // 128x128 grid cells
    this.tiberiumFields = [];
    this.updateBatch = [];
    this.batchSize = 20;
    this.lastUpdateIndex = 0;
  }
  
  /**
   * Add Tiberium field with spatial indexing
   */
  addTiberiumField(field) {
    this.tiberiumFields.push(field);
    
    // Index all chunks in spatial grid
    for (const [chunkKey, chunk] of field.chunks) {
      this.spatialGrid.insert(chunk.x, chunk.y, {
        type: 'tiberium',
        field: field,
        chunk: chunk
      });
    }
  }
  
  /**
   * Efficient harvesting with spatial queries
   */
  harvestNear(x, y, radius, maxAmount) {
    const nearby = this.spatialGrid.queryRadius(x, y, radius);
    let totalHarvested = 0;
    
    for (const item of nearby) {
      if (item.type === 'tiberium' && totalHarvested < maxAmount) {
        const harvestAmount = Math.min(
          maxAmount - totalHarvested,
          item.chunk.currentBails
        );
        
        if (harvestAmount > 0) {
          item.chunk.currentBails -= harvestAmount;
          totalHarvested += harvestAmount;
        }
      }
    }
    
    return totalHarvested;
  }
  
  /**
   * Batch update Tiberium regeneration
   */
  update(deltaTime) {
    const fieldsToUpdate = Math.min(
      this.batchSize,
      this.tiberiumFields.length
    );
    
    for (let i = 0; i < fieldsToUpdate; i++) {
      const fieldIndex = (this.lastUpdateIndex + i) % this.tiberiumFields.length;
      this.tiberiumFields[fieldIndex].regenerate(deltaTime);
    }
    
    this.lastUpdateIndex = (this.lastUpdateIndex + fieldsToUpdate) % this.tiberiumFields.length;
  }
}

/**
 * Spatial Grid for efficient spatial queries
 */
class SpatialGrid {
  constructor(cellSize) {
    this.cellSize = cellSize;
    this.grid = new Map();
  }
  
  insert(x, y, item) {
    const cellX = Math.floor(x / this.cellSize);
    const cellY = Math.floor(y / this.cellSize);
    const cellKey = `${cellX},${cellY}`;
    
    if (!this.grid.has(cellKey)) {
      this.grid.set(cellKey, []);
    }
    
    this.grid.get(cellKey).push({
      x, y, item
    });
  }
  
  queryRadius(x, y, radius) {
    const results = [];
    const cellRadius = Math.ceil(radius / this.cellSize);
    const centerCellX = Math.floor(x / this.cellSize);
    const centerCellY = Math.floor(y / this.cellSize);
    
    for (let dx = -cellRadius; dx <= cellRadius; dx++) {
      for (let dy = -cellRadius; dy <= cellRadius; dy++) {
        const cellKey = `${centerCellX + dx},${centerCellY + dy}`;
        const cell = this.grid.get(cellKey);
        
        if (cell) {
          for (const entry of cell) {
            const distance = Math.sqrt(
              Math.pow(entry.x - x, 2) + Math.pow(entry.y - y, 2)
            );
            
            if (distance <= radius) {
              results.push(entry.item);
            }
          }
        }
      }
    }
    
    return results;
  }
}
```

## 6. Integration with Existing Codebase

### 6.1 ECS Component Extensions

```javascript
/**
 * Extended components for economic system
 */

// Add to Component.js
export class ResourceComponent extends Component {
  constructor(resourceType, amount, maxAmount = null) {
    super();
    this.resourceType = resourceType; // 'tiberium', 'power', etc.
    this.amount = amount;
    this.maxAmount = maxAmount || amount;
    this.regenerationRate = 0;
    this.harvestable = true;
  }
  
  harvest(amount) {
    const harvestAmount = Math.min(amount, this.amount);
    this.amount -= harvestAmount;
    return harvestAmount;
  }
  
  regenerate(deltaTime) {
    if (this.regenerationRate > 0 && this.amount < this.maxAmount) {
      this.amount = Math.min(
        this.maxAmount,
        this.amount + this.regenerationRate * deltaTime
      );
    }
  }
}

export class ConstructionComponent extends Component {
  constructor(buildingType, buildTime, cost) {
    super();
    this.buildingType = buildingType;
    this.buildTime = buildTime;
    this.cost = cost;
    this.startTime = Date.now();
    this.progress = 0;
    this.paused = false;
  }
  
  getProgress() {
    if (this.paused) return this.progress;
    
    const elapsed = Date.now() - this.startTime;
    return Math.min(1.0, elapsed / this.buildTime);
  }
  
  isComplete() {
    return this.getProgress() >= 1.0;
  }
}

// Extend existing UnitComponent
UnitComponent.prototype.setPlayerControlled = function(playerId) {
  this.playerId = playerId;
  this.playerControlled = playerId !== null;
};

// Extend existing BuildingComponent
BuildingComponent.prototype.setPowerValues = function(powerOutput, powerRequired) {
  this.powerOutput = powerOutput || 0;
  this.powerRequired = powerRequired || 0;
};
```

### 6.2 Entity Factory Extensions

```javascript
/**
 * Extensions to EntityFactory for economic entities
 */

// Add to EntityFactory.js
EntityFactory.prototype.createHarvester = function(x, y, playerId, refinery = null) {
  const harvester = this.createUnit('HARVESTER', x, y, 'gdi'); // Adjust faction as needed
  
  if (harvester) {
    // Add harvester-specific components
    harvester.addComponent(new HarvesterAI());
    harvester.addComponent(new ResourceComponent('credits', 0, 700));
    
    const unitComp = harvester.getComponent(UnitComponent);
    unitComp.setPlayerControlled(playerId);
    
    const harvesterAI = harvester.getComponent(HarvesterAI);
    harvesterAI.assignedRefinery = refinery;
    harvesterAI.pathfinder = new HarvesterPathfinder();
    
    console.log(`Created harvester for player ${playerId} at (${x}, ${y})`);
  }
  
  return harvester;
};

EntityFactory.prototype.createTiberiumField = function(centerX, centerY, radius, density = 0.7) {
  const field = new TiberiumField(centerX, centerY, radius, density);
  
  // Create visual entities for each Tiberium chunk
  for (const [chunkKey, chunk] of field.chunks) {
    if (chunk.currentBails > 0) {
      const tiberiumEntity = this.world.createEntity();
      
      tiberiumEntity.addComponent(new TransformComponent(chunk.x + 16, chunk.y + 16));
      tiberiumEntity.addComponent(new SpriteComponent(this.cncAssets.getTexture('tiberium_green')));
      tiberiumEntity.addComponent(new ResourceComponent('tiberium', chunk.currentBails, chunk.maxBails));
      
      // Link entity to chunk for updates
      chunk.entity = tiberiumEntity;
    }
  }
  
  console.log(`Created Tiberium field at (${centerX}, ${centerY}) with ${field.chunks.size} chunks`);
  return field;
};

EntityFactory.prototype.createRefinery = function(x, y, playerId, faction = 'gdi') {
  const refinery = this.createBuilding(`${faction.toUpperCase()}_REFINERY`, x, y, faction);
  
  if (refinery) {
    const buildingComp = refinery.getComponent(BuildingComponent);
    buildingComp.setPowerValues(0, -40); // Consumes 40 power
    
    const unitComp = new UnitComponent('REFINERY', faction, 2000);
    unitComp.setPlayerControlled(playerId);
    refinery.addComponent(unitComp);
    
    // Create included harvester
    const harvester = this.createHarvester(x + 64, y, playerId, refinery);
    
    console.log(`Created refinery for player ${playerId} with included harvester`);
  }
  
  return refinery;
};
```

## 7. Economic Balance Recommendations

### 7.1 Authentic C&C Economic Ratios

```javascript
/**
 * Economic balance constants based on C&C analysis
 */
const ECONOMIC_BALANCE = {
  // Resource generation
  TIBERIUM_BAIL_VALUE: 25,
  HARVESTER_CAPACITY_BAILS: 28,
  HARVESTER_CAPACITY_CREDITS: 700,
  HARVEST_RATE_PER_SECOND: 25, // 1 bail per second
  REFINERY_UNLOAD_TIME: 3000,  // 3 seconds
  
  // Building costs maintain strategic depth
  EARLY_GAME_COSTS: {
    POWER_PLANT: 300,    // 12 bails, essential infrastructure
    BARRACKS: 400,       // 16 bails, unit production
    REFINERY: 2000       // 80 bails, economic investment
  },
  
  // Unit costs create meaningful choices
  UNIT_COST_TIERS: {
    SCOUT: 500,          // 20 bails, fast intel
    BASIC_COMBAT: 600,   // 24 bails, core army
    HEAVY_COMBAT: 800,   // 32 bails, breakthrough
    ADVANCED: 1200,      // 48 bails, specialized
    ULTIMATE: 1500       // 60 bails, game-changing
  },
  
  // Economic timing
  HARVESTER_ROUND_TRIP: 45000,  // 45 seconds average
  CREDITS_PER_MINUTE: 933,      // 700 credits / 45 seconds * 60
  BREAK_EVEN_TIME: {
    REFINERY: 128,              // 128 seconds to pay for itself
    SECOND_HARVESTER: 75        // 75 seconds additional payback
  }
};
```

### 7.2 Performance Benchmarks

```javascript
/**
 * Performance targets for economic system
 */
const PERFORMANCE_TARGETS = {
  // Update frequencies
  HARVESTER_AI_UPDATE: 100,     // 10 Hz for responsive behavior
  RESOURCE_REGENERATION: 1000,  // 1 Hz for Tiberium growth
  CREDIT_CALCULATION: 50,       // 20 Hz for accurate accumulation
  
  // Batch processing limits
  MAX_HARVESTERS_PER_FRAME: 50,
  MAX_BUILDINGS_PER_FRAME: 100,
  MAX_RESOURCE_CHUNKS_PER_FRAME: 200,
  
  // Memory optimization
  TRANSACTION_LOG_LIMIT: 1000,
  PATH_CACHE_SIZE: 500,
  SPATIAL_GRID_CELL_SIZE: 128,
  
  // Network optimization (multiplayer)
  ECONOMIC_SYNC_INTERVAL: 1000,  // 1 second
  TRANSACTION_BATCH_SIZE: 50,
  DELTA_COMPRESSION: true
};
```

## 8. Implementation Roadmap

### Phase 1: Core Economic Infrastructure (Week 1)
1. **EconomicManager** implementation with credit tracking
2. **TiberiumField** system with spatial partitioning
3. **ResourceComponent** and **ConstructionComponent** additions
4. Basic credit accumulation and spending validation

### Phase 2: Harvester AI System (Week 2)
1. **HarvesterAI** state machine implementation
2. **HarvesterPathfinder** with A* and caching
3. Integration with existing MovementComponent
4. Basic harvesting and unloading behaviors

### Phase 3: Construction Economics (Week 3)
1. **ConstructionManager** with validation systems
2. **TechTree** implementation for building prerequisites
3. Power system integration
4. Building placement validation

### Phase 4: Performance Optimization (Week 4)
1. **EconomicSystem** batch processing
2. **SpatialGrid** optimization for resource queries
3. Performance monitoring and benchmarking
4. Memory usage optimization

### Phase 5: Integration and Testing (Week 5)
1. EntityFactory extensions for economic entities
2. UI integration for economic displays
3. Multiplayer synchronization
4. Balance testing and adjustment

## 9. Success Metrics

### Economic Accuracy
- ✅ Maintain authentic C&C credit values and ratios
- ✅ Harvester capacity exactly 700 credits (28 bails)
- ✅ Building costs match original strategic depth
- ✅ Resource generation rates provide meaningful choices

### Performance Targets
- ✅ Support 50+ harvesters simultaneously at 60 FPS
- ✅ Economic calculations under 5ms per frame
- ✅ Memory usage under 50MB for economic systems
- ✅ Network traffic under 1KB/sec per player for economic sync

### Gameplay Quality
- ✅ Harvester AI provides satisfying automation
- ✅ Construction validation prevents exploits
- ✅ Economic feedback gives clear strategic information
- ✅ Balance maintains C&C strategic depth

## Conclusion

This comprehensive economic mechanics design provides authentic Command & Conquer economics while maintaining modern performance standards. The system supports scalable multiplayer operations, sophisticated AI behaviors, and maintains the strategic depth that made C&C economically engaging.

The modular design integrates seamlessly with the existing ECS architecture while providing room for future enhancements like advanced resource types, economic warfare mechanics, and sophisticated AI behaviors.

---

*Document prepared by Schema Database Expert Agent | Generated with Claude Code*