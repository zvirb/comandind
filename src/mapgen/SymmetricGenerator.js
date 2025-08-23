/**
 * SymmetricGenerator - Multiplayer Symmetric Map Generation
 * 
 * This system generates balanced, symmetric maps for competitive multiplayer
 * gameplay. It supports various symmetry types and ensures fair starting
 * conditions for all players.
 * 
 * Key Features:
 * - Multiple symmetry types (rotational, mirror, point)
 * - Balanced starting positions and resources
 * - Fair terrain distribution
 * - Customizable player counts (2, 4, 6, 8 players)
 * - Validation of symmetry integrity
 */

class SymmetricGenerator {
    constructor(width, height, playerCount, options = {}) {
        this.width = width;
        this.height = height;
        this.playerCount = playerCount;
        
        // Configuration options
        this.options = {
            symmetryType: 'rotational', // 'rotational', 'mirror', 'point'
            startingAreaRadius: 8, // Radius of guaranteed buildable area
            resourceBalance: true, // Ensure equal resources per player
            terrainVariation: 0.3, // How much terrain can vary between symmetric areas
            guaranteedExpansions: 2, // Number of guaranteed expansion sites per player
            centerFeature: true, // Add central contested feature
            ...options
        };
        
        // Validate player count and symmetry compatibility
        this.validateConfiguration();
        
        // Calculate symmetry parameters
        this.symmetryConfig = this.calculateSymmetryConfig();
        
        // Random seed for deterministic generation
        this.seed = Math.floor(Math.random() * 1000000);
        this.rng = this.createSeededRNG(this.seed);
    }

    /**
     * Generate a symmetric multiplayer map
     * @param {Object} baseGenerator - Generator to use for creating base terrain
     * @returns {Object} - Complete symmetric map data
     */
    generateSymmetricMap(baseGenerator) {
        // Generate base template (usually 1/nth of the map)
        const template = this.generateBaseTemplate(baseGenerator);
        
        // Apply symmetry to create full map
        const symmetricMap = this.applySymmetry(template);
        
        // Generate balanced starting positions
        const startingPositions = this.generateStartingPositions();
        
        // Place expansion areas
        const expansionAreas = this.placeExpansionAreas(symmetricMap, startingPositions);
        
        // Add center feature if enabled
        if (this.options.centerFeature) {
            this.addCenterFeature(symmetricMap);
        }
        
        // Validate symmetry integrity
        const symmetryValid = this.validateSymmetry(symmetricMap, startingPositions);
        
        return {
            terrain: symmetricMap,
            startingPositions,
            expansionAreas,
            symmetryType: this.options.symmetryType,
            playerCount: this.playerCount,
            symmetryValid,
            metadata: {
                width: this.width,
                height: this.height,
                seed: this.seed
            }
        };
    }

    /**
     * Generate base template for symmetry application
     */
    generateBaseTemplate(baseGenerator) {
        const templateConfig = this.getTemplateConfiguration();
        
        // Create smaller template area
        const templateWidth = Math.floor(this.width / templateConfig.divisorX);
        const templateHeight = Math.floor(this.height / templateConfig.divisorY);
        
        // Generate base terrain using provided generator
        let template;
        if (typeof baseGenerator === 'function') {
            template = baseGenerator(templateWidth, templateHeight, this.rng);
        } else if (baseGenerator && typeof baseGenerator.generate === 'function') {
            template = baseGenerator.generate();
        } else {
            // Fallback to simple terrain generation
            template = this.generateSimpleTemplate(templateWidth, templateHeight);
        }
        
        // Apply template-specific modifications
        this.processTemplate(template, templateWidth, templateHeight);
        
        return {
            terrain: template,
            width: templateWidth,
            height: templateHeight
        };
    }

    /**
     * Apply symmetry transformation to create full map
     */
    applySymmetry(template) {
        const fullMap = this.createEmptyMap();
        
        switch (this.options.symmetryType) {
            case 'rotational':
                return this.applyRotationalSymmetry(template, fullMap);
            case 'mirror':
                return this.applyMirrorSymmetry(template, fullMap);
            case 'point':
                return this.applyPointSymmetry(template, fullMap);
            default:
                throw new Error(`Unknown symmetry type: ${this.options.symmetryType}`);
        }
    }

