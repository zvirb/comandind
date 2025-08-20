# Monitoring Scripts Documentation

Monitoring scripts provide comprehensive logging, error tracking, and diagnostic capabilities for the AI Workflow Engine. These scripts implement multi-layered monitoring with real-time alerts and automated diagnostics.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `_comprehensive_logger.sh` | Orchestrates all logging systems | Runs automatically in containers |
| `_diagnostic_logger.sh` | Container failure diagnostics | Background process |
| `_realtime_error_monitor.sh` | Real-time error detection | Background process |
| `_app_log_collector.sh` | Application log aggregation | Background process |
| `_log_rotator.sh` | Automatic log rotation | Background process |
| `_noisy_log_collector.sh` | Noise-filtered logging | Background process |
| `_container_inspector.sh` | Container health monitoring | Background process |
| `_log_formatter.sh` | Log formatting utility | Used by other scripts |
| `_log_failures.sh` | Failure event logging | Event-triggered |
| `_find_error_source.sh` | Error source identification | Diagnostic tool |
| `_check_stack_health.sh` | Stack health verification | Health check tool |
| `_ask_gemini.sh` | AI-powered diagnostics | Automated assistant |

---

## scripts/_comprehensive_logger.sh

**Location:** `/scripts/_comprehensive_logger.sh`  
**Purpose:** Master logging orchestrator that coordinates all monitoring subsystems.

### Description
The central logging coordinator that starts and manages all monitoring processes. It runs as a background service in containers and provides comprehensive system observability.

### Architecture
```bash
# Process orchestration
Diagnostic Logger     (Container death events)
Real-time Monitor    (Running container errors)  
App Log Collector    (Application debug logs)
Log Rotator         (Automatic log management)
Noisy Log Collector (Filtered noise reduction)
Container Inspector (Health monitoring)
```

### Automatic Startup
The script automatically starts all monitoring subsystems:
```bash
# Started processes with PIDs
- Diagnostic logger PID: 1234
- Real-time monitor PID: 1235
- App log collector PID: 1236  
- Log rotator PID: 1237
- Noisy log collector PID: 1238
- Container inspector PID: 1239
```

### Signal Handling
Implements graceful shutdown with proper cleanup:
```bash
# Signal handling
trap cleanup SIGINT SIGTERM

cleanup() {
    echo "Shutting down comprehensive logger..."
    kill $DIAGNOSTIC_PID $REALTIME_PID $APP_LOG_PID 2>/dev/null
    exit 0
}
```

### Integration
- **Container Integration:** Runs automatically in monitoring containers
- **Service Coordination:** Coordinates with all application services
- **Log Aggregation:** Centralizes logs from all sources
- **Error Escalation:** Escalates critical errors to administrators

---

## scripts/_diagnostic_logger.sh

**Location:** `/scripts/_diagnostic_logger.sh`  
**Purpose:** Monitors for container failures and provides detailed diagnostic information.

### Description
Continuously monitors Docker events for container failures and generates comprehensive diagnostic reports including container state, configuration, logs, and dependency analysis.

### Monitoring Capabilities
- **Container Death Detection:** Immediate detection of container failures
- **State Analysis:** Complete container state inspection
- **Configuration Audit:** Environment variables, mounts, networking
- **Dependency Tracking:** Analysis of related service health
- **Historical Context:** Recent events and log history

### Diagnostic Information Collected
```bash
# Container State & Health
- Exit code and OOM status
- Last health check output
- Resource usage patterns
- Restart history

# Configuration Analysis  
- Command and entrypoint
- Environment variables
- Volume mounts and permissions
- Network configuration

# Log Analysis
- Recent container logs (last 100 lines)
- Error pattern identification
- Performance indicators
- Resource constraints
```

### Output Format
```
--- CONTAINER FAILURE LOGGED AT 2025-08-04 10:30:00 for service: api ---
Status: exited
ExitCode: 1
OOMKilled: false
Last Health Check Output: Connection refused

--- CONFIGURATION ---
Command: ["python", "-m", "uvicorn", "main:app"]
Environment Variables:
  - DATABASE_URL=postgresql://...
  - JWT_SECRET_KEY=***
Volume Mounts:
  - Source: /app/scripts
    Destination: /app/scripts
    Mode: rw

--- CONTAINER LOGS (last 100 lines) ---
[2025-08-04 10:29:58] ERROR: Database connection failed
[2025-08-04 10:29:59] CRITICAL: Unable to start application
```

---

## scripts/_realtime_error_monitor.sh

**Location:** `/scripts/_realtime_error_monitor.sh`  
**Purpose:** Real-time monitoring of running containers for error conditions.

### Description
Continuously streams logs from all running containers and identifies error patterns, performance issues, and security events in real-time.

