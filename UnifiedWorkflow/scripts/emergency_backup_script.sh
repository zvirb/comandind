#!/bin/bash

# EMERGENCY BACKUP SCRIPT
# Creates complete backup of critical data before recovery

set -e

BACKUP_DIR="/home/marku/emergency_backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/home/marku/ai_workflow_engine/emergency_backup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log_message() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log_message "=== EMERGENCY BACKUP START ==="
log_message "Backup directory: $BACKUP_DIR"

# Create backup directory
mkdir -p "$BACKUP_DIR"/{volumes,configs,secrets,logs}

# Backup critical volumes
log_message "Backing up critical volumes..."

# PostgreSQL Data (71MB)
log_message "Backing up PostgreSQL data volume..."
docker run --rm -v ai_workflow_engine_postgres_data:/source -v "$BACKUP_DIR/volumes":/backup alpine tar czf /backup/postgres_data.tar.gz -C /source .

# Redis Data (12KB)
log_message "Backing up Redis data volume..."
docker run --rm -v ai_workflow_engine_redis_data:/source -v "$BACKUP_DIR/volumes":/backup alpine tar czf /backup/redis_data.tar.gz -C /source .

# Certificates Volume
log_message "Backing up certificates volume..."
docker run --rm -v ai_workflow_engine_certs:/source -v "$BACKUP_DIR/volumes":/backup alpine tar czf /backup/certs.tar.gz -C /source .

# Ollama Data (29GB) - Optional based on disk space
AVAILABLE_SPACE=$(df "$BACKUP_DIR" | tail -1 | awk '{print $4}')
OLLAMA_SIZE_KB=$((29 * 1024 * 1024))  # 29GB in KB

if [ "$AVAILABLE_SPACE" -gt $((OLLAMA_SIZE_KB + 5*1024*1024)) ]; then
    log_message "Backing up Ollama data volume (29GB)..."
    docker run --rm -v ai_workflow_engine_ollama_data:/source -v "$BACKUP_DIR/volumes":/backup alpine tar czf /backup/ollama_data.tar.gz -C /source .
else
    log_message "WARNING: Insufficient space for Ollama backup - SKIPPING (can re-download models)"
fi

# Backup configuration files
log_message "Backing up configuration files..."
cp -r /home/marku/ai_workflow_engine/config "$BACKUP_DIR/configs/"
cp /home/marku/ai_workflow_engine/docker-compose.yml "$BACKUP_DIR/configs/"
cp /home/marku/ai_workflow_engine/.env "$BACKUP_DIR/configs/"
cp /home/marku/ai_workflow_engine/local.env "$BACKUP_DIR/configs/" 2>/dev/null || true

# Backup secrets directory
log_message "Backing up secrets directory..."
cp -r /home/marku/ai_workflow_engine/secrets "$BACKUP_DIR/secrets/"

# Backup application logs
log_message "Backing up application logs..."
cp -r /home/marku/ai_workflow_engine/logs "$BACKUP_DIR/logs/" 2>/dev/null || true

# Create recovery instructions
cat > "$BACKUP_DIR/RECOVERY_INSTRUCTIONS.md" << 'EOF'
# EMERGENCY RECOVERY INSTRUCTIONS

## Backup Contents:
- PostgreSQL data: volumes/postgres_data.tar.gz
- Redis data: volumes/redis_data.tar.gz  
- Certificates: volumes/certs.tar.gz
- Ollama models: volumes/ollama_data.tar.gz (if space allowed)
- Configuration: configs/
- Secrets: secrets/
- Logs: logs/

## Recovery Process:
1. Stop all containers: docker-compose down
2. Remove volumes: docker volume rm ai_workflow_engine_postgres_data ai_workflow_engine_redis_data ai_workflow_engine_certs
3. Recreate volumes: docker volume create [volume_name]
4. Restore data:
   ```bash
   docker run --rm -v ai_workflow_engine_postgres_data:/target -v /path/to/backup/volumes:/backup alpine tar xzf /backup/postgres_data.tar.gz -C /target
   docker run --rm -v ai_workflow_engine_redis_data:/target -v /path/to/backup/volumes:/backup alpine tar xzf /backup/redis_data.tar.gz -C /target
   docker run --rm -v ai_workflow_engine_certs:/target -v /path/to/backup/volumes:/backup alpine tar xzf /backup/certs.tar.gz -C /target
   ```
5. Restore configs and secrets
6. Start services: docker-compose up -d

## Critical Data Sizes:
- PostgreSQL: 71MB
- Redis: 12KB  
- Ollama: 29GB (can be re-downloaded)
- Total critical: ~71MB
EOF

# Create verification checksums
log_message "Creating verification checksums..."
cd "$BACKUP_DIR"
find . -type f -exec sha256sum {} \; > checksums.txt

# Set permissions
chmod -R 600 "$BACKUP_DIR/secrets"
chmod 755 "$BACKUP_DIR"

BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_message "=== EMERGENCY BACKUP COMPLETE ==="
log_message "Backup location: $BACKUP_DIR"
log_message "Backup size: $BACKUP_SIZE"
log_message "Recovery instructions: $BACKUP_DIR/RECOVERY_INSTRUCTIONS.md"

echo "$BACKUP_DIR"