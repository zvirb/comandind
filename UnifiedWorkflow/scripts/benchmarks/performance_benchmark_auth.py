#!/usr/bin/env python3
"""
Authentication Performance Benchmark Script
==========================================

Measures authentication performance improvements from Phase 5A optimizations:
1. Router consolidation (8 → 1 unified router)  
2. Enhanced JWT caching with Redis
3. Optimized rate limiting configuration
4. Database connection pool tuning

Target: Reduce auth latency from 176ms to <40ms (60%+ improvement)
"""

import asyncio
import aiohttp
import time
import statistics
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthPerformanceBenchmark:
    """
    Comprehensive authentication performance benchmarking tool.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = None
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_improvement": "60%+ latency reduction (176ms → <40ms)",
            "baseline_performance": {"auth_latency_ms": 176},
            "endpoints_tested": [],
            "performance_metrics": {},
            "optimization_validation": {}
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def authenticate_user(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate a test user and return access token.
        Returns: (success, auth_data)
        """
        auth_data = {"access_token": None, "auth_metrics": {}}
        
        try:
            login_payload = {
                "email": "admin@aiwfe.com",
                "password": "admin123",
                "method": "standard"
            }
            
            start_time = time.time()
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/jwt/login",
                json=login_payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                login_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    auth_data["access_token"] = data.get("access_token")
                    auth_data["auth_metrics"]["login_time_ms"] = round(login_time, 2)
                    
                    logger.info(f"✓ Authentication successful: {login_time:.1f}ms")
                    return True, auth_data
                else:
                    error_data = await response.text()
                    logger.error(f"Authentication failed: {response.status} - {error_data}")
                    return False, auth_data
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, auth_data
    
    async def benchmark_session_validation(
        self, 
        access_token: str, 
        num_requests: int = 50
    ) -> Dict[str, Any]:
        """
        Benchmark the critical /session/validate endpoint.
        This is the most important endpoint for frontend performance.
        
        Target: <40ms average response time (vs 176ms baseline)
        """
        logger.info(f"Benchmarking session validation with {num_requests} requests...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response_times = []
        success_count = 0
        cache_hits = 0
        errors = []
        
        # Warm up caches with 5 requests
        for i in range(5):
            try:
                async with self.session.get(
                    f"{self.base_url}/api/v1/session/validate",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    await response.json()
            except:
                pass
        
        # Main benchmark
        for i in range(num_requests):
            try:
                start_time = time.time()
                
                async with self.session.get(
                    f"{self.base_url}/api/v1/session/validate",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    response_times.append(response_time)
                    
                    if response.status == 200:
                        success_count += 1
                        data = await response.json()
                        
                        # Check if cached
                        if data.get("cached", False):
                            cache_hits += 1
                        
                        # Check auth cache header
                        auth_cache = response.headers.get("X-Auth-Cache")
                        if auth_cache == "hit":
                            cache_hits += 1
                    else:
                        error_text = await response.text()
                        errors.append(f"Status {response.status}: {error_text}")
                        
            except asyncio.TimeoutError:
                errors.append("Request timeout")
            except Exception as e:
                errors.append(str(e))
        
        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = 0
            min_response_time = max_response_time = 0
        
        cache_hit_rate = (cache_hits / num_requests) * 100 if num_requests > 0 else 0
        success_rate = (success_count / num_requests) * 100 if num_requests > 0 else 0
        
        # Performance analysis
        target_met = avg_response_time < 40
        improvement_vs_baseline = ((176 - avg_response_time) / 176) * 100 if avg_response_time > 0 else 0
        
        return {
            "endpoint": "/api/v1/session/validate",
            "requests_sent": num_requests,
            "successful_requests": success_count,
            "success_rate_percent": round(success_rate, 2),
            "response_times": {
                "average_ms": round(avg_response_time, 2),
                "median_ms": round(median_response_time, 2),
                "p95_ms": round(p95_response_time, 2),
                "min_ms": round(min_response_time, 2),
                "max_ms": round(max_response_time, 2)
            },
            "caching_metrics": {
                "cache_hits": cache_hits,
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "cache_efficiency": "excellent" if cache_hit_rate > 80 else "good" if cache_hit_rate > 60 else "needs_improvement"
            },
            "performance_analysis": {
                "target_40ms_met": target_met,
                "baseline_176ms_improvement_percent": round(improvement_vs_baseline, 2),
                "performance_grade": "A" if avg_response_time < 20 else "B" if avg_response_time < 40 else "C" if avg_response_time < 100 else "F"
            },
            "errors": errors[:10] if errors else []  # Limit errors shown
        }
    
    async def benchmark_auth_endpoints(self, access_token: str) -> Dict[str, Any]:
        """
        Benchmark various authentication endpoints for comprehensive performance analysis.
        """
        logger.info("Benchmarking authentication endpoints...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        endpoint_results = {}
        
        # Test endpoints with their expected performance targets
        endpoints = [
            ("/api/v1/auth/validate", "token_validation", 50),  # 50ms target
            ("/api/v1/auth/status", "auth_status", 30),         # 30ms target  
            ("/api/v1/user/current", "user_info", 40)           # 40ms target
        ]
        
        for endpoint_path, endpoint_name, target_ms in endpoints:
            response_times = []
            success_count = 0
            
            # Run 20 requests per endpoint
            for i in range(20):
                try:
                    start_time = time.time()
                    
                    async with self.session.get(
                        f"{self.base_url}{endpoint_path}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        response_times.append(response_time)
                        
                        if response.status == 200:
                            success_count += 1
                        
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint_path} request failed: {e}")
            
            # Calculate endpoint statistics
            if response_times:
                avg_time = statistics.mean(response_times)
                target_met = avg_time < target_ms
                
                endpoint_results[endpoint_name] = {
                    "endpoint": endpoint_path,
                    "average_response_time_ms": round(avg_time, 2),
                    "target_ms": target_ms,
                    "target_met": target_met,
                    "success_rate": round((success_count / 20) * 100, 2),
                    "performance_grade": "A" if avg_time < target_ms * 0.5 else "B" if target_met else "C"
                }
        
        return endpoint_results
    
    async def test_concurrent_load(self, access_token: str) -> Dict[str, Any]:
        """
        Test authentication performance under concurrent load.
        Simulates real-world usage with multiple simultaneous requests.
        """
        logger.info("Testing concurrent authentication load...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        concurrent_requests = 25  # Moderate concurrent load
        
        async def single_request():
            start_time = time.time()
            try:
                async with self.session.get(
                    f"{self.base_url}/api/v1/session/validate",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    success = response.status == 200
                    
                    return {
                        "response_time_ms": response_time,
                        "success": success,
                        "status_code": response.status
                    }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    "response_time_ms": response_time,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        results = await asyncio.gather(*[single_request() for _ in range(concurrent_requests)])
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        response_times = [r["response_time_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        success_rate = (success_count / concurrent_requests) * 100
        
        # Concurrent performance analysis
        concurrent_performance_good = avg_response_time < 80  # Higher threshold for concurrent
        
        return {
            "concurrent_requests": concurrent_requests,
            "total_execution_time_ms": round(total_time, 2),
            "successful_requests": success_count,
            "success_rate_percent": round(success_rate, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "max_response_time_ms": round(max_response_time, 2),
            "concurrent_performance_acceptable": concurrent_performance_good,
            "throughput_requests_per_second": round(concurrent_requests / (total_time / 1000), 2)
        }
    
    async def validate_optimizations(self) -> Dict[str, Any]:
        """
        Validate that all planned optimizations are working correctly.
        """
        logger.info("Validating authentication optimizations...")
        
        validations = {}
        
        try:
            # Test 1: Unified router consolidation
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                validations["router_consolidation"] = {
                    "status": "active" if response.status in [200, 401] else "error",
                    "unified_router_responding": response.status in [200, 401]
                }
        except Exception as e:
            validations["router_consolidation"] = {
                "status": "error",
                "error": str(e)
            }
        
        try:
            # Test 2: Health endpoint performance (should be fast)
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                health_time = (time.time() - start_time) * 1000
                
                validations["health_endpoint"] = {
                    "status": "good" if health_time < 50 else "slow",
                    "response_time_ms": round(health_time, 2),
                    "endpoint_accessible": response.status == 200
                }
        except Exception as e:
            validations["health_endpoint"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test 3: Rate limiting headers (validate optimized limits)
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/csrf-token",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                rate_limit_headers = {
                    key: value for key, value in response.headers.items() 
                    if "ratelimit" in key.lower() or "rate-limit" in key.lower()
                }
                
                validations["rate_limiting"] = {
                    "status": "configured" if rate_limit_headers else "not_detected",
                    "headers_present": bool(rate_limit_headers),
                    "rate_limit_headers": rate_limit_headers
                }
        except Exception as e:
            validations["rate_limiting"] = {
                "status": "error", 
                "error": str(e)
            }
        
        return validations
    
    async def run_complete_benchmark(self) -> Dict[str, Any]:
        """
        Run the complete authentication performance benchmark suite.
        """
        logger.info("="*80)
        logger.info("AUTHENTICATION PERFORMANCE BENCHMARK - Phase 5A")
        logger.info("="*80)
        
        # Step 1: Authentication
        logger.info("1. Authenticating test user...")
        auth_success, auth_data = await self.authenticate_user()
        
        if not auth_success:
            logger.error("Authentication failed - cannot proceed with benchmarks")
            self.results["error"] = "Authentication failed"
            return self.results
        
        access_token = auth_data["access_token"]
        self.results["authentication"] = auth_data["auth_metrics"]
        
        # Step 2: Session validation benchmark (most critical)
        logger.info("2. Benchmarking session validation performance...")
        session_results = await self.benchmark_session_validation(access_token)
        self.results["session_validation"] = session_results
        self.results["endpoints_tested"].append("/api/v1/session/validate")
        
        # Step 3: General auth endpoints
        logger.info("3. Benchmarking general authentication endpoints...")
        endpoint_results = await self.benchmark_auth_endpoints(access_token)
        self.results["auth_endpoints"] = endpoint_results
        
        # Step 4: Concurrent load testing
        logger.info("4. Testing concurrent authentication load...")
        concurrent_results = await self.test_concurrent_load(access_token)
        self.results["concurrent_performance"] = concurrent_results
        
        # Step 5: Optimization validation
        logger.info("5. Validating optimization implementation...")
        optimization_results = await self.validate_optimizations()
        self.results["optimization_validation"] = optimization_results
        
        # Step 6: Overall performance analysis
        logger.info("6. Analyzing overall performance improvements...")
        self.results["performance_summary"] = self._analyze_performance()
        
        return self.results
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze overall performance and generate summary."""
        session_data = self.results.get("session_validation", {})
        avg_session_time = session_data.get("response_times", {}).get("average_ms", 0)
        
        # Performance targets
        target_met = avg_session_time < 40
        baseline_improvement = ((176 - avg_session_time) / 176) * 100 if avg_session_time > 0 else 0
        
        # Cache efficiency
        cache_hit_rate = session_data.get("caching_metrics", {}).get("cache_hit_rate_percent", 0)
        
        # Overall grade
        if avg_session_time < 20 and cache_hit_rate > 80:
            overall_grade = "A+"
        elif avg_session_time < 40 and cache_hit_rate > 60:
            overall_grade = "A"
        elif avg_session_time < 80:
            overall_grade = "B"
        else:
            overall_grade = "C"
        
        return {
            "primary_metric": {
                "session_validation_avg_ms": avg_session_time,
                "target_40ms_achieved": target_met,
                "baseline_improvement_percent": round(baseline_improvement, 2)
            },
            "optimization_effectiveness": {
                "cache_hit_rate_percent": cache_hit_rate,
                "cache_efficiency_good": cache_hit_rate > 60,
                "performance_target_met": target_met
            },
            "overall_assessment": {
                "performance_grade": overall_grade,
                "optimization_successful": target_met and cache_hit_rate > 60,
                "recommendation": "Production ready" if overall_grade in ["A+", "A"] else "Needs tuning" if overall_grade == "B" else "Significant optimization required"
            }
        }
    
    def print_results(self):
        """Print formatted benchmark results."""
        logger.info("="*80)
        logger.info("BENCHMARK RESULTS SUMMARY")
        logger.info("="*80)
        
        # Session validation results
        session_data = self.results.get("session_validation", {})
        if session_data:
            avg_time = session_data.get("response_times", {}).get("average_ms", 0)
            cache_rate = session_data.get("caching_metrics", {}).get("cache_hit_rate_percent", 0)
            target_met = avg_time < 40
            
            print(f"\nSESSION VALIDATION PERFORMANCE:")
            print(f"  Average Response Time: {avg_time:.1f}ms")
            print(f"  Target (<40ms):        {'✓ ACHIEVED' if target_met else '✗ NOT MET'}")
            print(f"  Cache Hit Rate:        {cache_rate:.1f}%")
            print(f"  Baseline Improvement:  {((176 - avg_time) / 176) * 100:.1f}%")
        
        # Performance summary
        summary = self.results.get("performance_summary", {})
        if summary:
            overall_grade = summary.get("overall_assessment", {}).get("performance_grade", "N/A")
            recommendation = summary.get("overall_assessment", {}).get("recommendation", "N/A")
            
            print(f"\nOVERALL PERFORMANCE:")
            print(f"  Grade:           {overall_grade}")
            print(f"  Recommendation:  {recommendation}")
        
        # Optimization validation
        validations = self.results.get("optimization_validation", {})
        print(f"\nOPTIMIZATION STATUS:")
        for name, data in validations.items():
            status = data.get("status", "unknown")
            print(f"  {name.replace('_', ' ').title()::<20} {status}")
        
        print("\n" + "="*80)


async def main():
    """Run the authentication performance benchmark."""
    async with AuthPerformanceBenchmark() as benchmark:
        results = await benchmark.run_complete_benchmark()
        
        # Print results to console
        benchmark.print_results()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"/home/marku/ai_workflow_engine/app/auth_performance_benchmark_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Detailed results saved to: {results_file}")
        
        return results


if __name__ == "__main__":
    asyncio.run(main())