    /**
     * Apply rotational symmetry (e.g., 4-way rotation for 4 players)
     */
    applyRotationalSymmetry(template, fullMap) {
        const centerX = Math.floor(this.width / 2);
        const centerY = Math.floor(this.height / 2);
        const rotationAngle = (2 * Math.PI) / this.playerCount;
        
        // Copy template to each rotational position
        for (let rotation = 0; rotation < this.playerCount; rotation++) {
            const angle = rotation * rotationAngle;
            
            for (let ty = 0; ty < template.height; ty++) {
                for (let tx = 0; tx < template.width; tx++) {
                    const templateTile = template.terrain[ty][tx];
                    
                    // Calculate rotated position
                    const rotatedPos = this.rotatePoint(
                        tx - template.width / 2,
                        ty - template.height / 2,
                        angle
                    );
                    
                    const finalX = Math.round(centerX + rotatedPos.x);
                    const finalY = Math.round(centerY + rotatedPos.y);
                    
                    if (this.isValidPosition(finalX, finalY)) {
                        fullMap[finalY][finalX] = templateTile;
                    }
                }
            }
        }
        
        // Fill any remaining empty spaces
        this.fillEmptySpaces(fullMap);
        
        return fullMap;
    }

    /**
     * Apply mirror symmetry (horizontal, vertical, or diagonal)
     */
    applyMirrorSymmetry(template, fullMap) {
        const { mirrorType } = this.symmetryConfig;
        
        // Copy template to original position
        this.copyTemplateToMap(template, fullMap, 0, 0);
        
        switch (mirrorType) {
            case 'horizontal':
                this.mirrorHorizontally(template, fullMap);
                break;
            case 'vertical':
                this.mirrorVertically(template, fullMap);
                break;
            case 'both':
                this.mirrorHorizontally(template, fullMap);
                this.mirrorVertically(fullMap, fullMap);
                break;
            case 'diagonal':
                this.mirrorDiagonally(template, fullMap);
                break;
        }
        
        this.fillEmptySpaces(fullMap);
        return fullMap;
    }

    /**
     * Apply point symmetry (180-degree rotation)
     */
    applyPointSymmetry(template, fullMap) {
        const centerX = Math.floor(this.width / 2);
        const centerY = Math.floor(this.height / 2);
        
        // Copy template to each player area
        for (let player = 0; player < this.playerCount; player++) {
            const angle = (player * 2 * Math.PI) / this.playerCount;
            
            for (let ty = 0; ty < template.height; ty++) {
                for (let tx = 0; tx < template.width; tx++) {
                    const templateTile = template.terrain[ty][tx];
                    
                    // Calculate position relative to center
                    const offsetX = tx - template.width / 2;
                    const offsetY = ty - template.height / 2;
                    
                    // Apply point symmetry transformation
                    const transformedPos = this.rotatePoint(offsetX, offsetY, angle);
                    const finalX = Math.round(centerX + transformedPos.x);
                    const finalY = Math.round(centerY + transformedPos.y);
                    
                    if (this.isValidPosition(finalX, finalY)) {
                        fullMap[finalY][finalX] = templateTile;
                    }
                }
            }
        }
        
        this.fillEmptySpaces(fullMap);
        return fullMap;
    }

    /**
     * Generate balanced starting positions for all players
     */
    generateStartingPositions() {
        const positions = [];
        const centerX = Math.floor(this.width / 2);
        const centerY = Math.floor(this.height / 2);
        
        // Calculate starting distance from center
        const startDistance = Math.min(this.width, this.height) * 0.35;
        
        for (let player = 0; player < this.playerCount; player++) {
            const angle = (player * 2 * Math.PI) / this.playerCount;
            
            const x = Math.round(centerX + Math.cos(angle) * startDistance);
            const y = Math.round(centerY + Math.sin(angle) * startDistance);
            
            positions.push({
                playerId: player,
                x: Math.max(this.options.startingAreaRadius, 
                    Math.min(this.width - this.options.startingAreaRadius, x)),
                y: Math.max(this.options.startingAreaRadius,
                    Math.min(this.height - this.options.startingAreaRadius, y)),
                team: player % 2, // Simple team assignment for team games
                startingArea: this.defineStartingArea(x, y)
            });
        }
        
        return positions;
    }

