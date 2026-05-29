#!/bin/bash
# Download and install Godot 3.5.3 stable
echo "Downloading Godot 3.5.3..."
wget -q https://downloads.tuxfamily.org/godotengine/3.5.3/Godot_v3.5.3-stable_x11.64.zip -O /tmp/godot.zip
echo "Extracting Godot..."
unzip -o /tmp/godot.zip -d /tmp/
sudo mv /tmp/Godot_v3.5.3-stable_x11.64 /usr/local/bin/godot3
sudo chmod +x /usr/local/bin/godot3
rm /tmp/godot.zip
echo "Godot 3.5.3 installed as /usr/local/bin/godot3"
