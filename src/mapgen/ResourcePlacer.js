/**
 * ResourcePlacer - Intelligent Resource Distribution System
 * 
 * This system provides strategic and balanced placement of resources (Tiberium)
 * across the map, ensuring fair gameplay while maintaining natural-looking
 * distribution patterns.
 * 
 * Key Features:
 * - Strategic resource placement algorithms
 * - Balanced distribution for multiplayer fairness
 * - Natural clustering and organic shapes
 * - Distance-based balancing
 * - Support for multiple resource types
 * - Expansion resource placement
 */

class ResourcePlacer {
    constructor(mapWidth, mapHeight, options = {}) {
        this.width = mapWidth;
        this.height = mapHeight;
        
        // Configuration options
        this.options = {
            resourceDensity: 0.08, // Percentage of map covered by resources
            clusterCount: 6, // Number of main resource clusters
            playerPositions: [], // Starting positions for balance calculations
            resourceTypes: ['green', 'blue'], // Types of resources to place
            minimumDistance: 5, // Minimum distance between resource clusters
            expansionResources: true, // Place resources for base expansion
            naturalVariation: 0.3, // How organic the resource shapes should be
            balanceRadius: 8, // Radius for resource balance calculations
            ...options
        };
        
        // Resource type definitions
        this.resourceTypes = {
            green: {
                tiles: ['TI1', 'TI2', 'TI3'],
                frequency: 0.8, // 80% of resources are green
                clusterSize: { min: 8, max: 20 },
                value: 100 // Base value per tile
            },
            blue: {
                tiles: ['TI10', 'TI11', 'TI12'],
                frequency: 0.2, // 20% of resources are blue (rare)
                clusterSize: { min: 4, max: 10 },
                value: 300 // Higher value per tile
            }
        };
        
        // Placed resource fields
        this.resourceFields = [];
        this.placedClusters = [];
        
        // Random seed for deterministic placement
        this.seed = Math.floor(Math.random() * 1000000);
        this.rng = this.createSeededRNG(this.seed);
    }

    /**
     * Place resources on the terrain map
     * @param {Array} terrainMap - 2D array of terrain tiles
     * @param {Array} playerPositions - Array of {x, y} player starting positions
     * @returns {Array} - Array of resource fields
     */
    placeResources(terrainMap, playerPositions = []) {
        this.options.playerPositions = playerPositions;
        this.resourceFields = [];
        this.placedClusters = [];
        
        // Generate resource cluster positions
        const clusterPositions = this.generateClusterPositions(terrainMap);
        
        // Place main resource clusters
        for (const position of clusterPositions) {
            const cluster = this.createResourceCluster(
                terrainMap,
                position.x,
                position.y,
                position.type,
                position.size
            );
            
            if (cluster && cluster.length > 0) {
                this.resourceFields.push(cluster);
                this.placedClusters.push({
                    x: position.x,
                    y: position.y,
                    type: position.type,
                    size: cluster.length
                });
            }
        }
        
        // Place expansion resources if enabled
        if (this.options.expansionResources) {
            this.placeExpansionResources(terrainMap);
        }
        
        // Balance resources for multiplayer
        if (playerPositions.length > 1) {
            this.balanceResourcesForPlayers(terrainMap, playerPositions);
        }
        
        // Add small scattered resource patches
        this.addScatteredResources(terrainMap);
        
        return this.resourceFields;
    }

    /**
     * Generate strategic positions for main resource clusters
     */
    generateClusterPositions(terrainMap) {
        const positions = [];
        const attempts = this.options.clusterCount * 3; // Allow multiple attempts
        
        for (let attempt = 0; attempt < attempts && positions.length < this.options.clusterCount; attempt++) {
            const x = Math.floor(this.rng() * (this.width - 10)) + 5;
            const y = Math.floor(this.rng() * (this.height - 10)) + 5;
            
            // Check if position is valid
            if (!this.isValidResourcePosition(terrainMap, x, y)) {
                continue;
            }
            
            // Check minimum distance from existing clusters
            if (this.isTooCloseToExistingCluster(x, y)) {
                continue;
            }
            
            // Check distance from player positions (not too close, not too far)
            if (!this.isGoodDistanceFromPlayers(x, y)) {
                continue;
            }
            
            // Determine resource type based on frequency
            const resourceType = this.selectResourceType();
            const baseSize = this.resourceTypes[resourceType].clusterSize;
            const clusterSize = Math.floor(
                baseSize.min + this.rng() * (baseSize.max - baseSize.min)
            );
            
            positions.push({
                x,
                y,
                type: resourceType,
                size: clusterSize
            });
        }
        
        return positions;
    }

