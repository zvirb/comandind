# Backend Game Logic Analysis for Command and Independent Thought Iteration 2

**Research Date:** 2025-08-19  
**Scope:** AI Movement Intelligence, Pathfinding, Spatial Optimization, Tiberium Mechanics  
**Target Performance:** 50+ units, <5ms pathfinding computation  

## Current ECS Architecture Analysis

### Existing Component System
The current ECS foundation provides a solid base with well-structured components:

**Core Movement Components:**
- `MovementComponent`: Basic pathfinding with targetX/Y, path array, speed (50 px/s), turnRate (180°/s)
- `TransformComponent`: Position interpolation (x, y, rotation, scale) with previous state storage
- `VelocityComponent`: Speed control with maxSpeed (100), friction (0.95), velocity clamping
- `AIComponent`: Basic AI behaviors (idle, guard, patrol, attack) with think intervals (100ms)

**Current Systems:**
- `UnitMovementSystem`: Direct movement to targets with simple path following
- `MovementSystem`: Physics-based velocity application with friction
- `AISystem`: Basic enemy detection and behavior switching
- `CombatSystem`: Range-based target acquisition and attack execution

### Performance Characteristics
- Linear entity iteration (no spatial optimization)
- Simple direct pathfinding (no A* implementation)
- No group movement coordination
- Basic collision detection via distance calculations

## A* Pathfinding Implementation Strategy

### 1. Grid-Based Navigation System
```javascript
class PathfindingGrid {
    constructor(mapWidth, mapHeight, tileSize = 24) {
        this.tileSize = tileSize;
        this.width = Math.ceil(mapWidth / tileSize);
        this.height = Math.ceil(mapHeight / tileSize);
        this.nodes = this.createGrid();
        this.walkabilityCache = new Map();
    }
    
    createGrid() {
        const nodes = [];
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                nodes.push(new PathNode(x, y));
            }
        }
        return nodes;
    }
    
    updateWalkability(buildings, units) {
        // Dynamic obstacle updates
        this.nodes.forEach(node => node.walkable = true);
        
        // Mark building tiles as unwalkable
        buildings.forEach(building => {
            const tiles = this.getBuildingTiles(building);
            tiles.forEach(tile => this.setWalkable(tile.x, tile.y, false));
        });
        
        // Temporarily mark unit tiles (for collision avoidance)
        units.forEach(unit => {
            const tileX = Math.floor(unit.x / this.tileSize);
            const tileY = Math.floor(unit.y / this.tileSize);
            this.setWalkable(tileX, tileY, false);
        });
    }
}
```

### 2. Binary Heap Optimized A* Algorithm
```javascript
class AStarPathfinder {
    constructor(grid) {
        this.grid = grid;
        this.openSet = new BinaryHeap(node => node.fCost);
        this.closedSet = new Set();
    }
    
    findPath(startX, startY, endX, endY) {
        const startTime = performance.now();
        
        const startNode = this.grid.getNode(startX, startY);
        const endNode = this.grid.getNode(endX, endY);
        
        if (!startNode || !endNode || !endNode.walkable) {
            return null;
        }
        
        this.openSet.clear();
        this.closedSet.clear();
        
        startNode.gCost = 0;
        startNode.hCost = this.heuristic(startNode, endNode);
        startNode.fCost = startNode.gCost + startNode.hCost;
        
        this.openSet.push(startNode);
        
        while (this.openSet.size() > 0) {
            const currentNode = this.openSet.pop();
            this.closedSet.add(currentNode);
            
            if (currentNode === endNode) {
                const path = this.retracePath(startNode, endNode);
                const duration = performance.now() - startTime;
                
                // Target: <5ms computation time
                if (duration > 5) {
                    console.warn(`Pathfinding exceeded target time: ${duration.toFixed(2)}ms`);
                }
                
                return path;
            }
            
            // Process neighbors with diagonal movement support
            this.processNeighbors(currentNode, endNode);
        }
        
        return null; // No path found
    }
    
    processNeighbors(currentNode, endNode) {
        const neighbors = this.grid.getNeighbors(currentNode);
        
        for (let neighbor of neighbors) {
            if (!neighbor.walkable || this.closedSet.has(neighbor)) {
                continue;
            }
            
            // Diagonal movement cost adjustment
            const isDiagonal = Math.abs(neighbor.x - currentNode.x) + 
                              Math.abs(neighbor.y - currentNode.y) === 2;
            const moveCost = isDiagonal ? 14 : 10; // Diagonal = √2 * 10 ≈ 14
            
            const newGCost = currentNode.gCost + moveCost;
            
            if (newGCost < neighbor.gCost || !this.openSet.contains(neighbor)) {
                neighbor.gCost = newGCost;
                neighbor.hCost = this.heuristic(neighbor, endNode);
                neighbor.fCost = neighbor.gCost + neighbor.hCost;
                neighbor.parent = currentNode;
                
                if (!this.openSet.contains(neighbor)) {
                    this.openSet.push(neighbor);
                } else {
                    this.openSet.updateItem(neighbor);
                }
            }
        }
    }
    
    heuristic(nodeA, nodeB) {
        // Octile distance for diagonal movement
        const dx = Math.abs(nodeA.x - nodeB.x);
        const dy = Math.abs(nodeA.y - nodeB.y);
        return 10 * (dx + dy) + (14 - 2 * 10) * Math.min(dx, dy);
    }
}
```

