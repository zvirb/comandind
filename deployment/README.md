# Command & Independent Thought - Infrastructure Documentation

## 🏗️ Infrastructure Overview

This directory contains the complete infrastructure setup for Command & Independent Thought, including deployment orchestration, monitoring systems, and production validation tools specifically designed for RTS gameplay at scale.

## 🎮 RTS-Specific Infrastructure Features

### Performance Monitoring
- **Real-time FPS monitoring** with 200+ entity scenarios
- **Selection system response time tracking** (<16ms target)  
- **Pathfinding performance metrics** (<5ms per path target)
- **Memory usage monitoring** (<200MB target)
- **Resource economy balance tracking** and reporting

### Deployment Pipeline
- **Blue-green deployment** for zero-downtime updates
- **RTS performance validation** during deployments
- **Automated rollback** triggers if performance targets not met (60+ FPS)
- **Container orchestration** support for scaled testing environments

### Health Monitoring
- **Production health checks** for gameplay systems
- **Comprehensive system validation** covering all RTS components
- **Real-time alerting** for performance degradation
- **Historical performance tracking** and analysis

## 🚀 Quick Start

### Prerequisites

```bash
# Required tools
- Docker & Docker Compose
- Node.js 18+
- Git
- curl, bc, python3

# Optional for development
- kubectl (for Kubernetes deployment)
- Prometheus & Grafana (for advanced monitoring)
```

### Basic Deployment

```bash
# Clone and setup
cd /path/to/comandind

# Deploy with RTS validation
./deployment/scripts/rts-deploy.sh deploy

# Check deployment status
./deployment/scripts/rts-deploy.sh status

# Perform RTS health check
./deployment/scripts/rts-deploy.sh rts-check
```

### Advanced Deployment with Custom Targets

```bash
# Set custom RTS performance targets
export RTS_MIN_FPS=50
export RTS_MAX_MEMORY=150
export RTS_MAX_ENTITIES=150

# Deploy with custom targets
./deployment/scripts/rts-deploy.sh deploy

# Force deployment to specific slot
./deployment/scripts/rts-deploy.sh deploy green
```

## 📊 Monitoring Architecture

### Service Structure

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Game Blue     │    │   Game Green    │    │  Load Balancer  │
│   Port: 8080    │    │   Port: 8080    │    │   Port: 80/443  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Health Monitor  │    │ RTS Monitor     │    │   Prometheus    │
│   Port: 8080    │    │   Port: 8082    │    │   Port: 9090    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Monitoring Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Game Health | `/health` | Basic health check |
| Game Performance | `/api/performance-stats` | RTS performance metrics |
| RTS Monitor Dashboard | `:8082/rts-dashboard` | Comprehensive RTS metrics |
| Prometheus Metrics | `:8082/metrics` | Prometheus-compatible metrics |
| Health History | `:8082/historical` | Performance trends |

## 🔍 Monitoring Systems

### 1. RTS Performance Monitor (`/monitoring/rts-performance-monitor.js`)

**Features:**
- Real-time RTS gameplay metrics collection
- WebSocket integration with game client
- Performance alert system with thresholds
- Prometheus metrics export
- Historical data storage

**Key Metrics:**
```javascript
{
  fps: 60,                    // Current FPS
  frameTime: 16.67,          // Frame time in ms
  entityCount: 150,          // Active entities
  memoryUsage: 180,          // Memory usage in MB
  pathfindingTime: 3.2,      // Average pathfinding time
  selectionTime: 12.5,       // Selection response time
  cacheHitRatio: 0.85        // Pathfinding cache efficiency
}
```

### 2. RTS Profiler (`/src/monitoring/RTSProfiler.js`)

**Features:**
- Client-side performance profiling
- Pathfinding and selection system analysis
- Memory leak detection
- Performance bottleneck identification
- Real-time metrics broadcasting

**Usage in Game Code:**
```javascript
import { rtsProfiler } from './monitoring/RTSProfiler.js';

// Profile pathfinding operation
const start = performance.now();
const path = pathfinder.findPath(startPos, endPos);
const end = performance.now();
rtsProfiler.profilePathfinding('A*', start, end, path.length, cached);

// Profile selection operation
const selectionStart = performance.now();
const selectedEntities = selectionSystem.selectInArea(rect);
const selectionEnd = performance.now();
rtsProfiler.profileSelection('drag', selectedEntities.length, selectionStart, selectionEnd);
```

### 3. RTS Diagnostics (`/src/monitoring/RTSDiagnostics.js`)

**Features:**
- Comprehensive error tracking and logging
- Gameplay event logging
- System diagnostics and health assessment
- Automated error reporting
- Diagnostic data export

**Usage:**
```javascript
import { rtsDiagnostics } from './monitoring/RTSDiagnostics.js';

// Log gameplay events
rtsDiagnostics.logGameplayEvent('unit_created', { unitType: 'tank', player: 1 });

// Log performance issues
rtsDiagnostics.logPerformanceEvent('fps_drop', { fps: 35, expectedFps: 60 });

// Export diagnostic report
rtsDiagnostics.exportDiagnosticData();
```

