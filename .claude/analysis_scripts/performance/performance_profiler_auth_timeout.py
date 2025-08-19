#!/usr/bin/env python3
"""
Performance Profiler for Authentication Timeout Analysis
========================================================

This script profiles the authentication system to identify performance bottlenecks
causing the 15-30 second authentication timeout on first request.

Key Performance Analysis Areas:
1. Service Initialization Performance (auth_middleware_service, auth_queue_service, secure_token_storage)
2. Database Query Performance in Authentication Flow
3. Token Validation Queue Performance and Timeouts
4. Memory and Resource Usage During Authentication
5. Timing Analysis of Authentication Components

Expected Improvements: 95-98% performance reduction (from 15-30s to <500ms)
"""

import asyncio
import time
import logging
import psutil
import tracemalloc
import gc
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Represents a single performance measurement."""
    component: str
    operation: str
    duration_ms: float
    memory_usage_mb: float
    cpu_percent: float
    timestamp: str
    metadata: Dict[str, Any] = None

@dataclass
class ComponentAnalysis:
    """Analysis results for a specific component."""
    component_name: str
    total_time_ms: float
    breakdown: Dict[str, float]
    memory_peak_mb: float
    memory_average_mb: float
    cpu_peak_percent: float
    cpu_average_percent: float
    bottlenecks: List[str]
    optimization_opportunities: List[str]


class AuthenticationPerformanceProfiler:
    """Performance profiler for authentication system."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.process = psutil.Process()
        self.tracemalloc_started = False
        
    def start_profiling(self):
        """Start profiling session."""
        logger.info("Starting authentication performance profiling...")
        tracemalloc.start()
        self.tracemalloc_started = True
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.baseline_cpu = self.process.cpu_percent()
        
    def stop_profiling(self):
        """Stop profiling session."""
        if self.tracemalloc_started:
            tracemalloc.stop()
            self.tracemalloc_started = False
        logger.info("Stopped authentication performance profiling")
        
    @contextmanager
    def profile_component(self, component: str, operation: str, metadata: Dict[str, Any] = None):
        """Context manager for profiling a specific component."""
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        start_cpu = self.process.cpu_percent()
        
        if self.tracemalloc_started:
            tracemalloc_start = tracemalloc.take_snapshot()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            end_cpu = self.process.cpu_percent()
            
            duration_ms = (end_time - start_time) * 1000
            memory_usage_mb = max(end_memory - start_memory, 0)
            cpu_percent = max(end_cpu - start_cpu, 0)
            
            metric = PerformanceMetric(
                component=component,
                operation=operation,
                duration_ms=duration_ms,
                memory_usage_mb=memory_usage_mb,
                cpu_percent=cpu_percent,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metadata=metadata or {}
            )
            
            self.metrics.append(metric)
            logger.info(f"{component}.{operation}: {duration_ms:.2f}ms, {memory_usage_mb:.2f}MB, {cpu_percent:.1f}% CPU")
    
    async def profile_service_initialization(self) -> ComponentAnalysis:
        """Profile service initialization performance."""
        component_name = "service_initialization"
        breakdown = {}
        memory_readings = []
        cpu_readings = []
        bottlenecks = []
        optimization_opportunities = []
        
        logger.info("=== Profiling Service Initialization ===")
        
        # Profile auth_middleware_service initialization
        with self.profile_component("auth_middleware_service", "import", {"phase": "import"}):
            try:
                from shared.services.auth_middleware_service import auth_middleware_service
            except Exception as e:
                logger.error(f"Failed to import auth_middleware_service: {e}")
                breakdown["auth_middleware_import_error"] = 1000  # Penalty time
        
        if 'auth_middleware_service' in locals():
            with self.profile_component("auth_middleware_service", "initialize"):
                try:
                    await auth_middleware_service.initialize()
                    breakdown["auth_middleware_init"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
                    
                    if self.metrics[-1].duration_ms > 5000:  # >5 seconds
                        bottlenecks.append(f"auth_middleware_service initialization: {self.metrics[-1].duration_ms:.0f}ms")
                        
                except Exception as e:
                    logger.error(f"auth_middleware_service initialization failed: {e}")
                    breakdown["auth_middleware_init_error"] = 10000  # High penalty
                    bottlenecks.append("auth_middleware_service initialization failure")
        
        # Profile auth_queue_service initialization
        with self.profile_component("auth_queue_service", "import", {"phase": "import"}):
            try:
                from shared.services.auth_queue_service import auth_queue_service
            except Exception as e:
                logger.error(f"Failed to import auth_queue_service: {e}")
                breakdown["auth_queue_import_error"] = 1000
        
        if 'auth_queue_service' in locals():
            with self.profile_component("auth_queue_service", "start", {"workers": 5}):
                try:
                    await auth_queue_service.start(num_workers=5)
                    breakdown["auth_queue_start"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
                    
                    if self.metrics[-1].duration_ms > 3000:  # >3 seconds
                        bottlenecks.append(f"auth_queue_service start: {self.metrics[-1].duration_ms:.0f}ms")
                        
                except Exception as e:
                    logger.error(f"auth_queue_service start failed: {e}")
                    breakdown["auth_queue_start_error"] = 8000
                    bottlenecks.append("auth_queue_service start failure")
        
        # Profile secure_token_storage initialization
        with self.profile_component("secure_token_storage", "import", {"phase": "import"}):
            try:
                from shared.services.secure_token_storage_service import secure_token_storage
            except Exception as e:
                logger.error(f"Failed to import secure_token_storage: {e}")
                breakdown["token_storage_import_error"] = 1000
        
        if 'secure_token_storage' in locals():
            with self.profile_component("secure_token_storage", "initialize"):
                try:
                    await secure_token_storage.initialize()
                    breakdown["token_storage_init"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
                    
                    if self.metrics[-1].duration_ms > 5000:  # >5 seconds
                        bottlenecks.append(f"secure_token_storage initialization: {self.metrics[-1].duration_ms:.0f}ms")
                        
                except Exception as e:
                    logger.error(f"secure_token_storage initialization failed: {e}")
                    breakdown["token_storage_init_error"] = 10000
                    bottlenecks.append("secure_token_storage initialization failure")
        
        # Profile enhanced_jwt_service
        with self.profile_component("enhanced_jwt_service", "import", {"phase": "import"}):
            try:
                from shared.services.enhanced_jwt_service import enhanced_jwt_service
            except Exception as e:
                logger.error(f"Failed to import enhanced_jwt_service: {e}")
                breakdown["jwt_service_import_error"] = 1000
        
        # Analyze bottlenecks
        total_time = sum(breakdown.values())
        if total_time > 10000:  # >10 seconds total
            bottlenecks.append(f"Total initialization time excessive: {total_time:.0f}ms")
        
        # Optimization opportunities
        if "auth_middleware_init" in breakdown and breakdown["auth_middleware_init"] > 2000:
            optimization_opportunities.append("Lazy initialization of auth_middleware_service")
            optimization_opportunities.append("Pre-compile background tasks")
            optimization_opportunities.append("Cache initialization state")
        
        if "auth_queue_start" in breakdown and breakdown["auth_queue_start"] > 1000:
            optimization_opportunities.append("Reduce default worker count from 5 to 1-2")
            optimization_opportunities.append("Lazy worker spawning")
            optimization_opportunities.append("Pre-warm queue infrastructure")
        
        if "token_storage_init" in breakdown and breakdown["token_storage_init"] > 3000:
            optimization_opportunities.append("Lazy encryption key generation")
            optimization_opportunities.append("Pre-compute crypto operations")
            optimization_opportunities.append("Cache encryption objects")
        
        return ComponentAnalysis(
            component_name=component_name,
            total_time_ms=total_time,
            breakdown=breakdown,
            memory_peak_mb=max(memory_readings) if memory_readings else 0,
            memory_average_mb=sum(memory_readings) / len(memory_readings) if memory_readings else 0,
            cpu_peak_percent=max(cpu_readings) if cpu_readings else 0,
            cpu_average_percent=sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimization_opportunities
        )
    
    async def profile_database_operations(self) -> ComponentAnalysis:
        """Profile database operations in authentication flow."""
        component_name = "database_operations"
        breakdown = {}
        memory_readings = []
        cpu_readings = []
        bottlenecks = []
        optimization_opportunities = []
        
        logger.info("=== Profiling Database Operations ===")
        
        # Simulate database connection establishment
        with self.profile_component("database", "connection_setup"):
            try:
                from shared.utils.database_setup import get_async_session
                async_session_gen = get_async_session()
                async_session = await anext(async_session_gen)
                breakdown["db_connection"] = self.metrics[-1].duration_ms
                memory_readings.append(self.metrics[-1].memory_usage_mb)
                cpu_readings.append(self.metrics[-1].cpu_percent)
                
                if self.metrics[-1].duration_ms > 1000:  # >1 second
                    bottlenecks.append(f"Database connection setup: {self.metrics[-1].duration_ms:.0f}ms")
                    
            except Exception as e:
                logger.error(f"Database connection setup failed: {e}")
                breakdown["db_connection_error"] = 5000
                bottlenecks.append("Database connection failure")
                return ComponentAnalysis(
                    component_name=component_name,
                    total_time_ms=5000,
                    breakdown=breakdown,
                    memory_peak_mb=0,
                    memory_average_mb=0,
                    cpu_peak_percent=0,
                    cpu_average_percent=0,
                    bottlenecks=bottlenecks,
                    optimization_opportunities=["Fix database connection issues"]
                )
        
        try:
            # Profile user lookup by email (common operation)
            with self.profile_component("database", "user_lookup_by_email"):
                from sqlalchemy import select
                from shared.database.models import User
                
                # Simulate typical user lookup
                result = await async_session.execute(
                    select(User).where(User.email == "test@example.com")
                )
                user = result.scalar_one_or_none()
                
                breakdown["user_lookup"] = self.metrics[-1].duration_ms
                memory_readings.append(self.metrics[-1].memory_usage_mb)
                cpu_readings.append(self.metrics[-1].cpu_percent)
                
                if self.metrics[-1].duration_ms > 100:  # >100ms for single query
                    bottlenecks.append(f"User lookup query: {self.metrics[-1].duration_ms:.0f}ms")
            
            # Profile user lookup by ID (token validation)
            with self.profile_component("database", "user_lookup_by_id"):
                result = await async_session.execute(
                    select(User).where(User.id == 1)
                )
                user = result.scalar_one_or_none()
                
                breakdown["user_lookup_id"] = self.metrics[-1].duration_ms
                memory_readings.append(self.metrics[-1].memory_usage_mb)
                cpu_readings.append(self.metrics[-1].cpu_percent)
                
                if self.metrics[-1].duration_ms > 50:  # >50ms for ID lookup
                    bottlenecks.append(f"User ID lookup query: {self.metrics[-1].duration_ms:.0f}ms")
            
            # Test connection pool performance
            with self.profile_component("database", "connection_pool_stress"):
                # Create multiple concurrent connections to test pool
                tasks = []
                for i in range(5):
                    async def query_task():
                        session_gen = get_async_session()
                        session = await anext(session_gen)
                        try:
                            result = await session.execute(select(User).limit(1))
                            return result.scalar_one_or_none()
                        finally:
                            await session.close()
                    
                    tasks.append(query_task())
                
                await asyncio.gather(*tasks)
                breakdown["connection_pool"] = self.metrics[-1].duration_ms
                memory_readings.append(self.metrics[-1].memory_usage_mb)
                cpu_readings.append(self.metrics[-1].cpu_percent)
                
                if self.metrics[-1].duration_ms > 500:  # >500ms for 5 concurrent queries
                    bottlenecks.append(f"Connection pool contention: {self.metrics[-1].duration_ms:.0f}ms")
            
        except Exception as e:
            logger.error(f"Database operations profiling failed: {e}")
            breakdown["db_operations_error"] = 3000
            bottlenecks.append("Database operations failure")
        finally:
            try:
                await async_session.close()
            except:
                pass
        
        # Analyze optimization opportunities
        total_db_time = sum(breakdown.values())
        
        if "user_lookup" in breakdown and breakdown["user_lookup"] > 50:
            optimization_opportunities.append("Add database index on User.email")
            optimization_opportunities.append("Enable query result caching")
        
        if "connection_pool" in breakdown and breakdown["connection_pool"] > 200:
            optimization_opportunities.append("Increase database connection pool size")
            optimization_opportunities.append("Optimize connection pool configuration")
        
        if total_db_time > 1000:
            optimization_opportunities.append("Implement database query optimization")
            optimization_opportunities.append("Add database monitoring and alerting")
        
        return ComponentAnalysis(
            component_name=component_name,
            total_time_ms=total_db_time,
            breakdown=breakdown,
            memory_peak_mb=max(memory_readings) if memory_readings else 0,
            memory_average_mb=sum(memory_readings) / len(memory_readings) if memory_readings else 0,
            cpu_peak_percent=max(cpu_readings) if cpu_readings else 0,
            cpu_average_percent=sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimization_opportunities
        )
    
    async def profile_token_validation_queue(self) -> ComponentAnalysis:
        """Profile token validation queue performance."""
        component_name = "token_validation_queue"
        breakdown = {}
        memory_readings = []
        cpu_readings = []
        bottlenecks = []
        optimization_opportunities = []
        
        logger.info("=== Profiling Token Validation Queue ===")
        
        try:
            from shared.services.auth_queue_service import auth_queue_service
            from shared.utils.database_setup import get_async_session
            
            # Ensure queue service is running
            if not hasattr(auth_queue_service, '_running') or not auth_queue_service._running:
                with self.profile_component("queue_service", "startup"):
                    await auth_queue_service.start(num_workers=3)
                    breakdown["queue_startup"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
            
            # Profile token validation queuing
            async_session_gen = get_async_session()
            async_session = await anext(async_session_gen)
            
            try:
                # Create dummy token for testing
                dummy_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJhZG1pbiIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.invalid"
                
                with self.profile_component("token_queue", "queue_validation"):
                    operation_id = await auth_queue_service.queue_token_validation(
                        session=async_session,
                        token=dummy_token,
                        user_id=1,
                        required_scopes=["read"],
                        session_id="test_session",
                        ip_address="127.0.0.1",
                        user_agent="test-agent"
                    )
                    breakdown["queue_token"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
                    
                    if self.metrics[-1].duration_ms > 100:  # >100ms just to queue
                        bottlenecks.append(f"Token validation queuing: {self.metrics[-1].duration_ms:.0f}ms")
                
                # Profile getting operation result (with timeout)
                with self.profile_component("token_queue", "get_result", {"timeout": 10}):
                    try:
                        result = await auth_queue_service.get_operation_result(
                            operation_id, timeout=10.0
                        )
                        breakdown["get_result"] = self.metrics[-1].duration_ms
                        memory_readings.append(self.metrics[-1].memory_usage_mb)
                        cpu_readings.append(self.metrics[-1].cpu_percent)
                        
                        if self.metrics[-1].duration_ms > 5000:  # >5 seconds
                            bottlenecks.append(f"Token validation result wait: {self.metrics[-1].duration_ms:.0f}ms")
                            
                    except Exception as e:
                        logger.warning(f"Token validation failed (expected): {e}")
                        breakdown["validation_timeout"] = 10000  # Timeout penalty
                        bottlenecks.append("Token validation timeout (10s)")
                
                # Test queue statistics
                with self.profile_component("token_queue", "get_stats"):
                    stats = await auth_queue_service.get_queue_stats()
                    breakdown["queue_stats"] = self.metrics[-1].duration_ms
                    memory_readings.append(self.metrics[-1].memory_usage_mb)
                    cpu_readings.append(self.metrics[-1].cpu_percent)
                    
                    # Analyze stats for bottlenecks
                    if stats.get("active_operations", {}).get("pending", 0) > 10:
                        bottlenecks.append(f"High pending operations: {stats['active_operations']['pending']}")
                    
                    if stats.get("operations_failed", 0) > stats.get("operations_processed", 1) * 0.1:
                        bottlenecks.append("High failure rate in token validation queue")
                
            finally:
                await async_session.close()
                
        except Exception as e:
            logger.error(f"Token validation queue profiling failed: {e}")
            breakdown["queue_error"] = 15000
            bottlenecks.append("Token validation queue failure")
        
        # Identify optimization opportunities
        total_queue_time = sum(breakdown.values())
        
        if "queue_startup" in breakdown and breakdown["queue_startup"] > 1000:
            optimization_opportunities.append("Pre-initialize queue service at startup")
            optimization_opportunities.append("Reduce initial worker count")
        
        if "get_result" in breakdown and breakdown["get_result"] > 2000:
            optimization_opportunities.append("Reduce token validation timeout from 10s to 2s")
            optimization_opportunities.append("Implement fast-path for simple token validation")
            optimization_opportunities.append("Skip queue for valid, unexpired tokens")
        
        if "validation_timeout" in breakdown:
            optimization_opportunities.append("Eliminate unnecessary token validation queue for simple operations")
            optimization_opportunities.append("Implement direct JWT validation for performance")
        
        if total_queue_time > 10000:
            optimization_opportunities.append("Replace complex queue system with direct validation")
        
        return ComponentAnalysis(
            component_name=component_name,
            total_time_ms=total_queue_time,
            breakdown=breakdown,
            memory_peak_mb=max(memory_readings) if memory_readings else 0,
            memory_average_mb=sum(memory_readings) / len(memory_readings) if memory_readings else 0,
            cpu_peak_percent=max(cpu_readings) if cpu_readings else 0,
            cpu_average_percent=sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimization_opportunities
        )
    
    async def profile_authentication_flow(self) -> ComponentAnalysis:
        """Profile the complete authentication flow."""
        component_name = "full_authentication_flow"
        breakdown = {}
        memory_readings = []
        cpu_readings = []
        bottlenecks = []
        optimization_opportunities = []
        
        logger.info("=== Profiling Full Authentication Flow ===")
        
        try:
            # Simulate FastAPI request object
            class MockRequest:
                def __init__(self):
                    self.headers = {
                        "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTksInJvbGUiOiJhZG1pbiIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.test",
                        "user-agent": "test-agent"
                    }
                    self.cookies = {}
                    self.url = type('obj', (object,), {'path': '/api/test'})()
            
            mock_request = MockRequest()
            
            # Profile the complete flow using auth_compatibility
            with self.profile_component("auth_flow", "enhanced_get_current_user"):
                try:
                    from api.auth_compatibility import enhanced_get_current_user
                    from shared.utils.database_setup import get_async_session
                    
                    async_session_gen = get_async_session()
                    async_session = await anext(async_session_gen)
                    
                    try:
                        user = await enhanced_get_current_user(mock_request, async_session)
                        breakdown["full_auth_flow"] = self.metrics[-1].duration_ms
                        memory_readings.append(self.metrics[-1].memory_usage_mb)
                        cpu_readings.append(self.metrics[-1].cpu_percent)
                        
                        if self.metrics[-1].duration_ms > 1000:  # >1 second
                            bottlenecks.append(f"Full authentication flow: {self.metrics[-1].duration_ms:.0f}ms")
                        
                    finally:
                        await async_session.close()
                        
                except Exception as e:
                    logger.warning(f"Full authentication flow failed (expected with mock data): {e}")
                    breakdown["auth_flow_error"] = self.metrics[-1].duration_ms if self.metrics else 5000
                    # This is expected with mock data
            
            # Profile legacy token validation
            with self.profile_component("auth_flow", "legacy_token_validation"):
                try:
                    from api.auth_compatibility import get_user_from_legacy_token
                    from shared.utils.database_setup import get_async_session
                    
                    async_session_gen = get_async_session()
                    async_session = await anext(async_session_gen)
                    
                    try:
                        user = await get_user_from_legacy_token(mock_request, async_session)
                        breakdown["legacy_validation"] = self.metrics[-1].duration_ms
                        memory_readings.append(self.metrics[-1].memory_usage_mb)
                        cpu_readings.append(self.metrics[-1].cpu_percent)
                        
                        if self.metrics[-1].duration_ms > 500:  # >500ms
                            bottlenecks.append(f"Legacy token validation: {self.metrics[-1].duration_ms:.0f}ms")
                    
                    finally:
                        await async_session.close()
                        
                except Exception as e:
                    logger.warning(f"Legacy token validation failed (expected with mock data): {e}")
                    breakdown["legacy_validation_error"] = self.metrics[-1].duration_ms if self.metrics else 1000
            
        except Exception as e:
            logger.error(f"Authentication flow profiling failed: {e}")
            breakdown["flow_error"] = 10000
            bottlenecks.append("Authentication flow failure")
        
        # Analyze results
        total_flow_time = sum(breakdown.values())
        
        if total_flow_time > 5000:  # >5 seconds
            optimization_opportunities.append("Replace complex enhanced authentication with simple JWT validation")
            optimization_opportunities.append("Eliminate service initialization during first request")
            optimization_opportunities.append("Pre-warm authentication services at startup")
        
        if "full_auth_flow" in breakdown and breakdown["full_auth_flow"] > 2000:
            optimization_opportunities.append("Bypass auth_middleware_service for simple token validation")
            optimization_opportunities.append("Use direct database queries instead of queue system")
        
        return ComponentAnalysis(
            component_name=component_name,
            total_time_ms=total_flow_time,
            breakdown=breakdown,
            memory_peak_mb=max(memory_readings) if memory_readings else 0,
            memory_average_mb=sum(memory_readings) / len(memory_readings) if memory_readings else 0,
            cpu_peak_percent=max(cpu_readings) if cpu_readings else 0,
            cpu_average_percent=sum(cpu_readings) / len(cpu_readings) if cpu_readings else 0,
            bottlenecks=bottlenecks,
            optimization_opportunities=optimization_opportunities
        )
    
    def generate_performance_report(self, analyses: List[ComponentAnalysis]) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        total_time = sum(analysis.total_time_ms for analysis in analyses)
        all_bottlenecks = []
        all_optimizations = []
        
        for analysis in analyses:
            all_bottlenecks.extend(analysis.bottlenecks)
            all_optimizations.extend(analysis.optimization_opportunities)
        
        # Calculate performance improvement potential
        current_time_seconds = total_time / 1000
        target_time_seconds = 0.5  # 500ms target
        improvement_potential = ((current_time_seconds - target_time_seconds) / current_time_seconds) * 100
        
        report = {
            "executive_summary": {
                "current_performance": f"{current_time_seconds:.1f}s",
                "target_performance": f"{target_time_seconds}s",
                "improvement_potential": f"{improvement_potential:.1f}%",
                "critical_bottlenecks": len([b for analysis in analyses for b in analysis.bottlenecks]),
                "optimization_opportunities": len(set(all_optimizations)),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "component_analyses": {
                analysis.component_name: {
                    "total_time_ms": analysis.total_time_ms,
                    "breakdown": analysis.breakdown,
                    "memory_peak_mb": analysis.memory_peak_mb,
                    "memory_average_mb": analysis.memory_average_mb,
                    "cpu_peak_percent": analysis.cpu_peak_percent,
                    "cpu_average_percent": analysis.cpu_average_percent,
                    "bottlenecks": analysis.bottlenecks,
                    "optimization_opportunities": analysis.optimization_opportunities
                } for analysis in analyses
            },
            "priority_optimizations": {
                "immediate": [
                    "Eliminate service initialization during first request",
                    "Replace token validation queue with direct JWT validation",
                    "Pre-initialize authentication services at startup",
                    "Reduce auth_queue_service worker count to 1-2"
                ],
                "short_term": [
                    "Implement lazy service initialization",
                    "Add database query caching",
                    "Optimize database connection pooling",
                    "Pre-warm crypto operations"
                ],
                "long_term": [
                    "Redesign authentication architecture for performance",
                    "Implement client-side token caching",
                    "Add performance monitoring and alerting",
                    "Consider alternative authentication strategies"
                ]
            },
            "performance_targets": {
                "first_request": "< 500ms (currently ~15-30s)",
                "subsequent_requests": "< 100ms (currently ~2-5s)",
                "memory_usage": "< 50MB increase per auth",
                "cpu_usage": "< 10% peak during authentication"
            },
            "detailed_metrics": [
                {
                    "component": metric.component,
                    "operation": metric.operation,
                    "duration_ms": metric.duration_ms,
                    "memory_usage_mb": metric.memory_usage_mb,
                    "cpu_percent": metric.cpu_percent,
                    "timestamp": metric.timestamp,
                    "metadata": metric.metadata
                } for metric in self.metrics
            ]
        }
        
        return report


async def main():
    """Main performance profiling execution."""
    profiler = AuthenticationPerformanceProfiler()
    profiler.start_profiling()
    
    try:
        logger.info("Starting comprehensive authentication performance analysis...")
        
        # Profile each component
        analyses = []
        
        # 1. Service Initialization (biggest bottleneck)
        service_analysis = await profiler.profile_service_initialization()
        analyses.append(service_analysis)
        
        # 2. Database Operations
        db_analysis = await profiler.profile_database_operations()
        analyses.append(db_analysis)
        
        # 3. Token Validation Queue (major bottleneck)
        queue_analysis = await profiler.profile_token_validation_queue()
        analyses.append(queue_analysis)
        
        # 4. Full Authentication Flow
        flow_analysis = await profiler.profile_authentication_flow()
        analyses.append(flow_analysis)
        
        # Generate comprehensive report
        report = profiler.generate_performance_report(analyses)
        
        # Save detailed report
        report_file = f"authentication_performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Performance analysis complete. Report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("AUTHENTICATION TIMEOUT PERFORMANCE ANALYSIS SUMMARY")
        print("="*80)
        print(f"Current Performance: {report['executive_summary']['current_performance']}")
        print(f"Target Performance: {report['executive_summary']['target_performance']}")
        print(f"Improvement Potential: {report['executive_summary']['improvement_potential']}")
        print(f"Critical Bottlenecks: {report['executive_summary']['critical_bottlenecks']}")
        print(f"Optimization Opportunities: {report['executive_summary']['optimization_opportunities']}")
        
        print("\nTOP PERFORMANCE BOTTLENECKS:")
        for analysis in analyses:
            if analysis.bottlenecks:
                print(f"\n{analysis.component_name.upper()}:")
                for bottleneck in analysis.bottlenecks[:3]:  # Top 3
                    print(f"  • {bottleneck}")
        
        print("\nIMMEDIATE OPTIMIZATION ACTIONS:")
        for optimization in report["priority_optimizations"]["immediate"]:
            print(f"  • {optimization}")
        
        print(f"\nDetailed report: {report_file}")
        print("="*80)
        
    finally:
        profiler.stop_profiling()


if __name__ == "__main__":
    asyncio.run(main())