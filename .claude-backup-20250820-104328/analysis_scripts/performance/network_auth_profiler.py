#!/usr/bin/env python3
"""
Authentication Network Optimization Profiler
Analyzes network performance and identifies optimization opportunities for auth requests
"""

import subprocess
import time
import json
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import concurrent.futures
import requests

@dataclass 
class NetworkTimingData:
    """Network timing breakdown for a single request."""
    endpoint: str
    method: str
    namelookup_ms: float
    connect_ms: float
    appconnect_ms: float  # SSL handshake time
    pretransfer_ms: float
    redirect_ms: float
    starttransfer_ms: float  # Time to first byte (TTFB)
    total_ms: float
    http_code: int
    size_download: int
    timestamp: float

class NetworkAuthProfiler:
    """Profile network performance for authentication endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize network profiler."""
        self.base_url = base_url
        self.curl_template_path = ".claude/curl_timing_template.txt"
        self.results: List[NetworkTimingData] = []
        
    def profile_single_request(self, endpoint: str, method: str = "GET", data: Dict = None, headers: Dict = None) -> NetworkTimingData:
        """Profile network timing for a single request using curl."""
        url = self.base_url + endpoint
        
        # Build curl command
        curl_cmd = [
            "curl",
            "-w", f"@{self.curl_template_path}",
            "-o", "/dev/null",
            "-s",  # Silent mode
            "--max-time", "30"  # 30 second timeout
        ]
        
        # Add method-specific options
        if method.upper() == "POST":
            curl_cmd.extend(["-X", "POST"])
            if data:
                curl_cmd.extend(["-H", "Content-Type: application/json"])
                curl_cmd.extend(["-d", json.dumps(data)])
        elif method.upper() == "PUT":
            curl_cmd.extend(["-X", "PUT"])
            if data:
                curl_cmd.extend(["-H", "Content-Type: application/json"]) 
                curl_cmd.extend(["-d", json.dumps(data)])
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                curl_cmd.extend(["-H", f"{key}: {value}"])
        
        curl_cmd.append(url)
        
        try:
            # Execute curl command
            start_time = time.time()
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"Warning: curl failed for {endpoint}: {result.stderr}")
                return self._create_error_timing_data(endpoint, method, result.stderr)
            
            # Parse curl timing output
            timing_data = self._parse_curl_output(result.stdout, endpoint, method)
            timing_data.timestamp = start_time
            
            self.results.append(timing_data)
            return timing_data
            
        except subprocess.TimeoutExpired:
            print(f"Warning: Request to {endpoint} timed out")
            return self._create_error_timing_data(endpoint, method, "timeout")
        except Exception as e:
            print(f"Warning: Error profiling {endpoint}: {e}")
            return self._create_error_timing_data(endpoint, method, str(e))
    
    def _parse_curl_output(self, output: str, endpoint: str, method: str) -> NetworkTimingData:
        """Parse curl timing output into structured data."""
        lines = output.strip().split('\n')
        timings = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                try:
                    if key.startswith('time_'):
                        timings[key] = float(value) * 1000  # Convert seconds to milliseconds
                    elif key in ['http_code', 'size_download']:
                        timings[key] = int(value)
                except ValueError:
                    timings[key] = 0
        
        return NetworkTimingData(
            endpoint=endpoint,
            method=method,
            namelookup_ms=timings.get('time_namelookup', 0),
            connect_ms=timings.get('time_connect', 0),
            appconnect_ms=timings.get('time_appconnect', 0),
            pretransfer_ms=timings.get('time_pretransfer', 0),
            redirect_ms=timings.get('time_redirect', 0),
            starttransfer_ms=timings.get('time_starttransfer', 0),
            total_ms=timings.get('time_total', 0),
            http_code=timings.get('http_code', 0),
            size_download=timings.get('size_download', 0),
            timestamp=time.time()
        )
    
    def _create_error_timing_data(self, endpoint: str, method: str, error: str) -> NetworkTimingData:
        """Create error timing data for failed requests."""
        return NetworkTimingData(
            endpoint=endpoint,
            method=method,
            namelookup_ms=0,
            connect_ms=0,
            appconnect_ms=0,
            pretransfer_ms=0,
            redirect_ms=0,
            starttransfer_ms=0,
            total_ms=30000,  # Max timeout
            http_code=0,
            size_download=0,
            timestamp=time.time()
        )
    
    def profile_authentication_endpoints(self, iterations: int = 5) -> List[NetworkTimingData]:
        """Profile multiple authentication endpoints with multiple iterations."""
        print(f"=== AUTHENTICATION NETWORK PROFILING ({iterations} iterations per endpoint) ===\n")
        
        # Authentication endpoints to profile
        endpoints = [
            ("/health", "GET", None, None),  # Baseline
            ("/api/health", "GET", None, None),  # Baseline
            ("/api/v1/auth/status", "GET", None, None),
            ("/api/v1/user/current", "GET", None, None),
            ("/api/v1/auth/jwt/login", "POST", {"email": "test@example.com", "password": "test"}, None),
            ("/api/v1/auth/refresh", "POST", {}, {"Authorization": "Bearer fake-token"}),
            ("/api/v1/auth/logout", "POST", {}, {"Authorization": "Bearer fake-token"}),
            ("/ws/chat", "GET", None, None),  # WebSocket upgrade request
        ]
        
        results = []
        
        for endpoint, method, data, headers in endpoints:
            print(f"Profiling {method} {endpoint}...")
            endpoint_results = []
            
            for i in range(iterations):
                timing_data = self.profile_single_request(endpoint, method, data, headers)
                endpoint_results.append(timing_data)
                
                if timing_data.http_code == 0:
                    print(f"  Iteration {i+1}: ERROR")
                else:
                    print(f"  Iteration {i+1}: {timing_data.total_ms:.2f}ms (status: {timing_data.http_code})")
                
                # Brief pause between requests
                time.sleep(0.1)
            
            results.extend(endpoint_results)
            
            # Calculate statistics for this endpoint
            successful = [r for r in endpoint_results if r.http_code != 0]
            if successful:
                avg_total = statistics.mean([r.total_ms for r in successful])
                avg_ttfb = statistics.mean([r.starttransfer_ms for r in successful])
                print(f"  Average total: {avg_total:.2f}ms, Average TTFB: {avg_ttfb:.2f}ms")
            
            print()
        
        return results
    
    def profile_concurrent_requests(self, endpoint: str, concurrent_count: int = 10) -> List[NetworkTimingData]:
        """Profile concurrent requests to identify connection bottlenecks."""
        print(f"=== CONCURRENT REQUEST PROFILING ({concurrent_count} concurrent requests to {endpoint}) ===\n")
        
        def make_request():
            return self.profile_single_request(endpoint)
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_count)]
            concurrent_results = []
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                concurrent_results.append(result)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        successful = [r for r in concurrent_results if r.http_code != 0]
        if successful:
            avg_total = statistics.mean([r.total_ms for r in successful])
            max_total = max([r.total_ms for r in successful])
            min_total = min([r.total_ms for r in successful])
            
            print(f"Concurrent test completed in {total_duration:.2f} seconds")
            print(f"Successful requests: {len(successful)}/{concurrent_count}")
            print(f"Average response time: {avg_total:.2f}ms")
            print(f"Max response time: {max_total:.2f}ms")
            print(f"Min response time: {min_total:.2f}ms")
            print(f"Requests per second: {len(successful)/total_duration:.2f}")
        
        print()
        return concurrent_results
    
    def analyze_performance_bottlenecks(self) -> Dict[str, Any]:
        """Analyze timing data to identify performance bottlenecks."""
        if not self.results:
            return {"error": "No timing data available"}
        
        # Group results by endpoint
        by_endpoint = {}
        for result in self.results:
            key = f"{result.method} {result.endpoint}"
            if key not in by_endpoint:
                by_endpoint[key] = []
            by_endpoint[key].append(result)
        
        analysis = {
            "endpoint_analysis": {},
            "bottlenecks": [],
            "optimization_opportunities": []
        }
        
        # Analyze each endpoint
        for endpoint_key, endpoint_results in by_endpoint.items():
            successful = [r for r in endpoint_results if r.http_code != 0]
            
            if not successful:
                continue
            
            # Calculate statistics
            stats = {
                "count": len(successful),
                "avg_total_ms": statistics.mean([r.total_ms for r in successful]),
                "avg_ttfb_ms": statistics.mean([r.starttransfer_ms for r in successful]),
                "avg_connect_ms": statistics.mean([r.connect_ms for r in successful]),
                "avg_dns_ms": statistics.mean([r.namelookup_ms for r in successful]),
                "max_total_ms": max([r.total_ms for r in successful]),
                "min_total_ms": min([r.total_ms for r in successful]),
                "avg_size_bytes": statistics.mean([r.size_download for r in successful])
            }
            
            # Calculate breakdown percentages
            if stats["avg_total_ms"] > 0:
                stats["dns_percent"] = (stats["avg_dns_ms"] / stats["avg_total_ms"]) * 100
                stats["connect_percent"] = ((stats["avg_connect_ms"] - stats["avg_dns_ms"]) / stats["avg_total_ms"]) * 100
                stats["processing_percent"] = ((stats["avg_ttfb_ms"] - stats["avg_connect_ms"]) / stats["avg_total_ms"]) * 100
                stats["transfer_percent"] = ((stats["avg_total_ms"] - stats["avg_ttfb_ms"]) / stats["avg_total_ms"]) * 100
            
            analysis["endpoint_analysis"][endpoint_key] = stats
            
            # Identify bottlenecks
            if stats["avg_total_ms"] > 100:  # Slow endpoints (>100ms)
                analysis["bottlenecks"].append({
                    "type": "slow_endpoint",
                    "endpoint": endpoint_key,
                    "severity": "high" if stats["avg_total_ms"] > 500 else "medium",
                    "avg_response_time_ms": stats["avg_total_ms"],
                    "recommendation": "Optimize backend processing or add caching"
                })
            
            if stats["avg_ttfb_ms"] > 50:  # Slow server processing
                analysis["bottlenecks"].append({
                    "type": "slow_processing",
                    "endpoint": endpoint_key,
                    "severity": "high" if stats["avg_ttfb_ms"] > 200 else "medium",
                    "avg_ttfb_ms": stats["avg_ttfb_ms"],
                    "recommendation": "Optimize server-side processing, database queries, or middleware"
                })
            
            if stats["processing_percent"] > 80:  # Server processing dominates
                analysis["bottlenecks"].append({
                    "type": "processing_dominant",
                    "endpoint": endpoint_key,
                    "severity": "medium",
                    "processing_percent": stats["processing_percent"],
                    "recommendation": "Server processing dominates response time - investigate backend optimization"
                })
            
            if stats["connect_percent"] > 20:  # Connection overhead high
                analysis["bottlenecks"].append({
                    "type": "connection_overhead",
                    "endpoint": endpoint_key,
                    "severity": "medium",
                    "connection_percent": stats["connect_percent"],
                    "recommendation": "Consider connection keep-alive or HTTP/2 for reduced connection overhead"
                })
        
        return analysis
    
    def generate_optimization_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate specific optimization recommendations based on analysis."""
        recommendations = []
        
        # Generic recommendations based on patterns
        avg_response_times = [
            stats["avg_total_ms"] 
            for stats in analysis.get("endpoint_analysis", {}).values()
        ]
        
        if avg_response_times:
            overall_avg = statistics.mean(avg_response_times)
            
            if overall_avg > 50:
                recommendations.append({
                    "category": "general_performance",
                    "priority": "high",
                    "recommendation": "Implement authentication response time optimization",
                    "details": f"Average auth response time is {overall_avg:.2f}ms, target <30ms",
                    "implementation": "Add Redis caching for JWT validation, optimize database queries"
                })
            
            if overall_avg > 20:
                recommendations.append({
                    "category": "caching",
                    "priority": "medium", 
                    "recommendation": "Implement authentication result caching",
                    "details": "Cache authentication status and user data for faster subsequent requests",
                    "implementation": "Redis cache with 5-15 minute TTL for auth results"
                })
        
        # Connection optimization
        connection_issues = [b for b in analysis.get("bottlenecks", []) if "connection" in b["type"]]
        if connection_issues:
            recommendations.append({
                "category": "connection_optimization",
                "priority": "medium",
                "recommendation": "Optimize connection handling",
                "details": "Connection overhead detected in multiple endpoints",
                "implementation": "Enable HTTP keep-alive, implement connection pooling"
            })
        
        # Processing optimization
        processing_issues = [b for b in analysis.get("bottlenecks", []) if "processing" in b["type"]]
        if processing_issues:
            recommendations.append({
                "category": "backend_optimization",
                "priority": "high",
                "recommendation": "Optimize backend authentication processing",
                "details": "Server processing time dominates response times", 
                "implementation": "Optimize JWT decode, database queries, middleware stack"
            })
        
        # Endpoint-specific recommendations
        slow_endpoints = [b for b in analysis.get("bottlenecks", []) if b["type"] == "slow_endpoint"]
        if slow_endpoints:
            endpoints = [b["endpoint"] for b in slow_endpoints]
            recommendations.append({
                "category": "endpoint_optimization",
                "priority": "high",
                "recommendation": "Optimize slow authentication endpoints",
                "details": f"Slow endpoints identified: {', '.join(endpoints)}",
                "implementation": "Profile specific endpoints, add monitoring, implement optimizations"
            })
        
        return recommendations
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive network performance report."""
        print("Authentication Network Optimization Analysis")
        print("=" * 50)
        print()
        
        # Profile authentication endpoints
        endpoint_results = self.profile_authentication_endpoints(iterations=3)
        
        # Profile concurrent requests on key endpoint
        concurrent_results = self.profile_concurrent_requests("/api/v1/auth/status", concurrent_count=5)
        
        # Analyze performance bottlenecks
        bottleneck_analysis = self.analyze_performance_bottlenecks()
        
        # Generate optimization recommendations
        optimization_recommendations = self.generate_optimization_recommendations(bottleneck_analysis)
        
        # Compile comprehensive report
        report = {
            "timestamp": time.time(),
            "test_summary": {
                "endpoint_tests": len(endpoint_results),
                "concurrent_tests": len(concurrent_results),
                "total_requests": len(self.results)
            },
            "endpoint_profiling": endpoint_results,
            "concurrent_profiling": concurrent_results,
            "bottleneck_analysis": bottleneck_analysis,
            "optimization_recommendations": optimization_recommendations,
            "performance_targets": {
                "auth_response_time_target_ms": 30,
                "ttfb_target_ms": 20,
                "connection_time_target_ms": 5,
                "dns_lookup_target_ms": 1
            }
        }
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print summary of network performance analysis."""
        print("=== NETWORK PERFORMANCE SUMMARY ===\n")
        
        if "bottleneck_analysis" in report and "endpoint_analysis" in report["bottleneck_analysis"]:
            endpoint_analysis = report["bottleneck_analysis"]["endpoint_analysis"]
            
            # Calculate overall statistics
            all_avg_times = [stats["avg_total_ms"] for stats in endpoint_analysis.values()]
            all_ttfb_times = [stats["avg_ttfb_ms"] for stats in endpoint_analysis.values()]
            
            if all_avg_times:
                print(f"Endpoints analyzed: {len(endpoint_analysis)}")
                print(f"Average response time: {statistics.mean(all_avg_times):.2f}ms")
                print(f"Slowest endpoint: {max(all_avg_times):.2f}ms")
                print(f"Average TTFB: {statistics.mean(all_ttfb_times):.2f}ms")
            
            bottlenecks = report["bottleneck_analysis"].get("bottlenecks", [])
            high_priority_bottlenecks = [b for b in bottlenecks if b.get("severity") == "high"]
            print(f"Performance bottlenecks: {len(bottlenecks)}")
            print(f"High priority issues: {len(high_priority_bottlenecks)}")
        
        if "optimization_recommendations" in report:
            recommendations = report["optimization_recommendations"]
            high_priority = [r for r in recommendations if r.get("priority") == "high"]
            print(f"Optimization recommendations: {len(recommendations)}")
            print(f"High priority optimizations: {len(high_priority)}")
        
        print()

def main():
    """Main network profiling function."""
    # Initialize profiler
    profiler = NetworkAuthProfiler()
    
    # Generate comprehensive report
    report = profiler.generate_comprehensive_report()
    
    # Print summary
    profiler.print_summary(report)
    
    # Save detailed report
    import os
    report_file = ".claude/test_results/performance/auth_network_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Detailed report saved to: {report_file}")
    print("Network profiling complete.")

if __name__ == "__main__":
    main()