# AI Workflow Engine - Kubernetes Migration Guide

## Overview

This guide provides a comprehensive roadmap for migrating the AI Workflow Engine from Docker Compose to Kubernetes, enabling cloud-native scalability, advanced orchestration, and production-ready operations.

## Current State Analysis

### Docker Compose to Kubernetes Mapping

```yaml
Current Architecture          →    Kubernetes Resources
==================           →    ==================
Services (15+)               →    Deployments/StatefulSets
docker-compose.yml           →    Helm Charts
Volumes                      →    PersistentVolumes/PVCs
Networks                     →    Services/NetworkPolicies
Secrets                      →    Secrets/ConfigMaps
Health checks                →    Liveness/Readiness Probes
Dependencies                 →    Init Containers
Load balancing               →    Ingress/Service Mesh
```

## Phase 1: Kubernetes Foundation Setup

### 1.1 Cluster Architecture Design

```yaml
Production Cluster Specification:
├── Control Plane (3 nodes)
│   ├── etcd cluster (HA)
│   ├── API server (load balanced)
│   ├── Controller manager
│   └── Scheduler
├── Worker Nodes (5+ nodes)
│   ├── Node 1-2: Application workloads
│   ├── Node 3-4: Database workloads (SSD storage)
│   ├── Node 5: GPU workload (Ollama)
│   └── Auto-scaling enabled
└── Infrastructure Services
    ├── Ingress Controller (NGINX/Traefik)
    ├── Service Mesh (Istio/Linkerd)
    ├── Certificate Manager (cert-manager)
    └── Storage Provider (CSI drivers)
```

### 1.2 Namespace Strategy

```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-workflow-engine-production
  labels:
    environment: production
    app.kubernetes.io/name: ai-workflow-engine
---
apiVersion: v1
kind: Namespace
metadata:
  name: ai-workflow-engine-staging
  labels:
    environment: staging
    app.kubernetes.io/name: ai-workflow-engine
---
apiVersion: v1
kind: Namespace
metadata:
  name: ai-workflow-engine-monitoring
  labels:
    component: monitoring
    app.kubernetes.io/name: ai-workflow-engine
```

## Phase 2: Storage Strategy

### 2.1 Persistent Volume Design

```yaml
# storage-classes.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ai-workflow-engine-ssd
  labels:
    app.kubernetes.io/name: ai-workflow-engine
provisioner: kubernetes.io/aws-ebs  # or gce-pd, azure-disk
parameters:
  type: gp3
  fsType: ext4
  encrypted: "true"
allowVolumeExpansion: true
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ai-workflow-engine-nvme
  labels:
    app.kubernetes.io/name: ai-workflow-engine
    performance: high
provisioner: kubernetes.io/aws-ebs
parameters:
  type: io2
  iops: "3000"
  fsType: ext4
  encrypted: "true"
allowVolumeExpansion: true
reclaimPolicy: Retain
```

### 2.2 Database StatefulSet Configuration

```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: ai-workflow-engine-production
  labels:
    app.kubernetes.io/name: postgres
    app.kubernetes.io/component: database
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
        app.kubernetes.io/component: database
    spec:
      securityContext:
        fsGroup: 999
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: database
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
          subPath: pgdata
        - name: postgres-config
          mountPath: /etc/postgresql
        - name: postgres-certs
          mountPath: /etc/certs
          readOnly: true
        livenessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2"
      volumes:
      - name: postgres-config
        configMap:
          name: postgres-config
      - name: postgres-certs
        secret:
          secretName: postgres-tls
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ai-workflow-engine-ssd
      resources:
        requests:
          storage: 50Gi
```

## Phase 3: Application Migration

### 3.1 API Deployment Configuration

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ai-workflow-engine-production
  labels:
    app.kubernetes.io/name: api
    app.kubernetes.io/component: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app.kubernetes.io/name: api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: api
        app.kubernetes.io/component: backend
    spec:
      initContainers:
      - name: wait-for-postgres
        image: postgres:15-alpine
        command:
        - /bin/sh
        - -c
        - |
          until pg_isready -h postgres -U $POSTGRES_USER -d $POSTGRES_DB; do
            echo "Waiting for PostgreSQL..."
            sleep 2
          done
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: username
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: database
      - name: run-migrations
        image: ai_workflow_engine/api:latest
        command:
        - /bin/sh
        - -c
        - python -m alembic upgrade head
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
      containers:
      - name: api
        image: ai_workflow_engine/api:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: ai-workflow-engine-production
  labels:
    app.kubernetes.io/name: api
