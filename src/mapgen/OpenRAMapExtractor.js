/**
 * OpenRA Map Extractor
 * 
 * Parses OpenRA .oramap files and extracts terrain data for Wave Function Collapse training.
 * OpenRA maps are ZIP archives containing YAML configuration and binary map data.
 * 
 * This extractor:
 * - Reads .oramap ZIP archives
 * - Parses map.yaml configuration
 * - Extracts terrain tile data from map.bin
 * - Converts OpenRA tile IDs to C&C tile format
 * - Handles multiple map formats (RA, TD, D2K)
 */

import fs from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import yaml from 'js-yaml';

class OpenRAMapExtractor {
    constructor() {
        // Map OpenRA terrain IDs to our C&C tile definitions
        // Based on TerrainGenerator.js tile types
        this.tileMapping = {
            // Clear/Sand terrain mappings
            'clear1': 'S01', 'clear2': 'S02', 'clear3': 'S03', 'clear4': 'S04',
            'clear5': 'S05', 'clear6': 'S06', 'clear7': 'S07', 'clear8': 'S08',
            
            // Desert/Dirt terrain mappings
            'desert1': 'D01', 'desert2': 'D02', 'desert3': 'D03', 'desert4': 'D04',
            'desert5': 'D05', 'desert6': 'D06', 'desert7': 'D07', 'desert8': 'D08',
            
            // Water mappings
            'water': 'W1', 'water2': 'W2',
            
            // Shore transitions
            'shore1': 'SH1', 'shore2': 'SH2', 'shore3': 'SH3',
            'shore4': 'SH4', 'shore5': 'SH5', 'shore6': 'SH6',
            
            // Tree mappings
            'tree01': 'T01', 'tree02': 'T02', 'tree03': 'T03',
            'tree05': 'T05', 'tree06': 'T06', 'tree07': 'T07',
            'tree08': 'T08', 'tree09': 'T09',
            
            // Rock formations
            'rock1': 'ROCK1', 'rock2': 'ROCK2', 'rock3': 'ROCK3',
            'rock4': 'ROCK4', 'rock5': 'ROCK5', 'rock6': 'ROCK6', 'rock7': 'ROCK7',
            
            // Additional OpenRA specific tiles
            'road': 'D03',     // Map roads to dirt
            'rough': 'D05',    // Map rough terrain to dirt variation
            'cliff': 'ROCK3',  // Map cliffs to rocks
            'bridge': 'D01',   // Map bridges to buildable terrain
        };
        
        // Default tile for unmapped terrain
        this.defaultTile = 'S01';
        
        // Track extraction statistics
        this.stats = {
            mapsProcessed: 0,
            tilesExtracted: 0,
            uniqueTiles: new Set(),
            errors: []
        };
    }
    
    /**
     * Extract terrain data from an OpenRA .oramap file
     * @param {string} mapPath - Path to the .oramap file
     * @returns {Object} Extracted map data with terrain grid and metadata
     */
    async extractMap(mapPath) {
        try {
            console.log(`Extracting map: ${mapPath}`);
            
            // Verify file exists
            if (!fs.existsSync(mapPath)) {
                throw new Error(`Map file not found: ${mapPath}`);
            }
            
            // Open ZIP archive
            const zip = new AdmZip(mapPath);
            const entries = zip.getEntries();
            
            // Find and parse map.yaml
            const mapYamlEntry = entries.find(e => e.entryName === 'map.yaml');
            if (!mapYamlEntry) {
                throw new Error('map.yaml not found in archive');
            }
            
            const mapConfig = yaml.load(mapYamlEntry.getData().toString('utf8'));
            
            // Extract map dimensions and metadata
            const metadata = this.extractMetadata(mapConfig);
            
            // Find and parse map.bin (binary terrain data)
            const mapBinEntry = entries.find(e => e.entryName === 'map.bin');
            if (!mapBinEntry) {
                throw new Error('map.bin not found in archive');
            }
            
            // Parse binary terrain data
            const terrainGrid = this.parseBinaryTerrain(
                mapBinEntry.getData(),
                metadata.width,
                metadata.height,
                mapConfig
            );
            
            // Update statistics
            this.stats.mapsProcessed++;
            this.stats.tilesExtracted += metadata.width * metadata.height;
            
            return {
                name: metadata.name,
                width: metadata.width,
                height: metadata.height,
                terrain: terrainGrid,
                metadata: metadata,
                source: path.basename(mapPath)
            };
            
        } catch (error) {
            console.error(`Error extracting map ${mapPath}:`, error.message);
            this.stats.errors.push({ map: mapPath, error: error.message });
            return null;
        }
    }
    
