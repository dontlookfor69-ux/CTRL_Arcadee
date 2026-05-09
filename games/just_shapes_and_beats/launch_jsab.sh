#!/bin/bash
cd "$(dirname "$0")"

if [ ! -f "Just Shapes & Beats.exe" ]; then
    echo "ERROR: Just Shapes & Beats.exe not found!"
    echo "Please place your legally owned JSAB game files here."
    sleep 5
    exit 1
fi

# Launch with box64
box64 "Just Shapes & Beats.exe"
