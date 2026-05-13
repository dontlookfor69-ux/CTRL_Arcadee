#!/usr/bin/env python3
"""
Run once at arcade startup to ensure dark icons are visible against dark backgrounds.
Brightens icons that are known to be too dark.
"""
import os
import sys

try:
    from PIL import Image, ImageEnhance
except ImportError:
    # Use pip to install Pillow if missing
    os.system(f"{sys.executable} -m pip install Pillow --break-system-packages")
    from PIL import Image, ImageEnhance

# Set path relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "frontend", "godot_project", "assets", "icons")

ICONS_TO_BRIGHTEN = ["etch_a_sketch.png", "doom.png"]
BRIGHTNESS_FACTOR = 3.5  # Multiply brightness by this amount for dark icons
CONTRAST_FACTOR = 1.4

def process_icon(filepath):
    try:
        img = Image.open(filepath).convert("RGBA")
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        
        # Boost brightness
        enhancer = ImageEnhance.Brightness(rgb)
        rgb = enhancer.enhance(BRIGHTNESS_FACTOR)
        
        # Boost contrast slightly
        enhancer = ImageEnhance.Contrast(rgb)
        rgb = enhancer.enhance(CONTRAST_FACTOR)
        
        r2, g2, b2 = rgb.split()
        result = Image.merge("RGBA", (r2, g2, b2, a))
        result.save(filepath)
        print(f"Processed: {filepath}")
    except Exception as e:
        print(f"Failed to process {filepath}: {e}")

if __name__ == "__main__":
    if not os.path.exists(ICONS_DIR):
        print(f"ERROR: Icons directory not found: {ICONS_DIR}")
        sys.exit(1)
        
    for icon_name in ICONS_TO_BRIGHTEN:
        icon_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(icon_path):
            process_icon(icon_path)
        else:
            print(f"WARNING: Icon not found: {icon_path}")
