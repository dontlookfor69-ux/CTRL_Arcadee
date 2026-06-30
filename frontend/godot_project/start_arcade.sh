#!/bin/bash

# Arcade Startup Script
echo "=== Arcade Master Boot Sequence Initiated ==="

# ── Ensure we are in the correct directory ───────────────────────────
cd "$(dirname "$0")"

# ── HDMI & Display Force ──────────────────────────────────────────────
echo "Forcing HDMI display initialization..."
tvservice -p 2>/dev/null || true
fbset -depth 16 2>/dev/null || true

# Cleanup trap to kill any stuck games if CTRL+C is pressed
trap "killall -9 godot3 python3 2>/dev/null" SIGINT SIGTERM EXIT
sleep 1

# ── Boot Beep ────────────────────────────────────────────────────────
echo "Generating BIOS beep..."
python3 -c "
import math, struct, wave
sr=44100; dur=0.12; freq=880
samples=[int(32767*math.sin(2*math.pi*freq*i/sr)) for i in range(int(sr*dur))]
buf=struct.pack('<'+'h'*len(samples),*samples)
with wave.open('/tmp/boot_beep_${USER}.wav','w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(buf)
" && aplay /tmp/boot_beep_${USER}.wav 2>/dev/null &

# ── Launch Godot ─────────────────────────────────────────────────────
# Dependency checks have been moved to system/setup_pi.sh to speed up boot.
# Ensure no broken ALSA configs exist
rm -f ~/.asoundrc

export DISPLAY=${DISPLAY:-:0}
xrandr -s 1280x720 2>/dev/null || true
godot3 --video-driver GLES2 --fullscreen --path . 2>&1 | tee /tmp/arcade_godot_${USER}.log
