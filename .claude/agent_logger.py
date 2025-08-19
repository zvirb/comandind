#!/usr/bin/env python3
"""
Agent Logger
Simple logging system for agent actions and verification
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(".claude/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_action(agent_name: str, action: str, tools_used=None, result="unknown", context=None):
    """Log an agent action"""
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "agent": agent_name,
        "action": action,
        "tools_used": tools_used or [],
        "result": result,
        "context": context
    }
    
    # Write to agent-specific log file
    log_file = LOGS_DIR / f"{agent_name}_actions.log"
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"📝 [{agent_name}] {action} -> {result}")

def log_verification(agent_name: str, claim: str, evidence_provided=False, validated=False):
    """Log agent verification attempt"""
    timestamp = datetime.now().isoformat()
    
    verification_entry = {
        "timestamp": timestamp,
        "agent": agent_name,
        "claim": claim,
        "evidence_provided": evidence_provided,
        "validated": validated,
        "status": "validated" if validated else "failed"
    }
    
    # Write to verification log
    verification_file = LOGS_DIR / "agent_verification.log"
    
    with open(verification_file, "a") as f:
        f.write(json.dumps(verification_entry) + "\n")
    
    status_icon = "✅" if validated else "❌"
    print(f"🔍 [{agent_name}] {status_icon} {claim}")

def get_agent_logs(agent_name: str = None):
    """Get agent logs"""
    if agent_name:
        log_file = LOGS_DIR / f"{agent_name}_actions.log"
        if log_file.exists():
            with open(log_file) as f:
                return [json.loads(line.strip()) for line in f if line.strip()]
        return []
    else:
        # Return all logs
        all_logs = {}
        for log_file in LOGS_DIR.glob("*_actions.log"):
            agent = log_file.stem.replace("_actions", "")
            with open(log_file) as f:
                all_logs[agent] = [json.loads(line.strip()) for line in f if line.strip()]
        return all_logs