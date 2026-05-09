$pacman_dir = "c:\Users\HP\Desktop\CTRL_Arcade\games\pacman"
$source_dir = "c:\Users\HP\Desktop\CTRL_Arcade\Pacman-Source-Code-1.1.0"
$dest_dir = "$pacman_dir\atari_source"

if (-Not (Test-Path $dest_dir)) {
    New-Item -ItemType Directory -Path $dest_dir
}

Move-Item -Path "$source_dir\*" -Destination $dest_dir -Force

Remove-Item -Path "$pacman_dir\src" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$pacman_dir\assets" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$pacman_dir\levels" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$pacman_dir\main.py" -Force -ErrorAction SilentlyContinue
Remove-Item -Path $source_dir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Migration Complete"