spec:
  selector:
    app.kubernetes.io/name: api
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  type: ClusterIP
```

### 3.2 WebUI Deployment Configuration

```yaml
# webui-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webui
  namespace: ai-workflow-engine-production
  labels:
    app.kubernetes.io/name: webui
    app.kubernetes.io/component: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: webui
  template:
    metadata:
      labels:
        app.kubernetes.io/name: webui
        app.kubernetes.io/component: frontend
    spec:
      containers:
      - name: webui
        image: ai_workflow_engine/webui:latest
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: API_BASE_URL
          value: "http://api:8000"
        - name: NODE_ENV
          value: "production"
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
---
apiVersion: v1
kind: Service
metadata:
  name: webui
  namespace: ai-workflow-engine-production
  labels:
    app.kubernetes.io/name: webui
spec:
  selector:
    app.kubernetes.io/name: webui
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
    name: http
  type: ClusterIP
```

## Phase 4: Advanced Features

### 4.1 Horizontal Pod Autoscaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: ai-workflow-engine-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### 4.2 Pod Disruption Budget

```yaml
# pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: ai-workflow-engine-production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: api
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: postgres-pdb
  namespace: ai-workflow-engine-production
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
```

### 4.3 Network Policies

```yaml
# network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: ai-workflow-engine-production
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: webui
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: qdrant
    ports:
    - protocol: TCP
      port: 6333
  # Allow DNS resolution
  - to: []
    ports:
    - protocol: UDP
      port: 53
```

## Phase 5: Ingress and Load Balancing

### 5.1 Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-workflow-engine-ingress
  namespace: ai-workflow-engine-production
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$1
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - aiwfe.com
    - api.aiwfe.com
    secretName: ai-workflow-engine-tls
  rules:
  - host: aiwfe.com
    http:
      paths:
      - path: /(.*)
        pathType: Prefix
        backend:
          service:
            name: webui
            port:
              number: 3000
  - host: api.aiwfe.com
    http:
      paths:
      - path: /(.*)
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 8000
```

### 5.2 Certificate Management

```yaml
# cert-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: markuszvirbulis@gmail.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
    - dns01:
        cloudflare:
          email: markuszvirbulis@gmail.com
          apiTokenSecretRef:
            name: cloudflare-api-token
            key: api-token
```

## Phase 6: Monitoring and Observability

### 6.1 Prometheus Configuration

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: ai-workflow-engine-monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "/etc/prometheus/rules/*.yml"
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093
    
    scrape_configs:
    - job_name: 'kubernetes-apiservers'
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https
    
    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
    
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name
    
    - job_name: 'ai-workflow-engine-api'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - ai-workflow-engine-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_name]
        action: keep
        regex: api
      - source_labels: [__meta_kubernetes_endpoint_port_name]
        action: keep
        regex: http
```

### 6.2 Grafana Dashboard ConfigMap

```yaml
# grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-workflow-engine-dashboard
  namespace: ai-workflow-engine-monitoring
  labels:
    grafana_dashboard: "1"
data:
  ai-workflow-engine.json: |
    {
      "dashboard": {
        "id": null,
        "title": "AI Workflow Engine - Kubernetes",
        "tags": ["kubernetes", "ai-workflow-engine"],
        "timezone": "browser",
        "panels": [
          {
            "title": "API Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{job=\"ai-workflow-engine-api\"}[5m])",
                "legendFormat": "{{method}} {{status}}"
              }
            ]
          },
          {
            "title": "Pod CPU Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(container_cpu_usage_seconds_total{namespace=\"ai-workflow-engine-production\"}[5m]) * 100",
                "legendFormat": "{{pod}}"
              }
            ]
          },
          {
            "title": "Pod Memory Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "container_memory_usage_bytes{namespace=\"ai-workflow-engine-production\"} / 1024 / 1024",
                "legendFormat": "{{pod}} - MB"
              }
            ]
          }
        ],
        "time": {
          "from": "now-1h",
          "to": "now"
        },
        "refresh": "30s"
      }
    }
