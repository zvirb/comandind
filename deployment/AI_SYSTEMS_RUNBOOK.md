# AI Systems Operational Runbook
## Command & Independent Thought RTS - Production Deployment

### Document Information
- **Version**: 1.0
- **Last Updated**: August 20, 2025
- **Environment**: Production
- **Contact**: Production Operations Team

---

## Table of Contents
1. [System Overview](#system-overview)
2. [AI Components Status](#ai-components-status)
3. [Health Monitoring](#health-monitoring)
4. [Performance Thresholds](#performance-thresholds)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Rollback Procedures](#rollback-procedures)
7. [Emergency Contacts](#emergency-contacts)

---

## System Overview

### Production Deployment
- **Container**: `ai-rts-production`
- **Image**: `command-independent-thought:latest`
- **Port**: 8080
- **Health Endpoints**: `/health`, `/ready`, `/live`
- **Version**: ai-enhanced-v0.1.0

### AI Systems Integrated
1. **TensorFlow.js Manager** - WebGL backend with CPU fallback
2. **Deep Q-Networks** - 36→64→16 architecture with experience replay
3. **Behavior Trees** - GOAP-compatible hierarchical decision-making
4. **Ollama LLM Integration** - Strategic AI advisor
5. **ECS AI Components** - Entity-based AI state management
6. **Training Pipeline** - Asynchronous Q-learning

---

## AI Components Status

### TensorFlow.js Manager
- **Purpose**: ML inference engine for unit AI
- **Backend**: WebGL (with CPU fallback)
- **Performance Target**: <5ms inference time
- **Memory Budget**: <50MB GPU memory
- **Health Check**: Validates tensor operations on startup

### Deep Q-Networks
- **Purpose**: Unit behavior optimization
- **Architecture**: 36 input → 64 hidden → 16 output
- **Performance Target**: <2ms per inference
- **Training**: Experience replay with convergence validation

### Ollama Strategic Advisor
- **Purpose**: High-level strategic AI assistance
- **Performance Target**: <500ms response time
- **Fallback**: Graceful degradation to basic AI

---

## Health Monitoring

### Primary Health Endpoints
```bash
# Basic health check
curl http://localhost:8080/health
# Expected: "healthy"

# Readiness probe
curl http://localhost:8080/ready  
# Expected: "ready"

# Liveness probe
curl http://localhost:8080/live
# Expected: "alive"

# Detailed application health
curl http://localhost:8080/health/detailed
# Expected: HTML page with game interface
```

### Container Health Check
```bash
# Check container status
docker ps --filter "name=ai-rts-production"

# Check container logs
docker logs ai-rts-production --tail 50

# Execute health script inside container
docker exec ai-rts-production /usr/local/bin/health-check.sh
```

### Performance Monitoring
```bash
# Response time test
time curl -s http://localhost:8080/health

# Memory usage check
docker stats ai-rts-production --no-stream

# AI system validation
# Navigate to http://localhost:8080 and verify:
# - Game loads successfully
# - Units respond to selection
# - AI behaviors are functional
```

---

## Performance Thresholds

### Critical Thresholds (Require Immediate Action)
- **Response Time**: >1000ms
- **Memory Usage**: >512MB
- **CPU Usage**: >90% sustained
- **Container Restarts**: >3 in 5 minutes
- **Health Check Failures**: >3 consecutive

### Warning Thresholds (Monitor Closely)
- **Response Time**: >100ms
- **Memory Usage**: >256MB
- **CPU Usage**: >70% sustained
- **AI Inference Time**: >10ms
- **Frame Rate**: <45 FPS

### Optimal Performance Indicators
- **Response Time**: <10ms (as evidenced: 5-7ms)
- **Memory Usage**: <128MB
- **CPU Usage**: <50%
- **AI Inference Time**: <5ms
- **Frame Rate**: 60+ FPS

---

## Troubleshooting Guide

### Container Won't Start
```bash
# Check Docker daemon
systemctl status docker

# Check image exists
docker images | grep command-independent-thought

# Check port availability
netstat -tulpn | grep :8080

# Start with verbose logging
docker run -d --name ai-rts-debug -p 8080:8080 command-independent-thought:latest
docker logs -f ai-rts-debug
```

### Health Checks Failing
```bash
# Check nginx configuration
docker exec ai-rts-production nginx -t

# Check nginx access logs
docker exec ai-rts-production tail -f /var/log/nginx/access.log

# Check nginx error logs
docker exec ai-rts-production tail -f /var/log/nginx/error.log

# Restart nginx inside container
docker exec ai-rts-production nginx -s reload
```

### Performance Issues
```bash
# Check container resource usage
docker stats ai-rts-production

# Check host resources
top
htop
iostat 1

# Check for memory leaks
docker exec ai-rts-production ps aux --sort=-%mem | head -10

# AI system performance check
# Monitor browser developer tools for:
# - JavaScript errors
# - TensorFlow.js warnings
# - Memory growth patterns
```

### AI Systems Not Working
```bash
# Check AI components in browser console:
# 1. Open http://localhost:8080
# 2. Open Developer Tools (F12)
# 3. Check Console for errors related to:
#    - TensorFlow initialization
#    - WebGL context creation
#    - AI component loading
#    - Ollama connection issues

# Check if TensorFlow.js is loaded
# In browser console: typeof tf !== 'undefined'

# Check WebGL support
# In browser console: document.createElement('canvas').getContext('webgl') !== null
```

---

## Rollback Procedures

### Immediate Rollback (Emergency)
```bash
# Stop current container
docker stop ai-rts-production
docker rm ai-rts-production

# Start previous stable version
# Replace [PREVIOUS_VERSION] with last known good version
docker run -d --name ai-rts-production \
  -p 8080:8080 \
  command-independent-thought:[PREVIOUS_VERSION]

# Verify rollback success
curl http://localhost:8080/health
```

### Blue-Green Rollback
```bash
# If using blue-green deployment
cd deployment/

# Check current active slot
./scripts/deploy.sh status

# Rollback to previous slot
./scripts/deploy.sh rollback

# Verify rollback
./scripts/deploy.sh health
```

### Gradual Rollback (Planned)
```bash
# 1. Deploy previous version to standby slot
./scripts/deploy.sh deploy [PREVIOUS_VERSION]

# 2. Verify standby health
./scripts/deploy.sh health green

# 3. Switch traffic gradually
# Update load balancer configuration
# Monitor metrics during transition

# 4. Complete rollback
./scripts/deploy.sh status
```

---

## AI System Recovery Procedures

### TensorFlow.js Recovery
If TensorFlow.js fails to initialize:
1. Check WebGL support in browser
2. Verify GPU memory availability
3. Check for WebGL context loss
4. Fallback should activate automatically to CPU
5. If fallback fails, refresh application

### Ollama Integration Recovery
If Ollama strategic advisor fails:
1. Check Ollama service availability
2. Verify network connectivity
3. Check API rate limits
4. System should gracefully degrade to basic AI

### Performance Recovery
If AI performance degrades:
1. Check memory usage for leaks
2. Verify garbage collection is working
3. Monitor inference timing
4. Consider container restart if persistent

---

## Container Management Commands

### Standard Operations
```bash
# Start production container
docker run -d --name ai-rts-production \
  -p 8080:8080 \
  --restart unless-stopped \
  command-independent-thought:latest

# Stop container gracefully
docker stop ai-rts-production

# Restart container
docker restart ai-rts-production

# Update container (with new image)
docker stop ai-rts-production
docker rm ai-rts-production
docker pull command-independent-thought:latest
docker run -d --name ai-rts-production \
  -p 8080:8080 \
  --restart unless-stopped \
  command-independent-thought:latest
```

### Backup and Recovery
```bash
# Create container backup
docker commit ai-rts-production ai-rts-backup:$(date +%Y%m%d-%H%M%S)

# Export container state
docker export ai-rts-production > ai-rts-backup-$(date +%Y%m%d).tar

# View container configurations
docker inspect ai-rts-production
```

---

## Emergency Contacts

### Production Issues
- **Primary**: Production Operations Team
- **Secondary**: Development Team Lead
- **Escalation**: Technical Director

### AI System Issues
- **Primary**: AI Systems Engineer
- **Secondary**: Machine Learning Team
- **Escalation**: Chief Technology Officer

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-08-20 | Initial production runbook | Deployment Orchestrator |

---

## Additional Notes

- This runbook should be updated after any major deployment
- Performance baselines should be reviewed monthly
- Emergency procedures should be tested quarterly
- All production changes require approval and documentation