@echo off
echo ========================================
echo   CTRL Arcade - Laptop Testing Mode
echo ========================================
echo.
echo Launching Godot Frontend in WSL...
echo.

:: Path to the Godot project within WSL
set WSL_PROJECT_PATH=/mnt/d/Hoofd_Folder/CTRL_Arcadee/frontend/godot_project

:: Launch Godot using WSLg (Windows 11 GUI support)
:: We use -u root to ensure it has permissions for flag files in /tmp/
:: Added MESA_LOADER_DRIVER_OVERRIDE and GALLIUM_DRIVER to force hardware acceleration
wsl -d kali-linux -u root -- bash -c "export MESA_LOADER_DRIVER_OVERRIDE=d3d12; export GALLIUM_DRIVER=d3d12; cd %WSL_PROJECT_PATH% && godot3 --path . --video-driver GLES2"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Godot exited with an error.
    pause
)

echo.
echo Shutting down WSL to free memory and prevent lag...
wsl --shutdown
echo Done!
