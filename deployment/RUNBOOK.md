# Production Runbook
## Command & Independent Thought Game Operations

This runbook provides step-by-step operational procedures for managing the production deployment of Command & Independent Thought game.

## 🎯 Quick Reference

### Emergency Contacts
- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **Operations Team**: ops@company.com
- **Development Team**: dev@company.com

### Critical Endpoints
- **Production**: https://game.company.com
- **Health Check**: https://game.company.com/health
- **Monitoring**: https://monitoring.company.com:9090
- **Logs**: https://logs.company.com

### Emergency Commands
```bash
# Emergency rollback
./deployment/scripts/rollback.sh auto

# Stop all services
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml down

# Restart all services
docker compose -f deployment/docker-compose/docker-compose.blue-green.yml up -d
```

---

## 📋 Standard Operating Procedures

### SOP-001: Normal Deployment

**When**: Regular feature releases, bug fixes, security updates

**Prerequisites**:
- [ ] Change approval obtained
- [ ] Deployment window scheduled
- [ ] Team notified
- [ ] Rollback plan confirmed

**Steps**:

1. **Pre-deployment Validation**
   ```bash
   # Verify current system health
   ./deployment/scripts/deploy.sh health
   ./deployment/scripts/deploy.sh status
   
   # Check resource availability
   docker system df
   free -h
   ```

2. **Execute Deployment**
   ```bash
   # Set version and deploy
   export VERSION=$(git rev-parse --short HEAD)
   ./deployment/scripts/deploy.sh deploy
   ```

3. **Post-deployment Validation**
   ```bash
   # Wait for deployment to stabilize
   sleep 60
   
   # Verify health
   curl -f http://localhost/health
   curl -f http://localhost/health/detailed
   
   # Check monitoring metrics
   # Visit http://localhost:9090
   ```

4. **Rollback if Issues Detected**
   ```bash
   # Automatic rollback
   ./deployment/scripts/rollback.sh auto
   
   # Or manual rollback
   ./deployment/scripts/rollback.sh manual blue "deployment validation failed"
   ```

**Success Criteria**:
- [ ] Health checks pass
- [ ] Response times < 500ms
- [ ] No 5xx errors
- [ ] All monitoring green

---

### SOP-002: Emergency Rollback

**When**: Production issues, failed deployments, security incidents

**Trigger Conditions**:
- Service unavailable (5xx errors > 10%)
- Response times > 2 seconds
- Health checks failing
- Security incident

**Steps**:

1. **Immediate Assessment**
   ```bash
   # Check current status
   ./deployment/scripts/rollback.sh status
   
   # Check health of both slots
   ./deployment/scripts/deploy.sh health blue
   ./deployment/scripts/deploy.sh health green
   ```

2. **Execute Emergency Rollback**
   ```bash
   # Automatic rollback (recommended)
   ./deployment/scripts/rollback.sh auto
   
   # Or manual if specific slot needed
   ./deployment/scripts/rollback.sh manual blue "emergency-$(date +%s)"
   ```

3. **Verify Rollback Success**
   ```bash
   # Wait for rollback to complete
   sleep 30
   
   # Verify service recovery
   for i in {1..10}; do
     curl -f http://localhost/health || echo "Attempt $i failed"
     sleep 5
   done
   ```

4. **Communication**
   - Notify stakeholders immediately
   - Update status page if available
   - Document incident for post-mortem

**Success Criteria**:
- [ ] Service restored within 5 minutes
- [ ] Health checks passing
- [ ] Stakeholders notified
- [ ] Incident logged

---

### SOP-003: Health Check Investigation

**When**: Health checks failing, performance degradation

**Investigation Steps**:

1. **System-Level Checks**
   ```bash
   # Container status
   docker compose ps
   
   # Resource usage
   docker stats --no-stream
   
   # System resources
   df -h
   free -h
   top
   ```

2. **Application-Level Checks**
   ```bash
   # Detailed health check
   docker compose exec game-blue /usr/local/bin/health-check.sh full
   
   # Application logs
   docker compose logs --tail=100 game-blue
   docker compose logs --tail=100 game-green
   ```

3. **Network Checks**
   ```bash
   # Load balancer status
   docker compose exec nginx-lb nginx -t
   curl -I http://localhost/health
   
   # Internal connectivity
   docker compose exec game-blue curl -f http://localhost:8080/health
   ```

4. **Resolution Actions**
   ```bash
   # Restart unhealthy container
   docker compose restart game-blue
   
   # Reload nginx if needed
   docker compose exec nginx-lb nginx -s reload
   
   # Switch to healthy slot if available
   ./deployment/scripts/rollback.sh auto
   ```

---

### SOP-004: Performance Issue Response

**When**: High response times, resource exhaustion, user complaints

**Investigation**:

1. **Metrics Analysis**
   ```bash
   # Check monitoring dashboard
   # Visit http://localhost:9090
   
   # Container resource usage
   docker stats
   
   # Network I/O
   iftop -t -s 60
   ```

2. **Application Performance**
   ```bash
   # Response time testing
   for i in {1..10}; do
     time curl -o /dev/null -s http://localhost/
   done
   
   # Check for memory leaks
   curl http://localhost:8080/status | jq '.metrics'
   ```

