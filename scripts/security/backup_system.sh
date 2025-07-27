#!/bin/bash
# Comprehensive Backup System

set -euo pipefail

BACKUP_BASE_DIR="./backups"
ENCRYPTED_BACKUP_DIR="./backup/encrypted"
BACKUP_RETENTION_DAYS=30
ENCRYPTION_PASSWORD_FILE="config/security/backup_password.txt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Logging
log_backup() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - BACKUP - $1" | tee -a logs/security/backup.log
}

# Generate backup encryption password
generate_backup_password() {
    if [ ! -f "$ENCRYPTION_PASSWORD_FILE" ]; then
        echo "Generating backup encryption password..."
        openssl rand -base64 32 > "$ENCRYPTION_PASSWORD_FILE"
        chmod 600 "$ENCRYPTION_PASSWORD_FILE"
        log_backup "Generated new backup encryption password"
    fi
}

# Create encrypted backup
create_backup() {
    local backup_type="${1:-full}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="elite_bot_${backup_type}_${timestamp}"
    local backup_dir="$BACKUP_BASE_DIR/$backup_name"
    
    mkdir -p "$backup_dir"
    mkdir -p "$ENCRYPTED_BACKUP_DIR"
    
    log_backup "Starting $backup_type backup: $backup_name"
    
    # Generate encryption password if needed
    generate_backup_password
    
    # Backup database
    if [ "$backup_type" = "full" ] || [ "$backup_type" = "data" ]; then
        log_backup "Backing up database..."
        pg_dump -h localhost -U elite_bot elite_bot_prod > "$backup_dir/database.sql"
        
        # Backup Redis data
        if command -v redis-cli &> /dev/null; then
            redis-cli -a "${REDIS_PASSWORD:-}" --rdb "$backup_dir/redis_dump.rdb" 2>/dev/null || true
        fi
    fi
    
    # Backup configuration
    log_backup "Backing up configuration..."
    cp -r config "$backup_dir/" 2>/dev/null || true
    cp .env.production "$backup_dir/" 2>/dev/null || true
    
    # Backup data directory
    if [ "$backup_type" = "full" ] || [ "$backup_type" = "data" ]; then
        log_backup "Backing up data directory..."
        cp -r data "$backup_dir/" 2>/dev/null || true
    fi
    
    # Backup logs (recent only)
    log_backup "Backing up recent logs..."
    mkdir -p "$backup_dir/logs"
    find logs -name "*.log" -mtime -7 -exec cp {} "$backup_dir/logs/" \; 2>/dev/null || true
    
    # Create encrypted archive
    log_backup "Creating encrypted archive..."
    tar -czf "$backup_dir.tar.gz" -C "$BACKUP_BASE_DIR" "$backup_name"
    
    # Encrypt the archive
    openssl enc -aes-256-cbc -salt -pbkdf2 \
        -in "$backup_dir.tar.gz" \
        -out "$ENCRYPTED_BACKUP_DIR/$backup_name.tar.gz.enc" \
        -pass file:"$ENCRYPTION_PASSWORD_FILE"
    
    # Clean up unencrypted files
    rm -rf "$backup_dir"
    rm "$backup_dir.tar.gz"
    
    # Create checksum
    sha256sum "$ENCRYPTED_BACKUP_DIR/$backup_name.tar.gz.enc" > "$ENCRYPTED_BACKUP_DIR/$backup_name.sha256"
    
    log_backup "Backup completed: $ENCRYPTED_BACKUP_DIR/$backup_name.tar.gz.enc"
    
    # Clean old backups
    cleanup_old_backups
}

