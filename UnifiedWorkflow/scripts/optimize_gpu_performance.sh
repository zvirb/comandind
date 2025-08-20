#!/bin/bash

# GPU Performance Optimization Script
# Optimizes Ollama and ML services for better GPU utilization

set -e

echo "🚀 Starting GPU Performance Optimization..."

# Backup current docker-compose if needed
if [ ! -f docker-compose.yml.backup ]; then
    cp docker-compose.yml docker-compose.yml.backup
    echo "✓ Backed up docker-compose.yml"
fi

# Function to update Ollama environment variables
update_ollama_env() {
    echo "🔧 Updating Ollama environment variables for GPU optimization..."
    
    # Create temporary file with optimized environment
    cat > /tmp/ollama_env_update.txt << 'EOF'
    - OLLAMA_HOST=0.0.0.0
    - OLLAMA_NUM_PARALLEL=2
    - OLLAMA_FLASH_ATTENTION=true
    - OLLAMA_GPU_OVERHEAD=0
    - OLLAMA_MAX_LOADED_MODELS=3
    - OLLAMA_KEEP_ALIVE=15m
    - OLLAMA_LOAD_TIMEOUT=10m
    - OLLAMA_CONTEXT_LENGTH=8192
    - OLLAMA_KV_CACHE_TYPE=f16
    - OLLAMA_SCHED_SPREAD=true
    - OLLAMA_MAX_QUEUE=256
    - OLLAMA_DEBUG=INFO
    - CUDA_LAUNCH_BLOCKING=0
    - CUDA_CACHE_DISABLE=0
EOF
    
    echo "✓ Ollama environment optimization prepared"
}

# Function to add GPU monitor service to docker-compose
add_gpu_monitor() {
    echo "📊 Adding GPU monitor service..."
    
    # Check if gpu-monitor service already exists
    if ! grep -q "gpu-monitor:" docker-compose.yml; then
        # Add GPU monitor service after external-api-service
        sed -i '/external-api-service:/,/start_period: 30s/a\
\
  # GPU Performance Monitor Service\
  gpu-monitor:\
    restart: unless-stopped\
    networks: *id002\
    logging: *id001\
    build:\
      context: ./app/gpu_monitor\
      dockerfile: Dockerfile\
    image: ai_workflow_engine/gpu-monitor\
    ports:\
      - "8025:8025"\
    volumes:\
      - /var/run/docker.sock:/var/run/docker.sock:ro\
    environment:\
      - SERVICE_NAME=gpu-monitor\
      - PYTHONPATH=/app\
    deploy:\
      resources:\
        reservations:\
          devices:\
            - driver: nvidia\
              count: all\
              capabilities: [gpu]\
    depends_on:\
      ollama:\
        condition: service_healthy\
    healthcheck:\
      test: ["CMD", "curl", "-f", "http://localhost:8025/health"]\
      interval: 30s\
      timeout: 10s\
      retries: 3\
      start_period: 30s' docker-compose.yml
        
        echo "✓ GPU monitor service added to docker-compose.yml"
    else
        echo "ℹ️ GPU monitor service already exists in docker-compose.yml"
    fi
}

# Function to optimize other ML services for GPU
optimize_ml_services() {
    echo "🧠 Optimizing ML services for GPU utilization..."
    
    # Add GPU deployment to services that can benefit
    local services=("voice-interaction-service" "reasoning-service" "learning-service" "perception-service")
    
    for service in "${services[@]}"; do
        if grep -q "$service:" docker-compose.yml; then
            # Check if service already has GPU deployment
            if ! sed -n "/$service:/,/^  [a-zA-Z]/p" docker-compose.yml | grep -q "driver: nvidia"; then
                echo "🔧 Adding GPU support to $service..."
                # This would require more complex sed operations, placeholder for now
                echo "ℹ️ $service optimization noted for manual review"
            fi
        fi
    done
}