    /**
     * Extract metadata from map.yaml configuration
     */
    extractMetadata(mapConfig) {
        const metadata = {
            name: mapConfig.Title || 'Unknown',
            author: mapConfig.Author || 'Unknown',
            description: mapConfig.Description || '',
            width: 0,
            height: 0,
            tileset: mapConfig.Tileset || 'TEMPERAT',
            mapFormat: mapConfig.MapFormat || 11,
            players: []
        };
        
        // Extract map bounds
        if (mapConfig.MapSize) {
            const [width, height] = mapConfig.MapSize.split(',').map(s => parseInt(s.trim()));
            metadata.width = width;
            metadata.height = height;
        } else if (mapConfig.Bounds) {
            // Alternative bounds format
            const bounds = mapConfig.Bounds.split(',').map(s => parseInt(s.trim()));
            metadata.width = bounds[2];
            metadata.height = bounds[3];
        }
        
        // Extract player spawn points if available
        if (mapConfig.Players) {
            for (const [playerId, playerData] of Object.entries(mapConfig.Players)) {
                if (playerData.Playable !== false) {
                    metadata.players.push({
                        id: playerId,
                        name: playerData.Name || playerId,
                        faction: playerData.Faction || 'Random',
                        spawn: playerData.HomeLocation ? 
                            playerData.HomeLocation.split(',').map(s => parseInt(s.trim())) : 
                            null
                    });
                }
            }
        }
        
        return metadata;
    }
    
    /**
     * Parse binary terrain data from map.bin
     */
    parseBinaryTerrain(buffer, width, height, mapConfig) {
        const terrain = [];
        const tileSize = 2; // OpenRA uses 2 bytes per tile typically
        
        // Initialize terrain grid
        for (let y = 0; y < height; y++) {
            terrain[y] = [];
            for (let x = 0; x < width; x++) {
                terrain[y][x] = this.defaultTile;
            }
        }
        
        // Parse tile data based on map format
        const mapFormat = mapConfig.MapFormat || 11;
        
        if (mapFormat >= 11) {
            // Modern OpenRA format
            this.parseModernFormat(buffer, terrain, width, height, mapConfig);
        } else {
            // Legacy format
            this.parseLegacyFormat(buffer, terrain, width, height);
        }
        
        return terrain;
    }
    
