# Troubleshooting Guide

This comprehensive guide helps diagnose and resolve common issues in the AI Workflow Engine using the available scripts and tools.

## 🚨 Emergency Quick Fixes

### System Won't Start
```bash
# 1. Fix permissions first
sudo ./scripts/fix_permissions.sh

# 2. Try soft reset
./run.sh --soft-reset

# 3. If still failing, check logs
cat logs/error_log.txt

# 4. Nuclear option (loses all data)
./run.sh --reset
```

### Permission Denied Errors
```bash
# Fix all permission issues
sudo ./scripts/fix_permissions.sh
./scripts/_make_scripts_executable.sh

# Verify fix
ls -la scripts/ | head -5
```

### Services Won't Start
```bash
# Check service status
docker compose ps

# View detailed logs
docker compose logs <service_name>

# Try universal worker fix
./scripts/worker_universal_fix.sh

# Restart specific services
docker compose restart <service_name>
```

---

## 🔍 Diagnostic Process

### Step 1: Identify the Problem
```bash
# Check overall system health
./scripts/_check_stack_health.sh

# View recent errors
tail -20 logs/error_log.txt

# Check service status
docker compose ps -a

# Find error sources
./scripts/_find_error_source.sh
```

### Step 2: Gather Information
```bash
# Comprehensive error analysis
cat logs/error_log.txt

# Container health inspection
./scripts/_container_inspector.sh

# Real-time error monitoring
tail -f logs/runtime_errors.log

# Docker system information
docker system df
docker system events --since '10m'
```

### Step 3: Apply Targeted Fixes
Based on the problem type, use the appropriate scripts below.

---

## 🐳 Docker and Container Issues

### Container Won't Start
**Symptoms:** Service shows as "exited" or "restarting"

```bash
# Diagnosis
docker compose ps
docker compose logs <service_name>

# Solutions
# 1. Try restart
docker compose restart <service_name>

# 2. Rebuild container
docker compose build --no-cache <service_name>
docker compose up -d <service_name>

# 3. Check resource usage
docker stats
df -h  # Check disk space

# 4. Universal fix
./scripts/worker_universal_fix.sh  # For worker issues
```

### Container Health Check Failures
**Symptoms:** Container shows as "unhealthy" in `docker ps`

```bash
# Diagnosis
docker inspect <container_name> | jq '.[0].State.Health'

# Worker-specific health fixes
./scripts/fix_worker_healthcheck.sh
./scripts/test_worker_healthcheck.sh

# General health validation
./scripts/_check_stack_health.sh
```

### Out of Disk Space
**Symptoms:** "No space left on device" errors

```bash
# Check disk usage
df -h
docker system df

# Clean up Docker
docker system prune -f
docker volume prune -f
docker image prune -a -f

# Check log sizes
du -sh logs/
./scripts/_log_rotator.sh  # Force log rotation
```

### Docker Build Failures
**Symptoms:** Build process fails during `docker compose build`

```bash
# Diagnosis
# Check the build log in logs/error_log.txt

# Solutions
# 1. Clean build
docker compose build --no-cache --pull

# 2. Fix dependency issues
./scripts/lock_dependencies.sh

# 3. Check base images
docker pull python:3.11-slim
docker pull node:18-alpine

# 4. Clear build cache
docker builder prune -a -f
```

---

## 🗄️ Database Issues

### Database Connection Failures
**Symptoms:** "Connection refused", "Authentication failed"

```bash
# Diagnosis
docker compose logs postgres
docker compose logs pgbouncer

# Solutions
# 1. Fix database users
./scripts/fix_database_users.sh

# 2. Recreate admin user
./scripts/create_admin.sh

# 3. Post-startup fixes
./scripts/post_startup_fixes.sh

# 4. Check certificates
./scripts/validate_ssl_configuration.sh
```

### Migration Issues
**Symptoms:** "Migration failed", "Database schema mismatch"

