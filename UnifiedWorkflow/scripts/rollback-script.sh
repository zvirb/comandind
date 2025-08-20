#!/bin/bash
# Emergency Rollback Script - Generated $(date)
# Commit Reference: c0e8ae886ebd0bedb022688e746b8aee5b95f75c

echo "=== EMERGENCY ROLLBACK INITIATED ==="

# Stop current services
docker compose down

# Revert to previous git state
git checkout c0e8ae886ebd0bedb022688e746b8aee5b95f75c

# Restore docker compose files if needed
if [ -f "docker-compose.yml.backup-$(date +%Y%m%d)*" ]; then
    cp docker-compose.yml.backup-* docker-compose.yml
    cp docker-compose.override.yml.backup-* docker-compose.override.yml
fi

# Restart services
docker compose up -d

echo "=== ROLLBACK COMPLETED - Verify https://aiwfe.com ==="
