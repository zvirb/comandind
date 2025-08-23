# Advanced Map Generation System

An advanced, modular map generation system for the Command & Conquer clone that provides sophisticated terrain generation, resource placement, and balance validation.

## Features

### 🌍 Wave Function Collapse (WFC) Algorithm
- Coherent terrain generation using constraint-based tile placement
- Support for complex adjacency rules and natural transitions
- Backtracking for conflict resolution
- Entropy-based tile selection

### 🎨 Intelligent Auto-Tiling System
- 8-directional bitmasking for smooth transitions
- Support for multiple terrain layers (base, transition, overlay)
- Corner handling for complex junction tiles
- Automatic shoreline, cliff, and forest edge generation

### 💎 Strategic Resource Placement
- Balanced distribution for multiplayer fairness
- Natural clustering and organic shapes
- Distance-based balancing algorithms
- Support for multiple resource types (Tiberium green/blue)

### ⚖️ Symmetric Map Generation
- Support for 2, 4, 6, and 8 player maps
- Multiple symmetry types: rotational, mirror, point
- Balanced starting positions and resources
- Fair terrain distribution

### ✅ Comprehensive Map Validation
- Terrain accessibility validation
- Resource balance checking
- Starting position fairness analysis
- Performance impact assessment
- Automatic fix suggestions

### 🎮 Genesis Project-Inspired Features
- Customizable climate settings (desert, temperate, arctic, volcanic)
- Adjustable terrain density parameters
- Strategic base placement algorithms
- Expansion site placement

## Quick Start

```javascript
import { AdvancedMapGenerator } from '../mapgen/index.js';

// Create a basic map generator
const generator = new AdvancedMapGenerator({
    width: 40,
    height: 30,
    playerCount: 2,
    algorithm: 'hybrid'
});

// Generate a map
const mapData = await generator.generateMap();

// The result contains:
// - terrain: 2D array of tile IDs
// - resources: Array of resource field objects
// - startingPositions: Array of player starting positions
// - metadata: Generation settings and statistics
// - validation: Validation results and scores
```

## Advanced Usage

### Using Presets

```javascript
import { createCompetitiveGenerator, getAvailablePresets } from '../mapgen/index.js';

// Get available presets
const presets = getAvailablePresets();
console.log('Available presets:', Object.keys(presets));

// Create a competitive 1v1 generator
const generator = createCompetitiveGenerator(2);
const map = await generator.generateMap();
```

### Custom Configuration

```javascript
const generator = new AdvancedMapGenerator({
    // Map dimensions
    width: 60,
    height: 45,
    
    // Algorithm selection
    algorithm: 'wfc', // 'wfc', 'symmetric', 'hybrid', 'classic'
    
    // Environment (Genesis Project inspired)
    climate: 'desert',
    mountainDensity: 0.15,
    waterCoverage: 0.1,
    forestDensity: 0.05,
    
    // Resources
    resourceDensity: 0.08,
    resourceBalance: true,
    multipleResourceTypes: true,
    
    // Multiplayer
    playerCount: 4,
    symmetryType: 'rotational',
    
    // Quality control
    enableValidation: true,
    qualityThreshold: 80,
    maxGenerationAttempts: 3
});

const mapData = await generator.generateMap();
```

### Individual Component Usage

#### Wave Function Collapse

```javascript
import { WaveFunctionCollapse } from '../mapgen/index.js';

const tileRules = {
    'S01': {
        frequency: 0.4,
        adjacency: {
            up: ['S01', 'S02', 'D01'],
            down: ['S01', 'S02', 'D01'],
            left: ['S01', 'S02', 'D01'],
            right: ['S01', 'S02', 'D01']
        }
    },
    // ... more tile rules
};

const wfc = new WaveFunctionCollapse(40, 30, tileRules);
const terrain = wfc.generate();
```

#### Auto-Tiling

```javascript
import { AutoTiler } from '../mapgen/index.js';

const autoTiler = new AutoTiler();
const tilingResult = autoTiler.autoTile(terrainMap, {
    enableTransitions: true,
    enableCorners: true,
    enableVariation: true
});

// Result contains multiple layers
const processedTerrain = tilingResult.base;
const transitionLayer = tilingResult.transition;
const overlayLayer = tilingResult.overlay;
```

