#!/bin/bash

# Arcade Startup Script
echo "=== Arcade Master Boot Sequence Initiated ==="

# ── Ensure we are in the correct directory ───────────────────────────
cd "$(dirname "$0")"

# ── Dependency Check ──────────────────────────────────────────────────
echo "Checking system dependencies..."
DEPENDENCIES="python3-pip python3-setuptools python3-pygame libsdl2-2.0-0 box64 udisks2"
for pkg in $DEPENDENCIES; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        echo "Installing $pkg..."
        sudo apt-get update && sudo apt-get install -y $pkg
    fi
done
echo "All apt dependencies are met."

# ── Python Packages ───────────────────────────────────────────────────
PIP_PACKAGES="pynput tinytag keyboard evdev yt-dlp"
for pkg in $PIP_PACKAGES; do
    if ! python3 -c "import $pkg" >/dev/null 2>&1; then
        echo "Installing Python package: $pkg..."
        pip3 install $pkg --break-system-packages
    fi
done

# ── Special Packages ──────────────────────────────────────────────────
echo "Checking opencv-contrib-python..."
if ! python3 -c "import cv2; cv2.ximgproc" >/dev/null 2>&1; then
    echo "Installing opencv-contrib-python for etch-a-sketch AI..."
    pip3 install opencv-contrib-python --break-system-packages || \
    pip3 install opencv-contrib-python-headless --break-system-packages || \
    echo "WARNING: opencv-contrib failed — etch-a-sketch will use fallback thinning"
else
    echo "opencv-contrib already available."
fi
echo "All pip dependencies are met."

# ── Launch Godot ─────────────────────────────────────────────────────
echo "=== System Check Complete. Launching Arcade Frontend ==="
export DISPLAY=:0

# Use GLES2 for maximum compatibility on Raspberry Pi 4/5
# Removed .pck reference as we are running from source directory
godot3 --video-driver GLES2
