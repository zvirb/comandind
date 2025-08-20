#!/usr/bin/env python3
"""
API Polling Pattern Performance Profiler

Analyzes API polling patterns causing WebUI flickering, specifically:
- /api/v1/dashboard polling frequency and response times
- /api/v1/session/validate rapid polling patterns
- Resource utilization impact of frequent API calls
- Optimization opportunities for reduced flickering
"""

import asyncio
import aiohttp
import time
import json
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import psutil
import subprocess
from pathlib import Path

class APIPollingProfiler:
    def __init__(self, base_url="http://localhost", target_duration=300):
        self.base_url = base_url
        self.target_duration = target_duration  # 5 minutes default
        self.results = {
            "start_time": datetime.now().isoformat(),
            "dashboard_polling": {
                "requests": [],
                "response_times": [],
                "error_count": 0,
                "success_count": 0
            },
            "session_validate_polling": {
                "requests": [],
                "response_times": [],
                "error_count": 0,
                "success_count": 0
            },
            "health_check_polling": {
                "requests": [],
                "response_times": [],
                "error_count": 0,
                "success_count": 0
            },
            "resource_metrics": [],
            "analysis": {},
            "recommendations": []
        }
        self.session = None
        self.monitoring_active = False
        
    async def setup_session(self):
        """Setup HTTP session with appropriate timeouts"""
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
    async def cleanup_session(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            
    async def make_request(self, endpoint, method="GET", headers=None):
        """Make HTTP request and measure performance"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "POST":
                async with self.session.post(url, headers=headers or {}) as response:
                    response_time = (time.time() - start_time) * 1000
                    content = await response.text()
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "response_time_ms": response_time,
                        "status_code": response.status,
                        "success": response.status < 400,
                        "content_length": len(content),
                        "endpoint": endpoint
                    }
            else:
                async with self.session.get(url, headers=headers or {}) as response:
                    response_time = (time.time() - start_time) * 1000
                    content = await response.text()
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "response_time_ms": response_time,
                        "status_code": response.status,
                        "success": response.status < 400,
                        "content_length": len(content),
                        "endpoint": endpoint
                    }
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": response_time,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
    
    def collect_system_metrics(self):
        """Collect current system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network stats
            network = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "disk_percent": disk.percent,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "network_packets_sent": network.packets_sent,
                "network_packets_recv": network.packets_recv
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def simulate_dashboard_polling(self):
        """Simulate dashboard API polling patterns"""
        print("Starting dashboard polling simulation...")
        
        # Dashboard typically polls every 30 seconds when active
        poll_interval = 30
        
        while self.monitoring_active:
            # Dashboard data request
            dashboard_result = await self.make_request("/api/v1/dashboard")
            self.results["dashboard_polling"]["requests"].append(dashboard_result)
            
            if dashboard_result["success"]:
                self.results["dashboard_polling"]["success_count"] += 1
                self.results["dashboard_polling"]["response_times"].append(dashboard_result["response_time_ms"])
            else:
                self.results["dashboard_polling"]["error_count"] += 1
            
            # Performance dashboard request (often combined)
            perf_result = await self.make_request("/api/v1/performance_dashboard")
            if perf_result["success"]:
                self.results["dashboard_polling"]["response_times"].append(perf_result["response_time_ms"])
            
            await asyncio.sleep(poll_interval)
    
    async def simulate_session_validation_polling(self):
        """Simulate session validation polling patterns"""
        print("Starting session validation polling simulation...")
        
        # Session validation often happens more frequently
        # Based on AuthContext.jsx: throttleInterval = 5m for regular, but UI may poll more frequently
        poll_interval = 18  # Every 18 seconds (rapid polling that causes flickering)
        
        while self.monitoring_active:
            # Session validation request
            session_result = await self.make_request(
                "/api/v1/session/validate", 
                method="POST",
                headers={"Content-Type": "application/json"}
            )
            
            self.results["session_validate_polling"]["requests"].append(session_result)
            
            if session_result["success"]:
                self.results["session_validate_polling"]["success_count"] += 1
                self.results["session_validate_polling"]["response_times"].append(session_result["response_time_ms"])
            else:
                self.results["session_validate_polling"]["error_count"] += 1
            
            await asyncio.sleep(poll_interval)
    
    async def simulate_health_check_polling(self):
        """Simulate health check polling patterns"""
        print("Starting health check polling simulation...")
        
        # Health checks for integration status
        poll_interval = 45  # Every 45 seconds
        
        while self.monitoring_active:
            health_result = await self.make_request("/api/v1/health/integration")
            self.results["health_check_polling"]["requests"].append(health_result)
            
            if health_result["success"]:
                self.results["health_check_polling"]["success_count"] += 1
                self.results["health_check_polling"]["response_times"].append(health_result["response_time_ms"])
            else:
                self.results["health_check_polling"]["error_count"] += 1
            
            await asyncio.sleep(poll_interval)
    
    async def monitor_system_resources(self):
        """Monitor system resource usage during polling"""
        print("Starting system resource monitoring...")
        
        while self.monitoring_active:
            metrics = self.collect_system_metrics()
            self.results["resource_metrics"].append(metrics)
            await asyncio.sleep(5)  # Collect metrics every 5 seconds
    
    def analyze_results(self):
        """Analyze polling patterns and performance metrics"""
        print("Analyzing polling performance results...")
        
        analysis = {}
        
        # Analyze dashboard polling
        if self.results["dashboard_polling"]["response_times"]:
            dashboard_times = self.results["dashboard_polling"]["response_times"]
            analysis["dashboard_polling"] = {
                "total_requests": len(self.results["dashboard_polling"]["requests"]),
                "success_rate": self.results["dashboard_polling"]["success_count"] / len(self.results["dashboard_polling"]["requests"]) * 100,
                "avg_response_time_ms": statistics.mean(dashboard_times),
                "median_response_time_ms": statistics.median(dashboard_times),
                "p95_response_time_ms": self.percentile(dashboard_times, 95),
                "p99_response_time_ms": self.percentile(dashboard_times, 99),
                "min_response_time_ms": min(dashboard_times),
                "max_response_time_ms": max(dashboard_times)
            }
        
        # Analyze session validation polling
        if self.results["session_validate_polling"]["response_times"]:
            session_times = self.results["session_validate_polling"]["response_times"]
            analysis["session_validation_polling"] = {
                "total_requests": len(self.results["session_validate_polling"]["requests"]),
                "success_rate": self.results["session_validate_polling"]["success_count"] / len(self.results["session_validate_polling"]["requests"]) * 100,
                "avg_response_time_ms": statistics.mean(session_times),
                "median_response_time_ms": statistics.median(session_times),
                "p95_response_time_ms": self.percentile(session_times, 95),
                "p99_response_time_ms": self.percentile(session_times, 99),
                "min_response_time_ms": min(session_times),
                "max_response_time_ms": max(session_times),
                "requests_per_minute": len(self.results["session_validate_polling"]["requests"]) / (self.target_duration / 60)
            }
        
        # Analyze health check polling
        if self.results["health_check_polling"]["response_times"]:
            health_times = self.results["health_check_polling"]["response_times"]
            analysis["health_check_polling"] = {
                "total_requests": len(self.results["health_check_polling"]["requests"]),
                "success_rate": self.results["health_check_polling"]["success_count"] / len(self.results["health_check_polling"]["requests"]) * 100,
                "avg_response_time_ms": statistics.mean(health_times),
                "median_response_time_ms": statistics.median(health_times),
                "p95_response_time_ms": self.percentile(health_times, 95),
                "p99_response_time_ms": self.percentile(health_times, 99)
            }
        
        # Analyze resource utilization
        if self.results["resource_metrics"]:
            cpu_values = [m["cpu_percent"] for m in self.results["resource_metrics"] if "cpu_percent" in m]
            memory_values = [m["memory_percent"] for m in self.results["resource_metrics"] if "memory_percent" in m]
            
            if cpu_values and memory_values:
                analysis["resource_utilization"] = {
                    "avg_cpu_percent": statistics.mean(cpu_values),
                    "max_cpu_percent": max(cpu_values),
                    "avg_memory_percent": statistics.mean(memory_values),
                    "max_memory_percent": max(memory_values),
                    "samples_collected": len(self.results["resource_metrics"])
                }
        
        # Calculate polling frequencies
        analysis["polling_frequencies"] = {
            "session_validate_frequency_seconds": 18,  # Based on simulation
            "dashboard_frequency_seconds": 30,  # Based on simulation
            "health_check_frequency_seconds": 45,  # Based on simulation
            "total_requests_per_minute": 0
        }
        
        # Calculate total request load
        total_requests = sum([
            len(self.results["dashboard_polling"]["requests"]),
            len(self.results["session_validate_polling"]["requests"]),
            len(self.results["health_check_polling"]["requests"])
        ])
        
        analysis["polling_frequencies"]["total_requests_per_minute"] = total_requests / (self.target_duration / 60)
        
        self.results["analysis"] = analysis
        return analysis
    
    def percentile(self, data, percent):
        """Calculate percentile of data"""
        if not data:
            return 0
        data_sorted = sorted(data)
        k = (len(data_sorted) - 1) * percent / 100
        f = int(k)
        c = k - f
        if f == len(data_sorted) - 1:
            return data_sorted[f]
        return data_sorted[f] * (1 - c) + data_sorted[f + 1] * c
    
    def generate_recommendations(self):
        """Generate optimization recommendations"""
        recommendations = []
        analysis = self.results["analysis"]
        
        # Session validation optimization
        if "session_validation_polling" in analysis:
            session_data = analysis["session_validation_polling"]
            
            if session_data["requests_per_minute"] > 3:  # More than 3 requests per minute
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Session Validation Optimization",
                    "issue": f"Session validation polling at {session_data['requests_per_minute']:.1f} requests/minute is excessive",
                    "recommendation": "Increase session validation interval from 18s to 60s minimum",
                    "expected_improvement": "60-80% reduction in session validation requests"
                })
            
            if session_data["avg_response_time_ms"] > 100:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Session Validation Performance",
                    "issue": f"Average session validation response time of {session_data['avg_response_time_ms']:.1f}ms is causing UI delays",
                    "recommendation": "Implement Redis caching for session validation to achieve <50ms response times",
                    "expected_improvement": "50% reduction in response times"
                })
        
        # Dashboard polling optimization
        if "dashboard_polling" in analysis:
            dashboard_data = analysis["dashboard_polling"]
            
            if dashboard_data["avg_response_time_ms"] > 200:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Dashboard Performance",
                    "issue": f"Dashboard response time of {dashboard_data['avg_response_time_ms']:.1f}ms impacts user experience",
                    "recommendation": "Implement dashboard data caching and reduce payload size",
                    "expected_improvement": "40% faster dashboard loading"
                })
        
        # Overall polling strategy
        total_rpm = analysis.get("polling_frequencies", {}).get("total_requests_per_minute", 0)
        if total_rpm > 10:
            recommendations.append({
                "priority": "HIGH",
                "category": "Overall Polling Strategy",
                "issue": f"Total API polling rate of {total_rpm:.1f} requests/minute creates excessive load",
                "recommendation": "Implement WebSocket-based real-time updates for frequently changing data",
                "expected_improvement": "70-80% reduction in API polling requests"
            })
        
        # Resource utilization
        if "resource_utilization" in analysis:
            resource_data = analysis["resource_utilization"]
            if resource_data["avg_cpu_percent"] > 80:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Resource Optimization",
                    "issue": f"High CPU utilization ({resource_data['avg_cpu_percent']:.1f}%) during polling",
                    "recommendation": "Optimize API endpoint processing and implement request batching",
                    "expected_improvement": "25% reduction in CPU usage"
                })
        
        self.results["recommendations"] = recommendations
        return recommendations
    
    async def run_profiling(self):
        """Run complete API polling performance profiling"""
        print(f"Starting API Polling Performance Profiler for {self.target_duration} seconds...")
        print(f"Base URL: {self.base_url}")
        
        await self.setup_session()
        
        try:
            self.monitoring_active = True
            
            # Start all monitoring tasks
            tasks = [
                asyncio.create_task(self.simulate_dashboard_polling()),
                asyncio.create_task(self.simulate_session_validation_polling()),
                asyncio.create_task(self.simulate_health_check_polling()),
                asyncio.create_task(self.monitor_system_resources())
            ]
            
            # Run for specified duration
            await asyncio.sleep(self.target_duration)
            
            # Stop monitoring
            self.monitoring_active = False
            
            # Cancel tasks
            for task in tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            await self.cleanup_session()
        
        # Analyze results
        self.analyze_results()
        self.generate_recommendations()
        
        print("Profiling completed. Generating report...")
        return self.results
    
    def save_results(self, filename=None):
        """Save profiling results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/marku/ai_workflow_engine/.claude/test_results/performance/api_polling_profile_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"Results saved to: {filename}")
        return filename

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='API Polling Performance Profiler')
    parser.add_argument('--base-url', default='http://localhost', help='Base URL for API requests')
    parser.add_argument('--duration', type=int, default=300, help='Profiling duration in seconds')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    async def run_profiler():
        profiler = APIPollingProfiler(args.base_url, args.duration)
        results = await profiler.run_profiling()
        
        # Save results
        output_file = profiler.save_results(args.output)
        
        # Print summary
        print("\n" + "="*60)
        print("API POLLING PERFORMANCE PROFILER SUMMARY")
        print("="*60)
        
        analysis = results["analysis"]
        
        if "session_validation_polling" in analysis:
            sv = analysis["session_validation_polling"]
            print(f"\nSESSION VALIDATION POLLING:")
            print(f"  Total Requests: {sv['total_requests']}")
            print(f"  Success Rate: {sv['success_rate']:.1f}%")
            print(f"  Avg Response Time: {sv['avg_response_time_ms']:.1f}ms")
            print(f"  95th Percentile: {sv['p95_response_time_ms']:.1f}ms")
            print(f"  Requests/Minute: {sv['requests_per_minute']:.1f}")
        
        if "dashboard_polling" in analysis:
            dp = analysis["dashboard_polling"]
            print(f"\nDASHBOARD POLLING:")
            print(f"  Total Requests: {dp['total_requests']}")
            print(f"  Success Rate: {dp['success_rate']:.1f}%")
            print(f"  Avg Response Time: {dp['avg_response_time_ms']:.1f}ms")
            print(f"  95th Percentile: {dp['p95_response_time_ms']:.1f}ms")
        
        if "resource_utilization" in analysis:
            ru = analysis["resource_utilization"]
            print(f"\nRESOURCE UTILIZATION:")
            print(f"  Avg CPU: {ru['avg_cpu_percent']:.1f}%")
            print(f"  Max CPU: {ru['max_cpu_percent']:.1f}%")
            print(f"  Avg Memory: {ru['avg_memory_percent']:.1f}%")
        
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. [{rec['priority']}] {rec['category']}")
            print(f"     Issue: {rec['issue']}")
            print(f"     Fix: {rec['recommendation']}")
            print(f"     Impact: {rec['expected_improvement']}")
            print()
        
        print(f"Full results saved to: {output_file}")
    
    asyncio.run(run_profiler())

if __name__ == "__main__":
    main()