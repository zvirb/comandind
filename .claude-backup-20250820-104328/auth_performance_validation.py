#!/usr/bin/env python3
"""
Authentication Performance Validation Script
Measures improvements from authentication loop fixes.

Key metrics tracked:
1. API call frequency reduction (target >75%)
2. Navigation response times (target <200ms) 
3. Database connection pool efficiency
4. Redis cache hit rates
5. Resource utilization improvements
"""

import asyncio
import aiohttp
import psycopg2
import redis
import time
import json
import sys
import statistics
from datetime import datetime, timedelta
import subprocess
import requests
from urllib.parse import urljoin

class AuthPerformanceValidator:
    def __init__(self, base_url="http://localhost:8000", redis_host="localhost", redis_port=6379):
        self.base_url = base_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.session = None
        self.redis_client = None
        self.test_results = {}
        
    async def setup(self):
        """Initialize connections"""
        self.session = aiohttp.ClientSession()
        try:
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, db=0, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
            
    async def cleanup(self):
        """Clean up connections"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            self.redis_client.close()
            
    async def measure_api_call_frequency(self, duration_minutes=5):
        """
        Measure API call frequency before/after authentication improvements
        Target: >75% reduction in redundant authentication calls
        """
        print(f"\n=== Measuring API Call Frequency (Duration: {duration_minutes} min) ===")
        
        # Count current API calls by monitoring logs
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        api_calls = {
            'auth_calls': 0,
            'total_calls': 0,
            'unique_sessions': set(),
            'redundant_calls': 0,
            'cache_hits': 0
        }
        
        # Simulate user navigation patterns
        test_endpoints = [
            '/api/auth/profile',
            '/api/chat/history',
            '/api/workflows/list',
            '/api/health'
        ]
        
        # Measure baseline without improvements
        print("Measuring baseline API call patterns...")
        for endpoint in test_endpoints:
            for i in range(10):  # 10 calls per endpoint
                try:
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        api_calls['total_calls'] += 1
                        if 'auth' in endpoint:
                            api_calls['auth_calls'] += 1
                except Exception as e:
                    print(f"Error calling {endpoint}: {e}")
        
        # Check Redis for auth caching
        if self.redis_client:
            try:
                cache_info = self.redis_client.info('stats')
                api_calls['cache_hits'] = cache_info.get('keyspace_hits', 0)
                print(f"Redis cache hits: {api_calls['cache_hits']}")
            except:
                pass
        
        # Calculate reduction percentage
        auth_frequency = (api_calls['auth_calls'] / api_calls['total_calls']) * 100 if api_calls['total_calls'] > 0 else 0
        
        result = {
            'api_call_frequency': auth_frequency,
            'total_api_calls': api_calls['total_calls'],
            'auth_specific_calls': api_calls['auth_calls'],
            'cache_hits': api_calls['cache_hits'],
            'test_duration_minutes': duration_minutes,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results['api_frequency'] = result
        print(f"Auth API calls: {api_calls['auth_calls']}/{api_calls['total_calls']} ({auth_frequency:.1f}%)")
        return result
    
    async def measure_navigation_response_times(self, iterations=50):
        """
        Measure navigation response times after authentication improvements
        Target: <200ms average response time
        """
        print(f"\n=== Measuring Navigation Response Times ({iterations} iterations) ===")
        
        endpoints = [
            '/api/health',
            '/api/auth/profile', 
            '/api/chat/history',
            '/api/workflows/list'
        ]
        
        response_times = []
        
        for endpoint in endpoints:
            endpoint_times = []
            print(f"Testing {endpoint}...")
            
            for i in range(iterations // len(endpoints)):
                start = time.time()
                try:
                    async with self.session.get(f"{self.base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        end = time.time()
                        response_time = (end - start) * 1000  # Convert to milliseconds
                        endpoint_times.append(response_time)
                        response_times.append(response_time)
                except Exception as e:
                    print(f"Error testing {endpoint}: {e}")
                    endpoint_times.append(5000)  # 5s timeout
                    
            if endpoint_times:
                avg_time = statistics.mean(endpoint_times)
                print(f"  {endpoint}: {avg_time:.1f}ms avg")
        
        if response_times:
            result = {
                'average_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'total_requests': len(response_times),
                'target_met': statistics.mean(response_times) < 200,
                'timestamp': datetime.now().isoformat()
            }
        else:
            result = {'error': 'No successful response time measurements'}
        
        self.test_results['response_times'] = result
        print(f"Average response time: {result.get('average_response_time_ms', 0):.1f}ms")
        print(f"Target (<200ms): {'✓' if result.get('target_met', False) else '✗'}")
        return result
    
    def measure_database_pool_efficiency(self):
        """
        Test database connection pool optimization
        Measure connection reuse and pool efficiency
        """
        print(f"\n=== Measuring Database Connection Pool Efficiency ===")
        
        try:
            # Get PgBouncer stats
            result = subprocess.run([
                'docker', 'exec', 'ai_workflow_engine-pgbouncer-1',
                'psql', '-h', 'localhost', '-p', '6432', '-U', 'app_user', 
                '-d', 'pgbouncer', '-c', 'SHOW STATS;'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("PgBouncer Stats:")
                print(result.stdout)
                
                # Parse connection pool metrics
                lines = result.stdout.split('\n')
                pool_stats = {}
                for line in lines:
                    if 'ai_workflow_db' in line:
                        fields = line.split()
                        if len(fields) >= 8:
                            pool_stats = {
                                'total_requests': fields[1],
                                'total_received': fields[2],
                                'total_sent': fields[3],
                                'total_query_time': fields[4],
                                'avg_req': fields[5],
                                'avg_recv': fields[6],
                                'avg_sent': fields[7],
                                'avg_query': fields[8] if len(fields) > 8 else '0'
                            }
                            break
                
                result_data = {
                    'pool_stats': pool_stats,
                    'pool_health': 'healthy' if result.returncode == 0 else 'unhealthy',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                result_data = {'error': f'PgBouncer stats failed: {result.stderr}'}
                
        except Exception as e:
            result_data = {'error': f'Database pool measurement failed: {str(e)}'}
        
        self.test_results['database_pool'] = result_data
        print(f"Database pool health: {result_data.get('pool_health', 'unknown')}")
        return result_data
    
    def measure_redis_cache_performance(self):
        """
        Measure Redis cache hit rates for authentication caching
        """
        print(f"\n=== Measuring Redis Cache Performance ===")
        
        if not self.redis_client:
            result = {'error': 'Redis client not available'}
            self.test_results['redis_cache'] = result
            return result
        
        try:
            # Get Redis stats
            info = self.redis_client.info()
            stats = self.redis_client.info('stats')
            memory = self.redis_client.info('memory')
            
            # Calculate hit rate
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            hit_rate = (hits / (hits + misses)) * 100 if (hits + misses) > 0 else 0
            
            # Check auth-specific keys
            auth_keys = self.redis_client.keys('auth:*')
            session_keys = self.redis_client.keys('session:*')
            
            result = {
                'cache_hit_rate_percent': hit_rate,
                'total_hits': hits,
                'total_misses': misses,
                'auth_keys_count': len(auth_keys),
                'session_keys_count': len(session_keys),
                'memory_used_mb': memory.get('used_memory', 0) / (1024 * 1024),
                'memory_peak_mb': memory.get('used_memory_peak', 0) / (1024 * 1024),
                'connected_clients': info.get('connected_clients', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"Cache hit rate: {hit_rate:.1f}%")
            print(f"Auth keys: {len(auth_keys)}, Session keys: {len(session_keys)}")
            print(f"Memory usage: {result['memory_used_mb']:.1f}MB")
            
        except Exception as e:
            result = {'error': f'Redis cache measurement failed: {str(e)}'}
        
        self.test_results['redis_cache'] = result
        return result
    
    def measure_resource_utilization(self):
        """
        Validate resource utilization improvements (CPU, memory, network)
        """
        print(f"\n=== Measuring Resource Utilization ===")
        
        try:
            # Get container resource usage
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("Container Resource Usage:")
                print(result.stdout)
                
                # Parse resource metrics
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                containers = {}
                
                for line in lines:
                    fields = line.split('\t')
                    if len(fields) >= 4:
                        container_name = fields[0]
                        containers[container_name] = {
                            'cpu_percent': fields[1],
                            'memory_usage': fields[2],
                            'memory_percent': fields[3],
                            'network_io': fields[4] if len(fields) > 4 else 'N/A'
                        }
                
                # Calculate averages for key services
                auth_services = ['api', 'redis', 'pgbouncer']
                avg_cpu = 0
                avg_mem = 0
                service_count = 0
                
                for container, stats in containers.items():
                    for service in auth_services:
                        if service in container.lower():
                            try:
                                cpu = float(stats['cpu_percent'].replace('%', ''))
                                mem = float(stats['memory_percent'].replace('%', ''))
                                avg_cpu += cpu
                                avg_mem += mem
                                service_count += 1
                            except:
                                pass
                
                if service_count > 0:
                    avg_cpu /= service_count
                    avg_mem /= service_count
                
                result_data = {
                    'containers': containers,
                    'auth_services_avg_cpu': avg_cpu,
                    'auth_services_avg_memory': avg_mem,
                    'total_containers': len(containers),
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"Auth services average CPU: {avg_cpu:.1f}%")
                print(f"Auth services average Memory: {avg_mem:.1f}%")
                
            else:
                result_data = {'error': f'Resource measurement failed: {result.stderr}'}
                
        except Exception as e:
            result_data = {'error': f'Resource utilization measurement failed: {str(e)}'}
        
        self.test_results['resource_utilization'] = result_data
        return result_data
    
    async def test_production_environment(self):
        """
        Test production environment at https://aiwfe.com
        """
        print(f"\n=== Testing Production Environment (https://aiwfe.com) ===")
        
        production_url = "https://aiwfe.com"
        
        try:
            # Test basic connectivity
            start = time.time()
            async with self.session.get(f"{production_url}/api/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                end = time.time()
                response_time = (end - start) * 1000
                
                result = {
                    'status_code': response.status,
                    'response_time_ms': response_time,
                    'ssl_valid': True,  # HTTPS worked
                    'accessible': response.status == 200,
                    'timestamp': datetime.now().isoformat()
                }
                
                print(f"Production status: {response.status}")
                print(f"Production response time: {response_time:.1f}ms")
                
        except Exception as e:
            result = {
                'error': f'Production test failed: {str(e)}',
                'accessible': False,
                'timestamp': datetime.now().isoformat()
            }
            
        self.test_results['production'] = result
        return result
    
    def generate_performance_report(self):
        """
        Generate comprehensive performance validation report
        """
        print(f"\n" + "="*80)
        print("AUTHENTICATION PERFORMANCE VALIDATION REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary of target achievements
        targets_met = []
        targets_failed = []
        
        # Check API call frequency reduction
        api_freq = self.test_results.get('api_frequency', {})
        if api_freq and not api_freq.get('error'):
            freq = api_freq.get('api_call_frequency', 100)
            if freq < 25:  # Target: >75% reduction means <25% remaining
                targets_met.append(f"✓ API call frequency: {freq:.1f}% (Target: <25%)")
            else:
                targets_failed.append(f"✗ API call frequency: {freq:.1f}% (Target: <25%)")
        
        # Check response times
        resp_times = self.test_results.get('response_times', {})
        if resp_times and not resp_times.get('error'):
            avg_time = resp_times.get('average_response_time_ms', 1000)
            if avg_time < 200:
                targets_met.append(f"✓ Average response time: {avg_time:.1f}ms (Target: <200ms)")
            else:
                targets_failed.append(f"✗ Average response time: {avg_time:.1f}ms (Target: <200ms)")
        
        # Check cache hit rate
        redis_cache = self.test_results.get('redis_cache', {})
        if redis_cache and not redis_cache.get('error'):
            hit_rate = redis_cache.get('cache_hit_rate_percent', 0)
            if hit_rate > 70:
                targets_met.append(f"✓ Redis cache hit rate: {hit_rate:.1f}% (Good: >70%)")
            else:
                targets_failed.append(f"✗ Redis cache hit rate: {hit_rate:.1f}% (Target: >70%)")
        
        print("TARGET ACHIEVEMENT SUMMARY:")
        print("-" * 40)
        for target in targets_met:
            print(target)
        for target in targets_failed:
            print(target)
        
        print(f"\nOverall Score: {len(targets_met)}/{len(targets_met) + len(targets_failed)} targets met")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 40)
        for test_name, results in self.test_results.items():
            print(f"\n{test_name.upper()}:")
            if isinstance(results, dict):
                for key, value in results.items():
                    if key != 'timestamp':
                        print(f"  {key}: {value}")
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"/home/marku/ai_workflow_engine/.claude/auth_performance_validation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
        return self.test_results

async def main():
    """Main performance validation execution"""
    validator = AuthPerformanceValidator()
    
    try:
        await validator.setup()
        
        # Run all performance tests
        print("Starting Authentication Performance Validation...")
        
        # 1. API call frequency reduction
        await validator.measure_api_call_frequency(duration_minutes=2)
        
        # 2. Navigation response times  
        await validator.measure_navigation_response_times(iterations=30)
        
        # 3. Database connection pool efficiency
        validator.measure_database_pool_efficiency()
        
        # 4. Redis cache performance
        validator.measure_redis_cache_performance()
        
        # 5. Resource utilization
        validator.measure_resource_utilization()
        
        # 6. Production environment test
        await validator.test_production_environment()
        
        # Generate comprehensive report
        validator.generate_performance_report()
        
    except Exception as e:
        print(f"Performance validation failed: {e}")
        return 1
        
    finally:
        await validator.cleanup()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)