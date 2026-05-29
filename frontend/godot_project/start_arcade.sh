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

# ── Launch Godot ─────────────────────────────────────────────────────
# Dependency checks have been moved to system/setup_pi.sh to speed up boot.
echo "=== Launching Arcade Frontend ==="
export DISPLAY=:0
godot3 --video-driver GLES2 --fullscreen --path . 2>&1 | tee /tmp/arcade_godot.log
