#!/bin/bash
set -euo pipefail

MOUNTPOINT="/data/slideshow"
USER_NAME="admin"
GROUP_NAME="admin"

mkdir -p "$MOUNTPOINT"

# Schon gemountet? Dann nichts tun.
if findmnt -rn "$MOUNTPOINT" >/dev/null; then
  exit 0
fi

# Erstes USB-Blockdevice mit Filesystem suchen
DEV="$(lsblk -rpno NAME,TRAN,TYPE,FSTYPE \
  | awk '$2=="usb" && $3=="part" && $4!="" {print $1; exit}')"

[ -n "${DEV:-}" ] || exit 0

FSTYPE="$(blkid -o value -s TYPE "$DEV")"
UID_NUM="$(id -u "$USER_NAME")"
GID_NUM="$(id -g "$GROUP_NAME")"

case "$FSTYPE" in
  vfat|exfat|ntfs)
    mount -t "$FSTYPE" \
      -o rw,nosuid,nodev,noexec,uid="$UID_NUM",gid="$GID_NUM",umask=022 \
      "$DEV" "$MOUNTPOINT"
    ;;
  ext2|ext3|ext4)
    mount -t "$FSTYPE" \
      -o rw,nosuid,nodev,noexec \
      "$DEV" "$MOUNTPOINT"
    ;;
  *)
    mount -o rw,nosuid,nodev,noexec "$DEV" "$MOUNTPOINT"
    ;;
esac

chown "$USER_NAME:$GROUP_NAME" "$MOUNTPOINT" || true
