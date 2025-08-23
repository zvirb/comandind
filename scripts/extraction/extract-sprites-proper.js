#!/usr/bin/env node

/**
 * Proper C&C Sprite Extraction Script
 * 
 * This script extracts actual sprites from Command & Conquer MIX files
 * using proper tools:
 * 1. ccmixar - for extracting MIX archives
 * 2. OpenRA.Utility - for converting SHP to PNG
 * 
 * Prerequisites:
 * - Install ccmixar: go install github.com/askeladdk/ccmixar@latest
 * - Download OpenRA: https://www.openra.net/download/
 * - Or build OpenRA utilities from source
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const CONFIG = {
    mixPath: path.join(__dirname, '../../public/assets/cnc-extracted'),
    outputPath: path.join(__dirname, '../../public/assets/sprites/real-extracted'),
    tempPath: path.join(__dirname, '../../temp/extraction'),
    game: 'cc1', // cc1 for Tiberian Dawn
    
    // Tool paths (update these based on your system)
    ccmixar: 'ccmixar', // Assumes ccmixar is in PATH
    openraUtility: 'OpenRA.Utility', // Update with actual path to OpenRA.Utility
    
    // Key MIX files to extract
    mixFiles: [
        'conquer.mix',  // Units, buildings, sprites
        'general.mix',  // UI elements, cursors, fonts
        'temperat.mix', // Temperate terrain tiles
    ],
    
    // Key sprites we want (SHP files inside MIX)
    targetSprites: {
        // GDI Units
        'mtnk.shp': 'units/gdi/medium-tank',
        'htnk.shp': 'units/gdi/mammoth-tank',
        'jeep.shp': 'units/gdi/humvee',
        'apc.shp': 'units/gdi/apc',
        'arty.shp': 'units/gdi/artillery',
        'mlrs.shp': 'units/gdi/mlrs',
        'orca.shp': 'units/gdi/orca',
        
        // NOD Units  
        'ltnk.shp': 'units/nod/light-tank',
        'ftnk.shp': 'units/nod/flame-tank',
        'stnk.shp': 'units/nod/stealth-tank',
        'bggy.shp': 'units/nod/buggy',
        'bike.shp': 'units/nod/recon-bike',
        'heli.shp': 'units/nod/apache',
        
        // GDI Buildings
        'fact.shp': 'structures/gdi/construction-yard',
        'pyle.shp': 'structures/gdi/barracks',
        'nuke.shp': 'structures/gdi/power-plant',
        'proc.shp': 'structures/gdi/refinery',
        'weap.shp': 'structures/gdi/war-factory',
        'gtwr.shp': 'structures/gdi/guard-tower',
        'atwr.shp': 'structures/gdi/advanced-tower',
        'hq.shp': 'structures/gdi/comm-center',
        
        // NOD Buildings
        'hand.shp': 'structures/nod/hand-of-nod',
        'tmpl.shp': 'structures/nod/temple-of-nod',
        'obli.shp': 'structures/nod/obelisk',
        'afld.shp': 'structures/nod/airfield',
        'sam.shp': 'structures/nod/sam-site',
        'gun.shp': 'structures/nod/turret',
        
        // Infantry
        'e1.shp': 'infantry/minigunner',
        'e2.shp': 'infantry/grenadier',
        'e3.shp': 'infantry/rocket-soldier',
        'e4.shp': 'infantry/flamethrower',
        'e5.shp': 'infantry/chem-warrior',
        'e6.shp': 'infantry/engineer',
        'rmbo.shp': 'infantry/commando',
        
        // Resources
        'ti1.shp': 'resources/tiberium-1',
        'ti2.shp': 'resources/tiberium-2',
        'ti3.shp': 'resources/tiberium-3',
    }
};

// Utility functions
function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

function runCommand(command, options = {}) {
    console.log(`Running: ${command}`);
    try {
        const result = execSync(command, { encoding: 'utf8', ...options });
        return result;
    } catch (error) {
        console.error(`Command failed: ${command}`);
        console.error(error.message);
        return null;
    }
}

// Check if tools are available
function checkTools() {
    console.log('Checking required tools...');
    
    // Check ccmixar
    const ccmixarCheck = runCommand(`${CONFIG.ccmixar} --help 2>&1`);
    if (!ccmixarCheck || !ccmixarCheck.includes('ccmixar')) {
        console.error(`
ERROR: ccmixar not found!
Please install it:
  go install github.com/askeladdk/ccmixar@latest
Or download from: https://github.com/askeladdk/ccmixar
        `);
        return false;
    }
    console.log('✓ ccmixar found');
    
    // Check OpenRA.Utility (optional but recommended)
    const openraCheck = runCommand(`${CONFIG.openraUtility} --help 2>&1`);
    if (!openraCheck || !openraCheck.includes('OpenRA')) {
        console.warn(`
WARNING: OpenRA.Utility not found!
SHP to PNG conversion will not be available.
Download from: https://www.openra.net/download/
Or set the correct path in CONFIG.openraUtility
        `);
        CONFIG.hasOpenRA = false;
    } else {
        console.log('✓ OpenRA.Utility found');
        CONFIG.hasOpenRA = true;
    }
    
    return true;
}

// Extract MIX files
function extractMixFile(mixFile) {
    const mixPath = path.join(CONFIG.mixPath, mixFile);
    const outputDir = path.join(CONFIG.tempPath, mixFile.replace('.mix', ''));
    
    if (!fs.existsSync(mixPath)) {
        console.warn(`MIX file not found: ${mixPath}`);
        return false;
    }
    
    ensureDir(outputDir);
    
    console.log(`\nExtracting ${mixFile}...`);
    const result = runCommand(
        `${CONFIG.ccmixar} unpack -game ${CONFIG.game} -mix "${mixPath}" -dir "${outputDir}"`
    );
    
    if (result) {
        console.log(`✓ Extracted ${mixFile}`);
        
        // List extracted files
        const files = fs.readdirSync(outputDir);
        console.log(`  Found ${files.length} files`);
        
        // Show SHP files
        const shpFiles = files.filter(f => f.endsWith('.shp'));
        if (shpFiles.length > 0) {
            console.log(`  SHP files: ${shpFiles.slice(0, 10).join(', ')}${shpFiles.length > 10 ? '...' : ''}`);
        }
        
        return true;
    }
    
    return false;
}

// Convert SHP to PNG using OpenRA
function convertShpToPng(shpPath, pngPath) {
    if (!CONFIG.hasOpenRA) {
        console.warn('OpenRA.Utility not available, skipping SHP conversion');
        return false;
    }
    
    ensureDir(path.dirname(pngPath));
    
    // OpenRA command to convert SHP to PNG
    // Note: Requires a palette file, using temperat.pal as default
    const palettePath = path.join(CONFIG.tempPath, 'temperat.pal');
    
    const result = runCommand(
        `${CONFIG.openraUtility} ra --png "${shpPath}" "${palettePath}" --output "${pngPath}"`
    );
    
    return !!result;
}

// Process extracted files
function processExtractedFiles() {
    console.log('\nProcessing extracted files...');
    
    let found = 0;
    let converted = 0;
    
    for (const [shpFile, outputPath] of Object.entries(CONFIG.targetSprites)) {
        // Search for the SHP file in extracted directories
        for (const mixDir of CONFIG.mixFiles.map(m => m.replace('.mix', ''))) {
            const shpPath = path.join(CONFIG.tempPath, mixDir, shpFile);
            
            if (fs.existsSync(shpPath)) {
                found++;
                console.log(`Found: ${shpFile}`);
                
                const pngPath = path.join(CONFIG.outputPath, `${outputPath}.png`);
                
                if (CONFIG.hasOpenRA) {
                    if (convertShpToPng(shpPath, pngPath)) {
                        converted++;
                        console.log(`  ✓ Converted to: ${outputPath}.png`);
                    } else {
                        console.log(`  ✗ Failed to convert`);
                    }
                } else {
                    // Just copy the SHP file for now
                    ensureDir(path.dirname(pngPath));
                    fs.copyFileSync(shpPath, pngPath.replace('.png', '.shp'));
                    console.log(`  → Copied SHP to: ${outputPath}.shp`);
                }
                
                break;
            }
        }
    }
    
    console.log(`\nFound ${found}/${Object.keys(CONFIG.targetSprites).length} target sprites`);
    if (CONFIG.hasOpenRA) {
        console.log(`Converted ${converted} sprites to PNG`);
    }
}

// Alternative: Use Python script for SHP conversion
function createPythonConverter() {
    const pythonScript = `#!/usr/bin/env python3
"""
Simple SHP to PNG converter for C&C sprites
Requires: Pillow (pip install Pillow)
"""

import struct
import sys
from PIL import Image

def read_shp(filename):
    """Read a Westwood SHP file (simplified version)"""
    with open(filename, 'rb') as f:
        # Read header
        num_images = struct.unpack('<H', f.read(2))[0]
        unknown = struct.unpack('<H', f.read(2))[0]
        
        # Read offsets
        offsets = []
        for i in range(num_images + 2):
            offset = struct.unpack('<I', f.read(4))[0]
            offsets.append(offset)
        
        # Read images (simplified - actual format is more complex)
        images = []
        for i in range(num_images):
            f.seek(offsets[i])
            # This would need proper SHP format parsing
            # For now, just note that we'd extract the image data here
            pass
    
    return images

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: shp2png.py input.shp output.png")
        sys.exit(1)
    
    # This is a placeholder - actual SHP parsing is complex
    print(f"Would convert {sys.argv[1]} to {sys.argv[2]}")
`;
    
    const scriptPath = path.join(CONFIG.tempPath, 'shp2png.py');
    ensureDir(CONFIG.tempPath);
    fs.writeFileSync(scriptPath, pythonScript);
    console.log(`Created Python converter script at: ${scriptPath}`);
    console.log('Note: This is a template - actual SHP parsing requires more complex implementation');
}

// Main extraction process
async function main() {
    console.log('=== C&C Sprite Extraction Tool ===\n');
    
    // Check tools
    if (!checkTools()) {
        console.error('\nMissing required tools. Please install them and try again.');
        process.exit(1);
    }
    
    // Create directories
    ensureDir(CONFIG.outputPath);
    ensureDir(CONFIG.tempPath);
    
    // Extract MIX files
    let extractedAny = false;
    for (const mixFile of CONFIG.mixFiles) {
        if (extractMixFile(mixFile)) {
            extractedAny = true;
        }
    }
    
    if (!extractedAny) {
        console.error('\nNo MIX files could be extracted. Check your paths.');
        process.exit(1);
    }
    
    // Process extracted files
    processExtractedFiles();
    
    // Create Python converter as alternative
    if (!CONFIG.hasOpenRA) {
        console.log('\n=== Alternative: Python Converter ===');
        createPythonConverter();
    }
    
    console.log('\n=== Extraction Complete ===');
    console.log(`Output directory: ${CONFIG.outputPath}`);
    console.log(`Temp directory: ${CONFIG.tempPath}`);
    
    if (!CONFIG.hasOpenRA) {
        console.log(`
Next steps:
1. Install OpenRA for proper SHP to PNG conversion
2. Or use XCC Mixer on Windows
3. Or implement a custom SHP parser (complex format)
        `);
    }
}

// Run the extraction
main().catch(console.error);