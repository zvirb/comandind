# Troubleshooting

Comprehensive troubleshooting guide for common issues, debugging procedures, and problem resolution in the AI Workflow Engine.

## 🔧 Troubleshooting Overview

This section provides solutions for:
- **Common Setup Issues**: Installation and configuration problems
- **Authentication Problems**: Login, token, and permission issues
- **Database Issues**: Connection, migration, and performance problems
- **SSL/Certificate Issues**: mTLS, certificate validation, and connectivity
- **Performance Problems**: Slow responses, memory issues, and optimization
- **Agent System Issues**: Agent execution, orchestration, and tool problems

## 📋 Troubleshooting Categories

### [🚨 Common Issues](common-issues.md)
Most frequently encountered problems and solutions:
- Environment setup failures
- Docker container issues
- Service startup problems
- Configuration errors
- Network connectivity issues

### [🔐 Authentication Problems](authentication.md)
Authentication and authorization troubleshooting:
- Login failures and token issues
- JWT validation problems
- Session timeout and management
- Permission denied errors
- OAuth and external auth issues

### [🗄️ Database Issues](database.md)
Database-related problems and solutions:
- Connection pool issues
- Migration failures
- Query performance problems
- Data consistency issues
- Backup and recovery problems

### [🔒 SSL/Certificate Issues](ssl-certificates.md)
SSL, TLS, and certificate troubleshooting:
- Certificate validation failures
- mTLS handshake problems
- Certificate expiration issues
- CA trust problems
- Proxy and routing issues

## 🚨 Emergency Procedures

### System Recovery
```bash
# Complete system reset (use with caution)
docker-compose down -v
./scripts/security/setup_mtls_infrastructure.sh setup
docker-compose -f docker-compose-mtls.yml up

# Database recovery
docker-compose exec database pg_restore -U postgres -d ai_workflow_engine /backup/latest.sql

# Certificate emergency renewal
./scripts/security/emergency_cert_renewal.sh
```

### Quick Diagnostics
```bash
# System health check
./scripts/health_check.sh

# SSL/TLS validation
./scripts/validate_ssl_configuration.sh

# Database connectivity test
./scripts/test_database_connection.sh

# Authentication flow test
./scripts/test_auth_flow.sh
```

## 🔍 Common Problem Categories

### 🚀 Startup Issues

#### **Container Won't Start**
```bash
# Check container logs
docker-compose logs api
docker-compose logs database

# Check resource usage
docker stats

# Restart specific service
docker-compose restart api
```

#### **Port Conflicts**
```bash
# Check port usage
netstat -tlnp | grep :8443
lsof -i :8443

# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx
```

#### **Permission Issues**
```bash
# Fix permission issues
sudo chown -R $(whoami):$(whoami) .
chmod +x scripts/*.sh

# Docker permission issues
sudo usermod -aG docker $USER
newgrp docker
```

### 🔐 Authentication Issues

#### **JWT Token Problems**
```bash
# Debug JWT tokens
python debug_jwt.py

# Check token expiration
jwt_token="your_token_here"
echo $jwt_token | base64 -d

# Regenerate JWT secret
openssl rand -base64 32
```

#### **Login Failures**
```bash
# Check authentication logs
docker-compose logs api | grep "auth"

# Test authentication endpoint
curl -k -X POST https://localhost:8443/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Reset user password
docker-compose exec api python -c "
from shared.services.user_service import UserService
UserService.reset_password('admin', 'new_password')
"
```

### 🗄️ Database Issues

#### **Connection Problems**
```bash
# Test database connection
docker-compose exec database psql -U postgres -d ai_workflow_engine -c "SELECT 1;"

# Check connection pool
docker-compose exec pgbouncer psql -h localhost -p 6432 -U postgres -d pgbouncer -c "SHOW POOLS;"

# Reset connections
docker-compose restart pgbouncer
```

#### **Migration Failures**
```bash
# Check migration status
docker-compose exec api alembic current
docker-compose exec api alembic history

# Force migration
docker-compose exec api alembic stamp head
docker-compose exec api alembic upgrade head

# Manual migration rollback
docker-compose exec api alembic downgrade -1
```

