#!/bin/bash
cd "$(dirname "$0")"

ISO_FILE=$(find . -name "*.iso" -print -quit)

if [ -z "$ISO_FILE" ]; then
    echo "ERROR: Undertale.iso not found!"
    echo "Please place your legally owned Undertale.iso game file here or in a subfolder."
    sleep 5
    exit 1
fi

echo "Mounting $ISO_FILE..."
sudo mkdir -p /mnt/undertale_iso
sudo mount -o loop "$ISO_FILE" /mnt/undertale_iso

# Find ANY executable inside the mounted ISO
EXE_FILE=$(find /mnt/undertale_iso -iname "*.exe" -print -quit)

if [ -z "$EXE_FILE" ]; then
    echo "ERROR: No .exe files found inside the ISO!"
    echo "Here is what is inside the ISO:"
    ls -la /mnt/undertale_iso
    sudo umount /mnt/undertale_iso
    sleep 10
    exit 1
fi

echo "Found executable: $EXE_FILE"
echo "Launching Undertale via box64..."

# We must execute it from its own directory so it finds its data files
cd "$(dirname "$EXE_FILE")"
box64 "$(basename "$EXE_FILE")"

# After game closes, return and unmount
echo "Unmounting ISO..."
cd - > /dev/null
sudo umount /mnt/undertale_iso
