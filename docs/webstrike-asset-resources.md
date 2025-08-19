# WebStrike Command - Asset Resources & Management

## Legal Foundation
- **EA released C&C Tiberian Dawn as freeware in 2007**
- Available on Archive.org for legal download
- OpenRA project provides automatic asset downloading
- Respects EA's intellectual property rights

## Primary Asset Sources

### The Spriters Resource
**URL:** spriters-resource.com/pc_computer/commandconquertiberiandawn/
- Complete sprite archives including 20 structures and 14 units
- Organized by faction (GDI, NOD, Civilian)
- Multiple animation frames for units and buildings
- Terrain sprites and Tiberium graphics
- Pre-extracted and ready for use

### Original Game Files
**Source:** Archive.org C&C Freeware Release
- MIX archive files containing original assets
- Requires extraction tools for processing
- Authentic game data with original specifications
- Complete audio and configuration files

## Asset Extraction Tools

### XCC Mixer
**URL:** xhp.xwis.net/utilities/
- **Primary extraction tool** for C&C modding
- Extract sprites (SHP format) from MIX archives
- Extract audio (AUD format) with XCC AUD Writer
- Extract configuration (INI) files
- Batch conversion and processing capabilities
- Supports all C&C game formats

### Extraction Workflow
```bash
# Extract sprites from MIX files
xcc_mixer.exe extract -f *.shp tiberian.mix sprites/
xcc_mixer.exe extract -f *.aud sounds.mix audio/
xcc_mixer.exe extract -f *.ini rules.mix data/
```

## High-Resolution Options

### OpenRA Tiberian Dawn HD
**GitHub:** OpenRA/TiberianDawnHD
- Uses C&C Remastered Collection assets
- **Requires owning the remastered version**
- Higher quality textures and animations
- Modern sprite formats (PNG with alpha)
- Professionally remastered by EA

### xBRZ Algorithm Upscaling
**URL:** sourceforge.net/projects/xbrz/
- 2x to 6x integer scaling capability
- Preserves sharp edges and pixel art aesthetics
- Excellent results for retro sprite upscaling
- Open source implementation available
- Maintains sprite authenticity while improving clarity

```javascript
// Example xBRZ integration
class SpriteUpscaler {
  constructor(scaleFactor = 2) {
    this.scaleFactor = scaleFactor;
  }
  
  upscaleSprite(originalSprite) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = originalSprite.width * this.scaleFactor;
    canvas.height = originalSprite.height * this.scaleFactor;
    
    // Apply xBRZ algorithm (simplified example)
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(originalSprite, 0, 0, canvas.width, canvas.height);
    
    return canvas;
  }
}
```

## Audio Resources

### Frank Klepacki Original Soundtrack
**Source:** Archive.org
- Available in FLAC/OGG/MP3 formats
- Complete collection: 619.8MB
- **Iconic tracks included:**
  - 'Act on Instinct' (GDI Theme)
  - 'Hell March' (NOD Theme)
  - 'Industrial' (Action Music)
  - 'Target' (Combat Music)
- Ambient and action music variants
- High-quality recordings from original masters

### Sound Effects Extraction
- **XCC AUD Writer** for sound extraction
- Unit voice commands and responses
- Weapon firing and explosion sounds
- Environmental and UI sounds
- Original game audio quality preserved

```javascript
// Audio management system
class AudioManager {
  constructor() {
    this.music = new Map();
    this.sfx = new Map();
    this.voices = new Map();
  }
  
  loadAudioPack(packName, audioFiles) {
    audioFiles.forEach(file => {
      const audio = new Audio(file.path);
      audio.preload = 'metadata';
      
      switch(file.type) {
        case 'music':
          this.music.set(file.name, audio);
          break;
        case 'sfx':
          this.sfx.set(file.name, audio);
          break;
        case 'voice':
          this.voices.set(file.name, audio);
          break;
      }
    });
  }
}
```

## Asset Organization Structure

```
assets/
├── sprites/
│   ├── units/
│   │   ├── gdi/
│   │   │   ├── medium_tank/
│   │   │   │   ├── idle_00.png
│   │   │   │   ├── move_00.png
│   │   │   │   └── attack_00.png
│   │   │   └── mammoth_tank/
│   │   └── nod/
│   │       ├── light_tank/
│   │       └── stealth_tank/
│   ├── buildings/
│   │   ├── gdi/
│   │   │   ├── construction_yard/
│   │   │   ├── power_plant/
│   │   │   └── barracks/
│   │   └── nod/
│   │       ├── hand_of_nod/
│   │       ├── power_plant/
│   │       └── airstrip/
│   ├── terrain/
│   │   ├── desert/
│   │   ├── temperate/
│   │   └── winter/
│   └── effects/
│       ├── explosions/
│       ├── muzzle_flashes/
│       └── projectiles/
├── audio/
│   ├── music/
│   │   ├── act_on_instinct.ogg
│   │   ├── hell_march.ogg
│   │   └── industrial.ogg
│   ├── sfx/
│   │   ├── weapons/
│   │   ├── explosions/
│   │   └── ui/
│   └── voices/
│       ├── gdi/
│       └── nod/
├── textures/
│   ├── atlas_units.png
│   ├── atlas_units.json
│   ├── atlas_buildings.png
│   ├── atlas_buildings.json
│   ├── atlas_terrain.png
│   └── atlas_terrain.json
└── data/
    ├── units.json
    ├── buildings.json
    ├── weapons.json
    └── balance.json
```

