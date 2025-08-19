# C&C Asset Extraction Guide

## MIX Files Overview

The following MIX archives contain all C&C assets:

- **conquer.mix**: Units, buildings, sprites
- **general.mix**: UI elements, cursors, fonts
- **desert.mix**: Desert terrain tiles
- **temperat.mix**: Temperate terrain tiles
- **winter.mix**: Winter terrain tiles
- **sounds.mix**: Sound effects
- **speech.mix**: Voice samples
- **transit.mix**: Transition screens

## Extraction Methods

### Method 1: OpenRA Utilities (Recommended)
OpenRA includes built-in utilities to extract MIX files:

```bash
# Use OpenRA's utility (if available)
openra --extract-content conquer.mix output_directory/
```

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