```bash
# Check migration status
python ./scripts/migrate_check.py

# Solutions
# 1. Generate new migration
./scripts/_generate_migration.sh "Fix migration issue"

# 2. Manual migration
docker compose exec api alembic current
docker compose exec api alembic history

# 3. Reset database (loses data)
./run.sh --reset
```

### Database Performance Issues
**Symptoms:** Slow queries, connection timeouts

```bash
# Diagnosis
docker compose logs postgres | grep "slow query"
docker exec postgres pg_stat_activity

# Solutions
# 1. Check connection pool
docker compose logs pgbouncer

# 2. Optimize configuration
# Edit config/pgbouncer/pgbouncer.ini

# 3. Database maintenance
docker exec postgres psql -U app_user -d ai_workflow_db -c "VACUUM ANALYZE;"
```

---

## 🔐 Security and Certificate Issues

### SSL/TLS Certificate Errors
**Symptoms:** "Certificate verification failed", "SSL handshake failed"

```bash
# Diagnosis
./scripts/validate_ssl_configuration.sh --verbose

# Solutions
# 1. Regenerate certificates
./scripts/security/setup_mtls_infrastructure.sh setup

# 2. Validate certificate chain
./scripts/security/validate_security_implementation.sh

# 3. Development certificates (for dev only)
./scripts/generate_dev_certificates.sh

# 4. Fix certificate permissions
sudo ./scripts/fix_permissions.sh
```

### Authentication Issues
**Symptoms:** "Authentication failed", "Invalid token"

```bash
# Diagnosis
docker compose logs api | grep "auth"
cat logs/security_audit.log

# Solutions
# 1. Recreate admin user
./scripts/create_admin.sh

# 2. Check JWT secrets
cat secrets/jwt_secret_key.txt

# 3. Migrate passwords if needed
./scripts/migrate_user_passwords.sh

# 4. Fix authentication service
./scripts/post_startup_fixes.sh
```

### mTLS Communication Issues
**Symptoms:** Inter-service communication failures

```bash
# Diagnosis
./scripts/security/validate_security_implementation.sh

# Solutions
# 1. Regenerate all certificates
./scripts/security/setup_mtls_infrastructure.sh generate-all

# 2. Validate each service
for service in api worker postgres redis; do
    ./scripts/security/setup_mtls_infrastructure.sh info certs/$service/$service-cert.pem
done

# 3. Check certificate expiration
./scripts/security/setup_mtls_infrastructure.sh validate
```

---

## 🌐 Network and Connectivity Issues

### Web UI Not Accessible
**Symptoms:** Cannot access https://localhost:8080

```bash
# Diagnosis
curl -k https://localhost:8080/health
docker compose logs webui
docker compose logs caddy_reverse_proxy

# Solutions
# 1. Check port binding
docker compose ps | grep "8080"

# 2. Test SSL configuration
python ./scripts/test_webui_ssl.py

# 3. Validate domain configuration
python ./scripts/validate_domain_configuration.py

# 4. Check firewall/networking
netstat -tulpn | grep 8080
```

### API Endpoints Not Responding
**Symptoms:** API calls fail or timeout

```bash
# Diagnosis
curl -k https://localhost:8080/api/health
docker compose logs api

# Solutions
# 1. Check API service health
docker compose ps api
./scripts/_check_stack_health.sh

# 2. Restart API service
docker compose restart api

# 3. Check database connectivity
./scripts/fix_database_users.sh

# 4. Validate security configuration
./scripts/validate_security_monitoring.sh
```

### Service Discovery Issues
**Symptoms:** Services can't find each other

```bash
# Diagnosis
docker network ls
docker compose exec api nslookup postgres

# Solutions
# 1. Restart networking
docker compose down
docker compose up -d

# 2. Check DNS resolution
docker compose exec api cat /etc/resolv.conf

# 3. Validate service definitions
docker compose config
```

---

## ⚡ Performance Issues

### Slow Application Response
**Symptoms:** Long loading times, timeouts

