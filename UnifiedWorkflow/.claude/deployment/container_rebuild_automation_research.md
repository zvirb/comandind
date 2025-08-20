# Container Rebuild Automation Research - Phase 3 Deployment Orchestrator

## Executive Summary

This comprehensive research documents the container rebuild automation capabilities for deploying SSL fixes to all cognitive services. Based on successful worker service recovery patterns, we have identified systematic deployment procedures for parallel container rebuilds with evidence-based validation.

## Current Service Status Analysis

### Service Health States
```yaml
cognitive_services_status:
  hybrid-memory-service:
    status: "unhealthy"
    uptime: "6 hours"
    issue: "SSL parameter incompatibility in DATABASE_URL"
    fix_required: true
    
  reasoning-service:
    status: "unhealthy"  
    uptime: "16 hours"
    issue: "SSL parameter incompatibility in DATABASE_URL"
    fix_required: true
    
  learning-service:
    status: "restarting"
    issue: "Missing neo4j_auth environment variable"
    fix_required: true
    additional_fix: "Add LEARNING_NEO4J_AUTH environment variable"
    
  coordination-service:
    status: "unhealthy"
    uptime: "6 hours"
    issue: "SSL parameter incompatibility in DATABASE_URL"
    fix_required: true
    
  infrastructure-recovery-service:
    status: "healthy"
    uptime: "16 hours"
    issue: none
    monitoring_capability: active
```

## Container Rebuild Automation Framework

### 1. Docker-Compose Rebuild Commands

#### Standard Rebuild Operations
```bash
# Single service rebuild
docker compose build <service-name>
docker compose up -d <service-name>

# Parallel service rebuild
docker compose build --parallel hybrid-memory-service reasoning-service learning-service coordination-service
docker compose up -d hybrid-memory-service reasoning-service learning-service coordination-service

# Force rebuild with no cache
docker compose build --no-cache <service-name>

# Rebuild and restart in one command
docker compose up -d --build <service-name>
```

#### Automated Rebuild Script Pattern
```python
def rebuild_cognitive_services():
    """Rebuild all cognitive services with SSL fixes"""
    services = [
        'hybrid-memory-service',
        'reasoning-service', 
        'learning-service',
        'coordination-service'
    ]
    
    # Stop services first for clean state
    for service in services:
        subprocess.run(f"docker compose stop {service}", shell=True)
    
    # Rebuild containers in parallel
    subprocess.run(f"docker compose build --parallel {' '.join(services)}", shell=True)
    
    # Start services with new configuration
    for service in services:
        subprocess.run(f"docker compose up -d {service}", shell=True)
        time.sleep(5)  # Stagger startup to avoid resource contention
```

### 2. Environment Variable Deployment

#### SSL Fix Pattern (From Worker Service Success)
```yaml
# WORKING PATTERN (Worker Service)
environment:
  - POSTGRES_HOST=pgbouncer
  - POSTGRES_USER=app_user
  - POSTGRES_PORT=6432
  - POSTGRES_DB=ai_workflow_db
  # No DATABASE_URL with SSL parameters

# BROKEN PATTERN (Cognitive Services)
environment:
  - DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db
  # Missing SSL configuration or incompatible SSL parameters
```

#### Required Environment Variable Updates
```yaml
learning-service:
  environment:
    - LEARNING_NEO4J_AUTH=neo4j/password  # CRITICAL: Add this
    - DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db
    
hybrid-memory-service:
  environment:
    # Remove +asyncpg suffix causing SSL issues
    - DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db
    
reasoning-service:
  environment:
    - DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db
    
coordination-service:
  environment:
    - DATABASE_URL=postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db
```

### 3. Infrastructure Recovery Service Integration

#### Automated Recovery Capabilities
```python
class AutomatedRecoverySystem:
    recovery_actions = {
        RecoveryActionType.RESTART_CONTAINER: restart_container,
        RecoveryActionType.GRACEFUL_RESTART: graceful_restart,
        RecoveryActionType.REBUILD_INDEX: rebuild_index,
        RecoveryActionType.HEALTH_CHECK_RESET: health_check_reset,
        RecoveryActionType.EMERGENCY_ROLLBACK: emergency_rollback
    }
    
    async def restart_container(self, service: str):
        """Restart a Docker container with health monitoring"""
        container = self.docker_client.containers.get(service)
        container.restart(timeout=30)
        await self.wait_for_container_health(container, timeout=120)
        
    async def graceful_restart(self, service: str):
        """Graceful restart with SIGTERM and health check"""
        container = self.docker_client.containers.get(service)
        container.kill(signal="SIGTERM")
        await asyncio.sleep(10)
        container.start()
        await self.wait_for_container_health(container, timeout=120)
```

### 4. Deployment Automation Procedures

