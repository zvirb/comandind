#!/usr/bin/env python3
"""
Start Memory Management System
Initializes and starts the intelligent memory management system for Claude
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Add paths
sys.path.append('/home/marku/ai_workflow_engine/.claude/memory_management')

from intelligent_memory_manager import IntelligentMemoryManager
from orchestration_memory_integration import OrchestrationMemoryIntegration, initialize_orchestration_memory
from memory_mcp_adapter import MemoryMCPAdapter

def setup_memory_management_logging():
    """Setup comprehensive logging for memory management"""
    log_dir = "/home/marku/ai_workflow_engine/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"{log_dir}/memory_management.log"),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("MemoryManagementStartup")
    return logger

def check_system_requirements():
    """Check system requirements for memory management"""
    checks = {
        "python_version": sys.version_info >= (3, 8),
        "psutil_available": False,
        "memory_dir_exists": os.path.exists("/home/marku/ai_workflow_engine/.claude/memory_management"),
        "logs_dir_writable": os.access("/home/marku/ai_workflow_engine/logs", os.W_OK),
    }
    
    try:
        import psutil
        checks["psutil_available"] = True
    except ImportError:
        pass
        
    return checks

def install_memory_management_service():
    """Install memory management as a system service"""
    try:
        service_content = f"""[Unit]
Description=Claude AI Workflow Engine Memory Management
After=network.target

[Service]
Type=simple
User=marku
WorkingDirectory=/home/marku/ai_workflow_engine
ExecStart=/usr/bin/python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --daemon
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/marku/ai_workflow_engine/app

[Install]
WantedBy=multi-user.target
"""
        
        service_file = "/tmp/claude-memory-management.service"
        with open(service_file, 'w') as f:
            f.write(service_content)
            
        print(f"Service file created: {service_file}")
        print("To install as system service, run:")
        print(f"sudo cp {service_file} /etc/systemd/system/")
        print("sudo systemctl daemon-reload")
        print("sudo systemctl enable claude-memory-management.service")
        print("sudo systemctl start claude-memory-management.service")
        
    except Exception as e:
        print(f"Error creating service file: {e}")

def main():
    """Main function to start memory management"""
    parser = argparse.ArgumentParser(description="Claude Memory Management System")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--install-service", action="store_true", help="Install as system service")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--migrate", action="store_true", help="Migrate existing packages")
    args = parser.parse_args()
    
    logger = setup_memory_management_logging()
    
    if args.install_service:
        install_memory_management_service()
        return
    
    # Check system requirements
    requirements = check_system_requirements()
    missing_requirements = [k for k, v in requirements.items() if not v]
    
    if missing_requirements:
        logger.error(f"Missing requirements: {missing_requirements}")
        
        if "psutil_available" in missing_requirements:
            print("Install psutil: pip install psutil")
            
        if missing_requirements != ["psutil_available"]:
            return 1
    
    try:
        # Initialize memory management components
        logger.info("Initializing Intelligent Memory Manager...")
        memory_manager = IntelligentMemoryManager()
        
        logger.info("Initializing Memory MCP Adapter...")
        mcp_adapter = MemoryMCPAdapter()
        
        logger.info("Initializing Orchestration Memory Integration...")
        orchestration_integration = initialize_orchestration_memory()
        
        if args.status:
            # Show status
            status = memory_manager.get_status_report()
            print("Memory Management Status:")
            print(json.dumps(status, indent=2))
            return 0
            
        if args.test:
            # Run tests
            logger.info("Running memory management tests...")
            
            # Test memory monitoring
            usage = memory_manager.get_memory_usage()
            if usage:
                logger.info(f"Memory test passed: {usage.ram_percent:.1f}% RAM usage")
            else:
                logger.error("Memory monitoring test failed")
                
            # Test package storage
            from memory_mcp_adapter import store_in_mcp
            test_success = store_in_mcp(
                "test-package", 
                "Test content", 
                "test", 
                "low", 
                ["test"]
            )
            
            logger.info(f"Package storage test: {'Passed' if test_success else 'Failed'}")
            return 0
            
        if args.migrate:
            # Migrate existing packages
            logger.info("Migrating existing context packages...")
            if orchestration_integration:
                orchestration_integration.migrate_existing_packages()
                logger.info("Migration completed")
            return 0
        
        # Start memory management system
        logger.info("Starting memory management system...")
        
        # Start monitoring
        memory_manager.start_monitoring(check_interval=30)
        
        # Log startup success
        logger.info("Memory management system started successfully")
        logger.info(f"Monitoring thresholds: RAM {memory_manager.RAM_CRITICAL_THRESHOLD}%, "
                   f"VRAM {memory_manager.VRAM_CRITICAL_THRESHOLD}%, "
                   f"Process {memory_manager.PROCESS_MEMORY_THRESHOLD}GB")
        
        if args.daemon:
            # Run as daemon
            import time
            logger.info("Running in daemon mode...")
            
            try:
                while True:
                    time.sleep(60)
                    status = memory_manager.get_status_report()
                    
                    if status.get("cleanup_in_progress"):
                        logger.warning("Cleanup in progress...")
                        
                    # Log status every 10 minutes
                    if datetime.now().minute % 10 == 0:
                        usage = status.get("memory_usage", {})
                        logger.info(f"Status: RAM {usage.get('ram_percent', 0):.1f}%, "
                                  f"Process {usage.get('process_memory_gb', 0):.1f}GB")
                        
            except KeyboardInterrupt:
                logger.info("Shutting down memory management system...")
                
        else:
            # Interactive mode
            print("\nMemory Management System Active")
            print("Press Enter to check status, 'q' to quit")
            
            while True:
                try:
                    user_input = input("> ").strip().lower()
                    
                    if user_input == 'q':
                        break
                    elif user_input == '':
                        status = memory_manager.get_status_report()
                        print(json.dumps(status, indent=2))
                    elif user_input == 'cleanup':
                        memory_manager.cleanup_memory_packages()
                        print("Memory cleanup completed")
                    elif user_input == 'help':
                        print("Commands: <enter>=status, cleanup=clean memory, q=quit")
                        
                except KeyboardInterrupt:
                    break
            
            logger.info("Memory management system stopped")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error starting memory management: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)