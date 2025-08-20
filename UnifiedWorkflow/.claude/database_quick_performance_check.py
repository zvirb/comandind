#!/usr/bin/env python3
"""
Quick Database Performance Validation
Validates the database optimizations are working effectively
"""

import os
import time
import statistics
import subprocess
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def execute_postgres_command(sql_command: str) -> tuple:
    """Execute SQL command and return success status and output"""
    try:
        cmd = [
            'docker', 'exec', 'ai_workflow_engine-postgres-1',
            'psql', '-U', 'app_user', '-d', 'ai_workflow_db', '-c', sql_command
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout
        
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return False, str(e)

def test_query_performance():
    """Test query performance after optimizations"""
    logger.info("📊 Testing Query Performance...")
    
    query_times = []
    
    # Test basic user queries
    for i in range(10):
        start_time = time.perf_counter()
        
        success, output = execute_postgres_command("SELECT COUNT(*) FROM users WHERE is_active = true;")
        
        end_time = time.perf_counter()
        if success:
            query_times.append((end_time - start_time) * 1000)
        
        time.sleep(0.1)
    
    if query_times:
        avg_time = statistics.mean(query_times)
        min_time = min(query_times)
        max_time = max(query_times)
        
        print(f"   Query Performance Results:")
        print(f"   • Average Response Time: {avg_time:.2f}ms")
        print(f"   • Min/Max Response Time: {min_time:.2f}ms / {max_time:.2f}ms")
        print(f"   • Target Achievement: {'✅ ACHIEVED' if avg_time <= 100 else '❌ NEEDS IMPROVEMENT'}")
        
        return avg_time <= 100, avg_time
    
    return False, 0

def test_index_effectiveness():
    """Test that indexes are being used effectively"""
    logger.info("📇 Testing Index Effectiveness...")
    
    # Check that indexes exist and are being used
    index_check_sql = """
        SELECT 
            COUNT(*) as total_indexes,
            COUNT(*) FILTER (WHERE idx_scan > 0) as active_indexes
        FROM pg_stat_user_indexes 
        WHERE indexrelname LIKE 'idx_%';
    """
    
    success, output = execute_postgres_command(index_check_sql)
    
    if success and output:
        lines = output.strip().split('\n')
        data_line = None
        for line in lines:
            if '|' in line and not line.startswith('-'):
                data_line = line
                break
        
        if data_line:
            parts = [p.strip() for p in data_line.split('|')]
            if len(parts) >= 2:
                total_indexes = int(parts[0]) if parts[0].isdigit() else 0
                active_indexes = int(parts[1]) if parts[1].isdigit() else 0
                
                effectiveness = (active_indexes / total_indexes * 100) if total_indexes > 0 else 0
                
                print(f"   Index Effectiveness Results:")
                print(f"   • Total Custom Indexes: {total_indexes}")
                print(f"   • Active Indexes: {active_indexes}")
                print(f"   • Effectiveness: {effectiveness:.1f}%")
                print(f"   • Status: {'✅ GOOD' if effectiveness >= 60 else '⚠️ NEEDS IMPROVEMENT'}")
                
                return effectiveness >= 60, effectiveness
    
    print("   • Index check failed - unable to verify index usage")
    return False, 0

def test_connection_performance():
    """Test connection establishment performance"""
    logger.info("🔗 Testing Connection Performance...")
    
    connection_times = []
    
    for i in range(5):
        start_time = time.perf_counter()
        
        success, output = execute_postgres_command("SELECT 1;")
        
        end_time = time.perf_counter()
        if success:
            connection_times.append((end_time - start_time) * 1000)
        
        time.sleep(0.1)
    
    if connection_times:
        avg_time = statistics.mean(connection_times)
        
        efficiency = 95 if avg_time <= 50 else 85 if avg_time <= 100 else 75 if avg_time <= 200 else 60
        
        print(f"   Connection Performance Results:")
        print(f"   • Average Connection Time: {avg_time:.2f}ms")
        print(f"   • Efficiency Rating: {efficiency}%")
        print(f"   • Status: {'✅ EXCELLENT' if efficiency >= 85 else '⚠️ GOOD' if efficiency >= 75 else '❌ NEEDS IMPROVEMENT'}")
        
        return efficiency >= 75, efficiency
    
    return False, 0

def validate_configuration_changes():
    """Validate that configuration changes were applied"""
    logger.info("⚙️ Validating Configuration Changes...")
    
    config_checks = [
        ("work_mem", "16MB"),
        ("effective_cache_size", "6GB"),
        ("maintenance_work_mem", "128MB")
    ]
    
    validated_configs = 0
    total_configs = len(config_checks)
    
    for param, expected_value in config_checks:
        success, output = execute_postgres_command(f"SELECT current_setting('{param}');")
        
        if success and output:
            current_value = output.strip().split('\n')[-2].strip() if '\n' in output else output.strip()
            
            if expected_value in current_value or current_value in expected_value:
                validated_configs += 1
                print(f"   • {param}: ✅ {current_value}")
            else:
                print(f"   • {param}: ⚠️ {current_value} (expected {expected_value})")
        else:
            print(f"   • {param}: ❌ Failed to check")
    
    validation_rate = (validated_configs / total_configs * 100)
    print(f"   Configuration Validation: {validation_rate:.0f}% ({validated_configs}/{total_configs})")
    
    return validation_rate >= 60, validation_rate

def main():
    """Main performance validation function"""
    print("🔍 Database Performance Optimization Validation")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run all validation tests
    tests_passed = 0
    total_tests = 4
    
    test_results = {}
    
    # Test 1: Query Performance
    print("\n1. QUERY PERFORMANCE TEST:")
    query_success, query_avg = test_query_performance()
    if query_success:
        tests_passed += 1
    test_results['query_performance'] = {'success': query_success, 'avg_ms': query_avg}
    
    # Test 2: Index Effectiveness
    print("\n2. INDEX EFFECTIVENESS TEST:")
    index_success, index_effectiveness = test_index_effectiveness()
    if index_success:
        tests_passed += 1
    test_results['index_effectiveness'] = {'success': index_success, 'effectiveness': index_effectiveness}
    
    # Test 3: Connection Performance
    print("\n3. CONNECTION PERFORMANCE TEST:")
    conn_success, conn_efficiency = test_connection_performance()
    if conn_success:
        tests_passed += 1
    test_results['connection_performance'] = {'success': conn_success, 'efficiency': conn_efficiency}
    
    # Test 4: Configuration Validation
    print("\n4. CONFIGURATION VALIDATION TEST:")
    config_success, config_rate = validate_configuration_changes()
    if config_success:
        tests_passed += 1
    test_results['configuration_validation'] = {'success': config_success, 'validation_rate': config_rate}
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE OPTIMIZATION VALIDATION SUMMARY")
    print("=" * 60)
    
    success_rate = (tests_passed / total_tests * 100)
    
    print(f"\nTests Passed: {tests_passed}/{total_tests} ({success_rate:.0f}%)")
    print(f"Validation Duration: {(datetime.now() - start_time).total_seconds():.1f} seconds")
    
    # Detailed results
    if test_results.get('query_performance', {}).get('success'):
        avg_response = test_results['query_performance']['avg_ms']
        print(f"\n✅ Query Performance: {avg_response:.2f}ms (Target: <100ms)")
    else:
        print(f"\n❌ Query Performance: FAILED")
    
    if test_results.get('connection_performance', {}).get('success'):
        efficiency = test_results['connection_performance']['efficiency']
        print(f"✅ Connection Efficiency: {efficiency}% (Target: >75%)")
    else:
        print(f"❌ Connection Efficiency: FAILED")
    
    if test_results.get('index_effectiveness', {}).get('success'):
        effectiveness = test_results['index_effectiveness']['effectiveness']
        print(f"✅ Index Effectiveness: {effectiveness:.1f}% (Target: >60%)")
    else:
        print(f"❌ Index Effectiveness: FAILED")
    
    if test_results.get('configuration_validation', {}).get('success'):
        config_rate = test_results['configuration_validation']['validation_rate']
        print(f"✅ Configuration Applied: {config_rate:.0f}% (Target: >60%)")
    else:
        print(f"❌ Configuration Applied: FAILED")
    
    # Final assessment
    if success_rate >= 75:
        print(f"\n🎯 OVERALL STATUS: ✅ OPTIMIZATION SUCCESSFUL")
        print(f"   Database performance optimizations are working effectively!")
        return 0
    else:
        print(f"\n🎯 OVERALL STATUS: ⚠️ NEEDS ATTENTION")
        print(f"   Some optimizations may need additional tuning.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)