#### Resource Placement

```javascript
import { ResourcePlacer } from '../mapgen/index.js';

const resourcePlacer = new ResourcePlacer(40, 30, {
    resourceDensity: 0.08,
    playerPositions: startingPositions,
    resourceTypes: ['green', 'blue'],
    expansionResources: true
});

const resourceFields = resourcePlacer.placeResources(terrain, startingPositions);
```

#### Map Validation

```javascript
import { MapValidator } from '../mapgen/index.js';

const validator = new MapValidator({
    resourceBalanceTolerance: 0.15,
    minBuildablePercentage: 0.6
});

const validation = validator.validateMap(mapData);
console.log(`Map score: ${validation.overall.score}/100 (${validation.overall.grade})`);

if (!validation.overall.valid) {
    console.log('Issues found:', validation.suggestions);
}
```

## Integration with Existing System

### Compatible with MapGenerator.js

The advanced system is designed to be compatible with your existing `MapGenerator.js`:

```javascript
import AdvancedMapGenerator from '../mapgen/AdvancedMapGenerator.js';

// In your existing MapGenerator class
class MapGenerator {
    constructor(canvas, spriteConfig) {
        this.canvas = canvas;
        // ... existing code ...
        
        // Add advanced generator
        this.advancedGenerator = new AdvancedMapGenerator({
            width: this.mapWidth,
            height: this.mapHeight
        });
    }
    
    async generateAdvancedMap(config = {}) {
        const mapData = await this.advancedGenerator.generateMap(config);
        
        // Convert to existing format
        this.terrainMap = mapData.terrain;
        this.tiberiumFields = mapData.resources;
        this.terrainMetadata = mapData.metadata;
        
        return mapData;
    }
}
```

### Using with Existing Tile System

The system uses the same tile IDs as your existing `TerrainGenerator.js`:

- Sand: S01-S08
- Dirt: D01-D08  
- Water: W1-W2
- Shore: SH1-SH6
- Trees: T01-T09
- Rocks: ROCK1-ROCK7
- Tiberium: TI1-TI3 (green), TI10-TI12 (blue)

## Algorithm Comparison

| Algorithm | Best For | Strengths | Performance |
|-----------|----------|-----------|-------------|
| **WFC** | Complex, realistic terrain | Natural transitions, coherent patterns | Medium |
| **Symmetric** | Competitive multiplayer | Perfect balance, fairness | Fast |
| **Hybrid** | Best of both worlds | Balance + realism | Medium |
| **Classic** | Simple, fast generation | Speed, compatibility | Very Fast |

## Configuration Options

### Climate Types

- **Desert**: High sand coverage, minimal water/forests
- **Temperate**: Balanced terrain with forests and water
- **Arctic**: Light terrain colors, minimal vegetation
- **Volcanic**: Dark terrain, rocky formations

### Symmetry Types

- **Rotational**: Perfect for 4+ players, terrain rotated around center
- **Mirror**: Best for 2 players, horizontal/vertical mirroring  
- **Point**: 180-degree rotation, good for team games

### Quality Thresholds

- **90-100**: Tournament quality (strict validation)
- **80-89**: Competitive play (balanced)
- **70-79**: Casual multiplayer (good enough)
- **60-69**: Campaign/skirmish (acceptable)
- **<60**: Poor quality (needs improvement)

## Performance Considerations

### Memory Usage
- WFC: ~1-2MB for 40x30 map
- Auto-tiling: ~0.5MB additional
- Validation: ~0.2MB additional

### Generation Time
- Classic: ~50-100ms
- Hybrid: ~200-500ms
- WFC: ~500-2000ms
- Symmetric: ~100-300ms

### Optimization Tips
- Set `optimizeForPerformance: true` for faster generation
- Reduce `wfcIterations` for speed (lower quality)
- Disable validation for non-competitive maps
- Use smaller map sizes for testing

## Troubleshooting

### Common Issues

**Generation fails with "No solution found"**
- Reduce terrain complexity
- Increase `maxGenerationAttempts`
- Check tile adjacency rules