### 3. ECS Integration Strategy
```javascript
class PathfindingSystem extends System {
    constructor(world, mapWidth, mapHeight) {
        super(world);
        this.requiredComponents = [TransformComponent, MovementComponent];
        this.grid = new PathfindingGrid(mapWidth, mapHeight);
        this.pathfinder = new AStarPathfinder(this.grid);
        this.pathfindingQueue = [];
        this.maxPathfindingPerFrame = 5; // Spread pathfinding across frames
        this.priority = 1;
    }
    
    update(deltaTime) {
        // Update grid walkability
        this.updateGridWalkability();
        
        // Process pathfinding requests
        this.processPathfindingQueue();
        
        // Update movement along paths
        this.updateMovement(deltaTime);
    }
    
    requestPathfinding(entity, targetX, targetY) {
        const movement = entity.getComponent(MovementComponent);
        const transform = entity.getComponent(TransformComponent);
        
        this.pathfindingQueue.push({
            entity,
            startX: Math.floor(transform.x / this.grid.tileSize),
            startY: Math.floor(transform.y / this.grid.tileSize),
            endX: Math.floor(targetX / this.grid.tileSize),
            endY: Math.floor(targetY / this.grid.tileSize),
            priority: this.calculatePriority(entity)
        });
        
        // Sort by priority (combat units get higher priority)
        this.pathfindingQueue.sort((a, b) => b.priority - a.priority);
    }
    
    processPathfindingQueue() {
        const processed = Math.min(this.pathfindingQueue.length, this.maxPathfindingPerFrame);
        
        for (let i = 0; i < processed; i++) {
            const request = this.pathfindingQueue.shift();
            const path = this.pathfinder.findPath(
                request.startX, request.startY,
                request.endX, request.endY
            );
            
            if (path) {
                const movement = request.entity.getComponent(MovementComponent);
                movement.path = this.convertToWorldCoordinates(path);
                movement.pathIndex = 0;
                movement.isMoving = true;
            }
        }
    }
}
```

## Spatial Optimization for 50+ Units

