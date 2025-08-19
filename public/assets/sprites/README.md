# Command & Conquer: Tiberian Dawn Assets

## Legal Notice
These assets are from the freeware release of Command & Conquer: Tiberian Dawn,
which EA released in 2007. They are legally available for use.

## Asset Sources

### Official Sources
1. **OpenRA** - Automatically downloads freeware assets
   - Website: https://www.openra.net/
   - Assets location: ~/.openra/Content/cnc/

2. **The Spriters Resource** - Manual sprite downloads
   - URL: https://www.spriters-resource.com/pc_computer/commandconquertiberiandawn/

3. **EA GitHub** - Original source code
   - Repository: https://github.com/electronicarts/CnC_Remastered_Collection

## Directory Structure

```
sprites/
├── structures/
│   ├── gdi/       # GDI buildings
│   └── nod/       # NOD buildings
├── units/
│   ├── gdi/       # GDI vehicles and aircraft
│   ├── nod/       # NOD vehicles and aircraft
│   └── neutral/   # Civilian units
├── terrain/       # Map tiles and terrain
├── effects/       # Explosions, projectiles
├── ui/           # Interface elements
└── resources/    # Tiberium and other resources
```

## Sprite Sheet Format

Most sprite sheets contain multiple frames for animations:
- Buildings: Usually contain idle, active, and damaged states
- Units: Contain 32 directional frames for rotation
- Effects: Contain animation sequences

## Usage in Game

See `TextureAtlasManager.js` for loading and using these sprites in the game.
