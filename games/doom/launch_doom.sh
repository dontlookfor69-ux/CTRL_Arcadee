#!/bin/bash
cd "$(dirname "$0")"

# Check if WAD exists
if [ ! -f "DOOM.WAD" ] && [ ! -f "DOOM2.WAD" ] && [ ! -f "freedoom2.wad" ]; then
    echo "ERROR: No DOOM.WAD found in $(pwd)!"
    echo "Please place your legally owned DOOM.WAD file here."
    sleep 5
    exit 1
fi

# Attempt to compile original 1997 Linux Doom
if [ ! -f "DOOM-master/linuxdoom-1.10/linux/linuxxdoom" ]; then
    echo "Attempting to compile original DOOM 1997 source code..."
    cd DOOM-master/linuxdoom-1.10
    make
    cd ../..
fi

# Launch Logic
if [ -f "DOOM-master/linuxdoom-1.10/linux/linuxxdoom" ]; then
    echo "Launching compiled 1997 DOOM..."
    cd DOOM-master/linuxdoom-1.10/linux
    ./linuxxdoom -iwad ../../../DOOM.WAD -fullscreen
else
    echo "Original compilation unavailable. Falling back to chocolate-doom..."
    chocolate-doom -iwad DOOM.WAD -fullscreen
fi
