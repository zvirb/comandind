# SSL Certificate Automation for aiwfe.com

## Overview

This document describes the comprehensive SSL certificate automation system implemented for aiwfe.com, ensuring zero-downtime certificate management with proactive monitoring and automatic renewal.

## Current Certificate Status

- **Domain**: aiwfe.com
- **Provider**: Let's Encrypt (via Caddy automatic HTTPS)
- **Expiry**: November 8, 2025
- **Days Remaining**: ~85 days (as of August 15, 2025)
- **Status**: HEALTHY ✅

## Components

### 1. Caddy Automatic HTTPS

Caddy server handles automatic certificate provisioning and renewal through Let's Encrypt ACME protocol.

**Configuration**: `/home/marku/ai_workflow_engine/config/caddy/Caddyfile`

Key features:
- Automatic certificate provisioning on first HTTPS request
- Automatic renewal 30 days before expiry
- HTTP to HTTPS redirect
- Certificate storage in `/data/caddy/certificates/`

### 2. SSL Certificate Automation Script

**Location**: `/home/marku/ai_workflow_engine/scripts/ssl_certificate_automation.py`

Features:
- Certificate status monitoring
- Expiry tracking and alerting
- Automated backups
- Health endpoint verification
- Prometheus metrics generation

**Usage**:
```bash
# Check certificate status
python3 scripts/ssl_certificate_automation.py --check

# Backup certificates
python3 scripts/ssl_certificate_automation.py --backup

# Trigger renewal check
python3 scripts/ssl_certificate_automation.py --renew

# Verify SSL endpoint
python3 scripts/ssl_certificate_automation.py --verify

# Update monitoring metrics
python3 scripts/ssl_certificate_automation.py --monitor

# Run full automation cycle
python3 scripts/ssl_certificate_automation.py --run
```

### 3. Automated Cron Job

**Script**: `/home/marku/ai_workflow_engine/scripts/ssl_automation_cron.sh`

**Schedule**: Daily at 2:00 AM UTC

```cron
0 2 * * * /home/marku/ai_workflow_engine/scripts/ssl_automation_cron.sh
```

Actions performed:
1. Check certificate expiry status
2. Trigger renewal if needed (< 30 days remaining)
3. Backup current certificates
4. Verify endpoint availability
5. Update monitoring metrics
6. Log all actions

### 4. SSL Health API Endpoints

**Base Path**: `/api/v1/ssl`

#### GET /api/v1/ssl/health
Returns comprehensive certificate health information:
- Certificate expiry status
- Days remaining
- Endpoint verification results
- Backup status
- Caddy server health

#### GET /api/v1/ssl/metrics
Returns Prometheus-compatible metrics:
- Certificate days remaining
- Endpoint response times
- Validation status
- Backup timestamps

#### POST /api/v1/ssl/trigger-renewal
Manually trigger certificate renewal check

#### POST /api/v1/ssl/backup
Manually trigger certificate backup

### 5. Prometheus Monitoring

**Metrics File**: `/home/marku/ai_workflow_engine/metrics/ssl_metrics.prom`

Available metrics:
- `ssl_cert_days_remaining{domain="aiwfe.com"}` - Days until certificate expiry
- `ssl_cert_status{domain="aiwfe.com",status="HEALTHY"}` - Certificate health status
- `ssl_endpoint_https_accessible{domain="aiwfe.com"}` - HTTPS endpoint accessibility
- `ssl_endpoint_cert_valid{domain="aiwfe.com"}` - Certificate validity
- `ssl_endpoint_redirect_working{domain="aiwfe.com"}` - HTTP to HTTPS redirect status
- `ssl_endpoint_response_time_ms{domain="aiwfe.com"}` - SSL handshake response time

**Alert Rules**: `/home/marku/ai_workflow_engine/config/prometheus/ssl_certificate_rules.yml`

Configured alerts:
- **SSLCertificateExpiringSoon** (30 days warning)
- **SSLCertificateExpiringCritical** (7 days critical)
- **SSLCertificateExpired** (certificate expired)
- **SSLCertificateChainInvalid** (chain issues)
- **SSLCertificateSubjectMismatch** (domain mismatch)

## Certificate Backup Strategy

### Backup Location
`/home/marku/ai_workflow_engine/ssl_backups/`

### Backup Schedule
- Automatic daily backups via cron job
- Manual backups available via API or script
- Retention: 30 days (older backups automatically cleaned)

### Backup Contents
- Certificate file (.crt)
- Private key (.key)
- Metadata (.json)

### Recovery Procedure
1. Locate backup directory: `ssl_backups/cert_backup_aiwfe.com_YYYYMMDD_HHMMSS/`
2. Copy certificates to Caddy container
3. Reload Caddy configuration

## Renewal Process

### Automatic Renewal (Caddy)
Caddy automatically renews certificates when:
- Certificate has less than 30 days remaining
- Renewal window suggested by Let's Encrypt is reached

### Manual Renewal Trigger
```bash
# Via automation script
python3 scripts/ssl_certificate_automation.py --renew

# Via API
curl -X POST http://localhost:8000/api/v1/ssl/trigger-renewal

# Via Caddy reload
docker exec ai_workflow_engine-caddy_reverse_proxy-1 caddy reload --config /etc/caddy/Caddyfile
```

