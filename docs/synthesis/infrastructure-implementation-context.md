# Infrastructure Implementation Context Package - Phase 5

**Target**: Container Architecture Specialist, Monitoring Analyst, Deployment Orchestrator  
**Priority**: Medium - Supporting infrastructure  
**Dependencies**: All implementation streams  
**Performance Target**: <200MB memory, <5ms container communication, automated scaling

## Container Architecture Requirements

### 1. Microservice Separation (MANDATORY)
```dockerfile
# game-engine-service (Core ECS + Pathfinding + Selection)
FROM node:18-alpine
WORKDIR /app/game-engine
COPY src/core/ src/ecs/ src/pathfinding/ ./
EXPOSE 3001
CMD ["node", "game-engine.js"]

# economic-service (Harvester AI + Resource Management)
FROM node:18-alpine  
WORKDIR /app/economic
COPY src/economic/ src/ai/ ./
EXPOSE 3002
CMD ["node", "economic-service.js"]

# frontend-service (UI + Rendering + Input)
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### 2. API Gateway Configuration
```yaml
# api-gateway.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-gateway-config
data:
  nginx.conf: |
    upstream game-engine {
      server game-engine-service:3001;
    }
    upstream economic {
      server economic-service:3002;
    }
    
    location /api/game/ {
      proxy_pass http://game-engine/;
      proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/economic/ {
      proxy_pass http://economic/;
      proxy_set_header X-Real-IP $remote_addr;
    }
```

### 3. Inter-Service Communication
```javascript
// Efficient service mesh communication
class ServiceMeshClient {
  constructor() {
    this.connections = new Map();
    this.retryPolicy = {
      maxRetries: 3,
      backoffMs: 100,
      timeoutMs: 1000
    };
  }
  
  async callService(service, method, data) {
    // Target: <5ms inter-service latency
    // Implement circuit breaker pattern
    // Use connection pooling for efficiency
  }
  
  subscribeToEvents(service, eventType, handler) {
    // Real-time event streaming between services
    // WebSocket connections for game state sync
  }
}
```

## Performance Monitoring Infrastructure

### 1. Resource Monitoring Stack
```yaml
# monitoring-stack.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      
  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
```

### 2. Application Metrics Collection
```javascript
class MetricsCollector {
  constructor() {
    this.prometheus = require('prom-client');
    this.register = new this.prometheus.Registry();
    
    // Game-specific metrics
    this.frameTimeHistogram = new this.prometheus.Histogram({
      name: 'game_frame_time_ms',
      help: 'Game frame processing time in milliseconds',
      buckets: [1, 5, 10, 16.67, 25, 50, 100]
    });
    
    this.entityCountGauge = new this.prometheus.Gauge({
      name: 'game_entity_count',
      help: 'Current number of active game entities'
    });
    
    this.selectionLatencyHistogram = new this.prometheus.Histogram({
      name: 'selection_latency_ms',
      help: 'Unit selection response time in milliseconds',
      buckets: [1, 5, 10, 16, 25, 50]
    });
  }
  
  recordFrameTime(duration) {
    this.frameTimeHistogram.observe(duration);
  }
  
  recordSelectionLatency(duration) {
    this.selectionLatencyHistogram.observe(duration);
  }
}
```

### 3. Health Check System
```javascript
class HealthCheckManager {
  constructor() {
    this.checks = new Map();
    this.status = 'healthy';
  }
  
  addCheck(name, checkFn, interval = 5000) {
    this.checks.set(name, {
      checkFn,
      interval,
      lastCheck: Date.now(),
      status: 'unknown'
    });
  }
  
  async performChecks() {
    const results = {};
    
    for (const [name, check] of this.checks) {
      try {
        const result = await check.checkFn();
        results[name] = {
          status: 'healthy',
          latency: result.latency,
          details: result.details
        };
      } catch (error) {
        results[name] = {
          status: 'unhealthy',
          error: error.message
        };
      }
    }
    
    return results;
  }
}

// Service-specific health checks
const healthChecks = {
  gameEngine: async () => {
    // Check ECS world state
    // Verify pathfinding system responsiveness
    return { latency: 2, details: 'ECS operational' };
  },
  
  economicService: async () => {
    // Check harvester AI responsiveness
    // Verify resource calculations
    return { latency: 1, details: 'Economic system stable' };
  },
  
  frontend: async () => {
    // Check rendering pipeline
    // Verify input responsiveness
    return { latency: 3, details: 'Frontend responsive' };
  }
};
```

## Deployment Architecture

### 1. Docker Compose Development
```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 100mb
    
  game-engine:
    build: ./services/game-engine
    ports:
      - "3001:3001"
    environment:
      - REDIS_URL=redis://redis:6379
      - NODE_ENV=development
    volumes:
      - ./src:/app/src
    depends_on:
      - redis
      
  economic-service:
    build: ./services/economic
    ports:
      - "3002:3002"
    environment:
      - REDIS_URL=redis://redis:6379
      - GAME_ENGINE_URL=http://game-engine:3001
    depends_on:
      - redis
      - game-engine
      
  frontend:
    build: ./services/frontend
    ports:
      - "8080:80"
    environment:
      - API_URL=http://localhost:3001
    depends_on:
      - game-engine
      - economic-service
```

### 2. Production Kubernetes Deployment
```yaml
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: game-engine-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: game-engine
  template:
    metadata:
      labels:
        app: game-engine
    spec:
      containers:
      - name: game-engine
        image: comandind/game-engine:latest
        ports:
        - containerPort: 3001
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        livenessProbe:
          httpGet:
            path: /health
            port: 3001
          initialDelaySeconds: 30
          periodSeconds: 10
```

### 3. Horizontal Pod Autoscaler
```yaml
# hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: game-engine-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: game-engine-deployment
  minReplicas: 2
  maxReplicas: 10
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
```

## Memory Management & Optimization

### 1. Container Resource Limits
```yaml
# Resource allocation per service
resources:
  game-engine:
    requests:
      memory: "128Mi"  # Base ECS + Pathfinding
      cpu: "200m"
    limits:
      memory: "256Mi"  # Max with 50+ entities
      cpu: "500m"
      
  economic-service:
    requests:
      memory: "64Mi"   # Harvester AI + Economics
      cpu: "100m"
    limits:
      memory: "128Mi"  # Max with 20 harvesters
      cpu: "300m"
      
  frontend:
    requests:
      memory: "32Mi"   # Static assets + nginx
      cpu: "50m"
    limits:
      memory: "64Mi"   # Browser handles rendering
      cpu: "100m"
```

### 2. Memory Leak Detection
```javascript
class MemoryLeakDetector {
  constructor() {
    this.memorySnapshots = [];
    this.alertThreshold = 200 * 1024 * 1024; // 200MB
    this.monitoringInterval = 30000; // 30 seconds
  }
  
  startMonitoring() {
    setInterval(() => {
      const memUsage = process.memoryUsage();
      this.memorySnapshots.push({
        timestamp: Date.now(),
        heapUsed: memUsage.heapUsed,
        heapTotal: memUsage.heapTotal,
        external: memUsage.external,
        rss: memUsage.rss
      });
      
      // Keep only last 100 snapshots
      if (this.memorySnapshots.length > 100) {
        this.memorySnapshots.shift();
      }
      
      this.detectLeaks();
    }, this.monitoringInterval);
  }
  
  detectLeaks() {
    if (this.memorySnapshots.length < 10) return;
    
    const recent = this.memorySnapshots.slice(-10);
    const trend = this.calculateTrend(recent);
    
    if (trend > 1024 * 1024) { // 1MB/snapshot growth
      console.warn(`Memory leak detected: ${trend} bytes/snapshot trend`);
      this.generateHeapDump();
    }
  }
}
```

## CI/CD Pipeline Integration

### 1. GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy Command and Independent Thought

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: npm install
      
    - name: Run unit tests
      run: npm run test:unit
      
    - name: Run integration tests
      run: npm run test:integration
      
    - name: Performance benchmarks
      run: npm run test:performance
      
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - name: Build Docker images
      run: |
        docker build -t comandind/game-engine:${{ github.sha }} ./services/game-engine
        docker build -t comandind/economic:${{ github.sha }} ./services/economic
        docker build -t comandind/frontend:${{ github.sha }} ./services/frontend
        
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to production
      run: |
        kubectl set image deployment/game-engine-deployment \
          game-engine=comandind/game-engine:${{ github.sha }}
```

### 2. Automated Performance Regression Detection
```javascript
class PerformanceRegressionDetector {
  constructor() {
    this.baselineMetrics = new Map();
    this.regressionThresholds = {
      frameTime: 1.2,      // 20% slower fails
      selectionLatency: 1.3, // 30% slower fails
      memoryUsage: 1.5     // 50% more memory fails
    };
  }
  
  async detectRegressions(currentMetrics) {
    const regressions = [];
    
    for (const [metric, current] of currentMetrics) {
      const baseline = this.baselineMetrics.get(metric);
      if (!baseline) continue;
      
      const ratio = current / baseline;
      const threshold = this.regressionThresholds[metric] || 1.2;
      
      if (ratio > threshold) {
        regressions.push({
          metric,
          baseline,
          current,
          ratio,
          severity: ratio > threshold * 1.5 ? 'critical' : 'warning'
        });
      }
    }
    
    return regressions;
  }
}
```

## Production Monitoring & Alerting

### 1. Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Command and Independent Thought - Game Performance",
    "panels": [
      {
        "title": "Frame Time Distribution",
        "type": "histogram",
        "targets": [{
          "expr": "histogram_quantile(0.95, game_frame_time_ms)",
          "legendFormat": "95th percentile"
        }]
      },
      {
        "title": "Selection Latency",
        "type": "graph", 
        "targets": [{
          "expr": "avg(selection_latency_ms)",
          "legendFormat": "Average selection time"
        }]
      },
      {
        "title": "Memory Usage by Service",
        "type": "graph",
        "targets": [{
          "expr": "container_memory_usage_bytes{container=~\"game-engine|economic-service|frontend\"}",
          "legendFormat": "{{container}}"
        }]
      }
    ]
  }
}
```

### 2. Alert Rules
```yaml
# alerts.yml
groups:
- name: game-performance
  rules:
  - alert: HighFrameTime
    expr: histogram_quantile(0.95, game_frame_time_ms) > 16.67
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Game frame time exceeding 60 FPS target"
      
  - alert: SelectionLatencyHigh
    expr: avg(selection_latency_ms) > 16
    for: 30s
    labels:
      severity: warning
    annotations:
      summary: "Unit selection response time degraded"
      
  - alert: MemoryLeakDetected
    expr: increase(container_memory_usage_bytes[10m]) > 50*1024*1024
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Potential memory leak in {{$labels.container}}"
```

## Implementation Strategy

### Phase 1: Container Architecture (Week 1)
1. Create service separation and Docker configurations
2. Setup inter-service communication patterns
3. Implement health check systems
4. Basic monitoring infrastructure

### Phase 2: Production Deployment (Week 2)
1. Kubernetes deployment configurations
2. Horizontal pod autoscaler setup
3. CI/CD pipeline integration
4. Performance regression detection

### Phase 3: Monitoring & Alerting (Week 3)
1. Comprehensive metrics collection
2. Grafana dashboard configuration
3. Alert rule implementation
4. Memory leak detection systems

### Phase 4: Optimization & Scaling (Week 4)
1. Resource usage optimization
2. Container scaling strategies
3. Network performance tuning
4. Production readiness validation

### Phase 5: Operations & Maintenance (Week 5)
1. Automated deployment procedures
2. Disaster recovery planning
3. Performance baseline establishment
4. Long-term monitoring strategy

## Success Criteria

### Infrastructure Performance
- **Container Startup**: <30 seconds from cold start
- **Inter-service Latency**: <5ms between services
- **Memory Efficiency**: <200MB total for all services
- **Scaling Response**: Auto-scale within 60 seconds of load

### Monitoring & Operations
- **Uptime**: 99.9% availability target
- **Alert Response**: <5 minutes to critical alerts
- **Deployment Speed**: <10 minutes for full deployment
- **Recovery Time**: <15 minutes for service restoration