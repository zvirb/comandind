# Production Deployment Guide
## Command & Independent Thought Game - Blue-Green Deployment System

This document provides comprehensive instructions for deploying and managing the Command & Independent Thought game in a production environment using a blue-green deployment strategy.

## 🏗️ Architecture Overview

The deployment system uses a **blue-green deployment strategy** with the following components:

- **Blue Environment**: Current production version
- **Green Environment**: New version for testing and deployment
- **Load Balancer**: Nginx reverse proxy for traffic routing
- **Health Monitor**: Continuous health checking and alerting
- **Monitoring Stack**: Prometheus, cAdvisor, and Fluentd for observability
- **Automatic Rollback**: Intelligent rollback on deployment failures

## 📋 Prerequisites

### System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- curl and jq (for health checks)
- Minimum 2GB RAM, 10GB disk space

### Network Requirements
- Ports 80, 443 (web traffic)
- Port 9090 (Prometheus metrics)
- Port 8081 (cAdvisor metrics)
- Port 24224 (Fluentd logging)

## 🚀 Quick Start Deployment

### 1. Initial Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd command-and-independent-thought

# Copy environment configuration
cp deployment/config/production.env .env
cp deployment/config/secrets.env.example deployment/config/secrets.env

# Edit secrets.env with your actual secrets
nano deployment/config/secrets.env
```

### 2. First-Time Deployment

```bash
# Build and start the initial blue-green infrastructure
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml up -d

# Wait for services to be ready (2-3 minutes)
sleep 120

# Check deployment status
./deployment/scripts/deploy.sh status
```

### 3. Deploy New Version

```bash
# Set version (optional - uses git commit hash by default)
export VERSION=v1.0.0

# Deploy to production
./deployment/scripts/deploy.sh deploy

# Monitor deployment progress
watch -n 5 './deployment/scripts/deploy.sh status'
```

## 🔧 Deployment Commands

### Core Deployment Operations

```bash
# Deploy new version with automatic slot detection
./deployment/scripts/deploy.sh deploy

# Deploy to specific slot
./deployment/scripts/deploy.sh deploy green

# Check deployment status
./deployment/scripts/deploy.sh status

# Perform health check
./deployment/scripts/deploy.sh health

# Clean up old Docker images
./deployment/scripts/deploy.sh cleanup
```

### Rollback Operations

```bash
# Automatic rollback (if active slot is unhealthy)
./deployment/scripts/rollback.sh auto

# Manual rollback to specific slot
./deployment/scripts/rollback.sh manual blue "emergency rollback"

# Quick rollback shortcuts
./deployment/scripts/rollback.sh blue
./deployment/scripts/rollback.sh green

# Check rollback status and history
./deployment/scripts/rollback.sh status

# Validate slot before rollback
./deployment/scripts/rollback.sh validate green
```

## 📊 Monitoring and Health Checks

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost/health

# Detailed application health
curl http://localhost/health/detailed

# Container readiness probe
curl http://localhost/ready

# Container liveness probe
curl http://localhost/live
```

### Monitoring Services

- **Prometheus**: http://localhost:9090
- **Health Monitor**: http://localhost:8080/status
- **cAdvisor**: http://localhost:8081

### Log Aggregation

```bash
# View application logs
docker compose logs game-blue
docker compose logs game-green

# View load balancer logs
docker compose logs nginx-lb

# View health monitor logs
docker compose logs health-monitor
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| VERSION | Deployment version | git commit hash |
| TIMEOUT | Deployment timeout | 300s |
| HEALTH_CHECK_RETRIES | Health validation retries | 10 |
| HEALTH_CHECK_INTERVAL | Health check interval | 30s |
| ROLLBACK_TIMEOUT | Rollback operation timeout | 120s |
| VALIDATION_RETRIES | Rollback validation retries | 5 |

### Secrets Management

Store sensitive configuration in `deployment/config/secrets.env`:

```bash
# Database credentials
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_PASSWORD=secure_password

# API keys
MONITORING_API_KEY=your_monitoring_key
ALERT_WEBHOOK_URL=https://hooks.slack.com/your/webhook