**Poor validation scores**
- Adjust quality threshold
- Enable `resourceBalance`
- Increase `minBuildablePercentage`

**Performance issues**
- Enable `optimizeForPerformance`
- Reduce map size
- Use 'classic' algorithm

**Resources appear imbalanced**
- Enable `resourceBalance: true`
- Adjust `resourceBalanceTolerance`
- Increase `balanceRadius`

## API Reference

See individual component files for detailed API documentation:

- `AdvancedMapGenerator.js` - Main generator class
- `WaveFunctionCollapse.js` - WFC algorithm implementation  
- `AutoTiler.js` - Bitmasking and auto-tiling
- `ResourcePlacer.js` - Resource placement algorithms
- `SymmetricGenerator.js` - Symmetric map generation
- `MapValidator.js` - Map validation and quality checking

## Complete Workflow Examples

### Running the Complete Workflow

The complete OpenRA extraction to map generation workflow is available in `/examples/complete-workflow.js`:

```bash
# Navigate to the examples directory
cd src/mapgen/examples

# Run the complete workflow
node complete-workflow.js
```

This will:
1. Extract OpenRA assets and maps
2. Train WFC from map patterns
3. Generate maps using multiple algorithms
4. Validate and optimize map quality
5. Export game-ready maps

### Individual Workflow Steps

You can also run individual steps of the workflow:

```javascript
import { 
    extractOpenRAAssets,
    trainWFCFromMaps,
    generateMapsWithVariousAlgorithms,
    validateAndOptimizeMaps,
    exportMapsForGame
} from './examples/complete-workflow.js';

// Run individual steps
const extractedMaps = await extractOpenRAAssets();
const { trainingData } = await trainWFCFromMaps(extractedMaps);
const generatedMaps = await generateMapsWithVariousAlgorithms(trainingData);
```

### Integration with Game Systems

#### MapGenerator.js Integration

Add advanced generation to your existing MapGenerator:

```javascript
import { runCompleteWorkflow } from '../mapgen/examples/complete-workflow.js';
import { createMapGenerator } from '../mapgen/index.js';

class MapGenerator {
    constructor(canvas, spriteConfig) {
        this.canvas = canvas;
        this.spriteConfig = spriteConfig;
        // Initialize advanced generator
        this.advancedGenerator = createMapGenerator({
            width: 40,
            height: 30,
            algorithm: 'hybrid'
        });
    }
    
    async generateAdvancedMap(config = {}) {
        const mapData = await this.advancedGenerator.generateMap(config);
        
        // Convert to existing format
        this.convertToExistingFormat(mapData);
        
        return mapData;
    }
    
    async runFullWorkflow() {
        // Run the complete workflow
        const results = await runCompleteWorkflow();
        return results.exportedMaps;
    }
}
```

#### Game Integration Example

```javascript
import { exportMapsForGame } from '../mapgen/examples/complete-workflow.js';

// Load generated maps in your game
async function loadGeneratedMaps() {
    const fs = await import('fs');
    const mapIndex = JSON.parse(fs.readFileSync('./generated-maps/game-ready/map-index.json'));
    
    const availableMaps = mapIndex.maps.map(map => ({
        id: map.id,
        name: map.name,
        playerCount: map.playerCount,
        size: map.size,
        quality: map.quality
    }));
    
    return availableMaps;
}

// Load a specific map
async function loadMap(mapId) {
    const fs = await import('fs');
    const mapData = JSON.parse(fs.readFileSync(`./generated-maps/game-ready/${mapId}.json`));
    
    return {
        terrain: mapData.terrain,
        resources: mapData.resources,
        startingPositions: mapData.startingPositions,
        metadata: mapData.metadata
    };
}
```

### Workflow Configuration

Customize the workflow by modifying `WORKFLOW_CONFIG`:

```javascript
import { WORKFLOW_CONFIG, runCompleteWorkflow } from './examples/complete-workflow.js';

// Customize configuration
WORKFLOW_CONFIG.generation.mapSizes = [
    { width: 60, height: 60, name: 'tournament' }
];

WORKFLOW_CONFIG.validation.qualityThreshold = 85; // Higher quality requirement

// Run with custom config
const results = await runCompleteWorkflow();
```

