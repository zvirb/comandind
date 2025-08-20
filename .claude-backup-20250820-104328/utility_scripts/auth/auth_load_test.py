#!/usr/bin/env python3
"""
Authentication Load Test for Database Pool Analysis

Simulates concurrent authentication requests to identify pool exhaustion
conditions and measure performance bottlenecks.
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
from typing import List, Dict, Any
from datetime import datetime
import concurrent.futures
import sys
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuthLoadTester:
    """Load tester for authentication endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = []
        self.pool_stats_history = []
        
    async def get_csrf_token(self, session: aiohttp.ClientSession) -> str:
        """Get CSRF token for authenticated requests."""
        try:
            async with session.get(f"{self.base_url}/auth/csrf-token") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("csrf_token", "")
                return ""
        except Exception as e:
            logger.warning(f"Failed to get CSRF token: {e}")
            return ""
    
    async def authenticate_user(self, session: aiohttp.ClientSession, 
                              email: str, password: str, 
                              csrf_token: str = "") -> Dict[str, Any]:
        """Perform authentication request and measure timing."""
        start_time = time.time()
        
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-TOKEN": csrf_token
        } if csrf_token else {"Content-Type": "application/json"}
        
        payload = {
            "email": email,
            "password": password
        }
        
        try:
            async with session.post(
                f"{self.base_url}/auth/jwt/login",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "response_time_ms": response_time,
                    "status_code": response.status,
                    "success": response.status == 200,
                    "email": email
                }
                
                if response.status == 200:
                    try:
                        response_data = await response.json()
                        result["has_token"] = bool(response_data.get("access_token"))
                    except:
                        result["has_token"] = False
                else:
                    try:
                        error_data = await response.json()
                        result["error"] = error_data.get("detail", f"HTTP {response.status}")
                    except:
                        result["error"] = f"HTTP {response.status}"
                
                return result
                
        except asyncio.TimeoutError:
            return {
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": 30000,  # timeout
                "status_code": 408,
                "success": False,
                "email": email,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": (time.time() - start_time) * 1000,
                "status_code": 0,
                "success": False,
                "email": email,
                "error": str(e)
            }
    
    async def monitor_pool_stats(self, duration_seconds: int = 60):
        """Monitor database pool statistics during load test."""
        # Add app to Python path for pool monitoring
        sys.path.insert(0, '/home/marku/ai_workflow_engine/app')
        
        try:
            from shared.utils.database_setup import get_database_stats
            
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                stats = get_database_stats()
                if stats:
                    stats["timestamp"] = datetime.now().isoformat()
                    self.pool_stats_history.append(stats)
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
        except ImportError:
            logger.warning("Could not import pool monitoring - skipping pool stats")
        except Exception as e:
            logger.error(f"Pool monitoring error: {e}")
    
    async def run_concurrent_auth_test(self, 
                                     concurrent_users: int = 10,
                                     requests_per_user: int = 5,
                                     test_email: str = "admin@aiwfe.com",
                                     test_password: str = "admin123") -> Dict[str, Any]:
        """Run concurrent authentication load test."""
        
        logger.info(f"Starting auth load test: {concurrent_users} concurrent users, "
                   f"{requests_per_user} requests each")
        
        # Start pool monitoring
        monitor_task = asyncio.create_task(
            self.monitor_pool_stats(duration_seconds=60)
        )
        
        start_time = time.time()
        
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=concurrent_users * 2,
            limit_per_host=concurrent_users,
            keepalive_timeout=30
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Get CSRF token once
            csrf_token = await self.get_csrf_token(session)
            if csrf_token:
                logger.info("CSRF token obtained successfully")
            else:
                logger.warning("No CSRF token - requests may fail")
            
            # Create concurrent authentication tasks
            tasks = []
            
            for user_id in range(concurrent_users):
                for request_id in range(requests_per_user):
                    task = self.authenticate_user(
                        session, 
                        test_email,
                        test_password,
                        csrf_token
                    )
                    tasks.append(task)
            
            # Execute all authentication requests concurrently
            logger.info(f"Executing {len(tasks)} concurrent authentication requests...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            self.results = []
            for result in results:
                if isinstance(result, dict):
                    self.results.append(result)
                else:
                    # Handle exceptions
                    self.results.append({
                        "timestamp": datetime.now().isoformat(),
                        "response_time_ms": 0,
                        "status_code": 0,
                        "success": False,
                        "error": str(result)
                    })
        
        # Stop monitoring
        monitor_task.cancel()
        
        total_time = time.time() - start_time
        
        # Analyze results
        analysis = self.analyze_results(total_time)
        
        logger.info(f"Load test completed in {total_time:.2f}s")
        logger.info(f"Success rate: {analysis['success_rate']:.1%}")
        logger.info(f"Average response time: {analysis['avg_response_time']:.1f}ms")
        
        return analysis
    
    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """Analyze load test results."""
        
        if not self.results:
            return {"error": "No results to analyze"}
        
        successful_results = [r for r in self.results if r["success"]]
        failed_results = [r for r in self.results if not r["success"]]
        
        response_times = [r["response_time_ms"] for r in self.results if r["response_time_ms"] > 0]
        
        analysis = {
            "test_summary": {
                "total_requests": len(self.results),
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / len(self.results) if self.results else 0,
                "total_test_time": total_time,
                "requests_per_second": len(self.results) / total_time if total_time > 0 else 0
            },
            "response_time_stats": {},
            "error_analysis": {},
            "pool_statistics": {},
            "bottleneck_indicators": []
        }
        
        # Response time statistics
        if response_times:
            analysis["response_time_stats"] = {
                "avg_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0],
                "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) > 1 else response_times[0]
            }
        
        # Error analysis
        error_counts = {}
        for result in failed_results:
            error = result.get("error", "Unknown error")
            error_counts[error] = error_counts.get(error, 0) + 1
        
        analysis["error_analysis"] = {
            "error_types": error_counts,
            "most_common_error": max(error_counts.items(), key=lambda x: x[1]) if error_counts else None,
            "timeout_count": len([r for r in failed_results if "timeout" in r.get("error", "").lower()]),
            "connection_errors": len([r for r in failed_results if "connection" in r.get("error", "").lower()])
        }
        
        # Pool statistics analysis
        if self.pool_stats_history:
            analysis["pool_statistics"] = self.analyze_pool_stats()
        
        # Identify bottleneck indicators
        bottlenecks = []
        
        # High response times indicate database bottlenecks
        if analysis["response_time_stats"].get("avg_response_time", 0) > 500:
            bottlenecks.append("High average response time indicates database bottleneck")
        
        if analysis["response_time_stats"].get("p95_response_time", 0) > 1000:
            bottlenecks.append("Very high P95 response time suggests pool exhaustion")
        
        # Error patterns
        if analysis["error_analysis"]["timeout_count"] > len(self.results) * 0.1:
            bottlenecks.append("High timeout rate suggests connection pool exhaustion")
        
        if analysis["test_summary"]["success_rate"] < 0.8:
            bottlenecks.append("Low success rate indicates system overload")
        
        analysis["bottleneck_indicators"] = bottlenecks
        
        return analysis
    
    def analyze_pool_stats(self) -> Dict[str, Any]:
        """Analyze collected pool statistics."""
        if not self.pool_stats_history:
            return {}
        
        pool_analysis = {
            "sync_engine_stats": [],
            "async_engine_stats": [],
            "peak_utilization": {},
            "utilization_trends": {}
        }
        
        # Extract sync and async engine stats
        for stats in self.pool_stats_history:
            if stats.get("sync_engine"):
                pool_analysis["sync_engine_stats"].append(stats["sync_engine"])
            if stats.get("async_engine"):
                pool_analysis["async_engine_stats"].append(stats["async_engine"])
        
        # Calculate peak utilization
        for engine_type in ["sync_engine_stats", "async_engine_stats"]:
            if pool_analysis[engine_type]:
                peak_created = max(stat.get("connections_created", 0) for stat in pool_analysis[engine_type])
                max_total = max(stat.get("total_connections", 1) for stat in pool_analysis[engine_type])
                
                pool_analysis["peak_utilization"][engine_type.replace("_stats", "")] = {
                    "peak_connections": peak_created,
                    "max_total_connections": max_total,
                    "peak_utilization": peak_created / max_total if max_total > 0 else 0
                }
        
        return pool_analysis
    
    def save_results(self, analysis: Dict[str, Any], filename: str = None):
        """Save test results to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/marku/ai_workflow_engine/auth_load_test_results_{timestamp}.json"
        
        full_results = {
            "analysis": analysis,
            "raw_results": self.results,
            "pool_stats_history": self.pool_stats_history
        }
        
        with open(filename, 'w') as f:
            json.dump(full_results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {filename}")
        return filename

async def main():
    """Run authentication load test."""
    
    # Test configurations
    test_configs = [
        {"concurrent_users": 5, "requests_per_user": 3, "name": "Light Load"},
        {"concurrent_users": 10, "requests_per_user": 5, "name": "Moderate Load"}, 
        {"concurrent_users": 20, "requests_per_user": 5, "name": "Heavy Load"},
        {"concurrent_users": 30, "requests_per_user": 3, "name": "Peak Load"}
    ]
    
    print("\n" + "="*80)
    print("🔥 AUTHENTICATION LOAD TEST - DATABASE POOL ANALYSIS")
    print("="*80)
    
    tester = AuthLoadTester()
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{tester.base_url}/docs", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status != 200:
                    print(f"❌ API not accessible at {tester.base_url}")
                    print("Please ensure the API server is running")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to API at {tester.base_url}: {e}")
        print("Please ensure the API server is running")
        return
    
    print(f"✅ API accessible at {tester.base_url}")
    
    # Run load tests
    all_results = {}
    
    for config in test_configs:
        print(f"\n🚀 Running {config['name']} Test...")
        print(f"   Concurrent Users: {config['concurrent_users']}")
        print(f"   Requests per User: {config['requests_per_user']}")
        print(f"   Total Requests: {config['concurrent_users'] * config['requests_per_user']}")
        
        try:
            analysis = await tester.run_concurrent_auth_test(
                concurrent_users=config['concurrent_users'],
                requests_per_user=config['requests_per_user']
            )
            
            all_results[config['name']] = analysis
            
            # Display summary
            print(f"\n📊 {config['name']} Results:")
            print(f"   Success Rate: {analysis['test_summary']['success_rate']:.1%}")
            print(f"   Avg Response Time: {analysis['response_time_stats'].get('avg_response_time', 0):.1f}ms")
            print(f"   P95 Response Time: {analysis['response_time_stats'].get('p95_response_time', 0):.1f}ms")
            print(f"   Requests/Second: {analysis['test_summary']['requests_per_second']:.1f}")
            
            if analysis.get('bottleneck_indicators'):
                print(f"   🚨 Bottlenecks:")
                for bottleneck in analysis['bottleneck_indicators']:
                    print(f"      - {bottleneck}")
            
            # Clear results for next test
            tester.results = []
            tester.pool_stats_history = []
            
            # Brief pause between tests
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Test {config['name']} failed: {e}")
            all_results[config['name']] = {"error": str(e)}
    
    # Save comprehensive results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/home/marku/ai_workflow_engine/auth_load_test_comprehensive_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📄 Comprehensive results saved to: {results_file}")
    
    # Summary analysis
    print(f"\n📈 LOAD TEST SUMMARY")
    print("="*50)
    
    for test_name, results in all_results.items():
        if "error" not in results:
            success_rate = results['test_summary']['success_rate']
            avg_time = results['response_time_stats'].get('avg_response_time', 0)
            status = "✅ PASS" if success_rate > 0.9 and avg_time < 500 else "⚠️  DEGRADED" if success_rate > 0.8 else "❌ FAIL"
            print(f"{test_name}: {status} ({success_rate:.1%} success, {avg_time:.0f}ms avg)")
        else:
            print(f"{test_name}: ❌ ERROR - {results['error']}")
    
    print("\n" + "="*80)
    print("🏁 Load testing complete!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())