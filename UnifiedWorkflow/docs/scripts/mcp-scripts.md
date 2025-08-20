# MCP Scripts Documentation

Model Context Protocol (MCP) scripts manage MCP server infrastructure for AI coding sessions with Claude and Gemini. These scripts handle Redis-based session storage, server lifecycle management, and integration with AI development workflows.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `mcp-redis-start.sh` | Start Redis MCP server | `./scripts/mcp-redis-start.sh` |
| `mcp-redis-stop.sh` | Stop Redis MCP server | `./scripts/mcp-redis-stop.sh` |
| `mcp-redis-wrapper.sh` | Redis MCP wrapper script | Internal use |
| `mcp-session-manager.sh` | MCP session management | `./scripts/mcp-session-manager.sh [command]` |

---

## scripts/mcp-redis-start.sh

**Location:** `/scripts/mcp-redis-start.sh`  
**Purpose:** Starts the Redis MCP server for AI coding sessions with Claude and Gemini.

### Description
Initializes and starts a dedicated Redis instance configured for Model Context Protocol operations. This provides persistent storage for AI coding sessions, context management, and inter-session data sharing.

### Usage
```bash
./scripts/mcp-redis-start.sh
```

### What It Does
1. **Duplicate Check:** Verifies if Redis MCP server is already running
2. **Container Startup:** Starts Redis MCP using `docker-compose-mcp.yml`
3. **Health Verification:** Waits for Redis to be fully operational
4. **Connection Testing:** Validates Redis connectivity with authentication
5. **Status Reporting:** Provides connection details and management commands

### Process Flow
```bash
# 1. Check existing instance
if docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
    echo "Redis MCP server is already running!"
    exit 0
fi

# 2. Start MCP Redis instance
docker compose -f docker-compose-mcp.yml up -d redis-mcp

# 3. Wait for health check (30-second timeout)
timeout 30 bash -c 'until docker exec redis-mcp redis-cli -a simple_mcp_password ping 2>/dev/null | grep -q PONG; do sleep 1; done'

# 4. Report status
if [ $? -eq 0 ]; then
    echo "✅ Redis MCP server is ready at localhost:6380"
    echo "Password: simple_mcp_password"
    echo "To stop: ./scripts/mcp-redis-stop.sh"
else
    echo "❌ Failed to start Redis MCP server"
fi
```

### Configuration
```yaml
# docker-compose-mcp.yml configuration
services:
  redis-mcp:
    image: redis:7-alpine
    container_name: redis-mcp
    ports:
      - "6380:6379"
    environment:
      - REDIS_PASSWORD=simple_mcp_password
    command: redis-server --requirepass simple_mcp_password
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "simple_mcp_password", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3
```

### Connection Details
- **Host:** localhost
- **Port:** 6380
- **Password:** simple_mcp_password
- **Protocol:** Redis Protocol (RESP)
- **Authentication:** Required

### Output
```
Starting Redis MCP server for coding sessions...
Waiting for Redis MCP to be ready...
✅ Redis MCP server is ready at localhost:6380
Password: simple_mcp_password
To stop: ./scripts/mcp-redis-stop.sh
```

### Use Cases
- **Claude Coding Sessions:** Persistent context storage for Claude AI
- **Gemini Integration:** Session management for Gemini AI workflows
- **Cross-Session Data:** Sharing data between multiple AI sessions
- **Development Context:** Maintaining project context across sessions
- **Debugging Support:** Storing debugging information and logs

---

## scripts/mcp-redis-stop.sh

**Location:** `/scripts/mcp-redis-stop.sh`  
**Purpose:** Safely stops the Redis MCP server and cleans up resources.

### Description
Gracefully shuts down the Redis MCP server, ensuring data persistence and proper resource cleanup.

### Usage
```bash
./scripts/mcp-redis-stop.sh
```

### Process
1. **Service Detection:** Locates running Redis MCP container
2. **Graceful Shutdown:** Sends proper shutdown signals
3. **Data Persistence:** Ensures data is saved before shutdown
4. **Resource Cleanup:** Removes container and associated resources
5. **Verification:** Confirms successful shutdown

### Implementation
```bash
#!/bin/bash
# Stop Redis MCP server for Claude/Gemini coding sessions

echo "Stopping Redis MCP server..."

# Check if running
if ! docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
    echo "Redis MCP server is not running."
    exit 0
fi

# Graceful shutdown with data persistence
docker compose -f docker-compose-mcp.yml down

# Verify shutdown
if [ $? -eq 0 ]; then
    echo "✅ Redis MCP server stopped successfully"
    echo "Data has been persisted and can be restored on next start"
else
    echo "❌ Error stopping Redis MCP server"
    exit 1
fi
```

### Data Persistence
- **Automatic Saves:** Redis automatically persists data
- **Volume Mounting:** Data stored in Docker volumes
- **Graceful Shutdown:** Ensures proper data writes before exit
- **Recovery:** Data available on next startup

