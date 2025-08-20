#!/usr/bin/env python3
"""
Authentication Performance Analysis Script
Analyzes performance bottlenecks in authentication system.
"""
import os
import sys
import time
import psutil
import asyncio
import requests
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from urllib.parse import urljoin

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    operation: str
    duration_ms: float
    status_code: int
    error: str = None

class AuthenticationPerformanceProfiler:
    """Profiles authentication system performance."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize profiler with base URL."""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
        
    def measure_route_resolution(self, path: str) -> PerformanceMetric:
        """Measure route resolution performance."""
        url = urljoin(self.base_url, path)
        
        start_time = time.perf_counter()
        try:
            response = self.session.options(url)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return PerformanceMetric(
                operation=f"Route resolution: {path}",
                duration_ms=duration_ms,
                status_code=response.status_code
            )
        except Exception as e:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return PerformanceMetric(
                operation=f"Route resolution: {path}",
                duration_ms=duration_ms,
                status_code=0,
                error=str(e)
            )
    
    def measure_auth_endpoint(self, path: str, method: str = "GET") -> PerformanceMetric:
        """Measure authentication endpoint performance."""
        url = urljoin(self.base_url, path)
        
        start_time = time.perf_counter()
        try:
            if method.upper() == "POST":
                response = self.session.post(url, json={})
            else:
                response = self.session.get(url)
                
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return PerformanceMetric(
                operation=f"{method} {path}",
                duration_ms=duration_ms,
                status_code=response.status_code
            )
        except Exception as e:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return PerformanceMetric(
                operation=f"{method} {path}",
                duration_ms=duration_ms,
                status_code=0,
                error=str(e)
            )
    
    def analyze_authentication_routers(self) -> Dict[str, List[PerformanceMetric]]:
        """Analyze performance of all authentication routers."""
        results = {}
        
        # Authentication router prefixes (8 identified routers)
        auth_routers = {
            "custom_auth_router_v1": "/api/v1/auth",
            "secure_auth_router": "/api/v1/auth", 
            "custom_auth_router_legacy": "/api/auth",
            "custom_auth_router_production": "/auth",
            "oauth_router": "/api/v1/oauth",
            "two_factor_auth_router": "/api/v1/2fa",
            "enhanced_auth_router": "/api/v1",
            "webauthn_router": "/api/v1",
            "debug_auth_router": "/api/v1",
            "native_auth_router": "/native"
        }
        
        print("=== AUTHENTICATION ROUTER PERFORMANCE ANALYSIS ===\n")
        
        for router_name, prefix in auth_routers.items():
            print(f"Analyzing {router_name} ({prefix})...")
            metrics = []
            
            # Test route resolution performance
            test_paths = [
                f"{prefix}/health",
                f"{prefix}/test", 
                f"{prefix}/login",
                f"{prefix}/status"
            ]
            
            for path in test_paths:
                metric = self.measure_route_resolution(path)
                metrics.append(metric)
                
                if metric.error:
                    print(f"  {path}: {metric.duration_ms:.2f}ms (ERROR: {metric.error[:50]})")
                else:
                    print(f"  {path}: {metric.duration_ms:.2f}ms (status: {metric.status_code})")
            
            results[router_name] = metrics
            print()
        
        return results
    
    def analyze_jwt_performance(self) -> List[PerformanceMetric]:
        """Analyze JWT token performance."""
        print("=== JWT TOKEN PERFORMANCE ANALYSIS ===\n")
        
        metrics = []
        jwt_endpoints = [
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/refresh", 
            "/api/v1/auth/token",
            "/api/v1/auth/logout"
        ]
        
        for endpoint in jwt_endpoints:
            print(f"Testing JWT endpoint: {endpoint}")
            
            # Test GET performance
            get_metric = self.measure_auth_endpoint(endpoint, "GET")
            metrics.append(get_metric)
            
            if get_metric.error:
                print(f"  GET: {get_metric.duration_ms:.2f}ms (ERROR: {get_metric.error[:50]})")
            else:
                print(f"  GET: {get_metric.duration_ms:.2f}ms (status: {get_metric.status_code})")
            
            # Test POST performance  
            post_metric = self.measure_auth_endpoint(endpoint, "POST")
            metrics.append(post_metric)
            
            if post_metric.error:
                print(f"  POST: {post_metric.duration_ms:.2f}ms (ERROR: {post_metric.error[:50]})")
            else:
                print(f"  POST: {post_metric.duration_ms:.2f}ms (status: {post_metric.status_code})")
            
            print()
        
        return metrics
    
    def analyze_session_performance(self) -> List[PerformanceMetric]:
        """Analyze session management performance."""
        print("=== SESSION MANAGEMENT PERFORMANCE ANALYSIS ===\n")
        
        metrics = []
        session_endpoints = [
            "/api/v1/user/current",
            "/api/v1/auth/status",
            "/health",
            "/api/health"
        ]
        
        for endpoint in session_endpoints:
            print(f"Testing session endpoint: {endpoint}")
            
            metric = self.measure_auth_endpoint(endpoint, "GET")
            metrics.append(metric)
            
            if metric.error:
                print(f"  {metric.duration_ms:.2f}ms (ERROR: {metric.error[:50]})")
            else:
                print(f"  {metric.duration_ms:.2f}ms (status: {metric.status_code})")
            print()
        
        return metrics
    
    def analyze_websocket_auth_performance(self) -> List[PerformanceMetric]:
        """Analyze WebSocket authentication performance."""
        print("=== WEBSOCKET AUTHENTICATION PERFORMANCE ANALYSIS ===\n")
        
        metrics = []
        websocket_endpoints = [
            "/ws/chat",
            "/ws/debug", 
            "/api/v1/chat/ws",
            "/ws/v2/secure/agent",
            "/ws/v2/secure/helios",
            "/ws/v2/secure/monitoring"
        ]
        
        for endpoint in websocket_endpoints:
            print(f"Testing WebSocket endpoint: {endpoint}")
            
            # Test HTTP upgrade request performance
            metric = self.measure_auth_endpoint(endpoint, "GET")
            metrics.append(metric)
            
            if metric.error:
                print(f"  {metric.duration_ms:.2f}ms (ERROR: {metric.error[:50]})")
            else:
                print(f"  {metric.duration_ms:.2f}ms (status: {metric.status_code})")
            print()
        
        return metrics
    
    def generate_performance_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "timestamp": time.time(),
            "summary": {},
            "bottlenecks": [],
            "recommendations": [],
            "detailed_metrics": results
        }
        
        # Calculate summary statistics
        all_metrics = []
        for category_metrics in results.values():
            if isinstance(category_metrics, list):
                all_metrics.extend(category_metrics)
            elif isinstance(category_metrics, dict):
                for router_metrics in category_metrics.values():
                    all_metrics.extend(router_metrics)
        
        if all_metrics:
            durations = [m.duration_ms for m in all_metrics if not m.error]
            if durations:
                report["summary"] = {
                    "total_tests": len(all_metrics),
                    "successful_tests": len(durations),
                    "failed_tests": len(all_metrics) - len(durations),
                    "avg_response_time_ms": sum(durations) / len(durations),
                    "max_response_time_ms": max(durations),
                    "min_response_time_ms": min(durations)
                }
                
                # Identify bottlenecks (>500ms)
                slow_metrics = [m for m in all_metrics if not m.error and m.duration_ms > 500]
                report["bottlenecks"] = [
                    {"operation": m.operation, "duration_ms": m.duration_ms}
                    for m in slow_metrics
                ]
                
                # Generate recommendations
                report["recommendations"] = self.generate_recommendations(all_metrics)
        
        return report
    
    def generate_recommendations(self, metrics: List[PerformanceMetric]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Analyze response times
        durations = [m.duration_ms for m in metrics if not m.error]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            if avg_duration > 200:
                recommendations.append("Average response time exceeds 200ms - consider router optimization")
            
            if max_duration > 1000:
                recommendations.append("Maximum response time exceeds 1s - investigate slowest endpoints")
        
        # Analyze errors
        error_count = len([m for m in metrics if m.error])
        if error_count > 0:
            recommendations.append(f"Found {error_count} errors - investigate authentication failures")
        
        # Check for router conflicts
        router_paths = {}
        for metric in metrics:
            if "Route resolution" in metric.operation:
                path = metric.operation.split(": ")[1]
                prefix = "/".join(path.split("/")[:3])
                if prefix not in router_paths:
                    router_paths[prefix] = []
                router_paths[prefix].append(metric.duration_ms)
        
        # Look for overlapping prefixes with different performance
        overlapping_prefixes = [prefix for prefix in router_paths.keys() if prefix.count("/") >= 2]
        if len(overlapping_prefixes) > 5:
            recommendations.append("Multiple overlapping router prefixes detected - consider router consolidation")
        
        return recommendations

def main():
    """Main performance analysis function."""
    print("Authentication Performance Analysis")
    print("=" * 50)
    print()
    
    # Initialize profiler
    profiler = AuthenticationPerformanceProfiler()
    
    # Check if API is accessible
    try:
        response = profiler.session.get(profiler.base_url + "/health", timeout=5)
        if response.status_code != 200:
            print(f"WARNING: API health check failed (status: {response.status_code})")
        else:
            print("API is accessible - starting performance analysis...")
            print()
    except Exception as e:
        print(f"ERROR: Cannot connect to API at {profiler.base_url}")
        print(f"Error: {e}")
        print("Make sure the API is running and accessible.")
        return
    
    # Collect performance data
    results = {}
    
    # 1. Authentication router analysis
    results["auth_routers"] = profiler.analyze_authentication_routers()
    
    # 2. JWT performance analysis
    results["jwt_performance"] = profiler.analyze_jwt_performance()
    
    # 3. Session management analysis
    results["session_performance"] = profiler.analyze_session_performance()
    
    # 4. WebSocket authentication analysis
    results["websocket_performance"] = profiler.analyze_websocket_auth_performance()
    
    # Generate comprehensive report
    report = profiler.generate_performance_report(results)
    
    # Print summary
    print("=== PERFORMANCE ANALYSIS SUMMARY ===\n")
    if report["summary"]:
        summary = report["summary"]
        print(f"Total tests: {summary['total_tests']}")
        print(f"Successful tests: {summary['successful_tests']}")
        print(f"Failed tests: {summary['failed_tests']}")
        print(f"Average response time: {summary['avg_response_time_ms']:.2f}ms")
        print(f"Maximum response time: {summary['max_response_time_ms']:.2f}ms")
        print(f"Minimum response time: {summary['min_response_time_ms']:.2f}ms")
        print()
        
        if report["bottlenecks"]:
            print("PERFORMANCE BOTTLENECKS:")
            for bottleneck in report["bottlenecks"]:
                print(f"  - {bottleneck['operation']}: {bottleneck['duration_ms']:.2f}ms")
            print()
        
        if report["recommendations"]:
            print("OPTIMIZATION RECOMMENDATIONS:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")
            print()
    
    # Save detailed report
    report_file = "auth_performance_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Detailed report saved to: {report_file}")
    print("Performance analysis complete.")

if __name__ == "__main__":
    main()