#### Phase 1: Pre-Deployment Validation
```bash
# Capture current state for rollback
docker ps --format "table {{.Names}}\t{{.Status}}" > pre_deployment_state.txt
docker compose ps --services --filter "status=running" > running_services.txt

# Backup current environment configurations
for service in hybrid-memory-service reasoning-service learning-service coordination-service; do
    docker inspect $service > backup_${service}_config.json
done
```

#### Phase 2: Parallel Container Rebuild
```python
async def parallel_rebuild_deployment():
    """Execute parallel container rebuilds with monitoring"""
    
    services = {
        'hybrid-memory-service': {'ssl_fix': True},
        'reasoning-service': {'ssl_fix': True},
        'learning-service': {'ssl_fix': True, 'neo4j_auth': 'neo4j/password'},
        'coordination-service': {'ssl_fix': True}
    }
    
    # Stop all services simultaneously
    stop_tasks = []
    for service in services:
        stop_tasks.append(stop_service(service))
    await asyncio.gather(*stop_tasks)
    
    # Rebuild all containers in parallel
    rebuild_command = f"docker compose build --parallel {' '.join(services.keys())}"
    await run_command(rebuild_command)
    
    # Start services with staggered timing
    for service, config in services.items():
        await start_service(service, config)
        await asyncio.sleep(3)  # Prevent resource contention
```

#### Phase 3: Health Validation Loop
```python
async def validate_deployment():
    """Validate container health after deployment"""
    
    validation_results = {}
    max_retries = 30  # 5 minutes with 10 second intervals
    
    for retry in range(max_retries):
        all_healthy = True
        
        for service in ['hybrid-memory-service', 'reasoning-service', 
                       'learning-service', 'coordination-service']:
            health = await check_service_health(service)
            validation_results[service] = health
            
            if health != 'healthy':
                all_healthy = False
                
        if all_healthy:
            return True, validation_results
            
        await asyncio.sleep(10)
        
    return False, validation_results
```

### 5. Evidence Collection Framework

#### Container Health Evidence
```bash
# Real-time health monitoring
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "memory|reasoning|learning|coordination"'

# Health check logs
for service in hybrid-memory-service reasoning-service learning-service coordination-service; do
    echo "=== $service health ===" 
    docker inspect $service --format '{{.State.Health.Status}}'
    docker logs $service --tail 10 2>&1 | grep -E "health|ready|started"
done
```

#### SSL Fix Validation Evidence
```python
def collect_ssl_evidence():
    """Collect concrete evidence of SSL fix deployment"""
    
    evidence = {
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }
    
    for service in cognitive_services:
        # Check container is running
        container_status = subprocess.run(
            f"docker ps --filter name={service} --format '{{{{.Status}}}}'",
            shell=True, capture_output=True
        ).stdout.decode().strip()
        
        # Check for SSL errors in logs
        ssl_errors = subprocess.run(
            f"docker logs {service} --tail 100 2>&1 | grep -c 'sslmode'",
            shell=True, capture_output=True
        ).stdout.decode().strip()
        
        # Test service endpoint
        try:
            response = requests.get(f"http://{service}:{port}/health", timeout=5)
            endpoint_status = response.status_code
        except:
            endpoint_status = 'unreachable'
            
        evidence['services'][service] = {
            'container_status': container_status,
            'ssl_errors': int(ssl_errors),
            'endpoint_status': endpoint_status,
            'health': 'healthy' if 'healthy' in container_status else 'unhealthy'
        }
        
    return evidence
```

### 6. Rollback Procedures

#### Automated Rollback Triggers
```python
async def deployment_with_rollback():
    """Deploy with automatic rollback on failure"""
    
    # Create backup point
    backup_id = create_deployment_backup()
    
    try:
        # Execute deployment
        await parallel_rebuild_deployment()
        
        # Validate deployment
        success, results = await validate_deployment()
        
        if not success:
            logger.error("Deployment validation failed")
            await rollback_deployment(backup_id)
            return False
            
        # Verify no SSL errors
        if check_ssl_errors():
            logger.error("SSL errors detected after deployment")
            await rollback_deployment(backup_id)
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        await rollback_deployment(backup_id)
        return False
```

### 7. Deployment Coordination Requirements

#### Service Dependencies
```yaml
deployment_sequence:
  phase_1:  # Infrastructure
    - postgres  # Database must be healthy first
    - redis     # Cache service
    - qdrant    # Vector database
    
  phase_2:  # Core Services  
    - coordination-service  # Central orchestration
    
  phase_3:  # Cognitive Services (Parallel)
    - hybrid-memory-service
    - reasoning-service
    - learning-service
    
  phase_4:  # Recovery Monitoring
    - infrastructure-recovery-service  # Monitor deployment
```