### 🔒 SSL/Certificate Issues

#### **Certificate Validation Failures**
```bash
# Validate certificates
openssl x509 -in certs/server/server.crt -text -noout
openssl verify -CAfile certs/ca/ca.crt certs/server/server.crt

# Test SSL connection
openssl s_client -connect localhost:8443 -cert certs/client/client.crt -key certs/client/client.key

# Regenerate certificates
./scripts/security/setup_mtls_infrastructure.sh regenerate
```

#### **mTLS Handshake Problems**
```bash
# Debug mTLS handshake
curl -v --cert certs/client/client.crt --key certs/client/client.key \
  --cacert certs/ca/ca.crt https://localhost:8443/health

# Check certificate chain
openssl s_client -connect localhost:8443 -showcerts

# Verify client certificate
openssl x509 -in certs/client/client.crt -noout -dates
```

## 🛠️ Debugging Tools

### Log Analysis
```bash
# Application logs
docker-compose logs -f api

# Database logs
docker-compose logs -f database

# Reverse proxy logs
docker-compose logs -f caddy

# Security audit logs
docker-compose exec api cat /var/log/security_audit.log
```

### Performance Debugging
```bash
# Resource monitoring
docker stats
htop

# Database performance
docker-compose exec database pg_stat_activity
docker-compose exec database pg_stat_statements

# API performance
curl -w "@curl-format.txt" -s -o /dev/null https://localhost:8443/health
```

### Network Debugging
```bash
# Network connectivity
ping localhost
telnet localhost 8443

# DNS resolution
nslookup localhost
dig localhost

# Firewall status
sudo ufw status
iptables -L
```

## 📊 Diagnostic Scripts

### Health Check Script
```bash
#!/bin/bash
# scripts/health_check.sh

echo "=== AI Workflow Engine Health Check ==="

# Check Docker containers
echo "1. Container Status:"
docker-compose ps

# Check SSL certificates
echo "2. Certificate Status:"
./scripts/validate_ssl_configuration.sh

# Check database connectivity
echo "3. Database Status:"
docker-compose exec -T database pg_isready -U postgres

# Check API health
echo "4. API Health:"
curl -k -s https://localhost:8443/health || echo "API not responding"

# Check authentication
echo "5. Authentication Test:"
./scripts/test_auth_flow.sh
```

## 🔗 Getting Help

### Internal Resources
- [Development Environment Setup](../development/environment-setup.md)
- [Security Configuration](../security/overview.md)
- [Infrastructure Guide](../infrastructure/deployment.md)
- [API Documentation](../api/reference.md)

### Support Channels
1. **Check Logs**: Always check container logs first
2. **Search Documentation**: Use Ctrl+F to search this documentation
3. **GitHub Issues**: Check existing issues and create new ones
4. **Team Chat**: Internal team communication channels
5. **Emergency Contacts**: For critical production issues

### Creating Bug Reports
When reporting issues, include:
```
**Environment**: Development/Staging/Production
**Docker Compose Version**: docker-compose version
**Container Logs**: Relevant log excerpts
**Steps to Reproduce**: Detailed reproduction steps
**Expected Behavior**: What should happen
**Actual Behavior**: What actually happens
**Screenshots**: If applicable
```

## 📚 Quick Reference

### Emergency Commands
```bash
# Complete system restart
docker-compose down && docker-compose -f docker-compose-mtls.yml up

# Force certificate regeneration
rm -rf certs/ && ./scripts/security/setup_mtls_infrastructure.sh setup

# Database emergency backup
docker-compose exec database pg_dump -U postgres ai_workflow_engine > emergency_backup.sql

# Reset to clean state
docker-compose down -v && docker system prune -f
```

### Log Locations
- **Application Logs**: `docker-compose logs api`
- **Database Logs**: `docker-compose logs database`
- **Security Logs**: `/var/log/security_audit.log`
- **Access Logs**: `docker-compose logs caddy`

---

**Need More Help?** If you can't find a solution here, check the [Contributing Guidelines](../development/contributing.md) for how to get support or report issues.