# Restore from backup
restore_backup() {
    local backup_file="$1"
    local restore_dir="./restore_$(date +%Y%m%d_%H%M%S)"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}❌ Backup file not found: $backup_file${NC}"
        exit 1
    fi
    
    log_backup "Starting restore from: $backup_file"
    
    # Verify checksum
    local checksum_file="${backup_file%.enc}.sha256"
    if [ -f "$checksum_file" ]; then
        if ! sha256sum -c "$checksum_file"; then
            echo -e "${RED}❌ Checksum verification failed${NC}"
            exit 1
        fi
        log_backup "Checksum verification passed"
    fi
    
    mkdir -p "$restore_dir"
    
    # Decrypt backup
    log_backup "Decrypting backup..."
    openssl enc -aes-256-cbc -d -salt -pbkdf2 \
        -in "$backup_file" \
        -out "$restore_dir/backup.tar.gz" \
        -pass file:"$ENCRYPTION_PASSWORD_FILE"
    
    # Extract backup
    log_backup "Extracting backup..."
    tar -xzf "$restore_dir/backup.tar.gz" -C "$restore_dir"
    
    echo -e "${GREEN}✅ Backup extracted to: $restore_dir${NC}"
    echo -e "${YELLOW}⚠️  Manual restoration required for database and configuration${NC}"
    
    log_backup "Restore extraction completed: $restore_dir"
}

# Cleanup old backups
cleanup_old_backups() {
    log_backup "Cleaning up backups older than $BACKUP_RETENTION_DAYS days"
    
    find "$ENCRYPTED_BACKUP_DIR" -name "*.tar.gz.enc" -mtime +$BACKUP_RETENTION_DAYS -delete
    find "$ENCRYPTED_BACKUP_DIR" -name "*.sha256" -mtime +$BACKUP_RETENTION_DAYS -delete
    
    log_backup "Cleanup completed"
}

# List available backups
list_backups() {
    echo "Available encrypted backups:"
    ls -la "$ENCRYPTED_BACKUP_DIR"/*.tar.gz.enc 2>/dev/null | \
        awk '{print $9, $5, $6, $7, $8}' | \
        sed 's|.*/||' || echo "No backups found"
}

# Verify backup integrity
verify_backups() {
    local verified=0
    local failed=0
    
    for backup in "$ENCRYPTED_BACKUP_DIR"/*.tar.gz.enc; do
        [ -f "$backup" ] || continue
        
        local checksum_file="${backup%.enc}.sha256"
        if [ -f "$checksum_file" ]; then
            if sha256sum -c "$checksum_file" >/dev/null 2>&1; then
                echo "✅ $(basename "$backup")"
                ((verified++))
            else
                echo "❌ $(basename "$backup")"
                ((failed++))
            fi
        else
            echo "⚠️ $(basename "$backup") - no checksum"
        fi
    done
    
    echo "Verified: $verified, Failed: $failed"
}

# Schedule automatic backups
schedule_backups() {
    # Add cron job for daily backups
    (crontab -l 2>/dev/null; echo "0 2 * * * $PWD/scripts/security/backup_system.sh auto-backup") | crontab -
    log_backup "Scheduled daily automatic backups at 2 AM"
}

# Automatic backup (for cron)
auto_backup() {
    # Determine backup type based on day
    local day_of_week=$(date +%u)
    if [ "$day_of_week" = "7" ]; then
        # Full backup on Sunday
        create_backup "full"
    else
        # Data backup on other days
        create_backup "data"
    fi
}

# Main command handler
case "${1:-}" in
    "create")
        create_backup "${2:-full}"
        ;;
    "restore")
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        restore_backup "$2"
        ;;
    "list")
        list_backups
        ;;
    "verify")
        verify_backups
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "schedule")
        schedule_backups
        ;;
    "auto-backup")
        auto_backup
        ;;
    *)
        echo "Comprehensive Backup System"
        echo "Usage: $0 {create|restore|list|verify|cleanup|schedule|auto-backup}"
        echo ""
        echo "Commands:"
        echo "  create [type]    - Create encrypted backup (full|data|config)"
        echo "  restore <file>   - Restore from encrypted backup"
        echo "  list            - List available backups"
        echo "  verify          - Verify backup integrity"
        echo "  cleanup         - Remove old backups"
        echo "  schedule        - Schedule automatic backups"
        echo "  auto-backup     - Automatic backup (for cron)"
        echo ""
        echo "Examples:"
        echo "  $0 create full"
        echo "  $0 restore backup/encrypted/elite_bot_full_20241201_120000.tar.gz.enc"
        echo "  $0 list"
        exit 1
        ;;
esac
