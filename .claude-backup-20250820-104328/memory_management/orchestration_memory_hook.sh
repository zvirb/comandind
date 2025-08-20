#!/bin/bash
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
