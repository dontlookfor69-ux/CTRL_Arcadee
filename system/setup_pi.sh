#!/bin/bash
# Arcade Builder System Setup Script

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit
fi

echo "Updating APT..."
apt-get update -y

echo "Installing system dependencies..."
# Core Python dependencies & system libraries
apt-get install -y python3-pip python3-pygame python3-evdev python3-opencv python3-numpy \
                   box64 chocolate-doom plymouth plymouth-themes libsdl2-2.0-0 libsdl2-dev \
                   godot3 wget tar

# Install rembg, tinytag, and pynput (requires PEP 668 override on newer Pi OS, so we use break-system-packages if needed)
echo "Installing pip dependencies..."
pip3 install rembg tinytag pynput --break-system-packages || pip3 install rembg tinytag pynput

echo "Setting up Plymouth boot theme..."
# This will be configured manually or by another script, but we ensure plymouth is ready
plymouth-set-default-theme -R details

echo "System Setup Complete!"
