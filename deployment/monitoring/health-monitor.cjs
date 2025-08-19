#!/usr/bin/env node

/**
 * Health Monitor Service
 * Continuously monitors blue-green deployment health and provides metrics
 */

const http = require('http');
const { URL } = require('url');

class HealthMonitor {
  constructor() {
    this.config = {
      port: parseInt(process.env.PORT || '8080'),
      checkInterval: parseInt(process.env.CHECK_INTERVAL || '30') * 1000,
      blueEndpoint: process.env.BLUE_ENDPOINT || 'http://game-blue:8080',
      greenEndpoint: process.env.GREEN_ENDPOINT || 'http://game-green:8080',
      alertWebhook: process.env.ALERT_WEBHOOK_URL,
      timeout: parseInt(process.env.HEALTH_TIMEOUT || '10') * 1000
    };

    this.metrics = {
      blue: { healthy: false, responseTime: 0, lastCheck: null, consecutiveFailures: 0 },
      green: { healthy: false, responseTime: 0, lastCheck: null, consecutiveFailures: 0 }
    };

    this.startTime = Date.now();
    this.checks = 0;
    this.alerts = [];

    this.startMonitoring();
    this.startServer();
  }

  async checkHealth(endpoint, slot) {
    const startTime = Date.now();
    
    try {
      const url = new URL('/health', endpoint);
      const response = await this.httpRequest(url.href, { timeout: this.config.timeout });
      const responseTime = Date.now() - startTime;
      
      const healthy = response.statusCode === 200;
      
      this.metrics[slot] = {
        healthy,
        responseTime,
        lastCheck: new Date().toISOString(),
        consecutiveFailures: healthy ? 0 : this.metrics[slot].consecutiveFailures + 1,
        statusCode: response.statusCode,
        body: response.body
      };

      if (!healthy && this.metrics[slot].consecutiveFailures === 1) {
        await this.sendAlert(`🚨 ${slot.toUpperCase()} slot health check failed`, {
          slot,
          statusCode: response.statusCode,
          responseTime,
          endpoint
        });
      }

      if (healthy && this.metrics[slot].consecutiveFailures > 0) {
        await this.sendAlert(`✅ ${slot.toUpperCase()} slot recovered`, {
          slot,
          statusCode: response.statusCode,
          responseTime,
          endpoint,
          downDuration: this.metrics[slot].consecutiveFailures * this.config.checkInterval / 1000
        });
      }

      return this.metrics[slot];
    } catch (error) {
      const responseTime = Date.now() - startTime;
      
      this.metrics[slot] = {
        healthy: false,
        responseTime,
        lastCheck: new Date().toISOString(),
        consecutiveFailures: this.metrics[slot].consecutiveFailures + 1,
        error: error.message
      };

      if (this.metrics[slot].consecutiveFailures === 1) {
        await this.sendAlert(`🚨 ${slot.toUpperCase()} slot connection failed`, {
          slot,
          error: error.message,
          endpoint
        });
      }

      return this.metrics[slot];
    }
  }

  async httpRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      const parsedUrl = new URL(url);
      const requestOptions = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port,
        path: parsedUrl.pathname + parsedUrl.search,
        method: 'GET',
        timeout: options.timeout || 10000
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

      req.end();
    });
  }

  async sendAlert(message, details = {}) {
    const alert = {
      timestamp: new Date().toISOString(),
      message,
      details,
      severity: details.error || !details.statusCode || details.statusCode >= 500 ? 'critical' : 'warning'
    };

    this.alerts.unshift(alert);
    if (this.alerts.length > 100) {
      this.alerts = this.alerts.slice(0, 100);
    }

    console.log(`[ALERT] ${message}`, details);

    if (this.config.alertWebhook) {
      try {
        // Send webhook notification (Slack, Discord, etc.)
        const payload = {
          text: `${message}\n\`\`\`${JSON.stringify(details, null, 2)}\`\`\``
        };
        
        // This is a simplified webhook - implement actual webhook format as needed
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

  async performHealthChecks() {
    this.checks++;
    
    const [blueHealth, greenHealth] = await Promise.all([
      this.checkHealth(this.config.blueEndpoint, 'blue'),
      this.checkHealth(this.config.greenEndpoint, 'green')
    ]);

    // Log summary
    console.log(`Health Check #${this.checks}:`, {
      blue: { healthy: blueHealth.healthy, responseTime: `${blueHealth.responseTime}ms` },
      green: { healthy: greenHealth.healthy, responseTime: `${greenHealth.responseTime}ms` }
    });
  }

  startMonitoring() {
    console.log('Starting health monitoring...', {
      checkInterval: this.config.checkInterval / 1000 + 's',
      blueEndpoint: this.config.blueEndpoint,
      greenEndpoint: this.config.greenEndpoint
    });

    // Initial check
    this.performHealthChecks();

    // Periodic checks
    setInterval(() => {
      this.performHealthChecks();
    }, this.config.checkInterval);
  }

  generatePrometheusMetrics() {
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    
    let metrics = `# HELP game_health_check Health check status for game slots
# TYPE game_health_check gauge
game_health_check{slot="blue"} ${this.metrics.blue.healthy ? 1 : 0}
game_health_check{slot="green"} ${this.metrics.green.healthy ? 1 : 0}

# HELP game_response_time Response time for health checks in milliseconds
# TYPE game_response_time gauge
game_response_time{slot="blue"} ${this.metrics.blue.responseTime}
game_response_time{slot="green"} ${this.metrics.green.responseTime}

# HELP game_consecutive_failures Consecutive health check failures
# TYPE game_consecutive_failures gauge
game_consecutive_failures{slot="blue"} ${this.metrics.blue.consecutiveFailures}
game_consecutive_failures{slot="green"} ${this.metrics.green.consecutiveFailures}

# HELP health_monitor_uptime Health monitor uptime in seconds
# TYPE health_monitor_uptime counter
health_monitor_uptime ${uptime}

# HELP health_monitor_checks_total Total number of health checks performed
# TYPE health_monitor_checks_total counter
health_monitor_checks_total ${this.checks}

# HELP health_monitor_alerts_total Total number of alerts sent
# TYPE health_monitor_alerts_total counter
health_monitor_alerts_total ${this.alerts.length}
`;

    return metrics;
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
          res.end('healthy\n');
          break;

        case '/metrics':
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end(this.generatePrometheusMetrics());
          break;

        case '/status':
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            uptime: Math.floor((Date.now() - this.startTime) / 1000),
            checks: this.checks,
            metrics: this.metrics,
            recentAlerts: this.alerts.slice(0, 10),
            config: {
              checkInterval: this.config.checkInterval / 1000,
              endpoints: {
                blue: this.config.blueEndpoint,
                green: this.config.greenEndpoint
              }
            }
          }, null, 2));
          break;

        case '/alerts':
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(this.alerts, null, 2));
          break;

        default:
          res.writeHead(404, { 'Content-Type': 'text/plain' });
          res.end('Not Found\n');
      }
    });

    server.listen(this.config.port, () => {
      console.log(`Health monitor server running on port ${this.config.port}`);
    });
  }
}

// Start the health monitor
if (require.main === module) {
  new HealthMonitor();
}

module.exports = HealthMonitor;