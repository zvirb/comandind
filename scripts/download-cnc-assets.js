#!/usr/bin/env node

/**
 * Command & Conquer: Tiberian Dawn Asset Downloader
 * Downloads freeware sprites from The Spriters Resource
 * 
 * Since EA released C&C Tiberian Dawn as freeware in 2007,
 * these assets are legally available for use.
 */

import fs from 'fs';
import path from 'path';
import https from 'https';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Asset URLs from The Spriters Resource
const SPRITE_SHEETS = {
    // GDI Structures
    'gdi-structures': [
        { name: 'advanced-comm-center', id: '134605' },
        { name: 'advanced-guard-tower', id: '134606' },
        { name: 'advanced-power-plant', id: '134607' },
        { name: 'barracks', id: '134609' },
        { name: 'comm-center', id: '134610' },
        { name: 'construction-yard', id: '134611' },
        { name: 'guard-tower', id: '134612' },
        { name: 'helipad', id: '134614' },
        { name: 'power-plant', id: '134616' },
        { name: 'refinery', id: '134617' },
        { name: 'repair-facility', id: '134618' },
        { name: 'silo', id: '134620' },
        { name: 'weapons-factory', id: '134623' }
    ],
    
    // NOD Structures
    'nod-structures': [
        { name: 'airfield', id: '134608' },
        { name: 'hand-of-nod', id: '134613' },
        { name: 'obelisk-of-light', id: '134615' },
        { name: 'sam-site', id: '134619' },
        { name: 'temple-of-nod', id: '134621' },
        { name: 'turret', id: '134622' }
    ],
    
    // Units
    'units': [
        { name: 'mammoth-tank', id: '141110' },
        { name: 'medium-tank', id: '141109' },
        { name: 'artillery', id: '141111' },
        { name: 'orca', id: '141576' },
        { name: 'recon-bike', id: '141141' }
    ],
    
    // Neutral
    'neutral': [
        { name: 'oil-pump', id: '141139' }
    ]
};

// Base URL for The Spriters Resource
const BASE_URL = 'https://www.spriters-resource.com/download/';

// Asset directory structure
const ASSET_DIR = path.join(__dirname, '..', 'public', 'assets', 'sprites');

/**
 * Create directory structure for assets
 */
function createDirectoryStructure() {
    const directories = [
        path.join(ASSET_DIR, 'structures', 'gdi'),
        path.join(ASSET_DIR, 'structures', 'nod'),
        path.join(ASSET_DIR, 'units', 'gdi'),
        path.join(ASSET_DIR, 'units', 'nod'),
        path.join(ASSET_DIR, 'units', 'neutral'),
        path.join(ASSET_DIR, 'terrain'),
        path.join(ASSET_DIR, 'effects'),
        path.join(ASSET_DIR, 'ui'),
        path.join(ASSET_DIR, 'resources')
    ];
    
    directories.forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
            console.log(`Created directory: ${dir}`);
        }
    });
}

/**
 * Download a file from URL
 */
function downloadFile(url, filepath) {
    return new Promise((resolve, reject) => {
        console.log(`Downloading: ${path.basename(filepath)}...`);
        
        const file = fs.createWriteStream(filepath);
        
        https.get(url, (response) => {
            if (response.statusCode === 302 || response.statusCode === 301) {
                // Follow redirect
                https.get(response.headers.location, (redirectResponse) => {
                    redirectResponse.pipe(file);
                    file.on('finish', () => {
                        file.close();
                        console.log(`✓ Downloaded: ${path.basename(filepath)}`);
                        resolve();
                    });
                }).on('error', reject);
            } else {
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    console.log(`✓ Downloaded: ${path.basename(filepath)}`);
                    resolve();
                });
            }
        }).on('error', reject);
    });
}

/**
 * Download sprites from The Spriters Resource
 * Note: This would require actually visiting the site and downloading manually
 * as they have anti-bot measures. This is a placeholder for the structure.
 */
async function downloadSprites() {
    console.log('Command & Conquer: Tiberian Dawn Asset Downloader');
    console.log('================================================\n');
    
    console.log('⚠️  IMPORTANT: Due to The Spriters Resource anti-bot measures,');
    console.log('   you\'ll need to manually download the sprites from:');
    console.log('   https://www.spriters-resource.com/pc_computer/commandconquertiberiandawn/\n');
    
    console.log('Creating directory structure...\n');
    createDirectoryStructure();
    
    console.log('\n📁 Directory structure created! Place downloaded sprites as follows:\n');
    
    // GDI Structures
    console.log('GDI Structures → public/assets/sprites/structures/gdi/');
    SPRITE_SHEETS['gdi-structures'].forEach(sprite => {
        console.log(`  - ${sprite.name}.png (Sheet ID: ${sprite.id})`);
    });
    
    console.log('\nNOD Structures → public/assets/sprites/structures/nod/');
    SPRITE_SHEETS['nod-structures'].forEach(sprite => {
        console.log(`  - ${sprite.name}.png (Sheet ID: ${sprite.id})`);
    });
    
    console.log('\nUnits → public/assets/sprites/units/[faction]/');
    SPRITE_SHEETS['units'].forEach(sprite => {
        console.log(`  - ${sprite.name}.png (Sheet ID: ${sprite.id})`);
    });
    
    console.log('\n');
    console.log('Alternative: Use OpenRA for automatic asset extraction:');
    console.log('  1. Download OpenRA from https://www.openra.net/');
    console.log('  2. Run Tiberian Dawn mod');
    console.log('  3. Assets will be in ~/.openra/Content/cnc/');
    
    // Create a sample sprite configuration file
    createSpriteConfig();
}

