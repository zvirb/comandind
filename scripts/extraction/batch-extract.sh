#!/bin/bash

# Batch extract key C&C sprites
# This script extracts and organizes the SHP files for manual conversion

EXTRACT_DIR="/tmp/cnc-extracted"
OUTPUT_DIR="public/assets/sprites/cnc-shp-files"

echo "=== C&C Sprite Batch Extraction ==="
echo "Organizing SHP files for conversion..."

mkdir -p "$OUTPUT_DIR"/{units/gdi,units/nod,structures/gdi,structures/nod,infantry}

# Copy key unit sprites
echo "Processing units..."
cp "$EXTRACT_DIR/conquer/MTNK.SHP" "$OUTPUT_DIR/units/gdi/medium-tank.shp" 2>/dev/null && echo "  ✓ Medium Tank"
cp "$EXTRACT_DIR/conquer/HTNK.SHP" "$OUTPUT_DIR/units/gdi/mammoth-tank.shp" 2>/dev/null && echo "  ✓ Mammoth Tank"
cp "$EXTRACT_DIR/conquer/JEEP.SHP" "$OUTPUT_DIR/units/gdi/humvee.shp" 2>/dev/null && echo "  ✓ Humvee"
cp "$EXTRACT_DIR/conquer/APC.SHP" "$OUTPUT_DIR/units/gdi/apc.shp" 2>/dev/null && echo "  ✓ APC"
cp "$EXTRACT_DIR/conquer/ARTY.SHP" "$OUTPUT_DIR/units/gdi/artillery.shp" 2>/dev/null && echo "  ✓ Artillery"
cp "$EXTRACT_DIR/conquer/MLRS.SHP" "$OUTPUT_DIR/units/gdi/mlrs.shp" 2>/dev/null && echo "  ✓ MLRS"

cp "$EXTRACT_DIR/conquer/LTNK.SHP" "$OUTPUT_DIR/units/nod/light-tank.shp" 2>/dev/null && echo "  ✓ Light Tank"
cp "$EXTRACT_DIR/conquer/BIKE.SHP" "$OUTPUT_DIR/units/nod/recon-bike.shp" 2>/dev/null && echo "  ✓ Recon Bike"
cp "$EXTRACT_DIR/conquer/BGGY.SHP" "$OUTPUT_DIR/units/nod/buggy.shp" 2>/dev/null && echo "  ✓ Buggy"
cp "$EXTRACT_DIR/conquer/FTNK.SHP" "$OUTPUT_DIR/units/nod/flame-tank.shp" 2>/dev/null && echo "  ✓ Flame Tank"
cp "$EXTRACT_DIR/conquer/STNK.SHP" "$OUTPUT_DIR/units/nod/stealth-tank.shp" 2>/dev/null && echo "  ✓ Stealth Tank"

# Copy building sprites
echo "Processing structures..."
cp "$EXTRACT_DIR/conquer/FACT.SHP" "$OUTPUT_DIR/structures/gdi/construction-yard.shp" 2>/dev/null && echo "  ✓ Construction Yard"
cp "$EXTRACT_DIR/conquer/PYLE.SHP" "$OUTPUT_DIR/structures/gdi/barracks.shp" 2>/dev/null && echo "  ✓ Barracks"
cp "$EXTRACT_DIR/conquer/NUKE.SHP" "$OUTPUT_DIR/structures/gdi/power-plant.shp" 2>/dev/null && echo "  ✓ Power Plant"
cp "$EXTRACT_DIR/conquer/PROC.SHP" "$OUTPUT_DIR/structures/gdi/refinery.shp" 2>/dev/null && echo "  ✓ Refinery"
cp "$EXTRACT_DIR/conquer/WEAP.SHP" "$OUTPUT_DIR/structures/gdi/war-factory.shp" 2>/dev/null && echo "  ✓ War Factory"

cp "$EXTRACT_DIR/conquer/HAND.SHP" "$OUTPUT_DIR/structures/nod/hand-of-nod.shp" 2>/dev/null && echo "  ✓ Hand of NOD"
cp "$EXTRACT_DIR/conquer/OBLI.SHP" "$OUTPUT_DIR/structures/nod/obelisk.shp" 2>/dev/null && echo "  ✓ Obelisk"
cp "$EXTRACT_DIR/conquer/TMPL.SHP" "$OUTPUT_DIR/structures/nod/temple.shp" 2>/dev/null && echo "  ✓ Temple of NOD"
cp "$EXTRACT_DIR/conquer/AFLD.SHP" "$OUTPUT_DIR/structures/nod/airfield.shp" 2>/dev/null && echo "  ✓ Airfield"

# Copy infantry sprites
echo "Processing infantry..."
cp "$EXTRACT_DIR/conquer/E1.SHP" "$OUTPUT_DIR/infantry/minigunner.shp" 2>/dev/null && echo "  ✓ Minigunner"
cp "$EXTRACT_DIR/conquer/E2.SHP" "$OUTPUT_DIR/infantry/grenadier.shp" 2>/dev/null && echo "  ✓ Grenadier"
cp "$EXTRACT_DIR/conquer/E3.SHP" "$OUTPUT_DIR/infantry/rocket-soldier.shp" 2>/dev/null && echo "  ✓ Rocket Soldier"
cp "$EXTRACT_DIR/conquer/E4.SHP" "$OUTPUT_DIR/infantry/flamethrower.shp" 2>/dev/null && echo "  ✓ Flamethrower"
cp "$EXTRACT_DIR/conquer/E5.SHP" "$OUTPUT_DIR/infantry/chem-warrior.shp" 2>/dev/null && echo "  ✓ Chem Warrior"

# Copy palette
cp "$EXTRACT_DIR/temperat/TEMPERAT.PAL" "$OUTPUT_DIR/temperat.pal" 2>/dev/null && echo "  ✓ Palette"

echo ""
echo "=== Extraction Complete ==="
echo "SHP files copied to: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Use OpenRA.Utility to convert SHP to PNG:"
echo "   OpenRA.Utility ra --png file.shp temperat.pal"
echo ""
echo "2. Or use XCC Mixer on Windows"
echo ""
echo "3. Or use an online converter if available"
echo ""
echo "The SHP files are the actual game sprites in their original format."