### Monitoring Features
- **Multi-Container Streaming:** Simultaneous monitoring of all services
- **Error Pattern Recognition:** Identifies common error signatures
- **Performance Metrics:** Tracks response times and resource usage
- **Security Alerts:** Detects security-related events
- **Threshold Monitoring:** Alerts on configurable thresholds

### Error Detection Patterns
```bash
# Application Errors
- Database connection failures
- Authentication errors  
- API endpoint failures
- Memory leaks and resource exhaustion

# Infrastructure Errors
- Network connectivity issues
- SSL/TLS certificate problems
- Service discovery failures
- Load balancer issues

# Security Events
- Failed authentication attempts
- Suspicious request patterns
- Certificate validation failures
- Unauthorized access attempts
```

### Real-time Alerts
```bash
# Alert format
[ALERT] [SERVICE] [SEVERITY] [TIMESTAMP]
Description: Error condition detected
Context: Additional context information
Recommendation: Suggested remediation action
```

---

## scripts/_app_log_collector.sh

**Location:** `/scripts/_app_log_collector.sh`  
**Purpose:** Aggregates application-specific debug logs and development information.

### Description
Collects and processes application logs from debug files, development logs, and application-specific output for centralized analysis.

### Collection Sources
- **Debug Files:** Application debug output
- **Development Logs:** Development-specific logging
- **Performance Logs:** Application performance metrics
- **User Activity:** User interaction logs (anonymized)
- **API Logs:** REST API request/response logs

### Processing Features
- **Log Parsing:** Structured parsing of various log formats
- **Correlation:** Correlates related log entries across services
- **Filtering:** Removes sensitive information
- **Aggregation:** Combines related events
- **Enrichment:** Adds context and metadata

---

## scripts/_log_rotator.sh

**Location:** `/scripts/_log_rotator.sh`  
**Purpose:** Automatic log rotation and archive management.

### Description
Manages log file sizes, implements rotation policies, and maintains log archives to prevent disk space exhaustion while preserving historical data.

### Rotation Policies
```bash
# Size-based rotation
- Maximum file size: 100MB
- Archive count: 10 files
- Compression: gzip for archives

# Time-based rotation  
- Daily rotation for high-volume logs
- Weekly rotation for debug logs
- Monthly rotation for audit logs

# Cleanup policies
- Remove archives older than 30 days
- Compress archives older than 7 days
- Emergency cleanup at 90% disk usage
```

### Managed Log Files
- `logs/error_log.txt` - Main error log
- `logs/runtime_errors.log` - Runtime error log
- `logs/docker_cleanup.log` - Docker cleanup log
- `logs/security_audit.log` - Security audit log
- `logs/performance.log` - Performance monitoring log

---

## scripts/_noisy_log_collector.sh

**Location:** `/scripts/_noisy_log_collector.sh`  
**Purpose:** Filters and processes high-volume, noisy log sources.

### Description
Handles high-volume log sources by implementing intelligent filtering to reduce noise while preserving important information for debugging and monitoring.

### Noise Reduction Techniques
- **Pattern Filtering:** Removes known benign messages
- **Frequency Analysis:** Suppresses repeated messages
- **Severity Filtering:** Focuses on important severity levels
- **Content Analysis:** Identifies and filters debug noise
- **Rate Limiting:** Controls message frequency

### Filtering Examples
```bash
# Suppressed patterns
- Routine health check responses
- Normal authentication success
- Expected network keep-alives
- Scheduled task completions

# Preserved patterns  
- First occurrence of any error
- Errors with unique characteristics
- Security-related events
- Performance degradation indicators
```

---

## scripts/_container_inspector.sh

**Location:** `/scripts/_container_inspector.sh`  
**Purpose:** Deep inspection of container health and performance metrics.

### Description
Performs detailed analysis of container health, resource usage, and performance characteristics to identify optimization opportunities and potential issues.

### Inspection Capabilities
```bash
# Resource Analysis
- CPU usage patterns
- Memory consumption trends
- Network I/O statistics
- Disk usage and I/O

# Health Monitoring
- Container startup times
- Service response times
- Health check success rates
- Dependency health status

# Performance Metrics
- Request processing times
- Database query performance
- Cache hit rates
- Resource efficiency metrics
```

### Reporting Format
```json
{
  "container": "api",
  "timestamp": "2025-08-04T10:30:00Z",
  "health": "healthy",
  "resources": {
    "cpu_percent": 15.2,
    "memory_usage": "256MB",
    "memory_limit": "512MB",
    "network_rx": "1.2MB/s",
    "network_tx": "800KB/s"
  },
  "performance": {
    "avg_response_time": "125ms",
    "requests_per_second": 45,
    "error_rate": 0.02
  }
}
```

---

## Utility Monitoring Scripts

### _log_formatter.sh
**Purpose:** Standardizes log formatting across all monitoring scripts.

