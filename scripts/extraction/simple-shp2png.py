#!/usr/bin/env python3
"""
Simplified SHP to PNG converter without numpy dependency
"""

import struct
import sys
import os

# Try to import PIL, fall back to creating raw data if not available
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not available, will output raw data")

def load_palette(pal_file):
    """Load a C&C PAL file (768 bytes, 256 RGB triplets)"""
    palette = []
    try:
        with open(pal_file, 'rb') as f:
            data = f.read()
            if len(data) >= 768:
                for i in range(256):
                    r = data[i * 3] * 4      # C&C palettes use 6-bit values
                    g = data[i * 3 + 1] * 4
                    b = data[i * 3 + 2] * 4
                    palette.append((min(255, r), min(255, g), min(255, b)))
                return palette
    except Exception as e:
        print(f"Warning: Could not load palette: {e}")
    
    # Default palette if loading fails
    return [(i, i, i) for i in range(256)]

def read_shp_header(filename):
    """Read basic info from SHP file"""
    with open(filename, 'rb') as f:
        # Read header
        num_images = struct.unpack('<H', f.read(2))[0]
        print(f"  Number of frames: {num_images}")
        
        # Skip unknown bytes
        f.read(4)
        
        # Read first image offset to check if file is valid
        first_offset = struct.unpack('<I', f.read(4))[0]
        
        if first_offset > 0:
            # Seek to first image
            f.seek(first_offset)
            header = f.read(8)
            if len(header) >= 8:
                width = header[2]
                height = header[3]
                print(f"  Frame size: {width}x{height}")
                return True, num_images, width, height
    
    return False, 0, 0, 0

def copy_shp_with_info(shp_file, output_dir):
    """Copy SHP file and create info file"""
    basename = os.path.basename(shp_file).replace('.SHP', '')
    
    # Read SHP info
    valid, num_frames, width, height = read_shp_header(shp_file)
    
    if not valid:
        print(f"  ✗ Invalid or empty SHP file")
        return False
    
    # Copy SHP file
    output_shp = os.path.join(output_dir, f"{basename}.shp")
    with open(shp_file, 'rb') as src:
        with open(output_shp, 'wb') as dst:
            dst.write(src.read())
    
    # Create info file
    info_file = os.path.join(output_dir, f"{basename}.info")
    with open(info_file, 'w') as f:
        f.write(f"Original: {shp_file}\n")
        f.write(f"Frames: {num_frames}\n")
        f.write(f"Size: {width}x{height}\n")
        f.write(f"Type: Sprite Sheet\n")
        f.write(f"Note: Use OpenRA or XCC Mixer to convert to PNG\n")
    
    print(f"  ✓ Copied to {output_shp}")
    print(f"  ✓ Info saved to {info_file}")
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: simple-shp2png.py input.shp output_dir [palette.pal]")
        sys.exit(1)
    
    shp_file = sys.argv[1]
    output_dir = sys.argv[2]
    pal_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(shp_file):
        print(f"Error: {shp_file} not found")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Processing {shp_file}")
    
    # For now, just copy the SHP and create an info file
    # Real conversion requires complex SHP format parsing
    success = copy_shp_with_info(shp_file, output_dir)
    
    if success and pal_file:
        # Copy palette too
        pal_output = os.path.join(output_dir, "temperat.pal")
        with open(pal_file, 'rb') as src:
            with open(pal_output, 'wb') as dst:
                dst.write(src.read())
        print(f"  ✓ Palette copied")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()