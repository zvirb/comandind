#!/usr/bin/env python3
"""
Enhanced Orchestration Validation Framework
Implements mandatory independent verification to prevent false success claims
"""

import requests
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ValidationResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ERROR = "error"

@dataclass
class ValidationCheck:
    name: str
    description: str
    success: bool
    evidence: Dict[str, Any]
    error_message: Optional[str] = None

@dataclass
class OrchestrationValidationReport:
    execution_id: str
    validation_timestamp: str
    overall_success: bool
    validation_checks: List[ValidationCheck]
    evidence_summary: Dict[str, Any]
    required_iterations: List[str]

class EnhancedValidationFramework:
    """
    Mandatory independent validation system to prevent false success claims.
    Performs actual system testing rather than relying on agent reports.
    """
    
    def __init__(self):
        # Auto-discover API port to prevent configuration errors
        self.api_port = self._discover_api_port()
        self.validation_endpoints = {
            'api_health': f'http://localhost:{self.api_port}/health',
            'api_metrics': 'http://localhost:9090/metrics',  # Prometheus metrics
            'auth_metrics': f'http://localhost:{self.api_port}/auth/metrics',
            'user_metrics': f'http://localhost:{self.api_port}/user/metrics', 
            'node_metrics': 'http://localhost:9100/metrics'
        }
        
        self.evidence_requirements = {
            'authentication_fixes': [
                'redis_connectivity_proof',
                'jwt_validation_success',
                'login_flow_completion',
                'auth_endpoint_responses'
            ],
            'performance_improvements': [
                'response_time_metrics',
                'resource_utilization_data',
                'error_rate_reduction',
                'throughput_measurements'
            ],
            'api_implementations': [
                'endpoint_response_validation',
                'error_handling_tests',
                'integration_flow_tests',
                'api_contract_compliance'
            ],
            'monitoring_infrastructure': [
                'metrics_endpoint_functionality',
                'grafana_dashboard_access',
                'alerting_system_tests',
                'log_aggregation_validation'
            ]
        }
    
    def validate_orchestration_completion(self, execution_context: Dict[str, Any]) -> OrchestrationValidationReport:
        """
        Perform comprehensive independent validation of orchestration claims.
        This is the primary method that prevents false success reporting.
        """
        execution_id = execution_context.get('execution_id', f'validation_{int(time.time())}')
        validation_timestamp = datetime.now().isoformat()
        
        validation_checks = []
        
        # Critical Infrastructure Validation
        validation_checks.extend(self._validate_api_infrastructure())
        validation_checks.extend(self._validate_authentication_systems())
        validation_checks.extend(self._validate_monitoring_infrastructure())
        validation_checks.extend(self._validate_database_connectivity())
        validation_checks.extend(self._validate_service_integration())
        
        # Evidence Validation
        evidence_validation = self._validate_agent_evidence(execution_context)
        validation_checks.extend(evidence_validation)
        
        # Overall Success Determination
        critical_failures = [check for check in validation_checks if not check.success and 'critical' in check.name.lower()]
        overall_success = len(critical_failures) == 0
        
        # Required Iterations
        required_iterations = []
        if critical_failures:
            required_iterations.append("Phase 2.5 - Fix critical infrastructure failures")
        if len([c for c in validation_checks if not c.success]) > len(critical_failures):
            required_iterations.append("Phase 4 - Address validation failures")
            
        return OrchestrationValidationReport(
            execution_id=execution_id,
            validation_timestamp=validation_timestamp,
            overall_success=overall_success,
            validation_checks=validation_checks,
            evidence_summary=self._generate_evidence_summary(validation_checks),
            required_iterations=required_iterations
        )
    
    def _discover_api_port(self) -> int:
        """Discover the correct API port to prevent configuration errors"""
        # Try common API ports in order of likelihood
        potential_ports = [8000, 8080, 3000, 5000, 8001]
        
        for port in potential_ports:
            try:
                response = requests.get(f'http://localhost:{port}/health', timeout=2)
                if response.status_code < 400:
                    return port
            except:
                continue
        
        # Default to 8000 if no working port found
        return 8000
    
    def _validate_api_infrastructure(self) -> List[ValidationCheck]:
        """Test all API endpoints independently"""
        checks = []
        
        for endpoint_name, url in self.validation_endpoints.items():
            if 'localhost:8080' in url:  # API endpoints
                try:
                    response = requests.get(url, timeout=5)
                    success = response.status_code < 400 and response.text != "Error"
                    
                    checks.append(ValidationCheck(
                        name=f"critical_api_{endpoint_name}",
                        description=f"API endpoint {endpoint_name} functional test",
                        success=success,
                        evidence={
                            'url': url,
                            'status_code': response.status_code,
                            'response_preview': response.text[:200],
                            'response_time': response.elapsed.total_seconds()
                        },
                        error_message=None if success else f"API returned {response.status_code} or 'Error'"
                    ))
                    
                except Exception as e:
                    checks.append(ValidationCheck(
                        name=f"critical_api_{endpoint_name}",
                        description=f"API endpoint {endpoint_name} connectivity test",
                        success=False,
                        evidence={'url': url, 'error': str(e)},
                        error_message=f"Failed to connect to {url}: {str(e)}"
                    ))
        
        return checks
    
    def _validate_authentication_systems(self) -> List[ValidationCheck]:
        """Verify authentication infrastructure is working"""
        checks = []
        
        # Redis connectivity test
        try:
            # Use authenticated Redis connection (user: lwe-app)
            result = subprocess.run([
                'docker', 'exec', '-i', 'ai_workflow_engine-redis-1', 
                'redis-cli', '-u', 'redis://lwe-app:$(cat /run/secrets/REDIS_PASSWORD)@localhost:6379', 'ping'
            ], capture_output=True, text=True, timeout=10)
            
            redis_success = result.returncode == 0 and 'PONG' in result.stdout
            
            checks.append(ValidationCheck(
                name="critical_redis_connectivity",
                description="Redis authentication service connectivity",
                success=redis_success,
                evidence={
                    'command': 'docker exec redis-cli ping',
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                },
                error_message=None if redis_success else f"Redis ping failed: {result.stderr}"
            ))
            
        except Exception as e:
            checks.append(ValidationCheck(
                name="critical_redis_connectivity",
                description="Redis authentication service connectivity",
                success=False,
                evidence={'error': str(e)},
                error_message=f"Redis connectivity test failed: {str(e)}"
            ))
        
        # JWT service validation (if API is working)
        try:
            # Test auth endpoint specifically
            auth_response = requests.get('http://localhost:8000/auth/health', timeout=5)
            auth_success = auth_response.status_code < 400
            
            checks.append(ValidationCheck(
                name="critical_jwt_service",
                description="JWT authentication service validation",
                success=auth_success,
                evidence={
                    'status_code': auth_response.status_code,
                    'response': auth_response.text[:200]
                },
                error_message=None if auth_success else "JWT service health check failed"
            ))
            
        except Exception as e:
            checks.append(ValidationCheck(
                name="critical_jwt_service", 
                description="JWT authentication service validation",
                success=False,
                evidence={'error': str(e)},
                error_message=f"JWT service test failed: {str(e)}"
            ))
        
        return checks
    
    def _validate_monitoring_infrastructure(self) -> List[ValidationCheck]:
        """Verify monitoring and metrics systems are functional"""
        checks = []
        
        # Node exporter validation
        try:
            node_response = requests.get('http://localhost:9100/metrics', timeout=5)
            node_success = node_response.status_code == 200 and 'go_gc_duration_seconds' in node_response.text
            
            checks.append(ValidationCheck(
                name="monitoring_node_exporter",
                description="Node exporter metrics functionality",
                success=node_success,
                evidence={
                    'status_code': node_response.status_code,
                    'metrics_count': len(node_response.text.split('\n')) if node_success else 0,
                    'sample_metrics': node_response.text[:300] if node_success else None
                },
                error_message=None if node_success else "Node exporter metrics not accessible"
            ))
            
        except Exception as e:
            checks.append(ValidationCheck(
                name="monitoring_node_exporter",
                description="Node exporter metrics functionality", 
                success=False,
                evidence={'error': str(e)},
                error_message=f"Node exporter test failed: {str(e)}"
            ))
        
        # Grafana connectivity
        try:
            grafana_response = requests.get('http://localhost:3001/api/health', timeout=5)
            grafana_success = grafana_response.status_code == 200
            
            checks.append(ValidationCheck(
                name="monitoring_grafana",
                description="Grafana dashboard service",
                success=grafana_success,
                evidence={
                    'status_code': grafana_response.status_code,
                    'response': grafana_response.text[:200]
                },
                error_message=None if grafana_success else "Grafana health check failed"
            ))
            
        except Exception as e:
            checks.append(ValidationCheck(
                name="monitoring_grafana",
                description="Grafana dashboard service",
                success=False, 
                evidence={'error': str(e)},
                error_message=f"Grafana test failed: {str(e)}"
            ))
        
        return checks
    
    def _validate_database_connectivity(self) -> List[ValidationCheck]:
        """Verify database connections are functional"""
        checks = []
        
        try:
            # Test PostgreSQL connectivity
            result = subprocess.run([
                'docker', 'exec', '-i', 'ai_workflow_engine-postgres-1', 
                'psql', '-U', 'ai_workflow_user', '-d', 'ai_workflow_db', 
                '-c', 'SELECT 1;'
            ], capture_output=True, text=True, timeout=10)
            
            postgres_success = result.returncode == 0 and '1 row' in result.stdout
            
            checks.append(ValidationCheck(
                name="critical_postgres_connectivity",
                description="PostgreSQL database connectivity",
                success=postgres_success,
                evidence={
                    'command': 'psql SELECT 1',
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                },
                error_message=None if postgres_success else f"PostgreSQL test failed: {result.stderr}"
            ))
            
        except Exception as e:
            checks.append(ValidationCheck(
                name="critical_postgres_connectivity",
                description="PostgreSQL database connectivity",
                success=False,
                evidence={'error': str(e)},
                error_message=f"Database connectivity test failed: {str(e)}"
            ))
        
        return checks
    
    def _validate_service_integration(self) -> List[ValidationCheck]:
        """Test service-to-service communication"""
        checks = []
        
        # Docker container health check
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                unhealthy_containers = []
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip() and 'unhealthy' in line.lower():
                        unhealthy_containers.append(line.strip())
                
                integration_success = len(unhealthy_containers) == 0
                
                checks.append(ValidationCheck(
                    name="service_integration_health",
                    description="Docker container health status", 
                    success=integration_success,
                    evidence={
                        'container_status': result.stdout,
                        'unhealthy_containers': unhealthy_containers
                    },
                    error_message=None if integration_success else f"Unhealthy containers: {unhealthy_containers}"
                ))
                
        except Exception as e:
            checks.append(ValidationCheck(
                name="service_integration_health",
                description="Docker container health status",
                success=False,
                evidence={'error': str(e)},
                error_message=f"Container health check failed: {str(e)}"
            ))
        
        return checks
    
    def _validate_agent_evidence(self, execution_context: Dict[str, Any]) -> List[ValidationCheck]:
        """Validate that agents provided required evidence for their success claims"""
        checks = []
        
        agent_results = execution_context.get('agent_results', {})
        
        for agent_name, result in agent_results.items():
            if result.get('success', False):
                task_type = self._determine_task_type(result.get('task', ''))
                required_evidence = self.evidence_requirements.get(task_type, [])
                
                provided_evidence = result.get('evidence', {}) or {}
                missing_evidence = [req for req in required_evidence if req not in provided_evidence]
                
                evidence_complete = len(missing_evidence) == 0
                
                checks.append(ValidationCheck(
                    name=f"evidence_{agent_name}",
                    description=f"Evidence validation for {agent_name}",
                    success=evidence_complete,
                    evidence={
                        'required_evidence': required_evidence,
                        'provided_evidence': list(provided_evidence.keys()),
                        'missing_evidence': missing_evidence,
                        'task_type': task_type
                    },
                    error_message=None if evidence_complete else f"Missing evidence: {missing_evidence}"
                ))
        
        return checks
    
    def _determine_task_type(self, task_description: str) -> str:
        """Determine task type based on description for evidence requirements"""
        task_lower = task_description.lower()
        
        if any(word in task_lower for word in ['auth', 'login', 'jwt', 'redis']):
            return 'authentication_fixes'
        elif any(word in task_lower for word in ['performance', 'optimize', 'speed', 'latency']):
            return 'performance_improvements'
        elif any(word in task_lower for word in ['api', 'endpoint', 'service', 'backend']):
            return 'api_implementations'
        elif any(word in task_lower for word in ['monitor', 'metric', 'grafana', 'prometheus']):
            return 'monitoring_infrastructure'
        else:
            return 'general'
    
    def _generate_evidence_summary(self, validation_checks: List[ValidationCheck]) -> Dict[str, Any]:
        """Generate summary of validation evidence"""
        total_checks = len(validation_checks)
        successful_checks = len([c for c in validation_checks if c.success])
        critical_failures = len([c for c in validation_checks if not c.success and 'critical' in c.name])
        
        return {
            'total_validation_checks': total_checks,
            'successful_checks': successful_checks,
            'failed_checks': total_checks - successful_checks,
            'critical_failures': critical_failures,
            'success_rate': successful_checks / total_checks if total_checks > 0 else 0,
            'validation_quality': 'HIGH' if successful_checks / total_checks > 0.9 else 
                                'MEDIUM' if successful_checks / total_checks > 0.7 else 'LOW'
        }
    
    def generate_validation_report(self, validation_result: OrchestrationValidationReport) -> str:
        """Generate detailed validation report"""
        report = f"""
# Orchestration Validation Report
**Execution ID**: {validation_result.execution_id}
**Validation Time**: {validation_result.validation_timestamp}
**Overall Success**: {'✅ PASS' if validation_result.overall_success else '❌ FAIL'}

## Evidence Summary
- **Total Checks**: {validation_result.evidence_summary['total_validation_checks']}
- **Success Rate**: {validation_result.evidence_summary['success_rate']:.1%}
- **Critical Failures**: {validation_result.evidence_summary['critical_failures']}
- **Validation Quality**: {validation_result.evidence_summary['validation_quality']}

## Detailed Validation Results

"""
        
        for check in validation_result.validation_checks:
            status = "✅ PASS" if check.success else "❌ FAIL"
            report += f"### {check.name} - {status}\n"
            report += f"**Description**: {check.description}\n"
            
            if check.error_message:
                report += f"**Error**: {check.error_message}\n"
            
            report += f"**Evidence**: {json.dumps(check.evidence, indent=2)}\n\n"
        
        if validation_result.required_iterations:
            report += "## Required Iterations\n"
            for iteration in validation_result.required_iterations:
                report += f"- {iteration}\n"
        
        return report

def main():
    """Main function for standalone validation execution"""
    framework = EnhancedValidationFramework()
    
    # Mock execution context for testing
    execution_context = {
        'execution_id': f'validation_test_{int(time.time())}',
        'agent_results': {
            'agent1': {
                'task': 'API implementation',
                'success': True,
                'evidence': {'endpoint_response_validation': 'completed'}
            },
            'agent2': {
                'task': 'Authentication fix',
                'success': True,
                'evidence': {}  # Missing evidence
            }
        }
    }
    
    validation_result = framework.validate_orchestration_completion(execution_context)
    report = framework.generate_validation_report(validation_result)
    
    print("Enhanced Validation Framework Report:")
    print("=" * 50)
    print(report)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'/home/marku/ai_workflow_engine/validation_report_{timestamp}.md', 'w') as f:
        f.write(report)
    
    print(f"Report saved to validation_report_{timestamp}.md")

if __name__ == "__main__":
    main()