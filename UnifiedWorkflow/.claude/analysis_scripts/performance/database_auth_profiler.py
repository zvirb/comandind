#!/usr/bin/env python3
"""
Database Authentication Performance Profiler
Analyzes database queries related to authentication and session management.
"""
import os
import sys
import time
import asyncio
import psutil
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

@dataclass
class QueryPerformanceMetric:
    """Database query performance metric."""
    query: str
    duration_ms: float
    rows_affected: int
    execution_plan: Optional[str] = None
    index_usage: Optional[str] = None

class DatabaseAuthPerformanceProfiler:
    """Profiles database authentication performance."""
    
    def __init__(self, database_url: str = None):
        """Initialize profiler with database connection."""
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        
        self.session_factory = sessionmaker(bind=self.engine)
    
    def measure_query_performance(self, query: str, params: Dict = None) -> QueryPerformanceMetric:
        """Measure performance of a database query."""
        with self.session_factory() as session:
            start_time = time.perf_counter()
            
            try:
                result = session.execute(text(query), params or {})
                rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
                
                # Get execution plan for SELECT queries
                execution_plan = None
                if query.strip().upper().startswith('SELECT'):
                    explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
                    try:
                        explain_result = session.execute(text(explain_query), params or {})
                        execution_plan = '\n'.join([row[0] for row in explain_result])
                    except Exception:
                        pass
                
                session.commit()
                
            except Exception as e:
                session.rollback()
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                return QueryPerformanceMetric(
                    query=query,
                    duration_ms=duration_ms,
                    rows_affected=0,
                    execution_plan=f"ERROR: {str(e)}"
                )
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return QueryPerformanceMetric(
                query=query,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
                execution_plan=execution_plan
            )
    
    def analyze_user_authentication_queries(self) -> List[QueryPerformanceMetric]:
        """Analyze user authentication query performance."""
        print("=== USER AUTHENTICATION QUERY PERFORMANCE ===\n")
        
        metrics = []
        
        # Test user lookup by email (primary authentication query)
        user_lookup_queries = [
            "SELECT id, email, hashed_password, role, status, is_active FROM users WHERE email = :email LIMIT 1",
            "SELECT * FROM users WHERE email = :email AND is_active = true LIMIT 1",
            "SELECT id, email, role FROM users WHERE email = :email",
        ]
        
        for query in user_lookup_queries:
            print(f"Testing query: {query[:50]}...")
            metric = self.measure_query_performance(query, {"email": "test@example.com"})
            metrics.append(metric)
            
            if "ERROR" in str(metric.execution_plan):
                print(f"  Duration: {metric.duration_ms:.2f}ms (ERROR)")
            else:
                print(f"  Duration: {metric.duration_ms:.2f}ms, Rows: {metric.rows_affected}")
            print()
        
        return metrics
    
    def analyze_session_management_queries(self) -> List[QueryPerformanceMetric]:
        """Analyze session management query performance."""
        print("=== SESSION MANAGEMENT QUERY PERFORMANCE ===\n")
        
        metrics = []
        
        # Test session-related queries
        session_queries = [
            "SELECT * FROM user_sessions WHERE user_id = :user_id AND expires_at > NOW()",
            "SELECT * FROM user_sessions WHERE session_token = :token LIMIT 1",
            "INSERT INTO user_sessions (user_id, session_token, expires_at) VALUES (:user_id, :token, :expires)",
            "UPDATE user_sessions SET last_activity = NOW() WHERE session_token = :token",
            "DELETE FROM user_sessions WHERE expires_at < NOW()",
        ]
        
        for query in session_queries:
            print(f"Testing query: {query[:50]}...")
            
            params = {
                "user_id": 1,
                "token": "test_session_token_12345",
                "expires": "2025-08-16 00:00:00"
            }
            
            metric = self.measure_query_performance(query, params)
            metrics.append(metric)
            
            if "ERROR" in str(metric.execution_plan):
                print(f"  Duration: {metric.duration_ms:.2f}ms (ERROR)")
            else:
                print(f"  Duration: {metric.duration_ms:.2f}ms, Rows: {metric.rows_affected}")
            print()
        
        return metrics
    
    def analyze_oauth_token_queries(self) -> List[QueryPerformanceMetric]:
        """Analyze OAuth token query performance."""
        print("=== OAUTH TOKEN QUERY PERFORMANCE ===\n")
        
        metrics = []
        
        # Test OAuth token queries
        oauth_queries = [
            "SELECT * FROM oauth_tokens WHERE user_id = :user_id AND provider = :provider",
            "SELECT access_token, refresh_token FROM oauth_tokens WHERE user_id = :user_id",
            "UPDATE oauth_tokens SET access_token = :access_token WHERE user_id = :user_id AND provider = :provider",
            "INSERT INTO oauth_tokens (user_id, provider, access_token, refresh_token) VALUES (:user_id, :provider, :access_token, :refresh_token)",
        ]
        
        for query in oauth_queries:
            print(f"Testing query: {query[:50]}...")
            
            params = {
                "user_id": 1,
                "provider": "google",
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token"
            }
            
            metric = self.measure_query_performance(query, params)
            metrics.append(metric)
            
            if "ERROR" in str(metric.execution_plan):
                print(f"  Duration: {metric.duration_ms:.2f}ms (ERROR)")
            else:
                print(f"  Duration: {metric.duration_ms:.2f}ms, Rows: {metric.rows_affected}")
            print()
        
        return metrics
    
    def analyze_database_indexes(self) -> Dict[str, Any]:
        """Analyze database indexes for authentication tables."""
        print("=== DATABASE INDEX ANALYSIS ===\n")
        
        index_analysis = {}
        
        with self.session_factory() as session:
            # Get index information for authentication-related tables
            auth_tables = ['users', 'user_sessions', 'oauth_tokens', 'security_events']
            
            for table_name in auth_tables:
                print(f"Analyzing indexes for table: {table_name}")
                
                try:
                    # Get table indexes
                    index_query = """
                    SELECT 
                        indexname,
                        indexdef,
                        schemaname
                    FROM pg_indexes 
                    WHERE tablename = :table_name
                    """
                    
                    result = session.execute(text(index_query), {"table_name": table_name})
                    indexes = result.fetchall()
                    
                    table_indexes = []
                    for row in indexes:
                        table_indexes.append({
                            "name": row[0],
                            "definition": row[1],
                            "schema": row[2]
                        })
                        print(f"  Index: {row[0]} - {row[1]}")
                    
                    index_analysis[table_name] = table_indexes
                    
                except Exception as e:
                    print(f"  ERROR analyzing {table_name}: {e}")
                    index_analysis[table_name] = []
                
                print()
        
        return index_analysis
    
    def analyze_connection_pool_performance(self) -> Dict[str, Any]:
        """Analyze database connection pool performance."""
        print("=== CONNECTION POOL PERFORMANCE ANALYSIS ===\n")
        
        pool_info = {
            "pool_size": self.engine.pool.size(),
            "checked_in": self.engine.pool.checkedin(),
            "checked_out": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
            "invalid": self.engine.pool.invalid(),
        }
        
        print(f"Pool size: {pool_info['pool_size']}")
        print(f"Checked in connections: {pool_info['checked_in']}")
        print(f"Checked out connections: {pool_info['checked_out']}")
        print(f"Overflow connections: {pool_info['overflow']}")
        print(f"Invalid connections: {pool_info['invalid']}")
        print()
        
        # Test connection acquisition time
        connection_times = []
        for i in range(10):
            start_time = time.perf_counter()
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            end_time = time.perf_counter()
            connection_times.append((end_time - start_time) * 1000)
        
        pool_info["avg_connection_time_ms"] = sum(connection_times) / len(connection_times)
        pool_info["max_connection_time_ms"] = max(connection_times)
        pool_info["min_connection_time_ms"] = min(connection_times)
        
        print(f"Average connection time: {pool_info['avg_connection_time_ms']:.2f}ms")
        print(f"Max connection time: {pool_info['max_connection_time_ms']:.2f}ms")
        print(f"Min connection time: {pool_info['min_connection_time_ms']:.2f}ms")
        print()
        
        return pool_info
    
    def generate_database_performance_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive database performance report."""
        report = {
            "timestamp": time.time(),
            "database_config": {
                "url": self.database_url.split('@')[1] if '@' in self.database_url else "redacted",
                "pool_size": self.engine.pool.size(),
                "max_overflow": self.engine.pool.max_overflow,
            },
            "query_performance": results,
            "bottlenecks": [],
            "index_recommendations": [],
            "optimization_suggestions": []
        }
        
        # Analyze query performance for bottlenecks
        all_metrics = []
        for category in results.values():
            if isinstance(category, list):
                all_metrics.extend(category)
        
        if all_metrics:
            # Find slow queries (>100ms)
            slow_queries = [m for m in all_metrics if m.duration_ms > 100]
            report["bottlenecks"] = [
                {"query": m.query[:100], "duration_ms": m.duration_ms}
                for m in slow_queries
            ]
            
            # Generate optimization suggestions
            avg_duration = sum(m.duration_ms for m in all_metrics) / len(all_metrics)
            if avg_duration > 50:
                report["optimization_suggestions"].append("Average query time exceeds 50ms - consider query optimization")
            
            if len(slow_queries) > 0:
                report["optimization_suggestions"].append(f"Found {len(slow_queries)} slow queries - review execution plans")
        
        return report

def main():
    """Main database performance analysis function."""
    print("Database Authentication Performance Analysis")
    print("=" * 50)
    print()
    
    try:
        # Initialize profiler
        profiler = DatabaseAuthPerformanceProfiler()
        
        # Test database connectivity
        with profiler.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful - starting analysis...\n")
        
    except Exception as e:
        print(f"ERROR: Cannot connect to database")
        print(f"Error: {e}")
        print("Make sure DATABASE_URL is set correctly.")
        return
    
    # Collect performance data
    results = {}
    
    # 1. User authentication queries
    results["user_auth_queries"] = profiler.analyze_user_authentication_queries()
    
    # 2. Session management queries  
    results["session_queries"] = profiler.analyze_session_management_queries()
    
    # 3. OAuth token queries
    results["oauth_queries"] = profiler.analyze_oauth_token_queries()
    
    # 4. Database indexes
    results["index_analysis"] = profiler.analyze_database_indexes()
    
    # 5. Connection pool performance
    results["connection_pool"] = profiler.analyze_connection_pool_performance()
    
    # Generate comprehensive report
    report = profiler.generate_database_performance_report(results)
    
    # Print summary
    print("=== DATABASE PERFORMANCE SUMMARY ===\n")
    if results:
        all_metrics = []
        for category in results.values():
            if isinstance(category, list):
                all_metrics.extend([m for m in category if hasattr(m, 'duration_ms')])
        
        if all_metrics:
            durations = [m.duration_ms for m in all_metrics if not ("ERROR" in str(m.execution_plan))]
            if durations:
                print(f"Total queries tested: {len(all_metrics)}")
                print(f"Successful queries: {len(durations)}")
                print(f"Average query time: {sum(durations) / len(durations):.2f}ms")
                print(f"Maximum query time: {max(durations):.2f}ms")
                print(f"Minimum query time: {min(durations):.2f}ms")
                print()
        
        if report["bottlenecks"]:
            print("DATABASE BOTTLENECKS:")
            for bottleneck in report["bottlenecks"]:
                print(f"  - {bottleneck['query']}: {bottleneck['duration_ms']:.2f}ms")
            print()
        
        if report["optimization_suggestions"]:
            print("OPTIMIZATION SUGGESTIONS:")
            for i, suggestion in enumerate(report["optimization_suggestions"], 1):
                print(f"  {i}. {suggestion}")
            print()
    
    # Save detailed report
    report_file = "database_auth_performance_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Detailed report saved to: {report_file}")
    print("Database performance analysis complete.")

if __name__ == "__main__":
    main()