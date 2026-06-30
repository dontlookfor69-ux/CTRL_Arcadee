#!/bin/bash
# Setup script to configure Raspberry Pi to boot into a bare X11 server for the Arcade
# This disables the heavy desktop environment, freeing up massive amounts of RAM and VRAM.

echo "=== Configuring Bare X11 Arcade Mode ==="

echo "[1/3] Installing lightweight X11 dependencies (if needed)..."
sudo apt-get update
sudo apt-get install -y xinit xserver-xorg x11-xserver-utils

echo "[2/3] Disabling heavy desktop environment on boot..."
# Switch default boot target to CLI instead of GUI
sudo systemctl set-default multi-user.target

echo "[3/3] Setting up autostart profile for the arcade..."
PROFILE_FILE="$HOME/.bash_profile"

# Remove any existing arcade autostart block to avoid duplicates
if [ -f "$PROFILE_FILE" ]; then
    sed -i '/# === ARCADE AUTOSTART ===/,/# === END ARCADE AUTOSTART ===/d' "$PROFILE_FILE"
fi

# Add the new autostart block
cat << 'EOF' >> "$PROFILE_FILE"
# === ARCADE AUTOSTART ===
# Automatically start the arcade in a bare X server if logging in on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    echo "Starting Arcade Frontend..."
    # Launch xinit with the start_arcade.sh script, passing -nocursor to hide the mouse
    exec xinit /home/ctrl/Desktop/CTRL_Arcadee/frontend/godot_project/start_arcade.sh -- -nocursor
fi
# === END ARCADE AUTOSTART ===
EOF

echo "Done! The Raspberry Pi is now configured for Option 3."
echo "On the next reboot, it will boot directly into the Arcade without the desktop overhead."
