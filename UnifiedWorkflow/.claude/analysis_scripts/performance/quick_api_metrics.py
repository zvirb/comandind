#!/usr/bin/env python3
"""
Quick API Performance Metrics Collector

Analyzes immediate API performance patterns for polling optimization.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime

async def test_api_endpoints():
    """Test API endpoints for performance metrics"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        {"path": "/api/v1/health", "method": "GET"},
        {"path": "/api/v1/health/integration", "method": "GET"},
        {"path": "/api/v1/session/validate", "method": "POST"},
        # Note: Dashboard endpoints require authentication
    ]
    
    results = {}
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        for endpoint in endpoints:
            print(f"Testing {endpoint['path']}...")
            response_times = []
            success_count = 0
            
            # Test each endpoint 5 times
            for i in range(5):
                start_time = time.time()
                
                try:
                    if endpoint["method"] == "POST":
                        async with session.post(f"{base_url}{endpoint['path']}", 
                                              headers={"Content-Type": "application/json"}) as response:
                            await response.text()
                            response_time = (time.time() - start_time) * 1000
                            
                            if response.status < 400:
                                response_times.append(response_time)
                                success_count += 1
                            
                            print(f"  Test {i+1}: {response.status} - {response_time:.1f}ms")
                    else:
                        async with session.get(f"{base_url}{endpoint['path']}") as response:
                            await response.text()
                            response_time = (time.time() - start_time) * 1000
                            
                            if response.status < 400:
                                response_times.append(response_time)
                                success_count += 1
                            
                            print(f"  Test {i+1}: {response.status} - {response_time:.1f}ms")
                            
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    print(f"  Test {i+1}: ERROR - {response_time:.1f}ms - {e}")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            # Calculate metrics
            if response_times:
                results[endpoint["path"]] = {
                    "avg_response_time_ms": statistics.mean(response_times),
                    "min_response_time_ms": min(response_times),
                    "max_response_time_ms": max(response_times),
                    "median_response_time_ms": statistics.median(response_times),
                    "success_rate": (success_count / 5) * 100,
                    "response_times": response_times
                }
            else:
                results[endpoint["path"]] = {
                    "error": "No successful responses",
                    "success_rate": 0
                }
    
    return results