```

## Phase 7: Helm Charts

### 7.1 Helm Chart Structure

```
helm-chart/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── values-staging.yaml
├── templates/
│   ├── deployment-api.yaml
│   ├── deployment-webui.yaml
│   ├── deployment-worker.yaml
│   ├── statefulset-postgres.yaml
│   ├── statefulset-redis.yaml
│   ├── statefulset-qdrant.yaml
│   ├── service-api.yaml
│   ├── service-webui.yaml
│   ├── service-postgres.yaml
│   ├── service-redis.yaml
│   ├── service-qdrant.yaml
│   ├── ingress.yaml
│   ├── configmap-api.yaml
│   ├── secret-postgres.yaml
│   ├── hpa-api.yaml
│   ├── pdb-api.yaml
│   ├── networkpolicy.yaml
│   └── NOTES.txt
├── charts/  # Sub-charts
│   ├── postgresql/
│   ├── redis/
│   └── monitoring/
└── crds/  # Custom Resource Definitions
```

### 7.2 Helm Values Configuration

```yaml
# values.yaml
global:
  imageRegistry: "docker.io"
  imagePullSecrets: []
  storageClass: "ai-workflow-engine-ssd"
  
api:
  image:
    repository: ai_workflow_engine/api
    tag: "latest"
    pullPolicy: IfNotPresent
  replicaCount: 3
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  
webui:
  image:
    repository: ai_workflow_engine/webui
    tag: "latest"
    pullPolicy: IfNotPresent
  replicaCount: 2
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"

postgresql:
  enabled: true
  persistence:
    enabled: true
    size: "50Gi"
    storageClass: "ai-workflow-engine-ssd"
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2"

redis:
  enabled: true
  persistence:
    enabled: true
    size: "10Gi"
    storageClass: "ai-workflow-engine-ssd"
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "1Gi"
      cpu: "500m"

qdrant:
  enabled: true
  persistence:
    enabled: true
    size: "100Gi"
    storageClass: "ai-workflow-engine-nvme"
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2"

monitoring:
  prometheus:
    enabled: true
    retention: "15d"
    storage: "50Gi"
  grafana:
    enabled: true
    adminPassword: "admin123"  # Should be in secrets
  alertmanager:
    enabled: true

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: aiwfe.com
      paths:
        - path: /
          pathType: Prefix
          service: webui
    - host: api.aiwfe.com
      paths:
        - path: /
          pathType: Prefix
          service: api
  tls:
    - secretName: ai-workflow-engine-tls
      hosts:
        - aiwfe.com
        - api.aiwfe.com

networkPolicies:
  enabled: true
  defaultDeny: true

podDisruptionBudgets:
  enabled: true
  api:
    minAvailable: 2
  postgres:
    minAvailable: 1
```

## Phase 8: CI/CD Integration

### 8.1 GitHub Actions Kubernetes Deployment

```yaml
# .github/workflows/deploy-kubernetes.yml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
          
    - name: Build and push API image
      id: build
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./docker/api/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  security-scan:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ needs.build-and-push.outputs.image-tag }}
        format: 'sarif'
        output: 'trivy-results.sarif'
        
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  deploy-staging:
    needs: [build-and-push, security-scan]
    runs-on: ubuntu-latest
    environment: staging
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}
        
    - name: Deploy to staging
      run: |
        helm upgrade --install ai-workflow-engine-staging ./helm-chart \
          --namespace ai-workflow-engine-staging \
          --create-namespace \
          --values ./helm-chart/values-staging.yaml \
          --set api.image.tag="${{ needs.build-and-push.outputs.image-tag }}" \
          --wait --timeout=10m
          
    - name: Run smoke tests
      run: |
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=api \
          --namespace ai-workflow-engine-staging --timeout=300s
        
        # Run API health check
        kubectl port-forward service/api 8080:8000 \
          --namespace ai-workflow-engine-staging &
        sleep 5
        curl -f http://localhost:8080/health || exit 1

  deploy-production:
    needs: [build-and-push, security-scan, deploy-staging]
    runs-on: ubuntu-latest
    environment: production
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}
        
    - name: Deploy to production (Blue-Green)
      run: |
        # Determine current and target environments
        CURRENT_ENV=$(kubectl get configmap deployment-state \
          --namespace ai-workflow-engine-production \
          -o jsonpath='{.data.active-environment}' 2>/dev/null || echo "blue")
        TARGET_ENV=$([ "$CURRENT_ENV" = "blue" ] && echo "green" || echo "blue")
        
        echo "Deploying to $TARGET_ENV environment"
        
        # Deploy to target environment
        helm upgrade --install ai-workflow-engine-$TARGET_ENV ./helm-chart \
          --namespace ai-workflow-engine-production \
          --create-namespace \
          --values ./helm-chart/values-production.yaml \
          --set api.image.tag="${{ needs.build-and-push.outputs.image-tag }}" \
          --set global.environment=$TARGET_ENV \
          --wait --timeout=15m
        
        # Wait for deployment to be ready
        kubectl wait --for=condition=ready pod \
          -l app.kubernetes.io/name=api,environment=$TARGET_ENV \
          --namespace ai-workflow-engine-production --timeout=300s
        
        # Switch traffic to new environment
        kubectl patch ingress ai-workflow-engine-ingress \
          --namespace ai-workflow-engine-production \
          --type merge \
          --patch "{\"metadata\":{\"annotations\":{\"nginx.ingress.kubernetes.io/canary\":\"true\",\"nginx.ingress.kubernetes.io/canary-weight\":\"100\"}}}"
        
        # Update active environment state
        kubectl create configmap deployment-state \
          --from-literal=active-environment=$TARGET_ENV \
          --namespace ai-workflow-engine-production \
          --dry-run=client -o yaml | kubectl apply -f -
        
        echo "Successfully deployed to $TARGET_ENV environment"
