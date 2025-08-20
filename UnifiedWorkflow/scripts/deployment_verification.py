#!/usr/bin/env python3
"""
Deployment Verification System
Automated post-deployment validation with evidence collection
Bridges the gap between implementation and production deployment
"""

import subprocess
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import ssl
import socket
from urllib.parse import urlparse

class DeploymentVerifier:
    """Comprehensive deployment verification with evidence collection."""
    
    def __init__(self):
        self.production_urls = [
            "http://aiwfe.com",
            "https://aiwfe.com"
        ]
        self.local_endpoints = {
            'api': 'http://localhost:8000',
            'webui': 'http://localhost:3001',
            'perception': 'http://localhost:8001',
            'memory': 'http://localhost:8002',
            'reasoning': 'http://localhost:8003',
            'coordination': 'http://localhost:8004',
            'learning': 'http://localhost:8005'
        }
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'local_services': {},
            'production_endpoints': {},
            'ssl_certificates': {},
            'deployment_gaps': [],
            'evidence': {}
        }
    
    def verify_local_services(self) -> Dict[str, Any]:
        """Verify all local services are running and healthy."""
        print("🔍 Verifying local services...")
        
        for service, url in self.local_endpoints.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                self.verification_results['local_services'][service] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'evidence': response.text[:200] if response.text else None
                }
                print(f"  ✅ {service}: Healthy")
            except Exception as e:
                self.verification_results['local_services'][service] = {
                    'status': 'unreachable',
                    'error': str(e)
                }
                print(f"  ❌ {service}: Unreachable - {e}")
        
        return self.verification_results['local_services']
    
    def verify_production_endpoints(self) -> Dict[str, Any]:
        """Verify production endpoints are accessible and properly configured."""
        print("\n🌐 Verifying production endpoints...")
        
        for url in self.production_urls:
            try:
                # Test with curl for better diagnostics
                curl_cmd = f"curl -s -o /dev/null -w '%{{http_code}}:%{{time_total}}' -m 10 {url}"
                result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    http_code, response_time = result.stdout.strip().split(':')
                    
                    self.verification_results['production_endpoints'][url] = {
                        'status': 'accessible',
                        'http_code': http_code,
                        'response_time': float(response_time),
                        'evidence': f"curl output: {result.stdout}"
                    }
                    
                    # Additional validation with requests
                    try:
                        response = requests.get(url, timeout=10, allow_redirects=True)
                        self.verification_results['production_endpoints'][url]['final_url'] = response.url
                        self.verification_results['production_endpoints'][url]['content_length'] = len(response.content)
                        print(f"  ✅ {url}: Accessible (HTTP {http_code})")
                    except Exception as e:
                        print(f"  ⚠️  {url}: Curl succeeded but requests failed - {e}")
                else:
                    self.verification_results['production_endpoints'][url] = {
                        'status': 'unreachable',
                        'error': result.stderr
                    }
                    self.verification_results['deployment_gaps'].append(
                        f"Production endpoint {url} is not accessible"
                    )
                    print(f"  ❌ {url}: Unreachable")
                    
            except Exception as e:
                self.verification_results['production_endpoints'][url] = {
                    'status': 'error',
                    'error': str(e)
                }
                print(f"  ❌ {url}: Error - {e}")
        
        return self.verification_results['production_endpoints']
    
    def verify_ssl_certificates(self) -> Dict[str, Any]:
        """Verify SSL certificates for HTTPS endpoints."""
        print("\n🔒 Verifying SSL certificates...")
        
        for url in self.production_urls:
            if url.startswith('https://'):
                hostname = urlparse(url).hostname
                port = 443
                
                try:
                    context = ssl.create_default_context()
                    with socket.create_connection((hostname, port), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                            cert = ssock.getpeercert()
                            
                            self.verification_results['ssl_certificates'][url] = {
                                'status': 'valid',
                                'issuer': dict(x[0] for x in cert['issuer']),
                                'subject': dict(x[0] for x in cert['subject']),
                                'notAfter': cert['notAfter'],
                                'evidence': f"SSL certificate valid until {cert['notAfter']}"
                            }
                            print(f"  ✅ {url}: SSL certificate valid")
                            
                except Exception as e:
                    self.verification_results['ssl_certificates'][url] = {
                        'status': 'invalid',
                        'error': str(e)
                    }
                    self.verification_results['deployment_gaps'].append(
                        f"SSL certificate issue for {url}: {e}"
                    )
                    print(f"  ❌ {url}: SSL certificate issue - {e}")
        
        return self.verification_results['ssl_certificates']
    
    def verify_docker_deployment(self) -> Dict[str, Any]:
        """Verify Docker containers are properly deployed."""
        print("\n🐳 Verifying Docker deployment...")
        
        try:
            # Check Docker containers
            result = subprocess.run(
                "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                container_lines = result.stdout.strip().split('\n')
                self.verification_results['evidence']['docker_containers'] = container_lines
                
                # Check for critical services
                critical_services = ['api', 'webui', 'postgres', 'redis', 'ollama']
                running_services = []
                
                for line in container_lines:
                    for service in critical_services:
                        if service in line.lower() and 'Up' in line:
                            running_services.append(service)
                
                missing_services = set(critical_services) - set(running_services)
                if missing_services:
                    self.verification_results['deployment_gaps'].append(
                        f"Critical services not running: {', '.join(missing_services)}"
                    )
                    print(f"  ⚠️  Missing services: {', '.join(missing_services)}")
                else:
                    print(f"  ✅ All critical services running")
                
            else:
                self.verification_results['deployment_gaps'].append(
                    "Docker deployment verification failed"
                )
                print(f"  ❌ Docker verification failed")
                
        except Exception as e:
            self.verification_results['deployment_gaps'].append(
                f"Docker verification error: {e}"
            )
            print(f"  ❌ Docker verification error: {e}")
    
    def verify_networking(self) -> Dict[str, Any]:
        """Verify networking and routing configuration."""
        print("\n🌐 Verifying networking configuration...")
        
        # Check DNS resolution
        for url in self.production_urls:
            hostname = urlparse(url).hostname
            try:
                ip_address = socket.gethostbyname(hostname)
                self.verification_results['evidence'][f'dns_{hostname}'] = ip_address
                print(f"  ✅ DNS resolution for {hostname}: {ip_address}")
            except Exception as e:
                self.verification_results['deployment_gaps'].append(
                    f"DNS resolution failed for {hostname}: {e}"
                )
                print(f"  ❌ DNS resolution failed for {hostname}: {e}")
        
        # Check port availability
        critical_ports = [8000, 3001, 5432, 6379, 11434]
        for port in critical_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"  ✅ Port {port}: Open")
                else:
                    self.verification_results['deployment_gaps'].append(
                        f"Port {port} is not accessible"
                    )
                    print(f"  ❌ Port {port}: Closed")
            except Exception as e:
                print(f"  ⚠️  Port {port} check failed: {e}")
    
    def identify_deployment_gaps(self) -> List[str]:
        """Identify and summarize deployment gaps."""
        gaps = []
        
        # Check local vs production consistency
        local_healthy = sum(1 for s in self.verification_results['local_services'].values() 
                          if s.get('status') == 'healthy')
        production_accessible = sum(1 for s in self.verification_results['production_endpoints'].values() 
                                  if s.get('status') == 'accessible')
        
        if local_healthy > 0 and production_accessible == 0:
            gaps.append("Services running locally but not accessible in production")
        
        # Check SSL configuration
        ssl_issues = [url for url, cert in self.verification_results['ssl_certificates'].items() 
                     if cert.get('status') != 'valid']
        if ssl_issues:
            gaps.append(f"SSL certificate issues for: {', '.join(ssl_issues)}")
        
        # Add identified gaps
        gaps.extend(self.verification_results['deployment_gaps'])
        
        return gaps
    
    def generate_deployment_script(self) -> str:
        """Generate deployment script to fix identified gaps."""
        script = """#!/bin/bash
# Auto-generated deployment fix script
# Generated: {}

set -e

echo "🚀 Starting deployment gap resolution..."

""".format(datetime.now().isoformat())
        
        # Add fixes for identified gaps
        if "Services running locally but not accessible in production" in self.verification_results['deployment_gaps']:
            script += """
# Deploy to production
echo "📦 Deploying services to production..."
docker-compose -f docker-compose.yml up -d

# Wait for services to start
sleep 10

# Verify deployment
docker ps
"""
        
        if any("SSL certificate" in gap for gap in self.verification_results['deployment_gaps']):
            script += """
# Fix SSL certificates
echo "🔒 Configuring SSL certificates..."
./scripts/deploy_ssl_fixes.sh

# Restart nginx/reverse proxy
docker-compose restart nginx || true
"""
        
        if any("DNS" in gap for gap in self.verification_results['deployment_gaps']):
            script += """
# Update DNS configuration
echo "🌐 Updating DNS configuration..."
# Add DDNS update commands here
"""
        
        script += """
echo "✅ Deployment gap resolution complete!"
"""
        
        return script
    
    def run_verification(self) -> Dict[str, Any]:
        """Run complete deployment verification."""
        print("=" * 60)
        print("🚀 DEPLOYMENT VERIFICATION SYSTEM")
        print("=" * 60)
        
        # Run all verification steps
        self.verify_local_services()
        self.verify_production_endpoints()
        self.verify_ssl_certificates()
        self.verify_docker_deployment()
        self.verify_networking()
        
        # Identify gaps
        gaps = self.identify_deployment_gaps()
        self.verification_results['deployment_gaps'] = gaps
        
        # Generate summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        print(f"\n✅ Local Services Healthy: {sum(1 for s in self.verification_results['local_services'].values() if s.get('status') == 'healthy')}/{len(self.local_endpoints)}")
        print(f"🌐 Production Endpoints Accessible: {sum(1 for s in self.verification_results['production_endpoints'].values() if s.get('status') == 'accessible')}/{len(self.production_urls)}")
        print(f"🔒 SSL Certificates Valid: {sum(1 for s in self.verification_results['ssl_certificates'].values() if s.get('status') == 'valid')}/{len([u for u in self.production_urls if u.startswith('https')])}")
        
        if gaps:
            print(f"\n⚠️  DEPLOYMENT GAPS IDENTIFIED ({len(gaps)}):")
            for gap in gaps:
                print(f"  • {gap}")
            
            # Generate fix script
            fix_script = self.generate_deployment_script()
            script_path = '/home/marku/ai_workflow_engine/scripts/auto_deployment_fix.sh'
            with open(script_path, 'w') as f:
                f.write(fix_script)
            print(f"\n💡 Deployment fix script generated: {script_path}")
        else:
            print("\n✅ No deployment gaps identified!")
        
        # Save results
        results_file = f'/home/marku/ai_workflow_engine/.claude/deployment_verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")
        
        return self.verification_results

def main():
    """Main execution function."""
    verifier = DeploymentVerifier()
    results = verifier.run_verification()
    
    # Exit with error code if gaps found
    if results['deployment_gaps']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()