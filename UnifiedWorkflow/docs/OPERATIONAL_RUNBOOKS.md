# AI Workflow Engine - Operational Runbooks

## 📚 Runbook Overview

This comprehensive operational guide provides step-by-step procedures for deploying, monitoring, troubleshooting, and maintaining the AI Workflow Engine. All procedures are designed for production environments with emphasis on zero-downtime operations and system reliability.

**Target Audience**: DevOps Engineers, Site Reliability Engineers, System Administrators  
**Last Updated**: August 6, 2025  
**System Version**: 1.0.0

---

## 🚀 DEPLOYMENT RUNBOOKS

### 1. Initial System Deployment

#### Prerequisites Checklist

**Infrastructure Requirements**:
- [ ] Linux server (Ubuntu 20.04+ or CentOS 8+)
- [ ] Docker 20.10+ installed and running
- [ ] Docker Compose 2.0+ available
- [ ] Minimum 8GB RAM, 4 CPU cores, 50GB storage
- [ ] Network connectivity for external integrations
- [ ] SSL certificate for HTTPS (Let's Encrypt or custom)

**Access Requirements**:
- [ ] Root or sudo access to deployment server
- [ ] Git repository access credentials
- [ ] Google Cloud credentials (for Google services integration)
- [ ] Domain name configured (if using custom domain)

**Environment Setup**:
```bash
# Create deployment directory
sudo mkdir -p /opt/ai-workflow-engine
cd /opt/ai-workflow-engine

# Clone repository
git clone https://github.com/your-org/ai-workflow-engine.git .

# Set proper permissions
sudo chown -R $(id -u):$(id -g) /opt/ai-workflow-engine
```

#### Step-by-Step Deployment

**Step 1: Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables**:
```bash
# Database Configuration
POSTGRES_DB=ai_workflow_engine
POSTGRES_USER=aiworkflow
POSTGRES_PASSWORD=secure_random_password_here
DATABASE_URL=postgresql://aiworkflow:secure_random_password_here@postgres:5432/ai_workflow_engine

# Redis Configuration  
REDIS_URL=redis://redis:6379

# JWT Configuration
JWT_SECRET_KEY=generate_secure_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google Services (Optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_API_KEY=your_google_api_key

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Application Settings
ENVIRONMENT=production
DOMAIN=yourdomain.com
LOG_LEVEL=INFO
```

**Step 2: SSL Certificate Setup**
```bash
# For Let's Encrypt (recommended)
sudo apt update && sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to Caddy directory
sudo mkdir -p ./config/caddy/certs
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./config/caddy/certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./config/caddy/certs/
sudo chown -R 1000:1000 ./config/caddy/certs
```

**Step 3: Docker Secrets Setup**
```bash
# Create secrets directory
mkdir -p ./secrets

# Generate secure secrets
echo "$(openssl rand -base64 32)" > ./secrets/jwt_secret.txt
echo "$(openssl rand -base64 16)" > ./secrets/db_password.txt
echo "your_google_api_key" > ./secrets/google_api_key.txt

# Set proper permissions
chmod 600 ./secrets/*.txt
```

**Step 4: Database Initialization**
```bash
# Start PostgreSQL first for initialization
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 30

# Run database migrations
docker-compose run --rm api python -m alembic upgrade head

# Verify database setup
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine -c "\dt"
```

**Step 5: Service Deployment**
```bash
# Build and deploy all services
docker-compose build --no-cache
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Check service health
curl -k https://localhost/api/v1/health
```

**Step 6: Post-Deployment Verification**
```bash
# Test API endpoints
curl -k https://localhost/api/v1/health
curl -k https://localhost/public/status

# Test WebUI access
curl -I -k https://localhost/

# Check logs for errors
docker-compose logs --tail=50 api
docker-compose logs --tail=50 webui
docker-compose logs --tail=50 worker
```

#### Deployment Verification Checklist

**System Health Checks**:
- [ ] All 8 containers running (webui, caddy, api, worker, postgres, pgbouncer, redis, qdrant)
- [ ] Health endpoint returns 200 OK
- [ ] Database migrations completed successfully
- [ ] WebUI accessible via HTTPS
- [ ] No critical errors in container logs

**Functional Verification**:
- [ ] User registration works
- [ ] User login successful
- [ ] JWT token generation functional
- [ ] Database queries executing
- [ ] Redis cache operational
- [ ] Worker tasks processing

### 2. Rolling Updates and Deployments

#### Zero-Downtime Update Procedure

**Step 1: Pre-Update Preparation**
```bash
# Create backup before update
./scripts/backup.sh

# Pull latest changes
git fetch origin
git checkout main
git pull origin main

# Review changes
git log --oneline HEAD~10..HEAD

# Test configuration
docker-compose config
```

**Step 2: Database Migrations (if required)**
```bash
# Check for pending migrations
docker-compose run --rm api python -m alembic current
docker-compose run --rm api python -m alembic history

# Apply migrations (if any)
docker-compose run --rm api python -m alembic upgrade head
```

**Step 3: Rolling Service Updates**
```bash
# Update worker services first (background tasks)
docker-compose build worker
docker-compose up -d --no-deps worker

# Wait and verify worker health
sleep 30
docker-compose logs --tail=20 worker

# Update API services
docker-compose build api
docker-compose up -d --no-deps api

# Verify API health
curl -k https://localhost/api/v1/health

# Update WebUI (frontend)
docker-compose build webui
docker-compose up -d --no-deps webui

# Verify WebUI accessibility
curl -I -k https://localhost/
```

**Step 4: Post-Update Verification**
```bash
# Full system health check
./scripts/health-check.sh

# Monitor error rates
docker-compose logs -f --tail=100

# Verify key functionality
curl -k https://localhost/api/v1/health
```

#### Rollback Procedure

**Emergency Rollback Steps**:
```bash
# Immediate rollback to previous version
git log --oneline -n 5
PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
git checkout $PREVIOUS_COMMIT

# Quick rebuild and deploy
docker-compose build --no-cache
docker-compose up -d

# Rollback database migrations (if necessary)
docker-compose run --rm api python -m alembic downgrade -1

# Verify system functionality
./scripts/health-check.sh
```

### 3. Multi-Environment Deployments

#### Development Environment
```bash
# Development-specific configuration
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export CORS_ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

# Deploy with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

#### Staging Environment
```bash
# Staging-specific configuration
export ENVIRONMENT=staging
export LOG_LEVEL=INFO
export DATABASE_URL=postgresql://user:pass@staging-db:5432/ai_workflow_staging

# Deploy with staging overrides
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Run integration tests
./scripts/run-integration-tests.sh
```

#### Production Environment
```bash
# Production-specific configuration
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export ENABLE_MONITORING=true

# Deploy with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Enable production monitoring
./scripts/setup-monitoring.sh
```

---

## 📊 MONITORING RUNBOOKS

### 1. Health Monitoring Setup

#### Prometheus Configuration

**Step 1: Deploy Monitoring Stack**
```bash
# Create monitoring directory
mkdir -p ./monitoring/{prometheus,grafana,alertmanager}

# Deploy monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

# Verify monitoring services
curl http://localhost:9090  # Prometheus
curl http://localhost:3001  # Grafana
```

**Step 2: Configure Data Sources**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-workflow-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
      
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

**Step 3: Import Grafana Dashboards**
```bash
# Import pre-built dashboards
curl -X POST \
  http://admin:admin@localhost:3001/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @./monitoring/dashboards/ai-workflow-dashboard.json
```

#### Health Check Scripts

**Comprehensive Health Check Script** (`scripts/health-check.sh`):
```bash
#!/bin/bash
set -e

echo "=== AI Workflow Engine Health Check ==="
echo "Timestamp: $(date)"

# Check container health
echo "Checking container status..."
docker-compose ps

# Check API health
echo "Testing API health..."
API_HEALTH=$(curl -s -k https://localhost/api/v1/health | jq -r '.status // "error"')
if [ "$API_HEALTH" = "ok" ]; then
    echo "✅ API Health: OK"
else
    echo "❌ API Health: FAILED - $API_HEALTH"
    exit 1
fi

# Check database connectivity
echo "Testing database connectivity..."
DB_STATUS=$(docker-compose exec -T postgres pg_isready -U aiworkflow)
if echo "$DB_STATUS" | grep -q "accepting connections"; then
    echo "✅ Database: OK"
else
    echo "❌ Database: FAILED"
    exit 1
fi

# Check Redis connectivity
echo "Testing Redis connectivity..."
REDIS_STATUS=$(docker-compose exec -T redis redis-cli ping)
if [ "$REDIS_STATUS" = "PONG" ]; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAILED"
    exit 1
fi

# Check WebUI accessibility
echo "Testing WebUI accessibility..."
WEBUI_STATUS=$(curl -s -I -k https://localhost/ | head -n 1 | grep -o "200\|301\|302")
if [ -n "$WEBUI_STATUS" ]; then
    echo "✅ WebUI: OK"
else
    echo "❌ WebUI: FAILED"
    exit 1
fi

# Check worker queue
echo "Testing worker queue..."
QUEUE_LENGTH=$(docker-compose exec -T redis redis-cli llen celery)
echo "📋 Queue length: $QUEUE_LENGTH"

# Check disk usage
echo "Checking disk usage..."
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo "✅ Disk usage: ${DISK_USAGE}%"
else
    echo "⚠️  Disk usage high: ${DISK_USAGE}%"
fi

# Check memory usage
echo "Checking memory usage..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -lt 90 ]; then
    echo "✅ Memory usage: ${MEMORY_USAGE}%"
else
    echo "⚠️  Memory usage high: ${MEMORY_USAGE}%"
fi

echo "=== Health Check Complete ==="
```

#### Automated Monitoring Alerts

**AlertManager Configuration**:
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@yourdomain.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'admin@yourdomain.com'
        subject: 'AI Workflow Engine Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
    
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'AI Workflow Engine Alert'
        text: '{{ .CommonAnnotations.summary }}'
```

**Prometheus Alert Rules**:
```yaml
# alerts.yml
groups:
  - name: ai_workflow_alerts
    rules:
      - alert: HighCPUUsage
        expr: (100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"
      
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 90
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 90% for more than 3 minutes"
      
      - alert: APIResponseTimeHigh
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high"
          description: "95th percentile response time is above 2 seconds"
      
      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection count"
          description: "PostgreSQL has more than 50 active connections"
      
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} service is not responding"
```

### 2. Log Management

#### Centralized Logging Setup

**ELK Stack Configuration**:
```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    
  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./config/logstash:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

**Log Rotation Configuration**:
```bash
# /etc/logrotate.d/ai-workflow-engine
/var/log/ai-workflow-engine/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
    postrotate
        docker-compose restart api worker 2>/dev/null || true
    endscript
}
```

#### Log Analysis Scripts

**Error Analysis Script** (`scripts/analyze-errors.sh`):
```bash
#!/bin/bash

echo "=== AI Workflow Engine Error Analysis ==="
echo "Period: Last 24 hours"

# API errors
echo "API Errors:"
docker-compose logs --since 24h api 2>&1 | grep -i error | tail -20

# Worker errors  
echo -e "\nWorker Errors:"
docker-compose logs --since 24h worker 2>&1 | grep -i error | tail -20

# Database errors
echo -e "\nDatabase Errors:"  
docker-compose logs --since 24h postgres 2>&1 | grep -i error | tail -20

# High-frequency error patterns
echo -e "\nTop Error Patterns:"
docker-compose logs --since 24h 2>&1 | grep -i error | \
    sed 's/.*ERROR/ERROR/' | sort | uniq -c | sort -rn | head -10
```

### 3. Performance Monitoring

#### Real-Time Performance Dashboard

**Performance Monitoring Script** (`scripts/performance-monitor.sh`):
```bash
#!/bin/bash

while true; do
    clear
    echo "=== AI Workflow Engine Performance Monitor ==="
    echo "Updated: $(date)"
    echo
    
    # System resources
    echo "SYSTEM RESOURCES:"
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"
    echo
    
    # Container stats
    echo "CONTAINER STATS:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    echo
    
    # API performance
    echo "API PERFORMANCE:"
    API_RESPONSE=$(curl -s -w "%{time_total}" -k https://localhost/api/v1/health -o /dev/null)
    echo "Health endpoint response time: ${API_RESPONSE}s"
    
    # Database performance
    echo -e "\nDATABASE PERFORMANCE:"
    DB_CONNECTIONS=$(docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -t -c "SELECT count(*) FROM pg_stat_activity;")
    echo "Active connections: $DB_CONNECTIONS"
    
    # Queue status
    echo -e "\nWORKER QUEUE STATUS:"
    QUEUE_LENGTH=$(docker-compose exec -T redis redis-cli llen celery 2>/dev/null || echo "N/A")
    echo "Pending tasks: $QUEUE_LENGTH"
    
    sleep 10
done
```

---

## 🔧 MAINTENANCE RUNBOOKS

### 1. Database Maintenance

#### Daily Database Maintenance

**Automated Maintenance Script** (`scripts/db-maintenance.sh`):
```bash
#!/bin/bash
set -e

echo "=== Database Maintenance Started ==="
echo "Date: $(date)"

# Create backup
echo "Creating backup..."
docker-compose exec -T postgres pg_dump -U aiworkflow ai_workflow_engine | gzip > "backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# Analyze database statistics
echo "Updating database statistics..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "ANALYZE;"

# Vacuum database
echo "Vacuuming database..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "VACUUM ANALYZE;"

# Check database size
echo "Database size:"
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT pg_size_pretty(pg_database_size('ai_workflow_engine')) AS database_size;
"

# Check table sizes
echo "Largest tables:"
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables 
    WHERE schemaname = 'public' 
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
    LIMIT 10;
"

echo "=== Database Maintenance Complete ==="
```

#### Database Backup and Restore

**Backup Script** (`scripts/backup.sh`):
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/ai-workflow-engine/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Creating full system backup..."

# Database backup
echo "Backing up PostgreSQL database..."
docker-compose exec -T postgres pg_dump -U aiworkflow ai_workflow_engine | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Redis backup
echo "Backing up Redis data..."
docker-compose exec -T redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Qdrant backup
echo "Backing up Qdrant data..."
docker-compose exec -T qdrant tar -czf /tmp/qdrant_backup.tar.gz /qdrant/storage
docker cp $(docker-compose ps -q qdrant):/tmp/qdrant_backup.tar.gz "$BACKUP_DIR/qdrant_$DATE.tar.gz"

# Configuration backup
echo "Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env docker-compose.yml config/

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "*.gz" -o -name "*.rdb" | head -n -30 | xargs rm -f

echo "Backup completed: $BACKUP_DIR"
ls -lh $BACKUP_DIR/*$DATE*
```

**Restore Script** (`scripts/restore.sh`):
```bash
#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_date>"
    echo "Available backups:"
    ls backups/ | grep -E '_(20[0-9]{2}[0-9]{4}_[0-9]{6})\.' | cut -d'_' -f2-3 | sort -u
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/opt/ai-workflow-engine/backups"

echo "Restoring system from backup date: $BACKUP_DATE"

# Stop services
echo "Stopping services..."
docker-compose down

# Restore database
if [ -f "$BACKUP_DIR/postgres_$BACKUP_DATE.sql.gz" ]; then
    echo "Restoring PostgreSQL database..."
    docker-compose up -d postgres
    sleep 30
    zcat "$BACKUP_DIR/postgres_$BACKUP_DATE.sql.gz" | docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine
fi

# Restore Redis
if [ -f "$BACKUP_DIR/redis_$BACKUP_DATE.rdb" ]; then
    echo "Restoring Redis data..."
    docker cp "$BACKUP_DIR/redis_$BACKUP_DATE.rdb" $(docker-compose ps -q redis):/data/dump.rdb
fi

# Restore Qdrant
if [ -f "$BACKUP_DIR/qdrant_$BACKUP_DATE.tar.gz" ]; then
    echo "Restoring Qdrant data..."
    docker cp "$BACKUP_DIR/qdrant_$BACKUP_DATE.tar.gz" $(docker-compose ps -q qdrant):/tmp/
    docker-compose exec -T qdrant tar -xzf /tmp/qdrant_backup.tar.gz -C /
fi

# Start all services
echo "Starting all services..."
docker-compose up -d

echo "Restore completed. Verifying system health..."
sleep 60
./scripts/health-check.sh
```

### 2. Security Maintenance

#### Security Scanning and Updates

**Security Scan Script** (`scripts/security-scan.sh`):
```bash
#!/bin/bash

echo "=== Security Scan Started ==="

# Container vulnerability scanning
echo "Scanning container vulnerabilities..."
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image ai-workflow-engine_api:latest

# Network security scan
echo "Performing network security scan..."
nmap -sV -O localhost

# SSL/TLS certificate check
echo "Checking SSL certificate..."
echo | openssl s_client -connect localhost:443 2>/dev/null | openssl x509 -noout -dates

# Permission audit
echo "Auditing file permissions..."
find /opt/ai-workflow-engine -type f -perm -002 -exec ls -l {} \;

# Check for security updates
echo "Checking for security updates..."
python3 scripts/security_validation.py

echo "=== Security Scan Complete ==="
```

#### Certificate Renewal

**Automated Certificate Renewal** (`scripts/renew-certs.sh`):
```bash
#!/bin/bash
set -e

echo "=== Certificate Renewal Process ==="

# Backup current certificates
cp -r config/caddy/certs config/caddy/certs.backup.$(date +%Y%m%d)

# Renew Let's Encrypt certificate
certbot renew --quiet

# Copy new certificates
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem config/caddy/certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem config/caddy/certs/

# Restart Caddy to load new certificates
docker-compose restart caddy

# Verify new certificate
sleep 10
openssl x509 -in config/caddy/certs/fullchain.pem -noout -dates

echo "Certificate renewal completed successfully"
```

### 3. Performance Optimization

#### Database Performance Tuning

**Database Optimization Script** (`scripts/optimize-database.sh`):
```bash
#!/bin/bash

echo "=== Database Performance Optimization ==="

# Update PostgreSQL statistics
echo "Updating database statistics..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "ANALYZE;"

# Check for missing indexes
echo "Checking for missing indexes..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT schemaname, tablename, attname, n_distinct, correlation 
    FROM pg_stats 
    WHERE schemaname = 'public' 
    AND n_distinct > 100 
    AND correlation < 0.1;
"

# Identify slow queries
echo "Identifying slow queries..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT query, mean_time, calls 
    FROM pg_stat_statements 
    WHERE mean_time > 1000 
    ORDER BY mean_time DESC 
    LIMIT 10;
"

# Check table bloat
echo "Checking table bloat..."
docker-compose exec -T postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT tablename, n_dead_tup, n_live_tup,
           ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS bloat_percent
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 0
    ORDER BY bloat_percent DESC;
"

echo "Database optimization analysis complete"
```

---

## 🚨 TROUBLESHOOTING RUNBOOKS

### 1. Common Issues and Solutions

#### WebUI Not Accessible

**Symptoms**: Browser cannot connect to WebUI, timeout errors  
**Priority**: CRITICAL

**Diagnosis Steps**:
```bash
# Check container status
docker-compose ps webui

# Check container logs
docker-compose logs webui --tail=50

# Test internal connectivity
docker-compose exec api curl -I http://webui:3000

# Check Caddy configuration
docker-compose exec caddy caddy validate --config /etc/caddy/Caddyfile
```

**Resolution Steps**:
```bash
# Restart WebUI container
docker-compose restart webui

# Rebuild WebUI if necessary
docker-compose build --no-cache webui
docker-compose up -d webui

# Check SvelteKit build
docker-compose exec webui npm run build

# Verify Node.js process
docker-compose exec webui ps aux | grep node
```

#### Database Connection Issues

**Symptoms**: API returns database connection errors  
**Priority**: HIGH

**Diagnosis Steps**:
```bash
# Test database connectivity
docker-compose exec postgres pg_isready -U aiworkflow

# Check connection pool status
docker-compose exec pgbouncer psql -h localhost -p 6432 -U aiworkflow -d pgbouncer -c "SHOW POOLS;"

# Check database logs
docker-compose logs postgres --tail=100
```

**Resolution Steps**:
```bash
# Restart database services
docker-compose restart postgres pgbouncer

# Check database permissions
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine -c "\du"

# Reset connection pool
docker-compose exec pgbouncer psql -h localhost -p 6432 -U aiworkflow -d pgbouncer -c "RELOAD;"
```

#### High CPU Usage

**Symptoms**: System slow, high CPU utilization  
**Priority**: MEDIUM

**Diagnosis Steps**:
```bash
# Check container CPU usage
docker stats --no-stream

# Identify CPU-intensive processes
docker-compose exec api top -p $(docker-compose exec api pgrep -f python)

# Check for resource-intensive queries
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
    FROM pg_stat_activity 
    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"
```

**Resolution Steps**:
```bash
# Scale API instances if needed
docker-compose up -d --scale api=2

# Optimize database queries
./scripts/optimize-database.sh

# Add resource limits
# Edit docker-compose.yml to add resource constraints
docker-compose up -d
```

### 2. Emergency Procedures

#### Complete System Recovery

**Emergency Recovery Checklist**:

**Step 1: Assess Damage**
```bash
# Check what's running
docker ps -a

# Check disk space
df -h

# Check system logs
journalctl -u docker --since "1 hour ago"
```

**Step 2: Emergency Backup**
```bash
# Backup any running data
docker-compose exec postgres pg_dump -U aiworkflow ai_workflow_engine > emergency_backup.sql
docker-compose exec redis redis-cli BGSAVE
```

**Step 3: Full System Restart**
```bash
# Stop all services
docker-compose down --remove-orphans

# Clean up if necessary
docker system prune -f
docker volume prune -f

# Restart system
docker-compose up -d

# Wait and verify
sleep 120
./scripts/health-check.sh
```

**Step 4: Data Recovery**
```bash
# If data loss occurred, restore from backup
./scripts/restore.sh YYYYMMDD_HHMMSS
```

#### Security Incident Response

**Incident Response Procedure**:

**Step 1: Immediate Actions**
```bash
# Block suspicious traffic (if identified)
iptables -A INPUT -s SUSPICIOUS_IP -j DROP

# Rotate JWT secrets
echo "$(openssl rand -base64 32)" > ./secrets/jwt_secret.txt
docker-compose restart api

# Force logout all users
docker-compose exec redis redis-cli FLUSHDB 1
```

**Step 2: Investigation**
```bash
# Collect security logs
docker-compose logs --since "24h" > security_incident_logs.txt

# Check for unauthorized access
docker-compose exec postgres psql -U aiworkflow -d ai_workflow_engine -c "
    SELECT * FROM security_events 
    WHERE created_at > NOW() - INTERVAL '24 hours'
    ORDER BY created_at DESC;
"

# Analyze authentication patterns
grep -i "authentication\|login\|failed" security_incident_logs.txt
```

**Step 3: Containment**
```bash
# Update all passwords
./scripts/rotate-credentials.sh

# Patch security vulnerabilities
./scripts/security-updates.sh

# Enable additional monitoring
./scripts/enhanced-monitoring.sh
```

### 3. Performance Degradation Response

#### Slow Response Times

**Immediate Actions**:
```bash
# Check system resources
./scripts/performance-monitor.sh

# Identify bottlenecks
docker-compose exec api python -m py-spy top -p $(docker-compose exec api pgrep -f "python.*uvicorn")

# Scale critical services
docker-compose up -d --scale api=3 --scale worker=2
```

**Analysis and Resolution**:
```bash
# Database performance analysis
./scripts/db-performance-analysis.sh

# Cache optimization
docker-compose exec redis redis-cli info memory
docker-compose exec redis redis-cli --latency-history

# Application profiling
docker-compose exec api python -m cProfile -o profile.out -m uvicorn main:app
```

---

## 📋 OPERATIONAL CHECKLISTS

### Daily Operations Checklist

**Morning Checks** (10 minutes):
- [ ] Run health check script
- [ ] Review overnight logs for errors
- [ ] Check system resource usage
- [ ] Verify backup completion
- [ ] Check monitoring alerts

**Evening Checks** (5 minutes):
- [ ] Review daily performance metrics
- [ ] Check security events
- [ ] Verify all services running
- [ ] Plan next day maintenance

### Weekly Operations Checklist

**System Maintenance**:
- [ ] Update system packages
- [ ] Rotate log files
- [ ] Clean up old Docker images
- [ ] Review performance trends
- [ ] Test backup restore process

**Security Review**:
- [ ] Check for security updates
- [ ] Review access logs
- [ ] Update SSL certificates if needed
- [ ] Scan for vulnerabilities
- [ ] Review user access patterns

### Monthly Operations Checklist

**Comprehensive Review**:
- [ ] Full security audit
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Disaster recovery testing
- [ ] Documentation updates

**System Upgrades**:
- [ ] Plan system updates
- [ ] Schedule maintenance windows
- [ ] Prepare rollback procedures
- [ ] Coordinate with stakeholders
- [ ] Update monitoring thresholds

---

This comprehensive operational runbook provides all necessary procedures for maintaining a production AI Workflow Engine deployment with emphasis on reliability, security, and performance.