---

## scripts/mcp-redis-wrapper.sh

**Location:** `/scripts/mcp-redis-wrapper.sh`  
**Purpose:** Internal wrapper script for Redis MCP operations and management.

### Description
Provides a programmatic interface for Redis MCP operations, including configuration management, health monitoring, and maintenance tasks.

### Features
```bash
# Configuration Management
- Dynamic configuration updates
- Environment variable management
- Security setting adjustments
- Performance tuning parameters

# Health Monitoring
- Connection health checks
- Memory usage monitoring
- Performance metrics collection
- Error detection and reporting

# Maintenance Operations
- Database cleanup
- Memory optimization
- Connection pool management
- Backup and restore operations
```

### Internal Operations
```bash
# Health check function
check_mcp_redis_health() {
    local timeout=10
    local retries=3
    
    for i in $(seq 1 $retries); do
        if docker exec redis-mcp redis-cli -a simple_mcp_password ping | grep -q PONG; then
            return 0
        fi
        sleep $((timeout / retries))
    done
    
    return 1
}

# Memory optimization
optimize_mcp_redis_memory() {
    docker exec redis-mcp redis-cli -a simple_mcp_password CONFIG SET maxmemory-policy allkeys-lru
    docker exec redis-mcp redis-cli -a simple_mcp_password MEMORY PURGE
}

# Connection management
manage_mcp_connections() {
    local max_connections=100
    docker exec redis-mcp redis-cli -a simple_mcp_password CONFIG SET maxclients $max_connections
}
```

---

## scripts/mcp-session-manager.sh

**Location:** `/scripts/mcp-session-manager.sh`  
**Purpose:** Comprehensive MCP session lifecycle management and operations.

### Description
Advanced session management tool that handles MCP session creation, monitoring, cleanup, and data management for AI coding workflows.

### Usage
```bash
./scripts/mcp-session-manager.sh [COMMAND] [OPTIONS]
```

### Commands
- `start` - Start new MCP session
- `stop <session_id>` - Stop specific session
- `list` - List active sessions
- `cleanup` - Clean up expired sessions
- `backup` - Backup session data
- `restore <backup_id>` - Restore session from backup
- `monitor` - Monitor session activity
- `stats` - Display session statistics

### Examples
```bash
# Start new session
./scripts/mcp-session-manager.sh start --type claude --project ai_workflow_engine

# List active sessions
./scripts/mcp-session-manager.sh list

# Stop specific session
./scripts/mcp-session-manager.sh stop session_12345

# Clean up expired sessions
./scripts/mcp-session-manager.sh cleanup --older-than 24h

# Monitor session activity
./scripts/mcp-session-manager.sh monitor --session session_12345

# Backup all sessions
./scripts/mcp-session-manager.sh backup --all

# Get session statistics
./scripts/mcp-session-manager.sh stats
```

### Session Management Features
```bash
# Session Lifecycle
- Session creation with unique identifiers
- Session expiration and timeout management
- Automatic cleanup of inactive sessions
- Session state persistence and recovery

# Data Management
- Context data storage and retrieval
- Session history and audit logging
- Data compression and optimization
- Cross-session data sharing

# Monitoring and Analytics
- Real-time session activity monitoring
- Performance metrics collection
- Usage statistics and reporting
- Error tracking and analysis
```

### Session Data Structure
```json
{
  "session_id": "session_20250804_103000_claude",
  "type": "claude",
  "project": "ai_workflow_engine",
  "created_at": "2025-08-04T10:30:00Z",
  "last_activity": "2025-08-04T11:15:30Z",
  "status": "active",
  "context": {
    "current_file": "/app/api/main.py",
    "working_directory": "/home/user/ai_workflow_engine",
    "conversation_history": [...],
    "project_state": {...}
  },
  "metadata": {
    "ai_model": "claude-3.5-sonnet",
    "session_duration": 2730,
    "commands_executed": 45,
    "files_modified": 8
  }
}
```

---

## MCP Integration Architecture

### Redis as Context Store
```bash
# Key Patterns
mcp:session:{session_id}:context     # Session context data
mcp:session:{session_id}:history     # Conversation history
mcp:session:{session_id}:state       # Current state
mcp:session:{session_id}:metadata    # Session metadata
mcp:sessions:active                  # Active session list
mcp:sessions:expired                 # Expired session queue
mcp:global:config                    # Global MCP configuration
```

### Data Flow
```
AI Client (Claude/Gemini)
    ↓
MCP Server (via Redis)
    ↓
AI Workflow Engine
    ↓
Application Services
```

### Session Lifecycle
1. **Initialization:** Session created with unique ID
2. **Context Loading:** Previous context restored if available
3. **Active Phase:** Commands and responses processed
4. **Context Updates:** Context continuously updated
5. **Cleanup:** Session data archived or purged

