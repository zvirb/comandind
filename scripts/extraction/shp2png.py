#!/usr/bin/env python3
"""
Simple SHP to PNG converter for C&C Tiberian Dawn sprites
Based on the SHP format documentation
"""

import struct
import sys
import os
from PIL import Image
import numpy as np

# C&C Temperat palette (256 RGB colors)
# This is a simplified version - actual palette should be loaded from TEMPERAT.PAL
DEFAULT_PALETTE = [
    (0, 0, 0),       # 0: Black (transparent)
    (252, 252, 252), # 1: White
    (244, 0, 0),     # 2: Red
    (0, 232, 0),     # 3: Green
    (0, 0, 252),     # 4: Blue
    (252, 252, 0),   # 5: Yellow
    (252, 0, 252),   # 6: Magenta
    (0, 252, 252),   # 7: Cyan
] + [(i, i, i) for i in range(8, 256)]  # Grayscale for the rest

def load_palette(pal_file):
    """Load a C&C PAL file (768 bytes, 256 RGB triplets)"""
    try:
        with open(pal_file, 'rb') as f:
            data = f.read()
            if len(data) >= 768:
                palette = []
                for i in range(256):
                    r = data[i * 3] * 4      # C&C palettes use 6-bit values
                    g = data[i * 3 + 1] * 4
                    b = data[i * 3 + 2] * 4
                    palette.append((min(255, r), min(255, g), min(255, b)))
                return palette
    except:
        pass
    return DEFAULT_PALETTE

def read_shp_td(filename):
    """Read a Tiberian Dawn SHP file"""
    with open(filename, 'rb') as f:
        # Read header
        num_images = struct.unpack('<H', f.read(2))[0]
        
        # Skip unknown bytes
        f.read(4)
        
        # Read offsets for each image + 2 extra (EOF markers)
        offsets = []
        for i in range(num_images + 2):
            offset = struct.unpack('<I', f.read(4))[0]
            # Offset of 0 means no image
            offsets.append(offset)
        
        images = []
        
        for i in range(num_images):
            if offsets[i] == 0:
                images.append(None)
                continue
                
            # Seek to image data
            f.seek(offsets[i])
            
            # Read image header
            header = f.read(8)
            if len(header) < 8:
                images.append(None)
                continue
                
            flags = struct.unpack('<H', header[0:2])[0]
            width = header[2]
            height = header[3]
            delta_size = struct.unpack('<H', header[4:6])[0]
            rle_size = struct.unpack('<H', header[6:8])[0]
            
            # Skip for now if compressed
            if flags != 0:
                # Compressed format - simplified handling
                width = width if width > 0 else 24
                height = height if height > 0 else 24
                # Create placeholder
                img_data = np.zeros((height, width), dtype=np.uint8)
            else:
                # Uncompressed - read raw pixel data
                img_data = np.zeros((height, width), dtype=np.uint8)
                for y in range(height):
                    for x in range(width):
                        pixel = f.read(1)
                        if pixel:
                            img_data[y, x] = pixel[0]
            
            images.append({
                'width': width,
                'height': height,
                'data': img_data
            })
    
    return images

def create_sprite_sheet(images, palette):
    """Create a horizontal sprite sheet from SHP images"""
    if not images:
        return None
    
    # Filter out None images
    valid_images = [img for img in images if img is not None]
    if not valid_images:
        return None
    
    # Calculate dimensions
    max_height = max(img['height'] for img in valid_images)
    total_width = sum(img['width'] for img in valid_images)
    
    # Create sprite sheet
    sprite_sheet = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))
    
    x_offset = 0
    for img in valid_images:
        # Convert indexed color to RGBA
        frame = Image.new('RGBA', (img['width'], img['height']), (0, 0, 0, 0))
        pixels = frame.load()
        
        for y in range(img['height']):
            for x in range(img['width']):
                color_idx = img['data'][y, x]
                if color_idx > 0:  # 0 is transparent
                    color = palette[color_idx] if color_idx < len(palette) else (255, 255, 255)
                    pixels[x, y] = color + (255,)  # Add alpha
        
        sprite_sheet.paste(frame, (x_offset, 0))
        x_offset += img['width']
    
    return sprite_sheet

def convert_shp_to_png(shp_file, png_file, pal_file=None):
    """Convert a SHP file to PNG"""
    print(f"Converting {shp_file} to {png_file}")
    
    # Load palette
    palette = load_palette(pal_file) if pal_file else DEFAULT_PALETTE
    
    try:
        # Read SHP file
        images = read_shp_td(shp_file)
        
        if not images:
            print(f"  No images found in {shp_file}")
            return False
        
        # Create sprite sheet
        sprite_sheet = create_sprite_sheet(images, palette)
        
        if sprite_sheet:
            sprite_sheet.save(png_file)
            print(f"  ✓ Saved {len([i for i in images if i])} frames to {png_file}")
            return True
        else:
            print(f"  ✗ Failed to create sprite sheet")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: shp2png.py input.shp output.png [palette.pal]")
        sys.exit(1)
    
    shp_file = sys.argv[1]
    png_file = sys.argv[2]
    pal_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(shp_file):
        print(f"Error: {shp_file} not found")
        sys.exit(1)
    
    success = convert_shp_to_png(shp_file, png_file, pal_file)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()