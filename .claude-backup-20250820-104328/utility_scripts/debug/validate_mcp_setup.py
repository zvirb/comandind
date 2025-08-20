#!/usr/bin/env python3
"""
Validation script to check MCP server setup for Claude Code integration
"""

import json
import os
import sys
import subprocess
from pathlib import Path

def check_settings_file():
    """Check if Claude Code settings file exists and has MCP server config"""
    settings_path = Path.home() / ".claude-code" / "settings.json"
    
    if not settings_path.exists():
        return False, f"Settings file not found: {settings_path}"
    
    try:
        with open(settings_path) as f:
            settings = json.load(f)
        
        mcp_servers = settings.get("mcpServers", {})
        if "claude-agent-orchestrator" not in mcp_servers:
            return False, "claude-agent-orchestrator not found in mcpServers"
        
        orchestrator_config = mcp_servers["claude-agent-orchestrator"]
        required_fields = ["command", "args", "cwd", "env"]
        
        for field in required_fields:
            if field not in orchestrator_config:
                return False, f"Missing required field: {field}"
        
        return True, "Settings file configured correctly"
        
    except Exception as e:
        return False, f"Error reading settings: {e}"

def check_mcp_server_files():
    """Check if MCP server files exist"""
    base_path = Path("/home/marku/ai_workflow_engine/mcp_server")
    
    required_files = [
        "mcp_server_main.py",
        "claude_agent_orchestrator/__init__.py",
        "claude_agent_orchestrator/server.py",
        "claude_agent_orchestrator/registry.py",
        "claude_agent_orchestrator/orchestration.py",
        "claude_agent_orchestrator/context.py",
        "claude_agent_orchestrator/ollama_integration.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(str(full_path))
    
    if missing_files:
        return False, f"Missing files: {missing_files}"
    
    return True, "All MCP server files present"

def check_agent_registry():
    """Check if agent registry path exists with agent files"""
    registry_path = Path.home() / ".claude-code" / "agents"
    
    if not registry_path.exists():
        return False, f"Agent registry path not found: {registry_path}"
    
    agent_files = list(registry_path.glob("*.md"))
    if len(agent_files) == 0:
        return False, "No agent files found in registry"
    
    return True, f"Found {len(agent_files)} agent files"

def check_mcp_server_executable():
    """Check if MCP server entry point is executable"""
    entry_point = "/home/marku/ai_workflow_engine/mcp_server/mcp_server_main.py"
    
    try:
        result = subprocess.run(
            ["python", entry_point, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and "Claude Agent Orchestrator" in result.stdout:
            return True, "MCP server entry point working"
        else:
            return False, f"Entry point failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Error testing entry point: {e}"

def main():
    print("🧪 Validating MCP Server Setup for Claude Code")
    print("=" * 60)
    
    checks = [
        ("Settings File", check_settings_file),
        ("MCP Server Files", check_mcp_server_files), 
        ("Agent Registry", check_agent_registry),
        ("MCP Server Executable", check_mcp_server_executable)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            success, message = check_func()
            status = "✅" if success else "❌"
            print(f"{status} {check_name}: {message}")
            
            if not success:
                all_passed = False
                
        except Exception as e:
            print(f"❌ {check_name}: Error - {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! MCP server is ready for Claude Code.")
        print("\n📋 Next steps:")
        print("1. Restart Claude Code CLI to load the MCP server")
        print("2. Check available tools with the slash command")
        print("3. Look for 'claude-agent-orchestrator' in MCP servers list")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())