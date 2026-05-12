#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Robustly find the game directory (handling nested zip artifacts)
if [ -d "$SCRIPT_DIR/DOOM-style-Game-main/DOOM-style-Game-main" ]; then
    cd "$SCRIPT_DIR/DOOM-style-Game-main/DOOM-style-Game-main"
elif [ -d "$SCRIPT_DIR/DOOM-style-Game-main" ]; then
    cd "$SCRIPT_DIR/DOOM-style-Game-main"
else
    cd "$SCRIPT_DIR"
fi

exec python3 main.py
