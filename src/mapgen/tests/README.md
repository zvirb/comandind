# Map Generation Test Suite

A comprehensive testing framework for the Advanced Map Generation System, providing validation for all aspects of procedural map generation including Wave Function Collapse, symmetric balance, resource distribution, performance benchmarks, and OpenRA compatibility.

## 🚀 Quick Start

```bash
# Run all tests
npm test

# Run quick validation
npm run test:quick

# Run demonstration
npm run demo

# Run performance benchmarks
npm run benchmark
```

## 📋 Test Coverage

### Core Algorithm Tests
- **Wave Function Collapse (WFC)**: Tests constraint-based terrain generation with OpenRA tile patterns
- **Symmetric Map Generation**: Validates 2, 4, 6, and 8-player map balance and fairness
- **Resource Distribution**: Tests resource placement algorithms and balance validation
- **Map Validation**: Comprehensive quality scoring and validation systems

### Performance & Quality Tests
- **Performance Benchmarks**: Generation speed, memory usage, and concurrent processing
- **Map Quality Scoring**: Validation of scoring consistency and quality thresholds
- **Balance Validation**: Competitive play balance analysis and team game fairness
- **Memory Leak Detection**: Long-running stability and resource management

### Integration Tests
- **OpenRA Compatibility**: Tile ID validation and format compatibility
- **Generator Integration**: Factory functions, presets, and statistics tracking
- **Example Generation**: Demonstration maps for various scenarios

## 🛠️ Test Runner Options

### Basic Usage
```bash
# Complete test suite (recommended)
node runTests.js --all

# Quick subset of tests
node runTests.js --quick

# Demonstration mode
node runTests.js --demo
```

### Specific Test Suites
```bash
# Wave Function Collapse tests only
node runTests.js --wfc

# Symmetric map balance tests
node runTests.js --symmetric

# Resource distribution tests
node runTests.js --resources

# Performance benchmarks only
node runTests.js --performance

# Map quality scoring tests
node runTests.js --quality
```

### Advanced Options
```bash
# Export results to JSON
node runTests.js --performance --export-results

# Verbose output
node runTests.js --verbose

# Combine multiple suites
node runTests.js --wfc --resources --performance
```

## 📊 Test Results

The test suite provides comprehensive reporting including:

### Overall Metrics
- **Pass Rate**: Percentage of tests passing
- **Execution Time**: Total time for test completion
- **Memory Usage**: Peak memory consumption and growth
- **Warning Count**: Non-critical issues detected

### Performance Metrics
- **Generation Speed**: Average generation time per algorithm
- **Memory Efficiency**: Memory usage by map size
- **Concurrent Processing**: Multi-threaded generation performance
- **Validation Speed**: Map validation performance

### Quality Metrics
- **Algorithm Comparison**: Quality scores by generation method
- **Balance Analysis**: Resource and positional fairness
- **OpenRA Compatibility**: Tile and format validation
- **Example Maps**: Generated demonstration maps with scores

## 🎯 Test Categories

### 1. Wave Function Collapse Tests
Tests the WFC algorithm implementation with focus on:
- Constraint satisfaction and rule adherence
- Large map generation performance
- Edge case handling and error recovery
- Backtracking functionality for conflict resolution
- OpenRA tile pattern compatibility

### 2. Symmetric Map Balance Tests
Validates symmetric map generation for competitive play:
- 2-player mirror symmetry validation
- 4+ player rotational symmetry
- Resource distribution fairness
- Path length analysis between players
- Multi-player balance scoring

### 3. Resource Distribution Tests
Comprehensive resource placement validation:
- Density control and placement accuracy
- Resource clustering behavior analysis
- Distance-based balance validation
- Multi-resource type handling
- Economic sustainability analysis

### 4. Performance Benchmark Tests
Performance validation and optimization metrics:
- Algorithm speed comparison
- Memory usage analysis by map size
- Concurrent generation stress testing
- Validation system performance
- Memory leak detection

### 5. Map Quality Tests
Quality scoring and consistency validation:
- Score consistency across generations
- Algorithm quality comparison
- Quality threshold enforcement
- Balance validation for competitive play
- Resource economy analysis

## 🔧 Configuration

### Test Configuration Options

```javascript
const testOptions = {
    // Performance testing
    enablePerformanceTesting: true,
    enableVisualization: false,
    generateExampleMaps: true,
    
    // Performance thresholds
    maxGenerationTimeMs: 5000,
    minValidationScore: 75,
    maxMemoryUsageMB: 50,
    
    // Test parameters
    testMapSizes: [
        { width: 20, height: 15, name: 'small' },
        { width: 40, height: 30, name: 'medium' },
        { width: 60, height: 45, name: 'large' }
    ],
    
    playerCountTests: [1, 2, 4, 6, 8],
    algorithmTests: ['wfc', 'symmetric', 'hybrid', 'classic'],
    climateTests: ['desert', 'temperate', 'arctic', 'volcanic']
};
```

### Customizing Test Suites

```javascript
import MapGenerationTests from './MapGenerationTests.js';

// Create custom test configuration
const customTester = new MapGenerationTests({
    testMapSizes: [{ width: 30, height: 20, name: 'custom' }],
    playerCountTests: [2, 4],
    enablePerformanceTesting: false,
    maxGenerationTimeMs: 2000
});

// Run specific test suites
await customTester.runWFCTests();
await customTester.runResourceDistributionTests();
```

