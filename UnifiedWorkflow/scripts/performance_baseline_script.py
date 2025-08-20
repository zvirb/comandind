#!/usr/bin/env python3
"""
Comprehensive Performance Baseline and Bottleneck Analysis Script

This script establishes performance baselines and identifies bottlenecks across:
- API response times
- Database query performance 
- Redis cache performance
- Authentication flow performance
- Resource utilization patterns
- Scalability metrics
"""

import asyncio
import time
import logging
import json
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import aiohttp
import concurrent.futures
from pathlib import Path
import sys
import os

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

from shared.services.performance_monitoring_service import get_performance_monitor
from shared.services.redis_cache_service import get_redis_cache
from shared.services.query_performance_service import get_performance_summary, start_query_monitoring
from shared.utils.database_setup import get_database_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class APIEndpointMetrics:
    """Metrics for a specific API endpoint."""
    endpoint: str
    method: str
    response_count: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    error_count: int = 0
    success_rate: float = 100.0
    status_codes: Dict[int, int] = None
    
    def __post_init__(self):
        if self.status_codes is None:
            self.status_codes = {}

@dataclass
class LoginPerformanceMetrics:
    """Comprehensive login performance metrics."""
    jwt_login_time_ms: float = 0.0
    csrf_token_generation_time_ms: float = 0.0
    password_verification_time_ms: float = 0.0
    token_creation_time_ms: float = 0.0
    database_query_time_ms: float = 0.0
    total_login_time_ms: float = 0.0
    success_rate: float = 0.0
    cache_hit_rate: float = 0.0
    concurrent_login_performance: Dict[int, float] = None
    
    def __post_init__(self):
        if self.concurrent_login_performance is None:
            self.concurrent_login_performance = {}

