# Infrastructure Rollback Procedures

## Overview
This document provides step-by-step procedures for rolling back infrastructure changes in case of deployment failures or critical issues.

## Quick Rollback Commands

### 1. Docker Container Rollback
```bash
# Stop all containers
docker compose down

# Restore from previous images (tagged with date)
docker compose up -d --no-build

# Or restore specific service
docker compose up -d --no-build api worker
```

### 2. Configuration Rollback
```bash
# Restore previous docker-compose.yml
git checkout HEAD~1 docker-compose.yml

# Restore previous Dockerfiles
git checkout HEAD~1 docker/*/Dockerfile

# Rebuild with previous configuration
docker compose build
docker compose up -d
```

## Detailed Rollback Procedures

### A. Python Import Issues (PYTHONPATH)

**Symptoms:**
- Import errors in service logs
- Services failing to start
- Health checks reporting import failures

**Rollback Steps:**
1. Check current PYTHONPATH configuration:
   ```bash
   docker compose exec api env | grep PYTHONPATH
   ```

2. Remove PYTHONPATH from Dockerfile if causing issues:
   ```bash
   # Edit affected Dockerfiles
   vim docker/api/Dockerfile
   # Remove or modify ENV PYTHONPATH line
   ```

3. Rebuild affected containers:
   ```bash
   docker compose build api worker
   docker compose up -d api worker
   ```

4. Verify services are running:
   ```bash
   docker compose ps
   docker compose logs -f api worker
   ```

### B. Service Dependency Failures

**Symptoms:**
- Services unable to connect to dependencies
- Health checks failing for dependent services
- Timeout errors in logs

**Rollback Steps:**
1. Check service dependencies:
   ```bash
   docker compose logs -f --tail=100 [service-name]
   ```

2. Restore previous service configuration:
   ```bash
   git checkout HEAD~1 app/[service-name]/
   docker compose build [service-name]
   docker compose up -d [service-name]
   ```

3. Verify connectivity:
   ```bash
   docker compose exec [service-name] curl http://[dependency]:port/health
   ```

### C. Database Migration Rollback

**Symptoms:**
- Database schema incompatible with application
- Migration failures during startup
- Data integrity issues

**Rollback Steps:**
1. Stop affected services:
   ```bash
   docker compose stop api worker
   ```

2. Connect to database:
   ```bash
   docker compose exec postgres psql -U postgres -d ai_workflow_engine
   ```

3. Rollback migration (if using Alembic):
   ```sql
   -- Check current migration
   SELECT * FROM alembic_version;
   
   -- Manually update to previous version
   UPDATE alembic_version SET version_num = 'previous_version_id';
   ```

4. Restore database backup if available:
   ```bash
   docker compose exec postgres pg_restore -U postgres -d ai_workflow_engine /backup/latest.dump
   ```

5. Restart services:
   ```bash
   docker compose up -d api worker
   ```

### D. SSL/TLS Certificate Issues

**Symptoms:**
- HTTPS not working
- Certificate validation errors
- Caddy failing to start

**Rollback Steps:**
1. Check Caddy logs:
   ```bash
   docker compose logs -f caddy_reverse_proxy
   ```

2. Restore previous Caddy configuration:
   ```bash
   git checkout HEAD~1 docker/caddy_reverse_proxy/Caddyfile
   docker compose restart caddy_reverse_proxy
   ```

3. Clear certificate cache if needed:
   ```bash
   docker volume rm ai_workflow_engine_caddy_data
   docker volume rm ai_workflow_engine_caddy_config
   docker compose up -d caddy_reverse_proxy
   ```

### E. Complete System Rollback

**Emergency Full Rollback:**
```bash
# 1. Stop all services
docker compose down

# 2. Restore from git tag or commit
git checkout [last-known-good-tag]

# 3. Clean Docker system
docker system prune -f
docker volume prune -f  # WARNING: This removes data

# 4. Rebuild everything
docker compose build
docker compose up -d

# 5. Verify system health
./scripts/health_check.sh
```

## Blue-Green Deployment Rollback

If using blue-green deployment:

```bash
# Switch back to blue environment
export DEPLOYMENT_ENV=blue
docker compose -f docker-compose.blue.yml up -d

# Stop green environment
docker compose -f docker-compose.green.yml down
```

## Backup and Recovery

### Creating Backups Before Changes
```bash
# Backup database
docker compose exec postgres pg_dump -U postgres ai_workflow_engine > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup volumes
docker run --rm -v ai_workflow_engine_postgres_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/postgres_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Backup configuration
tar czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz docker/ app/*/Dockerfile
```

### Restoring from Backups
```bash
# Restore database
docker compose exec -T postgres psql -U postgres ai_workflow_engine < backup_20240815_120000.sql

# Restore volumes
docker run --rm -v ai_workflow_engine_postgres_data:/data -v $(pwd)/backups:/backup alpine tar xzf /backup/postgres_data_20240815_120000.tar.gz -C /data

# Restore configuration
tar xzf config_backup_20240815_120000.tar.gz
docker compose build
docker compose up -d
```

## Monitoring During Rollback

Monitor the rollback process:
```bash
# Watch service status
watch docker compose ps

# Monitor logs
docker compose logs -f --tail=100

# Check health endpoints
for service in api worker perception-service memory-service reasoning-service; do
  echo "Checking $service..."
  curl -s http://localhost:$(docker compose port $service 8000 | cut -d: -f2)/health | jq .
done
```

## Post-Rollback Verification

After rollback, verify:
1. All services are running: `docker compose ps`
2. Health checks are passing: `curl http://localhost/health`
3. No import errors in logs: `docker compose logs | grep -i "import"`
4. Database connectivity: `docker compose exec api python -c "from app.database import engine; print('DB OK')"`
5. External access working: `curl https://aiwfe.com/health`

## Contact Information

For critical issues requiring immediate assistance:
- Infrastructure Team: [contact info]
- On-call Engineer: [pager duty]
- Escalation: [management contact]

## Lessons Learned Log

Document all rollback events:
- Date/Time:
- Issue Description:
- Rollback Method Used:
- Time to Recovery:
- Root Cause:
- Prevention Measures: