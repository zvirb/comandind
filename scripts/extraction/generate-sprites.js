#!/usr/bin/env node

/**
 * Sprite Generator for Command & Conquer RTS Game
 * Generates placeholder PNG sprites based on sprite-config.json
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createCanvas } from 'canvas';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read sprite configuration
const configPath = path.join(__dirname, 'public/assets/sprites/sprite-config.json');
const spriteConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// Color schemes for different factions
const colorSchemes = {
    gdi: {
        primary: '#FFD700',    // Gold
        secondary: '#1E3A8A',  // Blue
        accent: '#FFFFFF'      // White
    },
    nod: {
        primary: '#DC2626',    // Red
        secondary: '#1F2937',  // Dark Gray
        accent: '#000000'      // Black
    },
    tiberium: {
        green: '#10B981',      // Green
        blue: '#3B82F6'        // Blue
    }
};

/**
 * Generate a sprite sheet with multiple frames
 */
function generateSpriteSheet(width, height, frameCount, colors, entityName, type) {
    const canvas = createCanvas(width * frameCount, height);
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    for (let i = 0; i < frameCount; i++) {
        const x = i * width;
        
        // Draw frame based on type
        if (type === 'structure') {
            drawStructure(ctx, x, 0, width, height, colors, i, frameCount);
        } else if (type === 'unit') {
            drawUnit(ctx, x, 0, width, height, colors, i, frameCount);
        } else if (type === 'resource') {
            drawResource(ctx, x, 0, width, height, colors.primary || colors.green || colors.blue, i, frameCount);
        }
        
        // Frame number
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.font = '8px Arial';
        ctx.fillText(i.toString(), x + 2, 10);
    }
    
    // Add entity name
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.font = '10px Arial';
    ctx.fillText(entityName, 2, height - 2);
    
    return canvas.toBuffer('image/png');
}

/**
 * Draw a structure sprite
 */
function drawStructure(ctx, x, y, width, height, colors, frame, totalFrames) {
    // Building base
    ctx.fillStyle = colors.secondary;
    ctx.fillRect(x + width * 0.1, y + height * 0.3, width * 0.8, height * 0.6);
    
    // Building top
    ctx.fillStyle = colors.primary;
    ctx.fillRect(x + width * 0.2, y + height * 0.1, width * 0.6, height * 0.3);
    
    // Windows/details with animation
    const windowAlpha = 0.5 + 0.5 * Math.sin((frame / totalFrames) * Math.PI * 2);
    ctx.fillStyle = `rgba(255, 255, 255, ${windowAlpha})`;
    ctx.fillRect(x + width * 0.3, y + height * 0.4, width * 0.1, height * 0.1);
    ctx.fillRect(x + width * 0.6, y + height * 0.4, width * 0.1, height * 0.1);
    
    // Faction emblem
    ctx.strokeStyle = colors.accent;
    ctx.lineWidth = 1;
    ctx.strokeRect(x + width * 0.4, y + height * 0.15, width * 0.2, height * 0.15);
}

/**
 * Draw a unit sprite
 */
function drawUnit(ctx, x, y, width, height, colors, frame, totalFrames) {
    // Calculate rotation for directional sprites
    const angle = (frame / totalFrames) * Math.PI * 2;
    
    ctx.save();
    ctx.translate(x + width / 2, y + height / 2);
    ctx.rotate(angle);
    
    // Unit body
    ctx.fillStyle = colors.secondary;
    ctx.fillRect(-width * 0.3, -height * 0.2, width * 0.6, height * 0.4);
    
    // Unit turret/top
    ctx.fillStyle = colors.primary;
    ctx.fillRect(-width * 0.2, -height * 0.1, width * 0.4, height * 0.2);
    
    // Direction indicator
    ctx.strokeStyle = colors.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(width * 0.3, 0);
    ctx.stroke();
    
    ctx.restore();
}

/**
 * Draw a resource sprite
 */
function drawResource(ctx, x, y, width, height, color, frame, totalFrames) {
    // Animated crystalline structure
    const scale = 0.8 + 0.2 * Math.sin((frame / totalFrames) * Math.PI * 2);
    
    ctx.save();
    ctx.translate(x + width / 2, y + height / 2);
    ctx.scale(scale, scale);
    
    // Crystal shape
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(0, -height * 0.4);
    ctx.lineTo(-width * 0.3, 0);
    ctx.lineTo(-width * 0.2, height * 0.3);
    ctx.lineTo(width * 0.2, height * 0.3);
    ctx.lineTo(width * 0.3, 0);
    ctx.closePath();
    ctx.fill();
    
    // Shimmer effect
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.beginPath();
    ctx.moveTo(0, -height * 0.3);
    ctx.lineTo(-width * 0.1, 0);
    ctx.lineTo(width * 0.1, 0);
    ctx.closePath();
    ctx.fill();
    
    ctx.restore();
}

