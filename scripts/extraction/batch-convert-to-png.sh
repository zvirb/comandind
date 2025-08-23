#!/bin/bash

# Batch convert all SHP files to PNG using OpenRA

OPENRA_UTIL="/snap/openra/1415/usr/lib/openra/OpenRA.Utility"
SHP_DIR="public/assets/sprites/cnc-shp-files"
PNG_DIR="public/assets/sprites/cnc-png"
PALETTE="$SHP_DIR/temperat.pal"

echo "=== Batch SHP to PNG Conversion ==="
echo "Using OpenRA.Utility to convert sprites..."

# Create output directories
mkdir -p "$PNG_DIR"/{units/gdi,units/nod,structures/gdi,structures/nod,infantry}

# Function to convert a single SHP file
convert_shp() {
    local shp_file=$1
    local output_dir=$2
    local basename=$(basename "$shp_file" .shp)
    
    echo "Converting: $basename"
    cd "$output_dir"
    $OPENRA_UTIL cnc --png "../../$shp_file" "../../$PALETTE" 2>&1 | grep -o "Saved.*" || echo "  ✗ Failed"
    cd - > /dev/null
}

# Convert units
echo -e "\nConverting GDI units..."
for shp in "$SHP_DIR"/units/gdi/*.shp; do
    [ -f "$shp" ] && convert_shp "$shp" "$PNG_DIR/units/gdi"
done

echo -e "\nConverting NOD units..."
for shp in "$SHP_DIR"/units/nod/*.shp; do
    [ -f "$shp" ] && convert_shp "$shp" "$PNG_DIR/units/nod"
done

# Convert structures
echo -e "\nConverting GDI structures..."
for shp in "$SHP_DIR"/structures/gdi/*.shp; do
    [ -f "$shp" ] && convert_shp "$shp" "$PNG_DIR/structures/gdi"
done

echo -e "\nConverting NOD structures..."
for shp in "$SHP_DIR"/structures/nod/*.shp; do
    [ -f "$shp" ] && convert_shp "$shp" "$PNG_DIR/structures/nod"
done

# Convert infantry
echo -e "\nConverting infantry..."
for shp in "$SHP_DIR"/infantry/*.shp; do
    [ -f "$shp" ] && convert_shp "$shp" "$PNG_DIR/infantry"
done

echo -e "\n=== Conversion Complete ==="
echo "PNG files saved to: $PNG_DIR"
echo "Each sprite has been split into individual frames"

# Count total PNGs created
total_pngs=$(find "$PNG_DIR" -name "*.png" | wc -l)
echo "Total PNG files created: $total_pngs"