### 1. Quadtree Spatial Indexing
```javascript
class SpatialQuadtree {
    constructor(x, y, width, height, maxObjects = 10, maxLevels = 5, level = 0) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
        this.maxObjects = maxObjects;
        this.maxLevels = maxLevels;
        this.level = level;
        this.objects = [];
        this.nodes = [];
    }
    
    clear() {
        this.objects = [];
        this.nodes.forEach(node => node.clear());
        this.nodes = [];
    }
    
    split() {
        const subWidth = this.width / 2;
        const subHeight = this.height / 2;
        
        this.nodes[0] = new SpatialQuadtree(this.x + subWidth, this.y, subWidth, subHeight, 
                                           this.maxObjects, this.maxLevels, this.level + 1);
        this.nodes[1] = new SpatialQuadtree(this.x, this.y, subWidth, subHeight, 
                                           this.maxObjects, this.maxLevels, this.level + 1);
        this.nodes[2] = new SpatialQuadtree(this.x, this.y + subHeight, subWidth, subHeight, 
                                           this.maxObjects, this.maxLevels, this.level + 1);
        this.nodes[3] = new SpatialQuadtree(this.x + subWidth, this.y + subHeight, subWidth, subHeight, 
                                           this.maxObjects, this.maxLevels, this.level + 1);
    }
    
    insert(entity) {
        if (this.nodes.length > 0) {
            const index = this.getIndex(entity);
            if (index !== -1) {
                this.nodes[index].insert(entity);
                return;
            }
        }
        
        this.objects.push(entity);
        
        if (this.objects.length > this.maxObjects && this.level < this.maxLevels) {
            if (this.nodes.length === 0) {
                this.split();
            }
            
            let i = 0;
            while (i < this.objects.length) {
                const index = this.getIndex(this.objects[i]);
                if (index !== -1) {
                    this.nodes[index].insert(this.objects.splice(i, 1)[0]);
                } else {
                    i++;
                }
            }
        }
    }
    
    retrieve(entity) {
        const returnObjects = [];
        const index = this.getIndex(entity);
        
        if (this.nodes.length > 0 && index !== -1) {
            returnObjects.push(...this.nodes[index].retrieve(entity));
        }
        
        returnObjects.push(...this.objects);
        return returnObjects;
    }
    
    getIndex(entity) {
        const transform = entity.getComponent(TransformComponent);
        const verticalMidpoint = this.x + (this.width / 2);
        const horizontalMidpoint = this.y + (this.height / 2);
        
        const topQuadrant = transform.y < horizontalMidpoint && transform.y + 24 < horizontalMidpoint;
        const bottomQuadrant = transform.y > horizontalMidpoint;
        
        if (transform.x < verticalMidpoint && transform.x + 24 < verticalMidpoint) {
            if (topQuadrant) return 1;
            else if (bottomQuadrant) return 2;
        } else if (transform.x > verticalMidpoint) {
            if (topQuadrant) return 0;
            else if (bottomQuadrant) return 3;
        }
        
        return -1;
    }
}
```

### 2. Spatial System for Efficient Queries
```javascript
class SpatialSystem extends System {
    constructor(world, mapWidth, mapHeight) {
        super(world);
        this.requiredComponents = [TransformComponent];
        this.quadtree = new SpatialQuadtree(0, 0, mapWidth, mapHeight);
        this.priority = 0; // Run first
    }
    
    update(deltaTime) {
        // Rebuild quadtree each frame (more efficient than tracking movements)
        this.quadtree.clear();
        
        for (const entity of this.entities) {
            if (entity.active) {
                this.quadtree.insert(entity);
            }
        }
    }
    
    getNearbyEntities(entity, radius) {
        const potentialCollisions = this.quadtree.retrieve(entity);
        const transform = entity.getComponent(TransformComponent);
        const nearby = [];
        
        for (const other of potentialCollisions) {
            if (other === entity) continue;
            
            const otherTransform = other.getComponent(TransformComponent);
            const dx = otherTransform.x - transform.x;
            const dy = otherTransform.y - transform.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance <= radius) {
                nearby.push({ entity: other, distance });
            }
        }
        
        return nearby.sort((a, b) => a.distance - b.distance);
    }
    
    findNearestTarget(entity, radius, filter = null) {
        const nearby = this.getNearbyEntities(entity, radius);
        
        for (const { entity: target } of nearby) {
            if (filter && !filter(target)) continue;
            return target;
        }
        
        return null;
    }
}
```

## Tiberium Resource Mechanics

