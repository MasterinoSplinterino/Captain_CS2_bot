#!/bin/bash

# USB Transfer Helper for CS2 Server
# Run this script on your Proxmox/Linux host as root (sudo).

DEST_DIR="/opt/cs2-data"
MOUNT_POINT="/mnt/usb_transfer"

# Ensure running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./usb_transfer.sh)"
  exit 1
fi

echo "=== CS2 USB Transfer Helper ==="
echo "1. Please plug in your USB drive now."
read -p "Press Enter when ready..."

echo "Scanning for drives..."
lsblk -o NAME,SIZE,TYPE,FSTYPE,MODEL,LABEL | grep -v "loop"
echo "-----------------------------------"
echo "Identify your USB partition (e.g., sdb1, sdc1)."
read -p "Enter the device name (e.g., sdb1): " DEVICE_NAME

DEVICE_PATH="/dev/$DEVICE_NAME"

if [ ! -b "$DEVICE_PATH" ]; then
    echo "Error: Device $DEVICE_PATH not found!"
    exit 1
fi

# Create mount point
mkdir -p "$MOUNT_POINT"

# Attempt mount
echo "Mounting $DEVICE_PATH to $MOUNT_POINT..."
mount "$DEVICE_PATH" "$MOUNT_POINT"

if [ $? -ne 0 ]; then
    echo "Mount failed. Trying with specific filesystems..."
    
    # Try ExFAT (Kernel)
    mount -t exfat "$DEVICE_PATH" "$MOUNT_POINT"
    if [ $? -eq 0 ]; then
        echo "Mounted as ExFAT (Kernel)."
    else
        # Try ExFAT (FUSE) - Fallback if kernel module is missing
        echo "Kernel mount failed. Trying FUSE..."
        mount.exfat-fuse "$DEVICE_PATH" "$MOUNT_POINT"
        if [ $? -eq 0 ]; then
            echo "Mounted as ExFAT (FUSE)."
        else
            # Try NTFS
            mount -t ntfs-3g "$DEVICE_PATH" "$MOUNT_POINT"
            if [ $? -eq 0 ]; then
                echo "Mounted as NTFS."
            else
                echo "----------------------------------------------------------------"
                echo "CRITICAL ERROR: Could not mount USB."
                echo "Most likely, you are missing the filesystem drivers."
                echo ""
                echo "PLEASE RUN THIS COMMAND TO FIX IT:"
                echo "   apt-get update && apt-get install -y exfat-fuse exfatprogs ntfs-3g"
                echo ""
                echo "Then run this script again."
                echo "----------------------------------------------------------------"
                exit 1
            fi
        fi
    fi
fi

echo "USB Mounted successfully."

# Check for source folder
SOURCE_DIR="$MOUNT_POINT/cs2-data"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Warning: 'cs2-data' folder not found at root of USB ($SOURCE_DIR)."
    echo "Contents of USB:"
    ls "$MOUNT_POINT"
    read -p "Enter the correct path to cs2-data relative to USB root (e.g., ./my_backup/cs2-data): " REL_PATH
    SOURCE_DIR="$MOUNT_POINT/$REL_PATH"
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory still not found. Aborting."
    umount "$MOUNT_POINT"
    exit 1
fi

echo "Ready to copy from $SOURCE_DIR to $DEST_DIR"
echo "This may take a while..."
read -p "Press Enter to start copy..."

mkdir -p "$DEST_DIR"

# Copy with progress
rsync -avP "$SOURCE_DIR/" "$DEST_DIR/"

echo "Copy complete."

echo "Setting permissions for Docker (UID 1000)..."
chown -R 1000:1000 "$DEST_DIR"
chmod -R 755 "$DEST_DIR"

echo "Unmounting USB..."
umount "$MOUNT_POINT"

echo "=== Done! ==="
echo "Files are ready at $DEST_DIR"
echo "You can now deploy in Dokploy."