```

## Migration Timeline

### Phase 1: Foundation (Weeks 1-4)
- ✅ Kubernetes cluster setup and configuration
- ✅ Namespace and RBAC configuration
- ✅ Storage class and persistent volume setup
- ✅ Basic monitoring stack deployment

### Phase 2: Core Services (Weeks 5-8)
- ✅ Database StatefulSet migration (PostgreSQL, Redis, Qdrant)
- ✅ Application Deployment migration (API, WebUI, Worker)
- ✅ Service and networking configuration
- ✅ Health check and probe configuration

### Phase 3: Advanced Features (Weeks 9-12)
- ✅ Horizontal Pod Autoscaling implementation
- ✅ Pod Disruption Budget configuration
- ✅ Network policy implementation
- ✅ Resource quotas and limits

### Phase 4: Production Readiness (Weeks 13-16)
- ✅ Ingress and certificate management
- ✅ Comprehensive monitoring and alerting
- ✅ Backup and disaster recovery setup
- ✅ CI/CD pipeline integration

### Phase 5: Optimization and Documentation (Weeks 17-20)
- ✅ Performance optimization and tuning
- ✅ Security hardening and compliance
- ✅ Documentation and training materials
- ✅ Migration validation and testing

## Success Criteria

### Technical Metrics
- ✅ 99.9% uptime (< 44 minutes downtime/month)
- ✅ <100ms API response time (95th percentile)
- ✅ Zero-downtime deployments
- ✅ Automatic scaling based on load
- ✅ Full disaster recovery capability

### Operational Metrics
- ✅ <30 minutes deployment time (commit to production)
- ✅ <5 minutes rollback time
- ✅ <15 minutes MTTR for critical issues
- ✅ 100% infrastructure as code coverage

### Security and Compliance
- ✅ Network segmentation and policies
- ✅ Automated security scanning
- ✅ Secret management and rotation
- ✅ Audit logging and compliance reporting

## Conclusion

This Kubernetes migration guide provides a comprehensive roadmap for transforming the AI Workflow Engine from a Docker Compose-based deployment to a cloud-native Kubernetes platform. The migration enables:

**Key Benefits:**
- 🚀 Horizontal scalability and auto-scaling
- 🛡️ Enhanced security and network isolation
- 🔄 Zero-downtime deployments and updates
- 📊 Advanced monitoring and observability
- ⚡ Improved performance and resource utilization
- 🌍 Multi-environment support and consistency

**Investment Requirements:**
- **Timeline:** 16-20 weeks for complete migration
- **Resources:** 3-4 engineers with Kubernetes expertise
- **Infrastructure:** Kubernetes cluster and associated tooling
- **Training:** Team upskilling on Kubernetes and cloud-native practices

The migration positions the AI Workflow Engine for enterprise-scale operations while maintaining development velocity and operational excellence.