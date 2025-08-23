#!/usr/bin/env node

/**
 * Simple SHP to Canvas converter for C&C sprites
 * Creates placeholder PNGs that show the sprite structure
 */

const fs = require('fs');
const path = require('path');

// C&C Temperat Palette (simplified RGB values)
const PALETTE = [
    [0, 0, 0],       // 0: Transparent
    [0, 0, 0],       // 1: Black
    [189, 0, 0],     // 2: Red
    [0, 189, 0],     // 3: Green
    [0, 0, 189],     // 4: Blue
    [189, 189, 0],   // 5: Yellow
    [189, 0, 189],   // 6: Magenta
    [0, 189, 189],   // 7: Cyan
    [189, 189, 189], // 8: Light gray
    [126, 126, 126], // 9: Dark gray
    [255, 0, 0],     // 10: Bright red
    [0, 255, 0],     // 11: Bright green
    [0, 0, 255],     // 12: Bright blue
    [255, 255, 0],   // 13: Bright yellow
    [255, 0, 255],   // 14: Bright magenta
    [0, 255, 255],   // 15: Bright cyan
];

// Fill rest with grayscale
for (let i = 16; i < 256; i++) {
    PALETTE[i] = [i, i, i];
}

function readSHPHeader(buffer) {
    // Read number of images (first 2 bytes, little-endian)
    const numImages = buffer.readUInt16LE(0);
    
    // Skip unknown bytes (2-6)
    
    // Read offsets for each image
    const offsets = [];
    for (let i = 0; i < numImages + 2; i++) {
        const offset = buffer.readUInt32LE(6 + i * 4);
        offsets.push(offset);
    }
    
    return { numImages, offsets };
}

function createPlaceholderPNG(shpFile, outputFile, info) {
    // Create a simple HTML canvas representation
    const html = `<!DOCTYPE html>
<html>
<head>
    <title>${path.basename(shpFile)}</title>
    <style>
        body { 
            background: #333; 
            color: white; 
            font-family: monospace; 
            padding: 20px;
        }
        .info {
            background: #444;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #666;
        }
        .frames {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }
        .frame {
            border: 1px solid #666;
            padding: 5px;
            text-align: center;
            background: #222;
        }
        canvas {
            border: 1px solid #888;
            image-rendering: pixelated;
        }
    </style>
</head>
<body>
    <h1>${path.basename(shpFile)}</h1>
    <div class="info">
        <p>Frames: ${info.numImages}</p>
        <p>Type: ${info.type}</p>
        <p>Note: This is a placeholder visualization. Use proper SHP converter for actual sprites.</p>
    </div>
    <div class="frames" id="frames"></div>
    
    <script>
        const numFrames = ${info.numImages};
        const container = document.getElementById('frames');
        
        // Determine sprite type based on frame count
        let frameSize = 32;
        let spriteType = 'unknown';
        
        if (numFrames === 32 || numFrames === 64) {
            spriteType = 'vehicle';
            frameSize = 24;
        } else if (numFrames > 100) {
            spriteType = 'infantry';
            frameSize = 16;
        } else if (numFrames < 10) {
            spriteType = 'building';
            frameSize = 48;
        }
        
        // Create placeholder frames
        for (let i = 0; i < Math.min(numFrames, 8); i++) {
            const div = document.createElement('div');
            div.className = 'frame';
            
            const canvas = document.createElement('canvas');
            canvas.width = frameSize;
            canvas.height = frameSize;
            const ctx = canvas.getContext('2d');
            
            // Draw placeholder sprite
            if (spriteType === 'vehicle') {
                // Draw simple tank shape
                ctx.fillStyle = '#666';
                ctx.fillRect(frameSize/4, frameSize/3, frameSize/2, frameSize/3);
                ctx.fillStyle = '#444';
                ctx.fillRect(frameSize/6, frameSize/3 - 2, frameSize*2/3, 4);
                ctx.fillRect(frameSize/6, frameSize*2/3 - 2, frameSize*2/3, 4);
                // Turret
                ctx.fillStyle = '#888';
                ctx.beginPath();
                ctx.arc(frameSize/2, frameSize/2, frameSize/6, 0, Math.PI * 2);
                ctx.fill();
                // Cannon rotated based on frame
                ctx.strokeStyle = '#999';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(frameSize/2, frameSize/2);
                const angle = (i / numFrames) * Math.PI * 2;
                ctx.lineTo(frameSize/2 + Math.cos(angle) * frameSize/3, 
                          frameSize/2 + Math.sin(angle) * frameSize/3);
                ctx.stroke();
            } else if (spriteType === 'building') {
                // Draw simple building
                ctx.fillStyle = '#555';
                ctx.fillRect(frameSize/4, frameSize/3, frameSize/2, frameSize/2);
                ctx.fillStyle = '#444';
                ctx.beginPath();
                ctx.moveTo(frameSize/4 - 4, frameSize/3);
                ctx.lineTo(frameSize/2, frameSize/4);
                ctx.lineTo(frameSize*3/4 + 4, frameSize/3);
                ctx.closePath();
                ctx.fill();
                // Windows
                ctx.fillStyle = i === 0 ? '#333' : '#ff0';
                ctx.fillRect(frameSize/3, frameSize/2 - 4, 4, 4);
                ctx.fillRect(frameSize*2/3 - 4, frameSize/2 - 4, 4, 4);
            } else {
                // Draw simple infantry
                ctx.fillStyle = '#888';
                // Head
                ctx.beginPath();
                ctx.arc(frameSize/2, frameSize/4, 2, 0, Math.PI * 2);
                ctx.fill();
                // Body
                ctx.fillRect(frameSize/2 - 2, frameSize/3, 4, frameSize/3);
                // Arms
                ctx.fillRect(frameSize/3, frameSize/2 - 2, frameSize/3, 2);
                // Legs
                ctx.fillRect(frameSize/2 - 3, frameSize*2/3, 2, frameSize/4);
                ctx.fillRect(frameSize/2 + 1, frameSize*2/3, 2, frameSize/4);
            }
            
            // Frame number
            ctx.fillStyle = '#0f0';
            ctx.font = '8px monospace';
            ctx.fillText(i.toString(), 2, 10);
            
            div.appendChild(canvas);
            const label = document.createElement('div');
            label.textContent = 'Frame ' + i;
            label.style.fontSize = '10px';
            label.style.color = '#888';
            div.appendChild(label);
            
            container.appendChild(div);
        }
        
        if (numFrames > 8) {
            const more = document.createElement('div');
            more.className = 'frame';
            more.style.padding = '20px';
            more.textContent = '+ ' + (numFrames - 8) + ' more frames';
            container.appendChild(more);
        }
    </script>
</body>
</html>`;
    
    // Write HTML file
    const htmlFile = outputFile.replace('.png', '.html');
    fs.writeFileSync(htmlFile, html);
    console.log(`  ✓ Created visualization: ${path.basename(htmlFile)}`);
    
    return true;
}