### 1. Harvester AI State Machine
```javascript
class HarvesterComponent extends Component {
    constructor(capacity = 700, harvestRate = 25) {
        super();
        this.capacity = capacity;
        this.harvestRate = harvestRate; // credits per bail
        this.currentLoad = 0;
        this.state = 'idle'; // idle, seeking_tiberium, harvesting, returning, unloading
        this.targetField = null;
        this.homeRefinery = null;
        this.harvestingTime = 0;
        this.bailsPerSecond = 2; // harvesting rate
    }
    
    canHarvest() {
        return this.currentLoad < this.capacity;
    }
    
    isEmpty() {
        return this.currentLoad === 0;
    }
    
    isFull() {
        return this.currentLoad >= this.capacity;
    }
    
    harvestBail() {
        if (this.canHarvest()) {
            this.currentLoad += this.harvestRate;
            return this.harvestRate;
        }
        return 0;
    }
    
    unload() {
        const credits = this.currentLoad;
        this.currentLoad = 0;
        return credits;
    }
}

class TiberiumFieldComponent extends Component {
    constructor(tiberiumAmount = 1000, regenerationRate = 0.5) {
        super();
        this.maxTiberium = tiberiumAmount;
        this.currentTiberium = tiberiumAmount;
        this.regenerationRate = regenerationRate; // bails per second
        this.lastRegenTime = Date.now();
        this.harvesters = new Set(); // Harvesters currently using this field
        this.depleted = false;
    }
    
    canHarvest() {
        return this.currentTiberium > 0 && !this.depleted;
    }
    
    harvestBail() {
        if (this.canHarvest()) {
            this.currentTiberium -= 25;
            if (this.currentTiberium <= 0) {
                this.currentTiberium = 0;
                this.depleted = true;
            }
            return 25;
        }
        return 0;
    }
    
    regenerate(deltaTime) {
        if (this.depleted && this.harvesters.size === 0) {
            // Start regenerating when no harvesters are present
            const now = Date.now();
            const timeDelta = (now - this.lastRegenTime) / 1000;
            
            if (timeDelta >= 1) { // Regenerate every second
                this.currentTiberium += this.regenerationRate * 25;
                if (this.currentTiberium >= this.maxTiberium * 0.25) {
                    this.depleted = false; // Field becomes active again
                }
                this.currentTiberium = Math.min(this.currentTiberium, this.maxTiberium);
                this.lastRegenTime = now;
            }
        }
    }
}
```

### 2. Harvester AI System
```javascript
class HarvesterAISystem extends System {
    constructor(world, spatialSystem) {
        super(world);
        this.requiredComponents = [TransformComponent, HarvesterComponent, MovementComponent, AIComponent];
        this.spatialSystem = spatialSystem;
        this.priority = 5;
    }
    
    update(deltaTime) {
        for (const entity of this.entities) {
            if (!entity.active) continue;
            
            const harvester = entity.getComponent(HarvesterComponent);
            const ai = entity.getComponent(AIComponent);
            const movement = entity.getComponent(MovementComponent);
            const transform = entity.getComponent(TransformComponent);
            
            if (!ai.shouldThink()) continue;
            ai.think();
            
            switch (harvester.state) {
                case 'idle':
                    this.handleIdleState(entity);
                    break;
                case 'seeking_tiberium':
                    this.handleSeekingState(entity);
                    break;
                case 'harvesting':
                    this.handleHarvestingState(entity, deltaTime);
                    break;
                case 'returning':
                    this.handleReturningState(entity);
                    break;
                case 'unloading':
                    this.handleUnloadingState(entity);
                    break;
            }
        }
    }
    
    handleIdleState(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        
        if (harvester.isEmpty()) {
            // Find nearest tiberium field
            const nearestField = this.findNearestTiberiumField(entity);
            if (nearestField) {
                harvester.targetField = nearestField;
                harvester.state = 'seeking_tiberium';
                this.moveToTarget(entity, nearestField);
            }
        } else {
            // Return to refinery
            harvester.state = 'returning';
            this.returnToRefinery(entity);
        }
    }
    
    handleSeekingState(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        const movement = entity.getComponent(MovementComponent);
        
        if (!movement.isMoving) {
            if (harvester.targetField && this.isNearTarget(entity, harvester.targetField)) {
                harvester.state = 'harvesting';
                harvester.harvestingTime = 0;
                
                // Add to field's harvester list
                const fieldComponent = harvester.targetField.getComponent(TiberiumFieldComponent);
                fieldComponent.harvesters.add(entity);
            } else {
                // Target field might be depleted, find another
                harvester.state = 'idle';
            }
        }
    }
    
    handleHarvestingState(entity, deltaTime) {
        const harvester = entity.getComponent(HarvesterComponent);
        const fieldComponent = harvester.targetField?.getComponent(TiberiumFieldComponent);
        
        if (!fieldComponent || !fieldComponent.canHarvest()) {
            // Field depleted, find another
            if (fieldComponent) {
                fieldComponent.harvesters.delete(entity);
            }
            harvester.targetField = null;
            harvester.state = 'idle';
            return;
        }
        
        harvester.harvestingTime += deltaTime;
        
        // Harvest at specified rate
        if (harvester.harvestingTime >= 1 / harvester.bailsPerSecond) {
            const harvested = fieldComponent.harvestBail();
            harvester.harvestBail();
            harvester.harvestingTime = 0;
            
            if (harvester.isFull()) {
                fieldComponent.harvesters.delete(entity);
                harvester.state = 'returning';
                this.returnToRefinery(entity);
            }
        }
    }
    
    handleReturningState(entity) {
        const movement = entity.getComponent(MovementComponent);
        
        if (!movement.isMoving) {
            const harvester = entity.getComponent(HarvesterComponent);
            if (this.isNearRefinery(entity)) {
                harvester.state = 'unloading';
            } else {
                // Refinery might be destroyed, find another
                this.returnToRefinery(entity);
            }
        }
    }
    
    handleUnloadingState(entity) {
        const harvester = entity.getComponent(HarvesterComponent);
        
        // Simulate unloading time
        setTimeout(() => {
            const credits = harvester.unload();
            this.addCreditsToPlayer(entity, credits);
            harvester.state = 'idle';
        }, 2000); // 2 second unloading time
    }
    
    findNearestTiberiumField(entity) {
        const nearbyEntities = this.spatialSystem.getNearbyEntities(entity, 1000);
        
        for (const { entity: target } of nearbyEntities) {
            const tiberiumField = target.getComponent(TiberiumFieldComponent);
            if (tiberiumField && tiberiumField.canHarvest()) {
                return target;
            }
        }
        
        return null;
    }
    
    isNearTarget(entity, target) {
        const transform = entity.getComponent(TransformComponent);
        const targetTransform = target.getComponent(TransformComponent);
        
        const dx = targetTransform.x - transform.x;
        const dy = targetTransform.y - transform.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        return distance <= 50; // Within 50 pixels
    }
}
```

