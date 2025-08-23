/**
 * Map Pattern Analyzer
 * 
 * Advanced pattern analysis for extracted map data.
 * Identifies common structures, terrain features, and strategic patterns
 * to improve WFC generation quality.
 * 
 * Features:
 * - Identifies base locations and choke points
 * - Detects terrain features (lakes, forests, cliffs)
 * - Analyzes symmetry and balance
 * - Extracts tactical patterns
 * - Validates pattern coherence
 */

import fs from 'fs';
import path from 'path';

class MapPatternAnalyzer {
    constructor() {
        // Pattern detection configurations
        this.config = {
            // Minimum size for feature detection
            minFeatureSize: 3,
            
            // Choke point detection threshold
            chokePointThreshold: 3,
            
            // Base location criteria
            baseAreaMinSize: 25, // 5x5 minimum
            baseAreaMaxWater: 0.1, // Max 10% water
            baseAreaMaxObstacles: 0.2, // Max 20% obstacles
            
            // Symmetry detection tolerance
            symmetryTolerance: 0.85, // 85% match for symmetry
            
            // Pattern classification thresholds
            patternMinOccurrences: 3,
            patternMinConfidence: 0.7
        };
        
        // Analyzed patterns storage
        this.patterns = {
            bases: [],
            chokePoints: [],
            terrainFeatures: [],
            tacticalPatterns: [],
            symmetryData: null
        };
        
        // Statistics
        this.stats = {
            mapsAnalyzed: 0,
            basesFound: 0,
            chokePointsFound: 0,
            featuresFound: 0,
            patternsExtracted: 0
        };
    }
    
    /**
     * Analyze a collection of maps to extract patterns
     * @param {Array} extractedMaps - Maps from OpenRAMapExtractor
     * @returns {Object} Analysis results with patterns and insights
     */
    analyzeMaps(extractedMaps) {
        console.log(`Analyzing ${extractedMaps.length} maps for patterns...`);
        
        const analysisResults = {
            individualAnalyses: [],
            aggregatePatterns: null,
            recommendations: []
        };
        
        // Analyze each map individually
        for (const mapData of extractedMaps) {
            if (!mapData || !mapData.terrain) continue;
            
            const mapAnalysis = this.analyzeMap(mapData);
            analysisResults.individualAnalyses.push(mapAnalysis);
            this.stats.mapsAnalyzed++;
        }
        
        // Aggregate patterns across all maps
        analysisResults.aggregatePatterns = this.aggregatePatterns(analysisResults.individualAnalyses);
        
        // Generate recommendations for WFC
        analysisResults.recommendations = this.generateRecommendations(analysisResults.aggregatePatterns);
        
        console.log(`Pattern analysis complete. Stats:`, this.stats);
        
        return analysisResults;
    }
    
    /**
     * Analyze a single map
     */
    analyzeMap(mapData) {
        const { terrain, width, height, name } = mapData;
        
        const analysis = {
            mapName: name,
            dimensions: { width, height },
            bases: [],
            chokePoints: [],
            terrainFeatures: [],
            symmetry: null,
            balance: null,
            tacticalValue: 0
        };
        
        // Find potential base locations
        analysis.bases = this.findBaseLocations(terrain, width, height);
        this.stats.basesFound += analysis.bases.length;
        
        // Detect choke points
        analysis.chokePoints = this.findChokePoints(terrain, width, height);
        this.stats.chokePointsFound += analysis.chokePoints.length;
        
        // Identify terrain features
        analysis.terrainFeatures = this.identifyTerrainFeatures(terrain, width, height);
        this.stats.featuresFound += analysis.terrainFeatures.length;
        
        // Analyze map symmetry
        analysis.symmetry = this.analyzeSymmetry(terrain, width, height);
        
        // Calculate map balance
        analysis.balance = this.calculateBalance(analysis);
        
        // Assess tactical value
        analysis.tacticalValue = this.assessTacticalValue(analysis);
        
        return analysis;
    }
    
