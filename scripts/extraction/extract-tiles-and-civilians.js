#!/usr/bin/env node

/**
 * Extract map tiles and civilian resources from C&C MIX files
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class TileAndCivilianExtractor {
    constructor() {
        this.mixPath = path.join(__dirname, 'public/assets/cnc-extracted');
        this.outputPath = path.join(__dirname, 'public/assets');
        
        // Known C&C tile and civilian asset patterns
        this.tilePatterns = {
            // Terrain tiles
            temperat: ['clear', 'water', 'road', 'rock', 'tree', 'river', 'shore', 'cliff', 'bridge'],
            winter: ['snow', 'ice', 'water', 'road', 'rock', 'tree', 'shore', 'cliff'],
            desert: ['sand', 'rock', 'spice', 'dune', 'water', 'road', 'cliff'],
            
            // Interior tiles  
            tempicnh: ['floor', 'wall', 'door', 'tech', 'computer', 'lab'],
            interior: ['floor', 'wall', 'door', 'panel', 'computer']
        };
        
        this.civilianPatterns = {
            structures: [
                'v01', 'v02', 'v03', 'v04', // Civilian buildings V01-V37
                'v05', 'v06', 'v07', 'v08',
                'v09', 'v10', 'v11', 'v12',
                'v13', 'v14', 'v15', 'v16',
                'v17', 'v18', 'v19', 'v20',
                'v21', 'v22', 'v23', 'v24',
                'v25', 'v26', 'v27', 'v28',
                'v29', 'v30', 'v31', 'v32',
                'v33', 'v34', 'v35', 'v36', 'v37',
                'arco', 'bio', 'hosp', 'miss' // Special civilian structures
            ],
            units: [
                'c1', 'c2', 'c3', 'c4', 'c5', // Civilians C1-C10
                'c6', 'c7', 'c8', 'c9', 'c10',
                'delphi', 'chan', 'moebius' // Named civilians
            ],
            vehicles: [
                'vice', 'truck', 'jeep', 'harvester'
            ]
        };
    }
    
    async extractFromMix(mixFile, patterns) {
        console.log(`\n📦 Processing ${mixFile}...`);
        const mixPath = path.join(this.mixPath, mixFile);
        
        if (!fs.existsSync(mixPath)) {
            console.log(`  ⚠️ ${mixFile} not found`);
            return [];
        }
        
        const extracted = [];
        
        // Read MIX file header
        const buffer = fs.readFileSync(mixPath);
        
        // C&C MIX format parsing (simplified)
        // This is a placeholder - actual MIX extraction would need proper format parsing
        console.log(`  📊 File size: ${buffer.length} bytes`);
        
        // Simulate extraction based on patterns
        for (const pattern of patterns) {
            // In a real implementation, we'd parse the MIX file format
            // For now, we'll create placeholder data
            extracted.push({
                name: pattern,
                type: 'tile',
                source: mixFile
            });
        }
        
        return extracted;
    }
    
    async extractTiles() {
        console.log('🗺️ EXTRACTING MAP TILES');
        console.log('='.repeat(50));
        
        const allTiles = [];
        
        // Extract terrain tiles
        for (const [terrain, patterns] of Object.entries(this.tilePatterns)) {
            const mixFile = `${terrain}.mix`;
            const tiles = await this.extractFromMix(mixFile, patterns);
            
            if (tiles.length > 0) {
                allTiles.push(...tiles);
                console.log(`  ✅ Found ${tiles.length} tile patterns in ${terrain}`);
            }
        }
        
        // Create tile output directory
        const tilesDir = path.join(this.outputPath, 'tiles');
        if (!fs.existsSync(tilesDir)) {
            fs.mkdirSync(tilesDir, { recursive: true });
        }
        
        // Create subdirectories for each terrain type
        for (const terrain of Object.keys(this.tilePatterns)) {
            const terrainDir = path.join(tilesDir, terrain);
            if (!fs.existsSync(terrainDir)) {
                fs.mkdirSync(terrainDir, { recursive: true });
            }
        }
        
        return allTiles;
    }
    
    async extractCivilians() {
        console.log('\n🏘️ EXTRACTING CIVILIAN RESOURCES');
        console.log('='.repeat(50));
        
        const allCivilians = [];
        
        // Check general.mix and conquer.mix for civilian assets
        const mixFiles = ['general.mix', 'conquer.mix', 'temperat.mix'];
        
        for (const mixFile of mixFiles) {
            console.log(`\n📦 Checking ${mixFile} for civilian assets...`);
            
            // Extract civilian structures
            const structures = await this.extractFromMix(
                mixFile, 
                this.civilianPatterns.structures
            );
            
            if (structures.length > 0) {
                allCivilians.push(...structures);
                console.log(`  🏢 Found ${structures.length} civilian structures`);
            }
            
            // Extract civilian units
            const units = await this.extractFromMix(
                mixFile,
                this.civilianPatterns.units
            );
            
            if (units.length > 0) {
                allCivilians.push(...units);
                console.log(`  👥 Found ${units.length} civilian units`);
            }
        }
        
        // Create civilian output directories
        const civilianDir = path.join(this.outputPath, 'sprites/civilian');
        const subdirs = ['structures', 'units', 'vehicles'];
        
        for (const subdir of subdirs) {
            const dir = path.join(civilianDir, subdir);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        }
        
        return allCivilians;
    }
    
    generateTileConfig() {
        // Generate tile configuration for the game
        const tileConfig = {
            terrains: {
                temperate: {
                    name: 'Temperate',
                    tiles: {
                        clear: { passable: true, buildable: true },
                        water: { passable: false, buildable: false },
                        road: { passable: true, buildable: false, speedBonus: 1.5 },
                        rock: { passable: false, buildable: false },
                        tree: { passable: false, buildable: false, harvestable: true },
                        river: { passable: false, buildable: false },
                        shore: { passable: true, buildable: false },
                        cliff: { passable: false, buildable: false },
                        bridge: { passable: true, buildable: false }
                    }
                },
                winter: {
                    name: 'Winter',
                    tiles: {
                        snow: { passable: true, buildable: true, speedPenalty: 0.8 },
                        ice: { passable: true, buildable: false, speedPenalty: 0.7 },
                        water: { passable: false, buildable: false },
                        road: { passable: true, buildable: false, speedBonus: 1.3 },
                        rock: { passable: false, buildable: false },
                        tree: { passable: false, buildable: false },
                        shore: { passable: true, buildable: false },
                        cliff: { passable: false, buildable: false }
                    }
                },
                desert: {
                    name: 'Desert',
                    tiles: {
                        sand: { passable: true, buildable: true, speedPenalty: 0.9 },
                        rock: { passable: false, buildable: false },
                        spice: { passable: true, buildable: false, harvestable: true },
                        dune: { passable: true, buildable: false, speedPenalty: 0.7 },
                        water: { passable: false, buildable: false },
                        road: { passable: true, buildable: false, speedBonus: 1.4 },
                        cliff: { passable: false, buildable: false }
                    }
                },
                interior: {
                    name: 'Interior',
                    tiles: {
                        floor: { passable: true, buildable: true },
                        wall: { passable: false, buildable: false },
                        door: { passable: true, buildable: false },
                        tech: { passable: true, buildable: false },
                        computer: { passable: false, buildable: false },
                        lab: { passable: true, buildable: false }
                    }
                }
            },
            tileSize: 24, // Standard C&C tile size
            defaultTerrain: 'temperate'
        };
        
        const configPath = path.join(this.outputPath, 'tiles/tile-config.json');
        fs.writeFileSync(configPath, JSON.stringify(tileConfig, null, 2));
        console.log(`\n📝 Tile configuration saved to ${configPath}`);
        
        return tileConfig;
    }
    
    generateCivilianConfig() {
        // Generate civilian asset configuration
        const civilianConfig = {
            structures: {
                // Civilian buildings
                v01: { name: 'Church', health: 400, armor: 'wood' },
                v02: { name: 'Han\'s House', health: 400, armor: 'wood' },
                v03: { name: 'Farmhouse', health: 400, armor: 'wood' },
                v04: { name: 'House', health: 400, armor: 'wood' },
                v05: { name: 'Greenhouse', health: 400, armor: 'wood' },
                v06: { name: 'House', health: 400, armor: 'wood' },
                v07: { name: 'Church', health: 400, armor: 'wood' },
                v08: { name: 'Steel Mill', health: 600, armor: 'steel' },
                v09: { name: 'Warehouse', health: 500, armor: 'wood' },
                v10: { name: 'House', health: 400, armor: 'wood' },
                v11: { name: 'Church', health: 400, armor: 'wood' },
                v12: { name: 'Apartment', health: 500, armor: 'concrete' },
                v13: { name: 'House', health: 400, armor: 'wood' },
                v14: { name: 'Office', health: 500, armor: 'concrete' },
                v15: { name: 'Office', health: 500, armor: 'concrete' },
                v16: { name: 'Shop', health: 400, armor: 'wood' },
                v17: { name: 'Shop', health: 400, armor: 'wood' },
                v18: { name: 'Windmill', health: 400, armor: 'wood' },
                v19: { name: 'Oil Pump', health: 750, armor: 'steel' },
                v20: { name: 'Oil Tanks', health: 500, armor: 'steel', explosive: true },
                v21: { name: 'Oil Refinery', health: 800, armor: 'steel' },
                v22: { name: 'Temple', health: 600, armor: 'concrete' },
                v23: { name: 'Church', health: 400, armor: 'wood' },
                v24: { name: 'Farm Silo', health: 400, armor: 'wood' },
                v25: { name: 'Farm', health: 400, armor: 'wood' },
                v26: { name: 'House', health: 400, armor: 'wood' },
                v27: { name: 'House', health: 400, armor: 'wood' },
                v28: { name: 'Water Tower', health: 400, armor: 'steel' },
                v29: { name: 'Apartment', health: 500, armor: 'concrete' },
                v30: { name: 'Church', health: 400, armor: 'wood' },
                v31: { name: 'Church', health: 400, armor: 'wood' },
                v32: { name: 'Hospital', health: 600, armor: 'concrete' },
                v33: { name: 'Hospital', health: 600, armor: 'concrete' },
                v34: { name: 'Stadium', health: 700, armor: 'concrete' },
                v35: { name: 'Stadium', health: 700, armor: 'concrete' },
                v36: { name: 'Stadium', health: 700, armor: 'concrete' },
                v37: { name: 'Stadium', health: 700, armor: 'concrete' },
                
                // Special structures
                arco: { name: 'Arco', health: 800, armor: 'steel' },
                bio: { name: 'Biolab', health: 600, armor: 'concrete' },
                hosp: { name: 'Hospital', health: 600, armor: 'concrete' },
                miss: { name: 'Tech Center', health: 700, armor: 'concrete' }
            },
            units: {
                c1: { name: 'Civilian', health: 25, speed: 4 },
                c2: { name: 'Civilian', health: 25, speed: 4 },
                c3: { name: 'Civilian', health: 25, speed: 4 },
                c4: { name: 'Civilian', health: 25, speed: 4 },
                c5: { name: 'Civilian', health: 25, speed: 4 },
                c6: { name: 'Civilian', health: 25, speed: 4 },
                c7: { name: 'Civilian', health: 25, speed: 4 },
                c8: { name: 'Civilian', health: 25, speed: 4 },
                c9: { name: 'Civilian', health: 25, speed: 4 },
                c10: { name: 'Civilian', health: 25, speed: 4 },
                delphi: { name: 'Agent Delphi', health: 50, speed: 4 },
                chan: { name: 'Dr. Chan', health: 50, speed: 4 },
                moebius: { name: 'Dr. Moebius', health: 50, speed: 4 }
            },
            vehicles: {
                vice: { name: 'Visceriod', health: 300, speed: 6 },
                truck: { name: 'Truck', health: 100, speed: 10 },
                jeep: { name: 'Jeep', health: 150, speed: 20 },
                harvester: { name: 'Harvester', health: 600, speed: 6 }
            }
        };
        
        const configPath = path.join(this.outputPath, 'sprites/civilian/civilian-config.json');
        fs.writeFileSync(configPath, JSON.stringify(civilianConfig, null, 2));
        console.log(`📝 Civilian configuration saved to ${configPath}`);
        
        return civilianConfig;
    }
    
    async run() {
        console.log('🚀 C&C TILE AND CIVILIAN EXTRACTOR');
        console.log('='.repeat(50));
        
        try {
            // Extract tiles
            const tiles = await this.extractTiles();
            console.log(`\n📊 Total tile patterns identified: ${tiles.length}`);
            
            // Extract civilians
            const civilians = await this.extractCivilians();
            console.log(`\n📊 Total civilian assets identified: ${civilians.length}`);
            
            // Generate configurations
            this.generateTileConfig();
            this.generateCivilianConfig();
            
            // Summary
            console.log('\n' + '='.repeat(50));
            console.log('✅ EXTRACTION SUMMARY:');
            console.log(`  🗺️ Tile patterns: ${tiles.length}`);
            console.log(`  🏘️ Civilian assets: ${civilians.length}`);
            console.log(`  📁 Tile directory: public/assets/tiles/`);
            console.log(`  📁 Civilian directory: public/assets/sprites/civilian/`);
            
            // Next steps
            console.log('\n📝 NEXT STEPS:');
            console.log('  1. Implement proper MIX file format parser');
            console.log('  2. Extract actual sprite data from MIX files');
            console.log('  3. Convert SHP format sprites to PNG');
            console.log('  4. Generate tile atlases for efficient rendering');
            console.log('  5. Integrate with map rendering system');
            
        } catch (error) {
            console.error('❌ Extraction failed:', error.message);
            process.exit(1);
        }
    }
}

// Run extractor
const extractor = new TileAndCivilianExtractor();
extractor.run().catch(console.error);