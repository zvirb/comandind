"""
Structured logging configuration for comprehensive system observability.

This module provides:
- Centralized logging configuration
- Structured JSON logging for all services
- Log correlation across requests
- Security event logging
- Performance logging
- Error tracking and alerting
- Log aggregation preparation
"""

import logging
import logging.config
import json
import time
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextvars import ContextVar
from functools import wraps
import os
import sys
from pathlib import Path

# Context variables for request correlation
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
user_id_context: ContextVar[str] = ContextVar('user_id', default='')
trace_id_context: ContextVar[str] = ContextVar('trace_id', default='')


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with consistent fields.
    """
    
    def __init__(self, service_name: str = "ai_workflow_engine", environment: str = "production"):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log structure
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "hostname": self.hostname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread,
        }
        
        # Add correlation IDs
        request_id = request_id_context.get('')
        user_id = user_id_context.get('')
        trace_id = trace_id_context.get('')
        
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = user_id
        if trace_id:
            log_entry["trace_id"] = trace_id
        
        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'message']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry.update(extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class SecurityEventLogger:
    """Specialized logger for security events."""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_auth_attempt(self, username: str, method: str, success: bool, 
                        ip_address: str, user_agent: str, **kwargs):
        """Log authentication attempt."""
        self.logger.info(
            "Authentication attempt",
            extra={
                "event_type": "auth_attempt",
                "username": username,
                "method": method,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent,
                **kwargs
            }
        )
    
    def log_auth_failure(self, username: str, reason: str, ip_address: str, 
                        user_agent: str, **kwargs):
        """Log authentication failure."""
        self.logger.warning(
            "Authentication failed",
            extra={
                "event_type": "auth_failure",
                "username": username,
                "failure_reason": reason,
                "ip_address": ip_address,
                "user_agent": user_agent,
                **kwargs
            }
        )
    
    def log_suspicious_activity(self, activity_type: str, description: str,
                               ip_address: str, severity: str = "medium", **kwargs):
        """Log suspicious activity."""
        log_method = getattr(self.logger, severity.lower(), self.logger.warning)
        log_method(
            "Suspicious activity detected",
            extra={
                "event_type": "suspicious_activity",
                "activity_type": activity_type,
                "description": description,
                "ip_address": ip_address,
                "severity": severity,
                **kwargs
            }
        )
    
    def log_data_access(self, user_id: str, resource_type: str, resource_id: str,
                       operation: str, success: bool, **kwargs):
        """Log data access events."""
        self.logger.info(
            "Data access event",
            extra={
                "event_type": "data_access",
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "operation": operation,
                "success": success,
                **kwargs
            }
        )
    
    def log_privilege_escalation(self, user_id: str, old_role: str, new_role: str,
                                granted_by: str, **kwargs):
        """Log privilege escalation events."""
        self.logger.warning(
            "Privilege escalation",
            extra={
                "event_type": "privilege_escalation",
                "user_id": user_id,
                "old_role": old_role,
                "new_role": new_role,
                "granted_by": granted_by,
                **kwargs
            }
        )


class PerformanceLogger:
    """Specialized logger for performance events."""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_slow_query(self, query: str, duration: float, table: str = None, **kwargs):
        """Log slow database query."""
        self.logger.warning(
            "Slow database query detected",
            extra={
                "event_type": "slow_query",
                "query": query[:500],  # Truncate long queries
                "duration_seconds": duration,
                "table": table,
                **kwargs
            }
        )
    
    def log_high_memory_usage(self, service: str, memory_mb: float, threshold_mb: float, **kwargs):
        """Log high memory usage."""
        self.logger.warning(
            "High memory usage detected",
            extra={
                "event_type": "high_memory_usage",
                "service": service,
                "memory_mb": memory_mb,
                "threshold_mb": threshold_mb,
                **kwargs
            }
        )
    
    def log_api_response_time(self, endpoint: str, method: str, duration: float, 
                             status_code: int, **kwargs):
        """Log API response times."""
        level = "warning" if duration > 2.0 else "info"
        log_method = getattr(self.logger, level)
        
        log_method(
            "API request processed",
            extra={
                "event_type": "api_response",
                "endpoint": endpoint,
                "method": method,
                "duration_seconds": duration,
                "status_code": status_code,
                **kwargs
            }
        )


class BusinessLogger:
    """Specialized logger for business events."""
    
    def __init__(self, logger_name: str = "business"):
        self.logger = logging.getLogger(logger_name)
    
    def log_user_registration(self, user_id: str, registration_method: str, **kwargs):
        """Log user registration."""
        self.logger.info(
            "User registered",
            extra={
                "event_type": "user_registration",
                "user_id": user_id,
                "registration_method": registration_method,
                **kwargs
            }
        )
    
    def log_ai_task_completion(self, task_id: str, task_type: str, duration: float,
                              success: bool, model_used: str, **kwargs):
        """Log AI task completion."""
        self.logger.info(
            "AI task completed",
            extra={
                "event_type": "ai_task_completion",
                "task_id": task_id,
                "task_type": task_type,
                "duration_seconds": duration,
                "success": success,
                "model_used": model_used,
                **kwargs
            }
        )
    
    def log_quota_exceeded(self, user_id: str, quota_type: str, current_usage: int,
                          limit: int, **kwargs):
        """Log quota exceeded events."""
        self.logger.warning(
            "User quota exceeded",
            extra={
                "event_type": "quota_exceeded",
                "user_id": user_id,
                "quota_type": quota_type,
                "current_usage": current_usage,
                "limit": limit,
                **kwargs
            }
        )


def setup_logging(
    service_name: str = "ai_workflow_engine",
    log_level: str = "INFO",
    environment: str = "production",
    log_file: Optional[str] = None,
    json_logs: bool = True,
    correlation_enabled: bool = True
) -> Dict[str, Any]:
    """
    Setup centralized logging configuration.
    
    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name (development, staging, production)
        log_file: Optional log file path
        json_logs: Whether to use JSON formatting
        correlation_enabled: Whether to enable request correlation
    
    Returns:
        Logging configuration dictionary
    """
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
                "service_name": service_name,
                "environment": environment
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured" if json_logs else "simple",
                "stream": sys.stdout
            }
        },
        "loggers": {
            # Root logger
            "": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            # Application loggers
            "ai_workflow_engine": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            # Specialized loggers
            "security": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "performance": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "business": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            # Third-party library loggers
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "celery": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    # Add file handler if log file is specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "structured" if json_logs else "simple",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            if "file" not in logger_config["handlers"]:
                logger_config["handlers"].append("file")
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    return config


def with_correlation(request_id: str = None, user_id: str = None, trace_id: str = None):
    """
    Decorator to add correlation IDs to log context.
    
    Usage:
        @with_correlation()
        async def my_function():
            logger.info("This will include correlation IDs")
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            token_request = request_id_context.set(request_id or str(uuid.uuid4()))
            token_user = user_id_context.set(user_id or '')
            token_trace = trace_id_context.set(trace_id or str(uuid.uuid4()))
            
            try:
                return await func(*args, **kwargs)
            finally:
                request_id_context.reset(token_request)
                user_id_context.reset(token_user)
                trace_id_context.reset(token_trace)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            token_request = request_id_context.set(request_id or str(uuid.uuid4()))
            token_user = user_id_context.set(user_id or '')
            token_trace = trace_id_context.set(trace_id or str(uuid.uuid4()))
            
            try:
                return func(*args, **kwargs)
            finally:
                request_id_context.reset(token_request)
                user_id_context.reset(token_user)
                trace_id_context.reset(token_trace)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


# Pre-configured logger instances
security_logger = SecurityEventLogger()
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()


# Utility functions for common logging patterns
def log_exception(logger: logging.Logger, message: str, **kwargs):
    """Log exception with full traceback."""
    logger.exception(message, extra=kwargs)


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """Log message with current context."""
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=kwargs)


def set_request_context(request_id: str, user_id: str = None, trace_id: str = None):
    """Set request correlation context."""
    request_id_context.set(request_id)
    if user_id:
        user_id_context.set(user_id)
    if trace_id:
        trace_id_context.set(trace_id)


def clear_request_context():
    """Clear request correlation context."""
    request_id_context.set('')
    user_id_context.set('')
    trace_id_context.set('')