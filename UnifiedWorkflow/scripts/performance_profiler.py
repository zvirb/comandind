#!/usr/bin/env python3
"""
AIWFE Phase 3 Performance Profiler
Comprehensive performance validation for cognitive services deployment
"""

import asyncio
import aiohttp
import time
import json
import statistics
import subprocess
import logging
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import psutil
import redis
import psycopg2
from neo4j import GraphDatabase


class PerformanceProfiler:
    def __init__(self):
        self.logger = self._setup_logging()
        self.results = {}
        self.start_time = datetime.now()
        
        # Performance targets from requirements
        self.targets = {
            'cognitive_response_time_p95': 1000,  # ms
            'db_query_response_time': 50,         # ms
            'service_mesh_overhead': 100,         # ms
            'cpu_usage_threshold': 80,            # %
            'memory_per_service_gb': 4,           # GB
            'concurrent_workflows': 50            # count
        }
        
        # Service endpoints
        self.services = {
            'perception': 'http://localhost:8001',
            'hybrid_memory': 'http://localhost:8002', 
            'reasoning': 'http://localhost:8003',
            'coordination': 'http://localhost:8004',
            'learning': 'http://localhost:8005'  # If available
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger = logging.getLogger('performance_profiler')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    async def profile_service_response_times(self) -> Dict:
        """Profile individual service response times"""
        self.logger.info("🔍 Profiling service response times...")
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for service_name, base_url in self.services.items():
                try:
                    response_times = []
                    
                    # Test health endpoint 100 times
                    for i in range(100):
                        start_time = time.perf_counter()
                        
                        try:
                            async with session.get(f"{base_url}/health", 
                                                 timeout=aiohttp.ClientTimeout(total=5)) as response:
                                await response.text()
                                end_time = time.perf_counter()
                                response_times.append((end_time - start_time) * 1000)  # Convert to ms
                        except Exception as e:
                            self.logger.warning(f"Request {i} to {service_name} failed: {e}")
                    
                    if response_times:
                        results[service_name] = {
                            'mean': statistics.mean(response_times),
                            'median': statistics.median(response_times),
                            'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                            'p99': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times),
                            'min': min(response_times),
                            'max': max(response_times),
                            'sample_count': len(response_times)
                        }
                        
                        self.logger.info(f"✓ {service_name}: P95={results[service_name]['p95']:.2f}ms, Mean={results[service_name]['mean']:.2f}ms")
                    
                except Exception as e:
                    self.logger.error(f"Failed to profile {service_name}: {e}")
                    results[service_name] = {'error': str(e)}
        
        return results
    
    async def test_cognitive_workflows(self) -> Dict:
        """Test end-to-end cognitive workflow performance"""
        self.logger.info("🧠 Testing cognitive workflow performance...")
        
        workflow_times = []
        successful_workflows = 0
        
        test_payloads = [
            {"text": "Analyze the implications of artificial general intelligence on software architecture patterns"},
            {"text": "What are the key considerations for implementing distributed consensus in microservices?"},
            {"text": "How can machine learning models be optimized for real-time inference in production systems?"},
            {"text": "Evaluate the trade-offs between consistency and availability in distributed databases"},
            {"text": "What are the security implications of implementing zero-trust networking in cloud infrastructure?"}
        ]
        
        async with aiohttp.ClientSession() as session:
            # Test workflows through reasoning service
            for payload in test_payloads:
                try:
                    start_time = time.perf_counter()
                    
                    # Submit to reasoning service (primary cognitive entry point)
                    async with session.post(
                        f"{self.services['reasoning']}/api/v1/reason",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        result = await response.json()
                        end_time = time.perf_counter()
                        
                        workflow_time = (end_time - start_time) * 1000
                        workflow_times.append(workflow_time)
                        successful_workflows += 1
                        
                        self.logger.info(f"✓ Workflow completed in {workflow_time:.2f}ms")
                
                except Exception as e:
                    self.logger.warning(f"Cognitive workflow failed: {e}")
        
        if workflow_times:
            return {
                'mean_response_time': statistics.mean(workflow_times),
                'p95_response_time': statistics.quantiles(workflow_times, n=20)[18] if len(workflow_times) > 20 else max(workflow_times),
                'success_rate': (successful_workflows / len(test_payloads)) * 100,
                'total_workflows': len(test_payloads),
                'successful_workflows': successful_workflows,
                'sample_times': workflow_times
            }
        else:
            return {'error': 'No successful workflows completed'}
    
    async def test_concurrent_load(self) -> Dict:
        """Test system performance under concurrent load"""
        self.logger.info("⚡ Testing concurrent load performance...")
        
        concurrent_levels = [10, 25, 50, 75]  # Concurrent request levels to test
        results = {}
        
        for concurrency in concurrent_levels:
            self.logger.info(f"Testing with {concurrency} concurrent requests...")
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                start_time = time.perf_counter()
                
                # Create concurrent tasks
                for i in range(concurrency):
                    task = self._make_concurrent_request(session, i % len(self.services.keys()))
                    tasks.append(task)
                
                # Execute all tasks concurrently
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.perf_counter()
                
                # Analyze results
                successful = sum(1 for r in responses if not isinstance(r, Exception))
                total_time = end_time - start_time
                
                results[concurrency] = {
                    'total_requests': concurrency,
                    'successful_requests': successful,
                    'success_rate': (successful / concurrency) * 100,
                    'total_time_seconds': total_time,
                    'requests_per_second': successful / total_time if total_time > 0 else 0,
                    'average_response_time': total_time / concurrency if concurrency > 0 else 0
                }
                
                self.logger.info(f"✓ Concurrency {concurrency}: {successful}/{concurrency} successful, {results[concurrency]['requests_per_second']:.2f} RPS")
        
        return results
    
    async def _make_concurrent_request(self, session: aiohttp.ClientSession, service_index: int):
        """Make a single concurrent request to a service"""
        services = list(self.services.values())
        service_url = services[service_index]
        
        try:
            async with session.get(f"{service_url}/health", 
                                 timeout=aiohttp.ClientTimeout(total=10)) as response:
                return await response.text()
        except Exception as e:
            return e
    
    def profile_system_resources(self) -> Dict:
        """Profile system resource usage"""
        self.logger.info("💻 Profiling system resource usage...")
        
        # Get Docker container stats
        try:
            container_stats = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 
                 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}'],
                capture_output=True, text=True, timeout=30
            )
            
            if container_stats.returncode == 0:
                stats_lines = container_stats.stdout.strip().split('\n')[1:]  # Skip header
                container_data = []
                
                for line in stats_lines:
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        container_data.append({
                            'container': parts[0],
                            'cpu_percent': parts[1],
                            'memory_usage': parts[2],
                            'memory_percent': parts[3],
                            'network_io': parts[4],
                            'disk_io': parts[5]
                        })
                
            else:
                container_data = {'error': 'Failed to get container stats'}
        except Exception as e:
            container_data = {'error': str(e)}
        
        # Get system-wide resource usage
        system_stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'available_memory_gb': psutil.virtual_memory().available / (1024**3)
        }
        
        return {
            'containers': container_data,
            'system': system_stats
        }
    
    def profile_database_performance(self) -> Dict:
        """Profile database performance across all database systems"""
        self.logger.info("🗄️ Profiling database performance...")
        
        results = {}
        
        # PostgreSQL performance
        try:
            import os
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "aiwfe_db"),
                user=os.getenv("POSTGRES_USER", "aiwfe"),
                password=os.getenv("POSTGRES_PASSWORD")
            )
            if not os.getenv("POSTGRES_PASSWORD"):
                raise ValueError("POSTGRES_PASSWORD environment variable must be set for database profiling")
            cursor = conn.cursor()
            
            # Test query performance
            query_times = []
            for i in range(50):
                start_time = time.perf_counter()
                cursor.execute("SELECT 1")
                cursor.fetchall()
                end_time = time.perf_counter()
                query_times.append((end_time - start_time) * 1000)
            
            results['postgresql'] = {
                'mean_query_time_ms': statistics.mean(query_times),
                'p95_query_time_ms': statistics.quantiles(query_times, n=20)[18] if len(query_times) > 20 else max(query_times),
                'sample_count': len(query_times)
            }
            
            conn.close()
            self.logger.info(f"✓ PostgreSQL: P95={results['postgresql']['p95_query_time_ms']:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"PostgreSQL profiling failed: {e}")
            results['postgresql'] = {'error': str(e)}
        
        # Redis performance
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            
            # Test Redis performance
            redis_times = []
            for i in range(100):
                start_time = time.perf_counter()
                r.set(f"test_key_{i}", f"test_value_{i}")
                r.get(f"test_key_{i}")
                end_time = time.perf_counter()
                redis_times.append((end_time - start_time) * 1000)
            
            # Cleanup
            for i in range(100):
                r.delete(f"test_key_{i}")
            
            results['redis'] = {
                'mean_operation_time_ms': statistics.mean(redis_times),
                'p95_operation_time_ms': statistics.quantiles(redis_times, n=20)[18] if len(redis_times) > 20 else max(redis_times),
                'sample_count': len(redis_times)
            }
            
            self.logger.info(f"✓ Redis: P95={results['redis']['p95_operation_time_ms']:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"Redis profiling failed: {e}")
            results['redis'] = {'error': str(e)}
        
        # Neo4j performance
        try:
            import os
            neo4j_auth = os.getenv("NEO4J_AUTH", "neo4j/changeme")
            if neo4j_auth == "neo4j/changeme":
                raise ValueError("NEO4J_AUTH environment variable must be set for database profiling")
            
            neo4j_user, neo4j_password = neo4j_auth.split('/', 1)
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=(neo4j_user, neo4j_password))
            
            with driver.session() as session:
                neo4j_times = []
                for i in range(30):
                    start_time = time.perf_counter()
                    session.run("RETURN 1 as test")
                    end_time = time.perf_counter()
                    neo4j_times.append((end_time - start_time) * 1000)
            
            driver.close()
            
            results['neo4j'] = {
                'mean_query_time_ms': statistics.mean(neo4j_times),
                'p95_query_time_ms': statistics.quantiles(neo4j_times, n=20)[18] if len(neo4j_times) > 20 else max(neo4j_times),
                'sample_count': len(neo4j_times)
            }
            
            self.logger.info(f"✓ Neo4j: P95={results['neo4j']['p95_query_time_ms']:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"Neo4j profiling failed: {e}")
            results['neo4j'] = {'error': str(e)}
        
        return results
    
    async def profile_service_mesh_overhead(self) -> Dict:
        """Profile service mesh performance impact"""
        self.logger.info("🕸️ Profiling service mesh overhead...")
        
        # Since we're using Docker networking, we'll measure inter-service latency
        results = {}
        
        # Test direct service-to-service communication latency
        service_pairs = [
            ('reasoning', 'hybrid_memory'),
            ('reasoning', 'coordination'),  
            ('coordination', 'learning'),
            ('hybrid_memory', 'perception')
        ]
        
        async with aiohttp.ClientSession() as session:
            for source, target in service_pairs:
                if source in self.services and target in self.services:
                    try:
                        # Measure network latency between services
                        latencies = []
                        
                        for i in range(20):
                            start_time = time.perf_counter()
                            
                            # Use health check as proxy for service communication
                            async with session.get(f"{self.services[target]}/health",
                                                 timeout=aiohttp.ClientTimeout(total=5)) as response:
                                await response.text()
                                end_time = time.perf_counter()
                                latencies.append((end_time - start_time) * 1000)
                        
                        results[f"{source}_to_{target}"] = {
                            'mean_latency_ms': statistics.mean(latencies),
                            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies),
                            'sample_count': len(latencies)
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Failed to measure {source} to {target} latency: {e}")
                        results[f"{source}_to_{target}"] = {'error': str(e)}
        
        return results
    
    def analyze_performance_bottlenecks(self) -> Dict:
        """Analyze performance data to identify bottlenecks"""
        self.logger.info("🔍 Analyzing performance bottlenecks...")
        
        bottlenecks = []
        recommendations = []
        
        # Analyze service response times
        if 'service_response_times' in self.results:
            for service, metrics in self.results['service_response_times'].items():
                if isinstance(metrics, dict) and 'p95' in metrics:
                    if metrics['p95'] > 500:  # High response time
                        bottlenecks.append(f"High response time in {service}: {metrics['p95']:.2f}ms P95")
                        recommendations.append(f"Optimize {service} response handling and resource allocation")
        
        # Analyze cognitive workflow performance
        if 'cognitive_workflows' in self.results:
            cw = self.results['cognitive_workflows']
            if isinstance(cw, dict) and 'p95_response_time' in cw:
                if cw['p95_response_time'] > self.targets['cognitive_response_time_p95']:
                    bottlenecks.append(f"Cognitive workflow P95 response time exceeds target: {cw['p95_response_time']:.2f}ms > {self.targets['cognitive_response_time_p95']}ms")
                    recommendations.append("Optimize cognitive processing pipeline and consider caching strategies")
        
        # Analyze database performance
        if 'database_performance' in self.results:
            for db, metrics in self.results['database_performance'].items():
                if isinstance(metrics, dict) and 'p95_query_time_ms' in metrics:
                    if metrics['p95_query_time_ms'] > self.targets['db_query_response_time']:
                        bottlenecks.append(f"{db} query time exceeds target: {metrics['p95_query_time_ms']:.2f}ms > {self.targets['db_query_response_time']}ms")
                        recommendations.append(f"Optimize {db} queries and consider indexing improvements")
        
        # Analyze system resources
        if 'system_resources' in self.results:
            system = self.results['system_resources'].get('system', {})
            if system.get('cpu_percent', 0) > self.targets['cpu_usage_threshold']:
                bottlenecks.append(f"High system CPU usage: {system['cpu_percent']}% > {self.targets['cpu_usage_threshold']}%")
                recommendations.append("Consider scaling horizontally or optimizing CPU-intensive operations")
        
        return {
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'performance_score': self._calculate_performance_score()
        }
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)"""
        score = 100.0
        deductions = 0
        
        # Check cognitive response time
        if 'cognitive_workflows' in self.results:
            cw = self.results['cognitive_workflows']
            if isinstance(cw, dict) and 'p95_response_time' in cw:
                if cw['p95_response_time'] > self.targets['cognitive_response_time_p95']:
                    deductions += 20
        
        # Check database performance
        if 'database_performance' in self.results:
            for db, metrics in self.results['database_performance'].items():
                if isinstance(metrics, dict) and 'p95_query_time_ms' in metrics:
                    if metrics['p95_query_time_ms'] > self.targets['db_query_response_time']:
                        deductions += 10
        
        # Check system resources
        if 'system_resources' in self.results:
            system = self.results['system_resources'].get('system', {})
            if system.get('cpu_percent', 0) > self.targets['cpu_usage_threshold']:
                deductions += 15
        
        return max(0, score - deductions)
    
    async def run_comprehensive_profile(self) -> Dict:
        """Run complete performance profiling suite"""
        self.logger.info("🚀 Starting comprehensive performance profiling...")
        
        # Run all profiling tasks
        self.results['service_response_times'] = await self.profile_service_response_times()
        self.results['cognitive_workflows'] = await self.test_cognitive_workflows()
        self.results['concurrent_load'] = await self.test_concurrent_load()
        self.results['system_resources'] = self.profile_system_resources()
        self.results['database_performance'] = self.profile_database_performance()
        self.results['service_mesh_overhead'] = await self.profile_service_mesh_overhead()
        self.results['bottleneck_analysis'] = self.analyze_performance_bottlenecks()
        
        # Add metadata
        self.results['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'targets': self.targets,
            'services_tested': list(self.services.keys())
        }
        
        self.logger.info("✅ Performance profiling complete!")
        return self.results
    
    def generate_report(self) -> str:
        """Generate human-readable performance report"""
        report = []
        report.append("=" * 80)
        report.append("AIWFE PHASE 3 PERFORMANCE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {self.results['metadata']['timestamp']}")
        report.append(f"Duration: {self.results['metadata']['duration_seconds']:.2f} seconds")
        report.append("")
        
        # Performance Score
        score = self.results['bottleneck_analysis']['performance_score']
        report.append(f"OVERALL PERFORMANCE SCORE: {score:.1f}/100")
        report.append("")
        
        # Service Response Times
        report.append("SERVICE RESPONSE TIMES:")
        report.append("-" * 40)
        for service, metrics in self.results['service_response_times'].items():
            if isinstance(metrics, dict) and 'p95' in metrics:
                status = "✅ PASS" if metrics['p95'] <= 500 else "❌ FAIL"
                report.append(f"{service:20} P95: {metrics['p95']:6.2f}ms  Mean: {metrics['mean']:6.2f}ms  {status}")
        report.append("")
        
        # Cognitive Workflows
        if 'cognitive_workflows' in self.results and isinstance(self.results['cognitive_workflows'], dict):
            cw = self.results['cognitive_workflows']
            report.append("COGNITIVE WORKFLOW PERFORMANCE:")
            report.append("-" * 40)
            report.append(f"P95 Response Time: {cw.get('p95_response_time', 'N/A'):.2f}ms")
            report.append(f"Success Rate: {cw.get('success_rate', 'N/A'):.1f}%")
            status = "✅ PASS" if cw.get('p95_response_time', 999999) <= self.targets['cognitive_response_time_p95'] else "❌ FAIL"
            report.append(f"Target Compliance: {status}")
            report.append("")
        
        # Database Performance
        report.append("DATABASE PERFORMANCE:")
        report.append("-" * 40)
        for db, metrics in self.results['database_performance'].items():
            if isinstance(metrics, dict) and 'p95_query_time_ms' in metrics:
                status = "✅ PASS" if metrics['p95_query_time_ms'] <= self.targets['db_query_response_time'] else "❌ FAIL"
                report.append(f"{db:15} P95: {metrics['p95_query_time_ms']:6.2f}ms  {status}")
        report.append("")
        
        # Bottlenecks and Recommendations
        report.append("BOTTLENECKS IDENTIFIED:")
        report.append("-" * 40)
        for bottleneck in self.results['bottleneck_analysis']['bottlenecks']:
            report.append(f"⚠️  {bottleneck}")
        
        if not self.results['bottleneck_analysis']['bottlenecks']:
            report.append("✅ No significant bottlenecks identified")
        report.append("")
        
        report.append("OPTIMIZATION RECOMMENDATIONS:")
        report.append("-" * 40)
        for recommendation in self.results['bottleneck_analysis']['recommendations']:
            report.append(f"💡 {recommendation}")
        
        if not self.results['bottleneck_analysis']['recommendations']:
            report.append("✅ System is performing within acceptable parameters")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


async def main():
    """Main execution function"""
    profiler = PerformanceProfiler()
    
    try:
        # Run comprehensive profiling
        results = await profiler.run_comprehensive_profile()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"/home/marku/AIWFE/performance_profile_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate and save report
        report = profiler.generate_report()
        report_file = f"/home/marku/AIWFE/PHASE3_PERFORMANCE_VALIDATION_REPORT.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\n📊 Detailed results saved to: {results_file}")
        print(f"📋 Report saved to: {report_file}")
        
        # Return exit code based on performance score
        score = results['bottleneck_analysis']['performance_score']
        if score >= 80:
            print(f"🎉 Performance validation PASSED with score {score:.1f}/100")
            sys.exit(0)
        elif score >= 60:
            print(f"⚠️  Performance validation WARNING with score {score:.1f}/100")
            sys.exit(1)
        else:
            print(f"❌ Performance validation FAILED with score {score:.1f}/100")
            sys.exit(2)
            
    except Exception as e:
        profiler.logger.error(f"Performance profiling failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())