    /**
     * Create a natural-looking resource cluster
     */
    createResourceCluster(terrainMap, centerX, centerY, resourceType, targetSize) {
        const cluster = [];
        const visited = new Set();
        const resourceTiles = this.resourceTypes[resourceType].tiles;
        
        // Start with center tile
        const queue = [{x: centerX, y: centerY, distance: 0}];
        visited.add(`${centerX},${centerY}`);
        
        while (queue.length > 0 && cluster.length < targetSize) {
            const {x, y, distance} = queue.shift();
            
            // Check if tile is valid for resource placement
            if (!this.isValidResourcePosition(terrainMap, x, y)) {
                continue;
            }
            
            // Calculate density based on distance from center
            const maxDistance = Math.sqrt(targetSize / Math.PI) * 1.5;
            const density = Math.max(0.3, 1.0 - (distance / maxDistance));
            
            // Add organic variation
            const variation = this.rng() * this.options.naturalVariation;
            const finalDensity = Math.min(1.0, density + variation);
            
            // Place resource tile with calculated density
            const tileId = resourceTiles[Math.floor(this.rng() * resourceTiles.length)];
            cluster.push({
                x,
                y,
                type: resourceType,
                tileId,
                density: finalDensity,
                value: this.resourceTypes[resourceType].value * finalDensity
            });
            
            // Add neighboring tiles to queue for organic growth
            if (cluster.length < targetSize) {
                this.addNeighborsToQueue(queue, visited, x, y, distance + 1, maxDistance);
            }
        }
        
        return cluster;
    }

    /**
     * Add neighboring positions to the growth queue
     */
    addNeighborsToQueue(queue, visited, x, y, distance, maxDistance) {
        if (distance >= maxDistance) return;
        
        const neighbors = [
            {x: x - 1, y: y}, {x: x + 1, y: y},
            {x: x, y: y - 1}, {x: x, y: y + 1},
            // Diagonal neighbors for more organic shapes
            {x: x - 1, y: y - 1}, {x: x + 1, y: y + 1},
            {x: x - 1, y: y + 1}, {x: x + 1, y: y - 1}
        ];
        
        // Randomize neighbor order for organic growth
        for (let i = neighbors.length - 1; i > 0; i--) {
            const j = Math.floor(this.rng() * (i + 1));
            [neighbors[i], neighbors[j]] = [neighbors[j], neighbors[i]];
        }
        
        for (const neighbor of neighbors) {
            const key = `${neighbor.x},${neighbor.y}`;
            if (!visited.has(key) && this.isInBounds(neighbor.x, neighbor.y)) {
                visited.add(key);
                
                // Probabilistic growth for organic shapes
                const growthProbability = Math.max(0.3, 1.0 - (distance / maxDistance));
                if (this.rng() < growthProbability) {
                    queue.push({
                        x: neighbor.x,
                        y: neighbor.y,
                        distance
                    });
                }
            }
        }
    }

    /**
     * Place expansion resources near map edges
     */
    placeExpansionResources(terrainMap) {
        const expansionZones = [
            {x: 5, y: 5, width: 8, height: 8}, // Northwest
            {x: this.width - 13, y: 5, width: 8, height: 8}, // Northeast
            {x: 5, y: this.height - 13, width: 8, height: 8}, // Southwest
            {x: this.width - 13, y: this.height - 13, width: 8, height: 8} // Southeast
        ];
        
        for (const zone of expansionZones) {
            // Skip if zone conflicts with existing clusters
            if (this.hasNearbyCluster(zone.x + zone.width/2, zone.y + zone.height/2, 10)) {
                continue;
            }
            
            // Place smaller resource patches in expansion zones
            const expansionCount = 1 + Math.floor(this.rng() * 2); // 1-2 patches per zone
            
            for (let i = 0; i < expansionCount; i++) {
                const x = zone.x + Math.floor(this.rng() * zone.width);
                const y = zone.y + Math.floor(this.rng() * zone.height);
                
                if (this.isValidResourcePosition(terrainMap, x, y)) {
                    const resourceType = this.selectResourceType();
                    const cluster = this.createResourceCluster(
                        terrainMap, x, y, resourceType, 4 + Math.floor(this.rng() * 4)
                    );
                    
                    if (cluster && cluster.length > 0) {
                        this.resourceFields.push(cluster);
                    }
                }
            }
        }
    }