    /**
     * Find potential base locations
     */
    findBaseLocations(terrain, width, height) {
        const bases = [];
        const searchGrid = this.config.baseAreaMinSize;
        
        // Scan map in grid sections
        for (let y = 0; y <= height - searchGrid; y += Math.floor(searchGrid / 2)) {
            for (let x = 0; x <= width - searchGrid; x += Math.floor(searchGrid / 2)) {
                const area = this.extractArea(terrain, x, y, searchGrid, searchGrid);
                
                if (this.isValidBaseLocation(area)) {
                    bases.push({
                        x: x + Math.floor(searchGrid / 2),
                        y: y + Math.floor(searchGrid / 2),
                        size: searchGrid,
                        quality: this.rateBaseLocation(area),
                        terrain: this.summarizeTerrain(area)
                    });
                }
            }
        }
        
        // Remove overlapping bases, keep highest quality
        return this.filterOverlappingBases(bases);
    }
    
    /**
     * Extract area from terrain
     */
    extractArea(terrain, startX, startY, width, height) {
        const area = [];
        
        for (let y = 0; y < height; y++) {
            const row = [];
            for (let x = 0; x < width; x++) {
                const terrainY = startY + y;
                const terrainX = startX + x;
                
                if (terrainY < terrain.length && terrainX < terrain[0].length) {
                    row.push(terrain[terrainY][terrainX]);
                } else {
                    row.push(null);
                }
            }
            area.push(row);
        }
        
        return area;
    }
    
    /**
     * Check if area is valid for base placement
     */
    isValidBaseLocation(area) {
        let totalTiles = 0;
        let waterTiles = 0;
        let obstacleTiles = 0;
        let buildableTiles = 0;
        
        for (const row of area) {
            for (const tile of row) {
                if (!tile) continue;
                
                totalTiles++;
                
                if (tile.startsWith('W') || tile.startsWith('SH')) {
                    waterTiles++;
                } else if (tile.startsWith('T') || tile.startsWith('ROCK')) {
                    obstacleTiles++;
                } else if (tile.startsWith('S') || tile.startsWith('D')) {
                    buildableTiles++;
                }
            }
        }
        
        if (totalTiles === 0) return false;
        
        const waterRatio = waterTiles / totalTiles;
        const obstacleRatio = obstacleTiles / totalTiles;
        const buildableRatio = buildableTiles / totalTiles;
        
        return waterRatio <= this.config.baseAreaMaxWater &&
               obstacleRatio <= this.config.baseAreaMaxObstacles &&
               buildableRatio >= 0.6; // At least 60% buildable
    }
    
    /**
     * Rate base location quality
     */
    rateBaseLocation(area) {
        let quality = 0;
        const centerX = Math.floor(area[0].length / 2);
        const centerY = Math.floor(area.length / 2);
        
        // Check for flat buildable terrain in center
        for (let y = centerY - 1; y <= centerY + 1; y++) {
            for (let x = centerX - 1; x <= centerX + 1; x++) {
                if (y >= 0 && y < area.length && x >= 0 && x < area[0].length) {
                    const tile = area[y][x];
                    if (tile && (tile.startsWith('S') || tile.startsWith('D'))) {
                        quality += 10;
                    }
                }
            }
        }
        
        // Check for defensive terrain on edges
        for (let i = 0; i < area.length; i++) {
            // Left and right edges
            if (area[i][0] && (area[i][0].startsWith('T') || area[i][0].startsWith('ROCK'))) {
                quality += 2;
            }
            if (area[i][area[0].length - 1] && 
                (area[i][area[0].length - 1].startsWith('T') || 
                 area[i][area[0].length - 1].startsWith('ROCK'))) {
                quality += 2;
            }
        }
        
        // Top and bottom edges
        for (let j = 0; j < area[0].length; j++) {
            if (area[0][j] && (area[0][j].startsWith('T') || area[0][j].startsWith('ROCK'))) {
                quality += 2;
            }
            if (area[area.length - 1][j] && 
                (area[area.length - 1][j].startsWith('T') || 
                 area[area.length - 1][j].startsWith('ROCK'))) {
                quality += 2;
            }
        }
        
        return quality;
    }
    