/**
 * Process and generate sprites for a category
 */
function processCategory(category, data, basePath) {
    console.log(`\nProcessing ${category}...`);
    
    if (category === 'structures' || category === 'units') {
        // Process faction-based entities
        for (const [faction, entities] of Object.entries(data)) {
            const factionPath = path.join(basePath, category, faction);
            
            for (const [entityName, entityData] of Object.entries(entities)) {
                const frameWidth = entityData.frameWidth || 32;
                const frameHeight = entityData.frameHeight || 32;
                
                // Determine frame count
                let frameCount = 1;
                if (entityData.animations) {
                    // Find the animation with the most frames
                    for (const animation of Object.values(entityData.animations)) {
                        if (Array.isArray(animation.frames)) {
                            frameCount = Math.max(frameCount, Math.max(...animation.frames) + 1);
                        } else if (animation.frames === 'directional' && entityData.directions) {
                            frameCount = entityData.directions;
                        }
                    }
                }
                
                // For units with turrets, double the frame count
                if (entityData.animations?.turret) {
                    frameCount *= 2;
                }
                
                const outputPath = path.join(factionPath, `${entityName}.png`);
                const spriteBuffer = generateSpriteSheet(
                    frameWidth,
                    frameHeight,
                    frameCount,
                    colorSchemes[faction],
                    entityName,
                    category.slice(0, -1) // Remove 's' from category name
                );
                
                fs.writeFileSync(outputPath, spriteBuffer);
                console.log(`  ✓ Generated ${faction}/${entityName}.png (${frameWidth}x${frameHeight}, ${frameCount} frames)`);
            }
        }
    } else if (category === 'tiberium') {
        // Process resources
        const resourcePath = path.join(basePath, 'resources');
        
        for (const [resourceType, resourceData] of Object.entries(data)) {
            const frameWidth = resourceData.frameWidth || 24;
            const frameHeight = resourceData.frameHeight || 24;
            let frameCount = 4; // Default for tiberium animations
            
            if (resourceData.animations?.idle?.frames) {
                frameCount = resourceData.animations.idle.frames.length;
            }
            
            const outputPath = path.join(resourcePath, `${resourceType}.png`);
            const spriteBuffer = generateSpriteSheet(
                frameWidth,
                frameHeight,
                frameCount,
                colorSchemes.tiberium,
                `tiberium-${resourceType}`,
                'resource'
            );
            
            fs.writeFileSync(outputPath, spriteBuffer);
            console.log(`  ✓ Generated resources/${resourceType}.png (${frameWidth}x${frameHeight}, ${frameCount} frames)`);
        }
    }
}

/**
 * Main execution
 */
function main() {
    console.log('🎮 Command & Conquer Sprite Generator');
    console.log('=====================================');
    
    const basePath = path.join(__dirname, 'public/assets/sprites');
    
    // Process each category
    for (const [category, data] of Object.entries(spriteConfig)) {
        processCategory(category, data, basePath);
    }
    
    console.log('\n✅ Sprite generation complete!');
    console.log(`📁 Sprites saved to: ${basePath}`);
    
    // Generate a summary
    const summary = {
        generated: new Date().toISOString(),
        categories: Object.keys(spriteConfig),
        totals: {
            structures: {
                gdi: Object.keys(spriteConfig.structures?.gdi || {}).length,
                nod: Object.keys(spriteConfig.structures?.nod || {}).length
            },
            units: {
                gdi: Object.keys(spriteConfig.units?.gdi || {}).length,
                nod: Object.keys(spriteConfig.units?.nod || {}).length
            },
            resources: Object.keys(spriteConfig.tiberium || {}).length
        }
    };
    
    fs.writeFileSync(
        path.join(basePath, 'sprite-generation-summary.json'),
        JSON.stringify(summary, null, 2)
    );
    
    console.log('\n📊 Summary saved to sprite-generation-summary.json');
}

// Run the sprite generator
main();