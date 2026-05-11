#!/bin/bash

# Arcade Master Boot Script
cd "$(dirname "$0")"

echo "=== Arcade Master Boot Sequence Initiated ==="

# 1. Dependency Checks & Auto-Install
echo "Checking system dependencies..."

# Define required apt packages
APT_PACKAGES="python3-pip python3-tk dasm stella box64 chocolate-doom godot3 mpv yt-dlp"
MISSING_APT=""

for pkg in $APT_PACKAGES; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        MISSING_APT="$MISSING_APT $pkg"
    fi
done

if [ ! -z "$MISSING_APT" ]; then
    echo "Missing apt packages detected: $MISSING_APT"
    echo "Updating and installing... (This requires internet access)"
    sudo apt-get update -y
    sudo apt-get install -y $MISSING_APT
else
    echo "All apt dependencies are met."
fi

# Define required pip packages
PIP_PACKAGES="pynput tinytag keyboard evdev"
MISSING_PIP=""

for pkg in $PIP_PACKAGES; do
    if ! python3 -c "import $pkg" >/dev/null 2>&1; then
        MISSING_PIP="$MISSING_PIP $pkg"
    fi
done

if [ ! -z "$MISSING_PIP" ]; then
    echo "Missing pip packages detected: $MISSING_PIP"
    echo "Installing via pip3..."
    pip3 install $MISSING_PIP --break-system-packages || pip3 install $MISSING_PIP
else
    echo "All pip dependencies are met."
fi

echo "=== System Check Complete. Launching Arcade Frontend ==="

# We export DISPLAY=:0 just in case
export DISPLAY=:0

# Launch Godot
/usr/bin/godot3 --path .
