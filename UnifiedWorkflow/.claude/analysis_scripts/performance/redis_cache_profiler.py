#!/usr/bin/env python3
"""
Redis Cache Integration Performance Profiler
===========================================

Analyzes Redis cache performance for JWT authentication system:
1. Redis connection performance
2. Cache hit/miss ratios
3. Cache response time optimization
4. Memory usage and efficiency
5. Cache invalidation performance

Target: >80% cache hit rate, <5ms cache response time
"""

import asyncio
import time
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

try:
    import redis.asyncio as redis
    import aiohttp
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCachePerformanceProfiler:
    """
    Comprehensive Redis cache performance profiler for JWT authentication.
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client: Optional[redis.Redis] = None
        self.performance_data = {
            "timestamp": datetime.now().isoformat(),
            "profiler_version": "1.0",
            "redis_config": {
                "host": redis_host,
                "port": redis_port
            },
            "target_metrics": {
                "cache_hit_rate_percent": 80,
                "cache_response_time_ms": 5,
                "redis_connection_time_ms": 10
            }
        }
    
    async def __aenter__(self):
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to create Redis client: {e}")
                self.redis_client = None
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.debug(f"Error closing Redis client: {e}")
    
    async def test_redis_connectivity(self) -> Dict[str, Any]:
        """Test basic Redis connectivity and response times."""
        logger.info("Testing Redis connectivity...")
        
        connectivity_results = {
            "connection_test": {},
            "basic_operations": {},
            "performance_metrics": {}
        }
        
        if not REDIS_AVAILABLE:
            connectivity_results["connection_test"] = {
                "status": "error",
                "error": "Redis library not available"
            }
            return connectivity_results
        
        if not self.redis_client:
            connectivity_results["connection_test"] = {
                "status": "error", 
                "error": "Redis client not initialized"
            }
            return connectivity_results
        
        try:
            # Test connection
            start_time = time.time()
            await self.redis_client.ping()
            connection_time = (time.time() - start_time) * 1000
            
            connectivity_results["connection_test"] = {
                "status": "success",
                "connection_time_ms": round(connection_time, 2),
                "connection_fast": connection_time < 10
            }
            
            # Test basic operations
            operation_times = {}
            
            # SET operation
            start_time = time.time()
            await self.redis_client.set("test_key", "test_value", ex=30)
            set_time = (time.time() - start_time) * 1000
            operation_times["set_ms"] = round(set_time, 2)
            
            # GET operation
            start_time = time.time()
            value = await self.redis_client.get("test_key")
            get_time = (time.time() - start_time) * 1000
            operation_times["get_ms"] = round(get_time, 2)
            
            # DELETE operation
            start_time = time.time()
            await self.redis_client.delete("test_key")
            del_time = (time.time() - start_time) * 1000
            operation_times["del_ms"] = round(del_time, 2)
            
            connectivity_results["basic_operations"] = {
                "operations_successful": value == "test_value",
                "operation_times": operation_times,
                "all_operations_fast": all(t < 5 for t in operation_times.values())
            }
            
            # Get Redis info
            try:
                redis_info = await self.redis_client.info()
                connectivity_results["redis_info"] = {
                    "version": redis_info.get("redis_version", "unknown"),
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory": redis_info.get("used_memory_human", "unknown"),
                    "total_commands_processed": redis_info.get("total_commands_processed", 0)
                }
            except Exception as e:
                logger.debug(f"Could not get Redis info: {e}")
            
        except Exception as e:
            connectivity_results["connection_test"] = {
                "status": "error",
                "error": str(e)
            }
        
        return connectivity_results
    
    async def profile_cache_operations(self) -> Dict[str, Any]:
        """Profile cache operations performance for JWT-related data."""
        logger.info("Profiling cache operations...")
        
        cache_operations = {
            "auth_cache_simulation": {},
            "performance_benchmarks": {},
            "efficiency_analysis": {}
        }
        
        if not self.redis_client:
            cache_operations["error"] = "Redis client not available"
            return cache_operations
        
        try:
            # Simulate JWT cache operations
            auth_cache_times = []
            jwt_tokens = []
            
            # Generate test JWT cache data
            for i in range(50):
                token_hash = f"auth_cache:token:{i:03d}"
                user_data = {
                    "user_id": i + 1,
                    "email": f"user{i}@test.com",
                    "role": "user",
                    "cached_at": time.time()
                }
                jwt_tokens.append((token_hash, json.dumps(user_data)))
            
            # Benchmark SET operations
            set_times = []
            for token_hash, user_data in jwt_tokens[:25]:
                start_time = time.time()
                await self.redis_client.setex(token_hash, 300, user_data)  # 5 min TTL
                set_time = (time.time() - start_time) * 1000
                set_times.append(set_time)
            
            # Benchmark GET operations (cache hits)
            get_times = []
            cache_hits = 0
            for token_hash, _ in jwt_tokens[:25]:
                start_time = time.time()
                cached_data = await self.redis_client.get(token_hash)
                get_time = (time.time() - start_time) * 1000
                get_times.append(get_time)
                if cached_data:
                    cache_hits += 1
            
            # Test cache misses
            miss_times = []
            for i in range(10):
                start_time = time.time()
                await self.redis_client.get(f"auth_cache:nonexistent:{i}")
                miss_time = (time.time() - start_time) * 1000
                miss_times.append(miss_time)
            
            cache_operations["auth_cache_simulation"] = {
                "tokens_cached": len(set_times),
                "cache_hits": cache_hits,
                "cache_hit_rate_percent": round((cache_hits / len(jwt_tokens[:25])) * 100, 2),
                "avg_set_time_ms": round(statistics.mean(set_times), 2),
                "avg_get_time_ms": round(statistics.mean(get_times), 2),
                "avg_miss_time_ms": round(statistics.mean(miss_times), 2)
            }
            
            # Performance benchmarks
            cache_operations["performance_benchmarks"] = {
                "set_operations": {
                    "avg_ms": round(statistics.mean(set_times), 2),
                    "min_ms": round(min(set_times), 2),
                    "max_ms": round(max(set_times), 2),
                    "target_5ms_met": statistics.mean(set_times) < 5
                },
                "get_operations": {
                    "avg_ms": round(statistics.mean(get_times), 2),
                    "min_ms": round(min(get_times), 2),
                    "max_ms": round(max(get_times), 2),
                    "target_5ms_met": statistics.mean(get_times) < 5
                },
                "miss_operations": {
                    "avg_ms": round(statistics.mean(miss_times), 2),
                    "faster_than_hits": statistics.mean(miss_times) < statistics.mean(get_times)
                }
            }
            
            # Efficiency analysis
            total_cache_time = sum(get_times)
            simulated_db_time = len(get_times) * 50  # Assume 50ms per DB query
            time_saved = simulated_db_time - total_cache_time
            efficiency_percent = (time_saved / simulated_db_time) * 100
            
            cache_operations["efficiency_analysis"] = {
                "total_cache_time_ms": round(total_cache_time, 2),
                "simulated_db_time_ms": simulated_db_time,
                "time_saved_ms": round(time_saved, 2),
                "efficiency_percent": round(efficiency_percent, 2),
                "cache_worthwhile": efficiency_percent > 50
            }
            
            # Cleanup test data
            for token_hash, _ in jwt_tokens:
                await self.redis_client.delete(token_hash)
            
        except Exception as e:
            cache_operations["error"] = str(e)
            logger.error(f"Cache operations profiling failed: {e}")
        
        return cache_operations
    
    async def analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze Redis memory usage and optimization opportunities."""
        logger.info("Analyzing Redis memory usage...")
        
        memory_analysis = {
            "current_usage": {},
            "key_analysis": {},
            "optimization_recommendations": []
        }
        
        if not self.redis_client:
            memory_analysis["error"] = "Redis client not available"
            return memory_analysis
        
        try:
            # Get memory info
            memory_info = await self.redis_client.info("memory")
            
            memory_analysis["current_usage"] = {
                "used_memory_human": memory_info.get("used_memory_human", "unknown"),
                "used_memory_peak_human": memory_info.get("used_memory_peak_human", "unknown"),
                "used_memory_rss_human": memory_info.get("used_memory_rss_human", "unknown"),
                "mem_fragmentation_ratio": memory_info.get("mem_fragmentation_ratio", 0)
            }
            
            # Analyze existing keys
            auth_keys = []
            async for key in self.redis_client.scan_iter(match="auth_cache:*", count=100):
                auth_keys.append(key)
            
            # Sample key analysis
            if auth_keys:
                sample_keys = auth_keys[:10]
                key_sizes = []
                key_ttls = []
                
                for key in sample_keys:
                    try:
                        # Get key size (approximate)
                        value = await self.redis_client.get(key)
                        if value:
                            key_sizes.append(len(value))
                        
                        # Get TTL
                        ttl = await self.redis_client.ttl(key)
                        if ttl > 0:
                            key_ttls.append(ttl)
                    except:
                        pass
                
                memory_analysis["key_analysis"] = {
                    "total_auth_keys": len(auth_keys),
                    "sample_keys_analyzed": len(sample_keys),
                    "avg_key_size_bytes": round(statistics.mean(key_sizes), 2) if key_sizes else 0,
                    "avg_ttl_seconds": round(statistics.mean(key_ttls), 2) if key_ttls else 0,
                    "keys_with_ttl": len(key_ttls)
                }
            else:
                memory_analysis["key_analysis"] = {
                    "total_auth_keys": 0,
                    "no_auth_keys_found": True
                }
            
            # Generate optimization recommendations
            fragmentation = memory_info.get("mem_fragmentation_ratio", 0)
            if fragmentation > 1.5:
                memory_analysis["optimization_recommendations"].append(
                    "High memory fragmentation detected - consider Redis restart"
                )
            
            if len(auth_keys) > 1000:
                memory_analysis["optimization_recommendations"].append(
                    "Large number of auth keys - implement key expiration cleanup"
                )
            
            if not memory_analysis["optimization_recommendations"]:
                memory_analysis["optimization_recommendations"].append(
                    "Memory usage appears optimal"
                )
            
        except Exception as e:
            memory_analysis["error"] = str(e)
            logger.error(f"Memory analysis failed: {e}")
        
        return memory_analysis
    
    async def test_concurrent_cache_performance(self) -> Dict[str, Any]:
        """Test cache performance under concurrent load."""
        logger.info("Testing concurrent cache performance...")
        
        concurrent_results = {
            "test_parameters": {},
            "performance_metrics": {},
            "scalability_analysis": {}
        }
        
        if not self.redis_client:
            concurrent_results["error"] = "Redis client not available"
            return concurrent_results
        
        try:
            concurrent_requests = 50
            cache_keys = [f"concurrent_test:{i}" for i in range(concurrent_requests)]
            
            concurrent_results["test_parameters"] = {
                "concurrent_requests": concurrent_requests,
                "test_keys": len(cache_keys)
            }
            
            # Pre-populate cache with test data
            for key in cache_keys:
                await self.redis_client.setex(key, 60, f"test_data_{key}")
            
            async def single_cache_operation(key: str) -> float:
                start_time = time.time()
                await self.redis_client.get(key)
                return (time.time() - start_time) * 1000
            
            # Execute concurrent GET operations
            start_time = time.time()
            response_times = await asyncio.gather(
                *[single_cache_operation(key) for key in cache_keys]
            )
            total_time = (time.time() - start_time) * 1000
            
            # Calculate metrics
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            concurrent_results["performance_metrics"] = {
                "total_execution_time_ms": round(total_time, 2),
                "avg_response_time_ms": round(avg_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2),
                "throughput_ops_per_second": round(concurrent_requests / (total_time / 1000), 2)
            }
            
            # Scalability analysis
            performance_degradation = (max_response_time / min_response_time) * 100 - 100
            
            concurrent_results["scalability_analysis"] = {
                "performance_degradation_percent": round(performance_degradation, 2),
                "consistent_performance": performance_degradation < 50,
                "high_throughput": (concurrent_requests / (total_time / 1000)) > 1000,
                "target_5ms_met_under_load": avg_response_time < 5
            }
            
            # Cleanup
            for key in cache_keys:
                await self.redis_client.delete(key)
            
        except Exception as e:
            concurrent_results["error"] = str(e)
            logger.error(f"Concurrent performance test failed: {e}")
        
        return concurrent_results
    
    async def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive Redis cache performance analysis."""
        logger.info("="*60)
        logger.info("REDIS CACHE PERFORMANCE ANALYSIS")
        logger.info("="*60)
        
        analysis_results = {
            **self.performance_data,
            "analysis_phases": {}
        }
        
        try:
            # Phase 1: Connectivity testing
            logger.info("Phase 1: Redis connectivity and basic operations")
            analysis_results["analysis_phases"]["connectivity"] = await self.test_redis_connectivity()
            
            # Phase 2: Cache operations profiling
            logger.info("Phase 2: Cache operations performance profiling")  
            analysis_results["analysis_phases"]["cache_operations"] = await self.profile_cache_operations()
            
            # Phase 3: Memory usage analysis
            logger.info("Phase 3: Memory usage and optimization analysis")
            analysis_results["analysis_phases"]["memory_analysis"] = await self.analyze_memory_usage()
            
            # Phase 4: Concurrent performance testing
            logger.info("Phase 4: Concurrent cache performance testing")
            analysis_results["analysis_phases"]["concurrent_performance"] = await self.test_concurrent_cache_performance()
            
            # Phase 5: Generate recommendations
            logger.info("Phase 5: Generating optimization recommendations")
            analysis_results["optimization_recommendations"] = self._generate_cache_recommendations(analysis_results)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            analysis_results["analysis_error"] = str(e)
        
        return analysis_results
    
    def _generate_cache_recommendations(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Redis cache optimization recommendations."""
        recommendations = {
            "performance_summary": {},
            "optimization_opportunities": [],
            "priority_actions": []
        }
        
        phases = analysis_data.get("analysis_phases", {})
        
        # Analyze connectivity
        connectivity = phases.get("connectivity", {})
        connection_test = connectivity.get("connection_test", {})
        if connection_test.get("status") != "success":
            recommendations["optimization_opportunities"].append({
                "area": "connectivity",
                "issue": "Redis connection issues detected",
                "recommendation": "Check Redis server status and network connectivity",
                "priority": "critical"
            })
        
        # Analyze cache operations
        cache_ops = phases.get("cache_operations", {})
        auth_cache = cache_ops.get("auth_cache_simulation", {})
        
        cache_hit_rate = auth_cache.get("cache_hit_rate_percent", 0)
        if cache_hit_rate < 80:
            recommendations["optimization_opportunities"].append({
                "area": "cache_hit_rate",
                "issue": f"Cache hit rate below target: {cache_hit_rate}%",
                "recommendation": "Increase cache TTL and optimize cache key strategies",
                "priority": "high"
            })
        
        # Analyze response times
        benchmarks = cache_ops.get("performance_benchmarks", {})
        get_ops = benchmarks.get("get_operations", {})
        if not get_ops.get("target_5ms_met", True):
            recommendations["optimization_opportunities"].append({
                "area": "response_time",
                "issue": f"Cache GET operations exceed 5ms target",
                "recommendation": "Optimize Redis configuration and consider Redis clustering",
                "priority": "medium"
            })
        
        # Analyze memory usage
        memory = phases.get("memory_analysis", {})
        memory_recs = memory.get("optimization_recommendations", [])
        if "fragmentation" in str(memory_recs).lower():
            recommendations["optimization_opportunities"].append({
                "area": "memory",
                "issue": "High memory fragmentation detected",
                "recommendation": "Schedule Redis restart during maintenance window",
                "priority": "medium"
            })
        
        # Generate priority actions
        critical_issues = [r for r in recommendations["optimization_opportunities"] if r["priority"] == "critical"]
        high_issues = [r for r in recommendations["optimization_opportunities"] if r["priority"] == "high"]
        
        if critical_issues:
            recommendations["priority_actions"] = [
                "Fix Redis connectivity issues immediately",
                "Verify Redis server health and configuration",
                "Check network connectivity and firewall settings"
            ]
        elif high_issues:
            recommendations["priority_actions"] = [
                "Optimize cache TTL settings for better hit rates",
                "Implement cache warming strategies",
                "Review and optimize cache key patterns"
            ]
        else:
            recommendations["priority_actions"] = [
                "Monitor cache performance metrics continuously",
                "Consider implementing cache analytics",
                "Evaluate horizontal scaling options"
            ]
        
        # Performance summary
        recommendations["performance_summary"] = {
            "overall_status": "critical" if critical_issues else "needs_optimization" if high_issues else "good",
            "key_metrics": {
                "connection_time_ms": connection_test.get("connection_time_ms", 0),
                "cache_hit_rate_percent": cache_hit_rate,
                "avg_get_time_ms": get_ops.get("avg_ms", 0)
            },
            "targets_met": {
                "connection_under_10ms": connection_test.get("connection_fast", False),
                "cache_hit_rate_over_80": cache_hit_rate >= 80,
                "get_operations_under_5ms": get_ops.get("target_5ms_met", False)
            }
        }
        
        return recommendations


