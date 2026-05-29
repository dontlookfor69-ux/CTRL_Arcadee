@echo off
title Pygame Force Installer
echo ========================================
echo     Pygame Force Installation Tool
echo ========================================
echo.

echo Attempting Method 1: python -m pip...
python -m pip install pygame
if %errorlevel% equ 0 goto SUCCESS

echo.
echo Attempting Method 2: pip install...
pip install pygame
if %errorlevel% equ 0 goto SUCCESS

echo.
echo Attempting Method 3: py launcher...
py -m pip install pygame
if %errorlevel% equ 0 goto SUCCESS

echo.
echo Attempting Method 4: User-only install...
python -m pip install pygame --user
if %errorlevel% equ 0 goto SUCCESS

:FAILED
echo.
echo [ERROR] All installation methods failed. 
echo Are you connected to the internet?
echo.
echo Please copy the text above and send it to me so I can help you fix it!
pause
exit /b

:SUCCESS
echo.
echo [SUCCESS] Pygame has been installed!
echo You can now close this and run "Start Game.bat"
pause
exit /b
