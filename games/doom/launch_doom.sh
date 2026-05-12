#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/DOOM-style-Game-main/DOOM-style-Game-main"
exec python3 main.py
