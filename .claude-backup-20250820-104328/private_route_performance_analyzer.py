#!/usr/bin/env python3
"""
PrivateRoute Performance Impact Analyzer
Analyzes performance impacts of PrivateRoute infinite loop on system resources
"""

import asyncio
import aiohttp
import time
import json
import psutil
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/marku/ai_workflow_engine/.claude/performance_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    def __init__(self):
        self.base_urls = [
            'http://localhost:8000',
            'https://aiwfe.com'
        ]
        self.session = None
        self.metrics = {
            'api_calls': [],
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'database_connections': [],
            'network_stats': [],
            'errors_429': [],
            'auth_check_frequency': []
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def get_system_metrics(self) -> Dict:
        """Collect current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process-specific metrics for containers
            container_stats = self.get_container_stats()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_available_gb': memory_available,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'container_stats': container_stats
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}

    def get_container_stats(self) -> Dict:
        """Get Docker container resource usage"""
        try:
            # Get stats for main API containers
            containers = ['ai_workflow_engine-api-1', 'ai_workflow_engine-postgres-1', 'ai_workflow_engine-redis-1']
            stats = {}
            
            for container in containers:
                try:
                    # Get container stats
                    result = subprocess.run(
                        ['docker', 'stats', container, '--no-stream', '--format', 
                         'table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:  # Skip header
                            data = lines[1].split('\t')
                            stats[container] = {
                                'cpu_percent': data[0].replace('%', '') if len(data) > 0 else '0',
                                'memory_usage': data[1] if len(data) > 1 else '0B / 0B',
                                'network_io': data[2] if len(data) > 2 else '0B / 0B',
                                'block_io': data[3] if len(data) > 3 else '0B / 0B'
                            }
                except subprocess.TimeoutExpired:
                    stats[container] = {'error': 'timeout'}
                except Exception as e:
                    stats[container] = {'error': str(e)}
                    
            return stats
        except Exception as e:
            logger.error(f"Error collecting container stats: {e}")
            return {}

    async def get_database_connection_stats(self) -> Dict:
        """Get PostgreSQL connection pool statistics"""
        try:
            # Execute query to get connection stats
            result = subprocess.run([
                'docker', 'exec', 'ai_workflow_engine-postgres-1', 
                'psql', '-U', 'app_user', '-d', 'ai_workflow_engine', '-c',
                "SELECT count(*) as total_connections, state, usename FROM pg_stat_activity GROUP BY state, usename;"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'raw_output': result.stdout,
                    'connection_count': result.stdout.count('app_user'),
                    'idle_connections': result.stdout.count('idle'),
                    'active_connections': result.stdout.count('active')
                }
            else:
                return {'error': result.stderr}
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}

    async def analyze_api_call_frequency(self, duration_minutes: int = 5) -> Dict:
        """Analyze API call frequency patterns during authentication loops"""
        logger.info(f"Analyzing API call frequency for {duration_minutes} minutes")
        
        endpoint_stats = {
            '/api/v1/session/validate': {'calls': 0, 'response_times': [], 'errors': 0},
            '/api/v1/health/integration': {'calls': 0, 'response_times': [], 'errors': 0},
            '/api/v1/auth/status': {'calls': 0, 'response_times': [], 'errors': 0}
        }
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Simulate authentication loop behavior
        loop_interval = 2  # seconds between calls
        
        while time.time() < end_time:
            for base_url in self.base_urls:
                for endpoint, stats in endpoint_stats.items():
                    try:
                        request_start = time.time()
                        
                        async with self.session.get(
                            f"{base_url}{endpoint}",
                            headers={'X-Integration-Layer': 'true'}
                        ) as response:
                            request_time = time.time() - request_start
                            
                            stats['calls'] += 1
                            stats['response_times'].append(request_time)
                            
                            if response.status == 429:
                                stats['errors'] += 1
                                self.metrics['errors_429'].append({
                                    'timestamp': datetime.now().isoformat(),
                                    'endpoint': endpoint,
                                    'status': response.status
                                })
                            
                            # Log high frequency calls
                            if stats['calls'] > 0 and (stats['calls'] % 10 == 0):
                                logger.warning(f"High frequency detected: {endpoint} called {stats['calls']} times")
                                
                    except asyncio.TimeoutError:
                        stats['errors'] += 1
                        logger.warning(f"Timeout on {endpoint}")
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Error calling {endpoint}: {e}")
            
            # Collect system metrics during loop
            system_metrics = self.get_system_metrics()
            self.metrics['cpu_usage'].append(system_metrics.get('cpu_percent', 0))
            self.metrics['memory_usage'].append(system_metrics.get('memory_percent', 0))
            
            # Database connection stats
            db_stats = await self.get_database_connection_stats()
            self.metrics['database_connections'].append(db_stats)
            
            await asyncio.sleep(loop_interval)
        
        return endpoint_stats

    def calculate_bandwidth_consumption(self, endpoint_stats: Dict) -> Dict:
        """Calculate estimated bandwidth consumption"""
        # Estimated response sizes (bytes)
        response_sizes = {
            '/api/v1/session/validate': 250,  # JSON response
            '/api/v1/health/integration': 1500,  # Larger health response
            '/api/v1/auth/status': 300  # Basic status response
        }
        
        total_bandwidth = 0
        bandwidth_breakdown = {}
        
        for endpoint, stats in endpoint_stats.items():
            calls = stats['calls']
            estimated_size = response_sizes.get(endpoint, 500)
            endpoint_bandwidth = calls * estimated_size
            
            bandwidth_breakdown[endpoint] = {
                'calls': calls,
                'bytes_per_call': estimated_size,
                'total_bytes': endpoint_bandwidth,
                'mb_consumed': endpoint_bandwidth / (1024 * 1024)
            }
            
            total_bandwidth += endpoint_bandwidth
        
        return {
            'total_bandwidth_bytes': total_bandwidth,
            'total_bandwidth_mb': total_bandwidth / (1024 * 1024),
            'endpoint_breakdown': bandwidth_breakdown
        }

    def analyze_memory_patterns(self) -> Dict:
        """Analyze memory usage patterns during loops"""
        if not self.metrics['memory_usage']:
            return {'error': 'No memory data collected'}
        
        memory_data = self.metrics['memory_usage']
        
        return {
            'min_memory_percent': min(memory_data),
            'max_memory_percent': max(memory_data),
            'avg_memory_percent': statistics.mean(memory_data),
            'memory_spike_count': len([m for m in memory_data if m > 80]),  # High usage spikes
            'memory_pattern': 'increasing' if memory_data[-1] > memory_data[0] else 'stable'
        }

    def analyze_cpu_patterns(self) -> Dict:
        """Analyze CPU usage patterns during loops"""
        if not self.metrics['cpu_usage']:
            return {'error': 'No CPU data collected'}
        
        cpu_data = self.metrics['cpu_usage']
        
        return {
            'min_cpu_percent': min(cpu_data),
            'max_cpu_percent': max(cpu_data),
            'avg_cpu_percent': statistics.mean(cpu_data),
            'cpu_spike_count': len([c for c in cpu_data if c > 70]),  # High CPU spikes
            'cpu_pattern': 'increasing' if cpu_data[-1] > cpu_data[0] else 'stable'
        }

    def generate_optimization_recommendations(self, analysis_results: Dict) -> List[str]:
        """Generate specific optimization recommendations"""
        recommendations = []
        
        # API call frequency recommendations
        endpoint_stats = analysis_results.get('api_call_analysis', {})
        total_calls = sum(stats.get('calls', 0) for stats in endpoint_stats.values())
        
        if total_calls > 100:  # High frequency threshold
            recommendations.append(
                f"CRITICAL: Detected {total_calls} authentication-related API calls in 5 minutes. "
                "Implement request throttling with minimum 5-second intervals between auth checks."
            )
            
        # Bandwidth consumption recommendations  
        bandwidth = analysis_results.get('bandwidth_analysis', {})
        if bandwidth.get('total_bandwidth_mb', 0) > 5:  # 5MB threshold
            recommendations.append(
                f"HIGH: Bandwidth consumption of {bandwidth.get('total_bandwidth_mb', 0):.2f}MB detected. "
                "Implement response caching and reduce session validation payload size."
            )
            
        # Memory pattern recommendations
        memory_analysis = analysis_results.get('memory_analysis', {})
        if memory_analysis.get('memory_spike_count', 0) > 3:
            recommendations.append(
                "MEDIUM: Memory usage spikes detected. Implement garbage collection optimization "
                "and reduce authentication state caching."
            )
            
        # CPU pattern recommendations
        cpu_analysis = analysis_results.get('cpu_analysis', {})
        if cpu_analysis.get('avg_cpu_percent', 0) > 50:
            recommendations.append(
                f"MEDIUM: High CPU usage ({cpu_analysis.get('avg_cpu_percent', 0):.1f}% average) detected. "
                "Optimize authentication logic and implement async processing."
            )
            
        # Database connection recommendations
        db_connections = analysis_results.get('database_analysis', {})
        if db_connections.get('connection_pool_pressure', False):
            recommendations.append(
                "HIGH: Database connection pool pressure detected. "
                "Implement connection pooling optimization and reduce session query frequency."
            )
            
        # 429 error recommendations
        error_429_count = len(self.metrics.get('errors_429', []))
        if error_429_count > 5:
            recommendations.append(
                f"CRITICAL: {error_429_count} rate limiting errors (HTTP 429) detected. "
                "Implement exponential backoff and circuit breaker patterns."
            )
            
        # General architecture recommendations
        recommendations.extend([
            "ARCHITECTURE: Replace continuous authentication polling with event-driven token refresh",
            "ARCHITECTURE: Implement client-side token expiration monitoring to reduce server calls",
            "ARCHITECTURE: Use WebSocket connections for real-time authentication state updates",
            "ARCHITECTURE: Implement service worker for background token refresh management",
            "PERFORMANCE: Add response compression for authentication endpoints",
            "PERFORMANCE: Implement authentication result caching with Redis",
            "MONITORING: Add authentication performance dashboards to Grafana",
            "SECURITY: Implement authentication anomaly detection to prevent abuse"
        ])
        
        return recommendations

    async def run_comprehensive_analysis(self, duration_minutes: int = 5) -> Dict:
        """Run comprehensive performance analysis"""
        logger.info(f"Starting comprehensive performance analysis for {duration_minutes} minutes")
        
        analysis_results = {
            'analysis_start': datetime.now().isoformat(),
            'duration_minutes': duration_minutes,
            'test_configuration': {
                'base_urls': self.base_urls,
                'loop_interval_seconds': 2,
                'timeout_seconds': 10
            }
        }
        
        try:
            # 1. API Call Frequency Analysis
            logger.info("Analyzing API call frequency patterns...")
            endpoint_stats = await self.analyze_api_call_frequency(duration_minutes)
            analysis_results['api_call_analysis'] = endpoint_stats
            
            # 2. Bandwidth Consumption Analysis
            logger.info("Calculating bandwidth consumption...")
            bandwidth_analysis = self.calculate_bandwidth_consumption(endpoint_stats)
            analysis_results['bandwidth_analysis'] = bandwidth_analysis
            
            # 3. Memory Pattern Analysis
            logger.info("Analyzing memory usage patterns...")
            memory_analysis = self.analyze_memory_patterns()
            analysis_results['memory_analysis'] = memory_analysis
            
            # 4. CPU Pattern Analysis
            logger.info("Analyzing CPU usage patterns...")
            cpu_analysis = self.analyze_cpu_patterns()
            analysis_results['cpu_analysis'] = cpu_analysis
            
            # 5. Database Connection Analysis
            logger.info("Analyzing database connection patterns...")
            final_db_stats = await self.get_database_connection_stats()
            analysis_results['database_analysis'] = {
                'final_connection_stats': final_db_stats,
                'connection_samples': len(self.metrics['database_connections']),
                'connection_pool_pressure': final_db_stats.get('active_connections', 0) > 5
            }
            
            # 6. Error Pattern Analysis
            analysis_results['error_analysis'] = {
                'http_429_errors': len(self.metrics['errors_429']),
                'timeout_errors': sum(1 for stats in endpoint_stats.values() for _ in range(stats.get('errors', 0))),
                'error_rate_percent': (len(self.metrics['errors_429']) / max(1, sum(stats.get('calls', 0) for stats in endpoint_stats.values()))) * 100
            }
            
            # 7. Generate Optimization Recommendations
            logger.info("Generating optimization recommendations...")
            analysis_results['optimization_recommendations'] = self.generate_optimization_recommendations(analysis_results)
            
            # 8. Performance Impact Summary
            analysis_results['performance_impact_summary'] = {
                'severity': self.calculate_severity_score(analysis_results),
                'primary_bottlenecks': self.identify_primary_bottlenecks(analysis_results),
                'estimated_resource_waste': self.calculate_resource_waste(analysis_results)
            }
            
            analysis_results['analysis_end'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            analysis_results['error'] = str(e)
            
        return analysis_results

    def calculate_severity_score(self, results: Dict) -> str:
        """Calculate overall performance impact severity"""
        score = 0
        
        # API call frequency (0-40 points)
        total_calls = sum(stats.get('calls', 0) for stats in results.get('api_call_analysis', {}).values())
        if total_calls > 200:
            score += 40
        elif total_calls > 100:
            score += 30
        elif total_calls > 50:
            score += 20
        elif total_calls > 25:
            score += 10
            
        # Bandwidth consumption (0-20 points)
        bandwidth_mb = results.get('bandwidth_analysis', {}).get('total_bandwidth_mb', 0)
        if bandwidth_mb > 10:
            score += 20
        elif bandwidth_mb > 5:
            score += 15
        elif bandwidth_mb > 2:
            score += 10
        elif bandwidth_mb > 1:
            score += 5
            
        # CPU usage (0-20 points)
        avg_cpu = results.get('cpu_analysis', {}).get('avg_cpu_percent', 0)
        if avg_cpu > 80:
            score += 20
        elif avg_cpu > 60:
            score += 15
        elif avg_cpu > 40:
            score += 10
        elif avg_cpu > 20:
            score += 5
            
        # Memory usage (0-20 points)
        avg_memory = results.get('memory_analysis', {}).get('avg_memory_percent', 0)
        if avg_memory > 90:
            score += 20
        elif avg_memory > 80:
            score += 15
        elif avg_memory > 70:
            score += 10
        elif avg_memory > 60:
            score += 5
            
        # Determine severity
        if score >= 70:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        elif score >= 10:
            return "LOW"
        else:
            return "MINIMAL"

    def identify_primary_bottlenecks(self, results: Dict) -> List[str]:
        """Identify the primary performance bottlenecks"""
        bottlenecks = []
        
        # Check API call frequency
        total_calls = sum(stats.get('calls', 0) for stats in results.get('api_call_analysis', {}).values())
        if total_calls > 100:
            bottlenecks.append("Excessive authentication API call frequency")
            
        # Check bandwidth consumption
        bandwidth_mb = results.get('bandwidth_analysis', {}).get('total_bandwidth_mb', 0)
        if bandwidth_mb > 5:
            bottlenecks.append("High bandwidth consumption from repeated authentication checks")
            
        # Check error rates
        error_rate = results.get('error_analysis', {}).get('error_rate_percent', 0)
        if error_rate > 10:
            bottlenecks.append("High authentication error rate causing retry loops")
            
        # Check system resource usage
        avg_cpu = results.get('cpu_analysis', {}).get('avg_cpu_percent', 0)
        if avg_cpu > 50:
            bottlenecks.append("High CPU utilization from continuous authentication processing")
            
        return bottlenecks

    def calculate_resource_waste(self, results: Dict) -> Dict:
        """Calculate estimated resource waste"""
        # Base estimates for resource costs
        api_call_cost_ms = 50  # 50ms average processing time per call
        bandwidth_cost_per_mb = 0.01  # Arbitrary cost unit
        
        total_calls = sum(stats.get('calls', 0) for stats in results.get('api_call_analysis', {}).values())
        bandwidth_mb = results.get('bandwidth_analysis', {}).get('total_bandwidth_mb', 0)
        
        return {
            'wasted_processing_time_seconds': (total_calls * api_call_cost_ms) / 1000,
            'wasted_bandwidth_cost_units': bandwidth_mb * bandwidth_cost_per_mb,
            'unnecessary_database_queries': total_calls,  # Assuming 1 query per auth check
            'estimated_performance_improvement_percent': min(80, total_calls * 0.5)  # Estimated improvement if optimized
        }


async def main():
    """Main function to run the performance analysis"""
    logger.info("Starting PrivateRoute Performance Impact Analysis")
    
    async with PerformanceAnalyzer() as analyzer:
        # Run 5-minute analysis
        results = await analyzer.run_comprehensive_analysis(duration_minutes=5)
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/home/marku/ai_workflow_engine/.claude/private_route_performance_analysis_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Analysis complete. Results saved to {output_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("PRIVATEROUTE PERFORMANCE IMPACT ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis Duration: {results.get('duration_minutes', 0)} minutes")
        print(f"Severity Score: {results.get('performance_impact_summary', {}).get('severity', 'UNKNOWN')}")
        print(f"Total API Calls: {sum(stats.get('calls', 0) for stats in results.get('api_call_analysis', {}).values())}")
        print(f"Total Bandwidth: {results.get('bandwidth_analysis', {}).get('total_bandwidth_mb', 0):.2f} MB")
        print(f"Avg CPU Usage: {results.get('cpu_analysis', {}).get('avg_cpu_percent', 0):.1f}%")
        print(f"Avg Memory Usage: {results.get('memory_analysis', {}).get('avg_memory_percent', 0):.1f}%")
        print(f"HTTP 429 Errors: {results.get('error_analysis', {}).get('http_429_errors', 0)}")
        
        print("\nPRIMARY BOTTLENECKS:")
        for bottleneck in results.get('performance_impact_summary', {}).get('primary_bottlenecks', []):
            print(f"• {bottleneck}")
            
        print("\nTOP OPTIMIZATION RECOMMENDATIONS:")
        for i, rec in enumerate(results.get('optimization_recommendations', [])[:5], 1):
            print(f"{i}. {rec}")
        
        print("="*80)
        
        return results

if __name__ == "__main__":
    asyncio.run(main())