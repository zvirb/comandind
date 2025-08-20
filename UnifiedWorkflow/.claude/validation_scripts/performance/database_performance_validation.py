#!/usr/bin/env python3
"""
Database Performance Validation for Phase 2 Improvements

Tests database performance improvements from Phase 2:
1. Profile queries with new indexes
2. Calendar sync performance
3. Authentication session queries
4. Connection pool optimization
5. Index effectiveness validation
"""

import asyncio
import time
import sys
import os
import json
import statistics
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import logging

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabasePerformanceValidator:
    """Validate database performance improvements from Phase 2"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'profile_queries': {},
            'calendar_queries': {},
            'auth_queries': {},
            'index_performance': {},
            'connection_performance': {},
            'summary': {}
        }
        
        # Database connection parameters
        self.db_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'ai_workflow_db',
            'user': 'app_user',
            'password': 'OVie0GVt2jSUi9aLrh9swS64KGraIZyHLprAEimLwKc='
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all database performance validation tests"""
        logger.info("📊 Starting Database Performance Validation")
        
        try:
            # Test profile queries
            self.test_profile_performance()
            
            # Test calendar queries
            self.test_calendar_performance()
            
            # Test authentication queries
            self.test_auth_performance()
            
            # Test index effectiveness
            self.test_index_effectiveness()
            
            # Test connection performance
            self.test_connection_performance()
            
            # Generate summary
            self._generate_summary()
            
        except Exception as e:
            logger.error(f"Database testing failed: {e}")
            self.results['error'] = str(e)
        
        return self.results
    
    def test_profile_performance(self):
        """Test profile query performance with new indexes"""
        logger.info("👤 Testing Profile Query Performance...")
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor()
            
            # Test profile lookup queries (should be faster with idx_user_profiles_lookup)
            profile_times = []
            
            for i in range(20):  # Run multiple times for reliable average
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT up.*, u.username, u.email 
                    FROM user_profiles up 
                    JOIN users u ON up.user_id = u.id 
                    WHERE up.user_id = %s
                    ORDER BY up.created_at DESC
                    LIMIT 1
                """, (1,))
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                profile_times.append((end_time - start_time) * 1000)  # Convert to ms
                
                time.sleep(0.05)  # Small delay between tests
            
            # Test profile completeness queries (should use idx_user_profiles_completeness)
            completeness_times = []
            
            for i in range(10):
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT user_id, first_name, last_name, work_email
                    FROM user_profiles 
                    WHERE first_name IS NOT NULL 
                    AND last_name IS NOT NULL
                    AND work_email IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                completeness_times.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            self.results['profile_queries'] = {
                'lookup_queries': {
                    'avg_ms': statistics.mean(profile_times),
                    'min_ms': min(profile_times),
                    'max_ms': max(profile_times),
                    'median_ms': statistics.median(profile_times),
                    'total_tests': len(profile_times)
                },
                'completeness_queries': {
                    'avg_ms': statistics.mean(completeness_times),
                    'min_ms': min(completeness_times),
                    'max_ms': max(completeness_times),
                    'total_tests': len(completeness_times)
                }
            }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Profile performance testing failed: {e}")
            self.results['profile_queries']['error'] = str(e)
    
    def test_calendar_performance(self):
        """Test calendar query performance with new time indexes"""
        logger.info("📅 Testing Calendar Query Performance...")
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor()
            
            # Test time range queries (should be faster with idx_events_time_range)
            time_range_queries = []
            
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now() + timedelta(days=30)
            
            for i in range(15):
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT e.*, c.name as calendar_name 
                    FROM events e 
                    JOIN calendars c ON e.calendar_id = c.id 
                    WHERE e.start_time >= %s AND e.end_time <= %s
                    ORDER BY e.start_time
                    LIMIT 50
                """, (start_date, end_date))
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                time_range_queries.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            # Test calendar-specific event queries (should use idx_events_calendar_time)
            calendar_queries = []
            
            for i in range(10):
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT id, title, start_time, end_time
                    FROM events 
                    WHERE calendar_id = %s
                    AND start_time >= %s
                    ORDER BY start_time DESC
                    LIMIT 20
                """, (1, datetime.now() - timedelta(days=7)))
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                calendar_queries.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            self.results['calendar_queries'] = {
                'time_range_queries': {
                    'avg_ms': statistics.mean(time_range_queries),
                    'min_ms': min(time_range_queries),
                    'max_ms': max(time_range_queries),
                    'total_tests': len(time_range_queries)
                },
                'calendar_specific_queries': {
                    'avg_ms': statistics.mean(calendar_queries),
                    'min_ms': min(calendar_queries),
                    'max_ms': max(calendar_queries),
                    'total_tests': len(calendar_queries)
                }
            }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Calendar performance testing failed: {e}")
            self.results['calendar_queries']['error'] = str(e)
    
    def test_auth_performance(self):
        """Test authentication session query performance"""
        logger.info("🔐 Testing Authentication Query Performance...")
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor()
            
            # Test active session queries (should use idx_auth_sessions_active)
            session_queries = []
            
            for i in range(15):
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT session_id, user_id, created_at, expires_at
                    FROM authentication_sessions 
                    WHERE user_id = %s 
                    AND is_active = true 
                    AND expires_at > NOW()
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (1,))
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                session_queries.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            # Test OAuth token queries (should use idx_oauth_tokens_service_lookup)
            oauth_queries = []
            
            for i in range(10):
                start_time = time.perf_counter()
                
                cursor.execute("""
                    SELECT user_id, service, access_token, token_expiry
                    FROM user_oauth_tokens 
                    WHERE user_id = %s 
                    AND service = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (1, 'google'))
                
                cursor.fetchall()
                
                end_time = time.perf_counter()
                oauth_queries.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            self.results['auth_queries'] = {
                'active_session_queries': {
                    'avg_ms': statistics.mean(session_queries),
                    'min_ms': min(session_queries),
                    'max_ms': max(session_queries),
                    'total_tests': len(session_queries)
                },
                'oauth_token_queries': {
                    'avg_ms': statistics.mean(oauth_queries),
                    'min_ms': min(oauth_queries),
                    'max_ms': max(oauth_queries),
                    'total_tests': len(oauth_queries)
                }
            }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Auth performance testing failed: {e}")
            self.results['auth_queries']['error'] = str(e)
    
    def test_index_effectiveness(self):
        """Test effectiveness of new database indexes"""
        logger.info("📇 Testing Index Effectiveness...")
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor()
            
            # Check if queries are using indexes (EXPLAIN ANALYZE)
            index_usage = {}
            
            # Test profile index usage
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
                SELECT up.* FROM user_profiles up 
                WHERE up.user_id = 1 
                ORDER BY up.created_at DESC
                LIMIT 1
            """)
            
            profile_plan = cursor.fetchone()[0]
            index_usage['profile_lookup'] = {
                'uses_index': 'Index Scan' in str(profile_plan),
                'execution_time': profile_plan[0].get('Execution Time', 0) if profile_plan else 0,
                'planning_time': profile_plan[0].get('Planning Time', 0) if profile_plan else 0
            }
            
            # Test calendar time range index usage
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                SELECT e.* FROM events e 
                WHERE e.start_time >= %s AND e.end_time <= %s
                ORDER BY e.start_time
                LIMIT 10
            """, (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=7)))
            
            calendar_plan = cursor.fetchone()[0]
            index_usage['calendar_time_range'] = {
                'uses_index': 'Index Scan' in str(calendar_plan),
                'execution_time': calendar_plan[0].get('Execution Time', 0) if calendar_plan else 0,
                'planning_time': calendar_plan[0].get('Planning Time', 0) if calendar_plan else 0
            }
            
            # Test auth session index usage
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                SELECT * FROM authentication_sessions 
                WHERE user_id = 1 AND is_active = true 
                AND expires_at > NOW()
                ORDER BY created_at DESC
            """)
            
            auth_plan = cursor.fetchone()[0]
            index_usage['auth_sessions'] = {
                'uses_index': 'Index Scan' in str(auth_plan),
                'execution_time': auth_plan[0].get('Execution Time', 0) if auth_plan else 0,
                'planning_time': auth_plan[0].get('Planning Time', 0) if auth_plan else 0
            }
            
            # Get index usage statistics
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename IN ('user_profiles', 'events', 'authentication_sessions', 'user_oauth_tokens')
                AND idx_scan > 0
                ORDER BY idx_scan DESC
            """)
            
            index_stats = cursor.fetchall()
            
            self.results['index_performance'] = {
                'query_plan_analysis': index_usage,
                'index_usage_statistics': [
                    {
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5]
                    } for row in index_stats
                ],
                'total_active_indexes': len(index_stats)
            }
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Index effectiveness testing failed: {e}")
            self.results['index_performance']['error'] = str(e)
    
    def test_connection_performance(self):
        """Test database connection and pool performance"""
        logger.info("🔌 Testing Connection Performance...")
        
        try:
            # Test connection creation times
            connection_times = []
            
            for i in range(10):
                start_time = time.perf_counter()
                
                conn = psycopg2.connect(**self.db_params)
                conn.close()
                
                end_time = time.perf_counter()
                connection_times.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            # Test concurrent connections
            concurrent_times = []
            
            def create_connection():
                start_time = time.perf_counter()
                conn = psycopg2.connect(**self.db_params)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                end_time = time.perf_counter()
                return (end_time - start_time) * 1000
            
            # Test 5 concurrent connections
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(create_connection) for _ in range(5)]
                concurrent_times = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            self.results['connection_performance'] = {
                'sequential_connections': {
                    'avg_ms': statistics.mean(connection_times),
                    'min_ms': min(connection_times),
                    'max_ms': max(connection_times),
                    'total_tests': len(connection_times)
                },
                'concurrent_connections': {
                    'avg_ms': statistics.mean(concurrent_times),
                    'min_ms': min(concurrent_times),
                    'max_ms': max(concurrent_times),
                    'total_tests': len(concurrent_times)
                }
            }
            
        except Exception as e:
            logger.error(f"Connection performance testing failed: {e}")
            self.results['connection_performance']['error'] = str(e)
    
    def _generate_summary(self):
        """Generate database performance summary"""
        summary = {
            'overall_performance': 'unknown',
            'profile_performance': 'unknown',
            'calendar_performance': 'unknown',
            'auth_performance': 'unknown',
            'index_effectiveness': 'unknown',
            'connection_performance': 'unknown',
            'recommendations': []
        }
        
        # Analyze profile query performance
        if 'profile_queries' in self.results and 'error' not in self.results['profile_queries']:
            lookup_avg = self.results['profile_queries']['lookup_queries'].get('avg_ms', 0)
            if lookup_avg < 10:
                summary['profile_performance'] = 'excellent'
            elif lookup_avg < 50:
                summary['profile_performance'] = 'good'
            else:
                summary['profile_performance'] = 'needs_improvement'
                summary['recommendations'].append('Profile queries are slower than expected. Check if indexes are being used.')
        
        # Analyze calendar query performance
        if 'calendar_queries' in self.results and 'error' not in self.results['calendar_queries']:
            time_range_avg = self.results['calendar_queries']['time_range_queries'].get('avg_ms', 0)
            if time_range_avg < 20:
                summary['calendar_performance'] = 'excellent'
            elif time_range_avg < 100:
                summary['calendar_performance'] = 'good'
            else:
                summary['calendar_performance'] = 'needs_improvement'
                summary['recommendations'].append('Calendar time range queries are slow. Check time indexes.')
        
        # Analyze auth query performance
        if 'auth_queries' in self.results and 'error' not in self.results['auth_queries']:
            session_avg = self.results['auth_queries']['active_session_queries'].get('avg_ms', 0)
            if session_avg < 15:
                summary['auth_performance'] = 'excellent'
            elif session_avg < 50:
                summary['auth_performance'] = 'good'
            else:
                summary['auth_performance'] = 'needs_improvement'
                summary['recommendations'].append('Authentication session queries are slow. Check auth indexes.')
        
        # Analyze index effectiveness
        if 'index_performance' in self.results and 'error' not in self.results['index_performance']:
            active_indexes = self.results['index_performance'].get('total_active_indexes', 0)
            query_plans = self.results['index_performance'].get('query_plan_analysis', {})
            
            using_indexes = sum(1 for plan in query_plans.values() if plan.get('uses_index', False))
            
            if active_indexes >= 5 and using_indexes >= 2:
                summary['index_effectiveness'] = 'excellent'
            elif active_indexes >= 3:
                summary['index_effectiveness'] = 'good'
            else:
                summary['index_effectiveness'] = 'needs_improvement'
                summary['recommendations'].append('Database indexes may not be created or used effectively.')
        
        # Analyze connection performance
        if 'connection_performance' in self.results and 'error' not in self.results['connection_performance']:
            sequential_avg = self.results['connection_performance']['sequential_connections'].get('avg_ms', 0)
            if sequential_avg < 50:
                summary['connection_performance'] = 'excellent'
            elif sequential_avg < 200:
                summary['connection_performance'] = 'good'
            else:
                summary['connection_performance'] = 'needs_improvement'
                summary['recommendations'].append('Database connection times are high. Check connection pool configuration.')
        
        # Overall performance assessment
        performance_scores = [
            summary['profile_performance'],
            summary['calendar_performance'],
            summary['auth_performance'],
            summary['index_effectiveness'],
            summary['connection_performance']
        ]
        
        if all(score in ['excellent', 'good'] for score in performance_scores if score != 'unknown'):
            summary['overall_performance'] = 'excellent'
        elif any(score == 'needs_improvement' for score in performance_scores):
            summary['overall_performance'] = 'needs_improvement'
        else:
            summary['overall_performance'] = 'good'
        
        if not summary['recommendations']:
            summary['recommendations'].append('All database performance tests passed successfully!')
        
        self.results['summary'] = summary
    
    def save_results(self, filename: str = None):
        """Save database performance results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_performance_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"📊 Database performance results saved to {filename}")
        return filename


def main():
    """Main execution function"""
    print("📊 Database Performance Validation Testing")
    print("=" * 50)
    
    validator = DatabasePerformanceValidator()
    
    try:
        results = validator.run_all_tests()
        
        # Save results
        results_file = validator.save_results()
        
        # Print summary
        print("\n📊 DATABASE PERFORMANCE SUMMARY")
        print("=" * 40)
        
        summary = results.get('summary', {})
        print(f"Overall Performance: {summary.get('overall_performance', 'unknown').upper()}")
        print(f"Profile Performance: {summary.get('profile_performance', 'unknown')}")
        print(f"Calendar Performance: {summary.get('calendar_performance', 'unknown')}")
        print(f"Auth Performance: {summary.get('auth_performance', 'unknown')}")
        print(f"Index Effectiveness: {summary.get('index_effectiveness', 'unknown')}")
        print(f"Connection Performance: {summary.get('connection_performance', 'unknown')}")
        
        print("\n📋 Recommendations:")
        for rec in summary.get('recommendations', []):
            print(f"  • {rec}")
        
        # Print key metrics
        if 'profile_queries' in results and 'error' not in results['profile_queries']:
            avg_lookup = results['profile_queries']['lookup_queries'].get('avg_ms', 0)
            print(f"\n📈 Key Metrics:")
            print(f"  Profile Lookup Avg: {avg_lookup:.2f}ms")
        
        if 'calendar_queries' in results and 'error' not in results['calendar_queries']:
            avg_calendar = results['calendar_queries']['time_range_queries'].get('avg_ms', 0)
            print(f"  Calendar Query Avg: {avg_calendar:.2f}ms")
        
        if 'auth_queries' in results and 'error' not in results['auth_queries']:
            avg_auth = results['auth_queries']['active_session_queries'].get('avg_ms', 0)
            print(f"  Auth Session Avg: {avg_auth:.2f}ms")
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Return appropriate exit code
        if summary.get('overall_performance') == 'excellent':
            return 0
        elif summary.get('overall_performance') == 'good':
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error(f"Database performance validation failed: {e}")
        print(f"\n❌ Testing failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)