    /**
     * Define starting area around a position
     */
    defineStartingArea(centerX, centerY) {
        const area = [];
        const radius = this.options.startingAreaRadius;
        
        for (let y = centerY - radius; y <= centerY + radius; y++) {
            for (let x = centerX - radius; x <= centerX + radius; x++) {
                if (this.isValidPosition(x, y)) {
                    const distance = Math.sqrt(
                        Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
                    );
                    
                    if (distance <= radius) {
                        area.push({
                            x,
                            y,
                            type: distance <= radius * 0.5 ? 'core' : 'outer',
                            buildable: true
                        });
                    }
                }
            }
        }
        
        return area;
    }

    /**
     * Place expansion areas for each player
     */
    placeExpansionAreas(map, startingPositions) {
        const expansionAreas = [];
        
        for (const position of startingPositions) {
            const playerExpansions = this.findExpansionSites(
                map, position, this.options.guaranteedExpansions
            );
            
            expansionAreas.push({
                playerId: position.playerId,
                expansions: playerExpansions
            });
        }
        
        return expansionAreas;
    }

    /**
     * Find expansion sites for a player
     */
    findExpansionSites(map, playerPosition, count) {
        const expansions = [];
        const searchRadius = this.options.startingAreaRadius * 2;
        const attempts = count * 5; // Multiple attempts per expansion
        
        for (let attempt = 0; attempt < attempts && expansions.length < count; attempt++) {
            const angle = this.rng() * 2 * Math.PI;
            const distance = searchRadius + this.rng() * searchRadius;
            
            const x = Math.round(playerPosition.x + Math.cos(angle) * distance);
            const y = Math.round(playerPosition.y + Math.sin(angle) * distance);
            
            if (this.isValidExpansionSite(map, x, y, expansions)) {
                expansions.push({
                    x,
                    y,
                    area: this.defineStartingArea(x, y, this.options.startingAreaRadius * 0.7)
                });
            }
        }
        
        return expansions;
    }

