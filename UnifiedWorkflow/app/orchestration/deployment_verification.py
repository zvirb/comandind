#!/usr/bin/env python3
"""
Deployment Verification System - Critical Gap Resolution
Automated deployment verification with comprehensive evidence collection
"""

import asyncio
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import docker
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DeploymentEvidence:
    """Evidence collection for deployment verification"""
    timestamp: str
    service_name: str
    status: str
    health_check: Dict
    curl_output: Optional[str]
    logs: List[str]
    metrics: Dict

class DeploymentVerificationSystem:
    """Automated deployment verification with evidence collection"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.evidence_dir = Path("/home/marku/ai_workflow_engine/.claude/deployment_evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.production_endpoints = [
            "https://aiwfe.com",
            "https://aiwfe.com/api/health",
            "https://aiwfe.com/api/v1/status",
            "http://aiwfe.com"  # Also test HTTP redirect
        ]
        
    async def verify_full_deployment(self) -> Dict:
        """Complete deployment verification with evidence"""
        logger.info("Starting comprehensive deployment verification...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "deployment_status": "verifying",
            "services": {},
            "endpoints": {},
            "evidence": [],
            "gaps_detected": [],
            "recommendations": []
        }
        
        # Step 1: Verify all services are running
        service_status = await self.verify_all_services()
        results["services"] = service_status
        
        # Step 2: Validate production endpoints
        endpoint_status = await self.validate_production_endpoints()
        results["endpoints"] = endpoint_status
        
        # Step 3: Check blue-green deployment
        blue_green_status = await self.verify_blue_green_deployment()
        results["blue_green"] = blue_green_status
        
        # Step 4: Collect comprehensive evidence
        evidence = await self.collect_deployment_evidence()
        results["evidence"] = evidence
        
        # Step 5: Detect deployment gaps
        gaps = self.detect_deployment_gaps(results)
        results["gaps_detected"] = gaps
        
        # Step 6: Generate recommendations
        recommendations = self.generate_recommendations(gaps)
        results["recommendations"] = recommendations
        
        # Determine overall status
        if not gaps:
            results["deployment_status"] = "verified_successful"
        else:
            results["deployment_status"] = "gaps_detected"
            
        # Save verification report
        self.save_verification_report(results)
        
        return results
    
    async def verify_all_services(self) -> Dict:
        """Verify all Docker services are running"""
        services = {}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                service_name = container.name
                services[service_name] = {
                    "status": container.status,
                    "health": await self.check_service_health(container),
                    "restart_count": container.attrs.get('RestartCount', 0),
                    "created": container.attrs.get('Created', ''),
                    "ports": container.attrs.get('NetworkSettings', {}).get('Ports', {})
                }
                
                # Collect logs for failed services
                if container.status != "running":
                    services[service_name]["error_logs"] = container.logs(tail=50).decode()
                    
        except Exception as e:
            logger.error(f"Error verifying services: {e}")
            services["error"] = str(e)
            
        return services
    
    async def check_service_health(self, container) -> Dict:
        """Check health status of a service"""
        health = {"status": "unknown"}
        
        try:
            # Check if container has health check
            health_config = container.attrs.get('Config', {}).get('Healthcheck')
            if health_config:
                health_status = container.attrs.get('State', {}).get('Health', {})
                health = {
                    "status": health_status.get('Status', 'unknown'),
                    "failing_streak": health_status.get('FailingStreak', 0),
                    "log": health_status.get('Log', [])[-1] if health_status.get('Log') else None
                }
            else:
                # Try to hit health endpoint if available
                if 'api' in container.name or 'backend' in container.name:
                    health = await self.check_http_health(container)
                    
        except Exception as e:
            health["error"] = str(e)
            
        return health
    
    async def check_http_health(self, container) -> Dict:
        """Check HTTP health endpoint"""
        health = {"status": "unknown"}
        
        try:
            # Get container port mapping
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            for internal, external in ports.items():
                if external and '/' in internal:
                    port = external[0]['HostPort']
                    health_url = f"http://localhost:{port}/health"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(health_url, timeout=5) as response:
                            health = {
                                "status": "healthy" if response.status == 200 else "unhealthy",
                                "http_status": response.status,
                                "endpoint": health_url
                            }
                            break
                            
        except Exception as e:
            health["error"] = str(e)
            
        return health
    
    async def validate_production_endpoints(self) -> Dict:
        """Validate all production endpoints with evidence"""
        endpoints = {}
        
        for endpoint in self.production_endpoints:
            logger.info(f"Validating endpoint: {endpoint}")
            
            # Curl test with evidence
            curl_result = await self.curl_with_evidence(endpoint)
            endpoints[endpoint] = curl_result
            
            # Additional validation for main site
            if endpoint == "https://aiwfe.com":
                endpoints[endpoint]["content_validation"] = await self.validate_site_content(endpoint)
                
        return endpoints
    
    async def curl_with_evidence(self, url: str) -> Dict:
        """Execute curl with comprehensive evidence collection"""
        result = {
            "url": url,
            "accessible": False,
            "response_code": None,
            "headers": {},
            "error": None,
            "evidence": {}
        }
        
        try:
            # Execute curl command
            cmd = f"curl -I -s -o /dev/null -w '%{{http_code}}' {url}"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            response_code = stdout.decode().strip()
            result["response_code"] = response_code
            result["accessible"] = response_code in ["200", "301", "302", "304"]
            
            # Get detailed headers
            headers_cmd = f"curl -I -s {url}"
            headers_process = await asyncio.create_subprocess_shell(
                headers_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            headers_out, _ = await headers_process.communicate()
            result["headers"] = headers_out.decode()
            
            # Save evidence
            evidence_file = self.evidence_dir / f"curl_{url.replace('://', '_').replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            evidence_file.write_text(f"URL: {url}\nResponse Code: {response_code}\nHeaders:\n{headers_out.decode()}")
            result["evidence"]["file"] = str(evidence_file)
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error validating {url}: {e}")
            
        return result
    
    async def validate_site_content(self, url: str) -> Dict:
        """Validate actual site content"""
        validation = {
            "has_content": False,
            "expected_elements": [],
            "missing_elements": []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Check for expected elements
                        expected = [
                            "AI Workflow Engine",
                            "Dashboard",
                            "Login",
                            "<!DOCTYPE html>"
                        ]
                        
                        for element in expected:
                            if element.lower() in content.lower():
                                validation["expected_elements"].append(element)
                            else:
                                validation["missing_elements"].append(element)
                                
                        validation["has_content"] = len(content) > 100
                        
        except Exception as e:
            validation["error"] = str(e)
            
        return validation
    
    async def verify_blue_green_deployment(self) -> Dict:
        """Verify blue-green deployment configuration"""
        blue_green = {
            "configured": False,
            "active_environment": None,
            "passive_environment": None,
            "can_rollback": False
        }
        
        try:
            # Check for blue-green configuration
            compose_file = Path("/home/marku/ai_workflow_engine/docker-compose.yml")
            if compose_file.exists():
                content = compose_file.read_text()
                
                # Look for blue-green indicators
                if "blue" in content.lower() or "green" in content.lower():
                    blue_green["configured"] = True
                    
                # Check active services
                running_containers = self.docker_client.containers.list()
                for container in running_containers:
                    if "blue" in container.name.lower():
                        blue_green["active_environment"] = "blue"
                    elif "green" in container.name.lower():
                        blue_green["active_environment"] = "green"
                        
                # Check for rollback capability
                blue_green["can_rollback"] = blue_green["configured"]
                
        except Exception as e:
            blue_green["error"] = str(e)
            
        return blue_green
    
    async def collect_deployment_evidence(self) -> List[Dict]:
        """Collect comprehensive deployment evidence"""
        evidence = []
        
        # Docker compose status
        try:
            cmd = "cd /home/marku/ai_workflow_engine && docker-compose ps --format json"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            evidence.append({
                "type": "docker_compose_status",
                "timestamp": datetime.now().isoformat(),
                "data": stdout.decode()
            })
        except Exception as e:
            logger.error(f"Error collecting docker-compose evidence: {e}")
            
        # System resource usage
        try:
            cmd = "docker stats --no-stream --format json"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            evidence.append({
                "type": "resource_usage",
                "timestamp": datetime.now().isoformat(),
                "data": stdout.decode()
            })
        except Exception as e:
            logger.error(f"Error collecting resource evidence: {e}")
            
        # Network connectivity
        try:
            cmd = "docker network ls --format json"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            evidence.append({
                "type": "network_configuration",
                "timestamp": datetime.now().isoformat(),
                "data": stdout.decode()
            })
        except Exception as e:
            logger.error(f"Error collecting network evidence: {e}")
            
        return evidence
    
    def detect_deployment_gaps(self, results: Dict) -> List[Dict]:
        """Detect gaps in deployment"""
        gaps = []
        
        # Check service gaps
        for service, status in results.get("services", {}).items():
            if isinstance(status, dict) and status.get("status") != "running":
                gaps.append({
                    "type": "service_not_running",
                    "service": service,
                    "current_status": status.get("status"),
                    "severity": "critical"
                })
                
        # Check endpoint gaps
        for endpoint, status in results.get("endpoints", {}).items():
            if not status.get("accessible"):
                gaps.append({
                    "type": "endpoint_not_accessible",
                    "endpoint": endpoint,
                    "response_code": status.get("response_code"),
                    "severity": "critical" if "aiwfe.com" in endpoint else "high"
                })
                
        # Check blue-green gaps
        bg_status = results.get("blue_green", {})
        if not bg_status.get("configured"):
            gaps.append({
                "type": "blue_green_not_configured",
                "severity": "medium",
                "recommendation": "Configure blue-green deployment for zero-downtime updates"
            })
            
        return gaps
    
    def generate_recommendations(self, gaps: List[Dict]) -> List[str]:
        """Generate recommendations based on detected gaps"""
        recommendations = []
        
        for gap in gaps:
            if gap["type"] == "service_not_running":
                recommendations.append(
                    f"Restart service '{gap['service']}' using: docker-compose restart {gap['service']}"
                )
            elif gap["type"] == "endpoint_not_accessible":
                recommendations.append(
                    f"Investigate and fix endpoint '{gap['endpoint']}' - Response code: {gap['response_code']}"
                )
            elif gap["type"] == "blue_green_not_configured":
                recommendations.append(gap["recommendation"])
                
        if not gaps:
            recommendations.append("Deployment verification successful - all systems operational")
            
        return recommendations
    
    def save_verification_report(self, results: Dict):
        """Save verification report with evidence"""
        report_file = self.evidence_dir / f"deployment_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logger.info(f"Verification report saved to: {report_file}")
        
        # Also save summary
        summary_file = self.evidence_dir / "latest_verification_summary.txt"
        summary = f"""
Deployment Verification Summary
================================
Timestamp: {results['timestamp']}
Status: {results['deployment_status']}
Services Checked: {len(results.get('services', {}))}
Endpoints Validated: {len(results.get('endpoints', {}))}
Gaps Detected: {len(results.get('gaps_detected', []))}

Recommendations:
{chr(10).join('- ' + r for r in results.get('recommendations', []))}

Full report: {report_file}
"""
        summary_file.write_text(summary)
        logger.info(f"Summary saved to: {summary_file}")


async def main():
    """Main execution for deployment verification"""
    verifier = DeploymentVerificationSystem()
    results = await verifier.verify_full_deployment()
    
    # Print summary
    print("\n" + "="*60)
    print("DEPLOYMENT VERIFICATION COMPLETE")
    print("="*60)
    print(f"Status: {results['deployment_status']}")
    print(f"Gaps Detected: {len(results['gaps_detected'])}")
    
    if results['gaps_detected']:
        print("\nGaps Found:")
        for gap in results['gaps_detected']:
            print(f"  - {gap['type']}: {gap.get('severity', 'unknown')} severity")
            
    print("\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  - {rec}")
        
    print("\nEvidence collected in: .claude/deployment_evidence/")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())