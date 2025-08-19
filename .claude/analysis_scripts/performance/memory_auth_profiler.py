#!/usr/bin/env python3
"""
Authentication Memory Usage Profiler
Identifies memory leaks and optimization opportunities in authentication flows
"""

import psutil
import time
import requests
import asyncio
import json
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess
import os

@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time."""
    timestamp: float
    process_memory_mb: float
    system_memory_percent: float
    cpu_percent: float
    active_connections: int
    open_files: int
    threads: int
    operation: str

class AuthenticationMemoryProfiler:
    """Profile memory usage during authentication operations."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize memory profiler."""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring = False
        
    def take_memory_snapshot(self, operation: str = "unknown") -> MemorySnapshot:
        """Take a memory usage snapshot."""
        try:
            # Get current process info
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            connections = len(process.connections())
            open_files = len(process.open_files())
            threads = process.num_threads()
            
            # Get system memory
            system_memory = psutil.virtual_memory()
            
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                process_memory_mb=memory_info.rss / 1024 / 1024,  # Convert bytes to MB
                system_memory_percent=system_memory.percent,
                cpu_percent=cpu_percent,
                active_connections=connections,
                open_files=open_files,
                threads=threads,
                operation=operation
            )
            
            self.snapshots.append(snapshot)
            return snapshot
            
        except Exception as e:
            print(f"Warning: Could not take memory snapshot: {e}")
            return MemorySnapshot(
                timestamp=time.time(),
                process_memory_mb=0,
                system_memory_percent=0,
                cpu_percent=0,
                active_connections=0,
                open_files=0,
                threads=0,
                operation=operation
            )
    
    def start_continuous_monitoring(self, interval: float = 0.5) -> threading.Thread:
        """Start continuous memory monitoring in background thread."""
        self.monitoring = True
        
        def monitor():
            while self.monitoring:
                self.take_memory_snapshot("continuous_monitoring")
                time.sleep(interval)
                
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        return monitor_thread
    
    def stop_continuous_monitoring(self):
        """Stop continuous memory monitoring."""
        self.monitoring = False
    
    def profile_authentication_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Profile memory usage for a single authentication request."""
        # Take pre-request snapshot
        pre_snapshot = self.take_memory_snapshot(f"pre_{method}_{endpoint}")
        
        start_time = time.time()
        try:
            url = self.base_url + endpoint
            
            if method.upper() == "POST":
                response = self.session.post(url, json=data or {})
            else:
                response = self.session.get(url)
                
            end_time = time.time()
            
            # Take post-request snapshot
            post_snapshot = self.take_memory_snapshot(f"post_{method}_{endpoint}")
            
            # Calculate memory delta
            memory_delta = post_snapshot.process_memory_mb - pre_snapshot.process_memory_mb
            
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "duration_ms": (end_time - start_time) * 1000,
                "memory_delta_mb": memory_delta,
                "pre_memory_mb": pre_snapshot.process_memory_mb,
                "post_memory_mb": post_snapshot.process_memory_mb,
                "connection_delta": post_snapshot.active_connections - pre_snapshot.active_connections,
                "files_delta": post_snapshot.open_files - pre_snapshot.open_files,
                "success": True
            }
            
        except Exception as e:
            end_time = time.time()
            post_snapshot = self.take_memory_snapshot(f"error_{method}_{endpoint}")
            
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "duration_ms": (end_time - start_time) * 1000,
                "memory_delta_mb": post_snapshot.process_memory_mb - pre_snapshot.process_memory_mb,
                "pre_memory_mb": pre_snapshot.process_memory_mb,
                "post_memory_mb": post_snapshot.process_memory_mb,
                "connection_delta": post_snapshot.active_connections - pre_snapshot.active_connections,
                "files_delta": post_snapshot.open_files - pre_snapshot.open_files,
                "error": str(e),
                "success": False
            }
    
    def profile_authentication_loop(self, iterations: int = 10) -> List[Dict[str, Any]]:
        """Profile memory usage during repeated authentication operations to detect leaks."""
        print(f"=== AUTHENTICATION LOOP MEMORY PROFILING ({iterations} iterations) ===\\n")
        
        results = []
        
        # Authentication endpoints to test
        endpoints = [
            ("/api/v1/auth/jwt/login", "POST", {"email": "test@example.com", "password": "test"}),
            ("/api/v1/auth/refresh", "POST", {}),
            ("/api/v1/auth/status", "GET", None),
            ("/api/v1/user/current", "GET", None),
            ("/health", "GET", None)
        ]
        
        initial_snapshot = self.take_memory_snapshot("loop_start")
        print(f"Initial memory: {initial_snapshot.process_memory_mb:.2f} MB\\n")
        
        for i in range(iterations):
            print(f"Iteration {i+1}/{iterations}")
            iteration_results = []
            
            for endpoint, method, data in endpoints:
                result = self.profile_authentication_request(endpoint, method, data)
                iteration_results.append(result)
                
                # Log significant memory increases
                if result["memory_delta_mb"] > 1.0:  # More than 1MB increase
                    print(f"  WARNING: {endpoint} increased memory by {result['memory_delta_mb']:.2f} MB")
                elif result["memory_delta_mb"] > 0.1:
                    print(f"  {endpoint}: +{result['memory_delta_mb']:.2f} MB")
                else:
                    print(f"  {endpoint}: {result['memory_delta_mb']:.2f} MB")
            
            results.extend(iteration_results)
            
            # Take iteration snapshot
            iteration_snapshot = self.take_memory_snapshot(f"iteration_{i+1}")
            memory_growth = iteration_snapshot.process_memory_mb - initial_snapshot.process_memory_mb
            
            print(f"  Iteration memory: {iteration_snapshot.process_memory_mb:.2f} MB (growth: +{memory_growth:.2f} MB)\\n")
            
            # Brief pause between iterations
            time.sleep(0.2)
        
        final_snapshot = self.take_memory_snapshot("loop_end")
        total_growth = final_snapshot.process_memory_mb - initial_snapshot.process_memory_mb
        print(f"Final memory: {final_snapshot.process_memory_mb:.2f} MB")
        print(f"Total memory growth: +{total_growth:.2f} MB\\n")
        
        return results
    
    def profile_concurrent_authentication(self, concurrent_users: int = 5, requests_per_user: int = 3) -> Dict[str, Any]:
        """Profile memory usage under concurrent authentication load."""
        print(f"=== CONCURRENT AUTHENTICATION PROFILING ({concurrent_users} users, {requests_per_user} requests each) ===\\n")
        
        import threading
        import concurrent.futures
        
        def simulate_user(user_id: int) -> List[Dict[str, Any]]:
            """Simulate a user making multiple authentication requests."""
            user_results = []
            user_session = requests.Session()
            user_session.timeout = 10
            
            for req_num in range(requests_per_user):
                start_time = time.time()
                try:
                    # Simulate typical authentication flow
                    endpoints = [
                        "/api/v1/auth/status",
                        "/api/v1/user/current", 
                        "/health"
                    ]
                    
                    for endpoint in endpoints:
                        response = user_session.get(self.base_url + endpoint)
                        user_results.append({
                            "user_id": user_id,
                            "request_num": req_num,
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "timestamp": time.time()
                        })
                        
                except Exception as e:
                    user_results.append({
                        "user_id": user_id,
                        "request_num": req_num,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            user_session.close()
            return user_results
        
        # Start memory monitoring
        monitor_thread = self.start_continuous_monitoring(interval=0.1)
        initial_snapshot = self.take_memory_snapshot("concurrent_start")
        
        # Run concurrent simulation
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(simulate_user, user_id) for user_id in range(concurrent_users)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        end_time = time.time()
        
        # Stop monitoring and get final snapshot
        self.stop_continuous_monitoring()
        monitor_thread.join(timeout=1.0)
        final_snapshot = self.take_memory_snapshot("concurrent_end")
        
        # Analyze results
        duration = end_time - start_time
        total_requests = len(all_results)
        memory_growth = final_snapshot.process_memory_mb - initial_snapshot.process_memory_mb
        
        # Find peak memory usage during test
        peak_memory = max(snapshot.process_memory_mb for snapshot in self.snapshots[-100:])  # Last 100 snapshots
        
        print(f"Concurrent test completed in {duration:.2f} seconds")
        print(f"Total requests: {total_requests}")
        print(f"Requests/second: {total_requests/duration:.2f}")
        print(f"Memory growth: +{memory_growth:.2f} MB")
        print(f"Peak memory: {peak_memory:.2f} MB")
        print(f"Connections: {initial_snapshot.active_connections} -> {final_snapshot.active_connections}")
        print()
        
        return {
            "test_type": "concurrent_authentication",
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "duration_seconds": duration,
            "requests_per_second": total_requests / duration,
            "initial_memory_mb": initial_snapshot.process_memory_mb,
            "final_memory_mb": final_snapshot.process_memory_mb,
            "peak_memory_mb": peak_memory,
            "memory_growth_mb": memory_growth,
            "connection_growth": final_snapshot.active_connections - initial_snapshot.active_connections,
            "results": all_results
        }
    
    def analyze_memory_leaks(self) -> Dict[str, Any]:
        """Analyze memory snapshots to identify potential leaks."""
        if len(self.snapshots) < 10:
            return {"error": "Not enough snapshots for analysis"}
        
        # Group snapshots by operation type
        operations = {}
        for snapshot in self.snapshots:
            op_type = snapshot.operation.split('_')[0] if '_' in snapshot.operation else snapshot.operation
            if op_type not in operations:
                operations[op_type] = []
            operations[op_type].append(snapshot)
        
        analysis = {
            "total_snapshots": len(self.snapshots),
            "timespan_seconds": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            "memory_growth_analysis": {},
            "leak_indicators": [],
            "recommendations": []
        }
        
        # Overall memory trend analysis
        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]
        total_memory_growth = last_snapshot.process_memory_mb - first_snapshot.process_memory_mb
        
        analysis["memory_growth_analysis"] = {
            "initial_memory_mb": first_snapshot.process_memory_mb,
            "final_memory_mb": last_snapshot.process_memory_mb,
            "total_growth_mb": total_memory_growth,
            "growth_rate_mb_per_minute": (total_memory_growth / analysis["timespan_seconds"]) * 60 if analysis["timespan_seconds"] > 0 else 0
        }
        
        # Detect memory leaks
        if total_memory_growth > 10:  # More than 10MB growth
            analysis["leak_indicators"].append({
                "type": "excessive_memory_growth",
                "severity": "high" if total_memory_growth > 50 else "medium",
                "description": f"Memory grew by {total_memory_growth:.2f} MB during profiling",
                "recommendation": "Investigate for memory leaks in authentication flows"
            })
        
        # Analyze connection leaks
        connection_growth = last_snapshot.active_connections - first_snapshot.active_connections
        if connection_growth > 5:
            analysis["leak_indicators"].append({
                "type": "connection_leak",
                "severity": "high",
                "description": f"Active connections grew by {connection_growth}",
                "recommendation": "Ensure proper connection cleanup in authentication middleware"
            })
        
        # Analyze file handle leaks
        files_growth = last_snapshot.open_files - first_snapshot.open_files
        if files_growth > 10:
            analysis["leak_indicators"].append({
                "type": "file_handle_leak", 
                "severity": "medium",
                "description": f"Open files grew by {files_growth}",
                "recommendation": "Check for proper file handle cleanup"
            })
        
        # Generate recommendations based on findings
        if len(analysis["leak_indicators"]) == 0:
            analysis["recommendations"].append("No significant memory leaks detected during profiling")
        else:
            analysis["recommendations"].extend([
                "Monitor authentication endpoints for memory growth in production",
                "Implement connection pooling and proper cleanup",
                "Add memory usage alerts for authentication services",
                "Consider implementing circuit breakers for memory protection"
            ])
        
        return analysis
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory performance report."""
        print("=== COMPREHENSIVE MEMORY PERFORMANCE REPORT ===\\n")
        
        # Run loop profiling
        loop_results = self.profile_authentication_loop(iterations=5)
        
        # Run concurrent profiling
        concurrent_results = self.profile_concurrent_authentication(concurrent_users=3, requests_per_user=2)
        
        # Analyze for memory leaks
        leak_analysis = self.analyze_memory_leaks()
        
        # Compile comprehensive report
        report = {
            "timestamp": time.time(),
            "test_summary": {
                "loop_test_requests": len(loop_results),
                "concurrent_test_requests": concurrent_results.get("total_requests", 0),
                "total_memory_snapshots": len(self.snapshots)
            },
            "loop_profiling": {
                "results": loop_results,
                "summary": self.summarize_loop_results(loop_results)
            },
            "concurrent_profiling": concurrent_results,
            "memory_leak_analysis": leak_analysis,
            "optimization_recommendations": self.generate_optimization_recommendations(loop_results, concurrent_results, leak_analysis)
        }
        
        return report
    
    def summarize_loop_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize loop profiling results."""
        if not results:
            return {}
        
        # Calculate averages
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            return {"error": "No successful requests in loop test"}
        
        total_memory_delta = sum(r.get("memory_delta_mb", 0) for r in successful_results)
        avg_memory_delta = total_memory_delta / len(successful_results)
        max_memory_delta = max(r.get("memory_delta_mb", 0) for r in successful_results)
        
        return {
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "total_memory_delta_mb": total_memory_delta,
            "average_memory_delta_mb": avg_memory_delta,
            "max_memory_delta_mb": max_memory_delta,
            "memory_efficient_endpoints": [r["endpoint"] for r in successful_results if r.get("memory_delta_mb", 0) < 0.01],
            "memory_heavy_endpoints": [r["endpoint"] for r in successful_results if r.get("memory_delta_mb", 0) > 0.5]
        }
    
    def generate_optimization_recommendations(self, loop_results: List[Dict], concurrent_results: Dict, leak_analysis: Dict) -> List[Dict[str, str]]:
        """Generate memory optimization recommendations."""
        recommendations = []
        
        # Based on loop results
        loop_summary = self.summarize_loop_results(loop_results)
        if loop_summary.get("max_memory_delta_mb", 0) > 1.0:
            recommendations.append({
                "category": "memory_efficiency",
                "priority": "high",
                "recommendation": "Optimize high-memory authentication endpoints",
                "details": f"Some endpoints use > 1MB per request. Heavy endpoints: {loop_summary.get('memory_heavy_endpoints', [])}"
            })
        
        # Based on concurrent results
        if concurrent_results.get("memory_growth_mb", 0) > 5:
            recommendations.append({
                "category": "concurrent_performance",
                "priority": "medium",
                "recommendation": "Optimize memory usage under concurrent load",
                "details": f"Memory grew by {concurrent_results.get('memory_growth_mb', 0):.2f}MB under concurrent load"
            })
        
        # Based on leak analysis
        leak_indicators = leak_analysis.get("leak_indicators", [])
        for indicator in leak_indicators:
            recommendations.append({
                "category": "memory_leak",
                "priority": indicator["severity"],
                "recommendation": indicator["recommendation"],
                "details": indicator["description"]
            })
        
        # Generic recommendations
        if not recommendations:
            recommendations.append({
                "category": "monitoring",
                "priority": "low",
                "recommendation": "Implement production memory monitoring",
                "details": "No significant issues detected, but monitoring is recommended"
            })
        
        return recommendations

def main():
    """Main memory profiling function."""
    print("Authentication Memory Usage Profiler")
    print("=" * 50)
    print()
    
    # Check if API is accessible
    profiler = AuthenticationMemoryProfiler()
    
    try:
        response = profiler.session.get(profiler.base_url + "/health", timeout=5)
        if response.status_code != 200:
            print(f"WARNING: API health check failed (status: {response.status_code})")
        else:
            print("API is accessible - starting memory profiling...")
            print()
    except Exception as e:
        print(f"ERROR: Cannot connect to API at {profiler.base_url}")
        print(f"Error: {e}")
        print("Make sure the API is running and accessible.")
        return
    
    # Generate comprehensive report
    report = profiler.generate_comprehensive_report()
    
    # Print summary
    print("=== MEMORY PERFORMANCE SUMMARY ===\\n")
    
    if "test_summary" in report:
        summary = report["test_summary"]
        print(f"Total requests tested: {summary['loop_test_requests'] + summary['concurrent_test_requests']}")
        print(f"Memory snapshots taken: {summary['total_memory_snapshots']}")
    
    if "memory_leak_analysis" in report:
        leak_analysis = report["memory_leak_analysis"]
        if "memory_growth_analysis" in leak_analysis:
            growth = leak_analysis["memory_growth_analysis"]
            print(f"Memory growth: +{growth['total_growth_mb']:.2f} MB")
            print(f"Growth rate: {growth['growth_rate_mb_per_minute']:.2f} MB/minute")
        
        leak_count = len(leak_analysis.get("leak_indicators", []))
        print(f"Memory leak indicators: {leak_count}")
    
    if "optimization_recommendations" in report:
        recommendations = report["optimization_recommendations"]
        high_priority = [r for r in recommendations if r["priority"] == "high"]
        print(f"High priority optimizations: {len(high_priority)}")
    
    print()
    
    # Save detailed report
    report_file = ".claude/test_results/performance/auth_memory_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Detailed report saved to: {report_file}")
    print("Memory profiling complete.")

if __name__ == "__main__":
    main()