```bash
# Diagnosis
./scripts/_container_inspector.sh
docker stats

# Solutions
# 1. Check resource usage
docker stats --no-stream

# 2. Apply performance optimizations
./scripts/deploy_performance_optimizations.sh

# 3. Monitor database performance
docker exec postgres pg_stat_statements

# 4. Check disk I/O
iostat -x 1 5
```

### Memory Issues
**Symptoms:** Out of memory errors, OOMKilled containers

```bash
# Diagnosis
docker stats
dmesg | grep -i "killed process"

# Solutions
# 1. Optimize memory usage
./scripts/_container_inspector.sh

# 2. Increase container limits
# Edit docker-compose.yml memory limits

# 3. Clean up unused resources
docker system prune -a -f

# 4. Monitor memory patterns
./scripts/_realtime_error_monitor.sh &
```

### High CPU Usage
**Symptoms:** System slowdown, high load averages

```bash
# Diagnosis
top
docker stats

# Solutions
# 1. Identify resource-heavy containers
docker stats --no-stream | sort -k 3 -nr

# 2. Check for runaway processes
docker compose exec <service> top

# 3. Restart problematic services
docker compose restart <service>

# 4. Apply resource limits
# Edit docker-compose.yml CPU limits
```

---

## 🤖 AI and ML Issues

### AI Models Not Loading
**Symptoms:** Model download failures, inference errors

```bash
# Diagnosis
docker compose logs ollama
docker exec ollama ollama list

# Solutions
# 1. Download required models
./scripts/pull_models_if_needed.sh

# 2. Check model availability
docker exec ollama ollama pull llama2:7b

# 3. Check disk space for models
du -sh $(docker volume inspect ollama_data -f '{{.Mountpoint}}')

# 4. Restart AI service
docker compose restart ollama
```

### Vector Database Issues
**Symptoms:** Qdrant connection failures, search errors

```bash
# Diagnosis
docker compose logs qdrant
curl -k https://localhost:6333/health

# Solutions
# 1. Check Qdrant health
curl -k https://qdrant:6333/health

# 2. Validate SSL configuration
./scripts/validate_ssl_configuration.sh --service qdrant

# 3. Restart Qdrant
docker compose restart qdrant

# 4. Check data volume
docker volume inspect qdrant_data
```

### MCP Server Issues
**Symptoms:** AI coding sessions not working, context not preserved

```bash
# Diagnosis
./scripts/mcp-session-manager.sh stats
docker compose logs redis-mcp

# Solutions
# 1. Restart MCP server
./scripts/mcp-redis-stop.sh
./scripts/mcp-redis-start.sh

# 2. Clean up sessions
./scripts/mcp-session-manager.sh cleanup --older-than 1h

# 3. Check Redis health
docker exec redis-mcp redis-cli -a simple_mcp_password ping

# 4. Monitor session activity
./scripts/mcp-session-manager.sh monitor
```

---

## 🔧 Development Environment Issues

### Code Changes Not Reflected
**Symptoms:** Code updates don't appear in running application

```bash
# Solutions
# 1. Soft reset (preserves data)
./run.sh --soft-reset

# 2. Rebuild specific service
docker compose build --no-cache <service>
docker compose up -d <service>

# 3. Check volume mounts
docker compose config | grep -A 5 volumes

# 4. Development restart
./scripts/_dev_restart.sh
```

### Test Failures
**Symptoms:** Tests failing unexpectedly

```bash
# Diagnosis
python ./scripts/test_webui_playwright.py --verbose
./scripts/validate_ssl_configuration.sh

# Solutions
# 1. Setup test environment
python ./scripts/setup_playwright_user.py

# 2. Validate test configuration
python ./scripts/validate_domain_configuration.py

# 3. Check browser automation
python ./scripts/create_playwright_user.py --email test@example.com --password testpass123

# 4. Reset test data
./scripts/create_admin_clean.sh
```