---

## Configuration and Customization

### Redis Configuration
```bash
# Performance Tuning
CONFIG SET maxmemory 256mb
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET timeout 300

# Security Settings
CONFIG SET requirepass simple_mcp_password
CONFIG SET protected-mode yes
CONFIG SET bind 127.0.0.1

# Persistence Settings
CONFIG SET save "900 1 300 10 60 10000"
CONFIG SET rdbcompression yes
CONFIG SET rdbchecksum yes
```

### MCP Server Configuration
```json
{
  "mcp_server": {
    "redis": {
      "host": "localhost",
      "port": 6380,
      "password": "simple_mcp_password",
      "db": 0,
      "max_connections": 10
    },
    "sessions": {
      "default_timeout": 3600,
      "max_context_size": "10MB",
      "cleanup_interval": 300,
      "max_sessions": 100
    },
    "logging": {
      "level": "INFO",
      "file": "logs/mcp_server.log",
      "max_size": "50MB",
      "backup_count": 5
    }
  }
}
```

---

## MCP Workflows

### Starting MCP Session
```bash
# 1. Start Redis MCP server
./scripts/mcp-redis-start.sh

# 2. Verify server health
./scripts/mcp-session-manager.sh stats

# 3. Configure AI client (Claude/Gemini) to use MCP server
# Redis connection: localhost:6380, password: simple_mcp_password

# 4. Start coding session with AI
# AI will automatically use MCP for context management
```

### Managing Active Sessions
```bash
# List all active sessions
./scripts/mcp-session-manager.sh list

# Monitor specific session
./scripts/mcp-session-manager.sh monitor --session session_12345

# View session statistics
./scripts/mcp-session-manager.sh stats --detailed
```

### Maintenance and Cleanup
```bash
# Clean up expired sessions (daily)
./scripts/mcp-session-manager.sh cleanup --older-than 24h

# Backup session data (weekly)
./scripts/mcp-session-manager.sh backup --all --compress

# Optimize Redis memory usage
./scripts/mcp-redis-wrapper.sh optimize-memory

# Stop MCP server when not needed
./scripts/mcp-redis-stop.sh
```

---

## Integration with AI Workflows

### Claude Integration
```bash
# Claude uses MCP for:
- Persistent conversation context
- Project state management
- File change tracking
- Command history
- Error context preservation
```

### Gemini Integration
```bash
# Gemini uses MCP for:
- Multi-turn conversation context
- Code analysis state
- Project understanding
- Development workflow tracking
- Session resumption
```

### Development Benefits
1. **Context Continuity:** Maintain context across AI sessions
2. **Project Memory:** AI remembers project structure and patterns
3. **Efficient Communication:** Reduced need to re-explain context
4. **Session Recovery:** Resume interrupted sessions
5. **Multi-AI Coordination:** Share context between different AI models

---

## Troubleshooting

### Common Issues
```bash
# Redis connection failed
# Solution: Check if Redis MCP is running
./scripts/mcp-redis-start.sh

# Session data corrupted
# Solution: Clean up and restart
./scripts/mcp-session-manager.sh cleanup --force
./scripts/mcp-redis-stop.sh
./scripts/mcp-redis-start.sh

# Memory issues
# Solution: Optimize Redis memory usage
./scripts/mcp-redis-wrapper.sh optimize-memory

# Performance issues
# Solution: Monitor and adjust configuration
./scripts/mcp-session-manager.sh monitor --performance
```

### Diagnostic Commands
```bash
# Check Redis health
docker exec redis-mcp redis-cli -a simple_mcp_password info

# View Redis memory usage
docker exec redis-mcp redis-cli -a simple_mcp_password info memory

# Check active connections
docker exec redis-mcp redis-cli -a simple_mcp_password client list

# Monitor Redis operations
docker exec redis-mcp redis-cli -a simple_mcp_password monitor
```

---

## Security Considerations

### Access Control
- **Password Protection:** Redis requires authentication
- **Network Isolation:** Bound to localhost only
- **Container Security:** Isolated in Docker container
- **Data Encryption:** Consider TLS for production use

### Data Privacy
- **Session Isolation:** Each session has separate namespace
- **Data Cleanup:** Automatic cleanup of expired sessions
- **Sensitive Data:** Avoid storing secrets in session context
- **Audit Logging:** Track session access and modifications

### Best Practices
1. **Regular Cleanup:** Clean up old sessions regularly
2. **Monitor Usage:** Track session activity and resource usage
3. **Backup Strategy:** Regular backups of important session data
4. **Security Updates:** Keep Redis updated to latest secure version
5. **Access Logging:** Log all MCP server access for security audit

---

*For advanced MCP integration and custom workflows, see the [MCP Integration Guide](../mcp-integration.md).*