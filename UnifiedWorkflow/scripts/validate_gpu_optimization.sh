#!/bin/bash

echo "=== COMPREHENSIVE GPU PERFORMANCE VALIDATION ==="
echo "Timestamp: $(date)"
echo ""

echo "1. GPU MEMORY UTILIZATION:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits
echo ""

echo "2. OLLAMA CONTAINER RESOURCE USAGE:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" ai_workflow_engine-ollama-1
echo ""

echo "3. INFERENCE PERFORMANCE TEST:"
echo "Testing single inference..."
time_start=$(date +%s.%N)
response=$(curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"llama3.2:3b","prompt":"Test performance optimization","stream":false}')
time_end=$(date +%s.%N)
inference_time=$(echo "$time_end - $time_start" | bc -l)
echo "Single inference time: ${inference_time}s"
echo "Response length: $(echo "$response" | jq -r '.response' | wc -c) characters"
echo ""

echo "4. CONCURRENT REQUEST CAPABILITY TEST:"
echo "Starting 2 concurrent requests..."
time_start=$(date +%s.%N)
curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"llama3.2:3b","prompt":"Quick test 1","stream":false}' > /tmp/test1.json &
curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"llama3.2:3b","prompt":"Quick test 2","stream":false}' > /tmp/test2.json &
wait
time_end=$(date +%s.%N)
concurrent_time=$(echo "$time_end - $time_start" | bc -l)
echo "Concurrent execution time: ${concurrent_time}s"
echo "Test 1 response length: $(jq -r '.response' /tmp/test1.json | wc -c) characters"
echo "Test 2 response length: $(jq -r '.response' /tmp/test2.json | wc -c) characters"
echo ""

echo "5. OPTIMIZATION SUMMARY:"
gpu_memory_total=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum}')
echo "Total GPU memory in use: ${gpu_memory_total}MB across 3 GPUs"
echo "Ollama system RAM usage: $(docker stats --no-stream --format '{{.MemUsage}}' ai_workflow_engine-ollama-1 | cut -d'/' -f1)"
echo ""

echo "6. CONFIGURATION VERIFICATION:"
echo "Checking optimized Ollama configuration..."
docker logs ai_workflow_engine-ollama-1 2>/dev/null | grep -E "(OLLAMA_NUM_PARALLEL|OLLAMA_FLASH_ATTENTION|OLLAMA_SCHED_SPREAD)" | tail -1
echo ""

echo "=== VALIDATION COMPLETE ==="