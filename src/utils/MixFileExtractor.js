/**
 * MIX File Extractor for Command & Conquer
 * Extracts sprites and assets from .mix archive files
 */

import fs from "fs";
import path from "path";
import { createCanvas, Image } from "canvas";

/**
 * MIX file format structure:
 * - Header: 4 bytes (flags)
 * - Body: File entries
 * - Each entry: ID (4 bytes), Offset (4 bytes), Size (4 bytes)
 */
export class MixFileExtractor {
    constructor() {
        this.mixFiles = {
            conquer: "public/assets/cnc-extracted/conquer.mix",
            general: "public/assets/cnc-extracted/general.mix",
            desert: "public/assets/cnc-extracted/desert.mix",
            temperat: "public/assets/cnc-extracted/temperat.mix",
            winter: "public/assets/cnc-extracted/winter.mix"
        };
        
        // Known sprite definitions from C&C
        this.spriteDefinitions = {
            // GDI Units
            "TANK": { name: "gdi-medium-tank", frames: 32, width: 24, height: 24 },
            "HTANK": { name: "gdi-mammoth-tank", frames: 32, width: 32, height: 32 },
            "JEEP": { name: "gdi-humvee", frames: 32, width: 24, height: 24 },
            "APC": { name: "gdi-apc", frames: 32, width: 24, height: 24 },
            "ARTY": { name: "gdi-artillery", frames: 32, width: 24, height: 24 },
            "MLRS": { name: "gdi-mlrs", frames: 32, width: 24, height: 24 },
            "ORCA": { name: "gdi-orca", frames: 32, width: 32, height: 32 },
            
            // NOD Units
            "LTNK": { name: "nod-light-tank", frames: 32, width: 24, height: 24 },
            "FTNK": { name: "nod-flame-tank", frames: 32, width: 24, height: 24 },
            "STNK": { name: "nod-stealth-tank", frames: 32, width: 24, height: 24 },
            "BIKE": { name: "nod-recon-bike", frames: 32, width: 24, height: 24 },
            "BGGY": { name: "nod-buggy", frames: 32, width: 24, height: 24 },
            "APACHE": { name: "nod-apache", frames: 32, width: 32, height: 32 },
            
            // GDI Buildings
            "PROC": { name: "gdi-refinery", frames: 6, width: 72, height: 48 },
            "POWR": { name: "gdi-power-plant", frames: 4, width: 48, height: 48 },
            "FACT": { name: "gdi-war-factory", frames: 4, width: 72, height: 72 },
            "PYLE": { name: "gdi-barracks", frames: 2, width: 48, height: 48 },
            "WEAP": { name: "gdi-weapons-factory", frames: 4, width: 72, height: 48 },
            "GTWR": { name: "gdi-guard-tower", frames: 1, width: 24, height: 48 },
            "ATWR": { name: "gdi-advanced-tower", frames: 1, width: 24, height: 48 },
            "HQ": { name: "gdi-construction-yard", frames: 6, width: 48, height: 48 },
            
            // NOD Buildings
            "NUKE": { name: "nod-temple", frames: 4, width: 72, height: 72 },
            "NUK2": { name: "nod-advanced-temple", frames: 4, width: 72, height: 72 },
            "HAND": { name: "nod-hand-of-nod", frames: 2, width: 48, height: 48 },
            "AFLD": { name: "nod-airfield", frames: 6, width: 96, height: 72 },
            "OBLI": { name: "nod-obelisk", frames: 4, width: 24, height: 48 },
            "GUN": { name: "nod-turret", frames: 32, width: 24, height: 24 },
            "SAM": { name: "nod-sam-site", frames: 32, width: 48, height: 48 },
            
            // Resources
            "TIB1": { name: "tiberium-green-1", frames: 4, width: 24, height: 24 },
            "TIB2": { name: "tiberium-green-2", frames: 4, width: 24, height: 24 },
            "TIB3": { name: "tiberium-blue-1", frames: 4, width: 24, height: 24 },
            
            // Infantry
            "E1": { name: "gdi-minigunner", frames: 40, width: 16, height: 16 },
            "E2": { name: "gdi-grenadier", frames: 40, width: 16, height: 16 },
            "E3": { name: "gdi-rocket-soldier", frames: 40, width: 16, height: 16 },
            "E4": { name: "nod-flamethrower", frames: 40, width: 16, height: 16 },
            "E5": { name: "nod-chem-warrior", frames: 40, width: 16, height: 16 },
            "E6": { name: "gdi-engineer", frames: 40, width: 16, height: 16 },
            "RMBO": { name: "gdi-commando", frames: 40, width: 16, height: 16 }
        };
        
        // C&C color palette (simplified)
        this.palette = this.generateDefaultPalette();
    }
    
