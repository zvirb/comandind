# Intelligent Memory Management System

## 🧠 Overview

The Intelligent Memory Management System prevents Claude process lockups by monitoring memory usage and automatically migrating context packages to persistent storage when thresholds are exceeded.

## 🚨 Key Features

### Memory Monitoring
- **RAM Usage**: Monitors system and process memory
- **VRAM Usage**: GPU memory monitoring via nvidia-smi
- **Virtual Memory**: Process virtual memory tracking
- **Automatic Thresholds**: Configurable warning and critical levels

### Memory Package Storage
- **Persistent Storage**: Context packages stored in Memory MCP and local files
- **Automatic Migration**: Existing context packages migrated to persistent storage
- **Token Counting**: Intelligent token estimation and package sizing
- **Priority Management**: Critical packages preserved during cleanup

### Graceful Cleanup
- **Progress Preservation**: Saves orchestration state before cleanup
- **Emergency Shutdown**: Graceful Claude process termination when critical
- **Recovery Support**: Backup files for session recovery
- **Memory MCP Integration**: Seamless integration with vector storage

## 📊 Memory Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| RAM Usage | 70% | 85% | Emergency cleanup |
| VRAM Usage | 80% | 90% | Memory package cleanup |
| Process Memory | 8GB | - | Package migration |
| Virtual Memory | 20GB | - | Immediate cleanup |

## 🚀 Usage

### Start Memory Management
```bash
# Interactive mode
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py

# Daemon mode
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --daemon

# Test system
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --test

# Check status
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --status
```

### Install as System Service
```bash
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --install-service
sudo cp /tmp/claude-memory-management.service /etc/systemd/system/
sudo systemctl enable claude-memory-management.service
sudo systemctl start claude-memory-management.service
```

### Migrate Existing Packages
```bash
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py --migrate
```

## 🏗️ Architecture

### Components
1. **IntelligentMemoryManager**: Core monitoring and cleanup logic
2. **OrchestrationMemoryIntegration**: Orchestration system integration
3. **MemoryMCPAdapter**: Memory MCP and vector store adapter
4. **StartMemoryManagement**: Main service orchestrator

### Storage Locations
- **Memory MCP**: Primary persistent storage for packages
- **Local Backup**: `/home/marku/ai_workflow_engine/.claude/memory_db/`
- **Progress Backups**: `/home/marku/ai_workflow_engine/.claude/progress_backups/`
- **Logs**: `/home/marku/ai_workflow_engine/logs/memory_manager.log`

## 🔄 Integration with Orchestration

### Context Package Management
```python
from orchestration_memory_integration import orchestration_memory

# Store context package
orchestration_memory.store_context_package(
    package_id="agent-context-001",
    content="Agent context data...",
    package_type="context",
    priority="high",
    context_tags=["agent", "context"]
)

# Load context package
content = orchestration_memory.load_context_package("agent-context-001")

# Emergency backup
backup_file = orchestration_memory.emergency_backup_orchestration(state_data)
```

### Memory Status Monitoring
```python
# Get current memory status
status = orchestration_memory.get_memory_status()

# Check if cleanup is needed
if status["thresholds"]["ram_critical"]:
    print("Critical memory condition detected")
```

## 🛡️ Emergency Procedures

### Automatic Emergency Cleanup
When critical thresholds are exceeded:

1. **Progress Backup**: Save current orchestration state
2. **Package Migration**: Move all context packages to persistent storage
3. **Memory Cleanup**: Force garbage collection and RAM cleanup
4. **Graceful Shutdown**: Terminate Claude process after 10-second delay

### Manual Recovery
```bash
# Check recent backups
ls -la /home/marku/ai_workflow_engine/.claude/progress_backups/

# View latest backup
cat /home/marku/ai_workflow_engine/.claude/progress_backups/progress_backup_*.json

# Restart with memory management
python3 /home/marku/ai_workflow_engine/.claude/memory_management/start_memory_management.py
```

## 📈 Monitoring and Logs

### Log Files
- **Memory Manager**: `/home/marku/ai_workflow_engine/logs/memory_manager.log`
- **Orchestration Memory**: `/home/marku/ai_workflow_engine/logs/orchestration_memory.log`
- **System Memory**: Check with `journalctl -u claude-memory-management`

### Status Commands
```bash
# Current memory usage
free -h

# GPU memory usage
nvidia-smi

# Memory manager status
python3 -c "
from start_memory_management import *
manager = IntelligentMemoryManager()
import json
print(json.dumps(manager.get_status_report(), indent=2))
"
```

## 🔧 Configuration

### Memory Thresholds (in intelligent_memory_manager.py)
```python
# Adjust these values as needed
self.RAM_WARNING_THRESHOLD = 70  # %
self.RAM_CRITICAL_THRESHOLD = 85  # %
self.VRAM_WARNING_THRESHOLD = 80  # %
self.VRAM_CRITICAL_THRESHOLD = 90  # %
self.PROCESS_MEMORY_THRESHOLD = 8  # GB
self.VIRTUAL_MEMORY_THRESHOLD = 20  # GB
```

### Monitoring Interval
```python
# Check every 15 seconds for orchestration, 30 seconds for general use
memory_manager.start_monitoring(check_interval=15)
```

## 🎯 Benefits

### Prevents System Lockups
- **OOM Prevention**: Prevents Out of Memory kills
- **Early Warning**: Alerts before critical thresholds
- **Graceful Degradation**: Maintains functionality under memory pressure

### Preserves Work
- **Progress Backup**: Never lose orchestration progress
- **Context Continuity**: Seamless context package recovery
- **Session Recovery**: Resume work after memory cleanup

### Optimizes Performance
- **Memory Efficiency**: Reduces RAM usage during long operations
- **GPU Optimization**: Monitors VRAM for ML workloads
- **Resource Management**: Intelligent cleanup based on priority

## 🚨 Implementation Success

```
✅ Memory package migration to persistent storage
✅ Real-time memory monitoring with GPU support
✅ Emergency cleanup with progress preservation
✅ Graceful Claude process shutdown
✅ Memory MCP integration
✅ Orchestration system integration
✅ Service installation support
✅ Comprehensive logging and monitoring
```

This system solves the 35GB memory leak that caused your system lockup by proactively managing memory usage and providing graceful cleanup mechanisms.