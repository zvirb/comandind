/**
 * MapValidator - Comprehensive Map Validation and Balance Checking
 * 
 * This system validates generated maps for gameplay balance, fairness,
 * and technical correctness. It ensures maps meet quality standards
 * for competitive play.
 * 
 * Key Features:
 * - Terrain accessibility validation
 * - Resource balance checking  
 * - Starting position fairness analysis
 * - Path length and chokepoint analysis
 * - Buildable area distribution
 * - Performance impact assessment
 * - Fix suggestions for common issues
 */

class MapValidator {
    constructor(options = {}) {
        this.options = {
            // Balance thresholds
            resourceBalanceTolerance: 0.15, // 15% tolerance for resource differences
            pathLengthTolerance: 0.2, // 20% tolerance for path length differences
            buildableAreaTolerance: 0.1, // 10% tolerance for buildable area differences
            
            // Minimum requirements
            minBuildablePercentage: 0.6, // 60% of map should be buildable
            minResourcesPerPlayer: 500, // Minimum resource value per player
            minPathWidth: 2, // Minimum path width in tiles
            maxChokepointRatio: 0.3, // Maximum percentage of map that can be chokepoints
            
            // Performance thresholds
            maxComplexityScore: 1000,
            maxTransitionTiles: 500,
            
            // Validation options
            validateAccessibility: true,
            validateBalance: true,
            validatePerformance: true,
            generateFixes: true,
            
            ...options
        };
        
        // Validation results storage
        this.results = {
            overall: { valid: false, score: 0 },
            terrain: { valid: false, issues: [] },
            resources: { valid: false, issues: [] },
            accessibility: { valid: false, issues: [] },
            balance: { valid: false, issues: [] },
            performance: { valid: false, issues: [] },
            suggestions: []
        };
        
        // Pathfinding for accessibility checks
        this.pathfinder = new MapPathfinder();
    }

    /**
     * Validate a complete map configuration
     * @param {Object} mapData - Complete map data including terrain, resources, starting positions
     * @returns {Object} - Validation results with scores and suggestions
     */
    validateMap(mapData) {
        const { terrain, resources, startingPositions, metadata } = mapData;
        
        this.resetResults();
        
        // Basic structure validation
        if (!this.validateMapStructure(mapData)) {
            return this.results;
        }
        
        // Terrain validation
        this.validateTerrain(terrain, metadata);
        
        // Resource validation
        if (resources && resources.length > 0) {
            this.validateResources(terrain, resources, startingPositions);
        }
        
        // Accessibility validation  
        if (this.options.validateAccessibility) {
            this.validateAccessibility(terrain, startingPositions);
        }
        
        // Balance validation
        if (this.options.validateBalance && startingPositions.length > 1) {
            this.validateBalance(terrain, resources, startingPositions);
        }
        
        // Performance validation
        if (this.options.validatePerformance) {
            this.validatePerformance(terrain, resources);
        }
        
        // Calculate overall validation score
        this.calculateOverallScore();
        
        // Generate improvement suggestions
        if (this.options.generateFixes) {
            this.generateFixSuggestions();
        }
        
        return this.results;
    }

    /**
     * Validate basic map structure
     */
    validateMapStructure(mapData) {
        const errors = [];
        
        if (!mapData.terrain || !Array.isArray(mapData.terrain)) {
            errors.push('Invalid terrain data structure');
        }
        
        if (!mapData.metadata || !mapData.metadata.width || !mapData.metadata.height) {
            errors.push('Missing or invalid map metadata');
        }
        
        const { terrain, metadata } = mapData;
        if (terrain && (terrain.length !== metadata.height || 
                       terrain[0]?.length !== metadata.width)) {
            errors.push('Terrain dimensions do not match metadata');
        }
        
        if (errors.length > 0) {
            this.results.overall.valid = false;
            this.results.terrain.issues = errors;
            return false;
        }
        
        return true;
    }

