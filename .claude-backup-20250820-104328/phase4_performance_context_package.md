# Performance Context Package - ML Workload Optimization
**Target**: performance-profiler, monitoring-analyst, langgraph-ollama-analyst
**Token Limit**: 3000 tokens | **Package Size**: 2987 tokens

## Performance Status Overview
**Critical Finding**: 3x NVIDIA TITAN X GPUs detected but UNDERUTILIZED
**Ollama Memory Usage**: 7.6GB consumption with optimization opportunities
**ML Service Status**: Configured services ready for GPU acceleration
**Optimization Target**: Enhanced ML performance through GPU utilization

## GPU Hardware Analysis (TITAN X Configuration)

### Hardware Specifications
```bash
# GPU Configuration Detected
GPU_COUNT=3
GPU_MODEL="NVIDIA GeForce GTX TITAN X"
GPU_MEMORY="12GB per GPU" 
TOTAL_GPU_MEMORY="36GB available"
CUDA_VERSION="Compatible with ML frameworks"

# Current Utilization Assessment
GPU_UTILIZATION="<20% average usage"
MEMORY_UTILIZATION="<30% GPU memory usage"
OPTIMIZATION_POTENTIAL="High (3-5x performance improvement possible)"
```

### GPU Utilization Opportunities
**Voice-Interaction-Service**: Audio processing, speech synthesis, voice recognition
**Chat-Service**: Language model inference, reasoning acceleration, context processing
**Sequential-Thinking**: Complex reasoning chains, multi-step inference
**Learning-Systems**: Model fine-tuning, adaptation, knowledge extraction

## Ollama Performance Analysis

### Current Resource Usage
```bash
# Ollama Memory Profile
OLLAMA_MEMORY_USAGE="7.6GB"
OLLAMA_MODEL_LOADING="Dynamic model swapping"
OLLAMA_GPU_UTILIZATION="Minimal GPU usage detected"
OLLAMA_OPTIMIZATION_POTENTIAL="GPU acceleration not fully utilized"

# Performance Metrics
MODEL_INFERENCE_TIME="High (CPU-bound processing)"
CONCURRENT_REQUESTS="Limited by CPU processing"
MEMORY_EFFICIENCY="Suboptimal (potential for GPU memory usage)"
```

### Ollama GPU Acceleration Configuration
```yaml
# Required Ollama GPU configuration
OLLAMA_GPU_ENABLE: true
OLLAMA_GPU_MEMORY_FRACTION: 0.8
OLLAMA_CUDA_VISIBLE_DEVICES: "0,1,2"
OLLAMA_MODEL_PARALLEL: true

# Docker GPU configuration
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0', '1', '2']
              capabilities: [gpu]
```

## ML Service Performance Optimization

### Voice-Interaction-Service Performance
**Current State**: CPU-based audio processing
**Optimization Target**: GPU-accelerated speech synthesis and recognition

**Performance Configuration**:
```python
# GPU acceleration for voice processing
VOICE_CONFIG = {
    "gpu_acceleration": True,
    "cuda_device": "0",  # Dedicated GPU for voice processing
    "batch_processing": True,
    "async_processing": True,
    "memory_optimization": True
}

# Audio processing optimization
AUDIO_PROCESSING = {
    "gpu_spectrogram": True,
    "parallel_synthesis": True,
    "voice_model_gpu": True,
    "real_time_processing": True
}
```

### Chat-Service Performance
**Current State**: CPU-based language processing
**Optimization Target**: GPU-accelerated inference and reasoning

**Performance Configuration**:
```python
# GPU acceleration for chat processing
CHAT_CONFIG = {
    "gpu_acceleration": True,
    "cuda_device": "1",  # Dedicated GPU for chat processing
    "model_parallel": True,
    "context_batching": True,
    "inference_optimization": True
}

# Language model optimization
LLM_OPTIMIZATION = {
    "gpu_inference": True,
    "memory_efficient_attention": True,
    "dynamic_batching": True,
    "kv_cache_optimization": True
}
```

## Database Performance Optimization

### Redis Performance (Connected to ML Services)
**Current Issue**: Connectivity problems affecting caching performance
**Optimization Target**: Enhanced caching for ML inference results

```bash
# Redis performance configuration
redis-cli CONFIG SET maxmemory 8gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"

# ML-specific caching patterns
redis-cli CONFIG SET hash-max-ziplist-entries 512
redis-cli CONFIG SET hash-max-ziplist-value 64
```

### PostgreSQL Optimization for ML Workloads
**Focus**: Efficient storage and retrieval of ML training data and results

