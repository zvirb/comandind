#!/usr/bin/env node

/**
 * RTS Performance Monitor Service
 * Specialized monitoring for Command & Independent Thought gameplay systems
 * Monitors entity counts, selection performance, pathfinding timing, and resource economy
 */

const http = require('http');
const { URL } = require('url');
const WebSocket = require('ws');

class RTSPerformanceMonitor {
  constructor() {
    this.config = {
      port: parseInt(process.env.PORT || '8082'),
      gameEndpoint: process.env.GAME_ENDPOINT || 'http://game-blue:8080',
      wsEndpoint: process.env.GAME_WS_ENDPOINT || 'ws://game-blue:8080/ws',
      checkInterval: parseInt(process.env.CHECK_INTERVAL || '5') * 1000, // 5 second default
      alertWebhook: process.env.ALERT_WEBHOOK_URL,
      timeout: parseInt(process.env.HEALTH_TIMEOUT || '10') * 1000
    };

    // RTS-specific performance targets
    this.performanceTargets = {
      targetFPS: 60,
      minFPS: 45,
      maxEntityCount: 200,
      selectionResponseTime: 16, // ms
      pathfindingTime: 5, // ms per path
      memoryLimit: 200, // MB
      maxFrameTime: 16.67 // ms for 60 FPS
    };

    // Performance metrics storage
    this.metrics = {
      gameplay: {
        fps: 0,
        frameTime: 0,
        entityCount: 0,
        selectedEntities: 0,
        activePathfinding: 0,
        memoryUsage: 0,
        lastUpdate: null
      },
      pathfinding: {
        averageCalculationTime: 0,
        pathsPerSecond: 0,
        cacheHitRatio: 0,
        queueLength: 0,
        spatialQueries: 0
      },
      selection: {
        averageSelectionTime: 0,
        lastSelectionSize: 0,
        selectionEventsPerSecond: 0,
        dragSelectionTime: 0
      },
      resources: {
        tickRate: 0,
        economyBalance: 0,
        resourceTransactions: 0,
        buildingCount: 0,
        unitCount: 0
      },
      alerts: [],
      historicalData: {
        fps: new Array(60).fill(60), // Last 5 minutes of FPS data
        frameTime: new Array(60).fill(16.67),
        entityCount: new Array(60).fill(0),
        pathfindingTime: new Array(60).fill(0),
        memoryUsage: new Array(60).fill(0)
      }
    };

    this.startTime = Date.now();
    this.checks = 0;
    this.wsClient = null;

    this.startMonitoring();
    this.connectToGameWebSocket();
    this.startServer();
  }