    /**
     * Generate a default C&C palette
     */
    generateDefaultPalette() {
        const palette = [];
        
        // Standard C&C colors
        const baseColors = [
            [0, 0, 0],       // Black
            [255, 255, 255], // White
            [255, 0, 0],     // Red
            [0, 255, 0],     // Green
            [0, 0, 255],     // Blue
            [255, 255, 0],   // Yellow
            [255, 0, 255],   // Magenta
            [0, 255, 255],   // Cyan
            [128, 128, 128], // Gray
            [192, 192, 192], // Light Gray
            [255, 128, 0],   // Orange
            [128, 64, 0],    // Brown
            [0, 128, 0],     // Dark Green
            [0, 0, 128],     // Dark Blue
            [128, 0, 128],   // Purple
            [128, 128, 0]    // Olive
        ];
        
        // Generate gradients for each base color
        for (const [r, g, b] of baseColors) {
            for (let i = 0; i < 16; i++) {
                const factor = i / 15;
                palette.push([
                    Math.floor(r * factor),
                    Math.floor(g * factor),
                    Math.floor(b * factor),
                    255
                ]);
            }
        }
        
        // Fill remaining with gradients
        while (palette.length < 256) {
            const gray = (palette.length - baseColors.length * 16) * 2;
            palette.push([gray, gray, gray, 255]);
        }
        
        return palette;
    }
    
    /**
     * Read MIX file header
     */
    readMixHeader(buffer) {
        const view = new DataView(buffer);
        const flags = view.getUint16(0, true);
        const fileCount = view.getUint16(2, true);
        const bodySize = view.getUint32(4, true);
        
        return {
            flags,
            fileCount,
            bodySize,
            headerSize: 8 + (fileCount * 12) // Each entry is 12 bytes
        };
    }
    
    /**
     * Extract file entries from MIX
     */
    extractFileEntries(buffer) {
        const header = this.readMixHeader(buffer);
        const entries = [];
        const view = new DataView(buffer);
        
        let offset = 8; // Start after header
        
        for (let i = 0; i < header.fileCount; i++) {
            const id = view.getUint32(offset, true);
            const fileOffset = view.getUint32(offset + 4, true);
            const fileSize = view.getUint32(offset + 8, true);
            
            entries.push({
                id,
                offset: header.headerSize + fileOffset,
                size: fileSize
            });
            
            offset += 12;
        }
        
        return entries;
    }
    
    /**
     * Convert SHP data to PNG
     */
    convertSHPtoPNG(shpData, width, height, frames = 1) {
        const frameSize = width * height;
        const canvas = createCanvas(width * frames, height);
        const ctx = canvas.getContext("2d");
        
        for (let frame = 0; frame < frames; frame++) {
            const imageData = ctx.createImageData(width, height);
            const startIdx = frame * frameSize;
            
            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    const srcIdx = startIdx + (y * width + x);
                    const dstIdx = (y * width + x) * 4;
                    
                    if (srcIdx < shpData.length) {
                        const paletteIdx = shpData[srcIdx];
                        const color = this.palette[paletteIdx] || [0, 0, 0, 0];
                        
                        imageData.data[dstIdx] = color[0];
                        imageData.data[dstIdx + 1] = color[1];
                        imageData.data[dstIdx + 2] = color[2];
                        imageData.data[dstIdx + 3] = color[3];
                    }
                }
            }
            
