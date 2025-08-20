#!/usr/bin/env python3
"""
Validate calendar sync monitoring setup and alert generation.

This script tests the monitoring system by simulating various scenarios and
verifying that metrics are collected and alerts are generated correctly.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.monitoring.calendar_sync_monitoring import (
    calendar_sync_monitor, start_calendar_sync_monitoring, finish_calendar_sync_monitoring,
    CalendarSyncStatus, ErrorPattern
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringValidator:
    """Validates calendar sync monitoring functionality."""
    
    def __init__(self):
        self.test_results = {}
        self.test_user_id = 9999  # Test user ID
        
    def simulate_successful_sync(self) -> bool:
        """Simulate a successful calendar sync operation."""
        try:
            logger.info("Simulating successful calendar sync...")
            
            sync_metrics = start_calendar_sync_monitoring(
                user_id=self.test_user_id,
                endpoint="/api/v1/calendar/sync/auto"
            )
            
            # Simulate processing time
            time.sleep(0.5)
            
            finish_calendar_sync_monitoring(
                sync_metrics,
                CalendarSyncStatus.SUCCESS,
                events_synced=25,
                retry_count=0
            )
            
            logger.info("✓ Successful sync simulation completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to simulate successful sync: {e}")
            return False
    
    def simulate_schema_error(self) -> bool:
        """Simulate a database schema error."""
        try:
            logger.info("Simulating database schema error...")
            
            sync_metrics = start_calendar_sync_monitoring(
                user_id=self.test_user_id,
                endpoint="/api/v1/calendar/sync/auto"
            )
            
            time.sleep(0.2)
            
            finish_calendar_sync_monitoring(
                sync_metrics,
                CalendarSyncStatus.SCHEMA_ERROR,
                error_message="psycopg2.errors.UndefinedColumn: column user_oauth_tokens.scope does not exist at character 366"
            )
            
            logger.info("✓ Schema error simulation completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to simulate schema error: {e}")
            return False
    
    def simulate_oauth_token_error(self) -> bool:
        """Simulate OAuth token scope error."""
        try:
            logger.info("Simulating OAuth token scope error...")
            
            sync_metrics = start_calendar_sync_monitoring(
                user_id=self.test_user_id,
                endpoint="/api/v1/calendar/sync/auto"
            )
            
            time.sleep(0.3)
            
            finish_calendar_sync_monitoring(
                sync_metrics,
                CalendarSyncStatus.SCHEMA_ERROR,
                error_message="SQLAlchemy column 'scope' missing from user_oauth_tokens table schema"
            )
            
            logger.info("✓ OAuth token error simulation completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to simulate OAuth token error: {e}")
            return False
    
    def simulate_circuit_breaker_trigger(self) -> bool:
        """Simulate multiple failures to trigger circuit breaker."""
        try:
            logger.info("Simulating circuit breaker trigger...")
            
            # Simulate 5 consecutive failures
            for i in range(5):
                sync_metrics = start_calendar_sync_monitoring(
                    user_id=self.test_user_id,
                    endpoint="/api/v1/calendar/sync/auto"
                )
                
                time.sleep(0.1)
                
                finish_calendar_sync_monitoring(
                    sync_metrics,
                    CalendarSyncStatus.FAILURE,
                    error_message=f"Network timeout error #{i+1}"
                )
            
            # Check circuit breaker state
            failure_count = calendar_sync_monitor.user_failure_counts.get(self.test_user_id, 0)
            if failure_count >= 3:
                logger.info(f"✓ Circuit breaker triggered after {failure_count} failures")
                return True
            else:
                logger.warning(f"Circuit breaker not triggered (failures: {failure_count})")
                return False
                
        except Exception as e:
            logger.error(f"✗ Failed to simulate circuit breaker: {e}")
            return False
    
    def simulate_performance_degradation(self) -> bool:
        """Simulate performance degradation."""
        try:
            logger.info("Simulating performance degradation...")
            
            sync_metrics = start_calendar_sync_monitoring(
                user_id=self.test_user_id,
                endpoint="/api/v1/calendar/sync/auto"
            )
            
            # Simulate long processing time
            time.sleep(2.0)
            
            finish_calendar_sync_monitoring(
                sync_metrics,
                CalendarSyncStatus.SUCCESS,
                events_synced=15,
                retry_count=2
            )
            
            logger.info("✓ Performance degradation simulation completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to simulate performance degradation: {e}")
            return False
    
    def validate_metrics_collection(self) -> Dict[str, Any]:
        """Validate that metrics are being collected correctly."""
        validation_results = {
            'prometheus_metrics': False,
            'error_pattern_detection': False,
            'circuit_breaker_tracking': False,
            'performance_tracking': False,
            'health_score_calculation': False
        }
        
        try:
            # Check Prometheus metrics
            if hasattr(calendar_sync_monitor, 'calendar_sync_requests_total'):
                validation_results['prometheus_metrics'] = True
                logger.info("✓ Prometheus metrics registry is available")
            
            # Check error pattern detection
            recent_errors = calendar_sync_monitor.get_recent_schema_errors(limit=10)
            if len(recent_errors) > 0:
                validation_results['error_pattern_detection'] = True
                logger.info(f"✓ Error pattern detection working ({len(recent_errors)} recent errors)")
            
            # Check circuit breaker tracking
            failure_count = calendar_sync_monitor.user_failure_counts.get(self.test_user_id, 0)
            if failure_count > 0:
                validation_results['circuit_breaker_tracking'] = True
                logger.info(f"✓ Circuit breaker tracking working (failures: {failure_count})")
            
            # Check performance tracking
            stats = calendar_sync_monitor.get_sync_statistics(user_id=self.test_user_id, hours=1)
            if stats['total_syncs'] > 0:
                validation_results['performance_tracking'] = True
                logger.info(f"✓ Performance tracking working ({stats['total_syncs']} syncs recorded)")
            
            # Check health score calculation
            health_score = calendar_sync_monitor._calculate_health_score(1)
            if 0 <= health_score <= 100:
                validation_results['health_score_calculation'] = True
                logger.info(f"✓ Health score calculation working (score: {health_score:.1f})")
            
        except Exception as e:
            logger.error(f"Metrics validation error: {e}")
        
        return validation_results
    
    def validate_alert_generation(self) -> Dict[str, Any]:
        """Validate alert generation functionality."""
        alert_results = {
            'schema_error_alerts': False,
            'circuit_breaker_alerts': False,
            'performance_alerts': False
        }
        
        try:
            # Test schema error alert
            sync_metrics = start_calendar_sync_monitoring(
                user_id=self.test_user_id,
                endpoint="/api/v1/calendar/sync/auto"
            )
            
            finish_calendar_sync_monitoring(
                sync_metrics,
                CalendarSyncStatus.SCHEMA_ERROR,
                error_message="column user_oauth_tokens.scope does not exist"
            )
            
            alerts = calendar_sync_monitor.should_trigger_alert(sync_metrics)
            if 'schema_error' in alerts:
                alert_results['schema_error_alerts'] = True
                logger.info("✓ Schema error alerts working")
            
            # Test circuit breaker alert
            if calendar_sync_monitor.user_failure_counts.get(self.test_user_id, 0) >= 3:
                # Simulate one more failure to trigger circuit breaker
                sync_metrics2 = start_calendar_sync_monitoring(
                    user_id=self.test_user_id,
                    endpoint="/api/v1/calendar/sync/auto"
                )
                
                finish_calendar_sync_monitoring(
                    sync_metrics2,
                    CalendarSyncStatus.FAILURE,
                    error_message="Test failure for circuit breaker"
                )
                
                alerts2 = calendar_sync_monitor.should_trigger_alert(sync_metrics2)
                if 'circuit_breaker' in alerts2:
                    alert_results['circuit_breaker_alerts'] = True
                    logger.info("✓ Circuit breaker alerts working")
            
            # Test performance alert (if baseline exists)
            if calendar_sync_monitor.baseline_duration:
                sync_metrics3 = start_calendar_sync_monitoring(
                    user_id=self.test_user_id,
                    endpoint="/api/v1/calendar/sync/auto"
                )
                
                # Manually set duration to trigger performance alert
                sync_metrics3.duration = calendar_sync_monitor.baseline_duration * 4
                sync_metrics3.status = CalendarSyncStatus.SUCCESS
                
                alerts3 = calendar_sync_monitor.should_trigger_alert(sync_metrics3)
                if 'performance_degradation' in alerts3:
                    alert_results['performance_alerts'] = True
                    logger.info("✓ Performance alerts working")
        
        except Exception as e:
            logger.error(f"Alert validation error: {e}")
        
        return alert_results
    
    def validate_error_classification(self) -> Dict[str, bool]:
        """Validate error classification functionality."""
        test_cases = {
            "column user_oauth_tokens.scope does not exist": ErrorPattern.OAUTH_TOKEN_SCOPE,
            "psycopg2.errors.UndefinedColumn: column test does not exist": ErrorPattern.UNDEFINED_COLUMN,
            "NameError: name 'undefined_variable' is not defined": ErrorPattern.NAME_ERROR,
            "sqlalchemy.exc.ProgrammingError": ErrorPattern.DATABASE_SCHEMA,
            "401 Unauthorized: Token expired": ErrorPattern.AUTHENTICATION_FAILURE,
            "Connection timeout": ErrorPattern.NETWORK_TIMEOUT,
            "Rate limit exceeded": ErrorPattern.RATE_LIMIT,
            "Unknown random error": ErrorPattern.UNKNOWN
        }
        
        results = {}
        
        for error_message, expected_pattern in test_cases.items():
            detected_pattern = calendar_sync_monitor.classify_error_pattern(error_message)
            results[error_message] = detected_pattern == expected_pattern
            
            if detected_pattern == expected_pattern:
                logger.info(f"✓ Correctly classified: '{error_message}' -> {expected_pattern.value}")
            else:
                logger.error(f"✗ Misclassified: '{error_message}' -> {detected_pattern.value} (expected {expected_pattern.value})")
        
        return results
    
    def cleanup_test_data(self):
        """Clean up test data."""
        try:
            # Remove test user from failure counts
            calendar_sync_monitor.user_failure_counts.pop(self.test_user_id, None)
            
            # Remove test sync data from history
            calendar_sync_monitor.sync_history = type(calendar_sync_monitor.sync_history)(
                [sync for sync in calendar_sync_monitor.sync_history 
                 if sync.user_id != self.test_user_id],
                maxlen=calendar_sync_monitor.sync_history.maxlen
            )
            
            logger.info("✓ Test data cleaned up")
            
        except Exception as e:
            logger.warning(f"Failed to clean up test data: {e}")
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive monitoring validation."""
        logger.info("Starting comprehensive calendar sync monitoring validation...")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'test_results': {},
            'overall_status': 'unknown'
        }
        
        try:
            # Test simulations
            logger.info("\n1. Testing sync simulations...")
            results['test_results']['successful_sync'] = self.simulate_successful_sync()
            results['test_results']['schema_error'] = self.simulate_schema_error()
            results['test_results']['oauth_error'] = self.simulate_oauth_token_error()
            results['test_results']['circuit_breaker'] = self.simulate_circuit_breaker_trigger()
            results['test_results']['performance_degradation'] = self.simulate_performance_degradation()
            
            # Validate metrics collection
            logger.info("\n2. Validating metrics collection...")
            metrics_validation = self.validate_metrics_collection()
            results['test_results']['metrics_collection'] = metrics_validation
            
            # Validate alert generation
            logger.info("\n3. Validating alert generation...")
            alert_validation = self.validate_alert_generation()
            results['test_results']['alert_generation'] = alert_validation
            
            # Validate error classification
            logger.info("\n4. Validating error classification...")
            classification_results = self.validate_error_classification()
            results['test_results']['error_classification'] = classification_results
            
            # Determine overall status
            all_tests_passed = (
                all(results['test_results'][key] if isinstance(results['test_results'][key], bool) 
                   else all(results['test_results'][key].values()) 
                   for key in ['successful_sync', 'schema_error', 'oauth_error', 'circuit_breaker', 'performance_degradation']) and
                all(metrics_validation.values()) and
                all(alert_validation.values()) and
                all(classification_results.values())
            )
            
            results['overall_status'] = 'passed' if all_tests_passed else 'failed'
            
            # Clean up
            self.cleanup_test_data()
            
            return results
            
        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            results['overall_status'] = 'error'
            results['error'] = str(e)
            return results