  async connectToGameWebSocket() {
    try {
      console.log(`🔌 Connecting to game WebSocket: ${this.config.wsEndpoint}`);
      
      this.wsClient = new WebSocket(this.config.wsEndpoint);
      
      this.wsClient.on('open', () => {
        console.log('✅ Connected to game WebSocket for real-time metrics');
        // Subscribe to performance metrics
        this.wsClient.send(JSON.stringify({
          type: 'subscribe',
          channels: ['performance', 'pathfinding', 'selection', 'resources']
        }));
      });

      this.wsClient.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.processGameMetrics(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error.message);
        }
      });

      this.wsClient.on('close', () => {
        console.log('🔌 WebSocket connection closed, attempting reconnect...');
        setTimeout(() => this.connectToGameWebSocket(), 5000);
      });

      this.wsClient.on('error', (error) => {
        console.error('WebSocket connection error:', error.message);
      });
    } catch (error) {
      console.error('Failed to connect to game WebSocket:', error.message);
      setTimeout(() => this.connectToGameWebSocket(), 10000);
    }
  }

  processGameMetrics(message) {
    const now = Date.now();
    
    switch (message.type) {
      case 'performance_update':
        this.updatePerformanceMetrics(message.data);
        break;
      case 'pathfinding_metrics':
        this.updatePathfindingMetrics(message.data);
        break;
      case 'selection_metrics':
        this.updateSelectionMetrics(message.data);
        break;
      case 'resource_metrics':
        this.updateResourceMetrics(message.data);
        break;
      default:
        // Unknown message type
        break;
    }
  }

  updatePerformanceMetrics(data) {
    const prev = this.metrics.gameplay;
    
    this.metrics.gameplay = {
      ...prev,
      fps: data.fps || prev.fps,
      frameTime: data.frameTime || prev.frameTime,
      entityCount: data.entityCount || prev.entityCount,
      selectedEntities: data.selectedEntities || prev.selectedEntities,
      activePathfinding: data.activePathfinding || prev.activePathfinding,
      memoryUsage: data.memoryUsage || prev.memoryUsage,
      lastUpdate: new Date().toISOString()
    };

    // Update historical data
    this.updateHistoricalData('fps', this.metrics.gameplay.fps);
    this.updateHistoricalData('frameTime', this.metrics.gameplay.frameTime);
    this.updateHistoricalData('entityCount', this.metrics.gameplay.entityCount);
    this.updateHistoricalData('memoryUsage', this.metrics.gameplay.memoryUsage);

    // Check performance thresholds
    this.checkPerformanceAlerts(this.metrics.gameplay);
  }

  updatePathfindingMetrics(data) {
    this.metrics.pathfinding = {
      averageCalculationTime: data.averageCalculationTime || 0,
      pathsPerSecond: data.pathsPerSecond || 0,
      cacheHitRatio: data.cacheHitRatio || 0,
      queueLength: data.queueLength || 0,
      spatialQueries: data.spatialQueries || 0
    };

    this.updateHistoricalData('pathfindingTime', data.averageCalculationTime || 0);

    // Check pathfinding performance
    if (data.averageCalculationTime > this.performanceTargets.pathfindingTime) {
      this.sendAlert(`🐌 Pathfinding performance degraded`, {
        averageTime: data.averageCalculationTime,
        target: this.performanceTargets.pathfindingTime,
        queueLength: data.queueLength
      });
    }
  }

  updateSelectionMetrics(data) {
    this.metrics.selection = {
      averageSelectionTime: data.averageSelectionTime || 0,
      lastSelectionSize: data.lastSelectionSize || 0,
      selectionEventsPerSecond: data.selectionEventsPerSecond || 0,
      dragSelectionTime: data.dragSelectionTime || 0
    };

    // Check selection performance
    if (data.averageSelectionTime > this.performanceTargets.selectionResponseTime) {
      this.sendAlert(`🖱️ Selection response time degraded`, {
        averageTime: data.averageSelectionTime,
        target: this.performanceTargets.selectionResponseTime,
        selectionSize: data.lastSelectionSize
      });
    }
  }

  updateResourceMetrics(data) {
    this.metrics.resources = {
      tickRate: data.tickRate || 0,
      economyBalance: data.economyBalance || 0,
      resourceTransactions: data.resourceTransactions || 0,
      buildingCount: data.buildingCount || 0,
      unitCount: data.unitCount || 0
    };
  }

  updateHistoricalData(metric, value) {
    if (this.metrics.historicalData[metric]) {
      this.metrics.historicalData[metric].shift();
      this.metrics.historicalData[metric].push(value);
    }
  }

  checkPerformanceAlerts(gameplay) {
    const alerts = [];

    // FPS alerts
    if (gameplay.fps < this.performanceTargets.minFPS) {
      alerts.push({
        type: 'fps_low',
        severity: gameplay.fps < 30 ? 'critical' : 'warning',
        message: `FPS dropped to ${gameplay.fps} (target: ${this.performanceTargets.targetFPS})`,
        data: { fps: gameplay.fps, entityCount: gameplay.entityCount }
      });
    }

    // Frame time alerts
    if (gameplay.frameTime > this.performanceTargets.maxFrameTime * 2) {
      alerts.push({
        type: 'frame_time_high',
        severity: 'warning',
        message: `Frame time spiked to ${gameplay.frameTime}ms`,
        data: { frameTime: gameplay.frameTime }
      });
    }

    // Entity count alerts
    if (gameplay.entityCount > this.performanceTargets.maxEntityCount) {
      alerts.push({
        type: 'entity_overflow',
        severity: 'warning',
        message: `Entity count exceeded limit: ${gameplay.entityCount}/${this.performanceTargets.maxEntityCount}`,
        data: { entityCount: gameplay.entityCount }
      });
    }

    // Memory alerts
    if (gameplay.memoryUsage > this.performanceTargets.memoryLimit) {
      alerts.push({
        type: 'memory_high',
        severity: 'critical',
        message: `Memory usage exceeded limit: ${gameplay.memoryUsage}MB/${this.performanceTargets.memoryLimit}MB`,
        data: { memoryUsage: gameplay.memoryUsage }
      });
    }

    // Send alerts
    alerts.forEach(alert => this.sendAlert(alert.message, alert.data, alert.severity));
  }

  async sendAlert(message, details = {}, severity = 'warning') {
    const alert = {
      timestamp: new Date().toISOString(),
      message,
      details,
      severity,
      component: 'rts-performance-monitor'
    };

    this.metrics.alerts.unshift(alert);
    if (this.metrics.alerts.length > 100) {
      this.metrics.alerts = this.metrics.alerts.slice(0, 100);
    }

    console.log(`[${severity.toUpperCase()}] ${message}`, details);

    if (this.config.alertWebhook) {
      try {
        const payload = {
          text: `🎮 RTS Performance Alert: ${message}`,
          attachments: [{
            color: severity === 'critical' ? 'danger' : 'warning',
            fields: Object.entries(details).map(([key, value]) => ({
              title: key,
              value: String(value),
              short: true
            }))
          }]
        };
        
        await this.httpRequest(this.config.alertWebhook, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } catch (error) {
        console.error('Failed to send webhook alert:', error.message);
      }
    }
  }

  async httpRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(url);
      const requestOptions = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port,
        path: parsedUrl.pathname + parsedUrl.search,
        method: options.method || 'GET',
        timeout: options.timeout || this.config.timeout,
        headers: options.headers || {}
      };

      const req = http.request(requestOptions, (res) => {
        let body = '';
        res.on('data', (chunk) => body += chunk);
        res.on('end', () => resolve({ statusCode: res.statusCode, body, headers: res.headers }));
      });

      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      if (options.body) {
        req.write(options.body);
      }

      req.end();
    });
  }

  async performGameplayHealthCheck() {
    this.checks++;
    
    try {
      const url = new URL('/api/performance-stats', this.config.gameEndpoint);
      const response = await this.httpRequest(url.href, { timeout: this.config.timeout });
      
      if (response.statusCode === 200) {
        const stats = JSON.parse(response.body);
        this.updatePerformanceMetrics(stats);
        
        console.log(`Health Check #${this.checks}:`, {
          fps: stats.fps,
          entities: stats.entityCount,
          memory: `${stats.memoryUsage}MB`,
          pathfinding: `${this.metrics.pathfinding.queueLength} queued`
        });
      }
    } catch (error) {
      console.error('Gameplay health check failed:', error.message);
      this.sendAlert('Gameplay health check failed', { error: error.message }, 'critical');
    }
  }

  startMonitoring() {
    console.log('🎮 Starting RTS Performance Monitoring...', {
      checkInterval: this.config.checkInterval / 1000 + 's',
      gameEndpoint: this.config.gameEndpoint,
      wsEndpoint: this.config.wsEndpoint
    });

    // Periodic health checks (fallback when WebSocket unavailable)
    setInterval(() => {
      this.performGameplayHealthCheck();
    }, this.config.checkInterval);
  }

  generateRTSMetrics() {
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    const gameplay = this.metrics.gameplay;
    const pathfinding = this.metrics.pathfinding;
    const selection = this.metrics.selection;
    
    return `# HELP rts_game_fps Current game FPS
# TYPE rts_game_fps gauge
rts_game_fps ${gameplay.fps}

# HELP rts_game_frame_time Current frame time in milliseconds
# TYPE rts_game_frame_time gauge
rts_game_frame_time ${gameplay.frameTime}

# HELP rts_entity_count Total entities in game world
# TYPE rts_entity_count gauge
rts_entity_count ${gameplay.entityCount}

# HELP rts_selected_entities Currently selected entities
# TYPE rts_selected_entities gauge
rts_selected_entities ${gameplay.selectedEntities}

# HELP rts_active_pathfinding Active pathfinding operations
# TYPE rts_active_pathfinding gauge
rts_active_pathfinding ${gameplay.activePathfinding}

# HELP rts_memory_usage Memory usage in MB
# TYPE rts_memory_usage gauge
rts_memory_usage ${gameplay.memoryUsage}

# HELP rts_pathfinding_time Average pathfinding calculation time in ms
# TYPE rts_pathfinding_time gauge
rts_pathfinding_time ${pathfinding.averageCalculationTime}

# HELP rts_pathfinding_cache_hit_ratio Pathfinding cache hit ratio
# TYPE rts_pathfinding_cache_hit_ratio gauge
rts_pathfinding_cache_hit_ratio ${pathfinding.cacheHitRatio}

# HELP rts_selection_response_time Selection response time in ms
# TYPE rts_selection_response_time gauge
rts_selection_response_time ${selection.averageSelectionTime}

# HELP rts_performance_target_fps_met Whether FPS target is being met
# TYPE rts_performance_target_fps_met gauge
rts_performance_target_fps_met ${gameplay.fps >= this.performanceTargets.targetFPS ? 1 : 0}

# HELP rts_monitor_uptime RTS monitor uptime in seconds
# TYPE rts_monitor_uptime counter
rts_monitor_uptime ${uptime}

# HELP rts_monitor_checks_total Total performance checks performed
# TYPE rts_monitor_checks_total counter
rts_monitor_checks_total ${this.checks}

# HELP rts_alerts_total Total alerts generated
# TYPE rts_alerts_total counter
rts_alerts_total ${this.metrics.alerts.length}
`;
  }

  calculatePerformanceScore() {
    const gameplay = this.metrics.gameplay;
    const pathfinding = this.metrics.pathfinding;
    const selection = this.metrics.selection;

    let score = 100;

    // FPS penalty
    if (gameplay.fps < this.performanceTargets.targetFPS) {
      score -= Math.max(0, (this.performanceTargets.targetFPS - gameplay.fps) * 2);
    }

    // Memory penalty
    if (gameplay.memoryUsage > this.performanceTargets.memoryLimit) {
      score -= Math.min(30, (gameplay.memoryUsage - this.performanceTargets.memoryLimit) / 10);
    }

    // Pathfinding penalty
    if (pathfinding.averageCalculationTime > this.performanceTargets.pathfindingTime) {
      score -= Math.min(20, pathfinding.averageCalculationTime - this.performanceTargets.pathfindingTime);
    }

    // Selection penalty
    if (selection.averageSelectionTime > this.performanceTargets.selectionResponseTime) {
      score -= Math.min(10, selection.averageSelectionTime - this.performanceTargets.selectionResponseTime);
    }

    return Math.max(0, Math.round(score));
  }

  startServer() {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, `http://${req.headers.host}`);
      
      // Set CORS headers
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

      if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
      }

      switch (url.pathname) {
        case '/health':
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end('rts-performance-monitor healthy\n');
          break;

        case '/metrics':
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end(this.generateRTSMetrics());
          break;

        case '/rts-dashboard':
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            timestamp: new Date().toISOString(),
            uptime: Math.floor((Date.now() - this.startTime) / 1000),
            performanceScore: this.calculatePerformanceScore(),
            metrics: this.metrics,
            targets: this.performanceTargets,
            status: {
              fpsTarget: this.metrics.gameplay.fps >= this.performanceTargets.targetFPS,
              memoryHealthy: this.metrics.gameplay.memoryUsage <= this.performanceTargets.memoryLimit,
              pathfindingHealthy: this.metrics.pathfinding.averageCalculationTime <= this.performanceTargets.pathfindingTime,
              selectionHealthy: this.metrics.selection.averageSelectionTime <= this.performanceTargets.selectionResponseTime
            }
          }, null, 2));
          break;

        case '/alerts':
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(this.metrics.alerts, null, 2));
          break;

        case '/historical':
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(this.metrics.historicalData, null, 2));
          break;

        default:
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('Not Found\n');
      }
    });

    server.listen(this.config.port, () => {
      console.log(`🎮 RTS Performance Monitor server running on port ${this.config.port}`);
      console.log(`📊 Dashboard: http://localhost:${this.config.port}/rts-dashboard`);
      console.log(`📈 Metrics: http://localhost:${this.config.port}/metrics`);
    });
  }
}

// Start the RTS performance monitor
if (require.main === module) {
  new RTSPerformanceMonitor();
}

module.exports = RTSPerformanceMonitor;