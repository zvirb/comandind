#!/usr/bin/env python3
"""
Real-Time System Health Monitoring Dashboard
Provides continuous visibility into AI Workflow Engine health status
"""

import subprocess
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import curses
from collections import deque

class SystemHealthMonitor:
    """Real-time monitoring dashboard for AIWFE"""
    
    def __init__(self):
        self.health_history = deque(maxlen=60)  # Last 60 checks
        self.alert_queue = deque(maxlen=20)
        self.metrics = {
            'uptime': 0,
            'last_incident': None,
            'recovery_count': 0,
            'validation_success_rate': 100.0
        }
    
    def check_docker_services(self) -> Dict[str, Dict]:
        """Check status of all Docker services"""
        services = {}
        
        try:
            # Get all containers
            result = subprocess.run(
                "docker ps -a --format '{{.Names}}|{{.Status}}|{{.State}}'",
                shell=True, capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        name = parts[0]
                        status = parts[1]
                        
                        # Determine health
                        healthy = 'Up' in status and ('healthy' in status or 'running' in status)
                        
                        services[name] = {
                            'status': status,
                            'healthy': healthy,
                            'needs_recovery': not healthy and any(
                                svc in name.lower() 
                                for svc in ['webui', 'backend', 'database', 'redis']
                            )
                        }
        except Exception as e:
            self.add_alert(f"Docker check error: {str(e)}", "ERROR")
        
        return services
    
    def check_production_endpoints(self) -> Dict[str, Dict]:
        """Check production endpoint accessibility"""
        endpoints = {
            'https://aiwfe.com': {'timeout': 5},
            'https://aiwfe.com/api/v1/health': {'timeout': 5},
            'http://localhost:3001/health': {'timeout': 3},
            'http://localhost:8000/health': {'timeout': 3}
        }
        
        results = {}
        
        for url, config in endpoints.items():
            try:
                result = subprocess.run(
                    f"curl -f -s -o /dev/null -w '%{{http_code}}|%{{time_total}}' --max-time {config['timeout']} {url}",
                    shell=True, capture_output=True, text=True
                )
                
                if '|' in result.stdout:
                    code, response_time = result.stdout.strip().split('|')
                    results[url] = {
                        'status_code': code,
                        'response_time': float(response_time),
                        'healthy': code == '200',
                        'accessible': code != '000'
                    }
                else:
                    results[url] = {
                        'status_code': '000',
                        'response_time': config['timeout'],
                        'healthy': False,
                        'accessible': False
                    }
                    
            except Exception as e:
                results[url] = {
                    'status_code': 'ERROR',
                    'response_time': 0,
                    'healthy': False,
                    'accessible': False,
                    'error': str(e)
                }
        
        return results
    
    def check_resource_usage(self) -> Dict[str, float]:
        """Check system resource usage"""
        resources = {}
        
        try:
            # CPU usage
            cpu_result = subprocess.run(
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1",
                shell=True, capture_output=True, text=True
            )
            resources['cpu_usage'] = float(cpu_result.stdout.strip() or 0)
            
            # Memory usage
            mem_result = subprocess.run(
                "free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2}'",
                shell=True, capture_output=True, text=True
            )
            resources['memory_usage'] = float(mem_result.stdout.strip() or 0)
            
            # Disk usage
            disk_result = subprocess.run(
                "df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1",
                shell=True, capture_output=True, text=True
            )
            resources['disk_usage'] = float(disk_result.stdout.strip() or 0)
            
            # Docker disk usage
            docker_result = subprocess.run(
                "docker system df --format 'json' | jq '.Images[0].Size' 2>/dev/null",
                shell=True, capture_output=True, text=True
            )
            if docker_result.stdout.strip():
                resources['docker_disk_mb'] = float(docker_result.stdout.strip()) / 1024 / 1024
            
        except Exception as e:
            self.add_alert(f"Resource check error: {str(e)}", "WARNING")
        
        return resources
    
    def check_recent_deployments(self) -> List[Dict]:
        """Check recent deployment status"""
        deployments = []
        
        try:
            # Check git log for recent deployments
            result = subprocess.run(
                "git log --oneline -10 --grep='deploy\\|Deploy' --since='24 hours ago'",
                shell=True, capture_output=True, text=True, cwd='/home/marku/ai_workflow_engine'
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        deployments.append({
                            'commit': parts[0],
                            'message': parts[1],
                            'time': 'recent'
                        })
        except:
            pass
        
        return deployments
    
    def add_alert(self, message: str, severity: str = "INFO"):
        """Add alert to queue"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'message': message
        }
        self.alert_queue.append(alert)
        
        # Log critical alerts
        if severity in ["ERROR", "CRITICAL"]:
            log_file = Path('.claude/logs/monitoring-alerts.log')
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(f"{json.dumps(alert)}\n")
    
    def calculate_health_score(self, services: Dict, endpoints: Dict) -> float:
        """Calculate overall system health score"""
        scores = []
        
        # Service health (40% weight)
        critical_services = ['webui', 'backend', 'database', 'redis']
        service_scores = []
        for name, info in services.items():
            if any(svc in name.lower() for svc in critical_services):
                service_scores.append(100 if info['healthy'] else 0)
        
        if service_scores:
            scores.append(sum(service_scores) / len(service_scores) * 0.4)
        
        # Endpoint health (40% weight)
        endpoint_scores = []
        for url, info in endpoints.items():
            if 'aiwfe.com' in url:  # Production endpoints have higher weight
                endpoint_scores.append(100 if info['healthy'] else 0)
                endpoint_scores.append(100 if info['healthy'] else 0)  # Double weight
            else:
                endpoint_scores.append(100 if info['healthy'] else 0)
        
        if endpoint_scores:
            scores.append(sum(endpoint_scores) / len(endpoint_scores) * 0.4)
        
        # Response time (20% weight)
        prod_endpoints = [e for u, e in endpoints.items() if 'aiwfe.com' in u]
        if prod_endpoints:
            avg_response = sum(e['response_time'] for e in prod_endpoints) / len(prod_endpoints)
            # Score based on response time (0-1s = 100%, 1-3s = 50%, >3s = 0%)
            if avg_response < 1:
                scores.append(20)
            elif avg_response < 3:
                scores.append(10)
            else:
                scores.append(0)
        
        return sum(scores) if scores else 0
    
    def display_dashboard(self, stdscr):
        """Display monitoring dashboard using curses"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)    # Non-blocking input
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Header
            header = "🔍 AI WORKFLOW ENGINE - REAL-TIME HEALTH MONITOR 🔍"
            stdscr.addstr(0, (width - len(header)) // 2, header, curses.A_BOLD)
            stdscr.addstr(1, 0, "=" * width)
            
            # Get current health data
            services = self.check_docker_services()
            endpoints = self.check_production_endpoints()
            resources = self.check_resource_usage()
            health_score = self.calculate_health_score(services, endpoints)
            
            # Update metrics
            self.metrics['uptime'] += 1
            if health_score < 50 and self.metrics['last_incident'] is None:
                self.metrics['last_incident'] = datetime.now()
                self.add_alert("System health degraded!", "WARNING")
            elif health_score >= 90 and self.metrics['last_incident']:
                self.metrics['last_incident'] = None
                self.metrics['recovery_count'] += 1
                self.add_alert("System recovered", "INFO")
            
            # Overall Health Score
            row = 3
            score_color = curses.color_pair(1) if health_score >= 80 else \
                         curses.color_pair(3) if health_score >= 50 else \
                         curses.color_pair(2)
            
            stdscr.addstr(row, 2, f"System Health Score: {health_score:.1f}%", score_color | curses.A_BOLD)
            stdscr.addstr(row, width - 30, f"Uptime: {self.metrics['uptime']} checks")
            row += 2
            
            # Docker Services
            stdscr.addstr(row, 2, "DOCKER SERVICES:", curses.A_BOLD)
            row += 1
            
            for name, info in list(services.items())[:10]:  # Limit display
                status_char = "✓" if info['healthy'] else "✗"
                color = curses.color_pair(1) if info['healthy'] else curses.color_pair(2)
                
                display_name = name[:30].ljust(30)
                status_text = info['status'][:40].ljust(40)
                
                stdscr.addstr(row, 4, f"{status_char} {display_name} {status_text}", color)
                row += 1
                
                if row >= height - 15:
                    break
            
            row += 1
            
            # Production Endpoints
            stdscr.addstr(row, 2, "PRODUCTION ENDPOINTS:", curses.A_BOLD)
            row += 1
            
            for url, info in endpoints.items():
                status_char = "✓" if info['healthy'] else "✗"
                color = curses.color_pair(1) if info['healthy'] else curses.color_pair(2)
                
                display_url = url[:40].ljust(40)
                response_info = f"[{info['status_code']}] {info['response_time']:.2f}s"
                
                stdscr.addstr(row, 4, f"{status_char} {display_url} {response_info}", color)
                row += 1
            
            row += 1
            
            # Resource Usage
            if resources and row < height - 8:
                stdscr.addstr(row, 2, "RESOURCE USAGE:", curses.A_BOLD)
                row += 1
                
                for resource, value in resources.items():
                    if isinstance(value, float):
                        color = curses.color_pair(1) if value < 70 else \
                               curses.color_pair(3) if value < 85 else \
                               curses.color_pair(2)
                        
                        display_name = resource.replace('_', ' ').title()
                        stdscr.addstr(row, 4, f"{display_name}: {value:.1f}%", color)
                        row += 1
            
            # Recent Alerts
            if self.alert_queue and row < height - 4:
                row = height - 8
                stdscr.addstr(row, 2, "RECENT ALERTS:", curses.A_BOLD)
                row += 1
                
                for alert in list(self.alert_queue)[-5:]:
                    severity_color = curses.color_pair(2) if alert['severity'] == "ERROR" else \
                                    curses.color_pair(3) if alert['severity'] == "WARNING" else \
                                    curses.color_pair(4)
                    
                    msg = f"[{alert['severity']}] {alert['message'][:60]}"
                    stdscr.addstr(row, 4, msg, severity_color)
                    row += 1
            
            # Footer
            stdscr.addstr(height - 2, 2, "Press 'q' to quit | 'r' to force refresh | Updates every 5s")
            stdscr.addstr(height - 1, 2, f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == ord('r'):
                continue
            
            # Wait 5 seconds or until key press
            for _ in range(50):
                if stdscr.getch() != -1:
                    break
                time.sleep(0.1)
    
    def run_dashboard(self):
        """Run the monitoring dashboard"""
        try:
            curses.wrapper(self.display_dashboard)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
        except Exception as e:
            print(f"Dashboard error: {str(e)}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Real-time System Health Monitor')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of dashboard')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    monitor = SystemHealthMonitor()
    
    if args.json or args.once:
        # Single check with JSON output
        services = monitor.check_docker_services()
        endpoints = monitor.check_production_endpoints()
        resources = monitor.check_resource_usage()
        health_score = monitor.calculate_health_score(services, endpoints)
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'health_score': health_score,
            'services': services,
            'endpoints': endpoints,
            'resources': resources,
            'metrics': monitor.metrics
        }
        
        print(json.dumps(output, indent=2))
    else:
        # Run interactive dashboard
        monitor.run_dashboard()

if __name__ == '__main__':
    main()