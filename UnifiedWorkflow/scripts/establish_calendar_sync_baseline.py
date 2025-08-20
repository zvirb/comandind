#!/usr/bin/env python3
"""
Establish baseline performance metrics for calendar sync operations.

This script analyzes historical data and sets performance baselines that will be used
for alerting and performance regression detection.
"""

import asyncio
import logging
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.monitoring.calendar_sync_monitoring import calendar_sync_monitor, CalendarSyncStatus
from shared.monitoring.prometheus_metrics import metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaselineEstablisher:
    """Establishes performance baselines for calendar sync operations."""
    
    def __init__(self):
        self.baseline_data = {}
        self.analysis_results = {}
    
    def analyze_historical_performance(self, hours_back: int = 168) -> Dict[str, Any]:
        """Analyze historical performance data to establish baselines."""
        
        # Get historical sync data
        stats = calendar_sync_monitor.get_sync_statistics(hours=hours_back)
        
        if stats['total_syncs'] == 0:
            logger.warning("No historical sync data available for baseline establishment")
            return {
                'baseline_established': False,
                'reason': 'no_historical_data'
            }
        
        # Calculate baselines
        baselines = {
            'success_rate_baseline': self._calculate_success_rate_baseline(stats),
            'duration_baseline': self._calculate_duration_baseline(stats),
            'error_rate_baseline': self._calculate_error_rate_baseline(stats),
            'events_per_sync_baseline': self._calculate_events_baseline(stats)
        }
        
        # Set confidence levels
        baselines['confidence_level'] = self._calculate_confidence_level(stats)
        baselines['data_points'] = stats['total_syncs']
        baselines['analysis_period_hours'] = hours_back
        baselines['established_at'] = datetime.utcnow().isoformat()
        
        self.baseline_data = baselines
        
        logger.info(f"Baselines established from {stats['total_syncs']} data points over {hours_back} hours")
        logger.info(f"Success rate baseline: {baselines['success_rate_baseline']:.2%}")
        logger.info(f"Duration baseline: {baselines['duration_baseline']:.2f}s")
        
        return {
            'baseline_established': True,
            'baselines': baselines,
            'analysis_summary': self._generate_analysis_summary(stats, baselines)
        }
    
    def _calculate_success_rate_baseline(self, stats: Dict[str, Any]) -> float:
        """Calculate success rate baseline (expected normal success rate)."""
        current_success_rate = stats.get('success_rate', 0.0)
        
        # For alerting, we want to trigger when success rate drops significantly below normal
        # Use 95th percentile of success rate as baseline, but cap at reasonable values
        baseline = max(0.85, min(0.98, current_success_rate * 0.95))
        
        return baseline
    
    def _calculate_duration_baseline(self, stats: Dict[str, Any]) -> float:
        """Calculate duration baseline (95th percentile of successful operations)."""
        avg_duration = stats.get('avg_duration', 5.0)
        baseline_duration = stats.get('baseline_duration')
        
        if baseline_duration and baseline_duration > 0:
            return baseline_duration
        
        # If no baseline exists, use average duration * 2 as a reasonable upper bound
        return min(30.0, max(2.0, avg_duration * 2))
    
    def _calculate_error_rate_baseline(self, stats: Dict[str, Any]) -> float:
        """Calculate acceptable error rate baseline."""
        current_success_rate = stats.get('success_rate', 0.95)
        error_rate = 1.0 - current_success_rate
        
        # Set error rate baseline to 2x current error rate, capped at 20%
        baseline_error_rate = min(0.20, max(0.05, error_rate * 2))
        
        return baseline_error_rate
    
    def _calculate_events_baseline(self, stats: Dict[str, Any]) -> Dict[str, float]:
        """Calculate events per sync baseline."""
        total_events = stats.get('total_events_synced', 0)
        total_syncs = stats.get('total_syncs', 1)
        
        avg_events_per_sync = total_events / total_syncs if total_syncs > 0 else 0
        
        return {
            'avg_events_per_sync': avg_events_per_sync,
            'min_expected': max(0, avg_events_per_sync * 0.5),
            'max_expected': avg_events_per_sync * 2
        }
    
    def _calculate_confidence_level(self, stats: Dict[str, Any]) -> str:
        """Calculate confidence level based on data volume and consistency."""
        total_syncs = stats.get('total_syncs', 0)
        
        if total_syncs < 10:
            return 'low'
        elif total_syncs < 100:
            return 'medium'
        else:
            return 'high'
    
    def _generate_analysis_summary(self, stats: Dict[str, Any], baselines: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the baseline analysis."""
        
        # Identify patterns in error data
        error_patterns = stats.get('error_patterns', {})
        schema_errors = stats.get('schema_errors_count', 0)
        
        summary = {
            'data_quality': {
                'total_syncs': stats['total_syncs'],
                'success_rate': stats['success_rate'],
                'avg_duration': stats['avg_duration'],
                'confidence': baselines['confidence_level']
            },
            'error_analysis': {
                'total_schema_errors': schema_errors,
                'schema_error_rate': schema_errors / stats['total_syncs'] if stats['total_syncs'] > 0 else 0,
                'error_patterns': error_patterns,
                'critical_issues': schema_errors > 0
            },
            'recommendations': self._generate_recommendations(stats, baselines)
        }
        
        return summary
    
    def _generate_recommendations(self, stats: Dict[str, Any], baselines: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Schema error recommendations
        schema_errors = stats.get('schema_errors_count', 0)
        if schema_errors > 0:
            recommendations.append(
                f"CRITICAL: {schema_errors} schema errors detected. Database migration required immediately."
            )
            recommendations.append(
                "Review and execute database migrations for user_oauth_tokens.scope column."
            )
        
        # Success rate recommendations
        success_rate = stats.get('success_rate', 0)
        if success_rate < 0.90:
            recommendations.append(
                f"Success rate ({success_rate:.1%}) is below recommended threshold. Investigate error patterns."
            )
        
        # Performance recommendations
        avg_duration = stats.get('avg_duration', 0)
        if avg_duration > 10.0:
            recommendations.append(
                f"Average sync duration ({avg_duration:.1f}s) is high. Consider performance optimization."
            )
        
        # Data volume recommendations
        total_syncs = stats.get('total_syncs', 0)
        if total_syncs < 50:
            recommendations.append(
                "Limited historical data. Monitor for 24-48 hours to establish more reliable baselines."
            )
        
        return recommendations
    
    def update_prometheus_baselines(self) -> bool:
        """Update Prometheus baseline metrics."""
        try:
            if not self.baseline_data:
                logger.warning("No baseline data available to update Prometheus metrics")
                return False
            
            # Update baseline metrics in Prometheus
            calendar_sync_monitor.baseline_duration = self.baseline_data.get('duration_baseline')
            calendar_sync_monitor.baseline_success_rate = self.baseline_data.get('success_rate_baseline')
            
            # Update Prometheus gauges
            if calendar_sync_monitor.baseline_duration:
                calendar_sync_monitor.calendar_sync_baseline_duration.set(
                    calendar_sync_monitor.baseline_duration
                )
            
            if calendar_sync_monitor.baseline_success_rate:
                calendar_sync_monitor.calendar_sync_baseline_success_rate.set(
                    calendar_sync_monitor.baseline_success_rate
                )
            
            logger.info("Prometheus baseline metrics updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Prometheus baseline metrics: {e}")
            return False
    
    def save_baseline_report(self, filepath: str = None) -> str:
        """Save baseline analysis report to file."""
        if not filepath:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = f"calendar_sync_baseline_report_{timestamp}.json"
        
        report = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'generator': 'calendar_sync_baseline_establisher',
                'version': '1.0.0'
            },
            'baselines': self.baseline_data,
            'analysis': self.analysis_results
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Baseline report saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save baseline report: {e}")
            raise
    
    def validate_current_performance(self) -> Dict[str, Any]:
        """Validate current performance against established baselines."""
        if not self.baseline_data:
            return {'validation': 'no_baselines_available'}
        
        # Get recent performance data (last 1 hour)
        recent_stats = calendar_sync_monitor.get_sync_statistics(hours=1)
        
        validation_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'baseline_comparison': {},
            'alerts': [],
            'overall_status': 'healthy'
        }
        
        # Compare success rate
        if recent_stats['total_syncs'] > 0:
            success_rate_baseline = self.baseline_data['success_rate_baseline']
            current_success_rate = recent_stats['success_rate']
            
            if current_success_rate < success_rate_baseline * 0.8:
                validation_results['alerts'].append({
                    'severity': 'high',
                    'metric': 'success_rate',
                    'current': current_success_rate,
                    'baseline': success_rate_baseline,
                    'deviation': (current_success_rate - success_rate_baseline) / success_rate_baseline
                })
                validation_results['overall_status'] = 'degraded'
        
        # Compare duration
        duration_baseline = self.baseline_data['duration_baseline']
        current_avg_duration = recent_stats['avg_duration']
        
        if current_avg_duration > duration_baseline * 1.5:
            validation_results['alerts'].append({
                'severity': 'medium',
                'metric': 'avg_duration',
                'current': current_avg_duration,
                'baseline': duration_baseline,
                'deviation': (current_avg_duration - duration_baseline) / duration_baseline
            })
            if validation_results['overall_status'] == 'healthy':
                validation_results['overall_status'] = 'degraded'
        
        # Check schema errors
        if recent_stats.get('schema_errors_count', 0) > 0:
            validation_results['alerts'].append({
                'severity': 'critical',
                'metric': 'schema_errors',
                'current': recent_stats['schema_errors_count'],
                'baseline': 0,
                'message': 'Database schema errors detected - immediate attention required'
            })
            validation_results['overall_status'] = 'critical'
        
        return validation_results


async def main():
    """Main function to establish baselines and generate report."""
    logger.info("Starting calendar sync baseline establishment")
    
    establisher = BaselineEstablisher()
    
    try:
        # Analyze historical performance
        logger.info("Analyzing historical performance data...")
        analysis_results = establisher.analyze_historical_performance(hours_back=168)  # 7 days
        
        if not analysis_results['baseline_established']:
            logger.error(f"Failed to establish baselines: {analysis_results['reason']}")
            return 1
        
        establisher.analysis_results = analysis_results
        
        # Update Prometheus baselines
        logger.info("Updating Prometheus baseline metrics...")
        if establisher.update_prometheus_baselines():
            logger.info("Prometheus baselines updated successfully")
        else:
            logger.warning("Failed to update Prometheus baselines")
        
        # Validate current performance
        logger.info("Validating current performance against baselines...")
        validation = establisher.validate_current_performance()
        
        if validation['overall_status'] == 'critical':
            logger.error("CRITICAL: Current performance shows critical issues")
            for alert in validation['alerts']:
                if alert['severity'] == 'critical':
                    logger.error(f"CRITICAL ALERT: {alert}")
        elif validation['overall_status'] == 'degraded':
            logger.warning("WARNING: Current performance is degraded")
            for alert in validation['alerts']:
                logger.warning(f"ALERT: {alert}")
        else:
            logger.info("Current performance is within acceptable baselines")
        
        # Save baseline report
        report_path = establisher.save_baseline_report()
        
        # Print summary
        baselines = establisher.baseline_data
        analysis = analysis_results['analysis_summary']
        
        print("\n" + "="*60)
        print("CALENDAR SYNC BASELINE ESTABLISHMENT SUMMARY")
        print("="*60)
        print(f"Analysis Period: {baselines['analysis_period_hours']} hours")
        print(f"Data Points: {baselines['data_points']}")
        print(f"Confidence Level: {baselines['confidence_level']}")
        print(f"Established At: {baselines['established_at']}")
        print("\nBaseline Metrics:")
        print(f"  Success Rate: {baselines['success_rate_baseline']:.2%}")
        print(f"  Duration: {baselines['duration_baseline']:.2f} seconds")
        print(f"  Error Rate Threshold: {baselines['error_rate_baseline']:.2%}")
        print(f"  Avg Events/Sync: {baselines['events_per_sync_baseline']['avg_events_per_sync']:.1f}")
        
        if analysis['error_analysis']['critical_issues']:
            print(f"\n⚠️  CRITICAL ISSUES DETECTED:")
            print(f"  Schema Errors: {analysis['error_analysis']['total_schema_errors']}")
            print(f"  Schema Error Rate: {analysis['error_analysis']['schema_error_rate']:.2%}")
        
        print(f"\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  • {rec}")
        
        print(f"\nCurrent Status: {validation['overall_status'].upper()}")
        if validation['alerts']:
            print("Active Alerts:")
            for alert in validation['alerts']:
                print(f"  • [{alert['severity'].upper()}] {alert['metric']}: {alert.get('message', 'Performance deviation detected')}")
        
        print(f"\nReport saved to: {report_path}")
        print("="*60)
        
        return 0 if validation['overall_status'] != 'critical' else 2
        
    except Exception as e:
        logger.error(f"Failed to establish baselines: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)