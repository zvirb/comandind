#!/usr/bin/env python3
"""
System Loop Pattern Detector
Analyzes cyclical patterns in the AI Workflow Engine that could cause WebUI looping
"""

import json
import time
import subprocess
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque

class SystemLoopDetector:
    def __init__(self):
        self.patterns = defaultdict(list)
        self.timing_analysis = {}
        self.containers = [
            'ai_workflow_engine-api-1',
            'ai_workflow_engine-webui-1', 
            'ai_workflow_engine-caddy_reverse_proxy-1',
            'ai_workflow_engine-redis-1',
            'ai_workflow_engine-postgres-1',
            'ai_workflow_engine-prometheus-1'
        ]
        
    def analyze_api_request_patterns(self):
        """Analyze API request timing patterns from logs"""
        print("🔍 Analyzing API Request Patterns...")
        
        try:
            # Get recent API logs
            result = subprocess.run([
                'docker', 'logs', 'ai_workflow_engine-api-1', 
                '--since=10m', '--timestamps'
            ], capture_output=True, text=True)
            
            # Parse request patterns
            session_validates = []
            dashboard_requests = []
            
            for line in result.stdout.split('\n'):
                if 'POST /api/v1/session/validate' in line:
                    timestamp = self.extract_timestamp(line)
                    if timestamp:
                        session_validates.append(timestamp)
                elif 'GET /api/v1/dashboard' in line:
                    timestamp = self.extract_timestamp(line)
                    if timestamp:
                        dashboard_requests.append(timestamp)
            
            # Calculate intervals
            session_intervals = self.calculate_intervals(session_validates)
            dashboard_intervals = self.calculate_intervals(dashboard_requests)
            
            self.patterns['api_session_validate'] = {
                'count': len(session_validates),
                'intervals': session_intervals[:10],  # Show first 10
                'avg_interval': sum(session_intervals) / len(session_intervals) if session_intervals else 0,
                'suspected_loop': len(session_intervals) > 50 and all(i < 1000 for i in session_intervals[:20])  # Less than 1 second apart
            }
            
            self.patterns['api_dashboard'] = {
                'count': len(dashboard_requests), 
                'intervals': dashboard_intervals[:10],
                'avg_interval': sum(dashboard_intervals) / len(dashboard_intervals) if dashboard_intervals else 0,
                'suspected_loop': len(dashboard_intervals) > 50 and all(i < 1000 for i in dashboard_intervals[:20])
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing API patterns: {e}")
            return False
    
    def analyze_health_check_cycles(self):
        """Analyze Docker health check timing"""
        print("🏥 Analyzing Health Check Cycles...")
        
        try:
            # Get recent docker events
            result = subprocess.run([
                'docker', 'events', '--since=10m', '--format', 'json'
            ], capture_output=True, text=True, timeout=5)
            
            health_checks = defaultdict(list)
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    try:
                        event = json.loads(line)
                        if event.get('Action', '').startswith('health_status'):
                            container = event.get('Actor', {}).get('Attributes', {}).get('name', 'unknown')
                            timestamp = event.get('time', 0)
                            health_checks[container].append(timestamp)
                    except:
                        continue
            
            for container, timestamps in health_checks.items():
                intervals = self.calculate_intervals(timestamps)
                self.patterns[f'health_check_{container}'] = {
                    'count': len(timestamps),
                    'intervals': intervals[:5],
                    'avg_interval': sum(intervals) / len(intervals) if intervals else 0
                }
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing health checks: {e}")
            return False
    
    def analyze_dns_resolution_issues(self):
        """Check for DNS resolution patterns in Caddy logs"""
        print("🌐 Analyzing DNS Resolution Patterns...")
        
        try:
            result = subprocess.run([
                'docker', 'logs', 'ai_workflow_engine-caddy_reverse_proxy-1',
                '--since=10m', '--timestamps'
            ], capture_output=True, text=True)
            
            dns_errors = []
            connection_refused = []
            
            for line in result.stdout.split('\n'):
                if 'server misbehaving' in line:
                    timestamp = self.extract_timestamp(line)
                    if timestamp:
                        dns_errors.append(timestamp)
                elif 'connection refused' in line:
                    timestamp = self.extract_timestamp(line)
                    if timestamp:
                        connection_refused.append(timestamp)
            
            dns_intervals = self.calculate_intervals(dns_errors)
            refused_intervals = self.calculate_intervals(connection_refused)
            
            self.patterns['caddy_dns_errors'] = {
                'count': len(dns_errors),
                'intervals': dns_intervals[:5],
                'suspected_dns_loop': len(dns_errors) > 10 and any(i < 30000 for i in dns_intervals[:10])  # Less than 30 seconds
            }
            
            self.patterns['caddy_connection_refused'] = {
                'count': len(connection_refused),
                'intervals': refused_intervals[:5],
                'suspected_connection_loop': len(connection_refused) > 10
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing DNS patterns: {e}")
            return False
    
    def analyze_prometheus_scraping(self):
        """Check Prometheus scraping patterns"""
        print("📊 Analyzing Prometheus Scraping Patterns...")
        
        try:
            result = subprocess.run([
                'docker', 'logs', 'ai_workflow_engine-prometheus-1',
                '--since=10m', '--timestamps'
            ], capture_output=True, text=True)
            
            scrape_errors = []
            
            for line in result.stdout.split('\n'):
                if 'error' in line.lower() and 'scrape' in line.lower():
                    timestamp = self.extract_timestamp(line)
                    if timestamp:
                        scrape_errors.append(timestamp)
            
            error_intervals = self.calculate_intervals(scrape_errors)
            
            self.patterns['prometheus_scrape_errors'] = {
                'count': len(scrape_errors),
                'intervals': error_intervals[:5],
                'suspected_scrape_loop': len(scrape_errors) > 20
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing Prometheus patterns: {e}")
            return False
    
    def extract_timestamp(self, log_line):
        """Extract timestamp from Docker log line"""
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)', log_line)
        if timestamp_match:
            try:
                ts = datetime.fromisoformat(timestamp_match.group(1).replace('Z', '+00:00'))
                return int(ts.timestamp() * 1000)  # Convert to milliseconds
            except:
                pass
        return None
    
    def calculate_intervals(self, timestamps):
        """Calculate intervals between timestamps in milliseconds"""
        if len(timestamps) < 2:
            return []
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals.append(interval)
        
        return intervals
    
    def detect_webui_loop_correlation(self):
        """Detect patterns that correlate with WebUI looping"""
        print("🔄 Analyzing WebUI Loop Correlation...")
        
        loop_indicators = []
        
        # Check API request frequency (key indicator)
        if self.patterns.get('api_session_validate', {}).get('suspected_loop'):
            loop_indicators.append({
                'type': 'HIGH_FREQUENCY_SESSION_VALIDATION',
                'severity': 'CRITICAL',
                'description': f"Session validation requests happening every {self.patterns['api_session_validate']['avg_interval']:.0f}ms",
                'evidence': f"{self.patterns['api_session_validate']['count']} requests in 10 minutes"
            })
        
        if self.patterns.get('api_dashboard', {}).get('suspected_loop'):
            loop_indicators.append({
                'type': 'HIGH_FREQUENCY_DASHBOARD_REQUESTS',
                'severity': 'CRITICAL', 
                'description': f"Dashboard requests happening every {self.patterns['api_dashboard']['avg_interval']:.0f}ms",
                'evidence': f"{self.patterns['api_dashboard']['count']} requests in 10 minutes"
            })
        
        # Check DNS issues
        if self.patterns.get('caddy_dns_errors', {}).get('suspected_dns_loop'):
            loop_indicators.append({
                'type': 'DNS_RESOLUTION_LOOP',
                'severity': 'HIGH',
                'description': "Frequent DNS resolution failures in load balancer",
                'evidence': f"{self.patterns['caddy_dns_errors']['count']} DNS errors"
            })
        
        return loop_indicators
    
    def generate_report(self):
        """Generate comprehensive loop analysis report"""
        print("📋 Generating System Loop Analysis Report...")
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'patterns_detected': self.patterns,
            'loop_indicators': self.detect_webui_loop_correlation(),
            'recommendations': []
        }
        
        # Generate recommendations based on findings
        if any(indicator['severity'] == 'CRITICAL' for indicator in report['loop_indicators']):
            report['recommendations'].extend([
                "IMMEDIATE ACTION: Frontend polling loop detected - check JavaScript timers and polling intervals",
                "Implement request debouncing in WebUI authentication components",
                "Add circuit breaker to session validation endpoint",
                "Review WebUI useEffect dependencies that might cause re-render loops"
            ])
        
        if self.patterns.get('caddy_dns_errors', {}).get('suspected_dns_loop'):
            report['recommendations'].append("Fix Docker DNS resolution issues in Caddy configuration")
        
        return report

def main():
    detector = SystemLoopDetector()
    
    print("🚀 Starting System Loop Pattern Analysis...")
    print("=" * 60)
    
    # Run all analyses
    analyses = [
        detector.analyze_api_request_patterns,
        detector.analyze_health_check_cycles, 
        detector.analyze_dns_resolution_issues,
        detector.analyze_prometheus_scraping
    ]
    
    for analysis in analyses:
        try:
            analysis()
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            continue
    
    # Generate and display report
    report = detector.generate_report()
    
    print("\n" + "=" * 60)
    print("📊 SYSTEM LOOP ANALYSIS RESULTS")
    print("=" * 60)
    
    if report['loop_indicators']:
        print("\n🚨 LOOP INDICATORS DETECTED:")
        for indicator in report['loop_indicators']:
            print(f"  ⚠️  {indicator['type']} ({indicator['severity']})")
            print(f"      {indicator['description']}")
            print(f"      Evidence: {indicator['evidence']}\n")
    else:
        print("\n✅ No obvious loop patterns detected")
    
    if report['recommendations']:
        print("💡 RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print("\n📁 Detailed patterns saved to: /tmp/system_loop_analysis.json")
    
    # Save detailed report
    with open('/tmp/system_loop_analysis.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

if __name__ == "__main__":
    main()