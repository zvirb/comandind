# Security Monitoring Infrastructure Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the advanced security monitoring and alerting infrastructure for the AI Workflow Engine. The implementation includes real-time threat detection, automated response capabilities, and comprehensive monitoring dashboards.

## 🛡️ Components Deployed

### Core Security Services

1. **Security Metrics Service** (`security_metrics_service.py`)
   - Prometheus metrics collection for security events
   - Real-time security health scoring
   - Comprehensive event rate monitoring

2. **Security Event Processor** (`security_event_processor.py`)
   - Real-time security event processing
   - Event correlation and pattern detection
   - High-priority event queue management

3. **Automated Security Response Service** (`automated_security_response_service.py`)
   - Automated IP blocking and rate limiting
   - User suspension capabilities
   - Threat quarantine and escalation

4. **Threat Detection Service** (`threat_detection_service.py`)
   - Advanced threat pattern recognition
   - Anomaly detection using statistical analysis
   - Behavioral analysis and baseline learning

### Monitoring Infrastructure

5. **AlertManager Integration**
   - Multi-tier alert routing and escalation
   - Email and webhook alert delivery
   - Alert deduplication and throttling

6. **Grafana Security Dashboards**
   - Security overview dashboard
   - Authentication and authorization monitoring
   - Threat detection and anomaly visualization
   - System health monitoring

7. **Prometheus Security Rules**
   - Comprehensive alerting rules
   - Security metric aggregation
   - Performance thresholds

### API Integration

8. **Security Metrics Router** (`security_metrics_router.py`)
   - Prometheus metrics endpoint (`/api/v1/security/metrics`)
   - Security health status (`/api/v1/security/health`)
   - Active security blocks management
   - Webhook integration for external alerts

## 📋 Prerequisites

### System Requirements

- Docker and Docker Compose
- Python 3.8+ with required dependencies
- Minimum 4GB RAM for monitoring services
- 10GB disk space for metrics storage

### Dependencies

```bash
# Python packages (already in pyproject.toml)
prometheus-client
numpy
redis
aiofiles
```

### Network Requirements

- Port 9090: Prometheus
- Port 9093: AlertManager
- Port 3000: Grafana
- Port 8000: API (security endpoints)
- Port 9091: Security metrics (internal)

## 🚀 Deployment Steps

### 1. Pre-Deployment Validation

Run the validation script to ensure all components are properly configured:

```bash
./scripts/validate_security_monitoring.sh
```

This script validates:
- Docker Compose configuration
- Security service files
- Configuration file integrity
- Python dependencies
- Service integration
- Dashboard structure

### 2. Configuration Setup

#### AlertManager Configuration

The AlertManager is configured with multi-tier routing:

```yaml
# config/alertmanager/alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'security-team'
  
  routes:
    - match:
        severity: critical
      receiver: 'security-critical'
      group_wait: 10s
      repeat_interval: 5m
```

#### Prometheus Security Rules

Security alerting rules are defined in:
- `config/prometheus/security_rules.yml`

#### Grafana Dashboards

Pre-configured dashboards:
- Security Overview: `/security/security-overview`
- Authentication Dashboard: `/security/authentication-dashboard`
- Threat Detection: `/security/threat-detection-dashboard`
- System Health: `/system/system-health-dashboard`

### 3. Service Deployment

#### Standard Deployment

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs -f alertmanager
docker-compose logs -f api
```

#### mTLS Deployment (Production)

```bash
# Deploy with mTLS security
docker-compose -f docker-compose-mtls.yml up -d

# Verify certificate setup
docker-compose -f docker-compose-mtls.yml logs alertmanager | grep -i certificate
```

### 4. Service Startup Verification

The security services are automatically started with the API:

```bash
# Check API logs for security service initialization
docker-compose logs api | grep -i "security monitoring"

# Expected output:
# Initializing security monitoring services...
# Security monitoring services initialized successfully.
```

### 5. Endpoint Testing

#### Health Check

```bash
# Check overall security monitoring health
curl http://localhost:8000/api/v1/security/health