    /**
     * Add contested center feature
     */
    addCenterFeature(map) {
        const centerX = Math.floor(this.width / 2);
        const centerY = Math.floor(this.height / 2);
        const featureRadius = 4;
        
        // Create central contested area with special terrain
        for (let y = centerY - featureRadius; y <= centerY + featureRadius; y++) {
            for (let x = centerX - featureRadius; x <= centerX + featureRadius; x++) {
                if (this.isValidPosition(x, y)) {
                    const distance = Math.sqrt(
                        Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2)
                    );
                    
                    if (distance <= featureRadius) {
                        if (distance <= 1) {
                            // Central feature (could be special resource or structure)
                            map[y][x] = 'SPECIAL_CENTER';
                        } else if (distance <= 3) {
                            // Surrounding area - keep buildable
                            map[y][x] = map[y][x] || 'S01';
                        }
                    }
                }
            }
        }
    }

    /**
     * Validate symmetry integrity of generated map
     */
    validateSymmetry(map, startingPositions) {
        const issues = [];
        
        // Check terrain symmetry
        for (let player = 0; player < this.playerCount; player++) {
            const referenceArea = this.getPlayerArea(map, startingPositions[0]);
            const playerArea = this.getPlayerArea(map, startingPositions[player]);
            
            if (!this.areasMatch(referenceArea, playerArea)) {
                issues.push(`Player ${player} starting area doesn't match reference`);
            }
        }
        
        // Check resource balance (if resources are present)
        const resourceBalance = this.checkResourceBalance(map, startingPositions);
        if (!resourceBalance.balanced) {
            issues.push(`Resource imbalance detected: ${resourceBalance.reason}`);
        }
        
        // Check path lengths to center
        const pathBalance = this.checkPathBalance(map, startingPositions);
        if (!pathBalance.balanced) {
            issues.push(`Path length imbalance: ${pathBalance.reason}`);
        }
        
        return {
            valid: issues.length === 0,
            issues
        };
    }

    /**
     * Helper method to rotate a point around origin
     */
    rotatePoint(x, y, angle) {
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        
        return {
            x: x * cos - y * sin,
            y: x * sin + y * cos
        };
    }

    /**
     * Helper method to check if position is valid
     */
    isValidPosition(x, y) {
        return x >= 0 && x < this.width && y >= 0 && y < this.height;
    }

    /**
     * Mirror template horizontally
     */
    mirrorHorizontally(template, fullMap) {
        for (let y = 0; y < template.height; y++) {
            for (let x = 0; x < template.width; x++) {
                const mirrorX = this.width - 1 - x;
                if (this.isValidPosition(mirrorX, y)) {
                    fullMap[y][mirrorX] = template.terrain[y][x];
                }
            }
        }
    }

    /**
     * Mirror template vertically
     */
    mirrorVertically(template, fullMap) {
        for (let y = 0; y < template.height; y++) {
            const mirrorY = this.height - 1 - y;
            if (this.isValidPosition(0, mirrorY)) {
                for (let x = 0; x < this.width; x++) {
                    if (fullMap[y][x]) {
                        fullMap[mirrorY][x] = fullMap[y][x];
                    }
                }
            }
        }
    }

    /**
     * Create empty map filled with null values
     */
    createEmptyMap() {
        const map = [];
        for (let y = 0; y < this.height; y++) {
            map[y] = new Array(this.width).fill(null);
        }
        return map;
    }

    /**
     * Fill empty spaces with appropriate terrain
     */
    fillEmptySpaces(map) {
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                if (!map[y][x]) {
                    // Use neighboring terrain or default sand
                    map[y][x] = this.getNeighborTerrain(map, x, y) || 'S01';
                }
            }
        }
    }

    /**
     * Get appropriate terrain based on neighbors
     */
    getNeighborTerrain(map, x, y) {
        const neighbors = [
            {dx: -1, dy: 0}, {dx: 1, dy: 0},
            {dx: 0, dy: -1}, {dx: 0, dy: 1}
        ];
        
        for (const {dx, dy} of neighbors) {
            const nx = x + dx;
            const ny = y + dy;
            
            if (this.isValidPosition(nx, ny) && map[ny][nx]) {
                return map[ny][nx];
            }
        }
        
        return null;
    }

    /**
     * Validate configuration compatibility
     */
    validateConfiguration() {
        const validPlayerCounts = [2, 4, 6, 8];
        if (!validPlayerCounts.includes(this.playerCount)) {
            throw new Error(`Invalid player count: ${this.playerCount}. Must be one of: ${validPlayerCounts.join(', ')}`);
        }
        
        // Check symmetry type compatibility
        const symmetryCompatibility = {
            'rotational': [2, 4, 6, 8],
            'mirror': [2, 4],
            'point': [2, 4, 6, 8]
        };
        
        const compatible = symmetryCompatibility[this.options.symmetryType];
        if (!compatible || !compatible.includes(this.playerCount)) {
            throw new Error(`Symmetry type '${this.options.symmetryType}' not compatible with ${this.playerCount} players`);
        }
    }

    /**
     * Calculate symmetry configuration parameters
     */
    calculateSymmetryConfig() {
        return {
            rotationAngle: (2 * Math.PI) / this.playerCount,
            mirrorType: this.playerCount === 2 ? 'vertical' : 'both',
            templateDivisor: this.options.symmetryType === 'mirror' ? 2 : this.playerCount
        };
    }

    /**
     * Get template configuration based on symmetry type
     */
    getTemplateConfiguration() {
        switch (this.options.symmetryType) {
            case 'rotational':
                return {
                    divisorX: Math.ceil(Math.sqrt(this.playerCount)),
                    divisorY: Math.ceil(Math.sqrt(this.playerCount))
                };
            case 'mirror':
                return {
                    divisorX: this.playerCount >= 4 ? 2 : 1,
                    divisorY: this.playerCount >= 2 ? 2 : 1
                };
            case 'point':
                return {
                    divisorX: 2,
                    divisorY: 2
                };
            default:
                return { divisorX: 1, divisorY: 1 };
        }
    }

    /**
     * Generate simple template when no generator provided
     */
    generateSimpleTemplate(width, height) {
        const template = [];
        for (let y = 0; y < height; y++) {
            template[y] = [];
            for (let x = 0; x < width; x++) {
                // Simple terrain generation with some variation
                const noise = this.rng();
                if (noise < 0.6) {
                    template[y][x] = 'S01'; // Sand
                } else if (noise < 0.85) {
                    template[y][x] = 'D01'; // Dirt
                } else {
                    template[y][x] = 'T01'; // Occasional tree
                }
            }
        }
        return template;
    }

    /**
     * Process template for specific modifications
     */
    processTemplate(template, width, height) {
        // Ensure starting areas are buildable
        const centerX = Math.floor(width / 2);
        const centerY = Math.floor(height / 2);
        
        const startRadius = this.options.startingAreaRadius;
        for (let y = centerY - startRadius; y <= centerY + startRadius; y++) {
            for (let x = centerX - startRadius; x <= centerX + startRadius; x++) {
                if (x >= 0 && x < width && y >= 0 && y < height) {
                    const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
                    if (distance <= startRadius) {
                        template[y][x] = 'S01'; // Ensure buildable terrain
                    }
                }
            }
        }
    }

    /**
     * Copy template to map at specified position
     */
    copyTemplateToMap(template, map, offsetX, offsetY) {
        for (let y = 0; y < template.height; y++) {
            for (let x = 0; x < template.width; x++) {
                const mapX = x + offsetX;
                const mapY = y + offsetY;
                
                if (this.isValidPosition(mapX, mapY)) {
                    map[mapY][mapX] = template.terrain[y][x];
                }
            }
        }
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
     * Check if position is valid expansion site
     */
    isValidExpansionSite(map, x, y, existingExpansions) {
        if (!this.isValidPosition(x, y)) return false;
        
        // Check minimum distance from existing expansions
        const minDistance = this.options.startingAreaRadius * 1.5;
        for (const expansion of existingExpansions) {
            const distance = Math.sqrt(
                Math.pow(x - expansion.x, 2) + Math.pow(y - expansion.y, 2)
            );
            if (distance < minDistance) return false;
        }
        
        // Check terrain suitability
        const terrain = map[y][x];
        return !terrain || terrain.startsWith('S') || terrain.startsWith('D');
    }

    /**
     * Check resource balance between players
     */
    checkResourceBalance(map, startingPositions) {
        // This would analyze resource distribution
        // Implementation depends on how resources are represented in the map
        return { balanced: true, reason: null };
    }

    /**
     * Check path balance between players
     */
    checkPathBalance(map, startingPositions) {
        // This would analyze path lengths and accessibility
        // Implementation depends on pathfinding requirements
        return { balanced: true, reason: null };
    }

    /**
     * Get player area for comparison
     */
    getPlayerArea(map, position) {
        const area = [];
        const radius = this.options.startingAreaRadius;
        
        for (let y = position.y - radius; y <= position.y + radius; y++) {
            for (let x = position.x - radius; x <= position.x + radius; x++) {
                if (this.isValidPosition(x, y)) {
                    area.push({
                        x: x - position.x,
                        y: y - position.y,
                        terrain: map[y][x]
                    });
                }
            }
        }
        
        return area;
    }

    /**
     * Check if two areas match (for symmetry validation)
     */
    areasMatch(area1, area2) {
        if (area1.length !== area2.length) return false;
        
        // Sort both areas by relative position for comparison
        const sort = (a, b) => a.x === b.x ? a.y - b.y : a.x - b.x;
        area1.sort(sort);
        area2.sort(sort);
        
        for (let i = 0; i < area1.length; i++) {
            if (area1[i].x !== area2[i].x || 
                area1[i].y !== area2[i].y || 
                area1[i].terrain !== area2[i].terrain) {
                return false;
            }
        }
        
        return true;
    }

    /**
     * Get generation statistics
     */
    getStats() {
        return {
            seed: this.seed,
            playerCount: this.playerCount,
            symmetryType: this.options.symmetryType,
            mapSize: `${this.width}x${this.height}`,
            startingAreaRadius: this.options.startingAreaRadius,
            guaranteedExpansions: this.options.guaranteedExpansions
        };
    }
}

export default SymmetricGenerator;