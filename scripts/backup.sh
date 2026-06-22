#!/bin/sh
# My Kitchen — hot, consistent SQLite backup.
#
# Uses SQLite's online .backup (via the app container's own sqlite3) so it's
# WAL-safe and can run while the app is live. Writes a timestamped copy into
# ./backups on the host. Keeps the last N (default 14).
#
# Usage:  ./scripts/backup.sh            (from the repo root, where compose runs)
set -e

SERVICE="my-kitchen"
DB_PATH="${MY_KITCHEN_DB_PATH:-/data/my_kitchen.db}"
KEEP="${BACKUP_KEEP:-14}"
BACKUP_DIR="./backups"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/my_kitchen_${STAMP}.db"

mkdir -p "$BACKUP_DIR"

# Is the container running? If so, back up live via its sqlite3. If not, the
# DB file is quiescent on the volume and a plain copy is safe.
if docker compose ps --status running 2>/dev/null | grep -q "$SERVICE"; then
    echo "Container running — taking a live consistent backup..."
    # .backup writes a clean single-file snapshot to the container's /data,
    # which is the bind-mounted ./data, so it appears on the host. Then move it
    # into ./backups with the timestamped name.
    docker compose exec -T "$SERVICE" \
        sqlite3 "$DB_PATH" ".backup '/data/_backup_tmp.db'"
    mv "./data/_backup_tmp.db" "$OUT"
else
    echo "Container stopped — copying the quiescent DB file..."
    if [ ! -f "./data/my_kitchen.db" ]; then
        echo "ERROR: ./data/my_kitchen.db not found. Nothing to back up."
        exit 1
    fi
    cp "./data/my_kitchen.db" "$OUT"
fi

echo "Backup written: $OUT"

# Prune old backups, keeping the most recent $KEEP.
COUNT=$(ls -1 "$BACKUP_DIR"/my_kitchen_*.db 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
    ls -1t "$BACKUP_DIR"/my_kitchen_*.db | tail -n +$((KEEP + 1)) | while read -r old; do
        echo "Pruning old backup: $old"
        rm -f "$old"
    done
fi

echo "Done. $(ls -1 "$BACKUP_DIR"/my_kitchen_*.db 2>/dev/null | wc -l) backup(s) retained."
