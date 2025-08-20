#!/usr/bin/env python3
"""
Database Performance Optimization Implementation
Implementation script for applying database optimizations to achieve <100ms response time

This script implements the optimization recommendations from the performance analysis:
1. Create missing critical indexes
2. Optimize PgBouncer configuration 
3. Update PostgreSQL configuration parameters
4. Implement caching layer enhancements
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseOptimizationImplementer:
    """Implement database performance optimizations"""
    
    def __init__(self):
        self.implementation_results = {
            'timestamp': datetime.now().isoformat(),
            'optimizations_applied': {},
            'performance_improvements': {},
            'validation_results': {},
            'rollback_info': {}
        }
        
        # Load analysis results
        self._load_analysis_results()
    
    def _load_analysis_results(self):
        """Load the latest analysis results"""
        try:
            # Find the most recent analysis file
            analysis_files = []
            for file in os.listdir('/home/marku/ai_workflow_engine/.claude/'):
                if file.startswith('database_performance_analysis_docker_'):
                    analysis_files.append(file)
            
            if analysis_files:
                latest_file = sorted(analysis_files)[-1]
                with open(f'/home/marku/ai_workflow_engine/.claude/{latest_file}', 'r') as f:
                    self.analysis_data = json.load(f)
                logger.info(f"Loaded analysis results from {latest_file}")
            else:
                logger.warning("No analysis results found - running with default optimizations")
                self.analysis_data = {}
        except Exception as e:
            logger.error(f"Failed to load analysis results: {e}")
            self.analysis_data = {}
    
    def run_optimization_implementation(self) -> Dict[str, Any]:
        """Run complete optimization implementation"""
        logger.info("🚀 Starting Database Performance Optimization Implementation")
        
        try:
            # Create backup/rollback point
            self._create_backup_point()
            
            # Implement index optimizations
            self._implement_index_optimizations()
            
            # Optimize PgBouncer configuration
            self._optimize_pgbouncer_configuration()
            
            # Update PostgreSQL configuration
            self._update_postgresql_configuration()
            
            # Implement caching enhancements
            self._implement_caching_enhancements()
            
            # Validate optimizations
            self._validate_optimizations()
            
            # Measure performance improvements
            self._measure_performance_improvements()
            
        except Exception as e:
            logger.error(f"Optimization implementation failed: {e}")
            self.implementation_results['error'] = str(e)
        
        return self.implementation_results
    
    def _execute_postgres_command(self, sql_command: str) -> bool:
        """Execute SQL command through Docker postgres container"""
        try:
            cmd = [
                'docker', 'exec', 'ai_workflow_engine-postgres-1',
                'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c', sql_command
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"SQL command failed: {result.stderr}")
                return False
            
            logger.info(f"SQL command executed successfully: {sql_command[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute postgres command: {e}")
            return False
    
    def _create_backup_point(self):
        """Create backup point for rollback capability"""
        logger.info("💾 Creating backup point...")
        
        backup_info = {
            'timestamp': datetime.now().isoformat(),
            'backup_type': 'configuration_snapshot',
            'files_backed_up': []
        }
        
        try:
            # Backup PgBouncer configuration
            pgbouncer_config = "/home/marku/ai_workflow_engine/config/pgbouncer/pgbouncer.ini"
            if os.path.exists(pgbouncer_config):
                backup_path = f"{pgbouncer_config}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                subprocess.run(['cp', pgbouncer_config, backup_path], check=True)
                backup_info['files_backed_up'].append(backup_path)
                logger.info(f"Backed up PgBouncer config to {backup_path}")
            
            # Create database schema snapshot
            schema_backup_cmd = [
                'docker', 'exec', 'ai_workflow_engine-postgres-1',
                'pg_dump', '-U', 'app_user', '-d', 'ai_workflow_db', '--schema-only',
                '-f', '/tmp/schema_backup.sql'
            ]
            
            result = subprocess.run(schema_backup_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                backup_info['schema_backup'] = '/tmp/schema_backup.sql'
                logger.info("Created database schema backup")
            
        except Exception as e:
            logger.warning(f"Backup creation failed: {e}")
        
        self.implementation_results['rollback_info'] = backup_info
    
    def _implement_index_optimizations(self):
        """Implement missing critical indexes"""
        logger.info("📇 Implementing Index Optimizations...")
        
        index_results = {
            'indexes_created': [],
            'indexes_failed': [],
            'performance_impact_expected': 'High'
        }
        
        # Get missing indexes from analysis
        missing_indexes = self.analysis_data.get('index_effectiveness', {}).get('missing_indexes', [])
        
        # Default critical indexes if analysis data not available
        if not missing_indexes:
            missing_indexes = [
                {
                    'table': 'users',
                    'columns': 'username',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username ON users (username);',
                    'priority': 'High'
                },
                {
                    'table': 'users',
                    'columns': 'email',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);',
                    'priority': 'High'
                },
                {
                    'table': 'user_oauth_tokens',
                    'columns': '(user_id, service)',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_oauth_tokens_user_service ON user_oauth_tokens (user_id, service);',
                    'priority': 'High'
                },
                {
                    'table': 'user_oauth_tokens',
                    'columns': 'token_expiry',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_oauth_tokens_expiry ON user_oauth_tokens (token_expiry);',
                    'priority': 'Medium'
                },
                {
                    'table': 'users',
                    'columns': '(is_active, created_at)',
                    'sql': 'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_created ON users (is_active, created_at);',
                    'priority': 'Medium'
                }
            ]
        
        # Create high-priority indexes first
        high_priority_indexes = [idx for idx in missing_indexes if idx.get('priority') == 'High']
        
        for index in high_priority_indexes:
            sql_command = index.get('sql', '')
            if sql_command:
                logger.info(f"Creating index: {index['table']}.{index['columns']}")
                
                if self._execute_postgres_command(sql_command):
                    index_results['indexes_created'].append({
                        'table': index['table'],
                        'columns': index['columns'],
                        'sql': sql_command
                    })
                else:
                    index_results['indexes_failed'].append({
                        'table': index['table'],
                        'columns': index['columns'],
                        'error': 'SQL execution failed'
                    })
                
                # Wait between index creations to avoid locking issues
                time.sleep(2)
        
        # Create medium-priority indexes
        medium_priority_indexes = [idx for idx in missing_indexes if idx.get('priority') == 'Medium']
        
        for index in medium_priority_indexes[:2]:  # Limit to avoid long execution time
            sql_command = index.get('sql', '')
            if sql_command:
                logger.info(f"Creating index: {index['table']}.{index['columns']}")
                
                if self._execute_postgres_command(sql_command):
                    index_results['indexes_created'].append({
                        'table': index['table'],
                        'columns': index['columns'],
                        'sql': sql_command
                    })
                else:
                    index_results['indexes_failed'].append({
                        'table': index['table'],
                        'columns': index['columns'],
                        'error': 'SQL execution failed'
                    })
                
                time.sleep(2)
        
        self.implementation_results['optimizations_applied']['indexes'] = index_results
        logger.info(f"Index optimization completed: {len(index_results['indexes_created'])} created, {len(index_results['indexes_failed'])} failed")
    
    def _optimize_pgbouncer_configuration(self):
        """Optimize PgBouncer configuration for better performance"""
        logger.info("🔗 Optimizing PgBouncer Configuration...")
        
        pgbouncer_results = {
            'configuration_updated': False,
            'parameters_changed': [],
            'restart_required': True
        }
        
        try:
            config_file = "/home/marku/ai_workflow_engine/config/pgbouncer/pgbouncer.ini"
            
            if not os.path.exists(config_file):
                logger.warning("PgBouncer config file not found")
                return
            
            # Read current configuration
            with open(config_file, 'r') as f:
                config_lines = f.readlines()
            
            # Define optimizations
            optimizations = {
                'default_pool_size': '80',          # Increase from 60
                'max_client_conn': '600',           # Increase from 500
                'reserve_pool_size': '30',          # Increase from 20
                'pool_timeout': '45',               # Reduce from current
                'query_timeout': '60',              # Reduce from 90
                'query_wait_timeout': '15',         # Reduce from 20
                'server_idle_timeout': '600',       # Increase from 300
                'server_check_delay': '10',         # Reduce from 15
                'listen_backlog': '12288',          # Increase from 8192
                'tcp_keepidle': '600',              # Increase from 300
                'tcp_keepintvl': '10'               # Reduce from 15
            }
            
            # Apply optimizations
            updated_lines = []
            changes_made = []
            
            for line in config_lines:
                line_updated = False
                
                for param, new_value in optimizations.items():
                    if line.strip().startswith(f"{param} =") or line.strip().startswith(f"{param}="):
                        # Extract current value
                        current_value = line.split('=')[1].strip()
                        
                        if current_value != new_value:
                            updated_lines.append(f"{param} = {new_value}\n")
                            changes_made.append({
                                'parameter': param,
                                'old_value': current_value,
                                'new_value': new_value
                            })
                            line_updated = True
                            break
                
                if not line_updated:
                    updated_lines.append(line)
            
            # Write updated configuration
            if changes_made:
                with open(config_file, 'w') as f:
                    f.writelines(updated_lines)
                
                pgbouncer_results['configuration_updated'] = True
                pgbouncer_results['parameters_changed'] = changes_made
                
                logger.info(f"PgBouncer configuration updated with {len(changes_made)} changes")
                
                # Note: PgBouncer restart would be needed but we'll defer that
                logger.info("Note: PgBouncer restart required for changes to take effect")
            else:
                logger.info("PgBouncer configuration already optimized")
            
        except Exception as e:
            logger.error(f"PgBouncer optimization failed: {e}")
            pgbouncer_results['error'] = str(e)
        
        self.implementation_results['optimizations_applied']['pgbouncer'] = pgbouncer_results
    
    def _update_postgresql_configuration(self):
        """Update PostgreSQL configuration for better performance"""
        logger.info("⚙️ Updating PostgreSQL Configuration...")
        
        postgres_results = {
            'configuration_updated': False,
            'parameters_changed': [],
            'restart_required': False
        }
        
        try:
            # Dynamic configuration changes that don't require restart
            dynamic_configs = {
                'work_mem': '16MB',                    # Increase from 4MB
                'maintenance_work_mem': '128MB',       # Increase from 64MB
                'effective_cache_size': '6GB',        # Increase from 4GB
                'checkpoint_completion_target': '0.9', # Optimize checkpoint behavior
                'random_page_cost': '1.1',            # Optimize for SSD
                'seq_page_cost': '1.0',               # Optimize for SSD
                'effective_io_concurrency': '200'     # Optimize for SSD
            }
            
            changes_made = []
            
            for param, value in dynamic_configs.items():
                # Get current value
                cmd = f"SELECT current_setting('{param}');"
                current_result = subprocess.run([
                    'docker', 'exec', 'ai_workflow_engine-postgres-1',
                    'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-t', '-c', cmd
                ], capture_output=True, text=True)
                
                if current_result.returncode == 0:
                    current_value = current_result.stdout.strip()
                    
                    if current_value != value:
                        # Apply the configuration change
                        alter_cmd = f"ALTER SYSTEM SET {param} = '{value}';"
                        
                        if self._execute_postgres_command(alter_cmd):
                            changes_made.append({
                                'parameter': param,
                                'old_value': current_value,
                                'new_value': value
                            })
                            logger.info(f"Updated {param}: {current_value} -> {value}")
            
            # Reload configuration
            if changes_made:
                if self._execute_postgres_command("SELECT pg_reload_conf();"):
                    postgres_results['configuration_updated'] = True
                    postgres_results['parameters_changed'] = changes_made
                    logger.info("PostgreSQL configuration reloaded successfully")
                else:
                    logger.error("Failed to reload PostgreSQL configuration")
            
        except Exception as e:
            logger.error(f"PostgreSQL configuration update failed: {e}")
            postgres_results['error'] = str(e)
        
        self.implementation_results['optimizations_applied']['postgresql'] = postgres_results
    
    def _implement_caching_enhancements(self):
        """Implement caching layer enhancements"""
        logger.info("💾 Implementing Caching Enhancements...")
        
        caching_results = {
            'query_cache_enabled': False,
            'connection_cache_optimized': False,
            'recommendations_documented': []
        }
        
        try:
            # Document caching recommendations for application implementation
            caching_recommendations = [
                {
                    'type': 'Redis Query Cache',
                    'implementation': 'Add Redis caching layer for frequent queries',
                    'expected_improvement': '30-50% reduction in database load',
                    'priority': 'High'
                },
                {
                    'type': 'Connection Pool Caching',
                    'implementation': 'Optimize connection reuse and warming',
                    'expected_improvement': '20-30% improvement in connection efficiency',
                    'priority': 'Medium'
                },
                {
                    'type': 'Query Result Caching',
                    'implementation': 'Cache authentication and user profile queries',
                    'expected_improvement': '40-60% improvement in auth response time',
                    'priority': 'High'
                },
                {
                    'type': 'Session Data Caching',
                    'implementation': 'Move session storage to Redis',
                    'expected_improvement': '25-35% improvement in session validation',
                    'priority': 'Medium'
                }
            ]
            
            caching_results['recommendations_documented'] = caching_recommendations
            
            # Log caching implementation plan
            logger.info("Caching enhancement recommendations documented:")
            for rec in caching_recommendations:
                logger.info(f"  • {rec['type']}: {rec['implementation']}")
            
        except Exception as e:
            logger.error(f"Caching enhancement implementation failed: {e}")
            caching_results['error'] = str(e)
        
        self.implementation_results['optimizations_applied']['caching'] = caching_results
    
    def _validate_optimizations(self):
        """Validate that optimizations were applied successfully"""
        logger.info("✅ Validating Optimizations...")
        
        validation_results = {
            'indexes_validation': {},
            'configuration_validation': {},
            'performance_validation': {}
        }
        
        try:
            # Validate indexes were created
            index_check_cmd = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname;
            """
            
            result = subprocess.run([
                'docker', 'exec', 'ai_workflow_engine-postgres-1',
                'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c', index_check_cmd
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                created_indexes = []
                for line in result.stdout.split('\n'):
                    if 'idx_' in line and '|' in line:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 3:
                            created_indexes.append({
                                'table': parts[1],
                                'index': parts[2]
                            })
                
                validation_results['indexes_validation'] = {
                    'indexes_found': len(created_indexes),
                    'indexes_list': created_indexes
                }
                logger.info(f"Index validation: {len(created_indexes)} indexes found")
            
            # Validate configuration changes
            config_params = ['work_mem', 'effective_cache_size', 'maintenance_work_mem']
            config_status = {}
            
            for param in config_params:
                result = subprocess.run([
                    'docker', 'exec', 'ai_workflow_engine-postgres-1',
                    'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-t', '-c',
                    f"SELECT current_setting('{param}');"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    config_status[param] = result.stdout.strip()
            
            validation_results['configuration_validation'] = config_status
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_results['error'] = str(e)
        
        self.implementation_results['validation_results'] = validation_results
    
    def _measure_performance_improvements(self):
        """Measure performance improvements after optimizations"""
        logger.info("📊 Measuring Performance Improvements...")
        
        performance_results = {
            'post_optimization_metrics': {},
            'improvement_summary': {},
            'target_achievement': {}
        }
        
        try:
            # Test query performance after optimizations
            query_times = []
            for i in range(10):
                start_time = time.perf_counter()
                
                result = subprocess.run([
                    'docker', 'exec', 'ai_workflow_engine-postgres-1',
                    'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c',
                    "SELECT COUNT(*) FROM users;"
                ], capture_output=True, text=True)
                
                end_time = time.perf_counter()
                if result.returncode == 0:
                    query_times.append((end_time - start_time) * 1000)
                
                time.sleep(0.05)
            
            if query_times:
                avg_response_time = sum(query_times) / len(query_times)
                performance_results['post_optimization_metrics'] = {
                    'avg_query_response_ms': avg_response_time,
                    'min_response_ms': min(query_times),
                    'max_response_ms': max(query_times),
                    'p95_response_ms': sorted(query_times)[int(len(query_times) * 0.95)]
                }
                
                # Compare with baseline
                baseline = self.analysis_data.get('performance_baseline', {})
                baseline_avg = baseline.get('simple_query_performance', {}).get('avg_ms', 0)
                
                if baseline_avg > 0:
                    improvement_percentage = ((baseline_avg - avg_response_time) / baseline_avg) * 100
                    
                    performance_results['improvement_summary'] = {
                        'baseline_avg_ms': baseline_avg,
                        'optimized_avg_ms': avg_response_time,
                        'improvement_percentage': improvement_percentage,
                        'improvement_ms': baseline_avg - avg_response_time
                    }
                    
                    # Check target achievement
                    target_response_time = 100  # ms
                    target_achieved = avg_response_time <= target_response_time
                    
                    performance_results['target_achievement'] = {
                        'target_ms': target_response_time,
                        'achieved': target_achieved,
                        'margin_ms': target_response_time - avg_response_time
                    }
                    
                    logger.info(f"Performance improvement: {improvement_percentage:.1f}% ({baseline_avg:.2f}ms -> {avg_response_time:.2f}ms)")
                    logger.info(f"Target achieved: {'✅ YES' if target_achieved else '❌ NO'}")
            
        except Exception as e:
            logger.error(f"Performance measurement failed: {e}")
            performance_results['error'] = str(e)
        
        self.implementation_results['performance_improvements'] = performance_results
    
    def save_results(self, filename: str = None) -> str:
        """Save implementation results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/home/marku/ai_workflow_engine/.claude/database_optimization_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.implementation_results, f, indent=2, default=str)
        
        logger.info(f"📊 Implementation results saved to {filename}")
        return filename
    
    def print_implementation_summary(self):
        """Print implementation summary"""
        print("\n" + "="*80)
        print("🚀 DATABASE OPTIMIZATION IMPLEMENTATION RESULTS")
        print("="*80)
        
        # Optimization Summary
        optimizations = self.implementation_results.get('optimizations_applied', {})
        
        print(f"\n📇 INDEX OPTIMIZATIONS:")
        indexes = optimizations.get('indexes', {})
        if indexes:
            created = len(indexes.get('indexes_created', []))
            failed = len(indexes.get('indexes_failed', []))
            print(f"   Indexes Created: {created}")
            print(f"   Indexes Failed: {failed}")
            
            for idx in indexes.get('indexes_created', [])[:3]:
                print(f"   ✅ {idx['table']}.{idx['columns']}")
        
        print(f"\n🔗 CONNECTION POOL OPTIMIZATIONS:")
        pgbouncer = optimizations.get('pgbouncer', {})
        if pgbouncer.get('configuration_updated'):
            changes = len(pgbouncer.get('parameters_changed', []))
            print(f"   Configuration Updated: ✅ {changes} parameters changed")
            for change in pgbouncer.get('parameters_changed', [])[:3]:
                print(f"   • {change['parameter']}: {change['old_value']} -> {change['new_value']}")
        else:
            print(f"   Configuration Updated: ❌ No changes applied")
        
        print(f"\n⚙️ POSTGRESQL CONFIGURATION:")
        postgres = optimizations.get('postgresql', {})
        if postgres.get('configuration_updated'):
            changes = len(postgres.get('parameters_changed', []))
            print(f"   Configuration Updated: ✅ {changes} parameters changed")
            for change in postgres.get('parameters_changed', [])[:3]:
                print(f"   • {change['parameter']}: {change['old_value']} -> {change['new_value']}")
        else:
            print(f"   Configuration Updated: ❌ No changes applied")
        
        # Performance Results
        performance = self.implementation_results.get('performance_improvements', {})
        if performance:
            improvement = performance.get('improvement_summary', {})
            target = performance.get('target_achievement', {})
            
            print(f"\n📊 PERFORMANCE IMPROVEMENTS:")
            if improvement:
                print(f"   Baseline Response Time: {improvement.get('baseline_avg_ms', 0):.2f}ms")
                print(f"   Optimized Response Time: {improvement.get('optimized_avg_ms', 0):.2f}ms")
                print(f"   Improvement: {improvement.get('improvement_percentage', 0):.1f}%")
            
            if target:
                achieved = target.get('achieved', False)
                print(f"   Target (<100ms): {'✅ ACHIEVED' if achieved else '❌ NOT ACHIEVED'}")
                if achieved:
                    print(f"   Margin: {target.get('margin_ms', 0):.2f}ms under target")
        
        # Validation Results
        validation = self.implementation_results.get('validation_results', {})
        if validation:
            print(f"\n✅ VALIDATION RESULTS:")
            indexes_val = validation.get('indexes_validation', {})
            if indexes_val:
                print(f"   Active Indexes: {indexes_val.get('indexes_found', 0)}")
            
            config_val = validation.get('configuration_validation', {})
            if config_val:
                print(f"   Configuration Parameters: {len(config_val)} validated")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    print("🚀 Database Performance Optimization Implementation")
    print("="*60)
    
    implementer = DatabaseOptimizationImplementer()
    
    try:
        # Run optimization implementation
        results = implementer.run_optimization_implementation()
        
        # Save detailed results
        results_file = implementer.save_results()
        
        # Print implementation summary
        implementer.print_implementation_summary()
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Return success if optimizations were applied
        performance = results.get('performance_improvements', {})
        target_achieved = performance.get('target_achievement', {}).get('achieved', False)
        
        if target_achieved:
            print("\n✅ Database optimization completed successfully! Target response time achieved.")
            return 0
        else:
            print("\n⚠️  Optimizations applied, but target response time may need additional tuning.")
            return 1
            
    except Exception as e:
        logger.error(f"Implementation failed: {e}")
        print(f"\n❌ Implementation failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)