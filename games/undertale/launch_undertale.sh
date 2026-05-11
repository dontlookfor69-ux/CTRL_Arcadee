#!/bin/bash
cd "$(dirname "$0")"

ISO_FILE=$(find . -name "*.iso" -print -quit 2>/dev/null)
if [ -z "$ISO_FILE" ]; then
    echo "ERROR: No .iso found. Place Undertale.iso in this directory."
    sleep 5; exit 1
fi

ISO_ABS="$(realpath "$ISO_FILE")"

# Set up loop device
LOOP_OUTPUT=$(udisksctl loop-setup -f "$ISO_ABS" 2>&1)
LOOP_DEV=$(echo "$LOOP_OUTPUT" | grep -oP '/dev/loop\d+')

if [ -z "$LOOP_DEV" ]; then
    echo "ERROR: Could not create loop device. Output: $LOOP_OUTPUT"
    sleep 5; exit 1
fi

echo "Loop device: $LOOP_DEV"

# Mount the loop device
MOUNT_OUTPUT=$(udisksctl mount -b "$LOOP_DEV" 2>&1)
MOUNT_PATH=$(echo "$MOUNT_OUTPUT" | grep -oP '(?<=at ).*' | sed 's/\.$//')

if [ -z "$MOUNT_PATH" ]; then
    echo "ERROR: Could not mount $LOOP_DEV. Output: $MOUNT_OUTPUT"
    udisksctl loop-delete -b "$LOOP_DEV"
    sleep 5; exit 1
fi

echo "Mounted at: $MOUNT_PATH"

EXE=$(find "$MOUNT_PATH" -iname "*.exe" -print -quit 2>/dev/null)
if [ -z "$EXE" ]; then
    echo "ERROR: No .exe found inside ISO at $MOUNT_PATH"
    udisksctl unmount -b "$LOOP_DEV"
    udisksctl loop-delete -b "$LOOP_DEV"
    sleep 5; exit 1
fi

echo "Launching: $EXE"
cd "$(dirname "$EXE")"
box64 "$(basename "$EXE")"
EXIT_CODE=$?

# Cleanup
udisksctl unmount -b "$LOOP_DEV" 2>/dev/null
udisksctl loop-delete -b "$LOOP_DEV" 2>/dev/null

exit $EXIT_CODE
