#!/bin/bash

# OpenRA Asset Extraction Script for Command and Independent Thought
# Downloads and extracts C&C Tiberian Dawn freeware assets

echo "================================================"
echo "OpenRA C&C Asset Extraction Setup"
echo "================================================"
echo ""

# Create tools directory
mkdir -p tools
cd tools

# Download OpenRA portable version
echo "Downloading OpenRA portable version..."
echo "This may take a few minutes..."

OPENRA_URL="https://github.com/OpenRA/OpenRA/releases/download/release-20231010/OpenRA-release-20231010-portable-linux.tar.bz2"
OPENRA_FILE="OpenRA-portable.tar.bz2"

# Try wget first, fallback to curl
if command -v wget &> /dev/null; then
    wget -O "$OPENRA_FILE" "$OPENRA_URL"
elif command -v curl &> /dev/null; then
    curl -L -o "$OPENRA_FILE" "$OPENRA_URL"
else
    echo "Error: Neither wget nor curl is available. Please install one of them."
    exit 1
fi

# Check if download was successful
if [ ! -f "$OPENRA_FILE" ]; then
    echo "Error: Failed to download OpenRA"
    exit 1
fi

echo "Download complete!"
echo ""

# Extract OpenRA
echo "Extracting OpenRA..."
tar -xjf "$OPENRA_FILE"

# Find the extracted directory
OPENRA_DIR=$(find . -maxdepth 1 -type d -name "OpenRA*" | head -1)

if [ -z "$OPENRA_DIR" ]; then
    echo "Error: Could not find extracted OpenRA directory"
    exit 1
fi

echo "OpenRA extracted to: $OPENRA_DIR"
echo ""

# Create asset extraction directory
ASSET_DIR="../public/assets/cnc-original"
mkdir -p "$ASSET_DIR"

echo "================================================"
echo "Manual Asset Extraction Instructions"
echo "================================================"
echo ""
echo "OpenRA has been downloaded but requires running to download assets."
echo ""
echo "To get the C&C assets:"
echo ""
echo "1. Run OpenRA Tiberian Dawn:"
echo "   cd tools/$OPENRA_DIR"
echo "   ./launch-game.sh --game=cnc"
echo ""
echo "2. OpenRA will automatically download the freeware assets"
echo "   Assets will be stored in: ~/.openra/Content/cnc/"
echo ""
echo "3. Copy the assets to your project:"
echo "   cp -r ~/.openra/Content/cnc/* $ASSET_DIR/"
echo ""
echo "================================================"
echo "Alternative: Direct Asset Download"
echo "================================================"
echo ""
echo "You can also download pre-extracted assets from:"
echo "- https://github.com/OpenRA/OpenRAContent (community extracts)"
echo "- Original freeware ISO from Archive.org"
echo ""

# Create a Python script to extract SHP files if they're available
cat > extract_shp.py << 'EOF'
#!/usr/bin/env python3
"""
SHP to PNG converter for C&C sprites
Converts Westwood SHP format to PNG for use in web games
"""

import os
import sys
from PIL import Image
import struct

def read_shp_header(file):
    """Read SHP file header"""
    # SHP format: 2 bytes count, 6 bytes unknown
    count = struct.unpack('<H', file.read(2))[0]
    file.read(6)  # Skip unknown bytes
    return count

def extract_shp_frames(shp_path, output_dir):
    """Extract all frames from a SHP file"""
    try:
        with open(shp_path, 'rb') as f:
            frame_count = read_shp_header(f)
            print(f"Found {frame_count} frames in {os.path.basename(shp_path)}")
            
            # Note: Full SHP extraction would require palette data
            # This is a placeholder for the structure
            
    except Exception as e:
        print(f"Error extracting {shp_path}: {e}")

if __name__ == "__main__":
    print("SHP Extractor - Placeholder")
    print("Use OpenRA's built-in tools for actual extraction")
EOF

chmod +x extract_shp.py

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Run this script: ./scripts/setup-openra-assets.sh"
echo "2. Follow the manual instructions above to get assets"
echo "3. Assets will be ready for use in the game"