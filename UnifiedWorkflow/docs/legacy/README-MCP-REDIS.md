# MCP Redis Setup for Claude/Gemini

This setup provides a dedicated Redis instance specifically for Model Context Protocol (MCP) access by coding assistants like Claude and Gemini.

## 🚀 Auto-Start Feature

**Claude and Gemini will automatically start the Redis MCP server when they begin a session!**

The system includes:
- **Auto-start**: Redis spins up automatically when MCP is first accessed
- **Session tracking**: Monitors active coding sessions
- **Auto-cleanup**: Stops Redis after 30 minutes of inactivity
- **Smart management**: Multiple sessions share the same Redis instance

## Manual Controls (Optional)

1. **Manually start Redis MCP server:**
   ```bash
   ./scripts/mcp-redis-start.sh
   ```

2. **Manually stop Redis MCP server:**
   ```bash
   ./scripts/mcp-redis-stop.sh
   ```

3. **Check session status:**
   ```bash
   ./scripts/mcp-session-manager.sh status
   ```

## What This Provides

- **Dedicated Redis Instance**: Separate from the production Redis with security
- **Local Access Only**: Runs on `localhost:6380` 
- **Simple Authentication**: Uses password `simple_mcp_password`
- **Memory Limited**: 256MB max memory with LRU eviction
- **On-Demand**: Only runs when explicitly started

## Security Notes

- This Redis instance is **NOT for production data**
- It's designed for temporary coding session data only  
- Uses simple authentication suitable for local development
- No network isolation - local access only
- Automatically stops when not needed

## Configuration

The MCP configuration is in `.mcp.json`:
```json
{
  "mcpServers": {
    "redis": {
      "type": "stdio", 
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-redis",
        "redis://:simple_mcp_password@localhost:6380"
      ]
    }
  }
}
```

## Integration with Claude Code

After starting the Redis MCP server, Claude Code should detect it automatically. You can verify with:
```bash
claude /mcp
```

The Redis MCP server should show as ✔ instead of ⚠.