## 📈 Performance Expectations

### Generation Speed Targets
- **Classic Algorithm**: < 200ms for 40x30 maps
- **WFC Algorithm**: < 3000ms for 40x30 maps  
- **Symmetric Algorithm**: < 500ms for 40x30 maps
- **Hybrid Algorithm**: < 1000ms for 40x30 maps

### Memory Usage Targets
- **Small Maps (20x15)**: < 2MB
- **Medium Maps (40x30)**: < 5MB
- **Large Maps (60x45)**: < 10MB

### Quality Score Targets
- **Competitive Maps**: ≥ 85/100
- **Casual Multiplayer**: ≥ 75/100
- **Campaign Maps**: ≥ 65/100

## 🎮 Example Map Generation

The test suite generates example maps demonstrating various scenarios:

### Desert 1v1 Competitive
```javascript
{
    width: 40, height: 30, playerCount: 2,
    climate: 'desert', algorithm: 'symmetric',
    symmetryType: 'mirror'
}
```

### Temperate 2v2 Team Play
```javascript
{
    width: 50, height: 40, playerCount: 4,
    climate: 'temperate', algorithm: 'symmetric',
    symmetryType: 'rotational'
}
```

### Large WFC Single Player
```javascript
{
    width: 60, height: 45, playerCount: 1,
    climate: 'temperate', algorithm: 'wfc'
}
```

## 🔍 Validation Criteria

### Resource Balance Validation
- **Distance Balance**: Resources equidistant from players (±25% tolerance)
- **Value Balance**: Total resource value per player (±15% tolerance)
- **Type Distribution**: Proper ratios of different resource types
- **Expansion Sites**: Adequate expansion opportunities

### Map Quality Scoring
- **Terrain Coherence**: Natural transitions and realistic terrain
- **Buildable Area**: Sufficient space for base construction (≥60%)
- **Strategic Depth**: Multiple strategic options and paths
- **Balance Fairness**: Equal opportunities for all players

### OpenRA Compatibility
- **Tile IDs**: All tiles match OpenRA tile definitions
- **Resource Types**: Compatible Tiberium tile types
- **Map Format**: Proper structure for OpenRA map files
- **Metadata**: Complete map information and settings

## 🐛 Troubleshooting

### Common Issues

**Test Timeouts**
```bash
# Reduce test complexity for slower systems
node runTests.js --quick
```

**Memory Issues**
```bash
# Run with more heap memory
node --max-old-space-size=4096 runTests.js
```

**Generation Failures**
```bash
# Run with verbose output to debug
node runTests.js --verbose
```

### Debug Mode

```javascript
// Enable debug logging
process.env.DEBUG = 'mapgen:*';
node runTests.js --verbose
```

## 📤 Exporting Results

### JSON Export Format

```json
{
  "timestamp": "2024-01-01T00:00:00.000Z",
  "testResults": {
    "overall": { "passed": 45, "failed": 0, "warnings": 2 },
    "suites": { ... },
    "performance": { ... },
    "examples": { ... }
  },
  "systemInfo": {
    "nodeVersion": "v18.0.0",
    "platform": "linux",
    "memory": { ... }
  }
}
```

### Continuous Integration

```yaml
# GitHub Actions example
- name: Run Map Generation Tests
  run: |
    cd src/mapgen/tests
    npm test
    npm run benchmark
```

## 🤝 Contributing

### Adding New Tests

1. Add test methods to `MapGenerationTests` class
2. Include validation criteria and assertions
3. Update test runner options if needed
4. Document expected behavior and thresholds

### Test Guidelines

- **Deterministic**: Tests should produce consistent results
- **Independent**: Each test should run independently
- **Clear Failures**: Assert messages should be descriptive
- **Performance Aware**: Include reasonable timeouts
- **Comprehensive**: Cover edge cases and error conditions

## 📚 API Reference

### MapGenerationTests Class

```javascript
class MapGenerationTests {
    constructor(options = {})
    async runAllTests()
    async runWFCTests()
    async runSymmetricMapTests()
    async runResourceDistributionTests()
    async runPerformanceTests()
    async runMapQualityTests()
    async runBalanceValidationTests()
    async runOpenRACompatibilityTests()
    async runGeneratorIntegrationTests()
    async generateExampleMaps()
}
```

### MapGenerationDemo Class

```javascript
class MapGenerationDemo {
    constructor()
    async runQuickDemo()
    async runFullTests()
}
```

## 📊 Metrics Dashboard

When running with `--export-results`, the test suite generates comprehensive metrics suitable for dashboard visualization:

- Generation performance trends
- Quality score distributions
- Resource balance analysis
- Memory usage patterns
- Test pass/fail rates over time

## 🏆 Quality Gates

The test suite enforces quality gates for:

- **Code Coverage**: Algorithm and edge case coverage
- **Performance**: Generation speed and memory efficiency
- **Balance**: Competitive play fairness
- **Compatibility**: OpenRA integration compliance
- **Reliability**: Consistent results across runs

---

*This test suite ensures the Advanced Map Generation System meets the highest standards for procedural map generation in real-time strategy games.*