### 4. RTS Health Monitor (`/src/monitoring/RTSHealthMonitor.js`)

**Features:**
- Production health validation
- Multi-system health checks (performance, gameplay, resources, network)
- Alert management with cooldown periods
- Health scoring and recommendations
- Historical health tracking

**Health Check Categories:**
- **System Health** (30% weight): Browser compatibility, memory, error rates
- **Performance Health** (25% weight): FPS, frame times, memory usage
- **Gameplay Health** (25% weight): Pathfinding, selection, entity systems
- **Resource Health** (10% weight): Asset loading, texture memory
- **Network Health** (10% weight): Connection status, WebSocket health

## 🚦 Performance Targets

### Default Performance Targets

```bash
# FPS Targets
RTS_MIN_FPS=45           # Minimum acceptable FPS
RTS_TARGET_FPS=60        # Target FPS for optimal gameplay
RTS_CRITICAL_FPS=30      # Critical threshold triggering alerts

# Response Time Targets  
RTS_MAX_FRAME_TIME=22    # Maximum frame time (ms)
RTS_MAX_PATHFINDING_TIME=5   # Maximum pathfinding time per path (ms)
RTS_MAX_SELECTION_TIME=16    # Maximum selection response time (ms)

# Resource Limits
RTS_MAX_MEMORY=200       # Maximum memory usage (MB)
RTS_MAX_ENTITIES=200     # Maximum recommended entity count
```

### Customizing Performance Targets

```bash
# Environment variables for deployment
export RTS_MIN_FPS=50
export RTS_MAX_MEMORY=150
export RTS_MAX_ENTITIES=300

# Or in docker-compose.yml
environment:
  - RTS_MIN_FPS=50
  - RTS_MAX_MEMORY=150
  - RTS_MAX_ENTITIES=300
```

## 🐳 Container Architecture

### Service Isolation Principles

**Each new functionality = separate container/service**

✅ **Correct Approach:**
- New Service = New Container
- Independent API endpoints (`/health`, `/api/v1/...`)
- Graceful degradation ("Service offline" messages)
- No cascading failures

❌ **Forbidden:**
- Modifying existing working containers
- Integrating new features into existing services
- Creating tight coupling between components

### Blue-Green Deployment Process

1. **Build Phase**: Create production build with RTS optimizations
2. **Deploy Phase**: Deploy to standby slot (blue/green)
3. **Validation Phase**: Comprehensive RTS performance validation
4. **Traffic Switch**: Atomic traffic switching via load balancer
5. **Monitor Phase**: Post-deployment monitoring and rollback if needed

### Deployment Validation Pipeline

```bash
# 1. Basic health check
curl -f http://localhost:8080/health

# 2. RTS performance validation
curl -s http://localhost:8080/api/performance-stats | jq '.fps >= 45'

# 3. Gameplay systems validation
curl -f http://localhost:8080/api/systems-status
curl -f http://localhost:8080/api/pathfinding-stats
curl -f http://localhost:8080/api/selection-stats

# 4. Final production validation
./deployment/scripts/rts-deploy.sh rts-check
```

## 🔧 Configuration Files

### Key Configuration Files

```
deployment/
├── docker-compose/
│   └── docker-compose.blue-green.yml    # Main orchestration
├── monitoring/
│   ├── rts-performance-monitor.js        # RTS monitoring service
│   ├── Dockerfile.rts-monitor           # RTS monitor container
│   ├── prometheus.yml                   # Metrics collection
│   └── health-monitor.js                # Basic health monitoring
├── nginx/
│   ├── loadbalancer.conf               # Load balancer config
│   └── default.conf                    # Default nginx config
└── scripts/
    ├── rts-deploy.sh                   # Enhanced deployment script
    ├── deploy.sh                       # Basic deployment script
    └── health-check.sh                 # Health check utilities
```

### Environment Configuration

```bash
# Core Settings
NODE_ENV=production
VERSION=1.0.0
DEPLOYMENT_SLOT=blue

# Monitoring Settings
GAME_ENDPOINT=http://game-blue:8080
GAME_WS_ENDPOINT=ws://game-blue:8080/ws
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
CHECK_INTERVAL=5

# Performance Targets
RTS_MIN_FPS=45
RTS_TARGET_FPS=60
RTS_MAX_MEMORY=200
RTS_MAX_ENTITIES=200
RTS_MAX_PATHFINDING_TIME=5
RTS_MAX_SELECTION_TIME=16
```

## 📈 Monitoring Integration

### Prometheus Metrics

The RTS Performance Monitor exposes Prometheus-compatible metrics:

```prometheus
# Game performance metrics
rts_game_fps                        # Current FPS
rts_game_frame_time                 # Frame time in milliseconds
rts_entity_count                    # Total entities in world
rts_selected_entities               # Currently selected entities
rts_active_pathfinding              # Active pathfinding operations
rts_memory_usage                    # Memory usage in MB

# System performance metrics
rts_pathfinding_time                # Average pathfinding time
rts_pathfinding_cache_hit_ratio     # Cache efficiency
rts_selection_response_time         # Selection response time
rts_performance_target_fps_met      # Whether FPS target is met

# Health metrics
rts_monitor_uptime                  # Monitor uptime
rts_alerts_total                    # Total alerts generated
```

