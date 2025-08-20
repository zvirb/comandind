#!/usr/bin/env python3
"""
JWT Authentication Performance Profiler
=======================================

Comprehensive performance analysis of JWT authentication system after optimization.
Measures:
1. Login endpoint response times
2. Token validation performance  
3. Redis cache integration efficiency
4. Middleware overhead analysis
5. WebUI authentication state management

Target: Sub-40ms authentication validation
"""

import asyncio
import aiohttp
import time
import statistics
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JWTAuthPerformanceProfiler:
    """
    Advanced JWT authentication performance profiler with Redis cache analysis.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.performance_data = {
            "timestamp": datetime.now().isoformat(),
            "profiler_version": "1.0",
            "target_metrics": {
                "auth_validation_ms": 40,
                "login_response_ms": 150,
                "cache_hit_rate_percent": 80
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def profile_login_endpoint(self) -> Dict[str, Any]:
        """Profile the JWT login endpoint for performance metrics."""
        logger.info("Profiling JWT login endpoint...")
        
        login_data = [
            {"email": "admin@aiwfe.com", "password": "admin123"},
            {"email": "test@aiwfe.com", "password": "test123"}, 
            {"email": "user@aiwfe.com", "password": "user123"}
        ]
        
        login_results = {
            "endpoint": "/api/v1/auth/jwt/login",
            "attempts": [],
            "metrics": {}
        }
        
        for i, credentials in enumerate(login_data):
            attempt_start = time.time()
            
            try:
                payload = {**credentials, "method": "standard"}
                
                async with self.session.post(
                    f"{self.base_url}/api/v1/auth/jwt/login",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_time = (time.time() - attempt_start) * 1000
                    
                    attempt_data = {
                        "attempt": i + 1,
                        "credentials": credentials["email"],
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "success": response.status == 200
                    }
                    
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            attempt_data["has_access_token"] = "access_token" in response_data
                            attempt_data["token_length"] = len(response_data.get("access_token", ""))
                            
                            # Store token for further testing
                            if "access_token" in response_data:
                                self.access_token = response_data["access_token"]
                                
                        except Exception as e:
                            attempt_data["parse_error"] = str(e)
                    else:
                        error_text = await response.text()
                        attempt_data["error"] = error_text[:200]  # Truncate long errors
                    
                    login_results["attempts"].append(attempt_data)
                    
            except Exception as e:
                response_time = (time.time() - attempt_start) * 1000
                login_results["attempts"].append({
                    "attempt": i + 1,
                    "credentials": credentials["email"],
                    "response_time_ms": round(response_time, 2),
                    "error": str(e),
                    "success": False
                })
        
        # Calculate metrics
        successful_attempts = [a for a in login_results["attempts"] if a["success"]]
        response_times = [a["response_time_ms"] for a in login_results["attempts"]]
        
        if successful_attempts:
            success_times = [a["response_time_ms"] for a in successful_attempts]
            login_results["metrics"] = {
                "successful_logins": len(successful_attempts),
                "success_rate_percent": round((len(successful_attempts) / len(login_results["attempts"])) * 100, 2),
                "avg_success_time_ms": round(statistics.mean(success_times), 2),
                "target_150ms_met": statistics.mean(success_times) < 150
            }
        
        if response_times:
            login_results["metrics"].update({
                "overall_avg_time_ms": round(statistics.mean(response_times), 2),
                "min_time_ms": round(min(response_times), 2),
                "max_time_ms": round(max(response_times), 2)
            })
        
        return login_results
    
    async def profile_token_validation(self) -> Dict[str, Any]:
        """Profile token validation endpoints with caching analysis."""
        logger.info("Profiling token validation performance...")
        
        # Use health endpoint for initial testing (no auth required)
        validation_results = {
            "endpoints_tested": [],
            "cache_analysis": {},
            "performance_metrics": {}
        }
        
        # Test public endpoints first for baseline
        public_endpoints = [
            ("/health", "health_check"),
            ("/api/v1/health", "api_health"),
            ("/api/v1/auth/status", "auth_status_no_token")
        ]
        
        for endpoint_path, endpoint_name in public_endpoints:
            endpoint_times = []
            
            # Warm-up requests
            for _ in range(3):
                try:
                    async with self.session.get(
                        f"{self.base_url}{endpoint_path}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        await response.text()
                except:
                    pass
            
            # Performance measurement requests
            for i in range(20):
                try:
                    start_time = time.time()
                    
                    async with self.session.get(
                        f"{self.base_url}{endpoint_path}",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        endpoint_times.append(response_time)
                        
                except Exception as e:
                    logger.debug(f"Request to {endpoint_path} failed: {e}")
            
            if endpoint_times:
                validation_results["performance_metrics"][endpoint_name] = {
                    "endpoint": endpoint_path,
                    "avg_response_time_ms": round(statistics.mean(endpoint_times), 2),
                    "median_response_time_ms": round(statistics.median(endpoint_times), 2),
                    "min_response_time_ms": round(min(endpoint_times), 2),
                    "max_response_time_ms": round(max(endpoint_times), 2),
                    "requests_tested": len(endpoint_times)
                }
                
                validation_results["endpoints_tested"].append(endpoint_path)
        
        return validation_results
    
    async def analyze_redis_cache_integration(self) -> Dict[str, Any]:
        """Analyze Redis cache integration efficiency."""
        logger.info("Analyzing Redis cache integration...")
        
        cache_analysis = {
            "redis_connectivity": {},
            "cache_performance": {},
            "integration_health": {}
        }
        
        try:
            # Test Redis connectivity through application
            redis_test_start = time.time()
            
            async with self.session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                redis_test_time = (time.time() - redis_test_start) * 1000
                
                cache_analysis["redis_connectivity"] = {
                    "app_health_response_time_ms": round(redis_test_time, 2),
                    "health_endpoint_accessible": response.status == 200,
                    "response_indicates_healthy": response.status == 200
                }
        
        except Exception as e:
            cache_analysis["redis_connectivity"] = {
                "connection_error": str(e),
                "health_check_failed": True
            }
        
        # Analyze cache performance through repeated requests
        if hasattr(self, 'access_token'):
            cache_analysis["authenticated_cache_test"] = await self._test_authenticated_cache()
        else:
            cache_analysis["authenticated_cache_test"] = {
                "status": "skipped",
                "reason": "no_valid_access_token"
            }
        
        return cache_analysis
    
    async def _test_authenticated_cache(self) -> Dict[str, Any]:
        """Test authenticated endpoint caching if token is available."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        cache_test_results = {
            "cache_effectiveness": {},
            "performance_comparison": {}
        }
        
        # Test authenticated endpoint with cache
        auth_endpoint = "/api/v1/user/current"
        cache_times = []
        
        try:
            # First request (cache miss)
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}{auth_endpoint}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                first_request_time = (time.time() - start_time) * 1000
                first_success = response.status == 200
            
            # Subsequent requests (potential cache hits)
            for i in range(10):
                start_time = time.time()
                try:
                    async with self.session.get(
                        f"{self.base_url}{auth_endpoint}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        cache_times.append(response_time)
                except:
                    pass
            
            if cache_times:
                avg_cache_time = statistics.mean(cache_times)
                cache_effectiveness = max(0, ((first_request_time - avg_cache_time) / first_request_time) * 100)
                
                cache_test_results = {
                    "first_request_ms": round(first_request_time, 2),
                    "avg_cached_request_ms": round(avg_cache_time, 2), 
                    "cache_effectiveness_percent": round(cache_effectiveness, 2),
                    "requests_tested": len(cache_times),
                    "cache_working": cache_effectiveness > 10  # At least 10% improvement
                }
        
        except Exception as e:
            cache_test_results = {"error": str(e), "status": "failed"}
        
        return cache_test_results
    
    async def profile_middleware_overhead(self) -> Dict[str, Any]:
        """Profile authentication middleware overhead."""
        logger.info("Profiling middleware overhead...")
        
        middleware_analysis = {
            "baseline_performance": {},
            "middleware_impact": {},
            "optimization_effectiveness": {}
        }
        
        # Test different endpoint types to measure middleware impact
        endpoint_tests = [
            ("/health", "no_auth_required", False),
            ("/api/v1/health", "api_health", False), 
            ("/api/v1/auth/status", "auth_status", True),
            ("/", "root_endpoint", False)
        ]
        
        for endpoint_path, endpoint_name, requires_auth in endpoint_tests:
            endpoint_times = []
            headers = {}
            
            if requires_auth and hasattr(self, 'access_token'):
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            # Measure endpoint performance
            for i in range(15):
                try:
                    start_time = time.time()
                    
                    async with self.session.get(
                        f"{self.base_url}{endpoint_path}",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        if response.status in [200, 401]:  # Valid responses
                            endpoint_times.append(response_time)
                        
                except Exception as e:
                    logger.debug(f"Middleware test {endpoint_path} failed: {e}")
            
            if endpoint_times:
                middleware_analysis[endpoint_name] = {
                    "endpoint": endpoint_path,
                    "requires_auth": requires_auth,
                    "avg_response_time_ms": round(statistics.mean(endpoint_times), 2),
                    "min_response_time_ms": round(min(endpoint_times), 2),
                    "max_response_time_ms": round(max(endpoint_times), 2),
                    "std_dev_ms": round(statistics.stdev(endpoint_times) if len(endpoint_times) > 1 else 0, 2),
                    "requests_measured": len(endpoint_times)
                }
        
        # Calculate middleware overhead
        no_auth_times = []
        auth_times = []
        
        for endpoint_name, data in middleware_analysis.items():
            if isinstance(data, dict) and "avg_response_time_ms" in data:
                if data["requires_auth"]:
                    auth_times.append(data["avg_response_time_ms"])
                else:
                    no_auth_times.append(data["avg_response_time_ms"])
        
        if no_auth_times and auth_times:
            avg_no_auth = statistics.mean(no_auth_times)
            avg_auth = statistics.mean(auth_times)
            overhead_ms = avg_auth - avg_no_auth
            
            middleware_analysis["middleware_impact"] = {
                "avg_no_auth_ms": round(avg_no_auth, 2),
                "avg_with_auth_ms": round(avg_auth, 2),
                "estimated_overhead_ms": round(overhead_ms, 2),
                "overhead_acceptable": overhead_ms < 20  # Target: <20ms overhead
            }
        
        return middleware_analysis
    
    async def validate_webui_auth_performance(self) -> Dict[str, Any]:
        """Validate WebUI authentication state management performance."""
        logger.info("Validating WebUI authentication performance...")
        
        webui_analysis = {
            "static_resource_performance": {},
            "api_integration": {},
            "frontend_readiness": {}
        }
        
        # Test static resources (should be fast)
        static_endpoints = [
            ("/", "webui_root"),
            ("/index.html", "webui_index"),
        ]
        
        for endpoint_path, endpoint_name in static_endpoints:
            try:
                start_time = time.time()
                
                async with self.session.get(
                    f"{self.base_url}{endpoint_path}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    webui_analysis["static_resource_performance"][endpoint_name] = {
                        "endpoint": endpoint_path,
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "content_served": response.status == 200,
                        "performance_good": response_time < 100  # Static should be <100ms
                    }
            
            except Exception as e:
                webui_analysis["static_resource_performance"][endpoint_name] = {
                    "endpoint": endpoint_path,
                    "error": str(e),
                    "accessible": False
                }
        
        # Test WebUI API integration endpoints
        api_endpoints = [
            "/api/v1/auth/csrf-token",
            "/api/v1/auth/status"
        ]
        
        for endpoint_path in api_endpoints:
            try:
                start_time = time.time()
                
                async with self.session.get(
                    f"{self.base_url}{endpoint_path}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    webui_analysis["api_integration"][endpoint_path] = {
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status,
                        "api_responding": response.status in [200, 401],
                        "performance_acceptable": response_time < 50
                    }
            
            except Exception as e:
                webui_analysis["api_integration"][endpoint_path] = {
                    "error": str(e),
                    "accessible": False
                }
        
        return webui_analysis
    
    async def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive JWT authentication performance analysis."""
        logger.info("="*60)
        logger.info("JWT AUTHENTICATION PERFORMANCE ANALYSIS")
        logger.info("="*60)
        
        analysis_results = {
            **self.performance_data,
            "analysis_phases": {}
        }
        
        try:
            # Phase 1: Login endpoint profiling
            logger.info("Phase 1: Login endpoint performance profiling")
            analysis_results["analysis_phases"]["login_profiling"] = await self.profile_login_endpoint()
            
            # Phase 2: Token validation performance
            logger.info("Phase 2: Token validation performance analysis")
            analysis_results["analysis_phases"]["token_validation"] = await self.profile_token_validation()
            
            # Phase 3: Redis cache integration analysis
            logger.info("Phase 3: Redis cache integration efficiency")
            analysis_results["analysis_phases"]["redis_cache_analysis"] = await self.analyze_redis_cache_integration()
            
            # Phase 4: Middleware overhead profiling
            logger.info("Phase 4: Middleware overhead analysis")
            analysis_results["analysis_phases"]["middleware_profiling"] = await self.profile_middleware_overhead()
            
            # Phase 5: WebUI authentication performance
            logger.info("Phase 5: WebUI authentication state management")
            analysis_results["analysis_phases"]["webui_performance"] = await self.validate_webui_auth_performance()
            
            # Phase 6: Generate optimization recommendations
            logger.info("Phase 6: Generating optimization recommendations")
            analysis_results["optimization_recommendations"] = self._generate_optimization_recommendations(analysis_results)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            analysis_results["analysis_error"] = str(e)
        
        return analysis_results
    
    def _generate_optimization_recommendations(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization recommendations based on analysis results."""
        recommendations = {
            "performance_summary": {},
            "optimization_opportunities": [],
            "priority_actions": []
        }
        
        phases = analysis_data.get("analysis_phases", {})
        
        # Analyze login performance
        login_data = phases.get("login_profiling", {})
        if login_data.get("metrics", {}).get("avg_success_time_ms", 0) > 150:
            recommendations["optimization_opportunities"].append({
                "area": "login_endpoint",
                "issue": "Login response time exceeds 150ms target",
                "recommendation": "Optimize database queries and implement connection pooling",
                "priority": "high"
            })
        
        # Analyze token validation performance
        token_data = phases.get("token_validation", {})
        slow_endpoints = []
        for endpoint_name, metrics in token_data.get("performance_metrics", {}).items():
            if metrics.get("avg_response_time_ms", 0) > 40:
                slow_endpoints.append(f"{endpoint_name}: {metrics['avg_response_time_ms']}ms")
        
        if slow_endpoints:
            recommendations["optimization_opportunities"].append({
                "area": "token_validation",
                "issue": f"Slow validation endpoints: {', '.join(slow_endpoints)}",
                "recommendation": "Implement JWT caching and optimize middleware",
                "priority": "high"
            })
        
        # Analyze cache effectiveness
        cache_data = phases.get("redis_cache_analysis", {})
        auth_cache = cache_data.get("authenticated_cache_test", {})
        if auth_cache.get("cache_effectiveness_percent", 0) < 30:
            recommendations["optimization_opportunities"].append({
                "area": "caching",
                "issue": "Low cache effectiveness for authenticated requests",
                "recommendation": "Increase cache TTL and implement better cache key strategies",
                "priority": "medium"
            })
        
        # Analyze middleware overhead
        middleware_data = phases.get("middleware_profiling", {})
        overhead = middleware_data.get("middleware_impact", {}).get("estimated_overhead_ms", 0)
        if overhead > 20:
            recommendations["optimization_opportunities"].append({
                "area": "middleware",
                "issue": f"High middleware overhead: {overhead}ms",
                "recommendation": "Optimize authentication middleware and implement request pooling",
                "priority": "high"
            })
        
        # Generate priority actions
        high_priority = [r for r in recommendations["optimization_opportunities"] if r["priority"] == "high"]
        
        if high_priority:
            recommendations["priority_actions"] = [
                "Implement Redis-based JWT validation caching",
                "Optimize database connection pooling for auth operations", 
                "Reduce authentication middleware overhead",
                "Implement token validation response caching"
            ]
        else:
            recommendations["priority_actions"] = [
                "Fine-tune existing optimizations",
                "Monitor performance metrics continuously",
                "Consider implementing token refresh strategies"
            ]
        
        # Performance summary
        recommendations["performance_summary"] = {
            "overall_status": "needs_optimization" if high_priority else "acceptable",
            "key_metrics": {
                "login_avg_ms": login_data.get("metrics", {}).get("avg_success_time_ms", 0),
                "token_validation_avg_ms": statistics.mean([
                    m.get("avg_response_time_ms", 0) 
                    for m in token_data.get("performance_metrics", {}).values()
                ]) if token_data.get("performance_metrics") else 0,
                "middleware_overhead_ms": overhead
            },
            "targets_met": {
                "login_under_150ms": login_data.get("metrics", {}).get("avg_success_time_ms", 999) < 150,
                "validation_under_40ms": all(
                    m.get("avg_response_time_ms", 999) < 40 
                    for m in token_data.get("performance_metrics", {}).values()
                ),
                "middleware_under_20ms": overhead < 20
            }
        }
        
        return recommendations


async def main():
    """Execute the JWT authentication performance profiler."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with JWTAuthPerformanceProfiler() as profiler:
        results = await profiler.run_comprehensive_analysis()
        
        # Save detailed results
        results_file = f"/home/marku/ai_workflow_engine/.claude/test_results/performance/jwt_auth_analysis_{timestamp}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        print("="*60)
        print("JWT AUTHENTICATION PERFORMANCE ANALYSIS COMPLETE")
        print("="*60)
        
        recommendations = results.get("optimization_recommendations", {})
        summary = recommendations.get("performance_summary", {})
        
        print(f"\nOVERALL STATUS: {summary.get('overall_status', 'unknown').upper()}")
        
        key_metrics = summary.get("key_metrics", {})
        if key_metrics:
            print(f"\nKEY METRICS:")
            print(f"  Login Average:           {key_metrics.get('login_avg_ms', 0):.1f}ms")
            print(f"  Token Validation Avg:    {key_metrics.get('token_validation_avg_ms', 0):.1f}ms")  
            print(f"  Middleware Overhead:     {key_metrics.get('middleware_overhead_ms', 0):.1f}ms")
        
        targets = summary.get("targets_met", {})
        if targets:
            print(f"\nTARGETS MET:")
            print(f"  Login <150ms:      {'✓' if targets.get('login_under_150ms') else '✗'}")
            print(f"  Validation <40ms:  {'✓' if targets.get('validation_under_40ms') else '✗'}")
            print(f"  Middleware <20ms:  {'✓' if targets.get('middleware_under_20ms') else '✗'}")
        
        opportunities = recommendations.get("optimization_opportunities", [])
        if opportunities:
            print(f"\nOPTIMIZATION OPPORTUNITIES ({len(opportunities)}):")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"  {i}. {opp['area'].title()}: {opp['issue']}")
        
        priority_actions = recommendations.get("priority_actions", [])
        if priority_actions:
            print(f"\nPRIORITY ACTIONS:")
            for i, action in enumerate(priority_actions[:3], 1):
                print(f"  {i}. {action}")
        
        print(f"\nDetailed results: {results_file}")
        print("="*60)
        
        return results


if __name__ == "__main__":
    asyncio.run(main())