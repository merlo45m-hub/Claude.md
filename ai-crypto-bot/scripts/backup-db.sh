#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB="$SCRIPT_DIR/data/trades.db"
RETENTION=14
mkdir -p "$BACKUP_DIR"
DATE=$(date '+%Y%m%d_%H%M%S')
sqlite3 "$DB" ".backup '$BACKUP_DIR/trades_$DATE.db'"
gzip -f "$BACKUP_DIR/trades_$DATE.db"
find "$BACKUP_DIR" -name "trades_*.db.gz" -mtime +$RETENTION -delete
echo "Backup: trades_$DATE.db.gz ($(du -h "$BACKUP_DIR/trades_$DATE.db.gz" | cut -f1))"
