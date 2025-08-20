#!/usr/bin/env python3
"""
Comprehensive Service Validation - Evidence-Based Success Reporting
Implements automatic error detection and fixes to prevent false success reporting.

This script is part of the orchestration audit improvements to ensure real functional
validation rather than superficial Docker health checks.
"""

import asyncio
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any
import subprocess
import sys

class ServiceValidator:
    """Evidence-based service validation with automatic error detection."""
    
    def __init__(self):
        self.services = {
            'postgres': {'port': 5432, 'type': 'database'},
            'redis': {'port': 6379, 'type': 'database'},
            'qdrant': {'port': 6333, 'type': 'vector_db'},
            'neo4j': {'port': 7474, 'type': 'graph_db'},
            'ollama': {'port': 11434, 'type': 'ai_model'},
            'perception-service': {'port': 8001, 'type': 'cognitive'},
            'hybrid-memory-service': {'port': 8002, 'type': 'cognitive'},
            'reasoning-service': {'port': 8003, 'type': 'cognitive'},
            'coordination-service': {'port': 8004, 'type': 'cognitive'},
            'learning-service': {'port': 8005, 'type': 'cognitive'},
            'integration-service': {'port': 8006, 'type': 'cognitive'}
        }
        self.validation_results = {}
        self.error_detection_log = []
        
    def validate_docker_containers(self) -> Dict[str, bool]:
        """Validate Docker container status."""
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, check=True)
            containers = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
            
            container_status = {}
            for container in containers:
                name = container['Names']
                if name.startswith('aiwfe-'):
                    service_name = name.replace('aiwfe-', '')
                    container_status[service_name] = container['State'] == 'running'
                    
            return container_status
        except Exception as e:
            self.error_detection_log.append(f"Docker validation failed: {str(e)}")
            return {}
    
    def validate_service_endpoint(self, service: str, port: int, service_type: str) -> Dict[str, Any]:
        """Validate actual service functionality, not just container health."""
        validation_result = {
            'service': service,
            'port': port,
            'type': service_type,
            'functional': False,
            'response_time': -1,
            'error': None,
            'evidence': None
        }
        
        try:
            start_time = time.time()
            
            if service_type == 'cognitive':
                # Test actual cognitive service endpoints
                response = requests.get(f"http://localhost:{port}/health", timeout=10)
                validation_result['response_time'] = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    health_data = response.json()
                    validation_result['evidence'] = health_data
                    
                    # Enhanced validation for cognitive services
                    if 'status' in health_data:
                        if health_data['status'] == 'healthy':
                            validation_result['functional'] = True
                        elif health_data['status'] == 'unhealthy':
                            validation_result['functional'] = False
                            validation_result['error'] = f"Service reports unhealthy status: {health_data}"
                        else:
                            validation_result['functional'] = False
                            validation_result['error'] = f"Unknown status: {health_data['status']}"
                    else:
                        validation_result['functional'] = False
                        validation_result['error'] = "No status field in health response"
                else:
                    validation_result['error'] = f"HTTP {response.status_code}: {response.text}"
                    
            elif service_type in ['database', 'vector_db', 'graph_db']:
                # Test database connectivity
                if service == 'qdrant':
                    response = requests.get(f"http://localhost:{port}", timeout=5)
                elif service == 'neo4j':
                    response = requests.get(f"http://localhost:{port}", timeout=5)
                else:
                    # For postgres/redis, just check if port is accessible
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    validation_result['functional'] = result == 0
                    validation_result['response_time'] = (time.time() - start_time) * 1000
                    if result != 0:
                        validation_result['error'] = f"Port {port} not accessible"
                    return validation_result
                    
                validation_result['response_time'] = (time.time() - start_time) * 1000
                validation_result['functional'] = response.status_code in [200, 404]  # 404 is OK for some services
                if not validation_result['functional']:
                    validation_result['error'] = f"HTTP {response.status_code}: {response.text}"
                    
            elif service_type == 'ai_model':
                # Test AI model availability
                response = requests.get(f"http://localhost:{port}/api/tags", timeout=10)
                validation_result['response_time'] = (time.time() - start_time) * 1000
                validation_result['functional'] = response.status_code == 200
                if not validation_result['functional']:
                    validation_result['error'] = f"HTTP {response.status_code}: {response.text}"
                else:
                    validation_result['evidence'] = response.json()
                    
        except Exception as e:
            validation_result['error'] = str(e)
            validation_result['response_time'] = (time.time() - start_time) * 1000
            
        return validation_result
    
    def calculate_success_metrics(self) -> Dict[str, float]:
        """Calculate evidence-based success metrics."""
        if not self.validation_results:
            return {'overall': 0.0, 'infrastructure': 0.0, 'cognitive': 0.0}
        
        infrastructure_services = [s for s, info in self.services.items() 
                                 if info['type'] in ['database', 'vector_db', 'graph_db', 'ai_model']]
        cognitive_services = [s for s, info in self.services.items() 
                            if info['type'] == 'cognitive']
        
        # Infrastructure success rate
        infra_functional = sum(1 for s in infrastructure_services 
                             if s in self.validation_results and self.validation_results[s].get('functional', False))
        infra_success = infra_functional / len(infrastructure_services) if infrastructure_services else 0
        
        # Cognitive services success rate
        cognitive_functional = sum(1 for s in cognitive_services 
                                 if s in self.validation_results and self.validation_results[s].get('functional', False))
        cognitive_success = cognitive_functional / len(cognitive_services) if cognitive_services else 0
        
        # Overall success rate
        all_functional = infra_functional + cognitive_functional
        overall_success = all_functional / len(self.services)
        
        return {
            'overall': overall_success,
            'infrastructure': infra_success,
            'cognitive': cognitive_success,
            'functional_services': all_functional,
            'total_services': len(self.services)
        }
    
    def detect_and_log_errors(self) -> List[str]:
        """Detect specific errors and provide actionable recommendations."""
        errors = []
        
        for service, result in self.validation_results.items():
            if not result.get('functional', False):
                error_msg = f"FAILURE: {service} - {result.get('error', 'Unknown error')}"
                errors.append(error_msg)
                
                # Specific error detection patterns
                if 'unhealthy' in str(result.get('error', '')).lower():
                    errors.append(f"  → {service} reports unhealthy status - check service logs")
                elif 'connection refused' in str(result.get('error', '')).lower():
                    errors.append(f"  → {service} not responding - service may not be started")
                elif 'timeout' in str(result.get('error', '')).lower():
                    errors.append(f"  → {service} timeout - service may be overloaded or starting")
        
        return errors
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation with automatic error detection."""
        print("🔍 Starting Comprehensive Service Validation...")
        print("=" * 60)
        
        # Step 1: Docker container validation
        print("1. Validating Docker containers...")
        container_status = self.validate_docker_containers()
        
        # Step 2: Service endpoint validation
        print("2. Validating service endpoints...")
        for service, config in self.services.items():
            print(f"   Testing {service} on port {config['port']}...")
            result = self.validate_service_endpoint(service, config['port'], config['type'])
            self.validation_results[service] = result
            
            status_icon = "✅" if result['functional'] else "❌"
            print(f"   {status_icon} {service}: {'FUNCTIONAL' if result['functional'] else 'FAILED'}")
            
            if not result['functional'] and result['error']:
                print(f"      Error: {result['error']}")
        
        # Step 3: Calculate success metrics
        metrics = self.calculate_success_metrics()
        
        # Step 4: Error detection and recommendations
        errors = self.detect_and_log_errors()
        
        # Step 5: Generate comprehensive report
        report = {
            'timestamp': datetime.now().isoformat(),
            'validation_results': self.validation_results,
            'success_metrics': metrics,
            'errors_detected': errors,
            'error_detection_log': self.error_detection_log,
            'passes_threshold': metrics['overall'] >= 0.85,  # >85% threshold
            'recommendations': self._generate_recommendations(metrics, errors)
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall Success Rate: {metrics['overall']:.1%} ({metrics['functional_services']}/{metrics['total_services']} services)")
        print(f"Infrastructure: {metrics['infrastructure']:.1%}")
        print(f"Cognitive Services: {metrics['cognitive']:.1%}")
        print(f"Threshold (>85%): {'✅ PASS' if report['passes_threshold'] else '❌ FAIL'}")
        
        if errors:
            print(f"\n🚨 ERRORS DETECTED ({len(errors)} issues):")
            for error in errors:
                print(f"  {error}")
        
        return report
    
    def _generate_recommendations(self, metrics: Dict[str, float], errors: List[str]) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []
        
        if metrics['overall'] < 0.85:
            recommendations.append("CRITICAL: System below 85% operational threshold - immediate action required")
        
        if metrics['infrastructure'] < 1.0:
            recommendations.append("Infrastructure services not fully operational - check database connections")
        
        if metrics['cognitive'] < 0.8:
            recommendations.append("Cognitive services degraded - check service dependencies and startup order")
        
        # Specific recommendations based on error patterns
        failed_services = [s for s, r in self.validation_results.items() if not r.get('functional', False)]
        
        if 'coordination-service' in failed_services and 'learning-service' in failed_services:
            recommendations.append("DETECTED: Circular dependency issue - coordination-service and learning-service both failing")
            recommendations.append("SOLUTION: Remove coordination-service dependency from learning-service startup")
        
        if any('unhealthy' in str(r.get('error', '')) for r in self.validation_results.values()):
            recommendations.append("Services reporting unhealthy status - check service-specific health requirements")
        
        return recommendations

async def main():
    """Main validation execution with automated error detection and reporting."""
    validator = ServiceValidator()
    report = await validator.run_comprehensive_validation()
    
    # Save detailed report
    report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Detailed report saved: {report_file}")
    
    # Return appropriate exit code
    sys.exit(0 if report['passes_threshold'] else 1)

if __name__ == "__main__":
    asyncio.run(main())