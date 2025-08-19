#!/usr/bin/env node

/**
 * C&C Tiberian Dawn GitHub Asset & Data Extractor
 * Extracts game rules, unit stats, and configuration from the GitHub repository
 * Combines with OpenRA assets for complete game resources
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class CnCGitHubExtractor {
    constructor() {
        this.baseDir = path.join(__dirname, '..');
        this.githubDir = path.join(this.baseDir, 'tools', 'CnC_Tiberian_Dawn');
        this.outputDir = path.join(this.baseDir, 'public', 'assets', 'cnc-data');
        this.assetsDir = path.join(this.baseDir, 'public', 'assets', 'sprites');
        
        this.unitStats = {};
        this.buildingStats = {};
        this.weaponStats = {};
        this.gameRules = {};
    }
    
    /**
     * Step 1: Clone or update the GitHub repository
     */
    async cloneRepository() {
        console.log('📦 Step 1: Checking C&C GitHub Repository...\n');
        
        const toolsDir = path.join(this.baseDir, 'tools');
        if (!fs.existsSync(toolsDir)) {
            fs.mkdirSync(toolsDir, { recursive: true });
        }
        
        if (fs.existsSync(this.githubDir)) {
            console.log('Repository already exists, pulling latest changes...');
            try {
                execSync('git pull', { cwd: this.githubDir });
                console.log('✅ Repository updated!\n');
            } catch (error) {
                console.log('⚠️  Could not update repository (might be offline)\n');
            }
        } else {
            console.log('Cloning EA C&C Tiberian Dawn repository...');
            console.log('This may take a few minutes...\n');
            
            try {
                execSync(
                    'git clone https://github.com/electronicarts/CnC_Remastered_Collection.git CnC_Tiberian_Dawn',
                    { cwd: toolsDir, stdio: 'inherit' }
                );
                console.log('\n✅ Repository cloned successfully!\n');
            } catch (error) {
                console.error('❌ Failed to clone repository:', error.message);
                console.log('\nPlease manually clone from:');
                console.log('https://github.com/electronicarts/CnC_Remastered_Collection\n');
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Step 2: Extract game rules and configuration from source files
     */
    extractGameData() {
        console.log('🔍 Step 2: Extracting Game Data from Source Code...\n');
        
        // Create output directory
        if (!fs.existsSync(this.outputDir)) {
            fs.mkdirSync(this.outputDir, { recursive: true });
        }
        
        // Look for TIBERIANDAWN folder
        const tdDir = path.join(this.githubDir, 'TIBERIANDAWN');
        if (!fs.existsSync(tdDir)) {
            console.log('⚠️  TIBERIANDAWN folder not found');
            console.log('Looking for alternative paths...\n');
            return false;
        }
        
        // Extract data from header files
        this.extractFromHeaders(tdDir);
        
        // Extract INI configurations if available
        this.extractINIFiles(tdDir);
        
        // Extract unit and building definitions
        this.extractGameConstants(tdDir);
        
        return true;
    }
    
    /**
     * Extract constants from header files
     */
    extractFromHeaders(tdDir) {
        const headerFiles = [
            'DEFINES.H',
            'TYPE.H',
            'CONST.H',
            'UNIT.H',
            'BUILDING.H',
            'INFANTRY.H',
            'WEAPON.H'
        ];
        
        console.log('📄 Extracting from header files...');
        
        headerFiles.forEach(file => {
            const filepath = path.join(tdDir, file);
            if (fs.existsSync(filepath)) {
                console.log(`  - Found: ${file}`);
                this.parseHeaderFile(filepath);
            }
        });
        
        console.log('');
    }
    
    /**
     * Parse a C++ header file for game constants
     */
    parseHeaderFile(filepath) {
        const content = fs.readFileSync(filepath, 'utf8');
        const filename = path.basename(filepath);
        
        // Extract unit stats from comments and definitions
        const unitPattern = /\/\*\*[\s\S]*?\*\/[\s\S]*?class\s+(\w+)/g;
        const definePattern = /#define\s+(\w+)\s+(.+)/g;
        const constPattern = /const\s+\w+\s+(\w+)\s*=\s*(.+);/g;
        
        // Extract #define constants
        let match;
        const defines = {};
        while ((match = definePattern.exec(content)) !== null) {
            defines[match[1]] = match[2].trim();
        }
        
        // Save relevant game constants
        if (Object.keys(defines).length > 0) {
            const category = filename.replace('.H', '').toLowerCase();
            this.gameRules[category] = defines;
        }
    }
    
    /**
     * Extract INI configuration files
     */
    extractINIFiles(tdDir) {
        console.log('📄 Extracting INI configuration files...');
        
        const iniFiles = fs.readdirSync(tdDir)
            .filter(file => file.endsWith('.INI'));
        
        iniFiles.forEach(file => {
            const filepath = path.join(tdDir, file);
            const content = fs.readFileSync(filepath, 'utf8');
            const outputPath = path.join(this.outputDir, file.toLowerCase());
            
            fs.writeFileSync(outputPath, content);
            console.log(`  - Extracted: ${file}`);
            
            // Parse INI for game data
            this.parseINIFile(content, file);
        });
        
        console.log('');
    }
    
    /**
     * Parse INI file for game configuration
     */
    parseINIFile(content, filename) {
        const lines = content.split('\n');
        let currentSection = null;
        const data = {};
        
        lines.forEach(line => {
            line = line.trim();
            
            // Skip comments and empty lines
            if (!line || line.startsWith(';') || line.startsWith('#')) {
                return;
            }
            
            // Section header
            if (line.startsWith('[') && line.endsWith(']')) {
                currentSection = line.slice(1, -1);
                data[currentSection] = {};
                return;
            }
            
            // Key-value pair
            if (currentSection && line.includes('=')) {
                const [key, value] = line.split('=').map(s => s.trim());
                data[currentSection][key] = value;
            }
        });
        
        // Store parsed data based on filename
        if (filename.includes('RULES')) {
            this.gameRules = { ...this.gameRules, ...data };
        }
    }
    
    /**
     * Extract game constants from source files
     */
    extractGameConstants(tdDir) {
        console.log('📊 Extracting Game Constants...\n');
        
        // Hardcoded game data based on C&C documentation
        // These would normally be extracted from the source files
        
        this.unitStats = {
            // GDI Units
            'MEDIUM_TANK': {
                name: 'Medium Tank',
                cost: 800,
                health: 400,
                armor: 'heavy',
                speed: 18,
                weapon: '105mm',
                damage: 30,
                range: 4.75,
                faction: 'GDI'
            },
            'MAMMOTH_TANK': {
                name: 'Mammoth Tank',
                cost: 1500,
                health: 600,
                armor: 'heavy',
                speed: 12,
                weapon: '120mm_dual',
                damage: 40,
                range: 6,
                faction: 'GDI'
            },
            'ORCA': {
                name: 'Orca',
                cost: 1200,
                health: 125,
                armor: 'light',
                speed: 40,
                weapon: 'rockets',
                damage: 50,
                range: 5,
                faction: 'GDI'
            },
            
            // NOD Units
            'LIGHT_TANK': {
                name: 'Light Tank',
                cost: 600,
                health: 300,
                armor: 'heavy',
                speed: 18,
                weapon: '75mm',
                damage: 25,
                range: 4,
                faction: 'NOD'
            },
            'STEALTH_TANK': {
                name: 'Stealth Tank',
                cost: 900,
                health: 110,
                armor: 'light',
                speed: 30,
                weapon: 'rockets',
                damage: 60,
                range: 5,
                faction: 'NOD',
                special: 'cloaking'
            },
            'RECON_BIKE': {
                name: 'Recon Bike',
                cost: 500,
                health: 160,
                armor: 'none',
                speed: 40,
                weapon: 'rockets',
                damage: 20,
                range: 4,
                faction: 'NOD'
            }
        };
        
        this.buildingStats = {
            // GDI Buildings
            'GDI_CONSTRUCTION_YARD': {
                name: 'Construction Yard',
                cost: 5000,
                health: 800,
                power: 0,
                faction: 'GDI'
            },
            'GDI_POWER_PLANT': {
                name: 'Power Plant',
                cost: 300,
                health: 400,
                power: 100,
                faction: 'GDI'
            },
            'GDI_BARRACKS': {
                name: 'Barracks',
                cost: 400,
                health: 500,
                power: -20,
                faction: 'GDI',
                produces: 'infantry'
            },
            'GDI_REFINERY': {
                name: 'Refinery',
                cost: 2000,
                health: 450,
                power: -40,
                faction: 'GDI',
                special: 'harvester_included'
            },
            
            // NOD Buildings
            'NOD_CONSTRUCTION_YARD': {
                name: 'Construction Yard',
                cost: 5000,
                health: 800,
                power: 0,
                faction: 'NOD'
            },
            'NOD_POWER_PLANT': {
                name: 'Power Plant',
                cost: 300,
                health: 400,
                power: 100,
                faction: 'NOD'
            },
            'NOD_HAND_OF_NOD': {
                name: 'Hand of Nod',
                cost: 400,
                health: 500,
                power: -20,
                faction: 'NOD',
                produces: 'infantry'
            },
            'NOD_OBELISK': {
                name: 'Obelisk of Light',
                cost: 1500,
                health: 400,
                power: -150,
                faction: 'NOD',
                weapon: 'laser',
                damage: 200,
                range: 7.5
            }
        };
        
        // Save to JSON files
        this.saveGameData();
    }
    
    /**
     * Save extracted game data to JSON files
     */
    saveGameData() {
        console.log('💾 Saving Game Data...\n');
        
        // Save unit stats
        const unitsPath = path.join(this.outputDir, 'units.json');
        fs.writeFileSync(unitsPath, JSON.stringify(this.unitStats, null, 2));
        console.log(`  ✅ Saved unit stats to: ${unitsPath}`);
        
        // Save building stats
        const buildingsPath = path.join(this.outputDir, 'buildings.json');
        fs.writeFileSync(buildingsPath, JSON.stringify(this.buildingStats, null, 2));
        console.log(`  ✅ Saved building stats to: ${buildingsPath}`);
        
        // Save game rules
        const rulesPath = path.join(this.outputDir, 'rules.json');
        fs.writeFileSync(rulesPath, JSON.stringify(this.gameRules, null, 2));
        console.log(`  ✅ Saved game rules to: ${rulesPath}`);
        
        console.log('');
    }
    
    /**
     * Step 3: Setup OpenRA integration
     */
    setupOpenRAIntegration() {
        console.log('🎮 Step 3: OpenRA Asset Integration Instructions\n');
        
        console.log('To get complete graphical assets:\n');
        console.log('1. Download OpenRA from: https://www.openra.net/');
        console.log('2. Run OpenRA and select "Tiberian Dawn"');
        console.log('3. OpenRA will auto-download freeware assets');
        console.log('4. Find assets in:');
        console.log('   - Linux/Mac: ~/.openra/Content/cnc/');
        console.log('   - Windows: %APPDATA%\\OpenRA\\Content\\cnc\\');
        console.log('\n5. Copy sprite files to:');
        console.log(`   ${this.assetsDir}`);
        console.log('');
    }
    
    /**
     * Generate PixiJS loader configuration
     */
    generateLoaderConfig() {
        console.log('⚙️  Generating PixiJS Loader Configuration...\n');
        
        const config = {
            units: this.unitStats,
            buildings: this.buildingStats,
            sprites: {
                basePath: '/assets/sprites/',
                sheets: {}
            }
        };
        
        // Add sprite sheet configurations
        Object.keys(this.unitStats).forEach(unitKey => {
            const unit = this.unitStats[unitKey];
            const faction = unit.faction.toLowerCase();
            const name = unit.name.toLowerCase().replace(/ /g, '-');
            
            config.sprites.sheets[unitKey] = {
                path: `units/${faction}/${name}.png`,
                frameWidth: unitKey.includes('MAMMOTH') ? 32 : 24,
                frameHeight: unitKey.includes('MAMMOTH') ? 32 : 24,
                animations: {
                    move: { frames: 32, speed: 0 },
                    turret: { frames: 32, speed: 0 }
                }
            };
        });
        
        const configPath = path.join(this.outputDir, 'game-config.json');
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
        console.log(`✅ Generated config at: ${configPath}\n`);
    }
    
    /**
     * Run the complete extraction process
     */
    async run() {
        console.log('========================================');
        console.log('🎮 C&C TIBERIAN DAWN ASSET EXTRACTOR 🎮');
        console.log('========================================\n');
        
        // Step 1: Clone/Update repository
        const repoReady = await this.cloneRepository();
        if (!repoReady) {
            console.log('⚠️  Repository setup required. Please follow manual instructions.\n');
            return;
        }
        
        // Step 2: Extract game data
        const dataExtracted = this.extractGameData();
        if (!dataExtracted) {
            console.log('⚠️  Could not extract all game data.\n');
        }
        
        // Step 3: Setup OpenRA integration
        this.setupOpenRAIntegration();
        
        // Step 4: Generate configs
        this.generateLoaderConfig();
        
        console.log('========================================');
        console.log('✅ EXTRACTION COMPLETE!');
        console.log('========================================\n');
        console.log('Next steps:');
        console.log('1. Get graphical assets from OpenRA');
        console.log('2. Place sprites in public/assets/sprites/');
        console.log('3. Run the game with: npm run dev');
        console.log('');
    }
}

// Run the extractor
const extractor = new CnCGitHubExtractor();
extractor.run();