@dataclass
class SystemResourceMetrics:
    """System resource utilization metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: List[float]
    docker_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.docker_stats is None:
            self.docker_stats = {}

class PerformanceProfiler:
    """Comprehensive performance profiler and baseline establishment."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.metrics = {
            "api_endpoints": {},
            "login_performance": LoginPerformanceMetrics(),
            "system_resources": [],
            "database_metrics": {},
            "cache_metrics": {},
            "scalability_metrics": {}
        }
        self.test_credentials = {
            "email": "admin@example.com",
            "password": "admin123"  # Default admin credentials
        }
        
    async def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run complete performance analysis and establish baselines."""
        logger.info("🚀 Starting comprehensive performance analysis...")
        
        try:
            # Phase 1: System Resource Baseline
            logger.info("📊 Phase 1: Establishing system resource baseline...")
            await self.collect_system_baseline()
            
            # Phase 2: Database Performance Analysis
            logger.info("🗄️ Phase 2: Analyzing database performance...")
            await self.analyze_database_performance()
            
            # Phase 3: Cache Performance Analysis
            logger.info("⚡ Phase 3: Analyzing Redis cache performance...")
            await self.analyze_cache_performance()
            
            # Phase 4: API Response Time Analysis
            logger.info("🌐 Phase 4: Measuring API response times...")
            await self.measure_api_response_times()
            
            # Phase 5: Login Performance Deep Dive
            logger.info("🔐 Phase 5: Profiling authentication performance...")
            await self.profile_login_performance()
            
            # Phase 6: Scalability Assessment
            logger.info("📈 Phase 6: Conducting scalability assessment...")
            await self.assess_scalability()
            
            # Generate comprehensive report
            report = await self.generate_performance_report()
            
            # Save results
            await self.save_results(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            raise

    async def collect_system_baseline(self):
        """Collect baseline system resource metrics."""
        logger.info("Collecting system resource baseline over 60 seconds...")
        
        baseline_metrics = []
        for i in range(12):  # Collect every 5 seconds for 1 minute
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory metrics  
                memory = psutil.virtual_memory()
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                
                # Network metrics
                network = psutil.net_io_counters()
                
                # Load average (Unix systems)
                load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
                
                metrics = SystemResourceMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available_gb=memory.available / (1024**3),
                    disk_usage_percent=disk.percent,
                    network_bytes_sent=network.bytes_sent,
                    network_bytes_recv=network.bytes_recv,
                    load_average=list(load_avg)
                )
                
                baseline_metrics.append(metrics)
                logger.info(f"Sample {i+1}/12: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%")
                
                if i < 11:  # Don't sleep after the last iteration
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                
        self.metrics["system_resources"] = baseline_metrics
        
        # Calculate averages
        if baseline_metrics:
            avg_cpu = sum(m.cpu_percent for m in baseline_metrics) / len(baseline_metrics)
            avg_memory = sum(m.memory_percent for m in baseline_metrics) / len(baseline_metrics)
            logger.info(f"System baseline: Avg CPU {avg_cpu:.1f}%, Avg Memory {avg_memory:.1f}%")

    async def analyze_database_performance(self):
        """Analyze database performance metrics."""
        logger.info("Analyzing database performance...")
        
        try:
            # Start query monitoring if not already running
            start_query_monitoring()
            
            # Get database health metrics
            monitor = await get_performance_monitor()
            db_metrics = await monitor.get_database_health_metrics()
            
            # Get connection pool stats
            pool_stats = get_database_stats()
            
            # Get query performance summary
            query_summary = await get_performance_summary()
            
            # Get performance recommendations
            recommendations = await monitor.get_performance_recommendations()
            
            self.metrics["database_metrics"] = {
                "health_metrics": asdict(db_metrics),
                "connection_pool_stats": pool_stats,
                "query_performance": query_summary,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Database analysis complete: "
                       f"Connections: {db_metrics.active_connections}/{db_metrics.max_connections}, "
                       f"Avg query time: {db_metrics.avg_query_time_ms:.2f}ms")
                       
        except Exception as e:
            logger.error(f"Database analysis failed: {e}")
            self.metrics["database_metrics"] = {"error": str(e)}

    async def analyze_cache_performance(self):
        """Analyze Redis cache performance."""
        logger.info("Analyzing Redis cache performance...")
        
        try:
            cache = await get_redis_cache()
            
            # Get current cache metrics
            cache_metrics = await cache.get_cache_metrics()
            
            # Test cache performance with sample operations
            cache_perf_test = await self._test_cache_performance(cache)
            
            self.metrics["cache_metrics"] = {
                "current_metrics": cache_metrics,
                "performance_test": cache_perf_test,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            hit_rate = cache_metrics.get("hit_rate_percent", 0)
            logger.info(f"Cache analysis complete: Hit rate {hit_rate:.2f}%")
            
        except Exception as e:
            logger.error(f"Cache analysis failed: {e}")
            self.metrics["cache_metrics"] = {"error": str(e)}

    async def _test_cache_performance(self, cache) -> Dict[str, Any]:
        """Test cache performance with various operations."""
        test_results = {
            "set_performance": [],
            "get_performance": [],
            "delete_performance": []
        }
        
        try:
            # Test SET operations
            for i in range(100):
                start_time = time.time()
                await cache.set(f"perf_test_{i}", {"test": "data", "index": i}, ttl=60)
                end_time = time.time()
                test_results["set_performance"].append((end_time - start_time) * 1000)
            
            # Test GET operations
            for i in range(100):
                start_time = time.time()
                await cache.get(f"perf_test_{i}")
                end_time = time.time()
                test_results["get_performance"].append((end_time - start_time) * 1000)
            
            # Test DELETE operations
            for i in range(100):
                start_time = time.time()
                await cache.delete(f"perf_test_{i}")
                end_time = time.time()
                test_results["delete_performance"].append((end_time - start_time) * 1000)
            
            # Calculate averages
            results = {}
            for operation, times in test_results.items():
                if times:
                    results[operation] = {
                        "avg_ms": sum(times) / len(times),
                        "min_ms": min(times),
                        "max_ms": max(times),
                        "operations_count": len(times)
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Cache performance test failed: {e}")
            return {"error": str(e)}

    async def measure_api_response_times(self):
        """Measure API endpoint response times."""
        logger.info("Measuring API response times...")
        
        # Key endpoints to test
        test_endpoints = [
            {"method": "GET", "path": "/health", "requires_auth": False},
            {"method": "GET", "path": "/api/v1/performance/status", "requires_auth": False},
            {"method": "GET", "path": "/api/v1/performance/health", "requires_auth": False},
            {"method": "POST", "path": "/api/v1/auth/jwt/login", "requires_auth": False},
            {"method": "GET", "path": "/api/v1/user/profile", "requires_auth": True},
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in test_endpoints:
                try:
                    metrics = await self._measure_endpoint_performance(session, endpoint)
                    endpoint_key = f"{endpoint['method']} {endpoint['path']}"
                    self.metrics["api_endpoints"][endpoint_key] = asdict(metrics)
                    
                    logger.info(f"Endpoint {endpoint_key}: Avg {metrics.avg_response_time:.2f}ms")
                    
                except Exception as e:
                    logger.error(f"Failed to measure {endpoint['path']}: {e}")

    async def _measure_endpoint_performance(self, session: aiohttp.ClientSession, endpoint: Dict[str, Any]) -> APIEndpointMetrics:
        """Measure performance of a specific endpoint."""
        metrics = APIEndpointMetrics(
            endpoint=endpoint["path"],
            method=endpoint["method"]
        )
        
        # Prepare request parameters
        url = f"{self.api_base_url}{endpoint['path']}"
        headers = {"Content-Type": "application/json"}
        
        # If auth required, get token first
        auth_token = None
        if endpoint.get("requires_auth"):
            auth_token = await self._get_auth_token(session)
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
        
        # Make multiple requests to get accurate metrics
        for i in range(50):  # 50 requests per endpoint
            try:
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    async with session.get(url, headers=headers) as response:
                        await response.text()
                        status_code = response.status
                elif endpoint["method"] == "POST":
                    data = None
                    if endpoint["path"] == "/api/v1/auth/jwt/login":
                        data = json.dumps(self.test_credentials)
                    
                    async with session.post(url, headers=headers, data=data) as response:
                        await response.text()
                        status_code = response.status
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Update metrics
                metrics.response_count += 1
                metrics.total_response_time += response_time
                metrics.min_response_time = min(metrics.min_response_time, response_time)
                metrics.max_response_time = max(metrics.max_response_time, response_time)
                
                # Track status codes
                if status_code not in metrics.status_codes:
                    metrics.status_codes[status_code] = 0
                metrics.status_codes[status_code] += 1
                
                if status_code >= 400:
                    metrics.error_count += 1
                
            except Exception as e:
                logger.warning(f"Request {i+1} to {endpoint['path']} failed: {e}")
                metrics.error_count += 1
        
        # Calculate final metrics
        if metrics.response_count > 0:
            metrics.avg_response_time = metrics.total_response_time / metrics.response_count
            successful_requests = metrics.response_count - metrics.error_count
            metrics.success_rate = (successful_requests / metrics.response_count) * 100
        
        return metrics

    async def _get_auth_token(self, session: aiohttp.ClientSession) -> Optional[str]:
        """Get authentication token for protected endpoints."""
        try:
            url = f"{self.api_base_url}/api/v1/auth/jwt/login"
            headers = {"Content-Type": "application/json"}
            data = json.dumps(self.test_credentials)
            
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("access_token")
                else:
                    logger.warning(f"Auth failed with status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            return None

    async def profile_login_performance(self):
        """Detailed profiling of login performance."""
        logger.info("Profiling login performance...")
        
        try:
            async with aiohttp.ClientSession() as session:
                login_times = []
                
                # Test login performance with multiple attempts
                for i in range(20):
                    start_time = time.time()
                    
                    # Measure full login flow
                    url = f"{self.api_base_url}/api/v1/auth/jwt/login"
                    headers = {"Content-Type": "application/json"}
                    data = json.dumps(self.test_credentials)
                    
                    async with session.post(url, headers=headers, data=data) as response:
                        await response.text()
                        status_code = response.status
                    
                    end_time = time.time()
                    login_time = (end_time - start_time) * 1000
                    
                    if status_code == 200:
                        login_times.append(login_time)
                
                # Calculate login performance metrics
                if login_times:
                    metrics = self.metrics["login_performance"]
                    metrics.total_login_time_ms = sum(login_times) / len(login_times)
                    metrics.success_rate = (len(login_times) / 20) * 100
                    
                    logger.info(f"Login performance: Avg {metrics.total_login_time_ms:.2f}ms, "
                               f"Success rate: {metrics.success_rate:.1f}%")
                
                # Test concurrent logins
                await self._test_concurrent_logins(session)
                
        except Exception as e:
            logger.error(f"Login profiling failed: {e}")

    async def _test_concurrent_logins(self, session: aiohttp.ClientSession):
        """Test login performance under concurrent load."""
        logger.info("Testing concurrent login performance...")
        
        concurrent_levels = [1, 5, 10, 20]
        
        for concurrency in concurrent_levels:
            try:
                tasks = []
                start_time = time.time()
                
                # Create concurrent login tasks
                for _ in range(concurrency):
                    task = self._single_login_request(session)
                    tasks.append(task)
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                total_time = (end_time - start_time) * 1000
                
                # Process results
                successful_logins = sum(1 for r in results if isinstance(r, float))
                avg_response_time = sum(r for r in results if isinstance(r, float)) / max(successful_logins, 1)
                
                self.metrics["login_performance"].concurrent_login_performance[concurrency] = {
                    "total_time_ms": total_time,
                    "avg_response_time_ms": avg_response_time,
                    "successful_logins": successful_logins,
                    "success_rate": (successful_logins / concurrency) * 100
                }
                
                logger.info(f"Concurrent logins ({concurrency}): "
                           f"Avg {avg_response_time:.2f}ms, "
                           f"Success: {successful_logins}/{concurrency}")
                
            except Exception as e:
                logger.error(f"Concurrent login test failed for level {concurrency}: {e}")

    async def _single_login_request(self, session: aiohttp.ClientSession) -> float:
        """Single login request for concurrent testing."""
        try:
            start_time = time.time()
            
            url = f"{self.api_base_url}/api/v1/auth/jwt/login"
            headers = {"Content-Type": "application/json"}
            data = json.dumps(self.test_credentials)
            
            async with session.post(url, headers=headers, data=data) as response:
                await response.text()
                
            end_time = time.time()
            return (end_time - start_time) * 1000
            
        except Exception as e:
            logger.error(f"Single login request failed: {e}")
            return 0.0

    async def assess_scalability(self):
        """Assess system scalability characteristics."""
        logger.info("Assessing system scalability...")
        
        try:
            # Test different load levels
            load_levels = [1, 5, 10, 25, 50]
            scalability_results = {}
            
            for load_level in load_levels:
                logger.info(f"Testing load level: {load_level} concurrent requests")
                
                # Measure system performance under load
                start_resource_usage = self._get_current_resource_usage()
                
                # Generate load
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    start_time = time.time()
                    
                    for _ in range(load_level):
                        # Mix of different endpoint requests
                        endpoints = [
                            f"{self.api_base_url}/health",
                            f"{self.api_base_url}/api/v1/performance/status"
                        ]
                        for endpoint in endpoints:
                            task = self._make_request(session, endpoint)
                            tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    end_time = time.time()
                
                end_resource_usage = self._get_current_resource_usage()
                total_time = end_time - start_time
                
                # Analyze results
                successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
                total_requests = len(results)
                throughput = total_requests / total_time
                
                scalability_results[load_level] = {
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "success_rate": (successful_requests / total_requests) * 100,
                    "total_time_seconds": total_time,
                    "throughput_rps": throughput,
                    "resource_usage_start": start_resource_usage,
                    "resource_usage_end": end_resource_usage
                }
                
                logger.info(f"Load {load_level}: {throughput:.2f} RPS, "
                           f"{(successful_requests/total_requests)*100:.1f}% success")
                
                # Wait between tests to allow system to recover
                await asyncio.sleep(5)
            
            self.metrics["scalability_metrics"] = scalability_results
            
        except Exception as e:
            logger.error(f"Scalability assessment failed: {e}")
            self.metrics["scalability_metrics"] = {"error": str(e)}

    async def _make_request(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Make a single HTTP request for scalability testing."""
        try:
            start_time = time.time()
            async with session.get(url) as response:
                await response.text()
                end_time = time.time()
                
                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "response_time_ms": (end_time - start_time) * 1000
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": 0
            }

    def _get_current_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io_read_mb": psutil.disk_io_counters().read_bytes / (1024**2),
                "disk_io_write_mb": psutil.disk_io_counters().write_bytes / (1024**2),
                "network_sent_mb": psutil.net_io_counters().bytes_sent / (1024**2),
                "network_recv_mb": psutil.net_io_counters().bytes_recv / (1024**2)
            }
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {}

    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance analysis report."""
        logger.info("Generating performance report...")
        
        report = {
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "api_base_url": self.api_base_url,
                "analysis_duration_minutes": 10,  # Approximate
                "system_info": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                    "platform": sys.platform
                }
            },
            "performance_summary": {
                "overall_health_score": self._calculate_health_score(),
                "critical_bottlenecks": self._identify_bottlenecks(),
                "performance_recommendations": self._generate_recommendations()
            },
            "detailed_metrics": self.metrics
        }
        
        return report

    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        score = 100.0
        
        try:
            # System resource score (30% weight)
            if self.metrics["system_resources"]:
                avg_cpu = sum(m.cpu_percent for m in self.metrics["system_resources"]) / len(self.metrics["system_resources"])
                avg_memory = sum(m.memory_percent for m in self.metrics["system_resources"]) / len(self.metrics["system_resources"])
                
                if avg_cpu > 80:
                    score -= 15
                elif avg_cpu > 60:
                    score -= 8
                
                if avg_memory > 90:
                    score -= 15
                elif avg_memory > 80:
                    score -= 8
            
            # API response time score (30% weight)
            api_penalties = 0
            for endpoint, metrics in self.metrics["api_endpoints"].items():
                if isinstance(metrics, dict) and "avg_response_time" in metrics:
                    avg_time = metrics["avg_response_time"]
                    if avg_time > 1000:  # > 1 second
                        api_penalties += 10
                    elif avg_time > 500:  # > 500ms
                        api_penalties += 5
            score -= min(api_penalties, 20)
            
            # Database performance score (25% weight)
            db_metrics = self.metrics.get("database_metrics", {})
            if isinstance(db_metrics, dict) and "health_metrics" in db_metrics:
                health = db_metrics["health_metrics"]
                if health.get("connection_utilization_percent", 0) > 80:
                    score -= 10
                if health.get("avg_query_time_ms", 0) > 500:
                    score -= 10
            
            # Cache performance score (15% weight)
            cache_metrics = self.metrics.get("cache_metrics", {})
            if isinstance(cache_metrics, dict) and "current_metrics" in cache_metrics:
                hit_rate = cache_metrics["current_metrics"].get("hit_rate_percent", 0)
                if hit_rate < 70:
                    score -= 10
                elif hit_rate < 85:
                    score -= 5
        
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            score = 50  # Default to moderate health if calculation fails
        
        return max(0.0, min(100.0, score))

    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify critical performance bottlenecks."""
        bottlenecks = []
        
        try:
            # System resource bottlenecks
            if self.metrics["system_resources"]:
                avg_cpu = sum(m.cpu_percent for m in self.metrics["system_resources"]) / len(self.metrics["system_resources"])
                avg_memory = sum(m.memory_percent for m in self.metrics["system_resources"]) / len(self.metrics["system_resources"])
                
                if avg_cpu > 80:
                    bottlenecks.append({
                        "type": "SYSTEM_RESOURCE",
                        "category": "CPU",
                        "severity": "HIGH",
                        "description": f"High CPU utilization: {avg_cpu:.1f}%",
                        "impact": "System performance degradation under load",
                        "recommendation": "Consider CPU optimization or scaling"
                    })
                
                if avg_memory > 90:
                    bottlenecks.append({
                        "type": "SYSTEM_RESOURCE",
                        "category": "MEMORY",
                        "severity": "CRITICAL",
                        "description": f"Critical memory usage: {avg_memory:.1f}%",
                        "impact": "Risk of OOM kills and system instability",
                        "recommendation": "Immediate memory optimization or scaling required"
                    })
            
            # API endpoint bottlenecks
            for endpoint, metrics in self.metrics["api_endpoints"].items():
                if isinstance(metrics, dict):
                    avg_time = metrics.get("avg_response_time", 0)
                    success_rate = metrics.get("success_rate", 100)
                    
                    if avg_time > 1000:
                        bottlenecks.append({
                            "type": "API_PERFORMANCE",
                            "category": "RESPONSE_TIME",
                            "severity": "HIGH",
                            "description": f"Slow API endpoint {endpoint}: {avg_time:.2f}ms",
                            "impact": "Poor user experience and potential timeouts",
                            "recommendation": "Optimize endpoint logic and database queries"
                        })
                    
                    if success_rate < 95:
                        bottlenecks.append({
                            "type": "API_RELIABILITY",
                            "category": "ERROR_RATE",
                            "severity": "HIGH",
                            "description": f"High error rate for {endpoint}: {100-success_rate:.1f}%",
                            "impact": "Service reliability issues",
                            "recommendation": "Investigate and fix error conditions"
                        })
            
            # Database bottlenecks
            db_metrics = self.metrics.get("database_metrics", {})
            if isinstance(db_metrics, dict) and "health_metrics" in db_metrics:
                health = db_metrics["health_metrics"]
                
                if health.get("connection_utilization_percent", 0) > 90:
                    bottlenecks.append({
                        "type": "DATABASE",
                        "category": "CONNECTION_POOL",
                        "severity": "CRITICAL",
                        "description": f"Database connection pool nearly exhausted: {health['connection_utilization_percent']:.1f}%",
                        "impact": "Connection timeouts and service degradation",
                        "recommendation": "Increase connection pool size or optimize connection usage"
                    })
                
                if health.get("avg_query_time_ms", 0) > 500:
                    bottlenecks.append({
                        "type": "DATABASE",
                        "category": "QUERY_PERFORMANCE",
                        "severity": "MEDIUM",
                        "description": f"Slow database queries: {health['avg_query_time_ms']:.2f}ms average",
                        "impact": "Increased response times across the application",
                        "recommendation": "Optimize slow queries and add appropriate indexes"
                    })
        
        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            bottlenecks.append({
                "type": "ANALYSIS_ERROR",
                "category": "MONITORING",
                "severity": "LOW",
                "description": f"Unable to complete bottleneck analysis: {e}",
                "impact": "Incomplete performance assessment",
                "recommendation": "Review monitoring configuration and logs"
            })
        
        return bottlenecks

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        try:
            # System optimization recommendations
            if self.metrics["system_resources"]:
                avg_cpu = sum(m.cpu_percent for m in self.metrics["system_resources"]) / len(self.metrics["system_resources"])
                
                if avg_cpu > 60:
                    recommendations.append({
                        "category": "SYSTEM_OPTIMIZATION",
                        "priority": "HIGH",
                        "title": "CPU Usage Optimization",
                        "description": "Implement CPU usage optimization strategies",
                        "actions": [
                            "Profile CPU-intensive operations",
                            "Implement async processing for heavy tasks",
                            "Consider horizontal scaling",
                            "Optimize database queries to reduce CPU load"
                        ],
                        "expected_impact": "20-30% improvement in response times"
                    })
            
            # Database optimization recommendations
            db_metrics = self.metrics.get("database_metrics", {})
            if isinstance(db_metrics, dict) and "recommendations" in db_metrics:
                db_recommendations = db_metrics["recommendations"]
                if db_recommendations:
                    recommendations.append({
                        "category": "DATABASE_OPTIMIZATION",
                        "priority": "HIGH",
                        "title": "Database Performance Tuning",
                        "description": "Address database performance issues",
                        "actions": [rec.get("action", rec.get("message", "")) for rec in db_recommendations[:3]],
                        "expected_impact": "30-50% improvement in query performance"
                    })
            
            # API optimization recommendations
            slow_endpoints = []
            for endpoint, metrics in self.metrics["api_endpoints"].items():
                if isinstance(metrics, dict) and metrics.get("avg_response_time", 0) > 200:
                    slow_endpoints.append(endpoint)
            
            if slow_endpoints:
                recommendations.append({
                    "category": "API_OPTIMIZATION",
                    "priority": "MEDIUM",
                    "title": "API Response Time Optimization",
                    "description": f"Optimize {len(slow_endpoints)} slow API endpoints",
                    "actions": [
                        "Implement response caching for frequently accessed data",
                        "Optimize database queries in slow endpoints",
                        "Add request/response compression",
                        "Consider pagination for large data sets"
                    ],
                    "expected_impact": "40-60% improvement in API response times"
                })
            
            # Cache optimization recommendations
            cache_metrics = self.metrics.get("cache_metrics", {})
            if isinstance(cache_metrics, dict) and "current_metrics" in cache_metrics:
                hit_rate = cache_metrics["current_metrics"].get("hit_rate_percent", 0)
                if hit_rate < 80:
                    recommendations.append({
                        "category": "CACHE_OPTIMIZATION",
                        "priority": "MEDIUM",
                        "title": "Cache Performance Improvement",
                        "description": f"Improve cache hit rate from {hit_rate:.1f}%",
                        "actions": [
                            "Review cache TTL settings",
                            "Implement cache warming strategies",
                            "Add caching to frequently accessed endpoints",
                            "Optimize cache key strategies"
                        ],
                        "expected_impact": "15-25% reduction in database load"
                    })
            
            # Login performance recommendations
            login_metrics = self.metrics["login_performance"]
            if login_metrics.total_login_time_ms > 500:
                recommendations.append({
                    "category": "AUTHENTICATION_OPTIMIZATION",
                    "priority": "MEDIUM",
                    "title": "Login Performance Enhancement",
                    "description": f"Optimize login flow (current: {login_metrics.total_login_time_ms:.2f}ms)",
                    "actions": [
                        "Implement password hashing optimization",
                        "Cache user authentication data",
                        "Optimize JWT token generation",
                        "Parallelize authentication steps where possible"
                    ],
                    "expected_impact": "30-40% improvement in login response time"
                })
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append({
                "category": "MONITORING",
                "priority": "LOW",
                "title": "Monitoring Configuration Review",
                "description": "Review and fix performance monitoring setup",
                "actions": [
                    "Check monitoring service configuration",
                    "Verify database connectivity for metrics",
                    "Review log files for monitoring errors"
                ],
                "expected_impact": "Improved visibility into system performance"
            })
        
        return recommendations

    async def save_results(self, report: Dict[str, Any]):
        """Save performance analysis results to file."""
        try:
            # Save detailed JSON report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"performance_analysis_{timestamp}.json"
            
            with open(json_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Save human-readable summary
            summary_filename = f"performance_summary_{timestamp}.txt"
            with open(summary_filename, 'w') as f:
                f.write("=== PERFORMANCE ANALYSIS SUMMARY ===\n")
                f.write(f"Timestamp: {report['analysis_metadata']['timestamp']}\n")
                f.write(f"Health Score: {report['performance_summary']['overall_health_score']:.1f}/100\n\n")
                
                f.write("=== CRITICAL BOTTLENECKS ===\n")
                bottlenecks = report['performance_summary']['critical_bottlenecks']
                if bottlenecks:
                    for bottleneck in bottlenecks:
                        f.write(f"- [{bottleneck['severity']}] {bottleneck['description']}\n")
                        f.write(f"  Impact: {bottleneck['impact']}\n")
                        f.write(f"  Recommendation: {bottleneck['recommendation']}\n\n")
                else:
                    f.write("No critical bottlenecks identified.\n\n")
                
                f.write("=== PERFORMANCE RECOMMENDATIONS ===\n")
                recommendations = report['performance_summary']['performance_recommendations']
                for rec in recommendations:
                    f.write(f"- [{rec['priority']}] {rec['title']}\n")
                    f.write(f"  {rec['description']}\n")
                    f.write(f"  Expected Impact: {rec['expected_impact']}\n\n")
            
            logger.info(f"Results saved to {json_filename} and {summary_filename}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

async def main():
    """Main entry point for performance analysis."""
    logger.info("Starting comprehensive performance analysis...")
    
    # Check if API is accessible
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    profiler = PerformanceProfiler(api_base_url=api_url)
    
    try:
        report = await profiler.run_comprehensive_analysis()
        
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS COMPLETE")
        print("="*60)
        print(f"Health Score: {report['performance_summary']['overall_health_score']:.1f}/100")
        print(f"Bottlenecks Found: {len(report['performance_summary']['critical_bottlenecks'])}")
        print(f"Recommendations: {len(report['performance_summary']['performance_recommendations'])}")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)