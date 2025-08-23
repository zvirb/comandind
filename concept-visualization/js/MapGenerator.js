import TerrainGenerator from './TerrainGenerator.js';
import { createMapGenerator, AdvancedMapGenerator } from '../../src/mapgen/index.js';

class MapGenerator {
    constructor(canvas, spriteConfig) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.spriteConfig = spriteConfig;
        this.tileSize = 32;
        this.mapWidth = 40;
        this.mapHeight = 30;
        this.sprites = {};
        this.loadedImages = {};
        this.terrainMap = null; // Store generated terrain
        
        // Progressive loading state
        this.loadingState = {
            isLoading: false,
            totalSprites: 0,
            loadedSprites: 0,
            priority: 'high' // high, medium, low
        };
        
        // Advanced map generation integration
        this.advancedGenerator = null;
        this.useAdvancedGeneration = true;
        this.textureAtlas = null;
        
        // Device capability detection
        this.deviceCapabilities = this.detectDeviceCapabilities();
    }

    async init() {
        // Initialize responsive canvas
        this.setupResponsiveCanvas();
        
        // Progressive sprite loading based on device capabilities
        await this.loadSpritesProgressively();
        
        // Initialize advanced map generation
        await this.initializeAdvancedGeneration();
        
        // Generate terrain using appropriate method
        await this.generateTerrainMap();
    }
    
    async generateTerrainMap() {
        try {
            if (this.useAdvancedGeneration && this.advancedGenerator) {
                // Use advanced map generation for enhanced terrain
                const advancedMapData = await this.advancedGenerator.generateMap();
                
                // Integrate advanced data with existing terrain system
                this.terrainMap = this.convertAdvancedTerrainData(advancedMapData.terrain);
                this.tiberiumFields = advancedMapData.resources || [];
                this.terrainMetadata = advancedMapData.metadata;
                
                console.log('Generated advanced C&C terrain map:', advancedMapData.summary);
            } else {
                // Fallback to improved TerrainGenerator for compatibility
                const terrainGenerator = new TerrainGenerator(this.mapWidth, this.mapHeight);
                const terrainData = terrainGenerator.generateMap();
                
                this.terrainMap = terrainData.map;
                this.tiberiumFields = terrainData.tiberiumFields;
                this.terrainMetadata = terrainData.metadata;
                
                console.log('Generated C&C terrain map:', terrainGenerator.getMapSummary());
            }
        } catch (error) {
            console.warn('Advanced generation failed, using fallback:', error.message);
            // Fallback to basic generation
            const terrainGenerator = new TerrainGenerator(this.mapWidth, this.mapHeight);
            const terrainData = terrainGenerator.generateMap();
            this.terrainMap = terrainData.map;
            this.tiberiumFields = terrainData.tiberiumFields;
            this.terrainMetadata = terrainData.metadata;
        }
    }
    
    // Device capability detection for optimization
    detectDeviceCapabilities() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const memoryInfo = navigator.deviceMemory || (isMobile ? 2 : 8); // Estimate if not available
        const isLowEnd = memoryInfo < 4 || isMobile;
        
        return {
            isMobile,
            isLowEnd,
            deviceMemory: memoryInfo,
            maxTextureSize: this.getMaxTextureSize(ctx),
            supportsWebGL: !!document.createElement('canvas').getContext('webgl'),
            pixelRatio: window.devicePixelRatio || 1
        };
    }
    
    getMaxTextureSize(ctx) {
        // Try to get WebGL context for accurate texture size
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl');
        if (gl) {
            return gl.getParameter(gl.MAX_TEXTURE_SIZE);
        }
        // Fallback estimation
        return this.deviceCapabilities.isLowEnd ? 1024 : 2048;
    }
    
    // Setup responsive canvas based on device capabilities
    setupResponsiveCanvas() {
        const container = this.canvas.parentElement;
        const containerWidth = container ? container.clientWidth : window.innerWidth;
        const containerHeight = container ? container.clientHeight : window.innerHeight;
        
        // Calculate optimal canvas size
        const maxCanvasWidth = this.deviceCapabilities.isLowEnd ? 800 : 1280;
        const maxCanvasHeight = this.deviceCapabilities.isLowEnd ? 600 : 960;
        
        const scaleX = Math.min(maxCanvasWidth, containerWidth) / (this.mapWidth * this.tileSize);
        const scaleY = Math.min(maxCanvasHeight, containerHeight) / (this.mapHeight * this.tileSize);
        const scale = Math.min(scaleX, scaleY, this.deviceCapabilities.isLowEnd ? 1 : 2);
        
        this.canvas.width = this.mapWidth * this.tileSize * scale;
        this.canvas.height = this.mapHeight * this.tileSize * scale;
        this.canvas.style.width = `${this.mapWidth * this.tileSize * scale / this.deviceCapabilities.pixelRatio}px`;
        this.canvas.style.height = `${this.mapHeight * this.tileSize * scale / this.deviceCapabilities.pixelRatio}px`;
        
        // Scale context for high-DPI displays
        this.ctx.scale(scale * this.deviceCapabilities.pixelRatio, scale * this.deviceCapabilities.pixelRatio);
        
        this.renderScale = scale;
    }
    
    // Initialize advanced map generation system
    async initializeAdvancedGeneration() {
        try {
            // Configure advanced generator based on device capabilities
            const generatorConfig = {
                width: this.mapWidth,
                height: this.mapHeight,
                algorithm: this.deviceCapabilities.isLowEnd ? 'classic' : 'hybrid',
                climate: 'temperate',
                resourceBalance: true,
                enableValidation: !this.deviceCapabilities.isLowEnd,
                qualityThreshold: this.deviceCapabilities.isLowEnd ? 50 : 75
            };
            
            this.advancedGenerator = createMapGenerator(generatorConfig);
            console.log('Advanced map generation initialized');
        } catch (error) {
            console.warn('Failed to initialize advanced generation:', error.message);
            this.useAdvancedGeneration = false;
        }
    }
    
    // Convert advanced terrain data to legacy format
    convertAdvancedTerrainData(advancedTerrain) {
        if (!advancedTerrain) return null;
        
        const legacyMap = [];
        for (let y = 0; y < this.mapHeight; y++) {
            legacyMap[y] = [];
            for (let x = 0; x < this.mapWidth; x++) {
                const advancedTile = advancedTerrain[y] && advancedTerrain[y][x];
                if (advancedTile) {
                    // Map advanced tile types to legacy sprite keys
                    legacyMap[y][x] = this.mapAdvancedTileToSprite(advancedTile);
                } else {
                    // Fallback to sand
                    legacyMap[y][x] = 'S01';
                }
            }
        }
        return legacyMap;
    }
    
    mapAdvancedTileToSprite(advancedTile) {
        // Map advanced terrain types to C&C sprite keys
        const tileType = advancedTile.type || advancedTile;
        
        switch (tileType) {
            case 'sand':
            case 'clear':
                return ['S01', 'S02', 'S03', 'S04'][Math.floor(Math.random() * 4)];
            case 'dirt':
            case 'rough':
                return ['D01', 'D02', 'D03', 'D04'][Math.floor(Math.random() * 4)];
            case 'water':
                return Math.random() > 0.5 ? 'W1' : 'W2';
            case 'shore':
                return ['SH1', 'SH2', 'SH3'][Math.floor(Math.random() * 3)];
            case 'forest':
            case 'tree':
                return ['T01', 'T02', 'T03', 'T05'][Math.floor(Math.random() * 4)];
            case 'rock':
            case 'mountain':
                return ['ROCK1', 'ROCK2', 'ROCK3'][Math.floor(Math.random() * 3)];
            default:
                return 'S01'; // Default fallback
        }
    }
    
    // Progressive sprite loading for performance
    async loadSpritesProgressively() {
        this.loadingState.isLoading = true;
        
        // Define sprite priorities
        const highPrioritySprites = this.getHighPrioritySprites();
        const mediumPrioritySprites = this.getMediumPrioritySprites();
        const lowPrioritySprites = this.getLowPrioritySprites();
        
        this.loadingState.totalSprites = 
            highPrioritySprites.length + 
            mediumPrioritySprites.length + 
            (this.deviceCapabilities.isLowEnd ? 0 : lowPrioritySprites.length);
        
        // Load high priority sprites first
        await this.loadSpriteSet(highPrioritySprites, 'high');
        
        // Load medium priority sprites
        await this.loadSpriteSet(mediumPrioritySprites, 'medium');
        
        // Load low priority sprites only on capable devices
        if (!this.deviceCapabilities.isLowEnd) {
            // Use requestIdleCallback for low priority loading if available
            if (window.requestIdleCallback) {
                window.requestIdleCallback(() => {
                    this.loadSpriteSet(lowPrioritySprites, 'low');
                });
            } else {
                setTimeout(() => {
                    this.loadSpriteSet(lowPrioritySprites, 'low');
                }, 100);
            }
        }
        
        this.loadingState.isLoading = false;
        
        // Create texture atlas after sprite loading (if not on low-end device)
        if (!this.deviceCapabilities.isLowEnd) {
            await this.createTextureAtlas();
        }
    }
    
    getHighPrioritySprites() {
        // Essential terrain tiles for immediate rendering
        return [
            { path: '/public/assets/sprites/cnc-png/terrain/S01-0000.png', key: 'S01' },
            { path: '/public/assets/sprites/cnc-png/terrain/S02-0000.png', key: 'S02' },
            { path: '/public/assets/sprites/cnc-png/terrain/D01-0000.png', key: 'D01' },
            { path: '/public/assets/sprites/cnc-png/terrain/D02-0000.png', key: 'D02' },
            { path: '/public/assets/sprites/cnc-png/terrain/W1-0000.png', key: 'W1' },
            { path: '/public/assets/sprites/cnc-png/terrain/TI1-0000.png', key: 'TI1' }
        ];
    }
    
    getMediumPrioritySprites() {
        // Additional terrain and basic units/structures
        return [
            { path: '/public/assets/sprites/cnc-png/terrain/S03-0000.png', key: 'S03' },
            { path: '/public/assets/sprites/cnc-png/terrain/S04-0000.png', key: 'S04' },
            { path: '/public/assets/sprites/cnc-png/terrain/D03-0000.png', key: 'D03' },
            { path: '/public/assets/sprites/cnc-png/terrain/D04-0000.png', key: 'D04' },
            { path: '/public/assets/sprites/cnc-png/terrain/W2-0000.png', key: 'W2' },
            { path: '/public/assets/sprites/cnc-png/terrain/T01-0000.png', key: 'T01' },
            { path: '/public/assets/sprites/cnc-png/terrain/T02-0000.png', key: 'T02' },
            { path: '/public/assets/sprites/cnc-png/individual/construction-yard-0000.png', key: 'gdi-cy' },
            { path: '/public/assets/sprites/cnc-png/individual/barracks-0000.png', key: 'gdi-barracks' },
            { path: '/public/assets/sprites/cnc-png/individual/mammoth-tank-0000.png', key: 'mammoth' }
        ];
    }
    
    getLowPrioritySprites() {
        // Full sprite set for high-end devices - using actual available sprites
        return [
            // Additional terrain variations
            { path: '/public/assets/sprites/cnc-png/terrain/S03-0000.png', key: 'S03' },
            { path: '/public/assets/sprites/cnc-png/terrain/S04-0000.png', key: 'S04' },
            { path: '/public/assets/sprites/cnc-png/terrain/S05-0000.png', key: 'S05' },
            { path: '/public/assets/sprites/cnc-png/terrain/S06-0000.png', key: 'S06' },
            { path: '/public/assets/sprites/cnc-png/terrain/D03-0000.png', key: 'D03' },
            { path: '/public/assets/sprites/cnc-png/terrain/D04-0000.png', key: 'D04' },
            { path: '/public/assets/sprites/cnc-png/terrain/D05-0000.png', key: 'D05' },
            { path: '/public/assets/sprites/cnc-png/terrain/D06-0000.png', key: 'D06' },
            
            // Shore transitions (using actual naming)
            { path: '/public/assets/sprites/cnc-png/terrain/BR1-0000.png', key: 'BR1' },
            { path: '/public/assets/sprites/cnc-png/terrain/BR2-0000.png', key: 'BR2' },
            { path: '/public/assets/sprites/cnc-png/terrain/BR3-0000.png', key: 'BR3' },
            { path: '/public/assets/sprites/cnc-png/terrain/BR4-0000.png', key: 'BR4' },
            { path: '/public/assets/sprites/cnc-png/terrain/BR5-0000.png', key: 'BR5' },
            { path: '/public/assets/sprites/cnc-png/terrain/BR6-0000.png', key: 'BR6' },
            
            // Tree variations
            { path: '/public/assets/sprites/cnc-png/terrain/T03-0000.png', key: 'T03' },
            { path: '/public/assets/sprites/cnc-png/terrain/T04-0000.png', key: 'T04' },
            { path: '/public/assets/sprites/cnc-png/terrain/T05-0000.png', key: 'T05' },
            { path: '/public/assets/sprites/cnc-png/terrain/T06-0000.png', key: 'T06' },
            { path: '/public/assets/sprites/cnc-png/terrain/T07-0000.png', key: 'T07' },
            { path: '/public/assets/sprites/cnc-png/terrain/T08-0000.png', key: 'T08' },
            
            // Boulder formations
            { path: '/public/assets/sprites/cnc-png/terrain/B1-0000.png', key: 'B1' },
            { path: '/public/assets/sprites/cnc-png/terrain/B2-0000.png', key: 'B2' },
            { path: '/public/assets/sprites/cnc-png/terrain/B3-0000.png', key: 'B3' },
            { path: '/public/assets/sprites/cnc-png/terrain/B4-0000.png', key: 'B4' },
            { path: '/public/assets/sprites/cnc-png/terrain/B5-0000.png', key: 'B5' },
            { path: '/public/assets/sprites/cnc-png/terrain/B6-0000.png', key: 'B6' },
            
            // Additional tiberium
            { path: '/public/assets/sprites/cnc-png/terrain/TI2-0000.png', key: 'TI2' },
            { path: '/public/assets/sprites/cnc-png/terrain/TI3-0000.png', key: 'TI3' },
            { path: '/public/assets/sprites/cnc-png/terrain/TI4-0000.png', key: 'TI4' },
            { path: '/public/assets/sprites/cnc-png/terrain/TI5-0000.png', key: 'TI5' },
            { path: '/public/assets/sprites/cnc-png/terrain/TI6-0000.png', key: 'TI6' },
            
            // Units and structures (using available sprites)
            { path: '/public/assets/sprites/cnc-png/individual/power-plant-0000.png', key: 'gdi-power' },
            { path: '/public/assets/sprites/cnc-png/individual/refinery-0000.png', key: 'gdi-refinery' },
            { path: '/public/assets/sprites/cnc-png/individual/hand-of-nod-0000.png', key: 'nod-hand' },
            { path: '/public/assets/sprites/cnc-png/individual/obelisk-0000.png', key: 'nod-obelisk' },
            { path: '/public/assets/sprites/cnc-png/medium-tank-0000.png', key: 'medium-tank' },
            { path: '/public/assets/sprites/cnc-png/individual/recon-bike-0000.png', key: 'recon-bike' },
            { path: '/public/assets/sprites/cnc-png/individual/mammoth-tank-0008.png', key: 'mammoth-right' },
            { path: '/public/assets/sprites/cnc-png/medium-tank-0016.png', key: 'medium-tank-down' }
        ];
    }
    
    async loadSpriteSet(sprites, priority) {
        const loadPromises = sprites.map(sprite => {
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = () => {
                    this.loadedImages[sprite.key] = img;
                    this.loadingState.loadedSprites++;
                    resolve();
                };
                img.onerror = () => {
                    console.warn(`Failed to load ${priority} priority sprite: ${sprite.path}`);
                    this.createPlaceholder(sprite.key);
                    this.loadingState.loadedSprites++;
                    resolve();
                };
                img.src = sprite.path;
            });
        });
        
        await Promise.all(loadPromises);
        console.log(`Loaded ${sprites.length} ${priority} priority sprites`);
    }
    
    // Texture atlas support for performance
    async createTextureAtlas(sprites) {
        if (this.deviceCapabilities.isLowEnd) {
            // Skip atlas creation on low-end devices to save memory
            console.log('Skipping texture atlas creation on low-end device');
            return null;
        }
        
        try {
            const atlasSize = Math.min(this.deviceCapabilities.maxTextureSize, 2048);
            const tileSize = 32; // Standard C&C tile size
            const tilesPerRow = Math.floor(atlasSize / tileSize);
            
            // Create atlas canvas
            const atlasCanvas = document.createElement('canvas');
            atlasCanvas.width = atlasSize;
            atlasCanvas.height = atlasSize;
            const atlasCtx = atlasCanvas.getContext('2d');
            
            // Atlas mapping for UV coordinates
            const atlasMap = new Map();
            
            let currentRow = 0;
            let currentCol = 0;
            
            for (const [key, image] of Object.entries(this.loadedImages)) {
                if (currentCol >= tilesPerRow) {
                    currentCol = 0;
                    currentRow++;
                }
                
                if (currentRow * tileSize >= atlasSize) {
                    console.warn('Atlas size exceeded, some sprites will not be atlased');
                    break;
                }
                
                const x = currentCol * tileSize;
                const y = currentRow * tileSize;
                
                // Draw sprite to atlas
                atlasCtx.drawImage(image, x, y, tileSize, tileSize);
                
                // Store UV coordinates
                atlasMap.set(key, {
                    u: x / atlasSize,
                    v: y / atlasSize,
                    width: tileSize / atlasSize,
                    height: tileSize / atlasSize,
                    pixelX: x,
                    pixelY: y
                });
                
                currentCol++;
            }
            
            this.textureAtlas = {
                canvas: atlasCanvas,
                texture: atlasCanvas,
                map: atlasMap,
                size: atlasSize,
                tileSize: tileSize
            };
            
            console.log(`Created texture atlas: ${atlasMap.size} sprites, ${atlasSize}x${atlasSize}px`);
            return this.textureAtlas;
            
        } catch (error) {
            console.warn('Failed to create texture atlas:', error.message);
            return null;
        }
    }
    
    // Enhanced drawing method with atlas support
    drawSpriteAtlas(spriteKey, x, y, scale = 1) {
        if (!this.textureAtlas || !this.textureAtlas.map.has(spriteKey)) {
            // Fallback to regular drawing
            return this.drawSprite(spriteKey, x, y, scale);
        }
        
        const atlasInfo = this.textureAtlas.map.get(spriteKey);
        const drawWidth = this.textureAtlas.tileSize * scale;
        const drawHeight = this.textureAtlas.tileSize * scale;
        
        // Center the sprite at the given position
        const drawX = x - drawWidth / 2;
        const drawY = y - drawHeight / 2;
        
        this.ctx.drawImage(
            this.textureAtlas.canvas,
            atlasInfo.pixelX, atlasInfo.pixelY,
            this.textureAtlas.tileSize, this.textureAtlas.tileSize,
            drawX, drawY,
            drawWidth, drawHeight
        );
    }
    
    // Memory management for texture resources
    cleanupTextureMemory() {
        if (this.textureAtlas) {
            // Clear atlas canvas to free GPU memory
            const ctx = this.textureAtlas.canvas.getContext('2d');
            ctx.clearRect(0, 0, this.textureAtlas.canvas.width, this.textureAtlas.canvas.height);
            this.textureAtlas.canvas.width = 1;
            this.textureAtlas.canvas.height = 1;
            this.textureAtlas = null;
        }
        
        // Clear individual images if using atlas
        if (this.deviceCapabilities.isLowEnd) {
            // Keep only essential sprites in memory
            const essentialSprites = ['S01', 'S02', 'D01', 'D02', 'W1', 'TI1'];
            for (const key of Object.keys(this.loadedImages)) {
                if (!essentialSprites.includes(key)) {
                    delete this.loadedImages[key];
                }
            }
        }
        
        // Force garbage collection hint
        if (window.gc && this.deviceCapabilities.isLowEnd) {
            window.gc();
        }
    }

    async loadSprites() {
        const spritesToLoad = [
            // Buildings and units (keeping existing sprites)
            { path: '../public/assets/sprites/cnc-png/individual/construction-yard-0000.png', key: 'gdi-cy' },
            { path: '../public/assets/sprites/cnc-png/individual/barracks-0000.png', key: 'gdi-barracks' },
            { path: '../public/assets/sprites/cnc-png/individual/power-plant-0000.png', key: 'gdi-power' },
            { path: '../public/assets/sprites/cnc-png/individual/refinery-0000.png', key: 'gdi-refinery' },
            { path: '../public/assets/sprites/cnc-png/individual/hand-of-nod-0000.png', key: 'nod-hand' },
            { path: '../public/assets/sprites/cnc-png/individual/obelisk-0000.png', key: 'nod-obelisk' },
            { path: '../public/assets/sprites/cnc-png/individual/mammoth-tank-0000.png', key: 'mammoth' },
            { path: '../public/assets/sprites/cnc-png/individual/medium-tank-0000.png', key: 'medium-tank' },
            { path: '../public/assets/sprites/cnc-png/individual/recon-bike-0000.png', key: 'recon-bike' },
            { path: '../public/assets/sprites/cnc-png/individual/mammoth-tank-0008.png', key: 'mammoth-right' },
            { path: '../public/assets/sprites/cnc-png/individual/medium-tank-0016.png', key: 'medium-tank-down' },
            
            // Comprehensive terrain tile set for realistic battlefield
            // Sand terrain (S01-S08)
            { path: '../public/assets/sprites/cnc-png/terrain/S01-0000.png', key: 'S01' },
            { path: '../public/assets/sprites/cnc-png/terrain/S02-0000.png', key: 'S02' },
            { path: '../public/assets/sprites/cnc-png/terrain/S03-0000.png', key: 'S03' },
            { path: '../public/assets/sprites/cnc-png/terrain/S04-0000.png', key: 'S04' },
            { path: '../public/assets/sprites/cnc-png/terrain/S05-0000.png', key: 'S05' },
            { path: '../public/assets/sprites/cnc-png/terrain/S06-0000.png', key: 'S06' },
            { path: '../public/assets/sprites/cnc-png/terrain/S07-0000.png', key: 'S07' },
            { path: '../public/assets/sprites/cnc-png/terrain/S08-0000.png', key: 'S08' },
            
            // Dirt/rough terrain (D01-D08)
            { path: '../public/assets/sprites/cnc-png/terrain/D01-0000.png', key: 'D01' },
            { path: '../public/assets/sprites/cnc-png/terrain/D02-0000.png', key: 'D02' },
            { path: '../public/assets/sprites/cnc-png/terrain/D03-0000.png', key: 'D03' },
            { path: '../public/assets/sprites/cnc-png/terrain/D04-0000.png', key: 'D04' },
            { path: '../public/assets/sprites/cnc-png/terrain/D05-0000.png', key: 'D05' },
            { path: '../public/assets/sprites/cnc-png/terrain/D06-0000.png', key: 'D06' },
            { path: '../public/assets/sprites/cnc-png/terrain/D07-0000.png', key: 'D07' },
            { path: '../public/assets/sprites/cnc-png/terrain/D08-0000.png', key: 'D08' },
            
            // Water tiles
            { path: '../public/assets/sprites/cnc-png/terrain/W1-0000.png', key: 'W1' },
            { path: '../public/assets/sprites/cnc-png/terrain/W2-0000.png', key: 'W2' },
            
            // Shore transitions (SH1-SH6)
            { path: '../public/assets/sprites/cnc-png/terrain/SH1-0000.png', key: 'SH1' },
            { path: '../public/assets/sprites/cnc-png/terrain/SH2-0000.png', key: 'SH2' },
            { path: '../public/assets/sprites/cnc-png/terrain/SH3-0000.png', key: 'SH3' },
            { path: '../public/assets/sprites/cnc-png/terrain/SH4-0000.png', key: 'SH4' },
            { path: '../public/assets/sprites/cnc-png/terrain/SH5-0000.png', key: 'SH5' },
            { path: '../public/assets/sprites/cnc-png/terrain/SH6-0000.png', key: 'SH6' },
            
            // Tree variations (T01-T09)
            { path: '../public/assets/sprites/cnc-png/terrain/T01-0000.png', key: 'T01' },
            { path: '../public/assets/sprites/cnc-png/terrain/T02-0000.png', key: 'T02' },
            { path: '../public/assets/sprites/cnc-png/terrain/T03-0000.png', key: 'T03' },
            { path: '../public/assets/sprites/cnc-png/terrain/T05-0000.png', key: 'T05' },
            { path: '../public/assets/sprites/cnc-png/terrain/T06-0000.png', key: 'T06' },
            { path: '../public/assets/sprites/cnc-png/terrain/T07-0000.png', key: 'T07' },
            { path: '../public/assets/sprites/cnc-png/terrain/T08-0000.png', key: 'T08' },
            { path: '../public/assets/sprites/cnc-png/terrain/T09-0000.png', key: 'T09' },
            
            // Rock formations (ROCK1-ROCK7)
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK1-0000.png', key: 'ROCK1' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK2-0000.png', key: 'ROCK2' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK3-0000.png', key: 'ROCK3' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK4-0000.png', key: 'ROCK4' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK5-0000.png', key: 'ROCK5' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK6-0000.png', key: 'ROCK6' },
            { path: '../public/assets/sprites/cnc-png/terrain/ROCK7-0000.png', key: 'ROCK7' },
            
            // Tiberium resources
            { path: '../public/assets/sprites/cnc-png/terrain/TI1-0000.png', key: 'TI1' },
            { path: '../public/assets/sprites/cnc-png/terrain/TI2-0000.png', key: 'TI2' },
            { path: '../public/assets/sprites/cnc-png/terrain/TI3-0000.png', key: 'TI3' },
            { path: '../public/assets/sprites/cnc-png/terrain/TI10-0000.png', key: 'TI10' },
            { path: '../public/assets/sprites/cnc-png/terrain/TI11-0000.png', key: 'TI11' },
            { path: '../public/assets/sprites/cnc-png/terrain/TI12-0000.png', key: 'TI12' }
        ];

        const loadPromises = spritesToLoad.map(sprite => {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    this.loadedImages[sprite.key] = img;
                    resolve();
                };
                img.onerror = () => {
                    console.warn(`Failed to load sprite: ${sprite.path}, using placeholder`);
                    this.createPlaceholder(sprite.key);
                    resolve();
                };
                img.src = sprite.path;
            });
        });

        await Promise.all(loadPromises);
    }

    createPlaceholder(key) {
        const canvas = document.createElement('canvas');
        
        // Generate appropriate sprite based on key
        if (key.includes('mammoth') || key.includes('medium-tank')) {
            this.generateTankSprite(canvas, key);
        } else if (key.includes('barracks')) {
            this.generateBuildingSprite(canvas, 'barracks');
        } else if (key.includes('power')) {
            this.generateBuildingSprite(canvas, 'power');
        } else if (key.includes('refinery')) {
            this.generateBuildingSprite(canvas, 'refinery');
        } else if (key.includes('cy') || key.includes('yard')) {
            this.generateBuildingSprite(canvas, 'cy');
        } else if (key.includes('obelisk')) {
            this.generateObeliskSprite(canvas);
        } else if (key.includes('hand')) {
            this.generateBuildingSprite(canvas, 'hand');
        } else if (key.includes('bike')) {
            this.generateVehicleSprite(canvas, 'bike');
        } else if (key.includes('tiberium')) {
            this.generateTiberiumSprite(canvas, key.includes('blue'));
        } else {
            // Default placeholder
            canvas.width = 48;
            canvas.height = 48;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#333';
            ctx.fillRect(0, 0, 48, 48);
            ctx.fillStyle = '#666';
            ctx.fillRect(2, 2, 44, 44);
            ctx.fillStyle = '#fff';
            ctx.font = '10px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(key.substring(0, 6), 24, 28);
        }
        
        const img = new Image();
        img.src = canvas.toDataURL();
        this.loadedImages[key] = img;
    }
    
    generateTankSprite(canvas, key) {
        const ctx = canvas.getContext('2d');
        canvas.width = 32;
        canvas.height = 32;
        
        ctx.clearRect(0, 0, 32, 32);
        
        const isMammoth = key.includes('mammoth');
        const color = key.includes('nod') ? '#dc2626' : '#3b82f6';
        
        // Tank body
        ctx.fillStyle = color;
        ctx.fillRect(8, 10, isMammoth ? 18 : 16, isMammoth ? 14 : 12);
        
        // Tracks
        ctx.fillStyle = '#1a202c';
        ctx.fillRect(6, 9, isMammoth ? 22 : 20, 3);
        ctx.fillRect(6, isMammoth ? 22 : 20, isMammoth ? 22 : 20, 3);
        
        // Turret
        ctx.fillStyle = '#2d3748';
        ctx.beginPath();
        ctx.arc(16, 16, isMammoth ? 6 : 5, 0, Math.PI * 2);
        ctx.fill();
        
        // Cannon(s)
        ctx.strokeStyle = '#1a202c';
        ctx.lineWidth = isMammoth ? 4 : 3;
        ctx.beginPath();
        ctx.moveTo(16, 16);
        ctx.lineTo(16, 4);
        ctx.stroke();
        
        if (isMammoth) {
            // Second cannon for mammoth
            ctx.beginPath();
            ctx.moveTo(13, 16);
            ctx.lineTo(13, 5);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(19, 16);
            ctx.lineTo(19, 5);
            ctx.stroke();
        }
    }
    
    generateBuildingSprite(canvas, type) {
        const ctx = canvas.getContext('2d');
        canvas.width = 48;
        canvas.height = 48;
        
        ctx.clearRect(0, 0, 48, 48);
        
        // Building base
        ctx.fillStyle = type === 'hand' ? '#991b1b' : '#4a5568';
        ctx.fillRect(8, 16, 32, 28);
        
        // Roof
        ctx.fillStyle = type === 'hand' ? '#dc2626' : '#2d3748';
        ctx.beginPath();
        ctx.moveTo(4, 16);
        ctx.lineTo(24, 4);
        ctx.lineTo(44, 16);
        ctx.closePath();
        ctx.fill();
        
        // Details
        if (type === 'barracks' || type === 'hand') {
            // Door
            ctx.fillStyle = '#1a202c';
            ctx.fillRect(20, 28, 8, 16);
            // Windows
            ctx.fillStyle = '#fbbf24';
            ctx.fillRect(10, 20, 6, 6);
            ctx.fillRect(32, 20, 6, 6);
        } else if (type === 'power') {
            // Smokestacks
            ctx.fillStyle = '#1a202c';
            ctx.fillRect(12, 8, 6, 16);
            ctx.fillRect(30, 8, 6, 16);
            // Glow
            ctx.fillStyle = '#fbbf24';
            ctx.fillRect(19, 24, 10, 10);
        } else if (type === 'refinery') {
            // Silo
            ctx.fillStyle = '#6366f1';
            ctx.beginPath();
            ctx.arc(35, 28, 10, 0, Math.PI * 2);
            ctx.fill();
        } else if (type === 'cy') {
            // Construction Yard antenna
            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(24, 4);
            ctx.lineTo(24, 0);
            ctx.stroke();
            ctx.fillStyle = '#ef4444';
            ctx.beginPath();
            ctx.arc(24, 0, 2, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Team color stripe
        ctx.fillStyle = type === 'hand' ? '#ef4444' : '#3b82f6';
        ctx.fillRect(8, 40, 32, 3);
    }
    
    generateObeliskSprite(canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = 32;
        canvas.height = 48;
        
        ctx.clearRect(0, 0, 32, 48);
        
        // Base
        ctx.fillStyle = '#1a202c';
        ctx.fillRect(10, 36, 12, 12);
        
        // Obelisk
        ctx.fillStyle = '#4a5568';
        ctx.beginPath();
        ctx.moveTo(16, 4);
        ctx.lineTo(11, 36);
        ctx.lineTo(21, 36);
        ctx.closePath();
        ctx.fill();
        
        // Energy core
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(16, 8);
        ctx.lineTo(16, 28);
        ctx.stroke();
        
        // Crystal
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(16, 4, 4, 0, Math.PI * 2);
        ctx.fill();
    }
    
    generateVehicleSprite(canvas, type) {
        const ctx = canvas.getContext('2d');
        canvas.width = 24;
        canvas.height = 24;
        
        ctx.clearRect(0, 0, 24, 24);
        
        if (type === 'bike') {
            // Bike body
            ctx.fillStyle = '#dc2626';
            ctx.fillRect(8, 10, 8, 6);
            
            // Wheels
            ctx.fillStyle = '#1a202c';
            ctx.beginPath();
            ctx.arc(8, 12, 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(16, 12, 3, 0, Math.PI * 2);
            ctx.fill();
            
            // Driver
            ctx.fillStyle = '#fbbf24';
            ctx.beginPath();
            ctx.arc(12, 8, 2, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    
    generateTiberiumSprite(canvas, isBlue) {
        const ctx = canvas.getContext('2d');
        canvas.width = 24;
        canvas.height = 24;
        
        ctx.clearRect(0, 0, 24, 24);
        
        const color = isBlue ? '#3b82f6' : '#10b981';
        
        // Crystal clusters
        const crystals = [
            { x: 8, y: 12, size: 4 },
            { x: 14, y: 10, size: 5 },
            { x: 12, y: 16, size: 3 }
        ];
        
        crystals.forEach(crystal => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.moveTo(crystal.x, crystal.y - crystal.size);
            ctx.lineTo(crystal.x - crystal.size/2, crystal.y);
            ctx.lineTo(crystal.x, crystal.y + crystal.size/2);
            ctx.lineTo(crystal.x + crystal.size/2, crystal.y);
            ctx.closePath();
            ctx.fill();
            
            // Glow
            ctx.fillStyle = color + '44';
            ctx.beginPath();
            ctx.arc(crystal.x, crystal.y, crystal.size * 1.5, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    drawTerrain() {
        // Use the professionally generated terrain map
        if (!this.terrainMap) {
            this.generateTerrainMap();
        }
        
        // Draw the base terrain layer
        for (let y = 0; y < this.mapHeight; y++) {
            for (let x = 0; x < this.mapWidth; x++) {
                const terrainTileKey = this.terrainMap[y][x];
                const tile = this.loadedImages[terrainTileKey];
                
                if (tile) {
                    // Use texture atlas if available for better performance
                    if (this.textureAtlas && this.textureAtlas.map.has(terrainTileKey)) {
                        this.drawSpriteAtlas(terrainTileKey, x * this.tileSize + this.tileSize/2, y * this.tileSize + this.tileSize/2, 1);
                    } else {
                        this.ctx.drawImage(tile, x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);
                    }
                } else {
                    // Intelligent fallback based on terrain type
                    let fallbackTile = null;
                    
                    if (terrainTileKey.startsWith('S')) {
                        // Sand fallback
                        fallbackTile = this.loadedImages['S01'] || this.loadedImages['S02'] || this.loadedImages['S03'];
                    } else if (terrainTileKey.startsWith('D')) {
                        // Dirt fallback
                        fallbackTile = this.loadedImages['D01'] || this.loadedImages['D02'] || this.loadedImages['D03'];
                    } else if (terrainTileKey.startsWith('W')) {
                        // Water fallback
                        fallbackTile = this.loadedImages['W1'] || this.loadedImages['W2'];
                    } else if (terrainTileKey.startsWith('SH')) {
                        // Shore fallback
                        fallbackTile = this.loadedImages['SH1'] || this.loadedImages['SH2'];
                    } else if (terrainTileKey.startsWith('T')) {
                        // Tree fallback
                        fallbackTile = this.loadedImages['T01'] || this.loadedImages['T02'];
                    } else if (terrainTileKey.startsWith('ROCK')) {
                        // Rock fallback
                        fallbackTile = this.loadedImages['ROCK1'] || this.loadedImages['ROCK2'];
                    }
                    
                    if (fallbackTile) {
                        this.ctx.drawImage(fallbackTile, x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);
                    } else {
                        // Ultimate fallback with terrain-appropriate colors
                        let fallbackColor = '#c4a57b'; // Default sand color
                        
                        if (terrainTileKey.startsWith('D')) fallbackColor = '#8b6f47';
                        else if (terrainTileKey.startsWith('W')) fallbackColor = '#4682b4';
                        else if (terrainTileKey.startsWith('SH')) fallbackColor = '#daa520';
                        else if (terrainTileKey.startsWith('T')) fallbackColor = '#228b22';
                        else if (terrainTileKey.startsWith('ROCK')) fallbackColor = '#696969';
                        
                        this.ctx.fillStyle = fallbackColor;
                        this.ctx.fillRect(x * this.tileSize, y * this.tileSize, this.tileSize, this.tileSize);
                    }
                }
            }
        }
        
        // Draw tiberium overlays using the generated fields
        if (this.tiberiumFields && this.tiberiumFields.length > 0) {
            this.tiberiumFields.forEach((field, fieldIndex) => {
                field.forEach(tiberiumTile => {
                    const tx = tiberiumTile.x * this.tileSize;
                    const ty = tiberiumTile.y * this.tileSize;
                    
                    // Choose tiberium sprite based on type
                    let tiberiumSprite = null;
                    if (tiberiumTile.type === 'blue') {
                        tiberiumSprite = this.loadedImages['TI10'] || this.loadedImages['TI11'] || this.loadedImages['TI12'];
                    } else {
                        // Default to green tiberium
                        tiberiumSprite = this.loadedImages['TI1'] || this.loadedImages['TI2'] || this.loadedImages['TI3'];
                    }
                    
                    if (tiberiumSprite) {
                        // Apply density-based alpha for realistic deposits
                        const originalAlpha = this.ctx.globalAlpha;
                        this.ctx.globalAlpha = Math.max(0.6, tiberiumTile.density || 0.8);
                        this.ctx.drawImage(tiberiumSprite, tx, ty, this.tileSize, this.tileSize);
                        this.ctx.globalAlpha = originalAlpha;
                    }
                });
            });
        }
    }

    drawSprite(spriteKey, x, y, scale = 1, frame = 0) {
        const img = this.loadedImages[spriteKey];
        if (img) {
            // We're now using individual PNG files, not sprite sheets
            // So we can draw the entire image directly
            const width = img.width * scale;
            const height = img.height * scale;
            
            // Center the sprite at the given position
            const drawX = x - width / 2;
            const drawY = y - height / 2;
            
            this.ctx.drawImage(img, drawX, drawY, width, height);
        }
    }

    drawText(text, x, y, options = {}) {
        const {
            fontSize = 14,
            color = '#FFD700',
            backgroundColor = 'rgba(0,0,0,0.8)',
            padding = 5,
            bold = true,
            maxWidth = 300
        } = options;

        this.ctx.font = `${bold ? 'bold ' : ''}${fontSize}px Arial`;
        this.ctx.textBaseline = 'top';
        
        const lines = this.wrapText(text, maxWidth);
        const lineHeight = fontSize + 4;
        const totalHeight = lines.length * lineHeight + padding * 2;
        
        let maxLineWidth = 0;
        lines.forEach(line => {
            const metrics = this.ctx.measureText(line);
            if (metrics.width > maxLineWidth) {
                maxLineWidth = metrics.width;
            }
        });
        
        this.ctx.fillStyle = backgroundColor;
        this.ctx.fillRect(x - padding, y - padding, maxLineWidth + padding * 2, totalHeight);
        
        this.ctx.fillStyle = color;
        lines.forEach((line, index) => {
            this.ctx.fillText(line, x, y + index * lineHeight);
        });
    }

    wrapText(text, maxWidth) {
        const words = text.split(' ');
        const lines = [];
        let currentLine = '';
        
        words.forEach(word => {
            const testLine = currentLine + (currentLine ? ' ' : '') + word;
            const metrics = this.ctx.measureText(testLine);
            
            if (metrics.width > maxWidth && currentLine) {
                lines.push(currentLine);
                currentLine = word;
            } else {
                currentLine = testLine;
            }
        });
        
        if (currentLine) {
            lines.push(currentLine);
        }
        
        return lines;
    }

    drawArrow(fromX, fromY, toX, toY, color = '#00FF00', label = '') {
        const headLength = 10;
        const angle = Math.atan2(toY - fromY, toX - fromX);
        
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(fromX, fromY);
        this.ctx.lineTo(toX, toY);
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(toX, toY);
        this.ctx.lineTo(toX - headLength * Math.cos(angle - Math.PI / 6), toY - headLength * Math.sin(angle - Math.PI / 6));
        this.ctx.moveTo(toX, toY);
        this.ctx.lineTo(toX - headLength * Math.cos(angle + Math.PI / 6), toY - headLength * Math.sin(angle + Math.PI / 6));
        this.ctx.stroke();
        
        if (label) {
            const midX = (fromX + toX) / 2;
            const midY = (fromY + toY) / 2;
            this.drawText(label, midX - 20, midY - 20, { fontSize: 12, backgroundColor: 'rgba(0,0,0,0.9)' });
        }
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

export default MapGenerator;