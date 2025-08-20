# Deployment Workflow Scripts

This guide covers production deployment workflows, security hardening, and maintenance operations for the AI Workflow Engine.

## 🚀 Production Deployment Overview

### Pre-Deployment Checklist
- [ ] Security infrastructure configured
- [ ] SSL certificates generated and validated
- [ ] Database migrations tested
- [ ] Performance optimizations applied
- [ ] Monitoring systems configured
- [ ] Backup strategy implemented
- [ ] Security monitoring enabled

### Deployment Architecture
```
Internet → Caddy (Reverse Proxy + SSL) → API/WebUI Services
                                       ↓
                     Database Layer (PostgreSQL + PgBouncer)
                                       ↓
                     Storage Layer (Redis + Qdrant + Ollama)
                                       ↓
                     Monitoring (Prometheus + Grafana)
```

---

## 🛡️ Security-First Deployment

### Step 1: Security Infrastructure Setup
```bash
# 1. Generate production mTLS infrastructure
./scripts/security/setup_mtls_infrastructure.sh setup

# 2. Validate security implementation
./scripts/security/validate_security_implementation.sh

# 3. Deploy security enhancements
./scripts/deploy_security_enhancements.sh

# 4. Validate SSL configuration
./scripts/validate_ssl_configuration.sh --verbose

# 5. Setup security monitoring
./scripts/validate_security_monitoring.sh
```

### Step 2: Certificate Management
```bash
# Production certificate deployment
./scripts/security/setup_mtls_infrastructure.sh generate-all

# Validate certificate chain
./scripts/security/setup_mtls_infrastructure.sh validate

# Check certificate expiration
for cert in certs/*/unified-cert.pem; do
    ./scripts/security/setup_mtls_infrastructure.sh info "$cert"
done

# Setup certificate rotation (if needed)
./scripts/security/rotate_certificates.sh
```

---

## 🏗️ Production Deployment Process

### Standard Production Deployment
```bash
# 1. Initial setup with production optimizations
./scripts/_setup.sh --no-cache

# 2. Deploy security enhancements
./scripts/deploy_security_enhancements.sh

# 3. Deploy performance optimizations
./scripts/deploy_performance_optimizations.sh

# 4. Deploy SSL fixes
./scripts/deploy_ssl_fixes.sh

# 5. Start production stack
./run.sh --build

# 6. Validate deployment
./scripts/_check_stack_health.sh
```

### Server-Specific Deployment  
```bash
# 1. Server setup and hardening
./scripts/_setup_server.sh

# 2. Configure client access
./scripts/_setup_client_access.sh

# 3. Setup remote access (if needed)
./scripts/_setup_remote_access.sh

# 4. Configure mTLS for clients
./scripts/configure_mtls_client.sh
```

---

## 📈 Performance Deployment Scripts

### scripts/deploy_performance_optimizations.sh
**Purpose:** Applies production performance optimizations across all services.

**Optimizations Applied:**
```bash
# Database Optimizations
- Connection pool tuning
- Query optimization settings
- Index creation and maintenance
- Memory allocation optimization

# Cache Optimizations  
- Redis memory policy configuration
- Cache warming strategies
- Connection pool optimization
- Persistence settings

# Application Optimizations
- Worker process scaling
- Resource limit adjustments
- JIT compilation settings
- Memory management tuning

# Network Optimizations
- Keep-alive settings
- Buffer size optimization
- Compression configuration
- Load balancing setup
```

**Usage:**
```bash
./scripts/deploy_performance_optimizations.sh [--service <name>] [--validate]
```

**Validation:**
```bash
# Apply and validate performance optimizations
./scripts/deploy_performance_optimizations.sh --validate

# Monitor performance impact
./scripts/_container_inspector.sh

# Check resource usage
docker stats --no-stream
```

---

## 🔒 Security Deployment Scripts

### scripts/deploy_security_enhancements.sh  
**Purpose:** Implements comprehensive security hardening for production.

**Security Enhancements:**
```bash
# Access Control
- mTLS client authentication
- API key management
- Role-based access control
- Session security policies

# Network Security
- Firewall rule implementation
- Network segmentation
- Intrusion detection setup
- DDoS protection

# Data Security
- Encryption at rest
- Secure communication channels
- Key rotation policies
- Backup encryption

# Monitoring Security
- Security event logging
- Anomaly detection
- Audit trail implementation
- Compliance reporting
```

**Implementation:**
```bash
# Deploy all security enhancements
./scripts/deploy_security_enhancements.sh

# Validate security deployment
./scripts/security/validate_security_implementation.sh

# Monitor security events
tail -f logs/security_audit.log
```

### scripts/deploy_security_migration.sh
**Purpose:** Migrates existing deployments to enhanced security model.

**Migration Process:**
1. **Backup:** Creates complete system backup
2. **Assessment:** Evaluates current security posture
3. **Planning:** Generates migration plan
4. **Implementation:** Applies security enhancements
5. **Validation:** Verifies security improvements
6. **Monitoring:** Enables enhanced monitoring

---

## 🌐 SSL/TLS Deployment