## Texture Atlas Creation

### Atlas Generation Tools
- **TexturePacker:** Professional atlas creation
- **Shoebox:** Free alternative with batch processing
- **Custom scripts:** Automated pipeline integration

### Atlas Configuration
```json
{
  "medium_tank_idle": {
    "frame": {"x": 0, "y": 0, "w": 32, "h": 32},
    "rotated": false,
    "trimmed": false,
    "spriteSourceSize": {"x": 0, "y": 0, "w": 32, "h": 32},
    "sourceSize": {"w": 32, "h": 32}
  },
  "medium_tank_move_01": {
    "frame": {"x": 32, "y": 0, "w": 32, "h": 32},
    "rotated": false,
    "trimmed": false,
    "spriteSourceSize": {"x": 0, "y": 0, "w": 32, "h": 32},
    "sourceSize": {"w": 32, "h": 32}
  }
}
```

### Performance Benefits
- Combine multiple sprites into single textures
- Reduce draw calls and improve GPU performance
- Support for different zoom levels and LOD
- Efficient memory usage

## Compression and Optimization

### Image Formats
- **PNG:** Sprites with transparency (units, buildings)
- **JPEG:** Non-transparent backgrounds (terrain)
- **WebP:** Modern browsers with better compression
- **Progressive loading:** Large assets loaded incrementally

### Compression Pipeline
```javascript
class AssetCompressionPipeline {
  constructor() {
    this.compressionTargets = {
      sprites: {format: 'png', quality: 90},
      terrain: {format: 'webp', quality: 85},
      ui: {format: 'png', quality: 95}
    };
  }
  
  async processAssets(assetList) {
    const processed = [];
    
    for (let asset of assetList) {
      const config = this.compressionTargets[asset.type];
      const compressed = await this.compressAsset(asset, config);
      processed.push(compressed);
    }
    
    return processed;
  }
}
```

## Asset Loading Strategy

### Lazy Loading System
```javascript
class AssetLoader {
  constructor() {
    this.cache = new Map();
    this.loading = new Map();
    this.preloadQueue = [];
  }
  
  async loadAsset(path) {
    if (this.cache.has(path)) {
      return this.cache.get(path);
    }
    
    if (this.loading.has(path)) {
      return this.loading.get(path);
    }
    
    const loadPromise = this.fetchAsset(path);
    this.loading.set(path, loadPromise);
    
    try {
      const asset = await loadPromise;
      this.cache.set(path, asset);
      this.loading.delete(path);
      return asset;
    } catch (error) {
      this.loading.delete(path);
      throw error;
    }
  }
  
  preloadAssets(paths) {
    paths.forEach(path => {
      if (!this.cache.has(path) && !this.loading.has(path)) {
        this.preloadQueue.push(path);
      }
    });
    
    this.processPreloadQueue();
  }
}
```

## Modding Community Resources

### Community Sites
- **CnC-Comm (cnc-comm.com):** Active modding community
- **ModDB Command & Conquer section:** Asset sharing
- **PPM (Project Perfect Mod) forums:** Technical discussions
- **XWW Forums:** Advanced modding techniques

### Asset Sharing Guidelines
- Respect original EA intellectual property
- Credit asset creators and sources
- Follow community quality standards
- Maintain sprite consistency and style

## Legal Considerations

### Usage Rights
- **Freeware assets:** Available for non-commercial use
- **Community created:** Check individual licenses
- **Remastered assets:** Require ownership of remaster
- **Fair use:** Educational and non-profit projects

### Best Practices
- Always credit original creators
- Maintain asset integrity and quality
- Follow community guidelines
- Respect intellectual property rights

## Quality Standards

### Sprite Requirements
- **Consistent color palette** matching original game
- **Proper animation timing** (125ms per frame typical)
- **Correct sprite dimensions** (32x32 for units, varies for buildings)
- **Clean transparency** with proper alpha channels

### Audio Standards
- **44.1kHz sample rate** for compatibility
- **OGG format** for web deployment
- **Normalized volume levels** across all assets
- **Looping markers** for music tracks