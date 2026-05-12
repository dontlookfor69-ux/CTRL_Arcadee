@echo off
title Just Shapes & Beats Arcade - Launcher
echo ========================================
echo   Just Shapes & Beats Arcade Launcher
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on your system.
    echo Please install Python 3 from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b
)

:: Check if Pygame is installed
python -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Pygame is missing. Attempting to install it...
    python -m pip install pygame
    
    :: Verify installation
    python -c "import pygame" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Could not install Pygame automatically.
        echo Please try running this command manually in a new CMD:
        echo pip install pygame
        echo.
        pause
        exit /b
    )
    echo [SUCCESS] Pygame has been installed!
    echo.
)

:: Run the game
echo Starting the game...
python game.py

:: If the game crashes, keep the window open so we can see the error
if %errorlevel% neq 0 (
    echo.
    echo [CRASH] The game closed with an error code: %errorlevel%
    pause
)