### scripts/deploy_ssl_fixes.sh
**Purpose:** Deploys comprehensive SSL/TLS fixes and improvements.

**SSL Enhancements:**
```bash
# Certificate Management
- Automated certificate deployment
- Certificate chain validation
- Expiration monitoring setup
- Rotation schedule configuration

# Protocol Security
- TLS version enforcement (minimum TLS 1.2)
- Cipher suite optimization
- Perfect Forward Secrecy
- HSTS implementation

# Performance Optimization
- OCSP stapling
- Session resumption
- Certificate caching
- Connection keep-alive

# Compliance
- Certificate transparency
- CAA record validation
- Security header implementation
- Vulnerability scanning
```

**Deployment Process:**
```bash
# Deploy SSL fixes
./scripts/deploy_ssl_fixes.sh

# Validate SSL configuration
./scripts/validate_ssl_configuration.sh

# Test SSL endpoints
python ./scripts/validate_ssl_fix.py --fix-issues

# Generate SSL validation report
./scripts/validate_ssl_configuration.sh --verbose > ssl_validation_report.txt
```

---

## 🔄 Database Migration Deployment

### Production Database Migrations
```bash
# 1. Backup database before migration
docker exec postgres pg_dump -U app_user ai_workflow_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Test migration in staging
python ./scripts/migrate_check.py

# 3. Apply migration with monitoring
python ./scripts/run_migrations.py 2>&1 | tee migration_$(date +%Y%m%d_%H%M%S).log

# 4. Validate migration success
python ./scripts/migrate_check.py

# 5. Post-migration cleanup
./scripts/post_startup_fixes.sh
```

### User Data Migration
```bash
# Migrate user passwords to new format
./scripts/migrate_user_passwords.sh

# Populate system data
python ./scripts/populate_system_prompts.py

# Seed initial production data
python ./scripts/seed_initial_data.py

# Create production admin user
./scripts/create_admin.sh
```

---

## 📊 Monitoring Deployment

### Production Monitoring Setup
```bash
# 1. Deploy monitoring infrastructure
# Monitoring is included in main deployment

# 2. Configure monitoring services
# Edit config/prometheus/prometheus.yml
# Edit config/grafana/grafana.ini

# 3. Validate monitoring
curl -k https://localhost:9090/api/v1/status/config
curl -k https://localhost:3000/api/health

# 4. Setup alerting
./scripts/validate_security_monitoring.sh

# 5. Test alert delivery
# Configure alert channels in Grafana
```

### Log Management Deployment
```bash
# Enable comprehensive logging
./scripts/_comprehensive_logger.sh &

# Configure log rotation
./scripts/_log_rotator.sh &

# Setup log forwarding (if needed)
# Configure external log aggregation
```

---

## 🔄 Rolling Updates and Zero-Downtime Deployment

### Service Update Strategy
```bash
# 1. Update individual services
update_service() {
    local service="$1"
    
    # Build new image
    docker compose build --no-cache "$service"
    
    # Rolling update
    docker compose up -d --no-deps "$service"
    
    # Health check
    wait_for_service_health "$service"
    
    # Validate functionality
    ./scripts/_check_stack_health.sh
}

# 2. Update sequence for minimal downtime
update_service "worker"      # Background service first
update_service "api"         # API service
update_service "webui"       # Frontend last
```

### Certificate Rotation (Zero Downtime)
```bash
# Rotate certificates without service interruption
./scripts/security/setup_mtls_infrastructure.sh rotate-all

# Validate new certificates
./scripts/security/validate_security_implementation.sh

# Test connectivity
./scripts/validate_ssl_configuration.sh
```

---

## 🔒 Production Security Hardening

### System Hardening Checklist
```bash
# Network Security
- [ ] Firewall configured (only necessary ports open)
- [ ] mTLS enabled for all inter-service communication
- [ ] API rate limiting configured
- [ ] DDoS protection enabled

# Access Control
- [ ] Default passwords changed
- [ ] API keys rotated
- [ ] User roles properly configured
- [ ] Admin access restricted

# Data Security
- [ ] Encryption at rest enabled
- [ ] Secure backup strategy implemented
- [ ] Key rotation schedule established
- [ ] Audit logging enabled

# Monitoring
- [ ] Security monitoring active
- [ ] Log aggregation configured  
- [ ] Alert delivery tested
- [ ] Incident response plan ready
```

### Security Validation Commands
```bash
# Complete security audit
./scripts/security/validate_security_implementation.sh > security_audit_$(date +%Y%m%d).txt

# SSL/TLS security scan
./scripts/validate_ssl_configuration.sh --verbose > ssl_security_scan.txt

# Certificate validation
./scripts/security/setup_mtls_infrastructure.sh validate

# Security monitoring test
./scripts/validate_security_monitoring.sh
```

---

## 📋 Production Maintenance

