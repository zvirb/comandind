# Command & Conquer Sprite Extraction Guide

## Current Status
The sprites in this project are currently placeholder/generated sprites, not the actual C&C graphics. To get real sprites, you need to extract them from the original game files.

## Tools Required

### Option 1: ccmixar + OpenRA (Recommended)
1. **Install ccmixar** - Modern MIX file extractor
   ```bash
   go install github.com/askeladdk/ccmixar@latest
   ```
   Or download from: https://github.com/askeladdk/ccmixar

2. **Install OpenRA** - For SHP to PNG conversion
   - Download from: https://www.openra.net/download/
   - Or build from source: https://github.com/OpenRA/OpenRA

### Option 2: XCC Mixer (Windows)
- Download XCC Utilities: http://xhp.xwis.net/
- GUI tool that can extract MIX files and convert SHP to PNG

### Option 3: Online Tools
- CNCNet provides some extracted sprites: https://cncnet.org/
- OpenRA's GitHub has some sprites in their mods folder

## Extraction Process

### Step 1: Extract MIX Files
```bash
# Extract conquer.mix (contains units and buildings)
ccmixar unpack -game cc1 -mix conquer.mix -dir output/

# Extract temperat.mix (contains palette files)
ccmixar unpack -game cc1 -mix temperat.mix -dir output/
```

### Step 2: Convert SHP to PNG
```bash
# Using OpenRA.Utility
OpenRA.Utility ra --png mtnk.shp temperat.pal

# This creates mtnk.png with all frames
```

### Step 3: Split Sprite Sheets
Most C&C sprites are multi-frame animations in a single row:
- Vehicles: 32 or 64 frames (rotations + turret positions)
- Buildings: 2-16 frames (construction/damage states)
- Infantry: 40+ frames (walk/fire animations)

## Key Sprite Files

### Units (in conquer.mix)
- **mtnk.shp** - Medium Tank (GDI)
- **htnk.shp** - Heavy/Mammoth Tank (GDI)
- **ltnk.shp** - Light Tank (NOD)
- **bike.shp** - Recon Bike (NOD)
- **jeep.shp** - Humvee (GDI)
- **bggy.shp** - Buggy (NOD)

### Buildings (in conquer.mix)
- **fact.shp** - Construction Yard
- **pyle.shp** - Barracks (GDI)
- **hand.shp** - Hand of NOD
- **nuke.shp** - Power Plant (GDI)
- **proc.shp** - Refinery
- **obli.shp** - Obelisk of Light (NOD)

### Infantry (in conquer.mix)
- **e1.shp** - Minigunner
- **e2.shp** - Grenadier
- **e3.shp** - Rocket Soldier
- **e4.shp** - Flamethrower
- **e5.shp** - Chem Warrior
- **rmbo.shp** - Commando

## Palette Files
C&C uses 256-color palettes. The main ones are:
- **temperat.pal** - Temperate theater palette
- **desert.pal** - Desert theater palette
- **winter.pal** - Winter theater palette

## Quick Solution: Use Pre-Extracted Sprites

### From OpenRA
```bash
# Clone OpenRA (they have some converted sprites)
git clone --depth 1 https://github.com/OpenRA/OpenRA.git
cd OpenRA/mods/cnc/bits/
# Note: Most are still in SHP format
```

### From CNCNet
Some community members have shared extracted sprites:
- https://forums.cncnet.org/
- Search for "sprite pack" or "graphics pack"

## JavaScript/Web Usage

Once you have PNG sprites, you can use them in web projects:

```javascript
// For sprite sheets (multiple frames in one image)
const spriteSheet = new Image();
spriteSheet.src = 'mammoth-tank.png';

// Extract single frame (assuming 32x32 frames)
function drawFrame(ctx, frameNumber, x, y) {
    const frameWidth = 32;
    const frameHeight = 32;
    const srcX = frameNumber * frameWidth;
    const srcY = 0;
    
    ctx.drawImage(
        spriteSheet,
        srcX, srcY, frameWidth, frameHeight,  // Source
        x, y, frameWidth, frameHeight          // Destination
    );
}
```

## Legal Note
Command & Conquer graphics are copyrighted by Electronic Arts. Extract sprites only from games you own for personal/educational use.

## Alternative: Generated Sprites
If you can't extract real sprites, the project includes generated placeholder sprites that maintain the C&C visual style:
- Blue for GDI units/buildings
- Red for NOD units/buildings
- Distinctive shapes for each unit type

## Scripts Available

1. **extract-sprites-proper.js** - Full extraction pipeline using ccmixar
2. **download-openra-sprites.js** - Attempts to download from OpenRA
3. **SpriteGenerator.js** - Creates C&C-style placeholder sprites

## Troubleshooting

### "MIX file not found"
- Ensure you have the original C&C game files
- Check file paths in the extraction scripts

### "SHP conversion failed"
- Install OpenRA.Utility or XCC Mixer
- Ensure you have the correct palette file

### "Sprites look wrong/corrupted"
- Wrong palette file (use temperat.pal for most sprites)
- Incorrect frame dimensions
- File might be compressed (some MIX files use compression)

## Contributing
If you successfully extract the sprites, consider:
1. Creating a sprite pack for others
2. Documenting your extraction process
3. Contributing to OpenRA or similar projects