# Expected response:
{
  "overall_status": "healthy",
  "components": {
    "security_metrics_service": {"status": "running"},
    "security_event_processor": {"status": "running"},
    "automated_response_service": {"status": "running"}
  }
}
```

#### Metrics Endpoint

```bash
# Verify Prometheus metrics
curl http://localhost:8000/api/v1/security/metrics

# Should return Prometheus format metrics
```

#### Dashboard Access

- Grafana: http://localhost:3000
- AlertManager: http://localhost:9093
- Prometheus: http://localhost:9090

## 🔧 Configuration Customization

### Alert Routing

Customize alert routing in `config/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'security-team'
    email_configs:
      - to: 'your-security-team@company.com'
        subject: '[SECURITY] {{ .GroupLabels.alertname }}'
```

### Detection Thresholds

Modify threat detection thresholds in the threat detection service:

```python
# app/shared/services/threat_detection_service.py
self.threat_rules = {
    ThreatType.BRUTE_FORCE: {
        'auth_failure_rate': 10,  # failures per minute
        'auth_failure_burst': 20,  # failures in 5 minutes
    }
}
```

### Security Response Actions

Configure automated response actions:

```python
# app/shared/services/automated_security_response_service.py
self.threat_thresholds = {
    'auth_failure_rate': 5,      # failures per minute
    'violation_rate': 3,         # violations per minute
    'anomaly_score': 0.8,        # anomaly detection threshold
}
```

## 📊 Monitoring and Alerting

### Key Metrics

The security monitoring system tracks:

- Authentication success/failure rates
- Authorization violations
- Data access patterns and anomalies
- Tool execution security events
- Network security validation
- Threat detection events
- System health scores

### Alert Categories

1. **Critical Alerts** (immediate response required)
   - Security breaches
   - Authentication bypasses
   - Sandbox escapes

2. **High Alerts** (urgent attention needed)
   - Multiple failed logins
   - Unauthorized access attempts
   - Resource abuse

3. **Medium Alerts** (investigation needed)
   - Unusual access patterns
   - Performance anomalies
   - Configuration changes

4. **Low Alerts** (informational)
   - Successful authentications
   - Routine operations

### Dashboard Features

#### Security Overview Dashboard
- Real-time security health score
- Authentication and authorization events
- Security violation trends
- Active threat detections

#### Authentication Dashboard
- Authentication attempt rates
- Failure analysis by IP and reason
- JWT token operations
- Cross-service authentication events

#### Threat Detection Dashboard
- Anomaly score distributions
- Threat detection events by type
- Rate limiting violations
- Data access anomalies

#### System Health Dashboard
- Security monitoring system status
- Database connection health
- Active user sessions
- Security audit log rates

## 🔒 Security Features

### Automated Response Capabilities

1. **IP Blocking**
   - Automatic blocking of malicious IPs
   - Configurable duration and escalation
   - Distributed coordination via Redis

2. **User Suspension**
   - Temporary account suspension for anomalous behavior
   - Administrative override capabilities
   - Audit trail maintenance

3. **Rate Limiting**
   - Dynamic rate limiting based on behavior
   - Per-endpoint and per-user limits
   - Real-time enforcement

4. **Threat Quarantine**
   - Isolation of detected threats
   - Evidence preservation
   - Incident response integration

### Threat Detection Algorithms

1. **Statistical Anomaly Detection**
   - Z-score based analysis
   - Baseline learning and adaptation
   - Multi-metric correlation

2. **Behavioral Analysis**
   - User behavior profiling
   - Deviation detection
   - Temporal pattern analysis

3. **Pattern Recognition**
   - Brute force attack detection
   - Data exfiltration patterns
   - Privilege escalation attempts

## 🚨 Incident Response

### Alert Escalation

The system implements a multi-tier escalation:

1. **Level 1**: Security team notification
2. **Level 2**: Management escalation
3. **Level 3**: Executive notification for critical incidents

### Incident Management Integration

The webhook endpoint (`/api/v1/security/alerts/webhook`) accepts alerts from:
- AlertManager
- External security tools
- Third-party monitoring services

### Manual Override Capabilities

Administrators can:
- Create manual security actions
- Revoke automated responses
- Adjust detection thresholds
- Review active security blocks

## 📈 Performance and Scaling

### Resource Requirements

- **CPU**: 2 cores minimum for monitoring services
- **Memory**: 4GB minimum (8GB recommended)
- **Storage**: 50GB for 30 days of metrics retention
- **Network**: 1Gbps for real-time processing

### Scaling Considerations

1. **Horizontal Scaling**
   - Multiple worker instances for event processing
   - Load balancing for metrics collection
   - Redis clustering for coordination

2. **Vertical Scaling**
   - Increased memory for baseline storage
   - Additional CPU for complex analysis
   - Faster storage for metrics

### Performance Monitoring

Monitor these key performance indicators:
- Event processing latency
- Queue sizes and throughput
- Detection accuracy and false positive rates
- Response time for automated actions

## 🔧 Troubleshooting

### Common Issues

1. **Service Startup Failures**
   ```bash
   # Check service logs
   docker-compose logs api | grep -i error
   
   # Verify Redis connectivity
   docker-compose exec api python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
   ```

2. **Missing Metrics**
   ```bash
   # Check Prometheus target health
   curl http://localhost:9090/api/v1/targets
   
   # Verify security metrics endpoint
   curl http://localhost:8000/api/v1/security/metrics
   ```

3. **Alert Delivery Issues**
   ```bash
   # Check AlertManager configuration
   curl http://localhost:9093/api/v1/status
   
   # Verify SMTP settings
   docker-compose logs alertmanager | grep -i smtp
   ```

### Log Analysis

Key log patterns to monitor:

```bash
# Security service initialization
grep "Security monitoring services initialized" logs/api.log