### WebSocket Integration

Real-time metrics streaming via WebSocket:

```javascript
// Connect to RTS monitoring WebSocket
const ws = new WebSocket('ws://localhost:8082/ws');

// Subscribe to specific metrics
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['performance', 'pathfinding', 'selection']
}));

// Receive real-time updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'performance_update') {
    updatePerformanceChart(data.data);
  }
};
```

## 🚨 Alert System

### Alert Categories

1. **Performance Alerts**
   - FPS below minimum threshold
   - Frame time spikes
   - Memory usage exceeded
   - Entity count overflow

2. **System Alerts**
   - Service unavailability
   - Database connection loss
   - Asset loading failures
   - Critical errors

3. **Gameplay Alerts**
   - Pathfinding performance degradation
   - Selection system slowdown
   - Resource system failures

### Alert Configuration

```javascript
// Alert thresholds (configurable via environment)
const alertThresholds = {
  fps: { warning: 50, critical: 35 },
  frameTime: { warning: 20, critical: 50 },
  memory: { warning: 180, critical: 250 },
  pathfinding: { warning: 8, critical: 15 },
  selection: { warning: 25, critical: 50 }
};
```

## 🔧 Troubleshooting

### Common Issues

**1. Deployment Fails RTS Validation**
```bash
# Check current performance
curl -s http://localhost:8080/api/performance-stats | jq '.'

# Review deployment logs
docker compose logs game-blue

# Force rollback if needed
./deployment/scripts/rts-deploy.sh rollback
```

**2. Performance Degradation**
```bash
# Check RTS monitoring dashboard
curl -s http://localhost:8082/rts-dashboard | jq '.performanceScore'

# Review recent alerts
curl -s http://localhost:8082/alerts | jq '.[:5]'

# Export diagnostic data
curl -X POST http://localhost:8082/export-diagnostics
```

**3. Health Check Failures**
```bash
# Manual health check
./deployment/scripts/rts-deploy.sh health blue

# Detailed RTS validation
./deployment/scripts/rts-deploy.sh rts-check blue

# Check specific systems
curl -f http://localhost:8080/api/systems-status
```

### Performance Optimization

**High Memory Usage:**
```bash
# Check memory breakdown
curl -s http://localhost:8080/api/memory-stats

# Monitor texture memory
curl -s http://localhost:8080/api/renderer-stats

# Enable object pooling in game settings
```

**Low FPS Issues:**
```bash
# Check entity count
curl -s http://localhost:8080/api/world-stats

# Review pathfinding performance  
curl -s http://localhost:8080/api/pathfinding-stats

# Analyze frame time breakdown
curl -s http://localhost:8082/historical | jq '.frameTime[-10:]'
```

## 📚 Advanced Topics

### Custom Health Checks

Extend the health monitoring system:

```javascript
// Add custom health check
rtsHealthMonitor.addCustomCheck('database', async () => {
  const dbStatus = await database.ping();
  return {
    status: dbStatus.connected ? 'healthy' : 'critical',
    latency: dbStatus.latency,
    activeConnections: dbStatus.connections
  };
});
```

### Performance Profiling

Enable detailed performance profiling:

```javascript
// Enable performance profiling
rtsProfiler.setEnabled(true);

// Add custom profiling points
rtsProfiler.startProfiling('render_cycle');
// ... rendering logic ...
rtsProfiler.endProfiling('render_cycle');
```

### Monitoring Data Export

Export comprehensive monitoring data:

```bash
# Export all monitoring data
curl -X POST http://localhost:8082/export-all > monitoring-export.json

# Export specific time range
curl -s "http://localhost:8082/historical?start=2024-01-01&end=2024-01-02"
```

## 🎯 Success Metrics

### Infrastructure Success Criteria

✅ **Comprehensive RTS monitoring** covers all gameplay systems
✅ **Blue-green deployment pipeline** supports safe feature releases
✅ **Performance profiling** enables optimization identification  
✅ **Production health monitoring** ensures stable RTS gameplay
✅ **Automated rollback** prevents performance regressions
✅ **Real-time alerting** for immediate issue detection

### Performance Benchmarks

- **60+ FPS** sustained with 200+ entities
- **<16ms frame time** for smooth gameplay
- **<5ms pathfinding** per operation
- **<16ms selection response** time
- **<200MB memory usage** for optimal performance
- **>95% uptime** in production environment

---

## 📞 Support

For infrastructure issues:
1. Check deployment logs: `docker compose logs`
2. Review RTS dashboard: `http://localhost:8082/rts-dashboard`
3. Export diagnostic data: `curl -X POST http://localhost:8082/export-diagnostics`
4. Consult troubleshooting section above

**Infrastructure monitoring enables reliable RTS gameplay at production scale** 🎮⚡