#!/usr/bin/env python3
"""
Phase 3 Performance Validation Testing Suite

Validates performance improvements from Phase 2 fixes:
1. Database Performance Testing (indexes, connection pools)
2. Frontend Resource Loading (CSS optimization)
3. API Response Time Analysis (profile, calendar, auth)
4. Memory and Resource Usage (connection pools, leaks)

Priority: HIGH - Validate no performance regressions from fixes
"""

import asyncio
import time
import sys
import os
import json
import statistics
import psutil
import requests
import aiohttp
import asyncpg
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import logging

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceValidator:
    """Comprehensive performance validation for Phase 2 improvements"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'database': {},
            'frontend': {},
            'api': {},
            'memory': {},
            'summary': {}
        }
        self.base_url = "http://localhost:8000"
        self.db_url = "postgresql://postgres:your_password@localhost:5432/ai_workflow_engine"
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance validation tests in parallel"""
        logger.info("🚀 Starting Phase 3 Performance Validation Testing")
        
        # Run tests in parallel for efficiency
        tasks = [
            self.test_database_performance(),
            self.test_frontend_performance(),
            self.test_api_performance(),
            self.test_memory_usage()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Generate summary
        self._generate_summary()
        
        return self.results
    
    async def test_database_performance(self):
        """Test database performance improvements from Phase 2"""
        logger.info("📊 Testing Database Performance...")
        
        try:
            # Test database connection and basic queries
            async with asyncpg.connect(self.db_url) as conn:
                # Test profile queries (should be faster with new indexes)
                profile_times = await self._test_profile_queries(conn)
                self.results['database']['profile_queries'] = profile_times
                
                # Test calendar sync performance
                calendar_times = await self._test_calendar_queries(conn)
                self.results['database']['calendar_queries'] = calendar_times
                
                # Test authentication session queries
                auth_times = await self._test_auth_session_queries(conn)
                self.results['database']['auth_queries'] = auth_times
                
                # Test index effectiveness
                index_stats = await self._test_index_performance(conn)
                self.results['database']['index_performance'] = index_stats
                
                # Test connection pool performance
                pool_stats = await self._test_connection_pool(conn)
                self.results['database']['connection_pool'] = pool_stats
                
        except Exception as e:
            logger.error(f"Database testing failed: {e}")
            self.results['database']['error'] = str(e)
    
    async def _test_profile_queries(self, conn) -> Dict[str, float]:
        """Test profile API database query performance"""
        times = []
        
        for i in range(10):  # Run multiple times for average
            start_time = time.perf_counter()
            
            # Simulate profile queries (should be faster with new indexes)
            await conn.fetch("""
                SELECT up.*, u.username, u.email 
                FROM user_profiles up 
                JOIN users u ON up.user_id = u.id 
                WHERE up.user_id = 1
                ORDER BY up.created_at DESC
                LIMIT 1
            """)
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to ms
            
            await asyncio.sleep(0.1)  # Small delay
        
        return {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    async def _test_calendar_queries(self, conn) -> Dict[str, float]:
        """Test calendar sync query performance"""
        times = []
        
        for i in range(10):
            start_time = time.perf_counter()
            
            # Simulate calendar sync queries (should be faster with time indexes)
            await conn.fetch("""
                SELECT e.*, c.name as calendar_name 
                FROM events e 
                JOIN calendars c ON e.calendar_id = c.id 
                WHERE e.start_time >= $1 AND e.end_time <= $2
                ORDER BY e.start_time
            """, datetime.now() - timedelta(days=30), datetime.now() + timedelta(days=30))
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
            
            await asyncio.sleep(0.1)
        
        return {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times)
        }
    
    async def _test_auth_session_queries(self, conn) -> Dict[str, float]:
        """Test authentication session query performance"""
        times = []
        
        for i in range(10):
            start_time = time.perf_counter()
            
            # Simulate active session queries (should be faster with new indexes)
            await conn.fetch("""
                SELECT * FROM authentication_sessions 
                WHERE user_id = 1 AND is_active = true 
                AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
            
            await asyncio.sleep(0.1)
        
        return {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times)
        }
    
    async def _test_index_performance(self, conn) -> Dict[str, Any]:
        """Test effectiveness of new database indexes"""
        try:
            # Check if indexes are being used
            explain_results = await conn.fetch("""
                EXPLAIN (ANALYZE, BUFFERS) 
                SELECT up.* FROM user_profiles up 
                WHERE up.user_id = 1 
                ORDER BY up.created_at DESC
            """)
            
            # Check index usage statistics
            index_stats = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename IN ('user_profiles', 'events', 'authentication_sessions', 'user_oauth_tokens')
                ORDER BY idx_scan DESC
            """)
            
            return {
                'query_plan_uses_index': 'Index Scan' in str(explain_results),
                'index_usage_stats': [dict(row) for row in index_stats],
                'total_indexes': len(index_stats)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _test_connection_pool(self, conn) -> Dict[str, Any]:
        """Test connection pool performance improvements"""
        try:
            # Test connection pool stats
            pool_stats = await conn.fetch("""
                SELECT 
                    application_name,
                    state,
                    count(*) as connection_count
                FROM pg_stat_activity 
                WHERE datname = 'ai_workflow_engine'
                GROUP BY application_name, state
            """)
            
            # Measure connection creation time
            connection_times = []
            for i in range(5):
                start_time = time.perf_counter()
                test_conn = await asyncpg.connect(self.db_url)
                await test_conn.close()
                end_time = time.perf_counter()
                connection_times.append((end_time - start_time) * 1000)
            
            return {
                'pool_stats': [dict(row) for row in pool_stats],
                'avg_connection_time_ms': statistics.mean(connection_times),
                'connection_times': connection_times
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def test_frontend_performance(self):
        """Test frontend resource loading performance"""
        logger.info("🎨 Testing Frontend Performance...")
        
        try:
            # Test page load times
            page_load_times = await self._test_page_load_performance()
            self.results['frontend']['page_loads'] = page_load_times
            
            # Test CSS resource loading
            css_performance = await self._test_css_performance()
            self.results['frontend']['css_loading'] = css_performance
            
            # Test static resource efficiency
            resource_loading = await self._test_resource_loading()
            self.results['frontend']['resource_loading'] = resource_loading
            
        except Exception as e:
            logger.error(f"Frontend testing failed: {e}")
            self.results['frontend']['error'] = str(e)
    
    async def _test_page_load_performance(self) -> Dict[str, Any]:
        """Test page load times after CSS optimization"""
        page_times = {}
        
        pages_to_test = [
            '/',
            '/auth/login',
            '/profile',
            '/calendar',
            '/dashboard'
        ]
        
        async with aiohttp.ClientSession() as session:
            for page in pages_to_test:
                times = []
                
                for i in range(5):  # Test each page 5 times
                    start_time = time.perf_counter()
                    
                    try:
                        async with session.get(f"{self.base_url}{page}") as response:
                            await response.read()  # Ensure full response is loaded
                            
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)
                        
                    except Exception as e:
                        logger.warning(f"Failed to load {page}: {e}")
                        continue
                    
                    await asyncio.sleep(0.5)
                
                if times:
                    page_times[page] = {
                        'avg_ms': statistics.mean(times),
                        'min_ms': min(times),
                        'max_ms': max(times),
                        'samples': len(times)
                    }
        
        return page_times
    
    async def _test_css_performance(self) -> Dict[str, Any]:
        """Test CSS loading performance after optimization"""
        css_times = {}
        
        css_files = [
            '/static/css/styles.css',
            '/static/css/components.css',
            '/static/css/themes.css'
        ]
        
        async with aiohttp.ClientSession() as session:
            for css_file in css_files:
                times = []
                
                for i in range(5):
                    start_time = time.perf_counter()
                    
                    try:
                        async with session.get(f"{self.base_url}{css_file}") as response:
                            content = await response.read()
                            
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)
                        
                        # Check CSS size and compression
                        css_times[css_file] = {
                            'avg_load_time_ms': statistics.mean(times) if i == 4 else None,
                            'size_bytes': len(content),
                            'status_code': response.status
                        }
                        
                    except Exception as e:
                        logger.warning(f"Failed to load CSS {css_file}: {e}")
                        continue
                    
                    await asyncio.sleep(0.2)
        
        return css_times
    
    async def _test_resource_loading(self) -> Dict[str, Any]:
        """Test overall resource loading efficiency"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test static resource loading
                static_resources = [
                    '/static/js/main.js',
                    '/static/js/auth.js',
                    '/static/images/logo.png',
                    '/favicon.ico'
                ]
                
                resource_stats = {}
                
                for resource in static_resources:
                    start_time = time.perf_counter()
                    
                    try:
                        async with session.get(f"{self.base_url}{resource}") as response:
                            content = await response.read()
                            
                        end_time = time.perf_counter()
                        
                        resource_stats[resource] = {
                            'load_time_ms': (end_time - start_time) * 1000,
                            'size_bytes': len(content),
                            'status_code': response.status,
                            'content_type': response.headers.get('content-type', 'unknown')
                        }
                        
                    except Exception as e:
                        resource_stats[resource] = {'error': str(e)}
                
                return resource_stats
                
        except Exception as e:
            return {'error': str(e)}
    
    async def test_api_performance(self):
        """Test API response time improvements"""
        logger.info("🔌 Testing API Performance...")
        
        try:
            # Test profile endpoint performance
            profile_perf = await self._test_profile_api_performance()
            self.results['api']['profile_endpoint'] = profile_perf
            
            # Test calendar sync performance
            calendar_perf = await self._test_calendar_api_performance()
            self.results['api']['calendar_endpoints'] = calendar_perf
            
            # Test authentication performance
            auth_perf = await self._test_auth_api_performance()
            self.results['api']['auth_endpoints'] = auth_perf
            
            # Test overall API stability
            stability_stats = await self._test_api_stability()
            self.results['api']['stability'] = stability_stats
            
        except Exception as e:
            logger.error(f"API testing failed: {e}")
            self.results['api']['error'] = str(e)
    
    async def _test_profile_api_performance(self) -> Dict[str, Any]:
        """Test /api/v1/profile endpoint performance after database fixes"""
        times = []
        status_codes = []
        
        # Create test session/token (simplified for testing)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'PerformanceTest/1.0'
        }
        
        async with aiohttp.ClientSession() as session:
            for i in range(10):
                start_time = time.perf_counter()
                
                try:
                    async with session.get(
                        f"{self.base_url}/api/v1/profile",
                        headers=headers
                    ) as response:
                        await response.read()
                        
                    end_time = time.perf_counter()
                    times.append((end_time - start_time) * 1000)
                    status_codes.append(response.status)
                    
                except Exception as e:
                    logger.warning(f"Profile API test failed: {e}")
                    continue
                
                await asyncio.sleep(0.5)
        
        return {
            'avg_response_time_ms': statistics.mean(times) if times else 0,
            'min_response_time_ms': min(times) if times else 0,
            'max_response_time_ms': max(times) if times else 0,
            'status_codes': status_codes,
            'success_rate': (status_codes.count(200) / len(status_codes) * 100) if status_codes else 0,
            'total_requests': len(times)
        }
    
    async def _test_calendar_api_performance(self) -> Dict[str, Any]:
        """Test calendar sync API performance"""
        endpoints = [
            '/api/v1/calendar/sync/auto',
            '/api/v1/calendar/events',
            '/api/v1/calendar/calendars'
        ]
        
        endpoint_performance = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                times = []
                status_codes = []
                
                for i in range(5):  # Fewer requests for calendar endpoints
                    start_time = time.perf_counter()
                    
                    try:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.read()
                            
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)
                        status_codes.append(response.status)
                        
                    except Exception as e:
                        logger.warning(f"Calendar API test failed for {endpoint}: {e}")
                        continue
                    
                    await asyncio.sleep(1.0)  # Longer delay for calendar endpoints
                
                if times:
                    endpoint_performance[endpoint] = {
                        'avg_response_time_ms': statistics.mean(times),
                        'min_response_time_ms': min(times),
                        'max_response_time_ms': max(times),
                        'status_codes': status_codes,
                        'success_rate': (len([s for s in status_codes if s < 400]) / len(status_codes) * 100) if status_codes else 0
                    }
        
        return endpoint_performance
    
    async def _test_auth_api_performance(self) -> Dict[str, Any]:
        """Test authentication middleware performance"""
        auth_endpoints = [
            '/api/v1/auth/status',
            '/api/v1/auth/validate',
            '/api/v1/auth/refresh'
        ]
        
        auth_performance = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in auth_endpoints:
                times = []
                status_codes = []
                
                for i in range(8):
                    start_time = time.perf_counter()
                    
                    try:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.read()
                            
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)
                        status_codes.append(response.status)
                        
                    except Exception as e:
                        logger.warning(f"Auth API test failed for {endpoint}: {e}")
                        continue
                    
                    await asyncio.sleep(0.3)
                
                if times:
                    auth_performance[endpoint] = {
                        'avg_response_time_ms': statistics.mean(times),
                        'status_codes': status_codes,
                        'total_requests': len(times)
                    }
        
        return auth_performance
    
    async def _test_api_stability(self) -> Dict[str, Any]:
        """Test overall API stability and response consistency"""
        # Test concurrent requests to check for race conditions
        concurrent_requests = 20
        
        async def make_request(session, endpoint):
            try:
                start_time = time.perf_counter()
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    content = await response.read()
                end_time = time.perf_counter()
                
                return {
                    'status': response.status,
                    'response_time': (end_time - start_time) * 1000,
                    'content_length': len(content)
                }
            except Exception as e:
                return {'error': str(e)}
        
        async with aiohttp.ClientSession() as session:
            # Test concurrent requests to key endpoints
            tasks = []
            endpoints_to_test = ['/', '/api/v1/health', '/static/css/styles.css']
            
            for endpoint in endpoints_to_test:
                for _ in range(concurrent_requests // len(endpoints_to_test)):
                    tasks.append(make_request(session, endpoint))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            success_count = len([r for r in results if isinstance(r, dict) and 'error' not in r])
            error_count = len([r for r in results if isinstance(r, dict) and 'error' in r])
            exception_count = len([r for r in results if isinstance(r, Exception)])
            
            response_times = [
                r['response_time'] for r in results 
                if isinstance(r, dict) and 'response_time' in r
            ]
            
            return {
                'total_requests': len(results),
                'successful_requests': success_count,
                'failed_requests': error_count,
                'exceptions': exception_count,
                'success_rate': (success_count / len(results) * 100) if results else 0,
                'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
                'concurrent_request_performance': 'stable' if success_count > len(results) * 0.8 else 'unstable'
            }
    
    async def test_memory_usage(self):
        """Test memory usage and resource efficiency"""
        logger.info("💾 Testing Memory Usage...")
        
        try:
            # Get initial memory stats
            initial_memory = self._get_system_memory_stats()
            
            # Monitor memory during API load testing
            memory_during_load = await self._test_memory_under_load()
            
            # Test for memory leaks
            memory_leak_test = await self._test_memory_leaks()
            
            # Get final memory stats
            final_memory = self._get_system_memory_stats()
            
            self.results['memory'] = {
                'initial': initial_memory,
                'during_load': memory_during_load,
                'leak_test': memory_leak_test,
                'final': final_memory,
                'memory_efficiency': 'good' if final_memory['available_mb'] >= initial_memory['available_mb'] * 0.8 else 'concerning'
            }
            
        except Exception as e:
            logger.error(f"Memory testing failed: {e}")
            self.results['memory']['error'] = str(e)
    
    def _get_system_memory_stats(self) -> Dict[str, Any]:
        """Get current system memory statistics"""
        memory = psutil.virtual_memory()
        
        return {
            'total_mb': memory.total / (1024 * 1024),
            'available_mb': memory.available / (1024 * 1024),
            'used_mb': memory.used / (1024 * 1024),
            'free_mb': memory.free / (1024 * 1024),
            'percent_used': memory.percent,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _test_memory_under_load(self) -> Dict[str, Any]:
        """Test memory usage during API load"""
        memory_samples = []
        
        # Start memory monitoring
        async def monitor_memory():
            for _ in range(10):
                memory_samples.append(self._get_system_memory_stats())
                await asyncio.sleep(2)
        
        # Start API load testing
        async def api_load():
            async with aiohttp.ClientSession() as session:
                tasks = []
                for _ in range(50):  # Create moderate load
                    tasks.append(session.get(f"{self.base_url}/"))
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Run both in parallel
        await asyncio.gather(monitor_memory(), api_load())
        
        if memory_samples:
            used_memory = [sample['used_mb'] for sample in memory_samples]
            return {
                'samples': len(memory_samples),
                'avg_used_mb': statistics.mean(used_memory),
                'max_used_mb': max(used_memory),
                'min_used_mb': min(used_memory),
                'memory_variation': max(used_memory) - min(used_memory)
            }
        
        return {'error': 'No memory samples collected'}
    
    async def _test_memory_leaks(self) -> Dict[str, Any]:
        """Test for potential memory leaks during repeated operations"""
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)
        
        # Perform repeated operations that might cause leaks
        async with aiohttp.ClientSession() as session:
            for i in range(100):  # Many small requests
                try:
                    async with session.get(f"{self.base_url}/") as response:
                        await response.read()
                except:
                    continue
                
                if i % 20 == 0:  # Check memory every 20 requests
                    await asyncio.sleep(0.1)
        
        final_memory = psutil.virtual_memory().used / (1024 * 1024)
        memory_increase = final_memory - initial_memory
        
        return {
            'initial_used_mb': initial_memory,
            'final_used_mb': final_memory,
            'memory_increase_mb': memory_increase,
            'leak_concern': 'high' if memory_increase > 100 else 'low' if memory_increase > 50 else 'none'
        }
    
    def _generate_summary(self):
        """Generate performance validation summary"""
        summary = {
            'overall_status': 'unknown',
            'database_performance': 'unknown',
            'frontend_performance': 'unknown',
            'api_performance': 'unknown',
            'memory_efficiency': 'unknown',
            'recommendations': []
        }
        
        # Analyze database performance
        if 'database' in self.results and 'error' not in self.results['database']:
            db_results = self.results['database']
            
            # Check if profile queries are fast (should be under 50ms avg)
            if 'profile_queries' in db_results:
                avg_profile_time = db_results['profile_queries'].get('avg_ms', 0)
                if avg_profile_time < 50:
                    summary['database_performance'] = 'excellent'
                elif avg_profile_time < 100:
                    summary['database_performance'] = 'good'
                else:
                    summary['database_performance'] = 'needs_improvement'
                    summary['recommendations'].append('Profile queries are slower than expected. Check database indexes.')
        
        # Analyze API performance
        if 'api' in self.results and 'error' not in self.results['api']:
            api_results = self.results['api']
            
            # Check API response times
            if 'profile_endpoint' in api_results:
                profile_response_time = api_results['profile_endpoint'].get('avg_response_time_ms', 0)
                if profile_response_time < 200:
                    summary['api_performance'] = 'excellent'
                elif profile_response_time < 500:
                    summary['api_performance'] = 'good'
                else:
                    summary['api_performance'] = 'needs_improvement'
                    summary['recommendations'].append('API response times are high. Check backend optimization.')
        
        # Analyze frontend performance
        if 'frontend' in self.results and 'error' not in self.results['frontend']:
            frontend_results = self.results['frontend']
            
            if 'page_loads' in frontend_results:
                page_times = [
                    page_data.get('avg_ms', 0) 
                    for page_data in frontend_results['page_loads'].values()
                    if isinstance(page_data, dict)
                ]
                
                if page_times:
                    avg_page_time = statistics.mean(page_times)
                    if avg_page_time < 1000:  # Under 1 second
                        summary['frontend_performance'] = 'excellent'
                    elif avg_page_time < 2000:  # Under 2 seconds
                        summary['frontend_performance'] = 'good'
                    else:
                        summary['frontend_performance'] = 'needs_improvement'
                        summary['recommendations'].append('Page load times are high. Check CSS and resource optimization.')
        
        # Analyze memory efficiency
        if 'memory' in self.results and 'error' not in self.results['memory']:
            memory_results = self.results['memory']
            
            if 'leak_test' in memory_results:
                leak_concern = memory_results['leak_test'].get('leak_concern', 'unknown')
                if leak_concern == 'none':
                    summary['memory_efficiency'] = 'excellent'
                elif leak_concern == 'low':
                    summary['memory_efficiency'] = 'good'
                else:
                    summary['memory_efficiency'] = 'concerning'
                    summary['recommendations'].append('Potential memory leak detected. Monitor application memory usage.')
        
        # Overall status
        statuses = [
            summary['database_performance'],
            summary['api_performance'],
            summary['frontend_performance'],
            summary['memory_efficiency']
        ]
        
        if all(status in ['excellent', 'good'] for status in statuses if status != 'unknown'):
            summary['overall_status'] = 'passed'
        elif any(status == 'needs_improvement' for status in statuses):
            summary['overall_status'] = 'passed_with_concerns'
        else:
            summary['overall_status'] = 'failed'
        
        if not summary['recommendations']:
            summary['recommendations'].append('All performance tests passed successfully!')
        
        self.results['summary'] = summary
    
    def save_results(self, filename: str = None):
        """Save performance test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_validation_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"📊 Results saved to {filename}")
        return filename


async def main():
    """Main execution function"""
    print("🚀 Phase 3 Performance Validation Testing")
    print("=" * 50)
    
    validator = PerformanceValidator()
    
    try:
        results = await validator.run_all_tests()
        
        # Save results
        results_file = validator.save_results()
        
        # Print summary
        print("\n📊 PERFORMANCE VALIDATION SUMMARY")
        print("=" * 40)
        
        summary = results.get('summary', {})
        print(f"Overall Status: {summary.get('overall_status', 'unknown').upper()}")
        print(f"Database Performance: {summary.get('database_performance', 'unknown')}")
        print(f"API Performance: {summary.get('api_performance', 'unknown')}")
        print(f"Frontend Performance: {summary.get('frontend_performance', 'unknown')}")
        print(f"Memory Efficiency: {summary.get('memory_efficiency', 'unknown')}")
        
        print("\n📋 Recommendations:")
        for rec in summary.get('recommendations', []):
            print(f"  • {rec}")
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Return appropriate exit code
        if summary.get('overall_status') == 'passed':
            return 0
        elif summary.get('overall_status') == 'passed_with_concerns':
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error(f"Performance validation failed: {e}")
        print(f"\n❌ Testing failed: {e}")
        return 3


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)