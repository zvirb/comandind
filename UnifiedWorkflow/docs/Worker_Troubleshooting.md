# Worker Container Troubleshooting Guide

This guide helps diagnose and fix issues with the `ai_workflow_engine-worker-1` container that keeps restarting.

## Quick Diagnosis

Run the diagnostic script to get a comprehensive analysis:

```bash
./scripts/diagnose_worker.sh
```

## Common Restart Causes

### 1. **Memory Issues**
- **Symptom**: Worker container keeps restarting with exit code 137 (SIGKILL)
- **Cause**: System running out of memory, Docker kills the container
- **Solution**: 
  ```bash
  # Check memory usage
  free -h
  # Monitor during worker operation
  docker stats ai_workflow_engine-worker-1
  # Increase server memory or reduce concurrency
  ```

### 2. **Dependency Connection Failures**
- **Symptom**: Worker fails to start, logs show connection errors
- **Cause**: Cannot connect to Redis, PostgreSQL, Qdrant, or Ollama
- **Solution**:
  ```bash
  # Check dependency health
  docker compose ps
  # Restart dependencies
  docker compose restart redis postgres qdrant ollama
  ```

### 3. **Secret/Environment Issues**
- **Symptom**: Worker fails with authentication or configuration errors
- **Cause**: Missing or corrupted secrets, environment variables
- **Solution**:
  ```bash
  # Check secrets exist
  ls -la secrets/
  # Regenerate if missing
  ./scripts/_setup_secrets_and_certs.sh
  ```

### 4. **GPU Resource Issues** (if GPU enabled)
- **Symptom**: Worker crashes when trying to use GPU
- **Cause**: GPU memory exhaustion, CUDA driver issues
- **Solution**:
  ```bash
  # Check GPU status
  nvidia-smi
  # Monitor GPU memory
  watch nvidia-smi
  ```

### 5. **Disk Space Issues**
- **Symptom**: Worker fails to start or crashes during operation
- **Cause**: Insufficient disk space for logs, models, or temp files
- **Solution**:
  ```bash
  # Check disk usage
  df -h
  # Clean up Docker resources
  docker system prune -f
  ```

### 6. **Celery Configuration Issues**
- **Symptom**: Worker starts but fails healthchecks
- **Cause**: Celery cannot connect to Redis broker
- **Solution**:
  ```bash
  # Test Redis connection manually
  docker exec ai_workflow_engine-worker-1 redis-cli -h redis -p 6379 -a "$(cat secrets/redis_password.txt)" ping
  ```

### 7. **Python/Application Errors**
- **Symptom**: Worker crashes with Python exceptions
- **Cause**: Application code errors, missing dependencies
- **Solution**:
  ```bash
  # Check detailed logs
  docker logs ai_workflow_engine-worker-1 --tail 100
  # Rebuild with latest code
  docker compose build worker
  ```

## Server vs Local Differences

### Resource Constraints
- **Server**: Often has limited memory, CPU, or disk
- **Local**: Usually has more resources available
- **Check**: Monitor resource usage during operation

### Network Configuration
- **Server**: May have firewall, proxy, or DNS issues
- **Local**: Direct network access
- **Check**: Test connectivity between containers

### GPU Availability
- **Server**: May have different GPU drivers or no GPU
- **Local**: GPU configuration might differ
- **Check**: Verify GPU compatibility and drivers

### File Permissions
- **Server**: Different user/group IDs, security policies
- **Local**: More permissive file system
- **Check**: Ensure correct file permissions

## Debugging Steps

### 1. **Check Container Status**
```bash
# Current status
docker ps -a | grep worker

# Restart count
docker inspect ai_workflow_engine-worker-1 --format='{{.RestartCount}}'

# Exit code
docker inspect ai_workflow_engine-worker-1 --format='{{.State.ExitCode}}'
```

### 2. **Monitor Logs in Real-Time**
```bash
# Follow logs
docker logs -f ai_workflow_engine-worker-1

# Check specific timeframe
docker logs ai_workflow_engine-worker-1 --since="10m"
```

### 3. **Test Dependencies**
```bash
# Check if all dependencies are healthy
docker compose ps

# Test specific connections
docker exec ai_workflow_engine-worker-1 python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"
```

### 4. **Resource Monitoring**
```bash
# System resources
htop
free -h
df -h

# Docker resources
docker stats

# GPU (if applicable)
nvidia-smi
```

### 5. **Manual Container Testing**
```bash
# Run worker interactively
docker run -it --rm \
  --network ai_workflow_engine_ai_workflow_engine_net \
  -v ai_workflow_engine_certs:/tmp/certs-volume:ro \
  -e POSTGRES_PASSWORD="$(cat secrets/postgres_password.txt)" \
  -e REDIS_PASSWORD="$(cat secrets/redis_password.txt)" \
  ai_workflow_engine/worker /bin/bash

# Test Celery manually
PYTHONPATH=/app celery -A worker.celery_app worker --loglevel=debug
```

## Prevention Strategies

### 1. **Resource Management**
- Monitor memory usage regularly
- Set appropriate resource limits
- Use `--memory` and `--cpus` Docker flags if needed

### 2. **Health Monitoring**
- Check healthcheck intervals and timeouts
- Monitor dependency health
- Set up alerts for container restarts

### 3. **Configuration Management**
- Keep secrets backed up
- Use environment variables consistently
- Document server-specific configurations

### 4. **Logging Strategy**
- Increase log levels temporarily for debugging
- Use structured logging
- Monitor log file sizes

## Emergency Recovery

If the worker keeps failing:

1. **Immediate Steps**:
   ```bash
   # Stop problematic container
   docker stop ai_workflow_engine-worker-1
   
   # Check what's consuming resources
   docker system df
   docker system prune -f
   
   # Restart with clean state
   docker compose up -d worker
   ```

2. **Escalation**:
   ```bash
   # Full service restart
   docker compose restart
   
   # If still failing, soft reset
   ./run.sh --soft-reset
   ```

3. **Last Resort**:
   ```bash
   # Full reset (loses all data)
   ./run.sh --reset
   ```

## Server-Specific Considerations

### Production Server Hardening
- Check if SELinux/AppArmor is causing issues
- Verify firewall rules allow container communication
- Ensure proper user permissions

### Resource Allocation
- Consider reducing worker concurrency on limited servers
- Implement resource quotas
- Monitor system load

### Monitoring Setup
- Use log aggregation tools
- Set up container restart alerts
- Monitor system metrics

## Getting Help

When seeking help, provide:

1. **Diagnostic Output**:
   ```bash
   ./scripts/diagnose_worker.sh > worker_diagnosis.log 2>&1
   ```

2. **System Information**:
   ```bash
   # System specs
   uname -a
   free -h
   df -h
   
   # Docker info
   docker version
   docker info
   ```

3. **Recent Logs**:
   ```bash
   docker logs ai_workflow_engine-worker-1 --since="1h" > worker_logs.txt
   ```

4. **Service Status**:
   ```bash
   docker compose ps > service_status.txt
   ```

This comprehensive information helps identify patterns and root causes specific to your server environment.