### Renewal Verification
1. Check new certificate expiry date
2. Verify certificate chain validity
3. Test HTTPS endpoint accessibility
4. Confirm metrics updated

## Monitoring & Alerting

### Health Monitoring
- Continuous monitoring via Prometheus
- Daily automated health checks via cron
- Real-time API health endpoints

### Alert Thresholds
- **30 days**: Warning alert, renewal process starts
- **7 days**: Critical alert, immediate action required
- **0 days**: Emergency alert, certificate expired

### Alert Channels
Currently logs to:
- `/home/marku/ai_workflow_engine/logs/ssl_automation.log`
- `/home/marku/ai_workflow_engine/logs/ssl_automation_cron.log`

To add email/Slack/PagerDuty alerts, modify the `send_alert()` method in `ssl_certificate_automation.py`.

## Troubleshooting

### Common Issues

#### Certificate Not Renewing
1. Check Caddy logs: `docker logs ai_workflow_engine-caddy_reverse_proxy-1`
2. Verify DNS resolution for domain
3. Check Let's Encrypt rate limits
4. Ensure ports 80/443 are accessible

#### Health Check Failures
1. Verify Caddy container is running
2. Check network connectivity
3. Review firewall rules
4. Validate certificate files exist

#### Backup Failures
1. Check disk space in backup directory
2. Verify Docker permissions
3. Review automation script logs

### Manual Certificate Installation
If automatic renewal fails:

1. Generate new certificate manually:
```bash
docker exec -it ai_workflow_engine-caddy_reverse_proxy-1 caddy trust
```

2. Or restore from backup:
```bash
# Copy backup certificates
docker cp ssl_backups/latest/aiwfe.com.crt ai_workflow_engine-caddy_reverse_proxy-1:/data/caddy/certificates/
docker cp ssl_backups/latest/aiwfe.com.key ai_workflow_engine-caddy_reverse_proxy-1:/data/caddy/certificates/
```

3. Reload Caddy:
```bash
docker exec ai_workflow_engine-caddy_reverse_proxy-1 caddy reload --config /etc/caddy/Caddyfile
```

## Security Considerations

### Certificate Storage
- Certificates stored in Docker volume with restricted permissions
- Backups stored with 600 permissions (owner read/write only)
- Private keys never exposed via API or logs

### Access Control
- API endpoints require authentication (except health check)
- Manual renewal requires admin privileges
- Backup access restricted to system user

### Best Practices
- Regular certificate rotation (90-day Let's Encrypt certificates)
- Automated monitoring and alerting
- Secure backup storage
- Principle of least privilege for certificate access

## Testing

### Verify SSL Configuration
```bash
# Check certificate details
openssl s_client -connect aiwfe.com:443 -servername aiwfe.com < /dev/null | openssl x509 -noout -dates

# Test SSL/TLS configuration
curl -I https://aiwfe.com

# Check certificate chain
openssl s_client -connect aiwfe.com:443 -showcerts < /dev/null

# SSL Labs test (external)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=aiwfe.com
```

### Test Automation
```bash
# Run full test cycle
python3 scripts/ssl_certificate_automation.py --run

# Check metrics generation
cat /home/marku/ai_workflow_engine/metrics/ssl_metrics.json
cat /home/marku/ai_workflow_engine/metrics/ssl_metrics.prom

# Verify cron job
crontab -l | grep ssl_automation_cron
```

## Maintenance

### Regular Tasks
- Review automation logs weekly
- Verify backup integrity monthly
- Update alert thresholds as needed
- Test recovery procedure quarterly

### Log Rotation
Logs automatically rotate when reaching 100MB. Old logs are moved to `.old` suffix.

### Updates
Keep Caddy updated for latest security patches and Let's Encrypt compatibility:
```bash
docker pull caddy:latest
docker-compose up -d caddy_reverse_proxy
```

## Contact & Support

For issues with SSL certificate automation:
1. Check this documentation
2. Review logs in `/home/marku/ai_workflow_engine/logs/`
3. Verify Prometheus alerts
4. Contact system administrator

## Appendix

### File Locations
- **Automation Script**: `/home/marku/ai_workflow_engine/scripts/ssl_certificate_automation.py`
- **Cron Script**: `/home/marku/ai_workflow_engine/scripts/ssl_automation_cron.sh`
- **API Module**: `/home/marku/ai_workflow_engine/app/api/ssl_health.py`
- **Prometheus Rules**: `/home/marku/ai_workflow_engine/config/prometheus/ssl_certificate_rules.yml`
- **Metrics**: `/home/marku/ai_workflow_engine/metrics/ssl_metrics.*`
- **Logs**: `/home/marku/ai_workflow_engine/logs/ssl_automation*.log`
- **Backups**: `/home/marku/ai_workflow_engine/ssl_backups/`

### Dependencies
- Python 3.x with cryptography library
- Docker with Caddy container
- Prometheus for monitoring
- Let's Encrypt for certificates

---

*Last Updated: August 15, 2025*
*Version: 1.0*