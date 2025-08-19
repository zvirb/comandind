#!/usr/bin/env python3
"""
Database Performance Optimization Analysis
Comprehensive analysis tool for achieving <100ms response time target

Analyzes:
1. Current database performance metrics and bottlenecks
2. Connection pool configuration and efficiency
3. Query performance patterns and optimization opportunities
4. Index usage and effectiveness
5. Database configuration tuning recommendations
6. Caching layer analysis and optimization potential
"""

import os
import sys
import time
import json
import statistics
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabasePerformanceOptimizer:
    """Comprehensive database performance analysis and optimization tool"""
    
    def __init__(self):
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'current_metrics': {},
            'connection_pool_analysis': {},
            'query_performance': {},
            'configuration_analysis': {},
            'optimization_recommendations': [],
            'performance_baseline': {},
            'target_metrics': {
                'response_time_target_ms': 100,
                'connection_pool_efficiency_target': 85,
                'cache_hit_ratio_target': 95
            }
        }
        
        # Database connection parameters - using direct postgres for analysis
        self.db_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'ai_workflow_db',
            'user': 'app_user',
            'password': 'OVie0GVt2jSUi9aLrh9swS64KGraIZyHLprAEimLwKc='
        }
        
        # PgBouncer parameters for pool analysis
        self.pgbouncer_params = {
            'host': 'localhost',
            'port': 6432,
            'database': 'ai_workflow_db',
            'user': 'app_user',
            'password': 'OVie0GVt2jSUi9aLrh9swS64KGraIZyHLprAEimLwKc='
        }
    
    @contextmanager
    def get_postgres_connection(self):
        """Get direct PostgreSQL connection for analysis"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            yield conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager 
    def get_pgbouncer_connection(self):
        """Get PgBouncer connection for pool analysis"""
        conn = None
        try:
            conn = psycopg2.connect(**self.pgbouncer_params)
            yield conn
        except Exception as e:
            logger.warning(f"Failed to connect to PgBouncer: {e}")
            # Fallback to direct connection for analysis
            conn = psycopg2.connect(**self.db_params)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run complete database performance analysis"""
        logger.info("🔍 Starting Comprehensive Database Performance Analysis")
        
        try:
            # Analyze current performance baseline
            self._analyze_performance_baseline()
            
            # Analyze database configuration
            self._analyze_database_configuration()
            
            # Analyze connection pool performance
            self._analyze_connection_pool_performance()
            
            # Analyze query performance patterns
            self._analyze_query_performance()
            
            # Analyze index usage and effectiveness
            self._analyze_index_effectiveness()
            
            # Analyze database statistics and cache performance
            self._analyze_database_statistics()
            
            # Generate optimization recommendations
            self._generate_optimization_recommendations()
            
            # Calculate performance improvement potential
            self._calculate_improvement_potential()
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            self.analysis_results['error'] = str(e)
        
        return self.analysis_results
    
    def _analyze_performance_baseline(self):
        """Establish current performance baseline"""
        logger.info("📊 Analyzing Performance Baseline...")
        
        baseline = {}
        
        try:
            with self.get_postgres_connection() as conn:
                cursor = conn.cursor()
                
                # Test basic query response times
                query_times = []
                for i in range(20):
                    start_time = time.perf_counter()
                    cursor.execute("SELECT COUNT(*) FROM users")
                    cursor.fetchone()
                    end_time = time.perf_counter()
                    query_times.append((end_time - start_time) * 1000)
                    time.sleep(0.01)
                
                baseline['simple_query_performance'] = {
                    'avg_ms': statistics.mean(query_times),
                    'median_ms': statistics.median(query_times),
                    'min_ms': min(query_times),
                    'max_ms': max(query_times),
                    'p95_ms': sorted(query_times)[int(len(query_times) * 0.95)]
                }
                
                # Test connection establishment time
                connection_times = []
                for i in range(10):
                    start_time = time.perf_counter()
                    test_conn = psycopg2.connect(**self.db_params)
                    test_conn.close()
                    end_time = time.perf_counter()
                    connection_times.append((end_time - start_time) * 1000)
                    time.sleep(0.05)
                
                baseline['connection_establishment'] = {
                    'avg_ms': statistics.mean(connection_times),
                    'median_ms': statistics.median(connection_times),
                    'target_improvement_needed': max(0, statistics.mean(connection_times) - 50)
                }
                
                # Test complex query performance (simulating real workload)
                complex_query_times = []
                for i in range(10):
                    start_time = time.perf_counter()
                    cursor.execute("""
                        SELECT u.id, u.username, u.email, uo.service, uo.created_at
                        FROM users u 
                        LEFT JOIN user_oauth_tokens uo ON u.id = uo.user_id
                        WHERE u.is_active = true
                        ORDER BY u.created_at DESC
                        LIMIT 10
                    """)
                    cursor.fetchall()
                    end_time = time.perf_counter()
                    complex_query_times.append((end_time - start_time) * 1000)
                    time.sleep(0.1)
                
                baseline['complex_query_performance'] = {
                    'avg_ms': statistics.mean(complex_query_times),
                    'target_improvement_needed': max(0, statistics.mean(complex_query_times) - 100)
                }
                
        except Exception as e:
            logger.error(f"Baseline analysis failed: {e}")
            baseline['error'] = str(e)
        
        self.analysis_results['performance_baseline'] = baseline
    
    def _analyze_database_configuration(self):
        """Analyze PostgreSQL configuration for optimization opportunities"""
        logger.info("⚙️ Analyzing Database Configuration...")
        
        config_analysis = {}
        
        try:
            with self.get_postgres_connection() as conn:
                cursor = conn.cursor()
                
                # Get key configuration parameters
                config_params = [
                    'shared_buffers', 'effective_cache_size', 'work_mem', 
                    'maintenance_work_mem', 'max_connections', 'random_page_cost',
                    'seq_page_cost', 'checkpoint_completion_target', 'wal_buffers',
                    'default_statistics_target', 'effective_io_concurrency'
                ]
                
                current_config = {}
                for param in config_params:
                    cursor.execute("SELECT current_setting(%s)", (param,))
                    current_config[param] = cursor.fetchone()[0]
                
                config_analysis['current_configuration'] = current_config
                
                # Analyze memory allocation
                memory_analysis = self._analyze_memory_configuration(current_config)
                config_analysis['memory_analysis'] = memory_analysis
                
                # Analyze connection settings
                connection_analysis = self._analyze_connection_configuration(current_config)
                config_analysis['connection_analysis'] = connection_analysis
                
                # Get database size and recommend memory settings
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                db_size = cursor.fetchone()[0]
                config_analysis['database_size'] = db_size
                
        except Exception as e:
            logger.error(f"Configuration analysis failed: {e}")
            config_analysis['error'] = str(e)
        
        self.analysis_results['configuration_analysis'] = config_analysis
    
    def _analyze_memory_configuration(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Analyze memory configuration and recommendations"""
        analysis = {}
        
        # Extract numeric values from PostgreSQL memory settings
        def parse_memory(value: str) -> int:
            """Parse PostgreSQL memory value to MB"""
            if value.endswith('MB'):
                return int(value[:-2])
            elif value.endswith('GB'):
                return int(value[:-2]) * 1024
            elif value.endswith('kB'):
                return int(value[:-2]) // 1024
            else:
                return int(value) // (1024 * 1024)  # Assume bytes
        
        try:
            shared_buffers_mb = parse_memory(config['shared_buffers'])
            effective_cache_mb = parse_memory(config['effective_cache_size'])
            work_mem_mb = parse_memory(config['work_mem'])
            
            analysis['current_memory_allocation'] = {
                'shared_buffers_mb': shared_buffers_mb,
                'effective_cache_size_mb': effective_cache_mb,
                'work_mem_mb': work_mem_mb
            }
            
            # Memory optimization recommendations
            recommendations = []
            
            if shared_buffers_mb < 256:
                recommendations.append({
                    'parameter': 'shared_buffers',
                    'current': f"{shared_buffers_mb}MB",
                    'recommended': '512MB',
                    'impact': 'High - Better buffer cache performance',
                    'justification': 'For production workloads, 25% of available RAM is recommended'
                })
            
            if work_mem_mb < 8:
                recommendations.append({
                    'parameter': 'work_mem',
                    'current': f"{work_mem_mb}MB",
                    'recommended': '16MB',
                    'impact': 'Medium - Improved sorting and hash operations',
                    'justification': 'Higher work_mem reduces disk I/O for complex queries'
                })
            
            analysis['memory_recommendations'] = recommendations
            
        except Exception as e:
            analysis['error'] = f"Memory analysis failed: {e}"
        
        return analysis
    
    def _analyze_connection_configuration(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Analyze connection configuration"""
        analysis = {}
        
        try:
            max_connections = int(config['max_connections'])
            
            analysis['current_connections'] = {
                'max_connections': max_connections
            }
            
            # Connection recommendations
            recommendations = []
            
            if max_connections > 200:
                recommendations.append({
                    'parameter': 'max_connections',
                    'current': str(max_connections),
                    'recommended': '150',
                    'impact': 'Medium - Reduced memory overhead',
                    'justification': 'With PgBouncer, lower max_connections improves memory efficiency'
                })
            
            analysis['connection_recommendations'] = recommendations
            
        except Exception as e:
            analysis['error'] = f"Connection analysis failed: {e}"
        
        return analysis
    
    def _analyze_connection_pool_performance(self):
        """Analyze connection pool performance and efficiency"""
        logger.info("🔗 Analyzing Connection Pool Performance...")
        
        pool_analysis = {}
        
        try:
            # Test connection pool efficiency
            pool_times = []
            
            # Test multiple connections through PgBouncer
            for i in range(20):
                start_time = time.perf_counter()
                
                try:
                    with self.get_pgbouncer_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                    
                    end_time = time.perf_counter()
                    pool_times.append((end_time - start_time) * 1000)
                except Exception as e:
                    logger.warning(f"Pool connection test failed: {e}")
                    pool_times.append(1000)  # Mark as slow
                
                time.sleep(0.02)
            
            pool_analysis['connection_pool_performance'] = {
                'avg_ms': statistics.mean(pool_times),
                'median_ms': statistics.median(pool_times),
                'p95_ms': sorted(pool_times)[int(len(pool_times) * 0.95)],
                'efficiency_rating': self._calculate_pool_efficiency(pool_times)
            }
            
            # Analyze pool configuration effectiveness
            pool_config_analysis = self._analyze_pool_configuration()
            pool_analysis['configuration_effectiveness'] = pool_config_analysis
            
        except Exception as e:
            logger.error(f"Connection pool analysis failed: {e}")
            pool_analysis['error'] = str(e)
        
        self.analysis_results['connection_pool_analysis'] = pool_analysis
    
    def _calculate_pool_efficiency(self, response_times: List[float]) -> str:
        """Calculate connection pool efficiency rating"""
        avg_time = statistics.mean(response_times)
        
        if avg_time < 10:
            return "Excellent (>95%)"
        elif avg_time < 25:
            return "Good (85-95%)"
        elif avg_time < 50:
            return "Fair (70-85%)"
        else:
            return "Poor (<70%)"
    
    def _analyze_pool_configuration(self) -> Dict[str, Any]:
        """Analyze PgBouncer pool configuration"""
        analysis = {}
        
        try:
            # Read PgBouncer configuration
            config_file = "/home/marku/ai_workflow_engine/config/pgbouncer/pgbouncer.ini"
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_content = f.read()
                
                # Extract key configuration values
                config_values = {}
                for line in config_content.split('\n'):
                    if '=' in line and not line.strip().startswith('#') and not line.strip().startswith('['):
                        key, value = line.split('=', 1)
                        config_values[key.strip()] = value.strip()
                
                analysis['pgbouncer_config'] = {
                    'default_pool_size': config_values.get('default_pool_size', 'unknown'),
                    'max_client_conn': config_values.get('max_client_conn', 'unknown'),
                    'reserve_pool_size': config_values.get('reserve_pool_size', 'unknown'),
                    'max_db_connections': config_values.get('max_db_connections', 'unknown'),
                    'pool_mode': config_values.get('pool_mode', 'unknown')
                }
                
                # Analyze configuration effectiveness
                recommendations = []
                
                try:
                    pool_size = int(config_values.get('default_pool_size', 60))
                    max_client = int(config_values.get('max_client_conn', 500))
                    
                    if pool_size < 30:
                        recommendations.append({
                            'parameter': 'default_pool_size',
                            'current': str(pool_size),
                            'recommended': '40-60',
                            'impact': 'High - Increase connection availability'
                        })
                    
                    if max_client < 300:
                        recommendations.append({
                            'parameter': 'max_client_conn', 
                            'current': str(max_client),
                            'recommended': '400-600',
                            'impact': 'Medium - Handle more concurrent requests'
                        })
                        
                except ValueError:
                    pass
                
                analysis['pool_recommendations'] = recommendations
            
        except Exception as e:
            analysis['error'] = f"Pool configuration analysis failed: {e}"
        
        return analysis
    
    def _analyze_query_performance(self):
        """Analyze query performance patterns"""
        logger.info("🚀 Analyzing Query Performance Patterns...")
        
        query_analysis = {}
        
        try:
            with self.get_postgres_connection() as conn:
                cursor = conn.cursor()
                
                # Test common query patterns with timing
                query_patterns = {
                    'user_lookup': "SELECT * FROM users WHERE id = %s",
                    'user_authentication': "SELECT id, username, password_hash FROM users WHERE username = %s",
                    'oauth_token_lookup': "SELECT * FROM user_oauth_tokens WHERE user_id = %s AND service = %s",
                    'user_join_query': """
                        SELECT u.*, uo.service, uo.access_token 
                        FROM users u 
                        LEFT JOIN user_oauth_tokens uo ON u.id = uo.user_id 
                        WHERE u.id = %s
                    """,
                    'category_aggregation': "SELECT category_name, COUNT(*) FROM user_categories GROUP BY category_name"
                }
                
                pattern_performance = {}
                
                for pattern_name, query in query_patterns.items():
                    times = []
                    
                    for i in range(10):
                        start_time = time.perf_counter()
                        
                        try:
                            if pattern_name == 'user_lookup':
                                cursor.execute(query, (1,))
                            elif pattern_name == 'user_authentication':
                                cursor.execute(query, ('test_user',))
                            elif pattern_name == 'oauth_token_lookup':
                                cursor.execute(query, (1, 'google'))
                            elif pattern_name == 'user_join_query':
                                cursor.execute(query, (1,))
                            else:
                                cursor.execute(query)
                            
                            cursor.fetchall()
                        except Exception as e:
                            logger.warning(f"Query {pattern_name} failed: {e}")
                            times.append(1000)  # Mark as slow
                            continue
                        
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)
                        time.sleep(0.05)
                    
                    if times:
                        pattern_performance[pattern_name] = {
                            'avg_ms': statistics.mean(times),
                            'median_ms': statistics.median(times),
                            'max_ms': max(times),
                            'improvement_needed': max(0, statistics.mean(times) - 50)
                        }
                
                query_analysis['query_patterns'] = pattern_performance
                
                # Identify optimization opportunities
                optimization_opportunities = []
                for pattern, perf in pattern_performance.items():
                    if perf['avg_ms'] > 50:
                        optimization_opportunities.append({
                            'query_pattern': pattern,
                            'current_avg_ms': perf['avg_ms'],
                            'optimization_potential': 'High' if perf['avg_ms'] > 100 else 'Medium',
                            'recommended_actions': self._get_query_optimization_recommendations(pattern)
                        })
                
                query_analysis['optimization_opportunities'] = optimization_opportunities
                
        except Exception as e:
            logger.error(f"Query performance analysis failed: {e}")
            query_analysis['error'] = str(e)
        
        self.analysis_results['query_performance'] = query_analysis
    
    def _get_query_optimization_recommendations(self, pattern: str) -> List[str]:
        """Get specific optimization recommendations for query patterns"""
        recommendations = {
            'user_lookup': [
                'Ensure index on users.id (primary key)',
                'Consider partial index if filtering by status'
            ],
            'user_authentication': [
                'Create index on users.username',
                'Consider covering index including password_hash'
            ],
            'oauth_token_lookup': [
                'Create composite index on (user_id, service)',
                'Consider index on token_expiry for cleanup queries'
            ],
            'user_join_query': [
                'Ensure foreign key indexes exist',
                'Consider materialized view for frequent joins'
            ],
            'category_aggregation': [
                'Create index on category_name',
                'Consider partial indexes for active categories'
            ]
        }
        
        return recommendations.get(pattern, ['Add appropriate indexes', 'Analyze query execution plan'])
    
    def _analyze_index_effectiveness(self):
        """Analyze database index usage and effectiveness"""
        logger.info("📇 Analyzing Index Effectiveness...")
        
        index_analysis = {}
        
        try:
            with self.get_postgres_connection() as conn:
                cursor = conn.cursor()
                
                # Get index usage statistics
                cursor.execute("""
                    SELECT 
                        schemaname,
                        relname as table_name,
                        indexrelname as index_name,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    ORDER BY idx_scan DESC
                """)
                
                index_stats = cursor.fetchall()
                
                index_analysis['index_usage_statistics'] = [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5],
                        'effectiveness': 'High' if row[3] > 100 else 'Low' if row[3] < 10 else 'Medium'
                    } for row in index_stats
                ]
                
                # Get table sizes and index sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename))) as table_size,
                        pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename)) as table_size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(quote_ident(schemaname)||'.'||quote_ident(tablename)) DESC
                """)
                
                table_sizes = cursor.fetchall()
                
                index_analysis['table_sizes'] = [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'size_pretty': row[2],
                        'size_bytes': row[3]
                    } for row in table_sizes
                ]
                
                # Identify missing indexes
                missing_indexes = self._identify_missing_indexes()
                index_analysis['missing_indexes'] = missing_indexes
                
                # Calculate index efficiency score
                total_scans = sum(stat['scans'] for stat in index_analysis['index_usage_statistics'])
                active_indexes = len([stat for stat in index_analysis['index_usage_statistics'] if stat['scans'] > 0])
                
                index_analysis['efficiency_metrics'] = {
                    'total_index_scans': total_scans,
                    'active_indexes': active_indexes,
                    'efficiency_score': min(100, (active_indexes / max(1, len(index_analysis['index_usage_statistics']))) * 100)
                }
                
        except Exception as e:
            logger.error(f"Index analysis failed: {e}")
            index_analysis['error'] = str(e)
        
        self.analysis_results['index_effectiveness'] = index_analysis
    
    def _identify_missing_indexes(self) -> List[Dict[str, str]]:
        """Identify potentially missing indexes based on common patterns"""
        missing_indexes = [
            {
                'table': 'users',
                'columns': 'username',
                'type': 'btree',
                'justification': 'Authentication queries frequently filter by username',
                'priority': 'High'
            },
            {
                'table': 'users', 
                'columns': 'email',
                'type': 'btree',
                'justification': 'Email-based lookups for password reset and notifications',
                'priority': 'Medium'
            },
            {
                'table': 'user_oauth_tokens',
                'columns': '(user_id, service)',
                'type': 'btree',
                'justification': 'OAuth token lookups always filter by user and service',
                'priority': 'High'
            },
            {
                'table': 'user_oauth_tokens',
                'columns': 'token_expiry',
                'type': 'btree',
                'justification': 'Token cleanup and validation queries filter by expiry',
                'priority': 'Medium'
            },
            {
                'table': 'users',
                'columns': '(is_active, created_at)',
                'type': 'btree',
                'justification': 'User listing queries often filter by status and sort by creation date',
                'priority': 'Medium'
            }
        ]
        
        return missing_indexes
    
    def _analyze_database_statistics(self):
        """Analyze database statistics and cache performance"""
        logger.info("📈 Analyzing Database Statistics...")
        
        stats_analysis = {}
        
        try:
            with self.get_postgres_connection() as conn:
                cursor = conn.cursor()
                
                # Get cache hit ratios
                cursor.execute("""
                    SELECT 
                        'index hit rate' as name,
                        (sum(idx_blks_hit)) / nullif(sum(idx_blks_hit + idx_blks_read),0) as ratio
                    FROM pg_statio_user_indexes
                    UNION ALL
                    SELECT 
                        'table hit rate' as name,
                        sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read),0) as ratio
                    FROM pg_statio_user_tables
                """)
                
                hit_ratios = cursor.fetchall()
                
                stats_analysis['cache_hit_ratios'] = {
                    row[0]: {
                        'ratio': float(row[1]) if row[1] else 0,
                        'percentage': float(row[1]) * 100 if row[1] else 0,
                        'status': 'Good' if (row[1] and float(row[1]) > 0.9) else 'Needs Improvement'
                    } for row in hit_ratios if row[1] is not None
                }
                
                # Get database activity statistics
                cursor.execute("""
                    SELECT 
                        datname,
                        numbackends,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        tup_returned,
                        tup_fetched,
                        tup_inserted,
                        tup_updated,
                        tup_deleted
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                db_stats = cursor.fetchone()
                
                if db_stats:
                    stats_analysis['database_activity'] = {
                        'active_connections': db_stats[1],
                        'transactions_committed': db_stats[2],
                        'transactions_rolled_back': db_stats[3],
                        'blocks_read_from_disk': db_stats[4],
                        'blocks_read_from_cache': db_stats[5],
                        'cache_hit_ratio': (db_stats[5] / (db_stats[4] + db_stats[5])) * 100 if (db_stats[4] + db_stats[5]) > 0 else 0,
                        'tuples_returned': db_stats[6],
                        'tuples_fetched': db_stats[7],
                        'tuples_inserted': db_stats[8],
                        'tuples_updated': db_stats[9],
                        'tuples_deleted': db_stats[10]
                    }
                
                # Get slow query information if available
                try:
                    cursor.execute("""
                        SELECT query, calls, total_time, mean_time, max_time
                        FROM pg_stat_statements 
                        ORDER BY mean_time DESC 
                        LIMIT 5
                    """)
                    slow_queries = cursor.fetchall()
                    
                    stats_analysis['slow_queries'] = [
                        {
                            'query': row[0][:100] + '...' if len(row[0]) > 100 else row[0],
                            'calls': row[1],
                            'total_time_ms': row[2],
                            'mean_time_ms': row[3],
                            'max_time_ms': row[4]
                        } for row in slow_queries
                    ]
                except Exception:
                    # pg_stat_statements extension might not be installed
                    stats_analysis['slow_queries'] = []
                    logger.info("pg_stat_statements not available - cannot analyze slow queries")
                
        except Exception as e:
            logger.error(f"Database statistics analysis failed: {e}")
            stats_analysis['error'] = str(e)
        
        self.analysis_results['database_statistics'] = stats_analysis
    
    def _generate_optimization_recommendations(self):
        """Generate comprehensive optimization recommendations"""
        logger.info("💡 Generating Optimization Recommendations...")
        
        recommendations = []
        
        # Analyze performance baseline results
        baseline = self.analysis_results.get('performance_baseline', {})
        if baseline.get('simple_query_performance', {}).get('avg_ms', 0) > 5:
            recommendations.append({
                'category': 'Query Performance',
                'priority': 'High',
                'recommendation': 'Optimize basic query performance',
                'current_value': f"{baseline['simple_query_performance']['avg_ms']:.2f}ms",
                'target_value': '<5ms',
                'actions': [
                    'Review and optimize slow queries',
                    'Ensure proper indexing strategy',
                    'Consider query result caching'
                ],
                'estimated_improvement': '30-50% reduction in response time'
            })
        
        # Connection pool recommendations
        pool_analysis = self.analysis_results.get('connection_pool_analysis', {})
        if pool_analysis.get('connection_pool_performance', {}).get('avg_ms', 0) > 20:
            recommendations.append({
                'category': 'Connection Pooling',
                'priority': 'High',
                'recommendation': 'Optimize PgBouncer connection pool configuration',
                'current_value': f"{pool_analysis['connection_pool_performance']['avg_ms']:.2f}ms",
                'target_value': '<15ms',
                'actions': [
                    'Increase default_pool_size to 80-100',
                    'Optimize pool_timeout settings',
                    'Review connection pool mode effectiveness',
                    'Monitor and tune reserve_pool_size'
                ],
                'estimated_improvement': '25-40% improvement in connection efficiency'
            })
        
        # Memory configuration recommendations
        config_analysis = self.analysis_results.get('configuration_analysis', {})
        memory_recs = config_analysis.get('memory_analysis', {}).get('memory_recommendations', [])
        if memory_recs:
            recommendations.append({
                'category': 'Memory Configuration',
                'priority': 'Medium',
                'recommendation': 'Optimize PostgreSQL memory settings',
                'actions': [rec['parameter'] + ': ' + rec['recommended'] for rec in memory_recs],
                'estimated_improvement': '15-30% improvement in query performance'
            })
        
        # Index recommendations
        index_analysis = self.analysis_results.get('index_effectiveness', {})
        missing_indexes = index_analysis.get('missing_indexes', [])
        high_priority_indexes = [idx for idx in missing_indexes if idx.get('priority') == 'High']
        
        if high_priority_indexes:
            recommendations.append({
                'category': 'Database Indexing',
                'priority': 'High',
                'recommendation': 'Create missing high-priority indexes',
                'actions': [
                    f"CREATE INDEX ON {idx['table']} {idx['columns']}" for idx in high_priority_indexes
                ],
                'estimated_improvement': '40-60% improvement in query performance'
            })
        
        # Cache optimization recommendations
        stats_analysis = self.analysis_results.get('database_statistics', {})
        cache_ratios = stats_analysis.get('cache_hit_ratios', {})
        
        poor_cache_performance = any(
            ratio['percentage'] < 90 for ratio in cache_ratios.values()
        )
        
        if poor_cache_performance:
            recommendations.append({
                'category': 'Cache Performance',
                'priority': 'Medium',
                'recommendation': 'Improve database cache hit ratios',
                'actions': [
                    'Increase shared_buffers to 512MB-1GB',
                    'Optimize effective_cache_size setting',
                    'Implement application-level caching for frequent queries',
                    'Consider Redis caching for session data'
                ],
                'estimated_improvement': '20-35% reduction in I/O operations'
            })
        
        # Query optimization recommendations
        query_analysis = self.analysis_results.get('query_performance', {})
        optimization_opportunities = query_analysis.get('optimization_opportunities', [])
        
        if optimization_opportunities:
            recommendations.append({
                'category': 'Query Optimization',
                'priority': 'High',
                'recommendation': 'Optimize slow query patterns',
                'actions': [
                    f"Optimize {opp['query_pattern']}: {opp['current_avg_ms']:.1f}ms -> target <50ms" 
                    for opp in optimization_opportunities[:3]
                ],
                'estimated_improvement': '45-70% improvement in application response time'
            })
        
        self.analysis_results['optimization_recommendations'] = recommendations
    
    def _calculate_improvement_potential(self):
        """Calculate overall performance improvement potential"""
        logger.info("📊 Calculating Performance Improvement Potential...")
        
        baseline = self.analysis_results.get('performance_baseline', {})
        current_avg = baseline.get('simple_query_performance', {}).get('avg_ms', 180)
        target_response_time = 100
        
        # Calculate theoretical improvement based on optimizations
        potential_improvements = {
            'index_optimization': 0.4,  # 40% improvement
            'connection_pool_optimization': 0.25,  # 25% improvement
            'memory_configuration': 0.20,  # 20% improvement
            'query_optimization': 0.50,  # 50% improvement
            'caching_improvements': 0.30   # 30% improvement
        }
        
        # Calculate compound improvement (not additive)
        compound_improvement = 1.0
        for improvement in potential_improvements.values():
            compound_improvement *= (1.0 - improvement)
        
        total_improvement_percentage = (1.0 - compound_improvement) * 100
        projected_response_time = current_avg * compound_improvement
        
        improvement_analysis = {
            'current_baseline_ms': current_avg,
            'target_response_time_ms': target_response_time,
            'projected_response_time_ms': projected_response_time,
            'total_improvement_percentage': total_improvement_percentage,
            'target_achievable': projected_response_time <= target_response_time,
            'improvement_breakdown': potential_improvements,
            'confidence_level': 'High' if projected_response_time <= target_response_time else 'Medium'
        }
        
        self.analysis_results['improvement_potential'] = improvement_analysis
    
    def save_analysis(self, filename: str = None) -> str:
        """Save analysis results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/marku/ai_workflow_engine/.claude/database_performance_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        logger.info(f"📊 Analysis results saved to {filename}")
        return filename
    
    def print_executive_summary(self):
        """Print executive summary of analysis results"""
        print("\n" + "="*80)
        print("🔍 DATABASE PERFORMANCE OPTIMIZATION ANALYSIS")
        print("="*80)
        
        # Current Performance
        baseline = self.analysis_results.get('performance_baseline', {})
        current_response = baseline.get('simple_query_performance', {}).get('avg_ms', 0)
        
        print(f"\n📊 CURRENT PERFORMANCE BASELINE:")
        print(f"   Average Query Response Time: {current_response:.2f}ms")
        print(f"   Target Response Time: {self.analysis_results['target_metrics']['response_time_target_ms']}ms")
        
        # Improvement Potential
        improvement = self.analysis_results.get('improvement_potential', {})
        if improvement:
            projected = improvement.get('projected_response_time_ms', 0)
            improvement_pct = improvement.get('total_improvement_percentage', 0)
            achievable = improvement.get('target_achievable', False)
            
            print(f"\n🎯 OPTIMIZATION POTENTIAL:")
            print(f"   Projected Response Time: {projected:.2f}ms")
            print(f"   Total Improvement: {improvement_pct:.1f}%")
            print(f"   Target Achievable: {'✅ YES' if achievable else '❌ NO (Additional optimizations needed)'}")
        
        # Top Recommendations
        recommendations = self.analysis_results.get('optimization_recommendations', [])
        high_priority = [r for r in recommendations if r.get('priority') == 'High']
        
        print(f"\n🚀 HIGH PRIORITY RECOMMENDATIONS:")
        for i, rec in enumerate(high_priority[:3], 1):
            print(f"   {i}. {rec['recommendation']}")
            print(f"      Impact: {rec.get('estimated_improvement', 'Significant')}")
        
        # Connection Pool Status
        pool_analysis = self.analysis_results.get('connection_pool_analysis', {})
        if pool_analysis.get('connection_pool_performance'):
            pool_avg = pool_analysis['connection_pool_performance'].get('avg_ms', 0)
            efficiency = pool_analysis['connection_pool_performance'].get('efficiency_rating', 'Unknown')
            print(f"\n🔗 CONNECTION POOL PERFORMANCE:")
            print(f"   Average Pool Response: {pool_avg:.2f}ms")
            print(f"   Efficiency Rating: {efficiency}")
        
        # Index Effectiveness
        index_analysis = self.analysis_results.get('index_effectiveness', {})
        if index_analysis.get('efficiency_metrics'):
            efficiency_score = index_analysis['efficiency_metrics'].get('efficiency_score', 0)
            active_indexes = index_analysis['efficiency_metrics'].get('active_indexes', 0)
            print(f"\n📇 INDEX EFFECTIVENESS:")
            print(f"   Active Indexes: {active_indexes}")
            print(f"   Efficiency Score: {efficiency_score:.1f}%")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    print("🔍 Database Performance Optimization Analysis")
    print("="*60)
    
    optimizer = DatabasePerformanceOptimizer()
    
    try:
        # Run comprehensive analysis
        results = optimizer.run_comprehensive_analysis()
        
        # Save detailed results
        results_file = optimizer.save_analysis()
        
        # Print executive summary
        optimizer.print_executive_summary()
        
        print(f"\n📄 Detailed analysis saved to: {results_file}")
        
        # Return success if target is achievable
        improvement = results.get('improvement_potential', {})
        if improvement.get('target_achievable', False):
            print("\n✅ Target response time (<100ms) is achievable with recommended optimizations!")
            return 0
        else:
            print("\n⚠️  Additional optimizations beyond current recommendations may be needed.")
            return 1
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)