# SSL certificates
SSL_CERTIFICATE_PATH=/path/to/cert.crt
SSL_PRIVATE_KEY_PATH=/path/to/private.key
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Deployment Fails During Build

```bash
# Check build logs
docker compose logs --tail=100

# Rebuild with no cache
docker compose build --no-cache

# Check disk space
df -h
```

#### 2. Health Checks Failing

```bash
# Check container health
docker compose exec game-blue /usr/local/bin/health-check.sh full

# View detailed health status
curl http://localhost:8080/status

# Check container resources
docker stats
```

#### 3. Rollback Not Working

```bash
# Validate rollback target
./deployment/scripts/rollback.sh validate blue

# Check rollback history
./deployment/scripts/rollback.sh status

# Force container restart
docker compose restart game-blue
```

#### 4. Load Balancer Issues

```bash
# Test nginx configuration
docker compose exec nginx-lb nginx -t

# Reload nginx
docker compose exec nginx-lb nginx -s reload

# Check upstream health
curl -I http://localhost/test/health
```

### Recovery Procedures

#### Emergency Recovery

```bash
# Stop all services
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml down

# Restart infrastructure
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml up -d

# Force rollback to last known good version
KEEP_OLD_SLOT=true ./deployment/scripts/rollback.sh auto
```

#### Data Recovery

```bash
# Backup current state
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml exec game-blue tar czf /tmp/backup.tar.gz /usr/share/nginx/html

# Restore from backup
docker cp backup.tar.gz game-blue:/tmp/
docker compose exec game-blue tar xzf /tmp/backup.tar.gz -C /
```

## 🔐 Security Considerations

### Container Security
- All containers run as non-root users
- Read-only root filesystems where possible
- Security headers enabled in nginx configuration
- Regular security updates via base image updates

### Network Security
- All internal communication uses docker network isolation
- Rate limiting enabled on public endpoints
- CORS configuration for API endpoints
- SSL/TLS termination at load balancer

### Secrets Management
- Never commit secrets to version control
- Use environment variables for runtime secrets
- Rotate secrets regularly
- Monitor for secret exposure

## 📈 Performance Optimization

### Resource Allocation
- Memory limits set per container
- CPU limits configured for fair resource sharing
- Health check intervals optimized for responsiveness

### Caching Strategy
- Static assets cached with long TTLs
- API responses cached appropriately
- Browser caching headers optimized

### Monitoring Metrics
- Response time monitoring
- Error rate tracking
- Resource utilization metrics
- Custom game performance metrics

## 🔄 Maintenance

### Regular Tasks

#### Daily
- Monitor health check status
- Review error logs
- Check resource utilization

#### Weekly
- Update base Docker images
- Review security alerts
- Clean up old deployment artifacts

#### Monthly
- Rotate secrets and certificates
- Review and update monitoring thresholds
- Performance optimization review

### Automation

```bash
# Set up automated health monitoring
crontab -e
*/5 * * * * /path/to/deployment/scripts/rollback.sh auto

# Set up log rotation
echo "0 2 * * * docker system prune -f" | crontab -

# Set up automated backups
echo "0 1 * * * /path/to/backup-script.sh" | crontab -
```

## 📞 Support and Escalation

### Alert Levels

1. **Info**: Deployment completed successfully
2. **Warning**: High resource usage, slow response times
3. **Critical**: Service unavailable, deployment failed

### Escalation Procedures

1. **Level 1**: Automated rollback attempted
2. **Level 2**: Operations team notified
3. **Level 3**: Development team engaged
4. **Level 4**: Emergency recovery procedures initiated

### Contact Information

- **Operations**: ops@yourcompany.com
- **Development**: dev@yourcompany.com  
- **Emergency**: emergency@yourcompany.com

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Load Balancing Guide](https://nginx.org/en/docs/http/load_balancing.html)
- [Prometheus Monitoring Guide](https://prometheus.io/docs/guides/basic-auth/)
- [Blue-Green Deployment Best Practices](https://martinfowler.com/bliki/BlueGreenDeployment.html)

---

*This deployment system was created with Claude Code AI Orchestration Engine*