    /**
     * Validate terrain properties
     */
    validateTerrain(terrain, metadata) {
        const issues = [];
        let buildableTiles = 0;
        let totalTiles = 0;
        let waterTiles = 0;
        let transitionTiles = 0;
        
        const terrainAnalysis = {
            sand: 0, dirt: 0, water: 0, shore: 0, 
            trees: 0, rocks: 0, unknown: 0
        };
        
        // Analyze terrain distribution
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                const tile = terrain[y][x];
                totalTiles++;
                
                // Categorize terrain type
                const category = this.categorizeTerrainTile(tile);
                terrainAnalysis[category]++;
                
                // Check buildability
                if (this.isBuildableTerrain(tile)) {
                    buildableTiles++;
                }
                
                if (this.isWaterTerrain(tile)) {
                    waterTiles++;
                }
                
                if (this.isTransitionTerrain(tile)) {
                    transitionTiles++;
                }
                
                // Check for problematic tile combinations
                this.checkTileNeighborhood(terrain, x, y, issues);
            }
        }
        
        // Validate buildable area percentage
        const buildablePercentage = buildableTiles / totalTiles;
        if (buildablePercentage < this.options.minBuildablePercentage) {
            issues.push({
                type: 'insufficient_buildable_area',
                severity: 'high',
                message: `Only ${(buildablePercentage * 100).toFixed(1)}% buildable (minimum: ${(this.options.minBuildablePercentage * 100)}%)`,
                value: buildablePercentage,
                threshold: this.options.minBuildablePercentage
            });
        }
        
        // Check for excessive water
        const waterPercentage = waterTiles / totalTiles;
        if (waterPercentage > 0.25) {
            issues.push({
                type: 'excessive_water',
                severity: 'medium',
                message: `${(waterPercentage * 100).toFixed(1)}% water coverage may limit gameplay`,
                value: waterPercentage
            });
        }
        
        // Check transition tile ratio
        if (transitionTiles > this.options.maxTransitionTiles) {
            issues.push({
                type: 'excessive_transitions',
                severity: 'low',
                message: `High transition tile count may impact performance`,
                value: transitionTiles,
                threshold: this.options.maxTransitionTiles
            });
        }
        
        this.results.terrain = {
            valid: issues.length === 0 || !issues.some(i => i.severity === 'high'),
            issues,
            analysis: terrainAnalysis,
            buildablePercentage,
            waterPercentage
        };
    }

    /**
     * Validate resource distribution and balance
     */
    validateResources(terrain, resources, startingPositions) {
        const issues = [];
        const resourceAnalysis = {
            totalFields: resources.length,
            totalTiles: 0,
            totalValue: 0,
            typeDistribution: {},
            playerAnalysis: []
        };
        
        // Analyze overall resource distribution
        for (const field of resources) {
            for (const tile of field) {
                resourceAnalysis.totalTiles++;
                resourceAnalysis.totalValue += tile.value || 0;
                
                const type = tile.type || 'unknown';
                resourceAnalysis.typeDistribution[type] = 
                    (resourceAnalysis.typeDistribution[type] || 0) + 1;
            }
        }
        
        // Validate minimum resource requirements
        if (startingPositions.length > 0) {
            const avgResourcesPerPlayer = resourceAnalysis.totalValue / startingPositions.length;
            if (avgResourcesPerPlayer < this.options.minResourcesPerPlayer) {
                issues.push({
                    type: 'insufficient_resources',
                    severity: 'high',
                    message: `Average ${avgResourcesPerPlayer.toFixed(0)} resources per player (minimum: ${this.options.minResourcesPerPlayer})`,
                    value: avgResourcesPerPlayer,
                    threshold: this.options.minResourcesPerPlayer
                });
            }
        }
        
        // Analyze resource balance per player
        if (startingPositions.length > 1) {
            const playerResourceValues = this.calculatePlayerResourceValues(
                resources, startingPositions
            );
            
            const resourceBalance = this.analyzeResourceBalance(playerResourceValues);
            resourceAnalysis.playerAnalysis = playerResourceValues;
            
            if (!resourceBalance.balanced) {
                issues.push({
                    type: 'resource_imbalance',
                    severity: 'high',
                    message: `Resource imbalance detected: ${resourceBalance.maxDifference.toFixed(1)}% difference`,
                    value: resourceBalance.maxDifference,
                    threshold: this.options.resourceBalanceTolerance * 100
                });
            }
        }
        
        // Check resource accessibility
        const inaccessibleResources = this.findInaccessibleResources(terrain, resources, startingPositions);
        if (inaccessibleResources.length > 0) {
            issues.push({
                type: 'inaccessible_resources',
                severity: 'high',
                message: `${inaccessibleResources.length} resource fields are inaccessible`,
                value: inaccessibleResources
            });
        }
        
        this.results.resources = {
            valid: issues.length === 0 || !issues.some(i => i.severity === 'high'),
            issues,
            analysis: resourceAnalysis
        };
    }

    /**
     * Validate map accessibility and connectivity
     */
    validateAccessibility(terrain, startingPositions) {
        const issues = [];
        const accessibilityAnalysis = {
            connectedAreas: 0,
            chokepoints: [],
            deadEnds: [],
            isolatedAreas: []
        };
        
        // Find all connected regions
        const connectedRegions = this.findConnectedRegions(terrain);
        accessibilityAnalysis.connectedAreas = connectedRegions.length;
        
        // Check if all starting positions are connected
        if (startingPositions.length > 1) {
            const connectivity = this.checkStartingPositionConnectivity(
                terrain, startingPositions, connectedRegions
            );
            
            if (!connectivity.allConnected) {
                issues.push({
                    type: 'disconnected_starts',
                    severity: 'critical',
                    message: `${connectivity.isolatedPlayers.length} starting positions are isolated`,
                    value: connectivity.isolatedPlayers
                });
            }
        }
        
        // Identify chokepoints
        const chokepoints = this.identifyChokepoints(terrain);
        accessibilityAnalysis.chokepoints = chokepoints;
        
        const chokepointRatio = chokepoints.length / (terrain.length * terrain[0].length);
        if (chokepointRatio > this.options.maxChokepointRatio) {
            issues.push({
                type: 'excessive_chokepoints',
                severity: 'medium',
                message: `${(chokepointRatio * 100).toFixed(1)}% of map consists of chokepoints`,
                value: chokepointRatio,
                threshold: this.options.maxChokepointRatio
            });
        }
        
        // Find dead ends
        const deadEnds = this.findDeadEnds(terrain);
        accessibilityAnalysis.deadEnds = deadEnds;
        
        if (deadEnds.length > terrain.length * terrain[0].length * 0.05) {
            issues.push({
                type: 'excessive_dead_ends',
                severity: 'low',
                message: `High number of dead-end areas may limit tactical options`,
                value: deadEnds.length
            });
        }
        
        this.results.accessibility = {
            valid: issues.length === 0 || !issues.some(i => i.severity === 'critical'),
            issues,
            analysis: accessibilityAnalysis
        };
    }

    /**
     * Validate balance for multiplayer gameplay
     */
    validateBalance(terrain, resources, startingPositions) {
        const issues = [];
        const balanceAnalysis = {
            pathLengthBalance: null,
            expansionBalance: null,
            tacticalBalance: null
        };
        
        // Analyze path lengths between players
        const pathAnalysis = this.analyzePathLengths(terrain, startingPositions);
        balanceAnalysis.pathLengthBalance = pathAnalysis;
        
        if (!pathAnalysis.balanced) {
            issues.push({
                type: 'path_length_imbalance',
                severity: 'medium',
                message: `Path length variance: ${pathAnalysis.variance.toFixed(1)}%`,
                value: pathAnalysis.variance,
                threshold: this.options.pathLengthTolerance * 100
            });
        }
        
        // Analyze expansion opportunities
        const expansionAnalysis = this.analyzeExpansionOpportunities(terrain, startingPositions);
        balanceAnalysis.expansionBalance = expansionAnalysis;
        
        if (!expansionAnalysis.balanced) {
            issues.push({
                type: 'expansion_imbalance',
                severity: 'medium',
                message: 'Unequal expansion opportunities detected',
                value: expansionAnalysis
            });
        }
        
        // Analyze tactical advantages
        const tacticalAnalysis = this.analyzeTacticalBalance(terrain, startingPositions);
        balanceAnalysis.tacticalBalance = tacticalAnalysis;
        
        if (tacticalAnalysis.imbalances.length > 0) {
            issues.push({
                type: 'tactical_imbalance',
                severity: 'low',
                message: `${tacticalAnalysis.imbalances.length} tactical imbalances detected`,
                value: tacticalAnalysis.imbalances
            });
        }
        
        this.results.balance = {
            valid: issues.length === 0 || !issues.some(i => i.severity === 'high'),
            issues,
            analysis: balanceAnalysis
        };
    }

    /**
     * Validate performance characteristics
     */
    validatePerformance(terrain, resources) {
        const issues = [];
        const performanceAnalysis = {
            complexityScore: 0,
            renderingComplexity: 0,
            pathfindingComplexity: 0
        };
        
        // Calculate terrain complexity
        const terrainComplexity = this.calculateTerrainComplexity(terrain);
        performanceAnalysis.complexityScore = terrainComplexity.total;
        performanceAnalysis.renderingComplexity = terrainComplexity.rendering;
        performanceAnalysis.pathfindingComplexity = terrainComplexity.pathfinding;
        
        if (terrainComplexity.total > this.options.maxComplexityScore) {
            issues.push({
                type: 'high_complexity',
                severity: 'medium',
                message: `High map complexity may impact performance`,
                value: terrainComplexity.total,
                threshold: this.options.maxComplexityScore
            });
        }
        
        // Check resource field complexity
        if (resources) {
            const resourceComplexity = this.calculateResourceComplexity(resources);
            if (resourceComplexity > 200) {
                issues.push({
                    type: 'complex_resources',
                    severity: 'low',
                    message: `Complex resource distribution may impact performance`,
                    value: resourceComplexity
                });
            }
        }
        
        this.results.performance = {
            valid: issues.length === 0 || !issues.some(i => i.severity === 'high'),
            issues,
            analysis: performanceAnalysis
        };
    }

    /**
     * Calculate overall validation score
     */
    calculateOverallScore() {
        const weights = {
            terrain: 0.25,
            resources: 0.20,
            accessibility: 0.25,
            balance: 0.20,
            performance: 0.10
        };
        
        let totalScore = 0;
        let validCategories = 0;
        
        for (const [category, weight] of Object.entries(weights)) {
            if (this.results[category]) {
                const categoryScore = this.results[category].valid ? 100 : 
                    this.calculateCategoryScore(this.results[category]);
                totalScore += categoryScore * weight;
                validCategories++;
            }
        }
        
        const overallScore = validCategories > 0 ? totalScore : 0;
        const allValid = Object.values(this.results)
            .filter(r => typeof r === 'object' && 'valid' in r)
            .every(r => r.valid);
        
        this.results.overall = {
            valid: allValid,
            score: Math.round(overallScore),
            grade: this.getScoreGrade(overallScore)
        };
    }

    /**
     * Generate suggestions for fixing issues
     */
    generateFixSuggestions() {
        const suggestions = [];
        
        // Analyze issues and generate specific suggestions
        for (const [category, result] of Object.entries(this.results)) {
            if (result.issues && result.issues.length > 0) {
                for (const issue of result.issues) {
                    const suggestion = this.generateSuggestionForIssue(category, issue);
                    if (suggestion) {
                        suggestions.push(suggestion);
                    }
                }
            }
        }
        
        // Add general improvement suggestions
        if (this.results.overall.score < 80) {
            suggestions.push({
                type: 'general',
                priority: 'medium',
                message: 'Consider regenerating the map with adjusted parameters',
                action: 'regenerate'
            });
        }
        
        this.results.suggestions = suggestions.sort((a, b) => {
            const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
            return priorityOrder[a.priority] - priorityOrder[b.priority];
        });
    }

    // Helper methods for terrain analysis
    categorizeTerrainTile(tile) {
        if (!tile) return 'unknown';
        if (tile.startsWith('S')) return 'sand';
        if (tile.startsWith('D')) return 'dirt';
        if (tile.startsWith('W')) return 'water';
        if (tile.startsWith('SH')) return 'shore';
        if (tile.startsWith('T')) return 'trees';
        if (tile.startsWith('ROCK')) return 'rocks';
        return 'unknown';
    }

    isBuildableTerrain(tile) {
        return tile && (tile.startsWith('S') || tile.startsWith('D'));
    }

    isWaterTerrain(tile) {
        return tile && tile.startsWith('W');
    }

    isTransitionTerrain(tile) {
        return tile && tile.startsWith('SH');
    }

    checkTileNeighborhood(terrain, x, y, issues) {
        // Check for problematic tile combinations
        const tile = terrain[y][x];
        const neighbors = this.getNeighborTiles(terrain, x, y);
        
        // Check for isolated water tiles
        if (this.isWaterTerrain(tile)) {
            const waterNeighbors = neighbors.filter(n => this.isWaterTerrain(n)).length;
            if (waterNeighbors === 0) {
                issues.push({
                    type: 'isolated_water',
                    severity: 'low',
                    message: `Isolated water tile at (${x}, ${y})`,
                    position: { x, y }
                });
            }
        }
    }

    getNeighborTiles(terrain, x, y) {
        const neighbors = [];
        const directions = [[-1, 0], [1, 0], [0, -1], [0, 1]];
        
        for (const [dx, dy] of directions) {
            const nx = x + dx;
            const ny = y + dy;
            
            if (nx >= 0 && nx < terrain[0].length && 
                ny >= 0 && ny < terrain.length) {
                neighbors.push(terrain[ny][nx]);
            }
        }
        
        return neighbors;
    }

    calculatePlayerResourceValues(resources, startingPositions) {
        const playerValues = startingPositions.map(pos => ({
            playerId: pos.playerId || pos.id,
            position: pos,
            nearbyValue: 0,
            accessibleValue: 0
        }));
        
        const checkRadius = 15; // Tiles to check around each player
        
        for (const field of resources) {
            for (const tile of field) {
                for (const player of playerValues) {
                    const distance = Math.sqrt(
                        Math.pow(tile.x - player.position.x, 2) +
                        Math.pow(tile.y - player.position.y, 2)
                    );
                    
                    if (distance <= checkRadius) {
                        const distanceMultiplier = Math.max(0.1, 1.0 - (distance / checkRadius));
                        player.nearbyValue += (tile.value || 0) * distanceMultiplier;
                    }
                }
            }
        }
        
        return playerValues;
    }

    analyzeResourceBalance(playerValues) {
        if (playerValues.length < 2) {
            return { balanced: true, maxDifference: 0 };
        }
        
        const values = playerValues.map(p => p.nearbyValue);
        const avgValue = values.reduce((sum, val) => sum + val, 0) / values.length;
        const maxDifference = Math.max(...values.map(val => 
            Math.abs(val - avgValue) / avgValue
        ));
        
        return {
            balanced: maxDifference <= this.options.resourceBalanceTolerance,
            maxDifference: maxDifference * 100,
            values: values,
            average: avgValue
        };
    }

    findInaccessibleResources(terrain, resources, startingPositions) {
        const inaccessible = [];
        
        for (let i = 0; i < resources.length; i++) {
            const field = resources[i];
            if (field.length === 0) continue;
            
            const testTile = field[0];
            let accessible = false;
            
            for (const startPos of startingPositions) {
                const path = this.pathfinder.findPath(
                    terrain, 
                    { x: startPos.x, y: startPos.y },
                    { x: testTile.x, y: testTile.y }
                );
                
                if (path && path.length > 0) {
                    accessible = true;
                    break;
                }
            }
            
            if (!accessible) {
                inaccessible.push(i);
            }
        }
        
        return inaccessible;
    }

    // Additional helper methods...
    findConnectedRegions(terrain) {
        // Implementation for connected component analysis
        return []; // Placeholder
    }

    checkStartingPositionConnectivity(terrain, startingPositions, regions) {
        // Implementation for checking if all starts are connected
        return { allConnected: true, isolatedPlayers: [] }; // Placeholder
    }

    identifyChokepoints(terrain) {
        // Implementation for chokepoint identification
        return []; // Placeholder
    }

    findDeadEnds(terrain) {
        // Implementation for dead-end detection
        return []; // Placeholder
    }

    analyzePathLengths(terrain, startingPositions) {
        // Implementation for path length analysis
        return { balanced: true, variance: 0 }; // Placeholder
    }

    analyzeExpansionOpportunities(terrain, startingPositions) {
        // Implementation for expansion analysis
        return { balanced: true }; // Placeholder
    }

    analyzeTacticalBalance(terrain, startingPositions) {
        // Implementation for tactical analysis
        return { imbalances: [] }; // Placeholder
    }

    calculateTerrainComplexity(terrain) {
        let complexity = 0;
        let transitionCount = 0;
        
        for (let y = 0; y < terrain.length; y++) {
            for (let x = 0; x < terrain[y].length; x++) {
                const tile = terrain[y][x];
                const neighbors = this.getNeighborTiles(terrain, x, y);
                
                // Count terrain transitions
                const uniqueNeighbors = new Set(neighbors).size;
                if (uniqueNeighbors > 2) {
                    transitionCount++;
                }
                
                // Add complexity based on terrain type
                if (this.isTransitionTerrain(tile)) complexity += 2;
                else if (this.isWaterTerrain(tile)) complexity += 1.5;
                else complexity += 1;
            }
        }
        
        return {
            total: complexity + transitionCount * 3,
            rendering: transitionCount * 2,
            pathfinding: complexity * 0.5
        };
    }

    calculateResourceComplexity(resources) {
        let complexity = 0;
        
        for (const field of resources) {
            complexity += field.length;
            
            // Add complexity for irregular shapes
            if (field.length > 10) {
                complexity += Math.floor(field.length / 10);
            }
        }
        
        return complexity;
    }

    calculateCategoryScore(categoryResult) {
        if (!categoryResult.issues) return 100;
        
        const severityPenalties = {
            critical: 40,
            high: 25,
            medium: 10,
            low: 5
        };
        
        let penalty = 0;
        for (const issue of categoryResult.issues) {
            penalty += severityPenalties[issue.severity] || 5;
        }
        
        return Math.max(0, 100 - penalty);
    }

    getScoreGrade(score) {
        if (score >= 90) return 'A';
        if (score >= 80) return 'B';
        if (score >= 70) return 'C';
        if (score >= 60) return 'D';
        return 'F';
    }

    generateSuggestionForIssue(category, issue) {
        const suggestionMap = {
            insufficient_buildable_area: {
                message: 'Reduce water/obstacle coverage or add more buildable terrain',
                action: 'modify_terrain',
                priority: 'high'
            },
            resource_imbalance: {
                message: 'Redistribute resources to ensure fairness between players',
                action: 'rebalance_resources',
                priority: 'high'
            },
            disconnected_starts: {
                message: 'Add paths to connect isolated starting positions',
                action: 'add_connections',
                priority: 'critical'
            },
            excessive_chokepoints: {
                message: 'Widen narrow passages to improve unit movement',
                action: 'widen_paths',
                priority: 'medium'
            }
        };
        
        const template = suggestionMap[issue.type];
        if (!template) return null;
        
        return {
            type: issue.type,
            category,
            priority: template.priority,
            message: template.message,
            action: template.action,
            targetValue: issue.threshold
        };
    }

    resetResults() {
        this.results = {
            overall: { valid: false, score: 0 },
            terrain: { valid: false, issues: [] },
            resources: { valid: false, issues: [] },
            accessibility: { valid: false, issues: [] },
            balance: { valid: false, issues: [] },
            performance: { valid: false, issues: [] },
            suggestions: []
        };
    }
}