## Advanced Movement Behaviors

### 1. Group Movement Coordination
```javascript
class FormationComponent extends Component {
    constructor(formationType = 'line', spacing = 48) {
        super();
        this.formationType = formationType; // line, column, box, wedge
        this.spacing = spacing;
        this.leader = null;
        this.members = new Set();
        this.formationPositions = new Map();
        this.cohesion = 0.8; // How tightly units stay in formation
    }
    
    addMember(entity) {
        this.members.add(entity);
        this.calculateFormationPositions();
    }
    
    removeMember(entity) {
        this.members.delete(entity);
        this.formationPositions.delete(entity);
        this.calculateFormationPositions();
    }
    
    calculateFormationPositions() {
        const members = Array.from(this.members);
        
        switch (this.formationType) {
            case 'line':
                this.calculateLineFormation(members);
                break;
            case 'column':
                this.calculateColumnFormation(members);
                break;
            case 'box':
                this.calculateBoxFormation(members);
                break;
            case 'wedge':
                this.calculateWedgeFormation(members);
                break;
        }
    }
    
    calculateLineFormation(members) {
        const halfCount = (members.length - 1) / 2;
        
        members.forEach((member, index) => {
            const offset = (index - halfCount) * this.spacing;
            this.formationPositions.set(member, { x: offset, y: 0 });
        });
    }
    
    calculateColumnFormation(members) {
        members.forEach((member, index) => {
            this.formationPositions.set(member, { x: 0, y: index * this.spacing });
        });
    }
}

class GroupMovementSystem extends System {
    constructor(world, pathfindingSystem) {
        super(world);
        this.requiredComponents = [TransformComponent, MovementComponent];
        this.pathfindingSystem = pathfindingSystem;
        this.formations = new Map();
        this.priority = 3;
    }
    
    createFormation(entities, formationType = 'line') {
        const formation = new FormationComponent(formationType);
        formation.leader = entities[0];
        
        entities.forEach(entity => formation.addMember(entity));
        this.formations.set(formation.leader, formation);
        
        return formation;
    }
    
    moveFormation(formation, targetX, targetY) {
        const leaderTransform = formation.leader.getComponent(TransformComponent);
        
        // Calculate formation center
        const centerX = targetX;
        const centerY = targetY;
        
        // Move each member to their formation position
        formation.members.forEach(member => {
            const offset = formation.formationPositions.get(member);
            if (offset) {
                const memberTargetX = centerX + offset.x;
                const memberTargetY = centerY + offset.y;
                
                this.pathfindingSystem.requestPathfinding(member, memberTargetX, memberTargetY);
            }
        });
    }
    
    update(deltaTime) {
        // Monitor formations and maintain cohesion
        for (const [leader, formation] of this.formations) {
            this.maintainFormationCohesion(formation, deltaTime);
        }
    }
    
    maintainFormationCohesion(formation, deltaTime) {
        const leaderTransform = formation.leader.getComponent(TransformComponent);
        const leaderMovement = formation.leader.getComponent(MovementComponent);
        
        if (!leaderMovement.isMoving) return;
        
        // Check if any member is too far from formation position
        formation.members.forEach(member => {
            if (member === formation.leader) return;
            
            const memberTransform = member.getComponent(TransformComponent);
            const memberMovement = member.getComponent(MovementComponent);
            const formationPos = formation.formationPositions.get(member);
            
            if (formationPos) {
                const targetX = leaderTransform.x + formationPos.x;
                const targetY = leaderTransform.y + formationPos.y;
                
                const dx = targetX - memberTransform.x;
                const dy = targetY - memberTransform.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                // If member is too far from formation position, issue new movement order
                if (distance > formation.spacing * 1.5) {
                    this.pathfindingSystem.requestPathfinding(member, targetX, targetY);
                }
            }
        });
    }
}
```

