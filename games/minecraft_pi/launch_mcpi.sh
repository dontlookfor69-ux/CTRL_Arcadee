#!/bin/bash
cd "$(dirname "$0")"

# Check if Minecraft Pi is downloaded
if [ ! -d "mcpi" ]; then
    echo "Minecraft Pi not found. Downloading..."
    wget -qO- https://s3.amazonaws.com/assets.minecraft.net/pi/minecraft-pi-0.1.1.tar.gz | tar -xz
    
    # Optional: apply patches for mcpi-reborn or standard library
fi

cd mcpi
export DISPLAY=:0
./minecraft-pi
