# 📊 AIWFE Monitoring Stack Access Guide

## 🔑 GRAFANA LOGIN CREDENTIALS

**URL**: http://alienware.local:3000
**Username**: admin
**Password**: admin

## 📈 MONITORING STACK STATUS

### ✅ OPERATIONAL SERVICES
- **Grafana**: Running and healthy (http://localhost:3000)
- **Prometheus**: Running and healthy (http://localhost:9090)
- **Node Exporter**: Functional but experiencing broken pipe errors
- **Redis Exporter**: Operational
- **Postgres Exporter**: Operational
- **cAdvisor**: Collecting container metrics
- **AlertManager**: Running and healthy

### ⚠️ SERVICES WITH ISSUES
- **Blackbox Exporter**: DNS resolution issues - all external probes failing
- **Qdrant Monitoring**: Permission issues with API key access
- **Ollama Metrics**: No metrics endpoint available (404)
- **Worker Service**: Connection refused
- **WebUI Metrics**: Returning HTML instead of metrics
- **Caddy Metrics**: Service connection refused
- **PgBouncer Exporter**: DNS resolution issues

### ❌ MISSING SERVICES
- **Promtail**: Not deployed - log shipping not functional
- **Loki**: Not deployed - log aggregation unavailable
- **Log Collection**: Limited to container logs only

## 🎯 KEY METRICS AVAILABLE

### Infrastructure Metrics
- **System Resources**: CPU, memory, disk, network (via Node Exporter)
- **Container Stats**: Docker container performance (via cAdvisor)
- **Database Performance**: PostgreSQL metrics (via Postgres Exporter)
- **Cache Performance**: Redis metrics (via Redis Exporter)

### Application Metrics
- **API Health**: FastAPI application metrics from /api/v1/monitoring/metrics
- **Authentication**: Auth system metrics
- **Security**: Security monitoring metrics
- **Business KPIs**: User activity and business metrics

## 📊 AVAILABLE DASHBOARDS

Navigate to http://alienware.local:3000 and explore:

### System Dashboards
- **System Health Dashboard**: Node metrics, resource utilization
- **Authentication Dashboard**: Login patterns, failures, user activity
- **Security Overview**: Security events and threat detection
- **Threat Detection Dashboard**: Advanced security monitoring

### Application Dashboards
- **AI Workflow Engine Overview**: Comprehensive application health

## 🔧 PROMETHEUS CONFIGURATION

- **Data Source**: Configured with HTTP proxy access to http://prometheus:9090
- **Scrape Interval**: 15-30s depending on service type
- **Storage**: Local Prometheus storage with no external retention configured

## 🚨 ALERTING STATUS

- **AlertManager**: Running but configuration needs review
- **Alert Rules**: Check Prometheus alerts at http://localhost:9090/alerts
- **Notification Channels**: Configure in AlertManager (http://localhost:9093)

## 🐛 CURRENT MONITORING ISSUES

### High Priority
1. **Node Exporter Broken Pipes**: Metrics collection experiencing connection issues
2. **External Service Monitoring**: Blackbox exporter cannot reach external endpoints
3. **Log Aggregation Missing**: Promtail and Loki not deployed

### Medium Priority
1. **Service Discovery**: Some services not properly exposing metrics endpoints
2. **Certificate Issues**: mTLS configuration needs validation
3. **Network Resolution**: DNS issues affecting inter-service communication

## 🔍 MANUAL VERIFICATION COMMANDS

```bash
# Check Grafana health
curl -f http://localhost:3000/api/health

# Check Prometheus health
curl -f http://localhost:9090/-/healthy

# View all monitored targets
curl -s http://localhost:9090/api/v1/targets

# Check specific metric
curl -s http://localhost:9090/api/v1/query?query=up

# View Node Exporter metrics directly
curl -s http://localhost:9100/metrics | head -20
```

## 📋 IMMEDIATE ACTION ITEMS

1. **Login to Grafana**: Use admin/admin credentials
2. **Review System Health Dashboard**: Check resource utilization
3. **Investigate Node Exporter Issues**: Address broken pipe errors
4. **Deploy Log Aggregation**: Add Promtail and Loki services
5. **Fix Service Discovery**: Resolve DNS and networking issues
6. **Configure Alerting**: Set up proper alert rules and notifications

## 🔒 SECURITY CONSIDERATIONS

- **Default Credentials**: Change admin password after first login
- **Network Access**: Monitoring interfaces accessible only on local network
- **Metrics Exposure**: Some services exposing internal metrics without authentication
- **Certificate Management**: mTLS configuration partially implemented

---

**Created**: 2025-08-13  
**Last Updated**: 2025-08-13  
**Status**: Monitoring Stack Partially Operational