    /**
     * Summarize terrain composition
     */
    summarizeTerrain(area) {
        const summary = {
            sand: 0,
            dirt: 0,
            water: 0,
            trees: 0,
            rocks: 0,
            total: 0
        };
        
        for (const row of area) {
            for (const tile of row) {
                if (!tile) continue;
                
                summary.total++;
                
                if (tile.startsWith('S')) summary.sand++;
                else if (tile.startsWith('D')) summary.dirt++;
                else if (tile.startsWith('W') || tile.startsWith('SH')) summary.water++;
                else if (tile.startsWith('T')) summary.trees++;
                else if (tile.startsWith('ROCK')) summary.rocks++;
            }
        }
        
        // Convert to percentages
        if (summary.total > 0) {
            for (const key of Object.keys(summary)) {
                if (key !== 'total') {
                    summary[key] = Math.round((summary[key] / summary.total) * 100);
                }
            }
        }
        
        return summary;
    }
    
    /**
     * Filter overlapping base locations
     */
    filterOverlappingBases(bases) {
        const filtered = [];
        const used = new Set();
        
        // Sort by quality descending
        bases.sort((a, b) => b.quality - a.quality);
        
        for (const base of bases) {
            const key = `${Math.floor(base.x / 10)},${Math.floor(base.y / 10)}`;
            
            if (!used.has(key)) {
                filtered.push(base);
                
                // Mark surrounding areas as used
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        const nearKey = `${Math.floor(base.x / 10) + dx},${Math.floor(base.y / 10) + dy}`;
                        used.add(nearKey);
                    }
                }
            }
        }
        
        return filtered;
    }
    
    /**
     * Find choke points on the map
     */
    findChokePoints(terrain, width, height) {
        const chokePoints = [];
        
        // Scan for narrow passages
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                if (this.isChokePoint(terrain, x, y, width, height)) {
                    chokePoints.push({
                        x,
                        y,
                        type: this.classifyChokePoint(terrain, x, y, width, height),
                        importance: this.rateChokePointImportance(terrain, x, y, width, height)
                    });
                }
            }
        }
        
        // Filter to keep only significant choke points
        return chokePoints.filter(cp => cp.importance > 5);
    }
    
    /**
     * Check if position is a choke point
     */
    isChokePoint(terrain, x, y, width, height) {
        const tile = terrain[y][x];
        
        // Must be passable terrain
        if (!tile || tile.startsWith('W') || tile.startsWith('ROCK') || tile.startsWith('T')) {
            return false;
        }
        
        // Check for constriction pattern
        let verticalBlocked = 0;
        let horizontalBlocked = 0;
        
        // Check vertical axis
        if (y > 0 && this.isBlocking(terrain[y - 1][x])) verticalBlocked++;
        if (y < height - 1 && this.isBlocking(terrain[y + 1][x])) verticalBlocked++;
        
        // Check horizontal axis
        if (x > 0 && this.isBlocking(terrain[y][x - 1])) horizontalBlocked++;
        if (x < width - 1 && this.isBlocking(terrain[y][x + 1])) horizontalBlocked++;
        
        // Choke point if constrained on perpendicular axes
        return (verticalBlocked >= 1 && horizontalBlocked === 0) ||
               (horizontalBlocked >= 1 && verticalBlocked === 0);
    }
    
    /**
     * Check if tile is blocking
     */
    isBlocking(tile) {
        return tile && (
            tile.startsWith('W') ||
            tile.startsWith('ROCK') ||
            tile.startsWith('T')
        );
    }
    
    /**
     * Classify choke point type
     */
    classifyChokePoint(terrain, x, y, width, height) {
        const surroundingTiles = [];
        
        for (let dy = -2; dy <= 2; dy++) {
            for (let dx = -2; dx <= 2; dx++) {
                const nx = x + dx;
                const ny = y + dy;
                
                if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                    surroundingTiles.push(terrain[ny][nx]);
                }
            }
        }
        
        const hasWater = surroundingTiles.some(t => t && t.startsWith('W'));
        const hasRocks = surroundingTiles.some(t => t && t.startsWith('ROCK'));
        const hasTrees = surroundingTiles.some(t => t && t.startsWith('T'));
        
        if (hasWater && !hasRocks && !hasTrees) return 'bridge';
        if (hasRocks && !hasWater) return 'mountain_pass';
        if (hasTrees && !hasWater && !hasRocks) return 'forest_path';
        if (hasWater && (hasRocks || hasTrees)) return 'coastal_pass';
        
        return 'generic';
    }
    
    /**
     * Rate choke point importance
     */
    rateChokePointImportance(terrain, x, y, width, height) {
        let importance = 0;
        
        // Check how much area is accessible through this point
        const passableRadius = 5;
        let passableBefore = 0;
        let passableAfter = 0;
        
        // Count passable tiles on each side
        for (let dy = -passableRadius; dy <= passableRadius; dy++) {
            for (let dx = -passableRadius; dx <= passableRadius; dx++) {
                const nx = x + dx;
                const ny = y + dy;
                
                if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                    const tile = terrain[ny][nx];
                    if (tile && !this.isBlocking(tile)) {
                        if (dx < 0) passableBefore++;
                        if (dx > 0) passableAfter++;
                    }
                }
            }
        }
        
        // Higher importance if it connects large areas
        importance = Math.min(passableBefore, passableAfter);
        
        // Bonus for central location
        const centerX = width / 2;
        const centerY = height / 2;
        const distFromCenter = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
        const maxDist = Math.sqrt(Math.pow(width / 2, 2) + Math.pow(height / 2, 2));
        
        importance += (1 - distFromCenter / maxDist) * 10;
        
        return importance;
    }
    
    /**
     * Identify terrain features
     */
    identifyTerrainFeatures(terrain, width, height) {
        const features = [];
        const visited = new Set();
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const key = `${x},${y}`;
                
                if (!visited.has(key)) {
                    const feature = this.extractFeature(terrain, x, y, width, height, visited);
                    
                    if (feature && feature.tiles.length >= this.config.minFeatureSize) {
                        features.push(this.classifyFeature(feature));
                        this.stats.patternsExtracted++;
                    }
                }
            }
        }
        
        return features;
    }
    
    /**
     * Extract connected feature using flood fill
     */
    extractFeature(terrain, startX, startY, width, height, visited) {
        const startTile = terrain[startY][startX];
        if (!startTile) return null;
        
        const tileType = this.getTileType(startTile);
        if (!tileType || tileType === 'mixed') return null;
        
        const feature = {
            type: tileType,
            tiles: [],
            bounds: {
                minX: startX,
                maxX: startX,
                minY: startY,
                maxY: startY
            }
        };
        
        const queue = [[startX, startY]];
        visited.add(`${startX},${startY}`);
        
        while (queue.length > 0) {
            const [x, y] = queue.shift();
            feature.tiles.push({ x, y });
            
            // Update bounds
            feature.bounds.minX = Math.min(feature.bounds.minX, x);
            feature.bounds.maxX = Math.max(feature.bounds.maxX, x);
            feature.bounds.minY = Math.min(feature.bounds.minY, y);
            feature.bounds.maxY = Math.max(feature.bounds.maxY, y);
            
            // Check neighbors
            const neighbors = [
                [x - 1, y], [x + 1, y],
                [x, y - 1], [x, y + 1]
            ];
            
            for (const [nx, ny] of neighbors) {
                const nKey = `${nx},${ny}`;
                
                if (nx >= 0 && nx < width && 
                    ny >= 0 && ny < height && 
                    !visited.has(nKey)) {
                    
                    const nTile = terrain[ny][nx];
                    if (nTile && this.getTileType(nTile) === tileType) {
                        visited.add(nKey);
                        queue.push([nx, ny]);
                    }
                }
            }
        }
        
        return feature;
    }
    
    /**
     * Get tile type category
     */
    getTileType(tile) {
        if (tile.startsWith('W') || tile.startsWith('SH')) return 'water';
        if (tile.startsWith('T')) return 'forest';
        if (tile.startsWith('ROCK')) return 'rocks';
        if (tile.startsWith('S') || tile.startsWith('D')) return 'terrain';
        return 'mixed';
    }
    
    /**
     * Classify extracted feature
     */
    classifyFeature(feature) {
        const width = feature.bounds.maxX - feature.bounds.minX + 1;
        const height = feature.bounds.maxY - feature.bounds.minY + 1;
        const area = feature.tiles.length;
        const density = area / (width * height);
        
        let classification = {
            type: feature.type,
            name: 'unknown',
            size: area,
            dimensions: { width, height },
            density: density,
            center: {
                x: Math.floor((feature.bounds.minX + feature.bounds.maxX) / 2),
                y: Math.floor((feature.bounds.minY + feature.bounds.maxY) / 2)
            }
        };
        
        // Classify based on type and characteristics
        if (feature.type === 'water') {
            if (area > 50) classification.name = 'lake';
            else if (width > height * 3 || height > width * 3) classification.name = 'river';
            else classification.name = 'pond';
        } else if (feature.type === 'forest') {
            if (area > 30) classification.name = 'large_forest';
            else if (area > 10) classification.name = 'forest';
            else classification.name = 'grove';
        } else if (feature.type === 'rocks') {
            if (width > height * 2 || height > width * 2) classification.name = 'cliff';
            else if (area > 15) classification.name = 'mountain';
            else classification.name = 'rock_formation';
        }
        
        return classification;
    }
    
    /**
     * Analyze map symmetry
     */
    analyzeSymmetry(terrain, width, height) {
        const symmetry = {
            horizontal: 0,
            vertical: 0,
            rotational: 0,
            diagonal: 0,
            type: 'none'
        };
        
        // Check horizontal symmetry
        let hMatches = 0;
        let hTotal = 0;
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < Math.floor(width / 2); x++) {
                const mirrorX = width - 1 - x;
                if (this.tilesMatch(terrain[y][x], terrain[y][mirrorX])) {
                    hMatches++;
                }
                hTotal++;
            }
        }
        symmetry.horizontal = hTotal > 0 ? hMatches / hTotal : 0;
        
        // Check vertical symmetry
        let vMatches = 0;
        let vTotal = 0;
        for (let y = 0; y < Math.floor(height / 2); y++) {
            for (let x = 0; x < width; x++) {
                const mirrorY = height - 1 - y;
                if (this.tilesMatch(terrain[y][x], terrain[mirrorY][x])) {
                    vMatches++;
                }
                vTotal++;
            }
        }
        symmetry.vertical = vTotal > 0 ? vMatches / vTotal : 0;
        
        // Check rotational symmetry (180 degrees)
        let rMatches = 0;
        let rTotal = 0;
        for (let y = 0; y < Math.floor(height / 2); y++) {
            for (let x = 0; x < width; x++) {
                const rotX = width - 1 - x;
                const rotY = height - 1 - y;
                if (this.tilesMatch(terrain[y][x], terrain[rotY][rotX])) {
                    rMatches++;
                }
                rTotal++;
            }
        }
        symmetry.rotational = rTotal > 0 ? rMatches / rTotal : 0;
        
        // Determine primary symmetry type
        const threshold = this.config.symmetryTolerance;
        if (symmetry.horizontal > threshold && symmetry.horizontal > symmetry.vertical) {
            symmetry.type = 'horizontal';
        } else if (symmetry.vertical > threshold && symmetry.vertical > symmetry.horizontal) {
            symmetry.type = 'vertical';
        } else if (symmetry.rotational > threshold) {
            symmetry.type = 'rotational';
        } else if (symmetry.horizontal > 0.6 && symmetry.vertical > 0.6) {
            symmetry.type = 'dual';
        }
        
        return symmetry;
    }
    
    /**
     * Check if two tiles match (similar type)
     */
    tilesMatch(tile1, tile2) {
        if (!tile1 || !tile2) return tile1 === tile2;
        
        // Extract tile type prefix
        const type1 = tile1.replace(/[0-9]/g, '');
        const type2 = tile2.replace(/[0-9]/g, '');
        
        return type1 === type2;
    }
    
    /**
     * Calculate map balance
     */
    calculateBalance(analysis) {
        const balance = {
            baseBalance: 0,
            resourceBalance: 0,
            terrainBalance: 0,
            overall: 0
        };
        
        // Base balance - check distribution
        if (analysis.bases.length >= 2) {
            const basePositions = analysis.bases.map(b => ({ x: b.x, y: b.y }));
            balance.baseBalance = this.calculatePositionBalance(basePositions);
        }
        
        // Terrain balance - check feature distribution
        if (analysis.terrainFeatures.length > 0) {
            const featurePositions = analysis.terrainFeatures.map(f => f.center);
            balance.terrainBalance = this.calculatePositionBalance(featurePositions);
        }
        
        // Overall balance
        balance.overall = (balance.baseBalance + balance.terrainBalance) / 2;
        
        return balance;
    }
    
    /**
     * Calculate position balance score
     */
    calculatePositionBalance(positions) {
        if (positions.length < 2) return 0;
        
        // Calculate center of mass
        let centerX = 0;
        let centerY = 0;
        for (const pos of positions) {
            centerX += pos.x;
            centerY += pos.y;
        }
        centerX /= positions.length;
        centerY /= positions.length;
        
        // Calculate variance from center
        let variance = 0;
        for (const pos of positions) {
            const dist = Math.sqrt(Math.pow(pos.x - centerX, 2) + Math.pow(pos.y - centerY, 2));
            variance += dist;
        }
        variance /= positions.length;
        
        // Lower variance = better balance
        return Math.max(0, 1 - variance / 50);
    }
    
    /**
     * Assess tactical value of map
     */
    assessTacticalValue(analysis) {
        let value = 0;
        
        // Value from base locations
        value += Math.min(analysis.bases.length * 10, 40);
        
        // Value from choke points
        value += Math.min(analysis.chokePoints.length * 5, 20);
        
        // Value from terrain variety
        const terrainTypes = new Set(analysis.terrainFeatures.map(f => f.type));
        value += terrainTypes.size * 5;
        
        // Value from balance
        value += analysis.balance.overall * 20;
        
        // Value from symmetry (for competitive maps)
        if (analysis.symmetry.type !== 'none') {
            value += 10;
        }
        
        return Math.min(value, 100); // Cap at 100
    }
    
    /**
     * Aggregate patterns across multiple maps
     */
    aggregatePatterns(analyses) {
        const aggregated = {
            commonBasePatterns: [],
            commonChokePatterns: [],
            commonFeatures: [],
            preferredSymmetry: null,
            averageBalance: 0,
            tacticalPatterns: []
        };
        
        // Aggregate base patterns
        const basePatterns = new Map();
        for (const analysis of analyses) {
            for (const base of analysis.bases) {
                const pattern = `${base.size}_${Math.round(base.quality / 10) * 10}`;
                basePatterns.set(pattern, (basePatterns.get(pattern) || 0) + 1);
            }
        }
        
        aggregated.commonBasePatterns = Array.from(basePatterns.entries())
            .filter(([_, count]) => count >= this.config.patternMinOccurrences)
            .map(([pattern, count]) => ({ pattern, occurrences: count }));
        
        // Aggregate choke patterns
        const chokeTypes = new Map();
        for (const analysis of analyses) {
            for (const choke of analysis.chokePoints) {
                chokeTypes.set(choke.type, (chokeTypes.get(choke.type) || 0) + 1);
            }
        }
        
        aggregated.commonChokePatterns = Array.from(chokeTypes.entries())
            .map(([type, count]) => ({ type, occurrences: count }));
        
        // Aggregate feature types
        const featureTypes = new Map();
        for (const analysis of analyses) {
            for (const feature of analysis.terrainFeatures) {
                const key = `${feature.type}_${feature.name}`;
                featureTypes.set(key, (featureTypes.get(key) || 0) + 1);
            }
        }
        
        aggregated.commonFeatures = Array.from(featureTypes.entries())
            .filter(([_, count]) => count >= this.config.patternMinOccurrences)
            .map(([feature, count]) => ({ feature, occurrences: count }));
        
        // Find preferred symmetry
        const symmetryTypes = new Map();
        for (const analysis of analyses) {
            if (analysis.symmetry && analysis.symmetry.type !== 'none') {
                symmetryTypes.set(
                    analysis.symmetry.type,
                    (symmetryTypes.get(analysis.symmetry.type) || 0) + 1
                );
            }
        }
        
        if (symmetryTypes.size > 0) {
            const sorted = Array.from(symmetryTypes.entries()).sort((a, b) => b[1] - a[1]);
            aggregated.preferredSymmetry = sorted[0][0];
        }
        
        // Calculate average balance
        let totalBalance = 0;
        let balanceCount = 0;
        for (const analysis of analyses) {
            if (analysis.balance) {
                totalBalance += analysis.balance.overall;
                balanceCount++;
            }
        }
        
        aggregated.averageBalance = balanceCount > 0 ? totalBalance / balanceCount : 0;
        
        return aggregated;
    }
    
    /**
     * Generate recommendations for WFC
     */
    generateRecommendations(aggregatePatterns) {
        const recommendations = [];
        
        // Base placement recommendations
        if (aggregatePatterns.commonBasePatterns.length > 0) {
            recommendations.push({
                category: 'base_placement',
                priority: 'high',
                suggestion: 'Ensure adequate buildable area clusters',
                details: `Common base sizes: ${aggregatePatterns.commonBasePatterns.map(p => p.pattern).join(', ')}`
            });
        }
        
        // Choke point recommendations
        if (aggregatePatterns.commonChokePatterns.length > 0) {
            const mostCommon = aggregatePatterns.commonChokePatterns[0];
            recommendations.push({
                category: 'choke_points',
                priority: 'medium',
                suggestion: `Include ${mostCommon.type} choke points for tactical depth`,
                details: 'Choke points add strategic value to maps'
            });
        }
        
        // Symmetry recommendations
        if (aggregatePatterns.preferredSymmetry) {
            recommendations.push({
                category: 'symmetry',
                priority: 'high',
                suggestion: `Consider ${aggregatePatterns.preferredSymmetry} symmetry for competitive balance`,
                details: 'Symmetrical maps ensure fair gameplay'
            });
        }
        
        // Feature variety recommendations
        if (aggregatePatterns.commonFeatures.length > 2) {
            recommendations.push({
                category: 'terrain_variety',
                priority: 'medium',
                suggestion: 'Include diverse terrain features',
                details: `Common features: ${aggregatePatterns.commonFeatures.map(f => f.feature).join(', ')}`
            });
        }
        
        // Balance recommendations
        if (aggregatePatterns.averageBalance < 0.6) {
            recommendations.push({
                category: 'balance',
                priority: 'high',
                suggestion: 'Improve positional balance of key features',
                details: 'Ensure resources and bases are evenly distributed'
            });
        }
        
        return recommendations;
    }
    
    /**
     * Export analysis results
     */
    exportAnalysis(analysisResults, outputPath) {
        try {
            const exportData = {
                metadata: {
                    analyzedAt: new Date().toISOString(),
                    mapsAnalyzed: this.stats.mapsAnalyzed,
                    configuration: this.config
                },
                statistics: this.stats,
                aggregatePatterns: analysisResults.aggregatePatterns,
                recommendations: analysisResults.recommendations,
                individualAnalyses: analysisResults.individualAnalyses.map(a => ({
                    mapName: a.mapName,
                    dimensions: a.dimensions,
                    baseCount: a.bases.length,
                    chokePointCount: a.chokePoints.length,
                    featureCount: a.terrainFeatures.length,
                    symmetry: a.symmetry.type,
                    balance: a.balance.overall,
                    tacticalValue: a.tacticalValue
                }))
            };
            
            fs.writeFileSync(outputPath, JSON.stringify(exportData, null, 2));
            console.log(`Analysis exported to: ${outputPath}`);
            
            return true;
        } catch (error) {
            console.error(`Error exporting analysis:`, error.message);
            return false;
        }
    }
}

export default MapPatternAnalyzer;