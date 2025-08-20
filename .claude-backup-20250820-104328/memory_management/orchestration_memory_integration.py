#!/usr/bin/env python3
"""
Orchestration Memory Integration
Integrates intelligent memory management with the agentic orchestration system
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add necessary paths
sys.path.append('/home/marku/ai_workflow_engine/app')
sys.path.append('/home/marku/ai_workflow_engine/.claude/memory_management')

from intelligent_memory_manager import IntelligentMemoryManager, MemoryPackage

class OrchestrationMemoryIntegration:
    """Integrates memory management with orchestration system"""
    
    def __init__(self):
        self.memory_manager = IntelligentMemoryManager()
        self.setup_logging()
        
        # Start memory monitoring
        self.memory_manager.start_monitoring(check_interval=15)  # Check every 15 seconds
        
    def setup_logging(self):
        """Setup logging"""
        self.logger = logging.getLogger("OrchestrationMemory")
        
    def store_context_package(self, package_id: str, content: str, 
                            package_type: str = "context", 
                            priority: str = "medium",
                            context_tags: List[str] = None) -> bool:
        """Store context package in persistent memory"""
        try:
            # Calculate approximate token count
            tokens = len(content.split()) * 1.3  # Rough estimate
            
            package = MemoryPackage(
                package_id=package_id,
                package_type=package_type,
                content=content,
                tokens=int(tokens),
                created_at=datetime.now().isoformat(),
                last_accessed=datetime.now().isoformat(),
                priority=priority,
                context_tags=context_tags or []
            )
            
            success = self.memory_manager.store_memory_package(package)
            
            if success:
                self.logger.info(f"Stored context package: {package_id} ({tokens} tokens)")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error storing context package {package_id}: {e}")
            return False
            
    def load_context_package(self, package_id: str) -> Optional[str]:
        """Load context package content"""
        try:
            package = self.memory_manager.load_memory_package(package_id)
            if package:
                self.logger.info(f"Loaded context package: {package_id}")
                return package.content
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading context package {package_id}: {e}")
            return None
            
    def store_agent_results(self, agent_name: str, results: Dict[str, Any]) -> bool:
        """Store agent execution results"""
        try:
            package_id = f"agent-results-{agent_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            content = json.dumps(results, indent=2)
            
            return self.store_context_package(
                package_id=package_id,
                content=content,
                package_type="agent-results",
                priority="high",
                context_tags=[agent_name, "agent-results", "execution"]
            )
            
        except Exception as e:
            self.logger.error(f"Error storing agent results for {agent_name}: {e}")
            return False
            
    def store_orchestration_state(self, phase: int, state_data: Dict[str, Any]) -> bool:
        """Store orchestration phase state"""
        try:
            package_id = f"orchestration-phase-{phase}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            content = json.dumps(state_data, indent=2)
            
            return self.store_context_package(
                package_id=package_id,
                content=content,
                package_type="orchestration-state",
                priority="critical",
                context_tags=[f"phase-{phase}", "orchestration", "state"]
            )
            
        except Exception as e:
            self.logger.error(f"Error storing orchestration state for phase {phase}: {e}")
            return False
            
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory management status"""
        return self.memory_manager.get_status_report()
        
    def emergency_backup_orchestration(self, orchestration_data: Dict[str, Any]) -> str:
        """Emergency backup of orchestration state"""
        try:
            # Save to progress backup
            backup_file = self.memory_manager.save_progress_report(orchestration_data)
            
            # Also store as memory package
            package_id = f"emergency-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.store_context_package(
                package_id=package_id,
                content=json.dumps(orchestration_data, indent=2),
                package_type="emergency-backup",
                priority="critical",
                context_tags=["emergency", "backup", "orchestration"]
            )
            
            self.logger.critical(f"Emergency backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Error during emergency backup: {e}")
            return None
            
    def migrate_existing_packages(self):
        """Migrate existing context packages to persistent storage"""
        try:
            context_packages_dir = "/home/marku/ai_workflow_engine/.claude/context_packages"
            
            if not os.path.exists(context_packages_dir):
                return
                
            for filename in os.listdir(context_packages_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(context_packages_dir, filename)
                    
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        package_id = filename.replace('.json', '')
                        
                        success = self.store_context_package(
                            package_id=package_id,
                            content=content,
                            package_type="migrated-context",
                            priority="medium",
                            context_tags=["migrated", "context-package"]
                        )
                        
                        if success:
                            self.logger.info(f"Migrated package: {package_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error migrating {filename}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error during package migration: {e}")
            
    def setup_orchestration_memory_hooks(self):
        """Setup memory management hooks for orchestration"""
        try:
            # Create orchestration integration script
            hook_script = """#!/bin/bash
# Memory Management Hook for Orchestration
# Monitors memory usage during orchestration phases

MEMORY_LOG="/home/marku/ai_workflow_engine/logs/orchestration_memory.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log memory usage
echo "[$TIMESTAMP] Orchestration Memory Check" >> "$MEMORY_LOG"
free -h >> "$MEMORY_LOG"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits >> "$MEMORY_LOG" 2>/dev/null || echo "No GPU detected" >> "$MEMORY_LOG"
echo "---" >> "$MEMORY_LOG"

# Check if memory manager is running
python3 /home/marku/ai_workflow_engine/.claude/memory_management/intelligent_memory_manager.py --status >> "$MEMORY_LOG" 2>&1
"""
            
            hook_file = "/home/marku/ai_workflow_engine/.claude/memory_management/orchestration_memory_hook.sh"
            with open(hook_file, 'w') as f:
                f.write(hook_script)
            
            os.chmod(hook_file, 0o755)
            
            self.logger.info("Orchestration memory hooks setup complete")
            
        except Exception as e:
            self.logger.error(f"Error setting up memory hooks: {e}")

# Global instance for orchestration integration
orchestration_memory = OrchestrationMemoryIntegration()

def initialize_orchestration_memory():
    """Initialize orchestration memory integration"""
    try:
        # Migrate existing packages
        orchestration_memory.migrate_existing_packages()
        
        # Setup hooks
        orchestration_memory.setup_orchestration_memory_hooks()
        
        # Start monitoring
        status = orchestration_memory.get_memory_status()
        logging.info(f"Orchestration memory integration initialized: {status}")
        
        return orchestration_memory
        
    except Exception as e:
        logging.error(f"Error initializing orchestration memory: {e}")
        return None

# Convenience functions for orchestration system
def store_phase_context(phase: int, context_data: Dict[str, Any]) -> bool:
    """Store context for orchestration phase"""
    return orchestration_memory.store_orchestration_state(phase, context_data)

def store_agent_context(agent_name: str, context: str, priority: str = "medium") -> bool:
    """Store agent context package"""
    package_id = f"agent-context-{agent_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return orchestration_memory.store_context_package(
        package_id=package_id,
        content=context,
        package_type="agent-context",
        priority=priority,
        context_tags=[agent_name, "context"]
    )

def get_agent_context(agent_name: str) -> Optional[str]:
    """Get latest context for agent"""
    # This would query memory MCP for latest agent context
    # Implementation would search for latest package with agent_name tag
    return orchestration_memory.load_context_package(f"agent-context-{agent_name}")

def emergency_save_orchestration(orchestration_state: Dict[str, Any]) -> str:
    """Emergency save of orchestration state"""
    return orchestration_memory.emergency_backup_orchestration(orchestration_state)

if __name__ == "__main__":
    # Initialize and test
    integration = initialize_orchestration_memory()
    
    if integration:
        print("Orchestration Memory Integration Status:")
        status = integration.get_memory_status()
        print(json.dumps(status, indent=2))