function processShpFile(shpFile, outputDir) {
    const basename = path.basename(shpFile, '.shp');
    const outputFile = path.join(outputDir, basename + '.png');
    
    console.log(`Processing: ${basename}.shp`);
    
    try {
        const buffer = fs.readFileSync(shpFile);
        const { numImages, offsets } = readSHPHeader(buffer);
        
        // Determine sprite type
        let type = 'unknown';
        if (numImages === 32 || numImages === 64) {
            type = 'vehicle/turret';
        } else if (numImages > 100) {
            type = 'infantry';
        } else if (numImages < 10) {
            type = 'building';
        } else {
            type = 'animation';
        }
        
        console.log(`  Frames: ${numImages}, Type: ${type}`);
        
        // Create placeholder visualization
        createPlaceholderPNG(shpFile, outputFile, { numImages, type });
        
        return true;
    } catch (error) {
        console.log(`  ✗ Error: ${error.message}`);
        return false;
    }
}

function main() {
    const inputDir = 'public/assets/sprites/cnc-shp-files';
    const outputDir = 'public/assets/sprites/cnc-converted';
    
    console.log('=== SHP to Visualization Converter ===\n');
    
    // Create output directory
    fs.mkdirSync(outputDir, { recursive: true });
    
    // Process all SHP files
    const categories = ['units/gdi', 'units/nod', 'structures/gdi', 'structures/nod', 'infantry'];
    
    let totalProcessed = 0;
    let totalSuccess = 0;
    
    for (const category of categories) {
        const categoryPath = path.join(inputDir, category);
        const outputCategoryPath = path.join(outputDir, category);
        
        if (!fs.existsSync(categoryPath)) continue;
        
        fs.mkdirSync(outputCategoryPath, { recursive: true });
        
        console.log(`\n${category}:`);
        
        const files = fs.readdirSync(categoryPath).filter(f => f.endsWith('.shp'));
        
        for (const file of files) {
            const shpPath = path.join(categoryPath, file);
            totalProcessed++;
            if (processShpFile(shpPath, outputCategoryPath)) {
                totalSuccess++;
            }
        }
    }
    
    console.log(`\n=== Conversion Complete ===`);
    console.log(`Processed: ${totalProcessed} files`);
    console.log(`Successful: ${totalSuccess} files`);
    console.log(`Output: ${outputDir}`);
    console.log('\nNote: These are placeholder visualizations.');
    console.log('For actual sprites, use OpenRA.Utility or XCC Mixer.');
}

main();