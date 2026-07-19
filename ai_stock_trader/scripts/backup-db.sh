#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
DB="$SCRIPT_DIR/trading_data.db"
RETENTION=14  # keep 14 days

mkdir -p "$BACKUP_DIR"

DATE=$(date '+%Y%m%d_%H%M%S')
sqlite3 "$DB" ".backup '$BACKUP_DIR/trading_data_$DATE.db'"

# Compress
gzip -f "$BACKUP_DIR/trading_data_$DATE.db"

# Clean old backups
find "$BACKUP_DIR" -name "trading_data_*.db.gz" -mtime +$RETENTION -delete

echo "Backup: trading_data_$DATE.db.gz ($(du -h "$BACKUP_DIR/trading_data_$DATE.db.gz" | cut -f1))"
