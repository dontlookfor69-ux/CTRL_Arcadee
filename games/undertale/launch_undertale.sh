#!/bin/bash
cd "$(dirname "$0")"
ISO_FILE=$(find . -name "*.iso" -print -quit 2>/dev/null)
if [ -z "$ISO_FILE" ]; then
    echo "ERROR: No .iso found. Place Undertale.iso here."
    sleep 5; exit 1
fi
MOUNT_PATH=$(udisksctl loop-setup -f "$(realpath "$ISO_FILE")" | grep -oP '(?<=as ).+(?=\.)')
EXE=$(find "${MOUNT_PATH}" -iname "*.exe" -print -quit 2>/dev/null)
if [ -z "$EXE" ]; then
    echo "ERROR: No .exe inside ISO."
    udisksctl loop-delete -b "${MOUNT_PATH}"
    sleep 5; exit 1
fi
cd "$(dirname "$EXE")"
box64 "$(basename "$EXE")"
udisksctl loop-delete -b "${MOUNT_PATH}"
