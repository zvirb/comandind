#!/bin/bash

# GPU Performance Monitoring Script
echo "=== GPU Performance Monitor ==="
echo "Timestamp: $(date)"
echo ""

# Check GPU utilization
echo "GPU Status:"
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

echo ""

# Check Ollama container stats
echo "Ollama Container Stats:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" ai_workflow_engine-ollama-1 2>/dev/null || echo "Ollama container not found"

echo ""

# Test inference performance
echo "Testing Ollama inference performance..."
start_time=$(date +%s.%N)
response=$(curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"What is AI?","stream":false}' 2>/dev/null)

if [ $? -eq 0 ] && echo "$response" | jq -r '.response' >/dev/null 2>&1; then
    end_time=$(date +%s.%N)
    inference_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "calc error")
    echo "✓ Inference successful"
    echo "Inference time: ${inference_time}s"
    echo "Response preview: $(echo "$response" | jq -r '.response' 2>/dev/null | head -c 100)..."
else
    echo "❌ Inference failed or Ollama not accessible"
fi

echo ""

# Check GPU monitor service if available
echo "GPU Monitor Service Status:"
if curl -s http://localhost:8025/health >/dev/null 2>&1; then
    echo "✓ GPU Monitor service is running"
    echo "📊 Performance Analysis:"
    curl -s http://localhost:8025/metrics/performance 2>/dev/null | jq '.performance_analysis' 2>/dev/null || echo "Performance data parsing failed"
else
    echo "⚠️ GPU Monitor service is not accessible"
fi

echo ""
echo "=== End Performance Report ==="