def print_validation_report(results: Dict[str, Any]):
    """Print a formatted validation report."""
    print("\n" + "="*70)
    print("CALENDAR SYNC MONITORING VALIDATION REPORT")
    print("="*70)
    print(f"Validation Time: {results['timestamp']}")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print()
    
    # Print test results
    test_results = results['test_results']
    
    print("SYNC SIMULATION TESTS:")
    for test_name in ['successful_sync', 'schema_error', 'oauth_error', 'circuit_breaker', 'performance_degradation']:
        status = "✓ PASS" if test_results.get(test_name, False) else "✗ FAIL"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print("\nMETRICS COLLECTION TESTS:")
    if 'metrics_collection' in test_results:
        for metric, passed in test_results['metrics_collection'].items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {metric.replace('_', ' ').title()}: {status}")
    
    print("\nALERT GENERATION TESTS:")
    if 'alert_generation' in test_results:
        for alert, passed in test_results['alert_generation'].items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {alert.replace('_', ' ').title()}: {status}")
    
    print("\nERROR CLASSIFICATION TESTS:")
    if 'error_classification' in test_results:
        passed_count = sum(test_results['error_classification'].values())
        total_count = len(test_results['error_classification'])
        print(f"  Classification Accuracy: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")
    
    if results['overall_status'] == 'passed':
        print("\n✓ ALL TESTS PASSED - Calendar sync monitoring is working correctly")
    elif results['overall_status'] == 'failed':
        print("\n✗ SOME TESTS FAILED - Review failed tests and fix issues")
    else:
        print("\n⚠ VALIDATION ERROR - Check logs for details")
    
    print("="*70)


async def main():
    """Main validation function."""
    validator = MonitoringValidator()
    
    try:
        results = validator.run_comprehensive_validation()
        print_validation_report(results)
        
        return 0 if results['overall_status'] == 'passed' else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)