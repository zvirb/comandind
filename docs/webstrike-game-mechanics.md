# WebStrike Command - Game Mechanics

## Unit Statistics

### GDI Key Units
- **Medium Tank:** $800, 400 HP, Heavy armor, Speed 18, Range 4.75, 30 damage (105mm)
- **Mammoth Tank:** $1500, 600 HP, Heavy armor, Speed 12, 40+75 damage (120mm + Missiles)
- **Commando:** $1000, 100 HP, Speed 10, Sniper rifle + C4 charges

### NOD Key Units
- **Light Tank:** $600, 300 HP, Heavy armor, Speed 18, Range 4, 25 damage (75mm)
- **Stealth Tank:** $900, 110 HP, Light armor, Speed 30, Cloaking capability
- **Obelisk of Light:** $1500, 400 HP, Range 7.5, 200 damage laser (Super warhead)

## Damage System: Warhead Modifier System
- **Small Arms (SA):** 100% vs infantry, 25% vs heavy armor
- **Armor Piercing (AP):** 30% vs infantry, 100% vs heavy armor
- **Super warhead:** 100% damage vs all armor types (Obelisk, Ion Cannon)

## Economic Mechanics
- **Tiberium value:** 25 credits per bail
- **Harvester capacity:** 700 credits maximum
- **Build speed formula:** 1 minute per 1000 credits base cost
- **Refund percentage:** 50% when selling structures

## Pathfinding Algorithms
- **Individual units:** A* with binary heap optimization
- **Group movement:** Flow fields (superior performance)
- Grid-based navigation with obstacle avoidance

```javascript
class FlowFieldPathfinder {
  generateFlowField(goalX, goalY) {
    const costField = this.generateCostField(goalX, goalY);
    
    for (let y = 0; y < this.grid.height; y++) {
      for (let x = 0; x < this.grid.width; x++) {
        const neighbors = this.getNeighbors(x, y);
        let bestNeighbor = null;
        let lowestCost = Infinity;
        
        for (let neighbor of neighbors) {
          const nIndex = neighbor.y * this.grid.width + neighbor.x;
          if (costField[nIndex] < lowestCost) {
            lowestCost = costField[nIndex];
            bestNeighbor = neighbor;
          }
        }
        
        if (bestNeighbor) {
          this.flowField[index] = {
            x: bestNeighbor.x - x,
            y: bestNeighbor.y - y
          };
        }
      }
    }
  }
}
```

## Fog of War System
- Grid-based reference counting (8x8 cell size)
- Efficient floodFill algorithm for vision updates
- Texture-based rendering with Uint8Array
- Update only when units move to reduce computational overhead

```javascript
class FogOfWar {
  constructor(mapWidth, mapHeight, cellSize = 8) {
    this.width = Math.ceil(mapWidth / cellSize);
    this.height = Math.ceil(mapHeight / cellSize);
    this.cells = new Array(this.width * this.height).fill(0);
    this.texture = new Uint8Array(this.width * this.height);
  }
  
  updateVision(units) {
    units.forEach(unit => {
      if (unit.moved) {
        this.floodFill(unit.x, unit.y, unit.visionRange, -1);
        this.floodFill(unit.newX, unit.newY, unit.visionRange, 1);
      }
    });
  }
}
```

## Selection and Control
- Mouse-based unit selection with drag rectangles
- Multi-unit selection and group commands
- Context-sensitive right-click commands
- Formation maintenance during group movement

## Resource Gathering
- Automated harvester pathfinding to Tiberium fields
- Refinery proximity optimization
- Tiberium field depletion and regeneration
- Economic balance to encourage expansion