    /**
     * Parse modern OpenRA map format (version 11+)
     */
    parseModernFormat(buffer, terrain, width, height, mapConfig) {
        let offset = 0;
        
        // Read tiles section
        // Format: [TileType:uint16][TileIndex:uint8]
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (offset + 3 <= buffer.length) {
                    const tileType = buffer.readUInt16LE(offset);
                    const tileIndex = buffer.readUInt8(offset + 2);
                    offset += 3;
                    
                    // Convert OpenRA tile to our format
                    terrain[y][x] = this.convertOpenRATile(tileType, tileIndex, mapConfig.Tileset);
                    this.stats.uniqueTiles.add(terrain[y][x]);
                }
            }
        }
        
        // Read resources section if present
        if (offset < buffer.length && mapConfig.Resources) {
            this.parseResources(buffer, offset, terrain, width, height);
        }
    }
    
    /**
     * Parse legacy OpenRA map format
     */
    parseLegacyFormat(buffer, terrain, width, height) {
        let offset = 0;
        const tileSize = 2;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (offset + tileSize <= buffer.length) {
                    const tileId = buffer.readUInt16LE(offset);
                    offset += tileSize;
                    
                    // Simple conversion for legacy format
                    terrain[y][x] = this.convertLegacyTile(tileId);
                    this.stats.uniqueTiles.add(terrain[y][x]);
                }
            }
        }
    }
    
    /**
     * Convert OpenRA tile ID to our C&C tile format
     */
    convertOpenRATile(tileType, tileIndex, tileset) {
        // Build tile identifier based on tileset
        const tilesetPrefix = this.getTilesetPrefix(tileset);
        
        // Map based on tile type ranges
        if (tileType >= 0 && tileType < 16) {
            // Clear/sand terrain
            return `S0${(tileIndex % 8) + 1}`;
        } else if (tileType >= 16 && tileType < 32) {
            // Desert/dirt terrain
            return `D0${(tileIndex % 8) + 1}`;
        } else if (tileType >= 32 && tileType < 48) {
            // Water tiles
            return tileIndex % 2 === 0 ? 'W1' : 'W2';
        } else if (tileType >= 48 && tileType < 64) {
            // Shore transitions
            return `SH${(tileIndex % 6) + 1}`;
        } else if (tileType >= 64 && tileType < 128) {
            // Trees
            const treeTypes = ['T01', 'T02', 'T03', 'T05', 'T06', 'T07', 'T08', 'T09'];
            return treeTypes[tileIndex % treeTypes.length];
        } else if (tileType >= 128 && tileType < 160) {
            // Rocks
            return `ROCK${(tileIndex % 7) + 1}`;
        } else {
            // Unknown tile type - use default
            return this.defaultTile;
        }
    }
    
    /**
     * Convert legacy tile ID
     */
    convertLegacyTile(tileId) {
        // Simple modulo-based mapping for legacy tiles
        if (tileId < 100) {
            return `S0${(tileId % 8) + 1}`;
        } else if (tileId < 200) {
            return `D0${(tileId % 8) + 1}`;
        } else if (tileId < 250) {
            return tileId % 2 === 0 ? 'W1' : 'W2';
        } else {
            return this.defaultTile;
        }
    }
    
    /**
     * Get tileset prefix for conversion
     */
    getTilesetPrefix(tileset) {
        const prefixMap = {
            'TEMPERAT': 'T',
            'DESERT': 'D',
            'SNOW': 'S',
            'INTERIOR': 'I',
            'JUNGLE': 'J'
        };
        return prefixMap[tileset] || 'T';
    }
    
    /**
     * Parse resource overlay data
     */
    parseResources(buffer, offset, terrain, width, height) {
        // Resources are typically stored as overlay data
        // Skip for now as we focus on terrain extraction
        // This could be extended to extract tiberium/ore positions
    }
    
    /**
     * Extract all maps from a directory
     */
    async extractDirectory(dirPath, recursive = true) {
        const results = [];
        
        try {
            const files = fs.readdirSync(dirPath);
            
            for (const file of files) {
                const filePath = path.join(dirPath, file);
                const stat = fs.statSync(filePath);
                
                if (stat.isDirectory() && recursive) {
                    // Recursively process subdirectories
                    const subResults = await this.extractDirectory(filePath, recursive);
                    results.push(...subResults);
                } else if (file.endsWith('.oramap')) {
                    // Process map file
                    const mapData = await this.extractMap(filePath);
                    if (mapData) {
                        results.push(mapData);
                    }
                }
            }
        } catch (error) {
            console.error(`Error processing directory ${dirPath}:`, error.message);
            this.stats.errors.push({ directory: dirPath, error: error.message });
        }
        
        return results;
    }
    
    /**
     * Extract terrain patterns from YAML map files (alternative format)
     */
    async extractYamlMap(yamlPath) {
        try {
            const yamlContent = fs.readFileSync(yamlPath, 'utf8');
            const mapData = yaml.load(yamlContent);
            
            // Extract terrain from Tiles section if present
            if (mapData.Tiles) {
                const terrain = this.parseTilesSection(mapData.Tiles);
                
                return {
                    name: mapData.Title || path.basename(yamlPath),
                    terrain: terrain,
                    metadata: {
                        format: 'yaml',
                        source: yamlPath
                    }
                };
            }
            
            return null;
        } catch (error) {
            console.error(`Error parsing YAML map ${yamlPath}:`, error.message);
            return null;
        }
    }
    
    /**
     * Parse Tiles section from YAML format
     */
    parseTilesSection(tilesData) {
        const terrain = [];
        let maxX = 0, maxY = 0;
        
        // Find map bounds
        for (const [coords, tileInfo] of Object.entries(tilesData)) {
            const [x, y] = coords.split(',').map(s => parseInt(s.trim()));
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        }
        
        // Initialize terrain grid
        for (let y = 0; y <= maxY; y++) {
            terrain[y] = [];
            for (let x = 0; x <= maxX; x++) {
                terrain[y][x] = this.defaultTile;
            }
        }
        
        // Fill terrain data
        for (const [coords, tileInfo] of Object.entries(tilesData)) {
            const [x, y] = coords.split(',').map(s => parseInt(s.trim()));
            const tileType = typeof tileInfo === 'string' ? tileInfo : tileInfo.Type;
            
            // Convert tile type to our format
            terrain[y][x] = this.mapYamlTile(tileType);
            this.stats.uniqueTiles.add(terrain[y][x]);
        }
        
        return terrain;
    }
    
    /**
     * Map YAML tile type to our format
     */
    mapYamlTile(tileType) {
        // Direct mapping if exists
        if (this.tileMapping[tileType.toLowerCase()]) {
            return this.tileMapping[tileType.toLowerCase()];
        }
        
        // Pattern-based mapping
        if (tileType.includes('clear') || tileType.includes('sand')) {
            return `S0${(Math.floor(Math.random() * 8) + 1)}`;
        } else if (tileType.includes('desert') || tileType.includes('dirt')) {
            return `D0${(Math.floor(Math.random() * 8) + 1)}`;
        } else if (tileType.includes('water')) {
            return Math.random() > 0.5 ? 'W1' : 'W2';
        } else if (tileType.includes('tree')) {
            const trees = ['T01', 'T02', 'T03', 'T05', 'T06', 'T07', 'T08', 'T09'];
            return trees[Math.floor(Math.random() * trees.length)];
        } else if (tileType.includes('rock') || tileType.includes('cliff')) {
            return `ROCK${Math.floor(Math.random() * 7) + 1}`;
        }
        
        return this.defaultTile;
    }
    
    /**
     * Get extraction statistics
     */
    getStatistics() {
        return {
            mapsProcessed: this.stats.mapsProcessed,
            tilesExtracted: this.stats.tilesExtracted,
            uniqueTileTypes: this.stats.uniqueTiles.size,
            uniqueTiles: Array.from(this.stats.uniqueTiles),
            errors: this.stats.errors,
            successRate: this.stats.mapsProcessed > 0 ? 
                ((this.stats.mapsProcessed - this.stats.errors.length) / this.stats.mapsProcessed * 100).toFixed(2) + '%' :
                '0%'
        };
    }
    
    /**
     * Reset statistics
     */
    resetStatistics() {
        this.stats = {
            mapsProcessed: 0,
            tilesExtracted: 0,
            uniqueTiles: new Set(),
            errors: []
        };
    }
}

export default OpenRAMapExtractor;