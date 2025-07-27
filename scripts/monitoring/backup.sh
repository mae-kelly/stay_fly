#!/bin/bash
# Backup Script for Production

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "💾 Creating production backup..."

# Backup database
pg_dump -h localhost -U elite_bot elite_bot_prod > "$BACKUP_DIR/database.sql"

# Backup configuration
cp -r config "$BACKUP_DIR/"
cp .env.production "$BACKUP_DIR/"

# Backup data
cp -r data "$BACKUP_DIR/"

# Backup logs (last 7 days)
find logs -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" -C backups "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

echo "✅ Backup completed: $BACKUP_DIR.tar.gz"
