#!/usr/bin/env python3
"""
Automated Recovery System for AI Workflow Engine
Prevents catastrophic failures like the 20+ hour outage incident
"""

import subprocess
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from pathlib import Path

# Ensure log directory exists
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'recovery.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('recovery-system')

class ServiceRecoveryManager:
    """Manages automatic recovery of failed services"""
    
    CRITICAL_SERVICES = {
        'webui': {
            'container_pattern': 'webui',
            'health_endpoint': 'http://localhost:3001/health',
            'production_url': 'https://aiwfe.com',
            'restart_command': 'docker-compose up -d webui',
            'validation_command': 'curl -f http://localhost:3001/health'
        },
        'backend': {
            'container_pattern': 'backend|fastapi',
            'health_endpoint': 'http://localhost:8000/health',
            'restart_command': 'docker-compose up -d backend',
            'validation_command': 'curl -f http://localhost:8000/health'
        },
        'database': {
            'container_pattern': 'postgres|mariadb',
            'health_endpoint': None,
            'restart_command': 'docker-compose up -d database',
            'validation_command': 'docker exec $(docker ps -q -f name=database) pg_isready'
        },
        'redis': {
            'container_pattern': 'redis',
            'health_endpoint': None,
            'restart_command': 'docker-compose up -d redis',
            'validation_command': 'docker exec $(docker ps -q -f name=redis) redis-cli ping'
        }
    }
    
    def __init__(self):
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3
        self.recovery_state_file = Path('.claude/recovery-state.json')
        self.load_recovery_state()
    
    def load_recovery_state(self):
        """Load previous recovery state"""
        if self.recovery_state_file.exists():
            with open(self.recovery_state_file, 'r') as f:
                self.recovery_attempts = json.load(f)
    
    def save_recovery_state(self):
        """Persist recovery state"""
        with open(self.recovery_state_file, 'w') as f:
            json.dump(self.recovery_attempts, f, indent=2)
    
    def check_container_health(self, service_name: str) -> Tuple[bool, str]:
        """Check if a service container is healthy"""
        service = self.CRITICAL_SERVICES[service_name]
        
        try:
            # Check if container is running
            result = subprocess.run(
                f"docker ps --filter 'name={service['container_pattern']}' --format '{{{{.Names}}}} {{{{.Status}}}}'",
                shell=True, capture_output=True, text=True
            )
            
            if not result.stdout.strip():
                return False, "Container not running"
            
            # Check if container is healthy
            if 'healthy' not in result.stdout and 'Up' not in result.stdout:
                return False, f"Container unhealthy: {result.stdout}"
            
            # Check health endpoint if available
            if service.get('health_endpoint'):
                health_result = subprocess.run(
                    f"curl -f -s {service['health_endpoint']}",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if health_result.returncode != 0:
                    return False, "Health endpoint check failed"
            
            # Run validation command
            if service.get('validation_command'):
                val_result = subprocess.run(
                    service['validation_command'],
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if val_result.returncode != 0:
                    return False, f"Validation failed: {val_result.stderr}"
            
            return True, "Service healthy"
            
        except Exception as e:
            return False, f"Health check error: {str(e)}"
    
    def recover_service(self, service_name: str) -> bool:
        """Attempt to recover a failed service"""
        logger.warning(f"Attempting recovery for service: {service_name}")
        
        # Track recovery attempts
        if service_name not in self.recovery_attempts:
            self.recovery_attempts[service_name] = []
        
        attempt_count = len([a for a in self.recovery_attempts[service_name] 
                           if time.time() - a < 3600])  # Count attempts in last hour
        
        if attempt_count >= self.max_recovery_attempts:
            logger.error(f"Max recovery attempts reached for {service_name}")
            self.trigger_manual_intervention(service_name)
            return False
        
        service = self.CRITICAL_SERVICES[service_name]
        
        try:
            # Stop the container first if it exists
            subprocess.run(
                f"docker stop $(docker ps -q -f name={service['container_pattern']})",
                shell=True, capture_output=True, timeout=30
            )
            
            # Remove the container
            subprocess.run(
                f"docker rm $(docker ps -aq -f name={service['container_pattern']})",
                shell=True, capture_output=True, timeout=10
            )
            
            # Restart the service
            result = subprocess.run(
                service['restart_command'],
                shell=True, capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to restart {service_name}: {result.stderr}")
                return False
            
            # Wait for service to stabilize
            time.sleep(10)
            
            # Verify recovery
            healthy, status = self.check_container_health(service_name)
            
            if healthy:
                logger.info(f"Successfully recovered {service_name}")
                self.recovery_attempts[service_name].append(time.time())
                self.save_recovery_state()
                return True
            else:
                logger.error(f"Recovery verification failed for {service_name}: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Recovery failed for {service_name}: {str(e)}")
            return False
    
    def trigger_manual_intervention(self, service_name: str):
        """Trigger manual intervention for critical failures"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'service': service_name,
            'severity': 'CRITICAL',
            'message': f"Automated recovery failed for {service_name}. Manual intervention required.",
            'recovery_attempts': self.recovery_attempts.get(service_name, [])
        }
        
        # Write alert to file
        alert_file = Path('.claude/alerts/critical-failures.json')
        alert_file.parent.mkdir(exist_ok=True)
        
        alerts = []
        if alert_file.exists():
            with open(alert_file, 'r') as f:
                alerts = json.load(f)
        
        alerts.append(alert)
        
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        logger.critical(f"MANUAL INTERVENTION REQUIRED: {alert['message']}")
    
    def continuous_monitoring(self):
        """Continuous monitoring loop"""
        logger.info("Starting continuous monitoring...")
        
        while True:
            try:
                for service_name in self.CRITICAL_SERVICES:
                    healthy, status = self.check_container_health(service_name)
                    
                    if not healthy:
                        logger.warning(f"Service {service_name} is unhealthy: {status}")
                        
                        # Attempt recovery
                        if not self.recover_service(service_name):
                            logger.error(f"Failed to recover {service_name}")
                    else:
                        logger.debug(f"Service {service_name} is healthy")
                
                # Check production accessibility
                prod_check = subprocess.run(
                    "curl -f -s -o /dev/null -w '%{http_code}' https://aiwfe.com",
                    shell=True, capture_output=True, text=True
                )
                
                if prod_check.stdout.strip() != '200':
                    logger.error(f"Production site not accessible: HTTP {prod_check.stdout}")
                    # Trigger webui recovery
                    self.recover_service('webui')
                
                # Sleep before next check
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}")
                time.sleep(60)

class DeploymentSafetyGuard:
    """Ensures safe deployments with service protection"""
    
    def __init__(self):
        self.protected_services = []
        self.deployment_state = {}
    
    def map_service_dependencies(self) -> Dict[str, List[str]]:
        """Map all service dependencies before deployment"""
        dependencies = {}
        
        # Get all running containers
        result = subprocess.run(
            "docker ps --format '{{.Names}}'",
            shell=True, capture_output=True, text=True
        )
        
        running_containers = result.stdout.strip().split('\n')
        
        for container in running_containers:
            if container:
                # Get container dependencies
                inspect_result = subprocess.run(
                    f"docker inspect {container} --format '{{{{.HostConfig.Links}}}}'",
                    shell=True, capture_output=True, text=True
                )
                
                deps = []
                if inspect_result.stdout.strip() and inspect_result.stdout.strip() != '[]':
                    deps = [d.strip() for d in inspect_result.stdout.strip()[1:-1].split()]
                
                dependencies[container] = deps
        
        return dependencies
    
    def protect_critical_services(self, deployment_plan: Dict):
        """Protect critical services during deployment"""
        critical_services = ['webui', 'backend', 'database', 'redis']
        
        for service in critical_services:
            if service in deployment_plan.get('services_to_update', []):
                logger.info(f"Protecting {service} during deployment")
                
                # Create backup of service configuration
                subprocess.run(
                    f"docker commit $(docker ps -q -f name={service}) {service}:backup",
                    shell=True, capture_output=True
                )
                
                self.protected_services.append(service)
    
    def validate_deployment(self) -> bool:
        """Validate deployment didn't break critical services"""
        recovery_manager = ServiceRecoveryManager()
        
        all_healthy = True
        for service_name in recovery_manager.CRITICAL_SERVICES:
            healthy, status = recovery_manager.check_container_health(service_name)
            
            if not healthy:
                logger.error(f"Deployment validation failed for {service_name}: {status}")
                all_healthy = False
        
        return all_healthy
    
    def rollback_deployment(self):
        """Rollback failed deployment"""
        logger.warning("Rolling back deployment...")
        
        for service in self.protected_services:
            try:
                # Stop current container
                subprocess.run(
                    f"docker stop $(docker ps -q -f name={service})",
                    shell=True, capture_output=True, timeout=30
                )
                
                # Restore from backup
                subprocess.run(
                    f"docker run -d --name {service}_restored {service}:backup",
                    shell=True, capture_output=True, timeout=30
                )
                
                logger.info(f"Rolled back {service}")
                
            except Exception as e:
                logger.error(f"Rollback failed for {service}: {str(e)}")

def main():
    """Main entry point for recovery system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Workflow Engine Recovery System')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--check', action='store_true', help='Check all services once')
    parser.add_argument('--recover', help='Recover specific service')
    
    args = parser.parse_args()
    
    recovery_manager = ServiceRecoveryManager()
    
    if args.monitor:
        recovery_manager.continuous_monitoring()
    elif args.check:
        for service_name in recovery_manager.CRITICAL_SERVICES:
            healthy, status = recovery_manager.check_container_health(service_name)
            print(f"{service_name}: {'✓ Healthy' if healthy else f'✗ {status}'}")
    elif args.recover:
        success = recovery_manager.recover_service(args.recover)
        print(f"Recovery {'successful' if success else 'failed'} for {args.recover}")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()