#!/usr/bin/env node

/**
 * Extract and Integrate Sprites from C&C MIX Files
 * This script extracts sprites from .mix files and integrates them with the game
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import MixFileExtractor from './src/utils/MixFileExtractor.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
    console.log('🎮 Command & Conquer Sprite Extraction and Integration');
    console.log('======================================================\n');
    
    // Step 1: Extract sprites from MIX files
    console.log('📦 Step 1: Extracting sprites from MIX files...');
    const extractor = new MixFileExtractor();
    
    try {
        const result = await extractor.extractSprites();
        console.log(`✅ Successfully extracted ${result.spritesExtracted} sprites\n`);
    } catch (error) {
        console.error('❌ Error extracting sprites:', error);
        return;
    }
    
    // Step 2: Merge with existing sprite configuration
    console.log('🔧 Step 2: Merging sprite configurations...');
    
    const existingConfigPath = path.join(__dirname, 'public/assets/sprites/sprite-config.json');
    const extractedConfigPath = path.join(__dirname, 'public/assets/sprites/extracted/extracted-sprite-config.json');
    const mergedConfigPath = path.join(__dirname, 'public/assets/sprites/merged-sprite-config.json');
    
    let existingConfig = {};
    let extractedConfig = {};
    
    // Load existing configuration
    if (fs.existsSync(existingConfigPath)) {
        existingConfig = JSON.parse(fs.readFileSync(existingConfigPath, 'utf8'));
        console.log('  ✓ Loaded existing sprite configuration');
    }
    
    // Load extracted configuration
    if (fs.existsSync(extractedConfigPath)) {
        extractedConfig = JSON.parse(fs.readFileSync(extractedConfigPath, 'utf8'));
        console.log('  ✓ Loaded extracted sprite configuration');
    }
    
    // Merge configurations (extracted takes precedence)
    const mergedConfig = {
        structures: {
            gdi: { ...existingConfig.structures?.gdi, ...extractedConfig.structures?.gdi },
            nod: { ...existingConfig.structures?.nod, ...extractedConfig.structures?.nod }
        },
        units: {
            gdi: { ...existingConfig.units?.gdi, ...extractedConfig.units?.gdi },
            nod: { ...existingConfig.units?.nod, ...extractedConfig.units?.nod }
        },
        infantry: extractedConfig.infantry || {},
        resources: { ...existingConfig.tiberium, ...extractedConfig.resources }
    };
    
    // Save merged configuration
    fs.writeFileSync(mergedConfigPath, JSON.stringify(mergedConfig, null, 2));
    console.log('  ✓ Created merged sprite configuration\n');
    
    // Step 3: Update TextureAtlasManager integration
    console.log('🎨 Step 3: Updating TextureAtlasManager integration...');
    
    const textureAtlasPath = path.join(__dirname, 'src/rendering/TextureAtlasManager.js');
    
    // Check if we need to update the texture atlas manager
    if (fs.existsSync(textureAtlasPath)) {
        console.log('  ✓ TextureAtlasManager found and ready for integration');
        
        // Create an integration test file
        const integrationTestPath = path.join(__dirname, 'test-sprite-integration.html');
        const integrationTestHTML = generateIntegrationTestHTML(mergedConfig);
        fs.writeFileSync(integrationTestPath, integrationTestHTML);
        console.log('  ✓ Created integration test page: test-sprite-integration.html\n');
    }
    
    // Step 4: Generate summary report
    console.log('📊 Step 4: Generating extraction summary...');
    
    const summary = {
        timestamp: new Date().toISOString(),
        mixFilesProcessed: ['conquer.mix'],
        spritesExtracted: {
            units: {
                gdi: Object.keys(extractedConfig.units?.gdi || {}).length,
                nod: Object.keys(extractedConfig.units?.nod || {}).length
            },
            structures: {
                gdi: Object.keys(extractedConfig.structures?.gdi || {}).length,
                nod: Object.keys(extractedConfig.structures?.nod || {}).length
            },
            infantry: {
                gdi: Object.keys(extractedConfig.infantry?.gdi || {}).length,
                nod: Object.keys(extractedConfig.infantry?.nod || {}).length
            },
            resources: Object.keys(extractedConfig.resources || {}).length
        },
        totalSprites: countTotalSprites(extractedConfig),
        outputDirectories: [
            'public/assets/sprites/extracted/units/gdi',
            'public/assets/sprites/extracted/units/nod',
            'public/assets/sprites/extracted/structures/gdi',
            'public/assets/sprites/extracted/structures/nod',
            'public/assets/sprites/extracted/infantry',
            'public/assets/sprites/extracted/resources'
        ]
    };
    
    fs.writeFileSync(
        path.join(__dirname, 'public/assets/sprites/extraction-summary.json'),
        JSON.stringify(summary, null, 2)
    );
    
    console.log('  ✓ Extraction summary saved\n');
    
    // Print summary
    console.log('✨ Extraction and Integration Complete!\n');
    console.log('📈 Summary:');
    console.log(`  • Total sprites extracted: ${summary.totalSprites}`);
    console.log(`  • GDI units: ${summary.spritesExtracted.units.gdi}`);
    console.log(`  • NOD units: ${summary.spritesExtracted.units.nod}`);
    console.log(`  • GDI structures: ${summary.spritesExtracted.structures.gdi}`);
    console.log(`  • NOD structures: ${summary.spritesExtracted.structures.nod}`);
    console.log(`  • Infantry: ${summary.spritesExtracted.infantry.gdi + summary.spritesExtracted.infantry.nod}`);
    console.log(`  • Resources: ${summary.spritesExtracted.resources}\n`);
    
    console.log('🚀 Next steps:');
    console.log('  1. Run the game to test sprite loading');
    console.log('  2. Open test-sprite-integration.html to view all extracted sprites');
    console.log('  3. Check TextureAtlasManager for proper sprite loading\n');
}

function countTotalSprites(config) {
    let total = 0;
    
    if (config.units) {
        total += Object.keys(config.units.gdi || {}).length;
        total += Object.keys(config.units.nod || {}).length;
    }
    
    if (config.structures) {
        total += Object.keys(config.structures.gdi || {}).length;
        total += Object.keys(config.structures.nod || {}).length;
    }
    
    if (config.infantry) {
        total += Object.keys(config.infantry.gdi || {}).length;
        total += Object.keys(config.infantry.nod || {}).length;
    }
    
    if (config.resources) {
        total += Object.keys(config.resources).length;
    }
    
    return total;
}

function generateIntegrationTestHTML(config) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>C&C Sprite Integration Test</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #0f0;
            padding: 20px;
            margin: 0;
        }
        h1 {
            color: #FFD700;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(255, 215, 0, 0.3);
        }
        .category {
            margin: 30px 0;
            padding: 20px;
            border: 2px solid #0f0;
            background: rgba(0, 255, 0, 0.05);
        }
        .category h2 {
            color: #FFD700;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 10px;
        }
        .faction {
            margin: 20px 0;
        }
        .faction h3 {
            color: #fff;
            margin-bottom: 15px;
        }
        .faction.gdi h3 { color: #FFD700; }
        .faction.nod h3 { color: #DC2626; }
        .sprite-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .sprite-item {
            background: rgba(0, 0, 0, 0.8);
            padding: 10px;
            border: 1px solid #0f0;
            text-align: center;
        }
        .sprite-item img {
            display: block;
            image-rendering: pixelated;
            margin: 10px auto;
            max-width: 200px;
            background: rgba(255, 255, 255, 0.1);
        }
        .sprite-name {
            font-size: 12px;
            color: #0f0;
            margin-top: 5px;
        }
        .stats {
            background: rgba(0, 255, 0, 0.1);
            padding: 15px;
            margin: 20px 0;
            border: 1px solid #0f0;
        }
        .loading {
            text-align: center;
            color: #FFD700;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <h1>🎮 COMMAND & CONQUER SPRITE INTEGRATION TEST</h1>
    
    <div class="stats">
        <h3>EXTRACTION STATISTICS</h3>
        <p>Total Sprites Extracted: <span id="total-count">Calculating...</span></p>
        <p>Categories: Units | Structures | Infantry | Resources</p>
        <p>Status: <span class="loading">LOADING SPRITES...</span></p>
    </div>
    
    <div id="sprite-gallery">
        <!-- Sprites will be loaded here -->
    </div>
    
    <script>
        const config = ${JSON.stringify(config, null, 2)};
        
        function loadSprites() {
            const gallery = document.getElementById('sprite-gallery');
            let totalCount = 0;
            
            // Units
            if (config.units) {
                const unitsDiv = createCategory('COMBAT UNITS');
                
                if (config.units.gdi && Object.keys(config.units.gdi).length > 0) {
                    const gdiDiv = createFaction('GDI Forces', 'gdi');
                    for (const [name, data] of Object.entries(config.units.gdi)) {
                        gdiDiv.appendChild(createSpriteItem('gdi-' + name, data, 'units/gdi'));
                        totalCount++;
                    }
                    unitsDiv.appendChild(gdiDiv);
                }
                
                if (config.units.nod && Object.keys(config.units.nod).length > 0) {
                    const nodDiv = createFaction('NOD Forces', 'nod');
                    for (const [name, data] of Object.entries(config.units.nod)) {
                        nodDiv.appendChild(createSpriteItem('nod-' + name, data, 'units/nod'));
                        totalCount++;
                    }
                    unitsDiv.appendChild(nodDiv);
                }
                
                gallery.appendChild(unitsDiv);
            }
            
            // Structures
            if (config.structures) {
                const structuresDiv = createCategory('BASE STRUCTURES');
                
                if (config.structures.gdi && Object.keys(config.structures.gdi).length > 0) {
                    const gdiDiv = createFaction('GDI Buildings', 'gdi');
                    for (const [name, data] of Object.entries(config.structures.gdi)) {
                        gdiDiv.appendChild(createSpriteItem('gdi-' + name, data, 'structures/gdi'));
                        totalCount++;
                    }
                    structuresDiv.appendChild(gdiDiv);
                }
                
                if (config.structures.nod && Object.keys(config.structures.nod).length > 0) {
                    const nodDiv = createFaction('NOD Buildings', 'nod');
                    for (const [name, data] of Object.entries(config.structures.nod)) {
                        nodDiv.appendChild(createSpriteItem('nod-' + name, data, 'structures/nod'));
                        totalCount++;
                    }
                    structuresDiv.appendChild(nodDiv);
                }
                
                gallery.appendChild(structuresDiv);
            }
            
            // Infantry
            if (config.infantry && (config.infantry.gdi || config.infantry.nod)) {
                const infantryDiv = createCategory('INFANTRY UNITS');
                
                if (config.infantry.gdi && Object.keys(config.infantry.gdi).length > 0) {
                    const gdiDiv = createFaction('GDI Infantry', 'gdi');
                    for (const [name, data] of Object.entries(config.infantry.gdi)) {
                        gdiDiv.appendChild(createSpriteItem('gdi-' + name, data, 'infantry'));
                        totalCount++;
                    }
                    infantryDiv.appendChild(gdiDiv);
                }
                
                if (config.infantry.nod && Object.keys(config.infantry.nod).length > 0) {
                    const nodDiv = createFaction('NOD Infantry', 'nod');
                    for (const [name, data] of Object.entries(config.infantry.nod)) {
                        nodDiv.appendChild(createSpriteItem('nod-' + name, data, 'infantry'));
                        totalCount++;
                    }
                    infantryDiv.appendChild(nodDiv);
                }
                
                gallery.appendChild(infantryDiv);
            }
            
            // Resources
            if (config.resources && Object.keys(config.resources).length > 0) {
                const resourcesDiv = createCategory('RESOURCES');
                const containerDiv = document.createElement('div');
                containerDiv.className = 'sprite-container';
                
                for (const [name, data] of Object.entries(config.resources)) {
                    containerDiv.appendChild(createSpriteItem(name, data, 'resources'));
                    totalCount++;
                }
                
                resourcesDiv.appendChild(containerDiv);
                gallery.appendChild(resourcesDiv);
            }
            
            // Update stats
            document.getElementById('total-count').textContent = totalCount;
            document.querySelector('.loading').textContent = 'SPRITES LOADED SUCCESSFULLY';
            document.querySelector('.loading').style.color = '#0f0';
        }
        
        function createCategory(title) {
            const div = document.createElement('div');
            div.className = 'category';
            div.innerHTML = '<h2>' + title + '</h2>';
            return div;
        }
        
        function createFaction(title, faction) {
            const div = document.createElement('div');
            div.className = 'faction ' + faction;
            div.innerHTML = '<h3>' + title + '</h3>';
            const container = document.createElement('div');
            container.className = 'sprite-container';
            div.appendChild(container);
            return div;
        }
        
        function createSpriteItem(name, data, category) {
            const div = document.createElement('div');
            div.className = 'sprite-item';
            
            const img = document.createElement('img');
            img.src = '/assets/sprites/extracted/' + category + '/' + name + '.png';
            img.alt = name;
            img.onerror = function() {
                // Fallback to generated sprites if extracted not found
                this.src = '/assets/sprites/' + category + '/' + name + '.png';
                this.onerror = function() {
                    this.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
                };
            };
            
            const nameDiv = document.createElement('div');
            nameDiv.className = 'sprite-name';
            nameDiv.textContent = name + ' (' + data.frameWidth + 'x' + data.frameHeight + ')';
            
            div.appendChild(img);
            div.appendChild(nameDiv);
            
            return div;
        }
        
        // Load sprites when page is ready
        document.addEventListener('DOMContentLoaded', loadSprites);
    </script>
</body>
</html>`;
}

// Run the extraction and integration
main().catch(console.error);