/**
 * Simple pathfinder for accessibility validation
 */
class MapPathfinder {
    findPath(terrain, start, end) {
        // Simple A* pathfinding implementation
        const openSet = [{ ...start, g: 0, h: this.heuristic(start, end), f: 0 }];
        const closedSet = new Set();
        
        while (openSet.length > 0) {
            openSet.sort((a, b) => a.f - b.f);
            const current = openSet.shift();
            
            if (current.x === end.x && current.y === end.y) {
                return this.reconstructPath(current);
            }
            
            closedSet.add(`${current.x},${current.y}`);
            
            const neighbors = this.getNeighbors(terrain, current.x, current.y);
            for (const neighbor of neighbors) {
                const key = `${neighbor.x},${neighbor.y}`;
                if (closedSet.has(key)) continue;
                
                const tentativeG = current.g + 1;
                const existing = openSet.find(n => n.x === neighbor.x && n.y === neighbor.y);
                
                if (!existing) {
                    neighbor.g = tentativeG;
                    neighbor.h = this.heuristic(neighbor, end);
                    neighbor.f = neighbor.g + neighbor.h;
                    neighbor.parent = current;
                    openSet.push(neighbor);
                } else if (tentativeG < existing.g) {
                    existing.g = tentativeG;
                    existing.f = existing.g + existing.h;
                    existing.parent = current;
                }
            }
        }
        
        return null; // No path found
    }
    
    heuristic(a, b) {
        return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
    }
    
    getNeighbors(terrain, x, y) {
        const neighbors = [];
        const directions = [[0, 1], [1, 0], [0, -1], [-1, 0]];
        
        for (const [dx, dy] of directions) {
            const nx = x + dx;
            const ny = y + dy;
            
            if (nx >= 0 && nx < terrain[0].length && 
                ny >= 0 && ny < terrain.length &&
                this.isPassable(terrain[ny][nx])) {
                neighbors.push({ x: nx, y: ny });
            }
        }
        
        return neighbors;
    }
    
    isPassable(tile) {
        return tile && !tile.startsWith('W') && !tile.startsWith('ROCK');
    }
    
    reconstructPath(node) {
        const path = [];
        let current = node;
        
        while (current) {
            path.unshift({ x: current.x, y: current.y });
            current = current.parent;
        }
        
        return path;
    }
}

export default MapValidator;