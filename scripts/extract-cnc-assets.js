#!/usr/bin/env node

/**
 * C&C MIX File Asset Extractor
 * Extracts sprites and data from OpenRA's downloaded C&C MIX files
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class MIXExtractor {
    constructor() {
        this.baseDir = path.join(__dirname, '..');
        this.openraContentDir = '/home/marku/snap/openra/1415/.config/openra/Content/cnc';
        this.outputDir = path.join(this.baseDir, 'public', 'assets', 'cnc-extracted');
        
        // Known MIX files and their contents
        this.mixFiles = {
            'conquer.mix': 'Units, buildings, sprites',
            'general.mix': 'UI elements, cursors, fonts',
            'desert.mix': 'Desert terrain tiles',
            'temperat.mix': 'Temperate terrain tiles', 
            'winter.mix': 'Winter terrain tiles',
            'sounds.mix': 'Sound effects',
            'speech.mix': 'Voice samples',
            'transit.mix': 'Transition screens'
        };
    }
    
    async run() {
        console.log('========================================');
        console.log('🎮 C&C MIX FILE ASSET EXTRACTOR 🎮');
        console.log('========================================\n');
        
        // Check if OpenRA content exists
        if (!fs.existsSync(this.openraContentDir)) {
            console.log('❌ OpenRA content directory not found!');
            console.log(`Expected: ${this.openraContentDir}`);
            return;
        }
        
        // List available MIX files
        console.log('📦 Found MIX Files:');
        const files = fs.readdirSync(this.openraContentDir);
        files.forEach(file => {
            if (file.endsWith('.mix')) {
                const stats = fs.statSync(path.join(this.openraContentDir, file));
                const sizeMB = (stats.size / 1048576).toFixed(1);
                const description = this.mixFiles[file] || 'Unknown content';
                console.log(`  ✅ ${file} (${sizeMB} MB) - ${description}`);
            }
        });
        console.log('');
        
        // Create output directory
        if (!fs.existsSync(this.outputDir)) {
            fs.mkdirSync(this.outputDir, { recursive: true });
        }
        
        // Copy MIX files to our project for analysis
        console.log('📋 Copying MIX files for analysis...');
        files.forEach(file => {
            if (file.endsWith('.mix')) {
                const src = path.join(this.openraContentDir, file);
                const dest = path.join(this.outputDir, file);
                fs.copyFileSync(src, dest);
                console.log(`  ✅ Copied: ${file}`);
            }
        });
        console.log('');
        
        // Since MIX files are complex binary formats, we'll document them
        // and provide instructions for using OpenRA's built-in extraction
        this.generateExtractionGuide();
        
        // Create placeholder sprites based on known C&C content
        this.createPlaceholderSprites();
        
        console.log('========================================');
        console.log('✅ MIX FILES READY FOR EXTRACTION!');
        console.log('========================================\n');
        
        console.log('Next steps:');
        console.log('1. MIX files copied to project');
        console.log('2. Use OpenRA utilities to extract sprites');
        console.log('3. Placeholder system ready for testing');
        console.log('');
    }
    
    generateExtractionGuide() {
        console.log('📚 Generating extraction guide...');
        
        const guide = `# C&C Asset Extraction Guide

## MIX Files Overview

The following MIX archives contain all C&C assets:

${Object.entries(this.mixFiles).map(([file, desc]) => `- **${file}**: ${desc}`).join('\n')}

## Extraction Methods

### Method 1: OpenRA Utilities (Recommended)
OpenRA includes built-in utilities to extract MIX files:

\`\`\`bash
# Use OpenRA's utility (if available)
openra --extract-content conquer.mix output_directory/
\`\`\`

### Method 2: XCC Utilities
Use the classic XCC Mixer tool:

1. Download XCC Mixer
2. Open MIX files
3. Extract SHP sprites and convert to PNG

### Method 3: Community Tools
- **OpenRA Extract**: Built-in extraction tools
- **MIX Browser**: Web-based MIX file browser
- **C&C Tools**: Community extraction utilities

## File Formats

- **SHP**: Sprite files (need palette)
- **PAL**: Palette files for colors
- **WSA**: Animation files
- **AUD**: Audio files
- **INI**: Configuration files

## Key Assets Locations

### Units & Buildings (conquer.mix)
- Tank sprites: TANK.SHP, HTANK.SHP
- Building sprites: PROC.SHP, POWR.SHP
- Infantry: E1.SHP, E2.SHP

### Terrain (desert.mix, temperat.mix, winter.mix)
- Terrain templates: *.TEM files
- Tile graphics: *.DES, *.TMP files

### UI Elements (general.mix)
- Mouse cursors: MOUSE.SHP
- Interface: SIDEBAR.SHP
- Icons: ICON.SHP

## For Web Game Development

Convert extracted assets to web-friendly formats:
- SHP → PNG (with transparency)
- AUD → OGG/MP3
- Create texture atlases for performance
`;
        
        const guidePath = path.join(this.outputDir, 'EXTRACTION_GUIDE.md');
        fs.writeFileSync(guidePath, guide);
        console.log(`  ✅ Guide saved to: ${guidePath}`);
    }
    
    createPlaceholderSprites() {
        console.log('🎨 Creating placeholder sprites for testing...');
        
        // Create simple colored rectangles as placeholders
        const placeholders = {
            'structures/gdi/construction-yard.png': { width: 48, height: 48, color: '#0066ff' },
            'structures/gdi/power-plant.png': { width: 48, height: 48, color: '#00aa00' },
            'structures/gdi/barracks.png': { width: 48, height: 48, color: '#ffaa00' },
            'structures/nod/hand-of-nod.png': { width: 48, height: 48, color: '#ff0000' },
            'structures/nod/obelisk-of-light.png': { width: 24, height: 48, color: '#ff00ff' },
            'units/gdi/medium-tank.png': { width: 24, height: 24, color: '#0088ff' },
            'units/gdi/mammoth-tank.png': { width: 32, height: 32, color: '#0044aa' },
            'units/nod/recon-bike.png': { width: 24, height: 24, color: '#ff4400' },
            'resources/tiberium-green.png': { width: 24, height: 24, color: '#00ff00' },
            'terrain/sand-01.png': { width: 24, height: 24, color: '#ffdd88' }
        };
        
        // Create an HTML file that generates placeholder images
        const placeholderHTML = `<!DOCTYPE html>
<html>
<head>
    <title>C&C Placeholder Generator</title>
</head>
<body>
    <h1>C&C Placeholder Sprite Generator</h1>
    <p>Run this in a browser to generate placeholder images:</p>
    
    <script>
        const placeholders = ${JSON.stringify(placeholders, null, 8)};
        
        function generateSprite(filename, config) {
            const canvas = document.createElement('canvas');
            canvas.width = config.width;
            canvas.height = config.height;
            const ctx = canvas.getContext('2d');
            
            // Fill with color
            ctx.fillStyle = config.color;
            ctx.fillRect(0, 0, config.width, config.height);
            
            // Add border
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;
            ctx.strokeRect(0, 0, config.width, config.height);
            
            // Add text label
            ctx.fillStyle = '#fff';
            ctx.font = '8px Arial';
            ctx.textAlign = 'center';
            const name = filename.split('/').pop().replace('.png', '');
            ctx.fillText(name.substring(0, 8), config.width/2, config.height/2 + 3);
            
            return canvas.toDataURL('image/png');
        }
        
        // Generate download links
        Object.entries(placeholders).forEach(([filename, config]) => {
            const dataUrl = generateSprite(filename, config);
            const link = document.createElement('a');
            link.download = filename.replace(/\\//g, '_');
            link.href = dataUrl;
            link.textContent = \`Download \${filename}\`;
            link.style.display = 'block';
            link.style.margin = '5px 0';
            document.body.appendChild(link);
        });
    </script>
</body>
</html>`;
        
        const htmlPath = path.join(this.outputDir, 'placeholder-generator.html');
        fs.writeFileSync(htmlPath, placeholderHTML);
        console.log(`  ✅ Placeholder generator: ${htmlPath}`);
        console.log('     Open this file in a browser to download placeholder sprites');
    }
}

// Run the extractor
const extractor = new MIXExtractor();
extractor.run();