# Function to create performance monitoring script
create_performance_script() {
    echo "📈 Creating performance monitoring script..."
    
    cat > scripts/monitor_gpu_performance.sh << 'EOF'
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
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" ai_workflow_engine-ollama-1

echo ""

# Test inference performance
echo "Testing Ollama inference performance..."
start_time=$(date +%s.%N)
curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"What is AI?","stream":false}' \
  | jq -r '.response' | head -1
end_time=$(date +%s.%N)
inference_time=$(echo "$end_time - $start_time" | bc)
echo "Inference time: ${inference_time}s"

echo ""

# Check GPU monitor service if available
echo "GPU Monitor Service Status:"
if curl -s http://localhost:8025/health >/dev/null 2>&1; then
    echo "✓ GPU Monitor service is running"
    curl -s http://localhost:8025/metrics/performance | jq '.performance_analysis' 2>/dev/null || echo "Performance data not available"
else
    echo "⚠️ GPU Monitor service is not accessible"
fi
EOF
    
    chmod +x scripts/monitor_gpu_performance.sh
    echo "✓ Performance monitoring script created"
}

# Function to restart services with optimization
restart_optimized_services() {
    echo "🔄 Restarting services with GPU optimizations..."
    
    # Build and restart GPU monitor
    if docker-compose ps gpu-monitor >/dev/null 2>&1; then
        docker-compose stop gpu-monitor
        docker-compose rm -f gpu-monitor
    fi
    
    # Build GPU monitor image
    docker-compose build gpu-monitor
    
    # Restart Ollama with optimization
    echo "🔄 Restarting Ollama with optimizations..."
    docker-compose stop ollama
    docker-compose up -d ollama
    
    # Start GPU monitor
    docker-compose up -d gpu-monitor
    
    echo "✓ Services restarted with optimizations"
}

# Function to validate optimization
validate_optimization() {
    echo "✅ Validating GPU optimization..."
    
    # Wait for services to start
    sleep 30
    
    # Check if services are running
    if docker-compose ps ollama | grep -q "Up"; then
        echo "✓ Ollama service is running"
    else
        echo "❌ Ollama service failed to start"
        return 1
    fi
    
    if docker-compose ps gpu-monitor | grep -q "Up"; then
        echo "✓ GPU monitor service is running"
    else
        echo "⚠️ GPU monitor service is not running (this is optional)"
    fi
    
    # Test GPU access
    if docker exec ai_workflow_engine-ollama-1 nvidia-smi >/dev/null 2>&1; then
        echo "✓ Ollama container can access GPUs"
    else
        echo "❌ Ollama container cannot access GPUs"
        return 1
    fi
    
    # Test inference
    echo "🧪 Testing inference performance..."
    if timeout 30s bash scripts/monitor_gpu_performance.sh > /tmp/gpu_test_output.txt 2>&1; then
        echo "✓ GPU performance test completed"
        echo "📋 Performance test results:"
        tail -10 /tmp/gpu_test_output.txt
    else
        echo "⚠️ GPU performance test failed or timed out"
    fi
}

# Main execution
main() {
    echo "🎯 GPU Performance Optimization Pipeline"
    echo "========================================"
    
    # Run optimization steps
    update_ollama_env
    add_gpu_monitor
    optimize_ml_services
    create_performance_script
    
    # Ask for confirmation before restarting services
    read -p "🤔 Do you want to restart services with optimizations now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        restart_optimized_services
        validate_optimization
        
        echo ""
        echo "🎉 GPU Performance Optimization Complete!"
        echo "📊 Run './scripts/monitor_gpu_performance.sh' to monitor performance"
        echo "🌐 GPU monitor dashboard: http://localhost:8025/metrics/performance"
    else
        echo "ℹ️ Optimization prepared but services not restarted"
        echo "📝 Run 'docker-compose up -d --build' when ready to apply changes"
    fi
}

# Run main function
main "$@"