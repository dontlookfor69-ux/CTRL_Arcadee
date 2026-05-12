#!/bin/bash

# Arcade Startup Script
echo "=== Arcade Master Boot Sequence Initiated ==="

# ── Ensure we are in the correct directory ───────────────────────────
cd "$(dirname "$0")"

# ── HDMI & Display Force ──────────────────────────────────────────────
echo "Forcing HDMI display initialization..."
tvservice -p 2>/dev/null || true
fbset -depth 16 2>/dev/null || true
sleep 1

# ── Boot Beep ────────────────────────────────────────────────────────
echo "Generating BIOS beep..."
python3 -c "
import math, struct, wave
sr=44100; dur=0.12; freq=880
samples=[int(32767*math.sin(2*math.pi*freq*i/sr)) for i in range(int(sr*dur))]
buf=struct.pack('<'+'h'*len(samples),*samples)
with wave.open('/tmp/boot_beep.wav','w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(buf)
" && aplay /tmp/boot_beep.wav 2>/dev/null &

# ── Dependency Check ──────────────────────────────────────────────────
echo "Checking system dependencies..."
DEPENDENCIES="python3-pip python3-setuptools python3-pygame libsdl2-2.0-0 box64 udisks2 alsa-utils"
for pkg in $DEPENDENCIES; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        echo "Installing $pkg..."
        sudo apt-get update && sudo apt-get install -y $pkg
    fi
done

# ── Python Packages ───────────────────────────────────────────────────
PIP_PACKAGES="pynput tinytag keyboard evdev yt-dlp scipy"
for pkg in $PIP_PACKAGES; do
    if ! python3 -c "import $pkg" >/dev/null 2>&1; then
        echo "Installing Python package: $pkg..."
        pip3 install $pkg --break-system-packages
    fi
done

# ── Special Packages ──────────────────────────────────────────────────
if ! python3 -c "import cv2; cv2.ximgproc" >/dev/null 2>&1; then
    echo "Installing opencv-contrib-python..."
    pip3 install opencv-contrib-python --break-system-packages || pip3 install opencv-contrib-python-headless --break-system-packages
fi

# ── Launch Godot ─────────────────────────────────────────────────────
echo "=== System Check Complete. Launching Arcade Frontend ==="
export DISPLAY=:0
godot3 --video-driver GLES2 --fullscreen --main-pack . 2>&1 | tee /tmp/arcade_godot.log
