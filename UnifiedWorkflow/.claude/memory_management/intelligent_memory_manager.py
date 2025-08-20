#!/usr/bin/env python3
"""
Intelligent Memory Manager for Claude Code AI Workflow Engine
Manages memory packages in persistent storage and monitors system resources
"""

import os
import sys
import json
import time
import psutil
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
import signal
import atexit

# Add app path for imports
sys.path.append('/home/marku/ai_workflow_engine/app')

@dataclass
class MemoryUsage:
    """Memory usage metrics"""
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    vram_used_gb: float
    vram_total_gb: float
    virtual_memory_gb: float
    process_memory_gb: float
    timestamp: str

@dataclass
class MemoryPackage:
    """Memory package for persistent storage"""
    package_id: str
    package_type: str
    content: str
    tokens: int
    created_at: str
    last_accessed: str
    priority: str
    context_tags: List[str]

class IntelligentMemoryManager:
    """Manages memory packages and system resource monitoring"""
    
    def __init__(self):
        self.setup_logging()
        self.memory_packages = {}
        self.monitoring_active = False
        self.cleanup_in_progress = False
        
        # Memory thresholds
        self.RAM_WARNING_THRESHOLD = 70  # %
        self.RAM_CRITICAL_THRESHOLD = 85  # %
        self.VRAM_WARNING_THRESHOLD = 80  # %
        self.VRAM_CRITICAL_THRESHOLD = 90  # %
        self.PROCESS_MEMORY_THRESHOLD = 8  # GB
        self.VIRTUAL_MEMORY_THRESHOLD = 20  # GB
        
        # Storage paths
        self.memory_db_path = "/home/marku/ai_workflow_engine/.claude/memory_db"
        self.progress_backup_path = "/home/marku/ai_workflow_engine/.claude/progress_backups"
        
        # Ensure directories exist
        os.makedirs(self.memory_db_path, exist_ok=True)
        os.makedirs(self.progress_backup_path, exist_ok=True)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        atexit.register(self.cleanup_on_exit)
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = "/home/marku/ai_workflow_engine/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{log_dir}/memory_manager.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("MemoryManager")
        
    def get_memory_usage(self) -> MemoryUsage:
        """Get current system memory usage"""
        try:
            # System RAM
            ram = psutil.virtual_memory()
            
            # Current process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # GPU VRAM (using nvidia-smi)
            vram_used, vram_total = self.get_gpu_memory()
            
            return MemoryUsage(
                ram_percent=ram.percent,
                ram_used_gb=ram.used / (1024**3),
                ram_total_gb=ram.total / (1024**3),
                vram_used_gb=vram_used,
                vram_total_gb=vram_total,
                virtual_memory_gb=process_memory.vms / (1024**3),
                process_memory_gb=process_memory.rss / (1024**3),
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            self.logger.error(f"Error getting memory usage: {e}")
            return None
            
    def get_gpu_memory(self) -> Tuple[float, float]:
        """Get GPU VRAM usage using nvidia-smi"""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=memory.used,memory.total',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                total_used = 0
                total_memory = 0
                
                for line in lines:
                    used, total = map(int, line.split(', '))
                    total_used += used
                    total_memory += total
                    
                return total_used / 1024, total_memory / 1024  # Convert MB to GB
            else:
                return 0.0, 0.0
        except Exception as e:
            self.logger.warning(f"Could not get GPU memory: {e}")
            return 0.0, 0.0
            
    def store_memory_package(self, package: MemoryPackage) -> bool:
        """Store memory package in persistent storage"""
        try:
            # Store in memory MCP
            self.store_in_memory_mcp(package)
            
            # Store in local file system as backup
            package_file = os.path.join(self.memory_db_path, f"{package.package_id}.json")
            with open(package_file, 'w') as f:
                json.dump(asdict(package), f, indent=2)
                
            self.logger.info(f"Stored memory package: {package.package_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing memory package {package.package_id}: {e}")
            return False
            
    def store_in_memory_mcp(self, package: MemoryPackage):
        """Store package in memory MCP system"""
        try:
            # Create entity in memory MCP
            entity_data = {
                "name": f"memory-package-{package.package_id}",
                "entityType": "memory-package",
                "observations": [
                    f"Package Type: {package.package_type}",
                    f"Tokens: {package.tokens}",
                    f"Priority: {package.priority}",
                    f"Context Tags: {', '.join(package.context_tags)}",
                    f"Content: {package.content}"
                ]
            }
            
            # Note: Would call MCP function here in actual implementation
            # mcp__memory__create_entities(entities=[entity_data])
            
        except Exception as e:
            self.logger.error(f"Error storing in memory MCP: {e}")
            
    def load_memory_package(self, package_id: str) -> Optional[MemoryPackage]:
        """Load memory package from persistent storage"""
        try:
            # Try to load from local storage first
            package_file = os.path.join(self.memory_db_path, f"{package_id}.json")
            if os.path.exists(package_file):
                with open(package_file, 'r') as f:
                    data = json.load(f)
                    package = MemoryPackage(**data)
                    package.last_accessed = datetime.now().isoformat()
                    return package
                    
            # Try to load from memory MCP
            return self.load_from_memory_mcp(package_id)
            
        except Exception as e:
            self.logger.error(f"Error loading memory package {package_id}: {e}")
            return None
            
    def load_from_memory_mcp(self, package_id: str) -> Optional[MemoryPackage]:
        """Load package from memory MCP system"""
        try:
            # Note: Would query MCP here in actual implementation
            # result = mcp__memory__search_nodes(query=f"memory-package-{package_id}")
            # Parse and return MemoryPackage
            
            return None  # Placeholder for now
            
        except Exception as e:
            self.logger.error(f"Error loading from memory MCP: {e}")
            return None
            
    def cleanup_memory_packages(self):
        """Clean up memory packages from RAM"""
        try:
            # Move all in-memory packages to persistent storage
            for package_id, package in self.memory_packages.items():
                self.store_memory_package(package)
                
            # Clear from RAM
            self.memory_packages.clear()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            self.logger.info("Memory packages cleaned up from RAM")
            
        except Exception as e:
            self.logger.error(f"Error during memory cleanup: {e}")
            
    def save_progress_report(self, orchestration_state: Dict = None):
        """Save current progress before cleanup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = os.path.join(self.progress_backup_path, f"progress_backup_{timestamp}.json")
            
            progress_data = {
                "timestamp": datetime.now().isoformat(),
                "memory_usage": asdict(self.get_memory_usage()) if self.get_memory_usage() else {},
                "orchestration_state": orchestration_state or {},
                "memory_packages_stored": len(self.memory_packages),
                "cleanup_reason": "Memory threshold exceeded"
            }
            
            with open(report_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
                
            # Also store in memory MCP
            self.store_progress_in_mcp(progress_data)
            
            self.logger.info(f"Progress report saved: {report_file}")
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error saving progress report: {e}")
            return None
            
    def store_progress_in_mcp(self, progress_data: Dict):
        """Store progress report in memory MCP"""
        try:
            entity_data = {
                "name": f"progress-backup-{progress_data['timestamp']}",
                "entityType": "progress-backup",
                "observations": [
                    f"Timestamp: {progress_data['timestamp']}",
                    f"Memory Usage: {progress_data['memory_usage']}",
                    f"Cleanup Reason: {progress_data['cleanup_reason']}",
                    f"Full State: {json.dumps(progress_data)}"
                ]
            }
            
            # Note: Would call MCP function here
            # mcp__memory__create_entities(entities=[entity_data])
            
        except Exception as e:
            self.logger.error(f"Error storing progress in MCP: {e}")
            
    def check_memory_thresholds(self) -> Dict[str, bool]:
        """Check if memory thresholds are exceeded"""
        usage = self.get_memory_usage()
        if not usage:
            return {}
            
        thresholds = {
            "ram_warning": usage.ram_percent > self.RAM_WARNING_THRESHOLD,
            "ram_critical": usage.ram_percent > self.RAM_CRITICAL_THRESHOLD,
            "vram_warning": (usage.vram_used_gb / usage.vram_total_gb * 100) > self.VRAM_WARNING_THRESHOLD if usage.vram_total_gb > 0 else False,
            "vram_critical": (usage.vram_used_gb / usage.vram_total_gb * 100) > self.VRAM_CRITICAL_THRESHOLD if usage.vram_total_gb > 0 else False,
            "process_memory_high": usage.process_memory_gb > self.PROCESS_MEMORY_THRESHOLD,
            "virtual_memory_high": usage.virtual_memory_gb > self.VIRTUAL_MEMORY_THRESHOLD
        }
        
        return thresholds
        
    def start_monitoring(self, check_interval: int = 30):
        """Start memory monitoring thread"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    thresholds = self.check_memory_thresholds()
                    
                    if any(thresholds.values()):
                        self.handle_memory_pressure(thresholds)
                        
                    time.sleep(check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(check_interval)
                    
        monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitoring_thread.start()
        
        self.logger.info("Memory monitoring started")
        
    def handle_memory_pressure(self, thresholds: Dict[str, bool]):
        """Handle memory pressure based on thresholds"""
        usage = self.get_memory_usage()
        
        if self.cleanup_in_progress:
            return
            
        critical_conditions = [
            thresholds.get("ram_critical", False),
            thresholds.get("vram_critical", False),
            thresholds.get("process_memory_high", False),
            thresholds.get("virtual_memory_high", False)
        ]
        
        if any(critical_conditions):
            self.logger.warning(f"Critical memory conditions detected: {thresholds}")
            self.emergency_cleanup()
        elif any(thresholds.values()):
            self.logger.info(f"Memory warnings detected: {thresholds}")
            self.cleanup_memory_packages()
            
    def emergency_cleanup(self):
        """Emergency cleanup and graceful shutdown"""
        if self.cleanup_in_progress:
            return
            
        self.cleanup_in_progress = True
        
        try:
            self.logger.critical("EMERGENCY CLEANUP: Critical memory thresholds exceeded")
            
            # Save progress immediately
            self.save_progress_report()
            
            # Clean up memory packages
            self.cleanup_memory_packages()
            
            # Stop monitoring
            self.monitoring_active = False
            
            # Log final state
            usage = self.get_memory_usage()
            if usage:
                self.logger.info(f"Final memory state: RAM {usage.ram_percent:.1f}%, "
                               f"Process {usage.process_memory_gb:.1f}GB, "
                               f"Virtual {usage.virtual_memory_gb:.1f}GB")
            
            # Graceful shutdown signal
            self.logger.critical("Initiating graceful Claude process shutdown in 10 seconds...")
            time.sleep(10)
            
            # Send termination signal to self
            os.kill(os.getpid(), signal.SIGTERM)
            
        except Exception as e:
            self.logger.error(f"Error during emergency cleanup: {e}")
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating cleanup...")
        self.cleanup_on_exit()
        
    def cleanup_on_exit(self):
        """Cleanup on exit"""
        if not self.cleanup_in_progress:
            self.save_progress_report()
            self.cleanup_memory_packages()
            
    def get_status_report(self) -> Dict:
        """Get current status report"""
        usage = self.get_memory_usage()
        thresholds = self.check_memory_thresholds()
        
        return {
            "memory_usage": asdict(usage) if usage else {},
            "thresholds": thresholds,
            "monitoring_active": self.monitoring_active,
            "packages_in_memory": len(self.memory_packages),
            "cleanup_in_progress": self.cleanup_in_progress
        }

# Global memory manager instance
memory_manager = IntelligentMemoryManager()

def start_memory_management():
    """Start the memory management system"""
    memory_manager.start_monitoring()
    return memory_manager

if __name__ == "__main__":
    # Test the memory manager
    manager = start_memory_management()
    
    print("Memory Manager Status:")
    status = manager.get_status_report()
    print(json.dumps(status, indent=2))
    
    # Keep running for testing
    try:
        while True:
            time.sleep(60)
            print("\nCurrent Status:")
            print(json.dumps(manager.get_status_report(), indent=2))
    except KeyboardInterrupt:
        print("\nShutting down...")