```sql
-- Performance optimization for ML data
CREATE INDEX CONCURRENTLY ON ml_conversations USING GIN (conversation_vector);
CREATE INDEX CONCURRENTLY ON voice_samples (audio_hash);
CREATE INDEX CONCURRENTLY ON reasoning_chains (session_id, timestamp);

-- Connection pooling optimization
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
```

### Qdrant Vector Database Performance
**Focus**: High-performance vector similarity search for AI reasoning

```python
# Qdrant performance configuration
QDRANT_CONFIG = {
    "vector_size": 1536,
    "distance": "Cosine",
    "hnsw_config": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
    },
    "optimizers_config": {
        "deleted_threshold": 0.2,
        "vacuum_min_vector_number": 1000
    }
}
```

## Resource Allocation Strategy

### GPU Resource Distribution
```yaml
GPU_ALLOCATION:
  - GPU_0: Voice-interaction-service (dedicated)
  - GPU_1: Chat-service and reasoning (primary)
  - GPU_2: Ollama model inference (shared)

MEMORY_ALLOCATION:
  - Voice Service: 8GB GPU memory
  - Chat Service: 10GB GPU memory  
  - Ollama: 12GB GPU memory
  - System Reserve: 6GB GPU memory
```

### CPU and System Memory Optimization
```yaml
CPU_ALLOCATION:
  - ML Services: 8 cores reserved
  - Database Services: 4 cores allocated
  - Web Services: 2 cores allocated
  - System: 2 cores reserved

MEMORY_ALLOCATION:
  - Ollama: 7.6GB (current) -> 10GB optimized
  - PostgreSQL: 4GB shared buffers
  - Redis: 8GB memory allocation
  - ML Services: 6GB combined allocation
```

## Performance Monitoring Configuration

### ML Service Metrics
```python
# Performance metrics to track
ML_METRICS = {
    "inference_latency": "95th percentile response time",
    "throughput": "requests per second capacity",
    "gpu_utilization": "percentage across all 3 GPUs",
    "memory_efficiency": "GPU memory usage optimization",
    "model_accuracy": "inference quality metrics"
}

# Monitoring endpoints
MONITORING_ENDPOINTS = {
    "/metrics/voice": "Voice service performance data",
    "/metrics/chat": "Chat service performance data", 
    "/metrics/gpu": "GPU utilization and memory stats",
    "/metrics/inference": "Model inference performance"
}
```

### Performance Alerting
```yaml
PERFORMANCE_ALERTS:
  - gpu_utilization_low: "Alert if GPU usage < 60%"
  - inference_latency_high: "Alert if response time > 2 seconds"
  - memory_usage_high: "Alert if GPU memory > 90%"
  - throughput_degradation: "Alert if RPS drops > 20%"
```

## Performance Testing Requirements

### Load Testing Configuration
```bash
# Voice service load testing
wrk -t12 -c400 -d30s --script=voice_load_test.lua \
  http://localhost:8006/synthesize

# Chat service load testing  
wrk -t12 -c400 -d30s --script=chat_load_test.lua \
  http://localhost:8007/chat

# GPU utilization during testing
nvidia-smi -l 1 | tee gpu_utilization_log.txt
```

### Performance Benchmarking
```python
# ML inference benchmarking
BENCHMARK_TESTS = {
    "voice_synthesis": "1000 text samples -> audio generation time",
    "voice_recognition": "1000 audio samples -> text accuracy/speed", 
    "chat_reasoning": "Complex reasoning chains -> response quality/time",
    "context_processing": "Large context -> inference efficiency"
}
```

## Performance Implementation Priority

### Immediate Optimizations (CRITICAL)
1. **GPU Acceleration**: Enable GPU support for Ollama and ML services
2. **Resource Allocation**: Distribute GPU resources across services
3. **Memory Optimization**: Configure optimal memory usage patterns

### Deployment Optimizations (HIGH)
1. **Container GPU Access**: Configure Docker GPU device access
2. **Service Configuration**: Enable GPU acceleration in service configs
3. **Performance Monitoring**: Implement comprehensive performance tracking

### Validation Requirements (MEDIUM)
1. **Load Testing**: Comprehensive performance testing under load
2. **Resource Monitoring**: Real-time GPU and memory utilization tracking
3. **Benchmark Comparison**: Before/after performance improvement metrics

**CRITICAL**: Execute performance optimization in parallel with deployment
**EVIDENCE**: Provide GPU utilization metrics and performance benchmarks
**TARGET**: Achieve 3-5x performance improvement through GPU acceleration