**Features:**
- Consistent timestamp formatting
- Structured message formatting
- Color coding for different severity levels
- JSON output support for structured logging

### _log_failures.sh
**Purpose:** Handles failure event logging with proper categorization.

**Features:**
- Failure classification (critical, major, minor)
- Automatic escalation based on failure type
- Integration with alerting systems
- Failure pattern analysis

### _find_error_source.sh
**Purpose:** Intelligent error source identification and analysis.

**Features:**
- Log correlation across services
- Error pattern matching
- Root cause analysis suggestions
- Integration with AI diagnostics

### _check_stack_health.sh
**Purpose:** Comprehensive health check for the entire application stack.

**Features:**
- Service availability verification
- Inter-service connectivity testing
- Performance baseline validation
- Security policy compliance checking

### _ask_gemini.sh
**Purpose:** AI-powered diagnostic assistance using Gemini AI.

**Features:**
- Automated error analysis
- Suggested remediation actions
- Knowledge base integration
- Interactive diagnostic sessions

---

## Monitoring Workflows

### Real-time Monitoring
```bash
# View real-time errors
tail -f logs/runtime_errors.log

# Monitor specific service
docker logs -f <service_name>

# Check overall health
./scripts/_check_stack_health.sh
```

### Error Investigation
```bash
# Find error sources
./scripts/_find_error_source.sh

# Get AI diagnostics  
./scripts/_ask_gemini.sh

# Comprehensive analysis
cat logs/error_log.txt | grep -A 10 -B 10 "ERROR"
```

### Performance Monitoring
```bash
# Container performance
./scripts/_container_inspector.sh

# Resource usage
docker stats

# Log analysis
grep "PERFORMANCE" logs/*.log
```

---

## Log File Structure

### Primary Log Files
```
logs/
├── error_log.txt              # Main error log with detailed context
├── runtime_errors.log         # Real-time error stream
├── docker_cleanup.log         # Docker maintenance operations
├── security_audit.log         # Security events and audits
├── performance.log            # Performance metrics and trends
├── container_health.log       # Container health status
├── .last_failed_service       # Last service that failed
├── .last_invocation_command   # Last command that caused error
└── archives/                  # Rotated log archives
    ├── error_log_2025-08-01.gz
    ├── error_log_2025-08-02.gz
    └── ...
```

### Log Entry Format
```
--- ERROR LOGGED AT 2025-08-04 10:30:00 for service: api ---
Invocation Command: ./run.sh --soft-reset
Context: Database connection failure during startup
Severity: CRITICAL
Category: DATABASE_CONNECTION

--- DETAILED INFORMATION ---
Error: Connection to database failed after 30 seconds
Database URL: postgresql://app_user@postgres:5432/ai_workflow_db
SSL Mode: require
Certificate: /etc/certs/api/unified-cert.pem

--- DIAGNOSTIC SUGGESTIONS ---
1. Verify database service is running: docker compose ps postgres
2. Check database logs: docker compose logs postgres  
3. Validate SSL certificates: ./scripts/security/validate_security_implementation.sh
4. Test database connectivity: ./scripts/test_database_connection.sh

--- END ERROR LOG ---
```

---

## Monitoring Integration

### Docker Integration
- **Container Events:** Monitors Docker daemon events
- **Service Health:** Integrates with Docker health checks
- **Resource Limits:** Monitors against container limits
- **Network Monitoring:** Tracks inter-container communication

### Application Integration
- **Structured Logging:** Applications use standardized log formats
- **Metrics Export:** Applications export performance metrics
- **Health Endpoints:** Services provide health check endpoints
- **Error Reporting:** Applications report errors to monitoring system

### External Integration
- **Prometheus:** Metrics export for Prometheus monitoring
- **Grafana:** Dashboard integration for visualization
- **Alerting:** Integration with external alerting systems
- **Log Aggregation:** Compatible with external log management

---

## Best Practices

### Monitoring Strategy
1. **Layered Approach:** Multiple monitoring layers for comprehensive coverage
2. **Proactive Monitoring:** Detect issues before they impact users
3. **Context Preservation:** Maintain context for effective troubleshooting
4. **Performance Impact:** Minimize monitoring overhead on system performance

### Log Management
1. **Structured Logging:** Use consistent, structured log formats
2. **Appropriate Levels:** Use correct log levels for different events
3. **Sensitive Data:** Never log sensitive information
4. **Storage Management:** Implement proper log rotation and archiving

### Error Handling
1. **Fast Detection:** Detect errors as quickly as possible
2. **Rich Context:** Provide comprehensive error context
3. **Automated Response:** Automate responses to common issues
4. **Escalation:** Proper escalation for critical issues

---

*For advanced monitoring configuration and troubleshooting, see the [Monitoring Guide](../monitoring.md).*