## Sprite Integration

### OpenRA Sprite Extraction

The system integrates with OpenRA sprite extraction:

```bash
# Extract OpenRA sprites (run from project root)
node scripts/extraction/download-openra-sprites.js

# Extract specific unit sprites
node scripts/extraction/extract-sprites-proper.js

# Batch convert sprites to PNG
./scripts/extraction/batch-convert-to-png.sh
```

### Using Extracted Sprites

```javascript
// Load extracted sprites in your map generator
const spriteConfig = {
    spritePath: './public/assets/sprites/cnc-converted/',
    units: ['mammoth-tank', 'medium-tank', 'recon-bike'],
    buildings: ['barracks', 'power-plant', 'refinery'],
    terrain: ['sand', 'dirt', 'water', 'trees']
};

const generator = createMapGenerator({
    width: 40,
    height: 30,
    spriteConfig: spriteConfig
});
```

## Advanced Usage Patterns

### Campaign Map Generation

```javascript
import { createCampaignGenerator } from '../mapgen/index.js';

const campaignGenerator = createCampaignGenerator({
    climate: 'desert',
    difficulty: 'hard',
    objectiveType: 'destroy-base',
    aiIntensity: 0.8
});

const campaignMap = await campaignGenerator.generateMap();
```

### ML-Enhanced Generation

```javascript
import { createMLEnhancedGenerator } from '../mapgen/index.js';

const mlGenerator = createMLEnhancedGenerator({
    enableMLEvaluation: true,
    mlQualityThreshold: 80,
    trainingDataPath: './wfc-training-data.json'
});

const mlMap = await mlGenerator.generateMap();
```

### Competitive Tournament Maps

```javascript
import { createCompetitiveGenerator } from '../mapgen/index.js';

// Generate tournament-quality 1v1 map
const tournamentGenerator = createCompetitiveGenerator(2);
tournamentGenerator.updateConfig({
    width: 60,
    height: 60,
    symmetryType: 'mirror',
    resourceBalance: true,
    qualityThreshold: 90
});

const tournamentMap = await tournamentGenerator.generateMap();
```

## Demo and Testing

### Interactive Demo

A complete interactive demo is available at `/demo-map-generation.html`. Open it in a browser to:

- Generate maps with different algorithms
- Adjust parameters in real-time
- Visualize map quality metrics
- Export maps for use in the game

### Running Tests

```bash
# Run map generation tests
cd src/mapgen/tests
npm test

# Run integration tests
node integrationExample.js

# Run performance benchmarks
node runTests.js --benchmark
```

## Troubleshooting

### Common Workflow Issues

**"No OpenRA maps found"**
- Check that OpenRA is installed
- Verify the maps directory path in `WORKFLOW_CONFIG`
- Fallback to example maps is enabled by default

**"WFC generation fails"**
- Reduce map size or pattern complexity
- Check training data quality
- Increase `maxGenerationAttempts`

**"Low map quality scores"**
- Adjust validation thresholds
- Enable map optimization
- Check resource placement settings

**"Sprite extraction fails"**
- Verify OpenRA installation
- Check network connectivity for downloads
- Use manual sprite extraction method

### Performance Optimization

**Slow generation times:**
- Enable `optimizeForPerformance: true`
- Use smaller pattern sizes
- Reduce WFC iterations
- Disable ML evaluation for faster testing

**Memory issues:**
- Reduce map sizes
- Limit concurrent generation
- Clean up training data after use
- Use streaming for large datasets

### Integration Issues

**Module import errors:**
- Ensure all dependencies are installed
- Check that `type: "module"` is in package.json
- Use correct import paths

**Game compatibility:**
- Verify tile ID mappings
- Check coordinate system consistency
- Validate exported map format

## Contributing

When extending the system:

1. Maintain compatibility with existing tile IDs
2. Add appropriate validation checks
3. Include performance considerations
4. Update presets for new features
5. Add unit tests for critical algorithms
6. Document workflow integration points
7. Test with the complete workflow example

## License

This advanced map generation system is part of the Command & Conquer clone project and follows the same licensing terms.