#!/bin/bash
# launch_mcpi.sh — Launch CTRL Craft (pure pygame, no OpenGL)
cd "$(dirname "$0")"
export DISPLAY=:0

# pygame is installed via apt on Raspberry Pi OS
if ! python3 -c "import pygame" &>/dev/null; then
    echo "=== Installing pygame ==="
    sudo apt-get install -y python3-pygame 2>/dev/null || \
    python3 -m pip install pygame --break-system-packages
fi

exec python3 Minecraft/main.py