    /**
     * Balance resources for multiplayer fairness
     */
    balanceResourcesForPlayers(terrainMap, playerPositions) {
        // Calculate resource value for each player's vicinity
        const playerResources = playerPositions.map(pos => ({
            x: pos.x,
            y: pos.y,
            nearbyValue: this.calculateNearbyResourceValue(pos.x, pos.y),
            needsBalance: false
        }));
        
        // Find resource imbalances
        const avgValue = playerResources.reduce((sum, pr) => sum + pr.nearbyValue, 0) / playerResources.length;
        const tolerance = avgValue * 0.2; // 20% tolerance
        
        for (const playerResource of playerResources) {
            if (playerResource.nearbyValue < avgValue - tolerance) {
                playerResource.needsBalance = true;
            }
        }
        
        // Add balancing resources for disadvantaged players
        for (const playerResource of playerResources) {
            if (playerResource.needsBalance) {
                this.addBalancingResources(
                    terrainMap,
                    playerResource.x,
                    playerResource.y,
                    avgValue - playerResource.nearbyValue
                );
            }
        }
    }

    /**
     * Add balancing resources for a specific player
     */
    addBalancingResources(terrainMap, playerX, playerY, valueDeficit) {
        const searchRadius = this.options.balanceRadius;
        const attempts = 20;
        
        for (let attempt = 0; attempt < attempts && valueDeficit > 0; attempt++) {
            // Find position within balance radius
            const angle = this.rng() * 2 * Math.PI;
            const distance = 3 + this.rng() * (searchRadius - 3);
            const x = Math.round(playerX + Math.cos(angle) * distance);
            const y = Math.round(playerY + Math.sin(angle) * distance);
            
            if (this.isValidResourcePosition(terrainMap, x, y) && 
                !this.hasNearbyCluster(x, y, 3)) {
                
                const resourceType = this.selectResourceType();
                const clusterSize = Math.min(8, Math.ceil(valueDeficit / this.resourceTypes[resourceType].value));
                
                const cluster = this.createResourceCluster(
                    terrainMap, x, y, resourceType, clusterSize
                );
                
                if (cluster && cluster.length > 0) {
                    this.resourceFields.push(cluster);
                    valueDeficit -= cluster.reduce((sum, tile) => sum + tile.value, 0);
                }
            }
        }
    }

    /**
     * Add small scattered resource patches for exploration
     */
    addScatteredResources(terrainMap) {
        const scatterCount = Math.floor(this.width * this.height * 0.001); // Small patches
        
        for (let i = 0; i < scatterCount; i++) {
            const x = Math.floor(this.rng() * this.width);
            const y = Math.floor(this.rng() * this.height);
            
            if (this.isValidResourcePosition(terrainMap, x, y) && 
                !this.hasNearbyCluster(x, y, 4)) {
                
                const resourceType = this.selectResourceType();
                const cluster = this.createResourceCluster(
                    terrainMap, x, y, resourceType, 2 + Math.floor(this.rng() * 3)
                );
                
                if (cluster && cluster.length > 0) {
                    this.resourceFields.push(cluster);
                }
            }
        }
    }

    /**
     * Check if position is valid for resource placement
     */
    isValidResourcePosition(terrainMap, x, y) {
        if (!this.isInBounds(x, y)) return false;
        
        const tile = terrainMap[y][x];
        
        // Resources can't be placed on water, trees, rocks, or shores
        if (tile.startsWith('W') || tile.startsWith('SH') || 
            tile.startsWith('T') || tile.startsWith('ROCK')) {
            return false;
        }
        
        // Resources prefer sand and dirt terrain
        return tile.startsWith('S') || tile.startsWith('D');
    }

    /**
     * Check if position is too close to existing clusters
     */
    isTooCloseToExistingCluster(x, y) {
        for (const cluster of this.placedClusters) {
            const distance = Math.sqrt(
                Math.pow(x - cluster.x, 2) + Math.pow(y - cluster.y, 2)
            );
            if (distance < this.options.minimumDistance) {
                return true;
            }
        }
        return false;
    }

