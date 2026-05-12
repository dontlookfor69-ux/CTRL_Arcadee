#!/bin/bash
cd "$(dirname "$0")"

# Check if Minecraft Pi is downloaded
if [ ! -d "mcpi" ]; then
    echo "ERROR: Minecraft Pi (mcpi/) not found in $(pwd)"
    echo "The official download link is currently unavailable."
    echo "Please manually place the 'mcpi' folder here to enable this game."
    sleep 5
    exit 1
fi

cd mcpi
export DISPLAY=:0
./minecraft-pi
