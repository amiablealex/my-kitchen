#!/bin/sh
# My Kitchen — restore a SQLite backup over the live database.
#
# Stops the app, swaps in the chosen backup (clearing stale WAL/SHM sidecars so
# the restored file is authoritative), then restarts.
#
# Usage:  ./scripts/restore.sh ./backups/my_kitchen_YYYYmmdd_HHMMSS.db
set -e

BACKUP_FILE="$1"
DATA_DIR="./data"
LIVE_DB="$DATA_DIR/my_kitchen.db"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <path-to-backup.db>"
    echo "Available backups:"
    ls -1t ./backups/my_kitchen_*.db 2>/dev/null || echo "  (none found in ./backups)"
    exit 1
fi
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "This will REPLACE the current database with:"
echo "    $BACKUP_FILE"
printf "Type 'yes' to continue: "
read -r CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 1; }

echo "Stopping the app..."
docker compose stop my-kitchen

# Safety net: snapshot the current DB before overwriting, so a wrong restore is
# itself recoverable.
if [ -f "$LIVE_DB" ]; then
    SAFETY="$DATA_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).db"
    cp "$LIVE_DB" "$SAFETY"
    echo "Current DB saved as: $SAFETY"
fi

echo "Restoring..."
cp "$BACKUP_FILE" "$LIVE_DB"
# Clear stale WAL/SHM so the restored file is the single source of truth.
rm -f "$LIVE_DB-wal" "$LIVE_DB-shm"

echo "Starting the app..."
docker compose start my-kitchen

echo "Restore complete. Check the app and your data."
