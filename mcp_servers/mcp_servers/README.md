# MCP Servers for AI Workflow Orchestration

This directory contains the implementation of two Model Context Protocol (MCP) servers required for the AI Workflow Orchestration system.

## 🚀 Quick Start

### Option 1: Simple Mode (No Docker Required)

```bash
# Start servers
./start_simple.sh

# Test servers
python test_mcp_servers.py

# Stop servers
./stop_simple.sh
```

### Option 2: Docker Mode (Recommended for Production)

```bash
# Start servers with Docker
./start_mcp_servers.sh

# Test servers
python test_mcp_servers.py

# Stop servers
./stop_mcp_servers.sh
```

## 📦 Components

### 1. Memory MCP Server
- **Port**: 8002
- **Purpose**: Long-term storage of agent outputs, documentation, and knowledge graph
- **Features**:
  - Entity creation and management
  - Full-text search capabilities
  - Knowledge graph relationships
  - Token limit enforcement (8000 tokens)
  - Persistent file-based storage

### 2. Redis MCP Server
- **Port**: 8001
- **Purpose**: Real-time coordination between parallel agent streams
- **Features**:
  - Hash operations for shared workspace
  - Set operations for agent notifications
  - Sorted set operations for timeline tracking
  - High-performance in-memory storage

### 3. Redis Database/Alternative
- **Port**: 6379 (Docker) or built-in alternative
- **Purpose**: Backend storage for Redis MCP
- **Options**:
  - Docker Redis (production)
  - Python in-memory alternative (development)

## 📁 Directory Structure

```
mcp_servers/
├── memory/                 # Memory MCP server
│   ├── memory_mcp_server.py
│   └── storage/           # Persistent storage
│       ├── entities/      # Entity JSON files
│       ├── knowledge_graph/ # Relationship data
│       └── index.json     # Search index
├── redis/                  # Redis MCP server
│   ├── redis_mcp_server.py
│   ├── redis_alternative.py # Python Redis alternative
│   ├── redis.conf         # Redis configuration
│   └── data/              # Redis persistence
├── logs/                   # Server logs
├── pids/                   # Process ID files
├── docker-compose.yml      # Docker configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration
├── start_simple.sh         # Start without Docker
├── stop_simple.sh          # Stop without Docker
├── start_mcp_servers.sh    # Start with Docker
├── stop_mcp_servers.sh     # Stop with Docker
└── test_mcp_servers.py     # Test suite
```

## 🔧 Configuration

Edit `.env` file to customize:

```bash
# Memory MCP Configuration
MEMORY_MCP_PORT=8002
MEMORY_MCP_TOKEN_LIMIT=8000

# Redis MCP Configuration  
REDIS_MCP_PORT=8001

# Redis Database
REDIS_PORT=6379
```

## 🧪 Testing

Run the test suite to verify servers are working:

```bash
python test_mcp_servers.py
```

Expected output:
```
✅ Redis MCP health check: PASSED
✅ Memory MCP health check: PASSED
✅ Entity creation: PASSED
✅ Entity search: PASSED
✅ Redis operations: PASSED
```

## 📊 API Documentation

When servers are running, visit:
- Redis MCP API: http://localhost:8001/docs
- Memory MCP API: http://localhost:8002/docs

## 🔌 Integration with Claude

The MCP servers integrate with Claude's workflow orchestration by providing:

1. **Memory MCP** - Used in:
   - Phase 0: Query existing knowledge
   - Phase 5: Store agent outputs
   - Phase 9: Store learning patterns

2. **Redis MCP** - Used in:
   - Phase 3-5: Agent coordination
   - Phase 6-7: Validation coordination
   - Throughout: Real-time status updates

## 🛠️ Troubleshooting

### Servers won't start
- Check Python 3 is installed: `python3 --version`
- Check ports are free: `lsof -i :8001` and `lsof -i :8002`
- Check logs in `logs/` directory

### Connection errors
- Ensure servers are running: `ps aux | grep mcp_server`
- Check firewall settings
- Verify localhost connectivity

### Docker issues
- Ensure Docker is running: `docker info`
- Check Docker Compose: `docker compose version`
- Clear Docker resources: `docker system prune`

## 📝 Development

To modify the MCP servers:

1. Edit the server files in `memory/` or `redis/`
2. Restart servers with `./stop_simple.sh && ./start_simple.sh`
3. Test changes with `python test_mcp_servers.py`

## 🔒 Security Notes

- Default configuration has no authentication
- For production, enable Redis password in `.env`
- Consider network isolation for production deployment
- Implement API key authentication for MCP endpoints

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/docs/)
- [AI Workflow Orchestration Guide](../CLAUDE.md)