async def analyze_docker_metrics():
    """Analyze Docker container resource usage"""
    import subprocess
    
    try:
        # Get API container stats
        result = subprocess.run([
            "docker", "stats", "--no-stream", "--format", 
            "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return {
                "docker_stats": lines,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"error": "Failed to get Docker stats"}
            
    except Exception as e:
        return {"error": f"Docker stats error: {e}"}

def analyze_polling_patterns():
    """Analyze polling patterns from code inspection"""
    
    patterns = {
        "session_validation": {
            "source": "AuthContext.jsx",
            "interval_seconds": 600,  # 10 minutes from line 508
            "throttle_interval_seconds": 300,  # 5 minutes from line 308
            "deduplication_enabled": True,
            "circuit_breaker_enabled": True,
            "description": "Periodic auth status check every 10 minutes with 5-minute throttling"
        },
        "health_checks": {
            "source": "AuthContext.jsx", 
            "interval_seconds": 30,  # Health check throttle from line 126
            "circuit_breaker_threshold": 5,  # From line 98
            "description": "Health checks throttled to minimum 30 seconds apart"
        },
        "dashboard_loading": {
            "source": "Dashboard.jsx",
            "pattern": "on_demand",
            "endpoints": ["/api/v1/dashboard", "/api/v1/performance_dashboard", "/api/v1/health"],
            "description": "Dashboard loads data once on component mount, no automatic polling"
        },
        "middleware_optimizations": {
            "source": "main.py middleware stack",
            "cached_auth_ttl": 600,  # 10 minutes from line 439
            "session_cache_ttl": 300,  # 5 minutes from line 440  
            "rate_limits": {
                "session_validate_calls": 600,  # Per 60 seconds from line 446
                "auth_calls": 120,  # Per 60 seconds from line 448
                "token_refresh_calls": 80  # Per 300 seconds from line 452
            },
            "description": "Extensive caching and rate limiting in place"
        }
    }
    
    return patterns

async def main():
    """Main analysis function"""
    print("Quick API Performance Metrics Analysis")
    print("=" * 50)
    
    # Test API performance
    print("\n1. Testing API Endpoint Performance...")
    api_results = await test_api_endpoints()
    
    print("\n2. Analyzing Docker Container Metrics...")
    docker_results = await analyze_docker_metrics()
    
    print("\n3. Analyzing Polling Patterns from Code...")
    polling_patterns = analyze_polling_patterns()
    
    # Compile results
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "api_performance": api_results,
        "docker_metrics": docker_results,
        "polling_patterns": polling_patterns,
        "analysis": {},
        "recommendations": []
    }
    
    # Generate analysis
    print("\n" + "=" * 50)
    print("PERFORMANCE ANALYSIS RESULTS")
    print("=" * 50)
    
    # API Performance Analysis
    print("\nAPI ENDPOINT PERFORMANCE:")
    for endpoint, metrics in api_results.items():
        if "error" not in metrics:
            print(f"  {endpoint}:")
            print(f"    Average: {metrics['avg_response_time_ms']:.1f}ms")
            print(f"    Range: {metrics['min_response_time_ms']:.1f}ms - {metrics['max_response_time_ms']:.1f}ms")
            print(f"    Success Rate: {metrics['success_rate']:.1f}%")
        else:
            print(f"  {endpoint}: {metrics['error']}")
    
    # Polling Pattern Analysis
    print("\nPOLLING PATTERN ANALYSIS:")
    print(f"  Session Validation: Every {polling_patterns['session_validation']['interval_seconds']}s")
    print(f"  Health Checks: Throttled to {polling_patterns['health_checks']['interval_seconds']}s minimum")
    print(f"  Dashboard: {polling_patterns['dashboard_loading']['pattern']}")
    
    # Generate recommendations
    recommendations = []
    
    # Check session validation performance
    session_validate_metrics = api_results.get("/api/v1/session/validate", {})
    if "avg_response_time_ms" in session_validate_metrics:
        if session_validate_metrics["avg_response_time_ms"] > 100:
            recommendations.append({
                "priority": "HIGH",
                "category": "Session Validation Performance",
                "issue": f"Session validation response time ({session_validate_metrics['avg_response_time_ms']:.1f}ms) may cause UI delays",
                "recommendation": "Optimize session validation endpoint or increase caching TTL",
                "current_cache_ttl": "5 minutes (session), 10 minutes (auth)"
            })
    
    # Check health check performance  
    health_metrics = api_results.get("/api/v1/health/integration", {})
    if "avg_response_time_ms" in health_metrics:
        if health_metrics["avg_response_time_ms"] > 50:
            recommendations.append({
                "priority": "MEDIUM", 
                "category": "Health Check Performance",
                "issue": f"Health check response time ({health_metrics['avg_response_time_ms']:.1f}ms) impacts responsiveness",
                "recommendation": "Consider caching health status or reducing check frequency",
                "current_throttle": "30 seconds minimum"
            })
    
    # Overall assessment
    recommendations.append({
        "priority": "INFO",
        "category": "Current State Assessment",
        "finding": "Code analysis shows good polling optimizations already in place",
        "details": [
            "Session validation: 10-minute intervals with throttling",
            "Health checks: 30-second minimum throttling",  
            "Dashboard: On-demand loading, no auto-polling",
            "Extensive caching: 5-10 minute TTLs",
            "Rate limiting: 600 session validations/minute allowed",
            "Circuit breaker: 5 failure threshold with exponential backoff"
        ]
    })
    
    # If flickering still occurs, likely frontend issues
    recommendations.append({
        "priority": "HIGH",
        "category": "Flickering Root Cause",
        "assessment": "Backend polling patterns appear optimized",
        "likely_cause": "Frontend state management or rendering cycles",
        "investigation_needed": [
            "React component re-rendering patterns",
            "State update cascades in AuthContext",
            "Conditional rendering based on auth state",
            "Component unmounting/remounting during auth checks"
        ],
        "recommendation": "Focus optimization on frontend rendering patterns rather than API polling frequency"
    })
    
    analysis["recommendations"] = recommendations
    
    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['priority']}] {rec['category']}")
        if "issue" in rec:
            print(f"   Issue: {rec['issue']}")
        if "finding" in rec:
            print(f"   Finding: {rec['finding']}")
        if "assessment" in rec:
            print(f"   Assessment: {rec['assessment']}")
        if "recommendation" in rec:
            print(f"   Recommendation: {rec['recommendation']}")
        if "details" in rec:
            print(f"   Details:")
            for detail in rec["details"]:
                print(f"     - {detail}")
        if "investigation_needed" in rec:
            print(f"   Investigation Needed:")
            for item in rec["investigation_needed"]:
                print(f"     - {item}")
    
    # Save results
    output_file = f"/home/marku/ai_workflow_engine/.claude/test_results/performance/quick_api_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"\nFull analysis saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())