#### Resource Management
```python
def calculate_deployment_resources():
    """Calculate resource requirements for parallel rebuilds"""
    
    # Each service rebuild requires approximately:
    # - 2GB RAM for build process
    # - 1 CPU core
    # - 5GB disk space for layers
    
    available_memory = get_available_memory()
    available_cpu = get_cpu_count()
    
    # Maximum parallel builds based on resources
    max_parallel = min(
        available_memory // 2048,  # 2GB per build
        available_cpu - 1,  # Leave 1 core for system
        4  # Maximum 4 parallel builds
    )
    
    return max_parallel
```

### 8. Monitoring and Alerting

#### Deployment Monitoring Dashboard
```python
async def deployment_monitor():
    """Real-time deployment monitoring"""
    
    while deployment_in_progress:
        clear_screen()
        print("=" * 60)
        print("COGNITIVE SERVICES DEPLOYMENT MONITOR")
        print("=" * 60)
        
        for service in cognitive_services:
            status = get_container_status(service)
            health = get_health_status(service)
            uptime = get_uptime(service)
            errors = check_recent_errors(service)
            
            print(f"\n{service}:")
            print(f"  Status: {status}")
            print(f"  Health: {health}")
            print(f"  Uptime: {uptime}")
            print(f"  Recent Errors: {errors}")
            
        print("\n" + "=" * 60)
        await asyncio.sleep(5)
```

## Deployment Execution Plan

### Quick Deployment Commands
```bash
# 1. Stop all cognitive services
docker compose stop hybrid-memory-service reasoning-service learning-service coordination-service

# 2. Update docker-compose.yml with environment fixes
vim docker-compose.yml  # Add LEARNING_NEO4J_AUTH and fix DATABASE_URLs

# 3. Rebuild all services in parallel
docker compose build --parallel hybrid-memory-service reasoning-service learning-service coordination-service

# 4. Start services with monitoring
docker compose up -d hybrid-memory-service reasoning-service learning-service coordination-service

# 5. Monitor health status
watch -n 2 'docker ps | grep -E "memory|reasoning|learning|coordination"'
```

### Python Automation Script
```python
#!/usr/bin/env python3
"""Automated Cognitive Services Deployment"""

import subprocess
import time
import asyncio

async def deploy_cognitive_services():
    """Main deployment function"""
    
    print("🚀 Starting Cognitive Services SSL Fix Deployment")
    
    # Phase 1: Stop services
    print("📦 Stopping services...")
    subprocess.run("docker compose stop hybrid-memory-service reasoning-service learning-service coordination-service", shell=True)
    
    # Phase 2: Rebuild containers
    print("🔨 Rebuilding containers...")
    subprocess.run("docker compose build --parallel hybrid-memory-service reasoning-service learning-service coordination-service", shell=True)
    
    # Phase 3: Start services
    print("🎯 Starting services...")
    subprocess.run("docker compose up -d hybrid-memory-service reasoning-service learning-service coordination-service", shell=True)
    
    # Phase 4: Validate
    print("✅ Validating deployment...")
    time.sleep(30)  # Wait for services to initialize
    
    result = subprocess.run("docker ps | grep -E 'memory|reasoning|learning|coordination'", shell=True, capture_output=True)
    print(result.stdout.decode())
    
    print("🎉 Deployment complete!")

if __name__ == "__main__":
    asyncio.run(deploy_cognitive_services())
```

## Risk Assessment and Mitigation

### Deployment Risks
1. **Service Dependency Failures**: Services may fail to start due to missing dependencies
   - Mitigation: Implement health check loops with dependency validation

2. **Resource Contention**: Parallel rebuilds may exhaust system resources
   - Mitigation: Implement resource monitoring and throttling

3. **Configuration Drift**: Environment variables may not propagate correctly
   - Mitigation: Validate configuration after each deployment

4. **Cascading Failures**: One service failure may impact others
   - Mitigation: Implement circuit breakers and isolation

### Rollback Triggers
- Any service fails to become healthy within 5 minutes
- SSL errors detected in logs after deployment
- Service endpoints return non-200 status codes
- Memory or CPU usage exceeds 90% during deployment

## Success Metrics

### Deployment Success Indicators
✅ All 4 cognitive services report "healthy" status
✅ No SSL-related errors in service logs
✅ All service endpoints respond with 200 OK
✅ Learning service successfully connects to Neo4j
✅ Container uptime exceeds 5 minutes without restarts
✅ Infrastructure recovery service reports all services green
✅ No rollback triggers activated

### Evidence Collection Requirements
- Pre-deployment state captured for comparison
- Health check logs from all services
- SSL error scan results (must be zero)
- Endpoint connectivity tests
- Container resource utilization metrics
- Deployment duration and timing logs

## Conclusion

This comprehensive research provides the foundation for systematic container rebuild automation with evidence-based validation. The deployment procedures follow the successful worker service recovery pattern while addressing specific requirements for each cognitive service. The parallel deployment strategy with proper resource management and rollback capabilities ensures safe and efficient SSL fix propagation across all services.