    /**
     * Check if position has good distance from players
     */
    isGoodDistanceFromPlayers(x, y) {
        if (this.options.playerPositions.length === 0) return true;
        
        const minDistanceFromPlayer = 6; // Not too close to starting position
        const maxDistanceFromPlayer = Math.min(this.width, this.height) * 0.4; // Not too far
        
        for (const player of this.options.playerPositions) {
            const distance = Math.sqrt(
                Math.pow(x - player.x, 2) + Math.pow(y - player.y, 2)
            );
            
            if (distance < minDistanceFromPlayer || distance > maxDistanceFromPlayer) {
                return false;
            }
        }
        
        return true;
    }

    /**
     * Select resource type based on frequency settings
     */
    selectResourceType() {
        const random = this.rng();
        let cumulativeFreq = 0;
        
        for (const [type, config] of Object.entries(this.resourceTypes)) {
            cumulativeFreq += config.frequency;
            if (random <= cumulativeFreq) {
                return type;
            }
        }
        
        // Fallback to first type
        return Object.keys(this.resourceTypes)[0];
    }

    /**
     * Check if there's a nearby cluster within radius
     */
    hasNearbyCluster(x, y, radius) {
        for (const cluster of this.placedClusters) {
            const distance = Math.sqrt(
                Math.pow(x - cluster.x, 2) + Math.pow(y - cluster.y, 2)
            );
            if (distance < radius) {
                return true;
            }
        }
        return false;
    }

    /**
     * Calculate total resource value near a position
     */
    calculateNearbyResourceValue(x, y) {
        let totalValue = 0;
        const checkRadius = this.options.balanceRadius;
        
        for (const field of this.resourceFields) {
            for (const tile of field) {
                const distance = Math.sqrt(
                    Math.pow(x - tile.x, 2) + Math.pow(y - tile.y, 2)
                );
                
                if (distance <= checkRadius) {
                    // Value decreases with distance
                    const distanceMultiplier = Math.max(0.1, 1.0 - (distance / checkRadius));
                    totalValue += tile.value * distanceMultiplier;
                }
            }
        }
        
        return totalValue;
    }

    /**
     * Check if coordinates are within map bounds
     */
    isInBounds(x, y) {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    /**
     * Create seeded random number generator
     */
    createSeededRNG(seed) {
        let currentSeed = seed;
        return function() {
            currentSeed = (currentSeed * 9301 + 49297) % 233280;
            return currentSeed / 233280;
        };
    }

    /**
     * Analyze resource distribution for balance checking
     */
    analyzeDistribution() {
        const analysis = {
            totalFields: this.resourceFields.length,
            totalTiles: this.resourceFields.reduce((sum, field) => sum + field.length, 0),
            totalValue: 0,
            resourceTypes: {},
            playerBalance: []
        };
        
        // Calculate totals by type
        for (const field of this.resourceFields) {
            for (const tile of field) {
                analysis.totalValue += tile.value;
                
                if (!analysis.resourceTypes[tile.type]) {
                    analysis.resourceTypes[tile.type] = {
                        tiles: 0,
                        value: 0,
                        fields: 0
                    };
                }
                
                analysis.resourceTypes[tile.type].tiles++;
                analysis.resourceTypes[tile.type].value += tile.value;
            }
        }
        
        // Count fields by type
        for (const field of this.resourceFields) {
            if (field.length > 0) {
                const type = field[0].type;
                if (analysis.resourceTypes[type]) {
                    analysis.resourceTypes[type].fields++;
                }
            }
        }
        
        // Player balance analysis
        for (const player of this.options.playerPositions) {
            analysis.playerBalance.push({
                x: player.x,
                y: player.y,
                nearbyValue: this.calculateNearbyResourceValue(player.x, player.y)
            });
        }
        
        return analysis;
    }

    /**
     * Get placement statistics
     */
    getStats() {
        return {
            seed: this.seed,
            fieldsPlaced: this.resourceFields.length,
            clustersPlaced: this.placedClusters.length,
            totalResourceTiles: this.resourceFields.reduce((sum, field) => sum + field.length, 0),
            distribution: this.analyzeDistribution()
        };
    }
}

export default ResourcePlacer;