#!/usr/bin/env python3
"""
Database Performance Validation via Docker

Tests database performance improvements from Phase 2 by executing queries
directly through Docker containers.
"""

import subprocess
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DockerDatabasePerformanceValidator:
    """Validate database performance through Docker containers"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'profile_queries': {},
            'calendar_queries': {},
            'auth_queries': {},
            'index_performance': {},
            'summary': {}
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all database performance validation tests"""
        logger.info("📊 Starting Database Performance Validation via Docker")
        
        try:
            # Test profile queries
            self.test_profile_performance()
            
            # Test calendar queries  
            self.test_calendar_performance()
            
            # Test authentication queries
            self.test_auth_performance()
            
            # Test index usage
            self.test_index_usage()
            
            # Generate summary
            self._generate_summary()
            
            logger.info("✅ Database performance validation completed successfully")
            
        except Exception as e:
            logger.error(f"Database testing failed: {e}")
            self.results['error'] = str(e)
        
        return self.results
    
    def _execute_query(self, query: str, description: str = "query") -> Dict[str, Any]:
        """Execute a database query through Docker and measure performance"""
        try:
            start_time = time.perf_counter()
            
            cmd = [
                'docker', 'compose', 'exec', '-T', 'postgres',
                'psql', '-U', 'app_user', '-d', 'ai_workflow_db',
                '-c', query
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd='/home/marku/ai_workflow_engine'
            )
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            return {
                'execution_time_ms': execution_time,
                'success': result.returncode == 0,
                'output': result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            }
            
        except Exception as e:
            return {
                'execution_time_ms': 0,
                'success': False,
                'error': str(e)
            }
    
    def test_profile_performance(self):
        """Test profile query performance"""
        logger.info("👤 Testing Profile Query Performance...")
        
        # Test profile lookup queries
        profile_lookup_times = []
        
        for i in range(10):
            query = f"""
                SELECT up.user_id, up.first_name, up.last_name, up.work_email, u.username
                FROM user_profiles up 
                JOIN users u ON up.user_id = u.id 
                WHERE up.user_id = {i % 7 + 1}  -- Cycle through available users
                ORDER BY up.created_at DESC
                LIMIT 1;
            """
            
            result = self._execute_query(query, "profile lookup")
            if result['success']:
                profile_lookup_times.append(result['execution_time_ms'])
            
            time.sleep(0.1)
        
        # Test profile completeness queries
        completeness_query = """
            SELECT user_id, first_name, last_name, work_email
            FROM user_profiles 
            WHERE first_name IS NOT NULL 
            AND last_name IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 5;
        """
        
        completeness_times = []
        for i in range(5):
            result = self._execute_query(completeness_query, "profile completeness")
            if result['success']:
                completeness_times.append(result['execution_time_ms'])
            time.sleep(0.1)
        
        self.results['profile_queries'] = {
            'lookup_queries': {
                'avg_ms': statistics.mean(profile_lookup_times) if profile_lookup_times else 0,
                'min_ms': min(profile_lookup_times) if profile_lookup_times else 0,
                'max_ms': max(profile_lookup_times) if profile_lookup_times else 0,
                'total_tests': len(profile_lookup_times),
                'samples': profile_lookup_times[:5] if profile_lookup_times else []  # First 5 samples for reference
            },
            'completeness_queries': {
                'avg_ms': statistics.mean(completeness_times) if completeness_times else 0,
                'total_tests': len(completeness_times)
            }
        }
        
        logger.info(f"Profile queries tested: {len(profile_lookup_times)} lookup, {len(completeness_times)} completeness")
    
    def test_calendar_performance(self):
        """Test calendar query performance"""
        logger.info("📅 Testing Calendar Query Performance...")
        
        # Test time range queries
        time_range_times = []
        
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        for i in range(8):
            query = f"""
                SELECT e.id, e.title, e.start_time, e.end_time, c.name as calendar_name
                FROM events e 
                JOIN calendars c ON e.calendar_id = c.id 
                WHERE e.start_time >= '{start_date}' 
                AND e.end_time <= '{end_date}'
                ORDER BY e.start_time
                LIMIT 20;
            """
            
            result = self._execute_query(query, "calendar time range")
            if result['success']:
                time_range_times.append(result['execution_time_ms'])
            
            time.sleep(0.1)
        
        # Test calendar-specific queries
        calendar_specific_times = []
        
        for i in range(5):
            query = f"""
                SELECT id, title, start_time, end_time
                FROM events 
                WHERE calendar_id = {i % 3 + 1}  -- Assuming at least 3 calendars exist
                AND start_time >= '{start_date}'
                ORDER BY start_time DESC
                LIMIT 10;
            """
            
            result = self._execute_query(query, "calendar specific")
            if result['success']:
                calendar_specific_times.append(result['execution_time_ms'])
            
            time.sleep(0.1)
        
        self.results['calendar_queries'] = {
            'time_range_queries': {
                'avg_ms': statistics.mean(time_range_times) if time_range_times else 0,
                'min_ms': min(time_range_times) if time_range_times else 0,
                'max_ms': max(time_range_times) if time_range_times else 0,
                'total_tests': len(time_range_times)
            },
            'calendar_specific_queries': {
                'avg_ms': statistics.mean(calendar_specific_times) if calendar_specific_times else 0,
                'total_tests': len(calendar_specific_times)
            }
        }
        
        logger.info(f"Calendar queries tested: {len(time_range_times)} time range, {len(calendar_specific_times)} specific")
    
    def test_auth_performance(self):
        """Test authentication query performance"""
        logger.info("🔐 Testing Authentication Query Performance...")
        
        # Test active session queries
        session_times = []
        
        for i in range(8):
            query = f"""
                SELECT session_id, user_id, created_at, expires_at, is_active
                FROM authentication_sessions 
                WHERE user_id = {i % 7 + 1}  -- Cycle through users
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 3;
            """
            
            result = self._execute_query(query, "auth sessions")
            if result['success']:
                session_times.append(result['execution_time_ms'])
            
            time.sleep(0.1)
        
        # Test OAuth token queries
        oauth_times = []
        
        for i in range(5):
            query = f"""
                SELECT user_id, service, created_at, token_expiry
                FROM user_oauth_tokens 
                WHERE user_id = {i % 7 + 1}
                AND service = 'google'
                ORDER BY created_at DESC
                LIMIT 1;
            """
            
            result = self._execute_query(query, "oauth tokens")
            if result['success']:
                oauth_times.append(result['execution_time_ms'])
            
            time.sleep(0.1)
        
        self.results['auth_queries'] = {
            'active_session_queries': {
                'avg_ms': statistics.mean(session_times) if session_times else 0,
                'min_ms': min(session_times) if session_times else 0,
                'max_ms': max(session_times) if session_times else 0,
                'total_tests': len(session_times)
            },
            'oauth_token_queries': {
                'avg_ms': statistics.mean(oauth_times) if oauth_times else 0,
                'total_tests': len(oauth_times)
            }
        }
        
        logger.info(f"Auth queries tested: {len(session_times)} session, {len(oauth_times)} oauth")
    
    def test_index_usage(self):
        """Test database index usage and effectiveness"""
        logger.info("📇 Testing Index Usage and Effectiveness...")
        
        # Check index usage statistics
        index_stats_query = """
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
            LIMIT 10;
        """
        
        result = self._execute_query(index_stats_query, "index statistics")
        
        # Check if key indexes exist
        index_existence_query = """
            SELECT 
                schemaname,
                tablename,
                indexname
            FROM pg_indexes 
            WHERE tablename IN ('user_profiles', 'events', 'authentication_sessions', 'user_oauth_tokens')
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname;
        """
        
        existence_result = self._execute_query(index_existence_query, "index existence")
        
        # Test query plan for profile lookup (should use index)
        explain_query = """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
            SELECT up.* FROM user_profiles up 
            WHERE up.user_id = 1 
            ORDER BY up.created_at DESC
            LIMIT 1;
        """
        
        plan_result = self._execute_query(explain_query, "query plan")
        
        self.results['index_performance'] = {
            'index_statistics_available': result['success'],
            'index_existence_check': existence_result['success'],
            'query_plan_analysis': {
                'available': plan_result['success'],
                'uses_index_scan': 'Index Scan' in plan_result.get('output', '') if plan_result['success'] else False,
                'plan_output': plan_result.get('output', '')[:500] if plan_result['success'] else ''  # First 500 chars
            },
            'raw_stats': {
                'index_stats': result.get('output', '') if result['success'] else '',
                'index_list': existence_result.get('output', '') if existence_result['success'] else ''
            }
        }
    
    def _generate_summary(self):
        """Generate performance summary"""
        summary = {
            'overall_performance': 'unknown',
            'profile_performance': 'unknown',
            'calendar_performance': 'unknown', 
            'auth_performance': 'unknown',
            'index_effectiveness': 'unknown',
            'recommendations': []
        }
        
        # Analyze profile performance
        if 'profile_queries' in self.results and self.results['profile_queries']:
            lookup_data = self.results['profile_queries'].get('lookup_queries', {})
            lookup_avg = lookup_data.get('avg_ms', 0)
            if lookup_avg > 0:
                if lookup_avg < 100:  # Under 100ms is good for Docker queries
                    summary['profile_performance'] = 'excellent'
                elif lookup_avg < 500:
                    summary['profile_performance'] = 'good'
                else:
                    summary['profile_performance'] = 'needs_improvement'
                    summary['recommendations'].append('Profile queries are slower than expected.')
        
        # Analyze calendar performance
        if 'calendar_queries' in self.results and self.results['calendar_queries']:
            time_range_data = self.results['calendar_queries'].get('time_range_queries', {})
            time_range_avg = time_range_data.get('avg_ms', 0)
            if time_range_avg > 0:
                if time_range_avg < 150:
                    summary['calendar_performance'] = 'excellent'
                elif time_range_avg < 800:
                    summary['calendar_performance'] = 'good'
                else:
                    summary['calendar_performance'] = 'needs_improvement'
                    summary['recommendations'].append('Calendar time range queries are slow.')
        
        # Analyze auth performance  
        if 'auth_queries' in self.results and self.results['auth_queries']:
            session_data = self.results['auth_queries'].get('active_session_queries', {})
            session_avg = session_data.get('avg_ms', 0)
            if session_avg > 0:
                if session_avg < 100:
                    summary['auth_performance'] = 'excellent'
                elif session_avg < 400:
                    summary['auth_performance'] = 'good'
                else:
                    summary['auth_performance'] = 'needs_improvement'
                    summary['recommendations'].append('Authentication session queries are slow.')
        
        # Analyze index effectiveness
        if 'index_performance' in self.results:
            index_perf = self.results['index_performance']
            if index_perf.get('query_plan_analysis', {}).get('uses_index_scan', False):
                summary['index_effectiveness'] = 'excellent'
            elif index_perf.get('index_statistics_available', False):
                summary['index_effectiveness'] = 'good'
            else:
                summary['index_effectiveness'] = 'needs_improvement'
                summary['recommendations'].append('Database indexes may not be working effectively.')
        
        # Overall assessment
        performance_scores = [
            summary['profile_performance'],
            summary['calendar_performance'],
            summary['auth_performance'],
            summary['index_effectiveness']
        ]
        
        if all(score in ['excellent', 'good'] for score in performance_scores if score != 'unknown'):
            summary['overall_performance'] = 'excellent'
        elif any(score == 'needs_improvement' for score in performance_scores):
            summary['overall_performance'] = 'needs_improvement'
        else:
            summary['overall_performance'] = 'good'
        
        # Add specific analysis results
        if summary['overall_performance'] == 'unknown':
            # If no data was collected, mark as needs investigation
            summary['overall_performance'] = 'needs_investigation'
            summary['recommendations'].append('No database performance data collected - check database connectivity and table structure.')
        elif not summary['recommendations']:
            summary['recommendations'].append('All database performance tests passed successfully!')
        
        self.results['summary'] = summary
    
    def save_results(self, filename: str = None):
        """Save results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"database_performance_docker_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"📊 Database performance results saved to {filename}")
        return filename


def main():
    """Main execution function"""
    print("📊 Database Performance Validation via Docker")
    print("=" * 50)
    
    validator = DockerDatabasePerformanceValidator()
    
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
        
        print("\n📋 Recommendations:")
        for rec in summary.get('recommendations', []):
            print(f"  • {rec}")
        
        # Print key metrics
        print(f"\n📈 Key Metrics:")
        
        if 'profile_queries' in results and results['profile_queries']:
            avg_lookup = results['profile_queries'].get('lookup_queries', {}).get('avg_ms', 0)
            if avg_lookup > 0:
                print(f"  Profile Lookup Avg: {avg_lookup:.2f}ms")
        
        if 'calendar_queries' in results and results['calendar_queries']:
            avg_calendar = results['calendar_queries'].get('time_range_queries', {}).get('avg_ms', 0)
            if avg_calendar > 0:
                print(f"  Calendar Query Avg: {avg_calendar:.2f}ms")
        
        if 'auth_queries' in results and results['auth_queries']:
            avg_auth = results['auth_queries'].get('active_session_queries', {}).get('avg_ms', 0)
            if avg_auth > 0:
                print(f"  Auth Session Avg: {avg_auth:.2f}ms")
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Return appropriate exit code
        if summary.get('overall_performance') in ['excellent', 'good']:
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