#!/bin/bash

# Just Shapes & Beats Arcade Launcher for Linux (Native Version)
# This script runs the game natively using Python and Pygame.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install it to play the game."
    exit 1
fi

# Check if Pygame is installed, if not try to install it
if ! python3 -c "import pygame" &> /dev/null
then
    echo "Pygame is not found. Attempting to install it..."
    python3 -m pip install pygame --user
    
    # Check again
    if ! python3 -c "import pygame" &> /dev/null
    then
        echo "Failed to install Pygame. Please run 'pip install pygame' manually."
        exit 1
    fi
fi

# Run the game
echo "Starting Just Shapes & Beats Arcade..."
python3 game.py
