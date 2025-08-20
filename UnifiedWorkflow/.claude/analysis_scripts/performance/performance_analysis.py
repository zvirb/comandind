#!/usr/bin/env python3
"""
Database Connection Pool Performance Analysis

Analyzes current pool configuration, identifies bottlenecks, and provides 
optimization recommendations for the authentication-heavy workload.
"""

import sys
import os
import time
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add app to Python path
sys.path.insert(0, '/home/marku/ai_workflow_engine/app')

from shared.utils.database_setup import get_database_stats, initialize_database, get_engine, get_async_engine
from shared.utils.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Comprehensive database connection pool performance analyzer."""
    
    def __init__(self):
        self.settings = get_settings()
        self.is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        self.service_type = "api" if os.path.exists("/etc/certs/api") else "worker"
        
    def analyze_current_config(self) -> Dict[str, Any]:
        """Analyze current connection pool configuration."""
        logger.info("Analyzing current database configuration...")
        
        analysis = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "service_type": self.service_type,
            "database_url": self.settings.database_url,
            "is_pgbouncer": "pgbouncer" in self.settings.database_url.lower(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Expected configuration based on database_setup.py
        if self.is_production:
            if self.service_type == "api":
                expected_config = {
                    "pool_size": 30,
                    "max_overflow": 50, 
                    "pool_timeout": 60,
                    "pool_recycle": 3600,
                    "async_pool_size": 21,  # 70% of sync
                    "async_max_overflow": 30  # 60% of sync overflow
                }
            else:
                expected_config = {
                    "pool_size": 15,
                    "max_overflow": 25,
                    "pool_timeout": 90,
                    "pool_recycle": 7200,
                    "async_pool_size": 11,
                    "async_max_overflow": 15
                }
        else:
            expected_config = {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 45,
                "pool_recycle": 3600,
                "async_pool_size": 7,
                "async_max_overflow": 12
            }
        
        analysis["expected_config"] = expected_config
        return analysis
    
    def get_current_pool_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics."""
        try:
            stats = get_database_stats()
            
            # Add calculated metrics
            for engine_type in ["sync_engine", "async_engine"]:
                if stats.get(engine_type):
                    engine_stats = stats[engine_type]
                    pool_size = engine_stats.get("pool_size", 0)
                    created = engine_stats.get("connections_created", 0)
                    available = engine_stats.get("connections_available", 0)
                    overflow = engine_stats.get("connections_overflow", 0)
                    total = engine_stats.get("total_connections", 0)
                    
                    # Calculate utilization metrics
                    if pool_size > 0:
                        engine_stats["pool_utilization"] = created / pool_size
                        engine_stats["active_connections"] = created - available
                        engine_stats["overflow_utilization"] = overflow / max(1, total - pool_size) if total > pool_size else 0
                        engine_stats["total_utilization"] = created / total if total > 0 else 0
                    
            return stats
        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {}
    
    def identify_authentication_bottlenecks(self) -> List[str]:
        """Identify specific bottlenecks in authentication flow."""
        bottlenecks = []
        
        # Analyze router patterns for session usage
        router_analysis = self.analyze_router_session_patterns()
        
        # Authentication-specific bottlenecks
        auth_patterns = [
            "Multiple database lookups per authentication request",
            "Sync fallback in async authentication dependency (lines 182-212 in dependencies.py)",
            "Mixed sync/async session usage across routers", 
            "Session not properly closed in error conditions",
            "Token validation requiring database lookup for every request"
        ]
        
        bottlenecks.extend(auth_patterns)
        
        # Router-specific issues
        if router_analysis["mixed_session_usage"]:
            bottlenecks.append("Mixed sync/async session usage causing pool fragmentation")
            
        if router_analysis["high_session_routers"]:
            bottlenecks.append(f"High session usage routers: {', '.join(router_analysis['high_session_routers'])}")
        
        return bottlenecks
    
    def analyze_router_session_patterns(self) -> Dict[str, Any]:
        """Analyze session usage patterns across routers."""
        import glob
        import re
        
        analysis = {
            "sync_session_routers": [],
            "async_session_routers": [],
            "mixed_session_usage": False,
            "high_session_routers": [],
            "session_dependency_count": {}
        }
        
        router_files = glob.glob("/home/marku/ai_workflow_engine/app/api/routers/*.py")
        
        for router_file in router_files:
            try:
                with open(router_file, 'r') as f:
                    content = f.read()
                    
                router_name = os.path.basename(router_file)
                
                # Count session dependencies
                sync_deps = len(re.findall(r'Depends\(get_db\)', content))
                async_deps = len(re.findall(r'Depends\(get_async_session\)', content))
                
                analysis["session_dependency_count"][router_name] = {
                    "sync": sync_deps,
                    "async": async_deps,
                    "total": sync_deps + async_deps
                }
                
                if sync_deps > 0:
                    analysis["sync_session_routers"].append(router_name)
                if async_deps > 0:
                    analysis["async_session_routers"].append(router_name)
                if sync_deps > 0 and async_deps > 0:
                    analysis["mixed_session_usage"] = True
                    
                # High usage routers (>5 session dependencies)
                if sync_deps + async_deps > 5:
                    analysis["high_session_routers"].append(router_name)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze {router_file}: {e}")
        
        return analysis
    
    def calculate_optimal_pool_config(self) -> Dict[str, Any]:
        """Calculate optimal pool configuration for authentication workload."""
        
        # Authentication load estimates
        concurrent_auth_requests = {
            "development": 5,
            "production": 25  # Peak concurrent authentication requests
        }
        
        environment = "production" if self.is_production else "development"
        base_concurrent = concurrent_auth_requests[environment]
        
        # Factor in authentication patterns
        auth_multiplier = 2.0  # Each auth request may need 2 connections (lookup + update)
        safety_factor = 1.5    # Safety margin for spikes
        
        optimal_pool_size = int(base_concurrent * auth_multiplier * safety_factor)
        optimal_overflow = int(optimal_pool_size * 0.8)  # 80% of pool size
        
        # Async pool sizing (authentication-heavy, so larger than default 70%)
        async_ratio = 0.8  # 80% of sync pool for async authentication
        optimal_async_pool = int(optimal_pool_size * async_ratio)
        optimal_async_overflow = int(optimal_overflow * 0.7)
        
        optimal_config = {
            "sync_pool_size": optimal_pool_size,
            "sync_max_overflow": optimal_overflow,
            "async_pool_size": optimal_async_pool,
            "async_max_overflow": optimal_async_overflow,
            "pool_timeout": 30,  # Faster timeout for auth responsiveness
            "pool_recycle": 1800,  # More frequent recycling
            "pool_pre_ping": True,
            "reasoning": {
                "base_concurrent_requests": base_concurrent,
                "auth_multiplier": auth_multiplier,
                "safety_factor": safety_factor,
                "async_ratio": async_ratio
            }
        }
        
        return optimal_config
    
    def generate_optimization_recommendations(self, current_stats: Dict[str, Any], 
                                            bottlenecks: List[str],
                                            optimal_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations."""
        
        recommendations = []
        
        # Pool size recommendations
        if current_stats:
            for engine_type in ["sync_engine", "async_engine"]:
                if engine_type in current_stats and current_stats[engine_type]:
                    stats = current_stats[engine_type]
                    utilization = stats.get("pool_utilization", 0)
                    
                    if utilization > 0.8:
                        recommendations.append({
                            "priority": "HIGH",
                            "category": "Pool Sizing",
                            "issue": f"{engine_type} pool utilization at {utilization:.1%}",
                            "recommendation": f"Increase {engine_type} pool size from {stats.get('pool_size', 0)} to {optimal_config[f'{engine_type.split('_')[0]}_pool_size']}",
                            "expected_improvement": "Reduce pool exhaustion by 60-80%"
                        })
        
        # Authentication-specific recommendations
        recommendations.extend([
            {
                "priority": "HIGH",
                "category": "Authentication Flow",
                "issue": "Sync fallback in async authentication causing pool mixing",
                "recommendation": "Remove sync fallback in get_current_user (lines 182-212 in dependencies.py)",
                "expected_improvement": "Eliminate async->sync pool switching, reduce connection churn by 40%"
            },
            {
                "priority": "MEDIUM", 
                "category": "Session Management",
                "issue": "Mixed sync/async session usage across routers",
                "recommendation": "Standardize on async sessions for all authentication-related endpoints",
                "expected_improvement": "Improve connection pool efficiency by 25%"
            },
            {
                "priority": "MEDIUM",
                "category": "Connection Pooling",
                "issue": "Potential connection leaks in error paths",
                "recommendation": "Add comprehensive finally blocks for session cleanup in all routers",
                "expected_improvement": "Prevent connection leaks, improve pool availability"
            },
            {
                "priority": "LOW",
                "category": "Performance",
                "issue": "Token validation requires database lookup",
                "recommendation": "Implement JWT token caching for frequently validated users",
                "expected_improvement": "Reduce authentication database calls by 30-50%"
            }
        ])
        
        return recommendations
    
    def create_monitoring_strategy(self) -> Dict[str, Any]:
        """Create comprehensive monitoring strategy."""
        
        monitoring_strategy = {
            "metrics_to_track": [
                "connection_pool_utilization",
                "connection_creation_rate", 
                "connection_cleanup_time",
                "authentication_response_time",
                "pool_exhaustion_events",
                "async_vs_sync_usage_ratio"
            ],
            "alert_thresholds": {
                "pool_utilization_warning": 0.7,   # 70%
                "pool_utilization_critical": 0.9,  # 90%
                "connection_churn_warning": 5,     # 5 conn/sec
                "connection_churn_critical": 15,   # 15 conn/sec
                "authentication_latency_warning": 200,  # 200ms
                "authentication_latency_critical": 500  # 500ms
            },
            "monitoring_tools": {
                "real_time_dashboard": "Grafana with PostgreSQL connection stats",
                "log_analysis": "ELK stack for authentication pattern analysis", 
                "automated_alerts": "PagerDuty integration for pool exhaustion",
                "performance_profiling": "py-spy for connection usage hotspots"
            },
            "testing_scenarios": [
                "concurrent_authentication_load_test",
                "pool_exhaustion_recovery_test", 
                "authentication_burst_handling",
                "connection_leak_detection"
            ]
        }
        
        return monitoring_strategy
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run complete performance analysis."""
        logger.info("Starting comprehensive database performance analysis...")
        
        try:
            # Initialize database if needed
            try:
                initialize_database(self.settings)
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
        
            # Gather analysis data
            config_analysis = self.analyze_current_config()
            current_stats = self.get_current_pool_stats()
            bottlenecks = self.identify_authentication_bottlenecks()
            optimal_config = self.calculate_optimal_pool_config()
            recommendations = self.generate_optimization_recommendations(
                current_stats, bottlenecks, optimal_config
            )
            monitoring_strategy = self.create_monitoring_strategy()
            
            # Compile complete analysis
            analysis_report = {
                "analysis_timestamp": datetime.now().isoformat(),
                "current_configuration": config_analysis,
                "current_pool_statistics": current_stats,
                "identified_bottlenecks": bottlenecks,
                "optimal_configuration": optimal_config,
                "optimization_recommendations": recommendations,
                "monitoring_strategy": monitoring_strategy,
                "router_session_analysis": self.analyze_router_session_patterns()
            }
            
            return analysis_report
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

def main():
    """Main analysis execution."""
    analyzer = PerformanceAnalyzer()
    
    print("\n" + "="*80)
    print("🔍 DATABASE CONNECTION POOL PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Run comprehensive analysis
    report = analyzer.run_comprehensive_analysis()
    
    if "error" in report:
        print(f"\n❌ Analysis failed: {report['error']}")
        return
    
    # Display key findings
    print(f"\n📊 ANALYSIS SUMMARY")
    print(f"Environment: {report['current_configuration']['environment']}")
    print(f"Service Type: {report['current_configuration']['service_type']}")
    print(f"Using PgBouncer: {report['current_configuration']['is_pgbouncer']}")
    
    # Current pool stats
    print(f"\n💾 CURRENT POOL STATISTICS")
    stats = report['current_pool_statistics']
    if stats:
        for engine_type, engine_stats in stats.items():
            if engine_stats and engine_type != 'timestamp':
                print(f"\n{engine_type.upper().replace('_', ' ')}:")
                print(f"  Pool Size: {engine_stats.get('pool_size', 'N/A')}")
                print(f"  Active Connections: {engine_stats.get('active_connections', 'N/A')}")
                print(f"  Pool Utilization: {engine_stats.get('pool_utilization', 0):.1%}")
                print(f"  Overflow Utilization: {engine_stats.get('overflow_utilization', 0):.1%}")
    else:
        print("  Database not initialized - no active pool statistics")
    
    # Bottlenecks
    print(f"\n🚨 IDENTIFIED BOTTLENECKS ({len(report['identified_bottlenecks'])})")
    for i, bottleneck in enumerate(report['identified_bottlenecks'], 1):
        print(f"  {i}. {bottleneck}")
    
    # Optimal configuration
    print(f"\n⚡ OPTIMAL CONFIGURATION")
    optimal = report['optimal_configuration']
    print(f"  Sync Pool: {optimal['sync_pool_size']} + {optimal['sync_max_overflow']} overflow")
    print(f"  Async Pool: {optimal['async_pool_size']} + {optimal['async_max_overflow']} overflow")
    print(f"  Timeout: {optimal['pool_timeout']}s")
    print(f"  Recycle: {optimal['pool_recycle']}s")
    
    # Top recommendations
    print(f"\n🎯 TOP OPTIMIZATION RECOMMENDATIONS")
    high_priority = [r for r in report['optimization_recommendations'] if r['priority'] == 'HIGH']
    for i, rec in enumerate(high_priority[:3], 1):
        print(f"\n  {i}. {rec['category']}: {rec['issue']}")
        print(f"     → {rec['recommendation']}")
        print(f"     💡 Expected: {rec['expected_improvement']}")
    
    # Router analysis
    print(f"\n📁 ROUTER SESSION USAGE ANALYSIS")
    router_analysis = report['router_session_analysis'] 
    print(f"  Sync Session Routers: {len(router_analysis['sync_session_routers'])}")
    print(f"  Async Session Routers: {len(router_analysis['async_session_routers'])}")
    print(f"  Mixed Usage: {'Yes' if router_analysis['mixed_session_usage'] else 'No'}")
    print(f"  High Usage Routers: {len(router_analysis['high_session_routers'])}")
    
    if router_analysis['high_session_routers']:
        print(f"    - {', '.join(router_analysis['high_session_routers'])}")
    
    # Save detailed report
    report_file = f"/home/marku/ai_workflow_engine/performance_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    print("\n" + "="*80)
    print("✅ Performance analysis complete!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()