### 2. Flow Field Pathfinding for Large Groups
```javascript
class FlowFieldSystem extends System {
    constructor(world, mapWidth, mapHeight, tileSize = 24) {
        super(world);
        this.tileSize = tileSize;
        this.width = Math.ceil(mapWidth / tileSize);
        this.height = Math.ceil(mapHeight / tileSize);
        this.costField = new Array(this.width * this.height);
        this.flowField = new Array(this.width * this.height);
        this.activeFlowFields = new Map();
        this.priority = 2;
    }
    
    generateFlowField(goalX, goalY, groupId) {
        const goalTileX = Math.floor(goalX / this.tileSize);
        const goalTileY = Math.floor(goalY / this.tileSize);
        
        // Initialize cost field with infinity
        this.costField.fill(Infinity);
        
        // Set goal cost to 0
        const goalIndex = goalTileY * this.width + goalTileX;
        this.costField[goalIndex] = 0;
        
        // Dijkstra's algorithm to calculate cost field
        const queue = [{ x: goalTileX, y: goalTileY, cost: 0 }];
        const visited = new Set();
        
        while (queue.length > 0) {
            queue.sort((a, b) => a.cost - b.cost);
            const current = queue.shift();
            const currentIndex = current.y * this.width + current.x;
            
            if (visited.has(currentIndex)) continue;
            visited.add(currentIndex);
            
            // Process neighbors
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    if (dx === 0 && dy === 0) continue;
                    
                    const nx = current.x + dx;
                    const ny = current.y + dy;
                    
                    if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;
                    
                    const neighborIndex = ny * this.width + nx;
                    if (visited.has(neighborIndex)) continue;
                    
                    // Check if tile is walkable
                    if (!this.isTileWalkable(nx, ny)) continue;
                    
                    const moveCost = (dx !== 0 && dy !== 0) ? 14 : 10; // Diagonal vs cardinal
                    const newCost = current.cost + moveCost;
                    
                    if (newCost < this.costField[neighborIndex]) {
                        this.costField[neighborIndex] = newCost;
                        queue.push({ x: nx, y: ny, cost: newCost });
                    }
                }
            }
        }
        
        // Generate flow field from cost field
        this.generateFlowFromCost();
        
        // Store flow field for this group
        this.activeFlowFields.set(groupId, {
            flowField: [...this.flowField],
            goalX: goalTileX,
            goalY: goalTileY,
            timestamp: Date.now()
        });
    }
    
    generateFlowFromCost() {
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const index = y * this.width + x;
                
                if (this.costField[index] === Infinity) {
                    this.flowField[index] = { x: 0, y: 0 };
                    continue;
                }
                
                let bestDirection = { x: 0, y: 0 };
                let lowestCost = this.costField[index];
                
                // Check all neighbors
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        
                        const nx = x + dx;
                        const ny = y + dy;
                        
                        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;
                        
                        const neighborIndex = ny * this.width + nx;
                        
                        if (this.costField[neighborIndex] < lowestCost) {
                            lowestCost = this.costField[neighborIndex];
                            bestDirection = { x: dx, y: dy };
                        }
                    }
                }
                
                // Normalize direction
                const length = Math.sqrt(bestDirection.x * bestDirection.x + bestDirection.y * bestDirection.y);
                if (length > 0) {
                    this.flowField[index] = {
                        x: bestDirection.x / length,
                        y: bestDirection.y / length
                    };
                } else {
                    this.flowField[index] = { x: 0, y: 0 };
                }
            }
        }
    }
    
    getFlowDirection(x, y, groupId) {
        const flowData = this.activeFlowFields.get(groupId);
        if (!flowData) return { x: 0, y: 0 };
        
        const tileX = Math.floor(x / this.tileSize);
        const tileY = Math.floor(y / this.tileSize);
        
        if (tileX < 0 || tileX >= this.width || tileY < 0 || tileY >= this.height) {
            return { x: 0, y: 0 };
        }
        
        const index = tileY * this.width + tileX;
        return flowData.flowField[index] || { x: 0, y: 0 };
    }
}
```

