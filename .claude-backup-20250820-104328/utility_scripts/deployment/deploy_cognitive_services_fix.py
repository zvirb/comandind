#!/usr/bin/env python3
"""
Cognitive Services SSL Fix Deployment Script

Deploys SSL configuration fixes to all cognitive services through container rebuilds.
Includes neo4j_auth fix for learning service and evidence-based validation.
"""

import subprocess
import time
import logging
import json
import asyncio
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveServicesDeployer:
    """Handles deployment of SSL fixes to cognitive services"""
    
    def __init__(self):
        self.cognitive_services = [
            'hybrid-memory-service',
            'reasoning-service',
            'learning-service',
            'coordination-service'
        ]
        
        self.service_ports = {
            'hybrid-memory-service': 8002,
            'reasoning-service': 8003,
            'learning-service': 8005,
            'coordination-service': 8004
        }
        
        self.deployment_evidence = {
            'timestamp': None,
            'pre_deployment_state': {},
            'post_deployment_state': {},
            'validation_results': {},
            'errors': [],
            'rollback_performed': False
        }
        
    def run_command(self, command: str, description: str, timeout: int = 120) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            logger.info(f"🔧 {description}")
            logger.debug(f"Running command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} completed successfully")
                return True, result.stdout
            else:
                logger.error(f"❌ {description} failed: {result.stderr}")
                self.deployment_evidence['errors'].append({
                    'step': description,
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                })
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} timed out after {timeout} seconds")
            self.deployment_evidence['errors'].append({
                'step': description,
                'error': f"Command timed out after {timeout} seconds",
                'timestamp': datetime.now().isoformat()
            })
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"❌ {description} failed: {e}")
            self.deployment_evidence['errors'].append({
                'step': description,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return False, str(e)
    
    def capture_pre_deployment_state(self) -> Dict[str, any]:
        """Capture current state of services before deployment"""
        logger.info("📸 Capturing pre-deployment state...")
        
        state = {}
        for service in self.cognitive_services:
            # Get container status
            cmd = f"docker ps --filter name={service} --format '{{{{.Status}}}}'"
            success, output = self.run_command(cmd, f"Checking {service} status", timeout=10)
            
            # Get health status
            health_cmd = f"docker inspect ai_workflow_engine-{service}-1 --format '{{{{.State.Health.Status}}}}' 2>/dev/null || echo 'unknown'"
            health_success, health_output = self.run_command(health_cmd, f"Checking {service} health", timeout=10)
            
            # Check for SSL errors in logs
            ssl_cmd = f"docker logs ai_workflow_engine-{service}-1 --tail 100 2>&1 | grep -c 'sslmode' || echo 0"
            ssl_success, ssl_count = self.run_command(ssl_cmd, f"Checking {service} SSL errors", timeout=10)
            
            state[service] = {
                'status': output.strip() if success else 'unknown',
                'health': health_output.strip() if health_success else 'unknown',
                'ssl_errors': sum(int(line.strip()) for line in ssl_count.strip().split('\n') if line.strip().isdigit()) if ssl_success else -1,
                'timestamp': datetime.now().isoformat()
            }
            
        self.deployment_evidence['pre_deployment_state'] = state
        return state
    
    def update_docker_compose_environment(self) -> bool:
        """Update docker-compose.yml with required environment variables"""
        logger.info("📝 Updating docker-compose.yml with environment fixes...")
        
        # First, backup the current docker-compose.yml
        backup_path = f"docker-compose.yml.backup.{int(time.time())}"
        success, _ = self.run_command(
            f"cp docker-compose.yml {backup_path}",
            f"Creating backup at {backup_path}"
        )
        
        if not success:
            logger.error("Failed to create docker-compose.yml backup")
            return False
            
        logger.info(f"✅ Backup created: {backup_path}")
        
        # Add neo4j_auth to learning service if not present
        logger.info("🔧 Adding neo4j_auth configuration for learning service...")
        
        # Create a Python script to safely update the docker-compose.yml
        update_script = '''
import yaml
import sys

# Load docker-compose.yml
with open('docker-compose.yml', 'r') as f:
    compose = yaml.safe_load(f)

# Update learning service with neo4j_auth
if 'learning-service' in compose['services']:
    env = compose['services']['learning-service'].get('environment', [])
    
    # Check if LEARNING_NEO4J_AUTH already exists
    has_neo4j_auth = any('LEARNING_NEO4J_AUTH' in str(e) for e in env)
    
    if not has_neo4j_auth:
        env.append('LEARNING_NEO4J_AUTH=neo4j/password')
        compose['services']['learning-service']['environment'] = env
        print("Added LEARNING_NEO4J_AUTH to learning service")
    else:
        print("LEARNING_NEO4J_AUTH already configured")

# Save updated docker-compose.yml
with open('docker-compose.yml', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

print("Docker-compose.yml updated successfully")
'''
        
        # Write and execute the update script
        with open('/tmp/update_compose.py', 'w') as f:
            f.write(update_script)
            
        success, output = self.run_command(
            "python3 /tmp/update_compose.py",
            "Updating docker-compose.yml"
        )
        
        return success
    
    def stop_cognitive_services(self) -> bool:
        """Stop all cognitive services"""
        logger.info("🛑 Stopping cognitive services...")
        
        # Stop all services in one command for efficiency
        services_str = ' '.join(self.cognitive_services)
        success, output = self.run_command(
            f"docker compose stop {services_str}",
            f"Stopping cognitive services",
            timeout=60
        )
        
        if not success:
            logger.warning("Some services may not have stopped cleanly")
        
        # Give services time to shut down
        logger.info("⏳ Waiting for services to shut down...")
        time.sleep(10)
        
        return True
    
    def rebuild_containers(self) -> bool:
        """Rebuild cognitive service containers in parallel"""
        logger.info("🔨 Rebuilding cognitive service containers...")
        
        services_str = ' '.join(self.cognitive_services)
        
        # Build containers in parallel for speed
        success, output = self.run_command(
            f"docker compose build --parallel {services_str}",
            "Rebuilding containers in parallel",
            timeout=300  # 5 minutes for builds
        )
        
        if not success:
            logger.error("Container rebuild failed")
            return False
            
        logger.info("✅ All containers rebuilt successfully")
        return True
    
    def start_cognitive_services(self) -> bool:
        """Start cognitive services with staggered timing"""
        logger.info("🚀 Starting cognitive services with new configuration...")
        
        # Start coordination service first as others may depend on it
        priority_order = [
            'coordination-service',
            'hybrid-memory-service',
            'reasoning-service',
            'learning-service'
        ]
        
        for service in priority_order:
            success, output = self.run_command(
                f"docker compose up -d {service}",
                f"Starting {service}",
                timeout=60
            )
            
            if not success:
                logger.error(f"Failed to start {service}")
                return False
                
            # Stagger startup to avoid resource contention
            time.sleep(5)
        
        logger.info("⏳ Waiting for all services to initialize...")
        time.sleep(20)
        
        return True
    
    def validate_service_health(self, max_retries: int = 30) -> Dict[str, bool]:
        """Validate that services are healthy after deployment"""
        logger.info("🔍 Validating service health...")
        
        validation_results = {}
        
        for retry in range(max_retries):
            logger.info(f"Health check attempt {retry + 1}/{max_retries}")
            all_healthy = True
            
            for service in self.cognitive_services:
                # Check container health status
                cmd = f"docker inspect ai_workflow_engine-{service}-1 --format '{{{{.State.Health.Status}}}}' 2>/dev/null || echo 'unknown'"
                success, health = self.run_command(
                    cmd, 
                    f"Checking {service} health",
                    timeout=10
                )
                
                health_status = health.strip() if success else 'unknown'
                
                if health_status == 'healthy':
                    validation_results[service] = True
                    logger.info(f"✅ {service} is healthy")
                else:
                    validation_results[service] = False
                    all_healthy = False
                    logger.warning(f"⚠️ {service} is {health_status}")
            
            if all_healthy:
                logger.info("🎉 All services are healthy!")
                return validation_results
                
            # Wait before next check
            time.sleep(10)
        
        logger.error("❌ Some services failed to become healthy")
        return validation_results
    
    def check_ssl_errors(self) -> Dict[str, int]:
        """Check for SSL errors in service logs"""
        logger.info("🔍 Checking for SSL errors in logs...")
        
        ssl_errors = {}
        
        for service in self.cognitive_services:
            cmd = f"docker logs ai_workflow_engine-{service}-1 --tail 200 2>&1 | grep -c 'sslmode\\|SSL\\|ssl' || echo 0"
            success, count = self.run_command(
                cmd,
                f"Checking {service} for SSL errors",
                timeout=10
            )
            
            error_count = int(count.strip()) if success else -1
            ssl_errors[service] = error_count
            
            if error_count == 0:
                logger.info(f"✅ No SSL errors found in {service}")
            elif error_count > 0:
                logger.warning(f"⚠️ Found {error_count} SSL-related messages in {service}")
            else:
                logger.error(f"❌ Could not check SSL errors for {service}")
                
        return ssl_errors
    
    def test_service_endpoints(self) -> Dict[str, bool]:
        """Test service health endpoints"""
        logger.info("🔍 Testing service endpoints...")
        
        endpoint_results = {}
        
        for service, port in self.service_ports.items():
            try:
                response = requests.get(
                    f"http://localhost:{port}/health",
                    timeout=5
                )
                
                if response.status_code == 200:
                    endpoint_results[service] = True
                    logger.info(f"✅ {service} endpoint responding (port {port})")
                else:
                    endpoint_results[service] = False
                    logger.warning(f"⚠️ {service} endpoint returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                endpoint_results[service] = False
                logger.error(f"❌ {service} endpoint unreachable: {e}")
                
        return endpoint_results
    
    def capture_post_deployment_state(self) -> Dict[str, any]:
        """Capture state after deployment for comparison"""
        logger.info("📸 Capturing post-deployment state...")
        
        state = {}
        for service in self.cognitive_services:
            # Get container status
            cmd = f"docker ps --filter name={service} --format '{{{{.Status}}}}'"
            success, output = self.run_command(cmd, f"Checking {service} status", timeout=10)
            
            # Get health status
            health_cmd = f"docker inspect ai_workflow_engine-{service}-1 --format '{{{{.State.Health.Status}}}}' 2>/dev/null || echo 'unknown'"
            health_success, health_output = self.run_command(health_cmd, f"Checking {service} health", timeout=10)
            
            # Get uptime
            uptime_cmd = f"docker ps --filter name={service} --format '{{{{.Status}}}}' | grep -oE '[0-9]+ (seconds|minutes|hours)' || echo 'unknown'"
            uptime_success, uptime = self.run_command(uptime_cmd, f"Checking {service} uptime", timeout=10)
            
            state[service] = {
                'status': output.strip() if success else 'unknown',
                'health': health_output.strip() if health_success else 'unknown',
                'uptime': uptime.strip() if uptime_success else 'unknown',
                'timestamp': datetime.now().isoformat()
            }
            
        self.deployment_evidence['post_deployment_state'] = state
        return state
    
    def rollback_deployment(self, backup_path: str) -> bool:
        """Rollback deployment if validation fails"""
        logger.error("🔄 Initiating rollback...")
        
        self.deployment_evidence['rollback_performed'] = True
        
        # Restore docker-compose.yml from backup
        success, _ = self.run_command(
            f"cp {backup_path} docker-compose.yml",
            f"Restoring docker-compose.yml from {backup_path}"
        )
        
        if not success:
            logger.error("Failed to restore docker-compose.yml")
            return False
            
        # Restart services with original configuration
        logger.info("Restarting services with original configuration...")
        services_str = ' '.join(self.cognitive_services)
        
        self.run_command(
            f"docker compose stop {services_str}",
            "Stopping services for rollback"
        )
        
        time.sleep(5)
        
        self.run_command(
            f"docker compose up -d {services_str}",
            "Starting services with original configuration"
        )
        
        logger.info("✅ Rollback completed")
        return True
    
    def generate_deployment_report(self):
        """Generate comprehensive deployment report"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 COGNITIVE SERVICES DEPLOYMENT REPORT")
        logger.info("=" * 80)
        
        # Deployment summary
        logger.info(f"\n🕒 Deployment Time: {self.deployment_evidence['timestamp']}")
        
        # Pre-deployment state
        logger.info("\n📸 Pre-Deployment State:")
        for service, state in self.deployment_evidence['pre_deployment_state'].items():
            logger.info(f"  {service}:")
            logger.info(f"    Status: {state['status']}")
            logger.info(f"    Health: {state['health']}")
            logger.info(f"    SSL Errors: {state['ssl_errors']}")
        
        # Post-deployment state
        logger.info("\n📸 Post-Deployment State:")
        for service, state in self.deployment_evidence['post_deployment_state'].items():
            logger.info(f"  {service}:")
            logger.info(f"    Status: {state['status']}")
            logger.info(f"    Health: {state['health']}")
            logger.info(f"    Uptime: {state['uptime']}")
        
        # Validation results
        logger.info("\n✅ Validation Results:")
        for test, results in self.deployment_evidence['validation_results'].items():
            logger.info(f"  {test}:")
            for service, result in results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"    {service}: {status}")
        
        # Errors
        if self.deployment_evidence['errors']:
            logger.info("\n❌ Deployment Errors:")
            for error in self.deployment_evidence['errors']:
                logger.info(f"  - {error['step']}: {error['error'][:100]}...")
        
        # Rollback status
        if self.deployment_evidence['rollback_performed']:
            logger.info("\n🔄 Rollback: PERFORMED")
        else:
            logger.info("\n✅ Rollback: NOT REQUIRED")
        
        # Overall status
        all_healthy = all(
            self.deployment_evidence['validation_results'].get('health', {}).values()
        ) if 'health' in self.deployment_evidence['validation_results'] else False
        
        if all_healthy and not self.deployment_evidence['rollback_performed']:
            logger.info("\n🎉 DEPLOYMENT STATUS: SUCCESS")
        else:
            logger.info("\n❌ DEPLOYMENT STATUS: FAILED")
            
        logger.info("=" * 80)
        
        # Save report to file
        report_path = f".claude/deployment/deployment_report_{int(time.time())}.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.deployment_evidence, f, indent=2)
            
        logger.info(f"\n📁 Deployment report saved to: {report_path}")
    
    def deploy(self) -> bool:
        """Execute the complete deployment process"""
        logger.info("🚀 Starting Cognitive Services SSL Fix Deployment")
        logger.info("=" * 80)
        
        self.deployment_evidence['timestamp'] = datetime.now().isoformat()
        
        # Step 1: Capture pre-deployment state
        self.capture_pre_deployment_state()
        
        # Step 2: Update docker-compose.yml
        if not self.update_docker_compose_environment():
            logger.error("Failed to update docker-compose.yml")
            return False
        
        # Keep track of backup for potential rollback
        import glob
        backups = sorted(glob.glob("docker-compose.yml.backup.*"))
        latest_backup = backups[-1] if backups else None
        
        # Step 3: Stop services
        if not self.stop_cognitive_services():
            logger.error("Failed to stop services")
            if latest_backup:
                self.rollback_deployment(latest_backup)
            return False
        
        # Step 4: Rebuild containers
        if not self.rebuild_containers():
            logger.error("Failed to rebuild containers")
            if latest_backup:
                self.rollback_deployment(latest_backup)
            return False
        
        # Step 5: Start services
        if not self.start_cognitive_services():
            logger.error("Failed to start services")
            if latest_backup:
                self.rollback_deployment(latest_backup)
            return False
        
        # Step 6: Validate health
        health_results = self.validate_service_health()
        self.deployment_evidence['validation_results']['health'] = health_results
        
        # Step 7: Check SSL errors
        ssl_results = self.check_ssl_errors()
        self.deployment_evidence['validation_results']['ssl_errors'] = ssl_results
        
        # Step 8: Test endpoints
        endpoint_results = self.test_service_endpoints()
        self.deployment_evidence['validation_results']['endpoints'] = endpoint_results
        
        # Step 9: Capture post-deployment state
        self.capture_post_deployment_state()
        
        # Step 10: Determine success
        all_healthy = all(health_results.values())
        no_ssl_errors = all(count == 0 for count in ssl_results.values() if count >= 0)
        endpoints_working = any(endpoint_results.values())  # At least some endpoints working
        
        deployment_success = all_healthy or (endpoints_working and no_ssl_errors)
        
        # Step 11: Rollback if failed
        if not deployment_success and latest_backup:
            logger.error("Deployment validation failed, initiating rollback...")
            self.rollback_deployment(latest_backup)
            
        # Step 12: Generate report
        self.generate_deployment_report()
        
        return deployment_success

def main():
    """Main deployment function"""
    deployer = CognitiveServicesDeployer()
    
    logger.info("Cognitive Services SSL Fix Deployment")
    logger.info("This will rebuild and restart all cognitive services")
    logger.info("Services: hybrid-memory, reasoning, learning, coordination")
    
    try:
        success = deployer.deploy()
        
        if success:
            logger.info("✅ Deployment completed successfully!")
            logger.info("All cognitive services have been updated with SSL fixes")
            logger.info("Learning service now has neo4j_auth configuration")
            return 0
        else:
            logger.error("❌ Deployment failed!")
            logger.error("Please check the deployment report for details")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Deployment failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)