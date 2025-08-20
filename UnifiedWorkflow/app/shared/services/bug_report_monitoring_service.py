"""
Bug Report Monitoring Service

This service monitors bug report submission failures and provides alerts
when issues occur with the bug report system.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class BugReportFailureType(Enum):
    """Types of bug report submission failures"""
    AUTHENTICATION_ERROR = "authentication_error"
    DATABASE_ERROR = "database_error"
    SUBTASK_GENERATION_ERROR = "subtask_generation_error"
    ADMIN_USER_NOT_FOUND = "admin_user_not_found"
    GENERAL_ERROR = "general_error"
    CRUD_IMPORT_ERROR = "crud_import_error"
    LLM_SERVICE_ERROR = "llm_service_error"

@dataclass
class BugReportFailure:
    """Represents a bug report submission failure"""
    timestamp: datetime
    failure_type: BugReportFailureType
    user_email: str
    bug_title: str
    error_message: str
    stack_trace: Optional[str] = None
    request_id: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None

class BugReportMonitoringService:
    """Service for monitoring bug report submission failures"""
    
    def __init__(self, max_recent_failures: int = 100):
        self.max_recent_failures = max_recent_failures
        self.recent_failures: List[BugReportFailure] = []
        self.failure_counts: Dict[BugReportFailureType, int] = {
            failure_type: 0 for failure_type in BugReportFailureType
        }
        self.total_attempts = 0
        self.total_failures = 0
        
    def record_attempt(self):
        """Record a bug report submission attempt"""
        self.total_attempts += 1
        logger.debug(f"Bug report attempt recorded. Total attempts: {self.total_attempts}")
    
    def record_failure(
        self,
        failure_type: BugReportFailureType,
        user_email: str,
        bug_title: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Record a bug report submission failure"""
        failure = BugReportFailure(
            timestamp=datetime.now(timezone.utc),
            failure_type=failure_type,
            user_email=user_email,
            bug_title=bug_title,
            error_message=error_message,
            stack_trace=stack_trace,
            request_id=request_id,
            additional_context=additional_context or {}
        )
        
        # Add to recent failures list
        self.recent_failures.append(failure)
        if len(self.recent_failures) > self.max_recent_failures:
            self.recent_failures.pop(0)
        
        # Update counters
        self.failure_counts[failure_type] += 1
        self.total_failures += 1
        
        # Log the failure
        logger.error(
            f"Bug report submission failure recorded: {failure_type.value} - "
            f"User: {user_email}, Title: '{bug_title}', Error: {error_message}"
        )
        
        # Check if we need to trigger alerts
        self._check_alert_conditions(failure)
    
    def _check_alert_conditions(self, failure: BugReportFailure):
        """Check if failure conditions warrant an alert"""
        now = datetime.now(timezone.utc)
        
        # Alert on high failure rate (>50% failures in last 10 attempts)
        recent_window = now - timedelta(minutes=30)
        recent_failures = [f for f in self.recent_failures if f.timestamp >= recent_window]
        
        if len(recent_failures) >= 5:
            failure_rate = len(recent_failures) / min(10, self.total_attempts)
            if failure_rate > 0.5:
                self._trigger_alert(
                    f"HIGH_FAILURE_RATE",
                    f"Bug report failure rate is {failure_rate:.1%} ({len(recent_failures)} failures in last 30 minutes)"
                )
        
        # Alert on critical failure types
        critical_types = [
            BugReportFailureType.DATABASE_ERROR,
            BugReportFailureType.ADMIN_USER_NOT_FOUND
        ]
        
        if failure.failure_type in critical_types:
            self._trigger_alert(
                f"CRITICAL_BUG_REPORT_FAILURE",
                f"Critical bug report failure: {failure.failure_type.value} - {failure.error_message}"
            )
        
        # Alert on repeated failures from same user
        user_failures = [f for f in recent_failures if f.user_email == failure.user_email]
        if len(user_failures) >= 3:
            self._trigger_alert(
                f"REPEATED_USER_FAILURES",
                f"User {failure.user_email} has {len(user_failures)} bug report failures in last 30 minutes"
            )
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger an alert for bug report failures"""
        logger.critical(f"🚨 BUG_REPORT_ALERT [{alert_type}]: {message}")
        
        # In a production system, this would integrate with:
        # - Email notifications
        # - Slack/Teams webhooks
        # - PagerDuty or similar alerting systems
        # - Metrics systems like Prometheus
        
        # For now, we'll log with a special format that monitoring tools can detect
        alert_data = {
            "alert_type": alert_type,
            "service": "bug_report_monitoring",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "critical"
        }
        
        logger.critical(f"MONITORING_ALERT: {json.dumps(alert_data)}")
    
    def get_failure_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get failure statistics for the specified time period"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_failures = [f for f in self.recent_failures if f.timestamp >= since]
        
        failure_by_type = {}
        for failure_type in BugReportFailureType:
            count = len([f for f in recent_failures if f.failure_type == failure_type])
            failure_by_type[failure_type.value] = count
        
        success_rate = 0.0
        if self.total_attempts > 0:
            success_rate = (self.total_attempts - len(recent_failures)) / self.total_attempts
        
        return {
            "time_period_hours": hours,
            "total_failures": len(recent_failures),
            "total_attempts": self.total_attempts,
            "success_rate": success_rate,
            "failure_rate": 1.0 - success_rate,
            "failures_by_type": failure_by_type,
            "most_common_failure": max(failure_by_type.items(), key=lambda x: x[1])[0] if recent_failures else None,
            "recent_failures": [
                {
                    "timestamp": f.timestamp.isoformat(),
                    "type": f.failure_type.value,
                    "user": f.user_email,
                    "title": f.bug_title,
                    "error": f.error_message
                }
                for f in recent_failures[-10:]  # Last 10 failures
            ]
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of bug report system"""
        now = datetime.now(timezone.utc)
        recent_window = now - timedelta(minutes=60)
        recent_failures = [f for f in self.recent_failures if f.timestamp >= recent_window]
        
        # Determine health status
        if not recent_failures:
            status = "healthy"
            status_message = "No recent failures"
        elif len(recent_failures) < 3:
            status = "warning"
            status_message = f"{len(recent_failures)} failures in last hour"
        else:
            status = "critical"
            status_message = f"{len(recent_failures)} failures in last hour - investigate immediately"
        
        return {
            "status": status,
            "message": status_message,
            "last_failure": recent_failures[-1].timestamp.isoformat() if recent_failures else None,
            "failures_last_hour": len(recent_failures),
            "total_failures": self.total_failures,
            "total_attempts": self.total_attempts
        }

# Global instance
bug_report_monitor = BugReportMonitoringService()

def record_bug_report_attempt():
    """Convenience function to record a bug report attempt"""
    bug_report_monitor.record_attempt()

def record_bug_report_failure(
    failure_type: BugReportFailureType,
    user_email: str,
    bug_title: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    request_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
):
    """Convenience function to record a bug report failure"""
    bug_report_monitor.record_failure(
        failure_type=failure_type,
        user_email=user_email,
        bug_title=bug_title,
        error_message=error_message,
        stack_trace=stack_trace,
        request_id=request_id,
        additional_context=additional_context
    )

def get_bug_report_statistics(hours: int = 24) -> Dict[str, Any]:
    """Convenience function to get bug report statistics"""
    return bug_report_monitor.get_failure_statistics(hours)

def get_bug_report_health() -> Dict[str, Any]:
    """Convenience function to get bug report health status"""
    return bug_report_monitor.get_health_status()