### Environment Configuration Issues
**Symptoms:** Environment variables not loaded, configuration mismatches

```bash
# Diagnosis
docker compose config
docker compose exec api env | grep -i workflow

# Solutions
# 1. Check environment files
cat .env
cat local.env

# 2. Regenerate secrets
./scripts/_setup_secrets_and_certs.sh

# 3. Validate configuration
./scripts/debug_worker_env.sh

# 4. Reset environment
./run.sh --soft-reset
```

---

## 🚀 Advanced Troubleshooting

### Using AI Diagnostics
```bash
# Get AI-powered problem analysis
./scripts/_ask_gemini.sh

# Find error patterns
./scripts/_find_error_source.sh

# Get comprehensive diagnostics
./scripts/_comprehensive_logger.sh
```

### Deep System Analysis
```bash
# Complete container inspection
./scripts/_container_inspector.sh

# Real-time monitoring
./scripts/_realtime_error_monitor.sh &

# Event monitoring
./scripts/_watch_events.sh &

# Docker system analysis
docker system events --since '1h' --until '0s'
```

### Log Analysis Techniques
```bash
# Find error patterns
grep -n "ERROR\|CRITICAL\|FATAL" logs/error_log.txt

# Analyze timing issues
grep -n "timeout\|slow\|delay" logs/*.log

# Check authentication issues
grep -n "auth\|login\|token" logs/security_audit.log

# Monitor real-time issues
tail -f logs/runtime_errors.log | grep -i "critical\|error"
```

---

## 🎯 Problem-Specific Quick Reference

### Quick Commands by Problem Type

| Problem | Quick Fix | Detailed Solution |
|---------|-----------|-------------------|
| Permission denied | `sudo ./scripts/fix_permissions.sh` | [Permissions Section](#-docker-and-container-issues) |
| Service won't start | `./scripts/worker_universal_fix.sh` | [Container Issues](#container-wont-start) |
| Database error | `./scripts/fix_database_users.sh` | [Database Section](#-database-issues) |
| Certificate error | `./scripts/validate_ssl_configuration.sh` | [Security Section](#-security-and-certificate-issues) |
| Web UI not loading | `python ./scripts/test_webui_ssl.py` | [Network Section](#-network-and-connectivity-issues) |
| Performance issues | `./scripts/_container_inspector.sh` | [Performance Section](#-performance-issues) |
| AI models failing | `./scripts/pull_models_if_needed.sh` | [AI Issues Section](#-ai-and-ml-issues) |

### Emergency Recovery Commands
```bash
# Complete system reset (loses all data)
./run.sh --reset

# Permission fix (safe)
sudo ./scripts/fix_permissions.sh

# Service recovery (safe)
./scripts/post_startup_fixes.sh

# Health check (diagnostic only)
./scripts/_check_stack_health.sh
```

---

## 📞 Getting Help

### Information to Gather Before Asking for Help
1. **Error Logs:** `cat logs/error_log.txt`
2. **System Status:** `docker compose ps -a`
3. **Recent Commands:** Last commands run before the issue
4. **Environment:** OS, Docker version, available resources
5. **Reproduction Steps:** How to reproduce the issue

### Useful Diagnostic Commands
```bash
# Complete system overview
./scripts/_check_stack_health.sh > system_health.txt

# Recent error summary
tail -50 logs/error_log.txt > recent_errors.txt

# Container status
docker compose ps -a > container_status.txt

# Resource usage
docker stats --no-stream > resource_usage.txt

# Configuration validation
docker compose config > current_config.yml
```

### Self-Diagnosis Checklist
- [ ] Tried basic permission fix
- [ ] Checked service logs
- [ ] Verified disk space availability
- [ ] Attempted soft reset
- [ ] Reviewed recent changes
- [ ] Checked system resources
- [ ] Validated configuration files

---

*For specific development workflows, see [Development Workflow](./development.md).  
For production deployment issues, see [Deployment Workflow](./deployment.md).*