# Threat detections
grep "THREAT DETECTED" logs/api.log

# Automated responses
grep "Security action.*executed" logs/api.log

# System health issues
grep "Security monitoring status.*degraded" logs/api.log
```

## 📚 Additional Resources

### API Documentation

The security monitoring system exposes these endpoints:

- `GET /api/v1/security/health` - System health status
- `GET /api/v1/security/metrics` - Prometheus metrics
- `GET /api/v1/security/summary` - Metrics summary
- `GET /api/v1/security/active-blocks` - Active security actions
- `POST /api/v1/security/manual-action` - Create manual action
- `DELETE /api/v1/security/action/{type}/{target}` - Revoke action
- `POST /api/v1/security/alerts/webhook` - External alert webhook
- `GET /api/v1/security/check-ip/{ip}` - Check IP status
- `GET /api/v1/security/check-user/{user_id}` - Check user status

### Configuration Files

- `config/alertmanager/alertmanager.yml` - Alert routing configuration
- `config/prometheus/security_rules.yml` - Prometheus alerting rules
- `config/grafana/provisioning/dashboards/` - Dashboard definitions
- `docker-compose.yml` - Service orchestration
- `docker-compose-mtls.yml` - Production mTLS deployment

### Security Models

The system uses these database models:
- `SecurityViolation` - Security violation records
- `SecurityAction` - Automated response actions
- `DataAccessLog` - Data access audit trail
- `AuditLog` - Comprehensive audit logging

## ✅ Validation Checklist

Before going live, verify:

- [ ] All services start successfully
- [ ] Security metrics are being collected
- [ ] Dashboards display data correctly
- [ ] Alerts are delivered properly
- [ ] Automated responses function as expected
- [ ] API endpoints respond correctly
- [ ] Database models are deployed
- [ ] SSL/TLS certificates are valid (for mTLS)
- [ ] Backup and recovery procedures are tested
- [ ] Security team is trained on the system

## 🎯 Success Criteria

The deployment is successful when:

1. **Real-time Monitoring**: Security events are processed within 5 seconds
2. **Threat Detection**: Anomalies are detected with <10% false positive rate
3. **Automated Response**: Security actions execute within 30 seconds
4. **Alert Delivery**: Critical alerts delivered within 2 minutes
5. **Dashboard Performance**: Dashboards load within 3 seconds
6. **System Availability**: 99.9% uptime for monitoring services

This comprehensive security monitoring infrastructure provides enterprise-grade protection with real-time threat detection, automated response capabilities, and detailed visibility into security events across the AI Workflow Engine platform.