### Regular Maintenance Tasks
```bash
# Daily maintenance
./scripts/auto_update.sh --security-only
./scripts/_log_rotator.sh
./scripts/_check_stack_health.sh

# Weekly maintenance  
./scripts/security/setup_mtls_infrastructure.sh validate
docker system prune -f
./scripts/deploy_performance_optimizations.sh --validate

# Monthly maintenance
./scripts/security/rotate_certificates.sh
./scripts/auto_update.sh --full
# Database maintenance (VACUUM, ANALYZE)
```

### Backup and Recovery
```bash
# Create system backup
backup_system() {
    local backup_date=$(date +%Y%m%d_%H%M%S)
    
    # Database backup
    docker exec postgres pg_dump -U app_user ai_workflow_db > "backup_db_${backup_date}.sql"
    
    # Secrets backup
    tar -czf "backup_secrets_${backup_date}.tar.gz" secrets/
    
    # Certificates backup
    tar -czf "backup_certs_${backup_date}.tar.gz" certs/
    
    # Configuration backup
    tar -czf "backup_config_${backup_date}.tar.gz" config/
    
    echo "Backup completed: ${backup_date}"
}
```

---

## 🔍 Production Monitoring and Alerting

### Health Monitoring
```bash
# Continuous health monitoring
./scripts/_check_stack_health.sh

# Performance monitoring
./scripts/_container_inspector.sh

# Security monitoring
./scripts/validate_security_monitoring.sh

# Real-time error monitoring
./scripts/_realtime_error_monitor.sh &
```

### Alert Configuration
```bash
# Configure Prometheus alerts
# Edit config/prometheus/alert_rules.yml

# Configure Grafana notifications
# Setup notification channels in Grafana UI

# Test alert delivery
# Trigger test alerts to verify delivery
```

---

## 🚀 Deployment Validation

### Post-Deployment Validation Checklist
```bash
# 1. Service Health
./scripts/_check_stack_health.sh

# 2. SSL/TLS Validation
./scripts/validate_ssl_configuration.sh

# 3. Security Validation
./scripts/security/validate_security_implementation.sh

# 4. Database Validation
python ./scripts/migrate_check.py

# 5. Performance Validation
./scripts/_container_inspector.sh

# 6. Monitoring Validation
curl -k https://localhost:9090/api/v1/status/config
curl -k https://localhost:3000/api/health

# 7. End-to-end Testing
python ./scripts/test_webui_playwright.py
python ./scripts/test_webui_ssl.py
```

### Deployment Success Criteria
- [ ] All services running and healthy
- [ ] SSL/TLS certificates valid and properly configured
- [ ] Database migrations applied successfully
- [ ] Security monitoring active
- [ ] Performance metrics within acceptable ranges
- [ ] End-to-end tests passing
- [ ] Monitoring and alerting functional

---

## 🔄 Rollback Procedures

### Emergency Rollback
```bash
# Quick rollback to previous version
rollback_deployment() {
    # Stop current deployment
    docker compose down
    
    # Restore from backup
    # (Implementation depends on backup strategy)
    
    # Start previous version
    docker compose up -d
    
    # Validate rollback
    ./scripts/_check_stack_health.sh
}
```

### Selective Service Rollback
```bash
# Rollback specific service
rollback_service() {
    local service="$1"
    local backup_tag="$2"
    
    # Tag current image for potential re-rollback
    docker tag "${service}:latest" "${service}:pre-rollback"
    
    # Rollback to backup version
    docker tag "${service}:${backup_tag}" "${service}:latest"
    
    # Restart service
    docker compose up -d --no-deps "$service"
    
    # Validate
    ./scripts/_check_stack_health.sh
}
```

---

## 📊 Production Monitoring Dashboard

### Key Metrics to Monitor
```bash
# System Health
- Service availability and response times
- Resource utilization (CPU, memory, disk)
- Network connectivity and throughput
- Error rates and failure patterns

# Security Metrics
- Authentication success/failure rates
- Certificate expiration dates
- Security event frequency
- Access pattern anomalies

# Performance Metrics
- Database query performance
- API response times
- Cache hit rates
- User session duration

# Business Metrics
- User activity levels
- Feature usage statistics
- System capacity utilization
- Cost optimization opportunities
```

---

## 🎯 Production Best Practices

### Deployment Strategy
1. **Blue-Green Deployment:** Maintain parallel environments
2. **Canary Releases:** Gradual rollout to subset of users
3. **Feature Flags:** Control feature availability
4. **Database Migrations:** Always backward compatible
5. **Monitoring First:** Deploy monitoring before application

### Security Best Practices
1. **Defense in Depth:** Multiple security layers
2. **Principle of Least Privilege:** Minimal necessary access
3. **Regular Security Audits:** Automated and manual reviews
4. **Incident Response Plan:** Prepared response procedures
5. **Security Training:** Team security awareness

### Operational Excellence
1. **Infrastructure as Code:** Reproducible deployments
2. **Automated Testing:** Comprehensive test coverage
3. **Continuous Monitoring:** Real-time system awareness
4. **Documentation:** Up-to-date operational procedures
5. **Disaster Recovery:** Tested recovery procedures

---

*For development workflows, see [Development Workflow](./development.md).  
For troubleshooting production issues, see [Troubleshooting Guide](./troubleshooting.md).*