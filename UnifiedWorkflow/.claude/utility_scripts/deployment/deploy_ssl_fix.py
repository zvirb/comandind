#!/usr/bin/env python3
"""
SSL Database Configuration Fix Deployment Script

Deploys the SSL configuration fix by restarting services in the correct order
and validating that the fix is working properly.
"""

import subprocess
import time
import logging
import json
import requests
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SSLFixDeployer:
    """Handles deployment of SSL database configuration fix"""
    
    def __init__(self):
        self.services_to_restart = [
            'postgres',  # Database first
            'pgbouncer', # Connection pooler
            'api',       # API service (uses both sync and async connections)
            'worker',    # Worker service
            'ollama',    # Ollama service
            'webui'      # Frontend
        ]
        
    def run_command(self, command: str, description: str) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            logger.info(f"🔧 {description}")
            logger.debug(f"Running command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {description} completed successfully")
                return True, result.stdout
            else:
                logger.error(f"❌ {description} failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} timed out")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"❌ {description} failed: {e}")
            return False, str(e)
    
    def stop_services(self) -> bool:
        """Stop services in reverse order to minimize disruption"""
        logger.info("🛑 Stopping services for SSL configuration deployment...")
        
        # Stop services in reverse order
        for service in reversed(self.services_to_restart):
            success, output = self.run_command(
                f"docker compose stop {service}",
                f"Stopping {service} service"
            )
            if not success:
                logger.warning(f"Failed to stop {service}, continuing anyway")
        
        # Give services time to shut down gracefully
        logger.info("⏳ Waiting for services to shut down...")
        time.sleep(5)
        return True
    
    def start_services(self) -> bool:
        """Start services in correct dependency order"""
        logger.info("🚀 Starting services with new SSL configuration...")
        
        # Start core services first
        core_services = ['postgres', 'pgbouncer']
        for service in core_services:
            success, output = self.run_command(
                f"docker compose up -d {service}",
                f"Starting {service} service"
            )
            if not success:
                logger.error(f"Critical service {service} failed to start")
                return False
            
            # Wait for core services to be ready
            time.sleep(3)
        
        # Start application services
        app_services = ['api', 'worker', 'ollama']
        for service in app_services:
            success, output = self.run_command(
                f"docker compose up -d {service}",
                f"Starting {service} service"
            )
            if not success:
                logger.warning(f"Application service {service} failed to start")
            
            time.sleep(2)
        
        # Start frontend last
        success, output = self.run_command(
            "docker compose up -d webui",
            "Starting webui service"
        )
        
        logger.info("⏳ Waiting for all services to initialize...")
        time.sleep(10)
        return True
    
    def validate_ssl_fix(self) -> Dict[str, bool]:
        """Validate that the SSL fix is working"""
        logger.info("🔍 Validating SSL database configuration fix...")
        
        validation_results = {
            'api_health': False,
            'database_connection': False,
            'ollama_models': False,
            'auth_working': False
        }
        
        # Test 1: API Health
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                validation_results['api_health'] = True
                logger.info("✅ API service is healthy")
            else:
                logger.error(f"❌ API health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ API health check failed: {e}")
        
        # Test 2: Database connection (via API)
        try:
            response = requests.get("http://localhost:8000/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get('database') == 'healthy':
                    validation_results['database_connection'] = True
                    logger.info("✅ Database connection is healthy")
                else:
                    logger.error(f"❌ Database connection status: {health_data.get('database')}")
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
        
        # Test 3: Ollama models (check if we have 10+ models now)
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                model_count = len(models)
                
                if model_count >= 10:
                    validation_results['ollama_models'] = True
                    logger.info(f"✅ Full Ollama model set available ({model_count} models)")
                elif model_count > 2:
                    logger.warning(f"⚠️  Partial model set available ({model_count} models)")
                else:
                    logger.error(f"❌ Minimal model set ({model_count} models)")
                    
        except Exception as e:
            logger.error(f"❌ Ollama models test failed: {e}")
        
        # Test 4: Authentication (basic endpoint test)
        try:
            # Test a protected endpoint - should return 401 without auth
            response = requests.get("http://localhost:8000/auth/me", timeout=10)
            if response.status_code == 401:
                validation_results['auth_working'] = True
                logger.info("✅ Authentication system is responding correctly")
            else:
                logger.error(f"❌ Authentication unexpected response: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Authentication test failed: {e}")
        
        return validation_results
    
    def check_logs_for_ssl_errors(self) -> bool:
        """Check recent logs for SSL-related errors"""
        logger.info("🔍 Checking logs for SSL errors...")
        
        services_to_check = ['api', 'worker']
        ssl_errors_found = False
        
        for service in services_to_check:
            success, output = self.run_command(
                f"docker compose logs {service} --tail=50",
                f"Checking {service} logs"
            )
            
            if success:
                # Check for common SSL errors
                ssl_error_patterns = [
                    "sslmode",
                    "unexpected keyword argument",
                    "SSL connection error",
                    "certificate verify failed"
                ]
                
                for pattern in ssl_error_patterns:
                    if pattern.lower() in output.lower():
                        logger.error(f"❌ SSL error found in {service} logs: {pattern}")
                        ssl_errors_found = True
                        break
                
                if not ssl_errors_found:
                    logger.info(f"✅ No SSL errors found in {service} logs")
        
        return not ssl_errors_found
    
    def deploy(self) -> bool:
        """Execute the complete deployment process"""
        logger.info("🚀 Starting SSL Database Configuration Fix Deployment")
        logger.info("="*80)
        
        # Step 1: Stop services
        if not self.stop_services():
            logger.error("❌ Failed to stop services")
            return False
        
        # Step 2: Start services with new configuration
        if not self.start_services():
            logger.error("❌ Failed to start services")
            return False
        
        # Step 3: Validate the fix
        validation_results = self.validate_ssl_fix()
        
        # Step 4: Check logs for errors
        logs_clean = self.check_logs_for_ssl_errors()
        
        # Step 5: Report results
        self.report_deployment_results(validation_results, logs_clean)
        
        # Determine overall success
        core_tests_passed = (
            validation_results['api_health'] and
            validation_results['database_connection'] and
            logs_clean
        )
        
        if core_tests_passed:
            logger.info("🎉 SSL Database Configuration Fix Deployment SUCCESSFUL!")
            return True
        else:
            logger.error("❌ SSL Database Configuration Fix Deployment FAILED!")
            return False
    
    def report_deployment_results(self, validation_results: Dict[str, bool], logs_clean: bool):
        """Report detailed deployment results"""
        logger.info("\n" + "="*80)
        logger.info("📊 DEPLOYMENT VALIDATION RESULTS")
        logger.info("="*80)
        
        results = {
            "API Health": validation_results['api_health'],
            "Database Connection": validation_results['database_connection'],
            "Ollama Models": validation_results['ollama_models'],
            "Authentication": validation_results['auth_working'],
            "Logs Clean": logs_clean
        }
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
        
        logger.info("-"*80)
        logger.info(f"SUMMARY: {passed}/{total} validations passed ({passed/total*100:.1f}%)")
        
        if validation_results['database_connection'] and logs_clean:
            logger.info("🎯 CORE SSL FIX SUCCESSFUL - Async database connections working!")
        
        if validation_results['ollama_models']:
            logger.info("🔧 SERVICE INTEGRATION RESTORED - Ollama showing full model set!")
        
        logger.info("="*80)

def main():
    """Main deployment function"""
    deployer = SSLFixDeployer()
    
    logger.info("SSL Database Configuration Fix - Deployment Starting")
    logger.info("This will restart all services to apply the SSL configuration fix")
    
    success = deployer.deploy()
    
    if success:
        logger.info("✅ Deployment completed successfully!")
        logger.info("The SSL parameter incompatibility has been resolved.")
        logger.info("All services should now have full functionality.")
        return 0
    else:
        logger.error("❌ Deployment failed!")
        logger.error("Manual intervention may be required.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"Deployment failed with unexpected error: {e}")
        exit(1)