async def main():
    """Execute the Redis cache performance profiler."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with RedisCachePerformanceProfiler() as profiler:
        results = await profiler.run_comprehensive_analysis()
        
        # Save detailed results
        results_file = f"/home/marku/ai_workflow_engine/.claude/test_results/performance/redis_cache_analysis_{timestamp}.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        print("="*60)
        print("REDIS CACHE PERFORMANCE ANALYSIS COMPLETE")
        print("="*60)
        
        recommendations = results.get("optimization_recommendations", {})
        summary = recommendations.get("performance_summary", {})
        
        print(f"\nOVERALL STATUS: {summary.get('overall_status', 'unknown').upper()}")
        
        key_metrics = summary.get("key_metrics", {})
        if key_metrics:
            print(f"\nKEY METRICS:")
            print(f"  Connection Time:      {key_metrics.get('connection_time_ms', 0):.2f}ms")
            print(f"  Cache Hit Rate:       {key_metrics.get('cache_hit_rate_percent', 0):.1f}%")
            print(f"  Avg GET Time:         {key_metrics.get('avg_get_time_ms', 0):.2f}ms")
        
        targets = summary.get("targets_met", {})
        if targets:
            print(f"\nTARGETS MET:")
            print(f"  Connection <10ms:     {'✓' if targets.get('connection_under_10ms') else '✗'}")
            print(f"  Hit Rate >80%:        {'✓' if targets.get('cache_hit_rate_over_80') else '✗'}")
            print(f"  GET Ops <5ms:         {'✓' if targets.get('get_operations_under_5ms') else '✗'}")
        
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