3. **Scaling Actions**
   ```bash
   # Increase container resources (if using limits)
   docker compose -f deployment/docker-compose/docker-compose.blue-green.yml up -d --scale game-blue=2
   
   # Clear caches
   docker compose exec nginx-lb nginx -s reload
   ```

---

### SOP-005: Security Incident Response

**When**: Security alerts, breach indicators, vulnerability exploitation

**Immediate Actions**:

1. **Containment**
   ```bash
   # Block suspicious traffic (example)
   # Add firewall rules or rate limits
   
   # Take snapshot for forensics
   docker commit game-blue security-incident-$(date +%s)
   ```

2. **Assessment**
   ```bash
   # Check for indicators of compromise
   docker compose exec game-blue find /usr/share/nginx/html -type f -mtime -1
   
   # Review access logs
   docker compose logs nginx-lb | grep -E "(4[0-9]{2}|5[0-9]{2})"
   ```

3. **Response**
   ```bash
   # Immediate rollback if compromised
   ./deployment/scripts/rollback.sh auto
   
   # Update secrets
   # Rotate all API keys and certificates
   
   # Apply security patches
   docker compose build --no-cache
   ./deployment/scripts/deploy.sh deploy
   ```

---

## 🚨 Alert Response Procedures

### Critical Alerts

#### Service Down
**Alert**: "Game service returning 5xx errors"
**Response Time**: < 5 minutes

1. Check load balancer and container status
2. Attempt automatic rollback
3. Notify on-call team if rollback fails
4. Escalate to development team

#### High Response Time
**Alert**: "Response time > 2 seconds"
**Response Time**: < 15 minutes

1. Check resource utilization
2. Review recent deployments
3. Scale containers if needed
4. Investigate application bottlenecks

#### Health Check Failure
**Alert**: "Health check failing for > 2 minutes"
**Response Time**: < 10 minutes

1. Validate health check endpoint
2. Check container logs for errors
3. Restart container if needed
4. Switch to backup slot

### Warning Alerts

#### High Memory Usage
**Alert**: "Memory usage > 80%"
**Response Time**: < 30 minutes

1. Monitor for memory leaks
2. Consider scaling
3. Review application memory usage
4. Plan for resource adjustment

#### Disk Space Low
**Alert**: "Disk usage > 85%"
**Response Time**: < 1 hour

1. Clean up old Docker images and containers
2. Review log file sizes
3. Archive or delete unnecessary files
4. Plan for storage expansion

---

## 📊 Monitoring and Alerting

### Key Metrics

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Response Time | < 500ms | 500ms-1s | > 2s |
| Error Rate | < 1% | 1-5% | > 10% |
| CPU Usage | < 70% | 70-85% | > 90% |
| Memory Usage | < 70% | 70-85% | > 90% |
| Disk Usage | < 80% | 80-90% | > 95% |

### Health Check Expectations

```bash
# All should return HTTP 200
curl http://localhost/health          # "healthy"
curl http://localhost/ready           # "ready"  
curl http://localhost/live            # "alive"
```

### Prometheus Queries

```promql
# Error rate
rate(nginx_http_requests_total{status=~"5.."}[5m])

# Response time 95th percentile
histogram_quantile(0.95, rate(nginx_http_request_duration_seconds_bucket[5m]))

# Container memory usage
container_memory_usage_bytes / container_spec_memory_limit_bytes * 100

# Game health status
game_health_check{slot="blue"}
```

---

## 🔧 Maintenance Procedures

### Daily Tasks
- [ ] Review monitoring dashboards
- [ ] Check error logs for anomalies
- [ ] Verify backup completion
- [ ] Update security monitoring

### Weekly Tasks
- [ ] Review performance trends
- [ ] Update Docker base images
- [ ] Clean up old deployments
- [ ] Review security alerts

### Monthly Tasks
- [ ] Capacity planning review
- [ ] Disaster recovery testing
- [ ] Security vulnerability assessment
- [ ] Performance optimization review

---

## 📞 Escalation Matrix

### Level 1 - Operations Team
**When**: Standard alerts, routine issues
**Response**: Follow SOP procedures
**Escalate if**: Unable to resolve in 30 minutes

### Level 2 - Senior Operations
**When**: Critical service issues, Level 1 escalation
**Response**: Advanced troubleshooting
**Escalate if**: Unable to resolve in 1 hour

### Level 3 - Development Team
**When**: Application bugs, architecture issues
**Response**: Code fixes, emergency patches
**Escalate if**: Systemic issues identified

### Level 4 - Emergency Response
**When**: Major outages, security breaches
**Response**: All hands, management notification
**Authority**: Service changes, resource allocation

---

## 📋 Checklists

### Pre-Deployment Checklist
- [ ] Backup current deployment
- [ ] Verify infrastructure health
- [ ] Confirm rollback procedures
- [ ] Notify stakeholders
- [ ] Schedule deployment window

### Post-Incident Checklist
- [ ] Service restored
- [ ] Root cause identified
- [ ] Timeline documented
- [ ] Stakeholders updated
- [ ] Post-mortem scheduled
- [ ] Preventive measures planned

### Shift Change Checklist
- [ ] Review ongoing incidents
- [ ] Check monitoring alerts
- [ ] Verify backup status
- [ ] Update handoff documentation
- [ ] Confirm escalation paths

---

*This runbook should be reviewed and updated monthly. Last updated: August 2025*