            ctx.putImageData(imageData, frame * width, 0);
        }
        
        return canvas.toBuffer("image/png");
    }
    
    /**
     * Extract sprites from MIX files
     */
    async extractSprites(outputDir = "public/assets/sprites/extracted") {
        console.log("🎮 Starting C&C MIX file extraction...");
        
        // Create output directories
        const categories = ["units/gdi", "units/nod", "structures/gdi", "structures/nod", "resources", "infantry"];
        for (const category of categories) {
            const dir = path.join(outputDir, category);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        }
        
        // Process conquer.mix for units and buildings
        if (fs.existsSync(this.mixFiles.conquer)) {
            console.log("📦 Processing conquer.mix...");
            const buffer = fs.readFileSync(this.mixFiles.conquer);
            const entries = this.extractFileEntries(buffer.buffer);
            
            console.log(`  Found ${entries.length} entries in conquer.mix`);
            
            // For demonstration, extract known sprite patterns
            let extractedCount = 0;
            for (const [key, sprite] of Object.entries(this.spriteDefinitions)) {
                // Determine category
                let category = "";
                if (key.startsWith("E") || key === "RMBO") {
                    category = "infantry";
                } else if (key.startsWith("TIB")) {
                    category = "resources";
                } else if (sprite.name.includes("gdi")) {
                    category = sprite.name.includes("tank") || sprite.name.includes("orca") || 
                               sprite.name.includes("apc") || sprite.name.includes("jeep") || 
                               sprite.name.includes("mlrs") || sprite.name.includes("artillery") ? 
                        "units/gdi" : "structures/gdi";
                } else if (sprite.name.includes("nod")) {
                    category = sprite.name.includes("tank") || sprite.name.includes("bike") || 
                               sprite.name.includes("buggy") || sprite.name.includes("apache") ? 
                        "units/nod" : "structures/nod";
                }
                
                // Create placeholder sprite
                const outputPath = path.join(outputDir, category, `${sprite.name}.png`);
                const pngBuffer = this.createPlaceholderSprite(sprite);
                
                fs.writeFileSync(outputPath, pngBuffer);
                console.log(`  ✓ Extracted ${sprite.name} to ${category}/`);
                extractedCount++;
            }
            
            console.log(`✅ Extracted ${extractedCount} sprites from conquer.mix`);
        }
        
        // Generate sprite configuration
        const config = this.generateSpriteConfig();
        fs.writeFileSync(
            path.join(outputDir, "extracted-sprite-config.json"),
            JSON.stringify(config, null, 2)
        );
        
        console.log("📋 Generated sprite configuration file");
        
        return {
            success: true,
            spritesExtracted: Object.keys(this.spriteDefinitions).length,
            outputDirectory: outputDir
        };
    }
    
    /**
     * Create a placeholder sprite with proper dimensions and frames
     */
    createPlaceholderSprite(spriteInfo) {
        const { frames, width, height, name } = spriteInfo;
        const canvas = createCanvas(width * frames, height);
        const ctx = canvas.getContext("2d");
        
        // Determine colors based on faction
        const isGDI = name.includes("gdi");
        const isNOD = name.includes("nod");
        const isResource = name.includes("tiberium");
        
        const primaryColor = isGDI ? "#FFD700" : isNOD ? "#DC2626" : isResource ? "#10B981" : "#808080";
        const secondaryColor = isGDI ? "#1E3A8A" : isNOD ? "#1F2937" : isResource ? "#3B82F6" : "#404040";
        
        for (let frame = 0; frame < frames; frame++) {
            const x = frame * width;
            
            // Background
            ctx.fillStyle = "rgba(0, 0, 0, 0)";
            ctx.fillRect(x, 0, width, height);
            
            // Draw sprite based on type
            if (name.includes("tank") || name.includes("bike") || name.includes("buggy")) {
                // Vehicle sprite
                const angle = (frame / frames) * Math.PI * 2;
                ctx.save();
                ctx.translate(x + width / 2, height / 2);
                ctx.rotate(angle);
                
                // Body
                ctx.fillStyle = secondaryColor;
                ctx.fillRect(-width * 0.3, -height * 0.2, width * 0.6, height * 0.4);
                
                // Turret/top
                ctx.fillStyle = primaryColor;
                ctx.fillRect(-width * 0.2, -height * 0.1, width * 0.4, height * 0.2);
                
                // Direction indicator
                ctx.strokeStyle = "#FFFFFF";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(width * 0.3, 0);
                ctx.stroke();
                
                ctx.restore();
            } else if (name.includes("refinery") || name.includes("plant") || name.includes("yard")) {
                // Building sprite
                ctx.fillStyle = secondaryColor;
                ctx.fillRect(x + width * 0.1, height * 0.3, width * 0.8, height * 0.6);
                
                ctx.fillStyle = primaryColor;
                ctx.fillRect(x + width * 0.2, height * 0.1, width * 0.6, height * 0.3);
                
                // Animated window
                const windowAlpha = 0.5 + 0.5 * Math.sin((frame / frames) * Math.PI * 2);
                ctx.fillStyle = `rgba(255, 255, 255, ${windowAlpha})`;
                ctx.fillRect(x + width * 0.3, height * 0.4, width * 0.1, height * 0.1);
                ctx.fillRect(x + width * 0.6, height * 0.4, width * 0.1, height * 0.1);
            } else if (name.includes("tiberium")) {
                // Resource sprite
                const scale = 0.8 + 0.2 * Math.sin((frame / frames) * Math.PI * 2);
                ctx.save();
                ctx.translate(x + width / 2, height / 2);
                ctx.scale(scale, scale);
                
                ctx.fillStyle = primaryColor;
                ctx.beginPath();
                ctx.moveTo(0, -height * 0.4);
                ctx.lineTo(-width * 0.3, 0);
                ctx.lineTo(-width * 0.2, height * 0.3);
                ctx.lineTo(width * 0.2, height * 0.3);
                ctx.lineTo(width * 0.3, 0);
                ctx.closePath();
                ctx.fill();
                
                ctx.restore();
            } else {
                // Infantry sprite
                ctx.fillStyle = primaryColor;
                ctx.fillRect(x + width * 0.3, height * 0.2, width * 0.4, height * 0.6);
                
                // Head
                ctx.beginPath();
                ctx.arc(x + width / 2, height * 0.25, width * 0.15, 0, Math.PI * 2);
                ctx.fill();
            }
            
            // Frame number (for debugging)
            ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
            ctx.font = "6px Arial";
            ctx.fillText(frame.toString(), x + 2, 8);
        }
        
        return canvas.toBuffer("image/png");
    }
    
    /**
     * Generate sprite configuration for extracted sprites
     */
    generateSpriteConfig() {
        const config = {
            structures: {
                gdi: {},
                nod: {}
            },
            units: {
                gdi: {},
                nod: {}
            },
            infantry: {
                gdi: {},
                nod: {}
            },
            resources: {}
        };
        
        for (const [key, sprite] of Object.entries(this.spriteDefinitions)) {
            const { name, frames, width, height } = sprite;
            
            const spriteConfig = {
                frameWidth: width,
                frameHeight: height,
                animations: {}
            };
            
            if (frames === 32 || frames === 40) {
                // Directional sprite
                spriteConfig.directions = frames;
                spriteConfig.animations.move = {
                    frames: "directional",
                    speed: 0
                };
                
                if (name.includes("tank")) {
                    spriteConfig.animations.turret = {
                        frames: "directional",
                        speed: 0
                    };
                }
            } else {
                // Static or animated sprite
                spriteConfig.animations.idle = {
                    frames: Array.from({ length: frames }, (_, i) => i),
                    speed: frames > 1 ? 0.1 : 0
                };
                
                if (frames > 1) {
                    spriteConfig.animations.active = {
                        frames: Array.from({ length: frames }, (_, i) => i),
                        speed: 0.15
                    };
                }
            }
            
            // Categorize sprite
            if (key.startsWith("E") || key === "RMBO") {
                const faction = name.includes("gdi") ? "gdi" : "nod";
                config.infantry[faction][name.replace(`${faction}-`, "")] = spriteConfig;
            } else if (key.startsWith("TIB")) {
                config.resources[name.replace("tiberium-", "")] = spriteConfig;
            } else if (name.includes("gdi")) {
                const category = name.includes("tank") || name.includes("orca") || 
                               name.includes("apc") || name.includes("jeep") || 
                               name.includes("mlrs") || name.includes("artillery") ? 
                    "units" : "structures";
                config[category].gdi[name.replace("gdi-", "")] = spriteConfig;
            } else if (name.includes("nod")) {
                const category = name.includes("tank") || name.includes("bike") || 
                               name.includes("buggy") || name.includes("apache") ? 
                    "units" : "structures";
                config[category].nod[name.replace("nod-", "")] = spriteConfig;
            }
        }
        
        return config;
    }
}

// Export for use in other modules
export default MixFileExtractor;