## Performance Optimization Strategies

### 1. Frame Budget Management
```javascript
class PerformanceManager {
    constructor() {
        this.frameTimeTarget = 16.67; // 60 FPS
        this.pathfindingBudget = 5; // ms per frame
        this.aiThinkingBudget = 3; // ms per frame
        this.spatialUpdateBudget = 2; // ms per frame
        
        this.frameStartTime = 0;
        this.systemTimes = new Map();
    }
    
    startFrame() {
        this.frameStartTime = performance.now();
    }
    
    canExecuteSystem(systemName, estimatedTime) {
        const elapsed = performance.now() - this.frameStartTime;
        const remaining = this.frameTimeTarget - elapsed;
        
        return remaining >= estimatedTime;
    }
    
    recordSystemTime(systemName, duration) {
        if (!this.systemTimes.has(systemName)) {
            this.systemTimes.set(systemName, []);
        }
        
        const times = this.systemTimes.get(systemName);
        times.push(duration);
        
        // Keep only last 60 measurements
        if (times.length > 60) {
            times.shift();
        }
    }
    
    getAverageSystemTime(systemName) {
        const times = this.systemTimes.get(systemName);
        if (!times || times.length === 0) return 0;
        
        return times.reduce((sum, time) => sum + time, 0) / times.length;
    }
}
```

### 2. Memory Pool for Entity Management
```javascript
class EntityPool {
    constructor(initialSize = 100) {
        this.available = [];
        this.inUse = new Set();
        
        // Pre-allocate entities
        for (let i = 0; i < initialSize; i++) {
            this.available.push(new Entity());
        }
    }
    
    acquire() {
        let entity;
        
        if (this.available.length > 0) {
            entity = this.available.pop();
        } else {
            entity = new Entity();
        }
        
        this.inUse.add(entity);
        entity.active = true;
        return entity;
    }
    
    release(entity) {
        if (this.inUse.has(entity)) {
            this.inUse.delete(entity);
            entity.active = false;
            entity.clearComponents();
            this.available.push(entity);
        }
    }
    
    getStats() {
        return {
            available: this.available.length,
            inUse: this.inUse.size,
            total: this.available.length + this.inUse.size
        };
    }
}
```

## Integration Recommendations

### 1. Incremental Implementation Plan
1. **Phase 1:** Implement A* pathfinding system with binary heap optimization
2. **Phase 2:** Add spatial quadtree indexing for performance
3. **Phase 3:** Implement basic Tiberium mechanics and harvester AI
4. **Phase 4:** Add group movement and formation systems
5. **Phase 5:** Implement flow field pathfinding for large unit groups
6. **Phase 6:** Add performance monitoring and optimization

### 2. Performance Targets
- **Pathfinding:** <5ms per unit request
- **Spatial Queries:** <1ms for 50 units within 200px radius
- **AI Updates:** <100ms for 50 units thinking every 100ms
- **Frame Rate:** Maintain 60 FPS with 50+ active units

### 3. Testing Strategy
- Unit tests for pathfinding algorithms
- Performance benchmarks for spatial systems
- Integration tests for Tiberium economy balance
- Stress tests with 100+ units for performance validation

This comprehensive analysis provides the foundation for implementing robust AI movement intelligence that can scale to support 50+ units while maintaining the target performance characteristics.