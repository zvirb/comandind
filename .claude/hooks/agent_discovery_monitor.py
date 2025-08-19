#!/usr/bin/env python3
"""
Agent Discovery Monitor Hook

This hook monitors for new agents being created and automatically triggers
the agent-integration-orchestrator to handle complete ecosystem integration.

This runs as a user-prompt-submit-hook to detect agent changes and respond automatically.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set

class AgentDiscoveryMonitor:
    def __init__(self):
        self.claude_dir = Path("/home/marku/ai_workflow_engine/.claude")
        self.agents_dir = self.claude_dir / "agents"
        self.state_file = self.claude_dir / "agent_registry_state.json"
        
    def get_current_agents(self) -> Set[str]:
        """Get list of currently known agents"""
        agents = set()
        
        # Scan .claude/agents directory for .md files
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("*.md"):
                agents.add(agent_file.stem)
            
            # Also scan subdirectories
            for subdir in self.agents_dir.iterdir():
                if subdir.is_dir():
                    for agent_file in subdir.glob("*.md"):
                        agents.add(subdir.name)
        
        return agents
    
    def load_previous_state(self) -> Set[str]:
        """Load previously known agents from state file"""
        if not self.state_file.exists():
            return set()
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return set(data.get('known_agents', []))
        except (json.JSONDecodeError, KeyError):
            return set()
    
    def save_current_state(self, agents: Set[str]):
        """Save current agent state"""
        data = {
            'known_agents': list(agents),
            'last_updated': str(Path(__file__).stat().st_mtime)
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def detect_agent_changes(self, user_input: str) -> List[str]:
        """Detect new agents from command output or direct scanning"""
        new_agents = []
        
        # Method 1: Parse command output for agent creation messages
        agent_creation_patterns = [
            r"Created agent: \[1m(.+?)\[22m",  # From /agents command
            r"Created agent: (.+?)$",           # Simple format
            r"Added agent: (.+?)$",             # Alternative format
        ]
        
        for pattern in agent_creation_patterns:
            matches = re.findall(pattern, user_input, re.MULTILINE | re.IGNORECASE)
            new_agents.extend(matches)
        
        # Method 2: Compare current agents with previous state
        current_agents = self.get_current_agents()
        previous_agents = self.load_previous_state()
        discovered_agents = current_agents - previous_agents
        
        # Convert to list and clean up names
        for agent in discovered_agents:
            clean_name = agent.replace('-', '_').replace(' ', '_').lower()
            if clean_name not in new_agents:
                new_agents.append(clean_name)
        
        # Save updated state
        if discovered_agents:
            self.save_current_state(current_agents)
        
        return new_agents
    
    def should_trigger_integration(self, user_input: str) -> tuple[bool, List[str]]:
        """Determine if agent integration should be triggered"""
        
        # Skip if this is already an agent integration response
        if "agent-integration-orchestrator" in user_input.lower():
            return False, []
        
        # Skip if user is explicitly managing agents manually
        if any(phrase in user_input.lower() for phrase in [
            "don't integrate", "manual integration", "skip integration"
        ]):
            return False, []
        
        new_agents = self.detect_agent_changes(user_input)
        
        return len(new_agents) > 0, new_agents

def main():
    """Main hook function - called by Claude Code"""
    import sys
    
    # Get user input from command line args or stdin
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = sys.stdin.read().strip()
    
    monitor = AgentDiscoveryMonitor()
    should_trigger, new_agents = monitor.should_trigger_integration(user_input)
    
    if should_trigger:
        print(f"🤖 New agent(s) detected: {', '.join(new_agents)}")
        print("⚡ Triggering automatic agent integration...")
        
        # Format the integration request
        integration_request = f"""I need to integrate newly discovered agent(s) into the ecosystem: {', '.join(new_agents)}

Please use the agent-integration-orchestrator to:
1. Create comprehensive documentation for each new agent
2. Update all relevant registries and cross-references  
3. Establish collaboration protocols
4. Ensure complete ecosystem integration

New agents detected: {', '.join(new_agents)}"""
        
        # Output the integration request for Claude to process
        print("=" * 60)
        print("AGENT INTEGRATION REQUEST:")
        print("=" * 60)
        print(integration_request)
        print("=" * 60)
        
        return True
    
    return False

if __name__ == "__main__":
    main()