/**
 * Create sprite configuration file
 */
function createSpriteConfig() {
    const configPath = path.join(ASSET_DIR, 'sprite-config.json');
    
    const config = {
        structures: {
            gdi: {
                'construction-yard': {
                    frameWidth: 48,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 },
                        active: { frames: [0, 1, 2, 3], speed: 0.1 },
                        damaged: { frames: [4], speed: 0 }
                    }
                },
                'power-plant': {
                    frameWidth: 48,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 },
                        active: { frames: [0, 1, 2], speed: 0.15 }
                    }
                },
                'barracks': {
                    frameWidth: 48,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 }
                    }
                },
                'refinery': {
                    frameWidth: 72,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 },
                        active: { frames: [0, 1, 2, 3], speed: 0.1 }
                    }
                }
            },
            nod: {
                'hand-of-nod': {
                    frameWidth: 48,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 }
                    }
                },
                'obelisk-of-light': {
                    frameWidth: 24,
                    frameHeight: 48,
                    animations: {
                        idle: { frames: [0], speed: 0 },
                        charging: { frames: [0, 1, 2], speed: 0.3 },
                        fire: { frames: [3, 4, 5], speed: 0.5 }
                    }
                }
            }
        },
        units: {
            gdi: {
                'medium-tank': {
                    frameWidth: 24,
                    frameHeight: 24,
                    directions: 32,
                    animations: {
                        move: { frames: 'directional', speed: 0 },
                        turret: { frames: 'directional', speed: 0 }
                    }
                },
                'mammoth-tank': {
                    frameWidth: 32,
                    frameHeight: 32,
                    directions: 32,
                    animations: {
                        move: { frames: 'directional', speed: 0 },
                        turret: { frames: 'directional', speed: 0 }
                    }
                }
            },
            nod: {
                'recon-bike': {
                    frameWidth: 24,
                    frameHeight: 24,
                    directions: 32,
                    animations: {
                        move: { frames: 'directional', speed: 0 }
                    }
                }
            }
        },
        tiberium: {
            green: {
                frameWidth: 24,
                frameHeight: 24,
                animations: {
                    idle: { frames: [0, 1, 2, 3], speed: 0.05 }
                }
            },
            blue: {
                frameWidth: 24,
                frameHeight: 24,
                animations: {
                    idle: { frames: [0, 1, 2, 3], speed: 0.05 }
                }
            }
        }
    };
    
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(`\n✓ Created sprite configuration file: ${configPath}`);
}

/**
 * Create a README for asset information
 */
function createAssetReadme() {
    const readmePath = path.join(ASSET_DIR, 'README.md');
    
    const readme = `# Command & Conquer: Tiberian Dawn Assets

## Legal Notice
These assets are from the freeware release of Command & Conquer: Tiberian Dawn,
which EA released in 2007. They are legally available for use.

## Asset Sources

### Official Sources
1. **OpenRA** - Automatically downloads freeware assets
   - Website: https://www.openra.net/
   - Assets location: ~/.openra/Content/cnc/

2. **The Spriters Resource** - Manual sprite downloads
   - URL: https://www.spriters-resource.com/pc_computer/commandconquertiberiandawn/

3. **EA GitHub** - Original source code
   - Repository: https://github.com/electronicarts/CnC_Remastered_Collection

## Directory Structure

\`\`\`
sprites/
├── structures/
│   ├── gdi/       # GDI buildings
│   └── nod/       # NOD buildings
├── units/
│   ├── gdi/       # GDI vehicles and aircraft
│   ├── nod/       # NOD vehicles and aircraft
│   └── neutral/   # Civilian units
├── terrain/       # Map tiles and terrain
├── effects/       # Explosions, projectiles
├── ui/           # Interface elements
└── resources/    # Tiberium and other resources
\`\`\`

## Sprite Sheet Format

Most sprite sheets contain multiple frames for animations:
- Buildings: Usually contain idle, active, and damaged states
- Units: Contain 32 directional frames for rotation
- Effects: Contain animation sequences

## Usage in Game

See \`TextureAtlasManager.js\` for loading and using these sprites in the game.
`;
    
    fs.writeFileSync(readmePath, readme);
    console.log(`✓ Created asset README: ${readmePath}`);
}

// Run the script
downloadSprites();
createAssetReadme();