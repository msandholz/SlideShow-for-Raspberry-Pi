#!/bin/bash

MOUNTPOINT="/data/slideshow"
LOG="/var/log/slideshow/mount-usb.log"

mkdir -p "$MOUNTPOINT"

echo "===== $(date) USB Mount Start =====" >> "$LOG"

# alle möglichen USB-Partitionen durchgehen
for DEV in /dev/sd[a-z][0-9]; do

    [ -b "$DEV" ] || continue

    echo "Prüfe: $DEV" >> "$LOG"

    # prüfen ob Dateisystem existiert
    FSTYPE=$(blkid -o value -s TYPE "$DEV" 2>/dev/null)

    if [ -z "$FSTYPE" ]; then
        echo "Kein Dateisystem auf $DEV -> skip" >> "$LOG"
        continue
    fi

    echo "FS: $DEV = $FSTYPE" >> "$LOG"

    # mountpoint sauber machen
    umount "$MOUNTPOINT" 2>/dev/null

    # Mount versuchen (auto erkennt exfat/ntfs/vfat/ext4)
    if  mount -t auto "$DEV" "$MOUNTPOINT" >> "$LOG" 2>&1; then
        echo "SUCCESS: $DEV gemountet auf $MOUNTPOINT" >> "$LOG"
        exit 0
    else
        echo "FAIL: $DEV konnte nicht gemountet werden" >> "$LOG"
    fi

done

echo "KEIN gültiger USB-Stick gefunden" >> "$LOG"
exit 1
