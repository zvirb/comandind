#!/usr/bin/env python3
"""
Database Performance Monitoring Dashboard
Real-time monitoring and validation of database optimizations

This script provides ongoing monitoring to validate that:
1. Database response times remain under 100ms target
2. Connection pool efficiency stays above 85%
3. Index utilization is optimal
4. Cache hit ratios are maintaining good performance
"""

import os
import sys
import json
import time
import statistics
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabasePerformanceMonitor:
    """Real-time database performance monitoring"""
    
    def __init__(self):
        self.monitoring_data = {
            'monitoring_start': datetime.now().isoformat(),
            'target_metrics': {
                'response_time_target_ms': 100,
                'connection_pool_efficiency_target': 85,
                'cache_hit_ratio_target': 95,
                'index_scan_ratio_target': 80
            },
            'real_time_metrics': [],
            'performance_alerts': [],
            'optimization_status': {}
        }
    
    def run_continuous_monitoring(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Run continuous performance monitoring"""
        logger.info(f"🔍 Starting {duration_minutes}-minute Database Performance Monitoring")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        measurement_count = 0
        
        try:
            while datetime.now() < end_time:
                # Collect performance metrics
                metrics = self._collect_performance_metrics()
                
                if metrics:
                    metrics['timestamp'] = datetime.now().isoformat()
                    metrics['measurement_id'] = measurement_count
                    self.monitoring_data['real_time_metrics'].append(metrics)
                    
                    # Check for performance alerts
                    self._check_performance_alerts(metrics)
                    
                    # Print real-time status
                    self._print_real_time_status(metrics)
                    
                    measurement_count += 1
                
                # Wait before next measurement
                time.sleep(30)  # Measure every 30 seconds
            
            # Generate monitoring summary
            self._generate_monitoring_summary()
            
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            self.monitoring_data['error'] = str(e)
        
        return self.monitoring_data
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect current performance metrics"""
        metrics = {}
        
        try:
            # Test query response times
            query_times = []
            for i in range(5):
                start_time = time.perf_counter()
                
                result = subprocess.run([
                    'docker', 'exec', 'ai_workflow_engine-postgres-1',
                    'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c',
                    "SELECT COUNT(*) FROM users WHERE is_active = true;"
                ], capture_output=True, text=True)
                
                end_time = time.perf_counter()
                if result.returncode == 0:
                    query_times.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            if query_times:
                metrics['query_performance'] = {
                    'avg_response_ms': statistics.mean(query_times),
                    'min_response_ms': min(query_times),
                    'max_response_ms': max(query_times),
                    'p95_response_ms': sorted(query_times)[int(len(query_times) * 0.95)] if len(query_times) > 1 else query_times[0]
                }
            
            # Test connection pool performance
            connection_times = []
            for i in range(3):
                start_time = time.perf_counter()
                
                result = subprocess.run([
                    'docker', 'exec', 'ai_workflow_engine-postgres-1',
                    'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c',
                    "SELECT 1;"
                ], capture_output=True, text=True)
                
                end_time = time.perf_counter()
                if result.returncode == 0:
                    connection_times.append((end_time - start_time) * 1000)
                
                time.sleep(0.1)
            
            if connection_times:
                avg_connection_time = statistics.mean(connection_times)
                efficiency_rating = self._calculate_connection_efficiency(avg_connection_time)
                
                metrics['connection_performance'] = {
                    'avg_connection_ms': avg_connection_time,
                    'efficiency_percentage': efficiency_rating
                }
            
            # Get database statistics
            db_stats = self._get_database_statistics()
            if db_stats:
                metrics['database_statistics'] = db_stats
            
            # Get index usage statistics
            index_stats = self._get_index_usage_statistics()
            if index_stats:
                metrics['index_performance'] = index_stats
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            metrics['collection_error'] = str(e)
        
        return metrics
    
    def _calculate_connection_efficiency(self, avg_time_ms: float) -> float:
        """Calculate connection efficiency percentage"""
        if avg_time_ms <= 20:
            return 95.0
        elif avg_time_ms <= 50:
            return 90.0
        elif avg_time_ms <= 100:
            return 85.0
        elif avg_time_ms <= 200:
            return 75.0
        else:
            return max(50.0, 100.0 - (avg_time_ms / 10))
    
    def _get_database_statistics(self) -> Dict[str, Any]:
        """Get current database performance statistics"""
        try:
            # Get cache hit ratios
            result = subprocess.run([
                'docker', 'exec', 'ai_workflow_engine-postgres-1',
                'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-t', '-c',
                """
                SELECT 
                    ROUND((sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0)) * 100, 2) as table_hit_ratio,
                    ROUND((sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0)) * 100, 2) as index_hit_ratio
                FROM pg_statio_user_tables;
                """
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 2:
                    table_hit_ratio = float(parts[0].strip()) if parts[0].strip() else 0
                    index_hit_ratio = float(parts[1].strip()) if parts[1].strip() else 0
                    
                    return {
                        'table_cache_hit_ratio': table_hit_ratio,
                        'index_cache_hit_ratio': index_hit_ratio,
                        'overall_cache_performance': (table_hit_ratio + index_hit_ratio) / 2
                    }
            
        except Exception as e:
            logger.warning(f"Failed to get database statistics: {e}")
        
        return {}
    
    def _get_index_usage_statistics(self) -> Dict[str, Any]:
        """Get current index usage statistics"""
        try:
            result = subprocess.run([
                'docker', 'exec', 'ai_workflow_engine-postgres-1',
                'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-t', '-c',
                """
                SELECT 
                    COUNT(*) as total_indexes,
                    COUNT(*) FILTER (WHERE idx_scan > 0) as active_indexes,
                    SUM(idx_scan) as total_scans
                FROM pg_stat_user_indexes;
                """
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|')
                if len(parts) >= 3:
                    total_indexes = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
                    active_indexes = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                    total_scans = int(parts[2].strip()) if parts[2].strip().isdigit() else 0
                    
                    index_efficiency = (active_indexes / total_indexes * 100) if total_indexes > 0 else 0
                    
                    return {
                        'total_indexes': total_indexes,
                        'active_indexes': active_indexes,
                        'total_scans': total_scans,
                        'index_efficiency_percentage': index_efficiency
                    }
            
        except Exception as e:
            logger.warning(f"Failed to get index statistics: {e}")
        
        return {}
    
    def _check_performance_alerts(self, metrics: Dict[str, Any]):
        """Check for performance alerts based on metrics"""
        alerts = []
        
        # Check query response time
        query_perf = metrics.get('query_performance', {})
        avg_response = query_perf.get('avg_response_ms', 0)
        
        if avg_response > self.monitoring_data['target_metrics']['response_time_target_ms']:
            alerts.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'RESPONSE_TIME_ALERT',
                'severity': 'HIGH',
                'message': f"Query response time {avg_response:.2f}ms exceeds target {self.monitoring_data['target_metrics']['response_time_target_ms']}ms",
                'current_value': avg_response,
                'target_value': self.monitoring_data['target_metrics']['response_time_target_ms']
            })
        
        # Check connection pool efficiency
        conn_perf = metrics.get('connection_performance', {})
        efficiency = conn_perf.get('efficiency_percentage', 0)
        
        if efficiency < self.monitoring_data['target_metrics']['connection_pool_efficiency_target']:
            alerts.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'CONNECTION_EFFICIENCY_ALERT',
                'severity': 'MEDIUM',
                'message': f"Connection pool efficiency {efficiency:.1f}% below target {self.monitoring_data['target_metrics']['connection_pool_efficiency_target']}%",
                'current_value': efficiency,
                'target_value': self.monitoring_data['target_metrics']['connection_pool_efficiency_target']
            })
        
        # Check cache hit ratios
        db_stats = metrics.get('database_statistics', {})
        cache_performance = db_stats.get('overall_cache_performance', 0)
        
        if cache_performance > 0 and cache_performance < self.monitoring_data['target_metrics']['cache_hit_ratio_target']:
            alerts.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'CACHE_HIT_RATIO_ALERT',
                'severity': 'MEDIUM',
                'message': f"Cache hit ratio {cache_performance:.1f}% below target {self.monitoring_data['target_metrics']['cache_hit_ratio_target']}%",
                'current_value': cache_performance,
                'target_value': self.monitoring_data['target_metrics']['cache_hit_ratio_target']
            })
        
        # Check index efficiency
        index_perf = metrics.get('index_performance', {})
        index_efficiency = index_perf.get('index_efficiency_percentage', 0)
        
        if index_efficiency > 0 and index_efficiency < self.monitoring_data['target_metrics']['index_scan_ratio_target']:
            alerts.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'INDEX_EFFICIENCY_ALERT',
                'severity': 'LOW',
                'message': f"Index efficiency {index_efficiency:.1f}% below target {self.monitoring_data['target_metrics']['index_scan_ratio_target']}%",
                'current_value': index_efficiency,
                'target_value': self.monitoring_data['target_metrics']['index_scan_ratio_target']
            })\n        \n        # Add new alerts to monitoring data\n        if alerts:\n            self.monitoring_data['performance_alerts'].extend(alerts)\n    \n    def _print_real_time_status(self, metrics: Dict[str, Any]):\n        \"\"\"Print real-time performance status\"\"\"\n        timestamp = datetime.now().strftime(\"%H:%M:%S\")\n        \n        query_perf = metrics.get('query_performance', {})\n        avg_response = query_perf.get('avg_response_ms', 0)\n        \n        conn_perf = metrics.get('connection_performance', {})\n        conn_efficiency = conn_perf.get('efficiency_percentage', 0)\n        \n        db_stats = metrics.get('database_statistics', {})\n        cache_perf = db_stats.get('overall_cache_performance', 0)\n        \n        index_perf = metrics.get('index_performance', {})\n        index_efficiency = index_perf.get('index_efficiency_percentage', 0)\n        \n        # Status indicators\n        response_status = \"✅\" if avg_response <= 100 else \"⚠️\" if avg_response <= 150 else \"❌\"\n        conn_status = \"✅\" if conn_efficiency >= 85 else \"⚠️\" if conn_efficiency >= 75 else \"❌\"\n        cache_status = \"✅\" if cache_perf >= 90 else \"⚠️\" if cache_perf >= 80 else \"❌\" if cache_perf > 0 else \"📊\"\n        index_status = \"✅\" if index_efficiency >= 80 else \"⚠️\" if index_efficiency >= 60 else \"❌\" if index_efficiency > 0 else \"📊\"\n        \n        print(f\"\\r[{timestamp}] Response: {response_status} {avg_response:.1f}ms | \"\n              f\"Pool: {conn_status} {conn_efficiency:.1f}% | \"\n              f\"Cache: {cache_status} {cache_perf:.1f}% | \"\n              f\"Index: {index_status} {index_efficiency:.1f}%\", end=\"\", flush=True)\n    \n    def _generate_monitoring_summary(self):\n        \"\"\"Generate monitoring session summary\"\"\"\n        logger.info(\"\\n📊 Generating monitoring summary...\")\n        \n        metrics = self.monitoring_data['real_time_metrics']\n        if not metrics:\n            return\n        \n        # Calculate summary statistics\n        response_times = [m.get('query_performance', {}).get('avg_response_ms', 0) for m in metrics if m.get('query_performance')]\n        connection_efficiencies = [m.get('connection_performance', {}).get('efficiency_percentage', 0) for m in metrics if m.get('connection_performance')]\n        cache_performances = [m.get('database_statistics', {}).get('overall_cache_performance', 0) for m in metrics if m.get('database_statistics', {}).get('overall_cache_performance', 0) > 0]\n        \n        summary = {\n            'monitoring_duration_minutes': len(metrics) * 0.5,  # 30-second intervals\n            'total_measurements': len(metrics),\n            'response_time_summary': {},\n            'connection_efficiency_summary': {},\n            'cache_performance_summary': {},\n            'performance_target_achievement': {},\n            'total_alerts': len(self.monitoring_data['performance_alerts'])\n        }\n        \n        if response_times:\n            summary['response_time_summary'] = {\n                'avg_ms': statistics.mean(response_times),\n                'min_ms': min(response_times),\n                'max_ms': max(response_times),\n                'median_ms': statistics.median(response_times),\n                'target_achievement_rate': len([rt for rt in response_times if rt <= 100]) / len(response_times) * 100\n            }\n        \n        if connection_efficiencies:\n            summary['connection_efficiency_summary'] = {\n                'avg_percentage': statistics.mean(connection_efficiencies),\n                'min_percentage': min(connection_efficiencies),\n                'max_percentage': max(connection_efficiencies),\n                'target_achievement_rate': len([ce for ce in connection_efficiencies if ce >= 85]) / len(connection_efficiencies) * 100\n            }\n        \n        if cache_performances:\n            summary['cache_performance_summary'] = {\n                'avg_percentage': statistics.mean(cache_performances),\n                'min_percentage': min(cache_performances),\n                'max_percentage': max(cache_performances)\n            }\n        \n        # Overall target achievement\n        response_target_met = summary.get('response_time_summary', {}).get('target_achievement_rate', 0) >= 90\n        efficiency_target_met = summary.get('connection_efficiency_summary', {}).get('target_achievement_rate', 0) >= 90\n        \n        summary['performance_target_achievement'] = {\n            'response_time_target_met': response_target_met,\n            'connection_efficiency_target_met': efficiency_target_met,\n            'overall_performance_acceptable': response_target_met and efficiency_target_met\n        }\n        \n        self.monitoring_data['optimization_status'] = summary\n    \n    def save_monitoring_results(self, filename: str = None) -> str:\n        \"\"\"Save monitoring results to file\"\"\"\n        if not filename:\n            timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")\n            filename = f\"/home/marku/ai_workflow_engine/.claude/database_performance_monitoring_{timestamp}.json\"\n        \n        with open(filename, 'w') as f:\n            json.dump(self.monitoring_data, f, indent=2, default=str)\n        \n        logger.info(f\"📊 Monitoring results saved to {filename}\")\n        return filename\n    \n    def print_monitoring_summary(self):\n        \"\"\"Print monitoring session summary\"\"\"\n        print(\"\\n\" + \"=\"*80)\n        print(\"📊 DATABASE PERFORMANCE MONITORING SUMMARY\")\n        print(\"=\"*80)\n        \n        summary = self.monitoring_data.get('optimization_status', {})\n        \n        # Monitoring session info\n        duration = summary.get('monitoring_duration_minutes', 0)\n        measurements = summary.get('total_measurements', 0)\n        alerts = summary.get('total_alerts', 0)\n        \n        print(f\"\\n📋 MONITORING SESSION:\")\n        print(f\"   Duration: {duration:.1f} minutes\")\n        print(f\"   Measurements: {measurements}\")\n        print(f\"   Total Alerts: {alerts}\")\n        \n        # Response time performance\n        response_summary = summary.get('response_time_summary', {})\n        if response_summary:\n            avg_response = response_summary.get('avg_ms', 0)\n            achievement_rate = response_summary.get('target_achievement_rate', 0)\n            \n            print(f\"\\n🚀 QUERY RESPONSE PERFORMANCE:\")\n            print(f\"   Average Response Time: {avg_response:.2f}ms\")\n            print(f\"   Target Achievement Rate: {achievement_rate:.1f}%\")\n            print(f\"   Min/Max Response: {response_summary.get('min_ms', 0):.1f}ms / {response_summary.get('max_ms', 0):.1f}ms\")\n            print(f\"   Target Status: {'✅ ACHIEVED' if achievement_rate >= 90 else '⚠️ NEEDS ATTENTION'}\")\n        \n        # Connection efficiency\n        efficiency_summary = summary.get('connection_efficiency_summary', {})\n        if efficiency_summary:\n            avg_efficiency = efficiency_summary.get('avg_percentage', 0)\n            efficiency_achievement = efficiency_summary.get('target_achievement_rate', 0)\n            \n            print(f\"\\n🔗 CONNECTION POOL EFFICIENCY:\")\n            print(f\"   Average Efficiency: {avg_efficiency:.1f}%\")\n            print(f\"   Target Achievement Rate: {efficiency_achievement:.1f}%\")\n            print(f\"   Efficiency Status: {'✅ EXCELLENT' if efficiency_achievement >= 90 else '⚠️ GOOD' if efficiency_achievement >= 70 else '❌ NEEDS IMPROVEMENT'}\")\n        \n        # Cache performance\n        cache_summary = summary.get('cache_performance_summary', {})\n        if cache_summary:\n            avg_cache = cache_summary.get('avg_percentage', 0)\n            \n            print(f\"\\n💾 CACHE PERFORMANCE:\")\n            print(f\"   Average Cache Hit Ratio: {avg_cache:.1f}%\")\n            print(f\"   Cache Status: {'✅ EXCELLENT' if avg_cache >= 95 else '⚠️ GOOD' if avg_cache >= 85 else '❌ NEEDS IMPROVEMENT'}\")\n        \n        # Overall status\n        achievement = summary.get('performance_target_achievement', {})\n        overall_acceptable = achievement.get('overall_performance_acceptable', False)\n        \n        print(f\"\\n🎯 OVERALL OPTIMIZATION STATUS:\")\n        print(f\"   Response Time Target: {'✅ MET' if achievement.get('response_time_target_met', False) else '❌ NOT MET'}\")\n        print(f\"   Connection Efficiency Target: {'✅ MET' if achievement.get('connection_efficiency_target_met', False) else '❌ NOT MET'}\")\n        print(f\"   Overall Performance: {'✅ ACCEPTABLE' if overall_acceptable else '⚠️ NEEDS MONITORING'}\")\n        \n        # Recent alerts\n        recent_alerts = self.monitoring_data.get('performance_alerts', [])[-3:]  # Last 3 alerts\n        if recent_alerts:\n            print(f\"\\n⚠️ RECENT PERFORMANCE ALERTS:\")\n            for alert in recent_alerts:\n                severity_icon = \"🔴\" if alert['severity'] == 'HIGH' else \"🟡\" if alert['severity'] == 'MEDIUM' else \"🔵\"\n                print(f\"   {severity_icon} {alert['type']}: {alert['message']}\")\n        \n        print(\"\\n\" + \"=\"*80)\n\n\ndef main():\n    \"\"\"Main execution function\"\"\"\n    print(\"📊 Database Performance Monitoring Dashboard\")\n    print(\"=\"*60)\n    \n    monitor = DatabasePerformanceMonitor()\n    \n    try:\n        # Run monitoring session\n        results = monitor.run_continuous_monitoring(duration_minutes=3)  # 3-minute monitoring session\n        \n        # Save detailed results\n        results_file = monitor.save_monitoring_results()\n        \n        # Print monitoring summary\n        monitor.print_monitoring_summary()\n        \n        print(f\"\\n📄 Detailed monitoring data saved to: {results_file}\")\n        \n        # Return success if performance targets are met\n        summary = results.get('optimization_status', {})\n        achievement = summary.get('performance_target_achievement', {})\n        \n        if achievement.get('overall_performance_acceptable', False):\n            print(\"\\n✅ Database performance monitoring: All targets achieved!\")\n            return 0\n        else:\n            print(\"\\n⚠️  Database performance monitoring: Some targets need attention.\")\n            return 1\n            \n    except Exception as e:\n        logger.error(f\"Monitoring failed: {e}\")\n        print(f\"\\n❌ Monitoring failed: {e}\")\n        return 2\n\n\nif __name__ == \"__main__\":\n    exit_code = main()\n    exit(exit_code)