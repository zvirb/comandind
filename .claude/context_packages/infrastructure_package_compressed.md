# Infrastructure Context Package (Compressed)
**Target Agents**: k8s-architecture-specialist, deployment-orchestrator, infrastructure-orchestrator  
**Token Limit**: 4000 | **Estimated Size**: 3,200 tokens | **Compression Ratio**: 75%

## 🚀 CRITICAL INFRASTRUCTURE REQUIREMENTS

### Docker Compose Current State
```yaml
# Core Services Active
api: FastAPI (port 8001) → Authentication, Calendar, OAuth
webui: SvelteKit (port 5173) → User Interface  
worker: Celery → Background tasks
postgres: Database (port 5432) → Primary data store
redis: Cache/Session (port 6379) → Session management, pub/sub
caddy: Reverse proxy (ports 80/443) → SSL termination, routing
```

### Infrastructure Priority Actions
1. **Container Health**: All services must maintain 99.9% uptime
2. **SSL/TLS**: Caddy handles auto-certificates for aiwfe.com
3. **Database Resilience**: PostgreSQL with backup automation  
4. **Memory Management**: Redis for sessions + caching with 2GB limit
5. **Worker Scaling**: Celery horizontal scaling for task processing

## 🏗️ KUBERNETES MIGRATION REQUIREMENTS

### K8s Architecture Target
```yaml
Namespaces:
  - aiwfe-prod: Production workloads
  - aiwfe-staging: Testing environment
  - aiwfe-monitoring: Observability stack

Core Deployments:
  - api-deployment: 3 replicas, resource limits
  - webui-deployment: 2 replicas, CDN integration
  - worker-deployment: HPA 2-10 replicas based on queue
  - postgres-statefulset: PVC, backup policies
  - redis-deployment: Master/slave, persistence
```

### Critical Migration Path
1. **Phase 1**: Convert docker-compose to k8s manifests
2. **Phase 2**: Implement service mesh (Istio optional)
3. **Phase 3**: Add monitoring (Prometheus/Grafana)
4. **Phase 4**: CI/CD pipeline integration
5. **Phase 5**: Production cutover with rollback plan

## 🔧 DEPLOYMENT ORCHESTRATION STRATEGY

### Container Configurations
```dockerfile
# API Container Optimizations
FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8001
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Resource Limits (K8s)
resources:
  requests: {cpu: 100m, memory: 256Mi}
  limits: {cpu: 500m, memory: 1Gi}
```

### Service Mesh Integration
- **Ingress**: nginx-ingress or Traefik for K8s
- **Load Balancing**: Round-robin with health checks
- **Auto-scaling**: HPA based on CPU/memory + queue depth
- **Circuit Breakers**: Retry logic for external API calls

## 📊 MONITORING & OBSERVABILITY

### Metrics Collection
```yaml
Prometheus Targets:
  - /metrics: Application metrics
  - /health: Service health endpoints
  - Node exporter: System metrics
  - PostgreSQL exporter: DB performance
  - Redis exporter: Cache metrics

Critical Alerts:
  - Pod restart rate > 3/hour
  - Memory usage > 80%
  - Response time > 2s
  - Queue depth > 100 items
  - SSL certificate expiry < 30 days
```

### Logging Strategy
```yaml
Log Aggregation:
  - ELK Stack: Elasticsearch, Logstash, Kibana
  - Alternative: Grafana Loki for cost efficiency
  - Retention: 30 days application, 7 days debug
  - Structured logging: JSON format with trace IDs
```

## 🔒 SECURITY & COMPLIANCE

### Infrastructure Security
- **mTLS**: Service-to-service encryption in K8s
- **RBAC**: Kubernetes role-based access control
- **Network Policies**: Pod-to-pod communication restrictions  
- **Secret Management**: Kubernetes secrets + Vault integration
- **Image Scanning**: Trivy/Snyk in CI pipeline

### Backup & Disaster Recovery
```yaml
Backup Strategy:
  Database: 
    - Daily full backup to object storage
    - WAL-E continuous archiving
    - 30-day retention policy
  Redis:
    - Snapshot every 6 hours
    - AOF for transaction durability
  Configuration:
    - GitOps with ArgoCD
    - Infrastructure as Code (Terraform)
```

## 🎯 SUCCESS CRITERIA

### Performance Targets
- **API Response**: p95 < 500ms, p99 < 1s
- **Database**: Query time p95 < 100ms
- **Worker Processing**: Task completion < 30s
- **Container Startup**: < 30s for any service
- **Deployment Time**: Rolling update < 5 minutes

### Reliability Metrics
- **Uptime**: 99.9% (< 8.76 hours downtime/year)
- **Error Rate**: < 0.1% of requests
- **Recovery Time**: RTO < 15 minutes, RPO < 5 minutes
- **Scaling Response**: Auto-scale trigger < 2 minutes

## ⚡ IMMEDIATE ACTIONS REQUIRED

### Phase 5 Implementation Tasks
1. **Docker Optimization**: Multi-stage builds, security scanning
2. **K8s Manifest Generation**: Helm charts with environment values
3. **Monitoring Setup**: Prometheus/Grafana stack deployment
4. **CI/CD Pipeline**: GitHub Actions → K8s deployment
5. **Security Hardening**: Pod security policies, network isolation

### Validation Requirements
- **Infrastructure Health**: All services respond to /health endpoints
- **Performance Testing**: Load test with 1000 concurrent users
- **Security Scan**: Container vulnerability assessment
- **Backup Testing**: Restore simulation successful
- **Failover Testing**: Service failure recovery < 60s

### Configuration Files Location
- `docker-compose.yml`: Current production setup
- `k8s/`: Kubernetes manifests (to be created)
- `monitoring/`: Prometheus, Grafana configs
- `scripts/deployment/`: Automation scripts
- `.github/workflows/`: CI/CD pipelines

**CRITICAL**: All infrastructure changes require production validation with evidence (curl tests, health checks, monitoring dashboards) before Step 6 validation.